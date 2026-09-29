from decimal import Decimal

from toobit_spot_order_live_transport_v0_1 import (
    LIVE_ORDER_ENDPOINT,
    SpotLiveOrderRequest,
    ToobitSpotOrderLiveTransport,
    build_query_string,
    generate_signature,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response=None):
        self.post_calls = []
        self.response = response or FakeResponse()

    def post(self, *args, **kwargs):
        self.post_calls.append((args, kwargs))
        return self.response


def make_limit_sell_request():
    return SpotLiveOrderRequest(
        symbol="BTCUSDT",
        side="SELL",
        order_type="LIMIT",
        time_in_force="GTC",
        quantity=Decimal("1.25000000"),
        quantity_unit="BASE_ASSET",
        price=Decimal("40000"),
        timestamp=1700000000000,
        new_client_order_id="LAB-0001",
    )


def test_live_order_is_fail_closed_by_default():
    session = FakeSession()
    transport = ToobitSpotOrderLiveTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
    )

    result = transport.submit(make_limit_sell_request())

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "TRANSPORT_DISABLED"
    assert result.submitted_to_matching_engine is False
    assert session.post_calls == []


def test_exact_query_serialization_and_signature():
    payload = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": Decimal("1.25"),
        "price": Decimal("40000"),
        "newClientOrderId": "LAB-0001",
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
        "&newClientOrderId=LAB-0001"
        "&recvWindow=5000"
        "&timestamp=1700000000000"
    )

    signature = generate_signature(query, "TEST_SECRET")
    assert len(signature) == 64
    assert signature == signature.lower()


def test_enabled_transport_posts_only_to_live_order_endpoint():
    session = FakeSession(
        FakeResponse(
            400,
            {"code": -2010, "msg": "insufficient balance"},
        )
    )
    transport = ToobitSpotOrderLiveTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        transport_enabled=True,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    request = make_limit_sell_request()
    result = transport.submit(request)

    assert result.status == "HTTP_ERROR"
    assert result.http_status == 400
    assert result.submitted_to_matching_engine is True
    assert result.error_code == "HTTP_ERROR"
    assert len(session.post_calls) == 1

    url = session.post_calls[0][0][0]
    assert "/api/v1/spot/order?" in url
    assert "/api/v1/spot/orderTest?" not in url


def test_quantity_is_not_mutated():
    session = FakeSession(
        FakeResponse(400, {"code": -2010, "msg": "insufficient balance"})
    )
    transport = ToobitSpotOrderLiveTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        transport_enabled=True,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    request = make_limit_sell_request()
    original_quantity = request.quantity

    transport.submit(request)

    assert request.quantity == original_quantity


def test_market_buy_base_asset_is_fail_closed():
    session = FakeSession()
    transport = ToobitSpotOrderLiveTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        transport_enabled=True,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    request = SpotLiveOrderRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        time_in_force=None,
        quantity=Decimal("1"),
        quantity_unit="BASE_ASSET",
        price=None,
        timestamp=1700000000000,
        new_client_order_id="LAB-0002",
    )

    result = transport.submit(request)

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "MARKET_BUY_REQUIRES_QUOTE_ASSET_QUANTITY"
    assert session.post_calls == []


def test_credentials_are_required_before_network():
    session = FakeSession()
    transport = ToobitSpotOrderLiveTransport(
        api_key=None,
        api_secret=None,
        session=session,
        transport_enabled=True,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    result = transport.submit(make_limit_sell_request())

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "CREDENTIALS_REQUIRED"
    assert session.post_calls == []


def test_database_write_is_never_enabled():
    from toobit_spot_order_live_transport_v0_1 import DATABASE_WRITE_ENABLED

    assert DATABASE_WRITE_ENABLED is False

def test_live_transport_preserves_exchange_order_id_on_acceptance():
    session = FakeSession(
        FakeResponse(
            200,
            {
                "orderId": "TOOBIT-ORDER-1",
                "status": "FILLED",
            },
        )
    )
    transport = ToobitSpotOrderLiveTransport(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        session=session,
        transport_enabled=True,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    result = transport.submit(make_limit_sell_request())

    assert result.status == "PASS"
    assert result.accepted is True
    assert result.exchange_order_id == "TOOBIT-ORDER-1"
