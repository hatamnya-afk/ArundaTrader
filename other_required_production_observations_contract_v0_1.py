"""CP39 other required production observations source contract.

Provider-neutral, read-only validation boundary for production-bound
liquidity and execution adjustment observations. No inference, API, DB,
execution, order, or pipeline coupling.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED"}


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    return number


def validate_production_observations(
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate explicit production-bound liquidity/execution observations."""
    if not isinstance(observation, Mapping):
        raise ValueError("OBSERVATION_INPUT_INVALID")

    if observation.get("observation_state") != "AVAILABLE":
        raise ValueError("OBSERVATION_STATE_INVALID")
    if observation.get("observation_validation") != "VALID":
        raise ValueError("OBSERVATION_VALIDATION_INVALID")

    observation_source = _text(observation.get("observation_source"))
    if observation_source is None or observation_source in _FORBIDDEN_SOURCES:
        raise ValueError("OBSERVATION_SOURCE_INVALID")

    provenance = _text(observation.get("provenance"))
    asset = _text(observation.get("asset"))
    observed_at = _text(observation.get("observed_at"))
    if any(value is None for value in (provenance, asset, observed_at)):
        raise ValueError("OBSERVATION_METADATA_INVALID")

    if observation.get("liquidity_validation") != "VALID":
        raise ValueError("LIQUIDITY_VALIDATION_INVALID")
    liquidity_source = _text(observation.get("liquidity_source"))
    if liquidity_source is None:
        raise ValueError("LIQUIDITY_SOURCE_INVALID")

    liquidity_score = _finite_number(observation.get("liquidity_score"))
    if liquidity_score is None or not 0 < liquidity_score <= 1:
        raise ValueError("LIQUIDITY_SCORE_INVALID")

    if observation.get("execution_validation") != "VALID":
        raise ValueError("EXECUTION_VALIDATION_INVALID")
    execution_source = _text(observation.get("execution_source"))
    if execution_source is None:
        raise ValueError("EXECUTION_SOURCE_INVALID")

    execution_adjustment = _finite_number(observation.get("execution_adjustment"))
    if execution_adjustment is None or execution_adjustment <= 0:
        raise ValueError("EXECUTION_ADJUSTMENT_INVALID")

    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": observation_source,
        "provenance": provenance,
        "asset": asset,
        "liquidity_validation": "VALID",
        "liquidity_source": liquidity_source,
        "liquidity_score": liquidity_score,
        "execution_validation": "VALID",
        "execution_source": execution_source,
        "execution_adjustment": execution_adjustment,
        "observed_at": observed_at,
    }


__all__ = ["validate_production_observations"]
