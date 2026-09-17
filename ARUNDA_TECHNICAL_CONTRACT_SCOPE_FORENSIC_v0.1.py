"""
ARUNDA TRADER
TECHNICAL CONTRACT SCOPE FORENSIC v0.1

MODE:
    READ ONLY

PURPOSE:
    Forensically verify that TECHNICAL_CONTRACT_v0.6
    selects exactly the trusted 987-record population.

NO:
    INSERT
    UPDATE
    DELETE
    ALTER
    CREATE
    DROP
    COMMIT
    VACUUM
    REINDEX
    NETWORK
    PRODUCTION MODULE EXECUTION
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path


# ============================================================================
# CONFIG
# ============================================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

EXPECTED_TOTAL = 6909
EXPECTED_IN_SCOPE = 987
EXPECTED_OUT_OF_SCOPE = 5922
EXPECTED_INVALID = 0

TRUSTED_HISTORY_POINTS = 200
TRUSTED_SOURCE = "REAL_MARKET_HISTORY"
TRUSTED_TECHNICAL_VERSION = "TECHNICAL_v0.5"
TRUSTED_ENGINE_VERSION = "TECHNICAL_v0.5"


# ============================================================================
# READ ONLY DB
# ============================================================================

def connect_read_only() -> sqlite3.Connection:
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


# ============================================================================
# EXACT CONTRACT SCOPE PREDICATE
# ============================================================================

def scope_condition_sql() -> str:
    return """
        symbol IS NOT NULL
        AND history_points = 200
        AND price IS NOT NULL
        AND close IS NOT NULL
        AND volatility IS NOT NULL
        AND volatility_20 IS NOT NULL
        AND regime IS NOT NULL
        AND technical_available IS NOT NULL
        AND technical_completeness IS NOT NULL
        AND technical_version = ?
        AND engine_version = ?
        AND source = ?
    """


# ============================================================================
# FORENSIC
# ============================================================================

def main() -> None:

    print("=" * 100)
    print("TECHNICAL CONTRACT SCOPE FORENSIC v0.1")
    print("=" * 100)

    print(f"MODE                 : READ ONLY")
    print(f"DATABASE             : {DB_PATH}")
    print(f"WRITE OPERATIONS     : NONE")
    print(f"PRODUCTION EXECUTION : NONE")
    print(f"NETWORK              : NONE")
    print()

    conn = connect_read_only()

    try:

        # --------------------------------------------------------------------
        # TABLE EXISTENCE
        # --------------------------------------------------------------------

        table = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'market_technical'
        """).fetchone()

        if not table:
            raise RuntimeError("market_technical table not found")

        print("[PASS] market_technical exists")
        print()

        # --------------------------------------------------------------------
        # TOTAL
        # --------------------------------------------------------------------

        total = conn.execute("""
            SELECT COUNT(*)
            FROM market_technical
        """).fetchone()[0]

        print("TOTAL RECORDS")
        print(f"  ACTUAL   : {total}")
        print(f"  EXPECTED : {EXPECTED_TOTAL}")
        print(f"  STATUS   : {'PASS' if total == EXPECTED_TOTAL else 'FAIL'}")
        print()

        # --------------------------------------------------------------------
        # EXACT TRUSTED SCOPE
        # --------------------------------------------------------------------

        condition = scope_condition_sql()
        params = (
            TRUSTED_TECHNICAL_VERSION,
            TRUSTED_ENGINE_VERSION,
            TRUSTED_SOURCE,
        )

        in_scope = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM market_technical
            WHERE {condition}
            """,
            params,
        ).fetchone()[0]

        print("IN-SCOPE")
        print(f"  ACTUAL   : {in_scope}")
        print(f"  EXPECTED : {EXPECTED_IN_SCOPE}")
        print(f"  STATUS   : {'PASS' if in_scope == EXPECTED_IN_SCOPE else 'FAIL'}")
        print()

        # --------------------------------------------------------------------
        # OUT OF SCOPE
        # --------------------------------------------------------------------

        out_scope = total - in_scope

        print("OUT-OF-SCOPE")
        print(f"  ACTUAL   : {out_scope}")
        print(f"  EXPECTED : {EXPECTED_OUT_OF_SCOPE}")
        print(f"  STATUS   : {'PASS' if out_scope == EXPECTED_OUT_OF_SCOPE else 'FAIL'}")
        print()

        # --------------------------------------------------------------------
        # IN-SCOPE FINGERPRINT
        # --------------------------------------------------------------------

        print("-" * 100)
        print("IN-SCOPE CONTRACT FINGERPRINT")
        print("-" * 100)

        fingerprint_sql = """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN history_points IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN price IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN close IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN volatility IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN volatility_20 IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN regime IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN technical_available IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN technical_completeness IS NOT NULL THEN 1 ELSE 0 END)
            FROM market_technical
            WHERE
                history_points = 200
                AND price IS NOT NULL
                AND close IS NOT NULL
                AND volatility IS NOT NULL
                AND volatility_20 IS NOT NULL
                AND regime IS NOT NULL
                AND technical_available IS NOT NULL
                AND technical_completeness IS NOT NULL
                AND technical_version = ?
                AND engine_version = ?
                AND source = ?
        """

        fp = conn.execute(
            fingerprint_sql,
            params,
        ).fetchone()

        labels = [
            "TOTAL",
            "HISTORY",
            "PRICE",
            "CLOSE",
            "VOLATILITY",
            "VOLATILITY_20",
            "REGIME",
            "TECHNICAL_AVAILABLE",
            "TECHNICAL_COMPLETENESS",
        ]

        for label, value in zip(labels, fp):
            print(f"{label:<25}: {value}")

        print()

        # --------------------------------------------------------------------
        # VERSION / SOURCE CROSS CHECK
        # --------------------------------------------------------------------

        print("-" * 100)
        print("TRUSTED VERSION / SOURCE CROSS CHECK")
        print("-" * 100)

        checks = [
            (
                "technical_version",
                TRUSTED_TECHNICAL_VERSION,
            ),
            (
                "engine_version",
                TRUSTED_ENGINE_VERSION,
            ),
            (
                "source",
                TRUSTED_SOURCE,
            ),
        ]

        for field, expected in checks:

            rows = conn.execute(
                f"""
                SELECT {field}, COUNT(*)
                FROM market_technical
                WHERE {condition}
                GROUP BY {field}
                ORDER BY COUNT(*) DESC
                """,
                params,
            ).fetchall()

            print(f"\n{field}:")

            for value, count in rows:
                print(f"  {value!r:<35} {count}")

        print()

        # --------------------------------------------------------------------
        # OUT-OF-SCOPE DISTRIBUTION
        # --------------------------------------------------------------------

        print("-" * 100)
        print("OUT-OF-SCOPE DISTRIBUTION")
        print("-" * 100)

        rows = conn.execute(
            f"""
            SELECT
                CASE
                    WHEN history_points IS NULL
                         AND price IS NULL
                         AND close IS NOT NULL
                         AND engine_version = 'MARKET_TECHNICAL_CMC_v0.2'
                        THEN 'PRE_CONTRACT_OR_FOREIGN_HISTORY_SHAPE'

                    WHEN history_points IS NULL
                         AND price IS NOT NULL
                         AND close IS NULL
                        THEN 'OUT_OF_SCOPE_NO_HISTORY_CONTEXT'

                    ELSE 'OUT_OF_SCOPE_OTHER'
                END AS family,
                COUNT(*)
            FROM market_technical
            WHERE NOT ({condition})
            GROUP BY family
            ORDER BY COUNT(*) DESC
            """,
            params,
        ).fetchall()

        for family, count in rows:
            print(f"{family:<55}: {count}")

        print()

        # --------------------------------------------------------------------
        # INVALID CHECK
        #
        # Important:
        # OUT_OF_SCOPE records are NOT invalid.
        # We only validate the 987 in-scope records.
        # --------------------------------------------------------------------

        print("-" * 100)
        print("IN-SCOPE INVALIDITY CHECK")
        print("-" * 100)

        invalid_rows = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM market_technical
            WHERE {condition}
              AND (
                    price <= 0
                    OR close <= 0
                    OR history_points < 200
                    OR technical_completeness < 0
                    OR technical_completeness > 1
                    OR technical_available NOT IN (0, 1)
                  )
            """,
            params,
        ).fetchone()[0]

        print(f"IN-SCOPE INVALID : {invalid_rows}")
        print(f"EXPECTED         : {EXPECTED_INVALID}")
        print(
            f"STATUS           : "
            f"{'PASS' if invalid_rows == EXPECTED_INVALID else 'FAIL'}"
        )
        print()

        # --------------------------------------------------------------------
        # ID RANGE / DENSITY EVIDENCE
        # --------------------------------------------------------------------

        print("-" * 100)
        print("IN-SCOPE ID DISTRIBUTION")
        print("-" * 100)

        id_stats = conn.execute(
            f"""
            SELECT
                MIN(id),
                MAX(id),
                COUNT(DISTINCT id)
            FROM market_technical
            WHERE {condition}
            """,
            params,
        ).fetchone()

        print(f"MIN ID           : {id_stats[0]}")
        print(f"MAX ID           : {id_stats[1]}")
        print(f"DISTINCT IDS     : {id_stats[2]}")
        print()

        # --------------------------------------------------------------------
        # FINAL
        # --------------------------------------------------------------------

        checks = {
            "TOTAL": total == EXPECTED_TOTAL,
            "IN_SCOPE": in_scope == EXPECTED_IN_SCOPE,
            "OUT_OF_SCOPE": out_scope == EXPECTED_OUT_OF_SCOPE,
            "INVALID": invalid_rows == EXPECTED_INVALID,
            "CONSERVATION": (
                in_scope + out_scope == total
                and EXPECTED_IN_SCOPE + EXPECTED_OUT_OF_SCOPE
                == EXPECTED_TOTAL
            ),
        }

        print("=" * 100)
        print("FINAL CONTRACT SCOPE FORENSIC")
        print("=" * 100)

        for name, status in checks.items():
            print(f"{name:<25}: {'PASS' if status else 'FAIL'}")

        final_status = all(checks.values())

        print()
        print(
            f"FINAL STATUS           : "
            f"{'PASS' if final_status else 'FAIL'}"
        )

        if final_status:
            print()
            print("CONTRACT SCOPE VERIFIED")
            print("987 records are IN-SCOPE.")
            print("5922 records are OUT-OF-SCOPE and MUST be ignored.")
            print("OUT-OF-SCOPE != INVALID.")
        else:
            print()
            print("CONTRACT SCOPE NOT VERIFIED")
            print("DO NOT CONNECT CONTRACT v0.6 TO VALIDATOR.")

    finally:
        conn.close()

    print()
    print("=" * 100)
    print("READ-ONLY FORENSIC COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()