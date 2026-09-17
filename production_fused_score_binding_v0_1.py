# =============================================================================
# ARUNDA PRODUCTION FUSED-SCORE BINDING v0.1
# =============================================================================
#
# PURPOSE
# -------
# Bind REAL FUSION_v0.6 fused_score into the existing REAL SCORE SNAPSHOT
# contract consumed by signal_scorer v0.4 and decision_engine v0.6.
#
# ARCHITECTURE
# ------------
#
# FUSION_v0.6
#      |
#      v
# fused_score [-100,+100]
#      |
#      v
# PRODUCTION FUSED-SCORE BINDING v0.1
#      |
#      v
# REAL SCORE SNAPSHOT [-1,+1]
#      |
#      v
# signal_scorer v0.4
#      |
#      v
# decision_engine v0.6
#
#
# RULES
# -----
# - REAL FUSION INPUT ONLY
# - NO SCORE GENERATION
# - NO SIGNAL GENERATION
# - NO DATABASE
# - NO SQL
# - NO DATABASE WRITES
# - NO SYNTHETIC DATA
# - NO INTERPOLATION
# - NO FILL
# - NO BACKFILL
# - NO PADDING
# - NO LEGACY market_technical
# - NO RISK
# - NO TRADE GATE
# - NO ORDER INTENT
# - NO EXECUTION
#
# IMPORTANT
# ---------
# This module does NOT reinterpret market/news/social information.
# It only binds the already-produced REAL fused_score to the existing
# [-1,+1] score representation required by signal_scorer v0.4.
#
# =============================================================================

from __future__ import annotations

import math
from typing import Any, Mapping


# =============================================================================
# CONSTANTS
# =============================================================================

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

EXPECTED_ASSET_COUNT = 15

FUSION_ENGINE_VERSION = "FUSION_v0.6"
BINDING_VERSION = "FUSED_SCORE_BINDING_v0.1"

FUSED_SCORE_MIN = -100.0
FUSED_SCORE_MAX = 100.0

SCORE_MIN = -1.0
SCORE_MAX = 1.0


VALID_SIGNAL_STATES = {
    "ACTIVE",
    "NEUTRAL",
}

VALID_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}


# =============================================================================
# NUMERIC VALIDATION
# =============================================================================

def safe_float(
    value: Any,
    field_name: str,
    asset: str,
) -> float:

    if isinstance(value, bool):

        raise RuntimeError(
            f"Boolean {field_name} for {asset}"
        )

    try:

        result = float(value)

    except (
        TypeError,
        ValueError,
    ) as error:

        raise RuntimeError(
            f"Invalid {field_name} for {asset}: "
            f"{value!r}"
        ) from error

    if not math.isfinite(result):

        raise RuntimeError(
            f"Non-finite {field_name} for {asset}: "
            f"{value!r}"
        )

    return result


# =============================================================================
# ASSET VALIDATION
# =============================================================================

def validate_asset_keys(
    data: Any,
    name: str,
) -> None:

    if not isinstance(data, Mapping):

        raise RuntimeError(
            f"{name} must be a mapping"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(data.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            f"{name} missing assets: "
            f"{sorted(missing)}"
        )

    if extra:

        raise RuntimeError(
            f"{name} contains unexpected assets: "
            f"{sorted(extra)}"
        )

    if len(actual) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            f"{name} asset count mismatch: "
            f"{len(actual)} != {EXPECTED_ASSET_COUNT}"
        )


# =============================================================================
# VALIDATED SIGNAL
# =============================================================================

def validate_signal(
    asset: str,
    signal: Any,
) -> Mapping[str, Any]:

    if not isinstance(signal, Mapping):

        raise RuntimeError(
            f"Invalid validated signal: {asset}"
        )

    if signal.get("asset") != asset:

        raise RuntimeError(
            f"Validated signal asset mismatch: {asset}"
        )

    if signal.get("valid") is not True:

        raise RuntimeError(
            f"Validated signal is not valid: {asset}"
        )

    state = signal.get("signal_state")
    direction = signal.get("direction")

    if state not in VALID_SIGNAL_STATES:

        raise RuntimeError(
            f"Invalid signal_state for {asset}: {state!r}"
        )

    if direction not in VALID_DIRECTIONS:

        raise RuntimeError(
            f"Invalid direction for {asset}: {direction!r}"
        )

    if state == "ACTIVE":

        if direction not in ("LONG", "SHORT"):

            raise RuntimeError(
                f"ACTIVE signal requires LONG/SHORT: {asset}"
            )

    if state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                f"NEUTRAL signal requires NONE: {asset}"
            )

    return signal


# =============================================================================
# FUSION RECORD VALIDATION
# =============================================================================

def validate_fusion_record(
    asset: str,
    fusion: Any,
) -> Mapping[str, Any]:

    if not isinstance(fusion, Mapping):

        raise RuntimeError(
            f"Invalid Fusion record: {asset}"
        )

    if fusion.get("asset") != asset:

        raise RuntimeError(
            f"Fusion asset mismatch: {asset}"
        )

    if "fused_score" not in fusion:

        raise RuntimeError(
            f"Fusion record missing fused_score: {asset}"
        )

    fused_score = safe_float(
        fusion["fused_score"],
        "fused_score",
        asset,
    )

    if (
        fused_score < FUSED_SCORE_MIN
        or fused_score > FUSED_SCORE_MAX
    ):

        raise RuntimeError(
            f"fused_score outside "
            f"[{FUSED_SCORE_MIN}, {FUSED_SCORE_MAX}] "
            f"for {asset}: {fused_score}"
        )

    if "direction" not in fusion:

        raise RuntimeError(
            f"Fusion record missing direction: {asset}"
        )

    direction = fusion["direction"]

    if direction not in (
        "LONG",
        "SHORT",
        "FLAT",
    ):

        raise RuntimeError(
            f"Invalid Fusion direction for "
            f"{asset}: {direction!r}"
        )

    return fusion


# =============================================================================
# FUSED SCORE → SCORE BINDING
# =============================================================================

def bind_one(
    asset: str,
    validated_signal: Mapping[str, Any],
    fusion_record: Mapping[str, Any],
) -> dict:

    signal = validate_signal(
        asset,
        validated_signal,
    )

    fusion = validate_fusion_record(
        asset,
        fusion_record,
    )

    signal_state = signal["signal_state"]
    signal_direction = signal["direction"]

    fused_score = safe_float(
        fusion["fused_score"],
        "fused_score",
        asset,
    )

    fusion_direction = fusion["direction"]

    # -------------------------------------------------------------------------
    # Directional cross-validation
    # -------------------------------------------------------------------------

    if signal_direction in ("LONG", "SHORT"):

        if fusion_direction == "FLAT":

            raise RuntimeError(
                f"Fusion/Signal direction mismatch for {asset}: "
                f"signal={signal_direction}, fusion=FLAT"
            )

        if fusion_direction != signal_direction:

            raise RuntimeError(
                f"Fusion/Signal direction mismatch for {asset}: "
                f"signal={signal_direction}, "
                f"fusion={fusion_direction}"
            )

    elif signal_direction == "NONE":

        if fusion_direction not in ("FLAT",):

            raise RuntimeError(
                f"NEUTRAL signal requires FLAT Fusion direction: "
                f"{asset}"
            )

    # -------------------------------------------------------------------------
    # Canonical representation binding
    #
    # Fusion:
    #     [-100,+100]
    #
    # Score:
    #     [-1,+1]
    #
    # This is representation conversion only.
    # -------------------------------------------------------------------------

    score = fused_score / 100.0

    # -------------------------------------------------------------------------
    # NONE direction has canonical zero score.
    # -------------------------------------------------------------------------

    if signal_direction == "NONE":

        score = 0.0

    # -------------------------------------------------------------------------
    # Final numeric boundary
    # -------------------------------------------------------------------------

    score = safe_float(
        score,
        "score",
        asset,
    )

    if score < SCORE_MIN or score > SCORE_MAX:

        raise RuntimeError(
            f"Bound score outside [-1,+1] for "
            f"{asset}: {score}"
        )

    return {
        "asset": asset,
        "signal_state": signal_state,
        "direction": signal_direction,
        "score": score,
    }


# =============================================================================
# BUILD COMPLETE SCORE SNAPSHOT
# =============================================================================

def build_score_snapshot(
    validated_signals: Mapping[str, Any],
    fusion_snapshot: Mapping[str, Any],
) -> dict:

    validate_asset_keys(
        validated_signals,
        "validated_signals",
    )

    validate_asset_keys(
        fusion_snapshot,
        "fusion_snapshot",
    )

    scores = {}

    for asset in EXPECTED_ASSETS:

        scores[asset] = bind_one(
            asset,
            validated_signals[asset],
            fusion_snapshot[asset],
        )

    return scores


# =============================================================================
# INTERNAL SCORE VALIDATION
# =============================================================================

def validate_score_snapshot(
    validated_signals: Mapping[str, Any],
    scores: Mapping[str, Any],
) -> bool:

    validate_asset_keys(
        validated_signals,
        "validated_signals",
    )

    validate_asset_keys(
        scores,
        "scores",
    )

    for asset in EXPECTED_ASSETS:

        signal = validated_signals[asset]
        score = scores[asset]

        validate_signal(
            asset,
            signal,
        )

        if not isinstance(score, Mapping):

            raise RuntimeError(
                f"Invalid score record: {asset}"
            )

        if score.get("asset") != asset:

            raise RuntimeError(
                f"Score asset mismatch: {asset}"
            )

        if score.get("signal_state") != signal["signal_state"]:

            raise RuntimeError(
                f"Score/signal state mismatch: {asset}"
            )

        if score.get("direction") != signal["direction"]:

            raise RuntimeError(
                f"Score/signal direction mismatch: {asset}"
            )

        value = safe_float(
            score.get("score"),
            "score",
            asset,
        )

        if value < SCORE_MIN or value > SCORE_MAX:

            raise RuntimeError(
                f"Score outside [-1,+1]: {asset}"
            )

        if score["direction"] == "NONE" and value != 0.0:

            raise RuntimeError(
                f"NONE direction requires score 0.0: {asset}"
            )

    return True


# =============================================================================
# REPORT
# =============================================================================

def print_result(
    scores: Mapping[str, Any],
) -> None:

    print()
    print("PRODUCTION SCORE SNAPSHOT")
    print("-" * 82)
    print(
        "Asset  | State   | Direction | Score"
    )
    print("-" * 82)

    for asset in EXPECTED_ASSETS:

        item = scores[asset]

        print(
            f"{asset:<6} | "
            f"{item['signal_state']:<7} | "
            f"{item['direction']:<9} | "
            f"{float(item['score']):+0.6f}"
        )

    print()


# =============================================================================
# CONTRACT REPORT
# =============================================================================

def print_contract(
    scores: Mapping[str, Any],
) -> None:

    active = 0
    neutral = 0

    for asset in EXPECTED_ASSETS:

        if scores[asset]["direction"] == "NONE":

            neutral += 1

        else:

            active += 1

    print("=" * 82)
    print("FUSED-SCORE BINDING CONTRACT")
    print("=" * 82)

    print(
        f"Binding Version : {BINDING_VERSION}"
    )

    print(
        f"Fusion Source   : {FUSION_ENGINE_VERSION}"
    )

    print(
        f"Expected Assets : {EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Bound Assets    : {len(scores)}"
    )

    print(
        f"Active          : {active}"
    )

    print(
        f"Neutral         : {neutral}"
    )

    print(
        "Conversion      : fused_score / 100.0"
    )

    print(
        "Score Range     : [-1,+1]"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database        : NOT TOUCHED"
    )

    print(
        "DB Writes       : 0"
    )

    print(
        "Synthetic       : FALSE"
    )

    print(
        "Interpolation   : FALSE"
    )

    print(
        "Fill            : FALSE"
    )

    print(
        "Backfill        : FALSE"
    )

    print(
        "Padding         : FALSE"
    )

    print(
        "Legacy          : FORBIDDEN"
    )

    print(
        "Risk            : OFF"
    )

    print(
        "Trade Gate      : OFF"
    )

    print(
        "Order Intents   : 0"
    )

    print(
        "Execution       : OFF"
    )

    print(
        "Contract Status : VALID"
    )

    print("=" * 82)


# =============================================================================
# RUNTIME
# =============================================================================

def run(
    validated_signals: Mapping[str, Any],
    fusion_snapshot: Mapping[str, Any],
) -> dict:

    print("=" * 82)
    print("ARUNDA PRODUCTION FUSED-SCORE BINDING v0.1")
    print("=" * 82)

    print(
        "Input           : REAL FUSION_v0.6"
    )

    print(
        "Output          : REAL SCORE SNAPSHOT"
    )

    print(
        "Database        : NOT TOUCHED"
    )

    print(
        "DB Writes       : 0"
    )

    print(
        "Execution       : OFF"
    )

    print("=" * 82)

    try:

        if validated_signals is None:

            raise RuntimeError(
                "validated_signals is required"
            )

        if fusion_snapshot is None:

            raise RuntimeError(
                "fusion_snapshot is required"
            )

        scores = build_score_snapshot(
            validated_signals,
            fusion_snapshot,
        )

        validate_score_snapshot(
            validated_signals,
            scores,
        )

        print_result(
            scores
        )

        print_contract(
            scores
        )

        print()
        print(
            "FUSED-SCORE BINDING STATUS : PASS"
        )

        return scores

    except Exception as error:

        print()
        print("=" * 82)
        print("FUSED-SCORE BINDING ERROR")
        print("=" * 82)

        print(
            "Type  :",
            type(error).__name__,
        )

        print(
            "Error :",
            str(error),
        )

        print()
        print(
            "FUSED-SCORE BINDING STATUS : FAILED"
        )

        raise


# =============================================================================
# MAIN
# =============================================================================

def main(
    validated_signals: Mapping[str, Any],
    fusion_snapshot: Mapping[str, Any],
) -> dict:

    return run(
        validated_signals,
        fusion_snapshot,
    )


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    print("=" * 82)
    print(
        "ARUNDA PRODUCTION FUSED-SCORE BINDING v0.1"
    )
    print("=" * 82)

    print(
        "STATUS : NOT EXECUTED"
    )

    print(
        "REASON : Real validated_signals and "
        "fusion_snapshot are required."
    )

    print(
        "REQUIRED:"
    )

    print(
        "    run("
    )

    print(
        "        validated_signals,"
    )

    print(
        "        fusion_snapshot,"
    )

    print(
        "    )"
    )

    print("=" * 82)