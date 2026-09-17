import sqlite3
import math
from pathlib import Path


# =============================================================================
# ARUNDA INDICATOR STANDARD CONVENTION RECONSTRUCTION v0.2
# =============================================================================
#
# PURPOSE:
#   Compare CURRENT IMPLEMENTATION values stored in the database
#   against independently reconstructed STANDARD conventions.
#
# INDICATORS:
#   EMA20
#   EMA50
#   RSI14
#
# SYMBOLS:
#   BTC / ETH / SOL / XRP
#
# MODE:
#   READ ONLY
#
# DATABASE WRITES:
#   NONE
#
# STANDARD CONVENTIONS:
#   EMA:
#       alpha = 2 / (period + 1)
#       initial seed = arithmetic mean of first period values
#       subsequent values = recursive EMA
#
#   RSI:
#       period = 14
#       gains/losses separated from price changes
#       initial average gain/loss = arithmetic mean
#       subsequent averages = Wilder smoothing
#       RSI = 100 - 100 / (1 + RS)
#
# =============================================================================


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

EMA_PERIODS = {
    "EMA20": 20,
    "EMA50": 50,
}

RSI_PERIOD = 14

LOOKBACK = 120
MIN_HISTORY = 60

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10


# =============================================================================
# OUTPUT
# =============================================================================

def banner(text):
    print("=" * 100)
    print(text)
    print("=" * 100)


def section(text):
    print()
    print("=" * 100)
    print(text)
    print("=" * 100)


# =============================================================================
# SQLITE HELPERS
# =============================================================================

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [row["name"] for row in rows]


def table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row["name"] for row in rows]


def find_table_with_columns(conn, required_columns):
    """
    Find the best table containing all requested columns.

    This is intentionally read-only and defensive because the database
    schema may evolve.
    """

    required = {c.lower() for c in required_columns}

    candidates = []

    for table in list_tables(conn):
        columns = table_columns(conn, table)
        lower_columns = {c.lower() for c in columns}

        if required.issubset(lower_columns):
            candidates.append(table)

    if not candidates:
        return None

    # Prefer market_data for price/history data.
    preferred = [
        "market_data",
        "market_records",
        "market_history",
    ]

    for table in preferred:
        if table in candidates:
            return table

    return candidates[0]


def resolve_column(columns, candidates):
    lower_map = {
        c.lower(): c
        for c in columns
    }

    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


# =============================================================================
# NUMERICAL HELPERS
# =============================================================================

def is_finite(value):
    return (
        value is not None
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def relative_error(stored, rebuilt):
    if stored is None or rebuilt is None:
        return None

    stored = float(stored)
    rebuilt = float(rebuilt)

    denominator = max(abs(stored), abs(rebuilt), 1e-30)

    return abs(stored - rebuilt) / denominator


def absolute_error(stored, rebuilt):
    if stored is None or rebuilt is None:
        return None

    return abs(float(stored) - float(rebuilt))


def compare_values(stored, rebuilt):
    if not is_finite(stored) or not is_finite(rebuilt):
        return "UNRESOLVED"

    abs_err = absolute_error(stored, rebuilt)
    rel_err = relative_error(stored, rebuilt)

    if (
        abs_err <= ABS_TOLERANCE
        or rel_err <= REL_TOLERANCE
    ):
        return "EXACT"

    return "MISMATCH"


# =============================================================================
# STANDARD EMA
# =============================================================================

def standard_ema(values, period):
    """
    Standard EMA convention:

        alpha = 2 / (period + 1)

    Initial seed:
        arithmetic mean of first 'period' values

    Recursive:
        EMA_t = alpha * value_t
              + (1 - alpha) * EMA_(t-1)

    Returns the final EMA value.
    """

    if values is None:
        return None

    if len(values) < period:
        return None

    clean = [float(v) for v in values]

    alpha = 2.0 / (period + 1.0)

    seed = sum(clean[:period]) / float(period)

    ema_value = seed

    for value in clean[period:]:
        ema_value = (
            alpha * value
            + (1.0 - alpha) * ema_value
        )

    return ema_value


# =============================================================================
# STANDARD WILDER RSI
# =============================================================================

def standard_rsi(values, period=14):
    """
    Standard Wilder RSI.

    Step 1:
        Calculate price changes.

    Step 2:
        Separate gains and losses.

    Step 3:
        Initial average gain/loss:
            arithmetic mean of first 'period' changes.

    Step 4:
        Subsequent averages:
            Wilder smoothing

            avg_gain =
                ((previous_avg_gain * (period - 1)) + gain) / period

            avg_loss =
                ((previous_avg_loss * (period - 1)) + loss) / period

    Step 5:
        RS = avg_gain / avg_loss

        RSI = 100 - 100 / (1 + RS)
    """

    if values is None:
        return None

    if len(values) < period + 1:
        return None

    prices = [float(v) for v in values]

    changes = []

    for i in range(1, len(prices)):
        changes.append(prices[i] - prices[i - 1])

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

    avg_gain = sum(gains[:period]) / float(period)
    avg_loss = sum(losses[:period]) / float(period)

    for i in range(period, len(gains)):
        gain = gains[i]
        loss = losses[i]

        avg_gain = (
            ((avg_gain * (period - 1.0)) + gain)
            / float(period)
        )

        avg_loss = (
            ((avg_loss * (period - 1.0)) + loss)
            / float(period)
        )

    if avg_loss == 0.0:

        if avg_gain == 0.0:
            return 50.0

        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (
        100.0 / (1.0 + rs)
    )


# =============================================================================
# TABLE RESOLUTION
# =============================================================================

def resolve_history_table(conn):
    tables = list_tables(conn)

    print("DATABASE TABLES :", len(tables))

    for table in tables:
        columns = table_columns(conn, table)

        lower = {c.lower() for c in columns}

        has_symbol = "symbol" in lower

        has_close = (
            "close" in lower
            or "price" in lower
        )

        has_timestamp = any(
            x in lower
            for x in [
                "source_timestamp",
                "timestamp",
                "time",
                "datetime",
            ]
        )

        if has_symbol and has_close and has_timestamp:
            print(
                f"[HISTORY CANDIDATE] {table}"
            )

    table = find_table_with_columns(
        conn,
        [
            "symbol",
        ]
    )

    return table


def load_history(conn, symbol):
    """
    Locate the most appropriate historical price table dynamically.

    The function prefers:
        market_data
        market_records
        market_history

    It then discovers the timestamp and close columns.
    """

    preferred_tables = [
        "market_data",
        "market_records",
        "market_history",
    ]

    selected_table = None
    selected_columns = None

    existing_tables = list_tables(conn)

    for table in preferred_tables:
        if table not in existing_tables:
            continue

        columns = table_columns(conn, table)
        lower = {c.lower() for c in columns}

        if "symbol" not in lower:
            continue

        close_column = resolve_column(
            columns,
            [
                "close",
                "close_price",
                "price",
            ]
        )

        timestamp_column = resolve_column(
            columns,
            [
                "source_timestamp",
                "timestamp",
                "time",
                "datetime",
            ]
        )

        if close_column and timestamp_column:
            selected_table = table
            selected_columns = (
                close_column,
                timestamp_column,
            )
            break

    if selected_table is None:

        for table in existing_tables:

            columns = table_columns(
                conn,
                table
            )

            close_column = resolve_column(
                columns,
                [
                    "close",
                    "close_price",
                    "price",
                ]
            )

            timestamp_column = resolve_column(
                columns,
                [
                    "source_timestamp",
                    "timestamp",
                    "time",
                    "datetime",
                ]
            )

            symbol_column = resolve_column(
                columns,
                [
                    "symbol",
                ]
            )

            if (
                symbol_column
                and close_column
                and timestamp_column
            ):
                selected_table = table
                selected_columns = (
                    close_column,
                    timestamp_column,
                )
                break

    if selected_table is None:
        return None, None, None, []

    close_column, timestamp_column = selected_columns

    query = f"""
        SELECT
            "{timestamp_column}" AS ts,
            "{close_column}" AS close
        FROM "{selected_table}"
        WHERE UPPER(symbol) = ?
          AND "{close_column}" IS NOT NULL
        ORDER BY "{timestamp_column}" ASC
        LIMIT ?
    """

    rows = conn.execute(
        query,
        (
            symbol.upper(),
            LOOKBACK,
        )
    ).fetchall()

    history = []

    for row in rows:
        if row["close"] is None:
            continue

        try:
            close = float(row["close"])
        except (TypeError, ValueError):
            continue

        if not math.isfinite(close):
            continue

        history.append(
            {
                "timestamp": row["ts"],
                "close": close,
            }
        )

    return (
        selected_table,
        close_column,
        timestamp_column,
        history,
    )


# =============================================================================
# ANALYSIS TABLE RESOLUTION
# =============================================================================

def resolve_analysis_table(conn):
    """
    Find the table containing the stored indicator values.

    Required fields:
        symbol
        ema20
        ema50
        rsi14

    Preferred analysis identifiers:
        analysis_id
        source_timestamp
        engine_version
    """

    required = [
        "symbol",
        "ema20",
        "ema50",
        "rsi14",
    ]

    candidates = []

    for table in list_tables(conn):

        columns = table_columns(
            conn,
            table
        )

        lower = {
            c.lower()
            for c in columns
        }

        if all(
            field.lower() in lower
            for field in required
        ):
            candidates.append(
                (
                    table,
                    lower,
                )
            )

    if not candidates:
        return None

    preferred = [
        "market_data",
        "market_data_analysis",
        "market_analysis",
        "analysis",
    ]

    for preferred_table in preferred:

        for table, _ in candidates:
            if table == preferred_table:
                return table

    return candidates[0][0]


def get_analysis_columns(conn, table):
    columns = table_columns(
        conn,
        table
    )

    return {
        "symbol": resolve_column(
            columns,
            ["symbol"]
        ),

        "ema20": resolve_column(
            columns,
            ["ema20"]
        ),

        "ema50": resolve_column(
            columns,
            ["ema50"]
        ),

        "rsi14": resolve_column(
            columns,
            ["rsi14"]
        ),

        "source_timestamp": resolve_column(
            columns,
            [
                "source_timestamp",
                "timestamp",
                "time",
                "datetime",
            ]
        ),

        "analysis_id": resolve_column(
            columns,
            [
                "analysis_id",
                "id",
            ]
        ),

        "engine_version": resolve_column(
            columns,
            [
                "engine_version",
            ]
        ),
    }


def get_stored_target(conn, table, columns, symbol):
    """
    Resolve the most recent stored analysis row for a symbol.

    If source_timestamp exists, the latest row is selected.
    """

    symbol_column = columns["symbol"]

    select_parts = [
        f'"{symbol_column}" AS symbol',
        f'"{columns["ema20"]}" AS ema20',
        f'"{columns["ema50"]}" AS ema50',
        f'"{columns["rsi14"]}" AS rsi14',
    ]

    optional = [
        ("source_timestamp", columns["source_timestamp"]),
        ("analysis_id", columns["analysis_id"]),
        ("engine_version", columns["engine_version"]),
    ]

    for alias, column in optional:
        if column:
            select_parts.append(
                f'"{column}" AS "{alias}"'
            )

    order_column = (
        columns["source_timestamp"]
        or columns["analysis_id"]
        or symbol_column
    )

    query = f"""
        SELECT
            {", ".join(select_parts)}
        FROM "{table}"
        WHERE UPPER("{symbol_column}") = ?
        ORDER BY "{order_column}" DESC
        LIMIT 1
    """

    row = conn.execute(
        query,
        (symbol.upper(),)
    ).fetchone()

    return row


# =============================================================================
# TARGET-ALIGNED HISTORY
# =============================================================================

def align_history_to_target(history, target_timestamp):
    """
    Keep observations up to and including the target timestamp.

    This prevents future observations from contaminating reconstruction.
    """

    if not history:
        return []

    if target_timestamp is None:
        return history[-LOOKBACK:]

    target_string = str(target_timestamp)

    eligible = []

    for row in history:

        ts = str(row["timestamp"])

        if ts <= target_string:
            eligible.append(row)

    return eligible[-LOOKBACK:]


# =============================================================================
# MAIN AUDIT
# =============================================================================

def run_audit():

    banner(
        "ARUNDA INDICATOR STANDARD CONVENTION RECONSTRUCTION v0.2"
    )

    print("MODE              : READ ONLY")
    print("DATABASE           :", DB_PATH.name)
    print("DATABASE WRITE     : NONE")
    print("FORMULA WRITE      : NONE")
    print("LOOKBACK           :", LOOKBACK)
    print("MIN HISTORY        :", MIN_HISTORY)
    print("ABS TOLERANCE      :", ABS_TOLERANCE)
    print("REL TOLERANCE      :", REL_TOLERANCE)

    section("STANDARD CONVENTIONS")

    print(
        "EMA20 / EMA50     : "
        "alpha = 2/(period+1), "
        "SMA seed, recursive EMA"
    )

    print(
        "RSI14              : "
        "Wilder RSI, arithmetic initial averages, "
        "Wilder recursive smoothing"
    )

    conn = get_connection()

    try:

        # ---------------------------------------------------------------------
        # DATABASE INVENTORY
        # ---------------------------------------------------------------------

        section("DATABASE RESOLUTION")

        tables = list_tables(conn)

        print(
            "DATABASE FOUND     :",
            DB_PATH.exists()
        )

        print(
            "TABLE COUNT        :",
            len(tables)
        )

        analysis_table = resolve_analysis_table(
            conn
        )

        print(
            "ANALYSIS TABLE     :",
            analysis_table
        )

        if analysis_table is None:

            print()
            print(
                "FATAL : ANALYSIS TABLE COULD NOT BE RESOLVED"
            )

            return 1

        analysis_columns = get_analysis_columns(
            conn,
            analysis_table
        )

        print(
            "EMA20 COLUMN       :",
            analysis_columns["ema20"]
        )

        print(
            "EMA50 COLUMN       :",
            analysis_columns["ema50"]
        )

        print(
            "RSI14 COLUMN       :",
            analysis_columns["rsi14"]
        )

        # ---------------------------------------------------------------------
        # SUMMARY COUNTERS
        # ---------------------------------------------------------------------

        total_exact = 0
        total_mismatch = 0
        total_unresolved = 0

        symbol_results = {}

        # ---------------------------------------------------------------------
        # SYMBOL LOOP
        # ---------------------------------------------------------------------

        for symbol in SYMBOLS:

            section(f"SYMBOL : {symbol}")

            stored = get_stored_target(
                conn,
                analysis_table,
                analysis_columns,
                symbol,
            )

            if stored is None:

                print(
                    "TARGET STATUS      : BLOCKED"
                )

                print(
                    "REASON             : "
                    "ANALYSIS_TARGET_NOT_FOUND"
                )

                symbol_results[symbol] = {
                    "exact": 0,
                    "mismatch": 0,
                    "unresolved": 3,
                }

                total_unresolved += 3

                continue

            print(
                "ANALYSIS TARGET    : FOUND"
            )

            if "analysis_id" in stored.keys():
                print(
                    "Analysis ID        :",
                    stored["analysis_id"]
                )

            if "source_timestamp" in stored.keys():
                print(
                    "Source Time        :",
                    stored["source_timestamp"]
                )

            if "engine_version" in stored.keys():
                print(
                    "Engine Version     :",
                    stored["engine_version"]
                )

            print(
                "Stored EMA20       :",
                stored["ema20"]
            )

            print(
                "Stored EMA50       :",
                stored["ema50"]
            )

            print(
                "Stored RSI14       :",
                stored["rsi14"]
            )

            target_timestamp = (
                stored["source_timestamp"]
                if "source_timestamp" in stored.keys()
                else None
            )

            # -----------------------------------------------------------------
            # HISTORY
            # -----------------------------------------------------------------

            (
                history_table,
                close_column,
                timestamp_column,
                history,
            ) = load_history(
                conn,
                symbol
            )

            if not history:

                print()
                print(
                    "HISTORY STATUS     : BLOCKED"
                )

                print(
                    "REASON             : "
                    "PRICE_HISTORY_NOT_FOUND"
                )

                symbol_results[symbol] = {
                    "exact": 0,
                    "mismatch": 0,
                    "unresolved": 3,
                }

                total_unresolved += 3

                continue

            history = align_history_to_target(
                history,
                target_timestamp
            )

            print()
            print(
                "HISTORY TABLE      :",
                history_table
            )

            print(
                "HISTORY COUNT      :",
                len(history)
            )

            if history:
                print(
                    "HISTORY FIRST      :",
                    history[0]["timestamp"]
                )

                print(
                    "HISTORY LAST       :",
                    history[-1]["timestamp"]
                )

            if len(history) < MIN_HISTORY:

                print()
                print(
                    "TARGET STATUS      : BLOCKED"
                )

                print(
                    "REASON             : "
                    f"INSUFFICIENT_HISTORY_{len(history)}"
                )

                symbol_results[symbol] = {
                    "exact": 0,
                    "mismatch": 0,
                    "unresolved": 3,
                }

                total_unresolved += 3

                continue

            closes = [
                row["close"]
                for row in history
            ]

            print()
            print(
                "TARGET STATUS      : READY"
            )

            # -----------------------------------------------------------------
            # STANDARD RECONSTRUCTION
            # -----------------------------------------------------------------

            standard_ema20 = standard_ema(
                closes,
                20
            )

            standard_ema50 = standard_ema(
                closes,
                50
            )

            standard_rsi14 = standard_rsi(
                closes,
                14
            )

            # -----------------------------------------------------------------
            # COMPARISON
            # -----------------------------------------------------------------

            comparisons = [
                (
                    "EMA20",
                    stored["ema20"],
                    standard_ema20,
                ),

                (
                    "EMA50",
                    stored["ema50"],
                    standard_ema50,
                ),

                (
                    "RSI14",
                    stored["rsi14"],
                    standard_rsi14,
                ),
            ]

            symbol_exact = 0
            symbol_mismatch = 0
            symbol_unresolved = 0

            print()
            print(
                "CURRENT IMPLEMENTATION vs STANDARD CONVENTION"
            )

            print("-" * 100)

            for name, current, standard in comparisons:

                status = compare_values(
                    current,
                    standard
                )

                abs_err = absolute_error(
                    current,
                    standard
                )

                rel_err = relative_error(
                    current,
                    standard
                )

                print()
                print(
                    "INDICATOR :",
                    name
                )

                print(
                    "CURRENT   :",
                    current
                )

                print(
                    "STANDARD  :",
                    standard
                )

                print(
                    "ABS ERR   :",
                    abs_err
                )

                print(
                    "REL ERR   :",
                    rel_err
                )

                print(
                    "STATUS    :",
                    status
                )

                if status == "EXACT":
                    symbol_exact += 1
                    total_exact += 1

                elif status == "MISMATCH":
                    symbol_mismatch += 1
                    total_mismatch += 1

                else:
                    symbol_unresolved += 1
                    total_unresolved += 1

            print()
            print(
                "SYMBOL SUMMARY"
            )

            print(
                "  EXACT      :",
                symbol_exact
            )

            print(
                "  MISMATCH   :",
                symbol_mismatch
            )

            print(
                "  UNRESOLVED :",
                symbol_unresolved
            )

            if symbol_unresolved > 0:

                symbol_status = "UNRESOLVED"

            elif symbol_mismatch > 0:

                symbol_status = "STANDARD MISMATCH"

            else:

                symbol_status = "STANDARD EXACT"

            print(
                "SYMBOL STATUS :",
                symbol_status
            )

            symbol_results[symbol] = {
                "exact": symbol_exact,
                "mismatch": symbol_mismatch,
                "unresolved": symbol_unresolved,
            }

        # ---------------------------------------------------------------------
        # FINAL SUMMARY
        # ---------------------------------------------------------------------

        section(
            "FINAL STANDARD CONVENTION RECONSTRUCTION SUMMARY"
        )

        print(
            "SYMBOLS CHECKED      :",
            len(SYMBOLS)
        )

        print(
            "TOTAL EXACT          :",
            total_exact
        )

        print(
            "TOTAL MISMATCH       :",
            total_mismatch
        )

        print(
            "TOTAL UNRESOLVED     :",
            total_unresolved
        )

        if total_unresolved > 0:

            final_status = "REVIEW_REQUIRED"

            reason = (
                "INSUFFICIENT DATA OR TARGET RESOLUTION"
            )

        elif total_mismatch > 0:

            final_status = "STANDARD_MISMATCH"

            reason = (
                "CURRENT IMPLEMENTATION DIFFERS "
                "FROM STANDARD CONVENTION"
            )

        else:

            final_status = "STANDARD_EXACT"

            reason = (
                "CURRENT IMPLEMENTATION MATCHES "
                "STANDARD CONVENTION"
            )

        print()
        print(
            "RECONSTRUCTION STATUS :",
            final_status
        )

        print(
            "REASON                :",
            reason
        )

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS      : NONE"
        )

        print(
            "FORMULA CALCULATIONS      : READ-ONLY RECONSTRUCTION"
        )

        print(
            "AUDIT COMPLETE"
        )

        return 0

    finally:

        conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    try:

        raise SystemExit(
            run_audit()
        )

    except Exception as exc:

        print()
        print("=" * 100)
        print("AUDIT ERROR")
        print("=" * 100)
        print(
            "ERROR TYPE :",
            type(exc).__name__
        )
        print(
            "ERROR      :",
            str(exc)
        )
        print()
        print(
            "NO DATABASE WRITE OPERATIONS WERE PERFORMED."
        )
        print("=" * 100)

        raise