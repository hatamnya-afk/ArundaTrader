# -*- coding: utf-8 -*-

"""
========================================================================================
ARUNDA TRADER — UPSTREAM REAL FEATURE PRODUCER CALLER TRACE v0.1
========================================================================================
MODE         : READ ONLY
EXECUTION    : STATIC AST ONLY
DB ACCESS    : NONE
WRITES       : NONE
SYNTHETIC    : FORBIDDEN

PURPOSE
-------
Trace ONLY the upstream origin/caller chain of:

    bars_by_asset
    indicators_by_asset
    structures_by_asset

starting from the confirmed scorer boundary:

    signal_scorer.run(
        bars_by_asset,
        indicators_by_asset,
        structures_by_asset
    )

DO NOT MODIFY PRODUCTION CODE.
========================================================================================
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from collections import defaultdict, deque


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FEATURES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

TARGET_MODULE = "signal_scorer.py"
TARGET_FUNCTION = "run"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

files = []
parsed = {}
syntax_failures = []

functions = {}
calls = []

function_by_name = defaultdict(list)
calls_by_callee = defaultdict(list)
calls_by_file = defaultdict(list)

feature_assignments = []
feature_returns = []
feature_passes = []


# =============================================================================
# HELPERS
# =============================================================================

def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr

    return None


def node_features(node):
    found = set()

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            if child.id in TARGET_FEATURES:
                found.add(child.id)

    return found


def expr_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def function_key(filename, qualname):
    return f"{filename}:{qualname}"


def is_target_function(filename, qualname):
    return (
        Path(filename).name == TARGET_MODULE
        and qualname == TARGET_FUNCTION
    )


# =============================================================================
# DISCOVER PYTHON FILES
# =============================================================================

for root, dirs, filenames in os.walk(PROJECT_ROOT):
    dirs[:] = [
        d for d in dirs
        if d not in SKIP_DIRS
    ]

    for filename in filenames:
        if filename.endswith(".py"):
            files.append(Path(root) / filename)


# =============================================================================
# PARSE FILES
# =============================================================================

for path in files:
    try:
        source = path.read_text(
            encoding="utf-8-sig",
            errors="strict",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

        parsed[path] = tree

    except Exception as exc:
        syntax_failures.append(
            (path, str(exc))
        )


# =============================================================================
# INDEX FUNCTIONS
# =============================================================================

def walk_functions(tree, filename):
    stack = []

    def visit(node):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            qualname = ".".join(
                stack + [node.name]
            )

            key = function_key(
                filename,
                qualname,
            )

            functions[key] = {
                "file": filename,
                "name": node.name,
                "qualname": qualname,
                "line": node.lineno,
                "args": [
                    a.arg
                    for a in node.args.args
                ],
                "features": sorted(
                    node_features(node)
                ),
                "node": node,
            }

            function_by_name[node.name].append(key)

            stack.append(node.name)

            for child in ast.iter_child_nodes(node):
                visit(child)

            stack.pop()
            return

        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)


for path, tree in parsed.items():
    walk_functions(
        tree,
        path.name,
    )


# =============================================================================
# INDEX ALL CALLS
# =============================================================================

for key, info in functions.items():

    node = info["node"]

    for child in ast.walk(node):

        if not isinstance(child, ast.Call):
            continue

        callee = dotted_name(child.func)

        if not callee:
            continue

        args = [
            expr_text(a)
            for a in child.args
        ]

        keywords = {
            kw.arg: expr_text(kw.value)
            for kw in child.keywords
        }

        features = sorted(
            node_features(child)
        )

        record = {
            "caller": key,
            "file": info["file"],
            "function": info["name"],
            "line": child.lineno,
            "callee": callee,
            "args": args,
            "keywords": keywords,
            "features": features,
        }

        calls.append(record)

        calls_by_callee[callee].append(record)
        calls_by_file[info["file"]].append(record)


# =============================================================================
# FEATURE ASSIGNMENTS / RETURNS
# =============================================================================

for key, info in functions.items():

    node = info["node"]

    for child in ast.walk(node):

        # -------------------------------------------------------------
        # assignments
        # -------------------------------------------------------------

        if isinstance(
            child,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.NamedExpr,
            ),
        ):

            targets = []

            if isinstance(child, ast.Assign):
                for target in child.targets:
                    targets.append(target)

            elif isinstance(child, ast.AnnAssign):
                targets.append(child.target)

            elif isinstance(child, ast.NamedExpr):
                targets.append(child.target)

            names = set()

            for target in targets:
                if isinstance(target, ast.Name):
                    if target.id in TARGET_FEATURES:
                        names.add(target.id)

            if names:

                value = getattr(
                    child,
                    "value",
                    None,
                )

                feature_assignments.append({
                    "file": info["file"],
                    "function": info["name"],
                    "line": child.lineno,
                    "targets": sorted(names),
                    "value": expr_text(value)
                    if value is not None
                    else "<none>",
                })

        # -------------------------------------------------------------
        # returns
        # -------------------------------------------------------------

        if isinstance(child, ast.Return):

            features = sorted(
                node_features(child.value)
                if child.value is not None
                else set()
            )

            if features:
                feature_returns.append({
                    "file": info["file"],
                    "function": info["name"],
                    "line": child.lineno,
                    "features": features,
                    "value": expr_text(child.value),
                })


# =============================================================================
# FEATURE PASSING CALLS
# =============================================================================

for call in calls:

    features = set(call["features"])

    if features & TARGET_FEATURES:

        feature_passes.append(call)


# =============================================================================
# FIND CONFIRMED SCORER RUN
# =============================================================================

scorer_keys = []

for key, info in functions.items():

    if (
        Path(info["file"]).name == TARGET_MODULE
        and info["name"] == TARGET_FUNCTION
    ):
        scorer_keys.append(key)


# =============================================================================
# FIND CALLERS OF signal_scorer.run
# =============================================================================

run_callers = []

for call in calls:

    callee = call["callee"]

    if (
        callee == "signal_scorer.run"
        or callee.endswith(".signal_scorer.run")
    ):
        run_callers.append(call)


# =============================================================================
# FIND GENERIC ".run" CALLS THAT MAY RESOLVE TO SCORER
# =============================================================================

generic_run_candidates = []

for call in calls:

    if call["callee"] == "run":

        if set(call["features"]) & TARGET_FEATURES:

            generic_run_candidates.append(call)


# =============================================================================
# FIND FUNCTIONS RECEIVING ALL THREE FEATURES
# =============================================================================

complete_feature_functions = []

for key, info in functions.items():

    feature_set = set(info["features"])

    if TARGET_FEATURES.issubset(feature_set):

        complete_feature_functions.append(
            info
        )


# =============================================================================
# FIND PRODUCER-LIKE FUNCTIONS
# =============================================================================

producer_candidates = []

producer_keywords = (
    "feature",
    "indicator",
    "technical",
    "history",
    "market",
    "snapshot",
    "analysis",
    "structure",
    "signal",
    "score",
)

for info in functions.values():

    name = info["name"].lower()

    if (
        TARGET_FEATURES.issubset(
            set(info["features"])
        )
        and any(
            k in name
            for k in producer_keywords
        )
    ):
        producer_candidates.append(info)


# =============================================================================
# BUILD FEATURE PROPAGATION GRAPH
# =============================================================================

graph = defaultdict(list)

for call in feature_passes:

    caller = call["caller"]
    callee = call["callee"]

    graph[caller].append({
        "callee": callee,
        "line": call["line"],
        "features": call["features"],
    })


# =============================================================================
# DISPLAY
# =============================================================================

print("=" * 96)
print("ARUNDA TRADER — UPSTREAM REAL FEATURE PRODUCER CALLER TRACE v0.1")
print("=" * 96)
print(f"PROJECT ROOT : {PROJECT_ROOT}")
print("MODE         : READ ONLY")
print("EXECUTION    : STATIC AST ONLY")
print("DB ACCESS    : NONE")
print("WRITES       : NONE")
print("SYNTHETIC    : FORBIDDEN")
print("=" * 96)

print()
print("=" * 96)
print("DISCOVERY")
print("=" * 96)
print(f"Python files discovered : {len(files)}")
print(f"Files parsed            : {len(parsed)}")
print(f"Syntax failures         : {len(syntax_failures)}")


# =============================================================================
# SYNTAX FAILURES
# =============================================================================

if syntax_failures:

    print()
    print("=" * 96)
    print("SYNTAX FAILURES")
    print("=" * 96)

    for path, error in syntax_failures[:50]:
        print(f"{Path(path).name}: {error}")


# =============================================================================
# SCORER RUN
# =============================================================================

print()
print("=" * 96)
print("CONFIRMED SCORER RUNTIME ENTRY")
print("=" * 96)

if scorer_keys:

    for key in scorer_keys:

        info = functions[key]

        print(
            f"{Path(info['file']).name}:"
            f"{info['line']} "
            f"{info['qualname']}"
        )

        print(
            f"  args     = {info['args']}"
        )

        print(
            f"  features = {info['features']}"
        )

else:
    print("signal_scorer.run() NOT FOUND")


# =============================================================================
# DIRECT CALLERS
# =============================================================================

print()
print("=" * 96)
print("DIRECT CALLERS OF signal_scorer.run()")
print("=" * 96)

if run_callers:

    for call in run_callers:

        print()
        print(
            f"{Path(call['file']).name}:"
            f"{call['line']}"
        )

        print(
            f"  caller   = {call['function']}"
        )

        print(
            f"  callee   = {call['callee']}"
        )

        print(
            f"  args     = {call['args']}"
        )

        print(
            f"  features = {call['features']}"
        )

else:

    print(
        "NO DIRECT signal_scorer.run() CALLER FOUND"
    )


# =============================================================================
# COMPLETE FEATURE FUNCTIONS
# =============================================================================

print()
print("=" * 96)
print("FUNCTIONS RECEIVING ALL THREE REAL FEATURE OBJECTS")
print("=" * 96)

if complete_feature_functions:

    seen = set()

    for info in complete_feature_functions:

        key = (
            info["file"],
            info["name"],
            info["line"],
        )

        if key in seen:
            continue

        seen.add(key)

        print()
        print(
            f"{Path(info['file']).name}:"
            f"{info['line']}"
        )

        print(
            f"  function = {info['qualname']}"
        )

        print(
            f"  args     = {info['args']}"
        )

        print(
            f"  features = {info['features']}"
        )

else:

    print(
        "NO FUNCTION WITH COMPLETE FEATURE SIGNATURE FOUND"
    )


# =============================================================================
# FEATURE ASSIGNMENTS
# =============================================================================

print()
print("=" * 96)
print("REAL FEATURE OBJECT CREATION / ASSIGNMENT CANDIDATES")
print("=" * 96)

if feature_assignments:

    for item in feature_assignments:

        print()
        print(
            f"{Path(item['file']).name}:"
            f"{item['line']}"
        )

        print(
            f"  function = {item['function']}"
        )

        print(
            f"  targets  = {item['targets']}"
        )

        print(
            f"  value    = {item['value']}"
        )

else:

    print(
        "NO DIRECT FEATURE ASSIGNMENT FOUND"
    )


# =============================================================================
# FEATURE RETURNS
# =============================================================================

print()
print("=" * 96)
print("REAL FEATURE OBJECT RETURN CANDIDATES")
print("=" * 96)

if feature_returns:

    for item in feature_returns:

        print()
        print(
            f"{Path(item['file']).name}:"
            f"{item['line']}"
        )

        print(
            f"  function = {item['function']}"
        )

        print(
            f"  features = {item['features']}"
        )

        print(
            f"  return   = {item['value']}"
        )

else:

    print(
        "NO FEATURE-BEARING RETURN FOUND"
    )


# =============================================================================
# FEATURE PROPAGATION CALLS
# =============================================================================

print()
print("=" * 96)
print("REAL FEATURE PROPAGATION CALLS")
print("=" * 96)

if feature_passes:

    seen = set()

    for call in feature_passes:

        key = (
            call["file"],
            call["line"],
            call["callee"],
        )

        if key in seen:
            continue

        seen.add(key)

        print()
        print(
            f"{Path(call['file']).name}:"
            f"{call['line']}"
        )

        print(
            f"  function = {call['function']}"
        )

        print(
            f"  callee   = {call['callee']}"
        )

        print(
            f"  features = {call['features']}"
        )

        print(
            f"  args     = {call['args']}"
        )

else:

    print(
        "NO FEATURE PROPAGATION CALLS FOUND"
    )


# =============================================================================
# PRODUCER CANDIDATES
# =============================================================================

print()
print("=" * 96)
print("UPSTREAM PRODUCER CANDIDATES")
print("=" * 96)

if producer_candidates:

    seen = set()

    for info in producer_candidates:

        key = (
            info["file"],
            info["name"],
            info["line"],
        )

        if key in seen:
            continue

        seen.add(key)

        print()
        print(
            f"{Path(info['file']).name}:"
            f"{info['line']}"
        )

        print(
            f"  function = {info['qualname']}"
        )

        print(
            f"  args     = {info['args']}"
        )

        print(
            f"  features = {info['features']}"
        )

else:

    print(
        "NO PRODUCER CANDIDATE FOUND"
    )


# =============================================================================
# STATIC CHAIN
# =============================================================================

print()
print("=" * 96)
print("STATIC UPSTREAM FEATURE CHAIN")
print("=" * 96)

print(
    """
UNKNOWN REAL PRODUCER
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
DECISION ENGINE
"""
)


# =============================================================================
# VERDICT
# =============================================================================

print()
print("=" * 96)
print("FORENSIC VERDICT")
print("=" * 96)

if run_callers:

    print(
        "RESULT : DIRECT signal_scorer.run() CALLER LOCATED"
    )

    print()
    print(
        "NEXT ACTION:"
    )

    print(
        "Trace ONLY the caller's arguments upstream."
    )

    print(
        "Identify the actual construction/loading point of:"
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

else:

    print(
        "RESULT : DIRECT signal_scorer.run() CALLER STILL NOT LOCATED"
    )

    print()
    print(
        "NEXT ACTION:"
    )

    print(
        "Trace runtime scheduler/orchestrator/import boundary."
    )

    print(
        "Prioritize functions receiving the complete feature set."
    )

    print(
        "DO NOT MODIFY PRODUCTION CODE."
    )


print()
print("=" * 96)
print("M7 STATUS : COMPLETE")
print("=" * 96)