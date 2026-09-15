"""ARUNDA CALIBRATION OBSERVATION CONTRACT v0.1 — prior/observation/validation boundary."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from trade_management_contract_common import ContractBase, _validate_optional_number


class CalibrationEvidenceState(str, Enum):
    PRIOR = "PRIOR"
    OBSERVED = "OBSERVED"
    VALIDATED = "VALIDATED"


@dataclass(frozen=True)
class CalibrationObservation(ContractBase):
    policy_version: str
    prior: Optional[Any]
    observed_evidence: Optional[Any]
    validated_evidence: Optional[Any]
    sample_size: Optional[int]
    market_regime: Optional[str]
    asset_segment: Optional[str]
    direction: Optional[str]
    mae_distribution: Optional[Any]
    mfe_distribution: Optional[Any]
    giveback_distribution: Optional[Any]
    realized_outcomes: Optional[Any]
    oos_result: Optional[Any]
    confidence: Optional[float]
    observation_timestamp: Any
    evidence_state: CalibrationEvidenceState

    def validate(self) -> bool:
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be non-empty text")
        if self.sample_size is not None and (isinstance(self.sample_size, bool) or not isinstance(self.sample_size, int) or self.sample_size < 0):
            raise ValueError("sample_size must be a non-negative integer")
        _validate_optional_number(self.confidence, "confidence")
        if not isinstance(self.evidence_state, CalibrationEvidenceState):
            raise TypeError("evidence_state must be CalibrationEvidenceState")
        return True


AUTOMATIC_POLICY_MUTATION = False
VALIDATED_IS_NOT_AUTOMATIC_UPDATE = True
