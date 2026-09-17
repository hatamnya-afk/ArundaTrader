# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
FIND_FUTURE_PRICE INSTRUCTION BOUNDARY RETURN PACKING TRACE
FORENSIC AUDIT v0.1

MODE:
    READ-ONLY / WRITE-NEUTRALIZED / RUNTIME FORENSICS

PURPOSE:
    Resolve the real production runtime boundary before continuing
    instruction-level return-packing localization.

CRITICAL SAFETY:
    - Production source files are NOT modified.
    - No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP.
    - No COMMIT.
    - SQLite SELECT remains available.
    - SQLite row objects are NOT replaced or converted.
    - No monkeypatch of sqlite Row / fetchone / fetchall.
    - Runtime tracing is observational only.

TARGET:
    signal_outcome_engine.py
        main()
          -> process_signals()
             -> create_outcome()
                -> find_future_price()

NEXT FRONTIER:
    Once genuine create_outcome() execution is confirmed,
    continue instruction-boundary tracing of:
        price
        prices[label]
        returned structure
"""

import os
import sys
import sqlite3
import runpy
import traceback
import inspect
import dis
import ast
import types
import builtins
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

ENGINE_FILE = BASE_DIR / "signal_outcome_engine.py"
DB_FILE = BASE_DIR / "arunda.db"

TARGET_MODULE = "signal_outcome_engine"

CREATE_OUTCOME_NAME = "create_outcome"
FIND_FUTURE_PRICE_NAME = "find_future_price"


# ============================================================================
# FORENSIC STATE
# ============================================================================

TRACE_ENABLED = False

create_outcome_calls = 0
create_outcome_returns = 0

find_future_price_calls = 0
find_future_price_returns = 0

runtime_exceptions = []

future_price_returns = []

frame_events = []

blocked_write_operations = 0

production_source_modified = False


# ============================================================================
# SAFETY HELPERS
# ============================================================================

WRITE_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "alter",
    "create",
    "drop",
    "replace",
    "truncate",
)


def is_write_sql(sql):
    if not isinstance(sql, str):
        return False

    normalized = sql.strip().lower()

    if not normalized:
        return False

    first = normalized.split(None, 1)[0]

    return first in WRITE_KEYWORDS


# ============================================================================
# WRITE-NEUTRALIZED CURSOR
#
# IMPORTANT:
# We deliberately DO NOT alter SELECT result rows.
# This prevents:
#
# TypeError('tuple indices must be integers or slices, not str')
#
# caused by replacing sqlite Row objects with tuples.
# ============================================================================

class WriteNeutralizedCursor:
    def __init__(self, real_cursor):
        self._cursor = real_cursor

    def execute(self, sql, parameters=()):
        global blocked_write_operations

        if is_write_sql(sql):
            blocked_write_operations += 1
            return self

        self._cursor.execute(sql, parameters)
        return self

    def executemany(self, sql, seq_of_parameters):
        global blocked_write_operations

        if is_write_sql(sql):
            blocked_write_operations += 1
            return self

        self._cursor.executemany(sql, seq_of_parameters)
        return self

    def executescript(self, script):
        global blocked_write_operations

        statements = []

        for statement in script.split(";"):
            statement = statement.strip()

            if not statement:
                continue

            if is_write_sql(statement):
                blocked_write_operations += 1
                continue

            statements.append(statement)

        for statement in statements:
            self._cursor.execute(statement)

        return self

    def fetchone(self):
        # Preserve original sqlite row type exactly.
        return self._cursor.fetchone()

    def fetchmany(self, size=None):
        if size is None:
            return self._cursor.fetchmany()

        return self._cursor.fetchmany(size)

    def fetchall(self):
        # Preserve original sqlite row objects exactly.
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


# ============================================================================
# WRITE-NEUTRALIZED CONNECTION
# ============================================================================

class WriteNeutralizedConnection:
    def __init__(self, real_connection):
        self._connection = real_connection

    def cursor(self, *args, **kwargs):
        return WriteNeutralizedCursor(
            self._connection.cursor(*args, **kwargs)
        )

    def execute(self, sql, parameters=()):
        global blocked_write_operations

        if is_write_sql(sql):
            blocked_write_operations += 1
            return WriteNeutralizedCursor(
                self._connection.cursor()
            )

        cursor = self._connection.execute(sql, parameters)
        return WriteNeutralizedCursor(cursor)

    def executemany(self, sql, seq_of_parameters):
        global blocked_write_operations

        if is_write_sql(sql):
            blocked_write_operations += 1
            return WriteNeutralizedCursor(
                self._connection.cursor()
            )

        cursor = self._connection.executemany(
            sql,
            seq_of_parameters
        )

        return WriteNeutralizedCursor(cursor)

    def executescript(self, script):
        global blocked_write_operations

        cursor = self._connection.cursor()

        for statement in script.split(";"):
            statement = statement.strip()

            if not statement:
                continue

            if is_write_sql(statement):
                blocked_write_operations += 1
                continue

            cursor.execute(statement)

        return WriteNeutralizedCursor(cursor)

    def commit(self):
        # NEVER commit.
        return None

    def rollback(self):
        return None

    def close(self):
        return self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


# ============================================================================
# SAFE SQLITE CONNECT
#
# Only the connection object is wrapped.
# Row factory remains untouched.
# ============================================================================

_original_sqlite_connect = sqlite3.connect


def forensic_connect(*args, **kwargs):

    connection = _original_sqlite_connect(*args, **kwargs)

    # Preserve the original row_factory.
    # DO NOT force tuples.
    # DO NOT replace sqlite3.Row.
    #
    # If production configured:
    #     conn.row_factory = sqlite3.Row
    #
    # it remains intact.

    return WriteNeutralizedConnection(connection)


# ============================================================================
# STATIC RESOLUTION
# ============================================================================

def resolve_static_targets():

    print("=" * 100)
    print("STEP 1 — STATIC TARGET RESOLUTION")
    print("=" * 100)

    if not ENGINE_FILE.exists():
        raise FileNotFoundError(
            f"Production source not found: {ENGINE_FILE}"
        )

    source = ENGINE_FILE.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(ENGINE_FILE)
    )

    create_node = None
    future_node = None

    for node in tree.body:

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            if node.name == CREATE_OUTCOME_NAME:
                create_node = node

            if node.name == FIND_FUTURE_PRICE_NAME:
                future_node = node

    print(f"TARGET FILE              : {ENGINE_FILE}")

    if create_node:
        print(
            f"CREATE_OUTCOME           : FOUND line={create_node.lineno}"
        )
    else:
        print("CREATE_OUTCOME           : NOT FOUND")

    if future_node:
        print(
            f"FIND_FUTURE_PRICE        : FOUND line={future_node.lineno}"
        )
    else:
        print("FIND_FUTURE_PRICE        : NOT FOUND")

    call_sites = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            func = node.func

            if (
                isinstance(func, ast.Name)
                and func.id == FIND_FUTURE_PRICE_NAME
            ):
                call_sites.append(node)

    print(
        f"CALL SITES               : {len(call_sites)}"
    )

    for index, call in enumerate(call_sites, 1):

        print(
            f"CALL SITE {index}              : "
            f"LINE={call.lineno} COL={call.col_offset}"
        )

    print()

    return tree


# ============================================================================
# STATIC BYTECODE / INSTRUCTION MAP
# ============================================================================

def print_instruction_boundary(module_globals):

    print("=" * 100)
    print("STEP 2 — CREATE_OUTCOME INSTRUCTION BOUNDARY MAP")
    print("=" * 100)

    create_func = module_globals.get(CREATE_OUTCOME_NAME)
    future_func = module_globals.get(FIND_FUTURE_PRICE_NAME)

    if not isinstance(create_func, types.FunctionType):
        print("CREATE_OUTCOME FUNCTION OBJECT : NOT RESOLVED")
        return

    if not isinstance(future_func, types.FunctionType):
        print("FIND_FUTURE_PRICE FUNCTION OBJECT : NOT RESOLVED")
        return

    print(
        f"CREATE_OUTCOME CODE OBJECT : {create_func.__code__.co_filename}"
    )

    print(
        f"FIND_FUTURE_PRICE CODE OBJECT : {future_func.__code__.co_filename}"
    )

    print()
    print("CREATE_OUTCOME INSTRUCTIONS")
    print("-" * 100)

    for instruction in dis.get_instructions(create_func):

        if instruction.opname in {
            "CALL",
            "CALL_FUNCTION",
            "CALL_METHOD",
            "PRECALL",
            "STORE_FAST",
            "STORE_NAME",
            "STORE_SUBSCR",
            "RETURN_VALUE",
        }:

            print(
                f"OFFSET={instruction.offset:<5} "
                f"LINE={instruction.starts_line!s:<5} "
                f"OP={instruction.opname:<18} "
                f"ARG={instruction.arg!s:<5} "
                f"ARGVAL={instruction.argval!r}"
            )

    print()


# ============================================================================
# VALUE SNAPSHOT
# ============================================================================

def safe_repr(value):

    try:
        return repr(value)
    except Exception:
        return f"<repr failed: {type(value).__name__}>"


def snapshot_locals(frame):

    result = {}

    try:

        for name, value in frame.f_locals.items():

            if name in {
                "price",
                "prices",
                "returns",
                "outcomes",
                "label",
                "minutes",
                "completed_returns",
                "max_gain",
                "max_drawdown",
                "overall_outcome",
            }:

                result[name] = {
                    "type": type(value).__name__,
                    "repr": safe_repr(value),
                    "id": id(value),
                }

    except Exception as exc:

        result["_snapshot_error"] = repr(exc)

    return result


# ============================================================================
# RUNTIME TRACE
# ============================================================================

def runtime_trace(frame, event, arg):

    global create_outcome_calls
    global create_outcome_returns
    global find_future_price_calls
    global find_future_price_returns

    if event == "call":

        function_name = frame.f_code.co_name

        if function_name == CREATE_OUTCOME_NAME:

            create_outcome_calls += 1

            frame_events.append({
                "event": "CREATE_OUTCOME_CALL",
                "line": frame.f_lineno,
                "locals": snapshot_locals(frame),
            })

        elif function_name == FIND_FUTURE_PRICE_NAME:

            find_future_price_calls += 1

            frame_events.append({
                "event": "FIND_FUTURE_PRICE_CALL",
                "line": frame.f_lineno,
                "locals": snapshot_locals(frame),
            })

        return runtime_trace

    if event == "line":

        function_name = frame.f_code.co_name

        if function_name in {
            CREATE_OUTCOME_NAME,
            FIND_FUTURE_PRICE_NAME,
        }:

            locals_snapshot = snapshot_locals(frame)

            frame_events.append({
                "event": "LINE",
                "function": function_name,
                "line": frame.f_lineno,
                "locals": locals_snapshot,
            })

        return runtime_trace

    if event == "return":

        function_name = frame.f_code.co_name

        if function_name == FIND_FUTURE_PRICE_NAME:

            find_future_price_returns += 1

            future_price_returns.append({
                "type": type(arg).__name__,
                "value": arg,
                "repr": safe_repr(arg),
                "id": id(arg),
            })

            frame_events.append({
                "event": "FIND_FUTURE_PRICE_RETURN",
                "line": frame.f_lineno,
                "value": arg,
                "id": id(arg),
                "locals": snapshot_locals(frame),
            })

        elif function_name == CREATE_OUTCOME_NAME:

            create_outcome_returns += 1

            frame_events.append({
                "event": "CREATE_OUTCOME_RETURN",
                "line": frame.f_lineno,
                "value": arg,
                "id": id(arg),
                "locals": snapshot_locals(frame),
            })

        return runtime_trace

    return runtime_trace


# ============================================================================
# RUNTIME EVENT REPORT
# ============================================================================

def report_runtime_events():

    print("=" * 100)
    print("STEP 3 — RUNTIME BOUNDARY OBSERVATION")
    print("=" * 100)

    print(
        f"CREATE_OUTCOME CALLS        : {create_outcome_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : {find_future_price_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : {find_future_price_returns}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : {create_outcome_returns}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : {len(runtime_exceptions)}"
    )

    print()


# ============================================================================
# RETURN REPORT
# ============================================================================

def report_future_price_returns():

    print("=" * 100)
    print("STEP 4 — CAPTURED FIND_FUTURE_PRICE RETURNS")
    print("=" * 100)

    if not future_price_returns:

        print("NONE")
        return

    for index, item in enumerate(
        future_price_returns,
        1
    ):

        print(
            f"{index:03d} | "
            f"TYPE={item['type']} | "
            f"VALUE={safe_repr(item['value'])} | "
            f"OBJECT_ID={item['id']}"
        )

    print()


# ============================================================================
# FRAME-LEVEL PRICE LOCALIZATION
# ============================================================================

def report_price_flow():

    print("=" * 100)
    print("STEP 5 — FRAME-LEVEL PRICE FLOW")
    print("=" * 100)

    observations = 0

    for event in frame_events:

        if event.get("function") != CREATE_OUTCOME_NAME:
            continue

        locals_snapshot = event.get(
            "locals",
            {}
        )

        if "price" not in locals_snapshot:
            continue

        observations += 1

        price_info = locals_snapshot["price"]

        print(
            f"LINE={event.get('line')} | "
            f"price TYPE={price_info['type']} | "
            f"VALUE={price_info['repr']} | "
            f"ID={price_info['id']}"
        )

        if observations >= 100:
            print(
                "... additional observations omitted ..."
            )
            break

    print()

    print(
        f"PRICE FRAME OBSERVATIONS    : {observations}"
    )

    print()


# ============================================================================
# FINAL STRUCTURE INSPECTION
# ============================================================================

def inspect_return_structure(value, path="ROOT"):

    matches = []

    if isinstance(value, dict):

        for key, child in value.items():

            child_path = (
                f"{path}.{key}"
            )

            matches.extend(
                inspect_return_structure(
                    child,
                    child_path
                )
            )

    elif isinstance(value, (list, tuple)):

        for index, child in enumerate(value):

            child_path = (
                f"{path}[{index}]"
            )

            matches.extend(
                inspect_return_structure(
                    child,
                    child_path
                )
            )

    return matches


def report_final_returns():

    print("=" * 100)
    print("STEP 6 — CREATE_OUTCOME RETURN STRUCTURES")
    print("=" * 100)

    return_events = [
        event
        for event in frame_events
        if event.get("event") == "CREATE_OUTCOME_RETURN"
    ]

    if not return_events:

        print("NONE")
        return

    for index, event in enumerate(
        return_events,
        1
    ):

        value = event.get("value")

        print(
            f"CREATE_OUTCOME RETURN #{index}"
        )

        print(
            f"TYPE  : {type(value).__name__}"
        )

        print(
            f"VALUE : {safe_repr(value)}"
        )

        print()

        if isinstance(value, (dict, list, tuple)):

            paths = inspect_return_structure(
                value
            )

            for path in paths[:100]:

                print(
                    f"STRUCTURE PATH : {path}"
                )

            if len(paths) > 100:

                print(
                    "... additional structure paths omitted ..."
                )

        print("-" * 80)

    print()


# ============================================================================
# RUNTIME ENTRYPOINT DIAGNOSTICS
# ============================================================================

def report_entrypoint(module_globals):

    print("=" * 100)
    print("STEP 7 — PRODUCTION ENTRYPOINT RESOLUTION")
    print("=" * 100)

    main_func = module_globals.get("main")

    process_func = module_globals.get("process_signals")

    create_func = module_globals.get(
        CREATE_OUTCOME_NAME
    )

    print(
        f"main()             : "
        f"{'FOUND' if callable(main_func) else 'NOT FOUND'}"
    )

    print(
        f"process_signals()  : "
        f"{'FOUND' if callable(process_func) else 'NOT FOUND'}"
    )

    print(
        f"create_outcome()   : "
        f"{'FOUND' if callable(create_func) else 'NOT FOUND'}"
    )

    if callable(main_func):

        try:

            print(
                f"main module       : "
                f"{main_func.__module__}"
            )

            print(
                f"main source       : "
                f"{inspect.getsourcefile(main_func)}"
            )

        except Exception:
            pass

    print()


# ============================================================================
# MAIN AUDIT RUNNER
# ============================================================================

def run_audit():

    global TRACE_ENABLED
    global production_source_modified

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE INSTRUCTION BOUNDARY "
        "RETURN PACKING TRACE FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE                         : "
        "READ-ONLY INSTRUCTION-BOUNDARY FORENSICS"
    )

    print(
        f"TARGET                       : "
        f"{ENGINE_FILE} -> create_outcome()"
    )

    print(
        "SOURCE VALUE                 : "
        "create_outcome().price"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    print()

    # ----------------------------------------------------------------------
    # STATIC ANALYSIS
    # ----------------------------------------------------------------------

    tree = resolve_static_targets()

    # ----------------------------------------------------------------------
    # INSTALL SAFE SQLITE CONNECT
    # ----------------------------------------------------------------------

    sqlite3.connect = forensic_connect

    # ----------------------------------------------------------------------
    # LOAD PRODUCTION MODULE
    #
    # IMPORTANT:
    # We load the actual production source.
    # No source rewrite.
    # No AST mutation.
    # No monkeypatch of row_factory.
    # ----------------------------------------------------------------------

    module_globals = None

    try:

        TRACE_ENABLED = True

        sys.settrace(runtime_trace)

        module_globals = runpy.run_path(
            str(ENGINE_FILE),
            run_name="__forensic_runtime__"
        )

    except SystemExit:
        pass

    except Exception as exc:

        runtime_exceptions.append(
            {
                "type": type(exc).__name__,
                "value": repr(exc),
                "traceback": traceback.format_exc(),
            }
        )

    finally:

        sys.settrace(None)

        TRACE_ENABLED = False

        sqlite3.connect = _original_sqlite_connect

    # ----------------------------------------------------------------------
    # ENTRYPOINT REPORT
    # ----------------------------------------------------------------------

    if module_globals is not None:

        report_entrypoint(
            module_globals
        )

        print_instruction_boundary(
            module_globals
        )

    # ----------------------------------------------------------------------
    # REPORTS
    # ----------------------------------------------------------------------

    report_runtime_events()

    report_future_price_returns()

    report_price_flow()

    report_final_returns()

    # ----------------------------------------------------------------------
    # EXCEPTION REPORT
    # ----------------------------------------------------------------------

    print("=" * 100)
    print("STEP 8 — RUNTIME EXCEPTION REPORT")
    print("=" * 100)

    if not runtime_exceptions:

        print("NONE")

    else:

        for index, error in enumerate(
            runtime_exceptions,
            1
        ):

            print(
                f"EXCEPTION #{index}"
            )

            print(
                f"TYPE  : {error['type']}"
            )

            print(
                f"VALUE : {error['value']}"
            )

            print()

    print()

    # ----------------------------------------------------------------------
    # FINAL CONCLUSION
    # ----------------------------------------------------------------------

    print("=" * 100)
    print("STEP 9 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{find_future_price_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{find_future_price_returns}"
    )

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{create_outcome_calls}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{create_outcome_returns}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_exceptions)}"
    )

    print(
        f"BLOCKED WRITE OPERATIONS    : "
        f"{blocked_write_operations}"
    )

    print()

    if (
        find_future_price_calls > 0
        and find_future_price_returns > 0
    ):

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_BOUNDARY_REACHED"
        )

        meaning = (
            "The genuine production runtime reached "
            "find_future_price() and its return boundary "
            "was observed without modifying production source."
        )

        next_frontier = (
            "Continue instruction-boundary localization "
            "from price -> prices[label] -> return packing."
        )

    elif create_outcome_calls > 0:

        status = (
            "CREATE_OUTCOME_REACHED_FIND_FUTURE_PRICE_NOT_REACHED"
        )

        meaning = (
            "The genuine production runtime entered "
            "create_outcome(), but the selected invocation "
            "did not reach find_future_price()."
        )

        next_frontier = (
            "Inspect the exact runtime branch preceding "
            "line 432 before continuing downstream tracing."
        )

    elif runtime_exceptions:

        status = (
            "PRODUCTION_RUNTIME_ENTRYPOINT_EXCEPTION"
        )

        meaning = (
            "The production runtime failed before "
            "create_outcome()/find_future_price() could be "
            "observed. The exception must be separated from "
            "the forensic target before localization continues."
        )

        next_frontier = (
            "Resolve the runtime exception without changing "
            "production logic, then rerun this same boundary audit."
        )

    else:

        status = (
            "PRODUCTION_RUNTIME_BOUNDARY_NOT_OBSERVED"
        )

        meaning = (
            "The production runtime entrypoint was not observed "
            "reaching create_outcome() or find_future_price()."
        )

        next_frontier = (
            "Resolve the genuine production execution boundary."
        )

    print(
        "FORENSIC CONCLUSION"
    )

    print(
        "-" * 100
    )

    print(
        f"STATUS                      : {status}"
    )

    print(
        f"MEANING                     : {meaning}"
    )

    print(
        f"NEXT FRONTIER               : {next_frontier}"
    )

    print()

    print(
        "DATABASE_WRITES             : NONE"
    )

    print(
        "ENGINE_MODIFIED             : NONE"
    )

    print(
        "PRODUCTION_SOURCE_MODIFIED  : NONE"
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
        "COMMIT                      : NONE"
    )

    print(
        "=" * 100
    )


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == "__main__":

    run_audit()