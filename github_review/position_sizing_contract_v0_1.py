"""ARUNDA POSITION SIZING CONTRACT v0.1 — structure only, no calculation."""
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from trade_management_contract_common import ContractBase, CapitalState, ValidationStatus, _require_nonempty_text, _validate_optional_number


@dataclass(frozen=True)
class PositionSizing(ContractBase):
    asset: str
    symbol: str
    direction: str
    entry_price: Optional[float]
    stop_distance: Optional[float]
    stop_price: Optional[float]
    usable_capital: Optional[float]
    risk_per_trade: Optional[float]
    risk_budget: Optional[float]
    trading_constraints: Optional[Mapping[str, Any]]
    risk_budget_output: Optional[float] = None
    position_size: Optional[float] = None
    quantity: Optional[float] = None
    exposure: Optional[float] = None
    normalized_quantity: Optional[float] = None
    capital_state: CapitalState = CapitalState.UNAVAILABLE_CAPITAL

    def validate(self) -> bool:
        _require_nonempty_text(self.asset, "asset")
        _require_nonempty_text(self.symbol, "symbol")
        _require_nonempty_text(self.direction, "direction")
        _validate_optional_number(self.entry_price, "entry_price", positive=True)
        _validate_optional_number(self.stop_distance, "stop_distance", positive=True)
        _validate_optional_number(self.stop_price, "stop_price", positive=True)
        for name, value in (("usable_capital", self.usable_capital), ("risk_per_trade", self.risk_per_trade), ("risk_budget", self.risk_budget), ("risk_budget_output", self.risk_budget_output), ("position_size", self.position_size), ("quantity", self.quantity), ("exposure", self.exposure), ("normalized_quantity", self.normalized_quantity)):
            _validate_optional_number(value, name)
        if self.trading_constraints is not None and not isinstance(self.trading_constraints, Mapping):
            raise TypeError("trading_constraints must be a mapping or None")
        if self.capital_state is not CapitalState.REAL_CAPITAL and (self.quantity is not None or self.position_size is not None):
            raise ValueError("Production sizing outputs require REAL_CAPITAL")
        return True


def validate_runtime_invariants(record: PositionSizing) -> dict:
    """Classify producer-dependent invariants without calculating sizing."""
    result = {
        "entry_price": ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value,
        "stop_distance": ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value,
        "quantity_positive": ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value,
        "quantity_max_qty": ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value,
        "quantity_step_size": ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value,
        "exposure_min_notional": ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value,
    }
    if record.entry_price is not None and record.entry_price > 0:
        result["entry_price"] = ValidationStatus.VALID.value
    if record.stop_distance is not None and record.stop_distance > 0:
        result["stop_distance"] = ValidationStatus.VALID.value
    if record.quantity is not None:
        result["quantity_positive"] = ValidationStatus.VALID.value if record.quantity > 0 else "INVALID"
        constraints = record.trading_constraints or {}
        if "max_qty" in constraints and record.quantity <= constraints["max_qty"]:
            result["quantity_max_qty"] = ValidationStatus.VALID.value
        if "step_size" in constraints:
            result["quantity_step_size"] = ValidationStatus.RUNTIME_VALIDATION_REQUIRED.value
    if record.exposure is not None and record.trading_constraints and "min_notional" in record.trading_constraints and record.exposure >= record.trading_constraints["min_notional"]:
        result["exposure_min_notional"] = ValidationStatus.VALID.value
    return result


PRODUCTION_CAPITAL_POLICY = "REAL_CAPITAL_REQUIRED"
