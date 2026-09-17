
"""
ARUNDA TRADER
DECISION → SCORE → REAL FEATURE INPUT BOUNDARY LOCATOR v0.1

PURPOSE
-------
Locate the REAL production runtime boundary that supplies:

    bars_by_asset
    indicators_by_asset
    structures_by_asset

into the Decision → Score chain.

TARGET CHAIN
------------
    REAL RUNTIME CALLER
            ↓
    bars_by_asset
    indicators_by_asset
    structures_by_asset
            ↓
    signal_scorer.load_scores(...)
            ↓
    decision_engine.load_scores(...)
            ↓
    decision_engine.build_decision_snapshot(...)
            ↓
    Risk Engine

MODE
----
    READ ONLY
    FORENSIC ONLY
    STATIC AST ANALYSIS ONLY

GUARANTEES
----------
    - NO database access
    - NO SQL
    - NO writes
    - NO imports of production modules
    - NO execution of production runtime
    - NO synthetic data
    - NO feature reconstruction
    - NO contract modification
    - NO source modification
    - NO Risk Engine modification
    - NO Decision Engine modification
    - NO scorer modification

IMPORTANT
---------
This locator does NOT attempt to repair the boundary.

It only identifies where the real production runtime
already possesses the required Feature inputs.

The result is intended to define the NEXT repair point.
"""


from __future__ import annotations

import ast
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DECISION_ENGINE = PROJECT_ROOT / "decision_engine.py"

TARGET_MODULES = {
    "decision_engine.py",
    "signal_scorer.py",
}

FEATURE_INPUT_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

DECISION_APIS = {
    "load_validated_signals",
    "load_scores",
    "build_decision_snapshot",
}

SCORE_APIS = {
    "load_scores",
    "run",
    "load_features",
}

RUNTIME_ENTRY_NAMES = {
    "main",
    "run",
    "process",
    "process_signals",
    "execute",
    "start",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FunctionInfo:
    file: Path
    name: str
    line: int
    end_line: int
    arguments: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)


@dataclass
class CallSite:
    file: Path
    function: Optional[str]
    line: int
    callee: str
    arguments: list[str]
    keywords: list[str]


@dataclass
class FileAnalysis:
    path: Path
    functions: list[FunctionInfo] = field(default_factory=list)
    calls: list[CallSite] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    feature_hits: list[tuple[int, str, str]] = field(default_factory=list)


# =============================================================================
# HELPERS
# =============================================================================

def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def dotted_name(node: ast.AST) -> Optional[str]:
    """
    Convert AST Name / Attribute into dotted string.
    """

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def expression_name(node: ast.AST) -> str:
    """
    Safe textual representation for call arguments.
    """

    name = dotted_name(node)

    if name:
        return name

    if isinstance(node, ast.Constant):
        return repr(node.value)

    if isinstance(node, ast.Call):
        callee = dotted_name(node.func)

        if callee:
            return f"{callee}(...)"

    if isinstance(node, ast.Dict):
        return "{...}"

    if isinstance(node, ast.List):
        return "[...]"

    if isinstance(node, ast.Tuple):
        return "(...)"

    return ast.dump(
        node,
        annotate_fields=False,
        include_attributes=False,
    )[:120]


# =============================================================================
# AST VISITOR
# =============================================================================

class SourceVisitor(ast.NodeVisitor):

    def __init__(self, path: Path):

        self.path = path

        self.functions: list[FunctionInfo] = []
        self.calls: list[CallSite] = []
        self.imports: list[str] = []
        self.feature_hits: list[tuple[int, str, str]] = []

        self.function_stack: list[str] = []

    # -------------------------------------------------------------------------
    # FUNCTIONS
    # -------------------------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):

        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):

        self._visit_function(node)

    def _visit_function(self, node):

        arguments = []

        all_args = (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        )

        if node.args.vararg:
            all_args.append(node.args.vararg)

        if node.args.kwarg:
            all_args.append(node.args.kwarg)

        for arg in all_args:

            if isinstance(arg, ast.arg):
                arguments.append(arg.arg)

        info = FunctionInfo(
            file=self.path,
            name=node.name,
            line=node.lineno,
            end_line=getattr(
                node,
                "end_lineno",
                node.lineno,
            ),
            arguments=arguments,
        )

        self.functions.append(info)

        self.function_stack.append(node.name)

        for child in node.body:
            self.visit(child)

        self.function_stack.pop()

    # -------------------------------------------------------------------------
    # IMPORTS
    # -------------------------------------------------------------------------

    def visit_Import(self, node: ast.Import):

        for alias in node.names:

            self.imports.append(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):

        module = node.module or ""

        self.imports.append(module)

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    def visit_Call(self, node: ast.Call):

        callee = dotted_name(node.func)

        if callee:

            arguments = [
                expression_name(arg)
                for arg in node.args
            ]

            keywords = []

            for keyword in node.keywords:

                if keyword.arg is None:
                    keywords.append("**")
                else:
                    keywords.append(
                        f"{keyword.arg}="
                        f"{expression_name(keyword.value)}"
                    )

            self.calls.append(
                CallSite(
                    file=self.path,
                    function=(
                        self.function_stack[-1]
                        if self.function_stack
                        else None
                    ),
                    line=node.lineno,
                    callee=callee,
                    arguments=arguments,
                    keywords=keywords,
                )
            )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # FEATURE INPUT REFERENCES
    # -------------------------------------------------------------------------

    def visit_Name(self, node: ast.Name):

        if node.id in FEATURE_INPUT_NAMES:

            context = (
                self.function_stack[-1]
                if self.function_stack
                else "<module>"
            )

            self.feature_hits.append(
                (
                    node.lineno,
                    node.id,
                    context,
                )
            )

        self.generic_visit(node)


# =============================================================================
# FILE PARSER
# =============================================================================

def analyze_file(path: Path) -> Optional[FileAnalysis]:

    try:

        source = path.read_text(
            encoding="utf-8"
        )

    except Exception as exc:

        print(
            f"[WARN] Cannot read "
            f"{relative(path)}: "
            f"{type(exc).__name__}: {exc}"
        )

        return None

    try:

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except SyntaxError as exc:

        print(
            f"[WARN] Syntax error in "
            f"{relative(path)}: "
            f"{exc}"
        )

        return None

    visitor = SourceVisitor(path)

    visitor.visit(tree)

    return FileAnalysis(
        path=path,
        functions=visitor.functions,
        calls=visitor.calls,
        imports=visitor.imports,
        feature_hits=visitor.feature_hits,
    )


# =============================================================================
# PROJECT FILE DISCOVERY
# =============================================================================

def discover_python_files():

    files = []

    for path in PROJECT_ROOT.rglob("*.py"):

        if any(
            part.startswith(".")
            for part in path.parts
        ):
            continue

        files.append(path)

    return sorted(files)


# =============================================================================
# DECISION ENGINE ANALYSIS
# =============================================================================

def analyze_decision_engine(
    analysis: FileAnalysis,
):

    print()
    print("=" * 88)
    print("DECISION ENGINE FORENSIC")
    print("=" * 88)

    print(
        f"Target : {relative(analysis.path)}"
    )

    print()

    print("DECISION APIs")

    for name in DECISION_APIS:

        matches = [
            fn
            for fn in analysis.functions
            if fn.name == name
        ]

        if matches:

            for fn in matches:

                print(
                    f"  FOUND  {name}() "
                    f"line={fn.line} "
                    f"args={fn.arguments}"
                )

        else:

            print(
                f"  MISSING {name}()"
            )

    print()

    print("DECISION → SCORE CALLS")

    found = False

    for call in analysis.calls:

        if (
            call.callee == "signal_scorer.load_scores"
            or call.callee.endswith(
                ".load_scores"
            )
        ):

            found = True

            print(
                f"  line={call.line} "
                f"function={call.function} "
                f"callee={call.callee}"
            )

            print(
                f"      args     = {call.arguments}"
            )

            print(
                f"      keywords = {call.keywords}"
            )

    if not found:

        print(
            "  No load_scores() call found."
        )


# =============================================================================
# FEATURE INPUT BOUNDARY ANALYSIS
# =============================================================================

def print_feature_hits(
    analyses: list[FileAnalysis],
):

    print()
    print("=" * 88)
    print("REAL FEATURE INPUT REFERENCES")
    print("=" * 88)

    found = False

    for analysis in analyses:

        if not analysis.feature_hits:
            continue

        found = True

        print()
        print(
            f"FILE : {relative(analysis.path)}"
        )

        for line, name, function in analysis.feature_hits:

            print(
                f"  line={line:<5} "
                f"name={name:<22} "
                f"function={function}"
            )

    if not found:

        print(
            "NO FEATURE INPUT REFERENCES FOUND"
        )


# =============================================================================
# CALLER DISCOVERY
# =============================================================================

def find_decision_callers(
    analyses: list[FileAnalysis],
):

    print()
    print("=" * 88)
    print("DECISION ENGINE CALLERS")
    print("=" * 88)

    callers = []

    for analysis in analyses:

        for call in analysis.calls:

            if (
                call.callee == "decision_engine"
                or call.callee.startswith(
                    "decision_engine."
                )
            ):

                callers.append(call)

    if not callers:

        print(
            "No explicit decision_engine call found."
        )

        return []

    for call in callers:

        print()

        print(
            f"FILE      : {relative(call.file)}"
        )

        print(
            f"FUNCTION  : {call.function}"
        )

        print(
            f"LINE      : {call.line}"
        )

        print(
            f"CALLEE    : {call.callee}"
        )

        print(
            f"ARGS      : {call.arguments}"
        )

        print(
            f"KEYWORDS  : {call.keywords}"
        )

    return callers


# =============================================================================
# LOAD_SCORES SIGNATURE ANALYSIS
# =============================================================================

def inspect_score_signature(
    analyses: list[FileAnalysis],
):

    print()
    print("=" * 88)
    print("SIGNAL SCORER INPUT CONTRACT")
    print("=" * 88)

    for analysis in analyses:

        if analysis.path.name != "signal_scorer.py":
            continue

        for fn in analysis.functions:

            if fn.name != "load_scores":
                continue

            print(
                f"FILE : {relative(analysis.path)}"
            )

            print(
                f"LINE : {fn.line}"
            )

            print(
                "ARGS : "
                + ", ".join(fn.arguments)
            )

            missing = (
                FEATURE_INPUT_NAMES
                - set(fn.arguments)
            )

            if missing:

                print(
                    "MISSING FEATURE INPUTS IN "
                    "SIGNATURE : "
                    + ", ".join(
                        sorted(missing)
                    )
                )

            else:

                print(
                    "FEATURE INPUT SIGNATURE : "
                    "COMPLETE"
                )


# =============================================================================
# FUNCTION OWNERSHIP
# =============================================================================

def inspect_feature_owners(
    analyses: list[FileAnalysis],
):

    print()
    print("=" * 88)
    print("FEATURE INPUT OWNERSHIP / PRODUCTION BOUNDARY CANDIDATES")
    print("=" * 88)

    for analysis in analyses:

        for fn in analysis.functions:

            matched = (
                set(fn.arguments)
                & FEATURE_INPUT_NAMES
            )

            if not matched:
                continue

            print()

            print(
                f"FILE     : {relative(fn.file)}"
            )

            print(
                f"FUNCTION : {fn.name}"
            )

            print(
                f"LINE     : {fn.line}"
            )

            print(
                "FEATURE INPUT ARGS : "
                + ", ".join(
                    sorted(matched)
                )
            )


# =============================================================================
# RUNTIME ENTRY CANDIDATES
# =============================================================================

def inspect_runtime_candidates(
    analyses: list[FileAnalysis],
):

    print()
    print("=" * 88)
    print("RUNTIME CALLER CANDIDATES")
    print("=" * 88)

    for analysis in analyses:

        for fn in analysis.functions:

            if fn.name not in RUNTIME_ENTRY_NAMES:
                continue

            interesting_calls = []

            for call in analysis.calls:

                if call.function != fn.name:
                    continue

                if (
                    "decision_engine" in call.callee
                    or "load_scores" in call.callee
                    or any(
                        arg in FEATURE_INPUT_NAMES
                        for arg in call.arguments
                    )
                    or any(
                        any(
                            name in keyword
                            for name in FEATURE_INPUT_NAMES
                        )
                        for keyword in call.keywords
                    )
                ):

                    interesting_calls.append(
                        call
                    )

            if not interesting_calls:
                continue

            print()

            print(
                f"FILE     : {relative(fn.file)}"
            )

            print(
                f"FUNCTION : {fn.name}"
            )

            print(
                f"LINE     : {fn.line}"
            )

            for call in interesting_calls:

                print(
                    f"  line={call.line} "
                    f"{call.callee}("
                    + ", ".join(
                        call.arguments
                        + call.keywords
                    )
                    + ")"
                )


# =============================================================================
# DECISION → SCORE → FEATURE CHAIN
# =============================================================================

def reconstruct_static_chain(
    analyses: list[FileAnalysis],
):

    print()
    print("=" * 88)
    print("STATIC CHAIN RECONSTRUCTION")
    print("=" * 88)

    decision = next(
        (
            a
            for a in analyses
            if a.path.name == "decision_engine.py"
        ),
        None,
    )

    scorer = next(
        (
            a
            for a in analyses
            if a.path.name == "signal_scorer.py"
        ),
        None,
    )

    if decision is None:

        print(
            "BLOCKER: decision_engine.py not found"
        )

        return

    print()
    print(
        "1. DECISION ENGINE"
    )

    decision_load_scores = [
        c
        for c in decision.calls
        if c.callee.endswith(
            "load_scores"
        )
    ]

    if not decision_load_scores:

        print(
            "   load_scores() call: NOT FOUND"
        )

    else:

        for call in decision_load_scores:

            print(
                f"   load_scores() at line "
                f"{call.line}"
            )

            print(
                f"   arguments: "
                f"{call.arguments}"
            )

    print()

    print(
        "2. SIGNAL SCORER"
    )

    if scorer is None:

        print(
            "   signal_scorer.py: NOT FOUND"
        )

    else:

        score_functions = [
            fn
            for fn in scorer.functions
            if fn.name == "load_scores"
        ]

        if not score_functions:

            print(
                "   load_scores(): NOT FOUND"
            )

        else:

            for fn in score_functions:

                print(
                    "   load_scores("
                    + ", ".join(fn.arguments)
                    + ")"
                )

    print()

    print(
        "3. REQUIRED REAL FEATURE INPUTS"
    )

    for name in sorted(
        FEATURE_INPUT_NAMES
    ):

        owners = []

        for analysis in analyses:

            for fn in analysis.functions:

                if name in fn.arguments:

                    owners.append(
                        f"{relative(fn.file)}:"
                        f"{fn.name}()"
                    )

        if owners:

            print(
                f"   {name}"
            )

            for owner in owners:

                print(
                    f"      ← {owner}"
                )

        else:

            print(
                f"   {name}"
                f"  ← OWNER NOT LOCATED"
            )


# =============================================================================
# FINAL FORENSIC VERDICT
# =============================================================================

def print_verdict(
    analyses: list[FileAnalysis],
    callers: list[CallSite],
):

    print()
    print("=" * 88)
    print("FORENSIC VERDICT")
    print("=" * 88)

    decision = next(
        (
            a
            for a in analyses
            if a.path.name == "decision_engine.py"
        ),
        None,
    )

    scorer = next(
        (
            a
            for a in analyses
            if a.path.name == "signal_scorer.py"
        ),
        None,
    )

    if decision is None:

        print(
            "STATUS : BLOCKED"
        )

        print(
            "REASON : decision_engine.py not found"
        )

        return 1

    decision_calls_scores = any(
        c.callee.endswith(
            "load_scores"
        )
        for c in decision.calls
    )

    scorer_load_scores = None

    if scorer:

        for fn in scorer.functions:

            if fn.name == "load_scores":

                scorer_load_scores = fn
                break

    feature_signature_complete = False

    if scorer_load_scores:

        feature_signature_complete = (
            FEATURE_INPUT_NAMES
            <= set(
                scorer_load_scores.arguments
            )
        )

    real_input_owners = set()

    for analysis in analyses:

        for fn in analysis.functions:

            for arg in fn.arguments:

                if arg in FEATURE_INPUT_NAMES:

                    real_input_owners.add(arg)

    print()

    print(
        "Decision Engine load_scores call : "
        + (
            "FOUND"
            if decision_calls_scores
            else "NOT FOUND"
        )
    )

    print(
        "Scorer load_scores signature       : "
        + (
            "FOUND"
            if scorer_load_scores
            else "NOT FOUND"
        )
    )

    print(
        "Scorer feature input contract      : "
        + (
            "COMPLETE"
            if feature_signature_complete
            else "INCOMPLETE / UNKNOWN"
        )
    )

    print(
        "Real feature input owners          : "
        + str(len(real_input_owners))
        + "/3"
    )

    print(
        "Decision runtime callers           : "
        + str(len(callers))
    )

    print()

    if (
        decision_calls_scores
        and scorer_load_scores
        and feature_signature_complete
        and len(real_input_owners) == 3
    ):

        print(
            "RESULT : REAL FEATURE INPUT "
            "BOUNDARY EXISTS / LOCATABLE"
        )

        print()
        print(
            "NEXT ACTION:"
        )

        print(
            "Connect Decision Engine to the "
            "already-existing runtime boundary."
        )

        print(
            "DO NOT modify Risk Engine."
        )

        print(
            "DO NOT reconstruct Feature Engine."
        )

        print(
            "DO NOT manufacture feature inputs."
        )

        return 0

    print(
        "RESULT : FEATURE INPUT BOUNDARY "
        "NOT YET FULLY LOCATED"
    )

    print(
        "NEXT ACTION : forensic tracing required"
    )

    return 2


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 88)
    print(
        "ARUNDA TRADER — "
        "DECISION → SCORE → REAL FEATURE INPUT "
        "BOUNDARY LOCATOR v0.1"
    )
    print("=" * 88)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "EXECUTION    : STATIC AST ONLY"
    )

    print(
        "DB ACCESS    : NONE"
    )

    print(
        "WRITES       : NONE"
    )

    print(
        "SYNTHETIC    : FORBIDDEN"
    )

    print(
        "RISK ENGINE  : UNTOUCHED"
    )

    print("=" * 88)

    if not DECISION_ENGINE.exists():

        print()
        print(
            "FATAL: decision_engine.py not found"
        )

        return 1

    # -------------------------------------------------------------------------
    # DISCOVER FILES
    # -------------------------------------------------------------------------

    files = discover_python_files()

    print()
    print(
        f"Python files discovered : {len(files)}"
    )

    # -------------------------------------------------------------------------
    # ANALYZE
    # -------------------------------------------------------------------------

    analyses = []

    for path in files:

        analysis = analyze_file(path)

        if analysis is not None:

            analyses.append(analysis)

    print(
        f"Files parsed            : {len(analyses)}"
    )

    # -------------------------------------------------------------------------
    # DECISION ENGINE
    # -------------------------------------------------------------------------

    decision_analysis = next(
        (
            a
            for a in analyses
            if a.path.resolve()
            == DECISION_ENGINE.resolve()
        ),
        None,
    )

    if decision_analysis:

        analyze_decision_engine(
            decision_analysis
        )

    # -------------------------------------------------------------------------
    # FEATURE REFERENCES
    # -------------------------------------------------------------------------

    print_feature_hits(
        analyses
    )

    # -------------------------------------------------------------------------
    # DECISION CALLERS
    # -------------------------------------------------------------------------

    callers = find_decision_callers(
        analyses
    )

    # -------------------------------------------------------------------------
    # SCORE CONTRACT
    # -------------------------------------------------------------------------

    inspect_score_signature(
        analyses
    )

    # -------------------------------------------------------------------------
    # FEATURE OWNERSHIP
    # -------------------------------------------------------------------------

    inspect_feature_owners(
        analyses
    )

    # -------------------------------------------------------------------------
    # RUNTIME CANDIDATES
    # -------------------------------------------------------------------------

    inspect_runtime_candidates(
        analyses
    )

    # -------------------------------------------------------------------------
    # STATIC CHAIN
    # -------------------------------------------------------------------------

    reconstruct_static_chain(
        analyses
    )

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------

    return print_verdict(
        analyses,
        callers,
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )