from __future__ import annotations

import json

from exchange_execution_contract import (
    CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION,
    QUANTITY_UNIT_BASE_ASSET,
)
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter
from toobit_ambiguous_submission_recovery_v0_1 import (
    LOOKUP_UNAVAILABLE,
    recover_ambiguous_toobit_submission,
)


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price="60000", intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )


def adapter_for(transport):
    return ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )


def test_spot_exact_order_lookup_captures_observation_using_get_only(tmp_path):
    calls = []
    row = {
        "symbol": "BTCUSDT", "clientOrderId": "INT-1", "orderId": "SPOT-1",
        "status": "FILLED", "executedQty": "0.01", "price": "60000",
    }

    def transport(**kwargs):
        calls.append(kwargs)
        return row

    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(transport), request=request(), venue="SPOT",
        symbol="BTCUSDT", trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z", stream_path=tmp_path / "outcomes.jsonl",
    )

    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == "/api/v1/spot/order"
    assert calls[0]["params"]["origClientOrderId"] == "INT-1"
    assert result["reconciliation_state"] == "FOUND"
    assert result["capture_state"] == "PERSISTED"
    assert result["safe_to_retry"] is False
    persisted = json.loads((tmp_path / "outcomes.jsonl").read_text(encoding="utf-8"))
    assert persisted["exchange_order_id"] == "SPOT-1"
    assert persisted["executed_quantity"] == "0.01"
    assert persisted["executed_price"] is None
    assert persisted["fill_inferred"] is False


def test_futures_exact_order_lookup_uses_v2_and_category(tmp_path):
    calls = []
    row = {
        "symbol": "BTC-SWAP-USDT", "clientOrderId": "INT-1", "orderId": "FUT-1",
        "status": "NEW", "executedQty": "0",
    }

    def transport(**kwargs):
        calls.append(kwargs)
        return {"code": 200, "data": row}

    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(transport), request=request(), venue="FUTURES",
        symbol="BTC-SWAP-USDT", category="USDT", trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z", stream_path=tmp_path / "outcomes.jsonl",
    )

    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == "/api/v2/futures/order"
    assert calls[0]["params"]["origClientOrderId"] == "INT-1"
    assert calls[0]["params"]["category"] == "USDT"
    assert result["reconciliation_state"] == "FOUND"
    assert result["capture_state"] == "PERSISTED"
    assert result["safe_to_retry"] is False


def test_lookup_failure_is_not_treated_as_not_found_or_safe_to_retry(tmp_path):
    calls = []

    def transport(**kwargs):
        calls.append(kwargs)
        return {"code": -2013, "msg": "order does not exist"}

    path = tmp_path / "outcomes.jsonl"
    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(transport), request=request(), venue="SPOT",
        symbol="BTCUSDT", trade_event_id="TE-1", stream_path=path,
    )

    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert result["reconciliation_state"] == LOOKUP_UNAVAILABLE
    assert result["capture_state"] == "NOT_CAPTURED"
    assert result["safe_to_retry"] is False
    assert not path.exists()


def test_client_id_or_symbol_mismatch_fails_closed_without_persisting(tmp_path):
    calls = []
    path = tmp_path / "outcomes.jsonl"

    def transport(**kwargs):
        calls.append(kwargs)
        return {
            "symbol": "ETHUSDT", "clientOrderId": "INT-1", "orderId": "WRONG",
            "status": "FILLED", "executedQty": "1",
        }

    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(transport), request=request(), venue="SPOT",
        symbol="BTCUSDT", trade_event_id="TE-1", stream_path=path,
    )

    assert len(calls) == 1
    assert result["reconciliation_state"] == "INVALID_OBSERVATION"
    assert result["capture_state"] == "NOT_CAPTURED"
    assert result["reason"] == "PROVIDER_LOOKUP_SYMBOL_MISMATCH"
    assert result["safe_to_retry"] is False
    assert not path.exists()


def test_invalid_futures_category_is_blocked_before_transport(tmp_path):
    calls = []
    path = tmp_path / "outcomes.jsonl"
    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(lambda **kwargs: calls.append(kwargs) or {}),
        request=request(), venue="FUTURES", symbol="BTC-SWAP-USDT",
        category="UNKNOWN", trade_event_id="TE-1", stream_path=path,
    )
    assert result["reconciliation_state"] == "INVALID_OBSERVATION"
    assert result["reason"] == "FUTURES_CATEGORY_INVALID"
    assert result["safe_to_retry"] is False
    assert calls == []
    assert not path.exists()



def test_invalid_observation_timestamp_fails_before_provider_lookup(tmp_path):
    calls = []
    path = tmp_path / "outcomes.jsonl"
    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(lambda **kwargs: calls.append(kwargs) or {}),
        request=request(), venue="SPOT", symbol="BTCUSDT",
        trade_event_id="TE-1", observed_at="2026-10-15T08:01:00",
        stream_path=path,
    )
    assert result["reconciliation_state"] == "INVALID_OBSERVATION"
    assert result["reason"] == "LOCAL_OBSERVATION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"
    assert result["safe_to_retry"] is False
    assert calls == []
    assert not path.exists()


def test_malformed_provider_lookup_row_fails_closed_without_persistence(tmp_path):
    calls = []
    path = tmp_path / "outcomes.jsonl"
    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(lambda **kwargs: calls.append(kwargs) or {"status": "FILLED"}),
        request=request(), venue="SPOT", symbol="BTCUSDT",
        trade_event_id="TE-1", observed_at="2026-10-15T08:01:00Z",
        stream_path=path,
    )
    assert len(calls) == 1
    assert result["reconciliation_state"] == "INVALID_OBSERVATION"
    assert result["reason"] == "PROVIDER_LOOKUP_CLIENT_ORDER_ID_MISMATCH"
    assert result["capture_state"] == "NOT_CAPTURED"
    assert result["safe_to_retry"] is False
    assert not path.exists()


def test_default_observation_timestamp_is_local_timezone_aware_time(tmp_path):
    import datetime

    row = {
        "symbol": "BTCUSDT", "clientOrderId": "INT-1", "orderId": "SPOT-2",
        "status": "NEW", "executedQty": "0",
    }
    result = recover_ambiguous_toobit_submission(
        adapter=adapter_for(lambda **kwargs: row),
        request=request(), venue="SPOT", symbol="BTCUSDT",
        trade_event_id="TE-1", stream_path=tmp_path / "outcomes.jsonl",
    )
    assert result["capture_state"] == "PERSISTED"
    observed_at = result["record"]["observed_at"]
    parsed = datetime.datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None and parsed.utcoffset() is not None
    assert result["record"]["provider_timestamp_known"] is True
