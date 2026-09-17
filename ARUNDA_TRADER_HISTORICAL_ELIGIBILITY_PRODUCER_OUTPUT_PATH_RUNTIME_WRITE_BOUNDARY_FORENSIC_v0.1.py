import ast
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCER = PROJECT_ROOT / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
TARGET_NAME = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
REPORT = PROJECT_ROOT / (
    "HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_PATH_RUNTIME_WRITE_BOUNDARY_FORENSIC_REPORT.json"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def syntax_valid(source):
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as exc:
        return False, str(exc)


def get_source_lines(source):
    return source.splitlines()


def find_assignments(tree):
    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    results.append(
                        {
                            "line": node.lineno,
                            "name": target.id,
                            "node": node,
                        }
                    )

    return results


def find_report_path_assignment(tree):
    matches = []

    for item in find_assignments(tree):
        if item["name"] == "report_path":
            matches.append(item)

    return matches


def expression_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse_failed>"


def is_deterministic_report_path(node):
    if not isinstance(node.value, ast.BinOp):
        return False

    if not isinstance(node.value.op, ast.Div):
        return False

    left = node.value.left
    right = node.value.right

    if not isinstance(left, ast.Name):
        return False

    if left.id != "PROJECT_ROOT":
        return False

    if not isinstance(right, ast.Constant):
        return False

    return right.value == TARGET_NAME


def find_writer_calls(tree):
    writers = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            fn = node.func.id

            if fn == "open":
                mode = None

                if len(node.args) >= 2:
                    arg = node.args[1]
                    if isinstance(arg, ast.Constant):
                        mode = arg.value

                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = kw.value.value

                writers.append(
                    {
                        "line": node.lineno,
                        "type": "open",
                        "mode": mode,
                        "target": (
                            expression_text(node.args[0])
                            if node.args
                            else None
                        ),
                    }
                )

        elif isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "json"
                and node.func.attr == "dump"
            ):
                target = None

                if len(node.args) >= 2:
                    target = expression_text(node.args[1])

                writers.append(
                    {
                        "line": node.lineno,
                        "type": "json.dump",
                        "mode": None,
                        "target": target,
                    }
                )

    return sorted(writers, key=lambda x: x["line"])


def find_report_path_references(tree):
    refs = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "report_path":
            refs.append(
                {
                    "line": node.lineno,
                    "context": type(
                        getattr(node, "ctx", None)
                    ).__name__,
                }
            )

    return sorted(refs, key=lambda x: x["line"])


def analyze_write_boundary(tree, report_assignment):
    assignment_line = report_assignment["line"]

    writers = find_writer_calls(tree)
    report_refs = find_report_path_references(tree)

    report_writes = []

    for writer in writers:
        target = writer.get("target") or ""

        if "report_path" in target:
            report_writes.append(writer)

    later_refs = [
        ref
        for ref in report_refs
        if ref["line"] >= assignment_line
    ]

    return {
        "assignment_line": assignment_line,
        "report_path_references": later_refs,
        "writer_calls": writers,
        "report_path_writer_calls": report_writes,
        "report_path_reaches_writer": bool(report_writes),
    }


def build_report(
    source_sha256,
    syntax_ok,
    syntax_error,
    assignment_info,
    boundary,
):
    deterministic = is_deterministic_report_path(
        assignment_info["node"]
    )

    report_writer_lines = [
        item["line"]
        for item in boundary["report_path_writer_calls"]
    ]

    return {
        "forensic": {
            "name": (
                "HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH "
                "RUNTIME WRITE BOUNDARY FORENSIC v0.1"
            ),
            "mode": "READ-ONLY FORENSIC",
            "timestamp_utc": utc_now(),
        },
        "project": {
            "project_root": str(PROJECT_ROOT),
            "producer": str(PRODUCER),
            "target_report": TARGET_NAME,
        },
        "producer": {
            "exists": PRODUCER.exists(),
            "sha256": source_sha256 if PRODUCER.exists() else None,
            "syntax_valid": syntax_ok,
            "syntax_error": syntax_error,
        },
        "report_path_contract": {
            "assignment_count": 1,
            "line": assignment_info["line"],
            "expression": expression_text(
                assignment_info["node"].value
            ),
            "deterministic": deterministic,
            "project_root_reference": (
                "PROJECT_ROOT"
                in expression_text(assignment_info["node"].value)
            ),
            "target_filename_correct": (
                TARGET_NAME
                in expression_text(assignment_info["node"].value)
            ),
        },
        "runtime_write_boundary_static_evidence": {
            "report_path_reference_count": len(
                boundary["report_path_references"]
            ),
            "writer_call_count": len(boundary["writer_calls"]),
            "report_path_writer_call_count": len(
                boundary["report_path_writer_calls"]
            ),
            "report_path_reaches_writer": boundary[
                "report_path_reaches_writer"
            ],
            "writer_lines": report_writer_lines,
            "writers": boundary["writer_calls"],
        },
        "runtime_execution": {
            "producer_executed": False,
            "producer_imported": False,
            "report_regenerated": False,
            "artifact_written": False,
            "network_access": False,
            "production_db_writes": False,
        },
    }


def print_report(report):
    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH "
        "RUNTIME WRITE BOUNDARY FORENSIC v0.1"
    )
    print("=" * 100)
    print("MODE                         : READ-ONLY FORENSIC")
    print(f"PROJECT ROOT                : {PROJECT_ROOT}")
    print(f"PRODUCER                    : {PRODUCER.name}")
    print(f"TARGET REPORT               : {TARGET_NAME}")
    print("=" * 100)

    print("PRODUCER")
    print("=" * 100)
    print(
        f"Producer exists              : "
        f"{report['producer']['exists']}"
    )
    print(
        f"Producer syntax valid        : "
        f"{report['producer']['syntax_valid']}"
    )
    print(
        f"Producer SHA256              : "
        f"{report['producer']['sha256']}"
    )

    print("=" * 100)
    print("REPORT_PATH CONTRACT")
    print("=" * 100)
    print(
        f"Assignment line              : "
        f"{report['report_path_contract']['line']}"
    )
    print(
        f"Expression                   : "
        f"{report['report_path_contract']['expression']}"
    )
    print(
        f"Deterministic                : "
        f"{report['report_path_contract']['deterministic']}"
    )
    print(
        f"PROJECT_ROOT reference      : "
        f"{report['report_path_contract']['project_root_reference']}"
    )
    print(
        f"Target filename correct      : "
        f"{report['report_path_contract']['target_filename_correct']}"
    )

    print("=" * 100)
    print("WRITE BOUNDARY")
    print("=" * 100)
    print(
        f"report_path references       : "
        f"{report['runtime_write_boundary_static_evidence']['report_path_reference_count']}"
    )
    print(
        f"Writer calls                 : "
        f"{report['runtime_write_boundary_static_evidence']['writer_call_count']}"
    )
    print(
        f"report_path writer calls     : "
        f"{report['runtime_write_boundary_static_evidence']['report_path_writer_call_count']}"
    )
    print(
        f"report_path → writer         : "
        f"{report['runtime_write_boundary_static_evidence']['report_path_reaches_writer']}"
    )

    for writer in report["runtime_write_boundary_static_evidence"]["writers"]:
        print(
            f"  line={writer['line']} | "
            f"type={writer['type']} | "
            f"mode={writer['mode']} | "
            f"target={writer['target']}"
        )

    print("=" * 100)
    print("RUNTIME SAFETY")
    print("=" * 100)
    print("Producer executed            : NO")
    print("Producer imported            : NO")
    print("Report regenerated           : NO")
    print("Artifact written             : NO")
    print("Synthetic artifact           : NO")
    print("Production DB writes         : NONE")
    print("Network access               : NONE")

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    contract_ok = (
        report["producer"]["exists"]
        and report["producer"]["syntax_valid"]
        and report["report_path_contract"]["deterministic"]
        and report["report_path_contract"]["project_root_reference"]
        and report["report_path_contract"]["target_filename_correct"]
        and report["runtime_write_boundary_static_evidence"][
            "report_path_reaches_writer"
        ]
    )

    if contract_ok:
        verdict = (
            "RUNTIME_WRITE_BOUNDARY_STATICALLY_MAPPED"
        )
    else:
        verdict = (
            "RUNTIME_WRITE_BOUNDARY_MAPPING_REQUIRES_REPAIR"
        )

    print(
        "HISTORICAL ELIGIBILITY RUNTIME WRITE BOUNDARY : "
        + verdict
    )
    print(f"FORENSIC REPORT              : {REPORT}")
    print("=" * 100)


def main():
    if not PRODUCER.exists():
        raise FileNotFoundError(
            f"Producer not found: {PRODUCER}"
        )

    source = PRODUCER.read_text(
        encoding="utf-8",
        errors="strict",
    )

    source_sha256 = sha256_file(PRODUCER)

    syntax_ok, syntax_error = syntax_valid(source)

    if not syntax_ok:
        report = {
            "forensic": {
                "name": (
                    "HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH "
                    "RUNTIME WRITE BOUNDARY FORENSIC v0.1"
                ),
                "mode": "READ-ONLY FORENSIC",
                "timestamp_utc": utc_now(),
            },
            "project": {
                "project_root": str(PROJECT_ROOT),
                "producer": str(PRODUCER),
                "target_report": TARGET_NAME,
            },
            "producer": {
                "exists": True,
                "sha256": source_sha256,
                "syntax_valid": False,
                "syntax_error": syntax_error,
            },
            "runtime_execution": {
                "producer_executed": False,
                "producer_imported": False,
                "report_regenerated": False,
                "artifact_written": False,
                "network_access": False,
                "production_db_writes": False,
            },
        }

        REPORT.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print_report(report)
        return

    tree = ast.parse(source)

    assignments = find_report_path_assignment(tree)

    if len(assignments) != 1:
        raise RuntimeError(
            "Expected exactly one report_path assignment, "
            f"found {len(assignments)}."
        )

    assignment = assignments[0]

    boundary = analyze_write_boundary(
        tree,
        assignment,
    )

    report = build_report(
        source_sha256=source_sha256,
        syntax_ok=syntax_ok,
        syntax_error=syntax_error,
        assignment_info=assignment,
        boundary=boundary,
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print_report(report)


if __name__ == "__main__":
    main()