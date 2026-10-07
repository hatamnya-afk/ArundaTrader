import sqlite3
import math
import time
import os
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# ARUNDA MARKET DATA ENGINE v0.4
# ============================================================
#
# PURPOSE
# -------
# Analyze REAL CMC snapshots already stored in market_data.
#
# NO:
#   - Binance
#   - synthetic candles
#   - fabricated OHLC
#   - ATR/ADX from fake OHLC
#   - interpolation
#   - forward fill
#   - back fill
#
# PIPELINE
# -------
#
# CMC SNAPSHOTS
#       â†“
# Latest N snapshots
#       â†“
# OLD -> NEW ordering
#       â†“
# EMA / RSI / MACD / Bollinger
# Volume / Volatility
#       â†“
# Normalized Snapshot Technical Score
#       â†“
# market_data
#
# ============================================================


# ============================================================
# CONFIG
# ============================================================

DB = "arunda.db"

ENGINE_VERSION = "MARKET_DATA_CMC_SNAPSHOT_v0.4"

SOURCE = "CMC_SNAPSHOT_ANALYSIS_v0.4"

SNAPSHOT_SOURCE = "COINMARKETCAP"

TIMEFRAME = "SNAPSHOT"

# ------------------------------------------------------------
# PRODUCTION OHLCV CONTRACT
# ------------------------------------------------------------
OHLCV_TIMEFRAME = "1h"
OHLCV_SOURCE = "KUCOIN_SPOT"
CMC_OHLCV_URL = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/ohlcv/historical"
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5
OHLCV_LOOKBACK = 100

LOOKBACK = 150

MIN_HISTORY = 60


