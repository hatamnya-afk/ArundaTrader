import os
import sys
import sqlite3
import dis
import inspect
import types
import traceback
from collections import defaultdict


TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE PRICES FINAL RETURN DB PACKING EXACT TRACE FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY FINAL PACKING FORENSICS")
print(f"TARGET                       : {TARGET}")
print(f"DATABASE                     : {DB_PATH}")
print("PRODUCTION SOURCE MODIFIED   : NONE")
print("PRODUCTION DATABASE WRITES   : NONE")
print("DATABASE MODE                : IN-MEMORY CLONE")
print("=" * 100)


# ---------------------------------------------------------------------------
# 1. STATIC FUNCTION RESOLUTION
# ---------------------------------------------------------------------------

source = open(TARGET, "r", encoding="utf-8").read()

module = types.ModuleType("__forensic_runtime__")
module.__file__ = TARGET

sys.modules["__forensic_runtime__"] = module

exec(compile(source, TARGET, "exec"), module.__dict__)


main = module.main
process_signals = module.process_signals
create_outcome = module.create_outcome
find_future_price = module.find_future_price


print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("-" * 100)

for fn_name, fn in [
    ("main", main),
    ("process_signals", process_signals),
    ("create_outcome", create_outcome),
    ("find_future_price", find_future_price),
]:
    print(
        f"{fn_name:<24} : FOUND | "
        f"LINE={fn.__code__.co_firstlineno} | "
        f"FILE={fn.__code__.co_filename}"
    )


# ---------------------------------------------------------------------------
# 2. BYTECODE FINAL PACKING MAP
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 2 — CREATE_OUTCOME FINAL PACKING BYTECODE MAP")
print("-" * 100)

create_instructions = list(dis.get_instructions(create_outcome))

target_offsets = {
    ins.offset
    for ins in create_instructions
    if ins.opname in {
        "STORE_SUBSCR",
        "RETURN_VALUE",
        "LOAD_FAST",
        "LOAD_GLOBAL",
        "LOAD_ATTR",
        "CALL",
        "CALL_FUNCTION",
        "CALL_METHOD",
        "PRECALL",
    }
}

for ins in create_instructions:
    if ins.offset in target_offsets:
        argval = repr(ins.argval)
        print(
            f"OFFSET={ins.offset:<8} "
            f"LINE={str(ins.starts_line):<6} "
            f"OP={ins.opname:<25} "
            f"ARG={str(ins.arg):<8} "
            f"ARGVAL={argval}"
        )


# ---------------------------------------------------------------------------
# 3. SQLITE IN-MEMORY CLONE
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 3 — READ-ONLY DATABASE CLONE")
print("-" * 100)


real_conn = sqlite3.connect(DB_PATH)

clone_conn = sqlite3.connect(":memory:")

real_conn.backup(clone_conn)

real_conn.close()


sql_trace = []


def sql_trace_callback(statement):
    sql_trace.append(statement)


clone_conn.set_trace_callback(sql_trace_callback)


# ---------------------------------------------------------------------------
# 4. FORENSIC STATE
# ---------------------------------------------------------------------------

main_calls = 0
process_calls = 0
create_calls = 0
future_calls = 0

future_returns = []
create_returns = []

store_subscr_events = []
prices_observations = []
returns_observations = []
outcomes_observations = []

return_observations = []

runtime_exceptions = []

price_identity = set()
future_identity = set()

active_create_frames = set()


# ---------------------------------------------------------------------------
# 5. SAFE VALUE DESCRIPTION
# ---------------------------------------------------------------------------

def describe_value(value, max_items=20):

    result = {
        "type": type(value).__name__,
        "id": id(value),
    }

    try:
        if isinstance(value, dict):
            result["len"] = len(value)

            items = []

            for k, v in list(value.items())[:max_items]:
                items.append(
                    {
                        "key": repr(k),
                        "value_type": type(v).__name__,
                        "value_id": id(v),
                        "value": repr(v)[:300],
                    }
                )

            result["items"] = items

        elif isinstance(value, (list, tuple)):
            result["len"] = len(value)
            result["value"] = repr(value[:max_items])[:1000]

        else:
            result["value"] = repr(value)[:500]

    except Exception as exc:
        result["describe_error"] = repr(exc)

    return result


# ---------------------------------------------------------------------------
# 6. CREATE_OUTCOME FRAME SNAPSHOT
# ---------------------------------------------------------------------------

