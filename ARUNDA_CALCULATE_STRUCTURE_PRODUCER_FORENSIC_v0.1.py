# =============================================================================
# ARUNDA_CALCULATE_STRUCTURE_PRODUCER_FORENSIC_v0.1.py
# =============================================================================

from pathlib import Path
import ast


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = PROJECT_ROOT / "market_regime_engine.py"

FUNCTION_NAME = "calculate_structure"


def get_source_segment(source_lines, node):
    start = node.lineno
    end = node.end_lineno

    return "".join(
        f"{i:6} | {source_lines[i - 1]}"
        for i in range(start, end + 1)
    )


def main():

    print("=" * 100)
    print("ARUNDA TRADER — CALCULATE STRUCTURE PRODUCER FORENSIC v0.1")
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
        raise FileNotFoundError(
            f"Target source not found: {TARGET}"
        )

    # -------------------------------------------------------------------------
    # READ ONLY
    # -------------------------------------------------------------------------

    source = TARGET.read_text(
        encoding="utf-8-sig"
    )

    source_lines = source.splitlines(
        keepends=True
    )

    # -------------------------------------------------------------------------
    # STATIC PARSE
    # -------------------------------------------------------------------------

    tree = ast.parse(
        source,
        filename=str(TARGET)
    )

    # -------------------------------------------------------------------------
    # FIND calculate_structure()
    # -------------------------------------------------------------------------

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == FUNCTION_NAME
    ]

    print()
    print("=" * 100)
    print("A) TARGET FUNCTION")
    print("=" * 100)

    if not functions:
        print("FUNCTION : NOT FOUND")
        print()
        print("=" * 100)
        print("FINAL FORENSIC DECISION")
        print("=" * 100)
        print("calculate_structure() definition was not found.")
        print("NO REPAIR WAS PERFORMED.")
        print("NO PRODUCTION SOURCE WAS MODIFIED.")
        return

    if len(functions) > 1:
        print(
            f"WARNING : {len(functions)} definitions found"
        )

    node = functions[0]

    print(f"FUNCTION : {node.name}()")
    print(f"LINE     : {node.lineno}")
    print(f"END LINE : {node.end_lineno}")

    # -------------------------------------------------------------------------
    # FUNCTION SOURCE
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("B) FUNCTION SOURCE")
    print("=" * 100)

    print("-" * 100)

    print(
        get_source_segment(
            source_lines,
            node
        ),
        end=""
    )

    # -------------------------------------------------------------------------
    # PARAMETERS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("C) FUNCTION PARAMETERS")
    print("=" * 100)

    positional = [
        arg.arg
        for arg in node.args.posonlyargs
    ]

    positional += [
        arg.arg
        for arg in node.args.args
    ]

    keyword_only = [
        arg.arg
        for arg in node.args.kwonlyargs
    ]

    print(
        "POSITIONAL : "
        + str(positional)
    )

    print(
        "KEYWORD ONLY : "
        + str(keyword_only)
    )

    if node.args.vararg:
        print(
            "VARARG : "
            + node.args.vararg.arg
        )

    if node.args.kwarg:
        print(
            "KWARG : "
            + node.args.kwarg.arg
        )

    # -------------------------------------------------------------------------
    # DIRECT CALLS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("D) DIRECT CALLS INSIDE calculate_structure()")
    print("=" * 100)

    calls = []

    for child in ast.walk(node):

        if not isinstance(child, ast.Call):
            continue

        func = child.func

        if isinstance(func, ast.Name):

            name = func.id

        elif isinstance(func, ast.Attribute):

            name = func.attr

        else:

            name = ast.dump(
                func,
                include_attributes=False
            )

        calls.append(
            (
                child.lineno,
                name,
                child
            )
        )

    calls.sort(
        key=lambda item: item[0]
    )

    if not calls:

        print("NO CALLS FOUND")

    else:

        for line, name, call_node in calls:

            print(
                f"LINE : {line}"
            )

            print(
                f"CALL : {name}"
            )

            print(
                "CALL AST :"
            )

            print(
                ast.dump(
                    call_node,
                    indent=2,
                    include_attributes=False
                )
            )

            print("-" * 100)

    # -------------------------------------------------------------------------
    # ASSIGNMENTS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("E) VARIABLE ASSIGNMENTS")
    print("=" * 100)

    assignments = []

    for child in ast.walk(node):

        if isinstance(
            child,
            (ast.Assign, ast.AnnAssign, ast.AugAssign)
        ):

            assignments.append(
                child
            )

    assignments.sort(
        key=lambda item: item.lineno
    )

    if not assignments:

        print("NO ASSIGNMENTS FOUND")

    else:

        for assignment in assignments:

            print(
                f"LINE : {assignment.lineno}"
            )

            print(
                "ASSIGNMENT AST :"
            )

            print(
                ast.dump(
                    assignment,
                    indent=2,
                    include_attributes=False
                )
            )

            print("-" * 100)

    # -------------------------------------------------------------------------
    # RETURN STATEMENTS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("F) RETURN STATEMENTS")
    print("=" * 100)

    returns = [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
    ]

    returns.sort(
        key=lambda item: item.lineno
    )

    if not returns:

        print("NO RETURN STATEMENT FOUND")

    else:

        for ret in returns:

            print(
                f"LINE : {ret.lineno}"
            )

            print(
                "RETURN AST :"
            )

            if ret.value is None:

                print("None")

            else:

                print(
                    ast.dump(
                        ret.value,
                        indent=2,
                        include_attributes=False
                    )
                )

            print("-" * 100)

    # -------------------------------------------------------------------------
    # RETURN VALUE CLASSIFICATION
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("G) RETURN VALUE CLASSIFICATION")
    print("=" * 100)

    for ret in returns:

        if ret.value is None:

            print(
                f"LINE {ret.lineno} : return None"
            )

        elif isinstance(
            ret.value,
            ast.Dict
        ):

            print(
                f"LINE {ret.lineno} : DIRECT DICT RETURN"
            )

            keys = []

            for key in ret.value.keys:

                if isinstance(key, ast.Constant):

                    keys.append(
                        repr(key.value)
                    )

                else:

                    keys.append(
                        ast.dump(
                            key,
                            include_attributes=False
                        )
                    )

            print(
                "DICT KEYS : "
                + str(keys)
            )

        elif isinstance(
            ret.value,
            ast.Name
        ):

            print(
                f"LINE {ret.lineno} : RETURN VARIABLE"
            )

            print(
                "VARIABLE : "
                + ret.value.id
            )

        elif isinstance(
            ret.value,
            ast.Call
        ):

            print(
                f"LINE {ret.lineno} : RETURN CALL"
            )

            print(
                "CALL : "
                + (
                    ret.value.func.id
                    if isinstance(
                        ret.value.func,
                        ast.Name
                    )
                    else getattr(
                        ret.value.func,
                        "attr",
                        "<unknown>"
                    )
                )
            )

        else:

            print(
                f"LINE {ret.lineno} : RETURN EXPRESSION"
            )

            print(
                ast.dump(
                    ret.value,
                    indent=2,
                    include_attributes=False
                )
            )

    # -------------------------------------------------------------------------
    # FUNCTION REFERENCES IN FILE
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("H) calculate_structure() NAME REFERENCES")
    print("=" * 100)

    references = []

    for child in ast.walk(tree):

        if isinstance(child, ast.Call):

            func = child.func

            if (
                isinstance(func, ast.Name)
                and func.id == FUNCTION_NAME
            ):

                references.append(
                    child
                )

    references.sort(
        key=lambda item: item.lineno
    )

    if not references:

        print("NO CALL SITES FOUND")

    else:

        for call in references:

            print(
                f"CALL LINE : {call.lineno}"
            )

            print(
                "CALL AST :"
            )

            print(
                ast.dump(
                    call,
                    indent=2,
                    include_attributes=False
                )
            )

            print("-" * 100)

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("I) FINAL FORENSIC DECISION")
    print("=" * 100)

    print(
        "PURPOSE : "
        "Identify the actual producer contract of calculate_structure()."
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
    print("J) SAFETY ASSERTION")
    print("=" * 100)

    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("SOURCE MUTATION : False")
    print("PRODUCTION EXECUTION : False")
    print("NETWORK         : False")

    print("=" * 100)
    print("END — CALCULATE STRUCTURE PRODUCER FORENSIC v0.1")
    print("=" * 100)


if __name__ == "__main__":
    main()