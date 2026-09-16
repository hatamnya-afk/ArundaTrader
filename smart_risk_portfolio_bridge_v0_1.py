"""CP38-G portfolio observation -> Smart Risk provider-neutral bridge."""
from __future__ import annotations
from collections.abc import Mapping
from math import isfinite
from typing import Any


def _number(value: Any, *, positive: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or (number <= 0 if positive else number < 0):
        return None
    return number


def merge_validated_portfolio_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Accept only an explicit, validated real portfolio observation."""
    if not isinstance(observation, Mapping):
        raise ValueError("INVALID_INPUT")
    if observation.get("portfolio_validation") != "VALID":
        raise ValueError("PORTFOLIO_OBSERVATION_UNVALIDATED")
    source = observation.get("portfolio_source")
    if not isinstance(source, str) or not source.strip() or source in {"TEST", "LEGACY", "SIMULATED"}:
        raise ValueError("PORTFOLIO_SOURCE_INVALID")
    provenance = observation.get("provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("PORTFOLIO_PROVENANCE_MISSING")
    portfolio_capital = _number(observation.get("portfolio_capital"), positive=True)
    usable_capital = _number(observation.get("usable_capital"), positive=True)
    allocated_risk = _number(observation.get("allocated_risk"))
    concurrent = observation.get("concurrent_positions")
    if portfolio_capital is None:
        raise ValueError("PORTFOLIO_CAPITAL_INVALID")
    if usable_capital is None or usable_capital > portfolio_capital:
        raise ValueError("USABLE_CAPITAL_INVALID")
    if allocated_risk is None:
        raise ValueError("ALLOCATED_RISK_INVALID")
    if not isinstance(concurrent, int) or isinstance(concurrent, bool) or concurrent < 0:
        raise ValueError("CONCURRENT_POSITIONS_INVALID")
    return {
        "portfolio_capital": portfolio_capital,
        "usable_capital": usable_capital,
        "allocated_risk": allocated_risk,
        "concurrent_positions": concurrent,
    }


__all__ = ["merge_validated_portfolio_observation"]
