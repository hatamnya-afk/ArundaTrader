import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


SCRIPT_VERSION = "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_MARKET_HISTORY_ALIGNMENT_FORENSIC_v0.2"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_MARKET_HISTORY_ALIGNMENT_FORENSIC_v0.2.json"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
RELATIONSHIP_CALCULATION = "NOT PERFORMED"


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_json(obj):
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(payload)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value.upper()


def normalize_symbol_set(values):
    result = set()

    for value in values:
        symbol = normalize_symbol(value)

        if symbol:
            result.add(symbol)

    return result


def extract_normalized_expected_universe(artifact):
    candidates = []

    direct = artifact.get("normalized_expected_universe")

    if isinstance(direct, list):
        candidates.append(
            (
                "normalized_expected_universe",
                direct,
            )
        )

    classification = artifact.get("classification")

    if isinstance(classification, dict):
        valid_symbols = classification.get("valid_symbol_candidates")

        if isinstance(valid_symbols, list):
            candidates.append(
                (
                    "classification.valid_symbol_candidates",
                    valid_symbols,
                )
            )

    candidates = [
        (
            path,
            normalize_symbol_set(symbols),
        )
        for path, symbols in candidates
    ]

    candidates = [
        (path, symbols)
        for path, symbols in candidates
        if symbols
    ]

    if not candidates:
        raise RuntimeError(
            "Normalized Expected Universe could not be resolved "
            "from normalization artifact."
        )

    candidates.sort(
        key=lambda item: (
            len(item[1]),
            item[0],
        ),
        reverse=True,
    )

    best_path, best_symbols = candidates[0]

    for path, symbols in candidates[1:]:
        if symbols != best_symbols:
            raise RuntimeError(
                "NORMALIZATION ARTIFACT CONTRACT INCOHERENT: "
                f"{best_path} != {path}"
            )

    return best_path, best_symbols, candidates


def get_table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def resolve_symbol_column(conn, table_name):
    columns = get_table_columns(
        conn,
        table_name,
    )

    preferred = [
        "symbol",
        "asset",
    ]

    for column in preferred:
        if column in columns:
            return column

    return None


def load_market_history_symbols(conn):
    table_name = "market_history"

    exists = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    if exists is None:
        raise RuntimeError(
            "market_history table not found."
        )

    symbol_column = resolve_symbol_column(
        conn,
        table_name,
    )

    if symbol_column is None:
        raise RuntimeError(
            "No symbol/asset column found in market_history."
        )

    rows = conn.execute(
        f'''
        SELECT DISTINCT "{symbol_column}"
        FROM "{table_name}"
        WHERE "{symbol_column}" IS NOT NULL
        '''
    ).fetchall()

    symbols = normalize_symbol_set(
        row[0]
        for row in rows
    )

    return symbol_column, symbols


def compare_sets(expected, observed):
    missing = sorted(
        expected - observed
    )

    extra = sorted(
        observed - expected
    )

    covered = expected & observed

    if expected:
        coverage = (
            len(covered)
            / len(expected)
            * 100.0
        )
    else:
        coverage = 0.0

    exact_match = (
        expected == observed
    )

    return {
        "expected_count": len(expected),
        "observed_count": len(observed),
        "covered_count": len(covered),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "missing_symbols": missing,
        "extra_symbols": extra,
        "coverage_pct": round(
            coverage,
            4,
        ),
        "exact_match": exact_match,
    }


def build_alignment_artifact(
    normalization_artifact,
    normalization_sha256,
    normalization_source_path,
    normalized_source_path,
    expected_symbols,
    market_history_symbols,
    market_history_symbol_column,
):
    comparison = compare_sets(
        expected_symbols,
        market_history_symbols,
    )

    expected_only = sorted(
        expected_symbols
        - market_history_symbols
    )

    history_only = sorted(
        market_history_symbols
        - expected_symbols
    )

    complete_containment = (
        len(expected_only) == 0
    )

    history_superset = (
        expected_symbols.issubset(
            market_history_symbols
        )
    )

    alignment_status = (
        "EXPECTED_UNIVERSE_FULLY_ALIGNED_WITH_MARKET_HISTORY"
        if complete_containment
        else
        "EXPECTED_UNIVERSE_HAS_MARKET_HISTORY_GAPS"
    )

    artifact = {
        "artifact": OUTPUT_PATH.name,
        "script_version": SCRIPT_VERSION,
        "generated_at_utc": utc_now(),

        "database": str(DB_PATH),

        "normalization_artifact": str(
            NORMALIZATION_PATH
        ),

        "normalization_artifact_sha256": (
            normalization_sha256
        ),

        "normalization_source_path": (
            normalized_source_path
        ),

        "mode": MODE,
        "network": NETWORK,
        "database_write": DATABASE_WRITE,
        "prediction": PREDICTION,
        "decision": DECISION,
        "outcome": OUTCOME,
        "relationship_calculation": (
            RELATIONSHIP_CALCULATION
        ),

        "expected_universe": {
            "source": (
                "NORMALIZATION_ARTIFACT"
            ),
            "source_path": normalized_source_path,
            "raw_count": normalization_artifact.get(
                "raw_candidate_count"
            ),
            "normalized_count": len(
                expected_symbols
            ),
            "symbols": sorted(
                expected_symbols
            ),
        },

        "market_history": {
            "table": "market_history",
            "symbol_column": (
                market_history_symbol_column
            ),
            "symbol_count": len(
                market_history_symbols
            ),
            "symbols": sorted(
                market_history_symbols
            ),
        },

        "alignment": {
            "expected_universe_count": len(
                expected_symbols
            ),
            "market_history_count": len(
                market_history_symbols
            ),

            "covered_expected_symbols": len(
                expected_symbols
                & market_history_symbols
            ),

            "missing_expected_symbols": len(
                expected_only
            ),

            "extra_market_history_symbols": len(
                history_only
            ),

            "coverage_pct": comparison[
                "coverage_pct"
            ],

            "expected_universe_contained": (
                complete_containment
            ),

            "market_history_is_superset": (
                history_superset
            ),

            "exact_match": comparison[
                "exact_match"
            ],

            "missing_symbols": expected_only,

            "extra_market_history_symbols_list": (
                history_only
            ),
        },

        "special_checks": {
            "normalized_expected_vs_market_history": {
                "expected": len(
                    expected_symbols
                ),
                "observed": len(
                    market_history_symbols
                ),
                "missing": expected_only,
                "extra": history_only,
                "complete_containment": (
                    complete_containment
                ),
            }
        },

        "forensic_status": alignment_status,

        "predictive_claim": (
            "NOT ESTABLISHED"
        ),

        "database_repair": (
            "NOT PERFORMED"
        ),
    }

    artifact["artifact_sha256"] = sha256_json(
        artifact
    )

    return artifact


def print_header():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> "
        "EXPECTED UNIVERSE MARKET HISTORY ALIGNMENT "
        "FORENSIC v0.2"
    )
    print("=" * 90)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Normalization   : {NORMALIZATION_PATH}"
    )

    print(
        f"Mode            : {MODE}"
    )

    print(
        f"Network         : {NETWORK}"
    )

    print(
        f"Database Write  : {DATABASE_WRITE}"
    )

    print(
        f"Prediction      : {PREDICTION}"
    )

    print(
        f"Decision        : {DECISION}"
    )

    print("-" * 90)


def print_comparison(comparison):
    print("=" * 90)
    print(
        "EXPECTED UNIVERSE -> MARKET HISTORY"
    )
    print("=" * 90)

    print(
        f"Expected symbols : "
        f"{comparison['expected_count']}"
    )

    print(
        f"Market History symbols : "
        f"{comparison['observed_count']}"
    )

    print(
        f"Covered symbols : "
        f"{comparison['covered_count']}"
    )

    print(
        f"Missing : "
        f"{comparison['missing_count']}"
    )

    if comparison["missing_symbols"]:
        print(
            "MISSING SYMBOLS : "
            + ", ".join(
                comparison["missing_symbols"]
            )
        )

    print(
        f"Extra : "
        f"{comparison['extra_count']}"
    )

    if comparison["extra_symbols"]:
        print(
            "EXTRA MARKET_HISTORY SYMBOLS : "
            + ", ".join(
                comparison["extra_symbols"]
            )
        )

    print(
        f"Coverage : "
        f"{comparison['coverage_pct']:.4f}%"
    )

    print(
        f"Exact Match : "
        f"{comparison['exact_match']}"
    )


def main():
    print_header()

    if not NORMALIZATION_PATH.exists():
        raise FileNotFoundError(
            f"Normalization artifact not found: "
            f"{NORMALIZATION_PATH}"
        )

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    normalization_artifact = load_json(
        NORMALIZATION_PATH
    )

    normalization_sha256 = sha256_json(
        normalization_artifact
    )

    print("=" * 90)
    print(
        "NORMALIZATION ARTIFACT CONTRACT INPUT"
    )
    print("=" * 90)

    print(
        f"Artifact : "
        f"{NORMALIZATION_PATH.name}"
    )

    print(
        f"Artifact SHA256 : "
        f"{normalization_sha256}"
    )

    (
        normalized_source_path,
        expected_symbols,
        candidates,
    ) = extract_normalized_expected_universe(
        normalization_artifact
    )

    print(
        f"Resolved source : "
        f"{normalized_source_path}"
    )

    print(
        f"Expected Universe : "
        f"{len(expected_symbols)}"
    )

    print("=" * 90)
    print(
        "CANDIDATE CROSS-CHECK"
    )
    print("=" * 90)

    for path, symbols in candidates:
        print("-" * 90)

        print(
            f"SOURCE : {path}"
        )

        print(
            f"SYMBOL COUNT : {len(symbols)}"
        )

        print(
            f"EXACT WITH BEST : "
            f"{symbols == expected_symbols}"
        )

    conn = sqlite3.connect(
        str(DB_PATH)
    )

    try:
        (
            market_history_symbol_column,
            market_history_symbols,
        ) = load_market_history_symbols(
            conn
        )
    finally:
        conn.close()

    comparison = compare_sets(
        expected_symbols,
        market_history_symbols,
    )

    print_comparison(
        comparison
    )

    print("=" * 90)
    print(
        "ALIGNMENT DECISION"
    )
    print("=" * 90)

    expected_contained = (
        len(
            expected_symbols
            - market_history_symbols
        )
        == 0
    )

    if expected_contained:
        print(
            "EXPECTED UNIVERSE FULLY PRESENT "
            "IN MARKET_HISTORY : True"
        )

        print(
            "MARKET_HISTORY GAP : 0"
        )

        print(
            "MARKET_HISTORY EXTRA SYMBOLS : "
            f"{len(market_history_symbols - expected_symbols)}"
        )

        if market_history_symbols - expected_symbols:
            print(
                "EXTRA SYMBOLS : "
                + ", ".join(
                    sorted(
                        market_history_symbols
                        - expected_symbols
                    )
                )
            )

        forensic_status = (
            "EXPECTED_UNIVERSE_FULLY_ALIGNED_WITH_MARKET_HISTORY"
        )

    else:
        print(
            "EXPECTED UNIVERSE FULLY PRESENT "
            "IN MARKET_HISTORY : False"
        )

        print(
            "MARKET_HISTORY GAP : "
            f"{len(expected_symbols - market_history_symbols)}"
        )

        forensic_status = (
            "EXPECTED_UNIVERSE_MARKET_HISTORY_GAP_DETECTED"
        )

    artifact = build_alignment_artifact(
        normalization_artifact=(
            normalization_artifact
        ),
        normalization_sha256=(
            normalization_sha256
        ),
        normalization_source_path=(
            NORMALIZATION_PATH
        ),
        normalized_source_path=(
            normalized_source_path
        ),
        expected_symbols=(
            expected_symbols
        ),
        market_history_symbols=(
            market_history_symbols
        ),
        market_history_symbol_column=(
            market_history_symbol_column
        ),
    )

    artifact[
        "forensic_status"
    ] = forensic_status

    artifact[
        "artifact_sha256"
    ] = sha256_json(
        artifact
    )

    with OUTPUT_PATH.open(
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

    final_sha256 = hashlib.sha256(
        OUTPUT_PATH.read_bytes()
    ).hexdigest()

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
        "RELATIONSHIP CALCULATION : "
        "NOT PERFORMED"
    )

    print(
        "DATABASE WRITE : NOT PERFORMED"
    )

    print(
        "DATABASE REPAIR : NOT PERFORMED"
    )

    print(
        f"Expected Universe : "
        f"{len(expected_symbols)}"
    )

    print(
        f"Market History : "
        f"{len(market_history_symbols)}"
    )

    print(
        f"Missing from History : "
        f"{len(expected_symbols - market_history_symbols)}"
    )

    print(
        f"Extra in History : "
        f"{len(market_history_symbols - expected_symbols)}"
    )

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256 : {final_sha256}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()