"""
ARUNDA TRADER — EXCHANGE ADAPTER CONTRACT MAPPING v0.1

Exchange-specific mapping layer.

This module may know concrete adapter implementations.
The canonical boundary itself remains exchange-agnostic.

READ-ONLY ONLY.
NO ORDER.
NO CANCEL.
NO WITHDRAW.
NO DATABASE WRITE.
"""

from __future__ import annotations

from typing import Any, Dict

from exchange_adapter_boundary import (
    AdapterBridge,
    CanonicalResult,
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_PUBLIC_MARKET_DATA,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
    readonly_capabilities,
    canonical_account,
    canonical_balance,
    canonical_constraints,
    canonical_symbol,
    unavailable_result,
)

from bitpin_trading_adapter import BitpinTradingAdapter
from toobit_trading_adapter import ToobitTradingAdapter

from exchange_execution_contract import (
    CanonicalOrderRequest,
    CanonicalExecutionResult,
    EXECUTION_ENABLED,
    ORDER_SUBMISSION_ENABLED,
)


# ============================================================
# CONCRETE READ-ONLY ADAPTER BRIDGE
# ============================================================

class _ReadOnlyAdapterBridge(AdapterBridge):
    """
    Concrete AdapterBridge implementing the canonical
    submission interface.

    Submission remains permanently fail-closed while
    ORDER_SUBMISSION and EXECUTION are disabled.

    No exchange submission method is called here.
    No raw exchange response can reach Core.
    """

    @staticmethod
    def _validate_submission_request(
        request: CanonicalOrderRequest,
    ) -> tuple[bool, str, str]:

        if not isinstance(request, CanonicalOrderRequest):
            return (
                False,
                "INVALID_REQUEST",
                "Request is not a CanonicalOrderRequest.",
            )

        asset = getattr(request, "asset", None)
        direction = getattr(request, "direction", None)
        entry_price = getattr(request, "entry_price", None)
        quantity = getattr(request, "quantity", None)
        timestamp = getattr(request, "timestamp", None)
        snapshot_id = getattr(request, "snapshot_id", None)
        intent_id = getattr(request, "intent_id", None)

        if not isinstance(asset, str) or not asset.strip():
            return False, "INVALID_ASSET", "Canonical asset is required."

        if direction not in ("LONG", "SHORT"):
            return (
                False,
                "INVALID_DIRECTION",
                "Canonical direction must be LONG or SHORT.",
            )

        if entry_price is None:
            return (
                False,
                "INVALID_ENTRY_PRICE",
                "Canonical entry_price is required.",
            )

        if isinstance(quantity, bool) or quantity is None:
            return (
                False,
                "INVALID_QUANTITY",
                "Canonical quantity is required.",
            )

        try:
            if quantity <= 0:
                return (
                    False,
                    "INVALID_QUANTITY",
                    "Canonical quantity must be greater than zero.",
                )
        except (TypeError, ValueError):
            return (
                False,
                "INVALID_QUANTITY",
                "Canonical quantity is not comparable.",
            )

        if not isinstance(timestamp, str) or not timestamp.strip():
            return (
                False,
                "INVALID_TIMESTAMP",
                "Canonical timestamp is required.",
            )

        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            return (
                False,
                "INVALID_SNAPSHOT_ID",
                "Canonical snapshot_id is required.",
            )

        if not isinstance(intent_id, str) or not intent_id.strip():
            return (
                False,
                "INVALID_INTENT_ID",
                "Canonical intent_id is required.",
            )

        return True, "", ""

    def submit_order(
        self,
        request: CanonicalOrderRequest,
    ) -> CanonicalExecutionResult:

        valid, error_code, error_message = (
            self._validate_submission_request(request)
        )

        if not valid:
            return CanonicalExecutionResult(
                accepted=False,
                exchange_order_id=None,
                status="FAIL_CLOSED",
                asset=getattr(request, "asset", None),
                direction=getattr(request, "direction", None),
                executed_quantity=None,
                executed_price=None,
                timestamp=None,
                adapter=None,
                error_code=error_code,
                error_message=error_message,
            )

        # Contract-level execution gate comes first.
        # Capability resolution must never override the
        # authoritative execution safety state.

        if EXECUTION_ENABLED is not True:
            return CanonicalExecutionResult(
                accepted=False,
                exchange_order_id=None,
                status="FAIL_CLOSED",
                asset=request.asset,
                direction=request.direction,
                executed_quantity=None,
                executed_price=None,
                timestamp=None,
                adapter=None,
                error_code="EXECUTION_DISABLED",
                error_message=(
                    "Execution is disabled in this environment."
                ),
            )

        if ORDER_SUBMISSION_ENABLED is not True:
            return CanonicalExecutionResult(
                accepted=False,
                exchange_order_id=None,
                status="FAIL_CLOSED",
                asset=request.asset,
                direction=request.direction,
                executed_quantity=None,
                executed_price=None,
                timestamp=None,
                adapter=None,
                error_code="ORDER_SUBMISSION_DISABLED",
                error_message=(
                    "Order submission is disabled by contract."
                ),
            )

        # Execution remains disabled in this checkpoint.
        # Even a future enabled capability cannot submit here.
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="FAIL_CLOSED",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=None,
            adapter=None,
            error_code="EXECUTION_DISABLED",
            error_message=(
                "Execution is disabled in this environment."
            ),
        )


# ============================================================
# GENERIC RESULT ACCESS
# ============================================================

def _result_value(result: Any, name: str, default: Any = None) -> Any:
    return getattr(result, name, default)


def _result_data(result: Any) -> Dict[str, Any]:
    data = _result_value(result, "data")
    return data if isinstance(data, dict) else {}


# ============================================================
# BITPIN MAPPING
# ============================================================

def map_bitpin_account(result: Any) -> CanonicalResult:
    return unavailable_result(
        "get_account",
        "Bitpin private account read is not verified.",
        data=canonical_account(
            account_type=None,
            can_trade=None,
            status="UNAVAILABLE",
            source="BITPIN",
        ),
    )


def map_bitpin_balance(result: Any) -> CanonicalResult:
    return unavailable_result(
        "get_balances",
        "Bitpin private balance read is not verified.",
        data=canonical_balance(
            asset=None,
            free=None,
            locked=None,
            total=None,
            source="BITPIN",
        ),
    )


def map_bitpin_exchange_info(result: Any) -> CanonicalResult:
    return unavailable_result(
        "get_exchange_info",
        "Bitpin exchange-info contract is not available in the verified adapter.",
        data=None,
    )


def map_bitpin_symbol(result: Any) -> CanonicalResult:
    data = _result_data(result)

    asset = data.get("asset")

    return CanonicalResult(
        status=str(
            _result_value(result, "status", "UNAVAILABLE")
        ),
        allowed=bool(
            _result_value(result, "allowed", False)
        ),
        operation="validate_symbol",
        reason=str(
            _result_value(
                result,
                "reason",
                "Bitpin symbol validation unavailable.",
            )
        ),
        data=canonical_symbol(
            symbol=None,
            exists=None,
            tradable=None,
            status=None,
        )
        | {
            "asset": asset,
        },
    )


def map_bitpin_constraints(result: Any) -> CanonicalResult:
    data = _result_data(result)

    return unavailable_result(
        "get_trading_constraints",
        str(
            _result_value(
                result,
                "reason",
                "Bitpin trading constraints unavailable.",
            )
        ),
        data=canonical_constraints(
            symbol=None,
            filters=None,
            min_qty=None,
            max_qty=None,
            step_size=None,
            min_notional=None,
            price_precision=None,
            quantity_precision=None,
        )
        | {
            "asset": data.get("asset"),
        },
    )


def bitpin_capabilities() -> Dict[str, bool]:
    return readonly_capabilities(
        public_market_data=False,
        account_read=False,
        balance_read=False,
        symbol_info=False,
        trading_constraints=False,
    )


def build_bitpin_boundary() -> AdapterBridge:
    adapter = BitpinTradingAdapter()

    return _ReadOnlyAdapterBridge(
        account_reader=adapter.account_check,
        balance_reader=adapter.balance_check,
        exchange_info_reader=lambda: unavailable_result(
            "get_exchange_info",
            "Bitpin exchange-info contract is unavailable.",
        ),
        symbol_validator=adapter.symbol_check,
        constraints_reader=adapter.trading_constraints,
        capability_map=bitpin_capabilities(),
        account_mapper=map_bitpin_account,
        balance_mapper=map_bitpin_balance,
        exchange_info_mapper=map_bitpin_exchange_info,
        symbol_mapper=map_bitpin_symbol,
        constraints_mapper=map_bitpin_constraints,
    )


# ============================================================
# TOOBIT MAPPING
# ============================================================

def map_toobit_account(result: Any) -> CanonicalResult:
    data = _result_data(result)
    payload = data.get("account_response")

    if not isinstance(payload, dict):
        payload = {}

    return CanonicalResult(
        status=str(
            _result_value(result, "status", "UNAVAILABLE")
        ),
        allowed=bool(
            _result_value(result, "allowed", False)
        ),
        operation="get_account",
        reason=str(
            _result_value(
                result,
                "reason",
                "Toobit account read unavailable.",
            )
        ),
        data=canonical_account(
            account_type=payload.get("accountType"),
            can_trade=payload.get("canTrade"),
            status=_result_value(
                result,
                "status",
                None,
            ),
            source="TOOBIT",
        ),
    )


def map_toobit_balance(result: Any) -> CanonicalResult:
    data = _result_data(result)

    rows = data.get("nonzero_balances")

    if not isinstance(rows, list):
        rows = []

    balances = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        balances.append(
            canonical_balance(
                asset=row.get("coin"),
                free=row.get("free"),
                locked=row.get("locked"),
                total=row.get("total"),
                source="TOOBIT",
            )
        )

    return CanonicalResult(
        status=str(
            _result_value(result, "status", "UNAVAILABLE")
        ),
        allowed=bool(
            _result_value(result, "allowed", False)
        ),
        operation="get_balances",
        reason=str(
            _result_value(
                result,
                "reason",
                "Toobit balance read unavailable.",
            )
        ),
        data={
            "balance_rows": data.get("balance_rows"),
            "nonzero_count": data.get("nonzero_count"),
            "balances": balances,
            "source": "TOOBIT",
        },
    )


def map_toobit_exchange_info(result: Any) -> CanonicalResult:
    data = _result_data(result)
    rows = data.get("symbols")

    if not isinstance(rows, list):
        return unavailable_result(
            "get_exchange_info",
            "Toobit symbol response is unavailable.",
        )

    symbols = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        symbols.append(
            canonical_symbol(
                symbol=row.get("symbol"),
                exists=True,
                tradable=(
                    str(row.get("status", "")).upper()
                    == "TRADING"
                ),
                status=row.get("status"),
            )
            | {
                "base_asset": row.get("baseAsset"),
                "quote_asset": row.get("quoteAsset"),
            }
        )

    return CanonicalResult(
        status=str(
            _result_value(result, "status", "UNAVAILABLE")
        ),
        allowed=bool(
            _result_value(result, "allowed", False)
        ),
        operation="get_exchange_info",
        reason=str(
            _result_value(
                result,
                "reason",
                "Toobit exchange information unavailable.",
            )
        ),
        data={
            "symbol_count": len(symbols),
            "symbols": symbols,
            "source": "TOOBIT",
        },
    )


def map_toobit_symbol(result: Any) -> CanonicalResult:
    data = _result_data(result)

    symbol = data.get("symbol")
    status = data.get("status")

    exists = symbol is not None

    return CanonicalResult(
        status=str(
            _result_value(result, "status", "UNAVAILABLE")
        ),
        allowed=bool(
            _result_value(result, "allowed", False)
        ),
        operation="validate_symbol",
        reason=str(
            _result_value(
                result,
                "reason",
                "Toobit symbol validation unavailable.",
            )
        ),
        data=canonical_symbol(
            symbol=symbol,
            exists=exists,
            tradable=(
                str(status).upper() == "TRADING"
                if status is not None
                else None
            ),
            status=status,
        )
        | {
            "asset": data.get("asset"),
            "base_asset": data.get("base_asset"),
            "quote_asset": data.get("quote_asset"),
        },
    )


def _filter_value(
    filters: Any,
    filter_type: str,
    key: str,
) -> Any:

    if not isinstance(filters, dict):
        return None

    row = filters.get(filter_type)

    if not isinstance(row, dict):
        return None

    return row.get(key)


def map_toobit_constraints(result: Any) -> CanonicalResult:
    data = _result_data(result)

    filters = data.get("filters")

    if not isinstance(filters, dict):
        return unavailable_result(
            "get_trading_constraints",
            str(
                _result_value(
                    result,
                    "reason",
                    "Toobit trading constraints unavailable.",
                )
            ),
            data=canonical_constraints(
                symbol=data.get("symbol"),
                filters=None,
                min_qty=None,
                max_qty=None,
                step_size=None,
                min_notional=None,
                price_precision=None,
                quantity_precision=None,
            ),
        )

    lot_size = filters.get("LOT_SIZE")
    market_lot_size = filters.get("MARKET_LOT_SIZE")
    notional = filters.get("MIN_NOTIONAL")

    if not isinstance(lot_size, dict):
        lot_size = {}

    if not isinstance(market_lot_size, dict):
        market_lot_size = {}

    if not isinstance(notional, dict):
        notional = {}

    min_qty = (
        lot_size.get("minQty")
        if lot_size.get("minQty") is not None
        else market_lot_size.get("minQty")
    )

    max_qty = (
        lot_size.get("maxQty")
        if lot_size.get("maxQty") is not None
        else market_lot_size.get("maxQty")
    )

    step_size = (
        lot_size.get("stepSize")
        if lot_size.get("stepSize") is not None
        else market_lot_size.get("stepSize")
    )

    min_notional = notional.get("minNotional")

    return CanonicalResult(
        status=str(
            _result_value(result, "status", "UNAVAILABLE")
        ),
        allowed=bool(
            _result_value(result, "allowed", False)
        ),
        operation="get_trading_constraints",
        reason=str(
            _result_value(
                result,
                "reason",
                "Toobit trading constraints unavailable.",
            )
        ),
        data=canonical_constraints(
            symbol=data.get("symbol"),
            filters=filters,
            min_qty=min_qty,
            max_qty=max_qty,
            step_size=step_size,
            min_notional=min_notional,
            price_precision=data.get("price_precision"),
            quantity_precision=data.get(
                "quantity_precision"
            ),
        ),
    )


def toobit_capabilities() -> Dict[str, bool]:
    return readonly_capabilities(
        public_market_data=False,
        account_read=True,
        balance_read=True,
        symbol_info=True,
        trading_constraints=True,
    )


def build_toobit_boundary() -> AdapterBridge:
    adapter = ToobitTradingAdapter()

    return _ReadOnlyAdapterBridge(
        account_reader=adapter.account_check,
        balance_reader=adapter.balance_check,
        exchange_info_reader=adapter.get_exchange_info,
        symbol_validator=adapter.symbol_check,
        constraints_reader=adapter.trading_constraints,
        capability_map=toobit_capabilities(),
        account_mapper=map_toobit_account,
        balance_mapper=map_toobit_balance,
        exchange_info_mapper=map_toobit_exchange_info,
        symbol_mapper=map_toobit_symbol,
        constraints_mapper=map_toobit_constraints,
    )


# ============================================================
# MAPPING CONTRACT CHECK
# ============================================================

def mapping_contract_check() -> Dict[str, Any]:
    bitpin = bitpin_capabilities()
    toobit = toobit_capabilities()

    write_keys = (
        CAPABILITY_ACCOUNT_READ,
        CAPABILITY_BALANCE_READ,
        CAPABILITY_SYMBOL_INFO,
        CAPABILITY_TRADING_CONSTRAINTS,
    )

    return {
        "BITPIN_CAPABILITIES": dict(bitpin),
        "TOOBIT_CAPABILITIES": dict(toobit),
        "BITPIN_WRITES": {
            "ORDER_SUBMISSION": False,
            "ORDER_CANCELLATION": False,
            "WITHDRAWAL": False,
        },
        "TOOBIT_WRITES": {
            "ORDER_SUBMISSION": False,
            "ORDER_CANCELLATION": False,
            "WITHDRAWAL": False,
        },
        "CANONICAL_READ_KEYS": write_keys,
        "EXECUTION_ENABLED": False,
        "DATABASE_WRITE_ENABLED": False,
        "EXCHANGE_WRITE_ENABLED": False,
    }


