
"""
ARUNDA TRADER — TOOBIT TRADING ADAPTER v0.2
============================================================
MODE        : READ-ONLY + CONTROLLED LIVE ORDER TRANSPORT
EXCHANGE    : Toobit
EXECUTION   : FAIL-CLOSED BY DEFAULT
ORDER WRITE : CONTROLLED / DISABLED BY DEFAULT
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
    - Live spot order transport is an explicit, fail-closed execution surface

Hard rules:
    - No order submission unless explicit live transport flags are enabled
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

from cp49_first_execution_contract_v0_1 import (
    AttemptState,
    ExecutionSafetyGate,
)


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

# Public
TIME_ENDPOINT = "/api/v1/time"
EXCHANGE_INFO_ENDPOINT = "/api/v1/exchangeInfo"
DEPTH_ENDPOINT = "/quote/v1/depth"
BOOK_TICKER_ENDPOINT = "/quote/v1/ticker/bookTicker"
RECENT_TRADES_ENDPOINT = "/quote/v1/trades"

# Signed USER_DATA
ACCOUNT_ENDPOINT = "/api/v1/account"
ACCOUNT_BALANCE_FLOW_ENDPOINT = "/api/v1/account/balanceFlow"
API_KEY_CHECK_ENDPOINT = "/api/v1/account/checkApiKey"
OPEN_ORDERS_ENDPOINT = "/api/v1/spot/openOrders"
ALL_ORDERS_ENDPOINT = "/api/v1/spot/tradeOrders"

# Futures USER_DATA / read-only
FUTURES_BALANCE_ENDPOINT = "/api/v1/futures/balance"
FUTURES_ACCOUNT_LEVERAGE_ENDPOINT = "/api/v1/futures/accountLeverage"
FUTURES_OPEN_ORDERS_ENDPOINT = "/api/v1/futures/openOrders"
FUTURES_HISTORY_ORDERS_ENDPOINT = "/api/v1/futures/historyOrders"


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
    Toobit exchange boundary, fail-closed by default.

    Allowed:
        - public server time
        - public exchange information
        - symbol discovery
        - trading constraints
        - authenticated account read
        - authenticated API-key metadata read

    Forbidden by default:
        - order submission until explicit live transport enablement
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
        live_order_transport: Any = None,
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

        self.live_order_transport = live_order_transport
        self.live_order_transport_enabled = False
        self._first_execution_activated = False

        self.session = requests.Session()

    def authorize_first_execution(
        self,
        safety_gate: ExecutionSafetyGate,
    ) -> bool:
        """Apply the already-approved CP49 first-execution gate once."""
        if not isinstance(safety_gate, ExecutionSafetyGate):
            return False

        if safety_gate.validate() is not AttemptState.READY:
            return False

        if self._first_execution_activated:
            return False

        transport = self.live_order_transport
        if transport is None:
            return False

        self.execution_enabled = True
        self.order_submission_enabled = True
        self.exchange_write_enabled = True
        self.live_order_transport_enabled = True

        transport.transport_enabled = True
        transport.execution_enabled = True
        transport.order_submission_enabled = True
        transport.exchange_write_enabled = True
        self._first_execution_activated = True

        return True

    # ========================================================
    # CONTRACT STATUS
    # ========================================================

    def capabilities(self) -> Dict[str, bool]:
        return {
            "ACCOUNT_READ": True,
            "BALANCE_READ": True,
            "FUTURES_CONTRACT_READ": callable(getattr(self, "futures_trading_constraints", None)),
            "FUTURES_ACCOUNT_READ": callable(getattr(self, "futures_account_state", None)),
            "ORDER_SUBMISSION": (
                self.live_order_transport_enabled is True
                and self.live_order_transport is not None
                and self.execution_enabled is True
                and self.order_submission_enabled is True
                and self.exchange_write_enabled is True
            ),
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

        signed_timestamp_ms = self._get_server_timestamp_ms()
        self._last_signed_timestamp_ms = signed_timestamp_ms
        payload["timestamp"] = signed_timestamp_ms

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
                    "contract_count": (
                        len(payload.get("contracts", []))
                        if isinstance(payload.get("contracts"), list)
                        else None
                    ),
                    "contracts": (
                        payload.get("contracts")
                        if isinstance(payload.get("contracts"), list)
                        else None
                    ),
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
    # PUBLIC MARKET MICROSTRUCTURE — READ ONLY
    # ========================================================

    def _public_market_data(self, endpoint: str, symbol: str, limit: Optional[int] = None) -> AdapterResult:
        if not isinstance(symbol, str) or not symbol.strip():
            return AdapterResult("INVALID", False, "public_market_data", "Provider symbol is missing.")
        params = {"symbol": symbol.strip().upper()}
        if limit is not None:
            params["limit"] = limit
        try:
            response = self._public_get(endpoint, params=params)
            if response.status_code != 200:
                return AdapterResult("HTTP_ERROR", False, "public_market_data", f"Toobit market-data endpoint returned HTTP {response.status_code}.", self._response_data(response))
            payload = response.json()
            return AdapterResult("PASS", True, "public_market_data", "Toobit public market-data read succeeded.", {"payload": payload, "captured_at_ms": int(time.time() * 1000)})
        except Exception as exc:
            return AdapterResult("ERROR", False, "public_market_data", f"Market-data request failed: {exc}")

    def get_book_ticker(self, symbol: str) -> AdapterResult:
        return self._public_market_data(BOOK_TICKER_ENDPOINT, symbol)

    def get_depth(self, symbol: str, limit: int = 20) -> AdapterResult:
        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            return AdapterResult("INVALID", False, "get_depth", "Depth limit must be an integer in 1..100.")
        return self._public_market_data(DEPTH_ENDPOINT, symbol, limit)

    def get_recent_trades(self, symbol: str, limit: int = 60) -> AdapterResult:
        if not isinstance(limit, int) or limit <= 0 or limit > 60:
            return AdapterResult("INVALID", False, "get_recent_trades", "Recent-trades limit must be an integer in 1..60.")
        return self._public_market_data(RECENT_TRADES_ENDPOINT, symbol, limit)

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

        try:

            symbol_map = self._load_symbol_map()

            # Provider symbol identity is authoritative exchange metadata.
            # Do not reconstruct <asset>USDT and treat that guess as the
            # provider symbol. Resolve the active Spot row by provider-owned
            # baseAsset/quoteAsset fields instead.
            matching_rows = [
                (symbol, row)
                for symbol, row in symbol_map.items()
                if isinstance(row, dict)
                and str(row.get("baseAsset", "")).strip().upper() == asset
                and str(row.get("quoteAsset", "")).strip().upper() == "USDT"
            ]

            if not matching_rows:

                return AdapterResult(
                    status="NOT_FOUND",
                    allowed=False,
                    operation="symbol_check",
                    reason=(
                        f"Toobit spot symbol for base asset {asset} "
                        "with USDT quote was not found in exchangeInfo."
                    ),
                    data={
                        "asset": asset,
                        "quote_asset": "USDT",
                        "provider_symbol_resolution": "EXCHANGE_INFO_METADATA",
                    },
                )

            trading_rows = [
                (symbol, row)
                for symbol, row in matching_rows
                if str(row.get("status", "")).upper() == "TRADING"
            ]

            if not trading_rows:

                symbol, row = matching_rows[0]
                status = str(row.get("status", "")).upper()

                return AdapterResult(
                    status="NOT_TRADING",
                    allowed=False,
                    operation="symbol_check",
                    reason=(
                        f"Toobit Spot symbol {symbol} exists "
                        "but is not TRADING."
                    ),
                    data={
                        "asset": asset,
                        "symbol": symbol,
                        "status": status,
                        "base_asset": row.get("baseAsset"),
                        "quote_asset": row.get("quoteAsset"),
                    },
                )

            # Multiple active USDT Spot rows for one base asset are
            # ambiguous provider state. Do not choose one silently.
            if len(trading_rows) != 1:
                return AdapterResult(
                    status="AMBIGUOUS",
                    allowed=False,
                    operation="symbol_check",
                    reason=(
                        f"Multiple active Toobit Spot symbols for "
                        f"{asset}/USDT were returned by exchangeInfo."
                    ),
                    data={
                        "asset": asset,
                        "quote_asset": "USDT",
                        "symbols": [symbol for symbol, _ in trading_rows],
                    },
                )

            symbol, row = trading_rows[0]

            return AdapterResult(
                status="PASS",
                allowed=True,
                operation="symbol_check",
                reason=(
                    "Verified active Toobit Spot symbol from "
                    "authoritative exchangeInfo metadata."
                ),
                data={
                    "asset": asset,
                    "symbol": symbol,
                    "status": str(row.get("status", "")).upper(),
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
    # SYMBOL CONTRACT — DYNAMIC EXCHANGE DISCOVERY
    # ========================================================

    def validate_expected_symbols(
        self,
        assets: Optional[List[str]] = None,
    ) -> AdapterResult:

        try:
            symbol_map = self._load_symbol_map()

            requested = None
            if assets is not None:
                requested = []
                seen = set()
                for value in assets:
                    if not isinstance(value, str):
                        raise ValueError("asset must be a string")
                    asset = value.strip().upper()
                    if "/" in asset:
                        asset = asset.split("/", 1)[0]
                    if not asset:
                        raise ValueError("asset must be non-empty")
                    if asset in seen:
                        raise ValueError(f"duplicate requested asset: {asset}")
                    seen.add(asset)
                    requested.append(asset)

            if requested is None:
                requested = sorted(
                    {
                        str(row.get("baseAsset", "")).strip().upper()
                        for symbol, row in symbol_map.items()
                        if isinstance(row, dict)
                        and str(symbol).upper().endswith("USDT")
                        and str(row.get("status", "")).upper() == "TRADING"
                        and row.get("baseAsset")
                    }
                )

            rows: List[Dict[str, Any]] = []
            missing: List[str] = []
            not_trading: List[str] = []
            invalid: List[str] = []

            for asset in requested:
                symbol = f"{asset}USDT"
                row = symbol_map.get(symbol)

                if row is None:
                    missing.append(asset)
                    continue

                status = str(row.get("status", "")).upper()
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

            passed = bool(requested) and (
                len(rows) == len(requested)
                and not missing
                and not not_trading
                and not invalid
            )

            return AdapterResult(
                status="PASS" if passed else "FAIL",
                allowed=passed,
                operation="validate_runtime_symbols",
                reason=(
                    "Requested/discovered Toobit spot contracts "
                    "verified against current exchange information."
                    if passed
                    else
                    "One or more requested/discovered Toobit "
                    "spot contracts failed validation."
                ),
                data={
                    "requested_count": len(requested),
                    "validated_count": len(rows),
                    "missing": missing,
                    "not_trading": not_trading,
                    "invalid": invalid,
                    "symbols": rows,
                    "dynamic_universe": True,
                },
            )

        except Exception as exc:
            return AdapterResult(
                status="ERROR",
                allowed=False,
                operation="validate_runtime_symbols",
                reason=f"Runtime-symbol validation failed: {exc}",
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
    # FUTURES READINESS — AUTHORITATIVE / READ ONLY
    # ========================================================

    def futures_trading_constraints(self, asset: str) -> AdapterResult:
        """Read authoritative Toobit Futures contract metadata."""
        if not isinstance(asset, str) or not asset.strip():
            return AdapterResult("INVALID", False, "futures_trading_constraints", "Asset symbol is missing or invalid.")
        asset = asset.strip().upper()
        try:
            result = self.get_exchange_info()
            if not result.allowed or not result.data:
                return AdapterResult("UNAVAILABLE", False, "futures_trading_constraints", result.reason)
            contracts = result.data.get("contracts")
            if not isinstance(contracts, list):
                return AdapterResult("INVALID_RESPONSE", False, "futures_trading_constraints", "Toobit exchangeInfo.contracts is unavailable; Futures readiness cannot be established.")
            matches = [
                row for row in contracts
                if isinstance(row, dict)
                and str(row.get("underlying", "")).strip().upper() == asset
                and str(row.get("quoteAsset", "")).strip().upper() == "USDT"
            ]
            trading = [row for row in matches if str(row.get("status", "")).strip().upper() == "TRADING"]
            if not matches:
                return AdapterResult("NOT_FOUND", False, "futures_trading_constraints", f"Authoritative Toobit Futures contract for {asset}/USDT was not found.")
            if len(trading) != 1:
                return AdapterResult(
                    "AMBIGUOUS" if trading else "NOT_TRADING", False,
                    "futures_trading_constraints",
                    f"Authoritative Toobit Futures contract state for {asset}/USDT is ambiguous or not TRADING.",
                    {"asset": asset, "symbols": [row.get("symbol") for row in matches]},
                )
            row = trading[0]
            filters = row.get("filters")
            if not isinstance(filters, list) or not filters:
                return AdapterResult("INVALID", False, "futures_trading_constraints", f"Authoritative Futures filters are unavailable for {row.get('symbol')}.")
            normalized_filters = {}
            for item in filters:
                if not isinstance(item, dict):
                    continue
                filter_type = item.get("filterType")
                if isinstance(filter_type, str) and filter_type.strip():
                    normalized_filters[filter_type.strip()] = dict(item)
            multiplier = row.get("contractMultiplier")
            if multiplier is None or str(multiplier).strip() == "":
                return AdapterResult("INVALID", False, "futures_trading_constraints", "Authoritative Futures contractMultiplier is unavailable.")
            lot = normalized_filters.get("LOT_SIZE") or normalized_filters.get("MARKET_LOT_SIZE")
            if not isinstance(lot, dict):
                return AdapterResult("INVALID", False, "futures_trading_constraints", "Authoritative Futures quantity filter is unavailable.")
            if any(lot.get(key) is None for key in ("minQty", "maxQty", "stepSize")):
                return AdapterResult("INVALID", False, "futures_trading_constraints", "Authoritative Futures quantity constraints are incomplete.")
            return AdapterResult(
                "PASS", True, "futures_trading_constraints",
                f"Authoritative Toobit Futures contract constraints verified for {row.get('symbol')}.",
                {
                    "asset": asset,
                    "symbol": str(row.get("symbol", "")).strip().upper(),
                    "status": str(row.get("status", "")).strip().upper(),
                    "underlying": row.get("underlying"),
                    "quote_asset": row.get("quoteAsset"),
                    "category": "USDT",
                    "quantity_unit": "CONTRACTS",
                    "contract_multiplier": multiplier,
                    "filters": normalized_filters,
                    "risk_limits": row.get("riskLimits"),
                },
            )
        except Exception as exc:
            return AdapterResult("ERROR", False, "futures_trading_constraints", f"Futures contract read failed: {exc}")

    def futures_account_state(self, asset: str) -> AdapterResult:
        """Read authoritative Futures balance, leverage and position state."""
        if not isinstance(asset, str) or not asset.strip():
            return AdapterResult("INVALID", False, "futures_account_state", "Asset symbol is missing or invalid.")
        if not self.api_key or not self.api_secret:
            return AdapterResult("MISSING_CREDENTIALS", False, "futures_account_state", "Toobit API credentials are not available.")
        asset = asset.strip().upper()
        try:
            constraints = self.futures_trading_constraints(asset)
            if not constraints.allowed or not constraints.data:
                return AdapterResult("UNAVAILABLE", False, "futures_account_state", constraints.reason)
            symbol = constraints.data["symbol"]
            balance_response = self._signed_get(FUTURES_BALANCE_ENDPOINT, params={"category": "USDT"})
            if balance_response.status_code != 200:
                return AdapterResult("HTTP_ERROR", False, "futures_account_state", f"Toobit Futures balance returned HTTP {balance_response.status_code}.", self._response_data(balance_response))
            balance_payload = balance_response.json()
            if not isinstance(balance_payload, list) or any(not isinstance(row, dict) for row in balance_payload):
                return AdapterResult("INVALID_RESPONSE", False, "futures_account_state", "Toobit Futures balance response is invalid.")
            leverage_response = self._signed_get(FUTURES_ACCOUNT_LEVERAGE_ENDPOINT, params={"symbol": symbol, "category": "USDT"})
            if leverage_response.status_code != 200:
                return AdapterResult("HTTP_ERROR", False, "futures_account_state", f"Toobit Futures accountLeverage returned HTTP {leverage_response.status_code}.", self._response_data(leverage_response))
            leverage_payload = leverage_response.json()
            if not isinstance(leverage_payload, list):
                return AdapterResult("INVALID_RESPONSE", False, "futures_account_state", "Toobit Futures accountLeverage response is invalid.")
            leverage_rows = [
                row for row in leverage_payload
                if isinstance(row, dict)
                and str(row.get("symbolId", "")).strip().upper() == symbol
            ]
            if len(leverage_rows) != 1:
                return AdapterResult("INVALID_STATE", False, "futures_account_state", "Authoritative Futures leverage/margin state is missing or ambiguous.")
            leverage_row = leverage_rows[0]
            leverage = leverage_row.get("leverage")
            margin_type = str(leverage_row.get("marginType", "")).strip().upper()
            if leverage is None or str(leverage).strip() == "" or margin_type not in {"CROSS", "ISOLATED"}:
                return AdapterResult("INVALID_STATE", False, "futures_account_state", "Authoritative Futures leverage/margin state is incomplete.")
            from toobit_position_reader_v0_1 import build_toobit_position_reader
            position_result = build_toobit_position_reader(self)()
            if not position_result.allowed or not isinstance(position_result.data, dict):
                return AdapterResult("UNAVAILABLE", False, "futures_account_state", "Authoritative Futures position state is unavailable.")
            positions = position_result.data.get("positions")
            if not isinstance(positions, list):
                return AdapterResult("INVALID_RESPONSE", False, "futures_account_state", "Authoritative Futures position state is invalid.")
            symbol_positions = [row for row in positions if isinstance(row, dict) and str(row.get("symbol", "")).strip().upper() == symbol]
            sides = [str(row.get("side", "")).strip().upper() for row in symbol_positions]
            position_conflict = len(sides) != len(set(sides))
            return AdapterResult(
                "PASS", True, "futures_account_state",
                "Authoritative Toobit Futures account state is available.",
                {
                    "state_known": True,
                    "symbol": symbol,
                    "category": "USDT",
                    "balance_rows": balance_payload,
                    "leverage": leverage,
                    "margin_type": margin_type,
                    "margin_state_known": True,
                    "leverage_state_known": True,
                    "position_conflict": position_conflict,
                    "positions": symbol_positions,
                    "source_type": "CEX_PRIVATE_API",
                },
            )
        except Exception as exc:
            return AdapterResult("ERROR", False, "futures_account_state", f"Futures account read failed: {exc}")

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

            account_id, identity_source_id, source_timestamp = (
                self._resolve_account_identity(payload)
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
                    # Provider-normalized account identity metadata for the
                    # provider-neutral observation/evidence boundary.
                    "account_id": account_id,
                    "account_type": payload.get("accountType"),
                    "account_response": payload,
                    "balance_rows": (
                        len(balances)
                        if isinstance(
                            balances,
                            list,
                        )
                        else None
                    ),
                    "source_type": "EXCHANGE_PRIVATE_API",
                    "account_source_id": f"{EXCHANGE_NAME}:{ACCOUNT_ENDPOINT}",
                    **(
                        {"source_id": identity_source_id}
                        if isinstance(identity_source_id, str)
                        and identity_source_id.strip()
                        else {}
                    ),
                    **(
                        {"source_timestamp": str(source_timestamp)}
                        if source_timestamp is not None
                        else {}
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

    def _resolve_account_identity(
        self,
        payload: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[int]]:
        """Resolve the authoritative Toobit account identity without invention.

        Toobit's authenticated /api/v1/account response may expose the authenticated
        account identity as either accountId or userId. Prefer either value
        directly from that authoritative authenticated response.

        Only when neither identity field is present, use the authenticated
        balanceFlow fallback exposing accountId.

        No local, synthetic, hashed, or inferred identifier is created.
        """
        account_id = payload.get("accountId")

        if isinstance(account_id, (str, int)) and str(account_id).strip():
            timestamp = getattr(self, "_last_signed_timestamp_ms", None)
            return (
                str(account_id).strip(),
                f"{EXCHANGE_NAME}:{ACCOUNT_ENDPOINT}",
                timestamp,
            )

        user_id = payload.get("userId")

        if isinstance(user_id, (str, int)) and str(user_id).strip():
            timestamp = getattr(self, "_last_signed_timestamp_ms", None)
            return (
                str(user_id).strip(),
                f"{EXCHANGE_NAME}:{ACCOUNT_ENDPOINT}",
                timestamp,
            )

        response = self._signed_get(
            ACCOUNT_BALANCE_FLOW_ENDPOINT,
            {"limit": 1},
        )

        if response.status_code != 200:
            return (
                None,
                None,
                getattr(self, "_last_signed_timestamp_ms", None),
            )

        flow_payload = response.json()

        if not isinstance(flow_payload, list):
            return (
                None,
                None,
                getattr(self, "_last_signed_timestamp_ms", None),
            )

        for row in flow_payload:
            if not isinstance(row, dict):
                continue

            candidate = row.get("accountId")

            if isinstance(candidate, (str, int)) and str(candidate).strip():
                timestamp = getattr(
                    self,
                    "_last_signed_timestamp_ms",
                    None,
                )

                return (
                    str(candidate).strip(),
                    f"{EXCHANGE_NAME}:{ACCOUNT_BALANCE_FLOW_ENDPOINT}",
                    timestamp,
                )

        return (
            None,
            None,
            getattr(self, "_last_signed_timestamp_ms", None),
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
                "balances": [
                    {
                        "asset": row.get("coin"),
                        "free": row.get("free"),
                        "locked": row.get("locked"),
                        "total": row.get("total"),
                    }
                    for row in balances
                    if isinstance(row, dict)
                ],
                "nonzero_balances": nonzero,
                "nonzero_count": len(nonzero),
                "balance_observation_complete": True,
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
    # AUTHORITATIVE SPOT ORDER STATE — READ ONLY
    # ========================================================

    def open_orders(self, asset: Optional[str] = None) -> AdapterResult:
        """Read current open Spot orders from Toobit's USER_DATA API."""
        if not self.api_key or not self.api_secret:
            return AdapterResult(
                status="MISSING_CREDENTIALS",
                allowed=False,
                operation="open_orders",
                reason="Toobit API credentials are not available.",
            )
        try:
            params = {}
            if asset:
                symbol_result = self.symbol_check(asset)
                if not symbol_result.allowed or not symbol_result.data:
                    return AdapterResult(
                        status="UNAVAILABLE", allowed=False,
                        operation="open_orders", reason=symbol_result.reason,
                        data=symbol_result.data,
                    )
                params["symbol"] = symbol_result.data["symbol"]
            response = self._signed_get(OPEN_ORDERS_ENDPOINT, params=params)
            if response.status_code != 200:
                return AdapterResult(
                    status="HTTP_ERROR", allowed=False,
                    operation="open_orders",
                    reason=f"Toobit openOrders returned HTTP {response.status_code}.",
                    data=self._response_data(response),
                )
            payload = response.json()
            if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
                return AdapterResult(
                    status="INVALID_RESPONSE", allowed=False,
                    operation="open_orders", reason="Toobit openOrders response is not a list of objects.",
                )
            return AdapterResult(
                status="PASS", allowed=True, operation="open_orders",
                reason="Authoritative Toobit current open-order state read succeeded.",
                data={"orders": payload, "state_known": True, "source_id": "TOOBIT", "source_type": "CEX_PRIVATE_API"},
            )
        except Exception as exc:
            return AdapterResult(status="ERROR", allowed=False, operation="open_orders", reason=f"Open-order read failed: {exc}")

    def recent_orders(self, asset: Optional[str] = None) -> AdapterResult:
        """Read recent Spot account orders from Toobit's USER_DATA API."""
        if not self.api_key or not self.api_secret:
            return AdapterResult(
                status="MISSING_CREDENTIALS", allowed=False,
                operation="recent_orders", reason="Toobit API credentials are not available.",
            )
        try:
            params = {}
            if asset:
                symbol_result = self.symbol_check(asset)
                if not symbol_result.allowed or not symbol_result.data:
                    return AdapterResult(
                        status="UNAVAILABLE", allowed=False,
                        operation="recent_orders", reason=symbol_result.reason,
                        data=symbol_result.data,
                    )
                params["symbol"] = symbol_result.data["symbol"]
            response = self._signed_get(ALL_ORDERS_ENDPOINT, params=params)
            if response.status_code != 200:
                return AdapterResult(
                    status="HTTP_ERROR", allowed=False,
                    operation="recent_orders",
                    reason=f"Toobit tradeOrders returned HTTP {response.status_code}.",
                    data=self._response_data(response),
                )
            payload = response.json()
            if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
                return AdapterResult(
                    status="INVALID_RESPONSE", allowed=False,
                    operation="recent_orders", reason="Toobit tradeOrders response is not a list of objects.",
                )
            return AdapterResult(
                status="PASS", allowed=True, operation="recent_orders",
                reason="Authoritative Toobit recent-order state read succeeded.",
                data={"orders": payload, "state_known": True, "source_id": "TOOBIT", "source_type": "CEX_PRIVATE_API"},
            )
        except Exception as exc:
            return AdapterResult(status="ERROR", allowed=False, operation="recent_orders", reason=f"Recent-order read failed: {exc}")

    def futures_duplicate_check(self, asset: str) -> AdapterResult:
        """Read authoritative Futures open/history order client IDs."""
        constraints = self.futures_trading_constraints(asset)
        if not constraints.allowed or not constraints.data:
            return AdapterResult("UNAVAILABLE", False, "futures_duplicate_check", constraints.reason)
        symbol = constraints.data["symbol"]
        try:
            open_response = self._signed_get(FUTURES_OPEN_ORDERS_ENDPOINT, params={"symbol": symbol, "category": "USDT"})
            history_response = self._signed_get(FUTURES_HISTORY_ORDERS_ENDPOINT, params={"symbol": symbol, "category": "USDT", "limit": 100})
            if open_response.status_code != 200 or history_response.status_code != 200:
                return AdapterResult(
                    "HTTP_ERROR", False, "futures_duplicate_check",
                    f"Futures order-state read failed: open_http={open_response.status_code}; history_http={history_response.status_code}.",
                    {"open": self._response_data(open_response), "history": self._response_data(history_response)},
                )
            open_payload = open_response.json()
            history_payload = history_response.json()
            if not isinstance(open_payload, list) or any(not isinstance(row, dict) for row in open_payload):
                raise RuntimeError("Futures open-order response is invalid")
            if not isinstance(history_payload, list) or any(not isinstance(row, dict) for row in history_payload):
                raise RuntimeError("Futures history-order response is invalid")
            return AdapterResult(
                "PASS", True, "futures_duplicate_check",
                "Authoritative Toobit Futures order state is available.",
                {
                    "asset": asset.upper(), "symbol": symbol, "state_known": True,
                    "open_order_client_ids": frozenset(str(row.get("clientOrderId")).strip() for row in open_payload if row.get("clientOrderId") not in (None, "")),
                    "recent_order_client_ids": frozenset(str(row.get("clientOrderId")).strip() for row in history_payload if row.get("clientOrderId") not in (None, "")),
                    "source_id": "TOOBIT", "source_type": "CEX_PRIVATE_API",
                },
            )
        except Exception as exc:
            return AdapterResult("ERROR", False, "futures_duplicate_check", f"Futures order-state read failed: {exc}")

    # ========================================================
    # DUPLICATE CHECK — AUTHORITATIVE READ ONLY
    # ========================================================

    def duplicate_check(self, asset: str, direction: str) -> AdapterResult:
        """Expose authoritative current/recent Spot order state for preflight."""
        open_result = self.open_orders(asset)
        recent_result = self.recent_orders(asset)
        if not open_result.allowed or not recent_result.allowed:
            return AdapterResult(
                status="UNAVAILABLE", allowed=False, operation="duplicate_check",
                reason=f"Provider order state unavailable: {open_result.reason}; {recent_result.reason}",
            )
        open_rows = open_result.data.get("orders", [])
        recent_rows = recent_result.data.get("orders", [])
        open_ids = frozenset(
            str(row.get("clientOrderId")).strip()
            for row in open_rows if row.get("clientOrderId") not in (None, "")
        )
        recent_ids = frozenset(
            str(row.get("clientOrderId")).strip()
            for row in recent_rows if row.get("clientOrderId") not in (None, "")
        )
        return AdapterResult(
            status="PASS", allowed=True, operation="duplicate_check",
            reason="Authoritative provider order state is available.",
            data={
                "asset": asset.upper() if isinstance(asset, str) else asset,
                "direction": direction,
                "state_known": True,
                "open_order_client_ids": open_ids,
                "recent_order_client_ids": recent_ids,
                "source_id": "TOOBIT",
                "source_type": "CEX_PRIVATE_API",
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

    # ========================================================
    # CANONICAL ORDER SUBMISSION ? FAIL CLOSED
    # CP46-A1
    # ========================================================

        # ========================================================
    # CANONICAL ORDER SUBMISSION — CP46-G / CP49
    # ========================================================

        # ========================================================
    # CANONICAL ORDER SUBMISSION — CP46-G / CP49
    # ========================================================

    def submit_order(
        self,
        request,
    ):
        """
        Canonical exchange-agnostic submission boundary.

        CP46-G / CP49:

            CanonicalOrderRequest
                +
            exact ProviderOrderRequest produced upstream
                |
                v
            Toobit provider transport

        Rules:
            - Canonical request remains the execution-boundary input.
            - Exact ProviderOrderRequest is consumed from CP46-G.
            - Provider request is never reconstructed from canonical data.
            - Provider quantity is authoritative.
            - Provider identity is preserved.
            - Fresh Toobit server timestamp is used at provider boundary.
            - Decision-Birth timestamp remains unchanged.
            - No database write.
            - Fail closed on missing or invalid provenance.
        """

        from exchange_execution_contract import (
            CanonicalExecutionResult,
            CanonicalOrderRequest,
            blocked_execution_result,
        )

        from cp46_d_production_provider_preflight_v0_1 import (
            ProviderOrderRequest,
        )

        # ----------------------------------------------------
        # Canonical request validation
        # ----------------------------------------------------

        if not isinstance(
            request,
            CanonicalOrderRequest,
        ):
            return blocked_execution_result(
                error_code="INVALID_REQUEST",
                error_message="CanonicalOrderRequest is required.",
                adapter=EXCHANGE_NAME,
            )

        # ----------------------------------------------------
        # Execution capability gates
        # ----------------------------------------------------

        if self.execution_enabled is not True:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="EXECUTION_DISABLED",
                error_message=(
                    "Toobit canonical order submission is disabled."
                ),
            )

        if self.order_submission_enabled is not True:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="ORDER_SUBMISSION_DISABLED",
                error_message=(
                    "Toobit order submission is disabled."
                ),
            )

        if self.exchange_write_enabled is not True:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="EXCHANGE_WRITE_DISABLED",
                error_message=(
                    "Toobit exchange write is disabled."
                ),
            )

        if self.live_order_transport_enabled is not True:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="SUBMISSION_TRANSPORT_DISABLED",
                error_message=(
                    "Toobit live order transport is disabled."
                ),
            )

        if self.live_order_transport is None:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="SUBMISSION_TRANSPORT_UNAVAILABLE",
                error_message=(
                    "Toobit live order transport is unavailable."
                ),
            )

        # ----------------------------------------------------
        # Current Spot scope
        # ----------------------------------------------------

        if request.direction != "LONG":
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="SPOT_DIRECTION_UNSUPPORTED",
                error_message=(
                    "Toobit spot transport currently supports "
                    "canonical LONG -> BUY only."
                ),
            )

        try:
            # ------------------------------------------------
            # CP46-G provider provenance
            # ------------------------------------------------

            provider_request = getattr(
                self,
                "_cp46g_provider_request",
                None,
            )

            # Missing provenance is different from invalid type.
            if provider_request is None:
                return blocked_execution_result(
                    asset=request.asset,
                    direction=request.direction,
                    adapter=EXCHANGE_NAME,
                    error_code="CP46G_PROVIDER_REQUEST_MISSING",
                    error_message=(
                        "Exact ProviderOrderRequest from "
                        "CP46-G handoff is unavailable."
                    ),
                )

            if not isinstance(
                provider_request,
                ProviderOrderRequest,
            ):
                return blocked_execution_result(
                    asset=request.asset,
                    direction=request.direction,
                    adapter=EXCHANGE_NAME,
                    error_code="CP46G_PROVIDER_REQUEST_TYPE_INVALID",
                    error_message=(
                        "CP46-G provider request must be the approved "
                        "ProviderOrderRequest instance."
                    ),
                )

            # ------------------------------------------------
            # Intent identity binding
            # ------------------------------------------------

            if provider_request.intent_id != request.intent_id:
                return blocked_execution_result(
                    asset=request.asset,
                    direction=request.direction,
                    adapter=EXCHANGE_NAME,
                    error_code="CP46G_INTENT_ID_MISMATCH",
                    error_message=(
                        "Provider and canonical intent identity "
                        "do not match."
                    ),
                )

            # ------------------------------------------------
            # Provider-owned symbol
            # ------------------------------------------------

            if (
                not isinstance(
                    provider_request.symbol,
                    str,
                )
                or not provider_request.symbol.strip()
            ):
                return blocked_execution_result(
                    asset=request.asset,
                    direction=request.direction,
                    adapter=EXCHANGE_NAME,
                    error_code="CP46G_PROVIDER_SYMBOL_MISSING",
                    error_message=(
                        "ProviderOrderRequest contains no "
                        "authoritative provider symbol."
                    ),
                )

            # ------------------------------------------------
            # Provider order type
            # ------------------------------------------------

            if (
                not isinstance(
                    provider_request.order_type,
                    str,
                )
                or not provider_request.order_type.strip()
            ):
                return blocked_execution_result(
                    asset=request.asset,
                    direction=request.direction,
                    adapter=EXCHANGE_NAME,
                    error_code="CP46G_PROVIDER_ORDER_TYPE_MISSING",
                    error_message=(
                        "ProviderOrderRequest contains no "
                        "provider order type."
                    ),
                )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # ProviderOrderRequest.quantity is authoritative.
            #
            # DO NOT compare it with request.quantity.
            # DO NOT reconstruct it from CanonicalOrderRequest.
            #
            # CP46-G explicitly requires the exact provider
            # projection to reach the transport unchanged.
            # ------------------------------------------------

            from toobit_spot_order_live_transport_v0_1 import (
                SpotLiveOrderRequest,
            )

            transport_request = SpotLiveOrderRequest(
                symbol=provider_request.symbol,
                side=provider_request.side,
                order_type=provider_request.order_type,
                time_in_force=(
                    "GTC"
                    if provider_request.order_type == "LIMIT"
                    else None
                ),
                quantity=provider_request.quantity,
                quantity_unit=provider_request.quantity_unit,
                price=(
                    provider_request.entry_price
                    if provider_request.order_type != "MARKET"
                    else None
                ),

                # Fresh Toobit server timestamp.
                #
                # This timestamp belongs exclusively to the
                # actual signed provider HTTP request.
                #
                # It does NOT replace the canonical Decision-Birth
                # timestamp or ProviderOrderRequest.timestamp.
                timestamp=self._get_server_timestamp_ms(),

                new_client_order_id=provider_request.client_order_id,
            )

            # ------------------------------------------------
            # Quantity integrity:
            #
            # Transport must consume the exact provider quantity.
            # ------------------------------------------------

            if transport_request.quantity != provider_request.quantity:
                return blocked_execution_result(
                    asset=request.asset,
                    direction=request.direction,
                    adapter=EXCHANGE_NAME,
                    error_code="CP46G_QUANTITY_PROJECTION_MUTATION",
                    error_message=(
                        "Provider transport projection changed "
                        "the authoritative provider quantity."
                    ),
                )

            # ------------------------------------------------
            # Actual provider transport boundary
            # ------------------------------------------------

            transport_result = self.live_order_transport.submit(
                transport_request
            )

            # ------------------------------------------------
            # Canonical result
            # ------------------------------------------------

            return CanonicalExecutionResult(
                accepted=transport_result.accepted,
                exchange_order_id=(
                    transport_result.exchange_order_id
                ),
                status=transport_result.status,
                asset=request.asset,
                direction=request.direction,
                executed_quantity=None,
                executed_price=None,

                # Preserve canonical Decision-Birth timestamp.
                timestamp=request.timestamp,

                adapter=EXCHANGE_NAME,
                error_code=transport_result.error_code,
                error_message=transport_result.error_message,
            )

        except Exception as exc:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                adapter=EXCHANGE_NAME,
                error_code="ADAPTER_SUBMISSION_ERROR",
                error_message=str(exc),
            )
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

            "runtime_symbols":
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