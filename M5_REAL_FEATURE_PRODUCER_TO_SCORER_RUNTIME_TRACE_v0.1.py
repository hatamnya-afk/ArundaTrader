# -*- coding: utf-8 -*-

"""
========================================================================================
ARUNDA TRADER — REAL FEATURE PRODUCER TO SCORER RUNTIME TRACE v0.1
========================================================================================
MODE         : READ ONLY
EXECUTION    : STATIC AST ONLY
DB ACCESS    : NONE
WRITES       : NONE
SYNTHETIC    : FORBIDDEN
RISK ENGINE  : UNTOUCHED
DECISION     : UNTOUCHED
SCORER       : UNTOUCHED

PURPOSE:
Locate the REAL production caller of:

    signal_scorer.run(
        bars_by_asset,
        indicators_by_asset,
        structures_by_asset
    )

Then trace backward only far enough to identify the actual producer/origin
of those three runtime objects.

NO CODE MODIFICATION.
NO DATABASE ACCESS.
NO SYNTHETIC DATA.
NO RECONSTRUCTION.
========================================================================================
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from collections import defaultdict


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_MODULE = "signal_scorer"
TARGET_FUNCTION = "run"

FEATURES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

# ---------------------------------------------------------------------
# Files that are clearly forensic / diagnostic / backup artifacts.
# They are not treated as production runtime callers.
# ---------------------------------------------------------------------

EXCLUDED_PREFIXES = (
    "M",
    "m",
    "STEP",
    "step",
    "AUDIT",
    "audit",
    "FORENSIC",
    "forensic",
    "DIAGNOSTIC",
    "diagnostic",
)

EXCLUDED_NAME_PARTS = (
    "backup",
    "broken",
    "corrupted",
    "quarantine",
    "_QUARANTINE",
)


def is_candidate_file(path: Path) -> bool:
    if path.suffix.lower() != ".py":
        return False

    name = path.name

    # Exclude this forensic script and obvious analysis artifacts.
    if name == Path(__file__).name:
        return False

    if any(name.startswith(p) for p in EXCLUDED_PREFIXES):
        return False

    lowered = name.lower()

    if any(part.lower() in lowered for part in EXCLUDED_NAME_PARTS):
        return False

    return True


def get_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def call_name(node):
    if not isinstance(node, ast.Call):
        return None

    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


def full_call_name(node):
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts = []
        cur = func

        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value

        if isinstance(cur, ast.Name):
            parts.append(cur.id)

        return ".".join(reversed(parts))

    return None


def extract_expr_names(node):
    names = set()

    if isinstance(node, ast.Name):
        names.add(node.id)

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)

    return names


def assigned_targets(node):
    targets = []

    if isinstance(node, ast.Assign):
        for target in node.targets:
            targets.extend(extract_target_names(target))

    elif isinstance(node, ast.AnnAssign):
        targets.extend(extract_target_names(node.target))

    elif isinstance(node, ast.AugAssign):
        targets.extend(extract_target_names(node.target))

    return targets


def extract_target_names(node):
    result = []

    if isinstance(node, ast.Name):
        result.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            result.extend(extract_target_names(element))

    elif isinstance(node, ast.Starred):
        result.extend(extract_target_names(node.value))

    return result


def contains_all_features(node):
    names = extract_expr_names(node)
    return FEATURES.issubset(names)


def feature_presence(node):
    names = extract_expr_names(node)
    return sorted(FEATURES.intersection(names))


# =============================================================================
# DISCOVERY
# =============================================================================

files = sorted(
    p for p in ROOT.rglob("*.py")
    if is_candidate_file(p)
)

print("=" * 88)
print("ARUNDA TRADER — REAL FEATURE PRODUCER TO SCORER RUNTIME TRACE v0.1")
print("=" * 88)
print(f"PROJECT ROOT : {ROOT}")
print("MODE         : READ ONLY")
print("EXECUTION    : STATIC AST ONLY")
print("DB ACCESS    : NONE")
print("WRITES       : NONE")
print("SYNTHETIC    : FORBIDDEN")
print("RISK ENGINE  : UNTOUCHED")
print("=" * 88)

print(f"Production candidate Python files : {len(files)}")


parsed = {}
syntax_failures = []

for path in files:
    try:
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        parsed[path] = tree
    except (SyntaxError, UnicodeError) as exc:
        syntax_failures.append((path, str(exc)))


print(f"Files parsed                      : {len(parsed)}")
print(f"Syntax failures                   : {len(syntax_failures)}")


# =============================================================================
# 1. LOCATE ALL REAL CALLERS OF signal_scorer.run()
# =============================================================================

print("\n" + "=" * 88)
print("SIGNAL SCORER RUN CALLERS")
print("=" * 88)

run_callers = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        name = full_call_name(node)

        if name not in {
            "signal_scorer.run",
            "run",
        }:
            continue

        # For bare run(), only accept files that import signal_scorer
        # or otherwise visibly reference signal_scorer.
        if name == "run":
            try:
                source = path.read_text(encoding="utf-8-sig")
            except Exception:
                continue

            if "signal_scorer" not in source:
                continue

        args = [ast.unparse(a) for a in node.args]
        keywords = [
            f"{kw.arg}={ast.unparse(kw.value)}"
            for kw in node.keywords
        ]

        present = feature_presence(node)

        run_callers.append({
            "file": path,
            "line": node.lineno,
            "name": name,
            "args": args,
            "keywords": keywords,
            "features": present,
            "complete": contains_all_features(node),
        })


if not run_callers:
    print("NO signal_scorer.run() CALLER FOUND")
else:
    for item in run_callers:
        print()
        print(f"FILE      : {item['file'].name}")
        print(f"LINE      : {item['line']}")
        print(f"CALLEE    : {item['name']}")
        print(f"ARGS      : {item['args']}")
        print(f"KEYWORDS  : {item['keywords']}")
        print(f"FEATURES  : {item['features']}")
        print(f"COMPLETE  : {'YES' if item['complete'] else 'NO'}")


# =============================================================================
# 2. IDENTIFY STRONG PRODUCTION CALLER
# =============================================================================

print("\n" + "=" * 88)
print("STRONG REAL FEATURE → SIGNAL SCORER CALLERS")
print("=" * 88)

strong_callers = [
    x for x in run_callers
    if x["complete"]
]

if not strong_callers:
    print("NO COMPLETE REAL FEATURE CALLER FOUND")
else:
    for item in strong_callers:
        print(
            f"{item['file'].name}:{item['line']} "
            f"→ {item['name']}("
            f"bars_by_asset, indicators_by_asset, structures_by_asset)"
        )


# =============================================================================
# 3. BACKWARD TRACE — PARAMETERS / LOCAL ASSIGNMENTS
# =============================================================================

print("\n" + "=" * 88)
print("BACKWARD FEATURE ORIGIN TRACE")
print("=" * 88)

origin_candidates = []

for caller in strong_callers:

    path = caller["file"]
    tree = parsed[path]

    target_function_node = None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)

            if start <= caller["line"] <= end:
                target_function_node = node
                break

    if target_function_node is None:
        continue

    params = {
        arg.arg
        for arg in (
            list(target_function_node.args.posonlyargs)
            + list(target_function_node.args.args)
            + list(target_function_node.args.kwonlyargs)
        )
    }

    print()
    print(f"CALLER FILE     : {path.name}")
    print(f"CALLER FUNCTION : {target_function_node.name}")
    print(f"CALLER LINE     : {caller['line']}")
    print(f"PARAMETERS      : {sorted(params)}")

    for feature in sorted(FEATURES):

        if feature in params:
            print()
            print(f"[PARAMETER ORIGIN] {feature}")
            print("  Feature enters caller from upstream runtime boundary.")

            origin_candidates.append({
                "feature": feature,
                "type": "FUNCTION_PARAMETER",
                "file": path,
                "function": target_function_node.name,
                "line": target_function_node.lineno,
            })

    # -------------------------------------------------------------
    # Scan local assignments involving the feature names.
    # -------------------------------------------------------------

    for node in ast.walk(target_function_node):

        if not isinstance(
            node,
            (ast.Assign, ast.AnnAssign, ast.AugAssign)
        ):
            continue

        assigned = assigned_targets(node)

        present = feature_presence(node)

        if not present:
            continue

        for feature in present:

            print()
            print(f"[LOCAL ORIGIN CANDIDATE] {feature}")
            print(f"  line      : {node.lineno}")
            print(f"  assigned  : {assigned}")

            if isinstance(node, ast.Assign):
                print(
                    f"  value     : {ast.unparse(node.value)[:500]}"
                )

            elif isinstance(node, ast.AnnAssign):
                if node.value is not None:
                    print(
                        f"  value     : {ast.unparse(node.value)[:500]}"
                    )

            origin_candidates.append({
                "feature": feature,
                "type": "LOCAL_ASSIGNMENT",
                "file": path,
                "function": target_function_node.name,
                "line": node.lineno,
            })


# =============================================================================
# 4. TRACE PRODUCER FUNCTIONS THAT RETURN FEATURE OBJECTS
# =============================================================================

print("\n" + "=" * 88)
print("FEATURE PRODUCER FUNCTION CANDIDATES")
print("=" * 88)

producer_candidates = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        feature_hits = set()

        for child in ast.walk(node):

            if isinstance(child, ast.Return) and child.value is not None:

                returned_names = extract_expr_names(child.value)

                feature_hits.update(
                    FEATURES.intersection(returned_names)
                )

                if contains_all_features(child.value):

                    producer_candidates.append({
                        "file": path,
                        "function": node.name,
                        "line": child.lineno,
                        "features": sorted(FEATURES),
                        "return": ast.unparse(child.value)[:500],
                    })

        if feature_hits:
            print()
            print(f"FILE     : {path.name}")
            print(f"FUNCTION : {node.name}")
            print(f"LINE     : {node.lineno}")
            print(f"FEATURES : {sorted(feature_hits)}")


# =============================================================================
# 5. SEARCH CALLS THAT RETURN / ASSIGN FEATURE OBJECTS
# =============================================================================

print("\n" + "=" * 88)
print("FEATURE OBJECT CALL-ASSIGNMENT CANDIDATES")
print("=" * 88)

call_assignments = []

for path, tree in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        if not node.targets:
            continue

        value = node.value

        if not isinstance(value, ast.Call):
            continue

        target_names = set()

        for target in node.targets:
            target_names.update(extract_target_names(target))

        hits = target_names.intersection(FEATURES)

        if not hits:
            continue

        callee = full_call_name(value)

        call_assignments.append({
            "file": path,
            "line": node.lineno,
            "targets": sorted(hits),
            "callee": callee,
            "expression": ast.unparse(value)[:500],
        })

        print()
        print(f"FILE     : {path.name}")
        print(f"LINE     : {node.lineno}")
        print(f"TARGETS  : {sorted(hits)}")
        print(f"CALLEE   : {callee}")
        print(f"EXPR     : {ast.unparse(value)[:500]}")


# =============================================================================
# 6. IMPORT / MODULE RELATIONSHIP
# =============================================================================

print("\n" + "=" * 88)
print("SCORER MODULE RELATIONSHIP")
print("=" * 88)

for path, tree in parsed.items():

    found_import = False

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "signal_scorer":
                    found_import = True

        elif isinstance(node, ast.ImportFrom):
            if node.module == "signal_scorer":
                found_import = True

    if found_import:
        print(f"{path.name}")


# =============================================================================
# 7. FINAL FORENSIC VERDICT
# =============================================================================

print("\n" + "=" * 88)
print("FORENSIC VERDICT")
print("=" * 88)

if not strong_callers:

    print("RESULT : NO COMPLETE REAL FEATURE → SIGNAL SCORER CALLER FOUND")
    print()
    print("NEXT ACTION:")
    print("Do NOT modify any production layer.")
    print("Locate the runtime scheduler / orchestrator invoking the scorer.")

else:

    print("RESULT : COMPLETE REAL FEATURE → SIGNAL SCORER RUNTIME CALLER FOUND")
    print()

    for item in strong_callers:
        print(
            f"STRONG CALLER : "
            f"{item['file'].name}:{item['line']}"
        )

    print()
    print("NEXT TRACE TARGET:")
    print("  bars_by_asset")
    print("  indicators_by_asset")
    print("  structures_by_asset")
    print()
    print("Trace ONLY their upstream origin.")
    print("Do NOT modify Decision Engine.")
    print("Do NOT modify Signal Scorer.")
    print("Do NOT modify Feature Contract.")
    print("Do NOT modify Risk Engine.")
    print("Do NOT create replacement feature data.")


print("\n" + "=" * 88)
print("M5 STATUS : COMPLETE")
print("=" * 88)