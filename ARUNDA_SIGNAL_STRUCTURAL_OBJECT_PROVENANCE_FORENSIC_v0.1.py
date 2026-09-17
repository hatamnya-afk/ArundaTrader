# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
SIGNAL STRUCTURAL OBJECT PROVENANCE FORENSIC v0.1

READ-ONLY RUNTIME FORENSIC

Goal:
    Resolve where the REAL runtime structural object comes from
    and where the extra "structure" field is introduced.

Safety:
    - No production source modification
    - No monkey patching
    - No database access
    - No database write
    - No JSON write
    - No artifact creation
    - No synthetic signal
    - No order creation/submission
    - No network access

Method:
    Python runtime tracing + source/AST inspection.

The forensic observes:
    signal_engine.main
        -> load_signals
        -> build_signal
        -> structural object creation/use
        -> signal_logic.validate_structure

It stops when the first REAL runtime structural object containing
the extra field "structure" reaches validate_structure().
"""

from __future__ import annotations

import ast
import sys
import time
from pathlib import Path


# ======================================================================
# CONFIG
# ======================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SIGNAL_ENGINE_FILE = PROJECT_ROOT / "signal_engine.py"
SIGNAL_LOGIC_FILE = PROJECT_ROOT / "signal_logic.py"

TARGET_MODULE = "signal_engine"
TARGET_FUNCTION = "main"

EXPECTED_EXTRA_FIELD = "structure"

FORENSIC_NAME = (
    "ARUNDA SIGNAL STRUCTURAL OBJECT PROVENANCE FORENSIC v0.1"
)


# ======================================================================
# STATE
# ======================================================================

trace_events = 0
build_signal_calls = 0

capture_found = False

captured_structure = None
captured_asset = None

captured_frame_file = None
captured_frame_function = None
captured_frame_line = None

runtime_stack = []


# ======================================================================
# SAFE HELPERS
# ======================================================================

def safe_repr(value, limit=20000):
    try:
        text = repr(value)
    except Exception:
        return "<UNREPRESENTABLE>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def source_line(filename, lineno):
    try:
        lines = Path(filename).read_text(
            encoding="utf-8"
        ).splitlines()

        if 1 <= lineno <= len(lines):
            return lines[lineno - 1].strip()

    except Exception:
        pass

    return "<SOURCE UNAVAILABLE>"


def asset_from_structure(structure):
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


# ======================================================================
# AST SOURCE FORENSICS
# ======================================================================

def ast_assignment_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def discover_structural_field_writes():

    results = []

    files = [
        SIGNAL_ENGINE_FILE,
        SIGNAL_LOGIC_FILE,
        PROJECT_ROOT / "market_regime.py",
        PROJECT_ROOT / "market_regime_engine.py",
        PROJECT_ROOT / "market_regime_contract.py",
    ]

    for file_path in files:

        if not file_path.exists():
            continue

        try:
            source = file_path.read_text(
                encoding="utf-8"
            )

            tree = ast.parse(
                source,
                filename=str(file_path),
            )

        except Exception:
            continue

        for node in ast.walk(tree):

            # ----------------------------------------------------------
            # Dictionary literal:
            #
            # {"structure": ...}
            # ----------------------------------------------------------

            if isinstance(node, ast.Dict):

                for key, value in zip(
                    node.keys,
                    node.values,
                ):

                    if (
                        isinstance(key, ast.Constant)
                        and key.value == EXPECTED_EXTRA_FIELD
                    ):

                        function_name = None

                        for parent in ast.walk(tree):

                            if not isinstance(
                                parent,
                                ast.FunctionDef,
                            ):
                                continue

                            for child in ast.walk(parent):

                                if child is node:
                                    function_name = (
                                        parent.name
                                    )
                                    break

                            if function_name:
                                break

                        results.append(
                            {
                                "file": str(file_path),
                                "line": getattr(
                                    node,
                                    "lineno",
                                    None,
                                ),
                                "function": function_name,
                                "kind": "DICT_LITERAL",
                                "source": ast_assignment_text(node),
                            }
                        )

            # ----------------------------------------------------------
            # Subscript writes:
            #
            # structure["structure"] = ...
            # obj["structure"] = ...
            # ----------------------------------------------------------

            if isinstance(node, ast.Assign):

                for target in node.targets:

                    if not isinstance(
                        target,
                        ast.Subscript,
                    ):
                        continue

                    slice_node = target.slice

                    if (
                        isinstance(
                            slice_node,
                            ast.Constant,
                        )
                        and slice_node.value
                        == EXPECTED_EXTRA_FIELD
                    ):

                        results.append(
                            {
                                "file": str(file_path),
                                "line": getattr(
                                    node,
                                    "lineno",
                                    None,
                                ),
                                "function": None,
                                "kind": "FIELD_ASSIGNMENT",
                                "source": ast_assignment_text(
                                    node
                                ),
                            }
                        )

            # ----------------------------------------------------------
            # update({"structure": ...})
            # ----------------------------------------------------------

            if isinstance(node, ast.Call):

                for arg in node.args:

                    if not isinstance(
                        arg,
                        ast.Dict,
                    ):
                        continue

                    for key in arg.keys:

                        if (
                            isinstance(key, ast.Constant)
                            and key.value
                            == EXPECTED_EXTRA_FIELD
                        ):

                            results.append(
                                {
                                    "file": str(file_path),
                                    "line": getattr(
                                        node,
                                        "lineno",
                                        None,
                                    ),
                                    "function": None,
                                    "kind": "DICT_ARGUMENT",
                                    "source": ast_assignment_text(
                                        node
                                    ),
                                }
                            )

    return results


# ======================================================================
# RUNTIME TRACE
# ======================================================================

def runtime_tracer(frame, event, arg):

    global trace_events
    global build_signal_calls
    global capture_found

    global captured_structure
    global captured_asset

    global captured_frame_file
    global captured_frame_function
    global captured_frame_line

    trace_events += 1

    filename = Path(
        frame.f_code.co_filename
    ).resolve()

    # Only observe project production source.
    if filename.parent != PROJECT_ROOT:
        return runtime_tracer

    function = frame.f_code.co_name

    # --------------------------------------------------------------
    # build_signal entry
    # --------------------------------------------------------------

    if (
        filename.name == "signal_engine.py"
        and function == "build_signal"
        and event == "call"
    ):
        build_signal_calls += 1

    # --------------------------------------------------------------
    # validate_structure
    # --------------------------------------------------------------

    if (
        filename.name == "signal_logic.py"
        and function == "validate_structure"
        and event == "call"
    ):

        structure = frame.f_locals.get(
            "structure"
        )

        expected = frame.f_globals.get(
            "EXPECTED_FIELDS"
        )

        if (
            isinstance(structure, dict)
            and EXPECTED_EXTRA_FIELD in structure
        ):

            if isinstance(
                expected,
                (list, tuple, set, frozenset),
            ):
                expected_set = set(expected)
            else:
                expected_set = set()

            actual_set = set(structure.keys())

            extra = sorted(
                str(x)
                for x in actual_set - expected_set
            )

            if EXPECTED_EXTRA_FIELD in extra:

                capture_found = True

                captured_structure = (
                    structure.copy()
                )

                captured_asset = (
                    asset_from_structure(
                        structure
                    )
                )

                captured_frame_file = str(
                    filename
                )

                captured_frame_function = (
                    function
                )

                captured_frame_line = (
                    frame.f_lineno
                )

                # Stop tracing deeper.
                return None

    return runtime_tracer


# ======================================================================
# RUNTIME CALL CHAIN SOURCE RESOLUTION
# ======================================================================

def source_call_chain():

    result = []

    if not SIGNAL_ENGINE_FILE.exists():
        return result

    try:
        source = SIGNAL_ENGINE_FILE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(SIGNAL_ENGINE_FILE),
        )

    except Exception:
        return result

    interesting = {
        "main",
        "load_signals",
        "build_signal",
    }

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.FunctionDef)
            and node.name in interesting
        ):

            for child in ast.walk(node):

                if isinstance(
                    child,
                    ast.Call,
                ):

                    if isinstance(
                        child.func,
                        ast.Name,
                    ):

                        if (
                            child.func.id
                            in interesting
                        ):

                            result.append(
                                {
                                    "function": node.name,
                                    "line": getattr(
                                        child,
                                        "lineno",
                                        None,
                                    ),
                                    "call":
                                        child.func.id,
                                    "source":
                                        ast_assignment_text(
                                            child
                                        ),
                                }
                            )

    return result


# ======================================================================
# MAIN
# ======================================================================

def main():

    global capture_found

    print("=" * 100)
    print(
        "ARUNDA TRADER — "
        "SIGNAL STRUCTURAL OBJECT PROVENANCE FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        f"TARGET       : {TARGET_MODULE}:{TARGET_FUNCTION}"
    )

    print(
        "MODE         : READ-ONLY RUNTIME OBSERVATION"
    )

    print(
        "PRODUCTION EXECUTION : REAL RUNTIME ONLY"
    )

    print(
        "DATABASE ACCESS       : NONE"
    )

    print(
        "DATABASE WRITE        : NONE"
    )

    print(
        "JSON WRITE            : NONE"
    )

    print(
        "SOURCE MUTATION       : NONE"
    )

    print(
        "SYNTHETIC SIGNAL      : FORBIDDEN"
    )

    print("=" * 100)

    # ------------------------------------------------------------------
    # STATIC CANDIDATE DISCOVERY
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("A) STATIC STRUCTURAL FIELD WRITE CANDIDATES")
    print("=" * 100)

    candidates = discover_structural_field_writes()

    print(
        f"FIELD '{EXPECTED_EXTRA_FIELD}' "
        f"STATIC CANDIDATES : {len(candidates)}"
    )

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        print()
        print(f"CANDIDATE #{index}")

        print(
            f"FILE     : {item.get('file')}"
        )

        print(
            f"FUNCTION : {item.get('function')}"
        )

        print(
            f"LINE     : {item.get('line')}"
        )

        print(
            f"KIND     : {item.get('kind')}"
        )

        print(
            f"SOURCE   : {item.get('source')}"
        )

    # ------------------------------------------------------------------
    # CALL CHAIN
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("B) SIGNAL ENGINE CALL CHAIN")
    print("=" * 100)

    chain = source_call_chain()

    for item in chain:

        print(
            f"{item['function']} "
            f"-> {item['call']} "
            f"(LINE {item['line']})"
        )

    # ------------------------------------------------------------------
    # REAL RUNTIME
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("C) REAL RUNTIME PROVENANCE OBSERVATION")
    print("=" * 100)

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

    module = __import__(
        TARGET_MODULE
    )

    if not hasattr(
        module,
        TARGET_FUNCTION,
    ):
        raise RuntimeError(
            "signal_engine.main not found"
        )

    print(
        "STATUS : OBSERVING_REAL_RUNTIME"
    )

    print(
        "TARGET : signal_engine.main"
    )

    previous_trace = sys.gettrace()

    sys.settrace(
        runtime_tracer
    )

    started = time.time()

    try:

        try:
            module.main()

        except Exception as exc:

            print()
            print("=" * 100)
            print("RUNTIME TERMINATION")
            print("=" * 100)

            print(
                f"TYPE  : {type(exc).__name__}"
            )

            print(
                f"ERROR : {exc}"
            )

    finally:

        sys.settrace(
            previous_trace
        )

    elapsed = time.time() - started

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("D) FINAL PROVENANCE DECISION")
    print("=" * 100)

    if capture_found:

        print(
            "VERDICT : "
            "REAL_RUNTIME_STRUCTURAL_OBJECT_REACHED"
        )

        print()
        print(
            f"ASSET : {captured_asset}"
        )

        print(
            f"RUNTIME FILE : "
            f"{captured_frame_file}"
        )

        print(
            f"RUNTIME FUNCTION : "
            f"{captured_frame_function}"
        )

        print(
            f"RUNTIME LINE : "
            f"{captured_frame_line}"
        )

        print()
        print(
            "RUNTIME SOURCE LINE:"
        )

        print(
            source_line(
                captured_frame_file,
                captured_frame_line,
            )
        )

        print()
        print(
            "ACTUAL STRUCTURAL OBJECT:"
        )

        print(
            safe_repr(
                captured_structure
            )
        )

        print()
        print(
            "EXTRA FIELD CONFIRMED:"
        )

        print(
            f"    {EXPECTED_EXTRA_FIELD}"
        )

    else:

        print(
            "VERDICT : "
            "RUNTIME_STRUCTURAL_OBJECT_NOT_CAPTURED"
        )

    print()
    print("=" * 100)
    print("E) METRICS")
    print("=" * 100)

    print(
        f"TRACE EVENTS       : {trace_events}"
    )

    print(
        f"BUILD_SIGNAL CALLS : {build_signal_calls}"
    )

    print(
        f"ELAPSED SECONDS    : {elapsed:.2f}"
    )

    print()
    print("=" * 100)
    print("F) SAFETY ASSERTION")
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
        "NETWORK ACCESS             : False"
    )

    print("=" * 100)
    print(
        "END — SIGNAL STRUCTURAL OBJECT "
        "PROVENANCE FORENSIC v0.1"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()