"""Direct CP44 tests for the neutral Predictive Evidence boundary.

These tests are pure contract tests. They do not execute Runtime, access the
production database, call an exchange, or create order intents.
"""

from __future__ import annotations

import unittest

from cp44_live_predictive_evidence_mapping_v0_1 import (
    LivePredictiveEvidenceMapping,
    NoPredictiveEvidence,
    build_live_predictive_evidence_mapping,
)


def _observation(
    direction: str,
    *,
    asset: str = "BTC/USDT",
    provenance: object = "unit-test",
    signal_state: str | None = None,
) -> dict[str, object]:
    observation: dict[str, object] = {
        "asset": asset,
        "direction": direction,
        "opportunity_score": 42.0,
        "momentum_1h": 1.0,
        "momentum_24h": 2.0,
        "rsi14": 55.0,
        "structure_direction": "BULLISH",
        "structure_strength": "STRONG",
        "structure_confidence": "EXPLICIT",
        "source": "CP44_TEST",
        "observed_at": "2026-09-22T00:00:00+00:00",
        "provenance": provenance,
    }
    if signal_state is not None:
        observation["signal_state"] = signal_state
    return observation


class CP44NeutralPredictiveEvidenceBoundaryTests(unittest.TestCase):

    def test_long_creates_directional_mapping(self) -> None:
        result = build_live_predictive_evidence_mapping(
            observation=_observation("LONG")
        )
        self.assertIsInstance(result, LivePredictiveEvidenceMapping)
        self.assertEqual(result.direction, "LONG")
        self.assertEqual(result.asset, "BTC/USDT")
        self.assertEqual(result.provenance, "unit-test")

    def test_short_creates_directional_mapping(self) -> None:
        result = build_live_predictive_evidence_mapping(
            observation=_observation("SHORT")
        )
        self.assertIsInstance(result, LivePredictiveEvidenceMapping)
        self.assertEqual(result.direction, "SHORT")
        self.assertEqual(result.asset, "BTC/USDT")
        self.assertEqual(result.provenance, "unit-test")

    def test_none_creates_explicit_no_predictive_evidence(self) -> None:
        result = build_live_predictive_evidence_mapping(
            observation=_observation("NONE")
        )
        self.assertIsInstance(result, NoPredictiveEvidence)
        self.assertNotIsInstance(result, LivePredictiveEvidenceMapping)
        self.assertEqual(result.direction, "NONE")
        self.assertEqual(result.status, "NO_PREDICTIVE_EVIDENCE")
        self.assertIsNone(result.predictive_evidence)
        self.assertEqual(result.asset, "BTC/USDT")
        self.assertEqual(result.provenance, "unit-test")

    def test_neutral_signal_state_preserves_no_evidence_semantics(self) -> None:
        result = build_live_predictive_evidence_mapping(
            observation=_observation(
                "NONE",
                signal_state="NEUTRAL",
            )
        )
        self.assertIsInstance(result, NoPredictiveEvidence)
        self.assertEqual(result.direction, "NONE")
        self.assertEqual(result.status, "NO_PREDICTIVE_EVIDENCE")
        self.assertEqual(result.asset, "BTC/USDT")

    def test_invalid_direction_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "^INVALID_DIRECTION$"):
            build_live_predictive_evidence_mapping(
                observation=_observation("BUY")
            )

    def test_forbidden_outcome_information_remains_rejected(self) -> None:
        observation = _observation("LONG")
        observation["outcome"] = "BUY"
        with self.assertRaisesRegex(
            ValueError,
            r"^FORBIDDEN_LIVE_INFORMATION:outcome$",
        ):
            build_live_predictive_evidence_mapping(
                observation=observation
            )

    def test_cardinality_is_preserved_for_directional_and_neutral_states(
        self,
    ) -> None:
        observations = [
            _observation(
                "LONG" if index % 2 == 0 else "NONE",
                asset=f"ASSET{index}/USDT",
                provenance=f"obs-{index}",
            )
            for index in range(420)
        ]

        results = [
            build_live_predictive_evidence_mapping(
                observation=observation
            )
            for observation in observations
        ]

        directional = [
            result
            for result in results
            if isinstance(result, LivePredictiveEvidenceMapping)
        ]
        no_evidence = [
            result
            for result in results
            if isinstance(result, NoPredictiveEvidence)
        ]

        self.assertEqual(len(results), 420)
        self.assertEqual(len(directional), 210)
        self.assertEqual(len(no_evidence), 210)
        self.assertEqual(
            len({result.asset for result in results}),
            420,
        )
        self.assertEqual(
            {result.asset for result in no_evidence},
            {
                f"ASSET{index}/USDT"
                for index in range(420)
                if index % 2 == 1
            },
        )


if __name__ == "__main__":
    unittest.main()
