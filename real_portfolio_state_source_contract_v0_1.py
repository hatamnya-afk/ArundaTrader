"""CP39 real portfolio state source contract v0.1."""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED"}


def _require_nonempty_string(observation: Mapping[str, Any], field: str, error: str) -> str:
    value = observation.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _require_finite_number(value: Any, error: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(error)
    number = float(value)
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(error)
    return number


def validate_real_portfolio_state(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an explicit real portfolio observation and return a provider-neutral view."""
    if not isinstance(observation, Mapping):
        raise ValueError("PORTFOLIO_INPUT_INVALID")

    if observation.get("portfolio_state") != "AVAILABLE":
        raise ValueError("PORTFOLIO_STATE_INVALID")

    if observation.get("portfolio_validation") != "VALID":
        raise ValueError("PORTFOLIO_VALIDATION_INVALID")

    portfolio_source = _require_nonempty_string(
        observation, "portfolio_source", "PORTFOLIO_SOURCE_INVALID"
    )
    if portfolio_source in _FORBIDDEN_SOURCES:
        raise ValueError("PORTFOLIO_SOURCE_INVALID")

    provenance = _require_nonempty_string(
        observation, "provenance", "PORTFOLIO_PROVENANCE_INVALID"
    )
    asset_scope = _require_nonempty_string(
        observation, "asset_scope", "PORTFOLIO_ASSET_SCOPE_INVALID"
    )
    observed_at = _require_nonempty_string(
        observation, "observed_at", "PORTFOLIO_OBSERVED_AT_INVALID"
    )

    portfolio_capital = _require_finite_number(
        observation.get("portfolio_capital"), "PORTFOLIO_CAPITAL_INVALID", positive=True
    )
    usable_capital = _require_finite_number(
        observation.get("usable_capital"), "USABLE_CAPITAL_INVALID", positive=True
    )
    if usable_capital > portfolio_capital:
        raise ValueError("USABLE_CAPITAL_INVALID")

    allocated_risk = _require_finite_number(
        observation.get("allocated_risk"), "ALLOCATED_RISK_INVALID"
    )

    concurrent_positions = observation.get("concurrent_positions")
    if (
        isinstance(concurrent_positions, bool)
        or not isinstance(concurrent_positions, int)
        or concurrent_positions < 0
    ):
        raise ValueError("CONCURRENT_POSITIONS_INVALID")

    return {
        "portfolio_state": "AVAILABLE",
        "portfolio_source": portfolio_source,
        "provenance": provenance,
        "asset_scope": asset_scope,
        "portfolio_capital": portfolio_capital,
        "usable_capital": usable_capital,
        "allocated_risk": allocated_risk,
        "concurrent_positions": concurrent_positions,
        "observed_at": observed_at,
    }


__all__ = ["validate_real_portfolio_state"]
