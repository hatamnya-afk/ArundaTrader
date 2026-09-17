import os
import sys
import ast
import time
import traceback
import importlib.util
import sqlite3
from collections import defaultdict, deque

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

TARGET_FILE = os.path.join(
    PROJECT_DIR,
    "signal_outcome_engine.py"
)

TARGET_MODULE_NAME = "signal_outcome_engine_forensic_runtime_v01"

TARGET_FUNCTION = "create_outcome"
SECONDARY_FUNCTION = "find_future_price"

ENTRYPOINT_FUNCTION = "main"

TARGETS = ["BTC", "ETH", "SOL", "XRP"]

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

runtime_events = []
runtime_calls = defaultdict(list)
runtime_returns = defaultdict(list)
runtime_sql = []
blocked_writes = []
runtime_exceptions = []

entrypoint_status = {
    "attempted": False,
    "executed": False,
    "exception": None,
}

static_call_sites = []
static_parse_errors = []


def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def safe_repr(value, limit=2000):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def normalize_sql(sql):
    return " ".join(
        str(sql).strip().upper().split()
    )


def classify_sql(sql):
    normalized = normalize_sql(sql)

    if not normalized:
        return False

    return normalized.startswith(
        WRITE_PREFIXES
    )


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
        f"TARGET EXISTS             : {os.path.isfile(TARGET_FILE)}"
    )

    if not os.path.isfile(TARGET_FILE):
        raise FileNotFoundError(TARGET_FILE)


def read_source():
    with open(
        TARGET_FILE,
        "r",
        encoding="utf-8-sig"
    ) as handle:
        return handle.read()


def inspect_target_source():
    section(
        "STEP 2 — TARGET SOURCE RESOLUTION"
    )

    source = read_source()

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
        f"TARGET FUNCTION FOUND       : "
        f"{TARGET_FUNCTION in functions}"
    )

    print(
        f"SECONDARY FUNCTION FOUND    : "
        f"{SECONDARY_FUNCTION in functions}"
    )

    print(
        f"ENTRYPOINT FUNCTION FOUND   : "
        f"{ENTRYPOINT_FUNCTION in functions}"
    )

    if TARGET_FUNCTION in functions:
        print(
            f"{TARGET_FUNCTION} LINE       : "
            f"{functions[TARGET_FUNCTION].lineno}"
        )

    if SECONDARY_FUNCTION in functions:
        print(
            f"{SECONDARY_FUNCTION} LINE    : "
            f"{functions[SECONDARY_FUNCTION].lineno}"
        )

    if ENTRYPOINT_FUNCTION in functions:
        print(
            f"{ENTRYPOINT_FUNCTION} LINE       : "
            f"{functions[ENTRYPOINT_FUNCTION].lineno}"
        )

    if TARGET_FUNCTION not in functions:
        raise RuntimeError(
            f"{TARGET_FUNCTION} not found"
        )

    return tree


def resolve_direct_call_sites(tree):
    section(
        "STEP 3 — STATIC CALL SITE RESOLUTION"
    )

    sites = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        caller = node.name

        for child in ast.walk(node):

            if not isinstance(
                child,
                ast.Call
            ):
                continue

            function_name = None

            if isinstance(
                child.func,
                ast.Name
            ):
                function_name = child.func.id

            elif isinstance(
                child.func,
                ast.Attribute
            ):
                function_name = child.func.attr

            if function_name in (
                TARGET_FUNCTION,
                SECONDARY_FUNCTION,
            ):

                event = {
                    "caller": caller,
                    "target": function_name,
                    "line": child.lineno,
                }

                sites.append(event)

                print(
                    f"CALLER={caller:<35} "
                    f"LINE={child.lineno:<6} "
                    f"CALL={function_name}"
                )

    return sites


