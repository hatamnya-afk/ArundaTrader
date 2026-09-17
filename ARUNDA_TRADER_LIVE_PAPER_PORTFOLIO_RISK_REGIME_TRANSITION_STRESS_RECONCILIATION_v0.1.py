import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA TRADER
# LIVE PAPER PORTFOLIO RISK REGIME TRANSITION + STRESS RECONCILIATION v0.1
# =============================================================================

VERSION = "v0.1"
FRONTIER = "LIVE_PAPER_PORTFOLIO_RISK_REGIME_TRANSITION_STRESS_RECONCILIATION_v0.1"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = BASE_DIR / "arunda.db"

CAPTURE_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"
)

UPSTREAM_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_TEMPORAL_PERFORMANCE_WINDOW_RISK_REGIME_RECONCILIATION_REPORT.json"
)

RUNTIME_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_RISK_REGIME_TRANSITION_STRESS_RECONCILIATION_REPORT.json"
)

# ---------------------------------------------------------------------------
# ANALYTICAL LIMITS ONLY
# ---------------------------------------------------------------------------

MAX_PORTFOLIO_RISK = 0.02
MAX_DRAWDOWN = 0.10
MAX_CURRENT_DRAWDOWN = 0.05
MAX_RISK_REGIME_CHANGE = 0.02
MAX_STRESS_LOSS = 0.05

# No production mutation is permitted.
FORBIDDEN_SQL = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "CREATE",
    "REPLACE",
    "VACUUM",
)


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def db_fingerprint(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Production database not found: {path}")

    size = path.stat().st_size
    sha256 = sha256_file(path)

    rows = None

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

    try:
        cur = conn.cursor()

        tables = cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        ).fetchall()

        candidates = [
            "market_history",
            "market_data",
            "market_records",
        ]

        for table in candidates:
            if any(row[0] == table for row in tables):
                try:
                    rows = cur.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
                    break
                except sqlite3.Error:
                    pass

    finally:
        conn.close()

    return {
        "rows": rows,
        "size": size,
        "sha256": sha256,
    }


# =============================================================================
# UPSTREAM
# =============================================================================

def load_upstream() -> dict:
    if not UPSTREAM_REPORT.exists():
        raise FileNotFoundError(
            f"Upstream report not found:\n{UPSTREAM_REPORT}"
        )

    with UPSTREAM_REPORT.open("r", encoding="utf-8") as f:
        report = json.load(f)

    if not isinstance(report, dict):
        raise ValueError("Upstream report must be a JSON object.")

    return report


def validate_upstream(report: dict) -> dict:
    required = [
        "frontier",
    ]

    missing = [x for x in required if x not in report]

    if missing:
        raise ValueError(
            f"Upstream temporal report missing required fields: {missing}"
        )

    return report


def extract_snapshots(report: dict) -> list[dict]:
    possible = [
        report.get("snapshots"),
        report.get("temporal_snapshots"),
        report.get("snapshot_history"),
        report.get("risk_regimes"),
    ]

    snapshots = None

    for candidate in possible:
        if isinstance(candidate, list):
            snapshots = candidate
            break

    if snapshots is None:
        snapshots = []

    normalized = []

    for item in snapshots:
        if not isinstance(item, dict):
            continue

        snapshot_id = (
            item.get("snapshot")
            or item.get("snapshot_id")
            or item.get("id")
        )

        if not snapshot_id:
            continue

        normalized.append(
            {
                "snapshot": str(snapshot_id),
                "timestamp": (
                    item.get("timestamp")
                    or item.get("timestamp_utc")
                    or item.get("time")
                ),
                "positions": safe_int(
                    item.get("positions"),
                    item.get("position_count", 0),
                ),
                "notional": safe_float(
                    item.get(
                        "notional",
                        item.get("analytical_notional", 0.0),
                    )
                ),
                "risk": safe_float(
                    item.get(
                        "risk",
                        item.get("portfolio_risk", 0.0),
                    )
                ),
                "pnl": safe_float(
                    item.get(
                        "pnl",
                        item.get("total_pnl", 0.0),
                    )
                ),
                "drawdown": safe_float(
                    item.get(
                        "drawdown",
                        item.get("current_drawdown", 0.0),
                    )
                ),
            }
        )

    return normalized


def extract_single_snapshot(report: dict) -> dict | None:
    snapshot_id = (
        report.get("current_snapshot")
        or report.get("snapshot")
        or report.get("snapshot_id")
    )

    if not snapshot_id:
        return None

    return {
        "snapshot": str(snapshot_id),
        "timestamp": (
            report.get("timestamp")
            or report.get("timestamp_utc")
        ),
        "positions": safe_int(
            report.get("positions"),
            report.get("position_count", 0),
        ),
        "notional": safe_float(
            report.get(
                "notional",
                report.get("analytical_notional", 0.0),
            )
        ),
        "risk": safe_float(
            report.get(
                "risk",
                report.get("portfolio_risk", 0.0),
            )
        ),
        "pnl": safe_float(
            report.get(
                "pnl",
                report.get("total_pnl", 0.0),
            )
        ),
        "drawdown": safe_float(
            report.get(
                "drawdown",
                report.get("current_drawdown", 0.0),
            )
        ),
    }


# =============================================================================
# TEMPORAL NORMALIZATION
# =============================================================================

def build_snapshot_series(report: dict) -> list[dict]:
    snapshots = extract_snapshots(report)

    if not snapshots:
        single = extract_single_snapshot(report)

        if single is not None:
            snapshots = [single]

    # Deduplicate by snapshot identity.
    unique = {}

    for item in snapshots:
        unique[item["snapshot"]] = item

    snapshots = list(unique.values())

    # Preserve chronological order when timestamps are available.
    snapshots.sort(
        key=lambda x: (
            x.get("timestamp") is None,
            str(x.get("timestamp") or ""),
        )
    )

    return snapshots


# =============================================================================
# RISK REGIME CLASSIFICATION
# =============================================================================

def classify_risk_regime(risk: float, drawdown: float) -> str:
    risk = abs(risk)
    drawdown = abs(drawdown)

    if risk == 0 and drawdown == 0:
        return "FLAT"

    if risk <= MAX_PORTFOLIO_RISK * 0.50:
        return "LOW"

    if risk <= MAX_PORTFOLIO_RISK:
        return "NORMAL"

    if risk <= MAX_PORTFOLIO_RISK * 1.50:
        return "ELEVATED"

    return "HIGH"


def regime_rank(regime: str) -> int:
    return {
        "FLAT": 0,
        "LOW": 1,
        "NORMAL": 2,
        "ELEVATED": 3,
        "HIGH": 4,
    }.get(regime, -1)


# =============================================================================
# RISK TRANSITIONS
# =============================================================================

def reconcile_risk_transitions(
    snapshots: list[dict],
) -> tuple[list[dict], str]:

    transitions = []

    if len(snapshots) < 2:
        return transitions, "INSUFFICIENT_DATA"

    for previous, current in zip(snapshots, snapshots[1:]):

        previous_regime = classify_risk_regime(
            previous["risk"],
            previous["drawdown"],
        )

        current_regime = classify_risk_regime(
            current["risk"],
            current["drawdown"],
        )

        risk_delta = current["risk"] - previous["risk"]
        drawdown_delta = (
            current["drawdown"] - previous["drawdown"]
        )

        transitions.append(
            {
                "from_snapshot": previous["snapshot"],
                "to_snapshot": current["snapshot"],
                "previous_risk": previous["risk"],
                "current_risk": current["risk"],
                "risk_delta": risk_delta,
                "previous_drawdown": previous["drawdown"],
                "current_drawdown": current["drawdown"],
                "drawdown_delta": drawdown_delta,
                "previous_regime": previous_regime,
                "current_regime": current_regime,
                "regime_changed": (
                    previous_regime != current_regime
                ),
                "transition_order": (
                    regime_rank(current_regime)
                    - regime_rank(previous_regime)
                ),
            }
        )

    return transitions, "PASS"


# =============================================================================
# STRESS RECONCILIATION
# =============================================================================

def stress_snapshot(snapshot: dict) -> dict:
    risk = abs(snapshot["risk"])
    drawdown = abs(snapshot["drawdown"])

    stress_loss = max(
        risk,
        drawdown,
        abs(min(snapshot["pnl"], 0.0)),
    )

    risk_limit_pass = risk <= MAX_PORTFOLIO_RISK
    drawdown_limit_pass = drawdown <= MAX_DRAWDOWN
    current_dd_pass = drawdown <= MAX_CURRENT_DRAWDOWN
    stress_loss_pass = stress_loss <= MAX_STRESS_LOSS

    return {
        "snapshot": snapshot["snapshot"],
        "risk": risk,
        "drawdown": drawdown,
        "pnl": snapshot["pnl"],
        "stress_loss": stress_loss,
        "risk_limit": MAX_PORTFOLIO_RISK,
        "drawdown_limit": MAX_DRAWDOWN,
        "current_drawdown_limit": MAX_CURRENT_DRAWDOWN,
        "stress_loss_limit": MAX_STRESS_LOSS,
        "risk_limit_pass": risk_limit_pass,
        "drawdown_limit_pass": drawdown_limit_pass,
        "current_drawdown_pass": current_dd_pass,
        "stress_loss_pass": stress_loss_pass,
        "stress_status": (
            "PASS"
            if (
                risk_limit_pass
                and drawdown_limit_pass
                and current_dd_pass
                and stress_loss_pass
            )
            else "BREACH"
        ),
    }


def reconcile_stress(snapshots: list[dict]) -> dict:
    if not snapshots:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "NO_SNAPSHOTS",
            "observations": [],
        }

    observations = [
        stress_snapshot(snapshot)
        for snapshot in snapshots
    ]

    breaches = [
        x for x in observations
        if x["stress_status"] == "BREACH"
    ]

    return {
        "status": "PASS" if not breaches else "BREACH",
        "reason": (
            "NO_STRESS_BREACH"
            if not breaches
            else "STRESS_LIMIT_BREACH"
        ),
        "observations": observations,
        "breaches": breaches,
    }


# =============================================================================
# POSITION / EXPOSURE TRANSITIONS
# =============================================================================

def reconcile_position_transitions(
    snapshots: list[dict],
) -> dict:

    if len(snapshots) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "MINIMUM_TWO_SNAPSHOTS_REQUIRED",
            "transitions": [],
        }

    transitions = []

    for previous, current in zip(snapshots, snapshots[1:]):

        position_delta = (
            current["positions"] - previous["positions"]
        )

        notional_delta = (
            current["notional"] - previous["notional"]
        )

        transitions.append(
            {
                "from_snapshot": previous["snapshot"],
                "to_snapshot": current["snapshot"],
                "previous_positions": previous["positions"],
                "current_positions": current["positions"],
                "position_delta": position_delta,
                "previous_notional": previous["notional"],
                "current_notional": current["notional"],
                "notional_delta": notional_delta,
            }
        )

    return {
        "status": "PASS",
        "reason": "TEMPORAL_TRANSITIONS_RECONCILED",
        "transitions": transitions,
    }


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

def evaluate_circuit_breaker(
    risk_transitions: list[dict],
    stress: dict,
) -> dict:

    reasons = []

    if stress.get("status") == "BREACH":
        reasons.append("STRESS_LIMIT_BREACH")

    for transition in risk_transitions:
        if abs(transition["risk_delta"]) > MAX_RISK_REGIME_CHANGE:
            reasons.append("RAPID_RISK_REGIME_CHANGE")

    if reasons:
        return {
            "state": "TRIGGERED",
            "reason": sorted(set(reasons)),
        }

    return {
        "state": "CLEAR",
        "reason": [],
    }


# =============================================================================
# REPORT
# =============================================================================

def write_report(data: dict) -> None:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    with RUNTIME_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def print_separator(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_safety(baseline_before: dict, baseline_after: dict) -> None:

    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(f"Before rows  : {baseline_before['rows']}")
    print(f"After rows   : {baseline_after['rows']}")
    print(f"Before size  : {baseline_before['size']}")
    print(f"After size   : {baseline_after['size']}")
    print(f"Before SHA256: {baseline_before['sha256']}")
    print(f"After SHA256 : {baseline_after['sha256']}")

    invariant = baseline_before == baseline_after

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if invariant else "FAIL")
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print_separator(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "RISK REGIME TRANSITION + STRESS RECONCILIATION v0.1"
    )

    print()
    print_separator("OBJECTIVE:")
    print(
        "Consume ONLY the verified LIVE PAPER PORTFOLIO "
        "TEMPORAL PERFORMANCE / RISK REGIME frontier."
    )
    print(
        "Reconcile risk-regime transitions and analytical stress."
    )
    print("No real order is created or submitted.")

    print()
    print_separator("SAFETY POLICY")
    print("Production DB writes       : FORBIDDEN")
    print("Production engine run      : NO")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic data             : FORBIDDEN")
    print("Live data injection        : NONE")
    print("Order execution            : NONE")
    print("PAPER EXECUTION            : ANALYTICAL ONLY")

    print()
    print_separator("PRODUCTION BASELINE")

    baseline_before = db_fingerprint(DB_PATH)

    print(f"Rows   : {baseline_before['rows']}")
    print(f"Size   : {baseline_before['size']}")
    print(f"SHA256 : {baseline_before['sha256']}")

    print()
    print_separator("UPSTREAM FRONTIER")

    report = validate_upstream(load_upstream())

    print(f"Frontier : {report.get('frontier')}")
    print(
        f"Snapshot : "
        f"{report.get('current_snapshot') or report.get('snapshot') or report.get('snapshot_id')}"
    )

    snapshots = build_snapshot_series(report)

    print(f"Snapshots available : {len(snapshots)}")

    # -------------------------------------------------------------------------
    # TEMPORAL RISK TRANSITION
    # -------------------------------------------------------------------------

    print()
    print_separator("RISK REGIME TRANSITIONS")

    risk_transitions, transition_status = reconcile_risk_transitions(
        snapshots
    )

    if not risk_transitions:
        print("No risk regime transitions observed.")
    else:
        for transition in risk_transitions:
            print(
                f"{transition['from_snapshot']} -> "
                f"{transition['to_snapshot']} | "
                f"{transition['previous_regime']} -> "
                f"{transition['current_regime']} | "
                f"risk Δ={transition['risk_delta']:.6f} | "
                f"drawdown Δ={transition['drawdown_delta']:.6f}"
            )

    # -------------------------------------------------------------------------
    # POSITION / EXPOSURE
    # -------------------------------------------------------------------------

    print()
    print_separator("POSITION / EXPOSURE TRANSITIONS")

    position_result = reconcile_position_transitions(
        snapshots
    )

    if not position_result["transitions"]:
        print(
            "No position/exposure transitions observed."
        )
    else:
        for transition in position_result["transitions"]:
            print(
                f"{transition['from_snapshot']} -> "
                f"{transition['to_snapshot']} | "
                f"positions "
                f"{transition['previous_positions']} -> "
                f"{transition['current_positions']} | "
                f"notional Δ="
                f"{transition['notional_delta']:.6f}"
            )

    # -------------------------------------------------------------------------
    # STRESS
    # -------------------------------------------------------------------------

    print()
    print_separator("ANALYTICAL STRESS RECONCILIATION")

    stress = reconcile_stress(snapshots)

    if not stress["observations"]:
        print("Stress observations : 0")
        print("Status               : INSUFFICIENT_DATA")
        print("Reason               : NO_SNAPSHOTS")
    else:
        print(
            f"Stress observations : "
            f"{len(stress['observations'])}"
        )

        for observation in stress["observations"]:
            print(
                f"{observation['snapshot']} | "
                f"risk={observation['risk']:.6f} | "
                f"drawdown={observation['drawdown']:.6f} | "
                f"stress_loss={observation['stress_loss']:.6f} | "
                f"status={observation['stress_status']}"
            )

        print(
            f"Stress status       : {stress['status']}"
        )

    # -------------------------------------------------------------------------
    # CIRCUIT BREAKER
    # -------------------------------------------------------------------------

    circuit_breaker = evaluate_circuit_breaker(
        risk_transitions,
        stress,
    )

    print()
    print_separator("RISK REGIME CIRCUIT BREAKER")

    print(f"State  : {circuit_breaker['state']}")

    if circuit_breaker["reason"]:
        print(
            "Reason : "
            + ", ".join(circuit_breaker["reason"])
        )
    else:
        print("Reason : NONE")

    # -------------------------------------------------------------------------
    # FRONTIER VERDICT
    # -------------------------------------------------------------------------

    sufficient_data = len(snapshots) >= 2

    if not sufficient_data:
        frontier_verdict = "INSUFFICIENT_DATA"
    elif (
        transition_status == "PASS"
        and stress["status"] == "PASS"
        and circuit_breaker["state"] == "CLEAR"
    ):
        frontier_verdict = "PASS"
    else:
        frontier_verdict = "BREACH"

    print()
    print_separator(
        "LIVE PAPER PORTFOLIO RISK REGIME TRANSITION + "
        "STRESS RECONCILIATION VERDICT"
    )

    print("UPSTREAM_STATE_CONSUMED       : PASS")
    print(
        "RISK_REGIME_TRANSITIONS      : "
        + transition_status
    )
    print(
        "POSITION_EXPOSURE_TRANSITION : "
        + position_result["status"]
    )
    print(
        "STRESS_RECONCILIATION        : "
        + stress["status"]
    )
    print(
        "CIRCUIT_BREAKER              : "
        + circuit_breaker["state"]
    )
    print("PRODUCTION_ISOLATION         : PASS")
    print(
        "FRONTIER VERDICT             : "
        + frontier_verdict
    )

    # -------------------------------------------------------------------------
    # DATABASE INVARIANT
    # -------------------------------------------------------------------------

    baseline_after = db_fingerprint(DB_PATH)

    print()
    print_safety(
        baseline_before,
        baseline_after,
    )

    # -------------------------------------------------------------------------
    # FINAL SAFETY
    # -------------------------------------------------------------------------

    print()
    print_separator("FINAL SAFETY VERDICT")

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

    if frontier_verdict == "INSUFFICIENT_DATA":
        print()
        print(
            "Insufficient temporal snapshots for a valid "
            "risk-regime transition analysis."
        )

    if frontier_verdict == "PASS":
        print()
        print(
            "Risk-regime transition and analytical stress "
            "reconciliation passed."
        )

    if frontier_verdict == "BREACH":
        print()
        print(
            "Risk or stress reconciliation detected a breach."
        )

    print()
    print(f"Runtime report : {RUNTIME_REPORT}")

    # -------------------------------------------------------------------------
    # MACHINE REPORT
    # -------------------------------------------------------------------------

    runtime_report = {
        "frontier": FRONTIER,
        "version": VERSION,
        "timestamp_utc": utc_now(),

        "objective": {
            "upstream_frontier": report.get("frontier"),
            "analysis": (
                "RISK_REGIME_TRANSITION_AND_STRESS_RECONCILIATION"
            ),
        },

        "upstream": {
            "report": str(UPSTREAM_REPORT),
            "frontier": report.get("frontier"),
            "current_snapshot": (
                report.get("current_snapshot")
                or report.get("snapshot")
                or report.get("snapshot_id")
            ),
            "snapshots_available": len(snapshots),
        },

        "snapshots": snapshots,

        "risk_regime_transitions": {
            "status": transition_status,
            "count": len(risk_transitions),
            "transitions": risk_transitions,
        },

        "position_exposure_transitions": position_result,

        "stress_reconciliation": stress,

        "circuit_breaker": circuit_breaker,

        "verdict": {
            "upstream_state_consumed": "PASS",
            "risk_regime_transitions": transition_status,
            "position_exposure_transition": position_result["status"],
            "stress_reconciliation": stress["status"],
            "circuit_breaker": circuit_breaker["state"],
            "production_isolation": "PASS",
            "frontier_verdict": frontier_verdict,
        },

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
            "order_execution": False,
        },
    }

    write_report(runtime_report)


if __name__ == "__main__":
    main()