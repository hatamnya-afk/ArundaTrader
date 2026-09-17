import sqlite3
from pathlib import Path
from statistics import mean

# ============================================================
# ARUNDA
# INDICATOR STANDARD CONVENTION COMPARISON AUDIT v0.1
# ============================================================
#
# MODE              : READ ONLY
# DATABASE WRITE    : NONE
# FORMULA WRITE     : NONE
# PURPOSE           : CURRENT IMPLEMENTATION vs STANDARD
#                     CONVENTION COMPARISON
#
# TARGET INDICATORS :
#   EMA20
#   EMA50
#   RSI14
#
# STANDARD:
#   EMA = alpha 2/(period+1)
#   EMA seed = SMA(first period values)
#   EMA recursive smoothing
#
#   RSI14 = Wilder RSI
#   Initial gain/loss = arithmetic mean
#   Subsequent gain/loss = Wilder smoothing
#
# ============================================================


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

LOOKBACK = 120
MIN_HISTORY = 60

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10

EXPECTED_ENGINE = "MARKET_DATA_CMC_SNAPSHOT_v0.2"


# ============================================================
# OUTPUT HELPERS
# ============================================================

def divider(char="=", width=99):
    print(char * width)


def section(title):
    print()
    divider("=")
    print(title)
    divider("=")


# ============================================================
# NUMERIC COMPARISON
# ============================================================

def relative_error(current, standard):
    if current is None or standard is None:
        return None

    denominator = max(abs(current), abs(standard), 1e-300)

    return abs(current - standard) / denominator


def absolute_error(current, standard):
    if current is None or standard is None:
        return None

    return abs(current - standard)


def compare_values(current, standard):
    if current is None or standard is None:
        return "UNRESOLVED"

    abs_err = absolute_error(current, standard)
    rel_err = relative_error(current, standard)

    if abs_err <= ABS_TOLERANCE:
        return "EXACT"

    if rel_err <= REL_TOLERANCE:
        return "MATCH"

    return "MISMATCH"


# ============================================================
# STANDARD EMA
# ============================================================

def standard_ema(values, period):
    """
    Standard EMA convention:

        alpha = 2 / (period + 1)

    Initial seed:
        SMA(first period values)

    Recursive:
        EMA_t = alpha * price_t
                + (1-alpha) * EMA_(t-1)
    """

    if values is None:
        return None

    if len(values) < period:
        return None

    seed = mean(values[:period])

    alpha = 2.0 / (period + 1.0)

    ema_value = seed

    for value in values[period:]:
        ema_value = (
            alpha * value
            + (1.0 - alpha) * ema_value
        )

    return ema_value


# ============================================================
# STANDARD WILDER RSI
# ============================================================

def standard_rsi(values, period=14):
    """
    Wilder RSI convention.

    Step 1:
        Calculate sequential changes.

    Step 2:
        Separate gains and losses.

    Step 3:
        Initial average gain/loss:
            arithmetic mean over first period changes.

    Step 4:
        Subsequent values use Wilder smoothing:

            avg_gain =
                ((prev_avg_gain * (period-1)) + gain) / period

            avg_loss =
                ((prev_avg_loss * (period-1)) + loss) / period

    Step 5:
        RS = avg_gain / avg_loss

        RSI = 100 - 100 / (1 + RS)
    """

    if values is None:
        return None

    if len(values) < period + 1:
        return None

    changes = []

    for i in range(1, len(values)):
        changes.append(values[i] - values[i - 1])

    gains = []
    losses = []

    for change in changes:
        if change > 0:
            gains.append(change)
            losses.append(0.0)

        elif change < 0:
            gains.append(0.0)
            losses.append(abs(change))

        else:
            gains.append(0.0)
            losses.append(0.0)

    if len(gains) < period:
        return None

    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])

    for i in range(period, len(gains)):
        gain = gains[i]
        loss = losses[i]

        avg_gain = (
            ((avg_gain * (period - 1)) + gain)
            / period
        )

        avg_loss = (
            ((avg_loss * (period - 1)) + loss)
            / period
        )

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (
        100.0 / (1.0 + rs)
    )


# ============================================================
# DATABASE SCHEMA
# ============================================================

def get_columns(conn, table_name):

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {row[1] for row in rows}


# ============================================================
# TARGET RESOLUTION
# ============================================================

def resolve_target(conn, symbol):

    query = """
        SELECT
            id,
            symbol,
            source_timestamp,
            engine_version,
            close,
            ema20,
            ema50,
            rsi14
        FROM market_data
        WHERE symbol = ?
          AND ema20 IS NOT NULL
          AND ema50 IS NOT NULL
          AND rsi14 IS NOT NULL
          AND engine_version = ?
        ORDER BY source_timestamp DESC, id DESC
        LIMIT 1
    """

    return conn.execute(
        query,
        (
            symbol,
            EXPECTED_ENGINE,
        )
    ).fetchone()


# ============================================================
# HISTORY RESOLUTION
# ============================================================

