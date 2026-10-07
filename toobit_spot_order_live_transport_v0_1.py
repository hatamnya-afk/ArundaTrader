"""
ARUNDA TRADER
TOOBIT SPOT LIVE ORDER TRANSPORT v0.1

Controlled live exchange transport.

Default state is FAIL-CLOSED. The transport can contact the real Toobit
spot matching-engine endpoint only when every explicit transport safety
switch is enabled by the caller.

Rules:
- no database write
- no retry
- no quantity conversion
- no quantity mutation
- no price estimation
- no orderTest endpoint
- exact signed query is used for both HMAC and HTTP request
- a real HTTP response, including rejection, is an exchange interaction
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Mapping, Optional


BASE_URL = "https://api.toobit.com"
LIVE_ORDER_ENDPOINT = "/api/v1/spot/order"

EXECUTION_ENABLED = False
ORDER_SUBMISSION_ENABLED = False
EXCHANGE_WRITE_ENABLED = False
DATABASE_WRITE_ENABLED = False

RECV_WINDOW = 5000

VALID_SIDES = frozenset({"BUY", "SELL"})
VALID_ORDER_TYPES = frozenset({"LIMIT", "MARKET", "LIMIT_MAKER"})
VALID_TIME_IN_FORCE = frozenset({"GTC", "FOK", "IOC", "POST_ONLY"})


class SpotLiveOrderContractError(ValueError):
    """Fail-closed provider contract violation."""


@dataclass(frozen=True)
class SpotLiveOrderRequest:
    symbol: str
    side: str
    order_type: str
    time_in_force: Optional[str]
    quantity: Any
    quantity_unit: str
    price: Optional[Any]
    timestamp: int
    new_client_order_id: str
    recv_window: int = RECV_WINDOW


@dataclass(frozen=True)
class SpotLiveOrderResult:
    accepted: bool
    status: str
    http_status: Optional[int]
    response_body: Optional[Any]
    error_code: Optional[str]
    error_message: Optional[str]
    submitted_to_matching_engine: bool
    exchange_order_id: Optional[str] = None


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        raise SpotLiveOrderContractError("NULL_SCALAR_FORBIDDEN")
    return str(value)


def validate_request(
    request: SpotLiveOrderRequest,
) -> tuple[bool, str]:
    if not isinstance(request, SpotLiveOrderRequest):
        return False, "REQUEST_TYPE_INVALID"

    if not request.symbol.strip():
        return False, "SYMBOL_INVALID"

    if request.side not in VALID_SIDES:
        return False, "SIDE_INVALID"

    if request.order_type not in VALID_ORDER_TYPES:
        return False, "ORDER_TYPE_INVALID"

    if request.quantity is None or str(request.quantity).strip() == "":
        return False, "QUANTITY_INVALID"

    if request.timestamp <= 0:
        return False, "TIMESTAMP_INVALID"

    if request.recv_window <= 0:
        return False, "RECV_WINDOW_INVALID"

    if not request.new_client_order_id.strip():
        return False, "CLIENT_ORDER_ID_INVALID"

    if request.order_type in {"LIMIT", "LIMIT_MAKER"}:
        if request.price is None or str(request.price).strip() == "":
            return False, "LIMIT_PRICE_REQUIRED"

    if request.order_type == "MARKET" and request.price is not None:
        return False, "MARKET_PRICE_FORBIDDEN"

    if request.time_in_force is not None:
        if request.time_in_force not in VALID_TIME_IN_FORCE:
            return False, "TIME_IN_FORCE_INVALID"

    if request.order_type == "LIMIT_MAKER" and request.time_in_force is not None:
        return False, "LIMIT_MAKER_TIME_IN_FORCE_FORBIDDEN"

    if request.quantity_unit not in {"BASE_ASSET", "QUOTE_ASSET"}:
        return False, "QUANTITY_UNIT_INVALID"

    if request.order_type == "MARKET" and request.side == "BUY":
        if request.quantity_unit != "QUOTE_ASSET":
            return False, "MARKET_BUY_REQUIRES_QUOTE_ASSET_QUANTITY"
    elif request.quantity_unit != "BASE_ASSET":
        return False, "QUOTE_ASSET_QUANTITY_UNSUPPORTED"

    return True, "VALID"


def build_query_params(
    request: SpotLiveOrderRequest,
) -> dict[str, str]:
    valid, reason = validate_request(request)
    if not valid:
        raise SpotLiveOrderContractError(reason)

    params: dict[str, str] = {
        "symbol": _scalar(request.symbol),
        "side": _scalar(request.side),
        "type": _scalar(request.order_type),
    }

    if request.time_in_force is not None:
        params["timeInForce"] = _scalar(request.time_in_force)

    params["quantity"] = _scalar(request.quantity)

    if request.price is not None:
        params["price"] = _scalar(request.price)

    params["newClientOrderId"] = _scalar(request.new_client_order_id)
    params["recvWindow"] = _scalar(request.recv_window)
    params["timestamp"] = _scalar(request.timestamp)

    return params


def build_query_string(params: Mapping[str, Any]) -> str:
    if not isinstance(params, Mapping):
        raise SpotLiveOrderContractError("QUERY_PARAMS_INVALID")

    return "&".join(
        f"{key}={_scalar(value)}"
        for key, value in params.items()
    )


def generate_signature(
    query_string: str,
    secret_key: str,
) -> str:
    if not query_string:
        raise SpotLiveOrderContractError("QUERY_STRING_EMPTY")
    if not secret_key:
        raise SpotLiveOrderContractError("SECRET_KEY_REQUIRED")

    return hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_request(
    request: SpotLiveOrderRequest,
    *,
    api_key: str,
    secret_key: str,
) -> dict[str, Any]:
    if not api_key:
        raise SpotLiveOrderContractError("API_KEY_REQUIRED")
    if not secret_key:
        raise SpotLiveOrderContractError("SECRET_KEY_REQUIRED")

    query_string = build_query_string(build_query_params(request))
    signature = generate_signature(query_string, secret_key)

    return {
        "url": f"{BASE_URL}{LIVE_ORDER_ENDPOINT}?{query_string}&signature={signature}",
        "endpoint": LIVE_ORDER_ENDPOINT,
        "method": "POST",
        "headers": {
            "X-BB-APIKEY": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        "query_string": query_string,
        "signature": signature,
    }


class ToobitSpotOrderLiveTransport:
    """Fail-closed live Toobit spot order transport."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        session: Any = None,
        transport_enabled: bool = False,
        execution_enabled: bool = False,
        order_submission_enabled: bool = False,
        exchange_write_enabled: bool = False,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = session
        self.transport_enabled = transport_enabled
        self.execution_enabled = execution_enabled
        self.order_submission_enabled = order_submission_enabled
        self.exchange_write_enabled = exchange_write_enabled

    def submit(
        self,
        request: SpotLiveOrderRequest,
    ) -> SpotLiveOrderResult:
        valid, reason = validate_request(request)
        if not valid:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code=reason,
                error_message=reason,
                submitted_to_matching_engine=False,
            )

        if self.transport_enabled is not True:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="TRANSPORT_DISABLED",
                error_message="Toobit live spot transport is disabled.",
                submitted_to_matching_engine=False,
            )

        if self.execution_enabled is not True:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="EXECUTION_FLAG_INVALID",
                error_message="EXECUTION_ENABLED must be True.",
                submitted_to_matching_engine=False,
            )

        if self.order_submission_enabled is not True:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="ORDER_SUBMISSION_FLAG_INVALID",
                error_message="ORDER_SUBMISSION_ENABLED must be True.",
                submitted_to_matching_engine=False,
            )

        if self.exchange_write_enabled is not True:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="EXCHANGE_WRITE_FLAG_INVALID",
                error_message="EXCHANGE_WRITE_ENABLED must be True.",
                submitted_to_matching_engine=False,
            )

        if DATABASE_WRITE_ENABLED is not False:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="DATABASE_WRITE_FLAG_INVALID",
                error_message="DATABASE_WRITE_ENABLED must remain False.",
                submitted_to_matching_engine=False,
            )

        if not self.api_key or not self.api_secret:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="CREDENTIALS_REQUIRED",
                error_message="API credentials are required.",
                submitted_to_matching_engine=False,
            )

        if self.session is None:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="SESSION_REQUIRED",
                error_message="HTTP session is required.",
                submitted_to_matching_engine=False,
            )

        original_quantity = request.quantity

        try:
            prepared = build_request(
                request,
                api_key=self.api_key,
                secret_key=self.api_secret,
            )

            if prepared["endpoint"] != LIVE_ORDER_ENDPOINT:
                raise SpotLiveOrderContractError(
                    "ENDPOINT_CONTRACT_VIOLATION"
                )

            if "/api/v1/spot/orderTest" in prepared["url"]:
                raise SpotLiveOrderContractError(
                    "ORDER_TEST_ENDPOINT_FORBIDDEN"
                )

            post_url = (
                f"{BASE_URL}{LIVE_ORDER_ENDPOINT}"
            )

            post_body = (
                f"{prepared['query_string']}"
                f"&signature={prepared['signature']}"
            )

            response = self.session.post(
                post_url,
                headers=prepared["headers"],
                data=post_body,
            )

            if request.quantity != original_quantity:
                raise SpotLiveOrderContractError(
                    "QUANTITY_MUTATION"
                )

            try:
                response_body = response.json()
            except Exception:
                response_body = getattr(response, "text", None)

            accepted = response.status_code == 200
            exchange_order_id = (
                str(response_body.get("orderId"))
                if accepted
                and isinstance(response_body, dict)
                and response_body.get("orderId") is not None
                else None
            )

            provider_error_code = None
            provider_error_message = None
            if not accepted and isinstance(response_body, dict):
                raw_code = response_body.get("code")
                raw_message = response_body.get("msg")
                if raw_code is not None:
                    provider_error_code = str(raw_code)
                if raw_message is not None:
                    provider_error_message = str(raw_message)

            return SpotLiveOrderResult(
                accepted=accepted,
                status=(
                    "PASS"
                    if accepted
                    else (
                        "INCONCLUSIVE"
                        if response.status_code >= 500
                        else "REJECTED"
                    )
                ),
                http_status=response.status_code,
                response_body=response_body,
                error_code=None if accepted else (
                    provider_error_code or "HTTP_ERROR"
                ),
                error_message=None if accepted else (
                    provider_error_message or str(response.status_code)
                ),
                submitted_to_matching_engine=True,
                exchange_order_id=exchange_order_id,
            )

        except SpotLiveOrderContractError as exc:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="CONTRACT_ERROR",
                error_message=str(exc),
                submitted_to_matching_engine=False,
            )
        except Exception as exc:
            return SpotLiveOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="TRANSPORT_ERROR",
                error_message=str(exc),
                submitted_to_matching_engine=False,
            )


def self_check() -> dict[str, bool]:
    request = SpotLiveOrderRequest(
        symbol="BTCUSDT",
        side="SELL",
        order_type="LIMIT",
        time_in_force="GTC",
        quantity="1",
        quantity_unit="BASE_ASSET",
        price="40000",
        timestamp=1700000000000,
        new_client_order_id="LAB-SELF-001",
    )

    valid, _ = validate_request(request)
    query = build_query_string(build_query_params(request))
    signature = generate_signature(query, "secret")

    return {
        "request_valid": valid,
        "quantity_unchanged": request.quantity == "1",
        "query_nonempty": bool(query),
        "signature_sha256": len(signature) == 64,
        "execution_disabled": EXECUTION_ENABLED is False,
        "order_submission_disabled": ORDER_SUBMISSION_ENABLED is False,
        "exchange_write_disabled": EXCHANGE_WRITE_ENABLED is False,
        "database_write_disabled": DATABASE_WRITE_ENABLED is False,
    }


if __name__ == "__main__":
    checks = self_check()
    for name, passed in checks.items():
        print(f"{name}: {passed}")
    print("SELF CHECK RESULT : " + ("PASS" if all(checks.values()) else "FAIL"))
