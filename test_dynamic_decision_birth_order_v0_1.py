from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import dynamic_decision_contract_boundary_v0_1 as dynamic_decision
import mcp01_main_integration_boundary_v0_1 as birth_boundary


class DynamicDecisionBirthOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signal = {
            "asset": "BTC",
            "signal_state": "ACTIVE",
            "direction": "LONG",
            "valid": True,
            "validation": "VALID",
        }
        self.score = {
            "asset": "BTC",
            "signal_state": "ACTIVE",
            "direction": "LONG",
            "score": 0.75,
        }

    def test_missing_id_returns_semantic_candidate_without_identity(self) -> None:
        result = dynamic_decision.build_dynamic_decision(
            "BTC/USDT", self.signal, self.score
        )
        self.assertEqual(result["status"], "SEMANTIC_READY")
        self.assertEqual(result["state"], "ACTIONABLE")
        self.assertEqual(result["direction"], "LONG")
        self.assertNotIn("decision_id", result)
        self.assertEqual(result["db_writes"], 0)
        self.assertFalse(result["execution"])

    def test_supplied_id_preserves_complete_decision_api(self) -> None:
        result = dynamic_decision.build_dynamic_decision(
            "BTC/USDT", self.signal, self.score,
            decision_id="CANONICAL-DECISION-1",
        )
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["decision_id"], "CANONICAL-DECISION-1")
        self.assertEqual(result["state"], "ACTIONABLE")

    def test_blank_explicit_id_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "decision_id must be non-empty"):
            dynamic_decision.build_dynamic_decision(
                "BTC/USDT", self.signal, self.score, decision_id=" "
            )

    def test_boolean_score_is_rejected_by_engine_contract(self) -> None:
        invalid_score = {**self.score, "score": True}
        with self.assertRaisesRegex(RuntimeError, "Boolean score is invalid"):
            dynamic_decision.build_dynamic_decision(
                "BTC/USDT", self.signal, invalid_score
            )

    def test_birth_persistence_promotes_candidate_and_preserves_semantics(self) -> None:
        market = SimpleNamespace(
            candles=[{"timestamp": 1791596700}],
            source="REAL_MARKET_SOURCE",
        )
        candidate = dynamic_decision.build_dynamic_decision(
            "BTC/USDT", self.signal, self.score
        )
        captured_births = []

        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "birth.sqlite3")
            with (
                patch.object(
                    birth_boundary,
                    "issue_canonical_decision_id",
                    return_value="CANONICAL-DECISION-2",
                ),
                patch.object(birth_boundary, "ensure_birth_schema"),
                patch.object(
                    birth_boundary,
                    "require_production_decision_birth",
                    side_effect=lambda events, expected_assets, conn: (
                        captured_births.extend(events.values())
                        or {asset: event["decision_id"] for asset, event in events.items()}
                    ),
                ),
            ):
                bound, count = birth_boundary.bind_authoritative_decision_birth(
                    db_path=db_path,
                    decision_snapshot={"BTC": candidate},
                    market_data_by_symbol={"BTC/USDT": market},
                )

        self.assertEqual(count, 1)
        self.assertEqual(bound["BTC"]["status"], "READY")
        self.assertEqual(bound["BTC"]["decision_id"], "CANONICAL-DECISION-2")
        self.assertEqual(bound["BTC"]["state"], "ACTIONABLE")
        self.assertEqual(bound["BTC"]["direction"], "LONG")
        self.assertEqual(bound["BTC"]["reason"], "VALID_ACTIVE_SIGNAL")
        self.assertEqual(len(captured_births), 1)
        self.assertEqual(captured_births[0]["decision"]["status"], "SEMANTIC_READY")
        self.assertNotIn("decision_id", captured_births[0]["decision"])

    def test_birth_refuses_to_issue_a_second_identity(self) -> None:
        market = SimpleNamespace(
            candles=[{"timestamp": 1791596700}],
            source="REAL_MARKET_SOURCE",
        )
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "birth.sqlite3")
            with patch.object(
                birth_boundary, "issue_canonical_decision_id"
            ) as issuer:
                with self.assertRaisesRegex(
                    RuntimeError, "MCP01_DECISION_BIRTH_ID_PREEXISTS"
                ):
                    birth_boundary.bind_authoritative_decision_birth(
                        db_path=db_path,
                        decision_snapshot={
                            "BTC": {
                                "decision_id": "EXISTING-ID",
                                "state": "ACTIONABLE",
                            }
                        },
                        market_data_by_symbol={"BTC/USDT": market},
                    )
                issuer.assert_not_called()

    def test_birth_persistence_failure_does_not_return_bound_decision(self) -> None:
        market = SimpleNamespace(
            candles=[{"timestamp": 1791596700}],
            source="REAL_MARKET_SOURCE",
        )
        candidate = dynamic_decision.build_dynamic_decision(
            "BTC/USDT", self.signal, self.score
        )
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "birth.sqlite3")
            with (
                patch.object(
                    birth_boundary,
                    "issue_canonical_decision_id",
                    return_value="CANONICAL-DECISION-3",
                ),
                patch.object(birth_boundary, "ensure_birth_schema"),
                patch.object(
                    birth_boundary,
                    "require_production_decision_birth",
                    side_effect=RuntimeError("PERSISTENCE_BLOCKED"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "PERSISTENCE_BLOCKED"):
                    birth_boundary.bind_authoritative_decision_birth(
                        db_path=db_path,
                        decision_snapshot={"BTC": candidate},
                        market_data_by_symbol={"BTC/USDT": market},
                    )


if __name__ == "__main__":
    unittest.main()
