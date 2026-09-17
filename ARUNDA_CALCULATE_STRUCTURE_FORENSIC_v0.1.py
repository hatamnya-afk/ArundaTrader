# =============================================================================
# ARUNDA TRADER — CALCULATE STRUCTURE FORENSIC v0.1
# =============================================================================
#
# MODE:
#   READ ONLY STATIC SOURCE INSPECTION
#
# PURPOSE:
#   Identify the actual producer contract of calculate_structure()
#
# SAFETY:
#   - No production execution
#   - No database access
#   - No file write
#   - No source mutation
#   - No signal generation
#   - No synthetic fields
#   - No mapping
#   - No repair
#
# =============================================================================

from pathlib import Path
import ast
import tokenize


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = PROJECT_ROOT / "market_regime_engine.py"


# =============================================================================
# SOURCE LOADER
# =============================================================================

def load_source(path):

    with tokenize.open(path) as f:
        return f.read()


# =============================================================================
# AST HELPERS
# =============================================================================

def get_function_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return "<unknown>"


def get_target_names(target):

    if isinstance(target, ast.Name):
        return [target.id]

    if isinstance(target, (ast.Tuple, ast.List)):
        names = []

        for element in target.elts:
            names.extend(
                get_target_names(element)
            )

        return names

    return ["<complex-target>"]


def dump_dict_keys(node):

    if not isinstance(node, ast.Dict):
        return None

    keys = []

    for key in node.keys:

        if isinstance(key, ast.Constant):
            keys.append(repr(key.value))

        elif isinstance(key, ast.Name):
            keys.append(
                f"<Name:{key.id}>"
            )

        else:
            keys.append(
                f"<{type(key).__name__}>"
            )

    return keys


# =============================================================================
# CALL EXTRACTION
# =============================================================================

def extract_calls(node):

    calls = []

    for child in ast.walk(node):

        if isinstance(child, ast.Call):

            calls.append(
                {
                    "line": child.lineno,
                    "function": get_function_name(
                        child.func
                    ),
                }
            )

    return calls


# =============================================================================
# RETURN ANALYSIS
# =============================================================================

def analyze_returns(function_node):

    results = []

    for node in ast.walk(function_node):

        if not isinstance(node, ast.Return):
            continue

        value = node.value

        if value is None:

            results.append(
                {
                    "line": node.lineno,
                    "type": "None",
                    "ast": "None",
                    "dict_keys": None,
                }
            )

            continue

        dict_keys = dump_dict_keys(value)

        results.append(
            {
                "line": node.lineno,
                "type": type(value).__name__,
                "ast": ast.dump(
                    value,
                    indent=2,
                ),
                "dict_keys": dict_keys,
            }
        )

    return results


# =============================================================================
# ASSIGNMENT ANALYSIS
# =============================================================================

def analyze_assignments(function_node):

    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):

            targets = []

            for target in node.targets:

                targets.extend(
                    get_target_names(target)
                )

            results.append(
                {
                    "line": node.lineno,
                    "targets": targets,
                    "value_ast": ast.dump(
                        node.value,
                        indent=2,
                    ),
                    "dict_keys": dump_dict_keys(
                        node.value
                    ),
                }
            )

        elif isinstance(node, ast.AnnAssign):

            targets = get_target_names(
                node.target
            )

            results.append(
                {
                    "line": node.lineno,
                    "targets": targets,
                    "value_ast": (
                        ast.dump(
                            node.value,
                            indent=2,
                        )
                        if node.value is not None
                        else "None"
                    ),
                    "dict_keys": (
                        dump_dict_keys(
                            node.value
                        )
                        if node.value is not None
                        else None
                    ),
                }
            )

    return results


# =============================================================================
# FUNCTION SOURCE
# =============================================================================

def get_function_source(
    source_lines,
    node,
):

    start = node.lineno
    end = node.end_lineno

    return "".join(
        source_lines[start - 1:end]
    )


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — CALCULATE STRUCTURE FORENSIC v0.1")
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"TARGET       : {TARGET}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("EXECUTION    : NONE")
    print("SOURCE MUTATION : NONE")
    print("BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY")

    print("=" * 100)

    if not TARGET.exists():

        raise RuntimeError(
            f"Target source not found: {TARGET}"
        )

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    source = load_source(TARGET)

    source_lines = source.splitlines(
        keepends=True
    )

    # -------------------------------------------------------------------------
    # PARSE
    # -------------------------------------------------------------------------

    tree = ast.parse(
        source,
        filename=str(TARGET),
    )

    # -------------------------------------------------------------------------
    # FIND calculate_structure
    # -------------------------------------------------------------------------

    targets = []

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "calculate_structure"
        ):

            targets.append(node)

    print()
    print("=" * 100)
    print("A) TARGET FUNCTION")
    print("=" * 100)

    if not targets:

        print("FUNCTION : calculate_structure")
        print("STATUS   : NOT FOUND")

        print()
        print("=" * 100)
        print("FINAL FORENSIC DECISION")
        print("=" * 100)
        print(
            "calculate_structure() was not found "
            "in market_regime_engine.py."
        )

        print()
        print("=" * 100)
        print("SAFETY ASSERTION")
        print("=" * 100)
        print("DATABASE ACCESS : False")
        print("DATABASE WRITE  : False")
        print("FILE WRITE      : False")
        print("SOURCE MUTATION : False")
        print("PRODUCTION EXECUTION : False")
        print("NETWORK         : False")

        return

    if len(targets) > 1:

        print(
            f"WARNING : {len(targets)} definitions found"
        )

    # -------------------------------------------------------------------------
    # ANALYZE EACH DEFINITION
    # -------------------------------------------------------------------------

    for index, function_node in enumerate(
        targets,
        start=1,
    ):

        print()
        print("-" * 100)
        print(
            f"CALCULATE_STRUCTURE DEFINITION #{index}"
        )
        print("-" * 100)

        print(
            f"FUNCTION : {function_node.name}"
        )

        print(
            f"LINE     : {function_node.lineno}"
        )

        print(
            f"END LINE : {function_node.end_lineno}"
        )

        # ---------------------------------------------------------------------
        # SIGNATURE
        # ---------------------------------------------------------------------

        args = function_node.args

        positional = [
            arg.arg
            for arg in args.args
        ]

        positional_only = [
            arg.arg
            for arg in args.posonlyargs
        ]

        keyword_only = [
            arg.arg
            for arg in args.kwonlyargs
        ]

        print()
        print(
            "SIGNATURE"
        )
        print("-" * 100)

        print(
            "POSITIONAL ONLY : "
            + repr(positional_only)
        )

        print(
            "POSITIONAL      : "
            + repr(positional)
        )

        print(
            "KEYWORD ONLY    : "
            + repr(keyword_only)
        )

        print(
            "VARARG          : "
            + (
                args.vararg.arg
                if args.vararg
                else "None"
            )
        )

        print(
            "KWARG           : "
            + (
                args.kwarg.arg
                if args.kwarg
                else "None"
            )
        )

        # ---------------------------------------------------------------------
        # SOURCE
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("B) FUNCTION SOURCE")
        print("=" * 100)

        print(
            get_function_source(
                source_lines,
                function_node,
            ),
            end="",
        )

        # ---------------------------------------------------------------------
        # DIRECT CALLS
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("C) DIRECT CALLS INSIDE calculate_structure()")
        print("=" * 100)

        calls = extract_calls(
            function_node
        )

        if not calls:

            print(
                "NO CALLS FOUND"
            )

        else:

            for call in calls:

                print(
                    f"LINE : {call['line']}"
                )

                print(
                    f"CALL : {call['function']}"
                )

        # ---------------------------------------------------------------------
        # ASSIGNMENTS
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("D) VARIABLE ASSIGNMENTS")
        print("=" * 100)

        assignments = analyze_assignments(
            function_node
        )

        if not assignments:

            print(
                "NO ASSIGNMENTS FOUND"
            )

        else:

            for assignment in assignments:

                print()
                print(
                    f"LINE    : {assignment['line']}"
                )

                print(
                    "TARGETS : "
                    + repr(
                        assignment["targets"]
                    )
                )

                print(
                    "VALUE AST :"
                )

                print(
                    assignment["value_ast"]
                )

                if assignment["dict_keys"] is not None:

                    print(
                        "DICT KEYS : "
                        + repr(
                            assignment["dict_keys"]
                        )
                    )

        # ---------------------------------------------------------------------
        # DICT CONSTRUCTION
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("E) DICT OBJECT CONSTRUCTIONS")
        print("=" * 100)

        dict_nodes = []

        for node in ast.walk(
            function_node
        ):

            if isinstance(
                node,
                ast.Dict,
            ):

                dict_nodes.append(node)

        if not dict_nodes:

            print(
                "NO DICT LITERALS FOUND"
            )

        else:

            for node in dict_nodes:

                print()
                print(
                    f"LINE : {node.lineno}"
                )

                keys = dump_dict_keys(
                    node
                )

                print(
                    "DICT KEYS : "
                    + repr(keys)
                )

                print(
                    "DICT AST :"
                )

                print(
                    ast.dump(
                        node,
                        indent=2,
                    )
                )

        # ---------------------------------------------------------------------
        # RETURNS
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("F) RETURN STATEMENTS")
        print("=" * 100)

        returns = analyze_returns(
            function_node
        )

        if not returns:

            print(
                "NO RETURN STATEMENTS FOUND"
            )

        else:

            for result in returns:

                print()
                print(
                    f"LINE : {result['line']}"
                )

                print(
                    f"RETURN TYPE : {result['type']}"
                )

                print(
                    "RETURN AST :"
                )

                print(
                    result["ast"]
                )

                if result["dict_keys"] is not None:

                    print(
                        "RETURN DICT KEYS : "
                        + repr(
                            result["dict_keys"]
                        )
                    )

        # ---------------------------------------------------------------------
        # CALLERS
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print(
            "G) calculate_structure() CALL SITES"
        )
        print("=" * 100)

        callers = []

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if (
                isinstance(
                    node.func,
                    ast.Name,
                )
                and node.func.id
                == "calculate_structure"
            ):

                callers.append(
                    node
                )

        if not callers:

            print(
                "NO CALL SITES FOUND"
            )

        else:

            for caller in callers:

                print(
                    f"CALL LINE : {caller.lineno}"
                )

                print(
                    "CALL AST :"
                )

                print(
                    ast.dump(
                        caller,
                        indent=2,
                    )
                )

        # ---------------------------------------------------------------------
        # NAME REFERENCES
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print(
            "H) calculate_structure NAME REFERENCES"
        )
        print("=" * 100)

        references = []

        for node in ast.walk(tree):

            if (
                isinstance(
                    node,
                    ast.Name,
                )
                and node.id
                == "calculate_structure"
            ):

                references.append(
                    node
                )

        if not references:

            print(
                "NO REFERENCES FOUND"
            )

        else:

            for reference in references:

                print(
                    f"LINE : {reference.lineno}"
                )

                print(
                    f"CONTEXT : "
                    f"{type(reference.ctx).__name__}"
                )

        # ---------------------------------------------------------------------
        # FINAL
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("I) FINAL FORENSIC DECISION")
        print("=" * 100)

        print(
            "PURPOSE : Identify the actual producer "
            "contract of calculate_structure()."
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

    # -------------------------------------------------------------------------
    # SAFETY
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("J) SAFETY ASSERTION")
    print("=" * 100)

    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("SOURCE MUTATION : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")

    print("=" * 100)
    print(
        "END — CALCULATE STRUCTURE FORENSIC v0.1"
    )
    print("=" * 100)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()