"""ARUNDA TRADE LIFECYCLE CONTRACT v0.1 — state machine definition only."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from trade_management_contract_common import ContractBase


class TradeLifecycleState(str, Enum):
    PRE_TRADE = "PRE_TRADE"
    OPEN = "OPEN"
    INITIAL_RISK = "INITIAL_RISK"
    PROFIT_ACTIVATION = "PROFIT_ACTIVATION"
    PROTECTION = "PROTECTION"
    EXTENSION = "EXTENSION"
    DISSIPATION = "DISSIPATION"
    EXIT = "EXIT"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"


ALLOWED_TRANSITIONS = {
    TradeLifecycleState.PRE_TRADE: (TradeLifecycleState.OPEN, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.OPEN: (TradeLifecycleState.INITIAL_RISK, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.INITIAL_RISK: (TradeLifecycleState.PROFIT_ACTIVATION, TradeLifecycleState.PROTECTION, TradeLifecycleState.EXTENSION, TradeLifecycleState.DISSIPATION, TradeLifecycleState.EXIT, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.PROFIT_ACTIVATION: (TradeLifecycleState.PROTECTION, TradeLifecycleState.EXTENSION, TradeLifecycleState.DISSIPATION, TradeLifecycleState.EXIT, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.PROTECTION: (TradeLifecycleState.EXTENSION, TradeLifecycleState.DISSIPATION, TradeLifecycleState.EXIT, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.EXTENSION: (TradeLifecycleState.PROFIT_ACTIVATION, TradeLifecycleState.PROTECTION, TradeLifecycleState.DISSIPATION, TradeLifecycleState.EXIT, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.DISSIPATION: (TradeLifecycleState.PROTECTION, TradeLifecycleState.EXIT, TradeLifecycleState.EMERGENCY_EXIT),
    TradeLifecycleState.EXIT: (),
    TradeLifecycleState.EMERGENCY_EXIT: (),
}

TERMINAL_STATES = frozenset({TradeLifecycleState.EXIT, TradeLifecycleState.EMERGENCY_EXIT})


@dataclass(frozen=True)
class TradeLifecycle(ContractBase):
    state: TradeLifecycleState
    state_reason: Optional[str] = None

    def validate(self) -> bool:
        if not isinstance(self.state, TradeLifecycleState):
            raise TypeError("state must be TradeLifecycleState")
        if self.state_reason is not None and not isinstance(self.state_reason, str):
            raise TypeError("state_reason must be text or None")
        return True

    def allowed_transitions(self) -> tuple:
        return ALLOWED_TRANSITIONS[self.state]

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
