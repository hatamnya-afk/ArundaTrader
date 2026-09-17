import ast
import inspect
import os
import re
import sqlite3
import sys
import traceback
import time
from collections import Counter


# =============================================================================
# ARUNDA
# INDICATOR PRODUCTION RUNTIME PRECALCULATION PATH FORENSIC AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Trace the actual production path immediately before calculate_analysis(rows)
# and capture the genuine runtime rows object without permitting database writes.
#
# SAFETY
# ------
# DATABASE WRITE             : BLOCKED
# ENGINE MODIFICATION       : NONE
# FORMULA MODIFICATION      : NONE
# PRODUCTION SOURCE MODIFY  : NONE
#
# IMPORTANT
# ---------
# This script does NOT alter market_data_engine.py.
# This script does NOT alter arunda.db.
# This script does NOT fabricate rows.
# Runtime rows are captured only if the real production execution creates them.
#
# =============================================================================


PROJECT_PATH = r"C:\Users\ASUS\ArundaTrader"
ENGINE_PATH = os.path.join(PROJECT_PATH, "market_data_engine.py")
DATABASE_PATH = os.path.join(PROJECT_PATH, "arunda.db")

TARGETS = ["BTC", "ETH", "SOL", "XRP"]

AUDIT_NAME = (
    "INDICATOR_PRODUCTION_RUNTIME_PRECALCULATION_PATH_FORENSIC_AUDIT_v0.1"
)


# =============================================================================
# GLOBAL FORENSIC STATE
# =============================================================================

STATE = {
    "start_time": time.perf_counter(),

    "calculate_calls": [],
    "runtime_returns": [],

    "sql_trace": [],
    "blocked_writes": [],

    "runtime_exceptions": [],

    "rows_observed": [],

    "production_main_executed": False,
    "production_main_completed": False,

    "entrypoint_name": None,

    "precalc_candidates": [],
    "precalc_runtime_functions": [],

    "schema_operations": [],
    "select_operations": [],

    "target_resolution": {},

    "capture_complete": False,
}


# =============================================================================
# PRINT HELPERS
# =============================================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=5000):
    try:
        text = repr(value)
    except Exception:
        text = "<UNREPRESENTABLE>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def normalize_sql(sql):
    if sql is None:
        return ""

    return re.sub(r"\s+", " ", str(sql)).strip()


def is_write_sql(sql):
    if not sql:
        return False

    normalized = normalize_sql(sql).upper()

    write_prefixes = (
        "INSERT ",
        "INSERT\n",
        "UPDATE ",
        "UPDATE\n",
        "DELETE ",
        "DELETE\n",
        "REPLACE ",
        "REPLACE\n",
        "CREATE ",
        "CREATE\n",
        "ALTER ",
        "ALTER\n",
        "DROP ",
        "DROP\n",
        "VACUUM",
        "REINDEX ",
        "REINDEX\n",
    )

    return normalized.startswith(write_prefixes)


def is_schema_sql(sql):
    if not sql:
        return False

    normalized = normalize_sql(sql).upper()

    return (
        normalized.startswith("CREATE ")
        or normalized.startswith("ALTER ")
        or normalized.startswith("DROP ")
    )


# =============================================================================
# SQLITE READ-ONLY FORENSIC PROXY
# =============================================================================

class ReadOnlyBlockedCursor:
    """
    Cursor proxy.

    SELECT statements:
        Execute normally against the read-only database.

    Write-like statements:
        Never reach SQLite.
        They are recorded as blocked forensic events.
    """

    def __init__(self, real_cursor, owner):
        self._cursor = real_cursor
        self._owner = owner

    def execute(self, sql, parameters=()):
        self._owner._record_sql(sql, parameters)

        if is_write_sql(sql):
            event = {
                "sql": str(sql),
                "parameters": parameters,
                "normalized_sql": normalize_sql(sql),
            }

            self._owner.blocked_writes.append(event)

            if is_schema_sql(sql):
                self._owner.schema_operations.append(event)

            # Return an empty forensic cursor without executing the write.
            return self

        if normalize_sql(sql).upper().startswith("SELECT "):
            self._owner.select_operations.append({
                "sql": str(sql),
                "parameters": parameters,
            })

        self._cursor.execute(sql, parameters)
        return self

    def executemany(self, sql, seq_of_parameters):
        event = {
            "sql": str(sql),
            "parameters": "<executemany>",
            "normalized_sql": normalize_sql(sql),
        }

        self._owner._record_sql(
            sql,
            "<executemany>"
        )

        self._owner.blocked_writes.append(event)
        return self

    def executescript(self, script):
        event = {
            "sql": str(script),
            "parameters": (),
            "normalized_sql": normalize_sql(script),
        }

        self._owner._record_sql(script, ())

        self._owner.blocked_writes.append(event)
        return self

    def fetchone(self):
        try:
            return self._cursor.fetchone()
        except sqlite3.ProgrammingError:
            return None

    def fetchmany(self, size=None):
        try:
            if size is None:
                return self._cursor.fetchmany()
            return self._cursor.fetchmany(size)
        except sqlite3.ProgrammingError:
            return []

    def fetchall(self):
        try:
            return self._cursor.fetchall()
        except sqlite3.ProgrammingError:
            return []

    def __iter__(self):
        try:
            return iter(self._cursor)
        except Exception:
            return iter(())

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class ReadOnlyBlockedConnection:
    """
    SQLite connection proxy.

    Real database:
        opened using SQLite URI mode=ro.

    Writes:
        blocked before SQLite receives them.

    Reads:
        passed through to the real read-only connection.
    """

    def __init__(self, real_connection, database_path):
        self._connection = real_connection
        self.database_path = database_path

        self.blocked_writes = []
        self.sql_trace = []
        self.schema_operations = []
        self.select_operations = []

    def _record_sql(self, sql, parameters):
        self.sql_trace.append({
            "sql": str(sql),
            "parameters": parameters,
            "write_like": is_write_sql(sql),
        })

    def cursor(self, *args, **kwargs):
        cursor = self._connection.cursor(*args, **kwargs)
        return ReadOnlyBlockedCursor(cursor, self)

    def execute(self, sql, parameters=()):
        cursor = self.cursor()
        return cursor.execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters):
        cursor = self.cursor()
        return cursor.executemany(sql, seq_of_parameters)

    def executescript(self, script):
        cursor = self.cursor()
        return cursor.executescript(script)

    def commit(self):
        # NEVER commit anything.
        return None

    def rollback(self):
        try:
            return self._connection.rollback()
        except Exception:
            return None

    def close(self):
        return self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()
        return False

    def __getattr__(self, name):
        return getattr(self._connection, name)


# =============================================================================
# READ-ONLY DATABASE FACTORY
# =============================================================================

ORIGINAL_SQLITE_CONNECT = sqlite3.connect


def forensic_sqlite_connect(database, *args, **kwargs):
    """
    Replacement for sqlite3.connect.

    Any path pointing to the production database is opened READ ONLY.
    """

    requested = str(database)

    requested_abs = os.path.abspath(
        requested.replace("file:", "")
    )

    production_abs = os.path.abspath(DATABASE_PATH)

    if requested_abs == production_abs or requested == DATABASE_PATH:
        uri = "file:" + production_abs.replace("\\", "/") + "?mode=ro"

        real_connection = ORIGINAL_SQLITE_CONNECT(
            uri,
            uri=True,
            check_same_thread=False,
        )

        proxy = ReadOnlyBlockedConnection(
            real_connection,
            production_abs,
        )

        STATE.setdefault("connections", []).append(proxy)

        return proxy

    # Any non-production database connection is also forced read-only
    # when possible.
    try:
        requested_abs = os.path.abspath(requested)

        uri = "file:" + requested_abs.replace("\\", "/") + "?mode=ro"

        real_connection = ORIGINAL_SQLITE_CONNECT(
            uri,
            uri=True,
            check_same_thread=False,
        )

        proxy = ReadOnlyBlockedConnection(
            real_connection,
            requested_abs,
        )

        STATE.setdefault("connections", []).append(proxy)

        return proxy

    except Exception:
        raise


# =============================================================================
# SOURCE / AST ANALYSIS
# =============================================================================

def load_engine_source():
    if not os.path.exists(ENGINE_PATH):
        raise FileNotFoundError(
            f"ENGINE NOT FOUND: {ENGINE_PATH}"
        )

    with open(
        ENGINE_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def parse_engine_source(source):
    return ast.parse(
        source,
        filename=ENGINE_PATH,
    )


def get_function_definitions(tree):
    functions = {}

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            functions.setdefault(
                node.name,
                []
            ).append(node)

    return functions


def function_source_lines(node):
    start = getattr(node, "lineno", None)
    end = getattr(
        node,
        "end_lineno",
        start,
    )

    return start, end


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []

        current = node

        while isinstance(
            current,
            ast.Attribute,
        ):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return None


def find_calculate_analysis(tree):
    result = []

    for node in ast.walk(tree):
        if (
            isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and node.name == "calculate_analysis"
        ):
            result.append(node)

    return result


def find_calculate_analysis_callers(tree):
    callers = []

    for function_node in ast.walk(tree):
        if not isinstance(
            function_node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        for node in ast.walk(function_node):
            if not isinstance(node, ast.Call):
                continue

            name = call_name(node.func)

            if name == "calculate_analysis":
                callers.append({
                    "caller": function_node.name,
                    "caller_line": function_node.lineno,
                    "call_line": node.lineno,
                    "arguments": [
                        ast.unparse(arg)
                        for arg in node.args
                    ],
                    "keywords": {
                        kw.arg: ast.unparse(kw.value)
                        for kw in node.keywords
                    },
                })

    return callers


def find_runtime_precalc_candidates(tree):
    """
    Identify assignments / calls surrounding calculate_analysis.

    We are especially interested in:
        rows = ...
        data = ...
        history = ...
        cursor.fetchall()
        cursor.execute(...)
        calculate_analysis(rows)
        analysis = calculate_analysis(rows)
    """

    candidates = []

    keywords = (
        "row",
        "rows",
        "data",
        "records",
        "history",
        "market_data",
        "fetchall",
        "fetchmany",
        "fetchone",
        "execute",
        "analysis",
        "calculate_analysis",
    )

    for function_node in ast.walk(tree):
        if not isinstance(
            function_node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        nodes = list(ast.walk(function_node))

        has_calc = any(
            isinstance(n, ast.Call)
            and call_name(n.func) == "calculate_analysis"
            for n in nodes
        )

        if not has_calc:
            continue

        for node in nodes:
            if isinstance(
                node,
                ast.Assign,
            ):
                try:
                    text = ast.unparse(node)
                except Exception:
                    continue

                lowered = text.lower()

                if any(
                    keyword in lowered
                    for keyword in keywords
                ):
                    candidates.append({
                        "function": function_node.name,
                        "line": node.lineno,
                        "type": "ASSIGNMENT",
                        "source": text,
                    })

            elif isinstance(
                node,
                ast.Call,
            ):
                try:
                    text = ast.unparse(node)
                except Exception:
                    continue

                lowered = text.lower()

                if any(
                    keyword in lowered
                    for keyword in keywords
                ):
                    candidates.append({
                        "function": function_node.name,
                        "line": node.lineno,
                        "type": "CALL",
                        "source": text,
                    })

    unique = []
    seen = set()

    for item in candidates:
        key = (
            item["function"],
            item["line"],
            item["type"],
            item["source"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return sorted(
        unique,
        key=lambda x: (
            x["function"],
            x["line"],
        ),
    )


def find_sql_operations(tree):
    operations = []

    for function_node in ast.walk(tree):
        if not isinstance(
            function_node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        for node in ast.walk(function_node):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = call_name(node.func)

            if name in {
                "execute",
                "executemany",
                "executescript",
            }:
                try:
                    source = ast.unparse(node)
                except Exception:
                    source = "<UNPARSEABLE>"

                operations.append({
                    "function": function_node.name,
                    "line": node.lineno,
                    "call": name,
                    "source": source,
                })

    return operations


# =============================================================================
# RUNTIME ROW CAPTURE
# =============================================================================

ORIGINAL_CALCULATE_ANALYSIS = None


def serialize_row(row):
    """
    Preserve the runtime object without changing it.

    sqlite3.Row / dict / tuple / custom row objects are handled.
    """

    result = {
        "type": type(row).__name__,
        "module": type(row).__module__,
    }

    if isinstance(row, sqlite3.Row):
        try:
            result["keys"] = list(row.keys())
            result["values"] = {
                key: row[key]
                for key in row.keys()
            }
        except Exception:
            result["repr"] = safe_repr(row)

        return result

    if isinstance(row, dict):
        result["keys"] = list(row.keys())
        result["values"] = dict(row)
        return result

    if isinstance(row, (tuple, list)):
        result["length"] = len(row)
        result["values"] = list(row)
        return result

    try:
        result["dict"] = dict(vars(row))
    except Exception:
        result["repr"] = safe_repr(row)

    return result


def extract_row_value(row, key, index=None):
    try:
        if isinstance(row, sqlite3.Row):
            return row[key]
    except Exception:
        pass

    try:
        if isinstance(row, dict):
            return row.get(key)
    except Exception:
        pass

    if index is not None:
        try:
            return row[index]
        except Exception:
            pass

    return None


def forensic_calculate_analysis(rows):
    """
    Runtime interception point.

    This does NOT replace the production implementation.

    It records the genuine rows object and then delegates to the original
    production calculate_analysis function.
    """

    call_id = len(STATE["calculate_calls"]) + 1

    event = {
        "call_id": call_id,
        "rows_type": type(rows).__name__,
        "rows_module": type(rows).__module__,
        "rows_length": None,
        "rows": [],
        "first_row": None,
        "last_row": None,
    }

    try:
        event["rows_length"] = len(rows)
    except Exception:
        event["rows_length"] = None

    try:
        iterable_rows = list(rows)
    except Exception:
        iterable_rows = []

    event["rows_length_materialized"] = len(iterable_rows)

    for row in iterable_rows:
        serialized = serialize_row(row)
        event["rows"].append(serialized)

    if event["rows"]:
        event["first_row"] = event["rows"][0]
        event["last_row"] = event["rows"][-1]

    # Compact close/timestamp analysis
    closes = []
    timestamps = []
    symbols = []

    for row in iterable_rows:

        close = extract_row_value(
            row,
            "close",
            7,
        )

        timestamp = extract_row_value(
            row,
            "timestamp",
            1,
        )

        symbol = extract_row_value(
            row,
            "symbol",
            2,
        )

        closes.append(close)
        timestamps.append(timestamp)
        symbols.append(symbol)

    event["close_count"] = len(closes)
    event["close_first"] = (
        closes[0]
        if closes
        else None
    )
    event["close_last"] = (
        closes[-1]
        if closes
        else None
    )

    event["timestamp_first"] = (
        timestamps[0]
        if timestamps
        else None
    )

    event["timestamp_last"] = (
        timestamps[-1]
        if timestamps
        else None
    )

    event["symbols"] = sorted(
        {
            str(x)
            for x in symbols
            if x is not None
        }
    )

    event["target_present"] = [
        target
        for target in TARGETS
        if target in event["symbols"]
    ]

    STATE["calculate_calls"].append(event)
    STATE["rows_observed"].append(event)

    print()
    print("[RUNTIME] calculate_analysis INTERCEPTED")
    print(f"CALL ID                 : {call_id}")
    print(f"ROWS TYPE               : {event['rows_type']}")
    print(f"ROWS LENGTH             : {event['rows_length']}")
    print(
        f"MATERIALIZED ROWS       : "
        f"{event['rows_length_materialized']}"
    )
    print(f"CLOSE COUNT             : {event['close_count']}")
    print(f"CLOSE FIRST             : {event['close_first']}")
    print(f"CLOSE LAST              : {event['close_last']}")
    print(
        f"TIMESTAMP FIRST         : "
        f"{event['timestamp_first']}"
    )
    print(
        f"TIMESTAMP LAST          : "
        f"{event['timestamp_last']}"
    )
    print(
        f"SYMBOLS                 : "
        f"{event['symbols'][:30]}"
    )
    print(
        f"TARGETS PRESENT         : "
        f"{event['target_present']}"
    )

    # IMPORTANT:
    # Delegate to the real production implementation.
    result = ORIGINAL_CALCULATE_ANALYSIS(rows)

    STATE["runtime_returns"].append({
        "call_id": call_id,
        "return_type": type(result).__name__,
        "return_value": result,
    })

    print()
    print("[RUNTIME] calculate_analysis PRODUCTION RETURN CAPTURED")
    print(f"CALL ID                 : {call_id}")
    print(f"RETURN TYPE             : {type(result).__name__}")
    print(f"RETURN                  : {safe_repr(result, 3000)}")

    return result


# =============================================================================
# PATCH PRODUCTION MODULE
# =============================================================================

def patch_module(module):
    global ORIGINAL_CALCULATE_ANALYSIS

    if not hasattr(
        module,
        "calculate_analysis",
    ):
        raise RuntimeError(
            "Production module does not expose calculate_analysis"
        )

    ORIGINAL_CALCULATE_ANALYSIS = (
        module.calculate_analysis
    )

    module.calculate_analysis = (
        forensic_calculate_analysis
    )

    return module


# =============================================================================
# TARGET DATABASE RESOLUTION
# =============================================================================

def resolve_targets_from_database():
    section("STEP 4 — DATABASE TARGET RESOLUTION")

    conn = forensic_sqlite_connect(
        DATABASE_PATH
    )

    try:
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT
                    symbol,
                    COUNT(*) AS row_count,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp
                FROM market_data
                WHERE symbol IN (?, ?, ?, ?)
                GROUP BY symbol
                ORDER BY symbol
                """,
                tuple(TARGETS),
            )

            rows = cursor.fetchall()

        except Exception as exc:
            print(
                f"DATABASE TARGET RESOLUTION ERROR: {exc}"
            )
            rows = []

        for row in rows:
            symbol = row[0]

            STATE["target_resolution"][
                symbol
            ] = {
                "row_count": row[1],
                "first_timestamp": row[2],
                "last_timestamp": row[3],
            }

            print(
                f"[STORED_TARGET_RESOLVED] : "
                f"{symbol}"
            )
            print(
                f"  ROWS                 : {row[1]}"
            )
            print(
                f"  FIRST                : {row[2]}"
            )
            print(
                f"  LAST                 : {row[3]}"
            )

    finally:
        conn.close()


# =============================================================================
# RUNTIME SQL TRACE COLLECTION
# =============================================================================

def collect_connection_traces():
    for connection in STATE.get(
        "connections",
        [],
    ):
        STATE["sql_trace"].extend(
            connection.sql_trace
        )

        STATE["blocked_writes"].extend(
            connection.blocked_writes
        )

        STATE["schema_operations"].extend(
            connection.schema_operations
        )

        STATE["select_operations"].extend(
            connection.select_operations
        )


# =============================================================================
# EXECUTION
# =============================================================================

def execute_production_main(module):
    section(
        "STEP 8 — PRODUCTION ENTRYPOINT PRECALCULATION RUNTIME"
    )

    main_function = getattr(
        module,
        "main",
        None,
    )

    if not callable(main_function):
        print(
            "MAIN ENTRYPOINT              : NOT FOUND"
        )
        return

    STATE["entrypoint_name"] = "main"
    STATE["production_main_executed"] = True

    print(
        "ENTRYPOINT                   : main"
    )
    print(
        "ARGUMENTS                    : ()"
    )
    print(
        "DATABASE WRITE               : BLOCKED"
    )
    print(
        "RUNTIME ROW CAPTURE          : ENABLED"
    )

    try:
        result = main_function()

        STATE["production_main_completed"] = True

        print()
        print(
            "ENTRYPOINT EXECUTION STATUS : COMPLETED"
        )
        print(
            f"MAIN RETURN TYPE             : "
            f"{type(result).__name__}"
        )
        print(
            f"MAIN RETURN                 : "
            f"{safe_repr(result, 2000)}"
        )

    except Exception as exc:

        STATE["runtime_exceptions"].append({
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })

        print()
        print(
            "ENTRYPOINT EXECUTION STATUS : STOPPED"
        )
        print(
            f"EXCEPTION                    : "
            f"{type(exc).__name__}"
        )
        print(
            f"MESSAGE                      : "
            f"{exc}"
        )

        print()
        print(
            "IMPORTANT:"
        )
        print(
            "This exception is recorded as an actual runtime "
            "observation."
        )
        print(
            "No rows or return values are fabricated."
        )


# =============================================================================
# RUNTIME ROW ANALYSIS
# =============================================================================

def analyze_runtime_rows():
    section(
        "STEP 9 — ACTUAL PRECALCULATION ROWS ANALYSIS"
    )

    if not STATE["calculate_calls"]:
        print(
            "CALCULATE_ANALYSIS CALLS      : 0"
        )
        print(
            "RUNTIME ROW OBJECT             : NOT OBSERVED"
        )
        return

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{len(STATE['calculate_calls'])}"
    )

    for event in STATE["calculate_calls"]:

        print()
        print(
            f"CALL #{event['call_id']}"
        )

        print(
            f"ROWS LENGTH                  : "
            f"{event['rows_length_materialized']}"
        )

        print(
            f"CLOSE FIRST                  : "
            f"{event['close_first']}"
        )

        print(
            f"CLOSE LAST                   : "
            f"{event['close_last']}"
        )

        print(
            f"TIMESTAMP FIRST              : "
            f"{event['timestamp_first']}"
        )

        print(
            f"TIMESTAMP LAST               : "
            f"{event['timestamp_last']}"
        )

        print(
            f"TARGETS PRESENT              : "
            f"{event['target_present']}"
        )

        if event["first_row"]:
            print()
            print(
                "FIRST RUNTIME ROW"
            )
            print(
                safe_repr(
                    event["first_row"],
                    5000,
                )
            )

        if event["last_row"]:
            print()
            print(
                "LAST RUNTIME ROW"
            )
            print(
                safe_repr(
                    event["last_row"],
                    5000,
                )
            )


# =============================================================================
# SQL TRACE SUMMARY
# =============================================================================

def print_sql_summary():
    section(
        "STEP 10 — RUNTIME SQL PRECALCULATION TRACE"
    )

    print(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(STATE['sql_trace'])}"
    )

    print(
        f"SELECT OPERATIONS             : "
        f"{len(STATE['select_operations'])}"
    )

    print(
        f"BLOCKED WRITE OPERATIONS      : "
        f"{len(STATE['blocked_writes'])}"
    )

    print(
        f"SCHEMA OPERATIONS             : "
        f"{len(STATE['schema_operations'])}"
    )

    if STATE["sql_trace"]:

        print()
        print(
            "SQL TRACE"
        )

        for index, item in enumerate(
            STATE["sql_trace"],
            start=1,
        ):

            print()
            print(
                f"SQL CALL #{index}"
            )

            print(
                f"WRITE-LIKE                  : "
                f"{item['write_like']}"
            )

            print(
                f"SQL                         : "
                f"{item['sql']}"
            )

            print(
                f"PARAMETERS                  : "
                f"{safe_repr(item['parameters'], 2000)}"
            )


# =============================================================================
# SOURCE PATH SUMMARY
# =============================================================================

def print_source_path_summary(
    callers,
    precalc_candidates,
    sql_operations,
):
    section(
        "STEP 11 — PRODUCTION PRECALCULATION PATH MAP"
    )

    print(
        f"CALCULATE_ANALYSIS CALLERS    : "
        f"{len(callers)}"
    )

    for caller in callers:
        print()
        print(
            f"[CALLER] {caller['caller']} "
            f"line={caller['caller_line']}"
        )
        print(
            f"CALL LINE                   : "
            f"{caller['call_line']}"
        )
        print(
            f"ARGUMENTS                   : "
            f"{caller['arguments']}"
        )
        print(
            f"KEYWORDS                    : "
            f"{caller['keywords']}"
        )

    print()
    print(
        f"PRECALCULATION CANDIDATES    : "
        f"{len(precalc_candidates)}"
    )

    for item in precalc_candidates:

        print(
            f"[{item['type']}] "
            f"{item['function']} "
            f"line={item['line']}"
        )

        print(
            f"  {item['source']}"
        )

    print()
    print(
        f"STATIC SQL OPERATIONS        : "
        f"{len(sql_operations)}"
    )


# =============================================================================
# WRITE SAFETY
# =============================================================================

def verify_write_safety():
    section(
        "STEP 12 — WRITE SAFETY VERIFICATION"
    )

    blocked = len(
        STATE["blocked_writes"]
    )

    print(
        "DATABASE CONNECTION MODE     : READ ONLY"
    )

    print(
        "SQLITE AUTHORITATIVE BLOCK   : ENABLED"
    )

    print(
        "WRITE-LIKE SQL BLOCK         : ENABLED"
    )

    print(
        f"BLOCKED WRITE OPERATIONS     : "
        f"{blocked}"
    )

    if blocked:
        for item in STATE["blocked_writes"][:20]:

            print()
            print(
                "[BLOCKED]"
            )

            print(
                f"SQL                         : "
                f"{item['sql']}"
            )

            print(
                f"PARAMETERS                  : "
                f"{safe_repr(item['parameters'], 2000)}"
            )

    print()
    print(
        "DATABASE WRITE OPERATIONS    : NONE"
    )


# =============================================================================
# FINAL FORENSIC CLASSIFICATION
# =============================================================================

def final_classification():
    section(
        "FINAL PRODUCTION RUNTIME PRECALCULATION FORENSIC SUMMARY"
    )

    calls = len(
        STATE["calculate_calls"]
    )

    returns = len(
        STATE["runtime_returns"]
    )

    blocked = len(
        STATE["blocked_writes"]
    )

    exceptions = len(
        STATE["runtime_exceptions"]
    )

    print(
        f"TARGETS REQUESTED             : "
        f"{len(TARGETS)}"
    )

    print(
        f"TARGETS FOUND IN DATABASE     : "
        f"{len(STATE['target_resolution'])}"
    )

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{calls}"
    )

    print(
        f"RUNTIME RETURNS                : "
        f"{returns}"
    )

    print(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(STATE['sql_trace'])}"
    )

    print(
        f"SELECT OPERATIONS             : "
        f"{len(STATE['select_operations'])}"
    )

    print(
        f"BLOCKED WRITE-LIKE OPERATIONS : "
        f"{blocked}"
    )

    print(
        f"RUNTIME EXCEPTIONS             : "
        f"{exceptions}"
    )

    if calls > 0:

        status = (
            "PRODUCTION_PRECALCULATION_RUNTIME_OBSERVED"
        )

        meaning = (
            "The genuine production runtime reached "
            "calculate_analysis and the actual rows object "
            "was captured immediately before indicator calculation."
        )

        next_frontier = (
            "Compare the captured runtime rows against the exact "
            "stored market_data rows and trace the post-calculation "
            "assignment path."
        )

    elif exceptions > 0:

        status = (
            "PRODUCTION_PRECALCULATION_RUNTIME_BLOCKED_OR_INTERRUPTED"
        )

        meaning = (
            "Production execution started, but an actual runtime "
            "exception prevented calculate_analysis from being reached."
        )

        next_frontier = (
            "Resolve the exact runtime blocker shown above without "
            "fabricating rows, then repeat this same forensic stage."
        )

    else:

        status = (
            "PRODUCTION_PRECALCULATION_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The production entrypoint executed or was attempted, "
            "but no genuine runtime rows object reached calculate_analysis."
        )

        next_frontier = (
            "Trace the exact pre-calculation data construction path "
            "or the runtime provider/data-loading branch that prevents "
            "calculate_analysis from being reached."
        )

    print()
    print(
        f"STATUS                       : {status}"
    )

    print(
        f"MEANING                      : {meaning}"
    )

    print(
        f"NEXT FRONTIER                : {next_frontier}"
    )

    print()
    print(
        "IMPORTANT                    : "
        "No runtime rows are fabricated."
    )

    print(
        "IMPORTANT                    : "
        "No production formula is modified."
    )

    print(
        "IMPORTANT                    : "
        "No database write is permitted."
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

    elapsed = (
        time.perf_counter()
        - STATE["start_time"]
    )

    print(
        f"ELAPSED SECONDS              : "
        f"{elapsed:.3f}"
    )

    print(
        "AUDIT COMPLETE"
    )

    line("=")


# =============================================================================
# MAIN AUDIT
# =============================================================================

def run_audit():

    line("=")

    print(
        "ARUNDA "
        "INDICATOR PRODUCTION RUNTIME PRECALCULATION PATH "
        "FORENSIC AUDIT v0.1"
    )

    line("=")

    print(
        "MODE                         : "
        "READ ONLY RUNTIME FORENSICS"
    )

    print(
        "DATABASE WRITE               : "
        "BLOCKED"
    )

    print(
        "ENGINE WRITE                 : "
        "NONE"
    )

    print(
        "FORMULA WRITE                : "
        "NONE"
    )

    print(
        "PRODUCTION RECALCULATION     : "
        "IN-MEMORY OBSERVATION ONLY"
    )

    print(
        "TARGETS                      : "
        "BTC / ETH / SOL / XRP"
    )

    # -------------------------------------------------------------------------
    # STEP 1
    # -------------------------------------------------------------------------

    section(
        "STEP 1 — PATH SAFETY RESOLUTION"
    )

    print(
        f"PROJECT PATH                 : "
        f"{PROJECT_PATH}"
    )

    print(
        f"ENGINE PATH                  : "
        f"{ENGINE_PATH}"
    )

    print(
        f"ENGINE FOUND                 : "
        f"{os.path.exists(ENGINE_PATH)}"
    )

    print(
        f"DATABASE PATH                : "
        f"{DATABASE_PATH}"
    )

    print(
        f"DATABASE FOUND               : "
        f"{os.path.exists(DATABASE_PATH)}"
    )

    if not os.path.exists(ENGINE_PATH):
        raise FileNotFoundError(
            ENGINE_PATH
        )

    if not os.path.exists(DATABASE_PATH):
        raise FileNotFoundError(
            DATABASE_PATH
        )

    # -------------------------------------------------------------------------
    # STEP 2
    # -------------------------------------------------------------------------

    source = load_engine_source()

    tree = parse_engine_source(
        source
    )

    functions = get_function_definitions(
        tree
    )

    calculate_nodes = find_calculate_analysis(
        tree
    )

    callers = find_calculate_analysis_callers(
        tree
    )

    precalc_candidates = (
        find_runtime_precalc_candidates(
            tree
        )
    )

    sql_operations = find_sql_operations(
        tree
    )

    STATE["precalc_candidates"] = (
        precalc_candidates
    )

    section(
        "STEP 2 — PRODUCTION SOURCE RESOLUTION"
    )

    print(
        f"SOURCE SIZE                 : "
        f"{len(source)} characters"
    )

    print(
        f"SOURCE LINES                : "
        f"{len(source.splitlines())}"
    )

    print(
        f"FUNCTIONS DISCOVERED        : "
        f"{len(functions)}"
    )

    print(
        f"CALCULATE_ANALYSIS DEFINITIONS : "
        f"{len(calculate_nodes)}"
    )

    for node in calculate_nodes:

        start, end = function_source_lines(
            node
        )

        print(
            f"[FOUND] calculate_analysis "
            f"LINE {start}-{end}"
        )

    # -------------------------------------------------------------------------
    # STEP 3
    # -------------------------------------------------------------------------

    section(
        "STEP 3 — STATIC PRECALCULATION CALL PATH"
    )

    print(
        f"CALCULATE_ANALYSIS CALL SITES : "
        f"{len(callers)}"
    )

    for caller in callers:

        print(
            f"[CALLER] {caller['caller']} "
            f"@ line {caller['call_line']}"
        )

    # -------------------------------------------------------------------------
    # STEP 4
    # -------------------------------------------------------------------------

    resolve_targets_from_database()

    # -------------------------------------------------------------------------
    # STEP 5
    # -------------------------------------------------------------------------

    section(
        "STEP 5 — SQLITE FORENSIC WRITE BLOCK ACTIVATION"
    )

    sqlite3.connect = forensic_sqlite_connect

    print(
        "READ-ONLY CONNECTION FACTORY  : ENABLED"
    )

    print(
        "SQLITE AUTHORITATIVE BLOCK     : ENABLED"
    )

    print(
        "WRITE-LIKE SQL BLOCK           : ENABLED"
    )

    # -------------------------------------------------------------------------
    # STEP 6
    # -------------------------------------------------------------------------

    section(
        "STEP 6 — PRODUCTION ENGINE IMPORT"
    )

    # Ensure project path is importable.
    if PROJECT_PATH not in sys.path:
        sys.path.insert(
            0,
            PROJECT_PATH,
        )

    import market_data_engine

    print(
        "MODULE IMPORTED               : "
        "market_data_engine"
    )

    # -------------------------------------------------------------------------
    # STEP 7
    # -------------------------------------------------------------------------

    section(
        "STEP 7 — RUNTIME calculate_analysis PATCH"
    )

    patch_module(
        market_data_engine
    )

    print(
        "PATCHED REFERENCES            : 1"
    )

    print(
        "[PATCHED] market_data_engine.calculate_analysis"
    )

    # -------------------------------------------------------------------------
    # STEP 8
    # -------------------------------------------------------------------------

    print_source_path_summary(
        callers,
        precalc_candidates,
        sql_operations,
    )

    # -------------------------------------------------------------------------
    # STEP 9
    # -------------------------------------------------------------------------

    execute_production_main(
        market_data_engine
    )

    # -------------------------------------------------------------------------
    # STEP 10
    # -------------------------------------------------------------------------

    collect_connection_traces()

    analyze_runtime_rows()

    # -------------------------------------------------------------------------
    # STEP 11
    # -------------------------------------------------------------------------

    print_sql_summary()

    # -------------------------------------------------------------------------
    # STEP 12
    # -------------------------------------------------------------------------

    verify_write_safety()

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    final_classification()


# =============================================================================
# ENTRY
# =============================================================================

if __name__ == "__main__":

    try:
        run_audit()

    except Exception as exc:

        print()
        line("=")

        print(
            "AUDIT FATAL ERROR"
        )

        print(
            f"TYPE                       : "
            f"{type(exc).__name__}"
        )

        print(
            f"MESSAGE                    : "
            f"{exc}"
        )

        print()
        traceback.print_exc()

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "The forensic audit failed."
        )

        print(
            "No database write is intentionally permitted."
        )

        line("=")

    finally:

        # Restore sqlite3.connect so this audit script does not leave
        # the interpreter globally patched after completion.
        sqlite3.connect = ORIGINAL_SQLITE_CONNECT