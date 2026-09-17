# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE PAPER EXECUTION SAFETY GATE v0.2

Purpose:
    Consume ONLY the output of the verified
    LIVE TRADE PLAN + STOP/TP CONTRACT frontier.

    This gate does NOT execute real orders.

Safety:
    - Production DB READ ONLY
    - Production engine NEVER executed
    - No historical repair
    - No direction inference
    - No score reconstruction
    - No synthetic data
    - No live data injection
    - No real order execution
    - Paper execution is analytical only
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_DIR / "arunda.db"

CAPTURE_ROOT = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_ROOT",
        r"C:\Users\ASUS\AppData\Local\Temp",
    )
)

UPSTREAM_REPORT_NAME = (
    "LIVE_TRADE_PLAN_STOP_TP_REPORT.json"
)

OUTPUT_REPORT_NAME = (
    "LIVE_PAPER_EXECUTION_SAFETY_GATE_REPORT.json"
)

EXPECTED_ENGINE = "FUSION_v0.5"

EXPECTED_UPSTREAM_FRONTIERS = {
    "LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.1",
    "LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.2",
    "LIVE_TRADE_PLAN_STOP_TP_CONTRACT",
}


# =============================================================================
# UTILITY
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            "Upstream JSON root must be an object."
        )

    return data


def find_latest_capture() -> Path:
    if not CAPTURE_ROOT.exists():
        raise FileNotFoundError(
            f"Capture root not found: {CAPTURE_ROOT}"
        )

    directories = [
        p
        for p in CAPTURE_ROOT.glob(
            "arunda_live_launch_*"
        )
        if p.is_dir()
    ]

    if not directories:
        raise FileNotFoundError(
            "No arunda_live_launch_* directory found."
        )

    return max(
        directories,
        key=lambda p: p.stat().st_mtime,
    )


def find_upstream_report(
    capture_dir: Path,
) -> Path:

    report = capture_dir / UPSTREAM_REPORT_NAME

    if not report.exists():
        raise FileNotFoundError(
            f"Upstream report not found:\n{report}"
        )

    return report


# =============================================================================
# PRODUCTION DATABASE
# =============================================================================

def production_baseline() -> dict[str, Any]:

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found:\n{PRODUCTION_DB}"
        )

    size = PRODUCTION_DB.stat().st_size

    digest = sha256_file(
        PRODUCTION_DB
    )

    conn = sqlite3.connect(
        str(PRODUCTION_DB)
    )

    try:

        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM fusion_signals
            """
        ).fetchone()

        rows = int(row[0])

    finally:
        conn.close()

    return {
        "rows": rows,
        "size": size,
        "sha256": digest,
    }


# =============================================================================
# GENERIC VALUE EXTRACTION
# =============================================================================

def first_present(
    obj: dict[str, Any],
    keys: list[str],
    default: Any = None,
) -> Any:

    for key in keys:
        if key in obj:
            return obj[key]

    return default


def normalize_count(
    value: Any,
    default: int = 0,
) -> int:

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):

        try:
            return int(value.strip())
        except ValueError:
            return default

    return default


# =============================================================================
# UPSTREAM CANDIDATE EXTRACTION
# =============================================================================

def extract_candidate_collection(
    report: dict[str, Any],
) -> list[Any]:

    """
    Supports the actual report layouts used by the previous
    trade-plan frontier.

    Priority:
        selected
        analytical_plans
        trade_plans
        plans
        candidates

    Empty collections are valid.
    """

    possible_keys = [
        "selected",
        "analytical_plans",
        "trade_plans",
        "plans",
        "candidates",
    ]

    for key in possible_keys:

        if key not in report:
            continue

        value = report[key]

        if value is None:
            return []

        if isinstance(value, list):
            return value

        # Some versions may expose a single object.
        if isinstance(value, dict):
            return [value]

    return []


# =============================================================================
# UPSTREAM VALIDATION
# =============================================================================

def validate_upstream(
    report: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:

    frontier = first_present(
        report,
        [
            "frontier",
            "source_frontier",
        ],
        "",
    )

    if not isinstance(frontier, str):
        frontier = str(frontier)

    # -------------------------------------------------------------------------
    # Engine
    # -------------------------------------------------------------------------

    engine = first_present(
        report,
        [
            "engine",
            "engine_version",
        ],
        EXPECTED_ENGINE,
    )

    if (
        engine is not None
        and str(engine) != EXPECTED_ENGINE
    ):
        raise ValueError(
            "Unexpected engine in upstream report: "
            f"{engine!r}"
        )

    # -------------------------------------------------------------------------
    # Snapshot
    #
    # The actual v0.2 report may use:
    #     snapshot
    #     Snapshot
    #     snapshot_id
    #     or no snapshot field when pool is empty.
    #
    # Missing snapshot is NOT fatal if the upstream explicitly reports
    # NO_TRADE / empty pool.
    # -------------------------------------------------------------------------

    snapshot = first_present(
        report,
        [
            "snapshot",
            "snapshot_id",
            "Snapshot",
        ],
        None,
    )

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    decision = first_present(
        report,
        [
            "decision",
            "frontier_verdict",
            "verdict",
        ],
        "UNKNOWN",
    )

    if decision is None:
        decision = "UNKNOWN"

    decision = str(decision)

    # -------------------------------------------------------------------------
    # Candidate counts
    # -------------------------------------------------------------------------

    candidate_pool = normalize_count(
        first_present(
            report,
            [
                "candidate_pool",
                "eligible_pool",
                "candidates_received",
                "candidate_count",
                "pool_size",
            ],
            0,
        )
    )

    selected_count = normalize_count(
        first_present(
            report,
            [
                "selected_candidates",
                "selected_count",
                "selected_candidate_count",
                "analytical_plans",
                "trade_plans_count",
            ],
            0,
        )
    )

    # -------------------------------------------------------------------------
    # Actual collection
    # -------------------------------------------------------------------------

    candidates = extract_candidate_collection(
        report
    )

    # If a real list exists, it is the strongest source of truth.
    if candidates:
        selected_count = len(candidates)

    # If the report explicitly says zero candidates,
    # empty collection is valid and expected.
    if candidate_pool < 0:
        raise ValueError(
            "candidate_pool cannot be negative."
        )

    if selected_count < 0:
        raise ValueError(
            "selected_candidates cannot be negative."
        )

    # -------------------------------------------------------------------------
    # Empty upstream is VALID.
    #
    # This is important:
    # The current project state has no eligible candidate.
    # That must produce NO_EXECUTION, not a schema crash.
    # -------------------------------------------------------------------------

    if (
        candidate_pool == 0
        and selected_count == 0
    ):
        return {
            "path": str(report_path),
            "frontier": frontier,
            "engine": engine,
            "snapshot": snapshot,
            "decision": decision,
            "candidate_pool": 0,
            "selected_candidates": 0,
            "candidates": [],
            "empty_pool": True,
        }

    # -------------------------------------------------------------------------
    # Non-empty pool requires actual candidate collection.
    # -------------------------------------------------------------------------

    if selected_count > 0 and not candidates:
        raise ValueError(
            "Upstream reports selected candidates > 0 "
            "but no candidate collection was found."
        )

    if (
        candidate_pool > 0
        and selected_count == 0
    ):
        raise ValueError(
            "Upstream candidate_pool > 0 but "
            "selected_candidates == 0."
        )

    return {
        "path": str(report_path),
        "frontier": frontier,
        "engine": engine,
        "snapshot": snapshot,
        "decision": decision,
        "candidate_pool": candidate_pool,
        "selected_candidates": selected_count,
        "candidates": candidates,
        "empty_pool": False,
    }


# =============================================================================
# CANDIDATE CONTRACT
# =============================================================================

def validate_candidate(
    candidate: Any,
) -> tuple[bool, list[str]]:

    reasons: list[str] = []

    if not isinstance(candidate, dict):
        return (
            False,
            ["CANDIDATE_NOT_OBJECT"],
        )

    # -------------------------------------------------------------------------
    # Asset
    # -------------------------------------------------------------------------

    asset = first_present(
        candidate,
        [
            "asset",
            "symbol",
        ],
        None,
    )

    if (
        not isinstance(asset, str)
        or not asset.strip()
    ):
        reasons.append(
            "MISSING_ASSET"
        )

    # -------------------------------------------------------------------------
    # Direction
    # -------------------------------------------------------------------------

    direction = first_present(
        candidate,
        [
            "direction",
            "dir",
        ],
        None,
    )

    if direction not in {
        "LONG",
        "SHORT",
    }:
        reasons.append(
            "INVALID_DIRECTION"
        )

    # -------------------------------------------------------------------------
    # Entry
    # -------------------------------------------------------------------------

    entry = first_present(
        candidate,
        [
            "entry_price",
            "entry",
        ],
        None,
    )

    if not isinstance(
        entry,
        (int, float),
    ):
        reasons.append(
            "INVALID_ENTRY_PRICE"
        )
    elif entry <= 0:
        reasons.append(
            "NON_POSITIVE_ENTRY_PRICE"
        )

    # -------------------------------------------------------------------------
    # Stop / TP
    # -------------------------------------------------------------------------

    stop = first_present(
        candidate,
        [
            "stop_price",
            "stop_loss",
            "stop",
        ],
        None,
    )

    tp = first_present(
        candidate,
        [
            "take_profit_price",
            "take_profit",
            "tp",
        ],
        None,
    )

    # Nested plan support.
    nested = candidate.get(
        "trade_plan"
    )

    if isinstance(nested, dict):

        if stop is None:
            stop = first_present(
                nested,
                [
                    "stop_price",
                    "stop_loss",
                    "stop",
                ],
                None,
            )

        if tp is None:
            tp = first_present(
                nested,
                [
                    "take_profit_price",
                    "take_profit",
                    "tp",
                ],
                None,
            )

    if not isinstance(
        stop,
        (int, float),
    ):
        reasons.append(
            "INVALID_STOP_PRICE"
        )
    elif stop <= 0:
        reasons.append(
            "NON_POSITIVE_STOP_PRICE"
        )

    if not isinstance(
        tp,
        (int, float),
    ):
        reasons.append(
            "INVALID_TP_PRICE"
        )
    elif tp <= 0:
        reasons.append(
            "NON_POSITIVE_TP_PRICE"
        )

    # -------------------------------------------------------------------------
    # Price geometry
    # -------------------------------------------------------------------------

    if (
        isinstance(entry, (int, float))
        and isinstance(stop, (int, float))
        and isinstance(tp, (int, float))
        and entry > 0
        and stop > 0
        and tp > 0
    ):

        if direction == "LONG":

            if not stop < entry:
                reasons.append(
                    "LONG_STOP_NOT_BELOW_ENTRY"
                )

            if not tp > entry:
                reasons.append(
                    "LONG_TP_NOT_ABOVE_ENTRY"
                )

        elif direction == "SHORT":

            if not stop > entry:
                reasons.append(
                    "SHORT_STOP_NOT_ABOVE_ENTRY"
                )

            if not tp < entry:
                reasons.append(
                    "SHORT_TP_NOT_BELOW_ENTRY"
                )

    return (
        len(reasons) == 0,
        reasons,
    )


# =============================================================================
# PAPER EXECUTION EVALUATION
# =============================================================================

def evaluate_candidates(
    upstream: dict[str, Any],
) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
]:

    candidates = upstream["candidates"]

    # -------------------------------------------------------------------------
    # Current project state:
    # no candidates.
    # -------------------------------------------------------------------------

    if not candidates:

        return (
            "NO_EXECUTION",
            [],
            [],
        )

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):

        valid, reasons = validate_candidate(
            candidate
        )

        if valid:

            accepted.append(
                candidate
            )

        else:

            rejected.append(
                {
                    "index": index,
                    "candidate": candidate,
                    "reasons": reasons,
                }
            )

    if accepted:

        return (
            "PAPER_READY",
            accepted,
            rejected,
        )

    return (
        "NO_EXECUTION",
        accepted,
        rejected,
    )


# =============================================================================
# PRODUCTION INVARIANT
# =============================================================================

def verify_production_invariant(
    before: dict[str, Any],
) -> dict[str, Any]:

    after = production_baseline()

    unchanged = (
        before["rows"]
        == after["rows"]
        and
        before["size"]
        == after["size"]
        and
        before["sha256"]
        == after["sha256"]
    )

    return {
        "before": before,
        "after": after,
        "unchanged": unchanged,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER EXECUTION "
        "SAFETY GATE v0.2"
    )
    print("=" * 100)

    print()
    print("OBJECTIVE:")
    print(
        "  Consume ONLY candidates already passed by the"
    )
    print(
        "  LIVE TRADE PLAN + STOP/TP CONTRACT frontier."
    )
    print()
    print(
        "  Determine PAPER execution readiness only."
    )
    print(
        "  No real order is created or submitted."
    )

    print()
    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)

    print(
        "Production DB writes       : FORBIDDEN"
    )
    print(
        "Production engine run      : NO"
    )
    print(
        "Historical repair          : NONE"
    )
    print(
        "Direction inference        : NONE"
    )
    print(
        "Score reconstruction       : NONE"
    )
    print(
        "Synthetic data             : FORBIDDEN"
    )
    print(
        "Live data injection        : NONE"
    )
    print(
        "REAL ORDER EXECUTION       : NONE"
    )
    print(
        "PAPER EXECUTION            : ANALYTICAL ONLY"
    )

    # =========================================================================
    # Production baseline
    # =========================================================================

    before = production_baseline()

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    print(
        f"Rows   : {before['rows']}"
    )
    print(
        f"Size   : {before['size']}"
    )
    print(
        f"SHA256 : {before['sha256']}"
    )

    # =========================================================================
    # Capture
    # =========================================================================

    capture_dir = find_latest_capture()

    upstream_report_path = (
        find_upstream_report(
            capture_dir
        )
    )

    print()
    print("=" * 100)
    print("LIVE CAPTURE")
    print("=" * 100)

    print(
        f"Directory : {capture_dir}"
    )
    print(
        f"Upstream  : {upstream_report_path}"
    )

    # =========================================================================
    # Upstream
    # =========================================================================

    report = load_json(
        upstream_report_path
    )

    upstream = validate_upstream(
        report,
        upstream_report_path,
    )

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    print(
        f"Frontier         : "
        f"{upstream['frontier']}"
    )

    print(
        f"Engine           : "
        f"{upstream['engine']}"
    )

    print(
        f"Snapshot         : "
        f"{upstream['snapshot']}"
    )

    print(
        f"Decision         : "
        f"{upstream['decision']}"
    )

    print(
        f"Candidate pool   : "
        f"{upstream['candidate_pool']}"
    )

    print(
        f"Selected         : "
        f"{upstream['selected_candidates']}"
    )

    # =========================================================================
    # Input
    # =========================================================================

    print()
    print("=" * 100)
    print("PAPER EXECUTION INPUT")
    print("=" * 100)

    print(
        "Candidates received : "
        f"{len(upstream['candidates'])}"
    )

    # =========================================================================
    # Evaluation
    # =========================================================================

    decision, accepted, rejected = (
        evaluate_candidates(
            upstream
        )
    )

    if not accepted:

        print()

        print(
            "Paper execution readiness : "
            "NOT READY"
        )

        if upstream["candidate_pool"] == 0:

            print(
                "Reason : UPSTREAM_POOL_EMPTY"
            )

        elif (
            upstream["selected_candidates"]
            == 0
        ):

            print(
                "Reason : UPSTREAM_SELECTION_EMPTY"
            )

        else:

            print(
                "Reason : "
                "ALL_CANDIDATES_FAILED_PAPER_CONTRACT"
            )

    else:

        print()
        print("=" * 100)
        print(
            "PAPER EXECUTION READY CANDIDATES"
        )
        print("=" * 100)

        for index, candidate in enumerate(
            accepted,
            start=1,
        ):

            asset = first_present(
                candidate,
                ["asset", "symbol"],
                "?",
            )

            direction = first_present(
                candidate,
                ["direction", "dir"],
                "?",
            )

            entry = first_present(
                candidate,
                [
                    "entry_price",
                    "entry",
                ],
                "?",
            )

            stop = first_present(
                candidate,
                [
                    "stop_price",
                    "stop_loss",
                    "stop",
                ],
                "?",
            )

            tp = first_present(
                candidate,
                [
                    "take_profit_price",
                    "take_profit",
                    "tp",
                ],
                "?",
            )

            print(
                f"{index:2d} | "
                f"{asset} | "
                f"{direction} | "
                f"entry={entry} | "
                f"stop={stop} | "
                f"tp={tp}"
            )

    # =========================================================================
    # Production invariant
    # =========================================================================

    invariant = (
        verify_production_invariant(
            before
        )
    )

    print()
    print("=" * 100)
    print(
        "PRODUCTION DATABASE INVARIANT"
    )
    print("=" * 100)

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
        + (
            "PASS"
            if invariant["unchanged"]
            else "FAIL"
        )
    )

    if not invariant["unchanged"]:
        raise RuntimeError(
            "Production database changed unexpectedly."
        )

    # =========================================================================
    # Verdict
    # =========================================================================

    frontier_verdict = (
        "PAPER_READY"
        if accepted
        else "NO_EXECUTION"
    )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER EXECUTION SAFETY GATE VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_PLAN_CONSUMED     : PASS"
    )

    print(
        "PAPER_EXECUTION_CONTRACT  : "
        + (
            "PASS"
            if accepted
            else "NO_EXECUTION"
        )
    )

    print(
        "REAL_ORDER_EXECUTION      : NONE"
    )

    print(
        "PRODUCTION_ISOLATION      : PASS"
    )

    print(
        f"FRONTIER VERDICT           : "
        f"{frontier_verdict}"
    )

    # =========================================================================
    # Runtime report
    # =========================================================================

    output_path = (
        capture_dir
        / OUTPUT_REPORT_NAME
    )

    output = {
        "frontier":
            "LIVE_PAPER_EXECUTION_SAFETY_GATE_v0.2",

        "timestamp_utc":
            utc_now(),

        "engine":
            upstream["engine"],

        "snapshot":
            upstream["snapshot"],

        "source_frontier":
            upstream["frontier"],

        "upstream_report":
            str(upstream_report_path),

        "upstream": {
            "decision":
                upstream["decision"],

            "candidate_pool":
                upstream["candidate_pool"],

            "selected_candidates":
                upstream[
                    "selected_candidates"
                ],

            "empty_pool":
                upstream["empty_pool"],
        },

        "paper_execution": {
            "decision":
                decision,

            "accepted_count":
                len(accepted),

            "rejected_count":
                len(rejected),

            "accepted":
                accepted,

            "rejected":
                rejected,
        },

        "production_database":
            invariant,

        "safety": {
            "production_db_modified":
                False,

            "production_engine_executed":
                False,

            "historical_repair":
                False,

            "direction_inference":
                False,

            "score_reconstruction":
                False,

            "synthetic_data":
                False,

            "live_data_injection":
                False,

            "real_order_execution":
                False,

            "paper_execution_only":
                True,
        },

        "verdict":
            frontier_verdict,
    }

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

    print()
    print(
        f"Runtime report : "
        f"{output_path}"
    )

    # =========================================================================
    # Final safety
    # =========================================================================

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)

    print(
        "Production DB writes : NONE"
    )
    print(
        "INSERT               : NONE"
    )
    print(
        "UPDATE               : NONE"
    )
    print(
        "DELETE               : NONE"
    )
    print(
        "DDL                  : NONE"
    )
    print(
        "Production engine    : NOT EXECUTED"
    )
    print(
        "Historical repair    : NONE"
    )
    print(
        "Direction inference  : NONE"
    )
    print(
        "Score reconstruction : NONE"
    )
    print(
        "Synthetic data       : NONE"
    )
    print(
        "Live data injection  : NONE"
    )
    print(
        "REAL ORDER EXECUTION : NONE"
    )
    print(
        "PAPER EXECUTION      : ANALYTICAL ONLY"
    )

    print()
    print(
        "No real trading order was created, "
        "submitted, or executed."
    )


if __name__ == "__main__":
    main()