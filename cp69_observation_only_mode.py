"""Explicit opt-in switch for CP69 observation-only runtime mode.

This mode computes a current real-market observation and writes only the CP69
artifact. It deliberately bypasses CP49 Birth persistence, selection-tracker
persistence, MCP01 evidence persistence, and every downstream order-intent or
execution-request producer.
"""
from __future__ import annotations

import os

OBSERVATION_ONLY_ENV = "ARUNDATRADER_OBSERVATION_ONLY"


def is_observation_only_enabled() -> bool:
    """Enable only for the exact opt-in value '1'; default remains production path."""
    return os.environ.get(OBSERVATION_ONLY_ENV, "").strip() == "1"


__all__ = ["OBSERVATION_ONLY_ENV", "is_observation_only_enabled"]
