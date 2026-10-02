"""ARUNDA TRADER â€” TOOBIT PREFLIGHT EVIDENCE PRODUCER v0.1

Provider-specific read-only owner for CP46-A6 evidence assembly.

This module composes authoritative Toobit reads into the existing
provider-neutral evidence contracts. It performs no order write,
database write, retry, synthesis, rounding, or quantity conversion.

Spot margin/leverage and position-conflict evidence remain absent when
Toobit does not expose an authoritative provider-native value.
"""

from __future__ import annotations

from typing import Any, Dict

from provider_preflight_evidence_assembler_v0_1 import (
    build_provider_preflight_evidence,
)
from provider_preflight_v0_1 import (
    ProviderAccountState,
    ProviderContractState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
)
from toobit_provider_order_state_v0_1 import (
    build_toobit_provider_order_state,
)


def _filter_map(filters: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(filters, dict):
        raise RuntimeError("Toobit contract filters are unavailable")
    return {
        str(key): value
        for key, value in filters.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _first_filter(filters: Dict[str, Dict[str, Any]], *names: str):
    for name in names:
        row = filters.get(name)
        if isinstance(row, dict):
            return row
    return None


def build_toobit_provider_contract_state(
    adapter,
    asset: str,
) -> ProviderContractState:
    result = adapter.trading_constraints(asset)
    if getattr(result, "allowed", False) is not True:
        raise RuntimeError(
            "Authoritative Toobit contract state unavailable: "
            f"{getattr(result, 'reason', 'unknown')}"
        )

    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        raise RuntimeError("Toobit contract evidence is invalid")

    symbol = data.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise RuntimeError("Toobit contract symbol is invalid")

    status = str(data.get("status", "")).upper()
    filters = _filter_map(data.get("filters"))
    lot = _first_filter(filters, "LOT_SIZE", "MARKET_LOT_SIZE")

    # Toobit Spot exchangeInfo publishes the minimum order notional in
    # MIN_NOTIONAL and the executable min/max trade amount in TRADE_AMOUNT.
    # The previous implementation incorrectly required maxNotional from
    # MIN_NOTIONAL, a field Toobit does not publish for Spot. Use the
    # provider-owned TRADE_AMOUNT bounds instead; no value is inferred.
    notional = _first_filter(filters, "TRADE_AMOUNT")
    min_notional_filter = _first_filter(filters, "NOTIONAL", "MIN_NOTIONAL")

    if lot is None:
        raise RuntimeError("Authoritative Toobit LOT_SIZE state is unavailable")
    if notional is None:
        raise RuntimeError("Authoritative Toobit TRADE_AMOUNT state is unavailable")

    required = ("minQty", "maxQty", "stepSize")
    if any(lot.get(key) is None for key in required):
        raise RuntimeError("Toobit quantity constraint state is incomplete")

    min_notional = notional.get("minAmount")
    max_notional = notional.get("maxAmount")

    if min_notional is None and min_notional_filter is not None:
        min_notional = min_notional_filter.get("minNotional")

    if min_notional is None or max_notional is None:
        raise RuntimeError("Toobit notional bounds are incomplete")

    return ProviderContractState(
        symbol_valid=(status == "TRADING"),
        contract_valid=True,
        min_quantity=lot["minQty"],
        max_quantity=lot["maxQty"],
        quantity_step=lot["stepSize"],
        quote_min_amount=notional["minAmount"],
        quote_max_amount=notional["maxAmount"],
        min_notional=min_notional,
        max_notional=max_notional,
    )


def build_toobit_provider_account_state(
    adapter,
) -> ProviderAccountState:
    result = adapter.account_check()
    if getattr(result, "allowed", False) is not True:
        raise RuntimeError(
            "Authoritative Toobit account state unavailable: "
            f"{getattr(result, 'reason', 'unknown')}"
        )

    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        raise RuntimeError("Toobit account evidence is invalid")

    return ProviderAccountState(
        state_known=True,
        margin_state_known=None,
        leverage_state_known=None,
        position_conflict=None,
    )


def build_toobit_provider_timestamp_state(
    adapter,
) -> ProviderTimestampState:
    result = adapter.get_server_time()
    if getattr(result, "allowed", False) is not True:
        raise RuntimeError(
            "Authoritative Toobit server time unavailable: "
            f"{getattr(result, 'reason', 'unknown')}"
        )

    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        raise RuntimeError("Toobit server-time evidence is invalid")

    raw = data.get("serverTime")
    if raw is None:
        raw = data.get("timestamp")

    try:
        timestamp_ms = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Toobit server timestamp is invalid") from exc

    if timestamp_ms <= 0:
        raise RuntimeError("Toobit server timestamp is non-positive")

    return ProviderTimestampState(
        state_known=True,
        exchange_timestamp_ms=timestamp_ms,
        max_drift_ms=5000,
    )


def build_toobit_provider_preflight_evidence(
    *,
    adapter,
    asset: str,
) -> ProviderPreflightEvidence:
    """Read and compose authoritative Toobit CP46-A6 evidence."""
    if adapter is None:
        raise RuntimeError("Toobit adapter is required")
    if not isinstance(asset, str) or not asset.strip():
        raise RuntimeError("Asset is required")

    contract = build_toobit_provider_contract_state(adapter, asset)
    account = build_toobit_provider_account_state(adapter)
    orders = build_toobit_provider_order_state(adapter, asset)
    timestamp = build_toobit_provider_timestamp_state(adapter)

    return build_provider_preflight_evidence(
        contract=contract,
        account=account,
        orders=orders,
        timestamp=timestamp,
        portfolio=None,
    )


__all__ = [
    "build_toobit_provider_contract_state",
    "build_toobit_provider_account_state",
    "build_toobit_provider_timestamp_state",
    "build_toobit_provider_preflight_evidence",
]
