# -*- coding: utf-8 -*-

"""
==========================================================================================
OUTCOME v0.3 FUSION DIRECTION WRITER RUNTIME BOUNDARY FORENSIC v0.1
==========================================================================================

PURPOSE
-------
Prove the runtime execution boundary responsible for writing
fusion_signals.direction.

This forensic stage is READ ONLY.

STRICT RULES
------------
- Production DB MUST remain unmodified.
- Production source MUST remain unmodified.
- No INSERT.
- No UPDATE.
- No DELETE.
- No ALTER.
- No CREATE.
- No direction reconstruction.
- No score -> direction inference.
- No synthetic data.
- No interpolation.
- No forward fill.
- No back fill.
- No eligibility repair.

OBJECTIVE
---------
Trace:

    upstream runtime
          |
          v
    direction construction
          |
          v
    fusion_signals INSERT
          |
          v
    actual row identity
          |
          v
    NULL direction origin

The stage distinguishes:

A) direction never constructed
B) direction constructed but lost before INSERT
C) INSERT explicitly receives NULL
D) another writer creates the row
E) different execution path / legacy path
F) runtime relationship remains unproven

IMPORTANT
---------
A source location is NOT considered the writer merely because
it contains the text "INSERT INTO fusion_signals".

Runtime proof is required.

==========================================================================================
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import re
import sqlite3
import sys
import traceback
from pathlib import Path
from collections import defaultdict


# ==========================================================================================
# CONFIGURATION
# ==========================================================================================

ENGINE_VERSION = "OUTCOME_v0.3.2"
FORENSIC_VERSION = "v0.1"

DB_NAME = "arunda.db"
TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / DB_NAME

VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}

PYTHON_EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "_backups",
    "backups",
    "indicator_repair_backups",
}

SOURCE_EXTENSIONS = {".py"}

MAX_CONTEXT_LINES = 8


# ==========================================================================================
# OUTPUT HELPERS
# ==========================================================================================

def print_header(title: str, width: int = 90):
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def print_subheader(title: str, width: int = 90):
    print("\n" + "-" * width)
    print(title)
    print("-" * width)


def safe_text(value):
    if value is None:
        return "NULL"
    return str(value)


def truncate(value, length=180):
    text = safe_text(value)
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


# ==========================================================================================
# DATABASE SAFETY
# ==========================================================================================

def connect_readonly(db_path: Path):
    """
    Open SQLite database through SQLite URI in immutable/read-only mode.

    immutable=1 guarantees that SQLite will not attempt to create journals,
    WAL files, or modify the database.
    """

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    # Explicit defensive settings.
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def verify_read_only_connection(conn):
    """
    Verify SQLite reports query-only mode.
    """

    row = conn.execute("PRAGMA query_only").fetchone()

    if not row or int(row[0]) != 1:
        raise RuntimeError("READ-ONLY connection verification failed.")

    return True


# ==========================================================================================
# SOURCE DISCOVERY
# ==========================================================================================

def iter_python_files(root: Path):
    for current_root, dirs, files in os.walk(root):

        dirs[:] = [
            d for d in dirs
            if d not in PYTHON_EXCLUDED_DIRS
        ]

        current_path = Path(current_root)

        for filename in files:
            path = current_path / filename

            if path.suffix.lower() in SOURCE_EXTENSIONS:
                yield path


def read_source(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            return None
    except Exception:
        return None


def source_hash(source: str):
    return hashlib.sha256(
        source.encode("utf-8", errors="replace")
    ).hexdigest()


# ==========================================================================================
# AST UTILITIES
# ==========================================================================================

def ast_line(node):
    return getattr(node, "lineno", None)


def get_call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []

        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.Str):
        return node.s

    return None


def contains_text(node, text):
    """
    Recursive AST text detection.
    """

    try:
        rendered = ast.unparse(node)
    except Exception:
        rendered = ""

    return text.lower() in rendered.lower()


# ==========================================================================================
# SOURCE INDEX
# ==========================================================================================

class WriterCandidate:
    def __init__(
        self,
        path,
        line,
        function,
        insert_sql,
        direction_context,
        confidence,
    ):
        self.path = path
        self.line = line
        self.function = function
        self.insert_sql = insert_sql
        self.direction_context = direction_context
        self.confidence = confidence

    def display(self):
        return (
            f"{self.path}:{self.line} | "
            f"function={self.function or '<module>'} | "
            f"confidence={self.confidence}"
        )


class DirectionConstruction:
    def __init__(
        self,
        path,
        line,
        function,
        expression,
        category,
    ):
        self.path = path
        self.line = line
        self.function = function
        self.expression = expression
        self.category = category

    def display(self):
        return (
            f"{self.path}:{self.line} | "
            f"function={self.function or '<module>'} | "
            f"{self.category} | "
            f"{truncate(self.expression)}"
        )


def collect_source_candidates(root: Path):

    writers = []
    direction_builders = []

    python_files = list(iter_python_files(root))

    for path in python_files:

        source = read_source(path)

        if not source:
            continue

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        except Exception:
            continue

        function_stack = []

        class Visitor(ast.NodeVisitor):

            def visit_FunctionDef(self, node):
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            def visit_AsyncFunctionDef(self, node):
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            def visit_Call(self, node):

                function_name = (
                    function_stack[-1]
                    if function_stack
                    else "<module>"
                )

                call_name = get_call_name(node.func)

                # ------------------------------------------------------------------
                # Detect direct fusion_signals INSERT
                # ------------------------------------------------------------------

                rendered = ""

                try:
                    rendered = ast.unparse(node)
                except Exception:
                    pass

                if (
                    "fusion_signals" in rendered.lower()
                    and "insert" in rendered.lower()
                ):
                    context = []

                    for child in ast.walk(node):

                        if isinstance(child, ast.Name):
                            if child.id == "direction":
                                context.append(
                                    f"Name(direction) @ line "
                                    f"{ast_line(child)}"
                                )

                        if isinstance(child, ast.Constant):
                            if child.value == "direction":
                                context.append(
                                    f"Literal('direction') @ line "
                                    f"{ast_line(child)}"
                                )

                    writers.append(
                        WriterCandidate(
                            path=path,
                            line=ast_line(node),
                            function=function_name,
                            insert_sql=rendered,
                            direction_context=context,
                            confidence=(
                                "HIGH"
                                if context
                                else "MEDIUM"
                            ),
                        )
                    )

                # ------------------------------------------------------------------
                # Detect direction construction / assignment-like calls
                # ------------------------------------------------------------------

                if "direction" in rendered.lower():

                    if any(
                        token in rendered.lower()
                        for token in (
                            "determine_direction",
                            "direction =",
                            "direction:",
                            "direction,",
                            "direction)",
                            "direction,",
                            '"direction"',
                            "'direction'",
                        )
                    ):
                        direction_builders.append(
                            DirectionConstruction(
                                path=path,
                                line=ast_line(node),
                                function=function_name,
                                expression=rendered,
                                category="DIRECTION_RELATED_CALL",
                            )
                        )

                self.generic_visit(node)

            def visit_Assign(self, node):

                function_name = (
                    function_stack[-1]
                    if function_stack
                    else "<module>"
                )

                for target in node.targets:

                    if (
                        isinstance(target, ast.Name)
                        and target.id == "direction"
                    ):

                        try:
                            expression = ast.unparse(node.value)
                        except Exception:
                            expression = "<unparse failed>"

                        category = classify_direction_expression(
                            expression
                        )

                        direction_builders.append(
                            DirectionConstruction(
                                path=path,
                                line=ast_line(node),
                                function=function_name,
                                expression=expression,
                                category=category,
                            )
                        )

                self.generic_visit(node)

        Visitor().visit(tree)

    return python_files, writers, direction_builders


def classify_direction_expression(expression: str):

    text = expression.lower()

    if "determine_direction" in text:
        return "DETERMINISTIC_DIRECTION_FUNCTION"

    if "direction" in text and "get(" in text:
        return "DIRECTION_FROM_CONTAINER"

    if "direction" in text:
        return "DIRECTION_REFERENCE"

    if "long" in text or "short" in text or "flat" in text:
        return "DIRECTION_LITERAL"

    if "score" in text:
        return "SCORE_RELATED_EXPRESSION"

    return "DIRECTION_ASSIGNMENT"


# ==========================================================================================
# SOURCE CONTEXT
# ==========================================================================================

def source_context(path: Path, line_number: int, radius=MAX_CONTEXT_LINES):

    source = read_source(path)

    if source is None:
        return []

    lines = source.splitlines()

    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)

    result = []

    for number in range(start, end + 1):
        result.append(
            (number, lines[number - 1])
        )

    return result


def print_context(path, line_number, radius=MAX_CONTEXT_LINES):

    for number, text in source_context(
        path,
        line_number,
        radius,
    ):
        marker = ">>" if number == line_number else "  "

        print(
            f"{marker} {number:5d} | {text}"
        )


# ==========================================================================================
# DATABASE SCHEMA
# ==========================================================================================

def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def table_columns(conn, table_name):

    return [
        row["name"]
        for row in conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    ]


# ==========================================================================================
# CURRENT FUSION POPULATION
# ==========================================================================================

def get_fusion_population(conn):

    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            direction,
            engine_version,
            snapshot_id,
            entry_price
        FROM fusion_signals
        ORDER BY id ASC
        """
    ).fetchall()


