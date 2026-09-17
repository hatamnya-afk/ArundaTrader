from pathlib import Path
import ast

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = [
    PROJECT_ROOT / "market_regime.py",
    PROJECT_ROOT / "signal_engine.py",
    PROJECT_ROOT / "market_regime_contract.py",
    PROJECT_ROOT / "signal_logic.py",
]

TARGET_FUNCTION = "build_structure"

print("=" * 100)
print("ARUNDA TRADER — BUILD_STRUCTURE PRODUCER LINEAGE FORENSIC v0.1")
print("=" * 100)
print(f"PROJECT ROOT : {PROJECT_ROOT}")
print("MODE         : READ ONLY")
print("DB ACCESS    : NONE")
print("WRITE        : NONE")
print("EXECUTION    : NONE")
print("=" * 100)


def parse(path):
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def function_ranges(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = (
                node.lineno,
                getattr(node, "end_lineno", node.lineno),
            )

    return result


for path in TARGET_FILES:

    if not path.exists():
        continue

    print()
    print("=" * 100)
    print(f"FILE : {path.name}")
    print("=" * 100)

    tree = parse(path)
    ranges = function_ranges(tree)

    found = False

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        called = None

        if isinstance(node.func, ast.Name):
            called = node.func.id

        elif isinstance(node.func, ast.Attribute):
            called = node.func.attr

        if called != TARGET_FUNCTION:
            continue

        found = True

        print()
        print("-" * 100)
        print(f"CALL SITE LINE : {node.lineno}")

        if not node.args:
            print("INPUT : NO POSitional ARGUMENT")
            continue

        arg = node.args[0]

        print(f"INPUT AST TYPE : {type(arg).__name__}")

        if isinstance(arg, ast.Name):

            variable = arg.id
            print(f"INPUT VARIABLE : {variable}")

            # Find enclosing function.
            enclosing = None

            for fn in ast.walk(tree):
                if isinstance(
                    fn,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    start = fn.lineno
                    end = getattr(
                        fn,
                        "end_lineno",
                        fn.lineno,
                    )

                    if start <= node.lineno <= end:
                        enclosing = fn.name
                        break

            print(f"CALLER FUNCTION : {enclosing}")

            # Search assignments to this variable.
            print()
            print("VARIABLE ASSIGNMENTS")
            print("-" * 100)

            assignments = []

            for item in ast.walk(tree):

                if isinstance(item, ast.Assign):

                    for target in item.targets:

                        if (
                            isinstance(target, ast.Name)
                            and target.id == variable
                        ):
                            assignments.append(
                                (
                                    item.lineno,
                                    ast.dump(
                                        item.value,
                                        indent=2,
                                    ),
                                )
                            )

                elif isinstance(item, ast.AnnAssign):

                    if (
                        isinstance(
                            item.target,
                            ast.Name,
                        )
                        and item.target.id == variable
                    ):
                        assignments.append(
                            (
                                item.lineno,
                                ast.dump(
                                    item.value,
                                    indent=2,
                                )
                                if item.value
                                else "NONE",
                            )
                        )

            if not assignments:
                print(
                    f"NO STATIC ASSIGNMENT FOUND FOR "
                    f"{variable}"
                )

            else:

                for line, value in assignments:
                    print()
                    print(f"LINE : {line}")
                    print(f"VALUE AST :")
                    print(value)

        elif isinstance(arg, ast.Call):

            print(
                "INPUT IS DIRECT FUNCTION CALL:"
            )
            print(
                ast.dump(
                    arg,
                    indent=2,
                )
            )

        else:

            print(
                "INPUT EXPRESSION:"
            )
            print(
                ast.dump(
                    arg,
                    indent=2,
                )
            )

    if not found:
        print("NO build_structure() CALL FOUND")


print()
print("=" * 100)
print("FINAL FORENSIC DECISION")
print("=" * 100)

print(
    "PURPOSE : Identify the actual producer lineage "
    "of the feature passed into build_structure()."
)

print(
    "NO REPAIR WAS PERFORMED."
)

print(
    "NO PRODUCTION SOURCE WAS MODIFIED."
)

print("=" * 100)