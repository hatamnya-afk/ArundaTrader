# =================================================================================================
# OUTCOME_v0.3 POST-REPAIR LAUNCH GATE v0.2
# =================================================================================================
#
# PURPOSE:
#   Launch-oriented structural gate for the repaired fusion_signals layer.
#
# IMPORTANT:
#   This script adapts to the REAL production schema.
#
#   It does NOT assume that optional analytical fields such as "score" exist.
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

VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}

REQUIRED_CONTRACT_COLUMNS = {
    "id",
    "timestamp",
    "asset",
    "direction",
    "entry_price",
    "engine_version",
}

OPTIONAL_ANALYTICAL_COLUMNS = {
    "score",
    "confidence",
    "regime",
    "snapshot_id",
}


# -------------------------------------------------------------------------------------------------
# OUTPUT
# -------------------------------------------------------------------------------------------------

def banner(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


# -------------------------------------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------------------------------------

def connect_read_only():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)

    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


# -------------------------------------------------------------------------------------------------
# FILE FINGERPRINT
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
# SCHEMA INTROSPECTION
# -------------------------------------------------------------------------------------------------

def get_schema(conn):

    rows = conn.execute(
        f"PRAGMA table_info({TARGET_TABLE})"
    ).fetchall()

    schema = {}

    for row in rows:
        # SQLite PRAGMA table_info:
        # cid, name, type, notnull, dflt_value, pk

        schema[row[1]] = {
            "type": row[2],
            "notnull": row[3],
            "default": row[4],
            "pk": row[5],
        }

    return schema


# -------------------------------------------------------------------------------------------------
# SAFE SELECT
# -------------------------------------------------------------------------------------------------

def load_rows(conn, columns):

    available = set(columns)

    preferred_order = [
        "id",
        "timestamp",
        "asset",
        "direction",
        "entry_price",
        "engine_version",
        "snapshot_id",
        "confidence",
        "regime",
        "score",
    ]

    selected = [
        column
        for column in preferred_order
        if column in available
    ]

    if "id" not in selected:
        raise RuntimeError("Cannot inspect rows: id column missing.")

    query_columns = ", ".join(selected)

    query = f"""
        SELECT {query_columns}
        FROM {TARGET_TABLE}
        ORDER BY id
    """

    raw_rows = conn.execute(query).fetchall()

    return selected, raw_rows


# -------------------------------------------------------------------------------------------------
# ROW OBJECTS
# -------------------------------------------------------------------------------------------------

def rows_to_dicts(columns, rows):

    return [
        dict(zip(columns, row))
        for row in rows
    ]


# -------------------------------------------------------------------------------------------------
# CONTRACT
# -------------------------------------------------------------------------------------------------

def check_required_columns(schema):

    available = set(schema)

    missing = REQUIRED_CONTRACT_COLUMNS - available

    if missing:
        return False, sorted(missing)

    return True, []


def report_optional_columns(schema):

    available = set(schema)

    for column in sorted(OPTIONAL_ANALYTICAL_COLUMNS):

        if column in available:
            print(
                f"{column:20} : PRESENT"
            )
        else:
            print(
                f"{column:20} : NOT PRESENT / NON-BLOCKING"
            )


# -------------------------------------------------------------------------------------------------
# IDENTITY
# -------------------------------------------------------------------------------------------------

def check_identity(rows):

    ids = [row.get("id") for row in rows]

    if len(ids) != len(set(ids)):
        return False, "Duplicate IDs detected."

    return True, "IDs unique."


# -------------------------------------------------------------------------------------------------
# DIRECTION
# -------------------------------------------------------------------------------------------------

def check_direction(rows):

    invalid = []

    for row in rows:

        direction = row.get("direction")

        if direction is None:
            invalid.append(
                (
                    row.get("id"),
                    row.get("asset"),
                    "NULL",
                )
            )
            continue

        normalized = str(direction).upper()

        if normalized not in VALID_DIRECTIONS:
            invalid.append(
                (
                    row.get("id"),
                    row.get("asset"),
                    direction,
                )
            )

    if invalid:
        return False, invalid

    return True, []


# -------------------------------------------------------------------------------------------------
# ENTRY PRICE
# -------------------------------------------------------------------------------------------------

def check_entry_price(rows):

    invalid = []

    for row in rows:

        entry = row.get("entry_price")

        if entry is None:

            invalid.append(
                (
                    row.get("id"),
                    row.get("asset"),
                    "NULL",
                )
            )

            continue

        try:

            value = float(entry)

            if value <= 0:

                invalid.append(
                    (
                        row.get("id"),
                        row.get("asset"),
                        value,
                    )
                )

        except Exception:

            invalid.append(
                (
                    row.get("id"),
                    row.get("asset"),
                    "NON_NUMERIC",
                )
            )

    if invalid:
        return False, invalid

    return True, []


# -------------------------------------------------------------------------------------------------
# OUTCOME INPUT READINESS
# -------------------------------------------------------------------------------------------------

def check_outcome_readiness(rows):

    failures = []

    for row in rows:

        required_for_outcome = [
            "timestamp",
            "asset",
            "direction",
            "entry_price",
            "engine_version",
        ]

        for field in required_for_outcome:

            if row.get(field) is None:

                failures.append(
                    (
                        row.get("id"),
                        row.get("asset"),
                        field,
                    )
                )

    return failures


# -------------------------------------------------------------------------------------------------
# UNIVERSE
# -------------------------------------------------------------------------------------------------

def analyze_universe(rows):

    assets = sorted(
        {
            str(row["asset"]).upper()
            for row in rows
            if row.get("asset") is not None
        }
    )

    return assets


# -------------------------------------------------------------------------------------------------
# ENGINE DISTRIBUTION
# -------------------------------------------------------------------------------------------------

def engine_distribution(rows):

    return Counter(
        row.get("engine_version")
        for row in rows
    )


# -------------------------------------------------------------------------------------------------
# DIRECTION DISTRIBUTION
# -------------------------------------------------------------------------------------------------

def direction_distribution(rows):

    return Counter(
        str(row.get("direction")).upper()
        for row in rows
        if row.get("direction") is not None
    )


# -------------------------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------------------------

def main():

    banner(
        "OUTCOME_v0.3 POST-REPAIR LAUNCH GATE v0.2"
    )

    print(f"Database       : {DB_PATH}")
    print(f"Target table   : {TARGET_TABLE}")

    print()
    print("MODE           : READ ONLY")
    print("PRODUCTION DB  : NEVER MODIFIED")
    print("ENGINE RUN     : NO")
    print()
    print("DESIGN:")
    print("  Gate adapts to the real production schema.")
    print("  Optional analytical fields do not block the gate.")
    print("  Current universe is NOT treated as final.")
    print("  No historical direction inference is performed.")
    print("  No live data is injected.")

    # ---------------------------------------------------------------------------------------------
    # SOURCE
    # ---------------------------------------------------------------------------------------------

    banner("SOURCE FINGERPRINT")

    fusion_path = os.path.join(
        PROJECT_ROOT,
        "fusion_engine.py"
    )

    if os.path.exists(fusion_path):

        print(
            f"fusion_engine.py SHA256 : "
            f"{sha256_file(fusion_path)}"
        )

    else:

        print(
            "fusion_engine.py : NOT FOUND"
        )

    # ---------------------------------------------------------------------------------------------
    # DATABASE
    # ---------------------------------------------------------------------------------------------

    conn = connect_read_only()

    try:

        # -----------------------------------------------------------------------------------------
        # REAL SCHEMA
        # -----------------------------------------------------------------------------------------

        banner("REAL PRODUCTION SCHEMA")

        schema = get_schema(conn)

        print(
            f"Columns discovered : {len(schema)}"
        )

        for name, info in schema.items():

            print(
                f"{name:25} | "
                f"type={info['type']!s:10} | "
                f"notnull={info['notnull']} | "
                f"pk={info['pk']}"
            )

        # -----------------------------------------------------------------------------------------
        # REQUIRED CONTRACT
        # -----------------------------------------------------------------------------------------

        banner("REQUIRED CONTRACT")

        schema_ok, missing = check_required_columns(
            schema
        )

        if schema_ok:

            print(
                "Required contract : PASS"
            )

        else:

            print(
                "Required contract : FAIL"
            )

            print(
                f"Missing columns  : {missing}"
            )

        # -----------------------------------------------------------------------------------------
        # OPTIONAL
        # -----------------------------------------------------------------------------------------

        banner(
            "OPTIONAL ANALYTICAL FIELDS"
        )

        report_optional_columns(schema)

        # -----------------------------------------------------------------------------------------
        # ROW LOAD
        # -----------------------------------------------------------------------------------------

        selected_columns, raw_rows = load_rows(
            conn,
            schema
        )

        rows = rows_to_dicts(
            selected_columns,
            raw_rows
        )

        # -----------------------------------------------------------------------------------------
        # BASELINE
        # -----------------------------------------------------------------------------------------

        banner(
            "POST-REPAIR DATABASE BASELINE"
        )

        total = len(rows)

        null_direction = sum(
            1
            for row in rows
            if row.get("direction") is None
        )

        valid_direction = total - null_direction

        print(
            f"Total rows       : {total}"
        )

        print(
            f"Valid direction  : {valid_direction}"
        )

        print(
            f"NULL direction   : {null_direction}"
        )

        # -----------------------------------------------------------------------------------------
        # IDENTITY
        # -----------------------------------------------------------------------------------------

        banner(
            "ROW IDENTITY CONTRACT"
        )

        identity_ok, identity_detail = check_identity(
            rows
        )

        print(
            f"Identity         : "
            f"{'PASS' if identity_ok else 'FAIL'}"
        )

        print(
            f"Detail           : "
            f"{identity_detail}"
        )

        # -----------------------------------------------------------------------------------------
        # DIRECTION
        # -----------------------------------------------------------------------------------------

        banner(
            "DIRECTION CONTRACT"
        )

        direction_ok, direction_detail = check_direction(
            rows
        )

        print(
            f"Direction        : "
            f"{'PASS' if direction_ok else 'FAIL'}"
        )

        if not direction_ok:

            for item in direction_detail[:30]:

                print(
                    f"  id={item[0]} "
                    f"asset={item[1]} "
                    f"value={item[2]}"
                )

        else:

            distribution = direction_distribution(
                rows
            )

            for direction, count in sorted(
                distribution.items()
            ):

                print(
                    f"  {direction:8} | {count}"
                )

        # -----------------------------------------------------------------------------------------
        # ENTRY
        # -----------------------------------------------------------------------------------------

        banner(
            "ENTRY PRICE CONTRACT"
        )

        entry_ok, entry_detail = check_entry_price(
            rows
        )

        print(
            f"Entry price      : "
            f"{'PASS' if entry_ok else 'FAIL'}"
        )

        if not entry_ok:

            for item in entry_detail[:30]:

                print(
                    f"  id={item[0]} "
                    f"asset={item[1]} "
                    f"value={item[2]}"
                )

        # -----------------------------------------------------------------------------------------
        # ENGINE
        # -----------------------------------------------------------------------------------------

        banner(
            "ENGINE VERSION DISTRIBUTION"
        )

        versions = engine_distribution(
            rows
        )

        for version, count in sorted(
            versions.items(),
            key=lambda x: str(x[0])
        ):

            print(
                f"{str(version):25} | {count}"
            )

        # -----------------------------------------------------------------------------------------
        # OUTCOME
        # -----------------------------------------------------------------------------------------

        banner(
            "OUTCOME INPUT READINESS"
        )

        outcome_failures = check_outcome_readiness(
            rows
        )

        outcome_ok = (
            len(outcome_failures) == 0
        )

        print(
            f"Outcome input contract : "
            f"{'PASS' if outcome_ok else 'FAIL'}"
        )

        if not outcome_ok:

            for item in outcome_failures[:30]:

                print(
                    f"  id={item[0]} "
                    f"asset={item[1]} "
                    f"field={item[2]}"
                )

        # -----------------------------------------------------------------------------------------
        # UNIVERSE
        # -----------------------------------------------------------------------------------------

        banner(
            "CURRENT UNIVERSE OBSERVATION"
        )

        assets = analyze_universe(
            rows
        )

        print(
            f"Assets represented : {len(assets)}"
        )

        print(
            f"Assets             : "
            f"{', '.join(assets)}"
        )

        print()
        print(
            "UNIVERSE STATUS    : NOT FINAL"
        )

        print(
            "Universe expansion : FUTURE FRONTIER"
        )

        print(
            "Launch completeness: NOT TESTED"
        )

        # -----------------------------------------------------------------------------------------
        # FINAL
        # -----------------------------------------------------------------------------------------

        banner(
            "POST-REPAIR LAUNCH GATE"
        )

        checks = {

            "SCHEMA_REQUIRED_CONTRACT":
                schema_ok,

            "ROW_IDENTITY":
                identity_ok,

            "DIRECTION_CONTRACT":
                direction_ok,

            "ENTRY_PRICE_CONTRACT":
                entry_ok,

            "OUTCOME_INPUT_READINESS":
                outcome_ok,

            "NO_NULL_DIRECTION":
                null_direction == 0,

        }

        for name, result in checks.items():

            print(
                f"{name:35} : "
                f"{'PASS' if result else 'FAIL'}"
            )

        overall = all(
            checks.values()
        )

        print()
        print(
            "=" * 100
        )

        if overall:

            print(
                "POST-REPAIR GATE : PASS"
            )

            print()
            print(
                "NEXT FRONTIER:"
            )

            print(
                "  1. OUTCOME PIPELINE"
            )

            print(
                "  2. LIVE MARKET CONNECTIVITY"
            )

            print(
                "  3. UNIVERSE EXPANSION"
            )

            print(
                "  4. FULL-SYSTEM LAUNCH READINESS"
            )

        else:

            print(
                "POST-REPAIR GATE : FAIL"
            )

            print()
            print(
                "Only the failed structural contract(s) "
                "require attention."
            )

        print(
            "=" * 100
        )

        # -----------------------------------------------------------------------------------------
        # SAFETY
        # -----------------------------------------------------------------------------------------

        banner(
            "FINAL SAFETY VERDICT"
        )

        print(
            "Production DB writes : NONE"
        )

        print(
            "INSERT               : NONE"
        )

        print(
            "UPDATE               : NONE"
        )

        print(
            "DELETE               : NONE"
        )

        print(
            "DDL                  : NONE"
        )

        print(
            "Production engine    : NOT EXECUTED"
        )

        print(
            "Historical repair    : NONE"
        )

        print(
            "Direction inference  : NONE"
        )

        print(
            "Synthetic data       : NONE"
        )

        print(
            "Live data injection  : NONE"
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()