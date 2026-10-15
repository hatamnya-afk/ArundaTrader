from __future__ import annotations

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import (
    CanonicalExecutionResult, CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION, QUANTITY_UNIT_BASE_ASSET,
)
import exchange_execution_order_attempt_boundary_v0_1 as boundary


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price="60000", intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )


class FakeAdapter:
    adapter_name = "FAKE"

    def __init__(self, result=None, fail=False):
        self.result = result
        self.fail = fail

    def capabilities(self):
        return ExchangeAdapterCapabilities(True, True, True, True, True, True, False)

    def prepare_order(self, request, *, venue, execution_instrument):
        return AdapterOrderPreparation(True, "READY", "FAKE", venue, {"symbol": "BTCUSDT"})

    def submit_prepared_order(self, preparation, *, canonical_request):
        if self.fail:
            raise TimeoutError("ambiguous")
        return self.result

    def submit_order(self, request):
        raise AssertionError("direct submission bypass must not be used")

    def cancel_order(self, *, asset, exchange_order_id):
        raise AssertionError("cancel must not be used")


def prepare_gates(monkeypatch):
    monkeypatch.setattr(boundary, "evaluate_execution_attempt_readiness", lambda **kwargs: {
        "readiness_state": "READY", "readiness_validation": "VALID",
        "asset": "BTC", "direction": "LONG", "quantity": "0.01",
        "entry_price": None, "notional": 600, "provider_binding": "DEFERRED",
        "execution_authorized": False,
    })
    monkeypatch.setattr(boundary, "evaluate_execution_authorization", lambda *args: {
        "authorization_state": "AUTHORIZED",
    })
    monkeypatch.setattr(boundary, "prepare_order_for_adapter", lambda **kwargs:
        AdapterOrderPreparation(True, "READY", "FAKE", "SPOT", {"symbol": "BTCUSDT"}))


def result(trade_event_id="PROVIDER-FORGED"):
    return CanonicalExecutionResult(
        accepted=True, exchange_order_id="EX-1", status="NEW",
        asset="BTC", direction="LONG", executed_quantity=None,
        executed_price=None, timestamp="2026-10-15T08:01:00Z",
        adapter="FAKE", error_code=None, error_message=None,
        trade_event_id=trade_event_id,
    )


def call(adapter):
    return boundary.attempt_prepared_order(
        request=request(), readiness_observation={},
        authorization_observation={"mandate_id": "test"},
        adapter=adapter, venue="SPOT", execution_instrument=None,
        execution_ready_package={"package_state": "EXECUTION_READY_PACKAGE"},
    )


def test_attempt_boundary_overwrites_provider_attempt_identity(monkeypatch):
    prepare_gates(monkeypatch)
    observed = call(FakeAdapter(result=result()))
    assert observed.trade_event_id.startswith("TE-")
    assert observed.trade_event_id != "PROVIDER-FORGED"
    assert len(observed.trade_event_id) == len("TE-") + 32
    assert observed.trade_event_id[3:].isalnum()


def test_ambiguous_adapter_exception_retains_boundary_attempt_identity(monkeypatch):
    prepare_gates(monkeypatch)
    observed = call(FakeAdapter(fail=True))
    assert observed.status == "FAIL_CLOSED"
    assert observed.error_code == "ADAPTER_SUBMIT_PREPARED_FAILED"
    assert observed.trade_event_id.startswith("TE-")
