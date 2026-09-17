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
# FIND_FUTURE_PRICE DOWNSTREAM VALUE COMPARISON
# FORENSIC AUDIT v0.2
# ============================================================
#
# PURPOSE
# -------
# Compare the REAL production return value of:
#
#     signal_outcome_engine.py
#         find_future_price()
#
# against the actual downstream value observed in:
#
#     create_outcome()
#
# The production function is executed unchanged.
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
# Database is opened read-only.
# Original production save/write paths are never executed.
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
    "arunda_signal_outcome_forensic_v02"
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

runtime_find_calls = defaultdict(list)
runtime_find_returns = defaultdict(list)
runtime_create_returns = defaultdict(list)

runtime_assignment_values = defaultdict(list)

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


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=1600):
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
        f"PROJECT PATH          : {PROJECT_DIR}"
    )

    print(
        f"TARGET FILE           : {TARGET_FILE}"
    )

    print(
        f"TARGET FILE FOUND     : {os.path.isfile(TARGET_FILE)}"
    )

    print(
        f"DATABASE PATH         : {DB_FILE}"
    )

    print(
        f"DATABASE FOUND        : {os.path.isfile(DB_FILE)}"
    )

    if not os.path.isfile(TARGET_FILE):
        raise FileNotFoundError(
            TARGET_FILE
        )

    if not os.path.isfile(DB_FILE):
        raise FileNotFoundError(
            DB_FILE
        )


# ============================================================
# SOURCE LOADER
# ============================================================

def load_source(path):

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as handle:

        return handle.read()


# ============================================================
# STATIC SOURCE INSPECTION
# ============================================================

def inspect_source():

    section(
        "STEP 2 — TARGET SOURCE INSPECTION"
    )

    source = load_source(
        TARGET_FILE
    )

    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    functions = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            functions[node.name] = node

    print(
        f"TARGET FUNCTION EXISTS : "
        f"{TARGET_FUNCTION in functions}"
    )

    print(
        f"CALLER FUNCTION EXISTS  : "
        f"{CALLER_FUNCTION in functions}"
    )

    if TARGET_FUNCTION in functions:

        print(
            f"{TARGET_FUNCTION} LINE : "
            f"{functions[TARGET_FUNCTION].lineno}"
        )

    if CALLER_FUNCTION in functions:

        print(
            f"{CALLER_FUNCTION} LINE : "
            f"{functions[CALLER_FUNCTION].lineno}"
        )

    if TARGET_FUNCTION not in functions:
        raise RuntimeError(
            "find_future_price() not found"
        )

    if CALLER_FUNCTION not in functions:
        raise RuntimeError(
            "create_outcome() not found"
        )

    return source, tree, functions


# ============================================================
# READ-ONLY SQLITE
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
# READ-ONLY CONNECTION WRAPPER
# ============================================================

class ForensicCursor:

    def __init__(self, cursor):

        self._cursor = cursor

    def execute(
        self,
        sql,
        parameters=()
    ):

        write_like = classify_sql(
            sql
        )

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

        write_like = classify_sql(
            sql
        )

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

    def execute(
        self,
        sql,
        parameters=()
    ):

        cursor = ForensicCursor(
            self._connection.cursor()
        )

        cursor.execute(
            sql,
            parameters
        )

        return cursor

    def cursor(self):

        return ForensicCursor(
            self._connection.cursor()
        )

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
# GENERIC SYMBOL / VALUE HELPERS
# ============================================================

def extract_symbol(args, kwargs):

    if "symbol" in kwargs:
        return kwargs["symbol"]

    for value in args:

        if isinstance(
            value,
            str
        ):

            upper = value.upper()

            if upper in TARGETS:
                return upper

    return None


def normalize_value(value):

    if isinstance(
        value,
        dict
    ):
        return dict(value)

    if isinstance(
        value,
        sqlite3.Row
    ):
        return {
            key: value[key]
            for key in value.keys()
        }

    try:
        return dict(value)
    except Exception:
        return value


# ============================================================
# VALUE COMPARISON
# ============================================================

def values_equal(left, right):

    if left is right:
        return True

    if type(left) is not type(right):

        try:
            return float(left) == float(right)
        except Exception:
            return False

    try:
        return left == right
    except Exception:
        return safe_repr(left) == safe_repr(right)


def compare_values(
    runtime_value,
    downstream_value
):

    result = {
        "runtime": runtime_value,
        "downstream": downstream_value,
        "equal": values_equal(
            runtime_value,
            downstream_value
        ),
    }

    return result


# ============================================================
# TARGET FUNCTION WRAPPER
# ============================================================

def install_runtime_observers(
    module
):

    section(
        "STEP 3 — RUNTIME OBSERVER INSTALLATION"
    )

    original_find = (
        getattr(
            module,
            TARGET_FUNCTION
        )
    )

    original_create = (
        getattr(
            module,
            CALLER_FUNCTION
        )
    )

    original_connect = getattr(
        module,
        "connect_database",
        None
    )

    original_save = getattr(
        module,
        "save_outcome",
        None
    )

    print(
        "ORIGINAL find_future_price : FOUND"
    )

    print(
        "ORIGINAL create_outcome     : FOUND"
    )

    if original_connect is not None:

        print(
            "ORIGINAL connect_database   : FOUND"
        )

    if original_save is not None:

        print(
            "ORIGINAL save_outcome       : FOUND"
        )

    # --------------------------------------------------------
    # FIND FUTURE PRICE OBSERVER
    # --------------------------------------------------------

    def forensic_find_future_price(
        *args,
        **kwargs
    ):

        symbol = extract_symbol(
            args,
            kwargs
        )

        call_index = (
            sum(
                len(values)
                for values in
                runtime_find_calls.values()
            )
            + 1
        )

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "args": args,
            "kwargs": kwargs,
        }

        runtime_find_calls[
            symbol or "UNKNOWN"
        ].append(
            event
        )

        print()

        print(
            "[FIND_FUTURE_PRICE CALL]"
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
                        TARGET_FUNCTION,
                    "symbol":
                        symbol,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            raise

        runtime_find_returns[
            symbol or "UNKNOWN"
        ].append(
            {
                "call_index": call_index,
                "symbol": symbol,
                "result": result,
                "result_type":
                    type(result).__name__,
            }
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

    # --------------------------------------------------------
    # CREATE OUTCOME OBSERVER
    #
    # The real production function is executed unchanged.
    # --------------------------------------------------------

    def forensic_create_outcome(
        *args,
        **kwargs
    ):

        symbol = extract_symbol(
            args,
            kwargs
        )

        print()

        print(
            "[CREATE_OUTCOME ENTER]"
        )

        print(
            f"SYMBOL : {symbol}"
        )

        print(
            f"ARGS   : {safe_repr(args)}"
        )

        print(
            f"KWARGS  : {safe_repr(kwargs)}"
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

            raise

        runtime_create_returns[
            symbol or "UNKNOWN"
        ].append(
            {
                "symbol": symbol,
                "result": result,
                "result_type":
                    type(result).__name__,
            }
        )

        print(
            "[CREATE_OUTCOME RETURN]"
        )

        print(
            f"TYPE   : "
            f"{type(result).__name__}"
        )

        print(
            f"RETURN : "
            f"{safe_repr(result)}"
        )

        return result

    # --------------------------------------------------------
    # CONNECT DATABASE
    # --------------------------------------------------------

    def forensic_connect():

        return forensic_connection_factory()

    # --------------------------------------------------------
    # OPTIONAL WRITE FUNCTIONS
    # --------------------------------------------------------

    def forensic_save_outcome(
        *args,
        **kwargs
    ):

        symbol = extract_symbol(
            args,
            kwargs
        )

        print()

        print(
            "[SAVE_OUTCOME OBSERVED]"
        )

        print(
            f"SYMBOL : {symbol}"
        )

        print(
            f"ARGS   : {safe_repr(args)}"
        )

        print(
            f"KWARGS : {safe_repr(kwargs)}"
        )

        return False

    # --------------------------------------------------------
    # PATCH MODULE REFERENCES
    # --------------------------------------------------------

    module.find_future_price = (
        forensic_find_future_price
    )

    module.create_outcome = (
        forensic_create_outcome
    )

    if original_connect is not None:

        module.connect_database = (
            forensic_connect
        )

    if original_save is not None:

        module.save_outcome = (
            forensic_save_outcome
        )

    module._forensic_original_find = (
        original_find
    )

    module._forensic_original_create = (
        original_create
    )

    print()

    print(
        "[PATCHED] find_future_price"
    )

    print(
        "[PATCHED] create_outcome"
    )

    if original_connect is not None:

        print(
            "[PATCHED] connect_database"
        )

    if original_save is not None:

        print(
            "[PATCHED] save_outcome"
        )


# ============================================================
# PRODUCTION MODULE IMPORT
# ============================================================

def import_production_module():

    section(
        "STEP 4 — PRODUCTION MODULE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            MODULE_NAME,
            TARGET_FILE
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
# PRODUCTION ENTRYPOINT RESOLUTION
# ============================================================

def resolve_entrypoint(module):

    section(
        "STEP 5 — PRODUCTION ENTRYPOINT RESOLUTION"
    )

    if hasattr(
        module,
        "main"
    ):

        print(
            "ENTRYPOINT : main()"
        )

        return module.main

    print(
        "ENTRYPOINT : NOT FOUND"
    )

    return None


# ============================================================
# OPTIONAL DATABASE SNAPSHOT
# ============================================================

def read_latest_market_data():

    section(
        "STEP 6 — READ-ONLY DATABASE SNAPSHOT"
    )

    try:

        conn = open_read_only_database()

        try:

            table = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name='market_data'
                """
            ).fetchone()

            if table is None:

                print(
                    "MARKET_DATA TABLE : NOT FOUND"
                )

                return

            print(
                "MARKET_DATA TABLE   : FOUND"
            )

            for symbol in TARGETS:

                row = conn.execute(
                    """
                    SELECT *
                    FROM market_data
                    WHERE symbol = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (symbol,)
                ).fetchone()

                if row is None:

                    print(
                        f"{symbol:<6} | NO ROW"
                    )

                    continue

                data = {
                    key: row[key]
                    for key in row.keys()
                }

                print()

                print(
                    f"{symbol} | "
                    f"ID={data.get('id')} | "
                    f"CLOSE={data.get('close')} | "
                    f"SOURCE={data.get('source')}"
                )

        finally:

            conn.close()

    except Exception as exc:

        print(
            "[READ-ONLY DB SNAPSHOT ERROR]"
        )

        print(
            repr(exc)
        )


# ============================================================
# RUNTIME EXECUTION
# ============================================================

def execute_entrypoint(
    entrypoint
):

    section(
        "STEP 7 — READ-ONLY PRODUCTION RUNTIME"
    )

    if entrypoint is None:

        print(
            "NO PRODUCTION ENTRYPOINT FOUND"
        )

        return None

    entrypoint_status[
        "executed"
    ] = True

    try:

        result = entrypoint()

        print()

        print(
            "[PRODUCTION ENTRYPOINT RETURN]"
        )

        print(
            f"TYPE   : {type(result).__name__}"
        )

        print(
            f"RETURN : {safe_repr(result)}"
        )

        return result

    except Exception as exc:

        entrypoint_status[
            "exception"
        ] = repr(exc)

        runtime_exceptions.append(
            {
                "stage": "main",
                "exception":
                    repr(exc),
                "traceback":
                    traceback.format_exc(),
            }
        )

        print()

        print(
            "[PRODUCTION ENTRYPOINT EXCEPTION]"
        )

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        return None


# ============================================================
# RUNTIME COMPARISON REPORT
# ============================================================

def report_comparison():

    section(
        "STEP 8 — DOWNSTREAM VALUE COMPARISON"
    )

    total_find_calls = sum(
        len(values)
        for values in runtime_find_calls.values()
    )

    total_find_returns = sum(
        len(values)
        for values in runtime_find_returns.values()
    )

    total_create_returns = sum(
        len(values)
        for values in runtime_create_returns.values()
    )

    print(
        f"FIND_FUTURE_PRICE CALLS  : "
        f"{total_find_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS : "
        f"{total_find_returns}"
    )

    print(
        f"CREATE_OUTCOME RETURNS    : "
        f"{total_create_returns}"
    )

    for symbol in TARGETS:

        subsection(
            f"TARGET : {symbol}"
        )

        calls = (
            runtime_find_calls.get(
                symbol,
                []
            )
        )

        returns = (
            runtime_find_returns.get(
                symbol,
                []
            )
        )

        creates = (
            runtime_create_returns.get(
                symbol,
                []
            )
        )

        print(
            f"FIND CALLS    : {len(calls)}"
        )

        print(
            f"FIND RETURNS  : {len(returns)}"
        )

        print(
            f"CREATE RETURNS: {len(creates)}"
        )

        if returns:

            latest_find = returns[-1]

            print()

            print(
                "ACTUAL FUTURE PRICE RETURN"
            )

            print(
                f"VALUE : "
                f"{safe_repr(latest_find['result'])}"
            )

        if creates:

            latest_create = creates[-1]

            create_result = normalize_value(
                latest_create["result"]
            )

            print()

            print(
                "CREATE_OUTCOME RESULT"
            )

            print(
                f"VALUE : "
                f"{safe_repr(create_result)}"
            )

            if isinstance(
                create_result,
                dict
            ):

                candidate_fields = [
                    "future_price",
                    "future_close",
                    "future_value",
                    "price",
                    "outcome_price",
                    "target_price",
                ]

                print()

                print(
                    "POSSIBLE DOWNSTREAM FIELDS"
                )

                for field in candidate_fields:

                    if field in create_result:

                        print(
                            f"{field:<20} : "
                            f"{safe_repr(create_result[field])}"
                        )

                        if returns:

                            comparison = compare_values(
                                returns[-1]["result"],
                                create_result[field]
                            )

                            print(
                                f"{'MATCH' if comparison['equal'] else 'DIFF':<20}"
                                f": "
                                f"runtime={safe_repr(comparison['runtime'])} "
                                f"| downstream={safe_repr(comparison['downstream'])}"
                            )


# ============================================================
# STATUS DETERMINATION
# ============================================================

def determine_status():

    total_find_calls = sum(
        len(values)
        for values in runtime_find_calls.values()
    )

    total_find_returns = sum(
        len(values)
        for values in runtime_find_returns.values()
    )

    if total_find_calls == 0:

        return (
            "FIND_FUTURE_PRICE_NOT_REACHED",
            "The production runtime did not reach find_future_price().",
        )

    if total_find_returns == 0:

        return (
            "FIND_FUTURE_PRICE_RETURN_NOT_CAPTURED",
            "find_future_price() was reached but no usable return was captured.",
        )

    total_create_returns = sum(
        len(values)
        for values in runtime_create_returns.values()
    )

    if total_create_returns == 0:

        return (
            "FIND_FUTURE_PRICE_DOWNSTREAM_NOT_OBSERVED",
            "The future price return was captured, but create_outcome() did not expose a downstream return.",
        )

    return (
        "FIND_FUTURE_PRICE_DOWNSTREAM_COMPARISON_READY",
        "The real find_future_price() return and downstream create_outcome() return were both observed.",
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary():

    status, meaning = determine_status()

    section(
        "STEP 9 — FINAL FORENSIC SUMMARY"
    )

    total_find_calls = sum(
        len(values)
        for values in runtime_find_calls.values()
    )

    total_find_returns = sum(
        len(values)
        for values in runtime_find_returns.values()
    )

    total_create_returns = sum(
        len(values)
        for values in runtime_create_returns.values()
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
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{total_find_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{total_find_returns}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{total_create_returns}"
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
        "FIND_FUTURE_PRICE_DOWNSTREAM_COMPARISON_READY"
    ):

        print(
            "NEXT FRONTIER              : "
            "Localize the exact downstream field "
            "receiving the captured future price and "
            "compare it field-by-field."
        )

    elif status == (
        "FIND_FUTURE_PRICE_DOWNSTREAM_NOT_OBSERVED"
    ):

        print(
            "NEXT FRONTIER              : "
            "Trace the internal assignment and return "
            "flow inside create_outcome()."
        )

    else:

        print(
            "NEXT FRONTIER              : "
            "Resolve the missing runtime path before "
            "performing downstream comparison."
        )

    print()

    print(
        "IMPORTANT                   : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                   : "
        "The original find_future_price() function "
        "was executed unchanged."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                   : "
        "No production database write was permitted."
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
        "ARUNDA FIND_FUTURE_PRICE DOWNSTREAM "
        "VALUE COMPARISON FORENSIC AUDIT v0.2"
    )

    print(
        "MODE                        : "
        "READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                      : "
        "signal_outcome_engine.py -> "
        "find_future_price()"
    )

    print(
        "CALLER                      : "
        "create_outcome()"
    )

    print(
        "DATABASE WRITE              : "
        "BLOCKED"
    )

    try:

        verify_paths()

        inspect_source()

        module = (
            import_production_module()
        )

        install_runtime_observers(
            module
        )

        read_latest_market_data()

        entrypoint = (
            resolve_entrypoint(
                module
            )
        )

        execute_entrypoint(
            entrypoint
        )

        report_comparison()

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