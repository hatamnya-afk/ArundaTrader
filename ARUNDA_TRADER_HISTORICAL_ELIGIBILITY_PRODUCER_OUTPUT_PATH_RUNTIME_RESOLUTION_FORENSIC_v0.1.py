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
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_PATH_"
    "RUNTIME_RESOLUTION_FORENSIC_REPORT.json"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_source():
    return PRODUCER.read_text(encoding="utf-8")


def syntax_check(source):
    try:
        ast.parse(source, filename=str(PRODUCER))
        return True, None
    except SyntaxError as exc:
        return False, str(exc)


def find_report_path_assignment(tree):
    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "report_path":
                    results.append(node)

        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == "report_path"
            ):
                results.append(node)

    return results


def expression_to_text(node):
    return ast.unparse(node)


def evaluate_static_path(node):
    """
    Resolve only the deterministic contract:

        PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

    No producer execution occurs.
    """

    if not isinstance(node, ast.Assign):
        return None

    if len(node.targets) != 1:
        return None

    target = node.targets[0]

    if not isinstance(target, ast.Name):
        return None

    if target.id != "report_path":
        return None

    value = node.value

    if not isinstance(value, ast.BinOp):
        return None

    if not isinstance(value.op, ast.Div):
        return None

    if not isinstance(value.left, ast.Name):
        return None

    if value.left.id != "PROJECT_ROOT":
        return None

    right = value.right

    if not isinstance(right, ast.Constant):
        return None

    if right.value != TARGET_NAME:
        return None

    return PROJECT_ROOT / TARGET_NAME


def find_writer_usage(tree):
    usages = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id

                if name == "open":
                    usages.append(
                        {
                            "line": node.lineno,
                            "type": "open",
                            "arguments": [
                                ast.unparse(arg)
                                for arg in node.args
                            ],
                        }
                    )

                elif name == "json.dump":
                    usages.append(
                        {
                            "line": node.lineno,
                            "type": "json.dump",
                            "arguments": [
                                ast.unparse(arg)
                                for arg in node.args
                            ],
                        }
                    )

            elif isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "json"
                    and node.func.attr == "dump"
                ):
                    usages.append(
                        {
                            "line": node.lineno,
                            "type": "json.dump",
                            "arguments": [
                                ast.unparse(arg)
                                for arg in node.args
                            ],
                        }
                    )

    return usages


def find_main(tree):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node

    return None


def find_main_guard(source):
    normalized = source.replace(" ", "")

    return (
        'if__name__=="__main__":' in normalized
        or "if__name__=='__main__':" in normalized
    )


def build_report(
    source_sha,
    syntax_valid,
    assignment_count,
    assignment_line,
    assignment_expression,
    resolved_path,
    writer_usages,
    main_exists,
    main_guard,
):
    expected_path = PROJECT_ROOT / TARGET_NAME

    deterministic_verified = (
        assignment_count == 1
        and resolved_path is not None
        and resolved_path == expected_path
    )

    return {
        "forensic": {
            "name": (
                "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_"
                "PRODUCER_OUTPUT_PATH_RUNTIME_RESOLUTION_FORENSIC_v0.1"
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
            "syntax_valid": syntax_valid,
            "sha256": source_sha,
        },
        "report_path_contract": {
            "assignment_count": assignment_count,
            "assignment_line": assignment_line,
            "assignment_expression": assignment_expression,
            "deterministic_static_resolution": deterministic_verified,
            "resolved_path": (
                str(resolved_path)
                if resolved_path is not None
                else None
            ),
            "expected_path": str(expected_path),
        },
        "writer_boundary": {
            "writer_usage_count": len(writer_usages),
            "writer_usages": writer_usages,
        },
        "runtime_entry": {
            "main_exists": main_exists,
            "main_guard": main_guard,
            "producer_executed": False,
        },
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "artifact_written": False,
            "synthetic_artifact": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
            "source_modified": False,
        },
        "verdict": (
            "RUNTIME_OUTPUT_PATH_RESOLUTION_VERIFIED"
            if deterministic_verified
            else "RUNTIME_OUTPUT_PATH_RESOLUTION_UNVERIFIED"
        ),
    }


def print_header():
    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH "
        "RUNTIME RESOLUTION FORENSIC v0.1"
    )
    print("=" * 100)
    print("MODE                         : READ-ONLY FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"PRODUCER                     : {PRODUCER.name}")
    print(f"TARGET REPORT                : {TARGET_NAME}")
    print("=" * 100)


def main():
    print_header()

    if not PRODUCER.exists():
        raise FileNotFoundError(
            f"Producer not found: {PRODUCER}"
        )

    source = load_source()
    source_sha = sha256_file(PRODUCER)

    syntax_valid, syntax_error = syntax_check(source)

    print("PRODUCER")
    print("=" * 100)
    print(f"Producer exists              : {PRODUCER.exists()}")
    print(f"Producer syntax valid        : {syntax_valid}")
    print(f"Producer SHA256              : {source_sha}")

    if not syntax_valid:
        print(f"Syntax error                 : {syntax_error}")

        report = {
            "verdict": "PRODUCER_SYNTAX_INVALID",
            "syntax_error": syntax_error,
            "safety": {
                "producer_executed": False,
                "source_modified": False,
                "production_db_writes": "NONE",
                "network_access": "NONE",
            },
        }

        REPORT.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return

    tree = ast.parse(source, filename=str(PRODUCER))

    assignments = find_report_path_assignment(tree)

    print("=" * 100)
    print("REPORT_PATH RUNTIME RESOLUTION")
    print("=" * 100)
    print(f"report_path assignments       : {len(assignments)}")

    assignment_line = None
    assignment_expression = None
    resolved_path = None

    if len(assignments) == 1:
        assignment = assignments[0]

        assignment_line = assignment.lineno
        assignment_expression = expression_to_text(assignment)

        resolved_path = evaluate_static_path(assignment)

        print(
            f"  line={assignment_line} | "
            f"{assignment_expression}"
        )
    else:
        for node in assignments:
            print(
                f"  line={node.lineno} | "
                f"{expression_to_text(node)}"
            )

    print("=" * 100)
    print("RESOLUTION")
    print("=" * 100)

    expected_path = PROJECT_ROOT / TARGET_NAME

    print(
        f"Expected runtime output path : "
        f"{expected_path}"
    )

    if resolved_path is not None:
        print(
            f"Resolved runtime output path : "
            f"{resolved_path}"
        )
    else:
        print(
            "Resolved runtime output path : "
            "UNRESOLVED"
        )

    deterministic_verified = (
        len(assignments) == 1
        and resolved_path == expected_path
    )

    print(
        f"Deterministic resolution      : "
        f"{deterministic_verified}"
    )

    print("=" * 100)
    print("WRITER BOUNDARY")
    print("=" * 100)

    writer_usages = find_writer_usage(tree)

    print(
        f"Writer references discovered  : "
        f"{len(writer_usages)}"
    )

    for item in writer_usages:
        args = ", ".join(item["arguments"])
        print(
            f"  line={item['line']} | "
            f"type={item['type']} | "
            f"args={args}"
        )

    main_node = find_main(tree)
    main_exists = main_node is not None
    main_guard = find_main_guard(source)

    print("=" * 100)
    print("RUNTIME ENTRY")
    print("=" * 100)
    print(f"main() exists                 : {main_exists}")
    print(f"main guard present            : {main_guard}")
    print(
        "Producer execution            : NOT PERFORMED"
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed             : NO")
    print("Producer imported             : NO")
    print("Eligibility executed         : NO")
    print("Eligibility rebuilt          : NO")
    print("Report regenerated           : NO")
    print("Artifact written             : NO")
    print("Synthetic artifact           : NO")
    print("Production DB writes         : NONE")
    print("Network access               : NONE")
    print("Source modified             : NO")

    report = build_report(
        source_sha=source_sha,
        syntax_valid=syntax_valid,
        assignment_count=len(assignments),
        assignment_line=assignment_line,
        assignment_expression=assignment_expression,
        resolved_path=resolved_path,
        writer_usages=writer_usages,
        main_exists=main_exists,
        main_guard=main_guard,
    )

    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    if deterministic_verified:
        print(
            "HISTORICAL ELIGIBILITY RUNTIME OUTPUT PATH : "
            "RUNTIME_OUTPUT_PATH_RESOLUTION_VERIFIED"
        )
    else:
        print(
            "HISTORICAL ELIGIBILITY RUNTIME OUTPUT PATH : "
            "RUNTIME_OUTPUT_PATH_RESOLUTION_UNVERIFIED"
        )

    print(f"FORENSIC REPORT              : {REPORT}")
    print("=" * 100)


if __name__ == "__main__":
    main()