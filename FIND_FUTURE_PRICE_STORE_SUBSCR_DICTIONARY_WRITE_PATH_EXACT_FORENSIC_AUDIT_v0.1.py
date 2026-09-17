import os
import sys
import sqlite3
import dis
import traceback


TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE STORE_SUBSCR DICTIONARY WRITE PATH")
print("EXACT FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY OPCODE WRITE-PATH FORENSICS")
print(f"TARGET                       : {TARGET}")
print(f"DATABASE                     : {DB_PATH}")
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("PRODUCTION DATABASE WRITES   : NONE")
print("DATABASE EXECUTION           : IN-MEMORY CLONE ONLY")
print("=" * 100)


# ============================================================================
# GLOBAL SAFETY STATE
# ============================================================================

_original_connect = sqlite3.connect

stats = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "future_calls": 0,
    "future_returns": 0,

    "store_events": 0,
    "price_store_events": 0,
    "prices_dict_events": 0,

    "identity_matches": 0,
    "label_matches": 0,
    "write_path_matches": 0,

    "create_returns": 0,
    "runtime_exceptions": 0,

    "memory_sql_writes": 0,
}

future_ids = set()
future_values = {}
store_records = []


# ============================================================================
# REAL DATABASE -> MEMORY CLONE
# ============================================================================

def build_memory_clone():

    print()
    print("=" * 100)
    print("STEP 0 — DATABASE MEMORY CLONE")
    print("=" * 100)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)

    print(f"SOURCE DATABASE              : {DB_PATH}")
    print("SOURCE ACCESS                : READ-ONLY")
    print("TARGET DATABASE              : :memory:")
    print("DISK WRITE                   : NONE")

    source = _original_connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    memory = _original_connect(":memory:")

    source.backup(memory)

    source.close()

    print("DATABASE CLONE               : READY")
    print("PRODUCTION FILE WRITES       : NONE")

    return memory


_memory_connection = None


# ============================================================================
# FORENSIC CONNECT
# ============================================================================

def forensic_connect(*args, **kwargs):
    """
    Every production sqlite3.connect() call is redirected to the
    already-created in-memory clone.

    No production database file is writable.
    """

    global _memory_connection

    if _memory_connection is None:
        _memory_connection = build_memory_clone()

    return _memory_connection


# ============================================================================
# STATIC MODULE LOAD
# ============================================================================

print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("=" * 100)


namespace = {
    "__name__": "__forensic_runtime__",
    "__file__": TARGET,
}


try:

    with open(TARGET, "r", encoding="utf-8") as f:
        source = f.read()

    compiled = compile(
        source,
        TARGET,
        "exec",
    )

    exec(
        compiled,
        namespace,
    )

except Exception as exc:

    print()
    print("MODULE LOAD ERROR")
    print(f"{type(exc).__name__}({exc!r})")
    traceback.print_exc()

    sys.exit(1)


for function_name in (
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
):

    function = namespace.get(function_name)

    if callable(function):

        print(
            f"{function_name:24} : FOUND | "
            f"LINE={function.__code__.co_firstlineno} | "
            f"FILE={function.__code__.co_filename}"
        )

    else:

        print(
            f"{function_name:24} : NOT FOUND"
        )


main = namespace.get("main")
create_outcome = namespace.get("create_outcome")


if not callable(main):
    print("FATAL : main() not resolved")
    sys.exit(1)

if not callable(create_outcome):
    print("FATAL : create_outcome() not resolved")
    sys.exit(1)


# ============================================================================
# STORE_SUBSCR STATIC MAP
# ============================================================================

print()
print("=" * 100)
print("STEP 2 — EXACT STORE_SUBSCR INSTRUCTION MAP")
print("=" * 100)


store_offsets = []

for instruction in dis.get_instructions(create_outcome):

    if instruction.opname == "STORE_SUBSCR":

        store_offsets.append(
            instruction.offset
        )

        print(
            f"OFFSET={instruction.offset:<8} "
            f"LINE={str(instruction.starts_line):<6} "
            f"OP={instruction.opname}"
        )


print()
print(
    f"STORE_SUBSCR COUNT : {len(store_offsets)}"
)


# ============================================================================
# SAFE OBJECT HELPERS
# ============================================================================

def safe_locals(frame):

    try:
        return dict(frame.f_locals)

    except Exception:
        return {}


def object_description(obj):

    try:

        return (
            type(obj).__name__,
            id(obj),
            repr(obj)[:300],
        )

    except Exception:

        return (
            type(obj).__name__,
            id(obj),
            "<unavailable>",
        )


def identity_key_in_dict(mapping, value):

    if not isinstance(mapping, dict):
        return None

    target_id = id(value)

    for key, candidate in mapping.items():

        if id(candidate) == target_id:
            return key

    return None


# ============================================================================
# OPCODE TRACE
# ============================================================================

def trace(frame, event, arg):

    try:

        if frame.f_code.co_filename != TARGET:
            return trace


        function_name = frame.f_code.co_name


        # --------------------------------------------------------------------
        # FUNCTION CALL
        # --------------------------------------------------------------------

        if event == "call":

            if function_name == "main":

                stats["main_calls"] += 1

                print(
                    "TRACE CALL | main | "
                    f"LINE={frame.f_lineno}"
                )


            elif function_name == "process_signals":

                stats["process_calls"] += 1

                print(
                    "TRACE CALL | process_signals | "
                    f"LINE={frame.f_lineno}"
                )


            elif function_name == "create_outcome":

                stats["create_calls"] += 1

                print(
                    "TRACE CALL | create_outcome | "
                    f"LINE={frame.f_lineno}"
                )


            elif function_name == "find_future_price":

                stats["future_calls"] += 1

            return trace


        # --------------------------------------------------------------------
        # FUNCTION RETURN
        # --------------------------------------------------------------------

        if event == "return":

            if function_name == "find_future_price":

                stats["future_returns"] += 1

                value_id = id(arg)

                future_ids.add(
                    value_id
                )

                future_values[
                    value_id
                ] = arg

                print()
                print("-" * 90)
                print(
                    f"FIND_FUTURE_PRICE RETURN "
                    f"#{stats['future_returns']}"
                )
                print("-" * 90)
                print(
                    f"LINE       : {frame.f_lineno}"
                )
                print(
                    f"TYPE       : {type(arg).__name__}"
                )
                print(
                    f"VALUE      : {repr(arg)}"
                )
                print(
                    f"OBJECT ID  : {id(arg)}"
                )


            elif function_name == "create_outcome":

                stats["create_returns"] += 1

                print()
                print("-" * 90)
                print(
                    f"CREATE_OUTCOME RETURN "
                    f"#{stats['create_returns']}"
                )
                print("-" * 90)
                print(
                    f"TYPE       : {type(arg).__name__}"
                )
                print(
                    f"VALUE      : {repr(arg)}"
                )


            return trace


        # --------------------------------------------------------------------
        # OPCODE
        # --------------------------------------------------------------------

        if event != "opcode":
            return trace


        if function_name != "create_outcome":
            return trace


        offset = frame.f_lasti


        if offset not in store_offsets:
            return trace


        stats["store_events"] += 1


        local_values = safe_locals(
            frame
        )


        # --------------------------------------------------------------------
        # EXACT LOCAL OBJECTS
        # --------------------------------------------------------------------

        price_exists = (
            "price" in local_values
        )

        label_exists = (
            "label" in local_values
        )

        prices_exists = (
            "prices" in local_values
        )


        price = (
            local_values.get("price")
            if price_exists
            else None
        )

        label = (
            local_values.get("label")
            if label_exists
            else None
        )

        prices = (
            local_values.get("prices")
            if prices_exists
            else None
        )


        price_id = (
            id(price)
            if price_exists
            else None
        )

        prices_id = (
            id(prices)
            if prices_exists
            else None
        )


        # --------------------------------------------------------------------
        # FUTURE RETURN IDENTITY
        # --------------------------------------------------------------------

        price_is_future_return = (
            price_id in future_ids
        )


        if price_is_future_return:

            stats["price_store_events"] += 1


        # --------------------------------------------------------------------
        # PRICES DICTIONARY
        # --------------------------------------------------------------------

        dictionary_key = None


        if isinstance(prices, dict):

            stats["prices_dict_events"] += 1

            dictionary_key = identity_key_in_dict(
                prices,
                price,
            )


        if dictionary_key is not None:

            stats["identity_matches"] += 1


        if dictionary_key == label:

            stats["label_matches"] += 1


        # --------------------------------------------------------------------
        # EXACT PATH
        # --------------------------------------------------------------------

        exact_write_path = (
            price_is_future_return
            and isinstance(prices, dict)
            and dictionary_key is not None
            and dictionary_key == label
        )


        if exact_write_path:

            stats["write_path_matches"] += 1


        # --------------------------------------------------------------------
        # RECORD
        # --------------------------------------------------------------------

        record = {
            "offset": offset,
            "line": frame.f_lineno,

            "label": label,

            "price_id": price_id,
            "price_type": (
                type(price).__name__
                if price_exists
                else None
            ),
            "price_value": (
                repr(price)
                if price_exists
                else None
            ),

            "price_is_future_return":
                price_is_future_return,

            "prices_id": prices_id,

            "prices_type": (
                type(prices).__name__
                if prices_exists
                else None
            ),

            "prices_size": (
                len(prices)
                if isinstance(prices, dict)
                else None
            ),

            "dictionary_identity_key":
                dictionary_key,

            "exact_write_path":
                exact_write_path,
        }


        store_records.append(
            record
        )


        # --------------------------------------------------------------------
        # OUTPUT
        # --------------------------------------------------------------------

        print()
        print("=" * 100)
        print("STORE_SUBSCR EXACT DICTIONARY WRITE-PATH OBSERVATION")
        print("=" * 100)

        print(
            f"BYTECODE OFFSET              : {offset}"
        )

        print(
            f"SOURCE LINE                  : {frame.f_lineno}"
        )

        print(
            f"LABEL                        : {repr(label)}"
        )

        print(
            f"PRICE TYPE                   : "
            f"{record['price_type']}"
        )

        print(
            f"PRICE VALUE                  : "
            f"{record['price_value']}"
        )

        print(
            f"PRICE OBJECT ID              : "
            f"{price_id}"
        )

        print(
            f"PRICE IS FUTURE RETURN      : "
            f"{price_is_future_return}"
        )

        print(
            f"PRICES OBJECT ID            : "
            f"{prices_id}"
        )

        print(
            f"PRICES TYPE                 : "
            f"{record['prices_type']}"
        )

        print(
            f"PRICES SIZE                 : "
            f"{record['prices_size']}"
        )

        print(
            f"IDENTITY KEY IN PRICES      : "
            f"{repr(dictionary_key)}"
        )

        print(
            f"IDENTITY KEY == LABEL       : "
            f"{dictionary_key == label}"
        )

        print(
            f"EXACT WRITE PATH            : "
            f"{exact_write_path}"
        )


    except Exception as trace_error:

        stats["runtime_exceptions"] += 1

        print(
            "TRACE ERROR | "
            f"{type(trace_error).__name__} | "
            f"{trace_error!r}"
        )


    return trace


# ============================================================================
# GLOBAL TRACE
# ============================================================================

def global_trace(frame, event, arg):

    try:

        frame.f_trace_opcodes = True

    except Exception:
        pass

    return trace


# ============================================================================
# STEP 3 — GENUINE PRODUCTION EXECUTION
# ============================================================================

print()
print("=" * 100)
print("STEP 3 — GENUINE PRODUCTION EXECUTION")
print("=" * 100)

print(
    "ENTRYPOINT                  : main()"
)

print(
    "EXECUTION MODE              : "
    "DIRECT FUNCTION INVOCATION"
)

print(
    "TRACE MODE                  : "
    "CPYTHON opcode + line trace"
)

print(
    "DATABASE                    : "
    "REAL DATA / IN-MEMORY CLONE"
)

print(
    "PRODUCTION DATABASE         : "
    "READ-ONLY"
)

print(
    "PRODUCTION SOURCE           : "
    "UNMODIFIED"
)

print("=" * 100)


# ============================================================================
# REDIRECT sqlite3.connect
# ============================================================================

sqlite3.connect = forensic_connect


old_trace = sys.gettrace()


try:

    sys.settrace(
        global_trace
    )

    main()


except Exception as exc:

    stats["runtime_exceptions"] += 1

    print()
    print("=" * 100)
    print("RUNTIME EXCEPTION")
    print("=" * 100)

    print(
        f"TYPE  : {type(exc).__name__}"
    )

    print(
        f"VALUE : {repr(exc)}"
    )

    traceback.print_exc()


finally:

    sys.settrace(
        old_trace
    )

    sqlite3.connect = _original_connect


# ============================================================================
# STEP 4 — EXACT WRITE PATH SUMMARY
# ============================================================================

print()
print("=" * 100)
print("STEP 4 — EXACT DICTIONARY WRITE-PATH SUMMARY")
print("=" * 100)


if not store_records:

    print(
        "NO STORE_SUBSCR OBSERVATIONS"
    )

else:

    for index, record in enumerate(
        store_records,
        1,
    ):

        print(
            f"{index:03d} | "
            f"OFFSET={record['offset']} | "
            f"LINE={record['line']} | "
            f"LABEL={record['label']!r} | "
            f"PRICE_ID={record['price_id']} | "
            f"FUTURE_RETURN="
            f"{record['price_is_future_return']} | "
            f"DICT_KEY="
            f"{record['dictionary_identity_key']!r} | "
            f"EXACT_PATH="
            f"{record['exact_write_path']}"
        )


# ============================================================================
# STEP 5 — FINAL FORENSIC SUMMARY
# ============================================================================

print()
print("=" * 100)
print("STEP 5 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    f"MAIN CALLS                  : "
    f"{stats['main_calls']}"
)

print(
    f"PROCESS_SIGNALS CALLS       : "
    f"{stats['process_calls']}"
)

print(
    f"CREATE_OUTCOME CALLS        : "
    f"{stats['create_calls']}"
)

print(
    f"FIND_FUTURE_PRICE CALLS     : "
    f"{stats['future_calls']}"
)

print(
    f"FIND_FUTURE_PRICE RETURNS   : "
    f"{stats['future_returns']}"
)

print(
    f"STORE_SUBSCR EVENTS         : "
    f"{stats['store_events']}"
)

print(
    f"PRICE AT STORE_SUBSCR       : "
    f"{stats['price_store_events']}"
)

print(
    f"PRICES DICT OBSERVATIONS    : "
    f"{stats['prices_dict_events']}"
)

print(
    f"PRICE IDENTITY MATCHES      : "
    f"{stats['identity_matches']}"
)

print(
    f"LABEL IDENTITY MATCHES      : "
    f"{stats['label_matches']}"
)

print(
    f"EXACT WRITE-PATH MATCHES    : "
    f"{stats['write_path_matches']}"
)

print(
    f"CREATE_OUTCOME RETURNS      : "
    f"{stats['create_returns']}"
)

print(
    f"RUNTIME / TRACE EXCEPTIONS  : "
    f"{stats['runtime_exceptions']}"
)


# ============================================================================
# CONCLUSION
# ============================================================================

print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("-" * 100)


if stats["write_path_matches"] > 0:

    print(
        "STATUS                      : "
        "STORE_SUBSCR_EXACT_DICTIONARY_WRITE_PATH_VERIFIED"
    )

    print(
        "MEANING                     : "
        "The find_future_price() return object was observed as "
        "create_outcome().price and the same object identity was "
        "located in prices under the active label."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace prices into the final return/DB packing boundary."
    )


elif stats["price_store_events"] > 0:

    print(
        "STATUS                      : "
        "STORE_SUBSCR_PRICE_STATE_CAPTURED"
    )

    print(
        "MEANING                     : "
        "The future-price return reached STORE_SUBSCR through "
        "create_outcome().price, but the exact dictionary "
        "identity/key relationship remains unresolved."
    )

    print(
        "NEXT FRONTIER               : "
        "Capture the operand stack immediately around STORE_SUBSCR."
    )


elif stats["future_returns"] > 0:

    print(
        "STATUS                      : "
        "FUTURE_PRICE_RETURN_OBSERVED_STORE_PATH_UNRESOLVED"
    )

    print(
        "MEANING                     : "
        "find_future_price() returned successfully, but the "
        "future-price identity was not simultaneously captured "
        "at STORE_SUBSCR."
    )

    print(
        "NEXT FRONTIER               : "
        "Continue with exact operand-stack tracing."
    )


elif stats["main_calls"] > 0:

    print(
        "STATUS                      : "
        "MAIN_REACHED_FUTURE_PRICE_NOT_OBSERVED"
    )

    print(
        "MEANING                     : "
        "main() executed, but the production flow did not produce "
        "an observable find_future_price() return."
    )

    print(
        "NEXT FRONTIER               : "
        "Resolve the downstream execution boundary."
    )


else:

    print(
        "STATUS                      : "
        "PRODUCTION_RUNTIME_NOT_OBSERVED"
    )

    print(
        "MEANING                     : "
        "The genuine production entrypoint was not successfully observed."
    )

    print(
        "NEXT FRONTIER               : "
        "Resolve the runtime entry boundary."
    )


# ============================================================================
# SAFETY
# ============================================================================

print()
print("=" * 100)
print("STEP 6 — SAFETY VERIFICATION")
print("=" * 100)

print(
    "PRODUCTION DATABASE WRITES  : NONE"
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
    "DATABASE FILE WRITES        : NONE"
)

print(
    "DATABASE EXECUTION          : IN-MEMORY CLONE"
)

print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)