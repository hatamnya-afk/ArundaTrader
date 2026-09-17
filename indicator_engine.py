"""
ARUNDA TRADER — DEV-06
INDICATOR ENGINE v0.1

Purpose
-------
Calculate deterministic technical-analysis indicators from ordered OHLCV
market observations.

Architecture
------------
- Analysis Layer only
- Database independent
- No SQL
- No database writes
- No trading decisions
- No BUY / SELL output
- No look-ahead
- Input order preserved
- CMC_ID / symbol identity preserved

Indicator Families
------------------
Trend:
    SMA
    EMA
    WMA
    MACD

Momentum:
    RSI
    Stochastic

Volatility:
    ATR
    Bollinger Bands

Trend Strength:
    ADX
    +DI
    -DI

Price / Volume:
    VWAP
    Volume Change Ratio

Cloud:
    Ichimoku

Design Principles
-----------------
1. Every value at index i uses data available at or before i.
2. Warm-up periods never use future observations.
3. Insufficient history returns None rather than fabricated values.
4. Non-finite numeric values are rejected.
5. Input order is preserved.
6. Identity metadata is preserved.
7. Indicator calculations are deterministic.
8. Indicators describe market state; they do not make decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple
import math


ENGINE_NAME = "INDICATOR_ENGINE_v0.1"


# ============================================================================
# DEFAULT PERIODS
# ============================================================================

DEFAULT_SMA_PERIOD = 20
DEFAULT_EMA_PERIOD = 20
DEFAULT_WMA_PERIOD = 20

DEFAULT_RSI_PERIOD = 14

DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9

DEFAULT_ATR_PERIOD = 14

DEFAULT_BB_PERIOD = 20
DEFAULT_BB_STDDEV = 2.0

DEFAULT_STOCH_PERIOD = 14
DEFAULT_STOCH_SMOOTH_K = 3
DEFAULT_STOCH_SMOOTH_D = 3

DEFAULT_ADX_PERIOD = 14

DEFAULT_ICHIMOKU_TENKAN = 9
DEFAULT_ICHIMOKU_KIJUN = 26
DEFAULT_ICHIMOKU_SENKOU_B = 52
DEFAULT_ICHIMOKU_DISPLACEMENT = 26


# ============================================================================
# NUMERIC SAFETY
# ============================================================================

def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _float(value: Any) -> float:

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(
            f"Non-finite numeric value: {value}"
        )

    return value


def _safe_div(
    numerator: float,
    denominator: float,
) -> Optional[float]:

    if not _finite(numerator):
        return None

    if not _finite(denominator):
        return None

    if denominator == 0:
        return None

    return numerator / denominator


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass(frozen=True)
class IndicatorBar:

    timestamp: Any

    high: float
    low: float
    close: float

    open: Optional[float] = None
    volume: Optional[float] = None

    cmc_id: Optional[int] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class IndicatorRecord:

    index: int
    timestamp: Any

    cmc_id: Optional[int]
    symbol: Optional[str]

    close: float

    sma: Optional[float]
    ema: Optional[float]
    wma: Optional[float]

    rsi: Optional[float]

    macd: Optional[float]
    macd_signal: Optional[float]
    macd_histogram: Optional[float]

    atr: Optional[float]

    bb_middle: Optional[float]
    bb_upper: Optional[float]
    bb_lower: Optional[float]
    bb_width: Optional[float]
    bb_position: Optional[float]

    stochastic_k: Optional[float]
    stochastic_d: Optional[float]

    adx: Optional[float]
    plus_di: Optional[float]
    minus_di: Optional[float]

    vwap: Optional[float]
    volume_change_ratio: Optional[float]

    ichimoku_tenkan: Optional[float]
    ichimoku_kijun: Optional[float]
    ichimoku_senkou_a: Optional[float]
    ichimoku_senkou_b: Optional[float]
    ichimoku_chikou: Optional[float]


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_bar(
    bar: Any,
) -> IndicatorBar:

    if isinstance(bar, IndicatorBar):

        result = bar

    elif isinstance(bar, dict):

        required = (
            "timestamp",
            "high",
            "low",
            "close",
        )

        for field in required:

            if field not in bar:

                raise ValueError(
                    f"Missing required bar field: {field}"
                )

        result = IndicatorBar(

            timestamp=bar["timestamp"],

            high=_float(
                bar["high"]
            ),

            low=_float(
                bar["low"]
            ),

            close=_float(
                bar["close"]
            ),

            open=(
                _float(bar["open"])
                if bar.get("open") is not None
                else None
            ),

            volume=(
                _float(bar["volume"])
                if bar.get("volume") is not None
                else None
            ),

            cmc_id=bar.get("cmc_id"),

            symbol=bar.get("symbol"),
        )

    else:

        raise TypeError(
            f"Unsupported bar type: {type(bar).__name__}"
        )

    if result.high < result.low:

        raise ValueError(
            f"Invalid OHLC: high < low at {result.timestamp}"
        )

    if not _finite(result.high):

        raise ValueError(
            "Invalid high."
        )

    if not _finite(result.low):

        raise ValueError(
            "Invalid low."
        )

    if not _finite(result.close):

        raise ValueError(
            "Invalid close."
        )

    if (
        result.open is not None
        and not _finite(result.open)
    ):

        raise ValueError(
            "Invalid open."
        )

    if result.volume is not None:

        if not _finite(result.volume):

            raise ValueError(
                "Invalid volume."
            )

        if result.volume < 0:

            raise ValueError(
                "Volume cannot be negative."
            )

    return result


def validate_bars(
    bars: Sequence[Any],
) -> List[IndicatorBar]:

    if bars is None:

        raise ValueError(
            "bars cannot be None"
        )

    result = [
        validate_bar(bar)
        for bar in bars
    ]

    if len(result) == 0:

        raise ValueError(
            "bars cannot be empty"
        )

    return result


# ============================================================================
# GENERIC SERIES HELPERS
# ============================================================================

def _window(
    values: Sequence[float],
    end_index: int,
    period: int,
) -> Optional[List[float]]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    start = (
        end_index
        - period
        + 1
    )

    if start < 0:

        return None

    values_window = list(
        values[
            start:
            end_index + 1
        ]
    )

    if len(values_window) != period:

        return None

    if not all(
        _finite(v)
        for v in values_window
    ):

        return None

    return values_window


def _mean(
    values: Sequence[float],
) -> float:

    if not values:

        raise ValueError(
            "Cannot calculate mean of empty sequence."
        )

    return sum(values) / len(values)


def _stddev(
    values: Sequence[float],
) -> float:

    if not values:

        raise ValueError(
            "Cannot calculate standard deviation."
        )

    mean = _mean(values)

    variance = sum(
        (
            value - mean
        ) ** 2

        for value in values
    ) / len(values)

    return math.sqrt(
        variance
    )


# ============================================================================
# SMA
# ============================================================================

def calculate_sma(
    closes: Sequence[float],
    period: int = DEFAULT_SMA_PERIOD,
) -> List[Optional[float]]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    result: List[Optional[float]] = []

    for i in range(
        len(closes)
    ):

        window = _window(
            closes,
            i,
            period,
        )

        if window is None:

            result.append(None)

        else:

            result.append(
                _mean(window)
            )

    return result


# ============================================================================
# EMA
# ============================================================================

def calculate_ema(
    closes: Sequence[float],
    period: int = DEFAULT_EMA_PERIOD,
) -> List[Optional[float]]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    result: List[Optional[float]] = [
        None
        for _ in closes
    ]

    if len(closes) < period:

        return result

    seed = _mean(
        closes[:period]
    )

    result[
        period - 1
    ] = seed

    alpha = (
        2.0
        / (period + 1.0)
    )

    previous = seed

    for i in range(
        period,
        len(closes)
    ):

        current = (
            alpha * closes[i]
            + (
                1.0 - alpha
            ) * previous
        )

        result[i] = current

        previous = current

    return result


# ============================================================================
# WMA
# ============================================================================

def calculate_wma(
    closes: Sequence[float],
    period: int = DEFAULT_WMA_PERIOD,
) -> List[Optional[float]]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    result: List[Optional[float]] = [
        None
        for _ in closes
    ]

    denominator = (
        period
        * (period + 1)
    ) / 2.0

    for i in range(
        len(closes)
    ):

        window = _window(
            closes,
            i,
            period,
        )

        if window is None:

            continue

        weighted_sum = sum(
            value * (j + 1)

            for j, value
            in enumerate(window)
        )

        result[i] = (
            weighted_sum
            / denominator
        )

    return result


# ============================================================================
# RSI — WILDER
# ============================================================================

def calculate_rsi(
    closes: Sequence[float],
    period: int = DEFAULT_RSI_PERIOD,
) -> List[Optional[float]]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    result: List[Optional[float]] = [
        None
        for _ in closes
    ]

    if len(closes) <= period:

        return result

    gains = []
    losses = []

    for i in range(
        1,
        period + 1
    ):

        delta = (
            closes[i]
            - closes[i - 1]
        )

        gains.append(
            max(
                delta,
                0.0
            )
        )

        losses.append(
            max(
                -delta,
                0.0
            )
        )

    avg_gain = _mean(gains)
    avg_loss = _mean(losses)

    def rsi_from_avgs(
        gain: float,
        loss: float,
    ) -> float:

        if loss == 0:

            if gain == 0:

                return 50.0

            return 100.0

        rs = gain / loss

        return (
            100.0
            - (
                100.0
                / (1.0 + rs)
            )
        )

    result[period] = (
        rsi_from_avgs(
            avg_gain,
            avg_loss,
        )
    )

    for i in range(
        period + 1,
        len(closes)
    ):

        delta = (
            closes[i]
            - closes[i - 1]
        )

        gain = max(
            delta,
            0.0
        )

        loss = max(
            -delta,
            0.0
        )

        avg_gain = (
            (
                avg_gain
                * (period - 1)
            )
            + gain
        ) / period

        avg_loss = (
            (
                avg_loss
                * (period - 1)
            )
            + loss
        ) / period

        result[i] = (
            rsi_from_avgs(
                avg_gain,
                avg_loss,
            )
        )

    return result


# ============================================================================
# MACD
# ============================================================================

def calculate_macd(
    closes: Sequence[float],
    fast_period: int = DEFAULT_MACD_FAST,
    slow_period: int = DEFAULT_MACD_SLOW,
    signal_period: int = DEFAULT_MACD_SIGNAL,
) -> Tuple[
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
]:

    if fast_period < 1:

        raise ValueError(
            "fast_period must be >= 1"
        )

    if slow_period <= fast_period:

        raise ValueError(
            "slow_period must be greater than fast_period"
        )

    if signal_period < 1:

        raise ValueError(
            "signal_period must be >= 1"
        )

    fast = calculate_ema(
        closes,
        fast_period,
    )

    slow = calculate_ema(
        closes,
        slow_period,
    )

    macd: List[Optional[float]] = []

    for i in range(
        len(closes)
    ):

        if (
            fast[i] is None
            or slow[i] is None
        ):

            macd.append(None)

        else:

            macd.append(
                fast[i]
                - slow[i]
            )

    signal: List[Optional[float]] = [
        None
        for _ in closes
    ]

    valid_macd = [
        value
        for value in macd
        if value is not None
    ]

    if len(valid_macd) >= signal_period:

        signal_values = calculate_ema(
            valid_macd,
            signal_period,
        )

        first_valid_index = (
            len(closes)
            - len(valid_macd)
        )

        for j, value in enumerate(
            signal_values
        ):

            signal[
                first_valid_index + j
            ] = value

    histogram: List[Optional[float]] = []

    for i in range(
        len(closes)
    ):

        if (
            macd[i] is None
            or signal[i] is None
        ):

            histogram.append(None)

        else:

            histogram.append(
                macd[i]
                - signal[i]
            )

    return (
        macd,
        signal,
        histogram,
    )


# ============================================================================
# TRUE RANGE
# ============================================================================

def calculate_true_range(
    bars: Sequence[IndicatorBar],
) -> List[float]:

    if not bars:

        return []

    result = []

    for i, bar in enumerate(
        bars
    ):

        if i == 0:

            tr = (
                bar.high
                - bar.low
            )

        else:

            previous_close = (
                bars[i - 1].close
            )

            tr = max(
                bar.high - bar.low,
                abs(
                    bar.high
                    - previous_close
                ),
                abs(
                    bar.low
                    - previous_close
                ),
            )

        result.append(tr)

    return result


# ============================================================================
# ATR — WILDER
# ============================================================================

def calculate_atr(
    bars: Sequence[IndicatorBar],
    period: int = DEFAULT_ATR_PERIOD,
) -> List[Optional[float]]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    tr = calculate_true_range(
        bars
    )

    result: List[Optional[float]] = [
        None
        for _ in bars
    ]

    if len(tr) < period:

        return result

    atr = _mean(
        tr[:period]
    )

    result[
        period - 1
    ] = atr

    for i in range(
        period,
        len(tr)
    ):

        atr = (
            (
                atr
                * (period - 1)
            )
            + tr[i]
        ) / period

        result[i] = atr

    return result


# ============================================================================
# BOLLINGER BANDS
# ============================================================================

def calculate_bollinger_bands(
    closes: Sequence[float],
    period: int = DEFAULT_BB_PERIOD,
    stddev_multiplier: float = DEFAULT_BB_STDDEV,
) -> Tuple[
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    if stddev_multiplier < 0:

        raise ValueError(
            "stddev_multiplier cannot be negative"
        )

    middle = []
    upper = []
    lower = []
    width = []
    position = []

    for i in range(
        len(closes)
    ):

        window = _window(
            closes,
            i,
            period,
        )

        if window is None:

            middle.append(None)
            upper.append(None)
            lower.append(None)
            width.append(None)
            position.append(None)

            continue

        mean = _mean(window)
        sd = _stddev(window)

        band_upper = (
            mean
            + stddev_multiplier * sd
        )

        band_lower = (
            mean
            - stddev_multiplier * sd
        )

        middle.append(mean)
        upper.append(band_upper)
        lower.append(band_lower)

        if mean != 0:

            width.append(
                (
                    band_upper
                    - band_lower
                ) / mean
            )

        else:

            width.append(None)

        denominator = (
            band_upper
            - band_lower
        )

        if denominator == 0:

            position.append(0.5)

        else:

            position.append(
                (
                    closes[i]
                    - band_lower
                ) / denominator
            )

    return (
        middle,
        upper,
        lower,
        width,
        position,
    )


# ============================================================================
# STOCHASTIC
# ============================================================================

def calculate_stochastic(
    bars: Sequence[IndicatorBar],
    period: int = DEFAULT_STOCH_PERIOD,
    smooth_k: int = DEFAULT_STOCH_SMOOTH_K,
    smooth_d: int = DEFAULT_STOCH_SMOOTH_D,
) -> Tuple[
    List[Optional[float]],
    List[Optional[float]],
]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    if smooth_k < 1:

        raise ValueError(
            "smooth_k must be >= 1"
        )

    if smooth_d < 1:

        raise ValueError(
            "smooth_d must be >= 1"
        )

    raw_k: List[Optional[float]] = [
        None
        for _ in bars
    ]

    for i in range(
        len(bars)
    ):

        start = (
            i
            - period
            + 1
        )

        if start < 0:

            continue

        window = bars[
            start:
            i + 1
        ]

        highest = max(
            bar.high
            for bar in window
        )

        lowest = min(
            bar.low
            for bar in window
        )

        denominator = (
            highest
            - lowest
        )

        if denominator == 0:

            raw_k[i] = 50.0

        else:

            raw_k[i] = (
                (
                    bars[i].close
                    - lowest
                )
                / denominator
            ) * 100.0

    k: List[Optional[float]] = [
        None
        for _ in bars
    ]

    for i in range(
        len(bars)
    ):

        start = (
            i
            - smooth_k
            + 1
        )

        if start < 0:

            continue

        values = [
            raw_k[j]
            for j in range(
                start,
                i + 1
            )
        ]

        if any(
            value is None
            for value in values
        ):

            continue

        k[i] = _mean(
            values
        )

    d: List[Optional[float]] = [
        None
        for _ in bars
    ]

    for i in range(
        len(bars)
    ):

        start = (
            i
            - smooth_d
            + 1
        )

        if start < 0:

            continue

        values = [
            k[j]
            for j in range(
                start,
                i + 1
            )
        ]

        if any(
            value is None
            for value in values
        ):

            continue

        d[i] = _mean(
            values
        )

    return (
        k,
        d,
    )


# ============================================================================
# ADX / DI — WILDER
# ============================================================================

def calculate_adx(
    bars: Sequence[IndicatorBar],
    period: int = DEFAULT_ADX_PERIOD,
) -> Tuple[
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
]:

    if period < 1:

        raise ValueError(
            "period must be >= 1"
        )

    n = len(bars)

    adx: List[Optional[float]] = [
        None
        for _ in range(n)
    ]

    plus_di: List[Optional[float]] = [
        None
        for _ in range(n)
    ]

    minus_di: List[Optional[float]] = [
        None
        for _ in range(n)
    ]

    # ------------------------------------------------------------------------
    # WARM-UP
    # ------------------------------------------------------------------------

    if n < period:

        return (
            adx,
            plus_di,
            minus_di,
        )

    # ------------------------------------------------------------------------
    # TRUE RANGE
    # ------------------------------------------------------------------------

    tr = calculate_true_range(
        bars
    )

    # ------------------------------------------------------------------------
    # DIRECTIONAL MOVEMENT
    # ------------------------------------------------------------------------

    plus_dm = [
        0.0
        for _ in range(n)
    ]

    minus_dm = [
        0.0
        for _ in range(n)
    ]

    for i in range(
        1,
        n
    ):

        up_move = (
            bars[i].high
            - bars[i - 1].high
        )

        down_move = (
            bars[i - 1].low
            - bars[i].low
        )

        if (
            up_move > down_move
            and up_move > 0.0
        ):

            plus_dm[i] = up_move

        elif (
            down_move > up_move
            and down_move > 0.0
        ):

            minus_dm[i] = down_move

    # ------------------------------------------------------------------------
    # INITIAL WILDER AVERAGES
    # ------------------------------------------------------------------------

    atr = _mean(
        tr[:period]
    )

    smoothed_plus_dm = _mean(
        plus_dm[:period]
    )

    smoothed_minus_dm = _mean(
        minus_dm[:period]
    )

    first_index = (
        period - 1
    )

    # ------------------------------------------------------------------------
    # FIRST DI
    # ------------------------------------------------------------------------

    if atr > 0.0:

        plus_di[first_index] = (
            100.0
            * smoothed_plus_dm
            / atr
        )

        minus_di[first_index] = (
            100.0
            * smoothed_minus_dm
            / atr
        )

    else:

        plus_di[first_index] = 0.0
        minus_di[first_index] = 0.0

    # ------------------------------------------------------------------------
    # WILDER SMOOTHING
    # ------------------------------------------------------------------------

    for i in range(
        period,
        n
    ):

        atr = (
            (
                atr
                * (period - 1)
            )
            + tr[i]
        ) / period

        smoothed_plus_dm = (
            (
                smoothed_plus_dm
                * (period - 1)
            )
            + plus_dm[i]
        ) / period

        smoothed_minus_dm = (
            (
                smoothed_minus_dm
                * (period - 1)
            )
            + minus_dm[i]
        ) / period

        if atr <= 0.0:

            plus_di[i] = 0.0
            minus_di[i] = 0.0

        else:

            plus_di[i] = (
                100.0
                * smoothed_plus_dm
                / atr
            )

            minus_di[i] = (
                100.0
                * smoothed_minus_dm
                / atr
            )

    # ------------------------------------------------------------------------
    # DX
    # ------------------------------------------------------------------------

    dx: List[Optional[float]] = [
        None
        for _ in range(n)
    ]

    for i in range(n):

        if (
            plus_di[i] is None
            or minus_di[i] is None
        ):

            continue

        denominator = (
            plus_di[i]
            + minus_di[i]
        )

        if denominator == 0.0:

            dx[i] = 0.0

        else:

            dx[i] = (
                100.0
                * abs(
                    plus_di[i]
                    - minus_di[i]
                )
                / denominator
            )

    # ------------------------------------------------------------------------
    # FIRST ADX
    #
    # First DX is available at period - 1.
    #
    # We need `period` DX observations.
    #
    # First ADX:
    #
    #     (period - 1) + (period - 1)
    #     = 2 * period - 2
    # ------------------------------------------------------------------------

    first_adx_index = (
        2 * period
        - 2
    )

    if n <= first_adx_index:

        return (
            adx,
            plus_di,
            minus_di,
        )

    initial_dx_values = [
        dx[i]
        for i in range(
            first_index,
            first_adx_index + 1
        )
        if dx[i] is not None
    ]

    if len(initial_dx_values) != period:

        return (
            adx,
            plus_di,
            minus_di,
        )

    initial_adx = _mean(
        initial_dx_values
    )

    adx[
        first_adx_index
    ] = initial_adx

    previous_adx = initial_adx

    # ------------------------------------------------------------------------
    # ADX WILDER SMOOTHING
    # ------------------------------------------------------------------------

    for i in range(
        first_adx_index + 1,
        n
    ):

        if dx[i] is None:

            continue

        previous_adx = (
            (
                previous_adx
                * (period - 1)
            )
            + dx[i]
        ) / period

        adx[i] = previous_adx

    return (
        adx,
        plus_di,
        minus_di,
    )


# ============================================================================
# VWAP
# ============================================================================

def calculate_vwap(
    bars: Sequence[IndicatorBar],
) -> List[Optional[float]]:

    result: List[Optional[float]] = []

    cumulative_pv = 0.0
    cumulative_volume = 0.0

    for bar in bars:

        if bar.volume is None:

            result.append(None)

            continue

        typical_price = (
            bar.high
            + bar.low
            + bar.close
        ) / 3.0

        cumulative_pv += (
            typical_price
            * bar.volume
        )

        cumulative_volume += (
            bar.volume
        )

        if cumulative_volume == 0:

            result.append(None)

        else:

            result.append(
                cumulative_pv
                / cumulative_volume
            )

    return result


# ============================================================================
# VOLUME CHANGE RATIO
# ============================================================================

def calculate_volume_change_ratio(
    bars: Sequence[IndicatorBar],
) -> List[Optional[float]]:

    result: List[Optional[float]] = [
        None
        for _ in bars
    ]

    for i in range(
        1,
        len(bars)
    ):

        current = bars[i].volume
        previous = bars[i - 1].volume

        if (
            current is None
            or previous is None
        ):

            continue

        if previous == 0:

            continue

        result[i] = (
            current
            / previous
        )

    return result


# ============================================================================
# ICHIMOKU
# ============================================================================

def calculate_ichimoku(
    bars: Sequence[IndicatorBar],
    tenkan_period: int = DEFAULT_ICHIMOKU_TENKAN,
    kijun_period: int = DEFAULT_ICHIMOKU_KIJUN,
    senkou_b_period: int = DEFAULT_ICHIMOKU_SENKOU_B,
    displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> Tuple[
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
    List[Optional[float]],
]:

    if tenkan_period < 1:

        raise ValueError(
            "tenkan_period must be >= 1"
        )

    if kijun_period < 1:

        raise ValueError(
            "kijun_period must be >= 1"
        )

    if senkou_b_period < 1:

        raise ValueError(
            "senkou_b_period must be >= 1"
        )

    if displacement < 0:

        raise ValueError(
            "displacement cannot be negative"
        )

    n = len(bars)

    tenkan: List[Optional[float]] = [
        None
        for _ in bars
    ]

    kijun: List[Optional[float]] = [
        None
        for _ in bars
    ]

    senkou_a: List[Optional[float]] = [
        None
        for _ in bars
    ]

    senkou_b: List[Optional[float]] = [
        None
        for _ in bars
    ]

    chikou: List[Optional[float]] = [
        None
        for _ in bars
    ]

    for i in range(n):

        # --------------------------------------------------------------------
        # Tenkan
        # --------------------------------------------------------------------

        if i + 1 >= tenkan_period:

            window = bars[
                i - tenkan_period + 1:
                i + 1
            ]

            highest = max(
                bar.high
                for bar in window
            )

            lowest = min(
                bar.low
                for bar in window
            )

            tenkan[i] = (
                highest
                + lowest
            ) / 2.0

        # --------------------------------------------------------------------
        # Kijun
        # --------------------------------------------------------------------

        if i + 1 >= kijun_period:

            window = bars[
                i - kijun_period + 1:
                i + 1
            ]

            highest = max(
                bar.high
                for bar in window
            )

            lowest = min(
                bar.low
                for bar in window
            )

            kijun[i] = (
                highest
                + lowest
            ) / 2.0

        # --------------------------------------------------------------------
        # Senkou B
        # --------------------------------------------------------------------

        if i + 1 >= senkou_b_period:

            window = bars[
                i - senkou_b_period + 1:
                i + 1
            ]

            highest = max(
                bar.high
                for bar in window
            )

            lowest = min(
                bar.low
                for bar in window
            )

            senkou_b[i] = (
                highest
                + lowest
            ) / 2.0

        # --------------------------------------------------------------------
        # Senkou A
        #
        # IMPORTANT:
        # Kept at calculation index.
        # Never shifted backward.
        # --------------------------------------------------------------------

        if (
            tenkan[i] is not None
            and kijun[i] is not None
        ):

            senkou_a[i] = (
                tenkan[i]
                + kijun[i]
            ) / 2.0

    # ------------------------------------------------------------------------
    # Chikou
    #
    # This is intentionally calculated only from historical data.
    # ------------------------------------------------------------------------

    for i in range(n):

        source_index = (
            i
            - displacement
        )

        if source_index >= 0:

            chikou[i] = (
                bars[
                    source_index
                ].close
            )

    return (
        tenkan,
        kijun,
        senkou_a,
        senkou_b,
        chikou,
    )


# ============================================================================
# INDICATOR RECORD GENERATION
# ============================================================================

def calculate_indicator_records(
    bars: Sequence[Any],
    sma_period: int = DEFAULT_SMA_PERIOD,
    ema_period: int = DEFAULT_EMA_PERIOD,
    wma_period: int = DEFAULT_WMA_PERIOD,
    rsi_period: int = DEFAULT_RSI_PERIOD,
    macd_fast: int = DEFAULT_MACD_FAST,
    macd_slow: int = DEFAULT_MACD_SLOW,
    macd_signal: int = DEFAULT_MACD_SIGNAL,
    atr_period: int = DEFAULT_ATR_PERIOD,
    bb_period: int = DEFAULT_BB_PERIOD,
    bb_stddev: float = DEFAULT_BB_STDDEV,
    stochastic_period: int = DEFAULT_STOCH_PERIOD,
    stochastic_smooth_k: int = DEFAULT_STOCH_SMOOTH_K,
    stochastic_smooth_d: int = DEFAULT_STOCH_SMOOTH_D,
    adx_period: int = DEFAULT_ADX_PERIOD,
    ichimoku_tenkan: int = DEFAULT_ICHIMOKU_TENKAN,
    ichimoku_kijun: int = DEFAULT_ICHIMOKU_KIJUN,
    ichimoku_senkou_b: int = DEFAULT_ICHIMOKU_SENKOU_B,
    ichimoku_displacement: int = DEFAULT_ICHIMOKU_DISPLACEMENT,
) -> List[IndicatorRecord]:

    validated = validate_bars(
        bars
    )

    closes = [
        bar.close
        for bar in validated
    ]

    sma = calculate_sma(
        closes,
        sma_period,
    )

    ema = calculate_ema(
        closes,
        ema_period,
    )

    wma = calculate_wma(
        closes,
        wma_period,
    )

    rsi = calculate_rsi(
        closes,
        rsi_period,
    )

    (
        macd,
        macd_signal_values,
        macd_histogram,
    ) = calculate_macd(
        closes,
        macd_fast,
        macd_slow,
        macd_signal,
    )

    atr = calculate_atr(
        validated,
        atr_period,
    )

    (
        bb_middle,
        bb_upper,
        bb_lower,
        bb_width,
        bb_position,
    ) = calculate_bollinger_bands(
        closes,
        bb_period,
        bb_stddev,
    )

    (
        stochastic_k,
        stochastic_d,
    ) = calculate_stochastic(
        validated,
        stochastic_period,
        stochastic_smooth_k,
        stochastic_smooth_d,
    )

    (
        adx,
        plus_di,
        minus_di,
    ) = calculate_adx(
        validated,
        adx_period,
    )

    vwap = calculate_vwap(
        validated
    )

    volume_change_ratio = (
        calculate_volume_change_ratio(
            validated
        )
    )

    (
        ichimoku_tenkan_values,
        ichimoku_kijun_values,
        ichimoku_senkou_a,
        ichimoku_senkou_b,
        ichimoku_chikou,
    ) = calculate_ichimoku(
        validated,
        ichimoku_tenkan,
        ichimoku_kijun,
        ichimoku_senkou_b,
        ichimoku_displacement,
    )

    records: List[IndicatorRecord] = []

    for i, bar in enumerate(
        validated
    ):

        records.append(
            IndicatorRecord(

                index=i,

                timestamp=bar.timestamp,

                cmc_id=bar.cmc_id,

                symbol=bar.symbol,

                close=bar.close,

                sma=sma[i],

                ema=ema[i],

                wma=wma[i],

                rsi=rsi[i],

                macd=macd[i],

                macd_signal=(
                    macd_signal_values[i]
                ),

                macd_histogram=(
                    macd_histogram[i]
                ),

                atr=atr[i],

                bb_middle=bb_middle[i],

                bb_upper=bb_upper[i],

                bb_lower=bb_lower[i],

                bb_width=bb_width[i],

                bb_position=bb_position[i],

                stochastic_k=(
                    stochastic_k[i]
                ),

                stochastic_d=(
                    stochastic_d[i]
                ),

                adx=adx[i],

                plus_di=plus_di[i],

                minus_di=minus_di[i],

                vwap=vwap[i],

                volume_change_ratio=(
                    volume_change_ratio[i]
                ),

                ichimoku_tenkan=(
                    ichimoku_tenkan_values[i]
                ),

                ichimoku_kijun=(
                    ichimoku_kijun_values[i]
                ),

                ichimoku_senkou_a=(
                    ichimoku_senkou_a[i]
                ),

                ichimoku_senkou_b=(
                    ichimoku_senkou_b[i]
                ),

                ichimoku_chikou=(
                    ichimoku_chikou[i]
                ),
            )
        )

    return records


# ============================================================================
# OUTPUT VALIDATION
# ============================================================================

def validate_indicator_record(
    record: IndicatorRecord,
) -> bool:

    if not isinstance(
        record,
        IndicatorRecord,
    ):

        raise TypeError(
            "Expected IndicatorRecord."
        )

    if record.index < 0:

        raise ValueError(
            "Indicator index cannot be negative."
        )

    if not _finite(
        record.close
    ):

        raise ValueError(
            "Indicator close must be finite."
        )

    numeric_fields = (
        "sma",
        "ema",
        "wma",
        "rsi",
        "macd",
        "macd_signal",
        "macd_histogram",
        "atr",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "bb_position",
        "stochastic_k",
        "stochastic_d",
        "adx",
        "plus_di",
        "minus_di",
        "vwap",
        "volume_change_ratio",
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_senkou_a",
        "ichimoku_senkou_b",
        "ichimoku_chikou",
    )

    for field in numeric_fields:

        value = getattr(
            record,
            field,
        )

        if (
            value is not None
            and not _finite(value)
        ):

            raise ValueError(
                f"Non-finite indicator field: {field}"
            )

    if record.rsi is not None:

        if not (
            0
            <= record.rsi
            <= 100
        ):

            raise ValueError(
                "RSI outside [0, 100]."
            )

    if record.stochastic_k is not None:

        if not (
            0
            <= record.stochastic_k
            <= 100
        ):

            raise ValueError(
                "Stochastic %K outside [0, 100]."
            )

    if record.stochastic_d is not None:

        if not (
            0
            <= record.stochastic_d
            <= 100
        ):

            raise ValueError(
                "Stochastic %D outside [0, 100]."
            )

    if record.adx is not None:

        if record.adx < 0:

            raise ValueError(
                "ADX cannot be negative."
            )

    if record.plus_di is not None:

        if not (
            0
            <= record.plus_di
            <= 100
        ):

            raise ValueError(
                "+DI outside [0, 100]."
            )

    if record.minus_di is not None:

        if not (
            0
            <= record.minus_di
            <= 100
        ):

            raise ValueError(
                "-DI outside [0, 100]."
            )

    return True


def validate_indicator_collection(
    records: Sequence[IndicatorRecord],
) -> bool:

    if records is None:

        raise ValueError(
            "Indicator collection cannot be None."
        )

    previous_index = -1

    for record in records:

        validate_indicator_record(
            record
        )

        if record.index <= previous_index:

            raise ValueError(
                "Indicator records must be strictly ordered."
            )

        previous_index = record.index

    return True


# ============================================================================
# LOOK-AHEAD AUDIT
# ============================================================================

def lookahead_audit(
    bars: Sequence[Any],
) -> bool:

    validated = validate_bars(
        bars
    )

    records = calculate_indicator_records(
        validated
    )

    fields = (
        "sma",
        "ema",
        "wma",
        "rsi",
        "macd",
        "macd_signal",
        "macd_histogram",
        "atr",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "bb_position",
        "stochastic_k",
        "stochastic_d",
        "adx",
        "plus_di",
        "minus_di",
        "vwap",
        "volume_change_ratio",
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_senkou_a",
        "ichimoku_senkou_b",
        "ichimoku_chikou",
    )

    # ------------------------------------------------------------------------
    # FULL-SERIES VS PREFIX AUDIT
    #
    # Every value at index i must be reproducible from:
    #
    #     bars[:i + 1]
    #
    # No indicator may depend on observations after i.
    # ------------------------------------------------------------------------

    for i, record in enumerate(
        records
    ):

        prefix = validated[
            :i + 1
        ]

        prefix_records = (
            calculate_indicator_records(
                prefix
            )
        )

        if not prefix_records:

            print(
                "LOOKAHEAD AUDIT ERROR | "
                f"index={i} | "
                "prefix produced no records"
            )

            return False

        prefix_record = (
            prefix_records[-1]
        )

        for field in fields:

            full_value = getattr(
                record,
                field,
            )

            prefix_value = getattr(
                prefix_record,
                field,
            )

            # ---------------------------------------------------------------
            # Both unavailable during warm-up
            # ---------------------------------------------------------------

            if (
                full_value is None
                and prefix_value is None
            ):

                continue

            # ---------------------------------------------------------------
            # One side available and other unavailable
            # ---------------------------------------------------------------

            if (
                full_value is None
                or prefix_value is None
            ):

                print(
                    "LOOKAHEAD MISMATCH | "
                    f"index={i} | "
                    f"field={field} | "
                    f"full={full_value} | "
                    f"prefix={prefix_value}"
                )

                return False

            # ---------------------------------------------------------------
            # Both must be finite
            # ---------------------------------------------------------------

            if not _finite(
                full_value
            ):

                print(
                    "LOOKAHEAD INVALID FULL VALUE | "
                    f"index={i} | "
                    f"field={field} | "
                    f"value={full_value}"
                )

                return False

            if not _finite(
                prefix_value
            ):

                print(
                    "LOOKAHEAD INVALID PREFIX VALUE | "
                    f"index={i} | "
                    f"field={field} | "
                    f"value={prefix_value}"
                )

                return False

            # ---------------------------------------------------------------
            # Numerical equality
            # ---------------------------------------------------------------

            if not math.isclose(
                float(full_value),
                float(prefix_value),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):

                print(
                    "LOOKAHEAD MISMATCH | "
                    f"index={i} | "
                    f"field={field} | "
                    f"full={full_value} | "
                    f"prefix={prefix_value}"
                )

                return False

    return True


# ============================================================================
# DETERMINISM AUDIT
# ============================================================================

def determinism_audit(
    bars: Sequence[Any],
) -> bool:

    first = (
        calculate_indicator_records(
            bars
        )
    )

    second = (
        calculate_indicator_records(
            bars
        )
    )

    if len(first) != len(second):

        return False

    for a, b in zip(
        first,
        second
    ):

        if a != b:

            return False

    return True


# ============================================================================
# SAMPLE PRINTER
# ============================================================================

def print_indicator_sample(
    records: Sequence[IndicatorRecord],
    limit: int = 10,
) -> None:

    print()

    print(
        "=" * 110
    )

    print(
        "ARUNDA TRADER — INDICATOR ENGINE v0.1"
    )

    print(
        "=" * 110
    )

    for record in records[
        -limit:
    ]:

        print(
            f"INDEX={record.index} | "
            f"CMC_ID={record.cmc_id} | "
            f"SYMBOL={record.symbol} | "
            f"CLOSE={record.close} | "
            f"RSI={record.rsi} | "
            f"EMA={record.ema} | "
            f"MACD={record.macd} | "
            f"ATR={record.atr} | "
            f"ADX={record.adx}"
        )


# ============================================================================
# SELF TEST
# ============================================================================

def self_test() -> bool:

    closes = [
        100,
        101,
        102,
        101,
        103,
        105,
        104,
        106,
        108,
        107,
        109,
        111,
        110,
        112,
        114,
        113,
        115,
        117,
        116,
        118,
        120,
        119,
        121,
        123,
        122,
        124,
        126,
        125,
        127,
        129,
        128,
        130,
        132,
        131,
        133,
        135,
        134,
        136,
        138,
        137,
        139,
        141,
        140,
        142,
        144,
        143,
        145,
        147,
        146,
        148,
        150,
        149,
        151,
        153,
        152,
        154,
        156,
        155,
        157,
        159,
        158,
    ]

    bars: List[IndicatorBar] = []

    for i, close in enumerate(
        closes
    ):

        bars.append(
            IndicatorBar(

                timestamp=i,

                high=close + 1.0,

                low=close - 1.0,

                close=float(close),

                open=float(close),

                volume=(
                    1000.0
                    + i * 10.0
                ),

                cmc_id=1,

                symbol="TEST",
            )
        )

    records = (
        calculate_indicator_records(
            bars
        )
    )

    assert len(records) == len(
        bars
    )

    assert validate_indicator_collection(
        records
    )

    # ------------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------------

    for record in records:

        assert record.cmc_id == 1

        assert record.symbol == "TEST"

    # ------------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------------

    assert [
        record.index
        for record in records
    ] == list(
        range(
            len(bars)
        )
    )

    # ------------------------------------------------------------------------
    # RSI range
    # ------------------------------------------------------------------------

    for record in records:

        if record.rsi is not None:

            assert (
                0.0
                <= record.rsi
                <= 100.0
            )

    # ------------------------------------------------------------------------
    # Stochastic range
    # ------------------------------------------------------------------------

    for record in records:

        if record.stochastic_k is not None:

            assert (
                0.0
                <= record.stochastic_k
                <= 100.0
            )

        if record.stochastic_d is not None:

            assert (
                0.0
                <= record.stochastic_d
                <= 100.0
            )

    # ------------------------------------------------------------------------
    # DI range
    # ------------------------------------------------------------------------

    for record in records:

        if record.plus_di is not None:

            assert (
                0.0
                <= record.plus_di
                <= 100.0
            )

        if record.minus_di is not None:

            assert (
                0.0
                <= record.minus_di
                <= 100.0
            )

    # ------------------------------------------------------------------------
    # Warm-up semantics
    # ------------------------------------------------------------------------

    assert records[0].sma is None

    assert records[0].rsi is None

    assert records[0].atr is None

    assert records[0].bb_middle is None

    # ------------------------------------------------------------------------
    # EMA seed
    # ------------------------------------------------------------------------

    ema_test = calculate_ema(
        closes,
        period=5,
    )

    assert ema_test[0] is None

    assert ema_test[3] is None

    assert ema_test[4] is not None

    # ------------------------------------------------------------------------
    # SMA mathematics
    # ------------------------------------------------------------------------

    sma_test = calculate_sma(
        closes,
        period=5,
    )

    expected_sma = (
        sum(closes[:5])
        / 5.0
    )

    assert math.isclose(
        sma_test[4],
        expected_sma,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    # ------------------------------------------------------------------------
    # WMA
    # ------------------------------------------------------------------------

    wma_test = calculate_wma(
        closes,
        period=3,
    )

    expected_wma = (
        closes[2] * 3
        + closes[1] * 2
        + closes[0] * 1
    ) / 6.0

    assert math.isclose(
        wma_test[2],
        expected_wma,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    # ------------------------------------------------------------------------
    # RSI constant sequence behavior
    # ------------------------------------------------------------------------

    constant = [
        100.0
        for _ in range(30)
    ]

    constant_rsi = calculate_rsi(
        constant,
        period=14,
    )

    assert (
        constant_rsi[14]
        == 50.0
    )

    # ------------------------------------------------------------------------
    # Bollinger mathematical sanity
    # ------------------------------------------------------------------------

    bb = calculate_bollinger_bands(
        closes,
        period=5,
        stddev_multiplier=2.0,
    )

    (
        middle,
        upper,
        lower,
        _,
        _,
    ) = bb

    assert middle[4] is not None

    assert upper[4] >= middle[4]

    assert lower[4] <= middle[4]

    # ------------------------------------------------------------------------
    # ATR positivity
    # ------------------------------------------------------------------------

    atr = calculate_atr(
        bars,
        period=5,
    )

    for value in atr:

        if value is not None:

            assert value >= 0.0

    # ------------------------------------------------------------------------
    # ADX / DI mathematical sanity
    # ------------------------------------------------------------------------

    adx, plus_di, minus_di = (
        calculate_adx(
            bars,
            period=14,
        )
    )

    assert len(adx) == len(bars)

    assert len(plus_di) == len(bars)

    assert len(minus_di) == len(bars)

    for value in adx:

        if value is not None:

            assert (
                value >= 0.0
            )

    for value in plus_di:

        if value is not None:

            assert (
                0.0
                <= value
                <= 100.0
            )

    for value in minus_di:

        if value is not None:

            assert (
                0.0
                <= value
                <= 100.0
            )

    # ------------------------------------------------------------------------
    # VWAP positivity / finite
    # ------------------------------------------------------------------------

    vwap = calculate_vwap(
        bars
    )

    for value in vwap:

        if value is not None:

            assert _finite(
                value
            )

    # ------------------------------------------------------------------------
    # MACD structure
    # ------------------------------------------------------------------------

    macd, signal, histogram = (
        calculate_macd(
            closes
        )
    )

    assert len(macd) == len(
        closes
    )

    assert len(signal) == len(
        closes
    )

    assert len(histogram) == len(
        closes
    )

    # ------------------------------------------------------------------------
    # Ichimoku warm-up
    # ------------------------------------------------------------------------

    ichi = calculate_ichimoku(
        bars
    )

    (
        tenkan,
        kijun,
        senkou_a,
        senkou_b,
        chikou,
    ) = ichi

    assert tenkan[0] is None

    assert kijun[0] is None

    assert senkou_b[0] is None

    # ------------------------------------------------------------------------
    # Numeric safety
    # ------------------------------------------------------------------------

    assert _finite(
        100.0
    )

    assert not _finite(
        float("nan")
    )

    assert not _finite(
        float("inf")
    )

    # ------------------------------------------------------------------------
    # Invalid OHLC
    # ------------------------------------------------------------------------

    invalid = [
        IndicatorBar(
            timestamp=0,
            high=10,
            low=20,
            close=15,
        )
    ]

    try:

        validate_bars(
            invalid
        )

        raise AssertionError(
            "Invalid OHLC was not rejected."
        )

    except ValueError:

        pass

    # ------------------------------------------------------------------------
    # Negative volume
    # ------------------------------------------------------------------------

    invalid_volume = [
        IndicatorBar(
            timestamp=0,
            high=10,
            low=5,
            close=8,
            volume=-1,
        )
    ]

    try:

        validate_bars(
            invalid_volume
        )

        raise AssertionError(
            "Negative volume was not rejected."
        )

    except ValueError:

        pass

    # ------------------------------------------------------------------------
    # Look-ahead protection
    # ------------------------------------------------------------------------

    assert lookahead_audit(
        bars
    )

    # ------------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------------

    assert determinism_audit(
        bars
    )

    return True


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    print(
        "=" * 110
    )

    print(
        "ARUNDA TRADER — DEV-06 — STEP 12"
    )

    print(
        "INDICATOR ENGINE v0.1"
    )

    print(
        "SELF TEST"
    )

    print(
        "=" * 110
    )

    try:

        self_test()

        print()

        print(
            "SELF TEST RESULT : PASS"
        )

        print()

        print(
            "ENGINE            : INDICATOR_ENGINE_v0.1"
        )

        print(
            "DATABASE          : NOT USED"
        )

        print(
            "DATABASE WRITE    : NONE"
        )

        print(
            "LOOK-AHEAD        : PROTECTED"
        )

        print(
            "CMC_ID IDENTITY   : PRESERVED"
        )

        print(
            "DECISION OUTPUT   : NONE"
        )

        print(
            "STATUS            : READY FOR STEP 12A CONTRACT AUDIT"
        )

    except Exception as exc:

        print()

        print(
            "SELF TEST RESULT : FAIL"
        )

        print(
            f"ERROR            : "
            f"{type(exc).__name__}: {exc}"
        )

        raise