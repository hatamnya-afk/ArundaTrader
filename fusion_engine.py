"""
ARUNDA FUSION ENGINE v0.6
Production Multi-Arm Fusion

ARCHITECTURE:

    MARKET ARM
        +
    NEWS ARM
        +
    SOCIAL ARM
        ↓
    INTELLIGENCE INPUT
        ↓
    FUSION v0.6
        ↓
    FUSED SIGNAL OUTPUT

HARD RULES:
- REAL DATA ONLY
- NO SYNTHETIC DATA
- NO INTERPOLATION
- NO FILL / BACKFILL / PADDING
- NO LEGACY market_technical
- NO CMC snapshot input
- NO Coinalyze dependency
- NO arunda.db access
- NO DB writes
- NO execution
- NO order intents

IMPORTANT:
- Technical / Market Score is INPUT.
- News Score is INPUT.
- Social Score is INPUT.
- Fused Score is OUTPUT ONLY.
- Fused Score must NEVER become Market input.
"""

from __future__ import annotations

import importlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# =====================================================================
# ENGINE IDENTITY
# =====================================================================

ENGINE_VERSION = "FUSION_v0.6"
CONTRACT_VERSION = "INFORMATION_CONTRACT_v0.1"

TIMEFRAME = "1h"

ASSETS = [
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

EXPECTED_ASSET_COUNT = len(ASSETS)

BASE_WEIGHTS = {
    "market": 0.50,
    "news": 0.25,
    "social": 0.25,
}

DIRECTION_THRESHOLD = 25.0
STRONG_THRESHOLD = 60.0


# =====================================================================
# UTILITY
# =====================================================================

def clamp(
    value: float,
    low: float = -100.0,
    high: float = 100.0,
) -> float:

    return max(
        low,
        min(high, float(value)),
    )


def safe_float(
    value: Any,
) -> Optional[float]:

    try:

        if value is None:
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (TypeError, ValueError):

        return None


def utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


# =====================================================================
# SENTIMENT NORMALIZATION
# =====================================================================

def normalize_sentiment(
    sentiment: Any,
) -> Optional[float]:
    """
    Information Contract sentiment
    → Fusion directional space.

    BULLISH  = +100
    NEUTRAL  = 0
    BEARISH  = -100
    UNKNOWN  = unavailable
    """

    if sentiment is None:
        return None

    value = str(
        sentiment
    ).strip().upper()

    if value == "BULLISH":
        return 100.0

    if value == "BEARISH":
        return -100.0

    if value == "NEUTRAL":
        return 0.0

    return None


# =====================================================================
# MARKET / TECHNICAL SCORE NORMALIZATION
# =====================================================================

def normalize_market_signal(
    signal: Optional[Dict[str, Any]],
) -> Optional[float]:
    """
    Normalize REAL Market / Technical evidence.

    Accepted native score fields:

        score
        signal_score
        directional_score

    IMPORTANT:
        fused_score is deliberately NOT accepted.

    This prevents circular architecture:

        Technical → Fusion → Fused

    and forbids:

        Fused → Market → Fusion
    """

    if not isinstance(
        signal,
        dict,
    ):
        return None

    # -------------------------------------------------------------
    # Native technical score
    # -------------------------------------------------------------

    numeric_candidates = [
        "score",
        "signal_score",
        "directional_score",
    ]

    for field in numeric_candidates:

        value = safe_float(
            signal.get(field)
        )

        if value is not None:
            return clamp(value)

    # -------------------------------------------------------------
    # Directional fallback
    # -------------------------------------------------------------

    direction = str(
        signal.get(
            "direction",
            "",
        )
    ).strip().upper()

    confidence = safe_float(
        signal.get(
            "confidence"
        )
    )

    if direction == "LONG":

        if confidence is None:
            return 100.0

        return clamp(
            confidence * 100.0
        )

    if direction == "SHORT":

        if confidence is None:
            return -100.0

        return clamp(
            -confidence * 100.0
        )

    if direction in (
        "NONE",
        "FLAT",
        "NEUTRAL",
    ):

        return 0.0

    return None


# =====================================================================
# INFORMATION ITEM SCORE
# =====================================================================

def information_item_score(
    item: Dict[str, Any],
) -> Optional[float]:
    """
    Convert one validated News/Social item
    into directional Fusion space.

    score =
        sentiment
        × relevance
        × confidence
        × freshness
    """

    sentiment_score = normalize_sentiment(
        item.get("sentiment")
    )

    if sentiment_score is None:
        return None

    relevance = safe_float(
        item.get("relevance")
    )

    confidence = safe_float(
        item.get("confidence")
    )

    freshness = safe_float(
        item.get("freshness")
    )

    if relevance is None:
        relevance = 1.0

    if confidence is None:
        confidence = 1.0

    if freshness is None:
        freshness = 1.0

    relevance = max(
        0.0,
        min(1.0, relevance),
    )

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    freshness = max(
        0.0,
        min(1.0, freshness),
    )

    strength = (
        relevance
        * confidence
        * freshness
    )

    return clamp(
        sentiment_score * strength
    )


# =====================================================================
# INFORMATION AGGREGATION
# =====================================================================

def aggregate_information(
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:

    scores: List[float] = []
    confidences: List[float] = []

    valid_items = 0

    for item in items:

        score = information_item_score(
            item
        )

        if score is None:
            continue

        scores.append(score)

        confidence = safe_float(
            item.get("confidence")
        )

        if confidence is not None:

            confidences.append(
                max(
                    0.0,
                    min(1.0, confidence),
                )
            )

        valid_items += 1

    if not scores:

        return {
            "available": False,
            "score": None,
            "confidence": 0.0,
            "count": 0,
        }

    score = sum(scores) / len(scores)

    if confidences:

        confidence = (
            sum(confidences)
            / len(confidences)
        )

    else:

        confidence = 0.0

    return {
        "available": True,
        "score": clamp(score),
        "confidence": max(
            0.0,
            min(1.0, confidence),
        ),
        "count": valid_items,
    }


# =====================================================================
# ARM AVAILABILITY
# =====================================================================

def calculate_available_weight(
    market_available: bool,
    news_available: bool,
    social_available: bool,
) -> float:

    total = 0.0

    if market_available:
        total += BASE_WEIGHTS["market"]

    if news_available:
        total += BASE_WEIGHTS["news"]

    if social_available:
        total += BASE_WEIGHTS["social"]

    return total


def calculate_dynamic_weights(
    market_available: bool,
    news_available: bool,
    social_available: bool,
    news_confidence: float,
    social_confidence: float,
) -> Dict[str, float]:

    weights = dict(
        BASE_WEIGHTS
    )

    # -------------------------------------------------------------
    # Market
    # -------------------------------------------------------------

    if not market_available:

        weights["market"] = 0.0

    # -------------------------------------------------------------
    # News
    # -------------------------------------------------------------

    if not news_available:

        weights["news"] = 0.0

    else:

        weights["news"] *= max(
            0.25,
            news_confidence,
        )

    # -------------------------------------------------------------
    # Social
    # -------------------------------------------------------------

    if not social_available:

        weights["social"] = 0.0

    else:

        weights["social"] *= max(
            0.25,
            social_confidence,
        )

    total = sum(
        weights.values()
    )

    if total <= 0.0:

        return {
            "market": 0.0,
            "news": 0.0,
            "social": 0.0,
        }

    return {
        key: value / total
        for key, value in weights.items()
    }


# =====================================================================
# AGREEMENT
# =====================================================================

def calculate_agreement(
    values: List[Optional[float]],
) -> float:

    clean = [
        float(value)
        for value in values
        if value is not None
    ]

    if not clean:
        return 0.0

    if len(clean) == 1:
        return 1.0

    directions = []

    for value in clean:

        if value > 10.0:

            directions.append(1)

        elif value < -10.0:

            directions.append(-1)

        else:

            directions.append(0)

    non_neutral = [
        value
        for value in directions
        if value != 0
    ]

    if not non_neutral:
        return 1.0

    positive = non_neutral.count(1)
    negative = non_neutral.count(-1)

    return (
        max(
            positive,
            negative,
        )
        / len(non_neutral)
    )


# =====================================================================
# MISSING ARM PENALTY
# =====================================================================

def calculate_missing_penalty(
    market_available: bool,
    news_available: bool,
    social_available: bool,
) -> float:

    available = sum(
        [
            market_available,
            news_available,
            social_available,
        ]
    )

    if available == 3:
        return 1.0

    if available == 2:
        return 0.82

    if available == 1:
        return 0.65

    return 0.0


# =====================================================================
# FUSED SCORE
# =====================================================================

def calculate_fused_score(
    market_score: Optional[float],
    news_score: Optional[float],
    social_score: Optional[float],
    weights: Dict[str, float],
    missing_penalty: float,
) -> float:
    """
    THE ONLY FUNCTION THAT CREATES FUSED SCORE.

    Fused Score is an output.
    It is never reused as Market input.
    """

    score = 0.0

    if market_score is not None:

        score += (
            weights["market"]
            * market_score
        )

    if news_score is not None:

        score += (
            weights["news"]
            * news_score
        )

    if social_score is not None:

        score += (
            weights["social"]
            * social_score
        )

    return clamp(
        score * missing_penalty
    )


# =====================================================================
# CONFIDENCE
# =====================================================================

def calculate_confidence(
    fused_score: float,
    agreement: float,
    available_weight: float,
    news_confidence: float,
    social_confidence: float,
    missing_penalty: float,
) -> float:

    strength = (
        abs(fused_score)
        / 100.0
    )

    information_confidence = (
        news_confidence
        + social_confidence
    ) / 2.0

    confidence = (
        0.40 * strength
        + 0.25 * agreement
        + 0.20 * available_weight
        + 0.15 * information_confidence
    )

    confidence *= missing_penalty

    return max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )


# =====================================================================
# CLASSIFICATION
# =====================================================================

def determine_regime(
    score: float,
) -> str:

    if score >= 60.0:
        return "STRONG_BULLISH"

    if score >= 25.0:
        return "BULLISH"

    if score <= -60.0:
        return "STRONG_BEARISH"

    if score <= -25.0:
        return "BEARISH"

    return "NEUTRAL"


def determine_direction(
    score: float,
) -> str:

    if score >= DIRECTION_THRESHOLD:
        return "LONG"

    if score <= -DIRECTION_THRESHOLD:
        return "SHORT"

    return "FLAT"


def determine_signal_strength(
    score: float,
    confidence: float,
) -> str:

    magnitude = abs(score)

    if (
        confidence >= 0.75
        and magnitude >= STRONG_THRESHOLD
    ):

        return "STRONG"

    if (
        confidence >= 0.55
        and magnitude >= 30.0
    ):

        return "MODERATE"

    return "WEAK"


# =====================================================================
# INFORMATION PROVENANCE
# =====================================================================

def validate_provenance(
    item: Dict[str, Any],
) -> bool:

    required = [
        "source",
        "source_id",
        "asset",
        "timestamp",
        "provenance",
    ]

    for field in required:

        value = item.get(field)

        if value is None:
            return False

        if str(value).strip() == "":
            return False

    return True


def validate_information_item(
    item: Dict[str, Any],
) -> bool:

    if not isinstance(
        item,
        dict,
    ):
        return False

    if not validate_provenance(
        item
    ):
        return False

    if item.get(
        "contract_version"
    ) != CONTRACT_VERSION:

        return False

    asset = str(
        item.get(
            "asset",
            "",
        )
    ).upper()

    if asset not in ASSETS:
        return False

    # UNKNOWN remains unavailable.
    # It must never become artificial neutral.
    if normalize_sentiment(
        item.get("sentiment")
    ) is None:

        return False

    return True


# =====================================================================
# EXTERNAL NEWS ARM
# =====================================================================

def load_news_arm() -> List[Dict[str, Any]]:
    """
    News ARM owns acquisition.
    Fusion only consumes its output.
    """

    module = importlib.import_module(
        "news_arm_v0_1"
    )

    run = getattr(
        module,
        "run",
        None,
    )

    if not callable(run):

        raise RuntimeError(
            "NEWS_ARM_RUN_NOT_AVAILABLE"
        )

    result = run()

    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "NEWS_ARM_INVALID_RUNTIME_OUTPUT"
        )

    items = result.get(
        "items",
        [],
    )

    if not isinstance(
        items,
        list,
    ):

        raise RuntimeError(
            "NEWS_ARM_ITEMS_INVALID"
        )

    valid = []

    for item in items:

        if validate_information_item(
            item
        ):

            valid.append(item)

    return valid


# =====================================================================
# EXTERNAL SOCIAL ARM
# =====================================================================

def load_social_arm() -> List[Dict[str, Any]]:
    """
    Social ARM owns acquisition.
    Fusion only consumes its output.
    """

    module = importlib.import_module(
        "social_arm_v0_1"
    )

    run = getattr(
        module,
        "run",
        None,
    )

    if not callable(run):

        raise RuntimeError(
            "SOCIAL_ARM_RUN_NOT_AVAILABLE"
        )

    result = run()

    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "SOCIAL_ARM_INVALID_RUNTIME_OUTPUT"
        )

    items = result.get(
        "items",
        [],
    )

    if not isinstance(
        items,
        list,
    ):

        raise RuntimeError(
            "SOCIAL_ARM_ITEMS_INVALID"
        )

    valid = []

    for item in items:

        if validate_information_item(
            item
        ):

            valid.append(item)

    return valid


# =====================================================================
# ASSET FILTER
# =====================================================================

def filter_asset(
    items: List[Dict[str, Any]],
    asset: str,
) -> List[Dict[str, Any]]:

    target = str(
        asset
    ).upper()

    return [
        item
        for item in items
        if str(
            item.get(
                "asset",
                "",
            )
        ).upper() == target
    ]


# =====================================================================
# MARKET SIGNAL VALIDATION
# =====================================================================

def validate_market_signal(
    asset: str,
    signal: Optional[Dict[str, Any]],
) -> bool:
    """
    Validate the production Market Signal object.

    Fusion does not access any database.
    """

    if not isinstance(
        signal,
        dict,
    ):

        return False

    signal_asset = str(
        signal.get(
            "asset",
            asset,
        )
    ).upper()

    if signal_asset != asset.upper():

        return False

    direction = str(
        signal.get(
            "direction",
            "",
        )
    ).upper()

    if direction not in (
        "LONG",
        "SHORT",
        "NONE",
        "FLAT",
        "NEUTRAL",
    ):

        return False

    # -------------------------------------------------------------
    # Explicit circular-input protection.
    # -------------------------------------------------------------

    fused_only = (
        "fused_score" in signal
        and not any(
            field in signal
            for field in (
                "score",
                "signal_score",
                "directional_score",
            )
        )
    )

    if fused_only:

        return False

    return True


# =====================================================================
# SINGLE-ASSET FUSION
# =====================================================================

def fuse_asset(
    asset: str,
    market_signal: Optional[Dict[str, Any]],
    news_items: List[Dict[str, Any]],
    social_items: List[Dict[str, Any]],
) -> Dict[str, Any]:

    # -----------------------------------------------------------------
    # MARKET / TECHNICAL ARM
    # -----------------------------------------------------------------

    market_valid = validate_market_signal(
        asset,
        market_signal,
    )

    if market_valid:

        market_score = normalize_market_signal(
            market_signal
        )

    else:

        market_score = None

    market_available = (
        market_score is not None
    )

    # -----------------------------------------------------------------
    # NEWS ARM
    # -----------------------------------------------------------------

    news = aggregate_information(
        news_items
    )

    news_available = bool(
        news["available"]
    )

    news_score = news["score"]

    news_confidence = (
        news["confidence"]
    )

    # -----------------------------------------------------------------
    # SOCIAL ARM
    # -----------------------------------------------------------------

    social = aggregate_information(
        social_items
    )

    social_available = bool(
        social["available"]
    )

    social_score = social["score"]

    social_confidence = (
        social["confidence"]
    )

    # -----------------------------------------------------------------
    # NO INFORMATION AVAILABLE
    # -----------------------------------------------------------------

    if not any(
        [
            market_available,
            news_available,
            social_available,
        ]
    ):

        return {
            "engine_version": ENGINE_VERSION,
            "contract_version": CONTRACT_VERSION,
            "asset": asset,
            "timestamp": utc_now(),

            "market": {
                "available": False,
                "score": None,
            },

            "news": {
                "available": False,
                "score": None,
                "confidence": 0.0,
                "count": 0,
            },

            "social": {
                "available": False,
                "score": None,
                "confidence": 0.0,
                "count": 0,
            },

            "weights": {
                "market": 0.0,
                "news": 0.0,
                "social": 0.0,
            },

            "available_weight": 0.0,
            "agreement": 0.0,
            "missing_arm_penalty": 0.0,

            "fused_score": None,
            "confidence": 0.0,
            "regime": "UNAVAILABLE",
            "direction": "NONE",
            "signal_strength": "NONE",

            "data_quality": "UNAVAILABLE",
            "provenance_valid": False,

            "db_writes": 0,
            "execution": "OFF",
            "order_intents": 0,
        }

    # -----------------------------------------------------------------
    # DYNAMIC WEIGHTS
    # -----------------------------------------------------------------

    weights = calculate_dynamic_weights(
        market_available,
        news_available,
        social_available,
        news_confidence,
        social_confidence,
    )

    available_weight = (
        calculate_available_weight(
            market_available,
            news_available,
            social_available,
        )
    )

    # -----------------------------------------------------------------
    # AGREEMENT
    # -----------------------------------------------------------------

    agreement = calculate_agreement(
        [
            market_score,
            news_score,
            social_score,
        ]
    )

    # -----------------------------------------------------------------
    # MISSING ARM PENALTY
    # -----------------------------------------------------------------

    missing_penalty = (
        calculate_missing_penalty(
            market_available,
            news_available,
            social_available,
        )
    )

    # -----------------------------------------------------------------
    # FUSED SCORE
    # -----------------------------------------------------------------

    fused_score = calculate_fused_score(
        market_score,
        news_score,
        social_score,
        weights,
        missing_penalty,
    )

    # -----------------------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------------------

    confidence = calculate_confidence(
        fused_score,
        agreement,
        available_weight,
        news_confidence,
        social_confidence,
        missing_penalty,
    )

    # -----------------------------------------------------------------
    # CLASSIFICATION
    # -----------------------------------------------------------------

    regime = determine_regime(
        fused_score
    )

    direction = determine_direction(
        fused_score
    )

    signal_strength = (
        determine_signal_strength(
            fused_score,
            confidence,
        )
    )

    # -----------------------------------------------------------------
    # DATA QUALITY
    # -----------------------------------------------------------------

    if (
        market_available
        and news_available
        and social_available
    ):

        data_quality = "VERIFIED"

    else:

        data_quality = "PARTIAL"

    # -----------------------------------------------------------------
    # PROVENANCE
    # -----------------------------------------------------------------

    provenance_valid = True

    if market_signal is not None:

        if not market_valid:

            provenance_valid = False

    for item in (
        news_items
        + social_items
    ):

        if not validate_information_item(
            item
        ):

            provenance_valid = False
            break

    # -----------------------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------------------

    return {
        "engine_version": ENGINE_VERSION,
        "contract_version": CONTRACT_VERSION,
        "asset": asset,
        "timestamp": utc_now(),

        "market": {
            "available": market_available,
            "score": market_score,
        },

        "news": {
            "available": news_available,
            "score": news_score,
            "confidence": news_confidence,
            "count": news["count"],
        },

        "social": {
            "available": social_available,
            "score": social_score,
            "confidence": social_confidence,
            "count": social["count"],
        },

        "weights": {
            "market": weights["market"],
            "news": weights["news"],
            "social": weights["social"],
        },

        "available_weight": available_weight,
        "agreement": agreement,
        "missing_arm_penalty": missing_penalty,

        "fused_score": fused_score,
        "confidence": confidence,
        "regime": regime,
        "direction": direction,
        "signal_strength": signal_strength,

        "data_quality": data_quality,
        "provenance_valid": provenance_valid,

        "db_writes": 0,
        "execution": "OFF",
        "order_intents": 0,
    }


# =====================================================================
# PRODUCTION FUSION RUNTIME
# =====================================================================

def run(
    market_signals: Dict[str, Dict[str, Any]],
    news_items: Optional[List[Dict[str, Any]]] = None,
    social_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Production memory-only Fusion.

    Inputs:

        market_signals
            REAL Production Signal Engine output.

        news_items
            REAL validated News ARM output.

        social_items
            REAL validated Social ARM output.

    Output:

        Fused Score per asset.

    Fused Score is never used as input.
    """

    if not isinstance(
        market_signals,
        dict,
    ):

        raise RuntimeError(
            "MARKET_SIGNALS_INVALID"
        )

    if news_items is None:
        news_items = []

    if social_items is None:
        social_items = []

    if not isinstance(
        news_items,
        list,
    ):

        raise RuntimeError(
            "NEWS_ITEMS_INVALID"
        )

    if not isinstance(
        social_items,
        list,
    ):

        raise RuntimeError(
            "SOCIAL_ITEMS_INVALID"
        )

    # -----------------------------------------------------------------
    # HARD MARKET COMPLETENESS CONTRACT
    # -----------------------------------------------------------------

    missing_market_assets = [
        asset
        for asset in ASSETS
        if asset not in market_signals
    ]

    if missing_market_assets:

        raise RuntimeError(
            "PRODUCTION_MARKET_BINDING_INCOMPLETE:"
            + ",".join(
                missing_market_assets
            )
        )

    if len(market_signals) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "PRODUCTION_MARKET_SIGNAL_COUNT_INVALID:"
            f"{len(market_signals)}"
        )

    # -----------------------------------------------------------------
    # Validate every Market Signal before Fusion.
    # -----------------------------------------------------------------

    for asset in ASSETS:

        signal = market_signals.get(
            asset
        )

        if not isinstance(
            signal,
            dict,
        ):

            raise RuntimeError(
                f"PRODUCTION_MARKET_SIGNAL_INVALID:{asset}"
            )

        if not validate_market_signal(
            asset,
            signal,
        ):

            raise RuntimeError(
                f"PRODUCTION_MARKET_SIGNAL_NOT_VALID:{asset}"
            )

        # -------------------------------------------------------------
        # Circular fused-score protection.
        # -------------------------------------------------------------

        native_score_present = any(
            field in signal
            for field in (
                "score",
                "signal_score",
                "directional_score",
            )
        )

        fused_score_only = (
            "fused_score" in signal
            and not native_score_present
            and "direction" not in signal
        )

        if fused_score_only:

            raise RuntimeError(
                f"CIRCULAR_FUSED_SCORE_MARKET_INPUT:{asset}"
            )

    # -----------------------------------------------------------------
    # Validate News
    # -----------------------------------------------------------------

    valid_news = []

    for item in news_items:

        if validate_information_item(
            item
        ):

            valid_news.append(item)

    # -----------------------------------------------------------------
    # Validate Social
    # -----------------------------------------------------------------

    valid_social = []

    for item in social_items:

        if validate_information_item(
            item
        ):

            valid_social.append(item)

    # -----------------------------------------------------------------
    # Fuse all production assets
    # -----------------------------------------------------------------

    results = []

    for asset in ASSETS:

        market_signal = (
            market_signals.get(
                asset
            )
        )

        asset_news = filter_asset(
            valid_news,
            asset,
        )

        asset_social = filter_asset(
            valid_social,
            asset,
        )

        result = fuse_asset(
            asset,
            market_signal,
            asset_news,
            asset_social,
        )

        results.append(
            result
        )

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------

    available = [
        result
        for result in results
        if result["fused_score"] is not None
    ]

    validated = [
        result
        for result in results
        if result["provenance_valid"]
    ]

    return {
        "engine_version": ENGINE_VERSION,
        "contract_version": CONTRACT_VERSION,
        "timestamp": utc_now(),

        "results": results,

        "summary": {
            "assets": len(results),
            "available": len(available),
            "validated": len(validated),
            "news_items": len(valid_news),
            "social_items": len(valid_social),
        },

        "production_only": True,
        "legacy_used": False,

        "synthetic_data": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,

        "db_writes": 0,
        "execution": "OFF",
        "order_intents": 0,
    }


# =====================================================================
# PRODUCTION MARKET SIGNAL LOADER
# =====================================================================

def load_production_market_signals() -> Dict[str, Dict[str, Any]]:
    """
    Load REAL production Market Signals from the
    authoritative Production Signal Engine Binding.

    HARD RULES:
    - No direct production DB access here.
    - No legacy market_technical.
    - No synthetic data.
    - No interpolation.
    - No fill.
    - No backfill.
    - No padding.
    - No blending.
    - No reconstruction of Signal Engine.
    - No fused_score as Market input.
    - KuCoin source_id must START WITH "KUCOIN".
    - Exact timeframe must be 1h.
    - Production Binding remains authoritative.
    - Market output must be fully validated.
    """

    # -----------------------------------------------------------------
    # AUTHORITATIVE BINDING
    # -----------------------------------------------------------------

    binding = importlib.import_module(
        "production_signal_engine_binding_v0_2"
    )

    load_fabric_rows = getattr(
        binding,
        "load_fabric_rows",
        None,
    )

    group_markets = getattr(
        binding,
        "group_markets",
        None,
    )

    process_market = getattr(
        binding,
        "process_market",
        None,
    )

    if not callable(
        load_fabric_rows
    ):

        raise RuntimeError(
            "PRODUCTION_BINDING_LOAD_FABRIC_ROWS_NOT_AVAILABLE"
        )

    if not callable(
        group_markets
    ):

        raise RuntimeError(
            "PRODUCTION_BINDING_GROUP_MARKETS_NOT_AVAILABLE"
        )

    if not callable(
        process_market
    ):

        raise RuntimeError(
            "PRODUCTION_BINDING_PROCESS_MARKET_NOT_AVAILABLE"
        )

    # -----------------------------------------------------------------
    # LOAD REAL FABRIC ROWS
    # -----------------------------------------------------------------

    rows = load_fabric_rows()

    if not isinstance(
        rows,
        list,
    ):

        raise RuntimeError(
            "PRODUCTION_FABRIC_ROWS_INVALID"
        )

    # -----------------------------------------------------------------
    # AUTHORITATIVE GROUPING
    # -----------------------------------------------------------------

    groups = group_markets(
        rows
    )

    if not isinstance(
        groups,
        dict,
    ):

        raise RuntimeError(
            "PRODUCTION_MARKET_GROUPS_INVALID"
        )

    market_signals: Dict[
        str,
        Dict[str, Any]
    ] = {}

    # -----------------------------------------------------------------
    # EXACT PRODUCTION ASSET UNIVERSE
    # -----------------------------------------------------------------

    for asset in ASSETS:

        candidates = []

        # -------------------------------------------------------------
        # FIND VALID KUCOIN PRODUCTION CONTEXTS
        # -------------------------------------------------------------

        for key, market_rows in groups.items():

            if not isinstance(
                key,
                tuple,
            ):

                continue

            if len(key) < 4:

                continue

            key_asset = str(
                key[0]
            ).upper()

            source_id = str(
                key[2]
            ).upper()

            timeframe = str(
                key[3]
            ).upper()

            # ---------------------------------------------------------
            # Exact asset
            # ---------------------------------------------------------

            if key_asset != asset:

                continue

            # ---------------------------------------------------------
            # IMPORTANT FIX
            #
            # The authoritative Binding uses:
            #
            #     source_id.startswith("KUCOIN")
            #
            # NOT:
            #
            #     source_id == "KUCOIN"
            #
            # Therefore valid production identifiers such as:
            #
            #     KUCOIN_SPOT
            #     KUCOIN_API
            #     KUCOIN_CEX
            #
            # are accepted.
            # ---------------------------------------------------------

            if not source_id.startswith(
                "KUCOIN"
            ):

                continue

            # ---------------------------------------------------------
            # Exact timeframe
            # ---------------------------------------------------------

            if timeframe != TIMEFRAME.upper():

                continue

            # ---------------------------------------------------------
            # Valid row container
            # ---------------------------------------------------------

            if not isinstance(
                market_rows,
                list,
            ):

                continue

            if not market_rows:

                continue

            candidates.append(
                (
                    key,
                    market_rows,
                )
            )

        # -------------------------------------------------------------
        # No valid Market context
        # -------------------------------------------------------------

        if not candidates:

            continue

        # -------------------------------------------------------------
        # Select longest REAL contiguous candidate.
        #
        # Continuity itself remains authoritative inside
        # process_market().
        # -------------------------------------------------------------

        selected_key, selected_rows = max(
            candidates,
            key=lambda item: len(
                item[1]
            ),
        )

        _ = selected_key

        if not selected_rows:

            continue

        # -------------------------------------------------------------
        # AUTHORITATIVE MARKET PROCESSING
        # -------------------------------------------------------------

        result = process_market(
            asset,
            selected_rows,
        )

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                f"PRODUCTION_MARKET_RESULT_INVALID:{asset}"
            )

        # -------------------------------------------------------------
        # Extract signal
        # -------------------------------------------------------------

        signal = result.get(
            "signal"
        )

        if signal is None:

            continue

        if not isinstance(
            signal,
            dict,
        ):

            raise RuntimeError(
                f"PRODUCTION_MARKET_SIGNAL_INVALID:{asset}"
            )

        # -------------------------------------------------------------
        # Asset identity
        # -------------------------------------------------------------

        signal_asset = str(
            signal.get(
                "asset",
                asset,
            )
        ).upper()

        if signal_asset != asset:

            raise RuntimeError(
                f"PRODUCTION_MARKET_ASSET_MISMATCH:"
                f"{asset}:{signal_asset}"
            )

        # -------------------------------------------------------------
        # Circular fused-score protection
        # -------------------------------------------------------------

        native_score_present = any(
            field in signal
            for field in (
                "score",
                "signal_score",
                "directional_score",
            )
        )

        fused_score_only = (
            "fused_score" in signal
            and not native_score_present
            and "direction" not in signal
        )

        if fused_score_only:

            raise RuntimeError(
                f"CIRCULAR_FUSED_SCORE_MARKET_INPUT:{asset}"
            )

        # -------------------------------------------------------------
        # Binding validation
        # -------------------------------------------------------------

        if result.get(
            "valid"
        ) is not True:

            raise RuntimeError(
                f"PRODUCTION_MARKET_SIGNAL_NOT_VALID:"
                f"{asset}:"
                f"{result.get('validation')}"
            )

        # -------------------------------------------------------------
        # Provenance validation
        # -------------------------------------------------------------

        if result.get(
            "provenance_valid"
        ) is not True:

            raise RuntimeError(
                f"PRODUCTION_MARKET_PROVENANCE_INVALID:"
                f"{asset}"
            )

        # -------------------------------------------------------------
        # Continuity validation
        # -------------------------------------------------------------

        if result.get(
            "continuity_valid"
        ) is not True:

            raise RuntimeError(
                f"PRODUCTION_MARKET_CONTINUITY_INVALID:"
                f"{asset}"
            )

        # -------------------------------------------------------------
        # Input readiness
        # -------------------------------------------------------------

        if result.get(
            "input_ready"
        ) is not True:

            raise RuntimeError(
                f"PRODUCTION_MARKET_INPUT_NOT_READY:"
                f"{asset}"
            )

        # -------------------------------------------------------------
        # Store validated REAL Market Signal
        # -------------------------------------------------------------

        market_signals[asset] = {
            **signal,
            "asset": asset,
        }

    # -----------------------------------------------------------------
    # HARD COMPLETENESS CONTRACT
    #
    # Never silently create News/Social-only Fusion.
    # -----------------------------------------------------------------

    missing_assets = [
        asset
        for asset in ASSETS
        if asset not in market_signals
    ]

    if missing_assets:

        raise RuntimeError(
            "PRODUCTION_MARKET_BINDING_INCOMPLETE:"
            + ",".join(
                missing_assets
            )
        )

    # -----------------------------------------------------------------
    # EXACT COUNT CONTRACT
    # -----------------------------------------------------------------

    if len(
        market_signals
    ) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "PRODUCTION_MARKET_SIGNAL_COUNT_INVALID:"
            f"{len(market_signals)}"
        )

    return market_signals


# =====================================================================
# RUNTIME REPORT
# =====================================================================

def print_runtime_result(
    output: Dict[str, Any],
) -> None:

    print(
        "                    FUSION OUTPUT"
    )

    print(
        "=" * 110
    )

    for result in output["results"]:

        asset = result["asset"]

        market_value = (
            result["market"]["score"]
        )

        news_value = (
            result["news"]["score"]
        )

        social_value = (
            result["social"]["score"]
        )

        fused_value = (
            result["fused_score"]
        )

        market_text = (
            f"{market_value:.3f}"
            if market_value is not None
            else "N/A"
        )

        news_text = (
            f"{news_value:.3f}"
            if news_value is not None
            else "N/A"
        )

        social_text = (
            f"{social_value:.3f}"
            if social_value is not None
            else "N/A"
        )

        fused_text = (
            f"{fused_value:.3f}"
            if fused_value is not None
            else "N/A"
        )

        confidence = safe_float(
            result["confidence"]
        )

        if confidence is None:

            confidence = 0.0

        direction = str(
            result["direction"]
        )

        quality = str(
            result["data_quality"]
        )

        news_count = result[
            "news"
        ]["count"]

        social_count = result[
            "social"
        ]["count"]

        print(
            f"{asset:<6} | "
            f"MARKET={market_text:>8} | "
            f"NEWS={news_text:>8} | "
            f"SOCIAL={social_text:>8} | "
            f"FUSED={fused_text:>8} | "
            f"CONF={confidence:.3f} | "
            f"DIR={direction:<5} | "
            f"QUALITY={quality:<11} | "
            f"N={news_count:<3} | "
            f"S={social_count:<3}"
        )

    print(
        "=" * 110
    )

    summary = output[
        "summary"
    ]

    print(
        f"ASSETS               : "
        f"{summary['assets']}"
    )

    print(
        f"AVAILABLE            : "
        f"{summary['available']}"
    )

    print(
        f"VALIDATED            : "
        f"{summary['validated']}"
    )

    print(
        f"NEWS_ITEMS           : "
        f"{summary['news_items']}"
    )

    print(
        f"SOCIAL_ITEMS         : "
        f"{summary['social_items']}"
    )

    print(
        "PRODUCTION_ONLY      : TRUE"
    )

    print(
        "LEGACY_USED          : FALSE"
    )

    print(
        "SYNTHETIC_DATA       : FALSE"
    )

    print(
        "INTERPOLATION        : FALSE"
    )

    print(
        "FILL                 : FALSE"
    )

    print(
        "BACKFILL             : FALSE"
    )

    print(
        "PADDING              : FALSE"
    )

    print(
        "DATABASE_TOUCHED     : FALSE"
    )

    print(
        "DB_WRITES             : 0"
    )

    print(
        "ORDER_INTENTS        : 0"
    )

    print(
        "EXECUTION            : OFF"
    )

    print(
        "=" * 110
    )


# =====================================================================
# PRODUCTION RUNTIME
# =====================================================================

def main() -> None:

    print(
        "=" * 110
    )

    print(
        "                 ARUNDA FUSION ENGINE v0.6"
    )

    print(
        "=" * 110
    )

    print(
        f"ENGINE_VERSION       : "
        f"{ENGINE_VERSION}"
    )

    print(
        "ARCHITECTURE         : MARKET + NEWS + SOCIAL"
    )

    print(
        "MARKET INPUT         : REAL TECHNICAL SCORE"
    )

    print(
        "NEWS INPUT           : REAL NEWS ARM"
    )

    print(
        "SOCIAL INPUT         : REAL SOCIAL ARM"
    )

    print(
        "FUSED SCORE          : OUTPUT ONLY"
    )

    print(
        "MODE                 : PRODUCTION MEMORY-ONLY"
    )

    print(
        "DATABASE             : NOT TOUCHED"
    )

    print(
        "DB_WRITES            : 0"
    )

    print(
        "LEGACY               : FORBIDDEN"
    )

    print(
        "EXECUTION            : OFF"
    )

    print(
        "ORDER INTENTS        : 0"
    )

    print(
        "=" * 110
    )

    # -----------------------------------------------------------------
    # MARKET
    # -----------------------------------------------------------------

    print(
        "[1/3] REAL PRODUCTION MARKET SIGNALS"
    )

    market_signals = (
        load_production_market_signals()
    )

    print(
        f"MARKET_SIGNALS       : "
        f"{len(market_signals)}"
    )

    # -----------------------------------------------------------------
    # NEWS + SOCIAL
    # -----------------------------------------------------------------

    print(
        "[2/3] REAL NEWS + SOCIAL ARMS"
    )

    news_items = load_news_arm()

    social_items = load_social_arm()

    print(
        f"NEWS_ITEMS           : "
        f"{len(news_items)}"
    )

    print(
        f"SOCIAL_ITEMS         : "
        f"{len(social_items)}"
    )

    # -----------------------------------------------------------------
    # FUSION
    # -----------------------------------------------------------------

    print(
        "[3/3] FUSION"
    )

    output = run(
        market_signals=market_signals,
        news_items=news_items,
        social_items=social_items,
    )

    print_runtime_result(
        output
    )


# =====================================================================
# DIRECT EXECUTION
# =====================================================================

if __name__ == "__main__":
    main()