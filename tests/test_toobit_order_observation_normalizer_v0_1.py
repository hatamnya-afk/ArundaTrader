from __future__ import annotations

import json

import pytest

from exchange_execution_contract import (
    CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION,
    QUANTITY_UNIT_BASE_ASSET,
)
from toobit_order_observation_normalizer_v0_1 import (
    capture_toobit_read_only_order_observation,
)


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price=None, intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )


def test_lookup_persists_real_provider_fields_without_inventing_fill_price(tmp_path):
    result = capture_toobit_read_only_order_observation(
        request=request(),
        provider_order={
            "symbol": "BTCUSDT", "clientOrderId": "INT-1",
            "orderId": "EX-1", "status": "FILLED",
            "executedQty": "0.01", "price": "60000",
        },
        trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00+00:00",
        stream_path=tmp_path / "outcomes.jsonl",
    )
    row = json.loads((tmp_path / "outcomes.jsonl").read_text(encoding="utf-8"))
    assert result["state"] == "PERSISTED"
    assert row["source_kind"] == "READ_ONLY_LOOKUP"
    assert row["provider_symbol"] == "BTCUSDT"
    assert row["outcome_state"] == "OUTCOME_INCOMPLETE"
    assert row["executed_price"] is None
    assert row["fill_inferred"] is False


def test_explicit_average_execution_price_can_reconcile_fill(tmp_path):
    result = capture_toobit_read_only_order_observation(
        request=request(),
        provider_order={
            "symbol": "BTCUSDT", "clientOrderId": "INT-1",
            "orderId": "EX-1", "status": "FILLED",
            "executedQty": "0.01", "avgPrice": "60000",
        },
        trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z",
        stream_path=tmp_path / "outcomes.jsonl",
    )
    assert result["record"]["outcome_state"] == "FILLED"
    assert result["record"]["executed_price"] == "60000"


def test_client_order_identity_mismatch_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="TOOBIT_CLIENT_ORDER_ID_MISMATCH"):
        capture_toobit_read_only_order_observation(
            request=request(),
            provider_order={
                "symbol": "BTCUSDT", "clientOrderId": "OTHER",
                "orderId": "EX-1", "status": "FILLED",
                "executedQty": "0.01", "avgPrice": "60000",
            },
            trade_event_id="TE-1",
            observed_at="2026-10-15T08:01:00Z",
            stream_path=tmp_path / "outcomes.jsonl",
        )
    assert not (tmp_path / "outcomes.jsonl").exists()


def test_unknown_status_stays_unknown_and_terminal_without_quantity_unreconciled(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    unknown = capture_toobit_read_only_order_observation(
        request=request(),
        provider_order={"symbol":"BTCUSDT","clientOrderId":"INT-1","orderId":"EX-1","status":"MYSTERY"},
        trade_event_id="TE-1", observed_at="2026-10-15T08:01:00Z", stream_path=path,
    )
    assert unknown["record"]["outcome_state"] == "UNKNOWN"
    terminal = capture_toobit_read_only_order_observation(
        request=request(),
        provider_order={"symbol":"BTCUSDT","clientOrderId":"INT-1","orderId":"EX-1","status":"CANCELED"},
        trade_event_id="TE-1", observed_at="2026-10-15T08:02:00Z", stream_path=path,
    )
    assert terminal["record"]["outcome_state"] == "TERMINAL_UNRECONCILED"