class ForensicCursor:

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, parameters=()):
        write_like = classify_sql(sql)

        event = {
            "sql": str(sql),
            "parameters": safe_repr(parameters),
            "write_like": write_like,
        }

        runtime_sql.append(event)

        if write_like:

            blocked_writes.append(event)

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL"
            )

        return self._cursor.execute(
            sql,
            parameters
        )

    def executemany(self, sql, parameters):
        write_like = classify_sql(sql)

        event = {
            "sql": str(sql),
            "parameters": "<executemany>",
            "write_like": write_like,
        }

        runtime_sql.append(event)

        if write_like:

            blocked_writes.append(event)

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL"
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

    def execute(self, sql, parameters=()):
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


def open_read_only_database():
    db_file = os.path.join(
        PROJECT_DIR,
        "arunda.db"
    )

    if not os.path.isfile(db_file):
        raise FileNotFoundError(db_file)

    uri = (
        "file:"
        + db_file.replace("\\", "/")
        + "?mode=ro"
    )

    connection = sqlite3.connect(
        uri,
        uri=True
    )

    connection.row_factory = sqlite3.Row

    return ForensicConnection(
        connection
    )


def snapshot_value(value):
    try:
        if isinstance(value, sqlite3.Row):
            return {
                key: value[key]
                for key in value.keys()
            }

        if isinstance(value, dict):
            return dict(value)

        if isinstance(value, (list, tuple)):
            return [
                snapshot_value(item)
                for item in value
            ]

        return value

    except Exception:
        return safe_repr(value)


def extract_symbol(args, kwargs):
    if "symbol" in kwargs:
        return kwargs["symbol"]

    for value in args:
        if isinstance(value, str):
            candidate = value.upper()

            if candidate in TARGETS:
                return candidate

    return None


def install_runtime_wrappers(module):
    section(
        "STEP 4 — RUNTIME OBSERVER INSTALLATION"
    )

    original_create_outcome = getattr(
        module,
        TARGET_FUNCTION,
        None
    )

    original_find_future_price = getattr(
        module,
        SECONDARY_FUNCTION,
        None
    )

    original_connect_database = getattr(
        module,
        "connect_database",
        None
    )

    if original_create_outcome is None:
        raise RuntimeError(
            "create_outcome not found"
        )

    print(
        "ORIGINAL create_outcome      : FOUND"
    )

    print(
        "ORIGINAL find_future_price   : "
        + (
            "FOUND"
            if original_find_future_price
            else "NOT FOUND"
        )
    )

    if original_connect_database:
        print(
            "ORIGINAL connect_database    : FOUND"
        )

    def forensic_create_outcome(
        *args,
        **kwargs
    ):

        call_index = (
            len(
                runtime_calls[TARGET_FUNCTION]
            ) + 1
        )

        symbol = extract_symbol(
            args,
            kwargs
        )

        event = {
            "function": TARGET_FUNCTION,
            "call_index": call_index,
            "symbol": symbol,
            "args": snapshot_value(args),
            "kwargs": snapshot_value(kwargs),
        }

        runtime_calls[
            TARGET_FUNCTION
        ].append(event)

        runtime_events.append(event)

        print()
        print(
            "[RUNTIME create_outcome]"
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

            result = original_create_outcome(
                *args,
                **kwargs
            )

            return_event = {
                "function": TARGET_FUNCTION,
                "call_index": call_index,
                "symbol": symbol,
                "result": snapshot_value(result),
                "result_type": type(result).__name__,
            }

            runtime_returns[
                TARGET_FUNCTION
            ].append(
                return_event
            )

            print(
                "[RUNTIME create_outcome RETURN]"
            )

            print(
                f"TYPE   : {type(result).__name__}"
            )

            print(
                f"RESULT : {safe_repr(result)}"
            )

            return result

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "function": TARGET_FUNCTION,
                    "symbol": symbol,
                    "exception": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            print(
                "[RUNTIME create_outcome EXCEPTION]"
            )

            print(
                repr(exc)
            )

            raise

    def forensic_find_future_price(
        *args,
        **kwargs
    ):

        call_index = (
            len(
                runtime_calls[
                    SECONDARY_FUNCTION
                ]
            ) + 1
        )

        symbol = extract_symbol(
            args,
            kwargs
        )

        event = {
            "function": SECONDARY_FUNCTION,
            "call_index": call_index,
            "symbol": symbol,
            "args": snapshot_value(args),
            "kwargs": snapshot_value(kwargs),
        }

        runtime_calls[
            SECONDARY_FUNCTION
        ].append(event)

        runtime_events.append(event)

        print()
        print(
            "[RUNTIME find_future_price]"
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

            result = original_find_future_price(
                *args,
                **kwargs
            )

            return_event = {
                "function": SECONDARY_FUNCTION,
                "call_index": call_index,
                "symbol": symbol,
                "result": snapshot_value(result),
                "result_type": type(result).__name__,
            }

            runtime_returns[
                SECONDARY_FUNCTION
            ].append(
                return_event
            )

            print(
                "[RUNTIME find_future_price RETURN]"
            )

            print(
                f"TYPE   : {type(result).__name__}"
            )

            print(
                f"RESULT : {safe_repr(result)}"
            )

            return result

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "function": SECONDARY_FUNCTION,
                    "symbol": symbol,
                    "exception": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            print(
                "[RUNTIME find_future_price EXCEPTION]"
            )

            print(
                repr(exc)
            )

            raise

    def forensic_connect_database():
        return open_read_only_database()

    module.create_outcome = (
        forensic_create_outcome
    )

    if original_find_future_price:
        module.find_future_price = (
            forensic_find_future_price
        )

    if original_connect_database:
        module.connect_database = (
            forensic_connect_database
        )

    module._forensic_original_create_outcome = (
        original_create_outcome
    )

    module._forensic_original_find_future_price = (
        original_find_future_price
    )

    print(
        "PATCHED: create_outcome"
    )

    if original_find_future_price:
        print(
            "PATCHED: find_future_price"
        )

    if original_connect_database:
        print(
            "PATCHED: connect_database"
        )


def import_target_module():
    section(
        "STEP 5 — PRODUCTION MODULE IMPORT"
    )

    spec = importlib.util.spec_from_file_location(
        TARGET_MODULE_NAME,
        TARGET_FILE
    )

    if spec is None:
        raise RuntimeError(
            "Unable to create module spec"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        TARGET_MODULE_NAME
    ] = module

    spec.loader.exec_module(module)

    print(
        f"MODULE IMPORTED : {TARGET_MODULE_NAME}"
    )

    return module


def invoke_production_entrypoint(module):
    section(
        "STEP 6 — PRODUCTION CALL-CHAIN RUNTIME TRACE"
    )

    entrypoint_status[
        "attempted"
    ] = True

    production_main = getattr(
        module,
        ENTRYPOINT_FUNCTION,
        None
    )

    if production_main is None:
        print(
            "ENTRYPOINT main() : NOT FOUND"
        )

        return None

    print(
        "ENTRYPOINT        : signal_outcome_engine.py::main()"
    )

    print(
        "MODE              : READ-ONLY FORENSIC"
    )

    print(
        "DATABASE WRITE     : BLOCKED"
    )

    try:

        result = production_main()

        entrypoint_status[
            "executed"
        ] = True

        print()
        print(
            "[PRODUCTION MAIN RETURN]"
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
                "function": ENTRYPOINT_FUNCTION,
                "exception": repr(exc),
                "traceback": traceback.format_exc(),
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


def print_runtime_inventory():
    section(
        "STEP 7 — RUNTIME TRACE INVENTORY"
    )

    create_calls = len(
        runtime_calls[TARGET_FUNCTION]
    )

    create_returns = len(
        runtime_returns[TARGET_FUNCTION]
    )

    future_calls = len(
        runtime_calls[SECONDARY_FUNCTION]
    )

    future_returns = len(
        runtime_returns[SECONDARY_FUNCTION]
    )

    print(
        f"CREATE_OUTCOME CALLS       : {create_calls}"
    )

    print(
        f"CREATE_OUTCOME RETURNS     : {create_returns}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS    : {future_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS  : {future_returns}"
    )

    print(
        f"SQL EVENTS                 : {len(runtime_sql)}"
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

        create_count = sum(
            1
            for event in runtime_calls[TARGET_FUNCTION]
            if event.get("symbol") == symbol
        )

        future_count = sum(
            1
            for event in runtime_calls[SECONDARY_FUNCTION]
            if event.get("symbol") == symbol
        )

        return_count = sum(
            1
            for event in runtime_returns[SECONDARY_FUNCTION]
            if event.get("symbol") == symbol
        )

        print(
            f"{symbol:<6} | "
            f"CREATE={create_count:<3} "
            f"| FIND_FUTURE_PRICE={future_count:<3} "
            f"| RETURNS={return_count:<3}"
        )


def print_static_trace(sites):
    section(
        "STEP 8 — STATIC CALLER TRACE"
    )

    print(
        f"STATIC CALL SITES : {len(sites)}"
    )

    for event in sites:

        print(
            f"CALLER={event['caller']:<35} "
            f"LINE={event['line']:<6} "
            f"CALL={event['target']}"
        )


def determine_status(sites):
    create_calls = len(
        runtime_calls[TARGET_FUNCTION]
    )

    future_calls = len(
        runtime_calls[SECONDARY_FUNCTION]
    )

    if create_calls == 0:

        return (
            "CREATE_OUTCOME_NOT_EXECUTED",
            "The resolved production entrypoint did not reach create_outcome().",
            "Resolve the runtime condition or production caller path that reaches create_outcome().",
        )

    if future_calls == 0 and sites:

        return (
            "CREATE_OUTCOME_EXECUTED_FIND_FUTURE_PRICE_NOT_REACHED",
            "create_outcome() executed, but find_future_price() was not reached.",
            "Trace the internal branch/path inside create_outcome().",
        )

    if future_calls > 0:

        return (
            "FIND_FUTURE_PRICE_RUNTIME_REACHED",
            "The production runtime reached find_future_price() through the resolved call chain.",
            "Trace find_future_price inputs, output, and downstream assignment.",
        )

    return (
        "RUNTIME_CALL_CHAIN_PARTIALLY_OBSERVED",
        "A runtime call-chain segment was observed but the downstream target was not reached.",
        "Continue tracing the unresolved runtime branch.",
    )


def final_summary(sites):
    section(
        "STEP 9 — FINAL FORENSIC SUMMARY"
    )

    create_calls = len(
        runtime_calls[TARGET_FUNCTION]
    )

    future_calls = len(
        runtime_calls[SECONDARY_FUNCTION]
    )

    create_returns = len(
        runtime_returns[TARGET_FUNCTION]
    )

    future_returns = len(
        runtime_returns[SECONDARY_FUNCTION]
    )

    status, meaning, next_frontier = (
        determine_status(sites)
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"SECONDARY FUNCTION          : "
        f"{SECONDARY_FUNCTION}"
    )

    print(
        f"STATIC CALL SITES           : "
        f"{len(sites)}"
    )

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{create_calls}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{create_returns}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{future_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{future_returns}"
    )

    print(
        f"RUNTIME SQL EVENTS          : "
        f"{len(runtime_sql)}"
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
        "Original production functions were executed unchanged."
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


def main():
    started = time.perf_counter()

    section(
        "ARUNDA SIGNAL OUTCOME RUNTIME CALL CHAIN TRACE "
        "FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                         : READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                       : "
        "signal_outcome_engine.py -> create_outcome()"
    )

    print(
        "SECONDARY TARGET             : "
        "find_future_price()"
    )

    print(
        "PRODUCTION EXECUTION         : "
        "CONTROLLED READ-ONLY TRACE"
    )

    print(
        "DATABASE WRITE               : "
        "BLOCKED"
    )

    try:

        verify_paths()

        tree = inspect_target_source()

        sites = resolve_direct_call_sites(
            tree
        )

        static_call_sites.extend(
            sites
        )

        print_static_trace(
            sites
        )

        module = import_target_module()

        install_runtime_wrappers(
            module
        )

        invoke_production_entrypoint(
            module
        )

        print_runtime_inventory()

        final_summary(
            sites
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
            "DATABASE WRITE OPERATIONS   : NONE"
        )

        print(
            "PRODUCTION DB WRITE         : BLOCKED"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )