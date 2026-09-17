"""ARUNDA SMART RISK CONTRACT v0.1.
Provider-neutral, execution-free risk decision boundary.

The contract treats capital allocation as an upstream validated intelligence
output. Risk converts that allocation plus an explicit invalidation price into
position size and loss-at-invalidation without imposing a universal risk cap.
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
    invalidation_price: Optional[float]
    stop_distance: Optional[float]
    allocation_fraction: Optional[float]
    allocated_capital: Optional[float]
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

        non_negative_fields = (
            "entry_price",
            "invalidation_price",
            "stop_distance",
            "allocation_fraction",
            "allocated_capital",
            "risk_budget",
            "position_size",
            "exposure",
            "remaining_portfolio_risk",
        )
        for name in non_negative_fields:
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 0
            ):
                raise ValueError(f"invalid {name}")

        if self.allocation_fraction is not None and self.allocation_fraction > 1:
            raise ValueError("allocation_fraction must be <= 1")

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
