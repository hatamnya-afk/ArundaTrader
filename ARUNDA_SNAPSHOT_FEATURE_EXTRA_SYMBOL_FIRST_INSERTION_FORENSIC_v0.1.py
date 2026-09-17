# ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.py
# READ ONLY / NETWORK FORBIDDEN / DATABASE WRITE FORBIDDEN
#
# Purpose:
#   Determine the earliest observable database timestamp/evidence for
#   the two extra feature-input symbols:
#       4
#       ASSET
#
# This script does NOT:
#   - modify the database
#   - repair/delete/rebuild anything
#   - perform prediction
#   - make trading decisions
#   - access network
#
# It only performs forensic reads against arunda.db and writes a JSON artifact.

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# CONTRACT
# =============================================================================

SCRIPT_NAME = "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

PROVENANCE_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SEMANTIC_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)

ORIGIN_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)

OUTPUT_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)

TARGET_SYMBOLS = {"4", "ASSET"}

MAX_SAMPLE_ROWS = 5


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    if not isinstance(obj, dict):
        raise RuntimeError(f"Artifact root is not an object: {path}")

    return obj


def canonical_sha256(obj: Any) -> str:
    canonical = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def json_safe(value: Any) -> Any:
    """
    Convert SQLite/Python values into JSON-safe primitives.
    """
    if isinstance(value, dict):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]

    if isinstance(value, set):
        return sorted(json_safe(v) for v in value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


# =============================================================================
# SQLITE INVENTORY
# =============================================================================

def get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [str(row[0]) for row in rows]


def get_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table)})"
    ).fetchall()

    return [str(row[1]) for row in rows]


def find_symbol_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:
    columns = get_columns(conn, table)

    candidates = []

    for column in columns:
        normalized = column.strip().lower()

        if normalized in {
            "symbol",
            "asset",
            "asset_symbol",
            "asset_symbols",
            "ticker",
            "coin",
        }:
            candidates.append(column)

    return candidates


# =============================================================================
# ROW SERIALIZATION
# =============================================================================

def row_to_dict(
    cursor: sqlite3.Cursor,
    row: sqlite3.Row,
) -> dict[str, Any]:
    return {
        str(cursor.description[i][0]): json_safe(row[i])
        for i in range(len(row))
    }


# =============================================================================
# TIMESTAMP DETECTION
# =============================================================================

TIMESTAMP_COLUMN_PRIORITY = [
    "timestamp",
    "source_timestamp",
    "created_at",
    "first_seen",
    "updated_at",
    "last_updated",
    "date_added",
    "observed_at",
    "inserted_at",
    "event_timestamp",
    "time",
    "datetime",
]


def timestamp_columns(columns: list[str]) -> list[str]:
    lower_map = {
        c.lower(): c
        for c in columns
    }

    result = []

    for preferred in TIMESTAMP_COLUMN_PRIORITY:
        actual = lower_map.get(preferred)

        if actual is not None:
            result.append(actual)

    return result


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    candidates = [
        text,
        text.replace("Z", "+00:00"),
    ]

    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)

        except ValueError:
            pass

    return None


# =============================================================================
# SYMBOL SEARCH
# =============================================================================

def search_symbol_rows(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    symbol: str,
) -> dict[str, Any]:

    q_table = quote_identifier(table)
    q_column = quote_identifier(column)

    columns = get_columns(conn, table)
    ts_columns = timestamp_columns(columns)

    select_sql = f"""
        SELECT *
        FROM {q_table}
        WHERE CAST({q_column} AS TEXT) = ?
    """

    cursor = conn.execute(
        select_sql,
        (symbol,),
    )

    rows = cursor.fetchall()

    total_count = len(rows)

    earliest_candidates = []

    for row in rows:
        row_dict = row_to_dict(cursor, row)

        parsed_timestamps = []

        for ts_col in ts_columns:
            if ts_col in row_dict:
                parsed = parse_timestamp(row_dict.get(ts_col))

                if parsed is not None:
                    parsed_timestamps.append(
                        (
                            parsed,
                            ts_col,
                            row_dict.get(ts_col),
                        )
                    )

        if parsed_timestamps:
            parsed_timestamps.sort(key=lambda x: x[0])

            earliest_dt, earliest_col, earliest_raw = (
                parsed_timestamps[0]
            )

            earliest_candidates.append(
                {
                    "timestamp_utc": earliest_dt.isoformat(),
                    "timestamp_column": earliest_col,
                    "raw_value": json_safe(earliest_raw),
                    "row": row_dict,
                }
            )
        else:
            earliest_candidates.append(
                {
                    "timestamp_utc": None,
                    "timestamp_column": None,
                    "raw_value": None,
                    "row": row_dict,
                }
            )

    timestamped = [
        x
        for x in earliest_candidates
        if x["timestamp_utc"] is not None
    ]

    timestamped.sort(
        key=lambda x: x["timestamp_utc"]
    )

    first = timestamped[0] if timestamped else None

    samples = timestamped[:MAX_SAMPLE_ROWS]

    if not samples:
        samples = earliest_candidates[:MAX_SAMPLE_ROWS]

    return {
        "table": table,
        "column": column,
        "symbol": symbol,
        "row_count": total_count,
        "timestamp_columns_considered": ts_columns,
        "timestamped_row_count": len(timestamped),
        "first_observed_timestamp_utc": (
            first["timestamp_utc"]
            if first
            else None
        ),
        "first_observed_timestamp_column": (
            first["timestamp_column"]
            if first
            else None
        ),
        "first_observed_row": (
            first["row"]
            if first
            else None
        ),
        "earliest_observed_rows": samples,
    }


# =============================================================================
# DATABASE FORENSIC
# =============================================================================

def collect_symbol_evidence(
    conn: sqlite3.Connection,
    symbol: str,
) -> list[dict[str, Any]]:

    evidence = []

    tables = get_tables(conn)

    for table in tables:

        symbol_columns = find_symbol_columns(
            conn,
            table,
        )

        for column in symbol_columns:

            result = search_symbol_rows(
                conn,
                table,
                column,
                symbol,
            )

            if result["row_count"] > 0:
                evidence.append(result)

    return evidence


# =============================================================================
# FIRST OBSERVABLE INSERTION ASSESSMENT
# =============================================================================

