from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.2"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

LIVE_CAPTURE_DIR = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_DIR",
        r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
    )
)

UPSTREAM_REPORT = (
    LIVE_CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_RISK_REGIME_STABILITY_STRESS_RESPONSE_RECONCILIATION_REPORT.json"
)

REPORT_PATH = (
    LIVE_CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_RISK_GOVERNANCE_READINESS_GATE_REPORT.json"
)


EXPECTED_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_RISK_REGIME_STABILITY_STRESS_RESPONSE_RECONCILIATION_v0.1"
)


LIMITS = {
    "MAX_PORTFOLIO_RISK": 0.02,
    "MAX_ANALYTICAL_NOTIONAL": 1.00,
    "MAX_ASSET_CONCENTRATION": 0.50,
    "MAX_DRAWDOWN": 0.10,
    "MAX_CURRENT_DRAWDOWN": 0.05,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def get_db_fingerprint() -> dict[str, Any]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Production DB not found: {DB_PATH}")

    size = DB_PATH.stat().st_size
    sha = sha256_file(DB_PATH)

    rows = None

    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only = ON")

        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM market_history"
            ).fetchone()

            if row:
                rows = int(row[0])

        except sqlite3.Error:
            rows = None

    return {
        "rows": rows,
        "size": size,
        "sha256": sha,
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Upstream report root must be a JSON object.")

    return data


def first_present(
    data: dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        if key in data:
            return data[key]

    return default


def extract_frontier(report: dict[str, Any]) -> str | None:
    value = first_present(
        report,
        "frontier",
        "FRONTIER",
        "Frontier",
    )

    if isinstance(value, str):
        return value.strip()

    return None


def extract_snapshot(report: dict[str, Any]) -> str | None:
    value = first_present(
        report,
        "snapshot",
        "current_snapshot",
        "CURRENT_SNAPSHOT",
        "Snapshot",
        "Current snapshot",
    )

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def extract_snapshots(report: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        report.get("snapshots"),
        report.get("SNAPSHOTS"),
        report.get("temporal_snapshots"),
        report.get("TEMPORAL_SNAPSHOTS"),
        report.get("snapshot_records"),
        report.get("SNAPSHOT_RECORDS"),
    ]

    for value in candidates:
        if isinstance(value, list):
            return [
                item for item in value
                if isinstance(item, dict)
            ]

    return []


def extract_numeric(
    report: dict[str, Any],
    *keys: str,
    default: float = 0.0,
) -> float:
    value = first_present(report, *keys, default=default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_positions(report: dict[str, Any]) -> int:
    value = first_present(
        report,
        "positions",
        "position_count",
        "open_positions",
        "PAPER_POSITIONS",
        "Positions",
        default=0,
    )

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def extract_circuit_breaker(
    report: dict[str, Any]
) -> tuple[str, str]:

    raw = first_present(
        report,
        "circuit_breaker",
        "CIRCUIT_BREAKER",
        "risk_regime_circuit_breaker",
        "RISK_REGIME_CIRCUIT_BREAKER",
        default=None,
    )

    if isinstance(raw, dict):
        state = str(
            raw.get(
                "state",
                raw.get(
                    "STATE",
                    raw.get("status", "CLEAR"),
                ),
            )
        ).upper()

        reason = str(
            raw.get(
                "reason",
                raw.get(
                    "REASON",
                    "NONE",
                ),
            )
        )

        return state, reason

    if isinstance(raw, str):
        return raw.upper(), "UPSTREAM_STATE"

    return "CLEAR", "NO_UPSTREAM_CIRCUIT_BREAKER"


def extract_temporal_status(
    report: dict[str, Any]
) -> tuple[str, str]:

    snapshots = extract_snapshots(report)

    count = first_present(
        report,
        "snapshots_available",
        "Snapshots available",
        "snapshots_observed",
        "Snapshots observed",
        default=len(snapshots),
    )

    try:
        count = int(count)
    except (TypeError, ValueError):
        count = len(snapshots)

    status = first_present(
        report,
        "temporal_evidence",
        "TEMPORAL_EVIDENCE",
        "temporal_status",
        "TEMPORAL_STATUS",
        default=None,
    )

    if isinstance(status, str):
        status_upper = status.upper()

        if status_upper in {
            "PASS",
            "VERIFIED",
            "SUFFICIENT",
            "CLEAR",
        }:
            return "PASS", f"UPSTREAM_{status_upper}"

        if status_upper in {
            "INSUFFICIENT_DATA",
            "BLOCKED",
            "FAIL",
        }:
            return "INSUFFICIENT_DATA", status_upper

    if count >= 2:
        return "PASS", "MINIMUM_TEMPORAL_EVIDENCE_AVAILABLE"

    return (
        "INSUFFICIENT_DATA",
        "MINIMUM_TWO_TEMPORAL_SNAPSHOTS_REQUIRED",
    )


def validate_upstream(
    report: dict[str, Any]
) -> dict[str, Any]:

    frontier = extract_frontier(report)

    if frontier is None:
        raise ValueError(
            "Upstream report missing frontier."
        )

    if frontier != EXPECTED_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier.\n"
            f"Expected: {EXPECTED_FRONTIER}\n"
            f"Received: {frontier}"
        )

    snapshots = extract_snapshots(report)
    snapshot = extract_snapshot(report)

    positions = extract_positions(report)

    return {
        "frontier": frontier,
        "snapshot": snapshot,
        "snapshots": snapshots,
        "positions": positions,
    }


def evaluate_limit(
    name: str,
    observed: float,
    limit: float,
) -> dict[str, Any]:

    passed = observed <= limit

    return {
        "name": name,
        "observed": observed,
        "limit": limit,
        "status": "PASS" if passed else "FAIL",
    }


def build_report(
    upstream: dict[str, Any],
    baseline_before: dict[str, Any],
    baseline_after: dict[str, Any],
) -> dict[str, Any]:

    source_report = load_json(UPSTREAM_REPORT)

    portfolio_risk = extract_numeric(
        source_report,
        "portfolio_risk",
        "Portfolio risk",
        "risk",
        "aggregate_risk",
        "AGGREGATE_RISK",
    )

    analytical_notional = extract_numeric(
        source_report,
        "analytical_notional",
        "Analytical notional",
        "total_analytical_notional",
        "notional",
    )

    max_concentration = extract_numeric(
        source_report,
        "maximum_concentration",
        "max_concentration",
        "Maximum concentration",
        "MAX_ASSET_CONCENTRATION",
        "concentration",
    )

    max_drawdown = extract_numeric(
        source_report,
        "maximum_drawdown",
        "Maximum drawdown",
        "max_drawdown",
        "MAX_DRAWDOWN",
    )

    current_drawdown = extract_numeric(
        source_report,
        "current_drawdown",
        "Current drawdown",
        "current_drawdown",
        "CURRENT_DRAWDOWN",
    )

    unrealized_pnl = extract_numeric(
        source_report,
        "unrealized_pnl",
        "Unrealized P&L",
        "unrealized_pnl_pct",
    )

    circuit_state, circuit_reason = extract_circuit_breaker(
        source_report
    )

    temporal_status, temporal_reason = extract_temporal_status(
        source_report
    )

    limits = [
        evaluate_limit(
            "MAX_PORTFOLIO_RISK",
            portfolio_risk,
            LIMITS["MAX_PORTFOLIO_RISK"],
        ),
        evaluate_limit(
            "MAX_ANALYTICAL_NOTIONAL",
            analytical_notional,
            LIMITS["MAX_ANALYTICAL_NOTIONAL"],
        ),
        evaluate_limit(
            "MAX_ASSET_CONCENTRATION",
            max_concentration,
            LIMITS["MAX_ASSET_CONCENTRATION"],
        ),
        evaluate_limit(
            "MAX_DRAWDOWN",
            max_drawdown,
            LIMITS["MAX_DRAWDOWN"],
        ),
        evaluate_limit(
            "MAX_CURRENT_DRAWDOWN",
            current_drawdown,
            LIMITS["MAX_CURRENT_DRAWDOWN"],
        ),
    ]

    risk_limits_pass = all(
        item["status"] == "PASS"
        for item in limits
    )

    # IMPORTANT:
    # CLEAR means no trigger is present.
    # Missing temporal data must NOT be interpreted as a
    # real circuit-breaker event.
    #
    # Therefore governance readiness is BLOCKED by
    # insufficient temporal evidence, but circuit breaker
    # remains CLEAR unless upstream explicitly reports
    # an active/triggered state.

    circuit_active = circuit_state in {
        "ACTIVE",
        "TRIGGERED",
        "BLOCKED",
        "HALT",
    }

    if circuit_active:
        readiness = "BLOCKED"
        readiness_reason = "CIRCUIT_BREAKER_ACTIVE"

    elif temporal_status != "PASS":
        readiness = "BLOCKED"
        readiness_reason = (
            "INSUFFICIENT_TEMPORAL_EVIDENCE"
        )

    elif not risk_limits_pass:
        readiness = "BLOCKED"
        readiness_reason = "RISK_LIMIT_BREACH"

    else:
        readiness = "READY"
        readiness_reason = "ALL_GOVERNANCE_CONDITIONS_PASS"

    if circuit_active:
        circuit_status = "BLOCKED"
    else:
        circuit_status = "CLEAR"

    if readiness == "READY":
        frontier_verdict = "PASS"
    else:
        frontier_verdict = "BLOCKED"

    return {
        "report_version": VERSION,
        "generated_at": utc_now(),
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_RISK_GOVERNANCE_READINESS_GATE_v0.2"
        ),
        "objective": (
            "Evaluate analytical risk-governance readiness "
            "from the verified upstream PAPER risk-regime frontier."
        ),
        "safety_policy": {
            "production_db_writes": False,
            "production_engine_run": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "real_order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
        },
        "upstream": {
            "report": str(UPSTREAM_REPORT),
            "frontier": upstream["frontier"],
            "snapshot": upstream["snapshot"],
            "snapshots_available": len(upstream["snapshots"]),
            "positions": upstream["positions"],
        },
        "current_risk_state": {
            "positions": upstream["positions"],
            "open_positions": upstream["positions"],
            "analytical_notional": analytical_notional,
            "portfolio_risk": portfolio_risk,
            "maximum_drawdown": max_drawdown,
            "current_drawdown": current_drawdown,
            "max_concentration": max_concentration,
            "unrealized_pnl": unrealized_pnl,
        },
        "risk_limits": limits,
        "temporal_governance": {
            "snapshots_observed": len(upstream["snapshots"]),
            "status": temporal_status,
            "reason": temporal_reason,
        },
        "circuit_breaker": {
            "state": circuit_status,
            "upstream_state": circuit_state,
            "reason": circuit_reason,
        },
        "risk_governance_readiness": {
            "risk_limits": (
                "PASS"
                if risk_limits_pass
                else "FAIL"
            ),
            "circuit_breaker": circuit_status,
            "temporal_evidence": temporal_status,
            "readiness": readiness,
            "reason": readiness_reason,
        },
        "verdict": {
            "upstream_state_consumed": "PASS",
            "risk_limit_evaluation": (
                "PASS"
                if risk_limits_pass
                else "FAIL"
            ),
            "circuit_breaker": circuit_status,
            "temporal_data": temporal_status,
            "risk_governance_readiness": readiness,
            "production_isolation": "PASS",
            "frontier_verdict": frontier_verdict,
        },
        "production_database_invariant": {
            "before": baseline_before,
            "after": baseline_after,
            "rows_unchanged": (
                baseline_before["rows"]
                == baseline_after["rows"]
            ),
            "size_unchanged": (
                baseline_before["size"]
                == baseline_after["size"]
            ),
            "sha256_unchanged": (
                baseline_before["sha256"]
                == baseline_after["sha256"]
            ),
            "pass": (
                baseline_before == baseline_after
            ),
        },
        "final_safety_verdict": {
            "production_db_writes": "NONE",
            "insert": "NONE",
            "update": "NONE",
            "delete": "NONE",
            "ddl": "NONE",
            "production_engine": "NOT_EXECUTED",
            "historical_repair": "NONE",
            "direction_inference": "NONE",
            "score_reconstruction": "NONE",
            "synthetic_data": "NONE",
            "live_data_injection": "NONE",
            "real_order_execution": "NONE",
            "paper_execution": "ANALYTICAL_ONLY",
        },
    }


def print_header(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_report(report: dict[str, Any]) -> None:

    print_header(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "RISK GOVERNANCE READINESS GATE v0.2"
    )

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print("=" * 100)
    print(
        "Consume ONLY the verified LIVE PAPER PORTFOLIO "
        "RISK REGIME STABILITY + STRESS RESPONSE frontier."
    )
    print(
        "Evaluate analytical risk-governance readiness."
    )
    print(
        "No real order is created or submitted."
    )

    print()
    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)
    print("Production DB writes       : FORBIDDEN")
    print("Production engine run     : NO")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic data            : FORBIDDEN")
    print("Live data injection       : NONE")
    print("Order execution           : NONE")
    print("PAPER EXECUTION           : ANALYTICAL ONLY")

    baseline = report["production_database_invariant"]["before"]

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {baseline['rows']}")
    print(f"Size   : {baseline['size']}")
    print(f"SHA256 : {baseline['sha256']}")

    upstream = report["upstream"]

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Frontier         : {upstream['frontier']}")
    print(f"Snapshot         : {upstream['snapshot']}")
    print(f"Snapshots        : {upstream['snapshots_available']}")
    print(f"Positions        : {upstream['positions']}")

    risk = report["current_risk_state"]

    print()
    print("=" * 100)
    print("CURRENT RISK STATE")
    print("=" * 100)
    print(f"Positions            : {risk['positions']}")
    print(f"Open positions       : {risk['open_positions']}")
    print(f"Analytical notional  : {risk['analytical_notional']:.6f}")
    print(f"Portfolio risk       : {risk['portfolio_risk']:.6f}")
    print(f"Maximum drawdown     : {risk['maximum_drawdown']:.6f}")
    print(f"Current drawdown     : {risk['current_drawdown']:.6f}")
    print(f"Max concentration    : {risk['max_concentration']:.6f}")
    print(f"Unrealized P&L       : {risk['unrealized_pnl']:.6f}")

    print()
    print("=" * 100)
    print("RISK LIMIT GOVERNANCE")
    print("=" * 100)

    for item in report["risk_limits"]:
        print(
            f"{item['name']:<32} | "
            f"observed={item['observed']:.6f} | "
            f"limit={item['limit']:.6f} | "
            f"{item['status']}"
        )

    temporal = report["temporal_governance"]

    print()
    print("=" * 100)
    print("TEMPORAL GOVERNANCE")
    print("=" * 100)
    print(
        f"Snapshots observed : "
        f"{temporal['snapshots_observed']}"
    )
    print(
        f"Temporal evidence  : "
        f"{temporal['status']}"
    )
    print(
        f"Reason             : "
        f"{temporal['reason']}"
    )

    breaker = report["circuit_breaker"]

    print()
    print("=" * 100)
    print("CIRCUIT BREAKER")
    print("=" * 100)
    print(f"State  : {breaker['state']}")
    print(f"Reason : {breaker['reason']}")

    readiness = report["risk_governance_readiness"]

    print()
    print("=" * 100)
    print("RISK GOVERNANCE READINESS")
    print("=" * 100)
    print(
        f"Risk limits       : "
        f"{readiness['risk_limits']}"
    )
    print(
        f"Circuit breaker   : "
        f"{readiness['circuit_breaker']}"
    )
    print(
        f"Temporal evidence : "
        f"{readiness['temporal_evidence']}"
    )
    print(
        f"Readiness         : "
        f"{readiness['readiness']}"
    )
    print(
        f"Reason            : "
        f"{readiness['reason']}"
    )

    verdict = report["verdict"]

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO RISK GOVERNANCE "
        "READINESS GATE VERDICT"
    )
    print("=" * 100)
    print(
        f"UPSTREAM_STATE_CONSUMED   : "
        f"{verdict['upstream_state_consumed']}"
    )
    print(
        f"RISK_LIMIT_EVALUATION     : "
        f"{verdict['risk_limit_evaluation']}"
    )
    print(
        f"CIRCUIT_BREAKER           : "
        f"{verdict['circuit_breaker']}"
    )
    print(
        f"TEMPORAL_DATA             : "
        f"{verdict['temporal_data']}"
    )
    print(
        f"RISK_GOVERNANCE_READINESS : "
        f"{verdict['risk_governance_readiness']}"
    )
    print(
        f"PRODUCTION_ISOLATION      : "
        f"{verdict['production_isolation']}"
    )
    print(
        f"FRONTIER VERDICT          : "
        f"{verdict['frontier_verdict']}"
    )

    invariant = report["production_database_invariant"]

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(
        f"Before rows  : "
        f"{invariant['before']['rows']}"
    )
    print(
        f"After rows   : "
        f"{invariant['after']['rows']}"
    )
    print(
        f"Before size  : "
        f"{invariant['before']['size']}"
    )
    print(
        f"After size   : "
        f"{invariant['after']['size']}"
    )
    print(
        f"Before SHA256: "
        f"{invariant['before']['sha256']}"
    )
    print(
        f"After SHA256 : "
        f"{invariant['after']['sha256']}"
    )
    print(
        f"PRODUCTION DB INVARIANT : "
        f"{'PASS' if invariant['pass'] else 'FAIL'}"
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)
    for key, value in report["final_safety_verdict"].items():
        print(
            f"{key.replace('_', ' '):<25}: {value}"
        )

    print()
    if verdict["frontier_verdict"] == "PASS":
        print(
            "Risk governance analytical readiness "
            "conditions are satisfied."
        )
    else:
        print(
            "Risk governance readiness remains BLOCKED "
            "until sufficient temporal evidence exists."
        )

    print()
    print(
        f"Runtime report : {REPORT_PATH}"
    )


def main() -> None:

    print_header(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "RISK GOVERNANCE READINESS GATE v0.2"
    )

    baseline_before = get_db_fingerprint()

    upstream_report = load_json(UPSTREAM_REPORT)

    upstream = validate_upstream(
        upstream_report
    )

    report = build_report(
        upstream,
        baseline_before,
        baseline_before,
    )

    baseline_after = get_db_fingerprint()

    invariant = report[
        "production_database_invariant"
    ]

    invariant["after"] = baseline_after
    invariant["rows_unchanged"] = (
        baseline_before["rows"]
        == baseline_after["rows"]
    )
    invariant["size_unchanged"] = (
        baseline_before["size"]
        == baseline_after["size"]
    )
    invariant["sha256_unchanged"] = (
        baseline_before["sha256"]
        == baseline_after["sha256"]
    )
    invariant["pass"] = (
        baseline_before == baseline_after
    )

    if not invariant["pass"]:
        report["verdict"]["production_isolation"] = "FAIL"
        report["verdict"]["frontier_verdict"] = "BLOCKED"
        report["risk_governance_readiness"]["readiness"] = "BLOCKED"
        report["risk_governance_readiness"]["reason"] = (
            "PRODUCTION_DATABASE_CHANGED"
        )

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print_report(report)


if __name__ == "__main__":
    main()