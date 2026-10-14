"""Bridge a validated account-wide ledger into Smart Risk source contracts.

This is a pure mapping boundary: it never fetches data, approves policy, or
turns a blocked/incompletely valued ledger into capital.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from smart_risk_readonly_producer_boundary_v0_1 import evaluate_readonly_smart_risk_cycle


def build_smart_risk_sources_from_authoritative_ledger(
    ledger_observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    def blocked(reason: str) -> dict[str, Any]:
        return {"bridge_state": "BLOCKED", "bridge_block_reason": reason,
                "capital_source_observation": None, "portfolio_source_observation": None}
    if not isinstance(ledger_observation, Mapping):
        return blocked("SMART_RISK_AUTHORITATIVE_LEDGER_REQUIRED")
    try:
        if ledger_observation.get("portfolio_state") != "AVAILABLE" or ledger_observation.get("portfolio_validation") != "VALID":
            raise ValueError("SMART_RISK_AUTHORITATIVE_LEDGER_NOT_VALID")
        if ledger_observation.get("coverage_scope") != "ACCOUNT_WIDE" or set(ledger_observation.get("market_coverage") or []) != {"SPOT", "FUTURES"}:
            raise ValueError("SMART_RISK_ACCOUNT_WIDE_SPOT_FUTURES_COVERAGE_REQUIRED")
        for key in ("account_scope", "observed_at", "cycle_id", "provenance", "valuation_policy_id", "valuation_policy_version"):
            value = ledger_observation.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("SMART_RISK_LEDGER_" + key.upper() + "_MISSING")
        if ledger_observation.get("valuation_policy_state") != "APPROVED":
            raise ValueError("SMART_RISK_APPROVED_VALUATION_POLICY_REQUIRED")
        rates = ledger_observation.get("asset_valuation_evidence")
        valued_assets = ledger_observation.get("valued_assets")
        if not isinstance(rates, Mapping) or not isinstance(valued_assets, list) or not valued_assets:
            raise ValueError("SMART_RISK_ALL_NONZERO_ASSETS_MUST_BE_VALUED")
        if set(str(asset).upper() for asset in valued_assets) != set(str(asset).upper() for asset in rates):
            raise ValueError("SMART_RISK_ASSET_VALUATION_COVERAGE_MISMATCH")
        available_capital = ledger_observation.get("portfolio_capital")
        usable_capital = ledger_observation.get("usable_capital")
        allocated_risk = ledger_observation.get("allocated_risk")
        concurrent_positions = ledger_observation.get("concurrent_positions")
        for value, reason in ((available_capital, "SMART_RISK_LEDGER_CAPITAL_INVALID"),
                              (usable_capital, "SMART_RISK_LEDGER_USABLE_CAPITAL_INVALID")):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(reason)
        if usable_capital > available_capital:
            raise ValueError("SMART_RISK_LEDGER_USABLE_CAPITAL_INVALID")
        if isinstance(allocated_risk, bool) or not isinstance(allocated_risk, (int, float)) or allocated_risk < 0:
            raise ValueError("SMART_RISK_LEDGER_ALLOCATED_RISK_INVALID")
        if isinstance(concurrent_positions, bool) or not isinstance(concurrent_positions, int) or concurrent_positions < 0:
            raise ValueError("SMART_RISK_LEDGER_CONCURRENT_POSITIONS_INVALID")
        source = "TOOBIT_ACCOUNT_WIDE_SPOT_FUTURES_VALUED_LEDGER_V0_1"
        capital = {
            "capital_state": "AVAILABLE", "capital_validation": "VALID",
            "capital_source": source, "provenance": ledger_observation["provenance"],
            "asset_scope": "ACCOUNT_WIDE", "observed_at": ledger_observation["observed_at"],
            "available_capital": float(available_capital), "usable_capital": float(usable_capital),
            "account_scope": ledger_observation["account_scope"], "cycle_id": ledger_observation["cycle_id"],
            "valuation_policy_id": ledger_observation["valuation_policy_id"],
            "valuation_policy_version": ledger_observation["valuation_policy_version"],
            "reporting_currency": "USDT", "valued_assets": list(valued_assets),
        }
        portfolio = {
            "portfolio_state": "AVAILABLE", "portfolio_validation": "VALID",
            "portfolio_source": source, "provenance": ledger_observation["provenance"],
            "asset_scope": "ACCOUNT_WIDE", "observed_at": ledger_observation["observed_at"],
            "portfolio_capital": float(available_capital), "usable_capital": float(usable_capital),
            "allocated_risk": float(allocated_risk), "concurrent_positions": concurrent_positions,
            "account_scope": ledger_observation["account_scope"], "cycle_id": ledger_observation["cycle_id"],
            "ledger_id": ledger_observation.get("ledger_id"), "ledger_version": ledger_observation.get("ledger_version"),
            "valuation_policy_id": ledger_observation["valuation_policy_id"],
            "valuation_policy_version": ledger_observation["valuation_policy_version"],
            "reporting_currency": "USDT", "valued_assets": list(valued_assets),
        }
        return {"bridge_state": "AVAILABLE", "bridge_block_reason": None,
                "capital_source_observation": capital, "portfolio_source_observation": portfolio}
    except (TypeError, ValueError) as exc:
        return blocked(str(exc).strip() or "SMART_RISK_LEDGER_BRIDGE_INVALID")


def evaluate_smart_risk_from_authoritative_ledger(
    *, ledger_observation: Mapping[str, Any] | None, asset: str, direction: str,
    entry_price: float, stop_policy_observation: Mapping[str, Any] | None,
    risk_policy_observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bridge = build_smart_risk_sources_from_authoritative_ledger(ledger_observation)
    if bridge.get("bridge_state") != "AVAILABLE":
        return {"risk_state": "BLOCKED", "block_reason": bridge.get("bridge_block_reason"),
                "position_quantity": None, "quantity_source": None}
    result = evaluate_readonly_smart_risk_cycle(
        asset=asset, direction=direction, entry_price=entry_price,
        capital_source_observation=bridge["capital_source_observation"],
        portfolio_source_observation=bridge["portfolio_source_observation"],
        stop_policy_observation=stop_policy_observation,
        risk_policy_observation=risk_policy_observation,
    )
    return {**result, "ledger_bridge_state": "AVAILABLE"}


__all__ = ["build_smart_risk_sources_from_authoritative_ledger", "evaluate_smart_risk_from_authoritative_ledger"]
