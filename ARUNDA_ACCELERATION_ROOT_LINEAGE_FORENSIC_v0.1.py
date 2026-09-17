# ARUNDA_ACCELERATION_LINEAGE_FORENSIC_v0.1.py

from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = [
    ROOT / "technical_engine.py",
    ROOT / "market_regime_engine.py",
    ROOT / "market_regime.py",
]

TARGET_FIELD = "acceleration"


def load_tree(path):
    source = path.read_text(encoding="utf-8-sig")
    return source, ast.parse(source, filename=str(path))


def function_name(node):
    return getattr(node, "name", None)


def dict_keys(node):
    if not isinstance(node, ast.Dict):
        return []

    result = []

    for key in node.keys:
        if isinstance(key, ast.Constant):
            result.append(key.value)

    return result


def ast_value(node):
    try:
        return ast.dump(node, indent=2)
    except TypeError:
        return ast.dump(node)


def main():

    print("=" * 100)
    print("ARUNDA TRADER — ACCELERATION ROOT LINEAGE FORENSIC v0.1")
    print("=" * 100)
    print(f"PROJECT ROOT : {ROOT}")
    print(f"TARGET FIELD : {TARGET_FIELD}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("SOURCE MUTATION : NONE")
    print("EXECUTION    : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")
    print("=" * 100)

    found = []

    for path in TARGETS:

        if not path.exists():
            print(f"\nFILE NOT FOUND : {path}")
            continue

        source, tree = load_tree(path)

        print("\n" + "=" * 100)
        print(f"FILE : {path.name}")
        print("=" * 100)

        for node in ast.walk(tree):

            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            fname = function_name(node)

            for child in ast.walk(node):

                # ----------------------------------------------------------
                # 1. Direct variable assignment:
                # acceleration = ...
                # ----------------------------------------------------------

                if isinstance(child, ast.Assign):

                    targets = []

                    for target in child.targets:

                        if isinstance(target, ast.Name):
                            targets.append(target.id)

                    if TARGET_FIELD in targets:

                        found.append(
                            (
                                path.name,
                                fname,
                                child.lineno,
                                "DIRECT_ASSIGNMENT",
                            )
                        )

                        print("\nDIRECT VARIABLE PRODUCER")
                        print("-" * 100)
                        print(f"FUNCTION : {fname}")
                        print(f"LINE     : {child.lineno}")
                        print(f"FIELD    : {TARGET_FIELD}")
                        print("\nVALUE AST")
                        print("-" * 100)
                        print(ast_value(child.value))

                # ----------------------------------------------------------
                # 2. Dict entry:
                # {"acceleration": acceleration}
                # ----------------------------------------------------------

                if isinstance(child, ast.Dict):

                    keys = dict_keys(child)

                    if TARGET_FIELD in keys:

                        index = keys.index(TARGET_FIELD)

                        value = child.values[index]

                        found.append(
                            (
                                path.name,
                                fname,
                                child.lineno,
                                "DICT_FIELD",
                            )
                        )

                        print("\nDICT FIELD")
                        print("-" * 100)
                        print(f"FUNCTION : {fname}")
                        print(f"LINE     : {child.lineno}")
                        print(f"FIELD    : {TARGET_FIELD}")

                        print("\nVALUE AST")
                        print("-" * 100)
                        print(ast_value(value))

                # ----------------------------------------------------------
                # 3. Function call using acceleration
                # ----------------------------------------------------------

                if isinstance(child, ast.Call):

                    for keyword in child.keywords:

                        if keyword.arg == TARGET_FIELD:

                            found.append(
                                (
                                    path.name,
                                    fname,
                                    child.lineno,
                                    "CALL_KEYWORD",
                                )
                            )

                            print("\nACCELERATION CALL CONSUMPTION")
                            print("-" * 100)
                            print(f"FUNCTION : {fname}")
                            print(f"LINE     : {child.lineno}")
                            print(f"FIELD    : {TARGET_FIELD}")

                            print("\nCALL")
                            print("-" * 100)
                            print(ast_value(child))

                # ----------------------------------------------------------
                # 4. acceleration.get(...)
                # ----------------------------------------------------------

                if isinstance(child, ast.Call):

                    func = child.func

                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr == "get"
                        and child.args
                    ):

                        arg = child.args[0]

                        if (
                            isinstance(arg, ast.Constant)
                            and arg.value == TARGET_FIELD
                        ):

                            found.append(
                                (
                                    path.name,
                                    fname,
                                    child.lineno,
                                    "GET_CONSUMPTION",
                                )
                            )

                            print("\nACCELERATION GET CONSUMPTION")
                            print("-" * 100)
                            print(f"FUNCTION : {fname}")
                            print(f"LINE     : {child.lineno}")
                            print(f"FIELD    : {TARGET_FIELD}")

                            print("\nCALL AST")
                            print("-" * 100)
                            print(ast_value(child))

    # ----------------------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    producers = [
        item
        for item in found
        if item[3] in {
            "DIRECT_ASSIGNMENT",
            "DICT_FIELD",
        }
    ]

    consumers = [
        item
        for item in found
        if item[3] in {
            "CALL_KEYWORD",
            "GET_CONSUMPTION",
        }
    ]

    print(f"\nTOTAL REFERENCES : {len(found)}")
    print(f"PRODUCERS        : {len(producers)}")
    print(f"CONSUMERS        : {len(consumers)}")

    print("\n" + "-" * 100)
    print("PRODUCER RESULT")
    print("-" * 100)

    if producers:

        for item in producers:
            print(
                f"{item[0]} | "
                f"{item[1]}() | "
                f"line {item[2]} | "
                f"{item[3]}"
            )

    else:

        print("NO CONFIRMED SOURCE-LEVEL ACCELERATION PRODUCER FOUND.")

    print("\n" + "-" * 100)
    print("FORENSIC DECISION")
    print("-" * 100)

    if producers:

        print(
            "ACCELERATION HAS A CONFIRMED SOURCE-LEVEL PRODUCER."
        )

        print(
            "NEXT ACTION: TRACE THAT PRODUCER ONE LEVEL UP "
            "UNTIL THE ORIGINAL NUMERIC/SEMANTIC SOURCE IS IDENTIFIED."
        )

    else:

        print(
            "ACCELERATION HAS NO CONFIRMED SOURCE-LEVEL PRODUCER "
            "IN THE INSPECTED FILES."
        )

        print(
            "ACCELERATION MUST NOT BE SYNTHESIZED."
        )

        print(
            "A CONTRACT REPAIR MAY BE REQUIRED ONLY AFTER "
            "THE COMPLETE PRODUCTION LINEAGE IS VERIFIED."
        )

    print("\n" + "=" * 100)
    print("SAFETY ASSERTION")
    print("=" * 100)
    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK ACCESS  : False")
    print("SOURCE MUTATION : False")
    print("=" * 100)


if __name__ == "__main__":
    main()