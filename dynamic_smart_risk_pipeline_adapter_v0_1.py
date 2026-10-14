"""Fail-closed orchestration adapter for Smart Risk evidence.

This boundary deliberately does not source or synthesize capital, portfolio,
stop, or policy observations. The caller must provide independently sourced
observations for the same current cycle. Missing evidence yields BLOCKED and
never falls back to legacy quantity sizing.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dynamic_smart_risk_sizing_boundary_v0_1 import (
    build_dynamic_smart_risk_decision,
    to_dynamic_risk_sizing_fields,
)


def evaluate_smart_risk_for_asset(
    *,
    asset: str,
    direction: str,
    entry_price: float,
    capital_observation: Any = None,
    portfolio_observation: Mapping[str, Any] | None = None,
    stop_policy_observation: Mapping[str, Any] | None = None,
    risk_policy_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a provenance-bearing sizing result, or an explicit BLOCKED result."""
    missing = [
        name
        for name, value in (
            ("real_capital", capital_observation),
            ("portfolio", portfolio_observation),
            ("stop_policy", stop_policy_observation),
            ("risk_policy", risk_policy_observation),
        )
        if value is None
    ]
    if missing:
        return {
            "asset": asset,
            "risk_state": "BLOCKED",
            "quantity_source": None,
            "position_quantity": None,
            "block_reason": "SMART_RISK_EVIDENCE_MISSING",
            "missing_observations": missing,
        }

    # Capital, portfolio, and per-asset stop evidence must describe the same
    # observation cycle. Policy is version-matched by the sizing boundary.
    try:
        capital_time = getattr(capital_observation, "observed_at", None)
        portfolio_time = portfolio_observation.get("observed_at")
        stop_time = stop_policy_observation.get("observed_at")
        cycle_times = (capital_time, portfolio_time, stop_time)
        if any(not isinstance(value, str) or not value.strip() for value in cycle_times):
            raise ValueError("SMART_RISK_CYCLE_TIMESTAMP_MISSING")
        if len(set(cycle_times)) != 1:
            raise ValueError("SMART_RISK_OBSERVATION_CYCLE_MISMATCH")

        decision = build_dynamic_smart_risk_decision(
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            capital=capital_observation,
            portfolio_observation=portfolio_observation,
            stop_policy_observation=stop_policy_observation,
            risk_policy=risk_policy_observation,
        )
        fields = to_dynamic_risk_sizing_fields(decision)
        return {
            "asset": asset,
            "risk_state": "APPROVED",
            "block_reason": None,
            **fields,
        }
    except (TypeError, ValueError, KeyError) as exc:
        reason = str(exc).strip() or "SMART_RISK_EVIDENCE_INVALID"
        return {
            "asset": asset,
            "risk_state": "BLOCKED",
            "quantity_source": None,
            "position_quantity": None,
            "block_reason": reason,
        }


__all__ = ["evaluate_smart_risk_for_asset"]
