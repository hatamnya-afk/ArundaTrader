import ast
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = "risk_decisions"


def source_lines(path):
    return path.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()


def is_target_value(node):
    if isinstance(node, ast.Constant):
        return (
            isinstance(node.value, str)
            and node.value.lower() == TARGET.lower()
        )

    return False


def expr_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def scan_file(path):

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        tree = ast.parse(source)

    except Exception:
        return []


    findings = []


    for node in ast.walk(tree):

        # -------------------------------------------------
        # 1. Direct assignment
        # -------------------------------------------------

        if isinstance(node, ast.Assign):

            if is_target_value(node.value):

                for target in node.targets:

                    if isinstance(target, ast.Name):

                        findings.append({
                            "kind": "TARGET_ASSIGNMENT",
                            "line": node.lineno,
                            "name": target.id,
                            "expression": expr_text(node),
                        })


        # -------------------------------------------------
        # 2. Annotated assignment
        # -------------------------------------------------

        elif isinstance(node, ast.AnnAssign):

            if is_target_value(node.value):

                if isinstance(node.target, ast.Name):

                    findings.append({
                        "kind": "TARGET_ANNOTATED_ASSIGNMENT",
                        "line": node.lineno,
                        "name": node.target.id,
                        "expression": expr_text(node),
                    })


        # -------------------------------------------------
        # 3. Function arguments / defaults
        # -------------------------------------------------

        elif isinstance(node, ast.FunctionDef):

            defaults = list(node.args.defaults)

            for arg, default in zip(
                node.args.args[-len(defaults):],
                defaults
            ):

                if is_target_value(default):

                    findings.append({
                        "kind": "TARGET_FUNCTION_DEFAULT",
                        "line": node.lineno,
                        "name": arg.arg,
                        "expression": expr_text(default),
                    })


        # -------------------------------------------------
        # 4. Containers
        # -------------------------------------------------

        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):

            if any(
                is_target_value(element)
                for element in node.elts
            ):

                findings.append({
                    "kind": "TARGET_CONTAINER",
                    "line": node.lineno,
                    "name": None,
                    "expression": expr_text(node),
                })


        # -------------------------------------------------
        # 5. Dictionary values / keys
        # -------------------------------------------------

        elif isinstance(node, ast.Dict):

            for key, value in zip(node.keys, node.values):

                if (
                    key is not None
                    and is_target_value(key)
                ) or (
                    value is not None
                    and is_target_value(value)
                ):

                    findings.append({
                        "kind": "TARGET_DICT",
                        "line": node.lineno,
                        "name": None,
                        "expression": expr_text(node),
                    })


        # -------------------------------------------------
        # 6. Calls receiving risk_decisions
        # -------------------------------------------------

        elif isinstance(node, ast.Call):

            for index, arg in enumerate(node.args):

                if is_target_value(arg):

                    findings.append({
                        "kind": "TARGET_CALL_ARGUMENT",
                        "line": node.lineno,
                        "name": expr_text(node.func),
                        "argument_index": index,
                        "expression": expr_text(node),
                    })


    return findings


def main():

    print("=" * 110)
    print("ARUNDA — RISK_DECISIONS TABLE-NAME PROPAGATION FORENSIC v0.1")
    print("=" * 110)

    print(f"ROOT   : {ROOT}")
    print(f"TARGET : {TARGET}")
    print()

    print("MODE   : STATIC SOURCE ANALYSIS ONLY")
    print("DB     : NOT OPENED")
    print("IMPORT : NONE")
    print("EXEC   : NO PRODUCTION EXECUTION")
    print()

    total = 0


    for path in sorted(ROOT.glob("*.py")):

        if path.name.startswith(
            "ARUNDA_RISK_TABLE_NAME_PROPAGATION_FORENSIC"
        ):
            continue


        findings = scan_file(path)

        for item in findings:

            total += 1

            print("-" * 110)

            print(f"FILE : {path.name}")
            print(f"KIND : {item['kind']}")
            print(f"LINE : {item['line']}")

            if item.get("name") is not None:
                print(f"NAME : {item['name']}")

            if "argument_index" in item:
                print(
                    f"ARGUMENT INDEX : "
                    f"{item['argument_index']}"
                )

            print(
                f"EXPRESSION : "
                f"{item['expression']}"
            )

            print()


    print("=" * 110)
    print("FINAL RESULT")
    print("=" * 110)

    print(
        f"RISK_DECISIONS TABLE-NAME PROPAGATION HITS : "
        f"{total}"
    )

    print()

    if total == 0:

        print(
            "RESULT : NO DIRECT TABLE-NAME PROPAGATION FOUND."
        )

        print()
        print(
            "NEXT TARGET : "
            "STRING BUILDERS / CONSTANT MAPS / SQL BUILDERS."
        )

    else:

        print(
            "RESULT : TABLE-NAME PROPAGATION CANDIDATES FOUND."
        )

        print()
        print(
            "NEXT TARGET : "
            "INSPECT ONLY THE REPORTED FILE/LINE CHAINS."
        )


if __name__ == "__main__":
    main()