import sqlite3
import math


# ============================================================
# ARUNDA TRADER
# FORMULA RECONSTRUCTION / VERIFICATION AUDIT v0.1
# ============================================================
#
# MODE:
#     READ ONLY
#
# PURPOSE:
#     Independently reconstruct MARKET_DATA_CMC_SNAPSHOT_v0.2
#     numerical formulas and compare against stored market_data.
#
# IMPORTANT:
#     This script intentionally does NOT import formulas from
#     market_data_engine.py.
#
# DATABASE WRITES:
#     NONE
#
# ============================================================


DB = "arunda.db"

SOURCE_SNAPSHOT = "COINMARKETCAP"
SOURCE_ANALYSIS = "CMC_SNAPSHOT_ANALYSIS_v0.2"

TIMEFRAME = "SNAPSHOT"

LOOKBACK = 150

PERIOD_RSI = 14
PERIOD_ATR = 14
PERIOD_ADX = 14
PERIOD_BB = 20
PERIOD_VOLUME = 20
PERIOD_VOLATILITY = 20

SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
]

# Floating-point verification tolerance.
ABS_TOL = 1e-10
REL_TOL = 1e-10


# ============================================================
# DATABASE
# ============================================================

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# BASIC NUMERICAL HELPERS
# ============================================================

def mean(values):

    if not values:
        return None

    return sum(values) / len(values)


def stdev(values):

    if len(values) < 2:
        return None

    avg = mean(values)

    variance = sum(
        (x - avg) ** 2
        for x in values
    ) / len(values)

    return math.sqrt(variance)


def close_enough(a, b):

    if a is None and b is None:
        return True

    if a is None or b is None:
        return False

    return math.isclose(
        float(a),
        float(b),
        rel_tol=REL_TOL,
        abs_tol=ABS_TOL,
    )


def delta(a, b):

    if a is None or b is None:
        return None

    return float(a) - float(b)


# ============================================================
# EMA
# ============================================================

def reconstruct_ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2.0 / (period + 1.0)

    result = mean(values[:period])

    for price in values[period:]:
        result = (
            (price - result)
            * multiplier
            + result
        )

    return result


def reconstruct_ema_series(values, period):

    if len(values) < period:
        return []

    multiplier = 2.0 / (period + 1.0)

    result = mean(values[:period])

    series = [result]

    for price in values[period:]:

        result = (
            (price - result)
            * multiplier
            + result
        )

        series.append(result)

    return series


# ============================================================
# RSI
# ============================================================

def reconstruct_rsi(values, period=14):

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = (
            values[i]
            - values[i - 1]
        )

        if change > 0:

            gains.append(change)
            losses.append(0.0)

        else:

            gains.append(0.0)
            losses.append(abs(change))

    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])

    for i in range(period, len(gains)):

        avg_gain = (
            (
                avg_gain
                * (period - 1)
            )
            + gains[i]
        ) / period

        avg_loss = (
            (
                avg_loss
                * (period - 1)
            )
            + losses[i]
        ) / period

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = avg_gain / avg_loss

    return (
        100.0
        - (
            100.0
            / (1.0 + rs)
        )
    )


# ============================================================
# MACD
# ============================================================

def reconstruct_macd(values):

    if len(values) < 35:
        return None, None, None

    ema12 = reconstruct_ema_series(
        values,
        12
    )

    ema26 = reconstruct_ema_series(
        values,
        26
    )

    if not ema12 or not ema26:
        return None, None, None

    offset = 26 - 12

    macd_values = []

    for i in range(len(ema26)):

        idx = i + offset

        if idx >= len(ema12):
            break

        macd_values.append(
            ema12[idx]
            - ema26[i]
        )

    if len(macd_values) < 9:
        return None, None, None

    signal_series = reconstruct_ema_series(
        macd_values,
        9
    )

    if not signal_series:
        return None, None, None

    macd_value = macd_values[-1]
    signal_value = signal_series[-1]

    histogram = (
        macd_value
        - signal_value
    )

    return (
        macd_value,
        signal_value,
        histogram,
    )


# ============================================================
# ATR
# ============================================================

def reconstruct_atr(
    highs,
    lows,
    closes,
    period=14
):

    if len(closes) <= period:
        return None

    true_ranges = []

    for i in range(1, len(closes)):

        high = highs[i]
        low = lows[i]

        previous_close = (
            closes[i - 1]
        )

        tr = max(
            high - low,
            abs(
                high
                - previous_close
            ),
            abs(
                low
                - previous_close
            ),
        )

        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    result = mean(
        true_ranges[:period]
    )

    for value in true_ranges[period:]:

        result = (
            (
                result
                * (period - 1)
            )
            + value
        ) / period

    return result


# ============================================================
# ADX
# ============================================================

def reconstruct_adx(
    highs,
    lows,
    closes,
    period=14
):

    if len(closes) < (
        period * 2 + 1
    ):
        return None

    trs = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(closes)):

        up_move = (
            highs[i]
            - highs[i - 1]
        )

        down_move = (
            lows[i - 1]
            - lows[i]
        )

        if (
            up_move > down_move
            and up_move > 0
        ):
            pdm = up_move
        else:
            pdm = 0.0

        if (
            down_move > up_move
            and down_move > 0
        ):
            mdm = down_move
        else:
            mdm = 0.0

        tr = max(
            highs[i] - lows[i],
            abs(
                highs[i]
                - closes[i - 1]
            ),
            abs(
                lows[i]
                - closes[i - 1]
            ),
        )

        trs.append(tr)
        plus_dm.append(pdm)
        minus_dm.append(mdm)

    if len(trs) < period:
        return None

    atr_value = mean(
        trs[:period]
    )

    plus_value = mean(
        plus_dm[:period]
    )

    minus_value = mean(
        minus_dm[:period]
    )

    dx_values = []

    for i in range(period, len(trs)):

        atr_value = (
            (
                atr_value
                * (period - 1)
            )
            + trs[i]
        ) / period

        plus_value = (
            (
                plus_value
                * (period - 1)
            )
            + plus_dm[i]
        ) / period

        minus_value = (
            (
                minus_value
                * (period - 1)
            )
            + minus_dm[i]
        ) / period

        if atr_value == 0:
            continue

        plus_di = (
            100.0
            * plus_value
            / atr_value
        )

        minus_di = (
            100.0
            * minus_value
            / atr_value
        )

        denominator = (
            plus_di
            + minus_di
        )

        if denominator == 0:
            continue

        dx = (
            100.0
            * abs(
                plus_di
                - minus_di
            )
            / denominator
        )

        dx_values.append(dx)

    if len(dx_values) < period:
        return None

    adx_value = mean(
        dx_values[:period]
    )

    for value in dx_values[period:]:

        adx_value = (
            (
                adx_value
                * (period - 1)
            )
            + value
        ) / period

    return adx_value


# ============================================================
# BOLLINGER
# ============================================================

def reconstruct_bollinger(
    values,
    period=20,
    deviations=2.0
):

    if len(values) < period:
        return None, None, None, None

    window = values[-period:]

    middle = mean(window)

    deviation = stdev(window)

    if middle is None:
        return None, None, None, None

    if deviation is None:
        deviation = 0.0

    upper = (
        middle
        + deviations * deviation
    )

    lower = (
        middle
        - deviations * deviation
    )

    if middle != 0:

        width = (
            upper - lower
        ) / middle

    else:

        width = 0.0

    return (
        middle,
        upper,
        lower,
        width,
    )


# ============================================================
# VOLUME
# ============================================================

def reconstruct_volume_metrics(
    volumes,
    period=20
):

    if len(volumes) < period:
        return None, None

    sma = mean(
        volumes[-period:]
    )

    current = volumes[-1]

    if sma is None or sma == 0:
        return sma, None

    ratio = current / sma

    return sma, ratio


# ============================================================
# VOLATILITY
# ============================================================

def reconstruct_volatility(
    closes,
    period=20
):

    if len(closes) < (
        period + 1
    ):
        return None

    returns = []

    start = max(
        1,
        len(closes) - period
    )

    for i in range(
        start,
        len(closes)
    ):

        previous = closes[i - 1]
        current = closes[i]

        if previous == 0:
            continue

        returns.append(
            (
                current - previous
            )
            / previous
            * 100.0
        )

    if len(returns) < 2:
        return None

    return stdev(returns)


# ============================================================
# TECHNICAL SCORE
# ============================================================

def reconstruct_score(
    close,
    ema20,
    ema50,
    rsi14,
    macd_value,
    macd_signal,
    adx14,
    bb_middle,
    volume_ratio,
):

    score = 0.0

    # EMA TREND

    if (
        ema20 is not None
        and ema50 is not None
    ):

        if (
            close > ema20
            and ema20 > ema50
        ):
            score += 25.0

        elif (
            close < ema20
            and ema20 < ema50
        ):
            score -= 25.0

    # RSI

    if rsi14 is not None:

        if rsi14 >= 60:
            score += 15.0

        elif rsi14 <= 40:
            score -= 15.0

    # MACD

    if (
        macd_value is not None
        and macd_signal is not None
    ):

        if macd_value > macd_signal:
            score += 20.0

        elif macd_value < macd_signal:
            score -= 20.0

    # ADX

    if adx14 is not None:

        if adx14 >= 25:

            if (
                ema20 is not None
                and ema50 is not None
            ):

                if ema20 > ema50:
                    score += 10.0

                elif ema20 < ema50:
                    score -= 10.0

    # BOLLINGER

    if bb_middle is not None:

        if close > bb_middle:
            score += 10.0

        elif close < bb_middle:
            score -= 10.0

    # VOLUME

    if (
        volume_ratio is not None
        and volume_ratio >= 1.2
    ):

        if score > 0:
            score += 5.0

        elif score < 0:
            score -= 5.0

    score = max(
        -100.0,
        min(
            100.0,
            score
        )
    )

    return score


# ============================================================
# LOAD EXACT ENGINE WINDOW
# ============================================================

def load_snapshot_window(
    conn,
    symbol
):

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            symbol,
            close,
            volume,
            source_timestamp
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND close IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (
            symbol,
            SOURCE_SNAPSHOT,
            TIMEFRAME,
            LOOKBACK,
        )
    ).fetchall()

    return rows


# ============================================================
# LOAD STORED ANALYSIS
# ============================================================

def load_stored_analysis(
    conn,
    symbol,
    source_timestamp
):

    return conn.execute(
        """
        SELECT *
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND source_timestamp = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            symbol,
            SOURCE_ANALYSIS,
            TIMEFRAME,
            source_timestamp,
        )
    ).fetchone()


# ============================================================
# RECONSTRUCTION
# ============================================================

def reconstruct(rows):

    closes = [
        float(row["close"])
        for row in rows
    ]

    volumes = [
        float(row["volume"])
        if row["volume"] is not None
        else 0.0
        for row in rows
    ]

    # IMPORTANT:
    # Reproduce engine's deliberate close-derived
    # pseudo-OHLC behavior.
    highs = list(closes)
    lows = list(closes)

    close = closes[-1]

    ema20 = reconstruct_ema(
        closes,
        20
    )

    ema50 = reconstruct_ema(
        closes,
        50
    )

    rsi14 = reconstruct_rsi(
        closes,
        14
    )

    (
        macd_value,
        macd_signal,
        macd_hist,
    ) = reconstruct_macd(
        closes
    )

    atr14 = reconstruct_atr(
        highs,
        lows,
        closes,
        14
    )

    adx14 = reconstruct_adx(
        highs,
        lows,
        closes,
        14
    )

    (
        bb_middle,
        bb_upper,
        bb_lower,
        bb_width,
    ) = reconstruct_bollinger(
        closes,
        20,
        2.0
    )

    (
        volume_sma20,
        volume_ratio,
    ) = reconstruct_volume_metrics(
        volumes,
        20
    )

    volatility_value = reconstruct_volatility(
        closes,
        20
    )

    technical_score_value = reconstruct_score(
        close,
        ema20,
        ema50,
        rsi14,
        macd_value,
        macd_signal,
        adx14,
        bb_middle,
        volume_ratio,
    )

    return {
        "close": close,
        "volume": volumes[-1],

        "ema20": ema20,
        "ema50": ema50,

        "rsi14": rsi14,

        "macd": macd_value,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,

        "atr14": atr14,
        "adx14": adx14,

        "bb_middle": bb_middle,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_width": bb_width,

        "volume_sma20": volume_sma20,
        "volume_ratio": volume_ratio,

        "volatility": volatility_value,

        "technical_score": technical_score_value,
    }


# ============================================================
# FIELD VERIFICATION
# ============================================================

FIELDS = [
    "close",
    "volume",

    "ema20",
    "ema50",

    "rsi14",

    "macd",
    "macd_signal",
    "macd_hist",

    "atr14",
    "adx14",

    "bb_middle",
    "bb_upper",
    "bb_lower",
    "bb_width",

    "volume_sma20",
    "volume_ratio",

    "volatility",

    "technical_score",
]


def verify_field(
    field,
    stored,
    reconstructed
):

    a = stored[field]
    b = reconstructed[field]

    status = (
        "EXACT"
        if close_enough(a, b)
        else "MISMATCH"
    )

    return {
        "field": field,
        "stored": a,
        "reconstructed": b,
        "delta": delta(
            b,
            a
        ),
        "status": status,
    }


# ============================================================
# AUDIT
# ============================================================

def audit_symbol(
    conn,
    symbol
):

    rows = load_snapshot_window(
        conn,
        symbol
    )

    print()
    print("=" * 100)
    print(f"SYMBOL : {symbol}")
    print(f"WINDOW : {len(rows)} snapshots")
    print("=" * 100)

    if len(rows) < 60:

        print(
            f"INSUFFICIENT WINDOW "
            f"({len(rows)} < 60)"
        )

        return

    latest_snapshot = rows[-1]

    source_timestamp = (
        latest_snapshot["source_timestamp"]
    )

    stored = load_stored_analysis(
        conn,
        symbol,
        source_timestamp
    )

    if stored is None:

        print(
            "NO STORED ANALYSIS ROW "
            f"FOR SOURCE_TIMESTAMP={source_timestamp}"
        )

        return

    reconstructed = reconstruct(rows)

    print(
        f"SNAPSHOT ID       : "
        f"{latest_snapshot['id']}"
    )

    print(
        f"SNAPSHOT TIMESTAMP: "
        f"{latest_snapshot['timestamp']}"
    )

    print(
        f"SOURCE TIMESTAMP  : "
        f"{source_timestamp}"
    )

    print()

    exact_count = 0
    mismatch_count = 0

    for field in FIELDS:

        result = verify_field(
            field,
            stored,
            reconstructed
        )

        if result["status"] == "EXACT":
            exact_count += 1
        else:
            mismatch_count += 1

        print(
            f"{field:<18} | "
            f"STATUS={result['status']:<9} | "
            f"STORED={result['stored']} | "
            f"RECON={result['reconstructed']} | "
            f"DELTA={result['delta']}"
        )

    print()
    print(
        f"EXACT     : {exact_count}"
    )

    print(
        f"MISMATCH  : {mismatch_count}"
    )

    if mismatch_count == 0:

        print(
            "FORMULA VERIFICATION : PASS"
        )

    else:

        print(
            "FORMULA VERIFICATION : FAIL"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA FORMULA RECONSTRUCTION / "
        "VERIFICATION AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE              : READ ONLY"
    )

    print(
        "DATABASE           : "
        f"{DB}"
    )

    print(
        "WRITE OPERATIONS   : NONE"
    )

    print(
        "SOURCE SNAPSHOT    : "
        f"{SOURCE_SNAPSHOT}"
    )

    print(
        "SOURCE ANALYSIS    : "
        f"{SOURCE_ANALYSIS}"
    )

    print(
        "LOOKBACK           : "
        f"{LOOKBACK}"
    )

    print(
        "TOLERANCE          : "
        f"abs={ABS_TOL}, rel={REL_TOL}"
    )

    print("=" * 100)

    conn = None

    try:

        conn = connect()

        for symbol in SYMBOLS:

            audit_symbol(
                conn,
                symbol
            )

        print()
        print("=" * 100)
        print(
            "FORMULA RECONSTRUCTION AUDIT COMPLETE"
        )
        print("=" * 100)

        return 0

    except Exception as exc:

        print()
        print(
            "AUDIT ERROR:"
        )

        print(
            repr(exc)
        )

        return 1

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )