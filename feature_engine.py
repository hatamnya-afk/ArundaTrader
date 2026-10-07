"""
ARUNDA TRADER — DEV-06
FEATURE ENGINE v0.1

Purpose
-------
Transform Market Structure and Indicator Engine outputs into deterministic,
causal, normalized market features.

Architecture
------------
- Analysis / Feature Layer only
- Database independent
- No SQL
- No database writes
- No trading decisions
- No BUY / SELL output
- No LONG / SHORT output
- No look-ahead
- Input order preserved
- Timestamp identity preserved
- CMC_ID identity preserved
- Symbol identity preserved

Design Principles
-----------------
1. Every feature at index i uses information available at or before i.
2. No future observations are accessed.
3. Missing upstream information remains None.
4. Non-finite numeric values are rejected.
5. Input ordering is preserved.
6. Identity metadata is preserved.
7. Feature generation is deterministic.
8. Features describe market state.
9. Features do not make trading decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Mapping
import math


ENGINE_NAME = "FEATURE_ENGINE_v0.1"


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
    numerator: Optional[float],
    denominator: Optional[float],
) -> Optional[float]:

    if numerator is None or denominator is None:
        return None

    if not _finite(numerator):
        return None

    if not _finite(denominator):
        return None

    if denominator == 0:
        return None

    result = numerator / denominator

    if not _finite(result):
        return None

    return result


def _clip(
    value: Optional[float],
    lower: float,
    upper: float,
) -> Optional[float]:

    if value is None:
        return None

    if not _finite(value):
        return None

    return max(
        lower,
        min(
            upper,
            value,
        ),
    )


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass(frozen=True)
class FeatureBar:
    timestamp: Any

    high: float
    low: float
    close: float

    open: Optional[float] = None
    volume: Optional[float] = None

    cmc_id: Optional[int] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class FeatureRecord:
    index: int
    timestamp: Any

    cmc_id: Optional[int]
    symbol: Optional[str]

    close: float

    # ------------------------------------------------------------------------
    # Trend
    # ------------------------------------------------------------------------

    ema_distance: Optional[float]
    sma_distance: Optional[float]
    wma_distance: Optional[float]

    # ------------------------------------------------------------------------
    # Momentum
    # ------------------------------------------------------------------------

    rsi_normalized: Optional[float]
    macd_normalized: Optional[float]
    stochastic_position: Optional[float]

    # ------------------------------------------------------------------------
    # Volatility
    # ------------------------------------------------------------------------

    atr_normalized: Optional[float]
    bb_position: Optional[float]
    bb_width: Optional[float]

    # ------------------------------------------------------------------------
    # Trend Strength
    # ------------------------------------------------------------------------

    adx_normalized: Optional[float]
    di_spread: Optional[float]

    # ------------------------------------------------------------------------
    # Price / Volume
    # ------------------------------------------------------------------------

    price_to_vwap: Optional[float]
    volume_change_ratio: Optional[float]

    # ------------------------------------------------------------------------
    # Ichimoku
    # ------------------------------------------------------------------------

    ichimoku_tenkan_distance: Optional[float]
    ichimoku_kijun_distance: Optional[float]
    ichimoku_cloud_position: Optional[float]

    # ------------------------------------------------------------------------
    # Market Structure
    # ------------------------------------------------------------------------

    structure_direction: Optional[str]
    structure_strength: Optional[str]
    structure_confidence: Optional[str]

    structure_point_type: Optional[str]

    bos_recent: Optional[bool]
    choch_recent: Optional[bool]

    # ------------------------------------------------------------------------
    # Composite descriptive features
    # ------------------------------------------------------------------------

    trend_alignment: Optional[float]
    momentum_alignment: Optional[float]
    volatility_regime: Optional[str]
    structure_regime: Optional[str]


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_feature_bar(
    bar: Any,
) -> FeatureBar:

    if isinstance(bar, FeatureBar):

        result = bar

    elif isinstance(bar, Mapping):

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

        result = FeatureBar(
            timestamp=bar["timestamp"],
            high=_float(bar["high"]),
            low=_float(bar["low"]),
            close=_float(bar["close"]),
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

    if result.open is not None:

        if not _finite(result.open):

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


def validate_feature_bars(
    bars: Sequence[Any],
) -> List[FeatureBar]:

    if bars is None:

        raise ValueError(
            "bars cannot be None"
        )

    result = [
        validate_feature_bar(bar)
        for bar in bars
    ]

    if not result:

        raise ValueError(
            "bars cannot be empty"
        )

    return result


# ============================================================================
# GENERIC FIELD ACCESS
# ============================================================================

def _get(
    obj: Any,
    field: str,
    default: Any = None,
) -> Any:

    if obj is None:

        return default

    if isinstance(obj, Mapping):

        return obj.get(
            field,
            default,
        )

    return getattr(
        obj,
        field,
        default,
    )


# ============================================================================
# INDICATOR FIELD ACCESS
# ============================================================================

def _indicator_value(
    record: Any,
    field: str,
) -> Optional[float]:

    value = _get(
        record,
        field,
    )

    if value is None:

        return None

    if not _finite(value):

        raise ValueError(
            f"Non-finite indicator value: {field}"
        )

    return float(value)


# ============================================================================
# STRUCTURE FIELD ACCESS
# ============================================================================

def _structure_value(
    record: Any,
    field: str,
) -> Any:

    return _get(
        record,
        field,
    )


def _normalize_direction(
    value: Any,
) -> Optional[str]:

    if value is None:

        return None

    value = str(value).upper()

    allowed = {
        "BULLISH",
        "BEARISH",
        "NEUTRAL",
        "UNKNOWN",
    }

    if value not in allowed:

        return None

    return value


def _normalize_strength(
    value: Any,
) -> Optional[str]:

    if value is None:

        return None

    value = str(value).upper()

    allowed = {
        "WEAK",
        "MEDIUM",
        "MODERATE",
        "STRONG",
        "UNKNOWN",
    }

    if value not in allowed:

        return None

    return value


def _normalize_confidence(
    value: Any,
) -> Optional[str]:

    if value is None:

        return None

    value = str(value).upper()

    allowed = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "UNKNOWN",
    }

    if value not in allowed:

        return None

    return value


# ============================================================================
# TREND FEATURES
# ============================================================================

def calculate_trend_features(
    close: float,
    indicator: Any,
) -> Dict[str, Optional[float]]:

    ema = _indicator_value(
        indicator,
        "ema",
    )

    sma = _indicator_value(
        indicator,
        "sma",
    )

    wma = _indicator_value(
        indicator,
        "wma",
    )

    return {

        "ema_distance": _safe_div(
            close - ema
            if ema is not None
            else None,
            ema,
        ),

        "sma_distance": _safe_div(
            close - sma
            if sma is not None
            else None,
            sma,
        ),

        "wma_distance": _safe_div(
            close - wma
            if wma is not None
            else None,
            wma,
        ),
    }


# ============================================================================
# MOMENTUM FEATURES
# ============================================================================

def calculate_momentum_features(
    indicator: Any,
) -> Dict[str, Optional[float]]:

    rsi = _indicator_value(
        indicator,
        "rsi",
    )

    macd = _indicator_value(
        indicator,
        "macd",
    )

    stochastic = _indicator_value(
        indicator,
        "stochastic_k",
    )

    return {

        "rsi_normalized": (
            _clip(
                (rsi - 50.0) / 50.0,
                -1.0,
                1.0,
            )
            if rsi is not None
            else None
        ),

        "macd_normalized": macd,

        "stochastic_position": (
            _clip(
                (stochastic - 50.0) / 50.0,
                -1.0,
                1.0,
            )
            if stochastic is not None
            else None
        ),
    }


# ============================================================================
# VOLATILITY FEATURES
# ============================================================================

def calculate_volatility_features(
    close: float,
    indicator: Any,
) -> Dict[str, Optional[float]]:

    atr = _indicator_value(
        indicator,
        "atr",
    )

    bb_position = _indicator_value(
        indicator,
        "bb_position",
    )

    bb_width = _indicator_value(
        indicator,
        "bb_width",
    )

    return {

        "atr_normalized": _safe_div(
            atr,
            close,
        ),

        "bb_position": bb_position,

        "bb_width": bb_width,
    }


# ============================================================================
# TREND STRENGTH FEATURES
# ============================================================================

def calculate_trend_strength_features(
    indicator: Any,
) -> Dict[str, Optional[float]]:

    adx = _indicator_value(
        indicator,
        "adx",
    )

    plus_di = _indicator_value(
        indicator,
        "plus_di",
    )

    minus_di = _indicator_value(
        indicator,
        "minus_di",
    )

    di_spread = None

    if (
        plus_di is not None
        and minus_di is not None
    ):

        di_spread = _safe_div(
            plus_di - minus_di,
            plus_di + minus_di,
        )

        di_spread = _clip(
            di_spread,
            -1.0,
            1.0,
        )

    return {

        "adx_normalized": (
            _clip(
                adx / 100.0,
                0.0,
                1.0,
            )
            if adx is not None
            else None
        ),

        "di_spread": di_spread,
    }


# ============================================================================
# PRICE / VOLUME FEATURES
# ============================================================================

def calculate_price_volume_features(
    close: float,
    indicator: Any,
) -> Dict[str, Optional[float]]:

    vwap = _indicator_value(
        indicator,
        "vwap",
    )

    volume_change_ratio = _indicator_value(
        indicator,
        "volume_change_ratio",
    )

    return {

        "price_to_vwap": _safe_div(
            close - vwap
            if vwap is not None
            else None,
            vwap,
        ),

        "volume_change_ratio":
            volume_change_ratio,
    }


# ============================================================================
# ICHIMOKU FEATURES
# ============================================================================

def calculate_ichimoku_features(
    close: float,
    indicator: Any,
) -> Dict[str, Optional[float]]:

    tenkan = _indicator_value(
        indicator,
        "ichimoku_tenkan",
    )

    kijun = _indicator_value(
        indicator,
        "ichimoku_kijun",
    )

    senkou_a = _indicator_value(
        indicator,
        "ichimoku_senkou_a",
    )

    senkou_b = _indicator_value(
        indicator,
        "ichimoku_senkou_b",
    )

    # ------------------------------------------------------------------------
    # Tenkan distance
    # ------------------------------------------------------------------------

    tenkan_distance = _safe_div(
        close - tenkan
        if tenkan is not None
        else None,
        tenkan,
    )

    # ------------------------------------------------------------------------
    # Kijun distance
    # ------------------------------------------------------------------------

    kijun_distance = _safe_div(
        close - kijun
        if kijun is not None
        else None,
        kijun,
    )

    # ------------------------------------------------------------------------
    # Cloud position
    #
    # Contract:
    #
    #     -1.0  = below cloud
    #      0.0  = inside / centered around cloud
    #     +1.0  = above cloud
    #
    # IMPORTANT:
    # The old implementation calculated a linear extrapolation outside
    # the cloud, which could produce values such as +3, +10, etc.
    #
    # That violates the Feature Engine normalized-feature contract.
    #
    # We therefore use a categorical-position encoding:
    #
    #     below cloud  -> -1
    #     inside cloud -> normalized internal position
    #     above cloud  -> +1
    #
    # For values inside the cloud:
    #
    #     low  -> -1
    #     mid  ->  0
    #     high -> +1
    #
    # Thus the feature is always bounded.
    # ------------------------------------------------------------------------

    cloud_position = None

    if (
        senkou_a is not None
        and senkou_b is not None
    ):

        cloud_low = min(
            senkou_a,
            senkou_b,
        )

        cloud_high = max(
            senkou_a,
            senkou_b,
        )

        cloud_width = (
            cloud_high
            - cloud_low
        )

        # ------------------------------------------------------------
        # Degenerate cloud
        # ------------------------------------------------------------

        if cloud_width == 0:

            if close > cloud_high:

                cloud_position = 1.0

            elif close < cloud_low:

                cloud_position = -1.0

            else:

                cloud_position = 0.0

        # ------------------------------------------------------------
        # Normal cloud
        # ------------------------------------------------------------

        else:

            if close <= cloud_low:

                cloud_position = -1.0

            elif close >= cloud_high:

                cloud_position = 1.0

            else:

                internal_position = (
                    (
                        close
                        - cloud_low
                    )
                    / cloud_width
                )

                cloud_position = (
                    internal_position * 2.0
                    - 1.0
                )

                cloud_position = _clip(
                    cloud_position,
                    -1.0,
                    1.0,
                )

    return {

        "ichimoku_tenkan_distance":
            tenkan_distance,

        "ichimoku_kijun_distance":
            kijun_distance,

        "ichimoku_cloud_position":
            cloud_position,
    }


# ============================================================================
# STRUCTURE FEATURES
# ============================================================================

def calculate_structure_features(
    structure: Any,
) -> Dict[str, Any]:

    direction = _normalize_direction(
        _structure_value(
            structure,
            "direction",
        )
    )

    strength = _normalize_strength(
        _structure_value(
            structure,
            "strength",
        )
    )

    confidence = _normalize_confidence(
        _structure_value(
            structure,
            "confidence",
        )
    )

    point_type = _structure_value(
        structure,
        "structure",
    )

    if point_type is None:

        point_type = _structure_value(
            structure,
            "type",
        )

    bos = _structure_value(
        structure,
        "bos",
    )

    choch = _structure_value(
        structure,
        "choch",
    )

    if bos is None:

        bos = _structure_value(
            structure,
            "is_bos",
        )

    if choch is None:

        choch = _structure_value(
            structure,
            "is_choch",
        )

    return {

        "structure_direction":
            direction,

        "structure_strength":
            strength,

        "structure_confidence":
            confidence,

        "structure_point_type": (
            str(point_type).upper()
            if point_type is not None
            else None
        ),

        "bos_recent": (
            bool(bos)
            if bos is not None
            else None
        ),

        "choch_recent": (
            bool(choch)
            if choch is not None
            else None
        ),
    }


# ============================================================================
# COMPOSITE FEATURES
# ============================================================================

def calculate_composite_features(
    trend: Dict[str, Optional[float]],
    momentum: Dict[str, Optional[float]],
    volatility: Dict[str, Optional[float]],
    strength: Dict[str, Optional[float]],
    structure: Dict[str, Any],
) -> Dict[str, Any]:

    trend_values = [

        trend["ema_distance"],

        trend["sma_distance"],

        trend["wma_distance"],
    ]

    valid_trend = [

        value
        for value in trend_values
        if value is not None
    ]

    trend_alignment = None

    if valid_trend:

        trend_alignment = sum(

            math.copysign(
                1.0,
                value,
            )

            if value != 0
            else 0.0

            for value in valid_trend

        ) / len(valid_trend)

        trend_alignment = _clip(
            trend_alignment,
            -1.0,
            1.0,
        )

    momentum_values = [

        momentum["rsi_normalized"],

        momentum["stochastic_position"],

        strength["di_spread"],
    ]

    valid_momentum = [

        value
        for value in momentum_values
        if value is not None
    ]

    momentum_alignment = None

    if valid_momentum:

        momentum_alignment = sum(
            valid_momentum
        ) / len(valid_momentum)

        momentum_alignment = _clip(
            momentum_alignment,
            -1.0,
            1.0,
        )

    atr_normalized = volatility[
        "atr_normalized"
    ]

    volatility_regime = None

    if atr_normalized is not None:

        if atr_normalized < 0.005:

            volatility_regime = "LOW"

        elif atr_normalized < 0.02:

            volatility_regime = "MEDIUM"

        else:

            volatility_regime = "HIGH"

    direction = structure[
        "structure_direction"
    ]

    strength_value = structure[
        "structure_strength"
    ]

    if direction is None:

        structure_regime = None

    elif strength_value is None:

        structure_regime = direction

    else:

        structure_regime = (
            f"{direction}_{strength_value}"
        )

    return {

        "trend_alignment":
            trend_alignment,

        "momentum_alignment":
            momentum_alignment,

        "volatility_regime":
            volatility_regime,

        "structure_regime":
            structure_regime,
    }


# ============================================================================
# FEATURE RECORD GENERATION
# ============================================================================

def calculate_feature_records(
    bars: Sequence[Any],
    indicator_records: Sequence[Any],
    structure_records: Optional[Sequence[Any]] = None,
) -> List[FeatureRecord]:

    validated = validate_feature_bars(
        bars
    )

    if indicator_records is None:

        raise ValueError(
            "indicator_records cannot be None"
        )

    if len(indicator_records) != len(validated):

        raise ValueError(
            "Indicator records length must match bars."
        )

    if structure_records is not None:

        if len(structure_records) != len(validated):

            raise ValueError(
                "Structure records length must match bars."
            )

    records: List[FeatureRecord] = []

    for i, bar in enumerate(validated):

        indicator = indicator_records[i]

        structure = (
            structure_records[i]
            if structure_records is not None
            else None
        )

        trend = calculate_trend_features(
            bar.close,
            indicator,
        )

        momentum = calculate_momentum_features(
            indicator,
        )

        volatility = calculate_volatility_features(
            bar.close,
            indicator,
        )

        trend_strength = (
            calculate_trend_strength_features(
                indicator
            )
        )

        price_volume = (
            calculate_price_volume_features(
                bar.close,
                indicator,
            )
        )

        ichimoku = calculate_ichimoku_features(
            bar.close,
            indicator,
        )

        structure_features = (
            calculate_structure_features(
                structure
            )
        )

        composite = (
            calculate_composite_features(
                trend,
                momentum,
                volatility,
                trend_strength,
                structure_features,
            )
        )

        records.append(

            FeatureRecord(

                index=i,

                timestamp=bar.timestamp,

                cmc_id=bar.cmc_id,

                symbol=bar.symbol,

                close=bar.close,

                ema_distance=trend[
                    "ema_distance"
                ],

                sma_distance=trend[
                    "sma_distance"
                ],

                wma_distance=trend[
                    "wma_distance"
                ],

                rsi_normalized=momentum[
                    "rsi_normalized"
                ],

                macd_normalized=momentum[
                    "macd_normalized"
                ],

                stochastic_position=momentum[
                    "stochastic_position"
                ],

                atr_normalized=volatility[
                    "atr_normalized"
                ],

                bb_position=volatility[
                    "bb_position"
                ],

                bb_width=volatility[
                    "bb_width"
                ],

                adx_normalized=trend_strength[
                    "adx_normalized"
                ],

                di_spread=trend_strength[
                    "di_spread"
                ],

                price_to_vwap=price_volume[
                    "price_to_vwap"
                ],

                volume_change_ratio=price_volume[
                    "volume_change_ratio"
                ],

                ichimoku_tenkan_distance=ichimoku[
                    "ichimoku_tenkan_distance"
                ],

                ichimoku_kijun_distance=ichimoku[
                    "ichimoku_kijun_distance"
                ],

                ichimoku_cloud_position=ichimoku[
                    "ichimoku_cloud_position"
                ],

                structure_direction=structure_features[
                    "structure_direction"
                ],

                structure_strength=structure_features[
                    "structure_strength"
                ],

                structure_confidence=structure_features[
                    "structure_confidence"
                ],

                structure_point_type=structure_features[
                    "structure_point_type"
                ],

                bos_recent=structure_features[
                    "bos_recent"
                ],

                choch_recent=structure_features[
                    "choch_recent"
                ],

                trend_alignment=composite[
                    "trend_alignment"
                ],

                momentum_alignment=composite[
                    "momentum_alignment"
                ],

                volatility_regime=composite[
                    "volatility_regime"
                ],

                structure_regime=composite[
                    "structure_regime"
                ],
            )
        )

    return records


# ============================================================================
# OUTPUT VALIDATION
# ============================================================================

def validate_feature_record(
    record: FeatureRecord,
) -> bool:

    if not isinstance(
        record,
        FeatureRecord,
    ):

        raise TypeError(
            "Expected FeatureRecord."
        )

    if record.index < 0:

        raise ValueError(
            "Feature index cannot be negative."
        )

    if not _finite(record.close):

        raise ValueError(
            "Feature close must be finite."
        )

    numeric_fields = (

        "ema_distance",

        "sma_distance",

        "wma_distance",

        "rsi_normalized",

        "macd_normalized",

        "stochastic_position",

        "atr_normalized",

        "bb_position",

        "bb_width",

        "adx_normalized",

        "di_spread",

        "price_to_vwap",

        "volume_change_ratio",

        "ichimoku_tenkan_distance",

        "ichimoku_kijun_distance",

        "ichimoku_cloud_position",

        "trend_alignment",

        "momentum_alignment",
    )

    for field in numeric_fields:

        value = getattr(
            record,
            field,
        )

        if value is not None:

            if not _finite(value):

                raise ValueError(
                    f"Non-finite feature field: {field}"
                )

    bounded_fields = (

        "rsi_normalized",

        "stochastic_position",

        "bb_position",

        "adx_normalized",

        "di_spread",

        "ichimoku_cloud_position",

        "trend_alignment",

        "momentum_alignment",
    )

    for field in bounded_fields:

        value = getattr(
            record,
            field,
        )

        if value is not None:

            # --------------------------------------------------------
            # BB position is intentionally inherited from the
            # Indicator Engine contract.
            # --------------------------------------------------------

            if field == "bb_position":

                continue

            if not -1.0 <= value <= 1.0:

                raise ValueError(
                    f"Feature outside [-1, 1]: {field}"
                )

    return True


def validate_feature_collection(
    records: Sequence[FeatureRecord],
) -> bool:

    if records is None:

        raise ValueError(
            "Feature collection cannot be None."
        )

    previous_index = -1

    for record in records:

        validate_feature_record(
            record
        )

        if record.index <= previous_index:

            raise ValueError(
                "Feature records must be strictly ordered."
            )

        previous_index = record.index

    return True


# ============================================================================
# LOOK-AHEAD AUDIT
# ============================================================================

def lookahead_audit(
    bars: Sequence[Any],
    indicator_records: Sequence[Any],
    structure_records: Optional[Sequence[Any]] = None,
) -> bool:

    validated = validate_feature_bars(
        bars
    )

    full = calculate_feature_records(
        validated,
        indicator_records,
        structure_records,
    )

    fields = (

        "ema_distance",

        "sma_distance",

        "wma_distance",

        "rsi_normalized",

        "macd_normalized",

        "stochastic_position",

        "atr_normalized",

        "bb_position",

        "bb_width",

        "adx_normalized",

        "di_spread",

        "price_to_vwap",

        "volume_change_ratio",

        "ichimoku_tenkan_distance",

        "ichimoku_kijun_distance",

        "ichimoku_cloud_position",

        "structure_direction",

        "structure_strength",

        "structure_confidence",

        "structure_point_type",

        "bos_recent",

        "choch_recent",

        "trend_alignment",

        "momentum_alignment",

        "volatility_regime",

        "structure_regime",
    )

    for i, record in enumerate(full):

        prefix_bars = validated[
            :i + 1
        ]

        prefix_indicators = indicator_records[
            :i + 1
        ]

        prefix_structures = (

            structure_records[
                :i + 1
            ]

            if structure_records is not None

            else None
        )

        prefix = calculate_feature_records(

            prefix_bars,

            prefix_indicators,

            prefix_structures,
        )

        if not prefix:

            return False

        prefix_record = prefix[-1]

        for field in fields:

            a = getattr(
                record,
                field,
            )

            b = getattr(
                prefix_record,
                field,
            )

            if a is None and b is None:

                continue

            if a is None or b is None:

                print(

                    "LOOKAHEAD MISMATCH | "

                    f"index={i} | "

                    f"field={field} | "

                    f"full={a} | "

                    f"prefix={b}"
                )

                return False

            if isinstance(a, bool):

                if a != b:

                    print(

                        "LOOKAHEAD MISMATCH | "

                        f"index={i} | "

                        f"field={field} | "

                        f"full={a} | "

                        f"prefix={b}"
                    )

                    return False

                continue

            if isinstance(a, str):

                if a != b:

                    print(

                        "LOOKAHEAD MISMATCH | "

                        f"index={i} | "

                        f"field={field} | "

                        f"full={a} | "

                        f"prefix={b}"
                    )

                    return False

                continue

            if not _finite(a):

                return False

            if not _finite(b):

                return False

            if not math.isclose(

                float(a),

                float(b),

                rel_tol=1e-12,

                abs_tol=1e-12,
            ):

                print(

                    "LOOKAHEAD MISMATCH | "

                    f"index={i} | "

                    f"field={field} | "

                    f"full={a} | "

                    f"prefix={b}"
                )

                return False

    return True


# ============================================================================
# DETERMINISM AUDIT
# ============================================================================

def determinism_audit(
    bars: Sequence[Any],
    indicator_records: Sequence[Any],
    structure_records: Optional[Sequence[Any]] = None,
) -> bool:

    first = calculate_feature_records(

        bars,

        indicator_records,

        structure_records,
    )

    second = calculate_feature_records(

        bars,

        indicator_records,

        structure_records,
    )

    return first == second


# ============================================================================
# SAMPLE PRINTER
# ============================================================================

def print_feature_sample(
    records: Sequence[FeatureRecord],
    limit: int = 10,
) -> None:

    print()

    print("=" * 110)

    print(
        "ARUNDA TRADER — FEATURE ENGINE v0.1"
    )

    print("=" * 110)

    for record in records[-limit:]:

        print(

            f"INDEX={record.index} | "

            f"CMC_ID={record.cmc_id} | "

            f"SYMBOL={record.symbol} | "

            f"CLOSE={record.close} | "

            f"RSI_N={record.rsi_normalized} | "

            f"EMA_D={record.ema_distance} | "

            f"ATR_N={record.atr_normalized} | "

            f"ADX_N={record.adx_normalized} | "

            f"ICHI_CLOUD={record.ichimoku_cloud_position} | "

            f"STRUCTURE={record.structure_direction}"
        )


# ============================================================================
# SELF TEST
# ============================================================================

def self_test() -> bool:

    bars: List[FeatureBar] = []

    for i in range(80):

        close = 100.0 + i

        bars.append(

            FeatureBar(

                timestamp=i,

                high=close + 1.0,

                low=close - 1.0,

                close=close,

                open=close,

                volume=1000.0 + i * 10.0,

                cmc_id=1,

                symbol="TEST",
            )
        )

    # ------------------------------------------------------------------------
    # Synthetic indicator records
    # ------------------------------------------------------------------------

    class SyntheticIndicator:

        def __init__(
            self,
            index: int,
        ):

            close = 100.0 + index

            self.ema = (

                close - 0.5

                if index >= 19

                else None
            )

            self.sma = (

                close - 0.4

                if index >= 19

                else None
            )

            self.wma = (

                close - 0.3

                if index >= 19

                else None
            )

            self.rsi = (

                60.0

                if index >= 14

                else None
            )

            self.macd = (

                1.0

                if index >= 25

                else None
            )

            self.stochastic_k = (

                70.0

                if index >= 15

                else None
            )

            self.atr = (

                2.0

                if index >= 13

                else None
            )

            self.bb_position = (

                0.7

                if index >= 19

                else None
            )

            self.bb_width = (

                0.04

                if index >= 19

                else None
            )

            self.adx = (

                30.0

                if index >= 27

                else None
            )

            self.plus_di = (

                35.0

                if index >= 13

                else None
            )

            self.minus_di = (

                15.0

                if index >= 13

                else None
            )

            self.vwap = (

                close - 0.2

                if index >= 0

                else None
            )

            self.volume_change_ratio = (

                1.01

                if index >= 1

                else None
            )

            self.ichimoku_tenkan = (

                close - 0.2

                if index >= 8

                else None
            )

            self.ichimoku_kijun = (

                close - 0.1

                if index >= 25

                else None
            )

            self.ichimoku_senkou_a = (

                close - 0.1

                if index >= 25

                else None
            )

            self.ichimoku_senkou_b = (

                close - 0.05

                if index >= 51

                else None
            )

    indicators = [

        SyntheticIndicator(i)

        for i in range(
            len(bars)
        )
    ]

    # ------------------------------------------------------------------------
    # Synthetic structure records
    # ------------------------------------------------------------------------

    structures = []

    for i in range(
        len(bars)
    ):

        structures.append(

            {

                "direction":
                    "BULLISH",

                "strength":
                    "STRONG",

                "confidence":
                    "HIGH",

                "structure":
                    "HH",

                "bos":
                    i >= 30,

                "choch":
                    False,
            }
        )

    # ------------------------------------------------------------------------
    # Feature generation
    # ------------------------------------------------------------------------

    records = calculate_feature_records(

        bars,

        indicators,

        structures,
    )

    assert len(records) == len(bars)

    assert validate_feature_collection(
        records
    )

    # ------------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------------

    for record in records:

        assert record.cmc_id == 1

        assert record.symbol == "TEST"

        assert record.timestamp == record.index

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
    # Warm-up
    # ------------------------------------------------------------------------

    assert records[0].ema_distance is None

    assert records[0].rsi_normalized is None

    assert records[0].atr_normalized is None

    assert records[0].ichimoku_cloud_position is None

    # ------------------------------------------------------------------------
    # Range checks
    # ------------------------------------------------------------------------

    for record in records:

        if record.rsi_normalized is not None:

            assert (
                -1.0
                <= record.rsi_normalized
                <= 1.0
            )

        if record.stochastic_position is not None:

            assert (
                -1.0
                <= record.stochastic_position
                <= 1.0
            )

        if record.adx_normalized is not None:

            assert (
                0.0
                <= record.adx_normalized
                <= 1.0
            )

        if record.di_spread is not None:

            assert (
                -1.0
                <= record.di_spread
                <= 1.0
            )

        if record.ichimoku_cloud_position is not None:

            assert (
                -1.0
                <= record.ichimoku_cloud_position
                <= 1.0
            )

    # ------------------------------------------------------------------------
    # Structure
    # ------------------------------------------------------------------------

    assert (
        records[-1].structure_direction
        == "BULLISH"
    )

    assert (
        records[-1].structure_strength
        == "STRONG"
    )

    assert (
        records[-1].structure_confidence
        == "HIGH"
    )

    # ------------------------------------------------------------------------
    # Numeric safety
    # ------------------------------------------------------------------------

    assert _finite(1.0)

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

        FeatureBar(

            timestamp=0,

            high=10.0,

            low=20.0,

            close=15.0,
        )
    ]

    try:

        validate_feature_bars(
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

        FeatureBar(

            timestamp=0,

            high=10.0,

            low=5.0,

            close=8.0,

            volume=-1.0,
        )
    ]

    try:

        validate_feature_bars(
            invalid_volume
        )

        raise AssertionError(
            "Negative volume was not rejected."
        )

    except ValueError:

        pass

    # ------------------------------------------------------------------------
    # Explicit Ichimoku normalization test
    # ------------------------------------------------------------------------

    class CloudTestIndicator:

        ichimoku_tenkan = 100.0

        ichimoku_kijun = 100.0

        ichimoku_senkou_a = 100.0

        ichimoku_senkou_b = 110.0

    below = calculate_ichimoku_features(
        50.0,
        CloudTestIndicator(),
    )

    inside = calculate_ichimoku_features(
        105.0,
        CloudTestIndicator(),
    )

    above = calculate_ichimoku_features(
        150.0,
        CloudTestIndicator(),
    )

    assert (
        below["ichimoku_cloud_position"]
        == -1.0
    )

    assert (
        above["ichimoku_cloud_position"]
        == 1.0
    )

    assert (
        -1.0
        <= inside["ichimoku_cloud_position"]
        <= 1.0
    )

    # ------------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------------

    assert determinism_audit(

        bars,

        indicators,

        structures,
    )

    # ------------------------------------------------------------------------
    # Look-ahead
    # ------------------------------------------------------------------------

    assert lookahead_audit(

        bars,

        indicators,

        structures,
    )

    # ------------------------------------------------------------------------
    # Decision isolation
    # ------------------------------------------------------------------------

    forbidden_fields = (

        "buy",

        "sell",

        "signal",

        "decision",

        "long",

        "short",
    )

    record_fields = {

        field.lower()

        for field
        in FeatureRecord.__dataclass_fields__
    }

    for forbidden in forbidden_fields:

        assert forbidden not in record_fields

    return True


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    print(
        "=" * 110
    )

    print(
        "ARUNDA TRADER — DEV-06 — STEP 13"
    )

    print(
        "FEATURE ENGINE v0.1"
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
            "ENGINE            : FEATURE_ENGINE_v0.1"
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
            "STATUS            : READY FOR STEP 13A CONTRACT AUDIT"
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