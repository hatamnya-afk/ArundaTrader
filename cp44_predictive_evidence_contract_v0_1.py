"""CP44 Predictive Evidence Contract v0.1.

Evidence is predictive signal strength, never probability.
Provider-neutral and side-effect free.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PredictiveEvidence:
    asset: str
    direction: str
    evidence: float
    source: str
    observed_at: str
    provenance: str
    validation: str = "VALID"

    def validate(self) -> bool:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("EVIDENCE_ASSET_INVALID")
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError("EVIDENCE_DIRECTION_INVALID")
        if not isinstance(self.evidence, (int, float)) or isinstance(self.evidence, bool):
            raise ValueError("EVIDENCE_VALUE_INVALID")
        if not isfinite(float(self.evidence)):
            raise ValueError("EVIDENCE_VALUE_INVALID")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("EVIDENCE_SOURCE_INVALID")
        if not isinstance(self.observed_at, str) or not self.observed_at.strip():
            raise ValueError("EVIDENCE_TIME_INVALID")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("EVIDENCE_PROVENANCE_INVALID")
        if self.validation != "VALID":
            raise ValueError("EVIDENCE_NOT_VALIDATED")
        return True


__all__ = ["PredictiveEvidence"]
