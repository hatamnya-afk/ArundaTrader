"""CP44 Relative Conviction Contract v0.1.

Conviction is a relative decision variable.
It is not probability, risk, capital, or exposure.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RelativeConviction:
    asset: str
    conviction: float
    evidence: float
    reliability: float
    uncertainty: float
    method: str
    source: str
    provenance: str
    validation: str = "VALID"

    def validate(self) -> bool:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("CONVICTION_ASSET_INVALID")

        values = (
            self.conviction,
            self.evidence,
            self.reliability,
            self.uncertainty,
        )

        if any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not isfinite(float(v))
            for v in values
        ):
            raise ValueError("CONVICTION_NUMERIC_INVALID")

        if not 0.0 <= self.conviction <= 1.0:
            raise ValueError("CONVICTION_OUT_OF_RANGE")

        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("RELIABILITY_OUT_OF_RANGE")

        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("UNCERTAINTY_OUT_OF_RANGE")

        if not isinstance(self.method, str) or not self.method.strip():
            raise ValueError("CONVICTION_METHOD_INVALID")

        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("CONVICTION_SOURCE_INVALID")

        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("CONVICTION_PROVENANCE_INVALID")

        if self.validation != "VALID":
            raise ValueError("CONVICTION_NOT_VALIDATED")

        return True


__all__ = ["RelativeConviction"]
