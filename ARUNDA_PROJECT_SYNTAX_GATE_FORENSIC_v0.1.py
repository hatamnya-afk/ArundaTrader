import ast
import hashlib
import json
import py_compile
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

SCRIPT_NAME = "ARUNDA_PROJECT_SYNTAX_GATE_FORENSIC_v0.1.py"
ARTIFACT_NAME = "ARUNDA_PROJECT_SYNTAX_GATE_FORENSIC_v0.1.json"
REPORT_NAME = "ARUNDA_PROJECT_SYNTAX_GATE_FORENSIC_v0.1.txt"

ARTIFACT_PATH = PROJECT_DIR / ARTIFACT_NAME
REPORT_PATH = PROJECT_DIR / REPORT_NAME


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_python_files():
    files = []

    for path in PROJECT_DIR.rglob("*.py"):
        if "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES" in path.parts:
            continue
        if not path.is_file():
            continue

        if any(part in {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            "site-packages",
        } for part in path.parts):
            continue

        if path.name == SCRIPT_NAME:
            continue

        files.append(path)

    return sorted(files, key=lambda p: str(p).lower())


def syntax_check(path):
    result = {
        "file": str(path),
        "relative_file": str(path.relative_to(PROJECT_DIR)),
        "status": "PASS",
        "error_type": None,
        "message": None,
        "line": None,
        "column": None,
        "offset": None,
        "text": None,
    }

    try:
        source = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        result["status"] = "FAIL"
        result["error_type"] = "UnicodeDecodeError"
        result["message"] = str(exc)
        return result
    except Exception as exc:
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
        result["message"] = str(exc)
        return result

    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        result["status"] = "FAIL"
        result["error_type"] = "SyntaxError"
        result["message"] = exc.msg
        result["line"] = exc.lineno
        result["column"] = exc.offset
        result["text"] = exc.text.strip() if exc.text else None
        return result
    except Exception as exc:
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
        result["message"] = str(exc)
        return result

    try:
        py_compile.compile(
            str(path),
            cfile=str(PROJECT_DIR / "__syntax_gate_tmp__.pyc"),
            doraise=True,
        )
    except py_compile.PyCompileError as exc:
        result["status"] = "FAIL"
        result["error_type"] = "PyCompileError"
        result["message"] = str(exc)

        syntax = exc.exc_value
        if isinstance(syntax, SyntaxError):
            result["line"] = syntax.lineno
            result["column"] = syntax.offset
            result["text"] = (
                syntax.text.strip()
                if syntax.text
                else None
            )

        return result
    except Exception as exc:
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
        result["message"] = str(exc)
        return result

    return result


def cleanup_temp():
    candidates = [
        PROJECT_DIR / "__syntax_gate_tmp__.pyc",
        PROJECT_DIR / "__syntax_gate_tmp__.py",
    ]

    for path in candidates:
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


def build_report(results, started_at, finished_at):
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed

    lines = []

    lines.append("=" * 90)
    lines.append("ARUNDA PROJECT SYNTAX GATE FORENSIC v0.1")
    lines.append("=" * 90)
    lines.append(f"Project Directory : {PROJECT_DIR}")
    lines.append(f"Started UTC      : {started_at}")
    lines.append(f"Finished UTC     : {finished_at}")
    lines.append("Mode             : READ ONLY")
    lines.append("Database         : NOT USED")
    lines.append("Network          : FORBIDDEN")
    lines.append("Production Run   : NOT PERFORMED")
    lines.append("File Modification: FORBIDDEN")
    lines.append("-" * 90)
    lines.append("")

    lines.append("=" * 90)
    lines.append("SYNTAX INVENTORY")
    lines.append("=" * 90)
    lines.append(f"Python Files Scanned : {total}")
    lines.append(f"Syntax PASS          : {passed}")
    lines.append(f"Syntax FAIL          : {failed}")
    lines.append("")

    if failed:
        lines.append("=" * 90)
        lines.append("FAILURES")
        lines.append("=" * 90)

        for index, result in enumerate(
            [r for r in results if r["status"] == "FAIL"],
            start=1,
        ):
            lines.append("-" * 90)
            lines.append(f"FAILURE #{index}")
            lines.append(f"FILE       : {result['relative_file']}")
            lines.append(f"ERROR TYPE : {result['error_type']}")
            lines.append(f"MESSAGE    : {result['message']}")

            if result["line"] is not None:
                lines.append(f"LINE       : {result['line']}")

            if result["column"] is not None:
                lines.append(f"COLUMN     : {result['column']}")

            if result["text"]:
                lines.append(f"SOURCE     : {result['text']}")

        lines.append("")

    lines.append("=" * 90)
    lines.append("FORENSIC STATUS")
    lines.append("=" * 90)

    if failed:
        status = "LAUNCH_SYNTAX_GATE_BLOCKED"
    else:
        status = "LAUNCH_SYNTAX_GATE_PASSED"

    lines.append(f"FORENSIC STATUS : {status}")
    lines.append("PREDICTIVE CLAIM : NOT ESTABLISHED")
    lines.append("DATABASE WRITE   : NOT PERFORMED")
    lines.append("NETWORK          : NOT USED")
    lines.append("PRODUCTION RUN   : NOT PERFORMED")
    lines.append("")

    lines.append("=" * 90)
    lines.append("NEXT INTERPRETATION")
    lines.append("=" * 90)

    if failed:
        lines.append(
            "Syntax failures exist. Resolve or explicitly quarantine "
            "non-production forensic/tooling files before launch."
        )
        lines.append(
            "No database cleanup, universe rebuild, symbol deletion, "
            "or production mutation is authorized by this artifact."
        )
    else:
        lines.append(
            "All scanned Python files passed syntax compilation."
        )
        lines.append(
            "Proceed to LIVE DATA BOUNDARY / LAUNCH READINESS."
        )

    lines.append("")
    lines.append("=" * 90)
    lines.append("ARTIFACT")
    lines.append("=" * 90)
    lines.append(f"Artifact : {ARTIFACT_PATH}")
    lines.append(f"Report   : {REPORT_PATH}")
    lines.append("=" * 90)

    return "\n".join(lines)


def main():
    started_at = utc_now()

    print("=" * 90)
    print("ARUNDA PROJECT SYNTAX GATE FORENSIC v0.1")
    print("=" * 90)
    print(f"Project Directory : {PROJECT_DIR}")
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : FORBIDDEN")
    print("Production Run    : NOT PERFORMED")
    print("File Modification : FORBIDDEN")
    print("-" * 90)

    if not PROJECT_DIR.exists():
        print(f"ERROR: Project directory does not exist: {PROJECT_DIR}")
        sys.exit(2)

    python_files = collect_python_files()

    print("")
    print("=" * 90)
    print("SCANNING")
    print("=" * 90)
    print(f"Python files found : {len(python_files)}")
    print("")

    results = []

    for index, path in enumerate(python_files, start=1):
        result = syntax_check(path)
        results.append(result)

        marker = "PASS" if result["status"] == "PASS" else "FAIL"

        print(
            f"[{index:04d}/{len(python_files):04d}] "
            f"{marker:<4} "
            f"{result['relative_file']}"
        )

        if result["status"] == "FAIL":
            print(
                f"       {result['error_type']}: "
                f"{result['message']}"
            )

            if result["line"] is not None:
                print(
                    f"       line={result['line']} "
                    f"column={result['column']}"
                )

    cleanup_temp()

    finished_at = utc_now()

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed

    artifact = {
        "artifact": ARTIFACT_NAME,
        "version": "v0.1",
        "project_directory": str(PROJECT_DIR),
        "mode": "READ_ONLY",
        "database_used": False,
        "database_write": False,
        "network_used": False,
        "production_run": False,
        "file_modification": False,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "inventory": {
            "python_files_scanned": total,
            "syntax_pass": passed,
            "syntax_fail": failed,
        },
        "status": (
            "LAUNCH_SYNTAX_GATE_BLOCKED"
            if failed
            else "LAUNCH_SYNTAX_GATE_PASSED"
        ),
        "results": results,
    }

    ARTIFACT_PATH.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_report(
        results,
        started_at,
        finished_at,
    )

    REPORT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    artifact_hash = sha256_file(ARTIFACT_PATH)

    print("")
    print(report)
    print(f"SHA256   : {artifact_hash}")
    print("=" * 90)

    if failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
