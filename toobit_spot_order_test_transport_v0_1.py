"""
ARUNDA TRADER — TOOBIT SPOT ORDER-TEST TRANSPORT v0.1
=====================================================

CP46-A4

Purpose:
    Provider-specific, fail-closed transport contract for
    Toobit Spot POST /api/v1/spot/orderTest.

Hard rules:
    - orderTest ONLY
    - never call /api/v1/spot/order
    - no database write
    - no execution enablement
    - no quantity mutation
    - no implicit BASE_ASSET -> QUOTE_ASSET conversion
    - no estimation
    - no rounding to force acceptance
    - deterministic serialization
    - exact serialized payload is signed
    - exact signed payload is sent
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import quote


BASE_URL = "https://api.toobit.com"
ORDER_TEST_ENDPOINT = "/api/v1/spot/orderTest"

EXECUTION_ENABLED = False
ORDER_SUBMISSION_ENABLED = False
EXCHANGE_WRITE_ENABLED = False
DATABASE_WRITE_ENABLED = False

RECV_WINDOW = 5000


class SpotOrderTestError(RuntimeError):
    """Base error for fail-closed Spot orderTest transport."""


@dataclass(frozen=True)
class SpotOrderTestRequest:
    """
    Provider-specific Spot orderTest request.

    This is deliberately NOT CanonicalOrderRequest.

    quantity_unit:
        BASE_ASSET
        QUOTE_ASSET

    For MARKET + BUY, Toobit requires QUOTE_ASSET quantity.
    No conversion is performed here.
    """

    symbol: str
    side: str
    order_type: str
    quantity: Any
    quantity_unit: str
    timestamp: int
    time_in_force: Optional[str] = None
    price: Optional[Any] = None
    new_client_order_id: Optional[str] = None
    recv_window: int = RECV_WINDOW


@dataclass(frozen=True)
class SpotOrderTestResult:
    status: str
    endpoint: str
    submitted_to_matching_engine: bool
    request_payload: Optional[Dict[str, Any]] = None
    response: Optional[Any] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


def _serialize_value(value: Any) -> str:
    """
    Deterministic scalar serialization.

    Decimal is converted without scientific notation.
    No float arithmetic is performed.
    """

    if isinstance(value, Decimal):
        return format(value, "f")

    return str(value)


def _encode_query_value(value: Any) -> str:
    return quote(
        _serialize_value(value),
        safe="",
    )


def build_query_string(
    payload: Dict[str, Any],
) -> str:
    """
    Preserve insertion order.

    The returned string is the exact string used for HMAC.
    """

    parts = []

    for key, value in payload.items():

        if value is None:
            continue

        parts.append(
            f"{key}={_encode_query_value(value)}"
        )

    if not parts:
        raise SpotOrderTestError(
            "EMPTY_SIGNED_QUERY"
        )

    return "&".join(parts)


def generate_signature(
    query_string: str,
    api_secret: str,
) -> str:

    if not api_secret:
        raise SpotOrderTestError(
            "API_SECRET_REQUIRED"
        )

    return hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_request(
    request: SpotOrderTestRequest,
) -> None:

    if not isinstance(
        request,
        SpotOrderTestRequest,
    ):
        raise SpotOrderTestError(
            "INVALID_REQUEST_TYPE"
        )

    if not request.symbol:
        raise SpotOrderTestError(
            "SYMBOL_REQUIRED"
        )

    if request.side not in {
        "BUY",
        "SELL",
    }:
        raise SpotOrderTestError(
            "INVALID_SIDE"
        )

    if request.order_type not in {
        "LIMIT",
        "MARKET",
        "LIMIT_MAKER",
    }:
        raise SpotOrderTestError(
            "INVALID_ORDER_TYPE"
        )

    if request.quantity_unit not in {
        "BASE_ASSET",
        "QUOTE_ASSET",
    }:
        raise SpotOrderTestError(
            "INVALID_QUANTITY_UNIT"
        )

    if request.quantity is None:
        raise SpotOrderTestError(
            "QUANTITY_REQUIRED"
        )

    if request.order_type in {
        "LIMIT",
        "LIMIT_MAKER",
    } and request.price is None:
        raise SpotOrderTestError(
            "PRICE_REQUIRED"
        )

    if (
        request.order_type == "LIMIT"
        and not request.time_in_force
    ):
        raise SpotOrderTestError(
            "TIME_IN_FORCE_REQUIRED"
        )

    # --------------------------------------------------------
    # Critical Toobit semantic boundary:
    #
    # MARKET + BUY quantity is QUOTE_ASSET.
    #
    # We do NOT convert BASE_ASSET here.
    # --------------------------------------------------------

    if (
        request.order_type == "MARKET"
        and request.side == "BUY"
        and request.quantity_unit != "QUOTE_ASSET"
    ):
        raise SpotOrderTestError(
            "MARKET_BUY_REQUIRES_QUOTE_ASSET_QUANTITY"
        )


def build_provider_payload(
    request: SpotOrderTestRequest,
) -> Dict[str, Any]:

    validate_request(request)

    payload: Dict[str, Any] = {
        "symbol": request.symbol,
        "side": request.side,
        "type": request.order_type,
    }

    if request.time_in_force is not None:
        payload["timeInForce"] = request.time_in_force

    payload["quantity"] = request.quantity

    if request.price is not None:
        payload["price"] = request.price

    if request.new_client_order_id is not None:
        payload["newClientOrderId"] = (
            request.new_client_order_id
        )

    payload["recvWindow"] = request.recv_window
    payload["timestamp"] = request.timestamp

    return payload


class ToobitSpotOrderTestTransport:
    """
    Controlled Spot orderTest transport.

    Default state is permanently fail-closed.

    A caller must explicitly provide:
        order_test_enabled=True

    even then only /spot/orderTest is reachable.
    """

    def __init__(
        self,
        api_key: Optional[str],
        api_secret: Optional[str],
        *,
        session: Any,
        order_test_enabled: bool = False,
        base_url: str = BASE_URL,
    ) -> None:

        self.api_key = api_key
        self.api_secret = api_secret
        self.session = session
        self.order_test_enabled = order_test_enabled
        self.base_url = base_url

    def build_signed_request(
        self,
        request: SpotOrderTestRequest,
    ) -> Dict[str, Any]:

        payload = build_provider_payload(
            request
        )

        query_string = build_query_string(
            payload
        )

        signature = generate_signature(
            query_string,
            self.api_secret or "",
        )

        final_query_string = (
            f"{query_string}"
            f"&signature={signature}"
        )

        return {
            "query_string": query_string,
            "final_query_string": final_query_string,
            "url": (
                f"{self.base_url}"
                f"{ORDER_TEST_ENDPOINT}"
                f"?{final_query_string}"
            ),
            "headers": {
                "X-BB-APIKEY": self.api_key or "",
            },
            "payload": payload,
            "signature": signature,
        }

    def order_test(
        self,
        request: SpotOrderTestRequest,
    ) -> SpotOrderTestResult:

        # ----------------------------------------------------
        # Global safety locks.
        # ----------------------------------------------------

        if EXECUTION_ENABLED is not False:
            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="EXECUTION_STATE_INVALID",
                error_message=(
                    "CP46-A4 requires "
                    "EXECUTION_ENABLED=False."
                ),
            )

        if ORDER_SUBMISSION_ENABLED is not False:
            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="ORDER_SUBMISSION_STATE_INVALID",
                error_message=(
                    "CP46-A4 requires "
                    "ORDER_SUBMISSION_ENABLED=False."
                ),
            )

        if EXCHANGE_WRITE_ENABLED is not False:
            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="EXCHANGE_WRITE_STATE_INVALID",
                error_message=(
                    "CP46-A4 requires "
                    "EXCHANGE_WRITE_ENABLED=False."
                ),
            )

        if DATABASE_WRITE_ENABLED is not False:
            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="DATABASE_WRITE_STATE_INVALID",
                error_message=(
                    "CP46-A4 requires "
                    "DATABASE_WRITE_ENABLED=False."
                ),
            )

        if not self.order_test_enabled:
            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="ORDER_TEST_DISABLED",
                error_message=(
                    "Toobit Spot orderTest transport "
                    "is disabled."
                ),
            )

        if not self.api_key or not self.api_secret:
            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="CREDENTIALS_REQUIRED",
                error_message=(
                    "API credentials are required "
                    "for signed orderTest."
                ),
            )

        try:
            signed = self.build_signed_request(
                request
            )

            # ------------------------------------------------
            # Explicit safety assertion:
            # orderTest endpoint only.
            # ------------------------------------------------

            if ORDER_TEST_ENDPOINT not in signed["url"]:
                raise SpotOrderTestError(
                    "INVALID_ORDER_TEST_ENDPOINT"
                )

            if "/api/v1/spot/order?" in signed["url"]:
                raise SpotOrderTestError(
                    "LIVE_ORDER_ENDPOINT_FORBIDDEN"
                )

            response = self.session.post(
                signed["url"],
                headers=signed["headers"],
                timeout=15,
            )

            try:
                response_payload = response.json()
            except ValueError:
                response_payload = response.text

            return SpotOrderTestResult(
                status=(
                    "PASS"
                    if response.status_code == 200
                    else "HTTP_ERROR"
                ),
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                request_payload=signed["payload"],
                response=response_payload,
                error_code=(
                    None
                    if response.status_code == 200
                    else f"HTTP_{response.status_code}"
                ),
                error_message=None,
            )

        except SpotOrderTestError as exc:

            return SpotOrderTestResult(
                status="FAIL_CLOSED",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code=str(exc),
                error_message=str(exc),
            )

        except Exception as exc:

            return SpotOrderTestResult(
                status="TRANSPORT_ERROR",
                endpoint=ORDER_TEST_ENDPOINT,
                submitted_to_matching_engine=False,
                error_code="TRANSPORT_ERROR",
                error_message=str(exc),
            )