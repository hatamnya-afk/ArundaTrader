"""
ARUNDA DYNAMIC SIGNAL SEMANTIC LAYER v0.1

Purpose:
    Convert existing production feature semantics into the
    existing five-field Signal Logic contract.

Boundary:
    ProductionSignalInput / existing feature data
        -> Dynamic Semantic Structure
        -> existing signal_logic.build_direction()

Rules:
    - No database access.
    - No synthetic data.
    - No interpolation/fill/backfill/padding/blending.
    - No new signal logic.
    - No new thresholds except proven legacy position mapping.
    - Fail closed on invalid/missing semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional
import math


VALID_TRENDS = {"UP", "DOWN", "FLAT"}
VALID_MOMENTUM = {"STRONG", "WEAK"}
VALID_POSITION = {"UPPER", "MIDDLE", "LOWER"}
VALID_VOLATILITY = {"LOW", "MEDIUM", "HIGH"}


@dataclass(frozen=True)
class DynamicSemanticStructure:
    """Public five-field semantic contract consumed by Signal Logic."""

    trend: Optional[str]
    momentum: Optional[str]
    acceleration: Optional[float]
    position: Optional[str]
    volatility: Optional[str]


def _get(source: Any, name: str, default: Any = None) -> Any:
    """Read a field from either a mapping or an object."""
    if source is None:
        return default

    if isinstance(source, Mapping):
        return source.get(name, default)

    return getattr(source, name, default)


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    try:
        text = str(value).strip().upper()
    except Exception:
        return None

    return text or None


def normalize_trend(value: Any) -> Optional[str]:
    """
    Existing trend semantics:
        BULLISH -> UP
        BEARISH -> DOWN
        NEUTRAL -> FLAT
    """
    value = _normalize_text(value)

    mapping = {
        "BULLISH": "UP",
        "BEARISH": "DOWN",
        "NEUTRAL": "FLAT",
        "UP": "UP",
        "DOWN": "DOWN",
        "FLAT": "FLAT",
    }

    result = mapping.get(value)

    return result if result in VALID_TRENDS else None


def normalize_momentum(value: Any) -> Optional[str]:
    """
    Existing momentum semantics:
        STRONG / VERY_STRONG -> STRONG
        WEAK / MODERATE / MEDIUM -> WEAK
    """
    value = _normalize_text(value)

    mapping = {
        "STRONG": "STRONG",
        "VERY_STRONG": "STRONG",
        "WEAK": "WEAK",
        "MODERATE": "WEAK",
        "MEDIUM": "WEAK",
    }

    result = mapping.get(value)

    return result if result in VALID_MOMENTUM else None


def normalize_acceleration(value: Any) -> Optional[float]:
    """
    Acceleration is passed through as a genuine numeric value.
    No classification or threshold is applied.
    """
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    try:
        value = float(value)
    except Exception:
        return None

    if not math.isfinite(value):
        return None

    return value


def classify_position_legacy(position_20: Any) -> Optional[str]:
    """
    Proven legacy position_20 semantic mapping.

        >= 0.66 -> UPPER
        <= 0.33 -> LOWER
        otherwise -> MIDDLE

    No new threshold is introduced here.
    """
    if isinstance(position_20, bool):
        return None

    if not isinstance(position_20, (int, float)):
        return None

    try:
        position_20 = float(position_20)
    except Exception:
        return None

    if not math.isfinite(position_20):
        return None

    if position_20 >= 0.66:
        return "UPPER"

    if position_20 <= 0.33:
        return "LOWER"

    return "MIDDLE"


def normalize_volatility(value: Any) -> Optional[str]:
    """
    FeatureRecord.volatility_regime is already an existing semantic.
    It is bound directly; invalid values fail closed.
    """
    value = _normalize_text(value)

    return value if value in VALID_VOLATILITY else None


def _extract_position_20(source: Any) -> Any:
    """
    Extract the existing numeric position_20 without interpreting
    unrelated fields or inventing fallbacks.
    """
    value = _get(source, "position_20", None)

    if value is not None:
        return value

    feature_record = _get(source, "feature_record", None)

    return _get(feature_record, "position_20", None)


def build_public_structure(
    source: Any,
) -> DynamicSemanticStructure:
    """
    Build the public five-field semantic structure from existing data.
    """
    feature_record = _get(source, "feature_record", None)

    trend_source = _get(source, "trend", None)
    if trend_source is None:
        trend_source = _get(source, "structure_direction", None)

    momentum_source = _get(source, "momentum", None)
    if momentum_source is None:
        momentum_source = _get(source, "structure_strength", None)

    acceleration_source = _get(source, "acceleration", None)
    if acceleration_source is None:
        acceleration_source = _get(feature_record, "acceleration", None)

    volatility_source = _get(source, "volatility_regime", None)
    if volatility_source is None:
        volatility_source = _get(source, "volatility", None)

    if volatility_source is None:
        volatility_source = _get(
            feature_record,
            "volatility_regime",
            None,
        )

    position_20 = _extract_position_20(source)

    return DynamicSemanticStructure(
        trend=normalize_trend(trend_source),
        momentum=normalize_momentum(momentum_source),
        acceleration=normalize_acceleration(acceleration_source),
        position=classify_position_legacy(position_20),
        volatility=normalize_volatility(volatility_source),
    )


def validate_public_structure(
    structure: DynamicSemanticStructure,
) -> bool:
    """Strict fail-closed validation of the public semantic contract."""

    if structure.trend is not None:
        if structure.trend not in VALID_TRENDS:
            return False

    if structure.momentum is not None:
        if structure.momentum not in VALID_MOMENTUM:
            return False

    if structure.acceleration is not None:
        if not isinstance(structure.acceleration, (int, float)):
            return False

        if not math.isfinite(float(structure.acceleration)):
            return False

    if structure.position is not None:
        if structure.position not in VALID_POSITION:
            return False

    if structure.volatility is not None:
        if structure.volatility not in VALID_VOLATILITY:
            return False

    return True


def production_input_to_semantics(
    production_input: Any,
) -> DynamicSemanticStructure:
    """
    Adapter entry point.

    Reads ProductionSignalInput and its genuine FeatureRecord.
    Does not mutate the input object.
    """
    structure = build_public_structure(production_input)

    if not validate_public_structure(structure):
        return DynamicSemanticStructure(
            trend=None,
            momentum=None,
            acceleration=None,
            position=None,
            volatility=None,
        )

    return structure


def build_dynamic_signal(
    production_input: Any,
) -> Any:
    """
    Pass the validated semantic structure to the authoritative
    existing signal_logic.build_direction().

    This function does not reimplement signal logic.
    """
    structure = production_input_to_semantics(production_input)

    from signal_logic import build_direction

    return build_direction(
        {
            "trend": structure.trend,
            "momentum": structure.momentum,
            "acceleration": structure.acceleration,
            "position": structure.position,
            "volatility": structure.volatility,
        }
    )


__all__ = [
    "DynamicSemanticStructure",
    "build_public_structure",
    "build_dynamic_signal",
    "production_input_to_semantics",
    "validate_public_structure",
    "normalize_trend",
    "normalize_momentum",
    "normalize_acceleration",
    "classify_position_legacy",
    "normalize_volatility",
]

