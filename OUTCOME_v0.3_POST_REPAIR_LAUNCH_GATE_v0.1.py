# =================================================================================================
# OUTCOME_v0.3 POST-REPAIR LAUNCH GATE v0.1
# =================================================================================================
#
# PURPOSE:
#   Verify the repaired fusion_signals layer is structurally usable by downstream
#   outcome / execution pipeline WITHOUT redesigning or modifying production code.
#
# IMPORTANT:
#   This is NOT a universe completeness test.
#   Current assets are NOT treated as final production universe.
#   This is NOT a live-data test.
#   This is NOT a signal-quality test.
#
# MODE:
#   READ ONLY
#
# PRODUCTION DB:
#   NEVER MODIFIED
#
# PRODUCTION ENGINE:
#   NEVER EXECUTED
#
# =================================================================================================

from __future__ import annotations

import os
import sqlite3
import hashlib
from collections import Counter


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
DB_PATH = os.path.join(PROJECT_ROOT, "arunda.db")

TARGET_TABLE = "fusion_signals"

EXPECTED_ENGINE = "FUSION_v0.5"

# Current known assets are deliberately NOT treated as final universe.
CURRENT_ASSETS = {"BTC", "ETH", "SOL", "XRP"}

# Directions accepted by the current contract.
VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}


# -------------------------------------------------------------------------------------------------
# OUTPUT
# -------------------------------------------------------------------------------------------------

def banner(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


# -------------------------------------------------------------------------------------------------
# DB
# -------------------------------------------------------------------------------------------------

def connect_read_only():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)

    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


# -------------------------------------------------------------------------------------------------
# SOURCE FINGERPRINT
# -------------------------------------------------------------------------------------------------

def sha256_file(path: str) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


# -------------------------------------------------------------------------------------------------
# SCHEMA
# -------------------------------------------------------------------------------------------------

def get_columns(conn):
    rows = conn.execute(
        f"PRAGMA table_info({TARGET_TABLE})"
    ).fetchall()

    return {
        row[1]: {
            "type": row[2],
            "notnull": row[3],
            "default": row[4],
            "pk": row[5],
        }
        for row in rows
    }


# -------------------------------------------------------------------------------------------------
# TABLE BASELINE
# -------------------------------------------------------------------------------------------------

def load_rows(conn):
    return conn.execute(
        f"""
        SELECT
            id,
            timestamp,
            asset,
            score,
            confidence,
            regime,
            direction,
            entry_price,
            engine_version,
            snapshot_id
        FROM {TARGET_TABLE}
        ORDER BY id
        """
    ).fetchall()


# -------------------------------------------------------------------------------------------------
# CONTRACT CHECKS
# -------------------------------------------------------------------------------------------------

def check_schema(columns):
    required = {
        "id",
        "timestamp",
        "asset",
        "score",
        "confidence",
        "regime",
        "direction",
        "entry_price",
        "engine_version",
        "snapshot_id",
    }

    missing = required - set(columns)

    if missing:
        return False, f"Missing columns: {sorted(missing)}"

    return True, "Required columns present"


def check_identity(rows):
    ids = [r[0] for r in rows]

    if len(ids) != len(set(ids)):
        return False, "Duplicate IDs detected"

    return True, "IDs unique"


def check_direction_contract(rows):
    invalid = []

    for row in rows:
        direction = row[6]

        if direction is None:
            invalid.append((row[0], row[2], "NULL"))

        elif str(direction).upper() not in VALID_DIRECTIONS:
            invalid.append((row[0], row[2], direction))

    if invalid:
        return False, invalid

    return True, None


def check_entry_price(rows):
    invalid = []

    for row in rows:
        entry = row[7]

        if entry is None:
            invalid.append((row[0], row[2], "NULL_ENTRY"))

        else:
            try:
                value = float(entry)

                if value <= 0:
                    invalid.append((row[0], row[2], value))

            except Exception:
                invalid.append((row[0], row[2], "NON_NUMERIC"))

    if invalid:
        return False, invalid

    return True, None


def check_engine_versions(rows):
    versions = Counter(row[8] for row in rows)

    return versions


# -------------------------------------------------------------------------------------------------
# CURRENT VS FUTURE UNIVERSE
# -------------------------------------------------------------------------------------------------

def analyze_universe(rows):
    assets = sorted(
        {
            str(row[2]).upper()
            for row in rows
            if row[2] is not None
        }
    )

    return assets


# -------------------------------------------------------------------------------------------------
# DOWNSTREAM READINESS
# -------------------------------------------------------------------------------------------------

def check_outcome_readiness(rows):
    """
    This checks whether fusion rows contain the minimum information required
    to be consumed by an outcome layer.

    It deliberately does NOT execute the outcome engine.
    """

    failures = []

    for row in rows:
        (
            row_id,
            timestamp,
            asset,
            score,
            confidence,
            regime,
            direction,
            entry_price,
            engine_version,
            snapshot_id,
        ) = row

        if timestamp is None:
            failures.append((row_id, "timestamp"))

        if asset is None:
            failures.append((row_id, "asset"))

        if direction is None:
            failures.append((row_id, "direction"))

        if entry_price is None:
            failures.append((row_id, "entry_price"))

        if engine_version is None:
            failures.append((row_id, "engine_version"))

    return failures


# -------------------------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------------------------

def main():

    banner("OUTCOME_v0.3 POST-REPAIR LAUNCH GATE v0.1")

    print(f"Database       : {DB_PATH}")
    print(f"Target table   : {TARGET_TABLE}")
    print()
    print("MODE           : READ ONLY")
    print("PRODUCTION DB  : NEVER MODIFIED")
    print("ENGINE RUN     : NO")
    print()
    print("IMPORTANT:")
    print("Current asset universe is NOT treated as final production universe.")
    print("This gate verifies readiness of the repaired layer only.")
    print("No historical inference is performed.")
    print("No live data is injected.")
    print("No production source is modified.")

    # ---------------------------------------------------------------------------------------------
    # SOURCE
    # ---------------------------------------------------------------------------------------------

    banner("SOURCE FINGERPRINT")

    fusion_path = os.path.join(PROJECT_ROOT, "fusion_engine.py")

    if os.path.exists(fusion_path):
        print(f"fusion_engine.py SHA256 : {sha256_file(fusion_path)}")
    else:
        print("fusion_engine.py : NOT FOUND")

    # ---------------------------------------------------------------------------------------------
    # READ DB
    # ---------------------------------------------------------------------------------------------

    conn = connect_read_only()

    try:

        banner("DATABASE BASELINE")

        total = conn.execute(
            f"SELECT COUNT(*) FROM {TARGET_TABLE}"
        ).fetchone()[0]

        null_direction = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {TARGET_TABLE}
            WHERE direction IS NULL
            """
        ).fetchone()[0]

        valid_direction = total - null_direction

        print(f"Total rows       : {total}")
        print(f"Valid direction  : {valid_direction}")
        print(f"NULL direction   : {null_direction}")

        # -----------------------------------------------------------------------------------------
        # SCHEMA
        # -----------------------------------------------------------------------------------------

        banner("SCHEMA CONTRACT")

        columns = get_columns(conn)

        schema_ok, schema_detail = check_schema(columns)

        print(f"Schema contract  : {'PASS' if schema_ok else 'FAIL'}")
        print(f"Detail           : {schema_detail}")

        # -----------------------------------------------------------------------------------------
        # ROWS
        # -----------------------------------------------------------------------------------------

        rows = load_rows(conn)

        # -----------------------------------------------------------------------------------------
        # IDENTITY
        # -----------------------------------------------------------------------------------------

        banner("ROW IDENTITY CONTRACT")

        identity_ok, identity_detail = check_identity(rows)

        print(f"Identity         : {'PASS' if identity_ok else 'FAIL'}")
        print(f"Detail           : {identity_detail}")

        # -----------------------------------------------------------------------------------------
        # DIRECTION
        # -----------------------------------------------------------------------------------------

        banner("DIRECTION CONTRACT")

        direction_ok, direction_detail = check_direction_contract(rows)

        print(f"Direction        : {'PASS' if direction_ok else 'FAIL'}")

        if direction_ok:
            print("Allowed values   : LONG / SHORT / FLAT")
        else:
            print("Invalid rows:")
            for item in direction_detail[:20]:
                print(f"  {item}")

        # -----------------------------------------------------------------------------------------
        # ENTRY
        # -----------------------------------------------------------------------------------------

        banner("ENTRY PRICE CONTRACT")

        entry_ok, entry_detail = check_entry_price(rows)

        print(f"Entry price      : {'PASS' if entry_ok else 'FAIL'}")

        if not entry_ok:
            for item in entry_detail[:20]:
                print(f"  {item}")

        # -----------------------------------------------------------------------------------------
        # ENGINE
        # -----------------------------------------------------------------------------------------

        banner("ENGINE VERSION DISTRIBUTION")

        versions = check_engine_versions(rows)

        for version, count in sorted(
            versions.items(),
            key=lambda x: str(x[0])
        ):
            print(f"{str(version):25} | {count}")

        # -----------------------------------------------------------------------------------------
        # UNIVERSE
        # -----------------------------------------------------------------------------------------

        banner("CURRENT UNIVERSE OBSERVATION")

        assets = analyze_universe(rows)

        print(f"Assets currently represented : {len(assets)}")
        print(f"Assets                       : {', '.join(assets)}")

        print()
        print("UNIVERSE STATUS              : NOT FINAL")
        print("Universe expansion           : FUTURE FRONTIER")
        print("Launch universe completeness : NOT TESTED")

        # -----------------------------------------------------------------------------------------
        # OUTCOME
        # -----------------------------------------------------------------------------------------

        banner("OUTCOME CONSUMER READINESS")

        outcome_failures = check_outcome_readiness(rows)

        outcome_ok = len(outcome_failures) == 0

        print(
            f"Minimum outcome input contract : "
            f"{'PASS' if outcome_ok else 'FAIL'}"
        )

        if not outcome_ok:
            print("Failures:")
            for item in outcome_failures[:30]:
                print(f"  row={item[0]} field={item[1]}")

        # -----------------------------------------------------------------------------------------
        # REPAIR SCOPE
        # -----------------------------------------------------------------------------------------

        banner("HISTORICAL REPAIR VERIFICATION")

        repaired_scope = conn.execute(
            f"""
            SELECT engine_version, COUNT(*)
            FROM {TARGET_TABLE}
            WHERE engine_version IN (
                'FUSION_v0.2',
                'FUSION_v0.3',
                'FUSION_v0.4'
            )
            GROUP BY engine_version
            ORDER BY engine_version
            """
        ).fetchall()

        for version, count in repaired_scope:
            print(f"{version:20} | rows={count}")

        # -----------------------------------------------------------------------------------------
        # FINAL GATE
        # -----------------------------------------------------------------------------------------

        banner("POST-REPAIR LAUNCH GATE")

        checks = {
            "DATABASE_EXISTS": True,
            "SCHEMA_CONTRACT": schema_ok,
            "ROW_IDENTITY": identity_ok,
            "DIRECTION_CONTRACT": direction_ok,
            "ENTRY_PRICE_CONTRACT": entry_ok,
            "OUTCOME_INPUT_READINESS": outcome_ok,
            "NO_NULL_DIRECTION": null_direction == 0,
        }

        for name, result in checks.items():
            print(f"{name:30} : {'PASS' if result else 'FAIL'}")

        overall = all(checks.values())

        print()
        print("=" * 100)

        if overall:
            print("POST-REPAIR GATE : PASS")
            print()
            print("NEXT FRONTIER:")
            print("  1. OUTCOME PIPELINE")
            print("  2. LIVE MARKET CONNECTIVITY")
            print("  3. UNIVERSE EXPANSION")
            print("  4. FULL-SYSTEM LAUNCH READINESS")
        else:
            print("POST-REPAIR GATE : FAIL")
            print()
            print("Launch path blocked until failed contract(s) are resolved.")

        print("=" * 100)

        print()
        print("SAFETY VERDICT")
        print("-" * 100)
        print("Production DB writes : NONE")
        print("INSERT               : NONE")
        print("UPDATE               : NONE")
        print("DELETE               : NONE")
        print("DDL                  : NONE")
        print("Production engine    : NOT EXECUTED")
        print("Historical repair    : NONE")
        print("Direction inference  : NONE")
        print("Synthetic data       : NONE")
        print("Live data injection  : NONE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()