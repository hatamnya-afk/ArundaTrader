# -*- coding: utf-8 -*-

"""
==============================================================================================
OUTCOME v0.3 FUSION DIRECTION WRITER FORENSIC v0.1
==============================================================================================

PURPOSE
-------
Identify the upstream production writer responsible for populating:

    fusion_signals.direction

This forensic stage exists because:

    fusion_signals
        └── direction
              ├── VALID : LONG / SHORT / FLAT
              └── NULL  : unresolved upstream provenance

IMPORTANT
---------
This script does NOT infer direction.

It does NOT derive direction from:
    - score
    - fused_score
    - market movement
    - price
    - technical indicators
    - confidence
    - regime
    - any other field

MODE
----
READ ONLY FORENSIC

NO production database writes.
NO production source modifications.
NO schema modifications.

FORBIDDEN
---------
Synthetic data
Interpolation
Forward fill
Back fill
Direction inference
Outcome repair
Signal repair
Tolerance modification
Production execution

==============================================================================================
"""

from __future__ import annotations

import ast
import os
import re
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone


# ==============================================================================================
# CONFIG
# ==============================================================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

EXPECTED_DIRECTIONS = {"LONG", "SHORT", "FLAT"}

ENGINE_NAME = "signal_outcome_engine.py"
EXPECTED_OUTCOME_VERSION = "OUTCOME_v0.3.2"

SCRIPT_VERSION = "OUTCOME_v0.3_FUSION_DIRECTION_WRITER_FORENSIC_v0.1"


# ==============================================================================================
# DISPLAY
# ==============================================================================================

WIDTH = 94


def line(char="=", width=WIDTH):
    print(char * width)


def title(text):
    line("=")
    print(text)
    line("=")


def section(text):
    print()
    line("=")
    print(text)
    line("=")


def subsection(text):
    print()
    line("-")
    print(text)
    line("-")


# ==============================================================================================
# SAFETY
# ==============================================================================================

FORBIDDEN_SQL = re.compile(
    r"""
    \b(
        INSERT
        |UPDATE
        |DELETE
        |ALTER
        |CREATE
        |DROP
        |REPLACE
        |VACUUM
        |ATTACH
        |DETACH
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def assert_read_only_sql(sql: str):
    """
    Safety gate.

    This forensic script is allowed to execute SELECT / PRAGMA only.
    """
    if FORBIDDEN_SQL.search(sql):
        raise RuntimeError(
            "SAFETY ABORT: forbidden SQL detected:\n"
            + sql
        )


def readonly_connect(db_path: Path):
    """
    Open SQLite database using read-only URI mode.
    """
    uri = f"file:{db_path.as_posix()}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==============================================================================================
# DATABASE HELPERS
# ==============================================================================================

def table_exists(conn, table_name):
    sql = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
    """

    assert_read_only_sql(sql)

    row = conn.execute(sql, (table_name,)).fetchone()

    return row is not None


def get_columns(conn, table_name):
    sql = f'PRAGMA table_info("{table_name}")'

    assert_read_only_sql(sql)

    rows = conn.execute(sql).fetchall()

    return [row["name"] for row in rows]


def scalar(conn, sql, params=()):
    assert_read_only_sql(sql)

    row = conn.execute(sql, params).fetchone()

    if row is None:
        return None

    return row[0]


# ==============================================================================================
# DATABASE STRUCTURE
# ==============================================================================================

def database_structure_check(conn):

    section("DATABASE STRUCTURE CHECK")

    for table in [
        "fusion_signals",
        "signal_outcomes",
        "hunter_signals",
        "news_signals",
        "opportunity_signals",
    ]:

        exists = table_exists(conn, table)

        print(
            f"{table:<30} | "
            f"{'FOUND' if exists else 'NOT FOUND'}"
        )

    if not table_exists(conn, TARGET_TABLE):
        raise RuntimeError(
            "fusion_signals table does not exist."
        )

    columns = get_columns(conn, TARGET_TABLE)

    print()
    print("fusion_signals columns:")
    print()

    for column in columns:
        print(f"  - {column}")


# ==============================================================================================
# FUSION POPULATION FORENSIC
# ==============================================================================================

def fusion_population_forensic(conn):

    section("CURRENT FUSION DIRECTION POPULATION")

    total = scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM fusion_signals
        """
    )

    null_direction = scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NULL
        """
    )

    empty_direction = scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NOT NULL
          AND TRIM(direction) = ''
        """
    )

    valid_direction = scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IN ('LONG', 'SHORT', 'FLAT')
        """
    )

    invalid_direction = scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NOT NULL
          AND TRIM(direction) <> ''
          AND direction NOT IN ('LONG', 'SHORT', 'FLAT')
        """
    )

    print(f"Total fusion_signals rows : {total}")
    print(f"Valid direction rows      : {valid_direction}")
    print(f"NULL direction rows       : {null_direction}")
    print(f"Empty direction rows      : {empty_direction}")
    print(f"Invalid direction rows    : {invalid_direction}")

    print()
    print("Direction distribution:")

    sql = """
        SELECT
            direction,
            COUNT(*) AS count
        FROM fusion_signals
        GROUP BY direction
        ORDER BY count DESC
    """

    assert_read_only_sql(sql)

    rows = conn.execute(sql).fetchall()

    for row in rows:
        print(
            f"  {str(row['direction']):<12} | "
            f"{row['count']}"
        )


# ==============================================================================================
# NULL SIGNAL IDENTITIES
# ==============================================================================================

def show_null_direction_signals(conn):

    section("NULL DIRECTION SIGNAL IDENTITIES")

    sql = """
        SELECT
            id,
            asset,
            timestamp,
            fused_score
        FROM fusion_signals
        WHERE direction IS NULL
        ORDER BY id ASC
    """

    assert_read_only_sql(sql)

    rows = conn.execute(sql).fetchall()

    print(f"NULL direction rows : {len(rows)}")
    print()

    if not rows:
        print("No NULL direction records.")
        return

    for row in rows:

        print(
            f"Signal #{row['id']:<5} | "
            f"{str(row['asset']):<6} | "
            f"timestamp={row['timestamp']} | "
            f"fused_score={row['fused_score']}"
        )


# ==============================================================================================
# SOURCE FILE DISCOVERY
# ==============================================================================================

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "_backups",
}


def discover_python_files():

    files = []

    if not PROJECT_ROOT.exists():
        return files

    for root, dirs, filenames in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in filenames:

            if not filename.lower().endswith(".py"):
                continue

            path = Path(root) / filename

            # Never treat this forensic script as production writer.
            if path.resolve() == Path(__file__).resolve():
                continue

            files.append(path)

    return sorted(files)


# ==============================================================================================
# SOURCE CONTEXT
# ==============================================================================================

def read_source(path: Path):

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        try:
            return path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )

        except Exception:

            return None


def context_lines(lines, line_number, radius=5):

    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)

    output = []

    for n in range(start, end + 1):

        marker = ">>" if n == line_number else "  "

        output.append(
            f"{marker} {n:5d} | {lines[n - 1]}"
        )

    return output


# ==============================================================================================
# AST ANALYSIS
# ==============================================================================================

class DirectionWriterVisitor(ast.NodeVisitor):

    def __init__(self, source_lines):

        self.source_lines = source_lines

        self.findings = []

    def add(self, line, category, detail):

        self.findings.append({
            "line": line,
            "category": category,
            "detail": detail,
        })

    def visit_Call(self, node):

        try:
            source_segment = ast.get_source_segment(
                "\n".join(self.source_lines),
                node,
            ) or ""
        except Exception:
            source_segment = ""

        normalized = source_segment.lower()

        # ------------------------------------------------------------------
        # INSERT INTO fusion_signals
        # ------------------------------------------------------------------

        if (
            "fusion_signals" in normalized
            and (
                "insert" in normalized
                or "to_sql" in normalized
                or "executemany" in normalized
            )
        ):

            self.add(
                node.lineno,
                "POSSIBLE_WRITE",
                source_segment.strip().replace("\n", " "),
            )

        # ------------------------------------------------------------------
        # SQL execute / executemany containing fusion_signals
        # ------------------------------------------------------------------

        if isinstance(node.func, ast.Attribute):

            function_name = node.func.attr.lower()

            if function_name in {
                "execute",
                "executemany",
                "executescript",
            }:

                for arg in node.args:

                    try:
                        text = ast.literal_eval(arg)

                    except Exception:
                        text = None

                    if isinstance(text, str):

                        if (
                            "fusion_signals" in text.lower()
                            and (
                                "insert" in text.lower()
                                or "update" in text.lower()
                                or "replace" in text.lower()
                            )
                        ):

                            self.add(
                                node.lineno,
                                "SQL_WRITE",
                                text.strip().replace("\n", " "),
                            )

        self.generic_visit(node)

    def visit_Assign(self, node):

        try:
            source_segment = ast.get_source_segment(
                "\n".join(self.source_lines),
                node,
            ) or ""
        except Exception:
            source_segment = ""

        normalized = source_segment.lower()

        if (
            "direction" in normalized
            and (
                "fusion_signals" in normalized
                or "direction" in normalized
            )
        ):

            self.add(
                node.lineno,
                "DIRECTION_ASSIGNMENT",
                source_segment.strip().replace("\n", " "),
            )

        self.generic_visit(node)


# ==============================================================================================
# REGEX FORENSIC
# ==============================================================================================

SOURCE_PATTERNS = [

    (
        "INSERT_FUSION_SIGNALS",
        re.compile(
            r"""
            INSERT
            \s+
            (?:OR\s+(?:IGNORE|REPLACE)\s+)?
            INTO
            \s+
            ["'`]?
            fusion_signals
            ["'`]?
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    (
        "UPDATE_FUSION_SIGNALS",
        re.compile(
            r"""
            UPDATE
            \s+
            ["'`]?
            fusion_signals
            ["'`]?
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    (
        "REPLACE_FUSION_SIGNALS",
        re.compile(
            r"""
            REPLACE
            \s+
            INTO
            \s+
            ["'`]?
            fusion_signals
            ["'`]?
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    (
        "FUSION_TO_SQL",
        re.compile(
            r"""
            \.to_sql
            \s*\(
            [^)]*
            fusion_signals
            """,
            re.IGNORECASE | re.VERBOSE | re.DOTALL,
        ),
    ),

    (
        "DIRECTION_COLUMN",
        re.compile(
            r"""
            \bdirection\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),

    (
        "FUSION_TABLE_REFERENCE",
        re.compile(
            r"""
            \bfusion_signals\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    ),
]


def regex_source_scan(path, source):

    findings = []

    lines = source.splitlines()

    for category, pattern in SOURCE_PATTERNS:

        for match in pattern.finditer(source):

            line_number = source.count(
                "\n",
                0,
                match.start(),
            ) + 1

            findings.append({
                "path": path,
                "line": line_number,
                "category": category,
                "text": lines[line_number - 1].strip(),
            })

    return findings


# ==============================================================================================
# SOURCE FORENSIC
# ==============================================================================================

def source_writer_forensic():

    section("UPSTREAM SOURCE WRITER FORENSIC")

    files = discover_python_files()

    print(
        f"Python files scanned : {len(files)}"
    )

    print(
        f"Project root         : {PROJECT_ROOT}"
    )

    all_findings = []

    ast_findings = []

    for path in files:

        source = read_source(path)

        if source is None:
            continue

        regex_findings = regex_source_scan(
            path,
            source,
        )

        all_findings.extend(
            regex_findings
        )

        # AST analysis
        try:

            tree = ast.parse(
                source,
                filename=str(path),
            )

            visitor = DirectionWriterVisitor(
                source.splitlines()
            )

            visitor.visit(tree)

            for finding in visitor.findings:

                ast_findings.append({
                    "path": path,
                    **finding,
                })

        except SyntaxError:
            pass

        except Exception:
            pass

    # ------------------------------------------------------------------
    # SQL writer candidates
    # ------------------------------------------------------------------

    subsection(
        "DIRECT FUSION TABLE WRITE CANDIDATES"
    )

    direct = [
        item
        for item in all_findings
        if item["category"] in {
            "INSERT_FUSION_SIGNALS",
            "UPDATE_FUSION_SIGNALS",
            "REPLACE_FUSION_SIGNALS",
            "FUSION_TO_SQL",
        }
    ]

    # deduplicate
    seen = set()

    unique_direct = []

    for item in direct:

        key = (
            str(item["path"]),
            item["line"],
            item["category"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_direct.append(item)

    if not unique_direct:

        print(
            "No direct fusion_signals writer pattern found."
        )

    else:

        for item in unique_direct:

            print(
                f"{item['category']:<28} | "
                f"{item['path']}:{item['line']}"
            )

            print(
                f"    {item['text']}"
            )

    # ------------------------------------------------------------------
    # AST findings
    # ------------------------------------------------------------------

    subsection(
        "AST DIRECTION / WRITE CANDIDATES"
    )

    if not ast_findings:

        print(
            "No AST direction/write candidates found."
        )

    else:

        seen = set()

        for item in ast_findings:

            key = (
                str(item["path"]),
                item["line"],
                item["category"],
            )

            if key in seen:
                continue

            seen.add(key)

            print(
                f"{item['category']:<24} | "
                f"{item['path']}:{item['line']}"
            )

            print(
                f"    {item['detail']}"
            )

    return unique_direct, ast_findings


# ==============================================================================================
# SOURCE CONTEXT FOR DIRECT WRITERS
# ==============================================================================================

def show_writer_context(direct_findings):

    section("DIRECT WRITER SOURCE CONTEXT")

    if not direct_findings:

        print(
            "No direct writer context available."
        )

        return

    seen = set()

    for item in direct_findings:

        key = (
            str(item["path"]),
            item["line"],
        )

        if key in seen:
            continue

        seen.add(key)

        path = item["path"]

        source = read_source(path)

        if source is None:
            continue

        lines = source.splitlines()

        print()
        print(
            f"FILE     : {path}"
        )

        print(
            f"LINE     : {item['line']}"
        )

        print(
            f"CATEGORY : {item['category']}"
        )

        print()

        for context in context_lines(
            lines,
            item["line"],
            radius=7,
        ):

            print(context)


# ==============================================================================================
# DIRECTION VALUE PROVENANCE
# ==============================================================================================

def direction_value_provenance_forensic():

    section("DIRECTION VALUE PROVENANCE FORENSIC")

    files = discover_python_files()

    candidates = []

    patterns = [

        (
            "DIRECTION_LITERAL",
            re.compile(
                r"""
                \b(direction)\b
                \s*
                =
                \s*
                ["'](LONG|SHORT|FLAT)["']
                """,
                re.IGNORECASE | re.VERBOSE,
            ),
        ),

        (
            "DIRECTION_DEFAULT",
            re.compile(
                r"""
                \b(direction)\b
                .*?
                \bor\b
                .*?
                ["']FLAT["']
                """,
                re.IGNORECASE | re.VERBOSE,
            ),
        ),

        (
            "DIRECTION_FROM_SCORE",
            re.compile(
                r"""
                direction
                .*?
                score
                |
                score
                .*?
                direction
                """,
                re.IGNORECASE | re.VERBOSE,
            ),
        ),

        (
            "DIRECTION_FROM_PRICE",
            re.compile(
                r"""
                direction
                .*?
                price
                |
                price
                .*?
                direction
                """,
                re.IGNORECASE | re.VERBOSE,
            ),
        ),
    ]

    for path in files:

        source = read_source(path)

        if source is None:
            continue

        lines = source.splitlines()

        for category, pattern in patterns:

            for match in pattern.finditer(source):

                line_number = source.count(
                    "\n",
                    0,
                    match.start(),
                ) + 1

                candidates.append({
                    "path": path,
                    "line": line_number,
                    "category": category,
                    "text": lines[line_number - 1].strip(),
                })

    if not candidates:

        print(
            "No direction-value provenance candidates found."
        )

        return candidates

    seen = set()

    for item in candidates:

        key = (
            str(item["path"]),
            item["line"],
            item["category"],
        )

        if key in seen:
            continue

        seen.add(key)

        print(
            f"{item['category']:<24} | "
            f"{item['path']}:{item['line']}"
        )

        print(
            f"    {item['text']}"
        )

    return candidates


# ==============================================================================================
# IMPORT / MODULE PROVENANCE
# ==============================================================================================

def module_provenance_forensic():

    section("FUSION SIGNAL MODULE PROVENANCE")

    files = discover_python_files()

    patterns = [
        re.compile(
            r"\bfusion_signals\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bfused_score\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdirection\b",
            re.IGNORECASE,
        ),
    ]

    records = []

    for path in files:

        source = read_source(path)

        if source is None:
            continue

        matches = []

        for pattern in patterns:

            if pattern.search(source):
                matches.append(
                    pattern.pattern
                )

        if matches:

            records.append(
                (
                    path,
                    matches,
                )
            )

    for path, matches in records:

        print(
            f"{path}"
        )

        print(
            f"    matched: {', '.join(matches)}"
        )


# ==============================================================================================
# SIGNAL TIMELINE FORENSIC
# ==============================================================================================

def signal_timeline_forensic(conn):

    section("FUSION SIGNAL TIMELINE")

    sql = """
        SELECT
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp,
            COUNT(*) AS rows,
            COUNT(DISTINCT timestamp) AS distinct_timestamps
        FROM fusion_signals
    """

    assert_read_only_sql(sql)

    row = conn.execute(sql).fetchone()

    print(
        f"Rows                  : {row['rows']}"
    )

    print(
        f"Distinct timestamps   : {row['distinct_timestamps']}"
    )

    print(
        f"First timestamp       : {row['first_timestamp']}"
    )

    print(
        f"Last timestamp        : {row['last_timestamp']}"
    )


# ==============================================================================================
# DIRECTION / SIGNAL CLUSTERING
# ==============================================================================================

def direction_cluster_forensic(conn):

    section("DIRECTION POPULATION BY SIGNAL TIMESTAMP")

    sql = """
        SELECT
            timestamp,
            COUNT(*) AS rows,
            SUM(
                CASE
                    WHEN direction IN ('LONG','SHORT','FLAT')
                    THEN 1
                    ELSE 0
                END
            ) AS valid_direction,
            SUM(
                CASE
                    WHEN direction IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS null_direction
        FROM fusion_signals
        GROUP BY timestamp
        ORDER BY timestamp ASC
    """

    assert_read_only_sql(sql)

    rows = conn.execute(sql).fetchall()

    for row in rows:

        print(
            f"{row['timestamp']} | "
            f"rows={row['rows']:<3} | "
            f"valid={row['valid_direction']:<3} | "
            f"NULL={row['null_direction']:<3}"
        )


# ==============================================================================================
# OUTCOME RECONCILIATION
# ==============================================================================================

def outcome_reconciliation(conn):

    section("OUTCOME / FUSION SIGNAL RECONCILIATION")

    if not table_exists(conn, "signal_outcomes"):

        print(
            "signal_outcomes table not found."
        )

        return

    fusion_ids = {
        row[0]
        for row in conn.execute(
            """
            SELECT id
            FROM fusion_signals
            """
        ).fetchall()
    }

    outcome_ids = {
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT signal_id
            FROM signal_outcomes
            WHERE signal_id IS NOT NULL
            """
        ).fetchall()
    }

    eligible_ids = {
        row[0]
        for row in conn.execute(
            """
            SELECT id
            FROM fusion_signals
            WHERE direction IN ('LONG','SHORT','FLAT')
            """
        ).fetchall()
    }

    missing_eligible = sorted(
        eligible_ids - outcome_ids
    )

    orphan_outcomes = sorted(
        outcome_ids - fusion_ids
    )

    print(
        f"Fusion signal IDs              : "
        f"{len(fusion_ids)}"
    )

    print(
        f"Direction-valid signal IDs     : "
        f"{len(eligible_ids)}"
    )

    print(
        f"Outcome signal IDs             : "
        f"{len(outcome_ids)}"
    )

    print(
        f"Eligible IDs missing outcomes  : "
        f"{len(missing_eligible)}"
    )

    print(
        f"Outcome IDs absent from Fusion : "
        f"{len(orphan_outcomes)}"
    )

    if missing_eligible:

        print()
        print(
            "Eligible IDs missing from outcomes:"
        )

        print(
            missing_eligible
        )

    if orphan_outcomes:

        print()
        print(
            "Outcome IDs absent from current fusion_signals:"
        )

        print(
            orphan_outcomes
        )


# ==============================================================================================
# PRODUCTION ENGINE CHECK
# ==============================================================================================

def production_engine_check():

    section("PRODUCTION OUTCOME ENGINE CHECK")

    engine_path = PROJECT_ROOT / ENGINE_NAME

    if not engine_path.exists():

        print(
            f"{ENGINE_NAME} : NOT FOUND"
        )

        return

    size = engine_path.stat().st_size

    source = read_source(engine_path) or ""

    version_found = (
        EXPECTED_OUTCOME_VERSION
        in source
    )

    print(
        f"{ENGINE_NAME:<30} : FOUND"
    )

    print(
        f"Size{'':<25} : {size:,} bytes"
    )

    print(
        f"{EXPECTED_OUTCOME_VERSION:<30} : "
        f"{'FOUND' if version_found else 'NOT FOUND'}"
    )

    print()
    print(
        "Production Outcome Engine is treated as"
    )

    print(
        "CONSUMER of fusion_signals.direction,"
    )

    print(
        "not as provenance origin."
    )


# ==============================================================================================
# ROOT CAUSE CLASSIFICATION
# ==============================================================================================

def root_cause_classification(
    direct_findings,
    direction_candidates,
):

    section("ROOT-CAUSE CLASSIFICATION")

    print(
        "Current production evidence:"
    )

    print()

    print(
        "1. fusion_signals.direction contains NULL records."
    )

    print(
        "2. Outcome engine consumes direction."
    )

    print(
        "3. Outcome engine is not treated as direction provenance."
    )

    print(
        "4. This forensic stage does not infer direction."
    )

    print()

    direct_writer_count = len(direct_findings)

    if direct_writer_count == 0:

        print(
            "PROVENANCE STATUS:"
        )

        print(
            "NO DIRECT FUSION WRITER IDENTIFIED"
        )

        print()

        print(
            "The upstream writer remains unresolved."
        )

    elif direct_writer_count == 1:

        print(
            "PROVENANCE STATUS:"
        )

        print(
            "ONE DIRECT FUSION WRITER CANDIDATE IDENTIFIED"
        )

    else:

        print(
            "PROVENANCE STATUS:"
        )

        print(
            f"{direct_writer_count} DIRECT FUSION WRITER "
            f"CANDIDATES IDENTIFIED"
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "A source location is a CANDIDATE until its runtime"
    )

    print(
        "execution relationship with fusion_signals is proven."
    )


# ==============================================================================================
# FINAL SAFETY VERDICT
# ==============================================================================================

def final_safety_verdict():

    section("FINAL SAFETY VERDICT")

    print(
        "Database writes       : NONE"
    )

    print(
        "INSERT                : NONE EXECUTED"
    )

    print(
        "UPDATE                : NONE EXECUTED"
    )

    print(
        "DELETE                : NONE EXECUTED"
    )

    print(
        "ALTER                 : NONE EXECUTED"
    )

    print(
        "CREATE                : NONE EXECUTED"
    )

    print(
        "Source files modified: NO"
    )

    print(
        "Production DB modified: NO"
    )

    print(
        "Tolerance modified    : NO"
    )

    print(
        "Direction inferred    : NO"
    )

    print(
        "Direction repaired    : NO"
    )

    print(
        "Synthetic data        : NOT USED"
    )

    print(
        "Interpolation         : NOT USED"
    )

    print(
        "Forward fill          : NOT USED"
    )

    print(
        "Back fill             : NOT USED"
    )


# ==============================================================================================
# CONCLUSION
# ==============================================================================================

def forensic_conclusion(
    direct_findings,
):

    section("FORENSIC CONCLUSION")

    if direct_findings:

        print(
            "Direct fusion_signals writer candidate(s) were identified."
        )

        print()

        print(
            "NEXT ACTION:"
        )

        print(
            "Perform runtime writer-boundary verification."
        )

        print()

        print(
            "The next stage must prove:"
        )

        print(
            "    upstream writer"
        )

        print(
            "        -> direction value construction"
        )

        print(
            "        -> fusion_signals write"
        )

        print(
            "        -> signal row identity"
        )

        print(
            "        -> NULL direction origin"
        )

        print()

        print(
            "NO eligibility repair is authorized yet."
        )

    else:

        print(
            "No direct fusion_signals writer was identified "
            "in the scanned Python source."
        )

        print()

        print(
            "The NULL direction provenance remains unresolved."
        )

        print()

        print(
            "NEXT ACTION:"
        )

        print(
            "Expand provenance search to:"
        )

        print(
            "    - imported modules"
        )

        print(
            "    - class methods"
        )

        print(
            "    - helper writers"
        )

        print(
            "    - dataframe / pandas persistence"
        )

        print(
            "    - generic DB writer functions"
        )

        print(
            "    - runtime call chain"
        )

        print()

        print(
            "NO direction inference or repair is authorized."
        )


# ==============================================================================================
# MAIN
# ==============================================================================================

def main():

    title(
        f"{SCRIPT_VERSION}"
    )

    print(
        f"Database          : {DB_PATH.name}"
    )

    print(
        f"Project root      : {PROJECT_ROOT}"
    )

    print(
        f"Target table      : {TARGET_TABLE}"
    )

    print(
        f"Target column     : {TARGET_COLUMN}"
    )

    print(
        "Mode              : READ ONLY"
    )

    print(
        "Production DB     : UNMODIFIED"
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

    # ------------------------------------------------------------------
    # DB
    # ------------------------------------------------------------------

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = readonly_connect(DB_PATH)

    try:

        database_structure_check(
            conn
        )

        fusion_population_forensic(
            conn
        )

        show_null_direction_signals(
            conn
        )

        signal_timeline_forensic(
            conn
        )

        direction_cluster_forensic(
            conn
        )

        production_engine_check()

        direct_findings, ast_findings = (
            source_writer_forensic()
        )

        show_writer_context(
            direct_findings
        )

        direction_candidates = (
            direction_value_provenance_forensic()
        )

        module_provenance_forensic()

        outcome_reconciliation(
            conn
        )

        root_cause_classification(
            direct_findings,
            direction_candidates,
        )

        final_safety_verdict()

        forensic_conclusion(
            direct_findings
        )

    finally:

        conn.close()

    print()
    line("=")
    print("FORENSIC COMPLETE.")
    line("=")


if __name__ == "__main__":
    main()