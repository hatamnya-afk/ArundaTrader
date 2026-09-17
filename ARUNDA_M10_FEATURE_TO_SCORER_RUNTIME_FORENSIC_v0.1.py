# ================================================================================================
# ARUNDA TRADER — M10 FEATURE → SCORER RUNTIME FORENSIC v0.1
# ================================================================================================
# MODE        : READ ONLY
# EXECUTION   : STATIC AST ONLY
# DB ACCESS   : NONE
# WRITES      : NONE
# SYNTHETIC   : FORBIDDEN
#
# PURPOSE:
#   Resolve the REAL production runtime bridge:
#
#   REAL MARKET DATA
#       ↓
#   FEATURE SNAPSHOT / FEATURE PRODUCER
#       ↓
#   bars_by_asset
#   indicators_by_asset
#   structures_by_asset
#       ↓
#   signal_scorer.load_features()
#       ↓
#   signal_scorer.load_scores()
#       ↓
#   signal_scorer.run()
#       ↓
#   DECISION ENGINE
#
# IMPORTANT:
#   This script DOES NOT modify production code.
# ================================================================================================

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from collections import defaultdict, deque


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = {
    "feature_contract.py",
    "feature_snapshot_reader.py",
    "feature_normalizer.py",
    "normalized_feature_contract.py",
    "signal_scorer.py",
    "signal_score_contract.py",
    "decision_engine.py",
    "arunda_pipeline.py",
    "arunda_source_engine.py",
    "main.py",
    "__main__.py",
}


FEATURE_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

SCORER_NAMES = {
    "run",
    "load_scores",
    "load_features",
}

FEATURE_FUNCTION_NAMES = {
    "build_features",
    "build_feature_snapshot",
    "load_feature_snapshot",
    "build_normalized_features",
    "load_features",
}

INTERESTING_CALL_NAMES = {
    "run",
    "load_scores",
    "load_features",
    "build_features",
    "build_feature_snapshot",
    "load_feature_snapshot",
    "build_normalized_features",
    "main",
}


# ------------------------------------------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------------------------------------------

class FunctionInfo:
    def __init__(self, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef):
        self.path = path
        self.node = node
        self.name = node.name
        self.lineno = node.lineno
        self.end_lineno = getattr(node, "end_lineno", node.lineno)

        self.args = [
            a.arg for a in node.args.posonlyargs
        ] + [
            a.arg for a in node.args.args
        ] + [
            a.arg for a in node.args.kwonlyargs
        ]

        self.calls = []
        self.imports = []
        self.assignments = []
        self.returns = []
        self.references = []

    @property
    def key(self):
        return f"{self.path.name}:{self.lineno}:{self.name}"


class ModuleInfo:
    def __init__(self, path: Path):
        self.path = path
        self.tree = None
        self.imports = []
        self.functions = []
        self.calls = []
        self.assignments = []
        self.references = []
        self.syntax_error = None


# ------------------------------------------------------------------------------------------------
# AST HELPERS
# ------------------------------------------------------------------------------------------------

def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr

    return None


def expr_repr(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node)


def extract_names(node):
    result = []

    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            result.append(n.id)

    return sorted(set(result))


def contains_feature_names(node):
    names = set(extract_names(node))
    return sorted(names & FEATURE_NAMES)


def call_target(node):
    if not isinstance(node, ast.Call):
        return None

    return dotted_name(node.func)


def function_from_node(path, node):
    return FunctionInfo(path, node)


# ------------------------------------------------------------------------------------------------
# PARSE
# ------------------------------------------------------------------------------------------------

def parse_target_files():
    modules = {}

    for filename in sorted(TARGET_FILES):
        path = PROJECT_ROOT / filename

        if not path.exists():
            continue

        info = ModuleInfo(path)

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            info.tree = ast.parse(
                source,
                filename=str(path),
            )

        except SyntaxError as exc:
            info.syntax_error = str(exc)
            modules[filename] = info
            continue

        modules[filename] = info

        for node in ast.walk(info.tree):

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fi = function_from_node(path, node)

                for child in ast.walk(node):

                    if isinstance(child, ast.Call):
                        target = call_target(child)

                        fi.calls.append({
                            "lineno": child.lineno,
                            "target": target,
                            "args": [expr_repr(x) for x in child.args],
                            "keywords": {
                                kw.arg: expr_repr(kw.value)
                                for kw in child.keywords
                            },
                            "features": contains_feature_names(child),
                        })

                    elif isinstance(child, (ast.Import, ast.ImportFrom)):
                        fi.imports.append({
                            "lineno": child.lineno,
                            "text": expr_repr(child),
                        })

                    elif isinstance(child, ast.Assign):
                        targets = [
                            expr_repr(x)
                            for x in child.targets
                        ]

                        fi.assignments.append({
                            "lineno": child.lineno,
                            "targets": targets,
                            "value": expr_repr(child.value),
                            "features": contains_feature_names(child.value),
                        })

                    elif isinstance(child, ast.AnnAssign):
                        fi.assignments.append({
                            "lineno": child.lineno,
                            "targets": [expr_repr(child.target)],
                            "value": (
                                expr_repr(child.value)
                                if child.value is not None
                                else None
                            ),
                            "features": contains_feature_names(child),
                        })

                    elif isinstance(child, ast.Return):
                        fi.returns.append({
                            "lineno": child.lineno,
                            "value": (
                                expr_repr(child.value)
                                if child.value is not None
                                else None
                            ),
                            "features": contains_feature_names(child),
                        })

                    elif isinstance(child, ast.Name):
                        if child.id in FEATURE_NAMES:
                            fi.references.append({
                                "lineno": child.lineno,
                                "name": child.id,
                                "context": type(child.ctx).__name__,
                            })

                info.functions.append(fi)

            elif isinstance(node, ast.Call):
                target = call_target(node)

                info.calls.append({
                    "lineno": node.lineno,
                    "target": target,
                    "args": [expr_repr(x) for x in node.args],
                    "features": contains_feature_names(node),
                })

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                info.imports.append({
                    "lineno": node.lineno,
                    "text": expr_repr(node),
                })

    return modules


# ------------------------------------------------------------------------------------------------
# IMPORT BOUNDARY
# ------------------------------------------------------------------------------------------------

def find_import_boundaries(modules):
    rows = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            if isinstance(node, ast.Import):

                for alias in node.names:

                    if (
                        alias.name == "signal_scorer"
                        or alias.name.startswith("signal_scorer.")
                    ):
                        rows.append({
                            "file": filename,
                            "line": node.lineno,
                            "kind": "import",
                            "source": alias.name,
                            "alias": alias.asname or alias.name,
                        })

            elif isinstance(node, ast.ImportFrom):

                if (
                    node.module == "signal_scorer"
                    or (
                        node.module
                        and node.module.startswith("signal_scorer.")
                    )
                ):
                    rows.append({
                        "file": filename,
                        "line": node.lineno,
                        "kind": "from_import",
                        "source": node.module,
                        "names": [
                            (a.name, a.asname)
                            for a in node.names
                        ],
                    })

    return rows


# ------------------------------------------------------------------------------------------------
# SCORER CALL SEARCH
# ------------------------------------------------------------------------------------------------

def find_scorer_calls(modules):
    rows = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            if not isinstance(node, ast.Call):
                continue

            target = call_target(node)

            if not target:
                continue

            interesting = (
                target == "signal_scorer.run"
                or target == "signal_scorer.load_scores"
                or target == "signal_scorer.load_features"
                or target in {
                    "run",
                    "load_scores",
                    "load_features",
                }
            )

            if not interesting:
                continue

            rows.append({
                "file": filename,
                "line": node.lineno,
                "target": target,
                "args": [expr_repr(x) for x in node.args],
                "keywords": {
                    kw.arg: expr_repr(kw.value)
                    for kw in node.keywords
                },
                "features": contains_feature_names(node),
            })

    return rows


# ------------------------------------------------------------------------------------------------
# FUNCTION REFERENCE / ALIAS SEARCH
# ------------------------------------------------------------------------------------------------

def find_function_references(modules):
    rows = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            # signal_scorer.run
            if isinstance(node, ast.Attribute):
                full = dotted_name(node)

                if full in {
                    "signal_scorer.run",
                    "signal_scorer.load_scores",
                    "signal_scorer.load_features",
                }:
                    parent = None

                    rows.append({
                        "file": filename,
                        "line": node.lineno,
                        "reference": full,
                        "context": type(node.ctx).__name__,
                    })

            # aliases:
            #
            # scorer = signal_scorer.run
            # runner = scorer
            #
            if isinstance(node, ast.Assign):

                value = node.value
                value_name = dotted_name(value)

                if value_name and (
                    "signal_scorer" in value_name
                    or value_name in {
                        "run",
                        "load_scores",
                        "load_features",
                    }
                ):
                    rows.append({
                        "file": filename,
                        "line": node.lineno,
                        "kind": "function_assignment",
                        "targets": [
                            expr_repr(x)
                            for x in node.targets
                        ],
                        "value": value_name,
                    })

    return rows


# ------------------------------------------------------------------------------------------------
# DYNAMIC IMPORT / GETATTR SEARCH
# ------------------------------------------------------------------------------------------------

def find_dynamic_boundaries(modules):
    rows = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            if not isinstance(node, ast.Call):
                continue

            target = call_target(node)

            if target in {
                "__import__",
                "importlib.import_module",
                "import_module",
                "getattr",
            }:

                args = [expr_repr(x) for x in node.args]

                suspicious = any(
                    "signal_scorer" in x
                    or x in {
                        "'run'",
                        '"run"',
                        "'load_scores'",
                        '"load_scores"',
                        "'load_features'",
                        '"load_features"',
                    }
                    for x in args
                )

                if suspicious:
                    rows.append({
                        "file": filename,
                        "line": node.lineno,
                        "target": target,
                        "args": args,
                    })

    return rows


# ------------------------------------------------------------------------------------------------
# FEATURE PRODUCER → CALLER
# ------------------------------------------------------------------------------------------------

def find_feature_producer_callers(modules):
    rows = []

    producer_names = {
        "build_features",
        "build_feature_snapshot",
        "load_feature_snapshot",
        "build_normalized_features",
        "load_features",
    }

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            if not isinstance(node, ast.Call):
                continue

            target = call_target(node)

            if not target:
                continue

            short_name = target.split(".")[-1]

            if short_name not in producer_names:
                continue

            rows.append({
                "file": filename,
                "line": node.lineno,
                "target": target,
                "args": [expr_repr(x) for x in node.args],
                "features": contains_feature_names(node),
            })

    return rows


# ------------------------------------------------------------------------------------------------
# FEATURE CREATION / TRANSFORMATION
# ------------------------------------------------------------------------------------------------

def find_feature_creation(modules):
    rows = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            if isinstance(node, ast.Assign):

                targets = [
                    expr_repr(x)
                    for x in node.targets
                ]

                features = contains_feature_names(node.value)

                if features:
                    rows.append({
                        "file": filename,
                        "line": node.lineno,
                        "targets": targets,
                        "value": expr_repr(node.value),
                        "features": features,
                    })

            elif isinstance(node, ast.AnnAssign):

                features = contains_feature_names(node)

                if features:
                    rows.append({
                        "file": filename,
                        "line": node.lineno,
                        "targets": [expr_repr(node.target)],
                        "value": (
                            expr_repr(node.value)
                            if node.value
                            else None
                        ),
                        "features": features,
                    })

    return rows


# ------------------------------------------------------------------------------------------------
# MAIN / ENTRYPOINT CHAIN
# ------------------------------------------------------------------------------------------------

def find_main_entrypoints(modules):
    rows = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for node in ast.walk(module.tree):

            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            if node.name != "main":
                continue

            for child in ast.walk(node):

                if isinstance(child, ast.Call):

                    target = call_target(child)

                    if target:
                        rows.append({
                            "file": filename,
                            "main_line": node.lineno,
                            "call_line": child.lineno,
                            "target": target,
                            "features": contains_feature_names(child),
                        })

    return rows


# ------------------------------------------------------------------------------------------------
# SCORE RANKING
# ------------------------------------------------------------------------------------------------

def rank_functions(modules):

    scores = []

    for filename, module in modules.items():

        if module.tree is None:
            continue

        for fn in module.functions:

            score = 0
            reasons = []

            if fn.name in FEATURE_FUNCTION_NAMES:
                score += 10
                reasons.append("feature_function_name")

            if fn.name in SCORER_NAMES:
                score += 10
                reasons.append("scorer_function_name")

            if fn.name == "main":
                score += 3
                reasons.append("main")

            feature_refs = {
                x["name"]
                for x in fn.references
                if x["name"] in FEATURE_NAMES
            }

            if feature_refs:
                score += 8
                reasons.append(
                    "feature_refs=" + ",".join(sorted(feature_refs))
                )

            scorer_calls = [
                c for c in fn.calls
                if c["target"]
                and (
                    "signal_scorer" in c["target"]
                    or c["target"] in SCORER_NAMES
                )
            ]

            if scorer_calls:
                score += 15
                reasons.append("scorer_call")

            producer_calls = [
                c for c in fn.calls
                if c["target"]
                and c["target"].split(".")[-1]
                in FEATURE_FUNCTION_NAMES
            ]

            if producer_calls:
                score += 8
                reasons.append("feature_producer_call")

            if fn.imports:
                if any(
                    "signal_scorer" in x["text"]
                    for x in fn.imports
                ):
                    score += 8
                    reasons.append("signal_scorer_import")

            if score:
                scores.append({
                    "file": filename,
                    "function": fn.name,
                    "line": fn.lineno,
                    "score": score,
                    "reasons": reasons,
                })

    return sorted(
        scores,
        key=lambda x: (-x["score"], x["file"], x["line"]),
    )


# ------------------------------------------------------------------------------------------------
# PRINT
# ------------------------------------------------------------------------------------------------

def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_rows(rows, fields):
    if not rows:
        print("NONE")
        return

    for row in rows:
        print()

        for field in fields:
            if field in row:
                print(f"{field.upper():15} : {row[field]}")


# ------------------------------------------------------------------------------------------------
# FORENSIC VERDICT
# ------------------------------------------------------------------------------------------------

def verdict(
    scorer_calls,
    feature_calls,
    imports,
    dynamic,
    references,
    feature_creation,
):
    direct_real = [
        x for x in scorer_calls
        if x.get("features")
    ]

    scorer_run = [
        x for x in scorer_calls
        if x.get("target") == "signal_scorer.run"
    ]

    real_creation = [
        x for x in feature_creation
        if x.get("features")
    ]

    section("FORENSIC VERDICT")

    print(f"signal_scorer.run calls              : {len(scorer_run)}")
    print(f"all scorer calls                     : {len(scorer_calls)}")
    print(f"feature producer calls               : {len(feature_calls)}")
    print(f"signal_scorer import boundaries      : {len(imports)}")
    print(f"dynamic scorer boundaries            : {len(dynamic)}")
    print(f"function references                 : {len(references)}")
    print(f"feature creation/assignment hits     : {len(real_creation)}")

    print()

    if direct_real:
        print("RESULT : DIRECT REAL FEATURE → SCORER BRIDGE CONFIRMED")

        for x in direct_real:
            print(
                f"  {x['file']}:{x['line']} "
                f"{x['target']} "
                f"FEATURES={x['features']}"
            )

        return

    if scorer_run:
        print("RESULT : signal_scorer.run FOUND, BUT REAL FEATURE ARGUMENTS NOT STATICALLY CONFIRMED")

        for x in scorer_run:
            print(
                f"  {x['file']}:{x['line']} "
                f"ARGS={x['args']}"
            )

        return

    if dynamic:
        print("RESULT : POSSIBLE DYNAMIC SCORER BOUNDARY FOUND")

        for x in dynamic:
            print(
                f"  {x['file']}:{x['line']} "
                f"{x['target']} "
                f"ARGS={x['args']}"
            )

        return

    print("RESULT : DIRECT STATIC SCORER CALL STILL UNRESOLVED")

    print()
    print("MOST IMPORTANT REMAINING QUESTION:")
    print(
        "Which production function invokes the feature snapshot loader "
        "and subsequently reaches the scorer?"
    )


# ------------------------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------------------------

def main():

    print("=" * 100)
    print("ARUNDA TRADER — M10 FEATURE → SCORER RUNTIME FORENSIC v0.1")
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ ONLY")
    print("EXECUTION    : STATIC AST ONLY")
    print("DB ACCESS    : NONE")
    print("WRITES       : NONE")
    print("SYNTHETIC    : FORBIDDEN")

    if not PROJECT_ROOT.exists():
        print()
        print("ERROR: PROJECT ROOT NOT FOUND")
        return 1

    modules = parse_target_files()

    section("TARGET FILE PARSING")

    for filename, module in modules.items():

        if module.syntax_error:
            print(
                f"{filename:45} : SYNTAX FAILURE"
            )
            print(
                f"  {module.syntax_error}"
            )
        else:
            print(
                f"{filename:45} : PARSED"
            )

    imports = find_import_boundaries(modules)
    scorer_calls = find_scorer_calls(modules)
    references = find_function_references(modules)
    dynamic = find_dynamic_boundaries(modules)
    feature_calls = find_feature_producer_callers(modules)
    feature_creation = find_feature_creation(modules)
    main_calls = find_main_entrypoints(modules)
    rankings = rank_functions(modules)

    section("1 — SIGNAL SCORER IMPORT / ALIAS BOUNDARY")

    print_rows(
        imports,
        [
            "file",
            "line",
            "kind",
            "source",
            "alias",
            "names",
        ],
    )

    section("2 — SIGNAL SCORER CALLS")

    print_rows(
        scorer_calls,
        [
            "file",
            "line",
            "target",
            "args",
            "keywords",
            "features",
        ],
    )

    section("3 — FUNCTION REFERENCES / WRAPPERS")

    print_rows(
        references,
        [
            "file",
            "line",
            "reference",
            "context",
            "kind",
            "targets",
            "value",
        ],
    )

    section("4 — DYNAMIC IMPORT / GETATTR BOUNDARIES")

    print_rows(
        dynamic,
        [
            "file",
            "line",
            "target",
            "args",
        ],
    )

    section("5 — FEATURE PRODUCER CALLS")

    print_rows(
        feature_calls,
        [
            "file",
            "line",
            "target",
            "args",
            "features",
        ],
    )

    section("6 — FEATURE OBJECT CREATION / TRANSFORMATION")

    print_rows(
        feature_creation,
        [
            "file",
            "line",
            "targets",
            "value",
            "features",
        ],
    )

    section("7 — MAIN ENTRYPOINT → INTERNAL CALLS")

    print_rows(
        main_calls,
        [
            "file",
            "main_line",
            "call_line",
            "target",
            "features",
        ],
    )

    section("8 — HIGHEST VALUE PRODUCTION FUNCTIONS")

    for row in rankings[:30]:
        print()
        print(
            f"{row['score']:3}  "
            f"{row['file']}:{row['line']}  "
            f"{row['function']}"
        )
        print(
            f"     REASONS : {', '.join(row['reasons'])}"
        )

    verdict(
        scorer_calls,
        feature_calls,
        imports,
        dynamic,
        references,
        feature_creation,
    )

    section("STATIC CHAIN")

    print(
        """
REAL MARKET DATA
       |
       v
FEATURE PRODUCER / SNAPSHOT
       |
       v
bars_by_asset
indicators_by_asset
structures_by_asset
       |
       v
feature_snapshot_reader
       |
       v
feature_normalizer
       |
       v
signal_scorer.load_features()
       |
       v
signal_scorer.load_scores()
       |
       v
signal_scorer.run()
       |
       v
DECISION ENGINE
       |
       v
RISK / EXECUTION
"""
    )

    section("M10 STATUS")

    print("COMPLETE")
    print()
    print("NO PRODUCTION MODIFICATION PERFORMED.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())