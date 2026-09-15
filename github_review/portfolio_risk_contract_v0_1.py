"""ARUNDA PORTFOLIO RISK CONTRACT v0.1 — dynamic portfolio boundary."""
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from trade_management_contract_common import ContractBase, CapitalState, _validate_optional_number


@dataclass(frozen=True)
class PortfolioRisk(ContractBase):
    portfolio_id: str
    portfolio_capital: Optional[float]
    usable_capital: Optional[float]
    total_risk: Optional[float]
    allocated_risk: Optional[float]
    remaining_risk_capacity: Optional[float]
    total_exposure: Optional[float]
    remaining_exposure_capacity: Optional[float]
    concurrent_positions: Optional[int]
    concentration: Optional[Mapping[str, Any]]
    correlation_exposure: Optional[Mapping[str, Any]]
    liquidity_state: Optional[str]
    constraints: Optional[Mapping[str, Any]]
    portfolio_risk_state: Optional[str]
    policy_version: Optional[str]
    capital_state: CapitalState = CapitalState.UNAVAILABLE_CAPITAL

    def validate(self) -> bool:
        if not isinstance(self.portfolio_id, str) or not self.portfolio_id.strip():
            raise ValueError("portfolio_id must be a non-empty string")

        if not isinstance(self.capital_state, CapitalState):
            raise TypeError("capital_state must be a CapitalState")

        for name, value in (
            ("portfolio_capital", self.portfolio_capital),
            ("usable_capital", self.usable_capital),
            ("total_risk", self.total_risk),
            ("allocated_risk", self.allocated_risk),
            ("remaining_risk_capacity", self.remaining_risk_capacity),
            ("total_exposure", self.total_exposure),
            ("remaining_exposure_capacity", self.remaining_exposure_capacity),
        ):
            _validate_optional_number(value, name)

        if self.concurrent_positions is not None and (
            isinstance(self.concurrent_positions, bool)
            or not isinstance(self.concurrent_positions, int)
            or self.concurrent_positions < 0
        ):
            raise ValueError("concurrent_positions must be a non-negative integer")

        for name, value in (
            ("concentration", self.concentration),
            ("correlation_exposure", self.correlation_exposure),
            ("constraints", self.constraints),
        ):
            if value is not None and not isinstance(value, Mapping):
                raise TypeError(f"{name} must be a mapping or None")

        for name, value in (
            ("liquidity_state", self.liquidity_state),
            ("portfolio_risk_state", self.portfolio_risk_state),
            ("policy_version", self.policy_version),
        ):
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a string or None")

        return True
