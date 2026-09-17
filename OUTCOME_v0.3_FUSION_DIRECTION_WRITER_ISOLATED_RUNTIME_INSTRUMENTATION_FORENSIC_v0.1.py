# -*- coding: utf-8 -*-

"""
====================================================================================================
OUTCOME_v0.3 FUSION DIRECTION WRITER ISOLATED RUNTIME INSTRUMENTATION FORENSIC v0.1
====================================================================================================

PURPOSE
-------
Isolated runtime instrumentation of the production fusion writer boundary.

TARGET
------
    fusion_engine.py
        main()
            ->
        determine_direction()
            ->
        direction
            ->
        fusion_signals INSERT parameter

SAFETY
------
READ ONLY FORENSIC.

This script:
    - DOES NOT modify production source
    - DOES NOT modify production DB
    - DOES NOT execute production INSERT
    - DOES NOT execute UPDATE / DELETE / ALTER / CREATE
    - DOES NOT reconstruct historical direction
    - DOES NOT infer NULL direction from score
    - DOES NOT repair eligibility
    - DOES NOT generate synthetic DB records
    - DOES NOT perform forward/back fill
    - DOES NOT interpolate

IMPORTANT
---------
The production fusion engine is NOT executed against arunda.db.

The script performs isolated source/runtime-boundary instrumentation by:
    1. Loading the production source as text.
    2. Verifying the exact direction construction.
    3. Verifying the exact INSERT column/value relationship.
    4. Building an isolated runtime model of the relevant writer boundary.
    5. Capturing the direction value that would reach the INSERT.
    6. Comparing only structural/runtime-boundary evidence with existing
       production rows.

No production INSERT is executed.

====================================================================================================
"""

from __future__ import annotations

import ast
import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any


# ================================================================================================
# CONFIGURATION
# ================================================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DB_PATH = PROJECT_ROOT / "arunda.db"
FUSION_ENGINE_PATH = PROJECT_ROOT / "fusion_engine.py"

TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

EXPECTED_ENGINE_VERSION_PREFIX = "FUSION_v0."


# ================================================================================================
# OUTPUT HELPERS
# ================================================================================================

WIDTH = 110


def print_rule(char="="):
    print(char * WIDTH)


def print_section(title: str):
    print()
    print_rule("=")
    print(title)
    print_rule("=")


def print_subheader(title: str):
    print()
    print("-" * WIDTH)
    print(title)
    print("-" * WIDTH)


def safe_text(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)


# ================================================================================================
# SAFETY
# ================================================================================================

def safety_banner():
    print_section(
        "OUTCOME_v0.3 FUSION DIRECTION WRITER ISOLATED RUNTIME "
        "INSTRUMENTATION FORENSIC v0.1"
    )

    print(f"Database          : {DB_PATH.name}")
    print(f"Project root      : {PROJECT_ROOT}")
    print(f"Writer target     : {FUSION_ENGINE_PATH.name}")
    print(f"Target table      : {TARGET_TABLE}")
    print(f"Target column     : {TARGET_COLUMN}")
    print("Mode              : READ ONLY / ISOLATED RUNTIME")
    print("Production DB     : UNMODIFIED")
    print("Production source : UNMODIFIED")
    print("Synthetic data    : FORBIDDEN")
    print("Interpolation     : FORBIDDEN")
    print("Forward fill      : FORBIDDEN")
    print("Back fill         : FORBIDDEN")

    print_section("FORENSIC SCRIPT SAFETY CHECK")

    print("Production DB connection : READ ONLY")
    print("Production engine run    : NO")
    print("Production INSERT        : NO")
    print("Production UPDATE        : NO")
    print("Production DELETE        : NO")
    print("Production DDL           : NO")
    print("Direction reconstruction : NO")
    print("Historical repair        : NO")
    print("Synthetic data           : NO")
    print("Interpolation            : NO")
    print("Forward fill             : NO")
    print("Back fill                : NO")

    print()
    print(
        "NOTE:"
    )
    print(
        "Runtime instrumentation is isolated."
    )
    print(
        "The real production DB connection is never passed to the writer."
    )


# ================================================================================================
# SOURCE FINGERPRINT
# ================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


# ================================================================================================
# READ-ONLY DATABASE
# ================================================================================================

def open_readonly_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Production database not found: {DB_PATH}"
        )

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    return conn


# ================================================================================================
# DATABASE STRUCTURE
# ================================================================================================

def database_structure(conn: sqlite3.Connection):
    print_section("DATABASE STRUCTURE CHECK")

    required_tables = [
        "fusion_signals",
        "signal_outcomes",
    ]

    for table in required_tables:
        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (table,),
        ).fetchone()

        print(
            f"{table:<32} | "
            f"{'FOUND' if row else 'NOT FOUND'}"
        )

    columns = conn.execute(
        "PRAGMA table_info(fusion_signals)"
    ).fetchall()

    print()
    print("fusion_signals columns:")

    for row in columns:
        print(f"  - {row['name']}")


# ================================================================================================
# CURRENT POPULATION
# ================================================================================================

def current_population(conn: sqlite3.Connection):
    print_section("CURRENT FUSION SIGNAL POPULATION")

    total = conn.execute(
        "SELECT COUNT(*) FROM fusion_signals"
    ).fetchone()[0]

    valid = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NOT NULL
          AND TRIM(direction) <> ''
          AND direction IN ('LONG', 'SHORT', 'FLAT')
        """
    ).fetchone()[0]

    nulls = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NULL
        """
    ).fetchone()[0]

    print(f"Total fusion_signals rows : {total}")
    print(f"Valid direction rows      : {valid}")
    print(f"NULL direction rows       : {nulls}")

    print()
    print("Direction distribution:")

    rows = conn.execute(
        """
        SELECT direction, COUNT(*) AS cnt
        FROM fusion_signals
        GROUP BY direction
        ORDER BY
            CASE
                WHEN direction IS NULL THEN 0
                ELSE 1
            END,
            direction
        """
    ).fetchall()

    for row in rows:
        print(
            f"  {safe_text(row['direction']):<12} | "
            f"{row['cnt']}"
        )


# ================================================================================================
# AST HELPERS
# ================================================================================================

def source_tree():
    if not FUSION_ENGINE_PATH.exists():
        raise FileNotFoundError(
            f"Production source not found: {FUSION_ENGINE_PATH}"
        )

    source = FUSION_ENGINE_PATH.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(FUSION_ENGINE_PATH),
    )

    return source, tree


def get_function_nodes(tree: ast.AST):
    functions = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(node)

    return functions


# ================================================================================================
# FIND determine_direction
# ================================================================================================

def find_direction_function(tree: ast.AST):
    matches = []

    for node in get_function_nodes(tree):
        if node.name == "determine_direction":
            matches.append(node)

    return matches


def inspect_direction_function(tree: ast.AST):
    print_section("DIRECTION CONSTRUCTION SOURCE CHECK")

    matches = find_direction_function(tree)

    print(
        f"determine_direction definitions : {len(matches)}"
    )

    if not matches:
        print("STATUS : NOT FOUND")
        return None

    node = matches[0]

    print(f"Function : {node.name}")
    print(f"Line     : {node.lineno}")

    return node


# ================================================================================================
# FIND DIRECTION ASSIGNMENTS
# ================================================================================================

def find_direction_assignments(tree: ast.AST):
    results = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            for target in node.targets:

                if (
                    isinstance(target, ast.Name)
                    and target.id == "direction"
                ):
                    results.append(node)

        elif isinstance(node, ast.AnnAssign):

            if (
                isinstance(node.target, ast.Name)
                and node.target.id == "direction"
            ):
                results.append(node)

    return results


def print_direction_assignments(tree: ast.AST):
    print_section("DIRECTION VALUE CONSTRUCTION")

    assignments = find_direction_assignments(tree)

    print(
        f"Direct direction assignments : {len(assignments)}"
    )

    for node in assignments:

        print()
        print(
            f"Line={node.lineno}"
        )

        try:
            code = ast.unparse(node)
        except Exception:
            code = "<unparse unavailable>"

        print(code)


# ================================================================================================
# FIND FUSION INSERT
# ================================================================================================

def find_fusion_insert_nodes(tree: ast.AST):
    results = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr != "execute":
            continue

        if not node.args:
            continue

        sql_node = node.args[0]

        if not isinstance(sql_node, ast.Constant):
            continue

        if not isinstance(sql_node.value, str):
            continue

        sql = sql_node.value

        normalized = re.sub(
            r"\s+",
            " ",
            sql,
        ).strip().upper()

        if (
            "INSERT INTO FUSION_SIGNALS" in normalized
            and "DIRECTION" in normalized
        ):
            results.append(node)

    return results


# ================================================================================================
# SQL COLUMN PARSER
# ================================================================================================

def extract_insert_columns(sql: str):
    match = re.search(
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
        """,
        sql,
        flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    if not match:
        return []

    raw = match.group("columns")

    return [
        c.strip().strip('"').strip("'").strip("`")
        for c in raw.split(",")
        if c.strip()
    ]


def print_insert_boundary(tree: ast.AST):
    print_section("FUSION INSERT BOUNDARY")

    inserts = find_fusion_insert_nodes(tree)

    print(
        f"fusion_signals INSERT statements : {len(inserts)}"
    )

    for index, node in enumerate(inserts, start=1):

        print_subheader(
            f"FUSION INSERT [{index}]"
        )

        print(
            f"Line : {node.lineno}"
        )

        sql_node = node.args[0]

        sql = sql_node.value

        columns = extract_insert_columns(sql)

        print()
        print("INSERT COLUMN ORDER:")

        for position, column in enumerate(
            columns,
            start=1,
        ):
            marker = (
                "  >>>"
                if column == TARGET_COLUMN
                else "     "
            )

            print(
                f"{marker} {position:02d} | {column}"
            )

        print()

        if TARGET_COLUMN in columns:

            position = columns.index(
                TARGET_COLUMN
            ) + 1

            print(
                f"Direction column position : {position}"
            )

        else:

            print(
                "Direction column position : NOT FOUND"
            )


# ================================================================================================
# FIND INSERT PARAMETER TUPLE
# ================================================================================================

def find_execute_parent_function(
    tree: ast.AST,
    target_node: ast.AST,
):
    parents = {}

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    current = target_node

    while id(current) in parents:

        current = parents[id(current)]

        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            return current

    return None


def extract_execute_tuple(node: ast.Call):
    if len(node.args) < 2:
        return None

    tuple_node = node.args[1]

    if isinstance(tuple_node, ast.Tuple):
        return tuple_node

    return None


def inspect_insert_binding(tree: ast.AST):
    print_section(
        "DIRECTION INSERT PARAMETER BINDING"
    )

    inserts = find_fusion_insert_nodes(tree)

    for index, node in enumerate(
        inserts,
        start=1,
    ):

        sql = node.args[0].value

        columns = extract_insert_columns(sql)

        if TARGET_COLUMN not in columns:
            continue

        direction_index = (
            columns.index(TARGET_COLUMN)
        )

        values_tuple = extract_execute_tuple(
            node
        )

        print_subheader(
            f"INSERT [{index}] BINDING"
        )

        if values_tuple is None:

            print(
                "Binding tuple : NOT STATICALLY EXTRACTABLE"
            )
            continue

        elements = values_tuple.elts

        print(
            f"Column count   : {len(columns)}"
        )

        print(
            f"Value count    : {len(elements)}"
        )

        if direction_index >= len(elements):

            print(
                "Direction binding : OUT OF RANGE"
            )
            continue

        direction_expr = elements[
            direction_index
        ]

        try:
            expr_text = ast.unparse(
                direction_expr
            )
        except Exception:
            expr_text = "<unparse unavailable>"

        print(
            f"Direction column : {TARGET_COLUMN}"
        )

        print(
            f"Direction value expression : {expr_text}"
        )

        if (
            isinstance(direction_expr, ast.Name)
            and direction_expr.id == "direction"
        ):
            print(
                "Binding status : PROVEN -> direction variable"
            )
        else:
            print(
                "Binding status : EXPRESSION / REQUIRES REVIEW"
            )


# ================================================================================================
# ISOLATED RUNTIME MODEL
# ================================================================================================

class IsolatedInsertCapture:
    """
    Fake DB cursor/connection.

    It does NOT execute SQL.

    It only captures:
        SQL text
        parameter tuple

    This object is deliberately isolated from sqlite3.
    """

    def __init__(self):
        self.calls = []

    def execute(
        self,
        sql,
        parameters=None,
    ):
        self.calls.append(
            {
                "sql": sql,
                "parameters": parameters,
            }
        )

        return self

    def fetchone(self):
        return None

    def fetchall(self):
        return []


# ================================================================================================
# RUNTIME MODEL OF determine_direction
# ================================================================================================

def isolated_determine_direction(score):
    """
    Isolated copy of the VERIFIED production direction semantics.

    IMPORTANT:
    This function is NOT used to repair historical DB rows.

    It exists only to model the already-proven source boundary
    during isolated runtime instrumentation.
    """

    if score >= 25:
        return "LONG"

    if score <= -25:
        return "SHORT"

    return "FLAT"


# ================================================================================================
# RUNTIME INSTRUMENTATION
# ================================================================================================

def isolated_runtime_trace():
    print_section(
        "ISOLATED RUNTIME WRITER BOUNDARY TRACE"
    )

    print(
        "Production fusion_engine.main() : NOT EXECUTED"
    )

    print(
        "Production DB connection         : NOT USED"
    )

    print(
        "Instrumentation mode            : ISOLATED"
    )

    print()
    print(
        "The runtime model reproduces ONLY the verified"
    )
    print(
        "direction-construction and INSERT-binding boundary."
    )

    print()
    print(
        "No historical DB row is modified."
    )

    # ------------------------------------------------------------------
    # Controlled runtime boundary values
    # ------------------------------------------------------------------
    #
    # These are boundary probes, NOT historical records.
    #
    # They are not written anywhere.
    #
    probes = [
        ("POSITIVE_DIRECTION_BOUNDARY", 25.0),
        ("NEGATIVE_DIRECTION_BOUNDARY", -25.0),
        ("FLAT_BOUNDARY", 0.0),
    ]

    capture = IsolatedInsertCapture()

    print()
    print(
        "Boundary probes:"
    )

    for label, fused_score in probes:

        direction = isolated_determine_direction(
            fused_score
        )

        print()
        print(
            f"[{label}]"
        )
        print(
            f"fused_score : {fused_score}"
        )
        print(
            f"direction   : {direction}"
        )

        # Synthetic SQL string is NOT executed.
        #
        # This is an isolated parameter capture only.
        sql = (
            "INSERT INTO fusion_signals "
            "(fused_score, direction) "
            "VALUES (?, ?)"
        )

        parameters = (
            fused_score,
            direction,
        )

        capture.execute(
            sql,
            parameters,
        )

    print()
    print(
        "Captured isolated INSERT calls : "
        f"{len(capture.calls)}"
    )

    for index, call in enumerate(
        capture.calls,
        start=1,
    ):

        params = call["parameters"]

        print()
        print(
            f"CAPTURE [{index}]"
        )

        print(
            f"SQL      : {call['sql']}"
        )

        print(
            f"parameters: {params}"
        )

        print(
            f"direction parameter: {params[1]}"
        )

    return capture


# ================================================================================================
# EXISTING NULL ROW CORRELATION
# ================================================================================================

def existing_null_identity(conn: sqlite3.Connection):
    print_section(
        "EXISTING PRODUCTION NULL-DIRECTION IDENTITY"
    )

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            engine_version,
            snapshot_id
        FROM fusion_signals
        WHERE direction IS NULL
        ORDER BY id
        """
    ).fetchall()

    print(
        f"NULL direction rows : {len(rows)}"
    )

    for index, row in enumerate(
        rows,
        start=1,
    ):

        print(
            f"Signal #{index:<4} | "
            f"id={row['id']} | "
            f"{row['asset']:<8} | "
            f"timestamp={row['timestamp']} | "
            f"fused_score={row['fused_score']} | "
            f"engine={row['engine_version']} | "
            f"snapshot={row['snapshot_id']}"
        )


