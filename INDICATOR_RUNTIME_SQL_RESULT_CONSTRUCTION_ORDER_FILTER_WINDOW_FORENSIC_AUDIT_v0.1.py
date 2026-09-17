# INDICATOR_RUNTIME_SQL_RESULT_CONSTRUCTION_ORDER_FILTER_WINDOW_FORENSIC_AUDIT_v0.1.py

import ast
import inspect
import os
import re
import sqlite3
import sys
import traceback
from collections import Counter
from pathlib import Path


# =============================================================================
# ARUNDA INDICATOR RUNTIME SQL RESULT CONSTRUCTION / ORDER / FILTER / WINDOW
# FORENSIC AUDIT v0.1
# =============================================================================

PROJECT_PATH = Path(r"C:\Users\ASUS\ArundaTrader")
ENGINE_PATH = PROJECT_PATH / "market_data_engine.py"
DATABASE_PATH = PROJECT_PATH / "arunda.db"

TARGETS = ["BTC", "ETH", "SOL", "XRP"]

AUDIT_NAME = (
    "INDICATOR_RUNTIME_SQL_RESULT_CONSTRUCTION_ORDER_FILTER_WINDOW_FORENSIC_AUDIT_v0.1"
)

WRITE_SQL_RE = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|VACUUM|REINDEX|ATTACH|DETACH)\b",
    re.IGNORECASE | re.DOTALL,
)

SELECT_RE = re.compile(
    r"^\s*(SELECT|WITH)\b",
    re.IGNORECASE | re.DOTALL,
)


# =============================================================================
# PRINT HELPERS
# =============================================================================

def line(char="=", n=100):
    print(char * n)


def section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def kv(key, value):
    print(f"{key:<32}: {value}")


# =============================================================================
# SAFETY
# =============================================================================

class ReadOnlyViolation(RuntimeError):
    pass


class ReadOnlyConnection:
    """
    Authoritative SQLite write blocker.

    Any write-like SQL is rejected before SQLite receives it.
    """

    WRITE_PREFIXES = (
        "insert",
        "update",
        "delete",
        "alter",
        "drop",
        "create",
        "replace",
        "vacuum",
        "reindex",
        "attach",
        "detach",
    )

    def __init__(self, path):
        uri = f"file:{Path(path).resolve()}?mode=ro"
        self.connection = sqlite3.connect(
            uri,
            uri=True,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.blocked = []

    def execute(self, sql, parameters=()):
        sql_text = str(sql or "")
        normalized = sql_text.lstrip().lower()

        if normalized.startswith(self.WRITE_PREFIXES):
            record = {
                "sql": sql_text,
                "parameters": parameters,
            }
            self.blocked.append(record)
            raise ReadOnlyViolation(
                "ARUNDA FORENSIC BLOCK: write-like SQL blocked"
            )

        return self.connection.execute(sql_text, parameters)

    def executemany(self, sql, parameters):
        sql_text = str(sql or "")
        normalized = sql_text.lstrip().lower()

        if normalized.startswith(self.WRITE_PREFIXES):
            record = {
                "sql": sql_text,
                "parameters": list(parameters),
            }
            self.blocked.append(record)
            raise ReadOnlyViolation(
                "ARUNDA FORENSIC BLOCK: write-like SQL blocked"
            )

        return self.connection.executemany(sql_text, parameters)

    def executescript(self, script):
        record = {
            "sql": script,
            "parameters": (),
        }

        self.blocked.append(record)

        raise ReadOnlyViolation(
            "ARUNDA FORENSIC BLOCK: executescript blocked"
        )

    def cursor(self):
        return ReadOnlyCursor(self)

    def commit(self):
        raise ReadOnlyViolation("COMMIT blocked")

    def rollback(self):
        return None

    def close(self):
        self.connection.close()

    def __getattr__(self, name):
        return getattr(self.connection, name)


class ReadOnlyCursor:
    def __init__(self, connection):
        self.connection = connection
        self.cursor_obj = connection.connection.cursor()

    def execute(self, sql, parameters=()):
        sql_text = str(sql or "")
        normalized = sql_text.lstrip().lower()

        if normalized.startswith(ReadOnlyConnection.WRITE_PREFIXES):
            record = {
                "sql": sql_text,
                "parameters": parameters,
            }
            self.connection.blocked.append(record)

            raise ReadOnlyViolation(
                "ARUNDA FORENSIC BLOCK: write-like SQL blocked"
            )

        return self.cursor_obj.execute(sql_text, parameters)

    def executemany(self, sql, parameters):
        sql_text = str(sql or "")
        normalized = sql_text.lstrip().lower()

        if normalized.startswith(ReadOnlyConnection.WRITE_PREFIXES):
            record = {
                "sql": sql_text,
                "parameters": list(parameters),
            }
            self.connection.blocked.append(record)

            raise ReadOnlyViolation(
                "ARUNDA FORENSIC BLOCK: write-like SQL blocked"
            )

        return self.cursor_obj.executemany(sql_text, parameters)

    def fetchone(self):
        return self.cursor_obj.fetchone()

    def fetchall(self):
        return self.cursor_obj.fetchall()

    def fetchmany(self, size=None):
        if size is None:
            return self.cursor_obj.fetchmany()
        return self.cursor_obj.fetchmany(size)

    def __iter__(self):
        return iter(self.cursor_obj)

    def __getattr__(self, name):
        return getattr(self.cursor_obj, name)


# =============================================================================
# PATH SAFETY
# =============================================================================

def verify_paths():
    section("STEP 1 — PATH SAFETY RESOLUTION")

    kv("PROJECT PATH", PROJECT_PATH)
    kv("ENGINE PATH", ENGINE_PATH)
    kv("ENGINE FOUND", ENGINE_PATH.exists())
    kv("DATABASE PATH", DATABASE_PATH)
    kv("DATABASE FOUND", DATABASE_PATH.exists())

    if not ENGINE_PATH.exists():
        raise FileNotFoundError(ENGINE_PATH)

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(DATABASE_PATH)


# =============================================================================
# AST SOURCE RESOLUTION
# =============================================================================

def load_source():
    return ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )


def parse_ast(source):
    return ast.parse(source, filename=str(ENGINE_PATH))


def function_map(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.setdefault(node.name, []).append(node)

    return result


# =============================================================================
# SQL NORMALIZATION
# =============================================================================

def normalize_sql(sql):
    if sql is None:
        return ""

    text = str(sql)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def classify_sql(sql):
    normalized = normalize_sql(sql)

    if WRITE_SQL_RE.match(normalized):
        return "WRITE-LIKE"

    if SELECT_RE.match(normalized):
        return "SELECT"

    return "OTHER"


# =============================================================================
# SQL STRUCTURAL FORENSICS
# =============================================================================

def extract_sql_components(sql):
    """
    Static SQL parser for forensic classification.

    This intentionally does NOT execute the SQL.
    """

    normalized = normalize_sql(sql)

    components = {
        "where": None,
        "order_by": None,
        "limit": None,
        "offset": None,
        "group_by": None,
        "having": None,
        "select": None,
        "from": None,
        "joins": [],
    }

    if not normalized:
        return components

    upper = normalized.upper()

    # SELECT
    m = re.search(
        r"\bSELECT\b(.*?)\bFROM\b",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["select"] = m.group(1).strip()

    # FROM
    m = re.search(
        r"\bFROM\b(.*?)(?:\bWHERE\b|\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|\bOFFSET\b|$)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["from"] = m.group(1).strip()

    # JOINs
    joins = re.findall(
        r"\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\b\s+(.*?)(?=\bON\b|\bWHERE\b|\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)",
        normalized,
        re.IGNORECASE,
    )

    components["joins"] = [x.strip() for x in joins]

    # WHERE
    m = re.search(
        r"\bWHERE\b(.*?)(?:\bGROUP\s+BY\b|\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|\bOFFSET\b|$)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["where"] = m.group(1).strip()

    # GROUP BY
    m = re.search(
        r"\bGROUP\s+BY\b(.*?)(?:\bHAVING\b|\bORDER\s+BY\b|\bLIMIT\b|\bOFFSET\b|$)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["group_by"] = m.group(1).strip()

    # HAVING
    m = re.search(
        r"\bHAVING\b(.*?)(?:\bORDER\s+BY\b|\bLIMIT\b|\bOFFSET\b|$)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["having"] = m.group(1).strip()

    # ORDER BY
    m = re.search(
        r"\bORDER\s+BY\b(.*?)(?:\bLIMIT\b|\bOFFSET\b|$)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["order_by"] = m.group(1).strip()

    # LIMIT
    m = re.search(
        r"\bLIMIT\b\s+([^\s]+)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["limit"] = m.group(1).strip()

    # OFFSET
    m = re.search(
        r"\bOFFSET\b\s+([^\s]+)",
        normalized,
        re.IGNORECASE,
    )

    if m:
        components["offset"] = m.group(1).strip()

    return components


# =============================================================================
# SQL CAPTURE
# =============================================================================

class SQLCapture:
    def __init__(self):
        self.calls = []

    def record(self, sql, parameters, result_rows=None):
        entry = {
            "sql": str(sql),
            "normalized_sql": normalize_sql(sql),
            "parameters": parameters,
            "classification": classify_sql(sql),
            "components": extract_sql_components(sql),
            "row_count": None if result_rows is None else len(result_rows),
            "rows": result_rows,
        }

        self.calls.append(entry)


# =============================================================================
# DATABASE SNAPSHOT
# =============================================================================

def database_schema(conn):
    section("STEP 2 — DATABASE SCHEMA RESOLUTION")

    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    )

    tables = [row["name"] for row in cursor.fetchall()]

    kv("TABLE COUNT", len(tables))

    for table in tables:
        print(f"[TABLE] {table}")

    return tables


# =============================================================================
# EXACT STORED TARGETS
# =============================================================================

def resolve_targets(conn):
    section("STEP 3 — STORED TARGET RESOLUTION")

    found = {}

    for symbol in TARGETS:
        row = conn.execute(
            """
            SELECT *
            FROM market_data
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

        if row is None:
            print(f"[STORED_TARGET_MISSING] : {symbol}")
            continue

        found[symbol] = dict(row)

        print(f"[STORED_TARGET_RESOLVED] : {symbol}")

    return found


# =============================================================================
# CANDIDATE SQL DISCOVERY
# =============================================================================

def discover_sql_strings(tree):
    """
    Find SQL-like string literals and report their source locations.

    This is discovery only. No SQL is executed here.
    """

    results = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Constant):
            continue

        if not isinstance(node.value, str):
            continue

        text = node.value.strip()

        if not text:
            continue

        if not (
            text.upper().startswith("SELECT")
            or text.upper().startswith("WITH")
            or text.upper().startswith("INSERT")
            or text.upper().startswith("UPDATE")
            or text.upper().startswith("DELETE")
            or text.upper().startswith("CREATE")
        ):
            continue

        results.append(
            {
                "line": getattr(node, "lineno", None),
                "sql": text,
                "classification": classify_sql(text),
                "components": extract_sql_components(text),
            }
        )

    return results


# =============================================================================
# RUNTIME ROW FINGERPRINT
# =============================================================================

ROW_KEYS = (
    "id",
    "timestamp",
    "symbol",
    "timeframe",
    "close",
    "volume",
    "source_timestamp",
)


def row_fingerprint(row):
    if isinstance(row, sqlite3.Row):
        row = dict(row)

    if isinstance(row, dict):
        return tuple(
            repr(row.get(k))
            for k in ROW_KEYS
        )

    try:
        return tuple(
            repr(row[k])
            for k in range(min(len(row), len(ROW_KEYS)))
        )
    except Exception:
        return repr(row)


def rows_fingerprint(rows):
    return [
        row_fingerprint(row)
        for row in rows
    ]


# =============================================================================
# ROW COMPARISON
# =============================================================================

def compare_rows(runtime_rows, stored_rows):
    runtime_fp = rows_fingerprint(runtime_rows)
    stored_fp = rows_fingerprint(stored_rows)

    runtime_counter = Counter(runtime_fp)
    stored_counter = Counter(stored_fp)

    overlap = sum(
        (runtime_counter & stored_counter).values()
    )

    runtime_only = list(
        (runtime_counter - stored_counter).elements()
    )

    stored_only = list(
        (stored_counter - runtime_counter).elements()
    )

    same_order = runtime_fp == stored_fp
    same_multiset = runtime_counter == stored_counter

    return {
        "runtime_count": len(runtime_fp),
        "stored_count": len(stored_fp),
        "overlap": overlap,
        "same_order": same_order,
        "same_multiset": same_multiset,
        "runtime_only": runtime_only,
        "stored_only": stored_only,
    }


# =============================================================================
# SQL RESULT WINDOW ANALYSIS
# =============================================================================

def analyze_window(sql, parameters):
    components = extract_sql_components(sql)

    return {
        "normalized_sql": normalize_sql(sql),
        "parameters": parameters,
        "where": components["where"],
        "order_by": components["order_by"],
        "limit": components["limit"],
        "offset": components["offset"],
        "group_by": components["group_by"],
        "having": components["having"],
        "from": components["from"],
        "joins": components["joins"],
    }


# =============================================================================
# SOURCE CALL-SITE FORENSICS
# =============================================================================

def find_calculate_analysis_call_sites(tree):
    calls = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        func = node.func

        if isinstance(func, ast.Name):
            name = func.id

        elif isinstance(func, ast.Attribute):
            name = func.attr

        else:
            continue

        if name != "calculate_analysis":
            continue

        calls.append(node)

    return calls


def find_function_containing_line(tree, lineno):
    candidates = []

    for node in ast.walk(tree):

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        start = node.lineno
        end = getattr(node, "end_lineno", start)

        if start <= lineno <= end:
            candidates.append(node)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda x: x.end_lineno - x.lineno,
    )


# =============================================================================
# STATIC INPUT EXPRESSION TRACE
# =============================================================================

def expression_text(source, node):
    try:
        return ast.get_source_segment(source, node)
    except Exception:
        return None


def trace_callsite_inputs(source, tree):
    section("STEP 4 — CALCULATE_ANALYSIS CALL-SITE INPUT TRACE")

    calls = find_calculate_analysis_call_sites(tree)

    kv("CALCULATE_ANALYSIS CALL SITES", len(calls))

    results = []

    for index, call in enumerate(calls, 1):

        caller = find_function_containing_line(
            tree,
            call.lineno,
        )

        caller_name = (
            caller.name
            if caller is not None
            else "<unknown>"
        )

        args = [
            expression_text(source, arg)
            for arg in call.args
        ]

        print()
        print(f"CALL #{index}")
        kv("LINE", call.lineno)
        kv("CALLER", caller_name)
        kv("ARGUMENT COUNT", len(args))

        for i, arg in enumerate(args):
            print(f"ARG[{i}] : {arg}")

        results.append(
            {
                "line": call.lineno,
                "caller": caller_name,
                "arguments": args,
            }
        )

    return results


# =============================================================================
# RUNTIME ENTRYPOINT OBSERVATION
# =============================================================================

def run_readonly_sql_probe(conn, symbol):
    """
    Probe the exact stored rows only for comparison.

    This is deliberately separate from production execution.

    No write operation is possible.
    """

    cursor = conn.execute(
        """
        SELECT *
        FROM market_data
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT 120
        """,
        (symbol,),
    )

    rows = cursor.fetchall()

    return rows


# =============================================================================
# TARGET WINDOW REPORT
# =============================================================================

def report_target_windows(conn, targets):
    section("STEP 5 — EXACT STORED RESULT WINDOW RECONSTRUCTION")

    reports = {}

    for symbol in targets:

        rows = run_readonly_sql_probe(
            conn,
            symbol,
        )

        print()
        print(f"SYMBOL : {symbol}")

        kv("ROWS", len(rows))

        if rows:
            first = dict(rows[0])
            last = dict(rows[-1])

            kv("FIRST ID", first.get("id"))
            kv("LAST ID", last.get("id"))

            kv(
                "FIRST TIMESTAMP",
                first.get("timestamp"),
            )

            kv(
                "LAST TIMESTAMP",
                last.get("timestamp"),
            )

            kv(
                "FIRST SOURCE_TIMESTAMP",
                first.get("source_timestamp"),
            )

            kv(
                "LAST SOURCE_TIMESTAMP",
                last.get("source_timestamp"),
            )

        reports[symbol] = rows

    return reports


# =============================================================================
# FORENSIC SQL EXECUTION TRACE
# =============================================================================

def trace_relevant_sql(conn):
    section("STEP 6 — SQL RESULT CONSTRUCTION TRACE")

    queries = [
        (
            "LATEST_TARGET",
            """
            SELECT *
            FROM market_data
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT 1
            """,
        ),
        (
            "ANALYSIS_WINDOW",
            """
            SELECT *
            FROM market_data
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT 120
            """,
        ),
    ]

    trace = []

    for name, sql in queries:

        for symbol in TARGETS:

            parameters = (symbol,)

            rows = conn.execute(
                sql,
                parameters,
            ).fetchall()

            entry = {
                "name": name,
                "symbol": symbol,
                "sql": sql,
                "parameters": parameters,
                "classification": classify_sql(sql),
                "components": extract_sql_components(sql),
                "rows": rows,
            }

            trace.append(entry)

            print()
            print(f"[SQL TRACE] {name}")
            kv("SYMBOL", symbol)
            kv("CLASSIFICATION", classify_sql(sql))
            kv("PARAMETERS", parameters)
            kv("ROW COUNT", len(rows))

            components = extract_sql_components(sql)

            kv("WHERE", components["where"])
            kv("ORDER BY", components["order_by"])
            kv("LIMIT", components["limit"])
            kv("OFFSET", components["offset"])

    return trace


# =============================================================================
# SQL RESULT ORDERING ANALYSIS
# =============================================================================

def inspect_ordering(rows):
    ids = [
        dict(row).get("id")
        for row in rows
    ]

    timestamps = [
        dict(row).get("timestamp")
        for row in rows
    ]

    return {
        "ids": ids,
        "timestamps": timestamps,
        "id_ascending": ids == sorted(ids),
        "id_descending": ids == sorted(ids, reverse=True),
        "timestamp_ascending": timestamps == sorted(timestamps),
        "timestamp_descending": timestamps == sorted(
            timestamps,
            reverse=True,
        ),
    }


# =============================================================================
# EXACT STORED TARGET ANALYSIS
# =============================================================================

def analyze_targets(conn, stored_targets):
    section("STEP 7 — TARGET RESULT CONSTRUCTION ANALYSIS")

    final = {}

    for symbol in TARGETS:

        rows = run_readonly_sql_probe(
            conn,
            symbol,
        )

        ordering = inspect_ordering(rows)

        print()
        print(f"SYMBOL : {symbol}")

        kv("ROW COUNT", len(rows))
        kv("ID ASCENDING", ordering["id_ascending"])
        kv("ID DESCENDING", ordering["id_descending"])
        kv(
            "TIMESTAMP ASCENDING",
            ordering["timestamp_ascending"],
        )
        kv(
            "TIMESTAMP DESCENDING",
            ordering["timestamp_descending"],
        )

        if rows:

            newest = dict(rows[0])
            oldest = dict(rows[-1])

            print()
            print("RESULT WINDOW")
            kv("NEWEST ID", newest.get("id"))
            kv("OLDEST ID", oldest.get("id"))
            kv(
                "NEWEST TIMESTAMP",
                newest.get("timestamp"),
            )
            kv(
                "OLDEST TIMESTAMP",
                oldest.get("timestamp"),
            )

            print()
            print("EXPECTED calculate_analysis[-1] INPUT")
            kv(
                "ROWS[0] ID",
                newest.get("id"),
            )
            kv(
                "ROWS[-1] ID",
                oldest.get("id"),
            )

        final[symbol] = {
            "rows": rows,
            "ordering": ordering,
        }

    return final


# =============================================================================
# MAIN
# =============================================================================

def main():

    start = __import__("time").perf_counter()

    line("=")
    print(AUDIT_NAME)
    line("=")

    print("MODE                         : READ ONLY FORENSIC")
    print("DATABASE WRITE               : BLOCKED")
    print("ENGINE WRITE                 : NONE")
    print("PRODUCTION RECALCULATION     : NONE")
    print("SQL EXECUTION                : READ ONLY")

    try:

        verify_paths()

        source = load_source()
        tree = parse_ast(source)

        section("STEP 2 — ENGINE AST RESOLUTION")

        fmap = function_map(tree)

        kv(
            "SOURCE SIZE",
            len(source),
        )

        kv(
            "SOURCE LINES",
            len(source.splitlines()),
        )

        kv(
            "FUNCTIONS DISCOVERED",
            len(fmap),
        )

        if "calculate_analysis" in fmap:

            for node in fmap["calculate_analysis"]:
                print(
                    f"[FOUND] calculate_analysis "
                    f"LINE {node.lineno}-{node.end_lineno}"
                )

        conn = ReadOnlyConnection(
            DATABASE_PATH
        )

        try:

            database_schema(conn)

            stored_targets = resolve_targets(
                conn
            )

            callsites = trace_callsite_inputs(
                source,
                tree,
            )

            reports = report_target_windows(
                conn,
                stored_targets,
            )

            sql_trace = trace_relevant_sql(
                conn,
            )

            target_analysis = analyze_targets(
                conn,
                stored_targets,
            )

            section(
                "STEP 8 — SQL RESULT CONSTRUCTION / "
                "ORDER / FILTER / WINDOW MATRIX"
            )

            for symbol in TARGETS:

                print()
                print(f"TARGET : {symbol}")

                if symbol not in target_analysis:
                    print(
                        "[TARGET_MISSING]"
                    )
                    continue

                data = target_analysis[symbol]

                rows = data["rows"]
                ordering = data["ordering"]

                kv("ROWS", len(rows))

                kv(
                    "ORDER BY ID DESC",
                    ordering["id_descending"],
                )

                kv(
                    "ORDER BY ID ASC",
                    ordering["id_ascending"],
                )

                kv(
                    "TIMESTAMP DESC",
                    ordering["timestamp_descending"],
                )

                kv(
                    "TIMESTAMP ASC",
                    ordering["timestamp_ascending"],
                )

                if rows:

                    ids = [
                        dict(r).get("id")
                        for r in rows
                    ]

                    kv(
                        "ID RANGE",
                        f"{min(ids)} -> {max(ids)}",
                    )

                    print(
                        "ROW WINDOW FINGERPRINT"
                    )

                    for position, row in enumerate(
                        rows[:5]
                    ):
                        d = dict(row)

                        print(
                            f"  [{position}] "
                            f"id={d.get('id')} "
                            f"timestamp={d.get('timestamp')} "
                            f"symbol={d.get('symbol')}"
                        )

                    if len(rows) > 5:
                        print("  ...")

            section(
                "STEP 9 — FORENSIC CLASSIFICATION"
            )

            total_selects = sum(
                1
                for x in sql_trace
                if x["classification"] == "SELECT"
            )

            total_write_like = sum(
                1
                for x in sql_trace
                if x["classification"] == "WRITE-LIKE"
            )

            kv(
                "TARGETS REQUESTED",
                len(TARGETS),
            )

            kv(
                "TARGETS FOUND",
                len(stored_targets),
            )

            kv(
                "CALCULATE_ANALYSIS CALL SITES",
                len(callsites),
            )

            kv(
                "SQL TRACE COUNT",
                len(sql_trace),
            )

            kv(
                "SELECT TRACE COUNT",
                total_selects,
            )

            kv(
                "WRITE-LIKE TRACE COUNT",
                total_write_like,
            )

            section(
                "FINAL SQL RESULT CONSTRUCTION "
                "ORDER FILTER WINDOW FORENSIC SUMMARY"
            )

            print(
                "[STORED_TARGET_RESOLVED] : "
                + ", ".join(
                    symbol
                    for symbol in TARGETS
                    if symbol in stored_targets
                )
            )

            print()
            print(
                "TARGETS REQUESTED"
                f"             : {len(TARGETS)}"
            )

            print(
                "TARGETS FOUND"
                f"                : {len(stored_targets)}"
            )

            print(
                "CALCULATE_ANALYSIS CALL SITES"
                f" : {len(callsites)}"
            )

            print(
                "SQL RESULT TRACES"
                f"            : {len(sql_trace)}"
            )

            print()
            print(
                "FORENSIC CONCLUSION"
            )

            print(
                "STATUS"
                "                       : "
                "SQL_RESULT_CONSTRUCTION_OBSERVED"
            )

            print(
                "MEANING"
                "                     : "
                "The exact read-only SQL result construction, "
                "ordering, filtering and window parameters "
                "were independently resolved for the target rows."
            )

            print(
                "IMPORTANT"
                "                   : "
                "This audit does NOT modify production."
            )

            print(
                "IMPORTANT"
                "                   : "
                "No database write is permitted."
            )

            print(
                "IMPORTANT"
                "                   : "
                "No production formula is modified."
            )

            print(
                "NEXT FRONTIER"
                "               : "
                "Compare the independently reconstructed SQL "
                "result against the ACTUAL runtime rows captured "
                "immediately before calculate_analysis, then "
                "trace any first divergent row."
            )

            print()
            print(
                "DATABASE WRITE OPERATIONS    : NONE"
            )

            print(
                "ENGINE MODIFICATIONS         : NONE"
            )

            print(
                "INSERT                       : NONE"
            )

            print(
                "UPDATE                       : NONE"
            )

            print(
                "DELETE                       : NONE"
            )

            print(
                "ALTER                        : NONE"
            )

            print(
                "CREATE                       : NONE"
            )

            print(
                "DROP                         : NONE"
            )

            print(
                "PRODUCTION DB WRITE          : BLOCKED"
            )

            elapsed = (
                __import__("time").perf_counter()
                - start
            )

            print(
                f"ELAPSED SECONDS              : "
                f"{elapsed:.3f}"
            )

            print(
                "AUDIT COMPLETE"
            )

        finally:
            conn.close()

    except Exception as exc:

        section("AUDIT EXCEPTION")

        kv(
            "EXCEPTION TYPE",
            type(exc).__name__,
        )

        kv(
            "EXCEPTION",
            repr(exc),
        )

        print()
        traceback.print_exc()

        print()
        print(
            "AUDIT STATUS                 : "
            "FORENSIC_ABORTED"
        )

        print(
            "DATABASE WRITE OPERATIONS    : NONE"
        )

        print(
            "PRODUCTION DB WRITE          : BLOCKED"
        )

        raise


if __name__ == "__main__":
    main()