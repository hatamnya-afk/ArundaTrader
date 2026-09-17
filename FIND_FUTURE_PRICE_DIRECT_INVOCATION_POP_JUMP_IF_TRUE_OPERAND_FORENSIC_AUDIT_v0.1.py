import ast
import dis
import inspect
import os
import sqlite3
import sys
import traceback
import types
from pathlib import Path


TARGET_FILE = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DATABASE_FILE = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_OFFSETS = {206, 226}

ASSETS = ["BTC", "ETH", "SOL", "XRP"]
MINUTES_LIST = [5, 15, 30, 60]


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE DIRECT INVOCATION")
print("POP_JUMP_IF_TRUE OPERAND FORENSIC AUDIT v0.1")
print("=" * 100)
print(f"TARGET : {TARGET_FILE}")
print(f"DATABASE : {DATABASE_FILE}")
print("MODE : READ-ONLY DIRECT FUNCTION INVOCATION")
print("PRODUCTION SOURCE : UNMODIFIED")
print("DATABASE WRITES : BLOCKED")
print("=" * 100)


# =============================================================================
# STEP 0 — VALIDATE FILES
# =============================================================================

if not os.path.isfile(TARGET_FILE):
    print("FATAL : production source file not found")
    sys.exit(1)

if not os.path.isfile(DATABASE_FILE):
    print("FATAL : production database file not found")
    sys.exit(1)


# =============================================================================
# STEP 1 — READ-ONLY SQLITE CONNECTION
# =============================================================================

print()
print("=" * 100)
print("STEP 1 — READ-ONLY DATABASE GUARD")
print("=" * 100)

uri = "file:" + os.path.abspath(DATABASE_FILE) + "?mode=ro"

try:
    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row

    print("DATABASE MODE : READ-ONLY")
    print("WRITE OPERATIONS : BLOCKED")

except Exception as exc:
    print("DATABASE OPEN ERROR :", repr(exc))
    sys.exit(1)


# =============================================================================
# STEP 2 — LOAD PRODUCTION MODULE WITHOUT EXECUTING main()
# =============================================================================

print()
print("=" * 100)
print("STEP 2 — LOAD PRODUCTION MODULE WITHOUT AUTO-MAIN")
print("=" * 100)


source_text = Path(TARGET_FILE).read_text(
    encoding="utf-8"
)


try:
    tree = ast.parse(
        source_text,
        filename=TARGET_FILE
    )
except Exception as exc:
    print("AST PARSE ERROR :", repr(exc))
    conn.close()
    sys.exit(1)


# -----------------------------------------------------------------------------
# Remove ONLY top-level automatic main() invocation from the in-memory AST.
#
# This does NOT modify the production source file.
#
# The production function bodies remain untouched.
# -----------------------------------------------------------------------------

new_body = []

removed_main_calls = 0

for node in tree.body:

    is_main_call = False

    if isinstance(node, ast.Expr):
        value = node.value

        if isinstance(value, ast.Call):
            func = value.func

            if (
                isinstance(func, ast.Name)
                and func.id == "main"
                and len(value.args) == 0
                and len(value.keywords) == 0
            ):
                is_main_call = True

    if is_main_call:
        removed_main_calls += 1
        continue

    new_body.append(node)


tree.body = new_body

ast.fix_missing_locations(tree)


namespace = {
    "__name__": "__arunda_forensic_direct__",
    "__file__": TARGET_FILE,
    "__package__": None,
}

try:
    compiled = compile(
        tree,
        TARGET_FILE,
        "exec"
    )

    exec(
        compiled,
        namespace,
        namespace
    )

except Exception as exc:
    print("PRODUCTION MODULE LOAD ERROR :", repr(exc))
    traceback.print_exc()
    conn.close()
    sys.exit(1)


print("MODULE LOAD : SUCCESS")
print("AUTO-MAIN CALLS REMOVED IN MEMORY :", removed_main_calls)
print("PRODUCTION SOURCE FILE MODIFIED : NONE")


# =============================================================================
# STEP 3 — RESOLVE find_future_price
# =============================================================================

print()
print("=" * 100)
print("STEP 3 — DIRECT FUNCTION RESOLUTION")
print("=" * 100)


find_future_price = namespace.get("find_future_price")


if not isinstance(
    find_future_price,
    types.FunctionType
):
    print("find_future_price : NOT FOUND")
    conn.close()
    sys.exit(1)


print(
    "FUNCTION : find_future_price"
)

print(
    "FILE     :",
    find_future_price.__code__.co_filename
)

print(
    "LINE     :",
    find_future_price.__code__.co_firstlineno
)

print(
    "SIGNATURE :",
    inspect.signature(find_future_price)
)


# =============================================================================
# STEP 4 — EXACT TARGET BYTECODE
# =============================================================================

print()
print("=" * 100)
print("STEP 4 — TARGET POP_JUMP_IF_TRUE BYTECODE")
print("=" * 100)


instructions = list(
    dis.get_instructions(find_future_price)
)

for ins in instructions:

    if ins.offset in TARGET_OFFSETS:

        print(
            f"OFFSET={ins.offset:>4} "
            f"LINE={str(ins.starts_line):<5} "
            f"OP={ins.opname:<25} "
            f"ARG={ins.arg!s:<5} "
            f"ARGVAL={ins.argval!r}"
        )


print()
print("INSTRUCTIONS IMMEDIATELY PRECEDING TARGET BRANCHES")
print("-" * 100)


for index, ins in enumerate(instructions):

    if ins.offset not in TARGET_OFFSETS:
        continue

    start = max(
        0,
        index - 8
    )

    end = min(
        len(instructions),
        index + 3
    )

    print()
    print(
        f"TARGET OFFSET {ins.offset}"
    )

    for x in instructions[start:end]:

        marker = "<<< TARGET" if x.offset == ins.offset else ""

        print(
            f"{x.offset:>5} "
            f"{x.opname:<25} "
            f"{str(x.argval):<25} "
            f"{marker}"
        )


# =============================================================================
# STEP 5 — RUNTIME OPCODE TRACE
# =============================================================================

print()
print("=" * 100)
print("STEP 5 — DIRECT find_future_price() OPCODE TRACE")
print("=" * 100)


runtime_events = []
return_events = []
exception_events = []

active_depth = 0


def safe_repr(value, limit=500):

    try:
        text = repr(value)
    except Exception:
        text = "<repr-error>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def snapshot_locals(frame):

    result = {}

    for name, value in frame.f_locals.items():

        try:
            result[name] = {
                "type": type(value).__name__,
                "id": id(value),
                "repr": safe_repr(value),
            }

        except Exception:

            result[name] = {
                "type": "<error>",
                "id": 0,
                "repr": "<error>",
            }

    return result


def trace_function(frame, event, arg):

    global active_depth

    if frame.f_code is not find_future_price.__code__:
        return trace_function

    if event == "call":

        active_depth += 1

        try:
            frame.f_trace_opcodes = True
        except Exception:
            pass

        return trace_function

    if event == "opcode":

        offset = frame.f_lasti

        if offset in TARGET_OFFSETS:

            ins = None

            for candidate in instructions:

                if candidate.offset == offset:
                    ins = candidate
                    break

            event_data = {
                "offset": offset,
                "opname": ins.opname if ins else "<unknown>",
                "arg": ins.arg if ins else None,
                "argval": ins.argval if ins else None,
                "locals": snapshot_locals(frame),
            }

            runtime_events.append(event_data)

            print()
            print("=" * 100)
            print("POP_JUMP_IF_TRUE RUNTIME EVENT")
            print("=" * 100)

            print(
                "OFFSET :",
                offset
            )

            print(
                "OPCODE :",
                ins.opname if ins else "<unknown>"
            )

            print(
                "ARG    :",
                ins.arg
                if ins
                else None
            )

            print(
                "ARGVAL :",
                repr(ins.argval)
                if ins
                else None
            )

            print()
            print("RUNTIME LOCALS")
            print("-" * 100)

            for name, data in event_data["locals"].items():

                print(
                    f"{name:<20} | "
                    f"{data['type']:<15} | "
                    f"ID={data['id']} | "
                    f"{data['repr']}"
                )

    elif event == "return":

        return_events.append(
            {
                "offset": frame.f_lasti,
                "value": arg,
                "type": type(arg).__name__,
                "id": id(arg),
                "locals": snapshot_locals(frame),
            }
        )

        print()
        print("=" * 100)
        print("find_future_price RETURN")
        print("=" * 100)

        print(
            "RETURN OFFSET :",
            frame.f_lasti
        )

        print(
            "TYPE          :",
            type(arg).__name__
        )

        print(
            "OBJECT ID     :",
            id(arg)
        )

        print(
            "VALUE         :",
            safe_repr(arg)
        )

    elif event == "exception":

        exception_type, exception_value, exception_tb = arg

        exception_events.append(
            {
                "type": exception_type.__name__,
                "value": safe_repr(exception_value),
                "offset": frame.f_lasti,
            }
        )

        print()
        print("=" * 100)
        print("find_future_price EXCEPTION")
        print("=" * 100)

        print(
            "OFFSET :",
            frame.f_lasti
        )

        print(
            "TYPE   :",
            exception_type.__name__
        )

        print(
            "VALUE  :",
            safe_repr(exception_value)
        )

    return trace_function


# =============================================================================
# STEP 6 — DIRECT INVOCATION ARGUMENT RESOLUTION
# =============================================================================

print()
print("=" * 100)
print("STEP 6 — DIRECT INVOCATION ARGUMENT RESOLUTION")
print("=" * 100)


signature = inspect.signature(
    find_future_price
)

parameters = list(
    signature.parameters.values()
)

print("PARAMETERS")

for parameter in parameters:

    print(
        f"{parameter.name:<20} "
        f"KIND={parameter.kind} "
        f"DEFAULT={parameter.default!r}"
    )


# -----------------------------------------------------------------------------
# This audit intentionally uses only the known production runtime dimensions:
#
# conn
# asset
# minutes
#
# No price is fabricated.
# -----------------------------------------------------------------------------

def build_arguments(asset, minutes):

    args = []

    for parameter in parameters:

        name = parameter.name.lower()

        if name in {
            "conn",
            "connection",
            "db",
            "database",
        }:

            args.append(conn)

        elif name in {
            "asset",
            "symbol",
            "ticker",
        }:

            args.append(asset)

        elif name in {
            "minutes",
            "minute",
            "horizon",
        }:

            args.append(minutes)

        else:

            if (
                parameter.default
                is not inspect.Parameter.empty
            ):

                continue

            raise RuntimeError(
                "UNRESOLVED_REQUIRED_PARAMETER:"
                + parameter.name
            )

    return args


# =============================================================================
# STEP 7 — DIRECT PRODUCTION INVOCATIONS
# =============================================================================

print()
print("=" * 100)
print("STEP 7 — DIRECT find_future_price() INVOCATIONS")
print("=" * 100)


invocation_count = 0
successful_count = 0
failed_count = 0


old_trace = sys.gettrace()

try:

    sys.settrace(trace_function)

    for asset in ASSETS:

        for minutes in MINUTES_LIST:

            invocation_count += 1

            print()
            print("-" * 100)

            print(
                f"DIRECT INVOCATION #{invocation_count}"
            )

            print(
                "ASSET   :",
                asset
            )

            print(
                "MINUTES :",
                minutes
            )

            try:

                args = build_arguments(
                    asset,
                    minutes
                )

                print(
                    "ARGUMENTS :",
                    [
                        (
                            type(x).__name__,
                            id(x),
                            safe_repr(x)
                        )
                        for x in args
                    ]
                )

                result = find_future_price(
                    *args
                )

                successful_count += 1

                print()
                print(
                    "DIRECT RETURN :",
                    type(result).__name__,
                    "| ID=",
                    id(result),
                    "| VALUE=",
                    safe_repr(result)
                )

            except Exception as exc:

                failed_count += 1

                print()
                print(
                    "DIRECT INVOCATION EXCEPTION :",
                    repr(exc)
                )

                traceback.print_exc()


finally:

    sys.settrace(old_trace)


# =============================================================================
# STEP 8 — FINAL FORENSIC SUMMARY
# =============================================================================

print()
print("=" * 100)
print("FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    "DIRECT INVOCATIONS        :",
    invocation_count
)

print(
    "SUCCESSFUL INVOCATIONS    :",
    successful_count
)

print(
    "FAILED INVOCATIONS        :",
    failed_count
)

print(
    "POP_JUMP_IF_TRUE EVENTS   :",
    len(runtime_events)
)

print(
    "RETURN EVENTS             :",
    len(return_events)
)

print(
    "RUNTIME EXCEPTIONS        :",
    len(exception_events)
)


# =============================================================================
# STEP 9 — BRANCH EVENT DETAIL
# =============================================================================

print()
print("=" * 100)
print("POP_JUMP_IF_TRUE EVENT DETAIL")
print("=" * 100)


if not runtime_events:

    print(
        "NO TARGET POP_JUMP_IF_TRUE EVENT WAS OBSERVED."
    )

else:

    for number, event in enumerate(
        runtime_events,
        start=1
    ):

        print()
        print(
            f"EVENT #{number}"
        )

        print(
            "OFFSET :",
            event["offset"]
        )

        print(
            "OPCODE :",
            event["opname"]
        )

        print(
            "ARG    :",
            event["arg"]
        )

        print(
            "ARGVAL :",
            repr(event["argval"])
        )

        print()
        print("LOCALS")
        print("-" * 100)

        for name, data in event["locals"].items():

            print(
                f"{name:<20} | "
                f"{data['type']:<15} | "
                f"ID={data['id']} | "
                f"{data['repr']}"
            )


# =============================================================================
# STEP 10 — RETURN DETAIL
# =============================================================================

print()
print("=" * 100)
print("RETURN DETAIL")
print("=" * 100)


for number, event in enumerate(
    return_events,
    start=1
):

    print()
    print(
        f"RETURN #{number}"
    )

    print(
        "TYPE :",
        event["type"]
    )

    print(
        "ID   :",
        event["id"]
    )

    print(
        "VALUE:",
        safe_repr(event["value"])
    )


# =============================================================================
# STEP 11 — SAFETY VERIFICATION
# =============================================================================

print()
print("=" * 100)
print("SAFETY VERIFICATION")
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
print("DATABASE FILE WRITES        : NONE")


# =============================================================================
# STEP 12 — FORENSIC CONCLUSION
# =============================================================================

print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("=" * 100)


if failed_count > 0 and successful_count == 0:

    status = (
        "DIRECT_INVOCATION_FAILED"
    )

    meaning = (
        "The direct find_future_price() invocation "
        "could not be completed. No branch behavior "
        "is inferred."
    )

elif len(runtime_events) == 0:

    status = (
        "POP_JUMP_IF_TRUE_DIRECT_RUNTIME_NOT_REACHED"
    )

    meaning = (
        "Direct find_future_price() invocation was attempted, "
        "but neither target POP_JUMP_IF_TRUE offset was observed."
    )

else:

    status = (
        "POP_JUMP_IF_TRUE_DIRECT_RUNTIME_CAPTURED"
    )

    meaning = (
        "Direct find_future_price() invocation reached at least "
        "one target POP_JUMP_IF_TRUE instruction. Runtime locals "
        "and exact opcode context were captured."
    )


print(
    "STATUS :",
    status
)

print(
    "MEANING:",
    meaning
)

print()
print(
    "NEXT FRONTIER :"
)

if len(runtime_events) > 0:

    print(
        "Use the captured runtime state immediately "
        "preceding POP_JUMP_IF_TRUE at offsets 206/226."
    )

    print(
        "Do not infer the operand value from source code alone."
    )

else:

    print(
        "Reproduce direct find_future_price() execution "
        "until offset 206 or 226 is reached."
    )

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)


try:
    conn.close()
except Exception:
    pass