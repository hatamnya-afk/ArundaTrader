from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FIELDS = {
    "trend",
    "volatility",
    "momentum",
    "position",
    "acceleration",
}

SKIP = {
    "__pycache__",
    ".git",
    "venv",
    ".venv",
}

def node_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def main():

    print("=" * 100)
    print("ARUNDA TRADER — SEMANTIC FEATURE PRODUCER FORENSIC v0.1")
    print("=" * 100)
    print(f"PROJECT ROOT : {ROOT}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("SOURCE MUTATION : NONE")
    print("=" * 100)

    definitions = []
    assignments = []
    dict_entries = []
    references = []

    for path in ROOT.glob("*.py"):

        if path.name == Path(__file__).name:
            continue

        try:
            source = path.read_text(
                encoding="utf-8-sig"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError as e:
            print()
            print("SKIPPED SYNTAX ERROR")
            print(f"FILE : {path.name}")
            print(f"ERROR: {e}")
            continue

        for node in ast.walk(tree):

            # --------------------------------------------------------------
            # FUNCTION DEFINITIONS
            # --------------------------------------------------------------

            if isinstance(node, ast.FunctionDef):

                function_fields = set()

                for child in ast.walk(node):

                    # assignment:
                    # trend = ...
                    if isinstance(child, ast.Assign):

                        for target in child.targets:

                            if isinstance(target, ast.Name):
                                if target.id in TARGET_FIELDS:
                                    function_fields.add(target.id)

                    # annotated assignment
                    if isinstance(child, ast.AnnAssign):

                        if isinstance(
                            child.target,
                            ast.Name
                        ):
                            if child.target.id in TARGET_FIELDS:
                                function_fields.add(
                                    child.target.id
                                )

                    # dict construction
                    if isinstance(child, ast.Dict):

                        for key, value in zip(
                            child.keys,
                            child.values,
                        ):

                            if (
                                isinstance(key, ast.Constant)
                                and key.value in TARGET_FIELDS
                            ):
                                dict_entries.append(
                                    (
                                        path.name,
                                        child.lineno,
                                        node.name,
                                        key.value,
                                        ast.dump(
                                            value,
                                            indent=2,
                                        ),
                                    )
                                )

                if function_fields:

                    definitions.append(
                        (
                            path.name,
                            node.lineno,
                            node.end_lineno,
                            node.name,
                            sorted(function_fields),
                        )
                    )

            # --------------------------------------------------------------
            # DIRECT VARIABLE ASSIGNMENTS
            # --------------------------------------------------------------

            if isinstance(node, ast.Assign):

                for target in node.targets:

                    if isinstance(target, ast.Name):

                        if target.id in TARGET_FIELDS:

                            assignments.append(
                                (
                                    path.name,
                                    node.lineno,
                                    target.id,
                                    ast.dump(
                                        node.value,
                                        indent=2,
                                    ),
                                )
                            )

            # --------------------------------------------------------------
            # NAME REFERENCES
            # --------------------------------------------------------------

            if isinstance(node, ast.Name):

                if node.id in TARGET_FIELDS:

                    references.append(
                        (
                            path.name,
                            node.lineno,
                            node.id,
                            type(node.ctx).__name__,
                        )
                    )

    # ======================================================================
    # REPORT
    # ======================================================================

    print()
    print("=" * 100)
    print("A) FUNCTIONS THAT DIRECTLY PRODUCE EXPECTED SEMANTIC FIELDS")
    print("=" * 100)

    if not definitions:
        print("NONE FOUND")
    else:
        for item in definitions:

            file_name, line, end_line, func, fields = item

            print()
            print(f"FILE      : {file_name}")
            print(f"FUNCTION  : {func}()")
            print(f"LINES     : {line}-{end_line}")
            print(f"FIELDS    : {fields}")

    print()
    print("=" * 100)
    print("B) DIRECT SEMANTIC FIELD ASSIGNMENTS")
    print("=" * 100)

    if not assignments:
        print("NONE FOUND")
    else:
        for item in assignments:

            file_name, line, field, value = item

            print()
            print(f"FILE  : {file_name}")
            print(f"LINE  : {line}")
            print(f"FIELD : {field}")
            print("VALUE AST :")
            print(value)

    print()
    print("=" * 100)
    print("C) DICT CONSTRUCTION OF EXPECTED SEMANTIC FIELDS")
    print("=" * 100)

    if not dict_entries:
        print("NONE FOUND")
    else:
        for item in dict_entries:

            file_name, line, func, field, value = item

            print()
            print(f"FILE     : {file_name}")
            print(f"LINE     : {line}")
            print(f"FUNCTION : {func}()")
            print(f"FIELD    : {field}")
            print("VALUE AST :")
            print(value)

    print()
    print("=" * 100)
    print("D) FIELD REFERENCE SUMMARY")
    print("=" * 100)

    counts = {
        field: {
            "Load": 0,
            "Store": 0,
        }
        for field in TARGET_FIELDS
    }

    for file_name, line, field, ctx in references:

        if field in counts:

            if ctx == "Load":
                counts[field]["Load"] += 1

            elif ctx == "Store":
                counts[field]["Store"] += 1

    for field in sorted(TARGET_FIELDS):

        print(
            f"{field:15}"
            f"Load={counts[field]['Load']:<4}"
            f"Store={counts[field]['Store']:<4}"
        )

    print()
    print("=" * 100)
    print("E) CRITICAL LINEAGE QUESTION")
    print("=" * 100)

    missing = []

    for field in sorted(TARGET_FIELDS):

        if counts[field]["Store"] == 0:
            missing.append(field)

    if missing:

        print("NO DIRECT PRODUCER FOUND FOR:")
        for field in missing:
            print(f"  - {field}")

    else:

        print(
            "ALL FIVE EXPECTED SEMANTIC FIELDS "
            "HAVE AT LEAST ONE SOURCE-LEVEL PRODUCER."
        )

    print()
    print("=" * 100)
    print("F) SAFETY ASSERTION")
    print("=" * 100)
    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("SOURCE MUTATION : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")
    print("=" * 100)
    print("END — SEMANTIC FEATURE PRODUCER FORENSIC v0.1")
    print("=" * 100)


if __name__ == "__main__":
    main()