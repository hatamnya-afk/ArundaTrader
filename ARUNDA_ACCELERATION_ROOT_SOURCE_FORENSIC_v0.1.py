from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FIELD = "acceleration"

FILES = [
    ROOT / "market_regime.py",
    ROOT / "market_regime_engine.py",
    ROOT / "technical_engine.py",
    ROOT / "signal_engine.py",
    ROOT / "signal_logic.py",
]


# =============================================================================
# HELPERS
# =============================================================================

def read_source(path):
    return path.read_text(encoding="utf-8-sig")


def parse_source(path):
    source = read_source(path)
    return ast.parse(source, filename=str(path))


def node_source(source, node):
    lines = source.splitlines()
    start = max(node.lineno - 1, 0)
    end = getattr(node, "end_lineno", node.lineno)
    return "\n".join(lines[start:end])


def is_target_dict_access(node):
    """
    Detect:
        feature.get("acceleration")
        structure.get("acceleration")
        x["acceleration"]
    """

    if not isinstance(node, ast.Call):
        return False

    if not isinstance(node.func, ast.Attribute):
        return False

    if node.func.attr != "get":
        return False

    if not node.args:
        return False

    arg = node.args[0]

    return (
        isinstance(arg, ast.Constant)
        and arg.value == TARGET_FIELD
    )


def is_target_subscript(node):
    if not isinstance(node, ast.Subscript):
        return False

    slice_node = node.slice

    return (
        isinstance(slice_node, ast.Constant)
        and slice_node.value == TARGET_FIELD
    )


def get_function_nodes(tree):
    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result.append(node)

    return result


def assignment_target_names(node):

    names = []

    if isinstance(node, ast.Name):
        names.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):

        for item in node.elts:
            if isinstance(item, ast.Name):
                names.append(item.id)

    return names


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — ACCELERATION ROOT SOURCE FORENSIC v0.1")
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

    loaded = []

    # =========================================================================
    # LOAD FILES
    # =========================================================================

    for path in FILES:

        if not path.exists():
            print(f"\nFILE NOT FOUND : {path.name}")
            continue

        try:
            source = read_source(path)
            tree = ast.parse(
                source,
                filename=str(path),
            )

            loaded.append(
                {
                    "path": path,
                    "source": source,
                    "tree": tree,
                }
            )

        except SyntaxError as error:

            print("\nSYNTAX ERROR")
            print("-" * 100)
            print(f"FILE : {path.name}")
            print(f"LINE : {error.lineno}")
            print(f"ERROR: {error}")

    # =========================================================================
    # STEP 1
    # Find every actual acceleration access.
    # =========================================================================

    accesses = []

    print("\n")
    print("=" * 100)
    print("STEP 1 — ACCELERATION ACCESS POINTS")
    print("=" * 100)

    for item in loaded:

        path = item["path"]
        source = item["source"]
        tree = item["tree"]

        for function in get_function_nodes(tree):

            for node in ast.walk(function):

                matched = False

                if is_target_dict_access(node):
                    matched = True

                elif is_target_subscript(node):
                    matched = True

                if not matched:
                    continue

                accesses.append(
                    {
                        "file": path,
                        "function": function.name,
                        "line": node.lineno,
                        "node": node,
                    }
                )

                print("\nACCESS")
                print("-" * 100)
                print(f"FILE     : {path.name}")
                print(f"FUNCTION : {function.name}")
                print(f"LINE     : {node.lineno}")
                print(node_source(source, node))

    # =========================================================================
    # STEP 2
    # Find variables that feed acceleration access.
    # Example:
    #
    # feature.get("acceleration")
    #
    # => producer of feature
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("STEP 2 — CONTAINER VARIABLES FEEDING ACCELERATION")
    print("=" * 100)

    container_names = set()

    for access in accesses:

        node = access["node"]

        if isinstance(node, ast.Call):

            receiver = node.func.value

            if isinstance(receiver, ast.Name):

                container_names.add(
                    receiver.id
                )

                print(
                    f"{access['file'].name} | "
                    f"{access['function']}() | "
                    f"line {access['line']} | "
                    f"CONTAINER = {receiver.id}"
                )

        elif isinstance(node, ast.Subscript):

            receiver = node.value

            if isinstance(receiver, ast.Name):

                container_names.add(
                    receiver.id
                )

                print(
                    f"{access['file'].name} | "
                    f"{access['function']}() | "
                    f"line {access['line']} | "
                    f"CONTAINER = {receiver.id}"
                )

    # =========================================================================
    # STEP 3
    # Trace assignments of those containers.
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("STEP 3 — CONTAINER PRODUCERS")
    print("=" * 100)

    container_producers = []

    for item in loaded:

        path = item["path"]
        source = item["source"]
        tree = item["tree"]

        for function in get_function_nodes(tree):

            for node in ast.walk(function):

                if not isinstance(
                    node,
                    (ast.Assign, ast.AnnAssign),
                ):
                    continue

                if isinstance(node, ast.Assign):

                    targets = []

                    for target in node.targets:
                        targets.extend(
                            assignment_target_names(
                                target
                            )
                        )

                    value = node.value

                else:

                    targets = assignment_target_names(
                        node.target
                    )

                    value = node.value

                matched_names = [
                    name
                    for name in targets
                    if name in container_names
                ]

                if not matched_names:
                    continue

                for name in matched_names:

                    record = {
                        "file": path,
                        "function": function.name,
                        "line": node.lineno,
                        "name": name,
                        "value": value,
                        "node": node,
                    }

                    container_producers.append(
                        record
                    )

                    print("\nCONTAINER PRODUCER")
                    print("-" * 100)
                    print(f"FILE     : {path.name}")
                    print(f"FUNCTION : {function.name}")
                    print(f"LINE     : {node.lineno}")
                    print(f"VARIABLE : {name}")
                    print("\nSOURCE")
                    print("-" * 100)
                    print(node_source(source, node))

    # =========================================================================
    # STEP 4
    # Specifically inspect dictionaries containing acceleration.
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("STEP 4 — DICTIONARY CONSTRUCTION CONTAINING ACCELERATION")
    print("=" * 100)

    dict_hits = []

    for item in loaded:

        path = item["path"]
        source = item["source"]
        tree = item["tree"]

        for function in get_function_nodes(tree):

            for node in ast.walk(function):

                if not isinstance(node, ast.Dict):
                    continue

                keys = []

                for key in node.keys:

                    if isinstance(key, ast.Constant):
                        keys.append(key.value)

                if TARGET_FIELD not in keys:
                    continue

                index = keys.index(TARGET_FIELD)

                value = node.values[index]

                record = {
                    "file": path,
                    "function": function.name,
                    "line": node.lineno,
                    "value": value,
                    "node": node,
                }

                dict_hits.append(record)

                print("\nDICTIONARY CONSTRUCTION")
                print("-" * 100)
                print(f"FILE     : {path.name}")
                print(f"FUNCTION : {function.name}")
                print(f"LINE     : {node.lineno}")
                print(f"FIELD    : {TARGET_FIELD}")
                print("\nACCELERATION VALUE AST")
                print("-" * 100)
                print(
                    ast.dump(
                        value,
                        indent=2,
                    )
                )

    # =========================================================================
    # STEP 5
    # Detect direct literal / function / variable origin.
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("STEP 5 — ACCELERATION VALUE ORIGIN CLASSIFICATION")
    print("=" * 100)

    for hit in dict_hits:

        value = hit["value"]

        print("\n")
        print(f"FILE     : {hit['file'].name}")
        print(f"FUNCTION : {hit['function']}")
        print(f"LINE     : {hit['line']}")

        if isinstance(value, ast.Constant):

            print("ORIGIN   : CONSTANT")
            print(f"VALUE    : {value.value}")

        elif isinstance(value, ast.Name):

            print("ORIGIN   : VARIABLE")
            print(f"VARIABLE : {value.id}")

        elif isinstance(value, ast.Call):

            if isinstance(value.func, ast.Name):

                print("ORIGIN   : FUNCTION CALL")
                print(
                    f"FUNCTION : {value.func.id}"
                )

            elif isinstance(
                value.func,
                ast.Attribute,
            ):

                print("ORIGIN   : METHOD / ATTRIBUTE CALL")
                print(
                    f"CALL     : {ast.dump(value.func)}"
                )

            else:

                print("ORIGIN   : CALL")

        else:

            print("ORIGIN   : EXPRESSION")

    # =========================================================================
    # STEP 6
    # Find function calls that may create the acceleration value.
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("STEP 6 — POSSIBLE ACCELERATION PRODUCER FUNCTIONS")
    print("=" * 100)

    producer_function_names = set()

    for hit in dict_hits:

        value = hit["value"]

        if isinstance(value, ast.Call):

            if isinstance(
                value.func,
                ast.Name,
            ):

                producer_function_names.add(
                    value.func.id
                )

            elif isinstance(
                value.func,
                ast.Attribute,
            ):

                producer_function_names.add(
                    value.func.attr
                )

    if producer_function_names:

        for name in sorted(
            producer_function_names
        ):

            print(
                f"PRODUCER FUNCTION CANDIDATE : {name}"
            )

    else:

        print(
            "NO FUNCTION-CALL PRODUCER FOUND "
            "AT ACCELERATION DICT ENTRY."
        )

    # =========================================================================
    # STEP 7
    # Search definitions of candidate producer functions.
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("STEP 7 — PRODUCER FUNCTION DEFINITIONS")
    print("=" * 100)

    definitions_found = []

    for item in loaded:

        path = item["path"]
        source = item["source"]
        tree = item["tree"]

        for function in get_function_nodes(tree):

            if function.name not in producer_function_names:
                continue

            definitions_found.append(
                {
                    "file": path,
                    "function": function.name,
                    "line": function.lineno,
                    "node": function,
                }
            )

            print("\nPRODUCER DEFINITION")
            print("-" * 100)
            print(f"FILE     : {path.name}")
            print(f"FUNCTION : {function.name}")
            print(f"LINE     : {function.lineno}")
            print(f"END LINE : {function.end_lineno}")

            print("\nSOURCE")
            print("-" * 100)
            print(
                node_source(
                    source,
                    function,
                )
            )

    # =========================================================================
    # FINAL DECISION
    # =========================================================================

    print("\n")
    print("=" * 100)
    print("FINAL FORENSIC DECISION")
    print("=" * 100)

    if not accesses:

        print(
            "NO ACCELERATION ACCESS FOUND."
        )

    elif not dict_hits:

        print(
            "ACCELERATION IS CONSUMED, "
            "BUT NO DICTIONARY CONSTRUCTION CONTAINING "
            "ACCELERATION WAS FOUND."
        )

        print(
            "ROOT SOURCE REMAINS UNRESOLVED."
        )

    elif producer_function_names:

        print(
            "ACCELERATION HAS A FUNCTION-LEVEL "
            "PRODUCER CANDIDATE."
        )

        print(
            "NEXT LINEAGE TARGETS:"
        )

        for name in sorted(
            producer_function_names
        ):
            print(
                f"  -> {name}()"
            )

        print(
            "\nTRACE THIS FUNCTION TO ITS ORIGINAL INPUT."
        )

    else:

        print(
            "ACCELERATION IS PRESENT IN A DICT "
            "BUT ITS VALUE IS NOT CREATED BY A DIRECT "
            "FUNCTION CALL AT THAT LOCATION."
        )

        print(
            "VARIABLE-LEVEL LINEAGE MUST BE FOLLOWED."
        )

    print("\n")
    print("=" * 100)
    print("SAFETY ASSERTION")
    print("=" * 100)
    print("DATABASE ACCESS : False")
    print("DATABASE WRITE : False")
    print("FILE WRITE : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK ACCESS : False")
    print("SOURCE MUTATION : False")
    print("=" * 100)


if __name__ == "__main__":
    main()