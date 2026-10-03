"""CP49 execution-boundary regression tests.

No live exchange, DB, or production runtime is used. These tests prove that:
1) an eligible canonical request reaches the existing execution boundary; and
2) the Toobit transport preserves a real provider rejection as execution evidence.
"""

from dataclasses import dataclass, field

import cp49_live_execution_bridge_v0_1 as bridge
from exchange_execution_contract import CanonicalOrderRequest
from toobit_spot_order_live_transport_v0_1 import (
    SpotLiveOrderRequest,
    ToobitSpotOrderLiveTransport,
)


def _request():
    return CanonicalOrderRequest(
        asset="BTCUSDT",
        direction="LONG",
        order_type="MARKET",
        quantity="0.001",
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=None,
        reference_price="100000",
        intent_id="INT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-10-03T00:00:00+00:00",
        decision_id="DEC-1",
    )


@dataclass
class _Account:
    status: str = "PASS"
    account_id: str = "ACC-1"
    source_id: str = "ACC-SRC-1"
    retrieved_at: str = "2026-10-03T00:00:00+00:00"


@dataclass
class _Observation:
    account: _Account = field(default_factory=_Account)


@dataclass
class _ApiKey:
    allowed: bool = True
    status: str = "PASS"
    operation: str = "api_key_check"
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {"account_type": "SPOT"}


@dataclass
class _Evidence:
    def validate(self):
        return True


@dataclass
class _ReadinessState:
    value: str = "READY_FOR_AUTHORIZATION"


@dataclass
class _Readiness:
    state: _ReadinessState = field(default_factory=_ReadinessState)


@dataclass
class _Handoff:
    pass


@dataclass
class _Preflight:
    status: str = "PASS"
    handoff: _Handoff = field(default_factory=_Handoff)


class _Adapter:
    api_key = "key"
    api_secret = "secret"
    session = object()
    live_order_transport = None

    def api_key_check(self):
        return _ApiKey()


def test_cp46d_pass_reaches_cp49_execution_boundary(monkeypatch):
    calls = []

    monkeypatch.setattr(
        bridge,
        "build_account_balance_observation",
        lambda adapter: _Observation(),
    )
    monkeypatch.setattr(
        bridge,
        "build_account_signature_evidence",
        lambda **kwargs: _Evidence(),
    )
    monkeypatch.setattr(
        bridge,
        "build_execution_eligibility",
        lambda request, handoff: object(),
    )
    monkeypatch.setattr(
        bridge,
        "evaluate_first_execution_readiness",
        lambda **kwargs: _Readiness(),
    )
    monkeypatch.setattr(
        bridge,
        "build_execution_safety_gate",
        lambda **kwargs: object(),
    )

    expected = object()

    def fake_execute_order(**kwargs):
        calls.append(kwargs["request"].asset)
        return expected

    monkeypatch.setattr(bridge, "execute_order", fake_execute_order)

    result = bridge.execute_canonical_request(
        adapter=_Adapter(),
        request=_request(),
        provider_preflight_result=_Preflight(),
        management_authorized=False,
    )

    assert result is expected
    assert calls == ["BTCUSDT"]


class _Response:
    status_code = 400
    text = '{"code":-2010,"msg":"insufficient balance"}'

    def json(self):
        return {"code": -2010, "msg": "insufficient balance"}


class _Session:
    def __init__(self):
        self.calls = []

    def post(self, url, headers):
        self.calls.append((url, headers))
        return _Response()


def test_toobit_rejection_is_preserved_as_real_provider_evidence():
    session = _Session()
    transport = ToobitSpotOrderLiveTransport(
        api_key="key",
        api_secret="secret",
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
        quantity="0.001",
        quantity_unit="QUOTE_ASSET",
        price=None,
        timestamp=1769990400000,
        new_client_order_id="ARUNDA-CP49-1",
    )

    result = transport.submit(request)

    assert len(session.calls) == 1
    assert "/api/v1/spot/order?" in session.calls[0][0]
    assert "/api/v1/spot/orderTest" not in session.calls[0][0]
    assert result.accepted is False
    assert result.status == "REJECTED"
    assert result.http_status == 400
    assert result.submitted_to_matching_engine is True
    assert result.error_code == "-2010"
    assert result.exchange_order_id is None
