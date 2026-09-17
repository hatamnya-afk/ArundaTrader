from pathlib import Path
import ast
import sys


# =============================================================================
# ARUNDA PROJECT — STAGE SCRIPT ASSIGNMENT FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#   Resolve where the variable `script` used by:
#
#       run_stage(name, script, number)
#
#   is assigned inside arunda_pipeline.py.
#
# TARGET PATH:
#
#   launcher
#       ->
#   main()
#       ->
#   stage construction / assignment
#       ->
#   script
#       ->
#   run_stage()
#       ->
#   subprocess.run([PYTHON, script])
#
# SAFETY:
#   READ ONLY
#   STATIC ONLY
#   NO DATABASE
#   NO NETWORK
#   NO PROJECT EXECUTION
#   NO FILE MODIFICATION
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent
PIPELINE_FILE = PROJECT_DIR / "arunda_pipeline.py"
TARGET = "upgrade_db.py"


# =============================================================================
# HELPERS
# =============================================================================

def source_segment(
    source_lines,
    start,
    end,
):
    start = max(1, start)
    end = min(len(source_lines), end)

    return "".join(
        source_lines[start - 1:end]
    )


def contains_upgrade_db(text):
    return (
        TARGET.lower() in text.lower()
        or "upgrade_db" in text.lower()
    )


def node_location(node):
    return (
        getattr(node, "lineno", None),
        getattr(node, "end_lineno", None),
    )


def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def assignment_target_names(node):
    names = []

    if isinstance(node, ast.Name):
        names.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            names.extend(
                assignment_target_names(element)
            )

    return names


def find_function(tree, name):
    matches = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            if node.name == name:
                matches.append(node)

    return matches


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def main():

    print("=" * 110)
    print(
        "ARUNDA PROJECT — STAGE SCRIPT ASSIGNMENT FORENSIC v0.1"
    )
    print("=" * 110)

    print(
        "MODE                : READ ONLY"
    )
    print(
        "STATIC ANALYSIS     : YES"
    )
    print(
        "DATABASE ACCESS     : NO"
    )
    print(
        "NETWORK ACCESS      : NO"
    )
    print(
        "PROJECT EXECUTION   : NO"
    )
    print(
        "FILE MODIFICATION   : NO"
    )

    print()
    print("-" * 110)

    print(
        "TARGET PIPELINE"
    )

    print("-" * 110)

    print(
        f"PIPELINE            : {PIPELINE_FILE}"
    )

    print(
        f"TARGET              : {TARGET}"
    )

    if not PIPELINE_FILE.exists():

        print()
        print(
            "FATAL : arunda_pipeline.py NOT FOUND"
        )

        return 1

    # -------------------------------------------------------------------------
    # READ SOURCE ONLY
    # -------------------------------------------------------------------------

    source = PIPELINE_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )

    source_lines = source.splitlines(
        keepends=True
    )

    try:

        tree = ast.parse(
            source,
            filename=str(PIPELINE_FILE),
        )

    except SyntaxError as exc:

        print()
        print(
            "FATAL : arunda_pipeline.py AST PARSE FAILED"
        )

        print(
            repr(exc)
        )

        return 1

    # -------------------------------------------------------------------------
    # MAIN FUNCTION
    # -------------------------------------------------------------------------

    main_functions = find_function(
        tree,
        "main",
    )

    print()
    print("-" * 110)

    print(
        "MAIN() ANALYSIS"
    )

    print("-" * 110)

    if not main_functions:

        print(
            "main()               : NOT FOUND"
        )

        return 1

    if len(main_functions) > 1:

        print(
            f"main() definitions   : {len(main_functions)}"
        )

    main_node = main_functions[0]

    main_start, main_end = node_location(
        main_node
    )

    print(
        f"main() range         : {main_start} - {main_end}"
    )

    # -------------------------------------------------------------------------
    # RUN_STAGE CALLS INSIDE MAIN
    # -------------------------------------------------------------------------

    print()
    print("-" * 110)

    print(
        "run_stage() CALLS INSIDE main()"
    )

    print("-" * 110)

    run_stage_calls = []

    for node in ast.walk(main_node):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Name):
            continue

        if node.func.id != "run_stage":
            continue

        line = getattr(
            node,
            "lineno",
            None,
        )

        end_line = getattr(
            node,
            "end_lineno",
            line,
        )

        run_stage_calls.append(
            (
                line,
                end_line,
                node,
            )
        )

    if not run_stage_calls:

        print(
            "NO run_stage() CALL FOUND INSIDE main()"
        )

    else:

        for line, end_line, node in run_stage_calls:

            print()
            print(
                f"CALL RANGE : {line} - {end_line}"
            )

            print(
                "CALL       : "
                + safe_unparse(node)
            )

            print(
                "ARGUMENTS:"
            )

            for index, arg in enumerate(node.args):

                print(
                    f"  ARG[{index}] : "
                    f"{type(arg).__name__} "
                    f"{safe_unparse(arg)}"
                )

    # -------------------------------------------------------------------------
    # ALL ASSIGNMENTS TO `script`
    # -------------------------------------------------------------------------

    print()
    print("-" * 110)

    print(
        "ALL ASSIGNMENTS TO VARIABLE `script`"
    )

    print("-" * 110)

    assignments = []

    for node in ast.walk(tree):

        target_names = []

        if isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                target_names.extend(
                    assignment_target_names(
                        target
                    )
                )

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            target_names.extend(
                assignment_target_names(
                    node.target
                )
            )

        elif isinstance(
            node,
            ast.NamedExpr,
        ):

            target_names.extend(
                assignment_target_names(
                    node.target
                )
            )

        if "script" not in target_names:
            continue

        line = getattr(
            node,
            "lineno",
            None,
        )

        end_line = getattr(
            node,
            "end_lineno",
            line,
        )

        segment = source_segment(
            source_lines,
            line,
            end_line,
        )

        assignments.append(
            (
                line,
                end_line,
                node,
                segment,
            )
        )

    if not assignments:

        print(
            "NO ASSIGNMENT TO `script` FOUND"
        )

    else:

        for line, end_line, node, segment in assignments:

            print()
            print(
                f"LINE RANGE : {line} - {end_line}"
            )

            print(
                "SOURCE:"
            )

            print(
                segment.rstrip()
            )

            if contains_upgrade_db(segment):

                print(
                    "UPGRADE_DB : PRESENT"
                )

            else:

                print(
                    "UPGRADE_DB : NOT PRESENT"
                )

    # -------------------------------------------------------------------------
    # FOR-LOOP / STAGE ITERATION CONTEXT
    # -------------------------------------------------------------------------

    print()
    print("-" * 110)

    print(
        "STAGE ITERATION CONTEXT"
    )

    print("-" * 110)

    for node in ast.walk(main_node):

        if not isinstance(
            node,
            (
                ast.For,
                ast.AsyncFor,
            ),
        ):
            continue

        start = getattr(
            node,
            "lineno",
            None,
        )

        end = getattr(
            node,
            "end_lineno",
            start,
        )

        segment = source_segment(
            source_lines,
            start,
            end,
        )

        if (
            "run_stage" in segment
            or "script" in segment
        ):

            print()
            print(
                f"LOOP RANGE : {start} - {end}"
            )

            print(
                segment.rstrip()
            )

    # -------------------------------------------------------------------------
    # COLLECTIONS / LISTS / TUPLES CONTAINING SCRIPT
    # -------------------------------------------------------------------------

    print()
    print("-" * 110)

    print(
        "COLLECTIONS / STRUCTURES RELATED TO `script`"
    )

    print("-" * 110)

    collection_hits = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.NamedExpr,
            ),
        ):

            continue

        line = getattr(
            node,
            "lineno",
            None,
        )

        end_line = getattr(
            node,
            "end_lineno",
            line,
        )

        segment = source_segment(
            source_lines,
            line,
            end_line,
        )

        if "script" not in segment.lower():
            continue

        collection_hits.append(
            (
                line,
                end_line,
                segment,
            )
        )

    if collection_hits:

        seen = set()

        for line, end_line, segment in collection_hits:

            key = (
                line,
                end_line,
                segment,
            )

            if key in seen:
                continue

            seen.add(key)

            print()
            print(
                f"LINE RANGE : {line} - {end_line}"
            )

            print(
                segment.rstrip()
            )

    else:

        print(
            "NO ADDITIONAL COLLECTION ASSIGNMENTS FOUND"
        )

    # -------------------------------------------------------------------------
    # STATIC upgrade_db REFERENCES IN PIPELINE
    # -------------------------------------------------------------------------

    print()
    print("-" * 110)

    print(
        "STATIC upgrade_db REFERENCES IN arunda_pipeline.py"
    )

    print("-" * 110)

    hits = []

    for index, line in enumerate(
        source_lines,
        start=1,
    ):

        if contains_upgrade_db(line):

            hits.append(
                (
                    index,
                    line.rstrip(),
                )
            )

    if not hits:

        print(
            "NO STATIC upgrade_db REFERENCE FOUND"
        )

    else:

        for line_number, text in hits:

            print(
                f"LINE {line_number:<6}: {text}"
            )

    # -------------------------------------------------------------------------
    # DIRECT RELATIONSHIP
    # -------------------------------------------------------------------------

    print()
    print("=" * 110)

    print(
        "DIRECT SCRIPT RESOLUTION STATUS"
    )

    print("=" * 110)

    if not assignments:

        print(
            "STATUS : SCRIPT_VARIABLE_ASSIGNMENT_NOT_FOUND"
        )

        print(
            "NEXT   : inspect the caller scope / stage collection construction"
        )

    else:

        upgrade_assignment = False

        for (
            line,
            end_line,
            node,
            segment,
        ) in assignments:

            if contains_upgrade_db(segment):

                upgrade_assignment = True

        if upgrade_assignment:

            print(
                "STATUS : UPGRADE_DB_DIRECTLY_REACHES_SCRIPT_ASSIGNMENT"
            )

        else:

            print(
                "STATUS : SCRIPT_ASSIGNMENT_FOUND_BUT_UPGRADE_DB_ORIGIN_UNRESOLVED"
            )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print("=" * 110)

    print(
        "FINAL FORENSIC STATUS"
    )

    print("=" * 110)

    print(
        "READ ONLY           : YES"
    )

    print(
        "STATIC ONLY         : YES"
    )

    print(
        "DATABASE            : NONE"
    )

    print(
        "NETWORK             : NONE"
    )

    print(
        "PROJECT EXECUTION   : NONE"
    )

    print(
        "FILE MODIFICATION   : NONE"
    )

    print()
    print(
        "TARGET:"
    )

    print(
        "launcher -> main -> arunda_pipeline.py"
    )

    print(
        "-> stage construction -> script assignment"
    )

    print(
        "-> run_stage() -> subprocess.run()"
    )

    print(
        "-> upgrade_db.py"
    )

    print(
        "=" * 110
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )