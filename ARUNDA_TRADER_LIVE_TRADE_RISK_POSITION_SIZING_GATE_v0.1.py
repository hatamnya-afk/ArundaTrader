# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE TRADE RISK + POSITION SIZING GATE v0.2

Purpose
-------
Consume the already-verified upstream candidate-ranking frontier and
evaluate trade risk / position sizing ONLY for candidates that have
already passed the upstream eligibility gate.

IMPORTANT PROJECT RULES
-----------------------
- Do NOT re-audit previous frontiers.
- Do NOT execute fusion_engine.main().
- Do NOT modify production DB.
- Do NOT reconstruct direction.
- Do NOT reconstruct scores.
- Do NOT inject live data.
- Do NOT repair historical data.
- Do NOT place orders.
- Do NOT perform exchange execution.
- Do NOT invent candidates.
- Empty upstream candidate pool => NO_TRADE.

Upstream frontier:
    ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING + MULTI-ASSET DECISION GATE v0.1

Output:
    Analytical risk classification and position-sizing proposal only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =================================================================================================
# CONFIGURATION
# =================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

CAPTURE_ROOT = Path(
    os.environ.get(
        "ARUNDA_LIVE_CAPTURE_ROOT",
        r"C:\Users\ASUS\AppData\Local\Temp",
    )
)

UPSTREAM_REPORT_NAME = "LIVE_TRADE_CANDIDATE_RANKING_REPORT.json"

OUTPUT_REPORT_NAME = "LIVE_TRADE_RISK_POSITION_SIZING_REPORT.json"

CURRENT_ENGINE = "FUSION_v0.5"


# -------------------------------------------------------------------------------------------------
# Risk configuration
#
# These are ANALYTICAL limits only.
# They do not create orders and do not interact with an exchange.
# -------------------------------------------------------------------------------------------------

ACCOUNT_EQUITY = 100.0

MAX_RISK_PER_TRADE = 0.01
MAX_PORTFOLIO_RISK = 0.02

MIN_CONFIDENCE = 0.60

MIN_AVAILABLE_WEIGHT = 0.65

REQUIRE_VERIFIED_QUALITY = True

REQUIRE_NON_FLAT_DIRECTION = True

REQUIRE_ENTRY_PRICE = True

MAX_POSITION_FRACTION = 0.25

DEFAULT_STOP_DISTANCE_PCT = 0.02


# =================================================================================================
# UTILITY
# =================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def db_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()

    with sqlite3.connect(path) as conn:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]

    return {
        "rows": row_count,
        "size": stat.st_size,
        "sha256": sha256_file(path),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# =================================================================================================
# CAPTURE DISCOVERY
# =================================================================================================

def discover_latest_capture() -> Path:
    candidates = []

    if not CAPTURE_ROOT.exists():
        raise FileNotFoundError(
            f"Capture root does not exist: {CAPTURE_ROOT}"
        )

    for path in CAPTURE_ROOT.glob("arunda_live_launch_*"):
        if not path.is_dir():
            continue

        db = path / "arunda_live_capture.db"

        if db.exists():
            candidates.append(path)

    if not candidates:
        raise FileNotFoundError(
            "No arunda_live_launch_* capture directory found."
        )

    candidates.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return candidates[0]


# =================================================================================================
# UPSTREAM REPORT DISCOVERY
# =================================================================================================

def discover_upstream_report(capture_dir: Path) -> Path:
    direct = capture_dir / UPSTREAM_REPORT_NAME

    if direct.exists():
        return direct

    # Search recursively inside capture directory.
    matches = list(capture_dir.rglob(UPSTREAM_REPORT_NAME))

    if matches:
        matches.sort(
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        return matches[0]

    # Fallback: search project root.
    project_matches = list(
        PROJECT_ROOT.glob(UPSTREAM_REPORT_NAME)
    )

    if project_matches:
        project_matches.sort(
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        return project_matches[0]

    raise FileNotFoundError(
        f"Upstream report not found: {UPSTREAM_REPORT_NAME}"
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            "Upstream report root must be a JSON object."
        )

    return data


# =================================================================================================
# UPSTREAM CONTRACT
# =================================================================================================

def validate_upstream_identity(report: dict[str, Any]) -> None:
    """
    Validate only structural usability of the upstream report.

    This function intentionally does NOT:
      - inspect fusion_signals
      - re-run eligibility
      - reconstruct candidates
      - reconstruct snapshot identity
      - infer direction
      - infer score
    """

    if not isinstance(report, dict):
        raise ValueError(
            "Upstream report root must be a JSON object."
        )

    candidate_fields = (
        "selected_candidates",
        "eligible_candidates",
        "candidates",
    )

    if any(
        isinstance(report.get(field), list)
        for field in candidate_fields
    ):
        return

    eligible_pool = report.get("eligible_pool")

    if isinstance(eligible_pool, (dict, list)):
        return

    # Known zero-candidate reports can legitimately expose
    # the result only through summary metadata.
    summary_fields = (
        "selected_count",
        "selected_candidates_count",
        "eligible_count",
        "eligible_candidates_count",
        "candidate_count",
    )

    if any(field in report for field in summary_fields):
        return

    raise ValueError(
        "Upstream report does not expose a usable candidate pool."
    )


# =================================================================================================
# CANDIDATE EXTRACTION
# =================================================================================================

def extract_candidate_pool(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Consume candidates already selected by the upstream frontier.

    No candidate is reconstructed from the production database.
    """

    possible_fields = (
        "selected_candidates",
        "eligible_candidates",
        "candidates",
    )

    for field in possible_fields:
        value = report.get(field)

        if isinstance(value, list):
            return [
                x for x in value
                if isinstance(x, dict)
            ]

    eligible_pool = report.get("eligible_pool")

    if isinstance(eligible_pool, list):
        return [
            x for x in eligible_pool
            if isinstance(x, dict)
        ]

    if isinstance(eligible_pool, dict):
        for field in (
            "candidates",
            "eligible_candidates",
            "selected_candidates",
            "items",
        ):
            value = eligible_pool.get(field)

            if isinstance(value, list):
                return [
                    x for x in value
                    if isinstance(x, dict)
                ]

        return []

    return []


# =================================================================================================
# NORMALIZATION
# =================================================================================================

def as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().upper()

    if text in {"1", "TRUE", "YES", "ON", "AVAILABLE"}:
        return True

    if text in {"0", "FALSE", "NO", "OFF", "UNAVAILABLE"}:
        return False

    return None


def candidate_value(
    candidate: dict[str, Any],
    *names: str,
) -> Any:
    for name in names:
        if name in candidate:
            return candidate[name]

    return None


# =================================================================================================
# RISK EVALUATION
# =================================================================================================

def evaluate_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:

    asset = candidate_value(
        candidate,
        "asset",
        "symbol",
    )

    direction = candidate_value(
        candidate,
        "direction",
    )

    confidence = as_float(
        candidate_value(
            candidate,
            "confidence",
        )
    )

    available_weight = as_float(
        candidate_value(
            candidate,
            "available_weight",
        )
    )

    data_quality = candidate_value(
        candidate,
        "data_quality",
        "quality",
    )

    entry_price = as_float(
        candidate_value(
            candidate,
            "entry_price",
        )
    )

    signal_strength = candidate_value(
        candidate,
        "signal_strength",
        "strength",
    )

    market_available = as_bool(
        candidate_value(
            candidate,
            "market_available",
            "market",
        )
    )

    positioning_available = as_bool(
        candidate_value(
            candidate,
            "positioning_available",
            "positioning",
        )
    )

    news_available = as_bool(
        candidate_value(
            candidate,
            "news_available",
            "news",
        )
    )

    reasons: list[str] = []

    # ---------------------------------------------------------------------------------------------
    # Structural safety
    # ---------------------------------------------------------------------------------------------

    if not asset:
        reasons.append("MISSING_ASSET")

    normalized_direction = (
        str(direction).upper()
        if direction is not None
        else ""
    )

    if REQUIRE_NON_FLAT_DIRECTION:
        if normalized_direction not in {"LONG", "SHORT"}:
            reasons.append("NON_TRADE_DIRECTION")

    if confidence is None:
        reasons.append("MISSING_CONFIDENCE")
    elif confidence < MIN_CONFIDENCE:
        reasons.append("CONFIDENCE_BELOW_RISK_GATE")

    if available_weight is None:
        reasons.append("MISSING_AVAILABLE_WEIGHT")
    elif available_weight < MIN_AVAILABLE_WEIGHT:
        reasons.append("INSUFFICIENT_AVAILABLE_WEIGHT")

    normalized_quality = (
        str(data_quality).upper()
        if data_quality is not None
        else ""
    )

    if REQUIRE_VERIFIED_QUALITY:
        if normalized_quality != "VERIFIED":
            reasons.append("DATA_QUALITY_NOT_VERIFIED")

    normalized_strength = (
        str(signal_strength).upper()
        if signal_strength is not None
        else ""
    )

    if normalized_strength in {"WEAK", ""}:
        reasons.append("WEAK_SIGNAL")

    if REQUIRE_ENTRY_PRICE:
        if entry_price is None or entry_price <= 0:
            reasons.append("INVALID_ENTRY_PRICE")

    # ---------------------------------------------------------------------------------------------
    # Arm safety
    # ---------------------------------------------------------------------------------------------

    arms = {
        "market": market_available,
        "positioning": positioning_available,
        "news": news_available,
    }

    known_arms = [
        value
        for value in arms.values()
        if value is not None
    ]

    available_arms = sum(
        1
        for value in known_arms
        if value
    )

    if available_arms == 0:
        reasons.append("NO_AVAILABLE_ARMS")

    # ---------------------------------------------------------------------------------------------
    # Decision
    # ---------------------------------------------------------------------------------------------

    eligible = len(reasons) == 0

    if not eligible:
        return {
            "asset": asset,
            "direction": normalized_direction,
            "confidence": confidence,
            "available_weight": available_weight,
            "data_quality": normalized_quality,
            "signal_strength": normalized_strength,
            "entry_price": entry_price,
            "arms": arms,
            "available_arms": available_arms,
            "risk_status": "NO_TRADE",
            "position_status": "NOT_SIZED",
            "risk_reasons": reasons,
            "risk_fraction": 0.0,
            "risk_amount": 0.0,
            "position_fraction": 0.0,
            "position_notional": 0.0,
        }

    # ---------------------------------------------------------------------------------------------
    # Position sizing
    #
    # Conservative analytical sizing:
    # risk budget = equity * max risk per trade
    #
    # Stop distance is intentionally fixed as an analytical placeholder.
    # It is NOT an order instruction.
    # ---------------------------------------------------------------------------------------------

    risk_budget = (
        ACCOUNT_EQUITY *
        MAX_RISK_PER_TRADE
    )

    stop_distance = DEFAULT_STOP_DISTANCE_PCT

    position_notional = (
        risk_budget / stop_distance
    )

    max_notional = (
        ACCOUNT_EQUITY *
        MAX_POSITION_FRACTION
    )

    position_notional = min(
        position_notional,
        max_notional,
    )

    position_fraction = (
        position_notional / ACCOUNT_EQUITY
        if ACCOUNT_EQUITY > 0
        else 0.0
    )

    return {
        "asset": asset,
        "direction": normalized_direction,
        "confidence": confidence,
        "available_weight": available_weight,
        "data_quality": normalized_quality,
        "signal_strength": normalized_strength,
        "entry_price": entry_price,
        "arms": arms,
        "available_arms": available_arms,
        "risk_status": "RISK_ACCEPTED",
        "position_status": "SIZED_ANALYTICALLY",
        "risk_reasons": [],
        "risk_fraction": MAX_RISK_PER_TRADE,
        "risk_amount": risk_budget,
        "position_fraction": position_fraction,
        "position_notional": position_notional,
        "stop_distance_pct": stop_distance,
    }


# =================================================================================================
# MULTI-ASSET PORTFOLIO SAFETY
# =================================================================================================

def apply_portfolio_risk_cap(
    evaluated: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    accepted = [
        x for x in evaluated
        if x.get("risk_status") == "RISK_ACCEPTED"
    ]

    if not accepted:
        return evaluated

    total_risk = sum(
        float(x.get("risk_fraction", 0.0))
        for x in accepted
    )

    if total_risk <= MAX_PORTFOLIO_RISK:
        return evaluated

    scale = (
        MAX_PORTFOLIO_RISK / total_risk
        if total_risk > 0
        else 0.0
    )

    for item in accepted:

        item["risk_fraction"] *= scale
        item["risk_amount"] *= scale
        item["position_notional"] *= scale

        item["position_fraction"] = (
            item["position_notional"] / ACCOUNT_EQUITY
            if ACCOUNT_EQUITY > 0
            else 0.0
        )

        item["portfolio_risk_scaled"] = True

    return evaluated


# =================================================================================================
# REPORT
# =================================================================================================

def build_report(
    production_before: dict[str, Any],
    production_after: dict[str, Any],
    capture_dir: Path,
    capture_db: Path,
    upstream_report: Path,
    upstream: dict[str, Any],
    candidates: list[dict[str, Any]],
    evaluated: list[dict[str, Any]],
) -> dict[str, Any]:

    accepted = [
        x for x in evaluated
        if x.get("risk_status") == "RISK_ACCEPTED"
    ]

    rejected = [
        x for x in evaluated
        if x.get("risk_status") != "RISK_ACCEPTED"
    ]

    return {
        "report_version": "ARUNDA_TRADER_LIVE_TRADE_RISK_POSITION_SIZING_GATE_v0.2",
        "generated_at": utc_now(),

        "objective": (
            "Consume already-verified upstream trade candidates and "
            "evaluate analytical risk and position sizing."
        ),

        "production_safety": {
            "production_db_writes": False,
            "production_engine_run": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "order_execution": False,
        },

        "production_baseline": production_before,

        "production_after": production_after,

        "production_invariant": (
            production_before == production_after
        ),

        "capture": {
            "directory": str(capture_dir),
            "database": str(capture_db),
        },

        "upstream": {
            "report": str(upstream_report),
            "snapshot": (
                upstream.get("snapshot")
                or upstream.get("snapshot_id")
                or upstream.get("current_snapshot")
                or upstream.get("current_snapshot_id")
                or "UPSTREAM_SNAPSHOT_NOT_EXPOSED"
            ),
        },

        "candidate_pool": {
            "received": len(candidates),
            "evaluated": len(evaluated),
            "risk_accepted": len(accepted),
            "no_trade": len(rejected),
        },

        "risk_configuration": {
            "account_equity": ACCOUNT_EQUITY,
            "max_risk_per_trade": MAX_RISK_PER_TRADE,
            "max_portfolio_risk": MAX_PORTFOLIO_RISK,
            "min_confidence": MIN_CONFIDENCE,
            "min_available_weight": MIN_AVAILABLE_WEIGHT,
            "require_verified_quality": REQUIRE_VERIFIED_QUALITY,
            "require_non_flat_direction": REQUIRE_NON_FLAT_DIRECTION,
            "require_entry_price": REQUIRE_ENTRY_PRICE,
            "max_position_fraction": MAX_POSITION_FRACTION,
            "default_stop_distance_pct": DEFAULT_STOP_DISTANCE_PCT,
        },

        "evaluations": evaluated,

        "frontier_verdict": (
            "RISK_CANDIDATES_AVAILABLE"
            if accepted
            else "NO_TRADE_RISK"
        ),

        "order_execution": False,
    }


# =================================================================================================
# MAIN
# =================================================================================================

def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE TRADE RISK + POSITION SIZING GATE v0.2"
    )
    print("=" * 100)

    print(
        """
OBJECTIVE:
  Consume ONLY candidates already passed by the upstream
  LIVE TRADE CANDIDATE RANKING + MULTI-ASSET DECISION GATE.

Previously verified frontiers are NOT re-audited.

Production DB writes : FORBIDDEN
Production engine run : NO
Historical repair     : NONE
Direction inference   : NONE
Score reconstruction  : NONE
Synthetic data        : FORBIDDEN
Live data injection   : NONE
Order execution       : NONE
"""
    )

    # ---------------------------------------------------------------------------------------------
    # Production baseline
    # ---------------------------------------------------------------------------------------------

    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    production_before = db_fingerprint(PRODUCTION_DB)

    print(
        f"Rows   : {production_before['rows']}"
    )
    print(
        f"Size   : {production_before['size']}"
    )
    print(
        f"SHA256 : {production_before['sha256']}"
    )

    # ---------------------------------------------------------------------------------------------
    # Capture
    # ---------------------------------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("LIVE CAPTURE")
    print("=" * 100)

    capture_dir = discover_latest_capture()

    capture_db = capture_dir / "arunda_live_capture.db"

    print(f"Directory : {capture_dir}")
    print(f"Database  : {capture_db}")

    if not capture_db.exists():
        raise FileNotFoundError(
            f"Capture DB not found: {capture_db}"
        )

    # ---------------------------------------------------------------------------------------------
    # Upstream report
    # ---------------------------------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    upstream_report = discover_upstream_report(
        capture_dir
    )

    print(
        f"Report : {upstream_report}"
    )

    upstream = load_json(upstream_report)

    validate_upstream_identity(upstream)

    snapshot = (
        upstream.get("snapshot")
        or upstream.get("snapshot_id")
        or upstream.get("current_snapshot")
        or upstream.get("current_snapshot_id")
        or "UPSTREAM_SNAPSHOT_NOT_EXPOSED"
    )

    print(
        f"Snapshot : {snapshot}"
    )

    # ---------------------------------------------------------------------------------------------
    # Consume upstream candidates
    # ---------------------------------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("UPSTREAM ELIGIBLE CANDIDATE POOL")
    print("=" * 100)

    candidates = extract_candidate_pool(upstream)

    print(
        f"Candidates received : {len(candidates)}"
    )

    # ---------------------------------------------------------------------------------------------
    # Empty candidate pool
    # ---------------------------------------------------------------------------------------------

    if not candidates:

        print(
            """
No eligible candidates received from upstream.

Risk evaluation : NOT PERFORMED
Position sizing : NOT PERFORMED
Reason          : UPSTREAM_POOL_EMPTY
"""
        )

        evaluated: list[dict[str, Any]] = []

    else:

        print("\n" + "=" * 100)
        print("RISK + POSITION SIZING EVALUATION")
        print("=" * 100)

        evaluated = []

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):

            result = evaluate_candidate(
                candidate
            )

            result["rank"] = index

            evaluated.append(result)

            print(
                f"{index:02d} | "
                f"{str(result.get('asset')):<6} | "
                f"{str(result.get('direction')):<5} | "
                f"CONF={result.get('confidence')} | "
                f"QUALITY={result.get('data_quality'):<10} | "
                f"RISK={result.get('risk_status')}"
            )

            if result["risk_reasons"]:
                for reason in result["risk_reasons"]:
                    print(
                        f"     - {reason}"
                    )

        evaluated = apply_portfolio_risk_cap(
            evaluated
        )

    # ---------------------------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------------------------

    accepted = [
        x for x in evaluated
        if x.get("risk_status") == "RISK_ACCEPTED"
    ]

    rejected = [
        x for x in evaluated
        if x.get("risk_status") != "RISK_ACCEPTED"
    ]

    print("\n" + "=" * 100)
    print("RISK SUMMARY")
    print("=" * 100)

    print(
        f"RISK_ACCEPTED : {len(accepted)}"
    )

    print(
        f"NO_TRADE      : {len(rejected)}"
    )

    total_risk = sum(
        float(x.get("risk_fraction", 0.0))
        for x in accepted
    )

    total_notional = sum(
        float(x.get("position_notional", 0.0))
        for x in accepted
    )

    print(
        f"Portfolio risk : {total_risk:.6f}"
    )

    print(
        f"Total analytical notional : {total_notional:.6f}"
    )

    # ---------------------------------------------------------------------------------------------
    # Production invariant
    # ---------------------------------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    production_after = db_fingerprint(
        PRODUCTION_DB
    )

    print(
        f"Before rows : {production_before['rows']}"
    )
    print(
        f"After rows  : {production_after['rows']}"
    )

    print(
        f"Before size : {production_before['size']}"
    )
    print(
        f"After size  : {production_after['size']}"
    )

    print(
        f"Before SHA256 : {production_before['sha256']}"
    )
    print(
        f"After SHA256  : {production_after['sha256']}"
    )

    invariant_pass = (
        production_before == production_after
    )

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if invariant_pass else "FAIL")
    )

    if not invariant_pass:
        raise RuntimeError(
            "Production DB changed unexpectedly."
        )

    # ---------------------------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------------------------

    report = build_report(
        production_before=production_before,
        production_after=production_after,
        capture_dir=capture_dir,
        capture_db=capture_db,
        upstream_report=upstream_report,
        upstream=upstream,
        candidates=candidates,
        evaluated=evaluated,
    )

    output_path = (
        capture_dir /
        OUTPUT_REPORT_NAME
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ---------------------------------------------------------------------------------------------
    # Final verdict
    # ---------------------------------------------------------------------------------------------

    print("\n" + "=" * 100)
    print(
        "LIVE TRADE RISK + POSITION SIZING VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_CANDIDATES_CONSUMED : PASS"
    )

    print(
        "RISK_EVALUATION              : "
        + ("PASS" if candidates else "NOT_PERFORMED")
    )

    print(
        "POSITION_SIZING              : "
        + ("ANALYTICAL_ONLY" if accepted else "NOT_PERFORMED")
    )

    print(
        "PRODUCTION_ISOLATION         : PASS"
    )

    if accepted:
        frontier_verdict = (
            "RISK_CANDIDATES_AVAILABLE"
        )
    else:
        frontier_verdict = "NO_TRADE_RISK"

    print(
        f"FRONTIER VERDICT             : {frontier_verdict}"
    )

    print(
        f"\nRuntime report : {output_path}"
    )

    print("\n" + "=" * 100)
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

    print(
        "\nRisk and position sizing are analytical only."
    )

    print(
        "No trading order or execution action is performed."
    )

    return 0


# =================================================================================================
# ENTRY POINT
# =================================================================================================

if __name__ == "__main__":
    try:
        sys.exit(main())

    except Exception as exc:

        print("\n" + "=" * 100)
        print("FRONTIER EXECUTION ERROR")
        print("=" * 100)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print(
            "\nNO TRADING ACTION WAS PERFORMED."
        )

        sys.exit(1)