SYMBOLS = [
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


# ============================================================
# DATABASE
# ============================================================

def connect_database():

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row

    return conn


def ensure_schema(conn):

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,

            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,

            ema20 REAL,
            ema50 REAL,

            rsi14 REAL,

            macd REAL,
            macd_signal REAL,
            macd_hist REAL,

            atr14 REAL,
            adx14 REAL,

            bb_middle REAL,
            bb_upper REAL,
            bb_lower REAL,
            bb_width REAL,

            volume_sma20 REAL,
            volume_ratio REAL,

            volatility REAL,

            technical_score REAL,

            source TEXT,
            source_timestamp TEXT,

            price_change_1h REAL,
            price_change_24h REAL,
            market_cap REAL,
            volume_24h REAL,
            source_latency_ms REAL,
            engine_version TEXT
        )
        """
    )

    conn.commit()


# ============================================================
# UTILITY
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_float(value):

    try:

        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except Exception:

        return None


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

    return math.sqrt(
        variance
    )


# ============================================================
# REAL 1h OHLCV
# ============================================================

def load_cmc_api_key():
    try:
        import market_snapshot_engine
        key = getattr(
            market_snapshot_engine,
            "API_KEY",
            None,
        )
        if key:
            return str(key).strip()
    except Exception:
        pass

    for name in (
        "CMC_API_KEY",
        "COINMARKETCAP_API_KEY",
        "X_CMC_PRO_API_KEY",
    ):
        value = os.environ.get(name)
        if value:
            return value.strip()

    return None


def validate_real_ohlcv_candle(candle):
    required = (
        "asset",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "timeframe",
        "source",
    )

    if any(candle.get(k) is None for k in required):
        return False

    if candle["timeframe"] != OHLCV_TIMEFRAME:
        return False

    if not str(candle["source"]).startswith(OHLCV_SOURCE + ":"):
        return False

    values = [
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"],
        candle["volume"],
    ]

    for value in values:
        if isinstance(value, bool):
            return False

        try:
            value = float(value)
        except Exception:
            return False

        if not math.isfinite(value):
            return False

    o = float(candle["open"])
    h = float(candle["high"])
    l = float(candle["low"])
    c = float(candle["close"])
    v = float(candle["volume"])

    if o <= 0 or h <= 0 or l <= 0 or c <= 0:
        return False

    if v < 0:
        return False

    if h < max(o, c):
        return False

    if l > min(o, c):
        return False

    if h < l:
        return False

    if not candle["timestamp"]:
        return False

    return True


def fetch_real_1h_ohlcv(
    symbol,
    count=OHLCV_LOOKBACK,
):
    """
    Production OHLCV source.

    Provider:
        Existing canonical KuCoin adapter.

    Rules:
        REAL DATA ONLY
        1h ONLY
        CLOSED CANDLES ONLY
        NO SYNTHETIC
        NO INTERPOLATION
        NO FILL
        NO BACKFILL
        NO CMC
    """

    import importlib.util

    adapter_path = (
        Path(__file__).resolve().parent
        / "public_market_data_kucoin.py"
    )

    if not adapter_path.exists():
        raise RuntimeError(
            "KUCOIN_ADAPTER_NOT_FOUND"
        )

    spec = importlib.util.spec_from_file_location(
        "arunda_public_market_data_kucoin",
        adapter_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "KUCOIN_ADAPTER_LOAD_FAILED"
        )

    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)

    required = (
        "fetch_kucoin",
        "normalize",
        "validate_candle",
    )

    for name in required:
        if not hasattr(adapter, name):
            raise RuntimeError(
                f"KUCOIN_ADAPTER_MISSING:{name}"
            )

    # SYMBOLS in this engine are canonical asset names.
    # Existing adapter owns asset -> KuCoin symbol mapping.
    assets = getattr(
        adapter,
        "ASSETS",
        {},
    )

    if symbol not in assets:
        raise RuntimeError(
            f"KUCOIN_ASSET_MAPPING_MISSING:{symbol}"
        )

    provider_symbol = assets[symbol]

    retrieved_at = (
        datetime.now(timezone.utc).isoformat()
    )

    raw_bars = adapter.fetch_kucoin(
        provider_symbol,
        count=int(count),
    )

    if not isinstance(raw_bars, list):
        raise RuntimeError(
            f"{symbol}: INVALID_KUCOIN_BARS"
        )

    candles = []

    for bar in raw_bars:

        if not isinstance(bar, list):
            continue

        if len(bar) < 6:
            continue

        try:
            candle = adapter.normalize(
                symbol,
                provider_symbol,
                bar,
                retrieved_at,
            )

            adapter.validate_candle(
                candle
            )

        except (
            ValueError,
            TypeError,
        ):
            continue

        # Production engine internal shape.
        internal = {
            "asset": symbol,
            "timestamp": int(
                candle["timestamp"]
            ),
            "open": float(
                candle["open"]
            ),
            "high": float(
                candle["high"]
            ),
            "low": float(
                candle["low"]
            ),
            "close": float(
                candle["close"]
            ),
            "volume": float(
                candle["volume"]
            ),
            "timeframe": "1h",

            # Preserve real provenance.
            "source": candle[
                "source_id"
            ],
            "source_id": candle[
                "source_id"
            ],
            "source_type": candle[
                "source_type"
            ],
            "source_timestamp": candle[
                "source_timestamp"
            ],
            "retrieved_at": candle[
                "retrieved_at"
            ],
        }

        if not validate_real_ohlcv_candle(
            internal
        ):
            continue

        candles.append(
            internal
        )

    if not candles:
        raise RuntimeError(
            f"{symbol}: NO_VALID_KUCOIN_1H_OHLCV"
        )

    # Oldest -> newest.
    candles.sort(
        key=lambda row: row["timestamp"]
    )

    # Remove duplicate timestamps.
    unique = {}
    for candle in candles:
        unique[
            candle["timestamp"]
        ] = candle

    candles = list(
        sorted(
            unique.values(),
            key=lambda row: row["timestamp"],
        )
    )

    # Explicitly exclude current/open candle.
    now = int(
        datetime.now(timezone.utc).timestamp()
    )

    current_hour = (
        now
        - (
            now % 3600
        )
    )

    candles = [
        candle
        for candle in candles
        if candle["timestamp"]
        < current_hour
    ]

    if len(candles) < ATR_PERIOD:
        raise RuntimeError(
            f"{symbol}: INSUFFICIENT_REAL_1H_CONTEXT:"
            f"{len(candles)}<{ATR_PERIOD}"
        )

    # Hard continuity validation.
    for index in range(
        1,
        len(candles),
    ):
        previous = candles[
            index - 1
        ]["timestamp"]

        current = candles[
            index
        ]["timestamp"]

        if (
            current - previous
            != 3600
        ):
            raise RuntimeError(
                f"{symbol}: "
                "NON_CONTIGUOUS_REAL_1H_CONTEXT"
            )

    return candles

def calculate_real_atr14_series(candles):
    """
    Calculate ATR14 for each real 1h candle context.

    Ordering:
        OLD -> NEW

    Convention:
        Wilder smoothing

    The first ATR14 becomes available at candle 14.
    No value is copied backward or forward.
    """

    if len(candles) < ATR_PERIOD:
        return [None] * len(candles)

    true_ranges = []

    for index, candle in enumerate(candles):

        high = float(candle["high"])
        low = float(candle["low"])

        if index == 0:
            tr = high - low
        else:
            previous_close = float(
                candles[index - 1]["close"]
            )

            tr = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        if not math.isfinite(tr) or tr < 0:
            return [None] * len(candles)

        true_ranges.append(tr)

    atr_series = [None] * len(candles)

    atr = (
        sum(true_ranges[:ATR_PERIOD])
        / ATR_PERIOD
    )

    atr_series[ATR_PERIOD - 1] = float(atr)

    for index in range(
        ATR_PERIOD,
        len(true_ranges)
    ):
        tr = true_ranges[index]

        atr = (
            (
                atr * (ATR_PERIOD - 1)
            )
            + tr
        ) / ATR_PERIOD

        if not math.isfinite(atr) or atr <= 0:
            return [None] * len(candles)

        atr_series[index] = float(atr)

    return atr_series

def calculate_real_atr14(candles):
    if len(candles) < ATR_PERIOD:
        return None

    true_ranges = []

    for index, candle in enumerate(candles):
        high = float(candle["high"])
        low = float(candle["low"])

        if index == 0:
            tr = high - low
        else:
            previous_close = float(
                candles[index - 1]["close"]
            )

            tr = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        if not math.isfinite(tr) or tr < 0:
            return None

        true_ranges.append(tr)

    atr = (
        sum(true_ranges[:ATR_PERIOD])
        / ATR_PERIOD
    )

    # Existing project convention:
    # Wilder smoothing.
    for tr in true_ranges[ATR_PERIOD:]:
        atr = (
            (
                atr * (ATR_PERIOD - 1)
            )
            + tr
        ) / ATR_PERIOD

    if not math.isfinite(atr) or atr <= 0:
        return None

    return float(atr)


def calculate_runtime_stop_distance(atr14):
    atr14 = safe_float(atr14)

    if atr14 is None or atr14 <= 0:
        return None

    stop_distance = (
        atr14 * ATR_MULTIPLIER
    )

    if (
        not math.isfinite(stop_distance)
        or stop_distance <= 0
    ):
        return None

    return float(stop_distance)


def ingest_real_1h_ohlcv(snapshot_id=None):
    conn = connect_database()

    try:
        ensure_schema(conn)

        results = {}

        for symbol in SYMBOLS:

            candles = fetch_real_1h_ohlcv(
                symbol,
                count=OHLCV_LOOKBACK,
            )

            if not candles:
                results[symbol] = {
                    "asset": symbol,
                    "timeframe": OHLCV_TIMEFRAME,
                    "source": OHLCV_SOURCE,
                    "snapshot_id": snapshot_id,
                    "latest_candle_timestamp": None,
                    "candle_count": 0,
                    "valid_candles": 0,
                    "atr14": None,
                    "stop_distance": None,
                    "status": "UNAVAILABLE",
                }

                print(
                    f"OHLCV | {symbol:<5} | "
                    f"TIMEFRAME=1h | "
                    f"CANDLES=0 | "
                    f"ATR14=None | "
                    f"STOP_DISTANCE=BLOCKED"
                )
                continue

            atr_series = calculate_real_atr14_series(
                candles
            )

            # Preserve the existing scalar production function
            # as the authoritative latest-runtime ATR calculation.
            atr14 = calculate_real_atr14(candles)

            latest_candle_timestamp = (
                candles[-1]["timestamp"]
                if candles
                else None
            )

            stop_distance = (
                calculate_runtime_stop_distance(
                    atr14
                )
                if atr14 is not None
                else None
            )

            if atr14 is None:
                status = "BLOCKED"
            else:
                status = "READY"

            # Persist ONLY genuine KuCoin 1h OHLCV.
            #
            # Each historical candle receives only the ATR
            # belonging to that candle's own context.
            #
            # No retroactive propagation of the latest ATR.
            for index, candle in enumerate(candles):

                candle_atr14 = atr_series[index]

                conn.execute(
                    """
                    INSERT OR IGNORE INTO market_data (
                        timestamp,
                        symbol,
                        timeframe,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        atr14,
                        source,
                        source_timestamp,
                        engine_version
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candle["timestamp"],
                        candle["asset"],
                        OHLCV_TIMEFRAME,
                        candle["open"],
                        candle["high"],
                        candle["low"],
                        candle["close"],
                        candle["volume"],
                        candle_atr14,
                        OHLCV_SOURCE,
                        candle["timestamp"],
                        "MARKET_DATA_KUCOIN_OHLCV_1H_v1.1",
                    ),
                )

            conn.commit()

            results[symbol] = {
                "asset": symbol,
                "timeframe": OHLCV_TIMEFRAME,
                "source": OHLCV_SOURCE,
                "snapshot_id": snapshot_id,
                "latest_candle_timestamp": latest_candle_timestamp,
                "candle_count": len(candles),
                "valid_candles": len(candles),
                "atr14": atr14,
                "stop_distance": stop_distance,
                "status": status,
            }

            print(
                f"OHLCV | {symbol:<5} | "
                f"TIMEFRAME=1h | "
                f"CANDLES={len(candles)} | "
                f"ATR14={format_value(atr14, 10)} | "
                f"STOP_DISTANCE="
                f"{format_value(stop_distance, 10)} | "
                f"STATUS={status}"
            )

        return results

    finally:
        conn.close()

def get_snapshot_history(
    conn,
    symbol,
    limit=LOOKBACK
):
    """
    IMPORTANT

    We first select the MOST RECENT snapshots.

    Then the returned rows are reversed to:
        OLD -> NEW

    This is required because indicators are time-series
    calculations and must not run backwards in time.
    """

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            symbol,
            timeframe,
            close,
            volume,
            price_change_1h,
            price_change_24h,
            market_cap,
            volume_24h,
            source,
            source_timestamp,
            source_latency_ms
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = 'SNAPSHOT'
            AND close IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            limit,
        )
    ).fetchall()

    # Database returns NEW -> OLD.
    #
    # Indicators require OLD -> NEW.

    rows = list(
        reversed(rows)
    )

    return rows


# ============================================================
# EMA
# ============================================================

def ema(values, period=20):

    if values is None:
        return None

    values = [
        float(x)
        for x in values
        if x is not None
    ]

    if len(values) < period:
        return None

    alpha = (
        2.0
        / (period + 1.0)
    )

    result = (
        sum(values[:period])
        / period
    )

    for value in values[period:]:

        result = (
            (value - result)
            * alpha
            + result
        )

    return result


def ema_series(
    values,
    period
):

    if len(values) < period:
        return []

    multiplier = (
        2.0
        / (period + 1.0)
    )

    result = mean(
        values[:period]
    )

    series = [
        result
    ]

    for price in values[period:]:

        result = (
            (price - result)
            * multiplier
            + result
        )

        series.append(
            result
        )

    return series