def snapshot_create_frame(frame, event, instruction=None):

    locals_ = frame.f_locals

    snapshot = {
        "event": event,
        "line": frame.f_lineno,
        "offset": instruction.offset if instruction else None,
        "opcode": instruction.opname if instruction else None,
    }

    for name in [
        "label",
        "price",
        "prices",
        "returns",
        "outcomes",
        "completed_returns",
        "overall_outcome",
        "max_gain",
        "max_drawdown",
        "value",
        "r",
        "asset",
        "direction",
        "entry_price",
    ]:

        if name in locals_:

            value = locals_[name]

            if name == "price":
                price_identity.add(id(value))

            if name == "prices":

                prices_observations.append(
                    {
                        "event": event,
                        "line": frame.f_lineno,
                        "offset": instruction.offset if instruction else None,
                        "label": repr(locals_.get("label")),
                        "price": describe_value(locals_.get("price")),
                        "prices": describe_value(value),
                    }
                )

            elif name == "returns":

                returns_observations.append(
                    {
                        "event": event,
                        "line": frame.f_lineno,
                        "offset": instruction.offset if instruction else None,
                        "returns": describe_value(value),
                    }
                )

            elif name == "outcomes":

                outcomes_observations.append(
                    {
                        "event": event,
                        "line": frame.f_lineno,
                        "offset": instruction.offset if instruction else None,
                        "outcomes": describe_value(value),
                    }
                )

    return snapshot


# ---------------------------------------------------------------------------
# 7. OPCODE TRACE
# ---------------------------------------------------------------------------

def trace_function(frame, event, arg):

    global main_calls
    global process_calls
    global create_calls
    global future_calls

    filename = frame.f_code.co_filename
    function_name = frame.f_code.co_name

    if filename != TARGET:
        return trace_function

    if event == "call":

        if function_name == "main":
            main_calls += 1

        elif function_name == "process_signals":
            process_calls += 1

        elif function_name == "create_outcome":
            create_calls += 1
            active_create_frames.add(id(frame))

        elif function_name == "find_future_price":
            future_calls += 1

        frame.f_trace_opcodes = True
        frame.f_trace_lines = True

        return trace_function

    # -----------------------------------------------------------------------
    # FUTURE PRICE RETURN
    # -----------------------------------------------------------------------

    if event == "return" and function_name == "find_future_price":

        value = arg

        future_identity.add(id(value))

        record = {
            "line": frame.f_lineno,
            "type": type(value).__name__,
            "id": id(value),
            "value": repr(value),
        }

        future_returns.append(record)

        return trace_function

    # -----------------------------------------------------------------------
    # CREATE_OUTCOME RETURN
    # -----------------------------------------------------------------------

    if event == "return" and function_name == "create_outcome":

        value = arg

        create_returns.append(
            {
                "line": frame.f_lineno,
                "type": type(value).__name__,
                "id": id(value),
                "value": repr(value),
                "prices": describe_value(frame.f_locals.get("prices")),
                "returns": describe_value(frame.f_locals.get("returns")),
                "outcomes": describe_value(frame.f_locals.get("outcomes")),
            }
        )

        active_create_frames.discard(id(frame))

        return trace_function

    # -----------------------------------------------------------------------
    # OPCODE OBSERVATION
    # -----------------------------------------------------------------------

    if event == "opcode" and function_name == "create_outcome":

        try:
            instructions = list(dis.get_instructions(frame.f_code))

            current = None

            for ins in instructions:

                if ins.offset == frame.f_lasti:
                    current = ins
                    break

            if current is None:
                return trace_function

            # ---------------------------------------------------------------
            # STORE_SUBSCR
            # ---------------------------------------------------------------

            if current.opname == "STORE_SUBSCR":

                locals_ = frame.f_locals

                prices = locals_.get("prices")
                label = locals_.get("label")
                price = locals_.get("price")

                event_record = {
                    "offset": current.offset,
                    "line": frame.f_lineno,
                    "label": repr(label),
                    "price": describe_value(price),
                    "price_id": id(price),
                    "prices_id": id(prices),
                    "prices": describe_value(prices),
                    "future_identity_match": id(price) in future_identity,
                    "future_price_identity_match": id(price) in price_identity,
                }

                store_subscr_events.append(event_record)

            # ---------------------------------------------------------------
            # LOAD_FAST prices
            # ---------------------------------------------------------------

            elif current.opname == "LOAD_FAST" and current.argval == "prices":

                locals_ = frame.f_locals

                prices = locals_.get("prices")
                label = locals_.get("label")
                price = locals_.get("price")

                snapshot = {
                    "event": "LOAD_FAST_PRICES",
                    "offset": current.offset,
                    "line": frame.f_lineno,
                    "label": repr(label),
                    "price": describe_value(price),
                    "price_id": id(price),
                    "prices": describe_value(prices),
                    "future_identity_match": id(price) in future_identity,
                }

                prices_observations.append(snapshot)

            # ---------------------------------------------------------------
            # RETURN_VALUE
            # ---------------------------------------------------------------

            elif current.opname == "RETURN_VALUE":

                locals_ = frame.f_locals

                snapshot = {
                    "offset": current.offset,
                    "line": frame.f_lineno,
                    "price": describe_value(locals_.get("price")),
                    "prices": describe_value(locals_.get("prices")),
                    "returns": describe_value(locals_.get("returns")),
                    "outcomes": describe_value(locals_.get("outcomes")),
                }

                return_observations.append(snapshot)

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "function": function_name,
                    "line": frame.f_lineno,
                    "type": type(exc).__name__,
                    "value": repr(exc),
                }
            )

    return trace_function


