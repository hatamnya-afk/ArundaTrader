# -*- coding: utf-8 -*-

"""
========================================================================================
ARUNDA TRADER — REAL FEATURE RUNTIME ORIGIN TO DECISION BRIDGE TRACE v0.1
========================================================================================

PURPOSE
-------
Trace the real runtime origin and propagation path of:

    bars_by_asset
    indicators_by_asset
    structures_by_asset

from their production/origin boundary through:

    signal_scorer.run()
        ->
    signal_scorer.load_scores()
        ->
    Decision Engine
        ->
    runtime caller chain

STRICT FORENSIC RULES
---------------------
MODE             : READ ONLY
EXECUTION        : STATIC AST ONLY
DB ACCESS        : NONE
WRITES           : NONE
SYNTHETIC        : FORBIDDEN
RISK ENGINE      : UNTOUCHED
PRODUCTION CODE  : UNTOUCHED

IMPORTANT
---------
This script does NOT execute production modules.
This script does NOT import production modules.
This script does NOT access SQLite.
This script does NOT infer missing runtime values.
This script only reconstructs static AST evidence.
========================================================================================
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Optional


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET_FEATURES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

TARGET_FUNCTIONS = {
    "run",
    "load_scores",
    "load_features",
    "build_feature_snapshot",
    "load_feature_snapshot",
    "build_features",
}

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


# ======================================================================================
# DATA STRUCTURES
# ======================================================================================

@dataclass
class FunctionInfo:
    file: str
    name: str
    line: int
    args: list[str] = field(default_factory=list)


@dataclass
class CallInfo:
    file: str
    function: str
    line: int
    callee: str
    args: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class AssignmentInfo:
    file: str
    function: str
    line: int
    target: str
    source: str
    source_type: str


# ======================================================================================
# AST HELPERS
# ======================================================================================

def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr

    return ""


def node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return dotted_name(node)

    if isinstance(node, ast.Call):
        return f"CALL:{dotted_name(node.func)}"

    if isinstance(node, ast.Subscript):
        return "SUBSCRIPT"

    if isinstance(node, ast.Constant):
        return repr(node.value)

    if isinstance(node, ast.Dict):
        return "DICT"

    if isinstance(node, ast.List):
        return "LIST"

    if isinstance(node, ast.Tuple):
        return "TUPLE"

    return type(node).__name__


def function_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    result = []

    for arg in node.args.posonlyargs:
        result.append(arg.arg)

    for arg in node.args.args:
        result.append(arg.arg)

    if node.args.vararg:
        result.append("*" + node.args.vararg.arg)

    for arg in node.args.kwonlyargs:
        result.append(arg.arg)

    if node.args.kwarg:
        result.append("**" + node.args.kwarg.arg)

    return result


def call_arguments(node: ast.Call) -> tuple[list[str], list[str]]:
    args = [node_name(x) for x in node.args]
    keywords = []

    for kw in node.keywords:
        if kw.arg is None:
            keywords.append("**" + node_name(kw.value))
        else:
            keywords.append(f"{kw.arg}={node_name(kw.value)}")

    return args, keywords


# ======================================================================================
# FILE DISCOVERY
# ======================================================================================

def discover_python_files(root: str) -> list[str]:
    files = []

    for current_root, dirs, filenames in os.walk(root):
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIRS
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                files.append(
                    os.path.join(current_root, filename)
                )

    return sorted(files)


# ======================================================================================
# SAFE AST PARSING
# ======================================================================================

def parse_file(path: str) -> Optional[ast.AST]:
    try:
        with open(
            path,
            "r",
            encoding="utf-8-sig",
            errors="strict",
        ) as f:
            source = f.read()

        return ast.parse(
            source,
            filename=path,
        )

    except (SyntaxError, UnicodeError, OSError):
        return None


# ======================================================================================
# RELATIVE PATH
# ======================================================================================

def rel(path: str) -> str:
    try:
        return os.path.relpath(path, PROJECT_ROOT)
    except ValueError:
        return path


# ======================================================================================
# COLLECT FUNCTION DEFINITIONS
# ======================================================================================

def collect_functions(
    path: str,
    tree: ast.AST,
) -> list[FunctionInfo]:

    results = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            results.append(
                FunctionInfo(
                    file=rel(path),
                    name=node.name,
                    line=node.lineno,
                    args=function_args(node),
                )
            )

    return results


# ======================================================================================
# COLLECT CALLS
# ======================================================================================

def collect_calls(
    path: str,
    tree: ast.AST,
) -> list[CallInfo]:

    results = []

    function_stack: list[str] = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):
            function_stack.append(node.name)
            self.generic_visit(node)
            function_stack.pop()

        def visit_AsyncFunctionDef(self, node):
            function_stack.append(node.name)
            self.generic_visit(node)
            function_stack.pop()

        def visit_Call(self, node):
            args, keywords = call_arguments(node)

            results.append(
                CallInfo(
                    file=rel(path),
                    function=function_stack[-1]
                    if function_stack
                    else "<module>",
                    line=node.lineno,
                    callee=dotted_name(node.func),
                    args=args,
                    keywords=keywords,
                )
            )

            self.generic_visit(node)

    Visitor().visit(tree)

    return results


# ======================================================================================
# COLLECT FEATURE ASSIGNMENTS / PROPAGATION
# ======================================================================================

def collect_assignments(
    path: str,
    tree: ast.AST,
) -> list[AssignmentInfo]:

    results = []

    function_stack: list[str] = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):
            function_stack.append(node.name)
            self.generic_visit(node)
            function_stack.pop()

        def visit_AsyncFunctionDef(self, node):
            function_stack.append(node.name)
            self.generic_visit(node)
            function_stack.pop()

        def record_assignment(self, node, target, value):
            target_name = node_name(target)

            if target_name not in TARGET_FEATURES:
                return

            source_name = node_name(value)

            if isinstance(value, ast.Call):
                source_type = "CALL"
            elif isinstance(value, ast.Name):
                source_type = "NAME"
            elif isinstance(value, ast.Attribute):
                source_type = "ATTRIBUTE"
            elif isinstance(value, ast.Subscript):
                source_type = "SUBSCRIPT"
            else:
                source_type = type(value).__name__

            results.append(
                AssignmentInfo(
                    file=rel(path),
                    function=function_stack[-1]
                    if function_stack
                    else "<module>",
                    line=node.lineno,
                    target=target_name,
                    source=source_name,
                    source_type=source_type,
                )
            )

        def visit_Assign(self, node):
            for target in node.targets:
                self.record_assignment(
                    node,
                    target,
                    node.value,
                )

            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            if node.value is not None:
                self.record_assignment(
                    node,
                    node.target,
                    node.value,
                )

            self.generic_visit(node)

        def visit_NamedExpr(self, node):
            self.record_assignment(
                node,
                node.target,
                node.value,
            )

            self.generic_visit(node)

    Visitor().visit(tree)

    return results


# ======================================================================================
# FEATURE REFERENCE SEARCH
# ======================================================================================

def feature_references(
    path: str,
    tree: ast.AST,
) -> list[tuple[int, str, str]]:

    results = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Name):
            if node.id in TARGET_FEATURES:
                results.append(
                    (
                        node.lineno,
                        node.id,
                        "Name",
                    )
                )

        elif isinstance(node, ast.arg):
            if node.arg in TARGET_FEATURES:
                results.append(
                    (
                        node.lineno,
                        node.arg,
                        "Parameter",
                    )
                )

    return sorted(results)


# ======================================================================================
# MAIN ANALYSIS
# ======================================================================================

def main():

    print("=" * 88)
    print(
        "ARUNDA TRADER — REAL FEATURE RUNTIME ORIGIN "
        "TO DECISION BRIDGE TRACE v0.1"
    )
    print("=" * 88)
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ ONLY")
    print("EXECUTION    : STATIC AST ONLY")
    print("DB ACCESS    : NONE")
    print("WRITES       : NONE")
    print("SYNTHETIC    : FORBIDDEN")
    print("RISK ENGINE  : UNTOUCHED")
    print("=" * 88)

    files = discover_python_files(PROJECT_ROOT)

    print(f"Python files discovered : {len(files)}")

    parsed = []
    syntax_failures = []

    all_functions: list[FunctionInfo] = []
    all_calls: list[CallInfo] = []
    all_assignments: list[AssignmentInfo] = []

    # ------------------------------------------------------------------
    # PARSE
    # ------------------------------------------------------------------

    for path in files:

        tree = parse_file(path)

        if tree is None:
            syntax_failures.append(rel(path))
            continue

        parsed.append(path)

        all_functions.extend(
            collect_functions(path, tree)
        )

        all_calls.extend(
            collect_calls(path, tree)
        )

        all_assignments.extend(
            collect_assignments(path, tree)
        )

    print(f"Files parsed            : {len(parsed)}")
    print(f"Syntax failures         : {len(syntax_failures)}")

    # ==================================================================================
    # TARGET FUNCTION MAP
    # ==================================================================================

    print()
    print("=" * 88)
    print("TARGET FUNCTION MAP")
    print("=" * 88)

    for fn in all_functions:

        if fn.name not in TARGET_FUNCTIONS:
            continue

        print(
            f"{fn.file:<65} "
            f"{fn.name:<25} "
            f"line={fn.line}"
        )

        if fn.args:
            print(
                f"  args={fn.args}"
            )

    # ==================================================================================
    # SIGNAL SCORER RUNTIME ENTRY
    # ==================================================================================

    print()
    print("=" * 88)
    print("SIGNAL SCORER RUNTIME ENTRY")
    print("=" * 88)

    scorer_run_calls = [
        c for c in all_calls
        if c.callee.endswith("signal_scorer.run")
        or c.callee == "run"
    ]

    if scorer_run_calls:

        for c in scorer_run_calls:
            print(
                f"{c.file}:{c.line} "
                f"{c.function}() -> {c.callee}()"
            )
            print(
                f"  args     = {c.args}"
            )
            print(
                f"  keywords = {c.keywords}"
            )

    else:
        print("NO signal_scorer.run() CALL FOUND")

    # ==================================================================================
    # FEATURE INPUT ORIGIN / ASSIGNMENT CANDIDATES
    # ==================================================================================

    print()
    print("=" * 88)
    print("REAL FEATURE OBJECT ORIGIN / ASSIGNMENT CANDIDATES")
    print("=" * 88)

    origin_hits = [
        a for a in all_assignments
        if a.target in TARGET_FEATURES
    ]

    if not origin_hits:

        print(
            "NO DIRECT ASSIGNMENT TO TARGET FEATURE OBJECTS FOUND"
        )

    else:

        for a in origin_hits:

            print()
            print(
                f"{a.file}:{a.line}"
            )
            print(
                f"  function    = {a.function}"
            )
            print(
                f"  target      = {a.target}"
            )
            print(
                f"  source      = {a.source}"
            )
            print(
                f"  source_type = {a.source_type}"
            )

    # ==================================================================================
    # CALLS PROPAGATING FEATURE OBJECTS
    # ==================================================================================

    print()
    print("=" * 88)
    print("CALLS PROPAGATING REAL FEATURE OBJECTS")
    print("=" * 88)

    propagation_hits = []

    for c in all_calls:

        joined = " ".join(
            c.args + c.keywords
        )

        matched = [
            feature
            for feature in TARGET_FEATURES
            if feature in joined
        ]

        if matched:
            propagation_hits.append(
                (c, matched)
            )

    if not propagation_hits:

        print("NO FEATURE PROPAGATION CALLS FOUND")

    else:

        for c, matched in propagation_hits:

            print()
            print(
                f"{c.file}:{c.line}"
            )
            print(
                f"  function = {c.function}"
            )
            print(
                f"  callee   = {c.callee}"
            )
            print(
                f"  features = {matched}"
            )
            print(
                f"  args     = {c.args}"
            )
            print(
                f"  keywords = {c.keywords}"
            )

    # ==================================================================================
    # EXACT SCORER BRIDGE
    # ==================================================================================

    print()
    print("=" * 88)
    print("EXACT SIGNAL SCORER FEATURE BRIDGE")
    print("=" * 88)

    exact_bridges = []

    for c in all_calls:

        if c.callee not in {
            "load_scores",
            "signal_scorer.load_scores",
        }:
            continue

        matched = [
            feature
            for feature in TARGET_FEATURES
            if feature in c.args
        ]

        if len(matched) == 3:
            exact_bridges.append(c)

    if exact_bridges:

        for c in exact_bridges:

            print(
                f"FOUND COMPLETE BRIDGE"
            )
            print(
                f"  file     = {c.file}"
            )
            print(
                f"  function = {c.function}"
            )
            print(
                f"  line     = {c.line}"
            )
            print(
                f"  callee   = {c.callee}"
            )
            print(
                f"  args     = {c.args}"
            )

    else:

        print(
            "NO COMPLETE STATIC FEATURE → load_scores BRIDGE FOUND"
        )

    # ==================================================================================
    # DECISION ENGINE BOUNDARY
    # ==================================================================================

    print()
    print("=" * 88)
    print("DECISION ENGINE SCORE BOUNDARY")
    print("=" * 88)

    decision_calls = [
        c for c in all_calls
        if c.file == "decision_engine.py"
        and (
            c.callee == "load_scores"
            or c.callee == "signal_scorer.load_scores"
        )
    ]

    if decision_calls:

        for c in decision_calls:

            print(
                f"{c.file}:{c.line}"
            )
            print(
                f"  function = {c.function}"
            )
            print(
                f"  callee   = {c.callee}"
            )
            print(
                f"  args     = {c.args}"
            )
            print(
                f"  keywords = {c.keywords}"
            )

    else:

        print(
            "NO DECISION ENGINE SCORE CALL FOUND"
        )

    # ==================================================================================
    # FUNCTION SIGNATURE VERIFICATION
    # ==================================================================================

    print()
    print("=" * 88)
    print("FEATURE SIGNATURE VERIFICATION")
    print("=" * 88)

    for fn in all_functions:

        if fn.name not in {
            "run",
            "load_scores",
            "load_features",
        }:
            continue

        matched = [
            feature
            for feature in TARGET_FEATURES
            if feature in fn.args
        ]

        if matched:

            print()
            print(
                f"{fn.file}:{fn.line} {fn.name}()"
            )
            print(
                f"  feature args = {matched}"
            )

            if len(matched) == 3:
                print(
                    "  STATUS       = COMPLETE"
                )
            else:
                print(
                    "  STATUS       = PARTIAL"
                )

    # ==================================================================================
    # STATIC CHAIN RECONSTRUCTION
    # ==================================================================================

    print()
    print("=" * 88)
    print("STATIC RUNTIME CHAIN RECONSTRUCTION")
    print("=" * 88)

    print(
        """
REAL FEATURE ORIGIN
        |
        v
bars_by_asset
indicators_by_asset
structures_by_asset
        |
        v
signal_scorer.run(...)
        |
        v
signal_scorer.load_scores(...)
        |
        v
Decision Engine
        |
        v
build_decision_snapshot(...)
        |
        v
Risk / Execution boundary
""".rstrip()
    )

    # ==================================================================================
    # FORENSIC VERDICT
    # ==================================================================================

    complete_feature_signature = any(
        fn.name in {"run", "load_scores"}
        and TARGET_FEATURES.issubset(set(fn.args))
        for fn in all_functions
    )

    complete_bridge = bool(exact_bridges)

    scorer_entry = bool(scorer_run_calls)

    print()
    print("=" * 88)
    print("FORENSIC VERDICT")
    print("=" * 88)

    print(
        "Signal scorer runtime entry : "
        f"{'FOUND' if scorer_entry else 'NOT FOUND'}"
    )

    print(
        "Complete feature signature  : "
        f"{'FOUND' if complete_feature_signature else 'NOT FOUND'}"
    )

    print(
        "Feature → scorer bridge     : "
        f"{'FOUND' if complete_bridge else 'NOT FOUND'}"
    )

    print(
        "Decision score boundary     : "
        f"{'FOUND' if decision_calls else 'NOT FOUND'}"
    )

    print()

    if scorer_entry and complete_bridge and decision_calls:

        print(
            "RESULT : REAL FEATURE RUNTIME BRIDGE "
            "IS STATICALLY TRACEABLE"
        )

        print()
        print(
            "NEXT ACTION:"
        )
        print(
            "Trace the caller of signal_scorer.run() "
            "to identify the actual producer of:"
        )
        print(
            "  bars_by_asset"
        )
        print(
            "  indicators_by_asset"
        )
        print(
            "  structures_by_asset"
        )

    elif scorer_entry and complete_feature_signature:

        print(
            "RESULT : SCORER FEATURE BOUNDARY FOUND; "
            "ORIGIN TRACE REMAINS OPEN"
        )

        print()
        print(
            "NEXT ACTION:"
        )
        print(
            "Trace upstream callers and assignments only."
        )

    else:

        print(
            "RESULT : REAL FEATURE ORIGIN NOT YET PROVEN"
        )

        print()
        print(
            "NEXT ACTION:"
        )
        print(
            "Continue static upstream trace."
        )

    print()
    print("=" * 88)
    print("M4 STATUS : COMPLETE")
    print("=" * 88)


if __name__ == "__main__":
    main()