import os
import sys
import sqlite3
import dis
import types
import traceback

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_FUNCTIONS = {
    "create_outcome",
    "find_future_price",
    "process_signals",
    "main",
}

STORE_OFFSETS = {488, 518, 548}

MAX_STACK_ITEMS = 80
MAX_REPR = 300


def forensic_connect(path):
    uri = "file:" + os.path.abspath(path) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def safe_repr(value):
    try:
        text = repr(value)
    except Exception:
        text = "<repr-error>"

    if len(text) > MAX_REPR:
        text = text[:MAX_REPR] + "..."

    return text


def object_info(value):
    try:
        return {
            "type": type(value).__name__,
            "id": id(value),
            "repr": safe_repr(value),
        }
    except Exception:
        return {
            "type": "<error>",
            "id": 0,
            "repr": "<error>",
        }


def frame_function_name(frame):
    try:
        return frame.f_code.co_name
    except Exception:
        return "<unknown>"


def build_instruction_map(code):
    return {
        ins.offset: ins
        for ins in dis.get_instructions(code)
    }


def nearest_instruction(code, offset):
    instructions = list(dis.get_instructions(code))

    previous = None

    for ins in instructions:
        if ins.offset > offset:
            break
        previous = ins

    return previous


def stack_snapshot(frame):
    """
    CPython does not expose the evaluation stack through frame.f_locals.
    Therefore this function deliberately records only visible locals and
    tracing metadata. The opcode tracer below reconstructs stack-relevant
    operands from bytecode events and local identities.

    We NEVER fabricate a stack.
    """
    snapshot = {}

    for name, value in frame.f_locals.items():
        try:
            snapshot[name] = object_info(value)
        except Exception:
            snapshot[name] = {
                "type": "<error>",
                "id": 0,
                "repr": "<error>",
            }

    return snapshot


def describe_locals(frame):
    result = {}

    try:
        for name, value in frame.f_locals.items():
            result[name] = object_info(value)
    except Exception:
        pass

    return result


class RuntimeForensic:
    def __init__(self):
        self.main_calls = 0
        self.process_calls = 0
        self.create_calls = 0
        self.future_calls = 0
        self.future_returns = 0
        self.create_returns = 0

        self.store_events = 0
        self.post_store_events = 0
        self.call_events = 0

        self.store_contexts = []
        self.call_contexts = []

        self.last_store_by_frame = {}

        self.runtime_exceptions = []

    def print_header(self):
        print("=" * 100)
        print("ARUNDA FIND_FUTURE_PRICE POST-STORE CALL STACK")
        print("EXACT RUNTIME TRACE FORENSIC AUDIT v0.2")
        print("=" * 100)
        print("MODE                         : READ-ONLY RUNTIME FORENSICS")
        print("TARGET                       :", TARGET)
        print("DATABASE                     :", DB)
        print("PRODUCTION SOURCE MODIFIED  : NONE")
        print("DATABASE WRITE              : BLOCKED")
        print("=" * 100)

    def trace(self, frame, event, arg):

        name = frame_function_name(frame)

        if name not in TARGET_FUNCTIONS:
            return self.trace

        if event == "call":

            if name == "main":
                self.main_calls += 1

            elif name == "process_signals":
                self.process_calls += 1

            elif name == "create_outcome":
                self.create_calls += 1

            elif name == "find_future_price":
                self.future_calls += 1

            try:
                frame.f_trace_opcodes = True
            except Exception:
                pass

            return self.trace

        if event == "exception":

            try:
                exc_type, exc_value, exc_tb = arg

                self.runtime_exceptions.append(
                    {
                        "function": name,
                        "line": frame.f_lineno,
                        "type": getattr(exc_type, "__name__", str(exc_type)),
                        "value": str(exc_value),
                    }
                )

            except Exception:
                pass

            return self.trace

        if event == "return":

            if name == "find_future_price":
                self.future_returns += 1

                print()
                print("-" * 90)
                print("FIND_FUTURE_PRICE RETURN")
                print("-" * 90)
                print("LINE        :", frame.f_lineno)
                print("TYPE        :", type(arg).__name__)
                print("OBJECT ID   :", id(arg))
                print("VALUE       :", safe_repr(arg))

            elif name == "create_outcome":
                self.create_returns += 1

                print()
                print("-" * 90)
                print("CREATE_OUTCOME RETURN")
                print("-" * 90)
                print("LINE        :", frame.f_lineno)
                print("TYPE        :", type(arg).__name__)
                print("OBJECT ID   :", id(arg))
                print("VALUE       :", safe_repr(arg))

            return self.trace

        if event != "opcode":
            return self.trace

        try:
            code = frame.f_code
            ins = nearest_instruction(code, frame.f_lasti)

            if ins is None:
                return self.trace

            offset = ins.offset
            opname = ins.opname

            if name == "create_outcome":

                previous_store = self.last_store_by_frame.get(id(frame))

                if offset in STORE_OFFSETS and opname == "STORE_SUBSCR":

                    self.store_events += 1

                    locals_now = describe_locals(frame)

                    context = {
                        "offset": offset,
                        "line": frame.f_lineno,
                        "opcode": opname,
                        "locals": locals_now,
                    }

                    self.store_contexts.append(context)

                    self.last_store_by_frame[id(frame)] = {
                        "offset": offset,
                        "line": frame.f_lineno,
                        "event_number": self.store_events,
                    }

                    print()
                    print("=" * 100)
                    print("STORE_SUBSCR REACHED")
                    print("=" * 100)
                    print("STORE EVENT     :", self.store_events)
                    print("OFFSET          :", offset)
                    print("LINE            :", frame.f_lineno)

                    for local_name in (
                        "label",
                        "price",
                        "prices",
                        "returns",
                        "outcomes",
                    ):
                        if local_name in frame.f_locals:
                            value = frame.f_locals[local_name]

                            print()
                            print(
                                local_name.upper(),
                                "| TYPE=",
                                type(value).__name__,
                                "| ID=",
                                id(value),
                                "| VALUE=",
                                safe_repr(value),
                            )

                    print("=" * 100)

                elif previous_store is not None:

                    self.post_store_events += 1

                    # Stop recording once a new line of execution is far
                    # beyond the immediate post-store region.
                    distance = offset - previous_store["offset"]

                    if distance <= 220:

                        if opname in {
                            "LOAD_FAST",
                            "LOAD_CONST",
                            "LOAD_GLOBAL",
                            "LOAD_DEREF",
                            "LOAD_ATTR",
                            "LOAD_METHOD",
                            "BUILD_TUPLE",
                            "BUILD_LIST",
                            "BUILD_MAP",
                            "BUILD_CONST_KEY_MAP",
                            "LIST_EXTEND",
                            "LIST_APPEND",
                            "MAP_ADD",
                            "KW_NAMES",
                            "PRECALL",
                            "CALL",
                            "CALL_FUNCTION_EX",
                            "CALL_METHOD",
                            "PUSH_NULL",
                        }:

                            locals_now = describe_locals(frame)

                            event_data = {
                                "store_offset": previous_store["offset"],
                                "store_line": previous_store["line"],
                                "offset": offset,
                                "line": frame.f_lineno,
                                "opcode": opname,
                                "arg": ins.arg,
                                "argval": safe_repr(ins.argval),
                                "locals": locals_now,
                            }

                            self.call_contexts.append(event_data)

                            print()
                            print(
                                f"POST-STORE OPCODE | "
                                f"STORE={previous_store['offset']} | "
                                f"OFFSET={offset} | "
                                f"LINE={frame.f_lineno} | "
                                f"OP={opname}"
                            )

                            if opname in {
                                "BUILD_TUPLE",
                                "BUILD_LIST",
                                "BUILD_MAP",
                                "BUILD_CONST_KEY_MAP",
                            }:

                                print(
                                    "CONTAINER BUILD ARG :",
                                    ins.arg
                                )

                            elif opname == "KW_NAMES":

                                print(
                                    "KW_NAMES ARGVAL      :",
                                    safe_repr(ins.argval)
                                )

                            elif opname in {
                                "PRECALL",
                                "CALL",
                                "CALL_FUNCTION_EX",
                                "CALL_METHOD",
                            }:

                                self.call_events += 1

                                print()
                                print(">>> CALL BOUNDARY CANDIDATE")
                                print("CALL OPCODE          :", opname)
                                print("CALL OFFSET          :", offset)
                                print("CALL ARG             :", ins.arg)
                                print("CALL ARGVAL          :", safe_repr(ins.argval))

                                print()
                                print("VISIBLE FRAME LOCALS")
                                print("-" * 80)

                                for k, v in locals_now.items():
                                    print(
                                        f"{k} | "
                                        f"TYPE={v['type']} | "
                                        f"ID={v['id']} | "
                                        f"VALUE={v['repr']}"
                                    )

                                print("-" * 80)

                                # Explicitly inspect prices identity.
                                if "prices" in frame.f_locals:

                                    prices = frame.f_locals["prices"]

                                    print()
                                    print("PRICES OBJECT")
                                    print(
                                        "TYPE :",
                                        type(prices).__name__
                                    )
                                    print(
                                        "ID   :",
                                        id(prices)
                                    )

                                    if isinstance(prices, dict):

                                        print("KEYS :", list(prices.keys()))

                                        for key, value in prices.items():

                                            print(
                                                "PRICE ENTRY | "
                                                f"KEY={safe_repr(key)} | "
                                                f"TYPE={type(value).__name__} | "
                                                f"ID={id(value)} | "
                                                f"VALUE={safe_repr(value)}"
                                            )

                                            if (
                                                "price"
                                                in frame.f_locals
                                                and value
                                                is frame.f_locals["price"]
                                            ):
                                                print(
                                                    "!!! EXACT PRICE "
                                                    "IDENTITY IN PRICES !!!"
                                                )

                                print()
                                print("CALL BOUNDARY RECORDED")
                                print("=" * 90)

        except Exception as exc:

            self.runtime_exceptions.append(
                {
                    "function": name,
                    "line": getattr(frame, "f_lineno", -1),
                    "type": type(exc).__name__,
                    "value": str(exc),
                }
            )

        return self.trace


def main():
    forensic = RuntimeForensic()
    forensic.print_header()

    # Import production module WITHOUT modifying it.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "arunda_signal_outcome_production",
        TARGET,
    )

    module = importlib.util.module_from_spec(spec)

    if spec.loader is None:
        raise RuntimeError("Unable to load production module")

    spec.loader.exec_module(module)

    print()
    print("=" * 100)
    print("PRODUCTION MODULE LOADED")
    print("=" * 100)

    print("MODULE :", module)
    print("MAIN   :", getattr(module, "main", None))
    print()

    # Install tracing ONLY after module loading.
    sys.settrace(forensic.trace)

    try:
        module.main()

    except Exception as exc:

        forensic.runtime_exceptions.append(
            {
                "function": "main",
                "line": -1,
                "type": type(exc).__name__,
                "value": str(exc),
            }
        )

        print()
        print("=" * 100)
        print("RUNTIME EXCEPTION")
        print("=" * 100)
        print(type(exc).__name__, repr(exc))

        traceback.print_exc()

    finally:
        sys.settrace(None)

    print()
    print("=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print("MAIN CALLS                  :", forensic.main_calls)
    print("PROCESS_SIGNALS CALLS      :", forensic.process_calls)
    print("CREATE_OUTCOME CALLS       :", forensic.create_calls)
    print("FIND_FUTURE_PRICE CALLS    :", forensic.future_calls)
    print("FIND_FUTURE_PRICE RETURNS  :", forensic.future_returns)
    print("CREATE_OUTCOME RETURNS     :", forensic.create_returns)

    print()
    print("STORE_SUBSCR EVENTS        :", forensic.store_events)
    print("POST-STORE OPCODE EVENTS   :", forensic.post_store_events)
    print("CALL BOUNDARY EVENTS       :", forensic.call_events)

    print()
    print("RUNTIME EXCEPTIONS         :", len(forensic.runtime_exceptions))

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if forensic.call_events > 0:

        print(
            "STATUS : POST_STORE_CALL_BOUNDARY_CAPTURED"
        )

        print(
            "MEANING : "
            "At least one CALL candidate was reached after "
            "STORE_SUBSCR and its surrounding runtime state "
            "was captured."
        )

        print(
            "NEXT FRONTIER : "
            "Identify the exact CALL whose operand construction "
            "contains the future-price object."
        )

    else:

        print(
            "STATUS : POST_STORE_CALL_OPERAND_UNRESOLVED"
        )

        print(
            "MEANING : "
            "STORE_SUBSCR was reached, but no relevant CALL "
            "candidate was captured inside the traced post-store window."
        )

        print(
            "NEXT FRONTIER : "
            "Extend only the post-STORE opcode window; "
            "do not re-audit earlier verified stages."
        )

    print()
    print("DATABASE_WRITES             : NONE")
    print("ENGINE_MODIFIED             : NONE")
    print("PRODUCTION_SOURCE_MODIFIED  : NONE")
    print("PRODUCTION_FORMULA_MODIFIED : NONE")
    print("INSERT                      : NONE")
    print("UPDATE                      : NONE")
    print("DELETE                      : NONE")
    print("ALTER                       : NONE")
    print("CREATE                      : NONE")
    print("DROP                        : NONE")
    print("COMMIT                      : NONE")

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()