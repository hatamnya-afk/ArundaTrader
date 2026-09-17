from pathlib import Path
import ast
import sys


# =============================================================================
# ARUNDA PROJECT — STAGE COLLECTION ORIGIN FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#   Determine the authoritative origin and lifecycle of STAGES inside
#   arunda_pipeline.py.
#
# TARGET:
#
#   launcher
#       ->
#   main()
#       ->
#   STAGES
#       ->
#   stage
#       ->
#   script = stage["script"]
#       ->
#   run_stage(...)
#       ->
#   subprocess.run(...)
#
# QUESTIONS:
#
#   1. Where is STAGES defined?
#   2. Is STAGES reassigned?
#   3. Is STAGES mutated?
#   4. Is STAGES extended / appended / modified?
#   5. Is STAGES passed into another function?
#   6. Is STAGES returned by another function?
#   7. Is STAGES imported from another module?
#   8. Is STAGES replaced dynamically?
#   9. Are stage dictionaries constructed elsewhere?
#  10. Does upgrade_db.py appear anywhere in those construction paths?
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

TARGET_VARIABLE = "STAGES"
TARGET_UPGRADE = "upgrade_db.py"


# =============================================================================
# HELPERS
# =============================================================================

def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def location(node):
    return (
        getattr(node, "lineno", None),
        getattr(node, "end_lineno", None),
    )


def source_segment(lines, start, end):
    if start is None:
        return ""

    if end is None:
        end = start

    start = max(1, start)
    end = min(len(lines), end)

    return "".join(
        lines[start - 1:end]
    )


def contains_upgrade(text):
    lower = text.lower()

    return (
        TARGET_UPGRADE.lower() in lower
        or "upgrade_db" in lower
    )


def is_stages_name(node):
    return (
        isinstance(node, ast.Name)
        and node.id == TARGET_VARIABLE
    )


def attribute_chain(node):
    parts = []

    current = node

    while isinstance(current, ast.Attribute):

        parts.append(current.attr)

        current = current.value

    if isinstance(current, ast.Name):

        parts.append(current.id)

        return ".".join(
            reversed(parts)
        )

    return None


def call_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return attribute_chain(node)

    return None


def target_names(node):

    result = []

    if isinstance(node, ast.Name):

        result.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):

        for element in node.elts:

            result.extend(
                target_names(element)
            )

    return result


def find_main(tree):

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name == "main":

                result.append(node)

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 110)
    print(
        "ARUNDA PROJECT — STAGE COLLECTION ORIGIN FORENSIC v0.1"
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
        "TARGET"
    )

    print("-" * 110)

    print(
        f"PIPELINE            : {PIPELINE_FILE}"
    )

    print(
        f"VARIABLE            : {TARGET_VARIABLE}"
    )

    print(
        f"UPGRADE TARGET      : {TARGET_UPGRADE}"
    )

    if not PIPELINE_FILE.exists():

        print()
        print(
            "FATAL : arunda_pipeline.py NOT FOUND"
        )

        return 1

    # =========================================================================
    # READ SOURCE
    # =========================================================================

    source = PIPELINE_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = source.splitlines(
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
            "FATAL : AST PARSE FAILED"
        )

        print(
            repr(exc)
        )

        return 1

    # =========================================================================
    # STAGES DEFINITIONS / ASSIGNMENTS
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "1. ALL STAGES DEFINITIONS / ASSIGNMENTS"
    )

    print("-" * 110)

    definitions = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Assign,
        ):

            names = []

            for target in node.targets:

                names.extend(
                    target_names(target)
                )

            if TARGET_VARIABLE in names:

                start, end = location(node)

                definitions.append(
                    (
                        start,
                        end,
                        node,
                    )
                )

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            names = target_names(
                node.target
            )

            if TARGET_VARIABLE in names:

                start, end = location(node)

                definitions.append(
                    (
                        start,
                        end,
                        node,
                    )
                )

        elif isinstance(
            node,
            ast.NamedExpr,
        ):

            names = target_names(
                node.target
            )

            if TARGET_VARIABLE in names:

                start, end = location(node)

                definitions.append(
                    (
                        start,
                        end,
                        node,
                    )
                )

    definitions.sort(
        key=lambda item: (
            item[0] or 0,
            item[1] or 0,
        )
    )

    if not definitions:

        print(
            "NO STAGES ASSIGNMENT FOUND"
        )

    else:

        for index, (
            start,
            end,
            node,
        ) in enumerate(
            definitions,
            start=1,
        ):

            print()
            print(
                f"[{index}] LINE RANGE : "
                f"{start} - {end}"
            )

            segment = source_segment(
                lines,
                start,
                end,
            )

            print(
                segment.rstrip()
            )

            print(
                f"UPGRADE_DB       : "
                f"{'PRESENT' if contains_upgrade(segment) else 'NOT PRESENT'}"
            )

    # =========================================================================
    # STAGES REFERENCES
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "2. ALL DIRECT REFERENCES TO STAGES"
    )

    print("-" * 110)

    references = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Name,
        ):

            continue

        if node.id != TARGET_VARIABLE:
            continue

        start, end = location(node)

        references.append(
            (
                start,
                end,
                node,
            )
        )

    references.sort(
        key=lambda item: (
            item[0] or 0,
            item[1] or 0,
        )
    )

    for index, (
        start,
        end,
        node,
    ) in enumerate(
        references,
        start=1,
    ):

        parent_context = ""

        # Find enclosing function / loop approximately.
        for parent in ast.walk(tree):

            if not hasattr(
                parent,
                "body",
            ):
                continue

            if not hasattr(
                parent,
                "lineno",
            ):
                continue

            parent_start = getattr(
                parent,
                "lineno",
                0,
            )

            parent_end = getattr(
                parent,
                "end_lineno",
                parent_start,
            )

            if (
                parent_start <= start <= parent_end
            ):

                if isinstance(
                    parent,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):

                    parent_context = (
                        f"FUNCTION={parent.name}"
                    )

        print(
            f"[{index:02d}] LINE {start:<5} "
            f"{parent_context}"
        )

    # =========================================================================
    # STAGES MUTATIONS
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "3. STAGES MUTATION OPERATIONS"
    )

    print("-" * 110)

    mutations = []

    for node in ast.walk(tree):

        # STAGES.append(...)
        if isinstance(
            node,
            ast.Call,
        ):

            name = call_name(
                node.func
            )

            if name and name.startswith(
                "STAGES."
            ):

                start, end = location(node)

                mutations.append(
                    (
                        start,
                        end,
                        name,
                        safe_unparse(node),
                    )
                )

        # STAGES[...] = ...
        if isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if (
                    isinstance(
                        target,
                        ast.Subscript,
                    )
                    and isinstance(
                        target.value,
                        ast.Name,
                    )
                    and target.value.id
                    == TARGET_VARIABLE
                ):

                    start, end = location(node)

                    mutations.append(
                        (
                            start,
                            end,
                            "STAGES_SUBSCRIPT_ASSIGN",
                            safe_unparse(node),
                        )
                    )

        # STAGES += ...
        if isinstance(
            node,
            ast.AugAssign,
        ):

            if is_stages_name(
                node.target
            ):

                start, end = location(node)

                mutations.append(
                    (
                        start,
                        end,
                        "STAGES_AUG_ASSIGN",
                        safe_unparse(node),
                    )
                )

    mutations.sort(
        key=lambda item: item[0] or 0
    )

    if not mutations:

        print(
            "NO STAGES MUTATION FOUND"
        )

    else:

        for (
            start,
            end,
            operation,
            expression,
        ) in mutations:

            print()
            print(
                f"LINE      : {start} - {end}"
            )

            print(
                f"OPERATION : {operation}"
            )

            print(
                f"EXPR      : {expression}"
            )

    # =========================================================================
    # STAGES PASSED AS FUNCTION ARGUMENT
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "4. FUNCTIONS RECEIVING STAGES"
    )

    print("-" * 110)

    passed_calls = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        for index, arg in enumerate(
            node.args
        ):

            if is_stages_name(arg):

                start, end = location(node)

                passed_calls.append(
                    (
                        start,
                        end,
                        call_name(node.func),
                        index,
                        safe_unparse(node),
                    )
                )

    if not passed_calls:

        print(
            "STAGES IS NOT PASSED AS A FUNCTION ARGUMENT"
        )

    else:

        for (
            start,
            end,
            function,
            index,
            expression,
        ) in passed_calls:

            print()
            print(
                f"LINE      : {start} - {end}"
            )

            print(
                f"FUNCTION  : {function}"
            )

            print(
                f"ARGUMENT  : {index}"
            )

            print(
                f"CALL      : {expression}"
            )

    # =========================================================================
    # FUNCTIONS RETURNING STAGES
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "5. FUNCTIONS RETURNING STAGES"
    )

    print("-" * 110)

    returned = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Return,
        ):

            continue

        if node.value is None:
            continue

        if is_stages_name(
            node.value
        ):

            start, end = location(node)

            returned.append(
                (
                    start,
                    end,
                    safe_unparse(node),
                )
            )

    if not returned:

        print(
            "NO FUNCTION RETURNS STAGES DIRECTLY"
        )

    else:

        for (
            start,
            end,
            expression,
        ) in returned:

            print()
            print(
                f"LINE      : {start} - {end}"
            )

            print(
                expression
            )

    # =========================================================================
    # IMPORTS INVOLVING STAGES
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "6. IMPORTS INVOLVING STAGES"
    )

    print("-" * 110)

    import_hits = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if (
                    alias.name == TARGET_VARIABLE
                    or TARGET_VARIABLE.lower()
                    in alias.name.lower()
                ):

                    start, end = location(node)

                    import_hits.append(
                        (
                            start,
                            end,
                            safe_unparse(node),
                        )
                    )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            for alias in node.names:

                if (
                    alias.name == TARGET_VARIABLE
                    or TARGET_VARIABLE.lower()
                    in alias.name.lower()
                ):

                    start, end = location(node)

                    import_hits.append(
                        (
                            start,
                            end,
                            safe_unparse(node),
                        )
                    )

    if not import_hits:

        print(
            "NO IMPORT OF STAGES FOUND"
        )

    else:

        for (
            start,
            end,
            expression,
        ) in import_hits:

            print()
            print(
                f"LINE : {start} - {end}"
            )

            print(
                expression
            )

    # =========================================================================
    # MAIN() STAGES USAGE
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "7. MAIN() STAGES USAGE"
    )

    print("-" * 110)

    main_functions = find_main(
        tree
    )

    if not main_functions:

        print(
            "main() NOT FOUND"
        )

    else:

        main_node = main_functions[0]

        start, end = location(
            main_node
        )

        print(
            f"main() RANGE : {start} - {end}"
        )

        main_hits = []

        for node in ast.walk(
            main_node
        ):

            if isinstance(
                node,
                ast.Name,
            ):

                if node.id == TARGET_VARIABLE:

                    line = getattr(
                        node,
                        "lineno",
                        None,
                    )

                    main_hits.append(
                        line
                    )

        for line in sorted(
            set(main_hits)
        ):

            print(
                f"STAGES reference : line {line}"
            )

    # =========================================================================
    # STAGE DICTIONARY STRUCTURES
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "8. DICTIONARY STRUCTURES CONTAINING SCRIPT"
    )

    print("-" * 110)

    dictionary_hits = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Dict,
        ):

            continue

        keys = node.keys
        values = node.values

        has_script_key = False

        for key in keys:

            if (
                isinstance(
                    key,
                    ast.Constant,
                )
                and key.value == "script"
            ):

                has_script_key = True

        if not has_script_key:
            continue

        start, end = location(node)

        expression = safe_unparse(
            node
        )

        dictionary_hits.append(
            (
                start,
                end,
                expression,
                contains_upgrade(expression),
            )
        )

    if not dictionary_hits:

        print(
            "NO DICTIONARY WITH `script` KEY FOUND"
        )

    else:

        for (
            start,
            end,
            expression,
            upgrade,
        ) in dictionary_hits:

            print()
            print(
                f"LINE RANGE : {start} - {end}"
            )

            print(
                expression
            )

            print(
                f"UPGRADE_DB : "
                f"{'PRESENT' if upgrade else 'NOT PRESENT'}"
            )

    # =========================================================================
    # ALL UPGRADE_DB REFERENCES IN PIPELINE
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "9. ALL STATIC upgrade_db REFERENCES"
    )

    print("-" * 110)

    upgrade_hits = []

    for index, line in enumerate(
        lines,
        start=1,
    ):

        if contains_upgrade(line):

            upgrade_hits.append(
                (
                    index,
                    line.rstrip(),
                )
            )

    if not upgrade_hits:

        print(
            "NO STATIC upgrade_db REFERENCE FOUND"
        )

    else:

        for (
            line_number,
            text,
        ) in upgrade_hits:

            print(
                f"LINE {line_number:<5}: {text}"
            )

    # =========================================================================
    # STAGE CONSTRUCTION / RESOLUTION SUMMARY
    # =========================================================================

    print()
    print("=" * 110)

    print(
        "10. STAGE COLLECTION RESOLUTION"
    )

    print("=" * 110)

    if definitions:

        print(
            "STAGES DEFINITION      : FOUND"
        )

        first_start = definitions[0][0]

        print(
            f"FIRST DEFINITION LINE  : {first_start}"
        )

    else:

        print(
            "STAGES DEFINITION      : NOT FOUND"
        )

    print(
        f"ASSIGNMENT COUNT       : {len(definitions)}"
    )

    print(
        f"REFERENCE COUNT        : {len(references)}"
    )

    print(
        f"MUTATION COUNT         : {len(mutations)}"
    )

    print(
        f"PASSED-AS-ARG COUNT    : {len(passed_calls)}"
    )

    print(
        f"RETURN COUNT           : {len(returned)}"
    )

    print(
        f"IMPORT COUNT           : {len(import_hits)}"
    )

    print(
        f"SCRIPT-DICT COUNT      : {len(dictionary_hits)}"
    )

    print(
        f"UPGRADE_DB HIT COUNT   : {len(upgrade_hits)}"
    )

    # =========================================================================
    # FINAL STATUS
    # =========================================================================

    print()
    print("=" * 110)

    print(
        "FINAL FORENSIC STATUS"
    )

    print("=" * 110)

    if not definitions:

        status = (
            "STAGES_ORIGIN_NOT_FOUND"
        )

    elif mutations:

        status = (
            "STAGES_HAS_MUTATION_PATH"
        )

    elif len(definitions) > 1:

        status = (
            "STAGES_HAS_MULTIPLE_ASSIGNMENTS"
        )

    elif upgrade_hits:

        status = (
            "UPGRADE_DB_STATIC_REFERENCE_EXISTS"
        )

    else:

        status = (
            "STAGES_STATIC_ORIGIN_IDENTIFIED_NO_UPGRADE_DB_REFERENCE"
        )

    print(
        f"STATUS              : {status}"
    )

    print()
    print(
        "TARGET:"
    )

    print(
        "launcher"
    )

    print(
        "-> main()"
    )

    print(
        "-> STAGES origin / mutation"
    )

    print(
        "-> stage"
    )

    print(
        "-> script = stage['script']"
    )

    print(
        "-> run_stage()"
    )

    print(
        "-> subprocess.run()"
    )

    print(
        "-> upgrade_db.py"
    )

    print()
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

    print("=" * 110)

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    sys.exit(
        main()
    )