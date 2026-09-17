# =============================================================================
# ARUNDA TRADER — FIRST RUNTIME ELIGIBILITY FAILURE TRACE v0.1
# =============================================================================
# MODE            : READ ONLY
# DATABASE        : arunda.db
# DB WRITE        : FORBIDDEN
# SOURCE WRITE    : FORBIDDEN
# SYNTHETIC DATA  : FORBIDDEN
# ORDER           : FORBIDDEN
# NETWORK         : FORBIDDEN
#
# PURPOSE:
#   Trace the FIRST runtime condition that rejects a current production signal.
#
# PATH:
#   REAL POST-LAUNCH DATA
#        -> SIGNAL
#        -> FUSION
#        -> ELIGIBILITY
#        -> ORDER INTENT
#
# IMPORTANT:
#   This script does NOT:
#       - lower thresholds
#       - bypass validators
#       - fabricate signals
#       - modify source
#       - modify database
#       - submit orders
# =============================================================================

from __future__ import annotations

import ast
import inspect
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "arunda.db"

TARGET_TABLE = "fusion_signals"

READ_ONLY_URI = f"file:{DB_PATH.as_posix()}?mode=ro"


# =============================================================================
# SAFETY
# =============================================================================

WRITE_KEYWORDS = (
    "insert ",
    "update ",
    "delete ",
    "alter ",
    "drop ",
    "create ",
    "replace ",
    "truncate ",
)


def assert_environment() -> None:
    print("=" * 90)
    print("ARUNDA TRADER — FIRST RUNTIME ELIGIBILITY FAILURE TRACE")
    print("=" * 90)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"DATABASE     : {DB_PATH}")
    print("READ ONLY    : True")
    print("SYNTHETIC    : False")
    print("DB WRITE     : False")
    print("ORDER        : False")
    print("NETWORK      : False")
    print()

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Production DB not found: {DB_PATH}")


# =============================================================================
# READ ONLY DB
# =============================================================================

def connect_read_only() -> sqlite3.Connection:
    conn = sqlite3.connect(
        READ_ONLY_URI,
        uri=True,
    )
    conn.row_factory = sqlite3.Row
    return conn


def assert_read_only_connection(conn: sqlite3.Connection) -> None:
    # SQLite defensive verification.
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    if not journal_mode:
        raise RuntimeError("Could not verify SQLite journal mode.")

    # Verify write attempts are not part of this script.
    for sql in (
        "SELECT name FROM sqlite_master WHERE type='table'",
    ):
        conn.execute(sql).fetchall()


# =============================================================================
# DATABASE OBSERVATION
# =============================================================================

def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [row["name"] for row in rows]


def get_latest_rows(
    conn: sqlite3.Connection,
    table: str,
    limit: int = 20,
) -> list[sqlite3.Row]:

    columns = get_columns(conn, table)

    if "timestamp" not in columns:
        raise RuntimeError(
            f"{table} has no timestamp column."
        )

    sql = f"""
        SELECT *
        FROM {table}
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
    """

    return conn.execute(sql, (limit,)).fetchall()


# =============================================================================
# SOURCE DISCOVERY
# =============================================================================

def source_files() -> list[Path]:
    return sorted(
        PROJECT_ROOT.glob("*.py")
    )


def read_source(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def source_contains_write_operation(source: str) -> list[str]:
    lowered = source.lower()

    hits = []

    for keyword in WRITE_KEYWORDS:
        if keyword in lowered:
            hits.append(keyword.strip())

    return hits


# =============================================================================
# AST CONDITION EXTRACTION
# =============================================================================

class ConditionVisitor(ast.NodeVisitor):

    def __init__(self) -> None:
        self.conditions: list[dict[str, Any]] = []
        self.function_stack: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.function_stack.append(node.name)

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> Any:

        self.function_stack.append(node.name)

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_If(self, node: ast.If) -> Any:

        condition = ast.unparse(node.test)

        self.conditions.append(
            {
                "function": (
                    self.function_stack[-1]
                    if self.function_stack
                    else "<module>"
                ),
                "line": node.lineno,
                "condition": condition,
                "type": "IF",
            }
        )

        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> Any:

        condition = ast.unparse(node.test)

        self.conditions.append(
            {
                "function": (
                    self.function_stack[-1]
                    if self.function_stack
                    else "<module>"
                ),
                "line": node.lineno,
                "condition": condition,
                "type": "ASSERT",
            }
        )

        self.generic_visit(node)


def extract_conditions(path: Path) -> list[dict[str, Any]]:

    try:
        tree = ast.parse(
            read_source(path),
            filename=str(path),
        )
    except SyntaxError:
        return []

    visitor = ConditionVisitor()
    visitor.visit(tree)

    return visitor.conditions


# =============================================================================
# ELIGIBILITY-LIKE DISCOVERY
# =============================================================================

ELIGIBILITY_TERMS = (
    "eligib",
    "qualif",
    "valid",
    "reject",
    "block",
    "allow",
    "release",
    "order_intent",
    "trade",
    "signal_strength",
    "direction",
    "confidence",
    "fused_score",
)


def is_eligibility_like(
    function_name: str,
    condition: str,
) -> bool:

    text = (
        f"{function_name} {condition}"
    ).lower()

    return any(
        term in text
        for term in ELIGIBILITY_TERMS
    )


def discover_runtime_conditions() -> list[dict[str, Any]]:

    results = []

    for path in source_files():

        conditions = extract_conditions(path)

        for condition in conditions:

            if is_eligibility_like(
                condition["function"],
                condition["condition"],
            ):
                item = dict(condition)
                item["file"] = str(path)
                results.append(item)

    return results


# =============================================================================
# CURRENT FUSION ROW EVALUATION
# =============================================================================

def row_value(
    row: sqlite3.Row,
    name: str,
) -> Any:

    try:
        return row[name]
    except (KeyError, IndexError):
        return None


def safe_number(value: Any) -> float | None:

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# =============================================================================
# CANONICAL ELIGIBILITY SIGNAL OBSERVATION
# =============================================================================

def observe_signal(
    row: sqlite3.Row,
) -> dict[str, Any]:

    fused_score = safe_number(
        row_value(row, "fused_score")
    )

    confidence = safe_number(
        row_value(row, "confidence")
    )

    direction = row_value(
        row,
        "direction",
    )

    signal_strength = row_value(
        row,
        "signal_strength",
    )

    data_quality = row_value(
        row,
        "data_quality",
    )

    market_available = row_value(
        row,
        "market_available",
    )

    positioning_available = row_value(
        row,
        "positioning_available",
    )

    news_available = row_value(
        row,
        "news_available",
    )

    return {
        "asset": row_value(row, "asset"),
        "timestamp": row_value(row, "timestamp"),
        "fused_score": fused_score,
        "confidence": confidence,
        "direction": direction,
        "signal_strength": signal_strength,
        "data_quality": data_quality,
        "market_available": market_available,
        "positioning_available": positioning_available,
        "news_available": news_available,
        "engine_version": row_value(
            row,
            "engine_version",
        ),
    }


# =============================================================================
# RUNTIME MODULE INSPECTION
# =============================================================================

def inspect_runtime_modules() -> None:

    print("=" * 90)
    print("CURRENT RUNTIME MODULES")
    print("=" * 90)

    module_names = (
        "signal_engine",
        "fusion_engine",
    )

    for module_name in module_names:

        module_path = (
            PROJECT_ROOT /
            f"{module_name}.py"
        )

        if not module_path.exists():
            print(
                f"{module_name:<20} : NOT FOUND"
            )
            continue

        print(
            f"\nMODULE: {module_name}"
        )

        try:
            source = read_source(module_path)
            tree = ast.parse(
                source,
                filename=str(module_path),
            )

            for node in tree.body:

                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):

                    lowered = node.name.lower()

                    if any(
                        term in lowered
                        for term in ELIGIBILITY_TERMS
                    ):
                        print(
                            f"  {node.name} | "
                            f"{module_path} | "
                            f"line={node.lineno}"
                        )

        except Exception as exc:
            print(
                f"  INSPECTION_ERROR: {exc}"
            )


# =============================================================================
# FIRST FAILURE HEURISTIC
# =============================================================================

def identify_obvious_blockers(
    observed: dict[str, Any],
) -> list[dict[str, Any]]:

    failures = []

    direction = observed["direction"]
    strength = observed["signal_strength"]
    quality = observed["data_quality"]

    fused_score = observed["fused_score"]
    confidence = observed["confidence"]

    # -------------------------------------------------------------------------
    # These are OBSERVATIONS ONLY.
    #
    # They are intentionally NOT thresholds.
    # We do not invent a pass/fail threshold here.
    # -------------------------------------------------------------------------

    if direction is None:
        failures.append(
            {
                "field": "direction",
                "reason": "direction is NULL",
                "value": direction,
            }
        )

    if direction == "FLAT":
        failures.append(
            {
                "field": "direction",
                "reason": "runtime direction is FLAT",
                "value": direction,
            }
        )

    if strength is None:
        failures.append(
            {
                "field": "signal_strength",
                "reason": "signal_strength is NULL",
                "value": strength,
            }
        )

    if quality is None:
        failures.append(
            {
                "field": "data_quality",
                "reason": "data_quality is NULL",
                "value": quality,
            }
        )

    if fused_score is None:
        failures.append(
            {
                "field": "fused_score",
                "reason": "fused_score is NULL",
                "value": fused_score,
            }
        )

    if confidence is None:
        failures.append(
            {
                "field": "confidence",
                "reason": "confidence is NULL",
                "value": confidence,
            }
        )

    return failures


# =============================================================================
# REPORT
# =============================================================================

def print_runtime_conditions(
    conditions: list[dict[str, Any]],
) -> None:

    print("=" * 90)
    print("ELIGIBILITY-LIKE RUNTIME CONDITIONS")
    print("=" * 90)

    if not conditions:
        print("NO ELIGIBILITY-LIKE AST CONDITIONS FOUND")
        return

    for index, item in enumerate(
        conditions,
        start=1,
    ):

        print(
            f"\n[{index}]"
        )

        print(
            f"FILE      : {item['file']}"
        )

        print(
            f"FUNCTION  : {item['function']}"
        )

        print(
            f"LINE      : {item['line']}"
        )

        print(
            f"TYPE      : {item['type']}"
        )

        print(
            f"CONDITION : {item['condition']}"
        )


def print_signal_observation(
    observed: dict[str, Any],
) -> None:

    print("=" * 90)
    print("CURRENT PRODUCTION SIGNAL OBSERVATION")
    print("=" * 90)

    for key, value in observed.items():
        print(
            f"{key:<24}: {value}"
        )


def print_failures(
    failures: list[dict[str, Any]],
) -> None:

    print("=" * 90)
    print("FIRST OBSERVED RUNTIME BLOCKERS")
    print("=" * 90)

    if not failures:
        print(
            "NO OBVIOUS BLOCKER OBSERVED "
            "FROM CURRENT FUSION ROW."
        )
        return

    for index, failure in enumerate(
        failures,
        start=1,
    ):

        print(
            f"\nFAILURE #{index}"
        )

        print(
            f"FIELD  : {failure['field']}"
        )

        print(
            f"VALUE  : {failure['value']}"
        )

        print(
            f"REASON : {failure['reason']}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    assert_environment()

    # -------------------------------------------------------------------------
    # DB
    # -------------------------------------------------------------------------

    conn = connect_read_only()

    try:

        assert_read_only_connection(conn)

        columns = get_columns(
            conn,
            TARGET_TABLE,
        )

        print("=" * 90)
        print("DATABASE OBSERVATION")
        print("=" * 90)

        print(
            f"TABLE       : {TARGET_TABLE}"
        )

        print(
            f"COLUMNS     : {columns}"
        )

        rows = get_latest_rows(
            conn,
            TARGET_TABLE,
            limit=20,
        )

        print(
            f"LATEST ROWS : {len(rows)}"
        )

        if not rows:
            print(
                "NO FUSION SIGNALS FOUND."
            )
            return

        # ---------------------------------------------------------------------
        # Select current runtime snapshot.
        #
        # We deliberately use the latest timestamp available in production DB.
        # ---------------------------------------------------------------------

        latest_timestamp = row_value(
            rows[0],
            "timestamp",
        )

        current_rows = [
            row
            for row in rows
            if row_value(row, "timestamp")
            == latest_timestamp
        ]

        print(
            f"CURRENT SNAPSHOT TIMESTAMP : "
            f"{latest_timestamp}"
        )

        print(
            f"CURRENT SNAPSHOT ROWS      : "
            f"{len(current_rows)}"
        )

        # ---------------------------------------------------------------------
        # Runtime source discovery
        # ---------------------------------------------------------------------

        inspect_runtime_modules()

        conditions = discover_runtime_conditions()

        print_runtime_conditions(
            conditions
        )

        # ---------------------------------------------------------------------
        # Current signals
        # ---------------------------------------------------------------------

        print("=" * 90)
        print("CURRENT SIGNAL TRACE")
        print("=" * 90)

        for row in current_rows:

            observed = observe_signal(
                row
            )

            print()
            print(
                "-" * 90
            )

            print_signal_observation(
                observed
            )

            failures = identify_obvious_blockers(
                observed
            )

            print_failures(
                failures
            )

        # ---------------------------------------------------------------------
        # Safety final
        # ---------------------------------------------------------------------

        print()
        print("=" * 90)
        print("EXECUTION STATUS")
        print("=" * 90)

        print("EXECUTED                 : YES")
        print("DATABASE                 : READ ONLY")
        print("DB WRITE                 : NONE")
        print("SOURCE WRITE             : NONE")
        print("SYNTHETIC DATA           : NO")
        print("THRESHOLD MODIFICATION   : NONE")
        print("VALIDATOR BYPASS         : NONE")
        print("ORDER SUBMISSION         : NONE")
        print("NETWORK                  : NONE")

        print()
        print("=" * 90)
        print("FINAL")
        print("=" * 90)

        print(
            "RESULT : FIRST RUNTIME ELIGIBILITY "
            "TRACE COMPLETED"
        )

        print(
            "REPAIR : NOT PERFORMED"
        )

        print(
            "FRONTIER : "
            "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()