# =============================================================================
# ARUNDA
# DECISION_ENGINE_RUNTIME_CALL_CHAIN_FORENSIC_v0.1.py
# =============================================================================
#
# PURPOSE
# -------
# Find the REAL production runtime chain connecting:
#
#     market inputs
#          ↓
#     feature producer
#          ↓
#     signal_scorer.load_scores(...)
#          ↓
#     decision_engine
#          ↓
#     risk / execution
#
# MODE
# ----
# READ ONLY
#
# NO:
#     SQL
#     DB writes
#     file writes
#     imports of production modules
#     execution of production runtime
#
# This script is STATIC FORENSICS ONLY.
# =============================================================================

from __future__ import annotations

import ast
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

SKIP_FILE_PATTERNS = {
    "forensic",
    "locator",
    "audit",
    "repair",
    "verify",
    "verification",
    "test",
    "step",
    "m2_",
    "m3_",
    "m4_",
    "m5_",
    "m6_",
    "m7_",
    "m8_",
    "m9_",
}


TARGETS = {
    "signal_scorer.load_scores",
    "decision_engine.load_scores",
    "decision_engine.build_decision_snapshot",
    "signal_scorer.run",
    "decision_engine.main",
    "risk_engine",
    "execution",
    "process_signals",
    "main",
}

INPUTS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

SCORE_NAMES = {
    "scores",
    "score_snapshot",
    "signal_scores",
    "real_scores",
}

DECISION_NAMES = {
    "decision_snapshot",
    "decisions",
}


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def is_candidate(path: Path) -> bool:

    if path.suffix != ".py":
        return False

    if any(
        part in SKIP_DIRS
        for part in path.parts
    ):
        return False

    name = path.name.lower()

    for pattern in SKIP_FILE_PATTERNS:
        if pattern in name:
            return False

    return True


def discover_python_files():

    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if is_candidate(path)
    )


# =============================================================================
# AST HELPERS
# =============================================================================

def dotted_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        left = dotted_name(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return ""


def call_name(node):

    if not isinstance(node, ast.Call):
        return ""

    return dotted_name(node.func)


def argument_names(call):

    names = []

    for arg in call.args:

        if isinstance(arg, ast.Name):
            names.append(arg.id)

        elif isinstance(arg, ast.Attribute):

            name = dotted_name(arg)

            if name:
                names.append(name)

        else:
            names.append(
                ast.unparse(arg)
            )

    for keyword in call.keywords:

        if keyword.arg is None:
            names.append(
                "**" + ast.unparse(keyword.value)
            )
        else:
            names.append(
                keyword.arg
                + "="
                + ast.unparse(keyword.value)
            )

    return names


# =============================================================================
# STATIC CALL RECORD
# =============================================================================

class CallRecord:

    def __init__(
        self,
        file,
        line,
        caller,
        callee,
        args,
    ):

        self.file = file
        self.line = line
        self.caller = caller
        self.callee = callee
        self.args = args


# =============================================================================
# AST SCAN
# =============================================================================

def scan_file(path):

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception as error:

        return [], [
            (
                str(path),
                type(error).__name__,
                str(error),
            )
        ]

    calls = []
    errors = []

    function_stack = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):

            function_stack.append(
                node.name
            )

            self.generic_visit(node)

            function_stack.pop()

        def visit_AsyncFunctionDef(self, node):

            function_stack.append(
                node.name
            )

            self.generic_visit(node)

            function_stack.pop()

        def visit_Call(self, node):

            callee = call_name(node)

            caller = (
                function_stack[-1]
                if function_stack
                else "<module>"
            )

            interesting = False

            if callee in TARGETS:
                interesting = True

            if (
                "load_scores" in callee
                or "build_decision_snapshot" in callee
                or "load_features" in callee
                or "load_feature_snapshot" in callee
            ):
                interesting = True

            args = argument_names(node)

            if any(
                name in str(args)
                for name in INPUTS
            ):
                interesting = True

            if interesting:

                calls.append(
                    CallRecord(
                        path,
                        node.lineno,
                        caller,
                        callee,
                        args,
                    )
                )

            self.generic_visit(node)

    Visitor().visit(tree)

    return calls, errors


# =============================================================================
# FUNCTION SIGNATURE SCAN
# =============================================================================

def scan_signatures(path):

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:

        return []

    results = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name not in {
            "load_scores",
            "run",
            "build_decision_snapshot",
            "load_features",
            "load_feature_snapshot",
            "main",
        }:
            continue

        args = []

        positional = (
            node.args.posonlyargs
            + node.args.args
        )

        defaults = [
            None
        ] * (
            len(positional)
            - len(node.args.defaults)
        ) + list(
            node.args.defaults
        )

        for arg, default in zip(
            positional,
            defaults,
        ):

            if default is None:
                args.append(
                    arg.arg
                )
            else:
                args.append(
                    arg.arg
                    + "="
                    + ast.unparse(default)
                )

        if node.args.vararg:
            args.append(
                "*" + node.args.vararg.arg
            )

        for arg, default in zip(
            node.args.kwonlyargs,
            node.args.kw_defaults,
        ):

            if default is None:
                args.append(
                    arg.arg
                )
            else:
                args.append(
                    arg.arg
                    + "="
                    + ast.unparse(default)
                )

        results.append(
            (
                node.name,
                node.lineno,
                args,
            )
        )

    return results


# =============================================================================
# PRINT
# =============================================================================

def print_header():

    print("=" * 100)
    print(
        "ARUNDA DECISION ENGINE "
        "RUNTIME CALL CHAIN FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        "ROOT        :",
        ROOT,
    )

    print(
        "MODE        : READ ONLY",
    )

    print(
        "FILE WRITES : NONE",
    )

    print(
        "SQL         : NONE",
    )

    print(
        "PROD EXEC   : NONE",
    )

    print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    files = discover_python_files()

    print()
    print(
        "PRODUCTION CANDIDATE FILES :",
        len(files),
    )

    all_calls = []
    all_errors = []

    for path in files:

        calls, errors = scan_file(path)

        all_calls.extend(calls)
        all_errors.extend(errors)

    # -------------------------------------------------------------------------
    # SIGNATURES
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("RELEVANT FUNCTION SIGNATURES")
    print("=" * 100)

    for path in files:

        signatures = scan_signatures(path)

        if not signatures:
            continue

        for (
            name,
            line,
            args,
        ) in signatures:

            if name in {
                "load_scores",
                "run",
                "build_decision_snapshot",
                "load_features",
                "load_feature_snapshot",
            }:

                print()
                print(
                    f"FILE : {path}"
                )

                print(
                    f"LINE : {line}"
                )

                print(
                    f"FUNC : {name}("
                    + ", ".join(args)
                    + ")"
                )

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("RELEVANT CALL SITES")
    print("=" * 100)

    for record in all_calls:

        print()
        print(
            "FILE   :",
            record.file,
        )

        print(
            "LINE   :",
            record.line,
        )

        print(
            "CALLER :",
            record.caller,
        )

        print(
            "CALLEE :",
            record.callee,
        )

        print(
            "ARGS   :",
            ", ".join(record.args)
            if record.args
            else "<ZERO ARGUMENTS>",
        )

    # -------------------------------------------------------------------------
    # CRITICAL PATTERNS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("CRITICAL BOUNDARY ANALYSIS")
    print("=" * 100)

    scorer_calls = [
        x
        for x in all_calls
        if (
            x.callee == "signal_scorer.load_scores"
            or x.callee.endswith(
                ".signal_scorer.load_scores"
            )
        )
    ]

    decision_score_calls = [
        x
        for x in all_calls
        if (
            x.callee == "decision_engine.load_scores"
            or x.callee.endswith(
                ".decision_engine.load_scores"
            )
        )
    ]

    decision_build_calls = [
        x
        for x in all_calls
        if (
            "build_decision_snapshot"
            in x.callee
        )
    ]

    real_input_calls = [
        x
        for x in all_calls
        if any(
            name in x.args
            for name in INPUTS
        )
    ]

    print()
    print(
        "signal_scorer.load_scores calls :",
        len(scorer_calls),
    )

    for x in scorer_calls:

        print(
            f"  {x.file.name}:{x.line}"
        )

        print(
            "     args:",
            ", ".join(x.args)
            if x.args
            else "<NONE>",
        )

    print()
    print(
        "decision_engine.load_scores calls :",
        len(decision_score_calls),
    )

    for x in decision_score_calls:

        print(
            f"  {x.file.name}:{x.line}"
        )

        print(
            "     args:",
            ", ".join(x.args)
            if x.args
            else "<NONE>",
        )

    print()
    print(
        "build_decision_snapshot calls :",
        len(decision_build_calls),
    )

    for x in decision_build_calls:

        print(
            f"  {x.file.name}:{x.line}"
        )

        print(
            "     args:",
            ", ".join(x.args)
            if x.args
            else "<NONE>",
        )

    print()
    print(
        "Calls carrying real feature inputs :",
        len(real_input_calls),
    )

    for x in real_input_calls:

        print(
            f"  {x.file.name}:{x.line}"
        )

        print(
            "     ",
            x.callee,
            "(",
            ", ".join(x.args),
            ")",
        )

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FORENSIC VERDICT")
    print("=" * 100)

    scorer_has_real_inputs = any(
        any(
            name in x.args
            for name in INPUTS
        )
        for x in scorer_calls
    )

    decision_receives_scores = any(
        any(
            name in x.args
            for name in SCORE_NAMES
        )
        for x in decision_build_calls
    )

    zero_arg_decision_loader = any(
        len(x.args) == 0
        for x in decision_score_calls
    )

    if scorer_has_real_inputs:

        print(
            "REAL FEATURE → SCORER : FOUND"
        )

    else:

        print(
            "REAL FEATURE → SCORER : NOT PROVEN"
        )

    if decision_receives_scores:

        print(
            "SCORE → DECISION        : FOUND"
        )

    else:

        print(
            "SCORE → DECISION        : NOT PROVEN"
        )

    if zero_arg_decision_loader:

        print(
            "ZERO-ARG DECISION SCORE LOADER : FOUND"
        )

    else:

        print(
            "ZERO-ARG DECISION SCORE LOADER : NOT FOUND"
        )

    print()

    if (
        scorer_has_real_inputs
        and decision_receives_scores
        and not zero_arg_decision_loader
    ):

        print(
            "OVERALL : REAL SCORE → DECISION BRIDGE "
            "STATICALLY CONNECTED"
        )

    elif (
        scorer_has_real_inputs
        and zero_arg_decision_loader
    ):

        print(
            "OVERALL : DECISION SCORE INPUT BOUNDARY "
            "IS STRUCTURALLY BROKEN"
        )

    else:

        print(
            "OVERALL : RUNTIME BRIDGE NOT YET PROVEN"
        )

    # -------------------------------------------------------------------------
    # ERRORS
    # -------------------------------------------------------------------------

    if all_errors:

        print()
        print("=" * 100)
        print("PARSE ERRORS")
        print("=" * 100)

        for (
            file,
            error_type,
            message,
        ) in all_errors:

            print(
                file,
                "|",
                error_type,
                "|",
                message,
            )

    print()
    print("=" * 100)
    print("FORENSIC STATUS : COMPLETE")
    print("=" * 100)


if __name__ == "__main__":

    main()