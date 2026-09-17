# ARUNDA_TECHNICAL_VALIDATOR_PRODUCTION_BOUNDARY_FORENSIC_v0.1.py
# ============================================================================
# ARUNDA TRADER
# TECHNICAL VALIDATOR PRODUCTION BOUNDARY FORENSIC v0.1
#
# PURPOSE:
#   Locate the real production Technical Validator boundary and determine:
#     1. Production validator source files
#     2. Validator entry functions
#     3. market_technical readers
#     4. SQL/query paths
#     5. Call-chain evidence
#     6. Current row-selection behavior
#     7. Whether Contract Scope is already enforced
#     8. The minimal safe integration point
#
# MODE:
#   READ ONLY FORENSIC
#
# HARD CONSTRAINTS:
#   - NO production module execution
#   - NO database writes
#   - NO schema changes
#   - NO network
#   - NO deletion/update/insert
#   - NO contract modification
#   - NO validator modification
#
# DATABASE:
#   C:\Users\ASUS\ArundaTrader\arunda.db
# ============================================================================

from __future__ import annotations

import ast
import os
import re
import sqlite3
from pathlib import Path
from collections import defaultdict


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

OUTPUT_NAME = "ARUNDA_TECHNICAL_VALIDATOR_PRODUCTION_BOUNDARY_FORENSIC_v0.1.py"

SELF_PATH = Path(__file__).resolve()

# Files / directories that are clearly forensic or generated reports.
EXCLUDED_NAME_PATTERNS = (
    "FORENSIC",
    "forensic",
    "AUDIT",
    "audit",
    "RECONCILIATION",
    "reconciliation",
    "CHECK",
    "check",
    "TEST",
    "test",
    "DEBUG",
    "debug",
    "REPORT",
    "report",
)

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

# Strong production-oriented names.
VALIDATOR_NAME_PATTERNS = (
    "validator",
    "validation",
)

# Technical-oriented names.
TECHNICAL_NAME_PATTERNS = (
    "technical",
)


# ============================================================================
# SAFE FILE DISCOVERY
# ============================================================================

def is_excluded_path(path: Path) -> bool:
    """
    Exclude known forensic/test/report artifacts from production-boundary
    discovery.
    """
    if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
        return True

    name = path.name

    if name == SELF_PATH.name:
        return True

    for pattern in EXCLUDED_NAME_PATTERNS:
        if pattern in name:
            return True

    return False


def discover_python_files() -> list[Path]:
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if is_excluded_path(path):
            continue

        files.append(path)

    return sorted(files)


# ============================================================================
# AST HELPERS
# ============================================================================

def get_source_segment(source: str, node: ast.AST) -> str:
    try:
        segment = ast.get_source_segment(source, node)
        return segment or ""
    except Exception:
        return ""


def node_line(node: ast.AST) -> int:
    return getattr(node, "lineno", -1)


def function_name(node: ast.AST) -> str:
    return getattr(node, "name", "")


def contains_text(node: ast.AST, source: str, patterns: tuple[str, ...]) -> bool:
    segment = get_source_segment(source, node).lower()

    return any(pattern.lower() in segment for pattern in patterns)


def is_function(node: ast.AST) -> bool:
    return isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )


# ============================================================================
# SQL / DB EVIDENCE EXTRACTION
# ============================================================================

def extract_sql_evidence(source: str, node: ast.AST) -> list[str]:
    """
    Extract SQL-looking string literals from a function without executing
    anything.
    """
    evidence = []

    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            value = child.value.strip()

            if not value:
                continue

            upper = value.upper()

            sql_markers = (
                "SELECT ",
                "SELECT\n",
                "FROM ",
                "WHERE ",
                "JOIN ",
                "INSERT ",
                "UPDATE ",
                "DELETE ",
                "PRAGMA ",
            )

            if any(marker in upper for marker in sql_markers):
                evidence.append(value)

    return evidence


def find_market_technical_queries(source: str, node: ast.AST) -> list[str]:
    evidence = []

    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            value = child.value

            if "market_technical" in value.lower():
                evidence.append(value.strip())

    return evidence


# ============================================================================
# DB CALL EXTRACTION
# ============================================================================

def extract_db_calls(source: str, node: ast.AST) -> list[dict]:
    calls = []

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        func = child.func

        call_name = ""

        if isinstance(func, ast.Attribute):
            call_name = func.attr

        elif isinstance(func, ast.Name):
            call_name = func.id

        if call_name not in {
            "execute",
            "executemany",
            "executescript",
            "fetchone",
            "fetchall",
            "fetchmany",
        }:
            continue

        segment = get_source_segment(source, child)

        if "market_technical" not in segment.lower():
            continue

        calls.append(
            {
                "line": node_line(child),
                "call": call_name,
                "source": segment.strip(),
            }
        )

    return calls


# ============================================================================
# VALIDATOR CANDIDATE ANALYSIS
# ============================================================================

def analyze_file(path: Path) -> dict:
    result = {
        "path": str(path),
        "relative": str(path.relative_to(PROJECT_ROOT)),
        "size": 0,
        "functions": [],
        "validator_score": 0,
        "technical_score": 0,
        "market_technical_hits": [],
        "sql_hits": [],
        "db_calls": [],
        "imports": [],
        "parse_error": None,
    }

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        result["parse_error"] = f"READ_ERROR: {exc}"
        return result

    result["size"] = len(source)

    validator_score = 0
    technical_score = 0

    lower_source = source.lower()

    for pattern in VALIDATOR_NAME_PATTERNS:
        if pattern in path.name.lower():
            validator_score += 5

    for pattern in TECHNICAL_NAME_PATTERNS:
        if pattern in path.name.lower():
            technical_score += 5

    if "market_technical" in lower_source:
        technical_score += 10

    if "validate" in lower_source:
        validator_score += 3

    try:
        tree = ast.parse(source, filename=str(path))
    except Exception as exc:
        result["parse_error"] = f"AST_PARSE_ERROR: {exc}"
        return result

    for node in ast.walk(tree):

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            segment = get_source_segment(source, node)
            result["imports"].append(segment.strip())

        if not is_function(node):
            continue

        name = function_name(node)

        fn_market_queries = find_market_technical_queries(source, node)
        fn_db_calls = extract_db_calls(source, node)
        fn_sql = extract_sql_evidence(source, node)

        name_lower = name.lower()

        score = 0

        if "valid" in name_lower:
            score += 10

        if "technical" in name_lower:
            score += 8

        if "market" in name_lower:
            score += 4

        if fn_market_queries:
            score += 20

        if fn_db_calls:
            score += 20

        if contains_text(
            node,
            source,
            (
                "technical_validation",
                "technical_validation_status",
                "technical_validation_score",
                "technical_validation_flags",
                "technical_validation_version",
            ),
        ):
            score += 15

        if score > 0:
            validator_score += score

        if fn_market_queries:
            technical_score += 15

            for query in fn_market_queries:
                result["market_technical_hits"].append(
                    {
                        "function": name,
                        "line": node_line(node),
                        "sql": query,
                    }
                )

        if fn_db_calls:
            for call in fn_db_calls:
                result["db_calls"].append(
                    {
                        "function": name,
                        **call,
                    }
                )

        if fn_sql:
            for sql in fn_sql:
                result["sql_hits"].append(
                    {
                        "function": name,
                        "line": node_line(node),
                        "sql": sql,
                    }
                )

        result["functions"].append(
            {
                "name": name,
                "line": node_line(node),
                "validator_score": score,
                "market_technical_reads": len(fn_market_queries),
                "db_calls": len(fn_db_calls),
            }
        )

    result["validator_score"] = validator_score
    result["technical_score"] = technical_score

    return result


# ============================================================================
# STATIC CALL-REFERENCE DISCOVERY
# ============================================================================

def find_function_references(files: list[Path], target_names: set[str]) -> dict:
    references = defaultdict(list)

    if not target_names:
        return references

    for path in files:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except Exception:
            continue

        for node in ast.walk(tree):

            if isinstance(node, ast.Call):
                func = node.func

                if isinstance(func, ast.Name):
                    called = func.id

                elif isinstance(func, ast.Attribute):
                    called = func.attr

                else:
                    continue

                if called in target_names:
                    references[called].append(
                        {
                            "file": str(path.relative_to(PROJECT_ROOT)),
                            "line": node_line(node),
                            "call": called,
                        }
                    )

    return references


# ============================================================================
# DATABASE READ-ONLY INSPECTION
# ============================================================================

def inspect_database() -> dict:
    result = {
        "connected": False,
        "tables": [],
        "market_technical_exists": False,
        "total_rows": None,
        "in_scope_rows": None,
        "out_scope_rows": None,
        "errors": [],
    }

    if not DB_PATH.exists():
        result["errors"].append(f"DATABASE_NOT_FOUND: {DB_PATH}")
        return result

    conn = None

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

        result["connected"] = True

        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        result["tables"] = [row[0] for row in rows]

        if "market_technical" not in result["tables"]:
            return result

        result["market_technical_exists"] = True

        result["total_rows"] = conn.execute(
            "SELECT COUNT(*) FROM market_technical"
        ).fetchone()[0]

        result["in_scope_rows"] = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_technical
            WHERE
                history_points = 200
                AND source = 'REAL_MARKET_HISTORY'
                AND technical_version = 'TECHNICAL_v0.5'
                AND engine_version = 'TECHNICAL_v0.5'
            """
        ).fetchone()[0]

        result["out_scope_rows"] = (
            result["total_rows"] - result["in_scope_rows"]
        )

    except Exception as exc:
        result["errors"].append(f"DB_READ_ERROR: {exc}")

    finally:
        if conn is not None:
            conn.close()

    return result


# ============================================================================
# PRINT HELPERS
# ============================================================================

def line():
    print("=" * 100)


def section(title: str):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def print_file_candidate(item: dict):
    print()
    print(f"FILE : {item['relative']}")
    print(f"VALIDATOR SCORE : {item['validator_score']}")
    print(f"TECHNICAL SCORE : {item['technical_score']}")

    if item["parse_error"]:
        print(f"PARSE STATUS : {item['parse_error']}")
        return

    if item["functions"]:
        print("FUNCTIONS:")

        for fn in sorted(
            item["functions"],
            key=lambda x: (-x["validator_score"], x["line"]),
        ):
            print(
                f"  {fn['name']:<45} "
                f"LINE={fn['line']:<5} "
                f"SCORE={fn['validator_score']:<3} "
                f"MARKET_TECHNICAL_READS={fn['market_technical_reads']:<2} "
                f"DB_CALLS={fn['db_calls']}"
            )

    if item["market_technical_hits"]:
        print()
        print("MARKET_TECHNICAL QUERIES:")

        for hit in item["market_technical_hits"]:
            print(
                f"  FUNCTION={hit['function']} "
                f"LINE={hit['line']}"
            )

            sql = re.sub(r"\s+", " ", hit["sql"])

            if len(sql) > 500:
                sql = sql[:500] + "..."

            print(f"    SQL={sql}")


# ============================================================================
# MAIN FORENSIC
# ============================================================================

def main():
    line()

    print("ARUNDA TECHNICAL VALIDATOR PRODUCTION BOUNDARY FORENSIC v0.1")
    print("=" * 100)

    print("MODE                 : READ ONLY")
    print(f"PROJECT ROOT         : {PROJECT_ROOT}")
    print(f"DATABASE             : {DB_PATH}")
    print("WRITE OPERATIONS     : NONE")
    print("PRODUCTION EXECUTION : NONE")
    print("NETWORK              : NONE")

    # ------------------------------------------------------------------------
    # DB
    # ------------------------------------------------------------------------

    section("DATABASE READ-ONLY CHECK")

    db = inspect_database()

    print(f"CONNECTED            : {db['connected']}")
    print(f"MARKET_TECHNICAL     : {db['market_technical_exists']}")

    if db["market_technical_exists"]:
        print(f"TOTAL ROWS           : {db['total_rows']}")
        print(f"CONTRACT IN-SCOPE    : {db['in_scope_rows']}")
        print(f"CONTRACT OUT-SCOPE   : {db['out_scope_rows']}")

    if db["errors"]:
        for error in db["errors"]:
            print(f"[ERROR] {error}")

    # ------------------------------------------------------------------------
    # FILE DISCOVERY
    # ------------------------------------------------------------------------

    section("STATIC PRODUCTION SOURCE DISCOVERY")

    files = discover_python_files()

    print(f"PYTHON FILES SCANNED  : {len(files)}")

    results = []

    for path in files:
        result = analyze_file(path)

        if (
            result["validator_score"] > 0
            or result["technical_score"] > 0
            or result["market_technical_hits"]
        ):
            results.append(result)

    results.sort(
        key=lambda x: (
            -x["validator_score"],
            -x["technical_score"],
            x["relative"],
        )
    )

    print(f"CANDIDATE FILES       : {len(results)}")

    for item in results:
        print_file_candidate(item)

    # ------------------------------------------------------------------------
    # TARGET FUNCTIONS
    # ------------------------------------------------------------------------

    section("POTENTIAL VALIDATOR ENTRY FUNCTIONS")

    target_names = set()

    for item in results:
        for fn in item["functions"]:
            if fn["validator_score"] >= 10:
                target_names.add(fn["name"])

    if not target_names:
        print("NO HIGH-CONFIDENCE VALIDATOR FUNCTION FOUND")
    else:
        for name in sorted(target_names):
            print(f"[CANDIDATE] {name}")

    # ------------------------------------------------------------------------
    # STATIC CALL REFERENCES
    # ------------------------------------------------------------------------

    section("STATIC CALL-REFERENCE FORENSIC")

    references = find_function_references(files, target_names)

    if not references:
        print("NO STATIC CALL REFERENCES FOUND")
    else:
        for name in sorted(references):
            print()
            print(f"TARGET FUNCTION : {name}")

            refs = references[name]

            for ref in refs:
                print(
                    f"  CALLER FILE={ref['file']} "
                    f"LINE={ref['line']} "
                    f"CALL={ref['call']}"
                )

    # ------------------------------------------------------------------------
    # BOUNDARY CLASSIFICATION
    # ------------------------------------------------------------------------

    section("BOUNDARY CLASSIFICATION")

    market_readers = []

    for item in results:
        for hit in item["market_technical_hits"]:
            market_readers.append(
                {
                    "file": item["relative"],
                    **hit,
                }
            )

    print(f"MARKET_TECHNICAL READ LOCATIONS : {len(market_readers)}")

    if not market_readers:
        print("[WARN] NO MARKET_TECHNICAL READ LOCATION FOUND")
    else:
        for reader in market_readers:
            print(
                f"  FILE={reader['file']} "
                f"FUNCTION={reader['function']} "
                f"LINE={reader['line']}"
            )

    # ------------------------------------------------------------------------
    # SCOPE LEAKAGE STATIC TEST
    # ------------------------------------------------------------------------

    section("STATIC CONTRACT-SCOPE LEAKAGE TEST")

    scope_markers = (
        "history_points",
        "REAL_MARKET_HISTORY",
        "TECHNICAL_v0.5",
        "engine_version",
        "technical_version",
    )

    scope_evidence = []

    for reader in market_readers:
        item = next(
            (
                x
                for x in results
                if x["relative"] == reader["file"]
            ),
            None,
        )

        if not item:
            continue

        for hit in item["market_technical_hits"]:
            sql_lower = hit["sql"].lower()

            found = [
                marker
                for marker in scope_markers
                if marker.lower() in sql_lower
            ]

            scope_evidence.append(
                {
                    "file": reader["file"],
                    "function": reader["function"],
                    "line": reader["line"],
                    "scope_markers": found,
                }
            )

    if not scope_evidence:
        print("NO SCOPE EVIDENCE AVAILABLE")
    else:
        for evidence in scope_evidence:
            markers = evidence["scope_markers"]

            if markers:
                status = "SCOPE_MARKERS_PRESENT"
            else:
                status = "NO_SCOPE_MARKERS"

            print(
                f"{status:<22} "
                f"{evidence['file']} :: "
                f"{evidence['function']} "
                f"LINE={evidence['line']}"
            )

            if markers:
                print(
                    f"  MARKERS : {', '.join(markers)}"
                )

    # ------------------------------------------------------------------------
    # MINIMAL INTEGRATION POINT
    # ------------------------------------------------------------------------

    section("MINIMAL CONTRACT INTEGRATION POINT")

    if market_readers:
        print(
            "CURRENT DATA BOUNDARY CANDIDATES:"
        )

        for reader in market_readers:
            print(
                f"  {reader['file']} :: "
                f"{reader['function']} "
                f"LINE={reader['line']}"
            )

        print()
        print(
            "RECOMMENDATION:"
        )
        print(
            "  Inject TECHNICAL CONTRACT SCOPE immediately "
            "before the first production Validator input."
        )
        print(
            "  Do NOT modify historical rows."
        )
        print(
            "  Do NOT classify OUT-OF-SCOPE rows as INVALID."
        )
        print(
            "  Do NOT duplicate Validator logic."
        )
    else:
        print(
            "[BLOCKED] Production Validator boundary "
            "could not be statically established."
        )

    # ------------------------------------------------------------------------
    # FINAL STATUS
    # ------------------------------------------------------------------------

    section("FINAL FORENSIC STATUS")

    if (
        db["connected"]
        and db["market_technical_exists"]
        and market_readers
    ):
        print("DATABASE ACCESS        : PASS")
        print("SOURCE DISCOVERY       : PASS")
        print("MARKET_TECHNICAL PATH  : PASS")
        print("PRODUCTION EXECUTION   : NONE")
        print("DATABASE WRITES        : NONE")
        print()
        print("STATUS                 : BOUNDARY IDENTIFIED")
        print()
        print(
            "NEXT SAFE ACTION:"
        )
        print(
            "  Review the identified production boundary, "
            "then integrate TECHNICAL CONTRACT SCOPE there."
        )
    else:
        print("STATUS                 : BLOCKED")
        print(
            "Production boundary is not sufficiently established."
        )

    print()
    print("=" * 100)
    print("READ-ONLY FORENSIC COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()