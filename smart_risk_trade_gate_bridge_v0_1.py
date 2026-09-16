"""ARUNDA SMART RISK -> TRADE GATE BRIDGE v0.1.
Provider-neutral, read-only boundary. No order or execution behavior.
"""
from collections.abc import Mapping

from smart_risk_contract_v0_1 import SmartRiskDecision


_FORBIDDEN_KEYS = frozenset(
    {
        "order",
        "order_intent",
        "quantity",
        "execution",
        "exchange",
        "api_key",
        "signature",
    }
)


def build_trade_gate_input(decision: SmartRiskDecision) -> dict:
    """Expose only approved Smart Risk evidence for Trade Gate consumption."""
    if not isinstance(decision, SmartRiskDecision):
        raise ValueError("SMART_RISK_DECISION_INVALID")

    try:
        decision.validate()
    except (TypeError, ValueError):
        raise ValueError("SMART_RISK_DECISION_INVALID") from None

    if decision.risk_state != "APPROVED":
        raise ValueError("SMART_RISK_NOT_APPROVED")

    result = {
        "asset": decision.asset,
        "direction": decision.direction,
        "entry_price": decision.entry_price,
        "stop_distance": decision.stop_distance,
        "position_size": decision.position_size,
        "exposure": decision.exposure,
        "risk_budget": decision.risk_budget,
        "remaining_portfolio_risk": decision.remaining_portfolio_risk,
        "concurrent_positions": decision.concurrent_positions,
        "max_concurrent_positions": decision.max_concurrent_positions,
        "risk_state": decision.risk_state,
        "risk_reason": decision.reason,
        "policy_version": decision.policy_version,
    }

    if _FORBIDDEN_KEYS.intersection(result):
        raise ValueError("TRADE_GATE_BOUNDARY_INVALID")

    return result
