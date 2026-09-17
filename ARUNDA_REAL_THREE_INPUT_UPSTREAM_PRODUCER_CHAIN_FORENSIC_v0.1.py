# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER — REAL THREE INPUT UPSTREAM PRODUCER CHAIN FORENSIC v0.1
====================================================================================================

MODE         : READ ONLY / STATIC FORENSIC
IMPORTS      : NONE FROM PROJECT
EXECUTION    : NONE
DATABASE     : NOT TOUCHED
SOURCE EDIT  : NONE

TARGETS:
    bars_by_asset
    indicators_by_asset
    structures_by_asset

PURPOSE:
    Find the FIRST production assignment / population point for each target mapping,
    then trace the immediate static caller chain.

IMPORTANT:
    This script does NOT import project modules.
    This script does NOT execute project functions.
    This script does NOT access the database.
====================================================================================================
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ================================================================================================
# CONFIG
# ================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = (
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
)

MAX_SOURCE_PREVIEW = 700


# ================================================================================================
# CLASSIFICATION
# ================================================================================================

EXCLUDE_NAME_PATTERNS = (
    "forensic",
    "diagnostic",
    "audit",
    "test",
    "backup",
    "broken",
    "pre_step",
    "quarantine",
    "corrupt",
    "repair",
    "reconciliation",
    "validation",
    "quality",
)

EXCLUDE_DIR_PATTERNS = (
    "__pycache__",
    ".git",
    "_quarantine",
    "quarantine",
    "backup",
    "backups",
    "archive",
    "archives",
)

PRODUCTION_HINTS = (
    "engine",
    "runtime",
    "pipeline",
    "loader",
    "producer",
    "builder",
    "collector",
    "scheduler",
    "market",
    "signal",
    "feature",
    "structure",
    "indicator",
    "technical",
    "analysis",
)


# ================================================================================================
# DATA CLASSES
# ================================================================================================

@dataclass
class Occurrence:
    file: str
    line: int
    function: str
    target: str
    kind: str
    source: str
    score: int = 0
    excluded: bool = False
    reason: str = ""


@dataclass
class FunctionInfo:
    file: str
    name: str
    qualname: str
    line: int
    end_line: int
    parent: Optional[str] = None
    calls: list[str] = field(default_factory=list)
    targets: set[str] = field(default_factory=set)


@dataclass
class FileInfo:
    path: str
    functions: list[FunctionInfo] = field(default_factory=list)
    occurrences: list[Occurrence] = field(default_factory=list)
    parse_error: Optional[str] = None


# ================================================================================================
# HELPERS
# ================================================================================================

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def source_segment(source: str, node: ast.AST) -> str:
    try:
        segment = ast.get_source_segment(source, node)
        if segment:
            return normalize(segment)[:MAX_SOURCE_PREVIEW]
    except Exception:
        pass
    return ""


def line_of(node: ast.AST) -> int:
    return int(getattr(node, "lineno", 0) or 0)


def end_line_of(node: ast.AST) -> int:
    return int(getattr(node, "end_lineno", line_of(node)) or line_of(node))


def path_is_excluded(path: Path) -> tuple[bool, str]:
    name = path.name.lower()
    parts = [p.lower() for p in path.parts]

    for token in EXCLUDE_DIR_PATTERNS:
        if token in parts:
            return True, f"excluded directory: {token}"

    for token in EXCLUDE_NAME_PATTERNS:
        if token in name:
            return True, f"excluded filename pattern: {token}"

    return False, ""


def production_score(path: Path, function_name: str) -> int:
    score = 0

    name = path.name.lower()
    fn = function_name.lower()

    if "audit" not in name:
        score += 10

    if not any(x in name for x in EXCLUDE_NAME_PATTERNS):
        score += 20

    for hint in PRODUCTION_HINTS:
        if hint in name:
            score += 3

    for hint in PRODUCTION_HINTS:
        if hint in fn:
            score += 2

    return score


def is_target_name(name: str) -> bool:
    return name in TARGETS


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr

    return ""


# ================================================================================================
# AST CONTEXT
# ================================================================================================

class ASTScanner(ast.NodeVisitor):

    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source

        self.current_function: list[str] = []

        self.functions: list[FunctionInfo] = []
        self.occurrences: list[Occurrence] = []

        self._function_stack: list[FunctionInfo] = []

    # --------------------------------------------------------------------------------------------
    # FUNCTION
    # --------------------------------------------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def _visit_function(self, node):

        parent = self._function_stack[-1].qualname if self._function_stack else None

        qualname = node.name
        if parent:
            qualname = f"{parent}.{node.name}"

        info = FunctionInfo(
            file=str(self.path),
            name=node.name,
            qualname=qualname,
            line=line_of(node),
            end_line=end_line_of(node),
            parent=parent,
        )

        self.functions.append(info)
        self._function_stack.append(info)

        # Inspect parameters.
        for arg in list(node.args.args) + list(node.args.kwonlyargs):
            if arg.arg in TARGETS:
                info.targets.add(arg.arg)

        if node.args.vararg and node.args.vararg.arg in TARGETS:
            info.targets.add(node.args.vararg.arg)

        if node.args.kwarg and node.args.kwarg.arg in TARGETS:
            info.targets.add(node.args.kwarg.arg)

        self.generic_visit(node)

        self._function_stack.pop()

    # --------------------------------------------------------------------------------------------
    # CALLS
    # --------------------------------------------------------------------------------------------

    def visit_Call(self, node: ast.Call):

        fn = self._function_stack[-1] if self._function_stack else None

        callee = dotted_name(node.func)

        if fn and callee:
            fn.calls.append(callee)

        self.generic_visit(node)

    # --------------------------------------------------------------------------------------------
    # ASSIGNMENTS
    # --------------------------------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign):

        fn = self._function_stack[-1] if self._function_stack else None
        function_name = fn.qualname if fn else "<module>"

        for target in node.targets:
            self._inspect_assignment(
                target,
                node.value,
                function_name,
                node,
            )

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):

        fn = self._function_stack[-1] if self._function_stack else None
        function_name = fn.qualname if fn else "<module>"

        self._inspect_assignment(
            node.target,
            node.value,
            function_name,
            node,
        )

        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr):

        fn = self._function_stack[-1] if self._function_stack else None
        function_name = fn.qualname if fn else "<module>"

        self._inspect_assignment(
            node.target,
            node.value,
            function_name,
            node,
        )

        self.generic_visit(node)

    # --------------------------------------------------------------------------------------------
    # SUBSCRIPT POPULATION
    # --------------------------------------------------------------------------------------------

    def visit_Subscript(self, node: ast.Subscript):

        target_name = dotted_name(node.value)

        if target_name in TARGETS:

            fn = self._function_stack[-1] if self._function_stack else None
            function_name = fn.qualname if fn else "<module>"

            context = source_segment(self.source, node)

            self._record(
                target=target_name,
                kind="SUBSCRIPT_ACCESS_OR_POPULATION",
                source=context,
                node=node,
                function_name=function_name,
            )

        self.generic_visit(node)

    # --------------------------------------------------------------------------------------------
    # ATTRIBUTE / METHOD MUTATION
    # --------------------------------------------------------------------------------------------

    def visit_Call_mutation_helper(self, node: ast.Call):
        pass

    # --------------------------------------------------------------------------------------------
    # RECORD ASSIGNMENT
    # --------------------------------------------------------------------------------------------

    def _inspect_assignment(
        self,
        target_node: ast.AST,
        value_node: Optional[ast.AST],
        function_name: str,
        node: ast.AST,
    ):

        target_name = dotted_name(target_node)

        if target_name in TARGETS:

            source = source_segment(self.source, value_node) if value_node else ""

            self._record(
                target=target_name,
                kind="DIRECT_ASSIGNMENT",
                source=f"{target_name} = {source}",
                node=node,
                function_name=function_name,
            )

        # Handle tuple/list unpacking:
        if isinstance(target_node, (ast.Tuple, ast.List)):
            for item in target_node.elts:
                item_name = dotted_name(item)

                if item_name in TARGETS:

                    source = source_segment(self.source, value_node)

                    self._record(
                        target=item_name,
                        kind="UNPACK_ASSIGNMENT",
                        source=f"{item_name} <- {source}",
                        node=node,
                        function_name=function_name,
                    )

    # --------------------------------------------------------------------------------------------
    # GENERIC CALL MUTATION DETECTION
    # --------------------------------------------------------------------------------------------

    def visit_Call(self, node: ast.Call):

        fn = self._function_stack[-1] if self._function_stack else None
        function_name = fn.qualname if fn else "<module>"

        callee = dotted_name(node.func)

        if fn and callee:
            fn.calls.append(callee)

        # target.setdefault(...)
        if isinstance(node.func, ast.Attribute):
            base = dotted_name(node.func.value)

            if base in TARGETS and node.func.attr in {
                "setdefault",
                "update",
                "setdefault",
                "clear",
                "pop",
                "popitem",
            }:

                self._record(
                    target=base,
                    kind=f"MUTATION_CALL:{node.func.attr}",
                    source=source_segment(self.source, node),
                    node=node,
                    function_name=function_name,
                )

        self.generic_visit(node)

    # --------------------------------------------------------------------------------------------
    # RECORD
    # --------------------------------------------------------------------------------------------

    def _record(
        self,
        target: str,
        kind: str,
        source: str,
        node: ast.AST,
        function_name: str,
    ):

        score = production_score(self.path, function_name)

        self.occurrences.append(
            Occurrence(
                file=str(self.path),
                line=line_of(node),
                function=function_name,
                target=target,
                kind=kind,
                source=source,
                score=score,
            )
        )


# ================================================================================================
# SCAN
# ================================================================================================

def scan_file(path: Path) -> FileInfo:

    info = FileInfo(path=str(path))

    try:
        raw = path.read_bytes()

        # Handle UTF-8 BOM safely without modifying source.
        source = raw.decode("utf-8-sig")

        tree = ast.parse(
            source,
            filename=str(path),
            type_comments=True,
        )

        scanner = ASTScanner(path, source)
        scanner.visit(tree)

        info.functions = scanner.functions
        info.occurrences = scanner.occurrences

    except SyntaxError as exc:
        info.parse_error = (
            f"SyntaxError: {exc.msg} "
            f"(line {exc.lineno})"
        )

    except Exception as exc:
        info.parse_error = f"{type(exc).__name__}: {exc}"

    return info


def scan_project():

    files = []

    for path in PROJECT_ROOT.rglob("*.py"):

        excluded, _ = path_is_excluded(path)

        if excluded:
            continue

        files.append(path)

    files.sort(
        key=lambda p: (
            len(p.parts),
            str(p).lower(),
        )
    )

    results = []

    for path in files:
        results.append(scan_file(path))

    return results


# ================================================================================================
# FILTER / RANK
# ================================================================================================

def classify_occurrence(occ: Occurrence):

    path = Path(occ.file)

    excluded, reason = path_is_excluded(path)

    if excluded:
        occ.excluded = True
        occ.reason = reason
        return

    text = (
        f"{path.name} "
        f"{occ.function} "
        f"{occ.source}"
    ).lower()

    # Audit/test contamination.
    contamination = (
        "audit",
        "test",
        "forensic",
        "diagnostic",
        "validation",
        "assert",
        "fixture",
        "mock",
        "synthetic",
    )

    for token in contamination:
        if token in text:
            occ.score -= 25

    # Strong production indicators.
    for token in (
        "producer",
        "loader",
        "runtime",
        "pipeline",
        "engine",
        "build",
        "create",
        "assemble",
        "collect",
        "calculate",
        "generate",
    ):
        if token in text:
            occ.score += 5

    # Direct mapping creation gets strong weight.
    if occ.kind == "DIRECT_ASSIGNMENT":
        occ.score += 20

    elif occ.kind == "UNPACK_ASSIGNMENT":
        occ.score += 18

    elif occ.kind.startswith("MUTATION_CALL"):
        occ.score += 15

    elif occ.kind == "SUBSCRIPT_ACCESS_OR_POPULATION":
        occ.score += 5


def rank_occurrences(results):

    all_occurrences = []

    for result in results:

        for occ in result.occurrences:

            classify_occurrence(occ)

            if not occ.excluded:
                all_occurrences.append(occ)

    all_occurrences.sort(
        key=lambda x: (
            -x.score,
            x.file.lower(),
            x.line,
        )
    )

    return all_occurrences


# ================================================================================================
# FUNCTION INDEX
# ================================================================================================

def build_function_index(results):

    index = {}

    for result in results:
        for fn in result.functions:
            index.setdefault(fn.name, []).append(fn)
            index.setdefault(fn.qualname, []).append(fn)

    return index


# ================================================================================================
# STATIC CALLER SEARCH
# ================================================================================================

def find_callers(results, target_function_name):

    callers = []

    short_name = target_function_name.split(".")[-1]

    for result in results:

        for fn in result.functions:

            for call in fn.calls:

                call_short = call.split(".")[-1]

                if call == target_function_name or call_short == short_name:

                    callers.append(
                        (
                            fn.file,
                            fn.qualname,
                            fn.line,
                            call,
                        )
                    )

    return callers


def caller_chain(results, function_name, max_depth=8):

    chain = []

    current = function_name
    visited = set()

    for _ in range(max_depth):

        if current in visited:
            break

        visited.add(current)

        callers = find_callers(results, current)

        if not callers:
            break

        # Prefer production-looking caller.
        callers.sort(
            key=lambda x: (
                -production_score(Path(x[0]), x[1]),
                x[0].lower(),
                x[2],
            )
        )

        selected = callers[0]

        chain.append(selected)

        current = selected[1]

    return chain


# ================================================================================================
# GROUPING
# ================================================================================================

def best_by_target(occurrences):

    grouped = {
        target: []
        for target in TARGETS
    }

    for occ in occurrences:
        grouped[occ.target].append(occ)

    for target in grouped:
        grouped[target].sort(
            key=lambda x: (
                -x.score,
                x.line,
            )
        )

    return grouped


# ================================================================================================
# OUTPUT
# ================================================================================================

def print_header():

    print("=" * 100)
    print("ARUNDA TRADER — REAL THREE INPUT UPSTREAM PRODUCER CHAIN FORENSIC v0.1")
    print("=" * 100)
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ ONLY / STATIC FORENSIC")
    print("IMPORTS      : NONE FROM PROJECT")
    print("EXECUTION    : NONE")
    print("DATABASE     : NOT TOUCHED")
    print("SOURCE EDIT  : NONE")
    print("=" * 100)


def print_target_report(target, occurrences, results):

    print()
    print("=" * 100)
    print(f"TARGET : {target}")
    print("=" * 100)

    if not occurrences:
        print("NO CANDIDATES FOUND.")
        return

    print()
    print("TOP PRODUCTION CANDIDATES")
    print("-" * 100)

    for idx, occ in enumerate(occurrences[:15], 1):

        print()
        print(f"[{idx}] SCORE : {occ.score}")
        print(f"FILE     : {occ.file}")
        print(f"LINE     : {occ.line}")
        print(f"FUNCTION : {occ.function}")
        print(f"KIND     : {occ.kind}")
        print(f"SOURCE   : {occ.source}")

    # Caller trace for strongest direct assignment.
    direct = [
        x for x in occurrences
        if x.kind in {
            "DIRECT_ASSIGNMENT",
            "UNPACK_ASSIGNMENT",
        }
    ]

    if not direct:
        print()
        print("NO DIRECT ASSIGNMENT CANDIDATE.")
        return

    owner = direct[0]

    print()
    print("-" * 100)
    print("STRONGEST DIRECT ASSIGNMENT")
    print("-" * 100)
    print(f"FILE     : {owner.file}")
    print(f"LINE     : {owner.line}")
    print(f"FUNCTION : {owner.function}")
    print(f"SCORE    : {owner.score}")
    print(f"SOURCE   : {owner.source}")

    print()
    print("-" * 100)
    print("STATIC CALLER CHAIN")
    print("-" * 100)

    chain = caller_chain(
        results,
        owner.function,
        max_depth=8,
    )

    if not chain:
        print("NO STATIC CALLER FOUND.")
        return

    print(f"OWNER FUNCTION : {owner.function}")

    for idx, caller in enumerate(chain, 1):

        file_name, fn_name, line, call = caller

        print(
            f"{idx}. "
            f"{file_name} :: {fn_name} "
            f"(line {line}) "
            f"CALL={call}"
        )


def print_cross_target_candidates(grouped):

    print()
    print("=" * 100)
    print("CROSS-TARGET PRODUCTION FUNCTIONS")
    print("=" * 100)

    by_function = {}

    for target in TARGETS:

        for occ in grouped[target]:

            key = (
                occ.file,
                occ.function,
            )

            by_function.setdefault(key, set()).add(target)

    rows = []

    for (file_name, function_name), targets in by_function.items():

        if len(targets) >= 2:

            score = 0

            for target in targets:

                candidates = [
                    x
                    for x in grouped[target]
                    if x.file == file_name
                    and x.function == function_name
                ]

                if candidates:
                    score = max(
                        score,
                        max(x.score for x in candidates)
                    )

            rows.append(
                (
                    score,
                    file_name,
                    function_name,
                    sorted(targets),
                )
            )

    rows.sort(
        key=lambda x: (
            -x[0],
            x[1].lower(),
            x[2],
        )
    )

    if not rows:
        print("NO CROSS-TARGET PRODUCTION FUNCTION FOUND.")
        return

    for idx, row in enumerate(rows, 1):

        score, file_name, function_name, targets = row

        print()
        print(f"[{idx}] SCORE    : {score}")
        print(f"FILE       : {file_name}")
        print(f"FUNCTION   : {function_name}")
        print(f"TARGETS    : {targets}")


def print_parse_errors(results):

    errors = [
        r for r in results
        if r.parse_error
    ]

    print()
    print("=" * 100)
    print("PARSE ERRORS")
    print("=" * 100)
    print(f"Parse errors : {len(errors)}")

    for result in errors:
        print(
            f"{result.path} -> "
            f"{result.parse_error}"
        )


def print_summary(results, occurrences, grouped):

    print()
    print("=" * 100)
    print("FORENSIC SUMMARY")
    print("=" * 100)

    print(f"PYTHON FILES SCANNED       : {len(results)}")
    print(f"TARGET OCCURRENCES         : {len(occurrences)}")

    for target in TARGETS:

        direct = [
            x for x in grouped[target]
            if x.kind in {
                "DIRECT_ASSIGNMENT",
                "UNPACK_ASSIGNMENT",
            }
        ]

        mutation = [
            x for x in grouped[target]
            if x.kind.startswith("MUTATION_CALL")
        ]

        print()
        print(f"{target}")
        print(f"  total candidates          : {len(grouped[target])}")
        print(f"  direct assignments       : {len(direct)}")
        print(f"  mutation calls            : {len(mutation)}")

        if direct:

            best = direct[0]

            print("  strongest assignment:")
            print(f"    FILE     : {best.file}")
            print(f"    LINE     : {best.line}")
            print(f"    FUNCTION : {best.function}")
            print(f"    SCORE    : {best.score}")
            print(f"    SOURCE   : {best.source}")

        else:

            print("  strongest assignment: NONE")

    print()
    print("=" * 100)
    print("INTERPRETATION")
    print("=" * 100)

    direct_by_target = {}

    for target in TARGETS:

        direct = [
            x for x in grouped[target]
            if x.kind in {
                "DIRECT_ASSIGNMENT",
                "UNPACK_ASSIGNMENT",
            }
        ]

        direct_by_target[target] = direct

    if all(direct_by_target[target] for target in TARGETS):

        print(
            "DIRECT PRODUCTION ASSIGNMENTS FOUND FOR ALL THREE TARGETS."
        )

    else:

        missing = [
            target
            for target in TARGETS
            if not direct_by_target[target]
        ]

        print(
            "DIRECT PRODUCTION ASSIGNMENT MISSING FOR:"
        )

        for target in missing:
            print(f"  - {target}")

    # Same function owns all three.
    same_function = {}

    for target in TARGETS:

        for occ in direct_by_target[target]:

            key = (
                occ.file,
                occ.function,
            )

            same_function.setdefault(key, set()).add(target)

    owners = [
        (key, targets)
        for key, targets in same_function.items()
        if len(targets) == 3
    ]

    print()

    if owners:

        print(
            "THREE-TARGET DIRECT ASSIGNMENT OWNER CANDIDATE(S):"
        )

        for key, targets in owners:

            print(
                f"  {key[0]} :: {key[1]} "
                f"-> {sorted(targets)}"
            )

    else:

        print(
            "NO SINGLE FUNCTION DIRECTLY ASSIGNS ALL THREE TARGETS."
        )

    print()
    print("=" * 100)
    print("NO SOURCE FILES MODIFIED.")
    print("NO DATABASE ACCESSED.")
    print("NO PIPELINE EXECUTED.")
    print("=" * 100)


# ================================================================================================
# MAIN
# ================================================================================================

def main():

    print_header()

    if not PROJECT_ROOT.exists():

        print()
        print("ERROR:")
        print(f"PROJECT ROOT NOT FOUND: {PROJECT_ROOT}")
        return

    results = scan_project()

    occurrences = rank_occurrences(results)

    grouped = best_by_target(occurrences)

    for target in TARGETS:

        print_target_report(
            target,
            grouped[target],
            results,
        )

    print_cross_target_candidates(grouped)

    print_parse_errors(results)

    print_summary(
        results,
        occurrences,
        grouped,
    )


if __name__ == "__main__":
    main()