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
# CREATE_OUTCOME -> FIND_FUTURE_PRICE
# RUNTIME CALLER TRACE FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Resolve the real runtime path:
#
#     create_outcome(...)
#             |
#             v
#     find_future_price(...)
#
# The previous forensic audit established:
#
#     signal_outcome_engine.py
#         create_outcome()
#             |
#             +----> find_future_price()   LINE ~432
#
# This audit observes whether the REAL production caller
# reaches the REAL production target at runtime.
#
#
# SAFETY
# ------
# READ ONLY
#
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
#
# Production functions are imported in memory only.
#
# No production main() is executed.
#
# The original create_outcome() is executed unchanged
# when explicitly invoked by this forensic driver.
#
# The original find_future_price() is executed unchanged.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

TARGET_FILE = os.path.join(
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

TARGET_FUNCTION = "find_future_price"
CALLER_FUNCTION = "create_outcome"

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# FORENSIC STATE
# ============================================================

runtime_create_calls = defaultdict(list)
runtime_target_calls = defaultdict(list)
runtime_target_returns = defaultdict(list)
runtime_exceptions = []

sql_trace = []
blocked_writes = []

static_call_sites = []

entrypoint_status = {
    "create_outcome_attempted": False,
    "create_outcome_executed": False,
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


def safe_repr(value, limit=1800):
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
        f"TARGET FILE               : {TARGET_FILE}"
    )

    print(
        f"TARGET FILE FOUND         : {os.path.isfile(TARGET_FILE)}"
    )

    print(
        f"DATABASE PATH             : {DB_FILE}"
    )

    print(
        f"DATABASE FOUND            : {os.path.isfile(DB_FILE)}"
    )

    if not os.path.isfile(TARGET_FILE):
        raise FileNotFoundError(TARGET_FILE)

    if not os.path.isfile(DB_FILE):
        raise FileNotFoundError(DB_FILE)


# ============================================================
# STATIC SOURCE INSPECTION
# ============================================================

def inspect_source():

    section(
        "STEP 2 — PRODUCTION SOURCE INSPECTION"
    )

    with open(
        TARGET_FILE,
        "r",
        encoding="utf-8"
    ) as handle:

        source = handle.read()

    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    function_defs = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            function_defs[node.name] = node

    print(
        f"CREATE_OUTCOME DEFINITION : "
        f"{'FOUND' if CALLER_FUNCTION in function_defs else 'NOT_FOUND'}"
    )

    print(
        f"FIND_FUTURE_PRICE DEFINITION : "
        f"{'FOUND' if TARGET_FUNCTION in function_defs else 'NOT_FOUND'}"
    )

    if CALLER_FUNCTION in function_defs:

        print(
            f"CREATE_OUTCOME LINE       : "
            f"{function_defs[CALLER_FUNCTION].lineno}"
        )

    if TARGET_FUNCTION in function_defs:

        print(
            f"FIND_FUTURE_PRICE LINE    : "
            f"{function_defs[TARGET_FUNCTION].lineno}"
        )

    if CALLER_FUNCTION not in function_defs:
        raise RuntimeError(
            "create_outcome() definition not found"
        )

    if TARGET_FUNCTION not in function_defs:
        raise RuntimeError(
            "find_future_price() definition not found"
        )

    return tree


# ============================================================
# STATIC CALL-SITE RESOLUTION
# ============================================================

def resolve_static_call_sites(tree):

    section(
        "STEP 3 — STATIC CALLER RESOLUTION"
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        function_name = None

        if isinstance(
            node.func,
            ast.Name
        ):

            function_name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute
        ):

            function_name = node.func.attr

        if function_name != TARGET_FUNCTION:
            continue

        caller = "<UNKNOWN>"

        for parent in ast.walk(tree):

            if not isinstance(
                parent,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            ):
                continue

            for child in ast.walk(parent):

                if child is node:

                    caller = parent.name
                    break

            if caller != "<UNKNOWN>":
                break

        event = {
            "line": node.lineno,
            "caller": caller,
        }

        static_call_sites.append(
            event
        )

    print(
        f"STATIC CALL SITES : "
        f"{len(static_call_sites)}"
    )

    for event in static_call_sites:

        print(
            f"CALLER={event['caller']:<40} "
            f"LINE={event['line']}"
        )

    if not static_call_sites:

        raise RuntimeError(
            "No static call to find_future_price() found"
        )


# ============================================================
# READ-ONLY DATABASE
# ============================================================

def connect_read_only():

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
            "sql": str(sql),
            "parameters": parameters,
            "write_like": write_like,
        }

        sql_trace.append(
            event
        )

        if write_like:

            blocked_writes.append(
                event
            )

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

        sql_trace.append(
            event
        )

        if write_like:

            blocked_writes.append(
                event
            )

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

        return self._cursor.fetchmany(size)

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


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


# ============================================================
# MODULE IMPORT
# ============================================================

def import_production_module():

    section(
        "STEP 4 — PRODUCTION MODULE IMPORT"
    )

    spec = importlib.util.spec_from_file_location(
        MODULE_NAME,
        TARGET_FILE
    )

    if spec is None:
        raise RuntimeError(
            "Could not create module spec"
        )

    module = importlib.util.module_from_spec(
        spec
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
# GENERIC SYMBOL EXTRACTION
# ============================================================

def extract_symbol(
    args,
    kwargs
):

    if "symbol" in kwargs:

        return kwargs["symbol"]

    for index, value in enumerate(args):

        if isinstance(value, str):

            upper = value.upper()

            if upper in TARGETS:

                return upper

    return "UNKNOWN"


# ============================================================
# OBSERVER INSTALLATION
# ============================================================

def install_observers(module):

    section(
        "STEP 5 — RUNTIME OBSERVER INSTALLATION"
    )

    original_create = getattr(
        module,
        CALLER_FUNCTION,
        None
    )

    original_target = getattr(
        module,
        TARGET_FUNCTION,
        None
    )

    if original_create is None:

        raise RuntimeError(
            "create_outcome() not available"
        )

    if original_target is None:

        raise RuntimeError(
            "find_future_price() not available"
        )

    print(
        "ORIGINAL create_outcome()       : FOUND"
    )

    print(
        "ORIGINAL find_future_price()    : FOUND"
    )

    def forensic_find_future_price(
        *args,
        **kwargs
    ):

        call_index = (
            len(
                runtime_target_calls[
                    "GLOBAL"
                ]
            )
            + 1
        )

        symbol = extract_symbol(
            args,
            kwargs
        )

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "args": args,
            "kwargs": kwargs,
        }

        runtime_target_calls[
            "GLOBAL"
        ].append(
            event
        )

        runtime_target_calls[
            symbol
        ].append(
            event
        )

        print()
        print(
            "[FIND_FUTURE_PRICE RUNTIME CALL]"
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

            result = original_target(
                *args,
                **kwargs
            )

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        TARGET_FUNCTION,
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

        result_event = {
            "call_index": call_index,
            "symbol": symbol,
            "result": result,
            "result_type":
                type(result).__name__,
        }

        runtime_target_returns[
            symbol
        ].append(
            result_event
        )

        print(
            "[FIND_FUTURE_PRICE RETURN]"
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
            f"{safe_repr(result)}"
        )

        return result

    def forensic_create_outcome(
        *args,
        **kwargs
    ):

        call_index = (
            sum(
                len(values)
                for values in runtime_create_calls.values()
            )
            + 1
        )

        symbol = extract_symbol(
            args,
            kwargs
        )

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "args": args,
            "kwargs": kwargs,
        }

        runtime_create_calls[
            symbol
        ].append(
            event
        )

        entrypoint_status[
            "create_outcome_attempted"
        ] = True

        print()
        print(
            "[CREATE_OUTCOME RUNTIME CALL]"
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
                        CALLER_FUNCTION,
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

        entrypoint_status[
            "create_outcome_executed"
        ] = True

        print()
        print(
            "[CREATE_OUTCOME RETURN]"
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
            f"{safe_repr(result)}"
        )

        return result

    module.find_future_price = (
        forensic_find_future_price
    )

    module.create_outcome = (
        forensic_create_outcome
    )

    print(
        "[PATCHED] find_future_price observer"
    )

    print(
        "[PATCHED] create_outcome observer"
    )

    module._forensic_original_find_future_price = (
        original_target
    )

    module._forensic_original_create_outcome = (
        original_create
    )


# ============================================================
# DISCOVER CREATE_OUTCOME SIGNATURE
# ============================================================

def inspect_signature(module):

    section(
        "STEP 6 — CREATE_OUTCOME SIGNATURE"

    )

    import inspect

    function = getattr(
        module,
        CALLER_FUNCTION
    )

    signature = inspect.signature(
        function
    )

    print(
        f"SIGNATURE : {signature}"
    )

    return signature


# ============================================================
# SAFE TARGET DATA DISCOVERY
# ============================================================

def discover_market_data_targets():

    section(
        "STEP 7 — READ-ONLY TARGET DATA DISCOVERY"
    )

    conn = connect_read_only()

    try:

        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='market_data'
            """
        ).fetchone()

        print(
            f"MARKET_DATA TABLE FOUND : "
            f"{table is not None}"
        )

        if table is None:
            return {}

        results = {}

        for symbol in TARGETS:

            rows = conn.execute(
                """
                SELECT *
                FROM market_data
                WHERE UPPER(symbol)=?
                ORDER BY id DESC
                LIMIT 3
                """,
                (symbol,)
            ).fetchall()

            results[symbol] = rows

            print(
                f"{symbol:<6} | "
                f"ROWS={len(rows)}"
            )

        return results

    finally:

        conn.close()


# ============================================================
# ARGUMENT STRATEGY
# ============================================================
#
# IMPORTANT:
#
# We do NOT invent a production call signature.
#
# The audit first inspects the actual signature.
#
# If it cannot safely determine arguments, it stops rather
# than fabricating a call.
#
# ============================================================

def build_safe_invocation(
    signature,
    symbol,
    market_rows
):

    import inspect

    parameters = list(
        signature.parameters.values()
    )

    args = []
    kwargs = {}

    unresolved_required = []

    for parameter in parameters:

        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):

            continue

        if parameter.default is not inspect.Parameter.empty:

            continue

        name = parameter.name.lower()

        if name in (
            "symbol",
            "ticker",
            "asset",
        ):

            kwargs[
                parameter.name
            ] = symbol

            continue

        if name in (
            "rows",
            "market_data",
            "data",
            "history",
        ):

            kwargs[
                parameter.name
            ] = market_rows

            continue

        unresolved_required.append(
            parameter.name
        )

    if unresolved_required:

        return None, None, unresolved_required

    return args, kwargs, []


# ============================================================
# EXPLICIT RUNTIME CALL
# ============================================================

def execute_create_outcome_for_target(
    module,
    signature,
    symbol,
    market_rows
):

    subsection(
        f"RUNTIME TARGET : {symbol}"
    )

    args, kwargs, unresolved = (
        build_safe_invocation(
            signature,
            symbol,
            market_rows
        )
    )

    if unresolved:

        print(
            "SAFE INVOCATION BLOCKED"
        )

        print(
            f"UNRESOLVED REQUIRED PARAMETERS : "
            f"{unresolved}"
        )

        print(
            "NO FABRICATED ARGUMENTS WERE USED."
        )

        return False

    print(
        "INVOCATION ARGUMENTS"
    )

    print(
        f"ARGS   : {safe_repr(args)}"
    )

    print(
        f"KWARGS : {safe_repr(kwargs)}"
    )

    try:

        module.create_outcome(
            *args,
            **kwargs
        )

        return True

    except Exception as exc:

        print()
        print(
            "[RUNTIME INVOCATION EXCEPTION]"
        )

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        return False


# ============================================================
# RUNTIME SUMMARY
# ============================================================

def runtime_summary():

    section(
        "STEP 8 — RUNTIME TRACE INVENTORY"
    )

    create_count = sum(
        len(values)
        for values in runtime_create_calls.values()
    )

    target_count = len(
        runtime_target_calls.get(
            "GLOBAL",
            []
        )
    )

    return_count = sum(
        len(values)
        for values in runtime_target_returns.values()
    )

    print(
        f"CREATE_OUTCOME CALLS       : {create_count}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS    : {target_count}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS  : {return_count}"
    )

    print(
        f"SQL EVENTS                 : {len(sql_trace)}"
    )

    print(
        f"BLOCKED WRITES             : {len(blocked_writes)}"
    )

    print(
        f"RUNTIME EXCEPTIONS         : {len(runtime_exceptions)}"
    )

    print()

    print(
        "TARGET DISTRIBUTION"
    )

    for symbol in TARGETS:

        print(
            f"{symbol:<6} | "
            f"CREATE="
            f"{len(runtime_create_calls.get(symbol, [])):<3}"
            f" | FIND_FUTURE_PRICE="
            f"{len(runtime_target_calls.get(symbol, [])):<3}"
            f" | RETURNS="
            f"{len(runtime_target_returns.get(symbol, [])):<3}"
        )


# ============================================================
# FINAL STATUS
# ============================================================

def determine_status():

    create_count = sum(
        len(values)
        for values in runtime_create_calls.values()
    )

    target_count = len(
        runtime_target_calls.get(
            "GLOBAL",
            []
        )
    )

    return_count = sum(
        len(values)
        for values in runtime_target_returns.values()
    )

    if target_count > 0 and return_count > 0:

        return (
            "CREATE_OUTCOME_REACHED_FIND_FUTURE_PRICE"
        )

    if create_count > 0 and target_count == 0:

        return (
            "CREATE_OUTCOME_EXECUTED_TARGET_NOT_REACHED"
        )

    if create_count == 0:

        return (
            "CREATE_OUTCOME_NOT_EXECUTED"
        )

    return (
        "RUNTIME_PATH_UNRESOLVED"
    )


# ============================================================
# FINAL FORENSIC SUMMARY
# ============================================================

def final_summary():

    section(
        "STEP 9 — FINAL FORENSIC SUMMARY"
    )

    status = determine_status()

    create_count = sum(
        len(values)
        for values in runtime_create_calls.values()
    )

    target_count = len(
        runtime_target_calls.get(
            "GLOBAL",
            []
        )
    )

    return_count = sum(
        len(values)
        for values in runtime_target_returns.values()
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"CALLER FUNCTION             : "
        f"{CALLER_FUNCTION}"
    )

    print(
        f"STATIC CALL SITES           : "
        f"{len(static_call_sites)}"
    )

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{create_count}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{target_count}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{return_count}"
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

    if status == (
        "CREATE_OUTCOME_REACHED_FIND_FUTURE_PRICE"
    ):

        print(
            "MEANING                     : "
            "The production create_outcome() "
            "caller was executed and the real "
            "find_future_price() production "
            "function was reached."
        )

        print(
            "NEXT FRONTIER               : "
            "Trace the find_future_price return "
            "into the create_outcome assignment "
            "and downstream outcome construction."
        )

    elif status == (
        "CREATE_OUTCOME_EXECUTED_TARGET_NOT_REACHED"
    ):

        print(
            "MEANING                     : "
            "The real create_outcome() executed, "
            "but find_future_price() was not reached "
            "during the observed invocation."
        )

        print(
            "NEXT FRONTIER               : "
            "Trace the conditional path inside "
            "create_outcome() that controls the "
            "find_future_price() call."
        )

    elif status == (
        "CREATE_OUTCOME_NOT_EXECUTED"
    ):

        print(
            "MEANING                     : "
            "create_outcome() was not reached "
            "during the safe runtime invocation."
        )

        print(
            "NEXT FRONTIER               : "
            "Resolve the actual production caller "
            "that reaches create_outcome()."
        )

    else:

        print(
            "MEANING                     : "
            "Runtime execution did not provide "
            "enough evidence to resolve the path."
        )

        print(
            "NEXT FRONTIER               : "
            "Inspect the captured runtime exception "
            "or invocation boundary without "
            "fabricating missing values."
        )

    print()

    print(
        "IMPORTANT                   : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                   : "
        "Original production functions were "
        "executed unchanged."
    )

    print(
        "IMPORTANT                   : "
        "No production main() was executed."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
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
        "ARUNDA CREATE_OUTCOME -> "
        "FIND_FUTURE_PRICE RUNTIME "
        "CALLER TRACE FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                        : READ ONLY FORENSIC"
    )

    print(
        "PRODUCTION main()           : NOT CALLED"
    )

    print(
        "DATABASE WRITE              : BLOCKED"
    )

    try:

        verify_paths()

        tree = inspect_source()

        resolve_static_call_sites(
            tree
        )

        module = import_production_module()

        signature = inspect_signature(
            module
        )

        install_observers(
            module
        )

        target_data = (
            discover_market_data_targets()
        )

        for symbol in TARGETS:

            market_rows = target_data.get(
                symbol,
                []
            )

            if not market_rows:

                print()
                print(
                    f"[TARGET SKIPPED] "
                    f"{symbol} — no market_data rows"
                )

                continue

            execute_create_outcome_for_target(
                module,
                signature,
                symbol,
                market_rows
            )

        runtime_summary()

        final_summary()

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