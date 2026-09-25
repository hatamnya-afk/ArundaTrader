"""ARUNDA SMART RISK ENGINE v0.1.
Deterministic, side-effect-free portfolio-risk budgeting and position sizing.
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


def _non_negative(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number < 0:
        return None
    return number


def _adjustment(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number <= 0 or number > 1:
        return None
    return number


def _blocked(
    asset: str,
    reason: str,
    policy_version: str | None = None,
) -> SmartRiskDecision:
    result = SmartRiskDecision(
        asset=asset,
        direction=None,
        entry_price=None,
        stop_distance=None,
        risk_budget=None,
        position_size=None,
        exposure=None,
        remaining_portfolio_risk=None,
        concurrent_positions=None,
        max_concurrent_positions=None,
        risk_state="BLOCKED",
        reason=reason,
        policy_version=policy_version,
        invalidation_price=None,
    )
    result.validate()
    return result


def build_smart_risk(
    observation: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> SmartRiskDecision:
    """Build deterministic Smart Risk from explicit upstream inputs.

    Frozen CP38 semantics:

        Base Risk =
            portfolio_capital * risk_per_trade

        Remaining Portfolio Risk =
            (portfolio_capital * max_portfolio_risk) - allocated_risk

        Risk Budget =
            min(
                Base Risk * correlation_adjustment
                          * liquidity_adjustment
                          * execution_adjustment,
                Remaining Portfolio Risk,
            )

        Position Size = Risk Budget / Stop Distance
        Exposure      = Position Size * Entry Price

    CP38-D compatibility:
        invalidation_price is optional when direct Engine input supplies
        validated entry_price + stop_distance.

    CP44:
        when invalidation_price is supplied, its directional geometry and
        consistency with stop_distance are validated.

    No allocation_fraction or allocated_capital semantics are used.
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
    invalidation_raw = observation.get("invalidation_price")
    invalidation = (
        _positive(invalidation_raw)
        if invalidation_raw is not None
        else None
    )
    stop_distance = _positive(observation.get("stop_distance"))
    # Capital is an observed input to sizing, not a pipeline gate.
    # Zero is a valid real observation; negative/non-finite remains invalid.
    portfolio_capital = _non_negative(observation.get("portfolio_capital"))
    usable_capital = _non_negative(observation.get("usable_capital"))
    allocated_risk = _non_negative(observation.get("allocated_risk"))

    concurrent = observation.get("concurrent_positions")

    if entry is None:
        return _blocked(asset, "ENTRY_PRICE_NOT_EXPLICIT", policy_version)

    if stop_distance is None:
        return _blocked(asset, "STOP_DISTANCE_NOT_EXPLICIT", policy_version)

    if invalidation_raw is not None and invalidation is None:
        return _blocked(asset, "INVALIDATION_PRICE_INVALID", policy_version)

    if portfolio_capital is None:
        return _blocked(asset, "PORTFOLIO_CAPITAL_INVALID", policy_version)

    if usable_capital is None:
        return _blocked(asset, "USABLE_CAPITAL_INVALID", policy_version)

    if usable_capital > portfolio_capital + EPSILON:
        return _blocked(asset, "USABLE_CAPITAL_EXCEEDED", policy_version)

    if allocated_risk is None:
        return _blocked(asset, "ALLOCATED_RISK_INVALID", policy_version)

    risk_per_trade = _positive(policy.get("risk_per_trade"))
    max_portfolio_risk = _positive(policy.get("max_portfolio_risk"))

    if risk_per_trade is None:
        return _blocked(asset, "RISK_PER_TRADE_INVALID", policy_version)

    if max_portfolio_risk is None:
        return _blocked(asset, "MAX_PORTFOLIO_RISK_INVALID", policy_version)

    if risk_per_trade > max_portfolio_risk + EPSILON:
        return _blocked(
            asset,
            "RISK_PER_TRADE_EXCEEDS_PORTFOLIO_CAP",
            policy_version,
        )

    if (
        not isinstance(concurrent, int)
        or isinstance(concurrent, bool)
        or concurrent < 0
    ):
        return _blocked(
            asset,
            "CONCURRENT_POSITIONS_INVALID",
            policy_version,
        )

    max_concurrent = policy.get("max_concurrent_positions")

    if (
        not isinstance(max_concurrent, int)
        or isinstance(max_concurrent, bool)
        or max_concurrent < 1
    ):
        return _blocked(
            asset,
            "MAX_CONCURRENT_POSITIONS_POLICY_INVALID",
            policy_version,
        )

    if concurrent >= max_concurrent:
        return _blocked(
            asset,
            "MAX_CONCURRENT_POSITIONS_REACHED",
            policy_version,
        )

    # CP44 explicit invalidation geometry.
    # CP38-D direct compatibility remains valid when invalidation is absent.
    if invalidation is not None:
        if direction == "LONG" and invalidation >= entry:
            return _blocked(
                asset,
                "LONG_INVALIDATION_MUST_BE_BELOW_ENTRY",
                policy_version,
            )

        if direction == "SHORT" and invalidation <= entry:
            return _blocked(
                asset,
                "SHORT_INVALIDATION_MUST_BE_ABOVE_ENTRY",
                policy_version,
            )

        expected_stop_distance = abs(entry - invalidation)

        if (
            not isfinite(expected_stop_distance)
            or expected_stop_distance <= EPSILON
        ):
            return _blocked(
                asset,
                "STOP_DISTANCE_INVALID",
                policy_version,
            )

        if abs(stop_distance - expected_stop_distance) > EPSILON:
            return _blocked(
                asset,
                "STOP_DISTANCE_INCONSISTENT_WITH_INVALIDATION",
                policy_version,
            )

    correlation_adjustment = _adjustment(
        observation.get("correlation_adjustment", 1.0)
    )
    liquidity_adjustment = _adjustment(
        observation.get("liquidity_adjustment", 1.0)
    )
    execution_adjustment = _adjustment(
        observation.get("execution_adjustment", 1.0)
    )

    if correlation_adjustment is None:
        return _blocked(
            asset,
            "CORRELATION_ADJUSTMENT_INVALID",
            policy_version,
        )

    if liquidity_adjustment is None:
        return _blocked(
            asset,
            "LIQUIDITY_ADJUSTMENT_INVALID",
            policy_version,
        )

    if execution_adjustment is None:
        return _blocked(
            asset,
            "EXECUTION_ADJUSTMENT_INVALID",
            policy_version,
        )

    max_portfolio_risk_amount = (
        portfolio_capital * max_portfolio_risk
    )
    remaining_portfolio_risk = (
        max_portfolio_risk_amount - allocated_risk
    )

    if remaining_portfolio_risk < -EPSILON:
        return _blocked(
            asset,
            "PORTFOLIO_RISK_CAPACITY_INVALID",
            policy_version,
        )

    # With zero observed real capital, the frozen sizing formula naturally
    # produces zero remaining capacity. This is not a balance gate and does
    # not change the pipeline route; it is the mathematical output of the
    # same sizing function at Capital = 0.
    if (
        remaining_portfolio_risk <= EPSILON
        and portfolio_capital > EPSILON
    ):
        return _blocked(
            asset,
            "PORTFOLIO_RISK_CAPACITY_EXHAUSTED",
            policy_version,
        )

    base_risk = portfolio_capital * risk_per_trade

    adjusted_risk = (
        base_risk
        * correlation_adjustment
        * liquidity_adjustment
        * execution_adjustment
    )

    risk_budget = min(
        adjusted_risk,
        remaining_portfolio_risk,
    )

    if not isfinite(risk_budget) or risk_budget < -EPSILON:
        return _blocked(
            asset,
            "RISK_BUDGET_INVALID",
            policy_version,
        )

    if risk_budget <= EPSILON and portfolio_capital > EPSILON:
        return _blocked(
            asset,
            "RISK_BUDGET_INVALID",
            policy_version,
        )

    if risk_budget > usable_capital + EPSILON:
        return _blocked(
            asset,
            "USABLE_CAPITAL_EXCEEDED",
            policy_version,
        )

    position_size = risk_budget / stop_distance
    exposure = position_size * entry

    if not all(
        isfinite(value) and value >= 0
        for value in (position_size, exposure)
    ):
        return _blocked(
            asset,
            "RISK_CALCULATION_INVALID",
            policy_version,
        )

    result = SmartRiskDecision(
        asset=asset,
        direction=direction,
        entry_price=entry,
        stop_distance=stop_distance,
        risk_budget=risk_budget,
        position_size=position_size,
        exposure=exposure,
        remaining_portfolio_risk=remaining_portfolio_risk,
        concurrent_positions=concurrent,
        max_concurrent_positions=max_concurrent,
        risk_state="APPROVED",
        reason=(
            "RISK_SIZING_ZERO_FROM_REAL_CAPITAL"
            if portfolio_capital <= EPSILON
            else "RISK_BUDGET_VALIDATED"
        ),
        policy_version=policy_version,
        invalidation_price=invalidation,
    )

    result.validate()
    return result


__all__ = ["build_smart_risk"]
