from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_IDS = {37, 38, 39, 40}

GENERATOR_TOKENS = (
    "order_intent",
    "order_intents",
    "generate_order",
    "generator",
)

SIGNAL_TOKENS = (
    "eligible_signal",
    "eligible_signals",
    "signal",
    "signals",
    "row_results",
    "artifact",
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


def dotted_name(
    node: ast.AST,
) -> str | None:

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parent = dotted_name(
            node.value
        )

        if parent:
            return (
                f"{parent}.{node.attr}"
            )

        return node.attr

    return None


def contains_token(
    text: str,
    tokens: tuple[str, ...],
) -> bool:

    lowered = text.lower()

    return any(
        token in lowered
        for token in tokens
    )


def assigned_names(
    node: ast.AST,
) -> set[str]:

    names: set[str] = set()

    if isinstance(node, ast.Name):
        names.add(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):

        for element in node.elts:
            names.update(
                assigned_names(element)
            )

    return names


def expression_names(
    node: ast.AST,
) -> set[str]:

    names: set[str] = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            names.add(child.id)

    return names


def constant_target_ids(
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
                and value in TARGET_IDS
            ):
                found.add(value)

    return found


def argument_description(
    node: ast.AST,
) -> str:

    name = dotted_name(node)

    if name:
        return name

    if isinstance(
        node,
        ast.Constant,
    ):
        return repr(node.value)

    if isinstance(
        node,
        ast.List,
    ):
        return (
            f"LIST[{len(node.elts)}]"
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
            return f"{callee}(...)"

        return "CALL(...)"

    return "<expression>"


def find_generator_definitions(
    tree: ast.AST,
    text: str,
) -> list[dict[str, Any]]:

    results: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        blob = node_source(
            text,
            node,
        )

        if (
            contains_token(
                node.name,
                GENERATOR_TOKENS,
            )
            or contains_token(
                blob,
                GENERATOR_TOKENS,
            )
        ):

            results.append(
                {
                    "name": node.name,
                    "line": line_of(node),
                    "end_line": end_line_of(node),
                    "source": blob,
                    "arguments": [
                        arg.arg
                        for arg in node.args.args
                    ],
                }
            )

    return results


def find_generator_calls(
    tree: ast.AST,
    text: str,
) -> list[dict[str, Any]]:

    results: list[
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

        blob = node_source(
            text,
            node,
        )

        if not (
            contains_token(
                callee,
                GENERATOR_TOKENS,
            )
            or contains_token(
                blob,
                GENERATOR_TOKENS,
            )
        ):
            continue

        positional = [
            {
                "description":
                    argument_description(arg),
                "names":
                    sorted(
                        expression_names(arg)
                    ),
                "target_ids":
                    sorted(
                        constant_target_ids(arg)
                    ),
                "source":
                    node_source(
                        text,
                        arg,
                    ).strip(),
            }
            for arg in node.args
        ]

        keywords = []

        for kw in node.keywords:

            keywords.append(
                {
                    "name": kw.arg or "**",
                    "description":
                        argument_description(
                            kw.value
                        ),
                    "names":
                        sorted(
                            expression_names(
                                kw.value
                            )
                        ),
                    "target_ids":
                        sorted(
                            constant_target_ids(
                                kw.value
                            )
                        ),
                    "source":
                        node_source(
                            text,
                            kw.value,
                        ).strip(),
                }
            )

        results.append(
            {
                "callee": callee,
                "line": line_of(node),
                "end_line": end_line_of(node),
                "source": blob,
                "positional": positional,
                "keywords": keywords,
            }
        )

    return results


def find_signal_assignments(
    tree: ast.AST,
    text: str,
) -> list[dict[str, Any]]:

    results: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        value_blob = node_source(
            text,
            node.value,
        )

        if not contains_token(
            value_blob,
            SIGNAL_TOKENS,
        ):
            continue

        names: set[str] = set()

        for target in node.targets:
            names.update(
                assigned_names(target)
            )

        if not names:
            continue

        results.append(
            {
                "line": line_of(node),
                "end_line": end_line_of(node),
                "names": sorted(names),
                "value_names": sorted(
                    expression_names(
                        node.value
                    )
                ),
                "target_ids": sorted(
                    constant_target_ids(
                        node.value
                    )
                ),
                "source": node_source(
                    text,
                    node,
                ),
            }
        )

    return results


def find_return_paths(
    tree: ast.AST,
    text: str,
) -> list[dict[str, Any]]:

    results: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Return,
        ):
            continue

        blob = node_source(
            text,
            node,
        )

        if not contains_token(
            blob,
            SIGNAL_TOKENS,
        ):
            continue

        results.append(
            {
                "line": line_of(node),
                "source": blob,
                "names": sorted(
                    expression_names(
                        node.value
                    )
                )
                if node.value
                else [],
            }
        )

    return results


def analyze_file(
    path: Path,
) -> dict[str, Any]:

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
            "definitions": [],
            "calls": [],
            "assignments": [],
            "returns": [],
        }

    return {
        "path": str(path),
        "parse_error": None,
        "definitions":
            find_generator_definitions(
                tree,
                text,
            ),
        "calls":
            find_generator_calls(
                tree,
                text,
            ),
        "assignments":
            find_signal_assignments(
                tree,
                text,
            ),
        "returns":
            find_return_paths(
                tree,
                text,
            ),
    }


def classify_argument(
    argument: dict[str, Any],
    known_signal_names: set[str],
) -> str:

    names = set(
        argument["names"]
    )

    target_ids = set(
        argument["target_ids"]
    )

    if target_ids & TARGET_IDS:
        return "DIRECT_TARGET_ROW_REFERENCE"

    if names & known_signal_names:
        return "SIGNAL_VARIABLE_BINDING"

    description = (
        argument["description"]
        .lower()
    )

    if "eligible_signal" in description:
        return "ELIGIBLE_SIGNAL_EXPRESSION"

    if "row_results" in description:
        return "ROW_RESULTS_EXPRESSION"

    if "artifact" in description:
        return "ARTIFACT_EXPRESSION"

    if "signal" in description:
        return "SIGNAL_EXPRESSION"

    return "UNRESOLVED_ARGUMENT"


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — ORDER-INTENT "
        "GENERATOR CALL BOUNDARY FORENSIC v0.3"
    )
    print("=" * 100)

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

    print("=" * 100)

    if not PROJECT_ROOT.exists():

        print(
            "ERROR: PROJECT ROOT NOT FOUND"
        )

        return 1

    python_files = sorted(
        PROJECT_ROOT.rglob("*.py")
    )

    print(
        f"PYTHON FILES DISCOVERED : "
        f"{len(python_files)}"
    )

    analyses: list[
        dict[str, Any]
    ] = []

    parse_errors: list[
        dict[str, str]
    ] = []

    for path in python_files:

        result = analyze_file(
            path
        )

        analyses.append(
            result
        )

        if result["parse_error"]:

            parse_errors.append(
                {
                    "path": result["path"],
                    "error": result[
                        "parse_error"
                    ],
                }
            )

    print(
        f"FILES ANALYZED : "
        f"{len(analyses)}"
    )

    print(
        f"PARSE ERRORS   : "
        f"{len(parse_errors)}"
    )

    print("=" * 100)
    print(
        "A) GENERATOR PRODUCER DEFINITIONS"
    )
    print("=" * 100)

    definitions: list[
        tuple[str, dict[str, Any]]
    ] = []

    for result in analyses:

        for definition in result[
            "definitions"
        ]:

            definitions.append(
                (
                    result["path"],
                    definition,
                )
            )

            print(
                f"\nFILE : {result['path']}"
            )

            print(
                f"FUNCTION : "
                f"{definition['name']}"
            )

            print(
                f"LINES : "
                f"{definition['line']}-"
                f"{definition['end_line']}"
            )

            print(
                f"PARAMETERS : "
                f"{definition['arguments']}"
            )

    print(
        f"\nPRODUCER DEFINITIONS : "
        f"{len(definitions)}"
    )

    print("=" * 100)
    print(
        "B) SIGNAL VARIABLE / ARTIFACT ASSIGNMENT DISCOVERY"
    )
    print("=" * 100)

    signal_names: set[str] = set()

    for result in analyses:

        for assignment in result[
            "assignments"
        ]:

            signal_names.update(
                assignment["names"]
            )

            print(
                f"\nFILE : {result['path']}"
            )

            print(
                f"LINES : "
                f"{assignment['line']}-"
                f"{assignment['end_line']}"
            )

            print(
                f"ASSIGNED NAMES : "
                f"{assignment['names']}"
            )

            print(
                f"VALUE NAMES : "
                f"{assignment['value_names']}"
            )

            print(
                "SOURCE:"
            )

            print(
                assignment["source"]
            )

    print(
        f"\nKNOWN SIGNAL/ARTIFACT VARIABLES : "
        f"{sorted(signal_names)}"
    )

    print("=" * 100)
    print(
        "C) GENERATOR CALL BOUNDARIES"
    )
    print("=" * 100)

    calls: list[
        tuple[str, dict[str, Any]]
    ] = []

    for result in analyses:

        for call in result["calls"]:

            calls.append(
                (
                    result["path"],
                    call,
                )
            )

            print(
                f"\nFILE : {result['path']}"
            )

            print(
                f"CALL : "
                f"{call['callee']}"
            )

            print(
                f"LINES : "
                f"{call['line']}-"
                f"{call['end_line']}"
            )

            print(
                "SOURCE:"
            )

            print(
                call["source"]
            )

            if call["positional"]:

                print(
                    "POSITIONAL ARGUMENTS:"
                )

                for index, argument in enumerate(
                    call["positional"]
                ):

                    classification = (
                        classify_argument(
                            argument,
                            signal_names,
                        )
                    )

                    print(
                        f"  positional[{index}]"
                        f" = "
                        f"{argument['description']}"
                    )

                    print(
                        f"    NAMES      : "
                        f"{argument['names']}"
                    )

                    print(
                        f"    TARGET IDS : "
                        f"{argument['target_ids']}"
                    )

                    print(
                        f"    CLASS      : "
                        f"{classification}"
                    )

            if call["keywords"]:

                print(
                    "KEYWORD ARGUMENTS:"
                )

                for argument in call[
                    "keywords"
                ]:

                    classification = (
                        classify_argument(
                            argument,
                            signal_names,
                        )
                    )

                    print(
                        f"  keyword[{argument['name']}]"
                        f" = "
                        f"{argument['description']}"
                    )

                    print(
                        f"    NAMES      : "
                        f"{argument['names']}"
                    )

                    print(
                        f"    TARGET IDS : "
                        f"{argument['target_ids']}"
                    )

                    print(
                        f"    CLASS      : "
                        f"{classification}"
                    )

    print(
        f"\nGENERATOR CALL SITES : "
        f"{len(calls)}"
    )

    print("=" * 100)
    print(
        "D) EXACT PRODUCER → INPUT CLASSIFICATION"
    )
    print("=" * 100)

    signal_bound_calls = 0
    row_result_calls = 0
    artifact_calls = 0
    unresolved_calls = 0
    direct_target_calls = 0

    for path, call in calls:

        classifications: list[str] = []

        all_arguments = (
            list(call["positional"])
            + list(call["keywords"])
        )

        for argument in all_arguments:

            classification = (
                classify_argument(
                    argument,
                    signal_names,
                )
            )

            classifications.append(
                classification
            )

        print(
            f"\nFILE : {path}"
        )

        print(
            f"CALL : {call['callee']}"
        )

        print(
            f"LINE : {call['line']}"
        )

        print(
            f"CLASSIFICATIONS : "
            f"{classifications}"
        )

        if (
            "DIRECT_TARGET_ROW_REFERENCE"
            in classifications
        ):

            direct_target_calls += 1

        if (
            "SIGNAL_VARIABLE_BINDING"
            in classifications
            or
            "ELIGIBLE_SIGNAL_EXPRESSION"
            in classifications
            or
            "SIGNAL_EXPRESSION"
            in classifications
        ):

            signal_bound_calls += 1

        if (
            "ROW_RESULTS_EXPRESSION"
            in classifications
        ):

            row_result_calls += 1

        if (
            "ARTIFACT_EXPRESSION"
            in classifications
        ):

            artifact_calls += 1

        if all(
            classification
            == "UNRESOLVED_ARGUMENT"
            for classification in classifications
        ):

            unresolved_calls += 1

    print(
        f"\nSIGNAL-BOUND CALLS : "
        f"{signal_bound_calls}"
    )

    print(
        f"ROW_RESULTS CALLS : "
        f"{row_result_calls}"
    )

    print(
        f"ARTIFACT CALLS : "
        f"{artifact_calls}"
    )

    print(
        f"DIRECT TARGET-ID CALLS : "
        f"{direct_target_calls}"
    )

    print(
        f"UNRESOLVED CALLS : "
        f"{unresolved_calls}"
    )

    print("=" * 100)
    print(
        "E) FINAL CALL BOUNDARY DECISION"
    )
    print("=" * 100)

    if not definitions:

        verdict = (
            "GENERATOR_PRODUCER_NOT_FOUND"
        )

        reason = (
            "No generator-like producer "
            "definition was found."
        )

    elif not calls:

        verdict = (
            "GENERATOR_CALL_SITE_NOT_FOUND"
        )

        reason = (
            "Producer definition exists, "
            "but no generator call boundary "
            "was statically identified."
        )

    elif direct_target_calls > 0:

        verdict = (
            "TARGET_ROWS_DIRECTLY_BOUND_TO_GENERATOR"
        )

        reason = (
            "The generator call contains a "
            "direct reference to one or more "
            "target row IDs 37-40."
        )

    elif signal_bound_calls > 0:

        verdict = (
            "ELIGIBLE_SIGNAL_PATH_REACHES_GENERATOR"
        )

        reason = (
            "The generator call receives an "
            "argument statically bound to signal/"
            "eligible-signal data. Target row IDs "
            "are not directly embedded, which is "
            "expected for runtime-produced rows."
        )

    elif row_result_calls > 0:

        verdict = (
            "ROW_RESULTS_REACH_GENERATOR_BOUNDARY"
        )

        reason = (
            "The generator call receives row-results "
            "data rather than a statically resolved "
            "eligible-signal variable. This requires "
            "checking the filtering boundary before "
            "the generator."
        )

    elif artifact_calls > 0:

        verdict = (
            "ARTIFACT_REACHES_GENERATOR_BOUNDARY"
        )

        reason = (
            "The generator call receives artifact-level "
            "data. The exact eligible-signal filtering "
            "boundary is not statically resolved."
        )

    else:

        verdict = (
            "GENERATOR_INPUT_BINDING_UNRESOLVED"
        )

        reason = (
            "A generator call exists, but its input "
            "cannot be statically classified as an "
            "eligible-signal path."
        )

    print(
        f"PRODUCER FOUND      : "
        f"{bool(definitions)}"
    )

    print(
        f"CALL SITE FOUND     : "
        f"{bool(calls)}"
    )

    print(
        f"SIGNAL BINDING      : "
        f"{signal_bound_calls > 0}"
    )

    print(
        f"ROW_RESULTS BINDING : "
        f"{row_result_calls > 0}"
    )

    print(
        f"ARTIFACT BINDING    : "
        f"{artifact_calls > 0}"
    )

    print(
        f"TARGET ROW BINDING  : "
        f"{direct_target_calls > 0}"
    )

    print(
        f"VERDICT             : "
        f"{verdict}"
    )

    print(
        f"REASON              : "
        f"{reason}"
    )

    print("=" * 100)
    print(
        "F) IMPORTANT LIMITATION"
    )
    print("=" * 100)

    print(
        "This forensic is static AST inspection only."
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
        "It does NOT generate an eligible signal."
    )

    print(
        "It does NOT generate an order intent."
    )

    print(
        "It does NOT modify any artifact."
    )

    print("=" * 100)
    print(
        "G) SAFETY ASSERTION"
    )
    print("=" * 100)

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
        "END — READ ONLY ORDER-INTENT "
        "GENERATOR CALL BOUNDARY FORENSIC v0.3"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())