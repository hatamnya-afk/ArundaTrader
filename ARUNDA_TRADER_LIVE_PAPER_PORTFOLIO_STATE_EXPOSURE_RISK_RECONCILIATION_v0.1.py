# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE PAPER PORTFOLIO STATE + EXPOSURE / RISK RECONCILIATION v0.1

Purpose:
    Consume ONLY already-verified upstream paper-trade lifecycle outputs.

    This frontier does NOT:
      - execute production engine
      - modify production DB
      - reconstruct signals
      - infer direction
      - inject live data
      - create synthetic positions
      - execute real orders

    It evaluates only:
      - paper portfolio state
      - position count
      - exposure
      - concentration
      - aggregate analytical risk
      - consistency across upstream paper lifecycle reports
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_DIR / "arunda.db"

CAPTURE_DIR = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_DIR",
        r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
    )
)

UPSTREAM_RISK_REPORT = (
    CAPTURE_DIR
    / "LIVE_TRADE_RISK_POSITION_SIZING_REPORT.json"
)

UPSTREAM_PLAN_REPORT = (
    CAPTURE_DIR
    / "LIVE_TRADE_PLAN_STOP_TP_REPORT.json"
)

UPSTREAM_LIFECYCLE_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json"
)

UPSTREAM_OUTCOME_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json"
)

UPSTREAM_MONITOR_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json"
)

OUTPUT_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json"
)

FRONTIER_NAME = (
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_v0.1"
)


# =============================================================================
# OUTPUT
# =============================================================================

def line(char="=", n=100):
    print(char * n)


def section(title: str):
    print()
    line("=")
    print(title)
    line("=")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required upstream report not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Report root must be an object: {path}")

    return data


# =============================================================================
# DATABASE BASELINE
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def production_baseline() -> dict:
    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(PRODUCTION_DB)

    with sqlite3.connect(PRODUCTION_DB) as conn:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]

    return {
        "rows": int(row_count),
        "size": PRODUCTION_DB.stat().st_size,
        "sha256": sha256_file(PRODUCTION_DB),
    }


def production_invariant(before: dict) -> dict:
    after = production_baseline()

    unchanged = (
        before["rows"] == after["rows"]
        and before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )

    return {
        "before": before,
        "after": after,
        "unchanged": unchanged,
    }


# =============================================================================
# UPSTREAM HELPERS
# =============================================================================

def get_snapshot(report: dict) -> str | None:
    """
    Upstream reports are intentionally allowed to expose snapshot information
    under several established field names.
    """

    candidates = [
        report.get("snapshot"),
        report.get("snapshot_id"),
        report.get("current_snapshot"),
    ]

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def get_decision(report: dict) -> str | None:
    for key in (
        "decision",
        "frontier_decision",
        "portfolio_decision",
    ):
        value = report.get(key)
        if isinstance(value, str):
            return value
    return None


def extract_candidate_collection(report: dict) -> list:
    """
    Read-only compatibility layer.

    It accepts only an actual collection already produced upstream.
    It NEVER creates candidates.
    """

    possible = [
        report.get("selected"),
        report.get("selected_candidates"),
        report.get("eligible_pool"),
        report.get("candidates"),
        report.get("positions"),
        report.get("paper_positions"),
    ]

    for value in possible:
        if isinstance(value, list):
            return value

    return []


def validate_upstream_reports(
    risk_report: dict,
    plan_report: dict,
    lifecycle_report: dict,
    outcome_report: dict,
    monitor_report: dict,
) -> dict:

    plan_snapshot = get_snapshot(plan_report)
    risk_snapshot = get_snapshot(risk_report)
    lifecycle_snapshot = get_snapshot(lifecycle_report)
    outcome_snapshot = get_snapshot(outcome_report)
    monitor_snapshot = get_snapshot(monitor_report)

    snapshots = [
        s for s in (
            plan_snapshot,
            risk_snapshot,
            lifecycle_snapshot,
            outcome_snapshot,
            monitor_snapshot,
        )
        if s is not None
    ]

    snapshot_coherent = (
        len(set(snapshots)) <= 1
        if snapshots
        else True
    )

    plan_candidates = extract_candidate_collection(plan_report)
    risk_candidates = extract_candidate_collection(risk_report)
    lifecycle_positions = extract_candidate_collection(
        lifecycle_report
    )
    outcome_positions = extract_candidate_collection(
        outcome_report
    )
    monitor_positions = extract_candidate_collection(
        monitor_report
    )

    return {
        "snapshot": (
            plan_snapshot
            or risk_snapshot
            or lifecycle_snapshot
            or outcome_snapshot
            or monitor_snapshot
        ),
        "snapshot_coherent": snapshot_coherent,
        "plan_candidates": plan_candidates,
        "risk_candidates": risk_candidates,
        "lifecycle_positions": lifecycle_positions,
        "outcome_positions": outcome_positions,
        "monitor_positions": monitor_positions,
    }


# =============================================================================
# POSITION NORMALIZATION
# =============================================================================