# ---------------------------------------------------------------------------
# 8. INSTALL TRACE
# ---------------------------------------------------------------------------

sys.settrace(trace_function)

module.__dict__["conn"] = clone_conn

try:

    main()

except Exception as exc:

    runtime_exceptions.append(
        {
            "function": "main",
            "line": None,
            "type": type(exc).__name__,
            "value": repr(exc),
            "traceback": traceback.format_exc(),
        }
    )

finally:

    sys.settrace(None)


# ---------------------------------------------------------------------------
# 9. EXACT SQL TRACE
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 4 — SQL PACKING TRACE")
print("-" * 100)

if sql_trace:

    for i, statement in enumerate(sql_trace[-100:], 1):
        print(f"SQL #{i:03d} : {statement}")

else:

    print("NO SQL STATEMENTS OBSERVED")


# ---------------------------------------------------------------------------
# 10. FUTURE PRICE RETURNS
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 5 — FUTURE PRICE RETURN IDENTITY")
print("-" * 100)

for i, record in enumerate(future_returns, 1):

    print(
        f"FUTURE RETURN #{i:<3} | "
        f"TYPE={record['type']:<12} | "
        f"ID={record['id']} | "
        f"VALUE={record['value']}"
    )


# ---------------------------------------------------------------------------
# 11. STORE_SUBSCR WRITE PATH
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 6 — EXACT STORE_SUBSCR WRITE PATH")
print("-" * 100)

if store_subscr_events:

    for i, event in enumerate(store_subscr_events, 1):

        print(
            f"STORE_SUBSCR #{i:<3} | "
            f"OFFSET={event['offset']:<5} | "
            f"LINE={event['line']:<5} | "
            f"LABEL={event['label']} | "
            f"PRICE_ID={event['price_id']} | "
            f"FUTURE_MATCH={event['future_identity_match']}"
        )

        print(
            f"    PRICE : {event['price']}"
        )

        print(
            f"    PRICES: {event['prices']}"
        )

else:

    print("NO STORE_SUBSCR EVENTS OBSERVED")


# ---------------------------------------------------------------------------
# 12. PRICES OBSERVATIONS
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 7 — PRICES DICTIONARY FINAL OBSERVATIONS")
print("-" * 100)

if prices_observations:

    for i, obs in enumerate(prices_observations[-100:], 1):

        print(
            f"PRICES OBS #{i:<3} | "
            f"OFFSET={obs.get('offset')} | "
            f"LINE={obs.get('line')} | "
            f"LABEL={obs.get('label')} | "
            f"PRICE_ID={obs.get('price_id')} | "
            f"FUTURE_MATCH={obs.get('future_identity_match')}"
        )

        if "prices" in obs:
            print(f"    PRICES = {obs['prices']}")

else:

    print("NO PRICES OBSERVATIONS")


# ---------------------------------------------------------------------------
# 13. CREATE_OUTCOME RETURN PACKING
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 8 — CREATE_OUTCOME RETURN PACKING")
print("-" * 100)

if create_returns:

    for i, record in enumerate(create_returns, 1):

        print(
            f"CREATE RETURN #{i:<3} | "
            f"TYPE={record['type']} | "
            f"ID={record['id']} | "
            f"VALUE={record['value']}"
        )

        print(
            f"    PRICES   = {record['prices']}"
        )

        print(
            f"    RETURNS  = {record['returns']}"
        )

        print(
            f"    OUTCOMES = {record['outcomes']}"
        )

else:

    print("NO CREATE_OUTCOME RETURNS")


# ---------------------------------------------------------------------------
# 14. RETURN VALUE LOCALIZATION
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 9 — RETURN_VALUE PRICE LOCALIZATION")
print("-" * 100)

if return_observations:

    for i, record in enumerate(return_observations, 1):

        print(
            f"RETURN OPCODE #{i:<3} | "
            f"OFFSET={record['offset']} | "
            f"LINE={record['line']}"
        )

        print(
            f"    PRICE    = {record['price']}"
        )

        print(
            f"    PRICES   = {record['prices']}"
        )

        print(
            f"    RETURNS  = {record['returns']}"
        )

        print(
            f"    OUTCOMES = {record['outcomes']}"
        )

else:

    print("NO RETURN_VALUE OPCODE OBSERVATIONS")


# ---------------------------------------------------------------------------
# 15. RUNTIME EXCEPTIONS
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 10 — RUNTIME EXCEPTION REPORT")
print("-" * 100)

if runtime_exceptions:

    for i, exc in enumerate(runtime_exceptions, 1):

        print(
            f"{i:03d} | "
            f"FUNCTION={exc.get('function')} | "
            f"LINE={exc.get('line')} | "
            f"TYPE={exc.get('type')} | "
            f"VALUE={exc.get('value')}"
        )

else:

    print("NO RUNTIME EXCEPTIONS")


# ---------------------------------------------------------------------------
# 16. FINAL FORENSIC DECISION
# ---------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 11 — FINAL FORENSIC SUMMARY")
print("-" * 100)

print(f"MAIN CALLS                  : {main_calls}")
print(f"PROCESS_SIGNALS CALLS       : {process_calls}")
print(f"CREATE_OUTCOME CALLS        : {create_calls}")
print(f"FIND_FUTURE_PRICE CALLS     : {future_calls}")
print(f"FIND_FUTURE_PRICE RETURNS   : {len(future_returns)}")
print(f"CREATE_OUTCOME RETURNS      : {len(create_returns)}")
print(f"STORE_SUBSCR EVENTS         : {len(store_subscr_events)}")
print(f"PRICES OBSERVATIONS         : {len(prices_observations)}")
print(f"RETURN_VALUE OBSERVATIONS   : {len(return_observations)}")
print(f"SQL STATEMENTS OBSERVED     : {len(sql_trace)}")
print(f"RUNTIME EXCEPTIONS          : {len(runtime_exceptions)}")


print()
print("FORENSIC CONCLUSION")
print("-" * 100)


verified_store = False

for event in store_subscr_events:

    if event.get("future_identity_match"):
        verified_store = True
        break


if verified_store and sql_trace:

    status = "FINAL_PACKING_SQL_BOUNDARY_REACHED"

    meaning = (
        "The future-price identity was followed through the prices "
        "dictionary into the production SQL/packing boundary."
    )

    frontier = (
        "Classify the exact SQL column/parameter receiving the "
        "future-price value and compare it with the outcome schema."
    )

elif verified_store:

    status = "PRICES_STORE_PATH_VERIFIED_SQL_UNRESOLVED"

    meaning = (
        "The future-price identity was verified at STORE_SUBSCR, "
        "but the subsequent persistence/return packing boundary "
        "was not localized."
    )

    frontier = (
        "Trace the subsequent LOAD_FAST prices / LOAD_CONST / "
        "CALL sequence until the final DB parameter or return object."
    )

elif future_returns and prices_observations:

    status = "FUTURE_PRICE_TO_PRICES_OBSERVED"

    meaning = (
        "The future-price return and prices dictionary were observed, "
        "but the exact STORE_SUBSCR identity boundary was not captured."
    )

    frontier = (
        "Repeat at STORE_SUBSCR with the captured price identity and label."
    )

elif future_returns:

    status = "FUTURE_PRICE_RETURN_OBSERVED_PACKING_UNRESOLVED"

    meaning = (
        "find_future_price() returned successfully, but its exact "
        "path into final packing remains unresolved."
    )

    frontier = (
        "Continue at the prices STORE_SUBSCR and subsequent packing boundary."
    )

else:

    status = "FUTURE_PRICE_RUNTIME_NOT_OBSERVED"

    meaning = (
        "No genuine future-price return was observed during production execution."
    )

    frontier = (
        "Resolve the runtime boundary before continuing final packing localization."
    )


print(f"STATUS                      : {status}")
print(f"MEANING                     : {meaning}")
print(f"NEXT FRONTIER               : {frontier}")

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
print("AUDIT COMPLETE")
print("=" * 100)