def print_population_summary(rows):

    total = len(rows)

    valid = [
        row for row in rows
        if row["direction"] in VALID_DIRECTIONS
    ]

    nulls = [
        row for row in rows
        if row["direction"] is None
    ]

    empty = [
        row for row in rows
        if row["direction"] == ""
    ]

    invalid = [
        row for row in rows
        if (
            row["direction"] is not None
            and row["direction"] != ""
            and row["direction"] not in VALID_DIRECTIONS
        )
    ]

    print(f"Total fusion_signals rows : {total}")
    print(f"Valid direction rows      : {len(valid)}")
    print(f"NULL direction rows       : {len(nulls)}")
    print(f"Empty direction rows      : {len(empty)}")
    print(f"Invalid direction rows    : {len(invalid)}")

    distribution = defaultdict(int)

    for row in rows:
        distribution[row["direction"]] += 1

    print("\nDirection distribution:")

    for direction, count in sorted(
        distribution.items(),
        key=lambda item: safe_text(item[0]),
    ):
        print(
            f"  {safe_text(direction):12} | {count}"
        )


# ==========================================================================================
# NULL ROW IDENTITY
# ==========================================================================================

def print_null_rows(rows):

    null_rows = [
        row for row in rows
        if row["direction"] is None
    ]

    print(f"NULL direction rows : {len(null_rows)}")

    for row in null_rows:

        print(
            f"Signal #{row['id']:<5} | "
            f"{safe_text(row['asset']):6} | "
            f"timestamp={safe_text(row['timestamp'])} | "
            f"fused_score={safe_text(row['fused_score'])} | "
            f"snapshot={safe_text(row['snapshot_id'])} | "
            f"engine={safe_text(row['engine_version'])}"
        )


# ==========================================================================================
# TIMELINE
# ==========================================================================================

def print_timeline(rows):

    grouped = defaultdict(
        lambda: {
            "rows": 0,
            "valid": 0,
            "null": 0,
        }
    )

    for row in rows:

        timestamp = row["timestamp"]

        grouped[timestamp]["rows"] += 1

        if row["direction"] in VALID_DIRECTIONS:
            grouped[timestamp]["valid"] += 1

        elif row["direction"] is None:
            grouped[timestamp]["null"] += 1

    print(
        f"Distinct timestamps : {len(grouped)}"
    )

    if rows:

        print(
            f"First timestamp     : {safe_text(rows[0]['timestamp'])}"
        )

        print(
            f"Last timestamp      : {safe_text(rows[-1]['timestamp'])}"
        )

    print()

    for timestamp in sorted(grouped):

        item = grouped[timestamp]

        print(
            f"{timestamp} | "
            f"rows={item['rows']:<3} | "
            f"valid={item['valid']:<3} | "
            f"NULL={item['null']}"
        )


# ==========================================================================================
# WRITER SQL STRUCTURAL FORENSIC
# ==========================================================================================

def extract_insert_blocks(source: str):

    """
    Conservative SQL-like extraction.

    This intentionally avoids the regex inline-flag problem that caused
    the previous forensic script to fail under Python 3.13.

    No regex global inline flags are used.
    """

    pattern = re.compile(
        r"""
        INSERT\s+INTO\s+fusion_signals
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    matches = []

    for match in pattern.finditer(source):

        start = match.start()

        line = source.count(
            "\n",
            0,
            start,
        ) + 1

        end = source.find(
            ")",
            match.end(),
        )

        if end == -1:
            end = min(
                len(source),
                match.end() + 1500,
            )

        block = source[
            start:min(len(source), end + 1)
        ]

        matches.append(
            {
                "line": line,
                "sql": block,
            }
        )

    return matches


def writer_direction_binding(source: str, line: int):

    context = source_context(
        Path("<memory>"),
        line,
    )

    # Not used directly because source is in-memory.
    return context


# ==========================================================================================
# DIRECT INSERT PARAMETER FORENSIC
# ==========================================================================================

def inspect_writer_candidate(candidate: WriterCandidate):

    source = read_source(candidate.path)

    if not source:
        return

    print_subheader(
        f"WRITER CANDIDATE | {candidate.path.name}:{candidate.line}"
    )

    print(
        f"Function   : {candidate.function}"
    )

    print(
        f"Confidence : {candidate.confidence}"
    )

    print(
        f"Path       : {candidate.path}"
    )

    print("\nSource context:")

    print_context(
        candidate.path,
        candidate.line,
    )

    print("\nDirection references near INSERT:")

    if candidate.direction_context:

        for item in candidate.direction_context:
            print(f"  {item}")

    else:
        print("  NONE")


# ==========================================================================================
# AST WRITER DATAFLOW FORENSIC
# ==========================================================================================

def analyze_writer_dataflow(candidate: WriterCandidate):

    source = read_source(candidate.path)

    if not source:
        return {
            "direction_parameter": False,
            "direction_variable": False,
            "determine_direction_call": False,
            "literal_direction": False,
            "unknown": True,
        }

    try:
        tree = ast.parse(
            source,
            filename=str(candidate.path),
        )
    except Exception:
        return {
            "direction_parameter": False,
            "direction_variable": False,
            "determine_direction_call": False,
            "literal_direction": False,
            "unknown": True,
        }

    result = {
        "direction_parameter": False,
        "direction_variable": False,
        "determine_direction_call": False,
        "literal_direction": False,
        "unknown": False,
    }

    target_function = None

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):

            start = getattr(
                node,
                "lineno",
                0,
            )

            end = getattr(
                node,
                "end_lineno",
                start,
            )

            if start <= candidate.line <= end:

                target_function = node
                break

    if target_function is None:
        return result

    # ----------------------------------------------------------------------
    # Function parameters
    # ----------------------------------------------------------------------

    all_args = (
        list(target_function.args.args)
        + list(target_function.args.kwonlyargs)
    )

    for arg in all_args:

        if arg.arg == "direction":
            result["direction_parameter"] = True

    # ----------------------------------------------------------------------
    # Function-local AST
    # ----------------------------------------------------------------------

    for node in ast.walk(target_function):

        if isinstance(node, ast.Name):

            if node.id == "direction":
                result["direction_variable"] = True

        if isinstance(node, ast.Call):

            call_name = get_call_name(node.func)

            if call_name.endswith("determine_direction"):
                result["determine_direction_call"] = True

        if isinstance(node, ast.Constant):

            if node.value in VALID_DIRECTIONS:
                result["literal_direction"] = True

    return result


# ==========================================================================================
# CROSS-MODULE PROVENANCE
# ==========================================================================================

def build_module_provenance(
    python_files,
    writers,
    direction_builders,
):

    print_subheader(
        "DIRECTION CONSTRUCTION CANDIDATES"
    )

    if not direction_builders:

        print("No direction construction candidate detected.")

    else:

        for item in direction_builders:

            print(
                f"DIRECTION | {item.display()}"
            )

    print_subheader(
        "DIRECT fusion_signals WRITER CANDIDATES"
    )

    if not writers:

        print(
            "No direct fusion_signals INSERT candidate detected."
        )

    else:

        print(
            f"Candidates identified : {len(writers)}"
        )

        for index, candidate in enumerate(
            writers,
            start=1,
        ):

            print(
                f"\n[{index}] {candidate.display()}"
            )

            dataflow = analyze_writer_dataflow(
                candidate
            )

            print(
                f"    direction parameter       : "
                f"{dataflow['direction_parameter']}"
            )

            print(
                f"    direction variable        : "
                f"{dataflow['direction_variable']}"
            )

            print(
                f"    determine_direction call  : "
                f"{dataflow['determine_direction_call']}"
            )

            print(
                f"    direction literals        : "
                f"{dataflow['literal_direction']}"
            )


# ==========================================================================================
# PRODUCTION OUTCOME ENGINE CHECK
# ==========================================================================================

def check_outcome_engine():

    path = PROJECT_ROOT / "signal_outcome_engine.py"

    print_subheader(
        "PRODUCTION OUTCOME ENGINE CHECK"
    )

    if not path.exists():

        print(
            "signal_outcome_engine.py : NOT FOUND"
        )

        return

    source = read_source(path) or ""

    print(
        f"signal_outcome_engine.py : FOUND"
    )

    print(
        f"Size                      : {path.stat().st_size:,} bytes"
    )

    print(
        f"{ENGINE_VERSION:<25} : "
        f"{'FOUND' if ENGINE_VERSION in source else 'NOT FOUND'}"
    )

    print(
        "\nProduction Outcome Engine is treated as"
    )

    print(
        "CONSUMER of fusion_signals.direction,"
    )

    print(
        "not as provenance origin."
    )


# ==========================================================================================
# RUNTIME BOUNDARY HEURISTIC
# ==========================================================================================

def runtime_boundary_assessment(
    writers,
    rows,
):

    print_subheader(
        "RUNTIME WRITER BOUNDARY ASSESSMENT"
    )

    null_count = sum(
        1
        for row in rows
        if row["direction"] is None
    )

    valid_count = sum(
        1
        for row in rows
        if row["direction"] in VALID_DIRECTIONS
    )

    print(
        f"Current NULL-direction rows : {null_count}"
    )

    print(
        f"Current valid-direction rows: {valid_count}"
    )

    print(
        f"Direct writer candidates    : {len(writers)}"
    )

    if not writers:

        print(
            "\nSTATUS:"
        )

        print(
            "NO DIRECT FUSION WRITER WAS IDENTIFIED."
        )

        print(
            "Runtime provenance remains UNPROVEN."
        )

        return

    print(
        "\nIMPORTANT:"
    )

    print(
        "Static writer candidates do NOT constitute runtime proof."
    )

    print(
        "\nThe following runtime evidence is required:"
    )

    print(
        "  1. Writer function is actually invoked."
    )

    print(
        "  2. direction construction occurs in that invocation."
    )

    print(
        "  3. The same invocation reaches fusion_signals INSERT."
    )

    print(
        "  4. INSERT parameter binding for direction is identified."
    )

    print(
        "  5. The resulting row identity matches a NULL-direction row."
    )

    print(
        "\nCURRENT STATUS:"
    )

    print(
        "STATIC CANDIDATES IDENTIFIED."
    )

    print(
        "RUNTIME RELATIONSHIP NOT YET PROVEN BY THIS READ-ONLY STAGE."
    )


# ==========================================================================================
# NULL ROW PATTERN ANALYSIS
# ==========================================================================================

def null_row_pattern_analysis(rows):

    print_subheader(
        "NULL DIRECTION TEMPORAL / IDENTITY PATTERN FORENSIC"
    )

    null_rows = [
        row
        for row in rows
        if row["direction"] is None
    ]

    if not null_rows:

        print(
            "No NULL direction rows present."
        )

        return

    by_engine = defaultdict(int)
    by_asset = defaultdict(int)
    by_snapshot = defaultdict(int)

    for row in null_rows:

        by_engine[
            safe_text(row["engine_version"])
        ] += 1

        by_asset[
            safe_text(row["asset"])
        ] += 1

        by_snapshot[
            safe_text(row["snapshot_id"])
        ] += 1

    print("By engine_version:")

    for key, count in sorted(by_engine.items()):
        print(
            f"  {key:<30} | {count}"
        )

    print("\nBy asset:")

    for key, count in sorted(by_asset.items()):
        print(
            f"  {key:<10} | {count}"
        )

    print("\nBy snapshot_id:")

    for key, count in sorted(by_snapshot.items()):
        print(
            f"  {key:<30} | {count}"
        )


# ==========================================================================================
# SOURCE HASH / IMMUTABILITY CHECK
# ==========================================================================================

def production_source_fingerprint():

    print_subheader(
        "PRODUCTION SOURCE FINGERPRINT"
    )

    important_files = [
        PROJECT_ROOT / "signal_outcome_engine.py",
        PROJECT_ROOT / "fusion_engine.py",
        PROJECT_ROOT / "signal_scorer.py",
        PROJECT_ROOT / "decision_engine.py",
    ]

    for path in important_files:

        if not path.exists():
            continue

        source = read_source(path)

        if source is None:
            continue

        print(
            f"{path.name:<35} | "
            f"SHA256={source_hash(source)}"
        )


# ==========================================================================================
# MAIN FORENSIC
# ==========================================================================================

def main():

    print_header(
        "OUTCOME v0.3 FUSION DIRECTION WRITER RUNTIME BOUNDARY FORENSIC v0.1",
        100,
    )

    print(
        f"Database          : {DB_NAME}"
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

    # ======================================================================================
    # DATABASE
    # ======================================================================================

    conn = None

    try:

        conn = connect_readonly(
            DB_PATH
        )

        verify_read_only_connection(
            conn
        )

        print_header(
            "DATABASE SAFETY CHECK",
            100,
        )

        print(
            "SQLite connection       : READ ONLY"
        )

        print(
            "PRAGMA query_only       : ON"
        )

        print(
            "Immutable database mode : ON"
        )

        # ------------------------------------------------------------------
        # Structure
        # ------------------------------------------------------------------

        print_header(
            "DATABASE STRUCTURE CHECK",
            100,
        )

        required_tables = [
            "fusion_signals",
            "signal_outcomes",
            "hunter_signals",
            "news_signals",
            "opportunity_signals",
        ]

        for table in required_tables:

            print(
                f"{table:<30} | "
                f"{'FOUND' if table_exists(conn, table) else 'NOT FOUND'}"
            )

        if not table_exists(
            conn,
            TARGET_TABLE,
        ):
            raise RuntimeError(
                "fusion_signals table does not exist."
            )

        columns = table_columns(
            conn,
            TARGET_TABLE,
        )

        print(
            "\nfusion_signals columns:"
        )

        for column in columns:
            print(
                f"  - {column}"
            )

        if TARGET_COLUMN not in columns:
            raise RuntimeError(
                "fusion_signals.direction column does not exist."
            )

        # ------------------------------------------------------------------
        # Population
        # ------------------------------------------------------------------

        rows = get_fusion_population(
            conn
        )

        print_header(
            "CURRENT FUSION DIRECTION POPULATION",
            100,
        )

        print_population_summary(
            rows
        )

        print_header(
            "NULL DIRECTION SIGNAL IDENTITIES",
            100,
        )

        print_null_rows(
            rows
        )

        # ------------------------------------------------------------------
        # Timeline
        # ------------------------------------------------------------------

        print_header(
            "FUSION SIGNAL TIMELINE",
            100,
        )

        print(
            f"Rows : {len(rows)}"
        )

        print_timeline(
            rows
        )

        # ------------------------------------------------------------------
        # Outcome engine
        # ------------------------------------------------------------------

        check_outcome_engine()

        # ------------------------------------------------------------------
        # Source discovery
        # ------------------------------------------------------------------

        print_header(
            "UPSTREAM SOURCE WRITER DISCOVERY",
            100,
        )

        python_files, writers, direction_builders = (
            collect_source_candidates(
                PROJECT_ROOT
            )
        )

        print(
            f"Python files scanned : {len(python_files)}"
        )

        print(
            f"Direct writer candidates : {len(writers)}"
        )

        print(
            f"Direction construction candidates : "
            f"{len(direction_builders)}"
        )

        # ------------------------------------------------------------------
        # Provenance
        # ------------------------------------------------------------------

        build_module_provenance(
            python_files,
            writers,
            direction_builders,
        )

        # ------------------------------------------------------------------
        # Candidate details
        # ------------------------------------------------------------------

        print_header(
            "DIRECT WRITER SOURCE CONTEXT",
            100,
        )

        for candidate in writers:

            inspect_writer_candidate(
                candidate
            )

        # ------------------------------------------------------------------
        # NULL patterns
        # ------------------------------------------------------------------

        null_row_pattern_analysis(
            rows
        )

        # ------------------------------------------------------------------
        # Runtime boundary
        # ------------------------------------------------------------------

        runtime_boundary_assessment(
            writers,
            rows,
        )

        # ------------------------------------------------------------------
        # Source fingerprints
        # ------------------------------------------------------------------

        production_source_fingerprint()

        # ==================================================================================
        # FINAL
        # ==================================================================================

        print_header(
            "FINAL SAFETY VERDICT",
            100,
        )

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
            "Production DB         : UNMODIFIED"
        )

        print(
            "Production source     : UNMODIFIED"
        )

        print(
            "Direction inferred    : NO"
        )

        print(
            "Direction repaired    : NO"
        )

        print(
            "Tolerance modified    : NO"
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

        print_header(
            "FORENSIC CONCLUSION",
            100,
        )

        null_count = sum(
            1
            for row in rows
            if row["direction"] is None
        )

        valid_count = sum(
            1
            for row in rows
            if row["direction"] in VALID_DIRECTIONS
        )

        print(
            f"Current fusion rows       : {len(rows)}"
        )

        print(
            f"Valid directional rows    : {valid_count}"
        )

        print(
            f"NULL directional rows     : {null_count}"
        )

        print(
            f"Direct writer candidates  : {len(writers)}"
        )

        print(
            "\nPROVENANCE STATUS:"
        )

        if writers:

            print(
                "DIRECT WRITER CANDIDATES IDENTIFIED."
            )

            print(
                "RUNTIME WRITER -> INSERT -> NULL ROW RELATIONSHIP "
                "REMAINS TO BE PROVEN."
            )

        else:

            print(
                "NO DIRECT WRITER CANDIDATE IDENTIFIED."
            )

            print(
                "RUNTIME PROVENANCE REMAINS UNPROVEN."
            )

        print(
            "\nNO ELIGIBILITY REPAIR IS AUTHORIZED."
        )

        print(
            "NO direction reconstruction is authorized."
        )

        print(
            "NO score-based direction inference is authorized."
        )

        print(
            "\nNEXT ACTION:"
        )

        print(
            "Perform exact runtime writer invocation tracing."
        )

        print(
            "The next stage must connect:"
        )

        print(
            "    writer invocation"
        )

        print(
            "        -> direction value"
        )

        print(
            "        -> INSERT parameter"
        )

        print(
            "        -> actual fusion_signals row"
        )

        print(
            "        -> NULL direction identity"
        )

        print(
            "\nFORENSIC COMPLETE."
        )

    except Exception as exc:

        print_header(
            "FORENSIC EXECUTION ERROR",
            100,
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print(
            "\nSAFETY:"
        )

        print(
            "No database write operation was intentionally executed."
        )

        traceback.print_exc()

        raise

    finally:

        if conn is not None:

            try:
                conn.close()
            except Exception:
                pass


# ==========================================================================================
# ENTRY POINT
# ==========================================================================================

if __name__ == "__main__":
    main()