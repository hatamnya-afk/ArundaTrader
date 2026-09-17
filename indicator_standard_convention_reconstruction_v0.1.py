from pathlib import Path
import sqlite3
import math
import statistics
import sys

# ============================================================
# ARUNDA INDICATOR STANDARD CONVENTION RECONSTRUCTION v0.1
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

LOOKBACK = 120
MIN_HISTORY = 60

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10


# ============================================================
# OUTPUT
# ============================================================

def header(title):
    print()
    print("=" * 99)
    print(title)
    print("=" * 99)


def section(title):
    print()
    print("-" * 99)
    print(title)
    print("-" * 99)


# ============================================================
# DB HELPERS
# ============================================================

def get_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def get_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return [row[1] for row in rows]


def find_column(columns, candidates):
    lowered = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    return None


# ============================================================
# NUMERIC HELPERS
# ============================================================

def clean_float(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value):
        return None

    return value


def errors(stored, rebuilt):
    if stored is None or rebuilt is None:
        return None, None

    abs_err = abs(stored - rebuilt)

    denominator = max(abs(stored), abs(rebuilt), 1e-30)
    rel_err = abs_err / denominator

    return abs_err, rel_err


def is_exact(stored, rebuilt):
    result = errors(stored, rebuilt)

    if result == (None, None):
        return False

    abs_err, rel_err = result

    return (
        abs_err <= ABS_TOLERANCE
        or rel_err <= REL_TOLERANCE
    )


# ============================================================
# STANDARD EMA
# ============================================================

def standard_ema(values, period):
    """
    Standard EMA convention:

    alpha = 2 / (period + 1)

    Initial seed:
        arithmetic mean of first period observations

    Subsequent:
        EMA_t = alpha * value_t
              + (1 - alpha) * EMA_(t-1)
    """

    if len(values) < period:
        return None

    values = [float(v) for v in values]

    alpha = 2.0 / (period + 1.0)

    seed = sum(values[:period]) / period

    ema_value = seed

    for value in values[period:]:
        ema_value = (
            alpha * value
            + (1.0 - alpha) * ema_value
        )

    return ema_value


# ============================================================
# STANDARD RSI - WILDER
# ============================================================

def standard_rsi(values, period=14):
    """
    Wilder RSI convention.

    Initial average gain/loss:
        arithmetic mean of first period changes

    Subsequent:
        Wilder smoothing

    RSI:
        100 - 100 / (1 + RS)
    """

    if len(values) < period + 1:
        return None

    values = [float(v) for v in values]

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0.0)

        elif change < 0:
            gains.append(0.0)
            losses.append(abs(change))

        else:
            gains.append(0.0)
            losses.append(0.0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            ((period - 1) * avg_gain) + gains[i]
        ) / period

        avg_loss = (
            ((period - 1) * avg_loss) + losses[i]
        ) / period

    if avg_loss == 0:
        if avg_gain == 0:
            return 50.0
        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (
        100.0 / (1.0 + rs)
    )


# ============================================================
# STANDARD SMA
# ============================================================

def standard_sma(values, period):
    if len(values) < period:
        return None

    return sum(values[-period:]) / period


# ============================================================
# STANDARD STANDARD-DEVIATION
# ============================================================

def standard_population_stdev(values):
    if not values:
        return None

    mean_value = sum(values) / len(values)

    variance = sum(
        (x - mean_value) ** 2
        for x in values
    ) / len(values)

    return math.sqrt(variance)


# ============================================================
# STANDARD BOLLINGER
# ============================================================

def standard_bollinger(values, period=20, multiplier=2.0):
    if len(values) < period:
        return None, None, None, None

    window = values[-period:]

    middle = standard_sma(window, period)

    deviation = standard_population_stdev(window)

    upper = middle + multiplier * deviation
    lower = middle - multiplier * deviation

    if middle == 0:
        width = None
    else:
        width = (upper - lower) / middle

    return middle, upper, lower, width


# ============================================================
# STANDARD TRUE RANGE
# ============================================================

def true_ranges(highs, lows, closes):
    if len(highs) != len(lows) or len(highs) != len(closes):
        return []

    result = []

    for i in range(len(closes)):
        high = highs[i]
        low = lows[i]

        if i == 0:
            tr = high - low
        else:
            previous_close = closes[i - 1]

            tr = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        result.append(tr)

    return result


# ============================================================
# STANDARD ATR - WILDER
# ============================================================

def standard_atr(highs, lows, closes, period=14):
    tr = true_ranges(highs, lows, closes)

    if len(tr) < period:
        return None

    atr_value = sum(tr[:period]) / period

    for value in tr[period:]:
        atr_value = (
            ((period - 1) * atr_value) + value
        ) / period

    return atr_value


# ============================================================
# STANDARD MACD
# ============================================================

def standard_macd(values):
    """
    Standard MACD:
        EMA12 - EMA26

    Signal:
        EMA9 of MACD series

    Histogram:
        MACD - Signal
    """

    if len(values) < 26:
        return None, None, None

    values = [float(v) for v in values]

    ema12_series = []
    ema26_series = []

    alpha12 = 2.0 / 13.0
    alpha26 = 2.0 / 27.0

    ema12 = sum(values[:12]) / 12

    for value in values[12:]:
        ema12 = alpha12 * value + (1 - alpha12) * ema12
        ema12_series.append(ema12)

    ema26 = sum(values[:26]) / 26

    for value in values[26:]:
        ema26 = alpha26 * value + (1 - alpha26) * ema26
        ema26_series.append(ema26)

    # Build aligned MACD series from the point where both EMA series exist.
    macd_series = []

    # Reconstruct complete EMA12 series including seed.
    full_ema12 = [sum(values[:12]) / 12]

    ema12 = full_ema12[0]

    for value in values[12:]:
        ema12 = alpha12 * value + (1 - alpha12) * ema12
        full_ema12.append(ema12)

    # Reconstruct complete EMA26 series including seed.
    full_ema26 = [None] * 14
    full_ema26.append(sum(values[:26]) / 26)

    ema26 = full_ema26[-1]

    for value in values[26:]:
        ema26 = alpha26 * value + (1 - alpha26) * ema26
        full_ema26.append(ema26)

    for i in range(25, len(values)):
        if i < len(full_ema12) and i < len(full_ema26):
            macd_series.append(
                full_ema12[i] - full_ema26[i]
            )

    if not macd_series:
        return None, None, None

    macd_value = macd_series[-1]

    if len(macd_series) < 9:
        return macd_value, None, None

    signal = sum(macd_series[:9]) / 9

    alpha9 = 2.0 / 10.0

    for value in macd_series[9:]:
        signal = alpha9 * value + (1 - alpha9) * signal

    histogram = macd_value - signal

    return macd_value, signal, histogram


# ============================================================
# STANDARD VOLUME
# ============================================================

def standard_volume_metrics(volumes, period=20):
    if len(volumes) < period:
        return None, None

    sma = sum(volumes[-period:]) / period
    current = volumes[-1]

    if sma == 0:
        ratio = None
    else:
        ratio = current / sma

    return sma, ratio


# ============================================================
# STANDARD VOLATILITY
# ============================================================

def standard_volatility(closes):
    if len(closes) < 3:
        return None

    returns = []

    for i in range(1, len(closes)):
        previous = closes[i - 1]
        current = closes[i]

        if previous == 0:
            continue

        returns.append(
            (current - previous) / previous
        )

    if len(returns) < 2:
        return None

    return standard_population_stdev(returns)


# ============================================================
# FIND MARKET_DATA SOURCE COLUMNS
# ============================================================

def resolve_market_data_schema(conn):
    tables = get_tables(conn)

    if "market_data" not in tables:
        return None

    columns = get_columns(conn, "market_data")

    schema = {
        "symbol": find_column(
            columns,
            ["symbol", "ticker"]
        ),

        "timestamp": find_column(
            columns,
            [
                "source_timestamp",
                "source_time",
                "timestamp",
                "time",
                "created_at",
            ]
        ),

        "close": find_column(
            columns,
            ["close", "price"]
        ),

        "high": find_column(
            columns,
            ["high"]
        ),

        "low": find_column(
            columns,
            ["low"]
        ),

        "volume": find_column(
            columns,
            ["volume", "volume_24h"]
        ),

        "ema20": find_column(
            columns,
            ["ema20"]
        ),

        "ema50": find_column(
            columns,
            ["ema50"]
        ),

        "rsi14": find_column(
            columns,
            ["rsi14"]
        ),

        "macd": find_column(
            columns,
            ["macd"]
        ),

        "macd_signal": find_column(
            columns,
            ["macd_signal"]
        ),

        "macd_hist": find_column(
            columns,
            ["macd_hist"]
        ),

        "atr14": find_column(
            columns,
            ["atr14"]
        ),

        "bb_middle": find_column(
            columns,
            ["bb_middle"]
        ),

        "bb_upper": find_column(
            columns,
            ["bb_upper"]
        ),

        "bb_lower": find_column(
            columns,
            ["bb_lower"]
        ),

        "bb_width": find_column(
            columns,
            ["bb_width"]
        ),

        "volume_sma20": find_column(
            columns,
            ["volume_sma20"]
        ),

        "volume_ratio": find_column(
            columns,
            ["volume_ratio"]
        ),

        "volatility": find_column(
            columns,
            ["volatility"]
        ),

        "technical_score": find_column(
            columns,
            ["technical_score"]
        ),
    }

    return schema


# ============================================================
# LOAD HISTORY
# ============================================================

def load_history(conn, schema, symbol):
    required = [
        "symbol",
        "timestamp",
        "close",
    ]

    for key in required:
        if schema.get(key) is None:
            return []

    columns = [
        schema["symbol"],
        schema["timestamp"],
        schema["close"],
    ]

    if schema.get("high"):
        columns.append(schema["high"])

    if schema.get("low"):
        columns.append(schema["low"])

    if schema.get("volume"):
        columns.append(schema["volume"])

    select_columns = ", ".join(
        f'"{column}"'
        for column in columns
    )

    query = f"""
        SELECT {select_columns}
        FROM market_data
        WHERE "{schema["symbol"]}" = ?
        ORDER BY "{schema["timestamp"]}" ASC
    """

    rows = conn.execute(
        query,
        (symbol,)
    ).fetchall()

    result = []

    for row in rows:
        record = {
            "symbol": row[0],
            "timestamp": row[1],
            "close": clean_float(row[2]),
        }

        offset = 3

        if schema.get("high"):
            record["high"] = clean_float(row[offset])
            offset += 1
        else:
            record["high"] = None

        if schema.get("low"):
            record["low"] = clean_float(row[offset])
            offset += 1
        else:
            record["low"] = None

        if schema.get("volume"):
            record["volume"] = clean_float(row[offset])
        else:
            record["volume"] = None

        if record["close"] is not None:
            result.append(record)

    return result


# ============================================================
# LOAD STORED INDICATORS
# ============================================================

def load_stored_latest(conn, schema, symbol):
    timestamp_column = schema.get("timestamp")
    symbol_column = schema.get("symbol")

    if not timestamp_column or not symbol_column:
        return None

    query = f"""
        SELECT *
        FROM market_data
        WHERE "{symbol_column}" = ?
        ORDER BY "{timestamp_column}" DESC
        LIMIT 1
    """

    cursor = conn.execute(
        query,
        (symbol,)
    )

    row = cursor.fetchone()

    if row is None:
        return None

    column_names = [
        description[0]
        for description in cursor.description
    ]

    data = dict(zip(column_names, row))

    return data


# ============================================================
# COMPARISON
# ============================================================

def compare_formula(
    symbol,
    formula,
    stored,
    rebuilt,
):
    stored = clean_float(stored)
    rebuilt = clean_float(rebuilt)

    print()
    print(f"FORMULA : {formula}")
    print(f"STORED  : {stored}")
    print(f"STANDARD: {rebuilt}")

    if stored is None or rebuilt is None:
        print("STATUS  : UNRESOLVED")
        return "UNRESOLVED"

    abs_err, rel_err = errors(
        stored,
        rebuilt
    )

    print(f"ABS ERR : {abs_err}")
    print(f"REL ERR : {rel_err}")

    if is_exact(stored, rebuilt):
        print("STATUS  : EXACT")
        return "EXACT"

    print("STATUS  : MISMATCH")
    return "MISMATCH"


# ============================================================
# MAIN
# ============================================================

def main():
    header(
        "ARUNDA INDICATOR STANDARD CONVENTION RECONSTRUCTION v0.1"
    )

    print("MODE              : READ ONLY")
    print("DATABASE           :", DB_PATH.name)
    print("DATABASE WRITE     : NONE")
    print("FORMULA CALC       : INDEPENDENT STANDARD RECONSTRUCTION")
    print("LOOKBACK           :", LOOKBACK)
    print("MIN HISTORY        :", MIN_HISTORY)
    print("ABS TOLERANCE      :", ABS_TOLERANCE)
    print("REL TOLERANCE      :", REL_TOLERANCE)

    if not DB_PATH.exists():
        print()
        print("DATABASE FOUND     : False")
        print("STATUS             : BLOCKED")
        print("REASON             : DATABASE_NOT_FOUND")
        return 1

    print("DATABASE FOUND     : True")

    conn = sqlite3.connect(
        str(DB_PATH)
    )

    try:
        schema = resolve_market_data_schema(conn)

        header("MARKET_DATA SCHEMA")

        if schema is None:
            print("MARKET_DATA        : NOT FOUND")
            return 1

        for key, value in schema.items():
            print(
                f"{key.upper():18} : {value}"
            )

        missing_core = [
            key
            for key in [
                "symbol",
                "timestamp",
                "close",
            ]
            if not schema.get(key)
        ]

        if missing_core:
            print()
            print(
                "SCHEMA STATUS      : BLOCKED"
            )
            print(
                "MISSING CORE       :",
                ", ".join(missing_core)
            )
            return 1

        total_exact = 0
        total_mismatch = 0
        total_unresolved = 0
        symbols_ready = 0

        for symbol in SYMBOLS:
            header(
                f"SYMBOL : {symbol}"
            )

            history = load_history(
                conn,
                schema,
                symbol
            )

            print(
                "HISTORY FOUND      :",
                len(history),
                "snapshots"
            )

            if len(history) < MIN_HISTORY:
                print(
                    "STATUS             : BLOCKED"
                )
                print(
                    "REASON             : INSUFFICIENT_HISTORY"
                )

                total_unresolved += 3
                continue

            symbols_ready += 1

            window = history[-LOOKBACK:]

            closes = [
                row["close"]
                for row in window
                if row["close"] is not None
            ]

            highs = [
                row["high"]
                for row in window
                if row["high"] is not None
            ]

            lows = [
                row["low"]
                for row in window
                if row["low"] is not None
            ]

            volumes = [
                row["volume"]
                for row in window
                if row["volume"] is not None
            ]

            stored_row = load_stored_latest(
                conn,
                schema,
                symbol
            )

            if stored_row is None:
                print(
                    "STATUS             : BLOCKED"
                )
                print(
                    "REASON             : STORED_TARGET_NOT_FOUND"
                )
                total_unresolved += 3
                continue

            print(
                "TARGET TIMESTAMP   :",
                stored_row.get(
                    schema["timestamp"]
                )
            )

            section(
                "STANDARD RECONSTRUCTION"
            )

            # ------------------------------------------------
            # EMA20
            # ------------------------------------------------

            rebuilt_ema20 = standard_ema(
                closes,
                20
            )

            status = compare_formula(
                symbol,
                "EMA20",
                stored_row.get(schema["ema20"])
                if schema.get("ema20")
                else None,
                rebuilt_ema20
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            # ------------------------------------------------
            # EMA50
            # ------------------------------------------------

            rebuilt_ema50 = standard_ema(
                closes,
                50
            )

            status = compare_formula(
                symbol,
                "EMA50",
                stored_row.get(schema["ema50"])
                if schema.get("ema50")
                else None,
                rebuilt_ema50
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            # ------------------------------------------------
            # RSI14
            # ------------------------------------------------

            rebuilt_rsi14 = standard_rsi(
                closes,
                14
            )

            status = compare_formula(
                symbol,
                "RSI14",
                stored_row.get(schema["rsi14"])
                if schema.get("rsi14")
                else None,
                rebuilt_rsi14
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            # ------------------------------------------------
            # MACD
            # ------------------------------------------------

            rebuilt_macd, rebuilt_signal, rebuilt_hist = (
                standard_macd(closes)
            )

            status = compare_formula(
                symbol,
                "MACD",
                stored_row.get(schema["macd"])
                if schema.get("macd")
                else None,
                rebuilt_macd
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            status = compare_formula(
                symbol,
                "MACD_SIGNAL",
                stored_row.get(schema["macd_signal"])
                if schema.get("macd_signal")
                else None,
                rebuilt_signal
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            status = compare_formula(
                symbol,
                "MACD_HIST",
                stored_row.get(schema["macd_hist"])
                if schema.get("macd_hist")
                else None,
                rebuilt_hist
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            # ------------------------------------------------
            # ATR
            # ------------------------------------------------

            if len(highs) == len(lows) == len(closes):
                rebuilt_atr = standard_atr(
                    highs,
                    lows,
                    closes,
                    14
                )
            else:
                rebuilt_atr = None

            status = compare_formula(
                symbol,
                "ATR14",
                stored_row.get(schema["atr14"])
                if schema.get("atr14")
                else None,
                rebuilt_atr
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            # ------------------------------------------------
            # Bollinger
            # ------------------------------------------------

            bb_middle, bb_upper, bb_lower, bb_width = (
                standard_bollinger(
                    closes,
                    20,
                    2.0
                )
            )

            bb_items = [
                ("BB_MIDDLE", "bb_middle", bb_middle),
                ("BB_UPPER", "bb_upper", bb_upper),
                ("BB_LOWER", "bb_lower", bb_lower),
                ("BB_WIDTH", "bb_width", bb_width),
            ]

            for formula, key, rebuilt in bb_items:
                status = compare_formula(
                    symbol,
                    formula,
                    stored_row.get(schema[key])
                    if schema.get(key)
                    else None,
                    rebuilt
                )

                if status == "EXACT":
                    total_exact += 1
                elif status == "MISMATCH":
                    total_mismatch += 1
                else:
                    total_unresolved += 1

            # ------------------------------------------------
            # Volume
            # ------------------------------------------------

            volume_sma20, volume_ratio = (
                standard_volume_metrics(
                    volumes,
                    20
                )
            )

            for formula, key, rebuilt in [
                (
                    "VOLUME_SMA20",
                    "volume_sma20",
                    volume_sma20
                ),
                (
                    "VOLUME_RATIO",
                    "volume_ratio",
                    volume_ratio
                ),
            ]:
                status = compare_formula(
                    symbol,
                    formula,
                    stored_row.get(schema[key])
                    if schema.get(key)
                    else None,
                    rebuilt
                )

                if status == "EXACT":
                    total_exact += 1
                elif status == "MISMATCH":
                    total_mismatch += 1
                else:
                    total_unresolved += 1

            # ------------------------------------------------
            # Volatility
            # ------------------------------------------------

            rebuilt_volatility = standard_volatility(
                closes
            )

            status = compare_formula(
                symbol,
                "VOLATILITY",
                stored_row.get(schema["volatility"])
                if schema.get("volatility")
                else None,
                rebuilt_volatility
            )

            if status == "EXACT":
                total_exact += 1
            elif status == "MISMATCH":
                total_mismatch += 1
            else:
                total_unresolved += 1

            section(
                "SYMBOL RECONSTRUCTION STATUS"
            )

            if total_mismatch == 0:
                print(
                    "SYMBOL STATUS      : STANDARD VALUES MATCH"
                )
            else:
                print(
                    "SYMBOL STATUS      : STANDARD CONVENTION DIFFERENCE DETECTED"
                )

        # ====================================================
        # FINAL SUMMARY
        # ====================================================

        header(
            "FINAL RECONSTRUCTION SUMMARY"
        )

        print(
            "SYMBOLS READY      :",
            symbols_ready
        )

        print(
            "TOTAL EXACT        :",
            total_exact
        )

        print(
            "TOTAL MISMATCH     :",
            total_mismatch
        )

        print(
            "TOTAL UNRESOLVED   :",
            total_unresolved
        )

        print()

        if total_mismatch > 0:
            status = "CONVENTION_DIFFERENCE_CONFIRMED"

        elif total_unresolved > 0:
            status = "REVIEW_REQUIRED"

        else:
            status = "STANDARD_CONFORMANT"

        print(
            "RECONSTRUCTION STATUS :",
            status
        )

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )
        print(
            "AUDIT COMPLETE"
        )

        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())