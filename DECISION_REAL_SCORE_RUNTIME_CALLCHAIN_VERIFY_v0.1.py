# -*- coding: utf-8 -*-

"""
ARUNDA DECISION REAL SCORE RUNTIME CALL-CHAIN VERIFY v0.1

MODE        : READ ONLY
DB WRITE    : NONE
SOURCE EDIT : NONE
PURPOSE     : Runtime verification of REAL SCORE -> DECISION call chain

IMPORTANT:
- This script does NOT modify production source files.
- This script does NOT write to the database.
- This script does NOT replace production functions permanently.
- Runtime wrappers are installed only in this process.
"""

from __future__ import annotations

import os
import sys
import inspect
import traceback
from pathlib import Path


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TARGET_MODULES = [
    "signal_scorer",
    "decision_engine",
    "risk_engine",
    "execution_engine",
]


# =============================================================================
# HEADER
# =============================================================================

print("=" * 90)
print("ARUNDA DECISION REAL SCORE RUNTIME CALL-CHAIN VERIFY v0.1")
print("=" * 90)
print(f"PROJECT ROOT : {PROJECT_ROOT}")
print("MODE         : READ ONLY")
print("DB WRITE     : NONE")
print("SOURCE EDIT  : NONE")
print("PIPELINE RUN : CONTROLLED RUNTIME TRACE")
print()


# =============================================================================
# PROJECT CHECK
# =============================================================================

print("=" * 90)
print("PROJECT FILE CHECK")
print("=" * 90)

required_files = [
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "execution_engine.py",
    "feature_contract.py",
    "feature_snapshot_reader.py",
]

missing = []

for filename in required_files:
    path = PROJECT_ROOT / filename

    if path.exists():
        print(f"[OK]      {filename}")
    else:
        print(f"[MISSING] {filename}")
        missing.append(filename)

print()

if missing:
    print("FATAL : REQUIRED FILES ARE MISSING")
    sys.exit(1)


# =============================================================================
# IMPORT
# =============================================================================

print("=" * 90)
print("MODULE IMPORT")
print("=" * 90)

try:
    import signal_scorer
    import decision_engine
    import risk_engine
    import execution_engine

    print("[OK] signal_scorer imported")
    print("[OK] decision_engine imported")
    print("[OK] risk_engine imported")
    print("[OK] execution_engine imported")

except Exception as exc:
    print()
    print("IMPORT FAILURE")
    print(type(exc).__name__, str(exc))
    traceback.print_exc()
    sys.exit(1)

print()


# =============================================================================
# FUNCTION EXISTENCE
# =============================================================================

print("=" * 90)
print("RUNTIME FUNCTION AVAILABILITY")
print("=" * 90)

checks = [
    ("signal_scorer", signal_scorer, "load_scores"),
    ("signal_scorer", signal_scorer, "run"),
    ("decision_engine", decision_engine, "load_scores"),
    ("decision_engine", decision_engine, "build_decision_snapshot"),
    ("decision_engine", decision_engine, "main"),
    ("risk_engine", risk_engine, "load_decisions"),
    ("execution_engine", execution_engine, "load_decisions"),
]

for module_name, module, function_name in checks:
    obj = getattr(module, function_name, None)

    if callable(obj):
        try:
            signature = inspect.signature(obj)
        except Exception:
            signature = "<signature unavailable>"

        print(
            f"{module_name}.py::{function_name}{signature}"
        )
    else:
        print(
            f"[MISSING] {module_name}.py::{function_name}"
        )

print()


# =============================================================================
# ORIGINAL FUNCTION REFERENCES
# =============================================================================

original_signal_load_scores = getattr(
    signal_scorer,
    "load_scores",
    None,
)

original_decision_load_scores = getattr(
    decision_engine,
    "load_scores",
    None,
)

original_decision_build_snapshot = getattr(
    decision_engine,
    "build_decision_snapshot",
    None,
)


# =============================================================================
# RUNTIME TRACE STATE
# =============================================================================

TRACE = {
    "signal_scorer.load_scores": {
        "calls": 0,
        "zero_arg": 0,
        "argument_calls": 0,
        "real_input_calls": 0,
        "returns": 0,
    },

    "decision_engine.load_scores": {
        "calls": 0,
        "zero_arg": 0,
        "returns": 0,
    },

    "decision_engine.build_decision_snapshot": {
        "calls": 0,
        "score_objects": 0,
        "returns": 0,
    },
}


# =============================================================================
# HELPERS
# =============================================================================

def describe_mapping(value):
    if isinstance(value, dict):
        keys = list(value.keys())

        return {
            "type": "dict",
            "len": len(value),
            "keys_sample": keys[:5],
        }

    return {
        "type": type(value).__name__,
        "len": None,
        "keys_sample": None,
    }


def has_real_input_shape(args, kwargs):
    """
    Detect whether runtime arguments structurally correspond to:

        bars_by_asset
        indicators_by_asset
        structures_by_asset

    This is deliberately structural.
    It does NOT manufacture data.
    """

    if len(args) < 3:
        return False

    first = args[0]
    second = args[1]
    third = args[2]

    return (
        isinstance(first, dict)
        and isinstance(second, dict)
        and isinstance(third, dict)
    )


# =============================================================================
# WRAPPER 1
# signal_scorer.load_scores
# =============================================================================

def traced_signal_load_scores(*args, **kwargs):

    TRACE["signal_scorer.load_scores"]["calls"] += 1

    caller = inspect.stack()[1]

    print()
    print("-" * 90)
    print("RUNTIME EVENT : signal_scorer.load_scores()")
    print("-" * 90)

    print(
        f"CALLER       : "
        f"{caller.function} "
        f"({Path(caller.filename).name}:{caller.lineno})"
    )

    print(f"ARGS COUNT   : {len(args)}")
    print(f"KWARGS       : {list(kwargs.keys())}")

    if len(args) == 0 and not kwargs:

        TRACE["signal_scorer.load_scores"]["zero_arg"] += 1

        print("BOUNDARY      : ZERO-ARG")
        print("REAL INPUTS   : NOT PROVIDED")

    else:

        TRACE["signal_scorer.load_scores"]["argument_calls"] += 1

        print("BOUNDARY      : ARGUMENT")

        if has_real_input_shape(args, kwargs):

            TRACE["signal_scorer.load_scores"]["real_input_calls"] += 1

            print("REAL INPUTS   : PRESENT")

            print(
                "bars_by_asset :",
                describe_mapping(args[0]),
            )

            print(
                "indicators    :",
                describe_mapping(args[1]),
            )

            print(
                "structures    :",
                describe_mapping(args[2]),
            )

        else:

            print("REAL INPUTS   : NOT PROVEN")
            print("ARGUMENT SHAPE:")
            print(
                [
                    type(x).__name__
                    for x in args
                ]
            )

    result = original_signal_load_scores(
        *args,
        **kwargs,
    )

    TRACE["signal_scorer.load_scores"]["returns"] += 1

    print()
    print("RETURN FROM signal_scorer.load_scores")
    print("RETURN TYPE   :", type(result).__name__)

    if isinstance(result, dict):
        print("SCORE COUNT   :", len(result))

        if result:
            print(
                "SCORE KEYS    :",
                list(result.keys())[:10],
            )

    return result


# =============================================================================
# WRAPPER 2
# decision_engine.load_scores
# =============================================================================

def traced_decision_load_scores(*args, **kwargs):

    TRACE["decision_engine.load_scores"]["calls"] += 1

    caller = inspect.stack()[1]

    print()
    print("-" * 90)
    print("RUNTIME EVENT : decision_engine.load_scores()")
    print("-" * 90)

    print(
        f"CALLER       : "
        f"{caller.function} "
        f"({Path(caller.filename).name}:{caller.lineno})"
    )

    print(f"ARGS COUNT   : {len(args)}")
    print(f"KWARGS       : {list(kwargs.keys())}")

    if len(args) == 0 and not kwargs:
        TRACE["decision_engine.load_scores"]["zero_arg"] += 1

        print("BOUNDARY      : ZERO-ARG")
        print("VERDICT       : ZERO-ARG DECISION SCORE LOADER EXECUTED")

    else:
        print("BOUNDARY      : ARGUMENT")

    result = original_decision_load_scores(
        *args,
        **kwargs,
    )

    TRACE["decision_engine.load_scores"]["returns"] += 1

    print()
    print("RETURN FROM decision_engine.load_scores")
    print("RETURN TYPE   :", type(result).__name__)

    if isinstance(result, dict):
        print("SCORE COUNT   :", len(result))

        if result:
            print(
                "SCORE KEYS    :",
                list(result.keys())[:10],
            )

    return result


# =============================================================================
# WRAPPER 3
# decision_engine.build_decision_snapshot
# =============================================================================

def traced_build_decision_snapshot(signals, scores):

    TRACE[
        "decision_engine.build_decision_snapshot"
    ]["calls"] += 1

    print()
    print("-" * 90)
    print("RUNTIME EVENT : decision_engine.build_decision_snapshot()")
    print("-" * 90)

    print("SIGNALS TYPE  :", type(signals).__name__)
    print("SCORES TYPE   :", type(scores).__name__)

    if isinstance(scores, dict):

        TRACE[
            "decision_engine.build_decision_snapshot"
        ]["score_objects"] += 1

        print("SCORE OBJECT  : PRESENT")
        print("SCORE COUNT   :", len(scores))

        if scores:
            print(
                "SCORE KEYS    :",
                list(scores.keys())[:10],
            )

    else:
        print("SCORE OBJECT  : ABSENT")

    result = original_decision_build_snapshot(
        signals,
        scores,
    )

    TRACE[
        "decision_engine.build_decision_snapshot"
    ]["returns"] += 1

    print()
    print(
        "RETURN FROM decision_engine.build_decision_snapshot"
    )
    print("RETURN TYPE   :", type(result).__name__)

    if isinstance(result, dict):
        print("DECISION COUNT:", len(result))

    return result


# =============================================================================
# INSTALL TEMPORARY RUNTIME WRAPPERS
# =============================================================================

print("=" * 90)
print("INSTALLING TEMPORARY RUNTIME TRACE")
print("=" * 90)

signal_scorer.load_scores = traced_signal_load_scores
decision_engine.load_scores = traced_decision_load_scores
decision_engine.build_decision_snapshot = (
    traced_build_decision_snapshot
)

print("[OK] signal_scorer.load_scores")
print("[OK] decision_engine.load_scores")
print("[OK] decision_engine.build_decision_snapshot")
print()

# =============================================================================
# CONTROLLED RUNTIME TEST
# =============================================================================

print("=" * 90)
print("CONTROLLED RUNTIME CALL-CHAIN TEST")
print("=" * 90)

print()
print("IMPORTANT:")
print("This test invokes the existing decision-engine entrypoint.")
print("No source files are modified.")
print("No database writes are intentionally performed.")
print()

runtime_exception = None

try:

    if callable(getattr(decision_engine, "main", None)):

        print("EXECUTING : decision_engine.main()")
        print()

        result = decision_engine.main()

        print()
        print("decision_engine.main() RETURNED")
        print("RETURN TYPE :", type(result).__name__)

    else:

        print("decision_engine.main() NOT AVAILABLE")

except Exception as exc:

    runtime_exception = exc

    print()
    print("=" * 90)
    print("RUNTIME EXCEPTION")
    print("=" * 90)

    print("TYPE   :", type(exc).__name__)
    print("ERROR  :", str(exc))

    traceback.print_exc()

print()


# =============================================================================
# RESTORE ORIGINAL FUNCTIONS
# =============================================================================

print("=" * 90)
print("RESTORING ORIGINAL RUNTIME FUNCTIONS")
print("=" * 90)

signal_scorer.load_scores = original_signal_load_scores
decision_engine.load_scores = original_decision_load_scores
decision_engine.build_decision_snapshot = (
    original_decision_build_snapshot
)

print("[OK] Runtime wrappers removed")
print()


# =============================================================================
# FINAL TRACE REPORT
# =============================================================================

print("=" * 90)
print("FINAL RUNTIME TRACE REPORT")
print("=" * 90)

sc = TRACE["signal_scorer.load_scores"]

print()
print("SIGNAL SCORER load_scores")
print("-" * 90)
print("TOTAL CALLS       :", sc["calls"])
print("ZERO-ARG CALLS    :", sc["zero_arg"])
print("ARGUMENT CALLS    :", sc["argument_calls"])
print("REAL INPUT CALLS  :", sc["real_input_calls"])
print("RETURN COUNT      :", sc["returns"])


dc = TRACE["decision_engine.load_scores"]

print()
print("DECISION ENGINE load_scores")
print("-" * 90)
print("TOTAL CALLS       :", dc["calls"])
print("ZERO-ARG CALLS    :", dc["zero_arg"])
print("RETURN COUNT      :", dc["returns"])


bc = TRACE["decision_engine.build_decision_snapshot"]

print()
print("DECISION SNAPSHOT")
print("-" * 90)
print("TOTAL CALLS       :", bc["calls"])
print("SCORE OBJECTS     :", bc["score_objects"])
print("RETURN COUNT      :", bc["returns"])


# =============================================================================
# VERDICT
# =============================================================================

print()
print("=" * 90)
print("FORENSIC VERDICT")
print("=" * 90)

if sc["real_input_calls"] > 0:
    print("REAL INPUT → SCORE RUNTIME PATH : PROVEN")
else:
    print("REAL INPUT → SCORE RUNTIME PATH : NOT PROVEN")


if sc["zero_arg"] > 0:
    print("ZERO-ARG signal_scorer.load_scores: EXECUTED")
else:
    print("ZERO-ARG signal_scorer.load_scores: NOT EXECUTED")


if dc["zero_arg"] > 0:
    print("DECISION ZERO-ARG LOADER          : EXECUTED")
else:
    print("DECISION ZERO-ARG LOADER          : NOT EXECUTED")


if bc["score_objects"] > 0:
    print("REAL SCORE OBJECT → DECISION      : PROVEN")
else:
    print("REAL SCORE OBJECT → DECISION      : NOT PROVEN")


# =============================================================================
# FINAL STATE CLASSIFICATION
# =============================================================================

if (
    sc["real_input_calls"] > 0
    and
    bc["score_objects"] > 0
    and
    dc["zero_arg"] == 0
):

    final_status = "REAL SCORE RUNTIME BRIDGE VERIFIED"

elif (
    sc["real_input_calls"] > 0
    and
    bc["score_objects"] > 0
    and
    dc["zero_arg"] > 0
):

    final_status = (
        "REAL SCORE RUNTIME PATH EXISTS; "
        "ZERO-ARG DECISION PATH ALSO EXECUTES"
    )

elif (
    sc["real_input_calls"] == 0
    and
    dc["zero_arg"] > 0
):

    final_status = (
        "RUNTIME EXECUTES ZERO-ARG SCORE PATH; "
        "REAL SCORE BRIDGE NOT PROVEN"
    )

else:

    final_status = (
        "RUNTIME BRIDGE NOT PROVEN; "
        "FURTHER CALL-CHAIN TRACE REQUIRED"
    )


print()
print("FINAL STATUS :", final_status)

if runtime_exception is not None:
    print("RUNTIME TEST  : EXCEPTION OCCURRED")
else:
    print("RUNTIME TEST  : COMPLETED")

print()
print("=" * 90)
print("END OF FORENSIC TRACE")
print("=" * 90)
print("DATABASE WRITE : NONE")
print("SOURCE EDIT    : NONE")
print("=" * 90)