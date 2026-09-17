# =============================================================================
# ARUNDA TRADER — ACCELERATION CALCULATE_STRUCTURE ROOT FORENSIC v0.3
# =============================================================================
# READ ONLY
# NO DATABASE
# NO WRITE
# NO SOURCE MUTATION
# NO NETWORK
# =============================================================================

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = ROOT / "market_regime_engine.py"


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def print_block(lines, start, end):
    start = max(1, start)
    end = min(len(lines), end)

    for n in range(start, end + 1):
        print(f"{n:5d} | {lines[n - 1]}")


def is_acceleration_key(node):
    return (
        isinstance(node, ast.Constant)
        and node.value == "acceleration"
    )


def contains_acceleration(node):
    for child in ast.walk(node):

        if isinstance(child, ast.Constant):
            if child.value == "acceleration":
                return True

        if isinstance(child, ast.Name):
            if "acceleration" in child.id.lower():
                return True

        if isinstance(child, ast.Attribute):
            if "acceleration" in child.attr.lower():
                return True

    return False


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — ACCELERATION CALCULATE_STRUCTURE ROOT FORENSIC v0.3"
    )
    print("=" * 100)

    print(f"PROJECT ROOT : {ROOT}")
    print(f"TARGET       : {TARGET}")
    print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
    print("DATABASE     : NONE")
    print("WRITE        : NONE")
    print("SOURCE MUTATION : NONE")
    print("NETWORK      : NONE")
    print("=" * 100)

    if not TARGET.exists():
        raise FileNotFoundError(TARGET)

    source = read_source(TARGET)
    lines = source.splitlines()

    tree = ast.parse(
        source,
        filename=str(TARGET),
    )

    calculate_structure = None

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name == "calculate_structure":
                calculate_structure = node
                break

    print()
    print("=" * 100)
    print("STEP 1 — CALCULATE_STRUCTURE DEFINITION")
    print("=" * 100)

    if calculate_structure is None:
        print("CRITICAL: calculate_structure() NOT FOUND")
        return

    print(
        f"FUNCTION : calculate_structure"
    )
    print(
        f"LINE     : {calculate_structure.lineno}"
    )

    end_line = getattr(
        calculate_structure,
        "end_lineno",
        calculate_structure.lineno + 1,
    )

    print()
    print("-" * 100)

    print_block(
        lines,
        calculate_structure.lineno,
        end_line,
    )

    # -------------------------------------------------------------------------
    # STEP 2
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 2 — ACCELERATION REFERENCES INSIDE calculate_structure()")
    print("=" * 100)

    found = False

    for node in ast.walk(calculate_structure):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.NamedExpr,
            ),
        ):

            if contains_acceleration(node):

                found = True

                print("-" * 100)
                print(
                    f"LINE : {getattr(node, 'lineno', '?')}"
                )

                print()
                print("AST")
                print("-" * 100)

                print(
                    ast.dump(
                        node,
                        indent=2,
                    )
                )

                print()
                print("SOURCE")
                print("-" * 100)

                line = getattr(
                    node,
                    "lineno",
                    1,
                )

                end = getattr(
                    node,
                    "end_lineno",
                    line,
                )

                print_block(
                    lines,
                    line,
                    end,
                )

    if not found:
        print(
            "NO ACCELERATION VARIABLE ASSIGNMENT FOUND "
            "INSIDE calculate_structure()."
        )

    # -------------------------------------------------------------------------
    # STEP 3
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 3 — DICTIONARIES RETURNED BY calculate_structure()")
    print("=" * 100)

    dict_found = False

    for node in ast.walk(calculate_structure):

        if not isinstance(node, ast.Dict):
            continue

        acceleration_entries = []

        for key, value in zip(
            node.keys,
            node.values,
        ):

            if is_acceleration_key(key):

                acceleration_entries.append(
                    (
                        key,
                        value,
                    )
                )

        if not acceleration_entries:
            continue

        dict_found = True

        print("-" * 100)

        print(
            f"DICT LINE : {node.lineno}"
        )

        for key, value in acceleration_entries:

            print()
            print("KEY")
            print(
                ast.dump(
                    key,
                    indent=2,
                )
            )

            print()
            print("VALUE")
            print(
                ast.dump(
                    value,
                    indent=2,
                )
            )

            print()
            print("SOURCE")
            print("-" * 100)

            print_block(
                lines,
                node.lineno,
                getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
            )

    if not dict_found:
        print(
            "NO acceleration dictionary entry found "
            "inside calculate_structure()."
        )

    # -------------------------------------------------------------------------
    # STEP 4
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 4 — ALL ACCELERATION-RELATED CALLS")
    print("=" * 100)

    calls_found = False

    for node in ast.walk(calculate_structure):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        name = call_name(node.func)

        if not name:
            continue

        if (
            "acceleration" not in name.lower()
            and not contains_acceleration(node)
        ):
            continue

        calls_found = True

        print("-" * 100)

        print(
            f"CALL     : {name}()"
        )

        print(
            f"LINE     : {node.lineno}"
        )

        print()
        print("CALL AST")
        print("-" * 100)

        print(
            ast.dump(
                node,
                indent=2,
            )
        )

        print()
        print("SOURCE")
        print("-" * 100)

        print_block(
            lines,
            node.lineno,
            getattr(
                node,
                "end_lineno",
                node.lineno,
            ),
        )

    if not calls_found:
        print(
            "NO ACCELERATION-RELATED FUNCTION CALL "
            "FOUND INSIDE calculate_structure()."
        )

    # -------------------------------------------------------------------------
    # STEP 5
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 5 — RETURN AST")
    print("=" * 100)

    for node in ast.walk(calculate_structure):

        if not isinstance(
            node,
            ast.Return,
        ):
            continue

        print()
        print(
            f"RETURN LINE : {node.lineno}"
        )

        print("-" * 100)

        print(
            ast.dump(
                node.value,
                indent=2,
            )
        )

        if contains_acceleration(node.value):

            print()
            print(">>> ACCELERATION IS PRESENT IN RETURN VALUE <<<")

    # -------------------------------------------------------------------------
    # STEP 6
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 6 — LOCAL VARIABLE PRODUCERS")
    print("=" * 100)

    for node in ast.walk(calculate_structure):

        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        target_names = []

        for target in node.targets:

            if isinstance(
                target,
                ast.Name,
            ):
                target_names.append(
                    target.id
                )

        if not target_names:
            continue

        print("-" * 100)
        print(
            f"LINE    : {node.lineno}"
        )
        print(
            f"TARGETS : {target_names}"
        )

        print()
        print("VALUE AST")
        print("-" * 100)

        print(
            ast.dump(
                node.value,
                indent=2,
            )
        )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL FORENSIC DECISION")
    print("=" * 100)

    print(
        """
The lineage has reached:

    market_regime.py
        ->
    build_market_regime()
        ->
    structural_state
        ->
    market_regime_engine.py
        ->
    build_structural_state()
        ->
    calculate_structure(asset, bars)

This forensic step inspects calculate_structure() itself.

The next valid repair point can only be selected after determining
whether acceleration is:

    1. genuinely calculated here,
    2. returned from another genuine producer,
    3. supplied by an existing structural source,
    4. or genuinely absent.

NO SYNTHETIC ACCELERATION IS CREATED.
NO DATABASE IS ACCESSED.
NO FILE IS WRITTEN.
NO SOURCE IS MODIFIED.
"""
    )

    print("=" * 100)
    print("SAFETY ASSERTION")
    print("=" * 100)

    print("DATABASE ACCESS : False")
    print("DATABASE WRITE  : False")
    print("FILE WRITE      : False")
    print("NETWORK         : False")
    print("SOURCE MUTATION : False")

    print("=" * 100)


if __name__ == "__main__":
    main()