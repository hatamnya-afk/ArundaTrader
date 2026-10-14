"""Normalize account-wide Toobit Spot balance rows into explicit amounts."""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any


def build_toobit_account_wide_spot_observation(
    *, adapter_result: Any, observed_at: str, cycle_id: str,
    account_scope: str, provenance: str,
) -> dict[str, Any]:
    def blocked(reason: str) -> dict[str, Any]:
        return {"observation_state": "BLOCKED", "observation_validation": "INVALID",
                "observation_source": "TOOBIT_SPOT_ACCOUNT_GET", "observation_block_reason": reason,
                "balances": None, "capital_state": "BLOCKED", "available_capital": None, "usable_capital": None}
    for value, reason in ((observed_at, "SPOT_OBSERVATION_TIMESTAMP_MISSING"),
                          (cycle_id, "SPOT_OBSERVATION_CYCLE_ID_MISSING"),
                          (account_scope, "SPOT_OBSERVATION_ACCOUNT_SCOPE_MISSING"),
                          (provenance, "SPOT_OBSERVATION_PROVENANCE_MISSING")):
        if not isinstance(value, str) or not value.strip():
            return blocked(reason)
    if getattr(adapter_result, "allowed", False) is not True:
        return blocked(str(getattr(adapter_result, "reason", "SPOT_PROVIDER_READ_UNAVAILABLE")))
    data = getattr(adapter_result, "data", None)
    if not isinstance(data, Mapping) or data.get("state_known") is not True:
        return blocked("SPOT_PROVIDER_ACCOUNT_STATE_UNKNOWN")
    rows = data.get("balances")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        return blocked("SPOT_PROVIDER_BALANCES_INVALID")
    balances = []
    seen = set()
    for row in rows:
        asset = row.get("asset")
        if not isinstance(asset, str) or not asset.strip():
            return blocked("SPOT_PROVIDER_BALANCE_ASSET_MISSING")
        asset = asset.strip().upper()
        if asset in seen:
            return blocked("SPOT_PROVIDER_BALANCE_ASSET_DUPLICATE:" + asset)
        seen.add(asset)
        try:
            free = Decimal(str(row.get("free")))
            locked = Decimal(str(row.get("locked")))
        except (InvalidOperation, TypeError, ValueError):
            return blocked("SPOT_PROVIDER_BALANCE_AMOUNT_INVALID:" + asset)
        if not free.is_finite() or not locked.is_finite() or free < 0 or locked < 0:
            return blocked("SPOT_PROVIDER_BALANCE_AMOUNT_INVALID:" + asset)
        balances.append({
            "asset": asset, "total_amount": float(free + locked),
            "usable_amount": float(free), "provider_native": dict(row),
        })
    return {
        "observation_state": "AVAILABLE", "observation_validation": "NORMALIZED_PROVIDER_EVIDENCE",
        "observation_source": "TOOBIT_SPOT_ACCOUNT_GET", "account_scope": account_scope.strip(),
        "cycle_id": cycle_id.strip(), "observed_at": observed_at.strip(),
        "coverage_scope": "ACCOUNT_WIDE", "provenance": provenance.strip(),
        "balances": balances, "capital_state": "BLOCKED",
        "capital_block_reason": "APPROVED_ALL_ASSET_VALUATION_AND_PORTFOLIO_RISK_REQUIRED",
        "available_capital": None, "usable_capital": None,
    }


__all__ = ["build_toobit_account_wide_spot_observation"]
