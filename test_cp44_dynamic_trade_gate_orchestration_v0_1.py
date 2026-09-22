"""Direct CP44 Trade Gate orchestration contract tests v0.1."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

import trade_gate_engine


ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "arunda_pipeline.py"


class TestCP44DynamicTradeGateOrchestration(unittest.TestCase):
    def test_authoritative_gate_returns_trade_ready_for_valid_chain(self):
        opportunity = {
            "asset": "BTC",
            "status": "ELIGIBLE",
            "direction": "LONG",
            "score": 0.8,
            "confidence": 0.9,
            "market_data_points": 50,
            "snapshot_age": 0.0,
        }
        decision = {
            "asset": "BTC",
            "state": "TRADE",
            "direction": "LONG",
        }
        risk = {
            "asset": "BTC",
            "risk_state": "APPROVED",
            "risk_decision": "APPROVED",
        }

        status, reasons = trade_gate_engine.evaluate(
            opportunity,
            decision,
            risk,
        )

        self.assertEqual(status, "TRADE_READY")
        self.assertEqual(reasons, ["all gates passed"])

    def test_neutral_direction_cannot_become_trade_ready(self):
        opportunity = {
            "asset": "BTC",
            "status": "ELIGIBLE",
            "direction": "NONE",
            "score": 0.8,
            "confidence": 0.9,
            "market_data_points": 50,
            "snapshot_age": 0.0,
        }
        decision = {
            "asset": "BTC",
            "state": "NONE",
            "direction": "NONE",
        }
        risk = {
            "asset": "BTC",
            "risk_state": "APPROVED",
            "risk_decision": "APPROVED",
        }

        status, reasons = trade_gate_engine.evaluate(
            opportunity,
            decision,
            risk,
        )

        self.assertNotEqual(status, "TRADE_READY")
        self.assertTrue(reasons)

    def test_pipeline_contains_explicit_gate_wiring(self):
        source = PIPELINE.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)

        main = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "main"
        )

        names = [
            node.id
            for node in ast.walk(main)
            if isinstance(node, ast.Name)
        ]

        self.assertIn("trade_gate_snapshot", names)
        self.assertIn("trade_ready_assets", names)
        self.assertIn("trade_gate_engine", names)
        self.assertIn("risk_snapshot", names)

        self.assertIn(
            "trade_gate_status, gate_reasons = trade_gate_engine.evaluate(",
            source,
        )
        self.assertIn(
            '"TRADE_GATE_v0.1"',
            source,
        )
        self.assertNotIn(
            'trade_ready_assets = []',
            source,
        )


if __name__ == "__main__":
    unittest.main()
