# -*- coding: utf-8 -*-

import os
import sys
import ast
import sqlite3
import runpy
import traceback
import time


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(PROJECT_DIR, "signal_outcome_engine.py")
DB_FILE = os.path.join(PROJECT_DIR, "arunda.db")

CREATE_NAME = "create_outcome"
FUTURE_NAME = "find_future_price"

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


# =============================================================================
# STATE
# =============================================================================

STATE = {
    "create_calls": 0,
    "create_returns": 0,
    "future_calls": 0,
    "future_returns": 0,
    "runtime_exceptions": 0,

    "future_values": [],
    "create_return_values": [],

    "price_values": [],
    "prices_values": [],
    "returns_values": [],
    "outcomes_values": [],

    "blocked_writes": 0,

    "source_modified": False,

    "trace_events": 0,
}


# =============================================================================
# SAFE HELPERS
# =============================================================================

def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<unrepresentable>"

    if len(text) > limit:
        return text[:limit] + "...<truncated>"

    return text


def safe_type(value):
    try:
        return type(value).__name__
    except Exception:
        return "<unknown>"


# =============================================================================
# STATIC RESOLUTION
# =============================================================================

def static_resolution():
    print("=" * 100)
    print("STEP 1 — STATIC TARGET RESOLUTION")
    print("=" * 100)

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=TARGET_FILE)

    create_node = None
    future_node = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == CREATE_NAME:
                create_node = node
            elif node.name == FUTURE_NAME:
                future_node = node

    if create_node is None:
        raise RuntimeError("create_outcome() not found")

    if future_node is None:
        raise RuntimeError("find_future_price() not found")

    call_sites = []

    for node in ast.walk(create_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == FUTURE_NAME:
                    call_sites.append(node)

    print(f"TARGET FILE              : {TARGET_FILE}")
    print(f"CREATE_OUTCOME           : FOUND")
    print(f"FIND_FUTURE_PRICE        : FOUND")
    print(f"CALL SITES               : {len(call_sites)}")

    for node in call_sites:
        print(
            f"CALL SITE                : "
            f"LINE={node.lineno} COL={node.col_offset}"
        )

    print()
    print("CREATE_OUTCOME ASSIGNMENT MAP")
    print("-" * 100)

    for node in ast.walk(create_node):

        if not isinstance(node, ast.Assign):
            continue

        targets = []

        for target in node.targets:
            try:
                targets.append(ast.unparse(target))
            except Exception:
                targets.append("<target>")

        try:
            value_text = ast.unparse(node.value)
        except Exception:
            value_text = "<expression>"

        value_text = " ".join(value_text.split())

        print(
            f"LINE={node.lineno:<5} | "
            f"TARGET={','.join(targets):<30} | "
            f"VALUE={value_text}"
        )

    return source


# =============================================================================
# ROW COMPATIBILITY
# =============================================================================

class CompatibleCursor:
    """
    Cursor proxy preserving sqlite3.Row behaviour.

    Production code may expect:

        row["snapshot_id"]

    Therefore fetchone/fetchall must return sqlite3.Row,
    not raw tuples.
    """

    def __init__(self, real_cursor):
        self._cursor = real_cursor

    def execute(self, sql, parameters=()):
        sql_text = str(sql).strip()
        upper = sql_text.upper()

        if any(upper.startswith(x) for x in WRITE_PREFIXES):
            STATE["blocked_writes"] += 1
            return NeutralizedResult()

        self._cursor.execute(sql, parameters)
        return self

    def executemany(self, sql, parameters=()):
        sql_text = str(sql).strip()
        upper = sql_text.upper()

        if any(upper.startswith(x) for x in WRITE_PREFIXES):
            STATE["blocked_writes"] += 1
            return NeutralizedResult()

        self._cursor.executemany(sql, parameters)
        return self

    def executescript(self, script):
        STATE["blocked_writes"] += 1
        return NeutralizedResult()

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size=None):
        if size is None:
            return self._cursor.fetchmany()
        return self._cursor.fetchmany(size)

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class NeutralizedResult:
    rowcount = 0
    lastrowid = None

    def fetchone(self):
        return None

    def fetchmany(self, size=None):
        return []

    def fetchall(self):
        return []

    def close(self):
        return None


# =============================================================================
# CONNECTION PROXY
# =============================================================================

class CompatibleConnection:
    def __init__(self, real_connection):
        self._conn = real_connection

    def cursor(self, *args, **kwargs):
        return CompatibleCursor(
            self._conn.cursor(*args, **kwargs)
        )

    def execute(self, sql, parameters=()):
        cursor = CompatibleCursor(
            self._conn.cursor()
        )

        cursor.execute(sql, parameters)

        return cursor

    def executemany(self, sql, parameters=()):
        cursor = CompatibleCursor(
            self._conn.cursor()
        )

        cursor.executemany(sql, parameters)

        return cursor

    def executescript(self, script):
        STATE["blocked_writes"] += 1
        return NeutralizedResult()

    def commit(self):
        STATE["blocked_writes"] += 1
        return None

    def rollback(self):
        return None

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __getattr__(self, name):
        return getattr(self._conn, name)


_ORIGINAL_CONNECT = sqlite3.connect


def forensic_connect(database, *args, **kwargs):
    """
    Open production DB read-only while preserving sqlite3.Row behaviour.

    The key compatibility point is:

        conn.row_factory = sqlite3.Row

    so production expressions such as row["field"] remain valid.
    """

    db_path = os.path.abspath(str(database))

    uri = (
        "file:"
        + db_path.replace("\\", "/")
        + "?mode=ro"
    )

    conn = _ORIGINAL_CONNECT(
        uri,
        uri=True,
    )

    # CRITICAL:
    # Preserve dictionary-like row access expected by production.
    conn.row_factory = sqlite3.Row

    return CompatibleConnection(conn)


# =============================================================================
# FRAME TRACE
# =============================================================================

def trace_function(frame, event, arg):

    try:
        filename = os.path.abspath(frame.f_code.co_filename)

        if filename != os.path.abspath(TARGET_FILE):
            return trace_function

        function_name = frame.f_code.co_name

        STATE["trace_events"] += 1

        # ---------------------------------------------------------------------
        # CREATE_OUTCOME
        # ---------------------------------------------------------------------

        if function_name == CREATE_NAME:

            if event == "call":

                STATE["create_calls"] += 1

                return trace_function

            if event == "line":

                local_vars = frame.f_locals

                if "price" in local_vars:
                    STATE["price_values"].append(
                        (
                            frame.f_lineno,
                            local_vars["price"],
                        )
                    )

                if "prices" in local_vars:
                    STATE["prices_values"].append(
                        (
                            frame.f_lineno,
                            local_vars["prices"],
                        )
                    )

                if "returns" in local_vars:
                    STATE["returns_values"].append(
                        (
                            frame.f_lineno,
                            local_vars["returns"],
                        )
                    )

                if "outcomes" in local_vars:
                    STATE["outcomes_values"].append(
                        (
                            frame.f_lineno,
                            local_vars["outcomes"],
                        )
                    )

                return trace_function

            if event == "return":

                STATE["create_returns"] += 1

                STATE["create_return_values"].append(
                    {
                        "number": STATE["create_returns"],
                        "value": arg,
                    }
                )

                return trace_function

        # ---------------------------------------------------------------------
        # FIND_FUTURE_PRICE
        # ---------------------------------------------------------------------

        if function_name == FUTURE_NAME:

            if event == "call":

                STATE["future_calls"] += 1

                return trace_function

            if event == "return":

                STATE["future_returns"] += 1

                STATE["future_values"].append(
                    {
                        "number": STATE["future_returns"],
                        "value": arg,
                        "type": safe_type(arg),
                    }
                )

                return trace_function

    except Exception:
        return trace_function

    return trace_function


# =============================================================================
# PRODUCTION EXECUTION
# =============================================================================

def execute_runtime():

    print("=" * 100)
    print("STEP 2 — ROW-COMPATIBLE WRITE-NEUTRALIZED RUNTIME")
    print("=" * 100)

    print("Production source mutation : NONE")
    print("Database writes            : BLOCKED")
    print("SQLite SELECT              : ALLOWED")
    print("sqlite3.Row compatibility : ENABLED")
    print("COMMIT                     : NEUTRALIZED")
    print()

    old_connect = sqlite3.connect
    old_trace = sys.gettrace()

    try:

        sqlite3.connect = forensic_connect

        sys.settrace(trace_function)

        namespace = runpy.run_path(
            TARGET_FILE,
            run_name="__arunda_forensic_runtime__",
        )

        main_func = namespace.get("main")

        if not callable(main_func):
            raise RuntimeError(
                "Production main() was not found."
            )

        main_func()

    except Exception as exc:

        STATE["runtime_exceptions"] += 1

        print("=" * 100)
        print("PRODUCTION RUNTIME ERROR")
        print("=" * 100)
        print(
            f"{type(exc).__name__}({exc!r})"
        )
        print()

    finally:

        sys.settrace(old_trace)
        sqlite3.connect = old_connect


# =============================================================================
# REPORT FUTURE VALUES
# =============================================================================

def report_future_values():

    print("=" * 100)
    print("STEP 3 — CAPTURED FUTURE PRICE RETURNS")
    print("=" * 100)

    if not STATE["future_values"]:
        print("NONE")
        return

    for item in STATE["future_values"]:

        print(
            f"{item['number']:03d} | "
            f"TYPE={item['type']} | "
            f"VALUE={safe_repr(item['value'])}"
        )


# =============================================================================
# PRICE LOCALIZATION
# =============================================================================

def report_price_flow():

    print()
    print("=" * 100)
    print("STEP 4 — CREATE_OUTCOME PRICE FLOW")
    print("=" * 100)

    if not STATE["future_values"]:
        print("NO FUTURE PRICE VALUES")
        return 0

    matches = 0

    for line, price in STATE["price_values"]:

        for future in STATE["future_values"]:

            try:
                same = (
                    price is future["value"]
                    or price == future["value"]
                )
            except Exception:
                same = False

            if same:

                matches += 1

                if matches <= 100:

                    print(
                        f"PRICE MATCH | "
                        f"RETURN={future['number']} | "
                        f"LINE={line} | "
                        f"VALUE={safe_repr(price)}"
                    )

    print()
    print(
        f"PRICE VARIABLE MATCHES : {matches}"
    )

    return matches


# =============================================================================
# FINAL STRUCTURE SEARCH
# =============================================================================

def find_paths(value, target, path="ROOT", depth=0, seen=None):

    if seen is None:
        seen = set()

    if depth > 15:
        return []

    try:
        if id(value) in seen:
            return []

        seen.add(id(value))
    except Exception:
        pass

    paths = []

    # Identity first.
    if value is target:
        paths.append(path)

    # Equality only for non-container scalar values.
    elif (
        not isinstance(value, (dict, list, tuple))
        and not isinstance(target, (dict, list, tuple))
    ):
        try:
            if value == target:
                paths.append(path)
        except Exception:
            pass

    if isinstance(value, dict):

        for key, child in value.items():

            child_path = (
                f"{path}[{safe_repr(key)}]"
            )

            paths.extend(
                find_paths(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    seen,
                )
            )

    elif isinstance(value, (list, tuple)):

        for index, child in enumerate(value):

            child_path = (
                f"{path}[{index}]"
            )

            paths.extend(
                find_paths(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    seen,
                )
            )

    return paths


def report_final_structure():

    print()
    print("=" * 100)
    print("STEP 5 — FINAL RETURN STRUCTURE")
    print("=" * 100)

    if not STATE["future_values"]:
        print("NO FUTURE PRICE RETURNS")
        return 0

    if not STATE["create_return_values"]:
        print("NO CREATE_OUTCOME RETURNS")
        return 0

    matches = 0

    for future in STATE["future_values"]:

        target = future["value"]

        for returned in STATE["create_return_values"]:

            paths = find_paths(
                returned["value"],
                target,
            )

            for path in paths:

                matches += 1

                print(
                    f"FINAL FIELD MATCH | "
                    f"FUTURE_RETURN={future['number']} | "
                    f"CREATE_RETURN={returned['number']} | "
                    f"PATH={path} | "
                    f"VALUE={safe_repr(target)}"
                )

    print()
    print(
        f"FINAL FIELD MATCHES : {matches}"
    )

    return matches


# =============================================================================
# SOURCE INTEGRITY
# =============================================================================

def verify_source(original_source):

    try:

        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            current = f.read()

        STATE["source_modified"] = (
            current != original_source
        )

    except Exception:

        STATE["source_modified"] = True


# =============================================================================
# FINAL SUMMARY
# =============================================================================

def final_summary(
    price_matches,
    final_matches,
):

    print()
    print("=" * 100)
    print("STEP 6 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{STATE['create_calls']}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{STATE['future_calls']}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{STATE['future_returns']}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{STATE['create_returns']}"
    )

    print(
        f"PRICE VARIABLE MATCHES      : "
        f"{price_matches}"
    )

    print(
        f"FINAL FIELD / PATH MATCHES  : "
        f"{final_matches}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{STATE['runtime_exceptions']}"
    )

    print(
        f"BLOCKED WRITE OPERATIONS    : "
        f"{STATE['blocked_writes']}"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if STATE["future_returns"] == 0:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The row-compatible write-neutralized runtime "
            "did not reach find_future_price()."
        )

        frontier = (
            "Resolve the production runtime boundary."
        )

    elif price_matches == 0:

        status = (
            "FIND_FUTURE_PRICE_RETURN_NOT_LOCALIZED"
        )

        meaning = (
            "The genuine future-price return was observed, "
            "but its price assignment was not localized."
        )

        frontier = (
            "Trace create_outcome() assignments at "
            "the frame-local boundary."
        )

    elif final_matches == 0:

        status = (
            "FIND_FUTURE_PRICE_FINAL_FIELD_NOT_LOCALIZED"
        )

        meaning = (
            "The genuine future-price return reached "
            "create_outcome().price, but exact final "
            "return-field localization remains unresolved."
        )

        frontier = (
            "Trace dictionary construction and return packing."
        )

    else:

        status = (
            "FIND_FUTURE_PRICE_FINAL_FIELD_LOCALIZED"
        )

        meaning = (
            "The genuine future-price return was followed "
            "through create_outcome().price into the final "
            "returned structure."
        )

        frontier = (
            "Verify exact value preservation versus transformation."
        )

    print(
        f"STATUS                      : {status}"
    )

    print(
        f"MEANING                     : {meaning}"
    )

    print(
        f"NEXT FRONTIER               : {frontier}"
    )

    print()
    print(
        "DATABASE_WRITES             : NONE"
    )

    print(
        "ENGINE_MODIFIED             : NONE"
    )

    print(
        "PRODUCTION_SOURCE_MODIFIED  : "
        f"{'YES' if STATE['source_modified'] else 'NONE'}"
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

    print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

def main():

    started = time.perf_counter()

    original_source = static_resolution()

    execute_runtime()

    report_future_values()

    price_matches = report_price_flow()

    final_matches = report_final_structure()

    verify_source(original_source)

    final_summary(
        price_matches,
        final_matches,
    )

    elapsed = time.perf_counter() - started

    print("=" * 100)
    print(
        f"ELAPSED SECONDS              : "
        f"{elapsed:.3f}"
    )
    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()