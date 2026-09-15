"""ARUNDA RISK CONTEXT CONTRACT v0.1 — observation boundary only."""
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from trade_management_contract_common import ContractBase, _require_nonempty_text, _validate_optional_number, _validate_text_or_none


@dataclass(frozen=True)
class RiskContext(ContractBase):
    asset: str
    symbol: str
    direction: str
    entry_price: Optional[float]
    trend_state: Optional[str] = None
    momentum_state: Optional[str] = None
    acceleration: Optional[float] = None
    position: Optional[float] = None
    volatility_regime: Optional[str] = None
    market_regime: Optional[str] = None
    structure_state: Optional[str] = None
    structure_strength: Optional[float] = None
    signal_quality: Optional[str] = None
    confidence: Optional[float] = None
    liquidity_state: Optional[str] = None
    correlation_context: Optional[Mapping[str, Any]] = None
    portfolio_exposure: Optional[float] = None
    portfolio_risk_state: Optional[str] = None
    market_data_freshness: Optional[Any] = None
    provenance: Optional[Mapping[str, Any]] = None
    timestamp: Optional[Any] = None
    snapshot_id: Optional[str] = None

    def validate(self) -> bool:
        _require_nonempty_text(self.asset, "asset")
        _require_nonempty_text(self.symbol, "symbol")
        _require_nonempty_text(self.direction, "direction")
        _validate_optional_number(self.entry_price, "entry_price", positive=True)
        _validate_optional_number(self.acceleration, "acceleration")
        _validate_optional_number(self.position, "position")
        _validate_optional_number(self.structure_strength, "structure_strength")
        _validate_optional_number(self.confidence, "confidence")
        _validate_optional_number(self.portfolio_exposure, "portfolio_exposure")
        if self.correlation_context is not None and not isinstance(self.correlation_context, Mapping):
            raise TypeError("correlation_context must be a mapping or None")
        if self.provenance is not None and not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a mapping or None")
        _validate_text_or_none(self.snapshot_id, "snapshot_id")
        return True
