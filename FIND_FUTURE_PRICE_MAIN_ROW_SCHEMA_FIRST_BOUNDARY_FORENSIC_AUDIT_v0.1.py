import ast
import dis
import inspect
import sqlite3
import sys
import traceback
from pathlib import Path


# =============================================================================
# ARUNDA FIND_FUTURE_PRICE MAIN ROW SCHEMA FIRST BOUNDARY FORENSIC AUDIT v0.1
# =============================================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_FILE = BASE_DIR / "signal_outcome_engine.py"
DB_FILE = BASE_DIR / "arunda.db"

MODE = "READ-ONLY MAIN ROW / SCHEMA FIRST-BOUNDARY FORENSICS"


# =============================================================================
# GLOBAL FORENSIC STATE
# =============================================================================

main_calls = 0
process_calls = 0
create_calls = 0
future_calls = 0

runtime_exceptions = []

select_operations = 0
row_observations = 0
schema_observations = 0

first_main_exception = None
first_process_boundary = None

trace_events = 0

TARGET_FUNCTIONS = {
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
}


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def banner(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        text = text[:limit] + "...<truncated>"

    return text


# =============================================================================
# STATIC SOURCE RESOLUTION
# =============================================================================

def load_source():
    return TARGET_FILE.read_text(encoding="utf-8")


def static_function_map(source):
    tree = ast.parse(source)
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def find_main_boundary_nodes(source):
    tree = ast.parse(source)

    main_node = None

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_node = node
            break

    if main_node is None:
        return []

    observations = []

    for index, node in enumerate(main_node.body):
        observations.append({
            "index": index,
            "type": type(node).__name__,
            "line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None),
            "source": ast.get_source_segment(source, node),
        })

    return observations


# =============================================================================
# AST CALL / SUBSCRIPT ANALYSIS
# =============================================================================

def describe_expr(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse failed>"


def collect_main_pre_process_operations(source):
    tree = ast.parse(source)

    main_node = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_node = node
            break

    if main_node is None:
        return []

    observations = []

    for node in main_node.body:
        text = describe_expr(node)

        calls = []
        subscripts = []
        attributes = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                calls.append(describe_expr(child))

            elif isinstance(child, ast.Subscript):
                subscripts.append(describe_expr(child))

            elif isinstance(child, ast.Attribute):
                attributes.append(describe_expr(child))

        observations.append({
            "line": getattr(node, "lineno", None),
            "type": type(node).__name__,
            "source": text,
            "calls": calls,
            "subscripts": subscripts,
            "attributes": attributes,
        })

    return observations


# =============================================================================
# DISASSEMBLY
# =============================================================================

def disassemble_main(module):
    try:
        fn = getattr(module, "main", None)

        if fn is None:
            return []

        return list(dis.get_instructions(fn))

    except Exception:
        return []


def print_main_instructions(module):
    print("\nMAIN INSTRUCTION BOUNDARY")
    print("-" * 100)

    instructions = disassemble_main(module)

    for ins in instructions:
        print(
            f"OFFSET={ins.offset:<6} "
            f"LINE={str(ins.starts_line):<5} "
            f"OP={ins.opname:<28} "
            f"ARG={str(ins.arg):<6} "
            f"ARGVAL={safe_repr(ins.argval, 180)}"
        )


# =============================================================================
# READ-ONLY SQLITE CONNECTION
# =============================================================================

class ReadOnlyCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, parameters=()):
        global select_operations

        normalized = sql.strip().upper()

        if (
            normalized.startswith("INSERT")
            or normalized.startswith("UPDATE")
            or normalized.startswith("DELETE")
            or normalized.startswith("ALTER")
            or normalized.startswith("CREATE")
            or normalized.startswith("DROP")
            or normalized.startswith("REPLACE")
        ):
            raise sqlite3.OperationalError(
                "FORENSIC WRITE BLOCKED"
            )

        if normalized.startswith("SELECT") or normalized.startswith("PRAGMA"):
            select_operations += 1

        return self._cursor.execute(sql, parameters)

    def executemany(self, sql, parameters):
        raise sqlite3.OperationalError(
            "FORENSIC EXECUTEMANY BLOCKED"
        )

    def executescript(self, script):
        raise sqlite3.OperationalError(
            "FORENSIC SCRIPT EXECUTION BLOCKED"
        )

    def fetchone(self):
        global row_observations

        row = self._cursor.fetchone()

        if row is not None:
            row_observations += 1

        return row

    def fetchall(self):
        rows = self._cursor.fetchall()

        if rows:
            row_observations += len(rows)

        return rows

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class ReadOnlyConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return ReadOnlyCursor(self._conn.cursor())

    def execute(self, sql, parameters=()):
        global select_operations

        normalized = sql.strip().upper()

        if (
            normalized.startswith("INSERT")
            or normalized.startswith("UPDATE")
            or normalized.startswith("DELETE")
            or normalized.startswith("ALTER")
            or normalized.startswith("CREATE")
            or normalized.startswith("DROP")
            or normalized.startswith("REPLACE")
        ):
            raise sqlite3.OperationalError(
                "FORENSIC WRITE BLOCKED"
            )

        if normalized.startswith("SELECT") or normalized.startswith("PRAGMA"):
            select_operations += 1

        return self._conn.execute(sql, parameters)

    def executemany(self, sql, parameters):
        raise sqlite3.OperationalError(
            "FORENSIC EXECUTEMANY BLOCKED"
        )

    def executescript(self, script):
        raise sqlite3.OperationalError(
            "FORENSIC SCRIPT EXECUTION BLOCKED"
        )

    def commit(self):
        raise sqlite3.OperationalError(
            "FORENSIC COMMIT BLOCKED"
        )

    def rollback(self):
        return None

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


# =============================================================================
# CONNECTION DISCOVERY
# =============================================================================

def forensic_connect(*args, **kwargs):
    """
    Real SQLite read-only connection.

    Important:
    No recursion.
    No monkeypatching sqlite3.connect globally.
    No mutation of production source.
    """

    path = DB_FILE.resolve()

    uri = f"file:{path.as_posix()}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    return ReadOnlyConnection(conn)


# =============================================================================
# ROW / SCHEMA INSPECTION
# =============================================================================

def inspect_database_row_shapes():
    global schema_observations

    print("\nDATABASE ROW / SCHEMA PROBE")
    print("-" * 100)

    conn = sqlite3.connect(
        f"file:{DB_FILE.resolve().as_posix()}?mode=ro",
        uri=True,
        check_same_thread=False,
    )

    try:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        print(f"TABLES | COUNT={len(tables)}")

        for (table_name,) in tables:
            if table_name.startswith("sqlite_"):
                continue

            try:
                columns = conn.execute(
                    f'PRAGMA table_info("{table_name}")'
                ).fetchall()

                schema_observations += 1

                column_names = [
                    row[1]
                    for row in columns
                ]

                print(
                    f"TABLE={table_name} | "
                    f"COLUMNS={column_names}"
                )

            except Exception as exc:
                print(
                    f"TABLE={table_name} | "
                    f"SCHEMA_ERROR={type(exc).__name__}({exc!r})"
                )

    finally:
        conn.close()


# =============================================================================
# RUNTIME TRACE
# =============================================================================

def trace_function(frame, event, arg):
    global main_calls
    global process_calls
    global create_calls
    global future_calls
    global trace_events
    global first_process_boundary
    global first_main_exception

    if event == "call":
        trace_events += 1

        name = frame.f_code.co_name

        if name not in TARGET_FUNCTIONS:
            return trace_function

        if name == "main":
            main_calls += 1

        elif name == "process_signals":
            process_calls += 1

            if first_process_boundary is None:
                first_process_boundary = {
                    "line": frame.f_lineno,
                    "locals": dict(frame.f_locals),
                }

        elif name == "create_outcome":
            create_calls += 1

        elif name == "find_future_price":
            future_calls += 1

        return trace_function

    if event == "exception":
        exc_type, exc_value, exc_tb = arg

        name = frame.f_code.co_name

        if name in TARGET_FUNCTIONS:
            record = {
                "function": name,
                "line": frame.f_lineno,
                "type": exc_type.__name__,
                "value": repr(exc_value),
            }

            runtime_exceptions.append(record)

            if name == "main" and first_main_exception is None:
                first_main_exception = record

        return trace_function

    return trace_function


# =============================================================================
# MODULE LOADING
# =============================================================================

def load_target_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "__forensic_runtime__",
        str(TARGET_FILE),
    )

    module = importlib.util.module_from_spec(spec)

    # IMPORTANT:
    # We deliberately do NOT replace sqlite3.connect globally.
    # This avoids the recursion bug encountered in previous audits.

    spec.loader.exec_module(module)

    return module


# =============================================================================
# RUNTIME ENTRY
# =============================================================================

def run_runtime(module):
    print("\n" + "=" * 78)
    print("GENUINE PRODUCTION MAIN() — FIRST ROW / SCHEMA BOUNDARY")
    print("=" * 78)

    main_fn = getattr(module, "main", None)

    if main_fn is None:
        print("MAIN NOT FOUND")
        return None

    print("ENTRYPOINT              : main()")
    print("EXECUTION MODE          : DIRECT FUNCTION INVOCATION")
    print("TRACE MODE              : CPYTHON sys.settrace")
    print("DATABASE SOURCE         : READ-ONLY")
    print("PRODUCTION SOURCE       : UNMODIFIED")

    old_trace = sys.gettrace()

    try:
        sys.settrace(trace_function)

        result = main_fn()

        return result

    except Exception as exc:
        print(
            f"\nRUNTIME TOP-LEVEL EXCEPTION | "
            f"{type(exc).__name__} | {exc!r}"
        )

        runtime_exceptions.append({
            "function": "<top-level>",
            "line": None,
            "type": type(exc).__name__,
            "value": repr(exc),
        })

        return None

    finally:
        sys.settrace(old_trace)


# =============================================================================
# MAIN
# =============================================================================

def main():
    start = __import__("time").perf_counter()

    banner(
        "ARUNDA FIND_FUTURE_PRICE MAIN ROW SCHEMA FIRST BOUNDARY "
        "FORENSIC AUDIT v0.1"
    )

    print(
        f"MODE                         : {MODE}\n"
        f"TARGET                       : {TARGET_FILE}\n"
        f"DATABASE                     : {DB_FILE}\n"
        f"PRODUCTION SOURCE MODIFIED   : NONE\n"
        f"DATABASE WRITE               : BLOCKED"
    )

    # -------------------------------------------------------------------------
    # STEP 1
    # -------------------------------------------------------------------------

    banner("STEP 1 — STATIC FUNCTION RESOLUTION")

    source = load_source()
    functions = static_function_map(source)

    for name in (
        "main",
        "process_signals",
        "create_outcome",
        "find_future_price",
    ):
        node = functions.get(name)

        if node is None:
            print(f"{name:<24}: NOT FOUND")
        else:
            print(
                f"{name:<24}: FOUND "
                f"LINE={node.lineno} "
                f"END={node.end_lineno}"
            )

    # -------------------------------------------------------------------------
    # STEP 2
    # -------------------------------------------------------------------------

    banner("STEP 2 — MAIN STATIC PRE-PROCESS BOUNDARY")

    observations = collect_main_pre_process_operations(source)

    process_seen = False

    for item in observations:
        calls = item["calls"]

        if any(
            "process_signals" in call
            for call in calls
        ):
            process_seen = True

        print(
            f"LINE={str(item['line']):<6} "
            f"TYPE={item['type']:<20} "
            f"SOURCE={item['source'][:500]}"
        )

        if item["calls"]:
            print(
                f"          CALLS={item['calls']}"
            )

        if item["subscripts"]:
            print(
                f"          SUBSCRIPTS={item['subscripts']}"
            )

    print(
        f"\nPROCESS_SIGNALS STATIC CALL PRESENT : {process_seen}"
    )

    # -------------------------------------------------------------------------
    # STEP 3
    # -------------------------------------------------------------------------

    banner("STEP 3 — MAIN INSTRUCTION BOUNDARY")

    module = load_target_module()

    print_main_instructions(module)

    # -------------------------------------------------------------------------
    # STEP 4
    # -------------------------------------------------------------------------

    banner("STEP 4 — DATABASE ROW / SCHEMA OBSERVATION")

    inspect_database_row_shapes()

    print(
        f"\nSELECT OPERATIONS       : {select_operations}"
    )

    print(
        f"ROW OBSERVATIONS        : {row_observations}"
    )

    print(
        f"SCHEMA OBSERVATIONS     : {schema_observations}"
    )

    # -------------------------------------------------------------------------
    # STEP 5
    # -------------------------------------------------------------------------

    banner("STEP 5 — GENUINE PRODUCTION EXECUTION")

    result = run_runtime(module)

    print(
        f"\nMAIN RETURN              : "
        f"TYPE={type(result).__name__} "
        f"VALUE={safe_repr(result)}"
    )

    # -------------------------------------------------------------------------
    # STEP 6
    # -------------------------------------------------------------------------

    banner("STEP 6 — FIRST RUNTIME BOUNDARY / EXCEPTION")

    if first_main_exception is None:
        print("NO MAIN-SCOPED EXCEPTION OBSERVED")
    else:
        print(
            f"FUNCTION={first_main_exception['function']} | "
            f"LINE={first_main_exception['line']} | "
            f"TYPE={first_main_exception['type']} | "
            f"VALUE={first_main_exception['value']}"
        )

    if runtime_exceptions:
        print("\nALL TARGET EXCEPTIONS")

        for index, item in enumerate(runtime_exceptions, 1):
            print(
                f"{index:03d} | "
                f"FUNCTION={item['function']} | "
                f"LINE={item['line']} | "
                f"TYPE={item['type']} | "
                f"VALUE={item['value']}"
            )

    # -------------------------------------------------------------------------
    # STEP 7
    # -------------------------------------------------------------------------

    banner("STEP 7 — PROCESS_SIGNALS ENTRY BOUNDARY")

    if first_process_boundary is None:
        print("PROCESS_SIGNALS ENTRY NOT OBSERVED")
    else:
        print(
            f"PROCESS_SIGNALS ENTERED | "
            f"LINE={first_process_boundary['line']}"
        )

        locals_snapshot = first_process_boundary["locals"]

        print(
            f"PROCESS_SIGNALS LOCALS | "
            f"NAMES={list(locals_snapshot.keys())}"
        )

    # -------------------------------------------------------------------------
    # STEP 8
    # -------------------------------------------------------------------------

    banner("STEP 8 — FIND_FUTURE_PRICE BOUNDARY")

    print(
        f"FIND_FUTURE_PRICE CALLS : {future_calls}"
    )

    print(
        f"CREATE_OUTCOME CALLS    : {create_calls}"
    )

    # -------------------------------------------------------------------------
    # STEP 9
    # -------------------------------------------------------------------------

    banner("STEP 9 — FINAL FORENSIC SUMMARY")

    print(
        f"MAIN CALLS                  : {main_calls}\n"
        f"PROCESS_SIGNALS CALLS       : {process_calls}\n"
        f"CREATE_OUTCOME CALLS        : {create_calls}\n"
        f"FIND_FUTURE_PRICE CALLS     : {future_calls}\n"
        f"FIND_FUTURE_PRICE RETURNS   : 0\n"
        f"SELECT OPERATIONS           : {select_operations}\n"
        f"ROW OBSERVATIONS            : {row_observations}\n"
        f"SCHEMA OBSERVATIONS         : {schema_observations}\n"
        f"TRACE EVENTS                : {trace_events}\n"
        f"RUNTIME EXCEPTIONS          : {len(runtime_exceptions)}"
    )

    # -------------------------------------------------------------------------
    # STEP 10
    # -------------------------------------------------------------------------

    banner("FORENSIC CONCLUSION")

    if first_process_boundary is not None:
        status = "MAIN_ROW_SCHEMA_BOUNDARY_RESOLVED"

        meaning = (
            "The genuine production main() crossed the first boundary "
            "and process_signals() was entered."
        )

        frontier = (
            "Continue from process_signals() toward create_outcome() "
            "and find_future_price()."
        )

    elif first_main_exception is not None:
        status = "MAIN_FIRST_ROW_SCHEMA_BOUNDARY_EXCEPTION"

        meaning = (
            "The genuine production main() was entered, but execution "
            "stopped before process_signals(). The first exception and "
            "its exact main() boundary were captured."
        )

        frontier = (
            "Localize the exact row/object access associated with the "
            "first main() exception, especially tuple-vs-mapping semantics."
        )

    else:
        status = "MAIN_ROW_SCHEMA_BOUNDARY_NOT_OBSERVED"

        meaning = (
            "main() was not observed crossing into process_signals(), "
            "and no target-scoped exception established the boundary."
        )

        frontier = (
            "Continue static/runtime localization of the main() execution path."
        )

    print(
        f"STATUS                      : {status}\n"
        f"MEANING                     : {meaning}\n"
        f"NEXT FRONTIER               : {frontier}\n\n"
        f"DATABASE_WRITES             : NONE\n"
        f"ENGINE_MODIFIED             : NONE\n"
        f"PRODUCTION_SOURCE_MODIFIED  : NONE\n"
        f"INSERT                      : NONE\n"
        f"UPDATE                      : NONE\n"
        f"DELETE                      : NONE\n"
        f"ALTER                       : NONE\n"
        f"CREATE                      : NONE\n"
        f"DROP                        : NONE\n"
        f"COMMIT                      : NONE"
    )

    elapsed = __import__("time").perf_counter() - start

    print(
        f"\nELAPSED SECONDS              : {elapsed:.3f}"
    )

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()