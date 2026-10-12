from pathlib import Path

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    CLAIMED,
    SQLiteIntentClaimStore,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from exchange_execution_order_reconciliation_contract_v0_1 import (
    evaluate_order_reconciliation,
)
from mcp01_execution_attempt_evidence_v0_1 import (
    build_execution_attempt_events,
    persist_execution_attempt_events,
)
from mcp01_trade_event_identity_v0_1 import issue_trade_event_id
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="INTENT-CYCLE-001",
        snapshot_id="SNAPSHOT-CYCLE-001",
        timestamp="2026-10-12T00:00:00+00:00",
        decision_id="DECISION-CYCLE-001",
    )


def _result():
    return CanonicalExecutionResult(
        accepted=False,
        exchange_order_id=None,
        status="SUBMISSION_OUTCOME_UNKNOWN",
        asset="BTC",
        direction="LONG",
        executed_quantity=None,
        executed_price=None,
        timestamp="2026-10-12T00:00:01+00:00",
        adapter="TOOBIT",
        error_code="TRANSPORT_UNKNOWN",
        error_message="offline integration fixture",
        trade_event_id=issue_trade_event_id(),
    )


def test_claim_evidence_and_found_provider_order_share_one_identity(tmp_path: Path):
    request = _request()
    result = _result()
    client_id = "AR-CYCLE-CLIENT-001"
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    claimed = store.claim(
        provider_namespace="TOOBIT-FUTURES",
        intent_id=request.intent_id,
        client_order_id=client_id,
    )
    assert claimed.outcome == "CLAIMED"
    assert claimed.status == CLAIMED

    events = build_execution_attempt_events(
        request=request, result=result, client_order_id=client_id
    )
    stream = tmp_path / "events.jsonl"
    persisted = persist_execution_attempt_events(events, stream_path=stream)
    assert persisted["persistence_state"] == "PERSISTED"
    assert len(stream.read_text(encoding="utf-8").splitlines()) == 2
    assert all(e.intent_id == request.intent_id for e in events)
    assert all(e.client_order_id == client_id for e in events)
    assert all(e.trade_event_id == result.trade_event_id for e in events)

    def transport(*, method, path, params, headers, base_url):
        assert method == "GET"
        assert path == "/api/v2/futures/order"
        assert params["origClientOrderId"] == client_id
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "orderId": "EX-CYCLE-001",
                "clientOrderId": client_id,
                "status": "NEW",
            },
        }

    lookup = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    ).lookup_futures_order_by_client_order_id(client_id)
    decision = evaluate_order_reconciliation(
        expected_client_order_id=client_id,
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=lookup,
    )
    assert decision.state == "MATCHED"
    assert decision.exchange_order_id == "EX-CYCLE-001"
    assert decision.may_submit is False
    assert decision.retry_allowed is False


def test_not_found_after_prior_attempt_keeps_claim_and_requires_reconciliation(tmp_path: Path):
    request = _request()
    client_id = "AR-CYCLE-CLIENT-002"
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(
        provider_namespace="TOOBIT-FUTURES",
        intent_id=request.intent_id,
        client_order_id=client_id,
    )

    def transport(**kwargs):
        return {"code": -2013, "msg": "Order does not exist."}

    lookup = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    ).lookup_futures_order_by_client_order_id(client_id)
    decision = evaluate_order_reconciliation(
        expected_client_order_id=client_id,
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=lookup,
    )
    reopened = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    claim = reopened.get(
        provider_namespace="TOOBIT-FUTURES",
        intent_id=request.intent_id,
    )
    duplicate_claim = reopened.claim(
        provider_namespace="TOOBIT-FUTURES",
        intent_id=request.intent_id,
        client_order_id=client_id,
    )

    assert duplicate_claim.outcome == "ALREADY_CLAIMED"
    assert lookup.state == "NOT_FOUND"
    assert decision.state == "RECONCILIATION_REQUIRED"
    assert decision.may_submit is False
    assert decision.retry_allowed is False
    assert claim is not None
    assert claim.client_order_id == client_id
    assert claim.status == CLAIMED
