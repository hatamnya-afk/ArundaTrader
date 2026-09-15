"""ARUNDA TRADE LIFECYCLE ENGINE v0.1 — lifecycle transition boundary only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


STATES = (
    "PRE_TRADE",
    "OPEN",
    "INITIAL_RISK",
    "PROFIT_ACTIVATION",
    "PROTECTION",
    "EXTENSION",
    "DISSIPATION",
    "EXIT",
    "EMERGENCY_EXIT",
)

TERMINAL_STATES = {"EXIT", "EMERGENCY_EXIT"}

ALLOWED_TRANSITIONS = {
    "PRE_TRADE": {"OPEN"},
    "OPEN": {"INITIAL_RISK", "EMERGENCY_EXIT"},
    "INITIAL_RISK": {"PROFIT_ACTIVATION", "PROTECTION", "EMERGENCY_EXIT"},
    "PROFIT_ACTIVATION": {"PROTECTION", "EXTENSION", "DISSIPATION", "EXIT", "EMERGENCY_EXIT"},
    "PROTECTION": {"EXTENSION", "DISSIPATION", "EXIT", "EMERGENCY_EXIT"},
    "EXTENSION": {"PROTECTION", "DISSIPATION", "EXIT", "EMERGENCY_EXIT"},
    "DISSIPATION": {"EXIT", "EMERGENCY_EXIT"},
    "EXIT": set(),
    "EMERGENCY_EXIT": set(),
}


@dataclass(frozen=True)
class TradeLifecycleTransition:
    state: str
    previous_state: str
    valid: bool
    asset: Optional[str] = None
    reason: Optional[str] = None


def transition_trade_lifecycle(
    current_state: str,
    requested_state: str,
    *,
    asset: Optional[str] = None,
) -> TradeLifecycleTransition:
    """Apply one explicitly requested lifecycle transition.

    This engine manages lifecycle state only. It does not calculate risk,
    size positions, create orders, execute trades, or write to storage.
    """
    if current_state not in STATES:
        return TradeLifecycleTransition(
            state=current_state,
            previous_state=current_state,
            valid=False,
            asset=asset,
            reason="UNKNOWN_CURRENT_STATE",
        )

    if requested_state not in STATES:
        return TradeLifecycleTransition(
            state=current_state,
            previous_state=current_state,
            valid=False,
            asset=asset,
            reason="UNKNOWN_REQUESTED_STATE",
        )

    if requested_state in ALLOWED_TRANSITIONS[current_state]:
        return TradeLifecycleTransition(
            state=requested_state,
            previous_state=current_state,
            valid=True,
            asset=asset,
        )

    reason = "TERMINAL_STATE" if current_state in TERMINAL_STATES else "INVALID_TRANSITION"
    return TradeLifecycleTransition(
        state=current_state,
        previous_state=current_state,
        valid=False,
        asset=asset,
        reason=reason,
    )
