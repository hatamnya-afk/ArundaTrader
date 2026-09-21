"""CP44 Reliability + Uncertainty Contract v0.1.

Reliability is not probability.
Uncertainty is an explicit penalty signal.
Neither layer creates capital, risk policy, position size, or exposure.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ReliabilityUncertainty:
    asset: str
    reliability: float
    uncertainty: float
    source: str
    observed_at: str
    provenance: str
    validation: str = "VALID"

    def validate(self) -> bool:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("RELIABILITY_ASSET_INVALID")

        for name, value in (
            ("reliability", self.reliability),
            ("uncertainty", self.uncertainty),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name.upper()}_INVALID")
            if not isfinite(float(value)):
                raise ValueError(f"{name.upper()}_INVALID")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name.upper()}_OUT_OF_RANGE")

        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("RELIABILITY_SOURCE_INVALID")
        if not isinstance(self.observed_at, str) or not self.observed_at.strip():
            raise ValueError("RELIABILITY_TIME_INVALID")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("RELIABILITY_PROVENANCE_INVALID")
        if self.validation != "VALID":
            raise ValueError("RELIABILITY_NOT_VALIDATED")

        return True


__all__ = ["ReliabilityUncertainty"]
