import ast
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER_NAME = "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

PRODUCER_PATH = PROJECT_ROOT / PRODUCER_NAME
BACKUP_DIR = PROJECT_ROOT / "_backups"

FORENSIC_REPORT_NAME = (
    "HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_PATH_DETERMINISTIC_APPLY_REPAIR_REPORT.json"
)

FORENSIC_REPORT_PATH = PROJECT_ROOT / FORENSIC_REPORT_NAME


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_source(path):
    return path.read_text(encoding="utf-8")


def write_source(path, source):
    path.write_text(source, encoding="utf-8", newline="")


def syntax_check(source, filename):
    try:
        ast.parse(source, filename=filename)
        return True, None
    except SyntaxError as exc:
        return False, {
            "line": exc.lineno,
            "column": exc.offset,
            "message": exc.msg,
            "text": exc.text,
        }


def get_line_offsets(source):
    lines = source.splitlines(keepends=True)

    offsets = []
    current = 0

    for line in lines:
        offsets.append(current)
        current += len(line)

    return lines, offsets


def get_report_path_assignments(source):
    tree = ast.parse(source)

    lines, offsets = get_line_offsets(source)

    assignments = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "report_path":
                    start_line = node.lineno
                    end_line = getattr(node, "end_lineno", node.lineno)

                    start_offset = offsets[start_line - 1]

                    if end_line - 1 < len(lines):
                        end_offset = (
                            offsets[end_line - 1]
                            + len(lines[end_line - 1])
                        )
                    else:
                        end_offset = len(source)

                    original_text = source[start_offset:end_offset]

                    assignments.append(
                        {
                            "line": start_line,
                            "end_line": end_line,
                            "start_offset": start_offset,
                            "end_offset": end_offset,
                            "text": original_text,
                        }
                    )

    assignments.sort(key=lambda x: (x["line"], x["end_line"]))

    return assignments


def build_repaired_assignment(original_assignment):
    indentation = ""

    for char in original_assignment["text"]:
        if char in (" ", "\t"):
            indentation += char
        else:
            break

    return (
        f'{indentation}report_path = PROJECT_ROOT / "{TARGET_REPORT}"\n'
    )


def apply_repair(source):
    assignments = get_report_path_assignments(source)

    if len(assignments) != 1:
        raise RuntimeError(
            "Expected exactly one report_path assignment, "
            f"but found {len(assignments)}."
        )

    assignment = assignments[0]

    old_text = assignment["text"]
    new_text = build_repaired_assignment(assignment)

    repaired_source = (
        source[:assignment["start_offset"]]
        + new_text
        + source[assignment["end_offset"]:]
    )

    return (
        repaired_source,
        assignment,
        old_text,
        new_text,
    )


def create_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = (
        BACKUP_DIR
        / f"ArundaTrader_PRE_OUTPUT_PATH_REPAIR_{timestamp}.py"
    )

    shutil.copy2(PRODUCER_PATH, backup_path)

    original_hash = sha256_file(PRODUCER_PATH)
    backup_hash = sha256_file(backup_path)

    if original_hash != backup_hash:
        raise RuntimeError(
            "Backup integrity verification failed: "
            "original and backup SHA256 differ."
        )

    return backup_path, backup_hash


def build_report(
    original_sha256,
    repaired_sha256,
    backup_path,
    assignment,
    old_text,
    new_text,
    pre_syntax,
    post_syntax,
):
    return {
        "timestamp_utc": utc_now(),
        "mode": "CONTROLLED SOURCE REPAIR",
        "project_root": str(PROJECT_ROOT),
        "producer": str(PRODUCER_PATH),
        "target_report": TARGET_REPORT,
        "repair": {
            "type": "DETERMINISTIC_ABSOLUTE_PROJECT_ROOT_PATH",
            "status": "APPLIED",
            "target_expression": 'PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"',
        },
        "pre_repair": {
            "sha256": original_sha256,
            "syntax_valid": pre_syntax,
            "report_path_assignment_line": assignment["line"],
            "report_path_assignment_end_line": assignment["end_line"],
            "original_assignment": old_text.rstrip("\r\n"),
        },
        "repair": {
            "type": "DETERMINISTIC_ABSOLUTE_PROJECT_ROOT_PATH",
            "status": "APPLIED",
            "target_expression": 'PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"',
            "old_assignment": old_text.rstrip("\r\n"),
            "new_assignment": new_text.rstrip("\r\n"),
        },
        "post_repair": {
            "sha256": repaired_sha256,
            "syntax_valid": post_syntax,
        },
        "backup": {
            "path": str(backup_path),
            "sha256": sha256_file(backup_path),
            "integrity": "VERIFIED",
        },
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "synthetic_artifact": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
            "source_modified": True,
            "repair_applied": True,
        },
        "verification": {
            "original_sha256_preserved_in_backup": True,
            "post_repair_sha256_changed": original_sha256 != repaired_sha256,
            "syntax_valid_after_repair": post_syntax,
            "deterministic_report_path": True,
        },
        "verdict": "DETERMINISTIC_OUTPUT_PATH_REPAIR_APPLIED_VERIFIED",
    }


def write_forensic_report(report):
    FORENSIC_REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def print_header():
    print("=" * 100)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH DETERMINISTIC APPLY REPAIR v0.1")
    print("=" * 100)
    print("MODE                         : CONTROLLED SOURCE REPAIR")
    print(f"PROJECT ROOT                : {PROJECT_ROOT}")
    print(f"PRODUCER                    : {PRODUCER_NAME}")
    print(f"TARGET REPORT               : {TARGET_REPORT}")
    print("=" * 100)


def main():
    print_header()

    if not PRODUCER_PATH.exists():
        raise FileNotFoundError(
            f"Producer not found: {PRODUCER_PATH}"
        )

    original_source = read_source(PRODUCER_PATH)

    original_sha256 = sha256_file(PRODUCER_PATH)

    pre_valid, pre_error = syntax_check(
        original_source,
        PRODUCER_NAME,
    )

    print("PRE-REPAIR VERIFICATION")
    print("=" * 100)
    print(f"Producer exists              : {PRODUCER_PATH.exists()}")
    print(f"Producer syntax valid        : {pre_valid}")
    print(f"Original SHA256              : {original_sha256}")

    if not pre_valid:
        print("Syntax error:")
        print(pre_error)
        raise RuntimeError(
            "Producer source is not syntactically valid. "
            "Repair aborted."
        )

    assignments = get_report_path_assignments(original_source)

    print(f"report_path assignments      : {len(assignments)}")

    for item in assignments:
        print(
            f"  line={item['line']} | "
            f"{item['text'].rstrip()}"
        )

    if len(assignments) != 1:
        raise RuntimeError(
            "Repair aborted because report_path assignment count "
            f"is {len(assignments)}, expected exactly 1."
        )

    print("=" * 100)
    print("BACKUP")
    print("=" * 100)

    backup_path, backup_hash = create_backup()

    print(f"Backup created               : {backup_path}")
    print(f"Backup SHA256                : {backup_hash}")
    print("Backup integrity             : VERIFIED")

    print("=" * 100)
    print("APPLYING DETERMINISTIC REPAIR")
    print("=" * 100)

    (
        repaired_source,
        assignment,
        old_text,
        new_text,
    ) = apply_repair(original_source)

    print("Original assignment:")
    print(old_text.rstrip())

    print()
    print("Replacement assignment:")
    print(new_text.rstrip())

    post_valid, post_error = syntax_check(
        repaired_source,
        PRODUCER_NAME,
    )

    if not post_valid:
        print("=" * 100)
        print("POST-REPAIR SYNTAX FAILURE")
        print("=" * 100)
        print(post_error)
        print("NO SOURCE WRITE PERFORMED.")
        raise RuntimeError(
            "Repaired source failed syntax validation. "
            "Original producer remains untouched."
        )

    if repaired_source == original_source:
        raise RuntimeError(
            "Repair produced no source change."
        )

    repaired_sha256 = sha256_bytes(
        repaired_source.encode("utf-8")
    )

    if repaired_sha256 == original_sha256:
        raise RuntimeError(
            "SHA256 did not change after repair."
        )

    print("=" * 100)
    print("POST-REPAIR VERIFICATION")
    print("=" * 100)
    print(f"Syntax valid                 : {post_valid}")
    print(f"Original SHA256              : {original_sha256}")
    print(f"Repaired SHA256              : {repaired_sha256}")
    print(f"SHA256 changed               : {original_sha256 != repaired_sha256}")

    print("=" * 100)
    print("WRITING CONTROLLED SOURCE REPAIR")
    print("=" * 100)

    write_source(PRODUCER_PATH, repaired_source)

    final_sha256 = sha256_file(PRODUCER_PATH)

    if final_sha256 != repaired_sha256:
        raise RuntimeError(
            "Final producer SHA256 does not match repaired source SHA256."
        )

    final_source = read_source(PRODUCER_PATH)

    final_valid, final_error = syntax_check(
        final_source,
        PRODUCER_NAME,
    )

    if not final_valid:
        raise RuntimeError(
            "Final producer syntax validation failed after write."
        )

    final_assignments = get_report_path_assignments(final_source)

    if len(final_assignments) != 1:
        raise RuntimeError(
            "Final producer does not contain exactly one "
            "report_path assignment."
        )

    final_assignment_text = final_assignments[0]["text"].strip()

    expected_assignment = (
        f'report_path = PROJECT_ROOT / "{TARGET_REPORT}"'
    )

    if final_assignment_text != expected_assignment:
        raise RuntimeError(
            "Final deterministic report_path assignment verification failed."
        )

    report = build_report(
        original_sha256=original_sha256,
        repaired_sha256=final_sha256,
        backup_path=backup_path,
        assignment=assignment,
        old_text=old_text,
        new_text=new_text,
        pre_syntax=pre_valid,
        post_syntax=final_valid,
    )

    write_forensic_report(report)

    print("=" * 100)
    print("FINAL VERIFICATION")
    print("=" * 100)
    print("Source repair                 : APPLIED")
    print("Final syntax valid            : YES")
    print("Deterministic output path     : VERIFIED")
    print("Final report_path              :")
    print(f"  {final_assignment_text}")
    print(f"Final SHA256                  : {final_sha256}")

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed             : NO")
    print("Producer imported             : NO")
    print("Eligibility executed          : NO")
    print("Eligibility rebuilt           : NO")
    print("Report regenerated            : NO")
    print("Synthetic artifact            : NO")
    print("Production DB writes          : NONE")
    print("Network access                : NONE")
    print("Source modification            : YES")
    print("Repair applied                : YES")

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        "HISTORICAL ELIGIBILITY OUTPUT PATH : "
        "DETERMINISTIC_OUTPUT_PATH_REPAIR_APPLIED_VERIFIED"
    )
    print(f"BACKUP                         : {backup_path}")
    print(f"FORENSIC REPORT                : {FORENSIC_REPORT_PATH}")
    print("=" * 100)


if __name__ == "__main__":
    main()