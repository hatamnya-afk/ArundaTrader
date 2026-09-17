"""ARUNDA DYNAMIC SMART-RISK CONTRACT BOUNDARY v0.1.

Provider-neutral boundary between dynamic Decision and Smart Risk.
No exchange, database, order, or execution dependency.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from smart_risk_engine_v0_1 import build_smart_risk


EXECUTION = False
DB_WRITES = 0
FIXED_15_USED = False


def normalize_asset(asset: Any) -> str:
    if not isinstance(asset, str):
        raise ValueError("asset must be string")
    value = asset.strip().upper()
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"invalid dynamic asset: {asset}")
    return f"{parts[0]}/{parts[1]}"


def build_dynamic_smart_risk(
    asset: str,
    decision: Mapping[str, Any],
    observation: Mapping[str, Any],
    policy: Mapping[str, Any],
):
    """Apply Smart Risk to one dynamic decision without fixed-universe logic."""
    dynamic_asset = normalize_asset(asset)

    if not isinstance(decision, Mapping):
        raise ValueError("decision must be mapping")
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be mapping")
    if not isinstance(policy, Mapping):
        raise ValueError("policy must be mapping")

    state = decision.get("state")
    direction = decision.get("direction")
    if state != "ACTIONABLE":
        raise ValueError("smart risk requires ACTIONABLE decision")
    if direction not in ("LONG", "SHORT"):
        raise ValueError("ACTIONABLE decision requires LONG or SHORT direction")

    risk_observation = dict(observation)
    risk_observation["asset"] = dynamic_asset
    risk_observation["direction"] = direction

    result = build_smart_risk(risk_observation, policy)

    if result.asset != dynamic_asset:
        raise RuntimeError("Smart Risk asset identity mismatch")
    if result.direction != direction:
        raise RuntimeError("Smart Risk direction mismatch")
    if result.risk_state not in ("APPROVED", "BLOCKED"):
        raise RuntimeError("invalid Smart Risk state")

    return result


def build_dynamic_smart_risk_snapshot(
    decisions: Mapping[str, Mapping[str, Any]],
    observations: Mapping[str, Mapping[str, Any]],
    policy: Mapping[str, Any],
):
    """Preserve dynamic cardinality: N decisions in, N Smart-Risk results out."""
    if not isinstance(decisions, Mapping) or not isinstance(observations, Mapping):
        raise ValueError("decisions and observations must be mappings")
    if set(decisions) != set(observations):
        raise ValueError("DECISION_RISK_CARDINALITY_MISMATCH")

    results = {}
    for asset, decision in decisions.items():
        results[asset] = build_dynamic_smart_risk(
            asset,
            decision,
            observations[asset],
            policy,
        )

    if set(results) != set(decisions):
        raise RuntimeError("SMART_RISK_CARDINALITY_MISMATCH")
    return results


__all__ = [
    "build_dynamic_smart_risk",
    "build_dynamic_smart_risk_snapshot",
]
