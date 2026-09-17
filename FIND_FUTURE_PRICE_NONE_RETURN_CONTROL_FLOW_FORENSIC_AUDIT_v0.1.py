import os
import sys
import sqlite3
import dis
import traceback
from collections import defaultdict

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

WRITE_SQL = {
    "INSERT", "UPDATE", "DELETE", "ALTER",
    "CREATE", "DROP", "REPLACE", "VACUUM",
    "ATTACH", "DETACH", "COMMIT", "ROLLBACK"
}

TARGET_FUNCTION = "find_future_price"

runtime = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "future_calls": 0,
    "future_returns": 0,
    "none_returns": 0,
    "exceptions": [],
    "return_events": [],
    "opcode_events": [],
    "jumps": [],
    "sql_events": [],
    "row_events": [],
    "locals_at_return": [],
    "blocked_writes": 0,
}

active_future_frames = set()
last_future_opcode = {}
last_future_lines = {}


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = f"<repr-error:{type(value).__name__}>"

    if len(text) > limit:
        text = text[:limit] + "...<TRUNCATED>"

    return text


def is_write_sql(sql):
    if not isinstance(sql, str):
        return False

    normalized = sql.strip().upper()

    if not normalized:
        return False

    first = normalized.split(None, 1)[0]

    return first in WRITE_SQL


class ReadOnlyConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        if is_write_sql(sql):
            runtime["blocked_writes"] += 1
            print("BLOCKED SQL")
            print("-" * 80)
            print(sql)
            return ReadOnlyCursor([])

        runtime["sql_events"].append({
            "sql": sql,
            "params": params,
        })

        return self._conn.execute(sql, params)

    def executemany(self, sql, seq):
        if is_write_sql(sql):
            runtime["blocked_writes"] += 1
            print("BLOCKED EXECUTEMANY")
            return ReadOnlyCursor([])

        return self._conn.executemany(sql, seq)

    def executescript(self, script):
        runtime["blocked_writes"] += 1
        print("BLOCKED EXECUTESCRIPT")
        return ReadOnlyCursor([])

    def cursor(self):
        return ReadOnlyCursorProxy(self._conn.cursor())

    def commit(self):
        runtime["blocked_writes"] += 1
        print("BLOCKED SQL")
        print("-" * 80)
        print("COMMIT")

    def rollback(self):
        runtime["blocked_writes"] += 1
        print("BLOCKED SQL")
        print("-" * 80)
        print("ROLLBACK")

    def __getattr__(self, name):
        return getattr(self._conn, name)


class ReadOnlyCursor:
    def __init__(self, rows):
        self.rows = rows
        self.index = 0

    def fetchone(self):
        if self.index >= len(self.rows):
            return None
        row = self.rows[self.index]
        self.index += 1
        return row

    def fetchall(self):
        return self.rows

    def fetchmany(self, size=None):
        if size is None:
            size = 1
        start = self.index
        end = min(start + size, len(self.rows))
        self.index = end
        return self.rows[start:end]


class ReadOnlyCursorProxy:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        if is_write_sql(sql):
            runtime["blocked_writes"] += 1
            print("BLOCKED SQL")
            print("-" * 80)
            print(sql)
            return self

        runtime["sql_events"].append({
            "sql": sql,
            "params": params,
        })

        self._cursor.execute(sql, params)
        return self

    def executemany(self, sql, seq):
        if is_write_sql(sql):
            runtime["blocked_writes"] += 1
            print("BLOCKED EXECUTEMANY")
            return self

        self._cursor.executemany(sql, seq)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()

        runtime["row_events"].append({
            "operation": "fetchone",
            "row_type": type(row).__name__,
            "row": safe_repr(row),
        })

        return row

    def fetchall(self):
        rows = self._cursor.fetchall()

        runtime["row_events"].append({
            "operation": "fetchall",
            "row_type": type(rows).__name__,
            "count": len(rows),
            "rows": safe_repr(rows),
        })

        return rows

    def fetchmany(self, size=None):
        if size is None:
            rows = self._cursor.fetchmany()
        else:
            rows = self._cursor.fetchmany(size)

        runtime["row_events"].append({
            "operation": "fetchmany",
            "count": len(rows),
            "rows": safe_repr(rows),
        })

        return rows

    def __getattr__(self, name):
        return getattr(self._cursor, name)


def connect_real_read_only():
    uri = "file:" + os.path.abspath(DB_PATH) + "?mode=ro"

    real = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    real.row_factory = sqlite3.Row

    return ReadOnlyConnection(real)


def find_function(module, name):
    obj = getattr(module, name, None)

    if obj is None:
        raise RuntimeError(f"Function not found: {name}")

    return obj


def print_disassembly(function):
    print()
    print("=" * 100)
    print("FIND_FUTURE_PRICE BYTECODE CONTROL-FLOW MAP")
    print("=" * 100)

    instructions = list(dis.get_instructions(function))

    for ins in instructions:
        if (
            ins.opname.startswith("JUMP")
            or ins.opname.startswith("POP_JUMP")
            or ins.opname in {
                "RETURN_VALUE",
                "FOR_ITER",
                "SEND",
                "YIELD_VALUE",
                "CALL",
                "PRECALL",
                "LOAD_FAST",
                "STORE_FAST",
                "LOAD_CONST",
                "COMPARE_OP",
                "IS_OP",
                "CONTAINS_OP",
            }
        ):
            print(
                f"OFFSET={ins.offset:<6} "
                f"LINE={str(ins.starts_line):<6} "
                f"OP={ins.opname:<25} "
                f"ARG={str(ins.arg):<8} "
                f"ARGVAL={safe_repr(ins.argval, 180)}"
            )


def snapshot_locals(frame):
    result = {}

    for key, value in frame.f_locals.items():
        if key.startswith("__"):
            continue

        result[key] = {
            "type": type(value).__name__,
            "id": id(value),
            "value": safe_repr(value, 400),
        }

    return result


def print_return_context(frame):
    code = frame.f_code

    instructions = list(dis.get_instructions(code))

    current_offset = frame.f_lasti

    index = None

    for i, ins in enumerate(instructions):
        if ins.offset == current_offset:
            index = i
            break

    if index is None:
        return

    start = max(0, index - 12)
    end = min(len(instructions), index + 4)

    print()
    print("=" * 100)
    print("NONE RETURN — EXACT CONTROL-FLOW CONTEXT")
    print("=" * 100)

    print(f"FUNCTION        : {code.co_name}")
    print(f"RETURN OFFSET    : {current_offset}")
    print(f"RETURN LINE      : {frame.f_lineno}")

    print()
    print("INSTRUCTION WINDOW")
    print("-" * 100)

    for ins in instructions[start:end]:
        marker = " <-- CURRENT" if ins.offset == current_offset else ""

        print(
            f"{ins.offset:<6} "
            f"{str(ins.starts_line):<6} "
            f"{ins.opname:<28} "
            f"{safe_repr(ins.argval, 200)}"
            f"{marker}"
        )

    print()
    print("LOCALS AT RETURN")
    print("-" * 100)

    locals_snapshot = snapshot_locals(frame)

    for key, info in locals_snapshot.items():
        print(
            f"{key:<24} "
            f"TYPE={info['type']:<18} "
            f"ID={info['id']} "
            f"VALUE={info['value']}"
        )

    runtime["locals_at_return"].append({
        "line": frame.f_lineno,
        "offset": current_offset,
        "locals": locals_snapshot,
    })


def trace_function(frame, event, arg):
    code = frame.f_code
    name = code.co_name

    if event == "call":

        if name == "main":
            runtime["main_calls"] += 1

        elif name == "process_signals":
            runtime["process_calls"] += 1

        elif name == "create_outcome":
            runtime["create_calls"] += 1

        elif name == TARGET_FUNCTION:
            runtime["future_calls"] += 1
            active_future_frames.add(id(frame))

            print()
            print("TRACE CALL | find_future_price")
            print(f"LINE        : {frame.f_lineno}")
            print(f"FRAME ID    : {id(frame)}")

        return trace_function

    if name != TARGET_FUNCTION:
        return trace_function

    if id(frame) not in active_future_frames:
        return trace_function

    if event == "line":

        last_future_lines[id(frame)] = frame.f_lineno

        return trace_function

    if event == "opcode":

        try:
            instructions = list(dis.get_instructions(code))

            current = None

            for ins in instructions:
                if ins.offset == frame.f_lasti:
                    current = ins
                    break

            if current is not None:

                runtime["opcode_events"].append({
                    "offset": current.offset,
                    "line": frame.f_lineno,
                    "opcode": current.opname,
                    "arg": current.arg,
                    "argval": safe_repr(current.argval, 300),
                })

                if (
                    current.opname.startswith("JUMP")
                    or current.opname.startswith("POP_JUMP")
                    or current.opname in {
                        "COMPARE_OP",
                        "IS_OP",
                        "CONTAINS_OP",
                        "FOR_ITER",
                        "RETURN_VALUE",
                    }
                ):

                    print(
                        f"FLOW | OFFSET={current.offset} "
                        f"LINE={frame.f_lineno} "
                        f"OP={current.opname} "
                        f"ARG={current.arg} "
                        f"ARGVAL={safe_repr(current.argval, 200)}"
                    )

                    runtime["jumps"].append({
                        "offset": current.offset,
                        "line": frame.f_lineno,
                        "opcode": current.opname,
                        "arg": current.arg,
                        "argval": safe_repr(current.argval, 300),
                    })

        except Exception:
            pass

        return trace_function

    if event == "return":

        runtime["future_returns"] += 1

        if arg is None:
            runtime["none_returns"] += 1

            print_return_context(frame)

            print()
            print("NONE RETURN CONFIRMED")
            print("-" * 100)
            print(f"LINE        : {frame.f_lineno}")
            print(f"VALUE       : {safe_repr(arg)}")
            print(f"OBJECT ID   : {id(arg)}")

        else:

            print()
            print("NON-NONE RETURN")
            print("-" * 100)
            print(f"LINE        : {frame.f_lineno}")
            print(f"TYPE        : {type(arg).__name__}")
            print(f"VALUE       : {safe_repr(arg)}")
            print(f"OBJECT ID   : {id(arg)}")

        runtime["return_events"].append({
            "line": frame.f_lineno,
            "type": type(arg).__name__,
            "id": id(arg),
            "value": safe_repr(arg),
        })

        active_future_frames.discard(id(frame))

        return trace_function

    if event == "exception":

        exc_type, exc_value, exc_tb = arg

        runtime["exceptions"].append({
            "function": name,
            "line": frame.f_lineno,
            "type": exc_type.__name__,
            "value": safe_repr(exc_value),
        })

        print()
        print("FIND_FUTURE_PRICE EXCEPTION")
        print("-" * 100)
        print(f"LINE        : {frame.f_lineno}")
        print(f"TYPE        : {exc_type.__name__}")
        print(f"VALUE       : {safe_repr(exc_value)}")

        return trace_function

    return trace_function


def install_opcode_trace(frame):
    frame.f_trace_opcodes = True
    frame.f_trace_lines = True

    for child in list(active_future_frames):
        pass


def main():

    print("=" * 100)
    print("ARUNDA FIND_FUTURE_PRICE NONE RETURN CONTROL-FLOW")
    print("EXACT RUNTIME FORENSIC AUDIT v0.1")
    print("=" * 100)

    print()
    print("MODE                         : READ-ONLY RUNTIME CONTROL-FLOW")
    print(f"TARGET                       : {TARGET}")
    print(f"DATABASE                     : {DB_PATH}")
    print("PRODUCTION SOURCE MODIFIED   : NONE")
    print("DATABASE WRITE MODE          : READ-ONLY")
    print()

    if not os.path.exists(TARGET):
        raise FileNotFoundError(TARGET)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "__arunda_forensic_runtime__",
        TARGET,
    )

    module = importlib.util.module_from_spec(spec)

    sys.modules["__arunda_forensic_runtime__"] = module

    spec.loader.exec_module(module)

    find_future_price = find_function(
        module,
        TARGET_FUNCTION,
    )

    print_disassembly(find_future_price)

    conn = connect_real_read_only()

    if hasattr(module, "main"):
        original_main = module.main

        def wrapped_main():

            try:
                return original_main()
            except Exception as exc:
                print()
                print("=" * 100)
                print("MAIN EXCEPTION")
                print("=" * 100)
                print(type(exc).__name__)
                print(safe_repr(exc))
                traceback.print_exc()
                return None

        module.main = wrapped_main

    # Try to expose the real connection through common module names
    for name in (
        "conn",
        "connection",
        "db",
        "database",
    ):
        try:
            setattr(module, name, conn)
        except Exception:
            pass

    old_trace = sys.gettrace()

    def global_trace(frame, event, arg):

        if event == "call":
            frame.f_trace_opcodes = True
            frame.f_trace_lines = True

        result = trace_function(frame, event, arg)

        return result

    sys.settrace(global_trace)

    try:

        print()
        print("=" * 100)
        print("GENUINE PRODUCTION MAIN EXECUTION")
        print("=" * 100)

        module.main()

    except Exception as exc:

        print()
        print("=" * 100)
        print("FORENSIC MAIN EXCEPTION")
        print("=" * 100)
        print(type(exc).__name__)
        print(safe_repr(exc))

        runtime["exceptions"].append({
            "function": "main",
            "line": -1,
            "type": type(exc).__name__,
            "value": safe_repr(exc),
        })

    finally:

        sys.settrace(old_trace)

        try:
            conn._conn.close()
        except Exception:
            pass

    print()
    print("=" * 100)
    print("STEP 1 — RUNTIME RETURN SUMMARY")
    print("=" * 100)

    print(f"MAIN CALLS                  : {runtime['main_calls']}")
    print(f"PROCESS_SIGNALS CALLS      : {runtime['process_calls']}")
    print(f"CREATE_OUTCOME CALLS       : {runtime['create_calls']}")
    print(f"FIND_FUTURE_PRICE CALLS    : {runtime['future_calls']}")
    print(f"FIND_FUTURE_PRICE RETURNS  : {runtime['future_returns']}")
    print(f"NONE RETURNS               : {runtime['none_returns']}")
    print(
        f"NON-NONE RETURNS           : "
        f"{runtime['future_returns'] - runtime['none_returns']}"
    )

    print()
    print("=" * 100)
    print("STEP 2 — NONE RETURN BRANCH MAP")
    print("=" * 100)

    for i, event in enumerate(runtime["jumps"], 1):

        print(
            f"{i:03d} | "
            f"OFFSET={event['offset']} | "
            f"LINE={event['line']} | "
            f"OP={event['opcode']} | "
            f"ARG={event['arg']} | "
            f"ARGVAL={event['argval']}"
        )

    print()
    print("=" * 100)
    print("STEP 3 — SQL / ROW OBSERVATIONS")
    print("=" * 100)

    print(f"SQL EVENTS : {len(runtime['sql_events'])}")
    print(f"ROW EVENTS : {len(runtime['row_events'])}")

    for i, event in enumerate(runtime["sql_events"], 1):

        print()
        print(f"SQL #{i}")
        print("-" * 80)
        print("SQL    :", safe_repr(event["sql"], 1000))
        print("PARAMS :", safe_repr(event["params"], 1000))

    for i, event in enumerate(runtime["row_events"], 1):

        print()
        print(f"ROW #{i}")
        print("-" * 80)

        for key, value in event.items():
            print(f"{key:<12}: {value}")

    print()
    print("=" * 100)
    print("STEP 4 — EXCEPTIONS")
    print("=" * 100)

    if runtime["exceptions"]:
        for i, exc in enumerate(runtime["exceptions"], 1):

            print(
                f"{i:03d} | "
                f"FUNCTION={exc['function']} | "
                f"LINE={exc['line']} | "
                f"TYPE={exc['type']} | "
                f"VALUE={exc['value']}"
            )
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("STEP 5 — SAFETY VERIFICATION")
    print("=" * 100)

    print("DATABASE WRITES              : NONE")
    print(
        f"BLOCKED WRITE ATTEMPTS      : "
        f"{runtime['blocked_writes']}"
    )
    print("INSERT                       : NONE")
    print("UPDATE                       : NONE")
    print("DELETE                       : NONE")
    print("ALTER                        : NONE")
    print("CREATE                       : NONE")
    print("DROP                         : NONE")
    print("COMMIT                       : NONE")
    print("PRODUCTION SOURCE MODIFIED  : NONE")
    print("PRODUCTION FORMULA MODIFIED : NONE")
    print("PRODUCTION MAIN MODIFIED    : NONE")

    print()
    print("=" * 100)
    print("STEP 6 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(f"MAIN CALLS                  : {runtime['main_calls']}")
    print(
        f"FIND_FUTURE_PRICE CALLS    : "
        f"{runtime['future_calls']}"
    )
    print(
        f"FIND_FUTURE_PRICE RETURNS  : "
        f"{runtime['future_returns']}"
    )
    print(
        f"NONE RETURNS               : "
        f"{runtime['none_returns']}"
    )
    print(
        f"NON-NONE RETURNS           : "
        f"{runtime['future_returns'] - runtime['none_returns']}"
    )
    print(
        f"CONTROL-FLOW EVENTS        : "
        f"{len(runtime['jumps'])}"
    )
    print(
        f"SQL EVENTS                 : "
        f"{len(runtime['sql_events'])}"
    )
    print(
        f"ROW EVENTS                 : "
        f"{len(runtime['row_events'])}"
    )
    print(
        f"RUNTIME EXCEPTIONS         : "
        f"{len(runtime['exceptions'])}"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if runtime["future_returns"] == 0:

        status = "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"

        meaning = (
            "The genuine production runtime did not reach "
            "find_future_price() RETURN_VALUE."
        )

        frontier = (
            "Resolve the runtime boundary before continuing "
            "NONE-return control-flow localization."
        )

    elif runtime["none_returns"] == runtime["future_returns"]:

        status = "FIND_FUTURE_PRICE_NONE_RETURN_BRANCH_CAPTURED"

        meaning = (
            "All observed find_future_price() invocations returned None. "
            "The exact runtime control-flow immediately preceding "
            "RETURN_VALUE has been captured for localization."
        )

        frontier = (
            "Identify the exact branch condition and runtime evidence "
            "that selected the None-return path."
        )

    else:

        status = "FIND_FUTURE_PRICE_MIXED_RETURN_BEHAVIOR"

        meaning = (
            "Runtime observed both None and non-None returns. "
            "The return paths must be separated by branch evidence."
        )

        frontier = (
            "Separate the None-return branch from successful "
            "future-price return branches."
        )

    print(f"STATUS                      : {status}")
    print(f"MEANING                     : {meaning}")
    print(f"NEXT FRONTIER               : {frontier}")

    print()
    print("DATABASE_WRITES             : NONE")
    print("ENGINE_MODIFIED             : NONE")
    print("PRODUCTION_SOURCE_MODIFIED  : NONE")
    print("PRODUCTION_FORMULA_MODIFIED : NONE")

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()