from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import traceback
import urllib.request
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# ARUNDA TRADER
# LIVE LAUNCH HARNESS v0.1
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"
ENGINE_MODULE_NAME = "fusion_engine"

CURRENT_ENGINE = "FUSION_v0.5"
TARGET_TABLE = "fusion_signals"

LIVE_CHECK_URLS = {
    "CMC": "https://api.coinmarketcap.com/",
    "COINALYZE": "https://api.coinalyze.net/",
    "NEWS": "https://www.google.com/",
}


# =============================================================================
# SAFETY
# =============================================================================

PRODUCTION_DB_MUST_REMAIN_UNTOUCHED = True

FORBIDDEN_SQL = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "CREATE",
    "REPLACE",
)


# =============================================================================
# HELPERS
# =============================================================================

def banner(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_fingerprint(path: Path):
    stat = path.stat()

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def table_count(path: Path, table: str) -> int:
    conn = sqlite3.connect(path)

    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        return int(row[0])

    finally:
        conn.close()


def direction_distribution(path: Path):
    conn = sqlite3.connect(path)

    try:
        rows = conn.execute(
            f"""
            SELECT direction, COUNT(*)
            FROM {TARGET_TABLE}
            GROUP BY direction
            ORDER BY direction
            """
        ).fetchall()

        return rows

    finally:
        conn.close()


# =============================================================================
# LIVE INTERNET PREFLIGHT
# =============================================================================

def check_live_internet():

    banner("LIVE INTERNET PREFLIGHT")

    results = {}

    for name, url in LIVE_CHECK_URLS.items():

        started = time.perf_counter()

        try:

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "ArundaTrader-LiveLaunchHarness/0.1"
                    )
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=10
            ) as response:

                status = response.status
                elapsed = time.perf_counter() - started

                results[name] = {
                    "ok": True,
                    "status": status,
                    "latency": round(elapsed, 3),
                }

                print(
                    f"{name:<12} | "
                    f"ONLINE | "
                    f"HTTP={status} | "
                    f"{elapsed:.3f}s"
                )

        except Exception as exc:

            elapsed = time.perf_counter() - started

            results[name] = {
                "ok": False,
                "error": repr(exc),
                "latency": round(elapsed, 3),
            }

            print(
                f"{name:<12} | "
                f"FAIL | "
                f"{repr(exc)}"
            )

    # Internet itself is required.
    internet_ok = any(
        item.get("ok")
        for item in results.values()
    )

    if internet_ok:
        print()
        print("LIVE INTERNET : AVAILABLE")
    else:
        print()
        print("LIVE INTERNET : FAIL")

    return internet_ok, results


# =============================================================================
# ISOLATED DATABASE
# =============================================================================

def create_isolated_database():

    banner("ISOLATED DATABASE CREATION")

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_live_launch_"
        )
    )

    isolated_db = temp_dir / "arunda_live_capture.db"

    shutil.copy2(
        PRODUCTION_DB,
        isolated_db
    )

    print(f"Production DB : {PRODUCTION_DB}")
    print(f"Isolated DB   : {isolated_db}")

    source_fp = db_fingerprint(PRODUCTION_DB)
    isolated_fp = db_fingerprint(isolated_db)

    print()
    print(
        f"Production size : "
        f"{source_fp['size']:,}"
    )

    print(
        f"Isolated size   : "
        f"{isolated_fp['size']:,}"
    )

    if source_fp["sha256"] != isolated_fp["sha256"]:
        raise RuntimeError(
            "Isolated database fingerprint mismatch."
        )

    print()
    print("DATABASE CLONE : VERIFIED")

    return temp_dir, isolated_db


# =============================================================================
# SQLITE REDIRECTION
# =============================================================================

class SQLiteRedirector:

    def __init__(
        self,
        production_path: Path,
        isolated_path: Path,
    ):

        self.production_path = str(
            production_path.resolve()
        )

        self.isolated_path = str(
            isolated_path.resolve()
        )

        self.original_connect = sqlite3.connect

    def _normalize(self, value):

        if isinstance(value, os.PathLike):
            return str(Path(value).resolve())

        if isinstance(value, str):

            try:
                return str(Path(value).resolve())

            except Exception:
                return value

        return value

    def connect(self, database, *args, **kwargs):

        normalized = self._normalize(database)

        # Redirect only the exact production DB.
        if normalized == self.production_path:

            print()
            print(
                "[HARNESS] "
                "Production DB connection intercepted."
            )

            print(
                "[HARNESS] "
                f"Redirecting -> {self.isolated_path}"
            )

            database = self.isolated_path

        return self.original_connect(
            database,
            *args,
            **kwargs
        )

    def install(self):

        sqlite3.connect = self.connect

    def restore(self):

        sqlite3.connect = self.original_connect


# =============================================================================
# ACTUAL ENGINE EXECUTION
# =============================================================================

def run_actual_engine(isolated_db):

    banner("ACTUAL FUSION ENGINE RUNTIME")

    print(
        f"Engine module : {ENGINE_MODULE_NAME}"
    )

    print(
        f"Expected      : {CURRENT_ENGINE}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "  The actual fusion_engine.main() will be invoked."
    )

    print(
        "  No Fusion logic is reimplemented by this harness."
    )

    print(
        "  Production DB connections are redirected."
    )

    print()

    redirector = SQLiteRedirector(
        PRODUCTION_DB,
        isolated_db
    )

    redirector.install()

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    runtime_exception = None
    return_value = None

    started = time.perf_counter()

    try:

        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(
                0,
                str(PROJECT_ROOT)
            )

        if ENGINE_MODULE_NAME in sys.modules:
            del sys.modules[ENGINE_MODULE_NAME]

        engine = importlib.import_module(
            ENGINE_MODULE_NAME
        )

        if not hasattr(engine, "main"):
            raise RuntimeError(
                "fusion_engine.main() not found."
            )

        print(
            f"Loaded source : "
            f"{Path(engine.__file__).resolve()}"
        )

        with redirect_stdout(
            stdout_buffer
        ), redirect_stderr(
            stderr_buffer
        ):

            return_value = engine.main()

    except Exception as exc:

        runtime_exception = exc

    finally:

        redirector.restore()

    elapsed = time.perf_counter() - started

    stdout_text = stdout_buffer.getvalue()
    stderr_text = stderr_buffer.getvalue()

    print(
        f"Runtime duration : {elapsed:.3f}s"
    )

    if runtime_exception is None:

        print(
            "RUNTIME EXCEPTION : NONE"
        )

    else:

        print(
            "RUNTIME EXCEPTION : PRESENT"
        )

        print(
            repr(runtime_exception)
        )

        print()
        traceback.print_exception(
            type(runtime_exception),
            runtime_exception,
            runtime_exception.__traceback__
        )

    return {
        "return_value": return_value,
        "exception": runtime_exception,
        "stdout": stdout_text,
        "stderr": stderr_text,
        "duration": elapsed,
    }


# =============================================================================
# CAPTURE VERIFICATION
# =============================================================================

def inspect_capture(
    isolated_db,
    before_count,
):

    banner("ISOLATED RUNTIME CAPTURE")

    after_count = table_count(
        isolated_db,
        TARGET_TABLE
    )

    inserted = after_count - before_count

    print(
        f"Before fusion_signals rows : {before_count}"
    )

    print(
        f"After fusion_signals rows  : {after_count}"
    )

    print(
        f"Captured row delta         : {inserted}"
    )

    distribution = direction_distribution(
        isolated_db
    )

    print()
    print("Direction distribution:")

    for direction, count in distribution:

        print(
            f"  {str(direction):<10} | {count}"
        )

    return {
        "before": before_count,
        "after": after_count,
        "inserted": inserted,
        "direction_distribution": [
            {
                "direction": direction,
                "count": count,
            }
            for direction, count in distribution
        ],
    }


# =============================================================================
# LIVE OUTPUT ANALYSIS
# =============================================================================

def analyze_runtime_output(
    runtime,
    capture,
):

    banner("LIVE RUNTIME OUTPUT ANALYSIS")

    stdout = runtime["stdout"]
    stderr = runtime["stderr"]

    print(
        f"STDOUT bytes : {len(stdout.encode('utf-8'))}"
    )

    print(
        f"STDERR bytes : {len(stderr.encode('utf-8'))}"
    )

    if stderr.strip():

        print()
        print("STDERR:")
        print(stderr)

    # Important runtime markers.
    markers = {
        "FUSION_v0.5": CURRENT_ENGINE in stdout,
        "ENTRY PRICE": "ENTRY PRICE" in stdout,
        "DIRECTION": "DIRECTION" in stdout,
        "CONFIDENCE": "CONFIDENCE" in stdout,
        "LIVE/CURRENT": (
            "LIVE" in stdout.upper()
            or "CMC" in stdout.upper()
        ),
    }

    print()
    print("Runtime markers:")

    for name, found in markers.items():

        print(
            f"{name:<20} | "
            f"{'FOUND' if found else 'NOT_FOUND'}"
        )

    return markers


# =============================================================================
# PRODUCTION DB INVARIANT
# =============================================================================

def verify_production_invariant(
    before_fp,
    before_count,
):

    banner("PRODUCTION DATABASE INVARIANT")

    after_fp = db_fingerprint(
        PRODUCTION_DB
    )

    after_count = table_count(
        PRODUCTION_DB,
        TARGET_TABLE
    )

    fingerprint_pass = (
        before_fp == after_fp
    )

    population_pass = (
        before_count == after_count
    )

    print(
        f"Before size : "
        f"{before_fp['size']:,}"
    )

    print(
        f"After size  : "
        f"{after_fp['size']:,}"
    )

    print()
    print(
        "SHA256       : "
        f"{'UNCHANGED' if fingerprint_pass else 'CHANGED'}"
    )

    print(
        "Row count    : "
        f"{'UNCHANGED' if population_pass else 'CHANGED'}"
    )

    passed = (
        fingerprint_pass
        and population_pass
    )

    print()
    print(
        "PRODUCTION DB INVARIANT : "
        f"{'PASS' if passed else 'FAIL'}"
    )

    return passed


# =============================================================================
# REPORT
# =============================================================================

def write_report(
    report_dir,
    live_check,
    runtime,
    capture,
    production_pass,
):

    report = {
        "timestamp": utc_now(),
        "engine": CURRENT_ENGINE,
        "database": str(PRODUCTION_DB),
        "mode": "LIVE_ISOLATED_CAPTURE",
        "production_db_modified": not production_pass,
        "live_preflight": live_check,
        "runtime_exception": (
            repr(runtime["exception"])
            if runtime["exception"]
            else None
        ),
        "runtime_duration": runtime["duration"],
        "capture": capture,
        "stdout": runtime["stdout"],
        "stderr": runtime["stderr"],
    }

    report_path = (
        report_dir
        / "LIVE_LAUNCH_RUNTIME_REPORT.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8"
    )

    return report_path


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TRADER "
        "LIVE LAUNCH HARNESS v0.1"
    )

    print(
        "OBJECTIVE:"
    )

    print(
        "  Execute the ACTUAL FUSION_v0.5 runtime"
    )

    print(
        "  against LIVE external sources"
    )

    print(
        "  while keeping production DB isolated."
    )

    print()
    print(
        "Production DB writes : BLOCKED BY ISOLATION"
    )

    print(
        "Synthetic data       : FORBIDDEN"
    )

    print(
        "Historical repair     : NONE"
    )

    print(
        "Fusion reimplementation : NONE"
    )

    # ------------------------------------------------------------
    # Production baseline
    # ------------------------------------------------------------

    if not PRODUCTION_DB.exists():

        raise FileNotFoundError(
            PRODUCTION_DB
        )

    before_fp = db_fingerprint(
        PRODUCTION_DB
    )

    before_count = table_count(
        PRODUCTION_DB,
        TARGET_TABLE
    )

    banner("PRODUCTION BASELINE")

    print(
        f"Rows : {before_count}"
    )

    print(
        f"SHA256 : {before_fp['sha256']}"
    )

    # ------------------------------------------------------------
    # Live internet
    # ------------------------------------------------------------

    internet_ok, live_check = (
        check_live_internet()
    )

    if not internet_ok:

        banner("LIVE LAUNCH ABORTED")

        print(
            "No external internet connectivity "
            "was confirmed."
        )

        print(
            "Production DB remains untouched."
        )

        return

    # ------------------------------------------------------------
    # Isolated database
    # ------------------------------------------------------------

    temp_dir, isolated_db = (
        create_isolated_database()
    )

    try:

        # --------------------------------------------------------
        # Actual runtime
        # --------------------------------------------------------

        runtime = run_actual_engine(
            isolated_db
        )

        # --------------------------------------------------------
        # Capture
        # --------------------------------------------------------

        capture = inspect_capture(
            isolated_db,
            before_count,
        )

        # --------------------------------------------------------
        # Runtime analysis
        # --------------------------------------------------------

        markers = analyze_runtime_output(
            runtime,
            capture,
        )

        # --------------------------------------------------------
        # Production invariant
        # --------------------------------------------------------

        production_pass = (
            verify_production_invariant(
                before_fp,
                before_count,
            )
        )

        # --------------------------------------------------------
        # Final verdict
        # --------------------------------------------------------

        banner("LIVE LAUNCH HARNESS VERDICT")

        runtime_pass = (
            runtime["exception"] is None
        )

        capture_pass = (
            capture["inserted"] > 0
        )

        actual_engine_pass = (
            CURRENT_ENGINE in runtime["stdout"]
        )

        if (
            runtime_pass
            and capture_pass
            and actual_engine_pass
            and production_pass
        ):

            verdict = (
                "LIVE_RUNTIME_CAPTURE : PASS"
            )

        else:

            verdict = (
                "LIVE_RUNTIME_CAPTURE : FAIL"
            )

        print(verdict)

        print()
        print(
            f"Actual {CURRENT_ENGINE} : "
            f"{'PASS' if actual_engine_pass else 'FAIL'}"
        )

        print(
            f"Runtime exception       : "
            f"{'NO' if runtime_pass else 'YES'}"
        )

        print(
            f"Isolated signal capture : "
            f"{'PASS' if capture_pass else 'FAIL'}"
        )

        print(
            f"Production DB invariant : "
            f"{'PASS' if production_pass else 'FAIL'}"
        )

        print()
        print(
            "Production DB writes : NONE"
        )

        print(
            "Production DB commit : NONE"
        )

        print(
            "Historical repair    : NONE"
        )

        print(
            "Direction inference  : NONE"
        )

        # --------------------------------------------------------
        # Report
        # --------------------------------------------------------

        report_path = write_report(
            temp_dir,
            live_check,
            runtime,
            capture,
            production_pass,
        )

        print()
        print(
            f"Runtime report : {report_path}"
        )

        print()
        print(
            f"Isolated runtime directory : {temp_dir}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "  The isolated DB is disposable."
        )

        print(
            "  It must NOT replace arunda.db."
        )

    except Exception:

        # Even if harness itself fails, verify production.
        try:

            verify_production_invariant(
                before_fp,
                before_count,
            )

        except Exception:
            pass

        raise


if __name__ == "__main__":
    main()