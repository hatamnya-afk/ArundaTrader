# =============================================================================
# ARUNDA DECISION RUNTIME TARGETED LOCATOR v0.2
# =============================================================================

from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = {
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "execution_engine.py",
    "signal_score_contract.py",
}

TARGET_NAMES = {
    "signal_scorer.load_scores",
    "decision_engine.load_scores",
    "build_decision_snapshot",
    "decision_engine.build_decision_snapshot",
    "load_decisions",
}

INPUT_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}


def dotted(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        left = dotted(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return ""


def call_args(node):

    result = []

    for arg in node.args:

        try:
            result.append(ast.unparse(arg))
        except Exception:
            result.append("?")

    return ", ".join(result)


print("=" * 90)
print("ARUNDA DECISION RUNTIME TARGETED LOCATOR v0.2")
print("=" * 90)

found_files = 0
found_calls = 0

for filename in sorted(TARGET_FILES):

    path = ROOT / filename

    if not path.exists():
        continue

    found_files += 1

    print()
    print("-" * 90)
    print("FILE :", path)

    try:

        source = path.read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception as error:

        print(
            "PARSE ERROR :",
            type(error).__name__,
            "|",
            error
        )

        continue

    file_calls = 0

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        name = dotted(node)

        if name not in TARGET_NAMES:
            continue

        file_calls += 1
        found_calls += 1

        args = call_args(node)

        print(
            f"L{node.lineno} | "
            f"{name}("
            f"{args if args else '<ZERO ARGUMENTS>'})"
        )

    present_inputs = [
        name
        for name in INPUT_NAMES
        if name in source
    ]

    print(
        "REAL INPUT REFERENCES :",
        ", ".join(present_inputs)
        if present_inputs
        else "NONE"
    )

    if file_calls == 0:
        print("TARGET CALLS : NONE")


print()
print("=" * 90)
print("SUMMARY")
print("=" * 90)

print(
    "TARGET FILES FOUND :",
    found_files,
)

print(
    "TARGET CALLS FOUND :",
    found_calls,
)

print("=" * 90)
print("END")
print("=" * 90)