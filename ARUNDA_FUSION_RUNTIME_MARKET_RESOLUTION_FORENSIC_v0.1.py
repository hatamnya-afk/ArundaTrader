# ============================================================================
# ARUNDA FUSION RUNTIME MARKET RESOLUTION FORENSIC v0.1
# ============================================================================
#
# PURPOSE:
#   Verify that the exact market resolution contract used by fusion_engine.py
#   can resolve consumable market_data rows at runtime.
#
# MODE:
#   READ ONLY
#
# WRITE OPERATIONS:
#   NONE
#   INSERT : NONE
#   UPDATE : NONE
#   DELETE : NONE
#   ALTER  : NONE
#   CREATE : NONE
#
# CONTRACT UNDER TEST:
#   source   = CMC_SNAPSHOT_ANALYSIS_v0.2
#   timeframe = SNAPSHOT
#   technical_score IS NOT NULL
#
# IMPORTANT:
#   This script does NOT modify fusion_engine.py.
#   This script does NOT modify the database.
#   This is a boundary-resolution test only.
# ============================================================================

import sqlite3
import sys
from datetime import datetime, timezone


# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

MARKET_SOURCE = "CMC_SNAPSHOT_ANALYSIS_v0.2"
MARKET_TIMEFRAME = "SNAPSHOT"

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]


# ============================================================================
# DATABASE
# ============================================================================

def connect_db():

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================================
# EXACT MARKET RESOLUTION CONTRACT
# ============================================================================
#
# This intentionally mirrors the query currently used by fusion_engine.py.
# ============================================================================

def get_latest_market(conn, asset):

    row = conn.execute(
        """
        SELECT *
        FROM market_data
        WHERE
            symbol = ?
            AND technical_score IS NOT NULL
            AND timeframe = ?
            AND source = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            asset,
            MARKET_TIMEFRAME,
            MARKET_SOURCE,
        ),
    ).fetchone()

    return row


# ============================================================================
# MAIN RUNTIME RESOLUTION TEST
# ============================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA FUSION RUNTIME MARKET RESOLUTION FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Started UTC       : "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    print(
        f"Database          : {DB_PATH}"
    )

    print(
        "Mode              : READ ONLY"
    )

    print(
        "Writes            : NONE"
    )

    print()

    print(
        "MARKET CONTRACT"
    )

    print(
        f"Source            : {MARKET_SOURCE}"
    )

    print(
        f"Timeframe         : {MARKET_TIMEFRAME}"
    )

    print(
        "Technical score    : IS NOT NULL"
    )

    print()

    conn = None

    try:

        conn = connect_db()

        print(
            "DATABASE CONNECTION : OK"
        )

        print()
        print(
            "-" * 90
        )

        found = 0
        not_found = 0

        resolved_assets = []
        unresolved_assets = []

        for asset in EXPECTED_ASSETS:

            market = get_latest_market(
                conn,
                asset,
            )

            if market is None:

                not_found += 1

                unresolved_assets.append(
                    asset
                )

                print(
                    f"[RUNTIME MARKET RESOLUTION] "
                    f"{asset:<8} -> NOT_FOUND"
                )

                continue

            found += 1

            resolved_assets.append(
                asset
            )

            print(
                f"[RUNTIME MARKET RESOLUTION] "
                f"{asset:<8} -> FOUND"
            )

            print(
                f"    id={market['id']} | "
                f"timestamp={market['timestamp']} | "
                f"source={market['source']} | "
                f"timeframe={market['timeframe']} | "
                f"technical_score={market['technical_score']} | "
                f"close={market['close']} | "
                f"engine={market['engine_version']}"
            )

        print()
        print(
            "-" * 90
        )

        print(
            "RUNTIME RESOLUTION SUMMARY"
        )

        print(
            f"Expected assets     : {len(EXPECTED_ASSETS)}"
        )

        print(
            f"FOUND               : {found}"
        )

        print(
            f"NOT_FOUND           : {not_found}"
        )

        print()

        if resolved_assets:

            print(
                "RESOLVED ASSETS"
            )

            print(
                ", ".join(
                    resolved_assets
                )
            )

            print()

        if unresolved_assets:

            print(
                "UNRESOLVED ASSETS"
            )

            print(
                ", ".join(
                    unresolved_assets
                )
            )

            print()

        # --------------------------------------------------------------------
        # CONTRACT-LEVEL DATABASE CHECK
        # --------------------------------------------------------------------

        contract_row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_rows,
                SUM(
                    CASE
                        WHEN technical_score IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS technical_ready
            FROM market_data
            WHERE
                source = ?
                AND timeframe = ?
            """,
            (
                MARKET_SOURCE,
                MARKET_TIMEFRAME,
            ),
        ).fetchone()

        print(
            "DATABASE CONTRACT CROSS-CHECK"
        )

        print(
            f"Matching rows       : "
            f"{contract_row['total_rows']}"
        )

        print(
            f"Technical ready     : "
            f"{contract_row['technical_ready'] or 0}"
        )

        print()

        # --------------------------------------------------------------------
        # FINAL VERDICT
        # --------------------------------------------------------------------

        if found == len(EXPECTED_ASSETS):

            print(
                "=" * 90
            )

            print(
                "VERDICT : RUNTIME MARKET RESOLUTION = READY"
            )

            print(
                "All expected assets resolved through the exact "
                "fusion market contract."
            )

            print(
                "=" * 90
            )

            return 0

        if found > 0:

            print(
                "=" * 90
            )

            print(
                "VERDICT : RUNTIME MARKET RESOLUTION = PARTIAL"
            )

            print(
                "Some assets resolve and some do not."
            )

            print(
                "=" * 90
            )

            return 2

        print(
            "=" * 90
        )

        print(
            "VERDICT : RUNTIME MARKET RESOLUTION = FAILED"
        )

        print(
            "No expected asset resolved through the exact "
            "fusion market contract."
        )

        print(
            "=" * 90
        )

        return 1

    except Exception as exc:

        print()
        print(
            "=" * 90
        )

        print(
            "VERDICT : FORENSIC TEST ERROR"
        )

        print(
            f"ERROR   : {type(exc).__name__}: {exc}"
        )

        print(
            "=" * 90
        )

        return 3

    finally:

        if conn is not None:

            conn.close()

            print()
            print(
                "DATABASE CONNECTION : CLOSED"
            )


# ============================================================================
# ENTRYPOINT
# ============================================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )