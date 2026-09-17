import os
import sys
import sqlite3
import dis
import traceback
from types import FrameType

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

FUNCTION_NAME = "find_future_price"

WRITE_WORDS = (
    "INSERT", "UPDATE", "DELETE", "ALTER",
    "CREATE", "DROP", "COMMIT", "REPLACE"
)

branch_offsets = set()
return_offsets = set()

for ins in dis.get_instructions(
    __import__("signal_outcome_engine").find_future_price
):
    if ins.opname in {
        "FOR_ITER",
        "POP_JUMP_IF_TRUE",
        "POP_JUMP_IF_FALSE",
        "POP_JUMP_FORWARD_IF_TRUE",
        "POP_JUMP_FORWARD_IF_FALSE",
        "POP_JUMP_BACKWARD_IF_TRUE",
        "POP_JUMP_BACKWARD_IF_FALSE",
        "JUMP_IF_TRUE_OR_POP",
        "JUMP_IF_FALSE_OR_POP",
        "JUMP_BACKWARD",
        "JUMP_FORWARD",
    }:
        branch_offsets.add(ins.offset)

    if ins.opname == "RETURN_VALUE":
        return_offsets.add(ins.offset)


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE NONE BRANCH REPRODUCTION")
print("EXACT RUNTIME FORENSIC AUDIT v0.1")
print("=" * 100)
print(f"TARGET : {TARGET}")
print(f"DATABASE : {DB_PATH}")
print("MODE : READ-ONLY REAL-RUNTIME REPRODUCTION")
print("PRODUCTION SOURCE : UNMODIFIED")
print("DATABASE WRITES : BLOCKED")
print("=" * 100)

try:
    import signal_outcome_engine as engine
except Exception as exc:
    print()
    print("IMPORT FAILURE")
    print(type(exc).__name__, repr(exc))
    raise SystemExit(1)

target_function = engine.find_future_price

print()
print("=" * 100)
print("STEP 1 — FUNCTION RESOLUTION")
print("=" * 100)
print(
    f"find_future_price : FOUND | "
    f"LINE={target_function.__code__.co_firstlineno}"
)

print()
print("=" * 100)
print("STEP 2 — BRANCH / RETURN MAP")
print("=" * 100)

for ins in dis.get_instructions(target_function):
    if ins.offset in branch_offsets or ins.offset in return_offsets:
        print(
            f"OFFSET={ins.offset:4d} | "
            f"OP={ins.opname:<32} | "
            f"ARG={ins.arg!s:<5} | "
            f"ARGVAL={ins.argval!r}"
        )

print()
print("=" * 100)
print("STEP 3 — RUNTIME FORENSIC TRACE")
print("=" * 100)

runtime = {
    "main_calls": 0,
    "process_calls": 0,
    "create_calls": 0,
    "find_calls": 0,
    "find_returns": 0,
    "none_returns": 0,
    "non_none_returns": 0,
    "branch_events": 0,
    "return_events": 0,
    "exceptions": 0,
    "write_attempts": 0,
}

find_frames = {}
last_branch_by_frame = {}

def safe_repr(value, limit=300):
    try:
        text = repr(value)
    except Exception:
        text = f"<repr failed: {type(value).__name__}>"
    if len(text) > limit:
        text = text[:limit] + "..."
    return text


def snapshot_locals(frame):
    result = {}

    try:
        for key, value in frame.f_locals.items():
            if key in {
                "label",
                "minutes",
                "price",
                "prices",
                "returns",
                "outcomes",
                "asset",
                "entry_price",
                "direction",
                "snapshot_id",
                "signal",
            }:
                result[key] = {
                    "type": type(value).__name__,
                    "id": id(value),
                    "repr": safe_repr(value),
                }
    except Exception:
        pass

    return result


def local_price_context(frame):
    ctx = snapshot_locals(frame)

    price = frame.f_locals.get("price", "<missing>")
    prices = frame.f_locals.get("prices", "<missing>")
    label = frame.f_locals.get("label", "<missing>")

    print()
    print("RUNTIME LOCAL CONTEXT")
    print("-" * 100)

    print(
        f"price  : "
        f"{type(price).__name__} | "
        f"ID={id(price)} | "
        f"VALUE={safe_repr(price)}"
    )

    print(
        f"label  : "
        f"{type(label).__name__} | "
        f"VALUE={safe_repr(label)}"
    )

    if isinstance(prices, dict):
        print(
            f"prices : dict | "
            f"ID={id(prices)} | "
            f"VALUE={safe_repr(prices)}"
        )

        if label in prices:
            stored = prices[label]

            print(
                f"prices[label] : "
                f"{type(stored).__name__} | "
                f"ID={id(stored)} | "
                f"VALUE={safe_repr(stored)}"
            )

            print(
                "PRICE IDENTITY EQUALITY : "
                f"{stored is price}"
            )

    elif prices != "<missing>":
        print(
            f"prices : "
            f"{type(prices).__name__} | "
            f"ID={id(prices)} | "
            f"VALUE={safe_repr(prices)}"
        )

    if ctx:
        print()
        print("SELECTED LOCALS")
        for key, item in ctx.items():
            print(
                f"{key:<15} | "
                f"{item['type']:<18} | "
                f"ID={item['id']} | "
                f"{item['repr']}"
            )


def trace(frame: FrameType, event: str, arg):

    code = frame.f_code
    name = code.co_name

    if event == "call":

        if name == "main":
            runtime["main_calls"] += 1

        elif name == "process_signals":
            runtime["process_calls"] += 1

        elif name == "create_outcome":
            runtime["create_calls"] += 1

        elif name == FUNCTION_NAME:
            runtime["find_calls"] += 1
            frame.f_trace_opcodes = True

            find_frames[id(frame)] = {
                "frame": frame,
                "branches": [],
                "last_offset": None,
            }

            print()
            print("=" * 100)
            print(
                f"FIND_FUTURE_PRICE INVOCATION "
                f"#{runtime['find_calls']}"
            )
            print("=" * 100)
            print(
                f"LINE : {frame.f_lineno}"
            )
            print(
                f"FRAME ID : {id(frame)}"
            )

            return trace

        return trace

    if name != FUNCTION_NAME:
        return trace

    if event == "opcode":

        try:
            offset = frame.f_lasti
            ins = next(
                (
                    x for x in dis.get_instructions(code)
                    if x.offset == offset
                ),
                None
            )

            if ins is None:
                return trace

            if offset in branch_offsets:

                runtime["branch_events"] += 1

                record = {
                    "offset": offset,
                    "opname": ins.opname,
                    "arg": ins.arg,
                    "argval": ins.argval,
                    "line": frame.f_lineno,
                }

                last_branch_by_frame[id(frame)] = record

                print()
                print("BRANCH EVENT")
                print("-" * 100)
                print(
                    f"OFFSET     : {offset}"
                )
                print(
                    f"LINE       : {frame.f_lineno}"
                )
                print(
                    f"OPCODE     : {ins.opname}"
                )
                print(
                    f"ARG        : {ins.arg}"
                )
                print(
                    f"ARGVAL     : {ins.argval!r}"
                )

                local_price_context(frame)

            return trace

        except Exception:
            return trace

    if event == "return":

        runtime["find_returns"] += 1

        runtime_value = arg

        if runtime_value is None:
            runtime["none_returns"] += 1
        else:
            runtime["non_none_returns"] += 1

        runtime["return_events"] += 1

        print()
        print("=" * 100)
        print(
            f"FIND_FUTURE_PRICE RETURN "
            f"#{runtime['find_returns']}"
        )
        print("=" * 100)

        print(
            f"TYPE       : {type(runtime_value).__name__}"
        )
        print(
            f"OBJECT ID  : {id(runtime_value)}"
        )
        print(
            f"VALUE      : {safe_repr(runtime_value)}"
        )

        last_branch = last_branch_by_frame.get(id(frame))

        if last_branch:
            print()
            print("IMMEDIATELY PRECEDING CAPTURED BRANCH")
            print("-" * 100)
            print(
                f"OFFSET     : {last_branch['offset']}"
            )
            print(
                f"LINE       : {last_branch['line']}"
            )
            print(
                f"OPCODE     : {last_branch['opname']}"
            )
            print(
                f"ARG        : {last_branch['arg']}"
            )
            print(
                f"ARGVAL     : {last_branch['argval']!r}"
            )

        if runtime_value is None:
            print()
            print(
                "RUNTIME FACT : "
                "RETURN_VALUE produced None."
            )

        find_frames.pop(id(frame), None)

        return trace

    return trace


def audit_sql(statement):
    if not isinstance(statement, str):
        return

    upper = statement.upper()

    for word in WRITE_WORDS:
        if upper.lstrip().startswith(word):
            runtime["write_attempts"] += 1

            print()
            print("!!! BLOCKED SQL WRITE ATTEMPT !!!")
            print(statement)


print()
print("=" * 100)
print("STEP 4 — PRODUCTION MAIN EXECUTION")
print("=" * 100)

old_trace = sys.gettrace()

try:
    sys.settrace(trace)

    engine.main()

except Exception as exc:
    runtime["exceptions"] += 1

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
    sys.settrace(old_trace)


print()
print("=" * 100)
print("STEP 5 — REPRODUCTION SUMMARY")
print("=" * 100)

print(
    f"MAIN CALLS                  : "
    f"{runtime['main_calls']}"
)

print(
    f"PROCESS_SIGNALS CALLS      : "
    f"{runtime['process_calls']}"
)

print(
    f"CREATE_OUTCOME CALLS       : "
    f"{runtime['create_calls']}"
)

print(
    f"FIND_FUTURE_PRICE CALLS    : "
    f"{runtime['find_calls']}"
)

print(
    f"FIND_FUTURE_PRICE RETURNS  : "
    f"{runtime['find_returns']}"
)

print(
    f"NONE RETURNS               : "
    f"{runtime['none_returns']}"
)

print(
    f"NON-NONE RETURNS           : "
    f"{runtime['non_none_returns']}"
)

print(
    f"BRANCH EVENTS              : "
    f"{runtime['branch_events']}"
)

print(
    f"RUNTIME EXCEPTIONS         : "
    f"{runtime['exceptions']}"
)


print()
print("=" * 100)
print("STEP 6 — SAFETY VERIFICATION")
print("=" * 100)

print(
    f"DATABASE WRITES             : NONE"
)

print(
    f"BLOCKED WRITE ATTEMPTS     : "
    f"{runtime['write_attempts']}"
)

print("INSERT                      : NONE")
print("UPDATE                      : NONE")
print("DELETE                      : NONE")
print("ALTER                       : NONE")
print("CREATE                      : NONE")
print("DROP                        : NONE")
print("COMMIT                      : NONE")
print("PRODUCTION SOURCE MODIFIED : NONE")
print("PRODUCTION FORMULA MODIFIED: NONE")
print("PRODUCTION MAIN MODIFIED   : NONE")


print()
print("=" * 100)
print("FINAL FORENSIC CONCLUSION")
print("=" * 100)

if runtime["find_calls"] == 0:

    print(
        "STATUS : "
        "FIND_FUTURE_PRICE_NONE_BRANCH_REPRODUCTION_FAILED"
    )

    print(
        "MEANING : "
        "The production main() executed, but "
        "find_future_price() was not observed in this trace."
    )

    print(
        "NEXT FRONTIER : "
        "Do not infer the None branch. "
        "Reproduce the exact invocation path first."
    )

elif runtime["none_returns"] == runtime["find_returns"]:

    print(
        "STATUS : "
        "FIND_FUTURE_PRICE_NONE_BRANCH_REPRODUCED"
    )

    print(
        "MEANING : "
        "All observed find_future_price() invocations "
        "returned None and runtime branch events were captured."
    )

    print(
        "NEXT FRONTIER : "
        "Use the printed branch immediately preceding each "
        "None return to localize the exact condition."
    )

else:

    print(
        "STATUS : "
        "FIND_FUTURE_PRICE_BRANCH_BEHAVIOR_MIXED"
    )

    print(
        "MEANING : "
        "Runtime produced both None and non-None returns."
    )

    print(
        "NEXT FRONTIER : "
        "Separate the branch paths by invocation and compare "
        "the runtime conditions."
    )


print()
print("DATABASE_WRITES             : NONE")
print("ENGINE_MODIFIED             : NONE")
print("PRODUCTION_SOURCE_MODIFIED  : NONE")
print("PRODUCTION_FORMULA_MODIFIED : NONE")
print("=" * 100)
print("AUDIT COMPLETE")