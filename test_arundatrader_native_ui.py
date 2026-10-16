"""Focused tests for the native ArundaTrader CP69 observation consumer/UI."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from arundatrader_observation_consumer import CanonicalRuntimeObservation
from arundatrader_live_ui import asset_rows, observation_age_seconds, read_latest_observation


def payload(**overrides):
    item = {
        "schema": "arunda.runtime_observation",
        "schema_version": "1.0",
        "source_system": "ArundaTrader",
        "environment_id": "arundatrader",
        "adapter_id": "arundatrader_adapter",
        "observation_id": "obs:test",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "knowledge_cutoff": None,
        "provenance": {
            "source": "arunda_pipeline",
            "runtime_snapshot_id": "RS-test",
            "launch_boundary": "2026-08-31T00:00:00+00:00",
            "db_write_boundary": None,
        },
        "state": {
            "universe_assets": ["BTC/USDT"],
            "market_data_results": {"BTC/USDT": {"status": "READY"}},
            "opportunity_by_asset": {"BTC": {"status": "FOUND"}},
            "dynamic_signals": {"BTC": {"direction": "NONE"}},
            "validation_results": {"BTC": {"valid": True}},
            "fusion_snapshot": {"BTC": {"status": "READY"}},
            "score_snapshot": {"BTC": {"source_score": 0}},
            "decision_snapshot": {"BTC": {"decision": "HOLD"}},
            "risk_snapshot": {"BTC": {"status": "PASS"}},
            "trade_gate_snapshot": {"BTC": {"trade_gate_state": "HOLD"}},
            "trade_ready_assets": [],
            "failure_attribution": {"trade_ready_count": 0, "predicate_failures": {}, "reason_counts": {}},
        },
        "execution_state": {"EXECUTION": "OFF", "REAL_ORDER": False, "REAL_TRADE": False, "DB_WRITES": 0},
    }
    item.update(overrides)
    return item


class CanonicalObservationTests(unittest.TestCase):
    def test_accepts_canonical_read_only_observation(self):
        observation = CanonicalRuntimeObservation.from_dict(payload())
        self.assertEqual(observation.observation_id, "obs:test")
        self.assertEqual(observation.execution_state["EXECUTION"], "OFF")

    def test_rejects_wrong_identity(self):
        item = payload()
        item["source_system"] = "AroondaAI"
        with self.assertRaisesRegex(ValueError, "source system mismatch"):
            CanonicalRuntimeObservation.from_dict(item)

    def test_rejects_execution_enabled(self):
        item = payload()
        item["execution_state"]["REAL_ORDER"] = True
        with self.assertRaisesRegex(ValueError, "REAL_ORDER"):
            CanonicalRuntimeObservation.from_dict(item)

    def test_rejects_unattributed_database_writes(self):
        item = payload()
        item["execution_state"]["DB_WRITES"] = 1
        with self.assertRaisesRegex(ValueError, "unauthorized production DB write boundary"):
            CanonicalRuntimeObservation.from_dict(item)

    def test_reads_latest_single_record_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current.jsonl"
            first = payload()
            second = payload()
            second["observation_id"] = "obs:latest"
            path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
            self.assertEqual(read_latest_observation(path).observation_id, "obs:latest")

    def test_malformed_latest_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current.jsonl"
            path.write_text(json.dumps(payload()) + "\n{broken-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "latest CP69 record is invalid JSON"):
                read_latest_observation(path)

    def test_stale_observation_age_is_measurable(self):
        observation = CanonicalRuntimeObservation.from_dict(payload())
        age = observation_age_seconds(observation, now=datetime.now(timezone.utc))
        self.assertGreaterEqual(age, 0)
        self.assertLess(age, 5)

    def test_asset_rows_only_project_source_maps(self):
        item = payload()
        item["state"]["market_data_results"] = [{"symbol": "BTC/USDT", "status": "READY"}]
        observation = CanonicalRuntimeObservation.from_dict(item)
        rows = asset_rows(observation)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "BTC")
        self.assertIn("READY", rows[0])
        self.assertIn("HOLD", rows[0])


if __name__ == "__main__":
    unittest.main()
