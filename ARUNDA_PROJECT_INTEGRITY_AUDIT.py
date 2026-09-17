#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARUNDA TRADER — PROJECT INTEGRITY AUDIT v1.0
==============================================================

MODE:
    READ ONLY

PURPOSE:
    Independent integrity / regression audit of the current
    ArundaTrader project state.

HARD GUARANTEES:
    - No source modification
    - No database writes
    - No INSERT / UPDATE / DELETE
    - No ALTER / CREATE / DROP
    - No generated production data
    - No interpolation
    - No forward fill
    - No backward fill
    - No padding
    - No duplication
    - No execution
    - No network access

OUTPUT:
    ARUNDA_PROJECT_INTEGRITY_AUDIT.txt

This script is intentionally conservative.
It reports findings; it does NOT repair anything.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path


# ==============================================================
# CONFIGURATION
# ==============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "arunda.db"
OUTPUT_PATH = PROJECT_ROOT / "ARUNDA_PROJECT_INTEGRITY_AUDIT.txt"

PYTHON_EXT = ".py"

# Directories that should not be treated as production source.
EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
}

# Files/directories commonly containing generated or temporary material.
IGNORED_FILE_PATTERNS = {
    ".pyc",
    ".pyo",
}

# Production-critical / known architectural names.
EXPECTED_KEYWORDS = {
    "feature": [
        "feature",
        "feature_contract",
        "feature_engine",
        "runtime_feature_producer",
    ],
    "score": [
        "score",
        "scorer",
    ],
    "signal": [
        "signal",
        "signal_engine",
        "signal_validator",
    ],
    "decision": [
        "decision",
    ],
    "risk": [
        "risk",
    ],
    "trade_gate": [
        "trade_gate",
        "trade",
        "execution_gate",
        "execution",
        "order_intent",
    ],
}

FORBIDDEN_WRITE_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bALTER\b",
    r"\bDROP\b",
    r"\bCREATE\s+TABLE\b",
    r"\bCREATE\s+INDEX\b",
    r"\bREPLACE\s+INTO\b",
    r"\bUPSERT\b",
]

DANGEROUS_RUNTIME_PATTERNS = [
    r"\brequests\.",
    r"\burllib\.",
    r"\bhttpx\.",
    r"\baiohttp\.",
    r"\bsocket\.",
    r"\bsubprocess\.",
    r"\bos\.system\s*\(",
    r"\bos\.popen\s*\(",
]

SYNTHETIC_DATA_PATTERNS = [
    r"\binterpolat",
    r"\bforward\s*fill\b",
    r"\bbackward\s*fill\b",
    r"\bbfill\b",
    r"\bffill\b",
    r"\bpadding\b",
    r"\bpad\s*\(",
    r"\breindex\s*\(",
    r"\bduplicate",
    r"\bsynthetic",
    r"\bfake\s+(?:data|bar|price|score|feature)",
]

WINDOW_PATTERNS = [
    r"\bWINDOW_SIZE\b",
    r"\bFULL_CONTEXT_TARGET\b",
    r"\bMIN_CONTEXT\b",
    r"\b150\b",
    r"\b21\b",
]

EXECUTION_PATTERNS = [
    r"\bEXECUTION_ENABLED\b",
    r"\bexecute_order\b",
    r"\bplace_order\b",
    r"\bsubmit_order\b",
    r"\border_intent\b",
]


# ==============================================================
# UTILITIES
# ==============================================================

class Audit:
    def __init__(self):
        self.sections = []
        self.findings = []
        self.warnings = []
        self.info = []

        self.stats = {
            "python_files": 0,
            "python_files_compiled": 0,
            "python_files_syntax_failed": 0,
            "ast_parse_failed": 0,
            "imports_checked": 0,
            "imports_failed": 0,
            "db_tables": 0,
            "db_views": 0,
            "db_indexes": 0,
            "db_triggers": 0,
        }

    def add(self, level, message):
        record = f"[{level}] {message}"

        if level == "FAIL":
            self.findings.append(record)
        elif level == "WARN":
            self.warnings.append(record)
        else:
            self.info.append(record)

    def section(self, title):
        self.sections.append(title)

    def render(self):
        lines = []

        lines.append("=" * 100)
        lines.append("ARUNDA TRADER — PROJECT INTEGRITY AUDIT v1.0")
        lines.append("=" * 100)
        lines.append("")
        lines.append("MODE              : READ ONLY")
        lines.append(f"PROJECT ROOT      : {PROJECT_ROOT}")
        lines.append(f"DATABASE          : {DB_PATH}")
        lines.append(f"OUTPUT            : {OUTPUT_PATH}")
        lines.append("")
        lines.append("WRITE OPERATIONS  : NONE")
        lines.append("NETWORK ACCESS    : NONE")
        lines.append("EXECUTION         : NOT RUN")
        lines.append("")

        lines.append("=" * 100)
        lines.append("EXECUTIVE RESULT")
        lines.append("=" * 100)

        if self.findings:
            final_status = "REGRESSION / INTEGRITY FAILURE DETECTED"
        elif self.warnings:
            final_status = "PASS WITH WARNINGS"
        else:
            final_status = "PASS"

        lines.append(f"FINAL STATUS      : {final_status}")
        lines.append(f"FAILURES          : {len(self.findings)}")
        lines.append(f"WARNINGS          : {len(self.warnings)}")
        lines.append(f"INFO              : {len(self.info)}")
        lines.append("")

        lines.append("=" * 100)
        lines.append("STATISTICS")
        lines.append("=" * 100)

        for key, value in self.stats.items():
            lines.append(f"{key:<32}: {value}")

        lines.append("")

        lines.append("=" * 100)
        lines.append("FAILURES")
        lines.append("=" * 100)

        if self.findings:
            lines.extend(self.findings)
        else:
            lines.append("NONE")

        lines.append("")

        lines.append("=" * 100)
        lines.append("WARNINGS")
        lines.append("=" * 100)

        if self.warnings:
            lines.extend(self.warnings)
        else:
            lines.append("NONE")

        lines.append("")

        lines.append("=" * 100)
        lines.append("INFORMATION")
        lines.append("=" * 100)

        if self.info:
            lines.extend(self.info)
        else:
            lines.append("NONE")

        lines.append("")

        return "\n".join(lines)