def determine_first_observable_event(
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:

    candidates = []

    for item in evidence:

        timestamp = item.get(
            "first_observed_timestamp_utc"
        )

        if timestamp is None:
            continue

        candidates.append(
            {
                "timestamp_utc": timestamp,
                "table": item["table"],
                "column": item["column"],
                "row_count": item["row_count"],
                "timestamp_column": item[
                    "first_observed_timestamp_column"
                ],
                "row": item[
                    "first_observed_row"
                ],
            }
        )

    candidates.sort(
        key=lambda x: x["timestamp_utc"]
    )

    if not candidates:
        return {
            "status": "NO_TIMESTAMPED_EVIDENCE",
            "exact_first_insertion_point": False,
            "first_observable_timestamp_utc": None,
            "first_observable_table": None,
            "first_observable_column": None,
            "first_observable_row": None,
            "candidate_count": 0,
            "candidates": [],
        }

    first = candidates[0]

    distinct_first_timestamp = first[
        "timestamp_utc"
    ]

    same_time_candidates = [
        c
        for c in candidates
        if c["timestamp_utc"]
        == distinct_first_timestamp
    ]

    return {
        "status": "EARLIEST_OBSERVABLE_TIMESTAMP_IDENTIFIED",
        "exact_first_insertion_point": False,
        "first_observable_timestamp_utc": (
            first["timestamp_utc"]
        ),
        "first_observable_table": (
            first["table"]
        ),
        "first_observable_column": (
            first["column"]
        ),
        "first_observable_row": (
            first["row"]
        ),
        "candidate_count": len(candidates),
        "same_timestamp_candidate_count": len(
            same_time_candidates
        ),
        "candidates": candidates,
    }


# =============================================================================
# CROSS-TABLE PROPAGATION ASSESSMENT
# =============================================================================

def propagation_assessment(
    evidence: list[dict[str, Any]],
    first_event: dict[str, Any],
) -> dict[str, Any]:

    tables = sorted(
        {
            item["table"]
            for item in evidence
        }
    )

    timestamped_tables = sorted(
        {
            item["table"]
            for item in evidence
            if item.get(
                "first_observed_timestamp_utc"
            )
            is not None
        }
    )

    return {
        "observed_table_count": len(tables),
        "observed_tables": tables,
        "timestamped_table_count": len(
            timestamped_tables
        ),
        "timestamped_tables": timestamped_tables,
        "first_observable_timestamp_utc": first_event[
            "first_observable_timestamp_utc"
        ],
        "exact_propagation_chain_established": False,
        "reason": (
            "Database evidence establishes earliest "
            "observable records but does not prove the "
            "application-level insertion caller or exact "
            "propagation sequence."
        ),
    }


# =============================================================================
# INPUT ARTIFACT VALIDATION
# =============================================================================

def validate_input_artifacts() -> dict[str, Any]:

    required = {
        "normalization": NORMALIZATION_ARTIFACT,
        "provenance": PROVENANCE_ARTIFACT,
        "semantic": SEMANTIC_ARTIFACT,
        "origin": ORIGIN_ARTIFACT,
    }

    result = {}

    for name, path in required.items():

        if not path.exists():
            raise FileNotFoundError(
                f"Required artifact not found: {path}"
            )

        result[name] = {
            "path": str(path),
            "sha256": sha256_file(path),
        }

    return result


# =============================================================================
# TARGET VALIDATION
# =============================================================================

def resolve_targets(
    provenance: dict[str, Any],
    semantic: dict[str, Any],
    origin: dict[str, Any],
) -> list[str]:

    discovered = set()

    # -------------------------------------------------------------------------
    # Provenance artifact
    # -------------------------------------------------------------------------

    cross_source = provenance.get(
        "cross_source_extra_presence",
        {},
    )

    if isinstance(cross_source, dict):

        for source_info in cross_source.values():

            if not isinstance(source_info, dict):
                continue

            extras = source_info.get(
                "extra_symbols",
                [],
            )

            if isinstance(extras, list):
                for symbol in extras:
                    discovered.add(str(symbol))

    # -------------------------------------------------------------------------
    # Semantic artifact
    # -------------------------------------------------------------------------

    for key in (
        "numeric_symbols",
        "generic_field_labels",
        "unresolved_symbols",
    ):

        values = semantic.get(key, [])

        if isinstance(values, list):

            for symbol in values:
                discovered.add(str(symbol))

    # -------------------------------------------------------------------------
    # Origin artifact
    # -------------------------------------------------------------------------

    for key in (
        "symbols",
        "target_symbols",
        "resolved_symbols",
    ):

        values = origin.get(key, [])

        if isinstance(values, list):

            for symbol in values:
                discovered.add(str(symbol))

    resolved = sorted(
        discovered.intersection(
            TARGET_SYMBOLS
        )
    )

    if set(resolved) != TARGET_SYMBOLS:
        raise RuntimeError(
            "Required target symbols could not be "
            f"resolved. Found={resolved}, "
            f"Required={sorted(TARGET_SYMBOLS)}"
        )

    return resolved


# =============================================================================
# DATABASE FINGERPRINT
# =============================================================================

def database_fingerprint(
    conn: sqlite3.Connection,
) -> dict[str, Any]:

    tables = get_tables(conn)

    table_row_counts = {}

    for table in tables:

        q_table = quote_identifier(table)

        row = conn.execute(
            f"SELECT COUNT(*) FROM {q_table}"
        ).fetchone()

        table_row_counts[table] = int(
            row[0]
        )

    return {
        "table_count": len(tables),
        "tables": tables,
        "table_row_counts": table_row_counts,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL "
        "FIRST INSERTION FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database       : {DB_PATH}")
    print(
        f"Normalization   : {NORMALIZATION_ARTIFACT}"
    )
    print(
        f"Provenance      : {PROVENANCE_ARTIFACT}"
    )
    print(
        f"Semantic        : {SEMANTIC_ARTIFACT}"
    )
    print(
        f"Origin          : {ORIGIN_ARTIFACT}"
    )
    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Database Write  : FORBIDDEN")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")
    print("-" * 90)

    # -------------------------------------------------------------------------
    # Input contract
    # -------------------------------------------------------------------------

    input_artifacts = (
        validate_input_artifacts()
    )

    normalization = load_json(
        NORMALIZATION_ARTIFACT
    )

    provenance = load_json(
        PROVENANCE_ARTIFACT
    )

    semantic = load_json(
        SEMANTIC_ARTIFACT
    )

    origin = load_json(
        ORIGIN_ARTIFACT
    )

    expected_universe = (
        normalization.get(
            "expected_universe"
        )
        or normalization.get(
            "resolved_expected_universe"
        )
        or normalization.get(
            "symbol_count"
        )
    )

    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)
    print(
        f"Expected Universe : "
        f"{expected_universe}"
    )

    targets = resolve_targets(
        provenance,
        semantic,
        origin,
    )

    print(
        f"Target Symbols    : "
        f"{', '.join(targets)}"
    )

    print("-" * 90)

    # -------------------------------------------------------------------------
    # Database open — explicitly read-only
    # -------------------------------------------------------------------------

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    db_uri = (
        "file:"
        + str(DB_PATH).replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        db_uri,
        uri=True,
        timeout=30,
    )

    conn.row_factory = sqlite3.Row

    try:

        db_fingerprint = database_fingerprint(
            conn
        )

        print("=" * 90)
        print("DATABASE INVENTORY")
        print("=" * 90)
        print(
            f"Database Tables : "
            f"{db_fingerprint['table_count']}"
        )

        # ---------------------------------------------------------------------
        # Per-symbol forensic investigation
        # ---------------------------------------------------------------------

        symbol_results = {}

        for symbol in targets:

            print("=" * 90)
            print(
                f"SYMBOL : {symbol}"
            )
            print("=" * 90)

            evidence = collect_symbol_evidence(
                conn,
                symbol,
            )

            first_event = (
                determine_first_observable_event(
                    evidence
                )
            )

            propagation = (
                propagation_assessment(
                    evidence,
                    first_event,
                )
            )

            print(
                f"Observed tables : "
                f"{propagation['observed_table_count']}"
            )

            for table in propagation[
                "observed_tables"
            ]:
                print(
                    f"  {table}"
                )

            print(
                "First observable timestamp : "
                f"{first_event['first_observable_timestamp_utc']}"
            )

            print(
                "First observable table      : "
                f"{first_event['first_observable_table']}"
            )

            print(
                "First observable column     : "
                f"{first_event['first_observable_column']}"
            )

            print(
                "Exact insertion point       : "
                f"{first_event['exact_first_insertion_point']}"
            )

            symbol_results[symbol] = {
                "symbol": symbol,
                "evidence": evidence,
                "first_observable_event": first_event,
                "propagation_assessment": propagation,
            }

        # ---------------------------------------------------------------------
        # Cross-symbol summary
        # ---------------------------------------------------------------------

        print("=" * 90)
        print(
            "CROSS-SYMBOL FIRST OBSERVABLE SUMMARY"
        )
        print("=" * 90)

        first_timestamps = []

        for symbol in targets:

            event = symbol_results[
                symbol
            ][
                "first_observable_event"
            ]

            timestamp = event.get(
                "first_observable_timestamp_utc"
            )

            print(
                f"SYMBOL : {symbol}"
            )
            print(
                f"FIRST OBSERVABLE : {timestamp}"
            )
            print(
                f"TABLE : "
                f"{event.get('first_observable_table')}"
            )
            print(
                f"COLUMN : "
                f"{event.get('first_observable_column')}"
            )
            print(
                f"EXACT INSERTION : "
                f"{event.get('exact_first_insertion_point')}"
            )
            print("-" * 90)

            if timestamp:
                first_timestamps.append(
                    (
                        timestamp,
                        symbol,
                    )
                )

        first_timestamps.sort()

        # ---------------------------------------------------------------------
        # Important forensic limitation
        # ---------------------------------------------------------------------

        temporal_status = (
            "TEMPORAL_EVIDENCE_AVAILABLE"
            if first_timestamps
            else "NO_TEMPORAL_EVIDENCE"
        )

        exact_first_insertion = all(
            result[
                "first_observable_event"
            ][
                "exact_first_insertion_point"
            ]
            for result in symbol_results.values()
        )

        if exact_first_insertion:
            forensic_status = (
                "EXACT_FIRST_INSERTION_POINTS_ESTABLISHED"
            )
        elif temporal_status == (
            "TEMPORAL_EVIDENCE_AVAILABLE"
        ):
            forensic_status = (
                "EARLIEST_OBSERVABLE_SYMBOL_RECORDS_ESTABLISHED"
            )
        else:
            forensic_status = (
                "FIRST_INSERTION_NOT_OBSERVABLE"
            )

        # ---------------------------------------------------------------------
        # Artifact
        # ---------------------------------------------------------------------

        artifact = {
            "artifact": {
                "name": OUTPUT_ARTIFACT.name,
                "version": "v0.1",
                "generated_at_utc": utc_now(),
            },

            "contract": {
                "script": SCRIPT_NAME,
                "database": str(DB_PATH),
                "mode": "READ ONLY",
                "network": "FORBIDDEN",
                "database_write": "FORBIDDEN",
                "prediction": "FORBIDDEN",
                "decision": "FORBIDDEN",
            },

            "input_artifacts": (
                input_artifacts
            ),

            "target_contract": {
                "expected_universe": (
                    expected_universe
                ),
                "target_symbols": targets,
                "target_count": len(targets),
            },

            "database_fingerprint": (
                db_fingerprint
            ),

            "symbol_results": (
                symbol_results
            ),

            "cross_symbol_first_observable_summary": {
                "ordered_by_first_observation": [
                    {
                        "symbol": symbol,
                        "first_observable_timestamp_utc": timestamp,
                    }
                    for timestamp, symbol
                    in first_timestamps
                ],
            },

            "first_insertion_assessment": {
                "temporal_status": (
                    temporal_status
                ),
                "exact_first_insertion_points": (
                    exact_first_insertion
                ),
                "forensic_status": (
                    forensic_status
                ),
                "important_limitation": (
                    "A database timestamp identifies the "
                    "earliest observable record carrying "
                    "the target symbol. It does not by "
                    "itself prove the exact application "
                    "function, caller, SQL statement, or "
                    "first insertion event."
                ),
            },

            "forensic_status": forensic_status,

            "claims": {
                "predictive_claim": (
                    "NOT ESTABLISHED"
                ),
                "relationship_calculation": (
                    "NOT PERFORMED"
                ),
                "database_write": (
                    "NOT PERFORMED"
                ),
                "database_repair": (
                    "NOT PERFORMED"
                ),
            },
        }

        # ---------------------------------------------------------------------
        # Canonicalize JSON-safe representation
        # ---------------------------------------------------------------------

        artifact = json_safe(
            artifact
        )

        artifact["artifact"][
            "content_sha256"
        ] = canonical_sha256(
            artifact
        )

        with OUTPUT_ARTIFACT.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                artifact,
                f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

        artifact_sha256 = (
            sha256_file(
                OUTPUT_ARTIFACT
            )
        )

        # ---------------------------------------------------------------------
        # Final report
        # ---------------------------------------------------------------------

        print("=" * 90)
        print(
            "FIRST INSERTION / EARLIEST "
            "OBSERVABLE ASSESSMENT"
        )
        print("=" * 90)

        for symbol in targets:

            result = symbol_results[
                symbol
            ]

            event = result[
                "first_observable_event"
            ]

            print("-" * 90)
            print(
                f"SYMBOL : {symbol}"
            )
            print(
                "FIRST OBSERVABLE TIMESTAMP : "
                f"{event['first_observable_timestamp_utc']}"
            )
            print(
                "FIRST OBSERVABLE TABLE      : "
                f"{event['first_observable_table']}"
            )
            print(
                "FIRST OBSERVABLE COLUMN     : "
                f"{event['first_observable_column']}"
            )
            print(
                "EXACT FIRST INSERTION POINT : "
                f"{event['exact_first_insertion_point']}"
            )

        print("=" * 90)
        print(
            "FORENSIC STATUS"
        )
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
            f"Artifact : "
            f"{OUTPUT_ARTIFACT}"
        )
        print(
            f"SHA256   : "
            f"{artifact_sha256}"
        )
        print("=" * 90)

    finally:
        conn.close()


if __name__ == "__main__":
    main()