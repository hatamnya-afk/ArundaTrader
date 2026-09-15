"""ARUNDA RISK ALLOCATION CONTRACT v0.1 — allocation boundary only."""
from dataclasses import dataclass
from typing import Optional
from trade_management_contract_common import ContractBase, _validate_optional_number, _validate_text_or_none


@dataclass(frozen=True)
class RiskAllocation(ContractBase):
    portfolio_risk_capacity: Optional[float]
    trade_risk_capacity: Optional[float]
    allocated_risk: Optional[float]
    correlation_adjustment: Optional[float]
    liquidity_adjustment: Optional[float]
    execution_adjustment: Optional[float]
    allocation_reason: Optional[str]

    def validate(self) -> bool:
        for name, value in (
            ("portfolio_risk_capacity", self.portfolio_risk_capacity),
            ("trade_risk_capacity", self.trade_risk_capacity),
            ("allocated_risk", self.allocated_risk),
            ("correlation_adjustment", self.correlation_adjustment),
            ("liquidity_adjustment", self.liquidity_adjustment),
            ("execution_adjustment", self.execution_adjustment),
        ):
            _validate_optional_number(value, name)
        _validate_text_or_none(self.allocation_reason, "allocation_reason")
        return True


RISK_PER_TRADE_STATUS = "UNVALIDATED"
MAX_PORTFOLIO_RISK_STATUS = "UNVALIDATED"
MAX_EXPOSURE_STATUS = "UNVALIDATED"
