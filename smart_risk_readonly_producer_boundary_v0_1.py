"""Read-only producer boundary for the Smart Risk handoff.

This module joins independently sourced observations; it does not call an
exchange, value raw balances, infer stop prices, or invent portfolio risk.
Only explicitly validated, same-cycle inputs can reach the sizing adapter.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dynamic_smart_risk_pipeline_adapter_v0_1 import evaluate_smart_risk_for_asset
from real_capital_source_contract_v0_1 import validate_real_capital_source
from real_portfolio_state_source_contract_v0_1 import validate_real_portfolio_state
from validated_stop_risk_policy_source_contract_v0_1 import validate_stop_risk_policy_source
from smart_risk_policy_bridge_v0_1 import merge_validated_risk_policy
from real_capital_observation_contract_v0_1 import RealCapitalObservation


def _blocked(asset: str, reason: str, missing: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "asset": asset,
        "risk_state": "BLOCKED",
        "quantity_source": None,
        "position_quantity": None,
        "block_reason": reason,
    }
    if missing:
        result["missing_observations"] = missing
    return result


def evaluate_readonly_smart_risk_cycle(
    *,
    asset: str,
    direction: str,
    entry_price: float,
    capital_source_observation: Mapping[str, Any] | None,
    portfolio_source_observation: Mapping[str, Any] | None,
    stop_policy_observation: Mapping[str, Any] | None,
    risk_policy_observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate four upstream observations and evaluate sizing without side effects.

    Capital source observation must already contain policy-valued capital. Raw
    exchange balances are intentionally insufficient. Portfolio risk must come
    from an authoritative portfolio ledger, not be inferred from position size.
    """
    supplied = {
        "capital": capital_source_observation,
        "portfolio": portfolio_source_observation,
        "stop_policy": stop_policy_observation,
        "risk_policy": risk_policy_observation,
    }
    missing = [name for name, value in supplied.items() if value is None]
    if missing:
        return _blocked(asset, "SMART_RISK_EVIDENCE_MISSING", missing)

    try:
        capital_row = validate_real_capital_source(capital_source_observation)
        portfolio_row = validate_real_portfolio_state(portfolio_source_observation)
        stop_row = validate_stop_risk_policy_source(stop_policy_observation)
        policy_row = merge_validated_risk_policy(risk_policy_observation)

        times = {
            capital_row["observed_at"],
            portfolio_row["observed_at"],
            stop_row["observed_at"],
        }
        if len(times) != 1:
            raise ValueError("SMART_RISK_OBSERVATION_CYCLE_MISMATCH")
        if stop_row["asset"].strip().upper() != asset.strip().upper():
            raise ValueError("STOP_POLICY_ASSET_MISMATCH")
        if stop_row["direction"] != direction:
            raise ValueError("STOP_POLICY_DIRECTION_MISMATCH")
        if stop_row["entry_price"] != float(entry_price):
            raise ValueError("STOP_POLICY_ENTRY_MISMATCH")
        if capital_row["asset_scope"] != portfolio_row["asset_scope"]:
            raise ValueError("CAPITAL_PORTFOLIO_SCOPE_MISMATCH")

        capital = RealCapitalObservation(
            capital_state="REAL_CAPITAL",
            portfolio_capital=capital_row["available_capital"],
            usable_capital=capital_row["usable_capital"],
            allocated_risk=portfolio_row["allocated_risk"],
            concurrent_positions=portfolio_row["concurrent_positions"],
            source=capital_row["capital_source"],
            observed_at=capital_row["observed_at"],
            provenance={
                "capital": capital_row["provenance"],
                "portfolio": portfolio_row["provenance"],
                "stop_policy": stop_row["provenance"],
            },
            validation="VALID",
        )
        capital.validate()

        # The sizing contract consumes a single coherent capital/portfolio view.
        portfolio_for_sizing = {
            **portfolio_row,
            "portfolio_capital": capital_row["available_capital"],
            "usable_capital": portfolio_row["usable_capital"],
            "observed_at": capital_row["observed_at"],
        }
        return evaluate_smart_risk_for_asset(
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            capital_observation=capital,
            portfolio_observation=portfolio_for_sizing,
            stop_policy_observation=stop_row,
            risk_policy_observation=policy_row,
        )
    except (TypeError, ValueError, KeyError) as exc:
        reason = str(exc).strip() or "SMART_RISK_EVIDENCE_INVALID"
        return _blocked(asset, reason)


__all__ = ["evaluate_readonly_smart_risk_cycle"]
