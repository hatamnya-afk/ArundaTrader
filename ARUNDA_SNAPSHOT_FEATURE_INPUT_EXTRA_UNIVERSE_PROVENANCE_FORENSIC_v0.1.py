import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# ARUNDA SNAPSHOT FEATURE INPUT EXTRA UNIVERSE PROVENANCE FORENSIC v0.1
# =============================================================================

SCRIPT_VERSION = "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

ALIGNMENT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_FEATURE_INPUT_ALIGNMENT_FORENSIC_v0.1.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"
RELATIONSHIP_CALCULATION = "NOT PERFORMED"


# =============================================================================
# HELPERS
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_symbol(value):
    if value is None:
        return None

    s = str(value).strip().upper()

    if not s:
        return None

    return s


def unique_symbols(values):
    result = set()

    for value in values:
        symbol = normalize_symbol(value)

        if symbol:
            result.add(symbol)

    return result


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_identifier(value):
    return str(value).replace('"', '""')


# =============================================================================
# DATABASE INVENTORY
# =============================================================================

def get_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def get_columns(conn, table):
    table_q = safe_identifier(table)

    rows = conn.execute(
        f'PRAGMA table_info("{table_q}")'
    ).fetchall()

    return [row[1] for row in rows]


def select_distinct_column(conn, table, column):
    table_q = safe_identifier(table)
    column_q = safe_identifier(column)

    try:
        rows = conn.execute(
            f'''
            SELECT DISTINCT "{column_q}"
            FROM "{table_q}"
            WHERE "{column_q}" IS NOT NULL
            '''
        ).fetchall()
    except sqlite3.Error:
        return set()

    return unique_symbols(row[0] for row in rows)


# =============================================================================
# KNOWN SYMBOL-COLUMN MAPPING
# =============================================================================

SYMBOL_COLUMN_CANDIDATES = {
    "market_history": ["symbol"],
    "market_history_legacy": ["symbol"],
    "market_microstructure": ["symbol"],
    "market_opportunity": ["symbol"],
    "market_state": ["symbol"],
    "market_technical": ["symbol"],
    "market_universe": ["symbol"],
    "market_data": ["symbol"],
    "market_records": ["asset", "symbol"],
    "fusion_signals": ["asset", "symbol"],
    "hunter_signals": ["asset", "symbol"],
    "market_news": ["symbol"],
    "market_news_intelligence": ["symbol"],
    "news_data": ["asset", "symbol"],
    "news_signals": ["asset", "symbol"],
    "opportunity_signals": ["asset", "symbol"],
    "positioning_data": ["symbol"],
    "risk_decisions": ["asset", "symbol"],
    "signal_outcomes": ["asset", "symbol"],
    "social_metrics": ["asset", "symbol"],
    "trade_decisions": ["asset", "symbol"],
    "trade_gate_decisions": ["asset", "symbol"],
    "market_whale": ["symbol"],
}


def inventory_database_symbols(conn):
    tables = get_tables(conn)

    inventory = {}

    for table in tables:
        candidates = SYMBOL_COLUMN_CANDIDATES.get(table, [])

        if not candidates:
            continue

        columns = set(get_columns(conn, table))

        selected_column = None

        for candidate in candidates:
            if candidate in columns:
                selected_column = candidate
                break

        if selected_column is None:
            continue

        symbols = select_distinct_column(
            conn,
            table,
            selected_column
        )

        inventory[table] = {
            "column": selected_column,
            "symbols": sorted(symbols),
            "count": len(symbols),
        }

    return inventory


# =============================================================================
# LOAD EXPECTED UNIVERSE
# =============================================================================

def resolve_expected_universe(normalization):
    candidates = [
        normalization.get("normalized_expected_universe"),
        normalization.get("classification", {}).get(
            "valid_symbol_candidates"
        ),
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            symbols = unique_symbols(candidate)

            if symbols:
                return symbols

    return set()


# =============================================================================
# LOAD FEATURE INPUT ALIGNMENT
# =============================================================================

def resolve_feature_input_source(alignment):
    """
    The previous forensic artifact identifies the primary feature input
    source as MARKET_HISTORY.

    This function attempts to recover that source without trusting a
    hard-coded symbol list.
    """

    expected = resolve_first_list(
        alignment,
        [
            ("primary_feature_input", "source"),
            ("primary_feature_input", "feature_input_source"),
            ("feature_input_decision", "source"),
        ],
    )

    if expected:
        return str(expected)

    return "DATABASE_TABLE:market_history:symbol"


def resolve_first_list(root, paths):
    for path in paths:
        node = root

        valid = True

        for key in path:
            if not isinstance(node, dict) or key not in node:
                valid = False
                break

            node = node[key]

        if valid and isinstance(node, list):
            return node

    return None


# =============================================================================
# PROVENANCE
# =============================================================================

def build_provenance(extra_symbols, inventory):
    provenance = {}

    for symbol in sorted(extra_symbols):

        evidence_sources = []
        evidence_tables = []

        for table, data in inventory.items():

            symbols = set(data.get("symbols", []))

            if symbol in symbols:

                column = data.get("column")

                source = (
                    f"DATABASE_TABLE:{table}:{str(column).upper()}"
                )

                evidence_sources.append(source)
                evidence_tables.append(table)

        provenance[symbol] = {
            "evidence_sources": sorted(set(evidence_sources)),
            "evidence_table_count": len(set(evidence_tables)),
            "evidence_tables": sorted(set(evidence_tables)),
            "database_present": bool(evidence_sources),
        }

    return provenance


# =============================================================================
# SPECIAL CONTAMINATION CHECKS
# =============================================================================

KNOWN_CONTAMINATION = {
    "0.25",
    "1.0",
    "BTCUSDT_PERP.A",
    "CRYPTO",
}

KNOWN_NON_UNIVERSE_ARTIFACT_SYMBOLS = {
    "ASSET",
}


def classify_extra_symbols(extra_symbols):
    known_contamination = sorted(
        extra_symbols.intersection(KNOWN_CONTAMINATION)
    )

    known_artifact_symbols = sorted(
        extra_symbols.intersection(KNOWN_NON_UNIVERSE_ARTIFACT_SYMBOLS)
    )

    numeric_symbols = sorted(
        s for s in extra_symbols
        if _is_numeric_symbol(s)
    )

    return {
        "known_contamination": known_contamination,
        "known_artifact_symbols": known_artifact_symbols,
        "numeric_symbols": numeric_symbols,
    }


def _is_numeric_symbol(symbol):
    try:
        float(symbol)
        return True
    except (TypeError, ValueError):
        return False


# =============================================================================
# CROSS SOURCE EXTRA ANALYSIS
# =============================================================================

def source_presence_for_extras(extra_symbols, inventory):
    result = {}

    for table, data in inventory.items():

        source_symbols = set(data.get("symbols", []))

        intersection = extra_symbols.intersection(source_symbols)

        result[table] = {
            "column": data.get("column"),
            "extra_symbol_count": len(intersection),
            "extra_symbols": sorted(intersection),
            "contains_any_extra": bool(intersection),
        }

    return result


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE INPUT -> EXTRA UNIVERSE "
        "PROVENANCE FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database        : {DB_PATH}")
    print(f"Normalization   : {NORMALIZATION_PATH}")
    print(f"Alignment       : {ALIGNMENT_PATH}")
    print(f"Mode            : {MODE}")
    print(f"Network         : {NETWORK}")
    print(f"Database Write  : {DATABASE_WRITE}")
    print(f"Prediction      : {PREDICTION}")
    print(f"Decision        : {DECISION}")

    print("-" * 90)

    # -------------------------------------------------------------------------
    # FILE VALIDATION
    # -------------------------------------------------------------------------

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if not NORMALIZATION_PATH.exists():
        raise FileNotFoundError(
            f"Normalization artifact not found: {NORMALIZATION_PATH}"
        )

    if not ALIGNMENT_PATH.exists():
        raise FileNotFoundError(
            f"Alignment artifact not found: {ALIGNMENT_PATH}"
        )

    normalization = load_json(NORMALIZATION_PATH)
    alignment = load_json(ALIGNMENT_PATH)

    normalization_sha256 = sha256_file(NORMALIZATION_PATH)
    alignment_sha256 = sha256_file(ALIGNMENT_PATH)

    # -------------------------------------------------------------------------
    # EXPECTED UNIVERSE
    # -------------------------------------------------------------------------

    expected_universe = resolve_expected_universe(normalization)

    if not expected_universe:
        raise RuntimeError(
            "EXPECTED UNIVERSE COULD NOT BE RESOLVED FROM NORMALIZATION ARTIFACT"
        )

    print("=" * 90)
    print("EXPECTED UNIVERSE")
    print("=" * 90)

    print(
        f"Normalization Artifact SHA256 : {normalization_sha256}"
    )
    print(
        f"Expected Universe              : {len(expected_universe)}"
    )

    # -------------------------------------------------------------------------
    # DATABASE READ ONLY
    # -------------------------------------------------------------------------

    conn = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:

        inventory = inventory_database_symbols(conn)

    finally:
        conn.close()

    # -------------------------------------------------------------------------
    # PRIMARY FEATURE INPUT
    # -------------------------------------------------------------------------

    market_history_symbols = set()

    if "market_history" in inventory:
        market_history_symbols = set(
            inventory["market_history"]["symbols"]
        )

    covered = expected_universe.intersection(
        market_history_symbols
    )

    extra = market_history_symbols - expected_universe
    missing = expected_universe - market_history_symbols

    coverage = (
        len(covered) / len(expected_universe) * 100
        if expected_universe
        else 0.0
    )

    print("=" * 90)
    print("PRIMARY FEATURE INPUT EXTRA UNIVERSE")
    print("=" * 90)

    print(
        f"Expected Universe : {len(expected_universe)}"
    )

    print(
        f"Feature Input     : {len(market_history_symbols)}"
    )

    print(
        f"Covered           : {len(covered)}"
    )

    print(
        f"Missing           : {len(missing)}"
    )

    print(
        f"Extra             : {len(extra)}"
    )

    print(
        f"Coverage          : {coverage:.4f}%"
    )

    print(
        f"Exact Match       : {not missing and not extra}"
    )

    # -------------------------------------------------------------------------
    # EXTRA SYMBOLS
    # -------------------------------------------------------------------------

    print("=" * 90)
    print("EXTRA FEATURE INPUT SYMBOLS")
    print("=" * 90)

    if extra:
        print(
            "EXTRA SYMBOLS : "
            + ", ".join(sorted(extra))
        )
    else:
        print("EXTRA SYMBOLS : NONE")

    # -------------------------------------------------------------------------
    # EXTRA CLASSIFICATION
    # -------------------------------------------------------------------------

    classification = classify_extra_symbols(extra)

    print("=" * 90)
    print("EXTRA SYMBOL CLASSIFICATION")
    print("=" * 90)

    print(
        f"Known contamination candidates : "
        f"{len(classification['known_contamination'])}"
    )

    if classification["known_contamination"]:
        print(
            "KNOWN CONTAMINATION : "
            + ", ".join(
                classification["known_contamination"]
            )
        )

    print(
        f"Known artifact candidates      : "
        f"{len(classification['known_artifact_symbols'])}"
    )

    if classification["known_artifact_symbols"]:
        print(
            "KNOWN ARTIFACT SYMBOLS : "
            + ", ".join(
                classification["known_artifact_symbols"]
            )
        )

    print(
        f"Numeric symbols                : "
        f"{len(classification['numeric_symbols'])}"
    )

    if classification["numeric_symbols"]:
        print(
            "NUMERIC SYMBOLS : "
            + ", ".join(
                classification["numeric_symbols"]
            )
        )

    # -------------------------------------------------------------------------
    # DATABASE PROVENANCE
    # -------------------------------------------------------------------------

    provenance = build_provenance(
        extra,
        inventory
    )

    print("=" * 90)
    print("EXTRA SYMBOL DATABASE PROVENANCE")
    print("=" * 90)

    for symbol in sorted(extra):

        record = provenance.get(symbol, {})

        sources = record.get(
            "evidence_sources",
            []
        )

        print("-" * 90)
        print(f"SYMBOL : {symbol}")
        print(
            f"EVIDENCE SOURCE COUNT : {len(sources)}"
        )

        if sources:
            for source in sources:
                print(
                    f"  {source}"
                )
        else:
            print(
                "  NO DATABASE EVIDENCE"
            )

    # -------------------------------------------------------------------------
    # CROSS SOURCE PRESENCE
    # -------------------------------------------------------------------------

    cross_source = source_presence_for_extras(
        extra,
        inventory
    )

    print("=" * 90)
    print("CROSS-SOURCE EXTRA PRESENCE")
    print("=" * 90)

    for table in sorted(cross_source):

        data = cross_source[table]

        if not data["contains_any_extra"]:
            continue

        print("-" * 90)
        print(
            f"SOURCE : DATABASE_TABLE:{table}:"
            f"{str(data['column']).upper()}"
        )

        print(
            f"EXTRA SYMBOL COUNT : "
            f"{data['extra_symbol_count']}"
        )

        print(
            "EXTRA SYMBOLS : "
            + ", ".join(
                data["extra_symbols"]
            )
        )

    # -------------------------------------------------------------------------
    # PROVENANCE GROUPING
    # -------------------------------------------------------------------------

    provenance_groups = {}

    for symbol, data in provenance.items():

        key = tuple(
            data.get("evidence_sources", [])
        )

        provenance_groups.setdefault(
            key,
            []
        ).append(symbol)

    provenance_group_records = []

    for sources, symbols in sorted(
        provenance_groups.items(),
        key=lambda item: (
            -len(item[1]),
            item[0]
        )
    ):

        provenance_group_records.append(
            {
                "evidence_sources": list(sources),
                "symbol_count": len(symbols),
                "symbols": sorted(symbols),
            }
        )

    # -------------------------------------------------------------------------
    # FORENSIC DECISION
    # -------------------------------------------------------------------------

    if not extra:
        forensic_status = (
            "NO_EXTRA_FEATURE_INPUT_UNIVERSE"
        )

    elif classification["known_contamination"]:
        forensic_status = (
            "EXTRA_FEATURE_INPUT_KNOWN_CONTAMINATION_PRESENT"
        )

    elif classification["known_artifact_symbols"]:
        forensic_status = (
            "EXTRA_FEATURE_INPUT_ARTIFACT_SYMBOLS_PRESENT"
        )

    elif all(
        provenance[symbol]["database_present"]
        for symbol in extra
    ):
        forensic_status = (
            "EXTRA_FEATURE_INPUT_DATABASE_PROVENANCE_ESTABLISHED"
        )

    else:
        forensic_status = (
            "EXTRA_FEATURE_INPUT_PROVENANCE_PARTIALLY_UNRESOLVED"
        )

    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)

    print(
        f"FORENSIC STATUS : {forensic_status}"
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

    # -------------------------------------------------------------------------
    # ARTIFACT
    # -------------------------------------------------------------------------

    artifact = {
        "script_version": SCRIPT_VERSION,
        "generated_at_utc": utc_now(),

        "database": str(DB_PATH),

        "mode": MODE,
        "network": NETWORK,
        "database_write": DATABASE_WRITE,
        "prediction": PREDICTION,
        "decision": DECISION,

        "normalization_artifact": {
            "path": str(NORMALIZATION_PATH),
            "sha256": normalization_sha256,
            "resolved_source": (
                "normalized_expected_universe"
            ),
        },

        "feature_input_alignment_artifact": {
            "path": str(ALIGNMENT_PATH),
            "sha256": alignment_sha256,
        },

        "expected_universe": {
            "count": len(expected_universe),
            "symbols": sorted(expected_universe),
        },

        "primary_feature_input": {
            "source": "DATABASE_TABLE:market_history:symbol",
            "count": len(market_history_symbols),
            "symbols": sorted(market_history_symbols),
        },

        "extra_universe": {
            "count": len(extra),
            "symbols": sorted(extra),
        },

        "missing_from_feature_input": {
            "count": len(missing),
            "symbols": sorted(missing),
        },

        "coverage": {
            "expected_count": len(expected_universe),
            "covered_count": len(covered),
            "missing_count": len(missing),
            "extra_count": len(extra),
            "coverage_percent": round(
                coverage,
                4
            ),
            "exact_match": (
                not missing and not extra
            ),
        },

        "extra_classification": classification,

        "symbol_provenance": provenance,

        "provenance_groups": provenance_group_records,

        "cross_source_extra_presence": cross_source,

        "feature_input_decision": {
            "expected_universe_fully_available": (
                len(missing) == 0
            ),
            "feature_input_gap": len(missing),
            "feature_input_extra_symbols": len(extra),
        },

        "forensic_constraints": {
            "network_forbidden": True,
            "database_write_forbidden": True,
            "prediction_forbidden": True,
            "decision_forbidden": True,
            "database_repair_performed": False,
            "relationship_calculation_performed": False,
        },

        "forensic_status": forensic_status,

        "predictive_claim": (
            "NOT ESTABLISHED"
        ),

        "relationship_calculation": (
            "NOT PERFORMED"
        ),

        "database_repair": (
            "NOT PERFORMED"
        ),

        "outcome": (
            "EXTRA FEATURE INPUT UNIVERSE "
            "WAS FORENSICALLY INVENTORIED "
            "AND DATABASE PROVENANCE WAS CHECKED"
        ),
    }

    # -------------------------------------------------------------------------
    # CANONICAL JSON + SHA256
    # -------------------------------------------------------------------------

    payload_without_hash = json.dumps(
        artifact,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")

    artifact_sha256 = sha256_bytes(
        payload_without_hash
    )

    artifact["artifact_sha256"] = artifact_sha256

    final_payload = json.dumps(
        artifact,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    OUTPUT_PATH.write_text(
        final_payload,
        encoding="utf-8"
    )

    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256   : {sha256_file(OUTPUT_PATH)}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()