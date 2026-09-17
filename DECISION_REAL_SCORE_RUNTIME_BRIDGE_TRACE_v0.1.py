# -*- coding: utf-8 -*-

"""
==========================================================================================
ARUNDA DECISION REAL SCORE RUNTIME BRIDGE TRACE v0.1
==========================================================================================

MODE         : READ ONLY
DB WRITE     : NONE
PIPELINE RUN : NONE
SOURCE EDIT  : NONE

PURPOSE:
    Trace the REAL score producer -> score return -> decision bridge.

TARGET:
    Verify whether the real score object produced by:

        signal_scorer.load_scores(
            bars_by_asset,
            indicators_by_asset,
            structures_by_asset
        )

    is actually propagated into:

        decision_engine.build_decision_snapshot(
            validated_signals,
            scores
        )

    or whether production decision flow falls back to:

        decision_engine.load_scores()
            -> signal_scorer.load_scores()

    with ZERO arguments.

IMPORTANT:
    This script is READ ONLY.
    It does NOT import production modules.
    It does NOT execute the trading pipeline.
    It does NOT modify source files.
    It does NOT modify the database.
==========================================================================================
"""

from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Optional


# ==========================================================================================
# CONFIG
# ==========================================================================================

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET_FILES = [
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "execution_engine.py",
    "feature_contract.py",
    "feature_snapshot_reader.py",
]


# ==========================================================================================
# DATA STRUCTURES
# ==========================================================================================

@dataclass
class FunctionInfo:
    file: str
    name: str
    line: int
    args: list[str]
    node: ast.AST


@dataclass
class CallInfo:
    file: str
    line: int
    caller: str
    callee: str
    args: list[str]
    source: str
    zero_arg: bool


@dataclass
class AssignmentInfo:
    file: str
    line: int
    function: str
    variable: str
    source: str
    kind: str


@dataclass
class FileAnalysis:
    path: str
    source_lines: list[str]
    tree: ast.AST
    functions: list[FunctionInfo] = field(default_factory=list)
    calls: list[CallInfo] = field(default_factory=list)
    assignments: list[AssignmentInfo] = field(default_factory=list)


# ==========================================================================================
# HELPERS
# ==========================================================================================

def banner(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def rel(path: str) -> str:
    return os.path.relpath(path, PROJECT_ROOT)


def safe_source(lines: list[str], line_no: int) -> str:
    if 1 <= line_no <= len(lines):
        return lines[line_no - 1].rstrip()
    return ""


def expr_to_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node, include_attributes=False)


def get_call_name(node: ast.Call) -> str:
    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts = []
        current = func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return expr_to_text(func)


def get_target_names(node: ast.AST) -> list[str]:
    names = []

    if isinstance(node, ast.Name):
        names.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):
        for item in node.elts:
            names.extend(get_target_names(item))

    return names


def is_zero_arg_call(call: ast.Call) -> bool:
    return (
        len(call.args) == 0
        and len(call.keywords) == 0
    )


def call_arguments(call: ast.Call) -> list[str]:
    args = [expr_to_text(x) for x in call.args]

    for kw in call.keywords:
        if kw.arg is None:
            args.append("**" + expr_to_text(kw.value))
        else:
            args.append(f"{kw.arg}={expr_to_text(kw.value)}")

    return args


def contains_real_input(args: list[str]) -> bool:
    targets = {
        "bars_by_asset",
        "indicators_by_asset",
        "structures_by_asset",
    }

    for arg in args:
        if any(target in arg for target in targets):
            return True

    return False


def contains_score_object(args: list[str]) -> bool:
    for arg in args:
        stripped = arg.strip()

        if stripped == "scores":
            return True

        if stripped.startswith("scores["):
            return True

    return False


# ==========================================================================================
# AST VISITOR
# ==========================================================================================

class Analyzer(ast.NodeVisitor):

    def __init__(
        self,
        file_path: str,
        source_lines: list[str],
    ):
        self.file_path = file_path
        self.source_lines = source_lines

        self.functions: list[FunctionInfo] = []
        self.calls: list[CallInfo] = []
        self.assignments: list[AssignmentInfo] = []

        self.function_stack: list[str] = []

    # ------------------------------------------------------------------
    # FUNCTIONS
    # ------------------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = []

        for arg in node.args.args:
            args.append(arg.arg)

        info = FunctionInfo(
            file=rel(self.file_path),
            name=node.name,
            line=node.lineno,
            args=args,
            node=node,
        )

        self.functions.append(info)

        self.function_stack.append(node.name)

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        args = []

        for arg in node.args.args:
            args.append(arg.arg)

        info = FunctionInfo(
            file=rel(self.file_path),
            name=node.name,
            line=node.lineno,
            args=args,
            node=node,
        )

        self.functions.append(info)

        self.function_stack.append(node.name)

        self.generic_visit(node)

        self.function_stack.pop()

    # ------------------------------------------------------------------
    # CALLS
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call):

        caller = (
            self.function_stack[-1]
            if self.function_stack
            else "<MODULE>"
        )

        callee = get_call_name(node)
        args = call_arguments(node)

        source = safe_source(
            self.source_lines,
            node.lineno,
        )

        self.calls.append(
            CallInfo(
                file=rel(self.file_path),
                line=node.lineno,
                caller=caller,
                callee=callee,
                args=args,
                source=source,
                zero_arg=is_zero_arg_call(node),
            )
        )

        self.generic_visit(node)

    # ------------------------------------------------------------------
    # ASSIGNMENTS
    # ------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign):

        function = (
            self.function_stack[-1]
            if self.function_stack
            else "<MODULE>"
        )

        source = safe_source(
            self.source_lines,
            node.lineno,
        )

        for target in node.targets:

            names = get_target_names(target)

            for name in names:

                kind = "ASSIGN"

                if name == "scores":
                    self.assignments.append(
                        AssignmentInfo(
                            file=rel(self.file_path),
                            line=node.lineno,
                            function=function,
                            variable=name,
                            source=source,
                            kind=kind,
                        )
                    )

        self.generic_visit(node)


# ==========================================================================================
# FILE LOADING
# ==========================================================================================

def analyze_file(path: str) -> Optional[FileAnalysis]:

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace",
        ) as f:
            text = f.read()

    except Exception as exc:
        print(f"[ERROR] Cannot read {rel(path)}: {exc}")
        return None

    lines = text.splitlines()

    try:
        tree = ast.parse(
            text,
            filename=path,
        )

    except SyntaxError as exc:
        print(
            f"[SYNTAX ERROR] {rel(path)} "
            f"line={exc.lineno}: {exc.msg}"
        )
        return None

    analyzer = Analyzer(
        path,
        lines,
    )

    analyzer.visit(tree)

    return FileAnalysis(
        path=path,
        source_lines=lines,
        tree=tree,
        functions=analyzer.functions,
        calls=analyzer.calls,
        assignments=analyzer.assignments,
    )


# ==========================================================================================
# SCAN
# ==========================================================================================

def scan_project():

    analyses = []

    banner("TARGET FILE SCAN")

    for filename in TARGET_FILES:

        path = os.path.join(
            PROJECT_ROOT,
            filename,
        )

        print(f"[SCAN] {filename}")

        if not os.path.isfile(path):
            print(f"       MISSING")
            continue

        result = analyze_file(path)

        if result is not None:
            analyses.append(result)

    print()
    print(f"FILES SCANNED : {len(analyses)}")
    print(
        f"FILES MISSING : "
        f"{len(TARGET_FILES) - len(analyses)}"
    )

    return analyses


# ==========================================================================================
# FUNCTION SIGNATURES
# ==========================================================================================

def print_function_signatures(analyses):

    banner("FUNCTION SIGNATURES")

    targets = {
        "load_scores",
        "run",
        "build_decision_snapshot",
        "load_decisions",
        "load_features",
        "build_feature_snapshot",
        "load_feature_snapshot",
        "build_features",
    }

    for analysis in analyses:

        for fn in analysis.functions:

            if fn.name in targets:

                print(
                    f"{fn.file}:{fn.line}  "
                    f"{fn.name}("
                    f"{', '.join(fn.args)}"
                    f")"
                )


# ==========================================================================================
# REAL SCORE PRODUCER
# ==========================================================================================

def print_real_score_producer(analyses):

    banner("REAL SCORE PRODUCER TRACE")

    found = False

    for analysis in analyses:

        for fn in analysis.functions:

            if fn.name != "load_scores":
                continue

            if fn.file != "signal_scorer.py":
                continue

            found = True

            print(
                f"{fn.file}:{fn.line}  "
                f"FUNCTION : {fn.name}"
            )

            print(
                "ARGS     : "
                + ", ".join(fn.args)
            )

            real_inputs = {
                "bars_by_asset",
                "indicators_by_asset",
                "structures_by_asset",
            }

            present = [
                x for x in fn.args
                if x in real_inputs
            ]

            print(
                "REAL INPUTS : "
                + (
                    ", ".join(present)
                    if present
                    else "NONE"
                )
            )

            print(
                "ROLE     : REAL SCORE PRODUCER CANDIDATE"
            )

    if not found:
        print(
            "REAL SCORE PRODUCER : NOT FOUND"
        )


# ==========================================================================================
# LOAD_SCORE CALLS
# ==========================================================================================

def collect_load_score_calls(analyses):

    result = []

    for analysis in analyses:

        for call in analysis.calls:

            if call.callee == "load_scores":
                result.append(call)

            elif call.callee.endswith(".load_scores"):
                result.append(call)

    return result


def print_load_score_boundaries(analyses):

    banner("LOAD_SCORES CALL-CHAIN BOUNDARY")

    calls = collect_load_score_calls(analyses)

    zero = 0
    arg = 0

    for call in calls:

        print(
            f"{call.file}:{call.line}"
        )

        print(
            f"  CALLER : {call.caller}"
        )

        print(
            f"  CALLEE : {call.callee}"
        )

        if call.zero_arg:

            zero += 1

            print(
                "  ARGS   : <ZERO>"
            )

            print(
                "  STATUS : ZERO-ARG SCORE BOUNDARY"
            )

            print(
                "  REAL INPUTS PROPAGATED : NO"
            )

        else:

            arg += 1

            print(
                "  ARGS   : "
                + ", ".join(call.args)
            )

            print(
                "  STATUS : ARGUMENT SCORE BOUNDARY"
            )

            print(
                "  REAL INPUTS PROPAGATED : "
                + (
                    "YES"
                    if contains_real_input(call.args)
                    else "NO"
                )
            )

        print(
            f"  SOURCE : {call.source}"
        )

        print()

    print(
        f"TOTAL load_scores CALLS : {len(calls)}"
    )

    print(
        f"ZERO-ARG CALLS          : {zero}"
    )

    print(
        f"ARGUMENT CALLS          : {arg}"
    )


# ==========================================================================================
# SCORE VARIABLE FLOW
# ==========================================================================================

def print_score_variable_flow(analyses):

    banner("SCORE VARIABLE FLOW")

    for analysis in analyses:

        for assignment in analysis.assignments:

            if assignment.variable != "scores":
                continue

            print(
                f"{assignment.file}:{assignment.line}"
            )

            print(
                f"  FUNCTION : {assignment.function}"
            )

            print(
                f"  VARIABLE : {assignment.variable}"
            )

            print(
                f"  SOURCE   : {assignment.source}"
            )

            print()


# ==========================================================================================
# DECISION BRIDGE
# ==========================================================================================

def print_decision_bridge(analyses):

    banner("REAL SCORE → DECISION BRIDGE")

    bridge_calls = []

    for analysis in analyses:

        for call in analysis.calls:

            if (
                call.callee.endswith(
                    "build_decision_snapshot"
                )
            ):
                bridge_calls.append(call)

    if not bridge_calls:

        print(
            "DECISION BRIDGE : NOT FOUND"
        )

        return

    for call in bridge_calls:

        print(
            f"{call.file}:{call.line}"
        )

        print(
            f"  CALLER : {call.caller}"
        )

        print(
            f"  CALLEE : {call.callee}"
        )

        print(
            f"  ARGS   : "
            + ", ".join(call.args)
        )

        if contains_score_object(call.args):

            print(
                "  SCORE OBJECT : PRESENT"
            )

        else:

            print(
                "  SCORE OBJECT : NOT DIRECTLY PRESENT"
            )

        print(
            f"  SOURCE : {call.source}"
        )

        print()


# ==========================================================================================
# CRITICAL DECISION ENGINE PATH
# ==========================================================================================

def print_decision_engine_path(analyses):

    banner("CRITICAL DECISION ENGINE PATH")

    decision_analysis = None

    for analysis in analyses:

        if os.path.basename(
            analysis.path
        ) == "decision_engine.py":

            decision_analysis = analysis
            break

    if decision_analysis is None:

        print(
            "decision_engine.py : NOT FOUND"
        )

        return

    print(
        "TARGET : decision_engine.py"
    )

    print()

    for call in decision_analysis.calls:

        if (
            call.callee == "signal_scorer.load_scores"
            or call.callee == "load_scores"
            or call.callee.endswith(".load_scores")
        ):

            print(
                f"{call.file}:{call.line}"
            )

            print(
                f"  CALLER : {call.caller}"
            )

            print(
                f"  CALLEE : {call.callee}"
            )

            print(
                "  ARGS   : "
                + (
                    "<ZERO>"
                    if call.zero_arg
                    else ", ".join(call.args)
                )
            )

            if call.zero_arg:

                print(
                    "  >>> CRITICAL ZERO-ARG BREAK <<<"
                )

            print(
                f"  SOURCE : {call.source}"
            )

            print()


# ==========================================================================================
# RUNTIME BRIDGE CANDIDATES
# ==========================================================================================

def build_bridge_verdict(analyses):

    banner("BRIDGE VERDICT")

    real_producer = False
    producer_return = False

    zero_arg_decision_loader = False
    real_input_bridge = False
    decision_score_consumption = False

    # ------------------------------------------------------------------
    # Producer
    # ------------------------------------------------------------------

    for analysis in analyses:

        for fn in analysis.functions:

            if (
                fn.file == "signal_scorer.py"
                and fn.name == "load_scores"
            ):

                expected = {
                    "bars_by_asset",
                    "indicators_by_asset",
                    "structures_by_asset",
                }

                if expected.issubset(set(fn.args)):
                    real_producer = True

    # ------------------------------------------------------------------
    # Calls
    # ------------------------------------------------------------------

    for analysis in analyses:

        for call in analysis.calls:

            # Real producer invocation
            if (
                call.callee == "load_scores"
                and contains_real_input(call.args)
            ):
                real_input_bridge = True

            if (
                call.callee == "signal_scorer.load_scores"
                and call.zero_arg
            ):
                zero_arg_decision_loader = True

            # Decision builder
            if call.callee.endswith(
                "build_decision_snapshot"
            ):

                if contains_score_object(call.args):
                    decision_score_consumption = True

    # ------------------------------------------------------------------
    # Return path approximation
    # ------------------------------------------------------------------

    for analysis in analyses:

        for fn in analysis.functions:

            if (
                fn.file == "signal_scorer.py"
                and fn.name in {"load_scores", "run"}
            ):

                body = getattr(
                    fn.node,
                    "body",
                    [],
                )

                for node in ast.walk(
                    ast.Module(body=body, type_ignores=[])
                ):

                    if isinstance(
                        node,
                        ast.Return,
                    ):

                        if (
                            expr_to_text(
                                node.value
                            ) == "scores"
                        ):
                            producer_return = True

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------

    print(
        "REAL SCORE PRODUCER              : "
        + (
            "FOUND"
            if real_producer
            else "NOT FOUND"
        )
    )

    print(
        "REAL SCORE RETURN PATH           : "
        + (
            "FOUND"
            if producer_return
            else "NOT FOUND"
        )
    )

    print(
        "REAL INPUT → SCORE BRIDGE        : "
        + (
            "FOUND"
            if real_input_bridge
            else "NOT FOUND"
        )
    )

    print(
        "DECISION SCORE CONSUMPTION      : "
        + (
            "FOUND"
            if decision_score_consumption
            else "NOT FOUND"
        )
    )

    print(
        "DECISION ZERO-ARG LOADER        : "
        + (
            "FOUND"
            if zero_arg_decision_loader
            else "NOT FOUND"
        )
    )

    print()

    # ------------------------------------------------------------------
    # Final state
    # ------------------------------------------------------------------

    if (
        real_producer
        and producer_return
        and real_input_bridge
        and decision_score_consumption
        and zero_arg_decision_loader
    ):

        print(
            "STATUS : REAL SCORE PATH EXISTS BUT "
            "DECISION ZERO-ARG PATH ALSO EXISTS"
        )

        print(
            "BRIDGE STATUS : AMBIGUOUS / "
            "RUNTIME CALL-CHAIN VERIFICATION REQUIRED"
        )

    elif (
        real_producer
        and producer_return
        and real_input_bridge
        and decision_score_consumption
        and not zero_arg_decision_loader
    ):

        print(
            "STATUS : REAL SCORE BRIDGE STRUCTURALLY CONNECTED"
        )

        print(
            "BRIDGE STATUS : STRUCTURALLY VALID"
        )

    elif zero_arg_decision_loader:

        print(
            "STATUS : ZERO-ARG DECISION SCORE PATH EXISTS"
        )

        print(
            "BRIDGE STATUS : BROKEN / REQUIRES REPAIR"
        )

    else:

        print(
            "STATUS : BRIDGE INCOMPLETE"
        )

        print(
            "BRIDGE STATUS : REQUIRES DEEPER TRACE"
        )

    return {
        "real_producer": real_producer,
        "producer_return": producer_return,
        "real_input_bridge": real_input_bridge,
        "decision_score_consumption": decision_score_consumption,
        "zero_arg_decision_loader": zero_arg_decision_loader,
    }


# ==========================================================================================
# FIRST BREAK
# ==========================================================================================

def print_first_break(analyses):

    banner("FIRST ZERO-ARG SCORE BREAK")

    candidates = []

    for analysis in analyses:

        for call in analysis.calls:

            if call.zero_arg and (
                call.callee == "signal_scorer.load_scores"
                or call.callee == "load_scores"
                or call.callee.endswith(".load_scores")
            ):

                candidates.append(call)

    candidates.sort(
        key=lambda x: (
            x.file,
            x.line,
        )
    )

    if not candidates:

        print(
            "NO ZERO-ARG SCORE BREAK FOUND"
        )

        return

    first = candidates[0]

    print(
        f"FILE   : {first.file}"
    )

    print(
        f"LINE   : {first.line}"
    )

    print(
        f"CALLER : {first.caller}"
    )

    print(
        f"CALLEE : {first.callee}"
    )

    print(
        "ARGS   : <ZERO>"
    )

    print(
        f"SOURCE : {first.source}"
    )

    print()

    print(
        "VERDICT : ZERO-ARG SCORE BOUNDARY FOUND"
    )


# ==========================================================================================
# FINAL FORENSIC REPORT
# ==========================================================================================

def final_report(verdict, analyses):

    banner("FINAL FORENSIC REPORT")

    load_calls = collect_load_score_calls(
        analyses
    )

    zero_calls = [
        x
        for x in load_calls
        if x.zero_arg
    ]

    arg_calls = [
        x
        for x in load_calls
        if not x.zero_arg
    ]

    decision_zero = [
        x
        for x in zero_calls
        if (
            x.file == "decision_engine.py"
            or x.file == "risk_engine.py"
            or x.file == "execution_engine.py"
        )
    ]

    print(
        f"TOTAL load_scores CALLS          : "
        f"{len(load_calls)}"
    )

    print(
        f"ZERO-ARG load_scores CALLS       : "
        f"{len(zero_calls)}"
    )

    print(
        f"ARGUMENT load_scores CALLS       : "
        f"{len(arg_calls)}"
    )

    print(
        f"DECISION/RISK/EXEC ZERO-ARG CALLS: "
        f"{len(decision_zero)}"
    )

    print()

    print(
        "REAL SCORE PRODUCER              : "
        + (
            "FOUND"
            if verdict["real_producer"]
            else "NOT FOUND"
        )
    )

    print(
        "REAL SCORE RETURN PATH           : "
        + (
            "FOUND"
            if verdict["producer_return"]
            else "NOT FOUND"
        )
    )

    print(
        "REAL INPUT SCORE BRIDGE          : "
        + (
            "FOUND"
            if verdict["real_input_bridge"]
            else "NOT FOUND"
        )
    )

    print(
        "DECISION SCORE CONSUMPTION       : "
        + (
            "FOUND"
            if verdict["decision_score_consumption"]
            else "NOT FOUND"
        )
    )

    print(
        "DECISION ZERO-ARG BOUNDARY       : "
        + (
            "FOUND"
            if verdict["zero_arg_decision_loader"]
            else "NOT FOUND"
        )
    )

    print()

    if (
        verdict["real_producer"]
        and verdict["producer_return"]
        and verdict["real_input_bridge"]
        and verdict["decision_score_consumption"]
        and verdict["zero_arg_decision_loader"]
    ):

        print(
            "FINAL STATUS : "
            "REAL SCORE PRODUCER EXISTS; "
            "REAL SCORE OBJECT EXISTS; "
            "DECISION CONSUMER EXISTS; "
            "BUT ZERO-ARG DECISION BRIDGE EXISTS"
        )

        print(
            "NEXT STATE   : "
            "RUNTIME CALL-CHAIN VALIDATION REQUIRED"
        )

    elif (
        verdict["real_producer"]
        and verdict["producer_return"]
        and verdict["real_input_bridge"]
        and verdict["decision_score_consumption"]
    ):

        print(
            "FINAL STATUS : "
            "REAL SCORE BRIDGE STRUCTURALLY CONNECTED"
        )

        print(
            "NEXT STATE   : "
            "RUNTIME VALUE IDENTITY VALIDATION"
        )

    elif verdict["zero_arg_decision_loader"]:

        print(
            "FINAL STATUS : "
            "DECISION ZERO-ARG SCORE BOUNDARY EXISTS"
        )

        print(
            "NEXT STATE   : "
            "BRIDGE REPAIR / RUNTIME TRACE REQUIRED"
        )

    else:

        print(
            "FINAL STATUS : "
            "INCOMPLETE SCORE BRIDGE"
        )

    print()

    print(
        "DATABASE WRITE : NONE"
    )

    print(
        "PIPELINE RUN   : NONE"
    )

    print(
        "SOURCE EDIT    : NONE"
    )


# ==========================================================================================
# MAIN
# ==========================================================================================

def main():

    banner(
        "ARUNDA DECISION REAL SCORE RUNTIME BRIDGE TRACE v0.1"
    )

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "DB WRITE     : NONE"
    )

    print(
        "PIPELINE RUN : NONE"
    )

    print(
        "SOURCE EDIT  : NONE"
    )

    analyses = scan_project()

    if not analyses:

        print()
        print(
            "FATAL : No target files available."
        )
        return 1

    print_function_signatures(
        analyses
    )

    print_real_score_producer(
        analyses
    )

    print_load_score_boundaries(
        analyses
    )

    print_score_variable_flow(
        analyses
    )

    print_decision_bridge(
        analyses
    )

    print_decision_engine_path(
        analyses
    )

    print_first_break(
        analyses
    )

    verdict = build_bridge_verdict(
        analyses
    )

    final_report(
        verdict,
        analyses,
    )

    return 0


# ==========================================================================================
# ENTRY POINT
# ==========================================================================================

if __name__ == "__main__":

    try:
        sys.exit(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "INTERRUPTED BY USER"
        )

        sys.exit(130)

    except Exception as exc:

        print()
        print(
            "=" * 90
        )

        print(
            "UNEXPECTED FORENSIC ERROR"
        )

        print(
            "=" * 90
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        sys.exit(1)