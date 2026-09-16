"""ARUNDA SMART RISK CONTRACT v0.1.

Provider-neutral, execution-free risk decision boundary.
"""
from dataclasses import dataclass
from typing import Optional


REAL_CAPITAL = "REAL_CAPITAL"
RISK_STATES = ("APPROVED", "BLOCKED")
DIRECTIONS = ("LONG", "SHORT")


@dataclass(frozen=True)
class SmartRiskDecision:
    asset: str
    direction: Optional[str]
    entry_price: Optional[float]
    stop_distance: Optional[float]
    risk_budget: Optional[float]
    position_size: Optional[float]
    exposure: Optional[float]
    remaining_portfolio_risk: Optional[float]
    concurrent_positions: Optional[int]
    max_concurrent_positions: Optional[int]
    risk_state: str
    reason: str
    policy_version: Optional[str]

    def validate(self) -> bool:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("asset must be a non-empty string")
        if self.risk_state not in RISK_STATES:
            raise ValueError("invalid risk_state")
        if self.direction is not None and self.direction not in DIRECTIONS:
            raise ValueError("invalid direction")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be a non-empty string")
        if self.policy_version is not None and not isinstance(self.policy_version, str):
            raise TypeError("policy_version must be a string or None")
        for name, value in (
            ("entry_price", self.entry_price),
            ("stop_distance", self.stop_distance),
            ("risk_budget", self.risk_budget),
            ("position_size", self.position_size),
            ("exposure", self.exposure),
            ("remaining_portfolio_risk", self.remaining_portfolio_risk),
        ):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                raise ValueError(f"invalid {name}")
        if self.concurrent_positions is not None and (
            isinstance(self.concurrent_positions, bool)
            or not isinstance(self.concurrent_positions, int)
            or self.concurrent_positions < 0
        ):
            raise ValueError("invalid concurrent_positions")
        if self.max_concurrent_positions is not None and (
            isinstance(self.max_concurrent_positions, bool)
            or not isinstance(self.max_concurrent_positions, int)
            or self.max_concurrent_positions < 1
        ):
            raise ValueError("invalid max_concurrent_positions")
        return True
