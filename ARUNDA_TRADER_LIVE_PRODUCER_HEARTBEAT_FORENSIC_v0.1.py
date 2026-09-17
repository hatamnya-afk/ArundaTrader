from __future__ import annotations

import ast
import json
import os
import re
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

POLL_SECONDS = 2.0

SIGNAL_KEYWORDS = (
    "signal",
    "eligible",
    "eligibility",
    "fusion",
)

OUTPUT_KEYWORDS = (
    "json",
    "artifact",
    "report",
    "output",
    "write",
    "dump",
    "save",
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

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

IGNORED_FILES = {
    "ARUNDA_TRADER_LIVE_PRODUCER_HEARTBEAT_FORENSIC_v0.1.py",
}


def print_rule() -> None:
    print("=" * 100)


def print_section(title: str) -> None:
    print_rule()
    print(title)
    print_rule()


def safe_read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def safe_load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        raw = path.read_bytes()

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode(
                "utf-8-sig",
                errors="replace",
            )

        if text.startswith("\ufeff"):
            text = text.lstrip("\ufeff")

        return json.loads(text), None

    except Exception as exc:
        return None, str(exc)


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
        lines[
            start - 1:end
        ]
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


def source_files() -> list[Path]:
    results: list[Path] = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS
        ]

        for filename in files:
            path = Path(root) / filename

            if filename in IGNORED_FILES:
                continue

            results.append(path)

    return sorted(results)


def python_files() -> list[Path]:
    return sorted(
        path
        for path in source_files()
        if path.suffix.lower() == ".py"
    )


def json_files() -> list[Path]:
    return sorted(
        path
        for path in source_files()
        if path.suffix.lower() == ".json"
    )


def function_is_producer(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    text: str,
) -> bool:
    name_match = contains_any(
        node.name,
        PRODUCER_KEYWORDS,
    )

    source = node_source(
        text,
        node,
    )

    body_match = contains_any(
        source,
        PRODUCER_KEYWORDS,
    )

    return name_match or body_match


def collect_producer_functions(
    path: Path,
) -> tuple[list[dict[str, Any]], str | None]:

    text = safe_read_text(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError as exc:
        return [], str(exc)

    found: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if not function_is_producer(
            node,
            text,
        ):
            continue

        calls: list[str] = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                callee = dotted_name(
                    child.func
                )

                if callee:
                    calls.append(
                        callee
                    )

        found.append(
            {
                "name": node.name,
                "line": line_of(node),
                "end_line": end_line_of(node),
                "calls": sorted(
                    set(calls)
                ),
                "source": node_source(
                    text,
                    node,
                ),
            }
        )

    return found, None


def collect_producer_calls(
    path: Path,
) -> tuple[list[dict[str, Any]], str | None]:

    text = safe_read_text(path)

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except SyntaxError as exc:
        return [], str(exc)

    calls: list[dict[str, Any]] = []

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

        if not contains_any(
            callee,
            PRODUCER_KEYWORDS,
        ) and not contains_any(
            blob,
            PRODUCER_KEYWORDS,
        ):
            continue

        arguments: list[str] = []

        for arg in node.args:
            name = dotted_name(arg)

            if name:
                arguments.append(name)
            else:
                arguments.append(
                    type(arg).__name__
                )

        keyword_arguments: dict[str, str] = {}

        for kw in node.keywords:
            key = kw.arg or "**"

            name = dotted_name(
                kw.value
            )

            keyword_arguments[key] = (
                name
                if name
                else type(
                    kw.value
                ).__name__
            )

        calls.append(
            {
                "callee": callee,
                "line": line_of(node),
                "end_line": end_line_of(node),
                "arguments": arguments,
                "keyword_arguments": keyword_arguments,
                "source": blob,
            }
        )

    return calls, None


def json_contains_eligible(
    obj: Any,
    path: str = "$",
) -> list[dict[str, Any]]:

    found: list[dict[str, Any]] = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            child_path = (
                f"{path}.{key}"
            )

            if (
                key.lower()
                == "eligible"
                and value is True
            ):
                found.append(
                    {
                        "path": child_path,
                        "parent": obj,
                    }
                )

            found.extend(
                json_contains_eligible(
                    value,
                    child_path,
                )
            )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            child_path = (
                f"{path}[{index}]"
            )

            found.extend(
                json_contains_eligible(
                    value,
                    child_path,
                )
            )

    return found


def signal_like_count(
    obj: Any,
) -> int:

    count = 0

    if isinstance(obj, dict):

        keys = {
            str(key).lower()
            for key in obj.keys()
        }

        signal_markers = {
            "signal_id",
            "direction",
            "confidence",
            "eligible",
            "entry_price",
            "asset",
            "symbol",
        }

        if len(
            keys & signal_markers
        ) >= 2:
            count += 1

        for value in obj.values():
            count += signal_like_count(
                value
            )

    elif isinstance(obj, list):

        for value in obj:
            count += signal_like_count(
                value
            )

    return count


def file_signature(
    path: Path,
) -> tuple[int, int]:

    try:
        stat = path.stat()

        return (
            int(stat.st_mtime_ns),
            int(stat.st_size),
        )

    except OSError:
        return (
            0,
            0,
        )


def discover_artifact_state() -> dict[str, tuple[int, int]]:
    state: dict[
        str,
        tuple[int, int],
    ] = {}

    for path in json_files():

        state[
            str(path)
        ] = file_signature(path)

    return state


def newest_json() -> tuple[Path | None, float]:

    newest_path: Path | None = None
    newest_time = 0.0

    for path in json_files():

        try:
            mtime = path.stat().st_mtime

        except OSError:
            continue

        if mtime > newest_time:
            newest_time = mtime
            newest_path = path

    return (
        newest_path,
        newest_time,
    )


def scan_json_artifacts() -> dict[str, Any]:

    artifacts = json_files()

    eligible_detections: list[
        dict[str, Any]
    ] = []

    parse_failures: list[
        dict[str, str]
    ] = []

    signal_objects = 0

    for path in artifacts:

        data, error = safe_load_json(
            path
        )

        if error:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": error,
                }
            )

            continue

        signal_objects += (
            signal_like_count(data)
        )

        eligible = (
            json_contains_eligible(
                data
            )
        )

        for item in eligible:

            eligible_detections.append(
                {
                    "artifact": str(path),
                    "path": item["path"],
                    "parent": item["parent"],
                }
            )

    newest_path, newest_time = newest_json()

    return {
        "artifact_count": len(artifacts),
        "signal_objects": signal_objects,
        "parse_failures": parse_failures,
        "eligible_detections": eligible_detections,
        "newest_path": newest_path,
        "newest_time": newest_time,
    }


def format_time(timestamp: float) -> str:
    if not timestamp:
        return "NONE"

    return time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime(timestamp),
    )


def source_output_mentions(
    path: Path,
) -> bool:

    text = safe_read_text(path)

    return (
        contains_any(
            text,
            OUTPUT_KEYWORDS,
        )
        and contains_any(
            text,
            SIGNAL_KEYWORDS,
        )
    )


