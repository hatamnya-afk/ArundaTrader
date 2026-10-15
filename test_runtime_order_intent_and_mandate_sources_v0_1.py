"""Focused tests for fail-closed runtime OrderIntent and mandate source boundaries."""
import json
import os
import unittest
from unittest.mock import patch

from runtime_order_intent_producer_v0_1 import produce_runtime_order_intents
from management_mandate_record_source_v0_1 import load_authoritative_management_mandate


class Market:
    source = "REAL_PROVIDER"
    candles = ({"timestamp": 1792000000000},)


def inputs():
    decision = {"decision_id": "DBIRTH-1", "direction": "LONG", "regime": "TRENDING"}
    risk = {
        "risk_status": "APPROVED", "position_quantity": 0.01,
        "quantity_unit": "BASE_ASSET", "quantity_source": "RISK.position_quantity",
    }
    gate = {"trade_gate_state": "TRADE_READY"}
    opportunity = {
        "status": "ELIGIBLE", "price": 100.0, "timestamp": "2026-10-15T12:00:00+00:00",
        "confidence": 0.9,
    }
    return (
        {"BTC": decision}, {"BTC": risk}, {"BTC": gate}, {"BTC": opportunity},
        {"BTC/USDT": Market()},
    )


class RuntimeOrderIntentProducerTests(unittest.TestCase):
    def test_intent_identity_is_born_from_authoritative_decision_birth(self):
        decision, risk, gate, opportunities, market = inputs()
        intents = produce_runtime_order_intents(
            decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
            opportunity_by_asset=opportunities, market_data_by_symbol=market,
        )
        self.assertEqual(intents["BTC"]["intent_id"], "OI-DBIRTH-1")
        self.assertEqual(intents["BTC"]["decision_id"], "DBIRTH-1")
        self.assertEqual(intents["BTC"]["quantity"], risk["BTC"]["position_quantity"])
        self.assertEqual(intents["BTC"]["snapshot_id"], "REAL_PROVIDER|BTC/USDT|1h|1792000000000")

    def test_trade_not_ready_never_emits_intent(self):
        decision, risk, gate, opportunities, market = inputs()
        gate["BTC"]["trade_gate_state"] = "REJECTED"
        self.assertEqual(produce_runtime_order_intents(
            decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
            opportunity_by_asset=opportunities, market_data_by_symbol=market,
        ), {})

    def test_missing_decision_birth_identity_fails_closed(self):
        decision, risk, gate, opportunities, market = inputs()
        decision["BTC"].pop("decision_id")
        with self.assertRaisesRegex(ValueError, "ORDER_INTENT_DECISION_BIRTH_ID_MISSING"):
            produce_runtime_order_intents(
                decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
                opportunity_by_asset=opportunities, market_data_by_symbol=market,
            )


class ManagementMandateSourceTests(unittest.TestCase):
    def test_missing_external_record_is_not_replaced_by_a_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "AUTHORITATIVE_MANAGEMENT_MANDATE_SOURCE_MISSING"):
                load_authoritative_management_mandate()

    def test_malformed_external_record_fails_closed(self):
        with patch.dict(os.environ, {"ARUNDA_MANAGEMENT_MANDATE_JSON": "{bad"}):
            with self.assertRaisesRegex(ValueError, "AUTHORITATIVE_MANAGEMENT_MANDATE_JSON_INVALID"):
                load_authoritative_management_mandate()

    def test_deferred_management_record_is_not_treated_as_permission(self):
        from datetime import datetime, timedelta, timezone
        record = {
            "decision": "DEFERRED", "mandate_id": "UNIT-ONLY",
            "authorized_by": "unit-test", "authorization_source": "UNIT_TEST",
            "environment": "REAL_PRODUCTION",
            "issued_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "allowed_markets": ["SPOT", "FUTURES"], "provider": "TOOBIT",
            "capital_policy": "UNIT_TEST", "evidence_required_before": ["unit-test"],
            "evidence_required_after": ["unit-test"],
        }
        with patch.dict(os.environ, {"ARUNDA_MANAGEMENT_MANDATE_JSON": json.dumps(record)}):
            with self.assertRaisesRegex(ValueError, "NOT_AUTHORIZED"):
                load_authoritative_management_mandate()

    def test_denied_management_record_is_not_treated_as_permission(self):
        from datetime import datetime, timedelta, timezone
        record = {
            "decision": "DENIED", "mandate_id": "UNIT-ONLY",
            "authorized_by": "unit-test", "authorization_source": "UNIT_TEST",
            "environment": "REAL_PRODUCTION",
            "issued_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "allowed_markets": ["SPOT", "FUTURES"], "provider": "TOOBIT",
            "capital_policy": "UNIT_TEST", "evidence_required_before": ["unit-test"],
            "evidence_required_after": ["unit-test"],
        }
        with patch.dict(os.environ, {"ARUNDA_MANAGEMENT_MANDATE_JSON": json.dumps(record)}):
            with self.assertRaisesRegex(ValueError, "NOT_AUTHORIZED"):
                load_authoritative_management_mandate()

    def test_record_requires_explicit_time_bounded_authorization(self):
        record = {
            "decision": "AUTHORIZED", "mandate_id": "UNIT-ONLY",
            "authorized_by": "unit-test", "authorization_source": "UNIT_TEST",
            "environment": "REAL_PRODUCTION", "allowed_markets": ["SPOT", "FUTURES"],
            "provider": "TOOBIT", "capital_policy": "UNIT_TEST",
            "evidence_required_before": ["unit-test"], "evidence_required_after": ["unit-test"],
        }
        with patch.dict(os.environ, {"ARUNDA_MANAGEMENT_MANDATE_JSON": json.dumps(record)}):
            with self.assertRaisesRegex(ValueError, "MANAGEMENT_ISSUED_AT_INVALID"):
                load_authoritative_management_mandate()


if __name__ == "__main__":
    unittest.main()
