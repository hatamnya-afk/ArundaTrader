"""Tests for the fail-closed Smart Risk orchestration adapter."""
import unittest

from dynamic_smart_risk_pipeline_adapter_v0_1 import evaluate_smart_risk_for_asset


class SmartRiskPipelineAdapterTests(unittest.TestCase):
    def test_missing_current_cycle_observations_block_without_quantity(self):
        result = evaluate_smart_risk_for_asset(
            asset="BTC",
            direction="LONG",
            entry_price=100.0,
        )
        self.assertEqual(result["risk_state"], "BLOCKED")
        self.assertEqual(result["block_reason"], "SMART_RISK_EVIDENCE_MISSING")
        self.assertEqual(
            result["missing_observations"],
            ["real_capital", "portfolio", "stop_policy", "risk_policy"],
        )
        self.assertIsNone(result["position_quantity"])
        self.assertIsNone(result["quantity_source"])

    def test_partial_observations_do_not_trigger_fallback_sizing(self):
        result = evaluate_smart_risk_for_asset(
            asset="BTC",
            direction="LONG",
            entry_price=100.0,
            portfolio_observation={},
        )
        self.assertEqual(result["risk_state"], "BLOCKED")
        self.assertIn("real_capital", result["missing_observations"])
        self.assertIn("stop_policy", result["missing_observations"])
        self.assertIn("risk_policy", result["missing_observations"])
        self.assertIsNone(result["position_quantity"])


    def test_mismatched_current_cycle_timestamps_block(self):
        from real_capital_observation_contract_v0_1 import RealCapitalObservation

        capital = RealCapitalObservation(
            capital_state="REAL_CAPITAL",
            portfolio_capital=1000.0,
            usable_capital=800.0,
            allocated_risk=0.0,
            concurrent_positions=0,
            source="READ_ONLY_ACCOUNT_SOURCE",
            observed_at="2026-10-14T09:00:00Z",
            provenance={"source": "read-only", "account_scope": "spot"},
            validation="VALID",
        )
        result = evaluate_smart_risk_for_asset(
            asset="BTC",
            direction="LONG",
            entry_price=100.0,
            capital_observation=capital,
            portfolio_observation={"observed_at": "2026-10-14T09:00:00Z"},
            stop_policy_observation={"observed_at": "2026-10-14T09:01:00Z"},
            risk_policy_observation={},
        )
        self.assertEqual(result["risk_state"], "BLOCKED")
        self.assertEqual(
            result["block_reason"], "SMART_RISK_OBSERVATION_CYCLE_MISMATCH"
        )
        self.assertIsNone(result["position_quantity"])
        self.assertIsNone(result["quantity_source"])

    def test_missing_cycle_timestamp_blocks(self):
        from real_capital_observation_contract_v0_1 import RealCapitalObservation

        capital = RealCapitalObservation(
            capital_state="REAL_CAPITAL",
            portfolio_capital=1000.0,
            usable_capital=800.0,
            allocated_risk=0.0,
            concurrent_positions=0,
            source="READ_ONLY_ACCOUNT_SOURCE",
            observed_at="2026-10-14T09:00:00Z",
            provenance={"source": "read-only", "account_scope": "spot"},
            validation="VALID",
        )
        result = evaluate_smart_risk_for_asset(
            asset="BTC",
            direction="LONG",
            entry_price=100.0,
            capital_observation=capital,
            portfolio_observation={},
            stop_policy_observation={},
            risk_policy_observation={},
        )
        self.assertEqual(result["risk_state"], "BLOCKED")
        self.assertEqual(result["block_reason"], "SMART_RISK_CYCLE_TIMESTAMP_MISSING")
        self.assertIsNone(result["position_quantity"])


if __name__ == "__main__":
    unittest.main()
