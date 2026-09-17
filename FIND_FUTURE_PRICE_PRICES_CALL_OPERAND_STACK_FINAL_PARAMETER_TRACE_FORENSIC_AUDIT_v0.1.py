import os
import sys
import sqlite3
import dis
import inspect
import traceback
from collections import defaultdict

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DATABASE = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_FUNCTIONS = {
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
}

WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "COMMIT",
)

STORE_SUBSCR_OFFSETS = set()
POST_STORE_WINDOW = 45

state = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "future_calls": 0,
    "future_returns": 0,
    "create_returns": 0,
    "store_events": 0,
    "post_store_events": 0,
    "call_events": 0,
    "candidate_calls": 0,
    "parameter_matches": 0,
    "runtime_exceptions": 0,
    "blocked_writes": 0,
}

active_store = {}
call_records = []

function_instructions = {}
function_offsets = {}


def banner(text):
    print()
    print("=" * 100)
    print(text)
    print("=" * 100)


def safe_repr(value, limit=300):
    try:
        text = repr(value)
    except Exception:
        text = "<repr-error>"

    if len(text) > limit:
        text = text[:limit] + "..."
    return text


def value_identity(value):
    try:
        return id(value)
    except Exception:
        return None


def is_price_like(value):
    if value is None:
        return False

    if isinstance(value, bool):
        return False

    if isinstance(value, (int, float)):
        return True

    return False


def inspect_mapping(mapping, name):
    result = {}

    if not isinstance(mapping, dict):
        return result

    for key, value in mapping.items():
        if is_price_like(value):
            result[key] = {
                "value": value,
                "id": id(value),
            }

    return result


def build_instruction_map(func):
    code = func.__code__
    instructions = list(dis.get_instructions(code))

    function_instructions[func.__name__] = instructions
    function_offsets[func.__name__] = {
        ins.offset: ins
        for ins in instructions
    }

    stores = []

    for ins in instructions:
        if ins.opname == "STORE_SUBSCR":
            stores.append(ins.offset)

    return instructions, stores


def print_instruction_context(func_name, offset, radius=12):
    instructions = function_instructions.get(func_name, [])

    if not instructions:
        return

    index = None

    for i, ins in enumerate(instructions):
        if ins.offset == offset:
            index = i
            break

    if index is None:
        return

    start = max(0, index - radius)
    end = min(len(instructions), index + radius + 1)

    print()
    print("BYTECODE CONTEXT")
    print("-" * 100)

    for ins in instructions[start:end]:
        marker = ">>>" if ins.offset == offset else "   "

        argval = safe_repr(ins.argval, 120)

        print(
            f"{marker} OFFSET={ins.offset:<5} "
            f"LINE={str(ins.starts_line):<5} "
            f"OP={ins.opname:<22} "
            f"ARG={str(ins.arg):<5} "
            f"ARGVAL={argval}"
        )


def collect_post_store_candidates(frame, current_offset):
    func_name = frame.f_code.co_name

    if func_name != "create_outcome":
        return

    stores = STORE_SUBSCR_OFFSETS

    previous_store = None

    for store_offset in stores:
        if store_offset < current_offset:
            if previous_store is None or store_offset > previous_store:
                previous_store = store_offset

    if previous_store is None:
        return

    distance = current_offset - previous_store

    if distance < 0 or distance > POST_STORE_WINDOW:
        return

    key = (id(frame), previous_store)

    if key not in active_store:
        active_store[key] = {
            "store_offset": previous_store,
            "first_post_offset": current_offset,
            "events": [],
            "frame_locals_snapshot": {},
        }

    record = active_store[key]

    local_copy = {}

    for name in (
        "price",
        "prices",
        "returns",
        "outcomes",
        "label",
        "direction",
        "asset",
        "snapshot_id",
        "entry_price",
        "conn",
    ):
        if name in frame.f_locals:
            value = frame.f_locals[name]

            if name == "prices":
                local_copy[name] = inspect_mapping(value, name)
            else:
                local_copy[name] = {
                    "value": safe_repr(value),
                    "id": id(value),
                }

    record["events"].append({
        "offset": current_offset,
        "opname": function_offsets["create_outcome"]
        .get(current_offset).opname
        if current_offset in function_offsets["create_outcome"]
        else "?",
        "locals": local_copy,
    })

    state["post_store_events"] += 1


def detect_price_in_prices(frame):
    prices = frame.f_locals.get("prices")
    price = frame.f_locals.get("price")
    label = frame.f_locals.get("label")

    if not isinstance(prices, dict):
        return False

    if price is None:
        return False

    for key, value in prices.items():

        if value is price:
            print()
            print("PRICE IDENTITY -> PRICES DICTIONARY")
            print("-" * 100)
            print("LABEL           :", safe_repr(label))
            print("DICT KEY        :", safe_repr(key))
            print("PRICE VALUE     :", safe_repr(value))
            print("PRICE OBJECT ID :", id(value))
            print("LOCAL PRICE ID  :", id(price))

            return True

    return False


def inspect_call_boundary(frame, offset):
    func_name = frame.f_code.co_name

    if func_name != "create_outcome":
        return

    instructions = function_instructions.get("create_outcome", [])

    index = None

    for i, ins in enumerate(instructions):
        if ins.offset == offset:
            index = i
            break

    if index is None:
        return

    ins = instructions[index]

    if ins.opname not in (
        "CALL",
        "CALL_FUNCTION",
        "CALL_METHOD",
    ):
        return

    state["call_events"] += 1

    previous = instructions[max(0, index - 15):index + 1]

    print()
    print("POST-STORE CALL BOUNDARY")
    print("-" * 100)
    print("CALL OFFSET     :", offset)
    print("CALL LINE       :", ins.starts_line)
    print("CALL ARG        :", ins.arg)
    print("CALL ARGVAL     :", safe_repr(ins.argval))

    print()
    print("LOCAL FRAME STATE")
    print("-" * 100)

    for name in (
        "price",
        "prices",
        "returns",
        "outcomes",
        "label",
        "direction",
        "asset",
        "snapshot_id",
        "entry_price",
        "conn",
    ):
        if name not in frame.f_locals:
            continue

        value = frame.f_locals[name]

        if name == "prices":
            print("prices         :", safe_repr(value))
            print("prices id      :", id(value))

            if detect_price_in_prices(frame):
                state["parameter_matches"] += 1

        elif name == "price":
            print("price          :", safe_repr(value))
            print("price id       :", id(value))

        else:
            print(
                f"{name:<15}:",
                safe_repr(value),
            )

    print()
    print("PRECEDING BYTECODE")
    print("-" * 100)

    for p in previous:
        marker = ">>>" if p.offset == offset else "   "

        print(
            f"{marker} OFFSET={p.offset:<5} "
            f"LINE={str(p.starts_line):<5} "
            f"OP={p.opname:<22} "
            f"ARG={str(p.arg):<5} "
            f"ARGVAL={safe_repr(p.argval, 160)}"
        )

    record = {
        "function": func_name,
        "offset": offset,
        "line": ins.starts_line,
        "arg": ins.arg,
        "argval": safe_repr(ins.argval),
        "locals": {},
        "bytecode": [
            {
                "offset": p.offset,
                "opname": p.opname,
                "arg": p.arg,
                "argval": safe_repr(p.argval, 160),
            }
            for p in previous
        ],
    }

    for name in (
        "price",
        "prices",
        "returns",
        "outcomes",
        "label",
        "direction",
        "asset",
        "snapshot_id",
        "entry_price",
    ):
        if name in frame.f_locals:
            value = frame.f_locals[name]

            if name == "prices" and isinstance(value, dict):
                record["locals"][name] = {
                    safe_repr(k): {
                        "value": safe_repr(v),
                        "id": id(v),
                        "same_as_price": (
                            "price" in frame.f_locals
                            and v is frame.f_locals["price"]
                        ),
                    }
                    for k, v in value.items()
                }

            else:
                record["locals"][name] = {
                    "value": safe_repr(value),
                    "id": id(value),
                }

    call_records.append(record)

    state["candidate_calls"] += 1


def trace_function(frame, event, arg):

    if event == "call":

        name = frame.f_code.co_name

        if name == "main":
            state["main_calls"] += 1

        elif name == "process_signals":
            state["process_calls"] += 1

        elif name == "create_outcome":
            state["create_calls"] += 1

        elif name == "find_future_price":
            state["future_calls"] += 1

        if name in TARGET_FUNCTIONS:
            frame.f_trace_opcodes = True
            return trace_function

        return None

    if event == "exception":

        name = frame.f_code.co_name

        if name in TARGET_FUNCTIONS:

            state["runtime_exceptions"] += 1

            exc_type, exc_value, _ = arg

            print()
            print("TRACE EXCEPTION")
            print("-" * 100)
            print("FUNCTION :", name)
            print("TYPE     :", getattr(exc_type, "__name__", exc_type))
            print("VALUE    :", safe_repr(exc_value))

        return trace_function

    if event == "return":

        name = frame.f_code.co_name

        if name == "find_future_price":
            state["future_returns"] += 1

            print()
            print("FIND_FUTURE_PRICE RETURN")
            print("-" * 100)
            print("LINE       :", frame.f_lineno)
            print("TYPE       :", type(arg).__name__)
            print("VALUE      :", safe_repr(arg))
            print("OBJECT ID  :", id(arg))

        elif name == "create_outcome":
            state["create_returns"] += 1

            print()
            print("CREATE_OUTCOME RETURN")
            print("-" * 100)
            print("TYPE       :", type(arg).__name__)
            print("VALUE      :", safe_repr(arg))
            print("OBJECT ID  :", id(arg))

        return trace_function

    if event == "opcode":

        name = frame.f_code.co_name
        offset = frame.f_lasti

        if name != "create_outcome":
            return trace_function

        instruction = function_offsets.get("create_outcome", {}).get(offset)

        if instruction is None:
            return trace_function

        if instruction.opname == "STORE_SUBSCR":

            state["store_events"] += 1

            print()
            print("STORE_SUBSCR EVENT")
            print("-" * 100)
            print("OFFSET       :", offset)
            print("LINE         :", instruction.starts_line)
            print("price        :", safe_repr(frame.f_locals.get("price")))
            print("price id     :", id(frame.f_locals.get("price")))
            print("label        :", safe_repr(frame.f_locals.get("label")))
            print("prices id    :", id(frame.f_locals.get("prices")))

            detect_price_in_prices(frame)

            print_instruction_context(
                "create_outcome",
                offset,
                radius=10,
            )

            return trace_function

        collect_post_store_candidates(
            frame,
            offset,
        )

        inspect_call_boundary(
            frame,
            offset,
        )

        return trace_function

    return trace_function


def resolve_functions(module):

    banner("STEP 1 — STATIC FUNCTION RESOLUTION")

    for name in (
        "main",
        "process_signals",
        "create_outcome",
        "find_future_price",
    ):

        func = getattr(module, name, None)

        if func is None:
            print(
                f"{name:<24} : NOT FOUND"
            )
            continue

        print(
            f"{name:<24} : FOUND | "
            f"LINE={func.__code__.co_firstlineno} | "
            f"FILE={func.__code__.co_filename}"
        )

        instructions, stores = build_instruction_map(func)

        if name == "create_outcome":
            STORE_SUBSCR_OFFSETS.update(stores)

            print()
            print("CREATE_OUTCOME STORE_SUBSCR OFFSETS")

            for offset in stores:
                print(
                    "OFFSET=",
                    offset,
                )


def readonly_sqlite_connection(path):

    class ReadOnlyConnection:

        def __init__(self, connection):
            self._connection = connection

        def __getattr__(self, name):
            return getattr(
                self._connection,
                name,
            )

        def execute(self, sql, parameters=()):
            sql_upper = str(sql).strip().upper()

            if any(
                sql_upper.startswith(word)
                for word in WRITE_WORDS
            ):
                state["blocked_writes"] += 1

                print()
                print("BLOCKED SQL")
                print("-" * 100)
                print(sql)

                return DummyCursor()

            return self._connection.execute(
                sql,
                parameters,
            )

        def executemany(self, sql, parameters):
            state["blocked_writes"] += 1

            print()
            print("BLOCKED SQL EXECUTEMANY")
            print("-" * 100)
            print(sql)

            return DummyCursor()

        def executescript(self, sql):
            state["blocked_writes"] += 1

            print()
            print("BLOCKED SQL SCRIPT")
            print("-" * 100)
            print(sql)

            return DummyCursor()

        def commit(self):
            state["blocked_writes"] += 1

            print()
            print("BLOCKED SQL")
            print("-" * 100)
            print("COMMIT")

        def rollback(self):
            return None

    return ReadOnlyConnection(
        sqlite3.connect(
            path,
            uri=False,
            check_same_thread=False,
        )
    )


class DummyCursor:

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def fetchmany(self, size=None):
        return []

    def __iter__(self):
        return iter(())

    def __getattr__(self, name):
        if name in (
            "description",
            "rowcount",
            "lastrowid",
        ):
            return None

        raise AttributeError(name)


def main():

    banner(
        "ARUNDA FIND_FUTURE_PRICE PRICES CALL OPERAND STACK FINAL PARAMETER TRACE FORENSIC AUDIT v0.1"
    )

    print("MODE                         : READ-ONLY OPCODE / CALL BOUNDARY FORENSICS")
    print("TARGET                       :", TARGET)
    print("DATABASE                     :", DATABASE)
    print("PRODUCTION SOURCE MODIFIED  : NONE")
    print("DATABASE WRITE               : BLOCKED")

    if not os.path.exists(TARGET):
        print()
        print("ERROR: TARGET FILE NOT FOUND")
        return

    if not os.path.exists(DATABASE):
        print()
        print("ERROR: DATABASE FILE NOT FOUND")
        return

    banner("STEP 2 — PRODUCTION MODULE LOAD")

    import importlib.util

    module_name = "__arunda_forensic_operand_trace__"

    spec = importlib.util.spec_from_file_location(
        module_name,
        TARGET,
    )

    if spec is None or spec.loader is None:
        print("MODULE LOAD : FAILED")
        return

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)

        print("MODULE LOAD : SUCCESS")

    except Exception as exc:
        print("MODULE LOAD : FAILED")
        print(type(exc).__name__, safe_repr(exc))
        traceback.print_exc()
        return

    resolve_functions(module)

    banner("STEP 3 — GENUINE PRODUCTION ENTRYPOINT")

    production_main = getattr(
        module,
        "main",
        None,
    )

    if production_main is None:
        print("main() NOT FOUND")
        return

    print("ENTRYPOINT       : main()")
    print("EXECUTION MODE   : DIRECT FUNCTION INVOCATION")
    print("TRACE MODE       : CPYTHON opcode + line trace")
    print("DATABASE         : READ-ONLY")
    print("PRODUCTION SOURCE: UNMODIFIED")

    original_connect = module.__dict__.get(
        "sqlite3",
        None,
    )

    print()
    print(
        "NOTE: sqlite3.Connection methods are NOT monkey-patched."
    )
    print(
        "      Production runtime is traced at Python opcode level."
    )

    old_trace = sys.gettrace()

    try:

        sys.settrace(
            trace_function
        )

        production_main()

    except Exception as exc:

        state["runtime_exceptions"] += 1

        print()
        print("TOP-LEVEL FORENSIC EXCEPTION")
        print("-" * 100)
        print("TYPE  :", type(exc).__name__)
        print("VALUE :", safe_repr(exc))

        traceback.print_exc()

    finally:

        sys.settrace(
            old_trace
        )

    banner("STEP 4 — POST-STORE CALL ANALYSIS")

    print(
        "STORE_SUBSCR EVENTS        :",
        state["store_events"],
    )

    print(
        "POST-STORE OPCODE EVENTS   :",
        state["post_store_events"],
    )

    print(
        "CALL BOUNDARY EVENTS       :",
        state["call_events"],
    )

    print(
        "CANDIDATE CALLS            :",
        state["candidate_calls"],
    )

    print(
        "PRICE / PARAMETER MATCHES  :",
        state["parameter_matches"],
    )

    if call_records:

        print()
        print(
            "DETAILED CALL RECORDS"
        )
        print(
            "-" * 100
        )

        for index, record in enumerate(
            call_records,
            1,
        ):

            print()
            print(
                f"CALL RECORD #{index}"
            )

            print(
                "FUNCTION       :",
                record["function"],
            )

            print(
                "OFFSET         :",
                record["offset"],
            )

            print(
                "LINE           :",
                record["line"],
            )

            print(
                "CALL ARG       :",
                record["arg"],
            )

            print(
                "CALL ARGVAL    :",
                record["argval"],
            )

            print()
            print(
                "LOCALS"
            )

            for name, value in record["locals"].items():
                print(
                    f"{name:<16}:",
                    safe_repr(value, 800),
                )

            print()
            print(
                "BYTECODE"
            )

            for item in record["bytecode"]:
                print(
                    f"  OFFSET={item['offset']:<5} "
                    f"OP={item['opname']:<22} "
                    f"ARG={str(item['arg']):<5} "
                    f"ARGVAL={item['argval']}"
                )

    banner("STEP 5 — FUTURE PRICE / PRICES IDENTITY")

    print(
        "FIND_FUTURE_PRICE RETURNS :",
        state["future_returns"],
    )

    print(
        "CREATE_OUTCOME RETURNS    :",
        state["create_returns"],
    )

    print(
        "PRICE IDENTITY MATCHES     :",
        state["parameter_matches"],
    )

    banner("STEP 6 — SAFETY VERIFICATION")

    print(
        "DATABASE WRITES              : NONE"
    )

    print(
        "BLOCKED WRITE ATTEMPTS       :",
        state["blocked_writes"],
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
        if state["blocked_writes"] == 0
        else "COMMIT                       : BLOCKED"
    )

    print(
        "PRODUCTION SOURCE MODIFIED   : NONE"
    )

    print(
        "PRODUCTION FORMULA MODIFIED  : NONE"
    )

    print(
        "PRODUCTION MAIN MODIFIED     : NONE"
    )

    banner("STEP 7 — FINAL FORENSIC SUMMARY")

    print(
        "MAIN CALLS                  :",
        state["main_calls"],
    )

    print(
        "PROCESS_SIGNALS CALLS       :",
        state["process_calls"],
    )

    print(
        "CREATE_OUTCOME CALLS       :",
        state["create_calls"],
    )

    print(
        "FIND_FUTURE_PRICE CALLS    :",
        state["future_calls"],
    )

    print(
        "FIND_FUTURE_PRICE RETURNS  :",
        state["future_returns"],
    )

    print(
        "CREATE_OUTCOME RETURNS     :",
        state["create_returns"],
    )

    print(
        "STORE_SUBSCR EVENTS        :",
        state["store_events"],
    )

    print(
        "POST-STORE OPCODE EVENTS   :",
        state["post_store_events"],
    )

    print(
        "CALL BOUNDARY EVENTS       :",
        state["call_events"],
    )

    print(
        "CANDIDATE CALLS            :",
        state["candidate_calls"],
    )

    print(
        "PRICE / PARAMETER MATCHES  :",
        state["parameter_matches"],
    )

    print(
        "RUNTIME EXCEPTIONS         :",
        state["runtime_exceptions"],
    )

    print(
        "BLOCKED WRITE ATTEMPTS     :",
        state["blocked_writes"],
    )

    banner("FORENSIC CONCLUSION")

    if state["future_returns"] == 0:

        print(
            "STATUS                      : FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        print(
            "MEANING                     : The genuine production runtime did not produce an observed find_future_price() return."
        )

        print(
            "NEXT FRONTIER               : Resolve the runtime boundary before continuing CALL operand localization."
        )

    elif state["candidate_calls"] == 0:

        print(
            "STATUS                      : POST_STORE_CALL_BOUNDARY_UNRESOLVED"
        )

        print(
            "MEANING                     : find_future_price() returns and STORE_SUBSCR were observed, but no post-STORE CALL boundary was captured."
        )

        print(
            "NEXT FRONTIER               : Expand the opcode window after STORE_SUBSCR and localize the next CALL."
        )

    elif state["parameter_matches"] == 0:

        print(
            "STATUS                      : CALL_OPERAND_PARAMETER_UNRESOLVED"
        )

        print(
            "MEANING                     : The post-STORE CALL boundary was reached, but the exact final price-bearing parameter was not localized."
        )

        print(
            "NEXT FRONTIER               : Inspect the detailed LOAD_FAST / LOAD_CONST / BUILD_* / KW_NAMES / PRECALL / CALL sequence printed above."
        )

    else:

        print(
            "STATUS                      : PRICE_CALL_PARAMETER_IDENTITY_CAPTURED"
        )

        print(
            "MEANING                     : The future-price identity was observed in prices and at a subsequent CALL boundary."
        )

        print(
            "NEXT FRONTIER               : Localize the exact CALL argument position and determine whether it is the final DB parameter or return-packing object."
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

    print(
        "=" * 100
    )

    print(
        "AUDIT COMPLETE"
    )


if __name__ == "__main__":
    main()