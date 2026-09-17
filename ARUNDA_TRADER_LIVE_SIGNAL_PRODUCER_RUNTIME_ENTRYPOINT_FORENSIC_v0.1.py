from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
}

IGNORED_FILES = {
    "ARUNDA_TRADER_LIVE_SIGNAL_PRODUCER_RUNTIME_ENTRYPOINT_FORENSIC_v0.1.py",
}

ENTRYPOINT_KEYWORDS = (
    "main",
    "run",
    "start",
    "launch",
    "execute",
)

PRODUCER_KEYWORDS = (
    "signal",
    "eligible",
    "eligibility",
    "fusion",
    "process_signal",
    "process_signals",
    "create_signal",
    "generate_signal",
    "build_signal",
    "produce_signal",
)

OUTPUT_KEYWORDS = (
    "json",
    "artifact",
    "report",
    "output",
    "dump",
    "write",
    "save",
    "open",
)


def rule() -> None:
    print("=" * 100)


def section(title: str) -> None:
    rule()
    print(title)
    rule()


def source_files() -> list[Path]:
    files: list[Path] = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS
        ]

        for filename in filenames:

            if filename in IGNORED_FILES:
                continue

            path = Path(root) / filename

            if path.suffix.lower() == ".py":
                files.append(path)

    return sorted(files)


def read_source(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def dotted_name(node: ast.AST) -> str | None:

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def line_of(node: ast.AST) -> int:
    return int(
        getattr(
            node,
            "lineno",
            0,
        )
    )


def end_line_of(node: ast.AST) -> int:
    return int(
        getattr(
            node,
            "end_lineno",
            line_of(node),
        )
    )


def node_source(
    text: str,
    node: ast.AST,
) -> str:

    lines = text.splitlines()

    start = line_of(node)
    end = end_line_of(node)

    if start <= 0:
        return ""

    return "\n".join(
        lines[start - 1:end]
    )


def contains_any(
    text: str,
    keywords: tuple[str, ...],
) -> bool:

    lowered = text.lower()

    return any(
        keyword.lower() in lowered
        for keyword in keywords
    )


def is_producer_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    text: str,
) -> bool:

    if contains_any(
        node.name,
        PRODUCER_KEYWORDS,
    ):
        return True

    source = node_source(
        text,
        node,
    )

    producer_hits = sum(
        1
        for keyword in PRODUCER_KEYWORDS
        if keyword.lower() in source.lower()
    )

    return producer_hits >= 2


def is_output_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    text: str,
) -> bool:

    source = node_source(
        text,
        node,
    )

    return (
        contains_any(
            node.name,
            OUTPUT_KEYWORDS,
        )
        and contains_any(
            source,
            (
                "json",
                "write",
                "dump",
                "open",
            ),
        )
    )


def collect_functions(
    path: Path,
) -> tuple[list[dict[str, Any]], str | None]:

    text = read_source(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        return [], str(exc)

    functions: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        source = node_source(
            text,
            node,
        )

        calls: list[str] = []

        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Call,
            ):

                callee = dotted_name(
                    child.func
                )

                if callee:
                    calls.append(
                        callee
                    )

        functions.append(
            {
                "name": node.name,
                "line": line_of(node),
                "end_line": end_line_of(node),
                "producer": is_producer_function(
                    node,
                    text,
                ),
                "output": is_output_function(
                    node,
                    text,
                ),
                "calls": sorted(
                    set(calls)
                ),
                "source": source,
            }
        )

    return functions, None


def collect_module_entrypoints(
    path: Path,
) -> tuple[list[dict[str, Any]], str | None]:

    text = read_source(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        return [], str(exc)

    results: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.If,
        ):
            continue

        test = node.test

        if not (
            isinstance(
                test,
                ast.Compare,
            )
        ):
            continue

        left = test.left

        if not (
            isinstance(
                left,
                ast.Name,
            )
        ):
            continue

        if left.id != "__name__":
            continue

        if not test.comparators:
            continue

        comparator = test.comparators[0]

        if not (
            isinstance(
                comparator,
                ast.Constant,
            )
        ):
            continue

        if comparator.value != "__main__":
            continue

        called_functions: list[str] = []

        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Call,
            ):

                callee = dotted_name(
                    child.func
                )

                if callee:
                    called_functions.append(
                        callee
                    )

        results.append(
            {
                "line": line_of(node),
                "end_line": end_line_of(node),
                "called_functions": sorted(
                    set(
                        called_functions
                    )
                ),
                "source": node_source(
                    text,
                    node,
                ),
            }
        )

    return results, None


def collect_top_level_calls(
    path: Path,
) -> tuple[list[dict[str, Any]], str | None]:

    text = read_source(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        return [], str(exc)

    calls: list[
        dict[str, Any]
    ] = []

    for node in tree.body:

        if not isinstance(
            node,
            ast.Expr,
        ):
            continue

        if not isinstance(
            node.value,
            ast.Call,
        ):
            continue

        callee = dotted_name(
            node.value.func
        )

        if not callee:
            continue

        calls.append(
            {
                "callee": callee,
                "line": line_of(node),
                "source": node_source(
                    text,
                    node,
                ),
            }
        )

    return calls, None


def collect_all_calls(
    path: Path,
) -> tuple[list[dict[str, Any]], str | None]:

    text = read_source(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )

    except SyntaxError as exc:
        return [], str(exc)

    calls: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        callee = dotted_name(
            node.func
        )

        if not callee:
            continue

        calls.append(
            {
                "callee": callee,
                "line": line_of(node),
                "source": node_source(
                    text,
                    node,
                ),
            }
        )

    return calls, None


def main() -> int:

    rule()

    print(
        "ARUNDA TRADER — LIVE SIGNAL PRODUCER "
        "RUNTIME ENTRYPOINT FORENSIC v0.1"
    )

    rule()

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "PYTHON EXECUTION : NONE"
    )

    print(
        "DATABASE ACCESS  : NONE"
    )

    print(
        "WRITE            : NONE"
    )

    print(
        "ARTIFACT CREATION : NONE"
    )

    print(
        "NETWORK ACCESS   : NONE"
    )

    if not PROJECT_ROOT.exists():

        print(
            "ERROR : PROJECT ROOT NOT FOUND"
        )

        return 1

    section(
        "A) PYTHON SOURCE INVENTORY"
    )

    files = source_files()

    print(
        f"PYTHON FILES : {len(files)}"
    )

    all_functions: list[
        dict[str, Any]
    ] = []

    all_entrypoints: list[
        dict[str, Any]
    ] = []

    all_calls: list[
        dict[str, Any]
    ] = []

    parse_failures: list[
        dict[str, str]
    ] = []

    for path in files:

        functions, error = (
            collect_functions(path)
        )

        if error:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": error,
                }
            )

        for item in functions:

            item["file"] = str(path)

            all_functions.append(
                item
            )

        entrypoints, entry_error = (
            collect_module_entrypoints(
                path
            )
        )

        if entry_error:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": entry_error,
                }
            )

        for item in entrypoints:

            item["file"] = str(path)

            all_entrypoints.append(
                item
            )

        calls, call_error = (
            collect_all_calls(
                path
            )
        )

        if call_error:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": call_error,
                }
            )

        for item in calls:

            item["file"] = str(path)

            all_calls.append(
                item
            )

    print(
        f"FUNCTIONS DISCOVERED : "
        f"{len(all_functions)}"
    )

    print(
        f"__main__ ENTRYPOINT BLOCKS : "
        f"{len(all_entrypoints)}"
    )

    print(
        f"TOTAL CALLS DISCOVERED : "
        f"{len(all_calls)}"
    )

    print(
        f"PARSE FAILURES : "
        f"{len(parse_failures)}"
    )

    section(
        "B) REAL __MAIN__ ENTRYPOINTS"
    )

    if not all_entrypoints:

        print(
            "NO __main__ ENTRYPOINT FOUND."
        )

    else:

        for item in all_entrypoints:

            print(
                f"\nFILE : {item['file']}"
            )

            print(
                f"LINES : "
                f"{item['line']}-"
                f"{item['end_line']}"
            )

            print(
                "CALLED FUNCTIONS : "
                f"{item['called_functions']}"
            )

            print(
                "SOURCE:"
            )

            print(
                item["source"]
            )

    section(
        "C) SIGNAL / ELIGIBILITY PRODUCER DEFINITIONS"
    )

    producer_functions = [
        item
        for item in all_functions
        if item["producer"]
    ]

    print(
        f"PRODUCER-LIKE FUNCTIONS : "
        f"{len(producer_functions)}"
    )

    for item in producer_functions:

        print(
            f"\nFILE : {item['file']}"
        )

        print(
            f"FUNCTION : {item['name']}"
        )

        print(
            f"LINES : "
            f"{item['line']}-"
            f"{item['end_line']}"
        )

        print(
            f"CALLS : {item['calls']}"
        )

    section(
        "D) OUTPUT / ARTIFACT WRITER CANDIDATES"
    )

    output_functions = [
        item
        for item in all_functions
        if item["output"]
    ]

    print(
        f"OUTPUT WRITER CANDIDATES : "
        f"{len(output_functions)}"
    )

    for item in output_functions:

        print(
            f"\nFILE : {item['file']}"
        )

        print(
            f"FUNCTION : {item['name']}"
        )

        print(
            f"LINES : "
            f"{item['line']}-"
            f"{item['end_line']}"
        )

        print(
            "SOURCE:"
        )

        print(
            item["source"]
        )

    section(
        "E) ENTRYPOINT → PRODUCER STATIC BINDING"
    )

    binding_results: list[
        dict[str, Any]
    ] = []

    producer_names = {
        item["name"]
        for item in producer_functions
    }

    producer_dotted_names = {
        item["name"]
        for item in producer_functions
    }

    for entrypoint in all_entrypoints:

        called = set(
            entrypoint[
                "called_functions"
            ]
        )

        direct_matches = (
            called
            & producer_names
        )

        if direct_matches:

            binding_results.append(
                {
                    "file": entrypoint[
                        "file"
                    ],
                    "line": entrypoint[
                        "line"
                    ],
                    "matches": sorted(
                        direct_matches
                    ),
                }
            )

            print(
                f"\nENTRYPOINT : "
                f"{entrypoint['file']}"
            )

            print(
                f"DIRECT PRODUCER MATCH : "
                f"{sorted(direct_matches)}"
            )

    if not binding_results:

        print(
            "NO DIRECT __main__ → PRODUCER "
            "STATIC BINDING FOUND."
        )

    section(
        "F) CALL-CHAIN SEARCH AROUND PRODUCER"
    )

    producer_callers: list[
        dict[str, Any]
    ] = []

    for call in all_calls:

        callee = call["callee"]

        callee_leaf = callee.split(
            "."
        )[-1]

        if (
            callee_leaf in producer_dotted_names
        ):

            producer_callers.append(
                call
            )

    print(
        f"CALLS TO PRODUCER NAMES : "
        f"{len(producer_callers)}"
    )

    for call in producer_callers:

        print(
            f"\nFILE : {call['file']}"
        )

        print(
            f"LINE : {call['line']}"
        )

        print(
            f"CALL : {call['callee']}"
        )

        print(
            "SOURCE:"
        )

        print(
            call["source"]
        )

    section(
        "G) RUNTIME ENTRYPOINT DECISION"
    )

    if not all_entrypoints:

        verdict = (
            "NO_PYTHON_MAIN_ENTRYPOINT_FOUND"
        )

        reason = (
            "No __main__ execution block was "
            "found in the project Python source."
        )

    elif not producer_functions:

        verdict = (
            "PRODUCER_DEFINITION_NOT_FOUND"
        )

        reason = (
            "No signal/eligibility producer-like "
            "function was found."
        )

    elif binding_results:

        verdict = (
            "MAIN_ENTRYPOINT_DIRECTLY_REACHES_PRODUCER"
        )

        reason = (
            "At least one __main__ entrypoint "
            "contains a direct static call to a "
            "signal/eligibility producer."
        )

    elif producer_callers:

        verdict = (
            "PRODUCER_EXISTS_BUT_MAIN_TO_PRODUCER "
            "REQUIRES_CALL_CHAIN_REVIEW"
        )

        reason = (
            "Producer functions and producer call "
            "sites exist, but the __main__ entrypoint "
            "does not directly call the producer. "
            "The intermediate call chain must be "
            "resolved."
        )

    else:

        verdict = (
            "PRODUCER_EXISTS_WITHOUT_DISCOVERED_RUNTIME_REACHABILITY"
        )

        reason = (
            "Producer definitions exist, but no "
            "static caller chain from a discovered "
            "__main__ entrypoint was established."
        )

    print(
        f"VERDICT : {verdict}"
    )

    print(
        f"REASON  : {reason}"
    )

    section(
        "H) IMPORTANT LIMITATION"
    )

    print(
        "This forensic is STATIC AST inspection only."
    )

    print(
        "It does NOT execute Python."
    )

    print(
        "It does NOT inspect runtime memory."
    )

    print(
        "It does NOT access the database."
    )

    print(
        "It does NOT create an eligible signal."
    )

    print(
        "It does NOT create an order intent."
    )

    print(
        "It does NOT modify JSON artifacts."
    )

    print(
        "It does NOT modify source code."
    )

    section(
        "I) SAFETY ASSERTION"
    )

    print(
        "PYTHON EXECUTION   : False"
    )

    print(
        "DATABASE READ      : False"
    )

    print(
        "DATABASE WRITE     : False"
    )

    print(
        "JSON WRITE         : False"
    )

    print(
        "ARTIFACT CREATION  : False"
    )

    print(
        "ORDER CREATION     : False"
    )

    print(
        "ORDER SUBMISSION   : False"
    )

    print(
        "NETWORK ACCESS     : False"
    )

    print(
        "ARTIFACT MUTATION  : False"
    )

    rule()

    print(
        "END — READ ONLY LIVE SIGNAL PRODUCER "
        "RUNTIME ENTRYPOINT FORENSIC v0.1"
    )

    rule()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())