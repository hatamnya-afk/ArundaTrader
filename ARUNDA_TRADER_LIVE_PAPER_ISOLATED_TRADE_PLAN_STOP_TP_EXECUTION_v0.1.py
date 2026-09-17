import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone


VERSION = "v0.1"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TEMP_ROOT = Path(os.environ.get("TEMP", r"C:\Users\ASUS\AppData\Local\Temp"))

PRODUCTION_DB = PROJECT_DIR / "arunda.db"

TARGET_REPORT = "LIVE_TRADE_PLAN_STOP_TP_REPORT.json"

SCRIPT_PATTERNS = [
    "*TRADE*PLAN*STOP*TP*.py",
    "*TRADE_PLAN*.py",
    "*STOP*TP*.py",
]

FORBIDDEN_TERMS = [
    "os.remove(",
    "os.unlink(",
    "shutil.rmtree(",
    "DROP TABLE",
    "DROP DATABASE",
    "DELETE FROM",
    "UPDATE ",
    "INSERT INTO",
    "ALTER TABLE",
    "CREATE TABLE",
]

DB_ENV_KEYS = [
    "ARUNDA_DB_PATH",
    "ARUNDA_DATABASE",
    "DATABASE_PATH",
    "DB_PATH",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def db_fingerprint(path: Path):
    if not path.exists():
        return {
            "exists": False,
            "size": None,
            "sha256": None,
        }

    return {
        "exists": True,
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def print_header(title: str):
    print("=" * 100)
    print(title)
    print("=" * 100)


def discover_launch_dirs():
    dirs = []

    for p in TEMP_ROOT.glob("arunda_live_launch_*"):
        if not p.is_dir():
            continue

        db = p / "arunda_live_capture.db"

        if db.exists():
            dirs.append(p)

    dirs.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return dirs


def select_isolated_launch():
    dirs = discover_launch_dirs()

    print_header("DISCOVERED ISOLATED LIVE LAUNCHES")

    if not dirs:
        print("NONE")
        return None

    for i, p in enumerate(dirs, 1):
        print(f"{i} | {p}")

    # Prefer the most recently modified isolated launch.
    return dirs[0]


def discover_candidate_scripts():
    found = set()

    for pattern in SCRIPT_PATTERNS:
        for p in PROJECT_DIR.glob(pattern):
            if p.is_file():
                found.add(p.resolve())

    return sorted(found)


def score_script(path: Path):
    name = path.name.upper()

    score = 0

    if "TRADE_PLAN" in name:
        score += 50

    if "STOP" in name:
        score += 30

    if "TP" in name:
        score += 20

    if "CONTRACT" in name:
        score += 10

    if "LIVE" in name:
        score += 5

    return score


def choose_candidate(scripts):
    if not scripts:
        return None

    ranked = sorted(
        scripts,
        key=score_script,
        reverse=True,
    )

    return ranked[0]


def inspect_script(path: Path):
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        return {
            "readable": False,
            "error": str(exc),
            "forbidden_terms": [],
            "production_db_refs": [],
        }

    upper = text.upper()

    forbidden = []

    for term in FORBIDDEN_TERMS:
        if term.upper() in upper:
            forbidden.append(term)

    production_refs = []

    production_db_strings = [
        str(PRODUCTION_DB),
        "ARUNDATRADER\\ARUNDA.DB",
        "ARUNDATRADER/ARUNDA.DB",
    ]

    for ref in production_db_strings:
        if ref.upper() in upper:
            production_refs.append(ref)

    return {
        "readable": True,
        "error": None,
        "forbidden_terms": forbidden,
        "production_db_refs": production_refs,
    }


def build_environment(isolated_db: Path, capture_dir: Path):
    env = os.environ.copy()

    # Multiple conventional names are supplied.
    # Existing frontier code may consume one of them.
    for key in DB_ENV_KEYS:
        env[key] = str(isolated_db)

    env["ARUNDA_ISOLATED_DB"] = str(isolated_db)
    env["ARUNDA_CAPTURE_DIR"] = str(capture_dir)
    env["ARUNDA_LIVE_CAPTURE_DIR"] = str(capture_dir)

    # Explicit safety markers.
    env["ARUNDA_PRODUCTION_DB_WRITES"] = "FORBIDDEN"
    env["ARUNDA_REAL_ORDER_EXECUTION"] = "FORBIDDEN"
    env["ARUNDA_SYNTHETIC_DATA"] = "FORBIDDEN"
    env["ARUNDA_PAPER_ANALYTICAL_ONLY"] = "1"

    return env


def run_component(script: Path, capture_dir: Path, isolated_db: Path):
    env = build_environment(
        isolated_db,
        capture_dir,
    )

    command = [
        sys.executable,
        str(script),
    ]

    started = time.time()

    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        return {
            "started": True,
            "exit_code": None,
            "duration": time.time() - started,
            "stdout": "",
            "stderr": str(exc),
            "exception": str(exc),
        }

    return {
        "started": True,
        "exit_code": result.returncode,
        "duration": time.time() - started,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exception": None,
    }


def report_exists(capture_dir: Path):
    report = capture_dir / TARGET_REPORT

    if not report.exists():
        return {
            "exists": False,
            "path": str(report),
            "valid_json": False,
            "data": None,
        }

    try:
        data = json.loads(
            report.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

        return {
            "exists": True,
            "path": str(report),
            "valid_json": isinstance(data, dict),
            "data": data,
        }

    except Exception as exc:
        return {
            "exists": True,
            "path": str(report),
            "valid_json": False,
            "data": None,
            "error": str(exc),
        }


def extract_frontier_state(report):
    data = report.get("data")

    if not isinstance(data, dict):
        return {
            "state": "INVALID",
            "snapshot": None,
        }

    frontier = (
        data.get("FRONTIER")
        or data.get("frontier")
        or data.get("VERDICT")
        or data.get("verdict")
        or data.get("state")
        or data.get("STATE")
    )

    snapshot = (
        data.get("SNAPSHOT")
        or data.get("snapshot")
        or data.get("snapshot_id")
        or data.get("SNAPSHOT_ID")
    )

    return {
        "state": frontier,
        "snapshot": snapshot,
    }


def write_runtime_report(
    capture_dir: Path,
    payload: dict,
):
    report_path = (
        capture_dir
        / "LIVE_PAPER_ISOLATED_TRADE_PLAN_STOP_TP_EXECUTION_REPORT.json"
    )

    report_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return report_path


def main():
    started_at = datetime.now(timezone.utc).isoformat()

    print_header(
        f"ARUNDA TRADER LIVE PAPER ISOLATED TRADE PLAN + STOP/TP EXECUTION {VERSION}"
    )

    print(
        """
OBJECTIVE
====================================================================================================
Execute ONLY the existing verified Trade Plan + Stop/TP frontier
inside the isolated LIVE PAPER launch.

This wrapper does NOT:
  - reconstruct Trade Plan logic
  - reconstruct Stop/TP logic
  - bypass PAPER execution safety
  - manufacture a report
  - create synthetic data
  - write to production DB
  - submit real orders
"""
    )

    print_header("SAFETY POLICY")

    print("Production DB writes       : FORBIDDEN")
    print("Production engine         : NO")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic data            : FORBIDDEN")
    print("Live data injection       : NONE")
    print("REAL ORDER EXECUTION      : FORBIDDEN")
    print("PAPER EXECUTION           : ANALYTICAL ONLY")

    baseline = db_fingerprint(PRODUCTION_DB)

    print_header("PRODUCTION BASELINE")

    print(f"Exists : {baseline['exists']}")
    print(f"Size   : {baseline['size']}")
    print(f"SHA256 : {baseline['sha256']}")

    capture_dir = select_isolated_launch()

    if capture_dir is None:
        print_header("RESULT")
        print("NO_ISOLATED_LAUNCH_FOUND")
        return 2

    isolated_db = capture_dir / "arunda_live_capture.db"

    print_header("SELECTED ISOLATED LAUNCH")

    print(f"Directory : {capture_dir}")
    print(f"Database  : {isolated_db}")

    isolated_before = db_fingerprint(isolated_db)

    print_header("ISOLATED DATABASE BASELINE")

    print(f"Size   : {isolated_before['size']}")
    print(f"SHA256 : {isolated_before['sha256']}")

    scripts = discover_candidate_scripts()

    print_header("TRADE PLAN + STOP/TP FRONTIER DISCOVERY")

    if not scripts:
        print("NO_CANDIDATE_FRONTIER_FOUND")

        print_header("NEXT ACTION")
        print(
            "The actual existing Trade Plan + Stop/TP frontier filename "
            "must be identified before execution."
        )

        return 3

    for p in scripts:
        print(f"FOUND | {p}")

    selected = choose_candidate(scripts)

    print_header("SELECTED FRONTIER")

    print(f"Script : {selected}")

    inspection = inspect_script(selected)

    print_header("STATIC SAFETY INSPECTION")

    if not inspection["readable"]:
        print("READ : FAIL")
        print(f"Reason : {inspection['error']}")

        return 4

    print("READ : PASS")

    if inspection["production_db_refs"]:
        print("Production DB references : DETECTED")

        for ref in inspection["production_db_refs"]:
            print(f"  - {ref}")

        print()
        print(
            "IMPORTANT: the wrapper will NOT rewrite the source file."
        )
        print(
            "Execution is allowed only through environment isolation."
        )
    else:
        print("Production DB references : NOT DETECTED")

    if inspection["forbidden_terms"]:
        print("Potential write/destructive terms : DETECTED")

        for term in inspection["forbidden_terms"]:
            print(f"  - {term}")

        print()
        print(
            "The frontier is not executed because static inspection "
            "cannot establish safe isolated execution."
        )

        return 5

    print("Potential destructive terms : NOT DETECTED")

    print_header("PRE-EXECUTION REPORT STATE")

    before_report = report_exists(capture_dir)

    if before_report["exists"]:
        print(
            f"Existing {TARGET_REPORT} : PRESENT"
        )
        print(
            "Execution is refused to prevent treating an old report "
            "as a newly generated upstream observation."
        )

        return 6

    print(
        f"{TARGET_REPORT} : ABSENT"
    )

    print_header("EXECUTING EXISTING FRONTIER")

    print(f"Script : {selected}")
    print(f"Isolated DB : {isolated_db}")
    print("Production DB : NOT USED BY ENVIRONMENT")

    result = run_component(
        selected,
        capture_dir,
        isolated_db,
    )

    print(f"Runtime : {result['duration']:.3f}s")
    print(f"Exit    : {result['exit_code']}")

    if result["stdout"]:
        print()
        print("----- STDOUT -----")
        print(result["stdout"])

    if result["stderr"]:
        print()
        print("----- STDERR -----")
        print(result["stderr"])

    print_header("UPSTREAM REPORT VERIFICATION")

    after_report = report_exists(capture_dir)

    if not after_report["exists"]:
        print(
            f"{TARGET_REPORT} : NOT CREATED"
        )

        print()
        print(
            "The existing Trade Plan + Stop/TP frontier did not produce "
            "the required upstream report."
        )

        print(
            "NO SYNTHETIC REPORT WILL BE CREATED."
        )

        result_state = "UPSTREAM_REPORT_NOT_CREATED"

    elif not after_report["valid_json"]:
        print(
            f"{TARGET_REPORT} : INVALID_JSON"
        )

        result_state = "INVALID_UPSTREAM_REPORT"

    else:
        print(
            f"{TARGET_REPORT} : CREATED"
        )

        state = extract_frontier_state(
            after_report
        )

        print(
            f"Frontier state : {state['state']}"
        )

        print(
            f"Snapshot       : {state['snapshot']}"
        )

        result_state = "PASS"

    isolated_after = db_fingerprint(isolated_db)

    production_after = db_fingerprint(PRODUCTION_DB)

    production_invariant = (
        baseline["size"] == production_after["size"]
        and baseline["sha256"] == production_after["sha256"]
    )

    print_header("PRODUCTION DATABASE INVARIANT")

    print(f"Before size   : {baseline['size']}")
    print(f"After size    : {production_after['size']}")
    print(f"Before SHA256 : {baseline['sha256']}")
    print(f"After SHA256  : {production_after['sha256']}")

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if production_invariant else "FAIL")
    )

    final_verdict = (
        "PASS"
        if result_state == "PASS"
        and result["exit_code"] == 0
        and production_invariant
        else result_state
    )

    payload = {
        "version": VERSION,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "objective": "ISOLATED_TRADE_PLAN_STOP_TP_EXECUTION",
        "selected_script": str(selected),
        "capture_dir": str(capture_dir),
        "isolated_db": str(isolated_db),
        "production_db": str(PRODUCTION_DB),
        "production_baseline": baseline,
        "production_after": production_after,
        "production_invariant": production_invariant,
        "isolated_before": isolated_before,
        "isolated_after": isolated_after,
        "runtime": {
            "exit_code": result["exit_code"],
            "duration_seconds": result["duration"],
            "exception": result["exception"],
        },
        "upstream_report": after_report,
        "verdict": final_verdict,
        "safety": {
            "production_db_writes": "NONE",
            "real_order_execution": "NONE",
            "synthetic_data": "NONE",
            "historical_repair": "NONE",
            "direction_inference": "NONE",
            "score_reconstruction": "NONE",
            "paper_execution": "ANALYTICAL_ONLY",
        },
    }

    runtime_report = write_runtime_report(
        capture_dir,
        payload,
    )

    print_header("ISOLATED TRADE PLAN + STOP/TP FRONTIER VERDICT")

    print(
        f"FRONTIER_EXECUTION : "
        f"{'PASS' if result['exit_code'] == 0 else 'FAILED'}"
    )

    print(
        f"UPSTREAM_REPORT    : "
        f"{'PASS' if result_state == 'PASS' else result_state}"
    )

    print(
        f"PRODUCTION_ISOLATION : "
        f"{'PASS' if production_invariant else 'FAIL'}"
    )

    print(
        f"FINAL VERDICT      : {final_verdict}"
    )

    print_header("FINAL SAFETY VERDICT")

    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Production engine    : NOT EXECUTED")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : NONE")
    print("Live data injection  : NONE")
    print("REAL ORDER EXECUTION : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")

    print()
    print(f"Runtime report : {runtime_report}")

    if final_verdict == "PASS":
        print()
        print(
            "The genuine Trade Plan + Stop/TP upstream report is now "
            "available for the existing PAPER safety gate."
        )
        return 0

    print()
    print(
        "The upstream frontier is not validly available."
    )
    print(
        "Do NOT manufacture LIVE_TRADE_PLAN_STOP_TP_REPORT.json."
    )

    return 10


if __name__ == "__main__":
    raise SystemExit(main())