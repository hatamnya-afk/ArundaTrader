# M8_REAL_FEATURE_RUNTIME_ORCHESTRATOR_IMPORT_BOUNDARY_TRACE_v0.1.py

from __future__ import annotations

import ast
import os
from pathlib import Path
from collections import defaultdict


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_SCORER = "signal_scorer"
TARGET_SCORER_FUNCTION = "run"

FEATURE_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

FEATURE_FUNCTIONS = {
    "build_features",
    "load_feature_snapshot",
    "build_feature_snapshot",
}

SCORE_FUNCTIONS = {
    "run",
    "load_scores",
}

ORCHESTRATOR_KEYWORDS = {
    "scheduler",
    "schedule",
    "orchestrator",
    "runtime",
    "pipeline",
    "engine",
    "loop",
    "worker",
    "service",
    "main",
    "start",
    "run",
    "process",
    "tick",
}


# =====================================================================
# DATA STRUCTURES
# =====================================================================

class FileInfo:
    def __init__(self, path: Path):
        self.path = path
        self.tree = None
        self.imports = []
        self.functions = []
        self.calls = []

        self.feature_receivers = []
        self.feature_creators = []
        self.scorer_calls = []
        self.orchestrator_signals = []


# =====================================================================
# HELPERS
# =====================================================================

def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr

    return None


def call_name(node):
    return dotted_name(node.func)


def node_arg_names(node):
    result = []

    for arg in getattr(node, "args", []):
        if isinstance(arg, ast.Name):
            result.append(arg.id)

    for kw in getattr(node, "keywords", []):
        if isinstance(kw.value, ast.Name):
            result.append(kw.value.id)

    return result


def contains_feature_names(names):
    return bool(set(names) & FEATURE_NAMES)


def path_is_production_candidate(path):
    name = path.name.lower()

    if name.startswith("test_"):
        return False

    if "audit" in name:
        return False

    if "forensic" in name:
        return False

    if "locator" in name:
        return False

    if "trace" in name:
        return False

    if "repair" in name:
        return False

    if "backup" in name:
        return False

    return True


# =====================================================================
# AST VISITOR
# =====================================================================

class Analyzer(ast.NodeVisitor):

    def __init__(self, info: FileInfo):
        self.info = info
        self.current_function = None

    def visit_FunctionDef(self, node):
        previous = self.current_function
        self.current_function = node.name

        args = [
            arg.arg
            for arg in node.args.args
        ]

        self.info.functions.append(
            {
                "name": node.name,
                "line": node.lineno,
                "args": args,
            }
        )

        # -------------------------------------------------------------
        # Feature receiver
        # -------------------------------------------------------------

        if contains_feature_names(args):
            self.info.feature_receivers.append(
                {
                    "function": node.name,
                    "line": node.lineno,
                    "features": [
                        x for x in args
                        if x in FEATURE_NAMES
                    ],
                }
            )

        self.generic_visit(node)

        self.current_function = previous

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node):
        for alias in node.names:
            self.info.imports.append(
                {
                    "type": "import",
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                }
            )

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""

        for alias in node.names:
            self.info.imports.append(
                {
                    "type": "from",
                    "name": f"{module}.{alias.name}",
                    "alias": alias.asname,
                    "line": node.lineno,
                }
            )

        self.generic_visit(node)

    def visit_Call(self, node):

        name = call_name(node)

        args = node_arg_names(node)

        record = {
            "function": self.current_function or "<module>",
            "line": node.lineno,
            "callee": name,
            "args": args,
        }

        self.info.calls.append(record)

        # -------------------------------------------------------------
        # Feature producer calls
        # -------------------------------------------------------------

        if name:
            leaf = name.split(".")[-1]

            if leaf in FEATURE_FUNCTIONS:

                self.info.feature_creators.append(
                    {
                        **record,
                        "feature_function": leaf,
                    }
                )

        # -------------------------------------------------------------
        # Direct signal_scorer.run
        # -------------------------------------------------------------

        if name in {
            "signal_scorer.run",
            "run",
        }:

            feature_args = [
                x for x in args
                if x in FEATURE_NAMES
            ]

            self.info.scorer_calls.append(
                {
                    **record,
                    "feature_args": feature_args,
                    "complete_feature_set":
                        set(feature_args) == FEATURE_NAMES,
                }
            )

        # -------------------------------------------------------------
        # Orchestrator signals
        # -------------------------------------------------------------

        if self.current_function:

            fn_lower = self.current_function.lower()

            matched_keywords = [
                key
                for key in ORCHESTRATOR_KEYWORDS
                if key in fn_lower
            ]

            if matched_keywords:

                self.info.orchestrator_signals.append(
                    {
                        "function": self.current_function,
                        "line": node.lineno,
                        "callee": name,
                        "keywords": matched_keywords,
                    }
                )

        self.generic_visit(node)


# =====================================================================
# DISCOVERY
# =====================================================================

def discover_python_files():

    files = []

    for path in PROJECT_ROOT.rglob("*.py"):

        if not path.is_file():
            continue

        if not path_is_production_candidate(path):
            continue

        files.append(path)

    return sorted(files)


# =====================================================================
# PARSE
# =====================================================================

def parse_file(path):

    info = FileInfo(path)

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        info.tree = ast.parse(
            source,
            filename=str(path),
        )

        Analyzer(info).visit(info.tree)

        return info, None

    except SyntaxError as exc:

        return info, (
            f"{exc.msg} "
            f"({path.name}, line {exc.lineno})"
        )

    except Exception as exc:

        return info, (
            f"{type(exc).__name__}: {exc}"
        )


# =====================================================================
# MODULE MAP
# =====================================================================

def build_module_map(infos):

    module_map = {}

    for info in infos:

        try:
            rel = info.path.relative_to(PROJECT_ROOT)
        except ValueError:
            continue

        parts = list(rel.parts)

        if not parts:
            continue

        filename = parts[-1]

        if filename.endswith(".py"):
            filename = filename[:-3]

        if filename == "__init__":
            module_name = ".".join(parts[:-1])
        else:
            module_name = ".".join(
                parts[:-1] + [filename]
            )

        module_map[module_name] = info.path

    return module_map


# =====================================================================
# MAIN FORENSIC
# =====================================================================

def main():

    print("=" * 96)
    print(
        "ARUNDA TRADER — REAL FEATURE RUNTIME "
        "ORCHESTRATOR IMPORT BOUNDARY TRACE v0.1"
    )
    print("=" * 96)
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ ONLY")
    print("EXECUTION    : STATIC AST ONLY")
    print("DB ACCESS    : NONE")
    print("WRITES       : NONE")
    print("SYNTHETIC    : FORBIDDEN")
    print("RISK ENGINE  : UNTOUCHED")
    print("=" * 96)

    files = discover_python_files()

    print("\n" + "=" * 96)
    print("DISCOVERY")
    print("=" * 96)

    print(f"Python files discovered : {len(files)}")

    infos = []
    failures = []

    for path in files:

        info, error = parse_file(path)

        if error:
            failures.append(
                (path, error)
            )
        else:
            infos.append(info)

    print(f"Files parsed            : {len(infos)}")
    print(f"Syntax failures         : {len(failures)}")

    if failures:

        print("\n" + "=" * 96)
        print("SYNTAX FAILURES")
        print("=" * 96)

        for path, error in failures:
            print(f"{path.name}: {error}")

    # =================================================================
    # DIRECT SCORER CALLERS
    # =================================================================

    print("\n" + "=" * 96)
    print("DIRECT SIGNAL SCORER RUN CALLERS")
    print("=" * 96)

    direct_callers = []

    for info in infos:

        for call in info.scorer_calls:

            direct_callers.append(
                (
                    info,
                    call,
                )
            )

    if not direct_callers:

        print("NO signal_scorer.run() CALLER FOUND")

    else:

        for info, call in direct_callers:

            print(
                f"{info.path.name}:{call['line']} "
                f"{call['function']} → {call['callee']}"
            )

            print(
                f"  args     = {call['args']}"
            )

            print(
                f"  features = {call['feature_args']}"
            )

            print(
                f"  COMPLETE = "
                f"{call['complete_feature_set']}"
            )

    # =================================================================
    # FEATURE PRODUCER CALLS
    # =================================================================

    print("\n" + "=" * 96)
    print("REAL FEATURE PRODUCER CALL CANDIDATES")
    print("=" * 96)

    producers = []

    for info in infos:

        for call in info.feature_creators:

            producers.append(
                (
                    info,
                    call,
                )
            )

    if not producers:

        print("NO FEATURE PRODUCER CALL FOUND")

    else:

        for info, call in producers:

            print(
                f"{info.path.name}:{call['line']}"
            )

            print(
                f"  function = {call['function']}"
            )

            print(
                f"  callee   = {call['callee']}"
            )

            print(
                f"  args     = {call['args']}"
            )

            print(
                f"  feature_function = "
                f"{call['feature_function']}"
            )

    # =================================================================
    # COMPLETE FEATURE SET RECEIVERS
    # =================================================================

    print("\n" + "=" * 96)
    print("FUNCTIONS RECEIVING COMPLETE REAL FEATURE SET")
    print("=" * 96)

    complete_receivers = []

    for info in infos:

        for receiver in info.feature_receivers:

            if set(receiver["features"]) == FEATURE_NAMES:

                complete_receivers.append(
                    (
                        info,
                        receiver,
                    )
                )

    if not complete_receivers:

        print("NO COMPLETE FEATURE RECEIVER FOUND")

    else:

        for info, receiver in complete_receivers:

            print(
                f"{info.path.name}:{receiver['line']}"
            )

            print(
                f"  function = {receiver['function']}"
            )

            print(
                f"  features = {receiver['features']}"
            )

    # =================================================================
    # ORCHESTRATOR CANDIDATES
    # =================================================================

    print("\n" + "=" * 96)
    print("RUNTIME SCHEDULER / ORCHESTRATOR CANDIDATES")
    print("=" * 96)

    orchestrators = []

    for info in infos:

        if not path_is_production_candidate(info.path):
            continue

        for item in info.orchestrator_signals:

            orchestrators.append(
                (
                    info,
                    item,
                )
            )

    # Deduplicate
    seen = set()

    unique_orchestrators = []

    for info, item in orchestrators:

        key = (
            str(info.path),
            item["function"],
            item["line"],
            item["callee"],
        )

        if key in seen:
            continue

        seen.add(key)

        unique_orchestrators.append(
            (
                info,
                item,
            )
        )

    for info, item in unique_orchestrators:

        print(
            f"{info.path.name}:{item['line']}"
        )

        print(
            f"  function = {item['function']}"
        )

        print(
            f"  callee   = {item['callee']}"
        )

        print(
            f"  keywords = {item['keywords']}"
        )

    # =================================================================
    # IMPORT BOUNDARY
    # =================================================================

    print("\n" + "=" * 96)
    print("IMPORT BOUNDARY")
    print("=" * 96)

    import_hits = []

    for info in infos:

        for imp in info.imports:

            name = imp["name"]

            if (
                "signal_scorer" in name
                or "feature_contract" in name
            ):

                import_hits.append(
                    (
                        info,
                        imp,
                    )
                )

    if not import_hits:

        print(
            "NO signal_scorer / feature_contract "
            "IMPORT BOUNDARY FOUND"
        )

    else:

        for info, imp in import_hits:

            print(
                f"{info.path.name}:{imp['line']}"
            )

            print(
                f"  type  = {imp['type']}"
            )

            print(
                f"  name  = {imp['name']}"
            )

            print(
                f"  alias = {imp['alias']}"
            )

    # =================================================================
    # FILE-LEVEL CORRELATION
    # =================================================================

    print("\n" + "=" * 96)
    print("HIGH-VALUE ORCHESTRATOR FILE CORRELATION")
    print("=" * 96)

    candidates = []

    for info in infos:

        has_feature = bool(
            info.feature_creators
        )

        has_scorer = bool(
            info.scorer_calls
        )

        has_import_boundary = any(
            "signal_scorer" in x["name"]
            or "feature_contract" in x["name"]
            for x in info.imports
        )

        orchestrator_score = 0

        name_lower = info.path.name.lower()

        for keyword in ORCHESTRATOR_KEYWORDS:

            if keyword in name_lower:

                orchestrator_score += 1

        if has_feature:
            orchestrator_score += 5

        if has_scorer:
            orchestrator_score += 10

        if has_import_boundary:
            orchestrator_score += 3

        if orchestrator_score > 0:

            candidates.append(
                (
                    orchestrator_score,
                    info,
                    has_feature,
                    has_scorer,
                    has_import_boundary,
                )
            )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    for score, info, has_feature, has_scorer, has_import in candidates[:50]:

        print(
            f"{info.path.name}"
        )

        print(
            f"  SCORE            = {score}"
        )

        print(
            f"  FEATURE_PRODUCER = {has_feature}"
        )

        print(
            f"  SCORER_CALL      = {has_scorer}"
        )

        print(
            f"  IMPORT_BOUNDARY  = {has_import}"
        )

    # =================================================================
    # VERDICT
    # =================================================================

    print("\n" + "=" * 96)
    print("FORENSIC VERDICT")
    print("=" * 96)

    complete_direct = [
        x for x in direct_callers
        if x[1]["complete_feature_set"]
    ]

    if complete_direct:

        print(
            "RESULT : COMPLETE REAL FEATURE → "
            "SCORER CALL EXISTS"
        )

        print(
            "BUT THE STATIC CALL GRAPH DOES NOT YET "
            "IDENTIFY ITS PRODUCTION ORCHESTRATOR."
        )

    else:

        print(
            "RESULT : PRODUCTION ORCHESTRATOR "
            "STILL UNRESOLVED"
        )

    print()
    print("STATIC CHAIN UNDER INVESTIGATION:")
    print()
    print(
        "REAL MARKET DATA"
    )
    print(
        "        |"
    )
    print(
        "        v"
    )
    print(
        "FEATURE PRODUCER / SNAPSHOT BUILDER"
    )
    print(
        "        |"
    )
    print(
        "        v"
    )
    print(
        "bars_by_asset"
    )
    print(
        "indicators_by_asset"
    )
    print(
        "structures_by_asset"
    )
    print(
        "        |"
    )
    print(
        "        v"
    )
    print(
        "signal_scorer.run(...)"
    )
    print(
        "        |"
    )
    print(
        "        v"
    )
    print(
        "signal_scorer.load_scores(...)"
    )
    print(
        "        |"
    )
    print(
        "        v"
    )
    print(
        "DECISION ENGINE"
    )
    print(
        "        |"
    )
    print(
        "        v"
    )
    print(
        "RISK / EXECUTION"
    )

    print()
    print(
        "NEXT ACTION:"
    )
    print(
        "Inspect ONLY the highest-ranked "
        "runtime orchestrator candidates."
    )
    print(
        "Determine whether one runtime boundary "
        "constructs the three real feature objects."
    )
    print(
        "DO NOT MODIFY PRODUCTION CODE."
    )

    print()
    print("=" * 96)
    print("M8 STATUS : COMPLETE")
    print("=" * 96)


if __name__ == "__main__":
    main()