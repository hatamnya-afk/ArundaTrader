"""Offline end-to-end proof: canonical request -> mandate -> adapter -> durable outcome.

All provider responses are deterministic fixtures; no network call or real order occurs.
"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    PROVIDER_ACCEPTED,
    SQLiteIntentClaimStore,
)
from exchange_execution_contract import CanonicalOrderRequest
from execution_attempt_runtime_producers_v0_1 import produce_final_execution_attempt_context
from execution_instrument_contract_v0_1 import ExecutionInstrumentSpecification
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


class FinalExecutionAttemptOfflineE2ETests(unittest.TestCase):
    def test_provider_acceptance_is_persisted_after_exactly_one_mock_post(self):
        now = datetime.now(timezone.utc)
        request = CanonicalOrderRequest(
            asset="BTC", direction="LONG", order_type="MARKET",
            quantity=0.01, quantity_unit="BASE_ASSET",
            quantity_source="RISK.position_quantity",
            entry_price=100.0, reference_price=100.0,
            intent_id="UNIT-E2E-INTENT", snapshot_id="UNIT-E2E-SNAPSHOT",
            timestamp=now.isoformat(), decision_id="UNIT-E2E-DECISION-BIRTH",
        )
        instrument = ExecutionInstrumentSpecification(
            asset="BTC", venue="SPOT", settlement_asset="USDT",
            instrument_type="SPOT", selection_source="UNIT_TEST_FIXTURE",
            policy_version="test-only",
        )
        readiness = {
            "readiness_state": "PRE_EXECUTION_READY",
            "readiness_validation": "VALID",
            "asset": "BTC", "direction": "LONG",
            "entry_price": 100.0, "stop_price": 95.0,
            "stop_distance": 5.0, "quantity": 0.01, "exposure": 1.0,
            "risk_state": "APPROVED", "trade_gate_state": "APPROVED",
            "policy_version": "unit-test-policy", "provenance": "REAL_MARKET",
            "observed_at": now.isoformat(), "provider_binding": "DEFERRED",
        }
        mandate = {
            "decision": "AUTHORIZED", "mandate_id": "UNIT-E2E-MANDATE",
            "authorized_by": "unit-test",
            "authorization_source": "MANAGEMENT_PHASE_ENTRY_DECISION",
            "environment": "REAL_PRODUCTION",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=5)).isoformat(),
            "allowed_markets": ["SPOT", "FUTURES"], "provider": "TOOBIT",
            "capital_policy": "PROGRESSIVE_AFTER_REAL_OUTCOME_REVIEW",
            "evidence_required_before": ["technical-gate"],
            "evidence_required_after": ["provider-outcome"],
        }
        context = produce_final_execution_attempt_context(
            readiness=readiness, management_observation=mandate,
            request=request, venue="SPOT", execution_instrument=instrument,
        )

        provider_calls = []
        def mock_transport(*, method, path, params, headers, base_url):
            if method == "GET" and path == "/api/v1/exchangeInfo":
                return {"symbols": [{
                    "symbol": "BTCUSDT", "status": "TRADING",
                    "baseAsset": "BTC", "quoteAsset": "USDT",
                    "filters": [{"filterType": "LOT_SIZE", "minQty": "0.00001",
                                 "maxQty": "100000", "stepSize": "0.00001"}],
                }], "contracts": []}
            if method == "POST" and path == "/api/v1/spot/order":
                provider_calls.append((method, path, dict(params)))
                return {
                    "symbol": "BTCUSDT", "orderId": "fixture-order-1",
                    "clientOrderId": params["newClientOrderId"], "status": "NEW",
                    "executedQty": "0", "avgPrice": "0",
                    "transactTime": str(int(now.timestamp() * 1000)),
                }
            raise AssertionError("Unexpected mock transport route")

        adapter = ToobitExchangeAdapter(
            transport=mock_transport, api_key="fixture-key",
            secret_key="fixture-secret", enable_order_submission=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteIntentClaimStore(Path(directory) / "claims.sqlite3")
            result = run_final_execution_attempt_contract(
                execution_ready_package=context["execution_ready_package"],
                request=request,
                authorization_observation=context["authorization_observation"],
                adapter=adapter, venue="SPOT",
                execution_instrument=instrument, claim_store=store,
            )
            claim = store.get(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id=request.intent_id,
            )

        self.assertTrue(result.accepted, result.error_code)
        self.assertEqual(result.exchange_order_id, "fixture-order-1")
        self.assertTrue(result.trade_event_id)
        self.assertEqual(len(provider_calls), 1)
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, PROVIDER_ACCEPTED)
        self.assertEqual(claim.exchange_order_id, "fixture-order-1")
        self.assertEqual(claim.decision_id, request.decision_id)
        self.assertEqual(claim.trade_event_id, result.trade_event_id)
        self.assertTrue(claim.evidence_event_id)


if __name__ == "__main__":
    unittest.main()
