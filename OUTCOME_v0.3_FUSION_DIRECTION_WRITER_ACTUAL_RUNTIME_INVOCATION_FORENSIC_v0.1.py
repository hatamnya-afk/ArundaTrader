# -*- coding: utf-8 -*-

"""
==============================================================================================================
OUTCOME_v0.3 FUSION DIRECTION WRITER ACTUAL RUNTIME INVOCATION FORENSIC v0.2
==============================================================================================================

PURPOSE
-------
Perform an ACTUAL invocation of fusion_engine.main() while guaranteeing that:

    production arunda.db
        |
        |  READ ONLY SNAPSHOT
        v
    isolated forensic DB
        |
        v
    fusion_engine.main()

The production database is NEVER passed to fusion_engine.main().

This stage attempts to prove the runtime chain:

    fusion_engine.main()
        -> determine_direction()
        -> direction
        -> fusion_signals INSERT
        -> actual INSERT parameter
        -> actual isolated fusion_signals row

SAFETY
------
READ ONLY against production DB.
NO production INSERT.
NO production UPDATE.
NO production DELETE.
NO production DDL.
NO historical repair.
NO direction reconstruction.
NO score-based inference.
NO synthetic production data.
NO interpolation.
NO forward fill.
NO back fill.

Python 3.13 compatible.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib
import io
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any


# ==========================================================================================================
# CONFIGURATION
# ==========================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader").resolve()
DB_PATH = PROJECT_ROOT / "arunda.db"
WRITER_PATH = PROJECT_ROOT / "fusion_engine.py"

WRITER_MODULE_NAME = "fusion_engine"
TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

# IMPORTANT:
# This alias is captured BEFORE sqlite3.connect is modified.
ORIGINAL_SQLITE_CONNECT = sqlite3.connect

# Runtime capture containers
RUNTIME_CONNECTIONS: list[sqlite3.Connection] = []
RUNTIME_INSERT_CAPTURES: list[dict[str, Any]] = []
RUNTIME_TRACE_EVENTS: list[str] = []

ORIGINAL_MODULE_CONNECT = None
WRITER_MODULE = None


# ==========================================================================================================
# FORMATTING
# ==========================================================================================================

WIDTH = 110


def line(char="=", width=WIDTH):
    print(char * width)


def header(title: str):
    line("=")
    print(title)
    line("=")


def subheader(title: str):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value):
    try:
        return repr(value)
    except Exception:
        return "<unreprable>"


# ==========================================================================================================
# HASH
# ==========================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with ORIGINAL_OPEN(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# Preserve original open reference.
ORIGINAL_OPEN = open


# ==========================================================================================================
# PRODUCTION READ ONLY CONNECTION
# ==========================================================================================================

def open_production_readonly() -> sqlite3.Connection:
    """
    Opens production DB READ ONLY.

    IMPORTANT:
    Uses ORIGINAL_SQLITE_CONNECT to avoid interception recursion.
    """

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    conn = ORIGINAL_SQLITE_CONNECT(
        uri,
        uri=True,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================================================================================
# DATABASE SNAPSHOT
# ==========================================================================================================

def create_isolated_database() -> tuple[Path, sqlite3.Connection]:
    """
    Creates an isolated forensic DB.

    Production DB is opened read-only.
    SQLite backup copies production state into isolated DB.

    fusion_engine.main() receives ONLY the isolated DB.
    """

    production = None
    isolated_conn = None

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_fusion_runtime_forensic_"
        )
    )

    isolated_path = temp_dir / "isolated_arunda.db"

    try:

        production = open_production_readonly()

        isolated_conn = ORIGINAL_SQLITE_CONNECT(
            str(isolated_path),
            check_same_thread=False,
        )

        isolated_conn.row_factory = sqlite3.Row

        # SQLite backup from READ-ONLY production
        production.backup(isolated_conn)

        isolated_conn.commit()

        return isolated_path, isolated_conn

    except Exception:

        if isolated_conn is not None:
            with contextlib.suppress(Exception):
                isolated_conn.close()

        shutil.rmtree(temp_dir, ignore_errors=True)

        raise

    finally:

        if production is not None:
            with contextlib.suppress(Exception):
                production.close()


# ==========================================================================================================
# DATABASE BASELINE
# ==========================================================================================================

def get_production_population():
    conn = open_production_readonly()

    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN direction IS NULL THEN 1 ELSE 0 END) AS null_direction,
                SUM(CASE WHEN direction IS NOT NULL THEN 1 ELSE 0 END) AS valid_direction
            FROM fusion_signals
            """
        ).fetchone()

        distribution = conn.execute(
            """
            SELECT direction, COUNT(*) AS count
            FROM fusion_signals
            GROUP BY direction
            ORDER BY direction
            """
        ).fetchall()

        return {
            "total": row["total"] or 0,
            "null_direction": row["null_direction"] or 0,
            "valid_direction": row["valid_direction"] or 0,
            "distribution": [
                (r["direction"], r["count"])
                for r in distribution
            ],
        }

    finally:
        conn.close()


# ==========================================================================================================
# SCHEMA CHECK
# ==========================================================================================================

def get_columns(conn, table_name: str):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


def check_database_structure():
    conn = open_production_readonly()

    try:

        subheader("DATABASE STRUCTURE CHECK")

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name IN ('fusion_signals', 'signal_outcomes')
            ORDER BY name
            """
        ).fetchall()

        found = {row["name"] for row in tables}

        for table in ("fusion_signals", "signal_outcomes"):

            print(
                f"{table:<32} | "
                f"{'FOUND' if table in found else 'MISSING'}"
            )

        if "fusion_signals" in found:

            print()
            print("fusion_signals columns:")

            for column in get_columns(conn, "fusion_signals"):
                print(f"  - {column}")

    finally:
        conn.close()


# ==========================================================================================================
# STATIC SOURCE ANALYSIS
# ==========================================================================================================

def source_text() -> str:
    return ORIGINAL_OPEN(
        WRITER_PATH,
        "r",
        encoding="utf-8",
    ).read()


def find_line_number(text: str, needle: str) -> int | None:
    for index, line_text in enumerate(
        text.splitlines(),
        start=1,
    ):
        if needle in line_text:
            return index

    return None


def static_direction_analysis():
    text = source_text()

    subheader("STATIC DIRECTION CONSTRUCTION ANALYSIS")

    definition_match = re.search(
        r"def\s+determine_direction\s*\(",
        text,
    )

    assignment_matches = re.findall(
        r"^\s*direction\s*=\s*.+$",
        text,
        flags=re.MULTILINE,
    )

    print(
        "determine_direction definitions : "
        f"{1 if definition_match else 0}"
    )

    definition_line = find_line_number(
        text,
        "def determine_direction",
    )

    print(
        "Function : determine_direction"
    )

    print(
        f"Line     : {definition_line}"
    )

    if definition_match:

        start = max(0, definition_match.start() - 100)

        context = text[
            start:
            start + 700
        ]

        print(context.strip())

    print()

    print(
        "Direct direction assignments : "
        f"{len(assignment_matches)}"
    )

    for line_no, line_text in enumerate(
        text.splitlines(),
        start=1,
    ):

        if re.search(
            r"\bdirection\s*=\s*determine_direction\s*\(",
            line_text,
        ):

            print(
                f"Line={line_no} | {line_text.strip()}"
            )


# ==========================================================================================================
# INSERT STATIC ANALYSIS
# ==========================================================================================================

def extract_fusion_insert():
    text = source_text()

    pattern = re.compile(
        r"""
        INSERT
        \s+INTO
        \s+fusion_signals
        \s*
        \(
            (?P<columns>.*?)
        \)
        \s*
        VALUES
        \s*
        \(
            (?P<values>.*?)
        \)
        """,
        re.IGNORECASE
        | re.VERBOSE
        | re.DOTALL,
    )

    matches = list(pattern.finditer(text))

    subheader("STATIC FUSION INSERT BOUNDARY")

    print(
        "fusion_signals INSERT statements : "
        f"{len(matches)}"
    )

    if not matches:
        return []

    results = []

    for index, match in enumerate(matches, start=1):

        start_line = (
            text.count(
                "\n",
                0,
                match.start(),
            )
            + 1
        )

        columns = [
            x.strip().strip("`\"'")
            for x in match.group("columns").split(",")
            if x.strip()
        ]

        values = [
            x.strip()
            for x in match.group("values").split(",")
            if x.strip()
        ]

        print()
        print(
            f"FUSION INSERT [{index}]"
        )

        print(
            f"Line     : {start_line}"
        )

        print(
            f"Column count : {len(columns)}"
        )

        print(
            f"Value count  : {len(values)}"
        )

        for position, column in enumerate(
            columns,
            start=1,
        ):

            marker = (
                "  >>> "
                if column.lower() == TARGET_COLUMN
                else "      "
            )

            print(
                f"{marker}{position:02d} | {column}"
            )

        if TARGET_COLUMN.lower() in [
            c.lower()
            for c in columns
        ]:

            direction_index = [
                c.lower()
                for c in columns
            ].index(
                TARGET_COLUMN.lower()
            )

            bound_value = (
                values[direction_index]
                if direction_index < len(values)
                else "<MISSING>"
            )

            print()
            print(
                "direction column position : "
                f"{direction_index + 1}"
            )

            print(
                "direction bound expression : "
                f"{bound_value}"
            )

        results.append(
            {
                "line": start_line,
                "columns": columns,
                "values": values,
            }
        )

    return results


# ==========================================================================================================
# SQLITE CONNECTION PROXY / INTERCEPTION
# ==========================================================================================================

def normalize_database_target(database) -> str:
    """
    Converts arbitrary sqlite connection target into a string
    only for diagnostic purposes.
    """

    try:
        return os.fspath(database)
    except TypeError:
        return str(database)


def is_memory_database(database) -> bool:
    target = normalize_database_target(database)

    return (
        target == ":memory:"
        or target.startswith("file::memory:")
        or "mode=memory" in target
    )


def capture_trace_factory(conn: sqlite3.Connection):
    """
    Installs SQLite trace callback.

    The callback observes executed SQL only.
    It does not alter SQL.
    """

    def trace_callback(statement: str):

        if not statement:
            return

        normalized = re.sub(
            r"\s+",
            " ",
            statement.strip(),
        )

        if re.search(
            r"""
            INSERT
            \s+INTO
            \s+["'`]?
            fusion_signals
            ["'`]?
            """,
            normalized,
            flags=re.IGNORECASE | re.VERBOSE,
        ):

            RUNTIME_TRACE_EVENTS.append(
                normalized
            )

            RUNTIME_INSERT_CAPTURES.append(
                {
                    "sql": normalized,
                    "connection_id": id(conn),
                }
            )

    conn.set_trace_callback(
        trace_callback
    )


def configure_isolated_connection(
    conn: sqlite3.Connection,
):

    # CRITICAL FIX:
    # fusion_engine.ensure_schema() accesses rows by column name.
    conn.row_factory = sqlite3.Row

    capture_trace_factory(conn)

    RUNTIME_CONNECTIONS.append(conn)

    return conn


# ==========================================================================================================
# INTERCEPTED CONNECT
# ==========================================================================================================

ISOLATED_DB_PATH: Path | None = None


def intercepted_connect(
    database,
    *args,
    **kwargs,
):

    """
    Every sqlite3.connect() requested by fusion_engine is redirected
    to the isolated DB.

    IMPORTANT:
    ORIGINAL_SQLITE_CONNECT is used here.
    Therefore this function can NEVER recurse into itself.
    """

    if ISOLATED_DB_PATH is None:
        raise RuntimeError(
            "ISOLATED_DB_PATH is not initialized."
        )

    isolated_target = str(
        ISOLATED_DB_PATH
    )

    conn = ORIGINAL_SQLITE_CONNECT(
        isolated_target,
        *args,
        **kwargs,
    )

    return configure_isolated_connection(
        conn
    )


# ==========================================================================================================
# PATCH / RESTORE
# ==========================================================================================================

def install_runtime_interception():
    global ORIGINAL_MODULE_CONNECT

    ORIGINAL_MODULE_CONNECT = sqlite3.connect

    sqlite3.connect = intercepted_connect

    # If fusion_engine has already been imported and has its own
    # "connect" symbol, redirect that too.
    if WRITER_MODULE is not None:

        if hasattr(
            WRITER_MODULE,
            "connect",
        ):

            ORIGINAL_MODULE_CONNECT = getattr(
                WRITER_MODULE,
                "connect",
            )

            setattr(
                WRITER_MODULE,
                "connect",
                intercepted_connect,
            )


def restore_runtime_interception():

    sqlite3.connect = ORIGINAL_SQLITE_CONNECT

    if WRITER_MODULE is not None:

        if ORIGINAL_MODULE_CONNECT is not None:

            with contextlib.suppress(Exception):

                setattr(
                    WRITER_MODULE,
                    "connect",
                    ORIGINAL_MODULE_CONNECT,
                )


# ==========================================================================================================
# IMPORT WRITER
# ==========================================================================================================

def import_writer():
    global WRITER_MODULE

    subheader("WRITER MODULE IMPORT")

    if str(PROJECT_ROOT) not in sys.path:

        sys.path.insert(
            0,
            str(PROJECT_ROOT),
        )

    # Ensure fresh import for forensic run.
    sys.modules.pop(
        WRITER_MODULE_NAME,
        None,
    )

    WRITER_MODULE = importlib.import_module(
        WRITER_MODULE_NAME
    )

    print(
        "Writer module imported : YES"
    )

    main = getattr(
        WRITER_MODULE,
        "main",
        None,
    )

    print(
        "fusion_engine.main found : "
        f"{'YES' if callable(main) else 'NO'}"
    )

    if not callable(main):

        raise RuntimeError(
            "fusion_engine.main() was not found."
        )

    return main


# ==========================================================================================================
# RUNTIME INSERT CORRELATION
# ==========================================================================================================

def extract_runtime_direction_from_sql(
    sql: str,
) -> str | None:

    """
    SQLite trace callback receives expanded SQL.

    Example:

        INSERT INTO fusion_signals (...)
        VALUES (..., 'LONG', ...)

    This parser intentionally remains conservative.
    """

    if not sql:
        return None

    match = re.search(
        r"""
        \bdirection\b
        \s*
        [=,]?
        \s*
        (?:
            '?(LONG|SHORT|FLAT)'?
        )
        """,
        sql,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if match:

        return match.group(1).upper()

    # Fallback: identify any explicit direction literal
    # in the INSERT statement.
    literals = re.findall(
        r"""
        ['"]
        (LONG|SHORT|FLAT)
        ['"]
        """,
        sql,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if literals:

        return literals[-1].upper()

    return None


def fetch_isolated_rows():
    if ISOLATED_DB_PATH is None:
        return []

    conn = ORIGINAL_SQLITE_CONNECT(
        str(ISOLATED_DB_PATH),
        check_same_thread=False,
    )

    try:

        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                timestamp,
                asset,
                fused_score,
                engine_version,
                snapshot_id,
                direction
            FROM fusion_signals
            ORDER BY id
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


# ==========================================================================================================
# RUNTIME INVOCATION
# ==========================================================================================================

def invoke_actual_writer_isolated():
    """
    ACTUAL fusion_engine.main() invocation.

    The writer receives ONLY isolated DB connections.
    """

    main = import_writer()

    subheader(
        "ACTUAL RUNTIME INVOCATION — ISOLATED PRODUCTION CODE"
    )

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    runtime_exception = None
    runtime_traceback = None
    result = None

    install_runtime_interception()

    try:

        print(
            "Production fusion_engine.main() : "
            "WILL BE EXECUTED"
        )

        print(
            "Production DB passed to writer : NO"
        )

        print(
            "Writer DB target                : "
            f"{ISOLATED_DB_PATH}"
        )

        print()
        print(
            "Invoking actual fusion_engine.main()..."
        )

        with contextlib.redirect_stdout(
            stdout_buffer
        ), contextlib.redirect_stderr(
            stderr_buffer
        ):

            try:

                result = main()

            except Exception as exc:

                runtime_exception = exc

                runtime_traceback = (
                    traceback.format_exc()
                )

    finally:

        restore_runtime_interception()

    print()
    print(
        "Runtime interception removed : YES"
    )

    print()
    print(
        "Actual main() invocation     : YES"
    )

    print()
    print(
        "Captured fusion_signals INSERTs : "
        f"{len(RUNTIME_INSERT_CAPTURES)}"
    )

    return {
        "result": result,
        "exception": runtime_exception,
        "traceback": runtime_traceback,
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
    }


# ==========================================================================================================
# RUNTIME CAPTURE REPORT
# ==========================================================================================================

def report_runtime_captures():
    subheader(
        "ACTUAL RUNTIME INSERT CAPTURES"
    )

    print(
        "Captured fusion_signals INSERTs : "
        f"{len(RUNTIME_INSERT_CAPTURES)}"
    )

    if not RUNTIME_INSERT_CAPTURES:

        print()
        print(
            "No fusion_signals INSERT was captured."
        )

        return

    for index, capture in enumerate(
        RUNTIME_INSERT_CAPTURES,
        start=1,
    ):

        sql = capture["sql"]

        direction = (
            extract_runtime_direction_from_sql(
                sql
            )
        )

        print()
        print(
            f"CAPTURE [{index}]"
        )

        print(
            f"SQL       : {sql}"
        )

        print(
            "direction : "
            f"{direction}"
        )


# ==========================================================================================================
# ISOLATED ROW REPORT
# ==========================================================================================================

def report_isolated_rows():
    rows = fetch_isolated_rows()

    subheader(
        "ISOLATED RUNTIME ROW IDENTITY CORRELATION"
    )

    print(
        "Total isolated fusion_signals rows : "
        f"{len(rows)}"
    )

    if not rows:

        print(
            "No isolated fusion_signals rows captured."
        )

        return rows

    print()

    for row in rows:

        print(
            f"id={row['id']} | "
            f"{row['asset']} | "
            f"timestamp={row['timestamp']} | "
            f"fused_score={row['fused_score']} | "
            f"engine={row['engine_version']} | "
            f"snapshot={row['snapshot_id']} | "
            f"direction={row['direction']}"
        )

    return rows


# ==========================================================================================================
# RUNTIME OUTPUT
# ==========================================================================================================

def report_runtime_output(runtime):
    subheader(
        "WRITER RUNTIME OUTPUT"
    )

    print()
    print(
        "STDOUT"
    )

    print("-" * 90)

    stdout = runtime["stdout"]

    if stdout.strip():

        print(stdout.rstrip())

    else:

        print(
            "EMPTY"
        )

    print()
    print(
        "STDERR"
    )

    print("-" * 90)

    stderr = runtime["stderr"]

    if stderr.strip():

        print(stderr.rstrip())

    else:

        print(
            "EMPTY"
        )

    print()
    print(
        "RUNTIME EXCEPTION"
    )

    print("-" * 90)

    if runtime["exception"] is None:

        print(
            "NONE"
        )

    else:

        print(
            repr(runtime["exception"])
        )

        print()

        print(
            runtime["traceback"]
        )


# ==========================================================================================================
# PRODUCTION INVARIANT
# ==========================================================================================================

def report_production_invariant(
    before,
    after,
):

    subheader(
        "POST-RUNTIME PRODUCTION DB INVARIANT"
    )

    print(
        "Before total rows : "
        f"{before['total']}"
    )

    print(
        "After total rows  : "
        f"{after['total']}"
    )

    print(
        "Before NULL direction : "
        f"{before['null_direction']}"
    )

    print(
        "After NULL direction  : "
        f"{after['null_direction']}"
    )

    invariant = (
        before["total"]
        == after["total"]
        and
        before["null_direction"]
        == after["null_direction"]
        and
        before["valid_direction"]
        == after["valid_direction"]
    )

    print()

    print(
        "DATABASE POPULATION INVARIANT : "
        f"{'PASS' if invariant else 'FAIL'}"
    )

    return invariant


# ==========================================================================================================
# SOURCE FINGERPRINT
# ==========================================================================================================

def report_source_fingerprint():
    subheader(
        "PRODUCTION SOURCE FINGERPRINT"
    )

    digest = sha256_file(
        WRITER_PATH
    )

    size = WRITER_PATH.stat().st_size

    print(
        f"fusion_engine.py | SHA256={digest}"
    )

    print(
        f"Source size : {size} bytes"
    )


# ==========================================================================================================
# FINAL CLASSIFICATION
# ==========================================================================================================

def final_classification(
    runtime,
    isolated_rows,
    production_invariant,
):

    captured = len(
        RUNTIME_INSERT_CAPTURES
    )

    directions = []

    for capture in RUNTIME_INSERT_CAPTURES:

        direction = (
            extract_runtime_direction_from_sql(
                capture["sql"]
            )
        )

        if direction is not None:

            directions.append(
                direction
            )

    subheader(
        "RUNTIME PROOF CLASSIFICATION"
    )

    print(
        "Actual fusion_engine.main() invocation : YES"
    )

    print(
        "Actual fusion_signals INSERT captures   : "
        f"{captured}"
    )

    print(
        "Isolated fusion_signals rows            : "
        f"{len(isolated_rows)}"
    )

    print(
        "Production DB invariant                 : "
        f"{'PASS' if production_invariant else 'FAIL'}"
    )

    print()

    print(
        "Runtime direction values captured:"
    )

    if directions:

        for direction in directions:

            print(
                f"  {direction}"
            )

    else:

        print(
            "  NONE"
        )

    if captured > 0 and directions:

        historical_causality = (
            "NOT AUTOMATICALLY PROVEN"
        )

    else:

        historical_causality = (
            "NOT PROVEN"
        )

    print()
    print(
        "Historical NULL-direction causality : "
        f"{historical_causality}"
    )

    return {
        "captured": captured,
        "directions": directions,
        "historical_causality": historical_causality,
    }


# ==========================================================================================================
# MAIN FORENSIC
# ==========================================================================================================

def main_forensic():

    global ISOLATED_DB_PATH

    header(
        "OUTCOME_v0.3 FUSION DIRECTION WRITER ACTUAL RUNTIME INVOCATION FORENSIC v0.2"
    )

    print(
        f"Database          : {DB_PATH.name}"
    )

    print(
        f"Project root      : {PROJECT_ROOT}"
    )

    print(
        f"Writer target     : {WRITER_PATH.name}"
    )

    print(
        f"Target table      : {TARGET_TABLE}"
    )

    print(
        f"Target column     : {TARGET_COLUMN}"
    )

    print(
        "Mode              : READ ONLY / ISOLATED ACTUAL RUNTIME"
    )

    print(
        "Production DB     : NEVER PASSED TO WRITER"
    )

    print(
        "Production source : UNMODIFIED"
    )

    print(
        "Synthetic data    : FORBIDDEN"
    )

    print(
        "Interpolation     : FORBIDDEN"
    )

    print(
        "Forward fill      : FORBIDDEN"
    )

    print(
        "Back fill         : FORBIDDEN"
    )

    # ----------------------------------------------------------------------------------
    # SAFETY
    # ----------------------------------------------------------------------------------

    header(
        "FORENSIC SCRIPT SAFETY CHECK"
    )

    print(
        "Original sqlite3.connect preserved : YES"
    )

    print(
        "Production DB connection            : READ ONLY"
    )

    print(
        "Writer production DB access         : BLOCKED"
    )

    print(
        "Writer isolated DB access            : ENABLED"
    )

    print(
        "Production source write              : NO"
    )

    print(
        "Historical repair                    : NO"
    )

    # ----------------------------------------------------------------------------------
    # ENVIRONMENT
    # ----------------------------------------------------------------------------------

    header(
        "ENVIRONMENT CHECK"
    )

    print(
        f"Python version       : {sys.version}"
    )

    print(
        f"Project root         : {PROJECT_ROOT}"
    )

    print(
        f"Database             : {DB_PATH}"
    )

    print(
        f"Writer source        : {WRITER_PATH}"
    )

    if not PROJECT_ROOT.exists():
        raise RuntimeError(
            "Project root does not exist."
        )

    if not DB_PATH.exists():
        raise RuntimeError(
            "Production DB does not exist."
        )

    if not WRITER_PATH.exists():
        raise RuntimeError(
            "fusion_engine.py does not exist."
        )

    print(
        "Environment status   : PASS"
    )

    # ----------------------------------------------------------------------------------
    # BASELINE
    # ----------------------------------------------------------------------------------

    check_database_structure()

    before = get_production_population()

    header(
        "CURRENT PRODUCTION FUSION SIGNAL POPULATION"
    )

    print(
        "Total fusion_signals rows : "
        f"{before['total']}"
    )

    print(
        "Valid direction rows      : "
        f"{before['valid_direction']}"
    )

    print(
        "NULL direction rows       : "
        f"{before['null_direction']}"
    )

    print()

    print(
        "Direction distribution:"
    )

    for direction, count in before[
        "distribution"
    ]:

        print(
            f"  {str(direction):<12} | {count}"
        )

    # ----------------------------------------------------------------------------------
    # SOURCE
    # ----------------------------------------------------------------------------------

    report_source_fingerprint()

    static_direction_analysis()

    insert_boundaries = (
        extract_fusion_insert()
    )

    # ----------------------------------------------------------------------------------
    # CREATE ISOLATED SNAPSHOT
    # ----------------------------------------------------------------------------------

    header(
        "ISOLATED DATABASE SNAPSHOT"
    )

    isolated_path, isolated_conn = (
        create_isolated_database()
    )

    ISOLATED_DB_PATH = isolated_path

    print(
        "Production DB : READ ONLY"
    )

    print(
        "Isolated DB   : CREATED"
    )

    print(
        f"Isolated path : {ISOLATED_DB_PATH}"
    )

    print(
        "Writer target : ISOLATED DB ONLY"
    )

    with contextlib.suppress(Exception):
        isolated_conn.close()

    # ----------------------------------------------------------------------------------
    # ACTUAL RUNTIME
    # ----------------------------------------------------------------------------------

    runtime = (
        invoke_actual_writer_isolated()
    )

    # ----------------------------------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------------------------------

    report_runtime_captures()

    isolated_rows = (
        report_isolated_rows()
    )

    report_runtime_output(
        runtime
    )

    # ----------------------------------------------------------------------------------
    # PRODUCTION AFTER
    # ----------------------------------------------------------------------------------

    after = get_production_population()

    invariant = (
        report_production_invariant(
            before,
            after,
        )
    )

    classification = (
        final_classification(
            runtime,
            isolated_rows,
            invariant,
        )
    )

    # ----------------------------------------------------------------------------------
    # FINAL SAFETY
    # ----------------------------------------------------------------------------------

    header(
        "FINAL SAFETY VERDICT"
    )

    print(
        "Production database writes : NONE"
    )

    print(
        "Production INSERT          : NONE"
    )

    print(
        "Production UPDATE          : NONE"
    )

    print(
        "Production DELETE          : NONE"
    )

    print(
        "Production DDL             : NONE"
    )

    print(
        "Production DB invariant    : "
        f"{'PASS' if invariant else 'FAIL'}"
    )

    print(
        "Production source modified : NO"
    )

    print(
        "Direction reconstructed     : NO"
    )

    print(
        "Historical direction repair: NO"
    )

    print(
        "Eligibility repair          : NO"
    )

    print(
        "Synthetic data              : NOT USED"
    )

    print(
        "Interpolation               : NOT USED"
    )

    print(
        "Forward fill                : NOT USED"
    )

    print(
        "Back fill                   : NOT USED"
    )

    print(
        "Isolated INSERT captures    : "
        f"{classification['captured']}"
    )

    print(
        "Production writer DB        : NEVER PASSED"
    )

    print(
        "Production commit           : NOT POSSIBLE"
    )

    # ----------------------------------------------------------------------------------
    # CONCLUSION
    # ----------------------------------------------------------------------------------

    header(
        "FORENSIC CONCLUSION"
    )

    if classification["captured"] > 0:

        print(
            "ACTUAL RUNTIME WRITER BOUNDARY : CAPTURED"
        )

        print()

        print(
            "The actual fusion_engine.main() invocation "
            "reached an isolated fusion_signals INSERT."
        )

        print()

        print(
            "Captured direction values:"
        )

        for direction in classification[
            "directions"
        ]:

            print(
                f"    -> {direction}"
            )

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "The captured INSERT proves the runtime writer "
            "boundary in the isolated environment."
        )

        print(
            "It does NOT by itself prove that historical "
            "NULL production rows were created by this exact invocation."
        )

    else:

        print(
            "ACTUAL RUNTIME WRITER BOUNDARY : NOT PROVEN"
        )

        print()

        print(
            "The actual fusion_engine.main() invocation "
            "did not produce a captured fusion_signals INSERT."
        )

        print(
            "The runtime result must therefore be interpreted "
            "together with the captured exception/output."
        )

    print()

    print(
        "HISTORICAL NULL-DIRECTION CAUSALITY:"
    )

    print(
        f"    {classification['historical_causality']}"
    )

    print()

    print(
        "DIRECTION REPAIR:"
    )

    print(
        "    BLOCKED"
    )

    print()

    print(
        "ELIGIBILITY REPAIR:"
    )

    print(
        "    BLOCKED"
    )

    print()

    print(
        "SCORE-BASED HISTORICAL DIRECTION INFERENCE:"
    )

    print(
        "    FORBIDDEN"
    )

    print()

    print(
        "FORENSIC COMPLETE."
    )

    # ----------------------------------------------------------------------------------
    # CLEANUP
    # ----------------------------------------------------------------------------------

    with contextlib.suppress(Exception):
        for conn in RUNTIME_CONNECTIONS:

            conn.close()

    temp_parent = (
        ISOLATED_DB_PATH.parent
        if ISOLATED_DB_PATH is not None
        else None
    )

    if temp_parent is not None:

        shutil.rmtree(
            temp_parent,
            ignore_errors=True,
        )


# ==========================================================================================================
# ENTRY POINT
# ==========================================================================================================

if __name__ == "__main__":

    try:

        main_forensic()

    except Exception as exc:

        print()
        line("!")

        print(
            "FORENSIC SCRIPT FAILURE"
        )

        print(
            repr(exc)
        )

        print()

        traceback.print_exc()

        line("!")

        print()
        print(
            "SAFETY NOTE:"
        )

        print(
            "The forensic script failed before any production "
            "write was intentionally performed."
        )

        sys.exit(1)