# ARUNDA_CLEANUP_CANDIDATE_INVENTORY_v0.1.py

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

ARTIFACT_JSON = Path(
    r"C:\Users\ASUS\ArundaTrader\ARUNDA_CLEANUP_CANDIDATE_INVENTORY_v0.1.json"
)

ARTIFACT_TXT = Path(
    r"C:\Users\ASUS\ArundaTrader\ARUNDA_CLEANUP_CANDIDATE_INVENTORY_v0.1.txt"
)

EXPECTED_UNIVERSE_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

VERSION = "ARUNDA_CLEANUP_CANDIDATE_INVENTORY_v0.1"


# ============================================================================
# SAFETY
# ============================================================================

READ_ONLY = True
NETWORK_ALLOWED = False
DATABASE_WRITE_ALLOWED = False
DELETE_ALLOWED = False
UPDATE_ALLOWED = False
INSERT_ALLOWED = False


# ============================================================================
# HELPERS
# ============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def safe_json_load(path):
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def normalize_symbol(value):
    if value is None:
        return None

    return str(value).strip().upper()


def table_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return [row[1] for row in rows]


def get_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def find_symbol_columns(conn, tables):
    result = {}

    for table in tables:
        cols = table_columns(conn, table)

        symbol_cols = []

        for col in cols:
            c = col.lower()

            if c in {
                "symbol",
                "market_symbol",
                "base_symbol",
                "asset_symbol",
                "ticker"
            }:
                symbol_cols.append(col)

        if symbol_cols:
            result[table] = symbol_cols

    return result


def load_expected_universe():
    data = safe_json_load(EXPECTED_UNIVERSE_ARTIFACT)

    if data is None:
        return set(), "ARTIFACT_NOT_READ"

    candidates = []

    def recursive_extract(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():

                key_lower = str(key).lower()

                if key_lower in {
                    "expected_universe",
                    "expected_symbols",
                    "symbols",
                    "universe"
                }:
                    if isinstance(value, list):
                        candidates.extend(value)

                recursive_extract(value)

        elif isinstance(obj, list):
            for item in obj:
                recursive_extract(item)

    recursive_extract(data)

    universe = set()

    for value in candidates:
        if isinstance(value, str):
            universe.add(normalize_symbol(value))

        elif isinstance(value, dict):
            for key in (
                "symbol",
                "market_symbol",
                "ticker"
            ):
                if key in value:
                    symbol = normalize_symbol(value[key])

                    if symbol:
                        universe.add(symbol)

    universe.discard(None)

    if universe:
        return universe, "LOADED"

    return set(), "NO_SYMBOL_LIST_FOUND"


# ============================================================================
# DATABASE INVENTORY
# ============================================================================

def inventory_database(conn):
    tables = get_tables(conn)

    symbol_columns = find_symbol_columns(conn, tables)

    symbol_inventory = {}

    for table, columns in symbol_columns.items():

        for column in columns:

            query = f'''
                SELECT "{column}", COUNT(*)
                FROM "{table}"
                WHERE "{column}" IS NOT NULL
                GROUP BY "{column}"
            '''

            try:
                rows = conn.execute(query).fetchall()
            except Exception:
                continue

            for raw_symbol, count in rows:

                symbol = normalize_symbol(raw_symbol)

                if not symbol:
                    continue

                if symbol not in symbol_inventory:
                    symbol_inventory[symbol] = {
                        "symbol": symbol,
                        "tables": {},
                        "total_rows": 0
                    }

                if table not in symbol_inventory[symbol]["tables"]:
                    symbol_inventory[symbol]["tables"][table] = 0

                symbol_inventory[symbol]["tables"][table] += int(count)
                symbol_inventory[symbol]["total_rows"] += int(count)

    return tables, symbol_columns, symbol_inventory


# ============================================================================
# CLASSIFICATION
# ============================================================================

def classify_symbol(symbol, info, expected_universe):

    tables = set(info["tables"].keys())
    total_rows = info["total_rows"]

    reasons = []
    severity = "NONE"

    is_expected = symbol in expected_universe

    # ------------------------------------------------------------
    # Numeric token
    # ------------------------------------------------------------

    numeric_token = symbol.isdigit()

    if numeric_token:
        reasons.append("NUMERIC_SYMBOL_TOKEN")

    # ------------------------------------------------------------
    # Empty / malformed
    # ------------------------------------------------------------

    malformed = False

    if len(symbol) == 0:
        malformed = True
        reasons.append("EMPTY_SYMBOL")

    if len(symbol) > 50:
        malformed = True
        reasons.append("ABNORMALLY_LONG_SYMBOL")

    # ------------------------------------------------------------
    # Historical known extras
    # ------------------------------------------------------------

    known_extra = symbol in {
        "4",
        "ASSET"
    }

    if known_extra:
        reasons.append("KNOWN_EXTRA_SYMBOL_FROM_FORENSIC_CHAIN")

    # ------------------------------------------------------------
    # Universe relationship
    # ------------------------------------------------------------

    if not is_expected:
        reasons.append("OUTSIDE_EXPECTED_UNIVERSE")

    # ------------------------------------------------------------
    # Candidate logic
    # ------------------------------------------------------------

    # IMPORTANT:
    # Outside universe alone is NOT enough for deletion.

    if malformed:
        classification = "MALFORMED_CANDIDATE"
        severity = "HIGH"

    elif numeric_token:
        classification = "REVIEW_NUMERIC_SYMBOL"
        severity = "MEDIUM"

    elif known_extra:
        classification = "REVIEW_KNOWN_EXTRA_SYMBOL"
        severity = "LOW"

    elif not is_expected:
        classification = "REVIEW_OUTSIDE_UNIVERSE"
        severity = "LOW"

    else:
        classification = "NOT_A_CLEANUP_CANDIDATE"

    return {
        "symbol": symbol,
        "expected_universe_member": is_expected,
        "total_rows": total_rows,
        "tables": sorted(tables),
        "classification": classification,
        "severity": severity,
        "reasons": reasons,
        "deletion_authorized": False
    }


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 90)
    print(VERSION)
    print("=" * 90)

    print(f"Database       : {DB_PATH}")
    print(f"Mode           : READ ONLY")
    print(f"Network        : FORBIDDEN")
    print(f"Database Write : FORBIDDEN")
    print(f"Delete         : FORBIDDEN")
    print(f"Update         : FORBIDDEN")
    print(f"Insert         : FORBIDDEN")
    print("-" * 90)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    expected_universe, universe_status = load_expected_universe()

    print()
    print("=" * 90)
    print("EXPECTED UNIVERSE")
    print("=" * 90)
    print(f"Status          : {universe_status}")
    print(f"Universe Symbols : {len(expected_universe)}")

    conn = sqlite3.connect(str(DB_PATH))

    try:

        tables, symbol_columns, symbol_inventory = inventory_database(conn)

    finally:

        conn.close()

    print()
    print("=" * 90)
    print("DATABASE INVENTORY")
    print("=" * 90)

    print(f"Tables        : {len(tables)}")
    print(f"Symbol Tables : {len(symbol_columns)}")
    print(f"Unique Symbols: {len(symbol_inventory)}")

    results = []

    for symbol in sorted(symbol_inventory):

        result = classify_symbol(
            symbol,
            symbol_inventory[symbol],
            expected_universe
        )

        results.append(result)

    candidates = [
        r for r in results
        if r["classification"] != "NOT_A_CLEANUP_CANDIDATE"
    ]

    malformed = [
        r for r in results
        if r["classification"] == "MALFORMED_CANDIDATE"
    ]

    numeric = [
        r for r in results
        if r["classification"] == "REVIEW_NUMERIC_SYMBOL"
    ]

    known_extra = [
        r for r in results
        if r["classification"] == "REVIEW_KNOWN_EXTRA_SYMBOL"
    ]

    outside = [
        r for r in results
        if r["classification"] == "REVIEW_OUTSIDE_UNIVERSE"
    ]

    print()
    print("=" * 90)
    print("CLEANUP CANDIDATE SUMMARY")
    print("=" * 90)

    print(f"Total Symbols              : {len(results)}")
    print(f"Cleanup Candidates         : {len(candidates)}")
    print(f"Malformed Candidates       : {len(malformed)}")
    print(f"Numeric Review Candidates  : {len(numeric)}")
    print(f"Known Extra Symbols        : {len(known_extra)}")
    print(f"Outside Universe Candidates: {len(outside)}")

    print()
    print("=" * 90)
    print("CANDIDATES")
    print("=" * 90)

    if not candidates:
        print("NONE")

    for result in candidates:

        print("-" * 90)
        print(f"SYMBOL       : {result['symbol']}")
        print(f"CLASS        : {result['classification']}")
        print(f"SEVERITY     : {result['severity']}")
        print(
            f"EXPECTED     : "
            f"{result['expected_universe_member']}"
        )
        print(f"TOTAL ROWS   : {result['total_rows']}")
        print(
            f"TABLE COUNT  : "
            f"{len(result['tables'])}"
        )
        print(
            f"TABLES       : "
            f"{', '.join(result['tables'])}"
        )
        print(
            f"REASONS      : "
            f"{'; '.join(result['reasons'])}"
        )
        print("DELETE AUTH  : False")

    # ========================================================================
    # KNOWN SYMBOL FOCUS
    # ========================================================================

    print()
    print("=" * 90)
    print("KNOWN EXTRA SYMBOL CHECK")
    print("=" * 90)

    for target in ("4", "ASSET"):

        info = symbol_inventory.get(target)

        if info is None:
            print(f"{target} : NOT OBSERVED")
            continue

        print("-" * 90)
        print(f"SYMBOL     : {target}")
        print(f"ROWS       : {info['total_rows']}")
        print(f"TABLE COUNT: {len(info['tables'])}")
        print(
            f"TABLES     : "
            f"{', '.join(sorted(info['tables']))}"
        )
        print(
            f"EXPECTED   : "
            f"{target in expected_universe}"
        )
        print("ACTION     : NO DELETE IN INVENTORY STAGE")

    # ========================================================================
    # ARTIFACT
    # ========================================================================

    artifact = {
        "version": VERSION,
        "generated_at_utc": utc_now(),

        "safety": {
            "read_only": READ_ONLY,
            "network_allowed": NETWORK_ALLOWED,
            "database_write_allowed": DATABASE_WRITE_ALLOWED,
            "delete_allowed": DELETE_ALLOWED,
            "update_allowed": UPDATE_ALLOWED,
            "insert_allowed": INSERT_ALLOWED
        },

        "database": {
            "path": str(DB_PATH),
            "tables": tables,
            "table_count": len(tables),
            "symbol_table_count": len(symbol_columns)
        },

        "expected_universe": {
            "artifact": str(EXPECTED_UNIVERSE_ARTIFACT),
            "status": universe_status,
            "count": len(expected_universe),
            "sha256": (
                sha256_file(EXPECTED_UNIVERSE_ARTIFACT)
                if EXPECTED_UNIVERSE_ARTIFACT.exists()
                else None
            )
        },

        "summary": {
            "total_symbols": len(results),
            "cleanup_candidates": len(candidates),
            "malformed_candidates": len(malformed),
            "numeric_review_candidates": len(numeric),
            "known_extra_symbols": len(known_extra),
            "outside_universe_candidates": len(outside)
        },

        "known_extra_symbols": {
            target: next(
                (
                    r for r in results
                    if r["symbol"] == target
                ),
                None
            )
            for target in ("4", "ASSET")
        },

        "candidates": candidates,

        "all_symbols": results,

        "decision": {
            "database_mutation": False,
            "deletion_performed": False,
            "repair_performed": False,
            "cleanup_authorized": False,
            "next_stage": (
                "REVIEW_ONLY_THEN_TARGETED_CLEANUP_IF_PROVEN"
            )
        }
    }

    with open(
        ARTIFACT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================================
    # TEXT REPORT
    # ========================================================================

    lines = []

    lines.append("=" * 90)
    lines.append(VERSION)
    lines.append("=" * 90)

    lines.append(f"Database       : {DB_PATH}")
    lines.append("Mode           : READ ONLY")
    lines.append("Network        : FORBIDDEN")
    lines.append("Database Write : FORBIDDEN")
    lines.append("Delete         : FORBIDDEN")
    lines.append("Repair         : FORBIDDEN")
    lines.append("")

    lines.append("=" * 90)
    lines.append("SUMMARY")
    lines.append("=" * 90)

    lines.append(
        f"Total Symbols               : {len(results)}"
    )

    lines.append(
        f"Cleanup Candidates          : {len(candidates)}"
    )

    lines.append(
        f"Malformed Candidates        : {len(malformed)}"
    )

    lines.append(
        f"Numeric Review Candidates   : {len(numeric)}"
    )

    lines.append(
        f"Known Extra Symbols         : {len(known_extra)}"
    )

    lines.append(
        f"Outside Universe Candidates : {len(outside)}"
    )

    lines.append("")

    lines.append("=" * 90)
    lines.append("CANDIDATES")
    lines.append("=" * 90)

    for result in candidates:

        lines.append("-" * 90)

        lines.append(
            f"SYMBOL       : {result['symbol']}"
        )

        lines.append(
            f"CLASS        : {result['classification']}"
        )

        lines.append(
            f"SEVERITY     : {result['severity']}"
        )

        lines.append(
            f"EXPECTED     : "
            f"{result['expected_universe_member']}"
        )

        lines.append(
            f"TOTAL ROWS   : {result['total_rows']}"
        )

        lines.append(
            f"TABLE COUNT  : {len(result['tables'])}"
        )

        lines.append(
            f"TABLES       : "
            f"{', '.join(result['tables'])}"
        )

        lines.append(
            f"REASONS      : "
            f"{'; '.join(result['reasons'])}"
        )

        lines.append(
            "DELETE AUTH  : False"
        )

    lines.append("")
    lines.append("=" * 90)
    lines.append("FORENSIC STATUS")
    lines.append("=" * 90)
    lines.append(
        "FORENSIC STATUS : CLEANUP_CANDIDATE_INVENTORY_ESTABLISHED"
    )
    lines.append(
        "DATABASE WRITE : NOT PERFORMED"
    )
    lines.append(
        "DATABASE DELETE: NOT PERFORMED"
    )
    lines.append(
        "DATABASE REPAIR: NOT PERFORMED"
    )
    lines.append(
        "PREDICTION     : NOT PERFORMED"
    )
    lines.append(
        "TRADING DECISION: NOT PERFORMED"
    )

    lines.append("")
    lines.append("=" * 90)
    lines.append("ARTIFACT")
    lines.append("=" * 90)

    lines.append(
        f"Artifact : {ARTIFACT_JSON}"
    )

    with open(
        ARTIFACT_TXT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("\n".join(lines))

    artifact_hash = sha256_file(ARTIFACT_JSON)

    print()
    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)

    print(f"Artifact : {ARTIFACT_JSON}")
    print(f"Report   : {ARTIFACT_TXT}")
    print(f"SHA256   : {artifact_hash}")
    print("=" * 90)


if __name__ == "__main__":
    main()