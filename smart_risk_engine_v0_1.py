"""ARUNDA SMART RISK ENGINE v0.1.
Deterministic, side-effect-free allocation validation, invalidation risk,
and position sizing.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from smart_risk_contract_v0_1 import REAL_CAPITAL, SmartRiskDecision

EPSILON = 1e-12


def _positive(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number <= EPSILON:
        return None
    return number


def _fraction(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number < 0 or number > 1:
        return None
    return number


def _blocked(
    asset: str,
    reason: str,
    policy_version: str | None = None,
) -> SmartRiskDecision:
    result = SmartRiskDecision(
        asset,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "BLOCKED",
        reason,
        policy_version,
    )
    result.validate()
    return result


def build_smart_risk(
    observation: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> SmartRiskDecision:
    """Validate an upstream allocation and explicit invalidation boundary.

    No capital, opportunity, stop, or market value is inferred. Allocation is
    an upstream intelligence output expressed as 0..1 of the supplied real
    portfolio capital. The engine converts that allocation into exposure and
    loss-at-invalidation, then fails closed on invalid geometry/capacity.
    """
    if not isinstance(observation, Mapping) or not isinstance(policy, Mapping):
        return _blocked("UNKNOWN", "INVALID_INPUT")

    asset = observation.get("asset")
    if not isinstance(asset, str) or not asset.strip():
        return _blocked("UNKNOWN", "ASSET_NOT_EXPLICIT")

    policy_version = policy.get("policy_version")
    if not isinstance(policy_version, str) or not policy_version.strip():
        return _blocked(asset, "RISK_POLICY_VERSION_MISSING")
    if policy.get("policy_validation") != "VALID":
        return _blocked(asset, "RISK_POLICY_UNVALIDATED", policy_version)
    if observation.get("capital_state") != REAL_CAPITAL:
        return _blocked(asset, "REAL_CAPITAL_NOT_AVAILABLE", policy_version)

    direction = observation.get("direction")
    if direction not in ("LONG", "SHORT"):
        return _blocked(asset, "DIRECTION_INVALID", policy_version)

    entry = _positive(observation.get("entry_price"))
    invalidation = _positive(observation.get("invalidation_price"))
    portfolio_capital = _positive(observation.get("portfolio_capital"))
    usable_capital = _positive(observation.get("usable_capital"))
    allocation_fraction = _fraction(observation.get("allocation_fraction"))
    concurrent = observation.get("concurrent_positions")

    if entry is None:
        return _blocked(asset, "ENTRY_PRICE_NOT_EXPLICIT", policy_version)
    if invalidation is None:
        return _blocked(asset, "INVALIDATION_PRICE_NOT_EXPLICIT", policy_version)
    if portfolio_capital is None:
        return _blocked(asset, "PORTFOLIO_CAPITAL_INVALID", policy_version)
    if usable_capital is None or usable_capital > portfolio_capital:
        return _blocked(asset, "USABLE_CAPITAL_INVALID", policy_version)
    if allocation_fraction is None:
        return _blocked(asset, "ALLOCATION_FRACTION_INVALID", policy_version)
    if allocation_fraction <= EPSILON:
        return _blocked(asset, "ALLOCATION_IS_ZERO", policy_version)
    if not isinstance(concurrent, int) or isinstance(concurrent, bool) or concurrent < 0:
        return _blocked(asset, "CONCURRENT_POSITIONS_INVALID", policy_version)

    max_concurrent = policy.get("max_concurrent_positions")
    if (
        not isinstance(max_concurrent, int)
        or isinstance(max_concurrent, bool)
        or max_concurrent < 1
    ):
        return _blocked(asset, "MAX_CONCURRENT_POSITIONS_POLICY_INVALID", policy_version)
    if concurrent >= max_concurrent:
        return _blocked(asset, "MAX_CONCURRENT_POSITIONS_REACHED", policy_version)

    if direction == "LONG" and invalidation >= entry:
        return _blocked(asset, "LONG_INVALIDATION_MUST_BE_BELOW_ENTRY", policy_version)
    if direction == "SHORT" and invalidation <= entry:
        return _blocked(asset, "SHORT_INVALIDATION_MUST_BE_ABOVE_ENTRY", policy_version)

    stop_distance = abs(entry - invalidation)
    if not isfinite(stop_distance) or stop_distance <= EPSILON:
        return _blocked(asset, "STOP_DISTANCE_INVALID", policy_version)

    allocated_capital = portfolio_capital * allocation_fraction
    if allocated_capital > usable_capital + EPSILON:
        return _blocked(asset, "ALLOCATED_CAPITAL_EXCEEDS_USABLE_CAPITAL", policy_version)

    position_size = allocated_capital / entry
    exposure = position_size * entry
    risk_budget = position_size * stop_distance

    if not all(
        isfinite(value) and value > EPSILON
        for value in (position_size, exposure, risk_budget)
    ):
        return _blocked(asset, "RISK_CALCULATION_INVALID", policy_version)

    if risk_budget > allocated_capital + EPSILON:
        return _blocked(asset, "INVALIDATION_LOSS_EXCEEDS_ALLOCATED_CAPITAL", policy_version)

    result = SmartRiskDecision(
        asset,
        direction,
        entry,
        invalidation,
        stop_distance,
        allocation_fraction,
        allocated_capital,
        risk_budget,
        position_size,
        exposure,
        None,
        concurrent,
        max_concurrent,
        "APPROVED",
        "ALLOCATION_AND_INVALIDATION_VALID",
        policy_version,
    )
    result.validate()
    return result


__all__ = ["build_smart_risk"]
