from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

SKIP = {
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "env",
    ".pytest_cache",
}

print("=" * 100)
print("ARUNDA — REAL DECISION UPSTREAM PRODUCER FINDER v0.4")
print("=" * 100)
print("PROJECT ROOT :", ROOT)
print("MODE         : READ ONLY")
print("IMPORTS      : NONE")
print("EXECUTION    : NONE")
print("DATABASE     : NOT TOUCHED")
print("SOURCE EDIT  : NONE")
print("=" * 100)


# =============================================================================
# FILE DISCOVERY
# =============================================================================

files = [
    p
    for p in ROOT.rglob("*.py")
    if not any(part in SKIP for part in p.parts)
]

print()
print("PYTHON FILES :", len(files))
print()


# =============================================================================
# HELPERS
# =============================================================================

def dotted_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        base = dotted_name(node.value)

        if base:
            return base + "." + node.attr

        return node.attr

    return None


def target_names(node):

    names = set()

    if node is None:
        return names

    if isinstance(node, ast.Name):

        names.add(node.id)

    elif isinstance(
        node,
        (ast.Tuple, ast.List),
    ):

        for item in node.elts:
            names.update(
                target_names(item)
            )

    return names


def expression_summary(node):

    if node is None:
        return "<none>"

    if isinstance(node, ast.Call):

        fn = (
            dotted_name(node.func)
            or "<call>"
        )

        args = []

        for arg in node.args:

            if isinstance(
                arg,
                ast.Name,
            ):

                args.append(
                    arg.id
                )

            else:

                try:
                    args.append(
                        ast.unparse(arg)
                    )
                except Exception:
                    args.append(
                        "<expression>"
                    )

        return (
            f"{fn}("
            + ", ".join(args)
            + ")"
        )

    if isinstance(
        node,
        ast.Name,
    ):

        return node.id

    try:

        return ast.unparse(
            node
        )

    except Exception:

        return "<expression>"


def collect_names(node):

    names = set()

    if node is None:
        return names

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ):

            names.add(
                child.id
            )

    return names


# =============================================================================
# SCAN
# =============================================================================

results = []


for path in files:

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:

        continue


    for node in ast.walk(tree):

        # =====================================================================
        # ASSIGNMENT
        # =====================================================================

        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):

            targets = set()

            if isinstance(
                node,
                ast.Assign,
            ):

                for target in node.targets:

                    targets.update(
                        target_names(
                            target
                        )
                    )

                value = node.value

            else:

                targets.update(
                    target_names(
                        node.target
                    )
                )

                value = node.value

            hit = targets & TARGETS

            if hit:

                results.append({
                    "kind": "ASSIGNMENT",
                    "file": str(path),
                    "line": node.lineno,
                    "targets": sorted(hit),
                    "expression":
                        expression_summary(
                            value
                        ),
                })


        # =====================================================================
        # RETURN
        # =====================================================================

        elif isinstance(
            node,
            ast.Return,
        ):

            # IMPORTANT:
            # `return` without expression has node.value == None.

            if node.value is None:
                continue

            names = collect_names(
                node.value
            )

            hit = names & TARGETS

            if hit:

                results.append({
                    "kind": "RETURN",
                    "file": str(path),
                    "line": node.lineno,
                    "targets": sorted(hit),
                    "expression":
                        expression_summary(
                            node.value
                        ),
                })


        # =====================================================================
        # FUNCTION CALL USING >= 2 TARGETS
        # =====================================================================

        elif isinstance(
            node,
            ast.Call,
        ):

            arg_names = set()

            for arg in node.args:

                arg_names.update(
                    collect_names(
                        arg
                    )
                )

            for keyword in node.keywords:

                arg_names.update(
                    collect_names(
                        keyword.value
                    )
                )

            hit = arg_names & TARGETS

            if len(hit) >= 2:

                results.append({
                    "kind":
                        "CALL_WITH_TARGET_INPUTS",
                    "file": str(path),
                    "line": node.lineno,
                    "targets": sorted(hit),
                    "expression":
                        expression_summary(
                            node
                        ),
                })


# =============================================================================
# REPORT 1
# =============================================================================

print("=" * 100)
print("REAL PRODUCER / RETURN / CALL CANDIDATES")
print("=" * 100)

if not results:

    print()
    print("NO CANDIDATES FOUND")

else:

    for index, item in enumerate(
        results,
        1,
    ):

        print()
        print("-" * 100)
        print(
            f"[{index}] {item['kind']}"
        )

        print(
            "FILE   :",
            item["file"],
        )

        print(
            "LINE   :",
            item["line"],
        )

        print(
            "TARGET :",
            item["targets"],
        )

        print(
            "CODE   :",
            item["expression"],
        )


# =============================================================================
# FUNCTION-LEVEL ANALYSIS
# =============================================================================

print()
print("=" * 100)
print("FUNCTIONS CONTAINING ALL THREE TARGET VARIABLES")
print("=" * 100)

function_hits = []


for path in files:

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:

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

        found = set()

        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Name,
            ):

                if child.id in TARGETS:

                    found.add(
                        child.id
                    )

        if found == TARGETS:

            function_hits.append(
                (
                    str(path),
                    node.lineno,
                    node.name,
                )
            )


if function_hits:

    for path, line, name in function_hits:

        print()
        print(
            "FILE     :",
            path,
        )

        print(
            "LINE     :",
            line,
        )

        print(
            "FUNCTION :",
            name,
        )

else:

    print()
    print(
        "NO FUNCTION CONTAINING ALL THREE "
        "TARGET VARIABLES FOUND"
    )


# =============================================================================
# DIRECT DECISION ENGINE CALLS
# =============================================================================

print()
print("=" * 100)
print("ALL decision_engine.main(...) CALL SITES")
print("=" * 100)

decision_calls = []


for path in files:

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:

        continue


    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):

            continue

        fn = dotted_name(
            node.func
        )

        if fn != "decision_engine.main":
            continue

        args = []

        for arg in node.args:

            args.append(
                expression_summary(
                    arg
                )
            )

        kwargs = []

        for kw in node.keywords:

            kwargs.append(
                (
                    kw.arg,
                    expression_summary(
                        kw.value
                    ),
                )
            )

        decision_calls.append(
            (
                str(path),
                node.lineno,
                args,
                kwargs,
            )
        )


if decision_calls:

    for (
        path,
        line,
        args,
        kwargs,
    ) in decision_calls:

        print()
        print(
            "FILE   :",
            path,
        )

        print(
            "LINE   :",
            line,
        )

        print(
            "ARGS   :",
            args,
        )

        print(
            "KWARGS :",
            kwargs,
        )

else:

    print()
    print(
        "NO decision_engine.main(...) CALL FOUND"
    )


# =============================================================================
# FINAL
# =============================================================================

print()
print("=" * 100)
print("FINAL FORENSIC RESULT")
print("=" * 100)

print(
    "TARGETS :",
    sorted(TARGETS),
)

print(
    "PRODUCER/CALL CANDIDATES :",
    len(results),
)

print(
    "FUNCTIONS WITH ALL THREE :",
    len(function_hits),
)

print(
    "decision_engine.main CALLS :",
    len(decision_calls),
)

print()
print(
    "NO SOURCE FILES MODIFIED."
)

print(
    "NO DATABASE ACCESSED."
)

print(
    "NO PIPELINE EXECUTED."
)

print("=" * 100)
print("SCAN COMPLETE")
print("=" * 100)