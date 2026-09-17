from pathlib import Path
import ast


# =============================================================================
# ARUNDA DECISION UPSTREAM CALLER FINDER v0.1
# =============================================================================
#
# PURPOSE
# -------
# Find the REAL caller(s) that can provide:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# to:
#
#     decision_engine.main(...)
#
# READ ONLY
# NO IMPORTS OF PROJECT MODULES
# NO PIPELINE EXECUTION
# NO DATABASE ACCESS
# NO SOURCE MODIFICATION
#
# =============================================================================


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILE = "decision_engine.py"

TARGET_FUNCTION = "main"

REQUIRED_NAMES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}


# =============================================================================
# HELPERS
# =============================================================================

def source_line(lines, lineno):
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def function_name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    return "<module>"


def get_parent_map(tree):
    parents = {}

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    return parents


def get_enclosing_function(node, parents):
    current = node

    while current in parents:
        current = parents[current]

        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            return current

    return None


def get_call_name(node):
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

        return ".".join(reversed(parts))

    return "<unknown>"


# =============================================================================
# MAIN SCAN
# =============================================================================

def main():

    print("=" * 100)
    print("ARUNDA DECISION UPSTREAM CALLER FINDER v0.1")
    print("=" * 100)

    print("PROJECT ROOT :", PROJECT_ROOT)
    print("TARGET       : decision_engine.main(...)")
    print("MODE         : READ ONLY")
    print("IMPORTS      : NONE")
    print("PIPELINE     : NOT EXECUTED")
    print("DATABASE     : NOT TOUCHED")
    print("SOURCE EDIT  : NONE")
    print("=" * 100)
    print()

    if not PROJECT_ROOT.exists():

        print("ERROR: Project root does not exist.")
        return 1

    py_files = sorted(
        PROJECT_ROOT.rglob("*.py")
    )

    print(
        "PYTHON FILES FOUND :",
        len(py_files)
    )
    print()

    # -------------------------------------------------------------------------
    # PASS 1
    # Find every syntactic call to decision_engine.main(...)
    # -------------------------------------------------------------------------

    callers = []

    print("=" * 100)
    print("PASS 1 : FIND decision_engine.main(...) CALLS")
    print("=" * 100)

    for path in py_files:

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            try:
                text = path.read_text(
                    encoding="utf-8-sig"
                )
            except Exception:
                continue

        try:
            tree = ast.parse(
                text,
                filename=str(path)
            )
        except SyntaxError:
            continue

        lines = text.splitlines()
        parents = get_parent_map(tree)

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            call_name = get_call_name(node)

            if call_name not in (
                "decision_engine.main",
                "main",
            ):
                continue

            # We only want explicit decision_engine.main()
            if call_name != "decision_engine.main":
                continue

            enclosing = get_enclosing_function(
                node,
                parents,
            )

            caller_name = (
                function_name(enclosing)
                if enclosing
                else "<module>"
            )

            callers.append({
                "path": path,
                "line": node.lineno,
                "caller": caller_name,
                "args": node.args,
                "keywords": node.keywords,
                "line_text": source_line(
                    lines,
                    node.lineno,
                ),
            })

    print()

    if not callers:

        print(
            "NO EXPLICIT decision_engine.main(...) CALL FOUND."
        )

        print()
        print(
            "Searching for imported/aliased main references..."
        )

    else:

        print(
            "EXPLICIT decision_engine.main CALLS :",
            len(callers),
        )

        print()

        for item in callers:

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
                "CALLER :",
                item["caller"],
            )

            print(
                "SOURCE :",
                item["line_text"],
            )

            print(
                "ARGS   :",
                len(item["args"]),
            )

            print(
                "KWARGS :",
                len(item["keywords"]),
            )

    # -------------------------------------------------------------------------
    # PASS 2
    # Find where the three required objects are CREATED / ASSIGNED
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PASS 2 : FIND REAL UPSTREAM INPUT VARIABLES")
    print("=" * 100)

    definitions = {
        name: []
        for name in REQUIRED_NAMES
    }

    for path in py_files:

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                text,
                filename=str(path)
            )
        except SyntaxError:
            continue

        lines = text.splitlines()

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Assign,
            ):
                continue

            for target in node.targets:

                if not isinstance(
                    target,
                    ast.Name,
                ):
                    continue

                name = target.id

                if name not in REQUIRED_NAMES:
                    continue

                definitions[name].append({
                    "path": path,
                    "line": node.lineno,
                    "source": source_line(
                        lines,
                        node.lineno,
                    ),
                })

    for name in REQUIRED_NAMES:

        print()
        print(
            f"[{name}]"
        )

        if not definitions[name]:

            print(
                "  NOT FOUND"
            )

        else:

            for item in definitions[name]:

                print(
                    "  FILE   :",
                    item["path"],
                )

                print(
                    "  LINE   :",
                    item["line"],
                )

                print(
                    "  SOURCE :",
                    item["source"],
                )

    # -------------------------------------------------------------------------
    # PASS 3
    # Find functions whose PARAMETERS contain all three objects
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PASS 3 : FIND FUNCTIONS RECEIVING ALL THREE INPUTS")
    print("=" * 100)

    upstream_functions = []

    for path in py_files:

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                text,
                filename=str(path)
            )
        except SyntaxError:
            continue

        lines = text.splitlines()

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            args = []

            args.extend(
                arg.arg
                for arg in node.args.posonlyargs
            )

            args.extend(
                arg.arg
                for arg in node.args.args
            )

            args.extend(
                arg.arg
                for arg in node.args.kwonlyargs
            )

            present = (
                REQUIRED_NAMES
                & set(args)
            )

            if present == REQUIRED_NAMES:

                upstream_functions.append({
                    "path": path,
                    "line": node.lineno,
                    "function": node.name,
                    "args": args,
                    "source": source_line(
                        lines,
                        node.lineno,
                    ),
                })

    if not upstream_functions:

        print(
            "NO FUNCTION WITH ALL THREE PARAMETERS FOUND."
        )

    else:

        for item in upstream_functions:

            print()
            print("-" * 100)

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
                ", ".join(item["args"]),
            )

            print(
                "SOURCE   :",
                item["source"],
            )

    # -------------------------------------------------------------------------
    # PASS 4
    # Look for functions that CALL decision_engine.main
    # AND contain/use the three real variables.
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PASS 4 : CROSS-MATCH REAL CALLER")
    print("=" * 100)

    real_candidates = []

    for item in callers:

        path = item["path"]

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        try:
            tree = ast.parse(
                text,
                filename=str(path)
            )
        except SyntaxError:
            continue

        parents = get_parent_map(tree)

        target_call = None

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if get_call_name(node) != "decision_engine.main":
                continue

            if node.lineno == item["line"]:

                target_call = node
                break

        if target_call is None:
            continue

        enclosing = get_enclosing_function(
            target_call,
            parents,
        )

        if enclosing is None:
            continue

        used_names = set()

        for node in ast.walk(enclosing):

            if isinstance(
                node,
                ast.Name,
            ):

                used_names.add(
                    node.id
                )

        present = (
            REQUIRED_NAMES
            & used_names
        )

        if present:

            real_candidates.append({
                "path": path,
                "line": item["line"],
                "caller": enclosing.name,
                "present": present,
            })

    if not real_candidates:

        print()
        print(
            "NO DIRECT CROSS-MATCH FOUND."
        )

        print(
            "This means the caller may pass aliases, "
            "returned objects, or values from another function."
        )

    else:

        for item in real_candidates:

            print()
            print("🔥 REAL CALLER CANDIDATE")
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
                "CALLER :",
                item["caller"],
            )

            print(
                "INPUTS :",
                ", ".join(
                    sorted(item["present"])
                ),
            )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL FORENSIC RESULT")
    print("=" * 100)

    if real_candidates:

        print(
            "REAL CALLER : FOUND"
        )

        for item in real_candidates:

            print()
            print(
                "FILE   :",
                item["path"],
            )

            print(
                "LINE   :",
                item["line"],
            )

            print(
                "CALLER :",
                item["caller"],
            )

            print(
                "INPUTS :",
                ", ".join(
                    sorted(item["present"])
                )

            )

    elif callers:

        print(
            "decision_engine.main(...) : FOUND"
        )

        print(
            "REAL THREE-INPUT BRIDGE   : NOT YET RESOLVED"
        )

        print(
            "NEXT : inspect caller argument expressions."
        )

    else:

        print(
            "decision_engine.main(...) : NOT FOUND"
        )

        print(
            "Search result : caller must be indirect/aliased."
        )

    print()
    print("=" * 100)
    print(
        "SCAN COMPLETE — NO SOURCE CHANGES"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )