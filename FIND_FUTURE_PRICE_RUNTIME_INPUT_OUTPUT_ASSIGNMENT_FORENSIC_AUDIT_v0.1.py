import ast
import os
import sqlite3
import sys
import time
import traceback
import importlib.util
from collections import defaultdict


# ============================================================
# ARUNDA
# FIND FUTURE PRICE
# RUNTIME INPUT / OUTPUT / ASSIGNMENT FORENSIC AUDIT v0.2
# ============================================================
#
# PURPOSE
# -------
# Trace the real production execution of:
#
#     signal_outcome_engine.py
#          |
#          v
#     create_outcome()
#          |
#          v
#     find_future_price()
#          |
#          v
#     actual production return
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
# Production functions are executed only through the selected
# production call path.
#
# Database is opened read-only.
#
# No production database write is permitted.
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
    "arunda_signal_outcome_find_future_price_forensic_v02"
)

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# FORENSIC STATE
# ============================================================

find_calls = []
find_returns = []
create_calls = []
create_returns = []

runtime_exceptions = []

sql_trace = []
blocked_writes = []

entrypoint_status = {
    "executed": False,
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


def sub_section(title):
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
        "STEP 1 — PATH SAFETY RESOLUTION"
    )

    print(
        f"PROJECT PATH        : {PROJECT_DIR}"
    )

    print(
        f"TARGET ENGINE       : {ENGINE_FILE}"
    )

    print(
        f"ENGINE FOUND        : {os.path.isfile(ENGINE_FILE)}"
    )

    print(
        f"DATABASE            : {DB_FILE}"
    )

    print(
        f"DATABASE FOUND      : {os.path.isfile(DB_FILE)}"
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
        "STEP 2 — PRODUCTION SOURCE INSPECTION"
    )

    with open(
        ENGINE_FILE,
        "r",
        encoding="utf-8-sig"
    ) as handle:

        source = handle.read()

    tree = ast.parse(
        source,
        filename=ENGINE_FILE
    )

    functions = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            functions[node.name] = node

    print(
        f"FUNCTIONS DISCOVERED : "
        f"{len(functions)}"
    )

    for target in [
        "find_future_price",
        "create_outcome",
        "process_signals",
        "main",
    ]:

        node = functions.get(target)

        if node is None:

            print(
                f"{target:<22} : NOT_FOUND"
            )

        else:

            print(
                f"{target:<22} : "
                f"FOUND LINE={node.lineno}"
            )

    if "find_future_price" not in functions:

        raise RuntimeError(
            "find_future_price() not found"
        )

    if "create_outcome" not in functions:

        raise RuntimeError(
            "create_outcome() not found"
        )

    return tree


# ============================================================
# READ ONLY SQLITE
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
            "sql": str(sql),
            "parameters": safe_repr(parameters),
            "write_like": write_like,
        }

        sql_trace.append(event)

        if write_like:

            blocked_writes.append(event)

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL blocked"
            )

        return self._cursor.execute(
            sql,
            parameters
        )

    def executemany(
        self,
        sql,
        parameters
    ):

        write_like = classify_sql(sql)

        event = {
            "sql": str(sql),
            "parameters": "<executemany>",
            "write_like": write_like,
        }

        sql_trace.append(event)

        if write_like:

            blocked_writes.append(event)

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL blocked"
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

        return self._cursor.fetchmany(
            size
        )

    def fetchall(self):

        return self._cursor.fetchall()

    def __iter__(self):

        return iter(
            self._cursor
        )

    def __getattr__(self, name):

        return getattr(
            self._cursor,
            name
        )


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


def forensic_database_connection():

    uri = (
        "file:"
        + DB_FILE.replace("\\", "/")
        + "?mode=ro"
    )

    real_connection = sqlite3.connect(
        uri,
        uri=True
    )

    real_connection.row_factory = sqlite3.Row

    return ForensicConnection(
        real_connection
    )


# ============================================================
# GENERIC VALUE SNAPSHOT
# ============================================================

def snapshot_value(value):

    if value is None:

        return None

    if isinstance(value, sqlite3.Row):

        return {
            key: value[key]
            for key in value.keys()
        }

    if isinstance(value, dict):

        return {
            key: value[key]
            for key in value
        }

    if isinstance(value, (list, tuple)):

        return [
            snapshot_value(item)
            for item in value
        ]

    try:

        return dict(value)

    except Exception:

        return value


# ============================================================
# SYMBOL EXTRACTION
# ============================================================

def extract_symbol(args, kwargs):

    if "symbol" in kwargs:

        return kwargs["symbol"]

    for value in args:

        if isinstance(value, str):

            upper = value.upper()

            if upper in TARGETS:

                return upper

    return None


# ============================================================
# PRODUCTION MODULE IMPORT
# ============================================================

def import_production_module():

    section(
        "STEP 3 — PRODUCTION MODULE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            MODULE_NAME,
            ENGINE_FILE
        )
    )

    if spec is None:

        raise RuntimeError(
            "Could not create module spec"
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

    print(
        f"MODULE IMPORTED : {MODULE_NAME}"
    )

    return module


# ============================================================
# INSTALL DATABASE SAFETY
# ============================================================

def install_database_safety(module):

    if not hasattr(
        module,
        "connect_database"
    ):

        print(
            "[DATABASE] "
            "connect_database() not found"
        )

        return

    original_connect = (
        module.connect_database
    )

    def forensic_connect():

        print(
            "[DATABASE] "
            "READ-ONLY CONNECTION REQUESTED"
        )

        return forensic_database_connection()

    module.connect_database = (
        forensic_connect
    )

    module._forensic_original_connect = (
        original_connect
    )

    print(
        "[PATCHED] module.connect_database"
    )


# ============================================================
# RUNTIME OBSERVER INSTALLATION
# ============================================================

def install_runtime_observers(module):

    section(
        "STEP 4 — RUNTIME OBSERVER INSTALLATION"
    )

    if not hasattr(
        module,
        "find_future_price"
    ):

        raise RuntimeError(
            "find_future_price() missing"
        )

    original_find = (
        module.find_future_price
    )

    original_create = (
        getattr(
            module,
            "create_outcome",
            None
        )
    )

    original_save = (
        getattr(
            module,
            "save_outcome",
            None
        )
    )

    print(
        "ORIGINAL find_future_price : FOUND"
    )

    print(
        "ORIGINAL create_outcome     : "
        + (
            "FOUND"
            if original_create
            else "NOT_FOUND"
        )
    )

    print(
        "ORIGINAL save_outcome       : "
        + (
            "FOUND"
            if original_save
            else "NOT_FOUND"
        )
    )

    # --------------------------------------------------------
    # find_future_price wrapper
    # --------------------------------------------------------

    def forensic_find_future_price(
        *args,
        **kwargs
    ):

        call_index = (
            len(find_calls) + 1
        )

        symbol = extract_symbol(
            args,
            kwargs
        )

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "args": snapshot_value(args),
            "kwargs": snapshot_value(kwargs),
        }

        find_calls.append(
            event
        )

        print()
        print(
            "[FIND_FUTURE_PRICE ENTER]"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"SYMBOL     : {symbol}"
        )

        print(
            f"ARGS       : {safe_repr(args)}"
        )

        print(
            f"KWARGS     : {safe_repr(kwargs)}"
        )

        try:

            result = original_find(
                *args,
                **kwargs
            )

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        "find_future_price",
                    "symbol":
                        symbol,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            print(
                "[FIND_FUTURE_PRICE EXCEPTION]"
            )

            print(
                repr(exc)
            )

            raise

        return_event = {
            "call_index": call_index,
            "symbol": symbol,
            "result": snapshot_value(result),
            "result_type": type(result).__name__,
        }

        find_returns.append(
            return_event
        )

        print(
            "[FIND_FUTURE_PRICE RETURN]"
        )

        print(
            f"RESULT TYPE : "
            f"{type(result).__name__}"
        )

        print(
            f"RESULT      : "
            f"{safe_repr(result)}"
        )

        return result

    module.find_future_price = (
        forensic_find_future_price
    )

    # --------------------------------------------------------
    # create_outcome wrapper
    # --------------------------------------------------------

    if original_create is not None:

        def forensic_create_outcome(
            *args,
            **kwargs
        ):

            call_index = (
                len(create_calls) + 1
            )

            symbol = extract_symbol(
                args,
                kwargs
            )

            event = {
                "call_index": call_index,
                "symbol": symbol,
                "args": snapshot_value(args),
                "kwargs": snapshot_value(kwargs),
            }

            create_calls.append(
                event
            )

            print()
            print(
                "[CREATE_OUTCOME ENTER]"
            )

            print(
                f"CALL INDEX : {call_index}"
            )

            print(
                f"SYMBOL     : {symbol}"
            )

            print(
                f"ARGS       : {safe_repr(args)}"
            )

            print(
                f"KWARGS     : {safe_repr(kwargs)}"
            )

            try:

                result = original_create(
                    *args,
                    **kwargs
                )

            except Exception as exc:

                runtime_exceptions.append(
                    {
                        "stage":
                            "create_outcome",
                        "symbol":
                            symbol,
                        "exception":
                            repr(exc),
                        "traceback":
                            traceback.format_exc(),
                    }
                )

                print(
                    "[CREATE_OUTCOME EXCEPTION]"
                )

                print(
                    repr(exc)
                )

                raise

            create_returns.append(
                {
                    "call_index":
                        call_index,
                    "symbol":
                        symbol,
                    "result":
                        snapshot_value(result),
                    "result_type":
                        type(result).__name__,
                }
            )

            print(
                "[CREATE_OUTCOME RETURN]"
            )

            print(
                f"RESULT TYPE : "
                f"{type(result).__name__}"
            )

            print(
                f"RESULT      : "
                f"{safe_repr(result)}"
            )

            return result

        module.create_outcome = (
            forensic_create_outcome
        )

    # --------------------------------------------------------
    # Disable persistence if present
    # --------------------------------------------------------

    if original_save is not None:

        def forensic_save_outcome(
            *args,
            **kwargs
        ):

            print()
            print(
                "[SAVE_OUTCOME OBSERVED — "
                "WRITE SUPPRESSED]"
            )

            print(
                f"ARGS   : {safe_repr(args)}"
            )

            print(
                f"KWARGS : {safe_repr(kwargs)}"
            )

            return False

        module.save_outcome = (
            forensic_save_outcome
        )

    print(
        "[PATCHED] find_future_price"
    )

    if original_create is not None:

        print(
            "[PATCHED] create_outcome"
        )

    if original_save is not None:

        print(
            "[PATCHED] save_outcome"
        )


# ============================================================
# TARGET DATABASE RESOLUTION
# ============================================================

def resolve_targets():

    section(
        "STEP 5 — TARGET DATABASE RESOLUTION"
    )

    conn = forensic_database_connection()

    resolved = []

    try:

        for symbol in TARGETS:

            try:

                row = conn.execute(
                    """
                    SELECT
                        symbol,
                        COUNT(*) AS row_count
                    FROM market_data
                    WHERE symbol = ?
                    GROUP BY symbol
                    LIMIT 1
                    """,
                    (symbol,)
                ).fetchone()

            except Exception:

                row = None

            if row is None:

                print(
                    f"{symbol:<6} : NOT_FOUND"
                )

                continue

            resolved.append(
                symbol
            )

            print(
                f"{symbol:<6} : "
                f"ROWS={row['row_count']}"
            )

    finally:

        conn.close()

    return resolved


# ============================================================
# SAFE RUNTIME INVOCATION
# ============================================================

def execute_runtime(module):

    section(
        "STEP 6 — PRODUCTION RUNTIME TRACE"
    )

    if not hasattr(
        module,
        "main"
    ):

        print(
            "PRODUCTION main() : NOT_FOUND"
        )

        return None

    print(
        "ENTRYPOINT : signal_outcome_engine.main()"
    )

    print(
        "MODE       : READ-ONLY FORENSIC"
    )

    print(
        "WRITE      : BLOCKED"
    )

    entrypoint_status[
        "executed"
    ] = True

    try:

        result = module.main()

        print()
        print(
            "[PRODUCTION MAIN RETURN]"
        )

        print(
            safe_repr(result)
        )

        return result

    except Exception as exc:

        entrypoint_status[
            "exception"
        ] = repr(exc)

        runtime_exceptions.append(
            {
                "stage": "main",
                "exception": repr(exc),
                "traceback":
                    traceback.format_exc(),
            }
        )

        print()
        print(
            "[PRODUCTION MAIN EXCEPTION]"
        )

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        return None


# ============================================================
# RUNTIME INVENTORY
# ============================================================

def runtime_inventory():

    section(
        "STEP 7 — RUNTIME TRACE INVENTORY"
    )

    print(
        f"CREATE_OUTCOME CALLS       : "
        f"{len(create_calls)}"
    )

    print(
        f"CREATE_OUTCOME RETURNS     : "
        f"{len(create_returns)}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS    : "
        f"{len(find_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS  : "
        f"{len(find_returns)}"
    )

    print(
        f"SQL EVENTS                 : "
        f"{len(sql_trace)}"
    )

    print(
        f"BLOCKED WRITES             : "
        f"{len(blocked_writes)}"
    )

    print(
        f"RUNTIME EXCEPTIONS         : "
        f"{len(runtime_exceptions)}"
    )

    print()

    print(
        "TARGET DISTRIBUTION"
    )

    for symbol in TARGETS:

        create_count = sum(
            1
            for event in create_calls
            if event.get("symbol") == symbol
        )

        find_count = sum(
            1
            for event in find_calls
            if event.get("symbol") == symbol
        )

        return_count = sum(
            1
            for event in find_returns
            if event.get("symbol") == symbol
        )

        print(
            f"{symbol:<6} | "
            f"CREATE={create_count:<3} | "
            f"FIND_FUTURE_PRICE={find_count:<3} | "
            f"RETURNS={return_count:<3}"
        )


# ============================================================
# DETAILED TARGET REPORT
# ============================================================

def report_target(symbol):

    section(
        f"TARGET : {symbol}"
    )

    target_calls = [
        event
        for event in find_calls
        if event.get("symbol") == symbol
    ]

    target_returns = [
        event
        for event in find_returns
        if event.get("symbol") == symbol
    ]

    print(
        f"FIND_FUTURE_PRICE CALLS   : "
        f"{len(target_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS : "
        f"{len(target_returns)}"
    )

    if target_calls:

        print()
        print(
            "INPUT OBSERVATION"
        )

        for event in target_calls[-3:]:

            print(
                f"CALL INDEX : "
                f"{event['call_index']}"
            )

            print(
                f"ARGS       : "
                f"{safe_repr(event['args'])}"
            )

            print(
                f"KWARGS     : "
                f"{safe_repr(event['kwargs'])}"
            )

    if target_returns:

        print()
        print(
            "OUTPUT OBSERVATION"
        )

        for event in target_returns[-3:]:

            print(
                f"CALL INDEX : "
                f"{event['call_index']}"
            )

            print(
                f"TYPE       : "
                f"{event['result_type']}"
            )

            print(
                f"RESULT     : "
                f"{safe_repr(event['result'])}"
            )


# ============================================================
# FINAL STATUS
# ============================================================

def determine_status():

    if len(find_calls) == 0:

        return (
            "FIND_FUTURE_PRICE_NOT_EXECUTED",
            "The production runtime did not reach find_future_price().",
            "Resolve or trace the production caller path again."
        )

    if len(find_returns) == 0:

        return (
            "FIND_FUTURE_PRICE_EXECUTED_NO_RETURN",
            "find_future_price() was reached but no usable return was captured.",
            "Trace the exception or downstream control path."
        )

    if len(find_returns) < len(find_calls):

        return (
            "FIND_FUTURE_PRICE_PARTIAL_OUTPUT",
            "find_future_price() was reached but not all calls produced returns.",
            "Localize the missing return path."
        )

    return (
        "FIND_FUTURE_PRICE_RUNTIME_INPUT_OUTPUT_CAPTURED",
        "The genuine production find_future_price() executed and its actual inputs and returns were captured.",
        "Trace the downstream assignment of the returned future price."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary(resolved_targets):

    status, meaning, next_frontier = (
        determine_status()
    )

    section(
        "STEP 8 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"TARGET FUNCTION             : "
        f"find_future_price"
    )

    print(
        f"TARGET FILE                 : "
        f"{ENGINE_FILE}"
    )

    print(
        f"TARGETS FOUND               : "
        f"{len(resolved_targets)}"
    )

    print(
        f"RUNTIME FUNCTION CALLS      : "
        f"{len(find_calls)}"
    )

    print(
        f"RUNTIME RETURNS             : "
        f"{len(find_returns)}"
    )

    print(
        f"CREATE_OUTCOME CALLS       : "
        f"{len(create_calls)}"
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

    print(
        f"NEXT FRONTIER              : "
        f"{next_frontier}"
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
        "No production main() was modified."
    )

    print(
        "IMPORTANT                   : "
        "Database access was read-only."
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


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA FIND FUTURE PRICE "
        "RUNTIME INPUT OUTPUT ASSIGNMENT "
        "FORENSIC AUDIT v0.2"
    )

    print(
        "MODE                     : READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "DATABASE WRITE           : BLOCKED"
    )

    print(
        "ENGINE WRITE             : NONE"
    )

    print(
        "TARGET                   : "
        "signal_outcome_engine.py -> "
        "find_future_price()"
    )

    try:

        verify_paths()

        inspect_source()

        resolved_targets = (
            resolve_targets()
        )

        module = (
            import_production_module()
        )

        install_database_safety(
            module
        )

        install_runtime_observers(
            module
        )

        execute_runtime(
            module
        )

        runtime_inventory()

        for symbol in resolved_targets:

            report_target(
                symbol
            )

        final_summary(
            resolved_targets
        )

        elapsed = (
            time.perf_counter()
            - started
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
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "PRODUCTION DB WRITE       : BLOCKED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )