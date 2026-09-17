import os
import json
import sqlite3
import hashlib
import math
from datetime import datetime, timezone


DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

FEATURE_CONTRACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

SOURCE_FORENSIC_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_SOURCE_SYMBOL_INPUT_FORENSIC_v0.1.json"
)

PROVENANCE_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

ARTIFACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"
DATABASE_WRITE = "NOT PERFORMED"


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_json(value):
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256_text(payload)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value.upper()


def is_numeric_symbol(value):
    if value is None:
        return False

    try:
        float(value)
        return True
    except Exception:
        return False


def looks_like_derivative_symbol(value):
    if value is None:
        return False

    upper = value.upper()

    derivative_tokens = (
        "USDT_PERP",
        "PERP.",
        "_PERP",
        "PERPETUAL",
    )

    return any(token in upper for token in derivative_tokens)


def looks_like_non_asset_label(value):
    if value is None:
        return False

    upper = value.upper()

    labels = {
        "CRYPTO",
        "ASSET",
        "UNKNOWN",
        "NONE",
        "NULL",
        "N/A",
        "NA",
        "TOTAL",
        "ALL",
    }

    return upper in labels


def classify_symbol(symbol):
    if symbol is None:
        return "NULL"

    value = normalize_symbol(symbol)

    if value is None:
        return "EMPTY"

    if is_numeric_symbol(value):
        return "NUMERIC_VALUE"

    if looks_like_derivative_symbol(value):
        return "DERIVATIVE_INSTRUMENT"

    if looks_like_non_asset_label(value):
        return "NON_ASSET_LABEL"

    return "SYMBOL_CANDIDATE"


def discover_table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def load_distinct_column_symbols(conn, table_name, column_name):
    if not table_exists(conn, table_name):
        return set()

    columns = discover_table_columns(conn, table_name)

    if column_name not in columns:
        return set()

    rows = conn.execute(
        f'''
        SELECT DISTINCT "{column_name}"
        FROM "{table_name}"
        WHERE "{column_name}" IS NOT NULL
        '''
    ).fetchall()

    result = set()

    for row in rows:
        symbol = normalize_symbol(row[0])

        if symbol:
            result.add(symbol)

    return result


def extract_symbols_from_source_forensic(payload):
    symbols = set()

    possible_keys = (
        "feature_symbols",
        "symbols",
        "established_symbols",
        "source_symbols",
        "symbol_universe",
        "expected_symbols",
    )

    def recursive_extract(value):
        if isinstance(value, dict):
            for key, item in value.items():
                key_lower = str(key).lower()

                if key_lower in possible_keys:
                    if isinstance(item, list):
                        for element in item:
                            if isinstance(element, str):
                                symbol = normalize_symbol(element)
                                if symbol:
                                    symbols.add(symbol)

                recursive_extract(item)

        elif isinstance(value, list):
            for item in value:
                recursive_extract(item)

    recursive_extract(payload)

    return symbols


def extract_symbols_from_provenance(payload):
    symbols = set()

    possible_keys = (
        "expected_symbols",
        "expected_universe",
        "resolved_symbols",
        "source_symbols",
    )

    def recursive_extract(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in possible_keys:
                    if isinstance(item, list):
                        for element in item:
                            if isinstance(element, str):
                                symbol = normalize_symbol(element)
                                if symbol:
                                    symbols.add(symbol)

                    elif isinstance(item, dict):
                        for element in item.values():
                            if isinstance(element, str):
                                symbol = normalize_symbol(element)
                                if symbol:
                                    symbols.add(symbol)

                recursive_extract(item)

        elif isinstance(value, list):
            for item in value:
                recursive_extract(item)

    recursive_extract(payload)

    return symbols


def build_classification(symbols):
    classification = {}

    for symbol in sorted(symbols):
        classification[symbol] = classify_symbol(symbol)

    return classification


def split_universe(symbols):
    valid = set()
    numeric = set()
    derivative = set()
    labels = set()
    empty = set()

    for symbol in symbols:
        classification = classify_symbol(symbol)

        if classification == "SYMBOL_CANDIDATE":
            valid.add(symbol)

        elif classification == "NUMERIC_VALUE":
            numeric.add(symbol)

        elif classification == "DERIVATIVE_INSTRUMENT":
            derivative.add(symbol)

        elif classification == "NON_ASSET_LABEL":
            labels.add(symbol)

        elif classification == "EMPTY":
            empty.add(symbol)

    return {
        "valid_symbol_candidates": valid,
        "numeric_values": numeric,
        "derivative_instruments": derivative,
        "non_asset_labels": labels,
        "empty_values": empty,
    }


def compare_sets(left, right):
    intersection = left & right
    missing = left - right
    extra = right - left

    coverage = (
        (len(intersection) / len(left) * 100.0)
        if left
        else 0.0
    )

    return {
        "left_count": len(left),
        "right_count": len(right),
        "intersection_count": len(intersection),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "coverage_pct": round(coverage, 4),
        "exact_match": left == right,
        "missing": sorted(missing),
        "extra": sorted(extra),
    }


def print_section(title):
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_set(label, values):
    print(f"{label} : {len(values)}")

    if values:
        print(
            "  " + ", ".join(sorted(values))
        )


def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> EXPECTED UNIVERSE "
        "NORMALIZATION FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database              : {DB_PATH}")
    print(f"Feature Contract      : {FEATURE_CONTRACT_PATH}")
    print(f"Source Forensic       : {SOURCE_FORENSIC_PATH}")
    print(f"Provenance Forensic   : {PROVENANCE_PATH}")
    print(f"Mode                  : {MODE}")
    print(f"Network               : {NETWORK}")
    print(f"Outcome               : {OUTCOME}")
    print(f"Prediction            : {PREDICTION}")
    print(f"Decision              : {DECISION}")
    print(f"Database Write        : {DATABASE_WRITE}")
    print("-" * 90)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)

    if not os.path.exists(SOURCE_FORENSIC_PATH):
        raise FileNotFoundError(SOURCE_FORENSIC_PATH)

    source_forensic = load_json(
        SOURCE_FORENSIC_PATH
    )

    provenance = None

    if os.path.exists(PROVENANCE_PATH):
        provenance = load_json(
            PROVENANCE_PATH
        )

    feature_contract = None

    if os.path.exists(FEATURE_CONTRACT_PATH):
        feature_contract = load_json(
            FEATURE_CONTRACT_PATH
        )

    source_symbols = extract_symbols_from_source_forensic(
        source_forensic
    )

    provenance_symbols = set()

    if provenance is not None:
        provenance_symbols = extract_symbols_from_provenance(
            provenance
        )

    if provenance_symbols:
        candidate_symbols = provenance_symbols
        candidate_source = "PROVENANCE_FORENSIC"
    else:
        candidate_symbols = source_symbols
        candidate_source = "SOURCE_FORENSIC"

    print_section("RAW EXPECTED UNIVERSE CANDIDATE")

    print(
        f"Candidate source : {candidate_source}"
    )

    print(
        f"Raw symbol count  : {len(candidate_symbols)}"
    )

    print_set(
        "Raw symbols",
        candidate_symbols,
    )

    split = split_universe(
        candidate_symbols
    )

    valid_symbols = split[
        "valid_symbol_candidates"
    ]

    numeric_values = split[
        "numeric_values"
    ]

    derivative_instruments = split[
        "derivative_instruments"
    ]

    non_asset_labels = split[
        "non_asset_labels"
    ]

    empty_values = split[
        "empty_values"
    ]

    print_section("SYMBOL CLASSIFICATION")

    print_set(
        "VALID SYMBOL CANDIDATES",
        valid_symbols,
    )

    print_set(
        "NUMERIC VALUES",
        numeric_values,
    )

    print_set(
        "DERIVATIVE INSTRUMENTS",
        derivative_instruments,
    )

    print_set(
        "NON-ASSET LABELS",
        non_asset_labels,
    )

    print_set(
        "EMPTY VALUES",
        empty_values,
    )

    normalized_universe = set(valid_symbols)

    excluded_symbols = (
        numeric_values
        | derivative_instruments
        | non_asset_labels
        | empty_values
    )

    print_section("NORMALIZED EXPECTED UNIVERSE")

    print(
        f"Raw Universe Count        : "
        f"{len(candidate_symbols)}"
    )

    print(
        f"Normalized Universe Count : "
        f"{len(normalized_universe)}"
    )

    print(
        f"Excluded Count            : "
        f"{len(excluded_symbols)}"
    )

    print_set(
        "Excluded Symbols",
        excluded_symbols,
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:
        market_history = load_distinct_column_symbols(
            conn,
            "market_history",
            "symbol",
        )

        market_data = load_distinct_column_symbols(
            conn,
            "market_data",
            "symbol",
        )

        market_universe = load_distinct_column_symbols(
            conn,
            "market_universe",
            "symbol",
        )

        market_records = load_distinct_column_symbols(
            conn,
            "market_records",
            "asset",
        )

    finally:
        conn.close()

    print_section("DATABASE COMPARISON")

    comparisons = {
        "MARKET_HISTORY": compare_sets(
            normalized_universe,
            market_history,
        ),
        "MARKET_DATA": compare_sets(
            normalized_universe,
            market_data,
        ),
        "MARKET_UNIVERSE": compare_sets(
            normalized_universe,
            market_universe,
        ),
        "MARKET_RECORDS": compare_sets(
            normalized_universe,
            market_records,
        ),
    }

    for name, result in comparisons.items():
        print("-" * 90)

        print(
            f"SOURCE : {name}"
        )

        print(
            f"EXPECTED SYMBOLS : "
            f"{result['left_count']}"
        )

        print(
            f"COVERED SYMBOLS : "
            f"{result['intersection_count']}"
        )

        print(
            f"MISSING : "
            f"{result['missing_count']}"
        )

        print(
            f"EXTRA : "
            f"{result['extra_count']}"
        )

        print(
            f"COVERAGE : "
            f"{result['coverage_pct']:.4f}%"
        )

        print(
            f"EXACT MATCH : "
            f"{result['exact_match']}"
        )

        if result["missing"]:
            print(
                "MISSING SYMBOLS : "
                + ", ".join(result["missing"])
            )

        if result["extra"]:
            print(
                "EXTRA SYMBOLS : "
                + ", ".join(result["extra"])
            )

    print_section("SPECIAL FORENSIC CHECKS")

    raw_vs_normalized = compare_sets(
        candidate_symbols,
        normalized_universe,
    )

    print("-" * 90)
    print("RAW UNIVERSE -> NORMALIZED UNIVERSE")

    print(
        f"Raw : {raw_vs_normalized['left_count']}"
    )

    print(
        f"Normalized : "
        f"{raw_vs_normalized['right_count']}"
    )

    print(
        f"Excluded : "
        f"{len(excluded_symbols)}"
    )

    print(
        f"Normalization changed universe : "
        f"{not raw_vs_normalized['exact_match']}"
    )

    print("-" * 90)
    print("KNOWN CONTAMINATION CHECK")

    known_contamination = {
        "0.25",
        "1.0",
        "BTCUSDT_PERP.A",
        "CRYPTO",
    }

    found_known_contamination = (
        candidate_symbols
        & known_contamination
    )

    print(
        f"Known contamination candidates : "
        f"{len(found_known_contamination)}"
    )

    print_set(
        "FOUND",
        found_known_contamination,
    )

    print("-" * 90)
    print("MARKET_HISTORY GAP CHECK")

    history_gap = (
        normalized_universe
        - market_history
    )

    print(
        f"Normalized Universe : "
        f"{len(normalized_universe)}"
    )

    print(
        f"Market History      : "
        f"{len(market_history)}"
    )

    print(
        f"Missing from History : "
        f"{len(history_gap)}"
    )

    if history_gap:
        print(
            "MISSING SYMBOLS : "
            + ", ".join(sorted(history_gap))
        )

    print_section("NORMALIZATION DECISION")

    if len(excluded_symbols) > 0:
        normalization_status = (
            "CONTAMINATED_SOURCE_DETECTED"
        )
    else:
        normalization_status = (
            "NO_SOURCE_CONTAMINATION_DETECTED"
        )

    if (
        len(normalized_universe) == len(market_history)
        and normalized_universe == market_history
    ):
        history_alignment = (
            "NORMALIZED_UNIVERSE_EXACTLY_ALIGNS_WITH_MARKET_HISTORY"
        )
    else:
        history_alignment = (
            "NORMALIZED_UNIVERSE_DOES_NOT_EXACTLY_ALIGN_WITH_MARKET_HISTORY"
        )

    print(
        f"NORMALIZATION STATUS : "
        f"{normalization_status}"
    )

    print(
        f"HISTORY ALIGNMENT : "
        f"{history_alignment}"
    )

    print(
        "DATABASE REPAIR : NOT PERFORMED"
    )

    print(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    print(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )

    artifact = {
        "artifact": {
            "name": (
                "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_"
                "NORMALIZATION_FORENSIC_v0.1"
            ),
            "version": "v0.1",
            "created_at_utc": utc_now(),
            "database": DB_PATH,
            "feature_contract": FEATURE_CONTRACT_PATH,
            "source_forensic": SOURCE_FORENSIC_PATH,
            "provenance_forensic": PROVENANCE_PATH,
            "mode": MODE,
            "network": NETWORK,
            "outcome": OUTCOME,
            "prediction": PREDICTION,
            "decision": DECISION,
            "database_write": DATABASE_WRITE,
        },
        "candidate_source": candidate_source,
        "raw_candidate_universe": sorted(
            candidate_symbols
        ),
        "raw_candidate_count": len(
            candidate_symbols
        ),
        "classification": {
            "valid_symbol_candidates": sorted(
                valid_symbols
            ),
            "numeric_values": sorted(
                numeric_values
            ),
            "derivative_instruments": sorted(
                derivative_instruments
            ),
            "non_asset_labels": sorted(
                non_asset_labels
            ),
            "empty_values": sorted(
                empty_values
            ),
        },
        "normalized_expected_universe": sorted(
            normalized_universe
        ),
        "normalized_expected_count": len(
            normalized_universe
        ),
        "excluded_symbols": sorted(
            excluded_symbols
        ),
        "excluded_count": len(
            excluded_symbols
        ),
        "known_contamination_detected": sorted(
            found_known_contamination
        ),
        "database_comparison": comparisons,
        "history_gap": sorted(
            history_gap
        ),
        "normalization_status": normalization_status,
        "history_alignment": history_alignment,
        "forensic_constraints": {
            "database_write": False,
            "prediction": False,
            "outcome": False,
            "decision": False,
            "network": False,
            "repair": False,
        },
    }

    artifact["artifact_sha256"] = sha256_json(
        artifact
    )

    save_json(
        ARTIFACT_PATH,
        artifact,
    )

    print_section("FORENSIC STATUS")

    if found_known_contamination:
        status = (
            "EXPECTED_UNIVERSE_SOURCE_CONTAMINATION_DETECTED"
        )
    else:
        status = (
            "EXPECTED_UNIVERSE_NORMALIZATION_CLEAN"
        )

    print(
        f"FORENSIC STATUS : {status}"
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
        f"Raw Expected Universe : "
        f"{len(candidate_symbols)}"
    )

    print(
        f"Normalized Expected Universe : "
        f"{len(normalized_universe)}"
    )

    print(
        f"Excluded / Contaminated : "
        f"{len(excluded_symbols)}"
    )

    print(
        f"Market History : "
        f"{len(market_history)}"
    )

    print(
        f"Market Data : "
        f"{len(market_data)}"
    )

    print(
        f"Artifact : {ARTIFACT_PATH}"
    )

    print(
        f"SHA256   : "
        f"{artifact['artifact_sha256']}"
    )


if __name__ == "__main__":
    main()