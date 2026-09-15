"""ARUNDA INITIAL RISK CONTRACT v0.1 — risk boundary only."""
from dataclasses import dataclass
from typing import Any, Optional
from trade_management_contract_common import ContractBase, _validate_optional_number, _validate_text_or_none


@dataclass(frozen=True)
class InitialRisk(ContractBase):
    entry_price: Optional[float]
    stop_price: Optional[float]
    stop_distance: Optional[float]
    risk_invalidation_reason: Optional[str]
    stop_method: Optional[str]
    atr14: Optional[float]
    structure_reference: Optional[Any]
    thesis_reference: Optional[Any]

    def validate(self) -> bool:
        _validate_optional_number(self.entry_price, "entry_price", positive=True)
        _validate_optional_number(self.stop_price, "stop_price", positive=True)
        _validate_optional_number(self.stop_distance, "stop_distance", positive=True)
        _validate_optional_number(self.atr14, "atr14", positive=True)
        _validate_text_or_none(self.risk_invalidation_reason, "risk_invalidation_reason")
        _validate_text_or_none(self.stop_method, "stop_method")
        return True


STOP_MULTIPLIER_STATUS = "UNVALIDATED"
ATR_POLICY_REFERENCE = "SOURCE_REFERENCE_ONLY"
