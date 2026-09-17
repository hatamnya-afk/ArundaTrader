# =============================================================================
# ARUNDA TRADER — STRUCTURAL STATE BUILDER FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#   Identify the actual construction lineage of the object returned by
#   market_regime_engine.build_structural_state().
#
# MODE:
#   READ ONLY STATIC SOURCE INSPECTION
#
# HARD RULES:
#   - DO NOT execute production code
#   - DO NOT call build_structural_state()
#   - DO NOT access database
#   - DO NOT write files
#   - DO NOT modify production source
#   - DO NOT synthesize missing fields
#   - DO NOT create mappings
#   - DO NOT repair anything
#
# =============================================================================

from pathlib import Path
import ast


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = PROJECT_ROOT / "market_regime_engine.py"

FUNCTION_NAME = "build_structural_state"

EXPECTED_FIELDS = {
    "asset",
    "bos_recent",
    "choch_recent",
    "event_count",
    "points",
    "status",
    "structure_confidence",
    "structure_direction",
    "structure_point_count",
    "structure_point_type",
    "structure_strength",
    "swing_count",
}


# =============================================================================
# HELPERS
# =============================================================================

def line_text(source_lines, line_no):
    if 1 <= line_no <= len(source_lines):
        return source_lines[line_no - 1].rstrip()
    return ""


def get_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def ast_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))

    return None


def collect_calls(function_node):
    calls = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            name = ast_name(node.func)

            if name:
                calls.append(
                    (
                        node.lineno,
                        name,
                    )
                )

    return sorted(set(calls))


def collect_assignments(function_node):
    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):

            targets = []

            for target in node.targets:

                if isinstance(target, ast.Name):
                    targets.append(target.id)

                elif isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        if isinstance(element, ast.Name):
                            targets.append(element.id)

            if targets:
                results.append(
                    (
                        node.lineno,
                        targets,
                        ast.dump(
                            node.value,
                            indent=2,
                        ),
                    )
                )

        elif isinstance(node, ast.AnnAssign):

            if isinstance(node.target, ast.Name):
                results.append(
                    (
                        node.lineno,
                        [node.target.id],
                        ast.dump(
                            node.value,
                            indent=2,
                        ) if node.value else "None",
                    )
                )

    return results


def collect_returns(function_node):
    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Return):

            results.append(
                (
                    node.lineno,
                    ast.dump(
                        node.value,
                        indent=2,
                    ) if node.value else "None",
                )
            )

    return sorted(results)


def extract_dict_keys(dict_node):
    if not isinstance(dict_node, ast.Dict):
        return None

    keys = []

    for key in dict_node.keys:

        if isinstance(key, ast.Constant):
            if isinstance(key.value, str):
                keys.append(key.value)

        elif isinstance(key, ast.Str):
            keys.append(key.s)

    return keys


def find_return_dicts(function_node):
    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Return):

            if isinstance(node.value, ast.Dict):

                keys = extract_dict_keys(node.value)

                results.append(
                    (
                        node.lineno,
                        keys,
                        ast.dump(
                            node.value,
                            indent=2,
                        ),
                    )
                )

    return results


def find_dict_assignments(function_node):
    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):

            if isinstance(node.value, ast.Dict):

                keys = extract_dict_keys(node.value)

                targets = []

                for target in node.targets:

                    if isinstance(target, ast.Name):
                        targets.append(target.id)

                results.append(
                    (
                        node.lineno,
                        targets,
                        keys,
                    )
                )

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — STRUCTURAL STATE BUILDER FORENSIC v0.1")
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"TARGET       : {TARGET}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("SOURCE MUTATION : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")

    print()
    print("=" * 100)
    print("A) TARGET FUNCTION")
    print("=" * 100)

    if not TARGET.exists():
        print("ERROR : TARGET FILE NOT FOUND")
        return 1

    # -------------------------------------------------------------------------
    # IMPORTANT:
    # UTF-8-SIG handles the BOM previously observed in market_regime_engine.py
    # without modifying the source file.
    # -------------------------------------------------------------------------

    source = TARGET.read_text(
        encoding="utf-8-sig"
    )

    source_lines = source.splitlines()

    try:
        tree = ast.parse(
            source,
            filename=str(TARGET),
        )

    except SyntaxError as exc:

        print("SYNTAX ERROR")
        print(f"LINE : {exc.lineno}")
        print(f"TEXT : {exc.text}")
        print(f"ERROR: {exc.msg}")

        return 1

    function_node = get_function(
        tree,
        FUNCTION_NAME,
    )

    if function_node is None:

        print()
        print(f"FUNCTION : {FUNCTION_NAME}")
        print("STATUS   : NOT FOUND")

        return 1

    start_line = function_node.lineno
    end_line = getattr(
        function_node,
        "end_lineno",
        start_line,
    )

    print(f"FUNCTION : {FUNCTION_NAME}()")
    print(f"LINE     : {start_line}")
    print(f"END LINE : {end_line}")

    print()
    print("=" * 100)
    print("B) FUNCTION SOURCE")
    print("=" * 100)

    for line_no in range(
        start_line,
        end_line + 1,
    ):
        print(
            f"{line_no:5d} | "
            f"{line_text(source_lines, line_no)}"
        )

    # =========================================================================
    # CALLS
    # =========================================================================

    print()
    print("=" * 100)
    print("C) DIRECT CALLS INSIDE build_structural_state()")
    print("=" * 100)

    calls = collect_calls(
        function_node
    )

    if not calls:
        print("NO CALLS FOUND")

    else:
        for line_no, name in calls:
            print(
                f"LINE : {line_no}"
            )
            print(
                f"CALL : {name}"
            )

    # =========================================================================
    # ASSIGNMENTS
    # =========================================================================

    print()
    print("=" * 100)
    print("D) VARIABLE ASSIGNMENTS")
    print("=" * 100)

    assignments = collect_assignments(
        function_node
    )

    if not assignments:
        print("NO ASSIGNMENTS FOUND")

    else:

        for line_no, targets, value_ast in assignments:

            print()
            print(f"LINE    : {line_no}")
            print(
                "TARGETS : "
                + ", ".join(targets)
            )

            print("VALUE AST :")
            print(value_ast)

    # =========================================================================
    # DICT ASSIGNMENTS
    # =========================================================================

    print()
    print("=" * 100)
    print("E) DICT OBJECT CONSTRUCTION")
    print("=" * 100)

    dict_assignments = find_dict_assignments(
        function_node
    )

    if not dict_assignments:

        print(
            "NO DIRECT DICT ASSIGNMENT FOUND"
        )

    else:

        for line_no, targets, keys in dict_assignments:

            print()
            print(f"LINE    : {line_no}")

            print(
                "TARGETS : "
                + (
                    ", ".join(targets)
                    if targets
                    else "UNKNOWN"
                )
            )

            print(
                "DICT KEYS : "
                + (
                    str(keys)
                    if keys is not None
                    else "DYNAMIC / UNKNOWN"
                )
            )

    # =========================================================================
    # RETURN
    # =========================================================================

    print()
    print("=" * 100)
    print("F) RETURN STATEMENTS")
    print("=" * 100)

    returns = collect_returns(
        function_node
    )

    if not returns:

        print("NO RETURN FOUND")

    else:

        for line_no, return_ast in returns:

            print()
            print(f"LINE : {line_no}")
            print("RETURN AST :")
            print(return_ast)

    # =========================================================================
    # RETURN DICTS
    # =========================================================================

    print()
    print("=" * 100)
    print("G) DIRECT RETURN DICT ANALYSIS")
    print("=" * 100)

    return_dicts = find_return_dicts(
        function_node
    )

    if not return_dicts:

        print(
            "NO DIRECT DICT RETURN FOUND"
        )

    else:

        for line_no, keys, dump in return_dicts:

            print()
            print(f"LINE : {line_no}")

            print(
                "RETURN DICT KEYS : "
                + (
                    str(keys)
                    if keys is not None
                    else "DYNAMIC / UNKNOWN"
                )
            )

            if keys is not None:

                actual = set(keys)

                missing = sorted(
                    EXPECTED_FIELDS - actual
                )

                extra = sorted(
                    actual - EXPECTED_FIELDS
                )

                print()
                print(
                    "EXPECTED 12-FIELD OBJECT:"
                )
                print(
                    sorted(EXPECTED_FIELDS)
                )

                print()
                print(
                    "MISSING FROM DIRECT RETURN : "
                    + str(missing)
                )

                print(
                    "EXTRA IN DIRECT RETURN      : "
                    + str(extra)
                )

            print()
            print("RETURN DICT AST :")
            print(dump)

    # =========================================================================
    # BUILDER CALL LINEAGE
    # =========================================================================

    print()
    print("=" * 100)
    print("H) BUILDER CALL LINEAGE CANDIDATES")
    print("=" * 100)

    builder_candidates = []

    for line_no, name in calls:

        if name != FUNCTION_NAME:
            builder_candidates.append(
                (
                    line_no,
                    name,
                )
            )

    if not builder_candidates:

        print(
            "NO INTERNAL BUILDER CALL CANDIDATE FOUND"
        )

    else:

        for line_no, name in builder_candidates:

            print(
                f"LINE : {line_no}"
            )
            print(
                f"CANDIDATE PRODUCER : {name}"
            )

    # =========================================================================
    # GLOBAL REFERENCES TO build_structural_state
    # =========================================================================

    print()
    print("=" * 100)
    print("I) build_structural_state() REFERENCES")
    print("=" * 100)

    references = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            name = ast_name(node.func)

            if name == FUNCTION_NAME:

                references.append(
                    node.lineno
                )

    references = sorted(
        set(references)
    )

    if not references:

        print(
            "NO CALL REFERENCES FOUND"
        )

    else:

        for line_no in references:

            print(
                f"CALL LINE : {line_no}"
            )

    # =========================================================================
    # FINAL
    # =========================================================================

    print()
    print("=" * 100)
    print("J) FINAL FORENSIC DECISION")
    print("=" * 100)

    print(
        "PURPOSE : Identify the actual producer "
        "lineage of the structural-state object."
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
    print("K) SAFETY ASSERTION")
    print("=" * 100)

    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("SOURCE MUTATION : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")

    print("=" * 100)
    print("END — STRUCTURAL STATE BUILDER FORENSIC v0.1")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )