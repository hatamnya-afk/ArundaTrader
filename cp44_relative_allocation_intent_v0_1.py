"""CP44 Relative Allocation Intent v0.1.

This is an intent layer only.
It does not calculate position size, exposure, capital, or risk budget.

Production formula remains unfrozen until Management approval.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from cp44_relative_conviction_contract_v0_1 import RelativeConviction


METHOD_UNFROZEN = "METHOD_UNFROZEN"


def _validate_convictions(
    convictions: Mapping[str, RelativeConviction],
) -> None:
    if not isinstance(convictions, Mapping) or not convictions:
        raise ValueError("CONVICTION_SET_INVALID")

    for asset, conviction in convictions.items():
        if not isinstance(asset, str) or not asset.strip():
            raise ValueError("CONVICTION_ASSET_INVALID")
        if not isinstance(conviction, RelativeConviction):
            raise ValueError("CONVICTION_OBJECT_INVALID")
        conviction.validate()


def build_candidate_relative_allocation(
    convictions: Mapping[str, RelativeConviction],
    method: str,
) -> dict[str, float]:
    """Build an explicitly selected research candidate.

    This function intentionally refuses an unspecified production method.
    """
    _validate_convictions(convictions)

    if method != "NORMALIZED_CONVICTION":
        raise ValueError(
            "ALLOCATION_METHOD_NOT_APPROVED"
        )

    total = sum(
        max(0.0, float(item.conviction))
        for item in convictions.values()
    )

    if not isfinite(total) or total <= 0.0:
        raise ValueError("CONVICTION_TOTAL_INVALID")

    allocation = {
        asset: max(0.0, float(item.conviction)) / total
        for asset, item in convictions.items()
    }

    total_allocation = sum(allocation.values())

    if not isfinite(total_allocation):
        raise ValueError("ALLOCATION_TOTAL_INVALID")

    if abs(total_allocation - 1.0) > 1e-12:
        raise RuntimeError("ALLOCATION_NOT_NORMALIZED")

    return allocation


def build_relative_allocation_intent(
    convictions: Mapping[str, RelativeConviction],
    method: str = METHOD_UNFROZEN,
) -> dict[str, object]:
    """Return allocation intent without capital/risk/exposure semantics."""
    allocation = build_candidate_relative_allocation(
        convictions,
        method,
    )

    return {
        "state": "READY",
        "method": method,
        "allocation_intent": allocation,
        "dynamic_universe": True,
        "fixed_15_used": False,
        "capital_used": False,
        "risk_budget_used": False,
        "position_size_used": False,
        "exposure_used": False,
        "production_formula_frozen": False,
        "validation": "VALID",
    }


__all__ = [
    "METHOD_UNFROZEN",
    "build_candidate_relative_allocation",
    "build_relative_allocation_intent",
]