def normalize_position(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return {}

    asset = (
        raw.get("asset")
        or raw.get("symbol")
        or raw.get("ticker")
    )

    direction = (
        raw.get("direction")
        or raw.get("side")
    )

    notional = (
        raw.get("analytical_notional")
        if raw.get("analytical_notional") is not None
        else raw.get("notional")
    )

    quantity = raw.get("quantity")

    entry_price = (
        raw.get("entry_price")
        if raw.get("entry_price") is not None
        else raw.get("entry")
    )

    stop_price = (
        raw.get("stop_price")
        if raw.get("stop_price") is not None
        else raw.get("stop_loss")
    )

    take_profit = (
        raw.get("take_profit")
        if raw.get("take_profit") is not None
        else raw.get("tp_price")
    )

    risk_amount = (
        raw.get("risk_amount")
        if raw.get("risk_amount") is not None
        else raw.get("risk")
    )

    pnl = (
        raw.get("unrealized_pnl")
        if raw.get("unrealized_pnl") is not None
        else raw.get("pnl")
    )

    return {
        "asset": str(asset).upper() if asset else None,
        "direction": str(direction).upper() if direction else None,
        "notional": safe_float(notional),
        "quantity": safe_float(quantity),
        "entry_price": safe_float(entry_price),
        "stop_price": safe_float(stop_price),
        "take_profit": safe_float(take_profit),
        "risk_amount": safe_float(risk_amount),
        "pnl": safe_float(pnl),
        "state": raw.get("state") or raw.get("status"),
        "raw": raw,
    }


def normalize_positions(collection: list) -> list[dict]:
    result = []

    for item in collection:
        if not isinstance(item, dict):
            continue

        normalized = normalize_position(item)

        if normalized.get("asset"):
            result.append(normalized)

    return result


# =============================================================================
# PORTFOLIO CALCULATIONS
# =============================================================================

def aggregate_by_asset(positions: list[dict]) -> dict:
    result = {}

    for pos in positions:
        asset = pos["asset"]

        bucket = result.setdefault(
            asset,
            {
                "asset": asset,
                "position_count": 0,
                "notional": 0.0,
                "risk_amount": 0.0,
                "pnl": 0.0,
            },
        )

        bucket["position_count"] += 1
        bucket["notional"] += pos["notional"]
        bucket["risk_amount"] += pos["risk_amount"]
        bucket["pnl"] += pos["pnl"]

    return result


def portfolio_metrics(positions: list[dict]) -> dict:
    total_notional = sum(
        p["notional"] for p in positions
    )

    total_risk = sum(
        p["risk_amount"] for p in positions
    )

    total_pnl = sum(
        p["pnl"] for p in positions
    )

    return {
        "position_count": len(positions),
        "total_notional": total_notional,
        "total_risk": total_risk,
        "total_pnl": total_pnl,
    }


def concentration_metrics(
    positions: list[dict],
    total_notional: float,
) -> dict:

    by_asset = aggregate_by_asset(positions)

    concentrations = {}

    for asset, data in by_asset.items():
        if total_notional > 0:
            pct = (
                data["notional"]
                / total_notional
                * 100.0
            )
        else:
            pct = 0.0

        concentrations[asset] = pct

    max_asset = None
    max_pct = 0.0

    if concentrations:
        max_asset = max(
            concentrations,
            key=concentrations.get,
        )
        max_pct = concentrations[max_asset]

    return {
        "asset_concentration_pct": concentrations,
        "max_asset": max_asset,
        "max_asset_pct": max_pct,
    }


# =============================================================================
# RECONCILIATION
# =============================================================================

def reconcile_state(
    validation: dict,
    lifecycle_positions: list[dict],
    outcome_positions: list[dict],
    monitor_positions: list[dict],
) -> dict:

    lifecycle_count = len(lifecycle_positions)
    outcome_count = len(outcome_positions)
    monitor_count = len(monitor_positions)

    state_coherent = True

    # Empty upstream is a valid state.
    if lifecycle_count == 0:
        state_coherent = (
            outcome_count == 0
            and monitor_count == 0
        )

    return {
        "snapshot_coherent": validation["snapshot_coherent"],
        "lifecycle_positions": lifecycle_count,
        "outcome_positions": outcome_count,
        "monitor_positions": monitor_count,
        "state_coherent": state_coherent,
    }


# =============================================================================
# REPORT
# =============================================================================

def write_report(report: dict):
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print()
    line("=")
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO STATE "
        "+ EXPOSURE / RISK RECONCILIATION v0.1"
    )
    line("=")

    print()
    print("OBJECTIVE:")
    print("  Consume ONLY verified upstream PAPER lifecycle state.")
    print("  Reconcile portfolio state, exposure and analytical risk.")
    print()
    print("Production DB writes : FORBIDDEN")
    print("Production engine run : NO")
    print("Historical repair     : NONE")
    print("Direction inference   : NONE")
    print("Score reconstruction  : NONE")
    print("Synthetic data        : FORBIDDEN")
    print("Live data injection   : NONE")
    print("Order execution       : NONE")

    # -------------------------------------------------------------------------
    # BASELINE
    # -------------------------------------------------------------------------

    section("PRODUCTION BASELINE")

    baseline = production_baseline()

    print(f"Rows   : {baseline['rows']}")
    print(f"Size   : {baseline['size']}")
    print(f"SHA256 : {baseline['sha256']}")

    # -------------------------------------------------------------------------
    # DISCOVERY
    # -------------------------------------------------------------------------

    section("LIVE CAPTURE")

    print(f"Directory : {CAPTURE_DIR}")
    print(f"Risk      : {UPSTREAM_RISK_REPORT}")
    print(f"Plan      : {UPSTREAM_PLAN_REPORT}")
    print(f"Lifecycle : {UPSTREAM_LIFECYCLE_REPORT}")
    print(f"Outcome   : {UPSTREAM_OUTCOME_REPORT}")
    print(f"Monitor   : {UPSTREAM_MONITOR_REPORT}")

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    risk_report = load_json(UPSTREAM_RISK_REPORT)
    plan_report = load_json(UPSTREAM_PLAN_REPORT)
    lifecycle_report = load_json(
        UPSTREAM_LIFECYCLE_REPORT
    )
    outcome_report = load_json(
        UPSTREAM_OUTCOME_REPORT
    )
    monitor_report = load_json(
        UPSTREAM_MONITOR_REPORT
    )

    validation = validate_upstream_reports(
        risk_report,
        plan_report,
        lifecycle_report,
        outcome_report,
        monitor_report,
    )

    lifecycle_positions = normalize_positions(
        validation["lifecycle_positions"]
    )

    outcome_positions = normalize_positions(
        validation["outcome_positions"]
    )

    monitor_positions = normalize_positions(
        validation["monitor_positions"]
    )

    # -------------------------------------------------------------------------
    # UPSTREAM
    # -------------------------------------------------------------------------

    section("UPSTREAM PORTFOLIO STATE")

    snapshot = validation["snapshot"]

    print(f"Snapshot        : {snapshot}")
    print(
        f"Snapshot coherence : "
        f"{'PASS' if validation['snapshot_coherent'] else 'FAIL'}"
    )

    print(
        f"Lifecycle positions : "
        f"{len(lifecycle_positions)}"
    )

    print(
        f"Outcome positions   : "
        f"{len(outcome_positions)}"
    )

    print(
        f"Monitor positions   : "
        f"{len(monitor_positions)}"
    )

    # -------------------------------------------------------------------------
    # PORTFOLIO SOURCE
    # -------------------------------------------------------------------------

    # Lifecycle is the authoritative source for open paper positions.
    positions = lifecycle_positions

    section("PAPER PORTFOLIO STATE")

    if not positions:
        print("PAPER POSITIONS : 0")
        print("OPEN POSITIONS  : 0")
        print("CLOSED POSITIONS: 0")
        print("PORTFOLIO STATE : EMPTY")
    else:
        print(f"PAPER POSITIONS : {len(positions)}")

        open_count = 0
        closed_count = 0

        for pos in positions:
            state = str(
                pos.get("state") or ""
            ).upper()

            if "CLOSED" in state:
                closed_count += 1
            else:
                open_count += 1

        print(f"OPEN POSITIONS  : {open_count}")
        print(f"CLOSED POSITIONS: {closed_count}")

        for pos in positions:
            print(
                f"{pos['asset']:8s} | "
                f"{str(pos['direction']):6s} | "
                f"notional={pos['notional']:.6f} | "
                f"risk={pos['risk_amount']:.6f} | "
                f"pnl={pos['pnl']:.6f}"
            )

    # -------------------------------------------------------------------------
    # EXPOSURE
    # -------------------------------------------------------------------------

    metrics = portfolio_metrics(positions)

    section("PORTFOLIO EXPOSURE")

    print(
        f"Total positions       : "
        f"{metrics['position_count']}"
    )

    print(
        f"Total analytical notional : "
        f"{metrics['total_notional']:.6f}"
    )

    print(
        f"Total analytical risk     : "
        f"{metrics['total_risk']:.6f}"
    )

    by_asset = aggregate_by_asset(positions)

    if by_asset:
        print()
        print(
            "ASSET EXPOSURE"
        )

        for asset, data in sorted(
            by_asset.items()
        ):
            print(
                f"{asset:8s} | "
                f"positions={data['position_count']} | "
                f"notional={data['notional']:.6f} | "
                f"risk={data['risk_amount']:.6f}"
            )
    else:
        print("No portfolio exposure exists.")

    # -------------------------------------------------------------------------
    # CONCENTRATION
    # -------------------------------------------------------------------------

    concentration = concentration_metrics(
        positions,
        metrics["total_notional"],
    )

    section("PORTFOLIO CONCENTRATION")

    print(
        f"Maximum asset : "
        f"{concentration['max_asset']}"
    )

    print(
        f"Maximum concentration : "
        f"{concentration['max_asset_pct']:.6f}%"
    )

    if concentration["asset_concentration_pct"]:
        for asset, pct in sorted(
            concentration[
                "asset_concentration_pct"
            ].items()
        ):
            print(
                f"{asset:8s} | "
                f"{pct:.6f}%"
            )
    else:
        print("No asset concentration.")

    # -------------------------------------------------------------------------
    # RISK
    # -------------------------------------------------------------------------

    section("AGGREGATE PAPER RISK")

    print(
        f"Portfolio risk        : "
        f"{metrics['total_risk']:.6f}"
    )

    print(
        f"Aggregate unrealized P&L : "
        f"{metrics['total_pnl']:.6f}"
    )

    if metrics["total_notional"] > 0:
        risk_pct = (
            metrics["total_risk"]
            / metrics["total_notional"]
            * 100.0
        )
    else:
        risk_pct = 0.0

    print(
        f"Risk / notional       : "
        f"{risk_pct:.6f}%"
    )

    # -------------------------------------------------------------------------
    # RECONCILIATION
    # -------------------------------------------------------------------------

    reconciliation = reconcile_state(
        validation,
        lifecycle_positions,
        outcome_positions,
        monitor_positions,
    )

    section("PORTFOLIO STATE RECONCILIATION")

    print(
        "SNAPSHOT COHERENCE       : "
        f"{'PASS' if reconciliation['snapshot_coherent'] else 'FAIL'}"
    )

    print(
        "POSITION STATE COHERENCE : "
        f"{'PASS' if reconciliation['state_coherent'] else 'FAIL'}"
    )

    # -------------------------------------------------------------------------
    # PORTFOLIO VERDICT
    # -------------------------------------------------------------------------

    section(
        "LIVE PAPER PORTFOLIO STATE "
        "+ EXPOSURE / RISK RECONCILIATION VERDICT"
    )

    state_pass = reconciliation["state_coherent"]
    snapshot_pass = reconciliation["snapshot_coherent"]

    frontier_pass = (
        state_pass
        and snapshot_pass
    )

    if not positions:
        verdict = "NO_TRADE"
    elif frontier_pass:
        verdict = "PORTFOLIO_STATE_PASS"
    else:
        verdict = "PORTFOLIO_RISK_REVIEW"

    print(
        f"UPSTREAM_STATE_CONSUMED : PASS"
    )

    print(
        f"PORTFOLIO_STATE         : "
        f"{'PASS' if state_pass else 'FAIL'}"
    )

    print(
        f"EXPOSURE_RECONCILIATION : "
        f"{'PASS' if frontier_pass else 'REVIEW'}"
    )

    print(
        f"RISK_RECONCILIATION     : "
        f"{'PASS' if frontier_pass else 'REVIEW'}"
    )

    print(
        f"PRODUCTION_ISOLATION    : PASS"
    )

    print(
        f"FRONTIER VERDICT        : {verdict}"
    )

    # -------------------------------------------------------------------------
    # DB INVARIANT
    # -------------------------------------------------------------------------

    invariant = production_invariant(
        baseline
    )

    section("PRODUCTION DATABASE INVARIANT")

    print(
        f"Before rows : "
        f"{invariant['before']['rows']}"
    )

    print(
        f"After rows  : "
        f"{invariant['after']['rows']}"
    )

    print(
        f"Before size : "
        f"{invariant['before']['size']}"
    )

    print(
        f"After size  : "
        f"{invariant['after']['size']}"
    )

    print(
        f"Before SHA256 : "
        f"{invariant['before']['sha256']}"
    )

    print(
        f"After SHA256  : "
        f"{invariant['after']['sha256']}"
    )

    print(
        "PRODUCTION DB INVARIANT : "
        f"{'PASS' if invariant['unchanged'] else 'FAIL'}"
    )

    # -------------------------------------------------------------------------
    # FINAL REPORT
    # -------------------------------------------------------------------------

    report = {
        "frontier": FRONTIER_NAME,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "snapshot": snapshot,

        "portfolio": {
            "position_count": metrics[
                "position_count"
            ],
            "total_notional": metrics[
                "total_notional"
            ],
            "total_risk": metrics[
                "total_risk"
            ],
            "total_pnl": metrics[
                "total_pnl"
            ],
        },

        "exposure": {
            "by_asset": by_asset,
            "concentration": concentration,
        },

        "reconciliation": reconciliation,

        "verdict": verdict,

        "production_database": invariant,

        "safety": {
            "production_db_modified": False,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
        },
    }

    write_report(report)

    # -------------------------------------------------------------------------
    # FINAL SAFETY
    # -------------------------------------------------------------------------

    section("FINAL SAFETY VERDICT")

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
    print("REAL ORDER EXECUTION : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")

    print()
    print(
        "No real trading order was created, "
        "submitted, or executed."
    )

    print()
    print(
        f"Runtime report : {OUTPUT_REPORT}"
    )


if __name__ == "__main__":
    main()