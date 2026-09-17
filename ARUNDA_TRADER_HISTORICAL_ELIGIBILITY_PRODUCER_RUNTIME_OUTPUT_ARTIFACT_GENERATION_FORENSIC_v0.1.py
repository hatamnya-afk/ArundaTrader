import ast
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_"
    "RUNTIME_OUTPUT_ARTIFACT_GENERATION_FORENSIC_REPORT.json"
)

BACKUP_DIR = PROJECT_ROOT / "_backups"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    if not path.exists():
        return None

    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def file_size(path):
    if not path.exists():
        return None

    return path.stat().st_size


def syntax_check(path):
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        return True, None
    except Exception as exc:
        return False, str(exc)


def verify_report(path):
    result = {
        "exists": path.exists(),
        "valid_json": False,
        "size": file_size(path),
        "sha256": sha256_file(path),
        "top_level_type": None,
        "keys": [],
        "error": None,
    }

    if not path.exists():
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        result["valid_json"] = True
        result["top_level_type"] = type(data).__name__

        if isinstance(data, dict):
            result["keys"] = list(data.keys())

    except Exception as exc:
        result["error"] = str(exc)

    return result


def backup_existing_target():
    if not TARGET.exists():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup = (
        BACKUP_DIR
        / f"ArundaTrader_PRE_RUNTIME_ARTIFACT_GENERATION_"
        f"{stamp}.json"
    )

    shutil.copy2(TARGET, backup)

    original_hash = sha256_file(TARGET)
    backup_hash = sha256_file(backup)

    if original_hash != backup_hash:
        raise RuntimeError(
            "Existing target backup integrity verification failed."
        )

    return {
        "path": str(backup),
        "sha256": backup_hash,
        "size": file_size(backup),
        "integrity": "VERIFIED",
    }


def remove_existing_target():
    """
    Remove only the existing target artifact before runtime execution.

    This ensures that a post-run artifact cannot be mistaken for an old
    artifact. If an existing artifact exists, it has already been backed up.
    """

    if TARGET.exists():
        TARGET.unlink()


def run_producer():
    """
    Execute the real producer as a subprocess.

    The producer is NOT imported.
    The producer is executed only once.
    """

    command = [
        sys.executable,
        str(PRODUCER),
    ]

    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return {
        "command": command,
        "returncode": completed.returncode,
        "success": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_report(
    syntax_valid,
    syntax_error,
    producer_sha_before,
    producer_sha_after,
    target_before,
    target_after,
    backup_info,
    execution,
):
    artifact_created = (
        target_after["exists"]
        and target_after["valid_json"]
    )

    artifact_changed = (
        target_before["sha256"] != target_after["sha256"]
    )

    producer_unchanged = (
        producer_sha_before == producer_sha_after
    )

    runtime_success = execution["success"]

    if artifact_created and runtime_success:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_GENERATED_AND_VERIFIED"
        )
    elif target_after["exists"] and target_after["valid_json"]:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_PRESENT_BUT_EXECUTION_FAILED"
        )
    elif runtime_success and not target_after["exists"]:
        verdict = (
            "PRODUCER_EXECUTED_BUT_RUNTIME_ARTIFACT_NOT_GENERATED"
        )
    else:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_GENERATION_FAILED"
        )

    return {
        "forensic": {
            "name": (
                "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_"
                "PRODUCER_RUNTIME_OUTPUT_ARTIFACT_GENERATION_FORENSIC_v0.1"
            ),
            "mode": "CONTROLLED RUNTIME FORENSIC",
            "timestamp_utc": utc_now(),
        },
        "project": {
            "project_root": str(PROJECT_ROOT),
            "producer": str(PRODUCER),
            "target": str(TARGET),
        },
        "producer": {
            "exists": PRODUCER.exists(),
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "sha256_before": producer_sha_before,
            "sha256_after": producer_sha_after,
            "source_unchanged": producer_unchanged,
        },
        "target_before_execution": target_before,
        "target_after_execution": target_after,
        "backup": backup_info,
        "execution": {
            "executed": True,
            "imported": False,
            "returncode": execution["returncode"],
            "success": execution["success"],
            "stdout": execution["stdout"],
            "stderr": execution["stderr"],
        },
        "artifact_verification": {
            "artifact_created": artifact_created,
            "artifact_changed": artifact_changed,
            "valid_json": target_after["valid_json"],
            "canonical_path": str(TARGET),
        },
        "safety": {
            "producer_executed": True,
            "producer_imported": False,
            "eligibility_executed": True,
            "eligibility_rebuilt": False,
            "report_regenerated": artifact_created,
            "synthetic_artifact": False,
            "production_source_modified": False,
            "production_db_writes": "NOT_PERFORMED_BY_FORENSIC_SCRIPT",
            "network_access": "DELEGATED_TO_PRODUCER",
            "target_artifact_write": (
                "PRODUCER_WRITE_ONLY"
                if artifact_created
                else "NONE"
            ),
        },
        "verdict": verdict,
    }


def print_header():
    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER "
        "RUNTIME OUTPUT ARTIFACT GENERATION FORENSIC v0.1"
    )
    print("=" * 100)
    print("MODE                         : CONTROLLED RUNTIME FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"PRODUCER                     : {PRODUCER.name}")
    print(f"TARGET REPORT                : {TARGET.name}")
    print("=" * 100)


def main():
    print_header()

    if not PRODUCER.exists():
        raise FileNotFoundError(
            f"Producer not found: {PRODUCER}"
        )

    syntax_valid, syntax_error = syntax_check(PRODUCER)

    producer_sha_before = sha256_file(PRODUCER)

    print("PRE-RUNTIME PRODUCER VERIFICATION")
    print("=" * 100)
    print(f"Producer exists              : {PRODUCER.exists()}")
    print(f"Producer syntax valid        : {syntax_valid}")
    print(f"Producer SHA256              : {producer_sha_before}")

    if not syntax_valid:
        print(f"Syntax error                 : {syntax_error}")
        raise RuntimeError(
            "Producer syntax is invalid. Runtime execution aborted."
        )

    target_before = verify_report(TARGET)

    print("=" * 100)
    print("TARGET BEFORE EXECUTION")
    print("=" * 100)
    print(f"Target exists                : {target_before['exists']}")
    print(f"Target valid JSON             : {target_before['valid_json']}")
    print(f"Target size                  : {target_before['size']}")
    print(f"Target SHA256                : {target_before['sha256']}")

    print("=" * 100)
    print("BACKUP")
    print("=" * 100)

    backup_info = backup_existing_target()

    if backup_info:
        print(
            f"Backup created               : "
            f"{backup_info['path']}"
        )
        print(
            f"Backup SHA256                : "
            f"{backup_info['sha256']}"
        )
        print(
            f"Backup integrity             : "
            f"{backup_info['integrity']}"
        )
    else:
        print("Existing target              : NONE")
        print("Backup required              : NO")

    print("=" * 100)
    print("PRE-RUNTIME TARGET ISOLATION")
    print("=" * 100)

    remove_existing_target()

    if TARGET.exists():
        raise RuntimeError(
            "Unable to isolate existing target artifact."
        )

    print("Existing target removed      : YES")
    print("Canonical target              : CLEAN")

    print("=" * 100)
    print("EXECUTING REAL PRODUCER")
    print("=" * 100)
    print("Producer execution            : STARTING")
    print("Producer import               : NO")
    print("Execution count               : 1")

    execution = run_producer()

    print(
        f"Producer return code          : "
        f"{execution['returncode']}"
    )
    print(
        f"Producer execution success    : "
        f"{execution['success']}"
    )

    if execution["stdout"]:
        print("=" * 100)
        print("PRODUCER STDOUT")
        print("=" * 100)
        print(execution["stdout"])

    if execution["stderr"]:
        print("=" * 100)
        print("PRODUCER STDERR")
        print("=" * 100)
        print(execution["stderr"])

    target_after = verify_report(TARGET)

    producer_sha_after = sha256_file(PRODUCER)

    print("=" * 100)
    print("POST-RUNTIME ARTIFACT VERIFICATION")
    print("=" * 100)
    print(f"Target exists                : {target_after['exists']}")
    print(
        f"Target valid JSON             : "
        f"{target_after['valid_json']}"
    )
    print(
        f"Target size                  : "
        f"{target_after['size']}"
    )
    print(
        f"Target SHA256                : "
        f"{target_after['sha256']}"
    )

    if target_after["keys"]:
        print("Top-level JSON keys          :")
        for key in target_after["keys"]:
            print(f"  - {key}")

    print("=" * 100)
    print("SOURCE INTEGRITY")
    print("=" * 100)
    print(
        f"Producer SHA256 before        : "
        f"{producer_sha_before}"
    )
    print(
        f"Producer SHA256 after         : "
        f"{producer_sha_after}"
    )
    print(
        "Producer source modified      : "
        f"{producer_sha_before != producer_sha_after}"
    )

    report = build_report(
        syntax_valid=syntax_valid,
        syntax_error=syntax_error,
        producer_sha_before=producer_sha_before,
        producer_sha_after=producer_sha_after,
        target_before=target_before,
        target_after=target_after,
        backup_info=backup_info,
        execution=execution,
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed             : YES")
    print("Producer imported             : NO")
    print("Eligibility executed         : YES")
    print("Eligibility rebuilt          : NO")
    print(
        "Report regenerated           : "
        f"{target_after['exists']}"
    )
    print("Synthetic artifact           : NO")
    print(
        "Production source modified   : "
        f"{producer_sha_before != producer_sha_after}"
    )
    print("Production DB writes         : NOT BY FORENSIC SCRIPT")
    print("Network access               : DELEGATED TO PRODUCER")

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        "HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT : "
        f"{report['verdict']}"
    )
    print(
        f"TARGET ARTIFACT               : {TARGET}"
    )
    print(
        f"FORENSIC REPORT                : {REPORT}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()