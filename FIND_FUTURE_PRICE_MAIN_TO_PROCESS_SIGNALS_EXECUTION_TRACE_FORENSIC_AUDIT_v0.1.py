import os
import sys
import sqlite3
import inspect
import dis
import traceback
import importlib.util
from collections import Counter

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"
TARGET_FILE = os.path.join(BASE_DIR, "signal_outcome_engine.py")
DB_FILE = os.path.join(BASE_DIR, "arunda.db")
MODULE_NAME = "__forensic_runtime__"

BLOCKED_WRITE_OPERATIONS = 0

TRACE_TARGETS = {
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
}

print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE MAIN -> PROCESS_SIGNALS EXECUTION TRACE FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                        : READ-ONLY PRODUCTION BOUNDARY FORENSICS")
print(f"TARGET                      : {TARGET_FILE}")
print(f"DATABASE                    : {DB_FILE}")
print("PRODUCTION SOURCE MODIFIED : NONE")
print("DATABASE WRITE              : BLOCKED")
print("=" * 100)


if not os.path.isfile(TARGET_FILE):
    raise FileNotFoundError(TARGET_FILE)

if not os.path.isfile(DB_FILE):
    raise FileNotFoundError(DB_FILE)


# =============================================================================
# READ-ONLY SQLITE CONNECTION
# =============================================================================

_original_sqlite_connect = sqlite3.connect


def forensic_connect(database, *args, **kwargs):
    global BLOCKED_WRITE_OPERATIONS

    database_value = database

    if isinstance(database_value, str) and database_value.startswith("file:"):
        return _original_sqlite_connect(
            database_value,
            *args,
            **kwargs,
        )

    absolute = os.path.abspath(os.fspath(database_value))
    uri = "file:" + absolute.replace("\\", "/") + "?mode=ro"

    clean_kwargs = dict(kwargs)
    clean_kwargs["uri"] = True

    return _original_sqlite_connect(
        uri,
        *args,
        **clean_kwargs,
    )


sqlite3.connect = forensic_connect


# =============================================================================
# STEP 1
# =============================================================================

print()
print("=" * 100)
print("STEP 1 — STATIC TARGET RESOLUTION")
print("=" * 100)

with open(TARGET_FILE, "r", encoding="utf-8") as f:
    source_text = f.read()

print(f"TARGET FILE              : {TARGET_FILE}")

for name in [
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
]:
    if f"def {name}(" in source_text:
        print(f"{name:<24} : FOUND")
    else:
        print(f"{name:<24} : NOT FOUND")


# =============================================================================
# STEP 2
# =============================================================================

print()
print("=" * 100)
print("STEP 2 — PRODUCTION MODULE LOAD")
print("=" * 100)

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    TARGET_FILE,
)

if spec is None or spec.loader is None:
    raise RuntimeError("Unable to create module spec")

module = importlib.util.module_from_spec(spec)

sys.modules[MODULE_NAME] = module

module_load_error = None

try:
    spec.loader.exec_module(module)
    print("MODULE LOAD              : SUCCESS")
except Exception as exc:
    module_load_error = exc
    print(
        f"MODULE LOAD              : ERROR | "
        f"{type(exc).__name__} | {exc}"
    )


# =============================================================================
# STEP 3
# =============================================================================

print()
print("=" * 100)
print("STEP 3 — RUNTIME FUNCTION RESOLUTION")
print("=" * 100)

resolved = {}

for name in [
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
]:

    obj = getattr(module, name, None)

    if callable(obj):

        resolved[name] = obj

        code = getattr(obj, "__code__", None)

        if code:
            print(
                f"{name:<24} : FOUND | "
                f"FILE={code.co_filename} | "
                f"FIRST_LINE={code.co_firstlineno}"
            )
        else:
            print(
                f"{name:<24} : FOUND | NO CODE OBJECT"
            )

    else:

        resolved[name] = None

        print(
            f"{name:<24} : NOT FOUND"
        )


# =============================================================================
# STEP 4
# =============================================================================

print()
print("=" * 100)
print("STEP 4 — STATIC CALL GRAPH")
print("=" * 100)


def get_calls(function_obj):

    if function_obj is None:
        return []

    result = []

    try:

        instructions = list(
            dis.get_instructions(function_obj)
        )

        for ins in instructions:

            if ins.opname in {
                "LOAD_GLOBAL",
                "LOAD_NAME",
                "LOAD_METHOD",
                "LOAD_ATTR",
            }:

                if ins.argval in TRACE_TARGETS:

                    if ins.argval not in result:
                        result.append(ins.argval)

    except Exception:
        pass

    return result


for name in [
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
]:

    obj = resolved.get(name)

    if obj:

        print(
            f"{name:<24} | CALLS={get_calls(obj)}"
        )


# =============================================================================
# STEP 5
# =============================================================================

print()
print("=" * 100)
print("STEP 5 — ENTRYPOINT CONTRACT")
print("=" * 100)

