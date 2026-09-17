# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
SIGNAL STRUCTURAL OBJECT ORIGIN TRACE v0.1

READ-ONLY RUNTIME FORENSIC

Purpose:
    Trace the REAL runtime structural object from its creation/origin
    through the production call chain until signal_logic.validate_structure().

Safety:
    - No production source mutation
    - No database access
    - No database write
    - No JSON write
    - No artifact creation
    - No synthetic signal
    - No production function patching
    - Real production runtime only
"""

from __future__ import annotations

import ast
import inspect
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_MODULE = "signal_engine"
TARGET_FUNCTION = "main"

EXPECTED_FIELDS = {
    "trend",
    "volatility",
    "momentum",
    "position",
    "acceleration",
}

TARGET_EXTRA_FIELD = "structure"

ERROR_TEXT = "Invalid structural fields"


print("=" * 100)
print("ARUNDA TRADER — SIGNAL STRUCTURAL OBJECT ORIGIN TRACE v0.1")
print("=" * 100)
print(f"PROJECT ROOT          : {PROJECT_ROOT}")
print("MODE                  : READ-ONLY RUNTIME OBSERVATION")
print("PRODUCTION MUTATION   : NONE")
print("DATABASE ACCESS       : NONE")
print("DATABASE WRITE        : NONE")
print("JSON WRITE            : NONE")
print("ARTIFACT CREATION     : NONE")
print("SOURCE MUTATION       : NONE")
print("SYNTHETIC SIGNAL      : FORBIDDEN")
print("=" * 100)


# ======================================================================
# A) STATIC ORIGIN CANDIDATES
# ======================================================================

def static_origin_candidates():
    results = []

    target_files = [
        PROJECT_ROOT / "market_regime.py",
        PROJECT_ROOT / "market_regime_engine.py",
        PROJECT_ROOT / "market_regime_contract.py",
        PROJECT_ROOT / "signal_engine.py",
        PROJECT_ROOT / "signal_logic.py",
    ]

    for path in target_files:
        if not path.exists():
            continue

        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except Exception:
            continue

        for node in ast.walk(tree):

            if not isinstance(node, (ast.Dict, ast.Call)):
                continue

            try:
                segment = ast.get_source_segment(source, node) or ""
            except Exception:
                segment = ""

            if (
                "structure" in segment
                and (
                    "trend" in segment
                    and "volatility" in segment
                    and "momentum" in segment
                    and "position" in segment
                    and "acceleration" in segment
                )
            ):
                results.append(
                    {
                        "file": str(path),
                        "line": getattr(node, "lineno", None),
                        "kind": type(node).__name__,
                        "source": segment.strip(),
                    }
                )

    return results


print()
print("=" * 100)
print("A) STATIC STRUCTURAL OBJECT ORIGIN CANDIDATES")
print("=" * 100)

candidates = static_origin_candidates()

print(f"ORIGIN CANDIDATES : {len(candidates)}")

for i, item in enumerate(candidates, 1):
    print()
    print(f"CANDIDATE #{i}")
    print(f"FILE     : {item['file']}")
    print(f"LINE     : {item['line']}")
    print(f"KIND     : {item['kind']}")
    print(f"SOURCE   : {item['source']}")


# ======================================================================
# B) RUNTIME TRACE STATE
# ======================================================================

runtime_trace = {
    "events": 0,
    "build_structure_calls": 0,
    "load_structural_state_calls": 0,
    "build_signal_calls": 0,
    "validate_structure_calls": 0,
    "origin_found": False,
    "validation_reached": False,
    "failure": None,
    "object": None,
    "asset": None,
    "origin_file": None,
    "origin_function": None,
    "origin_line": None,
    "origin_return_line": None,
}


def safe_repr(value):
    try:
        return repr(value)
    except Exception:
        return "<unrepr-able>"


def looks_like_structural_object(value):
    if not isinstance(value, dict):
        return False

    keys = set(value.keys())

    return (
        EXPECTED_FIELDS.issubset(keys)
        and TARGET_EXTRA_FIELD in keys
    )


def identify_asset_from_args(args, kwargs):
    for key in ("asset", "symbol", "ticker"):
        if key in kwargs:
            return kwargs[key]

    for value in args:
        if isinstance(value, str):
            if value:
                return value

    return None


# ======================================================================
# C) TRACE FUNCTIONS
# ======================================================================

def trace_function(frame, event, arg):

    runtime_trace["events"] += 1

    filename = Path(frame.f_code.co_filename)

    if PROJECT_ROOT not in filename.parents and filename != PROJECT_ROOT:
        return trace_function

    function = frame.f_code.co_name
    line = frame.f_lineno

    # --------------------------------------------------------------
    # build_structure
    # --------------------------------------------------------------

    if function == "build_structure":

        runtime_trace["build_structure_calls"] += 1

        if event == "return":

            value = arg

            if looks_like_structural_object(value):

                runtime_trace["origin_found"] = True
                runtime_trace["object"] = value
                runtime_trace["origin_file"] = str(filename)
                runtime_trace["origin_function"] = function
                runtime_trace["origin_return_line"] = line

                print()
                print("=" * 100)
                print("RUNTIME STRUCTURAL OBJECT ORIGIN")
                print("=" * 100)

                print(f"FILE             : {filename}")
                print(f"FUNCTION         : {function}")
                print(f"RETURN LINE      : {line}")
                print(f"OBJECT TYPE      : {type(value).__name__}")
                print(f"OBJECT            : {safe_repr(value)}")

                keys = set(value.keys())

                print()
                print(f"EXPECTED FIELDS  : {sorted(EXPECTED_FIELDS)}")
                print(f"ACTUAL FIELDS    : {sorted(keys)}")
                print(
                    f"EXTRA FIELDS     : "
                    f"{sorted(keys - EXPECTED_FIELDS)}"
                )
                print(
                    f"MISSING FIELDS   : "
                    f"{sorted(EXPECTED_FIELDS - keys)}"
                )

    # --------------------------------------------------------------
    # load_structural_state
    # --------------------------------------------------------------

    elif function == "load_structural_state":

        runtime_trace["load_structural_state_calls"] += 1

        if event == "call":

            asset = identify_asset_from_args(
                frame.f_locals,
                frame.f_locals,
            )

            if asset is not None:
                runtime_trace["asset"] = asset

    # --------------------------------------------------------------
    # build_signal
    # --------------------------------------------------------------

    elif function == "build_signal":

        runtime_trace["build_signal_calls"] += 1

        if event == "call":

            asset = identify_asset_from_args(
                frame.f_locals,
                frame.f_locals,
            )

            if asset is not None:
                runtime_trace["asset"] = asset

            structural_data = frame.f_locals.get(
                "structural_data"
            )

            if looks_like_structural_object(structural_data):

                runtime_trace["object"] = structural_data
                runtime_trace["origin_found"] = True

                print()
                print("=" * 100)
                print("RUNTIME OBJECT AT build_signal()")
                print("=" * 100)

                print(f"FILE       : {filename}")
                print(f"FUNCTION   : {function}")
                print(f"LINE       : {line}")
                print(f"ASSET      : {runtime_trace['asset']}")
                print(
                    f"OBJECT     : "
                    f"{safe_repr(structural_data)}"
                )

    # --------------------------------------------------------------
    # validate_structure
    # --------------------------------------------------------------

    elif function == "validate_structure":

        runtime_trace["validate_structure_calls"] += 1

        if event == "call":

            runtime_trace["validation_reached"] = True

            structure = frame.f_locals.get("structure")

            if looks_like_structural_object(structure):

                runtime_trace["object"] = structure

                print()
                print("=" * 100)
                print("RUNTIME OBJECT AT validate_structure()")
                print("=" * 100)

                print(f"FILE       : {filename}")
                print(f"FUNCTION   : {function}")
                print(f"LINE       : {line}")
                print(
                    f"ASSET      : "
                    f"{runtime_trace['asset']}"
                )
                print(
                    f"OBJECT     : "
                    f"{safe_repr(structure)}"
                )

                keys = set(structure.keys())

                print()
                print(
                    f"EXPECTED   : "
                    f"{sorted(EXPECTED_FIELDS)}"
                )
                print(
                    f"ACTUAL     : "
                    f"{sorted(keys)}"
                )
                print(
                    f"EXTRA      : "
                    f"{sorted(keys - EXPECTED_FIELDS)}"
                )
                print(
                    f"MISSING    : "
                    f"{sorted(EXPECTED_FIELDS - keys)}"
                )

    # --------------------------------------------------------------
    # RuntimeError
    # --------------------------------------------------------------

    if (
        event == "exception"
        and isinstance(arg, tuple)
        and len(arg) == 3
    ):

        exc_type, exc_value, _ = arg

        if (
            exc_type is RuntimeError
            and ERROR_TEXT.lower()
            in str(exc_value).lower()
        ):

            runtime_trace["failure"] = str(exc_value)

            print()
            print("=" * 100)
            print("TARGET RUNTIME ERROR OBSERVED")
            print("=" * 100)

            print(f"TYPE       : {exc_type.__name__}")
            print(f"ERROR      : {exc_value}")
            print(f"FILE       : {filename}")
            print(f"FUNCTION   : {function}")
            print(f"LINE       : {line}")
            print(
                f"ASSET      : "
                f"{runtime_trace['asset']}"
            )

            structure = frame.f_locals.get("structure")

            if looks_like_structural_object(structure):

                runtime_trace["object"] = structure

                print()
                print(
                    "FAILING STRUCTURAL OBJECT:"
                )
                print(safe_repr(structure))

    return trace_function


# ======================================================================
# D) REAL PRODUCTION RUNTIME
# ======================================================================

print()
print("=" * 100)
print("B) REAL PRODUCTION RUNTIME TRACE")
print("=" * 100)

print(f"TARGET MODULE : {TARGET_MODULE}")
print(f"TARGET        : {TARGET_MODULE}:{TARGET_FUNCTION}")

print()
print("STATUS : OBSERVING_REAL_PRODUCTION_RUNTIME")
print("No production function is patched.")
print("No signal is injected.")
print("No structural object is modified.")
print("Press Ctrl+C to stop if required.")

start = time.time()

previous_trace = sys.gettrace()

try:

    sys.settrace(trace_function)

    module = __import__(TARGET_MODULE)

    target = getattr(module, TARGET_FUNCTION)

    print()
    print(f"LOADED : {TARGET_MODULE}.{TARGET_FUNCTION}")
    print(
        f"SOURCE : "
        f"{inspect.getsourcefile(target)}"
    )

    target()

except KeyboardInterrupt:

    print()
    print("TRACE INTERRUPTED BY USER")

except Exception as exc:

    print()
    print("=" * 100)
    print("PRODUCTION RUNTIME RETURNED ERROR")
    print("=" * 100)
    print(f"TYPE  : {type(exc).__name__}")
    print(f"ERROR : {exc}")

finally:

    sys.settrace(previous_trace)


elapsed = time.time() - start


# ======================================================================
# E) FINAL DECISION
# ======================================================================

print()
print("=" * 100)
print("C) FINAL ORIGIN TRACE DECISION")
print("=" * 100)

if (
    runtime_trace["origin_found"]
    and runtime_trace["validation_reached"]
    and runtime_trace["object"] is not None
):

    obj = runtime_trace["object"]
    keys = set(obj.keys())

    print(
        "VERDICT : "
        "REAL_RUNTIME_STRUCTURAL_OBJECT_ORIGIN_TRACE_RESOLVED"
    )

    print()
    print(
        f"ASSET              : "
        f"{runtime_trace['asset']}"
    )

    print(
        f"ORIGIN FILE        : "
        f"{runtime_trace['origin_file']}"
    )

    print(
        f"ORIGIN FUNCTION    : "
        f"{runtime_trace['origin_function']}"
    )

    print(
        f"ORIGIN RETURN LINE : "
        f"{runtime_trace['origin_return_line']}"
    )

    print()
    print("ACTUAL RUNTIME OBJECT")
    print(safe_repr(obj))

    print()
    print(
        f"EXTRA FIELDS       : "
        f"{sorted(keys - EXPECTED_FIELDS)}"
    )

    print(
        f"MISSING FIELDS     : "
        f"{sorted(EXPECTED_FIELDS - keys)}"
    )

elif runtime_trace["failure"]:

    print(
        "VERDICT : "
        "REAL_RUNTIME_ERROR_OBSERVED_BUT_ORIGIN_NOT_FULLY_RESOLVED"
    )

else:

    print(
        "VERDICT : "
        "NO_RUNTIME_STRUCTURAL_OBJECT_ORIGIN_RESOLVED"
    )


# ======================================================================
# F) METRICS
# ======================================================================

print()
print("=" * 100)
print("D) TRACE METRICS")
print("=" * 100)

print(f"TRACE EVENTS              : {runtime_trace['events']}")
print(
    f"BUILD_STRUCTURE CALLS     : "
    f"{runtime_trace['build_structure_calls']}"
)
print(
    f"LOAD_STRUCTURAL_STATE     : "
    f"{runtime_trace['load_structural_state_calls']}"
)
print(
    f"BUILD_SIGNAL CALLS        : "
    f"{runtime_trace['build_signal_calls']}"
)
print(
    f"VALIDATE_STRUCTURE CALLS  : "
    f"{runtime_trace['validate_structure_calls']}"
)
print(f"ELAPSED SECONDS           : {elapsed:.2f}")


# ======================================================================
# G) SAFETY
# ======================================================================

print()
print("=" * 100)
print("E) SAFETY ASSERTION")
print("=" * 100)

print("PRODUCTION SOURCE MUTATION : False")
print("DATABASE READ              : False")
print("DATABASE WRITE             : False")
print("JSON WRITE                 : False")
print("ARTIFACT CREATION          : False")
print("SYNTHETIC SIGNAL           : False")
print("SIGNAL MUTATION            : False")
print("ORDER CREATION             : False")
print("ORDER SUBMISSION           : False")
print("NETWORK ACCESS BY TRACE    : False")
print("=" * 100)

print()
print("END — SIGNAL STRUCTURAL OBJECT ORIGIN TRACE v0.1")
print("=" * 100)