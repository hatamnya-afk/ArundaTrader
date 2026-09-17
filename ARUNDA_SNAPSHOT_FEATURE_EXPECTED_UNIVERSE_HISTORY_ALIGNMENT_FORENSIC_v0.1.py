import os
import json
import hashlib
import sqlite3
from datetime import datetime, timezone


DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

SOURCE_FORENSIC_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_SOURCE_SYMBOL_INPUT_FORENSIC_v0.1.json"
)

EXPECTED_UNIVERSE_RESOLUTION_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_RESOLUTION_FORENSIC_v0.1.json"
)

NORMALIZATION_FORENSIC_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

OUTPUT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_HISTORY_ALIGNMENT_FORENSIC_v0.1.json"
)

FEATURE_CONTRACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)


FORBIDDEN_CONTAMINATION = {
    "0.25",
    "1.0",
    "BTCUSDT_PERP.A",
    "CRYPTO",
    "4",
    "ASSET",
}


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_file(path):
    if not os.path.exists(path):
        return None

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_json(path):
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value.upper()


def table_exists(conn, table_name):
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    )

    return cursor.fetchone() is not None


def get_table_columns(conn, table_name):
    cursor = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    return [
        row[1]
        for row in cursor.fetchall()
    ]


def load_symbol_column(conn, table_name, column_name):
    if not table_exists(conn, table_name):
        return set()

    columns = get_table_columns(conn, table_name)

    if column_name not in columns:
        return set()

    cursor = conn.execute(
        f"""
        SELECT DISTINCT "{column_name}"
        FROM "{table_name}"
        WHERE "{column_name}" IS NOT NULL
        """
    )

    result = set()

    for row in cursor.fetchall():
        symbol = normalize_symbol(row[0])

        if symbol:
            result.add(symbol)

    return result


def resolve_expected_universe():
    candidates = []

    resolution = load_json(
        EXPECTED_UNIVERSE_RESOLUTION_PATH
    )

    normalization = load_json(
        NORMALIZATION_FORENSIC_PATH
    )

    source_forensic = load_json(
        SOURCE_FORENSIC_PATH
    )

    if isinstance(normalization, dict):
        normalized = normalization.get(
            "normalized_universe"
        )

        if isinstance(normalized, list):
            candidates.append(
                (
                    "NORMALIZATION_FORENSIC",
                    {
                        normalize_symbol(x)
                        for x in normalized
                        if normalize_symbol(x)
                    },
                )
            )

    if isinstance(resolution, dict):
        for key in (
            "expected_universe",
            "resolved_universe",
            "symbols",
        ):
            value = resolution.get(key)

            if isinstance(value, list):
                candidates.append(
                    (
                        "RESOLUTION_FORENSIC",
                        {
                            normalize_symbol(x)
                            for x in value
                            if normalize_symbol(x)
                        },
                    )
                )

    if isinstance(source_forensic, dict):
        for key in (
            "feature_symbols",
            "symbols",
            "established_symbols",
        ):
            value = source_forensic.get(key)

            if isinstance(value, list):
                candidates.append(
                    (
                        "SOURCE_FORENSIC",
                        {
                            normalize_symbol(x)
                            for x in value
                            if normalize_symbol(x)
                        },
                    )
                )

    candidates = [
        (name, symbols)
        for name, symbols in candidates
        if symbols
    ]

    if not candidates:
        return None, set()

    normalized_candidates = []

    for name, symbols in candidates:
        cleaned = {
            symbol
            for symbol in symbols
            if symbol not in FORBIDDEN_CONTAMINATION
        }

        normalized_candidates.append(
            (
                name,
                cleaned,
            )
        )

    normalized_candidates.sort(
        key=lambda x: len(x[1]),
        reverse=True,
    )

    return normalized_candidates[0]


def build_alignment(expected, history):
    missing = sorted(
        expected - history
    )

    extra = sorted(
        history - expected
    )

    intersection = sorted(
        expected & history
    )

    coverage = (
        len(intersection) / len(expected) * 100.0
        if expected
        else 0.0
    )

    exact_match = (
        expected == history
    )

    return {
        "expected_count": len(expected),
        "history_count": len(history),
        "intersection_count": len(intersection),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "coverage_percent": round(
            coverage,
            4,
        ),
        "exact_match": exact_match,
        "missing_symbols": missing,
        "extra_symbols": extra,
        "intersection_symbols": intersection,
    }


def classify_extra_history(extra):
    classification = {}

    for symbol in extra:
        if symbol in FORBIDDEN_CONTAMINATION:
            classification[symbol] = (
                "KNOWN_CONTAMINATION_CANDIDATE"
            )
        else:
            classification[symbol] = (
                "UNRESOLVED_HISTORY_EXTRA"
            )

    return classification


def classify_missing_history(missing):
    classification = {}

    for symbol in missing:
        if symbol in FORBIDDEN_CONTAMINATION:
            classification[symbol] = (
                "KNOWN_CONTAMINATION_CANDIDATE"
            )
        else:
            classification[symbol] = (
                "UNRESOLVED_EXPECTED_SYMBOL"
            )

    return classification


