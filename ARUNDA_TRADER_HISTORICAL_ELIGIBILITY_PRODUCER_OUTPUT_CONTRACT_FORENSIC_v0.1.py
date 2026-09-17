# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER
HISTORICAL ELIGIBILITY PRODUCER OUTPUT CONTRACT FORENSIC v0.1
====================================================================================================

MODE:
    READ-ONLY FORENSIC

PURPOSE:
    Inspect the historical eligibility producer's output contract without:
        - importing the producer
        - executing the producer
        - executing eligibility
        - regenerating the report
        - modifying production source
        - modifying production DB
        - network access

TARGET REPORT:
    LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json

PRODUCER:
    ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py

OUTPUT:
    HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_CONTRACT_FORENSIC_REPORT.json
====================================================================================================
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ==================================================================================================
# CONFIG
# ==================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER_NAME = (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

REPORT_NAME = (
    "HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_CONTRACT_FORENSIC_REPORT.json"
)

PRODUCER_PATH = PROJECT_ROOT / PRODUCER_NAME
REPORT_PATH = PROJECT_ROOT / REPORT_NAME


# ==================================================================================================
# CONSTANTS
# ==================================================================================================

SEPARATOR = "=" * 100

WRITE_FUNCTIONS = {
    "open",
    "write",
    "writelines",
    "json.dump",
    "json.dumps",
    "Path.write_text",
    "Path.write_bytes",
    "os.replace",
    "shutil.copy",
}

TARGET_EXTENSIONS = {
    ".py",
    ".json",
    ".txt",
    ".log",
    ".md",
}


# ==================================================================================================
# HELPERS
# ==================================================================================================

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def safe_read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            return path.read_text(errors="replace")
        except Exception:
            return None


def normalize_path_string(value: str) -> str:
    value = value.strip().strip("\"'`")
    value = value.replace("/", "\\")
    return value


def contains_target(value: str) -> bool:
    return TARGET_REPORT.lower() in value.lower()


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def make_excerpt(lines: list[str], line_no: int, radius: int = 2) -> list[str]:
    start = max(0, line_no - radius - 1)
    end = min(len(lines), line_no + radius)
    return [
        f"{idx + 1}: {lines[idx]}"
        for idx in range(start, end)
    ]


def ast_name(node: ast.AST | None) -> str | None:
    if node is None:
        return None

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = ast_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr

    return None


def constant_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{...}")
        return "".join(parts)

    return None


def call_name(node: ast.Call) -> str | None:
    return ast_name(node.func)


# ==================================================================================================
# FILESYSTEM DISCOVERY
# ==================================================================================================

def discover_files() -> list[Path]:
    files = []

    try:
        for root, dirs, filenames in os.walk(PROJECT_ROOT):
            dirs[:] = [
                d for d in dirs
                if d not in {
                    "__pycache__",
                    ".git",
                    ".venv",
                    "venv",
                    "node_modules",
                }
            ]

            for filename in filenames:
                try:
                    files.append(Path(root) / filename)
                except Exception:
                    pass
    except Exception:
        pass

    return files


# ==================================================================================================
# PRODUCER STATIC FORENSIC
# ==================================================================================================

def inspect_producer(path: Path) -> dict[str, Any]:

    result: dict[str, Any] = {
        "exists": path.exists(),
        "path": str(path),
        "sha256": None,
        "size_bytes": None,
        "syntax_valid": False,
        "parse_error": None,
        "target_string_occurrences": [],
        "target_literal_occurrences": [],
        "path_construction_occurrences": [],
        "writer_calls": [],
        "open_calls": [],
        "json_dump_calls": [],
        "json_load_calls": [],
        "write_text_calls": [],
        "write_bytes_calls": [],
        "rename_replace_calls": [],
        "function_definitions": [],
        "main_guard": False,
        "producer_execution_indicators": [],
        "report_generation_contract": {
            "target_referenced": False,
            "writer_present": False,
            "target_passed_to_writer": False,
            "static_output_path_resolved": False,
            "dynamic_output_path": False,
        },
    }

    if not path.exists():
        return result

    try:
        result["size_bytes"] = path.stat().st_size
    except Exception:
        pass

    result["sha256"] = sha256_file(path)

    source = safe_read_text(path)

    if source is None:
        result["parse_error"] = "SOURCE_READ_FAILED"
        return result

    lines = source.splitlines()

    # ----------------------------------------------------------------------------------------------
    # Raw textual target search
    # ----------------------------------------------------------------------------------------------

    for idx, line in enumerate(lines, start=1):
        if contains_target(line):
            result["target_string_occurrences"].append({
                "line": idx,
                "text": line[:1000],
            })

    # ----------------------------------------------------------------------------------------------
    # AST parse
    # ----------------------------------------------------------------------------------------------

    try:
        tree = ast.parse(source, filename=str(path))
        result["syntax_valid"] = True
    except SyntaxError as exc:
        result["parse_error"] = {
            "type": "SyntaxError",
            "message": str(exc),
            "line": exc.lineno,
            "offset": exc.offset,
            "text": exc.text,
        }
        return result
    except Exception as exc:
        result["parse_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return result

    # ----------------------------------------------------------------------------------------------
    # Function definitions
    # ----------------------------------------------------------------------------------------------

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["function_definitions"].append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", None),
            })

    # ----------------------------------------------------------------------------------------------
    # Main guard
    # ----------------------------------------------------------------------------------------------

    for node in tree.body:
        if not isinstance(node, ast.If):
            continue

        try:
            condition = ast.unparse(node.test)
        except Exception:
            condition = ""

        if "__name__" in condition and "__main__" in condition:
            result["main_guard"] = True

    # ----------------------------------------------------------------------------------------------
    # AST forensic calls
    # ----------------------------------------------------------------------------------------------

    for node in ast.walk(tree):

        # String literals
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value

            if contains_target(value):
                result["target_literal_occurrences"].append({
                    "line": getattr(node, "lineno", None),
                    "value": value,
                })

        # Function calls
        if isinstance(node, ast.Call):

            name = call_name(node)
            if not name:
                continue

            normalized = name.replace(" ", "")

            call_record = {
                "line": getattr(node, "lineno", None),
                "call": name,
                "source": None,
            }

            try:
                call_record["source"] = ast.unparse(node)
            except Exception:
                pass

            if name == "open":
                result["open_calls"].append(call_record)

            if name in {
                "json.dump",
                "json.dumps",
            }:
                result["json_dump_calls"].append(call_record)

            if name == "json.load":
                result["json_load_calls"].append(call_record)

            if name.endswith(".write_text"):
                result["write_text_calls"].append(call_record)

            if name.endswith(".write_bytes"):
                result["write_bytes_calls"].append(call_record)

            if name in {
                "os.replace",
                "os.rename",
                "Path.rename",
                "Path.replace",
            }:
                result["rename_replace_calls"].append(call_record)

            # Generic writer detection
            if (
                name == "open"
                or name.endswith(".write_text")
                or name.endswith(".write_bytes")
                or name in {"json.dump", "os.replace", "os.rename"}
            ):
                result["writer_calls"].append(call_record)

            # Target passed directly into call
            for arg in list(node.args) + [
                keyword.value for keyword in node.keywords
            ]:
                try:
                    arg_source = ast.unparse(arg)
                except Exception:
                    arg_source = ""

                if contains_target(arg_source):
                    result["report_generation_contract"][
                        "target_passed_to_writer"
                    ] = True

            # Dynamic path indicators
            if name in {
                "open",
                "Path",
                "Path.open",
                "Path.write_text",
                "Path.write_bytes",
            }:
                try:
                    call_source = ast.unparse(node)
                except Exception:
                    call_source = ""

                if (
                    "TARGET_REPORT" not in call_source
                    and "REPORT_NAME" not in call_source
                    and contains_target(call_source)
                ):
                    result["report_generation_contract"][
                        "dynamic_output_path"
                    ] = True

        # Assignments
        if isinstance(node, ast.Assign):
            try:
                value_source = ast.unparse(node.value)
            except Exception:
                value_source = ""

            if contains_target(value_source):
                result["path_construction_occurrences"].append({
                    "line": getattr(node, "lineno", None),
                    "source": value_source,
                })

    # ----------------------------------------------------------------------------------------------
    # Contract synthesis
    # ----------------------------------------------------------------------------------------------

    contract = result["report_generation_contract"]

    contract["target_referenced"] = bool(
        result["target_string_occurrences"]
        or result["target_literal_occurrences"]
    )

    contract["writer_present"] = bool(
        result["writer_calls"]
    )

    contract["static_output_path_resolved"] = bool(
        contract["target_referenced"]
        and (
            result["path_construction_occurrences"]
            or result["target_literal_occurrences"]
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Execution indicators
    # ----------------------------------------------------------------------------------------------

    suspicious_execution_patterns = [
        "main(",
        "process_signals(",
        "create_outcome(",
        "eligibility",
        "write_report",
        "save_report",
        "generate_report",
        "dump_report",
    ]

    for idx, line in enumerate(lines, start=1):
        lowered = line.lower()

        for pattern in suspicious_execution_patterns:
            if pattern.lower() in lowered:
                result["producer_execution_indicators"].append({
                    "line": idx,
                    "pattern": pattern,
                    "text": line[:1000],
                })

    return result


# ==================================================================================================
# RELATED REPORT FORENSIC
# ==================================================================================================

def inspect_related_json(files: list[Path]) -> list[dict[str, Any]]:
    evidence = []

    for path in files:

        if path.suffix.lower() != ".json":
            continue

        if path.name == REPORT_NAME:
            continue

        text = safe_read_text(path)

        if text is None:
            continue

        lowered = text.lower()

        score = 0
        reasons = []

        if TARGET_REPORT.lower() in lowered:
            score += 20
            reasons.append("TARGET_REPORT_REFERENCE")

        if PRODUCER_NAME.lower() in lowered:
            score += 15
            reasons.append("PRODUCER_REFERENCE")

        for token in (
            "producer",
            "runtime",
            "artifact",
            "eligibility",
            "report",
            "output",
            "writer",
            "path",
            "target",
        ):
            if token in lowered:
                score += 1

        if score <= 0:
            continue

        evidence.append({
            "path": str(path),
            "score": score,
            "target_reference": TARGET_REPORT.lower() in lowered,
            "producer_reference": PRODUCER_NAME.lower() in lowered,
            "reasons": reasons,
        })

    evidence.sort(
        key=lambda x: (-x["score"], x["path"].lower())
    )

    return evidence[:100]


# ==================================================================================================
# OUTPUT PATH FORENSIC
# ==================================================================================================

def inspect_filesystem_for_target(files: list[Path]) -> dict[str, Any]:
    exact = []
    similar = []

    target_lower = TARGET_REPORT.lower()
    target_stem = Path(TARGET_REPORT).stem.lower()

    for path in files:
        name_lower = path.name.lower()

        if name_lower == target_lower:
            exact.append(str(path))
            continue

        if (
            target_stem in name_lower
            or (
                "eligibility" in name_lower
                and "report" in name_lower
                and path.suffix.lower() == ".json"
            )
        ):
            similar.append(str(path))

    return {
        "exact_target_found": bool(exact),
        "exact_paths": exact,
        "similar_candidates": similar[:100],
    }


# ==================================================================================================
# CONTRACT VERDICT
# ==================================================================================================

def build_verdict(
    producer: dict[str, Any],
    target_fs: dict[str, Any],
) -> dict[str, Any]:

    if not producer["exists"]:
        status = "PRODUCER_NOT_FOUND"

    elif not producer["syntax_valid"]:
        status = "PRODUCER_SYNTAX_INVALID"

    elif target_fs["exact_target_found"]:
        status = "TARGET_ARTIFACT_ALREADY_PRESENT"

    elif not producer["report_generation_contract"]["target_referenced"]:
        status = "OUTPUT_CONTRACT_TARGET_NOT_REFERENCED"

    elif not producer["report_generation_contract"]["writer_present"]:
        status = "OUTPUT_CONTRACT_WRITER_NOT_FOUND"

    elif not producer["report_generation_contract"]["target_passed_to_writer"]:
        status = "OUTPUT_CONTRACT_TARGET_WRITER_LINK_UNVERIFIED"

    elif producer["report_generation_contract"]["dynamic_output_path"]:
        status = "OUTPUT_CONTRACT_DYNAMIC_PATH_REQUIRES_RUNTIME_VERIFICATION"

    else:
        status = "OUTPUT_CONTRACT_STATICALLY_PRESENT_RUNTIME_VERIFICATION_REQUIRED"

    return {
        "status": status,
        "exact_artifact_recovered": target_fs["exact_target_found"],
        "producer_exists": producer["exists"],
        "producer_syntax_valid": producer["syntax_valid"],
        "target_referenced": producer[
            "report_generation_contract"
        ]["target_referenced"],
        "writer_present": producer[
            "report_generation_contract"
        ]["writer_present"],
        "target_passed_to_writer": producer[
            "report_generation_contract"
        ]["target_passed_to_writer"],
        "dynamic_output_path": producer[
            "report_generation_contract"
        ]["dynamic_output_path"],
    }


# ==================================================================================================
# REPORT
# ==================================================================================================

def build_report() -> dict[str, Any]:

    files = discover_files()

    producer = inspect_producer(PRODUCER_PATH)

    target_fs = inspect_filesystem_for_target(files)

    related_json = inspect_related_json(files)

    verdict = build_verdict(
        producer,
        target_fs,
    )

    return {
        "metadata": {
            "title": (
                "ARUNDA TRADER "
                "HISTORICAL ELIGIBILITY PRODUCER OUTPUT CONTRACT FORENSIC v0.1"
            ),
            "mode": "READ-ONLY FORENSIC",
            "generated_at_utc": now_utc(),
            "project_root": str(PROJECT_ROOT),
            "producer": PRODUCER_NAME,
            "target_report": TARGET_REPORT,
            "report": REPORT_NAME,
        },

        "filesystem_inventory": {
            "files_discovered": len(files),
            "exact_target_files_found": len(
                target_fs["exact_paths"]
            ),
        },

        "target_artifact": target_fs,

        "producer_static_forensic": producer,

        "related_json_evidence": {
            "candidate_count": len(related_json),
            "candidates": related_json,
        },

        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "synthetic_artifact": False,
            "production_db_writes": "NONE",
            "production_source_modified": False,
            "network_access": False,
            "artifact_extraction_executed": False,
            "recovery_staging": False,
        },

        "verdict": verdict,

        "next_action": {
            "if_contract_broken": (
                "DIRECT_PRODUCER_OUTPUT_CONTRACT_REPAIR"
            ),
            "if_contract_valid": (
                "RUNTIME_OUTPUT_WRITER_INVOCATION_VERIFICATION"
            ),
        },
    }


# ==================================================================================================
# CONSOLE REPORT
# ==================================================================================================

def print_console(report: dict[str, Any]) -> None:

    metadata = report["metadata"]
    fs = report["filesystem_inventory"]
    producer = report["producer_static_forensic"]
    verdict = report["verdict"]

    print(SEPARATOR)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY PRODUCER OUTPUT CONTRACT FORENSIC v0.1")
    print(SEPARATOR)

    print(f"MODE                         : {metadata['mode']}")
    print(f"PROJECT ROOT                 : {metadata['project_root']}")
    print(f"TARGET REPORT                : {metadata['target_report']}")
    print(f"PRODUCER                     : {metadata['producer']}")
    print(SEPARATOR)

    print("FILESYSTEM INVENTORY")
    print(SEPARATOR)

    print(
        f"Files discovered              : "
        f"{fs['files_discovered']}"
    )

    print(
        f"Exact target files found      : "
        f"{fs['exact_target_files_found']}"
    )

    print(SEPARATOR)
    print("PRODUCER STATIC CONTRACT")
    print(SEPARATOR)

    print(
        f"Producer exists               : "
        f"{producer['exists']}"
    )

    print(
        f"Producer syntax valid         : "
        f"{producer['syntax_valid']}"
    )

    print(
        f"Target referenced             : "
        f"{producer['report_generation_contract']['target_referenced']}"
    )

    print(
        f"Writer present                : "
        f"{producer['report_generation_contract']['writer_present']}"
    )

    print(
        f"Target passed to writer       : "
        f"{producer['report_generation_contract']['target_passed_to_writer']}"
    )

    print(
        f"Dynamic output path           : "
        f"{producer['report_generation_contract']['dynamic_output_path']}"
    )

    print(
        f"Main guard                    : "
        f"{producer['main_guard']}"
    )

    print(SEPARATOR)
    print("TARGET REFERENCES")
    print(SEPARATOR)

    for item in producer["target_string_occurrences"][:20]:
        print(
            f"  line={item['line']} | "
            f"{item['text'][:300]}"
        )

    if not producer["target_string_occurrences"]:
        print("  NONE")

    print(SEPARATOR)
    print("WRITER CALLS")
    print(SEPARATOR)

    for item in producer["writer_calls"][:30]:
        print(
            f"  line={item['line']} | "
            f"{item['call']} | "
            f"{str(item['source'])[:500]}"
        )

    if not producer["writer_calls"]:
        print("  NONE")

    print(SEPARATOR)
    print("JSON EVIDENCE")
    print(SEPARATOR)

    print(
        f"Related JSON candidates       : "
        f"{report['related_json_evidence']['candidate_count']}"
    )

    for idx, item in enumerate(
        report["related_json_evidence"]["candidates"][:20],
        start=1,
    ):
        print(
            f"  {idx:2d} | "
            f"score={item['score']:3d} | "
            f"{item['path']}"
        )

    print(SEPARATOR)
    print("OUTPUT CONTRACT DECISION")
    print(SEPARATOR)

    print(
        f"STATUS                       : "
        f"{verdict['status']}"
    )

    print(
        f"EXACT ARTIFACT RECOVERED    : "
        f"{verdict['exact_artifact_recovered']}"
    )

    print(
        f"TARGET REFERENCED           : "
        f"{verdict['target_referenced']}"
    )

    print(
        f"WRITER PRESENT              : "
        f"{verdict['writer_present']}"
    )

    print(
        f"TARGET → WRITER VERIFIED    : "
        f"{verdict['target_passed_to_writer']}"
    )

    print(SEPARATOR)
    print("SAFETY")
    print(SEPARATOR)

    safety = report["safety"]

    print(
        f"Producer executed            : "
        f"{'YES' if safety['producer_executed'] else 'NO'}"
    )

    print(
        f"Producer imported            : "
        f"{'YES' if safety['producer_imported'] else 'NO'}"
    )

    print(
        f"Eligibility executed         : "
        f"{'YES' if safety['eligibility_executed'] else 'NO'}"
    )

    print(
        f"Eligibility rebuilt          : "
        f"{'YES' if safety['eligibility_rebuilt'] else 'NO'}"
    )

    print(
        f"Report regenerated           : "
        f"{'YES' if safety['report_regenerated'] else 'NO'}"
    )

    print(
        f"Synthetic artifact           : "
        f"{'YES' if safety['synthetic_artifact'] else 'NO'}"
    )

    print(
        f"Production DB writes         : "
        f"{safety['production_db_writes']}"
    )

    print(
        f"Production source modified   : "
        f"{'YES' if safety['production_source_modified'] else 'NO'}"
    )

    print(
        f"Network access               : "
        f"{'YES' if safety['network_access'] else 'NO'}"
    )

    print(SEPARATOR)
    print("FINAL VERDICT")
    print(SEPARATOR)

    print(
        f"HISTORICAL ELIGIBILITY OUTPUT CONTRACT : "
        f"{verdict['status']}"
    )

    print(
        f"FORENSIC REPORT              : "
        f"{REPORT_PATH}"
    )

    print(SEPARATOR)


# ==================================================================================================
# WRITE FORENSIC REPORT ONLY
# ==================================================================================================

def write_report(report: dict[str, Any]) -> None:

    # This is the ONLY write performed by this script.
    # It writes the forensic report itself, not production artifacts.

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    report = build_report()

    write_report(report)

    print_console(report)


if __name__ == "__main__":
    main()