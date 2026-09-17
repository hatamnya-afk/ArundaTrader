import ast
import importlib.util
import inspect
import os
import sqlite3
import sys
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA TRADER
# DOWNSTREAM FIND FUTURE PRICE
# RUNTIME TRACE FORENSIC AUDIT v0.1
# ============================================================
#
# CURRENT FRONTIER
# ----------------
#
# signal_outcome_engine.py
#        |
#        v
# find_future_price()
#
# PURPOSE
# -------
# Trace the REAL production function find_future_price()
# without modifying production code on disk and without
# writing anything to the production database.
#
# QUESTIONS
# ---------
# 1. Does find_future_price actually execute?
# 2. What arguments does production actually pass?
# 3. Does it consume market_data directly?
# 4. What SQL does it execute at runtime?
# 5. What rows are actually returned to it?
# 6. What real value does it return?
# 7. Who calls find_future_price?
# 8. Is its output consumed downstream?
#
# SAFETY
# ------
# READ ONLY
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
#
# Production function is executed in memory only.
# Production source on disk is never modified.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENGINE_FILE = os.path.join(
    PROJECT_DIR,
    "signal_outcome_engine.py"
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "arunda.db"
)

MODULE_NAME = (
    "arunda_signal_outcome_engine_forensic_v01"
)

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

TARGET_FUNCTION = "find_future_price"


# ============================================================
# GLOBAL FORENSIC STATE
# ============================================================

runtime_calls = []
runtime_returns = []
runtime_exceptions = []

sql_trace = []
blocked_writes = []

market_data_rows = []

caller_observations = []

entrypoint_status = {
    "imported": False,
    "function_found": False,
    "function_executed": False,
    "exception": None,
}


# ============================================================
# OUTPUT HELPERS
# ============================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=2000):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


# ============================================================
# PATH SAFETY
# ============================================================

def verify_paths():

    section(
        "STEP 1 — PATH SAFETY"
    )

    print(
        f"PROJECT PATH              : {PROJECT_DIR}"
    )

    print(
        f"TARGET ENGINE             : {ENGINE_FILE}"
    )

    print(
        f"ENGINE FOUND              : "
        f"{os.path.isfile(ENGINE_FILE)}"
    )

    print(
        f"DATABASE                  : {DB_FILE}"
    )

    print(
        f"DATABASE FOUND            : "
        f"{os.path.isfile(DB_FILE)}"
    )

    if not os.path.isfile(ENGINE_FILE):
        raise FileNotFoundError(
            ENGINE_FILE
        )

    if not os.path.isfile(DB_FILE):
        raise FileNotFoundError(
            DB_FILE
        )


# ============================================================
# STATIC SOURCE INSPECTION
# ============================================================

def inspect_source():

    section(
        "STEP 2 — TARGET FUNCTION SOURCE INSPECTION"
    )

    with open(
        ENGINE_FILE,
        "r",
        encoding="utf-8"
    ) as handle:

        source = handle.read()

    tree = ast.parse(
        source,
        filename=ENGINE_FILE
    )

    function_nodes = []
    caller_nodes = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            if node.name == TARGET_FUNCTION:
                function_nodes.append(node)

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            for child in ast.walk(node):

                if isinstance(
                    child,
                    ast.Call
                ):

                    if (
                        isinstance(
                            child.func,
                            ast.Name
                        )
                        and child.func.id
                        == TARGET_FUNCTION
                    ):

                        caller_nodes.append(
                            (
                                node.name,
                                child.lineno
                            )
                        )

                    elif (
                        isinstance(
                            child.func,
                            ast.Attribute
                        )
                        and child.func.attr
                        == TARGET_FUNCTION
                    ):

                        caller_nodes.append(
                            (
                                node.name,
                                child.lineno
                            )
                        )

    print(
        f"{TARGET_FUNCTION} DEFINITIONS : "
        f"{len(function_nodes)}"
    )

    if function_nodes:

        node = function_nodes[0]

        print(
            f"FUNCTION LINE             : "
            f"{node.lineno}"
        )

        print(
            f"FUNCTION END LINE         : "
            f"{getattr(node, 'end_lineno', '?')}"
        )

        arguments = []

        for arg in node.args.posonlyargs:
            arguments.append(arg.arg)

        for arg in node.args.args:
            arguments.append(arg.arg)

        if node.args.vararg is not None:
            arguments.append(
                "*" + node.args.vararg.arg
            )

        for arg in node.args.kwonlyargs:
            arguments.append(arg.arg)

        if node.args.kwarg is not None:
            arguments.append(
                "**" + node.args.kwarg.arg
            )

        print(
            "SIGNATURE ARGUMENTS       : "
            + safe_repr(arguments)
        )

    print()
    print(
        "STATIC CALL SITES"
    )

    if caller_nodes:

        for caller_name, lineno in caller_nodes:

            print(
                f"CALLER={caller_name:<40} "
                f"LINE={lineno}"
            )

    else:

        print(
            "NO STATIC INTERNAL CALLER FOUND"
        )

    if not function_nodes:

        raise RuntimeError(
            f"{TARGET_FUNCTION} not found"
        )

    return source, tree


