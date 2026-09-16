"""ARUNDA REAL CAPITAL OBSERVATION CONTRACT v0.1.
Provider-neutral, read-only capital observation boundary.

This contract carries validated production capital observations into core
risk logic. It contains no provider/API, database, order, or execution logic.
"""
from dataclasses import dataclass
from typing import Mapping

REAL_CAPITAL = "REAL_CAPITAL"
VALIDATION_STATES = ("VALID", "INVALID")


@dataclass(frozen=True)
class RealCapitalObservation:
    capital_state: str
    portfolio_capital: float
    usable_capital: float
    allocated_risk: float
    concurrent_positions: int
    source: str
    observed_at: str
    provenance: Mapping[str, str]
    validation: str

    def validate(self) -> bool:
        if self.capital_state != REAL_CAPITAL:
            raise ValueError("capital_state must be REAL_CAPITAL")
        if self.validation != "VALID":
            raise ValueError("capital observation must be VALID")
        if isinstance(self.portfolio_capital, bool) or not isinstance(self.portfolio_capital, (int, float)) or self.portfolio_capital <= 0:
            raise ValueError("portfolio_capital must be positive")
        if isinstance(self.usable_capital, bool) or not isinstance(self.usable_capital, (int, float)) or self.usable_capital <= 0:
            raise ValueError("usable_capital must be positive")
        if self.usable_capital > self.portfolio_capital:
            raise ValueError("usable_capital cannot exceed portfolio_capital")
        if isinstance(self.allocated_risk, bool) or not isinstance(self.allocated_risk, (int, float)) or self.allocated_risk < 0:
            raise ValueError("allocated_risk must be non-negative")
        if isinstance(self.concurrent_positions, bool) or not isinstance(self.concurrent_positions, int) or self.concurrent_positions < 0:
            raise ValueError("concurrent_positions must be a non-negative integer")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string")
        if not isinstance(self.observed_at, str) or not self.observed_at.strip():
            raise ValueError("observed_at must be a non-empty string")
        if not isinstance(self.provenance, Mapping) or not self.provenance:
            raise ValueError("provenance must be a non-empty mapping")
        for key, value in self.provenance.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
                raise ValueError("provenance entries must contain non-empty strings")
        return True