# ============================================================
# RSI
# ============================================================

def rsi(
    values,
    period=14
):

    if values is None:
        return None

    values = [
        float(x)
        for x in values
        if x is not None
    ]

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(values)
    ):

        delta = (
            values[i]
            - values[i - 1]
        )

        if delta > 0:

            gains.append(delta)
            losses.append(0.0)

        else:

            gains.append(0.0)
            losses.append(
                abs(delta)
            )

    if len(gains) < period:
        return None

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains)
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

    rs = (
        avg_gain
        / avg_loss
    )

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

def macd(values):

    if len(values) < 35:

        return (
            None,
            None,
            None
        )

    ema12 = ema_series(
        values,
        12
    )

    ema26 = ema_series(
        values,
        26
    )

    if not ema12 or not ema26:

        return (
            None,
            None,
            None
        )

    offset = 26 - 12

    macd_values = []

    for i in range(
        len(ema26)
    ):

        idx = (
            i
            + offset
        )

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
            None
        )

    signal_series = ema_series(
        macd_values,
        9
    )

    if not signal_series:

        return (
            None,
            None,
            None
        )

    macd_value = (
        macd_values[-1]
    )

    signal_value = (
        signal_series[-1]
    )

    histogram = (
        macd_value
        - signal_value
    )

    return (
        macd_value,
        signal_value,
        histogram
    )


# ============================================================
# BOLLINGER
# ============================================================

def bollinger(
    values,
    period=20,
    deviations=2.0
):

    if len(values) < period:

        return (
            None,
            None,
            None,
            None
        )

    window = values[
        -period:
    ]

    middle = mean(
        window
    )

    deviation = stdev(
        window
    )

    if middle is None:

        return (
            None,
            None,
            None,
            None
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
            upper
            - lower
        ) / middle

    else:

        width = 0.0

    return (
        middle,
        upper,
        lower,
        width
    )


# ============================================================
# VOLUME
# ============================================================

def volume_metrics(
    volumes,
    period=20
):

    if len(volumes) < period:

        return (
            None,
            None
        )

    sma = mean(
        volumes[-period:]
    )

    current = volumes[-1]

    if (
        sma is None
        or sma == 0
    ):

        return (
            sma,
            None
        )

    ratio = (
        current
        / sma
    )

    return (
        sma,
        ratio
    )


# ============================================================
# VOLATILITY
# ============================================================

def volatility(
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
        len(closes)
        - period
    )

    for i in range(
        start,
        len(closes)
    ):

        previous = (
            closes[i - 1]
        )

        current = (
            closes[i]
        )

        if previous == 0:
            continue

        returns.append(
            (
                (
                    current
                    - previous
                )
                / previous
            )
            * 100.0
        )

    if len(returns) < 2:

        return None

    return stdev(
        returns
    )


# ============================================================
# SNAPSHOT TECHNICAL SCORE
# ============================================================

def technical_score(
    close,
    ema20_value,
    ema50_value,
    rsi_value,
    macd_value,
    macd_signal_value,
    bb_middle_value,
    volume_ratio_value
):
    """
    Snapshot score.

    ATR / ADX are intentionally excluded because real
    high/low OHLC does not exist in the snapshot source.

    Maximum = +100
    Minimum = -100

    Components:

        EMA trend      = +/-30
        RSI            = +/-20
        MACD           = +/-25
        Bollinger      = +/-15
        Volume         = +/-10

    Volume is only a confirmation signal and cannot create
    direction by itself.
    """

    score = 0.0

    # --------------------------------------------------------
    # EMA TREND
    # --------------------------------------------------------

    if (
        ema20_value is not None
        and ema50_value is not None
    ):

        if (
            close > ema20_value
            and ema20_value
            > ema50_value
        ):

            score += 30.0

        elif (
            close < ema20_value
            and ema20_value
            < ema50_value
        ):

            score -= 30.0

    # --------------------------------------------------------
    # RSI
    #
    # RSI is directional, but extreme RSI should not keep
    # increasing the score indefinitely.
    #
    # 50-60  = mild bullish
    # 60-70  = bullish
    # >70    = strong momentum, capped
    #
    # 40-50  = mild bearish
    # 30-40  = bearish
    # <30    = strong downside momentum, capped
    # --------------------------------------------------------

    if rsi_value is not None:

        if rsi_value >= 70:

            score += 20.0

        elif rsi_value >= 60:

            score += 15.0

        elif rsi_value >= 55:

            score += 8.0

        elif rsi_value <= 30:

            score -= 20.0

        elif rsi_value <= 40:

            score -= 15.0

        elif rsi_value <= 45:

            score -= 8.0

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if (
        macd_value is not None
        and macd_signal_value is not None
    ):

        if macd_value > macd_signal_value:

            score += 25.0

        elif macd_value < macd_signal_value:

            score -= 25.0

    # --------------------------------------------------------
    # BOLLINGER
    # --------------------------------------------------------

    if (
        bb_middle_value is not None
    ):

        if close > bb_middle_value:

            score += 15.0

        elif close < bb_middle_value:

            score -= 15.0

    # --------------------------------------------------------
    # VOLUME CONFIRMATION
    # --------------------------------------------------------

    if (
        volume_ratio_value is not None
        and volume_ratio_value >= 1.2
    ):

        if score > 0:

            score += 10.0

        elif score < 0:

            score -= 10.0

    # --------------------------------------------------------
    # CLAMP
    # --------------------------------------------------------

    score = max(
        -100.0,
        min(
            100.0,
            score
        )
    )

    return score


# ============================================================
# ANALYSIS
# ============================================================

