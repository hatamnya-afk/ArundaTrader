"""CP38-F validated Risk Policy -> Smart Risk boundary.

Provider-neutral, read-only contract mapping. No inference, API, DB,
execution, or pipeline coupling.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any


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


def merge_validated_risk_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Return only an explicit, validated risk policy for Smart Risk."""
    if not isinstance(policy, Mapping):
        raise ValueError("POLICY_INVALID_INPUT")

    version = policy.get("policy_version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("POLICY_VERSION_MISSING")

    if policy.get("policy_validation") != "VALID":
        raise ValueError("POLICY_NOT_VALIDATED")

    risk_per_trade = _positive(policy.get("risk_per_trade"))
    if risk_per_trade is None or risk_per_trade > 1:
        raise ValueError("RISK_PER_TRADE_INVALID")

    max_portfolio_risk = _positive(policy.get("max_portfolio_risk"))
    if max_portfolio_risk is None or max_portfolio_risk > 1:
        raise ValueError("MAX_PORTFOLIO_RISK_INVALID")

    recommended_capital = _positive(policy.get("recommended_capital"))
    if recommended_capital is None:
        raise ValueError("RECOMMENDED_CAPITAL_INVALID")

    strategy_capital_envelope = _positive(
        policy.get("strategy_capital_envelope")
    )
    if strategy_capital_envelope is None:
        raise ValueError("STRATEGY_CAPITAL_ENVELOPE_INVALID")

    capital_allocation_factor = _positive(
        policy.get("capital_allocation_factor")
    )
    if capital_allocation_factor is None or capital_allocation_factor > 1:
        raise ValueError("CAPITAL_ALLOCATION_FACTOR_INVALID")

    capital_source = policy.get("capital_source")
    if not isinstance(capital_source, str) or not capital_source.strip():
        raise ValueError("CAPITAL_SOURCE_MISSING")

    max_concurrent = policy.get("max_concurrent_positions")
    if (
        not isinstance(max_concurrent, int)
        or isinstance(max_concurrent, bool)
        or max_concurrent < 1
    ):
        raise ValueError("MAX_CONCURRENT_POSITIONS_INVALID")

    return {
        "policy_version": version,
        "policy_validation": "VALID",
        "risk_per_trade": risk_per_trade,
        "max_portfolio_risk": max_portfolio_risk,
        "max_concurrent_positions": max_concurrent,
        "recommended_capital": recommended_capital,
        "strategy_capital_envelope": strategy_capital_envelope,
        "capital_allocation_factor": capital_allocation_factor,
        "capital_source": capital_source,
    }


__all__ = ["merge_validated_risk_policy"]
