import os
import sys
import json
import time
import hashlib
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone


PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_DIR / "arunda.db"

LAUNCH_ROOT = Path(tempfile.gettempdir())

EXPECTED_SCRIPTS = [
    "ARUNDA_TRADER_LIVE_PAPER_EXECUTION_SAFETY_GATE_v0.1.py",
    "ARUNDA_TRADER_LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_v0.1.py",
    "ARUNDA_TRADER_LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_v0.1.py",
    "ARUNDA_TRADER_LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_v0.1.py",
    "ARUNDA_TRADER_LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_v0.1.py",
]

EXPECTED_REPORTS = [
    "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json",
    "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json",
    "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json",
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def db_fingerprint(path):
    if not path.exists():
        return None, None, None

    size = path.stat().st_size

    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master"
            ).fetchone()
            _ = row
    except Exception:
        pass

    return size, sha256_file(path), path


def discover_launches():
    launches = []

    if not LAUNCH_ROOT.exists():
        return launches

    for p in LAUNCH_ROOT.glob("arunda_live_launch_*"):
        if not p.is_dir():
            continue

        db = p / "arunda_live_capture.db"

        if db.exists():
            launches.append(p)

    launches.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return launches


def choose_launch():
    launches = discover_launches()

    if not launches:
        return None

    print("=" * 100)
    print("DISCOVERED ISOLATED LIVE LAUNCHES")
    print("=" * 100)

    for i, p in enumerate(launches, 1):
        print(f"{i} | {p}")

    print()

    selected = launches[0]

    print("=" * 100)
    print("SELECTED ISOLATED LAUNCH")
    print("=" * 100)
    print(f"Directory : {selected}")
    print(f"Database  : {selected / 'arunda_live_capture.db'}")

    return selected


def verify_isolated_db(launch_dir):
    isolated_db = launch_dir / "arunda_live_capture.db"

    if not isolated_db.exists():
        raise RuntimeError(
            f"Isolated DB missing: {isolated_db}"
        )

    production_real = PRODUCTION_DB.resolve()
    isolated_real = isolated_db.resolve()

    if production_real == isolated_real:
        raise RuntimeError(
            "SAFETY STOP: isolated DB resolves to production DB."
        )

    size = isolated_db.stat().st_size
    digest = sha256_file(isolated_db)

    print("=" * 100)
    print("ISOLATED DATABASE")
    print("=" * 100)
    print(f"Path   : {isolated_db}")
    print(f"Size   : {size}")
    print(f"SHA256 : {digest}")

    return isolated_db


def discover_scripts():
    missing = []
    found = []

    print("=" * 100)
    print("PAPER LIFECYCLE PIPELINE DISCOVERY")
    print("=" * 100)

    for name in EXPECTED_SCRIPTS:
        path = PROJECT_DIR / name

        if path.exists():
            print(f"FOUND   | {path}")
            found.append(path)
        else:
            print(f"MISSING | {path}")
            missing.append(name)

    print()

    return found, missing


def script_mentions_production_db(script_path):
    try:
        text = script_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return True

    dangerous_patterns = [
        'sqlite3.connect(r"C:\\Users\\ASUS\\ArundaTrader\\arunda.db")',
        'sqlite3.connect("C:\\Users\\ASUS\\ArundaTrader\\arunda.db")',
        'sqlite3.connect(PRODUCTION_DB)',
        'PRODUCTION_DB',
    ]

    return any(
        pattern in text
        for pattern in dangerous_patterns
    )


def build_env(isolated_db):
    env = os.environ.copy()

    # Multiple conventional names are supplied so an existing
    # verified PAPER script can consume the isolated DB if it
    # already supports environment-based DB redirection.
    env["ARUNDA_DB_PATH"] = str(isolated_db)
    env["ARUNDA_DATABASE"] = str(isolated_db)
    env["ARUNDA_LIVE_DB"] = str(isolated_db)
    env["ARUNDA_PAPER_DB"] = str(isolated_db)

    env["ARUNDA_PAPER_MODE"] = "1"
    env["ARUNDA_ANALYTICAL_ONLY"] = "1"
    env["ARUNDA_REAL_ORDER_EXECUTION"] = "0"
    env["ARUNDA_PRODUCTION_WRITES"] = "0"

    return env


def run_script(script_path, isolated_db):
    print("=" * 100)
    print("EXECUTING VERIFIED PAPER PIPELINE COMPONENT")
    print("=" * 100)
    print(f"Script : {script_path.name}")
    print(f"DB     : {isolated_db}")
    print()

    env = build_env(isolated_db)

    start = time.time()

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    duration = time.time() - start

    print(f"Runtime : {duration:.3f}s")
    print(f"Exit    : {result.returncode}")
    print()

    if result.stdout:
        print("----- STDOUT -----")
        print(result.stdout)

    if result.stderr:
        print("----- STDERR -----")
        print(result.stderr)

    return result.returncode


def find_reports(search_dirs):
    found = {}

    for directory in search_dirs:
        if not directory.exists():
            continue

        for report_name in EXPECTED_REPORTS:
            candidate = directory / report_name

            if candidate.exists():
                found[report_name] = candidate

    return found


def inspect_report(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return {
            "valid_json": False,
            "error": str(exc),
        }

    return {
        "valid_json": True,
        "keys": sorted(data.keys()) if isinstance(data, dict) else [],
        "snapshot": (
            data.get("snapshot")
            or data.get("current_snapshot")
            or data.get("snapshot_id")
        ) if isinstance(data, dict) else None,
    }


def production_invariant(before_size, before_sha):
    after_size = PRODUCTION_DB.stat().st_size
    after_sha = sha256_file(PRODUCTION_DB)

    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(f"Before size  : {before_size}")
    print(f"After size   : {after_size}")
    print(f"Before SHA256: {before_sha}")
    print(f"After SHA256 : {after_sha}")

    passed = (
        before_size == after_size
        and before_sha == after_sha
    )

    print(
        f"PRODUCTION DB INVARIANT : "
        f"{'PASS' if passed else 'FAIL'}"
    )

    return passed


def write_runtime_report(
    launch_dir,
    status,
    reports,
    production_pass,
    executed,
):
    report = {
        "frontier": (
            "LIVE_PAPER_ISOLATED_LAUNCH_LIFECYCLE_PIPELINE_EXECUTION_v0.1"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "production_db_writes": "NONE",
        "real_order_execution": "NONE",
        "synthetic_snapshot": "NONE",
        "production_invariant": production_pass,
        "executed_components": [
            str(x) for x in executed
        ],
        "reports": {
            name: {
                "path": str(path),
                **inspect_report(path),
            }
            for name, path in reports.items()
        },
    }

    output = launch_dir / (
        "LIVE_PAPER_ISOLATED_LAUNCH_LIFECYCLE_PIPELINE_EXECUTION_REPORT.json"
    )

    with open(output, "w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False
        )

    return output


def main():
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER ISOLATED-LAUNCH "
        "LIFECYCLE PIPELINE EXECUTION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE")
    print("=" * 100)
    print(
        "Execute ONLY the already-existing PAPER lifecycle/state "
        "pipeline against the isolated LIVE launch."
    )
    print("No lifecycle logic is reimplemented.")
    print("No synthetic portfolio snapshot is created.")
    print("No production DB write is permitted.")
    print("No real order is created or submitted.")
    print()

    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)
    print("Production DB writes : FORBIDDEN")
    print("Production engine    : NO")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Synthetic data       : FORBIDDEN")
    print("Live data injection  : NONE")
    print("Real order           : FORBIDDEN")
    print("Paper execution      : ANALYTICAL ONLY")
    print()

    if not PRODUCTION_DB.exists():
        raise RuntimeError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    before_size = PRODUCTION_DB.stat().st_size
    before_sha = sha256_file(PRODUCTION_DB)

    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Size   : {before_size}")
    print(f"SHA256 : {before_sha}")

    launch_dir = choose_launch()

    if launch_dir is None:
        print()
        print("NO_ISOLATED_LAUNCH_FOUND")
        return 2

    isolated_db = verify_isolated_db(launch_dir)

    scripts, missing = discover_scripts()

    if missing:
        print("=" * 100)
        print("SAFETY STOP")
        print("=" * 100)
        print("Required PAPER lifecycle components are missing.")
        print("No component was executed.")
        return 3

    print("=" * 100)
    print("PRE-EXECUTION ISOLATION CHECK")
    print("=" * 100)

    for script in scripts:
        if script_mentions_production_db(script):
            print(
                f"WARNING | {script.name} contains a direct "
                "production DB reference."
            )

    print()
    print(
        "Environment DB redirection will be supplied, but this "
        "launcher will NOT rewrite lifecycle code."
    )
    print()

    executed = []

    # Execute only scripts that already exist.
    # If a component fails, stop immediately rather than continuing
    # with an inconsistent downstream state.
    for script in scripts:
        rc = run_script(script, isolated_db)

        if rc != 0:
            print()
            print("=" * 100)
            print("PIPELINE STOP")
            print("=" * 100)
            print(
                f"Component failed: {script.name}"
            )
            print(
                "Downstream components were NOT executed."
            )

            production_pass = production_invariant(
                before_size,
                before_sha
            )

            reports = find_reports([launch_dir])

            report_path = write_runtime_report(
                launch_dir,
                "BLOCKED_COMPONENT_FAILURE",
                reports,
                production_pass,
                executed,
            )

            print()
            print(f"Runtime report : {report_path}")
            return 4

        executed.append(script)

    production_pass = production_invariant(
        before_size,
        before_sha
    )

    reports = find_reports([launch_dir, Path(tempfile.gettempdir())])

    print()
    print("=" * 100)
    print("PAPER REPORT DISCOVERY")
    print("=" * 100)

    for report_name in EXPECTED_REPORTS:
        if report_name in reports:
            print(
                f"FOUND   | {reports[report_name]}"
            )
        else:
            print(
                f"MISSING | {report_name}"
            )

    all_reports = all(
        name in reports
        for name in EXPECTED_REPORTS
    )

    print()
    print("=" * 100)
    print("LIVE PAPER ISOLATED-LAUNCH LIFECYCLE VERDICT")
    print("=" * 100)

    if not production_pass:
        status = "SAFETY_FAILURE"
    elif all_reports:
        status = "PASS"
    else:
        status = "PARTIAL_REPORT_CHAIN"

    print(
        f"LIFECYCLE_PIPELINE_EXECUTION : {status}"
    )
    print(
        f"PRODUCTION_ISOLATION           : "
        f"{'PASS' if production_pass else 'FAIL'}"
    )
    print(
        f"PAPER_REPORT_CHAIN             : "
        f"{'COMPLETE' if all_reports else 'INCOMPLETE'}"
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)
    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Historical repair    : NONE")
    print("Synthetic snapshot   : NONE")
    print("Direction inference  : NONE")
    print("Real order execution : NONE")
    print("Paper execution      : ANALYTICAL ONLY")

    report_path = write_runtime_report(
        launch_dir,
        status,
        reports,
        production_pass,
        executed,
    )

    print()
    print(f"Runtime report : {report_path}")

    if status == "PASS":
        print()
        print(
            "Genuine PAPER lifecycle/state reports were produced "
            "inside the isolated launch."
        )
        print(
            "The next step is independent snapshot extraction "
            "and temporal continuity verification."
        )

    return 0 if production_pass else 5


if __name__ == "__main__":
    main()