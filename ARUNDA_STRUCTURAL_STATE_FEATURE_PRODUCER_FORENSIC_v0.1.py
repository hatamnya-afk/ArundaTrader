from pathlib import Path
import ast

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = PROJECT_ROOT / "market_regime_engine.py"


def read_source():
    # READ ONLY — BOM is removed only from the in-memory string.
    raw = TARGET.read_text(
        encoding="utf-8-sig"
    )
    return raw


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def direct_called_functions(function_node):
    calls = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)

            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

    return sorted(set(calls))


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — "
        "STRUCTURAL STATE FEATURE PRODUCER FORENSIC v0.1"
    )
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"TARGET       : {TARGET}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("SOURCE MUTATION : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")

    if not TARGET.exists():
        print()
        print("TARGET FILE NOT FOUND")
        return

    source = read_source()

    # Parse only the in-memory representation.
    tree = ast.parse(
        source,
        filename=str(TARGET),
    )

    loader = find_function(
        tree,
        "load_structural_state",
    )

    print()
    print("=" * 100)
    print("A) PRODUCER FUNCTION")
    print("=" * 100)

    if loader is None:
        print("load_structural_state() : NOT FOUND")
        return

    print("FUNCTION : load_structural_state()")
    print(f"LINE     : {loader.lineno}")

    end_line = getattr(
        loader,
        "end_lineno",
        loader.lineno,
    )

    print(f"END LINE : {end_line}")

    lines = source.splitlines()

    print()
    print("SOURCE")
    print("-" * 100)

    for number in range(
        loader.lineno,
        min(end_line, len(lines)) + 1,
    ):
        print(
            f"{number:5} | {lines[number - 1]}"
        )

    print()
    print("=" * 100)
    print("B) DIRECT CALLS INSIDE PRODUCER")
    print("=" * 100)

    calls = direct_called_functions(loader)

    if not calls:
        print("NO DIRECT FUNCTION CALLS")
    else:
        for name in calls:
            print(f"CALL : {name}")

    print()
    print("=" * 100)
    print("C) RETURN STATEMENTS")
    print("=" * 100)

    returns = []

    for node in ast.walk(loader):

        if isinstance(node, ast.Return):

            returns.append(
                (
                    node.lineno,
                    ast.dump(
                        node.value,
                        indent=2,
                    )
                    if node.value is not None
                    else "None",
                )
            )

    if not returns:
        print("NO RETURN STATEMENTS")
    else:
        for line, value in returns:
            print()
            print(f"LINE : {line}")
            print("RETURN AST :")
            print(value)

    print()
    print("=" * 100)
    print("D) STRUCTURAL-STATE ASSIGNMENTS")
    print("=" * 100)

    found_assignment = False

    for node in ast.walk(loader):

        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):

            text = ast.dump(
                node,
                indent=2,
            )

            if (
                "structural" in text.lower()
                or "state" in text.lower()
            ):

                found_assignment = True

                print()
                print(f"LINE : {node.lineno}")
                print(text)

    if not found_assignment:
        print("NO STRUCTURAL-STATE ASSIGNMENT FOUND")

    print()
    print("=" * 100)
    print("E) PRODUCER LINEAGE")
    print("=" * 100)

    print("market_regime.py")
    print("    ↓")
    print("market_regime_engine.load_structural_state()")
    print("    ↓")

    if calls:

        for name in calls:

            if name != "load_structural_state":
                print(f"    → {name}()")

    print()
    print("=" * 100)
    print("F) SAFETY ASSERTION")
    print("=" * 100)

    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("SOURCE MUTATION : False")
    print("EXECUTION       : False")
    print("NETWORK ACCESS  : False")

    print("=" * 100)


if __name__ == "__main__":
    main()