import hashlib
import json
import os
import sqlite3
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

EXPECTED_UNIVERSE_FORENSIC_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_RESOLUTION_FORENSIC_v0.1.json"
)

ARTIFACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SCRIPT_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_PROVENANCE_FORENSIC_v0.1"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"


# ============================================================================
# HELPERS
# ============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    return value


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_json(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return sha256_text(payload)


def load_json(path):
    if not os.path.exists(path):
        return None

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_columns(conn, table_name):
    if not table_exists(
        conn,
        table_name,
    ):
        return []

    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def quote_identifier(value):
    return (
        '"'
        + str(value).replace('"', '""')
        + '"'
    )


def find_symbol_column(columns):
    preferred = [
        "symbol",
        "asset",
        "ticker",
        "base_symbol",
        "coin",
        "currency",
    ]

    lower_map = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in preferred:
        if candidate in lower_map:
            return lower_map[candidate]

    return None


# ============================================================================
# GENERIC SYMBOL EXTRACTION
# ============================================================================

SYMBOL_KEYS = {
    "symbol",
    "symbols",
    "asset",
    "assets",
    "ticker",
    "tickers",
    "base_symbol",
    "base_symbols",
    "coin",
    "coins",
    "universe",
    "expected_universe",
    "expected_symbols",
    "feature_symbols",
}


def extract_symbols_from_json(value):
    symbols = set()

    def extract_value(node):
        if isinstance(node, str):
            symbol = normalize_symbol(node)

            if symbol:
                symbols.add(symbol)

        elif isinstance(node, list):
            for item in node:
                extract_value(item)

    def walk(node):
        if isinstance(node, dict):
            for key, child in node.items():
                normalized_key = (
                    str(key)
                    .strip()
                    .lower()
                )

                if normalized_key in SYMBOL_KEYS:
                    extract_value(child)

                walk(child)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)

    return sorted(symbols)


# ============================================================================
# DATABASE SYMBOL INVENTORY
# ============================================================================

def load_database_symbol_inventory(conn):
    inventory = []

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    for row in rows:
        table_name = row[0]

        columns = get_table_columns(
            conn,
            table_name,
        )

        symbol_column = find_symbol_column(
            columns
        )

        if symbol_column is None:
            continue

        quoted_table = quote_identifier(
            table_name
        )

        quoted_column = quote_identifier(
            symbol_column
        )

        try:
            result = conn.execute(
                f"""
                SELECT DISTINCT
                    {quoted_column}
                FROM {quoted_table}
                WHERE {quoted_column} IS NOT NULL
                  AND TRIM(
                        CAST(
                            {quoted_column}
                            AS TEXT
                        )
                      ) <> ''
                """
            ).fetchall()

        except Exception:
            continue

        symbols = set()

        for result_row in result:
            symbol = normalize_symbol(
                result_row[0]
            )

            if symbol:
                symbols.add(symbol)

        inventory.append(
            {
                "table": table_name,
                "column": symbol_column,
                "symbol_count": len(symbols),
                "symbols": sorted(symbols),
            }
        )

    return inventory


# ============================================================================
# EXPECTED UNIVERSE
# ============================================================================

def resolve_expected_universe(
    resolution_artifact,
):
    if not resolution_artifact:
        return {
            "status": "MISSING_RESOLUTION_ARTIFACT",
            "source": None,
            "symbols": [],
        }

    resolution = (
        resolution_artifact.get(
            "resolution",
            {},
        )
    )

    symbols = resolution.get(
        "symbols",
        [],
    )

    symbols = sorted(
        {
            normalize_symbol(symbol)
            for symbol in symbols
            if normalize_symbol(symbol)
        }
    )

    status = resolution.get(
        "status"
    )

    source = resolution.get(
        "source"
    )

    if not symbols:
        return {
            "status": "UNRESOLVED",
            "source": source,
            "symbols": [],
        }

    return {
        "status": status or "RESOLVED",
        "source": source,
        "symbols": symbols,
    }


# ============================================================================
# SET COMPARISON
# ============================================================================

def compare_sets(
    expected_symbols,
    observed_symbols,
):
    expected = set(expected_symbols)
    observed = set(observed_symbols)

    intersection = expected & observed
    missing = expected - observed
    extra = observed - expected

    coverage = 0.0

    if expected:
        coverage = (
            len(intersection)
            / len(expected)
        ) * 100.0

    return {
        "expected_count": len(expected),
        "observed_count": len(observed),
        "intersection_count": len(intersection),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "coverage_pct": round(
            coverage,
            4,
        ),
        "exact_match": (
            expected == observed
        ),
        "missing_symbols": sorted(
            missing
        ),
        "extra_symbols": sorted(
            extra
        ),
    }


# ============================================================================
# SYMBOL PROVENANCE
# ============================================================================

def build_symbol_provenance(
    expected_symbols,
    database_inventory,
    contract_symbols,
    source_forensic_symbols,
):
    expected_set = set(
        expected_symbols
    )

    provenance = {}

    database_maps = {}

    for source in database_inventory:
        source_name = (
            "DATABASE_TABLE:"
            + source["table"]
            + ":"
            + source["column"]
        )

        database_maps[source_name] = set(
            source["symbols"]
        )

    for symbol in sorted(expected_set):
        evidence = []

        if symbol in set(contract_symbols):
            evidence.append(
                "FEATURE_CONTRACT"
            )

        if symbol in set(
            source_forensic_symbols
        ):
            evidence.append(
                "SOURCE_FORENSIC"
            )

        for source_name, symbols in database_maps.items():
            if symbol in symbols:
                evidence.append(
                    source_name
                )

        provenance[symbol] = {
            "symbol": symbol,
            "evidence_count": len(
                evidence
            ),
            "evidence_sources": sorted(
                evidence
            ),
        }

    return provenance


# ============================================================================
# GROUP PROVENANCE
# ============================================================================

def build_provenance_groups(
    provenance,
):
    groups = {}

    for symbol, record in provenance.items():
        key = tuple(
            record["evidence_sources"]
        )

        groups.setdefault(
            key,
            [],
        ).append(symbol)

    result = []

    for evidence_sources, symbols in sorted(
        groups.items(),
        key=lambda item: (
            str(item[0]),
            item[1],
        ),
    ):
        result.append(
            {
                "evidence_sources": list(
                    evidence_sources
                ),
                "symbol_count": len(
                    symbols
                ),
                "symbols": sorted(
                    symbols
                ),
            }
        )

    return result


# ============================================================================
# IMPORTANT SYMBOL DIFFERENCE
# ============================================================================

def calculate_known_differences(
    expected_symbols,
    database_inventory,
):
    expected = set(
        expected_symbols
    )

    results = []

    for source in database_inventory:
        observed = set(
            source["symbols"]
        )

        comparison = compare_sets(
            expected,
            observed,
        )

        results.append(
            {
                "source": (
                    "DATABASE_TABLE:"
                    + source["table"]
                    + ":"
                    + source["column"]
                ),
                **comparison,
            }
        )

    return results


# ============================================================================
# READ-ONLY GUARD
# ============================================================================

def enable_read_only(conn):
    conn.execute(
        "PRAGMA query_only = ON"
    )

    row = conn.execute(
        "PRAGMA query_only"
    ).fetchone()

    return bool(
        row
        and row[0] == 1
    )


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> "
        "EXPECTED UNIVERSE PROVENANCE FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Feature Contract: {FEATURE_CONTRACT_PATH}"
    )

    print(
        f"Source Forensic : {SOURCE_FORENSIC_PATH}"
    )

    print(
        f"Universe Resolve: {EXPECTED_UNIVERSE_FORENSIC_PATH}"
    )

    print(
        f"Mode            : {MODE}"
    )

    print(
        f"Network         : {NETWORK}"
    )

    print(
        f"Outcome         : {OUTCOME}"
    )

    print(
        f"Prediction      : {PREDICTION}"
    )

    print(
        f"Decision        : {DECISION}"
    )

    print(
        f"Database Write  : {DATABASE_WRITE}"
    )

    print("-" * 90)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            DB_PATH
        )

    contract = load_json(
        FEATURE_CONTRACT_PATH
    )

    source_forensic = load_json(
        SOURCE_FORENSIC_PATH
    )

    resolution_artifact = load_json(
        EXPECTED_UNIVERSE_FORENSIC_PATH
    )

    contract_symbols = (
        extract_symbols_from_json(
            contract
        )
    )

    source_symbols = (
        extract_symbols_from_json(
            source_forensic
        )
    )

    universe_resolution = (
        resolve_expected_universe(
            resolution_artifact
        )
    )

    expected_symbols = (
        universe_resolution[
            "symbols"
        ]
    )

    print("=" * 90)
    print("EXPECTED UNIVERSE INPUT")
    print("=" * 90)

    print(
        f"Resolution status : "
        f"{universe_resolution['status']}"
    )

    print(
        f"Resolution source : "
        f"{universe_resolution['source']}"
    )

    print(
        f"Expected symbols  : "
        f"{len(expected_symbols)}"
    )

    if expected_symbols:
        print(
            "EXPECTED UNIVERSE : "
            + ", ".join(
                expected_symbols
            )
        )

    print("=" * 90)
    print("DIRECT INPUT COMPARISON")
    print("=" * 90)

    contract_comparison = compare_sets(
        expected_symbols,
        contract_symbols,
    )

    source_comparison = compare_sets(
        expected_symbols,
        source_symbols,
    )

    print("-" * 90)
    print("FEATURE CONTRACT")
    print(
        f"Expected : "
        f"{contract_comparison['expected_count']}"
    )
    print(
        f"Observed : "
        f"{contract_comparison['observed_count']}"
    )
    print(
        f"Intersection : "
        f"{contract_comparison['intersection_count']}"
    )
    print(
        f"Coverage : "
        f"{contract_comparison['coverage_pct']:.4f}%"
    )
    print(
        f"Missing : "
        f"{contract_comparison['missing_count']}"
    )
    print(
        f"Extra : "
        f"{contract_comparison['extra_count']}"
    )
    print(
        f"Exact match : "
        f"{contract_comparison['exact_match']}"
    )

    print("-" * 90)
    print("SOURCE FORENSIC")
    print(
        f"Expected : "
        f"{source_comparison['expected_count']}"
    )
    print(
        f"Observed : "
        f"{source_comparison['observed_count']}"
    )
    print(
        f"Intersection : "
        f"{source_comparison['intersection_count']}"
    )
    print(
        f"Coverage : "
        f"{source_comparison['coverage_pct']:.4f}%"
    )
    print(
        f"Missing : "
        f"{source_comparison['missing_count']}"
    )
    print(
        f"Extra : "
        f"{source_comparison['extra_count']}"
    )
    print(
        f"Exact match : "
        f"{source_comparison['exact_match']}"
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:
        readonly_verified = (
            enable_read_only(
                conn
            )
        )

        if not readonly_verified:
            raise RuntimeError(
                "SQLite READ ONLY guard failed."
            )

        print("=" * 90)
        print("DATABASE PROVENANCE INVENTORY")
        print("=" * 90)

        database_inventory = (
            load_database_symbol_inventory(
                conn
            )
        )

        for source in database_inventory:
            print("-" * 90)

            print(
                f"TABLE : {source['table']}"
            )

            print(
                f"COLUMN : {source['column']}"
            )

            print(
                f"SYMBOL COUNT : "
                f"{source['symbol_count']}"
            )

            if source["symbols"]:
                print(
                    "SYMBOLS : "
                    + ", ".join(
                        source["symbols"]
                    )
                )

        print("=" * 90)
        print("EXPECTED UNIVERSE DATABASE COMPARISON")
        print("=" * 90)

        database_differences = (
            calculate_known_differences(
                expected_symbols,
                database_inventory,
            )
        )

        for record in database_differences:
            print("-" * 90)

            print(
                f"SOURCE : "
                f"{record['source']}"
            )

            print(
                f"EXPECTED : "
                f"{record['expected_count']}"
            )

            print(
                f"OBSERVED : "
                f"{record['observed_count']}"
            )

            print(
                f"INTERSECTION : "
                f"{record['intersection_count']}"
            )

            print(
                f"COVERAGE : "
                f"{record['coverage_pct']:.4f}%"
            )

            print(
                f"MISSING : "
                f"{record['missing_count']}"
            )

            if record["missing_symbols"]:
                print(
                    "MISSING SYMBOLS : "
                    + ", ".join(
                        record[
                            "missing_symbols"
                        ]
                    )
                )

            print(
                f"EXTRA : "
                f"{record['extra_count']}"
            )

            print(
                f"EXACT MATCH : "
                f"{record['exact_match']}"
            )

        print("=" * 90)
        print("SYMBOL PROVENANCE")
        print("=" * 90)

        provenance = build_symbol_provenance(
            expected_symbols=expected_symbols,
            database_inventory=database_inventory,
            contract_symbols=contract_symbols,
            source_forensic_symbols=source_symbols,
        )

        provenance_groups = (
            build_provenance_groups(
                provenance
            )
        )

        for group in provenance_groups:
            print("-" * 90)

            print(
                "EVIDENCE SOURCES : "
                + (
                    ", ".join(
                        group[
                            "evidence_sources"
                        ]
                    )
                    if group[
                        "evidence_sources"
                    ]
                    else "NONE"
                )
            )

            print(
                f"SYMBOL COUNT : "
                f"{group['symbol_count']}"
            )

            print(
                "SYMBOLS : "
                + ", ".join(
                    group["symbols"]
                )
            )

        # ====================================================================
        # SPECIAL CHECKS
        # ====================================================================

        market_data_symbols = set()

        for source in database_inventory:
            if (
                source["table"]
                == "market_data"
            ):
                market_data_symbols = set(
                    source["symbols"]
                )
                break

        market_history_symbols = set()

        for source in database_inventory:
            if (
                source["table"]
                == "market_history"
            ):
                market_history_symbols = set(
                    source["symbols"]
                )
                break

        expected_set = set(
            expected_symbols
        )

        market_data_comparison = (
            compare_sets(
                expected_symbols,
                sorted(
                    market_data_symbols
                ),
            )
        )

        market_history_comparison = (
            compare_sets(
                expected_symbols,
                sorted(
                    market_history_symbols
                ),
            )
        )

        print("=" * 90)
        print("SPECIAL FORENSIC CHECKS")
        print("=" * 90)

        print("-" * 90)
        print("EXPECTED UNIVERSE -> MARKET_DATA")

        print(
            f"Expected symbols : "
            f"{market_data_comparison['expected_count']}"
        )

        print(
            f"Market_data symbols : "
            f"{market_data_comparison['observed_count']}"
        )

        print(
            f"Missing : "
            f"{market_data_comparison['missing_count']}"
        )

        if market_data_comparison[
            "missing_symbols"
        ]:
            print(
                "MISSING SYMBOLS : "
                + ", ".join(
                    market_data_comparison[
                        "missing_symbols"
                    ]
                )
            )

        print(
            f"Extra : "
            f"{market_data_comparison['extra_count']}"
        )

        print(
            f"Coverage : "
            f"{market_data_comparison['coverage_pct']:.4f}%"
        )

        print("-" * 90)
        print("EXPECTED UNIVERSE -> MARKET_HISTORY")

        print(
            f"Expected symbols : "
            f"{market_history_comparison['expected_count']}"
        )

        print(
            f"Market_history symbols : "
            f"{market_history_comparison['observed_count']}"
        )

        print(
            f"Missing : "
            f"{market_history_comparison['missing_count']}"
        )

        if market_history_comparison[
            "missing_symbols"
        ]:
            print(
                "MISSING SYMBOLS : "
                + ", ".join(
                    market_history_comparison[
                        "missing_symbols"
                    ]
                )
            )

        print(
            f"Extra : "
            f"{market_history_comparison['extra_count']}"
        )

        print(
            f"Coverage : "
            f"{market_history_comparison['coverage_pct']:.4f}%"
        )

        # ====================================================================
        # FINAL STATUS
        # ====================================================================

        provenance_established = (
            len(expected_symbols) > 0
            and (
                universe_resolution[
                    "status"
                ]
                in {
                    "RESOLVED",
                    "RESOLVED_BY_EXACT_SYMBOL_MATCH",
                }
            )
        )

        if provenance_established:
            forensic_status = (
                "EXPECTED_UNIVERSE_PROVENANCE_ESTABLISHED"
            )
        else:
            forensic_status = (
                "EXPECTED_UNIVERSE_PROVENANCE_BLOCKED"
            )

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
            f"Expected Universe : "
            f"{len(expected_symbols)}"
        )

        print(
            f"Market_data Coverage : "
            f"{market_data_comparison['coverage_pct']:.4f}%"
        )

        print(
            f"Market_history Coverage : "
            f"{market_history_comparison['coverage_pct']:.4f}%"
        )

        artifact = {
            "script_version": SCRIPT_VERSION,
            "generated_at_utc": utc_now(),
            "database": DB_PATH,
            "feature_contract": FEATURE_CONTRACT_PATH,
            "source_forensic": SOURCE_FORENSIC_PATH,
            "expected_universe_resolution": (
                EXPECTED_UNIVERSE_FORENSIC_PATH
            ),
            "mode": MODE,
            "network": NETWORK,
            "outcome": OUTCOME,
            "prediction": PREDICTION,
            "decision": DECISION,
            "database_write": DATABASE_WRITE,
            "sqlite_query_only": readonly_verified,
            "expected_universe_resolution": (
                universe_resolution
            ),
            "contract_symbols": (
                contract_symbols
            ),
            "source_forensic_symbols": (
                source_symbols
            ),
            "contract_comparison": (
                contract_comparison
            ),
            "source_forensic_comparison": (
                source_comparison
            ),
            "database_symbol_inventory": (
                database_inventory
            ),
            "database_differences": (
                database_differences
            ),
            "symbol_provenance": provenance,
            "provenance_groups": (
                provenance_groups
            ),
            "special_checks": {
                "market_data": (
                    market_data_comparison
                ),
                "market_history": (
                    market_history_comparison
                ),
            },
            "forensic_status": (
                forensic_status
            ),
            "predictive_claim": (
                "NOT ESTABLISHED"
            ),
            "relationship_calculation": (
                "NOT PERFORMED"
            ),
            "database_repair": (
                "NOT PERFORMED"
            ),
        }

        artifact["artifact_sha256"] = (
            sha256_json(
                artifact
            )
        )

        with open(
            ARTIFACT_PATH,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                artifact,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

        print(
            f"Artifact : "
            f"{ARTIFACT_PATH}"
        )

        print(
            f"SHA256   : "
            f"{artifact['artifact_sha256']}"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()