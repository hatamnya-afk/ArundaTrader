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
    }


__all__ = ["merge_validated_risk_policy"]
