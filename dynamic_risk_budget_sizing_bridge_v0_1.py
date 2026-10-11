"""Dynamic Risk -> Risk Budget -> Position Sizing bridge for the production universe.

Uses the existing capital policy, ATR14 calculation, ATR multiplier, and sizing
formula. It is variable-cardinality and memory-only; no DB/provider/execution I/O.
Missing or invalid current-run inputs fail closed per asset.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import floor, isfinite
from typing import Any


def _finite_positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
        and float(value) > 0
    )


def _field(record: Any, name: str, default=None):
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _block(risk: dict, reason: str) -> None:
    risk["position_sizing_state"] = "BLOCKED"
    risk["position_sizing_reason"] = reason
    risk["position_quantity"] = None
    risk["position_size"] = None
    risk["exposure"] = None
    risk["stop_price"] = None
    risk["stop_distance"] = None
    risk["quantity_source"] = None
    risk["quantity_unit"] = None


def build_dynamic_risk_budget_and_sizing(
    *,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    risk_snapshot: dict[str, dict[str, Any]],
    opportunity_by_asset: Mapping[str, Mapping[str, Any]],
    market_data_by_symbol: Mapping[str, Any],
    capital_config: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Enrich current-run Risk rows with existing policy budget/size fields.

    Allocation capacity matches risk_budget_engine:
      budget = capital * risk_per_trade
      portfolio capacity = floor((capital * max_portfolio_risk) / budget)
      allowed count = min(valid candidates, max concurrent, portfolio capacity)

    Candidate order is the current dynamic decision snapshot order. No fixed
    15-asset list, score re-ranking, budget invention, or fallback price is used.
    """
    import market_data_engine
    from position_sizing_engine import (
        calculate_position_size,
        calculate_exposure,
    )

    if not isinstance(decision_snapshot, Mapping) or not isinstance(risk_snapshot, dict):
        raise TypeError("decision/risk snapshots have invalid types")
    if set(decision_snapshot) != set(risk_snapshot):
        raise ValueError("decision/risk snapshot cardinality mismatch")
    if not isinstance(capital_config, Mapping):
        raise TypeError("capital_config must be a Mapping")

    capital = capital_config.get("capital")
    risk_per_trade = capital_config.get("risk_per_trade")
    max_portfolio_risk = capital_config.get("max_portfolio_risk")
    max_positions = capital_config.get("max_concurrent_positions")

    if not _finite_positive(capital) or not _finite_positive(risk_per_trade):
        raise ValueError("capital/risk_per_trade configuration invalid")
    if not _finite_positive(max_portfolio_risk):
        raise ValueError("max_portfolio_risk configuration invalid")
    if isinstance(max_positions, bool) or not isinstance(max_positions, int) or max_positions <= 0:
        raise ValueError("max_concurrent_positions configuration invalid")

    risk_budget = float(capital) * float(risk_per_trade)
    max_portfolio_risk_amount = float(capital) * float(max_portfolio_risk)
    if not _finite_positive(risk_budget) or not _finite_positive(max_portfolio_risk_amount):
        raise ValueError("computed risk budget invalid")

    portfolio_capacity = floor(max_portfolio_risk_amount / risk_budget)
    allowed_capacity = min(max_positions, portfolio_capacity)

    candidates = []
    for asset, decision in decision_snapshot.items():
        risk = risk_snapshot[asset]
        if not isinstance(risk, dict):
            raise ValueError(f"risk row invalid: {asset}")
        _block(risk, "NOT_AN_ACTIONABLE_RISK_CANDIDATE")

        if (
            not isinstance(decision, Mapping)
            or decision.get("state") != "ACTIONABLE"
            or decision.get("direction") not in ("LONG", "SHORT")
            or risk.get("risk_state") != "APPROVED"
            or risk.get("direction") != decision.get("direction")
        ):
            continue

        opportunity = opportunity_by_asset.get(asset)
        if not isinstance(opportunity, Mapping):
            _block(risk, "CURRENT_RUN_OPPORTUNITY_MISSING")
            continue

        entry_price = opportunity.get("price")
        if not _finite_positive(entry_price):
            _block(risk, "AUTHORITATIVE_ENTRY_PRICE_INVALID")
            continue

        symbol = f"{asset}/USDT"
        market_record = market_data_by_symbol.get(symbol)
        candles = _field(market_record, "candles")
        if not isinstance(candles, (list, tuple)):
            _block(risk, "CURRENT_RUN_CANDLES_MISSING")
            continue

        atr14 = market_data_engine.calculate_real_atr14(candles)
        stop_distance = market_data_engine.calculate_runtime_stop_distance(atr14)
        if not _finite_positive(stop_distance):
            _block(risk, "REAL_ATR14_STOP_DISTANCE_UNAVAILABLE")
            continue

        direction = decision["direction"]
        stop_price = float(entry_price) - float(stop_distance) if direction == "LONG" else float(entry_price) + float(stop_distance)
        if not _finite_positive(stop_price):
            _block(risk, "DIRECTIONAL_STOP_PRICE_INVALID")
            continue
        if (direction == "LONG" and not stop_price < float(entry_price)) or (
            direction == "SHORT" and not stop_price > float(entry_price)
        ):
            _block(risk, "DIRECTIONAL_STOP_ALIGNMENT_INVALID")
            continue

        candidates.append({
            "asset": asset,
            "direction": direction,
            "entry_price": float(entry_price),
            "stop_distance": float(stop_distance),
            "stop_price": float(stop_price),
            "risk": risk,
        })

    allocated = 0
    for candidate in candidates:
        risk = candidate["risk"]
        if allocated >= allowed_capacity:
            _block(risk, "PORTFOLIO_RISK_CAPACITY_EXCEEDED")
            continue

        quantity = calculate_position_size(risk_budget, candidate["stop_distance"])
        exposure = calculate_exposure(quantity, candidate["entry_price"])
        if not _finite_positive(quantity) or not _finite_positive(exposure):
            _block(risk, "POSITION_SIZE_OR_EXPOSURE_INVALID")
            continue

        risk.update({
            "position_sizing_state": "CALCULATED",
            "position_sizing_reason": "EXISTING_RISK_BUDGET_AND_POSITION_SIZE_POLICY",
            "risk_budget": float(risk_budget),
            "position_quantity": float(quantity),
            "position_size": float(quantity),
            "exposure": float(exposure),
            "entry_price": candidate["entry_price"],
            "stop_price": candidate["stop_price"],
            "stop_distance": candidate["stop_distance"],
            "quantity_source": "POSITION_SIZING.position_size",
            "position_quantity_source": "POSITION_SIZING.position_size",
            "quantity_unit": "BASE_ASSET",
            "quantity_recomputed": False,
            "quantity_rescaled": False,
            "quantity_rounded": False,
            "quantity_clipped": False,
        })
        allocated += 1

    return risk_snapshot


__all__ = ["build_dynamic_risk_budget_and_sizing"]
