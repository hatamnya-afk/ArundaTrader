# ARUNDA_SIGNAL_ENGINE_RUNTIME_ERROR_ORIGIN_FORENSIC_v0.1.py
#
# READ-ONLY STATIC FORENSIC
#
# PURPOSE:
#   Resolve the source origin of the runtime error:
#
#       RuntimeError: Invalid structural fields
#
#   The previous forensic proved that the exact text does NOT exist
#   inside signal_engine.py.
#
#   This forensic therefore searches the production source tree and
#   resolves:
#
#       ERROR TEXT
#          ↓
#       EXACT FILE
#          ↓
#       FUNCTION
#          ↓
#       LINE
#          ↓
#       CALLER / CALLEE RELATION
#          ↓
#       STRUCTURAL / SIGNAL PATH
#
# SAFETY:
#   - No production Python execution
#   - No database access
#   - No network
#   - No JSON write
#   - No artifact creation
#   - No source mutation
#   - No signal generation
#   - No order generation

from __future__ import annotations

import ast
import os
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_MODULES = {
    "signal_engine.py",
    "signal_logic.py",
    "signal_contract.py",
    "market_regime.py",
    "market_regime_contract.py",
}

ERROR_TERMS = (
    "invalid structural fields",
    "structural fields",
)

RUNTIME_ERROR_TERMS = (
    "RuntimeError",
    "ValueError",
    "TypeError",
    "KeyError",
    "AssertionError",
)


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}


def safe_read(path: Path) -> str | None:
    try:
        return path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        try:
            return path.read_text(
                encoding="utf-8-sig"
            )
        except Exception:
            return None
    except Exception:
        return None


def function_owner(
    node: ast.AST,
    parents: dict[int, ast.AST],
):
    current = node

    while id(current) in parents:
        current = parents[id(current)]

        if isinstance(
            current,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            return current

    return None


def build_parent_map(tree):
    parents = {}

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    return parents


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return None


def source_window(lines, line, radius=5):
    if not line:
        return ""

    start = max(1, line - radius)
    end = min(len(lines), line + radius)

    output = []

    for number in range(start, end + 1):
        output.append(
            f"{number:>6}: {lines[number - 1].rstrip()}"
        )

    return "\n".join(output)


def discover_python_files():
    files = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            path = Path(root) / filename

            files.append(path)

    return sorted(files)


def inspect_file(path: Path):
    source = safe_read(path)

    if source is None:
        return None

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        return {
            "path": path,
            "syntax_error": {
                "line": exc.lineno,
                "column": exc.offset,
                "message": exc.msg,
            },
            "matches": [],
            "calls": [],
        }

    parents = build_parent_map(tree)

    lines = source.splitlines()

    matches = []
    calls = []

    for node in ast.walk(tree):

        # ------------------------------------------------------------
        # String constants containing structural-error terminology
        # ------------------------------------------------------------

        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):

                value = node.value.lower()

                if any(
                    term in value
                    for term in ERROR_TERMS
                ):
                    owner = function_owner(
                        node,
                        parents,
                    )

                    matches.append(
                        {
                            "kind": "STRING",
                            "line": getattr(
                                node,
                                "lineno",
                                None,
                            ),
                            "column": getattr(
                                node,
                                "col_offset",
                                None,
                            ),
                            "function": (
                                owner.name
                                if owner
                                else None
                            ),
                            "value": node.value,
                            "source": source_window(
                                lines,
                                getattr(
                                    node,
                                    "lineno",
                                    None,
                                ),
                            ),
                        }
                    )

        # ------------------------------------------------------------
        # Exception constructors
        # ------------------------------------------------------------

        if isinstance(node, ast.Call):

            name = call_name(node.func)

            if name in RUNTIME_ERROR_TERMS:

                text_parts = []

                for arg in node.args:
                    if isinstance(
                        arg,
                        ast.Constant,
                    ):
                        if isinstance(
                            arg.value,
                            str,
                        ):
                            text_parts.append(
                                arg.value
                            )

                combined = " ".join(
                    text_parts
                ).lower()

                if (
                    "structural" in combined
                    or "fields" in combined
                ):
                    owner = function_owner(
                        node,
                        parents,
                    )

                    calls.append(
                        {
                            "kind": (
                                "EXCEPTION_CONSTRUCTOR"
                            ),
                            "line": getattr(
                                node,
                                "lineno",
                                None,
                            ),
                            "column": getattr(
                                node,
                                "col_offset",
                                None,
                            ),
                            "exception": name,
                            "function": (
                                owner.name
                                if owner
                                else None
                            ),
                            "message": combined,
                            "source": source_window(
                                lines,
                                getattr(
                                    node,
                                    "lineno",
                                    None,
                                ),
                            ),
                        }
                    )

    # ------------------------------------------------------------
    # All calls involving structural/signal/contract path
    # ------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        name = call_name(node.func)

        if not name:
            continue

        lname = name.lower()

        if not any(
            term in lname
            for term in (
                "struct",
                "regime",
                "signal",
                "contract",
                "direction",
                "validate",
                "build",
                "load",
            )
        ):
            continue

        owner = function_owner(
            node,
            parents,
        )

        calls.append(
            {
                "kind": "PATH_CALL",
                "line": getattr(
                    node,
                    "lineno",
                    None,
                ),
                "column": getattr(
                    node,
                    "col_offset",
                    None,
                ),
                "call": name,
                "function": (
                    owner.name
                    if owner
                    else None
                ),
            }
        )

    return {
        "path": path,
        "syntax_error": None,
        "matches": matches,
        "calls": calls,
    }


def resolve_module_imports(path: Path):
    source = safe_read(path)

    if source is None:
        return []

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError:
        return []

    imports = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                imports.append(
                    {
                        "type": "import",
                        "module": alias.name,
                        "line": node.lineno,
                    }
                )

        elif isinstance(node, ast.ImportFrom):

            module = node.module or ""

            imports.append(
                {
                    "type": "from",
                    "module": module,
                    "line": node.lineno,
                }
            )

    return imports


def main():

    print()
    print("=" * 100)
    print(
        "ARUNDA SIGNAL ENGINE — "
        "RUNTIME ERROR ORIGIN FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT       : {PROJECT_ROOT}"
    )
    print(
        "MODE               : READ ONLY"
    )
    print(
        "PRODUCTION EXECUTE : NONE"
    )
    print(
        "DATABASE ACCESS    : NONE"
    )
    print(
        "DATABASE WRITE     : NONE"
    )
    print(
        "JSON WRITE         : NONE"
    )
    print(
        "ARTIFACT CREATION  : NONE"
    )
    print(
        "NETWORK ACCESS     : NONE"
    )

    print("=" * 100)

    print()
    print("A) ERROR TARGET")
    print("=" * 100)

    print(
        'TARGET ERROR : RuntimeError("Invalid structural fields")'
    )

    print()
    print("B) PYTHON SOURCE DISCOVERY")
    print("=" * 100)

    files = discover_python_files()

    print(
        f"PYTHON FILES DISCOVERED : {len(files)}"
    )

    results = []

    for path in files:
        result = inspect_file(path)

        if result is not None:
            results.append(result)

    print(
        f"FILES PARSED            : "
        f"{sum(1 for r in results if not r['syntax_error'])}"
    )

    syntax_failures = [
        r
        for r in results
        if r["syntax_error"]
    ]

    print(
        f"SYNTAX FAILURES         : "
        f"{len(syntax_failures)}"
    )

    if syntax_failures:

        print()
        print("SYNTAX FAILURES")
        print("-" * 100)

        for item in syntax_failures:
            print(
                f"{item['path']} : "
                f"{item['syntax_error']}"
            )

    # ------------------------------------------------------------
    # Exact target matches
    # ------------------------------------------------------------

    all_matches = []

    for result in results:

        for match in result["matches"]:

            all_matches.append(
                {
                    "path": result["path"],
                    **match,
                }
            )

        for match in result["calls"]:

            if (
                match["kind"]
                == "EXCEPTION_CONSTRUCTOR"
            ):
                all_matches.append(
                    {
                        "path": result["path"],
                        **match,
                    }
                )

    exact_text_matches = [
        m
        for m in all_matches
        if (
            m.get("kind") == "STRING"
            and (
                "invalid structural fields"
                in m.get(
                    "value",
                    "",
                ).lower()
            )
        )
    ]

    structural_matches = [
        m
        for m in all_matches
        if (
            "structural"
            in str(m).lower()
            or "fields"
            in str(m).lower()
        )
    ]

    print()
    print("C) EXACT ERROR ORIGIN SEARCH")
    print("=" * 100)

    print(
        f'EXACT "Invalid structural fields" '
        f"MATCHES : {len(exact_text_matches)}"
    )

    if exact_text_matches:

        for index, match in enumerate(
            exact_text_matches,
            start=1,
        ):
            print()
            print(
                f"MATCH #{index}"
            )
            print(
                f"FILE     : {match['path']}"
            )
            print(
                f"FUNCTION : {match.get('function')}"
            )
            print(
                f"LINE     : {match.get('line')}"
            )
            print(
                f"KIND     : {match.get('kind')}"
            )
            print(
                f"VALUE    : {match.get('value')}"
            )
            print()
            print(
                match.get(
                    "source",
                    "",
                )
            )

    else:

        print(
            "NO EXACT ERROR TEXT FOUND "
            "IN PYTHON SOURCE."
        )

    print()
    print("D) STRUCTURAL ERROR CANDIDATES")
    print("=" * 100)

    print(
        f"CANDIDATES : {len(structural_matches)}"
    )

    for index, match in enumerate(
        structural_matches[:200],
        start=1,
    ):

        print()
        print(
            f"MATCH #{index}"
        )
        print(
            f"FILE     : {match['path']}"
        )
        print(
            f"FUNCTION : {match.get('function')}"
        )
        print(
            f"LINE     : {match.get('line')}"
        )
        print(
            f"KIND     : {match.get('kind')}"
        )

        if match.get("exception"):
            print(
                f"EXCEPTION: {match['exception']}"
            )

        if match.get("value"):
            print(
                f"VALUE    : {match['value']}"
            )

        if match.get("message"):
            print(
                f"MESSAGE  : {match['message']}"
            )

    # ------------------------------------------------------------
    # Target production modules
    # ------------------------------------------------------------

    print()
    print("E) TARGET PRODUCTION MODULE IMPORT GRAPH")
    print("=" * 100)

    target_paths = [
        PROJECT_ROOT / name
        for name in TARGET_MODULES
    ]

    for path in target_paths:

        if not path.exists():
            continue

        imports = resolve_module_imports(
            path
        )

        relevant = [
            item
            for item in imports
            if any(
                term in item["module"].lower()
                for term in (
                    "signal",
                    "struct",
                    "regime",
                    "contract",
                )
            )
        ]

        print()
        print(
            f"FILE : {path}"
        )

        if not relevant:
            print(
                "  RELEVANT IMPORTS : NONE"
            )
            continue

        for item in relevant:
            print(
                f"  LINE={item['line']} "
                f"{item['type']} "
                f"{item['module']}"
            )

    # ------------------------------------------------------------
    # signal_engine focused path
    # ------------------------------------------------------------

    signal_engine_result = next(
        (
            r
            for r in results
            if r["path"].name
            == "signal_engine.py"
        ),
        None,
    )

    print()
    print("F) SIGNAL_ENGINE STRUCTURAL PATH")
    print("=" * 100)

    if signal_engine_result:

        calls = [
            c
            for c in signal_engine_result["calls"]
            if c["kind"]
            == "PATH_CALL"
        ]

        for item in sorted(
            calls,
            key=lambda x: (
                x.get("line") or 0
            ),
        ):
            print(
                f"LINE={item['line']} "
                f"FUNCTION={item['function']} "
                f"CALL={item['call']}"
            )

    else:

        print(
            "signal_engine.py NOT FOUND."
        )

    # ------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------

    print()
    print("G) FINAL ERROR ORIGIN DECISION")
    print("=" * 100)

    if exact_text_matches:

        first = exact_text_matches[0]

        print(
            "VERDICT : "
            "EXACT_RUNTIME_ERROR_ORIGIN_RESOLVED"
        )
        print(
            f"FILE     : {first['path']}"
        )
        print(
            f"FUNCTION : {first.get('function')}"
        )
        print(
            f"LINE     : {first.get('line')}"
        )
        print(
            "REASON   : "
            "The exact runtime error text "
            '"Invalid structural fields" '
            "was found in Python source."
        )

    elif structural_matches:

        print(
            "VERDICT : "
            "STRUCTURAL_ERROR_CANDIDATE_FOUND"
        )
        print(
            "REASON   : "
            "Structural/field-related exception "
            "or validation code exists, but the "
            "exact runtime message was not found."
        )

    else:

        print(
            "VERDICT : "
            "RUNTIME_ERROR_ORIGIN_NOT_FOUND_IN_SOURCE"
        )
        print(
            "REASON   : "
            "The exact runtime error text and "
            "structural exception candidates were "
            "not found in the scanned Python source."
        )

    print()
    print("H) IMPORTANT LIMITATION")
    print("=" * 100)

    print(
        "This forensic performs STATIC SOURCE/AST inspection only."
    )
    print(
        "It does NOT execute signal_engine.py."
    )
    print(
        "It does NOT execute dependencies."
    )
    print(
        "It does NOT inspect runtime memory."
    )
    print(
        "It does NOT inspect the database."
    )
    print(
        "It does NOT reproduce the runtime failure."
    )
    print(
        "It does NOT generate an eligible signal."
    )
    print(
        "It does NOT generate an order intent."
    )
    print(
        "It does NOT modify production source."
    )

    print()
    print("I) SAFETY ASSERTION")
    print("=" * 100)

    print(
        "PYTHON PRODUCTION EXECUTION : False"
    )
    print(
        "DATABASE READ               : False"
    )
    print(
        "DATABASE WRITE              : False"
    )
    print(
        "JSON WRITE                  : False"
    )
    print(
        "ARTIFACT CREATION           : False"
    )
    print(
        "SIGNAL CREATION             : False"
    )
    print(
        "ORDER CREATION              : False"
    )
    print(
        "ORDER SUBMISSION            : False"
    )
    print(
        "NETWORK ACCESS              : False"
    )
    print(
        "SOURCE MUTATION             : False"
    )

    print("=" * 100)
    print(
        "END — READ ONLY SIGNAL ENGINE "
        "RUNTIME ERROR ORIGIN FORENSIC v0.1"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )