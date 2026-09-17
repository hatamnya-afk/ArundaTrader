
# =============================================================================
# ARUNDA NEAR TRADE GATE VALIDATION v0.4
# CURRENT-RUN DIRECT VALIDATION
# =============================================================================
#
# PURPOSE
# -------
# Validate ONLY NEAR through:
#
#   CURRENT OPPORTUNITY
#          â†“
#       DECISION
#          â†“
#         RISK
#          â†“
#     RISK BUDGET
#          â†“
#    POSITION SIZING
#          â†“
#      TRADE GATE
#
# HARD SAFETY
# -----------
# READ ONLY
# DB_WRITES = 0
# EXECUTION = OFF
# ORDER_INTENTS = 0
# NO ENGINE MODIFICATION
# NO THRESHOLD MODIFICATION
# NO SYNTHETIC DATA
# NO FALLBACK DATA
#
# IMPORTANT
# ---------
# This validator does NOT call arunda_pipeline.main().
# It directly consumes the current runtime APIs.
#
# =============================================================================

from __future__ import annotations

import math
from typing import Any, Mapping

import opportunity_engine
import signal_validator
import score_producer
import signal_scorer
import decision_engine
import risk_engine
import risk_budget_engine
import position_sizing_engine
import trade_gate_engine


# =============================================================================
# CONSTANTS
# =============================================================================

TARGET_ASSET = "NEAR"

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

EXPECTED_DIRECTION = "LONG"
EXPECTED_STATUS = "ELIGIBLE"

MIN_SCORE = 10.0
MIN_CONFIDENCE = 0.55
MIN_MARKET_DATA_POINTS = 4

EXPECTED_SCORE_PREVIOUS = 37.2398
EXPECTED_CONFIDENCE_PREVIOUS = 0.6164


# =============================================================================
# HELPERS
# =============================================================================

def is_number(value: Any) -> bool:

    if isinstance(value, bool):
        return False

    try:
        value = float(value)
    except (TypeError, ValueError):
        return False

    return math.isfinite(value)


def normalize_asset(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().upper()


def asset_of(row: Any) -> str:

    if not isinstance(row, Mapping):
        return ""

    for key in (
        "asset",
        "symbol",
        "market",
    ):

        value = row.get(key)

        if value is not None:

            asset = normalize_asset(value)

            if asset:
                return asset

    return ""


def rows_from_mapping_or_list(value: Any) -> dict:

    result = {}

    if isinstance(value, Mapping):

        for key, row in value.items():

            if not isinstance(row, Mapping):
                continue

            asset = normalize_asset(key)

            if not asset:
                asset = asset_of(row)

            if asset in EXPECTED_ASSETS:
                result[asset] = dict(row)

        return result

    if isinstance(value, (list, tuple)):

        for row in value:

            if not isinstance(row, Mapping):
                continue

            asset = asset_of(row)

            if asset in EXPECTED_ASSETS:
                result[asset] = dict(row)

        return result

    return result



def extract_rows(snapshot: Any, preferred_keys=()) -> dict:

    """
    Extract asset records from a runtime snapshot.

    This deliberately does NOT depend on one historical
    wrapper shape. It recognizes actual asset records by
    their semantic fields.

    No transformation of engine output is performed.
    """

    if snapshot is None:
        return {}

    visited = set()

    def looks_like_asset_record(value):

        if not isinstance(value, Mapping):
            return False

        asset = ""

        for key in (
            "asset",
            "symbol",
            "market",
        ):

            if key in value and value[key] is not None:

                candidate = normalize_asset(
                    value[key]
                )

                if candidate in EXPECTED_ASSETS:
                    asset = candidate
                    break

        if not asset:
            return False

        # Opportunity / decision / risk records have
        # at least one semantic state field.
        semantic_fields = (
            "status",
            "opportunity_status",
            "state",
            "decision_state",
            "decision",
            "risk_state",
            "risk_status",
            "direction",
            "score",
            "confidence",
            "position_size",
            "budget_state",
        )

        return any(
            field in value
            for field in semantic_fields
        )

    def collect(value, result):

        if isinstance(value, Mapping):

            object_id = id(value)

            if object_id in visited:
                return

            visited.add(object_id)

            if looks_like_asset_record(value):

                asset = asset_of(value)

                if asset in EXPECTED_ASSETS:

                    # First occurrence wins.
                    if asset not in result:
                        result[asset] = dict(value)

                    return

            # Prefer known runtime containers first.
            ordered_keys = [
                "opportunities",
                "opportunity",
                "candidates",
                "results",
                "decisions",
                "decision",
                "risk",
                "risks",
                "risk_snapshot",
                "budget",
                "budgets",
                "risk_budget",
                "risk_budgets",
                "position_sizing",
                "positions",
                "rows",
                "assets",
                "snapshot",
                "data",
                "payload",
                "output",
                "runtime",
            ]

            seen_keys = set()

            for key in ordered_keys:

                if key not in value:
                    continue

                seen_keys.add(key)

                collect(
                    value[key],
                    result,
                )

            # Then inspect any remaining containers.
            for key, nested in value.items():

                if key in seen_keys:
                    continue

                if isinstance(
                    nested,
                    (Mapping, list, tuple),
                ):

                    collect(
                        nested,
                        result,
                    )

            return

        if isinstance(value, (list, tuple)):

            object_id = id(value)

            if object_id in visited:
                return

            visited.add(object_id)

            for item in value:

                if isinstance(
                    item,
                    (Mapping, list, tuple),
                ):

                    collect(
                        item,
                        result,
                    )

    result = {}

    collect(
        snapshot,
        result,
    )

    return result

def find_target(rows: Mapping) -> dict:

    row = rows.get(TARGET_ASSET)

    if row is None:

        for key, candidate in rows.items():

            if normalize_asset(key) == TARGET_ASSET:
                row = candidate
                break

    if not isinstance(row, Mapping):

        raise RuntimeError(
            f"{TARGET_ASSET}: runtime record not found"
        )

    return dict(row)


def get_direction(row: Mapping) -> str:

    for key in (
        "direction",
        "side",
        "trade_direction",
    ):

        if key in row and row[key] is not None:

            return str(row[key]).strip().upper()

    return ""


def get_score(row: Mapping):

    for key in (
        "score",
        "opportunity_score",
        "edge",
        "fused_score",
    ):

        if key in row and row[key] is not None:

            try:
                return float(row[key])
            except (TypeError, ValueError):
                pass

    return None


def get_confidence(row: Mapping):

    for key in (
        "confidence",
        "opportunity_confidence",
    ):

        if key in row and row[key] is not None:

            try:
                return float(row[key])
            except (TypeError, ValueError):
                pass

    return None


def get_status(row: Mapping) -> str:

    for key in (
        "status",
        "opportunity_status",
    ):

        if key in row and row[key] is not None:

            return str(row[key]).strip().upper()

    return ""


def get_points(row: Mapping):

    for key in (
        "market_data_points",
        "points",
        "context_points",
    ):

        if key in row and row[key] is not None:

            try:
                return int(row[key])
            except (TypeError, ValueError):
                pass

    return None


def get_snapshot_age(row: Mapping):

    value = row.get("snapshot_age")

    if value is None:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# =============================================================================
# DECISION EXTRACTION
# =============================================================================

def extract_decision_snapshot() -> dict:

    validated_signals = (
        signal_validator.load_validated_signals()
    )

    if not isinstance(validated_signals, dict):

        raise RuntimeError(
            "Signal Validator returned invalid snapshot"
        )

    if len(validated_signals) != 15:

        raise RuntimeError(
            f"Signal Validator coverage failure: "
            f"{len(validated_signals)}/15"
        )

    for asset in EXPECTED_ASSETS:

        row = validated_signals.get(asset)

        if not isinstance(row, Mapping):

            # Defensive case-insensitive lookup.
            row = None

            for key, candidate in validated_signals.items():

                if normalize_asset(key) == asset:
                    row = candidate
                    break

        if not isinstance(row, Mapping):

            raise RuntimeError(
                f"Validated signal missing: {asset}"
            )

        if row.get("valid") is not True:

            raise RuntimeError(
                f"Validated signal invalid: {asset}"
            )

    scores = score_producer.run(
        validated_signals
    )

    if not isinstance(scores, dict):

        raise RuntimeError(
            "Score Producer returned invalid snapshot"
        )

    aligned_scores = signal_scorer.run(
        validated_signals,
        scores,
    )

    if not isinstance(aligned_scores, dict):

        raise RuntimeError(
            "Signal Scorer returned invalid snapshot"
        )

    decision_snapshot = decision_engine.run(
        validated_signals,
        aligned_scores,
    )

    if not isinstance(decision_snapshot, dict):

        raise RuntimeError(
            "Decision Engine returned invalid snapshot"
        )

    return decision_snapshot


# =============================================================================
# RISK
# =============================================================================

def extract_risk_snapshot(
    decision_snapshot: dict,
) -> dict:

    risk_snapshot = risk_engine.run(
        decision_snapshot
    )

    if not isinstance(risk_snapshot, dict):

        raise RuntimeError(
            "Risk Engine returned invalid snapshot"
        )

    return risk_snapshot


# =============================================================================
# RISK BUDGET
# =============================================================================

def build_risk_budget(
    risk_snapshot: dict,
):

    capital_config = (
        risk_budget_engine.load_capital_config()
    )

    if capital_config is None:

        raise RuntimeError(
            "Risk Budget capital configuration unavailable"
        )

    budget_snapshot = (
        risk_budget_engine.build_budget_snapshot(
            risk_snapshot,
            capital_config,
        )
    )

    if not isinstance(budget_snapshot, dict):

        raise RuntimeError(
            "Risk Budget returned invalid snapshot"
        )

    risk_budget_engine.validate_budget(
        budget_snapshot
    )

    return budget_snapshot


# =============================================================================
# BUDGET ROW EXTRACTION
# =============================================================================

def extract_asset_row(
    snapshot: Any,
    asset: str,
) -> dict:

    rows = extract_rows(
        snapshot,
        (
            "budget",
            "budgets",
            "risk_budget",
            "risk_budgets",
            "position_sizing",
            "positions",
            "rows",
        ),
    )

    row = rows.get(asset)

    if isinstance(row, Mapping):
        return dict(row)

    return {}


# =============================================================================
# POSITION SIZING
# =============================================================================

def try_position_sizing(
    opportunity: Mapping,
    risk_budget_snapshot: Mapping,
):

    budget_row = extract_asset_row(
        risk_budget_snapshot,
        TARGET_ASSET,
    )

    if not budget_row:

        return {
            "available": False,
            "reason": "NEAR risk-budget row unavailable",
        }

    budget_state = str(
        budget_row.get("budget_state", "")
    ).strip().upper()

    if budget_state != "ALLOCATED":

        return {
            "available": False,
            "budget_state": budget_state,
            "reason": (
                "position sizing not invoked because "
                "risk budget is not ALLOCATED"
            ),
        }

    entry_price = opportunity.get("price")

    stop_distance = opportunity.get(
        "stop_distance"
    )

    if stop_distance is None:

        stop_distance = opportunity.get(
            "atr_stop_distance"
        )

    if not is_number(entry_price):

        return {
            "available": False,
            "budget_state": budget_state,
            "reason": "entry price unavailable",
        }

    if not is_number(stop_distance):

        return {
            "available": False,
            "budget_state": budget_state,
            "reason": "stop distance unavailable",
        }

    risk_budget = budget_row.get(
        "risk_budget"
    )

    snapshot_id = (
        opportunity.get("snapshot_id")
        or opportunity.get("runtime_snapshot_id")
        or ""
    )

    try:

        record = (
            position_sizing_engine
            .build_runtime_position_record(
                asset=TARGET_ASSET,
                direction=EXPECTED_DIRECTION,
                risk_budget=risk_budget,
                entry_price=float(entry_price),
                stop_distance=float(stop_distance),
                snapshot_id=snapshot_id,
            )
        )

    except TypeError:

        # Defensive compatibility for positional signature.
        record = (
            position_sizing_engine
            .build_runtime_position_record(
                TARGET_ASSET,
                EXPECTED_DIRECTION,
                risk_budget,
                float(entry_price),
                float(stop_distance),
                snapshot_id,
            )
        )

    if not isinstance(record, Mapping):

        raise RuntimeError(
            "Position Sizing returned invalid record"
        )

    return {
        "available": True,
        "budget_state": budget_state,
        "record": dict(record),
    }


# =============================================================================
# TRADE GATE
# =============================================================================

def validate_trade_gate(
    opportunity: Mapping,
    decision: Mapping,
    risk: Mapping,
):

    gate_status, reasons = (
        trade_gate_engine.evaluate(
            opportunity,
            decision,
            risk,
        )
    )

    observability = (
        trade_gate_engine.build_gate_observability(
            opportunity,
            decision,
            risk,
        )
    )

    if not isinstance(observability, list):

        raise RuntimeError(
            "Trade Gate observability is invalid"
        )

    return gate_status, reasons, observability


# =============================================================================
# MAIN
# =============================================================================

def run():

    print("=" * 100)
    print("ARUNDA NEAR TRADE GATE VALIDATION v0.4")
    print("=" * 100)

    print("MODE=READ_ONLY")
    print(f"TARGET={TARGET_ASSET}")
    print(f"EXPECTED_DIRECTION={EXPECTED_DIRECTION}")
    print(f"EXPECTED_STATUS={EXPECTED_STATUS}")
    print(
        f"PREVIOUS_SCORE={EXPECTED_SCORE_PREVIOUS}"
    )
    print(
        f"PREVIOUS_CONFIDENCE={EXPECTED_CONFIDENCE_PREVIOUS}"
    )
    print("DB_WRITES=0")
    print("EXECUTION=OFF")
    print("ORDER_INTENTS=0")
    print()

    # =========================================================================
    # 1. CURRENT OPPORTUNITY
    # =========================================================================

    print("=" * 100)
    print("[1/6] CURRENT OPPORTUNITY")
    print("=" * 100)

    opportunity_snapshot = (
        opportunity_engine.run()
    )

    if not isinstance(
        opportunity_snapshot,
        dict,
    ):

        raise RuntimeError(
            "Opportunity Engine returned invalid snapshot"
        )

    opportunity_rows = extract_rows(
        opportunity_snapshot,
        (
            "opportunities",
            "results",
            "candidates",
            "rows",
        ),
    )

    if len(opportunity_rows) != 15:

        raise RuntimeError(
            "Opportunity coverage failure: "
            f"{len(opportunity_rows)}/15"
        )

    opportunity = find_target(
        opportunity_rows
    )

    print(
        f"NEAR | STATUS={get_status(opportunity)} "
        f"| DIRECTION={get_direction(opportunity)} "
        f"| SCORE={get_score(opportunity)} "
        f"| CONF={get_confidence(opportunity)} "
        f"| POINTS={get_points(opportunity)}"
    )

    # =========================================================================
    # 2. DECISION
    # =========================================================================

    print()
    print("=" * 100)
    print("[2/6] DECISION")
    print("=" * 100)

    decision_snapshot = (
        extract_decision_snapshot()
    )

    decision_rows = extract_rows(
        decision_snapshot,
        (
            "decisions",
            "rows",
            "snapshot",
        ),
    )

    if len(decision_rows) != 15:

        raise RuntimeError(
            "Decision coverage failure: "
            f"{len(decision_rows)}/15"
        )

    decision = find_target(
        decision_rows
    )

    print(
        f"NEAR | STATE="
        f"{decision.get('state', decision.get('decision_state', decision.get('decision')))} "
        f"| DIRECTION={get_direction(decision)} "
        f"| SCORE={get_score(decision)}"
    )

    # =========================================================================
    # 3. RISK
    # =========================================================================

    print()
    print("=" * 100)
    print("[3/6] RISK")
    print("=" * 100)

    risk_snapshot = extract_risk_snapshot(
        decision_snapshot
    )

    risk_rows = extract_rows(
        risk_snapshot,
        (
            "risk",
            "risks",
            "rows",
            "snapshot",
        ),
    )

    if len(risk_rows) != 15:

        raise RuntimeError(
            "Risk coverage failure: "
            f"{len(risk_rows)}/15"
        )

    risk = find_target(
        risk_rows
    )

    print(
        f"NEAR | STATUS="
        f"{risk.get('status', risk.get('risk_state'))} "
        f"| DECISION="
        f"{risk.get('risk_decision', risk.get('decision'))}"
    )

    # =========================================================================
    # 4. RISK BUDGET
    # =========================================================================

    print()
    print("=" * 100)
    print("[4/6] RISK BUDGET")
    print("=" * 100)

    risk_budget_snapshot = build_risk_budget(
        risk_snapshot
    )

    budget = extract_asset_row(
        risk_budget_snapshot,
        TARGET_ASSET,
    )

    if budget:

        print(
            f"NEAR | BUDGET_STATE="
            f"{budget.get('budget_state')} "
            f"| RISK_BUDGET="
            f"{budget.get('risk_budget')}"
        )

    else:

        print(
            "NEAR | BUDGET_STATE=NO_ROW"
        )

    # =========================================================================
    # 5. POSITION SIZING
    # =========================================================================

    print()
    print("=" * 100)
    print("[5/6] POSITION SIZING")
    print("=" * 100)

    position_result = try_position_sizing(
        opportunity,
        risk_budget_snapshot,
    )

    print(
        f"NEAR | AVAILABLE="
        f"{position_result.get('available')}"
    )

    if position_result.get(
        "budget_state"
    ) is not None:

        print(
            f"NEAR | BUDGET_STATE="
            f"{position_result.get('budget_state')}"
        )

    if position_result.get("record"):

        record = position_result["record"]

        print(
            f"NEAR | POSITION_SIZE="
            f"{record.get('position_size')}"
        )

    else:

        print(
            f"NEAR | POSITION_SIZING_REASON="
            f"{position_result.get('reason')}"
        )

    # =========================================================================
    # 6. TRADE GATE
    # =========================================================================

    print()
    print("=" * 100)
    print("[6/6] TRADE GATE")
    print("=" * 100)

    gate_status, reasons, predicates = (
        validate_trade_gate(
            opportunity,
            decision,
            risk,
        )
    )

    print(
        f"TRADE_GATE_STATUS={gate_status}"
    )

    print(
        f"OPPORTUNITY_STATUS="
        f"{get_status(opportunity)}"
    )

    print(
        f"OPPORTUNITY_DIRECTION="
        f"{get_direction(opportunity)}"
    )

    print(
        f"OPPORTUNITY_SCORE="
        f"{get_score(opportunity)}"
    )

    print(
        f"OPPORTUNITY_CONFIDENCE="
        f"{get_confidence(opportunity)}"
    )

    print(
        f"MARKET_DATA_POINTS="
        f"{get_points(opportunity)}"
    )

    print(
        f"DECISION_STATE="
        f"{decision.get('state', decision.get('decision_state', decision.get('decision')))}"
    )

    print(
        f"RISK_STATUS="
        f"{risk.get('status', risk.get('risk_state'))}"
    )

    print()
    print("-" * 100)
    print("TRADE GATE PREDICATES")
    print("-" * 100)

    for item in predicates:

        print(
            "PREDICATE | "
            f"{item.get('name')} | "
            f"ACTUAL={item.get('actual')} | "
            f"EXPECTED={item.get('expected')} | "
            f"PASS={item.get('pass')} | "
            f"OWNER={item.get('owner_file')}"
            f"::{item.get('owner_function')}"
        )

    print("-" * 100)

    failed = [
        item
        for item in predicates
        if not item.get("pass")
    ]

    print(
        f"ALL_PREDICATES_PASS={not failed}"
    )

    if reasons:

        print(
            "TRADE_GATE_REASONS="
            + " | ".join(
                str(reason)
                for reason in reasons
            )
        )

    else:

        print(
            "TRADE_GATE_REASONS=NONE"
        )

    # =========================================================================
    # CURRENT-RUN TRUTH
    # =========================================================================

    current_status = get_status(
        opportunity
    )

    current_direction = get_direction(
        opportunity
    )

    current_score = get_score(
        opportunity
    )

    current_confidence = get_confidence(
        opportunity
    )

    print()
    print("=" * 100)
    print("CURRENT-RUN TRUTH")
    print("=" * 100)

    print(
        f"NEAR_STATUS={current_status}"
    )

    print(
        f"NEAR_DIRECTION={current_direction}"
    )

    print(
        f"NEAR_SCORE={current_score}"
    )

    print(
        f"NEAR_CONFIDENCE={current_confidence}"
    )

    # =========================================================================
    # FINAL DECISION
    # =========================================================================

    print()
    print("=" * 100)

    if (
        gate_status == "TRADE_READY"
        and not failed
    ):

        print(
            "TRADE_GATE=READY"
        )

        print(
            "NEAR TRADE GATE VALIDATION = "
            "CLOSED / VERIFIED / PASS"
        )

        print(
            "NEXT_STAGE=ORDER_INTENT_RELEASE_PREFLIGHT"
        )

    else:

        print(
            "TRADE_GATE=NOT_READY"
        )

        print(
            "NEAR TRADE GATE VALIDATION = BLOCKED"
        )

        if failed:

            first = failed[0]

            print(
                "FIRST_REAL_GATE_FAILURE="
                f"{first.get('name')} | "
                f"ACTUAL={first.get('actual')} | "
                f"EXPECTED={first.get('expected')} | "
                f"OWNER={first.get('owner_file')}"
                f"::{first.get('owner_function')}"
            )

        elif reasons:

            print(
                "FIRST_REAL_GATE_FAILURE="
                f"{reasons[0]}"
            )

        else:

            print(
                "FIRST_REAL_GATE_FAILURE=UNKNOWN"
            )

    print("=" * 100)

    print()
    print("DB_WRITES=0")
    print("EXECUTION=OFF")
    print("ORDER_INTENTS=0")
    print("STATUS=VALIDATION_COMPLETE")


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":

    try:

        run()

    except Exception as exc:

        print()
        print("=" * 100)
        print("ARUNDA NEAR TRADE GATE VALIDATION ERROR")
        print("=" * 100)
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
            "EXECUTION=OFF"
        )
        print(
            "ORDER_INTENTS=0"
        )
        print(
            "STATUS=VALIDATION_RUNTIME_ERROR"
        )
        print("=" * 100)

        raise
