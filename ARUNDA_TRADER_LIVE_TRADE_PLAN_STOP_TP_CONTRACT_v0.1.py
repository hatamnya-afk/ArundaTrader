# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE TRADE PLAN + STOP/TP CONTRACT v0.2

UPSTREAM:
LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1

DESIGN:
- Consume upstream candidates only.
- Never recreate eligibility.
- Never recreate ranking.
- Never infer direction.
- Never reconstruct score.
- Never inject live data.
- Never execute orders.
- Never modify production DB.
- Empty upstream candidate pool is a valid NO_TRADE state.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

PRODUCTION_DB = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

CAPTURE_DIR = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_DIR",
        r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
    )
)

UPSTREAM_REPORT = (
    CAPTURE_DIR
    / "LIVE_TRADE_CANDIDATE_RANKING_REPORT.json"
)

REPORT_PATH = (
    CAPTURE_DIR
    / "LIVE_TRADE_PLAN_STOP_TP_REPORT.json"
)

EXPECTED_ENGINE = "FUSION_v0.5"

EXPECTED_FRONTIER = (
    "LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1"
)

# Analytical risk-plan defaults.
# These values NEVER create eligibility.
DEFAULT_RISK_PCT = 0.01
DEFAULT_STOP_DISTANCE_PCT = 0.02
DEFAULT_TP1_RR = 1.5
DEFAULT_TP2_RR = 2.5

EPS = 1e-12


# =============================================================================
# GENERAL HELPERS
# =============================================================================

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def get_production_baseline() -> dict[str, Any]:
    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production database not found: {PRODUCTION_DB}"
        )

    size = PRODUCTION_DB.stat().st_size
    sha256 = sha256_file(PRODUCTION_DB)

    with sqlite3.connect(PRODUCTION_DB) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]

    return {
        "rows": int(rows),
        "size": int(size),
        "sha256": sha256,
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Upstream report not found: {path}"
        )

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(
            "Upstream report root must be a JSON object."
        )

    return data


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def safe_string(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# UPSTREAM VALIDATION
# =============================================================================

def extract_candidates(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Correctly handles the actual upstream report structure.

    Actual upstream structure:

        candidate_pool       : integer
        selected             : list
        eligible_pool        : list
        rejected             : list

    Candidate collection priority:
        1. selected
        2. eligible_pool

    If both are empty, this is a valid NO_TRADE state.

    IMPORTANT:
    candidate_pool is a COUNT, not a candidate collection.
    """

    selected = report.get("selected", [])
    eligible_pool = report.get("eligible_pool", [])

    if selected is None:
        selected = []

    if eligible_pool is None:
        eligible_pool = []

    if not isinstance(selected, list):
        raise ValueError(
            "Upstream 'selected' field must be a list."
        )

    if not isinstance(eligible_pool, list):
        raise ValueError(
            "Upstream 'eligible_pool' field must be a list."
        )

    # The ranking gate's selected candidates are the preferred source.
    if selected:
        candidates = selected
    else:
        candidates = eligible_pool

    normalized: list[dict[str, Any]] = []

    for item in candidates:

        if not isinstance(item, dict):
            raise ValueError(
                "Every upstream candidate must be a JSON object."
            )

        normalized.append(item)

    return normalized


def validate_upstream(
    report: dict[str, Any]
) -> dict[str, Any]:

    frontier = report.get("frontier")
    engine = report.get("engine")
    snapshot_id = report.get("snapshot_id")
    decision = report.get("decision")

    if frontier != EXPECTED_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier: "
            f"{frontier!r}"
        )

    if engine != EXPECTED_ENGINE:
        raise ValueError(
            "Unexpected upstream engine: "
            f"{engine!r}"
        )

    if not snapshot_id:
        raise ValueError(
            "Upstream report missing snapshot_id."
        )

    candidates = extract_candidates(report)

    candidate_pool = safe_int(
        report.get("candidate_pool")
    )

    selected_count = safe_int(
        report.get("selected_candidates")
    )

    if candidate_pool is None:
        raise ValueError(
            "Upstream report missing numeric candidate_pool."
        )

    if selected_count is None:
        raise ValueError(
            "Upstream report missing numeric selected_candidates."
        )

    # Empty pool is explicitly valid.
    if not candidates:

        if candidate_pool != 0:
            raise ValueError(
                "Upstream candidate_pool is non-zero "
                "but no candidate collection was supplied."
            )

        if selected_count != 0:
            raise ValueError(
                "Upstream selected_candidates is non-zero "
                "but selected collection is empty."
            )

    else:

        if selected_count != len(candidates):
            raise ValueError(
                "Upstream selected_candidates does not match "
                "the selected candidate collection."
            )

    return {
        "frontier": frontier,
        "engine": engine,
        "snapshot_id": snapshot_id,
        "decision": decision,
        "candidate_pool": candidate_pool,
        "selected_candidates": selected_count,
        "candidates": candidates,
    }


# =============================================================================
# CANDIDATE NORMALIZATION
# =============================================================================

def normalize_candidate(
    candidate: dict[str, Any]
) -> dict[str, Any]:

    asset = safe_string(
        candidate.get("asset")
    )

    direction = safe_string(
        candidate.get("direction")
    )

    entry_price = safe_float(
        candidate.get("entry_price")
    )

    confidence = safe_float(
        candidate.get("confidence")
    )

    ranking_score = safe_float(
        candidate.get("ranking_score")
    )

    selection_score = safe_float(
        candidate.get("selection_score")
    )

    available_weight = safe_float(
        candidate.get("available_weight")
    )

    data_quality = safe_string(
        candidate.get("data_quality")
    )

    signal_strength = safe_string(
        candidate.get("signal_strength")
    )

    candidate_id = candidate.get("id")

    if asset is None:
        raise ValueError(
            "Candidate missing asset."
        )

    if direction is None:
        raise ValueError(
            f"Candidate {asset} missing direction."
        )

    if entry_price is None or entry_price <= 0:
        raise ValueError(
            f"Candidate {asset} has invalid entry_price."
        )

    return {
        "id": candidate_id,
        "asset": asset,
        "direction": direction.upper(),
        "entry_price": entry_price,
        "confidence": confidence,
        "ranking_score": ranking_score,
        "selection_score": selection_score,
        "available_weight": available_weight,
        "data_quality": data_quality,
        "signal_strength": signal_strength,
    }


# =============================================================================
# STOP / TP PLAN
# =============================================================================

def build_plan(
    candidate: dict[str, Any]
) -> dict[str, Any]:

    asset = candidate["asset"]
    direction = candidate["direction"]
    entry = candidate["entry_price"]

    if direction not in {"LONG", "SHORT"}:
        return {
            **candidate,
            "plan_status": "NO_TRADE",
            "plan_reason": "NON_DIRECTIONAL_SIGNAL",
            "risk_pct": DEFAULT_RISK_PCT,
            "stop_distance_pct": DEFAULT_STOP_DISTANCE_PCT,
            "stop_price": None,
            "tp1_price": None,
            "tp2_price": None,
            "risk_per_unit": None,
            "reward_risk_tp1": None,
            "reward_risk_tp2": None,
            "analytical_notional": 0.0,
        }

    stop_distance = (
        entry * DEFAULT_STOP_DISTANCE_PCT
    )

    if direction == "LONG":

        stop_price = entry - stop_distance

        tp1_price = (
            entry
            + stop_distance * DEFAULT_TP1_RR
        )

        tp2_price = (
            entry
            + stop_distance * DEFAULT_TP2_RR
        )

        risk_per_unit = (
            entry - stop_price
        )

    else:

        stop_price = entry + stop_distance

        tp1_price = (
            entry
            - stop_distance * DEFAULT_TP1_RR
        )

        tp2_price = (
            entry
            - stop_distance * DEFAULT_TP2_RR
        )

        risk_per_unit = (
            stop_price - entry
        )

    if risk_per_unit <= EPS:
        return {
            **candidate,
            "plan_status": "NO_TRADE",
            "plan_reason": "INVALID_RISK_DISTANCE",
            "risk_pct": DEFAULT_RISK_PCT,
            "stop_distance_pct": DEFAULT_STOP_DISTANCE_PCT,
            "stop_price": None,
            "tp1_price": None,
            "tp2_price": None,
            "risk_per_unit": None,
            "reward_risk_tp1": None,
            "reward_risk_tp2": None,
            "analytical_notional": 0.0,
        }

    return {
        **candidate,
        "plan_status": "ANALYTICAL_PLAN",
        "plan_reason": "UPSTREAM_CANDIDATE_ACCEPTED",
        "risk_pct": DEFAULT_RISK_PCT,
        "stop_distance_pct": DEFAULT_STOP_DISTANCE_PCT,
        "stop_price": stop_price,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "risk_per_unit": risk_per_unit,
        "reward_risk_tp1": DEFAULT_TP1_RR,
        "reward_risk_tp2": DEFAULT_TP2_RR,
        "analytical_notional": 0.0,
    }


# =============================================================================
# REPORT
# =============================================================================

def write_report(report: dict[str, Any]) -> None:

    CAPTURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            report,
            handle,
            indent=2,
            ensure_ascii=False,
        )


# =============================================================================
# OUTPUT
# =============================================================================

def print_header() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE TRADE PLAN + STOP/TP CONTRACT v0.2"
    )
    print("=" * 100)

    print()
    print("OBJECTIVE:")
    print(
        "  Consume ONLY candidates already passed by the upstream"
    )
    print(
        "  LIVE TRADE CANDIDATE RANKING + MULTI-ASSET DECISION GATE."
    )
    print()
    print("Previously verified frontiers are NOT re-audited.")
    print()
    print("Production DB writes : FORBIDDEN")
    print("Production engine run : NO")
    print("Historical repair     : NONE")
    print("Direction inference   : NONE")
    print("Score reconstruction  : NONE")
    print("Synthetic data        : FORBIDDEN")
    print("Live data injection   : NONE")
    print("Order execution       : NONE")
    print()


def main() -> None:

    print_header()

    # -------------------------------------------------------------------------
    # Production baseline
    # -------------------------------------------------------------------------

    baseline = get_production_baseline()

    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    print(f"Rows   : {baseline['rows']}")
    print(f"Size   : {baseline['size']}")
    print(f"SHA256 : {baseline['sha256']}")
    print()

    # -------------------------------------------------------------------------
    # Upstream
    # -------------------------------------------------------------------------

    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    print(f"Report   : {UPSTREAM_REPORT}")

    upstream_report = load_json(
        UPSTREAM_REPORT
    )

    upstream = validate_upstream(
        upstream_report
    )

    print(
        f"Snapshot : {upstream['snapshot_id']}"
    )

    print(
        f"Decision : {upstream['decision']}"
    )

    print(
        f"Candidate pool : {upstream['candidate_pool']}"
    )

    print(
        f"Selected candidates : "
        f"{upstream['selected_candidates']}"
    )

    # -------------------------------------------------------------------------
    # Candidate pool
    # -------------------------------------------------------------------------

    candidates = upstream["candidates"]

    print()
    print("=" * 100)
    print("UPSTREAM CANDIDATE POOL")
    print("=" * 100)

    print(
        f"Candidates received : {len(candidates)}"
    )

    # -------------------------------------------------------------------------
    # Empty upstream pool
    # -------------------------------------------------------------------------

    if not candidates:

        print()
        print(
            "No eligible candidates received from upstream."
        )

        print()
        print(
            "Trade plan generation : NOT PERFORMED"
        )

        print(
            "Stop/TP construction   : NOT PERFORMED"
        )

        print(
            "Reason                 : UPSTREAM_POOL_EMPTY"
        )

        print()
        print("=" * 100)
        print("TRADE PLAN SUMMARY")
        print("=" * 100)

        print("ANALYTICAL_PLANS : 0")
        print("NO_TRADE         : 0")
        print("Analytical notional : 0.000000")

        # -------------------------------------------------------------
        # Re-read production baseline only for invariant confirmation.
        # No audit of previously completed frontiers.
        # -------------------------------------------------------------

        after = get_production_baseline()

        invariant = (
            baseline["rows"] == after["rows"]
            and baseline["size"] == after["size"]
            and baseline["sha256"] == after["sha256"]
        )

        print()
        print("=" * 100)
        print("PRODUCTION DATABASE INVARIANT")
        print("=" * 100)

        print(
            f"Before rows : {baseline['rows']}"
        )
        print(
            f"After rows  : {after['rows']}"
        )

        print(
            f"Before size : {baseline['size']}"
        )
        print(
            f"After size  : {after['size']}"
        )

        print(
            f"Before SHA256 : {baseline['sha256']}"
        )
        print(
            f"After SHA256  : {after['sha256']}"
        )

        print(
            "PRODUCTION DB INVARIANT : "
            f"{'PASS' if invariant else 'FAIL'}"
        )

        report = {
            "frontier": (
                "LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.2"
            ),
            "timestamp_utc": utc_now(),
            "engine": EXPECTED_ENGINE,
            "snapshot_id": upstream["snapshot_id"],
            "source_frontier": EXPECTED_FRONTIER,
            "upstream_report": str(
                UPSTREAM_REPORT
            ),
            "candidate_pool": 0,
            "plans": [],
            "plan_count": 0,
            "no_trade_count": 0,
            "decision": "NO_TRADE",
            "production_database": {
                "before": baseline,
                "after": after,
                "unchanged": invariant,
            },
            "safety": {
                "production_db_modified": False,
                "production_engine_executed": False,
                "historical_repair": False,
                "direction_inference": False,
                "score_reconstruction": False,
                "synthetic_data": False,
                "live_data_injection": False,
                "order_execution": False,
            },
        }

        write_report(report)

        print()
        print("=" * 100)
        print(
            "LIVE TRADE PLAN + STOP/TP CONTRACT VERDICT"
        )
        print("=" * 100)

        print(
            "UPSTREAM_CANDIDATES_CONSUMED : PASS"
        )

        print(
            "TRADE_PLAN_GENERATION       : "
            "NOT_PERFORMED"
        )

        print(
            "STOP_TP_CONTRACT             : "
            "NOT_PERFORMED"
        )

        print(
            "PRODUCTION_ISOLATION         : "
            f"{'PASS' if invariant else 'FAIL'}"
        )

        print(
            "FRONTIER VERDICT             : "
            "NO_TRADE"
        )

        print()
        print(
            f"Runtime report : {REPORT_PATH}"
        )

        print()
        print("=" * 100)
        print("FINAL SAFETY VERDICT")
        print("=" * 100)

        print("Production DB writes : NONE")
        print("INSERT               : NONE")
        print("UPDATE               : NONE")
        print("DELETE               : NONE")
        print("DDL                  : NONE")
        print("Production engine    : NOT EXECUTED")
        print("Historical repair    : NONE")
        print("Direction inference  : NONE")
        print("Score reconstruction : NONE")
        print("Synthetic data       : NONE")
        print("Live data injection  : NONE")
        print("Order execution      : NONE")
        print()
        print(
            "No eligible upstream candidate exists."
        )
        print(
            "No trade plan, stop, or TP was constructed."
        )

        return

    # -------------------------------------------------------------------------
    # Normalize and build analytical plans
    # -------------------------------------------------------------------------

    normalized_candidates = []

    for candidate in candidates:

        normalized = normalize_candidate(
            candidate
        )

        normalized_candidates.append(
            normalized
        )

    print()
    print("=" * 100)
    print("TRADE PLAN INPUT")
    print("=" * 100)

    for candidate in normalized_candidates:

        print(
            f"{candidate['asset']:6s} | "
            f"{candidate['direction']:5s} | "
            f"entry={candidate['entry_price']}"
        )

    plans = []

    for candidate in normalized_candidates:

        plan = build_plan(
            candidate
        )

        plans.append(plan)

    analytical_plans = [
        p for p in plans
        if p["plan_status"] == "ANALYTICAL_PLAN"
    ]

    no_trade = [
        p for p in plans
        if p["plan_status"] == "NO_TRADE"
    ]

    # -------------------------------------------------------------------------
    # Plan output
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("TRADE PLAN + STOP/TP")
    print("=" * 100)

    print(
        "ASSET | DIR | ENTRY | STOP | TP1 | TP2 | STATUS"
    )
    print("-" * 100)

    for plan in plans:

        print(
            f"{plan['asset']:5s} | "
            f"{plan['direction']:5s} | "
            f"{plan['entry_price']:.10f} | "
            f"{plan['stop_price'] if plan['stop_price'] is not None else '-'} | "
            f"{plan['tp1_price'] if plan['tp1_price'] is not None else '-'} | "
            f"{plan['tp2_price'] if plan['tp2_price'] is not None else '-'} | "
            f"{plan['plan_status']}"
        )

    # -------------------------------------------------------------------------
    # Production invariant
    # -------------------------------------------------------------------------

    after = get_production_baseline()

    invariant = (
        baseline["rows"] == after["rows"]
        and baseline["size"] == after["size"]
        and baseline["sha256"] == after["sha256"]
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(
        f"Before rows : {baseline['rows']}"
    )

    print(
        f"After rows  : {after['rows']}"
    )

    print(
        f"Before size : {baseline['size']}"
    )

    print(
        f"After size  : {after['size']}"
    )

    print(
        f"Before SHA256 : {baseline['sha256']}"
    )

    print(
        f"After SHA256  : {after['sha256']}"
    )

    print(
        "PRODUCTION DB INVARIANT : "
        f"{'PASS' if invariant else 'FAIL'}"
    )

    # -------------------------------------------------------------------------
    # Final decision
    # -------------------------------------------------------------------------

    if not invariant:
        decision = "SAFETY_FAIL"
    elif analytical_plans:
        decision = "ANALYTICAL_PLAN_READY"
    else:
        decision = "NO_TRADE"

    report = {
        "frontier": (
            "LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.2"
        ),
        "timestamp_utc": utc_now(),
        "engine": EXPECTED_ENGINE,
        "snapshot_id": upstream["snapshot_id"],
        "source_frontier": EXPECTED_FRONTIER,
        "upstream_report": str(
            UPSTREAM_REPORT
        ),
        "candidate_pool": len(candidates),
        "plan_count": len(analytical_plans),
        "no_trade_count": len(no_trade),
        "decision": decision,
        "plans": plans,
        "production_database": {
            "before": baseline,
            "after": after,
            "unchanged": invariant,
        },
        "safety": {
            "production_db_modified": False,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "order_execution": False,
        },
    }

    write_report(report)

    print()
    print("=" * 100)
    print(
        "LIVE TRADE PLAN + STOP/TP CONTRACT VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_CANDIDATES_CONSUMED : PASS"
    )

    print(
        "TRADE_PLAN_GENERATION       : "
        f"{'PASS' if analytical_plans else 'NOT_PERFORMED'}"
    )

    print(
        "STOP_TP_CONTRACT             : "
        f"{'PASS' if analytical_plans else 'NOT_PERFORMED'}"
    )

    print(
        "PRODUCTION_ISOLATION         : "
        f"{'PASS' if invariant else 'FAIL'}"
    )

    print(
        f"FRONTIER VERDICT             : {decision}"
    )

    print()
    print(
        f"Analytical plans : "
        f"{len(analytical_plans)}"
    )

    print(
        f"NO_TRADE plans   : "
        f"{len(no_trade)}"
    )

    print()
    print(
        f"Runtime report : {REPORT_PATH}"
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)

    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Production engine    : NOT EXECUTED")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : NONE")
    print("Live data injection  : NONE")
    print("Order execution      : NONE")
    print()
    print(
        "Trade plans are analytical only."
    )
    print(
        "No trading order or execution action is performed."
    )


if __name__ == "__main__":
    main()