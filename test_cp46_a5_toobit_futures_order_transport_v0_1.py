"""
CP46-A5
TOOBIT FUTURES V2 ORDER TRANSPORT TESTS

Scope:
    - Provider transport contract
    - Futures V2 semantics
    - Deterministic JSON serialization
    - Exact signing payload
    - HMAC-SHA256
    - Fail-closed safety behavior

Forbidden:
    - Live exchange execution
    - Real credentials
    - Database writes
    - Quantity conversion
    - Leverage calculation
    - Margin calculation
    - Contract-multiplier conversion
"""

import hashlib
import hmac
import json

import toobit_futures_order_transport_v0_1 as transport


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {
            "code": 200,
            "msg": "success",
        }

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(
            {
                "url": url,
                "kwargs": kwargs,
            }
        )
        return FakeResponse()


class ForbiddenSession:
    def __init__(self):
        self.post_called = False

    def post(self, *args, **kwargs):
        self.post_called = True
        raise AssertionError(
            "HTTP POST MUST NOT OCCUR IN CP46-A5 TESTS"
        )


def make_request(**overrides):
    values = {
        "symbol": "BTC-SWAP-USDT",
        "side": "SELL",
        "position_side": "SHORT",
        "order_type": "LIMIT",
        "quantity": "10",
        "quantity_unit": "CONTRACTS",
        "new_client_order_id": "A5-TEST-001",
        "timestamp": 1700000000000,
        "recv_window": 5000,
        "price": "30000",
        "time_in_force": "GTC",
        "category": "USDT",
    }

    values.update(overrides)

    return transport.ToobitFuturesOrderRequest(
        **values
    )


def test_transport_disabled_before_http():
    session = ForbiddenSession()

    client = transport.ToobitFuturesOrderTransport(
        api_key="test-api-key",
        secret_key="test-secret-key",
        session=session,
        enabled=False,
    )

    result = client.submit(make_request())

    assert result.accepted is False
    assert result.status == "FAIL_CLOSED"
    assert result.http_status is None
    assert result.response_body is None
    assert result.error_code == "TRANSPORT_DISABLED"
    assert session.post_called is False


def test_quantity_unit_must_be_contracts():
    request = make_request(
        quantity_unit="BASE_ASSET",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == (
        "QUANTITY_UNIT_MUST_BE_CONTRACTS"
    )


def test_quantity_is_not_converted():
    request = make_request(
        quantity="10",
    )

    body = transport.build_json_body(request)

    parsed = json.loads(body)

    assert parsed["quantity"] == "10"


def test_quantity_preserves_exact_provider_value():
    request = make_request(
        quantity="10.5000",
    )

    body = transport.build_json_body(request)

    parsed = json.loads(body)

    assert parsed["quantity"] == "10.5000"


def test_position_side_is_explicit():
    request = make_request(
        side="SELL",
        position_side="SHORT",
    )

    body = json.loads(
        transport.build_json_body(request)
    )

    assert body["side"] == "SELL"
    assert body["positionSide"] == "SHORT"


def test_long_and_short_are_distinct():
    long_request = make_request(
        side="BUY",
        position_side="LONG",
    )

    short_request = make_request(
        side="SELL",
        position_side="SHORT",
    )

    long_body = json.loads(
        transport.build_json_body(long_request)
    )

    short_body = json.loads(
        transport.build_json_body(short_request)
    )

    assert long_body["side"] == "BUY"
    assert long_body["positionSide"] == "LONG"

    assert short_body["side"] == "SELL"
    assert short_body["positionSide"] == "SHORT"


def test_invalid_side_fail_closed():
    request = make_request(
        side="SELL_OPEN",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "SIDE_INVALID"


def test_invalid_position_side_fail_closed():
    request = make_request(
        position_side="SELL",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "POSITION_SIDE_INVALID"


def test_market_order_forbids_price():
    request = make_request(
        order_type="MARKET",
        price="30000",
        time_in_force=None,
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "MARKET_PRICE_FORBIDDEN"


def test_market_order_without_price_is_valid():
    request = make_request(
        order_type="MARKET",
        price=None,
        time_in_force=None,
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is True
    assert reason == "VALID"


def test_limit_order_requires_price():
    request = make_request(
        order_type="LIMIT",
        price=None,
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "LIMIT_PRICE_REQUIRED"


def test_client_order_id_required():
    request = make_request(
        new_client_order_id="",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "CLIENT_ORDER_ID_INVALID"


def test_json_is_compact_and_single_line():
    request = make_request()

    body = transport.build_json_body(request)

    assert "\n" not in body
    assert "\r" not in body
    assert " " not in body


def test_json_body_is_valid_json():
    request = make_request()

    body = transport.build_json_body(request)

    parsed = json.loads(body)

    assert isinstance(parsed, dict)


def test_json_body_contains_required_futures_fields():
    request = make_request()

    body = json.loads(
        transport.build_json_body(request)
    )

    assert body["newClientOrderId"] == (
        "A5-TEST-001"
    )
    assert body["symbol"] == "BTC-SWAP-USDT"
    assert body["side"] == "SELL"
    assert body["positionSide"] == "SHORT"
    assert body["type"] == "LIMIT"
    assert body["quantity"] == "10"
    assert body["price"] == "30000"


def test_limit_time_in_force_is_preserved():
    request = make_request(
        time_in_force="GTC",
    )

    body = json.loads(
        transport.build_json_body(request)
    )

    assert body["timeInForce"] == "GTC"


def test_market_body_does_not_contain_price():
    request = make_request(
        order_type="MARKET",
        price=None,
        time_in_force=None,
    )

    body = json.loads(
        transport.build_json_body(request)
    )

    assert body["type"] == "MARKET"
    assert "price" not in body


def test_query_string_is_deterministic():
    request = make_request()

    params = transport.build_query_params(
        request
    )

    query_1 = transport.build_query_string(
        params
    )

    query_2 = transport.build_query_string(
        params
    )

    assert query_1 == query_2


def test_query_string_contains_expected_fields():
    request = make_request(
        timestamp=1700000000000,
        recv_window=5000,
    )

    params = transport.build_query_params(
        request
    )

    query = transport.build_query_string(
        params
    )

    assert (
        query
        == "category=USDT"
        "&timestamp=1700000000000"
        "&recvWindow=5000"
    )


def test_signature_uses_query_plus_raw_json_without_ampersand():
    request = make_request()

    query = transport.build_query_string(
        transport.build_query_params(request)
    )

    body = transport.build_json_body(request)

    payload = transport.build_signing_payload(
        query,
        body,
    )

    expected = query + body

    assert payload == expected
    assert payload != (
        query + "&" + body
    )


def test_signing_payload_preserves_exact_raw_body():
    request = make_request()

    query = transport.build_query_string(
        transport.build_query_params(request)
    )

    body = transport.build_json_body(request)

    payload = transport.build_signing_payload(
        query,
        body,
    )

    assert payload.endswith(body)
    assert payload == query + body


def test_signature_matches_hmac_sha256():
    request = make_request()

    query = transport.build_query_string(
        transport.build_query_params(request)
    )

    body = transport.build_json_body(request)

    payload = query + body

    expected = hmac.new(
        b"test-secret",
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    actual = transport.generate_signature(
        "test-secret",
        payload,
    )

    assert actual == expected


def test_signature_is_sha256_hex():
    request = make_request()

    query = transport.build_query_string(
        transport.build_query_params(request)
    )

    body = transport.build_json_body(request)

    signature = transport.generate_signature(
        "test-secret",
        query + body,
    )

    assert len(signature) == 64
    assert all(
        character in "0123456789abcdef"
        for character in signature
    )


def test_endpoint_is_futures_v2():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    assert prepared["endpoint"] == (
        "/api/v2/futures/order"
    )

    assert "/api/v2/futures/order" in (
        prepared["url"]
    )

    assert "/api/v1/futures/order" not in (
        prepared["url"]
    )


def test_request_method_is_post():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    assert prepared["method"] == "POST"


def test_api_key_is_sent_as_header():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    assert prepared["headers"]["X-BB-APIKEY"] == (
        "test-api-key"
    )


def test_content_type_is_json():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    assert prepared["headers"]["Content-Type"] == (
        "application/json"
    )


def test_prepared_body_equals_signed_body():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    expected_payload = (
        prepared["query_string"]
        + prepared["raw_json_body"]
    )

    assert prepared["signing_payload"] == (
        expected_payload
    )


def test_prepared_signature_matches_payload():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    expected_signature = hmac.new(
        b"test-secret-key",
        prepared["signing_payload"].encode(
            "utf-8"
        ),
        hashlib.sha256,
    ).hexdigest()

    assert prepared["signature"] == (
        expected_signature
    )


def test_credentials_required():
    request = make_request()

    try:
        transport.build_request(
            request,
            api_key="",
            secret_key="test-secret-key",
        )
    except transport.FuturesOrderContractError as exc:
        assert str(exc) == "API_KEY_REQUIRED"
    else:
        raise AssertionError(
            "Missing API key must fail closed"
        )


def test_secret_required():
    request = make_request()

    try:
        transport.build_request(
            request,
            api_key="test-api-key",
            secret_key="",
        )
    except transport.FuturesOrderContractError as exc:
        assert str(exc) == "SECRET_KEY_REQUIRED"
    else:
        raise AssertionError(
            "Missing secret key must fail closed"
        )


def test_enabled_transport_still_fails_closed():
    session = ForbiddenSession()

    client = transport.ToobitFuturesOrderTransport(
        api_key="test-api-key",
        secret_key="test-secret-key",
        session=session,
        enabled=True,
    )

    result = client.submit(make_request())

    assert result.accepted is False
    assert result.status == "FAIL_CLOSED"
    assert result.http_status is None
    assert result.response_body is None

    assert result.error_code in {
        "EXECUTION_FLAG_INVALID",
        "ORDER_SUBMISSION_FLAG_INVALID",
        "EXCHANGE_WRITE_FLAG_INVALID",
        "DATABASE_WRITE_FLAG_INVALID",
    }

    assert session.post_called is False


def test_no_http_when_execution_safety_lock_is_active():
    session = ForbiddenSession()

    client = transport.ToobitFuturesOrderTransport(
        api_key="test-api-key",
        secret_key="test-secret-key",
        session=session,
        enabled=True,
    )

    result = client.submit(make_request())

    assert result.status == "FAIL_CLOSED"
    assert session.post_called is False


def test_no_quantity_translation_surface():
    request = make_request(
        quantity="10",
    )

    body = json.loads(
        transport.build_json_body(request)
    )

    assert body["quantity"] == "10"

    assert "contractMultiplier" not in body
    assert "baseAssetQuantity" not in body
    assert "convertedQuantity" not in body


def test_contract_multiplier_is_not_used():
    request = make_request(
        quantity="10",
    )

    body = json.loads(
        transport.build_json_body(request)
    )

    assert "contractMultiplier" not in body


def test_no_leverage_field_is_injected():
    request = make_request()

    body = json.loads(
        transport.build_json_body(request)
    )

    assert "leverage" not in body


def test_no_margin_calculation_surface():
    request = make_request()

    body = json.loads(
        transport.build_json_body(request)
    )

    assert "margin" not in body
    assert "marginAmount" not in body


def test_safety_flags_are_false():
    assert transport.EXECUTION_ENABLED is False

    assert (
        transport.ORDER_SUBMISSION_ENABLED
        is False
    )

    assert (
        transport.EXCHANGE_WRITE_ENABLED
        is False
    )

    assert (
        transport.DATABASE_WRITE_ENABLED
        is False
    )


def test_database_write_is_disabled():
    assert (
        transport.DATABASE_WRITE_ENABLED
        is False
    )


def test_invalid_order_type_fail_closed():
    request = make_request(
        order_type="STOP",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "ORDER_TYPE_INVALID"


def test_invalid_category_fail_closed():
    request = make_request(
        category="INVALID",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "CATEGORY_INVALID"


def test_invalid_time_in_force_fail_closed():
    request = make_request(
        time_in_force="INVALID",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "TIME_IN_FORCE_INVALID"


def test_invalid_timestamp_fail_closed():
    request = make_request(
        timestamp=0,
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "TIMESTAMP_INVALID"


def test_invalid_recv_window_fail_closed():
    request = make_request(
        recv_window=0,
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "RECV_WINDOW_INVALID"


def test_empty_symbol_fail_closed():
    request = make_request(
        symbol="",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "SYMBOL_INVALID"


def test_empty_quantity_fail_closed():
    request = make_request(
        quantity="",
    )

    valid, reason = transport.validate_request(
        request
    )

    assert valid is False
    assert reason == "QUANTITY_INVALID"


def test_self_check_passes():
    checks = transport.self_check()

    assert checks
    assert all(checks.values())


def test_no_database_surface():
    module_names = dir(transport)

    assert "sqlite3" not in module_names
    assert "DATABASE_WRITE_ENABLED" in module_names
    assert (
        transport.DATABASE_WRITE_ENABLED
        is False
    )


def test_no_live_endpoint_alias():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="test-api-key",
        secret_key="test-secret-key",
    )

    url = prepared["url"]

    assert "/api/v2/futures/order" in url
    assert "/api/v1/futures/order" not in url


def test_transport_result_is_fail_closed_on_http_error():
    class ErrorResponse:
        status_code = 400

        def json(self):
            return {
                "code": 400,
                "msg": "test error",
            }

    class ErrorSession:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append(
                {
                    "url": url,
                    "kwargs": kwargs,
                }
            )
            return ErrorResponse()

    # The global safety lock is intentionally disabled,
    # therefore transport must fail before HTTP.
    session = ErrorSession()

    client = transport.ToobitFuturesOrderTransport(
        api_key="test-api-key",
        secret_key="test-secret-key",
        session=session,
        enabled=True,
    )

    result = client.submit(make_request())

    assert result.accepted is False
    assert result.status == "FAIL_CLOSED"
    assert session.calls == []


def test_no_real_credentials_are_required():
    request = make_request()

    prepared = transport.build_request(
        request,
        api_key="TEST_ONLY",
        secret_key="TEST_ONLY",
    )

    assert prepared["headers"]["X-BB-APIKEY"] == (
        "TEST_ONLY"
    )

    assert prepared["signature"]
