from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SIGNAL_KEYWORDS = (
    "signal",
    "eligible",
    "fusion",
    "process_signals",
    "create_signal",
)

GENERATOR_KEYWORDS = (
    "order_intent",
    "order_intents",
    "generate_order",
)


def source_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def line_of(node: ast.AST) -> int:
    return int(getattr(node, "lineno", 0))


def end_line_of(node: ast.AST) -> int:
    return int(
        getattr(
            node,
            "end_lineno",
            getattr(node, "lineno", 0),
        )
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


def node_source(text: str, node: ast.AST) -> str:
    lines = text.splitlines()

    start = line_of(node)
    end = end_line_of(node)

    if start <= 0:
        return ""

    return "\n".join(lines[start - 1:end])


def keyword_match(value: str, keywords: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in keywords)


def function_contains_keyword(
    text: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    keywords: tuple[str, ...],
) -> bool:
    name = node.name.lower()

    if keyword_match(name, keywords):
        return True

    body = node_source(text, node).lower()

    return keyword_match(body, keywords)


def analyze_file(path: Path) -> dict[str, Any]:
    text = source_text(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError as exc:
        return {
            "path": str(path),
            "parse_error": str(exc),
            "functions": [],
            "calls": [],
        }

    functions: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            if (
                function_contains_keyword(
                    text,
                    node,
                    SIGNAL_KEYWORDS,
                )
                or function_contains_keyword(
                    text,
                    node,
                    GENERATOR_KEYWORDS,
                )
            ):
                functions.append(
                    {
                        "name": node.name,
                        "line": line_of(node),
                        "end_line": end_line_of(node),
                        "source": node_source(
                            text,
                            node,
                        ),
                    }
                )

        elif isinstance(node, ast.Call):

            callee = dotted_name(node.func)

            if not callee:
                continue

            blob = node_source(text, node)

            if (
                keyword_match(
                    callee,
                    SIGNAL_KEYWORDS,
                )
                or keyword_match(
                    callee,
                    GENERATOR_KEYWORDS,
                )
                or keyword_match(
                    blob,
                    SIGNAL_KEYWORDS,
                )
                or keyword_match(
                    blob,
                    GENERATOR_KEYWORDS,
                )
            ):
                calls.append(
                    {
                        "callee": callee,
                        "line": line_of(node),
                        "end_line": end_line_of(node),
                        "source": blob,
                    }
                )

    return {
        "path": str(path),
        "parse_error": None,
        "functions": functions,
        "calls": calls,
    }


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — RUNTIME PRODUCER ENTRYPOINT "
        "FORENSIC v0.1"
    )
    print("=" * 100)
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ ONLY")
    print("PYTHON EXECUTION : NONE")
    print("DATABASE ACCESS  : NONE")
    print("WRITE            : NONE")
    print("ARTIFACT CREATION : NONE")
    print("NETWORK ACCESS   : NONE")
    print("=" * 100)

    if not PROJECT_ROOT.exists():
        print("ERROR: PROJECT ROOT NOT FOUND")
        return 1

    python_files = sorted(
        path
        for path in PROJECT_ROOT.rglob("*.py")
        if ".venv" not in path.parts
        and "__pycache__" not in path.parts
        and "_QUARANTINE" not in path.parts
    )

    print_section("A) PYTHON SOURCE DISCOVERY")

    print(
        f"PYTHON FILES DISCOVERED : {len(python_files)}"
    )

    results: list[dict[str, Any]] = []
    parse_errors = []

    for path in python_files:

        try:
            result = analyze_file(path)
            results.append(result)

            if result["parse_error"]:
                parse_errors.append(result)

        except Exception as exc:
            parse_errors.append(
                {
                    "path": str(path),
                    "parse_error": str(exc),
                    "functions": [],
                    "calls": [],
                }
            )

    print(
        f"FILES ANALYZED : {len(results)}"
    )

    print(
        f"PARSE ERRORS   : {len(parse_errors)}"
    )

    print_section(
        "B) CANDIDATE RUNTIME PRODUCER FUNCTIONS"
    )

    producer_functions = []

    for result in results:

        for function in result["functions"]:

            name = function["name"].lower()
            source = function["source"].lower()

            if keyword_match(
                name,
                SIGNAL_KEYWORDS,
            ):
                producer_functions.append(
                    (
                        result["path"],
                        function,
                    )
                )

            elif (
                "eligible" in source
                and "signal" in source
            ):
                producer_functions.append(
                    (
                        result["path"],
                        function,
                    )
                )

    for path, function in producer_functions:

        print()
        print(f"FILE     : {path}")
        print(f"FUNCTION : {function['name']}")
        print(
            f"LINES    : "
            f"{function['line']}-"
            f"{function['end_line']}"
        )

    print(
        f"\nPRODUCER CANDIDATES : "
        f"{len(producer_functions)}"
    )

    print_section(
        "C) MAIN / RUNTIME ENTRYPOINT CANDIDATES"
    )

    entrypoints = []

    for result in results:

        text = source_text(
            Path(result["path"])
        )

        if "if __name__" in text:

            entrypoints.append(
                result["path"]
            )

    for path in entrypoints:
        print(f"ENTRYPOINT : {path}")

    print(
        f"\nMAIN ENTRYPOINT FILES : "
        f"{len(entrypoints)}"
    )

    print_section(
        "D) SIGNAL → GENERATOR CALL BOUNDARY"
    )

    boundary_calls = []

    for result in results:

        for call in result["calls"]:

            source = call["source"].lower()

            has_signal = (
                "signal" in source
                or "eligible" in source
                or "fusion" in source
            )

            has_generator = (
                "order_intent" in source
                or "order-intents" in source
                or "generate_order" in source
            )

            if has_signal and has_generator:
                boundary_calls.append(
                    (
                        result["path"],
                        call,
                    )
                )

    for path, call in boundary_calls:

        print()
        print(f"FILE  : {path}")
        print(f"CALL  : {call['callee']}")
        print(
            f"LINES : "
            f"{call['line']}-"
            f"{call['end_line']}"
        )
        print("SOURCE:")
        print(call["source"])

    print(
        f"\nSIGNAL → GENERATOR BOUNDARY CANDIDATES : "
        f"{len(boundary_calls)}"
    )

    print_section(
        "E) EXACT PRODUCER → GENERATOR PATH DECISION"
    )

    producer_found = bool(producer_functions)
    entrypoint_found = bool(entrypoints)
    boundary_found = bool(boundary_calls)

    if (
        producer_found
        and entrypoint_found
        and boundary_found
    ):
        verdict = (
            "RUNTIME_PRODUCER_TO_GENERATOR_PATH_CANDIDATE_FOUND"
        )
        reason = (
            "A runtime entrypoint, signal-related producer "
            "function, and signal-to-order-intent boundary "
            "candidate were found."
        )

    elif producer_found and entrypoint_found:
        verdict = (
            "PRODUCER_AND_ENTRYPOINT_FOUND_BOUNDARY_REVIEW_REQUIRED"
        )
        reason = (
            "Producer and runtime entrypoint candidates exist, "
            "but the exact producer-to-generator call boundary "
            "was not statically resolved."
        )

    elif producer_found:
        verdict = (
            "PRODUCER_FOUND_RUNTIME_ENTRYPOINT_REVIEW_REQUIRED"
        )
        reason = (
            "Signal producer candidates exist, but a concrete "
            "runtime entrypoint was not resolved."
        )

    else:
        verdict = (
            "RUNTIME_PRODUCER_NOT_RESOLVED"
        )
        reason = (
            "No sufficiently strong runtime signal producer "
            "candidate was resolved by static inspection."
        )

    print(
        f"PRODUCER FOUND      : {producer_found}"
    )
    print(
        f"ENTRYPOINT FOUND    : {entrypoint_found}"
    )
    print(
        f"BOUNDARY FOUND      : {boundary_found}"
    )
    print(
        f"VERDICT             : {verdict}"
    )
    print(
        f"REASON              : {reason}"
    )

    print_section(
        "F) IMPORTANT LIMITATION"
    )

    print(
        "This forensic performs static AST/source inspection only."
    )
    print(
        "It does NOT execute Python."
    )
    print(
        "It does NOT access the database."
    )
    print(
        "It does NOT modify production source."
    )
    print(
        "It does NOT generate a signal."
    )
    print(
        "It does NOT generate an order intent."
    )
    print(
        "It does NOT claim runtime execution occurred."
    )

    print_section(
        "G) SAFETY ASSERTION"
    )

    print("PYTHON EXECUTION   : False")
    print("DATABASE READ      : False")
    print("DATABASE WRITE     : False")
    print("JSON WRITE         : False")
    print("ARTIFACT CREATION  : False")
    print("ORDER CREATION     : False")
    print("ORDER SUBMISSION   : False")
    print("NETWORK ACCESS     : False")
    print("ARTIFACT MUTATION  : False")

    print("=" * 100)
    print(
        "END — READ ONLY RUNTIME PRODUCER ENTRYPOINT FORENSIC v0.1"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())