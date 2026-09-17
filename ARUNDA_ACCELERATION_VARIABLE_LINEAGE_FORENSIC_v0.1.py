# -*- coding: utf-8 -*-

import ast
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FIELD = "acceleration"

TARGET_FILES = [
    PROJECT_ROOT / "market_regime.py",
    PROJECT_ROOT / "market_regime_engine.py",
    PROJECT_ROOT / "technical_engine.py",
    PROJECT_ROOT / "signal_engine.py",
    PROJECT_ROOT / "signal_logic.py",
]


def read_source(path: Path):
    return path.read_text(
        encoding="utf-8-sig"
    )


def get_source_segment(source, node):
    return ast.get_source_segment(
        source,
        node,
    )


def constant_value(node):
    if isinstance(node, ast.Constant):
        return node.value

    return None


def is_target_dict_key(node, target):
    return (
        isinstance(node, ast.Constant)
        and node.value == target
    )


def collect_dict_acceleration_sources(
    path,
    tree,
    source,
):
    results = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Dict):
            continue

        for key, value in zip(
            node.keys,
            node.values,
        ):

            if not is_target_dict_key(
                key,
                TARGET_FIELD,
            ):
                continue

            results.append(
                {
                    "file": path.name,
                    "line": node.lineno,
                    "type": "DICT_FIELD",
                    "value_ast": ast.dump(
                        value,
                        indent=2,
                    ),
                    "source": get_source_segment(
                        source,
                        node,
                    ),
                }
            )

    return results


def collect_variable_assignments(
    path,
    tree,
    source,
):
    results = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.NamedExpr,
            ),
        ):

            targets = []

            if isinstance(
                node,
                ast.Assign,
            ):
                targets = node.targets
                value = node.value

            elif isinstance(
                node,
                ast.AnnAssign,
            ):
                targets = [node.target]
                value = node.value

            else:
                targets = [node.target]
                value = node.value

            for target in targets:

                if (
                    isinstance(
                        target,
                        ast.Name,
                    )
                    and target.id == TARGET_FIELD
                ):

                    results.append(
                        {
                            "file": path.name,
                            "function": find_function_name(
                                tree,
                                node.lineno,
                            ),
                            "line": node.lineno,
                            "type": "VARIABLE_ASSIGNMENT",
                            "variable": TARGET_FIELD,
                            "value_ast": ast.dump(
                                value,
                                indent=2,
                            ),
                            "source": get_source_segment(
                                source,
                                node,
                            ),
                        }
                    )

    return results


def collect_subscript_reads(
    path,
    tree,
    source,
):
    results = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Subscript,
        ):
            continue

        if not isinstance(
            node.slice,
            ast.Constant,
        ):
            continue

        if node.slice.value != TARGET_FIELD:
            continue

        results.append(
            {
                "file": path.name,
                "function": find_function_name(
                    tree,
                    node.lineno,
                ),
                "line": node.lineno,
                "type": "FIELD_READ",
                "source": get_source_segment(
                    source,
                    node,
                ),
            }
        )

    return results


def collect_get_reads(
    path,
    tree,
    source,
):
    results = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if not isinstance(
            node.func,
            ast.Attribute,
        ):
            continue

        if node.func.attr != "get":
            continue

        if not node.args:
            continue

        key = node.args[0]

        if not (
            isinstance(
                key,
                ast.Constant,
            )
            and key.value == TARGET_FIELD
        ):
            continue

        container = get_source_segment(
            source,
            node.func.value,
        )

        results.append(
            {
                "file": path.name,
                "function": find_function_name(
                    tree,
                    node.lineno,
                ),
                "line": node.lineno,
                "type": "FIELD_GET",
                "container": container,
                "source": get_source_segment(
                    source,
                    node,
                ),
            }
        )

    return results


def collect_name_references(
    path,
    tree,
    source,
):
    results = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Name,
        ):
            continue

        if node.id != TARGET_FIELD:
            continue

        results.append(
            {
                "file": path.name,
                "function": find_function_name(
                    tree,
                    node.lineno,
                ),
                "line": node.lineno,
                "type": "NAME_REFERENCE",
                "context": type(
                    node.ctx
                ).__name__,
                "source": get_source_segment(
                    source,
                    node,
                ),
            }
        )

    return results


def find_function_name(
    tree,
    lineno,
):
    best = None

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        end_lineno = getattr(
            node,
            "end_lineno",
            node.lineno,
        )

        if (
            node.lineno
            <= lineno
            <= end_lineno
        ):
            if (
                best is None
                or node.lineno > best.lineno
            ):
                best = node

    if best is None:
        return "<module>"

    return best.name


def resolve_name_definition(
    path,
    tree,
    source,
    variable_name,
):
    results = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if (
                    isinstance(
                        target,
                        ast.Name,
                    )
                    and target.id
                    == variable_name
                ):

                    results.append(
                        {
                            "file": path.name,
                            "function": find_function_name(
                                tree,
                                node.lineno,
                            ),
                            "line": node.lineno,
                            "variable": variable_name,
                            "value_ast": ast.dump(
                                node.value,
                                indent=2,
                            ),
                            "source": get_source_segment(
                                source,
                                node,
                            ),
                        }
                    )

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            if (
                isinstance(
                    node.target,
                    ast.Name,
                )
                and node.target.id
                == variable_name
            ):

                results.append(
                    {
                        "file": path.name,
                        "function": find_function_name(
                            tree,
                            node.lineno,
                        ),
                        "line": node.lineno,
                        "variable": variable_name,
                        "value_ast": ast.dump(
                            node.value,
                            indent=2,
                        ),
                        "source": get_source_segment(
                            source,
                            node,
                        ),
                    }
                )

    return results


def print_section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — ACCELERATION VARIABLE LINEAGE FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )
    print(
        f"TARGET FIELD : {TARGET_FIELD}"
    )
    print(
        "MODE         : READ ONLY STATIC SOURCE INSPECTION"
    )
    print(
        "DATABASE     : NONE"
    )
    print(
        "WRITE        : NONE"
    )
    print(
        "SOURCE MUTATION : NONE"
    )
    print(
        "EXECUTION    : NONE"
    )
    print(
        "NETWORK      : NONE"
    )
    print("=" * 100)

    all_results = []

    for path in TARGET_FILES:

        if not path.exists():
            continue

        source = read_source(path)

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError as error:

            print()
            print(
                f"[SYNTAX ERROR] {path.name}"
            )
            print(error)
            continue

        dict_results = (
            collect_dict_acceleration_sources(
                path,
                tree,
                source,
            )
        )

        assignment_results = (
            collect_variable_assignments(
                path,
                tree,
                source,
            )
        )

        get_results = (
            collect_get_reads(
                path,
                tree,
                source,
            )
        )

        subscript_results = (
            collect_subscript_reads(
                path,
                tree,
                source,
            )
        )

        name_results = (
            collect_name_references(
                path,
                tree,
                source,
            )
        )

        if dict_results:

            print_section(
                f"DICT SOURCES — {path.name}"
            )

            for item in dict_results:

                print(
                    f"\nFILE     : {item['file']}"
                )
                print(
                    f"LINE     : {item['line']}"
                )
                print(
                    f"TYPE     : {item['type']}"
                )
                print(
                    "VALUE AST"
                )
                print(
                    item["value_ast"]
                )
                print(
                    "SOURCE"
                )
                print(
                    item["source"]
                )

                all_results.append(item)

        if assignment_results:

            print_section(
                f"VARIABLE ASSIGNMENTS — {path.name}"
            )

            for item in assignment_results:

                print(
                    f"\nFILE     : {item['file']}"
                )
                print(
                    f"FUNCTION : {item['function']}"
                )
                print(
                    f"LINE     : {item['line']}"
                )
                print(
                    f"VARIABLE : {item['variable']}"
                )
                print(
                    "VALUE AST"
                )
                print(
                    item["value_ast"]
                )
                print(
                    "SOURCE"
                )
                print(
                    item["source"]
                )

                all_results.append(item)

        if get_results:

            print_section(
                f"FIELD GET READS — {path.name}"
            )

            for item in get_results:

                print(
                    f"\nFILE      : {item['file']}"
                )
                print(
                    f"FUNCTION  : {item['function']}"
                )
                print(
                    f"LINE      : {item['line']}"
                )
                print(
                    f"CONTAINER : {item['container']}"
                )
                print(
                    "SOURCE"
                )
                print(
                    item["source"]
                )

                all_results.append(item)

        if subscript_results:

            print_section(
                f"FIELD SUBSCRIPT READS — {path.name}"
            )

            for item in subscript_results:

                print(
                    f"\nFILE     : {item['file']}"
                )
                print(
                    f"FUNCTION : {item['function']}"
                )
                print(
                    f"LINE     : {item['line']}"
                )
                print(
                    item["source"]
                )

                all_results.append(item)

        if name_results:

            print_section(
                f"NAME REFERENCES — {path.name}"
            )

            for item in name_results:

                print(
                    f"\nFILE     : {item['file']}"
                )
                print(
                    f"FUNCTION : {item['function']}"
                )
                print(
                    f"LINE     : {item['line']}"
                )
                print(
                    f"CONTEXT  : {item['context']}"
                )
                print(
                    f"SOURCE   : {item['source']}"
                )

                all_results.append(item)

    # ------------------------------------------------------------------
    # SECOND PASS:
    # Resolve variables discovered as the value of acceleration.
    # ------------------------------------------------------------------

    discovered_variables = set()

    for item in all_results:

        if (
            item.get("type")
            == "DICT_FIELD"
        ):

            value_ast = item[
                "value_ast"
            ]

            try:
                node = ast.parse(
                    value_ast,
                    mode="eval",
                ).body
            except Exception:
                continue

            if isinstance(
                node,
                ast.Name,
            ):
                discovered_variables.add(
                    node.id
                )

    if discovered_variables:

        print_section(
            "SECOND PASS — VARIABLE ROOT RESOLUTION"
        )

        print(
            "DISCOVERED VARIABLES:"
        )

        for variable in sorted(
            discovered_variables
        ):
            print(
                f"  - {variable}"
            )

        for path in TARGET_FILES:

            if not path.exists():
                continue

            source = read_source(path)

            try:
                tree = ast.parse(
                    source,
                    filename=str(path),
                )
            except SyntaxError:
                continue

            for variable in sorted(
                discovered_variables
            ):

                definitions = (
                    resolve_name_definition(
                        path,
                        tree,
                        source,
                        variable,
                    )
                )

                for item in definitions:

                    print()
                    print(
                        f"VARIABLE : {variable}"
                    )
                    print(
                        f"FILE     : {item['file']}"
                    )
                    print(
                        f"FUNCTION : {item['function']}"
                    )
                    print(
                        f"LINE     : {item['line']}"
                    )
                    print(
                        "VALUE AST"
                    )
                    print(
                        item["value_ast"]
                    )
                    print(
                        "SOURCE"
                    )
                    print(
                        item["source"]
                    )

    print_section(
        "FINAL FORENSIC DECISION"
    )

    print(
        "ACCELERATION VARIABLE LINEAGE HAS BEEN TRACED "
        "FROM FIELD ACCESS TOWARD SOURCE-LEVEL DEFINITIONS."
    )

    print(
        "NO REPAIR WAS PERFORMED."
    )
    print(
        "NO SYNTHETIC VALUE WAS CREATED."
    )
    print(
        "NO DATABASE WAS ACCESSED."
    )
    print(
        "NO FILE WAS WRITTEN."
    )
    print(
        "NO PRODUCTION SOURCE WAS MODIFIED."
    )

    print()
    print("=" * 100)
    print("END — ACCELERATION VARIABLE LINEAGE FORENSIC v0.1")
    print("=" * 100)


if __name__ == "__main__":
    main()