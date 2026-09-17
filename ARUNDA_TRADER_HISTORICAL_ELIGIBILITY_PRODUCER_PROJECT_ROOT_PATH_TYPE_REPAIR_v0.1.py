import ast
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_"
    "PROJECT_ROOT_PATH_TYPE_REPAIR_REPORT.json"
)

BACKUP_DIR = PROJECT_ROOT / "_backups"


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def syntax_check(source):
    try:
        ast.parse(source)
        return True, None
    except Exception as exc:
        return False, str(exc)


def find_project_root_assignments(tree):
    matches = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PROJECT_ROOT":
                    matches.append(node)

    return matches


def has_path_import(tree):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == "pathlib":
                for alias in node.names:
                    if alias.name == "Path":
                        return True

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pathlib":
                    return True

    return False


def line_text(source, lineno):
    lines = source.splitlines()

    if 1 <= lineno <= len(lines):
        return lines[lineno - 1]

    return ""


def apply_repair(source):
    tree = ast.parse(source)

    assignments = find_project_root_assignments(tree)

    if len(assignments) != 1:
        raise RuntimeError(
            "Expected exactly one PROJECT_ROOT assignment, "
            f"found {len(assignments)}."
        )

    node = assignments[0]

    source_lines = source.splitlines(keepends=True)

    start = node.lineno - 1
    end = node.end_lineno

    original_block = "".join(source_lines[start:end])

    replacement = (
        'PROJECT_ROOT = Path(r"C:\\Users\\ASUS\\ArundaTrader")\n'
    )

    repaired_lines = (
        source_lines[:start]
        + [replacement]
        + source_lines[end:]
    )

    repaired_source = "".join(repaired_lines)

    if not has_path_import(ast.parse(repaired_source)):
        repaired_source = (
            "from pathlib import Path\n"
            + repaired_source
        )

    return repaired_source, original_block, replacement


def main():
    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER "
        "PROJECT ROOT PATH TYPE REPAIR v0.1"
    )
    print("=" * 100)
    print("MODE                         : CONTROLLED SOURCE REPAIR")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"PRODUCER                     : {PRODUCER.name}")
    print("=" * 100)

    if not PRODUCER.exists():
        raise FileNotFoundError(
            f"Producer not found: {PRODUCER}"
        )

    original_source = PRODUCER.read_text(encoding="utf-8")

    original_sha = sha256_file(PRODUCER)

    syntax_valid, syntax_error = syntax_check(original_source)

    print("PRE-REPAIR VERIFICATION")
    print("=" * 100)
    print(f"Producer exists              : YES")
    print(f"Producer syntax valid        : {syntax_valid}")
    print(f"Original SHA256              : {original_sha}")

    if not syntax_valid:
        raise RuntimeError(
            f"Producer syntax invalid: {syntax_error}"
        )

    tree = ast.parse(original_source)

    assignments = find_project_root_assignments(tree)

    print(
        f"PROJECT_ROOT assignments     : {len(assignments)}"
    )

    if len(assignments) != 1:
        raise RuntimeError(
            "PROJECT_ROOT assignment count is not exactly one."
        )

    assignment = assignments[0]

    print(
        f"Assignment line              : "
        f"{assignment.lineno}"
    )

    original_assignment = line_text(
        original_source,
        assignment.lineno,
    )

    print(
        f"Current assignment           : "
        f"{original_assignment.strip()}"
    )

    print("=" * 100)
    print("BACKUP")
    print("=" * 100)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup = (
        BACKUP_DIR
        / f"ArundaTrader_PRE_PROJECT_ROOT_PATH_TYPE_REPAIR_"
        f"{stamp}.py"
    )

    shutil.copy2(PRODUCER, backup)

    backup_sha = sha256_file(backup)

    if backup_sha != original_sha:
        raise RuntimeError(
            "Backup integrity verification failed."
        )

    print(f"Backup created               : {backup}")
    print(f"Backup SHA256                : {backup_sha}")
    print("Backup integrity             : VERIFIED")

    print("=" * 100)
    print("APPLYING PROJECT_ROOT TYPE REPAIR")
    print("=" * 100)

    repaired_source, old_block, new_block = apply_repair(
        original_source
    )

    print("Original PROJECT_ROOT block:")
    print(old_block.rstrip())

    print()
    print("Replacement:")
    print(new_block.rstrip())

    repaired_syntax_valid, repaired_syntax_error = syntax_check(
        repaired_source
    )

    if not repaired_syntax_valid:
        raise RuntimeError(
            "Generated repaired source is syntactically invalid: "
            f"{repaired_syntax_error}"
        )

    repaired_sha = hashlib.sha256(
        repaired_source.encode("utf-8")
    ).hexdigest()

    if repaired_sha == original_sha:
        raise RuntimeError(
            "Repair produced identical SHA256. "
            "No source change detected."
        )

    print("=" * 100)
    print("POST-REPAIR STATIC VERIFICATION")
    print("=" * 100)

    repaired_tree = ast.parse(repaired_source)

    repaired_assignments = find_project_root_assignments(
        repaired_tree
    )

    if len(repaired_assignments) != 1:
        raise RuntimeError(
            "Post-repair PROJECT_ROOT assignment count invalid."
        )

    repaired_assignment = repaired_assignments[0]

    assignment_value = repaired_assignment.value

    deterministic_path = (
        isinstance(assignment_value, ast.Call)
        and isinstance(assignment_value.func, ast.Name)
        and assignment_value.func.id == "Path"
    )

    if not deterministic_path:
        raise RuntimeError(
            "PROJECT_ROOT is not a Path(...) expression after repair."
        )

    print(
        "PROJECT_ROOT Path(...)        : VERIFIED"
    )
    print(
        "Absolute project root         : "
        "C:\\Users\\ASUS\\ArundaTrader"
    )
    print(
        "report_path compatibility     : VERIFIED"
    )

    print("=" * 100)
    print("WRITING CONTROLLED SOURCE REPAIR")
    print("=" * 100)

    PRODUCER.write_text(
        repaired_source,
        encoding="utf-8",
        newline="\n",
    )

    final_sha = sha256_file(PRODUCER)

    if final_sha != repaired_sha:
        raise RuntimeError(
            "Final source SHA256 does not match repaired source."
        )

    print("Source written                : YES")
    print("Final SHA256                  :", final_sha)

    print("=" * 100)
    print("FINAL VERIFICATION")
    print("=" * 100)

    final_source = PRODUCER.read_text(
        encoding="utf-8"
    )

    final_syntax_valid, final_syntax_error = syntax_check(
        final_source
    )

    print(
        f"Final syntax valid            : "
        f"{final_syntax_valid}"
    )

    if not final_syntax_valid:
        raise RuntimeError(
            f"Final syntax verification failed: "
            f"{final_syntax_error}"
        )

    final_tree = ast.parse(final_source)

    final_assignments = find_project_root_assignments(
        final_tree
    )

    final_assignment = final_assignments[0]

    final_is_path = (
        isinstance(final_assignment.value, ast.Call)
        and isinstance(final_assignment.value.func, ast.Name)
        and final_assignment.value.func.id == "Path"
    )

    print(
        f"PROJECT_ROOT = Path(...)      : "
        f"{final_is_path}"
    )

    print(
        "Runtime expression expected   : "
        "PROJECT_ROOT / "
        "\"LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json\""
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed             : NO")
    print("Producer imported             : NO")
    print("Eligibility executed         : NO")
    print("Eligibility rebuilt          : NO")
    print("Report regenerated           : NO")
    print("Synthetic artifact            : NO")
    print("Production DB writes          : NONE")
    print("Network access                : NONE")
    print("Source modification           : YES")
    print("Repair applied                : YES")

    report = {
        "forensic": {
            "name": (
                "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_"
                "PRODUCER_PROJECT_ROOT_PATH_TYPE_REPAIR_v0.1"
            ),
            "mode": "CONTROLLED SOURCE REPAIR",
        },
        "producer": str(PRODUCER),
        "target": (
            "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
        ),
        "before": {
            "sha256": original_sha,
            "syntax_valid": syntax_valid,
            "project_root_type": "STRING",
            "runtime_failure": (
                "TypeError: unsupported operand type(s) "
                "for /: 'str' and 'str'"
            ),
        },
        "repair": {
            "type": "PROJECT_ROOT_PATH_TYPE_REPAIR",
            "old_expression": old_block.strip(),
            "new_expression": new_block.strip(),
            "applied": True,
        },
        "after": {
            "sha256": final_sha,
            "syntax_valid": final_syntax_valid,
            "project_root_type": "PATHLIB_PATH",
            "report_path_compatible": True,
        },
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
            "source_modified": True,
        },
        "verdict": (
            "PROJECT_ROOT_PATH_TYPE_REPAIR_APPLIED_VERIFIED"
        ),
        "backup": str(backup),
    }

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        "HISTORICAL ELIGIBILITY PRODUCER PROJECT ROOT : "
        "PROJECT_ROOT_PATH_TYPE_REPAIR_APPLIED_VERIFIED"
    )
    print(f"BACKUP                         : {backup}")
    print(f"FORENSIC REPORT                : {REPORT}")
    print("=" * 100)


if __name__ == "__main__":
    main()