def load_history(conn, symbol, target_timestamp):

    query = """
        SELECT
            source_timestamp,
            close
        FROM market_data
        WHERE symbol = ?
          AND source_timestamp <= ?
          AND close IS NOT NULL
        ORDER BY source_timestamp ASC, id ASC
        LIMIT ?
    """

    rows = conn.execute(
        query,
        (
            symbol,
            target_timestamp,
            LOOKBACK,
        )
    ).fetchall()

    return rows


# ============================================================
# SYMBOL COMPARISON
# ============================================================

def compare_symbol(conn, symbol):

    print()
    divider("=")
    print(f"SYMBOL : {symbol}")
    divider("-")

    target = resolve_target(conn, symbol)

    if target is None:

        print("ANALYSIS TARGET    : NOT FOUND")
        print("TARGET STATUS      : BLOCKED")
        print("REASON             : VALID_TARGET_NOT_FOUND")

        return {
            "symbol": symbol,
            "status": "BLOCKED",
            "exact": 0,
            "match": 0,
            "mismatch": 0,
            "unresolved": 3,
        }

    (
        analysis_id,
        db_symbol,
        source_timestamp,
        engine_version,
        close,
        current_ema20,
        current_ema50,
        current_rsi14,
    ) = target

    print("ANALYSIS TARGET    : FOUND")
    print("Analysis ID        :", analysis_id)
    print("Source Time        :", source_timestamp)
    print("Engine Version     :", engine_version)
    print("Stored Close       :", close)

    print()
    print("CURRENT IMPLEMENTATION")
    divider("-")

    print("Current EMA20      :", current_ema20)
    print("Current EMA50      :", current_ema50)
    print("Current RSI14      :", current_rsi14)

    history_rows = load_history(
        conn,
        symbol,
        source_timestamp,
    )

    history_count = len(history_rows)

    print()
    print("HISTORY RESOLUTION")
    divider("-")

    print("Requested Lookback :", LOOKBACK)
    print("History Found      :", history_count)

    if history_count > 0:

        print("History First      :", history_rows[0][0])
        print("History Last       :", history_rows[-1][0])

    if history_count < MIN_HISTORY:

        print()
        print("TARGET STATUS      : BLOCKED")
        print(
            "REASON             : "
            f"INSUFFICIENT_HISTORY_{history_count}"
        )

        return {
            "symbol": symbol,
            "status": "BLOCKED",
            "exact": 0,
            "match": 0,
            "mismatch": 0,
            "unresolved": 3,
        }

    closes = [
        float(row[1])
        for row in history_rows
        if row[1] is not None
    ]

    if len(closes) < MIN_HISTORY:

        print()
        print("TARGET STATUS      : BLOCKED")
        print("REASON             : INSUFFICIENT_CLOSE_VALUES")

        return {
            "symbol": symbol,
            "status": "BLOCKED",
            "exact": 0,
            "match": 0,
            "mismatch": 0,
            "unresolved": 3,
        }

    # --------------------------------------------------------
    # STANDARD RECONSTRUCTION
    # --------------------------------------------------------

    standard_ema20 = standard_ema(
        closes,
        20,
    )

    standard_ema50 = standard_ema(
        closes,
        50,
    )

    standard_rsi14 = standard_rsi(
        closes,
        14,
    )

    print()
    print("STANDARD CONVENTION RECONSTRUCTION")
    divider("-")

    print("Standard EMA20     :", standard_ema20)
    print("Standard EMA50     :", standard_ema50)
    print("Standard RSI14     :", standard_rsi14)

    print()
    print("CURRENT IMPLEMENTATION vs STANDARD CONVENTION")
    divider("-")

    indicators = [
        (
            "EMA20",
            current_ema20,
            standard_ema20,
        ),
        (
            "EMA50",
            current_ema50,
            standard_ema50,
        ),
        (
            "RSI14",
            current_rsi14,
            standard_rsi14,
        ),
    ]

    exact = 0
    match = 0
    mismatch = 0
    unresolved = 0

    for name, current, standard in indicators:

        abs_err = absolute_error(
            current,
            standard,
        )

        rel_err = relative_error(
            current,
            standard,
        )

        status = compare_values(
            current,
            standard,
        )

        if status == "EXACT":
            exact += 1

        elif status == "MATCH":
            match += 1

        elif status == "MISMATCH":
            mismatch += 1

        else:
            unresolved += 1

        print()
        print("INDICATOR :", name)
        print("CURRENT   :", current)
        print("STANDARD  :", standard)
        print("ABS ERR   :", abs_err)
        print("REL ERR   :", rel_err)
        print("STATUS    :", status)

    print()
    print("SYMBOL SUMMARY")
    print(
        f"  EXACT      : {exact}"
    )
    print(
        f"  MATCH      : {match}"
    )
    print(
        f"  MISMATCH   : {mismatch}"
    )
    print(
        f"  UNRESOLVED : {unresolved}"
    )

    if unresolved > 0:
        symbol_status = "UNRESOLVED"

    elif mismatch > 0:
        symbol_status = "MISMATCH"

    else:
        symbol_status = "CONFORMANT"

    print("SYMBOL STATUS :", symbol_status)

    return {
        "symbol": symbol,
        "status": symbol_status,
        "exact": exact,
        "match": match,
        "mismatch": mismatch,
        "unresolved": unresolved,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    section(
        "ARUNDA INDICATOR STANDARD CONVENTION "
        "COMPARISON AUDIT v0.1"
    )

    print("MODE              : READ ONLY")
    print("DATABASE           : arunda.db")
    print("DATABASE WRITE     : NONE")
    print("FORMULA WRITE      : NONE")
    print("LOOKBACK           :", LOOKBACK)
    print("MIN HISTORY        :", MIN_HISTORY)
    print("ABS TOLERANCE      :", ABS_TOLERANCE)
    print("REL TOLERANCE      :", REL_TOLERANCE)

    section("STANDARD CONVENTIONS")

    print(
        "EMA20 / EMA50      : "
        "alpha = 2/(period+1), SMA seed, recursive EMA"
    )

    print(
        "RSI14              : "
        "Wilder RSI, arithmetic initial averages, "
        "Wilder recursive smoothing"
    )

    section("DATABASE RESOLUTION")

    print("DATABASE PATH      :", DB_PATH)
    print("DATABASE FOUND     :", DB_PATH.exists())

    if not DB_PATH.exists():

        print("AUDIT STATUS       : BLOCKED")
        print("REASON             : DATABASE_NOT_FOUND")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        table_names = [
            row[0]
            for row in tables
        ]

        print("TABLE COUNT        :", len(table_names))

        if "market_data" not in table_names:

            print("ANALYSIS TABLE     : MISSING")
            print("AUDIT STATUS       : BLOCKED")
            print(
                "REASON             : "
                "MARKET_DATA_TABLE_NOT_FOUND"
            )
            return

        print("ANALYSIS TABLE     : market_data")

        columns = get_columns(
            conn,
            "market_data",
        )

        required_fields = [
            "id",
            "symbol",
            "source_timestamp",
            "engine_version",
            "close",
            "ema20",
            "ema50",
            "rsi14",
        ]

        missing = [
            field
            for field in required_fields
            if field not in columns
        ]

        if missing:

            print("MISSING FIELDS     :", ", ".join(missing))
            print("AUDIT STATUS       : BLOCKED")
            print(
                "REASON             : "
                "REQUIRED_FIELDS_MISSING"
            )
            return

        print("REQUIRED FIELDS    : PRESENT")

        # ----------------------------------------------------
        # RUN SYMBOLS
        # ----------------------------------------------------

        results = []

        for symbol in SYMBOLS:

            result = compare_symbol(
                conn,
                symbol,
            )

            results.append(result)

        # ----------------------------------------------------
        # FINAL SUMMARY
        # ----------------------------------------------------

        section(
            "FINAL STANDARD CONVENTION "
            "COMPARISON SUMMARY"
        )

        total_exact = sum(
            result["exact"]
            for result in results
        )

        total_match = sum(
            result["match"]
            for result in results
        )

        total_mismatch = sum(
            result["mismatch"]
            for result in results
        )

        total_unresolved = sum(
            result["unresolved"]
            for result in results
        )

        total_blocked = sum(
            1
            for result in results
            if result["status"] == "BLOCKED"
        )

        print(
            "SYMBOLS CHECKED      :",
            len(results)
        )

        print(
            "TOTAL EXACT          :",
            total_exact
        )

        print(
            "TOTAL MATCH          :",
            total_match
        )

        print(
            "TOTAL MISMATCH       :",
            total_mismatch
        )

        print(
            "TOTAL UNRESOLVED     :",
            total_unresolved
        )

        print(
            "BLOCKED SYMBOLS      :",
            total_blocked
        )

        print()
        print("INDICATOR STATUS MATRIX")
        divider("-")

        for result in results:

            print(
                f"  [{result['status']:<12}] : "
                f"{result['symbol']}"
            )

        print()
        divider("=")

        if total_blocked > 0:

            print(
                "COMPARISON STATUS : BLOCKED"
            )

            print(
                "REASON            : "
                "TARGET OR HISTORY RESOLUTION FAILURE"
            )

        elif total_unresolved > 0:

            print(
                "COMPARISON STATUS : REVIEW_REQUIRED"
            )

            print(
                "REASON            : "
                "CURRENT OR STANDARD VALUE UNRESOLVED"
            )

        elif total_mismatch > 0:

            print(
                "COMPARISON STATUS : DIFFERENCE_DETECTED"
            )

            print(
                "REASON            : "
                "CURRENT IMPLEMENTATION DIFFERS "
                "FROM STANDARD CONVENTION"
            )

        else:

            print(
                "COMPARISON STATUS : STANDARD_CONFORMANT"
            )

            print(
                "REASON            : "
                "CURRENT IMPLEMENTATION MATCHES "
                "STANDARD CONVENTION"
            )

        divider("=")

        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS      : NONE"
        )

        print(
            "FORMULA WRITE             : NONE"
        )

        print(
            "AUDIT COMPLETE"
        )

        divider("=")

    finally:

        conn.close()


if __name__ == "__main__":
    main()