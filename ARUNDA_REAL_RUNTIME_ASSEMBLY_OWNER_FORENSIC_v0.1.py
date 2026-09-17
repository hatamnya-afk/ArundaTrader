from __future__ import annotations

import ast
from pathlib import Path
from collections import defaultdict


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_VARS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

TARGET_FUNCTIONS = {
    "build_feature_snapshot",
    "load_feature_snapshot",
    "build_features",
    "load_features",
    "load_scores",
    "main",
    "run",
}

DOWNSTREAM_FILES = {
    "feature_contract.py",
    "feature_engine.py",
    "signal_scorer.py",
    "decision_engine.py",
}

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}


# =============================================================================
# HELPERS
# =============================================================================

def source_segment(source, node):
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


def is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def function_name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    return None


def enclosing_function(stack):
    for node in reversed(stack):
        name = function_name(node)
        if name:
            return name
    return "<MODULE>"


def target_names_in_node(node):
    found = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            if child.id in TARGET_VARS:
                found.add(child.id)

        elif isinstance(child, ast.arg):
            if child.arg in TARGET_VARS:
                found.add(child.arg)

    return found


def call_target_names(node):
    found = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            if child.id in TARGET_VARS:
                found.add(child.id)

        elif isinstance(child, ast.Attribute):
            if child.attr in TARGET_VARS:
                found.add(child.attr)

    return found


def called_name(node):
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        return func.attr

    return None


def has_db_reference(node):
    db_terms = {
        "sqlite3",
        "connect",
        "cursor",
        "execute",
        "executemany",
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "market_data",
        "market_records",
        "market_history",
    }

    text = ast.dump(node)

    return any(term in text for term in db_terms)


# =============================================================================
# SCAN CONTAINERS
# =============================================================================

files_scanned = 0
parse_errors = []

definitions = []
assignments = []
calls = []
returns = []
producer_calls = []
downstream_calls = []

function_inventory = defaultdict(
    lambda: {
        "targets": set(),
        "assignments": [],
        "calls": [],
        "returns": [],
        "db": False,
    }
)


# =============================================================================
# FILE SCAN
# =============================================================================

for path in PROJECT_ROOT.rglob("*.py"):

    if is_ignored(path):
        continue

    files_scanned += 1

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception as exc:

        parse_errors.append(
            (
                str(path),
                f"{type(exc).__name__}: {exc}",
            )
        )

        continue

    stack = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):

            stack.append(node)

            fn = node.name

            names = target_names_in_node(node)

            if names:

                definitions.append(
                    {
                        "file": str(path),
                        "line": node.lineno,
                        "function": fn,
                        "targets": sorted(names),
                    }
                )

                function_inventory[
                    (str(path), fn)
                ]["targets"].update(names)

            if has_db_reference(node):

                function_inventory[
                    (str(path), fn)
                ]["db"] = True

            self.generic_visit(node)

            stack.pop()

        def visit_AsyncFunctionDef(self, node):

            self.visit_FunctionDef(node)

        def visit_Assign(self, node):

            names = set()

            for target in node.targets:
                names.update(
                    target_names_in_node(target)
                )

            if names:

                record = {
                    "file": str(path),
                    "line": node.lineno,
                    "function": enclosing_function(stack),
                    "targets": sorted(names),
                    "source": source_segment(source, node),
                }

                assignments.append(record)

                key = (
                    str(path),
                    enclosing_function(stack),
                )

                function_inventory[key][
                    "assignments"
                ].append(record)

            self.generic_visit(node)

        def visit_AnnAssign(self, node):

            names = target_names_in_node(
                node.target
            )

            if names:

                record = {
                    "file": str(path),
                    "line": node.lineno,
                    "function": enclosing_function(stack),
                    "targets": sorted(names),
                    "source": source_segment(source, node),
                }

                assignments.append(record)

                key = (
                    str(path),
                    enclosing_function(stack),
                )

                function_inventory[key][
                    "assignments"
                ].append(record)

            self.generic_visit(node)

        def visit_Call(self, node):

            name = called_name(node)
            targets = call_target_names(node)

            if targets:

                record = {
                    "file": str(path),
                    "line": node.lineno,
                    "function": enclosing_function(stack),
                    "call": name,
                    "targets": sorted(targets),
                    "source": source_segment(source, node),
                }

                calls.append(record)

                key = (
                    str(path),
                    enclosing_function(stack),
                )

                function_inventory[key][
                    "calls"
                ].append(record)

            if name in {
                "calculate_feature_records",
                "build_feature_snapshot",
                "load_feature_snapshot",
                "load_features",
                "load_scores",
            }:

                record = {
                    "file": str(path),
                    "line": node.lineno,
                    "function": enclosing_function(stack),
                    "call": name,
                    "targets": sorted(targets),
                    "source": source_segment(source, node),
                }

                downstream_calls.append(record)

            self.generic_visit(node)

        def visit_Return(self, node):

            targets = target_names_in_node(
                node.value
            ) if node.value else set()

            if targets:

                record = {
                    "file": str(path),
                    "line": node.lineno,
                    "function": enclosing_function(stack),
                    "targets": sorted(targets),
                    "source": source_segment(source, node),
                }

                returns.append(record)

                key = (
                    str(path),
                    enclosing_function(stack),
                )

                function_inventory[key][
                    "returns"
                ].append(record)

            self.generic_visit(node)

    Visitor().visit(tree)


# =============================================================================
# MULTI-TARGET OWNERS
# =============================================================================

assembly_owners = []

for key, info in function_inventory.items():

    targets = info["targets"]

    if TARGET_VARS.issubset(targets):

        assembly_owners.append(
            (
                key,
                info,
            )
        )


# =============================================================================
# OUTPUT
# =============================================================================

print("=" * 100)
print(
    "ARUNDA TRADER — REAL RUNTIME ASSEMBLY OWNER FORENSIC v0.1"
)
print("=" * 100)

print(
    f"PROJECT ROOT : {PROJECT_ROOT}"
)

print(
    "MODE         : READ ONLY"
)

print(
    "IMPORTS      : NONE"
)

print(
    "EXECUTION    : NONE"
)

print(
    "DATABASE     : NOT TOUCHED"
)

print(
    "SOURCE EDIT  : NONE"
)

print("=" * 100)

print()
print(
    f"PYTHON FILES SCANNED : {files_scanned}"
)

# =============================================================================
# PASS 1
# =============================================================================

print()
print("=" * 100)
print("PASS 1 : TARGET VARIABLE DEFINITIONS / ASSIGNMENTS")
print("=" * 100)

if not assignments:

    print("NO TARGET ASSIGNMENTS FOUND.")

else:

    for item in assignments:

        print()
        print("-" * 100)
        print(
            f"FILE     : {item['file']}"
        )
        print(
            f"LINE     : {item['line']}"
        )
        print(
            f"FUNCTION : {item['function']}"
        )
        print(
            f"TARGETS  : {item['targets']}"
        )
        print(
            f"SOURCE   : {item['source']}"
        )


# =============================================================================
# PASS 2
# =============================================================================

print()
print("=" * 100)
print("PASS 2 : FUNCTIONS THAT KNOW MULTIPLE TARGETS")
print("=" * 100)

multi_functions = []

for key, info in function_inventory.items():

    overlap = info["targets"] & TARGET_VARS

    if len(overlap) >= 2:

        multi_functions.append(
            (
                key,
                overlap,
                info,
            )
        )

if not multi_functions:

    print("NO MULTI-TARGET FUNCTIONS FOUND.")

else:

    for key, overlap, info in multi_functions:

        file_name, fn = key

        print()
        print("-" * 100)
        print(
            f"FILE     : {file_name}"
        )
        print(
            f"FUNCTION : {fn}"
        )
        print(
            f"TARGETS  : {sorted(overlap)}"
        )
        print(
            f"DB REF   : {'YES' if info['db'] else 'NO'}"
        )


# =============================================================================
# PASS 3
# =============================================================================

print()
print("=" * 100)
print("PASS 3 : COMPLETE THREE-TARGET OWNERS")
print("=" * 100)

if not assembly_owners:

    print(
        "NO FUNCTION CURRENTLY CONTAINS ALL THREE TARGET VARIABLES."
    )

else:

    for key, info in assembly_owners:

        file_name, fn = key

        print()
        print("-" * 100)
        print(
            f"FILE     : {file_name}"
        )
        print(
            f"FUNCTION : {fn}"
        )
        print(
            f"TARGETS  : {sorted(info['targets'])}"
        )
        print(
            f"DB REF   : {'YES' if info['db'] else 'NO'}"
        )

        for item in info["assignments"]:

            print(
                f"ASSIGN   : line {item['line']} "
                f"{item['source']}"
            )

        for item in info["calls"]:

            print(
                f"CALL     : line {item['line']} "
                f"{item['call']} "
                f"{item['source']}"
            )


# =============================================================================
# PASS 4
# =============================================================================

print()
print("=" * 100)
print("PASS 4 : FEATURE / SCORER DOWNSTREAM BOUNDARIES")
print("=" * 100)

for item in downstream_calls:

    print()
    print("-" * 100)
    print(
        f"FILE     : {item['file']}"
    )
    print(
        f"LINE     : {item['line']}"
    )
    print(
        f"FUNCTION : {item['function']}"
    )
    print(
        f"CALL     : {item['call']}"
    )
    print(
        f"TARGETS  : {item['targets']}"
    )
    print(
        f"SOURCE   : {item['source']}"
    )


# =============================================================================
# PASS 5
# =============================================================================

print()
print("=" * 100)
print("PASS 5 : TARGET RETURNS")
print("=" * 100)

if not returns:

    print("NO TARGET RETURNS FOUND.")

else:

    for item in returns:

        print()
        print("-" * 100)
        print(
            f"FILE     : {item['file']}"
        )
        print(
            f"LINE     : {item['line']}"
        )
        print(
            f"FUNCTION : {item['function']}"
        )
        print(
            f"TARGETS  : {item['targets']}"
        )
        print(
            f"SOURCE   : {item['source']}"
        )


# =============================================================================
# PASS 6
# =============================================================================

print()
print("=" * 100)
print("PASS 6 : PROBABLE RUNTIME ASSEMBLY CANDIDATES")
print("=" * 100)

candidates = []

for key, info in function_inventory.items():

    overlap = info["targets"] & TARGET_VARS

    if len(overlap) >= 2:

        file_name, fn = key

        score = 0

        if len(overlap) == 3:
            score += 100

        if info["assignments"]:
            score += 20

        if info["calls"]:
            score += 10

        if info["db"]:
            score += 15

        if fn in TARGET_FUNCTIONS:
            score -= 40

        if Path(file_name).name in DOWNSTREAM_FILES:
            score -= 50

        candidates.append(
            (
                score,
                file_name,
                fn,
                sorted(overlap),
                info,
            )
        )

candidates.sort(
    reverse=True,
    key=lambda x: x[0],
)

if not candidates:

    print(
        "NO RUNTIME ASSEMBLY CANDIDATES FOUND."
    )

else:

    for rank, item in enumerate(
        candidates,
        start=1,
    ):

        score, file_name, fn, overlap, info = item

        print()
        print("-" * 100)
        print(
            f"[{rank}] SCORE    : {score}"
        )
        print(
            f"FILE       : {file_name}"
        )
        print(
            f"FUNCTION   : {fn}"
        )
        print(
            f"TARGETS    : {overlap}"
        )
        print(
            f"DB REF     : {'YES' if info['db'] else 'NO'}"
        )


# =============================================================================
# PASS 7 — REAL UPSTREAM PRODUCER SIGNALS
# =============================================================================

print()
print("=" * 100)
print("PASS 7 : UPSTREAM PRODUCER SIGNALS")
print("=" * 100)

producer_terms = (
    "fetch",
    "request",
    "response",
    "api",
    "market",
    "ohlcv",
    "kline",
    "candle",
    "bar",
    "indicator",
    "structure",
    "history",
    "records",
    "snapshot",
    "load",
    "build",
    "calculate",
    "detect",
    "generate",
)

producer_hits = []

for key, info in function_inventory.items():

    file_name, fn = key

    lower_fn = fn.lower()

    if any(
        term in lower_fn
        for term in producer_terms
    ):

        overlap = info["targets"] & TARGET_VARS

        if overlap:

            producer_hits.append(
                (
                    file_name,
                    fn,
                    sorted(overlap),
                )
            )

if not producer_hits:

    print(
        "NO UPSTREAM PRODUCER SIGNALS FOUND."
    )

else:

    for file_name, fn, overlap in producer_hits:

        print()
        print("-" * 100)
        print(
            f"FILE     : {file_name}"
        )
        print(
            f"FUNCTION : {fn}"
        )
        print(
            f"TARGETS  : {overlap}"
        )


# =============================================================================
# FINAL
# =============================================================================

print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("=" * 100)

if assembly_owners:

    print()
    print(
        "COMPLETE THREE-TARGET OWNER(S) FOUND:"
    )

    for key, info in assembly_owners:

        print(
            f"  {key[0]} :: {key[1]}"
        )

    print()
    print(
        "These are the strongest runtime-assembly ownership candidates."
    )

else:

    print()
    print(
        "NO SINGLE FUNCTION CURRENTLY OWNS ALL THREE TARGET VARIABLES."
    )

    print()
    print(
        "Therefore the assembly is likely distributed across:"
    )

    print(
        "  market-data producer"
    )

    print(
        "  -> bars producer"
    )

    print(
        "  -> indicator producer"
    )

    print(
        "  -> structure producer"
    )

    print(
        "  -> separate runtime/container assembly"
    )

print()
print(
    "IMPORTANT:"
)

print(
    "This script does NOT declare production truth from variable names alone."
)

print(
    "The final owner must be verified by caller/callee runtime reachability."
)

print()
print(
    f"PARSE ERRORS : {len(parse_errors)}"
)

for file_name, error in parse_errors:

    print(
        f"{file_name} -> {error}"
    )

print()
print(
    "NO SOURCE FILES MODIFIED."
)

print(
    "NO DATABASE ACCESSED."
)

print(
    "NO PIPELINE EXECUTED."
)

print("=" * 100)
print("SCAN COMPLETE")
print("=" * 100)