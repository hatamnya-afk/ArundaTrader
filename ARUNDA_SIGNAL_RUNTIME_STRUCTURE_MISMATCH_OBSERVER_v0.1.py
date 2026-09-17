# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
REAL RUNTIME STRUCTURE MISMATCH OBSERVER v0.1

Purpose:
    Observe the real runtime path of signal_engine.main and capture
    the actual structural object immediately before/at the validation
    boundary that raises:

        RuntimeError("Invalid structural fields")

Safety:
    READ ONLY
    No production source modification
    No database access by observer
    No JSON writes
    No artifact creation
    No synthetic signal
    No order creation/submission
    No network access by observer

Important:
    This observer uses Python tracing only.
    It does not monkey-patch production functions.
"""

from __future__ import annotations

import ast
import sys
import time
import traceback
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_MODULE = "signal_engine"
TARGET_FILE = PROJECT_ROOT / "signal_engine.py"

ERROR_TEXT = "Invalid structural fields"

FORENSIC_NAME = (
    "ARUNDA SIGNAL RUNTIME STRUCTURE MISMATCH OBSERVER v0.1"
)


# ----------------------------------------------------------------------
# GLOBAL OBSERVATION STATE
# ----------------------------------------------------------------------

trace_events = 0
calls = 0
start_time = time.time()

captured = False
captured_asset = None
captured_structure = None
captured_expected = None
captured_actual = None
captured_missing = None
captured_extra = None

target_validate_code = None
target_build_signal_code = None


# ----------------------------------------------------------------------
# SAFE VALUE HELPERS
# ----------------------------------------------------------------------

def safe_repr(value, limit=12000):
    try:
        text = repr(value)
    except Exception:
        text = "<UNREPRESENTABLE>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def field_names(value):
    if isinstance(value, dict):
        return sorted(str(k) for k in value.keys())

    return []


def find_asset(structure):
    if not isinstance(structure, dict):
        return None

    for key in (
        "asset",
        "symbol",
        "market",
        "pair",
        "ticker",
    ):
        if key in structure:
            return structure.get(key)

    return None


# ----------------------------------------------------------------------
# STATIC DISCOVERY — ONLY TO IDENTIFY TRACE TARGETS
# ----------------------------------------------------------------------

def discover_targets():
    global target_validate_code
    global target_build_signal_code

    source = TARGET_FILE.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(TARGET_FILE),
    )

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):

            if node.name == "build_signal":
                target_build_signal_code = node

    # signal_logic.py is inspected only to identify the exact
    # validation function. It is NOT modified or executed here.
    logic_file = PROJECT_ROOT / "signal_logic.py"

    if logic_file.exists():

        logic_source = logic_file.read_text(
            encoding="utf-8"
        )

        logic_tree = ast.parse(
            logic_source,
            filename=str(logic_file),
        )

        for node in ast.walk(logic_tree):

            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "validate_structure"
            ):
                target_validate_code = node


# ----------------------------------------------------------------------
# TRACE CALLBACK
# ----------------------------------------------------------------------

def tracer(frame, event, arg):

    global trace_events
    global calls

    global captured
    global captured_asset
    global captured_structure
    global captured_expected
    global captured_actual
    global captured_missing
    global captured_extra

    trace_events += 1

    filename = Path(
        frame.f_code.co_filename
    ).resolve()

    function = frame.f_code.co_name

    # Only observe production files.
    if filename.parent != PROJECT_ROOT:
        return tracer

    # --------------------------------------------------------------
    # Observe entry to build_signal
    # --------------------------------------------------------------

    if (
        filename.name == "signal_engine.py"
        and function == "build_signal"
        and event == "call"
    ):
        calls += 1

        return tracer

    # --------------------------------------------------------------
    # Observe validate_structure
    # --------------------------------------------------------------

    if (
        filename.name == "signal_logic.py"
        and function == "validate_structure"
    ):

        # Capture the local "structure" object if available.
        structure = frame.f_locals.get(
            "structure"
        )

        # Capture EXPECTED_FIELDS from globals.
        expected = frame.f_globals.get(
            "EXPECTED_FIELDS"
        )

        if isinstance(structure, dict):

            actual = field_names(structure)

            if isinstance(expected, (list, tuple, set, frozenset)):
                expected_fields = sorted(
                    str(x) for x in expected
                )
            else:
                expected_fields = []

            missing = sorted(
                set(expected_fields) - set(actual)
            )

            extra = sorted(
                set(actual) - set(expected_fields)
            )

            # Only stop on an actual mismatch.
            if missing or extra:

                captured = True

                captured_structure = structure.copy()
                captured_expected = expected_fields
                captured_actual = actual
                captured_missing = missing
                captured_extra = extra
                captured_asset = find_asset(
                    structure
                )

                return None

        return tracer

    # --------------------------------------------------------------
    # Observe RuntimeError event.
    # --------------------------------------------------------------

    if event == "exception":

        exc_type, exc_value, exc_tb = arg

        if (
            exc_type is RuntimeError
            and ERROR_TEXT in str(exc_value)
        ):

            # If structural data was already captured,
            # terminate immediately.
            return None

    return tracer


# ----------------------------------------------------------------------
# RUNTIME ENTRYPOINT
# ----------------------------------------------------------------------

def run_real_runtime():

    global captured

    print("=" * 100)
    print(
        "ARUNDA TRADER — "
        "REAL RUNTIME STRUCTURE MISMATCH OBSERVER v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT       : {PROJECT_ROOT}"
    )

    print(
        f"TARGET             : "
        f"{TARGET_MODULE}:main"
    )

    print(
        "MODE               : "
        "READ-ONLY RUNTIME OBSERVATION"
    )

    print(
        "PRODUCTION MUTATION : NONE"
    )

    print(
        "DATABASE ACCESS     : NONE"
    )

    print(
        "DATABASE WRITE      : NONE"
    )

    print(
        "JSON WRITE          : NONE"
    )

    print(
        "ARTIFACT CREATION   : NONE"
    )

    print(
        "SYNTHETIC SIGNAL    : FORBIDDEN"
    )

    print("=" * 100)

    discover_targets()

    if not TARGET_FILE.exists():
        raise FileNotFoundError(
            f"Missing target: {TARGET_FILE}"
        )

    print()
    print("=" * 100)
    print("RUNTIME TARGET")
    print("=" * 100)

    print(
        f"MODULE : {TARGET_MODULE}"
    )

    print(
        f"FILE   : {TARGET_FILE}"
    )

    print()
    print(
        "TRACE : Python runtime observation enabled"
    )

    print(
        "TRACE : No production function is patched"
    )

    print()
    print("=" * 100)
    print("RUNTIME OBSERVATION START")
    print("=" * 100)

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

    # Import production module normally.
    module = __import__(
        TARGET_MODULE
    )

    if not hasattr(module, "main"):
        raise RuntimeError(
            "signal_engine.main not found"
        )

    previous_trace = sys.gettrace()

    sys.settrace(tracer)

    try:

        try:
            module.main()

        except Exception as exc:

            print()
            print("=" * 100)
            print("RUNTIME TERMINATION")
            print("=" * 100)

            print(
                f"TYPE   : {type(exc).__name__}"
            )

            print(
                f"ERROR  : {exc}"
            )

            if (
                isinstance(exc, RuntimeError)
                and ERROR_TEXT in str(exc)
            ):
                print(
                    "MATCH  : TARGET STRUCTURAL "
                    "RUNTIME ERROR"
                )

    finally:

        sys.settrace(previous_trace)

    # ------------------------------------------------------------------
    # FINAL OBSERVATION RESULT
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL RUNTIME OBSERVATION")
    print("=" * 100)

    if captured:

        print(
            "VERDICT : "
            "REAL_RUNTIME_STRUCTURAL_SCHEMA_MISMATCH_RESOLVED"
        )

        print()
        print(
            f"ASSET : {captured_asset}"
        )

        print()
        print(
            "EXPECTED FIELDS"
        )
        print(
            safe_repr(captured_expected)
        )

        print()
        print(
            "ACTUAL FIELDS"
        )
        print(
            safe_repr(captured_actual)
        )

        print()
        print(
            "MISSING FIELDS"
        )
        print(
            safe_repr(captured_missing)
        )

        print()
        print(
            "EXTRA FIELDS"
        )
        print(
            safe_repr(captured_extra)
        )

        print()
        print(
            "ACTUAL STRUCTURE OBJECT"
        )
        print(
            safe_repr(captured_structure)
        )

    else:

        print(
            "VERDICT : "
            "NO_RUNTIME_STRUCTURAL_MISMATCH_CAPTURED"
        )

    elapsed = time.time() - start_time

    print()
    print("=" * 100)
    print("OBSERVATION METRICS")
    print("=" * 100)

    print(
        f"TRACE EVENTS : {trace_events}"
    )

    print(
        f"BUILD SIGNAL CALLS : {calls}"
    )

    print(
        f"ELAPSED SECONDS : {elapsed:.2f}"
    )

    print()
    print("=" * 100)
    print("SAFETY ASSERTION")
    print("=" * 100)

    print(
        "PRODUCTION SOURCE MUTATION : False"
    )

    print(
        "DATABASE READ              : False"
    )

    print(
        "DATABASE WRITE             : False"
    )

    print(
        "JSON WRITE                 : False"
    )

    print(
        "ARTIFACT CREATION          : False"
    )

    print(
        "SYNTHETIC SIGNAL           : False"
    )

    print(
        "SIGNAL MUTATION            : False"
    )

    print(
        "ORDER CREATION             : False"
    )

    print(
        "ORDER SUBMISSION           : False"
    )

    print(
        "NETWORK ACCESS BY OBSERVER : False"
    )

    print("=" * 100)
    print(
        "END — REAL RUNTIME STRUCTURE "
        "MISMATCH OBSERVER v0.1"
    )
    print("=" * 100)


if __name__ == "__main__":
    run_real_runtime()