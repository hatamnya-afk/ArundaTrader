from pathlib import Path
import ast


# =============================================================================
# ARUNDA — FIND REAL DECISION UPSTREAM v0.2
# =============================================================================
#
# READ ONLY
# NO IMPORT
# NO DB
# NO PIPELINE
# NO SOURCE EDIT
#
# PURPOSE:
# Find the REAL runtime bridge carrying the three upstream objects:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# into:
#
#     decision_engine.main(...)
#
# Also inspect:
#
#     signal_scorer.run(...)
#     signal_scorer.load_scores(...)
#
# =============================================================================


PROJECT_ROOT = Path(
    r"C:\Users\ASUS\ArundaTrader"
)

TARGET_MODULES = {
    "decision_engine.main",
    "decision_engine.run",
    "signal_scorer.run",
    "signal_scorer.load_scores",
}


REQUIRED_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}


# =============================================================================
# HELPERS
# =============================================================================

def call_name(node):

    if not isinstance(node, ast.Call):
        return "<not-call>"

    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):

        parts = []

        current = func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(
            reversed(parts)
        )

    return "<unknown>"


def expr_text(node):

    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse-failed>"


def parent_map(tree):

    result = {}

    for parent in ast.walk(tree):

        for child in ast.iter_child_nodes(parent):

            result[child] = parent

    return result


def enclosing_function(node, parents):

    current = node

    while current in parents:

        current = parents[current]

        if isinstance(
            current,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            return current

    return None


def function_args(node):

    result = []

    if not isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        return result

    result.extend(
        x.arg
        for x in node.args.posonlyargs
    )

    result.extend(
        x.arg
        for x in node.args.args
    )

    result.extend(
        x.arg
        for x in node.args.kwonlyargs
    )

    return result


def contains_names(node, names):

    found = set()

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ):

            if child.id in names:

                found.add(
                    child.id
                )

    return found


# =============================================================================
# LOAD FILES
# =============================================================================

def load_python_files():

    files = []

    for path in PROJECT_ROOT.rglob("*.py"):

        # Ignore common cache/build directories
        parts = set(path.parts)

        if "__pycache__" in parts:
            continue

        if ".git" in parts:
            continue

        if "venv" in parts:
            continue

        if ".venv" in parts:
            continue

        files.append(path)

    return sorted(files)


# =============================================================================
# PASS 1
# =============================================================================

def find_target_calls(files):

    results = []

    for path in files:

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                text,
                filename=str(path),
            )
        except SyntaxError:
            continue

        parents = parent_map(tree)

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = call_name(node)

            if name not in TARGET_MODULES:
                continue

            fn = enclosing_function(
                node,
                parents,
            )

            results.append({
                "path": path,
                "line": node.lineno,
                "call": name,
                "function": (
                    fn.name
                    if fn
                    else "<module>"
                ),
                "args": [
                    expr_text(x)
                    for x in node.args
                ],
                "keywords": [
                    (
                        x.arg,
                        expr_text(x.value),
                    )
                    for x in node.keywords
                ],
            })

    return results


# =============================================================================
# PASS 2
# FIND FUNCTIONS USING UPSTREAM OBJECTS
# =============================================================================

def find_upstream_functions(files):

    results = []

    for path in files:

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                text,
                filename=str(path),
            )
        except SyntaxError:
            continue

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            params = set(
                function_args(node)
            )

            used = contains_names(
                node,
                REQUIRED_NAMES,
            )

            # Strong candidate:
            # function receives all three explicitly.
            if REQUIRED_NAMES <= params:

                results.append({
                    "kind": "ALL_PARAMS",
                    "path": path,
                    "line": node.lineno,
                    "function": node.name,
                    "params": sorted(params),
                    "used": sorted(used),
                })

                continue

            # Second-level candidate:
            # function uses all three somewhere internally.
            if REQUIRED_NAMES <= used:

                results.append({
                    "kind": "ALL_USED",
                    "path": path,
                    "line": node.lineno,
                    "function": node.name,
                    "params": sorted(params),
                    "used": sorted(used),
                })

    return results


# =============================================================================
# PASS 3
# TRACE CALL ARGUMENTS
# =============================================================================

def print_argument_analysis(target_calls):

    print()
    print("=" * 100)
    print("PASS 3 : TARGET CALL ARGUMENT ANALYSIS")
    print("=" * 100)

    if not target_calls:

        print(
            "NO TARGET CALLS FOUND."
        )

        return

    for item in target_calls:

        print()
        print("-" * 100)

        print(
            "FILE   :",
            item["path"],
        )

        print(
            "LINE   :",
            item["line"],
        )

        print(
            "CALL   :",
            item["call"],
        )

        print(
            "CALLER :",
            item["function"],
        )

        print(
            "ARGS   :",
            len(item["args"]),
        )

        for index, arg in enumerate(
            item["args"],
            start=1,
        ):

            print(
                f"  ARG {index}: {arg}"
            )

            matched = (
                REQUIRED_NAMES
                & set(
                    token
                    for token in arg.replace(
                        "(",
                        " ",
                    ).replace(
                        ")",
                        " ",
                    ).replace(
                        ",",
                        " ",
                    ).split()
                )
            )

            if matched:

                print(
                    "    REQUIRED NAME MATCH :",
                    sorted(matched),
                )

        if item["keywords"]:

            print(
                "KWARGS:"
            )

            for key, value in item["keywords"]:

                print(
                    f"  {key} = {value}"
                )


# =============================================================================
# PASS 4
# SEARCH FOR ALIASES
# =============================================================================

def find_aliases(files):

    aliases = []

    for path in files:

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                text,
                filename=str(path),
            )
        except SyntaxError:
            continue

        for node in ast.walk(tree):

            if isinstance(
                node,
                ast.Assign,
            ):

                if len(node.targets) != 1:
                    continue

                target = node.targets[0]

                if not isinstance(
                    target,
                    ast.Name,
                ):
                    continue

                value = expr_text(
                    node.value
                )

                if any(
                    name in value
                    for name in REQUIRED_NAMES
                ):

                    aliases.append({
                        "path": path,
                        "line": node.lineno,
                        "target": target.id,
                        "value": value,
                    })

    return aliases


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA — FIND REAL DECISION UPSTREAM v0.2"
    )
    print("=" * 100)

    print(
        "PROJECT ROOT :",
        PROJECT_ROOT,
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "IMPORTS      : NONE"
    )

    print(
        "DATABASE     : NOT TOUCHED"
    )

    print(
        "PIPELINE     : NOT EXECUTED"
    )

    print(
        "SOURCE EDIT  : NONE"
    )

    print("=" * 100)

    files = load_python_files()

    print()
    print(
        "PYTHON FILES SCANNED :",
        len(files),
    )

    # -------------------------------------------------------------------------
    # PASS 1
    # -------------------------------------------------------------------------

    targets = find_target_calls(
        files
    )

    print()
    print("=" * 100)
    print(
        "PASS 1 : REAL ENGINE CALLS"
    )
    print("=" * 100)

    if not targets:

        print(
            "NO TARGET CALLS FOUND."
        )

    else:

        for item in targets:

            print()
            print("-" * 100)

            print(
                "FILE   :",
                item["path"],
            )

            print(
                "LINE   :",
                item["line"],
            )

            print(
                "CALL   :",
                item["call"],
            )

            print(
                "CALLER :",
                item["function"],
            )

            print(
                "ARGS   :",
                item["args"],
            )

            print(
                "KWARGS :",
                item["keywords"],
            )

    # -------------------------------------------------------------------------
    # PASS 2
    # -------------------------------------------------------------------------

    upstream = find_upstream_functions(
        files
    )

    print()
    print("=" * 100)
    print(
        "PASS 2 : FUNCTIONS WITH REAL UPSTREAM INPUTS"
    )
    print("=" * 100)

    if not upstream:

        print(
            "NO FUNCTION USING ALL THREE REQUIRED OBJECTS FOUND."
        )

    else:

        for item in upstream:

            print()
            print("-" * 100)

            print(
                "TYPE     :",
                item["kind"],
            )

            print(
                "FILE     :",
                item["path"],
            )

            print(
                "LINE     :",
                item["line"],
            )

            print(
                "FUNCTION :",
                item["function"],
            )

            print(
                "PARAMS   :",
                item["params"],
            )

            print(
                "USED     :",
                item["used"],
            )

    # -------------------------------------------------------------------------
    # PASS 3
    # -------------------------------------------------------------------------

    print_argument_analysis(
        targets
    )

    # -------------------------------------------------------------------------
    # PASS 4
    # -------------------------------------------------------------------------

    aliases = find_aliases(
        files
    )

    print()
    print("=" * 100)
    print(
        "PASS 4 : POSSIBLE UPSTREAM ALIASES"
    )
    print("=" * 100)

    if not aliases:

        print(
            "NO DIRECT ALIASES FOUND."
        )

    else:

        for item in aliases:

            print()
            print("-" * 100)

            print(
                "FILE   :",
                item["path"],
            )

            print(
                "LINE   :",
                item["line"],
            )

            print(
                "ALIAS  :",
                item["target"],
            )

            print(
                "VALUE  :",
                item["value"],
            )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print(
        "FINAL RESULT"
    )
    print("=" * 100)

    decision_main_calls = [
        x
        for x in targets
        if x["call"] == "decision_engine.main"
    ]

    scorer_calls = [
        x
        for x in targets
        if x["call"] == "signal_scorer.run"
    ]

    print(
        "decision_engine.main calls :",
        len(decision_main_calls),
    )

    print(
        "signal_scorer.run calls    :",
        len(scorer_calls),
    )

    print(
        "three-input functions      :",
        len(upstream),
    )

    print()

    if decision_main_calls:

        print(
            "DECISION ENTRYPOINT : FOUND"
        )

    else:

        print(
            "DECISION ENTRYPOINT : NOT FOUND"
        )

    if scorer_calls:

        print(
            "SCORER RUNTIME ENTRYPOINT : FOUND"
        )

    else:

        print(
            "SCORER RUNTIME ENTRYPOINT : NOT FOUND"
        )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This script does NOT modify any project file."
    )

    print(
        "This script does NOT execute the trading pipeline."
    )

    print(
        "This script does NOT touch the database."
    )

    print("=" * 100)
    print(
        "SCAN COMPLETE"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )