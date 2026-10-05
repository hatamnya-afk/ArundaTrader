"""CP49 execution-boundary regression tests.

No live exchange, DB, or production runtime is used. These tests prove that:
1) an eligible canonical request reaches the existing execution boundary; and
2) the Toobit transport preserves a real provider rejection as execution evidence.
"""

from dataclasses import dataclass, field

import cp49_live_execution_bridge_v0_1 as bridge
from exchange_execution_contract import CanonicalOrderRequest
from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
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


def _provider_request():
    from provider_order_translation_v0_1 import ProviderOrderRequest

    return ProviderOrderRequest(
        venue="SPOT",
        symbol="BTCUSDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity="0.001",
        quantity_unit="BASE_ASSET",
        entry_price=None,
        intent_id="INT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-10-03T00:00:00+00:00",
        decision_id="DEC-1",
    )


def _handoff():
    from cp46_d_provider_execution_handoff_v0_1 import (
        ProviderExecutionHandoffResult,
    )

    preflight = type(
        "_ProviderPreflight",
        (),
        {"status": "PASS"},
    )()

    return ProviderExecutionHandoffResult(
        status="PASS",
        reason="PASS",
        message="Provider translation and preflight handoff passed.",
        provider_request=_provider_request(),
        preflight=preflight,
    )


@dataclass
class _Preflight:
    status: str = "PASS"
    handoff: object = field(default_factory=_handoff)


class _Adapter:
    api_key = "key"
    api_secret = "secret"
    session = object()
    live_order_transport = None

    def authorize_first_execution(self, safety_gate):
        return True

    def capabilities(self):
        return {
            "ORDER_SUBMISSION": True,
            "ACCOUNT_READ": True,
            "BALANCE_READ": True,
        }

    def api_key_check(self):
        return _ApiKey()

    def get_account(self):
        from toobit_trading_adapter import AdapterResult

        return AdapterResult(
            status="PASS",
            allowed=True,
            operation="account_check",
            reason="test account read",
            data={
                "account_id": "TEST-ACCOUNT",
                "account_type": "SPOT",
                "environment": "LIVE",
                "source_id": "TEST-SOURCE",
                "source_type": "TOOBIT_ACCOUNT",
                "source_timestamp": "2026-10-04T00:00:00+00:00",
            },
        )

    def get_balances(self):
        from toobit_trading_adapter import AdapterResult

        return AdapterResult(
            status="PASS",
            allowed=True,
            operation="balance_check",
            reason="test balance read",
            data={
                "source_id": "TEST-SOURCE",
                "source_type": "TOOBIT_BALANCE",
                "source_timestamp": "2026-10-04T00:00:00+00:00",
                "balances": [
                    {
                        "asset": "USDT",
                        "free": "1000",
                        "locked": "0",
                        "total": "1000",
                    }
                ],
            },
        )

def test_cp46d_pass_reaches_cp49_execution_boundary(monkeypatch):
    calls = []

    monkeypatch.setattr(
        bridge,
        "build_execution_eligibility",
        lambda request, handoff: ExecutionEligibilityResult(
            status=EligibilityStatus.PASS,
            reason="PASS",
            message="provider preflight passed",
            canonical_request=request,
        ),
    )

    monkeypatch.setattr(
        bridge,
        "evaluate_first_execution_readiness",
        lambda **kwargs: _Readiness(),
    )

    from cp49_first_execution_contract_v0_1 import ExecutionSafetyGate

    monkeypatch.setattr(
        bridge,
        "build_execution_safety_gate",
        lambda **kwargs: ExecutionSafetyGate(
            management_authorized=True,
            implementation_verified=True,
            prior_attempt_exists=False,
            execution_enabled=True,
            order_submission_enabled=True,
            exchange_write_enabled=True,
            automatic_retry_enabled=False,
        ),
    )

    from cp46_g_binding_execution_consumer_handoff_v0_1 import (
        ConsumerHandoffStatus,
        ProviderExecutionConsumerHandoffResult,
    )
    from exchange_execution_contract import CanonicalExecutionResult

    expected_execution = CanonicalExecutionResult(
        accepted=False,
        exchange_order_id=None,
        status="REJECTED",
        asset="BTCUSDT",
        direction="LONG",
        executed_quantity=None,
        executed_price=None,
        timestamp="2026-10-04T00:00:00+00:00",
        adapter="TOOBIT",
        error_code="TEST_PROVIDER_REJECTION",
        error_message="test execution result",
    )

    expected = ProviderExecutionConsumerHandoffResult(
        status=ConsumerHandoffStatus.PASS,
        reason="EXECUTION_CONSUMER_HANDOFF_COMPLETE",
        message="test consumer handoff",
        canonical_request=_request(),
        execution_result=expected_execution,
    )

    def fake_consumer_handoff(*args, **kwargs):
        calls.append(args[0].__class__.__name__)
        return expected

    monkeypatch.setattr(
        bridge,
        "handoff_binding_to_execution_consumer",
        fake_consumer_handoff,
    )

    result = bridge.execute_canonical_request(
        adapter=_Adapter(),
        request=_request(),
        provider_preflight_result=_Preflight(),
        management_authorized=False,
    )

    assert result is expected_execution
    assert calls == ["ProviderExecutionBindingResult"]

class _Response:
    status_code = 400

    def json(self):
        return {"code": -2010, "msg": "Order would trigger immediately."}

class _Session:
    def __init__(self):
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
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
    assert session.calls[0][0][0] == "https://api.toobit.com/api/v1/spot/order"
    assert "/api/v1/spot/orderTest" not in session.calls[0][0][0]
    assert result.accepted is False
    assert result.status == "REJECTED"
    assert result.http_status == 400
    assert result.submitted_to_matching_engine is True
    assert result.error_code == "-2010"
    assert result.exchange_order_id is None
