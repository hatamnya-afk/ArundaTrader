# ARUNDA_SIGNAL_ENGINE_RUNTIME_ERROR_BOUNDARY_FORENSIC_v0.1.py
# READ-ONLY STATIC FORENSIC
#
# Purpose:
#   Resolve the exact source boundary associated with:
#       RuntimeError("Invalid structural fields")
#
# Safety:
#   - No Python execution of production modules
#   - No database access
#   - No network access
#   - No JSON writes
#   - No artifact creation
#   - No source mutation
#   - No signal generation
#   - No order generation

from __future__ import annotations

import ast
import os
import re
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_FILE = PROJECT_ROOT / "signal_engine.py"

ERROR_TEXT = "Invalid structural fields"

FORENSIC_NAME = (
    "ARUNDA SIGNAL ENGINE RUNTIME ERROR BOUNDARY FORENSIC v0.1"
)


def line_text(lines, lineno):
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].rstrip()
    return ""


def source_window(lines, lineno, radius=4):
    start = max(1, lineno - radius)
    end = min(len(lines), lineno + radius)

    result = []

    for number in range(start, end + 1):
        result.append(
            f"{number:>6}: {line_text(lines, number)}"
        )

    return "\n".join(result)


def get_call_name(node):
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


def is_target_error_node(node):
    if not isinstance(node, ast.Call):
        return False

    if not (
        isinstance(node.func, ast.Name)
        and node.func.id == "RuntimeError"
    ):
        return False

    for arg in node.args:
        if isinstance(arg, ast.Constant):
            if isinstance(arg.value, str):
                if ERROR_TEXT.lower() in arg.value.lower():
                    return True

    return False


def collect_parent_map(tree):
    parents = {}

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    return parents


def enclosing_function(node, parents):
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


def collect_raises(tree, parents):
    matches = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue

        exc = node.exc

        if is_target_error_node(exc):
            function = enclosing_function(node, parents)

            matches.append(
                {
                    "line": getattr(node, "lineno", None),
                    "column": getattr(node, "col_offset", None),
                    "function": (
                        function.name
                        if function is not None
                        else None
                    ),
                    "error": ERROR_TEXT,
                    "kind": "RAISE_RUNTIME_ERROR",
                }
            )

    return matches


def collect_error_string_occurrences(tree):
    matches = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue

        if not isinstance(node.value, str):
            continue

        if ERROR_TEXT.lower() not in node.value.lower():
            continue

        function = None

        # Function ownership is resolved later through parent map.

        matches.append(
            {
                "line": getattr(node, "lineno", None),
                "column": getattr(node, "col_offset", None),
                "kind": "ERROR_STRING",
                "function": function,
                "value": node.value,
            }
        )

    return matches


def collect_structural_field_references(tree, parents):
    structural_terms = (
        "structural",
        "fields",
        "field",
        "structure",
    )

    matches = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Name):
            continue

        name = node.id.lower()

        if not any(term in name for term in structural_terms):
            continue

        function = enclosing_function(node, parents)

        matches.append(
            {
                "line": getattr(node, "lineno", None),
                "column": getattr(node, "col_offset", None),
                "name": node.id,
                "function": (
                    function.name
                    if function is not None
                    else None
                ),
            }
        )

    return matches


def collect_validation_like_calls(tree, parents):
    keywords = (
        "validate",
        "validation",
        "contract",
        "structure",
        "structural",
        "signal",
        "regime",
    )

    matches = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = get_call_name(node.func)

        if not name:
            continue

        lname = name.lower()

        if not any(keyword in lname for keyword in keywords):
            continue

        function = enclosing_function(node, parents)

        matches.append(
            {
                "line": getattr(node, "lineno", None),
                "column": getattr(node, "col_offset", None),
                "call": name,
                "function": (
                    function.name
                    if function is not None
                    else None
                ),
            }
        )

    return matches


def collect_control_flow(tree, parents):
    matches = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.If,
                ast.Assert,
                ast.Raise,
            ),
        ):
            continue

        source = ast.unparse(node)

        if "structural" not in source.lower():
            continue

        function = enclosing_function(node, parents)

        matches.append(
            {
                "line": getattr(node, "lineno", None),
                "kind": type(node).__name__,
                "function": (
                    function.name
                    if function is not None
                    else None
                ),
                "source": source[:500],
            }
        )

    return matches


def inspect_file():

    if not PROJECT_ROOT.exists():
        print(
            f"PROJECT ROOT NOT FOUND : {PROJECT_ROOT}"
        )
        return 2

    if not TARGET_FILE.exists():
        print(
            f"TARGET FILE NOT FOUND : {TARGET_FILE}"
        )
        return 3

    try:
        raw = TARGET_FILE.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        raw = TARGET_FILE.read_text(
            encoding="utf-8-sig"
        )

    lines = raw.splitlines()

    try:
        tree = ast.parse(
            raw,
            filename=str(TARGET_FILE),
        )
    except SyntaxError as exc:
        print(
            "\n"
            + "=" * 100
        )
        print("AST PARSE FAILURE")
        print("=" * 100)
        print(f"LINE   : {exc.lineno}")
        print(f"COLUMN : {exc.offset}")
        print(f"ERROR  : {exc.msg}")
        print("=" * 100)
        return 4

    parents = collect_parent_map(tree)

    raise_matches = collect_raises(
        tree,
        parents,
    )

    string_matches = collect_error_string_occurrences(
        tree
    )

    for item in string_matches:
        node = None

        for candidate in ast.walk(tree):
            if (
                isinstance(candidate, ast.Constant)
                and isinstance(candidate.value, str)
                and getattr(candidate, "lineno", None)
                == item["line"]
                and getattr(candidate, "col_offset", None)
                == item["column"]
            ):
                node = candidate
                break

        if node is not None:
            function = enclosing_function(
                node,
                parents,
            )

            item["function"] = (
                function.name
                if function is not None
                else None
            )

    structural_refs = collect_structural_field_references(
        tree,
        parents,
    )

    validation_calls = collect_validation_like_calls(
        tree,
        parents,
    )

    control_flow = collect_control_flow(
        tree,
        parents,
    )

    print()
    print("=" * 100)
    print(f"ARUNDA SIGNAL ENGINE — {FORENSIC_NAME}")
    print("=" * 100)

    print(f"PROJECT ROOT       : {PROJECT_ROOT}")
    print(f"TARGET FILE        : {TARGET_FILE}")
    print("MODE               : READ ONLY")
    print("PRODUCTION EXECUTE : NONE")
    print("DATABASE ACCESS    : NONE")
    print("DATABASE WRITE     : NONE")
    print("JSON WRITE         : NONE")
    print("ARTIFACT CREATION  : NONE")
    print("NETWORK ACCESS     : NONE")
    print("=" * 100)

    print()
    print("A) TARGET ERROR")
    print("=" * 100)
    print(f'ERROR TARGET       : RuntimeError("{ERROR_TEXT}")')
    print(
        f"EXACT RAISES FOUND : {len(raise_matches)}"
    )
    print(
        f"ERROR STRING HITS  : {len(string_matches)}"
    )

    print()
    print("B) EXACT RAISE BOUNDARY")
    print("=" * 100)

    if raise_matches:
        for index, match in enumerate(
            raise_matches,
            start=1,
        ):
            print()
            print(f"MATCH #{index}")
            print(
                f"FUNCTION : {match['function']}"
            )
            print(
                f"LINE     : {match['line']}"
            )
            print(
                f"COLUMN   : {match['column']}"
            )
            print(
                f"KIND     : {match['kind']}"
            )

            print()
            print("SOURCE WINDOW")
            print("-" * 100)

            print(
                source_window(
                    lines,
                    match["line"],
                    radius=6,
                )
            )

    else:
        print(
            "NO DIRECT RuntimeError RAISE "
            "WITH TARGET TEXT FOUND."
        )

    print()
    print("C) ERROR STRING OWNERSHIP")
    print("=" * 100)

    if string_matches:
        for index, match in enumerate(
            string_matches,
            start=1,
        ):
            print()
            print(f"MATCH #{index}")
            print(
                f"LINE     : {match['line']}"
            )
            print(
                f"COLUMN   : {match['column']}"
            )
            print(
                f"FUNCTION : {match['function']}"
            )
            print(
                f"VALUE    : {match['value']!r}"
            )
    else:
        print("NONE")

    print()
    print("D) STRUCTURAL FIELD REFERENCES")
    print("=" * 100)

    print(
        f"REFERENCES FOUND : {len(structural_refs)}"
    )

    for item in structural_refs[:100]:
        print(
            f"LINE={item['line']} "
            f"NAME={item['name']} "
            f"FUNCTION={item['function']}"
        )

    if len(structural_refs) > 100:
        print(
            f"... {len(structural_refs) - 100} "
            "additional references omitted"
        )

    print()
    print("E) VALIDATION / CONTRACT / SIGNAL CALLS")
    print("=" * 100)

    print(
        f"CALL CANDIDATES : {len(validation_calls)}"
    )

    for item in validation_calls[:100]:
        print(
            f"LINE={item['line']} "
            f"CALL={item['call']} "
            f"FUNCTION={item['function']}"
        )

    if len(validation_calls) > 100:
        print(
            f"... {len(validation_calls) - 100} "
            "additional calls omitted"
        )

    print()
    print("F) STRUCTURAL CONTROL-FLOW REFERENCES")
    print("=" * 100)

    print(
        f"CONTROL-FLOW CANDIDATES : {len(control_flow)}"
    )

    for item in control_flow[:100]:
        print()
        print(
            f"LINE     : {item['line']}"
        )
        print(
            f"KIND     : {item['kind']}"
        )
        print(
            f"FUNCTION : {item['function']}"
        )
        print(
            f"SOURCE   : {item['source']}"
        )

    if len(control_flow) > 100:
        print(
            f"... {len(control_flow) - 100} "
            "additional control-flow candidates omitted"
        )

    print()
    print("G) FINAL RUNTIME ERROR BOUNDARY DECISION")
    print("=" * 100)

    if len(raise_matches) == 1:
        match = raise_matches[0]

        print("EXACT ERROR RAISE FOUND : True")
        print(
            f"ERROR FUNCTION          : "
            f"{match['function']}"
        )
        print(
            f"ERROR LINE              : "
            f"{match['line']}"
        )
        print(
            "VERDICT                 : "
            "EXACT_RUNTIME_ERROR_BOUNDARY_RESOLVED"
        )
        print(
            "REASON                  : "
            "The exact RuntimeError raise site containing "
            '"Invalid structural fields" was statically '
            "resolved inside signal_engine.py."
        )

    elif len(raise_matches) > 1:

        print("EXACT ERROR RAISE FOUND : True")
        print(
            f"MULTIPLE RAISE SITES   : "
            f"{len(raise_matches)}"
        )
        print(
            "VERDICT                 : "
            "MULTIPLE_ERROR_BOUNDARIES_REQUIRE_DISAMBIGUATION"
        )

    else:

        print("EXACT ERROR RAISE FOUND : False")
        print(
            "VERDICT                 : "
            "ERROR_BOUNDARY_NOT_RESOLVED"
        )
        print(
            "REASON                  : "
            "The target RuntimeError text was not found "
            "as a direct RuntimeError raise in signal_engine.py."
        )

    print()
    print("H) IMPORTANT LIMITATION")
    print("=" * 100)
    print(
        "This forensic performs STATIC AST/source inspection only."
    )
    print(
        "It does NOT execute signal_engine.py."
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
        "It does NOT generate a signal."
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
    print("PYTHON PRODUCTION EXECUTION : False")
    print("DATABASE READ               : False")
    print("DATABASE WRITE              : False")
    print("JSON WRITE                  : False")
    print("ARTIFACT CREATION           : False")
    print("SIGNAL CREATION             : False")
    print("ORDER CREATION              : False")
    print("ORDER SUBMISSION            : False")
    print("NETWORK ACCESS              : False")
    print("SOURCE MUTATION             : False")

    print("=" * 100)
    print(
        "END — READ ONLY SIGNAL ENGINE "
        "RUNTIME ERROR BOUNDARY FORENSIC v0.1"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        inspect_file()
    )