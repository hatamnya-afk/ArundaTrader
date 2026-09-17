"""
ARUNDA TRADER — EXCHANGE-AGNOSTIC ADAPTER BOUNDARY v0.1

Canonical read-only boundary.

This module contains NO exchange-specific implementation.
Concrete exchange adapters are injected into AdapterBridge.

NON-NEGOTIABLE:
- No exchange-specific API knowledge.
- No HTTP.
- No database.
- No order submission.
- No cancellation.
- No withdrawal.
- No market-data-provider coupling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


# ============================================================
# CANONICAL RESULT
# ============================================================

@dataclass(frozen=True)
class CanonicalResult:
    status: str
    allowed: bool
    operation: str
    reason: str
    data: Optional[Dict[str, Any]] = None


# ============================================================
# CAPABILITY CONTRACT
# ============================================================

CAPABILITY_PUBLIC_MARKET_DATA = "PUBLIC_MARKET_DATA"
CAPABILITY_ACCOUNT_READ = "ACCOUNT_READ"
CAPABILITY_BALANCE_READ = "BALANCE_READ"
CAPABILITY_SYMBOL_INFO = "SYMBOL_INFO"
CAPABILITY_TRADING_CONSTRAINTS = "TRADING_CONSTRAINTS"
CAPABILITY_ORDER_SUBMISSION = "ORDER_SUBMISSION"
CAPABILITY_ORDER_CANCELLATION = "ORDER_CANCELLATION"
CAPABILITY_WITHDRAWAL = "WITHDRAWAL"

CANONICAL_CAPABILITIES = (
    CAPABILITY_PUBLIC_MARKET_DATA,
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
)


# ============================================================
# CANONICAL INTERFACE
# ============================================================

class ExchangeAdapter(ABC):

    @abstractmethod
    def get_account(self) -> CanonicalResult:
        raise NotImplementedError

    @abstractmethod
    def get_balances(self) -> CanonicalResult:
        raise NotImplementedError

    @abstractmethod
    def get_exchange_info(self) -> CanonicalResult:
        raise NotImplementedError

    @abstractmethod
    def validate_symbol(
        self,
        symbol: str,
    ) -> CanonicalResult:
        raise NotImplementedError

    @abstractmethod
    def get_trading_constraints(
        self,
        symbol: str,
    ) -> CanonicalResult:
        raise NotImplementedError

    @abstractmethod
    def submit_order(self, request: CanonicalOrderRequest) -> CanonicalExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        raise NotImplementedError


# ============================================================
# CANONICAL DATA BUILDERS
# ============================================================

def canonical_account(
    *,
    account_type: Any = None,
    can_trade: Any = None,
    status: Any = None,
    source: Any = None,
) -> Dict[str, Any]:
    return {
        "account_type": account_type,
        "can_trade": can_trade,
        "status": status,
        "source": source,
    }


def canonical_balance(
    *,
    asset: Any = None,
    free: Any = None,
    locked: Any = None,
    total: Any = None,
    source: Any = None,
) -> Dict[str, Any]:
    return {
        "asset": asset,
        "free": free,
        "locked": locked,
        "total": total,
        "source": source,
    }


def canonical_symbol(
    *,
    symbol: Any = None,
    exists: Any = None,
    tradable: Any = None,
    status: Any = None,
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "exists": exists,
        "tradable": tradable,
        "status": status,
    }


def canonical_constraints(
    *,
    symbol: Any = None,
    filters: Any = None,
    min_qty: Any = None,
    max_qty: Any = None,
    step_size: Any = None,
    min_notional: Any = None,
    price_precision: Any = None,
    quantity_precision: Any = None,
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "filters": filters,
        "min_qty": min_qty,
        "max_qty": max_qty,
        "step_size": step_size,
        "min_notional": min_notional,
        "price_precision": price_precision,
        "quantity_precision": quantity_precision,
    }


# ============================================================
# RESULT HELPERS
# ============================================================

def unavailable_result(
    operation: str,
    reason: str,
    *,
    data: Optional[Dict[str, Any]] = None,
) -> CanonicalResult:
    return CanonicalResult(
        status="UNAVAILABLE",
        allowed=False,
        operation=operation,
        reason=reason,
        data=data,
    )


def blocked_result(
    operation: str,
    reason: str,
) -> CanonicalResult:
    return CanonicalResult(
        status="BLOCKED",
        allowed=False,
        operation=operation,
        reason=reason,
        data=None,
    )


# ============================================================
# CAPABILITY CONTRACT
# ============================================================

def readonly_capabilities(
    *,
    public_market_data: bool,
    account_read: bool,
    balance_read: bool,
    symbol_info: bool,
    trading_constraints: bool,
) -> Dict[str, bool]:

    return {
        CAPABILITY_PUBLIC_MARKET_DATA:
            bool(public_market_data),

        CAPABILITY_ACCOUNT_READ:
            bool(account_read),

        CAPABILITY_BALANCE_READ:
            bool(balance_read),

        CAPABILITY_SYMBOL_INFO:
            bool(symbol_info),

        CAPABILITY_TRADING_CONSTRAINTS:
            bool(trading_constraints),

        CAPABILITY_ORDER_SUBMISSION: False,
        CAPABILITY_ORDER_CANCELLATION: False,
        CAPABILITY_WITHDRAWAL: False,
    }


def validate_capabilities(
    capabilities: Dict[str, bool],
) -> CanonicalResult:

    missing = [
        key
        for key in CANONICAL_CAPABILITIES
        if key not in capabilities
    ]

    if missing:
        return CanonicalResult(
            status="FAIL",
            allowed=False,
            operation="capabilities",
            reason=f"Missing capability keys: {missing}",
        )

    forbidden_enabled = [
        key
        for key in (
            CAPABILITY_ORDER_SUBMISSION,
            CAPABILITY_ORDER_CANCELLATION,
            CAPABILITY_WITHDRAWAL,
        )
        if capabilities.get(key) is not False
    ]

    if forbidden_enabled:
        return CanonicalResult(
            status="FAIL",
            allowed=False,
            operation="capabilities",
            reason=(
                "Read-only boundary violation: "
                f"{forbidden_enabled}"
            ),
        )

    return CanonicalResult(
        status="PASS",
        allowed=True,
        operation="capabilities",
        reason="Canonical read-only capability contract valid",
        data=dict(capabilities),
    )


# ============================================================
# LEGACY ADAPTER BRIDGE
# ============================================================

class AdapterBridge(ExchangeAdapter):
    """
    Exchange-agnostic bridge.

    The concrete adapter is injected from outside.
    No exchange name, endpoint, header, API format, or
    authentication mechanism exists here.
    """

    def __init__(
        self,
        *,
        account_reader: Callable[[], Any],
        balance_reader: Callable[[], Any],
        exchange_info_reader: Callable[[], Any],
        symbol_validator: Callable[[str], Any],
        constraints_reader: Callable[[str], Any],
        capability_map: Dict[str, bool],
        account_mapper: Callable[[Any], CanonicalResult],
        balance_mapper: Callable[[Any], CanonicalResult],
        exchange_info_mapper: Callable[[Any], CanonicalResult],
        symbol_mapper: Callable[[Any], CanonicalResult],
        constraints_mapper: Callable[[Any], CanonicalResult],
    ) -> None:

        self._account_reader = account_reader
        self._balance_reader = balance_reader
        self._exchange_info_reader = exchange_info_reader
        self._symbol_validator = symbol_validator
        self._constraints_reader = constraints_reader

        self._account_mapper = account_mapper
        self._balance_mapper = balance_mapper
        self._exchange_info_mapper = exchange_info_mapper
        self._symbol_mapper = symbol_mapper
        self._constraints_mapper = constraints_mapper

        self._capability_map = dict(capability_map)

    def get_account(self) -> CanonicalResult:
        return self._account_mapper(
            self._account_reader()
        )

    def get_balances(self) -> CanonicalResult:
        return self._balance_mapper(
            self._balance_reader()
        )

    def get_exchange_info(self) -> CanonicalResult:
        return self._exchange_info_mapper(
            self._exchange_info_reader()
        )

    def validate_symbol(
        self,
        symbol: str,
    ) -> CanonicalResult:
        return self._symbol_mapper(
            self._symbol_validator(symbol)
        )

    def get_trading_constraints(
        self,
        symbol: str,
    ) -> CanonicalResult:
        return self._constraints_mapper(
            self._constraints_reader(symbol)
        )

    def capabilities(self) -> Dict[str, bool]:
        return dict(self._capability_map)


# ============================================================
# SAFETY CONTRACT
# ============================================================

EXECUTION_ENABLED = False
ORDER_SUBMISSION_ENABLED = False
ORDER_CANCELLATION_ENABLED = False
WITHDRAWAL_ENABLED = False
DATABASE_WRITE_ENABLED = False
EXCHANGE_WRITE_ENABLED = False


def boundary_safety_contract() -> Dict[str, bool]:
    return {
        "EXECUTION_ENABLED": False,
        "ORDER_SUBMISSION_ENABLED": False,
        "ORDER_CANCELLATION_ENABLED": False,
        "WITHDRAWAL_ENABLED": False,
        "DATABASE_WRITE_ENABLED": False,
        "EXCHANGE_WRITE_ENABLED": False,
    }


# ============================================================
# MODULE SELF-CHECK
# ============================================================

def self_check() -> CanonicalResult:

    capabilities = readonly_capabilities(
        public_market_data=False,
        account_read=False,
        balance_read=False,
        symbol_info=False,
        trading_constraints=False,
    )

    capability_check = validate_capabilities(
        capabilities
    )

    if not capability_check.allowed:
        return capability_check

    safety = boundary_safety_contract()

    if any(safety.values()):
        return CanonicalResult(
            status="FAIL",
            allowed=False,
            operation="self_check",
            reason="Read-only safety contract violated",
            data=safety,
        )

    return CanonicalResult(
        status="PASS",
        allowed=True,
        operation="self_check",
        reason="Exchange-agnostic read-only boundary valid",
        data={
            "capabilities": capabilities,
            "safety": safety,
        },
    )
