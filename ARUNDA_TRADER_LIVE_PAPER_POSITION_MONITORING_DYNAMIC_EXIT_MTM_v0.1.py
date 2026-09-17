# -*- coding: utf-8 -*-

"""
ARUNDA TRADER LIVE PAPER POSITION MONITORING + DYNAMIC EXIT / MARK-TO-MARKET v0.1

Purpose
-------
Analytically monitor PAPER positions from the upstream lifecycle/outcome
frontiers and evaluate dynamic exit / mark-to-market state.

Safety
------
- Production DB is READ ONLY.
- Production engine is NOT executed.
- No historical repair.
- No direction inference.
- No score reconstruction.
- No synthetic/live data injection.
- No real order execution.
- No production writes.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.1"

PRODUCTION_DB = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

CAPTURE_ROOT = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_DIR",
        r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
    )
)

OUTCOME_REPORT = (
    CAPTURE_ROOT
    / "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json"
)

LIFECYCLE_REPORT = (
    CAPTURE_ROOT
    / "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json"
)

OUTPUT_REPORT = (
    CAPTURE_ROOT
    / "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def db_baseline(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    digest = sha256_file(path)

    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]

    return {
        "rows": rows,
        "size": size,
        "sha256": digest,
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Report root must be an object: {path}")

    return data


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def normalize_candidates(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Accept candidate collections emitted by the existing upstream reports.

    Supported forms:
      selected
      selected_candidates
      candidates
      eligible_pool
      candidate_pool
    """

    candidates = first_present(
        report,
        "selected",
        "selected_candidates",
        "candidates",
        "eligible_pool",
        "candidate_pool",
    )

    if candidates is None:
        return []

    if isinstance(candidates, list):
        return [
            x for x in candidates
            if isinstance(x, dict)
        ]

    if isinstance(candidates, dict):
        return [candidates]

    if isinstance(candidates, int):
        return []

    raise ValueError(
        "Upstream candidate collection must be a list, dict, "
        "or integer count."
    )


def extract_snapshot(report: dict[str, Any]) -> str | None:
    value = first_present(
        report,
        "snapshot",
        "snapshot_id",
    )

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        nested = first_present(
            value,
            "id",
            "snapshot_id",
        )
        if isinstance(nested, str):
            return nested

    return None


def validate_upstream(
    report: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:

    frontier = report.get("frontier")

    if not frontier:
        raise ValueError(
            f"Upstream report missing frontier: {report_path}"
        )

    engine = report.get("engine")

    if engine is not None and engine != "FUSION_v0.5":
        raise ValueError(
            f"Unexpected upstream engine: {engine}"
        )

    snapshot = extract_snapshot(report)

    candidates = normalize_candidates(report)

    candidate_pool = report.get("candidate_pool")

    if isinstance(candidate_pool, int):
        declared_pool = candidate_pool
    else:
        declared_pool = len(candidates)

    selected_count = report.get("selected_candidates")

    if isinstance(selected_count, int):
        declared_selected = selected_count
    else:
        declared_selected = len(candidates)

    decision = report.get("decision")

    if declared_pool == 0 and candidates:
        raise ValueError(
            "Upstream candidate_pool=0 but candidate collection is non-empty."
        )

    return {
        "report": str(report_path),
        "frontier": frontier,
        "engine": engine,
        "snapshot": snapshot,
        "decision": decision,
        "candidate_pool": declared_pool,
        "selected_count": declared_selected,
        "candidates": candidates,
    }


def candidate_identity(candidate: dict[str, Any]) -> str:
    for key in (
        "id",
        "candidate_id",
        "signal_id",
        "position_id",
    ):
        value = candidate.get(key)
        if value is not None:
            return str(value)

    asset = candidate.get("asset", "UNKNOWN")
    timestamp = candidate.get("timestamp", "")
    return f"{asset}:{timestamp}"


def get_float(
    data: dict[str, Any],
    *keys: str,
) -> float | None:

    value = first_present(data, *keys)

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_direction(candidate: dict[str, Any]) -> str:
    value = first_present(
        candidate,
        "direction",
        "side",
    )

    if value is None:
        return "UNKNOWN"

    value = str(value).upper()

    if value in {"LONG", "SHORT", "FLAT"}:
        return value

    return "UNKNOWN"


def mark_to_market(
    direction: str,
    entry_price: float,
    current_price: float,
) -> float:

    if direction == "LONG":
        return ((current_price - entry_price) / entry_price) * 100.0

    if direction == "SHORT":
        return ((entry_price - current_price) / entry_price) * 100.0

    return 0.0


def dynamic_exit_state(
    candidate: dict[str, Any],
    mtm_pct: float,
) -> tuple[str, list[str]]:

    direction = get_direction(candidate)

    stop_price = get_float(
        candidate,
        "stop_price",
        "stop_loss",
        "stop",
    )

    take_profit = get_float(
        candidate,
        "take_profit",
        "tp_price",
        "tp",
    )

    current_price = get_float(
        candidate,
        "current_price",
        "mark_price",
        "market_price",
        "last_price",
    )

    reasons: list[str] = []

    if direction == "FLAT":
        return "NO_TRADE", ["FLAT_DIRECTION"]

    if current_price is None:
        return "MONITOR_ONLY", ["CURRENT_PRICE_UNAVAILABLE"]

    if stop_price is not None:
        if direction == "LONG" and current_price <= stop_price:
            reasons.append("STOP_LOSS_TRIGGERED")

        if direction == "SHORT" and current_price >= stop_price:
            reasons.append("STOP_LOSS_TRIGGERED")

    if take_profit is not None:
        if direction == "LONG" and current_price >= take_profit:
            reasons.append("TAKE_PROFIT_TRIGGERED")

        if direction == "SHORT" and current_price <= take_profit:
            reasons.append("TAKE_PROFIT_TRIGGERED")

    if "STOP_LOSS_TRIGGERED" in reasons:
        return "EXIT_STOP", reasons

    if "TAKE_PROFIT_TRIGGERED" in reasons:
        return "EXIT_TP", reasons

    if mtm_pct < 0:
        return "OPEN_LOSS", ["MARK_TO_MARKET_NEGATIVE"]

    if mtm_pct > 0:
        return "OPEN_PROFIT", ["MARK_TO_MARKET_POSITIVE"]

    return "OPEN_FLAT", ["MARK_TO_MARKET_ZERO"]


def inspect_candidates(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:

    results: list[dict[str, Any]] = []

    counters = {
        "paper_positions": 0,
        "monitorable": 0,
        "mtm_available": 0,
        "exit_triggered": 0,
        "stop_exits": 0,
        "tp_exits": 0,
        "open_profit": 0,
        "open_loss": 0,
        "open_flat": 0,
        "monitor_only": 0,
        "no_trade": 0,
        "invalid": 0,
    }

    for candidate in candidates:
        counters["paper_positions"] += 1

        identity = candidate_identity(candidate)

        direction = get_direction(candidate)

        entry_price = get_float(
            candidate,
            "entry_price",
            "entry",
        )

        current_price = get_float(
            candidate,
            "current_price",
            "mark_price",
            "market_price",
            "last_price",
        )

        stop_price = get_float(
            candidate,
            "stop_price",
            "stop_loss",
            "stop",
        )

        take_profit = get_float(
            candidate,
            "take_profit",
            "tp_price",
            "tp",
        )

        result: dict[str, Any] = {
            "candidate_id": identity,
            "asset": candidate.get("asset"),
            "direction": direction,
            "entry_price": entry_price,
            "current_price": current_price,
            "stop_price": stop_price,
            "take_profit": take_profit,
            "mark_to_market_pct": None,
            "state": "INVALID",
            "exit_reasons": [],
        }

        if direction not in {"LONG", "SHORT"}:
            if direction == "FLAT":
                result["state"] = "NO_TRADE"
                result["exit_reasons"] = ["FLAT_DIRECTION"]
                counters["no_trade"] += 1
            else:
                counters["invalid"] += 1

            results.append(result)
            continue

        if entry_price is None or entry_price <= 0:
            result["state"] = "INVALID"
            result["exit_reasons"] = ["INVALID_ENTRY_PRICE"]
            counters["invalid"] += 1
            results.append(result)
            continue

        counters["monitorable"] += 1

        if current_price is None or current_price <= 0:
            result["state"] = "MONITOR_ONLY"
            result["exit_reasons"] = [
                "CURRENT_PRICE_UNAVAILABLE"
            ]
            counters["monitor_only"] += 1
            results.append(result)
            continue

        counters["mtm_available"] += 1

        mtm = mark_to_market(
            direction,
            entry_price,
            current_price,
        )

        result["mark_to_market_pct"] = mtm

        state, reasons = dynamic_exit_state(
            candidate,
            mtm,
        )

        result["state"] = state
        result["exit_reasons"] = reasons

        if state in {"EXIT_STOP", "EXIT_TP"}:
            counters["exit_triggered"] += 1

        if state == "EXIT_STOP":
            counters["stop_exits"] += 1

        elif state == "EXIT_TP":
            counters["tp_exits"] += 1

        elif state == "OPEN_PROFIT":
            counters["open_profit"] += 1

        elif state == "OPEN_LOSS":
            counters["open_loss"] += 1

        elif state == "OPEN_FLAT":
            counters["open_flat"] += 1

        results.append(result)

    return results, counters


def print_header():
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER POSITION MONITORING "
        "+ DYNAMIC EXIT / MARK-TO-MARKET v0.1"
    )
    print("=" * 100)

    print("""
OBJECTIVE:
  Monitor ONLY PAPER positions originating from the verified
  upstream trade lifecycle.

  Evaluate:
    - position state
    - mark-to-market
    - dynamic stop/TP state
    - exit trigger state

No real order is created or submitted.
""")


def main():

    print_header()

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    before = db_baseline(PRODUCTION_DB)

    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    print()
    print("=" * 100)
    print("LIVE CAPTURE")
    print("=" * 100)
    print(f"Directory : {CAPTURE_ROOT}")
    print(f"Outcome   : {OUTCOME_REPORT}")
    print(f"Lifecycle : {LIFECYCLE_REPORT}")

    upstream_path = OUTCOME_REPORT

    if not upstream_path.exists():
        upstream_path = LIFECYCLE_REPORT

    if not upstream_path.exists():
        raise FileNotFoundError(
            "Neither outcome nor lifecycle report exists."
        )

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Report : {upstream_path}")

    report = load_json(upstream_path)

    upstream = validate_upstream(
        report,
        upstream_path,
    )

    print(f"Frontier : {upstream['frontier']}")
    print(f"Engine   : {upstream['engine']}")
    print(f"Snapshot : {upstream['snapshot']}")
    print(f"Decision : {upstream['decision']}")
    print(f"Candidate pool : {upstream['candidate_pool']}")

    candidates = upstream["candidates"]

    print()
    print("=" * 100)
    print("PAPER POSITION MONITORING")
    print("=" * 100)
    print(f"Positions received : {len(candidates)}")

    if not candidates:
        print()
        print("Monitoring : NOT PERFORMED")
        print("Dynamic exit : NOT PERFORMED")
        print("Mark-to-market : NOT PERFORMED")
        print("Reason : UPSTREAM_POOL_EMPTY")

        results = []
        counters = {
            "paper_positions": 0,
            "monitorable": 0,
            "mtm_available": 0,
            "exit_triggered": 0,
            "stop_exits": 0,
            "tp_exits": 0,
            "open_profit": 0,
            "open_loss": 0,
            "open_flat": 0,
            "monitor_only": 0,
            "no_trade": 0,
            "invalid": 0,
        }

        frontier_verdict = "NO_TRADE"

    else:
        results, counters = inspect_candidates(
            candidates
        )

        frontier_verdict = (
            "EXIT_SIGNAL"
            if counters["exit_triggered"] > 0
            else "MONITORING_ACTIVE"
        )

        print()
        print(
            "ID | ASSET | DIR | ENTRY | CURRENT | MTM % | STATE"
        )
        print("-" * 100)

        for row in results:
            print(
                f"{row['candidate_id']} | "
                f"{row['asset']} | "
                f"{row['direction']} | "
                f"{row['entry_price']} | "
                f"{row['current_price']} | "
                f"{row['mark_to_market_pct']} | "
                f"{row['state']}"
            )

    print()
    print("=" * 100)
    print("POSITION MONITORING SUMMARY")
    print("=" * 100)

    print(f"PAPER POSITIONS       : {counters['paper_positions']}")
    print(f"MONITORABLE           : {counters['monitorable']}")
    print(f"MTM AVAILABLE         : {counters['mtm_available']}")
    print(f"EXIT TRIGGERS         : {counters['exit_triggered']}")
    print(f"STOP LOSS EXITS       : {counters['stop_exits']}")
    print(f"TAKE PROFIT EXITS     : {counters['tp_exits']}")
    print(f"OPEN PROFIT           : {counters['open_profit']}")
    print(f"OPEN LOSS             : {counters['open_loss']}")
    print(f"OPEN FLAT             : {counters['open_flat']}")
    print(f"MONITOR ONLY          : {counters['monitor_only']}")
    print(f"NO TRADE              : {counters['no_trade']}")
    print(f"INVALID               : {counters['invalid']}")

    after = db_baseline(PRODUCTION_DB)

    unchanged = before == after

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(f"Before rows : {before['rows']}")
    print(f"After rows  : {after['rows']}")
    print(f"Before size : {before['size']}")
    print(f"After size  : {after['size']}")
    print(f"Before SHA256 : {before['sha256']}")
    print(f"After SHA256  : {after['sha256']}")
    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if unchanged else "FAIL")
    )

    if not unchanged:
        raise RuntimeError(
            "Production DB invariant violated."
        )

    report_out = {
        "frontier": (
            "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_v0.1"
        ),
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "upstream": {
            "report": str(upstream_path),
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "snapshot": upstream["snapshot"],
            "decision": upstream["decision"],
            "candidate_pool": upstream["candidate_pool"],
            "selected_count": upstream["selected_count"],
        },

        "monitoring": {
            "counters": counters,
            "positions": results,
            "frontier_verdict": frontier_verdict,
        },

        "production_database": {
            "before": before,
            "after": after,
            "unchanged": unchanged,
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
            "paper_execution": "analytical_only",
        },
    }

    CAPTURE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report_out,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER POSITION MONITORING "
        "+ DYNAMIC EXIT / MARK-TO-MARKET VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_POSITION_SOURCE : PASS"
    )
    print(
        "POSITION_MONITORING     : "
        + (
            "NOT_PERFORMED"
            if not candidates
            else "PASS"
        )
    )
    print(
        "MARK_TO_MARKET           : "
        + (
            "NOT_PERFORMED"
            if not candidates
            else "PASS"
        )
    )
    print(
        "DYNAMIC_EXIT             : "
        + (
            "NOT_PERFORMED"
            if not candidates
            else "PASS"
        )
    )
    print(
        "PRODUCTION_ISOLATION     : PASS"
    )
    print(
        f"FRONTIER VERDICT         : {frontier_verdict}"
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
    print("REAL ORDER EXECUTION : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")

    print()
    print(
        "Runtime report : "
        f"{OUTPUT_REPORT}"
    )

    print()
    print(
        "No real trading order was created, "
        "submitted, or executed."
    )


if __name__ == "__main__":
    main()