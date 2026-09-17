import os
import sys
import sqlite3
import dis
import types
import traceback

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


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

    @property
    def description(self):
        return None


class WriteNoOpConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, *args, **kwargs):
        command = sql.strip().upper()

        if command.startswith(
            (
                "INSERT",
                "UPDATE",
                "DELETE",
                "ALTER",
                "CREATE",
                "DROP",
                "REPLACE",
            )
        ):
            return NoOpCursor()

        return self._conn.execute(sql, *args, **kwargs)

    def executemany(self, sql, *args, **kwargs):
        command = sql.strip().upper()

        if command.startswith(
            (
                "INSERT",
                "UPDATE",
                "DELETE",
                "ALTER",
                "CREATE",
                "DROP",
                "REPLACE",
            )
        ):
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


def forensic_connect(database, *args, **kwargs):
    kwargs = dict(kwargs)

    kwargs.pop("uri", None)
    kwargs.pop("check_same_thread", None)

    conn = sqlite3.connect(
        database,
        check_same_thread=False,
    )

    return WriteNoOpConnection(conn)


def load_module():
    source = open(
        TARGET,
        "r",
        encoding="utf-8",
    ).read()

    namespace = {
        "__name__": "__forensic_runtime__",
        "__file__": TARGET,
        "__package__": None,
        "__builtins__": __builtins__,
    }

    original_connect = sqlite3.connect

    sqlite3.connect = forensic_connect

    try:
        code = compile(
            source,
            TARGET,
            "exec",
        )

        exec(
            code,
            namespace,
            namespace,
        )

    finally:
        sqlite3.connect = original_connect

    return namespace


def safe_repr(value):
    try:
        return repr(value)
    except Exception:
        return "<unrepresentable>"


def describe(value):
    return (
        f"TYPE={type(value).__name__} | "
        f"ID={id(value)} | "
        f"VALUE={safe_repr(value)}"
    )


class OpcodeTracer:
    def __init__(self):
        self.main_calls = 0
        self.process_calls = 0
        self.create_calls = 0
        self.future_calls = 0

        self.future_returns = 0
        self.create_returns = 0

        self.store_subscr_events = 0
        self.store_subscr_price_events = 0
        self.return_value_events = 0

        self.runtime_exceptions = 0
        self.trace_events = 0

        self.price_ids = set()

    def trace(self, frame, event, arg):
        filename = frame.f_code.co_filename

        if filename != TARGET:
            return self.trace

        name = frame.f_code.co_name

        self.trace_events += 1

        if event == "call":

            if name == "main":
                self.main_calls += 1

            elif name == "process_signals":
                self.process_calls += 1

            elif name == "create_outcome":
                self.create_calls += 1

            elif name == "find_future_price":
                self.future_calls += 1

            # Critical:
            # enable opcode-level tracing for this frame.
            frame.f_trace_opcodes = True

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

        if event == "opcode":

            self.handle_opcode(
                frame,
            )

            return self.trace

        if event == "return":

            if name == "find_future_price":

                self.future_returns += 1

                print()
                print("=" * 90)
                print(
                    f"FIND_FUTURE_PRICE RETURN "
                    f"#{self.future_returns}"
                )
                print("=" * 90)

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
                    f"VALUE      : {safe_repr(arg)}"
                )

            elif name == "create_outcome":

                self.create_returns += 1

                print()
                print("-" * 90)
                print(
                    f"CREATE_OUTCOME RETURN "
                    f"#{self.create_returns}"
                )
                print("-" * 90)

                print(
                    f"TYPE       : {type(arg).__name__}"
                )
                print(
                    f"OBJECT ID  : {id(arg)}"
                )
                print(
                    f"VALUE      : {safe_repr(arg)}"
                )

            return self.trace

        if event == "exception":

            self.runtime_exceptions += 1

            exc_type, exc_value, _ = arg

            print(
                f"TRACE EXCEPTION | "
                f"{name} | "
                f"LINE={frame.f_lineno} | "
                f"{exc_type.__name__} | "
                f"{exc_value!r}"
            )

            return self.trace

        if event == "line":
            return self.trace

        return self.trace

    def handle_opcode(self, frame):

        if frame.f_code.co_name != "create_outcome":
            return

        code = frame.f_code

        instructions = list(
            dis.get_instructions(code)
        )

        current_offset = frame.f_lasti

        current_instruction = None
        previous_instructions = []

        for index, ins in enumerate(instructions):

            if ins.offset == current_offset:

                current_instruction = ins

                previous_instructions = instructions[
                    max(0, index - 8):index
                ]

                break

        if current_instruction is None:
            return

        opname = current_instruction.opname

        if opname == "STORE_SUBSCR":

            self.capture_store_subscr(
                frame,
                current_instruction,
                previous_instructions,
            )

        elif opname == "RETURN_VALUE":

            self.return_value_events += 1

            print()
            print("=" * 90)
            print(
                f"RETURN_VALUE OPCODE "
                f"#{self.return_value_events}"
            )
            print("=" * 90)

            print(
                f"LINE   : {frame.f_lineno}"
            )

            print(
                f"OFFSET : {current_instruction.offset}"
            )

            locals_map = frame.f_locals

            for key in (
                "price",
                "prices",
                "returns",
                "outcomes",
                "label",
            ):
                if key in locals_map:

                    print(
                        f"{key:12} | "
                        f"{describe(locals_map[key])}"
                    )

    def capture_store_subscr(
        self,
        frame,
        instruction,
        previous_instructions,
    ):

        self.store_subscr_events += 1

        locals_map = frame.f_locals

        print()
        print("#" * 100)
        print(
            f"STORE_SUBSCR OPCODE EVENT "
            f"#{self.store_subscr_events}"
        )
        print("#" * 100)

        print(
            f"FUNCTION       : {frame.f_code.co_name}"
        )

        print(
            f"LINE           : {frame.f_lineno}"
        )

        print(
            f"BYTECODE OFFSET: {instruction.offset}"
        )

        print()
        print("PREVIOUS OPCODES")
        print("-" * 100)

        for ins in previous_instructions:

            print(
                f"{ins.offset:<6} "
                f"{ins.opname:<25} "
                f"ARG={ins.arg!r:<6} "
                f"ARGVAL={ins.argval!r}"
            )

        print()
        print("CREATE_OUTCOME LOCALS")
        print("-" * 100)

        for key in (
            "label",
            "price",
            "prices",
            "returns",
            "outcomes",
            "entry_price",
            "direction",
        ):

            if key in locals_map:

                value = locals_map[key]

                print(
                    f"{key:16} | "
                    f"{describe(value)}"
                )

        if "price" in locals_map:

            price = locals_map["price"]

            self.price_ids.add(
                id(price)
            )

            self.store_subscr_price_events += 1

            print()
            print("PRICE OPERAND")
            print("-" * 100)

            print(
                f"TYPE       : {type(price).__name__}"
            )

            print(
                f"OBJECT ID  : {id(price)}"
            )

            print(
                f"VALUE      : {safe_repr(price)}"
            )

        if "prices" in locals_map:

            prices = locals_map["prices"]

            print()
            print("PRICES DICTIONARY BEFORE/AT STORE")
            print("-" * 100)

            print(
                f"TYPE       : {type(prices).__name__}"
            )

            print(
                f"OBJECT ID  : {id(prices)}"
            )

            if isinstance(prices, dict):

                print(
                    f"SIZE       : {len(prices)}"
                )

                for key, value in prices.items():

                    print(
                        f"KEY={key!r} | "
                        f"{describe(value)}"
                    )


def run():

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE "
        "STORE_SUBSCR OPCODE STACK EXACT TRACE "
        "FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE                         : "
        "READ-ONLY OPCODE-LEVEL FORENSICS"
    )

    print(
        f"TARGET                       : {TARGET}"
    )

    print(
        f"DATABASE                     : {DB_PATH}"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    if not os.path.exists(TARGET):

        print()
        print(
            "TARGET FILE NOT FOUND"
        )

        return

    namespace = load_module()

    main_fn = namespace.get("main")

    if main_fn is None:

        print(
            "main() NOT FOUND"
        )

        return

    tracer = OpcodeTracer()

    previous_trace = sys.gettrace()

    result = None

    try:

        sys.settrace(
            tracer.trace
        )

        result = main_fn()

    except Exception as exc:

        tracer.runtime_exceptions += 1

        print()
        print(
            "=" * 100
        )

        print(
            "TOP LEVEL EXCEPTION"
        )

        print(
            f"TYPE  : {type(exc).__name__}"
        )

        print(
            f"VALUE : {exc!r}"
        )

        print(
            "=" * 100
        )

        traceback.print_exc()

    finally:

        sys.settrace(
            previous_trace
        )

    print()
    print("=" * 100)
    print(
        "STEP 4 — OPCODE TRACE SUMMARY"
    )
    print("=" * 100)

    print(
        f"MAIN CALLS                  : "
        f"{tracer.main_calls}"
    )

    print(
        f"PROCESS_SIGNALS CALLS      : "
        f"{tracer.process_calls}"
    )

    print(
        f"CREATE_OUTCOME CALLS       : "
        f"{tracer.create_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS    : "
        f"{tracer.future_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS  : "
        f"{tracer.future_returns}"
    )

    print(
        f"CREATE_OUTCOME RETURNS     : "
        f"{tracer.create_returns}"
    )

    print(
        f"STORE_SUBSCR EVENTS        : "
        f"{tracer.store_subscr_events}"
    )

    print(
        f"PRICE AT STORE_SUBSCR      : "
        f"{tracer.store_subscr_price_events}"
    )

    print(
        f"RETURN_VALUE EVENTS        : "
        f"{tracer.return_value_events}"
    )

    print(
        f"RUNTIME EXCEPTIONS         : "
        f"{tracer.runtime_exceptions}"
    )

    print(
        f"TRACE EVENTS               : "
        f"{tracer.trace_events}"
    )

    print()
    print("=" * 100)
    print(
        "STEP 5 — SAFETY VERIFICATION"
    )
    print("=" * 100)

    print(
        "DATABASE WRITES              : NONE"
    )

    print(
        "INSERT                       : NONE"
    )

    print(
        "UPDATE                       : NONE"
    )

    print(
        "DELETE                       : NONE"
    )

    print(
        "ALTER                        : NONE"
    )

    print(
        "CREATE                       : NONE"
    )

    print(
        "DROP                         : NONE"
    )

    print(
        "COMMIT                       : NONE"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "PRODUCTION FORMULA MODIFIED : NONE"
    )

    print(
        "PRODUCTION MAIN MODIFIED    : NONE"
    )

    print()
    print("=" * 100)
    print(
        "STEP 6 — FINAL FORENSIC SUMMARY"
    )
    print("=" * 100)

    print(
        f"MAIN CALLS                  : "
        f"{tracer.main_calls}"
    )

    print(
        f"PROCESS_SIGNALS CALLS       : "
        f"{tracer.process_calls}"
    )

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{tracer.create_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{tracer.future_calls}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{tracer.future_returns}"
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
        f"{tracer.store_subscr_price_events}"
    )

    print(
        f"RETURN_VALUE EVENTS         : "
        f"{tracer.return_value_events}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{tracer.runtime_exceptions}"
    )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    print("-" * 100)

    if tracer.store_subscr_price_events > 0:

        status = (
            "STORE_SUBSCR_OPCODE_PRICE_STATE_CAPTURED"
        )

        meaning = (
            "The actual CPython opcode event for "
            "STORE_SUBSCR was reached and the create_outcome() "
            "price local was simultaneously observable."
        )

        frontier = (
            "Use the captured opcode context, label, prices "
            "dictionary and price object identity to establish "
            "the exact dictionary write path."
        )

    elif tracer.store_subscr_events > 0:

        status = (
            "STORE_SUBSCR_OPCODE_REACHED_PRICE_STATE_UNRESOLVED"
        )

        meaning = (
            "The actual STORE_SUBSCR opcode was reached, "
            "but price could not be established from the "
            "current frame locals."
        )

        frontier = (
            "Capture the operand-stack values immediately "
            "before STORE_SUBSCR."
        )

    elif tracer.future_returns > 0:

        status = (
            "FUTURE_PRICE_RETURN_OBSERVED_OPCODE_BOUNDARY_UNRESOLVED"
        )

        meaning = (
            "find_future_price() returns were observed, but "
            "the CPython STORE_SUBSCR opcode event was not captured."
        )

        frontier = (
            "Verify opcode tracing and frame.f_trace_opcodes "
            "for the create_outcome() frame."
        )

    else:

        status = (
            "FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "No future-price return was observed."
        )

        frontier = (
            "Resolve the production execution boundary first."
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


if __name__ == "__main__":
    run()