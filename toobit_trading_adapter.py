
"""
ARUNDA TRADER — TOOBIT TRADING ADAPTER v0.2
============================================================
MODE        : READ-ONLY CONTRACT INTEGRATION
EXCHANGE    : Toobit
EXECUTION   : DISABLED
ORDER WRITE : FORBIDDEN
WITHDRAW    : FORBIDDEN
DATABASE    : NO WRITE

Purpose:
    Exchange-agnostic read-only boundary between ArundaTrader
    and Toobit Spot API.

v0.2 repair:
    - Exact signed-query construction
    - Exact query reused for HMAC and HTTP request
    - No sorted() parameter reordering
    - Server-time synchronized timestamp
    - recvWindow included in signed USER_DATA requests
    - No requests parameter re-encoding of signed query
    - Diagnostic HTTP/API error payload preserved
    - No execution surface added

Hard rules:
    - No order submission
    - No order cancellation
    - No withdrawal
    - No exchange write
    - No database write
    - No synthetic values
    - No fallback values
    - No modification of core production layers
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests


# ============================================================
# CONTRACT CONSTANTS
# ============================================================

ADAPTER_VERSION = "TOOBIT_ADAPTER_v0.2"
EXCHANGE_NAME = "TOOBIT"

BASE_URL = "https://api.toobit.com"

EXECUTION_ENABLED = False

ORDER_SUBMISSION_ENABLED = False
ORDER_CANCELLATION_ENABLED = False
WITHDRAW_ENABLED = False

PRIVATE_API_ENABLED = True
ACCOUNT_API_ENABLED = True

DATABASE_WRITE_ENABLED = False
EXCHANGE_WRITE_ENABLED = False

RECV_WINDOW = 5000
HTTP_TIMEOUT = 15

EXPECTED_ASSETS = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
)

# Public
TIME_ENDPOINT = "/api/v1/time"
EXCHANGE_INFO_ENDPOINT = "/api/v1/exchangeInfo"

# Signed USER_DATA
ACCOUNT_ENDPOINT = "/api/v1/account"
API_KEY_CHECK_ENDPOINT = "/api/v1/account/checkApiKey"


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

class ToobitTradingAdapter:
    """
    Read-only Toobit exchange boundary.

    Allowed:
        - public server time
        - public exchange information
        - symbol discovery
        - trading constraints
        - authenticated account read
        - authenticated API-key metadata read

    Forbidden:
        - order submission
        - order cancellation
        - withdrawal
        - any exchange write
        - database write
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: int = HTTP_TIMEOUT,
    ) -> None:

        self.adapter_version = ADAPTER_VERSION
        self.exchange = EXCHANGE_NAME
        self.base_url = BASE_URL
        self.timeout = timeout

        self.api_key = (
            api_key
            if api_key is not None
            else os.getenv("TOOBIT_API_KEY")
        )

        self.api_secret = (
            api_secret
            if api_secret is not None
            else os.getenv("TOOBIT_API_SECRET")
        )

        self.execution_enabled = EXECUTION_ENABLED
        self.order_submission_enabled = ORDER_SUBMISSION_ENABLED
        self.order_cancellation_enabled = ORDER_CANCELLATION_ENABLED
        self.withdraw_enabled = WITHDRAW_ENABLED

        self.private_api_enabled = PRIVATE_API_ENABLED
        self.account_api_enabled = ACCOUNT_API_ENABLED

        self.database_write_enabled = DATABASE_WRITE_ENABLED
        self.exchange_write_enabled = EXCHANGE_WRITE_ENABLED

        self.session = requests.Session()

    # ========================================================
    # CONTRACT STATUS
    # ========================================================

    def capabilities(self) -> Dict[str, bool]:
        return {
            "ACCOUNT_READ": True,
            "BALANCE_READ": True,
        }

    def get_account(self) -> AdapterResult:
        """Adapter-neutral account read backed by the existing Toobit check."""
        return self.account_check()

    def get_balances(self) -> AdapterResult:
        """Adapter-neutral balance read backed by the existing Toobit check."""
        return self.balance_check()

    def contract_status(self) -> AdapterResult:

        return AdapterResult(
            status="READY_READ_ONLY",
            allowed=True,
            operation="contract_status",
            reason=(
                "Toobit adapter contract is present and all "
                "exchange-write operations are disabled."
            ),
            data={
                "adapter_version": self.adapter_version,
                "exchange": self.exchange,
                "execution_enabled": self.execution_enabled,
                "order_submission_enabled":
                    self.order_submission_enabled,
                "order_cancellation_enabled":
                    self.order_cancellation_enabled,
                "withdraw_enabled":
                    self.withdraw_enabled,
                "private_api_enabled":
                    self.private_api_enabled,
                "account_api_enabled":
                    self.account_api_enabled,
                "database_write_enabled":
                    self.database_write_enabled,
                "exchange_write_enabled":
                    self.exchange_write_enabled,
            },
        )

    # ========================================================
    # CREDENTIAL PRESENCE
    # ========================================================

    def credential_presence(self) -> AdapterResult:
        """
        Local-only credential presence check.

        Secret values are never returned or printed.
        """

        api_key_present = bool(self.api_key)
        api_secret_present = bool(self.api_secret)

        return AdapterResult(
            status=(
                "READY"
                if api_key_present and api_secret_present
                else "MISSING"
            ),
            allowed=True,
            operation="credential_presence",
            reason="Credential presence checked locally only.",
            data={
                "api_key_present": api_key_present,
                "api_secret_present": api_secret_present,
            },
        )

    # ========================================================
    # HTTP HELPERS
    # ========================================================

    def _public_get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:

        url = self.base_url + endpoint

        return self.session.get(
            url,
            params=params or {},
            timeout=self.timeout,
        )

    # ========================================================
    # EXACT QUERY ENCODER
    # ========================================================

    @staticmethod
    def _encode_query_value(value: Any) -> str:
        """
        Encode exactly one query value.

        quote(..., safe='') is used so the resulting value is
        deterministic and suitable for both signing and URL use.
        """

        return quote(
            str(value),
            safe="",
        )

    def _build_query_string(
        self,
        payload: Dict[str, Any],
    ) -> str:
        """
        Build ONE deterministic query string.

        IMPORTANT:
            - preserves dictionary insertion order
            - does not sort
            - excludes no fields implicitly
            - this exact string is used for HMAC
            - this exact string is also sent to the server
        """

        parts: List[str] = []

        for key, value in payload.items():

            if value is None:
                continue

            parts.append(
                f"{key}={self._encode_query_value(value)}"
            )

        return "&".join(parts)

    # ========================================================
    # SERVER TIME FOR SIGNED REQUESTS
    # ========================================================

    def _get_server_timestamp_ms(self) -> int:
        """
        Read Toobit's public server timestamp.

        No fallback to local time is permitted here.
        If server time cannot be obtained, the signed request
        fails closed.
        """

        response = self._public_get(TIME_ENDPOINT)

        if response.status_code != 200:
            raise RuntimeError(
                "Unable to obtain Toobit server time. "
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Toobit server time response is not an object."
            )

        timestamp = payload.get("serverTime")

        if timestamp is None:
            timestamp = payload.get("timestamp")

        if timestamp is None:
            raise RuntimeError(
                "Toobit server time response does not contain "
                "serverTime/timestamp."
            )

        try:
            timestamp_int = int(timestamp)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "Toobit server timestamp is invalid."
            ) from exc

        if timestamp_int <= 0:
            raise RuntimeError(
                "Toobit server timestamp is non-positive."
            )

        return timestamp_int

    # ========================================================
    # SIGNATURE
    # ========================================================

    def _generate_signature(
        self,
        query_string: str,
    ) -> str:
        """
        HMAC SHA256 over the exact query string.

        Signature field itself is NOT included in query_string.
        """

        if not self.api_secret:
            raise RuntimeError(
                "TOOBIT_API_SECRET is required for signature."
            )

        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # ========================================================
    # SIGNED GET — READ ONLY
    # ========================================================

    def _signed_get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Exact Toobit signed GET implementation.

        Security properties:
            1. timestamp is mandatory
            2. timestamp comes from Toobit server time
            3. recvWindow is included in the signed payload
            4. query string is built exactly once
            5. HMAC is calculated over that exact query string
            6. signature is appended AFTER signing
            7. the same query string is used in the actual URL
            8. requests does NOT rebuild/reorder the signed query
        """

        if not self.api_key or not self.api_secret:
            raise RuntimeError(
                "TOOBIT_API_KEY / TOOBIT_API_SECRET are required "
                "for signed read-only endpoint."
            )

        payload: Dict[str, Any] = dict(params or {})

        # ----------------------------------------------------
        # Mandatory timestamp.
        #
        # IMPORTANT:
        # Do not use local machine time here.
        # ----------------------------------------------------

        payload["timestamp"] = (
            self._get_server_timestamp_ms()
        )

        # ----------------------------------------------------
        # Signed recvWindow.
        #
        # This value is part of the exact query string that
        # is signed and then sent to Toobit.
        # ----------------------------------------------------

        payload["recvWindow"] = RECV_WINDOW

        # ----------------------------------------------------
        # Build EXACT string used for HMAC.
        # ----------------------------------------------------

        query_string = self._build_query_string(
            payload
        )

        if not query_string:
            raise RuntimeError(
                "Signed query string is unexpectedly empty."
            )

        # ----------------------------------------------------
        # Generate HMAC over EXACT query string.
        # ----------------------------------------------------

        signature = self._generate_signature(
            query_string
        )

        # ----------------------------------------------------
        # Build final request URL manually.
        #
        # DO NOT use requests params= here.
        # This guarantees the exact signed string reaches
        # Toobit without reordering/re-encoding.
        # ----------------------------------------------------

        final_query_string = (
            f"{query_string}&signature={signature}"
        )

        url = (
            f"{self.base_url}"
            f"{endpoint}"
            f"?{final_query_string}"
        )

        headers = {
            "X-BB-APIKEY": self.api_key,
        }

        return self.session.get(
            url,
            headers=headers,
            timeout=self.timeout,
        )

    # ========================================================
    # RESPONSE DIAGNOSTICS
    # ========================================================

    @staticmethod
    def _response_data(
        response: requests.Response,
    ) -> Dict[str, Any]:
        """
        Extract safe diagnostic information.

        Never includes API key or API secret.
        """

        data: Dict[str, Any] = {
            "http_status": response.status_code,
        }

        try:
            payload = response.json()

            if isinstance(payload, dict):

                if "code" in payload:
                    data["api_code"] = payload.get("code")

                if "msg" in payload:
                    data["api_message"] = payload.get("msg")

                data["response"] = payload

            else:
                data["response"] = payload

        except ValueError:
            data["response_text"] = response.text[:1000]

        return data

    # ========================================================
    # SERVER TIME
    # ========================================================

    def get_server_time(self) -> AdapterResult:

        try:

            response = self._public_get(
                TIME_ENDPOINT
            )

            if response.status_code != 200:

                return AdapterResult(
                    status="HTTP_ERROR",
                    allowed=False,
                    operation="get_server_time",
                    reason=(
                        f"Toobit server time returned HTTP "
                        f"{response.status_code}."
                    ),
                    data=self._response_data(response),
                )

            data = response.json()

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="get_server_time",
                reason=(
                    "Toobit public server time is reachable."
                ),
                data=data,
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="get_server_time",
                reason=(
                    f"Server time request failed: {exc}"
                ),
            )

    # ========================================================
    # EXCHANGE INFO
    # ========================================================

    def get_exchange_info(self) -> AdapterResult:

        try:

            response = self._public_get(
                EXCHANGE_INFO_ENDPOINT
            )

            if response.status_code != 200:

                return AdapterResult(
                    status="HTTP_ERROR",
                    allowed=False,
                    operation="get_exchange_info",
                    reason=(
                        f"Toobit exchangeInfo returned HTTP "
                        f"{response.status_code}."
                    ),
                    data=self._response_data(response),
                )

            payload = response.json()

            symbols = payload.get("symbols")

            if not isinstance(symbols, list):

                return AdapterResult(
                    status="INVALID_RESPONSE",
                    allowed=False,
                    operation="get_exchange_info",
                    reason=(
                        "exchangeInfo.symbols is not a list."
                    ),
                )

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="get_exchange_info",
                reason=(
                    "Toobit exchange information is valid."
                ),
                data={
                    "symbol_count": len(symbols),
                    "symbols": symbols,
                },
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="get_exchange_info",
                reason=(
                    f"Exchange info request failed: {exc}"
                ),
            )

    # ========================================================
    # SYMBOL MAP
    # ========================================================

    def _load_symbol_map(
        self,
    ) -> Dict[str, Dict[str, Any]]:

        result = self.get_exchange_info()

        if not result.allowed or not result.data:
            raise RuntimeError(result.reason)

        symbols = result.data.get(
            "symbols",
            [],
        )

        symbol_map: Dict[str, Dict[str, Any]] = {}

        for row in symbols:

            if not isinstance(row, dict):
                continue

            symbol = row.get("symbol")

            if not isinstance(symbol, str):
                continue

            symbol_map[symbol.upper()] = row

        return symbol_map

    # ========================================================
    # SYMBOL CHECK
    # ========================================================

    def symbol_check(
        self,
        asset: str,
    ) -> AdapterResult:

        if (
            not isinstance(asset, str)
            or not asset.strip()
        ):

            return AdapterResult(
                status="INVALID",
                allowed=False,
                operation="symbol_check",
                reason=(
                    "Asset symbol is missing or invalid."
                ),
            )

        asset = asset.upper().strip()
        symbol = f"{asset}USDT"

        try:

            symbol_map = self._load_symbol_map()

            row = symbol_map.get(symbol)

            if row is None:

                return AdapterResult(
                    status="NOT_FOUND",
                    allowed=False,
                    operation="symbol_check",
                    reason=(
                        f"Toobit spot symbol {symbol} "
                        "was not found in exchangeInfo."
                    ),
                    data={
                        "asset": asset,
                        "symbol": symbol,
                    },
                )

            status = str(
                row.get("status", "")
            ).upper()

            if status != "TRADING":

                return AdapterResult(
                    status="NOT_TRADING",
                    allowed=False,
                    operation="symbol_check",
                    reason=(
                        f"Toobit symbol {symbol} exists "
                        "but is not TRADING."
                    ),
                    data={
                        "asset": asset,
                        "symbol": symbol,
                        "status": status,
                    },
                )

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="symbol_check",
                reason=(
                    "Verified active Toobit spot symbol."
                ),
                data={
                    "asset": asset,
                    "symbol": symbol,
                    "status": status,
                    "base_asset": row.get("baseAsset"),
                    "quote_asset": row.get("quoteAsset"),
                },
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="symbol_check",
                reason=(
                    f"Symbol validation failed: {exc}"
                ),
            )

    # ========================================================
    # SYMBOL CONTRACT — 15 PRODUCTION ASSETS
    # ========================================================

    def validate_expected_symbols(self) -> AdapterResult:

        try:

            symbol_map = self._load_symbol_map()

            rows: List[Dict[str, Any]] = []
            missing: List[str] = []
            not_trading: List[str] = []
            invalid: List[str] = []

            for asset in EXPECTED_ASSETS:

                symbol = f"{asset}USDT"
                row = symbol_map.get(symbol)

                if row is None:
                    missing.append(asset)
                    continue

                status = str(
                    row.get("status", "")
                ).upper()

                if status != "TRADING":
                    not_trading.append(asset)
                    continue

                filters = row.get("filters")

                if not isinstance(filters, list):
                    invalid.append(asset)
                    continue

                rows.append(
                    {
                        "asset": asset,
                        "symbol": symbol,
                        "status": status,
                        "filters_count": len(filters),
                    }
                )

            passed = (
                len(rows) == len(EXPECTED_ASSETS)
                and not missing
                and not not_trading
                and not invalid
            )

            return AdapterResult(
                status="PASS" if passed else "FAIL",
                allowed=passed,
                operation="validate_expected_symbols",
                reason=(
                    "All expected production assets have "
                    "verified active Toobit spot contracts."
                    if passed
                    else
                    "One or more expected production asset "
                    "contracts failed validation."
                ),
                data={
                    "expected_count":
                        len(EXPECTED_ASSETS),
                    "validated_count":
                        len(rows),
                    "missing": missing,
                    "not_trading": not_trading,
                    "invalid": invalid,
                    "symbols": rows,
                },
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="validate_expected_symbols",
                reason=(
                    f"Expected-symbol validation failed: {exc}"
                ),
            )

    # ========================================================
    # TRADING CONSTRAINTS
    # ========================================================

    def trading_constraints(
        self,
        asset: str,
    ) -> AdapterResult:

        symbol_result = self.symbol_check(asset)

        if (
            not symbol_result.allowed
            or not symbol_result.data
        ):

            return AdapterResult(
                status="UNAVAILABLE",
                allowed=False,
                operation="trading_constraints",
                reason=symbol_result.reason,
            )

        symbol = symbol_result.data["symbol"]

        try:

            symbol_map = self._load_symbol_map()

            row = symbol_map.get(symbol)

            if row is None:

                return AdapterResult(
                    status="NOT_FOUND",
                    allowed=False,
                    operation="trading_constraints",
                    reason=(
                        f"Symbol {symbol} disappeared "
                        "from exchangeInfo."
                    ),
                )

            filters = row.get("filters")

            if (
                not isinstance(filters, list)
                or not filters
            ):

                return AdapterResult(
                    status="INVALID",
                    allowed=False,
                    operation="trading_constraints",
                    reason=(
                        f"No valid filters were returned "
                        f"for {symbol}."
                    ),
                )

            normalized_filters: Dict[
                str,
                Dict[str, Any],
            ] = {}

            for item in filters:

                if not isinstance(item, dict):
                    continue

                filter_type = item.get(
                    "filterType"
                )

                if not isinstance(
                    filter_type,
                    str,
                ):
                    continue

                normalized_filters[
                    filter_type
                ] = dict(item)

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="trading_constraints",
                reason=(
                    f"Trading constraints verified "
                    f"for {symbol}."
                ),
                data={
                    "asset": asset.upper(),
                    "symbol": symbol,
                    "status": row.get("status"),
                    "filters": normalized_filters,
                },
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="trading_constraints",
                reason=(
                    f"Trading constraint request failed: "
                    f"{exc}"
                ),
            )

    # ========================================================
    # ACCOUNT READ
    # ========================================================

    def account_check(self) -> AdapterResult:

        if (
            not self.api_key
            or not self.api_secret
        ):

            return AdapterResult(
                status="MISSING_CREDENTIALS",
                allowed=False,
                operation="account_check",
                reason=(
                    "Toobit API credentials are not available."
                ),
            )

        try:

            response = self._signed_get(
                ACCOUNT_ENDPOINT
            )

            if response.status_code != 200:

                response_data = self._response_data(
                    response
                )

                return AdapterResult(
                    status="HTTP_ERROR",
                    allowed=False,
                    operation="account_check",
                    reason=(
                        f"Toobit account endpoint returned "
                        f"HTTP {response.status_code}."
                    ),
                    data=response_data,
                )

            payload = response.json()

            if not isinstance(payload, dict):

                return AdapterResult(
                    status="INVALID_RESPONSE",
                    allowed=False,
                    operation="account_check",
                    reason=(
                        "Account response is not an object."
                    ),
                )

            balances = payload.get("balances")

            if (
                balances is not None
                and not isinstance(
                    balances,
                    list,
                )
            ):

                return AdapterResult(
                    status="INVALID_RESPONSE",
                    allowed=False,
                    operation="account_check",
                    reason=(
                        "Account balances field is invalid."
                    ),
                )

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="account_check",
                reason=(
                    "Authenticated Toobit account "
                    "read succeeded."
                ),
                data={
                    "account_response": payload,
                    "balance_rows": (
                        len(balances)
                        if isinstance(
                            balances,
                            list,
                        )
                        else None
                    ),
                },
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="account_check",
                reason=(
                    f"Account read failed: {exc}"
                ),
            )

    # ========================================================
    # BALANCE CHECK
    # ========================================================

    def balance_check(self) -> AdapterResult:

        result = self.account_check()

        if (
            not result.allowed
            or not result.data
        ):

            return AdapterResult(
                status="UNAVAILABLE",
                allowed=False,
                operation="balance_check",
                reason=result.reason,
                data=result.data,
            )

        payload = result.data.get(
            "account_response",
            {},
        )

        balances = payload.get("balances")

        if balances is None:

            return AdapterResult(
                status="PASS_NO_BALANCE_FIELD",
                allowed=True,
                operation="balance_check",
                reason=(
                    "Account read succeeded but no "
                    "balances field was returned."
                ),
            )

        nonzero = []

        for row in balances:

            if not isinstance(row, dict):
                continue

            total = row.get("total")

            try:

                if (
                    total is not None
                    and float(total) != 0
                ):

                    nonzero.append(
                        {
                            "coin": row.get("coin"),
                            "total": total,
                            "free": row.get("free"),
                            "locked": row.get("locked"),
                        }
                    )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return AdapterResult(
            status="PASS",
            allowed=True,
            operation="balance_check",
            reason=(
                "Account balances were read successfully."
            ),
            data={
                "balance_rows": len(balances),
                "nonzero_balances": nonzero,
                "nonzero_count": len(nonzero),
            },
        )

    # ========================================================
    # API KEY CHECK
    # ========================================================

    def api_key_check(self) -> AdapterResult:

        if (
            not self.api_key
            or not self.api_secret
        ):

            return AdapterResult(
                status="MISSING_CREDENTIALS",
                allowed=False,
                operation="api_key_check",
                reason=(
                    "Toobit API credentials are not available."
                ),
            )

        try:

            response = self._signed_get(
                API_KEY_CHECK_ENDPOINT
            )

            if response.status_code != 200:

                response_data = self._response_data(
                    response
                )

                return AdapterResult(
                    status="HTTP_ERROR",
                    allowed=False,
                    operation="api_key_check",
                    reason=(
                        f"Toobit checkApiKey returned "
                        f"HTTP {response.status_code}."
                    ),
                    data=response_data,
                )

            payload = response.json()

            if not isinstance(payload, dict):

                return AdapterResult(
                    status="INVALID_RESPONSE",
                    allowed=False,
                    operation="api_key_check",
                    reason=(
                        "API-key response is not an object."
                    ),
                )

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="api_key_check",
                reason=(
                    "Authenticated API-key read succeeded."
                ),
                data={
                    "account_type":
                        payload.get("accountType"),
                    "response": payload,
                },
            )

        except Exception as exc:

            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="api_key_check",
                reason=(
                    f"API-key check failed: {exc}"
                ),
            )

    # ========================================================
    # DUPLICATE CHECK — FAIL CLOSED
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
                "Open-order/private order-state integration "
                "is not part of TOOBIT_ADAPTER_v0.2. "
                "Duplicate protection therefore fails closed."
            ),
            data={
                "asset": (
                    asset.upper()
                    if isinstance(asset, str)
                    else asset
                ),
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
                "ORDER SUBMISSION IS DISABLED IN "
                "TOOBIT_ADAPTER_v0.2. "
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
                "ORDER CANCELLATION IS DISABLED IN "
                "TOOBIT_ADAPTER_v0.2. "
                "No exchange request is generated."
            ),
        )

    # ========================================================
    # WITHDRAWAL — HARD BLOCK
    # ========================================================

    def withdraw(
        self,
        request: Dict[str, Any],
    ) -> AdapterResult:

        return AdapterResult(
            status="BLOCKED",
            allowed=False,
            operation="withdraw",
            reason=(
                "WITHDRAWAL IS DISABLED IN "
                "TOOBIT_ADAPTER_v0.2. "
                "No exchange request is generated."
            ),
        )

    # ========================================================
    # READ-ONLY PREFLIGHT
    # ========================================================

    def read_only_preflight(
        self,
        asset: Optional[str] = None,
    ) -> Dict[str, Any]:

        result: Dict[str, Any] = {
            "adapter_version":
                self.adapter_version,

            "exchange":
                self.exchange,

            "execution_enabled":
                self.execution_enabled,

            "order_submission_enabled":
                self.order_submission_enabled,

            "order_cancellation_enabled":
                self.order_cancellation_enabled,

            "withdraw_enabled":
                self.withdraw_enabled,

            "private_api_enabled":
                self.private_api_enabled,

            "account_api_enabled":
                self.account_api_enabled,

            "database_write_enabled":
                self.database_write_enabled,

            "exchange_write_enabled":
                self.exchange_write_enabled,

            "contract":
                self.contract_status().__dict__,

            "credentials":
                self.credential_presence().__dict__,

            "server_time":
                self.get_server_time().__dict__,

            "exchange_info":
                self.get_exchange_info().__dict__,

            "expected_symbols":
                self.validate_expected_symbols().__dict__,

            "account":
                self.account_check().__dict__,

            "balance":
                self.balance_check().__dict__,

            "api_key":
                self.api_key_check().__dict__,
        }

        if asset:

            result["symbol"] = (
                self.symbol_check(asset).__dict__
            )

            result["constraints"] = (
                self.trading_constraints(asset).__dict__
            )

        return result


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> int:

    adapter = ToobitTradingAdapter()

    contract = adapter.contract_status()

    assert contract.allowed is True

    assert adapter.execution_enabled is False
    assert adapter.order_submission_enabled is False
    assert adapter.order_cancellation_enabled is False
    assert adapter.withdraw_enabled is False

    assert adapter.private_api_enabled is True
    assert adapter.account_api_enabled is True

    assert adapter.database_write_enabled is False
    assert adapter.exchange_write_enabled is False

    # --------------------------------------------------------
    # Hard safety tests
    # --------------------------------------------------------

    order_test = adapter.place_order(
        {
            "asset": "UNI",
            "direction": "LONG",
            "entry_price": 1.0,
        }
    )

    assert order_test.allowed is False
    assert order_test.status == "BLOCKED"

    cancel_test = adapter.cancel_order(
        "TEST"
    )

    assert cancel_test.allowed is False
    assert cancel_test.status == "BLOCKED"

    withdraw_test = adapter.withdraw(
        {
            "coin": "USDT",
            "amount": 1,
        }
    )

    assert withdraw_test.allowed is False
    assert withdraw_test.status == "BLOCKED"

    # --------------------------------------------------------
    # Local signature construction test
    # --------------------------------------------------------

    test_query = (
        "timestamp=1700000000000"
        "&recvWindow=5000"
    )

    test_signature = (
        adapter._generate_signature(
            test_query
        )
        if adapter.api_secret
        else None
    )

    if adapter.api_secret:

        assert isinstance(
            test_signature,
            str,
        )

        assert len(test_signature) == 64

        assert test_signature.lower() == (
            test_signature
        )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print("=" * 80)
    print(
        "ARUNDA TRADER — TOOBIT TRADING ADAPTER v0.2"
    )
    print("=" * 80)

    print(
        "STATUS                 : READY_READ_ONLY"
    )

    print(
        "EXCHANGE               :",
        adapter.exchange,
    )

    print(
        "EXECUTION_ENABLED      :",
        adapter.execution_enabled,
    )

    print(
        "ORDER_SUBMISSION       :",
        adapter.order_submission_enabled,
    )

    print(
        "ORDER_CANCELLATION     :",
        adapter.order_cancellation_enabled,
    )

    print(
        "WITHDRAW_ENABLED       :",
        adapter.withdraw_enabled,
    )

    print(
        "PRIVATE_API_ENABLED    :",
        adapter.private_api_enabled,
    )

    print(
        "ACCOUNT_API_ENABLED    :",
        adapter.account_api_enabled,
    )

    print(
        "DATABASE_WRITE         :",
        adapter.database_write_enabled,
    )

    print(
        "EXCHANGE_WRITE         :",
        adapter.exchange_write_enabled,
    )

    print(
        "SIGNED_QUERY_MODEL     : "
        "EXACT_MANUAL_QUERY"
    )

    print(
        "TIMESTAMP_SOURCE       : "
        "TOOBIT_SERVER_TIME"
    )

    print(
        "RECV_WINDOW_SIGNING    : "
        "INCLUDED_SIGNED_QUERY"
    )

    print(
        "PLACE_ORDER            : BLOCKED"
    )

    print(
        "CANCEL_ORDER           : BLOCKED"
    )

    print(
        "WITHDRAW               : BLOCKED"
    )

    print(
        "SELF TEST              : PASS"
    )

    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        self_test()
    )


def build_toobit_portfolio_observation(
    adapter: ToobitTradingAdapter,
    account_balance,
    *,
    portfolio_id=None,
):
    """Provider-local Toobit wiring.

    REAL ToobitTradingAdapter
        -> Toobit Position Reader
        -> provider-neutral Portfolio Observation
    """

    from portfolio_observation_v0_1 import build_portfolio_observation
    from toobit_position_reader_v0_1 import build_toobit_position_reader

    if not isinstance(adapter, ToobitTradingAdapter):
        raise TypeError(
            "adapter must be ToobitTradingAdapter"
        )

    position_reader = build_toobit_position_reader(adapter)

    return build_portfolio_observation(
        account_balance,
        position_reader=position_reader,
        portfolio_id=portfolio_id,
    )