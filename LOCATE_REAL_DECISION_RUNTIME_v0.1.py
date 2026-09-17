from __future__ import annotations

import ast
import os
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "decision_engine",
    "signal_scorer",
    "risk_engine",
    "execution_engine",
    "feature_contract",
    "feature_snapshot_reader",
}

FUNCTIONS = {
    "main",
    "run",
    "load_scores",
    "load_decisions",
    "build_decision_snapshot",
    "load_features",
    "load_feature_snapshot",
    "process_signals",
}


def read_source(path: Path):
    try:
        return path.read_text(
            encoding="utf-8-sig"
        )
    except Exception:
        try:
            return path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            return None


def parse(path: Path):
    source = read_source(path)

    if source is None:
        return None, None

    try:
        return source, ast.parse(
            source,
            filename=str(path),
        )
    except Exception:
        return source, None


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return ""


def call_name(node):
    return dotted_name(node.func)


def arg_summary(node):
    parts = []

    for arg in node.args:
        try:
            parts.append(
                ast.unparse(arg)
            )
        except Exception:
            parts.append("?")

    return ", ".join(parts)


def collect_files():
    result = []

    for path in ROOT.glob("*.py"):

        name = path.name

        if name.startswith("_"):
            continue

        if name.startswith("LOCATE_"):
            continue

        result.append(path)

    return sorted(result)


records = []


for path in collect_files():

    source, tree = parse(path)

    if tree is None:
        continue

    imports = set()
    functions = {}

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                imports.add(
                    alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                imports.add(
                    node.module.split(".")[0]
                )

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.setdefault(
                node.name,
                [],
            ).append(node)

    interesting_calls = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        name = call_name(node)

        if not name:
            continue

        terminal = name.split(".")[-1]

        if terminal in FUNCTIONS:

            interesting_calls.append(
                (
                    node.lineno,
                    name,
                    arg_summary(node),
                )
            )

    target_import = bool(
        imports & TARGETS
    )

    target_function = bool(
        set(functions) & FUNCTIONS
    )

    target_calls = bool(
        interesting_calls
    )

    if (
        target_import
        or target_function
        or target_calls
    ):

        records.append(
            {
                "path": path,
                "imports": sorted(
                    imports & TARGETS
                ),
                "functions": sorted(
                    set(functions) & FUNCTIONS
                ),
                "calls": interesting_calls,
            }
        )


print()
print("=" * 100)
print("ARUNDA REAL DECISION RUNTIME LOCATOR v0.1")
print("=" * 100)
print()
print("ROOT :", ROOT)
print("FILES ANALYZED :", len(collect_files()))
print("CANDIDATES :", len(records))
print()


# -------------------------------------------------------------------------
# IMPORT GRAPH
# -------------------------------------------------------------------------

print("=" * 100)
print("TARGET IMPORT GRAPH")
print("=" * 100)

for r in records:

    if not r["imports"]:
        continue

    print()
    print("FILE :", r["path"].name)

    for item in r["imports"]:
        print("  imports :", item)


# -------------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("IMPORTANT FUNCTIONS")
print("=" * 100)

for r in records:

    if not r["functions"]:
        continue

    print()
    print("FILE :", r["path"].name)

    for fn in r["functions"]:
        print("  FUNC :", fn)


# -------------------------------------------------------------------------
# CALL GRAPH
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("IMPORTANT CALL SITES")
print("=" * 100)

for r in records:

    if not r["calls"]:
        continue

    print()
    print("FILE :", r["path"])

    for line, name, args in r["calls"]:

        print(
            f"  L{line:<5} "
            f"{name}("
            f"{args}"
            f")"
        )


# -------------------------------------------------------------------------
# MAIN CANDIDATES
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("PRODUCTION MAIN CANDIDATES")
print("=" * 100)

main_candidates = []

for r in records:

    if "main" in r["functions"]:

        main_candidates.append(
            r["path"]
        )

for path in main_candidates:
    print()
    print(path)


# -------------------------------------------------------------------------
# DECISION RUNTIME CANDIDATES
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("DECISION RUNTIME CANDIDATES")
print("=" * 100)

for r in records:

    calls = r["calls"]

    interesting = []

    for line, name, args in calls:

        if name in {
            "load_scores",
            "decision_engine.load_scores",
            "signal_scorer.load_scores",
            "build_decision_snapshot",
            "decision_engine.build_decision_snapshot",
            "load_decisions",
        }:

            interesting.append(
                (
                    line,
                    name,
                    args,
                )
            )

    if not interesting:
        continue

    print()
    print("FILE :", r["path"])

    for line, name, args in interesting:

        print(
            f"  L{line:<5}"
        )

        print(
            f"    CALL : {name}"
        )

        print(
            f"    ARGS : {args or '<ZERO ARGUMENTS>'}"
        )


# -------------------------------------------------------------------------
# REAL FEATURE INPUT PROPAGATION
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("REAL FEATURE INPUT PROPAGATION")
print("=" * 100)

FEATURE_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

for r in records:

    source = read_source(
        r["path"]
    )

    if source is None:
        continue

    found = []

    for name in FEATURE_NAMES:

        if name in source:
            found.append(name)

    if found:

        print()
        print("FILE :", r["path"])
        print(
            "  INPUT REFERENCES :",
            ", ".join(found),
        )


# -------------------------------------------------------------------------
# PRINT SOURCE AROUND MAIN
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("MAIN SOURCE WINDOWS")
print("=" * 100)

for path in main_candidates:

    source, tree = parse(path)

    if tree is None:
        continue

    mains = [
        n
        for n in ast.walk(tree)
        if isinstance(
            n,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and n.name == "main"
    ]

    if not mains:
        continue

    node = mains[0]

    lines = source.splitlines()

    start = max(
        0,
        node.lineno - 1 - 30,
    )

    end = min(
        len(lines),
        getattr(
            node,
            "end_lineno",
            node.lineno + 100,
        ) + 30,
    )

    print()
    print("-" * 100)
    print("FILE :", path)
    print(
        f"MAIN LINES : {node.lineno} - "
        f"{getattr(node, 'end_lineno', '?')}"
    )
    print("-" * 100)

    for i in range(start, end):

        print(
            f"{i + 1:5d} | {lines[i]}"
        )


# -------------------------------------------------------------------------
# MODULE LEVEL ENTRY
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("MODULE LEVEL EXECUTION")
print("=" * 100)

for path in main_candidates:

    source, tree = parse(path)

    if tree is None:
        continue

    print()
    print("FILE :", path)

    for node in tree.body:

        if isinstance(
            node,
            ast.If,
        ):

            try:
                condition = ast.unparse(
                    node.test
                )
            except Exception:
                condition = "?"

            if (
                "__name__" in condition
                and "__main__" in condition
            ):

                print(
                    "  __main__ block :",
                    f"L{node.lineno}"
                )

                lines = source.splitlines()

                start = max(
                    0,
                    node.lineno - 1,
                )

                end = min(
                    len(lines),
                    getattr(
                        node,
                        "end_lineno",
                        node.lineno + 30,
                    ),
                )

                for i in range(
                    start,
                    end,
                ):

                    print(
                        f"{i + 1:5d} | "
                        f"{lines[i]}"
                    )


print()
print("=" * 100)
print("END")
print("=" * 100)