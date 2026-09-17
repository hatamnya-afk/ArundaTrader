# -*- coding: utf-8 -*-

"""
========================================================================================
ARUNDA TRADER — REAL SCORE RUNTIME ENTRYPOINT AND FEATURE ORIGIN LOCATOR v0.1
========================================================================================
MODE         : READ ONLY
EXECUTION    : STATIC AST ONLY
DB ACCESS    : NONE
WRITES       : NONE
SYNTHETIC    : FORBIDDEN

PURPOSE
-------
M5 proved that signal_scorer.run() is NOT statically reachable as a production caller.

Therefore this module does NOT assume run() is the runtime entrypoint.

This forensic locator searches for the ACTUAL runtime path into:

    signal_scorer.load_scores(
        bars_by_asset,
        indicators_by_asset,
        structures_by_asset
    )

and also detects:

    signal_scorer.load_scores()

    decision_engine.load_scores()

    signal_score_contract.load_score_snapshot()

    execution_engine.load_decisions()

The objective is to locate the first production boundary where the three
REAL feature objects exist before score generation.

NO PRODUCTION MODIFICATION.
NO DATABASE ACCESS.
NO SYNTHETIC DATA.
========================================================================================
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FEATURES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

TARGET_CALLS = {
    "signal_scorer.load_scores",
    "decision_engine.load_scores",
    "load_scores",
    "signal_score_contract.load_score_snapshot",
    "execution_engine.load_decisions",
    "load_decisions",
}


# =============================================================================
# FILE DISCOVERY
# =============================================================================

files = sorted(ROOT.rglob("*.py"))

print("=" * 96)
print("ARUNDA TRADER — REAL SCORE RUNTIME ENTRYPOINT AND FEATURE ORIGIN LOCATOR v0.1")
print("=" * 96)
print(f"PROJECT ROOT : {ROOT}")
print("MODE         : READ ONLY")
print("EXECUTION    : STATIC AST ONLY")
print("DB ACCESS    : NONE")
print("WRITES       : NONE")
print("SYNTHETIC    : FORBIDDEN")
print("=" * 96)

print(f"Python files discovered : {len(files)}")


parsed = {}
syntax_failures = []

for path in files:

    try:
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        parsed[path] = tree

    except (SyntaxError, UnicodeError) as exc:
        syntax_failures.append((path, str(exc)))


print(f"Files parsed            : {len(parsed)}")
print(f"Syntax failures         : {len(syntax_failures)}")


# =============================================================================
# HELPERS
# =============================================================================

def full_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parts = []
        cur = node

        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value

        if isinstance(cur, ast.Name):
            parts.append(cur.id)

        return ".".join(reversed(parts))

    return None


def call_full_name(node):

    if not isinstance(node, ast.Call):
        return None

    return full_name(node.func)


def names_in(node):

    result = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            result.add(child.id)

    return result


def feature_hits(node):

    return sorted(FEATURES.intersection(names_in(node)))


def enclosing_function(tree, target_line):

    best = None

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        start = node.lineno
        end = getattr(node, "end_lineno", start)

        if start <= target_line <= end:

            if best is None:
                best = node
            else:
                old_span = getattr(best, "end_lineno", best.lineno) - best.lineno
                new_span = end - start

                if new_span < old_span:
                    best = node

    return best


def params_of(function):

    if function is None:
        return []

    args = (
        list(function.args.posonlyargs)
        + list(function.args.args)
        + list(function.args.kwonlyargs)
    )

    return [a.arg for a in args]


# =============================================================================
# 1. ALL SCORE / DECISION ENTRYPOINT CALLS
# =============================================================================

print("\n" + "=" * 96)
print("ALL SCORE / DECISION RUNTIME CALLS")
print("=" * 96)

calls = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        callee = call_full_name(node)

        if callee not in TARGET_CALLS:
            continue

        args = [ast.unparse(x) for x in node.args]

        keywords = [
            f"{kw.arg}={ast.unparse(kw.value)}"
            for kw in node.keywords
        ]

        hits = feature_hits(node)

        fn = enclosing_function(tree, node.lineno)

        record = {
            "file": path,
            "line": node.lineno,
            "callee": callee,
            "args": args,
            "keywords": keywords,
            "features": hits,
            "function": fn.name if fn else "<module>",
            "params": params_of(fn),
        }

        calls.append(record)

        print()
        print(f"FILE      : {path.name}")
        print(f"LINE      : {node.lineno}")
        print(f"FUNCTION  : {record['function']}")
        print(f"CALLEE    : {callee}")
        print(f"ARGS      : {args}")
        print(f"KEYWORDS  : {keywords}")
        print(f"FEATURES  : {hits}")


# =============================================================================
# 2. COMPLETE FEATURE → SCORE CALLS
# =============================================================================

print("\n" + "=" * 96)
print("COMPLETE REAL FEATURE → SCORE CALLS")
print("=" * 96)

complete_calls = [
    c for c in calls
    if FEATURES.issubset(set(c["features"]))
]

if not complete_calls:
    print("NO DIRECT COMPLETE FEATURE → SCORE CALL FOUND")
else:

    for c in complete_calls:

        print()
        print(
            f"{c['file'].name}:{c['line']} "
            f"{c['function']} → {c['callee']}"
        )

        print(
            "  REAL INPUTS : "
            "bars_by_asset, indicators_by_asset, structures_by_asset"
        )


# =============================================================================
# 3. ZERO-INPUT SCORE CALLS
# =============================================================================

print("\n" + "=" * 96)
print("ZERO-INPUT SCORE CALLS")
print("=" * 96)

zero_calls = [
    c for c in calls
    if not c["args"] and not c["keywords"]
]

if not zero_calls:
    print("NONE")
else:

    for c in zero_calls:

        print()
        print(f"{c['file'].name}:{c['line']}")
        print(f"  function : {c['function']}")
        print(f"  callee   : {c['callee']}")
        print("  args     : []")


# =============================================================================
# 4. SEARCH FOR FEATURE-BEARING VARIABLES
# =============================================================================

print("\n" + "=" * 96)
print("FEATURE VARIABLE CREATION / ASSIGNMENT CANDIDATES")
print("=" * 96)

feature_assignments = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        targets = []

        for target in node.targets:

            if isinstance(target, ast.Name):
                targets.append(target.id)

            elif isinstance(target, (ast.Tuple, ast.List)):

                for item in target.elts:

                    if isinstance(item, ast.Name):
                        targets.append(item.id)

        hits = sorted(FEATURES.intersection(targets))

        if not hits:
            continue

        expression = ast.unparse(node.value)

        feature_assignments.append({
            "file": path,
            "line": node.lineno,
            "targets": hits,
            "expression": expression,
        })

        print()
        print(f"FILE     : {path.name}")
        print(f"LINE     : {node.lineno}")
        print(f"TARGETS  : {hits}")
        print(f"VALUE    : {expression[:600]}")


# =============================================================================
# 5. FEATURE-BEARING FUNCTION PARAMETERS
# =============================================================================

print("\n" + "=" * 96)
print("FUNCTIONS RECEIVING REAL FEATURE OBJECTS")
print("=" * 96)

feature_parameter_functions = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        params = set(params_of(node))
        hits = sorted(FEATURES.intersection(params))

        if not hits:
            continue

        feature_parameter_functions.append({
            "file": path,
            "line": node.lineno,
            "function": node.name,
            "features": hits,
            "params": sorted(params),
        })

        print()
        print(f"FILE      : {path.name}")
        print(f"FUNCTION  : {node.name}")
        print(f"LINE      : {node.lineno}")
        print(f"FEATURES  : {hits}")


# =============================================================================
# 6. FEATURE-BEARING FUNCTION CALLS
# =============================================================================

print("\n" + "=" * 96)
print("CALLS THAT PROPAGATE FEATURE OBJECTS")
print("=" * 96)

propagation_calls = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        hits = feature_hits(node)

        if not hits:
            continue

        callee = call_full_name(node)

        # Ignore obvious print/report statements.
        if callee in {"print", "append", "write", "logger.info"}:
            continue

        fn = enclosing_function(tree, node.lineno)

        args = [ast.unparse(x) for x in node.args]

        propagation_calls.append({
            "file": path,
            "line": node.lineno,
            "function": fn.name if fn else "<module>",
            "callee": callee,
            "features": hits,
            "args": args,
        })

        print()
        print(f"FILE      : {path.name}")
        print(f"LINE      : {node.lineno}")
        print(f"FUNCTION  : {fn.name if fn else '<module>'}")
        print(f"CALLEE    : {callee}")
        print(f"FEATURES  : {hits}")
        print(f"ARGS      : {args}")


# =============================================================================
# 7. RUNTIME ORCHESTRATOR CANDIDATES
# =============================================================================

print("\n" + "=" * 96)
print("RUNTIME ORCHESTRATOR CANDIDATES")
print("=" * 96)

orchestrators = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        body_names = set()

        for child in ast.walk(node):

            if isinstance(child, ast.Call):

                name = call_full_name(child)

                if name:
                    body_names.add(name)

        score_related = any(
            x in body_names
            for x in {
                "signal_scorer.load_scores",
                "load_scores",
                "decision_engine.load_scores",
                "execution_engine.load_decisions",
                "load_decisions",
            }
        )

        feature_related = bool(
            FEATURES.intersection(params_of(node))
        )

        if score_related or feature_related:

            orchestrators.append({
                "file": path,
                "function": node.name,
                "line": node.lineno,
                "score_related": score_related,
                "feature_related": feature_related,
            })

            print()
            print(f"FILE     : {path.name}")
            print(f"FUNCTION : {node.name}")
            print(f"LINE     : {node.lineno}")
            print(f"SCORE    : {score_related}")
            print(f"FEATURES : {feature_related}")


# =============================================================================
# 8. MAIN / MODULE ENTRYPOINTS
# =============================================================================

print("\n" + "=" * 96)
print("MODULE ENTRYPOINTS RELEVANT TO SCORE PATH")
print("=" * 96)

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        if node.name not in {
            "main",
            "run",
            "process",
            "process_signals",
            "load_decisions",
            "load_scores",
            "execute",
            "pipeline",
            "start",
            "loop",
        }:
            continue

        related = False

        for child in ast.walk(node):

            if isinstance(child, ast.Call):

                name = call_full_name(child)

                if name in TARGET_CALLS:
                    related = True

        if related:

            print(
                f"{path.name}:{node.lineno} "
                f"FUNCTION={node.name}"
            )


# =============================================================================
# 9. STATIC CHAIN
# =============================================================================

print("\n" + "=" * 96)
print("STATIC SCORE RUNTIME CHAIN")
print("=" * 96)

print("""
REAL FEATURE OBJECTS
        |
        |  ??? actual producer
        v
bars_by_asset
indicators_by_asset
structures_by_asset
        |
        |  ??? actual runtime propagation
        v
SIGNAL SCORER SCORE BOUNDARY
        |
        v
signal_scorer.load_scores(...)
        |
        v
DECISION ENGINE
        |
        v
build_decision_snapshot(...)
        |
        v
RISK / EXECUTION
""")


# =============================================================================
# 10. FORENSIC VERDICT
# =============================================================================

print("\n" + "=" * 96)
print("FORENSIC VERDICT")
print("=" * 96)

print(
    f"Score/decision calls found       : {len(calls)}"
)

print(
    f"Complete feature → score calls   : {len(complete_calls)}"
)

print(
    f"Zero-input score calls           : {len(zero_calls)}"
)

print(
    f"Feature parameter functions      : "
    f"{len(feature_parameter_functions)}"
)

print(
    f"Feature propagation calls        : "
    f"{len(propagation_calls)}"
)


if complete_calls:

    print()
    print("RESULT : DIRECT REAL FEATURE → SCORE RUNTIME BRIDGE FOUND")

    for c in complete_calls:

        print(
            f"  {c['file'].name}:{c['line']} "
            f"{c['function']} → {c['callee']}"
        )

    print()
    print("NEXT ACTION:")
    print("Trace ONLY the caller's upstream feature producer.")
    print("Do NOT modify production code.")

elif zero_calls:

    print()
    print(
        "RESULT : SCORE ENTRYPOINT EXISTS BUT REAL FEATURE INPUTS "
        "ARE NOT PRESENT AT THIS CALL SITE"
    )

    print()
    print("NEXT ACTION:")
    print(
        "Trace the zero-input score call backward through its "
        "runtime orchestrator."
    )

else:

    print()
    print("RESULT : NO SCORE RUNTIME ENTRYPOINT FOUND")

    print()
    print("NEXT ACTION:")
    print(
        "Locate the production scheduler/orchestrator that invokes "
        "the decision pipeline."
    )


print("\n" + "=" * 96)
print("M6 STATUS : COMPLETE")
print("=" * 96)