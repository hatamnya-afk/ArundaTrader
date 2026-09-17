import os
import sys
import sqlite3
import dis
import types
import traceback


TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE PRICES POST STORE_SUBSCR FINAL DB PARAMETER TRACE FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY POST-STORE_SUBSCR FORENSICS")
print(f"TARGET                       : {TARGET}")
print(f"DATABASE                     : {DB_PATH}")
print("PRODUCTION SOURCE MODIFIED   : NONE")
print("DATABASE WRITE               : NONE")
print("DATABASE MODE                : IN-MEMORY CLONE")
print("=" * 100)


# ============================================================================
# STEP 1 — LOAD PRODUCTION SOURCE WITHOUT MODIFYING IT
# ============================================================================

source = open(TARGET, "r", encoding="utf-8").read()

module = types.ModuleType("__forensic_runtime__")
module.__file__ = TARGET

sys.modules["__forensic_runtime__"] = module

exec(
    compile(source, TARGET, "exec"),
    module.__dict__
)


main = module.main
process_signals = module.process_signals
create_outcome = module.create_outcome
find_future_price = module.find_future_price


print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("-" * 100)

for name, fn in [
    ("main", main),
    ("process_signals", process_signals),
    ("create_outcome", create_outcome),
    ("find_future_price", find_future_price),
]:

    print(
        f"{name:<24} : FOUND | "
        f"LINE={fn.__code__.co_firstlineno} | "
        f"FILE={fn.__code__.co_filename}"
    )


# ============================================================================
# STEP 2 — BYTECODE MAP
# ============================================================================

instructions = list(dis.get_instructions(create_outcome))

store_subscr_offsets = [
    ins.offset
    for ins in instructions
    if ins.opname == "STORE_SUBSCR"
]

return_offsets = [
    ins.offset
    for ins in instructions
    if ins.opname == "RETURN_VALUE"
]


print()
print("=" * 100)
print("STEP 2 — POST STORE_SUBSCR BYTECODE MAP")
print("-" * 100)

print(f"STORE_SUBSCR OFFSETS       : {store_subscr_offsets}")
print(f"RETURN_VALUE OFFSETS       : {return_offsets}")

print()
print("RELEVANT INSTRUCTIONS")
print("-" * 100)

for ins in instructions:

    if (
        ins.opname in {
            "STORE_SUBSCR",
            "LOAD_FAST",
            "LOAD_CONST",
            "LOAD_GLOBAL",
            "LOAD_ATTR",
            "LOAD_METHOD",
            "BUILD_TUPLE",
            "BUILD_LIST",
            "BUILD_MAP",
            "BUILD_CONST_KEY_MAP",
            "BUILD_STRING",
            "CALL",
            "PRECALL",
            "CALL_FUNCTION",
            "CALL_METHOD",
            "KW_NAMES",
            "RETURN_VALUE",
        }
    ):

        print(
            f"OFFSET={ins.offset:<6} "
            f"LINE={str(ins.starts_line):<6} "
            f"OP={ins.opname:<24} "
            f"ARG={str(ins.arg):<6} "
            f"ARGVAL={repr(ins.argval)}"
        )


# ============================================================================
# STEP 3 — REAL DATABASE READ / IN-MEMORY CLONE
# ============================================================================

print()
print("=" * 100)
print("STEP 3 — DATABASE CLONE")
print("-" * 100)

real_conn = sqlite3.connect(DB_PATH)

clone_conn = sqlite3.connect(":memory:")

real_conn.backup(clone_conn)

real_conn.close()

print("REAL DATABASE                 : READ ONLY")
print("PRODUCTION DATABASE WRITES    : NONE")
print("EXECUTION DATABASE            : :memory:")


# ============================================================================
# STEP 4 — SQL TRACE
# ============================================================================

sql_trace = []


def sql_trace_callback(statement):
    sql_trace.append(statement)


clone_conn.set_trace_callback(sql_trace_callback)


# ============================================================================
# STEP 5 — FORENSIC STATE
# ============================================================================

main_calls = 0
process_calls = 0
create_calls = 0
future_calls = 0

future_returns = []
create_returns = []

store_events = []
post_store_events = []

prices_observations = []

call_events = []
db_candidate_calls = []

return_events = []

runtime_exceptions = []

future_ids = set()
price_ids = set()

active_create_frames = set()


# ============================================================================
# STEP 6 — SAFE OBJECT DESCRIPTION
# ============================================================================

def describe(value, max_items=25):

    result = {
        "type": type(value).__name__,
        "id": id(value),
    }

    try:

        if isinstance(value, dict):

            result["len"] = len(value)

            items = []

            for key, item in list(value.items())[:max_items]:

                items.append(
                    {
                        "key": repr(key),
                        "value_type": type(item).__name__,
                        "value_id": id(item),
                        "value": repr(item)[:300],
                        "future_identity":
                            id(item) in future_ids,
                        "price_identity":
                            id(item) in price_ids,
                    }
                )

            result["items"] = items

        elif isinstance(value, (tuple, list)):

            result["len"] = len(value)

            result["items"] = [
                {
                    "index": i,
                    "type": type(item).__name__,
                    "id": id(item),
                    "value": repr(item)[:300],
                    "future_identity":
                        id(item) in future_ids,
                    "price_identity":
                        id(item) in price_ids,
                }
                for i, item in enumerate(value[:max_items])
            ]

        else:

            result["value"] = repr(value)[:500]

    except Exception as exc:

        result["describe_error"] = repr(exc)

    return result


# ============================================================================
# STEP 7 — CODE OBJECT INSTRUCTION CACHE
# ============================================================================

instruction_cache = {}


def get_instruction(frame):

    code = frame.f_code

    if code not in instruction_cache:

        instruction_cache[code] = {
            ins.offset: ins
            for ins in dis.get_instructions(code)
        }

    return instruction_cache[code].get(frame.f_lasti)


# ============================================================================
# STEP 8 — FRAME STACK OBSERVATION
# ============================================================================

def frame_stack_snapshot(frame):

    """
    We intentionally do NOT attempt to mutate or inspect the private CPython
    evaluation stack directly.

    Instead we capture every Python-visible local that participates in the
    packing path plus the exact opcode boundary.
    """

    locals_copy = dict(frame.f_locals)

    result = {}

    for name in [
        "label",
        "price",
        "prices",
        "returns",
        "outcomes",
        "completed_returns",
        "overall_outcome",
        "value",
        "r",
        "asset",
        "direction",
        "entry_price",
        "snapshot_id",
    ]:

        if name in locals_copy:

            value = locals_copy[name]

            result[name] = describe(value)

    return result


# ============================================================================
# STEP 9 — TRACE FUNCTION
# ============================================================================

def trace_function(frame, event, arg):

    global main_calls
    global process_calls
    global create_calls
    global future_calls

    if frame.f_code.co_filename != TARGET:

        return trace_function


    function_name = frame.f_code.co_name


    # ------------------------------------------------------------------------
    # FUNCTION ENTRY
    # ------------------------------------------------------------------------

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


    # ------------------------------------------------------------------------
    # FIND_FUTURE_PRICE RETURN
    # ------------------------------------------------------------------------

    if (
        event == "return"
        and function_name == "find_future_price"
    ):

        value = arg

        future_ids.add(id(value))

        future_returns.append(
            {
                "line": frame.f_lineno,
                "type": type(value).__name__,
                "id": id(value),
                "value": repr(value),
            }
        )

        return trace_function


    # ------------------------------------------------------------------------
    # CREATE_OUTCOME RETURN
    # ------------------------------------------------------------------------

    if (
        event == "return"
        and function_name == "create_outcome"
    ):

        value = arg

        create_returns.append(
            {
                "line": frame.f_lineno,
                "type": type(value).__name__,
                "id": id(value),
                "value": repr(value),
                "locals": frame_stack_snapshot(frame),
            }
        )

        active_create_frames.discard(id(frame))

        return trace_function


    # ------------------------------------------------------------------------
    # OPCODE TRACE
    # ------------------------------------------------------------------------

    if event == "opcode" and function_name == "create_outcome":

        try:

            ins = get_instruction(frame)

            if ins is None:

                return trace_function


            locals_ = frame.f_locals

            label = locals_.get("label")
            price = locals_.get("price")
            prices = locals_.get("prices")


            # ----------------------------------------------------------------
            # PRICE IDENTITY
            # ----------------------------------------------------------------

            if "price" in locals_:

                price_ids.add(id(price))


            # ----------------------------------------------------------------
            # STORE_SUBSCR
            # ----------------------------------------------------------------

            if ins.opname == "STORE_SUBSCR":

                event_record = {
                    "offset": ins.offset,
                    "line": frame.f_lineno,
                    "label": repr(label),
                    "price": describe(price),
                    "price_id": id(price),
                    "prices_id": id(prices),
                    "prices": describe(prices),
                    "future_match":
                        id(price) in future_ids,
                    "price_match":
                        id(price) in price_ids,
                }

                store_events.append(event_record)


            # ----------------------------------------------------------------
            # AFTER STORE_SUBSCR
            # ----------------------------------------------------------------

            if store_subscr_offsets:

                previous_store = [
                    offset
                    for offset in store_subscr_offsets
                    if offset < ins.offset
                ]

                if previous_store:

                    nearest_store = max(previous_store)

                    if ins.offset > nearest_store:

                        post_store_events.append(
                            {
                                "store_offset": nearest_store,
                                "current_offset": ins.offset,
                                "line": frame.f_lineno,
                                "opcode": ins.opname,
                                "arg": ins.arg,
                                "argval": repr(ins.argval),
                                "label": repr(label),
                                "price": describe(price),
                                "prices": describe(prices),
                                "locals": frame_stack_snapshot(frame),
                                "future_match":
                                    id(price) in future_ids,
                            }
                        )


            # ----------------------------------------------------------------
            # LOAD_FAST prices
            # ----------------------------------------------------------------

            if (
                ins.opname == "LOAD_FAST"
                and ins.argval == "prices"
            ):

                prices_observations.append(
                    {
                        "offset": ins.offset,
                        "line": frame.f_lineno,
                        "label": repr(label),
                        "price": describe(price),
                        "prices": describe(prices),
                        "future_match":
                            id(price) in future_ids,
                    }
                )


            # ----------------------------------------------------------------
            # CALL / PRECALL / CALL_METHOD
            # ----------------------------------------------------------------

            if ins.opname in {
                "CALL",
                "PRECALL",
                "CALL_FUNCTION",
                "CALL_METHOD",
            }:

                call_record = {
                    "offset": ins.offset,
                    "line": frame.f_lineno,
                    "opcode": ins.opname,
                    "arg": ins.arg,
                    "argval": repr(ins.argval),
                    "label": repr(label),
                    "price": describe(price),
                    "prices": describe(prices),
                    "locals": frame_stack_snapshot(frame),
                }

                call_events.append(call_record)


                # ------------------------------------------------------------
                # Candidate DB / persistence call
                # ------------------------------------------------------------

                argval = str(ins.argval)

                if any(
                    token in argval.lower()
                    for token in [
                        "execute",
                        "executemany",
                        "executescript",
                        "insert",
                        "update",
                        "replace",
                        "save",
                        "persist",
                        "write",
                        "store",
                        "commit",
                    ]
                ):

                    db_candidate_calls.append(
                        call_record
                    )


            # ----------------------------------------------------------------
            # RETURN_VALUE
            # ----------------------------------------------------------------

            if ins.opname == "RETURN_VALUE":

                return_events.append(
                    {
                        "offset": ins.offset,
                        "line": frame.f_lineno,
                        "price": describe(price),
                        "prices": describe(prices),
                        "returns": describe(
                            locals_.get("returns")
                        ),
                        "outcomes": describe(
                            locals_.get("outcomes")
                        ),
                        "future_price_match":
                            id(price) in future_ids,
                    }
                )

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


# ============================================================================
# STEP 10 — PRODUCTION EXECUTION
# ============================================================================

print()
print("=" * 100)
print("STEP 4 — GENUINE PRODUCTION EXECUTION")
print("-" * 100)
print("ENTRYPOINT                  : main()")
print("TRACE MODE                  : CPYTHON opcode + line trace")
print("DATABASE                    : IN-MEMORY CLONE")
print("PRODUCTION SOURCE           : UNMODIFIED")
print("=" * 100)


sys.settrace(trace_function)

try:

    module.__dict__["conn"] = clone_conn

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


# ============================================================================
# STEP 11 — FUTURE RETURNS
# ============================================================================

print()
print("=" * 100)
print("STEP 5 — FUTURE PRICE RETURNS")
print("-" * 100)

if future_returns:

    for i, record in enumerate(future_returns, 1):

        print(
            f"RETURN #{i:<3} | "
            f"LINE={record['line']} | "
            f"TYPE={record['type']} | "
            f"ID={record['id']} | "
            f"VALUE={record['value']}"
        )

else:

    print("NONE")


# ============================================================================
# STEP 12 — STORE_SUBSCR
# ============================================================================

print()
print("=" * 100)
print("STEP 6 — STORE_SUBSCR VERIFIED PATH")
print("-" * 100)

if store_events:

    for i, record in enumerate(store_events, 1):

        print(
            f"STORE #{i:<3} | "
            f"OFFSET={record['offset']} | "
            f"LINE={record['line']} | "
            f"LABEL={record['label']} | "
            f"PRICE_ID={record['price_id']} | "
            f"FUTURE_MATCH={record['future_match']}"
        )

        print(
            f"    PRICE  : {record['price']}"
        )

        print(
            f"    PRICES : {record['prices']}"
        )

else:

    print("NONE")


# ============================================================================
# STEP 13 — POST STORE SUBSCR INSTRUCTIONS
# ============================================================================

print()
print("=" * 100)
print("STEP 7 — POST STORE_SUBSCR INSTRUCTION FLOW")
print("-" * 100)

if post_store_events:

    for i, record in enumerate(post_store_events[-150:], 1):

        print(
            f"POST #{i:<3} | "
            f"STORE_OFFSET={record['store_offset']} | "
            f"CURRENT_OFFSET={record['current_offset']} | "
            f"LINE={record['line']} | "
            f"OP={record['opcode']:<18} | "
            f"ARG={record['arg']} | "
            f"ARGVAL={record['argval']}"
        )

        print(
            f"    LABEL  : {record['label']}"
        )

        print(
            f"    PRICE  : {record['price']}"
        )

        print(
            f"    PRICES : {record['prices']}"
        )

else:

    print("NONE")


# ============================================================================
# STEP 14 — CALL BOUNDARY
# ============================================================================

print()
print("=" * 100)
print("STEP 8 — POST STORE_SUBSCR CALL BOUNDARY")
print("-" * 100)

if call_events:

    for i, record in enumerate(call_events[-150:], 1):

        print(
            f"CALL #{i:<3} | "
            f"OFFSET={record['offset']} | "
            f"LINE={record['line']} | "
            f"OP={record['opcode']:<18} | "
            f"ARG={record['arg']} | "
            f"ARGVAL={record['argval']}"
        )

        print(
            f"    PRICE  : {record['price']}"
        )

        print(
            f"    PRICES : {record['prices']}"
        )

else:

    print("NONE")


# ============================================================================
# STEP 15 — DB CANDIDATE CALLS
# ============================================================================

print()
print("=" * 100)
print("STEP 9 — FINAL DB / PERSISTENCE CANDIDATE CALLS")
print("-" * 100)

if db_candidate_calls:

    for i, record in enumerate(db_candidate_calls, 1):

        print(
            f"DB CANDIDATE #{i:<3} | "
            f"OFFSET={record['offset']} | "
            f"LINE={record['line']} | "
            f"OP={record['opcode']} | "
            f"ARGVAL={record['argval']}"
        )

        print(
            f"    PRICE  : {record['price']}"
        )

        print(
            f"    PRICES : {record['prices']}"
        )

        print(
            f"    LOCALS : {record['locals']}"
        )

else:

    print("NONE")


# ============================================================================
# STEP 16 — SQL TRACE
# ============================================================================

print()
print("=" * 100)
print("STEP 10 — SQL STATEMENT TRACE")
print("-" * 100)

if sql_trace:

    for i, statement in enumerate(sql_trace[-100:], 1):

        print(
            f"SQL #{i:03d} : {statement}"
        )

else:

    print("NO SQL STATEMENTS")


# ============================================================================
# STEP 17 — CREATE_OUTCOME RETURNS
# ============================================================================

print()
print("=" * 100)
print("STEP 11 — CREATE_OUTCOME RETURN PACKING")
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
            f"    LOCALS = {record['locals']}"
        )

else:

    print("NONE")


# ============================================================================
# STEP 18 — RETURN VALUE
# ============================================================================

print()
print("=" * 100)
print("STEP 12 — RETURN_VALUE LOCALIZATION")
print("-" * 100)

if return_events:

    for i, record in enumerate(return_events, 1):

        print(
            f"RETURN OPCODE #{i:<3} | "
            f"OFFSET={record['offset']} | "
            f"LINE={record['line']} | "
            f"FUTURE_PRICE_MATCH={record['future_price_match']}"
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

    print("NONE")


# ============================================================================
# STEP 19 — EXCEPTIONS
# ============================================================================

print()
print("=" * 100)
print("STEP 13 — RUNTIME EXCEPTION REPORT")
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

    print("NONE")


# ============================================================================
# STEP 20 — FINAL CLASSIFICATION
# ============================================================================

verified_store = any(
    event.get("future_match")
    for event in store_events
)

prices_after_store = any(
    event.get("future_match")
    for event in post_store_events
)

db_reached = bool(db_candidate_calls or sql_trace)


print()
print("=" * 100)
print("STEP 14 — FINAL FORENSIC SUMMARY")
print("-" * 100)

print(f"MAIN CALLS                  : {main_calls}")
print(f"PROCESS_SIGNALS CALLS       : {process_calls}")
print(f"CREATE_OUTCOME CALLS        : {create_calls}")
print(f"FIND_FUTURE_PRICE CALLS     : {future_calls}")
print(f"FIND_FUTURE_PRICE RETURNS   : {len(future_returns)}")
print(f"CREATE_OUTCOME RETURNS      : {len(create_returns)}")
print(f"STORE_SUBSCR EVENTS         : {len(store_events)}")
print(f"POST-STORE EVENTS            : {len(post_store_events)}")
print(f"CALL EVENTS                 : {len(call_events)}")
print(f"DB CANDIDATE CALLS          : {len(db_candidate_calls)}")
print(f"SQL STATEMENTS              : {len(sql_trace)}")
print(f"RETURN_VALUE EVENTS         : {len(return_events)}")
print(f"RUNTIME EXCEPTIONS          : {len(runtime_exceptions)}")


print()
print("FORENSIC CONCLUSION")
print("-" * 100)


if verified_store and prices_after_store and db_reached:

    status = "FINAL_DB_PARAMETER_PACKING_BOUNDARY_REACHED"

    meaning = (
        "The verified future-price identity was followed from "
        "STORE_SUBSCR through the post-store instruction flow "
        "into the final persistence/return packing boundary."
    )

    frontier = (
        "Identify the exact final SQL parameter/column or return-field "
        "position receiving the future-price object."
    )


elif verified_store and prices_after_store:

    status = "POST_STORE_PRICES_FLOW_VERIFIED_DB_UNRESOLVED"

    meaning = (
        "The future-price identity was followed through prices "
        "after STORE_SUBSCR, but the final DB/return packing call "
        "was not localized."
    )

    frontier = (
        "Trace the next CALL operand construction toward execute/"
        "executemany or the final return structure."
    )


elif verified_store:

    status = "STORE_VERIFIED_POST_STORE_FLOW_UNRESOLVED"

    meaning = (
        "The future-price identity is verified at STORE_SUBSCR, "
        "but the subsequent prices flow was not localized."
    )

    frontier = (
        "Continue from the first LOAD_FAST prices after STORE_SUBSCR."
    )


elif future_returns:

    status = "FUTURE_RETURN_OBSERVED_STORE_PATH_LOST"

    meaning = (
        "find_future_price() returned successfully, but the "
        "previously verified dictionary write identity was not "
        "captured in this execution."
    )

    frontier = (
        "Re-establish the STORE_SUBSCR identity boundary."
    )


else:

    status = "FUTURE_PRICE_RUNTIME_NOT_OBSERVED"

    meaning = (
        "No genuine future-price return was observed."
    )

    frontier = (
        "Resolve the production runtime boundary first."
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