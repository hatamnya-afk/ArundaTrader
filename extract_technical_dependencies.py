from pathlib import Path
import ast

FILE = Path(r"C:\Users\ASUS\ArundaTrader\technical_engine.py")

TARGET_FUNCTIONS = {
    "get_symbols",
    "load_history",
    "prices_from_history",
    "volumes_from_history",
}

TARGET_CLASSES = {
    "TechnicalRecord",
}

TARGET_CONSTANTS = {
    "MIN_RETURN_5_POINTS",
    "MIN_VOLATILITY_20_POINTS",
    "MIN_STRUCTURE_20_POINTS",
}


def extract_source(node, source_lines):
    start = node.lineno - 1
    end = node.end_lineno
    return "".join(source_lines[start:end])


def main():
    source = FILE.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)

    tree = ast.parse(source)

    print("=" * 100)
    print("ARUNDA TECHNICAL ENGINE — DEPENDENCY EXTRACTION")
    print("=" * 100)
    print(f"FILE: {FILE}")
    print("=" * 100)

    # ------------------------------------------------------------------
    # CONSTANTS
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("TARGET CONSTANTS")
    print("=" * 100)

    found_constants = set()

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in TARGET_CONSTANTS:
                        found_constants.add(target.id)

                        print(
                            f"\nCONSTANT: {target.id}\n"
                            f"LINES   : {node.lineno}-{node.end_lineno}\n"
                            + "-" * 100
                        )

                        print(extract_source(node, lines), end="")

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                if node.target.id in TARGET_CONSTANTS:
                    found_constants.add(node.target.id)

                    print(
                        f"\nCONSTANT: {node.target.id}\n"
                        f"LINES   : {node.lineno}-{node.end_lineno}\n"
                        + "-" * 100
                    )

                    print(extract_source(node, lines), end="")

    missing_constants = TARGET_CONSTANTS - found_constants

    if missing_constants:
        print("\nMISSING CONSTANTS:")
        for name in sorted(missing_constants):
            print(f"  - {name}")

    # ------------------------------------------------------------------
    # FUNCTIONS / CLASS
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("TARGET FUNCTIONS / CLASS")
    print("=" * 100)

    found_functions = set()
    found_classes = set()

    for node in tree.body:

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in TARGET_FUNCTIONS:
                found_functions.add(node.name)

                print(
                    f"\nFUNCTION: {node.name}\n"
                    f"LINES   : {node.lineno}-{node.end_lineno}\n"
                    f"SIGNATURE: {ast.unparse(node.args)}\n"
                    + "-" * 100
                )

                print(extract_source(node, lines), end="")

        elif isinstance(node, ast.ClassDef):
            if node.name in TARGET_CLASSES:
                found_classes.add(node.name)

                print(
                    f"\nCLASS: {node.name}\n"
                    f"LINES: {node.lineno}-{node.end_lineno}\n"
                    + "-" * 100
                )

                print(extract_source(node, lines), end="")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("EXTRACTION SUMMARY")
    print("=" * 100)

    print("\nFOUND FUNCTIONS:")
    for name in sorted(found_functions):
        print(f"  [FOUND] {name}")

    print("\nMISSING FUNCTIONS:")
    for name in sorted(TARGET_FUNCTIONS - found_functions):
        print(f"  [MISSING] {name}")

    print("\nFOUND CLASSES:")
    for name in sorted(found_classes):
        print(f"  [FOUND] {name}")

    print("\nMISSING CLASSES:")
    for name in sorted(TARGET_CLASSES - found_classes):
        print(f"  [MISSING] {name}")

    print("\n" + "=" * 100)
    print("END")
    print("=" * 100)


if __name__ == "__main__":
    main()