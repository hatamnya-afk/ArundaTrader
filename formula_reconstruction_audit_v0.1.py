import sqlite3
import math


# ============================================================
# ARUNDA FORMULA RECONSTRUCTION / VERIFICATION AUDIT v0.1
# ============================================================
#
# MODE:
#     READ ONLY
#
# IMPORTANT:
#     This audit DOES NOT import or call formulas from
#     market_data_engine.py.
#
#     Every formula is independently reconstructed here.
#
# DATABASE WRITES:
#     NONE
#
# ============================================================


DB = "arunda.db"

ANALYSIS_SOURCE = "CMC_SNAPSHOT_ANALYSIS_v0.2"
SNAPSHOT_SOURCE = "COINMARKETCAP"
TIMEFRAME = "SNAPSHOT"

LOOKBACK = 120
MIN_HISTORY = 60

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10

SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# DATABASE
# ============================================================

def connect_database():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# TARGET RESOLUTION
# ============================================================

def find_analysis_target(conn, symbol):

    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            ema20,
            ema50,
            rsi14,
            macd,
            macd_signal,
            macd_hist,
            atr14,
            adx14,
            bb_middle,
            bb_upper,
            bb_lower,
            bb_width,
            volume_sma20,
            volume_ratio,
            volatility,
            technical_score
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            symbol,
            ANALYSIS_SOURCE,
            TIMEFRAME,
        ),
    ).fetchone()


def get_raw_window(
    conn,
    symbol,
    source_timestamp,
    limit,
):

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            volume
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND source_timestamp <= ?
            AND close IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            TIMEFRAME,
            source_timestamp,
            limit,
        ),
    ).fetchall()

    return list(reversed(rows))


# ============================================================
# NUMERICAL HELPERS
# ============================================================

def mean(values):

    if not values:
        return None

    return sum(values) / len(values)


def population_stdev(values):

    if len(values) < 2:
        return None

    avg = mean(values)

    variance = sum(
        (x - avg) ** 2
        for x in values
    ) / len(values)

    return math.sqrt(variance)


def compare_values(stored, rebuilt):

    if stored is None and rebuilt is None:
        return True, 0.0, 0.0

    if stored is None or rebuilt is None:
        return False, None, None

    stored = float(stored)
    rebuilt = float(rebuilt)

    abs_error = abs(stored - rebuilt)

    denominator = max(
        abs(stored),
        abs(rebuilt),
        1e-300,
    )

    rel_error = abs_error / denominator

    exact = (
        abs_error <= ABS_TOLERANCE
        or rel_error <= REL_TOLERANCE
    )

    return exact, abs_error, rel_error


def print_formula_result(
    name,
    stored,
    rebuilt,
):

    exact, abs_error, rel_error = compare_values(
        stored,
        rebuilt,
    )

    status = "EXACT" if exact else "MISMATCH"

    print()
    print(f"FORMULA : {name}")
    print(f"STORED  : {stored}")
    print(f"REBUILT : {rebuilt}")
    print(f"ABS ERR : {abs_error}")
    print(f"REL ERR : {rel_error}")
    print(f"STATUS  : {status}")

    return exact


# ============================================================
# EMA
# ============================================================

def reconstruct_ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2.0 / (period + 1.0)

    result = mean(
        values[:period]
    )

    for price in values[period:]:

        result = (
            (price - result)
            * multiplier
            + result
        )

    return result


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

    avg_gain = mean(
        gains[:period]
    )

    avg_loss = mean(
        losses[:period]
    )

    for i in range(
        period,
        len(gains),
    ):

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

def reconstruct_ema_series(values, period):

    if len(values) < period:
        return []

    multiplier = 2.0 / (period + 1.0)

    result = mean(
        values[:period]
    )

    series = [result]

    for price in values[period:]:

        result = (
            (price - result)
            * multiplier
            + result
        )

        series.append(result)

    return series


def reconstruct_macd(values):

    if len(values) < 35:
        return (
            None,
            None,
            None,
        )

    ema12 = reconstruct_ema_series(
        values,
        12,
    )

    ema26 = reconstruct_ema_series(
        values,
        26,
    )

    if not ema12 or not ema26:
        return (
            None,
            None,
            None,
        )

    offset = 26 - 12

    macd_values = []

    for i in range(
        len(ema26)
    ):

        idx = i + offset

        if idx >= len(ema12):
            break

        macd_values.append(
            ema12[idx]
            - ema26[i]
        )

    if len(macd_values) < 9:
        return (
            None,
            None,
            None,
        )

    signal_series = reconstruct_ema_series(
        macd_values,
        9,
    )

    if not signal_series:
        return (
            None,
            None,
            None,
        )

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
    period=14,
):

    if len(closes) <= period:
        return None

    true_ranges = []

    for i in range(
        1,
        len(closes),
    ):

        high = highs[i]
        low = lows[i]
        previous_close = closes[i - 1]

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
    period=14,
):

    if len(closes) < (
        period * 2 + 1
    ):
        return None

    trs = []
    plus_dm = []
    minus_dm = []

    for i in range(
        1,
        len(closes),
    ):

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

    for i in range(
        period,
        len(trs),
    ):

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
    deviations=2.0,
):

    if len(values) < period:
        return (
            None,
            None,
            None,
            None,
        )

    window = values[-period:]

    middle = mean(window)

    deviation = population_stdev(window)

    if middle is None:
        return (
            None,
            None,
            None,
            None,
        )

    if deviation is None:
        deviation = 0.0

    upper = (
        middle
        + deviations
        * deviation
    )

    lower = (
        middle
        - deviations
        * deviation
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
    period=20,
):

    if len(volumes) < period:
        return (
            None,
            None,
        )

    sma = mean(
        volumes[-period:]
    )

    current = volumes[-1]

    if sma is None or sma == 0:

        return (
            sma,
            None,
        )

    ratio = current / sma

    return (
        sma,
        ratio,
    )


# ============================================================
# VOLATILITY
# ============================================================

def reconstruct_volatility(
    closes,
    period=20,
):

    if len(closes) < period + 1:
        return None

    returns = []

    start = max(
        1,
        len(closes) - period,
    )

    for i in range(
        start,
        len(closes),
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

    return population_stdev(
        returns
    )


# ============================================================
# TECHNICAL SCORE
# ============================================================

def reconstruct_technical_score(
    close,
    ema20,
    ema50,
    rsi14,
    macd,
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
        macd is not None
        and macd_signal is not None
    ):

        if macd > macd_signal:

            score += 20.0

        elif macd < macd_signal:

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
            score,
        ),
    )

    return score


# ============================================================
# RECONSTRUCTION
# ============================================================

def reconstruct(rows):

    closes = []
    highs = []
    lows = []
    volumes = []

    for row in rows:

        close = float(row["close"])

        if row["volume"] is None:
            volume = 0.0
        else:
            volume = float(row["volume"])

        closes.append(close)

        # IMPORTANT:
        # CMC snapshots do not contain real OHLC.
        #
        # Therefore, exactly like the source architecture,
        # close is used as observation boundary for high/low.
        #
        highs.append(close)
        lows.append(close)

        volumes.append(volume)

    close = closes[-1]

    ema20 = reconstruct_ema(
        closes,
        20,
    )

    ema50 = reconstruct_ema(
        closes,
        50,
    )

    rsi14 = reconstruct_rsi(
        closes,
        14,
    )

    (
        macd,
        macd_signal,
        macd_hist,
    ) = reconstruct_macd(
        closes
    )

    atr14 = reconstruct_atr(
        highs,
        lows,
        closes,
        14,
    )

    adx14 = reconstruct_adx(
        highs,
        lows,
        closes,
        14,
    )

    (
        bb_middle,
        bb_upper,
        bb_lower,
        bb_width,
    ) = reconstruct_bollinger(
        closes,
        20,
        2.0,
    )

    (
        volume_sma20,
        volume_ratio,
    ) = reconstruct_volume_metrics(
        volumes,
        20,
    )

    volatility = reconstruct_volatility(
        closes,
        20,
    )

    technical_score = reconstruct_technical_score(
        close,
        ema20,
        ema50,
        rsi14,
        macd,
        macd_signal,
        adx14,
        bb_middle,
        volume_ratio,
    )

    return {
        "ema20": ema20,
        "ema50": ema50,
        "rsi14": rsi14,
        "macd": macd,
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
        "volatility": volatility,
        "technical_score": technical_score,
    }


# ============================================================
# MAIN AUDIT
# ============================================================

