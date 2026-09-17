from pathlib import Path
import ast


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_FILE = ROOT / "market_regime_engine.py"

TARGET_FUNCTION = "calculate_structure"

TARGET_FIELDS = {
    "trend",
    "momentum",
    "acceleration",
    "volatility",
}


# =============================================================================
# HELPERS
# =============================================================================

def dump(node):
    return ast.dump(node, indent=2)


def node_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == name:
                return node
    return None


def parent_function_map(tree):
    result = {}

    for fn in ast.walk(tree):

        if not isinstance(fn, ast.FunctionDef):
            continue

        for node in ast.walk(fn):
            result[id(node)] = fn.name

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — CALCULATE_STRUCTURE MISSING SEMANTIC "
        "PRODUCER FORENSIC v0.1"
    )
    print("=" * 100)
    print(f"PROJECT ROOT : {ROOT}")
    print(f"TARGET FILE  : {TARGET_FILE}")
    print(f"TARGET FUNC  : {TARGET_FUNCTION}()")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("SOURCE MUTATION : NONE")
    print("NETWORK      : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")
    print("=" * 100)

    # =========================================================================
    # LOAD
    # =========================================================================

    source = TARGET_FILE.read_text(
        encoding="utf-8-sig"
    )

    tree = ast.parse(
        source,
        filename=str(TARGET_FILE),
    )

    lines = source.splitlines()

    fn = find_function(
        tree,
        TARGET_FUNCTION,
    )

    if fn is None:

        print()
        print("calculate_structure() NOT FOUND")
        return

    # =========================================================================
    # A) TARGET FUNCTION
    # =========================================================================

    print()
    print("=" * 100)
    print("A) TARGET FUNCTION")
    print("=" * 100)

    print(
        f"FUNCTION : {TARGET_FUNCTION}()"
    )

    print(
        f"LINES    : {fn.lineno}-{fn.end_lineno}"
    )

    print()
    print("SOURCE")
    print("-" * 100)

    for number in range(
        fn.lineno,
        fn.end_lineno + 1,
    ):
        print(
            f"{number:5} | {lines[number - 1]}"
        )

    # =========================================================================
    # B) TARGET FIELD REFERENCES
    # =========================================================================

    print()
    print("=" * 100)
    print("B) TARGET FIELD REFERENCES INSIDE calculate_structure()")
    print("=" * 100)

    for field in sorted(TARGET_FIELDS):

        references = []

        for node in ast.walk(fn):

            if isinstance(node, ast.Name):

                if node.id == field:

                    references.append(
                        (
                            node.lineno,
                            type(node.ctx).__name__,
                        )
                    )

            elif isinstance(node, ast.Dict):

                for key in node.keys:

                    if (
                        isinstance(key, ast.Constant)
                        and key.value == field
                    ):

                        references.append(
                            (
                                node.lineno,
                                "DICT_KEY",
                            )
                        )

        print()
        print(f"FIELD : {field}")

        if not references:

            print("  NO REFERENCES")

        else:

            for line_no, context in references:

                print(
                    f"  LINE : {line_no} | CONTEXT : {context}"
                )

    # =========================================================================
    # C) ASSIGNMENTS TO TARGET FIELDS
    # =========================================================================

    print()
    print("=" * 100)
    print("C) DIRECT ASSIGNMENTS TO TARGET FIELDS")
    print("=" * 100)

    direct_assignments = []

    for node in ast.walk(fn):

        # -------------------------------------------------------------
        # normal assignment
        # -------------------------------------------------------------

        if isinstance(node, ast.Assign):

            for target in node.targets:

                if (
                    isinstance(target, ast.Name)
                    and target.id in TARGET_FIELDS
                ):

                    direct_assignments.append(
                        (
                            target.id,
                            node.lineno,
                            node.value,
                        )
                    )

        # -------------------------------------------------------------
        # annotated assignment
        # -------------------------------------------------------------

        elif isinstance(node, ast.AnnAssign):

            if (
                isinstance(node.target, ast.Name)
                and node.target.id in TARGET_FIELDS
            ):

                direct_assignments.append(
                    (
                        node.target.id,
                        node.lineno,
                        node.value,
                    )
                )

    if not direct_assignments:

        print("NO DIRECT FIELD ASSIGNMENTS FOUND")

    else:

        for field, line_no, value in direct_assignments:

            print()
            print(f"FIELD : {field}")
            print(f"LINE  : {line_no}")
            print("VALUE AST :")
            print(dump(value))

    # =========================================================================
    # D) DICT CONSTRUCTION OF TARGET FIELDS
    # =========================================================================

    print()
    print("=" * 100)
    print("D) TARGET FIELDS USED AS DICT VALUES")
    print("=" * 100)

    dict_entries = []

    for node in ast.walk(fn):

        if not isinstance(node, ast.Dict):
            continue

        for key, value in zip(
            node.keys,
            node.values,
        ):

            if (
                isinstance(key, ast.Constant)
                and key.value in TARGET_FIELDS
            ):

                dict_entries.append(
                    (
                        key.value,
                        node.lineno,
                        value,
                    )
                )

    if not dict_entries:

        print("NO TARGET FIELD DICT ENTRIES FOUND")

    else:

        for field, line_no, value in dict_entries:

            print()
            print(f"FIELD : {field}")
            print(f"LINE  : {line_no}")
            print("VALUE AST :")
            print(dump(value))

    # =========================================================================
    # E) FUNCTION CALLS INSIDE calculate_structure()
    # =========================================================================

    print()
    print("=" * 100)
    print("E) FUNCTION CALLS INSIDE calculate_structure()")
    print("=" * 100)

    calls = []

    for node in ast.walk(fn):

        if not isinstance(node, ast.Call):
            continue

        name = node_name(node.func)

        if name is None:
            continue

        calls.append(
            (
                node.lineno,
                name,
                node,
            )
        )

    calls.sort(
        key=lambda x: x[0]
    )

    if not calls:

        print("NO FUNCTION CALLS FOUND")

    else:

        for line_no, name, node in calls:

            print()
            print(f"LINE : {line_no}")
            print(f"CALL : {name}()")
            print("CALL AST :")
            print(dump(node))

    # =========================================================================
    # F) CALLS ASSOCIATED WITH TARGET FIELDS
    # =========================================================================

    print()
    print("=" * 100)
    print("F) TARGET FIELD → POSSIBLE UPSTREAM CALL RELATION")
    print("=" * 100)

    # Look at assignments where RHS contains calls.
    for field, line_no, value in direct_assignments:

        print()
        print(f"FIELD : {field}")
        print(f"LINE  : {line_no}")

        field_calls = []

        for child in ast.walk(value):

            if isinstance(child, ast.Call):

                name = node_name(child.func)

                if name:

                    field_calls.append(
                        (
                            name,
                            child.lineno,
                            child,
                        )
                    )

        if not field_calls:

            print(
                "  NO FUNCTION CALL IN FIELD VALUE"
            )

        else:

            for name, call_line, call_node in field_calls:

                print(
                    f"  CALL : {name}()"
                )
                print(
                    f"  LINE : {call_line}"
                )
                print(
                    "  AST :"
                )
                print(
                    dump(call_node)
                )

    # =========================================================================
    # G) VARIABLES USED TO BUILD TARGET FIELDS
    # =========================================================================

    print()
    print("=" * 100)
    print("G) VARIABLES REFERENCED BY TARGET FIELD VALUES")
    print("=" * 100)

    for field, line_no, value in direct_assignments:

        names = set()

        for child in ast.walk(value):

            if isinstance(child, ast.Name):

                names.add(child.id)

        print()
        print(f"FIELD : {field}")
        print(f"LINE  : {line_no}")

        if names:

            for name in sorted(names):

                print(
                    f"  VARIABLE : {name}"
                )

        else:

            print(
                "  NO VARIABLE REFERENCES"
            )

    # =========================================================================
    # H) FIELD VALUE SOURCE CLASSIFICATION
    # =========================================================================

    print()
    print("=" * 100)
    print("H) FIELD SOURCE CLASSIFICATION")
    print("=" * 100)

    assigned_fields = {
        field
        for field, _, _ in direct_assignments
    }

    for field in sorted(TARGET_FIELDS):

        print()
        print(f"FIELD : {field}")

        if field in assigned_fields:

            print(
                "SOURCE STATUS : DIRECTLY ASSIGNED "
                "INSIDE calculate_structure()"
            )

        else:

            print(
                "SOURCE STATUS : NOT DIRECTLY ASSIGNED "
                "INSIDE calculate_structure()"
            )

            # Search for uses of same variable-like names is intentionally
            # not guessed here. We only report structural evidence.

    # =========================================================================
    # I) ALL FUNCTIONS IN TARGET FILE
    # =========================================================================

    print()
    print("=" * 100)
    print("I) FUNCTIONS AVAILABLE IN market_regime_engine.py")
    print("=" * 100)

    functions = []

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):

            functions.append(
                (
                    node.name,
                    node.lineno,
                    node.end_lineno,
                )
            )

    functions.sort(
        key=lambda x: x[1]
    )

    for name, start, end in functions:

        print(
            f"{name:40} lines={start}-{end}"
        )

    # =========================================================================
    # J) SEARCH FOR FUNCTIONS WHOSE RETURN VALUES CONTAIN TARGET FIELDS
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "J) FUNCTIONS IN market_regime_engine.py "
        "RETURNING TARGET SEMANTIC FIELDS"
    )
    print("=" * 100)

    producers = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.FunctionDef):
            continue

        for child in ast.walk(node):

            if not isinstance(child, ast.Return):
                continue

            if not isinstance(child.value, ast.Dict):
                continue

            keys = []

            for key in child.value.keys:

                if (
                    isinstance(key, ast.Constant)
                    and key.value in TARGET_FIELDS
                ):

                    keys.append(
                        key.value
                    )

            if keys:

                producers.append(
                    (
                        node.name,
                        child.lineno,
                        keys,
                        child.value,
                    )
                )

    if not producers:

        print(
            "NO FUNCTION RETURN DICT CONTAINING "
            "TARGET FIELDS FOUND"
        )

    else:

        for (
            function,
            line_no,
            fields,
            value,
        ) in producers:

            print()
            print(
                f"FUNCTION : {function}()"
            )
            print(
                f"RETURN LINE : {line_no}"
            )
            print(
                f"FIELDS : {fields}"
            )

            print(
                "RETURN AST :"
            )

            print(
                dump(value)
            )

    # =========================================================================
    # K) FINAL DECISION
    # =========================================================================

    print()
    print("=" * 100)
    print("K) FINAL FORENSIC DECISION")
    print("=" * 100)

    missing = TARGET_FIELDS - assigned_fields

    if not missing:

        print(
            "ALL FOUR TARGET FIELDS ARE DIRECTLY ASSIGNED "
            "INSIDE calculate_structure()."
        )

    else:

        print(
            "THE FOLLOWING TARGET FIELDS ARE NOT DIRECTLY "
            "ASSIGNED INSIDE calculate_structure():"
        )

        for field in sorted(missing):

            print(
                f"  - {field}"
            )

        print()
        print(
            "NEXT STEP: TRACE THE VARIABLES / FUNCTION CALLS "
            "THAT FEED THESE FIELDS."
        )

    print()
    print("=" * 100)
    print("L) SAFETY ASSERTION")
    print("=" * 100)
    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")
    print("SOURCE MUTATION : False")
    print("=" * 100)

    print()
    print(
        "END — CALCULATE_STRUCTURE MISSING SEMANTIC "
        "PRODUCER FORENSIC v0.1"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()