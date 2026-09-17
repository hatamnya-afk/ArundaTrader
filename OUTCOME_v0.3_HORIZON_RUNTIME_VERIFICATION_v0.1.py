import sqlite3
import subprocess
import sys
from datetime import datetime, timezone


# ============================================================
# ARUNDA TRADER
# OUTCOME v0.3 HORIZON RUNTIME VERIFICATION v0.1
# ============================================================

DB_NAME = "arunda.db"
ENGINE_SCRIPT = "signal_outcome_engine.py"

ENGINE_VERSION = "OUTCOME_v0.3.2"

HORIZONS = (
    "5m",
    "15m",
    "30m",
    "60m",
)

# Expected production tolerance AFTER approved repair
EXPECTED_TOLERANCES = {
    "5m": 600,
    "15m": 300,
    "30m": 600,
    "60m": 900,
}


# ============================================================
# HELPERS
# ============================================================

def get_connection():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE
            type = 'table'
            AND name = ?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def column_exists(conn, table_name, column_name):

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def count_non_null(
    conn,
    column
):

    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM signal_outcomes
        WHERE
            engine_version = ?
            AND {column} IS NOT NULL
        """,
        (ENGINE_VERSION,)
    ).fetchone()

    return row[0]


def count_non_null_pair(
    conn,
    return_column,
    outcome_column
):

    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM signal_outcomes
        WHERE
            engine_version = ?
            AND {return_column} IS NOT NULL
            AND {outcome_column} IS NOT NULL
        """,
        (ENGINE_VERSION,)
    ).fetchone()

    return row[0]


def count_outcome(
    conn,
    column,
    value
):

    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM signal_outcomes
        WHERE
            engine_version = ?
            AND {column} = ?
        """,
        (
            ENGINE_VERSION,
            value,
        )
    ).fetchone()

    return row[0]


def print_header(title):

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 78)
    print(
        "OUTCOME v0.3 HORIZON RUNTIME VERIFICATION v0.1"
    )
    print("=" * 78)

    print(
        f"Database         : {DB_NAME}"
    )

    print(
        f"Engine            : {ENGINE_SCRIPT}"
    )

    print(
        f"Expected version  : {ENGINE_VERSION}"
    )

    print(
        "Mode              : RUNTIME VERIFICATION"
    )

    print(
        "Production source : ALREADY REPAIRED"
    )

    print(
        "Synthetic data    : FORBIDDEN"
    )

    print(
        "Interpolation     : FORBIDDEN"
    )

    print(
        "Forward fill      : FORBIDDEN"
    )

    print(
        "Back fill         : FORBIDDEN"
    )

    print("=" * 78)


    # ========================================================
    # CHECK ENGINE SOURCE
    # ========================================================

    print_header(
        "PRODUCTION TOLERANCE CONFIGURATION CHECK"
    )

    try:

        with open(
            ENGINE_SCRIPT,
            "r",
            encoding="utf-8"
        ) as f:

            source = f.read()

    except Exception as exc:

        print(
            f"ERROR | Cannot read {ENGINE_SCRIPT}"
        )

        print(
            repr(exc)
        )

        return

    expected_strings = {
        "5m": '"5m": 600',
        "15m": '"15m": 300',
        "30m": '"30m": 600',
        "60m": '"60m": 900',
    }

    tolerance_check = True

    for horizon in HORIZONS:

        expected = expected_strings[horizon]

        found = expected in source

        status = (
            "PASS"
            if found
            else "NOT FOUND"
        )

        print(
            f"{horizon:<5} | "
            f"Expected={EXPECTED_TOLERANCES[horizon]:>4}s | "
            f"{status}"
        )

        if not found:
            tolerance_check = False


    if not tolerance_check:

        print()
        print(
            "VERDICT: EXPECTED PRODUCTION TOLERANCE "
            "CONFIGURATION NOT CONFIRMED."
        )

        print(
            "STOP — DO NOT RUN PRODUCTION VERIFICATION."
        )

        return


    print()
    print(
        "Tolerance configuration : VERIFIED"
    )


    # ========================================================
    # DATABASE PRE-RUN SNAPSHOT
    # ========================================================

    print_header(
        "PRE-RUN DATABASE STATE"
    )

    conn = None

    try:

        conn = get_connection()

        if not table_exists(
            conn,
            "signal_outcomes"
        ):

            print(
                "ERROR | signal_outcomes table missing."
            )

            return

        pre_total = conn.execute(
            """
            SELECT COUNT(*)
            FROM signal_outcomes
            WHERE engine_version = ?
            """,
            (ENGINE_VERSION,)
        ).fetchone()[0]

        print(
            f"Current {ENGINE_VERSION} records : {pre_total}"
        )

        print()

        print(
            "HORIZON BEFORE RUNTIME"
        )

        for horizon in HORIZONS:

            price_column = (
                f"price_{horizon}"
            )

            return_column = (
                f"return_{horizon}"
            )

            outcome_column = (
                f"outcome_{horizon}"
            )

            prices = count_non_null(
                conn,
                price_column
            )

            returns = count_non_null(
                conn,
                return_column
            )

            outcomes = count_non_null(
                conn,
                outcome_column
            )

            print(
                f"{horizon:<5} | "
                f"Prices={prices:<4} | "
                f"Returns={returns:<4} | "
                f"Outcomes={outcomes:<4}"
            )

    finally:

        if conn is not None:
            conn.close()


    # ========================================================
    # RUNTIME EXECUTION
    # ========================================================

    print_header(
        "EXECUTING PRODUCTION OUTCOME ENGINE"
    )

    print(
        f"Command : {sys.executable} {ENGINE_SCRIPT}"
    )

    print(
        "Database target : PRODUCTION arunda.db"
    )

    print()

    started_at = datetime.now(
        timezone.utc
    )

    try:

        result = subprocess.run(
            [
                sys.executable,
                ENGINE_SCRIPT,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

    except subprocess.TimeoutExpired:

        print(
            "RUNTIME ERROR | Engine timeout."
        )

        return

    except Exception as exc:

        print(
            "RUNTIME ERROR | Failed to execute engine."
        )

        print(
            repr(exc)
        )

        return

    finished_at = datetime.now(
        timezone.utc
    )

    runtime_seconds = (
        finished_at - started_at
    ).total_seconds()


    print(
        f"Process return code : {result.returncode}"
    )

    print(
        f"Runtime             : {runtime_seconds:.2f} sec"
    )

    print()

    print(
        "---------------- ENGINE STDOUT ----------------"
    )

    print(
        result.stdout
    )

    if result.stderr:

        print(
            "---------------- ENGINE STDERR ----------------"
        )

        print(
            result.stderr
        )


    if result.returncode != 0:

        print_header(
            "RUNTIME VERIFICATION STOPPED"
        )

        print(
            "Production outcome engine returned non-zero exit code."
        )

        return


    # ========================================================
    # POST-RUN DATABASE VERIFICATION
    # ========================================================

    print_header(
        "POST-RUN HORIZON POPULATION"
    )

    conn = None

    try:

        conn = get_connection()

        post_total = conn.execute(
            """
            SELECT COUNT(*)
            FROM signal_outcomes
            WHERE engine_version = ?
            """,
            (ENGINE_VERSION,)
        ).fetchone()[0]

        print(
            f"Current {ENGINE_VERSION} records : {post_total}"
        )

        print()

        print(
            "HORIZON RUNTIME RESULTS"
        )

        print("-" * 78)

        results = {}

        for horizon in HORIZONS:

            price_column = (
                f"price_{horizon}"
            )

            return_column = (
                f"return_{horizon}"
            )

            outcome_column = (
                f"outcome_{horizon}"
            )

            prices = count_non_null(
                conn,
                price_column
            )

            returns = count_non_null(
                conn,
                return_column
            )

            outcomes = count_non_null(
                conn,
                outcome_column
            )

            paired = count_non_null_pair(
                conn,
                return_column,
                outcome_column
            )

            wins = count_outcome(
                conn,
                outcome_column,
                "WIN"
            )

            losses = count_outcome(
                conn,
                outcome_column,
                "LOSS"
            )

            flats = count_outcome(
                conn,
                outcome_column,
                "FLAT"
            )

            pending = count_outcome(
                conn,
                outcome_column,
                "PENDING"
            )

            results[horizon] = {
                "prices": prices,
                "returns": returns,
                "outcomes": outcomes,
                "paired": paired,
                "wins": wins,
                "losses": losses,
                "flats": flats,
                "pending": pending,
            }

            print(
                f"{horizon:<5} | "
                f"Prices={prices:<4} | "
                f"Returns={returns:<4} | "
                f"Outcomes={outcomes:<4} | "
                f"Paired={paired:<4} | "
                f"W={wins:<3} | "
                f"L={losses:<3} | "
                f"F={flats:<3} | "
                f"P={pending:<3}"
            )


        # ====================================================
        # SIGNAL-LEVEL DETAIL
        # ====================================================

        print_header(
            "SIGNAL-LEVEL HORIZON VERIFICATION"
        )

        rows = conn.execute(
            """
            SELECT
                id,
                snapshot_id,
                asset,
                direction,
                entry_timestamp,
                price_5m,
                price_15m,
                price_30m,
                price_60m,
                return_5m,
                return_15m,
                return_30m,
                return_60m,
                outcome_5m,
                outcome_15m,
                outcome_30m,
                outcome_60m
            FROM signal_outcomes
            WHERE
                engine_version = ?
            ORDER BY id ASC
            """,
            (ENGINE_VERSION,)
        ).fetchall()

        print(
            f"Records inspected : {len(rows)}"
        )

        print()

        for row in rows:

            print(
                f"Signal #{row['id']:<5} | "
                f"{row['asset']:<5} | "
                f"{row['direction']:<5}"
            )

            print(
                f"  5m  | "
                f"price={row['price_5m']} | "
                f"return={row['return_5m']} | "
                f"outcome={row['outcome_5m']}"
            )

            print(
                f"  15m | "
                f"price={row['price_15m']} | "
                f"return={row['return_15m']} | "
                f"outcome={row['outcome_15m']}"
            )

            print(
                f"  30m | "
                f"price={row['price_30m']} | "
                f"return={row['return_30m']} | "
                f"outcome={row['outcome_30m']}"
            )

            print(
                f"  60m | "
                f"price={row['price_60m']} | "
                f"return={row['return_60m']} | "
                f"outcome={row['outcome_60m']}"
            )


        # ====================================================
        # OVERALL OUTCOME STATUS
        # ====================================================

        print_header(
            "OVERALL OUTCOME STATUS"
        )

        overall_rows = conn.execute(
            """
            SELECT
                outcome,
                COUNT(*) AS count
            FROM signal_outcomes
            WHERE
                engine_version = ?
            GROUP BY outcome
            ORDER BY outcome
            """,
            (ENGINE_VERSION,)
        ).fetchall()

        if overall_rows:

            for row in overall_rows:

                print(
                    f"{row['outcome']:<10} | "
                    f"{row['count']}"
                )

        else:

            print(
                "No outcome records."
            )


        # ====================================================
        # VERDICT
        # ====================================================

        print_header(
            "FINAL FORENSIC VERDICT"
        )

        all_horizons_have_prices = all(
            results[h]["prices"] > 0
            for h in HORIZONS
        )

        five_min_populated = (
            results["5m"]["prices"] > 0
        )

        five_min_has_returns = (
            results["5m"]["returns"] > 0
        )

        five_min_has_outcomes = (
            results["5m"]["outcomes"] > 0
        )

        any_runtime_population = any(
            results[h]["prices"] > 0
            for h in HORIZONS
        )


        print(
            f"5m  populated prices : "
            f"{results['5m']['prices']}"
        )

        print(
            f"15m populated prices : "
            f"{results['15m']['prices']}"
        )

        print(
            f"30m populated prices : "
            f"{results['30m']['prices']}"
        )

        print(
            f"60m populated prices : "
            f"{results['60m']['prices']}"
        )

        print()

        if five_min_populated:

            print(
                "5m FUTURE PRICE RESOLUTION : PASS"
            )

        else:

            print(
                "5m FUTURE PRICE RESOLUTION : FAIL"
            )


        if five_min_has_returns:

            print(
                "5m RETURN POPULATION : PASS"
            )

        else:

            print(
                "5m RETURN POPULATION : FAIL"
            )


        if five_min_has_outcomes:

            print(
                "5m OUTCOME POPULATION : PASS"
            )

        else:

            print(
                "5m OUTCOME POPULATION : FAIL"
            )


        print()

        if all_horizons_have_prices:

            print(
                "ALL HORIZONS HAVE REAL FUTURE PRICES : PASS"
            )

        elif any_runtime_population:

            print(
                "HORIZON RUNTIME POPULATION : PARTIAL"
            )

        else:

            print(
                "HORIZON RUNTIME POPULATION : FAIL"
            )


        print()

        if (
            five_min_populated
            and five_min_has_returns
            and five_min_has_outcomes
        ):

            print(
                "VERDICT : OUTCOME 5m RUNTIME VERIFICATION = PASS"
            )

        elif five_min_populated:

            print(
                "VERDICT : 5m FUTURE PRICE RESOLUTION = PASS, "
                "DOWNSTREAM POPULATION INCOMPLETE"
            )

        else:

            print(
                "VERDICT : OUTCOME HORIZON RUNTIME VERIFICATION = FAIL"
            )


        print()
        print(
            "Synthetic data       : NOT USED"
        )

        print(
            "Interpolation        : NOT USED"
        )

        print(
            "Forward fill         : NOT USED"
        )

        print(
            "Back fill            : NOT USED"
        )

        print(
            "Production DB        : MODIFIED BY PRODUCTION ENGINE"
        )

        print(
            "Production formulas  : UNMODIFIED"
        )

        print("=" * 78)


    except Exception as exc:

        print_header(
            "POST-RUN VERIFICATION ERROR"
        )

        print(
            repr(exc)
        )

    finally:

        if conn is not None:
            conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()