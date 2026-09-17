
"""
====================================================================================================
ARUNDA TRADER — M2
REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.1
====================================================================================================

PURPOSE
-------
Execute the REAL production signal path:

    signal_engine.build_all()
            |
            v
    REAL SIGNAL
            |
            v
    signal_scorer.calculate_score()
            |
            v
    REAL VALID SCORE

ARCHITECTURAL RULES
-------------------
- signal_engine.build_all() is the ONLY real signal source.
- signal_scorer.calculate_score() is the ONLY production scorer.
- No synthetic signal.
- No synthetic feature.
- No synthetic structural state.
- No synthetic regime data.
- No database write.
- No decision engine.
- No prediction.
- No execution.
- No heuristic scorer discovery.
- No candidate ranking.
- Helper functions such as print_scores() and
  validate_score_snapshot() are NOT scorers.

CURRENT M2 BLOCKER REPAIR
-------------------------
Previous runtime discovery incorrectly treated:

    print_scores
    validate_score_snapshot

as possible production scorers.

The production scorer contract is explicitly resolved as:

    signal_scorer.calculate_score(
        direction,
        feature_record,
        structural_state,
        regime_data
    )

This file resolves that function deterministically.
"""


from __future__ import annotations

import importlib
import inspect
import math
import os
import sys
from typing import Any, Mapping


# ==================================================================================================
# CONSTANTS
# ==================================================================================================

ENGINE_VERSION = "M2_REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.1"

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SIGNAL_ENGINE_MODULE = "signal_engine"

SCORER_MODULE = "signal_scorer"

SCORER_FUNCTION = "calculate_score"

REQUIRED_SCORER_PARAMETERS = (
    "direction",
    "feature_record",
    "structural_state",
    "regime_data",
)

FORBIDDEN_SCORER_NAMES = {
    "print_scores",
    "validate_score_snapshot",
    "load_scores",
}


# ==================================================================================================
# TERMINAL HELPERS
# ==================================================================================================

def line(char="=", length=100):
    print(char * length)


def section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def safe_float(value):
    try:
        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (
        TypeError,
        ValueError,
    ):
        return None


# ==================================================================================================
# MODULE LOADING
# ==================================================================================================

def load_signal_engine():

    try:

        module = importlib.import_module(
            SIGNAL_ENGINE_MODULE
        )

    except Exception as exc:

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_ENGINE_IMPORT_FAILED:"
            f"{type(exc).__name__}:{exc}"
        ) from exc

    if not hasattr(
        module,
        "build_all",
    ):

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_SOURCE_NOT_FOUND:"
            "signal_engine.build_all"
        )

    build_all = getattr(
        module,
        "build_all",
    )

    if not callable(build_all):

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_SOURCE_NOT_CALLABLE:"
            "signal_engine.build_all"
        )

    return module


# ==================================================================================================
# REAL SIGNAL SOURCE
# ==================================================================================================

def load_real_signal_snapshot():

    signal_engine = load_signal_engine()

    snapshot = signal_engine.build_all()

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_SOURCE_INVALID_OUTPUT:"
            "signal_engine.build_all() must return dict"
        )

    return snapshot


# ==================================================================================================
# REAL SIGNAL EXTRACTION
# ==================================================================================================

def extract_signal_records(
    snapshot,
):

    records = []

    for asset, payload in snapshot.items():

        if not isinstance(
            payload,
            Mapping,
        ):
            continue

        signal = payload.get(
            "signal"
        )

        if signal is None:
            continue

        records.append(
            (
                asset,
                payload,
                signal,
            )
        )

    return records


def extract_signal_value(
    signal,
    name,
    default=None,
):

    if isinstance(
        signal,
        Mapping,
    ):

        return signal.get(
            name,
            default,
        )

    return getattr(
        signal,
        name,
        default,
    )


# ==================================================================================================
# PRODUCTION SCORER RESOLVER
# ==================================================================================================

