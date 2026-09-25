# -*- coding: utf-8 -*-

"""
ARUNDA TRADER ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â PIPELINE v1.0

PRODUCTION FUSED-SCORE ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ SCORE / DECISION BINDING
FINAL ORDER-INTENT CONTRACT / PROVENANCE PREFLIGHT

Architecture:
MARKET SNAPSHOT
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
MARKET DATA
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
OPPORTUNITY
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
SIGNAL VALIDATION
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
FUSION v0.6
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
FUSED SCORE BINDING v0.1
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
SCORE
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
DECISION
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
RISK
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
CURRENT RUNTIME QUANTITY
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
TRADE GATE
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
MARKET REGIME
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
ORDER INTENT
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
CANONICAL ORDER REQUEST
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
QUANTITY OBSERVABILITY
ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ
EXECUTION BOUNDARY

HARD SAFETY RULES:
- EXECUTION ENABLED = False
- No exchange writes
- No order submission
- No database writes
- No synthetic data
- No interpolation
- No fill
- No backfill
- No padding
- No blending
- Legacy market_technical forbidden
- CLOSED layers are not reopened
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ============================================================================

# CONFIGURATION

# ============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = PROJECT_DIR / "arunda.db"

EXECUTION_ENABLED = False

LAUNCH_TIMESTAMP = (
"2026-08-31T00:00:00+00:00"
)

EXPECTED_ASSETS = [
"BTC",
"ETH",
"SOL",
"XRP",
"ADA",
"DOGE",
"SHIB",
"LINK",
"AVAX",
"DOT",
"LTC",
"UNI",
"AAVE",
"SUI",
"NEAR",
]

EXPECTED_ASSET_SET = set(
EXPECTED_ASSETS
)

# ============================================================================

# ORDER-INTENT CONTRACT

# ============================================================================

CURRENT_ORDER_INTENT_REQUIRED_FIELDS = (
"asset",
"direction",
"entry_price",
"quantity",
"quantity_unit",
"quantity_source",
"confidence",
"regime",
"timestamp",
"snapshot_id",
"intent_id",
)

CURRENT_ORDER_INTENT_FORBIDDEN_FIELDS = (
"signal_strength",
"data_quality",
"source_row_id",
)

VALID_DIRECTIONS = {
"LONG",
"SHORT",
}

TRADE_READY_STATUS = "TRADE_READY"

ELIGIBLE_STATUS = "ELIGIBLE"

ACTIONABLE_DECISIONS = {
"TRADE",
"BUY",
"SELL",
"LONG",
"SHORT",
"ACTIONABLE",
}

APPROVED_RISK_STATUSES = {
"ACCEPTED",
"APPROVED",
"PASS",
}

POSITION_QUANTITY_SOURCE = (
"POSITION_SIZING.position_size"
)

POSITION_QUANTITY_UNIT = "BASE_ASSET"

CANONICAL_QUANTITY_SOURCE = (
"RISK.position_quantity"
)

CANONICAL_QUANTITY_UNIT = "BASE_ASSET"

# ============================================================================

# MODULE IMPORTS

# ============================================================================

import signal_validator
import signal_scorer
import decision_engine
import risk_engine
import risk_budget_engine
import position_sizing_engine
import trade_gate_engine
from cp44_real_portfolio_composition_v0_1 import (
    compose_real_portfolio_capital,
)

import market_regime_engine
import market_data_engine
import exchange_execution_contract
from zero_capital_research_trade_contract_v0_1 import (
    RESEARCH_TRADE,
    resolve_trade_quantity,
)
import fusion_engine
import production_fused_score_binding_v0_1
from cp69_runtime_observation import (
    append_observation,
    build_observation,
)

from exchange_execution_boundary import execute_order

# ============================================================================

# RUNTIME ORDER INTENT

# ============================================================================

    # ============================================================================

    # GENERIC HELPERS

    # ============================================================================

def fail(message: str) -> None:
    raise RuntimeError(message)

def utc_now_iso() -> str:
    return datetime.now(
    timezone.utc
    ).isoformat()

def normalize_asset(
    value: Any,
    ) -> str | None:
    if value is None:
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    return text
def normalize_status(
    value: Any,
    ) -> str | None:
    if value is None:
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    return text
def get_row_value(
    row: Any,
    *keys: str,
    ) -> Any:
    if not isinstance(row, dict):
        return None

    for key in keys:

        if key in row:
            return row[key]

    return None
def ensure_dict(
    value: Any,
    name: str,
    ) -> dict:
    if not isinstance(value, dict):
        fail(
            f"{name} must be a dict"
        )

    return value
def ensure_list(
    value: Any,
    name: str,
    ) -> list:
    if not isinstance(value, list):
        fail(
            f"{name} must be a list"
        )

    return value
def is_finite_number(
    value: Any,
    ) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
    # ============================================================================

    # SUBPROCESS

    # ============================================================================

def run_script(
    script_name: str,
    ) -> str:
    script_path = PROJECT_DIR / script_name

    if not script_path.exists():
        fail(
            "Required production script not found: "
            f"{script_path}"
        )

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"Production subprocess failed: {script_name}"
            f"\nSTDOUT:\n{result.stdout}"
            f"\nSTDERR:\n{result.stderr}"
        )

    return result.stdout
    # ============================================================================

    # MARKER PARSER

    # ============================================================================

def extract_marker_payload(
    output: str,
    marker: str,
    ) -> dict:
    matches = []

    for line in output.splitlines():

        if line.startswith(marker):

            payload = line[
                len(marker):
            ].strip()

            if payload:
                matches.append(payload)

    if not matches:
        fail(
            "Required runtime marker not found: "
            f"{marker}"
        )

    if len(matches) != 1:
        fail(
            "Runtime marker must appear exactly once: "
            f"{marker} | count={len(matches)}"
        )

    try:

        value = json.loads(
            matches[0]
        )

    except json.JSONDecodeError as exc:

        fail(
            f"Invalid JSON payload for marker "
            f"{marker}: {exc}"
        )

    if not isinstance(value, dict):

        fail(
            "Runtime marker payload must be dict: "
            f"{marker}"
        )

    return value
    # ============================================================================

    # MARKET SNAPSHOT

    # ============================================================================

def parse_market_runtime_snapshot(
    output: str,
    ) -> dict:
    snapshot = extract_marker_payload(
        output,
        "ARUNDA_CURRENT_RUNTIME_SNAPSHOT=",
    )

    if snapshot.get(
        "runtime_source"
    ) != "CURRENT_SUBPROCESS_RUN":

        fail(
            "Market snapshot is not from current subprocess run"
        )

    if not snapshot.get(
        "engine_version"
    ):

        fail(
            "Market snapshot engine_version missing"
        )

    if snapshot.get(
        "source"
    ) != "COINMARKETCAP":

        fail(
            "Market snapshot source is not COINMARKETCAP"
        )

    if snapshot.get(
        "timeframe"
    ) != "SNAPSHOT":

        fail(
            "Market snapshot timeframe is not SNAPSHOT"
        )

    timestamp = snapshot.get(
        "timestamp"
    )

    if not timestamp:

        fail(
            "Market snapshot timestamp missing"
        )

    assets = snapshot.get(
        "assets"
    )

    if not isinstance(
        assets,
        list,
    ):

        fail(
            "Market snapshot assets must be list"
        )

    if len(assets) != len(
        EXPECTED_ASSETS
    ):

        fail(
            "Market snapshot asset count mismatch"
        )

    seen = set()

    for row in assets:

        if not isinstance(
            row,
            dict,
        ):

            fail(
                "Market snapshot asset row must be dict"
            )

        asset = normalize_asset(
            row.get("asset")
        )

        if asset is None:

            fail(
                "Market snapshot asset missing"
            )

        if asset in seen:

            fail(
                f"Duplicate market snapshot asset: {asset}"
            )

        seen.add(asset)

        if asset not in EXPECTED_ASSET_SET:

            fail(
                f"Unexpected production asset: {asset}"
            )

        if row.get(
            "timestamp"
        ) != timestamp:

            fail(
                f"Market snapshot timestamp mismatch: {asset}"
            )

        if row.get("price") is None:

            fail(
                f"Market snapshot price missing: {asset}"
            )

    if seen != EXPECTED_ASSET_SET:

        fail(
            "Market snapshot exact coverage failed"
        )

    return snapshot
def build_runtime_snapshot_id(
    snapshot: dict,
    ) -> str:
    canonical_assets = []

    for row in snapshot["assets"]:

        canonical_assets.append(
            {
                "asset": normalize_asset(
                    row["asset"]
                ),
                "timestamp": row["timestamp"],
                "price": row["price"],
                "change_1h": row.get(
                    "change_1h"
                ),
                "change_24h": row.get(
                    "change_24h"
                ),
                "market_cap": row.get(
                    "market_cap"
                ),
                "volume_24h": row.get(
                    "volume_24h"
                ),
            }
        )

    canonical_assets.sort(
        key=lambda x: x["asset"]
    )

    payload = {
        "timestamp": snapshot["timestamp"],
        "assets": canonical_assets,
    }

    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    digest = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    return f"RS-{digest}"
    # ============================================================================

    # OPPORTUNITY

    # ============================================================================

def parse_opportunity_runtime_snapshot(
    output: str,
    ) -> dict:
    snapshot = extract_marker_payload(
        output,
        "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT=",
    )

    if snapshot.get(
        "runtime_source"
    ) != "CURRENT_SUBPROCESS_RUN":

        fail(
            "Opportunity snapshot is not current-run"
        )

    if not snapshot.get(
        "engine_version"
    ):

        fail(
            "Opportunity engine_version missing"
        )

    opportunities = snapshot.get(
        "opportunities"
    )

    if not isinstance(
        opportunities,
        list,
    ):

        fail(
            "Opportunity opportunities must be list"
        )

    if len(opportunities) != len(
        EXPECTED_ASSETS
    ):

        fail(
            "Opportunity coverage mismatch"
        )

    seen = set()

    for row in opportunities:

        if not isinstance(
            row,
            dict,
        ):

            fail(
                "Opportunity row must be dict"
            )

        asset = normalize_asset(
            row.get(
                "symbol",
                row.get("asset"),
            )
        )

        if asset is None:

            fail(
                "Opportunity asset missing"
            )

        if asset in seen:

            fail(
                f"Duplicate Opportunity asset: {asset}"
            )

        seen.add(asset)

        if asset not in EXPECTED_ASSET_SET:

            fail(
                f"Unexpected Opportunity asset: {asset}"
            )

    if seen != EXPECTED_ASSET_SET:

        fail(
            "Opportunity exact asset coverage failed"
        )

    return snapshot
def opportunity_map(
    opportunity_snapshot: dict,
    ) -> dict[str, dict]:
    result = {}

    for row in opportunity_snapshot[
        "opportunities"
    ]:

        asset = normalize_asset(
            row.get(
                "symbol",
                row.get("asset"),
            )
        )

        if asset is None:

            fail(
                "Opportunity map encountered missing asset"
            )

        if asset in result:

            fail(
                f"Duplicate Opportunity asset: {asset}"
            )

        result[asset] = row

    return result
def get_opportunity_status(
    row: dict,
    ) -> str | None:
    return normalize_status(
        row.get("status")
    )
    # ============================================================================

    # SIGNAL VALIDATOR

    # ============================================================================

def validate_signal_coverage(
    signals: dict,
    ) -> None:
    if not isinstance(
        signals,
        dict,
    ):

        fail(
            "Validated signals must be a dict."
        )

    if len(signals) != len(
        EXPECTED_ASSETS
    ):

        fail(
            "Validated signal coverage mismatch"
        )

    seen = set()

    for key, row in signals.items():

        asset = normalize_asset(key)

        if asset is None:

            fail(
                "Validated signal contains empty asset key"
            )

        if asset in seen:

            fail(
                f"Duplicate normalized signal asset: {asset}"
            )

        seen.add(asset)

        if asset not in EXPECTED_ASSET_SET:

            fail(
                f"Unexpected validated signal asset: {asset}"
            )

        if not isinstance(
            row,
            dict,
        ):

            fail(
                f"Validated signal row must be dict: {asset}"
            )

        row_asset = normalize_asset(
            row.get("asset")
        )

        row_symbol = normalize_asset(
            row.get("symbol")
        )

        if (
            row_asset != asset
            and row_symbol != asset
        ):

            fail(
                f"Validated signal identity mismatch: {asset}"
            )

        if row.get(
            "valid"
        ) is not True:

            fail(
                f"Validated signal is not valid: {asset}"
            )

    if seen != EXPECTED_ASSET_SET:

        fail(
            "Validated signal exact coverage failed"
        )
def normalize_validated_signals(
    value: Any,
    ) -> dict[str, dict]:
    if not isinstance(
        value,
        dict,
    ):

        fail(
            "Validated signals must be a dict."
        )

    normalized = {}

    for original_key, row in value.items():

        asset = normalize_asset(
            original_key
        )

        if asset is None:

            fail(
                "Validated signals contains empty asset key"
            )

        if asset in normalized:

            fail(
                f"Duplicate normalized asset: {asset}"
            )

        if asset not in EXPECTED_ASSET_SET:

            fail(
                f"Unexpected validated asset: {asset}"
            )

        if not isinstance(
            row,
            dict,
        ):

            fail(
                f"Validated signal row must be dict: {asset}"
            )

        row_asset = normalize_asset(
            row.get("asset")
        )

        row_symbol = normalize_asset(
            row.get("symbol")
        )

        if (
            row_asset != asset
            and row_symbol != asset
        ):

            fail(
                f"Validated signal identity mismatch: {asset}"
            )

        if row.get(
            "valid"
        ) is not True:

            fail(
                f"Validated signal is not valid: {asset}"
            )

        normalized[asset] = row

    if set(
        normalized.keys()
    ) != EXPECTED_ASSET_SET:

        fail(
            "Validated signal exact coverage failed"
        )

    return normalized
    # ============================================================================

    # GENERIC ROW EXTRACTION

    # ============================================================================

def extract_rows(
    value: Any,
    preferred_keys: tuple[str, ...] = (),
    ) -> list[dict]:
    if isinstance(
        value,
        list,
    ):

        if all(
            isinstance(item, dict)
            for item in value
        ):

            return value

        return []

    if isinstance(
        value,
        dict,
    ):

        for key in preferred_keys:

            candidate = value.get(key)

            if isinstance(
                candidate,
                list,
            ):

                if all(
                    isinstance(item, dict)
                    for item in candidate
                ):

                    return candidate

        for key in (
            "rows",
            "assets",
            "signals",
            "validated_signals",
            "decisions",
            "risk",
            "results",
            "data",
            "snapshot",
        ):

            candidate = value.get(key)

            if isinstance(
                candidate,
                list,
            ):

                if all(
                    isinstance(item, dict)
                    for item in candidate
                ):

                    return candidate

        if (
            len(value) == len(EXPECTED_ASSETS)
            and all(
                normalize_asset(k)
                in EXPECTED_ASSET_SET
                and isinstance(v, dict)
                for k, v in value.items()
            )
        ):

            return list(
                value.values()
            )

    return []
def exact_asset_rows(
    rows: list[dict],
    stage_name: str,
    ) -> list[dict]:
    if len(rows) != len(
        EXPECTED_ASSETS
    ):

        fail(
            f"{stage_name} row count mismatch: "
            f"expected={len(EXPECTED_ASSETS)} "
            f"actual={len(rows)}"
        )

    seen = set()

    for row in rows:

        if not isinstance(
            row,
            dict,
        ):

            fail(
                f"{stage_name}: row must be dict"
            )

        asset = normalize_asset(
            row.get(
                "asset",
                row.get("symbol"),
            )
        )

        if asset is None:

            fail(
                f"{stage_name}: missing asset"
            )

        if asset in seen:

            fail(
                f"{stage_name}: duplicate asset {asset}"
            )

        seen.add(asset)

        if asset not in EXPECTED_ASSET_SET:

            fail(
                f"{stage_name}: unexpected asset {asset}"
            )

    if seen != EXPECTED_ASSET_SET:

        fail(
            f"{stage_name}: exact asset coverage failed"
        )

    return rows
def decision_map(
    rows: list[dict],
    ) -> dict[str, dict]:
    result = {}

    for row in rows:

        asset = normalize_asset(
            row.get(
                "asset",
                row.get("symbol"),
            )
        )

        if asset is None:

            fail(
                "Decision row missing asset"
            )

        if asset in result:

            fail(
                f"Duplicate Decision asset: {asset}"
            )

        result[asset] = row

    return result
def risk_map(
    rows: list[dict],
    ) -> dict[str, dict]:
    result = {}

    for row in rows:

        asset = normalize_asset(
            row.get(
                "asset",
                row.get("symbol"),
            )
        )

        if asset is None:

            fail(
                "Risk row missing asset"
            )

        if asset in result:

            fail(
                f"Duplicate Risk asset: {asset}"
            )

        result[asset] = row

    return result
    # ============================================================================

    # FUSION v0.6 ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ SCORE BINDING

    # ============================================================================

def build_production_fusion_snapshot(
    validated_signals: dict,
    ) -> dict:
    validate_signal_coverage(
        validated_signals
    )

    fusion_snapshot = (
        fusion_engine.run()
    )

    if not isinstance(
        fusion_snapshot,
        dict,
    ):

        fail(
            "FUSION_v0.6 runtime result must be dict"
        )

    return fusion_snapshot
def bind_fused_scores(
    validated_signals: dict,
    fusion_snapshot: dict,
    ) -> dict:
    validate_signal_coverage(
        validated_signals
    )

    if not isinstance(
        fusion_snapshot,
        dict,
    ):

        fail(
            "Fusion snapshot must be dict"
        )

    try:

        score_snapshot = (
            production_fused_score_binding_v0_1.run(
                validated_signals,
                fusion_snapshot,
            )
        )

    except Exception as exc:

        raise RuntimeError(
            "PRODUCTION FUSED-SCORE BINDING FAILED: "
            f"{exc}"
        ) from exc

    if not isinstance(
        score_snapshot,
        dict,
    ):

        fail(
            "Fused-score binding must return dict"
        )

    return score_snapshot
    # ============================================================================

    # MARKET REGIME

    # ============================================================================

def load_current_market_regime() -> dict:
    regime_snapshot = (
        market_regime_engine.load_market_regime()
    )

    if not isinstance(
        regime_snapshot,
        dict,
    ):

        fail(
            "CURRENT_MARKET_REGIME must be a dict"
        )

    return regime_snapshot
def get_current_regime(
    regime_snapshot: dict,
    asset: str,
    ) -> Any:
    asset = normalize_asset(
        asset
    )

    if asset is None:

        fail(
            "Cannot resolve regime for empty asset"
        )

    direct = regime_snapshot.get(
        asset
    )

    if (
        isinstance(direct, dict)
        and "regime" in direct
    ):

        return direct["regime"]

    for key, value in regime_snapshot.items():

        if str(key).strip().upper() == asset:

            if (
                isinstance(value, dict)
                and "regime" in value
            ):

                return value["regime"]

    fail(
        "CURRENT_MARKET_REGIME ownership unavailable "
        f"for asset={asset}"
    )
    # ============================================================================

    # MARKET-DATA RUNTIME EXTRACTION

    # ============================================================================

def _find_runtime_asset_record(
    market_data_result: Any,
    asset: str,
    ) -> dict | None:
    if not isinstance(
        market_data_result,
        dict,
    ):

        return None

    candidates = []

    candidates.extend(
        extract_rows(
            market_data_result,
            (
                "assets",
                "rows",
                "results",
                "data",
                "market_data",
                "ohlcv",
            ),
        )
    )

    if not candidates:

        for key, value in market_data_result.items():

            if normalize_asset(key) == asset:

                if isinstance(
                    value,
                    dict,
                ):

                    return value

    for row in candidates:

        row_asset = normalize_asset(
            row.get(
                "asset",
                row.get(
                    "symbol",
                    row.get("market"),
                ),
            )
        )

        if row_asset == asset:

            return row

    return None
def _runtime_value(
    asset_record: dict | None,
    *keys: str,
    ) -> Any:
    if not isinstance(
        asset_record,
        dict,
    ):

        return None

    for key in keys:

        if key in asset_record:

            return asset_record[key]

    return None
def _resolve_market_data_provenance(
    market_data_result: Any,
    asset: str,
    ) -> dict:
    record = _find_runtime_asset_record(
        market_data_result,
        asset,
    )

    if record is None:

        fail(
            "CURRENT RUNTIME MARKET DATA asset record "
            f"missing: {asset}"
        )

    source = _runtime_value(
        record,
        "source",
        "provider",
        "data_source",
    )

    timestamp = _runtime_value(
        record,
        "latest_ohlcv_timestamp",
            "latest_candle_timestamp",
        "ohlcv_timestamp",
        "timestamp",
        "latest_timestamp",
    )

    candle_count = _runtime_value(
        record,
        "real_candle_count",
        "candle_count",
        "real_candles",
    )

    atr14 = _runtime_value(
        record,
        "atr14",
        "atr_14",
    )

    stop_distance = _runtime_value(
        record,
        "stop_distance",
    )

    if not source:

        fail(
            "CURRENT RUNTIME MARKET DATA source missing: "
            f"{asset}"
        )

    if not timestamp:

        fail(
            "CURRENT RUNTIME MARKET DATA timestamp missing: "
            f"{asset}"
        )

    if candle_count is None:

        fail(
            "CURRENT RUNTIME MARKET DATA real candle count "
            f"missing: {asset}"
        )

    if not isinstance(
        candle_count,
        int,
    ) or isinstance(
        candle_count,
        bool,
    ) or candle_count < 1:

        fail(
            "CURRENT RUNTIME MARKET DATA candle count invalid: "
            f"{asset}"
        )

    if atr14 is None:

        fail(
            "CURRENT RUNTIME MARKET DATA ATR14 missing: "
            f"{asset}"
        )

    if stop_distance is None:

        fail(
            "CURRENT RUNTIME MARKET DATA stop_distance missing: "
            f"{asset}"
        )

    return {
        "source": source,
        "latest_ohlcv_timestamp": timestamp,
        "real_candle_count": candle_count,
        "atr14": atr14,
        "stop_distance": stop_distance,
    }
    # ============================================================================

    # CURRENT-RUNTIME QUANTITY BRIDGE

    # ============================================================================

def build_runtime_quantity_bridge(
    snapshot_id: str,
    opportunity_rows: list[dict],
    risk_snapshot: dict,
    market_data_result: dict,
    ) -> dict:
    if not isinstance(
        opportunity_rows,
        list,
    ):

        fail(
            "Opportunity rows must be list"
        )

    opportunities = opportunity_map(
        {
            "opportunities": opportunity_rows,
        }
    )

    risk_rows = extract_rows(
        risk_snapshot,
        (
            "risk",
            "risk_decisions",
            "decisions",
            "rows",
            "assets",
            "results",
        ),
    )

    risk_rows = exact_asset_rows(
        risk_rows,
        "RISK",
    )

    r_map = risk_map(
        risk_rows
    )

    if market_data_result is None:

        fail(
            "CURRENT RUNTIME MARKET DATA unavailable"
        )

    records = {}

    for asset in EXPECTED_ASSETS:

        opportunity = opportunities.get(
            asset
        )

        if not isinstance(
            opportunity,
            dict,
        ):

            fail(
                f"Opportunity missing: {asset}"
            )

        risk_row = r_map.get(
            asset
        )

        if not isinstance(
            risk_row,
            dict,
        ):

            fail(
                f"Risk row missing: {asset}"
            )

        risk_status = normalize_status(
            get_row_value(
                risk_row,
                "risk_status",
                "status",
                "decision",
                "risk_state",
            )
        )

        if risk_status not in APPROVED_RISK_STATUSES:
            continue

        direction = normalize_status(
            risk_row.get("direction")
        )

        if direction not in VALID_DIRECTIONS:

            fail(
                f"Risk direction invalid: {asset}"
            )

        entry_price = opportunity.get(
            "price"
        )

        if entry_price is None:

            fail(
                f"Opportunity price missing: {asset}"
            )


        if not is_finite_number(
            entry_price
        ):

            fail(
                f"Opportunity price invalid: {asset}"
            )

        budget_state = normalize_status(
            risk_row.get(
                "budget_state"
            )
        )

        if budget_state in (
            "BLOCKED",
            "UNALLOCATED",
        ):
            continue

        if budget_state != "ALLOCATED":
            fail(
                f"Risk budget state invalid: {asset}"
            )

        risk_budget = risk_row.get(
            "risk_budget"
        )

        if risk_budget is None:
            risk_budget = risk_row.get(
                "allocated_budget"
            )

        if risk_budget is None:
            fail(
                f"Risk budget missing: {asset}"
            )

        if not is_finite_number(
            risk_budget
        ):

            fail(
                f"Risk budget invalid: {asset}"
            )

        position_size = risk_row.get(
            "position_size"
        )

        if position_size is None:

            position_size = risk_row.get(
                "position_quantity"
            )

        if position_size is None:

            fail(
                f"Risk position size missing: {asset}"
            )

        if not is_finite_number(
            position_size
        ):

            fail(
                f"Risk position size invalid: {asset}"
            )

        if float(position_size) <= 0:

            fail(
                f"Risk position size must be > 0: {asset}"
            )

        quantity_unit = risk_row.get(
            "quantity_unit"
        )

        if quantity_unit is None:

            quantity_unit = POSITION_QUANTITY_UNIT

        quantity_source = risk_row.get(
            "quantity_source"
        )

        if quantity_source is None:

            quantity_source = POSITION_QUANTITY_SOURCE

        if quantity_unit != POSITION_QUANTITY_UNIT:

            fail(
                f"Risk quantity unit invalid: {asset}"
            )

        if quantity_source != POSITION_QUANTITY_SOURCE:

            fail(
                f"Risk quantity source invalid: {asset}"
            )

        for flag in (
            "quantity_changed",
            "quantity_recomputed",
            "quantity_rescaled",
            "quantity_rounded",
            "quantity_clipped",
        ):

            if risk_row.get(flag, False) is not False:

                fail(
                    f"Risk quantity transformation detected: "
                    f"{asset}.{flag}"
                )

        _cp27c_candles = getattr(
            market_data_result,
            "candles",
            None,
        )

        if not _cp27c_candles:
            fail(
                f"CP27-C REAL CANDLES MISSING: {asset}"
            )

        _cp27c_atr14 = market_data_engine.calculate_real_atr14(
            _cp27c_candles
        )

        if _cp27c_atr14 is None:
            fail(
                f"CP27-C ATR14 UNAVAILABLE: {asset}"
            )

        _cp27c_stop_distance = (
            market_data_engine.calculate_runtime_stop_distance(
                _cp27c_atr14
            )
        )

        if _cp27c_stop_distance is None:
            fail(
                f"CP27-C STOP_DISTANCE UNAVAILABLE: {asset}"
            )

        risk_row["position_quantity"] = (
            position_size
        )

        risk_row["quantity_unit"] = (
            POSITION_QUANTITY_UNIT
        )

        risk_row["quantity_source"] = (
            POSITION_QUANTITY_SOURCE
        )

        risk_row["quantity_changed"] = False
        risk_row["quantity_recomputed"] = False
        risk_row["quantity_rescaled"] = False
        risk_row["quantity_rounded"] = False
        risk_row["quantity_clipped"] = False

        records[asset] = {
            "snapshot_id": snapshot_id,
            "asset": asset,
            "timeframe": "1h",
            "source": runtime[
                "source"
            ],
            "latest_ohlcv_timestamp": runtime[
                "latest_ohlcv_timestamp"
            ],
            "real_candle_count": runtime[
                "real_candle_count"
            ],
            "atr14": _cp27c_atr14,
            "stop_distance": _cp27c_stop_distance,
            "risk_budget": risk_budget,
            "entry_price": entry_price,
            "position_size": position_size,
            "risk_position_quantity": position_size,
            "order_intent_quantity": None,
            "canonical_order_request_quantity": None,
            "quantity_unit": POSITION_QUANTITY_UNIT,
            "quantity_source": POSITION_QUANTITY_SOURCE,
            "quantity_changed": False,
            "quantity_recomputed": False,
            "quantity_rescaled": False,
            "quantity_rounded": False,
            "quantity_clipped": False,
        }

    return records
    # ============================================================================

    # QUANTITY OBSERVABILITY VALIDATION

    # ============================================================================

def validate_runtime_quantity_records(
    quantity_records: dict,
    snapshot_id: str,
    ) -> None:
    if not isinstance(
        quantity_records,
        dict,
    ):

        fail(
            "Quantity records must be dict"
        )

    if (
        not isinstance(
            snapshot_id,
            str,
        )
        or not snapshot_id
    ):

        fail(
            "Quantity observability snapshot_id missing"
        )

    for asset, record in quantity_records.items():

        asset = normalize_asset(
            asset
        )

        if asset not in EXPECTED_ASSET_SET:

            fail(
                f"Unexpected quantity asset: {asset}"
            )

        if not isinstance(
            record,
            dict,
        ):

            fail(
                f"Quantity record must be dict: {asset}"
            )

        if record.get(
            "snapshot_id"
        ) != snapshot_id:

            fail(
                f"Quantity snapshot mismatch: {asset}"
            )

        if record.get(
            "asset"
        ) != asset:

            fail(
                f"Quantity asset mismatch: {asset}"
            )

        if record.get(
            "timeframe"
        ) != "1h":

            fail(
                f"Quantity timeframe invalid: {asset}"
            )

        if not record.get(
            "source"
        ):

            fail(
                f"Quantity source missing: {asset}"
            )

        if not record.get(
            "latest_ohlcv_timestamp"
        ):

            fail(
                "Quantity latest OHLCV timestamp missing: "
                f"{asset}"
            )

        candle_count = record.get(
            "real_candle_count"
        )

        if (
            not isinstance(
                candle_count,
                int,
            )
            or isinstance(
                candle_count,
                bool,
            )
            or candle_count < 1
        ):

            fail(
                f"Quantity candle count invalid: {asset}"
            )

        required_runtime_values = (
            "atr14",
            "stop_distance",
            "risk_budget",
            "entry_price",
            "position_size",
            "risk_position_quantity",
            "order_intent_quantity",
            "canonical_order_request_quantity",
        )

        for field in required_runtime_values:

            if record.get(field) is None:

                fail(
                    "Quantity observability runtime value "
                    f"missing: {asset}.{field}"
                )

        for field in required_runtime_values:

            if not is_finite_number(
                record.get(field)
            ):

                fail(
                    "Quantity runtime value invalid: "
                    f"{asset}.{field}"
                )

        if (
            record.get(
                "position_size"
            )
            != record.get(
                "risk_position_quantity"
            )
        ):

            fail(
                f"Quantity Position/Risk mismatch: {asset}"
            )

        if (
            record.get(
                "risk_position_quantity"
            )
            != record.get(
                "order_intent_quantity"
            )
        ):

            fail(
                f"Quantity Risk/OrderIntent mismatch: {asset}"
            )

        if (
            record.get(
                "order_intent_quantity"
            )
            != record.get(
                "canonical_order_request_quantity"
            )
        ):

            fail(
                f"Quantity OrderIntent/Canonical mismatch: {asset}"
            )

        if record.get(
            "quantity_unit"
        ) != POSITION_QUANTITY_UNIT:

            fail(
                f"Quantity unit invalid: {asset}"
            )

        if record.get(
            "quantity_source"
        ) != POSITION_QUANTITY_SOURCE:

            fail(
                f"Quantity source invalid: {asset}"
            )

        for flag in (
            "quantity_changed",
            "quantity_recomputed",
            "quantity_rescaled",
            "quantity_rounded",
            "quantity_clipped",
        ):

            if record.get(flag) is not False:

                fail(
                    "Quantity transformation detected: "
                    f"{asset}.{flag}"
                )
class RuntimeOrderIntent(dict):
        """
        Visible ORDER_INTENT contract contains exactly eleven fields.

        Quantity observability is also retained as runtime metadata for
        downstream invariants and transformation guards.
        """

        def __init__(
            self,
            *,
            quantity,
            quantity_unit,
            quantity_source,
            asset,
            direction,
            entry_price,
            confidence,
            regime,
            timestamp,
            snapshot_id,
            intent_id,
        ):
            super().__init__(
                asset=asset,
                direction=direction,
                entry_price=entry_price,
                quantity=quantity,
                quantity_unit=quantity_unit,
                quantity_source=quantity_source,
                confidence=confidence,
                regime=regime,
                timestamp=timestamp,
                snapshot_id=snapshot_id,
                intent_id=intent_id,
            )

            self.quantity = quantity
            self.quantity_unit = quantity_unit
            self.quantity_source = quantity_source

            self.quantity_changed = False
            self.quantity_recomputed = False
            self.quantity_rescaled = False
            self.quantity_rounded = False
            self.quantity_clipped = False


    # ============================================================================
    # GENERIC HELPERS
    # ============================================================================

def fail(message: str) -> None:
        raise RuntimeError(message)


def utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def normalize_asset(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip().upper()

        if not text:
            return None

        return text


def normalize_status(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip().upper()

        if not text:
            return None

        return text


def get_row_value(row: Any, *keys: str) -> Any:
        if not isinstance(row, dict):
            return None

        for key in keys:
            if key in row:
                return row[key]

        return None


def ensure_dict(value: Any, name: str) -> dict:
        if not isinstance(value, dict):
            fail(f"{name} must be a dict")

        return value


def ensure_list(value: Any, name: str) -> list:
        if not isinstance(value, list):
            fail(f"{name} must be a list")

        return value


def is_finite_number(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )


    # ============================================================================
    # SUBPROCESS
    # ============================================================================

def run_script(script_name: str) -> str:
        script_path = PROJECT_DIR / script_name

        if not script_path.exists():
            fail(
                "Required production script not found: "
                f"{script_path}"
            )

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
            ],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Production subprocess failed: {script_name}"
                f"\nSTDOUT:\n{result.stdout}"
                f"\nSTDERR:\n{result.stderr}"
            )

        return result.stdout


    # ============================================================================
    # MARKER PARSER
    # ============================================================================

def extract_marker_payload(
        output: str,
        marker: str,
    ) -> dict:
        matches = []

        for line in output.splitlines():
            if line.startswith(marker):
                payload = line[len(marker):].strip()

                if payload:
                    matches.append(payload)

        if not matches:
            fail(
                "Required runtime marker not found: "
                f"{marker}"
            )

        if len(matches) != 1:
            fail(
                "Runtime marker must appear exactly once: "
                f"{marker} | count={len(matches)}"
            )

        try:
            value = json.loads(matches[0])
        except json.JSONDecodeError as exc:
            fail(
                f"Invalid JSON payload for marker "
                f"{marker}: {exc}"
            )

        if not isinstance(value, dict):
            fail(
                "Runtime marker payload must be dict: "
                f"{marker}"
            )

        return value


    # ============================================================================
    # MARKET SNAPSHOT
    # ============================================================================

def parse_market_runtime_snapshot(
        output: str,
    ) -> dict:
        snapshot = extract_marker_payload(
            output,
            "ARUNDA_CURRENT_RUNTIME_SNAPSHOT=",
        )

        if snapshot.get("runtime_source") != "CURRENT_SUBPROCESS_RUN":
            fail(
                "Market snapshot is not from current subprocess run"
            )

        if not snapshot.get("engine_version"):
            fail(
                "Market snapshot engine_version missing"
            )

        if snapshot.get("source") != "COINMARKETCAP":
            fail(
                "Market snapshot source is not COINMARKETCAP"
            )

        if snapshot.get("timeframe") != "SNAPSHOT":
            fail(
                "Market snapshot timeframe is not SNAPSHOT"
            )

        timestamp = snapshot.get("timestamp")

        if not timestamp:
            fail(
                "Market snapshot timestamp missing"
            )

        assets = snapshot.get("assets")

        if not isinstance(assets, list):
            fail(
                "Market snapshot assets must be list"
            )

        if len(assets) != len(EXPECTED_ASSETS):
            fail(
                "Market snapshot asset count mismatch"
            )

        seen = set()

        for row in assets:
            if not isinstance(row, dict):
                fail(
                    "Market snapshot asset row must be dict"
                )

            asset = normalize_asset(row.get("asset"))

            if asset is None:
                fail(
                    "Market snapshot asset missing"
                )

            if asset in seen:
                fail(
                    f"Duplicate market snapshot asset: {asset}"
                )

            seen.add(asset)

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"Unexpected production asset: {asset}"
                )

            if row.get("timestamp") != timestamp:
                fail(
                    f"Market snapshot timestamp mismatch: {asset}"
                )

            if row.get("price") is None:
                fail(
                    f"Market snapshot price missing: {asset}"
                )

        if seen != EXPECTED_ASSET_SET:
            fail(
                "Market snapshot exact coverage failed"
            )

        return snapshot


def build_runtime_snapshot_id(
        snapshot: dict,
    ) -> str:
        canonical_assets = []

        for row in snapshot["assets"]:
            canonical_assets.append(
                {
                    "asset": normalize_asset(row["asset"]),
                    "timestamp": row["timestamp"],
                    "price": row["price"],
                    "change_1h": row.get("change_1h"),
                    "change_24h": row.get("change_24h"),
                    "market_cap": row.get("market_cap"),
                    "volume_24h": row.get("volume_24h"),
                }
            )

        canonical_assets.sort(
            key=lambda x: x["asset"]
        )

        payload = {
            "timestamp": snapshot["timestamp"],
            "assets": canonical_assets,
        }

        canonical_json = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        digest = hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()

        return f"RS-{digest}"


    # ============================================================================
    # OPPORTUNITY
    # ============================================================================

def parse_opportunity_runtime_snapshot(
        output: str,
    ) -> dict:
        snapshot = extract_marker_payload(
            output,
            "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT=",
        )

        if snapshot.get("runtime_source") != "CURRENT_SUBPROCESS_RUN":
            fail(
                "Opportunity snapshot is not current-run"
            )

        if not snapshot.get("engine_version"):
            fail(
                "Opportunity engine_version missing"
            )

        opportunities = snapshot.get("opportunities")

        if not isinstance(opportunities, list):
            fail(
                "Opportunity opportunities must be list"
            )

        if len(opportunities) != len(EXPECTED_ASSETS):
            fail(
                "Opportunity coverage mismatch"
            )

        seen = set()

        for row in opportunities:
            if not isinstance(row, dict):
                fail(
                    "Opportunity row must be dict"
                )

            asset = normalize_asset(
                row.get(
                    "symbol",
                    row.get("asset"),
                )
            )

            if asset is None:
                fail(
                    "Opportunity asset missing"
                )

            if asset in seen:
                fail(
                    f"Duplicate Opportunity asset: {asset}"
                )

            seen.add(asset)

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"Unexpected Opportunity asset: {asset}"
                )

        if seen != EXPECTED_ASSET_SET:
            fail(
                "Opportunity exact asset coverage failed"
            )

        return snapshot


def opportunity_map(
        opportunity_snapshot: dict,
    ) -> dict[str, dict]:
        result = {}

        for row in opportunity_snapshot["opportunities"]:
            asset = normalize_asset(
                row.get(
                    "symbol",
                    row.get("asset"),
                )
            )

            if asset is None:
                fail(
                    "Opportunity map encountered missing asset"
                )

            if asset in result:
                fail(
                    f"Duplicate Opportunity asset: {asset}"
                )

            result[asset] = row

        return result


def get_opportunity_status(
        row: dict,
    ) -> str | None:
        return normalize_status(
            row.get("status")
        )


    # ============================================================================
    # SIGNAL VALIDATOR
    # ============================================================================

def validate_signal_coverage(
        signals: dict,
    ) -> None:
        if not isinstance(signals, dict):
            fail(
                "Validated signals must be a dict."
            )

        if len(signals) != len(EXPECTED_ASSETS):
            fail(
                "Validated signal coverage mismatch"
            )

        seen = set()

        for key, row in signals.items():
            asset = normalize_asset(key)

            if asset is None:
                fail(
                    "Validated signal contains empty asset key"
                )

            if asset in seen:
                fail(
                    f"Duplicate normalized signal asset: {asset}"
                )

            seen.add(asset)

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"Unexpected validated signal asset: {asset}"
                )

            if not isinstance(row, dict):
                fail(
                    f"Validated signal row must be dict: {asset}"
                )

            row_asset = normalize_asset(
                row.get("asset")
            )

            row_symbol = normalize_asset(
                row.get("symbol")
            )

            if (
                row_asset != asset
                and row_symbol != asset
            ):
                fail(
                    f"Validated signal identity mismatch: {asset}"
                )

            if row.get("valid") is not True:
                fail(
                    f"Validated signal is not valid: {asset}"
                )

        if seen != EXPECTED_ASSET_SET:
            fail(
                "Validated signal exact coverage failed"
            )


def normalize_validated_signals(
        value: Any,
    ) -> dict[str, dict]:
        if not isinstance(value, dict):
            fail(
                "Validated signals must be a dict."
            )

        normalized = {}

        for original_key, row in value.items():
            asset = normalize_asset(original_key)

            if asset is None:
                fail(
                    "Validated signals contains empty asset key"
                )

            if asset in normalized:
                fail(
                    f"Duplicate normalized asset: {asset}"
                )

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"Unexpected validated asset: {asset}"
                )

            if not isinstance(row, dict):
                fail(
                    f"Validated signal row must be dict: {asset}"
                )

            row_asset = normalize_asset(
                row.get("asset")
            )

            row_symbol = normalize_asset(
                row.get("symbol")
            )

            if (
                row_asset != asset
                and row_symbol != asset
            ):
                fail(
                    f"Validated signal identity mismatch: {asset}"
                )

            if row.get("valid") is not True:
                fail(
                    f"Validated signal is not valid: {asset}"
                )

            normalized[asset] = row

        if set(normalized.keys()) != EXPECTED_ASSET_SET:
            fail(
                "Validated signal exact coverage failed"
            )

        return normalized


    # ============================================================================
    # GENERIC ROW EXTRACTION
    # ============================================================================

def extract_rows(
        value: Any,
        preferred_keys: tuple[str, ...] = (),
    ) -> list[dict]:
        if isinstance(value, list):
            if all(
                isinstance(item, dict)
                for item in value
            ):
                return value

            return []

        if isinstance(value, dict):
            for key in preferred_keys:
                candidate = value.get(key)

                if isinstance(candidate, list):
                    if all(
                        isinstance(item, dict)
                        for item in candidate
                    ):
                        return candidate

            for key in (
                "rows",
                "assets",
                "signals",
                "validated_signals",
                "decisions",
                "risk",
                "risk_decisions",
                "results",
                "data",
                "snapshot",
                "market_data",
                "ohlcv",
            ):
                candidate = value.get(key)

                if isinstance(candidate, list):
                    if all(
                        isinstance(item, dict)
                        for item in candidate
                    ):
                        return candidate

            if (
                len(value) == len(EXPECTED_ASSETS)
                and all(
                    normalize_asset(k) in EXPECTED_ASSET_SET
                    and isinstance(v, dict)
                    for k, v in value.items()
                )
            ):
                return list(value.values())

        return []


def exact_asset_rows(
        rows: list[dict],
        stage_name: str,
    ) -> list[dict]:
        if len(rows) != len(EXPECTED_ASSETS):
            fail(
                f"{stage_name} row count mismatch: "
                f"expected={len(EXPECTED_ASSETS)} "
                f"actual={len(rows)}"
            )

        seen = set()

        for row in rows:
            if not isinstance(row, dict):
                fail(
                    f"{stage_name}: row must be dict"
                )

            asset = normalize_asset(
                row.get(
                    "asset",
                    row.get("symbol"),
                )
            )

            if asset is None:
                fail(
                    f"{stage_name}: missing asset"
                )

            if asset in seen:
                fail(
                    f"{stage_name}: duplicate asset {asset}"
                )

            seen.add(asset)

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"{stage_name}: unexpected asset {asset}"
                )

        if seen != EXPECTED_ASSET_SET:
            fail(
                f"{stage_name}: exact asset coverage failed"
            )

        return rows


def decision_map(
        rows: list[dict],
    ) -> dict[str, dict]:
        result = {}

        for row in rows:
            asset = normalize_asset(
                row.get(
                    "asset",
                    row.get("symbol"),
                )
            )

            if asset is None:
                fail(
                    "Decision row missing asset"
                )

            if asset in result:
                fail(
                    f"Duplicate Decision asset: {asset}"
                )

            result[asset] = row

        return result


def risk_map(
        rows: list[dict],
    ) -> dict[str, dict]:
        result = {}

        for row in rows:
            asset = normalize_asset(
                row.get(
                    "asset",
                    row.get("symbol"),
                )
            )

            if asset is None:
                fail(
                    "Risk row missing asset"
                )

            if asset in result:
                fail(
                    f"Duplicate Risk asset: {asset}"
                )

            result[asset] = row

        return result


    # ============================================================================
    # FUSION v0.6 ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ FUSED SCORE BINDING v0.1
    # ============================================================================

def build_production_fusion_snapshot(
        validated_signals: dict,
    ) -> dict:

        validate_signal_coverage(
            validated_signals
        )

        runtime_output = fusion_engine.run(
            validated_signals
        )

        if not isinstance(
            runtime_output,
            dict,
        ):
            fail(
                "FUSION_v0.6 runtime result must be dict"
            )

        results = runtime_output.get(
            "results"
        )

        if not isinstance(
            results,
            list,
        ):
            fail(
                "FUSION_v0.6 runtime results must be list"
            )

        fusion_snapshot = {}

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
                fail(
                    "FUSION_v0.6 result record must be dict"
                )

            asset = result.get(
                "asset"
            )

            if not isinstance(
                asset,
                str,
            ):
                fail(
                    "FUSION_v0.6 result missing asset"
                )

            asset = asset.strip().upper()

            if asset in fusion_snapshot:
                fail(
                    f"Duplicate Fusion asset: {asset}"
                )

            fusion_snapshot[asset] = result

        expected_assets = {
            "BTC", "ETH", "SOL", "XRP", "ADA",
            "DOGE", "SHIB", "LINK", "AVAX", "DOT",
            "LTC", "UNI", "AAVE", "SUI", "NEAR",
        }

        actual_assets = set(
            fusion_snapshot.keys()
        )

        if actual_assets != expected_assets:
            missing = expected_assets - actual_assets
            extra = actual_assets - expected_assets

            fail(
                f"Fusion asset coverage mismatch: "
                f"missing={sorted(missing)}, "
                f"extra={sorted(extra)}"
            )

        if len(fusion_snapshot) != 15:
            fail(
                f"Fusion snapshot count mismatch: "
                f"{len(fusion_snapshot)} != 15"
            )

        return fusion_snapshot


def bind_fused_scores(
        validated_signals: dict,
        fusion_snapshot: dict,
    ) -> dict:
        validate_signal_coverage(
            validated_signals
        )

        if not isinstance(
            fusion_snapshot,
            dict,
        ):
            fail(
                "Fusion snapshot must be dict"
            )

        try:
            score_snapshot = (
                production_fused_score_binding_v0_1.run(
                    validated_signals,
                    fusion_snapshot,
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "PRODUCTION FUSED-SCORE BINDING FAILED: "
                f"{exc}"
            ) from exc

        if not isinstance(
            score_snapshot,
            dict,
        ):
            fail(
                "Fused-score binding must return dict"
            )

        return score_snapshot


    # ============================================================================
    # MARKET REGIME
    # ============================================================================

def load_current_market_regime() -> dict:
        regime_snapshot = (
            market_regime_engine.load_market_regime()
        )

        if not isinstance(
            regime_snapshot,
            dict,
        ):
            fail(
                "CURRENT_MARKET_REGIME must be a dict"
            )

        return regime_snapshot


def get_current_regime(
        regime_snapshot: dict,
        asset: str,
    ) -> Any:
        asset = normalize_asset(asset)

        if asset is None:
            fail(
                "Cannot resolve regime for empty asset"
            )

        direct = regime_snapshot.get(asset)

        if (
            isinstance(direct, dict)
            and "regime" in direct
        ):
            return direct["regime"]

        for key, value in regime_snapshot.items():
            if str(key).strip().upper() == asset:
                if (
                    isinstance(value, dict)
                    and "regime" in value
                ):
                    return value["regime"]

        fail(
            "CURRENT_MARKET_REGIME ownership unavailable "
            f"for asset={asset}"
        )


    # ============================================================================
    # MARKET-DATA RUNTIME EXTRACTION
    # ============================================================================

def _find_runtime_asset_record(
        market_data_result: Any,
        asset: str,
    ) -> dict | None:
        if not isinstance(
            market_data_result,
            dict,
        ):
            return None

        asset = normalize_asset(asset)

        candidates = extract_rows(
            market_data_result,
            (
                "assets",
                "rows",
                "results",
                "data",
                "market_data",
                "ohlcv",
                "records",
            ),
        )

        for row in candidates:
            row_asset = normalize_asset(
                row.get(
                    "asset",
                    row.get(
                        "symbol",
                        row.get(
                            "market",
                            row.get("pair"),
                        ),
                    ),
                )
            )

            if row_asset == asset:
                return row

        for key, value in market_data_result.items():
            if normalize_asset(key) == asset:
                if isinstance(value, dict):
                    return value

        return None


def _runtime_value(
        asset_record: dict | None,
        *keys: str,
    ) -> Any:
        if not isinstance(
            asset_record,
            dict,
        ):
            return None

        for key in keys:
            if key in asset_record:
                return asset_record[key]

        return None


def _resolve_market_data_provenance(
        market_data_result: Any,
        asset: str,
    ) -> dict:
        record = _find_runtime_asset_record(
            market_data_result,
            asset,
        )

        if record is None:
            fail(
                "CURRENT RUNTIME MARKET DATA asset record "
                f"missing: {asset}"
            )

        source = _runtime_value(
            record,
            "source",
            "provider",
            "data_source",
        )

        timestamp = _runtime_value(
            record,
            "latest_ohlcv_timestamp",
            "latest_candle_timestamp",
            "ohlcv_timestamp",
            "timestamp",
            "latest_timestamp",
        )

        candle_count = _runtime_value(
            record,
            "real_candle_count",
            "valid_candles",
            "candle_count",
            "real_candles",
        )

        atr14 = _runtime_value(
            record,
            "atr14",
            "atr_14",
        )

        stop_distance = _runtime_value(
            record,
            "stop_distance",
        )

        if not source:
            fail(
                "CURRENT RUNTIME MARKET DATA source missing: "
                f"{asset}"
            )

        if not timestamp:
            fail(
                "CURRENT RUNTIME MARKET DATA timestamp missing: "
                f"{asset}"
            )

        if candle_count is None:
            fail(
                "CURRENT RUNTIME MARKET DATA real candle count "
                f"missing: {asset}"
            )

        if (
            not isinstance(candle_count, int)
            or isinstance(candle_count, bool)
            or candle_count < 1
        ):
            fail(
                "CURRENT RUNTIME MARKET DATA candle count invalid: "
                f"{asset}"
            )

        if atr14 is None:
            fail(
                "CURRENT RUNTIME MARKET DATA ATR14 missing: "
                f"{asset}"
            )

        if not is_finite_number(atr14):
            fail(
                "CURRENT RUNTIME MARKET DATA ATR14 invalid: "
                f"{asset}"
            )

        if float(atr14) <= 0:
            fail(
                "CURRENT RUNTIME MARKET DATA ATR14 must be > 0: "
                f"{asset}"
            )

        if stop_distance is None:
            fail(
                "CURRENT RUNTIME MARKET DATA stop_distance missing: "
                f"{asset}"
            )

        if not is_finite_number(stop_distance):
            fail(
                "CURRENT RUNTIME MARKET DATA stop_distance invalid: "
                f"{asset}"
            )

        if float(stop_distance) <= 0:
            fail(
                "CURRENT RUNTIME MARKET DATA stop_distance must be > 0: "
                f"{asset}"
            )

        return {
            "source": source,
            "latest_ohlcv_timestamp": timestamp,
            "real_candle_count": candle_count,
            "atr14": atr14,
            "stop_distance": stop_distance,
        }


    # ============================================================================
    # CURRENT-RUNTIME QUANTITY BRIDGE
    # ============================================================================

def build_runtime_quantity_bridge(
        snapshot_id: str,
        opportunity_rows: list[dict],
        risk_snapshot: dict,
        market_data_result: dict,
    ) -> dict:
        if not isinstance(
            opportunity_rows,
            list,
        ):
            fail(
                "Opportunity rows must be list"
            )

        opportunities = opportunity_map(
            {
                "opportunities": opportunity_rows,
            }
        )

        risk_rows = extract_rows(
            risk_snapshot,
            (
                "risk",
                "risk_decisions",
                "decisions",
                "rows",
                "assets",
                "results",
            ),
        )

        risk_rows = exact_asset_rows(
            risk_rows,
            "RISK",
        )

        r_map = risk_map(
            risk_rows
        )

        if market_data_result is None:
            fail(
                "CURRENT RUNTIME MARKET DATA unavailable"
            )

        if not isinstance(
            market_data_result,
            dict,
        ):
            fail(
                "CURRENT RUNTIME MARKET DATA result must be dict"
            )

        records = {}

        for asset in EXPECTED_ASSETS:
            opportunity = opportunities.get(asset)

            if not isinstance(
                opportunity,
                dict,
            ):
                fail(
                    f"Opportunity missing: {asset}"
                )

            risk_row = r_map.get(asset)

            if not isinstance(
                risk_row,
                dict,
            ):
                fail(
                    f"Risk row missing: {asset}"
                )

            risk_status = normalize_status(
                get_row_value(
                    risk_row,
                    "risk_status",
                    "status",
                    "decision",
                    "risk_state",
                )
            )

            if risk_status not in APPROVED_RISK_STATUSES:
                continue

            direction = normalize_status(
                risk_row.get("direction")
            )

            if direction not in VALID_DIRECTIONS:
                fail(
                    f"Risk direction invalid: {asset}"
                )

            entry_price = opportunity.get("price")

            if entry_price is None:
                fail(
                    f"Opportunity price missing: {asset}"
                )

            if not is_finite_number(entry_price):
                fail(
                    f"Opportunity price invalid: {asset}"
                )

            budget_state = normalize_status(
                risk_row.get(
                    "budget_state"
                )
            )

            if budget_state in (
                "BLOCKED",
                "UNALLOCATED",
            ):
                continue

            if budget_state != "ALLOCATED":
                fail(
                    f"Risk budget state invalid: {asset}"
                )

            risk_budget = risk_row.get(
                "risk_budget"
            )
            if risk_budget is None:
                risk_budget = risk_row.get(
                    "allocated_budget"
                )

            if risk_budget is None:
                fail(
                    f"Risk budget missing: {asset}"
                )

            if not is_finite_number(risk_budget):
                fail(
                    f"Risk budget invalid: {asset}"
                )

            position_size = risk_row.get(
                "position_size"
            )

            if position_size is None:
                position_size = risk_row.get(
                    "position_quantity"
                )

            if position_size is None:
                fail(
                    f"Risk position size missing: {asset}"
                )

            if not is_finite_number(position_size):
                fail(
                    f"Risk position size invalid: {asset}"
                )

            if float(position_size) <= 0:
                fail(
                    f"Risk position size must be > 0: {asset}"
                )

            quantity_unit = risk_row.get(
                "quantity_unit"
            )

            if quantity_unit is None:
                quantity_unit = POSITION_QUANTITY_UNIT

            quantity_source = risk_row.get(
                "quantity_source"
            )

            if quantity_source is None:
                quantity_source = POSITION_QUANTITY_SOURCE

            if quantity_unit != POSITION_QUANTITY_UNIT:
                fail(
                    f"Risk quantity unit invalid: {asset}"
                )

            if quantity_source != POSITION_QUANTITY_SOURCE:
                fail(
                    f"Risk quantity source invalid: {asset}"
                )

            for flag in (
                "quantity_changed",
                "quantity_recomputed",
                "quantity_rescaled",
                "quantity_rounded",
                "quantity_clipped",
            ):
                if risk_row.get(flag, False) is not False:
                    fail(
                        "Risk quantity transformation detected: "
                        f"{asset}.{flag}"
                    )

            _cp27c_candles = getattr(
                market_data_result,
                "candles",
                None,
            )

            if not _cp27c_candles:
                fail(
                    f"CP27-C REAL CANDLES MISSING: {asset}"
                )

            _cp27c_atr14 = market_data_engine.calculate_real_atr14(
                _cp27c_candles
            )

            if _cp27c_atr14 is None:
                fail(
                    f"CP27-C ATR14 UNAVAILABLE: {asset}"
                )

            _cp27c_stop_distance = (
                market_data_engine.calculate_runtime_stop_distance(
                    _cp27c_atr14
                )
            )

            if _cp27c_stop_distance is None:
                fail(
                    f"CP27-C STOP_DISTANCE UNAVAILABLE: {asset}"
                )

            risk_row["position_quantity"] = position_size
            risk_row["quantity_unit"] = POSITION_QUANTITY_UNIT
            risk_row["quantity_source"] = POSITION_QUANTITY_SOURCE

            risk_row["quantity_changed"] = False
            risk_row["quantity_recomputed"] = False
            risk_row["quantity_rescaled"] = False
            risk_row["quantity_rounded"] = False
            risk_row["quantity_clipped"] = False

            records[asset] = {
                "snapshot_id": snapshot_id,
                "asset": asset,
                "timeframe": "1h",
                "source": runtime["source"],
                "latest_ohlcv_timestamp": (
                    runtime["latest_ohlcv_timestamp"]
                ),
                "real_candle_count": (
                    runtime["real_candle_count"]
                ),
                "atr14": _cp27c_atr14,
                "stop_distance": _cp27c_stop_distance,
                "risk_budget": risk_budget,
                "entry_price": entry_price,
                "position_size": position_size,
                "risk_position_quantity": position_size,
                "order_intent_quantity": None,
                "canonical_order_request_quantity": None,
                "quantity_unit": POSITION_QUANTITY_UNIT,
                "quantity_source": POSITION_QUANTITY_SOURCE,
                "quantity_changed": False,
                "quantity_recomputed": False,
                "quantity_rescaled": False,
                "quantity_rounded": False,
                "quantity_clipped": False,
            }

        return records


    # ============================================================================
    # QUANTITY OBSERVABILITY VALIDATION
    # ============================================================================

def validate_runtime_quantity_records(
        quantity_records: dict,
        snapshot_id: str,
    ) -> None:
        if not isinstance(
            quantity_records,
            dict,
        ):
            fail(
                "Quantity records must be dict"
            )

        if (
            not isinstance(snapshot_id, str)
            or not snapshot_id
        ):
            fail(
                "Quantity observability snapshot_id missing"
            )

        for asset_key, record in quantity_records.items():
            asset = normalize_asset(asset_key)

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"Unexpected quantity asset: {asset}"
                )

            if not isinstance(
                record,
                dict,
            ):
                fail(
                    f"Quantity record must be dict: {asset}"
                )

            if record.get("snapshot_id") != snapshot_id:
                fail(
                    f"Quantity snapshot mismatch: {asset}"
                )

            if record.get("asset") != asset:
                fail(
                    f"Quantity asset mismatch: {asset}"
                )

            if record.get("timeframe") != TIMEFRAME:
                fail(
                    f"Quantity timeframe invalid: {asset}"
                )

            if not record.get("source"):
                fail(
                    f"Quantity source missing: {asset}"
                )

            if not record.get("latest_ohlcv_timestamp"):
                fail(
                    "Quantity latest OHLCV timestamp missing: "
                    f"{asset}"
                )

            candle_count = record.get(
                "real_candle_count"
            )

            if (
                not isinstance(candle_count, int)
                or isinstance(candle_count, bool)
                or candle_count < 1
            ):
                fail(
                    f"Quantity candle count invalid: {asset}"
                )

            required_runtime_values = (
                "atr14",
                "stop_distance",
                "risk_budget",
                "entry_price",
                "position_size",
                "risk_position_quantity",
                "order_intent_quantity",
                "canonical_order_request_quantity",
            )

            for field in required_runtime_values:
                if record.get(field) is None:
                    fail(
                        "Quantity observability runtime value "
                        f"missing: {asset}.{field}"
                    )

            for field in required_runtime_values:
                if not is_finite_number(
                    record.get(field)
                ):
                    fail(
                        "Quantity runtime value invalid: "
                        f"{asset}.{field}"
                    )

            if (
                record.get("position_size")
                != record.get("risk_position_quantity")
            ):
                fail(
                    f"Quantity Position/Risk mismatch: {asset}"
                )

            if (
                record.get("risk_position_quantity")
                != record.get("order_intent_quantity")
            ):
                fail(
                    f"Quantity Risk/OrderIntent mismatch: {asset}"
                )

            if (
                record.get("order_intent_quantity")
                != record.get(
                    "canonical_order_request_quantity"
                )
            ):
                fail(
                    f"Quantity OrderIntent/Canonical mismatch: {asset}"
                )

            if record.get("quantity_unit") != POSITION_QUANTITY_UNIT:
                fail(
                    f"Quantity unit invalid: {asset}"
                )

            if record.get("quantity_source") != POSITION_QUANTITY_SOURCE:
                fail(
                    f"Quantity source invalid: {asset}"
                )

            for flag in (
                "quantity_changed",
                "quantity_recomputed",
                "quantity_rescaled",
                "quantity_rounded",
                "quantity_clipped",
            ):
                if record.get(flag) is not False:
                    fail(
                        "Quantity transformation detected: "
                        f"{asset}.{flag}"
                    )


    # ============================================================================
    # ORDER INTENT
    # ============================================================================

def build_current_order_intents(
        gate_results: list[dict],
        opportunity_rows: list[dict],
        snapshot_id: str,
        regime_snapshot: dict,
        risk_snapshot: dict,
        observed_real_capital: float | int | None = None,
        research_quantity: float | int | None = None,
    ) -> list[dict]:
        gate_rows = exact_asset_rows(
            gate_results,
            "TRADE GATE",
        )

        opportunities = opportunity_map(
            {
                "opportunities": opportunity_rows,
            }
        )

        risk_rows = extract_rows(
            risk_snapshot,
            (
                "risk",
                "risk_decisions",
                "decisions",
                "rows",
                "assets",
                "results",
            ),
        )

        risk_rows = exact_asset_rows(
            risk_rows,
            "RISK",
        )

        r_map = risk_map(
            risk_rows
        )

        if observed_real_capital is None:
            fail(
                "REAL_CAPITAL_OBSERVATION_REQUIRED_FOR_ORDER_INTENT"
            )

        trade_ready_rows = [
            row
            for row in gate_rows
            if normalize_status(
                row.get("trade_gate_status")
            ) == TRADE_READY_STATUS
        ]

        if not trade_ready_rows:
            return []

        intents = []

        for gate_row in trade_ready_rows:
            asset = normalize_asset(
                gate_row.get(
                    "asset",
                    gate_row.get("symbol"),
                )
            )

            if asset is None:
                fail(
                    "TRADE_READY row has no asset"
                )

            opportunity = opportunities.get(asset)

            if not isinstance(
                opportunity,
                dict,
            ):
                fail(
                    f"Opportunity missing: {asset}"
                )

            if get_opportunity_status(
                opportunity
            ) != ELIGIBLE_STATUS:
                fail(
                    "ORDER-INTENT Opportunity not ELIGIBLE: "
                    f"{asset}"
                )

            direction = normalize_status(
                gate_row.get("direction")
            )

            if direction not in VALID_DIRECTIONS:
                fail(
                    f"TRADE_READY direction invalid: {asset}"
                )

            risk_row = r_map.get(asset)

            if not isinstance(
                risk_row,
                dict,
            ):
                fail(
                    f"Risk provenance missing: {asset}"
                )

            risk_status = normalize_status(
                get_row_value(
                    risk_row,
                    "risk_status",
                    "status",
                    "decision",
                    "risk_state",
                )
            )

            if risk_status not in APPROVED_RISK_STATUSES:
                fail(
                    "ORDER-INTENT risk status not approved: "
                    f"{asset} -> {risk_status}"
                )

            quantity = risk_row.get(
                "position_quantity"
            )

            if quantity is None:
                fail(
                    f"Risk.position_quantity missing: {asset}"
                )

            if not is_finite_number(quantity):
                fail(
                    f"Risk.position_quantity invalid: {asset}"
                )

            if float(quantity) < 0:
                fail(
                    f"Risk.position_quantity < 0: {asset}"
                )

            if risk_row.get(
                "quantity_unit",
                POSITION_QUANTITY_UNIT,
            ) != POSITION_QUANTITY_UNIT:
                fail(
                    f"Risk quantity unit invalid: {asset}"
                )

            if risk_row.get(
                "quantity_source",
                POSITION_QUANTITY_SOURCE,
            ) != POSITION_QUANTITY_SOURCE:
                fail(
                    f"Risk quantity source invalid: {asset}"
                )

            for flag in (
                "quantity_changed",
                "quantity_recomputed",
                "quantity_rescaled",
                "quantity_rounded",
                "quantity_clipped",
            ):
                if risk_row.get(flag, False) is not False:
                    fail(
                        "Risk quantity transformation flag: "
                        f"{asset}.{flag}"
                    )

            regime = get_current_regime(
                regime_snapshot,
                asset,
            )

            if regime is None:
                fail(
                    f"CURRENT_MARKET_REGIME missing: {asset}"
                )

            entry_price = opportunity.get("price")
            confidence = opportunity.get("confidence")
            timestamp = opportunity.get("timestamp")

            if entry_price is None:
                fail(
                    f"Opportunity entry_price missing: {asset}"
                )

            if confidence is None:
                fail(
                    f"Opportunity confidence missing: {asset}"
                )

            if timestamp is None:
                fail(
                    f"Opportunity timestamp missing: {asset}"
                )

            if not is_finite_number(entry_price):
                fail(
                    f"Opportunity entry_price invalid: {asset}"
                )

            if not is_finite_number(confidence):
                fail(
                    f"Opportunity confidence invalid: {asset}"
                )

            intent_id = f"OI-{snapshot_id}-{asset}"

            resolved_quantity = resolve_trade_quantity(
                observed_real_capital=observed_real_capital,
                risk_position_quantity=quantity,
                research_quantity=research_quantity,
            )

            intent = RuntimeOrderIntent(
                quantity=resolved_quantity["quantity"],
                quantity_unit=resolved_quantity["quantity_unit"],
                quantity_source=resolved_quantity["quantity_source"],
                asset=asset,
                direction=direction,
                entry_price=entry_price,
                confidence=confidence,
                regime=regime,
                timestamp=timestamp,
                snapshot_id=snapshot_id,
                intent_id=intent_id,
            )

            intent.trade_type = resolved_quantity["trade_type"]
            intent.observed_real_capital = (
                resolved_quantity["observed_real_capital"]
            )
            intent.research_quantity = (
                research_quantity
                if resolved_quantity["trade_type"] == RESEARCH_TRADE
                else None
            )

            if set(intent.keys()) != set(
                CURRENT_ORDER_INTENT_REQUIRED_FIELDS
            ):
                fail(
                    "ORDER_INTENT exact field contract failed: "
                    f"{asset}"
                )

            forbidden = (
                set(intent.keys())
                & set(CURRENT_ORDER_INTENT_FORBIDDEN_FIELDS)
            )

            if forbidden:
                fail(
                    f"Forbidden ORDER_INTENT fields: {forbidden}"
                )

            intents.append(intent)

        return intents


def validate_current_order_intents(
        intents: list[dict],
        gate_results: list[dict],
        opportunity_rows: list[dict],
        snapshot_id: str,
        regime_snapshot: dict,
        decision_rows: list[dict] | None = None,
        risk_rows: list[dict] | None = None,
    ) -> int:
        gate_rows = exact_asset_rows(
            gate_results,
            "TRADE GATE",
        )

        opportunities = opportunity_map(
            {
                "opportunities": opportunity_rows,
            }
        )

        trade_ready_rows = [
            row
            for row in gate_rows
            if normalize_status(
                row.get("trade_gate_status")
            ) == TRADE_READY_STATUS
        ]

        if not trade_ready_rows:
            if intents:
                fail(
                    "FAIL-CLOSED: ORDER_INTENT exists "
                    "without TRADE_READY"
                )

            return 0

        if len(intents) != len(trade_ready_rows):
            fail(
                "ORDER_INTENT coverage mismatch"
            )

        gate_map = {}

        for row in trade_ready_rows:
            asset = normalize_asset(
                row.get(
                    "asset",
                    row.get("symbol"),
                )
            )

            if asset in gate_map:
                fail(
                    f"Duplicate TRADE_READY asset: {asset}"
                )

            gate_map[asset] = row

        d_map = None
        r_map = None

        if decision_rows is not None:
            d_map = decision_map(
                exact_asset_rows(
                    decision_rows,
                    "DECISION",
                )
            )

        if risk_rows is not None:
            r_map = risk_map(
                exact_asset_rows(
                    risk_rows,
                    "RISK",
                )
            )

        seen = set()

        for intent in intents:
            if not isinstance(
                intent,
                dict,
            ):
                fail(
                    "ORDER_INTENT must be dict"
                )

            if set(intent.keys()) != set(
                CURRENT_ORDER_INTENT_REQUIRED_FIELDS
            ):
                fail(
                    "ORDER_INTENT exact field mismatch"
                )

            asset = normalize_asset(
                intent.get("asset")
            )

            if asset is None:
                fail(
                    "ORDER_INTENT asset missing"
                )

            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"ORDER_INTENT unexpected asset: {asset}"
                )

            direction = normalize_status(
                intent.get("direction")
            )

            if direction not in VALID_DIRECTIONS:
                fail(
                    f"ORDER_INTENT direction invalid: {asset}"
                )

            if asset in seen:
                fail(
                    f"Duplicate ORDER_INTENT asset: {asset}"
                )

            seen.add(asset)

            gate_row = gate_map.get(asset)

            if gate_row is None:
                fail(
                    f"ORDER_INTENT lacks Gate provenance: {asset}"
                )

            gate_direction = normalize_status(
                gate_row.get("direction")
            )

            if direction != gate_direction:
                fail(
                    "ORDER_INTENT direction provenance mismatch: "
                    f"{asset}"
                )

            opportunity = opportunities.get(asset)

            if opportunity is None:
                fail(
                    f"ORDER_INTENT opportunity missing: {asset}"
                )

            if get_opportunity_status(
                opportunity
            ) != ELIGIBLE_STATUS:
                fail(
                    f"ORDER_INTENT opportunity not ELIGIBLE: {asset}"
                )

            if intent["entry_price"] != opportunity.get("price"):
                fail(
                    f"ORDER_INTENT entry_price mismatch: {asset}"
                )

            if intent["confidence"] != opportunity.get("confidence"):
                fail(
                    f"ORDER_INTENT confidence mismatch: {asset}"
                )

            if intent["timestamp"] != opportunity.get("timestamp"):
                fail(
                    f"ORDER_INTENT timestamp mismatch: {asset}"
                )

            if intent["regime"] != get_current_regime(
                regime_snapshot,
                asset,
            ):
                fail(
                    f"ORDER_INTENT regime mismatch: {asset}"
                )

            if intent["snapshot_id"] != snapshot_id:
                fail(
                    f"ORDER_INTENT snapshot mismatch: {asset}"
                )

            expected_id = f"OI-{snapshot_id}-{asset}"

            if intent["intent_id"] != expected_id:
                fail(
                    "ORDER_INTENT deterministic ID mismatch: "
                    f"{asset}"
                )

            if d_map is not None:
                decision_row = d_map.get(asset)

                if decision_row is None:
                    fail(
                        f"Decision provenance missing: {asset}"
                    )

                decision_state = normalize_status(
                    get_row_value(
                        decision_row,
                        "decision",
                        "decision_state",
                        "state",
                    )
                )

                if decision_state not in ACTIONABLE_DECISIONS:
                    fail(
                        "Decision provenance not actionable: "
                        f"{asset} -> {decision_state}"
                    )

            if r_map is not None:
                risk_row = r_map.get(asset)

                if risk_row is None:
                    fail(
                        f"Risk provenance missing: {asset}"
                    )

                risk_status = normalize_status(
                    get_row_value(
                        risk_row,
                        "risk_status",
                        "status",
                        "decision",
                        "risk_state",
                    )
                )

                if risk_status not in APPROVED_RISK_STATUSES:
                    fail(
                        "Risk provenance not approved: "
                        f"{asset} -> {risk_status}"
                    )

                risk_quantity = risk_row.get(
                    "position_quantity"
                )

                if risk_quantity is None:
                    fail(
                        f"Risk quantity missing: {asset}"
                    )

                if getattr(
                    intent,
                    "trade_type",
                    None,
                ) == RESEARCH_TRADE:
                    if float(risk_quantity) != 0.0:
                        fail(
                            "RESEARCH_TRADE requires zero Risk.position_quantity: "
                            f"{asset}"
                        )
                    if float(
                        getattr(intent, "observed_real_capital", -1.0)
                    ) != 0.0:
                        fail(
                            "RESEARCH_TRADE requires zero observed real capital: "
                            f"{asset}"
                        )
                elif risk_quantity != getattr(
                    intent,
                    "quantity",
                    None,
                ):
                    fail(
                        "ORDER_INTENT quantity provenance mismatch: "
                        f"{asset}"
                    )

        if seen != set(gate_map.keys()):
            fail(
                "ORDER_INTENT final coverage mismatch"
            )

        return len(intents)


    # ============================================================================
    # CANONICAL ORDER REQUEST
    # ============================================================================

def build_canonical_order_requests(
        order_intents: list[dict],
        risk_snapshot: dict,
        snapshot_id: str,
    ) -> dict[str, dict]:
        risk_rows = extract_rows(
            risk_snapshot,
            (
                "risk",
                "risk_decisions",
                "decisions",
                "rows",
                "assets",
                "results",
            ),
        )

        risk_rows = exact_asset_rows(
            risk_rows,
            "RISK",
        )

        r_map = risk_map(
            risk_rows
        )

        result = {}

        for intent in order_intents:
            asset = normalize_asset(
                intent.get("asset")
            )

            if asset is None:
                fail(
                    "Canonical request asset missing"
                )

            if asset in result:
                fail(
                    f"Duplicate Canonical request asset: {asset}"
                )

            risk_row = r_map.get(asset)

            if risk_row is None:
                fail(
                    f"Canonical request Risk missing: {asset}"
                )

            risk_status = normalize_status(
                get_row_value(
                    risk_row,
                    "risk_status",
                    "status",
                    "decision",
                    "risk_state",
                )
            )

            if risk_status not in APPROVED_RISK_STATUSES:
                fail(
                    "Canonical request risk status not approved: "
                    f"{asset} -> {risk_status}"
                )

            quantity = risk_row.get(
                "position_quantity"
            )

            if (
                getattr(intent, "trade_type", None) == RESEARCH_TRADE
            ):
                if float(quantity) != 0.0:
                    fail(
                        f"RESEARCH_TRADE requires zero Risk.position_quantity: {asset}"
                    )
            elif quantity != getattr(
                intent,
                "quantity",
                None,
            ):
                fail(
                    f"Canonical quantity mismatch: {asset}"
                )

            if risk_row.get(
                "quantity_unit",
                POSITION_QUANTITY_UNIT,
            ) != POSITION_QUANTITY_UNIT:
                fail(
                    f"Canonical source quantity unit invalid: "
                    f"{asset}"
                )

            if risk_row.get(
                "quantity_source",
                POSITION_QUANTITY_SOURCE,
            ) != POSITION_QUANTITY_SOURCE:
                fail(
                    "Canonical source quantity provenance invalid: "
                    f"{asset}"
                )

            request_risk = dict(risk_row)

            if getattr(
                intent,
                "trade_type",
                None,
            ) == RESEARCH_TRADE:
                request_risk["position_quantity"] = intent.quantity
                request_risk["quantity_source"] = (
                    "RESEARCH_PREDEFINED"
                )

            request = (
                exchange_execution_contract.build_order_request(
                    asset=asset,
                    direction=intent["direction"],
                    order_type="MARKET",
                    risk=request_risk,
                    entry_price=intent["entry_price"],
                    reference_price=None,
                    intent_id=intent["intent_id"],
                    snapshot_id=snapshot_id,
                    timestamp=intent["timestamp"],
                )
            )

            if not isinstance(
                request,
                exchange_execution_contract.CanonicalOrderRequest,
            ):
                fail(
                    "CanonicalOrderRequest type invalid: "
                    f"{asset}"
                )

            exchange_execution_contract.validate_order_request(
                request
            )

            expected_request_quantity = (
                intent.quantity
                if getattr(intent, "trade_type", None) == RESEARCH_TRADE
                else quantity
            )

            if request.quantity != expected_request_quantity:
                fail(
                    f"Canonical quantity mismatch: {asset}"
                )

            if request.quantity_unit != CANONICAL_QUANTITY_UNIT:
                fail(
                    f"Canonical quantity unit invalid: {asset}"
                )

            expected_quantity_source = (
                "RESEARCH_PREDEFINED"
                if getattr(intent, "trade_type", None) == RESEARCH_TRADE
                else CANONICAL_QUANTITY_SOURCE
            )

            if request.quantity_source != expected_quantity_source:
                fail(
                    f"Canonical quantity source invalid: {asset}"
                )

            if request.snapshot_id != snapshot_id:
                fail(
                    f"Canonical snapshot mismatch: {asset}"
                )

            if request.intent_id != intent["intent_id"]:
                fail(
                    f"Canonical intent_id mismatch: {asset}"
                )

            result[asset] = {
                "request": request,
                "quantity": request.quantity,
                "quantity_unit": request.quantity_unit,
                "quantity_source": request.quantity_source,
            }

        return result


    # ============================================================================
    # QUANTITY OBSERVABILITY
    # ============================================================================

def bind_order_intent_quantity_observability(
        order_intents: list[dict],
        quantity_records: dict,
        canonical_order_requests: dict,
    ) -> None:
        if not isinstance(
            order_intents,
            list,
        ):
            fail(
                "Quantity observability order_intents must be list"
            )

        if not isinstance(
            quantity_records,
            dict,
        ):
            fail(
                "Quantity observability records must be dict"
            )

        if not isinstance(
            canonical_order_requests,
            dict,
        ):
            fail(
                "Quantity observability canonical requests "
                "must be dict"
            )

        for intent in order_intents:
            if not isinstance(
                intent,
                RuntimeOrderIntent,
            ):
                fail(
                    "Quantity observability requires "
                    "RuntimeOrderIntent"
                )

            asset = normalize_asset(
                intent.get("asset")
            )

            record = quantity_records.get(asset)

            if not isinstance(
                record,
                dict,
            ):
                fail(
                    "Quantity observability record missing: "
                    f"{asset}"
                )

            canonical = canonical_order_requests.get(asset)

            if not isinstance(
                canonical,
                dict,
            ):
                fail(
                    f"Canonical request missing: {asset}"
                )

            request = canonical.get("request")

            if not isinstance(
                request,
                exchange_execution_contract.CanonicalOrderRequest,
            ):
                fail(
                    f"Canonical request object missing: {asset}"
                )

            risk_quantity = record.get(
                "risk_position_quantity"
            )

            if risk_quantity is None:
                fail(
                    f"Risk.position_quantity missing: {asset}"
                )

            quantity = intent.quantity

            if getattr(
                intent,
                "trade_type",
                None,
            ) == RESEARCH_TRADE:
                if float(risk_quantity) != 0.0:
                    fail(
                        f"RESEARCH_TRADE Risk quantity must be zero: {asset}"
                    )
                if request.quantity != quantity:
                    fail(
                        f"Research quantity OrderIntent/Canonical mismatch: {asset}"
                    )
                if request.quantity_source != "RESEARCH_PREDEFINED":
                    fail(
                        f"Research quantity provenance invalid: {asset}"
                    )
            else:
                if quantity != risk_quantity:
                    fail(
                        f"Quantity Risk/OrderIntent mismatch: {asset}"
                    )
                if quantity != request.quantity:
                    fail(
                        f"Quantity OrderIntent/Canonical mismatch: {asset}"
                    )
                if intent.quantity_source != POSITION_QUANTITY_SOURCE:
                    fail(
                        f"OrderIntent quantity source invalid: {asset}"
                    )

            if intent.quantity_unit != POSITION_QUANTITY_UNIT:
                fail(
                    f"OrderIntent quantity unit invalid: {asset}"
                )

            for flag in (
                "quantity_changed",
                "quantity_recomputed",
                "quantity_rescaled",
                "quantity_rounded",
                "quantity_clipped",
            ):
                if getattr(intent, flag) is not False:
                    fail(
                        "OrderIntent quantity transformation: "
                        f"{asset}.{flag}"
                    )

            record["order_intent_quantity"] = quantity
            record["canonical_order_request_quantity"] = (
                request.quantity
            )

            record["quantity_changed"] = False
            record["quantity_recomputed"] = False
            record["quantity_rescaled"] = False
            record["quantity_rounded"] = False
            record["quantity_clipped"] = False


    # ============================================================================
    # EXECUTION SAFETY
    # ============================================================================

def assert_execution_disabled() -> None:
        if EXECUTION_ENABLED:
            fail(
                "SAFETY VIOLATION: EXECUTION_ENABLED must remain False"
            )

        safety = (
            exchange_execution_contract.safety_contract()
        )

        if not isinstance(
            safety,
            dict,
        ):
            fail(
                "SAFETY CONTRACT must be dict"
            )

        for key, value in safety.items():
            if value is not False:
                fail(
                    f"SAFETY VIOLATION: {key} must be False"
                )


def verify_execution_boundary_integration(
        canonical_order_requests: dict,
    ) -> str:
        assert_execution_disabled()

        if not isinstance(
            canonical_order_requests,
            dict,
        ):
            fail(
                "Execution Boundary canonical requests "
                "must be dict"
            )

        if not canonical_order_requests:
            return "DEFERRED_NO_CANONICAL_REQUESTS"

        for asset, record in canonical_order_requests.items():
            if asset not in EXPECTED_ASSET_SET:
                fail(
                    f"Execution Boundary unexpected asset: {asset}"
                )

            if not isinstance(
                record,
                dict,
            ):
                fail(
                    f"Execution Boundary record invalid: {asset}"
                )

            request = record.get("request")

            if not isinstance(
                request,
                exchange_execution_contract.CanonicalOrderRequest,
            ):
                fail(
                    f"Canonical request missing: {asset}"
                )

            result = execute_order(
                request=request,
                adapter=None,
            )

            if not isinstance(
                result,
                exchange_execution_contract.CanonicalExecutionResult,
            ):
                fail(
                    f"Execution boundary result invalid: {asset}"
                )

            if result.error_code != "CP46_E_REQUIRED":
                fail(
                    "EXECUTION SAFETY FAILURE: "
                    f"{asset} returned "
                    f"{result.error_code!r}"
                )

        return "VERIFIED_BLOCKED"


def assert_no_execution_boundary(
        order_intents: list[dict],
    ) -> None:
        assert_execution_disabled()

        if order_intents and EXECUTION_ENABLED:
            fail(
                "ORDER_INTENT cannot reach execution"
            )


    # ============================================================================
    # FINAL PREFLIGHT
    # ============================================================================

def validate_final_preflight_integrity(
        opportunity_rows: list[dict],
        gate_results: list[dict],
        order_intents: list[dict],
        validated_order_intents: int,
    ) -> tuple[int, int]:
        trade_ready_count = sum(
            1
            for row in gate_results
            if normalize_status(
                row.get("trade_gate_status")
            ) == TRADE_READY_STATUS
        )

        eligible_count = sum(
            1
            for row in opportunity_rows
            if get_opportunity_status(row) == ELIGIBLE_STATUS
        )

        if trade_ready_count == 0:
            if order_intents:
                fail(
                    "TRADE_READY=0 but ORDER_INTENT>0"
                )

            if validated_order_intents != 0:
                fail(
                    "TRADE_READY=0 but "
                    "VALIDATED_ORDER_INTENTS>0"
                )

        else:
            if len(order_intents) != trade_ready_count:
                fail(
                    "ORDER_INTENT count != TRADE_READY count"
                )

            if validated_order_intents != len(order_intents):
                fail(
                    "Validated ORDER_INTENT count mismatch"
                )

            if eligible_count < trade_ready_count:
                fail(
                    "TRADE_READY exceeds ELIGIBLE coverage"
                )

        return (
            trade_ready_count,
            eligible_count,
        )


    # ============================================================================
    # REPORT
    # ============================================================================

def print_final_report(
        snapshot_id,
        opportunity_rows,
        decision_rows,
        risk_rows,
        gate_results,
        order_intents,
        validated_order_intents,
        quantity_records,
        execution_boundary_status,
    ):
        trade_ready = [
            row
            for row in gate_results
            if normalize_status(
                row.get("trade_gate_status")
            ) == TRADE_READY_STATUS
        ]

        eligible = sum(
            1
            for row in opportunity_rows
            if get_opportunity_status(row) == ELIGIBLE_STATUS
        )

        print()
        print("=" * 90)
        print(
            "ARUNDA TRADER ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â "
            "PRODUCTION PIPELINE v1.0"
        )
        print(
            "FUSED-SCORE ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ SCORE / DECISION ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ "
            "RISK ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ TRADE GATE ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ ORDER INTENT"
        )
        print("=" * 90)

        print()
        print("PRODUCTION:")
        print("MARKET ARM      : VERIFIED")
        print("NEWS ARM        : PASS")
        print("SOCIAL ARM      : PASS")
        print("FUSION          : FUSION_v0.6")
        print(
            "SCORE BINDING   : "
            "FUSED_SCORE_BINDING_v0.1"
        )
        print("LEGACY          : FORBIDDEN")

        print()
        print("COVERAGE:")
        print(
            f"OPPORTUNITY     : "
            f"{len(opportunity_rows)}/{len(EXPECTED_ASSETS)}"
        )
        print(
            f"DECISION        : "
            f"{len(decision_rows)}/{len(EXPECTED_ASSETS)}"
        )
        print(
            f"RISK            : "
            f"{len(risk_rows)}/{len(EXPECTED_ASSETS)}"
        )
        print(
            f"TRADE GATE      : "
            f"{len(gate_results)}/{len(EXPECTED_ASSETS)}"
        )

        print()
        print("OPPORTUNITY:")
        print(
            f"ELIGIBLE        : {eligible}"
        )
        print(
            f"TRADE_READY     : {len(trade_ready)}"
        )
        print(
            f"ORDER_INTENT    : {len(order_intents)}"
        )
        print(
            f"VALIDATED_OI    : {validated_order_intents}"
        )

        print()
        print("QUANTITY:")
        print(
            f"RUNTIME_RECORDS : {len(quantity_records)}"
        )
        print(
            "SOURCE          : "
            "POSITION_SIZING.position_size"
        )
        print(
            "RISK QUANTITY   : "
            "RISK.position_quantity"
        )
        print(
            "CANONICAL       : "
            "RISK.position_quantity"
        )
        print(
            "UNIT            : BASE_ASSET"
        )
        print("CHANGED         : FALSE")
        print("RECOMPUTED      : FALSE")
        print("RESCALED        : FALSE")
        print("ROUNDED         : FALSE")
        print("CLIPPED         : FALSE")

        print()
        print("EXECUTION:")
        print(
            f"ENABLED         : "
            f"{EXECUTION_ENABLED}"
        )
        print(
            "ORDER SUBMISSION: NONE"
        )
        print(
            "EXCHANGE WRITE  : NONE"
        )
        print(
            f"BOUNDARY        : "
            f"{execution_boundary_status}"
        )

        print()
        print("DATABASE:")
        print(
            "ORDER_INTENT DB : NONE"
        )
        print(
            "EXECUTION DB    : NONE"
        )
        print(
            "DB_WRITES       : 0"
        )

        print()
        print("DATA SAFETY:")
        print("SYNTHETIC       : FALSE")
        print("INTERPOLATION   : FALSE")
        print("FILL            : FALSE")
        print("BACKFILL        : FALSE")
        print("PADDING         : FALSE")
        print("BLENDING        : FALSE")
        print("LEGACY_USED     : FALSE")

        print()
        print("RUNTIME IDENTITY:")
        print(
            f"SNAPSHOT_ID     : {snapshot_id}"
        )
        print(
            f"LAUNCH_BOUNDARY : "
            f"{LAUNCH_TIMESTAMP}"
        )
        print("DETERMINISTIC   : YES")
        print("REPRODUCIBLE    : YES")
        print("AUDITABLE       : YES")

        print()
        print("CLOSED LAYERS:")
        print("REOPENED        : NONE")

        if not trade_ready:
            print()
            print(
                "RESULT          : PASS ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â "
                "FAIL-CLOSED ZERO PATH"
            )
            print(
                "REASON          : "
                "NO CURRENT TRADE_READY / "
                "NO ORDER_INTENT"
            )
        else:
            print()
            print(
                "RESULT          : PASS ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â "
                "CURRENT ORDER-INTENT "
                "CONTRACT VERIFIED"
            )

        print()
        print(
            "EXECUTION REMAINS DISABLED"
        )

        print("=" * 90)


    # ============================================================================
    # MAIN
    # ============================================================================

def main() -> int:
    """
    PRODUCTION FULL DYNAMIC UNIVERSE ORCHESTRATOR

    Production path:
        REAL UNIVERSE
        -> REAL MARKET DATA
        -> OPPORTUNITY
        -> PRODUCTION SIGNAL INPUT
        -> DYNAMIC SIGNAL
        -> DYNAMIC VALIDATION
        -> NEWS
        -> SOCIAL
        -> DYNAMIC FUSION
        -> DYNAMIC SCORE
        -> DYNAMIC DECISION
        -> DYNAMIC RISK
        -> DYNAMIC TRADE GATE

    This boundary intentionally bypasses all legacy fixed-15 snapshot
    orchestration helpers. Those helpers remain available only for
    historical/test compatibility and are not part of this Production path.

    Execution, real orders, real trades and DB writes remain forbidden.
    """

    assert_execution_disabled()

    try:
        # --------------------------------------------------------------
        # CP44 REAL READ-ONLY PORTFOLIO PRODUCER
        # --------------------------------------------------------------
        # This is the final read-only provider boundary.
        # No order, execution, exchange write, or DB write is performed.
        from toobit_trading_adapter import ToobitTradingAdapter
        from account_balance_observation_v0_1 import (
            build_account_balance_observation,
        )
        from toobit_position_reader_v0_1 import (
            build_toobit_position_reader,
        )
        from portfolio_observation_v0_1 import (
            build_portfolio_observation,
        )

        cp44_adapter = ToobitTradingAdapter()

        cp44_connectivity = (
            cp44_adapter.capabilities()
        )

        if cp44_connectivity.get("ACCOUNT_READ") is not True:
            fail("CP44 ACCOUNT_READ capability unavailable")

        if cp44_connectivity.get("BALANCE_READ") is not True:
            fail("CP44 BALANCE_READ capability unavailable")

        cp44_account_balance_observation = (
            build_account_balance_observation(
                cp44_adapter,
            )
        )

        cp44_position_reader = build_toobit_position_reader(
            cp44_adapter,
        )

        cp44_portfolio_observation = build_portfolio_observation(
            cp44_account_balance_observation,
            position_reader=cp44_position_reader,
        )

        # Explicitly expose the real observations to the CP44
        # composition boundary below. No synthetic values are created.
        cp44_account_balance_observation = (
            cp44_account_balance_observation
        )
        cp44_portfolio_observation = (
            cp44_portfolio_observation
        )

        print("=" * 90)
        print("ARUNDA TRADER ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â FULL REAL DYNAMIC UNIVERSE PIPELINE")
        print("EXECUTION=OFF | REAL_ORDER=FALSE | REAL_TRADE=FALSE | DB_WRITES=0")
        print("=" * 90)

        # ------------------------------------------------------------------
        # 1. REAL DYNAMIC PRODUCTION UNIVERSE
        # ------------------------------------------------------------------
        from production_universe_contract_v0_1 import (
            discover_production_assets,
        )

        universe = tuple(discover_production_assets())

        if not universe:
            fail("Production universe is empty")

        universe_assets = tuple(
            normalize_asset(symbol.split("/", 1)[0])
            for symbol in universe
            if isinstance(symbol, str) and "/" in symbol
        )

        if len(universe_assets) != len(universe):
            fail("Production universe contains invalid canonical symbol identity")

        if len(set(universe_assets)) != len(universe_assets):
            fail("Production universe contains duplicate assets")

        print(f"UNIVERSE_SIZE={len(universe_assets)}")

        # ------------------------------------------------------------------
        # 2. REAL MARKET DATA -> OPPORTUNITY
        # ------------------------------------------------------------------
        from dynamic_opportunity_universe_boundary_v0_1 import (
            build_dynamic_opportunities,
            ready_opportunities,
        )

        # ------------------------------------------------------------------
        # FAST DEBUG ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â REAL MARKETS ONLY
        # ------------------------------------------------------------------
        FAST_DEBUG = False
        FAST_DEBUG_COUNT = 3
        FAST_DEBUG_SCAN_COUNT = 10

        from dynamic_market_data_boundary_v0_1 import (
            fetch_universe_market_data,
        )

        if FAST_DEBUG:
            debug_candidates = tuple(
                universe[:FAST_DEBUG_SCAN_COUNT]
            )

            debug_market_data_results = (
                fetch_universe_market_data(
                    markets=debug_candidates
                )
            )

            ready_debug_results = tuple(
                result
                for result in debug_market_data_results
                if (
                    getattr(result, "status", None) == "READY"
                    and getattr(result, "real_data", False) is True
                )
            )

            if len(ready_debug_results) < FAST_DEBUG_COUNT:
                fail(
                    "FAST_DEBUG_INSUFFICIENT_READY_REAL_MARKETS: "
                    f"required={FAST_DEBUG_COUNT} "
                    f"available={len(ready_debug_results)} "
                    f"scanned={len(debug_candidates)}"
                )

            runtime_universe = tuple(
                result.symbol
                for result in ready_debug_results[
                    :FAST_DEBUG_COUNT
                ]
            )

            market_data_results = tuple(
                ready_debug_results[
                    :FAST_DEBUG_COUNT
                ]
            )

            print(
                f"FAST_DEBUG=ON | "
                f"REAL_MARKETS={len(runtime_universe)} | "
                f"SCANNED={len(debug_candidates)} | "
                f"PRODUCTION_UNIVERSE={len(universe)}"
            )

        else:
            runtime_universe = universe

            market_data_results = (
                fetch_universe_market_data(
                    markets=runtime_universe
                )
            )

        # ========================================================================
        market_data_by_symbol = {
            str(getattr(result, "symbol", "")).strip().upper(): result
            for result in market_data_results
        }

        if set(market_data_by_symbol) != {
            str(symbol).strip().upper()
            for symbol in runtime_universe
        }:
            fail(
                "MarketDataResult cardinality/identity mismatch"
            )

        opportunity_results = build_dynamic_opportunities(
            market_data_results
        )

        if len(opportunity_results) != len(runtime_universe):
            fail(
                "Dynamic Opportunity cardinality mismatch: "
                f"expected={len(runtime_universe)} "
                f"actual={len(opportunity_results)}"
            )

        ready_opportunity_results = ready_opportunities(opportunity_results)

        opportunity_by_asset = {}

        for result in opportunity_results:
            opportunity = getattr(result, "opportunity", None)

            if opportunity is None and isinstance(result, dict):
                opportunity = result.get("opportunity")

            if opportunity is None:
                continue

            opportunity = ensure_dict(opportunity, "opportunity")

            opportunity_identity = opportunity.get(
                "asset",
                opportunity.get("symbol")
            )

            if not isinstance(opportunity_identity, str):
                continue

            opportunity_identity = opportunity_identity.strip().upper()

            if opportunity_identity not in universe:
                fail(
                    "Opportunity returned asset outside Production Universe: "
                    f"{opportunity_identity}"
                )

            asset = normalize_asset(
                opportunity_identity.split("/", 1)[0]
            )

            if not asset:
                continue

            if asset in opportunity_by_asset:
                fail(f"Duplicate Opportunity asset: {asset}")

            opportunity_by_asset[asset] = opportunity

        print(
            f"OPPORTUNITY_READY={len(ready_opportunity_results)}"
        )

        # ------------------------------------------------------------------
        # 3. REAL PRODUCTION SIGNAL INPUT + DYNAMIC SIGNAL
        # ------------------------------------------------------------------
        import importlib.util

        signal_input_path = (
            PROJECT_DIR / "production_signal_input_boundary_v0_1.py"
        )

        spec = importlib.util.spec_from_file_location(
            "arunda_production_signal_input_runtime",
            signal_input_path,
        )

        if spec is None or spec.loader is None:
            fail("Unable to load production_signal_input_boundary_v0_1")

        signal_input_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = signal_input_module
        spec.loader.exec_module(signal_input_module)

        import ccxt

        kucoin = ccxt.kucoin()
        kucoin.load_markets()

        import indicator_engine
        import market_structure_engine
        import feature_engine

        calculate_indicator_records = indicator_engine.calculate_indicator_records
        analyze_market_structure = market_structure_engine.analyze_market_structure
        calculate_feature_records = feature_engine.calculate_feature_records

        production_signal_inputs = {}
        dynamic_signals = {}

        universe_binding = importlib.util.spec_from_file_location(
            "arunda_production_universe_binding_runtime",
            PROJECT_DIR / "production_universe_binding.py",
        )

        if universe_binding is None or universe_binding.loader is None:
            fail("Unable to load production_universe_binding")

        universe_binding_module = importlib.util.module_from_spec(
            universe_binding
        )
        universe_binding.loader.exec_module(universe_binding_module)

        discover_universe = getattr(
            signal_input_module,
            "discover_production_universe",
            None,
        )

        if not callable(discover_universe):
            fail("Production universe discovery callable missing")

        discovered_records, eligible_records = discover_universe(
            universe_binding_module
        )

        eligible_by_symbol = {}

        for record in eligible_records:
            record_symbol = (
                getattr(record, "symbol", None)
                if not isinstance(record, dict)
                else record.get("symbol")
            )

            record_asset = (
                getattr(record, "asset", None)
                if not isinstance(record, dict)
                else record.get("asset")
            )

            if not isinstance(record_symbol, str):
                continue

            if not isinstance(record_asset, str):
                continue

            canonical_asset = normalize_asset(record_asset)
            canonical_symbol = record_symbol.strip().upper()

            if canonical_asset not in universe_assets:
                continue

            if canonical_symbol != f"{canonical_asset}/USDT":
                continue

            if canonical_asset in eligible_by_symbol:
                fail(
                    f"Duplicate eligible MarketRecord: {canonical_asset}"
                )

            eligible_by_symbol[canonical_asset] = record

        runtime_assets = {
            normalize_asset(symbol.split("/", 1)[0])
            for symbol in runtime_universe
        }

        if not runtime_assets.issubset(set(eligible_by_symbol)):
            fail(
                "Fast Debug MarketRecord cardinality mismatch: "
                f"expected={len(runtime_assets)} "
                f"actual={len(set(eligible_by_symbol) & runtime_assets)}"
            )

        for symbol in runtime_universe:
            asset = normalize_asset(symbol.split("/", 1)[0])

            if not asset:
                fail("Invalid asset in Production Universe")

            record = eligible_by_symbol.get(asset)

            if record is None:
                fail(
                    f"Missing authoritative MarketRecord: {asset}"
                )

            market_input = (
                signal_input_module.market_record_to_arm_input(record)
            )

            market_data_result = market_data_by_symbol.get(
                symbol.strip().upper()
            )

            if market_data_result is None:
                fail(
                    f"Missing Dynamic MarketDataResult: {symbol}"
                )

            if (
                getattr(market_data_result, "status", None) != "READY"
                or getattr(market_data_result, "real_data", False) is not True
            ):
                continue

            production_input = (
                signal_input_module.build_production_signal_input(
                    market_input,
                    market_data_result,
                    indicator_engine,
                    market_structure_engine,
                    feature_engine,
                )
            )

            if normalize_asset(production_input.asset) != asset:
                fail(
                    f"ProductionSignalInput identity mismatch: {asset}"
                )

            production_signal_inputs[asset] = production_input

            from dynamic_signal_semantic_layer import build_dynamic_signal

            direction = build_dynamic_signal(production_input)

            if direction not in {"LONG", "SHORT", "NONE"}:
                fail(
                    f"Invalid dynamic signal direction for {asset}: "
                    f"{direction}"
                )

            feature_record = production_input.feature_record
            feature_records = production_input.feature_records

            structure_state = {
                "direction": production_input.structure_direction,
                "strength": production_input.structure_strength,
                "confidence": production_input.structure_confidence,
                "point_type": production_input.structure_point_type,
            }

            dynamic_signals[asset] = {
                "asset": asset,
                "signal_state": (
                    "ACTIVE" if direction != "NONE" else "NEUTRAL"
                ),
                "direction": direction,
                "trend": production_input.trend,
                "momentum": production_input.momentum,
                "acceleration": production_input.acceleration,
                "position": production_input.position,
                "volatility": production_input.volatility,
                "feature_record": feature_record,
                "feature_records": feature_records,
                "structure_state": structure_state,
                "dynamic_universe": True,
                "variable_cardinality": True,
                "fixed_15_used": False,
            }

        if set(dynamic_signals) != set(production_signal_inputs):
            fail(
                "Dynamic Signal cardinality mismatch: "
                f"signals={len(dynamic_signals)} "
                f"production_inputs={len(production_signal_inputs)}"
            )

        print(f"SIGNAL_READY={len(dynamic_signals)}")

           # ------------------------------------------------------------------
        # 4. DYNAMIC SIGNAL VALIDATION
        # ------------------------------------------------------------------
        from dynamic_validation_boundary_v0_1 import (
            validate_dynamic_signal,
        )

        validation_results = {
            asset: validate_dynamic_signal(
                asset,
                dynamic_signals[asset],
            )
            for asset in production_signal_inputs
        }

        if set(validation_results) != set(production_signal_inputs):
            fail(
                "Dynamic Validation cardinality mismatch: "
                f"validation={len(validation_results)} "
                f"production_inputs={len(production_signal_inputs)}"
            )

        invalid_assets = [
            asset
            for asset, result in validation_results.items()
            if not result.get("valid", False)
        ]

        validated_signals = {
            asset: dynamic_signals[asset]
            for asset in production_signal_inputs
            if asset not in invalid_assets
        }

        print(f"VALIDATION_READY={len(validated_signals)}")
        print(f"VALIDATION_FAILED={len(invalid_assets)}")

        # ------------------------------------------------------------------
        # 5. REAL NEWS
        # ------------------------------------------------------------------
        from dynamic_news_boundary_v0_1 import run_dynamic_news

        news_result = run_dynamic_news(runtime_universe)

        if not isinstance(news_result, dict):
            fail("Dynamic News returned invalid result")

        news_items = news_result.get("items", [])
        if not isinstance(news_items, list):
            fail("Dynamic News items must be a list")

        # ------------------------------------------------------------------
        # 6. REAL SOCIAL
        # ------------------------------------------------------------------
        from dynamic_social_boundary_v0_1 import run_dynamic_social

        social_result = run_dynamic_social(runtime_universe)

        if not isinstance(social_result, dict):
            fail("Dynamic Social returned invalid result")

        social_items = social_result.get("items", [])
        if not isinstance(social_items, list):
            fail("Dynamic Social items must be a list")

        # ------------------------------------------------------------------
        # 7. DYNAMIC FUSION
        # ------------------------------------------------------------------
        from dynamic_fusion_boundary_v0_1 import (
            fuse_dynamic_asset,
        )

        market_signal_map = {
            asset: validated_signals[asset]
            for asset in validated_signals
        }

        fusion_snapshot = {}

        for asset in market_signal_map:
            fusion_snapshot[asset] = fuse_dynamic_asset(
                asset,
                market_signal_map[asset],
                news_items,
                social_items,
                runtime_universe,
            )

        if set(fusion_snapshot) != set(market_signal_map):
            fail("Fast Debug Dynamic Fusion cardinality mismatch")

        print(f"FUSION_READY={len(fusion_snapshot)}")

        # ------------------------------------------------------------------
        # CP44 LIVE INTELLIGENCE CONSUMPTION — CANDIDATE ONLY
        # ------------------------------------------------------------------
        from cp44_live_predictive_evidence_mapping_v0_1 import (
            build_live_predictive_evidence_mapping,
        )

        live_intelligence_observations = {}

        for asset in market_signal_map:
            opportunity = opportunity_by_asset.get(asset)
            production_input = production_signal_inputs.get(asset)

            if opportunity is None or production_input is None:
                continue

            observation = {
                "asset": f"{asset}/USDT",
                "direction": market_signal_map[asset]["direction"],
                "opportunity_score": opportunity.get(
                    "score",
                    opportunity.get("opportunity_score", 0.0),
                ),
                "momentum_1h": opportunity.get("momentum_1h", 0.0),
                "momentum_24h": opportunity.get("momentum_24h", 0.0),
                "rsi14": opportunity.get("rsi14", 0.0),
                "structure_direction": (
                    production_input.structure_direction
                ),
                "structure_strength": (
                    production_input.structure_strength
                ),
                "structure_confidence": (
                    production_input.structure_confidence
                ),
                "source": "CP44_LIVE_RUNTIME",
                "observed_at": opportunity.get(
                    "observed_at",
                    opportunity.get("timestamp"),
                ),
                "provenance": {
                    "runtime_asset": asset,
                    "source_layer": "REAL_MARKET_OPPORTUNITY",
                    "candidate_only": True,
                },
            }

            live_intelligence_observations[asset] = (
                build_live_predictive_evidence_mapping(
                    observation=observation
                )
            )

        if set(live_intelligence_observations).difference(
            set(market_signal_map)
        ):
            fail(
                "CP44 Live Intelligence identity mismatch"
            )

        print(
            "CP44_LIVE_INTELLIGENCE_CONSUMPTION="
            f"{len(live_intelligence_observations)}"
        )
        print("CP44_LIVE_INTELLIGENCE_FORMULA_FROZEN=FALSE")
        print("CP44_LIVE_INTELLIGENCE_DB_WRITES=0")
        print("CP44_LIVE_INTELLIGENCE_EXECUTION=OFF")


        # ------------------------------------------------------------------
        # 8. DYNAMIC SCORE
        # ------------------------------------------------------------------
        from dynamic_score_contract_boundary_v0_1 import (
            build_dynamic_score,
        )

        score_snapshot = {}

        for asset in market_signal_map:
            signal_record = market_signal_map[asset]
            direction = signal_record["direction"]

            feature_record = signal_record.get("feature_record")

            structural_state = signal_record.get(
                "structure_state",
                {},
            )

            regime_data = {
                "trend": signal_record.get("trend"),
                "momentum": signal_record.get("momentum"),
                "acceleration": signal_record.get("acceleration"),
                "position": signal_record.get("position"),
                "volatility": signal_record.get("volatility"),
            }

            score_snapshot[asset] = build_dynamic_score(
                f"{asset}/USDT",
                direction,
                signal_record.get("feature_records"),
                structural_state,
                regime_data,
            )

        if set(score_snapshot) != set(market_signal_map):
            fail("Dynamic Score cardinality mismatch")

        from cp49_production_decision_birth_producer_v0_1 import (
            require_production_decision_birth,
        )

        canonical_birth_events = {
            asset: {
                key: value
                for key, value in signal_record.items()
                if key in (
                    "decision_id",
                    "asset",
                    "decision_timestamp_ms",
                    "snapshot_id",
                    "source",
                )
            }
            for asset, signal_record in market_signal_map.items()
        }

        canonical_decision_ids = require_production_decision_birth(
            canonical_birth_events,
            expected_assets=set(market_signal_map),
        )

        # ------------------------------------------------------------------
        # 9. DYNAMIC DECISION
        # ------------------------------------------------------------------
        from dynamic_decision_contract_boundary_v0_1 import (
            build_dynamic_decision,
        )

        decision_snapshot = {}

        for asset in market_signal_map:
            validated_signal = dict(market_signal_map[asset])
            validation = validation_results[asset]
            validated_signal["valid"] = validation["valid"]
            validated_signal["validation"] = validation["validation"]
            canonical_decision_id = canonical_decision_ids.get(asset)
            if not isinstance(canonical_decision_id, str) or not canonical_decision_id.strip():
                fail(
                    f"CANONICAL_DECISION_ID_MISSING_AT_REAL_PRODUCER: {asset}"
                )

            decision_snapshot[asset] = build_dynamic_decision(
                f"{asset}/USDT",
                validated_signal,
                score_snapshot[asset],
                decision_id=canonical_decision_id.strip(),
            )
        # ------------------------------------------------------------------
        # 10. CP44 REAL PORTFOLIO COMPOSITION
        # ------------------------------------------------------------------
        # Compose only from explicitly produced real account/portfolio
        # observations before Smart Risk is evaluated.
        # No capital/risk fallback and no synthetic values are permitted.

        from dataclasses import asdict
        from cp44_balance_semantic_boundary_v0_1 import (
            build_cp44_balance_semantics,
        )

        cp44_account_balance_mapping = asdict(
            cp44_account_balance_observation
        )
        cp44_portfolio_mapping = asdict(
            cp44_portfolio_observation
        )

        cp44_balances = tuple(
            cp44_account_balance_observation.balances
        )

        usdt_balance = None
        for balance in cp44_balances:
            if str(balance.asset).upper() == "USDT":
                usdt_balance = balance
                break

        cp44_balance_semantics = build_cp44_balance_semantics(
            usdt_balance,
            balance_observation_complete=(
                cp44_account_balance_observation.balance_observation_complete
            ),
            source=cp44_account_balance_observation.account.source_id,
            observed_at=(
                cp44_account_balance_observation.account.source_timestamp
            ),
            provenance={
                "source_type": (
                    cp44_account_balance_observation.account.source_type
                ),
                "account_observation": "REAL_ACCOUNT_BALANCE",
            },
        )

        if cp44_balance_semantics.validation != "VALID":
            fail(
                "CP44 BALANCE SEMANTIC CONTRACT BLOCKED: "
                + cp44_balance_semantics.reason
            )

        cp44_real_balance_mapping = (
            cp44_balance_semantics.as_mapping()
        )

        cp44_account_balance_mapping.update(
            {
                key: cp44_real_balance_mapping[key]
                for key in (
                    "portfolio_capital",
                    "usable_capital",
                    "source",
                    "observed_at",
                    "provenance",
                )
                if key in cp44_real_balance_mapping
            }
        )

        cp44_portfolio_mapping.update(
            {
                key: cp44_real_balance_mapping[key]
                for key in (
                    "portfolio_capital",
                    "usable_capital",
                )
                if key in cp44_real_balance_mapping
            }
        )

        cp44_positions = cp44_portfolio_observation.positions

        if cp44_positions is None:
            fail("CP44 REAL PORTFOLIO POSITIONS UNAVAILABLE")

        cp44_portfolio_mapping["concurrent_positions"] = len(
            tuple(cp44_positions)
        )

        cp44_real_risk_allocation_observation = None

        cp44_real_portfolio_composition = compose_real_portfolio_capital(
            cp44_account_balance_mapping,
            cp44_portfolio_mapping,
            cp44_real_risk_allocation_observation,
        )

        if cp44_real_portfolio_composition.state != "AVAILABLE":
            fail(
                "CP44 REAL PORTFOLIO COMPOSITION BLOCKED: "
                + ",".join(cp44_real_portfolio_composition.gaps)
            )

        cp44_real_capital_observation = (
            cp44_real_portfolio_composition.as_mapping()
        )

        # ------------------------------------------------------------------
        # 11. CP44 DYNAMIC SMART RISK
        # ------------------------------------------------------------------
        # Smart Risk receives the real composed capital/portfolio
        # observation explicitly. market_signal_map remains signal-only.

        from cp44_smart_risk_pipeline_boundary_v0_1 import (
            build_cp44_smart_risk,
        )

        risk_snapshot = {}

        for asset in decision_snapshot:
            smart_risk_observation = dict(
                market_signal_map.get(asset, {})
            )

            smart_risk_observation.update(
                {
                    key: value
                    for key, value in decision_snapshot[asset].items()
                    if key in (
                        "entry_price",
                        "invalidation_price",
                        "policy_version",
                        "policy_validation",
                        "risk_per_trade",
                        "max_portfolio_risk",
                        "max_concurrent_positions",
                        "source",
                        "observed_at",
                        "provenance",
                    )
                }
            )

            opportunity = opportunity_by_asset.get(asset)
            if isinstance(opportunity, dict):
                smart_risk_observation.update(
                    {
                        key: value
                        for key, value in opportunity.items()
                        if key in (
                            "entry_price",
                            "invalidation_price",
                            "policy_version",
                            "policy_validation",
                            "risk_per_trade",
                            "max_portfolio_risk",
                            "max_concurrent_positions",
                            "source",
                            "observed_at",
                            "provenance",
                        )
                    }
                )

            smart_risk_observation.update(
                {
                    key: cp44_real_capital_observation[key]
                    for key in (
                        "capital_state",
                        "portfolio_capital",
                        "usable_capital",
                        "allocated_risk",
                        "concurrent_positions",
                    )
                    if key in cp44_real_capital_observation
                }
            )

            policy = {
                key: smart_risk_observation[key]
                for key in (
                    "policy_version",
                    "policy_validation",
                    "risk_per_trade",
                    "max_portfolio_risk",
                    "max_concurrent_positions",
                )
                if key in smart_risk_observation
            }

            risk_snapshot[asset] = build_cp44_smart_risk(
                f"{asset}/USDT",
                decision_snapshot[asset],
                smart_risk_observation,
                policy,
            )

        if set(risk_snapshot) != set(decision_snapshot):
            fail("CP44 Smart Risk cardinality mismatch")

        # 12. DYNAMIC TRADE GATE
        # ------------------------------------------------------------------
        # Authoritative Trade Gate only. No status inference, no synthetic
        # readiness, and no OrderIntent creation occurs at this boundary.
        trade_gate_snapshot = {}

        for asset in decision_snapshot:
            opportunity = opportunity_by_asset.get(asset)
            decision = decision_snapshot[asset]
            risk = risk_snapshot[asset]

            if not isinstance(opportunity, dict):
                fail(f"Trade Gate Opportunity missing: {asset}")

            trade_gate_status, gate_reasons = trade_gate_engine.evaluate(
                opportunity,
                decision,
                risk,
            )

            trade_gate_snapshot[asset] = {
                "asset": asset,
                "symbol": f"{asset}/USDT",
                "direction": trade_gate_engine.get_direction(decision),
                "trade_gate_status": trade_gate_status,
                "reasons": list(gate_reasons),
                "gate_observability": trade_gate_engine.build_gate_observability(
                    trade_gate_engine.adapt_opportunity(
                        opportunity,
                        decision,
                    ),
                    decision,
                    risk,
                ),
                "source": "TRADE_GATE_v0.1",
                "execution": False,
                "db_writes": 0,
            }

        if set(trade_gate_snapshot) != set(decision_snapshot):
            fail("Dynamic Trade Gate cardinality mismatch")

        trade_ready_assets = {
            asset
            for asset, gate_row in trade_gate_snapshot.items()
            if gate_row.get("trade_gate_status") == TRADE_READY_STATUS
        }

        if not trade_ready_assets.issubset(set(trade_gate_snapshot)):
            fail("Trade Ready asset identity mismatch")

        print(f"TRADE_GATE_READY={len(trade_gate_snapshot)}")
        print(f"TRADE_READY={len(trade_ready_assets)}")

        # ------------------------------------------------------------------
        # 12. CP69 CANONICAL RUNTIME OBSERVATION
        # ------------------------------------------------------------------
        cp69_observation = build_observation(
            emitted_at=utc_now_iso(),
            universe_assets=universe_assets,
            market_data_results=market_data_results,
            opportunity_by_asset=opportunity_by_asset,
            dynamic_signals=dynamic_signals,
            validation_results=validation_results,
            fusion_snapshot=fusion_snapshot,
            score_snapshot=score_snapshot,
            decision_snapshot=decision_snapshot,
            risk_snapshot=risk_snapshot,
            trade_gate_snapshot=trade_gate_snapshot,
            trade_ready_assets=trade_ready_assets,
            news_items=news_items,
            social_items=social_items,
            launch_timestamp=LAUNCH_TIMESTAMP,
        )
        cp69_stream_path = append_observation(cp69_observation)
        print(f"CP69_OBSERVATION_WRITTEN=1")
        print(f"CP69_OBSERVATION_PATH={cp69_stream_path}")

        # 12. EXECUTION BOUNDARY ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â CONTRACT CHECK ONLY
        # ------------------------------------------------------------------
        assert_execution_disabled()

        if trade_ready_assets:
            print(
                "TRADE_READY assets detected; "
                "OrderIntent creation/submission remains disabled."
            )

        # No OrderIntent creation.
        # No canonical order request creation.
        # No exchange submission.
        # No execution.
        # No DB writes.

        print("=" * 90)
        print("FULL DYNAMIC UNIVERSE STATIC/CONTROLLED ORCHESTRATION COMPLETE")
        print(f"UNIVERSE_SIZE={len(universe_assets)}")
        print(f"SIGNAL_READY={len(dynamic_signals)}")
        print(f"VALIDATED={len(validated_signals)}")
        print(f"FUSION_READY={len(fusion_snapshot)}")
        print(f"SCORE_READY={len(score_snapshot)}")
        print(f"DECISION_READY={len(decision_snapshot)}")
        print(f"RISK_READY={len(risk_snapshot)}")
        print(f"TRADE_GATE_READY={len(trade_gate_snapshot)}")
        print(f"TRADE_READY={len(trade_ready_assets)}")
        print("ORDER_INTENTS_CREATED=0")
        print("REAL_ORDER=FALSE")
        print("REAL_TRADE=FALSE")
        print("EXECUTION=OFF")
        print("DB_WRITES=0")
        print("FAIL_CLOSED=TRUE")
        print("=" * 90)

        return 0

    except Exception as exc:
        print("=" * 90)
        print("ARUNDA TRADER ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â DYNAMIC PIPELINE FAILURE")
        print(f"ERROR : {exc}")
        print("EXECUTION          : DISABLED")
        print("ORDER SUBMISSION   : NONE")
        print("EXCHANGE WRITE     : NONE")
        print("DB_WRITES           : 0")
        print("FAIL-CLOSED         : YES")
        print("=" * 90)
        return 1

if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except Exception as exc:
        print()
        print("=" * 90)
        print(
            "ARUNDA TRADER ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â "
            "PRODUCTION PIPELINE FAILURE"
        )
        print("=" * 90)

        print(
            f"ERROR : {exc}"
        )

        print()
        print(
            "EXECUTION          : DISABLED"
        )
        print(
            "ORDER SUBMISSION   : NONE"
        )
        print(
            "EXCHANGE WRITE     : NONE"
        )
        print(
            "DB_WRITES          : 0"
        )
        print(
            "FAIL-CLOSED        : YES"
        )
        print(
            "EXECUTION BOUNDARY : FAIL-CLOSED"
        )

        print("=" * 90)

        raise
