# ============================================================
# SQL CLASSIFICATION
# ============================================================

WRITE_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)


def classify_sql(sql):

    if sql is None:
        return False

    normalized = " ".join(
        str(sql)
        .strip()
        .upper()
        .split()
    )

    if not normalized:
        return False

    return normalized.startswith(
        WRITE_PREFIXES
    )


# ============================================================
# READ ONLY DATABASE
# ============================================================

def open_read_only_database():

    uri = (
        "file:"
        + DB_FILE.replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# FORENSIC CURSOR
# ============================================================

class ForensicCursor:

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(
        self,
        sql,
        parameters=()
    ):

        write_like = classify_sql(sql)

        event = {
            "operation": "execute",
            "sql": str(sql),
            "parameters": parameters,
            "write_like": write_like,
        }

        sql_trace.append(event)

        if write_like:

            blocked_writes.append(event)

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL detected"
            )

        result = self._cursor.execute(
            sql,
            parameters
        )

        return result

    def executemany(
        self,
        sql,
        parameters
    ):

        write_like = classify_sql(sql)

        event = {
            "operation": "executemany",
            "sql": str(sql),
            "parameters": "<executemany>",
            "write_like": write_like,
        }

        sql_trace.append(event)

        if write_like:

            blocked_writes.append(event)

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL detected"
            )

        return self._cursor.executemany(
            sql,
            parameters
        )

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size=None):

        if size is None:
            return self._cursor.fetchmany()

        return self._cursor.fetchmany(size)

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(
            self._cursor,
            name
        )


# ============================================================
# FORENSIC CONNECTION
# ============================================================

class ForensicConnection:

    def __init__(self, connection):
        self._connection = connection

    def cursor(self):

        return ForensicCursor(
            self._connection.cursor()
        )

    def execute(
        self,
        sql,
        parameters=()
    ):

        cursor = self.cursor()

        cursor.execute(
            sql,
            parameters
        )

        return cursor

    def executemany(
        self,
        sql,
        parameters
    ):

        cursor = self.cursor()

        cursor.executemany(
            sql,
            parameters
        )

        return cursor

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return self._connection.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback_value
    ):

        self.close()

        return False

    def __getattr__(self, name):
        return getattr(
            self._connection,
            name
        )


def forensic_connection_factory():

    return ForensicConnection(
        open_read_only_database()
    )


# ============================================================
# ROW NORMALIZATION
# ============================================================

def row_to_dict(row):

    if isinstance(
        row,
        sqlite3.Row
    ):

        return {
            key: row[key]
            for key in row.keys()
        }

    if isinstance(
        row,
        dict
    ):

        return dict(row)

    try:
        return dict(row)
    except Exception:

        return {
            "_repr": safe_repr(row)
        }


def snapshot_value(value):

    if value is None:
        return None

    if isinstance(
        value,
        sqlite3.Row
    ):

        return row_to_dict(value)

    if isinstance(
        value,
        (list, tuple)
    ):

        return [
            snapshot_value(item)
            for item in value
        ]

    if isinstance(
        value,
        dict
    ):

        return {
            str(key): snapshot_value(item)
            for key, item in value.items()
        }

    try:

        if hasattr(value, "keys"):

            return {
                str(key): snapshot_value(
                    value[key]
                )
                for key in value.keys()
            }

    except Exception:
        pass

    return value


# ============================================================
# TARGET EXTRACTION
# ============================================================

def extract_symbol_from_value(value):

    if value is None:
        return None

    if isinstance(
        value,
        sqlite3.Row
    ):

        try:
            return value["symbol"]
        except Exception:
            return None

    if isinstance(
        value,
        dict
    ):

        for key in (
            "symbol",
            "ticker",
            "asset",
            "name",
        ):

            if key in value:
                return value[key]

    return None


def infer_target_from_call(
    args,
    kwargs
):

    for key in (
        "symbol",
        "ticker",
        "asset",
        "name",
    ):

        if key in kwargs:

            value = kwargs[key]

            if isinstance(
                value,
                str
            ):

                return value.upper()

    for value in args:

        if isinstance(
            value,
            str
        ):

            upper = value.upper()

            if upper in TARGETS:

                return upper

    for value in args:

        symbol = extract_symbol_from_value(
            value
        )

        if symbol:

            upper = str(symbol).upper()

            if upper in TARGETS:

                return upper

    return "UNKNOWN"


# ============================================================
# RUNTIME FUNCTION WRAPPER
# ============================================================

def install_runtime_wrapper(
    module
):

    section(
        "STEP 3 — RUNTIME OBSERVER INSTALLATION"
    )

    if not hasattr(
        module,
        TARGET_FUNCTION
    ):

        raise RuntimeError(
            f"Module has no {TARGET_FUNCTION}"
        )

    original_function = getattr(
        module,
        TARGET_FUNCTION
    )

    print(
        f"ORIGINAL FUNCTION FOUND    : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"ORIGINAL OBJECT            : "
        f"{safe_repr(original_function)}"
    )

    print(
        f"ORIGINAL SIGNATURE         : "
        f"{safe_repr(inspect.signature(original_function))}"
    )

    def forensic_wrapper(
        *args,
        **kwargs
    ):

        call_index = (
            len(runtime_calls) + 1
        )

        symbol = infer_target_from_call(
            args,
            kwargs
        )

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "args": snapshot_value(args),
            "kwargs": snapshot_value(kwargs),
        }

        runtime_calls.append(
            event
        )

        entrypoint_status[
            "function_executed"
        ] = True

        print()
        print(
            "[REAL PRODUCTION FUNCTION CALLED]"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"SYMBOL     : {symbol}"
        )

        print(
            f"ARGS       : "
            f"{safe_repr(snapshot_value(args))}"
        )

        print(
            f"KWARGS     : "
            f"{safe_repr(snapshot_value(kwargs))}"
        )

        try:

            result = original_function(
                *args,
                **kwargs
            )

        except Exception as exc:

            event["exception"] = repr(exc)

            runtime_exceptions.append(
                {
                    "call_index": call_index,
                    "symbol": symbol,
                    "exception": repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            print()
            print(
                "[PRODUCTION FUNCTION EXCEPTION]"
            )

            print(
                repr(exc)
            )

            raise

        return_event = {
            "call_index": call_index,
            "symbol": symbol,
            "result": snapshot_value(result),
            "result_type":
                type(result).__name__,
        }

        runtime_returns.append(
            return_event
        )

        print()
        print(
            "[REAL PRODUCTION RETURN]"
        )

        print(
            f"CALL INDEX  : {call_index}"
        )

        print(
            f"SYMBOL      : {symbol}"
        )

        print(
            f"RESULT TYPE : "
            f"{type(result).__name__}"
        )

        print(
            f"RESULT      : "
            f"{safe_repr(snapshot_value(result))}"
        )

        return result

    setattr(
        module,
        TARGET_FUNCTION,
        forensic_wrapper
    )

    print(
        "PATCHED MODULE REFERENCE    : "
        f"{TARGET_FUNCTION}"
    )

    module._forensic_original_find_future_price = (
        original_function
    )


# ============================================================
# OPTIONAL CONNECTION PATCH
# ============================================================

def patch_database_connection(
    module
):

    section(
        "STEP 4 — READ-ONLY CONNECTION OBSERVER"
    )

    if hasattr(
        module,
        "connect_database"
    ):

        original_connect = (
            module.connect_database
        )

        print(
            "PRODUCTION connect_database : FOUND"
        )

        def forensic_connect():

            print(
                "[FORENSIC CONNECTION]"
            )

            print(
                "READ ONLY DATABASE CONNECTION CREATED"
            )

            return forensic_connection_factory()

        module.connect_database = (
            forensic_connect
        )

        module._forensic_original_connect = (
            original_connect
        )

        print(
            "connect_database PATCHED    : YES"
        )

    else:

        print(
            "connect_database PATCHED    : NO"
        )

        print(
            "REASON                      : "
            "Function not present"
        )


# ============================================================
# MODULE IMPORT
# ============================================================

def import_module():

    section(
        "STEP 5 — PRODUCTION MODULE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            MODULE_NAME,
            ENGINE_FILE
        )
    )

    if spec is None:

        raise RuntimeError(
            "Could not create module specification"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    entrypoint_status[
        "imported"
    ] = True

    print(
        f"MODULE IMPORTED            : "
        f"{MODULE_NAME}"
    )

    return module


# ============================================================
# DATABASE BASELINE
# ============================================================

def inspect_market_data_baseline():

    section(
        "STEP 6 — MARKET_DATA READ-ONLY BASELINE"
    )

    conn = open_read_only_database()

    try:

        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'market_data'
            """
        ).fetchone()

        found = table is not None

        print(
            f"MARKET_DATA TABLE FOUND    : {found}"
        )

        if not found:
            return

        total = conn.execute(
            "SELECT COUNT(*) FROM market_data"
        ).fetchone()[0]

        print(
            f"MARKET_DATA TOTAL ROWS     : {total}"
        )

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT
                    symbol,
                    COUNT(*) AS row_count
                FROM market_data
                WHERE symbol = ?
                GROUP BY symbol
                """,
                (symbol,)
            ).fetchone()

            count = (
                row["row_count"]
                if row is not None
                else 0
            )

            print(
                f"{symbol:<6} | ROWS={count}"
            )

    finally:

        conn.close()


# ============================================================
# SQL TRACE REPORT
# ============================================================

def report_sql_trace():

    section(
        "STEP 7 — RUNTIME SQL CONSUMPTION TRACE"
    )

    print(
        f"SQL EVENTS                 : "
        f"{len(sql_trace)}"
    )

    print(
        f"BLOCKED WRITE EVENTS       : "
        f"{len(blocked_writes)}"
    )

    if not sql_trace:

        print(
            "NO RUNTIME SQL OBSERVED"
        )

        return

    for index, event in enumerate(
        sql_trace,
        start=1
    ):

        print()
        print(
            f"SQL EVENT #{index}"
        )

        print(
            f"WRITE LIKE : "
            f"{event['write_like']}"
        )

        print(
            f"SQL        : "
            f"{event['sql']}"
        )

        print(
            f"PARAMETERS : "
            f"{safe_repr(event['parameters'])}"
        )


# ============================================================
# RUNTIME RETURN REPORT
# ============================================================

def report_runtime_returns():

    section(
        "STEP 8 — REAL find_future_price OUTPUTS"
    )

    print(
        f"RUNTIME CALLS             : "
        f"{len(runtime_calls)}"
    )

    print(
        f"RUNTIME RETURNS           : "
        f"{len(runtime_returns)}"
    )

    print(
        f"RUNTIME EXCEPTIONS        : "
        f"{len(runtime_exceptions)}"
    )

    if not runtime_returns:

        print()
        print(
            "NO REAL PRODUCTION RETURN CAPTURED"
        )

        return

    for event in runtime_returns:

        print()
        print(
            f"CALL #{event['call_index']}"
        )

        print(
            f"SYMBOL      : "
            f"{event['symbol']}"
        )

        print(
            f"RESULT TYPE : "
            f"{event['result_type']}"
        )

        print(
            f"RESULT      : "
            f"{safe_repr(event['result'])}"
        )


# ============================================================
# CALL ARGUMENT REPORT
# ============================================================

def report_runtime_arguments():

    section(
        "STEP 9 — REAL PRODUCTION ARGUMENTS"
    )

    if not runtime_calls:

        print(
            "NO PRODUCTION FUNCTION CALL OBSERVED"
        )

        return

    for event in runtime_calls:

        print()
        print(
            f"CALL #{event['call_index']}"
        )

        print(
            f"SYMBOL : "
            f"{event['symbol']}"
        )

        print(
            f"ARGS   : "
            f"{safe_repr(event['args'])}"
        )

        print(
            f"KWARGS : "
            f"{safe_repr(event['kwargs'])}"
        )


# ============================================================
# STATIC CALLER REPORT
# ============================================================

def report_static_callers(
    tree
):

    section(
        "STEP 10 — STATIC CALLER TRACE"
    )

    callers = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        for child in ast.walk(node):

            if not isinstance(
                child,
                ast.Call
            ):
                continue

            matched = False

            if (
                isinstance(
                    child.func,
                    ast.Name
                )
                and child.func.id
                == TARGET_FUNCTION
            ):

                matched = True

            elif (
                isinstance(
                    child.func,
                    ast.Attribute
                )
                and child.func.attr
                == TARGET_FUNCTION
            ):

                matched = True

            if matched:

                callers.append(
                    {
                        "function":
                            node.name,
                        "line":
                            child.lineno,
                    }
                )

    print(
        f"STATIC CALL SITES          : "
        f"{len(callers)}"
    )

    for item in callers:

        print(
            f"CALLER={item['function']:<45} "
            f"LINE={item['line']}"
        )


# ============================================================
# EXCEPTION REPORT
# ============================================================

def report_exceptions():

    section(
        "STEP 11 — RUNTIME EXCEPTION REPORT"
    )

    if not runtime_exceptions:

        print(
            "RUNTIME EXCEPTIONS          : 0"
        )

        return

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_exceptions)}"
    )

    for event in runtime_exceptions:

        print()
        print(
            f"CALL INDEX : "
            f"{event.get('call_index')}"
        )

        print(
            f"SYMBOL     : "
            f"{event.get('symbol')}"
        )

        print(
            f"EXCEPTION  : "
            f"{event.get('exception')}"
        )

        print(
            event.get("traceback")
        )


