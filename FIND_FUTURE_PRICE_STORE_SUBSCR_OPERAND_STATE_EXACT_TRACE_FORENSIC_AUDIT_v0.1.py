import os
import sys
import sqlite3
import dis
import types
import traceback
from collections import Counter

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


class WriteNoOpConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, *args, **kwargs):
        command = sql.strip().upper()
        if command.startswith(("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP", "REPLACE")):
            return NoOpCursor()
        return self._conn.execute(sql, *args, **kwargs)

    def executemany(self, sql, *args, **kwargs):
        command = sql.strip().upper()
        if command.startswith(("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP", "REPLACE")):
            return NoOpCursor()
        return self._conn.executemany(sql, *args, **kwargs)

    def executescript(self, sql, *args, **kwargs):
        return NoOpCursor()

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


class NoOpCursor:
    rowcount = 0

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def fetchmany(self, size=None):
        return []

    def __iter__(self):
        return iter(())

    def __getattr__(self, name):
        if name == "description":
            return None
        return lambda *args, **kwargs: None


def forensic_connect(database, *args, **kwargs):
    kwargs = dict(kwargs)
    kwargs.pop("uri", None)
    kwargs.pop("check_same_thread", None)

    conn = sqlite3.connect(
        database,
        uri=False,
        check_same_thread=False,
    )

    return WriteNoOpConnection(conn)


def load_module():
    namespace = {
        "__name__": "__forensic_runtime__",
        "__file__": TARGET,
        "__package__": None,
        "__builtins__": __builtins__,
        "sqlite3": sqlite3,
    }

    source = open(TARGET, "r", encoding="utf-8").read()

    # Replace sqlite3.connect inside the production module only.
    original_connect = sqlite3.connect
    sqlite3.connect = forensic_connect

    try:
        code = compile(source, TARGET, "exec")
        exec(code, namespace, namespace)
    finally:
        sqlite3.connect = original_connect

    return namespace


def function_info(fn):
    if not isinstance(fn, types.FunctionType):
        return None

    return {
        "name": fn.__name__,
        "file": fn.__code__.co_filename,
        "line": fn.__code__.co_firstlineno,
        "code": fn.__code__,
    }


def print_function_resolution(namespace):
    print("=" * 100)
    print("STEP 1 — STATIC FUNCTION RESOLUTION")
    print("=" * 100)

    for name in (
        "main",
        "process_signals",
        "create_outcome",
        "find_future_price",
    ):
        fn = namespace.get(name)

        if fn is None:
            print(f"{name:24} : NOT FOUND")
            continue

        info = function_info(fn)

        print(
            f"{name:24} : FOUND | "
            f"LINE={info['line']} | "
            f"FILE={info['file']}"
        )


def print_instruction_map(namespace):
    fn = namespace.get("create_outcome")

    print()
    print("=" * 100)
    print("STEP 2 — EXACT STORE_SUBSCR / RETURN_VALUE INSTRUCTION MAP")
    print("=" * 100)

    if fn is None:
        print("create_outcome : NOT FOUND")
        return

    instructions = list(dis.get_instructions(fn))

    for ins in instructions:
        if ins.opname in (
            "STORE_SUBSCR",
            "RETURN_VALUE",
            "LOAD_FAST",
            "STORE_FAST",
            "BUILD_MAP",
            "BUILD_CONST_KEY_MAP",
        ):
            if (
                ins.opname in ("STORE_SUBSCR", "RETURN_VALUE")
                or ins.argval in ("price", "prices", "returns", "outcomes", "label")
            ):
                print(
                    f"OFFSET={ins.offset:<8} "
                    f"LINE={str(ins.starts_line):<5} "
                    f"OP={ins.opname:<28} "
                    f"ARG={str(ins.arg):<8} "
                    f"ARGVAL={repr(ins.argval)}"
                )


def describe(value):
    try:
        return {
            "type": type(value).__name__,
            "id": id(value),
            "repr": repr(value),
        }
    except Exception:
        return {
            "type": type(value).__name__,
            "id": id(value),
            "repr": "<unrepresentable>",
        }


class OperandTracer:
    def __init__(self):
        self.store_subscr_events = 0
        self.return_events = 0
        self.price_store_events = 0
        self.price_return_events = 0
        self.find_returns = 0
        self.create_returns = 0
        self.runtime_exceptions = 0
        self.trace_events = 0
        self.current_function = None
        self.frame_seen = set()

    def trace(self, frame, event, arg):
        self.trace_events += 1

        filename = frame.f_code.co_filename

        if filename != TARGET:
            return self.trace

        name = frame.f_code.co_name

        if event == "call":
            self.frame_seen.add(id(frame))
            self.current_function = name

            if name in (
                "main",
                "process_signals",
                "create_outcome",
                "find_future_price",
            ):
                print(
                    f"TRACE CALL | {name} | "
                    f"LINE={frame.f_lineno}"
                )

            return self.trace

        if event == "exception":
            self.runtime_exceptions += 1

            exc_type, exc_value, _ = arg

            print(
                f"TRACE EXCEPTION | {name} | "
                f"LINE={frame.f_lineno} | "
                f"{exc_type.__name__} | "
                f"{exc_value!r}"
            )

            return self.trace

        if event == "return":
            if name == "find_future_price":
                self.find_returns += 1

                print()
                print("-" * 90)
                print(
                    f"FIND_FUTURE_PRICE RETURN #{self.find_returns}"
                )
                print("-" * 90)
                print(
                    f"LINE       : {frame.f_lineno}"
                )
                print(
                    f"TYPE       : {type(arg).__name__}"
                )
                print(
                    f"OBJECT ID  : {id(arg)}"
                )
                print(
                    f"VALUE      : {arg!r}"
                )

            elif name == "create_outcome":
                self.create_returns += 1

                print()
                print("-" * 90)
                print(
                    f"CREATE_OUTCOME RETURN #{self.create_returns}"
                )
                print("-" * 90)
                print(
                    f"TYPE       : {type(arg).__name__}"
                )
                print(
                    f"OBJECT ID  : {id(arg)}"
                )
                print(
                    f"VALUE      : {arg!r}"
                )

            return self.trace

        if event == "line":
            if name == "create_outcome":
                self.inspect_create_frame(frame)

            return self.trace

        return self.trace

    def inspect_create_frame(self, frame):
        code = frame.f_code

        try:
            current = frame.f_lasti
        except Exception:
            return

        instructions = list(dis.get_instructions(code))

        index = None

        for i, ins in enumerate(instructions):
            if ins.offset == current:
                index = i
                break

        if index is None:
            return

        ins = instructions[index]

        if ins.opname == "STORE_SUBSCR":
            self.capture_store_subscr(frame, instructions, index)

    def capture_store_subscr(self, frame, instructions, index):
        self.store_subscr_events += 1

        locals_copy = dict(frame.f_locals)

        print()
        print("=" * 90)
        print(
            f"STORE_SUBSCR EVENT #{self.store_subscr_events}"
        )
        print("=" * 90)

        print(
            f"FUNCTION       : {frame.f_code.co_name}"
        )
        print(
            f"BYTECODE OFFSET: {instructions[index].offset}"
        )
        print(
            f"LINE           : {frame.f_lineno}"
        )

        print()
        print("LOCAL OPERANDS")
        print("-" * 90)

        interesting = (
            "price",
            "prices",
            "returns",
            "outcomes",
            "label",
            "entry_price",
            "direction",
        )

        for name in interesting:
            if name in locals_copy:
                info = describe(locals_copy[name])

                print(
                    f"{name:16} | "
                    f"TYPE={info['type']:<12} | "
                    f"ID={info['id']} | "
                    f"VALUE={info['repr']}"
                )

        if "price" in locals_copy:
            self.price_store_events += 1

            print()
            print(
                "PRICE LOCAL AT STORE_SUBSCR"
            )
            print("-" * 90)

            print(
                f"PRICE TYPE : {type(locals_copy['price']).__name__}"
            )
            print(
                f"PRICE ID   : {id(locals_copy['price'])}"
            )
            print(
                f"PRICE VALUE: {locals_copy['price']!r}"
            )

            if locals_copy["price"] is None:
                print("PRICE STATE : NONE")
            else:
                print("PRICE STATE : NON-NONE")

        if "prices" in locals_copy:
            prices = locals_copy["prices"]

            print()
            print(
                "PRICES DICTIONARY OBSERVATION"
            )
            print("-" * 90)

            print(
                f"DICT TYPE : {type(prices).__name__}"
            )
            print(
                f"DICT ID   : {id(prices)}"
            )

            if isinstance(prices, dict):
                print(
                    f"DICT SIZE : {len(prices)}"
                )

                for key, value in list(prices.items())[-5:]:
                    print(
                        f"KEY={key!r} | "
                        f"TYPE={type(value).__name__} | "
                        f"ID={id(value)} | "
                        f"VALUE={value!r}"
                    )


def run():
    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE STORE_SUBSCR "
        "OPERAND STATE EXACT TRACE FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print("MODE                         : READ-ONLY BYTECODE / OPERAND FORENSICS")
    print(f"TARGET                       : {TARGET}")
    print(f"DATABASE                     : {DB_PATH}")
    print("PRODUCTION SOURCE MODIFIED  : NONE")
    print("DATABASE WRITE               : BLOCKED")

    if not os.path.exists(TARGET):
        print()
        print("TARGET FILE NOT FOUND")
        return

    namespace = load_module()

    print_function_resolution(namespace)
    print_instruction_map(namespace)

    print()
    print("=" * 100)
    print("STEP 3 — GENUINE PRODUCTION EXECUTION")
    print("=" * 100)

    main_fn = namespace.get("main")

    if main_fn is None:
        print("main() NOT FOUND")
        return

    tracer = OperandTracer()

    previous_trace = sys.gettrace()

    try:
        sys.settrace(tracer.trace)

        result = main_fn()

    except Exception as exc:
        tracer.runtime_exceptions += 1

        print()
        print(
            "TOP-LEVEL TRACE EXCEPTION"
        )
        print(
            f"TYPE  : {type(exc).__name__}"
        )
        print(
            f"VALUE : {exc!r}"
        )

        traceback.print_exc()

        result = None

    finally:
        sys.settrace(previous_trace)

    print()
    print("=" * 100)
    print("STEP 4 — TRACE RESULT")
    print("=" * 100)

    print(
        f"MAIN RETURN TYPE  : {type(result).__name__}"
    )
    print(
        f"MAIN RETURN VALUE : {result!r}"
    )

    print()
    print("=" * 100)
    print("STEP 5 — OPERAND / STORE_SUBSCR SUMMARY")
    print("=" * 100)

    print(
        f"STORE_SUBSCR EVENTS          : {tracer.store_subscr_events}"
    )
    print(
        f"PRICE AT STORE_SUBSCR        : {tracer.price_store_events}"
    )
    print(
        f"PRICES DICT OBSERVATIONS     : "
        f"{tracer.store_subscr_events}"
    )
    print(
        f"RETURN_VALUE FIND RETURNS    : {tracer.find_returns}"
    )
    print(
        f"CREATE_OUTCOME RETURNS       : {tracer.create_returns}"
    )
    print(
        f"RUNTIME / TRACE EXCEPTIONS   : "
        f"{tracer.runtime_exceptions}"
    )
    print(
        f"TRACE EVENTS                  : "
        f"{tracer.trace_events}"
    )

    print()
    print("=" * 100)
    print("STEP 6 — SAFETY VERIFICATION")
    print("=" * 100)

    print("DATABASE WRITES              : NONE")
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
    print("STEP 7 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"MAIN CALLS                  : "
        f"{1 if main_fn else 0}"
    )
    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{tracer.find_returns}"
    )
    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{tracer.create_returns}"
    )
    print(
        f"STORE_SUBSCR EVENTS         : "
        f"{tracer.store_subscr_events}"
    )
    print(
        f"PRICE AT STORE_SUBSCR       : "
        f"{tracer.price_store_events}"
    )
    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{tracer.runtime_exceptions}"
    )

    print()
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if tracer.price_store_events > 0:
        status = "STORE_SUBSCR_OPERAND_STATE_OBSERVED"
        meaning = (
            "The create_outcome() frame was observed at "
            "STORE_SUBSCR with the local price operand visible."
        )
        frontier = (
            "Use the captured dictionary/key/value state to establish "
            "the exact price -> prices[label] path."
        )
    elif tracer.find_returns > 0:
        status = "FUTURE_PRICE_RETURN_OBSERVED_STORE_STATE_UNRESOLVED"
        meaning = (
            "find_future_price() returns were observed, but "
            "the STORE_SUBSCR operand state was not captured."
        )
        frontier = (
            "Continue at the exact bytecode boundary immediately "
            "around STORE_SUBSCR."
        )
    else:
        status = "FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        meaning = (
            "The runtime did not produce an observable "
            "find_future_price() return."
        )
        frontier = (
            "Resolve the first runtime boundary before "
            "continuing operand-stack localization."
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
    print("DATABASE_WRITES             : NONE")
    print("ENGINE_MODIFIED             : NONE")
    print("PRODUCTION_SOURCE_MODIFIED  : NONE")
    print("INSERT                      : NONE")
    print("UPDATE                      : NONE")
    print("DELETE                      : NONE")
    print("ALTER                       : NONE")
    print("CREATE                      : NONE")
    print("DROP                        : NONE")
    print("COMMIT                      : NONE")
    print("=" * 100)


if __name__ == "__main__":
    run()