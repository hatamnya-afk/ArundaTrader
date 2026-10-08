"""ARUNDA TRADER — TOOBIT PREFLIGHT EVIDENCE PRODUCER v0.1

Provider-specific read-only owner for CP46-A6 evidence assembly.

This module composes authoritative Toobit reads into the existing
provider-neutral evidence contracts. It performs no order write,
database write, retry, synthesis, rounding, or quantity conversion.

Spot margin/leverage and position-conflict evidence remain absent when
Toobit does not expose an authoritative provider-native value.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from provider_preflight_evidence_assembler_v0_1 import (
    build_provider_preflight_evidence,
)
from provider_preflight_v0_1 import (
    ProviderAccountState,
    ProviderContractState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
    ProviderOrderPreflightRequest,
    ProviderPreflightResult,
    run_provider_preflight,
)
from toobit_provider_order_state_v0_1 import (
    build_toobit_provider_order_state,
)
from provider_preflight_v0_1 import ProviderPortfolioState

def _filter_map(filters: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(filters, dict):
        return {
            str(key): value
            for key, value in filters.items()
            if isinstance(key, str) and isinstance(value, dict)
        }

    if isinstance(filters, list):
        normalized: Dict[str, Dict[str, Any]] = {}
        for value in filters:
            if not isinstance(value, dict):
                continue
            filter_type = value.get("filterType")
            if isinstance(filter_type, str) and filter_type.strip():
                normalized[filter_type.strip()] = value
        return normalized

    raise RuntimeError("Toobit contract filters are unavailable")


def _first_filter(filters: Dict[str, Dict[str, Any]], *names: str):
    for name in names:
        row = filters.get(name)
        if isinstance(row, dict):
            return row
    return None


def _positive_decimal(value: Any) -> Decimal:
    if value is None or isinstance(value, bool):
        raise RuntimeError("Authoritative numeric constraint is unavailable")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RuntimeError("Authoritative numeric constraint is invalid") from exc
    if not number.is_finite() or number <= 0:
        raise RuntimeError("Authoritative numeric constraint is non-positive")
    return number


def build_toobit_provider_contract_state(
    adapter,
    asset: str,
    *,
    venue: str = "SPOT",
    execution_instrument=None,
) -> ProviderContractState:
    """Compose provider contract state in the exact provider quantity unit."""
    if venue == "FUTURES":
        result = adapter.futures_trading_constraints(
            asset,
            execution_instrument=execution_instrument,
        )
        if getattr(result, "allowed", False) is not True:
            raise RuntimeError(
                "Authoritative Toobit Futures contract state unavailable: "
                f"{getattr(result, 'reason', 'unknown')}"
            )
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            raise RuntimeError("Toobit Futures contract evidence is invalid")

        symbol = data.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise RuntimeError("Toobit Futures contract symbol is invalid")
        status = str(data.get("status", "")).upper()
        if status != "TRADING":
            raise RuntimeError("Toobit Futures contract is not TRADING")

        filters = _filter_map(data.get("filters"))
        lot = _first_filter(filters, "LOT_SIZE", "MARKET_LOT_SIZE")
        if lot is None:
            raise RuntimeError("Authoritative Toobit Futures quantity filter is unavailable")

        multiplier = _positive_decimal(
            data.get("contract_multiplier", data.get("contractMultiplier"))
        )
        min_underlying = _positive_decimal(lot.get("minQty"))
        max_underlying = _positive_decimal(lot.get("maxQty"))
        step_underlying = _positive_decimal(lot.get("stepSize"))

        # Toobit exchangeInfo documents these Futures filter quantities in
        # underlying/token units while the V2 order API consumes CONTRACTS.
        # Normalize the provider-owned constraints into the order unit using
        # the authoritative contractMultiplier; no order quantity is rounded
        # or fabricated here.
        min_contracts = min_underlying / multiplier
        max_contracts = max_underlying / multiplier
        step_contracts = step_underlying / multiplier

        if min_contracts <= 0 or max_contracts <= 0 or step_contracts <= 0:
            raise RuntimeError("Normalized Toobit Futures contract constraints are invalid")

        return ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity=str(min_contracts),
            max_quantity=str(max_contracts),
            quantity_step=str(step_contracts),
            # Toobit Futures exchangeInfo does not publish an authoritative
            # max notional bound for this contract family. Do not infer one.
            quote_min_amount=None,
            quote_max_amount=None,
            min_notional=None,
            max_notional=None,
            notional_validation_required=False,
        )

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
        notional_validation_required=True,
    )


def build_toobit_provider_account_state(
    adapter,
    asset: str,
    *,
    venue: str = "SPOT",
    execution_instrument=None,
) -> ProviderAccountState:
    if venue == "FUTURES":
        result = adapter.futures_account_state(
            asset,
            execution_instrument=execution_instrument,
        )
        if getattr(result, "allowed", False) is not True:
            raise RuntimeError(
                "Authoritative Toobit Futures account state unavailable: "
                f"{getattr(result, 'reason', 'unknown')}"
            )
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            raise RuntimeError("Toobit Futures account evidence is invalid")
        if data.get("state_known") is not True:
            raise RuntimeError("Toobit Futures account state is unknown")
        margin_known = data.get("margin_state_known")
        leverage_known = data.get("leverage_state_known")
        position_known = data.get("position_state_known")

        if not isinstance(margin_known, bool) or not isinstance(leverage_known, bool):
            raise RuntimeError("Toobit Futures margin/leverage state is invalid")

        if position_known is not True:
            raise RuntimeError("Toobit Futures position state is invalid")

        return ProviderAccountState(
            state_known=True,
            margin_state_known=margin_known,
            leverage_state_known=leverage_known,
            position_conflict=False,
        )

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
    venue: str = "SPOT",
    execution_instrument=None,
) -> ProviderPreflightEvidence:
    """Read and compose authoritative Toobit CP46-A6 evidence."""
    if adapter is None:
        raise RuntimeError("Toobit adapter is required")
    if not isinstance(asset, str) or not asset.strip():
        raise RuntimeError("Asset is required")

    contract = build_toobit_provider_contract_state(
        adapter,
        asset,
        venue=venue,
        execution_instrument=execution_instrument,
    )
    account = build_toobit_provider_account_state(
        adapter,
        asset,
        venue=venue,
        execution_instrument=execution_instrument,
    )
    orders = build_toobit_provider_order_state(
        adapter,
        asset,
        venue=venue,
        execution_instrument=execution_instrument,
    )
    timestamp = build_toobit_provider_timestamp_state(adapter)

    portfolio = None

    if venue == "FUTURES":
        futures_account = adapter.futures_account_state(
            asset,
            execution_instrument=execution_instrument,
        )

        if not getattr(futures_account, "allowed", False):
            raise RuntimeError(
                getattr(
                    futures_account,
                    "reason",
                    "FUTURES_ACCOUNT_UNAVAILABLE",
                )
            )

        state = getattr(futures_account, "data", None)

        if not isinstance(state, dict):
            raise RuntimeError(
                "Futures account state payload is invalid"
            )

        # Toobit exposes account/position state, leverage, and margin
        # mode, but no provider-native Futures boolean authorizing
        # additional portfolio exposure. Do not infer exposure_allowed
        # from balance, leverage, or absence of positions.
        portfolio = ProviderPortfolioState(
            state_known=state.get("state_known") is True,
            exposure_allowed=None,
        )

    return build_provider_preflight_evidence(
        contract=contract,
        account=account,
        orders=orders,
        timestamp=timestamp,
        portfolio=portfolio,
    )

def run_toobit_provider_preflight(
    *,
    adapter,
    request: ProviderOrderPreflightRequest,
) -> ProviderPreflightResult:
    """Production provider boundary: authoritative reads -> pure CP46-A6 preflight."""
    if adapter is None:
        raise RuntimeError("Toobit adapter is required")
    if not isinstance(request, ProviderOrderPreflightRequest):
        raise TypeError("request must be ProviderOrderPreflightRequest")

    evidence = build_toobit_provider_preflight_evidence(
        adapter=adapter,
        asset=request.symbol.replace("USDT", "").strip().upper(),
    )
    return run_provider_preflight(request, evidence)


__all__ = [
    "build_toobit_provider_contract_state",
    "build_toobit_provider_account_state",
    "build_toobit_provider_timestamp_state",
    "build_toobit_provider_preflight_evidence",
    "run_toobit_provider_preflight",
]