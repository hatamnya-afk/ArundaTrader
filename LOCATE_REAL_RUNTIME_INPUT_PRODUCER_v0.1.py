from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SKIP = {
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}

TARGET_VARS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

TARGET_CALLS = {
    "signal_scorer.load_scores",
    "signal_scorer.run",
    "feature_contract.load_feature_snapshot",
    "feature_contract.build_feature_snapshot",
}


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return left + "." + node.attr

    return None


def contains_target_var(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            if child.id in TARGET_VARS:
                return True
    return False


def call_info(call):
    name = dotted_name(call.func)
    if name not in TARGET_CALLS:
        return None

    args = []

    for arg in call.args:
        if isinstance(arg, ast.Name):
            args.append(arg.id)
        else:
            args.append(ast.unparse(arg))

    return name, args


print("=" * 90)
print("ARUNDA REAL RUNTIME INPUT PRODUCER LOCATOR v0.1")
print("=" * 90)

hits = []

for path in ROOT.glob("*.py"):

    if any(part in SKIP for part in path.parts):
        continue

    try:
        source = path.read_text(
            encoding="utf-8-sig"
        )
        tree = ast.parse(source)
    except Exception:
        continue

    for node in ast.walk(tree):

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        params = {
            arg.arg
            for arg in node.args.args
        }

        real_params = params & TARGET_VARS

        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                info = call_info(child)
                if info:
                    calls.append(
                        (
                            child.lineno,
                            info[0],
                            info[1],
                        )
                    )

        if real_params or calls:

            hits.append(
                (
                    path.name,
                    node.lineno,
                    node.name,
                    sorted(real_params),
                    calls,
                )
            )


print()
print("CANDIDATES :", len(hits))
print()

for filename, line, func, params, calls in hits:

    print(f"{filename}:{line} | {func}")

    if params:
        print(
            "  REAL INPUT PARAMS : "
            + ", ".join(params)
        )

    for call_line, name, args in calls:
        print(
            f"  CALL L{call_line} : {name}("
            + ", ".join(args)
            + ")"
        )

    print()

print("=" * 90)
print("END")
print("=" * 90)