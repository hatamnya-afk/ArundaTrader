"""Dynamic-universe Smart Risk sizing boundary.

This is a pure contract adapter. It does not fetch capital, positions, stops,
policy, market data, or write to any persistence/execution surface. Callers
must supply independently sourced current-cycle observations.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import math

from real_capital_observation_contract_v0_1 import RealCapitalObservation
from smart_risk_engine_v0_1 import build_smart_risk
from smart_risk_entry_stop_bridge_v0_1 import merge_validated_entry_stop
from smart_risk_policy_bridge_v0_1 import merge_validated_risk_policy
from smart_risk_portfolio_bridge_v0_1 import merge_validated_portfolio_observation
from validated_stop_risk_policy_source_contract_v0_1 import (
    validate_stop_risk_policy_source,
)


def _asset_key(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("SMART_RISK_ASSET_INVALID")
    return value.strip().upper().split("/", 1)[0]


def _asset_matches(source: Any, canonical_asset: str) -> bool:
    if not isinstance(source, str) or not source.strip():
        return False
    normalized = source.strip().upper()
    return normalized in {
        canonical_asset,
        f"{canonical_asset}/USDT",
        f"{canonical_asset}USDT",
    }


def _same_number(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return False


def build_dynamic_smart_risk_decision(
    *,
    asset: str,
    direction: str,
    entry_price: float,
    capital: RealCapitalObservation,
    portfolio_observation: Mapping[str, Any],
    stop_policy_observation: Mapping[str, Any],
    risk_policy: Mapping[str, Any],
):
    """Calculate position sizing only from validated, mutually consistent evidence.

    Missing producers must be handled by the caller as blocked; this function
    never supplies defaults or infers stop/capital/policy values.
    """
    canonical_asset = _asset_key(asset)
    if direction not in ("LONG", "SHORT"):
        raise ValueError("SMART_RISK_DIRECTION_INVALID")
    if isinstance(entry_price, bool):
        raise ValueError("SMART_RISK_ENTRY_INVALID")
    try:
        entry = float(entry_price)
    except (TypeError, ValueError):
        raise ValueError("SMART_RISK_ENTRY_INVALID") from None
    if not math.isfinite(entry) or entry <= 0:
        raise ValueError("SMART_RISK_ENTRY_INVALID")

    if not isinstance(capital, RealCapitalObservation):
        raise ValueError("SMART_RISK_REAL_CAPITAL_OBSERVATION_MISSING")
    capital.validate()
    if str(capital.capital_state) != "REAL_CAPITAL":
        raise ValueError("SMART_RISK_REAL_CAPITAL_NOT_AVAILABLE")

    portfolio = merge_validated_portfolio_observation(portfolio_observation)
    for field in (
        "portfolio_capital",
        "usable_capital",
        "allocated_risk",
        "concurrent_positions",
    ):
        if not _same_number(getattr(capital, field), portfolio[field]):
            raise ValueError(f"SMART_RISK_CAPITAL_PORTFOLIO_MISMATCH:{field}")

    stop = validate_stop_risk_policy_source(stop_policy_observation)
    if not _asset_matches(stop["asset"], canonical_asset):
        raise ValueError("SMART_RISK_STOP_ASSET_MISMATCH")
    if stop["direction"] != direction:
        raise ValueError("SMART_RISK_STOP_DIRECTION_MISMATCH")
    if not _same_number(stop["entry_price"], entry):
        raise ValueError("SMART_RISK_STOP_ENTRY_MISMATCH")

    policy = merge_validated_risk_policy(risk_policy)
    if (
        policy["policy_version"] != stop["risk_policy_version"]
        or not _same_number(policy["risk_per_trade"], stop["risk_per_trade"])
        or not _same_number(policy["max_portfolio_risk"], stop["max_portfolio_risk"])
        or policy["max_concurrent_positions"] != stop["max_concurrent_positions"]
    ):
        raise ValueError("SMART_RISK_POLICY_SOURCE_MISMATCH")

    stop_inputs = merge_validated_entry_stop(
        {
            "asset": canonical_asset,
            "direction": direction,
            "entry_price": entry,
            "entry_validation": "VALID",
            "stop_distance": stop["stop_distance"],
            "stop_validation": "VALID",
            "stop_source": stop["observation_source"],
        }
    )

    observation = {
        "asset": canonical_asset,
        "capital_state": "REAL_CAPITAL",
        "portfolio_capital": float(capital.portfolio_capital),
        "usable_capital": float(capital.usable_capital),
        "allocated_risk": float(capital.allocated_risk),
        "concurrent_positions": capital.concurrent_positions,
        "direction": stop_inputs["direction"],
        "entry_price": stop_inputs["entry_price"],
        "stop_distance": stop_inputs["stop_distance"],
    }

    decision = build_smart_risk(observation, policy)
    decision.validate()
    return decision


def to_dynamic_risk_sizing_fields(decision: Any) -> dict[str, Any]:
    """Expose provenance-bearing sizing fields for an explicit downstream adapter."""
    from smart_risk_contract_v0_1 import SmartRiskDecision

    if not isinstance(decision, SmartRiskDecision):
        raise ValueError("SMART_RISK_DECISION_INVALID")
    decision.validate()
    if decision.risk_state != "APPROVED":
        raise ValueError("SMART_RISK_NOT_APPROVED")
    if decision.position_size is None or decision.position_size <= 0:
        raise ValueError("SMART_RISK_POSITION_SIZE_INVALID")
    return {
        "risk_status": "APPROVED",
        "risk_state": "APPROVED",
        "position_quantity": decision.position_size,
        "quantity_unit": "BASE_ASSET",
        "quantity_source": "SMART_RISK_ENGINE_V0_1",
        "quantity_changed": False,
        "quantity_recomputed": False,
        "quantity_rescaled": False,
        "quantity_rounded": False,
        "quantity_clipped": False,
        "risk_budget": decision.risk_budget,
        "risk_position_quantity": decision.position_size,
        "risk_policy_version": decision.policy_version,
        "risk_source": "VALIDATED_REAL_CAPITAL_PORTFOLIO_STOP_POLICY",
    }


__all__ = [
    "build_dynamic_smart_risk_decision",
    "to_dynamic_risk_sizing_fields",
]
