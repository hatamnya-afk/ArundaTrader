"""ARUNDA TRADER — ZERO-CAPITAL RESEARCH TRADE CONTRACT v0.1.

One-pipeline quantity resolution:
    observed real capital > 0 -> normal dynamic risk quantity.
    observed real capital == 0 -> predefined research quantity.

This contract never invents capital and never submits an order.
"""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping


NORMAL_TRADE = "NORMAL_TRADE"
RESEARCH_TRADE = "RESEARCH_TRADE"

RISK_QUANTITY_SOURCE = "RISK.position_quantity"
RESEARCH_QUANTITY_SOURCE = "RESEARCH_PREDEFINED"
QUANTITY_UNIT_BASE_ASSET = "BASE_ASSET"


def _non_negative(value: Any, reason: str) -> float:
    if isinstance(value, bool):
        raise ValueError(reason)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(reason) from None
    if not isfinite(number) or number < 0:
        raise ValueError(reason)
    return number


def _positive(value: Any, reason: str) -> float:
    number = _non_negative(value, reason)
    if number <= 0:
        raise ValueError(reason)
    return number


def resolve_trade_quantity(
    *,
    observed_real_capital: Any,
    risk_position_quantity: Any,
    research_quantity: Any,
) -> dict[str, Any]:
    """Resolve Trade Intent quantity from observed capital.

    Capital is a runtime observation, never a configured contract value.

    For real capital > 0, quantity MUST come from dynamic Risk/Position
    Sizing. For real capital == 0, the only permitted quantity is the
    explicitly supplied predefined research quantity.

    No synthetic capital, fallback capital, scaling, rounding, or blending
    is performed.
    """
    capital = _non_negative(
        observed_real_capital,
        "OBSERVED_REAL_CAPITAL_INVALID",
    )

    if capital > 0:
        quantity = _positive(
            risk_position_quantity,
            "RISK_POSITION_QUANTITY_INVALID",
        )
        return {
            "trade_type": NORMAL_TRADE,
            "quantity": quantity,
            "quantity_unit": QUANTITY_UNIT_BASE_ASSET,
            "quantity_source": RISK_QUANTITY_SOURCE,
            "observed_real_capital": capital,
        }

    quantity = _positive(
        research_quantity,
        "RESEARCH_QUANTITY_INVALID",
    )
    return {
        "trade_type": RESEARCH_TRADE,
        "quantity": quantity,
        "quantity_unit": QUANTITY_UNIT_BASE_ASSET,
        "quantity_source": RESEARCH_QUANTITY_SOURCE,
        "observed_real_capital": 0.0,
    }


def validate_research_trade_contract(
    *,
    trade_type: Any,
    observed_real_capital: Any,
    quantity: Any,
    quantity_source: Any,
) -> bool:
    """Validate the zero-capital research clause."""
    capital = _non_negative(
        observed_real_capital,
        "OBSERVED_REAL_CAPITAL_INVALID",
    )

    if trade_type == RESEARCH_TRADE:
        if capital != 0.0:
            raise ValueError(
                "RESEARCH_TRADE_REQUIRES_ZERO_OBSERVED_REAL_CAPITAL"
            )
        _positive(quantity, "RESEARCH_QUANTITY_INVALID")
        if quantity_source != RESEARCH_QUANTITY_SOURCE:
            raise ValueError("RESEARCH_QUANTITY_SOURCE_INVALID")
        return True

    if trade_type == NORMAL_TRADE:
        if capital <= 0.0:
            raise ValueError(
                "NORMAL_TRADE_REQUIRES_POSITIVE_OBSERVED_REAL_CAPITAL"
            )
        _positive(quantity, "RISK_POSITION_QUANTITY_INVALID")
        if quantity_source != RISK_QUANTITY_SOURCE:
            raise ValueError("RISK_QUANTITY_SOURCE_INVALID")
        return True

    raise ValueError("TRADE_TYPE_INVALID")


__all__ = [
    "NORMAL_TRADE",
    "RESEARCH_TRADE",
    "RISK_QUANTITY_SOURCE",
    "RESEARCH_QUANTITY_SOURCE",
    "QUANTITY_UNIT_BASE_ASSET",
    "resolve_trade_quantity",
    "validate_research_trade_contract",
]