def main():

    print("=" * 100)
    print("ARUNDA FORMULA RECONSTRUCTION / VERIFICATION AUDIT v0.1")
    print("=" * 100)

    print("MODE              : READ ONLY")
    print(f"DATABASE          : {DB}")
    print(f"ANALYSIS SOURCE   : {ANALYSIS_SOURCE}")
    print(f"SNAPSHOT SOURCE   : {SNAPSHOT_SOURCE}")
    print(f"LOOKBACK          : {LOOKBACK}")
    print(f"MIN HISTORY       : {MIN_HISTORY}")
    print(f"ABS TOLERANCE     : {ABS_TOLERANCE}")
    print(f"REL TOLERANCE     : {REL_TOLERANCE}")

    print("=" * 100)

    conn = None

    total_exact = 0
    total_mismatch = 0
    total_blocked = 0

    try:

        conn = connect_database()

        for symbol in SYMBOLS:

            print()
            print("=" * 100)
            print(f"SYMBOL : {symbol}")
            print("-" * 100)

            analysis = find_analysis_target(
                conn,
                symbol,
            )

            if analysis is None:

                print(
                    "TARGET STATUS : BLOCKED"
                )

                print(
                    "REASON        : ANALYSIS_TARGET_NOT_FOUND"
                )

                total_blocked += 1

                continue

            source_timestamp = (
                analysis["source_timestamp"]
            )

            print(
                f"ANALYSIS ID   : {analysis['id']}"
            )

            print(
                f"SOURCE TIME   : {source_timestamp}"
            )

            print(
                f"STORED CLOSE  : {analysis['close']}"
            )

            rows = get_raw_window(
                conn,
                symbol,
                source_timestamp,
                LOOKBACK,
            )

            print(
                f"WINDOW        : {len(rows)} snapshots"
            )

            if len(rows) < MIN_HISTORY:

                print(
                    "TARGET STATUS : BLOCKED"
                )

                print(
                    f"REASON        : "
                    f"INSUFFICIENT_HISTORY_{len(rows)}"
                )

                total_blocked += 1

                continue

            rebuilt = reconstruct(rows)

            print()
            print(
                "FORMULA COMPARISON"
            )

            print("-" * 100)

            formula_pairs = [

                (
                    "EMA20",
                    analysis["ema20"],
                    rebuilt["ema20"],
                ),

                (
                    "EMA50",
                    analysis["ema50"],
                    rebuilt["ema50"],
                ),

                (
                    "RSI14",
                    analysis["rsi14"],
                    rebuilt["rsi14"],
                ),

                (
                    "MACD",
                    analysis["macd"],
                    rebuilt["macd"],
                ),

                (
                    "MACD_SIGNAL",
                    analysis["macd_signal"],
                    rebuilt["macd_signal"],
                ),

                (
                    "MACD_HIST",
                    analysis["macd_hist"],
                    rebuilt["macd_hist"],
                ),

                (
                    "ATR14",
                    analysis["atr14"],
                    rebuilt["atr14"],
                ),

                (
                    "ADX14",
                    analysis["adx14"],
                    rebuilt["adx14"],
                ),

                (
                    "BB_MIDDLE",
                    analysis["bb_middle"],
                    rebuilt["bb_middle"],
                ),

                (
                    "BB_UPPER",
                    analysis["bb_upper"],
                    rebuilt["bb_upper"],
                ),

                (
                    "BB_LOWER",
                    analysis["bb_lower"],
                    rebuilt["bb_lower"],
                ),

                (
                    "BB_WIDTH",
                    analysis["bb_width"],
                    rebuilt["bb_width"],
                ),

                (
                    "VOLUME_SMA20",
                    analysis["volume_sma20"],
                    rebuilt["volume_sma20"],
                ),

                (
                    "VOLUME_RATIO",
                    analysis["volume_ratio"],
                    rebuilt["volume_ratio"],
                ),

                (
                    "VOLATILITY",
                    analysis["volatility"],
                    rebuilt["volatility"],
                ),

                (
                    "TECHNICAL_SCORE",
                    analysis["technical_score"],
                    rebuilt["technical_score"],
                ),
            ]

            symbol_exact = 0
            symbol_mismatch = 0

            for (
                name,
                stored,
                reconstructed,
            ) in formula_pairs:

                exact = print_formula_result(
                    name,
                    stored,
                    reconstructed,
                )

                if exact:

                    symbol_exact += 1
                    total_exact += 1

                else:

                    symbol_mismatch += 1
                    total_mismatch += 1

            print()
            print("-" * 100)

            print(
                f"SYMBOL SUMMARY : "
                f"EXACT={symbol_exact} "
                f"MISMATCH={symbol_mismatch}"
            )

            if symbol_mismatch == 0:

                print(
                    "SYMBOL STATUS  : ALL FORMULAS EXACT"
                )

            else:

                print(
                    "SYMBOL STATUS  : FORMULA MISMATCH DETECTED"
                )

        print()
        print("=" * 100)
        print("FORMULA RECONSTRUCTION AUDIT SUMMARY")
        print("=" * 100)

        print(
            f"TOTAL EXACT    : {total_exact}"
        )

        print(
            f"TOTAL MISMATCH : {total_mismatch}"
        )

        print(
            f"TOTAL BLOCKED  : {total_blocked}"
        )

        print()

        if total_mismatch == 0:

            print(
                "FORMULA VERIFICATION STATUS : EXACT"
            )

        else:

            print(
                "FORMULA VERIFICATION STATUS : MISMATCH"
            )

        print("=" * 100)
        print("DATABASE WRITE OPERATIONS : NONE")
        print("AUDIT COMPLETE")
        print("=" * 100)

        return 0

    except Exception as exc:

        print()
        print("=" * 100)
        print("FORMULA RECONSTRUCTION AUDIT ERROR")
        print("=" * 100)
        print(repr(exc))
        print("=" * 100)

        return 1

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())