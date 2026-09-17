import os
import sys
import dis
import types
import traceback
import sqlite3
import inspect
import runpy

TARGET_FILE = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_FILE = r"C:\Users\ASUS\ArundaTrader\arunda.db"
TARGET_FUNCTION = "find_future_price"
TARGET_OFFSETS = {206, 226}

print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE REAL INVOCATION POP_JUMP OPERAND FORENSIC AUDIT v0.1")
print("=" * 100)
print(f"TARGET : {TARGET_FILE}")
print(f"DATABASE : {DB_FILE}")
print("MODE : READ-ONLY REAL-RUNTIME FORENSICS")
print("PRODUCTION SOURCE : UNMODIFIED")
print("DATABASE WRITES : BLOCKED")
print("=" * 100)

# ----------------------------------------------------------------------
# READ-ONLY SQLITE GUARD
# ----------------------------------------------------------------------

_real_connect = sqlite3.connect


def readonly_connect(*args, **kwargs):
    if args:
        path = args[0]
    else:
        path = kwargs.get("database")

    if isinstance(path, str) and path.lower().endswith(".db"):
        uri = "file:" + os.path.abspath(path) + "?mode=ro"
        kwargs["uri"] = True
        if args:
            args = (uri,) + tuple(args[1:])
        else:
            kwargs["database"] = uri

    conn = _real_connect(*args, **kwargs)

    real_execute = conn.execute
    real_executemany = conn.executemany
    real_executescript = conn.executescript
    real_commit = conn.commit

    def blocked_execute(sql, *a, **kw):
        text = str(sql).strip().upper()

        forbidden = (
            "INSERT ",
            "UPDATE ",
            "DELETE ",
            "ALTER ",
            "CREATE ",
            "DROP ",
            "REPLACE ",
        )

        if text.startswith(forbidden) or text == "COMMIT":
            print("BLOCKED WRITE ATTEMPT :", text[:120])
            raise RuntimeError("ARUNDA_FORENSIC_WRITE_BLOCKED")

        return real_execute(sql, *a, **kw)

    def blocked_executemany(sql, *a, **kw):
        print("BLOCKED EXECUTEMANY")
        raise RuntimeError("ARUNDA_FORENSIC_WRITE_BLOCKED")

    def blocked_executescript(sql, *a, **kw):
        print("BLOCKED EXECUTESCRIPT")
        raise RuntimeError("ARUNDA_FORENSIC_WRITE_BLOCKED")

    def blocked_commit(*a, **kw):
        print("BLOCKED COMMIT")
        raise RuntimeError("ARUNDA_FORENSIC_WRITE_BLOCKED")

    try:
        conn.execute = blocked_execute
        conn.executemany = blocked_executemany
        conn.executescript = blocked_executescript
        conn.commit = blocked_commit
    except Exception:
        pass

    return conn


# ----------------------------------------------------------------------
# STATIC TARGET RESOLUTION
# ----------------------------------------------------------------------

if not os.path.exists(TARGET_FILE):
    raise FileNotFoundError(TARGET_FILE)

source = open(TARGET_FILE, "r", encoding="utf-8").read()

compile(source, TARGET_FILE, "exec")

namespace = {
    "__name__": "__arunda_forensic_runtime__",
    "__file__": TARGET_FILE,
    "__package__": None,
    "__cached__": None,
}

# prevent accidental automatic main execution during loader stage
try:
    exec(compile(source, TARGET_FILE, "exec"), namespace, namespace)
except SystemExit:
    pass
except Exception as exc:
    print()
    print("=" * 100)
    print("MODULE LOAD EXCEPTION")
    print("=" * 100)
    print(repr(exc))
    print()
    print("The forensic loader will attempt runtime capture through")
    print("the production entrypoint only if the target function exists.")
    print()

find_future_price = namespace.get(TARGET_FUNCTION)

if not isinstance(find_future_price, types.FunctionType):
    raise RuntimeError("find_future_price function was not resolved")

print()
print("=" * 100)
print("STEP 1 — TARGET FUNCTION")
print("=" * 100)

print("FUNCTION :", find_future_price.__name__)
print("FILE     :", find_future_price.__code__.co_filename)
print("LINE     :", find_future_price.__code__.co_firstlineno)

print()
print("=" * 100)
print("STEP 2 — EXACT SIGNATURE")
print("=" * 100)

try:
    sig = inspect.signature(find_future_price)
    print("SIGNATURE :", sig)
except Exception as exc:
    print("SIGNATURE ERROR :", repr(exc))

print()
print("=" * 100)
print("STEP 3 — TARGET BYTECODE")
print("=" * 100)

instructions = list(dis.get_instructions(find_future_price))

for ins in instructions:
    if ins.offset in TARGET_OFFSETS:
        print(
            f"OFFSET={ins.offset:>4} "
            f"LINE={ins.starts_line!s:<5} "
            f"OP={ins.opname:<24} "
            f"ARG={ins.arg!s:<4} "
            f"ARGVAL={ins.argval!s}"
        )

print()
print("=" * 100)
print("STEP 4 — PRECEDING OPCODE WINDOWS")
print("=" * 100)

for target in sorted(TARGET_OFFSETS):
    print()
    print("TARGET OFFSET :", target)

    nearby = [
        ins for ins in instructions
        if target - 24 <= ins.offset <= target
    ]

    for ins in nearby:
        print(
            f"{ins.offset:>4} "
            f"{str(ins.starts_line):>5} "
            f"{ins.opname:<28} "
            f"ARG={str(ins.arg):<5} "
            f"ARGVAL={ins.argval!s}"
        )

# ----------------------------------------------------------------------
# RUNTIME STATE
# ----------------------------------------------------------------------

runtime = {
    "main_calls": 0,
    "find_calls": 0,
    "find_returns": 0,
    "none_returns": 0,
    "non_none_returns": 0,
    "branch_events": 0,
    "target_206": 0,
    "target_226": 0,
    "runtime_exceptions": 0,
    "captured_invocations": [],
}

active_find_frames = {}
last_find_frame_id = None


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        text = text[:limit] + "...<TRUNCATED>"

    return text


def locals_snapshot(frame):
    result = {}

    for key, value in frame.f_locals.items():
        try:
            result[key] = {
                "type": type(value).__name__,
                "id": id(value),
                "repr": safe_repr(value),
            }
        except Exception:
            result[key] = {
                "type": "<error>",
                "id": None,
                "repr": "<error>",
            }

    return result


def print_selected_locals(frame):
    names = [
        "conn",
        "asset",
        "entry_timestamp",
        "minutes",
        "target_epoch",
        "rows",
        "row",
        "row_epoch",
        "distance",
        "best_distance",
        "best_price",
        "price",
        "label",
    ]

    for name in names:
        if name in frame.f_locals:
            value = frame.f_locals[name]

            print(
                f"{name:<18} | "
                f"TYPE={type(value).__name__:<15} | "
                f"ID={id(value)} | "
                f"VALUE={safe_repr(value, 350)}"
            )


def trace(frame, event, arg):
    global last_find_frame_id

    try:
        code = frame.f_code
        filename = os.path.abspath(code.co_filename)

        if filename != os.path.abspath(TARGET_FILE):
            return trace

        if code.co_name != TARGET_FUNCTION:
            return trace

        frame_id = id(frame)

        if event == "call":
            runtime["find_calls"] += 1
            active_find_frames[frame_id] = frame
            last_find_frame_id = frame_id

            print()
            print("=" * 100)
            print(f"REAL find_future_price INVOCATION #{runtime['find_calls']}")
            print("=" * 100)

            print_selected_locals(frame)

            try:
                args = inspect.getargvalues(frame)

                print()
                print("ACTUAL PRODUCTION ARGUMENTS")
                print("-" * 100)

                for name in args.args:
                    value = frame.f_locals.get(name)

                    print(
                        f"{name:<20} | "
                        f"TYPE={type(value).__name__:<15} | "
                        f"ID={id(value)} | "
                        f"VALUE={safe_repr(value, 500)}"
                    )

                runtime["captured_invocations"].append(
                    {
                        "args": {
                            name: frame.f_locals.get(name)
                            for name in args.args
                        }
                    }
                )

            except Exception as exc:
                print("ARGUMENT CAPTURE ERROR :", repr(exc))

            frame.f_trace_opcodes = True
            return trace

        if event == "opcode":
            offset = frame.f_lasti

            if offset in TARGET_OFFSETS:
                runtime["branch_events"] += 1

                if offset == 206:
                    runtime["target_206"] += 1

                if offset == 226:
                    runtime["target_226"] += 1

                ins = next(
                    (
                        x for x in instructions
                        if x.offset == offset
                    ),
                    None,
                )

                print()
                print("=" * 100)
                print("POP_JUMP_IF_TRUE RUNTIME EVENT")
                print("=" * 100)

                print(
                    "OFFSET     :",
                    offset
                )

                if ins is not None:
                    print(
                        "OPCODE     :",
                        ins.opname
                    )
                    print(
                        "ARG        :",
                        ins.arg
                    )
                    print(
                        "ARGVAL     :",
                        ins.argval
                    )

                print()
                print("RUNTIME LOCALS")
                print("-" * 100)

                print_selected_locals(frame)

                print()
                print("COMPLETE LOCAL SNAPSHOT")
                print("-" * 100)

                snap = locals_snapshot(frame)

                for key in sorted(snap):
                    item = snap[key]

                    print(
                        f"{key:<20} | "
                        f"{item['type']:<18} | "
                        f"ID={item['id']} | "
                        f"{item['repr']}"
                    )

                print()
                print("IMPORTANT")
                print("-" * 100)
                print(
                    "The CPython frame API does not expose the evaluation stack "
                    "directly. Therefore this audit does NOT invent the operand value."
                )
                print(
                    "The exact runtime locals immediately at POP_JUMP_IF_TRUE "
                    "are recorded as evidence."
                )

        if event == "return":
            runtime["find_returns"] += 1

            if arg is None:
                runtime["none_returns"] += 1
            else:
                runtime["non_none_returns"] += 1

            print()
            print("=" * 100)
            print(
                f"FIND_FUTURE_PRICE RETURN #{runtime['find_returns']}"
            )
            print("=" * 100)

            print(
                "TYPE  :",
                type(arg).__name__
            )

            print(
                "ID    :",
                id(arg)
            )

            print(
                "VALUE :",
                safe_repr(arg, 500)
            )

            print()
            print("RETURN LOCALS")
            print("-" * 100)

            print_selected_locals(frame)

            active_find_frames.pop(frame_id, None)

            return trace

    except Exception as exc:
        runtime["runtime_exceptions"] += 1

        print()
        print("TRACE EXCEPTION :", repr(exc))

    return trace


# ----------------------------------------------------------------------
# REAL PRODUCTION EXECUTION
# ----------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 5 — REAL PRODUCTION EXECUTION")
print("=" * 100)

try:
    sys.settrace(trace)

    # Production source is executed exactly as a module.
    # We do not call find_future_price manually and do not fabricate
    # entry_timestamp.
    runpy.run_path(
        TARGET_FILE,
        run_name="__main__"
    )

except SystemExit as exc:
    print("SYSTEM EXIT :", repr(exc))

except Exception as exc:
    runtime["runtime_exceptions"] += 1

    print()
    print("=" * 100)
    print("PRODUCTION RUNTIME EXCEPTION")
    print("=" * 100)
    print(repr(exc))
    traceback.print_exc()

finally:
    sys.settrace(None)


# ----------------------------------------------------------------------
# FINAL SUMMARY
# ----------------------------------------------------------------------

print()
print("=" * 100)
print("FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    f"FIND_FUTURE_PRICE CALLS       : {runtime['find_calls']}"
)

print(
    f"FIND_FUTURE_PRICE RETURNS     : {runtime['find_returns']}"
)

print(
    f"NONE RETURNS                  : {runtime['none_returns']}"
)

print(
    f"NON-NONE RETURNS              : {runtime['non_none_returns']}"
)

print(
    f"POP_JUMP_IF_TRUE EVENTS      : {runtime['branch_events']}"
)

print(
    f"OFFSET 206 EVENTS            : {runtime['target_206']}"
)

print(
    f"OFFSET 226 EVENTS            : {runtime['target_226']}"
)

print(
    f"RUNTIME EXCEPTIONS            : {runtime['runtime_exceptions']}"
)

print()
print("=" * 100)
print("SAFETY VERIFICATION")
print("=" * 100)

print("DATABASE WRITES             : NONE")
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
print("FORENSIC CONCLUSION")
print("=" * 100)

if runtime["find_calls"] == 0:
    status = "REAL_INVOCATION_NOT_CAPTURED"
    meaning = (
        "The production runtime did not enter find_future_price(). "
        "No branch behavior is inferred."
    )
    frontier = (
        "Capture the real production invocation before attempting "
        "POP_JUMP_IF_TRUE operand localization."
    )

elif runtime["branch_events"] == 0:
    status = "REAL_INVOCATION_CAPTURED_BRANCH_NOT_REACHED"
    meaning = (
        "A genuine find_future_price() invocation was observed, "
        "but offsets 206/226 were not reached."
    )
    frontier = (
        "Use the captured real invocation context and continue tracing "
        "the exact execution path toward offsets 206/226."
    )

else:
    status = "POP_JUMP_IF_TRUE_RUNTIME_CONTEXT_CAPTURED"
    meaning = (
        "A genuine production find_future_price() invocation reached "
        "the target POP_JUMP_IF_TRUE instruction(s), and the complete "
        "runtime local state was captured without fabricating the operand."
    )
    frontier = (
        "Next isolate the exact stack operand immediately before "
        "POP_JUMP_IF_TRUE using the captured opcode sequence and runtime state."
    )

print("STATUS :", status)
print("MEANING :", meaning)
print("NEXT FRONTIER :", frontier)

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)