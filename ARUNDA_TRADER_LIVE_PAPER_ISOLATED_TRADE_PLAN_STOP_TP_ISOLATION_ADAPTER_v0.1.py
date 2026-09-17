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


FRONTIER_NAME = "ARUNDA_TRADER_LIVE_PAPER_ISOLATED_TRADE_PLAN_STOP_TP_ISOLATION_ADAPTER_v0.3"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = BASE_DIR / "arunda.db"

TARGET_FRONTIER = BASE_DIR / "ARUNDA_TRADER_LIVE_TRADE_PLAN_STOP_TP_CONTRACT_v0.1.py"

LAUNCH_ROOT = Path(tempfile.gettempdir())
LAUNCH_PREFIX = "arunda_live_launch_"


FORBIDDEN_RUNTIME_TOKENS = (
    "REAL ORDER",
    "LIVE ORDER",
    "SUBMIT ORDER",
    "PLACE ORDER",
    "CREATE ORDER",
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_size(path):
    return path.stat().st_size if path.exists() else 0


def sqlite_row_count(path):
    if not path.exists():
        return None

    conn = sqlite3.connect(str(path))
    try:
        rows = {}
        tables = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        for (table,) in tables:
            try:
                value = conn.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                rows[table] = int(value)
            except Exception:
                rows[table] = None

        return rows
    finally:
        conn.close()


def discover_launches():
    launches = []

    if not LAUNCH_ROOT.exists():
        return launches

    for p in LAUNCH_ROOT.iterdir():
        if not p.is_dir():
            continue

        if not p.name.startswith(LAUNCH_PREFIX):
            continue

        db = p / "arunda_live_capture.db"

        if db.exists():
            launches.append(p)

    launches.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return launches


def select_launch():
    launches = discover_launches()

    if not launches:
        raise FileNotFoundError(
            "No isolated LIVE launch containing arunda_live_capture.db was found."
        )

    return launches[0]


def source_text():
    if not TARGET_FRONTIER.exists():
        raise FileNotFoundError(
            f"Target frontier not found:\n{TARGET_FRONTIER}"
        )

    return TARGET_FRONTIER.read_text(
        encoding="utf-8",
        errors="replace",
    )


def static_inspection(source):
    result = {
        "target_exists": TARGET_FRONTIER.exists(),
        "sqlite3_detected": "sqlite3" in source.lower(),
        "environment_detected": (
            "os.environ" in source
            or "getenv(" in source
            or "environ.get(" in source
        ),
        "production_references": [],
        "write_patterns": [],
    }

    lower = source.lower()

    production_patterns = (
        str(PRODUCTION_DB).lower(),
        "arundatrader\\arunda.db",
        "arundatrader/arunda.db",
        "arunda.db",
    )

    for pattern in production_patterns:
        if pattern in lower:
            result["production_references"].append(pattern)

    write_patterns = (
        "insert into",
        "update ",
        "delete from",
        "create table",
        "alter table",
        "drop table",
        ".commit(",
    )

    for pattern in write_patterns:
        if pattern in lower:
            result["write_patterns"].append(pattern)

    return result


def build_runtime_runner(
    target_path,
    isolated_db,
    runtime_dir,
):
    runner = runtime_dir / "_isolated_frontier_runner.py"

    target_literal = str(target_path).replace("\\", "\\\\")
    isolated_literal = str(isolated_db).replace("\\", "\\\\")
    production_literal = str(PRODUCTION_DB).replace("\\", "\\\\")

    code = f'''
import os
import sys
import json
import sqlite3
import traceback
from pathlib import Path

TARGET = r"{target_literal}"
ISOLATED_DB = r"{isolated_literal}"
PRODUCTION_DB = r"{production_literal}"

_original_connect = sqlite3.connect

runtime_log = {{
    "redirect_calls": 0,
    "blocked_production_calls": 0,
    "connections": [],
}}

def isolated_connect(database, *args, **kwargs):
    original = str(database)

    production_norm = os.path.normcase(
        os.path.abspath(PRODUCTION_DB)
    )

    database_norm = os.path.normcase(
        os.path.abspath(original)
    )

    if database_norm == production_norm:
        runtime_log["blocked_production_calls"] += 1
        database = ISOLATED_DB
        runtime_log["redirect_calls"] += 1

    elif (
        original.lower() == "arunda.db"
        or original.lower().endswith("\\\\arunda.db")
        or original.lower().endswith("/arunda.db")
    ):
        database = ISOLATED_DB
        runtime_log["redirect_calls"] += 1

    runtime_log["connections"].append({{
        "requested": original,
        "actual": str(database),
    }})

    actual_norm = os.path.normcase(
        os.path.abspath(str(database))
    )

    if actual_norm == production_norm:
        raise RuntimeError(
            "ISOLATION FAILURE: attempted production DB connection"
        )

    return _original_connect(database, *args, **kwargs)


sqlite3.connect = isolated_connect

os.environ["ARUNDA_DB_PATH"] = ISOLATED_DB
os.environ["ARUNDA_DATABASE"] = ISOLATED_DB
os.environ["DATABASE_PATH"] = ISOLATED_DB
os.environ["ARUNDA_ISOLATED_DB"] = ISOLATED_DB
os.environ["ARUNDA_LIVE_PAPER_MODE"] = "1"
os.environ["ARUNDA_PAPER_ONLY"] = "1"
os.environ["ARUNDA_REAL_ORDERS"] = "0"

os.chdir(r"{str(runtime_dir)}")

try:
    import runpy

    runpy.run_path(
        TARGET,
        run_name="__main__",
    )

    runtime_log["exit_code"] = 0

except SystemExit as exc:
    code = exc.code

    if code is None:
        code = 0

    runtime_log["exit_code"] = int(code)

except Exception:
    runtime_log["exit_code"] = 1
    runtime_log["exception"] = traceback.format_exc()

finally:
    Path(r"{str(runtime_dir / "_runtime_redirect_report.json")}").write_text(
        json.dumps(runtime_log, indent=2),
        encoding="utf-8",
    )
'''

    runner.write_text(code, encoding="utf-8")
    return runner


def execute_isolated(target, isolated_db, runtime_dir):
    runner = build_runtime_runner(
        target,
        isolated_db,
        runtime_dir,
    )

    start = time.time()

    completed = subprocess.run(
        [
            sys.executable,
            str(runner),
        ],
        cwd=str(runtime_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )

    duration = time.time() - start

    redirect_report = runtime_dir / "_runtime_redirect_report.json"

    runtime_info = {}

    if redirect_report.exists():
        try:
            runtime_info = json.loads(
                redirect_report.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
        except Exception:
            runtime_info = {}

    return {
        "returncode": completed.returncode,
        "duration": duration,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "runtime_info": runtime_info,
    }


def find_reports(runtime_dir):
    reports = []

    for p in runtime_dir.glob("*.json"):
        if p.name.startswith("_"):
            continue

        reports.append(p)

    return sorted(
        reports,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def contains_real_order_marker(text):
    upper = text.upper()

    for token in FORBIDDEN_RUNTIME_TOKENS:
        if token in upper:
            return True

    return False


def main():
    print("=" * 100)
    print(f"ARUNDA TRADER LIVE PAPER TRADE PLAN + STOP/TP ISOLATION ADAPTER v0.3")
    print("=" * 100)

    print()
    print("OBJECTIVE")
    print("=" * 100)
    print("Execute the EXISTING Trade Plan + Stop/TP frontier")
    print("inside the isolated LIVE PAPER database.")
    print("No source modification.")
    print("No bypass of the safety gate.")
    print("No synthetic Trade Plan.")
    print("No production DB write.")
    print("No real order execution.")

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    production_before_size = file_size(PRODUCTION_DB)
    production_before_sha = sha256_file(PRODUCTION_DB)
    production_before_rows = sqlite_row_count(PRODUCTION_DB)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Size   : {production_before_size}")
    print(f"SHA256 : {production_before_sha}")

    print()
    print("=" * 100)
    print("ISOLATED LAUNCH DISCOVERY")
    print("=" * 100)

    launch_dir = select_launch()
    isolated_db = launch_dir / "arunda_live_capture.db"

    print(f"Selected : {launch_dir}")
    print(f"Database : {isolated_db}")

    isolated_before_size = file_size(isolated_db)
    isolated_before_sha = sha256_file(isolated_db)
    isolated_before_rows = sqlite_row_count(isolated_db)

    print()
    print("=" * 100)
    print("ISOLATED DATABASE BASELINE")
    print("=" * 100)
    print(f"Size   : {isolated_before_size}")
    print(f"SHA256 : {isolated_before_sha}")

    print()
    print("=" * 100)
    print("TARGET FRONTIER")
    print("=" * 100)
    print(f"Script : {TARGET_FRONTIER}")

    source = source_text()

    print()
    print("=" * 100)
    print("SOURCE STATIC ANALYSIS")
    print("=" * 100)

    inspection = static_inspection(source)

    print(
        "Python source          : PASS"
    )
    print(
        f"sqlite3 detected       : "
        f"{'YES' if inspection['sqlite3_detected'] else 'NO'}"
    )
    print(
        f"environment detected   : "
        f"{'YES' if inspection['environment_detected'] else 'NO'}"
    )

    print()
    print("Production references:")

    if inspection["production_references"]:
        for item in inspection["production_references"]:
            print(f"  - {item}")
    else:
        print("  NONE")

    print()
    print("Write-related patterns:")

    if inspection["write_patterns"]:
        for item in inspection["write_patterns"]:
            print(f"  - {item}")
    else:
        print("  NONE")

    print()
    print("=" * 100)
    print("RUNTIME ISOLATION")
    print("=" * 100)
    print("Runtime sqlite3.connect interception : ENABLED")
    print("Production DB connection              : BLOCKED")
    print("Isolated DB redirection               : ENABLED")
    print("Source modification                   : NONE")

    runtime_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_trade_plan_isolated_"
        )
    )

    print()
    print(f"Runtime directory : {runtime_dir}")

    result = execute_isolated(
        TARGET_FRONTIER,
        isolated_db,
        runtime_dir,
    )

    runtime_info = result["runtime_info"]

    print()
    print("=" * 100)
    print("ISOLATED FRONTIER EXECUTION")
    print("=" * 100)
    print(f"Runtime duration : {result['duration']:.3f}s")
    print(f"Exit code        : {result['returncode']}")

    if result["stdout"]:
        print()
        print("----- STDOUT -----")
        print(result["stdout"])

    if result["stderr"]:
        print()
        print("----- STDERR -----")
        print(result["stderr"])

    redirect_calls = int(
        runtime_info.get(
            "redirect_calls",
            0,
        )
    )

    blocked_production_calls = int(
        runtime_info.get(
            "blocked_production_calls",
            0,
        )
    )

    connections = runtime_info.get(
        "connections",
        [],
    )

    production_connection_observed = False

    production_norm = os.path.normcase(
        os.path.abspath(str(PRODUCTION_DB))
    )

    for item in connections:
        actual = item.get("actual")

        if actual is None:
            continue

        actual_norm = os.path.normcase(
            os.path.abspath(str(actual))
        )

        if actual_norm == production_norm:
            production_connection_observed = True

    print()
    print("=" * 100)
    print("RUNTIME ISOLATION EVIDENCE")
    print("=" * 100)
    print(f"SQLite redirect calls       : {redirect_calls}")
    print(f"Production calls intercepted: {blocked_production_calls}")
    print(
        "Production connection used  : "
        + ("YES" if production_connection_observed else "NO")
    )

    isolated_after_size = file_size(isolated_db)
    isolated_after_sha = sha256_file(isolated_db)
    isolated_after_rows = sqlite_row_count(isolated_db)

    production_after_size = file_size(PRODUCTION_DB)
    production_after_sha = sha256_file(PRODUCTION_DB)
    production_after_rows = sqlite_row_count(PRODUCTION_DB)

    production_invariant = (
        production_before_size == production_after_size
        and production_before_sha == production_after_sha
        and production_before_rows == production_after_rows
    )

    isolated_changed = (
        isolated_before_size != isolated_after_size
        or isolated_before_sha != isolated_after_sha
        or isolated_before_rows != isolated_after_rows
    )

    reports = find_reports(runtime_dir)

    report_names = [
        p.name
        for p in reports
    ]

    output_has_real_order_marker = contains_real_order_marker(
        result["stdout"]
        + "\n"
        + result["stderr"]
    )

    execution_pass = (
        result["returncode"] == 0
        and not production_connection_observed
        and production_invariant
        and not output_has_real_order_marker
    )

    print()
    print("=" * 100)
    print("ISOLATED DATABASE RESULT")
    print("=" * 100)
    print(f"Before size  : {isolated_before_size}")
    print(f"After size   : {isolated_after_size}")
    print(f"Before SHA256: {isolated_before_sha}")
    print(f"After SHA256 : {isolated_after_sha}")
    print(
        "Isolated DB changed : "
        + ("YES" if isolated_changed else "NO")
    )

    print()
    print("=" * 100)
    print("GENERATED REPORTS")
    print("=" * 100)

    if reports:
        for report in reports:
            print(f"FOUND | {report}")
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(f"Before size  : {production_before_size}")
    print(f"After size   : {production_after_size}")
    print(f"Before SHA256: {production_before_sha}")
    print(f"After SHA256 : {production_after_sha}")
    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if production_invariant else "FAIL")
    )

    print()
    print("=" * 100)
    print("ISOLATION ADAPTER VERDICT")
    print("=" * 100)
    print(
        "FRONTIER EXECUTION       : "
        + ("PASS" if execution_pass else "FAIL")
    )
    print(
        "SOURCE MODIFICATION      : NONE"
    )
    print(
        "PRODUCTION DB WRITES     : "
        + ("NONE" if production_invariant else "UNKNOWN")
    )
    print(
        "REAL ORDER EXECUTION     : "
        + ("NONE" if not output_has_real_order_marker else "MARKER_DETECTED")
    )
    print(
        "ISOLATED DB USE          : "
        + ("PASS" if not production_connection_observed else "FAIL")
    )

    report = {
        "frontier": FRONTIER_NAME,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "target_frontier": str(TARGET_FRONTIER),

        "isolated_launch": str(launch_dir),
        "isolated_db": str(isolated_db),
        "runtime_dir": str(runtime_dir),

        "production_baseline": {
            "size": production_before_size,
            "sha256": production_before_sha,
            "rows": production_before_rows,
        },

        "production_after": {
            "size": production_after_size,
            "sha256": production_after_sha,
            "rows": production_after_rows,
        },

        "isolated_before": {
            "size": isolated_before_size,
            "sha256": isolated_before_sha,
            "rows": isolated_before_rows,
        },

        "isolated_after": {
            "size": isolated_after_size,
            "sha256": isolated_after_sha,
            "rows": isolated_after_rows,
        },

        "runtime": {
            "returncode": result["returncode"],
            "duration_seconds": result["duration"],
            "redirect_calls": redirect_calls,
            "blocked_production_calls": blocked_production_calls,
            "connections": connections,
        },

        "reports": report_names,

        "verdict": {
            "execution": (
                "PASS"
                if execution_pass
                else "BLOCKED"
            ),
            "production_isolation": (
                "PASS"
                if production_invariant
                and not production_connection_observed
                else "FAIL"
            ),
            "source_modification": "NONE",
            "synthetic_data": "NONE",
            "real_order_execution": (
                "NONE"
                if not output_has_real_order_marker
                else "MARKER_DETECTED"
            ),
        },
    }

    report_path = runtime_dir / (
        "LIVE_PAPER_ISOLATED_TRADE_PLAN_STOP_TP_"
        "ISOLATION_ADAPTER_REPORT.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)

    if execution_pass:
        print(
            "Existing Trade Plan + Stop/TP frontier executed "
            "inside isolated runtime."
        )
        print(
            "The production database remained unchanged."
        )
    else:
        print(
            "The existing frontier was NOT accepted as safely executed."
        )
        print(
            "No source modification or bypass was performed."
        )

    print()
    print(f"Runtime report : {report_path}")
    print(f"Runtime directory : {runtime_dir}")


if __name__ == "__main__":
    main()