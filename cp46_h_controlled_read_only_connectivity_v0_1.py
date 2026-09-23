"""CP46-H controlled read-only exchange connectivity contract.

Static/provider-neutral gate for the existing Toobit read-only adapter.
This module performs no network, database, order, or exchange write I/O.
Live provider verification is a separate explicitly authorized runtime step.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from toobit_trading_adapter import ToobitTradingAdapter


class ReadOnlyConnectivityStatus:
    PASS = "PASS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ReadOnlyConnectivityResult:
    status: str
    reason: str
    message: str


REQUIRED_READ_METHODS = (
    "get_account",
    "get_balances",
    "symbol_check",
    "trading_constraints",
    "server_time",
)


def verify_read_only_connectivity_contract(
    adapter: Any,
) -> ReadOnlyConnectivityResult:
    """Verify the existing adapter is structurally safe for read-only use.

    This is intentionally static: it does not call the adapter and therefore
    cannot claim that live credentials or the provider are reachable.
    """
    if not isinstance(adapter, ToobitTradingAdapter):
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "ADAPTER_INVALID",
            "Existing ToobitTradingAdapter is required.",
        )

    if adapter.execution_enabled is not False:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "EXECUTION_STATE_INVALID",
            "Execution must remain disabled.",
        )
    if adapter.order_submission_enabled is not False:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "ORDER_SUBMISSION_STATE_INVALID",
            "Order submission must remain disabled.",
        )
    if adapter.exchange_write_enabled is not False:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "EXCHANGE_WRITE_STATE_INVALID",
            "Exchange write must remain disabled.",
        )
    if adapter.database_write_enabled is not False:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "DATABASE_WRITE_STATE_INVALID",
            "Database write must remain disabled.",
        )

    capabilities = adapter.capabilities()
    if capabilities.get("ACCOUNT_READ") is not True:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "ACCOUNT_READ_CAPABILITY_MISSING",
            "Authenticated account read capability is required.",
        )
    if capabilities.get("BALANCE_READ") is not True:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "BALANCE_READ_CAPABILITY_MISSING",
            "Balance read capability is required.",
        )

    missing = tuple(
        name for name in REQUIRED_READ_METHODS
        if not callable(getattr(adapter, name, None))
    )
    if missing:
        return ReadOnlyConnectivityResult(
            ReadOnlyConnectivityStatus.BLOCK,
            "READ_METHOD_MISSING",
            "Required read-only adapter method is missing: "
            + ", ".join(missing),
        )

    return ReadOnlyConnectivityResult(
        ReadOnlyConnectivityStatus.PASS,
        "READ_ONLY_CONTRACT_READY",
        "Existing Toobit adapter is structurally ready for "
        "separately authorized live read-only verification.",
    )


__all__ = [
    "ReadOnlyConnectivityStatus",
    "ReadOnlyConnectivityResult",
    "REQUIRED_READ_METHODS",
    "verify_read_only_connectivity_contract",
]