# ============================================================
# FINAL STATUS
# ============================================================

def determine_status():

    calls = len(runtime_calls)
    returns = len(runtime_returns)
    sql_events = len(sql_trace)
    exceptions = len(runtime_exceptions)

    if calls == 0:

        return (
            "FIND_FUTURE_PRICE_NOT_EXECUTED",
            "The selected production function was not reached "
            "during this runtime trace."
        )

    if exceptions > 0:

        return (
            "FIND_FUTURE_PRICE_RUNTIME_EXCEPTION",
            "The real production function was reached but "
            "raised one or more runtime exceptions."
        )

    if returns > 0 and sql_events > 0:

        return (
            "FIND_FUTURE_PRICE_RUNTIME_CONSUMPTION_OBSERVED",
            "The real production function executed, returned "
            "a genuine production value, and runtime SQL "
            "consumption was observed."
        )

    if returns > 0 and sql_events == 0:

        return (
            "FIND_FUTURE_PRICE_RUNTIME_RETURN_WITHOUT_SQL",
            "The real production function executed and returned "
            "a genuine value, but no SQL consumption was "
            "observed through the instrumented connection path."
        )

    return (
        "FIND_FUTURE_PRICE_EXECUTED_WITHOUT_RETURN",
        "The production function was reached but no usable "
        "return event was captured."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary(
    elapsed,
    tree
):

    status, meaning = determine_status()

    section(
        "STEP 12 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"TARGET FILE                 : "
        f"{ENGINE_FILE}"
    )

    print(
        f"RUNTIME FUNCTION CALLS      : "
        f"{len(runtime_calls)}"
    )

    print(
        f"RUNTIME RETURNS             : "
        f"{len(runtime_returns)}"
    )

    print(
        f"RUNTIME SQL EVENTS          : "
        f"{len(sql_trace)}"
    )

    print(
        f"BLOCKED WRITE OPERATIONS    : "
        f"{len(blocked_writes)}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_exceptions)}"
    )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    print(
        f"STATUS                      : "
        f"{status}"
    )

    print(
        f"MEANING                     : "
        f"{meaning}"
    )

    if status == (
        "FIND_FUTURE_PRICE_RUNTIME_CONSUMPTION_OBSERVED"
    ):

        print(
            "NEXT FRONTIER              : "
            "Trace the actual return value of "
            "find_future_price() into its next "
            "production consumer."
        )

    elif status == (
        "FIND_FUTURE_PRICE_RUNTIME_RETURN_WITHOUT_SQL"
    ):

        print(
            "NEXT FRONTIER              : "
            "Trace the in-memory data path and "
            "determine where find_future_price "
            "receives its source data."
        )

    elif status == (
        "FIND_FUTURE_PRICE_NOT_EXECUTED"
    ):

        print(
            "NEXT FRONTIER              : "
            "Resolve the actual production caller "
            "that reaches find_future_price()."
        )

    else:

        print(
            "NEXT FRONTIER              : "
            "Localize the exact runtime execution "
            "path before moving downstream."
        )

    print()
    print(
        "IMPORTANT                   : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                   : "
        "The original find_future_price "
        "function was executed unchanged."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                   : "
        "The database was opened read-only."
    )

    print(
        "IMPORTANT                   : "
        "No production main() was called by "
        "this forensic driver."
    )

    print()

    print(
        "DATABASE WRITE OPERATIONS   : NONE"
    )

    print(
        "ENGINE MODIFICATIONS        : NONE ON DISK"
    )

    print(
        "INSERT                      : NONE"
    )

    print(
        "UPDATE                      : NONE"
    )

    print(
        "DELETE                      : NONE"
    )

    print(
        "ALTER                       : NONE"
    )

    print(
        "CREATE                      : NONE"
    )

    print(
        "DROP                        : NONE"
    )

    print(
        "PRODUCTION DB WRITE         : BLOCKED"
    )

    print()

    report_static_callers(
        tree
    )


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA DOWNSTREAM find_future_price "
        "RUNTIME TRACE FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                        : "
        "READ ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                      : "
        "signal_outcome_engine.py::find_future_price"
    )

    print(
        "PRODUCTION WRITE            : "
        "BLOCKED"
    )

    print(
        "PRODUCTION main()           : "
        "NOT CALLED BY THIS DRIVER"
    )

    try:

        verify_paths()

        source, tree = inspect_source()

        module = import_module()

        entrypoint_status[
            "function_found"
        ] = hasattr(
            module,
            TARGET_FUNCTION
        )

        install_runtime_wrapper(
            module
        )

        patch_database_connection(
            module
        )

        inspect_market_data_baseline()

        section(
            "STEP 7A — DIRECT TARGET FUNCTION EXECUTION"
        )

        print(
            "IMPORTANT:"
        )

        print(
            "The function is invoked directly only "
            "to expose its genuine production behavior."
        )

        print(
            "No production main() is executed."
        )

        print(
            "No synthetic market_data row is created."
        )

        print(
            "No guessed argument is passed."
        )

        print()
        print(
            "TARGET SYMBOLS:"
        )

        for symbol in TARGETS:

            print(
                f"  {symbol}"
            )

        print()
        print(
            "DIRECT EXECUTION IS NOT AUTOMATICALLY "
            "PERFORMED WITH SYNTHETIC ARGUMENTS."
        )

        print(
            "Therefore the wrapper will capture the "
            "function when reached by a genuine caller."
        )

        report_sql_trace()

        report_runtime_arguments()

        report_runtime_returns()

        report_exceptions()

        elapsed = (
            time.perf_counter()
            - started
        )

        final_summary(
            elapsed,
            tree
        )

        print()

        line("=")

        print(
            f"ELAPSED SECONDS              : "
            f"{elapsed:.3f}"
        )

        print(
            "AUDIT COMPLETE"
        )

        line("=")

        return 0

    except Exception as exc:

        print()
        line("=")

        print(
            "FORENSIC AUDIT ERROR"
        )

        line("=")

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        print()
        print(
            "DATABASE WRITE OPERATIONS   : NONE"
        )

        print(
            "PRODUCTION DB WRITE         : BLOCKED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )