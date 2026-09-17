# =============================================================================
# ARUNDA TRADER — M3
# DECISION → SCORE → REAL FEATURE RUNTIME BRIDGE LOCATOR v0.1
# =============================================================================
#
# PURPOSE
# -------
# Locate the REAL production runtime bridge carrying:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# into:
#
#     signal_scorer.run(...)
#     signal_scorer.load_scores(...)
#
# and determine how that path reaches:
#
#     decision_engine.load_scores()
#
# MODE
# ----
# READ ONLY
# STATIC AST ONLY
#
# GUARANTEES
# ----------
# - No database access
# - No SQL
# - No writes
# - No source modification
# - No synthetic inputs
# - No runtime execution of production modules
# - No Feature Engine modification
# - No Signal Layer modification
# - No Risk Engine modification
# - No reconstruction
#
# IMPORTANT
# ---------
# This script is a forensic locator.
# It does NOT repair the runtime.
#
# =============================================================================

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = {
    "decision_engine.py",
    "signal_scorer.py",
}

FEATURE_INPUTS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

DECISION_TARGET = "decision_engine"
SCORER_TARGET = "signal_scorer"

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
}


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def header(title: str) -> None:
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def safe_source(path: Path) -> Optional[str]:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return None


def parse_file(path: Path) -> Optional[ast.AST]:
    source = safe_source(path)

    if source is None:
        return None

    try:
        return ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        print(
            f"[WARN] Syntax error in {path.name}: "
            f"{exc}"
        )
        return None
    except Exception as exc:
        print(
            f"[WARN] Parse failure in {path.name}: "
            f"{type(exc).__name__}: {exc}"
        )
        return None


def dotted_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def call_name(node: ast.Call) -> Optional[str]:
    return dotted_name(node.func)


def argument_names(node: ast.Call) -> List[str]:
    result: List[str] = []

    for arg in node.args:
        name = dotted_name(arg)

        if name:
            result.append(name)
        else:
            result.append(ast.unparse(arg))

    for kw in node.keywords:
        if kw.arg is None:
            result.append(f"**{ast.unparse(kw.value)}")
        else:
            result.append(
                f"{kw.arg}={ast.unparse(kw.value)}"
            )

    return result


# =============================================================================
# FUNCTION INDEX
# =============================================================================

def build_function_index(
    tree: ast.AST,
    path: Path,
) -> Dict[str, ast.AST]:

    result: Dict[str, ast.AST] = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result[node.name] = node

    return result


# =============================================================================
# IMPORT MAP
# =============================================================================

def build_import_map(tree: ast.AST) -> Dict[str, str]:

    imports: Dict[str, str] = {}

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                local_name = alias.asname or alias.name

                imports[local_name] = alias.name

        elif isinstance(node, ast.ImportFrom):

            module = node.module or ""

            for alias in node.names:

                if alias.name == "*":
                    continue

                local_name = (
                    alias.asname
                    or alias.name
                )

                imports[local_name] = (
                    f"{module}.{alias.name}"
                )

    return imports


# =============================================================================
# CALL RECORD
# =============================================================================

def find_calls(
    tree: ast.AST,
    wanted: Set[str],
) -> List[Dict[str, Any]]:

    records: List[Dict[str, Any]] = []

    function_stack: List[str] = []

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

            name = call_name(node)

            if name in wanted:

                records.append(
                    {
                        "line": node.lineno,
                        "function": (
                            function_stack[-1]
                            if function_stack
                            else "<module>"
                        ),
                        "callee": name,
                        "args": argument_names(node),
                    }
                )

            self.generic_visit(node)

    Visitor().visit(tree)

    return records


# =============================================================================
# FEATURE INPUT FLOW ANALYSIS
# =============================================================================

def find_feature_input_usage(
    tree: ast.AST,
) -> List[Dict[str, Any]]:

    records: List[Dict[str, Any]] = []

    function_stack: List[str] = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):
            function_stack.append(node.name)

            self.generic_visit(node)

            function_stack.pop()

        def visit_AsyncFunctionDef(self, node):
            function_stack.append(node.name)

            self.generic_visit(node)

            function_stack.pop()

        def visit_Name(self, node):

            if node.id in FEATURE_INPUTS:

                records.append(
                    {
                        "line": node.lineno,
                        "name": node.id,
                        "function": (
                            function_stack[-1]
                            if function_stack
                            else "<module>"
                        ),
                        "context": type(
                            node.ctx
                        ).__name__,
                    }
                )

            self.generic_visit(node)

    Visitor().visit(tree)

    return records


# =============================================================================
# FUNCTION PARAMETER ANALYSIS
# =============================================================================

def function_parameters(
    node: ast.AST,
) -> List[str]:

    if not isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        return []

    args = node.args

    result = []

    for arg in args.posonlyargs:
        result.append(arg.arg)

    for arg in args.args:
        result.append(arg.arg)

    if args.vararg:
        result.append(
            f"*{args.vararg.arg}"
        )

    for arg in args.kwonlyargs:
        result.append(arg.arg)

    if args.kwarg:
        result.append(
            f"**{args.kwarg.arg}"
        )

    return result


# =============================================================================
# PRODUCTION-LIKE BRIDGE DETECTION
# =============================================================================

def score_bridge_candidate(
    record: Dict[str, Any],
) -> Tuple[int, List[str]]:

    score = 0
    evidence: List[str] = []

    args = set(record["args"])

    present = (
        args
        & FEATURE_INPUTS
    )

    if "bars_by_asset" in present:
        score += 3
        evidence.append(
            "bars_by_asset propagated"
        )

    if "indicators_by_asset" in present:
        score += 3
        evidence.append(
            "indicators_by_asset propagated"
        )

    if "structures_by_asset" in present:
        score += 3
        evidence.append(
            "structures_by_asset propagated"
        )

    if len(present) == 3:
        score += 5
        evidence.append(
            "COMPLETE REAL FEATURE INPUT SET"
        )

    return score, evidence


# =============================================================================
# PROJECT DISCOVERY
# =============================================================================

def discover_python_files() -> List[Path]:

    files: List[Path] = []

    for root, dirs, filenames in os.walk(
        PROJECT_ROOT
    ):

        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
        ]

        for filename in filenames:

            if filename.endswith(".py"):

                files.append(
                    Path(root) / filename
                )

    return sorted(files)


# =============================================================================
# TARGET ANALYSIS
# =============================================================================

def analyze_target(
    path: Path,
) -> Optional[Dict[str, Any]]:

    tree = parse_file(path)

    if tree is None:
        return None

    return {
        "path": path,
        "tree": tree,
        "functions": build_function_index(
            tree,
            path,
        ),
        "imports": build_import_map(tree),
        "feature_usage": find_feature_input_usage(
            tree
        ),
    }


# =============================================================================
# DECISION ENGINE ANALYSIS
# =============================================================================

def analyze_decision_engine(
    data: Dict[str, Any],
) -> None:

    header("DECISION ENGINE")

    functions = data["functions"]

    for name in (
        "load_scores",
        "build_decision_snapshot",
        "load_validated_signals",
        "main",
    ):

        node = functions.get(name)

        if node is None:
            print(
                f"MISSING {name}()"
            )
            continue

        params = function_parameters(node)

        print(
            f"FOUND  {name}() "
            f"line={node.lineno} "
            f"args={params}"
        )

    print()
    print("DECISION → SCORE CALLS")

    calls = find_calls(
        data["tree"],
        {
            "signal_scorer.load_scores",
            "load_scores",
        },
    )

    for record in calls:

        print(
            f"  line={record['line']} "
            f"function={record['function']} "
            f"callee={record['callee']}"
        )

        print(
            f"      args={record['args']}"
        )


# =============================================================================
# SCORER ANALYSIS
# =============================================================================

def analyze_signal_scorer(
    data: Dict[str, Any],
) -> None:

    header("SIGNAL SCORER")

    functions = data["functions"]

    for name in (
        "load_features",
        "load_scores",
        "run",
    ):

        node = functions.get(name)

        if node is None:
            print(
                f"MISSING {name}()"
            )
            continue

        params = function_parameters(node)

        feature_params = [
            p
            for p in params
            if p in FEATURE_INPUTS
        ]

        print(
            f"FOUND  {name}() "
            f"line={node.lineno}"
        )

        print(
            f"       args={params}"
        )

        if feature_params:

            print(
                f"       REAL FEATURE INPUTS="
                f"{feature_params}"
            )


# =============================================================================
# FEATURE PROPAGATION ANALYSIS
# =============================================================================

def analyze_feature_propagation(
    data: Dict[str, Any],
) -> None:

    header(
        "REAL FEATURE INPUT PROPAGATION "
        "INSIDE SIGNAL SCORER"
    )

    functions = data["functions"]

    for name in (
        "load_features",
        "load_scores",
        "run",
    ):

        node = functions.get(name)

        if node is None:
            continue

        params = set(
            function_parameters(node)
        )

        present = (
            params
            & FEATURE_INPUTS
        )

        print(
            f"{name}() line={node.lineno}"
        )

        print(
            f"  feature parameters : "
            f"{sorted(present)}"
        )

        calls = find_calls(
            node,
            {
                "feature_contract.load_feature_snapshot",
                "load_features",
                "load_scores",
            },
        )

        for record in calls:

            print(
                f"  call line={record['line']} "
                f"{record['callee']}"
            )

            print(
                f"      args={record['args']}"
            )


# =============================================================================
# ALL PROJECT CALLER SEARCH
# =============================================================================

def search_project_callers(
    python_files: List[Path],
) -> List[Dict[str, Any]]:

    records: List[Dict[str, Any]] = []

    wanted = {
        "signal_scorer.run",
        "signal_scorer.load_scores",
        "load_scores",
    }

    for path in python_files:

        tree = parse_file(path)

        if tree is None:
            continue

        calls = find_calls(
            tree,
            wanted,
        )

        for record in calls:

            record = dict(record)

            record["file"] = str(
                path.relative_to(
                    PROJECT_ROOT
                )
            )

            score, evidence = (
                score_bridge_candidate(
                    record
                )
            )

            record["score"] = score
            record["evidence"] = evidence

            records.append(record)

    return records


# =============================================================================
# PARAMETER FLOW SEARCH
# =============================================================================

def search_feature_parameter_functions(
    python_files: List[Path],
) -> List[Dict[str, Any]]:

    results: List[Dict[str, Any]] = []

    for path in python_files:

        tree = parse_file(path)

        if tree is None:
            continue

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            params = set(
                function_parameters(node)
            )

            present = (
                params
                & FEATURE_INPUTS
            )

            if not present:
                continue

            results.append(
                {
                    "file": str(
                        path.relative_to(
                            PROJECT_ROOT
                        )
                    ),
                    "function": node.name,
                    "line": node.lineno,
                    "params": sorted(
                        present
                    ),
                    "complete": (
                        present
                        == FEATURE_INPUTS
                    ),
                }
            )

    return results


# =============================================================================
# PRINT PARAMETER CANDIDATES
# =============================================================================

def print_parameter_candidates(
    candidates: List[Dict[str, Any]],
) -> None:

    header(
        "FEATURE INPUT PARAMETER "
        "BOUNDARY CANDIDATES"
    )

    if not candidates:

        print(
            "No functions explicitly "
            "receive feature inputs."
        )

        return

    candidates = sorted(
        candidates,
        key=lambda x: (
            not x["complete"],
            x["file"],
            x["line"],
        ),
    )

    for item in candidates:

        status = (
            "COMPLETE"
            if item["complete"]
            else "PARTIAL"
        )

        print(
            f"{status:<8} "
            f"{item['file']} "
            f"line={item['line']} "
            f"function={item['function']}"
        )

        print(
            f"         inputs={item['params']}"
        )


# =============================================================================
# PRINT CALLER CANDIDATES
# =============================================================================

def print_caller_candidates(
    records: List[Dict[str, Any]],
) -> None:

    header(
        "REAL RUNTIME BRIDGE CALL "
        "CANDIDATES"
    )

    if not records:

        print(
            "No signal_scorer runtime calls found."
        )

        return

    records = sorted(
        records,
        key=lambda x: (
            -x["score"],
            x["file"],
            x["line"],
        ),
    )

    for record in records:

        print(
            f"SCORE={record['score']:<2} "
            f"{record['file']}"
        )

        print(
            f"  function={record['function']} "
            f"line={record['line']}"
        )

        print(
            f"  callee={record['callee']}"
        )

        print(
            f"  args={record['args']}"
        )

        for evidence in record["evidence"]:

            print(
                f"  + {evidence}"
            )

        print()


# =============================================================================
# STATIC CHAIN RECONSTRUCTION
# =============================================================================

def reconstruct_chain(
    decision_data: Dict[str, Any],
    scorer_data: Dict[str, Any],
    callers: List[Dict[str, Any]],
) -> None:

    header(
        "STATIC RUNTIME BRIDGE "
        "RECONSTRUCTION"
    )

    print(
        "1. DECISION ENGINE"
    )

    decision_functions = (
        decision_data["functions"]
    )

    decision_loader = (
        decision_functions.get(
            "load_scores"
        )
    )

    if decision_loader:

        print(
            f"   decision_engine.load_scores() "
            f"line={decision_loader.lineno}"
        )

    decision_calls = find_calls(
        decision_loader,
        {
            "signal_scorer.load_scores"
        },
    ) if decision_loader else []

    if decision_calls:

        for call in decision_calls:

            print(
                f"   ↓ signal_scorer.load_scores() "
                f"line={call['line']}"
            )

            print(
                f"     arguments={call['args']}"
            )

    else:

        print(
            "   ↓ NO DIRECT "
            "signal_scorer.load_scores(...) "
            "CALL FOUND"
        )

    print()
    print(
        "2. SIGNAL SCORER"
    )

    scorer_functions = (
        scorer_data["functions"]
    )

    scorer_loader = (
        scorer_functions.get(
            "load_scores"
        )
    )

    if scorer_loader:

        params = function_parameters(
            scorer_loader
        )

        print(
            "   signal_scorer.load_scores("
            f"{', '.join(params)}"
            ")"
        )

        print(
            f"   line={scorer_loader.lineno}"
        )

    print()
    print(
        "3. REAL FEATURE INPUTS"
    )

    print(
        "   bars_by_asset"
    )

    print(
        "   indicators_by_asset"
    )

    print(
        "   structures_by_asset"
    )

    print()
    print(
        "4. RUNTIME CALL CANDIDATES"
    )

    if not callers:

        print(
            "   NONE"
        )

    else:

        for item in callers[:10]:

            print(
                f"   {item['file']}"
                f":{item['line']} "
                f"{item['function']}()"
                f" → {item['callee']}"
            )

            print(
                f"      args={item['args']}"
            )


# =============================================================================
# VERDICT
# =============================================================================

def forensic_verdict(
    decision_data: Dict[str, Any],
    scorer_data: Dict[str, Any],
    callers: List[Dict[str, Any]],
    parameter_candidates: List[Dict[str, Any]],
) -> None:

    header("FORENSIC VERDICT")

    decision_functions = (
        decision_data["functions"]
    )

    scorer_functions = (
        scorer_data["functions"]
    )

    decision_loader = (
        decision_functions.get(
            "load_scores"
        )
    )

    scorer_loader = (
        scorer_functions.get(
            "load_scores"
        )
    )

    decision_direct_call = False

    if decision_loader:

        calls = find_calls(
            decision_loader,
            {
                "signal_scorer.load_scores"
            },
        )

        decision_direct_call = bool(
            calls
        )

    scorer_complete = False

    if scorer_loader:

        params = set(
            function_parameters(
                scorer_loader
            )
        )

        scorer_complete = (
            params
            & FEATURE_INPUTS
        ) == FEATURE_INPUTS

    complete_boundaries = [
        x
        for x in parameter_candidates
        if x["complete"]
    ]

    strong_callers = [
        x
        for x in callers
        if x["score"] >= 14
    ]

    print(
        "Decision load_scores()       : "
        + (
            "FOUND"
            if decision_loader
            else "MISSING"
        )
    )

    print(
        "Decision → scorer direct call : "
        + (
            "FOUND"
            if decision_direct_call
            else "NOT FOUND"
        )
    )

    print(
        "Scorer load_scores()         : "
        + (
            "FOUND"
            if scorer_loader
            else "MISSING"
        )
    )

    print(
        "Scorer complete input sig.   : "
        + (
            "YES"
            if scorer_complete
            else "NO"
        )
    )

    print(
        "Complete feature boundaries  : "
        f"{len(complete_boundaries)}"
    )

    print(
        "Strong runtime callers       : "
        f"{len(strong_callers)}"
    )

    print()

    if strong_callers:

        print(
            "RESULT : REAL FEATURE RUNTIME "
            "BRIDGE CANDIDATE(S) LOCATED"
        )

        print()
        print(
            "NEXT ACTION:"
        )

        print(
            "Trace only the highest-scoring "
            "production caller."
        )

        print(
            "Confirm how its real feature "
            "objects reach Decision Engine."
        )

        print(
            "DO NOT MODIFY ANY PRODUCTION "
            "LAYER YET."
        )

    elif complete_boundaries:

        print(
            "RESULT : FEATURE INPUT "
            "BOUNDARIES EXIST, BUT "
            "PRODUCTION BRIDGE IS NOT "
            "YET PROVEN"
        )

        print()
        print(
            "NEXT ACTION:"
        )

        print(
            "Locate the caller that owns "
            "the complete three-input set."
        )

    else:

        print(
            "RESULT : REAL FEATURE INPUT "
            "RUNTIME BRIDGE NOT LOCATED"
        )

        print()
        print(
            "NEXT ACTION:"
        )

        print(
            "Expand forensic search only "
            "around upstream runtime owners."
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    header(
        "ARUNDA TRADER — DECISION → SCORE → "
        "REAL FEATURE RUNTIME BRIDGE LOCATOR v0.1"
    )

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

    print(
        "=" * 88
    )

    python_files = discover_python_files()

    print(
        f"Python files discovered : "
        f"{len(python_files)}"
    )

    target_paths = {
        name: PROJECT_ROOT / name
        for name in TARGET_FILES
    }

    decision_path = target_paths[
        "decision_engine.py"
    ]

    scorer_path = target_paths[
        "signal_scorer.py"
    ]

    decision_data = analyze_target(
        decision_path
    )

    scorer_data = analyze_target(
        scorer_path
    )

    if decision_data is None:

        print(
            "FATAL: decision_engine.py "
            "could not be parsed."
        )

        return 1

    if scorer_data is None:

        print(
            "FATAL: signal_scorer.py "
            "could not be parsed."
        )

        return 1

    analyze_decision_engine(
        decision_data
    )

    analyze_signal_scorer(
        scorer_data
    )

    analyze_feature_propagation(
        scorer_data
    )

    callers = search_project_callers(
        python_files
    )

    parameter_candidates = (
        search_feature_parameter_functions(
            python_files
        )
    )

    print_parameter_candidates(
        parameter_candidates
    )

    print_caller_candidates(
        callers
    )

    reconstruct_chain(
        decision_data,
        scorer_data,
        callers,
    )

    forensic_verdict(
        decision_data,
        scorer_data,
        callers,
        parameter_candidates,
    )

    print()
    print("=" * 88)
    print(
        "M3 STATUS : FORENSIC LOCATOR COMPLETE"
    )
    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())