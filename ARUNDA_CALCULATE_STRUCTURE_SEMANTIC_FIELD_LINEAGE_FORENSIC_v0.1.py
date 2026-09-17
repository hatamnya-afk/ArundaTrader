from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FUNCTION = "calculate_structure"

TARGET_FIELDS = {
    "trend",
    "volatility",
    "momentum",
    "position",
    "acceleration",
}


# =============================================================================
# HELPERS
# =============================================================================

def safe_dump(node):
    try:
        return ast.dump(node, indent=2)
    except Exception:
        return repr(node)


def get_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def collect_target_dict_fields(node):
    found = []

    for child in ast.walk(node):

        if not isinstance(child, ast.Dict):
            continue

        for key, value in zip(
            child.keys,
            child.values,
        ):

            if (
                isinstance(key, ast.Constant)
                and key.value in TARGET_FIELDS
            ):
                found.append(
                    (
                        key.value,
                        child.lineno,
                        safe_dump(value),
                    )
                )

    return found


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — CALCULATE_STRUCTURE SEMANTIC FIELD LINEAGE FORENSIC v0.1")
    print("=" * 100)
    print(f"PROJECT ROOT : {ROOT}")
    print(f"TARGET       : {TARGET_FUNCTION}()")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("SOURCE MUTATION : NONE")
    print("NETWORK      : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")
    print("=" * 100)

    functions = {}
    callers = []
    field_assignments = []
    field_dicts = []
    field_returns = []

    # =========================================================================
    # SCAN
    # =========================================================================

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

        # ---------------------------------------------------------------------
        # FUNCTION DEFINITIONS
        # ---------------------------------------------------------------------

        for node in ast.walk(tree):

            if isinstance(node, ast.FunctionDef):

                functions[node.name] = (
                    path.name,
                    node.lineno,
                    node.end_lineno,
                    node,
                )

        # ---------------------------------------------------------------------
        # CALCULATE_STRUCTURE CALLS
        # ---------------------------------------------------------------------

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            name = get_name(node.func)

            if name == TARGET_FUNCTION:

                callers.append(
                    (
                        path.name,
                        node.lineno,
                        safe_dump(node),
                    )
                )

        # ---------------------------------------------------------------------
        # FIELD ASSIGNMENTS
        # ---------------------------------------------------------------------

        for node in ast.walk(tree):

            if isinstance(node, ast.Assign):

                for target in node.targets:

                    if (
                        isinstance(target, ast.Name)
                        and target.id in TARGET_FIELDS
                    ):

                        field_assignments.append(
                            (
                                path.name,
                                node.lineno,
                                target.id,
                                safe_dump(node.value),
                            )
                        )

            elif isinstance(node, ast.AnnAssign):

                if (
                    isinstance(node.target, ast.Name)
                    and node.target.id in TARGET_FIELDS
                ):

                    field_assignments.append(
                        (
                            path.name,
                            node.lineno,
                            node.target.id,
                            safe_dump(node.value),
                        )
                    )

        # ---------------------------------------------------------------------
        # DICT FIELDS
        # ---------------------------------------------------------------------

        for node in ast.walk(tree):

            if isinstance(node, ast.Dict):

                for key, value in zip(
                    node.keys,
                    node.values,
                ):

                    if (
                        isinstance(key, ast.Constant)
                        and key.value in TARGET_FIELDS
                    ):

                        parent_function = None

                        for candidate in ast.walk(tree):

                            if isinstance(
                                candidate,
                                ast.FunctionDef,
                            ):

                                if (
                                    candidate.lineno
                                    <= node.lineno
                                    <= candidate.end_lineno
                                ):
                                    parent_function = candidate.name

                        field_dicts.append(
                            (
                                path.name,
                                node.lineno,
                                parent_function,
                                key.value,
                                safe_dump(value),
                            )
                        )

        # ---------------------------------------------------------------------
        # RETURNS CONTAINING TARGET FIELDS
        # ---------------------------------------------------------------------

        for node in ast.walk(tree):

            if not isinstance(node, ast.Return):
                continue

            if isinstance(node.value, ast.Dict):

                keys = []

                for key in node.value.keys:

                    if (
                        isinstance(key, ast.Constant)
                        and key.value in TARGET_FIELDS
                    ):
                        keys.append(key.value)

                if keys:

                    field_returns.append(
                        (
                            path.name,
                            node.lineno,
                            keys,
                            safe_dump(node.value),
                        )
                    )

    # =========================================================================
    # A) CALCULATE_STRUCTURE DEFINITION
    # =========================================================================

    print()
    print("=" * 100)
    print("A) calculate_structure() DEFINITION")
    print("=" * 100)

    if TARGET_FUNCTION not in functions:

        print("calculate_structure() DEFINITION : NOT FOUND")

    else:

        file_name, line, end_line, node = functions[
            TARGET_FUNCTION
        ]

        print(f"FILE      : {file_name}")
        print(f"FUNCTION  : {TARGET_FUNCTION}()")
        print(f"LINES     : {line}-{end_line}")

        print()
        print("FUNCTION SOURCE")
        print("-" * 100)

        lines = source_lines_for_function(
            ROOT / file_name,
            node,
        )

        for number, text in lines:
            print(f"{number:5} | {text}")

    # =========================================================================
    # B) calculate_structure CALL SITES
    # =========================================================================

    print()
    print("=" * 100)
    print("B) calculate_structure() CALL SITES")
    print("=" * 100)

    if not callers:

        print("NO CALL SITES FOUND")

    else:

        for file_name, line, call in callers:

            print()
            print(f"FILE : {file_name}")
            print(f"LINE : {line}")
            print("CALL AST :")
            print(call)

    # =========================================================================
    # C) EXPECTED FIELD PRODUCERS
    # =========================================================================

    print()
    print("=" * 100)
    print("C) SEMANTIC FIELD DIRECT ASSIGNMENTS")
    print("=" * 100)

    if not field_assignments:

        print("NONE FOUND")

    else:

        for (
            file_name,
            line,
            field,
            value,
        ) in field_assignments:

            print()
            print(f"FILE  : {file_name}")
            print(f"LINE  : {line}")
            print(f"FIELD : {field}")
            print("VALUE AST :")
            print(value)

    # =========================================================================
    # D) DICT FIELD PRODUCERS
    # =========================================================================

    print()
    print("=" * 100)
    print("D) SEMANTIC FIELDS INSIDE DICT CONSTRUCTIONS")
    print("=" * 100)

    if not field_dicts:

        print("NONE FOUND")

    else:

        for (
            file_name,
            line,
            function,
            field,
            value,
        ) in field_dicts:

            print()
            print(f"FILE     : {file_name}")
            print(f"LINE     : {line}")
            print(f"FUNCTION : {function}")
            print(f"FIELD    : {field}")
            print("VALUE AST :")
            print(value)

    # =========================================================================
    # E) RETURN STRUCTURES
    # =========================================================================

    print()
    print("=" * 100)
    print("E) RETURN STRUCTURES CONTAINING SEMANTIC FIELDS")
    print("=" * 100)

    if not field_returns:

        print("NONE FOUND")

    else:

        for (
            file_name,
            line,
            keys,
            value,
        ) in field_returns:

            print()
            print(f"FILE : {file_name}")
            print(f"LINE : {line}")
            print(f"FIELDS : {keys}")
            print("RETURN AST :")
            print(value)

    # =========================================================================
    # F) TARGET FUNCTION INTERNAL FIELD PRODUCTION
    # =========================================================================

    print()
    print("=" * 100)
    print("F) calculate_structure() INTERNAL SEMANTIC FIELD PRODUCTION")
    print("=" * 100)

    if TARGET_FUNCTION in functions:

        file_name, line, end_line, node = functions[
            TARGET_FUNCTION
        ]

        internal_fields = []

        for child in ast.walk(node):

            if isinstance(child, ast.Assign):

                for target in child.targets:

                    if (
                        isinstance(target, ast.Name)
                        and target.id in TARGET_FIELDS
                    ):

                        internal_fields.append(
                            (
                                target.id,
                                child.lineno,
                                safe_dump(child.value),
                            )
                        )

            elif isinstance(child, ast.AnnAssign):

                if (
                    isinstance(child.target, ast.Name)
                    and child.target.id in TARGET_FIELDS
                ):

                    internal_fields.append(
                        (
                            child.target.id,
                            child.lineno,
                            safe_dump(child.value),
                        )
                    )

            elif isinstance(child, ast.Dict):

                for key, value in zip(
                    child.keys,
                    child.values,
                ):

                    if (
                        isinstance(key, ast.Constant)
                        and key.value in TARGET_FIELDS
                    ):

                        internal_fields.append(
                            (
                                key.value,
                                child.lineno,
                                safe_dump(value),
                            )
                        )

        if not internal_fields:

            print(
                "calculate_structure() DOES NOT DIRECTLY "
                "PRODUCE ANY OF THE FIVE EXPECTED FIELDS."
            )

        else:

            for field, line, value in internal_fields:

                print()
                print(f"FIELD : {field}")
                print(f"LINE  : {line}")
                print("VALUE :")
                print(value)

    else:

        print("calculate_structure() NOT FOUND")

    # =========================================================================
    # G) FIELD SUMMARY
    # =========================================================================

    print()
    print("=" * 100)
    print("G) FIELD PRODUCER SUMMARY")
    print("=" * 100)

    for field in sorted(TARGET_FIELDS):

        assignment_count = sum(
            1
            for item in field_assignments
            if item[2] == field
        )

        dict_count = sum(
            1
            for item in field_dicts
            if item[3] == field
        )

        return_count = sum(
            1
            for item in field_returns
            if field in item[2]
        )

        print(
            f"{field:15}"
            f" assignments={assignment_count:<4}"
            f" dict_entries={dict_count:<4}"
            f" returns={return_count:<4}"
        )

    # =========================================================================
    # H) FINAL FORENSIC DECISION
    # =========================================================================

    print()
    print("=" * 100)
    print("H) FINAL FORENSIC DECISION")
    print("=" * 100)

    if TARGET_FUNCTION not in functions:

        print(
            "calculate_structure() definition was not found."
        )

    else:

        file_name, line, end_line, node = functions[
            TARGET_FUNCTION
        ]

        internal = set()

        for child in ast.walk(node):

            if isinstance(child, ast.Assign):

                for target in child.targets:

                    if (
                        isinstance(target, ast.Name)
                        and target.id in TARGET_FIELDS
                    ):
                        internal.add(target.id)

            elif isinstance(child, ast.AnnAssign):

                if (
                    isinstance(child.target, ast.Name)
                    and child.target.id in TARGET_FIELDS
                ):
                    internal.add(child.target.id)

            elif isinstance(child, ast.Dict):

                for key in child.keys:

                    if (
                        isinstance(key, ast.Constant)
                        and key.value in TARGET_FIELDS
                    ):
                        internal.add(key.value)

        missing_internal = (
            TARGET_FIELDS - internal
        )

        if missing_internal:

            print(
                "calculate_structure() DOES NOT DIRECTLY "
                "PRODUCE:"
            )

            for field in sorted(missing_internal):
                print(f"  - {field}")

            print()
            print(
                "These fields must be traced upstream/downstream "
                "from the actual production lineage."
            )

        else:

            print(
                "calculate_structure() directly produces "
                "all five semantic fields."
            )

    print()
    print("=" * 100)
    print("I) SAFETY ASSERTION")
    print("=" * 100)
    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("SOURCE MUTATION : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")
    print("=" * 100)
    print(
        "END — CALCULATE_STRUCTURE SEMANTIC FIELD LINEAGE FORENSIC v0.1"
    )
    print("=" * 100)


# =============================================================================
# SOURCE DISPLAY HELPER
# =============================================================================

def source_lines_for_function(path, node):

    try:
        text = path.read_text(
            encoding="utf-8-sig"
        )
    except Exception:

        return []

    lines = text.splitlines()

    start = node.lineno
    end = node.end_lineno

    return [
        (
            number,
            lines[number - 1],
        )
        for number in range(
            start,
            min(end, len(lines)) + 1,
        )
    ]


# =============================================================================
# ENTRY
# =============================================================================

if __name__ == "__main__":
    main()