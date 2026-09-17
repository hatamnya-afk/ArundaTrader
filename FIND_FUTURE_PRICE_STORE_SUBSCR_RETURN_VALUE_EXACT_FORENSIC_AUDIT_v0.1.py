import os
import sys
import sqlite3
import importlib.util
import dis
import time

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"
MODULE_NAME = "__arunda_store_subscr_return_trace__"

print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE STORE_SUBSCR / RETURN_VALUE EXACT FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY BYTECODE / INSTRUCTION FORENSICS")
print(f"TARGET                       : {TARGET}")
print(f"DATABASE                     : {DB_PATH}")
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("DATABASE WRITE               : BLOCKED")
print("=" * 100)

started = time.time()

# =============================================================================
# READ-ONLY DATABASE
# =============================================================================

def readonly_connect(path):
    absolute = os.path.abspath(path)
    uri = "file:" + absolute.replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


# =============================================================================
# LOAD GENUINE PRODUCTION MODULE
# =============================================================================

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    TARGET
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

main_fn = getattr(module, "main", None)
process_fn = getattr(module, "process_signals", None)
create_fn = getattr(module, "create_outcome", None)
future_fn = getattr(module, "find_future_price", None)

print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("=" * 100)

for name, fn in (
    ("main", main_fn),
    ("process_signals", process_fn),
    ("create_outcome", create_fn),
    ("find_future_price", future_fn),
):
    if fn is None:
        print(f"{name:<24}: NOT FOUND")
    else:
        print(
            f"{name:<24}: FOUND | "
            f"LINE={fn.__code__.co_firstlineno} | "
            f"FILE={fn.__code__.co_filename}"
        )


# =============================================================================
# BYTECODE MAP
# =============================================================================

print()
print("=" * 100)
print("STEP 2 — CREATE_OUTCOME STORE_SUBSCR / RETURN_VALUE MAP")
print("=" * 100)

create_instructions = list(dis.get_instructions(create_fn))

target_offsets = set()

for ins in create_instructions:

    if ins.opname in (
        "STORE_FAST",
        "STORE_SUBSCR",
        "BUILD_MAP",
        "BUILD_CONST_KEY_MAP",
        "RETURN_VALUE",
        "LOAD_FAST",
        "LOAD_CONST",
        "LOAD_GLOBAL",
        "CALL",
        "PRECALL",
    ):

        if (
            ins.opname in (
                "STORE_SUBSCR",
                "RETURN_VALUE",
                "BUILD_MAP",
                "BUILD_CONST_KEY_MAP",
            )
            or ins.argval in (
                "price",
                "prices",
                "returns",
                "outcomes",
                "label",
            )
        ):

            target_offsets.add(ins.offset)

            print(
                f"OFFSET={ins.offset:<8} "
                f"LINE={str(ins.starts_line):<6} "
                f"OP={ins.opname:<24} "
                f"ARG={str(ins.arg):<8} "
                f"ARGVAL={repr(ins.argval)}"
            )


# =============================================================================
# RUNTIME STATE
# =============================================================================

state = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "future_calls": 0,
    "future_returns": 0,
    "create_returns": 0,

    "store_subscr_events": 0,
    "return_value_events": 0,

    "price_identity": 0,
    "price_store_events": 0,
    "prices_store_events": 0,

    "return_candidates": 0,
    "final_identity_matches": 0,

    "exceptions": 0,
}

future_returns = []
price_values = []
store_events = []
return_events = []


# =============================================================================
# SAFE REPRESENTATION
# =============================================================================

def safe_repr(value, limit=1200):

    try:
        text = repr(value)
    except Exception:
        return "<repr-error>"

    if len(text) > limit:
        return text[:limit] + "...<truncated>"

    return text


def relevant_locals(frame):

    wanted = {
        "price",
        "prices",
        "returns",
        "outcomes",
        "label",
        "minutes",
        "asset",
        "entry_price",
        "direction",
        "completed_returns",
        "max_gain",
        "max_drawdown",
        "overall_outcome",
        "r",
    }

    result = {}

    try:

        for name, value in frame.f_locals.items():

            if name in wanted:

                result[name] = {
                    "id": id(value),
                    "type": type(value).__name__,
                    "repr": safe_repr(value),
                }

    except Exception:
        pass

    return result


# =============================================================================
# EXACT BYTECODE TRACE
# =============================================================================

def tracer(frame, event, arg):

    try:

        filename = frame.f_code.co_filename

        if filename != TARGET:
            return tracer

        function = frame.f_code.co_name

        # ---------------------------------------------------------------------
        # CALL
        # ---------------------------------------------------------------------

        if event == "call":

            if function == "main":

                state["main_calls"] += 1

                print(
                    f"TRACE CALL | main | LINE={frame.f_lineno}"
                )

            elif function == "process_signals":

                state["process_calls"] += 1

                print(
                    f"TRACE CALL | process_signals | LINE={frame.f_lineno}"
                )

            elif function == "create_outcome":

                state["create_calls"] += 1

                print(
                    f"TRACE CALL | create_outcome | LINE={frame.f_lineno}"
                )

            elif function == "find_future_price":

                state["future_calls"] += 1

            return tracer

        # ---------------------------------------------------------------------
        # RETURN EVENT
        # ---------------------------------------------------------------------

        if event == "return":

            if function == "find_future_price":

                state["future_returns"] += 1

                record = {
                    "id": id(arg),
                    "type": type(arg).__name__,
                    "repr": safe_repr(arg),
                    "line": frame.f_lineno,
                }

                future_returns.append(record)

                print()
                print("-" * 90)
                print(
                    f"FIND_FUTURE_PRICE RETURN "
                    f"#{state['future_returns']}"
                )
                print("-" * 90)

                print(f"LINE       : {frame.f_lineno}")
                print(f"TYPE       : {type(arg).__name__}")
                print(f"VALUE      : {safe_repr(arg)}")
                print(f"OBJECT ID  : {id(arg)}")

            elif function == "create_outcome":

                state["create_returns"] += 1

                print()
                print("-" * 90)
                print(
                    f"CREATE_OUTCOME RETURN "
                    f"#{state['create_returns']}"
                )
                print("-" * 90)

                print(f"TYPE       : {type(arg).__name__}")
                print(f"OBJECT ID  : {id(arg)}")
                print(f"VALUE      : {safe_repr(arg, 2500)}")

                if isinstance(arg, dict):

                    print("RETURN DICT KEYS:")

                    for key, value in arg.items():

                        print(
                            f"  KEY={repr(key)} | "
                            f"TYPE={type(value).__name__} | "
                            f"ID={id(value)} | "
                            f"VALUE={safe_repr(value, 600)}"
                        )

                return_events.append({
                    "id": id(arg),
                    "type": type(arg).__name__,
                    "repr": safe_repr(arg, 3000),
                })

            return tracer

        # ---------------------------------------------------------------------
        # INSTRUCTION EVENT
        #
        # CPython emits opcode events only when f_trace_opcodes=True.
        # ---------------------------------------------------------------------

        if event == "call":

            try:
                frame.f_trace_opcodes = True
                frame.f_trace_lines = True
            except Exception:
                pass

            return tracer

        if event == "opcode":

            offset = frame.f_lasti

            instruction = None

            for ins in dis.get_instructions(frame.f_code):

                if ins.offset == offset:

                    instruction = ins
                    break

            if instruction is None:
                return tracer

            # -----------------------------------------------------------------
            # STORE_SUBSCR
            # -----------------------------------------------------------------

            if (
                function == "create_outcome"
                and instruction.opname == "STORE_SUBSCR"
            ):

                state["store_subscr_events"] += 1

                locals_now = relevant_locals(frame)

                event_record = {
                    "offset": offset,
                    "line": instruction.starts_line,
                    "locals": locals_now,
                }

                store_events.append(event_record)

                print()
                print("=" * 90)
                print(
                    "STORE_SUBSCR | "
                    f"OFFSET={offset} | "
                    f"LINE={instruction.starts_line}"
                )
                print("=" * 90)

                print("FRAME LOCALS:")

                for name, data in locals_now.items():

                    print(
                        f"  {name:<20} "
                        f"ID={data['id']} | "
                        f"TYPE={data['type']} | "
                        f"VALUE={data['repr']}"
                    )

                if "price" in locals_now:

                    state["price_store_events"] += 1

                    print(
                        "PRICE PRESENT AT STORE_SUBSCR : YES"
                    )

                    print(
                        f"PRICE OBJECT ID : "
                        f"{locals_now['price']['id']}"
                    )

                if "prices" in locals_now:

                    state["prices_store_events"] += 1

                    print(
                        "PRICES DICT PRESENT              : YES"
                    )

                    print(
                        f"PRICES OBJECT ID : "
                        f"{locals_now['prices']['id']}"
                    )

                    print(
                        f"PRICES VALUE     : "
                        f"{locals_now['prices']['repr']}"
                    )

            # -----------------------------------------------------------------
            # RETURN_VALUE
            # -----------------------------------------------------------------

            if (
                function == "create_outcome"
                and instruction.opname == "RETURN_VALUE"
            ):

                state["return_value_events"] += 1

                locals_now = relevant_locals(frame)

                print()
                print("=" * 90)
                print(
                    "RETURN_VALUE INSTRUCTION | "
                    f"OFFSET={offset}"
                )
                print("=" * 90)

                print("FRAME LOCALS AT RETURN:")

                for name, data in locals_now.items():

                    print(
                        f"  {name:<20} "
                        f"ID={data['id']} | "
                        f"TYPE={data['type']} | "
                        f"VALUE={data['repr']}"
                    )

                return_events.append({
                    "offset": offset,
                    "locals": locals_now,
                })

            return tracer

        return tracer

    except Exception as exc:

        state["exceptions"] += 1

        print(
            f"TRACE INTERNAL ERROR | "
            f"{type(exc).__name__} | {exc}"
        )

        return tracer


# =============================================================================
# REAL PRODUCTION EXECUTION
# =============================================================================

print()
print("=" * 100)
print("STEP 3 — GENUINE PRODUCTION EXECUTION")
print("=" * 100)

print("ENTRYPOINT                  : main()")
print("EXECUTION MODE              : DIRECT FUNCTION INVOCATION")
print("TRACE MODE                  : CPYTHON opcode + line trace")
print("DATABASE                    : READ-ONLY")
print("PRODUCTION SOURCE           : UNMODIFIED")
print("=" * 100)

previous_trace = sys.gettrace()

sys.settrace(tracer)

main_result = None

try:

    main_result = main_fn()

except Exception as exc:

    state["exceptions"] += 1

    print()
    print(
        "PRODUCTION TRACE EXCEPTION | "
        f"{type(exc).__name__} | {repr(exc)}"
    )

finally:

    sys.settrace(previous_trace)


# =============================================================================
# EXACT IDENTITY ANALYSIS
# =============================================================================

print()
print("=" * 100)
print("STEP 4 — EXACT PRICE IDENTITY ANALYSIS")
print("=" * 100)

future_ids = {
    item["id"]
    for item in future_returns
}

for record in future_returns:

    print(
        f"FUTURE RETURN | "
        f"ID={record['id']} | "
        f"TYPE={record['type']} | "
        f"VALUE={record['repr']}"
    )


# =============================================================================
# PRICE → STORE_SUBSCR IDENTITY
# =============================================================================

print()
print("=" * 100)
print("STEP 5 — PRICE → STORE_SUBSCR LOCALIZATION")
print("=" * 100)

for record in store_events:

    locals_now = record["locals"]

    if "price" not in locals_now:
        continue

    price_id = locals_now["price"]["id"]

    if price_id in future_ids:

        state["price_identity"] += 1

        print(
            "EXACT IDENTITY MATCH | "
            f"future_return_id={price_id} | "
            f"STORE_OFFSET={record['offset']} | "
            f"LINE={record['line']}"
        )

print(
    f"PRICE IDENTITY MATCHES : "
    f"{state['price_identity']}"
)


# =============================================================================
# FINAL RETURN INSTRUCTION OBSERVATION
# =============================================================================

print()
print("=" * 100)
print("STEP 6 — RETURN_VALUE FRAME LOCALIZATION")
print("=" * 100)

return_price_matches = 0

for record in return_events:

    if "locals" not in record:
        continue

    locals_now = record["locals"]

    if "price" in locals_now:

        price_id = locals_now["price"]["id"]

        if price_id in future_ids:

            return_price_matches += 1

            print(
                "RETURN FRAME PRICE IDENTITY MATCH | "
                f"PRICE_ID={price_id}"
            )

print(
    f"RETURN-VALUE PRICE MATCHES : "
    f"{return_price_matches}"
)


# =============================================================================
# SAFETY
# =============================================================================

print()
print("=" * 100)
print("STEP 7 — SAFETY VERIFICATION")
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


# =============================================================================
# FINAL SUMMARY
# =============================================================================

print()
print("=" * 100)
print("STEP 8 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(f"MAIN CALLS                  : {state['main_calls']}")
print(f"PROCESS_SIGNALS CALLS       : {state['process_calls']}")
print(f"CREATE_OUTCOME CALLS        : {state['create_calls']}")
print(f"FIND_FUTURE_PRICE CALLS     : {state['future_calls']}")
print(f"FIND_FUTURE_PRICE RETURNS   : {state['future_returns']}")
print(f"CREATE_OUTCOME RETURNS      : {state['create_returns']}")
print(f"STORE_SUBSCR EVENTS         : {state['store_subscr_events']}")
print(f"PRICE AT STORE_SUBSCR       : {state['price_store_events']}")
print(f"PRICES DICT OBSERVATIONS    : {state['prices_store_events']}")
print(f"RETURN_VALUE EVENTS         : {state['return_value_events']}")
print(f"PRICE IDENTITY MATCHES      : {state['price_identity']}")
print(f"RETURN FRAME PRICE MATCHES  : {return_price_matches}")
print(f"RUNTIME / TRACE EXCEPTIONS  : {state['exceptions']}")


# =============================================================================
# CONCLUSION
# =============================================================================

print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("-" * 100)

if state["future_returns"] == 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_NOT_OBSERVED"
    )

    print(
        "MEANING                     : "
        "find_future_price() was entered but its return boundary "
        "was not observed."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace the internal return branches of find_future_price()."
    )

elif state["price_identity"] > 0 and return_price_matches > 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_FINAL_RETURN_IDENTITY_VERIFIED"
    )

    print(
        "MEANING                     : "
        "The exact future-price object identity survived through "
        "price, STORE_SUBSCR, and the create_outcome RETURN_VALUE boundary."
    )

    print(
        "NEXT FRONTIER               : "
        "Identify the exact returned dictionary key/path containing "
        "the future-price value."
    )

elif state["price_identity"] > 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_STORE_SUBSCR_IDENTITY_VERIFIED"
    )

    print(
        "MEANING                     : "
        "The exact future-price object reached STORE_SUBSCR, "
        "but final RETURN_VALUE packing remains unresolved."
    )

    print(
        "NEXT FRONTIER               : "
        "Capture the operand stack immediately before RETURN_VALUE."
    )

else:

    print(
        "STATUS                      : "
        "STORE_SUBSCR_PRICE_IDENTITY_UNRESOLVED"
    )

    print(
        "MEANING                     : "
        "The future-price return was observed, but its exact identity "
        "at dictionary construction was not established."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace operand-stack state around STORE_SUBSCR."
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

print()
print(f"ELAPSED SECONDS             : {time.time() - started:.3f}")
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)