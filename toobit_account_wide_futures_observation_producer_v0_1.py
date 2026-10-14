"""Normalize documented account-wide Toobit Futures read evidence (no I/O)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from account_wide_futures_coverage_contract_v0_1 import validate_account_wide_futures_coverage


def build_toobit_account_wide_futures_observation(
    *, positions_adapter_result: Any, balances_adapter_result: Any, observed_at: str, cycle_id: str,
    account_scope: str, provenance: str,
) -> dict[str, Any]:
    def blocked(reason: str) -> dict[str, Any]:
        return {"observation_state": "BLOCKED", "portfolio_state": "BLOCKED",
                "positions_coverage": "BLOCKED", "observation_block_reason": reason,
                "positions": None, "balances": None, "coverage_evidence": None}
    for value, reason in ((observed_at, "FUTURES_OBSERVATION_TIMESTAMP_MISSING"),
                          (cycle_id, "FUTURES_OBSERVATION_CYCLE_ID_MISSING"),
                          (account_scope, "FUTURES_OBSERVATION_ACCOUNT_SCOPE_MISSING"),
                          (provenance, "FUTURES_OBSERVATION_PROVENANCE_MISSING")):
        if not isinstance(value, str) or not value.strip():
            return blocked(reason)
    for result, reason in ((positions_adapter_result, "FUTURES_POSITION_PROVIDER_READ_UNAVAILABLE"),
                           (balances_adapter_result, "FUTURES_BALANCE_PROVIDER_READ_UNAVAILABLE")):
        if getattr(result, "allowed", False) is not True:
            return blocked(str(getattr(result, "reason", reason)))
    position_data = getattr(positions_adapter_result, "data", None)
    balance_data = getattr(balances_adapter_result, "data", None)
    if not isinstance(position_data, Mapping) or position_data.get("coverage_scope") != "ACCOUNT_WIDE":
        return blocked("FUTURES_PROVIDER_ACCOUNT_WIDE_COVERAGE_REQUIRED")
    if not isinstance(balance_data, Mapping) or balance_data.get("coverage_scope") != "ACCOUNT_WIDE":
        return blocked("FUTURES_PROVIDER_ACCOUNT_WIDE_BALANCE_COVERAGE_REQUIRED")
    if position_data.get("categories_queried") != ["USDT", "USDC"] or balance_data.get("categories_queried") != ["USDT", "USDC"]:
        return blocked("FUTURES_BOTH_SETTLEMENT_CATEGORIES_REQUIRED")
    positions_by_category = position_data.get("positions_by_category")
    balances_by_category = balance_data.get("balances_by_category")
    if not isinstance(positions_by_category, Mapping) or set(positions_by_category) != {"USDT", "USDC"}:
        return blocked("FUTURES_ACCOUNT_WIDE_POSITION_CATEGORIES_INVALID")
    if not isinstance(balances_by_category, Mapping) or set(balances_by_category) != {"USDT", "USDC"}:
        return blocked("FUTURES_ACCOUNT_WIDE_BALANCE_CATEGORIES_INVALID")
    positions = []
    for category in ("USDT", "USDC"):
        rows = positions_by_category[category]
        if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
            return blocked("FUTURES_ACCOUNT_WIDE_POSITION_ROWS_INVALID")
        for row in rows:
            if row.get("side") not in {"LONG", "SHORT"} or not isinstance(row.get("symbol"), str) or not row["symbol"].strip():
                return blocked("FUTURES_ACCOUNT_WIDE_POSITION_IDENTITY_INVALID")
            positions.append({**dict(row), "settlement_category": category})
    balances = []
    for category in ("USDT", "USDC"):
        rows = balances_by_category[category]
        if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
            return blocked("FUTURES_ACCOUNT_WIDE_BALANCE_ROWS_INVALID")
        for row in rows:
            if row.get("category") != category or not isinstance(row.get("asset"), str):
                return blocked("FUTURES_ACCOUNT_WIDE_BALANCE_IDENTITY_INVALID")
            balances.append(dict(row))
    coverage_input = {
        "account_scope": account_scope.strip(), "cycle_id": cycle_id.strip(),
        "observed_at": observed_at.strip(),
        "provider_endpoint": "/api/v1/futures/positions",
        "provenance": provenance.strip(), "http_method": "GET",
        "coverage_scope": "ACCOUNT_WIDE", "pagination_complete": True,
        "pages_received": 2, "pages_total": 2,
        "provider_contract_semantics": "DOCUMENTED_ALL_CONTRACT_POSITIONS_WHEN_SYMBOL_OMITTED",
        "positions": positions,
    }
    coverage = validate_account_wide_futures_coverage(coverage_input)
    if coverage.get("coverage_state") != "AVAILABLE":
        return blocked(coverage.get("coverage_block_reason") or "FUTURES_COVERAGE_INVALID")
    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "PROVIDER_CONTRACT_AND_SHAPE_VALID",
        "observation_source": "TOOBIT_FUTURES_ACCOUNT_GET",
        "account_scope": account_scope.strip(), "cycle_id": cycle_id.strip(),
        "observed_at": observed_at.strip(), "provenance": provenance.strip(),
        "coverage_scope": "ACCOUNT_WIDE", "positions_coverage": "ACCOUNT_WIDE",
        "positions": positions, "balances": balances, "coverage_evidence": coverage_input,
        "coverage_validation": coverage, "portfolio_state": "BLOCKED",
        "portfolio_block_reason": "PER_POSITION_RISK_ALLOCATION_AND_APPROVED_VALUATION_REQUIRED",
        "allocated_risk": None, "concurrent_positions": len(positions),
        "portfolio_capital": None, "usable_capital": None,
    }


__all__ = ["build_toobit_account_wide_futures_observation"]
