from decimal import Decimal

from toobit_spot_order_test_transport_v0_1 import (
    ORDER_TEST_ENDPOINT,
    SpotOrderTestRequest,
    ToobitSpotOrderTestTransport,
    build_query_string,
    generate_signature,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = (
            {} if payload is None else payload
        )
        self.text = "{}"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.post_calls = []
        self.get_calls = []

    def post(self, *args, **kwargs):
        self.post_calls.append(
            (args, kwargs)
        )
        return FakeResponse(
            200,
            {},
        )

    def get(self, *args, **kwargs):
        self.get_calls.append(
            (args, kwargs)
        )
        raise AssertionError(
            "GET_MUST_NOT_BE_CALLED"
        )


class ForbiddenLiveOrderSession(FakeSession):

    def post(self, url, *args, **kwargs):

        if "/api/v1/spot/order?" in url:
            raise AssertionError(
                "LIVE_SPOT_ORDER_ENDPOINT_FORBIDDEN"
            )

        return super().post(
            url,
            *args,
            **kwargs,
        )


def make_limit_sell_request():

    return SpotOrderTestRequest(
        symbol="BTCUSDT",
        side="SELL",
        order_type="LIMIT",
        time_in_force="GTC",
        quantity=Decimal("1.25000000"),
        quantity_unit="BASE_ASSET",
        price=Decimal("40000"),
        timestamp=1700000000000,
    )


def make_market_buy_base_quantity_request():

    return SpotOrderTestRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("1"),
        quantity_unit="BASE_ASSET",
        timestamp=1700000000000,
    )


def make_market_buy_quote_quantity_request():

    return SpotOrderTestRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("400"),
        quantity_unit="QUOTE_ASSET",
        timestamp=1700000000000,
    )


def test_order_test_is_disabled_by_default():

    session = FakeSession()

    transport = ToobitSpotOrderTestTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
    )

    result = transport.order_test(
        make_limit_sell_request()
    )

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "ORDER_TEST_DISABLED"
    assert result.submitted_to_matching_engine is False
    assert session.post_calls == []


def test_exact_query_serialization():

    payload = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": Decimal("1.25"),
        "price": Decimal("40000"),
        "recvWindow": 5000,
        "timestamp": 1700000000000,
    }

    query = build_query_string(payload)

    assert query == (
        "symbol=BTCUSDT"
        "&side=SELL"
        "&type=LIMIT"
        "&timeInForce=GTC"
        "&quantity=1.25"
        "&price=40000"
        "&recvWindow=5000"
        "&timestamp=1700000000000"
    )


def test_signature_is_hmac_sha256():

    query = (
        "symbol=BTCUSDT"
        "&side=SELL"
        "&type=LIMIT"
        "&timeInForce=GTC"
        "&quantity=1"
        "&price=400"
        "&recvWindow=5000"
        "&timestamp=1700000000000"
    )

    signature = generate_signature(
        query,
        "TEST_SECRET",
    )

    assert len(signature) == 64
    assert signature == signature.lower()


def test_order_test_posts_only_to_order_test_endpoint():

    session = ForbiddenLiveOrderSession()

    transport = ToobitSpotOrderTestTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        order_test_enabled=True,
    )

    request = make_limit_sell_request()

    result = transport.order_test(
        request
    )

    assert result.status == "PASS"
    assert (
        result.endpoint
        == ORDER_TEST_ENDPOINT
    )
    assert (
        result.submitted_to_matching_engine
        is False
    )

    assert len(session.post_calls) == 1

    url = session.post_calls[0][0][0]

    assert (
        "/api/v1/spot/orderTest?"
        in url
    )

    assert (
        "/api/v1/spot/order?"
        not in url
    )


def test_request_quantity_is_not_mutated():

    session = FakeSession()

    transport = ToobitSpotOrderTestTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        order_test_enabled=True,
    )

    request = make_limit_sell_request()

    original_quantity = request.quantity

    result = transport.order_test(
        request
    )

    assert result.status == "PASS"
    assert request.quantity == original_quantity
    assert request.quantity == Decimal(
        "1.25000000"
    )


def test_market_buy_base_asset_is_fail_closed():

    session = FakeSession()

    transport = ToobitSpotOrderTestTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        order_test_enabled=True,
    )

    result = transport.order_test(
        make_market_buy_base_quantity_request()
    )

    assert result.status == "FAIL_CLOSED"
    assert (
        result.error_code
        == "MARKET_BUY_REQUIRES_QUOTE_ASSET_QUANTITY"
    )

    assert session.post_calls == []


def test_market_buy_quote_asset_is_accepted():

    session = FakeSession()

    transport = ToobitSpotOrderTestTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        order_test_enabled=True,
    )

    result = transport.order_test(
        make_market_buy_quote_quantity_request()
    )

    assert result.status == "PASS"
    assert (
        result.request_payload["quantity"]
        == Decimal("400")
    )

    assert (
        result.submitted_to_matching_engine
        is False
    )


def test_credentials_are_required():

    session = FakeSession()

    transport = ToobitSpotOrderTestTransport(
        api_key=None,
        api_secret=None,
        session=session,
        order_test_enabled=True,
    )

    result = transport.order_test(
        make_limit_sell_request()
    )

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "CREDENTIALS_REQUIRED"
    assert session.post_calls == []


def test_safety_flags_remain_disabled():

    from toobit_spot_order_test_transport_v0_1 import (
        DATABASE_WRITE_ENABLED,
        EXECUTION_ENABLED,
        EXCHANGE_WRITE_ENABLED,
        ORDER_SUBMISSION_ENABLED,
    )

    assert EXECUTION_ENABLED is False
    assert ORDER_SUBMISSION_ENABLED is False
    assert EXCHANGE_WRITE_ENABLED is False
    assert DATABASE_WRITE_ENABLED is False


def test_no_database_surface_exists_in_transport():

    session = FakeSession()

    transport = ToobitSpotOrderTestTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        order_test_enabled=True,
    )

    assert not hasattr(
        transport,
        "database",
    )

    assert not hasattr(
        transport,
        "db",
    )