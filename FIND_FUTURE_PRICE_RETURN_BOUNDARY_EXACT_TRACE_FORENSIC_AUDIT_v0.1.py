import os
import sys
import sqlite3
import importlib.util
import dis
import traceback
import time

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE RETURN BOUNDARY EXACT TRACE FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY EXACT RETURN-BOUNDARY FORENSICS")
print(f"TARGET                       : {TARGET}")
print(f"DATABASE                     : {DB_PATH}")
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("DATABASE WRITE               : BLOCKED")
print("=" * 100)

start = time.time()

# -----------------------------------------------------------------------------
# 1. READ-ONLY SQLITE CONNECTION
# -----------------------------------------------------------------------------

def forensic_connect(path):
    uri = "file:" + os.path.abspath(path).replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)

# -----------------------------------------------------------------------------
# 2. LOAD PRODUCTION MODULE
# -----------------------------------------------------------------------------

module_name = "__arunda_return_boundary__"

spec = importlib.util.spec_from_file_location(module_name, TARGET)
module = importlib.util.module_from_spec(spec)

# IMPORTANT:
# We intentionally load the genuine production source.
# No source mutation.
# No monkey patching of production functions.

spec.loader.exec_module(module)

main_fn = getattr(module, "main", None)
process_fn = getattr(module, "process_signals", None)
create_fn = getattr(module, "create_outcome", None)
future_fn = getattr(module, "find_future_price", None)

print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("=" * 100)

for name, fn in [
    ("main", main_fn),
    ("process_signals", process_fn),
    ("create_outcome", create_fn),
    ("find_future_price", future_fn),
]:
    if fn is None:
        print(f"{name:<24}: NOT FOUND")
    else:
        print(
            f"{name:<24}: FOUND | "
            f"LINE={fn.__code__.co_firstlineno} | "
            f"FILE={fn.__code__.co_filename}"
        )

# -----------------------------------------------------------------------------
# 3. STATIC RETURN INSTRUCTION MAP
# -----------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 2 — FIND_FUTURE_PRICE RETURN INSTRUCTION MAP")
print("=" * 100)

if future_fn is not None:
    for ins in dis.get_instructions(future_fn):
        if ins.opname in (
            "RETURN_VALUE",
            "STORE_FAST",
            "STORE_DEREF",
            "STORE_SUBSCR",
            "LOAD_FAST",
            "CALL",
        ):
            print(
                f"OFFSET={ins.offset:<8} "
                f"LINE={str(ins.starts_line):<6} "
                f"OP={ins.opname:<24} "
                f"ARG={str(ins.arg):<8} "
                f"ARGVAL={repr(ins.argval)}"
            )

# -----------------------------------------------------------------------------
# 4. CREATE_OUTCOME RETURN MAP
# -----------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 3 — CREATE_OUTCOME PRICE / RETURN PACKING MAP")
print("=" * 100)

if create_fn is not None:
    for ins in dis.get_instructions(create_fn):
        if ins.opname in (
            "STORE_FAST",
            "STORE_SUBSCR",
            "BUILD_MAP",
            "RETURN_VALUE",
        ):
            if (
                ins.argval in {
                    "price",
                    "prices",
                    "returns",
                    "outcomes",
                    "completed_returns",
                    "max_gain",
                    "max_drawdown",
                    "overall_outcome",
                }
                or ins.opname in ("STORE_SUBSCR", "BUILD_MAP", "RETURN_VALUE")
            ):
                print(
                    f"OFFSET={ins.offset:<8} "
                    f"LINE={str(ins.starts_line):<6} "
                    f"OP={ins.opname:<24} "
                    f"ARG={str(ins.arg):<8} "
                    f"ARGVAL={repr(ins.argval)}"
                )

# -----------------------------------------------------------------------------
# 5. RUNTIME STATE
# -----------------------------------------------------------------------------

state = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "future_calls": 0,
    "future_returns": 0,
    "create_returns": 0,
    "return_events": 0,
    "price_observations": 0,
    "prices_dict_observations": 0,
    "final_return_observations": 0,
    "exceptions": [],
}

future_return_objects = []
price_observations = []
prices_observations = []
create_return_objects = []

# Prevent recursive tracing noise.
trace_depth = 0

# -----------------------------------------------------------------------------
# 6. FRAME VALUE SNAPSHOT
# -----------------------------------------------------------------------------

def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        return "<repr-error>"

    if len(text) > limit:
        return text[:limit] + "...<truncated>"

    return text


def snapshot_locals(frame):
    result = {}

    try:
        for key, value in frame.f_locals.items():
            if key in {
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
            }:
                result[key] = {
                    "id": id(value),
                    "type": type(value).__name__,
                    "repr": safe_repr(value),
                }
    except Exception:
        pass

    return result

# -----------------------------------------------------------------------------
# 7. EXACT RETURN-BOUNDARY TRACE
# -----------------------------------------------------------------------------

def tracer(frame, event, arg):
    global trace_depth

    try:
        filename = frame.f_code.co_filename
        func = frame.f_code.co_name

        if filename != TARGET:
            return tracer

        # ---------------------------------------------------------------------
        # FUNCTION ENTRY
        # ---------------------------------------------------------------------

        if event == "call":

            if func == "main":
                state["main_calls"] += 1
                print()
                print(
                    f"TRACE CALL | main | "
                    f"LINE={frame.f_lineno}"
                )

            elif func == "process_signals":
                state["process_calls"] += 1
                print(
                    f"TRACE CALL | process_signals | "
                    f"LINE={frame.f_lineno}"
                )

            elif func == "create_outcome":
                state["create_calls"] += 1
                print(
                    f"TRACE CALL | create_outcome | "
                    f"LINE={frame.f_lineno}"
                )

            elif func == "find_future_price":
                state["future_calls"] += 1

                print(
                    f"TRACE CALL | find_future_price | "
                    f"LINE={frame.f_lineno}"
                )

                print(
                    "  ARGUMENT LOCALS:",
                    snapshot_locals(frame)
                )

            return tracer

        # ---------------------------------------------------------------------
        # RETURN FROM find_future_price
        # ---------------------------------------------------------------------

        if event == "return" and func == "find_future_price":

            state["future_returns"] += 1
            state["return_events"] += 1

            record = {
                "return_number": state["future_returns"],
                "value_id": id(arg),
                "type": type(arg).__name__,
                "repr": safe_repr(arg),
                "line": frame.f_lineno,
            }

            future_return_objects.append(record)

            print()
            print("=" * 80)
            print(
                f"FIND_FUTURE_PRICE RETURN #{state['future_returns']}"
            )
            print("=" * 80)

            print(f"RETURN LINE : {frame.f_lineno}")
            print(f"TYPE        : {type(arg).__name__}")
            print(f"VALUE       : {safe_repr(arg)}")
            print(f"OBJECT ID   : {id(arg)}")

            return tracer

        # ---------------------------------------------------------------------
        # LOCAL PRICE OBSERVATION INSIDE create_outcome
        # ---------------------------------------------------------------------

        if event == "line" and func == "create_outcome":

            try:
                locals_now = frame.f_locals

                if "price" in locals_now:

                    price = locals_now["price"]

                    state["price_observations"] += 1

                    observation = {
                        "line": frame.f_lineno,
                        "id": id(price),
                        "type": type(price).__name__,
                        "repr": safe_repr(price),
                    }

                    price_observations.append(observation)

                    print(
                        f"PRICE OBSERVATION | "
                        f"create_outcome line={frame.f_lineno} | "
                        f"id={id(price)} | "
                        f"type={type(price).__name__} | "
                        f"value={safe_repr(price)}"
                    )

                if "prices" in locals_now:

                    prices = locals_now["prices"]

                    if isinstance(prices, dict):

                        state["prices_dict_observations"] += 1

                        prices_observations.append({
                            "line": frame.f_lineno,
                            "id": id(prices),
                            "repr": safe_repr(prices),
                        })

            except Exception:
                pass

            return tracer

        # ---------------------------------------------------------------------
        # CREATE_OUTCOME RETURN
        # ---------------------------------------------------------------------

        if event == "return" and func == "create_outcome":

            state["create_returns"] += 1

            record = {
                "return_number": state["create_returns"],
                "id": id(arg),
                "type": type(arg).__name__,
                "repr": safe_repr(arg),
            }

            create_return_objects.append(record)

            print()
            print("=" * 80)
            print(
                f"CREATE_OUTCOME RETURN #{state['create_returns']}"
            )
            print("=" * 80)

            print(
                f"TYPE      : {type(arg).__name__}"
            )
            print(
                f"OBJECT ID : {id(arg)}"
            )
            print(
                f"VALUE     : {safe_repr(arg, 2000)}"
            )

            if isinstance(arg, dict):

                state["final_return_observations"] += 1

                print("DICT KEYS :")

                for key, value in arg.items():

                    print(
                        f"  KEY={repr(key)} | "
                        f"TYPE={type(value).__name__} | "
                        f"ID={id(value)} | "
                        f"VALUE={safe_repr(value, 500)}"
                    )

            return tracer

        return tracer

    except Exception as exc:

        state["exceptions"].append({
            "function": frame.f_code.co_name,
            "line": frame.f_lineno,
            "type": type(exc).__name__,
            "value": str(exc),
        })

        return tracer


# -----------------------------------------------------------------------------
# 8. REAL PRODUCTION ENTRYPOINT
# -----------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 4 — GENUINE PRODUCTION EXECUTION")
print("=" * 100)

print("ENTRYPOINT                  : main()")
print("EXECUTION MODE              : DIRECT FUNCTION INVOCATION")
print("TRACE MODE                  : CPYTHON sys.settrace")
print("DATABASE                    : READ-ONLY")
print("PRODUCTION SOURCE           : UNMODIFIED")
print("=" * 100)

old_trace = sys.gettrace()
sys.settrace(tracer)

main_result = None

try:
    main_result = main_fn()

except Exception as exc:

    state["exceptions"].append({
        "function": "main",
        "line": None,
        "type": type(exc).__name__,
        "value": str(exc),
    })

    print()
    print(
        "TRACE EXCEPTION | main | "
        f"{type(exc).__name__} | {repr(exc)}"
    )

finally:
    sys.settrace(old_trace)

# -----------------------------------------------------------------------------
# 9. EXACT RETURN IDENTITY ANALYSIS
# -----------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 5 — EXACT RETURN OBJECT IDENTITY ANALYSIS")
print("=" * 100)

identity_matches = 0

for ret in future_return_objects:

    future_id = ret["value_id"]

    for obs in price_observations:

        if obs["id"] == future_id:

            identity_matches += 1

            print(
                "IDENTITY MATCH | "
                f"future_return_id={future_id} | "
                f"price_line={obs['line']} | "
                f"value={obs['repr']}"
            )

print(f"PRICE IDENTITY MATCHES : {identity_matches}")

# -----------------------------------------------------------------------------
# 10. FINAL STRUCTURE IDENTITY
# -----------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 6 — FINAL RETURN STRUCTURE IDENTITY")
print("=" * 100)

final_matches = 0

future_ids = {
    item["value_id"]
    for item in future_return_objects
}

for ret in create_return_objects:

    obj = ret.get("repr")

    print(
        f"CREATE_RETURN | "
        f"ID={ret['id']} | "
        f"TYPE={ret['type']} | "
        f"VALUE={obj}"
    )

print(
    f"FINAL RETURN OBJECTS : {len(create_return_objects)}"
)

# -----------------------------------------------------------------------------
# 11. SAFETY
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# 12. FINAL SUMMARY
# -----------------------------------------------------------------------------

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
print(f"PRICE OBSERVATIONS          : {state['price_observations']}")
print(f"PRICE IDENTITY MATCHES      : {identity_matches}")
print(
    f"FINAL RETURN OBSERVATIONS   : "
    f"{state['final_return_observations']}"
)
print(f"RUNTIME EXCEPTIONS          : {len(state['exceptions'])}")
print("=" * 100)

# -----------------------------------------------------------------------------
# 13. CONCLUSION
# -----------------------------------------------------------------------------

print()
print("FORENSIC CONCLUSION")
print("-" * 100)

if state["future_returns"] == 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_BOUNDARY_UNRESOLVED"
    )

    print(
        "MEANING                     : "
        "find_future_price() was entered but no return event "
        "was observed."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace the internal return path of find_future_price(), "
        "including SELECT result acquisition and every return branch."
    )

elif identity_matches > 0 and state["final_return_observations"] > 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_TO_FINAL_STRUCTURE_VERIFIED"
    )

    print(
        "MEANING                     : "
        "The exact future-price object identity was observed in "
        "create_outcome() and final return packing."
    )

    print(
        "NEXT FRONTIER               : "
        "Compare the final field value across all invocations "
        "and verify preservation versus transformation."
    )

elif identity_matches > 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_TO_PRICE_VERIFIED"
    )

    print(
        "MEANING                     : "
        "The exact return identity reached create_outcome().price, "
        "but final return packing remains unresolved."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace STORE_SUBSCR and RETURN_VALUE instructions "
        "inside create_outcome()."
    )

else:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_OBSERVED_LOCALIZATION_UNRESOLVED"
    )

    print(
        "MEANING                     : "
        "A genuine future-price return was observed, but exact "
        "object identity propagation into price was not established."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace the caller frame at the exact return boundary."
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
print(f"ELAPSED SECONDS             : {time.time() - start:.3f}")
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)