"""CP39 validated Stop + Risk Policy production source contract.

Provider-neutral, read-only validation boundary. No inference, API, DB,
execution, order, or pipeline coupling.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any


_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED"}


def _positive(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number <= 0:
        return None
    return number


def _nonnegative(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number < 0:
        return None
    return number


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def validate_stop_risk_policy_source(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return an explicit production-bound Stop/Risk observation."""
    if not isinstance(observation, Mapping):
        raise ValueError("PORTFOLIO_INPUT_INVALID")

    if observation.get("observation_validation") != "VALID":
        raise ValueError("OBSERVATION_VALIDATION_INVALID")
    if observation.get("observation_state") != "AVAILABLE":
        raise ValueError("OBSERVATION_STATE_INVALID")

    source = _text(observation.get("observation_source"))
    if source is None or source in _FORBIDDEN_SOURCES:
        raise ValueError("OBSERVATION_SOURCE_INVALID")

    provenance = _text(observation.get("provenance"))
    asset = _text(observation.get("asset"))
    observed_at = _text(observation.get("observed_at"))
    policy_version = _text(observation.get("risk_policy_version"))
    if any(value is None for value in (provenance, asset, observed_at, policy_version)):
        raise ValueError("REQUIRED_METADATA_INVALID")

    direction = observation.get("direction")
    if direction not in ("LONG", "SHORT"):
        raise ValueError("STOP_DIRECTION_INVALID")

    entry = _positive(observation.get("entry_price"))
    stop_price = _positive(observation.get("stop_price"))
    stop_distance = _positive(observation.get("stop_distance"))
    if entry is None or stop_price is None or stop_distance is None:
        raise ValueError("STOP_INPUT_INVALID")

    expected_distance = abs(entry - stop_price)
    if stop_distance != expected_distance:
        raise ValueError("STOP_DISTANCE_INVALID")
    if direction == "LONG" and stop_price >= entry:
        raise ValueError("STOP_DIRECTION_INVALID")
    if direction == "SHORT" and stop_price <= entry:
        raise ValueError("STOP_DIRECTION_INVALID")

    if observation.get("risk_policy_validation") != "VALID":
        raise ValueError("RISK_POLICY_VALIDATION_INVALID")

    risk_per_trade = _positive(observation.get("risk_per_trade"))
    max_portfolio_risk = _positive(observation.get("max_portfolio_risk"))
    if risk_per_trade is None or max_portfolio_risk is None:
        raise ValueError("RISK_POLICY_VALUE_INVALID")
    if max_portfolio_risk < risk_per_trade:
        raise ValueError("RISK_POLICY_RELATION_INVALID")

    max_concurrent = observation.get("max_concurrent_positions")
    if (
        not isinstance(max_concurrent, int)
        or isinstance(max_concurrent, bool)
        or max_concurrent <= 0
    ):
        raise ValueError("MAX_CONCURRENT_POSITIONS_INVALID")

    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": source,
        "provenance": provenance,
        "asset": asset,
        "direction": direction,
        "entry_price": entry,
        "stop_price": stop_price,
        "stop_distance": stop_distance,
        "risk_policy_version": policy_version,
        "risk_policy_validation": "VALID",
        "risk_per_trade": risk_per_trade,
        "max_portfolio_risk": max_portfolio_risk,
        "max_concurrent_positions": max_concurrent,
        "observed_at": observed_at,
    }


__all__ = ["validate_stop_risk_policy_source"]
