"""
ARUNDA TRADER
TOOBIT FUTURES V2 ORDER TRANSPORT v0.1

CP46-A5

CONTRACT-ONLY TRANSPORT.

NO LIVE EXECUTION BY DEFAULT.
NO DATABASE WRITE.
NO QUANTITY CONVERSION.
NO LEVERAGE CALCULATION.
NO MARGIN CALCULATION.
NO CONTRACT-MULTIPLIER CONVERSION.

Provider semantics:
    Toobit Futures V2 quantity = CONTRACTS.

Canonical quantity semantics:
    Arunda canonical quantity remains BASE_ASSET.

Therefore:
    This transport MUST NOT translate BASE_ASSET -> CONTRACTS.

Any such translation requires a separate,
explicitly authorized provider-translation contract.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional


BASE_URL = "https://api.toobit.com"
ORDER_ENDPOINT = "/api/v2/futures/order"

EXECUTION_ENABLED = False
ORDER_SUBMISSION_ENABLED = False
EXCHANGE_WRITE_ENABLED = False
DATABASE_WRITE_ENABLED = False

RECV_WINDOW = 5000

VALID_SIDES = frozenset({"BUY", "SELL"})
VALID_POSITION_SIDES = frozenset({"LONG", "SHORT"})
VALID_ORDER_TYPES = frozenset({"LIMIT", "MARKET"})
VALID_TIME_IN_FORCE = frozenset(
    {"GTC", "FOK", "IOC", "POST_ONLY"}
)


class FuturesOrderContractError(ValueError):
    """Fail-closed provider contract violation."""


@dataclass(frozen=True)
class ToobitFuturesOrderRequest:
    symbol: str
    side: str
    position_side: str
    order_type: str
    quantity: Any
    quantity_unit: str
    new_client_order_id: str
    timestamp: int
    recv_window: int = RECV_WINDOW
    price: Optional[Any] = None
    time_in_force: Optional[str] = None
    category: str = "USDT"


@dataclass(frozen=True)
class ToobitFuturesOrderResult:
    accepted: bool
    status: str
    http_status: Optional[int]
    response_body: Optional[Any]
    error_code: Optional[str]
    error_message: Optional[str]


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    if value is None:
        raise FuturesOrderContractError(
            "NULL_SCALAR_FORBIDDEN"
        )

    return str(value)


def validate_request(
    request: ToobitFuturesOrderRequest,
) -> tuple[bool, str]:

    if not isinstance(request, ToobitFuturesOrderRequest):
        return False, "REQUEST_TYPE_INVALID"

    if not request.symbol.strip():
        return False, "SYMBOL_INVALID"

    if request.side not in VALID_SIDES:
        return False, "SIDE_INVALID"

    if request.position_side not in VALID_POSITION_SIDES:
        return False, "POSITION_SIDE_INVALID"

    if request.order_type not in VALID_ORDER_TYPES:
        return False, "ORDER_TYPE_INVALID"

    if request.quantity_unit != "CONTRACTS":
        return False, "QUANTITY_UNIT_MUST_BE_CONTRACTS"

    if request.quantity is None:
        return False, "QUANTITY_UNAVAILABLE"

    if str(request.quantity).strip() == "":
        return False, "QUANTITY_INVALID"

    if not request.new_client_order_id.strip():
        return False, "CLIENT_ORDER_ID_INVALID"

    if request.timestamp <= 0:
        return False, "TIMESTAMP_INVALID"

    if request.recv_window <= 0:
        return False, "RECV_WINDOW_INVALID"

    if request.category not in {"USDT", "USDC"}:
        return False, "CATEGORY_INVALID"

    if request.order_type == "LIMIT":
        if request.price is None:
            return False, "LIMIT_PRICE_REQUIRED"

        if str(request.price).strip() == "":
            return False, "LIMIT_PRICE_INVALID"

    if request.order_type == "MARKET":
        if request.price is not None:
            return False, "MARKET_PRICE_FORBIDDEN"

    if request.time_in_force is not None:
        if request.time_in_force not in VALID_TIME_IN_FORCE:
            return False, "TIME_IN_FORCE_INVALID"

    return True, "VALID"


def build_query_params(
    request: ToobitFuturesOrderRequest,
) -> dict[str, str]:

    valid, reason = validate_request(request)

    if not valid:
        raise FuturesOrderContractError(reason)

    return {
        "category": _scalar(request.category),
        "timestamp": _scalar(request.timestamp),
        "recvWindow": _scalar(request.recv_window),
    }


def build_query_string(
    params: Mapping[str, Any],
) -> str:

    if not isinstance(params, Mapping):
        raise FuturesOrderContractError(
            "QUERY_PARAMS_INVALID"
        )

    return "&".join(
        f"{key}={_scalar(value)}"
        for key, value in params.items()
    )


def build_json_body(
    request: ToobitFuturesOrderRequest,
) -> str:

    valid, reason = validate_request(request)

    if not valid:
        raise FuturesOrderContractError(reason)

    body: dict[str, Any] = {
        "newClientOrderId": request.new_client_order_id,
        "symbol": request.symbol,
        "side": request.side,
        "positionSide": request.position_side,
        "type": request.order_type,
        "quantity": _scalar(request.quantity),
    }

    if request.order_type == "LIMIT":
        body["price"] = _scalar(request.price)

        if request.time_in_force is not None:
            body["timeInForce"] = request.time_in_force

    elif request.time_in_force is not None:
        body["timeInForce"] = request.time_in_force

    return json.dumps(
        body,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def build_signing_payload(
    query_string: str,
    raw_json_body: str,
) -> str:

    if not query_string:
        raise FuturesOrderContractError(
            "QUERY_STRING_EMPTY"
        )

    if not raw_json_body:
        raise FuturesOrderContractError(
            "JSON_BODY_EMPTY"
        )

    if "\n" in raw_json_body or "\r" in raw_json_body:
        raise FuturesOrderContractError(
            "JSON_BODY_NEWLINE_FORBIDDEN"
        )

    # Official V2 rule:
    # queryString + rawJsonBody
    # NO '&' between them.
    return query_string + raw_json_body


def generate_signature(
    secret_key: str,
    signing_payload: str,
) -> str:

    if not secret_key:
        raise FuturesOrderContractError(
            "SECRET_KEY_REQUIRED"
        )

    if not signing_payload:
        raise FuturesOrderContractError(
            "SIGNING_PAYLOAD_EMPTY"
        )

    return hmac.new(
        secret_key.encode("utf-8"),
        signing_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_request(
    request: ToobitFuturesOrderRequest,
    *,
    api_key: str,
    secret_key: str,
) -> dict[str, Any]:

    if not api_key:
        raise FuturesOrderContractError(
            "API_KEY_REQUIRED"
        )

    if not secret_key:
        raise FuturesOrderContractError(
            "SECRET_KEY_REQUIRED"
        )

    query_params = build_query_params(request)
    query_string = build_query_string(query_params)
    raw_json_body = build_json_body(request)

    signing_payload = build_signing_payload(
        query_string,
        raw_json_body,
    )

    signature = generate_signature(
        secret_key,
        signing_payload,
    )

    return {
        "url": (
            f"{BASE_URL}{ORDER_ENDPOINT}"
            f"?{query_string}&signature={signature}"
        ),
        "endpoint": ORDER_ENDPOINT,
        "method": "POST",
        "headers": {
            "X-BB-APIKEY": api_key,
            "Content-Type": "application/json",
        },
        "query_string": query_string,
        "raw_json_body": raw_json_body,
        "signing_payload": signing_payload,
        "signature": signature,
    }


class ToobitFuturesOrderTransport:

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        session: Any = None,
        enabled: bool = False,
    ) -> None:

        self.api_key = api_key
        self.secret_key = secret_key
        self.session = session
        self.enabled = enabled

    def submit(
        self,
        request: ToobitFuturesOrderRequest,
    ) -> ToobitFuturesOrderResult:

        valid, reason = validate_request(request)

        if not valid:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code=reason,
                error_message=reason,
            )

        # =========================================================
        # CP46-A5 HARD SAFETY BOUNDARY
        #
        # No credentials inspection.
        # No request construction.
        # No signing.
        # No HTTP session access.
        # No POST.
        #
        # until the transport safety boundary has been evaluated.
        # =========================================================

        if self.enabled is not True:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="TRANSPORT_DISABLED",
                error_message=(
                    "Toobit Futures transport is disabled."
                ),
            )

                # =========================================================
        # CP46-A5 HARD SAFETY BOUNDARY
        #
        # Current CP46-A5 contract is NON-EXECUTABLE.
        #
        # No credentials inspection.
        # No request construction.
        # No signing.
        # No HTTP session access.
        # No POST.
        #
        # unless the required execution permissions are explicitly
        # enabled.
        # =========================================================

        if EXECUTION_ENABLED is not True:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="EXECUTION_FLAG_INVALID",
                error_message=(
                    "EXECUTION_ENABLED must be True "
                    "for exchange submission."
                ),
            )

        if ORDER_SUBMISSION_ENABLED is not True:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="ORDER_SUBMISSION_FLAG_INVALID",
                error_message=(
                    "ORDER_SUBMISSION_ENABLED must be True "
                    "for exchange submission."
                ),
            )

        if EXCHANGE_WRITE_ENABLED is not True:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="EXCHANGE_WRITE_FLAG_INVALID",
                error_message=(
                    "EXCHANGE_WRITE_ENABLED must be True "
                    "for exchange submission."
                ),
            )

        if DATABASE_WRITE_ENABLED is not False:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="DATABASE_WRITE_FLAG_INVALID",
                error_message=(
                    "DATABASE_WRITE_ENABLED must remain False."
                ),
            )

        # =========================================================
        # Only after the complete safety boundary passes may the
        # transport inspect credentials/session or construct HTTP.
        # =========================================================

        # =========================================================
        # Only after the complete safety boundary passes may the
        # transport inspect credentials/session or construct HTTP.
        # =========================================================

        if self.api_key is None or self.secret_key is None:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="CREDENTIALS_REQUIRED",
                error_message=(
                    "API credentials are required."
                ),
            )

        if self.session is None:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="SESSION_REQUIRED",
                error_message=(
                    "HTTP session is required."
                ),
            )

        try:
            prepared = build_request(
                request,
                api_key=self.api_key,
                secret_key=self.secret_key,
            )

            url = prepared["url"]

            if ORDER_ENDPOINT not in url:
                raise FuturesOrderContractError(
                    "ENDPOINT_CONTRACT_VIOLATION"
                )

            if "/api/v1/futures/order" in url:
                raise FuturesOrderContractError(
                    "V1_ENDPOINT_FORBIDDEN"
                )

            response = self.session.post(
                url,
                headers=prepared["headers"],
                data=prepared["raw_json_body"],
            )

            return ToobitFuturesOrderResult(
                accepted=response.status_code == 200,
                status=(
                    "PASS"
                    if response.status_code == 200
                    else "HTTP_ERROR"
                ),
                http_status=response.status_code,
                response_body=getattr(
                    response,
                    "json",
                    lambda: None,
                )(),
                error_code=(
                    None
                    if response.status_code == 200
                    else "HTTP_ERROR"
                ),
                error_message=(
                    None
                    if response.status_code == 200
                    else str(response.status_code)
                ),
            )

        except FuturesOrderContractError as exc:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="CONTRACT_ERROR",
                error_message=str(exc),
            )

        except Exception as exc:
            return ToobitFuturesOrderResult(
                accepted=False,
                status="FAIL_CLOSED",
                http_status=None,
                response_body=None,
                error_code="TRANSPORT_ERROR",
                error_message=str(exc),
            )


def self_check() -> dict[str, bool]:

    request = ToobitFuturesOrderRequest(
        symbol="BTC-SWAP-USDT",
        side="SELL",
        position_side="SHORT",
        order_type="LIMIT",
        quantity="10",
        quantity_unit="CONTRACTS",
        new_client_order_id="A5-TEST-001",
        timestamp=1700000000000,
        price="30000",
        time_in_force="GTC",
    )

    valid, _ = validate_request(request)

    body = build_json_body(request)

    query = build_query_string(
        build_query_params(request)
    )

    payload = build_signing_payload(
        query,
        body,
    )

    signature = generate_signature(
        "secret",
        payload,
    )

    return {
        "request_valid": valid,
        "quantity_unit_contracts": (
            request.quantity_unit == "CONTRACTS"
        ),
        "quantity_unchanged": request.quantity == "10",
        "body_compact": "\n" not in body,
        "body_nonempty": bool(body),
        "signature_sha256": len(signature) == 64,
        "signature_lowercase": signature == signature.lower(),
        "execution_disabled": (
            EXECUTION_ENABLED is False
        ),
        "order_submission_disabled": (
            ORDER_SUBMISSION_ENABLED is False
        ),
        "exchange_write_disabled": (
            EXCHANGE_WRITE_ENABLED is False
        ),
        "database_write_disabled": (
            DATABASE_WRITE_ENABLED is False
        ),
    }


if __name__ == "__main__":
    checks = self_check()

    for name, passed in checks.items():
        print(f"{name}: {passed}")

    print(
        "SELF CHECK RESULT : "
        + ("PASS" if all(checks.values()) else "FAIL")
    )