# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE PAPER TRADE OUTCOME + POSITION CLOSE / P&L RECONCILIATION v0.1

Purpose:
    Consume ONLY paper-trade candidates produced by the upstream
    LIVE TRADE PLAN + STOP/TP CONTRACT frontier.

    This frontier:
      - performs analytical paper outcome reconciliation
      - never creates real orders
      - never modifies production DB
      - never reconstructs historical direction
      - never invents prices
      - never injects synthetic/live data
      - does not re-audit previously verified frontiers

Safety:
    Production DB = READ ONLY
    Capture DB     = READ ONLY
    Real execution = FORBIDDEN
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


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_DIR / "arunda.db"

CAPTURE_ROOT = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_ROOT",
        r"C:\Users\ASUS\AppData\Local\Temp",
    )
)

UPSTREAM_REPORT_NAME = "LIVE_TRADE_PLAN_STOP_TP_REPORT.json"

OUTPUT_REPORT_NAME = (
    "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json"
)


# ============================================================================
# CONSTANTS
# ============================================================================

FRONTIER_NAME = (
    "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_v0.1"
)

EXPECTED_UPSTREAM_FRONTIER = (
    "LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.2"
)

EXPECTED_ENGINE = "FUSION_v0.5"


# ============================================================================
# UTILITY
# ============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_present(mapping: dict, keys: list[str], default=None):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


# ============================================================================
# CAPTURE DISCOVERY
# ============================================================================

def discover_latest_capture() -> Path:
    candidates = []

    if not CAPTURE_ROOT.exists():
        raise FileNotFoundError(
            f"Capture root does not exist: {CAPTURE_ROOT}"
        )

    for p in CAPTURE_ROOT.glob("arunda_live_launch_*"):
        if not p.is_dir():
            continue

        report = p / UPSTREAM_REPORT_NAME

        if report.exists():
            candidates.append(p)

    if not candidates:
        raise FileNotFoundError(
            "No live launch capture containing "
            f"{UPSTREAM_REPORT_NAME} was found."
        )

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )


# ============================================================================
# PRODUCTION BASELINE
# ============================================================================

def production_baseline() -> dict:
    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    size = PRODUCTION_DB.stat().st_size
    digest = sha256_file(PRODUCTION_DB)

    with sqlite3.connect(
        f"file:{PRODUCTION_DB}?mode=ro",
        uri=True,
    ) as conn:

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        ).fetchall()

        fusion_exists = any(
            row[0] == "fusion_signals"
            for row in tables
        )

        rows = 0

        if fusion_exists:
            rows = conn.execute(
                "SELECT COUNT(*) FROM fusion_signals"
            ).fetchone()[0]

    return {
        "rows": rows,
        "size": size,
        "sha256": digest,
    }


# ============================================================================
# UPSTREAM REPORT
# ============================================================================

def load_upstream(report_path: Path) -> dict:
    with report_path.open(
        "r",
        encoding="utf-8",
    ) as f:
        report = json.load(f)

    if not isinstance(report, dict):
        raise ValueError(
            "Upstream report root must be an object."
        )

    return report


def extract_snapshot(report: dict) -> str | None:
    return first_present(
        report,
        [
            "snapshot",
            "snapshot_id",
        ],
    )


def extract_candidates(report: dict) -> list:
    """
    Upstream v0.2 may contain the candidate collection under
    different names depending on the exact report implementation.

    Empty collections are valid and mean NO_TRADE.
    """

    candidate_keys = [
        "selected_candidates",
        "selected",
        "candidates",
        "eligible_pool",
    ]

    for key in candidate_keys:
        value = report.get(key)

        if isinstance(value, list):
            return value

    # Explicitly empty upstream pool.
    candidate_pool = report.get("candidate_pool")

    if candidate_pool == 0:
        return []

    selected_count = report.get("selected_candidates")

    if selected_count == 0:
        return []

    # Some versions expose a scalar count instead of a collection.
    if isinstance(selected_count, int) and selected_count == 0:
        return []

    raise ValueError(
        "Upstream report does not contain a supported "
        "candidate collection."
    )


def validate_upstream(report: dict) -> dict:
    frontier = report.get("frontier")
    engine = report.get("engine")
    snapshot = extract_snapshot(report)

    if frontier != EXPECTED_UPSTREAM_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier: "
            f"{frontier!r}"
        )

    if engine not in (None, EXPECTED_ENGINE):
        raise ValueError(
            "Unexpected upstream engine: "
            f"{engine!r}"
        )

    candidates = extract_candidates(report)

    if not isinstance(candidates, list):
        raise ValueError(
            "Upstream candidate collection must be a list."
        )

    return {
        "frontier": frontier,
        "engine": engine,
        "snapshot": snapshot,
        "decision": report.get("decision"),
        "candidate_pool": report.get(
            "candidate_pool",
            len(candidates),
        ),
        "selected_count": report.get(
            "selected_candidates",
            len(candidates)
            if isinstance(candidates, list)
            else 0,
        ),
        "candidates": candidates,
    }


# ============================================================================
# CANDIDATE NORMALIZATION
# ============================================================================

def normalize_candidate(candidate: dict) -> dict:
    """
    Normalize common naming variants without changing values.

    No inference is performed.
    """

    if not isinstance(candidate, dict):
        raise ValueError(
            "Candidate entry must be an object."
        )

    asset = first_present(
        candidate,
        ["asset", "symbol"],
    )

    direction = first_present(
        candidate,
        ["direction", "dir"],
    )

    entry = first_present(
        candidate,
        [
            "entry_price",
            "entry",
            "planned_entry",
        ],
    )

    stop = first_present(
        candidate,
        [
            "stop_price",
            "stop_loss",
            "stop",
            "sl",
        ],
    )

    take_profit = first_present(
        candidate,
        [
            "take_profit",
            "tp_price",
            "take_profit_price",
            "tp",
        ],
    )

    notional = first_present(
        candidate,
        [
            "notional",
            "analytical_notional",
        ],
    )

    quantity = first_present(
        candidate,
        [
            "quantity",
            "position_size",
            "size",
        ],
    )

    return {
        "asset": asset,
        "direction": direction,
        "entry_price": safe_float(entry),
        "stop_price": safe_float(stop),
        "take_profit": safe_float(take_profit),
        "notional": safe_float(notional),
        "quantity": safe_float(quantity),
        "raw": candidate,
    }


# ============================================================================
# PRICE / OUTCOME POLICY
# ============================================================================

def determine_outcome(
    candidate: dict,
    close_price: float | None,
) -> dict:
    """
    Reconcile a paper trade ONLY when a real observed close price
    is explicitly supplied by an upstream/approved source.

    No price is guessed.
    """

    direction = str(
        candidate.get("direction") or ""
    ).upper()

    entry = candidate.get("entry_price")
    stop = candidate.get("stop_price")
    tp = candidate.get("take_profit")

    result = {
        "status": "NOT_RECONCILED",
        "close_price": close_price,
        "exit_reason": None,
        "pnl_price": None,
        "pnl_pct": None,
        "risk_multiple": None,
    }

    if close_price is None:
        result["status"] = "AWAITING_OBSERVED_CLOSE_PRICE"
        return result

    if entry is None:
        result["status"] = "INVALID_MISSING_ENTRY_PRICE"
        return result

    if direction not in {"LONG", "SHORT"}:
        result["status"] = "INVALID_DIRECTION"
        return result

    if entry <= 0 or close_price <= 0:
        result["status"] = "INVALID_PRICE"
        return result

    # ------------------------------------------------------------
    # P&L
    # ------------------------------------------------------------

    if direction == "LONG":
        pnl_price = close_price - entry
        pnl_pct = ((close_price - entry) / entry) * 100.0

    else:
        pnl_price = entry - close_price
        pnl_pct = ((entry - close_price) / entry) * 100.0

    result["pnl_price"] = pnl_price
    result["pnl_pct"] = pnl_pct

    # ------------------------------------------------------------
    # Stop / TP observation
    #
    # IMPORTANT:
    # A single close price cannot prove intrabar execution order.
    # Therefore we only classify an exact stop/TP hit when the
    # observed close equals/crosses the configured level.
    # Otherwise the position remains observationally open.
    # ------------------------------------------------------------

    if direction == "LONG":

        if stop is not None and close_price <= stop:
            result["status"] = "CLOSED"
            result["exit_reason"] = "STOP_LOSS"

        elif tp is not None and close_price >= tp:
            result["status"] = "CLOSED"
            result["exit_reason"] = "TAKE_PROFIT"

        else:
            result["status"] = "OPEN_OBSERVATION"

    else:

        if stop is not None and close_price >= stop:
            result["status"] = "CLOSED"
            result["exit_reason"] = "STOP_LOSS"

        elif tp is not None and close_price <= tp:
            result["status"] = "CLOSED"
            result["exit_reason"] = "TAKE_PROFIT"

        else:
            result["status"] = "OPEN_OBSERVATION"

    # ------------------------------------------------------------
    # Risk multiple
    # ------------------------------------------------------------

    if stop is not None:
        risk_distance = abs(entry - stop)

        if risk_distance > 0:
            result["risk_multiple"] = (
                abs(pnl_price) / risk_distance
            )

    return result


# ============================================================================
# OPTIONAL OBSERVED CLOSE SOURCE
# ============================================================================

def discover_observed_close(candidate: dict) -> float | None:
    """
    Deliberately conservative.

    This function DOES NOT fetch internet prices.

    It only accepts an explicitly embedded observed close price
    if the upstream candidate already contains one.

    This prevents hidden live-data injection and keeps this
    frontier strictly downstream of the existing chain.
    """

    raw = candidate.get("raw", {})

    value = first_present(
        raw,
        [
            "observed_close_price",
            "close_price",
            "exit_price",
            "observed_exit_price",
        ],
    )

    return safe_float(value)


# ============================================================================
# RECONCILIATION
# ============================================================================

def reconcile_candidates(
    candidates: list[dict],
) -> list[dict]:

    results = []

    for index, raw_candidate in enumerate(
        candidates,
        start=1,
    ):

        candidate = normalize_candidate(
            raw_candidate
        )

        observed_close = discover_observed_close(
            candidate
        )

        outcome = determine_outcome(
            candidate,
            observed_close,
        )

        results.append(
            {
                "candidate_index": index,
                "asset": candidate["asset"],
                "direction": candidate["direction"],
                "entry_price": candidate["entry_price"],
                "stop_price": candidate["stop_price"],
                "take_profit": candidate["take_profit"],
                "quantity": candidate["quantity"],
                "notional": candidate["notional"],
                "outcome": outcome,
            }
        )

    return results


# ============================================================================
# SUMMARY
# ============================================================================

def summarize(results: list[dict]) -> dict:
    closed = [
        r for r in results
        if r["outcome"]["status"] == "CLOSED"
    ]

    open_positions = [
        r for r in results
        if r["outcome"]["status"] == "OPEN_OBSERVATION"
    ]

    awaiting = [
        r for r in results
        if r["outcome"]["status"]
        == "AWAITING_OBSERVED_CLOSE_PRICE"
    ]

    invalid = [
        r for r in results
        if r["outcome"]["status"].startswith("INVALID")
    ]

    pnl_values = [
        r["outcome"]["pnl_pct"]
        for r in closed
        if r["outcome"]["pnl_pct"] is not None
    ]

    total_pnl_pct = (
        sum(pnl_values)
        if pnl_values
        else 0.0
    )

    return {
        "paper_ready": len(results),
        "closed_positions": len(closed),
        "open_positions": len(open_positions),
        "awaiting_observed_close": len(awaiting),
        "invalid_positions": len(invalid),
        "stop_loss_closes": sum(
            1
            for r in closed
            if r["outcome"]["exit_reason"]
            == "STOP_LOSS"
        ),
        "take_profit_closes": sum(
            1
            for r in closed
            if r["outcome"]["exit_reason"]
            == "TAKE_PROFIT"
        ),
        "total_reconciled_pnl_pct": total_pnl_pct,
    }


# ============================================================================
# REPORT
# ============================================================================

def build_report(
    baseline_before: dict,
    baseline_after: dict,
    capture_dir: Path,
    upstream_path: Path,
    upstream: dict,
    results: list[dict],
) -> dict:

    summary = summarize(results)

    if not results:
        frontier_verdict = "NO_TRADE"

    elif summary["invalid_positions"] > 0:
        frontier_verdict = "RECONCILIATION_BLOCKED"

    elif summary["closed_positions"] > 0:
        frontier_verdict = "P&L_RECONCILED"

    elif summary["open_positions"] > 0:
        frontier_verdict = "POSITIONS_OPEN"

    else:
        frontier_verdict = "AWAITING_OBSERVED_CLOSE"

    return {
        "frontier": FRONTIER_NAME,
        "timestamp_utc": utc_now(),

        "objective": {
            "paper_trade_outcome": True,
            "position_close_reconciliation": True,
            "pnl_reconciliation": True,
        },

        "upstream": {
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "snapshot": upstream["snapshot"],
            "decision": upstream["decision"],
            "candidate_pool": upstream["candidate_pool"],
            "selected_count": upstream["selected_count"],
            "report": str(upstream_path),
        },

        "capture": {
            "directory": str(capture_dir),
        },

        "results": results,

        "summary": summary,

        "production_database": {
            "before": baseline_before,
            "after": baseline_after,
            "unchanged": (
                baseline_before == baseline_after
            ),
        },

        "safety": {
            "production_db_modified": False,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "real_order_execution": False,
            "paper_execution_only": True,
        },

        "verdict": {
            "upstream_consumed": True,
            "outcome_reconciliation": (
                "NOT_PERFORMED"
                if not results
                else "PERFORMED"
            ),
            "position_close_reconciliation": (
                "NOT_PERFORMED"
                if not results
                else "PERFORMED"
            ),
            "pnl_reconciliation": (
                "NOT_PERFORMED"
                if not results
                else (
                    "PERFORMED"
                    if summary["closed_positions"] > 0
                    else "AWAITING_CLOSE"
                )
            ),
            "production_isolation": (
                baseline_before == baseline_after
            ),
            "frontier_verdict": frontier_verdict,
        },
    }


# ============================================================================
# OUTPUT
# ============================================================================

def print_header(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_report(report: dict):
    upstream = report["upstream"]
    summary = report["summary"]
    verdict = report["verdict"]
    safety = report["safety"]

    print_header(
        "ARUNDA TRADER LIVE PAPER TRADE OUTCOME + "
        "POSITION CLOSE / P&L RECONCILIATION v0.1"
    )

    print(
        """
OBJECTIVE:
  Consume ONLY candidates already passed by the upstream
  LIVE TRADE PLAN + STOP/TP CONTRACT frontier.

  Reconcile PAPER trade outcomes analytically.
  No real order is created or submitted.
"""
    )

    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)

    print("Production DB writes       : FORBIDDEN")
    print("Production engine run      : NO")
    print("Historical repair          : NONE")
    print("Direction inference        : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic data             : FORBIDDEN")
    print("Live data injection        : NONE")
    print("REAL ORDER EXECUTION       : NONE")
    print("PAPER EXECUTION            : ANALYTICAL ONLY")

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    before = report["production_database"]["before"]

    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    print(f"Report           : {upstream['report']}")
    print(f"Frontier         : {upstream['frontier']}")
    print(f"Engine           : {upstream['engine']}")
    print(f"Snapshot         : {upstream['snapshot']}")
    print(f"Decision         : {upstream['decision']}")
    print(f"Candidate pool   : {upstream['candidate_pool']}")
    print(f"Selected         : {upstream['selected_count']}")

    print()
    print("=" * 100)
    print("PAPER TRADE OUTCOME RECONCILIATION")
    print("=" * 100)

    print(
        f"Candidates received : "
        f"{len(report['results'])}"
    )

    if not report["results"]:
        print()
        print("Outcome reconciliation : NOT PERFORMED")
        print("Position close        : NOT PERFORMED")
        print("P&L reconciliation    : NOT PERFORMED")
        print("Reason                : UPSTREAM_POOL_EMPTY")

    else:
        for row in report["results"]:
            outcome = row["outcome"]

            print(
                f"{row['candidate_index']:02d} | "
                f"{str(row['asset']):<6} | "
                f"{str(row['direction']):<5} | "
                f"entry={row['entry_price']} | "
                f"close={outcome['close_price']} | "
                f"status={outcome['status']} | "
                f"reason={outcome['exit_reason']} | "
                f"pnl%={outcome['pnl_pct']}"
            )

    print()
    print("=" * 100)
    print("POSITION / P&L SUMMARY")
    print("=" * 100)

    print(
        f"PAPER_READY             : "
        f"{summary['paper_ready']}"
    )
    print(
        f"CLOSED POSITIONS        : "
        f"{summary['closed_positions']}"
    )
    print(
        f"OPEN POSITIONS          : "
        f"{summary['open_positions']}"
    )
    print(
        f"AWAITING CLOSE          : "
        f"{summary['awaiting_observed_close']}"
    )
    print(
        f"INVALID POSITIONS       : "
        f"{summary['invalid_positions']}"
    )
    print(
        f"STOP LOSS CLOSES        : "
        f"{summary['stop_loss_closes']}"
    )
    print(
        f"TAKE PROFIT CLOSES      : "
        f"{summary['take_profit_closes']}"
    )
    print(
        f"TOTAL RECONCILED P&L %  : "
        f"{summary['total_reconciled_pnl_pct']:.6f}"
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    after = report["production_database"]["after"]

    print(f"Before rows : {before['rows']}")
    print(f"After rows  : {after['rows']}")
    print(f"Before size : {before['size']}")
    print(f"After size  : {after['size']}")
    print(f"Before SHA256 : {before['sha256']}")
    print(f"After SHA256  : {after['sha256']}")

    print(
        "PRODUCTION DB INVARIANT : "
        + (
            "PASS"
            if report["production_database"]["unchanged"]
            else "FAIL"
        )
    )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER TRADE OUTCOME + "
        "POSITION CLOSE / P&L RECONCILIATION VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_PLAN_CONSUMED     : "
        + ("PASS" if verdict["upstream_consumed"] else "FAIL")
    )

    print(
        "OUTCOME_RECONCILIATION    : "
        + verdict["outcome_reconciliation"]
    )

    print(
        "POSITION_CLOSE_RECONCILIATION : "
        + verdict["position_close_reconciliation"]
    )

    print(
        "P&L_RECONCILIATION        : "
        + verdict["pnl_reconciliation"]
    )

    print(
        "PRODUCTION_ISOLATION      : "
        + (
            "PASS"
            if verdict["production_isolation"]
            else "FAIL"
        )
    )

    print(
        "FRONTIER VERDICT          : "
        + verdict["frontier_verdict"]
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)

    print(
        f"Production DB writes : "
        f"{'NONE' if not safety['production_db_modified'] else 'DETECTED'}"
    )
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print(
        "Production engine    : "
        f"{'NOT EXECUTED' if not safety['production_engine_executed'] else 'EXECUTED'}"
    )
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : NONE")
    print("Live data injection  : NONE")
    print("REAL ORDER EXECUTION : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")

    if not report["results"]:
        print()
        print(
            "No eligible upstream candidate exists."
        )
        print(
            "No paper position was closed or "
            "reconciled."
        )

    print()
    print(
        "No real trading order was created, "
        "submitted, or executed."
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    # ------------------------------------------------------------
    # Production baseline BEFORE
    # ------------------------------------------------------------

    baseline_before = production_baseline()

    print_header(
        "ARUNDA TRADER LIVE PAPER TRADE OUTCOME + "
        "POSITION CLOSE / P&L RECONCILIATION v0.1"
    )

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    print(
        f"Rows   : {baseline_before['rows']}"
    )
    print(
        f"Size   : {baseline_before['size']}"
    )
    print(
        f"SHA256 : {baseline_before['sha256']}"
    )

    # ------------------------------------------------------------
    # Discover capture
    # ------------------------------------------------------------

    capture_dir = discover_latest_capture()

    upstream_path = (
        capture_dir / UPSTREAM_REPORT_NAME
    )

    print()
    print("=" * 100)
    print("LIVE CAPTURE")
    print("=" * 100)

    print(f"Directory : {capture_dir}")
    print(f"Upstream  : {upstream_path}")

    # ------------------------------------------------------------
    # Load upstream
    # ------------------------------------------------------------

    report = load_upstream(
        upstream_path
    )

    upstream = validate_upstream(
        report
    )

    # ------------------------------------------------------------
    # Reconcile ONLY upstream candidates
    # ------------------------------------------------------------

    results = reconcile_candidates(
        upstream["candidates"]
    )

    # ------------------------------------------------------------
    # Production baseline AFTER
    # ------------------------------------------------------------

    baseline_after = production_baseline()

    # ------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------

    output = build_report(
        baseline_before=baseline_before,
        baseline_after=baseline_after,
        capture_dir=capture_dir,
        upstream_path=upstream_path,
        upstream=upstream,
        results=results,
    )

    # ------------------------------------------------------------
    # Write report OUTSIDE production DB
    # ------------------------------------------------------------

    output_path = (
        capture_dir / OUTPUT_REPORT_NAME
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Print
    # ------------------------------------------------------------

    print_report(output)

    print()
    print(
        f"Runtime report : {output_path}"
    )

    # ------------------------------------------------------------
    # Hard safety assertion
    # ------------------------------------------------------------

    if baseline_before != baseline_after:
        raise RuntimeError(
            "CRITICAL SAFETY FAILURE: "
            "Production database changed."
        )


if __name__ == "__main__":
    main()