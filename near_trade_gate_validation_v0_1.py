# =============================================================================
# ARUNDA MANAGER COMMAND
# NEAR TRADE GATE VALIDATION v0.2
# =============================================================================
#
# READ-ONLY CURRENT RUNTIME VALIDATION
#
# TARGET:
#   NEAR
#
# FLOW:
#   CURRENT OPPORTUNITY v0.6
#       ->
#   CURRENT SIGNAL / SCORE / DECISION RUNTIME
#       ->
#   CURRENT RISK ENGINE
#       ->
#   CURRENT TRADE GATE
#
# SAFETY:
#   DB_WRITES=0
#   ORDER_INTENTS=0
#   EXECUTION=OFF
#
# IMPORTANT:
#   Does NOT call arunda_pipeline.main()
#   because that legacy orchestration expects an old Opportunity
#   runtime marker which Opportunity v0.6 intentionally does not emit.
#
#   This validator calls the existing production functions directly.
#   No business logic is reimplemented.
# =============================================================================

from __future__ import annotations

import contextlib
import io
import os
import sys
from typing import Any, Mapping


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_DIR = r"C:\Users\ASUS\ArundaTrader"

TARGET_ASSET = "NEAR"

EXPECTED_OPPORTUNITY = "ELIGIBLE"
EXPECTED_DIRECTION = "LONG"
EXPECTED_SCORE = 37.2398
EXPECTED_CONFIDENCE = 0.6164

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]

EXECUTION_ENABLED = False


# =============================================================================
# PATH
# =============================================================================

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


# =============================================================================
# CURRENT PRODUCTION MODULES
# =============================================================================

import opportunity_engine
import arunda_pipeline
import trade_gate_engine


# =============================================================================
# HELPERS
# =============================================================================

def norm(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().upper()


def safe_float(value: Any):

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def get_asset(row: Any) -> str:

    if not isinstance(row, Mapping):
        return ""

    for key in (
        "asset",
        "symbol",
        "ticker",
    ):

        value = row.get(key)

        if value is not None:

            value = norm(value)

            if value:
                return value

    return ""


def extract_rows(
    snapshot: Any,
) -> list:

    if isinstance(snapshot, list):
        return [
            row
            for row in snapshot
            if isinstance(row, Mapping)
        ]

    if isinstance(snapshot, tuple):
        return [
            row
            for row in snapshot
            if isinstance(row, Mapping)
        ]

    if not isinstance(snapshot, Mapping):

        raise RuntimeError(
            "Snapshot must be mapping/list/tuple"
        )

    for key in (
        "decisions",
        "risk",
        "risks",
        "rows",
        "results",
        "snapshot",
        "data",
        "payload",
    ):

        value = snapshot.get(key)

        if isinstance(value, (list, tuple)):

            return [
                row
                for row in value
                if isinstance(row, Mapping)
            ]

        if isinstance(value, Mapping):

            rows = []

            for asset, row in value.items():

                if not isinstance(row, Mapping):
                    continue

                item = dict(row)

                if not get_asset(item):
                    item["asset"] = asset

                rows.append(item)

            if rows:
                return rows

    rows = []

    for asset, row in snapshot.items():

        if not isinstance(row, Mapping):
            continue

        item = dict(row)

        if not get_asset(item):
            item["asset"] = asset

        rows.append(item)

    if rows:
        return rows

    raise RuntimeError(
        "Could not extract runtime rows"
    )


def build_asset_map(
    rows: Any,
) -> dict:

    result = {}

    for row in extract_rows(rows):

        asset = get_asset(row)

        if not asset:
            continue

        if asset in result:

            raise RuntimeError(
                f"Duplicate runtime asset: {asset}"
            )

        result[asset] = dict(row)

    return result


def find_asset(
    rows: Any,
    asset: str,
) -> Mapping[str, Any]:

    mapping = build_asset_map(rows)

    if asset not in mapping:

        raise RuntimeError(
            f"{asset}: runtime record not found"
        )

    return mapping[asset]


# =============================================================================
# OPPORTUNITY
# =============================================================================

def run_current_opportunity():

    """
    Execute Opportunity v0.6 directly.

    IMPORTANT:
        We intentionally use the existing module function instead of
        arunda_pipeline.main(), because the current Opportunity v0.6
        does not emit the legacy pipeline marker.
    """

    runner = getattr(
        opportunity_engine,
        "run",
        None,
    )

    if not callable(runner):

        raise RuntimeError(
            "opportunity_engine.run() not found"
        )

    captured = io.StringIO()

    with contextlib.redirect_stdout(captured):

        result = runner()

    return result, captured.getvalue()


def extract_opportunities(
    result: Any,
    stdout: str,
) -> list:

    # -------------------------------------------------------------------------
    # Preferred: direct runtime return
    # -------------------------------------------------------------------------

    if isinstance(result, Mapping):

        for key in (
            "opportunities",
            "results",
            "rows",
            "data",
        ):

            value = result.get(key)

            if isinstance(value, (list, tuple)):

                return [
                    dict(row)
                    for row in value
                    if isinstance(row, Mapping)
                ]

        # Asset-keyed mapping
        rows = []

        for asset, row in result.items():

            if (
                norm(asset)
                in set(EXPECTED_ASSETS)
                and isinstance(row, Mapping)
            ):

                item = dict(row)

                if not get_asset(item):
                    item["asset"] = asset

                rows.append(item)

        if rows:
            return rows

    if isinstance(result, (list, tuple)):

        return [
            dict(row)
            for row in result
            if isinstance(row, Mapping)
        ]

    # -------------------------------------------------------------------------
    # Defensive stdout parser for current v0.6 human output
    # -------------------------------------------------------------------------

    rows = []

    for raw_line in stdout.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        parts = [
            part.strip()
            for part in line.split("|")
        ]

        if len(parts) < 5:
            continue

        asset = norm(parts[0])

        if asset not in EXPECTED_ASSETS:
            continue

        fields = {}

        for part in parts[1:]:

            if "=" not in part:
                continue

            key, value = part.split(
                "=",
                1,
            )

            fields[
                key.strip().lower()
            ] = value.strip()

        if not fields:
            continue

        row = {
            "asset": asset,
        }

        if "status" in fields:
            row["status"] = fields["status"]

        if "direction" in fields:
            row["direction"] = fields["direction"]

        if "score" in fields:
            row["score"] = safe_float(
                fields["score"]
            )

        if "conf" in fields:
            row["confidence"] = safe_float(
                fields["conf"]
            )

        if "points" in fields:
            try:
                row["market_data_points"] = int(
                    fields["points"]
                )
            except ValueError:
                pass

        if "source" in fields:
            row["source"] = fields["source"]

        rows.append(row)

    if rows:
        return rows

    raise RuntimeError(
        "Current Opportunity runtime rows unavailable"
    )


# =============================================================================
# DECISION + RISK
# =============================================================================

def run_current_decision():

    """
    Use the actual existing Pipeline helper.

    No Decision logic is reproduced here.
    """

    runner = getattr(
        arunda_pipeline,
        "run_signal_score_decision_runtime",
        None,
    )

    if not callable(runner):

        raise RuntimeError(
            "run_signal_score_decision_runtime() not found"
        )

    return runner()


def run_current_risk(
    decision_snapshot,
):

    runner = getattr(
        arunda_pipeline,
        "run_risk_stage",
        None,
    )

    if not callable(runner):

        raise RuntimeError(
            "run_risk_stage() not found"
        )

    return runner(
        decision_snapshot
    )


# =============================================================================
# TRADE GATE
# =============================================================================

def run_current_trade_gate(
    opportunity_rows,
    decision_snapshot,
    risk_snapshot,
):

    runner = getattr(
        trade_gate_engine,
        "run_runtime",
        None,
    )

    if not callable(runner):

        raise RuntimeError(
            "trade_gate_engine.run_runtime() not found"
        )

    return runner(
        opportunity_rows,
        decision_snapshot,
        risk_snapshot,
    )


# =============================================================================
# AUTHORITATIVE SINGLE-ASSET CHECK
# =============================================================================

def authoritative_check(
    opportunity,
    decision,
    risk,
):

    adapted = (
        trade_gate_engine.adapt_opportunity(
            dict(opportunity),
            dict(decision),
        )
    )

    status, reasons = (
        trade_gate_engine.evaluate(
            adapted,
            dict(decision),
            dict(risk),
        )
    )

    observability = (
        trade_gate_engine.build_gate_observability(
            adapted,
            dict(decision),
            dict(risk),
        )
    )

    return (
        status,
        reasons,
        observability,
        adapted,
    )


# =============================================================================
# OPTIONAL BUDGET / POSITION SIZING DISCOVERY
# =============================================================================

def discover_optional_layers():

    """
    These are intentionally discovery-only.

    If current Trade Gate does not expose Budget or Position Sizing
    as authoritative predicates, we report NOT_IN_CURRENT_GATE_CONTRACT.

    We never invent values.
    """

    budget = None
    sizing = None

    for module_name in (
        "risk_budget_engine",
        "budget_engine",
        "risk_budget",
    ):

        try:

            module = __import__(
                module_name
            )

        except Exception:
            continue

        for name in (
            "run",
            "evaluate",
            "calculate",
        ):

            if callable(
                getattr(module, name, None)
            ):

                budget = (
                    module_name,
                    name,
                )

                break

        if budget:
            break

    for module_name in (
        "position_sizing",
        "position_sizing_engine",
    ):

        try:

            module = __import__(
                module_name
            )

        except Exception:
            continue

        for name in (
            "run",
            "calculate",
            "position_size",
        ):

            if callable(
                getattr(module, name, None)
            ):

                sizing = (
                    module_name,
                    name,
                )

                break

        if sizing:
            break

    return budget, sizing


# =============================================================================
# MAIN
# =============================================================================

def main():

    if EXECUTION_ENABLED:

        raise RuntimeError(
            "Execution must remain OFF"
        )

    print(
        "ARUNDA MANAGER COMMAND — "
        "NEAR TRADE GATE VALIDATION v0.2"
    )

    print(
        "MODE=READ_ONLY"
    )

    print(
        "TARGET=NEAR"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    # =========================================================================
    # 1. CURRENT OPPORTUNITY
    # =========================================================================

    opportunity_result, opportunity_stdout = (
        run_current_opportunity()
    )

    opportunity_rows = extract_opportunities(
        opportunity_result,
        opportunity_stdout,
    )

    opportunity_map = build_asset_map(
        opportunity_rows
    )

    if set(opportunity_map) != set(
        EXPECTED_ASSETS
    ):

        missing = sorted(
            set(EXPECTED_ASSETS)
            - set(opportunity_map)
        )

        extra = sorted(
            set(opportunity_map)
            - set(EXPECTED_ASSETS)
        )

        raise RuntimeError(
            "Opportunity coverage failure: "
            f"missing={missing}, extra={extra}"
        )

    opportunity = opportunity_map[
        TARGET_ASSET
    ]

    # =========================================================================
    # 2. CURRENT DECISION
    # =========================================================================

    decision_runtime = (
        run_current_decision()
    )

    if not isinstance(
        decision_runtime,
        Mapping,
    ):

        raise RuntimeError(
            "Decision runtime invalid"
        )

    decision_snapshot = (
        decision_runtime[
            "decision_snapshot"
        ]
    )

    decision = find_asset(
        decision_snapshot,
        TARGET_ASSET,
    )

    # =========================================================================
    # 3. CURRENT RISK
    # =========================================================================

    risk_snapshot = run_current_risk(
        decision_snapshot
    )

    risk = find_asset(
        risk_snapshot,
        TARGET_ASSET,
    )

    # =========================================================================
    # 4. CURRENT TRADE GATE RUNTIME
    # =========================================================================

    gate_results = run_current_trade_gate(
        opportunity_rows,
        decision_snapshot,
        risk_snapshot,
    )

    gate = find_asset(
        gate_results,
        TARGET_ASSET,
    )

    # =========================================================================
    # 5. AUTHORITATIVE SINGLE-ASSET EVALUATION
    # =========================================================================

    (
        authoritative_status,
        reasons,
        observability,
        adapted_opportunity,
    ) = authoritative_check(
        opportunity,
        decision,
        risk,
    )

    runtime_gate_status = norm(
        gate.get(
            "trade_gate_status"
        )
    )

    if runtime_gate_status != norm(
        authoritative_status
    ):

        raise RuntimeError(
            "Trade Gate runtime / authoritative mismatch: "
            f"{runtime_gate_status} != "
            f"{authoritative_status}"
        )

    # =========================================================================
    # 6. OPTIONAL LAYER DISCOVERY
    # =========================================================================

    budget_layer, sizing_layer = (
        discover_optional_layers()
    )

    # =========================================================================
    # 7. EXTRACT REAL VALUES
    # =========================================================================

    opportunity_status = norm(
        opportunity.get(
            "status",
            opportunity.get(
                "opportunity_status"
            ),
        )
    )

    direction = norm(
        opportunity.get(
            "direction"
        )
    )

    score = safe_float(
        opportunity.get(
            "score",
            opportunity.get(
                "opportunity_score"
            ),
        )
    )

    confidence = safe_float(
        opportunity.get(
            "confidence"
        )
    )

    decision_state = norm(
        decision.get(
            "state",
            decision.get(
                "decision"
            ),
        )
    )

    decision_direction = norm(
        decision.get(
            "direction"
        )
    )

    decision_score = safe_float(
        decision.get(
            "score"
        )
    )

    risk_state = norm(
        risk.get(
            "risk_state",
            risk.get(
                "status"
            ),
        )
    )

    risk_decision = norm(
        risk.get(
            "risk_decision",
            risk.get(
                "decision"
            ),
        )
    )

    stop_distance = risk.get(
        "stop_distance"
    )

    if stop_distance is None:
        stop_distance = risk.get(
            "stop_distance_pct"
        )

    risk_reward = safe_float(
        risk.get(
            "risk_reward"
        )
    )

    # =========================================================================
    # 8. PREDICATES
    # =========================================================================

    passed = [
        item["name"]
        for item in observability
        if item.get("pass") is True
    ]

    failed = [
        item["name"]
        for item in observability
        if item.get("pass") is not True
    ]

    # =========================================================================
    # 9. BUDGET / POSITION SIZING
    # =========================================================================

    budget_status = (
        "NOT_IN_CURRENT_TRADE_GATE_CONTRACT"
    )

    budget_allocated = (
        "NOT_IN_CURRENT_TRADE_GATE_CONTRACT"
    )

    position_size = (
        "NOT_IN_CURRENT_TRADE_GATE_CONTRACT"
    )

    quantity = (
        "NOT_IN_CURRENT_TRADE_GATE_CONTRACT"
    )

    if budget_layer is not None:
        budget_status = (
            f"AVAILABLE_VIA={budget_layer}"
        )

    if sizing_layer is not None:
        position_size = (
            f"AVAILABLE_VIA={sizing_layer}"
        )

    # =========================================================================
    # 10. FINAL
    # =========================================================================

    final_status = (
        "READY"
        if authoritative_status
        == "TRADE_READY"
        else "BLOCKED"
    )

    blocker = (
        "; ".join(reasons)
        if reasons
        else "NONE"
    )

    if final_status == "READY":

        next_step = (
            "ORDER INTENT RELEASE PREFLIGHT"
        )

    else:

        next_step = (
            "REPAIR ONLY THE ACTUAL BLOCKER"
        )

    print()
    print("=" * 100)

    print(
        f"STATUS={'NEAR TRADE GATE VALIDATION = CLOSED / VERIFIED / PASS' if final_status == 'READY' else 'NEAR TRADE GATE VALIDATION = BLOCKED'}"
    )

    print(
        f"ASSET={TARGET_ASSET}"
    )

    print(
        f"OPPORTUNITY={opportunity_status}"
    )

    print(
        f"DECISION={decision_state}"
    )

    print(
        f"DIRECTION={direction}"
    )

    print(
        f"SCORE={score}"
    )

    print(
        f"CONFIDENCE={confidence}"
    )

    print(
        f"ACTIONABLE={decision_state == 'ACTIONABLE'}"
    )

    print(
        f"RISK_STATUS={risk_state}"
    )

    print(
        f"RISK_DECISION={risk_decision}"
    )

    print(
        f"STOP_DISTANCE={stop_distance}"
    )

    print(
        f"RISK_REWARD={risk_reward}"
    )

    print(
        f"BUDGET_STATUS={budget_status}"
    )

    print(
        f"BUDGET_ALLOCATED={budget_allocated}"
    )

    print(
        f"POSITION_SIZE={position_size}"
    )

    print(
        f"QUANTITY={quantity}"
    )

    print(
        f"TRADE_GATE={runtime_gate_status}"
    )

    print(
        "PASSED_PREDICATES="
        +
        (
            ",".join(passed)
            if passed
            else "NONE"
        )
    )

    print(
        "FAILED_PREDICATE="
        +
        (
            ",".join(failed)
            if failed
            else "NONE"
        )
    )

    print(
        f"BLOCK_REASON={blocker}"
    )

    print(
        "CONTRACT="
        "CURRENT_TRADE_GATE_ENGINE_AUTHORITATIVE"
    )

    print(
        "PROVENANCE=CURRENT_PRODUCTION_RUNTIME"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print(
        "FILES_MODIFIED=0"
    )

    print(
        f"BLOCKER={blocker}"
    )

    print(
        f"NEXT={next_step}"
    )

    print("=" * 100)


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print(
            "STATUS=VALIDATION_RUNTIME_ERROR"
        )

        print(
            f"ASSET={TARGET_ASSET}"
        )

        print(
            f"ERROR_TYPE={type(exc).__name__}"
        )

        print(
            f"ERROR={exc}"
        )

        print(
            "DB_WRITES=0"
        )

        print(
            "ORDER_INTENTS=0"
        )

        print(
            "EXECUTION=OFF"
        )

        print(
            "FILES_MODIFIED=0"
        )

        raise