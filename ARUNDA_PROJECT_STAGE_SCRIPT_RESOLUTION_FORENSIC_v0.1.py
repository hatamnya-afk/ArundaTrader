# =============================================================================
# ARUNDA PROJECT — STAGE SCRIPT RESOLUTION FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#   Resolve, statically and read-only, how arunda_pipeline.py determines
#   the "script" argument consumed by run_stage().
#
# TARGET:
#   launcher
#      ->
#   main
#      ->
#   arunda_pipeline.py
#      ->
#   stage dispatcher / run_stage
#      ->
#   script resolution
#      ->
#   upgrade_db.py
#
# SAFETY:
#   READ ONLY
#   STATIC ONLY
#   NO DATABASE
#   NO NETWORK
#   NO PROJECT EXECUTION
#   NO FILE MODIFICATION
#
# =============================================================================

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

PIPELINE_FILE = PROJECT_DIR / "arunda_pipeline.py"
TARGET_UPGRADE = "upgrade_db.py"

OUTPUT_JSON = (
    PROJECT_DIR
    / "ARUNDA_PROJECT_STAGE_SCRIPT_RESOLUTION_FORENSIC_v0.1.json"
)

OUTPUT_TXT = (
    PROJECT_DIR
    / "ARUNDA_PROJECT_STAGE_SCRIPT_RESOLUTION_FORENSIC_v0.1.txt"
)

# IMPORTANT:
# These are intentionally disabled.
# This artifact must not modify the project.
WRITE_OUTPUT_FILES = False


# =============================================================================
# HELPERS
# =============================================================================

def source_segment(
    source: str,
    node: ast.AST,
) -> str:

    try:
        return ast.get_source_segment(
            source,
            node,
        ) or ""
    except Exception:
        return ""


def safe_constant(
    node: ast.AST,
) -> Any:

    if isinstance(node, ast.Constant):
        return node.value

    return None


def line_texts(
    source: str,
    start: int,
    end: int,
) -> list[str]:

    lines = source.splitlines()

    start_index = max(0, start - 1)
    end_index = min(len(lines), end)

    return lines[start_index:end_index]


def contains_upgrade_reference(
    text: str,
) -> bool:

    lower = text.lower()

    return (
        TARGET_UPGRADE.lower() in lower
        or "upgrade_db" in lower
    )


# =============================================================================
# AST NODE DESCRIPTION
# =============================================================================

def describe_call(
    source: str,
    node: ast.Call,
) -> dict[str, Any]:

    function_name = ""

    if isinstance(node.func, ast.Name):
        function_name = node.func.id

    elif isinstance(node.func, ast.Attribute):
        function_name = (
            f"{source_segment(source, node.func.value)}."
            f"{node.func.attr}"
        )

    args = []

    for index, arg in enumerate(node.args):

        args.append(
            {
                "index": index,
                "type": type(arg).__name__,
                "source": source_segment(
                    source,
                    arg,
                ),
                "constant": safe_constant(arg),
                "contains_upgrade_db": contains_upgrade_reference(
                    source_segment(source, arg)
                ),
            }
        )

    keywords = []

    for keyword in node.keywords:

        keywords.append(
            {
                "name": keyword.arg,
                "type": type(keyword.value).__name__,
                "source": source_segment(
                    source,
                    keyword.value,
                ),
                "constant": safe_constant(
                    keyword.value
                ),
                "contains_upgrade_db": contains_upgrade_reference(
                    source_segment(
                        source,
                        keyword.value,
                    )
                ),
            }
        )

    return {
        "line": getattr(node, "lineno", None),
        "end_line": getattr(
            node,
            "end_lineno",
            getattr(node, "lineno", None),
        ),
        "function": function_name,
        "source": source_segment(
            source,
            node,
        ),
        "args": args,
        "keywords": keywords,
        "contains_upgrade_db": contains_upgrade_reference(
            source_segment(source, node)
        ),
    }


# =============================================================================
# FUNCTION FINDER
# =============================================================================

def find_function(
    tree: ast.AST,
    name: str,
) -> list[ast.AST]:

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name == name:
                result.append(node)

    return result


# =============================================================================
# ASSIGNMENT ANALYSIS
# =============================================================================

def collect_assignments(
    source: str,
    tree: ast.AST,
) -> list[dict[str, Any]]:

    records = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
            ),
        ):

            text = source_segment(
                source,
                node,
            )

            if (
                "script" in text.lower()
                or contains_upgrade_reference(text)
            ):

                records.append(
                    {
                        "line": getattr(
                            node,
                            "lineno",
                            None,
                        ),
                        "end_line": getattr(
                            node,
                            "end_lineno",
                            getattr(
                                node,
                                "lineno",
                                None,
                            ),
                        ),
                        "type": type(node).__name__,
                        "source": text,
                        "contains_upgrade_db": contains_upgrade_reference(
                            text
                        ),
                    }
                )

    return sorted(
        records,
        key=lambda item: (
            item["line"] or 0
        ),
    )


# =============================================================================
# CALL ANALYSIS
# =============================================================================

def collect_relevant_calls(
    source: str,
    tree: ast.AST,
) -> list[dict[str, Any]]:

    records = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            call = describe_call(
                source,
                node,
            )

            function_name = call["function"].lower()

            if (
                "run_stage" in function_name
                or "subprocess.run" in function_name
                or "stage" in function_name
                or "script" in call["source"].lower()
                or call["contains_upgrade_db"]
            ):

                records.append(call)

    return sorted(
        records,
        key=lambda item: (
            item["line"] or 0
        ),
    )


# =============================================================================
# RUN_STAGE ANALYSIS
# =============================================================================

def analyze_run_stage(
    source: str,
    tree: ast.AST,
) -> dict[str, Any]:

    functions = find_function(
        tree,
        "run_stage",
    )

    if not functions:

        return {
            "found": False,
            "functions": [],
        }

    results = []

    for function in functions:

        body_start = getattr(
            function,
            "lineno",
            None,
        )

        body_end = getattr(
            function,
            "end_lineno",
            body_start,
        )

        calls = []

        for node in ast.walk(function):

            if isinstance(
                node,
                ast.Call,
            ):

                calls.append(
                    describe_call(
                        source,
                        node,
                    )
                )

        assignments = []

        for node in ast.walk(function):

            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.AugAssign,
                ),
            ):

                text = source_segment(
                    source,
                    node,
                )

                assignments.append(
                    {
                        "line": getattr(
                            node,
                            "lineno",
                            None,
                        ),
                        "source": text,
                        "contains_script": (
                            "script"
                            in text.lower()
                        ),
                        "contains_upgrade_db": (
                            contains_upgrade_reference(
                                text
                            )
                        ),
                    }
                )

        relevant_lines = line_texts(
            source,
            body_start,
            body_end,
        )

        results.append(
            {
                "name": function.name,
                "line": body_start,
                "end_line": body_end,
                "source_contains_upgrade_db": (
                    contains_upgrade_reference(
                        "\n".join(
                            relevant_lines
                        )
                    )
                ),
                "assignments": assignments,
                "calls": calls,
            }
        )

    return {
        "found": True,
        "functions": results,
    }


# =============================================================================
# DISPATCHER / CALLER ANALYSIS
# =============================================================================

def analyze_run_stage_callers(
    source: str,
    tree: ast.AST,
) -> list[dict[str, Any]]:

    records = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if isinstance(
            node.func,
            ast.Name,
        ):

            if node.func.id != "run_stage":
                continue

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            if node.func.attr != "run_stage":
                continue

        else:
            continue

        records.append(
            {
                "line": getattr(
                    node,
                    "lineno",
                    None,
                ),
                "source": source_segment(
                    source,
                    node,
                ),
                "arguments": [
                    {
                        "index": index,
                        "source": source_segment(
                            source,
                            arg,
                        ),
                        "type": type(arg).__name__,
                        "constant": safe_constant(
                            arg
                        ),
                        "contains_upgrade_db": contains_upgrade_reference(
                            source_segment(
                                source,
                                arg,
                            )
                        ),
                    }
                    for index, arg
                    in enumerate(node.args)
                ],
                "keywords": [
                    {
                        "name": keyword.arg,
                        "source": source_segment(
                            source,
                            keyword.value,
                        ),
                        "type": type(
                            keyword.value
                        ).__name__,
                        "constant": safe_constant(
                            keyword.value
                        ),
                        "contains_upgrade_db": contains_upgrade_reference(
                            source_segment(
                                source,
                                keyword.value,
                            )
                        ),
                    }
                    for keyword in node.keywords
                ],
            }
        )

    return sorted(
        records,
        key=lambda item: (
            item["line"] or 0
        ),
    )


# =============================================================================
# GLOBAL upgrade_db SEARCH
# =============================================================================

def collect_upgrade_references(
    source: str,
) -> list[dict[str, Any]]:

    records = []

    for number, line in enumerate(
        source.splitlines(),
        start=1,
    ):

        if contains_upgrade_reference(line):

            records.append(
                {
                    "line": number,
                    "source": line.strip(),
                }
            )

    return records


# =============================================================================
# AST DYNAMIC EXECUTION ANALYSIS
# =============================================================================

def collect_dynamic_execution_calls(
    source: str,
    tree: ast.AST,
) -> list[dict[str, Any]]:

    records = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        call = describe_call(
            source,
            node,
        )

        function_name = call["function"].lower()

        if (
            "subprocess.run" in function_name
            or "subprocess.popen" in function_name
            or "subprocess.call" in function_name
            or "subprocess.check_call" in function_name
            or "subprocess.check_output" in function_name
            or "exec(" in call["source"]
            or "eval(" in call["source"]
            or "import_module" in function_name
            or "__import__" in function_name
        ):

            records.append(
                call
            )

    return sorted(
        records,
        key=lambda item: (
            item["line"] or 0
        ),
    )


# =============================================================================
# MAIN FORENSIC ANALYSIS
# =============================================================================

def build_report() -> dict[str, Any]:

    report: dict[str, Any] = {
        "artifact": (
            "ARUNDA_PROJECT_STAGE_SCRIPT_RESOLUTION_FORENSIC_v0.1"
        ),
        "mode": "READ ONLY",
        "static_analysis": True,
        "database_access": False,
        "network_access": False,
        "project_execution": False,
        "file_modification": False,
        "pipeline_file": str(
            PIPELINE_FILE
        ),
        "target_upgrade": TARGET_UPGRADE,
    }

    # -------------------------------------------------------------------------
    # FILE EXISTENCE
    # -------------------------------------------------------------------------

    report["pipeline_exists"] = (
        PIPELINE_FILE.exists()
    )

    if not PIPELINE_FILE.exists():

        report["status"] = (
            "BLOCKED_PIPELINE_NOT_FOUND"
        )

        return report

    # -------------------------------------------------------------------------
    # READ SOURCE ONLY
    # -------------------------------------------------------------------------

    try:

        source = PIPELINE_FILE.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        source = PIPELINE_FILE.read_text(
            encoding="utf-8-sig"
        )

    report["pipeline_size_bytes"] = (
        PIPELINE_FILE.stat().st_size
    )

    # -------------------------------------------------------------------------
    # PARSE AST
    # -------------------------------------------------------------------------

    try:

        tree = ast.parse(
            source,
            filename=str(
                PIPELINE_FILE
            ),
        )

    except SyntaxError as exc:

        report["ast_parse_error"] = {
            "line": exc.lineno,
            "offset": exc.offset,
            "message": exc.msg,
        }

        report["status"] = (
            "BLOCKED_AST_PARSE_ERROR"
        )

        return report

    report["ast_parse_success"] = True

    # -------------------------------------------------------------------------
    # FUNCTIONS
    # -------------------------------------------------------------------------

    functions = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                }
            )

    report["functions"] = sorted(
        functions,
        key=lambda item: item["line"],
    )

    # -------------------------------------------------------------------------
    # run_stage
    # -------------------------------------------------------------------------

    report["run_stage_analysis"] = (
        analyze_run_stage(
            source,
            tree,
        )
    )

    # -------------------------------------------------------------------------
    # run_stage CALLERS
    # -------------------------------------------------------------------------

    report["run_stage_callers"] = (
        analyze_run_stage_callers(
            source,
            tree,
        )
    )

    # -------------------------------------------------------------------------
    # SCRIPT / UPGRADE ASSIGNMENTS
    # -------------------------------------------------------------------------

    report["script_assignments"] = (
        collect_assignments(
            source,
            tree,
        )
    )

    # -------------------------------------------------------------------------
    # RELEVANT CALLS
    # -------------------------------------------------------------------------

    report["relevant_calls"] = (
        collect_relevant_calls(
            source,
            tree,
        )
    )

    # -------------------------------------------------------------------------
    # DYNAMIC EXECUTION
    # -------------------------------------------------------------------------

    report["dynamic_execution_calls"] = (
        collect_dynamic_execution_calls(
            source,
            tree,
        )
    )

    # -------------------------------------------------------------------------
    # STATIC upgrade_db REFERENCES
    # -------------------------------------------------------------------------

    report["upgrade_db_references"] = (
        collect_upgrade_references(
            source,
        )
    )

    # -------------------------------------------------------------------------
    # RESOLUTION CONCLUSION
    # -------------------------------------------------------------------------

    run_stage = report[
        "run_stage_analysis"
    ]

    callers = report[
        "run_stage_callers"
    ]

    dynamic_calls = report[
        "dynamic_execution_calls"
    ]

    upgrade_refs = report[
        "upgrade_db_references"
    ]

    has_run_stage = bool(
        run_stage.get("found")
    )

    has_dynamic_execution = bool(
        dynamic_calls
    )

    has_upgrade_static_ref = bool(
        upgrade_refs
    )

    script_argument_sources = []

    for caller in callers:

        if caller["arguments"]:

            for argument in caller[
                "arguments"
            ]:

                script_argument_sources.append(
                    {
                        "line": caller["line"],
                        "argument_index": argument[
                            "index"
                        ],
                        "source": argument[
                            "source"
                        ],
                        "type": argument[
                            "type"
                        ],
                        "constant": argument[
                            "constant"
                        ],
                        "contains_upgrade_db": argument[
                            "contains_upgrade_db"
                        ],
                    }
                )

    report[
        "script_argument_sources"
    ] = script_argument_sources

    direct_upgrade_argument = any(
        item["contains_upgrade_db"]
        for item in script_argument_sources
    )

    if not has_run_stage:

        status = (
            "NO_RUN_STAGE_FOUND"
        )

    elif not has_dynamic_execution:

        status = (
            "RUN_STAGE_FOUND_BUT_NO_DYNAMIC_EXECUTION"
        )

    elif direct_upgrade_argument:

        status = (
            "DIRECT_UPGRADE_DB_STAGE_ARGUMENT_FOUND"
        )

    elif has_upgrade_static_ref:

        status = (
            "UPGRADE_DB_REFERENCE_EXISTS_BUT_RESOLUTION_NOT_PROVEN"
        )

    else:

        status = (
            "SCRIPT_RESOLUTION_REMAINS_DYNAMIC_UNRESOLVED"
        )

    report["status"] = status

    # -------------------------------------------------------------------------
    # EXPLICIT FORENSIC QUESTION
    # -------------------------------------------------------------------------

    report["forensic_question"] = (
        "How does arunda_pipeline.py resolve the "
        "script argument passed into run_stage(), "
        "and can that resolution be statically proven "
        "to resolve to upgrade_db.py?"
    )

    report["target_path"] = (
        "launcher -> main -> arunda_pipeline.py "
        "-> dispatcher -> run_stage -> script resolution "
        "-> upgrade_db.py"
    )

    # -------------------------------------------------------------------------
    # SAFETY ASSERTIONS
    # -------------------------------------------------------------------------

    report["safety"] = {
        "read_only": True,
        "static_only": True,
        "database_access": False,
        "network_access": False,
        "project_execution": False,
        "file_modification": False,
        "output_files_written": False,
    }

    return report


# =============================================================================
# TEXT REPORT
# =============================================================================

def print_report(
    report: dict[str, Any],
) -> None:

    print(
        "=" * 110
    )

    print(
        "ARUNDA PROJECT — STAGE SCRIPT RESOLUTION FORENSIC v0.1"
    )

    print(
        "=" * 110
    )

    print(
        f"MODE                : {report['mode']}"
    )

    print(
        f"STATIC ANALYSIS     : YES"
    )

    print(
        f"DATABASE ACCESS     : NO"
    )

    print(
        f"NETWORK ACCESS      : NO"
    )

    print(
        f"PROJECT EXECUTION   : NO"
    )

    print(
        f"FILE MODIFICATION   : NO"
    )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "TARGET"
    )

    print(
        "-" * 110
    )

    print(
        f"PIPELINE            : {report['pipeline_file']}"
    )

    print(
        f"UPGRADE_DB          : {report['target_upgrade']}"
    )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "RUN_STAGE ANALYSIS"
    )

    print(
        "-" * 110
    )

    run_stage = report[
        "run_stage_analysis"
    ]

    print(
        f"FOUND               : {run_stage.get('found')}"
    )

    for function in run_stage.get(
        "functions",
        [],
    ):

        print(
            f"FUNCTION            : {function['name']}"
        )

        print(
            f"RANGE               : "
            f"{function['line']} - "
            f"{function['end_line']}"
        )

        print(
            f"SOURCE HAS UPGRADE  : "
            f"{function['source_contains_upgrade_db']}"
        )

        print(
            "\nCALLS:"
        )

        for call in function[
            "calls"
        ]:

            print(
                f"  {call['line']} | "
                f"{call['function']} | "
                f"{call['source']}"
            )

        print(
            "\nSCRIPT-RELATED ASSIGNMENTS:"
        )

        for assignment in function[
            "assignments"
        ]:

            if assignment[
                "contains_script"
            ] or assignment[
                "contains_upgrade_db"
            ]:

                print(
                    f"  {assignment['line']} | "
                    f"{assignment['source']}"
                )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "run_stage() CALLERS"
    )

    print(
        "-" * 110
    )

    callers = report[
        "run_stage_callers"
    ]

    if not callers:

        print(
            "NO STATIC run_stage() CALLER FOUND"
        )

    else:

        for caller in callers:

            print(
                f"LINE : {caller['line']}"
            )

            print(
                f"CALL : {caller['source']}"
            )

            for argument in caller[
                "arguments"
            ]:

                print(
                    f"  ARG[{argument['index']}] "
                    f"type={argument['type']} "
                    f"value={argument['source']}"
                )

            for keyword in caller[
                "keywords"
            ]:

                print(
                    f"  KW[{keyword['name']}] "
                    f"type={keyword['type']} "
                    f"value={keyword['source']}"
                )

            print()

    print(
        "\n"
        + "-" * 110
    )

    print(
        "SCRIPT ARGUMENT SOURCES"
    )

    print(
        "-" * 110
    )

    arguments = report[
        "script_argument_sources"
    ]

    if not arguments:

        print(
            "NO STATIC SCRIPT ARGUMENT SOURCE FOUND"
        )

    else:

        for item in arguments:

            print(
                f"LINE             : {item['line']}"
            )

            print(
                f"ARGUMENT INDEX    : {item['argument_index']}"
            )

            print(
                f"TYPE             : {item['type']}"
            )

            print(
                f"SOURCE           : {item['source']}"
            )

            print(
                f"UPGRADE_DB       : "
                f"{item['contains_upgrade_db']}"
            )

            print()

    print(
        "\n"
        + "-" * 110
    )

    print(
        "DYNAMIC EXECUTION CALLS"
    )

    print(
        "-" * 110
    )

    dynamic_calls = report[
        "dynamic_execution_calls"
    ]

    if not dynamic_calls:

        print(
            "NO STATIC DYNAMIC EXECUTION CALL FOUND"
        )

    else:

        for call in dynamic_calls:

            print(
                f"LINE   : {call['line']}"
            )

            print(
                f"CALL   : {call['function']}"
            )

            print(
                f"SOURCE : {call['source']}"
            )

            print()

    print(
        "\n"
        + "-" * 110
    )

    print(
        "STATIC upgrade_db.py REFERENCES"
    )

    print(
        "-" * 110
    )

    references = report[
        "upgrade_db_references"
    ]

    if not references:

        print(
            "NO STATIC upgrade_db.py REFERENCE FOUND"
        )

    else:

        for reference in references:

            print(
                f"LINE {reference['line']} : "
                f"{reference['source']}"
            )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "FINAL FORENSIC STATUS"
    )

    print(
        "=" * 110
    )

    print(
        f"STATUS              : "
        f"{report['status']}"
    )

    print(
        "\nTARGET:"
    )

    print(
        report["target_path"]
    )

    print(
        "\n"
        + "-" * 110
    )

    print(
        "READ ONLY           : YES"
    )

    print(
        "STATIC ONLY         : YES"
    )

    print(
        "DATABASE            : NONE"
    )

    print(
        "NETWORK             : NONE"
    )

    print(
        "PROJECT EXECUTION   : NONE"
    )

    print(
        "FILE MODIFICATION   : NONE"
    )

    print(
        "=" * 110
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    report = build_report()

    print_report(
        report
    )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    # No JSON/TXT output is written.
    # The forensic artifact is intentionally console-only.
    # -------------------------------------------------------------------------

    if WRITE_OUTPUT_FILES:

        raise RuntimeError(
            "WRITE_OUTPUT_FILES must remain False "
            "for this forensic artifact."
        )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    main()