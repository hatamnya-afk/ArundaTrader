from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}

FORENSIC_FILE_MARKERS = (
    "FORENSIC",
    "AUDIT",
    "DIAGNOSTIC",
    "REPAIR",
    "WATCHER",
    "TRACE",
    "VERIFICATION",
    "PREFLIGHT",
    "HEALTH",
    "REPORT",
)

SIGNAL_TERMS = (
    "signal",
    "fusion",
)

GENERATOR_TERMS = (
    "order_intent",
    "order_intents",
    "generate_order",
    "generate_intent",
)

ENTRYPOINT_NAMES = {
    "main",
}


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def function_source(
    text: str,
    node: ast.AST,
) -> str:
    lines = text.splitlines()

    start = int(getattr(node, "lineno", 0))
    end = int(
        getattr(
            node,
            "end_lineno",
            getattr(node, "lineno", 0),
        )
    )

    if start <= 0:
        return ""

    return "\n".join(lines[start - 1:end])


def contains_term(
    value: str,
    terms: tuple[str, ...],
) -> bool:
    lowered = value.lower()

    return any(
        term.lower() in lowered
        for term in terms
    )


def is_excluded(path: Path) -> bool:
    return any(
        part in EXCLUDED_DIRS
        for part in path.parts
    )


def is_forensic_file(path: Path) -> bool:
    upper = path.name.upper()

    return any(
        marker in upper
        for marker in FORENSIC_FILE_MARKERS
    )


def safe_parse(path: Path) -> tuple[ast.AST | None, str | None]:
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        return (
            ast.parse(
                text,
                filename=str(path),
            ),
            None,
        )

    except Exception as exc:
        return None, str(exc)


def collect_functions(
    path: Path,
    tree: ast.AST,
) -> list[dict[str, Any]]:
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    result: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        source = function_source(
            text,
            node,
        )

        result.append(
            {
                "name": node.name,
                "line": int(
                    getattr(
                        node,
                        "lineno",
                        0,
                    )
                ),
                "end_line": int(
                    getattr(
                        node,
                        "end_lineno",
                        getattr(
                            node,
                            "lineno",
                            0,
                        ),
                    )
                ),
                "source": source,
                "file": str(path),
            }
        )

    return result


def collect_calls(
    path: Path,
    tree: ast.AST,
) -> list[dict[str, Any]]:
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    calls: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        callee = dotted_name(node.func)

        if not callee:
            continue

        source = function_source(
            text,
            node,
        )

        args: list[str] = []

        for arg in node.args:
            name = dotted_name(arg)

            if name:
                args.append(name)
            else:
                args.append(
                    ast.unparse(arg)
                    if hasattr(ast, "unparse")
                    else "<expression>"
                )

        keyword_args: dict[str, str] = {}

        for kw in node.keywords:
            key = kw.arg or "**"

            keyword_args[key] = (
                dotted_name(kw.value)
                or (
                    ast.unparse(kw.value)
                    if hasattr(ast, "unparse")
                    else "<expression>"
                )
            )

        calls.append(
            {
                "file": str(path),
                "callee": callee,
                "line": int(
                    getattr(
                        node,
                        "lineno",
                        0,
                    )
                ),
                "end_line": int(
                    getattr(
                        node,
                        "end_lineno",
                        getattr(
                            node,
                            "lineno",
                            0,
                        ),
                    )
                ),
                "args": args,
                "keyword_args": keyword_args,
                "source": source,
            }
        )

    return calls


def resolve_local_function_calls(
    functions: list[dict[str, Any]],
    calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    known = {
        item["name"]
        for item in functions
    }

    resolved = []

    for call in calls:
        callee = call["callee"]

        base = callee.split(".")[-1]

        if base in known:
            resolved.append(call)

    return resolved


def classify_signal_function(
    function: dict[str, Any],
) -> bool:
    name = function["name"]
    source = function["source"]

    return (
        contains_term(
            name,
            SIGNAL_TERMS,
        )
        or contains_term(
            source,
            SIGNAL_TERMS,
        )
    )


def classify_generator_function(
    function: dict[str, Any],
) -> bool:
    name = function["name"]
    source = function["source"]

    return (
        contains_term(
            name,
            GENERATOR_TERMS,
        )
        or contains_term(
            source,
            GENERATOR_TERMS,
        )
    )


def classify_generator_call(
    call: dict[str, Any],
) -> bool:
    blob = (
        call["callee"]
        + " "
        + call["source"]
    )

    return contains_term(
        blob,
        GENERATOR_TERMS,
    )


def classify_signal_call(
    call: dict[str, Any],
) -> bool:
    blob = (
        call["callee"]
        + " "
        + call["source"]
    )

    return contains_term(
        blob,
        SIGNAL_TERMS,
    )


def build_function_call_graph(
    path: Path,
    tree: ast.AST,
) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}

    function_nodes: dict[str, ast.AST] = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            function_nodes[node.name] = node

    for function_name, function_node in function_nodes.items():

        graph.setdefault(
            function_name,
            [],
        )

        for node in ast.walk(function_node):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            callee = dotted_name(node.func)

            if not callee:
                continue

            base = callee.split(".")[-1]

            if base in function_nodes:
                graph[function_name].append(
                    base
                )

    for key in graph:
        graph[key] = sorted(
            set(graph[key])
        )

    return graph


def find_main_functions(
    functions_by_file: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    results = []

    for file_path, functions in functions_by_file.items():

        path = Path(file_path)

        if is_forensic_file(path):
            continue

        for function in functions:

            if function["name"] in ENTRYPOINT_NAMES:

                results.append(
                    {
                        "file": file_path,
                        "name": function["name"],
                        "line": function["line"],
                        "source": function["source"],
                    }
                )

    return results


def find_signal_functions(
    functions_by_file: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    results = []

    for file_path, functions in functions_by_file.items():

        path = Path(file_path)

        if is_forensic_file(path):
            continue

        for function in functions:

            if classify_signal_function(function):

                results.append(
                    function
                )

    return results


def find_generator_functions(
    functions_by_file: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    results = []

    for file_path, functions in functions_by_file.items():

        path = Path(file_path)

        if is_forensic_file(path):
            continue

        for function in functions:

            if classify_generator_function(function):

                results.append(
                    function
                )

    return results


def find_generator_calls(
    calls_by_file: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    results = []

    for file_path, calls in calls_by_file.items():

        path = Path(file_path)

        if is_forensic_file(path):
            continue

        for call in calls:

            if classify_generator_call(call):

                results.append(
                    call
                )

    return results


def find_signal_related_calls(
    calls_by_file: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    results = []

    for file_path, calls in calls_by_file.items():

        path = Path(file_path)

        if is_forensic_file(path):
            continue

        for call in calls:

            if classify_signal_call(call):

                results.append(
                    call
                )

    return results


def function_contains_call_to(
    function: dict[str, Any],
    target_names: set[str],
) -> bool:
    source = function["source"]

    lowered = source.lower()

    return any(
        name.lower() in lowered
        for name in target_names
    )


def find_direct_signal_to_generator(
    signal_functions: list[dict[str, Any]],
    generator_names: set[str],
) -> list[dict[str, Any]]:
    results = []

    for signal_function in signal_functions:

        if function_contains_call_to(
            signal_function,
            generator_names,
        ):
            results.append(
                signal_function
            )

    return results


def find_generator_calls_receiving_signal(
    generator_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []

    for call in generator_calls:

        blob_parts = [
            call["callee"],
            call["source"],
            " ".join(call["args"]),
            " ".join(
                call["keyword_args"].values()
            ),
        ]

        blob = " ".join(blob_parts).lower()

        if any(
            term in blob
            for term in (
                "signal",
                "signals",
                "eligible_signal",
                "eligible_signals",
                "fusion",
                "row_results",
                "artifact",
            )
        ):
            results.append(call)

    return results


def find_main_to_signal_paths(
    main_functions: list[dict[str, Any]],
    signal_names: set[str],
) -> list[dict[str, Any]]:
    results = []

    for main in main_functions:

        source = main["source"]

        matched = []

        for signal_name in signal_names:

            if signal_name.lower() in source.lower():
                matched.append(
                    signal_name
                )

        if matched:

            results.append(
                {
                    "main": main,
                    "matched_signal_functions": sorted(
                        set(matched)
                    ),
                }
            )

    return results


def main() -> int:

    print_section(
        "ARUNDA TRADER — REAL RUNTIME SIGNAL → GENERATOR TRACE v0.1"
    )

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
        "NETWORK ACCESS   : NONE"
    )

    print_section(
        "A) SOURCE DISCOVERY"
    )

    if not PROJECT_ROOT.exists():
        print(
            "ERROR : PROJECT ROOT NOT FOUND"
        )
        return 1

    python_files = sorted(
        path
        for path in PROJECT_ROOT.rglob("*.py")
        if not is_excluded(path)
    )

    print(
        f"PYTHON FILES DISCOVERED : {len(python_files)}"
    )

    functions_by_file: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    calls_by_file: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    parse_failures: list[
        tuple[str, str]
    ] = []

    for path in python_files:

        tree, error = safe_parse(path)

        if tree is None:

            parse_failures.append(
                (
                    str(path),
                    error or "UNKNOWN",
                )
            )

            continue

        functions_by_file[
            str(path)
        ] = collect_functions(
            path,
            tree,
        )

        calls_by_file[
            str(path)
        ] = collect_calls(
            path,
            tree,
        )

    print(
        f"PARSE FAILURES : {len(parse_failures)}"
    )

    if parse_failures:

        for file_path, error in parse_failures:
            print(
                f"\nPARSE FAILURE : {file_path}"
            )
            print(
                f"ERROR : {error}"
            )

    print_section(
        "B) REAL RUNTIME ENTRYPOINT"
    )

    main_functions = find_main_functions(
        functions_by_file
    )

    print(
        f"NON-FORENSIC MAIN FUNCTIONS : "
        f"{len(main_functions)}"
    )

    for item in main_functions:

        print(
            f"\nENTRYPOINT : {item['file']}"
        )
        print(
            f"FUNCTION   : {item['name']}"
        )
        print(
            f"LINE       : {item['line']}"
        )

    print_section(
        "C) SIGNAL PRODUCER FUNCTIONS"
    )

    signal_functions = find_signal_functions(
        functions_by_file
    )

    print(
        f"SIGNAL-RELATED FUNCTIONS : "
        f"{len(signal_functions)}"
    )

    for function in signal_functions:

        print(
            f"\nSIGNAL FUNCTION : "
            f"{function['file']}"
        )

        print(
            f"NAME : {function['name']}"
        )

        print(
            f"LINES : "
            f"{function['line']}-"
            f"{function['end_line']}"
        )

    print_section(
        "D) ORDER-INTENT GENERATOR"
    )

    generator_functions = find_generator_functions(
        functions_by_file
    )

    generator_names = {
        function["name"]
        for function in generator_functions
    }

    print(
        f"GENERATOR-LIKE FUNCTIONS : "
        f"{len(generator_functions)}"
    )

    for function in generator_functions:

        print(
            f"\nGENERATOR FUNCTION : "
            f"{function['file']}"
        )

        print(
            f"NAME : {function['name']}"
        )

        print(
            f"LINES : "
            f"{function['line']}-"
            f"{function['end_line']}"
        )

    print_section(
        "E) GENERATOR CALL SITES"
    )

    generator_calls = find_generator_calls(
        calls_by_file
    )

    print(
        f"GENERATOR CALL SITES : "
        f"{len(generator_calls)}"
    )

    for call in generator_calls:

        print(
            f"\nFILE : {call['file']}"
        )

        print(
            f"CALL : {call['callee']}"
        )

        print(
            f"LINE : {call['line']}"
        )

        print(
            f"ARGS : {call['args']}"
        )

        print(
            f"KEYWORDS : {call['keyword_args']}"
        )

    print_section(
        "F) GENERATOR CALL → SIGNAL INPUT BINDING"
    )

    signal_input_calls = (
        find_generator_calls_receiving_signal(
            generator_calls
        )
    )

    print(
        f"GENERATOR CALLS WITH SIGNAL-RELATED INPUT : "
        f"{len(signal_input_calls)}"
    )

    for call in signal_input_calls:

        print(
            f"\nFILE : {call['file']}"
        )

        print(
            f"CALL : {call['callee']}"
        )

        print(
            f"LINE : {call['line']}"
        )

        print(
            f"ARGS : {call['args']}"
        )

        print(
            f"KEYWORDS : {call['keyword_args']}"
        )

        print(
            "SOURCE:"
        )

        print(
            call["source"]
        )

    print_section(
        "G) SIGNAL FUNCTION → GENERATOR BOUNDARY"
    )

    direct_signal_generator = (
        find_direct_signal_to_generator(
            signal_functions,
            generator_names,
        )
    )

    print(
        f"DIRECT SIGNAL → GENERATOR FUNCTIONS : "
        f"{len(direct_signal_generator)}"
    )

    for function in direct_signal_generator:

        print(
            f"\nFILE : {function['file']}"
        )

        print(
            f"FUNCTION : {function['name']}"
        )

        print(
            f"LINES : "
            f"{function['line']}-"
            f"{function['end_line']}"
        )

    print_section(
        "H) MAIN → SIGNAL PRODUCER PATH"
    )

    signal_names = {
        function["name"]
        for function in signal_functions
    }

    main_signal_paths = find_main_to_signal_paths(
        main_functions,
        signal_names,
    )

    print(
        f"MAIN → SIGNAL STATIC PATH CANDIDATES : "
        f"{len(main_signal_paths)}"
    )

    for item in main_signal_paths:

        main_item = item["main"]

        print(
            f"\nENTRYPOINT : "
            f"{main_item['file']}"
        )

        print(
            f"MAIN LINE : "
            f"{main_item['line']}"
        )

        print(
            "SIGNAL FUNCTIONS REFERENCED : "
            f"{item['matched_signal_functions']}"
        )

    print_section(
        "I) FUNCTION CALL GRAPH"
    )

    graph_count = 0

    for file_path in sorted(
        functions_by_file
    ):

        if is_forensic_file(
            Path(file_path)
        ):
            continue

        tree, error = safe_parse(
            Path(file_path)
        )

        if tree is None:
            continue

        graph = build_function_call_graph(
            Path(file_path),
            tree,
        )

        interesting = {
            key: value
            for key, value in graph.items()
            if (
                key in signal_names
                or key in generator_names
                or any(
                    child in signal_names
                    or child in generator_names
                    for child in value
                )
            )
        }

        if not interesting:
            continue

        graph_count += len(
            interesting
        )

        print(
            f"\nFILE : {file_path}"
        )

        for caller, callees in sorted(
            interesting.items()
        ):

            print(
                f"{caller} -> {callees}"
            )

    print(
        f"\nINTERESTING CALL GRAPH NODES : "
        f"{graph_count}"
    )

    print_section(
        "J) FINAL RUNTIME PATH DECISION"
    )

    producer_found = bool(
        signal_functions
    )

    generator_found = bool(
        generator_functions
    )

    call_site_found = bool(
        generator_calls
    )

    signal_binding = bool(
        signal_input_calls
    )

    direct_boundary = bool(
        direct_signal_generator
    )

    main_signal_path = bool(
        main_signal_paths
    )

    if (
        producer_found
        and generator_found
        and call_site_found
        and signal_binding
        and (
            direct_boundary
            or main_signal_path
        )
    ):

        verdict = (
            "RUNTIME_SIGNAL_TO_GENERATOR_CHAIN_CANDIDATE_RESOLVED"
        )

        reason = (
            "A non-forensic runtime entrypoint/signal path, "
            "signal-related producer, Order-Intent generator "
            "and generator call receiving signal-related input "
            "were statically resolved."
        )

    elif (
        producer_found
        and generator_found
        and call_site_found
        and signal_binding
    ):

        verdict = (
            "SIGNAL_TO_GENERATOR_BOUNDARY_RESOLVED_ENTRYPOINT_UNRESOLVED"
        )

        reason = (
            "The signal producer and Order-Intent generator "
            "boundary is statically visible, but the real "
            "runtime entrypoint-to-producer path is not "
            "resolved sufficiently."
        )

    elif (
        generator_found
        and call_site_found
    ):

        verdict = (
            "GENERATOR_EXISTS_BUT_SIGNAL_RUNTIME_BINDING_UNRESOLVED"
        )

        reason = (
            "Generator definitions and call sites exist, "
            "but a sufficiently resolvable signal input "
            "binding was not established."
        )

    else:

        verdict = (
            "RUNTIME_SIGNAL_TO_GENERATOR_CHAIN_NOT_RESOLVED"
        )

        reason = (
            "The complete static chain "
            "REAL RUNTIME ENTRYPOINT → SIGNAL PRODUCER "
            "→ ORDER-INTENT GENERATOR could not be resolved."
        )

    print(
        f"PRODUCER FOUND       : {producer_found}"
    )

    print(
        f"GENERATOR FOUND      : {generator_found}"
    )

    print(
        f"GENERATOR CALL FOUND : {call_site_found}"
    )

    print(
        f"SIGNAL INPUT BINDING : {signal_binding}"
    )

    print(
        f"DIRECT BOUNDARY      : {direct_boundary}"
    )

    print(
        f"MAIN → SIGNAL PATH   : {main_signal_path}"
    )

    print(
        f"VERDICT              : {verdict}"
    )

    print(
        f"REASON               : {reason}"
    )

    print_section(
        "K) IMPORTANT LIMITATION"
    )

    print(
        "This forensic performs static AST/source inspection only."
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
        "It does NOT generate a signal."
    )

    print(
        "It does NOT generate an order intent."
    )

    print(
        "It does NOT submit an order."
    )

    print(
        "It does NOT modify production source."
    )

    print(
        "It does NOT create or modify artifacts."
    )

    print_section(
        "L) SAFETY ASSERTION"
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

    print("=" * 100)
    print(
        "END — READ ONLY REAL RUNTIME SIGNAL → GENERATOR TRACE"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())