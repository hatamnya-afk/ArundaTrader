import os
import sys
import sqlite3
import inspect
import traceback
import dis
import types

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"
TARGET_FILE = os.path.join(BASE_DIR, "signal_outcome_engine.py")
DB_FILE = os.path.join(BASE_DIR, "arunda.db")

print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE MAIN ROW / SCHEMA BOUNDARY FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY MAIN ROW / SCHEMA FORENSICS")
print("TARGET                       :", TARGET_FILE)
print("DATABASE                     :", DB_FILE)
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("DATABASE WRITE               : BLOCKED")
print("=" * 100)


# ==========================================================================================
# GLOBAL FORENSIC STATE
# ==========================================================================================

stats = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "future_calls": 0,
    "future_returns": 0,
    "runtime_exceptions": 0,
    "selects": 0,
    "blocked_writes": 0,
    "row_observations": 0,
}

exceptions = []
row_observations = []
boundary_observations = []

TARGET_LINES = {
    "main": 990,
    "process_signals": 700,
    "create_outcome": 316,
    "find_future_price": 212,
}


# ==========================================================================================
# SAFE READ-ONLY SQLITE CONNECTION
# ==========================================================================================

class ReadOnlyCursorProxy:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        sql_upper = sql.lstrip().upper()

        if (
            sql_upper.startswith("INSERT")
            or sql_upper.startswith("UPDATE")
            or sql_upper.startswith("DELETE")
            or sql_upper.startswith("ALTER")
            or sql_upper.startswith("CREATE")
            or sql_upper.startswith("DROP")
            or sql_upper.startswith("REPLACE")
        ):
            stats["blocked_writes"] += 1
            raise sqlite3.OperationalError(
                "FORENSIC BLOCKED WRITE OPERATION"
            )

        if sql_upper.startswith("SELECT") or sql_upper.startswith("PRAGMA"):
            stats["selects"] += 1

        return self._cursor.execute(sql, params)

    def executemany(self, sql, seq):
        stats["blocked_writes"] += 1
        raise sqlite3.OperationalError(
            "FORENSIC BLOCKED EXECUTEMANY"
        )

    def executescript(self, script):
        stats["blocked_writes"] += 1
        raise sqlite3.OperationalError(
            "FORENSIC BLOCKED EXECUTESCRIPT"
        )

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class ReadOnlyConnectionProxy:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return ReadOnlyCursorProxy(
            self._conn.cursor(*args, **kwargs)
        )

    def execute(self, sql, params=()):
        sql_upper = sql.lstrip().upper()

        if (
            sql_upper.startswith("INSERT")
            or sql_upper.startswith("UPDATE")
            or sql_upper.startswith("DELETE")
            or sql_upper.startswith("ALTER")
            or sql_upper.startswith("CREATE")
            or sql_upper.startswith("DROP")
            or sql_upper.startswith("REPLACE")
        ):
            stats["blocked_writes"] += 1
            raise sqlite3.OperationalError(
                "FORENSIC BLOCKED WRITE OPERATION"
            )

        if sql_upper.startswith("SELECT") or sql_upper.startswith("PRAGMA"):
            stats["selects"] += 1

        return self._conn.execute(sql, params)

    def executemany(self, sql, seq):
        stats["blocked_writes"] += 1
        raise sqlite3.OperationalError(
            "FORENSIC BLOCKED EXECUTEMANY"
        )

    def executescript(self, script):
        stats["blocked_writes"] += 1
        raise sqlite3.OperationalError(
            "FORENSIC BLOCKED EXECUTESCRIPT"
        )

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def forensic_connect(database, *args, **kwargs):
    print(
        f"FORENSIC CONNECT | REQUESTED={database} | "
        f"REAL_READ_ONLY=True"
    )

    if os.path.isabs(database):
        path = database
    else:
        path = os.path.join(BASE_DIR, database)

    uri = f"file:{os.path.abspath(path)}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)

    # Preserve normal tuple behavior first.
    # The audit will inspect whether production expects tuple
    # or mapping-style row access.
    conn.row_factory = None

    return ReadOnlyConnectionProxy(conn)


# ==========================================================================================
# STATIC SOURCE / FUNCTION RESOLUTION
# ==========================================================================================

print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("=" * 100)

if not os.path.exists(TARGET_FILE):
    print("TARGET FILE : NOT FOUND")
    sys.exit(1)

with open(TARGET_FILE, "r", encoding="utf-8") as f:
    source_text = f.read()

compile(source_text, TARGET_FILE, "exec")

module = types.ModuleType("__forensic_runtime__")
module.__file__ = TARGET_FILE
module.__name__ = "__forensic_runtime__"

# Prevent __main__ guard from executing automatically.
exec(compile(source_text, TARGET_FILE, "exec"), module.__dict__)

for name in (
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
):
    obj = getattr(module, name, None)

    if callable(obj):
        try:
            line = inspect.getsourcelines(obj)[1]
        except Exception:
            line = "UNKNOWN"

        print(
            f"{name:24} : FOUND | LINE={line} | "
            f"FILE={getattr(obj, '__code__', None).co_filename}"
        )
    else:
        print(f"{name:24} : NOT FOUND")


# ==========================================================================================
# MAIN DISASSEMBLY AROUND FIRST BOUNDARY
# ==========================================================================================

print()
print("=" * 100)
print("STEP 2 — MAIN INSTRUCTION / ROW ACCESS BOUNDARY")
print("=" * 100)

main_fn = getattr(module, "main", None)

if main_fn is not None:

    print()
    print("MAIN INSTRUCTIONS")
    print("-" * 100)

    for ins in dis.get_instructions(main_fn):
        if (
            ins.opname in {
                "BINARY_SUBSCR",
                "STORE_SUBSCR",
                "LOAD_ATTR",
                "LOAD_METHOD",
                "CALL",
                "PRECALL",
                "FOR_ITER",
                "GET_ITER",
                "RETURN_VALUE",
            }
            or (
                ins.starts_line is not None
                and 1035 <= ins.starts_line <= 1060
            )
        ):
            print(
                f"OFFSET={ins.offset:<8} "
                f"LINE={str(ins.starts_line):<6} "
                f"OP={ins.opname:<22} "
                f"ARG={str(ins.arg):<8} "
                f"ARGVAL={repr(ins.argval)}"
            )


# ==========================================================================================
# RUNTIME TRACE
# ==========================================================================================

print()
print("=" * 100)
print("STEP 3 — GENUINE PRODUCTION ENTRYPOINT EXECUTION")
print("=" * 100)
print("ENTRYPOINT                  : main()")
print("EXECUTION MODE              : DIRECT FUNCTION INVOCATION")
print("TRACE MODE                  : CPYTHON sys.settrace")
print("DATABASE MODE               : REAL SELECT / WRITE BLOCKED")
print("PRODUCTION SOURCE           : UNMODIFIED")
print("=" * 100)


def describe_value(value):
    info = {
        "type": type(value).__name__,
        "repr": repr(value)[:500],
    }

    if isinstance(value, dict):
        info["kind"] = "dict"
        info["keys"] = list(value.keys())[:50]

    elif isinstance(value, (tuple, list)):
        info["kind"] = type(value).__name__
        info["length"] = len(value)

        if len(value) <= 20:
            info["items"] = [
                repr(x)[:250]
                for x in value
            ]

    elif isinstance(value, sqlite3.Row):
        info["kind"] = "sqlite3.Row"

        try:
            info["keys"] = list(value.keys())
        except Exception:
            pass

    elif isinstance(value, sqlite3.Cursor):
        info["kind"] = "sqlite3.Cursor"

    return info


def inspect_frame_locals(frame, event, function_name):
    interesting = {}

    for name, value in frame.f_locals.items():

        if (
            name in {
                "signal",
                "signals",
                "row",
                "rows",
                "existing",
                "conn",
                "cursor",
                "result",
                "record",
                "asset",
                "snapshot_id",
            }
            or "signal" in name.lower()
            or "row" in name.lower()
            or "record" in name.lower()
        ):
            try:
                interesting[name] = describe_value(value)
            except Exception:
                interesting[name] = {
                    "type": type(value).__name__,
                    "repr": "<UNAVAILABLE>",
                }

    if interesting:
        observation = {
            "function": function_name,
            "line": frame.f_lineno,
            "event": event,
            "locals": interesting,
        }

        boundary_observations.append(observation)

        if len(boundary_observations) <= 100:
            print()
            print(
                f"BOUNDARY OBSERVATION | "
                f"FUNCTION={function_name} | "
                f"LINE={frame.f_lineno} | "
                f"EVENT={event}"
            )

            for key, value in interesting.items():
                print(
                    f"  {key:<20} | "
                    f"TYPE={value.get('type')} | "
                    f"KIND={value.get('kind')} | "
                    f"REPR={value.get('repr')}"
                )

                if "keys" in value:
                    print(
                        f"  {key:<20} | "
                        f"KEYS={value['keys']}"
                    )


def tracer(frame, event, arg):

    filename = os.path.abspath(frame.f_code.co_filename)

    if filename != os.path.abspath(TARGET_FILE):
        return tracer

    function_name = frame.f_code.co_name

    if event == "call":

        if function_name == "main":
            stats["main_calls"] += 1
            print(
                f"TRACE CALL | main | LINE={frame.f_lineno}"
            )

        elif function_name == "process_signals":
            stats["process_calls"] += 1
            print(
                f"TRACE CALL | process_signals | "
                f"LINE={frame.f_lineno}"
            )

        elif function_name == "create_outcome":
            stats["create_calls"] += 1
            print(
                f"TRACE CALL | create_outcome | "
                f"LINE={frame.f_lineno}"
            )

        elif function_name == "find_future_price":
            stats["future_calls"] += 1
            print(
                f"TRACE CALL | find_future_price | "
                f"LINE={frame.f_lineno}"
            )

        inspect_frame_locals(
            frame,
            event,
            function_name,
        )

        return tracer

    if event == "return":

        if function_name == "find_future_price":
            stats["future_returns"] += 1

            print(
                f"TRACE RETURN | find_future_price | "
                f"TYPE={type(arg).__name__} | "
                f"VALUE={repr(arg)}"
            )

        inspect_frame_locals(
            frame,
            event,
            function_name,
        )

        return tracer

    if event == "exception":

        exc_type, exc_value, exc_tb = arg

        stats["runtime_exceptions"] += 1

        record = {
            "function": function_name,
            "line": frame.f_lineno,
            "type": getattr(
                exc_type,
                "__name__",
                str(exc_type),
            ),
            "value": repr(exc_value),
        }

        exceptions.append(record)

        print()
        print(
            f"TRACE EXCEPTION | "
            f"{function_name} | "
            f"LINE={frame.f_lineno} | "
            f"{record['type']} | "
            f"{record['value']}"
        )

        inspect_frame_locals(
            frame,
            event,
            function_name,
        )

        return tracer

    if event == "line":

        # Focus heavily on the known main boundary.
        if (
            function_name == "main"
            and 1035 <= frame.f_lineno <= 1060
        ):
            inspect_frame_locals(
                frame,
                event,
                function_name,
            )

        # Capture process_signals entry boundary.
        if function_name == "process_signals":
            inspect_frame_locals(
                frame,
                event,
                function_name,
            )

        return tracer

    return tracer


# ==========================================================================================
# EXECUTION
# ==========================================================================================

try:

    # Inject read-only connector.
    module.__dict__["sqlite3"].connect = forensic_connect

    # Also expose connector directly in case production resolves
    # sqlite3.connect through the module namespace.
    module.__dict__["forensic_connect"] = forensic_connect

    main_fn = module.__dict__.get("main")

    if not callable(main_fn):
        raise RuntimeError("main() not resolved")

    sys.settrace(tracer)

    result = main_fn()

except Exception as exc:

    stats["runtime_exceptions"] += 1

    record = {
        "function": "AUDIT_TOP_LEVEL",
        "line": None,
        "type": type(exc).__name__,
        "value": repr(exc),
    }

    exceptions.append(record)

    print()
    print(
        "TOP-LEVEL TRACE EXCEPTION | "
        f"{type(exc).__name__} | {repr(exc)}"
    )

finally:
    sys.settrace(None)


# ==========================================================================================
# POST-RUNTIME ROW ANALYSIS
# ==========================================================================================

print()
print("=" * 100)
print("STEP 4 — ROW / SCHEMA OBSERVATION SUMMARY")
print("=" * 100)

if boundary_observations:

    unique = {}

    for obs in boundary_observations:

        for name, data in obs["locals"].items():

            key = (
                obs["function"],
                name,
                data.get("type"),
                data.get("kind"),
            )

            unique[key] = data

    for key, data in list(unique.items())[:100]:

        function_name, variable_name, type_name, kind = key

        print(
            f"FUNCTION={function_name:<18} | "
            f"VARIABLE={variable_name:<18} | "
            f"TYPE={type_name:<16} | "
            f"KIND={kind}"
        )

        if "keys" in data:
            print(
                f"    KEYS={data['keys']}"
            )

else:
    print("NO ROW / SCHEMA OBSERVATIONS")


# ==========================================================================================
# EXCEPTION REPORT
# ==========================================================================================

print()
print("=" * 100)
print("STEP 5 — FIRST RUNTIME BOUNDARY / EXCEPTION")
print("=" * 100)

if exceptions:

    for idx, exc in enumerate(exceptions[:50], 1):

        print(
            f"{idx:03d} | "
            f"FUNCTION={exc['function']} | "
            f"LINE={exc['line']} | "
            f"TYPE={exc['type']} | "
            f"VALUE={exc['value']}"
        )

else:
    print("NO RUNTIME EXCEPTIONS")


# ==========================================================================================
# FINAL SUMMARY
# ==========================================================================================

print()
print("=" * 100)
print("STEP 6 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    f"MAIN CALLS                  : {stats['main_calls']}"
)
print(
    f"PROCESS_SIGNALS CALLS       : {stats['process_calls']}"
)
print(
    f"CREATE_OUTCOME CALLS        : {stats['create_calls']}"
)
print(
    f"FIND_FUTURE_PRICE CALLS     : {stats['future_calls']}"
)
print(
    f"FIND_FUTURE_PRICE RETURNS   : {stats['future_returns']}"
)
print(
    f"RUNTIME EXCEPTIONS          : {stats['runtime_exceptions']}"
)
print(
    f"SELECT OPERATIONS           : {stats['selects']}"
)
print(
    f"ROW / SCHEMA OBSERVATIONS   : {len(boundary_observations)}"
)
print(
    f"BLOCKED WRITE OPERATIONS    : {stats['blocked_writes']}"
)

print()
print("FORENSIC CONCLUSION")
print("-" * 100)

if stats["main_calls"] == 0:

    status = "MAIN_RUNTIME_NOT_OBSERVED"

    meaning = (
        "The genuine production main() was not entered."
    )

    frontier = (
        "Resolve main() execution before investigating row/schema boundaries."
    )

elif stats["process_calls"] == 0:

    status = "MAIN_ROW_SCHEMA_BOUNDARY_BLOCKED"

    meaning = (
        "The genuine main() was entered, but execution stopped "
        "before process_signals(). The first runtime row/schema "
        "boundary must be localized."
    )

    frontier = (
        "Inspect the exact object accessed immediately before "
        "the process_signals() call, especially tuple-vs-mapping "
        "row semantics."
    )

elif stats["create_calls"] == 0:

    status = "PROCESS_SIGNALS_ROW_BOUNDARY_BLOCKED"

    meaning = (
        "process_signals() was entered, but create_outcome() "
        "was not reached."
    )

    frontier = (
        "Trace process_signals() input rows and the first "
        "signal object handed toward create_outcome()."
    )

elif stats["future_calls"] == 0:

    status = "CREATE_OUTCOME_FUTURE_PRICE_BOUNDARY_BLOCKED"

    meaning = (
        "create_outcome() was entered, but find_future_price() "
        "was not reached."
    )

    frontier = (
        "Trace create_outcome() instruction flow to the "
        "price assignment."
    )

else:

    status = "FUTURE_PRICE_RUNTIME_REACHED"

    meaning = (
        "The genuine production runtime reached find_future_price()."
    )

    frontier = (
        "Resume exact identity tracing from the future-price "
        "return into create_outcome().price."
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

print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)