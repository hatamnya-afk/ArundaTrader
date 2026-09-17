import hashlib
import json
import os
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
    "RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FORENSIC_REPORT.json"
)

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"


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


def validate_json(path):
    if not path.exists():
        return False, None, "FILE_NOT_FOUND"

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return True, data, None

    except Exception as exc:
        return False, None, str(exc)


def db_fingerprint(path):
    if not path.exists():
        return {
            "exists": False,
            "size": None,
            "sha256": None,
        }

    return {
        "exists": True,
        "size": file_size(path),
        "sha256": sha256_file(path),
    }


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def print_section(title):
    print("=" * 100)
    print(title)
    print("=" * 100)


def main():
    print_section("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER "
        "RUNTIME OUTPUT ARTIFACT GENERATION RETRY FORENSIC v0.1"
    )
    print("=" * 100)

    print("MODE                         : CONTROLLED RUNTIME FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"PRODUCER                     : {PRODUCER.name}")
    print(f"TARGET REPORT                : {TARGET.name}")

    if not PRODUCER.exists():
        raise FileNotFoundError(
            f"Producer does not exist: {PRODUCER}"
        )

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB does not exist: {PRODUCTION_DB}"
        )

    producer_sha_before = sha256_file(PRODUCER)

    print_section("PRE-RUNTIME PRODUCER VERIFICATION")

    print(f"Producer exists              : True")
    print(f"Producer SHA256              : {producer_sha_before}")

    try:
        compile(
            PRODUCER.read_text(encoding="utf-8"),
            str(PRODUCER),
            "exec",
        )
        syntax_valid = True
        syntax_error = None

    except Exception as exc:
        syntax_valid = False
        syntax_error = str(exc)

    print(f"Producer syntax valid        : {syntax_valid}")

    if not syntax_valid:
        print(f"Syntax error                 : {syntax_error}")
        raise RuntimeError(
            "Producer syntax validation failed."
        )

    print_section("TARGET BEFORE RETRY")

    before_exists = TARGET.exists()
    before_size = file_size(TARGET)
    before_sha = sha256_file(TARGET)

    before_json_valid, before_json, before_json_error = (
        validate_json(TARGET)
    )

    print(f"Target exists                : {before_exists}")
    print(f"Target valid JSON            : {before_json_valid}")
    print(f"Target size                  : {before_size}")
    print(f"Target SHA256                : {before_sha}")

    if before_exists:
        print(
            "Existing target detected. "
            "This retry will remove only the canonical target artifact."
        )

    print_section("PRODUCTION DATABASE BASELINE")

    db_before = db_fingerprint(PRODUCTION_DB)

    print(f"Rows invariant               : fingerprint-only")
    print(f"Production DB exists         : {db_before['exists']}")
    print(f"Production DB size           : {db_before['size']}")
    print(f"Production DB SHA256         : {db_before['sha256']}")

    print_section("PRE-RUNTIME TARGET ISOLATION")

    if TARGET.exists():
        TARGET.unlink()

    print(f"Existing target removed      : {not TARGET.exists()}")
    print(f"Canonical target             : {TARGET}")

    if TARGET.exists():
        raise RuntimeError(
            "Target isolation failed."
        )

    print_section("EXECUTING REAL PRODUCER")

    print("Producer execution            : STARTING")
    print("Producer import               : NO")
    print("Execution count               : 1")

    started = utc_now()

    process = subprocess.run(
        [
            sys.executable,
            str(PRODUCER),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    finished = utc_now()

    return_code = process.returncode
    execution_success = return_code == 0

    print(f"Producer return code          : {return_code}")
    print(
        "Producer execution success    : "
        f"{execution_success}"
    )

    print_section("PRODUCER STDOUT")

    if process.stdout:
        print(process.stdout, end="")
    else:
        print("<EMPTY>")

    print_section("PRODUCER STDERR")

    if process.stderr:
        print(process.stderr, end="")
    else:
        print("<EMPTY>")

    print_section("POST-RUNTIME ARTIFACT VERIFICATION")

    target_exists = TARGET.exists()
    target_size = file_size(TARGET)
    target_sha = sha256_file(TARGET)

    target_json_valid, target_json, target_json_error = (
        validate_json(TARGET)
    )

    print(f"Target exists                : {target_exists}")
    print(f"Target valid JSON            : {target_json_valid}")
    print(f"Target size                  : {target_size}")
    print(f"Target SHA256                : {target_sha}")

    if target_json_error:
        print(
            f"JSON validation error        : "
            f"{target_json_error}"
        )

    print_section("TARGET PATH VERIFICATION")

    expected_target = (
        PROJECT_ROOT
        / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
    )

    resolved_target = TARGET.resolve()

    print(f"Expected path                : {expected_target}")
    print(f"Resolved path                : {resolved_target}")
    print(
        "Canonical path match         : "
        f"{resolved_target == expected_target.resolve()}"
    )

    print_section("ARTIFACT CONTENT EVIDENCE")

    artifact_keys = []

    if isinstance(target_json, dict):
        artifact_keys = sorted(target_json.keys())

        print(
            f"Top-level JSON object        : True"
        )
        print(
            f"Top-level keys count         : "
            f"{len(artifact_keys)}"
        )

        for key in artifact_keys:
            print(f"  - {key}")

    elif target_json is not None:
        print(
            f"Top-level JSON object        : False"
        )
        print(
            f"JSON type                   : "
            f"{type(target_json).__name__}"
        )

    else:
        print("Artifact content             : UNAVAILABLE")

    print_section("PRODUCTION DATABASE INVARIANT")

    db_after = db_fingerprint(PRODUCTION_DB)

    db_size_same = (
        db_before["size"] == db_after["size"]
    )

    db_sha_same = (
        db_before["sha256"] == db_after["sha256"]
    )

    db_invariant = (
        db_before["exists"]
        and db_after["exists"]
        and db_size_same
        and db_sha_same
    )

    print(
        f"Before size                  : "
        f"{db_before['size']}"
    )
    print(
        f"After size                   : "
        f"{db_after['size']}"
    )
    print(
        f"Before SHA256                : "
        f"{db_before['sha256']}"
    )
    print(
        f"After SHA256                 : "
        f"{db_after['sha256']}"
    )
    print(
        f"Size invariant               : "
        f"{db_size_same}"
    )
    print(
        f"SHA256 invariant             : "
        f"{db_sha_same}"
    )
    print(
        "PRODUCTION DB INVARIANT      : "
        f"{'PASS' if db_invariant else 'FAIL'}"
    )

    print_section("SOURCE INTEGRITY")

    producer_sha_after = sha256_file(PRODUCER)

    source_modified = (
        producer_sha_before != producer_sha_after
    )

    print(
        f"Producer SHA256 before       : "
        f"{producer_sha_before}"
    )
    print(
        f"Producer SHA256 after        : "
        f"{producer_sha_after}"
    )
    print(
        f"Producer source modified     : "
        f"{source_modified}"
    )

    print_section("RUNTIME SAFETY")

    print("Producer executed             : YES")
    print("Producer imported             : NO")
    print("Eligibility executed          : YES")
    print("Eligibility rebuilt           : NO")
    print(
        "Report regenerated            : "
        f"{target_exists and target_json_valid}"
    )
    print("Synthetic artifact            : NO")
    print(
        "Production source modified    : "
        f"{source_modified}"
    )
    print("Production DB writes          : NOT BY FORENSIC SCRIPT")
    print("Network access                : DELEGATED TO PRODUCER")

    artifact_success = (
        return_code == 0
        and target_exists
        and target_json_valid
        and target_size is not None
        and target_size > 0
        and db_invariant
        and not source_modified
        and resolved_target == expected_target.resolve()
    )

    if artifact_success:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_VERIFIED"
        )
    elif target_exists and target_json_valid:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_GENERATED_WITH_RUNTIME_WARNINGS"
        )
    else:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FAILED"
        )

    report_data = {
        "forensic": {
            "name": (
                "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_"
                "RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FORENSIC_v0.1"
            ),
            "mode": "CONTROLLED RUNTIME FORENSIC",
            "started_utc": started,
            "finished_utc": finished,
        },
        "producer": {
            "path": str(PRODUCER),
            "sha256_before": producer_sha_before,
            "sha256_after": producer_sha_after,
            "source_modified": source_modified,
            "return_code": return_code,
            "execution_success": execution_success,
        },
        "target": {
            "path": str(TARGET),
            "exists_before": before_exists,
            "exists_after": target_exists,
            "valid_json": target_json_valid,
            "size": target_size,
            "sha256": target_sha,
            "json_error": target_json_error,
            "canonical_path_match": (
                resolved_target == expected_target.resolve()
            ),
            "top_level_keys": artifact_keys,
        },
        "production_db": {
            "before": db_before,
            "after": db_after,
            "size_same": db_size_same,
            "sha256_same": db_sha_same,
            "invariant": db_invariant,
        },
        "execution": {
            "producer_executed": True,
            "producer_imported": False,
            "eligibility_executed": True,
            "eligibility_rebuilt": False,
            "report_regenerated": (
                target_exists and target_json_valid
            ),
            "synthetic_artifact": False,
            "forensic_script_db_writes": False,
        },
        "stdout": process.stdout,
        "stderr": process.stderr,
        "verdict": verdict,
    }

    REPORT.write_text(
        json.dumps(
            report_data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print_section("FINAL VERDICT")

    print(
        "HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT : "
        f"{verdict}"
    )
    print(
        f"TARGET ARTIFACT               : {TARGET}"
    )
    print(
        f"TARGET EXISTS                 : {target_exists}"
    )
    print(
        f"TARGET VALID JSON             : {target_json_valid}"
    )
    print(
        f"TARGET SIZE                   : {target_size}"
    )
    print(
        f"TARGET SHA256                 : {target_sha}"
    )
    print(
        f"PRODUCTION DB INVARIANT       : "
        f"{'PASS' if db_invariant else 'FAIL'}"
    )
    print(
        f"FORENSIC REPORT               : {REPORT}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()