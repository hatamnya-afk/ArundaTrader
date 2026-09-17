from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

TARGET_ROW_IDS = {37, 38, 39, 40}

ORDER_INTENT_TERMS = (
    "order_intent",
    "order_intents",
    "OrderIntent",
    "generate_order",
    "generate_order_intent",
    "order_intent_generator",
)

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

EXCLUDED_FILES = {
    "ARUNDA_TRADER_ORDER_INTENT_GENERATOR_INPUT_TRACE_FORENSIC_v0.1.py",
}


def print_line(char: str = "=", width: int = 100) -> None:
    print(char * width)


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def iter_python_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*.py"):

        if any(
            part in EXCLUDED_DIRS
            for part in path.parts
        ):
            continue

        if path.name in EXCLUDED_FILES:
            continue

        files.append(path)

    return sorted(files)


def iter_json_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*.json"):

        if any(
            part in EXCLUDED_DIRS
            for part in path.parts
        ):
            continue

        files.append(path)

    return sorted(files)


def load_json_read_only(
    path: Path,
) -> Any:

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)
    except Exception:
        return None


def node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts: list[str] = []

        current: ast.AST | None = node

        while isinstance(
            current,
            ast.Attribute,
        ):
            parts.append(current.attr)
            current = current.value

        if isinstance(
            current,
            ast.Name,
        ):
            parts.append(current.id)

        return ".".join(
            reversed(parts)
        )

    return ""


def source_segment(
    source: str,
    node: ast.AST,
) -> str:

    try:
        segment = ast.get_source_segment(
            source,
            node,
        )

        if segment:
            return segment.strip()

    except Exception:
        pass

    return ""


def discover_generator_definitions(
    path: Path,
    source: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError:
        return results

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            name = node.name.lower()

            relevant = any(
                term.lower() in name
                for term in ORDER_INTENT_TERMS
            )

            if not relevant:
                continue

            results.append(
                {
                    "file": str(path),
                    "line": node.lineno,
                    "type": type(node).__name__,
                    "name": node.name,
                }
            )

    return results


def discover_generator_calls(
    path: Path,
    source: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError:
        return results

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        name = node_name(
            node.func
        )

        if not name:
            continue

        lowered = name.lower()

        relevant = any(
            term.lower() in lowered
            for term in ORDER_INTENT_TERMS
        )

        if not relevant:
            continue

        args = []

        for arg in node.args:
            args.append(
                source_segment(
                    source,
                    arg,
                )
            )

        keywords = {}

        for kw in node.keywords:
            if kw.arg is None:
                continue

            keywords[kw.arg] = source_segment(
                source,
                kw.value,
            )

        results.append(
            {
                "file": str(path),
                "line": node.lineno,
                "call": name,
                "args": args,
                "keywords": keywords,
                "source": source_segment(
                    source,
                    node,
                ),
            }
        )

    return results


def discover_order_intent_related_lines(
    path: Path,
    source: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    lines = source.splitlines()

    for index, line in enumerate(
        lines,
        start=1,
    ):

        lowered = line.lower()

        if not any(
            term.lower() in lowered
            for term in ORDER_INTENT_TERMS
        ):
            continue

        results.append(
            {
                "file": str(path),
                "line": index,
                "text": line.strip(),
            }
        )

    return results


def recursive_find_paths(
    obj: Any,
    target_ids: set[int],
    path: str = "$",
) -> list[dict[str, Any]]:

    found: list[dict[str, Any]] = []

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            child_path = (
                f"{path}.{key}"
            )

            found.extend(
                recursive_find_paths(
                    value,
                    target_ids,
                    child_path,
                )
            )

    elif isinstance(
        obj,
        list,
    ):

        for index, value in enumerate(
            obj
        ):

            child_path = (
                f"{path}[{index}]"
            )

            found.extend(
                recursive_find_paths(
                    value,
                    target_ids,
                    child_path,
                )
            )

    elif isinstance(
        obj,
        int,
    ) and not isinstance(
        obj,
        bool,
    ):

        if obj in target_ids:

            found.append(
                {
                    "path": path,
                    "value": obj,
                }
            )

    return found


def discover_signal_rows(
    obj: Any,
    path: str = "$",
) -> list[dict[str, Any]]:

    rows: list[dict[str, Any]] = []

    if isinstance(
        obj,
        dict,
    ):

        if (
            "id" in obj
            and "asset" in obj
            and "eligible" in obj
            and "status" in obj
        ):

            rows.append(
                {
                    "path": path,
                    "row": obj,
                }
            )

        for key, value in obj.items():

            rows.extend(
                discover_signal_rows(
                    value,
                    f"{path}.{key}",
                )
            )

    elif isinstance(
        obj,
        list,
    ):

        for index, value in enumerate(
            obj
        ):

            rows.extend(
                discover_signal_rows(
                    value,
                    f"{path}[{index}]",
                )
            )

    return rows


def classify_signal_row(
    row: dict[str, Any],
) -> bool:

    row_id = row.get("id")

    return (
        isinstance(row_id, int)
        and not isinstance(row_id, bool)
        and row_id in TARGET_ROW_IDS
    )


def find_json_signal_evidence() -> list[dict[str, Any]]:

    evidence: list[dict[str, Any]] = []

    for path in iter_json_files():

        data = load_json_read_only(
            path
        )

        if data is None:
            continue

        rows = discover_signal_rows(
            data
        )

        for item in rows:

            row = item["row"]

            if classify_signal_row(
                row
            ):

                evidence.append(
                    {
                        "file": str(path),
                        "path": item["path"],
                        "row": row,
                    }
                )

    return evidence


def find_json_id_references() -> list[dict[str, Any]]:

    evidence: list[dict[str, Any]] = []

    for path in iter_json_files():

        data = load_json_read_only(
            path
        )

        if data is None:
            continue

        matches = recursive_find_paths(
            data,
            TARGET_ROW_IDS,
        )

        if not matches:
            continue

        evidence.append(
            {
                "file": str(path),
                "matches": matches,
            }
        )

    return evidence


def find_source_id_references(
    path: Path,
    source: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    lines = source.splitlines()

    for index, line in enumerate(
        lines,
        start=1,
    ):

        for row_id in sorted(
            TARGET_ROW_IDS
        ):

            patterns = (
                rf"\bid\s*=\s*{row_id}\b",
                rf"\bid['\"]?\s*[:=]\s*{row_id}\b",
                rf"\b{row_id}\b",
            )

            if any(
                re.search(
                    pattern,
                    line,
                    re.IGNORECASE,
                )
                for pattern in patterns
            ):

                results.append(
                    {
                        "file": str(path),
                        "line": index,
                        "row_id": row_id,
                        "text": line.strip(),
                    }
                )

    return results


def analyze_producer_relationship(
    definitions: list[dict[str, Any]],
    calls: list[dict[str, Any]],
) -> dict[str, Any]:

    result = {
        "definitions": definitions,
        "calls": calls,
        "producer_found": bool(
            definitions
        ),
        "call_sites_found": bool(
            calls
        ),
    }

    return result


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — ORDER-INTENT GENERATOR INPUT TRACE FORENSIC v0.2"
    )
    print("=" * 100)
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
        "WRITE              : NONE"
    )
    print(
        "ARTIFACT CREATION  : NONE"
    )
    print("=" * 100)

    python_files = iter_python_files()
    json_files = iter_json_files()

    print(
        f"PYTHON FILES SCANNED : {len(python_files)}"
    )

    print(
        f"JSON FILES SCANNED   : {len(json_files)}"
    )

    print("=" * 100)
    print("A) EXISTING REAL SIGNAL EVIDENCE")
    print("=" * 100)

    signal_evidence = (
        find_json_signal_evidence()
    )

    if not signal_evidence:

        print(
            "TARGET ROWS 37-40 : NOT FOUND"
        )

    else:

        for item in signal_evidence:

            row = item["row"]

            print(
                f"FILE      : {item['file']}"
            )

            print(
                f"PATH      : {item['path']}"
            )

            print(
                f"ID        : {row.get('id')}"
            )

            print(
                f"ASSET     : {row.get('asset')}"
            )

            print(
                f"DIRECTION : {row.get('direction')}"
            )

            print(
                f"ELIGIBLE  : {row.get('eligible')}"
            )

            print(
                f"STATUS    : {row.get('status')}"
            )

            print(
                f"ENTRY     : {row.get('entry_price')}"
            )

            print("-" * 100)

    print("=" * 100)
    print("B) ORDER-INTENT GENERATOR DEFINITIONS")
    print("=" * 100)

    all_definitions: list[dict[str, Any]] = []

    for path in python_files:

        source = safe_read_text(
            path
        )

        if not source:
            continue

        definitions = (
            discover_generator_definitions(
                path,
                source,
            )
        )

        all_definitions.extend(
            definitions
        )

    if not all_definitions:

        print(
            "NO ORDER-INTENT GENERATOR DEFINITION FOUND."
        )

    else:

        for item in all_definitions:

            print(
                f"TYPE : {item['type']}"
            )

            print(
                f"NAME : {item['name']}"
            )

            print(
                f"FILE : {item['file']}"
            )

            print(
                f"LINE : {item['line']}"
            )

            print("-" * 100)

    print("=" * 100)
    print("C) ORDER-INTENT GENERATOR CALL SITES")
    print("=" * 100)

    all_calls: list[dict[str, Any]] = []

    for path in python_files:

        source = safe_read_text(
            path
        )

        if not source:
            continue

        calls = discover_generator_calls(
            path,
            source,
        )

        all_calls.extend(
            calls
        )

    if not all_calls:

        print(
            "NO ORDER-INTENT GENERATOR CALL SITE FOUND."
        )

    else:

        for item in all_calls:

            print(
                f"FILE : {item['file']}"
            )

            print(
                f"LINE : {item['line']}"
            )

            print(
                f"CALL : {item['call']}"
            )

            print(
                f"ARGS : {item['args']}"
            )

            print(
                f"KW   : {item['keywords']}"
            )

            print(
                f"SRC  : {item['source']}"
            )

            print("-" * 100)

    print("=" * 100)
    print("D) TARGET ROW ID REFERENCES IN PROJECT SOURCE")
    print("=" * 100)

    source_id_evidence: list[dict[str, Any]] = []

    for path in python_files:

        source = safe_read_text(
            path
        )

        if not source:
            continue

        refs = find_source_id_references(
            path,
            source,
        )

        source_id_evidence.extend(
            refs
        )

    if not source_id_evidence:

        print(
            "NO SOURCE-CODE REFERENCE TO TARGET ROW IDs 37-40 FOUND."
        )

    else:

        for item in source_id_evidence:

            print(
                f"FILE    : {item['file']}"
            )

            print(
                f"LINE    : {item['line']}"
            )

            print(
                f"ROW ID  : {item['row_id']}"
            )

            print(
                f"SOURCE  : {item['text']}"
            )

            print("-" * 100)

    print("=" * 100)
    print("E) JSON ID REFERENCES — READ ONLY")
    print("=" * 100)

    json_id_evidence = (
        find_json_id_references()
    )

    if not json_id_evidence:

        print(
            "NO JSON REFERENCES TO TARGET ROW IDs 37-40 FOUND."
        )

    else:

        for item in json_id_evidence:

            print(
                f"FILE : {item['file']}"
            )

            for match in item["matches"]:

                print(
                    f"PATH : {match['path']}"
                )

                print(
                    f"VALUE: {match['value']}"
                )

            print("-" * 100)

    print("=" * 100)
    print("F) ORDER-INTENT RELATED SOURCE MAP")
    print("=" * 100)

    related_source_lines: list[dict[str, Any]] = []

    for path in python_files:

        source = safe_read_text(
            path
        )

        if not source:
            continue

        related = (
            discover_order_intent_related_lines(
                path,
                source,
            )
        )

        related_source_lines.extend(
            related
        )

    if not related_source_lines:

        print(
            "NO ORDER-INTENT RELATED SOURCE LINES FOUND."
        )

    else:

        for item in related_source_lines:

            print(
                f"{item['file']}:{item['line']}"
            )

            print(
                f"    {item['text']}"
            )

    print("=" * 100)
    print("G) PRODUCER / INPUT TRACE DECISION")
    print("=" * 100)

    producer_found = bool(
        all_definitions
    )

    call_site_found = bool(
        all_calls
    )

    real_signal_found = bool(
        signal_evidence
    )

    target_id_source_refs = bool(
        source_id_evidence
    )

    target_id_json_refs = bool(
        json_id_evidence
    )

    if not producer_found:

        verdict = (
            "BLOCKED_PRODUCER_NOT_FOUND"
        )

        reason = (
            "No real Order-Intent Generator definition "
            "was found in the project source."
        )

    elif not call_site_found:

        verdict = (
            "BLOCKED_GENERATOR_CALL_SITE_NOT_FOUND"
        )

        reason = (
            "Generator definition exists, but no call-site "
            "was found."
        )

    elif not real_signal_found:

        verdict = (
            "BLOCKED_NO_REAL_SIGNAL_INPUT"
        )

        reason = (
            "Generator exists, but no real target signal "
            "row 37-40 exists in scanned JSON artifacts."
        )

    elif not target_id_source_refs:

        verdict = (
            "INPUT_DELIVERY_NOT_PROVEN"
        )

        reason = (
            "Real target rows exist, but source-code tracing "
            "does not prove that rows 37-40 are delivered "
            "to the generator."
        )

    else:

        verdict = (
            "GENERATOR_INPUT_TRACE_REQUIRES_CALL_ARGUMENT_REVIEW"
        )

        reason = (
            "Generator and target-row references exist. "
            "Exact producer-to-input binding requires reviewing "
            "the discovered generator call arguments."
        )

    print(
        f"REAL SIGNAL ROWS  : {real_signal_found}"
    )

    print(
        f"PRODUCER FOUND    : {producer_found}"
    )

    print(
        f"CALL SITE FOUND   : {call_site_found}"
    )

    print(
        f"SOURCE ID REFS    : {target_id_source_refs}"
    )

    print(
        f"JSON ID REFS      : {target_id_json_refs}"
    )

    print(
        f"VERDICT            : {verdict}"
    )

    print(
        f"REASON             : {reason}"
    )

    print("=" * 100)
    print("H) SAFETY ASSERTION")
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
        "END — READ ONLY PRODUCER / INPUT TRACE FORENSIC"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())