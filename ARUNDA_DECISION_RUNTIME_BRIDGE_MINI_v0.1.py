from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "signal_scorer.load_scores",
    "decision_engine.load_scores",
    "decision_engine.build_decision_snapshot",
    "build_feature_snapshot",
    "load_feature_snapshot",
}

REAL_INPUTS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)

        if left:
            return f"{left}.{node.attr}"

        return node.attr

    return None


def is_target_call(node):
    name = dotted_name(node.func)

    if not name:
        return False

    return (
        name in TARGETS
        or name.endswith(".load_scores")
        or name.endswith(".build_decision_snapshot")
    )


def argument_names(node):
    result = []

    for arg in node.args:
        name = dotted_name(arg)

        if name:
            result.append(name)

    return result


def contains_real_input(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            if child.id in REAL_INPUTS:
                return True

    return False


def scan_file(path):

    try:
        source = path.read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception:
        return []

    hits = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not is_target_call(node):
            continue

        callee = dotted_name(node.func)

        args = argument_names(node)

        real = [
            x for x in args
            if x in REAL_INPUTS
        ]

        hits.append(
            (
                node.lineno,
                callee,
                args,
                real,
            )
        )

    return hits


def main():

    print("=" * 90)
    print("ARUNDA DECISION RUNTIME BRIDGE MINI v0.1")
    print("=" * 90)

    files = list(ROOT.glob("*.py"))

    total = 0

    for path in files:

        hits = scan_file(path)

        if not hits:
            continue

        total += len(hits)

        print()
        print(f"FILE : {path.name}")

        for line, callee, args, real in hits:

            print(
                f"L{line} | {callee}"
            )

            print(
                f"  ARGS : "
                + (
                    ", ".join(args)
                    if args
                    else "<ZERO>"
                )
            )

            if real:
                print(
                    "  REAL : "
                    + ", ".join(real)
                )
            else:
                print(
                    "  REAL : NONE"
                )

    print()
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(
        "TARGET CALLS FOUND :",
        total
    )
    print("=" * 90)


if __name__ == "__main__":
    main()