main_obj = resolved.get("main")

if main_obj:

    try:
        print(
            f"main() signature           : "
            f"{inspect.signature(main_obj)}"
        )
    except Exception as exc:
        print(
            f"main() signature           : ERROR | {exc}"
        )


# =============================================================================
# TRACE STATE
# =============================================================================

call_counts = Counter()
return_counts = Counter()

trace_events = 0

runtime_exceptions = []

price_observations = []


# =============================================================================
# TRACE FUNCTION
# =============================================================================

def trace_function(frame, event, arg):

    global trace_events

    trace_events += 1

    function_name = frame.f_code.co_name

    if function_name not in TRACE_TARGETS:
        return trace_function

    if event == "call":

        call_counts[function_name] += 1

        print(
            f"TRACE CALL               : "
            f"{function_name} "
            f"LINE={frame.f_lineno}"
        )

        return trace_function

    if event == "line":

        if function_name == "main":

            print(
                f"TRACE MAIN LINE          : "
                f"{frame.f_lineno}"
            )

        elif function_name == "process_signals":

            print(
                f"TRACE PROCESS_SIGNALS    : "
                f"LINE={frame.f_lineno}"
            )

        elif function_name == "create_outcome":

            local_names = [
                "asset",
                "price",
                "prices",
                "returns",
                "outcomes",
                "label",
                "minutes",
                "entry_price",
                "direction",
            ]

            snapshot = {}

            for key in local_names:

                if key in frame.f_locals:

                    try:
                        snapshot[key] = repr(
                            frame.f_locals[key]
                        )
                    except Exception:
                        snapshot[key] = "<repr-error>"

            if snapshot:

                price_observations.append(
                    (
                        frame.f_lineno,
                        snapshot,
                    )
                )

                if "price" in snapshot:

                    print(
                        f"TRACE CREATE_OUTCOME    : "
                        f"LINE={frame.f_lineno} "
                        f"PRICE={snapshot['price']}"
                    )

        elif function_name == "find_future_price":

            print(
                f"TRACE FIND_FUTURE_PRICE  : "
                f"LINE={frame.f_lineno}"
            )

        return trace_function

    if event == "return":

        return_counts[function_name] += 1

        try:
            value_repr = repr(arg)
        except Exception:
            value_repr = "<repr-error>"

        print(
            f"TRACE RETURN             : "
            f"{function_name} | "
            f"TYPE={type(arg).__name__} | "
            f"VALUE={value_repr}"
        )

        return trace_function

    if event == "exception":

        exc_type, exc_value, exc_tb = arg

        runtime_exceptions.append(
            (
                function_name,
                exc_type.__name__,
                str(exc_value),
            )
        )

        print(
            f"TRACE EXCEPTION         : "
            f"{function_name} | "
            f"{exc_type.__name__} | "
            f"{exc_value}"
        )

        return trace_function

    return trace_function


# =============================================================================
# STEP 6 — GENUINE PRODUCTION EXECUTION
# =============================================================================

print()
print("=" * 100)
print("STEP 6 — GENUINE PRODUCTION ENTRYPOINT EXECUTION")
print("=" * 100)

if main_obj is None:

    print(
        "MAIN EXECUTION           : "
        "BLOCKED | main() unresolved"
    )

else:

    print("ENTRYPOINT               : main()")
    print("EXECUTION MODE           : DIRECT FUNCTION INVOCATION")
    print("TRACE MODE               : CPYTHON sys.settrace")

    sys.settrace(trace_function)

    main_return = None

    try:

        main_return = main_obj()

    except Exception as exc:

        runtime_exceptions.append(
            (
                "main",
                type(exc).__name__,
                str(exc),
            )
        )

        print(
            f"MAIN EXCEPTION           : "
            f"{type(exc).__name__} | {exc}"
        )

        traceback.print_exc()

    finally:

        sys.settrace(None)


# =============================================================================
# STEP 7
# =============================================================================

print()
print("=" * 100)
print("STEP 7 — RUNTIME BOUNDARY OBSERVATION")
print("=" * 100)

print(
    f"main() CALLS                : "
    f"{call_counts['main']}"
)

print(
    f"process_signals() CALLS     : "
    f"{call_counts['process_signals']}"
)

print(
    f"create_outcome() CALLS      : "
    f"{call_counts['create_outcome']}"
)

print(
    f"find_future_price() CALLS   : "
    f"{call_counts['find_future_price']}"
)

print(
    f"find_future_price RETURNS   : "
    f"{return_counts['find_future_price']}"
)

print(
    f"create_outcome RETURNS      : "
    f"{return_counts['create_outcome']}"
)

print(
    f"RUNTIME EXCEPTIONS          : "
    f"{len(runtime_exceptions)}"
)


# =============================================================================
# STEP 8
# =============================================================================

print()
print("=" * 100)
print("STEP 8 — PRICE FLOW OBSERVATION")
print("=" * 100)

if not price_observations:

    print("NONE")

else:

    shown = 0

    for lineno, snapshot in price_observations:

        if "price" in snapshot:

            print(
                f"PRICE FLOW | "
                f"LINE={lineno} | "
                f"PRICE={snapshot['price']}"
            )

            shown += 1

            if shown >= 50:

                print(
                    "... additional observations omitted ..."
                )

                break


print(
    f"PRICE FLOW OBSERVATIONS    : "
    f"{len(price_observations)}"
)


# =============================================================================
# STEP 9
# =============================================================================

print()
print("=" * 100)
print("STEP 9 — MAIN RETURN")
print("=" * 100)

print(
    f"MAIN RETURN TYPE           : "
    f"{type(main_return).__name__}"
)

try:

    print(
        f"MAIN RETURN VALUE          : "
        f"{repr(main_return)}"
    )

except Exception:

    print(
        "MAIN RETURN VALUE          : "
        "<unavailable>"
    )


# =============================================================================
# STEP 10
# =============================================================================

print()
print("=" * 100)
print("STEP 10 — RUNTIME EXCEPTION REPORT")
print("=" * 100)

if runtime_exceptions:

    for index, item in enumerate(
        runtime_exceptions,
        start=1,
    ):

        function_name, exc_type, message = item

        print(
            f"{index:03d} | "
            f"FUNCTION={function_name} | "
            f"TYPE={exc_type} | "
            f"VALUE={message}"
        )

else:

    print("NONE")


# =============================================================================
# STEP 11
# =============================================================================

print()
print("=" * 100)
print("STEP 11 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    f"MODULE LOADED               : "
    f"{module_load_error is None}"
)

print(
    f"MAIN RESOLVED               : "
    f"{resolved.get('main') is not None}"
)

print(
    f"PROCESS_SIGNALS RESOLVED    : "
    f"{resolved.get('process_signals') is not None}"
)

print(
    f"CREATE_OUTCOME RESOLVED     : "
    f"{resolved.get('create_outcome') is not None}"
)

print(
    f"FIND_FUTURE_PRICE RESOLVED  : "
    f"{resolved.get('find_future_price') is not None}"
)

print(
    f"MAIN CALLS                  : "
    f"{call_counts['main']}"
)

print(
    f"PROCESS_SIGNALS CALLS       : "
    f"{call_counts['process_signals']}"
)

print(
    f"CREATE_OUTCOME CALLS        : "
    f"{call_counts['create_outcome']}"
)

print(
    f"FIND_FUTURE_PRICE CALLS     : "
    f"{call_counts['find_future_price']}"
)

print(
    f"FIND_FUTURE_PRICE RETURNS   : "
    f"{return_counts['find_future_price']}"
)

print(
    f"CREATE_OUTCOME RETURNS      : "
    f"{return_counts['create_outcome']}"
)

print(
    f"TRACE EVENTS                : "
    f"{trace_events}"
)

print(
    f"RUNTIME EXCEPTIONS          : "
    f"{len(runtime_exceptions)}"
)

print(
    f"BLOCKED WRITE ATTEMPTS      : "
    f"{BLOCKED_WRITE_OPERATIONS}"
)


# =============================================================================
# CONCLUSION
# =============================================================================

if call_counts["find_future_price"] > 0:

    status = "PRODUCTION_PRICE_BOUNDARY_REACHED"

    meaning = (
        "The genuine production main() reached process_signals(), "
        "create_outcome(), and find_future_price()."
    )

    frontier = (
        "Continue tracing the future-price value through "
        "create_outcome() dictionary construction and return packing."
    )

elif call_counts["create_outcome"] > 0:

    status = "CREATE_OUTCOME_BOUNDARY_REACHED"

    meaning = (
        "The genuine production runtime reached create_outcome(), "
        "but find_future_price() was not observed."
    )

    frontier = (
        "Trace the branch immediately before the "
        "find_future_price() call."
    )

elif call_counts["process_signals"] > 0:

    status = "PROCESS_SIGNALS_BOUNDARY_REACHED"

    meaning = (
        "The genuine production runtime reached process_signals(), "
        "but create_outcome() was not observed."
    )

    frontier = (
        "Trace signal eligibility and the exact "
        "create_outcome() invocation branch."
    )

elif call_counts["main"] > 0:

    status = "MAIN_BOUNDARY_REACHED"

    meaning = (
        "The genuine production main() was entered, "
        "but process_signals() was not observed."
    )

    frontier = (
        "Trace main() execution line-by-line to identify "
        "the exact boundary before process_signals()."
    )

else:

    status = "PRODUCTION_RUNTIME_NOT_OBSERVED"

    meaning = (
        "The genuine production entrypoint was not observed."
    )

    frontier = (
        "Resolve module loading and main invocation."
    )


print()
print("FORENSIC CONCLUSION")
print("-" * 100)
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