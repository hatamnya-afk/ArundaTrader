"""Focused tests for CP72's opt-in observation-only guard."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from cp69_observation_only_mode import (
    OBSERVATION_ONLY_ENV,
    is_observation_only_enabled,
)


class ObservationOnlyModeTests(unittest.TestCase):
    def test_disabled_when_environment_variable_is_absent(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_observation_only_enabled())

    def test_enabled_only_by_exact_one(self):
        for value in ("true", "yes", "on", "0", ""):
            with self.subTest(value=value), patch.dict(os.environ, {OBSERVATION_ONLY_ENV: value}):
                self.assertFalse(is_observation_only_enabled())
        with patch.dict(os.environ, {OBSERVATION_ONLY_ENV: "1"}):
            self.assertTrue(is_observation_only_enabled())
        with patch.dict(os.environ, {OBSERVATION_ONLY_ENV: " 1 "}):
            self.assertTrue(is_observation_only_enabled())

    def test_pipeline_declares_all_three_side_effect_guards(self):
        source = Path(__file__).with_name("arunda_pipeline.py").read_text(encoding="utf-8-sig")
        self.assertIn("if observation_only:", source)
        self.assertIn("OBSERVATION_ONLY_CP49_BIRTH=SKIPPED", source)
        self.assertIn("OBSERVATION_ONLY_SELECTION_TRACKER=SKIPPED", source)
        self.assertIn("OBSERVATION_ONLY_MCP01_EVIDENCE=SKIPPED", source)

    def test_observation_mode_returns_before_mcp01_and_order_intent(self):
        source = Path(__file__).with_name("arunda_pipeline.py").read_text(encoding="utf-8-sig")
        cp69_write = source.index('print("CP69_OBSERVATION_WRITTEN=1")')
        observation_exit = source.index("OBSERVATION_ONLY_MCP01_EVIDENCE=SKIPPED")
        mcp01_emission = source.index("emit_mcp01_evidence(")
        order_intent = source.index("produce_runtime_order_intents(")
        self.assertLess(cp69_write, observation_exit)
        self.assertLess(observation_exit, mcp01_emission)
        self.assertLess(observation_exit, order_intent)


if __name__ == "__main__":
    unittest.main()
