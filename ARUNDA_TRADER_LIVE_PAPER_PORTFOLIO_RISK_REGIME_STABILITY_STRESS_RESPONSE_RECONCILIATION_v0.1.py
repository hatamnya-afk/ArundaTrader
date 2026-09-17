# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE PAPER PORTFOLIO RISK REGIME STABILITY + STRESS RESPONSE RECONCILIATION v0.1

READ-ONLY / ANALYTICAL ONLY

Consumes:
    LIVE_PAPER_PORTFOLIO_RISK_REGIME_TRANSITION_STRESS_RECONCILIATION_REPORT.json

Safety:
    - No production DB writes
    - No production engine execution
    - No historical repair
    - No direction inference
    - No score reconstruction
    - No synthetic data
    - No live data injection
    - No order execution
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

LIVE_CAPTURE_DIR = (
    r"C:\Users\ASUS\AppData\Local\Temp"
    r"\arunda_live_launch_76134ecc"
)

UPSTREAM_REPORT = os.path.join(
    LIVE_CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_RISK_REGIME_TRANSITION_STRESS_RECONCILIATION_REPORT.json",
)

RUNTIME_REPORT = os.path.join(
    LIVE_CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_RISK_REGIME_STABILITY_STRESS_RESPONSE_RECONCILIATION_REPORT.json",
)

DB_PATH = os.path.join(BASE_DIR, "arunda.db")

EXPECTED_UPSTREAM_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_RISK_REGIME_TRANSITION_STRESS_RECONCILIATION_v0.1"
)

CURRENT_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_RISK_REGIME_STABILITY_STRESS_RESPONSE_RECONCILIATION_v0.1"
)

# Analytical limits only.
MAX_RISK = 0.02
MAX_EXPOSURE = 1.00
MAX_CONCENTRATION = 0.50
MAX_DRAWDOWN = 0.10
MAX_STRESS_LOSS = 0.05

EPS = 1e-12


# =============================================================================
# SAFETY
# =============================================================================

def safety_policy() -> dict[str, Any]:
    return {
        "production_db_modified": False,
        "production_engine_executed": False,
        "historical_repair": False,
        "direction_inference": False,
        "score_reconstruction": False,
        "synthetic_data": False,
        "live_data_injection": False,
        "order_execution": False,
        "paper_execution": "ANALYTICAL ONLY",
    }


# =============================================================================
# DATABASE FINGERPRINT
# =============================================================================

def db_fingerprint(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {
            "rows": None,
            "size": None,
            "sha256": None,
            "exists": False,
        }

    size = os.path.getsize(path)

    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)

    rows = None

    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()

        tables = {
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            ).fetchall()
        }

        # Prefer the largest known production table.
        candidates = [
            "market_history",
            "market_history_repair",
            "market_data",
            "market_records",
        ]

        for table in candidates:
            if table in tables:
                try:
                    rows = cur.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
                    break
                except Exception:
                    pass

        conn.close()

    except Exception:
        rows = None

    return {
        "rows": rows,
        "size": size,
        "sha256": sha.hexdigest(),
        "exists": True,
    }


# =============================================================================
# JSON HELPERS
# =============================================================================

def load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Required upstream report not found:\n{path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Upstream report root must be an object.")

    return data


def first_present(
    obj: dict[str, Any],
    names: list[str],
    default: Any = None,
) -> Any:
    for name in names:
        if name in obj:
            return obj[name]
    return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default

        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


# =============================================================================
# UPSTREAM VALIDATION
# =============================================================================

def validate_upstream(report: dict[str, Any]) -> dict[str, Any]:

    frontier = report.get("frontier")

    if frontier != EXPECTED_UPSTREAM_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier.\n"
            f"Expected: {EXPECTED_UPSTREAM_FRONTIER}\n"
            f"Received: {frontier}"
        )

    safety = report.get("safety", {})

    forbidden_flags = [
        "production_db_modified",
        "production_engine_executed",
        "historical_repair",
        "direction_inference",
        "score_reconstruction",
        "synthetic_data",
        "live_data_injection",
        "order_execution",
    ]

    violations = [
        key for key in forbidden_flags
        if bool(safety.get(key, False))
    ]

    if violations:
        raise ValueError(
            "Upstream safety violation detected: "
            + ", ".join(violations)
        )

    return report


# =============================================================================
# SNAPSHOT EXTRACTION
# =============================================================================

def extract_snapshots(report: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[Any] = []

    possible_sources = [
        report.get("snapshots"),
        report.get("temporal_snapshots"),
        report.get("risk_regime_snapshots"),
        report.get("stress_snapshots"),
        report.get("snapshot_history"),
        report.get("observations"),
    ]

    for source in possible_sources:
        if isinstance(source, list):
            candidates.extend(source)

    # Some upstream versions may store one snapshot in a singular object.
    singular = first_present(
        report,
        [
            "current_snapshot",
            "snapshot",
            "latest_snapshot",
        ],
    )

    if isinstance(singular, dict):
        candidates.append(singular)

    normalized: list[dict[str, Any]] = []

    seen: set[str] = set()

    for item in candidates:

        if not isinstance(item, dict):
            continue

        snapshot_id = first_present(
            item,
            [
                "snapshot",
                "snapshot_id",
                "id",
                "snapshotId",
            ],
        )

        if snapshot_id is None:
            continue

        snapshot_id = str(snapshot_id)

        if snapshot_id in seen:
            continue

        seen.add(snapshot_id)

        timestamp = first_present(
            item,
            [
                "timestamp_utc",
                "timestamp",
                "time",
                "created_at",
            ],
        )

        positions = as_float(
            first_present(
                item,
                [
                    "positions",
                    "position_count",
                    "open_positions",
                    "paper_positions",
                ],
                0,
            )
        )

        notional = as_float(
            first_present(
                item,
                [
                    "analytical_notional",
                    "notional",
                    "exposure",
                    "total_notional",
                ],
                0,
            )
        )

        risk = as_float(
            first_present(
                item,
                [
                    "analytical_risk",
                    "portfolio_risk",
                    "risk",
                    "risk_ratio",
                ],
                0,
            )
        )

        pnl = as_float(
            first_present(
                item,
                [
                    "pnl",
                    "total_pnl",
                    "unrealized_pnl",
                    "realized_pnl",
                ],
                0,
            )
        )

        drawdown = as_float(
            first_present(
                item,
                [
                    "drawdown",
                    "current_drawdown",
                    "drawdown_pct",
                ],
                0,
            )
        )

        concentration = as_float(
            first_present(
                item,
                [
                    "maximum_concentration",
                    "max_concentration",
                    "concentration",
                ],
                0,
            )
        )

        regime = first_present(
            item,
            [
                "risk_regime",
                "regime",
                "risk_state",
                "state",
            ],
            "UNKNOWN",
        )

        normalized.append(
            {
                "snapshot": snapshot_id,
                "timestamp": timestamp,
                "positions": positions,
                "notional": notional,
                "risk": risk,
                "pnl": pnl,
                "drawdown": drawdown,
                "concentration": concentration,
                "risk_regime": str(regime),
            }
        )

    return normalized


# =============================================================================
# TEMPORAL ORDER
# =============================================================================

def timestamp_key(item: dict[str, Any]) -> tuple[int, str]:

    value = item.get("timestamp")

    if value is None:
        return (1, "")

    text = str(value)

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        return (
            0,
            parsed.astimezone(timezone.utc).isoformat(),
        )

    except Exception:
        return (1, text)


def sort_snapshots(
    snapshots: list[dict[str, Any]]
) -> list[dict[str, Any]]:

    return sorted(snapshots, key=timestamp_key)


# =============================================================================
# RISK REGIME CLASSIFICATION
# =============================================================================

def classify_risk(snapshot: dict[str, Any]) -> str:

    risk = abs(as_float(snapshot.get("risk")))
    drawdown = abs(as_float(snapshot.get("drawdown")))
    concentration = abs(
        as_float(snapshot.get("concentration"))
    )

    if (
        risk > MAX_RISK
        or drawdown > MAX_DRAWDOWN
        or concentration > MAX_CONCENTRATION
    ):
        return "STRESSED"

    if (
        risk > MAX_RISK * 0.50
        or drawdown > MAX_DRAWDOWN * 0.50
        or concentration > MAX_CONCENTRATION * 0.50
    ):
        return "ELEVATED"

    return "NORMAL"


# =============================================================================
# STABILITY ANALYSIS
# =============================================================================

def analyze_stability(
    snapshots: list[dict[str, Any]]
) -> dict[str, Any]:

    if len(snapshots) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "MINIMUM_TWO_SNAPSHOTS_REQUIRED",
            "observations": 0,
            "stable": None,
            "transitions": [],
        }

    transitions: list[dict[str, Any]] = []

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):

        prev_regime = classify_risk(previous)
        curr_regime = classify_risk(current)

        risk_delta = (
            as_float(current["risk"])
            - as_float(previous["risk"])
        )

        drawdown_delta = (
            as_float(current["drawdown"])
            - as_float(previous["drawdown"])
        )

        exposure_delta = (
            as_float(current["notional"])
            - as_float(previous["notional"])
        )

        pnl_delta = (
            as_float(current["pnl"])
            - as_float(previous["pnl"])
        )

        transitions.append(
            {
                "from_snapshot": previous["snapshot"],
                "to_snapshot": current["snapshot"],
                "from_regime": prev_regime,
                "to_regime": curr_regime,
                "risk_delta": risk_delta,
                "drawdown_delta": drawdown_delta,
                "exposure_delta": exposure_delta,
                "pnl_delta": pnl_delta,
                "transition":
                    "STABLE"
                    if prev_regime == curr_regime
                    else "REGIME_CHANGE",
            }
        )

    stable_count = sum(
        1
        for item in transitions
        if item["transition"] == "STABLE"
    )

    stability_ratio = (
        stable_count / len(transitions)
        if transitions
        else 0.0
    )

    return {
        "status": "PASS",
        "reason": None,
        "observations": len(transitions),
        "stable": stability_ratio >= 0.50,
        "stability_ratio": stability_ratio,
        "transitions": transitions,
    }


# =============================================================================
# STRESS RESPONSE
# =============================================================================

def stress_response(
    snapshots: list[dict[str, Any]]
) -> dict[str, Any]:

    if len(snapshots) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "MINIMUM_TWO_SNAPSHOTS_REQUIRED",
            "observations": 0,
            "responses": [],
        }

    responses: list[dict[str, Any]] = []

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):

        prev_risk = as_float(previous["risk"])
        curr_risk = as_float(current["risk"])

        prev_dd = as_float(previous["drawdown"])
        curr_dd = as_float(current["drawdown"])

        prev_pnl = as_float(previous["pnl"])
        curr_pnl = as_float(current["pnl"])

        risk_delta = curr_risk - prev_risk
        drawdown_delta = curr_dd - prev_dd
        pnl_delta = curr_pnl - prev_pnl

        stressed = (
            risk_delta > EPS
            or drawdown_delta > EPS
            or pnl_delta < -MAX_STRESS_LOSS
        )

        response = "NO_STRESS"

        if stressed:
            if (
                curr_risk <= MAX_RISK
                and curr_dd <= MAX_DRAWDOWN
            ):
                response = "CONTAINED"
            else:
                response = "BREACH"

        responses.append(
            {
                "from_snapshot": previous["snapshot"],
                "to_snapshot": current["snapshot"],
                "risk_delta": risk_delta,
                "drawdown_delta": drawdown_delta,
                "pnl_delta": pnl_delta,
                "stress_detected": stressed,
                "response": response,
            }
        )

    breaches = sum(
        1
        for item in responses
        if item["response"] == "BREACH"
    )

    return {
        "status": "PASS" if breaches == 0 else "FAIL",
        "reason": None if breaches == 0 else "STRESS_LIMIT_BREACH",
        "observations": len(responses),
        "breaches": breaches,
        "responses": responses,
    }


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

def circuit_breaker(
    snapshots: list[dict[str, Any]]
) -> dict[str, str]:

    if not snapshots:
        return {
            "state": "CLEAR",
            "reason": "NO_SNAPSHOT_DATA",
        }

    latest = snapshots[-1]

    risk = abs(as_float(latest["risk"]))
    drawdown = abs(as_float(latest["drawdown"]))
    concentration = abs(
        as_float(latest["concentration"])
    )

    reasons = []

    if risk > MAX_RISK:
        reasons.append("MAX_PORTFOLIO_RISK")

    if drawdown > MAX_DRAWDOWN:
        reasons.append("MAX_DRAWDOWN")

    if concentration > MAX_CONCENTRATION:
        reasons.append("MAX_ASSET_CONCENTRATION")

    if reasons:
        return {
            "state": "TRIGGERED",
            "reason": ",".join(reasons),
        }

    return {
        "state": "CLEAR",
        "reason": "NONE",
    }


# =============================================================================
# REPORT
# =============================================================================

def build_report(
    upstream: dict[str, Any],
    snapshots: list[dict[str, Any]],
    stability: dict[str, Any],
    stress: dict[str, Any],
    breaker: dict[str, str],
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:

    safety = safety_policy()

    if not snapshots:
        verdict = "INSUFFICIENT_DATA"
    elif (
        stability["status"] == "PASS"
        and stress["status"] == "PASS"
        and breaker["state"] == "CLEAR"
    ):
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return {
        "frontier": CURRENT_FRONTIER,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "objective": (
            "Consume ONLY the verified LIVE PAPER "
            "PORTFOLIO RISK REGIME TRANSITION + STRESS "
            "RECONCILIATION frontier."
        ),

        "upstream": {
            "frontier": upstream.get("frontier"),
            "snapshot": upstream.get(
                "current_snapshot",
                upstream.get("snapshot"),
            ),
            "snapshots_available": len(snapshots),
        },

        "snapshots": snapshots,

        "performance_stability": stability,

        "stress_response": stress,

        "circuit_breaker": breaker,

        "limits": {
            "max_portfolio_risk": MAX_RISK,
            "max_exposure": MAX_EXPOSURE,
            "max_concentration": MAX_CONCENTRATION,
            "max_drawdown": MAX_DRAWDOWN,
            "max_stress_loss": MAX_STRESS_LOSS,
        },

        "production_database": {
            "before": before,
            "after": after,
            "unchanged": (
                before.get("sha256")
                == after.get("sha256")
                and before.get("size")
                == after.get("size")
                and before.get("rows")
                == after.get("rows")
            ),
        },

        "safety": safety,

        "verdict": {
            "upstream_state_consumed": "PASS",
            "risk_regime_stability":
                stability["status"],
            "stress_response_reconciliation":
                stress["status"],
            "circuit_breaker":
                breaker["state"],
            "production_isolation": "PASS",
            "frontier_verdict": verdict,
        },
    }


# =============================================================================
# OUTPUT
# =============================================================================

def print_report(
    upstream: dict[str, Any],
    snapshots: list[dict[str, Any]],
    stability: dict[str, Any],
    stress: dict[str, Any],
    breaker: dict[str, str],
    before: dict[str, Any],
    after: dict[str, Any],
    verdict: str,
) -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "RISK REGIME STABILITY + STRESS RESPONSE "
        "RECONCILIATION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print("=" * 100)
    print(
        "Consume ONLY the verified LIVE PAPER PORTFOLIO "
        "RISK REGIME TRANSITION + STRESS frontier."
    )
    print(
        "Evaluate risk-regime stability and analytical "
        "stress response."
    )
    print("No real order is created or submitted.")

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

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {before.get('rows')}")
    print(f"Size   : {before.get('size')}")
    print(f"SHA256 : {before.get('sha256')}")

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Frontier : {upstream.get('frontier')}")
    print(
        f"Snapshot : "
        f"{upstream.get('current_snapshot', upstream.get('snapshot'))}"
    )
    print(f"Snapshots available : {len(snapshots)}")

    print()
    print("=" * 100)
    print("RISK REGIME STABILITY")
    print("=" * 100)
    print(
        f"Snapshots observed : "
        f"{stability.get('observations', 0)}"
    )
    print(f"Status              : {stability.get('status')}")

    if stability.get("reason"):
        print(f"Reason              : {stability.get('reason')}")

    if stability.get("stability_ratio") is not None:
        print(
            f"Stability ratio     : "
            f"{stability['stability_ratio']:.6f}"
        )

    if not snapshots:
        print("No valid temporal observations available.")

    print()
    print("=" * 100)
    print("STRESS RESPONSE RECONCILIATION")
    print("=" * 100)
    print(
        f"Stress observations : "
        f"{stress.get('observations', 0)}"
    )
    print(f"Status              : {stress.get('status')}")

    if stress.get("reason"):
        print(f"Reason              : {stress.get('reason')}")

    if stress.get("breaches") is not None:
        print(f"Stress breaches     : {stress['breaches']}")

    print()
    print("=" * 100)
    print("RISK REGIME CIRCUIT BREAKER")
    print("=" * 100)
    print(f"State  : {breaker['state']}")
    print(f"Reason : {breaker['reason']}")

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO RISK REGIME STABILITY "
        "+ STRESS RESPONSE RECONCILIATION VERDICT"
    )
    print("=" * 100)

    print("UPSTREAM_STATE_CONSUMED       : PASS")
    print(
        "RISK_REGIME_STABILITY        : "
        f"{stability.get('status')}"
    )
    print(
        "STRESS_RESPONSE_RECONCILIATION : "
        f"{stress.get('status')}"
    )
    print(
        "CIRCUIT_BREAKER              : "
        f"{breaker['state']}"
    )
    print("PRODUCTION_ISOLATION         : PASS")
    print(f"FRONTIER VERDICT             : {verdict}")

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(f"Before rows  : {before.get('rows')}")
    print(f"After rows   : {after.get('rows')}")
    print(f"Before size  : {before.get('size')}")
    print(f"After size   : {after.get('size')}")
    print(f"Before SHA256: {before.get('sha256')}")
    print(f"After SHA256 : {after.get('sha256')}")

    unchanged = (
        before.get("rows") == after.get("rows")
        and before.get("size") == after.get("size")
        and before.get("sha256") == after.get("sha256")
    )

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if unchanged else "FAIL")
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

    if verdict == "INSUFFICIENT_DATA":
        print()
        print(
            "Insufficient temporal snapshots for a valid "
            "risk-regime stability / stress-response analysis."
        )

    print()
    print(f"Runtime report : {RUNTIME_REPORT}")


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    before = db_fingerprint(DB_PATH)

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "RISK REGIME STABILITY + STRESS RESPONSE "
        "RECONCILIATION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {before.get('rows')}")
    print(f"Size   : {before.get('size')}")
    print(f"SHA256 : {before.get('sha256')}")

    upstream = load_json(UPSTREAM_REPORT)
    upstream = validate_upstream(upstream)

    snapshots = sort_snapshots(
        extract_snapshots(upstream)
    )

    stability = analyze_stability(snapshots)
    stress = stress_response(snapshots)
    breaker = circuit_breaker(snapshots)

    # No production write is performed.
    after = db_fingerprint(DB_PATH)

    db_unchanged = (
        before.get("rows") == after.get("rows")
        and before.get("size") == after.get("size")
        and before.get("sha256") == after.get("sha256")
    )

    if not db_unchanged:
        raise RuntimeError(
            "PRODUCTION DATABASE INVARIANT FAILED."
        )

    if not snapshots:
        verdict = "INSUFFICIENT_DATA"

    elif (
        stability["status"] == "PASS"
        and stress["status"] == "PASS"
        and breaker["state"] == "CLEAR"
    ):
        verdict = "PASS"

    else:
        verdict = "FAIL"

    report = build_report(
        upstream=upstream,
        snapshots=snapshots,
        stability=stability,
        stress=stress,
        breaker=breaker,
        before=before,
        after=after,
    )

    os.makedirs(
        LIVE_CAPTURE_DIR,
        exist_ok=True,
    )

    with open(
        RUNTIME_REPORT,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print_report(
        upstream=upstream,
        snapshots=snapshots,
        stability=stability,
        stress=stress,
        breaker=breaker,
        before=before,
        after=after,
        verdict=verdict,
    )


if __name__ == "__main__":
    main()