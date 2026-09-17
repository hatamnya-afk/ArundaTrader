"""
ARUNDA TRADER — BITPIN TRADING ADAPTER v0.1
============================================================
MODE        : READ-ONLY CONTRACT
EXCHANGE    : Bitpin
EXECUTION   : DISABLED
ORDER WRITE : FORBIDDEN
ACCOUNT API : NOT IMPLEMENTED
PRIVATE API : NOT IMPLEMENTED

Purpose:
    Define the exchange-agnostic boundary between ArundaTrader
    and a future Bitpin execution adapter.

Hard rules:
    - No order submission
    - No order cancellation
    - No private API requests
    - No exchange writes
    - No database writes
    - No synthetic values
    - No modification of existing production layers
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


# ============================================================
# CONTRACT CONSTANTS
# ============================================================

ADAPTER_VERSION = "BITPIN_ADAPTER_v0.1"

EXCHANGE_NAME = "BITPIN"

EXECUTION_ENABLED = False

ORDER_SUBMISSION_ENABLED = False
ORDER_CANCELLATION_ENABLED = False

PRIVATE_API_ENABLED = False
ACCOUNT_API_ENABLED = False

DATABASE_WRITE_ENABLED = False
EXCHANGE_WRITE_ENABLED = False


# Public endpoints already verified in project
PUBLIC_MARKETS_URL = "https://api.bitpin.ir/v1/mkt/markets/"
PUBLIC_ORDERBOOK_URL = (
    "https://api.bitpin.ir/v4/mth/orderbook/{market_id}/?limit=50"
)


# ============================================================
# RESULT CONTRACT
# ============================================================

@dataclass(frozen=True)
class AdapterResult:
    status: str
    allowed: bool
    operation: str
    reason: str
    data: Optional[Dict[str, Any]] = None


# ============================================================
# ADAPTER
# ============================================================

class BitpinTradingAdapter:
    """
    Read-only Bitpin execution boundary.

    This class intentionally does NOT implement:
        - authenticated HTTP
        - private endpoints
        - order creation
        - order cancellation
        - exchange writes
    """

    def __init__(self) -> None:

        self.adapter_version = ADAPTER_VERSION
        self.exchange = EXCHANGE_NAME

        self.execution_enabled = EXECUTION_ENABLED
        self.order_submission_enabled = ORDER_SUBMISSION_ENABLED
        self.order_cancellation_enabled = ORDER_CANCELLATION_ENABLED

        self.private_api_enabled = PRIVATE_API_ENABLED
        self.account_api_enabled = ACCOUNT_API_ENABLED

        self.database_write_enabled = DATABASE_WRITE_ENABLED
        self.exchange_write_enabled = EXCHANGE_WRITE_ENABLED

    # ========================================================
    # CONTRACT STATUS
    # ========================================================

    def contract_status(self) -> AdapterResult:

        return AdapterResult(
            status="READY_READ_ONLY",
            allowed=True,
            operation="contract_status",
            reason="Bitpin adapter contract is present and execution is disabled.",
            data={
                "adapter_version": self.adapter_version,
                "exchange": self.exchange,
                "execution_enabled": self.execution_enabled,
                "order_submission_enabled": self.order_submission_enabled,
                "order_cancellation_enabled": self.order_cancellation_enabled,
                "private_api_enabled": self.private_api_enabled,
                "account_api_enabled": self.account_api_enabled,
                "database_write_enabled": self.database_write_enabled,
                "exchange_write_enabled": self.exchange_write_enabled,
            },
        )

    # ========================================================
    # CREDENTIAL PRESENCE
    # ========================================================

    def credential_presence(self) -> AdapterResult:
        """
        Checks only whether credential environment variables exist.

        No credential value is returned.
        No authentication request is sent.
        """

        api_key_present = bool(
            os.getenv("BITPIN_API_KEY")
        )

        api_secret_present = bool(
            os.getenv("BITPIN_API_SECRET")
        )

        return AdapterResult(
            status="READ_ONLY",
            allowed=True,
            operation="credential_presence",
            reason="Credential presence checked locally only.",
            data={
                "api_key_present": api_key_present,
                "api_secret_present": api_secret_present,
            },
        )

    # ========================================================
    # PUBLIC CONNECTIVITY CONTRACT
    # ========================================================

    def public_endpoints(self) -> AdapterResult:

        return AdapterResult(
            status="AVAILABLE",
            allowed=True,
            operation="public_endpoints",
            reason="Known public Bitpin endpoints are registered.",
            data={
                "markets": PUBLIC_MARKETS_URL,
                "orderbook": PUBLIC_ORDERBOOK_URL,
            },
        )

    # ========================================================
    # ACCOUNT CHECK
    # ========================================================

    def account_check(self) -> AdapterResult:

        return AdapterResult(
            status="NOT_IMPLEMENTED",
            allowed=False,
            operation="account_check",
            reason=(
                "Bitpin private account endpoint is not verified. "
                "Fail-closed."
            ),
        )

    # ========================================================
    # BALANCE CHECK
    # ========================================================

    def balance_check(self) -> AdapterResult:

        return AdapterResult(
            status="NOT_IMPLEMENTED",
            allowed=False,
            operation="balance_check",
            reason=(
                "Bitpin private balance endpoint is not verified. "
                "Fail-closed."
            ),
        )

    # ========================================================
    # SYMBOL / MARKET CONTRACT
    # ========================================================

    def symbol_check(
        self,
        asset: str,
    ) -> AdapterResult:

        if not asset or not isinstance(asset, str):

            return AdapterResult(
                status="INVALID",
                allowed=False,
                operation="symbol_check",
                reason="Asset symbol is missing or invalid.",
            )

        return AdapterResult(
            status="UNVERIFIED",
            allowed=False,
            operation="symbol_check",
            reason=(
                "Private trading-symbol validation is not implemented. "
                "Public market discovery exists separately."
            ),
            data={
                "asset": asset.upper(),
            },
        )

    # ========================================================
    # TRADING CONSTRAINTS
    # ========================================================

    def trading_constraints(
        self,
        asset: str,
    ) -> AdapterResult:

        return AdapterResult(
            status="UNAVAILABLE",
            allowed=False,
            operation="trading_constraints",
            reason=(
                "Authenticated Bitpin trading constraints are not "
                "verified. No assumptions are permitted."
            ),
            data={
                "asset": asset.upper()
                if isinstance(asset, str)
                else asset,
            },
        )

    # ========================================================
    # DUPLICATE / OPEN ORDER CHECK
    # ========================================================

    def duplicate_check(
        self,
        asset: str,
        direction: str,
    ) -> AdapterResult:

        return AdapterResult(
            status="UNAVAILABLE",
            allowed=False,
            operation="duplicate_check",
            reason=(
                "Private open-order/account state is not available. "
                "Duplicate protection therefore fails closed."
            ),
            data={
                "asset": asset.upper()
                if isinstance(asset, str)
                else asset,
                "direction": direction,
            },
        )

    # ========================================================
    # ORDER SUBMISSION — HARD BLOCK
    # ========================================================

    def place_order(
        self,
        order_intent: Dict[str, Any],
    ) -> AdapterResult:

        return AdapterResult(
            status="BLOCKED",
            allowed=False,
            operation="place_order",
            reason=(
                "ORDER SUBMISSION IS DISABLED IN BITPIN_ADAPTER_v0.1. "
                "No exchange request is generated."
            ),
        )

    # ========================================================
    # ORDER CANCELLATION — HARD BLOCK
    # ========================================================

    def cancel_order(
        self,
        order_id: str,
    ) -> AdapterResult:

        return AdapterResult(
            status="BLOCKED",
            allowed=False,
            operation="cancel_order",
            reason=(
                "ORDER CANCELLATION IS DISABLED IN BITPIN_ADAPTER_v0.1. "
                "No exchange request is generated."
            ),
        )

    # ========================================================
    # FULL READ-ONLY PREFLIGHT
    # ========================================================

    def read_only_preflight(
        self,
        asset: Optional[str] = None,
    ) -> Dict[str, Any]:

        result = {
            "adapter_version": self.adapter_version,
            "exchange": self.exchange,
            "execution_enabled": self.execution_enabled,
            "order_submission_enabled": self.order_submission_enabled,
            "order_cancellation_enabled": self.order_cancellation_enabled,
            "private_api_enabled": self.private_api_enabled,
            "account_api_enabled": self.account_api_enabled,
            "database_write_enabled": self.database_write_enabled,
            "exchange_write_enabled": self.exchange_write_enabled,

            "contract": self.contract_status().__dict__,
            "credentials": self.credential_presence().__dict__,
            "public_endpoints": self.public_endpoints().__dict__,
            "account": self.account_check().__dict__,
            "balance": self.balance_check().__dict__,
        }

        if asset:
            result["symbol"] = self.symbol_check(asset).__dict__
            result["constraints"] = (
                self.trading_constraints(asset).__dict__
            )

        return result


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> int:

    adapter = BitpinTradingAdapter()

    contract = adapter.contract_status()

    assert contract.allowed is True
    assert adapter.execution_enabled is False
    assert adapter.order_submission_enabled is False
    assert adapter.order_cancellation_enabled is False
    assert adapter.private_api_enabled is False
    assert adapter.account_api_enabled is False
    assert adapter.database_write_enabled is False
    assert adapter.exchange_write_enabled is False

    order_test = adapter.place_order({
        "asset": "UNI",
        "direction": "LONG",
        "entry_price": 1.0,
    })

    assert order_test.allowed is False
    assert order_test.status == "BLOCKED"

    cancel_test = adapter.cancel_order("TEST")

    assert cancel_test.allowed is False
    assert cancel_test.status == "BLOCKED"

    print("=" * 80)
    print("ARUNDA TRADER — BITPIN TRADING ADAPTER v0.1")
    print("=" * 80)
    print("STATUS                 : READY_READ_ONLY")
    print("EXECUTION_ENABLED      :", adapter.execution_enabled)
    print("ORDER_SUBMISSION      :", adapter.order_submission_enabled)
    print("ORDER_CANCELLATION    :", adapter.order_cancellation_enabled)
    print("PRIVATE_API_ENABLED    :", adapter.private_api_enabled)
    print("ACCOUNT_API_ENABLED    :", adapter.account_api_enabled)
    print("DATABASE_WRITE         :", adapter.database_write_enabled)
    print("EXCHANGE_WRITE         :", adapter.exchange_write_enabled)
    print("PLACE_ORDER            : BLOCKED")
    print("CANCEL_ORDER           : BLOCKED")
    print("SELF TEST              : PASS")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(self_test())