def get_symbol_evidence(conn, symbol):
    evidence = []

    tables = [
        ("market_universe", "symbol"),
        ("market_history", "symbol"),
        ("market_history_legacy", "symbol"),
        ("market_microstructure", "symbol"),
        ("market_opportunity", "symbol"),
        ("market_state", "symbol"),
        ("market_technical", "symbol"),
        ("market_records", "asset"),
        ("market_data", "symbol"),
        ("hunter_signals", "asset"),
        ("news_data", "asset"),
        ("news_signals", "asset"),
        ("fusion_signals", "asset"),
        ("market_news", "symbol"),
        ("market_news_intelligence", "symbol"),
        ("signal_outcomes", "asset"),
        ("opportunity_signals", "asset"),
        ("risk_decisions", "asset"),
        ("trade_decisions", "asset"),
        ("trade_gate_decisions", "asset"),
        ("positioning_data", "symbol"),
    ]

    for table_name, column_name in tables:
        if not table_exists(conn, table_name):
            continue

        columns = get_table_columns(
            conn,
            table_name,
        )

        if column_name not in columns:
            continue

        cursor = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM "{table_name}"
            WHERE UPPER(TRIM("{column_name}")) = ?
            """,
            (symbol,),
        )

        count = cursor.fetchone()[0]

        if count:
            evidence.append(
                {
                    "table": table_name,
                    "column": column_name,
                    "row_count": count,
                }
            )

    return evidence


def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> EXPECTED UNIVERSE "
        "MARKET HISTORY ALIGNMENT FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print(
        f"Resolution      : "
        f"{EXPECTED_UNIVERSE_RESOLUTION_PATH}"
    )
    print(
        f"Normalization   : "
        f"{NORMALIZATION_FORENSIC_PATH}"
    )
    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Database Write  : FORBIDDEN")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")
    print("-" * 90)

    expected_source, expected = (
        resolve_expected_universe()
    )

    if expected_source is None:
        print(
            "EXPECTED UNIVERSE COULD NOT BE RESOLVED"
        )
        return

    print(
        f"Expected Universe source : {expected_source}"
    )
    print(
        f"Expected Universe        : {len(expected)}"
    )

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:
        history = load_symbol_column(
            conn,
            "market_history",
            "symbol",
        )

        market_universe = load_symbol_column(
            conn,
            "market_universe",
            "symbol",
        )

        market_data = load_symbol_column(
            conn,
            "market_data",
            "symbol",
        )

        print("=" * 90)
        print("UNIVERSE -> MARKET_HISTORY")
        print("=" * 90)

        alignment = build_alignment(
            expected,
            history,
        )

        print(
            f"Expected symbols : "
            f"{alignment['expected_count']}"
        )

        print(
            f"Market_history   : "
            f"{alignment['history_count']}"
        )

        print(
            f"Intersection     : "
            f"{alignment['intersection_count']}"
        )

        print(
            f"Missing          : "
            f"{alignment['missing_count']}"
        )

        if alignment["missing_symbols"]:
            print(
                "MISSING SYMBOLS : "
                + ", ".join(
                    alignment["missing_symbols"]
                )
            )

        print(
            f"Extra            : "
            f"{alignment['extra_count']}"
        )

        if alignment["extra_symbols"]:
            print(
                "EXTRA SYMBOLS : "
                + ", ".join(
                    alignment["extra_symbols"]
                )
            )

        print(
            f"Coverage         : "
            f"{alignment['coverage_percent']:.4f}%"
        )

        print(
            f"Exact Match      : "
            f"{alignment['exact_match']}"
        )

        print("=" * 90)
        print("HISTORY EXTRA SYMBOL FORENSICS")
        print("=" * 90)

        extra_classification = (
            classify_extra_history(
                alignment["extra_symbols"]
            )
        )

        extra_evidence = {}

        for symbol in alignment[
            "extra_symbols"
        ]:
            print("-" * 90)
            print(f"SYMBOL : {symbol}")
            print(
                "CLASSIFICATION : "
                + extra_classification[symbol]
            )

            evidence = get_symbol_evidence(
                conn,
                symbol,
            )

            extra_evidence[symbol] = evidence

            if evidence:
                print("EVIDENCE :")

                for item in evidence:
                    print(
                        f"  {item['table']}"
                        f":{item['column']}"
                        f" -> {item['row_count']} rows"
                    )
            else:
                print(
                    "EVIDENCE : NONE"
                )

        print("=" * 90)
        print("EXPECTED SYMBOL MISSING FROM HISTORY")
        print("=" * 90)

        missing_classification = (
            classify_missing_history(
                alignment["missing_symbols"]
            )
        )

        missing_evidence = {}

        for symbol in alignment[
            "missing_symbols"
        ]:
            print("-" * 90)
            print(f"SYMBOL : {symbol}")
            print(
                "CLASSIFICATION : "
                + missing_classification[symbol]
            )

            evidence = get_symbol_evidence(
                conn,
                symbol,
            )

            missing_evidence[symbol] = evidence

            if evidence:
                print("EVIDENCE :")

                for item in evidence:
                    print(
                        f"  {item['table']}"
                        f":{item['column']}"
                        f" -> {item['row_count']} rows"
                    )
            else:
                print(
                    "EVIDENCE : NONE"
                )

        print("=" * 90)
        print("REFERENCE TABLE COMPARISON")
        print("=" * 90)

        reference_comparisons = {}

        for name, symbols in [
            (
                "MARKET_UNIVERSE",
                market_universe,
            ),
            (
                "MARKET_HISTORY",
                history,
            ),
            (
                "MARKET_DATA",
                market_data,
            ),
        ]:
            comparison = build_alignment(
                expected,
                symbols,
            )

            reference_comparisons[name] = (
                comparison
            )

            print("-" * 90)
            print(f"SOURCE : {name}")
            print(
                f"SYMBOL COUNT : "
                f"{len(symbols)}"
            )
            print(
                f"INTERSECTION : "
                f"{comparison['intersection_count']}"
            )
            print(
                f"MISSING : "
                f"{comparison['missing_count']}"
            )
            print(
                f"EXTRA : "
                f"{comparison['extra_count']}"
            )
            print(
                f"COVERAGE : "
                f"{comparison['coverage_percent']:.4f}%"
            )
            print(
                f"EXACT MATCH : "
                f"{comparison['exact_match']}"
            )

            if comparison["extra_symbols"]:
                print(
                    "EXTRA SYMBOLS : "
                    + ", ".join(
                        comparison["extra_symbols"]
                    )
                )

        history_extra = set(
            alignment["extra_symbols"]
        )

        known_history_extra = (
            history_extra
            & FORBIDDEN_CONTAMINATION
        )

        unresolved_history_extra = (
            history_extra
            - FORBIDDEN_CONTAMINATION
        )

        expected_missing = set(
            alignment["missing_symbols"]
        )

        known_expected_missing = (
            expected_missing
            & FORBIDDEN_CONTAMINATION
        )

        unresolved_expected_missing = (
            expected_missing
            - FORBIDDEN_CONTAMINATION
        )

        if (
            alignment["exact_match"]
        ):
            status = (
                "EXPECTED_UNIVERSE_HISTORY_EXACT_ALIGNMENT"
            )

        elif (
            history_extra
            and not unresolved_history_extra
            and not unresolved_expected_missing
        ):
            status = (
                "HISTORY_EXTRA_SYMBOLS_EXPLAINED_BY_KNOWN_CONTAMINATION"
            )

        elif unresolved_history_extra:
            status = (
                "HISTORY_EXTRA_SYMBOLS_UNRESOLVED"
            )

        elif unresolved_expected_missing:
            status = (
                "EXPECTED_SYMBOLS_MISSING_FROM_HISTORY"
            )

        else:
            status = (
                "EXPECTED_UNIVERSE_HISTORY_ALIGNMENT_PARTIAL"
            )

        artifact = {
            "artifact": (
                "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_"
                "HISTORY_ALIGNMENT_FORENSIC_v0.1"
            ),
            "timestamp_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "mode": "READ ONLY",
            "network": "FORBIDDEN",
            "database_write": False,
            "prediction": False,
            "decision": False,
            "database": DB_PATH,
            "expected_universe": {
                "source": expected_source,
                "count": len(expected),
                "symbols": sorted(expected),
            },
            "market_history": {
                "count": len(history),
                "symbols": sorted(history),
            },
            "alignment": alignment,
            "history_extra_classification":
                extra_classification,
            "history_extra_evidence":
                extra_evidence,
            "missing_symbol_classification":
                missing_classification,
            "missing_symbol_evidence":
                missing_evidence,
            "reference_comparisons":
                reference_comparisons,
            "known_history_extra": sorted(
                known_history_extra
            ),
            "unresolved_history_extra": sorted(
                unresolved_history_extra
            ),
            "known_expected_missing": sorted(
                known_expected_missing
            ),
            "unresolved_expected_missing":
                sorted(
                    unresolved_expected_missing
                ),
            "forensic_status": status,
            "predictive_claim":
                "NOT ESTABLISHED",
            "relationship_calculation":
                "NOT PERFORMED",
            "database_repair":
                "NOT PERFORMED",
        }

        payload = json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        with open(
            OUTPUT_PATH,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(payload)

        digest = sha256_text(
            payload
        )

        print("=" * 90)
        print("ALIGNMENT FORENSIC STATUS")
        print("=" * 90)
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
            "DATABASE REPAIR : NOT PERFORMED"
        )
        print(
            f"Expected Universe : {len(expected)}"
        )
        print(
            f"Market History : {len(history)}"
        )
        print(
            "Known History Extras : "
            f"{len(known_history_extra)}"
        )
        print(
            "Unresolved History Extras : "
            f"{len(unresolved_history_extra)}"
        )
        print(
            "Known Expected Missing : "
            f"{len(known_expected_missing)}"
        )
        print(
            "Unresolved Expected Missing : "
            f"{len(unresolved_expected_missing)}"
        )
        print(
            f"Artifact : {OUTPUT_PATH}"
        )
        print(
            f"SHA256 : {digest}"
        )
        print("=" * 90)

    finally:
        conn.close()


if __name__ == "__main__":
    main()