def calculate_analysis(rows):

    closes = []

    volumes = []

    for row in rows:

        close = safe_float(
            row["close"]
        )

        volume = safe_float(
            row["volume"]
        )

        if close is None:
            continue

        closes.append(
            close
        )

        volumes.append(
            volume
            if volume is not None
            else 0.0
        )

    if len(closes) < MIN_HISTORY:

        return None

    # --------------------------------------------------------
    # IMPORTANT
    #
    # rows are guaranteed OLD -> NEW by
    # get_snapshot_history().
    # --------------------------------------------------------

    latest_row = rows[-1]

    close = closes[-1]

    ema20_value = ema(
        closes,
        20
    )

    ema50_value = ema(
        closes,
        50
    )

    rsi_value = rsi(
        closes,
        14
    )

    (
        macd_value,
        macd_signal_value,
        macd_hist_value
    ) = macd(
        closes
    )

    (
        bb_middle_value,
        bb_upper_value,
        bb_lower_value,
        bb_width_value
    ) = bollinger(
        closes,
        20,
        2.0
    )

    (
        volume_sma20_value,
        volume_ratio_value
    ) = volume_metrics(
        volumes,
        20
    )

    volatility_value = volatility(
        closes,
        20
    )

    score = technical_score(
        close,
        ema20_value,
        ema50_value,
        rsi_value,
        macd_value,
        macd_signal_value,
        bb_middle_value,
        volume_ratio_value
    )

    return {

        "timestamp":
            latest_row["timestamp"],

        "source_timestamp":
            latest_row[
                "source_timestamp"
            ],

        "close":
            close,

        "volume":
            volumes[-1],

        "ema20":
            ema20_value,

        "ema50":
            ema50_value,

        "rsi14":
            rsi_value,

        "macd":
            macd_value,

        "macd_signal":
            macd_signal_value,

        "macd_hist":
            macd_hist_value,

        # ----------------------------------------------------
        # Snapshot data has no genuine OHLC.
        # Therefore these remain NULL.
        # ----------------------------------------------------

        "atr14":
            None,

        "adx14":
            None,

        "bb_middle":
            bb_middle_value,

        "bb_upper":
            bb_upper_value,

        "bb_lower":
            bb_lower_value,

        "bb_width":
            bb_width_value,

        "volume_sma20":
            volume_sma20_value,

        "volume_ratio":
            volume_ratio_value,

        "volatility":
            volatility_value,

        "technical_score":
            score,

        "price_change_1h":
            safe_float(
                latest_row[
                    "price_change_1h"
                ]
            ),

        "price_change_24h":
            safe_float(
                latest_row[
                    "price_change_24h"
                ]
            ),

        "market_cap":
            safe_float(
                latest_row[
                    "market_cap"
                ]
            ),

        "volume_24h":
            safe_float(
                latest_row[
                    "volume_24h"
                ]
            ),

        "source_latency_ms":
            safe_float(
                latest_row[
                    "source_latency_ms"
                ]
            ),
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def analysis_exists(
    conn,
    symbol,
    analysis
):

    source_timestamp = (
        analysis[
            "source_timestamp"
        ]
    )

    # --------------------------------------------------------
    # Normal case:
    # source_timestamp exists.
    # --------------------------------------------------------

    if source_timestamp is not None:

        row = conn.execute(
            """
            SELECT id
            FROM market_data
            WHERE
                symbol = ?
                AND timeframe = ?
                AND source = ?
                AND source_timestamp = ?
            LIMIT 1
            """,
            (
                symbol,
                TIMEFRAME,
                SOURCE,
                source_timestamp,
            )
        ).fetchone()

        return row is not None

    # --------------------------------------------------------
    # NULL source_timestamp fallback.
    #
    # SQLite:
    #
    # NULL = NULL
    #
    # is NOT true.
    #
    # Therefore normal equality cannot be used here.
    # --------------------------------------------------------

    row = conn.execute(
        """
        SELECT id
        FROM market_data
        WHERE
            symbol = ?
            AND timeframe = ?
            AND source = ?
            AND source_timestamp IS NULL
            AND timestamp = ?
        LIMIT 1
        """,
        (
            symbol,
            TIMEFRAME,
            SOURCE,
            analysis["timestamp"],
        )
    ).fetchone()

    return row is not None


# ============================================================
# SAVE ANALYSIS
# ============================================================

def save_analysis(
    conn,
    symbol,
    analysis
):

    if analysis_exists(
        conn,
        symbol,
        analysis
    ):

        return False

    conn.execute(
        """
        INSERT INTO market_data (

            timestamp,
            symbol,
            timeframe,

            open,
            high,
            low,
            close,
            volume,

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

            technical_score,

            source,
            source_timestamp,

            price_change_1h,
            price_change_24h,
            market_cap,
            volume_24h,
            source_latency_ms,

            engine_version
        )

        VALUES (

            ?, ?, ?,

            ?, ?, ?, ?, ?,

            ?, ?,

            ?,

            ?, ?, ?,

            ?, ?,

            ?, ?, ?, ?,

            ?, ?,

            ?,

            ?,

            ?, ?,

            ?, ?, ?, ?, ?,

            ?
        )
        """,
        (

            analysis["timestamp"],
            symbol,
            TIMEFRAME,

            # ------------------------------------------------
            # No synthetic OHLC.
            #
            # Snapshot close is stored only in close.
            # ------------------------------------------------

            None,
            None,
            None,
            analysis["close"],
            analysis["volume"],

            analysis["ema20"],
            analysis["ema50"],

            analysis["rsi14"],

            analysis["macd"],
            analysis["macd_signal"],
            analysis["macd_hist"],

            None,
            None,

            analysis["bb_middle"],
            analysis["bb_upper"],
            analysis["bb_lower"],
            analysis["bb_width"],

            analysis["volume_sma20"],
            analysis["volume_ratio"],

            analysis["volatility"],

            analysis["technical_score"],

            SOURCE,
            analysis[
                "source_timestamp"
            ],

            analysis["price_change_1h"],
            analysis["price_change_24h"],
            analysis["market_cap"],
            analysis["volume_24h"],
            analysis["source_latency_ms"],

            ENGINE_VERSION,
        )
    )

    return True


# ============================================================
# DISPLAY
# ============================================================

def format_value(
    value,
    digits=2
):

    if value is None:
        return "N/A"

    try:

        return f"{value:.{digits}f}"

    except Exception:

        return "N/A"


def print_insufficient(
    symbol,
    count
):

    print(
        f"{symbol:<6}"
        f" | INSUFFICIENT DATA"
        f" | POINTS={count}"
        f" | REQUIRED={MIN_HISTORY}"
    )


# ============================================================
# RECENT ANALYSIS
# ============================================================

def show_recent_analysis(
    conn
):

    rows = conn.execute(
        """
        SELECT
            symbol,
            timestamp,
            close,
            technical_score,
            rsi14,
            atr14,
            adx14,
            volatility,
            source
        FROM market_data
        WHERE
            source = ?
        ORDER BY id DESC
        LIMIT 15
        """,
        (
            SOURCE,
        )
    ).fetchall()

    print()

    print(
        "RECENT MARKET ANALYSIS"
    )

    print(
        "-" * 90
    )

    if not rows:

        print(
            "NO ANALYSIS ROWS"
        )

        return

    for row in rows:

        print(
            f"{row['symbol']:<5} | "
            f"{row['timestamp']} | "
            f"PRICE {row['close']:,.8f} | "
            f"SCORE {format_value(row['technical_score']):>7} | "
            f"RSI {format_value(row['rsi14']):>7} | "
            f"ATR {format_value(row['atr14']):>7} | "
            f"ADX {format_value(row['adx14']):>7}"
        )


# ============================================================
# COUNTERS
# ============================================================

def count_snapshot_rows(
    conn
):

    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_data
        WHERE
            source = ?
            AND timeframe = 'SNAPSHOT'
        """,
        (
            SNAPSHOT_SOURCE,
        )
    ).fetchone()

    return int(
        row[0]
    )


def count_analysis_rows(
    conn
):

    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_data
        WHERE
            source = ?
        """,
        (
            SOURCE,
        )
    ).fetchone()

    return int(
        row[0]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    print(
        "=" * 90
    )

    print(
        "             ARUNDA MARKET DATA ENGINE v0.4"
    )

    print(
        "=" * 90
    )

    print(
        "Provider : COINMARKETCAP SNAPSHOTS"
    )

    print(
        f"Database : {DB}"
    )

    print(
        "Binance  : REMOVED"
    )

    print(
        f"History  : LAST {LOOKBACK} SNAPSHOTS"
    )

    print(
        f"Minimum  : {MIN_HISTORY} SNAPSHOTS"
    )

    print(
        "Mode     : SNAPSHOT ANALYSIS"
    )

    print(
        "OHLC     : NOT MANUFACTURED"
    )

    print(
        "ATR/ADX  : DISABLED FOR SNAPSHOT DATA"
    )

    print(
        "Ordering : OLD -> NEW FOR INDICATORS"
    )

    print(
        "=" * 90
    )

    conn = None

    try:

        conn = connect_database()

        print()

        print(
            "Checking market-data schema..."
        )

        ensure_schema(
            conn
        )

        snapshot_count_before = (
            count_snapshot_rows(
                conn
            )
        )

        analysis_count_before = (
            count_analysis_rows(
                conn
            )
        )

        print(
            f"Snapshot rows : "
            f"{snapshot_count_before}"
        )

        print(
            f"Analysis rows : "
            f"{analysis_count_before}"
        )

        print()

        print(
            "Reading latest CMC snapshot history..."
        )

        print(
            "-" * 90
        )

        evaluated = 0

        inserted = 0

        insufficient = 0

        errors = 0

        for symbol in SYMBOLS:

            try:

                rows = get_snapshot_history(
                    conn,
                    symbol,
                    LOOKBACK
                )

                count = len(
                    rows
                )

                if count < MIN_HISTORY:

                    print_insufficient(
                        symbol,
                        count
                    )

                    insufficient += 1

                    continue

                analysis = calculate_analysis(
                    rows
                )

                if analysis is None:

                    print_insufficient(
                        symbol,
                        count
                    )

                    insufficient += 1

                    continue

                evaluated += 1

                was_inserted = save_analysis(
                    conn,
                    symbol,
                    analysis
                )

                if was_inserted:

                    inserted += 1

                    status = "INSERTED"

                else:

                    status = "DUPLICATE"

                print(
                    f"{symbol:<6}"
                    f" | {status:<9}"
                    f" | POINTS={count:<3}"
                    f" | PRICE={analysis['close']:>14,.6f}"
                    f" | SCORE={analysis['technical_score']:>7.2f}"
                    f" | RSI={format_value(analysis['rsi14'])}"
                )

            except Exception as exc:

                errors += 1

                print(
                    f"{symbol:<6}"
                    f" | ERROR | "
                    f"{repr(exc)}"
                )

        conn.commit()

        analysis_count_after = (
            count_analysis_rows(
                conn
            )
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print()

        print(
            "=" * 90
        )

        print(
            "                 MARKET DATA SUMMARY"
        )

        print(
            "=" * 90
        )

        print(
            f"Symbols Evaluated : "
            f"{evaluated}"
        )

        print(
            f"Inserted          : "
            f"{inserted}"
        )

        print(
            f"Insufficient Data : "
            f"{insufficient}"
        )

        print(
            f"Errors            : "
            f"{errors}"
        )

        print(
            f"Analysis Records  : "
            f"{analysis_count_after}"
        )

        print(
            f"Run Time          : "
            f"{elapsed:.2f} sec"
        )

        print(
            f"Engine            : "
            f"{ENGINE_VERSION}"
        )

        print(
            "Provider          : "
            "COINMARKETCAP SNAPSHOT"
        )

        print(
            "Binance           : "
            "DISABLED / REMOVED"
        )

        print(
            "Synthetic OHLC    : "
            "FORBIDDEN"
        )

        print(
            "ATR / ADX         : "
            "NULL / NOT DERIVED"
        )

        print(
            "Time-Series Order : "
            "OLD -> NEW"
        )

        print(
            "=" * 90
        )

        show_recent_analysis(
            conn
        )

        print()

        print(
            "=" * 90
        )

        print(
            "             MARKET DATA ENGINE COMPLETE"
        )

        print(
            "=" * 90
        )

        if (
            errors == 0
            and evaluated > 0
        ):

            print(
                "MARKET DATA STATUS : SUCCESS"
            )

        elif evaluated > 0:

            print(
                "MARKET DATA STATUS : PARTIAL"
            )

        elif insufficient > 0:

            print(
                "MARKET DATA STATUS : INSUFFICIENT HISTORY"
            )

        else:

            print(
                "MARKET DATA STATUS : FAILED"
            )

        print(
            f"SNAPSHOT RECORDS : "
            f"{snapshot_count_before}"
        )

        print(
            f"ANALYSIS BEFORE  : "
            f"{analysis_count_before}"
        )

        print(
            f"ANALYSIS AFTER   : "
            f"{analysis_count_after}"
        )

        print(
            f"ANALYSIS NEW     : "
            f"{inserted}"
        )

        print(
            "=" * 90
        )

        # ----------------------------------------------------
        # Pipeline may continue.
        #
        # Downstream signal engines must independently enforce
        # their own eligibility / confidence contracts.
        # ----------------------------------------------------

        return 0

    except Exception as exc:

        print()

        print(
            "=" * 90
        )

        print(
            "                 MARKET DATA ENGINE ERROR"
        )

        print(
            "=" * 90
        )

        print(
            repr(exc)
        )

        print(
            "=" * 90
        )

        return 1

    finally:

        if conn is not None:

            conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )


