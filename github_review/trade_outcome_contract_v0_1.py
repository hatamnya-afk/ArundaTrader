"""ARUNDA TRADE OUTCOME CONTRACT v0.1 — immutable lifecycle observation."""
from dataclasses import dataclass
from typing import Any, Optional
from trade_management_contract_common import ContractBase, _validate_optional_number, _validate_text_or_none


@dataclass(frozen=True)
class TradeOutcome(ContractBase):
    asset: str
    symbol: str
    direction: str
    entry_time: Any
    entry_price: Optional[float]
    exit_time: Any
    exit_price: Optional[float]
    holding_time: Optional[float]
    mae: Optional[float]
    mfe: Optional[float]
    maximum_drawdown: Optional[float]
    maximum_favorable_excursion: Optional[float]
    giveback: Optional[float]
    realized_pnl: Optional[float]
    realized_r: Optional[float]
    exit_reason: Optional[str]
    initial_stop: Optional[float]
    final_stop: Optional[float]
    market_regime: Optional[str]
    volatility_regime: Optional[str]
    signal_state: Optional[str]
    decision_state: Optional[str]
    policy_version: Optional[str]
    snapshot_id: Optional[str]

    def validate(self) -> bool:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("asset must be non-empty text")
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be non-empty text")
        if not isinstance(self.direction, str) or not self.direction.strip():
            raise ValueError("direction must be non-empty text")
        for name, value in (("entry_price", self.entry_price), ("exit_price", self.exit_price), ("holding_time", self.holding_time), ("mae", self.mae), ("mfe", self.mfe), ("maximum_drawdown", self.maximum_drawdown), ("maximum_favorable_excursion", self.maximum_favorable_excursion), ("giveback", self.giveback), ("realized_pnl", self.realized_pnl), ("realized_r", self.realized_r), ("initial_stop", self.initial_stop), ("final_stop", self.final_stop)):
            _validate_optional_number(value, name)
        _validate_text_or_none(self.exit_reason, "exit_reason")
        _validate_text_or_none(self.policy_version, "policy_version")
        _validate_text_or_none(self.snapshot_id, "snapshot_id")
        return True


UNAVAILABLE_PRODUCER_POLICY = "NOT_YET_AVAILABLE"
