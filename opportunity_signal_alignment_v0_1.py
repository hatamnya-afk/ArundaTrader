# =============================================================================
# ARUNDA SIGNAL <-> OPPORTUNITY ALIGNMENT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Canonical semantic boundary between:
#
#     MARKET OPPORTUNITY DISCOVERY
#                 +
#          VALIDATED SIGNAL
#                 ↓
#        ALIGNED OPPORTUNITY
#
# IMPORTANT
# ---------
# Opportunity discovery remains market-derived.
# Signal remains the authoritative semantic direction/state.
#
# This layer DOES NOT:
#     - change opportunity score
#     - change opportunity confidence
#     - change thresholds
#     - manufacture direction
#     - override conflicts
#     - write DB
#     - execute trades
#
# SAFETY
# ------
# READ ONLY
# MEMORY ONLY
# DB_WRITES = 0
# EXECUTION = OFF
# ORDER_INTENTS = 0
# SYNTHETIC = FALSE
# INTERPOLATION = FALSE
# FILL = FALSE
# BACKFILL = FALSE
# PADDING = FALSE
# =============================================================================

from __future__ import annotations

from typing import Any, Mapping


ENGINE_VERSION = "OPPORTUNITY_SIGNAL_ALIGNMENT_v0.1"

DB_WRITES = 0
EXECUTION = False
ORDER_INTENTS = 0

EXPECTED_SIGNAL_STATES = {
    "ACTIVE",
    "NEUTRAL",
}

EXPECTED_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}

EXPECTED_OPPORTUNITY_STATUSES = {
    "ELIGIBLE",
    "NO_TRADE",
    "WAITING_HISTORY",
}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_signal(
    asset: str,
    signal: Mapping[str, Any],
) -> None:

    if not isinstance(signal, Mapping):
        raise RuntimeError(
            f"{asset}: invalid signal object"
        )

    if signal.get("asset") != asset:
        raise RuntimeError(
            f"{asset}: signal asset mismatch"
        )

    if signal.get("valid") is not True:
        raise RuntimeError(
            f"{asset}: signal is not validated"
        )

    state = signal.get("signal_state")
    direction = signal.get("direction")

    if state not in EXPECTED_SIGNAL_STATES:
        raise RuntimeError(
            f"{asset}: invalid signal state {state!r}"
        )

    if direction not in EXPECTED_DIRECTIONS:
        raise RuntimeError(
            f"{asset}: invalid signal direction {direction!r}"
        )

    if state == "ACTIVE":
        if direction not in {"LONG", "SHORT"}:
            raise RuntimeError(
                f"{asset}: ACTIVE signal requires LONG/SHORT"
            )

    if state == "NEUTRAL":
        if direction != "NONE":
            raise RuntimeError(
                f"{asset}: NEUTRAL signal requires NONE"
            )


def validate_opportunity(
    asset: str,
    opportunity: Mapping[str, Any],
) -> None:

    if not isinstance(opportunity, Mapping):
        raise RuntimeError(
            f"{asset}: invalid opportunity object"
        )

    if opportunity.get("asset") != asset:
        raise RuntimeError(
            f"{asset}: opportunity asset mismatch"
        )

    status = opportunity.get("status")

    if status not in EXPECTED_OPPORTUNITY_STATUSES:
        raise RuntimeError(
            f"{asset}: invalid opportunity status {status!r}"
        )

    direction = opportunity.get("direction")

    if direction not in EXPECTED_DIRECTIONS:
        raise RuntimeError(
            f"{asset}: invalid opportunity direction {direction!r}"
        )


# =============================================================================
# CORE BOUNDARY
# =============================================================================

def align_one(
    asset: str,
    opportunity: Mapping[str, Any],
    signal: Mapping[str, Any],
) -> dict[str, Any]:

    validate_opportunity(
        asset,
        opportunity,
    )

    validate_signal(
        asset,
        signal,
    )

    result = dict(opportunity)

    signal_state = signal["signal_state"]
    signal_direction = signal["direction"]
    opportunity_direction = opportunity["direction"]

    result["alignment_engine"] = ENGINE_VERSION
    result["signal_state"] = signal_state
    result["signal_direction"] = signal_direction
    result["opportunity_direction"] = opportunity_direction
    result["alignment_status"] = "BLOCKED"
    result["alignment_reason"] = None

    # -------------------------------------------------------------------------
    # WAITING HISTORY
    # -------------------------------------------------------------------------

    if opportunity["status"] == "WAITING_HISTORY":

        result["alignment_status"] = "BLOCKED"
        result["alignment_reason"] = (
            "WAITING_HISTORY"
        )

        return result

    # -------------------------------------------------------------------------
    # NEUTRAL SIGNAL
    #
    # A neutral signal is authoritative.
    # A market-derived directional opportunity cannot become
    # trade-eligible without an active signal.
    # -------------------------------------------------------------------------

    if signal_state == "NEUTRAL":

        result["status"] = "NO_TRADE"
        result["direction"] = "NONE"

        result["alignment_status"] = "BLOCKED"
        result["alignment_reason"] = (
            "NEUTRAL_SIGNAL_WITH_DIRECTIONAL_OPPORTUNITY"
            if opportunity_direction in {"LONG", "SHORT"}
            else "NEUTRAL_SIGNAL"
        )

        return result

    # -------------------------------------------------------------------------
    # ACTIVE SIGNAL
    # -------------------------------------------------------------------------

    if signal_state == "ACTIVE":

        # Impossible state after signal validation.
        if signal_direction not in {"LONG", "SHORT"}:
            raise RuntimeError(
                f"{asset}: ACTIVE signal has invalid direction"
            )

        # No directional market opportunity.
        if opportunity_direction not in {"LONG", "SHORT"}:

            result["status"] = "NO_TRADE"
            result["direction"] = "NONE"

            result["alignment_status"] = "BLOCKED"
            result["alignment_reason"] = (
                "ACTIVE_SIGNAL_WITH_NON_DIRECTIONAL_OPPORTUNITY"
            )

            return result

        # ---------------------------------------------------------------------
        # PERFECT DIRECTIONAL AGREEMENT
        # ---------------------------------------------------------------------

        if opportunity_direction == signal_direction:

            result["signal_state"] = "ACTIVE"
            result["direction"] = signal_direction

            result["alignment_status"] = "ALIGNED"

            if opportunity["status"] == "ELIGIBLE":

                result["status"] = "ELIGIBLE"
                result["alignment_reason"] = (
                    "ACTIVE_SIGNAL_AND_OPPORTUNITY_DIRECTION_ALIGNED"
                )

            else:

                # Preserve Opportunity's original threshold decision.
                result["status"] = opportunity["status"]
                result["alignment_reason"] = (
                    "ACTIVE_SIGNAL_AND_OPPORTUNITY_DIRECTION_ALIGNED"
                    "_BUT_OPPORTUNITY_NOT_ELIGIBLE"
                )

            return result

        # ---------------------------------------------------------------------
        # HARD DIRECTION CONFLICT
        #
        # NEVER override either side.
        # ---------------------------------------------------------------------

        result["status"] = "NO_TRADE"
        result["direction"] = "NONE"

        result["alignment_status"] = "BLOCKED"

        result["alignment_reason"] = (
            "SIGNAL_OPPORTUNITY_DIRECTION_CONFLICT"
        )

        return result

    raise RuntimeError(
        f"{asset}: unreachable alignment state"
    )


# =============================================================================
# SNAPSHOT ALIGNMENT
# =============================================================================

def align_snapshot(
    opportunities: Mapping[str, Mapping[str, Any]],
    validated_signals: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:

    if not isinstance(opportunities, Mapping):
        raise RuntimeError(
            "Opportunities must be a mapping"
        )

    if not isinstance(validated_signals, Mapping):
        raise RuntimeError(
            "Validated signals must be a mapping"
        )

    opportunity_assets = set(
        opportunities.keys()
    )

    signal_assets = set(
        validated_signals.keys()
    )

    missing_signal = (
        opportunity_assets - signal_assets
    )

    if missing_signal:
        raise RuntimeError(
            "Missing validated signals: "
            + repr(sorted(missing_signal))
        )

    aligned = {}

    for asset in opportunity_assets:

        aligned[asset] = align_one(
            asset,
            opportunities[asset],
            validated_signals[asset],
        )

    return aligned


# =============================================================================
# SNAPSHOT VALIDATION
# =============================================================================

def validate_aligned_snapshot(
    aligned: Mapping[str, Mapping[str, Any]],
) -> None:

    if not isinstance(aligned, Mapping):
        raise RuntimeError(
            "Aligned snapshot must be a mapping"
        )

    for asset, item in aligned.items():

        if not isinstance(item, Mapping):
            raise RuntimeError(
                f"{asset}: invalid aligned record"
            )

        if item.get("asset") != asset:
            raise RuntimeError(
                f"{asset}: aligned asset mismatch"
            )

        if item.get("alignment_status") not in {
            "ALIGNED",
            "BLOCKED",
        }:
            raise RuntimeError(
                f"{asset}: invalid alignment status"
            )

        if item.get("signal_state") not in {
            "ACTIVE",
            "NEUTRAL",
        }:
            raise RuntimeError(
                f"{asset}: invalid aligned signal state"
            )

        if item.get("signal_direction") not in {
            "LONG",
            "SHORT",
            "NONE",
        }:
            raise RuntimeError(
                f"{asset}: invalid aligned signal direction"
            )

        if item.get("direction") not in {
            "LONG",
            "SHORT",
            "NONE",
        }:
            raise RuntimeError(
                f"{asset}: invalid final direction"
            )

        # ---------------------------------------------------------------------
        # HARD SEMANTIC INVARIANTS
        # ---------------------------------------------------------------------

        if item["signal_state"] == "NEUTRAL":

            if item["signal_direction"] != "NONE":
                raise RuntimeError(
                    f"{asset}: neutral signal semantic violation"
                )

            if item["status"] == "ELIGIBLE":
                raise RuntimeError(
                    f"{asset}: neutral signal cannot be ELIGIBLE"
                )

            if item["direction"] != "NONE":
                raise RuntimeError(
                    f"{asset}: neutral signal cannot expose direction"
                )

        if item["alignment_status"] == "ALIGNED":

            if item["signal_state"] != "ACTIVE":
                raise RuntimeError(
                    f"{asset}: only ACTIVE signals can align"
                )

            if item["signal_direction"] != item["direction"]:
                raise RuntimeError(
                    f"{asset}: aligned direction mismatch"
                )

        if item["status"] == "ELIGIBLE":

            if item["alignment_status"] != "ALIGNED":
                raise RuntimeError(
                    f"{asset}: ELIGIBLE requires ALIGNED boundary"
                )

            if item["signal_state"] != "ACTIVE":
                raise RuntimeError(
                    f"{asset}: ELIGIBLE requires ACTIVE signal"
                )

            if item["direction"] not in {
                "LONG",
                "SHORT",
            }:
                raise RuntimeError(
                    f"{asset}: ELIGIBLE requires direction"
                )


# =============================================================================
# STATISTICS
# =============================================================================

def calculate_statistics(
    aligned: Mapping[str, Mapping[str, Any]],
) -> dict[str, int]:

    return {
        "assets": len(aligned),
        "aligned": sum(
            1
            for item in aligned.values()
            if item["alignment_status"] == "ALIGNED"
        ),
        "blocked": sum(
            1
            for item in aligned.values()
            if item["alignment_status"] == "BLOCKED"
        ),
        "eligible": sum(
            1
            for item in aligned.values()
            if item["status"] == "ELIGIBLE"
        ),
        "no_trade": sum(
            1
            for item in aligned.values()
            if item["status"] == "NO_TRADE"
        ),
        "waiting_history": sum(
            1
            for item in aligned.values()
            if item["status"] == "WAITING_HISTORY"
        ),
        "long": sum(
            1
            for item in aligned.values()
            if item["direction"] == "LONG"
        ),
        "short": sum(
            1
            for item in aligned.values()
            if item["direction"] == "SHORT"
        ),
        "none": sum(
            1
            for item in aligned.values()
            if item["direction"] == "NONE"
        ),
    }


# =============================================================================
# RUNTIME TEST
# =============================================================================

def run() -> dict[str, Any]:

    import opportunity_engine
    import signal_validator

    print("=" * 90)
    print(
        "ARUNDA SIGNAL <-> OPPORTUNITY ALIGNMENT v0.1"
    )
    print("=" * 90)

    print(
        "Mode                  : READ ONLY / MEMORY ONLY"
    )

    print(
        "DB Writes             : 0"
    )

    print(
        "Execution             : OFF"
    )

    print(
        "Order Intents         : 0"
    )

    print(
        "Threshold Mutation    : NONE"
    )

    print(
        "Direction Override     : FORBIDDEN"
    )

    print()

    opportunities_wrapper = (
        opportunity_engine.run()
    )

    opportunities = (
        opportunities_wrapper["assets"]
    )

    validated_signals = (
        signal_validator.load_validated_signals()
    )

    aligned = align_snapshot(
        opportunities,
        validated_signals,
    )

    validate_aligned_snapshot(
        aligned
    )

    stats = calculate_statistics(
        aligned
    )

    print()
    print(
        "ASSET | SIGNAL       | OPPORTUNITY | FINAL     | ALIGNMENT | REASON"
    )

    print("-" * 110)

    for asset in sorted(aligned):

        item = aligned[asset]

        print(
            f"{asset:<5} | "
            f"{item['signal_state']:<7}/"
            f"{item['signal_direction']:<5} | "
            f"{item['opportunity_direction']:<10} | "
            f"{item['direction']:<9} | "
            f"{item['alignment_status']:<9} | "
            f"{item['alignment_reason']}"
        )

    print("-" * 110)

    print()
    print(
        f"ASSETS={stats['assets']}"
    )

    print(
        f"ALIGNED={stats['aligned']}"
    )

    print(
        f"BLOCKED={stats['blocked']}"
    )

    print(
        f"ELIGIBLE={stats['eligible']}"
    )

    print(
        f"NO_TRADE={stats['no_trade']}"
    )

    print(
        f"WAITING_HISTORY={stats['waiting_history']}"
    )

    print(
        f"LONG={stats['long']}"
    )

    print(
        f"SHORT={stats['short']}"
    )

    print(
        f"NONE={stats['none']}"
    )

    print()
    print(
        "NEUTRAL_DIRECTIONAL_OPPORTUNITIES=BLOCKED"
    )

    print(
        "DIRECTION_CONFLICTS=BLOCKED"
    )

    print(
        "SIGNAL_DIRECTION_OVERRIDE=FALSE"
    )

    print(
        "OPPORTUNITY_DIRECTION_OVERRIDE=FALSE"
    )

    print(
        "THRESHOLDS_CHANGED=FALSE"
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
        "STATUS=ALIGNMENT_BOUNDARY_PASS"
    )

    print("=" * 90)

    return {
        "engine_version": ENGINE_VERSION,
        "assets": aligned,
        "summary": stats,
        "db_writes": 0,
        "execution": False,
        "order_intents": 0,
    }


if __name__ == "__main__":
    run()
