# =============================================================================
# ARUNDA DECISION ENGINE v0.6
# DIRECT SCORE SNAPSHOT CONTRACT
# =============================================================================
#
# PURPOSE
# -------
# Combine:
#
#     VALIDATED SIGNAL SNAPSHOT
#     +
#     REAL SCORE SNAPSHOT
#
# and produce:
#
#     DECISION SNAPSHOT
#
#
# ARCHITECTURE
# ------------
#
# signal_engine
#       |
#       v
# signal_validator
#       |
#       v
# VALIDATED SIGNAL SNAPSHOT
#
# signal_scorer
#       |
#       v
# REAL SCORE SNAPSHOT
#
# validated_signals + scores
#       |
#       v
# DECISION ENGINE
#       |
#       v
# DECISION SNAPSHOT
#
#
# IMPORTANT ARCHITECTURAL REPAIR
# ------------------------------
#
# Decision Engine NO LONGER knows about:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# These belong upstream.
#
# Decision Engine does NOT generate:
#
#     features
#     indicators
#     structures
#     scores
#     signals
#
# Decision Engine ONLY consumes:
#
#     validated_signals
#     scores
#
#
# RULES
# -----
# - MEMORY ONLY
# - READ ONLY
# - NO SQL
# - NO DATABASE
# - NO DATABASE WRITES
# - NO SYNTHETIC DATA
# - NO FEATURE GENERATION
# - NO INDICATOR GENERATION
# - NO STRUCTURE GENERATION
# - NO SCORE GENERATION
# - NO SIGNAL GENERATION
# - NO PREDICTION
# - NO RANKING
# - NO RISK
# - NO EXECUTION
#
# =============================================================================

from __future__ import annotations

import math
from typing import Any, Mapping

import decision_contract


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


SIGNAL_STATES = (
    "ACTIVE",
    "NEUTRAL",
)

DECISION_STATES = (
    "ACTIONABLE",
    "HOLD",
    "REJECT",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)


# =============================================================================
# SNAPSHOT TYPES
# =============================================================================

ValidatedSignalSnapshot = Mapping[
    str,
    Mapping[str, Any],
]

ScoreSnapshot = Mapping[
    str,
    Mapping[str, Any],
]


# =============================================================================
# SNAPSHOT KEY VALIDATION
# =============================================================================

def validate_asset_keys(
    snapshot: Any,
    source_name: str,
) -> None:

    if not isinstance(
        snapshot,
        Mapping,
    ):

        raise RuntimeError(
            f"{source_name} must be a mapping"
        )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        snapshot.keys()
    )

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            f"{source_name} missing assets: "
            f"{sorted(missing)}"
        )

    if extra:

        raise RuntimeError(
            f"{source_name} contains unexpected assets: "
            f"{sorted(extra)}"
        )

    if len(actual) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            f"{source_name} asset count mismatch: "
            f"{len(actual)} != "
            f"{EXPECTED_ASSET_COUNT}"
        )


# =============================================================================
# VALIDATE ONE SIGNAL RECORD
# =============================================================================

def validate_signal_record(
    asset: str,
    record: Any,
) -> Mapping[str, Any]:

    if not isinstance(
        record,
        Mapping,
    ):

        raise RuntimeError(
            f"Invalid validated signal record: {asset}"
        )

    required = (
        "asset",
        "signal_state",
        "direction",
        "valid",
        "validation",
    )

    missing = [
        field
        for field in required
        if field not in record
    ]

    if missing:

        raise RuntimeError(
            f"Validated signal {asset} missing fields: "
            f"{missing}"
        )

    if record["asset"] != asset:

        raise RuntimeError(
            f"Signal asset mismatch: {asset}"
        )

    state = record["signal_state"]
    direction = record["direction"]
    valid = record["valid"]
    validation = record["validation"]

    if state not in SIGNAL_STATES:

        raise RuntimeError(
            f"Invalid signal state for {asset}: "
            f"{state}"
        )

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid signal direction for {asset}: "
            f"{direction}"
        )

    if not isinstance(
        valid,
        bool,
    ):

        raise RuntimeError(
            f"Invalid validator flag for {asset}: "
            f"{valid!r}"
        )

    if not isinstance(
        validation,
        str,
    ):

        raise RuntimeError(
            f"Invalid validation reason for {asset}"
        )

    # -------------------------------------------------------------------------
    # Signal semantic consistency
    # -------------------------------------------------------------------------

    if state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"ACTIVE signal must have LONG/SHORT "
                f"direction: {asset}"
            )

    elif state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                f"NEUTRAL signal must have NONE "
                f"direction: {asset}"
            )

    return record


# =============================================================================
# VALIDATE ONE SCORE RECORD
# =============================================================================

def validate_score_record(
    asset: str,
    record: Any,
) -> Mapping[str, Any]:

    if not isinstance(
        record,
        Mapping,
    ):

        raise RuntimeError(
            f"Invalid score record: {asset}"
        )

    required = (
        "asset",
        "signal_state",
        "direction",
        "score",
    )

    missing = [
        field
        for field in required
        if field not in record
    ]

    if missing:

        raise RuntimeError(
            f"Score record {asset} missing fields: "
            f"{missing}"
        )

    if record["asset"] != asset:

        raise RuntimeError(
            f"Score asset mismatch: {asset}"
        )

    state = record["signal_state"]
    direction = record["direction"]
    score = record["score"]

    if state not in SIGNAL_STATES:

        raise RuntimeError(
            f"Invalid score signal state for {asset}: "
            f"{state}"
        )

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid score direction for {asset}: "
            f"{direction}"
        )

    if isinstance(
        score,
        bool,
    ):

        raise RuntimeError(
            f"Boolean score is invalid for {asset}"
        )

    if not isinstance(
        score,
        (int, float),
    ):

        raise RuntimeError(
            f"Invalid score for {asset}: "
            f"{score!r}"
        )

    if not math.isfinite(
        float(score)
    ):

        raise RuntimeError(
            f"Non-finite score for {asset}: "
            f"{score!r}"
        )

    # -------------------------------------------------------------------------
    # Score semantic consistency
    # -------------------------------------------------------------------------

    if state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"ACTIVE score must have LONG/SHORT "
                f"direction: {asset}"
            )

    elif state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                f"NEUTRAL score must have NONE "
                f"direction: {asset}"
            )

    return record


# =============================================================================
# CROSS VALIDATE SIGNAL + SCORE
# =============================================================================

def cross_validate_signal_and_score(
    asset: str,
    signal_record: Mapping[str, Any],
    score_record: Mapping[str, Any],
) -> None:

    if (
        signal_record["signal_state"]
        !=
        score_record["signal_state"]
    ):

        raise RuntimeError(
            f"Signal/scorer state mismatch: {asset}"
        )

    if (
        signal_record["direction"]
        !=
        score_record["direction"]
    ):

        raise RuntimeError(
            f"Signal/scorer direction mismatch: {asset}"
        )


# =============================================================================
# DETERMINE DECISION
# =============================================================================

def determine_decision(
    signal_record: Mapping[str, Any],
    score_record: Mapping[str, Any],
) -> dict:

    state = signal_record["signal_state"]
    direction = signal_record["direction"]
    valid = signal_record["valid"]

    score = float(
        score_record["score"]
    )

    # -------------------------------------------------------------------------
    # Validator rejection
    # -------------------------------------------------------------------------

    if valid is not True:

        return {
            "state": "REJECT",
            "direction": "NONE",
            "score": score,
            "reason": (
                "VALIDATOR_REJECTED:"
                +
                signal_record["validation"]
            ),
        }

    # -------------------------------------------------------------------------
    # Neutral
    # -------------------------------------------------------------------------

    if state == "NEUTRAL":

        if direction == "NONE":

            return {
                "state": "HOLD",
                "direction": "NONE",
                "score": score,
                "reason": "VALID_NEUTRAL_SIGNAL",
            }

        return {
            "state": "REJECT",
            "direction": "NONE",
            "score": score,
            "reason": "INVALID_NEUTRAL_DIRECTION",
        }

    # -------------------------------------------------------------------------
    # Active
    # -------------------------------------------------------------------------

    if state == "ACTIVE":

        if direction in (
            "LONG",
            "SHORT",
        ):

            return {
                "state": "ACTIONABLE",
                "direction": direction,
                "score": score,
                "reason": "VALID_ACTIVE_SIGNAL",
            }

        return {
            "state": "REJECT",
            "direction": "NONE",
            "score": score,
            "reason": "INVALID_ACTIVE_DIRECTION",
        }

    # -------------------------------------------------------------------------
    # Unknown state
    # -------------------------------------------------------------------------

    return {
        "state": "REJECT",
        "direction": "NONE",
        "score": score,
        "reason": "UNKNOWN_SIGNAL_STATE",
    }


# =============================================================================
# BUILD ONE DECISION
# =============================================================================

def build_decision(
    asset: str,
    signal_record: Mapping[str, Any],
    score_record: Mapping[str, Any],
) -> dict:

    signal = validate_signal_record(
        asset,
        signal_record,
    )

    score = validate_score_record(
        asset,
        score_record,
    )

    cross_validate_signal_and_score(
        asset,
        signal,
        score,
    )

    result = determine_decision(
        signal,
        score,
    )

    decision = {
        "asset": asset,
        "state": result["state"],
        "direction": result["direction"],
        "score": result["score"],
        "reason": result["reason"],
    }

    # -------------------------------------------------------------------------
    # Local Decision Contract
    # -------------------------------------------------------------------------

    if not hasattr(
        decision_contract,
        "validate_decision",
    ):

        raise RuntimeError(
            "decision_contract.py must expose "
            "validate_decision()"
        )

    contract_result = (
        decision_contract.validate_decision(
            decision
        )
    )

    if contract_result is False:

        raise RuntimeError(
            f"Decision contract rejected: {asset}"
        )

    return decision


# =============================================================================
# BUILD COMPLETE DECISION SNAPSHOT
# =============================================================================

def build_decision_snapshot(
    validated_signals: ValidatedSignalSnapshot,
    scores: ScoreSnapshot,
) -> dict:

    validate_asset_keys(
        validated_signals,
        "validated signals",
    )

    validate_asset_keys(
        scores,
        "scores",
    )

    decisions = {}

    for asset in EXPECTED_ASSETS:

        decisions[asset] = build_decision(
            asset,
            validated_signals[asset],
            scores[asset],
        )

    return decisions


# =============================================================================
# VALIDATE COMPLETE DECISION SNAPSHOT
# =============================================================================

def validate_decision_snapshot(
    snapshot: Any,
) -> bool:

    if not hasattr(
        decision_contract,
        "validate_decision_snapshot",
    ):

        raise RuntimeError(
            "decision_contract.py must expose "
            "validate_decision_snapshot()"
        )

    result = (
        decision_contract
        .validate_decision_snapshot(
            snapshot
        )
    )

    if result is False:

        raise RuntimeError(
            "Decision snapshot contract invalid"
        )

    return True


# =============================================================================
# INTERNAL SNAPSHOT VALIDATION
# =============================================================================

def validate_internal_snapshot(
    snapshot: Any,
) -> bool:

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "Decision snapshot must be a dictionary"
        )

    validate_asset_keys(
        snapshot,
        "decision snapshot",
    )

    for asset in EXPECTED_ASSETS:

        decision = snapshot[asset]

        if not isinstance(
            decision,
            dict,
        ):

            raise RuntimeError(
                f"Invalid decision object: {asset}"
            )

        required = (
            "asset",
            "state",
            "direction",
            "score",
            "reason",
        )

        for field in required:

            if field not in decision:

                raise RuntimeError(
                    f"Decision {asset} missing field: "
                    f"{field}"
                )

        if decision["asset"] != asset:

            raise RuntimeError(
                f"Decision asset mismatch: {asset}"
            )

        if decision["state"] not in DECISION_STATES:

            raise RuntimeError(
                f"Invalid decision state for {asset}: "
                f"{decision['state']}"
            )

        if decision["direction"] not in DIRECTIONS:

            raise RuntimeError(
                f"Invalid decision direction for {asset}: "
                f"{decision['direction']}"
            )

        if isinstance(
            decision["score"],
            bool,
        ):

            raise RuntimeError(
                f"Invalid decision score for {asset}"
            )

        if not isinstance(
            decision["score"],
            (int, float),
        ):

            raise RuntimeError(
                f"Invalid decision score for {asset}"
            )

        if not math.isfinite(
            float(decision["score"])
        ):

            raise RuntimeError(
                f"Non-finite decision score for {asset}"
            )

        if not isinstance(
            decision["reason"],
            str,
        ):

            raise RuntimeError(
                f"Invalid decision reason for {asset}"
            )

        # ---------------------------------------------------------------------
        # Decision semantic consistency
        # ---------------------------------------------------------------------

        state = decision["state"]
        direction = decision["direction"]

        if state == "ACTIONABLE":

            if direction not in (
                "LONG",
                "SHORT",
            ):

                raise RuntimeError(
                    f"ACTIONABLE decision must have "
                    f"LONG/SHORT direction: {asset}"
                )

        elif state == "HOLD":

            if direction != "NONE":

                raise RuntimeError(
                    f"HOLD decision must have "
                    f"NONE direction: {asset}"
                )

        elif state == "REJECT":

            if direction != "NONE":

                raise RuntimeError(
                    f"REJECT decision must have "
                    f"NONE direction: {asset}"
                )

    return True


# =============================================================================
# STATISTICS
# =============================================================================

def calculate_statistics(
    snapshot: Mapping[str, Mapping[str, Any]],
) -> dict:

    actionable = 0
    hold = 0
    reject = 0

    long_count = 0
    short_count = 0
    none_count = 0

    for asset in EXPECTED_ASSETS:

        item = snapshot[asset]

        state = item["state"]
        direction = item["direction"]

        if state == "ACTIONABLE":

            actionable += 1

        elif state == "HOLD":

            hold += 1

        elif state == "REJECT":

            reject += 1

        if direction == "LONG":

            long_count += 1

        elif direction == "SHORT":

            short_count += 1

        elif direction == "NONE":

            none_count += 1

    return {
        "actionable": actionable,
        "hold": hold,
        "reject": reject,
        "long": long_count,
        "short": short_count,
        "none": none_count,
    }


# =============================================================================
# HEADER
# =============================================================================

def print_header() -> None:

    print("=" * 82)
    print("ARUNDA DECISION ENGINE v0.6")
    print("=" * 82)

    print(
        "Signals       : validated_signals"
    )

    print(
        "Scores        : REAL score snapshot"
    )

    print(
        "Input Contract: validated_signals + scores"
    )

    print(
        "Feature Gen   : NOT USED"
    )

    print(
        "Indicator Gen : NOT USED"
    )

    print(
        "Structure Gen : NOT USED"
    )

    print(
        "Score Gen     : NOT USED"
    )

    print(
        "Prediction    : NOT USED"
    )

    print(
        "Ranking       : NOT USED"
    )

    print(
        "Risk          : NOT USED"
    )

    print(
        "Execution     : NOT USED"
    )

    print(
        "Storage       : MEMORY ONLY"
    )

    print(
        "Writes        : NONE"
    )

    print(
        "SQL           : NOT USED"
    )

    print("=" * 82)


# =============================================================================
# PRINT DECISIONS
# =============================================================================

def print_decisions(
    snapshot: Mapping[str, Mapping[str, Any]],
) -> None:

    print()
    print(
        "DECISION SNAPSHOT"
    )

    print("-" * 100)

    print(
        "Asset  | Decision    | Direction | Score        | Reason"
    )

    print("-" * 100)

    for asset in EXPECTED_ASSETS:

        decision = snapshot[asset]

        print(
            f"{asset:<6} | "
            f"{decision['state']:<11} | "
            f"{decision['direction']:<9} | "
            f"{decision['score']:>11.6f} | "
            f"{decision['reason']}"
        )

    print()


# =============================================================================
# PRINT CONTRACT
# =============================================================================

def print_contract(
    snapshot: Mapping[str, Mapping[str, Any]],
) -> bool:

    stats = calculate_statistics(
        snapshot
    )

    print("=" * 82)
    print(
        "DECISION ENGINE CONTRACT"
    )
    print("=" * 82)

    print(
        f"Expected Assets : {EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Ready Assets    : {len(snapshot)}"
    )

    print(
        f"Actionable      : {stats['actionable']}"
    )

    print(
        f"Hold            : {stats['hold']}"
    )

    print(
        f"Reject          : {stats['reject']}"
    )

    print(
        f"LONG            : {stats['long']}"
    )

    print(
        f"SHORT           : {stats['short']}"
    )

    print(
        f"NONE            : {stats['none']}"
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
        "Feature Gen     : NOT USED"
    )

    print(
        "Indicator Gen   : NOT USED"
    )

    print(
        "Structure Gen   : NOT USED"
    )

    print(
        "Score Gen       : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Risk            : NOT USED"
    )

    print(
        "Execution       : NOT USED"
    )

    print(
        "Contract Status : VALID"
    )

    print("=" * 82)

    return True


# =============================================================================
# MAIN
# =============================================================================
#
# NEW CONTRACT:
#
#     main(
#         validated_signals,
#         scores,
#     )
#
# NO bars_by_asset
# NO indicators_by_asset
# NO structures_by_asset
#
# =============================================================================

def main(
    validated_signals: ValidatedSignalSnapshot,
    scores: ScoreSnapshot,
) -> dict:

    print_header()

    try:

        # ---------------------------------------------------------------------
        # 1. Input boundary
        # ---------------------------------------------------------------------

        if validated_signals is None:

            raise RuntimeError(
                "validated_signals is required"
            )

        if scores is None:

            raise RuntimeError(
                "scores is required"
            )

        # ---------------------------------------------------------------------
        # 2. Build decision snapshot
        # ---------------------------------------------------------------------

        decision_snapshot = (
            build_decision_snapshot(
                validated_signals,
                scores,
            )
        )

        # ---------------------------------------------------------------------
        # 3. Internal validation
        # ---------------------------------------------------------------------

        validate_internal_snapshot(
            decision_snapshot
        )

        # ---------------------------------------------------------------------
        # 4. Formal contract validation
        # ---------------------------------------------------------------------

        validate_decision_snapshot(
            decision_snapshot
        )

        # ---------------------------------------------------------------------
        # 5. Print result
        # ---------------------------------------------------------------------

        print_decisions(
            decision_snapshot
        )

        print_contract(
            decision_snapshot
        )

        print()
        print(
            "DECISION ENGINE STATUS : READY"
        )

        return decision_snapshot

    except Exception as error:

        print()
        print("=" * 82)
        print(
            "DECISION ENGINE ERROR"
        )
        print("=" * 82)

        print(
            "Type   :",
            type(error).__name__,
        )

        print(
            "Error  :",
            str(error),
        )

        print()

        print(
            "DECISION ENGINE STATUS : FAILED"
        )

        raise


# =============================================================================
# RUN ALIAS
# =============================================================================

def run(
    validated_signals: ValidatedSignalSnapshot,
    scores: ScoreSnapshot,
) -> dict:

    return main(
        validated_signals,
        scores,
    )


# =============================================================================
# DIRECT EXECUTION
# =============================================================================
#
# Decision Engine cannot manufacture:
#
#     validated_signals
#     scores
#
# Therefore direct execution does NOT fabricate inputs.
#
# The real runtime must call:
#
#     decision_engine.run(
#         validated_signals,
#         scores,
#     )
#
# =============================================================================

if __name__ == "__main__":

    print("=" * 82)
    print(
        "ARUNDA DECISION ENGINE v0.6"
    )
    print("=" * 82)

    print(
        "STATUS : NOT EXECUTED"
    )

    print(
        "REASON : Real validated_signals and scores "
        "are required."
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