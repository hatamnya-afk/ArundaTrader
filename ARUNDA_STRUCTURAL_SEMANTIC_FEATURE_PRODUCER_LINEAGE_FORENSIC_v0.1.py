from pathlib import Path
import ast


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FIELDS = {
    "trend",
    "momentum",
    "acceleration",
    "volatility",
}

EXCLUDE_PREFIXES = {
    "ARUNDA_",
    "step",
}


def is_excluded(path):
    name = path.name
    return any(name.startswith(prefix) for prefix in EXCLUDE_PREFIXES)


def get_source_files():
    files = []

    for path in ROOT.glob("*.py"):
        if not is_excluded(path):
            files.append(path)

    return sorted(files)


def field_from_key(key):
    if isinstance(key, ast.Constant):
        if isinstance(key.value, str):
            return key.value

    return None


def function_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def source_segment(lines, node):
    start = node.lineno
    end = getattr(node, "end_lineno", start)

    return "\n".join(
        f"{i:5} | {lines[i - 1]}"
        for i in range(start, end + 1)
    )


def inspect_file(path):

    try:
        source = path.read_text(
            encoding="utf-8-sig"
        )
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except Exception as error:
        print()
        print("=" * 100)
        print(f"FILE : {path.name}")
        print(f"PARSE ERROR : {error}")
        return

    lines = source.splitlines()

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]

    # -------------------------------------------------------------------------
    # DIRECT DICT KEY/VALUE PRODUCERS
    # -------------------------------------------------------------------------

    for fn in functions:

        for node in ast.walk(fn):

            if not isinstance(node, ast.Dict):
                continue

            for key, value in zip(
                node.keys,
                node.values,
            ):

                field = field_from_key(key)

                if field not in TARGET_FIELDS:
                    continue

                print()
                print("=" * 100)
                print("DIRECT DICT FIELD PRODUCER")
                print("=" * 100)
                print(f"FILE     : {path.name}")
                print(f"FUNCTION : {fn.name}()")
                print(f"LINE     : {node.lineno}")
                print(f"FIELD    : {field}")

                print()
                print("VALUE AST")
                print("-" * 100)
                print(ast.dump(value, indent=2))

                print()
                print("SOURCE")
                print("-" * 100)
                print(source_segment(lines, node))

    # -------------------------------------------------------------------------
    # DIRECT ASSIGNMENTS
    # -------------------------------------------------------------------------

    for fn in functions:

        for node in ast.walk(fn):

            if isinstance(node, ast.Assign):

                for target in node.targets:

                    if (
                        isinstance(target, ast.Name)
                        and target.id in TARGET_FIELDS
                    ):

                        print()
                        print("=" * 100)
                        print("DIRECT VARIABLE PRODUCER")
                        print("=" * 100)
                        print(f"FILE     : {path.name}")
                        print(f"FUNCTION : {fn.name}()")
                        print(f"LINE     : {node.lineno}")
                        print(f"FIELD    : {target.id}")

                        print()
                        print("VALUE AST")
                        print("-" * 100)
                        print(ast.dump(node.value, indent=2))

                        print()
                        print("SOURCE")
                        print("-" * 100)
                        print(source_segment(lines, node))

            elif isinstance(node, ast.AnnAssign):

                target = node.target

                if (
                    isinstance(target, ast.Name)
                    and target.id in TARGET_FIELDS
                ):

                    print()
                    print("=" * 100)
                    print("DIRECT VARIABLE PRODUCER")
                    print("=" * 100)
                    print(f"FILE     : {path.name}")
                    print(f"FUNCTION : {fn.name}()")
                    print(f"LINE     : {node.lineno}")
                    print(f"FIELD    : {target.id}")

                    print()
                    print("VALUE AST")
                    print("-" * 100)
                    print(ast.dump(node.value, indent=2))

                    print()
                    print("SOURCE")
                    print("-" * 100)
                    print(source_segment(lines, node))

    # -------------------------------------------------------------------------
    # RETURN EXPRESSIONS REFERENCING TARGET FIELDS
    # -------------------------------------------------------------------------

    for fn in functions:

        for node in ast.walk(fn):

            if not isinstance(node, ast.Return):
                continue

            if node.value is None:
                continue

            referenced = set()

            for child in ast.walk(node.value):

                if isinstance(child, ast.Name):
                    if child.id in TARGET_FIELDS:
                        referenced.add(child.id)

                elif isinstance(child, ast.Dict):

                    for key in child.keys:

                        field = field_from_key(key)

                        if field in TARGET_FIELDS:
                            referenced.add(field)

            if referenced:

                print()
                print("=" * 100)
                print("RETURN-LEVEL FIELD PRODUCER / CONSUMER")
                print("=" * 100)
                print(f"FILE     : {path.name}")
                print(f"FUNCTION : {fn.name}()")
                print(f"LINE     : {node.lineno}")
                print(
                    "FIELDS   : "
                    + ", ".join(sorted(referenced))
                )

                print()
                print("RETURN AST")
                print("-" * 100)
                print(ast.dump(node.value, indent=2))


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — STRUCTURAL SEMANTIC FEATURE "
        "PRODUCER LINEAGE FORENSIC v0.1"
    )
    print("=" * 100)
    print(f"PROJECT ROOT : {ROOT}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("NETWORK      : NONE")
    print("SOURCE MUTATION : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")
    print("=" * 100)

    files = get_source_files()

    print()
    print("=" * 100)
    print("SOURCE FILES SCANNED")
    print("=" * 100)

    for path in files:
        print(path.name)

    for path in files:
        inspect_file(path)

    print()
    print("=" * 100)
    print("FINAL FORENSIC DECISION")
    print("=" * 100)
    print(
        "PURPOSE : Identify actual source-level producers "
        "of trend, momentum, acceleration, volatility."
    )
    print(
        "NO REPAIR WAS PERFORMED."
    )
    print(
        "NO MAPPING WAS CREATED."
    )
    print(
        "NO SYNTHETIC FIELD WAS CREATED."
    )
    print(
        "NO PRODUCTION SOURCE WAS MODIFIED."
    )

    print()
    print("=" * 100)
    print("SAFETY ASSERTION")
    print("=" * 100)
    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")
    print("SOURCE MUTATION : False")
    print("=" * 100)


if __name__ == "__main__":
    main()