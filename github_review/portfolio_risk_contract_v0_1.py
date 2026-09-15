"""ARUNDA PORTFOLIO RISK CONTRACT v0.1 — dynamic portfolio boundary."""
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from trade_management_contract_common import ContractBase, CapitalState, _validate_optional_number


@dataclass(frozen=True)
class PortfolioRisk(ContractBase):
    portfolio_capital: Optional[float]
    usable_capital: Optional[float]
    total_risk: Optional[float]
    allocated_risk: Optional[float]
    total_exposure: Optional[float]
    concurrent_positions: Optional[int]
    correlation_exposure: Optional[Mapping[str, Any]]
    concentration: Optional[Mapping[str, Any]]
    portfolio_risk_state: Optional[str]
    capital_state: CapitalState = CapitalState.UNAVAILABLE_CAPITAL

    def validate(self) -> bool:
        for name, value in (("portfolio_capital", self.portfolio_capital), ("usable_capital", self.usable_capital), ("total_risk", self.total_risk), ("allocated_risk", self.allocated_risk), ("total_exposure", self.total_exposure)):
            _validate_optional_number(value, name)
        if self.concurrent_positions is not None and (isinstance(self.concurrent_positions, bool) or not isinstance(self.concurrent_positions, int) or self.concurrent_positions < 0):
            raise ValueError("concurrent_positions must be a non-negative integer")
        for name, value in (("correlation_exposure", self.correlation_exposure), ("concentration", self.concentration)):
            if value is not None and not isinstance(value, Mapping):
                raise TypeError(f"{name} must be a mapping or None")
        return True
