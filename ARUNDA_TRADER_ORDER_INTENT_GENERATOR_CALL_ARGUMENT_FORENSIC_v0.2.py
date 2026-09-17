from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

REPLAY_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_REPORT.json"
)

DRY_RUN_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_DRY_RUN_REPORT.json"
)

ROW_IDS = {37, 38, 39, 40}

GENERATOR_KEYWORDS = (
    "order_intent",
    "order_intents",
    "generate_order",
    "generator",
)

EXCLUDED_SOURCE_TOKENS = (
    "FORENSIC",
    "FORENSIC_v0.1",
    "FORENSIC_v0.2",
    "AUDIT",
)

SIGNAL_TOKENS = (
    "row_results",
    "eligible_signal",
    "eligible_signals",
    "signal",
    "signals",
    "artifact",
    "order_intent",
    "order_intents",
)


def source_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


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
            getattr(
                node,
                "lineno",
                0,
            ),
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
        lines[
            start - 1:end
        ]
    )


def dotted_name(
    node: ast.AST | None,
) -> str | None:

    if isinstance(
        node,
        ast.Name,
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute,
    ):
        parent = dotted_name(
            node.value
        )

        if parent:
            return (
                f"{parent}.{node.attr}"
            )

        return node.attr

    return None


def contains_keyword(
    value: str,
) -> bool:

    lowered = value.lower()

    return any(
        keyword in lowered
        for keyword in GENERATOR_KEYWORDS
    )


def expression_contains_signal_token(
    node: ast.AST,
) -> bool:

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ):
            if any(
                token in child.id.lower()
                for token in SIGNAL_TOKENS
            ):
                return True

        if isinstance(
            child,
            ast.Attribute,
        ):
            if any(
                token in child.attr.lower()
                for token in SIGNAL_TOKENS
            ):
                return True

        if isinstance(
            child,
            ast.Constant,
        ):
            if isinstance(
                child.value,
                str,
            ):
                lowered = child.value.lower()

                if any(
                    token in lowered
                    for token in SIGNAL_TOKENS
                ):
                    return True

    return False


def extract_constant_ids(
    node: ast.AST,
) -> set[int]:

    found: set[int] = set()

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Constant,
        ):

            value = child.value

            if (
                isinstance(value, int)
                and value in ROW_IDS
            ):
                found.add(value)

    return found


def describe_expression(
    node: ast.AST,
) -> str:

    name = dotted_name(node)

    if name:
        return name

    if isinstance(
        node,
        ast.Constant,
    ):
        return repr(
            node.value
        )

    if isinstance(
        node,
        ast.List,
    ):
        return (
            f"LIST[{len(node.elts)}]"
        )

    if isinstance(
        node,
        ast.Tuple,
    ):
        return (
            f"TUPLE[{len(node.elts)}]"
        )

    if isinstance(
        node,
        ast.Dict,
    ):
        return (
            f"DICT[{len(node.keys)}]"
        )

    if isinstance(
        node,
        ast.Call,
    ):

        callee = dotted_name(
            node.func
        )

        if callee:
            return (
                f"{callee}(...)"
            )

        return "CALL(...)"

    if isinstance(
        node,
        ast.Subscript,
    ):

        base = describe_expression(
            node.value
        )

        return (
            f"{base}[...]"
        )

    return ast.dump(
        node,
        include_attributes=False,
    )


def assignment_target_names(
    target: ast.AST,
) -> list[str]:

    names: list[str] = []

    if isinstance(
        target,
        ast.Name,
    ):
        names.append(
            target.id
        )

    elif isinstance(
        target,
        (
            ast.Tuple,
            ast.List,
        ),
    ):

        for element in target.elts:
            names.extend(
                assignment_target_names(
                    element
                )
            )

    return names


def build_assignment_index(
    tree: ast.AST,
    text: str,
) -> dict[str, list[dict[str, Any]]]:

    index: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Assign,
        ):

            names: list[str] = []

            for target in node.targets:
                names.extend(
                    assignment_target_names(
                        target
                    )
                )

            for name in names:

                index.setdefault(
                    name,
                    [],
                ).append(
                    {
                        "line": line_of(node),
                        "end_line": end_line_of(node),
                        "expression": describe_expression(
                            node.value
                        ),
                        "source": node_source(
                            text,
                            node,
                        ),
                        "signal_related": expression_contains_signal_token(
                            node.value
                        ),
                        "constant_ids": sorted(
                            extract_constant_ids(
                                node.value
                            )
                        ),
                    }
                )

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            if not isinstance(
                node.target,
                ast.Name,
            ):
                continue

            name = node.target.id

            if node.value is None:
                continue

            index.setdefault(
                name,
                [],
            ).append(
                {
                    "line": line_of(node),
                    "end_line": end_line_of(node),
                    "expression": describe_expression(
                        node.value
                    ),
                    "source": node_source(
                        text,
                        node,
                    ),
                    "signal_related": expression_contains_signal_token(
                        node.value
                    ),
                    "constant_ids": sorted(
                        extract_constant_ids(
                            node.value
                        )
                    ),
                }
            )

    return index


def trace_name(
    name: str,
    assignments: dict[
        str,
        list[dict[str, Any]],
    ],
    visited: set[str] | None = None,
) -> dict[str, Any]:

    if visited is None:
        visited = set()

    if name in visited:
        return {
            "name": name,
            "cycle": True,
            "assignments": [],
            "signal_related": False,
            "constant_ids": [],
        }

    visited.add(name)

    records = assignments.get(
        name,
        [],
    )

    result = {
        "name": name,
        "cycle": False,
        "assignments": records,
        "signal_related": False,
        "constant_ids": set(),
        "linked_names": set(),
    }

    for record in records:

        if record.get(
            "signal_related"
        ):
            result[
                "signal_related"
            ] = True

        for value in record.get(
            "constant_ids",
            [],
        ):
            result[
                "constant_ids"
            ].add(value)

        expression = record.get(
            "expression",
            "",
        )

        try:
            expression_tree = ast.parse(
                expression,
                mode="eval",
            ).body
        except Exception:
            expression_tree = None

        if expression_tree is None:
            continue

        for child in ast.walk(
            expression_tree
        ):

            if isinstance(
                child,
                ast.Name,
            ):

                linked = child.id

                if linked == name:
                    continue

                result[
                    "linked_names"
                ].add(linked)

                nested = trace_name(
                    linked,
                    assignments,
                    visited.copy(),
                )

                if nested.get(
                    "signal_related"
                ):
                    result[
                        "signal_related"
                    ] = True

                result[
                    "constant_ids"
                ].update(
                    nested.get(
                        "constant_ids",
                        set(),
                    )
                )

    return result


def trace_expression(
    node: ast.AST,
    assignments: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Any]:

    direct_ids = extract_constant_ids(
        node
    )

    names: set[str] = set()

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ):
            names.add(
                child.id
            )

    signal_related = (
        expression_contains_signal_token(
            node
        )
    )

    resolved_ids = set(
        direct_ids
    )

    traces: list[
        dict[str, Any]
    ] = []

    for name in sorted(
        names
    ):

        trace = trace_name(
            name,
            assignments,
        )

        traces.append(
            trace
        )

        if trace.get(
            "signal_related"
        ):
            signal_related = True

        resolved_ids.update(
            trace.get(
                "constant_ids",
                set(),
            )
        )

    return {
        "signal_related": signal_related,
        "constant_ids": sorted(
            resolved_ids
        ),
        "names": sorted(names),
        "traces": traces,
    }


def function_contains_target_rows(
    node: ast.AST,
) -> bool:

    return bool(
        extract_constant_ids(node)
    )


def analyze_python_file(
    path: Path,
) -> dict[str, Any]:

    text = source_text(
        path
    )

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError as exc:

        return {
            "path": str(path),
            "parse_error": str(exc),
            "definitions": [],
            "calls": [],
            "assignments": {},
        }

    assignments = build_assignment_index(
        tree,
        text,
    )

    definitions: list[
        dict[str, Any]
    ] = []

    calls: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            function_blob = node_source(
                text,
                node,
            )

            if (
                contains_keyword(
                    node.name
                )
                or contains_keyword(
                    function_blob
                )
            ):

                definitions.append(
                    {
                        "name": node.name,
                        "line": line_of(node),
                        "end_line": end_line_of(node),
                        "source": function_blob,
                        "target_rows": sorted(
                            extract_constant_ids(
                                node
                            )
                        ),
                    }
                )

        elif isinstance(
            node,
            ast.Call,
        ):

            callee = dotted_name(
                node.func
            )

            if not callee:
                continue

            call_blob = node_source(
                text,
                node,
            )

            if not (
                contains_keyword(
                    callee
                )
                or contains_keyword(
                    call_blob
                )
            ):
                continue

            positional: list[
                dict[str, Any]
            ] = []

            for index, arg in enumerate(
                node.args
            ):

                trace = trace_expression(
                    arg,
                    assignments,
                )

                positional.append(
                    {
                        "index": index,
                        "expression": describe_expression(
                            arg
                        ),
                        "trace": trace,
                    }
                )

            keyword_args: list[
                dict[str, Any]
            ] = []

            for kw in node.keywords:

                trace = trace_expression(
                    kw.value,
                    assignments,
                )

                keyword_args.append(
                    {
                        "name": kw.arg or "**",
                        "expression": describe_expression(
                            kw.value
                        ),
                        "trace": trace,
                    }
                )

            direct_ids = extract_constant_ids(
                node
            )

            resolved_ids = set(
                direct_ids
            )

            signal_related = (
                expression_contains_signal_token(
                    node
                )
            )

            for argument in positional:
                trace = argument[
                    "trace"
                ]

                resolved_ids.update(
                    trace.get(
                        "constant_ids",
                        [],
                    )
                )

                if trace.get(
                    "signal_related"
                ):
                    signal_related = True

            for argument in keyword_args:
                trace = argument[
                    "trace"
                ]

                resolved_ids.update(
                    trace.get(
                        "constant_ids",
                        [],
                    )
                )

                if trace.get(
                    "signal_related"
                ):
                    signal_related = True

            calls.append(
                {
                    "callee": callee,
                    "line": line_of(node),
                    "end_line": end_line_of(node),
                    "positional": positional,
                    "keyword_args": keyword_args,
                    "direct_ids": sorted(
                        direct_ids
                    ),
                    "resolved_ids": sorted(
                        resolved_ids
                    ),
                    "signal_related": signal_related,
                    "source": call_blob,
                }
            )

    return {
        "path": str(path),
        "parse_error": None,
        "definitions": definitions,
        "calls": calls,
        "assignments": assignments,
    }


def print_section(
    title: str,
) -> None:

    print(
        "=" * 100
    )

    print(title)

    print(
        "=" * 100
    )


def print_trace(
    trace: dict[str, Any],
    indent: str = "      ",
    depth: int = 0,
) -> None:

    if depth > 3:
        print(
            indent
            + "... trace depth limit ..."
        )
        return

    print(
        indent
        + "signal_related : "
        + str(
            trace.get(
                "signal_related",
                False,
            )
        )
    )

    print(
        indent
        + "constant_ids   : "
        + str(
            trace.get(
                "constant_ids",
                [],
            )
        )
    )

    names = trace.get(
        "names",
        [],
    )

    if names:
        print(
            indent
            + "names          : "
            + str(names)
        )

    for nested in trace.get(
        "traces",
        [],
    ):

        print(
            indent
            + "TRACE NAME     : "
            + str(
                nested.get(
                    "name"
                )
            )
        )

        print(
            indent
            + "TRACE SIGNAL   : "
            + str(
                nested.get(
                    "signal_related",
                    False,
                )
            )
        )

        print(
            indent
            + "TRACE IDS      : "
            + str(
                sorted(
                    nested.get(
                        "constant_ids",
                        set(),
                    )
                )
            )
        )


def main() -> int:

    print(
        "=" * 100
    )

    print(
        "ARUNDA TRADER — ORDER-INTENT GENERATOR "
        "CALL ARGUMENT FORENSIC v0.2"
    )

    print(
        "=" * 100
    )

    print(
        f"PROJECT ROOT       : {PROJECT_ROOT}"
    )

    print(
        "MODE               : READ ONLY"
    )

    print(
        "PYTHON EXECUTION   : NONE"
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
        "=" * 100
    )

    if not PROJECT_ROOT.exists():

        print(
            "ERROR: PROJECT ROOT NOT FOUND"
        )

        return 1

    print_section(
        "A) REAL DRY-RUN ROW FIXTURE"
    )

    print(
        "SOURCE : "
        f"{DRY_RUN_REPORT}"
    )

    print(
        "TARGET ROW IDS : "
        f"{sorted(ROW_IDS)}"
    )

    print(
        "NOTE : IDs are used only as "
        "previously observed real-row references."
    )

    print_section(
        "B) TARGET ARTIFACT PRESENCE"
    )

    for path in (
        REPLAY_REPORT,
        DRY_RUN_REPORT,
    ):

        print(
            f"{path.name} : "
            f"{'FOUND' if path.exists() else 'NOT FOUND'}"
        )

    print_section(
        "C) PYTHON PRODUCER DISCOVERY"
    )

    python_files = sorted(
        PROJECT_ROOT.rglob("*.py")
    )

    source_candidates: list[
        Path
    ] = []

    for path in python_files:

        upper_name = path.name.upper()

        if any(
            token in upper_name
            for token in EXCLUDED_SOURCE_TOKENS
        ):
            continue

        source_candidates.append(
            path
        )

    print(
        "PYTHON FILES DISCOVERED : "
        f"{len(python_files)}"
    )

    print(
        "SOURCE CANDIDATES       : "
        f"{len(source_candidates)}"
    )

    analyzed: list[
        dict[str, Any]
    ] = []

    parse_errors: list[
        dict[str, str]
    ] = []

    for path in source_candidates:

        try:

            result = analyze_python_file(
                path
            )

            analyzed.append(
                result
            )

            if result.get(
                "parse_error"
            ):

                parse_errors.append(
                    {
                        "path": str(path),
                        "error": str(
                            result[
                                "parse_error"
                            ]
                        ),
                    }
                )

        except Exception as exc:

            parse_errors.append(
                {
                    "path": str(path),
                    "error": str(exc),
                }
            )

    print(
        "FILES ANALYZED : "
        f"{len(analyzed)}"
    )

    print(
        "PARSE ERRORS   : "
        f"{len(parse_errors)}"
    )

    if parse_errors:

        for item in parse_errors:

            print(
                "\nPARSE ERROR FILE : "
                f"{item['path']}"
            )

            print(
                "ERROR : "
                f"{item['error']}"
            )

    print_section(
        "D) ORDER-INTENT GENERATOR DEFINITIONS"
    )

    definitions_found = 0

    generator_names: set[str] = set()

    for result in analyzed:

        for definition in result[
            "definitions"
        ]:

            definitions_found += 1

            generator_names.add(
                definition[
                    "name"
                ]
            )

            print(
                "\nFILE : "
                f"{result['path']}"
            )

            print(
                "FUNCTION : "
                f"{definition['name']}"
            )

            print(
                "LINES : "
                f"{definition['line']}-"
                f"{definition['end_line']}"
            )

            print(
                "CONSTANT TARGET IDS : "
                f"{definition['target_rows']}"
            )

    print(
        "\nGENERATOR-LIKE DEFINITIONS : "
        f"{definitions_found}"
    )

    print(
        "GENERATOR NAMES : "
        f"{sorted(generator_names)}"
    )

    print_section(
        "E) GENERATOR CALL SITES"
    )

    all_calls: list[
        tuple[
            dict[str, Any],
            dict[str, Any],
        ]
    ] = []

    for result in analyzed:

        for call in result[
            "calls"
        ]:

            all_calls.append(
                (
                    result,
                    call,
                )
            )

            print(
                "\nFILE : "
                f"{result['path']}"
            )

            print(
                "CALLEE : "
                f"{call['callee']}"
            )

            print(
                "LINES : "
                f"{call['line']}-"
                f"{call['end_line']}"
            )

            print(
                "DIRECT CONSTANT IDS : "
                f"{call['direct_ids']}"
            )

            print(
                "RESOLVED IDS : "
                f"{call['resolved_ids']}"
            )

            print(
                "SIGNAL RELATED : "
                f"{call['signal_related']}"
            )

            if call[
                "positional"
            ]:

                print(
                    "POSITIONAL ARGUMENTS:"
                )

                for argument in call[
                    "positional"
                ]:

                    print(
                        "  positional["
                        f"{argument['index']}"
                        "] = "
                        f"{argument['expression']}"
                    )

                    print_trace(
                        argument[
                            "trace"
                        ],
                        indent="      ",
                    )

            if call[
                "keyword_args"
            ]:

                print(
                    "KEYWORD ARGUMENTS:"
                )

                for argument in call[
                    "keyword_args"
                ]:

                    print(
                        "  keyword["
                        f"{argument['name']}"
                        "] = "
                        f"{argument['expression']}"
                    )

                    print_trace(
                        argument[
                            "trace"
                        ],
                        indent="      ",
                    )

            print(
                "SOURCE:"
            )

            print(
                call[
                    "source"
                ]
            )

    print(
        "\nGENERATOR-LIKE CALL SITES : "
        f"{len(all_calls)}"
    )

    print_section(
        "F) TARGET ROW → GENERATOR ARGUMENT BINDING"
    )

    target_binding_calls: list[
        tuple[
            dict[str, Any],
            dict[str, Any],
            set[int],
        ]
    ] = []

    signal_binding_calls: list[
        tuple[
            dict[str, Any],
            dict[str, Any],
        ]
    ] = []

    for result, call in all_calls:

        resolved_ids = set(
            call[
                "resolved_ids"
            ]
        )

        if resolved_ids & ROW_IDS:

            target_binding_calls.append(
                (
                    result,
                    call,
                    resolved_ids & ROW_IDS,
                )
            )

        if call[
            "signal_related"
        ]:

            signal_binding_calls.append(
                (
                    result,
                    call,
                )
            )

    print(
        "CALL SITES WITH TARGET ROW BINDING : "
        f"{len(target_binding_calls)}"
    )

    for (
        result,
        call,
        matched,
    ) in target_binding_calls:

        print(
            "\nTARGET-BINDING FILE : "
            f"{result['path']}"
        )

        print(
            "CALLEE : "
            f"{call['callee']}"
        )

        print(
            "LINE : "
            f"{call['line']}"
        )

        print(
            "MATCHED ROW IDS : "
            f"{sorted(matched)}"
        )

        print(
            "SOURCE:"
        )

        print(
            call[
                "source"
            ]
        )

    print(
        "\nSIGNAL-RELATED CALL SITES : "
        f"{len(signal_binding_calls)}"
    )

    for (
        result,
        call,
    ) in signal_binding_calls:

        print(
            "\nSIGNAL-RELATED FILE : "
            f"{result['path']}"
        )

        print(
            "CALLEE : "
            f"{call['callee']}"
        )

        print(
            "LINE : "
            f"{call['line']}"
        )

        print(
            "RESOLVED IDS : "
            f"{call['resolved_ids']}"
        )

    print_section(
        "G) EXACT PRODUCER → INPUT TRACE DECISION"
    )

    producer_found = (
        definitions_found > 0
    )

    call_site_found = (
        len(all_calls) > 0
    )

    target_binding_found = (
        len(target_binding_calls) > 0
    )

    signal_binding_found = (
        len(signal_binding_calls) > 0
    )

    if not producer_found:

        verdict = (
            "GENERATOR_PRODUCER_NOT_FOUND"
        )

        reason = (
            "No real Order-Intent Generator-like "
            "definition was found in non-forensic "
            "project source."
        )

    elif not call_site_found:

        verdict = (
            "GENERATOR_CALL_SITE_NOT_FOUND"
        )

        reason = (
            "Generator-like definitions exist, "
            "but no generator-like call site was found."
        )

    elif target_binding_found:

        verdict = (
            "TARGET_ROWS_REACH_GENERATOR_CALL_ARGUMENT"
        )

        reason = (
            "Static AST/data-flow tracing resolves "
            "one or more target row IDs 37-40 into "
            "a generator-like call argument."
        )

    elif signal_binding_found:

        verdict = (
            "SIGNAL_INPUT_REACHES_GENERATOR_CALL"
        )

        reason = (
            "A generator-like call receives an argument "
            "statically related to signal/artifact data, "
            "but the specific target row IDs 37-40 "
            "cannot be resolved through static binding."
        )

    else:

        verdict = (
            "NO_TARGET_SIGNAL_BINDING_TO_GENERATOR"
        )

        reason = (
            "Generator call sites exist, but static "
            "analysis found no binding from signal/artifact "
            "data or target rows 37-40 into those calls."
        )

    print(
        f"PRODUCER FOUND      : {producer_found}"
    )

    print(
        f"CALL SITE FOUND     : {call_site_found}"
    )

    print(
        f"TARGET ROW BINDING  : {target_binding_found}"
    )

    print(
        f"SIGNAL BINDING      : {signal_binding_found}"
    )

    print(
        f"VERDICT             : {verdict}"
    )

    print(
        f"REASON              : {reason}"
    )

    print_section(
        "H) IMPORTANT LIMITATION"
    )

    print(
        "This forensic performs static AST/data-flow "
        "inspection only."
    )

    print(
        "It does NOT execute Python."
    )

    print(
        "It does NOT inspect runtime memory."
    )

    print(
        "It does NOT inspect the database."
    )

    print(
        "It does NOT generate an eligible signal."
    )

    print(
        "It does NOT generate an order intent."
    )

    print(
        "A positive static binding means the source code "
        "contains a resolvable producer-to-input path; "
        "it does not claim that the path executed at runtime."
    )

    print_section(
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

    print(
        "=" * 100
    )

    print(
        "END — READ ONLY ORDER-INTENT "
        "GENERATOR CALL ARGUMENT FORENSIC v0.2"
    )

    print(
        "=" * 100
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )