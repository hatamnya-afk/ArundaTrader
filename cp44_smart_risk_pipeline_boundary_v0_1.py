"""CP44 provider-neutral downstream Smart Risk wiring boundary v0.1.

This boundary replaces the legacy Dynamic Risk call path without introducing
fixed capital, exchange dependencies, synthetic values, or fallback sizing.

All capital, Entry/Invalidation, and policy values must be explicit upstream
observations. Missing inputs fail closed into Smart Risk BLOCKED state.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from dynamic_smart_risk_contract_boundary_v0_1 import build_dynamic_smart_risk
from entry_invalidation_boundary_v0_1 import normalize_entry_invalidation
from smart_risk_policy_bridge_v0_1 import merge_validated_risk_policy


def _blocked_asset(asset: str, reason: str) -> dict[str, Any]:
    return {
        "asset": asset,
        "risk_state": "BLOCKED",
        "status": "BLOCKED",
        "risk_decision": None,
        "decision": None,
        "risk_reward": None,
        "reason": reason,
        "fixed_15_used": False,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
        "db_writes": 0,
        "execution": False,
    }


def build_cp44_smart_risk(
    asset: str,
    decision: Mapping[str, Any],
    observation: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the CP44 Smart Risk result from explicit real inputs only.

    The function never invents capital, Entry/Invalidation, policy, or
    position state. Missing or invalid inputs become an explicit BLOCKED
    result rather than falling back to the legacy Dynamic Risk engine.
    """

    if not isinstance(decision, Mapping):
        return _blocked_asset(asset, "DECISION_INPUT_INVALID")
    if not isinstance(observation, Mapping):
        return _blocked_asset(asset, "OBSERVATION_INPUT_INVALID")

    merged_observation = dict(observation)
    merged_observation["asset"] = asset
    merged_observation["direction"] = decision.get("direction")

    entry_boundary = normalize_entry_invalidation(
        asset,
        decision,
        merged_observation,
    )
    if entry_boundary.state != "READY":
        result = _blocked_asset(asset, entry_boundary.reason)
        result["entry_invalidation_state"] = entry_boundary.state
        result["entry_price"] = entry_boundary.entry_price
        result["invalidation_price"] = entry_boundary.invalidation_price
        result["stop_distance"] = entry_boundary.stop_distance
        return result

    merged_observation["entry_price"] = entry_boundary.entry_price
    merged_observation["invalidation_price"] = entry_boundary.invalidation_price
    merged_observation["stop_distance"] = entry_boundary.stop_distance

    required_capital = (
        "capital_state",
        "portfolio_capital",
        "usable_capital",
        "allocated_risk",
        "concurrent_positions",
    )
    if not all(field in merged_observation for field in required_capital):
        missing = [
            field for field in required_capital
            if field not in merged_observation
        ]
        result = _blocked_asset(
            asset,
            "REAL_CAPITAL_OBSERVATION_MISSING:" + ",".join(missing),
        )
        result["entry_invalidation_state"] = entry_boundary.state
        result["entry_price"] = entry_boundary.entry_price
        result["invalidation_price"] = entry_boundary.invalidation_price
        result["stop_distance"] = entry_boundary.stop_distance
        return result

    if not isinstance(policy, Mapping):
        policy = {}

    try:
        validated_policy = merge_validated_risk_policy(policy)
    except (TypeError, ValueError) as exc:
        result = _blocked_asset(
            asset,
            "RISK_POLICY_UNAVAILABLE:" + str(exc),
        )
        result["entry_invalidation_state"] = entry_boundary.state
        result["entry_price"] = entry_boundary.entry_price
        result["invalidation_price"] = entry_boundary.invalidation_price
        result["stop_distance"] = entry_boundary.stop_distance
        return result

    result = build_dynamic_smart_risk(
        asset,
        decision,
        merged_observation,
        validated_policy,
    )
    output = asdict(result)
    output["status"] = output.get("risk_state")
    output["risk_decision"] = output.get("risk_state")
    output["decision"] = output.get("risk_state")
    output["entry_invalidation_state"] = entry_boundary.state
    output["fixed_15_used"] = False
    output["synthetic"] = False
    output["interpolation"] = False
    output["fill"] = False
    output["backfill"] = False
    output["padding"] = False
    output["blending"] = False
    output["db_writes"] = 0
    output["execution"] = False
    return output


__all__ = ["build_cp44_smart_risk"]
