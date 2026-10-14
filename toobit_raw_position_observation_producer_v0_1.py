"""Read-only raw Toobit futures position observation boundary.

This producer accepts an already obtained result from the adapter's signed
GET-only futures_account_state method. It preserves provider-native positions
but never derives portfolio capital, allocated risk, or a complete account-wide
portfolio from a symbol-scoped response.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_toobit_raw_position_observation(
    *,
    adapter_result: Any,
    observed_at: str,
    account_scope: str,
    requested_asset: str,
    provenance: str,
) -> dict[str, Any]:
    """Preserve raw position evidence and explicitly block derived portfolio risk."""
    for value, reason in (
        (observed_at, "TOOBIT_POSITION_OBSERVATION_TIMESTAMP_MISSING"),
        (account_scope, "TOOBIT_POSITION_ACCOUNT_SCOPE_MISSING"),
        (requested_asset, "TOOBIT_POSITION_ASSET_MISSING"),
        (provenance, "TOOBIT_POSITION_PROVENANCE_MISSING"),
    ):
        if not isinstance(value, str) or not value.strip():
            return _blocked(reason)

    allowed = getattr(adapter_result, "allowed", False)
    reason = getattr(adapter_result, "reason", None)
    data = getattr(adapter_result, "data", None)
    if allowed is not True or not isinstance(data, Mapping):
        return _blocked(
            str(reason).strip()
            if isinstance(reason, str) and reason.strip()
            else "TOOBIT_POSITION_READ_NOT_AVAILABLE"
        )
    if data.get("position_state_known") is not True:
        return _blocked("TOOBIT_POSITION_STATE_UNKNOWN")

    positions = data.get("positions")
    if not isinstance(positions, list) or any(
        not isinstance(row, Mapping) for row in positions
    ):
        return _blocked("TOOBIT_POSITION_ROWS_INVALID")

    target = requested_asset.strip().upper()
    normalized = []
    for row in positions:
        symbol = row.get("symbol")
        side = row.get("side")
        if not isinstance(symbol, str) or not symbol.strip():
            return _blocked("TOOBIT_POSITION_SYMBOL_INVALID")
        if not isinstance(side, str) or side.strip().upper() not in {"LONG", "SHORT"}:
            return _blocked("TOOBIT_POSITION_SIDE_INVALID")
        # Keep all rows supplied by the adapter, but refuse to claim the
        # requested asset's position state if the provider response mixes symbols.
        if symbol.strip().upper() != target:
            return _blocked("TOOBIT_POSITION_SYMBOL_SCOPE_MISMATCH")
        normalized.append(dict(row))

    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "RAW_PROVIDER_EVIDENCE_ONLY",
        "observation_source": "TOOBIT_FUTURES_POSITIONS_GET",
        "account_scope": account_scope.strip(),
        "asset_scope": target,
        "observed_at": observed_at.strip(),
        "provenance": provenance.strip(),
        "position_state_known": True,
        "positions": normalized,
        "portfolio_state": "BLOCKED",
        "portfolio_block_reason": "AUTHORITATIVE_ACCOUNT_WIDE_PORTFOLIO_RISK_LEDGER_REQUIRED",
        "allocated_risk": None,
        "concurrent_positions": None,
        "portfolio_capital": None,
        "usable_capital": None,
    }


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "observation_state": "BLOCKED",
        "observation_validation": "INVALID",
        "observation_source": "TOOBIT_FUTURES_POSITIONS_GET",
        "positions": None,
        "portfolio_state": "BLOCKED",
        "portfolio_block_reason": reason,
        "allocated_risk": None,
        "concurrent_positions": None,
        "portfolio_capital": None,
        "usable_capital": None,
    }


__all__ = ["build_toobit_raw_position_observation"]
