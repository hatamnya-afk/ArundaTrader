"""ARUNDA CP33 — Initial Risk Engine v0.1.

Observation-only initial-risk boundary. This module preserves explicitly
provided risk observations and refuses to invent stop values when policy is
not validated.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from initial_risk_contract import (
    ATR_POLICY_REFERENCE,
    STOP_MULTIPLIER_STATUS,
    InitialRisk,
)

NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_YET_AVAILABLE = "NOT_YET_AVAILABLE"


def _mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("observation source must be a mapping or None")
    return value


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def _optional_reference(value: Any) -> Any:
    return value if value is not None else None


def build_initial_risk(
    risk_context: Mapping[str, Any],
    *,
    structure: Mapping[str, Any] | None = None,
    thesis: Mapping[str, Any] | None = None,
) -> InitialRisk:
    """Build InitialRisk from explicit observations only.

    Entry price is accepted only from ``entry_price``. The engine never falls
    back to ``price`` or ``latest_close``. ATR14 is retained as a reference;
    because the stop multiplier is explicitly UNVALIDATED, no stop is derived
    from ATR. Explicit stop observations are preserved unchanged.
    """
    context = _mapping(risk_context)
    struct = _mapping(structure)
    thesis_map = _mapping(thesis)

    entry_price = _positive_number(context.get("entry_price"))
    stop_price = _positive_number(context.get("stop_price"))
    stop_distance = _positive_number(context.get("stop_distance"))
    atr14 = _positive_number(context.get("atr14"))

    invalidation: str | None = None
    if entry_price is None:
        invalidation = "ENTRY_PRICE_NOT_EXPLICIT"
    elif STOP_MULTIPLIER_STATUS != "VALIDATED" and stop_price is None and stop_distance is None:
        invalidation = "STOP_POLICY_UNVALIDATED"

    stop_method = context.get("stop_method")
    if stop_method is not None and not isinstance(stop_method, str):
        stop_method = None

    result = InitialRisk(
        entry_price=entry_price,
        stop_price=stop_price,
        stop_distance=stop_distance,
        risk_invalidation_reason=invalidation,
        stop_method=stop_method,
        atr14=atr14,
        structure_reference=_optional_reference(
            context.get("structure_reference", struct.get("structure_state"))
        ),
        thesis_reference=_optional_reference(
            context.get("thesis_reference", thesis_map.get("thesis_reference"))
        ),
    )
    result.validate()
    return result


__all__ = [
    "ATR_POLICY_REFERENCE",
    "NOT_AVAILABLE",
    "NOT_YET_AVAILABLE",
    "STOP_MULTIPLIER_STATUS",
    "build_initial_risk",
]
