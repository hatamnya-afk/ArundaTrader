"""ARUNDA RISK ALLOCATION ENGINE v0.1 — observation boundary only."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from risk_allocation_contract import RiskAllocation


_REAL_CAPITAL = "REAL_CAPITAL"
_VALID = "VALID"


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def _policy_valid(policy: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(policy, Mapping):
        return False
    return policy.get("policy_validation") == _VALID


def build_risk_allocation(
    context: Mapping[str, Any],
    policy: Optional[Mapping[str, Any]] = None,
) -> RiskAllocation:
    """Build an allocation observation without inventing policy or capital."""
    capital_state = context.get("capital_state") if isinstance(context, Mapping) else None

    portfolio_capacity = _number(context.get("portfolio_risk_capacity"))
    trade_capacity = _number(context.get("trade_risk_capacity"))
    allocated = _number(context.get("allocated_risk"))
    correlation = _number(context.get("correlation_adjustment"))
    liquidity = _number(context.get("liquidity_adjustment"))
    execution = _number(context.get("execution_adjustment"))

    if capital_state != _REAL_CAPITAL:
        return RiskAllocation(
            portfolio_risk_capacity=None,
            trade_risk_capacity=None,
            allocated_risk=None,
            correlation_adjustment=correlation,
            liquidity_adjustment=liquidity,
            execution_adjustment=execution,
            allocation_reason="REAL_CAPITAL_NOT_AVAILABLE",
        )

    if not _policy_valid(policy):
        return RiskAllocation(
            portfolio_risk_capacity=portfolio_capacity,
            trade_risk_capacity=None,
            allocated_risk=None,
            correlation_adjustment=correlation,
            liquidity_adjustment=liquidity,
            execution_adjustment=execution,
            allocation_reason="RISK_POLICY_UNVALIDATED",
        )

    return RiskAllocation(
        portfolio_risk_capacity=portfolio_capacity,
        trade_risk_capacity=trade_capacity,
        allocated_risk=allocated,
        correlation_adjustment=correlation,
        liquidity_adjustment=liquidity,
        execution_adjustment=execution,
        allocation_reason=None,
    )
