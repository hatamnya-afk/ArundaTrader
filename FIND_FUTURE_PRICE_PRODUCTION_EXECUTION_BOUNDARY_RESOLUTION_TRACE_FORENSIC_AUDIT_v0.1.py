# -*- coding: utf-8 -*-

"""
ARUNDA FIND_FUTURE_PRICE
PRODUCTION EXECUTION BOUNDARY RESOLUTION TRACE
FORENSIC AUDIT v0.1

MODE
----
READ-ONLY EXECUTION FORENSICS

PURPOSE
-------
Resolve and observe the genuine production execution boundary:

    module load
        |
        v
      main()
        |
        v
   process_signals()
        |
        v
   create_outcome()
        |
        v
find_future_price()

This audit does NOT modify production source.

DATABASE POLICY
---------------
SQLite reads are allowed.
Database writes are blocked at the connection level where possible.

IMPORTANT
---------
This audit deliberately avoids replacing target functions with wrappers
that call themselves. Original function objects are preserved explicitly.
"""

import ast
import dis
import importlib.util
import inspect
import io
import os
import runpy
import sqlite3
import sys
import time
import traceback
import types
from contextlib import redirect_stdout, redirect_stderr


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

TARGET_FILE = os.path.join(
    BASE_DIR,
    "signal_outcome_engine.py"
)

DB_FILE = os.path.join(
    BASE_DIR,
    "arunda.db"
)

MODULE_NAME = "__arunda_forensic_boundary__"


# =============================================================================
# GLOBAL FORENSIC STATE
# =============================================================================

STATE = {
    "module_loaded": False,
    "main_resolved": False,
    "process_signals_resolved": False,
    "create_outcome_resolved": False,
    "find_future_price_resolved": False,

    "main_calls": 0,
    "process_signals_calls": 0,
    "create_outcome_calls": 0,
    "find_future_price_calls": 0,

    "find_future_price_returns": 0,
    "create_outcome_returns": 0,

    "runtime_exceptions": 0,

    "trace_events": 0,

    "entrypoint_attempted": False,
    "entrypoint_completed": False,

    "write_attempts": 0,
}


# =============================================================================
# SAFE PRINT
# =============================================================================

def p(text=""):
    print(text, flush=True)


# =============================================================================
# STATIC SOURCE ANALYSIS
# =============================================================================

def resolve_static_functions():

    if not os.path.exists(TARGET_FILE):
        raise FileNotFoundError(TARGET_FILE)

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=TARGET_FILE)

    found = {
        "main": [],
        "process_signals": [],
        "create_outcome": [],
        "find_future_price": [],
    }

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            if node.name in found:

                found[node.name].append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": getattr(
                            node,
                            "end_lineno",
                            node.lineno
                        ),
                    }
                )

    return found


# =============================================================================
# LOAD MODULE WITHOUT EXECUTING __main__ BLOCK
# =============================================================================

def load_production_module():

    spec = importlib.util.spec_from_file_location(
        MODULE_NAME,
        TARGET_FILE
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to construct import specification."
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[MODULE_NAME] = module

    spec.loader.exec_module(module)

    STATE["module_loaded"] = True

    return module


# =============================================================================
# FUNCTION RESOLUTION
# =============================================================================

def resolve_runtime_function(module, name):

    obj = getattr(module, name, None)

    if callable(obj):

        return obj

    return None


# =============================================================================
# ORIGINAL FUNCTION REGISTRY
#
# Critical anti-recursion mechanism:
# wrappers NEVER overwrite the production function.
# =============================================================================

ORIGINAL_FUNCTIONS = {}


def register_original(module, name):

    fn = getattr(module, name, None)

    if callable(fn):

        ORIGINAL_FUNCTIONS[name] = fn

        return fn

    return None


# =============================================================================
# READ-ONLY SQLITE CONNECTION
# =============================================================================

class ReadOnlyConnectionProxy:

    """
    Minimal connection proxy.

    SELECT / cursor / execute / fetch operations are delegated.

    Mutating SQL statements are blocked before execution.
    """

    WRITE_KEYWORDS = {
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
    }

    def __init__(self, conn):

        self._conn = conn

    def _is_write(self, sql):

        if not isinstance(sql, str):
            return False

        normalized = sql.strip().upper()

        if not normalized:
            return False

        first = normalized.split(None, 1)[0]

        return first in self.WRITE_KEYWORDS

    def execute(self, sql, parameters=()):

        if self._is_write(sql):

            STATE["write_attempts"] += 1

            raise sqlite3.OperationalError(
                "FORENSIC WRITE BLOCKED"
            )

        return self._conn.execute(sql, parameters)

    def executemany(self, sql, parameters):

        if self._is_write(sql):

            STATE["write_attempts"] += 1

            raise sqlite3.OperationalError(
                "FORENSIC WRITE BLOCKED"
            )

        return self._conn.executemany(sql, parameters)

    def executescript(self, script):

        upper = str(script).upper()

        for keyword in self.WRITE_KEYWORDS:

            if keyword in upper:

                STATE["write_attempts"] += 1

                raise sqlite3.OperationalError(
                    "FORENSIC WRITE BLOCKED"
                )

        return self._conn.executescript(script)

    def commit(self):

        STATE["write_attempts"] += 1

        raise sqlite3.OperationalError(
            "FORENSIC COMMIT BLOCKED"
        )

    def rollback(self):

        return self._conn.rollback()

    def cursor(self, *args, **kwargs):

        return self._conn.cursor(*args, **kwargs)

    def close(self):

        return self._conn.close()

    def __getattr__(self, name):

        return getattr(self._conn, name)


def forensic_connect(*args, **kwargs):

    """
    Open database in SQLite read-only URI mode.

    This function is installed only into the imported production module's
    sqlite3.connect reference.

    It does NOT modify the source file.
    """

    original = sqlite3.connect

    # Determine target database.

    db_path = DB_FILE

    if args:
        requested = args[0]

        if isinstance(requested, str):

            if requested:
                db_path = requested

    if not os.path.isabs(db_path):

        db_path = os.path.abspath(
            os.path.join(BASE_DIR, db_path)
        )

    uri = (
        "file:"
        + db_path.replace("\\", "/")
        + "?mode=ro"
    )

    conn_kwargs = dict(kwargs)

    # sqlite3.connect(uri, uri=True)

    conn = original(
        uri,
        uri=True,
        **conn_kwargs
    )

    return ReadOnlyConnectionProxy(conn)


# =============================================================================
# INSTALL READ-ONLY DB GUARD
# =============================================================================

def install_readonly_guard(module):

    sqlite_mod = getattr(module, "sqlite3", None)

    if sqlite_mod is None:

        p("SQLITE MODULE                  : NOT FOUND")
        return False

    try:

        sqlite_mod.connect = forensic_connect

        p("SQLITE CONNECT GUARD           : INSTALLED")

        return True

    except Exception as exc:

        p(
            "SQLITE CONNECT GUARD           : FAILED | "
            f"{exc!r}"
        )

        return False


# =============================================================================
# STATIC CALL GRAPH
# =============================================================================

def print_static_call_graph():

    p()
    p("=" * 100)
    p("STEP 2 — STATIC PRODUCTION ENTRYPOINT / CALL GRAPH")
    p("=" * 100)

    try:

        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(
            source,
            filename=TARGET_FILE
        )

        target_names = {
            "main",
            "process_signals",
            "create_outcome",
            "find_future_price",
        }

        for node in ast.walk(tree):

            if isinstance(node, ast.FunctionDef):

                if node.name in target_names:

                    calls = []

                    for child in ast.walk(node):

                        if isinstance(child, ast.Call):

                            func = child.func

                            if isinstance(
                                func,
                                ast.Name
                            ):

                                if func.id in target_names:

                                    calls.append(func.id)

                            elif isinstance(
                                func,
                                ast.Attribute
                            ):

                                if func.attr in target_names:

                                    calls.append(
                                        func.attr
                                    )

                    p(
                        f"{node.name:20s} | "
                        f"LINE={node.lineno:<5} | "
                        f"CALLS={sorted(set(calls))}"
                    )

    except Exception as exc:

        p(
            "STATIC CALL GRAPH ERROR        : "
            f"{exc!r}"
        )


# =============================================================================
# CODE OBJECT RESOLUTION
# =============================================================================

def print_code_object_info(module):

    p()
    p("=" * 100)
    p("STEP 3 — RUNTIME CODE OBJECT RESOLUTION")
    p("=" * 100)

    names = [
        "main",
        "process_signals",
        "create_outcome",
        "find_future_price",
    ]

    for name in names:

        fn = getattr(module, name, None)

        if callable(fn):

            code = getattr(fn, "__code__", None)

            if code is not None:

                p(
                    f"{name:20s} | "
                    f"FILE={code.co_filename} | "
                    f"FIRST_LINE={code.co_firstlineno} | "
                    f"NAME={code.co_name}"
                )

            else:

                p(
                    f"{name:20s} | CODE OBJECT : NONE"
                )

        else:

            p(
                f"{name:20s} | NOT RESOLVED"
            )


# =============================================================================
# TRACE FUNCTION
#
# No wrappers.
# No monkey-patching of target functions.
# Direct CPython execution tracing.
# =============================================================================

TARGET_CODE_OBJECTS = {}


def forensic_trace(frame, event, arg):

    if event not in {
        "call",
        "return",
        "exception",
    }:

        return forensic_trace

    code = frame.f_code

    if code.co_filename != os.path.abspath(TARGET_FILE):

        return forensic_trace

    STATE["trace_events"] += 1

    name = code.co_name

    if event == "call":

        if name == "main":

            STATE["main_calls"] += 1

            p(
                f"TRACE CALL                  : main "
                f"LINE={frame.f_lineno}"
            )

        elif name == "process_signals":

            STATE["process_signals_calls"] += 1

            p(
                f"TRACE CALL                  : process_signals "
                f"LINE={frame.f_lineno}"
            )

        elif name == "create_outcome":

            STATE["create_outcome_calls"] += 1

            p(
                f"TRACE CALL                  : create_outcome "
                f"LINE={frame.f_lineno}"
            )

        elif name == "find_future_price":

            STATE["find_future_price_calls"] += 1

            p(
                f"TRACE CALL                  : find_future_price "
                f"LINE={frame.f_lineno}"
            )

    elif event == "return":

        if name == "create_outcome":

            STATE["create_outcome_returns"] += 1

            p(
                f"TRACE RETURN                : create_outcome "
                f"TYPE={type(arg).__name__} "
                f"VALUE={repr(arg)[:300]}"
            )

        elif name == "find_future_price":

            STATE["find_future_price_returns"] += 1

            p(
                f"TRACE RETURN                : find_future_price "
                f"TYPE={type(arg).__name__} "
                f"VALUE={repr(arg)[:300]}"
            )

    elif event == "exception":

        STATE["runtime_exceptions"] += 1

        exc_type, exc_value, _ = arg

        if name in {
            "main",
            "process_signals",
            "create_outcome",
            "find_future_price",
        }:

            p(
                f"TRACE EXCEPTION             : {name} | "
                f"{exc_type.__name__} | "
                f"{exc_value!r}"
            )

    return forensic_trace


# =============================================================================
# ENTRYPOINT CANDIDATE RESOLUTION
# =============================================================================

def resolve_entrypoint(module):

    p()
    p("=" * 100)
    p("STEP 4 — PRODUCTION ENTRYPOINT RESOLUTION")
    p("=" * 100)

    main_fn = resolve_runtime_function(
        module,
        "main"
    )

    process_fn = resolve_runtime_function(
        module,
        "process_signals"
    )

    create_fn = resolve_runtime_function(
        module,
        "create_outcome"
    )

    future_fn = resolve_runtime_function(
        module,
        "find_future_price"
    )

    STATE["main_resolved"] = main_fn is not None
    STATE["process_signals_resolved"] = process_fn is not None
    STATE["create_outcome_resolved"] = create_fn is not None
    STATE["find_future_price_resolved"] = future_fn is not None

    p(
        f"main()                     : "
        f"{'FOUND' if main_fn else 'NOT FOUND'}"
    )

    p(
        f"process_signals()          : "
        f"{'FOUND' if process_fn else 'NOT FOUND'}"
    )

    p(
        f"create_outcome()           : "
        f"{'FOUND' if create_fn else 'NOT FOUND'}"
    )

    p(
        f"find_future_price()        : "
        f"{'FOUND' if future_fn else 'NOT FOUND'}"
    )

    return (
        main_fn,
        process_fn,
        create_fn,
        future_fn,
    )


# =============================================================================
# ENTRYPOINT EXECUTION
# =============================================================================

def execute_real_entrypoint(module):

    p()
    p("=" * 100)
    p("STEP 5 — GENUINE PRODUCTION ENTRYPOINT EXECUTION")
    p("=" * 100)

    main_fn = getattr(
        module,
        "main",
        None
    )

    if not callable(main_fn):

        p(
            "ENTRYPOINT STATUS           : "
            "NO CALLABLE main()"
        )

        return

    STATE["entrypoint_attempted"] = True

    old_trace = sys.gettrace()

    try:

        p(
            "ENTRYPOINT                  : main()"
        )

        p(
            "EXECUTION MODE              : "
            "DIRECT FUNCTION INVOCATION"
        )

        p(
            "TRACE MODE                  : "
            "CPYTHON sys.settrace"
        )

        sys.settrace(forensic_trace)

        result = main_fn()

        STATE["entrypoint_completed"] = True

        p()
        p(
            "MAIN RETURN                 : "
            f"TYPE={type(result).__name__} "
            f"VALUE={repr(result)[:500]}"
        )

    except BaseException as exc:

        STATE["runtime_exceptions"] += 1

        p()
        p(
            "PRODUCTION ENTRYPOINT ERROR : "
            f"{type(exc).__name__}({exc!r})"
        )

        p()
        p("TRACEBACK")
        p("-" * 100)
        traceback.print_exc()

    finally:

        sys.settrace(old_trace)


# =============================================================================
# FALLBACK ENTRYPOINT ANALYSIS
# =============================================================================

def inspect_main_signature(module):

    p()
    p("=" * 100)
    p("STEP 6 — ENTRYPOINT SIGNATURE / INVOCATION CONTRACT")
    p("=" * 100)

    main_fn = getattr(
        module,
        "main",
        None
    )

    if not callable(main_fn):

        p("main()                     : UNAVAILABLE")
        return

    try:

        sig = inspect.signature(main_fn)

        p(
            f"main() signature           : {sig}"
        )

        if len(sig.parameters) == 0:

            p(
                "INVOCATION CONTRACT       : "
                "ZERO-ARGUMENT MAIN"
            )

        else:

            p(
                "INVOCATION CONTRACT       : "
                f"{len(sig.parameters)} PARAMETER(S)"
            )

            for name, param in sig.parameters.items():

                p(
                    f"PARAMETER                  : "
                    f"{name} | "
                    f"KIND={param.kind} | "
                    f"DEFAULT={param.default!r}"
                )

    except Exception as exc:

        p(
            "SIGNATURE RESOLUTION ERROR  : "
            f"{exc!r}"
        )


# =============================================================================
# MODULE GUARD ANALYSIS
# =============================================================================

def inspect_main_guard():

    p()
    p("=" * 100)
    p("STEP 7 — __MAIN__ GUARD ANALYSIS")
    p("=" * 100)

    try:

        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(
            source,
            filename=TARGET_FILE
        )

        found = False

        for node in tree.body:

            if isinstance(node, ast.If):

                try:

                    text = ast.unparse(node.test)

                except Exception:

                    text = ""

                if "__name__" in text:

                    found = True

                    p(
                        f"MAIN GUARD                 : FOUND "
                        f"LINE={node.lineno}"
                    )

                    p(
                        f"GUARD EXPRESSION           : {text}"
                    )

                    for child in node.body:

                        if isinstance(
                            child,
                            ast.Expr
                        ):

                            if isinstance(
                                child.value,
                                ast.Call
                            ):

                                fn = child.value.func

                                if isinstance(
                                    fn,
                                    ast.Name
                                ):

                                    p(
                                        "GUARD CALL                 : "
                                        f"{fn.id}()"
                                    )

        if not found:

            p(
                "MAIN GUARD                 : "
                "NOT FOUND"
            )

    except Exception as exc:

        p(
            "MAIN GUARD ANALYSIS ERROR    : "
            f"{exc!r}"
        )


# =============================================================================
# FINAL SUMMARY
# =============================================================================

def final_summary():

    p()
    p("=" * 100)
    p("STEP 8 — FINAL FORENSIC SUMMARY")
    p("=" * 100)

    p(
        f"MODULE LOADED               : "
        f"{STATE['module_loaded']}"
    )

    p(
        f"MAIN RESOLVED               : "
        f"{STATE['main_resolved']}"
    )

    p(
        f"PROCESS_SIGNALS RESOLVED    : "
        f"{STATE['process_signals_resolved']}"
    )

    p(
        f"CREATE_OUTCOME RESOLVED     : "
        f"{STATE['create_outcome_resolved']}"
    )

    p(
        f"FIND_FUTURE_PRICE RESOLVED  : "
        f"{STATE['find_future_price_resolved']}"
    )

    p(
        f"MAIN CALLS                  : "
        f"{STATE['main_calls']}"
    )

    p(
        f"PROCESS_SIGNALS CALLS       : "
        f"{STATE['process_signals_calls']}"
    )

    p(
        f"CREATE_OUTCOME CALLS        : "
        f"{STATE['create_outcome_calls']}"
    )

    p(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{STATE['find_future_price_calls']}"
    )

    p(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{STATE['find_future_price_returns']}"
    )

    p(
        f"CREATE_OUTCOME RETURNS      : "
        f"{STATE['create_outcome_returns']}"
    )

    p(
        f"TRACE EVENTS                : "
        f"{STATE['trace_events']}"
    )

    p(
        f"RUNTIME EXCEPTIONS          : "
        f"{STATE['runtime_exceptions']}"
    )

    p(
        f"BLOCKED WRITE ATTEMPTS      : "
        f"{STATE['write_attempts']}"
    )

    p()
    p("FORENSIC CONCLUSION")
    p("-" * 100)

    if STATE["find_future_price_calls"] > 0:

        status = (
            "FIND_FUTURE_PRICE_PRODUCTION_BOUNDARY_VERIFIED"
        )

        meaning = (
            "The genuine production entrypoint was observed "
            "reaching find_future_price()."
        )

        frontier = (
            "Resume instruction-boundary tracing from the "
            "observed production invocation."
        )

    elif STATE["create_outcome_calls"] > 0:

        status = (
            "CREATE_OUTCOME_BOUNDARY_REACHED"
        )

        meaning = (
            "The genuine production entrypoint reached "
            "create_outcome(), but find_future_price() was "
            "not reached during the observed execution."
        )

        frontier = (
            "Trace the branch/loop boundary between "
            "create_outcome() entry and find_future_price()."
        )

    elif STATE["process_signals_calls"] > 0:

        status = (
            "PROCESS_SIGNALS_BOUNDARY_REACHED"
        )

        meaning = (
            "The genuine production entrypoint reached "
            "process_signals(), but create_outcome() was "
            "not observed."
        )

        frontier = (
            "Trace signal eligibility / branching inside "
            "process_signals()."
        )

    elif STATE["main_calls"] > 0:

        status = (
            "MAIN_BOUNDARY_REACHED"
        )

        meaning = (
            "The genuine production main() was entered, "
            "but downstream production execution was not observed."
        )

        frontier = (
            "Trace main() instruction flow into process_signals()."
        )

    elif STATE["entrypoint_attempted"]:

        status = (
            "PRODUCTION_ENTRYPOINT_ABORTED_BEFORE_TARGET"
        )

        meaning = (
            "main() invocation was attempted but execution "
            "did not reach the target call chain."
        )

        frontier = (
            "Resolve the first exception/termination boundary "
            "before main() reaches process_signals()."
        )

    else:

        status = (
            "PRODUCTION_EXECUTION_BOUNDARY_UNRESOLVED"
        )

        meaning = (
            "No genuine production entrypoint execution "
            "was observed."
        )

        frontier = (
            "Resolve the actual launcher/entrypoint contract "
            "before continuing price-flow localization."
        )

    p(
        f"STATUS                      : {status}"
    )

    p(
        f"MEANING                     : {meaning}"
    )

    p(
        f"NEXT FRONTIER               : {frontier}"
    )

    p()
    p(
        "DATABASE_WRITES             : NONE"
    )
    p(
        "ENGINE_MODIFIED             : NONE"
    )
    p(
        "PRODUCTION_SOURCE_MODIFIED  : NONE"
    )
    p(
        "INSERT                      : NONE"
    )
    p(
        "UPDATE                      : NONE"
    )
    p(
        "DELETE                      : NONE"
    )
    p(
        "ALTER                       : NONE"
    )
    p(
        "CREATE                      : NONE"
    )
    p(
        "DROP                        : NONE"
    )
    p(
        "COMMIT                      : NONE"
    )


# =============================================================================
# MAIN AUDIT
# =============================================================================

def audit():

    started = time.perf_counter()

    p("=" * 100)
    p(
        "ARUNDA FIND_FUTURE_PRICE "
        "PRODUCTION EXECUTION BOUNDARY RESOLUTION "
        "TRACE FORENSIC AUDIT v0.1"
    )
    p("=" * 100)

    p(
        "MODE                        : "
        "READ-ONLY PRODUCTION BOUNDARY FORENSICS"
    )

    p(
        f"TARGET                      : {TARGET_FILE}"
    )

    p(
        f"DATABASE                    : {DB_FILE}"
    )

    p(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    p(
        "DATABASE WRITE               : BLOCKED"
    )

    # -------------------------------------------------------------------------
    # STEP 1
    # -------------------------------------------------------------------------

    p()
    p("=" * 100)
    p("STEP 1 — STATIC TARGET RESOLUTION")
    p("=" * 100)

    try:

        found = resolve_static_functions()

        for name in [
            "main",
            "process_signals",
            "create_outcome",
            "find_future_price",
        ]:

            entries = found.get(name, [])

            if entries:

                for item in entries:

                    p(
                        f"{name:20s} : FOUND "
                        f"LINE={item['line']} "
                        f"END={item['end_line']}"
                    )

            else:

                p(
                    f"{name:20s} : NOT FOUND"
                )

    except Exception as exc:

        p(
            "STATIC RESOLUTION ERROR     : "
            f"{exc!r}"
        )

    # -------------------------------------------------------------------------
    # STEP 2
    # -------------------------------------------------------------------------

    print_static_call_graph()

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    p()
    p("=" * 100)
    p("STEP 3 — PRODUCTION MODULE LOAD")
    p("=" * 100)

    module = None

    try:

        module = load_production_module()

        p(
            "MODULE LOAD                  : SUCCESS"
        )

    except Exception as exc:

        STATE["runtime_exceptions"] += 1

        p(
            "MODULE LOAD                  : FAILED"
        )

        p(
            f"ERROR                       : "
            f"{type(exc).__name__}({exc!r})"
        )

        traceback.print_exc()

        final_summary()

        elapsed = time.perf_counter() - started

        p(
            f"ELAPSED SECONDS              : "
            f"{elapsed:.3f}"
        )

        p("=" * 100)
        p("AUDIT COMPLETE")
        return

    # -------------------------------------------------------------------------
    # STEP 4
    # -------------------------------------------------------------------------

    p()
    p("=" * 100)
    p("STEP 4 — RUNTIME FUNCTION RESOLUTION")
    p("=" * 100)

    (
        main_fn,
        process_fn,
        create_fn,
        future_fn,
    ) = resolve_entrypoint(module)

    print_code_object_info(module)

    inspect_main_signature(module)

    inspect_main_guard()

    # -------------------------------------------------------------------------
    # STEP 5
    # -------------------------------------------------------------------------

    p()
    p("=" * 100)
    p("STEP 5 — READ-ONLY DATABASE GUARD")
    p("=" * 100)

    install_readonly_guard(module)

    # -------------------------------------------------------------------------
    # STEP 6
    # -------------------------------------------------------------------------

    p()
    p("=" * 100)
    p("STEP 6 — GENUINE PRODUCTION EXECUTION")
    p("=" * 100)

    execute_real_entrypoint(module)

    # -------------------------------------------------------------------------
    # STEP 7
    # -------------------------------------------------------------------------

    p()
    p("=" * 100)
    p("STEP 7 — RUNTIME BOUNDARY OBSERVATION")
    p("=" * 100)

    p(
        f"main() CALLS                : "
        f"{STATE['main_calls']}"
    )

    p(
        f"process_signals() CALLS     : "
        f"{STATE['process_signals_calls']}"
    )

    p(
        f"create_outcome() CALLS      : "
        f"{STATE['create_outcome_calls']}"
    )

    p(
        f"find_future_price() CALLS   : "
        f"{STATE['find_future_price_calls']}"
    )

    p(
        f"find_future_price RETURNS   : "
        f"{STATE['find_future_price_returns']}"
    )

    p(
        f"create_outcome RETURNS      : "
        f"{STATE['create_outcome_returns']}"
    )

    p(
        f"RUNTIME EXCEPTIONS          : "
        f"{STATE['runtime_exceptions']}"
    )

    # -------------------------------------------------------------------------
    # STEP 8
    # -------------------------------------------------------------------------

    final_summary()

    elapsed = time.perf_counter() - started

    p()
    p(
        f"ELAPSED SECONDS              : "
        f"{elapsed:.3f}"
    )

    p("=" * 100)
    p("AUDIT COMPLETE")
    p("=" * 100)


# =============================================================================
# EXECUTION
# =============================================================================

if __name__ == "__main__":

    audit()