def main() -> int:

    print_rule()
    print(
        "ARUNDA TRADER — LIVE PRODUCER HEARTBEAT "
        "FORENSIC v0.1"
    )
    print_rule()

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
            "ERROR: PROJECT ROOT NOT FOUND"
        )

        return 1

    print_section(
        "A) SOURCE / PRODUCER DISCOVERY"
    )

    py_files = python_files()

    print(
        f"PYTHON FILES DISCOVERED : "
        f"{len(py_files)}"
    )

    producer_definitions: list[
        dict[str, Any]
    ] = []

    producer_calls: list[
        dict[str, Any]
    ] = []

    parse_failures: list[
        dict[str, str]
    ] = []

    output_sources: list[
        str
    ] = []

    for path in py_files:

        definitions, error = (
            collect_producer_functions(
                path
            )
        )

        if error:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": error,
                }
            )

        for definition in definitions:

            definition[
                "file"
            ] = str(path)

            producer_definitions.append(
                definition
            )

        calls, call_error = (
            collect_producer_calls(
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

        for call in calls:

            call[
                "file"
            ] = str(path)

            producer_calls.append(
                call
            )

        try:

            if source_output_mentions(
                path
            ):
                output_sources.append(
                    str(path)
                )

        except Exception:
            pass

    print(
        f"PRODUCER-LIKE DEFINITIONS : "
        f"{len(producer_definitions)}"
    )

    print(
        f"PRODUCER-LIKE CALL SITES : "
        f"{len(producer_calls)}"
    )

    print(
        f"SOURCE PARSE FAILURES : "
        f"{len(parse_failures)}"
    )

    if producer_definitions:

        print_section(
            "B) PRODUCER DEFINITIONS"
        )

        for item in producer_definitions:

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
                "CALLS : "
                f"{item['calls']}"
            )

    if producer_calls:

        print_section(
            "C) PRODUCER CALL SITES"
        )

        for item in producer_calls:

            print(
                f"\nFILE : {item['file']}"
            )

            print(
                f"CALL : {item['callee']}"
            )

            print(
                f"LINES : "
                f"{item['line']}-"
                f"{item['end_line']}"
            )

            print(
                "ARGUMENTS : "
                f"{item['arguments']}"
            )

            print(
                "KEYWORD ARGUMENTS : "
                f"{item['keyword_arguments']}"
            )

            print(
                "SOURCE:"
            )

            print(
                item["source"]
            )

    print_section(
        "D) CURRENT ARTIFACT STATE"
    )

    initial_scan = (
        scan_json_artifacts()
    )

    print(
        "JSON ARTIFACTS : "
        f"{initial_scan['artifact_count']}"
    )

    print(
        "SIGNAL-LIKE OBJECTS : "
        f"{initial_scan['signal_objects']}"
    )

    print(
        "PARSE FAILURES : "
        f"{len(initial_scan['parse_failures'])}"
    )

    print(
        "ELIGIBLE DETECTIONS : "
        f"{len(initial_scan['eligible_detections'])}"
    )

    newest_path = (
        initial_scan["newest_path"]
    )

    print(
        "NEWEST ARTIFACT : "
        f"{newest_path if newest_path else 'NONE'}"
    )

    print(
        "NEWEST ARTIFACT TIME : "
        f"{format_time(initial_scan['newest_time'])}"
    )

    if initial_scan[
        "eligible_detections"
    ]:

        print_section(
            "E) EXISTING ELIGIBLE DETECTIONS"
        )

        for item in initial_scan[
            "eligible_detections"
        ]:

            print(
                f"ARTIFACT : "
                f"{item['artifact']}"
            )

            print(
                f"PATH : "
                f"{item['path']}"
            )

            print(
                f"OBJECT : "
                f"{item['parent']}"
            )

    else:

        print_section(
            "E) EXISTING ELIGIBLE DETECTIONS"
        )

        print(
            "NONE"
        )

    print_section(
        "F) PRODUCER OUTPUT SOURCES"
    )

    print(
        f"SOURCE FILES WITH SIGNAL/OUTPUT "
        f"EVIDENCE : {len(output_sources)}"
    )

    for path in output_sources:

        print(
            f"SOURCE : {path}"
        )

    print_section(
        "G) INITIAL PRODUCER HEARTBEAT DECISION"
    )

    if not producer_definitions:

        initial_verdict = (
            "PRODUCER_NOT_FOUND"
        )

        initial_reason = (
            "No signal/eligibility producer-like "
            "function was found in project Python source."
        )

    elif not producer_calls:

        initial_verdict = (
            "PRODUCER_CALL_SITE_NOT_FOUND"
        )

        initial_reason = (
            "Producer-like definitions exist, "
            "but no producer call site was statically found."
        )

    elif initial_scan[
        "eligible_detections"
    ]:

        initial_verdict = (
            "REAL_ELIGIBLE_SIGNAL_ALREADY_PRESENT"
        )

        initial_reason = (
            "An existing JSON artifact contains "
            "eligible=True."
        )

    else:

        initial_verdict = (
            "PRODUCER_EXISTS_BUT_NO_CURRENT_ELIGIBLE_OUTPUT"
        )

        initial_reason = (
            "Producer definitions and call sites exist, "
            "but the current artifact set contains "
            "no eligible=True signal."
        )

    print(
        f"VERDICT : {initial_verdict}"
    )

    print(
        f"REASON  : {initial_reason}"
    )

    print_section(
        "H) LIVE HEARTBEAT WATCH"
    )

    print(
        "STATUS : WAIT_FOR_ELIGIBLE_SIGNAL"
    )

    print(
        "The watcher monitors only filesystem "
        "artifact changes."
    )

    print(
        "No production Python execution will occur."
    )

    print(
        "No database access will occur."
    )

    print(
        "No artifact will be created or modified."
    )

    print(
        "Press Ctrl+C to stop."
    )

    previous_state = (
        discover_artifact_state()
    )

    scan_number = 0

    try:

        while True:

            time.sleep(
                POLL_SECONDS
            )

            scan_number += 1

            current_state = (
                discover_artifact_state()
            )

            changed_paths: list[str] = []

            all_paths = (
                set(previous_state)
                | set(current_state)
            )

            for path_string in sorted(
                all_paths
            ):

                before = (
                    previous_state.get(
                        path_string
                    )
                )

                after = (
                    current_state.get(
                        path_string
                    )
                )

                if before != after:

                    changed_paths.append(
                        path_string
                    )

            scan = (
                scan_json_artifacts()
            )

            print()

            print("-" * 100)

            print(
                f"HEARTBEAT : "
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            print(
                f"SCAN      : "
                f"{scan_number}"
            )

            print(
                f"JSON ARTIFACTS : "
                f"{scan['artifact_count']}"
            )

            print(
                f"ARTIFACT CHANGES : "
                f"{len(changed_paths)}"
            )

            if changed_paths:

                print(
                    "CHANGED ARTIFACTS:"
                )

                for path_string in changed_paths:

                    print(
                        f"  {path_string}"
                    )

            newest_path = (
                scan["newest_path"]
            )

            print(
                "NEWEST ARTIFACT : "
                f"{newest_path if newest_path else 'NONE'}"
            )

            print(
                "NEWEST ARTIFACT TIME : "
                f"{format_time(scan['newest_time'])}"
            )

            print(
                "SIGNAL OBJECTS SCANNED : "
                f"{scan['signal_objects']}"
            )

            print(
                "PARSE FAILURES : "
                f"{len(scan['parse_failures'])}"
            )

            print(
                "ELIGIBLE DETECTIONS : "
                f"{len(scan['eligible_detections'])}"
            )

            if scan[
                "eligible_detections"
            ]:

                print_section(
                    "REAL ELIGIBLE SIGNAL DETECTED"
                )

                for item in scan[
                    "eligible_detections"
                ]:

                    print(
                        f"ARTIFACT : "
                        f"{item['artifact']}"
                    )

                    print(
                        f"PATH : "
                        f"{item['path']}"
                    )

                    print(
                        f"OBJECT : "
                        f"{item['parent']}"
                    )

                print(
                    "WATCHER STATUS : "
                    "REAL_ELIGIBLE_SIGNAL_DETECTED"
                )

                print(
                    "NEXT STAGE : "
                    "TRACE_THIS_REAL_SIGNAL_ONLY"
                )

                print_rule()

                return 0

            print(
                "WATCHER STATUS : "
                "WAIT_FOR_ELIGIBLE_SIGNAL"
            )

            previous_state = current_state

    except KeyboardInterrupt:

        print()
        print_section(
            "WATCH STOPPED"
        )

        print(
            "STATUS : WAIT_FOR_ELIGIBLE_SIGNAL"
        )

        print(
            "No eligible signal was detected "
            "during this watcher session."
        )

    except Exception as exc:

        print()
        print_section(
            "WATCHER ERROR"
        )

        print(
            f"ERROR : {exc}"
        )

        return 1

    print_section(
        "I) FINAL SAFETY ASSERTION"
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

    print_rule()
    print(
        "END — READ ONLY LIVE PRODUCER HEARTBEAT FORENSIC"
    )
    print_rule()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())