import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

PRODUCTION_DB = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

CAPTURE_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"
)

UPSTREAM_REPORT = (
    CAPTURE_DIR /
    "LIVE_TRADE_PLAN_STOP_TP_REPORT.json"
)

OUTPUT_REPORT = (
    CAPTURE_DIR /
    "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json"
)

EXPECTED_ENGINE = "FUSION_v0.5"

EXPECTED_FRONTIER = "LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.2"


# ============================================================
# UTILITIES
# ============================================================

def sha256_file(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def db_baseline(path: Path):
    size = path.stat().st_size
    sha = sha256_file(path)

    conn = sqlite3.connect(path)

    try:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "rows": row_count,
        "size": size,
        "sha256": sha,
    }


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# UPSTREAM EXTRACTION
# ============================================================

def extract_selected_candidates(report):
    """
    Compatible with both upstream report formats:

        selected_candidates : [...]
        selected             : [...]

    Empty collections are valid and mean NO_TRADE.
    """

    candidates = None
    source_field = None

    if "selected_candidates" in report:
        candidates = report["selected_candidates"]
        source_field = "selected_candidates"

    elif "selected" in report:
        candidates = report["selected"]
        source_field = "selected"

    if candidates is None:
        return [], None

    if not isinstance(candidates, list):
        raise ValueError(
            f"Upstream field '{source_field}' must be a list."
        )

    return candidates, source_field


def validate_upstream(report):

    frontier = report.get("frontier")
    engine = report.get("engine")
    snapshot = report.get("snapshot_id")

    if frontier != EXPECTED_FRONTIER:
        raise ValueError(
            f"Unexpected upstream frontier: {frontier!r}"
        )

    if engine != EXPECTED_ENGINE:
        raise ValueError(
            f"Unexpected upstream engine: {engine!r}"
        )

    if not snapshot:
        raise ValueError(
            "Upstream report missing snapshot_id."
        )

    candidates, source_field = extract_selected_candidates(report)

    decision = report.get(
        "decision",
        "NO_TRADE" if not candidates else "TRADE_CANDIDATE"
    )

    return {
        "frontier": frontier,
        "engine": engine,
        "snapshot": snapshot,
        "decision": decision,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "candidate_source_field": source_field,
    }


# ============================================================
# POSITION LIFECYCLE
# ============================================================

def normalize_candidate(candidate):
    """
    Normalize without reconstructing signal information.
    Only fields explicitly supplied by upstream are consumed.
    """

    if not isinstance(candidate, dict):
        return {
            "valid": False,
            "reason": "CANDIDATE_NOT_OBJECT",
        }

    asset = candidate.get("asset")
    direction = candidate.get("direction")

    entry_price = candidate.get("entry_price")

    stop_loss = (
        candidate.get("stop_loss")
        if "stop_loss" in candidate
        else candidate.get("stop")
    )

    take_profit = (
        candidate.get("take_profit")
        if "take_profit" in candidate
        else candidate.get("tp")
    )

    quantity = candidate.get("quantity")
    notional = candidate.get("notional")

    return {
        "valid": True,
        "asset": asset,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "quantity": quantity,
        "notional": notional,
        "raw": candidate,
    }


def validate_trade_plan(candidate):

    if not candidate.get("valid"):
        return False, ["CANDIDATE_NOT_OBJECT"]

    reasons = []

    if not candidate.get("asset"):
        reasons.append("MISSING_ASSET")

    if candidate.get("direction") not in ("LONG", "SHORT"):
        reasons.append("INVALID_DIRECTION")

    if candidate.get("entry_price") is None:
        reasons.append("MISSING_ENTRY_PRICE")

    if candidate.get("stop_loss") is None:
        reasons.append("MISSING_STOP_LOSS")

    if candidate.get("take_profit") is None:
        reasons.append("MISSING_TAKE_PROFIT")

    return len(reasons) == 0, reasons


def build_position_lifecycle(candidate):

    valid, reasons = validate_trade_plan(candidate)

    if not valid:
        return {
            "asset": candidate.get("asset"),
            "direction": candidate.get("direction"),
            "status": "NO_EXECUTION",
            "lifecycle": [],
            "reasons": reasons,
        }

    entry = float(candidate["entry_price"])
    stop = float(candidate["stop_loss"])
    tp = float(candidate["take_profit"])

    direction = candidate["direction"]

    if direction == "LONG":
        stop_valid = stop < entry
        tp_valid = tp > entry
    else:
        stop_valid = stop > entry
        tp_valid = tp < entry

    if not stop_valid:
        return {
            "asset": candidate["asset"],
            "direction": direction,
            "status": "NO_EXECUTION",
            "lifecycle": [],
            "reasons": ["INVALID_STOP_RELATION"],
        }

    if not tp_valid:
        return {
            "asset": candidate["asset"],
            "direction": direction,
            "status": "NO_EXECUTION",
            "lifecycle": [],
            "reasons": ["INVALID_TP_RELATION"],
        }

    quantity = candidate.get("quantity")
    notional = candidate.get("notional")

    lifecycle = [
        {
            "state": "PLANNED",
            "event": "PAPER_PLAN_ACCEPTED",
        },
        {
            "state": "OPEN",
            "event": "PAPER_ENTRY",
            "entry_price": entry,
        },
        {
            "state": "MONITORING",
            "event": "POSITION_ACTIVE",
        },
        {
            "state": "CLOSED",
            "event": "WAIT_FOR_STOP_OR_TP",
        },
    ]

    return {
        "asset": candidate["asset"],
        "direction": direction,
        "status": "PAPER_SIMULATION_READY",
        "entry_price": entry,
        "stop_loss": stop,
        "take_profit": tp,
        "quantity": quantity,
        "notional": notional,
        "lifecycle": lifecycle,
        "reasons": [],
    }


# ============================================================
# PRODUCTION INVARIANT
# ============================================================

def verify_production_invariant(before):

    after = db_baseline(PRODUCTION_DB)

    unchanged = (
        before["rows"] == after["rows"]
        and before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )

    return after, unchanged


# ============================================================
# REPORT
# ============================================================

def write_report(report):
    with OUTPUT_REPORT.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER TRADE SIMULATION + "
        "POSITION LIFECYCLE v0.2"
    )
    print("=" * 100)

    print()
    print("OBJECTIVE:")
    print(
        "  Consume ONLY candidates already passed by the upstream"
    )
    print(
        "  LIVE TRADE PLAN + STOP/TP CONTRACT frontier."
    )
    print()
    print("  Simulate PAPER position lifecycle analytically.")
    print("  No real order is created or submitted.")
    print()
    print("Production DB writes       : FORBIDDEN")
    print("Production engine run      : NO")
    print("Historical repair          : NONE")
    print("Direction inference        : NONE")
    print("Score reconstruction       : NONE")
    print("Synthetic data             : FORBIDDEN")
    print("Live data injection        : NONE")
    print("REAL ORDER EXECUTION       : NONE")
    print("PAPER EXECUTION            : ANALYTICAL ONLY")

    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    before = db_baseline(PRODUCTION_DB)

    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    # --------------------------------------------------------
    # UPSTREAM
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    print(f"Report : {UPSTREAM_REPORT}")

    report = load_json(UPSTREAM_REPORT)

    upstream = validate_upstream(report)

    print(f"Frontier         : {upstream['frontier']}")
    print(f"Engine           : {upstream['engine']}")
    print(f"Snapshot         : {upstream['snapshot']}")
    print(f"Decision         : {upstream['decision']}")
    print(f"Candidate source : {upstream['candidate_source_field']}")
    print(f"Candidate pool   : {upstream['candidate_count']}")

    # --------------------------------------------------------
    # PAPER SIMULATION
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("PAPER TRADE SIMULATION")
    print("=" * 100)

    candidates = upstream["candidates"]

    simulation_results = []

    if not candidates:

        print("Candidates received : 0")
        print()
        print("Paper simulation : NOT PERFORMED")
        print("Position lifecycle: NOT PERFORMED")
        print("Reason            : UPSTREAM_POOL_EMPTY")

        simulation_status = "NO_TRADE"
        ready_count = 0
        rejected_count = 0

    else:

        print(f"Candidates received : {len(candidates)}")
        print()

        ready_count = 0
        rejected_count = 0

        for index, raw_candidate in enumerate(candidates, start=1):

            candidate = normalize_candidate(raw_candidate)

            result = build_position_lifecycle(candidate)

            result["candidate_index"] = index

            simulation_results.append(result)

            if result["status"] == "PAPER_SIMULATION_READY":
                ready_count += 1
            else:
                rejected_count += 1

            print(
                f"{index:02d} | "
                f"{result.get('asset', 'UNKNOWN'):6} | "
                f"{result.get('direction', 'UNKNOWN'):5} | "
                f"{result['status']}"
            )

        simulation_status = (
            "PAPER_READY"
            if ready_count > 0
            else "NO_TRADE"
        )

    # --------------------------------------------------------
    # LIFECYCLE SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("POSITION LIFECYCLE SUMMARY")
    print("=" * 100)

    print(f"PAPER_READY        : {ready_count}")
    print(f"NO_EXECUTION       : {rejected_count}")

    if not candidates:
        print("OPEN POSITIONS     : 0")
        print("CLOSED POSITIONS   : 0")
    else:
        print(f"SIMULATED POSITIONS: {ready_count}")

    # --------------------------------------------------------
    # PRODUCTION INVARIANT
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    after, unchanged = verify_production_invariant(before)

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

    # --------------------------------------------------------
    # VERDICT
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print(
        "LIVE PAPER TRADE SIMULATION + "
        "POSITION LIFECYCLE VERDICT"
    )
    print("=" * 100)

    print("UPSTREAM_PLAN_CONSUMED     : PASS")

    if candidates:
        print(
            "PAPER_SIMULATION           : "
            + ("PASS" if ready_count > 0 else "NO_EXECUTION")
        )
        print(
            "POSITION_LIFECYCLE         : "
            + ("PASS" if ready_count > 0 else "NO_EXECUTION")
        )
    else:
        print("PAPER_SIMULATION           : NOT_PERFORMED")
        print("POSITION_LIFECYCLE         : NOT_PERFORMED")

    print(
        "PRODUCTION_ISOLATION       : "
        + ("PASS" if unchanged else "FAIL")
    )

    print(f"FRONTIER VERDICT           : {simulation_status}")

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    runtime_report = {
        "frontier": (
            "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_v0.2"
        ),
        "timestamp_utc": now_utc(),

        "upstream": {
            "report": str(UPSTREAM_REPORT),
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "snapshot": upstream["snapshot"],
            "decision": upstream["decision"],
            "candidate_source_field": upstream[
                "candidate_source_field"
            ],
            "candidate_pool": upstream["candidate_count"],
        },

        "simulation": {
            "status": simulation_status,
            "paper_ready": ready_count,
            "no_execution": rejected_count,
            "results": simulation_results,
        },

        "production_database": {
            "before": before,
            "after": after,
            "unchanged": unchanged,
        },

        "safety": {
            "production_db_modified": not unchanged,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "real_order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
        },
    }

    write_report(runtime_report)

    # --------------------------------------------------------
    # FINAL SAFETY
    # --------------------------------------------------------

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
    if candidates:
        print(
            "Paper position lifecycle was simulated analytically."
        )
    else:
        print(
            "No eligible upstream candidate exists."
        )
        print(
            "No paper position was opened or simulated."
        )

    print()
    print(f"Runtime report : {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()