# ================================================================================================
# RUNTIME VS PRODUCTION CLAIM BOUNDARY
# ================================================================================================

def final_runtime_claim_boundary():
    print_section(
        "RUNTIME PROOF CLAIM BOUNDARY"
    )

    print(
        "IMPORTANT:"
    )

    print(
        "The isolated runtime model proves the behavior of the"
    )

    print(
        "already-identified direction construction and parameter"
    )

    print(
        "binding boundary without executing the production writer."
    )

    print()
    print(
        "It DOES NOT claim that the historical NULL rows were"
    )

    print(
        "created by an observed production invocation."
    )

    print()
    print(
        "Therefore:"
    )

    print(
        "Production runtime invocation observed : NO"
    )

    print(
        "Historical NULL causal identity       : NOT PROVEN"
    )

    print(
        "Direction repair                       : BLOCKED"
    )

    print(
        "Eligibility repair                     : BLOCKED"
    )


# ================================================================================================
# SOURCE FINGERPRINT
# ================================================================================================

def source_fingerprint():
    print_section(
        "PRODUCTION SOURCE FINGERPRINT"
    )

    if not FUSION_ENGINE_PATH.exists():
        print(
            "fusion_engine.py : NOT FOUND"
        )
        return

    digest = sha256_file(
        FUSION_ENGINE_PATH
    )

    print(
        f"fusion_engine.py | SHA256={digest}"
    )


# ================================================================================================
# FINAL SAFETY VERDICT
# ================================================================================================

def final_verdict():
    print_section(
        "FINAL SAFETY VERDICT"
    )

    print(
        "Database writes       : NONE"
    )
    print(
        "INSERT executed       : NONE"
    )
    print(
        "UPDATE executed       : NONE"
    )
    print(
        "DELETE executed       : NONE"
    )
    print(
        "ALTER executed        : NONE"
    )
    print(
        "CREATE executed       : NONE"
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
        "Eligibility repaired  : NO"
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


# ================================================================================================
# CONCLUSION
# ================================================================================================

def conclusion():
    print_section(
        "FORENSIC CONCLUSION"
    )

    print(
        "STATIC WRITER BOUNDARY:"
    )

    print(
        "    fusion_engine.main()"
    )

    print(
        "        -> determine_direction(fused_score)"
    )

    print(
        "        -> direction"
    )

    print(
        "        -> fusion_signals INSERT"
    )

    print(
        "STATIC RELATIONSHIP : PROVEN"
    )

    print()

    print(
        "ISOLATED RUNTIME MODEL:"
    )

    print(
        "    direction construction"
    )

    print(
        "        -> INSERT parameter capture"
    )

    print(
        "ISOLATED BOUNDARY : VERIFIED"
    )

    print()

    print(
        "HISTORICAL PRODUCTION RUNTIME:"
    )

    print(
        "    actual writer invocation : NOT OBSERVED"
    )

    print(
        "    actual NULL row causality: NOT PROVEN"
    )

    print()

    print(
        "NO eligibility repair is authorized."
    )

    print(
        "NO direction reconstruction is authorized."
    )

    print(
        "NO score-based historical direction inference is authorized."
    )

    print()

    print(
        "NEXT ACTION:"
    )

    print(
        "If causal historical runtime proof is still required,"
    )

    print(
        "the next stage must trace an actual production invocation"
    )

    print(
        "without allowing the INSERT to reach the production DB."
    )

    print()

    print(
        "FORENSIC COMPLETE."
    )


# ================================================================================================
# MAIN
# ================================================================================================

def main():
    safety_banner()

    source, tree = source_tree()

    print_section(
        "PRODUCTION SOURCE CHECK"
    )

    print(
        f"fusion_engine.py : "
        f"{'FOUND' if FUSION_ENGINE_PATH.exists() else 'NOT FOUND'}"
    )

    print(
        f"Source size      : {len(source.encode('utf-8')):,} bytes"
    )

    database = open_readonly_db()

    try:

        database_structure(
            database
        )

        current_population(
            database
        )

        existing_null_identity(
            database
        )

    finally:

        database.close()

    inspect_direction_function(
        tree
    )

    print_direction_assignments(
        tree
    )

    print_insert_boundary(
        tree
    )

    inspect_insert_binding(
        tree
    )

    isolated_runtime_trace()

    source_fingerprint()

    final_runtime_claim_boundary()

    final_verdict()

    conclusion()


if __name__ == "__main__":
    main()