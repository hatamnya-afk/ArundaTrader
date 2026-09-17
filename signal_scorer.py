# =============================================================================
# ARUNDA SIGNAL SCORER v0.4
# =============================================================================
#
# PURPOSE
# -------
# Consume and validate the REAL score snapshot produced by the REAL
# upstream Score Producer.
#
#
# FINAL ARCHITECTURE
# ------------------
#
# signal_engine.build_all()
#        |
#        v
# signal_validator
#        |
#        v
# validated_signals
#        |
#        +-----------------------------+
#                                      |
#                                      v
#                              REAL SCORE PRODUCER
#                                      |
#                                      v
#                                    scores
#                                      |
#                                      v
#                              SIGNAL SCORER CONTRACT
#                                      |
#                                      v
#                                  DECISION ENGINE
#
#
# IMPORTANT CONTRACT REPAIR
# --------------------------
#
# REMOVED:
#
#     BarsByAsset
#     IndicatorsByAsset
#     StructuresByAsset
#
# REMOVED:
#
#     feature_contract loading
#     market_state loading
#     market_regime loading
#     signal loading
#     internal feature calculation
#     synthetic score generation
#
#
# THIS MODULE NOW RECEIVES:
#
#     validated_signals
#     scores
#
#
# RUNTIME CONTRACT:
#
#     run(
#         validated_signals,
#         scores,
#     )
#
#
# RULES
# -----
# - MEMORY ONLY
# - READ ONLY
# - NO SQL
# - NO DATABASE
# - NO DATABASE WRITES
# - NO FEATURE FABRICATION
# - NO SCORE FABRICATION
# - NO SIGNAL FABRICATION
# - NO NEW SIGNAL
# - NO DECISION
# - NO PREDICTION
# - NO RANKING
# - NO INTERPRETATION
#
# SCORE PRODUCER:
# ----------------
# This module does NOT manufacture scores.
#
# The upstream producer is authoritative.
#
# If the real producer is missing, this module FAILS CLOSED.
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
# SCORE PRODUCER STATE
# =============================================================================
#
# This module is NOT the producer.
#
# The actual producer must supply the scores argument to run().
#
# =============================================================================

SCORE_PRODUCER = "UPSTREAM_RUNTIME"

SCORER_VERSION = "SCORER_v0.4"


# =============================================================================
# NUMERIC VALIDATION
# =============================================================================

def safe_float(
    value: Any,
) -> float:

    if isinstance(
        value,
        bool,
    ):
        raise RuntimeError(
            "Boolean is not a valid numeric score."
        )

    try:

        result = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as error:

        raise RuntimeError(
            "Invalid numeric score: "
            + repr(value)
        ) from error

    if not math.isfinite(
        result
    ):

        raise RuntimeError(
            "Non-finite score: "
            + repr(value)
        )

    return result


# =============================================================================
# ASSET CONTRACT
# =============================================================================

def validate_asset_keys(
    data: Any,
    name: str,
) -> None:

    if not isinstance(
        data,
        dict,
    ):

        raise RuntimeError(
            name
            + " must be a dict."
        )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        data.keys()
    )

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            "Missing assets in "
            + name
            + ": "
            + repr(
                sorted(missing)
            )
        )

    if extra:

        raise RuntimeError(
            "Unexpected assets in "
            + name
            + ": "
            + repr(
                sorted(extra)
            )
        )

    if len(data) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "Asset count mismatch in "
            + name
            + ": "
            + str(
                len(data)
            )
        )


# =============================================================================
# VALIDATED SIGNAL CONTRACT
# =============================================================================

def validate_validated_signal(
    asset: str,
    signal: Mapping[str, Any],
) -> None:

    if not isinstance(
        signal,
        dict,
    ):

        raise RuntimeError(
            "Invalid validated signal object: "
            + asset
        )

    if signal.get(
        "asset"
    ) != asset:

        raise RuntimeError(
            "Validated signal asset mismatch: "
            + asset
        )

    if signal.get(
        "valid"
    ) is not True:

        raise RuntimeError(
            "Cannot score invalid validated signal: "
            + asset
        )

    signal_state = signal.get(
        "signal_state"
    )

    direction = signal.get(
        "direction"
    )

    if signal_state not in VALID_SIGNAL_STATES:

        raise RuntimeError(
            "Invalid signal state for "
            + asset
            + ": "
            + repr(signal_state)
        )

    if direction not in VALID_DIRECTIONS:

        raise RuntimeError(
            "Invalid direction for "
            + asset
            + ": "
            + repr(direction)
        )

    if signal_state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                "ACTIVE signal without LONG/SHORT direction: "
                + asset
            )

    if signal_state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                "NEUTRAL signal with non-NONE direction: "
                + asset
            )


# =============================================================================
# VALIDATED SIGNAL SNAPSHOT
# =============================================================================

def validate_validated_signals(
    validated_signals: Any,
) -> bool:

    validate_asset_keys(
        validated_signals,
        "validated_signals",
    )

    for asset in EXPECTED_ASSETS:

        validate_validated_signal(
            asset,
            validated_signals[asset],
        )

    return True


# =============================================================================
# SCORE ITEM CONTRACT
# =============================================================================

def validate_score_item(
    asset: str,
    score_item: Mapping[str, Any],
    validated_signal: Mapping[str, Any],
) -> None:

    if not isinstance(
        score_item,
        dict,
    ):

        raise RuntimeError(
            "Invalid score object: "
            + asset
        )

    # -------------------------------------------------------------------------
    # REQUIRED FIELDS
    # -------------------------------------------------------------------------

    required = {
        "asset",
        "signal_state",
        "direction",
        "score",
    }

    missing = (
        required
        - set(
            score_item.keys()
        )
    )

    if missing:

        raise RuntimeError(
            "Score missing required fields for "
            + asset
            + ": "
            + repr(
                sorted(missing)
            )
        )

    # -------------------------------------------------------------------------
    # ASSET IDENTITY
    # -------------------------------------------------------------------------

    if score_item.get(
        "asset"
    ) != asset:

        raise RuntimeError(
            "Score asset mismatch: "
            + asset
        )

    # -------------------------------------------------------------------------
    # SIGNAL ALIGNMENT
    # -------------------------------------------------------------------------

    score_state = score_item.get(
        "signal_state"
    )

    score_direction = score_item.get(
        "direction"
    )

    signal_state = validated_signal.get(
        "signal_state"
    )

    signal_direction = validated_signal.get(
        "direction"
    )

    if score_state != signal_state:

        raise RuntimeError(
            "Score / signal state mismatch for "
            + asset
            + ": score="
            + repr(score_state)
            + " signal="
            + repr(signal_state)
        )

    if score_direction != signal_direction:

        raise RuntimeError(
            "Score / signal direction mismatch for "
            + asset
            + ": score="
            + repr(score_direction)
            + " signal="
            + repr(signal_direction)
        )

    # -------------------------------------------------------------------------
    # STATE CONTRACT
    # -------------------------------------------------------------------------

    if score_state not in VALID_SIGNAL_STATES:

        raise RuntimeError(
            "Invalid score signal state for "
            + asset
        )

    if score_direction not in VALID_DIRECTIONS:

        raise RuntimeError(
            "Invalid score direction for "
            + asset
        )

    # -------------------------------------------------------------------------
    # SCORE NUMERIC CONTRACT
    # -------------------------------------------------------------------------

    score = safe_float(
        score_item.get(
            "score"
        )
    )

    if score < -1.0 or score > 1.0:

        raise RuntimeError(
            "Score outside [-1, +1] for "
            + asset
            + ": "
            + repr(score)
        )

    # -------------------------------------------------------------------------
    # NONE DIRECTION CONTRACT
    # -------------------------------------------------------------------------

    if score_direction == "NONE":

        if score != 0.0:

            raise RuntimeError(
                "NONE direction must have score 0.0 for "
                + asset
            )


# =============================================================================
# SCORE SNAPSHOT CONTRACT
# =============================================================================

def validate_score_snapshot(
    validated_signals: Mapping[str, Any],
    scores: Any,
) -> bool:

    validate_validated_signals(
        validated_signals
    )

    validate_asset_keys(
        scores,
        "scores",
    )

    for asset in EXPECTED_ASSETS:

        validate_score_item(
            asset,
            scores[asset],
            validated_signals[asset],
        )

    return True


# =============================================================================
# LOAD SCORES
# =============================================================================
#
# CRITICAL CONTRACT CHANGE
# ------------------------
#
# OLD:
#
#     load_scores(
#         bars_by_asset,
#         indicators_by_asset,
#         structures_by_asset,
#     )
#
# NEW:
#
#     load_scores(scores)
#
#
# No upstream reconstruction happens here.
#
# =============================================================================

def load_scores(
    scores: Any,
):

    if scores is None:

        raise RuntimeError(
            "REAL SCORE PRODUCER OUTPUT IS MISSING."
        )

    if not isinstance(
        scores,
        dict,
    ):

        raise RuntimeError(
            "Score Producer must return a dict."
        )

    return scores


# =============================================================================
# SCORE ALIGNMENT
# =============================================================================

def align_scores(
    validated_signals: Mapping[str, Any],
    scores: Mapping[str, Any],
):

    validate_score_snapshot(
        validated_signals,
        scores,
    )

    aligned = {}

    for asset in EXPECTED_ASSETS:

        source = scores[
            asset
        ]

        aligned[
            asset
        ] = dict(
            source
        )

    return aligned


# =============================================================================
# SCORE CONTRACT REPORT
# =============================================================================

def print_scores(
    scores: Mapping[str, Any],
):

    print(
        "REAL SIGNAL SCORE SNAPSHOT"
    )

    print("-" * 82)

    print(
        "Asset  | State   | Direction | Score"
    )

    print("-" * 82)

    for asset in EXPECTED_ASSETS:

        item = scores[
            asset
        ]

        print(
            "{:<6} | {:<7} | {:<9} | {:+.6f}".format(
                asset,
                item["signal_state"],
                item["direction"],
                float(
                    item["score"]
                ),
            )
        )

    print()


# =============================================================================
# CONTRACT SUMMARY
# =============================================================================

def print_contract(
    validated_signals,
    scores,
):

    active = 0
    neutral = 0

    for asset in EXPECTED_ASSETS:

        direction = scores[
            asset
        ][
            "direction"
        ]

        if direction == "NONE":

            neutral += 1

        else:

            active += 1

    valid = False

    try:

        valid = validate_score_snapshot(
            validated_signals,
            scores,
        )

    except Exception:

        valid = False

    print("=" * 82)
    print(
        "SIGNAL SCORE CONTRACT"
    )
    print("=" * 82)

    print(
        "Scorer Version  :",
        SCORER_VERSION,
    )

    print(
        "Score Producer  :",
        SCORE_PRODUCER,
    )

    print(
        "Expected Assets :",
        EXPECTED_ASSET_COUNT,
    )

    print(
        "Scored Assets   :",
        len(scores),
    )

    print(
        "Active Signals  :",
        active,
    )

    print(
        "Neutral Signals :",
        neutral,
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "SQL             : NOT USED"
    )

    print(
        "Feature Loading : NOT USED"
    )

    print(
        "Signal Loading  : NOT USED"
    )

    print(
        "Decision        : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    print(
        "Contract Status :",
        "VALID"
        if valid
        else "INVALID",
    )

    print()

    return valid


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 82)
    print(
        "ARUNDA SIGNAL SCORER v0.4"
    )
    print("=" * 82)

    print(
        "Input 1    : validated_signals"
    )

    print(
        "Input 2    : REAL scores"
    )

    print(
        "Producer   : UPSTREAM RUNTIME"
    )

    print(
        "Storage    : MEMORY ONLY"
    )

    print(
        "Writes     : NONE"
    )

    print(
        "SQL        : NOT USED"
    )

    print(
        "Feature    : NOT LOADED"
    )

    print(
        "Signal     : NOT LOADED"
    )

    print(
        "Decision   : NOT USED"
    )

    print(
        "Prediction : NOT USED"
    )

    print(
        "Ranking    : NOT USED"
    )

    print("=" * 82)
    print()


# =============================================================================
# RUNTIME
# =============================================================================
#
# FINAL CONTRACT:
#
#     run(
#         validated_signals,
#         scores,
#     )
#
# =============================================================================

def run(
    validated_signals,
    scores,
):

    print_header()

    # -------------------------------------------------------------------------
    # VALIDATED SIGNAL INPUT
    # -------------------------------------------------------------------------

    validate_validated_signals(
        validated_signals
    )

    # -------------------------------------------------------------------------
    # REAL SCORE INPUT
    # -------------------------------------------------------------------------

    real_scores = load_scores(
        scores
    )

    # -------------------------------------------------------------------------
    # ALIGN + VALIDATE
    # -------------------------------------------------------------------------

    aligned_scores = align_scores(
        validated_signals,
        real_scores,
    )

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

    print_scores(
        aligned_scores
    )

    valid = print_contract(
        validated_signals,
        aligned_scores,
    )

    if not valid:

        raise RuntimeError(
            "SIGNAL SCORE CONTRACT INVALID"
        )

    print(
        "SIGNAL SCORER STATUS : READY"
    )

    return aligned_scores


# =============================================================================
# MAIN
# =============================================================================
#
# MAIN NOW HAS THE SAME REAL RUNTIME CONTRACT.
#
# =============================================================================

def main(
    validated_signals,
    scores,
):

    try:

        return run(
            validated_signals,
            scores,
        )

    except Exception as error:

        print("=" * 82)
        print(
            "SIGNAL SCORER ERROR"
        )
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
            "SIGNAL SCORER STATUS : FAILED"
        )

        raise


# =============================================================================
# DIRECT EXECUTION
# =============================================================================
#
# Deliberately disabled.
#
# The scorer cannot manufacture:
#
#     validated_signals
#     scores
#
# Both must come from the real upstream runtime.
#
# =============================================================================

if __name__ == "__main__":

    print("=" * 82)
    print(
        "ARUNDA SIGNAL SCORER v0.4"
    )
    print("=" * 82)

    print(
        "STATUS : NOT EXECUTED"
    )

    print(
        "REASON : Real validated_signals and scores are required."
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
        "        scores,"
    )

    print(
        "    )"
    )

    print("=" * 82)