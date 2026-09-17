import inspect
import math
import sys
from pathlib import Path
from typing import Any, Mapping


# =============================================================================
# ARUNDA TRADER
# M2 — REAL SIGNAL TO PRODUCTION SCORER RUNTIME
# v0.2
# =============================================================================
#
# PURPOSE
# -------
# Execute the real production signal path:
#
#     signal_engine.build_all()
#             |
#             v
#     result[asset]["signal"]
#             |
#             v
#     REAL SIGNAL SEMANTIC RESOLUTION
#             |
#             v
#     signal_scorer.calculate_score()
#             |
#             v
#     REAL VALID SCORE
#
# RULES
# -----
# - signal_engine.build_all() is the ONLY signal source
# - signal_scorer.calculate_score() is the production scorer
# - NO synthetic signals
# - NO synthetic features
# - NO database writes
# - NO decision engine
# - NO prediction
# - NO execution
# - NO production source modification
#
# IMPORTANT
# ---------
# The current signal object does not expose an "eligible" field.
#
# Therefore this runtime MUST NOT invent:
#
#     signal["eligible"]
#
# Eligibility is resolved from the real signal semantic state:
#
#     ACTIVE + LONG/SHORT => scorer-consumable signal
#     NEUTRAL/NONE         => not scorer-consumable
#
# =============================================================================


ENGINE_VERSION = "M2_REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.2"

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# IMPORTS
# =============================================================================

import signal_engine
import signal_scorer


# =============================================================================
# CONSTANTS
# =============================================================================

ACTIVE_STATE = "ACTIVE"

LONG = "LONG"
SHORT = "SHORT"

VALID_DIRECTIONS = {
    LONG,
    SHORT,
}


# =============================================================================
# TERMINAL
# =============================================================================

def line(char="=", length=100):
    print(char * length)


def fail(message):
    raise RuntimeError(message)


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def is_mapping(value):
    return isinstance(value, Mapping)


def clean_text(value):
    if value is None:
        return None

    return str(value).strip().upper()


def safe_float(value):
    try:
        if value is None:
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (
        TypeError,
        ValueError,
    ):
        return None


# =============================================================================
# PRODUCTION SCORER RESOLUTION
# =============================================================================

def resolve_production_scorer():
    """
    Resolve ONLY the real production scorer.

    Required production function:

        signal_scorer.calculate_score(
            direction,
            feature_record,
            structural_state,
            regime_data
        )
    """

    module_name = "signal_scorer"
    function_name = "calculate_score"

    scorer = getattr(
        signal_scorer,
        function_name,
        None,
    )

    if scorer is None:
        fail(
            "BLOCKER:PRODUCTION_SCORER_NOT_FOUND"
        )

    if not callable(scorer):
        fail(
            "BLOCKER:PRODUCTION_SCORER_NOT_CALLABLE"
        )

    signature = inspect.signature(scorer)

    parameters = list(
        signature.parameters.values()
    )

    required_names = [
        "direction",
        "feature_record",
        "structural_state",
        "regime_data",
    ]

    actual_names = [
        parameter.name
        for parameter in parameters
    ]

    if actual_names[:4] != required_names:
        fail(
            "BLOCKER:UNEXPECTED_PRODUCTION_SCORER_SIGNATURE:"
            f"{actual_names}"
        )

    return scorer, module_name, function_name, signature


# =============================================================================
# REAL SIGNAL EXTRACTION
# =============================================================================

def load_real_signal_snapshot():
    """
    The ONLY permitted signal source.
    """

    build_all = getattr(
        signal_engine,
        "build_all",
        None,
    )

    if build_all is None:
        fail(
            "BLOCKER:SIGNAL_ENGINE_BUILD_ALL_NOT_FOUND"
        )

    if not callable(build_all):
        fail(
            "BLOCKER:SIGNAL_ENGINE_BUILD_ALL_NOT_CALLABLE"
        )

    snapshot = build_all()

    if not isinstance(snapshot, dict):
        fail(
            "BLOCKER:BUILD_ALL_MUST_RETURN_DICT"
        )

    if not snapshot:
        fail(
            "BLOCKER:REAL_SIGNAL_SNAPSHOT_EMPTY"
        )

    return snapshot


# =============================================================================
# SIGNAL RECORD
# =============================================================================

def extract_signal_record(asset, record):
    """
    Consume ONLY:

        build_all()[asset]["signal"]
    """

    if not isinstance(record, Mapping):
        fail(
            f"BLOCKER:INVALID_ASSET_RECORD:{asset}"
        )

    signal = record.get("signal")

    if not isinstance(signal, Mapping):
        fail(
            f"BLOCKER:REAL_SIGNAL_RECORD_MISSING:{asset}"
        )

    return signal


# =============================================================================
# SEMANTIC SIGNAL RESOLUTION
# =============================================================================

def resolve_state(signal):
    """
    Resolve semantic state from the real signal object.

    No default ACTIVE is permitted.
    """

    candidates = (
        "state",
        "signal_state",
        "status",
    )

    for field in candidates:

        if field in signal:

            value = clean_text(
                signal.get(field)
            )

            if value is not None:
                return value

    return None


def resolve_direction(signal):
    """
    Resolve semantic direction from the real signal object.

    No default direction is permitted.
    """

    candidates = (
        "direction",
        "signal_direction",
    )

    for field in candidates:

        if field in signal:

            value = clean_text(
                signal.get(field)
            )

            if value is not None:
                return value

    return None


def resolve_real_eligibility(signal):
    """
    Resolve scorer eligibility from the REAL semantic signal.

    Contract:

        ACTIVE + LONG  -> eligible
        ACTIVE + SHORT -> eligible

        NEUTRAL / NONE -> not eligible

    IMPORTANT:
    We deliberately do NOT read a missing "eligible" field.
    """

    state = resolve_state(signal)

    direction = resolve_direction(signal)

    if state == ACTIVE_STATE and direction in VALID_DIRECTIONS:
        return True

    return False


# =============================================================================
# SCORER INPUT RESOLUTION
# =============================================================================

def extract_mapping(
    record,
    signal,
    names,
):
    """
    Locate an existing real mapping without manufacturing data.

    The scorer requires:
        feature_record
        structural_state
        regime_data

    This resolver only accepts mappings already present in
    the real build_all() result or signal record.
    """

    for name in names:

        value = signal.get(name)

        if isinstance(value, Mapping):
            return value

        value = record.get(name)

        if isinstance(value, Mapping):
            return value

    return None


def resolve_scorer_inputs(
    asset,
    record,
    signal,
):
    """
    Resolve scorer inputs strictly from existing runtime data.

    NO synthetic fallback.
    """

    feature_record = extract_mapping(
        record,
        signal,
        (
            "feature_record",
            "features",
            "feature_snapshot",
        ),
    )

    structural_state = extract_mapping(
        record,
        signal,
        (
            "structural_state",
            "structure",
            "market_structure",
        ),
    )

    regime_data = extract_mapping(
        record,
        signal,
        (
            "regime_data",
            "regime",
            "market_regime",
        ),
    )

    missing = []

    if feature_record is None:
        missing.append(
            "feature_record"
        )

    if structural_state is None:
        missing.append(
            "structural_state"
        )

    if regime_data is None:
        missing.append(
            "regime_data"
        )

    if missing:

        fail(
            "BLOCKER:REAL_SCORER_INPUT_MISSING:"
            f"{asset}:"
            f"{missing}"
        )

    return (
        feature_record,
        structural_state,
        regime_data,
    )


# =============================================================================
# SCORE VALIDATION
# =============================================================================

def validate_real_score(
    asset,
    score,
):
    """
    Validate that the returned score is a REAL finite numeric score.
    """

    numeric_score = safe_float(score)

    if numeric_score is None:

        fail(
            "BLOCKER:INVALID_REAL_SCORE:"
            f"{asset}:{score!r}"
        )

    return numeric_score


# =============================================================================
# SELF TEST
# =============================================================================

def self_test():
    """
    Static/runtime contract checks only.
    """

    if not hasattr(
        signal_engine,
        "build_all",
    ):
        fail(
            "SELF_TEST_FAILED:build_all_missing"
        )

    if not hasattr(
        signal_scorer,
        "calculate_score",
    ):
        fail(
            "SELF_TEST_FAILED:calculate_score_missing"
        )

    scorer = getattr(
        signal_scorer,
        "calculate_score",
    )

    if not callable(scorer):
        fail(
            "SELF_TEST_FAILED:calculate_score_not_callable"
        )

    signature = inspect.signature(
        scorer
    )

    expected = [
        "direction",
        "feature_record",
        "structural_state",
        "regime_data",
    ]

    actual = [
        parameter.name
        for parameter in signature.parameters.values()
    ]

    if actual[:4] != expected:

        fail(
            "SELF_TEST_FAILED:unexpected_scorer_signature:"
            f"{actual}"
        )

    print(
        "SELF TEST : PASS"
    )


# =============================================================================
# MAIN RUNTIME
# =============================================================================

def main():

    print("=" * 100)

    print(
        "ARUNDA TRADER — M2"
    )

    print(
        "REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.2"
    )

    print("=" * 100)

    print(
        f"PROJECT              : {PROJECT_ROOT}"
    )

    print(
        "MODE                 : PRODUCTION RUNTIME READ"
    )

    print(
        "REAL SIGNAL SOURCE   : signal_engine.build_all()"
    )

    print(
        "SCORER               : signal_scorer.calculate_score()"
    )

    print(
        "DATABASE WRITE       : NONE"
    )

    print(
        "SYNTHETIC DATA       : NONE"
    )

    print(
        "DECISION             : NOT USED"
    )

    print(
        "PREDICTION           : NOT USED"
    )

    print(
        "EXECUTION            : NOT USED"
    )

    print("=" * 100)

    print()
    print(
        "Running self-test..."
    )

    self_test()

    # =========================================================================
    # SCORER
    # =========================================================================

    print()
    line("-")

    print(
        "PRODUCTION SCORER RESOLUTION"
    )

    line("-")

    scorer, module_name, function_name, signature = (
        resolve_production_scorer()
    )

    print(
        f"Module       : {module_name}"
    )

    print(
        f"Function     : {function_name}"
    )

    print(
        f"Signature    : {signature}"
    )

    print(
        "Resolution   : DETERMINISTIC"
    )

    print(
        "Status       : PRODUCTION SCORER RESOLVED"
    )

    # =========================================================================
    # REAL SIGNAL
    # =========================================================================

    snapshot = load_real_signal_snapshot()

    print()
    line("-")

    print(
        "REAL SIGNAL SOURCE"
    )

    line("-")

    print(
        "Source       : signal_engine.build_all()"
    )

    print(
        f"Assets       : {len(snapshot)}"
    )

    print(
        "Signal source: build_all()[asset]['signal']"
    )

    print()
    print(
        "REAL SIGNALS"
    )

    line("-")

    real_signals = []

    for asset, record in snapshot.items():

        signal = extract_signal_record(
            asset,
            record,
        )

        state = resolve_state(
            signal
        )

        direction = resolve_direction(
            signal
        )

        eligible = resolve_real_eligibility(
            signal
        )

        print(
            f"{asset:<10}"
            f"STATE={str(state):<12}"
            f"DIRECTION={str(direction):<8}"
            f"SCORER_ELIGIBLE={eligible}"
        )

        if eligible:

            real_signals.append(
                (
                    asset,
                    record,
                    signal,
                    direction,
                )
            )

    # =========================================================================
    # BLOCK ONLY IF REAL SIGNAL PATH IS EMPTY
    # =========================================================================

    if not real_signals:

        print()
        line("=")

        print(
            "M2 STATUS : BLOCKED"
        )

        print(
            "ERROR     : BLOCKER:NO_REAL_ELIGIBLE_SIGNAL"
        )

        print(
            "DETAIL    : build_all() produced no ACTIVE "
            "signal with LONG/SHORT direction."
        )

        line("=")

        return 1

    # =========================================================================
    # SCORE REAL SIGNALS
    # =========================================================================

    print()
    line("-")

    print(
        "REAL SIGNAL → PRODUCTION SCORER"
    )

    line("-")

    print(
        f"{'ASSET':<10}"
        f"{'DIRECTION':<12}"
        f"{'SCORE':>12}"
        f"{'VALID':>10}"
    )

    print("-" * 48)

    scores = {}

    for asset, record, signal, direction in real_signals:

        (
            feature_record,
            structural_state,
            regime_data,
        ) = resolve_scorer_inputs(
            asset,
            record,
            signal,
        )

        raw_score = scorer(
            direction,
            feature_record,
            structural_state,
            regime_data,
        )

        score = validate_real_score(
            asset,
            raw_score,
        )

        scores[asset] = score

        print(
            f"{asset:<10}"
            f"{direction:<12}"
            f"{score:>12.6f}"
            f"{'PASS':>10}"
        )

    # =========================================================================
    # FINAL M2 CONTRACT
    # =========================================================================

    if not scores:

        fail(
            "BLOCKER:NO_REAL_SCORE"
        )

    print()
    line("=")

    print(
        "M2 RESULT"
    )

    line("=")

    print(
        f"REAL SIGNALS CONSUMED : {len(real_signals)}"
    )

    print(
        f"REAL SCORES PRODUCED  : {len(scores)}"
    )

    print(
        "SIGNAL SOURCE         : signal_engine.build_all()"
    )

    print(
        "SCORER                : signal_scorer.calculate_score()"
    )

    print(
        "SYNTHETIC DATA        : NONE"
    )

    print(
        "DATABASE WRITE        : NONE"
    )

    print(
        "DECISION              : NOT USED"
    )

    print(
        "PREDICTION            : NOT USED"
    )

    print(
        "EXECUTION             : NOT USED"
    )

    print(
        "REAL VALID SCORE      : PASS"
    )

    line("=")

    print()
    print(
        "M2 STATUS : REAL VALID SCORE"
    )

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )