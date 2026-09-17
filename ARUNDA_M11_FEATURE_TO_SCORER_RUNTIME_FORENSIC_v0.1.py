# =================================================================================================
# ARUNDA TRADER — M11 FEATURE → SCORER REAL RUNTIME TRACE v0.1
# =================================================================================================
# MODE        : READ ONLY
# DB ACCESS   : NONE
# WRITES      : NONE
# SYNTHETIC   : FORBIDDEN
#
# PURPOSE:
#   Verify REAL runtime execution of:
#
#       feature producer
#            ↓
#       signal_scorer.load_features()
#            ↓
#       signal_scorer.load_scores()
#            ↓
#       signal_scorer.run()
#
# IMPORTANT:
#   This script does NOT modify production source.
#   It imports the real signal_scorer module and invokes only the
#   existing functions with REAL feature objects supplied by the
#   real feature-loading boundary.
# =================================================================================================

from __future__ import annotations

import inspect
import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


print("=" * 100)
print("ARUNDA TRADER — M11 FEATURE → SCORER REAL RUNTIME TRACE v0.1")
print("=" * 100)
print(f"PROJECT ROOT : {PROJECT_ROOT}")
print("MODE         : READ ONLY")
print("DB ACCESS    : NONE")
print("WRITES       : NONE")
print("SYNTHETIC    : FORBIDDEN")
print("=" * 100)


# -------------------------------------------------------------------------------------------------
# 1 — IMPORT REAL PRODUCTION MODULE
# -------------------------------------------------------------------------------------------------

print("\n[1] IMPORT REAL signal_scorer")
print("-" * 100)

try:
    import signal_scorer

    print("IMPORT STATUS : PASS")
    print("MODULE        :", signal_scorer.__file__)

except Exception as exc:
    print("IMPORT STATUS : FAIL")
    print("ERROR         :", repr(exc))
    traceback.print_exc()
    raise SystemExit(1)


# -------------------------------------------------------------------------------------------------
# 2 — FUNCTION EXISTENCE / SIGNATURE
# -------------------------------------------------------------------------------------------------

print("\n[2] PRODUCTION FUNCTION BOUNDARY")
print("-" * 100)

targets = [
    "load_features",
    "load_scores",
    "run",
]

for name in targets:
    obj = getattr(signal_scorer, name, None)

    print(f"\nFUNCTION : {name}")

    if obj is None:
        print("STATUS   : MISSING")
        continue

    print("STATUS   : EXISTS")

    try:
        print("SIGNATURE:", inspect.signature(obj))
    except Exception:
        print("SIGNATURE: <unavailable>")


# -------------------------------------------------------------------------------------------------
# 3 — DISCOVER REAL FEATURE INPUT BOUNDARY
# -------------------------------------------------------------------------------------------------

print("\n[3] REAL FEATURE INPUT DISCOVERY")
print("-" * 100)

feature_loader = getattr(signal_scorer, "load_features", None)

if feature_loader is None:
    print("RESULT : BLOCKED — load_features does not exist")
    raise SystemExit(1)


print("load_features signature:")
print(inspect.signature(feature_loader))


# -------------------------------------------------------------------------------------------------
# 4 — DO NOT SYNTHESIZE FEATURES
# -------------------------------------------------------------------------------------------------
#
# We deliberately do NOT create:
#
#   bars_by_asset = {}
#   indicators_by_asset = {}
#   structures_by_asset = {}
#
# because that would violate the forensic rule.
#
# Instead, inspect the production function source to identify whether
# its caller-side contract requires externally supplied REAL mappings.
# -------------------------------------------------------------------------------------------------

print("\n[4] FEATURE CONTRACT CHECK")
print("-" * 100)

try:
    source = inspect.getsource(feature_loader)

    print("SOURCE RETRIEVAL : PASS")

    feature_names = [
        "bars_by_asset",
        "indicators_by_asset",
        "structures_by_asset",
    ]

    for name in feature_names:
        print(
            f"{name:25s}: "
            + ("FOUND" if name in source else "NOT FOUND")
        )

except Exception as exc:
    print("SOURCE RETRIEVAL : FAIL")
    print("ERROR             :", repr(exc))
    source = ""


# -------------------------------------------------------------------------------------------------
# 5 — TRACE INTERNAL EXECUTION WITHOUT MODIFYING SOURCE
# -------------------------------------------------------------------------------------------------
#
# Python's sys.settrace() allows us to observe actual function execution.
#
# No monkey patch.
# No source rewrite.
# No DB write.
# No synthetic data.
#
# We trace only the target module.
# -------------------------------------------------------------------------------------------------

print("\n[5] RUNTIME TRACE PREPARATION")
print("-" * 100)

TARGET_FILE = str(Path(signal_scorer.__file__).resolve())


events = []


