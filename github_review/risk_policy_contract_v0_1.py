"""ARUNDA RISK POLICY CONTRACT v0.1 — versioned policy representation only."""
from dataclasses import dataclass
from typing import Any, Optional
from trade_management_contract_common import ContractBase, CapitalState, ValidationStatus, _require_nonempty_text, _validate_optional_number


@dataclass(frozen=True)
class RiskPolicy(ContractBase):
    policy_id: str
    policy_version: str
    risk_per_trade: Optional[float]
    portfolio_risk_limit: Optional[float]
    max_exposure: Optional[float]
    max_concurrent_positions: Optional[int]
    initial_stop_policy: Any
    trailing_policy: Any
    profit_policy: Any
    partial_exit_policy: Any
    breakeven_policy: Any
    time_exit_policy: Any
    emergency_exit_policy: Any
    real_capital_required: bool = True
    capital_state: CapitalState = CapitalState.UNAVAILABLE_CAPITAL

    def validate(self) -> bool:
        _require_nonempty_text(self.policy_id, "policy_id")
        _require_nonempty_text(self.policy_version, "policy_version")
        for name, value in (("risk_per_trade", self.risk_per_trade), ("portfolio_risk_limit", self.portfolio_risk_limit), ("max_exposure", self.max_exposure)):
            _validate_optional_number(value, name)
        if self.max_concurrent_positions is not None and (isinstance(self.max_concurrent_positions, bool) or not isinstance(self.max_concurrent_positions, int) or self.max_concurrent_positions < 0):
            raise ValueError("max_concurrent_positions must be a non-negative integer")
        if not isinstance(self.real_capital_required, bool):
            raise TypeError("real_capital_required must be bool")
        return True


POLICY_VALUE_STATUS = ValidationStatus.UNVALIDATED.value
RISK_POLICY_VERSIONING = "REQUIRED"