audit = Audit()


# ==============================================================
# FILE DISCOVERY
# ==============================================================

def iter_project_files():
    """
    Read-only recursive traversal.
    """
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in files:
            path = Path(root) / filename

            if path == OUTPUT_PATH:
                continue

            if path.suffix.lower() in IGNORED_FILE_PATTERNS:
                continue

            yield path


def python_files():
    return sorted(
        p for p in iter_project_files()
        if p.suffix.lower() == PYTHON_EXT
    )


# ==============================================================
# FILESYSTEM INTEGRITY
# ==============================================================

def audit_filesystem():
    audit.section("FILESYSTEM")

    if not PROJECT_ROOT.exists():
        audit.add("FAIL", "Project root does not exist.")
        return

    if not PROJECT_ROOT.is_dir():
        audit.add("FAIL", "Project root is not a directory.")
        return

    audit.add("INFO", f"Project root exists: {PROJECT_ROOT}")

    files = list(iter_project_files())

    audit.add("INFO", f"Visible project files: {len(files)}")

    py = [p for p in files if p.suffix.lower() == ".py"]

    audit.stats["python_files"] = len(py)

    audit.add("INFO", f"Python files discovered: {len(py)}")

    if not DB_PATH.exists():
        audit.add("WARN", "Production database arunda.db was not found.")
    else:
        audit.add("INFO", f"Database exists: {DB_PATH}")


# ==============================================================
# HASHING
# ==============================================================

def sha256_file(path: Path):
    """
    Read-only SHA256.
    """
    h = hashlib.sha256()

    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)

                if not chunk:
                    break

                h.update(chunk)

        return h.hexdigest()

    except Exception as exc:
        audit.add(
            "WARN",
            f"Could not hash {path.relative_to(PROJECT_ROOT)}: {exc}"
        )
        return None


def audit_source_fingerprints():
    audit.section("SOURCE FINGERPRINTS")

    files = python_files()

    rows = []

    for path in files:
        digest = sha256_file(path)

        try:
            size = path.stat().st_size
            mtime = path.stat().st_mtime
        except Exception:
            size = -1
            mtime = 0

        rows.append(
            (
                str(path.relative_to(PROJECT_ROOT)),
                size,
                int(mtime),
                digest,
            )
        )

    rows.sort()

    audit.add("INFO", f"SHA256 fingerprints generated: {len(rows)}")

    # Only write fingerprints into the final audit report.
    audit.source_fingerprints = rows


# ==============================================================
# PYTHON SYNTAX / AST
# ==============================================================

def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            return None
    except Exception:
        return None


def audit_python_syntax():
    audit.section("PYTHON SYNTAX")

    files = python_files()

    for path in files:

        try:
            source = read_text(path)

            if source is None:
                audit.add(
                    "FAIL",
                    f"Cannot read Python source: {path.relative_to(PROJECT_ROOT)}"
                )
                continue

            compile(
                source,
                str(path),
                "exec",
                dont_inherit=True,
            )

            audit.stats["python_files_compiled"] += 1

        except SyntaxError as exc:
            audit.stats["python_files_syntax_failed"] += 1

            audit.add(
                "FAIL",
                (
                    f"Syntax failure: "
                    f"{path.relative_to(PROJECT_ROOT)} "
                    f"line={exc.lineno} "
                    f"offset={exc.offset} "
                    f"msg={exc.msg}"
                )
            )

        except Exception as exc:
            audit.add(
                "FAIL",
                f"Compilation failure: {path.relative_to(PROJECT_ROOT)} -> {exc}"
            )

    audit.add(
        "INFO",
        (
            f"Python compile result: "
            f"{audit.stats['python_files_compiled']} pass / "
            f"{audit.stats['python_files_syntax_failed']} fail"
        )
    )


def audit_ast():
    audit.section("AST PARSE")

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        try:
            ast.parse(source, filename=str(path))

        except SyntaxError:
            audit.stats["ast_parse_failed"] += 1

        except Exception as exc:
            audit.stats["ast_parse_failed"] += 1

            audit.add(
                "FAIL",
                f"AST failure: {path.relative_to(PROJECT_ROOT)} -> {exc}"
            )

    if audit.stats["ast_parse_failed"]:
        audit.add(
            "FAIL",
            f"AST parse failures: {audit.stats['ast_parse_failed']}"
        )
    else:
        audit.add("INFO", "AST parsing passed for all readable Python files.")


# ==============================================================
# STATIC IMPORT ANALYSIS
# ==============================================================

def module_name_from_path(path: Path):
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return None

    parts = list(relative.with_suffix("").parts)

    if not parts:
        return None

    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts)


def local_module_map():
    mapping = {}

    for path in python_files():
        module = module_name_from_path(path)

        if module:
            mapping[module] = path

    return mapping


def audit_imports():
    audit.section("IMPORT GRAPH")

    modules = local_module_map()

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        try:
            tree = ast.parse(source, filename=str(path))
        except Exception:
            continue

        current_module = module_name_from_path(path)

        for node in ast.walk(tree):

            imported = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    check_local_import(
                        imported,
                        path,
                        modules,
                    )

            elif isinstance(node, ast.ImportFrom):

                if node.module:
                    imported = node.module

                    if node.level == 0:
                        check_local_import(
                            imported,
                            path,
                            modules,
                        )

    audit.add(
        "INFO",
        (
            f"Local import references checked: "
            f"{audit.stats['imports_checked']}"
        )
    )

    if audit.stats["imports_failed"]:
        audit.add(
            "WARN",
            (
                f"Potential unresolved local imports: "
                f"{audit.stats['imports_failed']}"
            )
        )


def check_local_import(imported, source_path, modules):

    # Only treat exact local modules as candidates.
    # External libraries are ignored.

    candidates = [
        imported,
    ]

    parts = imported.split(".")

    for i in range(len(parts) - 1, 0, -1):
        candidates.append(".".join(parts[:i]))

    audit.stats["imports_checked"] += 1

    if any(c in modules for c in candidates):
        return

    # We cannot safely determine whether every unknown import
    # is external, so report only suspicious project-like names.
    first = parts[0]

    suspicious_names = {
        "arunda",
        "market",
        "signal",
        "feature",
        "score",
        "decision",
        "risk",
        "trade",
        "execution",
        "fusion",
        "outcome",
    }

    if first.lower() in suspicious_names:
        audit.stats["imports_failed"] += 1

        audit.add(
            "WARN",
            (
                f"Potential unresolved project import: "
                f"{source_path.relative_to(PROJECT_ROOT)} -> {imported}"
            )
        )


# ==============================================================
# ARCHITECTURE DISCOVERY
# ==============================================================

def audit_architecture():
    audit.section("ARCHITECTURE DISCOVERY")

    files = python_files()

    categorized = defaultdict(list)

    for path in files:
        name = path.name.lower()

        for category, keywords in EXPECTED_KEYWORDS.items():

            if any(k in name for k in keywords):
                categorized[category].append(path)

    audit.architecture = categorized

    for category in [
        "feature",
        "score",
        "signal",
        "decision",
        "risk",
        "trade_gate",
    ]:
        found = categorized.get(category, [])

        if found:
            names = ", ".join(
                str(p.relative_to(PROJECT_ROOT))
                for p in found
            )

            audit.add(
                "INFO",
                f"{category.upper()} candidates: {names}"
            )
        else:
            audit.add(
                "WARN",
                f"No obvious {category.upper()} source file discovered."
            )


# ==============================================================
# KEY SYMBOL / CONTRACT DISCOVERY
# ==============================================================

def find_symbol_occurrences(symbols):
    audit.section("KEY SYMBOL DISCOVERY")

    occurrences = defaultdict(list)

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        for symbol in symbols:

            # Avoid matching inside longer identifiers where possible.
            pattern = rf"\b{re.escape(symbol)}\b"

            for match in re.finditer(pattern, source):

                line = source.count("\n", 0, match.start()) + 1

                occurrences[symbol].append(
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        line,
                    )
                )

    audit.symbol_occurrences = occurrences

    for symbol in symbols:

        found = occurrences.get(symbol, [])

        if found:
            display = "; ".join(
                f"{file}:{line}"
                for file, line in found[:20]
            )

            extra = ""

            if len(found) > 20:
                extra = f" ... +{len(found) - 20} more"

            audit.add(
                "INFO",
                f"{symbol}: {len(found)} occurrence(s) -> {display}{extra}"
            )
        else:
            audit.add(
                "WARN",
                f"Symbol not found: {symbol}"
            )


# ==============================================================
# FORBIDDEN / DANGEROUS PATTERN SCAN
# ==============================================================

def scan_patterns():
    audit.section("STATIC POLICY SCAN")

    all_patterns = {
        "DATABASE_WRITE": FORBIDDEN_WRITE_PATTERNS,
        "RUNTIME_NETWORK_OR_PROCESS": DANGEROUS_RUNTIME_PATTERNS,
        "SYNTHETIC_DATA_RISK": SYNTHETIC_DATA_PATTERNS,
        "WINDOW_CONTEXT": WINDOW_PATTERNS,
        "EXECUTION": EXECUTION_PATTERNS,
    }

    audit.pattern_hits = defaultdict(list)

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        for category, patterns in all_patterns.items():

            for pattern in patterns:

                try:
                    matches = list(re.finditer(
                        pattern,
                        source,
                        flags=re.IGNORECASE,
                    ))
                except re.error:
                    continue

                for match in matches:

                    line = source.count(
                        "\n",
                        0,
                        match.start(),
                    ) + 1

                    audit.pattern_hits[category].append(
                        (
                            str(path.relative_to(PROJECT_ROOT)),
                            line,
                            match.group(0),
                        )
                    )

    # Do not automatically fail on every hit.
    # These are forensic indicators and require context.

    for category, hits in audit.pattern_hits.items():

        if not hits:
            audit.add(
                "INFO",
                f"{category}: no static hits."
            )
            continue

        audit.add(
            "WARN",
            f"{category}: {len(hits)} static hit(s) requiring context review."
        )


# ==============================================================
# EXECUTION STATE
# ==============================================================

def audit_execution_state():
    audit.section("EXECUTION STATE")

    found = []

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        if "EXECUTION_ENABLED" in source:
            for match in re.finditer(
                r"\bEXECUTION_ENABLED\b\s*=\s*([^\n#]+)",
                source,
            ):
                line = source.count(
                    "\n",
                    0,
                    match.start(),
                ) + 1

                value = match.group(1).strip()

                found.append(
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        line,
                        value,
                    )
                )

    audit.execution_values = found

    if not found:
        audit.add(
            "WARN",
            "EXECUTION_ENABLED assignment was not discovered."
        )
        return

    for file, line, value in found:

        audit.add(
            "INFO",
            f"EXECUTION_ENABLED at {file}:{line} = {value}"
        )

        normalized = value.replace(" ", "").lower()

        if normalized not in {"false", "0"}:
            audit.add(
                "FAIL",
                (
                    f"Execution may not be disabled: "
                    f"{file}:{line} = {value}"
                )
            )


# ==============================================================
# FEATURE / SCORE / SIGNAL / DECISION CONTRACT SCAN
# ==============================================================

def audit_pipeline_contracts():
    audit.section("PIPELINE CONTRACT SCAN")

    target_symbols = [
        "WINDOW_SIZE",
        "FULL_CONTEXT_TARGET",
        "MIN_CONTEXT",
        "FEATURE_CONTRACT_v0.3",
        "FEATURE_CONTRACT_v0.2",
        "load_feature_snapshot",
        "runtime_feature_producer",
        "load_scores",
        "align_scores",
        "calculate_score",
        "build_score",
        "score",
        "validated_signals",
        "decision_snapshot",
        "build_decision",
        "build_decision_snapshot",
        "validate_decision_snapshot",
    ]

    occurrences = getattr(
        audit,
        "symbol_occurrences",
        {},
    )

    for symbol in target_symbols:

        hits = occurrences.get(symbol, [])

        if not hits:
            continue

        audit.add(
            "INFO",
            f"Contract symbol active/present: {symbol}"
        )


# ==============================================================
# DATABASE READ-ONLY AUDIT
# ==============================================================

def sqlite_read_only_connect():
    """
    SQLite URI with mode=ro.

    This makes the DB connection explicitly read-only.
    """

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )


def audit_database():
    audit.section("DATABASE INTEGRITY — READ ONLY")

    if not DB_PATH.exists():
        audit.add("WARN", "arunda.db not found; DB audit skipped.")
        return

    try:
        conn = sqlite_read_only_connect()

    except Exception as exc:
        audit.add(
            "FAIL",
            f"Could not open database read-only: {exc}"
        )
        return

    try:

        conn.execute("PRAGMA query_only = ON")

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        if query_only != 1:
            audit.add(
                "FAIL",
                "SQLite query_only pragma is not enabled."
            )
        else:
            audit.add(
                "INFO",
                "SQLite connection is explicitly query-only."
            )

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity == "ok":
            audit.add(
                "INFO",
                "SQLite PRAGMA integrity_check = ok"
            )
        else:
            audit.add(
                "FAIL",
                f"SQLite integrity_check = {integrity}"
            )

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        views = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'view'
            ORDER BY name
            """
        ).fetchall()

        indexes = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
            ORDER BY name
            """
        ).fetchall()

        triggers = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'trigger'
            ORDER BY name
            """
        ).fetchall()

        audit.stats["db_tables"] = len(tables)
        audit.stats["db_views"] = len(views)
        audit.stats["db_indexes"] = len(indexes)
        audit.stats["db_triggers"] = len(triggers)

        audit.db_objects = {
            "tables": [x[0] for x in tables],
            "views": [x[0] for x in views],
            "indexes": [x[0] for x in indexes],
            "triggers": [x[0] for x in triggers],
        }

        audit.add(
            "INFO",
            f"DB tables={len(tables)} views={len(views)} "
            f"indexes={len(indexes)} triggers={len(triggers)}"
        )

        expected_tables = {
            "market_records",
            "market_history",
            "market_universe",
            "market_data",
            "market_history_repair",
            "market_state",
            "signal_outcomes",
            "fusion_signals",
        }

        existing = set(audit.db_objects["tables"])

        for table in sorted(expected_tables):

            if table in existing:
                audit.add(
                    "INFO",
                    f"Expected table present: {table}"
                )
            else:
                audit.add(
                    "WARN",
                    f"Expected historical table not found: {table}"
                )

        # Record row counts without modifying anything.
        audit.db_counts = {}

        for table in audit.db_objects["tables"]:

            # sqlite_master names are database identifiers.
            # Quote safely for this controlled identifier.
            safe_name = '"' + table.replace('"', '""') + '"'

            try:
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {safe_name}"
                ).fetchone()[0]

                audit.db_counts[table] = count

            except Exception as exc:
                audit.add(
                    "WARN",
                    f"Could not count table {table}: {exc}"
                )

    except Exception as exc:

        audit.add(
            "FAIL",
            f"Database read-only audit failure: {exc}"
        )

    finally:

        try:
            conn.close()
        except Exception:
            pass


# ==============================================================
# DATABASE SCHEMA AUDIT
# ==============================================================

def audit_database_schema():
    audit.section("DATABASE SCHEMA")

    if not DB_PATH.exists():
        return

    try:
        conn = sqlite_read_only_connect()
        conn.execute("PRAGMA query_only = ON")

    except Exception:
        return

    try:

        schema_rows = conn.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
            ORDER BY type, name
            """
        ).fetchall()

        audit.db_schema = schema_rows

        for object_type, name, sql in schema_rows:

            upper_sql = sql.upper()

            # We are inspecting the schema only.
            # Presence of triggers is noteworthy.
            if object_type == "trigger":

                audit.add(
                    "WARN",
                    f"Database trigger present: {name}"
                )

            # Detect obvious destructive/odd schema patterns.
            if "WITHOUT ROWID" in upper_sql:
                audit.add(
                    "INFO",
                    f"WITHOUT ROWID table/index construct: {name}"
                )

    except Exception as exc:

        audit.add(
            "WARN",
            f"Schema audit failed: {exc}"

        )

    finally:
        try:
            conn.close()
        except Exception:
            pass


# ==============================================================
# MARKET DATA SCHEMA
# ==============================================================

def audit_market_data_schema():
    audit.section("MARKET DATA SCHEMA")

    if not DB_PATH.exists():
        return

    try:
        conn = sqlite_read_only_connect()
        conn.execute("PRAGMA query_only = ON")

    except Exception:
        return

    try:

        rows = conn.execute(
            """
            PRAGMA table_info("market_data")
            """
        ).fetchall()

        if not rows:
            audit.add(
                "WARN",
                "market_data table not found or has no columns."
            )
            return

        columns = [row[1] for row in rows]

        audit.market_data_columns = columns

        expected = [
            "timestamp",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        missing = [
            col for col in expected
            if col not in columns
        ]

        if missing:

            audit.add(
                "FAIL",
                f"market_data missing expected OHLCV columns: {missing}"
            )

        else:

            audit.add(
                "INFO",
                "market_data contains expected OHLCV schema."
            )

    except Exception as exc:

        audit.add(
            "WARN",
            f"market_data schema audit failed: {exc}"
        )

    finally:

        try:
            conn.close()
        except Exception:
            pass


# ==============================================================
# DB READ-ONLY DATA FINGERPRINT
# ==============================================================

def audit_market_data_fingerprint():
    audit.section("MARKET DATA FINGERPRINT — READ ONLY")

    if not DB_PATH.exists():
        return

    try:
        conn = sqlite_read_only_connect()
        conn.execute("PRAGMA query_only = ON")

    except Exception:
        return

    try:

        exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table'
              AND name='market_data'
            """
        ).fetchone()[0]

        if not exists:
            audit.add(
                "WARN",
                "market_data table unavailable."
            )
            return

        total = conn.execute(
            'SELECT COUNT(*) FROM "market_data"'
        ).fetchone()[0]

        audit.market_data_total = total

        audit.add(
            "INFO",
            f"market_data total rows = {total:,}"
        )

        # Symbol distribution.
        rows = conn.execute(
            """
            SELECT symbol, COUNT(*) AS n
            FROM market_data
            GROUP BY symbol
            ORDER BY n DESC, symbol
            """
        ).fetchall()

        audit.market_data_distribution = rows

        audit.add(
            "INFO",
            f"market_data symbols = {len(rows)}"
        )

        # Latest timestamp.
        latest = conn.execute(
            'SELECT MAX(timestamp) FROM "market_data"'
        ).fetchone()[0]

        earliest = conn.execute(
            'SELECT MIN(timestamp) FROM "market_data"'
        ).fetchone()[0]

        audit.add(
            "INFO",
            f"market_data earliest timestamp = {earliest}"
        )

        audit.add(
            "INFO",
            f"market_data latest timestamp = {latest}"
        )

    except Exception as exc:

        audit.add(
            "WARN",
            f"market_data fingerprint failed: {exc}"
        )

    finally:

        try:
            conn.close()
        except Exception:
            pass


# ==============================================================
# RUNTIME ENTRYPOINT DISCOVERY
# ==============================================================

def audit_entrypoints():
    audit.section("RUNTIME ENTRYPOINT DISCOVERY")

    candidates = []

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        if re.search(
            r"if\s+__name__\s*==\s*[\"']__main__[\"']",
            source,
        ):
            candidates.append(
                str(path.relative_to(PROJECT_ROOT))
            )

    audit.entrypoints = candidates

    if candidates:

        for item in candidates:
            audit.add(
                "INFO",
                f"Python entrypoint: {item}"
            )

    else:

        audit.add(
            "WARN",
            "No __main__ entrypoint discovered."
        )


# ==============================================================
# FUNCTION / CLASS INVENTORY
# ==============================================================

def audit_symbol_inventory():
    audit.section("FUNCTION / CLASS INVENTORY")

    inventory = defaultdict(lambda: {
        "functions": [],
        "classes": [],
    })

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except Exception:
            continue

        relative = str(path.relative_to(PROJECT_ROOT))

        for node in ast.walk(tree):

            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                inventory[relative]["functions"].append(
                    node.name
                )

            elif isinstance(node, ast.ClassDef):
                inventory[relative]["classes"].append(
                    node.name
                )

    audit.inventory = inventory

    for file, data in inventory.items():

        important = [
            x for x in data["functions"]
            if any(
                token in x.lower()
                for token in [
                    "main",
                    "run",
                    "build",
                    "load",
                    "score",
                    "decision",
                    "risk",
                    "signal",
                    "feature",
                    "trade",
                    "validate",
                    "snapshot",
                    "process",
                ]
            )
        ]

        if important:

            audit.add(
                "INFO",
                (
                    f"{file} important functions: "
                    + ", ".join(sorted(set(important)))
                )
            )


# ==============================================================
# SUSPICIOUS CODE CHANGE DETECTION
# ==============================================================

def audit_suspicious_fallbacks():
    audit.section("FALLBACK / FABRICATION RISK")

    patterns = [
        r"\bexcept\s+Exception\s*:",
        r"\bexcept\s*:",
        r"\breturn\s+0(?:\.0+)?\b",
        r"\breturn\s+None\b",
        r"\bdefault\s*=",
        r"\bfallback\b",
        r"\bmock\b",
        r"\bplaceholder\b",
        r"\btest[_-]?data\b",
        r"\bdummy\b",
        r"\brandom\.",
    ]

    hits = []

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                source,
                flags=re.IGNORECASE,
            ):

                line = source.count(
                    "\n",
                    0,
                    match.start(),
                ) + 1

                hits.append(
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        line,
                        match.group(0),
                    )
                )

    audit.fallback_hits = hits

    if hits:

        audit.add(
            "WARN",
            (
                f"Potential fallback/default patterns found: "
                f"{len(hits)}"
            )
        )

    else:

        audit.add(
            "INFO",
            "No obvious fallback/default patterns discovered."
        )


# ==============================================================
# FEATURE CONTRACT SEMANTICS
# ==============================================================

def audit_feature_context_semantics():
    audit.section("FEATURE CONTEXT SEMANTICS")

    semantic_targets = {
        "FULL_CONTEXT_TARGET": False,
        "MIN_CONTEXT": False,
        "LIMITED": False,
        "FULL": False,
        "NONE": False,
    }

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        for key in semantic_targets:

            if re.search(
                rf"\b{re.escape(key)}\b",
                source,
                flags=re.IGNORECASE,
            ):
                semantic_targets[key] = True

    for key, found in semantic_targets.items():

        if found:
            audit.add(
                "INFO",
                f"Feature context semantic token present: {key}"
            )
        else:
            audit.add(
                "WARN",
                f"Feature context semantic token not discovered: {key}"
            )


# ==============================================================
# SCORE FORMULA DISCOVERY
# ==============================================================

def audit_score_formula():
    audit.section("SCORE FORMULA DISCOVERY")

    weights = {
        "return_20": 0.20,
        "momentum_20": 0.20,
        "trend_slope_20": 0.20,
        "acceleration": 0.10,
        "position_20": 0.10,
        "volatility_20": 0.10,
        "range_20": 0.10,
    }

    discovered = {}

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        for field, expected in weights.items():

            if re.search(
                rf"\b{re.escape(field)}\b",
                source,
            ):
                discovered[field] = True

    audit.score_formula_fields = discovered

    for field in weights:

        if field in discovered:
            audit.add(
                "INFO",
                f"Score component discovered: {field}"
            )
        else:
            audit.add(
                "WARN",
                f"Score component not discovered: {field}"
            )


# ==============================================================
# DECISION INPUT BOUNDARY CHECK
# ==============================================================

def audit_decision_boundary():
    audit.section("DECISION INPUT BOUNDARY")

    suspicious = []

    for path in python_files():

        source = read_text(path)

        if source is None:
            continue

        name = path.name.lower()

        if "decision" not in name:
            continue

        # We specifically look for the old raw-feature bridge.
        patterns = [
            r"\bbars_by_asset\b",
            r"\bindicators_by_asset\b",
            r"\bstructures_by_asset\b",
        ]

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                source,
            ):

                line = source.count(
                    "\n",
                    0,
                    match.start(),
                ) + 1

                suspicious.append(
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        line,
                        match.group(0),
                    )
                )

    audit.decision_boundary_hits = suspicious

    if suspicious:

        audit.add(
            "FAIL",
            (
                "Legacy raw-feature Decision boundary symbols "
                "still exist in Decision source."
            )
        )

    else:

        audit.add(
            "INFO",
            (
                "No bars_by_asset / indicators_by_asset / "
                "structures_by_asset symbols found in Decision files."
            )
        )


# ==============================================================
# SIGNAL SCORER BOUNDARY
# ==============================================================

def audit_signal_scorer_boundary():
    audit.section("SIGNAL SCORER BOUNDARY")

    hits = []

    for path in python_files():

        if "scor" not in path.name.lower():
            continue

        source = read_text(path)

        if source is None:
            continue

        for pattern in [
            r"\bload_scores\s*\(",
            r"\balign_scores\s*\(",
            r"\brun\s*\(",
        ]:

            for match in re.finditer(pattern, source):

                line = source.count(
                    "\n",
                    0,
                    match.start(),
                ) + 1

                hits.append(
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        line,
                        match.group(0),
                    )
                )

    audit.signal_scorer_hits = hits

    if hits:

        audit.add(
            "INFO",
            f"Potential Signal Scorer API symbols: {len(hits)}"
        )

    else:

        audit.add(
            "WARN",
            "Signal Scorer API symbols not discovered."
        )


# ==============================================================
# DUPLICATE PRODUCER DETECTION
# ==============================================================

def audit_duplicate_producers():
    audit.section("DUPLICATE PRODUCER DETECTION")

    producer_terms = [
        "score_producer",
        "runtime_score",
        "feature_producer",
        "runtime_feature",
        "signal_producer",
    ]

    found = defaultdict(list)

    for path in python_files():

        name = path.name.lower()

        for term in producer_terms:

            if term in name:
                found[term].append(
                    str(path.relative_to(PROJECT_ROOT))
                )

    audit.duplicate_producers = found

    for term, paths in found.items():

        if len(paths) > 1:

            audit.add(
                "WARN",
                (
                    f"Multiple files match producer role '{term}': "
                    + ", ".join(paths)
                )
            )

        else:

            audit.add(
                "INFO",
                f"Producer candidate '{term}': {paths[0]}"
            )


# ==============================================================
# PROJECT SIZE / LARGE FILES
# ==============================================================

def audit_large_files():
    audit.section("LARGE SOURCE FILES")

    rows = []

    for path in python_files():

        try:
            size = path.stat().st_size
        except Exception:
            continue

        rows.append(
            (
                size,
                str(path.relative_to(PROJECT_ROOT)),
            )
        )

    rows.sort(reverse=True)

    audit.large_files = rows[:30]

    for size, path in audit.large_files[:15]:

        audit.add(
            "INFO",
            f"Python source size: {size:,} bytes -> {path}"
        )


# ==============================================================
# ENVIRONMENT
# ==============================================================

def audit_environment():
    audit.section("ENVIRONMENT")

    audit.add(
        "INFO",
        f"Python executable: {sys.executable}"
    )

    audit.add(
        "INFO",
        f"Python version: {sys.version.replace(chr(10), ' ')}"
    )

    audit.add(
        "INFO",
        f"Platform: {sys.platform}"
    )

    audit.add(
        "INFO",
        f"Working directory: {Path.cwd()}"
    )


# ==============================================================
# REPORT DETAILS
# ==============================================================

def append_detailed_sections(lines):
    """
    Add structured detail to the final report.
    """

    lines.append("")
    lines.append("=" * 100)
    lines.append("DETAILED SOURCE FINGERPRINTS")
    lines.append("=" * 100)

    for path, size, mtime, digest in getattr(
        audit,
        "source_fingerprints",
        [],
    ):
        lines.append(
            f"{path} | size={size} | mtime={mtime} | sha256={digest}"
        )

    lines.append("")
    lines.append("=" * 100)
    lines.append("DATABASE TABLE COUNTS")
    lines.append("=" * 100)

    for table, count in sorted(
        getattr(audit, "db_counts", {}).items()
    ):
        lines.append(
            f"{table:<40} {count:,}"
        )

    lines.append("")
    lines.append("=" * 100)
    lines.append("DATABASE OBJECTS")
    lines.append("=" * 100)

    db_objects = getattr(
        audit,
        "db_objects",
        {},
    )

    for object_type, names in db_objects.items():

        lines.append("")
        lines.append(f"[{object_type.upper()}]")

        if names:
            lines.extend(
                f"  {name}"
                for name in names
            )
        else:
            lines.append("  NONE")

    lines.append("")
    lines.append("=" * 100)
    lines.append("MARKET DATA DISTRIBUTION")
    lines.append("=" * 100)

    distribution = getattr(
        audit,
        "market_data_distribution",
        [],
    )

    if distribution:

        for symbol, count in distribution:

            lines.append(
                f"{str(symbol):<25} {count:,}"
            )

    else:

        lines.append("NONE")

    lines.append("")
    lines.append("=" * 100)
    lines.append("EXECUTION ASSIGNMENTS")
    lines.append("=" * 100)

    execution_values = getattr(
        audit,
        "execution_values",
        [],
    )

    if execution_values:

        for file, line, value in execution_values:

            lines.append(
                f"{file}:{line} -> EXECUTION_ENABLED = {value}"
            )

    else:

        lines.append("NONE")

    lines.append("")
    lines.append("=" * 100)
    lines.append("STATIC POLICY HITS")
    lines.append("=" * 100)

    pattern_hits = getattr(
        audit,
        "pattern_hits",
        {},
    )

    for category, hits in pattern_hits.items():

        lines.append("")
        lines.append(f"[{category}]")

        if not hits:

            lines.append("  NONE")
            continue

        for file, line, match in hits[:250]:

            lines.append(
                f"  {file}:{line} -> {match!r}"
            )

        if len(hits) > 250:

            lines.append(
                f"  ... {len(hits) - 250} additional hit(s)"
            )

    lines.append("")
    lines.append("=" * 100)
    lines.append("FALLBACK / FABRICATION INDICATORS")
    lines.append("=" * 100)

    fallback_hits = getattr(
        audit,
        "fallback_hits",
        [],
    )

    if fallback_hits:

        for file, line, match in fallback_hits[:250]:

            lines.append(
                f"{file}:{line} -> {match!r}"
            )

    else:

        lines.append("NONE")

    lines.append("")
    lines.append("=" * 100)
    lines.append("DECISION BOUNDARY HITS")
    lines.append("=" * 100)

    decision_hits = getattr(
        audit,
        "decision_boundary_hits",
        [],
    )

    if decision_hits:

        for file, line, match in decision_hits:

            lines.append(
                f"{file}:{line} -> {match!r}"
            )

    else:

        lines.append("NONE")

    lines.append("")
    lines.append("=" * 100)
    lines.append("ENTRYPOINTS")
    lines.append("=" * 100)

    for item in getattr(
        audit,
        "entrypoints",
        [],
    ):
        lines.append(item)

    if not getattr(
        audit,
        "entrypoints",
        [],
    ):
        lines.append("NONE")

    lines.append("")
    lines.append("=" * 100)
    lines.append("IMPORTANT FUNCTION INVENTORY")
    lines.append("=" * 100)

    inventory = getattr(
        audit,
        "inventory",
        {},
    )

    for file, data in sorted(
        inventory.items()
    ):

        important = [
            x for x in data["functions"]
            if any(
                token in x.lower()
                for token in [
                    "main",
                    "run",
                    "build",
                    "load",
                    "score",
                    "decision",
                    "risk",
                    "signal",
                    "feature",
                    "trade",
                    "validate",
                    "snapshot",
                    "process",
                ]
            )
        ]

        if important:

            lines.append(
                f"{file}: {', '.join(sorted(set(important)))}"
            )

    lines.append("")
    lines.append("=" * 100)
    lines.append("END OF AUDIT")
    lines.append("=" * 100)


# ==============================================================
# MAIN AUDIT
# ==============================================================

def run_audit():

    started = time.time()

    # Important:
    # No source file is imported.
    #
    # This prevents module-level side effects,
    # database writes, execution, network calls,
    # and accidental runtime mutations.
    #
    # Static AST/compile analysis is intentionally used instead.

    audit_environment()

    audit_filesystem()

    audit_source_fingerprints()

    audit_python_syntax()

    audit_ast()

    audit_imports()

    audit_architecture()

    find_symbol_occurrences([
        "EXECUTION_ENABLED",
        "WINDOW_SIZE",
        "FULL_CONTEXT_TARGET",
        "MIN_CONTEXT",
        "FEATURE_CONTRACT_v0.3",
        "FEATURE_CONTRACT_v0.2",
        "load_feature_snapshot",
        "runtime_feature_producer",
        "load_scores",
        "align_scores",
        "validated_signals",
        "decision_snapshot",
        "bars_by_asset",
        "indicators_by_asset",
        "structures_by_asset",
    ])

    scan_patterns()

    audit_execution_state()

    audit_pipeline_contracts()

    audit_database()

    audit_database_schema()

    audit_market_data_schema()

    audit_market_data_fingerprint()

    audit_entrypoints()

    audit_symbol_inventory()

    audit_suspicious_fallbacks()

    audit_feature_context_semantics()

    audit_score_formula()

    audit_decision_boundary()

    audit_signal_scorer_boundary()

    audit_duplicate_producers()

    audit_large_files()

    elapsed = time.time() - started

    audit.add(
        "INFO",
        f"Audit elapsed time: {elapsed:.2f} seconds"
    )

    # ----------------------------------------------------------
    # FINAL REPORT
    # ----------------------------------------------------------

    report = audit.render()

    lines = report.splitlines()

    append_detailed_sections(lines)

    final_report = "\n".join(lines)

    # This is the ONLY write operation of the script.
    # It writes the audit report, never the project source or DB.
    #
    # If absolute zero file writes are required, redirect stdout
    # instead and comment this block out.

    try:
        OUTPUT_PATH.write_text(
            final_report,
            encoding="utf-8",
        )

    except Exception as exc:

        print(
            "ERROR: Could not write audit report:",
            exc,
        )

        print(final_report)

        return 2

    print(final_report)

    print("")
    print("=" * 100)
    print("AUDIT REPORT CREATED")
    print("=" * 100)
    print(OUTPUT_PATH)

    if audit.findings:
        return 1

    return 0


# ==============================================================
# ENTRY
# ==============================================================

if __name__ == "__main__":
    try:
        exit_code = run_audit()
    except KeyboardInterrupt:
        print("\nAudit interrupted by user.")
        exit_code = 130
    except Exception:
        traceback.print_exc()
        exit_code = 2

    raise SystemExit(exit_code)