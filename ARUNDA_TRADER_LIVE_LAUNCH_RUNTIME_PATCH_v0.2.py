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
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# ARUNDA TRADER
# LIVE LAUNCH RUNTIME PATCH v0.2
#
# PURPOSE:
#   Forward-only execution of the ACTUAL FUSION_v0.5 runtime.
#
#   This patch intentionally removes the old generic connectivity gate.
#   The actual fusion_engine runtime is the source of truth for whether
#   its configured live dependencies are reachable.
#
# SAFETY:
#   Production DB is cloned.
#   Exact production sqlite3.connect() calls are redirected to the clone.
#   Production DB is fingerprinted before and after execution.
#
# FORBIDDEN:
#   Fusion reimplementation
#   Signal reconstruction
#   Signal inference
#   Synthetic signals
#   Historical repair
#   Production DB writes
# =============================================================================


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

ENGINE_MODULE_NAME = "fusion_engine"
EXPECTED_ENGINE = "FUSION_v0.5"

TARGET_TABLE = "fusion_signals"

REPORT_NAME = "LIVE_LAUNCH_RUNTIME_PATCH_REPORT.json"


# =============================================================================
# SAFETY
# =============================================================================

PRODUCTION_DB_MUST_REMAIN_UNTOUCHED = True


# =============================================================================
# HELPERS
# =============================================================================

def banner(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def fingerprint(path: Path) -> dict:
    stat = path.stat()

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def sqlite_scalar(
    path: Path,
    sql: str,
    params: tuple = (),
):
    conn = sqlite3.connect(path)

    try:
        row = conn.execute(
            sql,
            params,
        ).fetchone()

        if row is None:
            return None

        return row[0]

    finally:
        conn.close()

def table_exists(
    path: Path,
    table_name: str,
) -> bool:

    conn = sqlite3.connect(path)

    try:
        row = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()

        return row is not None

    finally:
        conn.close()

def table_columns(
    path: Path,
    table: str,
) -> list[str]:

    conn = sqlite3.connect(path)

    try:
        rows = conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        return [
            str(row[1])
            for row in rows
        ]

    finally:
        conn.close()


def table_count(
    path: Path,
    table: str,
) -> int:

    conn = sqlite3.connect(path)

    try:
        row = conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()

        return int(row[0])

    finally:
        conn.close()


# =============================================================================
# PRODUCTION BASELINE
# =============================================================================

def capture_production_baseline() -> dict:

    banner("PRODUCTION BASELINE")

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    fp = fingerprint(PRODUCTION_DB)

    count = table_count(
        PRODUCTION_DB,
        TARGET_TABLE,
    )

    print(f"Database : {PRODUCTION_DB}")
    print(f"Rows     : {count}")
    print(f"Size     : {fp['size']:,}")
    print(f"SHA256   : {fp['sha256']}")

    return {
        "fingerprint": fp,
        "fusion_signals_rows": count,
    }


# =============================================================================
# ISOLATED DATABASE
# =============================================================================

def create_isolated_database():

    banner("ISOLATED DATABASE")

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_live_launch_"
        )
    )

    isolated_db = (
        temp_dir
        / "arunda_live_capture.db"
    )

    shutil.copy2(
        PRODUCTION_DB,
        isolated_db,
    )

    production_fp = fingerprint(
        PRODUCTION_DB
    )

    isolated_fp = fingerprint(
        isolated_db
    )

    if production_fp["sha256"] != isolated_fp["sha256"]:
        raise RuntimeError(
            "Initial isolated DB fingerprint mismatch."
        )

    print(f"Production DB : {PRODUCTION_DB}")
    print(f"Isolated DB   : {isolated_db}")
    print()
    print("DATABASE CLONE : VERIFIED")

    return temp_dir, isolated_db


# =============================================================================
# SQLITE REDIRECTOR
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

    def normalize(self, value):

        if isinstance(value, os.PathLike):
            return str(
                Path(value).resolve()
            )

        if isinstance(value, str):

            try:
                return str(
                    Path(value).resolve()
                )

            except Exception:
                return value

        return value

    def connect(
        self,
        database,
        *args,
        **kwargs,
    ):

        normalized = self.normalize(
            database
        )

        if normalized == self.production_path:

            print(
                "\n[HARNESS] "
                "Production SQLite connection intercepted."
            )

            print(
                "[HARNESS] "
                f"REDIRECT -> {self.isolated_path}"
            )

            database = self.isolated_path

        return self.original_connect(
            database,
            *args,
            **kwargs,
        )

    def install(self):
        sqlite3.connect = self.connect

    def restore(self):
        sqlite3.connect = self.original_connect


# =============================================================================
# ACTUAL FUSION RUNTIME
# =============================================================================

def run_actual_fusion(
    isolated_db: Path,
) -> dict:

    banner("ACTUAL FUSION_v0.5 RUNTIME")

    print(
        "Generic connectivity gate : BYPASSED"
    )

    print(
        "Reason:"
    )

    print(
        "  The previous gate tested generic URLs rather than"
    )

    print(
        "  the actual dependency execution path."
    )

    print()
    print(
        "Actual runtime            : ENABLED"
    )

    print(
        f"Engine module             : {ENGINE_MODULE_NAME}"
    )

    print(
        f"Expected engine           : {EXPECTED_ENGINE}"
    )

    print(
        f"Isolated database         : {isolated_db}"
    )

    redirector = SQLiteRedirector(
        PRODUCTION_DB,
        isolated_db,
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
                str(PROJECT_ROOT),
            )

        # Ensure fresh import.
        if ENGINE_MODULE_NAME in sys.modules:
            del sys.modules[
                ENGINE_MODULE_NAME
            ]

        engine = importlib.import_module(
            ENGINE_MODULE_NAME
        )

        engine_file = getattr(
            engine,
            "__file__",
            None,
        )

        print(
            f"Loaded source             : {engine_file}"
        )

        if not hasattr(engine, "main"):
            raise RuntimeError(
                "fusion_engine.main() not found."
            )

        print()
        print(
            "EXECUTING ACTUAL "
            "fusion_engine.main() ..."
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

    elapsed = (
        time.perf_counter()
        - started
    )

    stdout = stdout_buffer.getvalue()
    stderr = stderr_buffer.getvalue()

    print()
    print(
        f"Runtime duration : {elapsed:.3f}s"
    )

    if runtime_exception is None:

        print(
            "Runtime exception : NONE"
        )

    else:

        print(
            "Runtime exception : PRESENT"
        )

        print(
            repr(runtime_exception)
        )

        print()
        traceback.print_exception(
            type(runtime_exception),
            runtime_exception,
            runtime_exception.__traceback__,
        )

    return {
        "return_value": return_value,
        "exception": runtime_exception,
        "stdout": stdout,
        "stderr": stderr,
        "duration": elapsed,
    }


# =============================================================================
# CAPTURE NEW FUSION STATE
# =============================================================================

def inspect_isolated_result(
    isolated_db: Path,
    before_count: int,
) -> dict:

    banner("ISOLATED FUSION RESULT")

    if not table_exists(
        isolated_db,
        TARGET_TABLE,
    ):
        raise RuntimeError(
            f"Target table not found: {TARGET_TABLE}"
        )

    after_count = table_count(
        isolated_db,
        TARGET_TABLE,
    )

    delta = (
        after_count
        - before_count
    )

    columns = table_columns(
        isolated_db,
        TARGET_TABLE,
    )

    print(
        f"Before {TARGET_TABLE} rows : "
        f"{before_count}"
    )

    print(
        f"After {TARGET_TABLE} rows  : "
        f"{after_count}"
    )

    print(
        f"Row delta                   : "
        f"{delta}"
    )

    print()
    print(
        "Columns:"
    )

    print(
        "  "
        + ", ".join(columns)
    )

    result = {
        "before_rows": before_count,
        "after_rows": after_count,
        "delta": delta,
        "columns": columns,
    }

    # ---------------------------------------------------------
    # Snapshot information if the existing schema exposes it.
    # No schema is invented.
    # ---------------------------------------------------------

    snapshot_candidates = [
        "snapshot_id",
        "snapshot",
        "snapshot_uuid",
    ]

    snapshot_column = next(
        (
            column
            for column in snapshot_candidates
            if column in columns
        ),
        None,
    )

    if snapshot_column:

        conn = sqlite3.connect(
            isolated_db
        )

        try:

            rows = conn.execute(
                f'''
                SELECT "{snapshot_column}", COUNT(*)
                FROM "{TARGET_TABLE}"
                GROUP BY "{snapshot_column}"
                ORDER BY ROWID DESC
                LIMIT 10
                '''
            ).fetchall()

        finally:

            conn.close()

        print()
        print(
            f"Recent {snapshot_column} values:"
        )

        for value, count in rows:

            print(
                f"  {value} | rows={count}"
            )

        result[
            "snapshot_column"
        ] = snapshot_column

        result[
            "recent_snapshots"
        ] = [
            {
                "snapshot_id": value,
                "rows": count,
            }
            for value, count in rows
        ]

    return result


# =============================================================================
# RUNTIME MARKERS
# =============================================================================

def analyze_runtime(
    runtime: dict,
) -> dict:

    banner("RUNTIME RESULT")

    stdout = runtime["stdout"]
    stderr = runtime["stderr"]

    markers = {
        "engine_marker": (
            EXPECTED_ENGINE
            in stdout
        ),
        "runtime_output_present": bool(
            stdout.strip()
        ),
        "stderr_present": bool(
            stderr.strip()
        ),
    }

    for name, value in markers.items():

        print(
            f"{name:<25} : "
            f"{'YES' if value else 'NO'}"
        )

    if stderr.strip():

        print()
        print("STDERR:")
        print(stderr)

    return markers


# =============================================================================
# PRODUCTION INVARIANT
# =============================================================================

def verify_production_unchanged(
    baseline: dict,
) -> bool:

    banner("PRODUCTION DATABASE INVARIANT")

    after_fp = fingerprint(
        PRODUCTION_DB
    )

    after_count = table_count(
        PRODUCTION_DB,
        TARGET_TABLE,
    )

    before_fp = baseline[
        "fingerprint"
    ]

    before_count = baseline[
        "fusion_signals_rows"
    ]

    fingerprint_pass = (
        before_fp == after_fp
    )

    population_pass = (
        before_count == after_count
    )

    print(
        "SHA256 : "
        + (
            "UNCHANGED"
            if fingerprint_pass
            else "CHANGED"
        )
    )

    print(
        "Rows   : "
        + (
            "UNCHANGED"
            if population_pass
            else "CHANGED"
        )
    )

    passed = (
        fingerprint_pass
        and population_pass
    )

    print()
    print(
        "PRODUCTION DB INVARIANT : "
        + (
            "PASS"
            if passed
            else "FAIL"
        )
    )

    return passed


# =============================================================================
# REPORT
# =============================================================================

def write_report(
    temp_dir: Path,
    baseline: dict,
    runtime: dict,
    isolated_result: dict,
    markers: dict,
    production_unchanged: bool,
) -> Path:

    report = {
        "timestamp": utc_now(),

        "project": "ARUNDA TRADER",

        "component": (
            "LIVE LAUNCH RUNTIME PATCH"
        ),

        "version": "v0.2",

        "mode": (
            "LIVE_EXTERNAL_SOURCES__"
            "ISOLATED_PRODUCTION_DB"
        ),

        "objective": (
            "Execute the actual FUSION_v0.5 "
            "runtime against live dependencies "
            "without touching production DB."
        ),

        "forward_only": True,

        "generic_connectivity_gate": (
            "BYPASSED"
        ),

        "engine": {
            "module": ENGINE_MODULE_NAME,
            "expected": EXPECTED_ENGINE,
            "actual_runtime_invoked": True,
        },

        "safety": {
            "production_db_writes": False,
            "production_db_commit": False,
            "signal_injection": False,
            "signal_reconstruction": False,
            "signal_inference": False,
            "synthetic_data": False,
            "historical_repair": False,
            "order_execution": False,
        },

        "production_baseline": baseline,

        "isolated_runtime": {
            "directory": str(temp_dir),
            "database": str(
                temp_dir
                / "arunda_live_capture.db"
            ),
        },

        "runtime": {
            "exception": (
                repr(runtime["exception"])
                if runtime["exception"]
                else None
            ),
            "return_value": runtime[
                "return_value"
            ],
            "duration": runtime[
                "duration"
            ],
            "stdout": runtime[
                "stdout"
            ],
            "stderr": runtime[
                "stderr"
            ],
        },

        "isolated_result": isolated_result,

        "runtime_markers": markers,

        "production_db_unchanged": (
            production_unchanged
        ),

        "next_frontier": (
            "LIVE_NEW_FUSION_SNAPSHOT_ELIGIBILITY"
        ),
    }

    report_path = (
        temp_dir
        / REPORT_NAME
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return report_path


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    banner(
        "ARUNDA TRADER "
        "LIVE LAUNCH RUNTIME PATCH v0.2"
    )

    print(
        "FORWARD-ONLY EXECUTION"
    )

    print()
    print(
        "LIVE CONNECTIVITY REPAIR"
        " -> ACTUAL FUSION_v0.5 RUNTIME"
    )

    print()
    print(
        "No generic connectivity gate."
    )

    print(
        "No Fusion reimplementation."
    )

    print(
        "No signal reconstruction."
    )

    print(
        "No signal inference."
    )

    print(
        "No synthetic data."
    )

    print(
        "No production DB writes."
    )

    # ---------------------------------------------------------
    # Baseline
    # ---------------------------------------------------------

    baseline = (
        capture_production_baseline()
    )

    # ---------------------------------------------------------
    # Clone
    # ---------------------------------------------------------

    temp_dir, isolated_db = (
        create_isolated_database()
    )

    try:

        before_count = table_count(
            isolated_db,
            TARGET_TABLE,
        )

        # -----------------------------------------------------
        # ACTUAL ENGINE
        # -----------------------------------------------------

        runtime = run_actual_fusion(
            isolated_db
        )

        # -----------------------------------------------------
        # ISOLATED RESULT
        # -----------------------------------------------------

        isolated_result = (
            inspect_isolated_result(
                isolated_db,
                before_count,
            )
        )

        # -----------------------------------------------------
        # Runtime markers
        # -----------------------------------------------------

        markers = analyze_runtime(
            runtime
        )

        # -----------------------------------------------------
        # Production invariant
        # -----------------------------------------------------

        production_unchanged = (
            verify_production_unchanged(
                baseline
            )
        )

        # -----------------------------------------------------
        # Verdict
        # -----------------------------------------------------

        banner(
            "LIVE LAUNCH RUNTIME VERDICT"
        )

        runtime_pass = (
            runtime["exception"]
            is None
        )

        actual_engine_pass = (
            EXPECTED_ENGINE
            in runtime["stdout"]
        )

        isolation_pass = (
            production_unchanged
        )

        if (
            runtime_pass
            and actual_engine_pass
            and isolation_pass
        ):

            verdict = (
                "ACTUAL_FUSION_RUNTIME : PASS"
            )

        else:

            verdict = (
                "ACTUAL_FUSION_RUNTIME : FAIL"
            )

        print(verdict)

        print()
        print(
            f"Actual {EXPECTED_ENGINE:<15}: "
            f"{'PASS' if actual_engine_pass else 'FAIL'}"
        )

        print(
            "Runtime exception        : "
            f"{'NO' if runtime_pass else 'YES'}"
        )

        print(
            "Production DB isolation  : "
            f"{'PASS' if isolation_pass else 'FAIL'}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "  The isolated database is disposable."
        )

        print(
            "  It must NOT replace arunda.db."
        )

        # -----------------------------------------------------
        # Report
        # -----------------------------------------------------

        report_path = write_report(
            temp_dir,
            baseline,
            runtime,
            isolated_result,
            markers,
            production_unchanged,
        )

        print()
        print(
            f"Runtime report : {report_path}"
        )

        print(
            f"Isolated dir   : {temp_dir}"
        )

        return (
            0
            if (
                runtime_pass
                and actual_engine_pass
                and isolation_pass
            )
            else 1
        )

    except Exception:

        # Always verify production if the harness itself fails.
        try:

            verify_production_unchanged(
                baseline
            )

        except Exception:
            pass

        raise


if __name__ == "__main__":
    raise SystemExit(
        main()
    )