def tracer(frame, event, arg):
    if event != "call":
        return tracer

    filename = str(Path(frame.f_code.co_filename).resolve())

    if filename != TARGET_FILE:
        return tracer

    function_name = frame.f_code.co_name
    line_number = frame.f_lineno

    if function_name in {
        "load_features",
        "load_scores",
        "run",
        "load_feature_snapshot",
        "build_feature_snapshot",
        "build_features",
    }:
        events.append(
            {
                "function": function_name,
                "line": line_number,
            }
        )

        print(
            f"RUNTIME CALL  : {function_name}() "
            f"at {Path(filename).name}:{line_number}"
        )

    return tracer


# -------------------------------------------------------------------------------------------------
# 6 — REAL ENTRYPOINT
# -------------------------------------------------------------------------------------------------
#
# First attempt:
#
#     signal_scorer.run()
#
# is intentionally NOT performed blindly because the signature may require
# real externally produced objects.
#
# We inspect its signature and determine whether the production run boundary
# can be entered without fabricating inputs.
# -------------------------------------------------------------------------------------------------

print("\n[6] REAL signal_scorer.run() ENTRYPOINT")
print("-" * 100)

run_fn = getattr(signal_scorer, "run", None)

if run_fn is None:
    print("RUN STATUS : MISSING")
    raise SystemExit(1)


run_signature = inspect.signature(run_fn)

print("SIGNATURE :", run_signature)


required_parameters = []

for parameter in run_signature.parameters.values():

    if (
        parameter.default is inspect.Parameter.empty
        and parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ):
        required_parameters.append(parameter.name)


print("REQUIRED PARAMETERS :", required_parameters)


# -------------------------------------------------------------------------------------------------
# 7 — SAFE RUNTIME DECISION
# -------------------------------------------------------------------------------------------------

if required_parameters:
    print("\nRUN STATUS : NOT INVOKED")
    print(
        "REASON     : run() requires externally supplied parameters."
    )
    print(
        "RULE       : No synthetic feature objects will be fabricated."
    )

else:

    print("\nRUN STATUS : INVOKING REAL run()")
    print("-" * 100)

    old_trace = sys.gettrace()

    try:
        sys.settrace(tracer)

        result = run_fn()

        print("\nREAL RUN RESULT")
        print("-" * 100)
        print("STATUS :", "RETURNED")
        print("TYPE   :", type(result).__name__)

    except Exception as exc:

        print("\nREAL RUN RESULT")
        print("-" * 100)
        print("STATUS : EXCEPTION")
        print("TYPE   :", type(exc).__name__)
        print("ERROR  :", repr(exc))

        traceback.print_exc()

    finally:
        sys.settrace(old_trace)


# -------------------------------------------------------------------------------------------------
# 8 — RUNTIME LINEAGE RESULT
# -------------------------------------------------------------------------------------------------

print("\n[8] RUNTIME LINEAGE")
print("=" * 100)

observed = [event["function"] for event in events]

for index, name in enumerate(observed, 1):
    print(f"{index:02d}. {name}()")


required_chain = [
    "load_features",
    "load_scores",
    "run",
]


print("\nCHAIN CHECK")
print("-" * 100)

for name in required_chain:
    count = observed.count(name)
    print(f"{name:20s} calls = {count}")


# -------------------------------------------------------------------------------------------------
# 9 — FINAL VERDICT
# -------------------------------------------------------------------------------------------------

print("\n" + "=" * 100)
print("M11 FORENSIC VERDICT")
print("=" * 100)

load_features_count = observed.count("load_features")
load_scores_count = observed.count("load_scores")
run_count = observed.count("run")


if run_count > 0 and load_features_count > 0 and load_scores_count > 0:

    print("RESULT : REAL FEATURE → SCORER RUNTIME CHAIN OBSERVED")
    print()
    print("CONFIRMED:")
    print("  feature input")
    print("      ↓")
    print("  signal_scorer.load_features()")
    print("      ↓")
    print("  signal_scorer.load_scores()")
    print("      ↓")
    print("  signal_scorer.run()")

elif load_features_count > 0 or load_scores_count > 0:

    print("RESULT : PARTIAL RUNTIME OBSERVATION")
    print()
    print("The scorer module was entered at runtime, but the complete")
    print("feature → scorer → run chain was NOT observed.")

else:

    print("RESULT : RUNTIME BRIDGE NOT OBSERVED")
    print()
    print("Static linkage exists, but this execution did not establish")
    print("the real production runtime chain.")


print("\nRUNTIME COUNTS")
print("-" * 100)
print(f"load_features() : {load_features_count}")
print(f"load_scores()   : {load_scores_count}")
print(f"run()           : {run_count}")

print("\nNO PRODUCTION MODIFICATION")
print("NO DB WRITE")
print("NO SYNTHETIC DATA")
print("=" * 100)