def resolve_production_scorer():

    try:

        module = importlib.import_module(
            SCORER_MODULE
        )

    except Exception as exc:

        raise RuntimeError(
            "BLOCKER:PRODUCTION_SCORER_IMPORT_FAILED:"
            f"{type(exc).__name__}:{exc}"
        ) from exc

    scorer = getattr(
        module,
        SCORER_FUNCTION,
        None,
    )

    if scorer is None:

        raise RuntimeError(
            "BLOCKER:PRODUCTION_SCORER_NOT_FOUND:"
            f"{SCORER_MODULE}.{SCORER_FUNCTION}"
        )

    if not callable(
        scorer
    ):

        raise RuntimeError(
            "BLOCKER:PRODUCTION_SCORER_NOT_CALLABLE:"
            f"{SCORER_MODULE}.{SCORER_FUNCTION}"
        )

    if SCORER_FUNCTION in FORBIDDEN_SCORER_NAMES:

        raise RuntimeError(
            "BLOCKER:INVALID_SCORER_RESOLUTION:"
            f"{SCORER_FUNCTION}"
        )

    signature = inspect.signature(
        scorer
    )

    parameter_names = [
        parameter.name
        for parameter in signature.parameters.values()
    ]

    missing = [
        name
        for name in REQUIRED_SCORER_PARAMETERS
        if name not in parameter_names
    ]

    if missing:

        raise RuntimeError(
            "BLOCKER:PRODUCTION_SCORER_CONTRACT_MISMATCH:"
            f"missing={missing}:"
            f"signature={signature}"
        )

    return {
        "module": module,
        "module_name": SCORER_MODULE,
        "function_name": SCORER_FUNCTION,
        "callable": scorer,
        "signature": signature,
        "parameters": parameter_names,
    }


# ==================================================================================================
# SCORER INPUT RESOLUTION
# ==================================================================================================

def resolve_signal_direction(
    signal,
):

    direction = extract_signal_value(
        signal,
        "direction",
    )

    if direction is None:

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_DIRECTION_MISSING"
        )

    if not isinstance(
        direction,
        str,
    ):

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_DIRECTION_INVALID:"
            f"{type(direction).__name__}"
        )

    direction = direction.strip().upper()

    if direction not in {
        "LONG",
        "SHORT",
        "NONE",
        "NEUTRAL",
    }:

        raise RuntimeError(
            "BLOCKER:REAL_SIGNAL_DIRECTION_INVALID:"
            f"{direction}"
        )

    return direction


def resolve_mapping(
    signal,
    payload,
    names,
    label,
):

    candidates = []

    for name in names:

        value = extract_signal_value(
            signal,
            name,
        )

        if value is not None:
            candidates.append(
                value
            )

    if isinstance(
        signal,
        Mapping,
    ):

        for name in names:

            value = signal.get(
                name
            )

            if value is not None:
                candidates.append(
                    value
                )

    if isinstance(
        payload,
        Mapping,
    ):

        for name in names:

            value = payload.get(
                name
            )

            if value is not None:
                candidates.append(
                    value
                )

    for value in candidates:

        if isinstance(
            value,
            Mapping,
        ):

            return value

    raise RuntimeError(
        f"BLOCKER:REAL_SIGNAL_{label.upper()}_MISSING"
    )


# ==================================================================================================
# PRODUCTION FEATURE / STRUCTURE / REGIME RESOLUTION
# ==================================================================================================

def resolve_feature_record(
    asset,
    signal,
    payload,
):

    return resolve_mapping(
        signal,
        payload,
        (
            "feature_record",
            "features",
            "feature_snapshot",
            "feature_state",
        ),
        "feature_record",
    )


def resolve_structural_state(
    asset,
    signal,
    payload,
):

    return resolve_mapping(
        signal,
        payload,
        (
            "structural_state",
            "structure",
            "market_structure",
            "structure_state",
        ),
        "structural_state",
    )


def resolve_regime_data(
    asset,
    signal,
    payload,
):

    return resolve_mapping(
        signal,
        payload,
        (
            "regime_data",
            "regime",
            "market_regime",
            "regime_state",
        ),
        "regime_data",
    )


# ==================================================================================================
# IMPORTANT:
# Do NOT manufacture missing scorer inputs.
#
# The production scorer requires four inputs.
# If the REAL signal snapshot does not carry the required
# production objects, this is a real integration blocker.
# ==================================================================================================

def build_real_scorer_inputs(
    asset,
    signal,
    payload,
):

    direction = resolve_signal_direction(
        signal
    )

    feature_record = resolve_feature_record(
        asset,
        signal,
        payload,
    )

    structural_state = resolve_structural_state(
        asset,
        signal,
        payload,
    )

    regime_data = resolve_regime_data(
        asset,
        signal,
        payload,
    )

    return {
        "direction": direction,
        "feature_record": feature_record,
        "structural_state": structural_state,
        "regime_data": regime_data,
    }


# ==================================================================================================
# REAL SCORE EXECUTION
# ==================================================================================================

def execute_real_score(
    scorer,
    inputs,
):

    try:

        score = scorer(
            inputs["direction"],
            inputs["feature_record"],
            inputs["structural_state"],
            inputs["regime_data"],
        )

    except Exception as exc:

        raise RuntimeError(
            "BLOCKER:PRODUCTION_SCORER_RUNTIME_FAILED:"
            f"{type(exc).__name__}:{exc}"
        ) from exc

    numeric_score = safe_float(
        score
    )

    if numeric_score is None:

        raise RuntimeError(
            "BLOCKER:PRODUCTION_SCORER_INVALID_SCORE:"
            f"{score!r}"
        )

    return numeric_score


# ==================================================================================================
# SCORE VALIDATION
# ==================================================================================================

def validate_real_score(
    score,
):

    if not math.isfinite(
        score
    ):

        raise RuntimeError(
            "BLOCKER:REAL_SCORE_NON_FINITE"
        )

    if score < 0.0 or score > 100.0:

        raise RuntimeError(
            "BLOCKER:REAL_SCORE_OUT_OF_RANGE:"
            f"{score}"
        )

    return True


# ==================================================================================================
# SELF TEST
# ==================================================================================================

def self_test():

    print()
    print("Running self-test...")

    # --------------------------------------------------------------------------
    # Resolver contract
    # --------------------------------------------------------------------------

    resolved = resolve_production_scorer()

    assert (
        resolved["module_name"]
        == "signal_scorer"
    )

    assert (
        resolved["function_name"]
        == "calculate_score"
    )

    assert callable(
        resolved["callable"]
    )

    # --------------------------------------------------------------------------
    # Signature contract
    # --------------------------------------------------------------------------

    parameter_names = set(
        resolved["parameters"]
    )

    for parameter in REQUIRED_SCORER_PARAMETERS:

        assert parameter in parameter_names

    # --------------------------------------------------------------------------
    # Forbidden helper protection
    # --------------------------------------------------------------------------

    assert (
        "print_scores"
        != SCORER_FUNCTION
    )

    assert (
        "validate_score_snapshot"
        != SCORER_FUNCTION
    )

    print(
        "SELF TEST : PASS"
    )

    return True


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    started = __import__(
        "time"
    ).perf_counter()

    line()

    print(
        "ARUNDA TRADER — M2"
    )

    print(
        "REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.1"
    )

    line()

    print(
        f"PROJECT              : {PROJECT_DIR}"
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

    line()

    try:

        # ==============================================================================
        # SELF TEST
        # ==============================================================================

        self_test()

        # ==============================================================================
        # RESOLVE REAL PRODUCTION SCORER
        # ==============================================================================

        section(
            "PRODUCTION SCORER RESOLUTION"
        )

        resolved = resolve_production_scorer()

        print(
            f"Module       : {resolved['module_name']}"
        )

        print(
            f"Function     : {resolved['function_name']}"
        )

        print(
            f"Signature    : {resolved['signature']}"
        )

        print(
            "Resolution   : DETERMINISTIC"
        )

        print(
            "Status       : PRODUCTION SCORER RESOLVED"
        )

        # ==============================================================================
        # LOAD REAL SIGNAL
        # ==============================================================================

        section(
            "REAL SIGNAL SOURCE"
        )

        snapshot = load_real_signal_snapshot()

        records = extract_signal_records(
            snapshot
        )

        print(
            "Source       : signal_engine.build_all()"
        )

        print(
            f"Assets       : {len(snapshot)}"
        )

        print(
            f"Signal records: {len(records)}"
        )

        if not records:

            raise RuntimeError(
                "BLOCKER:NO_REAL_SIGNAL_RECORDS"
            )

        # ==============================================================================
        # REAL SIGNAL INVENTORY
        # ==============================================================================

        print()
        print(
            "REAL SIGNALS"
        )

        print("-" * 100)

        for asset, payload, signal in records:

            direction = extract_signal_value(
                signal,
                "direction",
                "UNKNOWN",
            )

            state = extract_signal_value(
                signal,
                "state",
                extract_signal_value(
                    signal,
                    "signal_state",
                    "UNKNOWN",
                ),
            )

            eligible = extract_signal_value(
                signal,
                "eligible",
                None,
            )

            print(
                f"{asset:<10}"
                f"STATE={str(state):<12}"
                f"DIRECTION={str(direction):<8}"
                f"ELIGIBLE={eligible}"
            )

        # ==============================================================================
        # SELECT REAL ELIGIBLE SIGNAL
        # ==============================================================================

        eligible_records = []

        for asset, payload, signal in records:

            eligible = extract_signal_value(
                signal,
                "eligible",
                None,
            )

            if eligible is True:

                eligible_records.append(
                    (
                        asset,
                        payload,
                        signal,
                    )
                )

        if not eligible_records:

            raise RuntimeError(
                "BLOCKER:NO_REAL_ELIGIBLE_SIGNAL"
            )

        # ==============================================================================
        # M2 CONTRACT:
        # We need an ACTUAL real signal to enter the scorer.
        #
        # Do not create a test signal.
        # Do not fabricate feature/structure/regime dictionaries.
        #
        # We use the first REAL eligible signal returned by build_all().
        # ==============================================================================

        asset, payload, signal = eligible_records[0]

        section(
            "REAL SIGNAL SELECTED FOR SCORING"
        )

        print(
            f"Asset        : {asset}"
        )

        print(
            f"Direction    : {resolve_signal_direction(signal)}"
        )

        print(
            "Source       : signal_engine.build_all()[asset]['signal']"
        )

        # ==============================================================================
        # RESOLVE REAL SCORER INPUTS
        # ==============================================================================

        section(
            "REAL SCORER INPUT RESOLUTION"
        )

        scorer_inputs = build_real_scorer_inputs(
            asset,
            signal,
            payload,
        )

        print(
            f"Direction        : {scorer_inputs['direction']}"
        )

        print(
            "Feature Record   : REAL"
        )

        print(
            "Structural State : REAL"
        )

        print(
            "Regime Data      : REAL"
        )

        print(
            "Synthetic Data   : NONE"
        )

        # ==============================================================================
        # EXECUTE PRODUCTION SCORER
        # ==============================================================================

        section(
            "PRODUCTION SCORER EXECUTION"
        )

        score = execute_real_score(
            resolved["callable"],
            scorer_inputs,
        )

        validate_real_score(
            score
        )

        print(
            f"Asset        : {asset}"
        )

        print(
            f"Direction    : {scorer_inputs['direction']}"
        )

        print(
            f"REAL SCORE   : {score:.6f}"
        )

        print(
            "Score Valid  : YES"
        )

        # ==============================================================================
        # M2 SUCCESS
        # ==============================================================================

        elapsed = (
            __import__(
                "time"
            ).perf_counter()
            - started
        )

        line()

        print(
            "M2 STATUS : REAL VALID SCORE"
        )

        print(
            f"Asset      : {asset}"
        )

        print(
            f"Direction  : {scorer_inputs['direction']}"
        )

        print(
            f"Score      : {score:.6f}"
        )

        print(
            "Source     : signal_engine.build_all()"
        )

        print(
            "Scorer     : signal_scorer.calculate_score()"
        )

        print(
            "Synthetic  : NONE"
        )

        print(
            "DB WRITE   : NONE"
        )

        print(
            "Decision   : NOT USED"
        )

        print(
            "Execution  : NOT USED"
        )

        print(
            f"Runtime    : {elapsed:.4f} sec"
        )

        line()

        return 0

    except KeyboardInterrupt:

        print()

        line(
            "-"
        )

        print(
            "M2 STATUS : INTERRUPTED"
        )

        line(
            "-"
        )

        return 130

    except Exception as exc:

        print()

        line()

        print(
            "M2 STATUS : BLOCKED"
        )

        print(
            f"ERROR     : {type(exc).__name__}: {exc}"
        )

        line()

        return 1


# ==================================================================================================
# ENTRY POINT
# ==================================================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )