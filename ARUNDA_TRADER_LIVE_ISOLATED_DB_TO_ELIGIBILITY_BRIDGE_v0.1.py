from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import sqlite3
import sys
import tempfile
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


# =============================================================================
# ARUNDA TRADER
# LIVE ISOLATED DB -> EXISTING ELIGIBILITY GATE BRIDGE v0.1
# =============================================================================
#
# FORWARD ONLY
#
# This bridge does NOT:
#   - implement eligibility logic
#   - reconstruct signals
#   - infer direction
#   - modify Fusion
#   - create signals
#   - create Order Intents
#   - write production DB
#   - inject synthetic data
#
# It only redirects the EXISTING eligibility gate's production DB connection
# to the disposable isolated live-runtime database.
# =============================================================================


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

# -------------------------------------------------------------------------
# IMPORTANT:
# Use the actual isolated DB path printed by the successful LIVE RUNTIME.
# -------------------------------------------------------------------------

ISOLATED_DB = Path(
    r"C:\Users\ASUS\AppData\Local\Temp"
    r"\arunda_live_launch_zf2lqqx6"
    r"\arunda_live_capture.db"
)

# -------------------------------------------------------------------------
# Existing eligibility gate.
# Change ONLY this filename if the actual filename differs.
# -------------------------------------------------------------------------

ELIGIBILITY_GATE = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)


# =============================================================================
# SAFETY
# =============================================================================

PRODUCTION_DB_WRITE_FORBIDDEN = True
SIGNAL_CREATION_FORBIDDEN = True
SIGNAL_INJECTION_FORBIDDEN = True
SYNTHETIC_DATA_FORBIDDEN = True
DIRECTION_INFERENCE_FORBIDDEN = True
FUSION_REIMPLEMENTATION_FORBIDDEN = True
ORDER_EXECUTION_FORBIDDEN = True


# =============================================================================
# HELPERS
# =============================================================================

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def db_fingerprint(path: Path) -> dict:
    stat = path.stat()

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def sqlite_table_count(
    path: Path,
    table: str,
) -> int:

    conn = sqlite3.connect(path)

    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        return int(row[0])

    finally:
        conn.close()


def load_module(path: Path):

    if not path.exists():
        raise FileNotFoundError(
            f"Eligibility gate not found: {path}"
        )

    module_name = (
        "arunda_existing_eligibility_gate_bridge"
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to load module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


# =============================================================================
# SQLITE REDIRECTION
# =============================================================================

class SQLiteRedirector:

    def __init__(
        self,
        production_db: Path,
        isolated_db: Path,
    ):

        self.production_db = str(
            production_db.resolve()
        )

        self.isolated_db = str(
            isolated_db.resolve()
        )

        self.original_connect = sqlite3.connect

    @staticmethod
    def normalize(value):

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

        normalized = self.normalize(database)

        if normalized == self.production_db:

            print(
                "[BRIDGE] Production DB connection intercepted."
            )

            print(
                "[BRIDGE] Redirecting existing Eligibility Gate ->"
            )

            print(
                f"[BRIDGE] {self.isolated_db}"
            )

            database = self.isolated_db

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
# SNAPSHOT IDENTIFICATION
# =============================================================================

def inspect_latest_snapshot(
    isolated_db: Path,
):

    conn = sqlite3.connect(isolated_db)

    try:

        row = conn.execute(
            """
            SELECT
                snapshot_id,
                COUNT(*) AS rows
            FROM fusion_signals
            WHERE snapshot_id IS NOT NULL
            GROUP BY snapshot_id
            ORDER BY rowid DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "No non-null fusion snapshot exists in isolated DB."
            )

        snapshot_id = row[0]
        row_count = int(row[1])

        return {
            "snapshot_id": snapshot_id,
            "rows": row_count,
        }

    finally:
        conn.close()


# =============================================================================
# PRODUCTION INVARIANT
# =============================================================================

def verify_production_invariant(
    before_fp: dict,
    before_count: int,
):

    after_fp = db_fingerprint(
        PRODUCTION_DB
    )

    after_count = sqlite_table_count(
        PRODUCTION_DB,
        "fusion_signals",
    )

    fingerprint_pass = (
        before_fp == after_fp
    )

    population_pass = (
        before_count == after_count
    )

    return {
        "fingerprint_unchanged": fingerprint_pass,
        "row_count_unchanged": population_pass,
        "pass": (
            fingerprint_pass
            and population_pass
        ),
        "before": before_fp,
        "after": after_fp,
        "before_rows": before_count,
        "after_rows": after_count,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER "
        "LIVE ISOLATED DB -> EXISTING ELIGIBILITY GATE BRIDGE v0.1"
    )
    print("=" * 100)

    print()
    print("FORWARD-ONLY EXECUTION")
    print()
    print(
        "Actual Fusion output -> Existing Eligibility Gate"
    )

    print()
    print(
        "No eligibility logic reimplementation."
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
        "No signal injection."
    )
    print(
        "No Order Intent creation."
    )
    print(
        "No order execution."
    )
    print(
        "Production DB writes : FORBIDDEN"
    )

    # -------------------------------------------------------------------------
    # Preconditions
    # -------------------------------------------------------------------------

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    if not ISOLATED_DB.exists():
        raise FileNotFoundError(
            f"Isolated DB not found: {ISOLATED_DB}"
        )

    if not ELIGIBILITY_GATE.exists():
        raise FileNotFoundError(
            f"Eligibility Gate not found: {ELIGIBILITY_GATE}"
        )

    # -------------------------------------------------------------------------
    # Production baseline
    # -------------------------------------------------------------------------

    before_fp = db_fingerprint(
        PRODUCTION_DB
    )

    before_count = sqlite_table_count(
        PRODUCTION_DB,
        "fusion_signals",
    )

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    print(
        f"Rows   : {before_count}"
    )

    print(
        f"Size   : {before_fp['size']:,}"
    )

    print(
        f"SHA256 : {before_fp['sha256']}"
    )

    # -------------------------------------------------------------------------
    # Isolated DB
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ISOLATED LIVE DATABASE")
    print("=" * 100)

    print(
        f"Database : {ISOLATED_DB}"
    )

    isolated_fp = db_fingerprint(
        ISOLATED_DB
    )

    print(
        f"Size     : {isolated_fp['size']:,}"
    )

    print(
        f"SHA256   : {isolated_fp['sha256']}"
    )

    # -------------------------------------------------------------------------
    # Identify the NEW snapshot produced by actual Fusion runtime.
    # -------------------------------------------------------------------------

    snapshot = inspect_latest_snapshot(
        ISOLATED_DB
    )

    print()
    print("=" * 100)
    print("LIVE FUSION SNAPSHOT")
    print("=" * 100)

    print(
        f"Snapshot : {snapshot['snapshot_id']}"
    )

    print(
        f"Rows     : {snapshot['rows']}"
    )

    # -------------------------------------------------------------------------
    # Load existing gate.
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EXISTING ELIGIBILITY GATE")
    print("=" * 100)

    print(
        f"Gate : {ELIGIBILITY_GATE}"
    )

    gate = load_module(
        ELIGIBILITY_GATE
    )

    if not hasattr(gate, "main"):
        raise RuntimeError(
            "Existing Eligibility Gate does not expose main()."
        )

    print(
        "Gate import : PASS"
    )

    # -------------------------------------------------------------------------
    # Redirect DB connections.
    # -------------------------------------------------------------------------

    redirector = SQLiteRedirector(
        PRODUCTION_DB,
        ISOLATED_DB,
    )

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    runtime_exception = None
    return_value = None

    redirector.install()

    try:

        print()
        print("=" * 100)
        print("EXECUTING EXISTING ELIGIBILITY GATE")
        print("=" * 100)

        print()
        print(
            "Database routing:"
        )

        print(
            f"  Requested production DB : {PRODUCTION_DB}"
        )

        print(
            f"  Actual runtime DB      : {ISOLATED_DB}"
        )

        print()
        print(
            "Eligibility logic : EXISTING GATE"
        )

        print(
            "Fusion logic      : EXISTING FUSION OUTPUT"
        )

        print(
            "Reconstruction    : NONE"
        )

        print(
            "Inference         : NONE"
        )

        print()

        with redirect_stdout(
            stdout_buffer
        ), redirect_stderr(
            stderr_buffer
        ):

            return_value = gate.main()

    except Exception as exc:

        runtime_exception = exc

    finally:

        redirector.restore()

    # -------------------------------------------------------------------------
    # Runtime output
    # -------------------------------------------------------------------------

    stdout_text = stdout_buffer.getvalue()
    stderr_text = stderr_buffer.getvalue()

    print(
        stdout_text,
        end=""
    )

    if stderr_text.strip():

        print()
        print("=" * 100)
        print("ELIGIBILITY GATE STDERR")
        print("=" * 100)

        print(
            stderr_text
        )

    print()
    print("=" * 100)
    print("ELIGIBILITY BRIDGE RUNTIME")
    print("=" * 100)

    print(
        "Runtime exception : "
        f"{'NONE' if runtime_exception is None else 'PRESENT'}"
    )

    if runtime_exception is not None:

        print()
        traceback.print_exception(
            type(runtime_exception),
            runtime_exception,
            runtime_exception.__traceback__,
        )

    # -------------------------------------------------------------------------
    # Production invariant
    # -------------------------------------------------------------------------

    invariant = verify_production_invariant(
        before_fp,
        before_count,
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(
        "SHA256 : "
        f"{'UNCHANGED' if invariant['fingerprint_unchanged'] else 'CHANGED'}"
    )

    print(
        "Rows   : "
        f"{'UNCHANGED' if invariant['row_count_unchanged'] else 'CHANGED'}"
    )

    print()
    print(
        "PRODUCTION DB INVARIANT : "
        f"{'PASS' if invariant['pass'] else 'FAIL'}"
    )

    # -------------------------------------------------------------------------
    # Final bridge verdict
    # -------------------------------------------------------------------------

    bridge_pass = (
        runtime_exception is None
        and invariant["pass"]
    )

    print()
    print("=" * 100)
    print("LIVE ISOLATED DB -> ELIGIBILITY GATE VERDICT")
    print("=" * 100)

    print(
        f"Bridge execution : "
        f"{'PASS' if bridge_pass else 'FAIL'}"
    )

    print(
        f"Existing Gate    : "
        f"{'EXECUTED' if runtime_exception is None else 'FAILED'}"
    )

    print(
        f"Live snapshot    : {snapshot['snapshot_id']}"
    )

    print(
        f"Snapshot rows    : {snapshot['rows']}"
    )

    print(
        "Production DB     : "
        f"{'UNTOUCHED' if invariant['pass'] else 'CHANGED'}"
    )

    print()
    print(
        "NEXT DECISION:"
    )

    print(
        "  The Eligibility Gate result above is authoritative."
    )

    print(
        "  If TRADE_ELIGIBLE > 0 -> proceed directly to Order Intent."
    )

    print(
        "  If TRADE_ELIGIBLE = 0 -> accept NO_TRADE and stop."
    )

    print()
    print(
        "No Order Intent was created by this bridge."
    )

    print(
        "No order was submitted."
    )

    print(
        "No production DB write was permitted."
    )

    print("=" * 100)

    return 0 if bridge_pass else 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
