"""ARUNDA EXIT EVIDENCE CONTRACT v0.1 — evidence only, no exit decision."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from trade_management_contract_common import ContractBase, _validate_optional_number


class ExitEvidenceLevel(str, Enum):
    NONE = "NONE"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ExitEvidence(ContractBase):
    signal_health: Optional[str]
    structure_health: Optional[str]
    momentum_state: Optional[str]
    volatility_state: Optional[str]
    mfe: Optional[float]
    mae: Optional[float]
    giveback: Optional[float]
    holding_time: Optional[float]
    liquidity: Optional[Any]
    market_regime: Optional[str]
    trend_state: Optional[str]
    exit_evidence_level: ExitEvidenceLevel
    evidence_reasons: tuple[str, ...] = ()

    def validate(self) -> bool:
        for name, value in (("mfe", self.mfe), ("mae", self.mae), ("giveback", self.giveback), ("holding_time", self.holding_time)):
            _validate_optional_number(value, name)
        if not isinstance(self.exit_evidence_level, ExitEvidenceLevel):
            raise TypeError("exit_evidence_level must be ExitEvidenceLevel")
        if not isinstance(self.evidence_reasons, tuple) or not all(isinstance(x, str) for x in self.evidence_reasons):
            raise TypeError("evidence_reasons must be tuple[str, ...]")
        return True
