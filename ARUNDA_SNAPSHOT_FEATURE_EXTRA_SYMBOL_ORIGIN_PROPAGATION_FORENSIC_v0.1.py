import sqlite3
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL ORIGIN PROPAGATION FORENSIC v0.1
# =============================================================================

SCRIPT_VERSION = "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

PROVENANCE_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SEMANTIC_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)

TARGET_SYMBOLS = {"4", "ASSET"}

NETWORK = "FORBIDDEN"
MODE = "READ ONLY"
DATABASE_WRITE = "FORBIDDEN"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    if not path.exists():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def normalize_symbol(value):
    if value is None:
        return None

    return str(value).strip()


def safe_json_value(value):
    """
    Convert SQLite/Python values into JSON-safe primitives.
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, bytes):
        return value.hex()

    return str(value)


# =============================================================================
# SQLITE INSPECTION
# =============================================================================

def connect_read_only(db_path):
    """
    Open SQLite explicitly in read-only URI mode.
    """
    uri = f"file:{db_path.as_posix()}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [row["name"] for row in rows]


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()

    result = []

    for row in rows:
        result.append(
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": row["notnull"],
                "default": row["dflt_value"],
                "pk": row["pk"],
            }
        )

    return result


# =============================================================================
# COLUMN SEMANTICS
# =============================================================================

SYMBOL_COLUMN_NAMES = {
    "symbol",
    "symbols",
    "asset",
    "assets",
    "asset_symbol",
    "asset_symbols",
    "ticker",
    "tickers",
    "coin",
    "coin_symbol",
    "market",
    "market_symbol",
    "instrument",
    "instrument_symbol",
    "base_asset",
    "base_symbol",
}

TIME_COLUMN_HINTS = (
    "time",
    "timestamp",
    "date",
    "datetime",
    "created",
    "updated",
    "modified",
    "event",
    "observed",
    "generated",
    "ingested",
    "recorded",
)

ID_COLUMN_HINTS = (
    "id",
    "rowid",
    "sequence",
    "seq",
    "version",
)


def is_symbol_like_column(column_name):
    name = column_name.strip().lower()

    if name in SYMBOL_COLUMN_NAMES:
        return True

    if "symbol" in name:
        return True

    if name == "asset":
        return True

    if name.endswith("_asset"):
        return True

    if name.endswith("_ticker"):
        return True

    return False


def is_time_like_column(column_name):
    name = column_name.strip().lower()

    return any(token in name for token in TIME_COLUMN_HINTS)


def is_id_like_column(column_name):
    name = column_name.strip().lower()

    if name == "id":
        return True

    if name == "rowid":
        return True

    return any(token in name for token in ID_COLUMN_HINTS)


# =============================================================================
# TABLE TARGET SEARCH
# =============================================================================

def search_target_in_column(conn, table_name, column_name, target):
    """
    Exact semantic match only.

    No LIKE.
    No substring matching.
    No normalization that could merge unrelated symbols.
    """

    table_q = quote_identifier(table_name)
    column_q = quote_identifier(column_name)

    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM {table_q}
        WHERE CAST({column_q} AS TEXT) = ?
    """

    row = conn.execute(sql, (target,)).fetchone()

    return int(row["cnt"])


def get_table_target_presence(conn, table_name, target):
    columns = get_columns(conn, table_name)

    symbol_columns = [
        c["name"]
        for c in columns
        if is_symbol_like_column(c["name"])
    ]

    findings = []

    for column_name in symbol_columns:
        try:
            count = search_target_in_column(
                conn,
                table_name,
                column_name,
                target,
            )
        except Exception as exc:
            findings.append(
                {
                    "column": column_name,
                    "error": str(exc),
                }
            )
            continue

        if count > 0:
            findings.append(
                {
                    "column": column_name,
                    "count": count,
                }
            )

    return findings


# =============================================================================
# SAMPLE ROW EXTRACTION
# =============================================================================

def get_sample_rows(
    conn,
    table_name,
    column_name,
    target,
    limit=5,
):
    """
    Read-only forensic samples.

    We intentionally inspect:
      - rowid when available
      - likely timestamp columns
      - likely ID columns
      - all columns for a very small number of rows
    """

    table_q = quote_identifier(table_name)
    column_q = quote_identifier(column_name)

    columns = get_columns(conn, table_name)

    selected = []

    for c in columns:
        name = c["name"]

        if (
            is_time_like_column(name)
            or is_id_like_column(name)
            or name == column_name
        ):
            if name not in selected:
                selected.append(name)

    # Include all columns only if table is reasonably narrow.
    # This remains bounded by LIMIT.
    if len(columns) <= 30:
        for c in columns:
            name = c["name"]
            if name not in selected:
                selected.append(name)

    if not selected:
        selected = [column_name]

    selected_sql = ", ".join(
        quote_identifier(name)
        for name in selected
    )

    sql = f"""
        SELECT {selected_sql}
        FROM {table_q}
        WHERE CAST({column_q} AS TEXT) = ?
        LIMIT ?
    """

    rows = conn.execute(
        sql,
        (target, limit),
    ).fetchall()

    result = []

    for row in rows:
        item = {}

        for key in row.keys():
            item[key] = safe_json_value(row[key])

        result.append(item)

    return result


# =============================================================================
# TABLE ROW COUNTS
# =============================================================================

def get_table_row_count(conn, table_name):
    table_q = quote_identifier(table_name)

    row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {table_q}"
    ).fetchone()

    return int(row["cnt"])


# =============================================================================
# DATABASE SYMBOL PROVENANCE
# =============================================================================

def build_database_provenance(conn):
    tables = get_tables(conn)

    target_results = {
        target: []
        for target in sorted(TARGET_SYMBOLS)
    }

    table_inventory = []

    for table_name in tables:
        columns = get_columns(conn, table_name)

        symbol_columns = [
            c["name"]
            for c in columns
            if is_symbol_like_column(c["name"])
        ]

        table_entry = {
            "table": table_name,
            "row_count": None,
            "symbol_like_columns": symbol_columns,
            "targets": {},
        }

        try:
            table_entry["row_count"] = get_table_row_count(
                conn,
                table_name,
            )
        except Exception as exc:
            table_entry["row_count_error"] = str(exc)

        for target in sorted(TARGET_SYMBOLS):
            findings = get_table_target_presence(
                conn,
                table_name,
                target,
            )

            if findings:
                table_entry["targets"][target] = findings

                for finding in findings:
                    if "count" not in finding:
                        continue

                    column_name = finding["column"]

                    samples = get_sample_rows(
                        conn,
                        table_name,
                        column_name,
                        target,
                        limit=5,
                    )

                    target_results[target].append(
                        {
                            "table": table_name,
                            "column": column_name,
                            "count": finding["count"],
                            "samples": samples,
                        }
                    )

        if table_entry["targets"]:
            table_inventory.append(table_entry)

    return target_results, table_inventory


# =============================================================================
# FIRST / LAST APPEARANCE FORENSICS
# =============================================================================

def find_timestamp_columns(columns):
    return [
        c["name"]
        for c in columns
        if is_time_like_column(c["name"])
    ]


def find_id_columns(columns):
    return [
        c["name"]
        for c in columns
        if is_id_like_column(c["name"])
    ]


