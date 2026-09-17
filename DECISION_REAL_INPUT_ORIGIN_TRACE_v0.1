# -*- coding: utf-8 -*-

"""
==========================================================================================
DECISION_REAL_INPUT_ORIGIN_TRACE_v0.1
==========================================================================================

PURPOSE
-------
Trace the REAL production origin and propagation of:

    bars_by_asset
    indicators_by_asset
    structures_by_asset

toward:

    decision_engine
        -> load_scores()
        -> signal_scorer.load_scores(...)

MODE
----
READ ONLY
FORENSIC ONLY

SAFETY
------
- No production module execution
- No database writes
- No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP
- No pipeline execution
- No mutation of production objects
- Static source inspection only
- AST + textual lineage analysis

TARGET FILES
------------
arunda_pipeline.py
decision_engine.py
risk_engine.py
execution_engine.py
signal_scorer.py
feature_engine.py
feature_contract.py
feature_snapshot_reader.py
arunda_snapshot_feature_contract_v0_1.py

OUTPUT
------
For each target variable:

    VARIABLE
    PRODUCER
    PRODUCER FUNCTION
    PRODUCTION CALLER
    ARGUMENT PROPAGATION
    FIRST ZERO-ARG BREAK
    FIRST REAL-INPUT BREAK
    MISSING BRIDGE

IMPORTANT
---------
This script does NOT repair anything.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ==========================================================================================
# CONFIG
# ==========================================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

TARGET_FILES = [
    "arunda_pipeline.py",
    "decision_engine.py",
    "risk_engine.py",
    "execution_engine.py",
    "signal_scorer.py",
    "feature_engine.py",
    "feature_contract.py",
    "feature_snapshot_reader.py",
    "arunda_snapshot_feature_contract_v0_1.py",
]

TARGET_VARIABLES = [
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
]

TARGET_FUNCTIONS = [
    "load_scores",
    "load_features",
    "build_feature_snapshot",
    "load_feature_snapshot",
    "build_features",
    "run",
]


# ==========================================================================================
# DATA STRUCTURES
# ==========================================================================================

@dataclass
class FunctionInfo:
    file: str
    name: str
    lineno: int
    end_lineno: int
    args: list[str] = field(default_factory=list)


@dataclass
class VariableReference:
    file: str
    lineno: int
    function: Optional[str]
    kind: str
    variable: str
    source_line: str


@dataclass
class CallInfo:
    file: str
    lineno: int
    caller: Optional[str]
    callee: str
    args_count: int
    args_repr: list[str]
    source_line: str


# ==========================================================================================
# GLOBAL COLLECTIONS
# ==========================================================================================

FUNCTIONS: list[FunctionInfo] = []
VARIABLE_REFS: list[VariableReference] = []
CALLS: list[CallInfo] = []


# ==========================================================================================
# FILE HELPERS
# ==========================================================================================

def read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def safe_parse(source: str, filename: str):
    try:
        return ast.parse(source, filename=filename)
    except SyntaxError as exc:
        print(
            f"[SYNTAX-SKIP] {filename}: "
            f"line={exc.lineno} offset={exc.offset} msg={exc.msg}"
        )
        return None


def source_line(lines: list[str], lineno: int) -> str:
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


# ==========================================================================================
# AST HELPERS
# ==========================================================================================

def node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = node_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr

    return ""


def call_name(node: ast.Call) -> str:
    return node_name(node.func)


def function_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = []

    for arg in node.args.posonlyargs:
        args.append(arg.arg)

    for arg in node.args.args:
        args.append(arg.arg)

    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)

    for arg in node.args.kwonlyargs:
        args.append(arg.arg)

    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)

    return args


# ==========================================================================================
# FUNCTION DISCOVERY
# ==========================================================================================

class FunctionVisitor(ast.NodeVisitor):

    def __init__(self, filename: str):
        self.filename = filename
        self.stack: list[str] = []

    def visit_FunctionDef(self, node):
        self._record_function(node)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self._record_function(node)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def _record_function(self, node):
        FUNCTIONS.append(
            FunctionInfo(
                file=self.filename,
                name=node.name,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                args=args_to_names(node),
            )
        )


def args_to_names(node):
    return function_args(node)


# ==========================================================================================
# VARIABLE TRACE
# ==========================================================================================

class VariableVisitor(ast.NodeVisitor):

    def __init__(self, filename: str, lines: list[str]):
        self.filename = filename
        self.lines = lines
        self.function_stack: list[str] = []

    def visit_FunctionDef(self, node):
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def _record(self, node, variable: str, kind: str):
        VARIABLE_REFS.append(
            VariableReference(
                file=self.filename,
                lineno=node.lineno,
                function=self.function_stack[-1]
                if self.function_stack
                else None,
                kind=kind,
                variable=variable,
                source_line=source_line(self.lines, node.lineno),
            )
        )

    def visit_Name(self, node):
        if node.id in TARGET_VARIABLES:
            if isinstance(node.ctx, ast.Store):
                self._record(node, node.id, "ASSIGN")

            elif isinstance(node.ctx, ast.Load):
                self._record(node, node.id, "READ")

            elif isinstance(node.ctx, ast.Del):
                self._record(node, node.id, "DELETE")

        self.generic_visit(node)


# ==========================================================================================
# CALL TRACE
# ==========================================================================================

class CallVisitor(ast.NodeVisitor):

    def __init__(self, filename: str, lines: list[str]):
        self.filename = filename
        self.lines = lines
        self.function_stack: list[str] = []

    def visit_FunctionDef(self, node):
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Call(self, node):

        name = call_name(node)

        if not name:
            self.generic_visit(node)
            return

        interesting = (
            name.endswith(".load_scores")
            or name.endswith(".load_features")
            or name.endswith(".build_feature_snapshot")
            or name.endswith(".load_feature_snapshot")
            or name.endswith(".build_features")
            or name.endswith(".build_decision_snapshot")
            or name.endswith(".load_validated_signals")
            or name in TARGET_FUNCTIONS
        )

        if interesting:
            CALLS.append(
                CallInfo(
                    file=self.filename,
                    lineno=node.lineno,
                    caller=self.function_stack[-1]
                    if self.function_stack
                    else None,
                    callee=name,
                    args_count=len(node.args) + len(node.keywords),
                    args_repr=[
                        ast.unparse(arg)
                        for arg in node.args
                    ]
                    + [
                        f"{kw.arg}={ast.unparse(kw.value)}"
                        for kw in node.keywords
                    ],
                    source_line=source_line(self.lines, node.lineno),
                )
            )

        self.generic_visit(node)


# ==========================================================================================
# STATIC SCAN
# ==========================================================================================

def scan_file(path: Path):

    if not path.exists():
        print(f"[MISSING] {path.name}")
        return

    source = read_source(path)

    if not source:
        print(f"[EMPTY/UNREADABLE] {path.name}")
        return

    tree = safe_parse(source, path.name)

    if tree is None:
        return

    lines = source.splitlines()

    FunctionVisitor(path.name).visit(tree)
    VariableVisitor(path.name, lines).visit(tree)
    CallVisitor(path.name, lines).visit(tree)


# ==========================================================================================
# REPORT HELPERS
# ==========================================================================================

def section(title: str):
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_functions():

    section("FUNCTION SIGNATURES")

    for info in FUNCTIONS:

        if (
            info.name in TARGET_FUNCTIONS
            or any(
                variable in info.args
                for variable in TARGET_VARIABLES
            )
        ):
            print(
                f"{info.file}:{info.lineno}"
                f"  {info.name}("
                f"{', '.join(info.args)}"
                f")"
            )


def print_variable_refs():

    section("REAL INPUT VARIABLE REFERENCES")

    for variable in TARGET_VARIABLES:

        print()
        print(f"VARIABLE : {variable}")
        print("-" * 90)

        refs = [
            ref
            for ref in VARIABLE_REFS
            if ref.variable == variable
        ]

        if not refs:
            print("  NO REFERENCES FOUND")
            continue

        for ref in refs:

            print(
                f"  {ref.file}:{ref.lineno}"
                f"  FUNCTION={ref.function}"
                f"  KIND={ref.kind}"
            )

            print(
                f"      {ref.source_line}"
            )


def print_calls():

    section("PRODUCTION-CANDIDATE CALLS")

    for call in CALLS:

        print(
            f"{call.file}:{call.lineno}"
        )

        print(
            f"  CALLER : {call.caller}"
        )

        print(
            f"  CALLEE : {call.callee}"
        )

        print(
            f"  ARGS   : {call.args_count}"
        )

        if call.args_repr:
            for arg in call.args_repr:
                print(
                    f"      ARG : {arg}"
                )
        else:
            print(
                "      ARG : <ZERO>"
            )

        print(
            f"  SOURCE : {call.source_line}"
        )

        print()


# ==========================================================================================
# LOAD_SCORES SPECIFIC ANALYSIS
# ==========================================================================================

def print_load_scores_boundary():

    section("LOAD_SCORES BOUNDARY ANALYSIS")

    candidates = [
        c
        for c in CALLS
        if c.callee.endswith(".load_scores")
        or c.callee == "load_scores"
    ]

    if not candidates:
        print("NO load_scores() REFERENCES FOUND")
        return

    for call in candidates:

        print(
            f"{call.file}:{call.lineno}"
        )

        print(
            f"  CALLER : {call.caller}"
        )

        print(
            f"  CALLEE : {call.callee}"
        )

        if call.args_count == 0:

            print(
                "  STATUS : ZERO-ARG BOUNDARY"
            )

            print(
                "  VERDICT: REAL INPUTS ARE NOT PROPAGATED AT THIS CALL"
            )

        else:

            print(
                "  STATUS : ARGUMENTS PRESENT"
            )

            real_inputs = []

            for arg in call.args_repr:

                for variable in TARGET_VARIABLES:

                    if variable in arg:
                        real_inputs.append(variable)

            if real_inputs:

                print(
                    "  REAL INPUTS : "
                    + ", ".join(sorted(set(real_inputs)))
                )

                print(
                    "  VERDICT : REAL INPUT REFERENCES PRESENT"
                )

            else:

                print(
                    "  REAL INPUTS : NOT FOUND IN ARGUMENTS"
                )

                print(
                    "  VERDICT : INPUT PROPAGATION NOT PROVEN"
                )


# ==========================================================================================
# PRODUCER SEARCH
# ==========================================================================================

def print_producer_candidates():

    section("VARIABLE PRODUCER CANDIDATES")

    for variable in TARGET_VARIABLES:

        print()
        print(f"TARGET : {variable}")
        print("-" * 90)

        refs = [
            r
            for r in VARIABLE_REFS
            if r.variable == variable
            and r.kind == "ASSIGN"
        ]

        if not refs:

            print(
                "PRODUCER : NOT FOUND"
            )

            continue

        for ref in refs:

            print(
                f"PRODUCER CANDIDATE : "
                f"{ref.file}:{ref.lineno}"
            )

            print(
                f"FUNCTION            : {ref.function}"
            )

            print(
                f"SOURCE              : {ref.source_line}"
            )


# ==========================================================================================
# FIRST ZERO-ARG BREAK
# ==========================================================================================

def print_first_zero_arg_break():

    section("FIRST ZERO-ARG BREAK")

    zero_calls = [
        c
        for c in CALLS
        if (
            c.callee.endswith(".load_scores")
            or c.callee == "load_scores"
        )
        and c.args_count == 0
    ]

    if not zero_calls:

        print(
            "ZERO-ARG load_scores() CALL : NOT FOUND"
        )

        return

    zero_calls.sort(
        key=lambda x: (
            x.file,
            x.lineno
        )
    )

    first = zero_calls[0]

    print(
        f"FILE   : {first.file}"
    )

    print(
        f"LINE   : {first.lineno}"
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
        f"SOURCE : {first.source_line}"
    )

    print(
        "VERDICT: ZERO-ARG BREAK FOUND"
    )


# ==========================================================================================
# DECISION CHAIN
# ==========================================================================================

def print_decision_chain():

    section("DECISION RUNTIME CHAIN")

    chain_patterns = [
        ("risk_engine.py", "load_validated_signals"),
        ("risk_engine.py", "load_scores"),
        ("risk_engine.py", "build_decision_snapshot"),
        ("decision_engine.py", "load_scores"),
        ("decision_engine.py", "build_decision_snapshot"),
        ("execution_engine.py", "load_scores"),
        ("execution_engine.py", "build_decision_snapshot"),
    ]

    found = False

    for filename, function_name in chain_patterns:

        matches = [
            c
            for c in CALLS
            if c.file == filename
            and (
                c.callee.endswith(function_name)
                or c.callee == function_name
            )
        ]

        for call in matches:

            found = True

            print(
                f"{call.file}:{call.lineno}"
            )

            print(
                f"  {call.callee}"
            )

            print(
                f"  CALLER={call.caller}"
            )

            print(
                f"  ARGS={call.args_count}"
            )

            if call.args_repr:

                for arg in call.args_repr:
                    print(
                        f"      {arg}"
                    )

            else:

                print(
                    "      <ZERO>"
                )

    if not found:
        print(
            "DECISION CHAIN REFERENCES NOT FOUND"
        )


# ==========================================================================================
# FINAL VERDICT
# ==========================================================================================

def final_verdict():

    section("FINAL FORENSIC VERDICT")

    score_calls = [
        c
        for c in CALLS
        if (
            c.callee.endswith(".load_scores")
            or c.callee == "load_scores"
        )
    ]

    zero_score_calls = [
        c
        for c in score_calls
        if c.args_count == 0
    ]

    real_input_refs = [
        r
        for r in VARIABLE_REFS
        if r.variable in TARGET_VARIABLES
    ]

    producer_refs = [
        r
        for r in real_input_refs
        if r.kind == "ASSIGN"
    ]

    print(
        f"load_scores CALLS          : {len(score_calls)}"
    )

    print(
        f"ZERO-ARG load_scores CALLS : {len(zero_score_calls)}"
    )

    print(
        f"REAL INPUT REFERENCES      : {len(real_input_refs)}"
    )

    print(
        f"PRODUCER CANDIDATES        : {len(producer_refs)}"
    )

    print()

    if zero_score_calls:

        print(
            "DECISION ZERO-ARG LOADER : FOUND"
        )

    else:

        print(
            "DECISION ZERO-ARG LOADER : NOT FOUND"
        )

    if producer_refs:

        print(
            "REAL INPUT PRODUCER       : CANDIDATE FOUND"
        )

    else:

        print(
            "REAL INPUT PRODUCER       : NOT FOUND"
        )

    if real_input_refs:

        print(
            "REAL INPUT REFERENCES     : FOUND"
        )

    else:

        print(
            "REAL INPUT REFERENCES     : NOT FOUND"
        )

    print()

    if zero_score_calls and not producer_refs:

        print(
            "STATUS : BOUNDARY REPAIR REQUIRED"
        )

    elif zero_score_calls:

        print(
            "STATUS : ZERO-ARG BOUNDARY EXISTS; "
            "PRODUCER/BRIDGE TRACE REQUIRED"
        )

    elif producer_refs:

        print(
            "STATUS : REAL INPUT PATH CANDIDATE FOUND; "
            "ARGUMENT PROPAGATION MUST BE VERIFIED"
        )

    else:

        print(
            "STATUS : REAL INPUT ORIGIN NOT PROVEN"
        )


# ==========================================================================================
# MAIN
# ==========================================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA DECISION REAL INPUT ORIGIN TRACE v0.1"
    )
    print("=" * 90)

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

    print()

    print(
        "TARGET VARIABLES:"
    )

    for variable in TARGET_VARIABLES:
        print(
            f"  - {variable}"
        )

    print()

    print(
        "SCANNING TARGET FILES..."
    )

    for filename in TARGET_FILES:
        scan_file(
            PROJECT_ROOT / filename
        )

    print(
        "SCAN COMPLETE"
    )

    print_functions()

    print_producer_candidates()

    print_variable_refs()

    print_calls()

    print_load_scores_boundary()

    print_first_zero_arg_break()

    print_decision_chain()

    final_verdict()

    print()
    print("=" * 90)
    print("END")
    print("=" * 90)


if __name__ == "__main__":
    main()