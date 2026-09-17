# ARUNDA_RUNTIME_PROVENANCE_INSTRUMENTATION_v0.2.py
# =================================================================================================
# PURPOSE:
#   REAL RUNTIME PROVENANCE — find the first runtime population/assignment
#   of:
#       bars_by_asset
#       indicators_by_asset
#       structures_by_asset
#
# MODE:
#   READ ONLY / RUNTIME INSTRUMENTATION
#
# GUARANTEES:
#   - NO DATABASE ACCESS
#   - NO DATABASE WRITE
#   - NO PROJECT IMPORT BY THIS SCRIPT
#   - NO SOURCE FILE MODIFICATION
#   - NO SYNTHETIC DATA
#
# IMPORTANT:
#   This script executes ONLY the selected production entrypoint.
#   It does NOT execute the pipeline automatically unless an entrypoint
#   has been explicitly supplied or uniquely discovered.
# =================================================================================================

from __future__ import annotations

import argparse
import ast
import builtins
import inspect
import os
import runpy
import sys
import threading
import traceback
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader").resolve()

TARGETS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

FORENSIC_MARKERS = (
    "main",
    "run",
    "launcher",
    "live",
    "production",
    "pipeline",
    "engine",
    "startup",
)


# -------------------------------------------------------------------------------------------------
# OUTPUT
# -------------------------------------------------------------------------------------------------

def banner(text: str):
    print("=" * 100)
    print(text)
    print("=" * 100)


def section(text: str):
    print()
    print("-" * 100)
    print(text)
    print("-" * 100)


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = f"<repr failed: {type(value).__name__}>"

    if len(text) > limit:
        return text[:limit] + "..."
    return text


def describe_value(name, value):
    try:
        typ = type(value).__name__
        module = type(value).__module__

        if isinstance(value, dict):
            return (
                f"{name}: type={module}.{typ}, "
                f"len={len(value)}, "
                f"keys_sample={list(value.keys())[:5]}"
            )

        return (
            f"{name}: type={module}.{typ}, "
            f"value={safe_repr(value)}"
        )

    except Exception as exc:
        return f"{name}: <inspection failed: {exc}>"


# -------------------------------------------------------------------------------------------------
# STATIC DISCOVERY OF POSSIBLE ENTRYPOINTS
# -------------------------------------------------------------------------------------------------

def is_project_python(path: Path) -> bool:
    return (
        path.suffix.lower() == ".py"
        and PROJECT_ROOT in path.resolve().parents
        and not path.name.startswith(".")
    )


def ast_entrypoint_score(path: Path):
    score = 0
    reasons = []

    name = path.name.lower()

    for marker in FORENSIC_MARKERS:
        if marker in name:
            score += 10
            reasons.append(f"name:{marker}")

    try:
        source = path.read_text(encoding="utf-8-sig", errors="replace")
        tree = ast.parse(source, filename=str(path))

        function_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        if "main" in function_names:
            score += 30
            reasons.append("function:main")

        if "run" in function_names:
            score += 20
            reasons.append("function:run")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == "main":
                        score += 15
                        reasons.append("calls:main")

                    if node.func.id == "run":
                        score += 10
                        reasons.append("calls:run")

        if "__name__" in source and "__main__" in source:
            score += 20
            reasons.append("__main__")

    except Exception:
        return -1, ["parse-error"]

    return score, reasons


def discover_entrypoints():
    candidates = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if not is_project_python(path):
            continue

        score, reasons = ast_entrypoint_score(path)

        if score >= 30:
            candidates.append(
                {
                    "path": path,
                    "score": score,
                    "reasons": reasons,
                }
            )

    candidates.sort(
        key=lambda x: (-x["score"], str(x["path"]).lower())
    )

    return candidates


def print_entrypoint_candidates(candidates):
    banner("ENTRYPOINT DISCOVERY")

    if not candidates:
        print("NO STRONG ENTRYPOINT CANDIDATE FOUND.")
        return

    for i, item in enumerate(candidates[:30], 1):
        print()
        print(f"[{i}] SCORE : {item['score']}")
        print(f"FILE    : {item['path']}")
        print(f"REASONS : {', '.join(item['reasons'])}")


# -------------------------------------------------------------------------------------------------
# RUNTIME PROVENANCE STATE
# -------------------------------------------------------------------------------------------------

class ProvenanceState:
    def __init__(self):
        self.lock = threading.RLock()

        self.first_seen = {
            target: None
            for target in TARGETS
        }

        self.events = []

        self.stack = []

        self.function_calls = 0

        self.assignment_candidates = 0

    def record(
        self,
        target,
        value,
        filename,
        lineno,
        function,
        event,
        detail="",
    ):
        with self.lock:

            record = {
                "target": target,
                "event": event,
                "filename": filename,
                "lineno": lineno,
                "function": function,
                "detail": detail,
                "value": describe_value(target, value),
                "stack": list(self.stack),
            }

            self.events.append(record)

            if self.first_seen[target] is None:
                self.first_seen[target] = record

                banner(
                    f"FIRST RUNTIME PROVENANCE FOUND :: {target}"
                )

                print(f"EVENT    : {event}")
                print(f"FILE     : {filename}")
                print(f"LINE     : {lineno}")
                print(f"FUNCTION : {function}")
                print(f"DETAIL   : {detail}")
                print(f"VALUE    : {record['value']}")

                if self.stack:
                    print("CALL CHAIN:")
                    for idx, frame in enumerate(self.stack, 1):
                        print(f"  {idx}. {frame}")

                print()

    def push_function(self, filename, function, lineno):
        with self.lock:
            self.stack.append(
                f"{filename} :: {function} @ {lineno}"
            )

    def pop_function(self):
        with self.lock:
            if self.stack:
                self.stack.pop()


STATE = ProvenanceState()


# -------------------------------------------------------------------------------------------------
# TRACE FUNCTION
# -------------------------------------------------------------------------------------------------

def trace_function(frame, event, arg):

    if event == "call":

        filename = frame.f_code.co_filename

        # Trace only project runtime.
        try:
            resolved = Path(filename).resolve()
        except Exception:
            return trace_function

        if PROJECT_ROOT not in resolved.parents:
            return trace_function

        STATE.function_calls += 1

        STATE.push_function(
            filename,
            frame.f_code.co_name,
            frame.f_lineno,
        )

        return trace_function

    if event == "line":

        filename = frame.f_code.co_filename

        try:
            resolved = Path(filename).resolve()
        except Exception:
            return trace_function

        if PROJECT_ROOT not in resolved.parents:
            return trace_function

        lineno = frame.f_lineno

        # Inspect locals at the exact runtime line.
        for target in TARGETS:

            if target not in frame.f_locals:
                continue

            value = frame.f_locals[target]

            # We are interested in first actual runtime presence,
            # not merely AST existence.
            STATE.record(
                target=target,
                value=value,
                filename=filename,
                lineno=lineno,
                function=frame.f_code.co_name,
                event="RUNTIME_LOCAL_PRESENT",
                detail=(
                    "Target exists in live frame locals."
                ),
            )

        return trace_function

    if event == "return":

        filename = frame.f_code.co_filename

        try:
            resolved = Path(filename).resolve()
        except Exception:
            return trace_function

        if PROJECT_ROOT in resolved.parents:
            STATE.pop_function()

        return trace_function

    return trace_function


# -------------------------------------------------------------------------------------------------
# BYTECODE / SOURCE CORRELATION
# -------------------------------------------------------------------------------------------------

def inspect_assignment_source(record):
    filename = Path(record["filename"])

    try:
        source = filename.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

        lines = source.splitlines()

        line_index = record["lineno"] - 1

        start = max(0, line_index - 3)
        end = min(len(lines), line_index + 4)

        return "\n".join(
            f"{i + 1:6d} | {lines[i]}"
            for i in range(start, end)
        )

    except Exception as exc:
        return f"<source inspection failed: {exc}>"


# -------------------------------------------------------------------------------------------------
# RUN
# -------------------------------------------------------------------------------------------------

def execute_entrypoint(entrypoint: Path):

    banner("RUNTIME PROVENANCE EXECUTION")

    print(f"ENTRYPOINT : {entrypoint}")
    print("MODE       : INSTRUMENTED READ-ONLY RUNTIME")
    print("DATABASE   : NOT TOUCHED BY FORENSIC SCRIPT")
    print()

    # Prevent this forensic script from becoming the apparent caller.
    original_trace = sys.gettrace()

    sys.settrace(trace_function)

    try:
        runpy.run_path(
            str(entrypoint),
            run_name="__main__",
        )

    except SystemExit as exc:
        print()
        print(
            f"[RUNTIME] Production entrypoint exited with "
            f"SystemExit({exc.code})"
        )

    except Exception as exc:
        print()
        print("=" * 100)
        print("RUNTIME EXCEPTION")
        print("=" * 100)
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    finally:
        sys.settrace(original_trace)


# -------------------------------------------------------------------------------------------------
# FINAL REPORT
# -------------------------------------------------------------------------------------------------

def final_report(entrypoint):

    banner("FINAL RUNTIME PROVENANCE REPORT")

    print(f"ENTRYPOINT : {entrypoint}")
    print(f"FUNCTION CALLS OBSERVED : {STATE.function_calls}")

    print()

    for target in sorted(TARGETS):

        record = STATE.first_seen[target]

        print("=" * 100)
        print(f"TARGET : {target}")
        print("=" * 100)

        if record is None:
            print("STATUS : NOT OBSERVED IN THIS RUNTIME")
            continue

        print("STATUS   : FIRST RUNTIME PRESENCE FOUND")
        print(f"EVENT    : {record['event']}")
        print(f"FILE     : {record['filename']}")
        print(f"LINE     : {record['lineno']}")
        print(f"FUNCTION : {record['function']}")
        print(f"DETAIL   : {record['detail']}")
        print(f"VALUE    : {record['value']}")

        print()
        print("CALL CHAIN AT FIRST OBSERVATION:")

        for i, frame in enumerate(record["stack"], 1):
            print(f"  {i}. {frame}")

        print()
        print("SOURCE CONTEXT:")

        print(
            inspect_assignment_source(record)
        )

    print()
    banner("FORENSIC INTERPRETATION")

    found = [
        target
        for target in TARGETS
        if STATE.first_seen[target] is not None
    ]

    missing = TARGETS - set(found)

    print(f"TARGETS OBSERVED : {len(found)}/3")

    if missing:
        print(
            "TARGETS NOT OBSERVED : "
            + ", ".join(sorted(missing))
        )

    if len(found) == 3:

        records = [
            STATE.first_seen[target]
            for target in TARGETS
        ]

        files = {
            r["filename"]
            for r in records
        }

        functions = {
            r["function"]
            for r in records
        }

        print()
        print("ALL THREE TARGETS WERE OBSERVED AT RUNTIME.")

        if len(files) == 1 and len(functions) == 1:
            print()
            print("STRONG RESULT:")
            print(
                "All three mappings first appeared in the same "
                "runtime function."
            )
            print(f"FILE(S)     : {list(files)[0]}")
            print(f"FUNCTION(S) : {list(functions)[0]}")
        else:
            print()
            print(
                "RESULT:"
            )
            print(
                "The three mappings do NOT share one first runtime "
                "population point."
            )

    print()
    print("NO SOURCE FILES MODIFIED.")
    print("NO DATABASE ACCESSED BY FORENSIC SCRIPT.")
    print("NO SYNTHETIC DATA CREATED.")
    print("RUNTIME PROVENANCE TRACE COMPLETE.")


# -------------------------------------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "ARUNDA TRADER — REAL RUNTIME PROVENANCE "
            "INSTRUMENTATION"
        )
    )

    parser.add_argument(
        "--entrypoint",
        type=str,
        default=None,
        help=(
            "Explicit production Python entrypoint. "
            "If omitted, candidates are discovered."
        ),
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Automatically execute the strongest discovered "
            "entrypoint if confidence is high."
        ),
    )

    args = parser.parse_args()

    banner(
        "ARUNDA TRADER — REAL RUNTIME PROVENANCE "
        "INSTRUMENTATION v0.2"
    )

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ ONLY / RUNTIME INSTRUMENTATION")
    print("IMPORTS      : NONE FROM PROJECT BY FORENSIC SCRIPT")
    print("DATABASE     : NOT TOUCHED")
    print("SOURCE EDIT  : NONE")
    print()

    if args.entrypoint:

        entrypoint = Path(args.entrypoint).resolve()

        if not entrypoint.exists():
            print(
                f"ERROR: entrypoint does not exist:\n{entrypoint}"
            )
            sys.exit(2)

        if entrypoint.suffix.lower() != ".py":
            print(
                f"ERROR: entrypoint must be a Python file:\n"
                f"{entrypoint}"
            )
            sys.exit(2)

        execute_entrypoint(entrypoint)
        final_report(entrypoint)
        return

    candidates = discover_entrypoints()

    print_entrypoint_candidates(candidates)

    if not args.auto:

        print()
        banner("NO RUNTIME EXECUTION PERFORMED")

        print(
            "You did not provide --entrypoint."
        )

        print()
        print(
            "This version intentionally refuses to execute an "
            "ambiguous candidate."
        )

        print()
        print(
            "NEXT COMMAND:"
        )

        if candidates:
            print(
                f'python "{Path(__file__).name}" '
                f'--entrypoint "{candidates[0]["path"]}"'
            )
        else:
            print(
                'python "ARUNDA_RUNTIME_PROVENANCE_INSTRUMENTATION_v0.2.py" '
                '--entrypoint "YOUR_REAL_PRODUCTION_ENTRYPOINT.py"'
            )

        print()
        print(
            "No source modified."
        )
        print(
            "No database accessed."
        )

        return

    # AUTO MODE
    if not candidates:

        print()
        print(
            "AUTO MODE ABORTED: no sufficiently strong "
            "production entrypoint candidate."
        )
        return

    if len(candidates) > 1:
        top = candidates[0]["score"]
        second = candidates[1]["score"]

        # Do not guess if confidence is too close.
        if top - second < 20:

            print()
            print(
                "AUTO MODE ABORTED: entrypoint ambiguity."
            )
            print(
                f"TOP SCORE    : {top}"
            )
            print(
                f"SECOND SCORE : {second}"
            )
            print()
            print(
                "Use --entrypoint explicitly."
            )
            return

    entrypoint = candidates[0]["path"]

    execute_entrypoint(entrypoint)
    final_report(entrypoint)


if __name__ == "__main__":
    main()