def get_ordering_evidence(
    conn,
    table_name,
    column_name,
    target,
):
    """
    Attempts to identify earliest/latest observable rows.

    Important:
    This does NOT claim historical insertion order unless a timestamp
    or SQLite rowid is actually available.
    """

    columns = get_columns(conn, table_name)

    timestamp_columns = find_timestamp_columns(columns)
    id_columns = find_id_columns(columns)

    table_q = quote_identifier(table_name)
    column_q = quote_identifier(column_name)

    evidence = {
        "timestamp_columns": timestamp_columns,
        "id_columns": id_columns,
        "rowid_available": True,
        "ordering_attempts": [],
    }

    # -------------------------------------------------------------------------
    # Timestamp-based evidence
    # -------------------------------------------------------------------------

    for time_column in timestamp_columns[:5]:
        time_q = quote_identifier(time_column)

        sql = f"""
            SELECT {time_q} AS value
            FROM {table_q}
            WHERE CAST({column_q} AS TEXT) = ?
              AND {time_q} IS NOT NULL
            ORDER BY {time_q} ASC
            LIMIT 1
        """

        try:
            row = conn.execute(
                sql,
                (target,),
            ).fetchone()

            if row:
                evidence["ordering_attempts"].append(
                    {
                        "method": "timestamp_ascending",
                        "column": time_column,
                        "value": safe_json_value(row["value"]),
                    }
                )
        except Exception as exc:
            evidence["ordering_attempts"].append(
                {
                    "method": "timestamp_ascending",
                    "column": time_column,
                    "error": str(exc),
                }
            )

        sql = f"""
            SELECT {time_q} AS value
            FROM {table_q}
            WHERE CAST({column_q} AS TEXT) = ?
              AND {time_q} IS NOT NULL
            ORDER BY {time_q} DESC
            LIMIT 1
        """

        try:
            row = conn.execute(
                sql,
                (target,),
            ).fetchone()

            if row:
                evidence["ordering_attempts"].append(
                    {
                        "method": "timestamp_descending",
                        "column": time_column,
                        "value": safe_json_value(row["value"]),
                    }
                )
        except Exception as exc:
            evidence["ordering_attempts"].append(
                {
                    "method": "timestamp_descending",
                    "column": time_column,
                    "error": str(exc),
                }
            )

    # -------------------------------------------------------------------------
    # ID-based evidence
    # -------------------------------------------------------------------------

    for id_column in id_columns[:5]:
        id_q = quote_identifier(id_column)

        sql = f"""
            SELECT {id_q} AS value
            FROM {table_q}
            WHERE CAST({column_q} AS TEXT) = ?
              AND {id_q} IS NOT NULL
            ORDER BY {id_q} ASC
            LIMIT 1
        """

        try:
            row = conn.execute(
                sql,
                (target,),
            ).fetchone()

            if row:
                evidence["ordering_attempts"].append(
                    {
                        "method": "id_ascending",
                        "column": id_column,
                        "value": safe_json_value(row["value"]),
                    }
                )
        except Exception as exc:
            evidence["ordering_attempts"].append(
                {
                    "method": "id_ascending",
                    "column": id_column,
                    "error": str(exc),
                }
            )

    # -------------------------------------------------------------------------
    # SQLite rowid evidence
    # -------------------------------------------------------------------------

    sql = f"""
        SELECT rowid AS value
        FROM {table_q}
        WHERE CAST({column_q} AS TEXT) = ?
        ORDER BY rowid ASC
        LIMIT 1
    """

    try:
        row = conn.execute(
            sql,
            (target,),
        ).fetchone()

        if row:
            evidence["ordering_attempts"].append(
                {
                    "method": "sqlite_rowid_ascending",
                    "column": "rowid",
                    "value": safe_json_value(row["value"]),
                }
            )
    except Exception as exc:
        evidence["rowid_available"] = False
        evidence["ordering_attempts"].append(
            {
                "method": "sqlite_rowid_ascending",
                "column": "rowid",
                "error": str(exc),
            }
        )

    return evidence


# =============================================================================
# ORIGIN CLASSIFICATION
# =============================================================================

def classify_origin(target, presence_records):
    """
    Conservative classification.

    We do NOT infer the exact original insertion point merely from
    propagation across multiple tables.

    The classification is based only on observable evidence.
    """

    tables = sorted(
        {
            record["table"]
            for record in presence_records
        }
    )

    count = len(tables)

    if count == 0:
        return {
            "origin_class": "NOT_OBSERVED_IN_DATABASE_SYMBOL_COLUMNS",
            "confidence": "HIGH",
            "reason": (
                "Target was not observed in any recognized symbol-like "
                "database column."
            ),
        }

    if target == "ASSET":
        return {
            "origin_class": "GENERIC_FIELD_LABEL_PROPAGATED_AS_SYMBOL",
            "confidence": "HIGH",
            "reason": (
                "ASSET is a generic field label and appears in multiple "
                "symbol-like columns; this pattern is inconsistent with "
                "a canonical market symbol."
            ),
        }

    if target == "4":
        return {
            "origin_class": "NUMERIC_IDENTIFIER_PROPAGATED_AS_SYMBOL",
            "confidence": "HIGH",
            "reason": (
                "4 is a pure numeric token and is therefore not established "
                "as a canonical market symbol."
            ),
        }

    if count >= 3:
        return {
            "origin_class": "MULTI_TABLE_PROPAGATED_EXTRA_SYMBOL",
            "confidence": "MEDIUM",
            "reason": (
                "Target appears across multiple database symbol-like "
                "columns, but exact first insertion point is not established."
            ),
        }

    return {
        "origin_class": "LIMITED_SYMBOL_COLUMN_PRESENCE",
        "confidence": "MEDIUM",
        "reason": (
            "Target is present in a limited number of symbol-like columns."
        ),
    }


# =============================================================================
# CROSS-TABLE PROPAGATION GRAPH
# =============================================================================

def build_propagation_graph(target_results):
    graph = {}

    for target, records in target_results.items():
        graph[target] = {
            "tables": [],
            "edges": [],
        }

        tables = sorted(
            {
                record["table"]
                for record in records
            }
        )

        graph[target]["tables"] = tables

        # The graph is intentionally observational:
        # shared presence does NOT prove causal propagation.
        for i, source in enumerate(tables):
            for destination in tables[i + 1:]:
                graph[target]["edges"].append(
                    {
                        "from": source,
                        "to": destination,
                        "relationship": "CO_PRESENT",
                        "causality_established": False,
                    }
                )

    return graph


# =============================================================================
# ARTIFACT INPUT VALIDATION
# =============================================================================

def validate_input_artifacts():
    normalization = load_json(NORMALIZATION_PATH)
    provenance = load_json(PROVENANCE_PATH)
    semantic = load_json(SEMANTIC_PATH)

    return {
        "normalization": {
            "path": str(NORMALIZATION_PATH),
            "sha256": sha256_file(NORMALIZATION_PATH),
            "root_type": type(normalization).__name__,
        },
        "provenance": {
            "path": str(PROVENANCE_PATH),
            "sha256": sha256_file(PROVENANCE_PATH),
            "root_type": type(provenance).__name__,
        },
        "semantic": {
            "path": str(SEMANTIC_PATH),
            "sha256": sha256_file(SEMANTIC_PATH),
            "root_type": type(semantic).__name__,
        },
    }


# =============================================================================
# FORENSIC STATUS
# =============================================================================

def determine_status(target_results):
    observed = {
        target: bool(records)
        for target, records in target_results.items()
    }

    if all(observed.values()):
        return "EXTRA_SYMBOL_ORIGIN_AND_PROPAGATION_OBSERVED"

    if any(observed.values()):
        return "EXTRA_SYMBOL_PARTIAL_ORIGIN_OBSERVED"

    return "EXTRA_SYMBOL_ORIGIN_NOT_OBSERVED"


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 90)
    print("ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL ORIGIN PROPAGATION FORENSIC v0.1")
    print("=" * 90)

    print(f"Database       : {DB_PATH}")
    print(f"Normalization  : {NORMALIZATION_PATH}")
    print(f"Provenance     : {PROVENANCE_PATH}")
    print(f"Semantic       : {SEMANTIC_PATH}")
    print(f"Mode           : {MODE}")
    print(f"Network        : {NETWORK}")
    print(f"Database Write : {DATABASE_WRITE}")
    print(f"Prediction     : {PREDICTION}")
    print(f"Decision       : {DECISION}")
    print("-" * 90)

    # -------------------------------------------------------------------------
    # Input artifacts
    # -------------------------------------------------------------------------

    artifact_inputs = validate_input_artifacts()

    normalization = load_json(NORMALIZATION_PATH)
    provenance = load_json(PROVENANCE_PATH)
    semantic = load_json(SEMANTIC_PATH)

    normalized_universe = normalization.get(
        "normalized_expected_universe",
        [],
    )

    if not isinstance(normalized_universe, list):
        normalized_universe = []

    normalized_universe = {
        normalize_symbol(x)
        for x in normalized_universe
        if normalize_symbol(x) is not None
    }

    # -------------------------------------------------------------------------
    # Verify targets remain EXTRA relative to normalized universe
    # -------------------------------------------------------------------------

    still_extra = sorted(
        TARGET_SYMBOLS - normalized_universe
    )

    print("=" * 90)
    print("TARGET CONTRACT")
    print("=" * 90)

    print(
        f"Normalized Expected Universe : "
        f"{len(normalized_universe)}"
    )

    print(
        f"Requested Extra Symbols      : "
        f"{len(TARGET_SYMBOLS)}"
    )

    print(
        "Targets                       : "
        + ", ".join(sorted(TARGET_SYMBOLS))
    )

    print(
        "Still Outside Expected       : "
        + ", ".join(still_extra)
    )

    if set(still_extra) != TARGET_SYMBOLS:
        raise RuntimeError(
            "Target symbols are no longer both outside the normalized "
            "expected universe."
        )

    # -------------------------------------------------------------------------
    # Open DB read-only
    # -------------------------------------------------------------------------

    conn = connect_read_only(DB_PATH)

    try:

        # ---------------------------------------------------------------------
        # Database inventory
        # ---------------------------------------------------------------------

        tables = get_tables(conn)

        print("=" * 90)
        print("DATABASE INVENTORY")
        print("=" * 90)

        print(f"Database Tables : {len(tables)}")

        # ---------------------------------------------------------------------
        # Search all tables / recognized symbol-like columns
        # ---------------------------------------------------------------------

        target_results, table_inventory = build_database_provenance(
            conn
        )

        # ---------------------------------------------------------------------
        # Ordering evidence
        # ---------------------------------------------------------------------

        ordering_evidence = {
            target: []
            for target in sorted(TARGET_SYMBOLS)
        }

        for target in sorted(TARGET_SYMBOLS):

            for record in target_results[target]:

                evidence = get_ordering_evidence(
                    conn,
                    record["table"],
                    record["column"],
                    target,
                )

                ordering_evidence[target].append(
                    {
                        "table": record["table"],
                        "column": record["column"],
                        "evidence": evidence,
                    }
                )

        # ---------------------------------------------------------------------
        # Origin classification
        # ---------------------------------------------------------------------

        classifications = {}

        for target in sorted(TARGET_SYMBOLS):

            classifications[target] = classify_origin(
                target,
                target_results[target],
            )

        # ---------------------------------------------------------------------
        # Propagation graph
        # ---------------------------------------------------------------------

        propagation_graph = build_propagation_graph(
            target_results
        )

        # ---------------------------------------------------------------------
        # Console report
        # ---------------------------------------------------------------------

        print("=" * 90)
        print("EXTRA SYMBOL ORIGIN / PROPAGATION")
        print("=" * 90)

        for target in sorted(TARGET_SYMBOLS):

            records = target_results[target]

            tables_for_target = sorted(
                {
                    record["table"]
                    for record in records
                }
            )

            print("-" * 90)
            print(f"SYMBOL : {target}")
            print(
                f"OBSERVED TABLE COUNT : "
                f"{len(tables_for_target)}"
            )

            if tables_for_target:
                for table_name in tables_for_target:
                    print(f"  {table_name}")

            classification = classifications[target]

            print(
                f"ORIGIN CLASS : "
                f"{classification['origin_class']}"
            )

            print(
                f"CONFIDENCE   : "
                f"{classification['confidence']}"
            )

            print(
                f"REASON       : "
                f"{classification['reason']}"
            )

        # ---------------------------------------------------------------------
        # Detailed source evidence
        # ---------------------------------------------------------------------

        print("=" * 90)
        print("DETAILED DATABASE EVIDENCE")
        print("=" * 90)

        for target in sorted(TARGET_SYMBOLS):

            print("-" * 90)
            print(f"SYMBOL : {target}")

            records = target_results[target]

            for record in records:

                print(
                    f"  TABLE  : {record['table']}"
                )

                print(
                    f"  COLUMN : {record['column']}"
                )

                print(
                    f"  COUNT  : {record['count']}"
                )

                if record["samples"]:
                    print("  SAMPLE ROWS :")

                    for sample in record["samples"]:
                        print(
                            "    "
                            + json.dumps(
                                sample,
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )

        # ---------------------------------------------------------------------
        # Conservative first-origin assessment
        # ---------------------------------------------------------------------

        print("=" * 90)
        print("FIRST ORIGIN ASSESSMENT")
        print("=" * 90)

        first_origin_assessment = {}

        for target in sorted(TARGET_SYMBOLS):

            records = ordering_evidence[target]

            timestamp_candidates = []
            rowid_candidates = []
            id_candidates = []

            for record in records:

                evidence = record["evidence"]

                for attempt in evidence["ordering_attempts"]:

                    method = attempt.get("method")

                    item = {
                        "table": record["table"],
                        "column": record["column"],
                        "method": method,
                        "value": attempt.get("value"),
                    }

                    if method.startswith("timestamp_"):
                        timestamp_candidates.append(item)

                    elif method.startswith("sqlite_rowid"):
                        rowid_candidates.append(item)

                    elif method.startswith("id_"):
                        id_candidates.append(item)

            if timestamp_candidates:
                assessment = {
                    "status": "TEMPORAL_EVIDENCE_AVAILABLE",
                    "exact_first_insertion_point_established": False,
                    "timestamp_evidence": timestamp_candidates,
                    "rowid_evidence": rowid_candidates,
                    "id_evidence": id_candidates,
                    "reason": (
                        "Timestamp-like fields were found, but timestamp "
                        "values alone do not establish the original source "
                        "insertion point."
                    ),
                }

            elif rowid_candidates:
                assessment = {
                    "status": "ROWID_EVIDENCE_AVAILABLE",
                    "exact_first_insertion_point_established": False,
                    "timestamp_evidence": [],
                    "rowid_evidence": rowid_candidates,
                    "id_evidence": id_candidates,
                    "reason": (
                        "SQLite rowid ordering is observable, but rowid "
                        "ordering does not prove causal origin across tables."
                    ),
                }

            else:
                assessment = {
                    "status": "NO_RELIABLE_ORDERING_EVIDENCE",
                    "exact_first_insertion_point_established": False,
                    "timestamp_evidence": [],
                    "rowid_evidence": [],
                    "id_evidence": id_candidates,
                    "reason": (
                        "No reliable temporal or row-order evidence was "
                        "available to establish the first insertion point."
                    ),
                }

            first_origin_assessment[target] = assessment

            print("-" * 90)
            print(f"SYMBOL : {target}")
            print(
                f"STATUS : "
                f"{assessment['status']}"
            )
            print(
                "EXACT FIRST INSERTION POINT : "
                f"{assessment['exact_first_insertion_point_established']}"
            )

        # ---------------------------------------------------------------------
        # Database fingerprint
        # ---------------------------------------------------------------------

        try:
            db_size = DB_PATH.stat().st_size
        except Exception:
            db_size = None

        # ---------------------------------------------------------------------
        # Artifact
        # ---------------------------------------------------------------------

        forensic_status = determine_status(
            target_results
        )

        artifact = {
            "artifact": OUTPUT_PATH.name,
            "script_version": SCRIPT_VERSION,
            "generated_at_utc": utc_now(),

            "database": str(DB_PATH),

            "mode": MODE,
            "network": NETWORK,
            "database_write": DATABASE_WRITE,
            "prediction": PREDICTION,
            "decision": DECISION,

            "database_fingerprint": {
                "database_size_bytes": db_size,
            },

            "input_artifacts": artifact_inputs,

            "target_contract": {
                "targets": sorted(TARGET_SYMBOLS),
                "normalized_expected_universe_count": len(
                    normalized_universe
                ),
                "targets_outside_expected_universe": still_extra,
                "all_targets_extra": (
                    set(still_extra) == TARGET_SYMBOLS
                ),
            },

            "semantic_input": {
                "artifact": str(SEMANTIC_PATH),
                "sha256": sha256_file(SEMANTIC_PATH),
                "target_symbols": sorted(TARGET_SYMBOLS),
            },

            "provenance_input": {
                "artifact": str(PROVENANCE_PATH),
                "sha256": sha256_file(PROVENANCE_PATH),
            },

            "database_inventory": {
                "table_count": len(tables),
                "tables": tables,
            },

            "target_database_provenance": target_results,

            "table_inventory_with_targets": table_inventory,

            "ordering_evidence": ordering_evidence,

            "first_origin_assessment": first_origin_assessment,

            "propagation_graph": propagation_graph,

            "origin_classification": classifications,

            "causality_policy": {
                "shared_presence_is_not_causality": True,
                "first_insertion_point_requires_direct_evidence": True,
                "rowid_is_not_treated_as_causal_proof": True,
                "timestamp_is_not_treated_as_causal_proof": True,
                "no_symbol_reclassification_performed": True,
                "no_universe_rebuild_performed": True,
            },

            "forensic_status": forensic_status,

            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",
            "database_repair": "NOT PERFORMED",
            "database_write_status": "NOT PERFORMED",

            "outcome": {
                "symbols_analyzed": sorted(TARGET_SYMBOLS),
                "symbols_observed": sorted(
                    target
                    for target in TARGET_SYMBOLS
                    if target_results[target]
                ),
                "symbols_not_observed": sorted(
                    target
                    for target in TARGET_SYMBOLS
                    if not target_results[target]
                ),
            },
        }

        # ---------------------------------------------------------------------
        # Canonical JSON
        # ---------------------------------------------------------------------

        canonical_without_hash = json.dumps(
            artifact,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        artifact["artifact_sha256"] = sha256_bytes(
            canonical_without_hash
        )

        with OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as f:
            json.dump(
                artifact,
                f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

        # ---------------------------------------------------------------------
        # Final report
        # ---------------------------------------------------------------------

        print("=" * 90)
        print("FORENSIC STATUS")
        print("=" * 90)

        print(
            f"FORENSIC STATUS : "
            f"{forensic_status}"
        )

        print(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )

        print(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )

        print(
            "DATABASE WRITE : NOT PERFORMED"
        )

        print(
            "DATABASE REPAIR : NOT PERFORMED"
        )

        print("=" * 90)
        print("ARTIFACT")
        print("=" * 90)

        print(
            f"Artifact : {OUTPUT_PATH}"
        )

        print(
            f"SHA256   : "
            f"{artifact['artifact_sha256']}"
        )

        print("=" * 90)

    finally:
        conn.close()


if __name__ == "__main__":
    main()