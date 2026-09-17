import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone


DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"
FEATURE_CONTRACT_PATH = r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
SOURCE_FORENSIC_PATH = r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_SOURCE_SYMBOL_INPUT_FORENSIC_v0.1.json"

ARTIFACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_RESOLUTION_FORENSIC_v0.1.json"
)

SCRIPT_VERSION = "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_RESOLUTION_FORENSIC_v0.1"

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"


# ============================================================================
# BASIC HELPERS
# ============================================================================

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


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    return value


def load_json(path):
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as handle:
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
    if not table_exists(conn, table_name):
        return []

    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def safe_identifier(value):
    return '"' + str(value).replace('"', '""') + '"'


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
# SYMBOL EXTRACTION
# ============================================================================

def collect_symbols_from_json(value):
    symbols = set()

    symbol_keys = {
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

    def walk(node):
        if isinstance(node, dict):
            for key, child in node.items():
                normalized_key = str(key).strip().lower()

                if normalized_key in symbol_keys:
                    extract_symbol_value(child)

                walk(child)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    def extract_symbol_value(node):
        if isinstance(node, str):
            symbol = normalize_symbol(node)

            if symbol and len(symbol) <= 30:
                symbols.add(symbol)

        elif isinstance(node, list):
            for item in node:
                if isinstance(item, str):
                    symbol = normalize_symbol(item)

                    if symbol and len(symbol) <= 30:
                        symbols.add(symbol)

    walk(value)

    return sorted(symbols)


def extract_contract_symbols(contract):
    if not contract:
        return []

    return collect_symbols_from_json(contract)


def extract_source_forensic_symbols(source_forensic):
    if not source_forensic:
        return []

    symbols = set(
        collect_symbols_from_json(source_forensic)
    )

    return sorted(symbols)


# ============================================================================
# DATABASE SYMBOL DISCOVERY
# ============================================================================

def discover_database_symbol_sources(conn):
    results = []

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
        columns = get_table_columns(conn, table_name)

        symbol_column = find_symbol_column(columns)

        if symbol_column is None:
            continue

        quoted_table = safe_identifier(table_name)
        quoted_column = safe_identifier(symbol_column)

        try:
            query = f"""
                SELECT DISTINCT {quoted_column}
                FROM {quoted_table}
                WHERE {quoted_column} IS NOT NULL
                  AND TRIM(CAST({quoted_column} AS TEXT)) <> ''
            """

            values = conn.execute(query).fetchall()

        except Exception:
            continue

        symbols = set()

        for value_row in values:
            symbol = normalize_symbol(value_row[0])

            if symbol:
                symbols.add(symbol)

        results.append(
            {
                "table": table_name,
                "column": symbol_column,
                "symbol_count": len(symbols),
                "symbols": sorted(symbols),
            }
        )

    return results


# ============================================================================
# MARKET DATA UNIVERSE
# ============================================================================

def discover_market_data_symbols(conn):
    if not table_exists(conn, "market_data"):
        return {
            "table_exists": False,
            "symbol_column": None,
            "symbol_count": 0,
            "symbols": [],
        }

    columns = get_table_columns(conn, "market_data")
    symbol_column = find_symbol_column(columns)

    if symbol_column is None:
        return {
            "table_exists": True,
            "symbol_column": None,
            "symbol_count": 0,
            "symbols": [],
        }

    quoted_column = safe_identifier(symbol_column)

    rows = conn.execute(
        f"""
        SELECT DISTINCT {quoted_column}
        FROM market_data
        WHERE {quoted_column} IS NOT NULL
          AND TRIM(CAST({quoted_column} AS TEXT)) <> ''
        """
    ).fetchall()

    symbols = set()

    for row in rows:
        symbol = normalize_symbol(row[0])

        if symbol:
            symbols.add(symbol)

    return {
        "table_exists": True,
        "symbol_column": symbol_column,
        "symbol_count": len(symbols),
        "symbols": sorted(symbols),
    }


# ============================================================================
# CANDIDATE UNIVERSE RESOLUTION
# ============================================================================

def score_candidate(candidate_symbols, feature_symbols):
    candidate = set(candidate_symbols)
    feature = set(feature_symbols)

    if not candidate:
        return {
            "intersection_count": 0,
            "feature_coverage_count": 0,
            "feature_coverage_pct": 0.0,
            "extra_count": 0,
            "missing_count": len(feature),
            "exact_match": False,
        }

    intersection = candidate & feature
    missing = feature - candidate
    extra = candidate - feature

    coverage_pct = 0.0

    if feature:
        coverage_pct = (
            len(intersection) / len(feature)
        ) * 100.0

    return {
        "intersection_count": len(intersection),
        "feature_coverage_count": len(intersection),
        "feature_coverage_pct": round(coverage_pct, 4),
        "extra_count": len(extra),
        "missing_count": len(missing),
        "exact_match": candidate == feature,
    }


def resolve_expected_universe(
    contract_symbols,
    source_symbols,
    database_sources,
    market_data_symbols,
):
    candidates = []

    if contract_symbols:
        candidates.append(
            {
                "source": "FEATURE_CONTRACT",
                "symbols": sorted(set(contract_symbols)),
            }
        )

    if source_symbols:
        candidates.append(
            {
                "source": "SOURCE_FORENSIC",
                "symbols": sorted(set(source_symbols)),
            }
        )

    for source in database_sources:
        if source["symbols"]:
            candidates.append(
                {
                    "source": (
                        "DATABASE_TABLE:"
                        + source["table"]
                        + ":"
                        + source["column"]
                    ),
                    "symbols": source["symbols"],
                }
            )

    if market_data_symbols:
        candidates.append(
            {
                "source": "MARKET_DATA",
                "symbols": sorted(set(market_data_symbols)),
            }
        )

    scored = []

    for candidate in candidates:
        score = score_candidate(
            candidate["symbols"],
            source_symbols if source_symbols else contract_symbols,
        )

        scored.append(
            {
                "source": candidate["source"],
                "symbols": candidate["symbols"],
                "symbol_count": len(candidate["symbols"]),
                "score": score,
            }
        )

    # Deterministic priority:
    # 1. FEATURE_CONTRACT
    # 2. SOURCE_FORENSIC
    # 3. exact match
    # 4. highest feature coverage
    # 5. highest symbol count
    priority = {
        "FEATURE_CONTRACT": 0,
        "SOURCE_FORENSIC": 1,
    }

    def ranking(item):
        return (
            priority.get(item["source"], 2),
            -int(item["score"]["exact_match"]),
            -item["score"]["feature_coverage_count"],
            -item["score"]["feature_coverage_pct"],
            -item["symbol_count"],
            item["source"],
        )

    scored_sorted = sorted(
        scored,
        key=ranking,
    )

    if not scored_sorted:
        return {
            "status": "UNRESOLVED",
            "source": None,
            "symbols": [],
            "symbol_count": 0,
            "candidates": [],
        }

    best = scored_sorted[0]

    # A candidate is considered resolved only if it is
    # directly grounded in contract/source forensic evidence,
    # or it exactly matches the established feature symbol universe.
    authoritative_sources = {
        "FEATURE_CONTRACT",
        "SOURCE_FORENSIC",
    }

    if best["source"] in authoritative_sources:
        resolution_status = "RESOLVED"
    elif best["score"]["exact_match"]:
        resolution_status = "RESOLVED_BY_EXACT_SYMBOL_MATCH"
    else:
        resolution_status = "UNRESOLVED"

    return {
        "status": resolution_status,
        "source": (
            best["source"]
            if resolution_status != "UNRESOLVED"
            else None
        ),
        "symbols": (
            best["symbols"]
            if resolution_status != "UNRESOLVED"
            else []
        ),
        "symbol_count": (
            best["symbol_count"]
            if resolution_status != "UNRESOLVED"
            else 0
        ),
        "candidates": scored_sorted,
    }


# ============================================================================
# DATABASE READ-ONLY GUARD
# ============================================================================

def verify_read_only(conn):
    conn.execute("PRAGMA query_only = ON")

    row = conn.execute(
        "PRAGMA query_only"
    ).fetchone()

    return bool(row and row[0] == 1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> EXPECTED UNIVERSE RESOLUTION FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print(f"Feature Contract: {FEATURE_CONTRACT_PATH}")
    print(f"Source Forensic : {SOURCE_FORENSIC_PATH}")
    print(f"Mode            : {MODE}")
    print(f"Network         : {NETWORK}")
    print(f"Outcome         : {OUTCOME}")
    print(f"Prediction      : {PREDICTION}")
    print(f"Decision        : {DECISION}")
    print(f"Database Write  : {DATABASE_WRITE}")
    print("-" * 90)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    contract = load_json(
        FEATURE_CONTRACT_PATH
    )

    source_forensic = load_json(
        SOURCE_FORENSIC_PATH
    )

    contract_symbols = extract_contract_symbols(
        contract
    )

    source_symbols = extract_source_forensic_symbols(
        source_forensic
    )

    print("FEATURE SYMBOL INPUT")
    print("-" * 90)
    print(
        f"Contract symbols discovered : {len(contract_symbols)}"
    )
    print(
        f"Source forensic symbols     : {len(source_symbols)}"
    )

    if contract_symbols:
        print(
            "CONTRACT SYMBOLS : "
            + ", ".join(contract_symbols)
        )

    if source_symbols:
        print(
            "SOURCE FORENSIC SYMBOLS : "
            + ", ".join(source_symbols)
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:
        readonly_verified = verify_read_only(
            conn
        )

        print("-" * 90)
        print(
            f"SQLite query_only : {readonly_verified}"
        )

        if not readonly_verified:
            raise RuntimeError(
                "READ-ONLY verification failed."
            )

        print("=" * 90)
        print("DATABASE SYMBOL SOURCES")
        print("=" * 90)

        database_sources = (
            discover_database_symbol_sources(
                conn
            )
        )

        for source in database_sources:
            print("-" * 90)
            print(
                f"TABLE : {source['table']}"
            )
            print(
                f"COLUMN : {source['column']}"
            )
            print(
                f"SYMBOL COUNT : {source['symbol_count']}"
            )

            if source["symbols"]:
                print(
                    "SYMBOLS : "
                    + ", ".join(source["symbols"])
                )

        print("=" * 90)
        print("MARKET DATA UNIVERSE")
        print("=" * 90)

        market_data_universe = (
            discover_market_data_symbols(
                conn
            )
        )

        print(
            f"Table exists : {market_data_universe['table_exists']}"
        )
        print(
            f"Symbol column : {market_data_universe['symbol_column']}"
        )
        print(
            f"Market_data symbols : {market_data_universe['symbol_count']}"
        )

        if market_data_universe["symbols"]:
            print(
                "SYMBOLS : "
                + ", ".join(
                    market_data_universe["symbols"]
                )
            )

        print("=" * 90)
        print("EXPECTED UNIVERSE RESOLUTION")
        print("=" * 90)

        resolution = resolve_expected_universe(
            contract_symbols=contract_symbols,
            source_symbols=source_symbols,
            database_sources=database_sources,
            market_data_symbols=market_data_universe[
                "symbols"
            ],
        )

        print(
            f"Resolution status : {resolution['status']}"
        )
        print(
            f"Resolved source   : {resolution['source']}"
        )
        print(
            f"Expected symbols  : {resolution['symbol_count']}"
        )

        if resolution["symbols"]:
            print(
                "EXPECTED UNIVERSE : "
                + ", ".join(
                    resolution["symbols"]
                )
            )

        print("=" * 90)
        print("CANDIDATE UNIVERSE COMPARISON")
        print("=" * 90)

        for candidate in resolution["candidates"]:
            score = candidate["score"]

            print("-" * 90)
            print(
                f"SOURCE : {candidate['source']}"
            )
            print(
                f"SYMBOL COUNT : {candidate['symbol_count']}"
            )
            print(
                f"FEATURE INTERSECTION : "
                f"{score['intersection_count']}"
            )
            print(
                f"FEATURE COVERAGE : "
                f"{score['feature_coverage_pct']:.4f}%"
            )
            print(
                f"MISSING : {score['missing_count']}"
            )
            print(
                f"EXTRA : {score['extra_count']}"
            )
            print(
                f"EXACT MATCH : {score['exact_match']}"
            )

        # ------------------------------------------------------------------
        # FINAL STATUS
        # ------------------------------------------------------------------

        if resolution["status"] in {
            "RESOLVED",
            "RESOLVED_BY_EXACT_SYMBOL_MATCH",
        }:
            forensic_status = (
                "EXPECTED_UNIVERSE_RESOLVED"
            )
        else:
            forensic_status = (
                "EXPECTED_UNIVERSE_RESOLUTION_BLOCKED"
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
            f"Resolved source : {resolution['source']}"
        )
        print(
            f"Expected Universe : {resolution['symbol_count']}"
        )

        artifact = {
            "script_version": SCRIPT_VERSION,
            "generated_at_utc": utc_now(),
            "database": DB_PATH,
            "feature_contract": FEATURE_CONTRACT_PATH,
            "source_forensic": SOURCE_FORENSIC_PATH,
            "mode": MODE,
            "network": NETWORK,
            "outcome": OUTCOME,
            "prediction": PREDICTION,
            "decision": DECISION,
            "database_write": DATABASE_WRITE,
            "sqlite_query_only": readonly_verified,
            "feature_symbol_input": {
                "contract_symbols": contract_symbols,
                "source_forensic_symbols": source_symbols,
                "contract_symbol_count": len(
                    contract_symbols
                ),
                "source_forensic_symbol_count": len(
                    source_symbols
                ),
            },
            "market_data_universe": market_data_universe,
            "database_symbol_sources": database_sources,
            "resolution": resolution,
            "forensic_status": forensic_status,
            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",
            "database_repair": "NOT PERFORMED",
        }

        artifact["artifact_sha256"] = sha256_json(
            artifact
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
            f"Artifact : {ARTIFACT_PATH}"
        )
        print(
            f"SHA256   : {artifact['artifact_sha256']}"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()