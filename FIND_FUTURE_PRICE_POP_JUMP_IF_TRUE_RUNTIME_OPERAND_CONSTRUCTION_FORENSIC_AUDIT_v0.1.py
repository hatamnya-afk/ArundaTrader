# ARUNDA FORENSIC AUDIT
# FIND_FUTURE_PRICE_POP_JUMP_IF_TRUE_RUNTIME_OPERAND_CONSTRUCTION_FORENSIC_AUDIT_v0.1.py

import os
import sys
import dis
import sqlite3
import runpy
import types
import traceback
import inspect
from collections import deque


TARGET_FILE = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DATABASE_FILE = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_FUNCTION = "find_future_price"

TARGET_OFFSETS = {
    206,
    226,
}

WINDOW_BEFORE = 36
WINDOW_AFTER = 4


# ============================================================================
# GLOBAL FORENSIC STATE
# ============================================================================

STATE = {
    "find_calls": 0,
    "find_returns": 0,
    "none_returns": 0,
    "non_none_returns": 0,
    "target_events": 0,
    "offset_206": 0,
    "offset_226": 0,
    "runtime_exceptions": 0,
    "blocked_writes": 0,
    "opcode_events": 0,
    "operand_windows": 0,
    "captured_frames": 0,
}


# ============================================================================
# SAFE REPRESENTATION
# ============================================================================

def safe_repr(value, limit=700):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def value_info(value):
    return (
        f"TYPE={type(value).__name__} "
        f"ID={id(value)} "
        f"VALUE={safe_repr(value)}"
    )


# ============================================================================
# READ-ONLY SQLITE GUARD
# ============================================================================

_real_sqlite_connect = sqlite3.connect


def forensic_connect(*args, **kwargs):

    database = None

    if len(args) > 0:
        database = args[0]
    else:
        database = kwargs.get("database")

    if isinstance(database, str):

        absolute_path = os.path.abspath(database)

        if absolute_path.lower().endswith(".db"):

            uri = (
                "file:"
                + absolute_path.replace("\\", "/")
                + "?mode=ro"
            )

            args = (uri,) + tuple(args[1:])
            kwargs["uri"] = True

    connection = _real_sqlite_connect(*args, **kwargs)

    original_execute = connection.execute
    original_executemany = connection.executemany
    original_executescript = connection.executescript
    original_commit = connection.commit

    def guarded_execute(sql, *execute_args, **execute_kwargs):

        sql_text = str(sql).strip().upper()

        forbidden = (
            "INSERT",
            "UPDATE",
            "DELETE",
            "ALTER",
            "CREATE",
            "DROP",
            "REPLACE",
            "VACUUM",
        )

        if any(sql_text.startswith(x) for x in forbidden):

            STATE["blocked_writes"] += 1

            print()
            print("=" * 100)
            print("BLOCKED DATABASE WRITE")
            print("=" * 100)
            print(sql_text[:500])

            raise RuntimeError(
                "ARUNDA_FORENSIC_DATABASE_WRITE_BLOCKED"
            )

        if sql_text == "COMMIT":

            STATE["blocked_writes"] += 1

            print()
            print("BLOCKED COMMIT")

            raise RuntimeError(
                "ARUNDA_FORENSIC_DATABASE_COMMIT_BLOCKED"
            )

        return original_execute(
            sql,
            *execute_args,
            **execute_kwargs
        )

    def guarded_executemany(sql, *execute_args, **execute_kwargs):

        STATE["blocked_writes"] += 1

        print()
        print("BLOCKED EXECUTEMANY")

        raise RuntimeError(
            "ARUNDA_FORENSIC_EXECUTEMANY_BLOCKED"
        )

    def guarded_executescript(
        sql,
        *execute_args,
        **execute_kwargs
    ):

        STATE["blocked_writes"] += 1

        print()
        print("BLOCKED EXECUTESCRIPT")

        raise RuntimeError(
            "ARUNDA_FORENSIC_EXECUTESCRIPT_BLOCKED"
        )

    def guarded_commit(*commit_args, **commit_kwargs):

        STATE["blocked_writes"] += 1

        print()
        print("BLOCKED COMMIT")

        raise RuntimeError(
            "ARUNDA_FORENSIC_COMMIT_BLOCKED"
        )

    try:
        connection.execute = guarded_execute
        connection.executemany = guarded_executemany
        connection.executescript = guarded_executescript
        connection.commit = guarded_commit
    except Exception:
        pass

    return connection


# ============================================================================
# LOAD SOURCE
# ============================================================================

if not os.path.exists(TARGET_FILE):
    raise FileNotFoundError(TARGET_FILE)


with open(
    TARGET_FILE,
    "r",
    encoding="utf-8"
) as source_handle:

    SOURCE_TEXT = source_handle.read()


COMPILED = compile(
    SOURCE_TEXT,
    TARGET_FILE,
    "exec"
)


# ============================================================================
# STATIC FUNCTION RESOLUTION
# ============================================================================

STATIC_NAMESPACE = {
    "__name__": "__arunda_forensic_static__",
    "__file__": TARGET_FILE,
    "__package__": None,
}


try:

    exec(
        COMPILED,
        STATIC_NAMESPACE,
        STATIC_NAMESPACE
    )

except SystemExit:
    pass

except Exception as exc:

    print()
    print("=" * 100)
    print("STATIC LOAD EXCEPTION")
    print("=" * 100)
    print(repr(exc))


FIND_FUNCTION = STATIC_NAMESPACE.get(
    TARGET_FUNCTION
)


if not isinstance(
    FIND_FUNCTION,
    types.FunctionType
):

    raise RuntimeError(
        "find_future_price function could not be resolved"
    )


CODE = FIND_FUNCTION.__code__


INSTRUCTIONS = list(
    dis.get_instructions(CODE)
)


INSTRUCTION_BY_OFFSET = {
    instruction.offset: instruction
    for instruction in INSTRUCTIONS
}


TARGET_INSTRUCTIONS = {
    offset: INSTRUCTION_BY_OFFSET.get(offset)
    for offset in TARGET_OFFSETS
}


# ============================================================================
# STATIC REPORT
# ============================================================================

print("=" * 100)
print(
    "ARUNDA FIND_FUTURE_PRICE POP_JUMP_IF_TRUE "
    "RUNTIME OPERAND CONSTRUCTION FORENSIC AUDIT v0.1"
)
print("=" * 100)

print("TARGET :", TARGET_FILE)
print("DATABASE :", DATABASE_FILE)
print("MODE : READ-ONLY REAL-RUNTIME FORENSICS")
print("PRODUCTION SOURCE : UNMODIFIED")
print("DATABASE WRITES : BLOCKED")

print()
print("=" * 100)
print("STEP 1 — TARGET FUNCTION")
print("=" * 100)

print("FUNCTION :", CODE.co_name)
print("FILE     :", CODE.co_filename)
print("LINE     :", CODE.co_firstlineno)

try:
    print(
        "SIGNATURE :",
        inspect.signature(FIND_FUNCTION)
    )
except Exception:
    print(
        "SIGNATURE : <unavailable>"
    )


print()
print("=" * 100)
print("STEP 2 — TARGET POP_JUMP_IF_TRUE")
print("=" * 100)

for offset in sorted(TARGET_OFFSETS):

    instruction = TARGET_INSTRUCTIONS.get(offset)

    if instruction is None:

        print(
            f"OFFSET={offset} NOT FOUND"
        )

    else:

        print(
            f"OFFSET={instruction.offset:>4} "
            f"LINE={str(instruction.starts_line):<5} "
            f"OP={instruction.opname:<24} "
            f"ARG={instruction.arg!s:<5} "
            f"ARGVAL={instruction.argval!s}"
        )


# ============================================================================
# PRECEDING OPCODE WINDOW
# ============================================================================

def static_window(target_offset):

    lower = max(
        0,
        target_offset - WINDOW_BEFORE
    )

    upper = target_offset + WINDOW_AFTER

    return [
        instruction
        for instruction in INSTRUCTIONS
        if lower <= instruction.offset <= upper
    ]


print()
print("=" * 100)
print("STEP 3 — STATIC OPERAND-CONSTRUCTION WINDOWS")
print("=" * 100)

for target_offset in sorted(TARGET_OFFSETS):

    print()
    print(
        f"TARGET OFFSET : {target_offset}"
    )

    for instruction in static_window(
        target_offset
    ):

        print(
            f"{instruction.offset:>4} "
            f"{str(instruction.starts_line):>5} "
            f"{instruction.opname:<28} "
            f"ARG={str(instruction.arg):<5} "
            f"ARGVAL={instruction.argval!s}"
        )


# ============================================================================
# RUNTIME FRAME SNAPSHOT
# ============================================================================

def snapshot_locals(frame):

    snapshot = {}

    try:

        local_items = list(
            frame.f_locals.items()
        )

    except Exception:

        return snapshot

    for name, value in local_items:

        snapshot[name] = {
            "type": type(value).__name__,
            "id": id(value),
            "repr": safe_repr(value),
        }

    return snapshot


def print_selected_locals(frame):

    selected = (
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
    )

    for name in selected:

        if name in frame.f_locals:

            value = frame.f_locals[name]

            print(
                f"{name:<18} | "
                f"TYPE={type(value).__name__:<16} | "
                f"ID={id(value)} | "
                f"VALUE={safe_repr(value, 500)}"
            )


# ============================================================================
# OPCODE STATE
# ============================================================================

FRAME_STATE = {}


def get_frame_state(frame):

    frame_id = id(frame)

    if frame_id not in FRAME_STATE:

        FRAME_STATE[frame_id] = {
            "recent": deque(
                maxlen=64
            ),
            "target_windows": [],
            "last_target": None,
        }

    return FRAME_STATE[frame_id]


# ============================================================================
# STATIC STACK EFFECT KNOWLEDGE
# ============================================================================

STACK_EFFECT_NOTES = {

    "LOAD_FAST":
        "pushes local value",

    "LOAD_CONST":
        "pushes constant",

    "LOAD_GLOBAL":
        "pushes global/builtin reference",

    "LOAD_ATTR":
        "replaces object with attribute value",

    "LOAD_METHOD":
        "prepares method call",

    "LOAD_DEREF":
        "pushes closure value",

    "LOAD_NAME":
        "pushes name value",

    "COMPARE_OP":
        "consumes two operands and pushes comparison result",

    "IS_OP":
        "consumes two operands and pushes identity-test result",

    "CONTAINS_OP":
        "consumes two operands and pushes containment-test result",

    "UNARY_NOT":
        "consumes one operand and pushes boolean inversion",

    "POP_JUMP_IF_TRUE":
        "consumes condition and branches if truthy",

    "POP_JUMP_IF_FALSE":
        "consumes condition and branches if falsy",

    "JUMP_IF_TRUE_OR_POP":
        "tests top-of-stack",

    "JUMP_IF_FALSE_OR_POP":
        "tests top-of-stack",

    "BUILD_TUPLE":
        "packs N stack values into tuple",

    "BUILD_LIST":
        "packs N stack values into list",

    "BUILD_SET":
        "packs N stack values into set",

    "BUILD_MAP":
        "builds mapping from stack operands",

    "BUILD_CONST_KEY_MAP":
        "builds mapping from stack values and constant keys",

    "KW_NAMES":
        "sets keyword-name tuple for following call",

    "PRECALL":
        "prepares call",

    "CALL":
        "consumes callable and arguments",

    "RETURN_VALUE":
        "returns top stack value",
}


def stack_note(instruction):

    return STACK_EFFECT_NOTES.get(
        instruction.opname,
        ""
    )


# ============================================================================
# IMPORTANT:
# CPYTHON FRAME API DOES NOT EXPOSE EVALUATION STACK
# ============================================================================

def print_runtime_operand_boundary(
    frame,
    target_offset
):

    instruction = INSTRUCTION_BY_OFFSET.get(
        target_offset
    )

    if instruction is None:
        return

    state = get_frame_state(frame)

    print()
    print("=" * 100)
    print("RUNTIME POP_JUMP_IF_TRUE OPERAND CONSTRUCTION")
    print("=" * 100)

    print(
        "TARGET OFFSET :",
        target_offset
    )

    print(
        "TARGET OPCODE :",
        instruction.opname
    )

    print(
        "TARGET ARG    :",
        instruction.arg
    )

    print(
        "TARGET ARGVAL :",
        instruction.argval
    )

    print()
    print("RUNTIME LOCALS AT TARGET")
    print("-" * 100)

    print_selected_locals(frame)

    print()
    print("RECENT RUNTIME OPCODE WINDOW")
    print("-" * 100)

    for item in state["recent"]:

        print(
            f"OFFSET={item['offset']:>4} "
            f"OP={item['opname']:<28} "
            f"ARG={str(item['arg']):<5} "
            f"ARGVAL={item['argval']!s:<25} "
            f"LINE={str(item['line']):<5}"
        )

    print()
    print("STATIC STACK-EFFECT INTERPRETATION")
    print("-" * 100)

    for item in state["recent"]:

        note = STACK_EFFECT_NOTES.get(
            item["opname"],
            ""
        )

        if note:

            print(
                f"OFFSET={item['offset']:>4} "
                f"{item['opname']:<28} "
                f"-> {note}"
            )

    print()
    print("LOCAL VALUE CORRELATION")
    print("-" * 100)

    for name in (
        "price",
        "best_price",
        "best_distance",
        "distance",
        "row_epoch",
        "target_epoch",
        "row",
        "rows",
    ):

        if name in frame.f_locals:

            value = frame.f_locals[name]

            print(
                f"{name:<18} | "
                f"TYPE={type(value).__name__:<16} | "
                f"ID={id(value)} | "
                f"VALUE={safe_repr(value, 600)}"
            )

    print()
    print("STACK EVIDENCE STATUS")
    print("-" * 100)

    print(
        "DIRECT EVALUATION STACK : UNAVAILABLE THROUGH CPYTHON FRAME API"
    )

    print(
        "INFERRED STACK VALUE     : NOT ASSUMED"
    )

    print(
        "RUNTIME LOCALS           : CAPTURED"
    )

    print(
        "BYTECODE ORDER           : CAPTURED"
    )


# ============================================================================
# RUNTIME TRACE
# ============================================================================

def runtime_trace(
    frame,
    event,
    arg
):

    try:

        filename = os.path.abspath(
            frame.f_code.co_filename
        )

        if filename != os.path.abspath(
            TARGET_FILE
        ):

            return runtime_trace

        if frame.f_code.co_name != TARGET_FUNCTION:

            return runtime_trace

        state = get_frame_state(frame)

        if event == "call":

            STATE["find_calls"] += 1
            STATE["captured_frames"] += 1

            frame.f_trace_opcodes = True

            print()
            print("=" * 100)
            print(
                f"FIND_FUTURE_PRICE REAL CALL "
                f"#{STATE['find_calls']}"
            )
            print("=" * 100)

            print_selected_locals(frame)

            print()
            print("ACTUAL ARGUMENTS")
            print("-" * 100)

            try:

                arguments = inspect.getargvalues(
                    frame
                )

                for name in arguments.args:

                    value = frame.f_locals.get(
                        name
                    )

                    print(
                        f"{name:<20} | "
                        f"TYPE={type(value).__name__:<16} | "
                        f"ID={id(value)} | "
                        f"VALUE={safe_repr(value, 700)}"
                    )

            except Exception as exc:

                print(
                    "ARGUMENT CAPTURE ERROR :",
                    repr(exc)
                )

            return runtime_trace

        if event == "opcode":

            STATE["opcode_events"] += 1

            offset = frame.f_lasti

            instruction = INSTRUCTION_BY_OFFSET.get(
                offset
            )

            if instruction is None:

                return runtime_trace

            state["recent"].append(
                {
                    "offset": offset,
                    "opname": instruction.opname,
                    "arg": instruction.arg,
                    "argval": instruction.argval,
                    "line": instruction.starts_line,
                }
            )

            if offset in TARGET_OFFSETS:

                STATE["target_events"] += 1
                STATE["operand_windows"] += 1

                if offset == 206:
                    STATE["offset_206"] += 1

                if offset == 226:
                    STATE["offset_226"] += 1

                print_runtime_operand_boundary(
                    frame,
                    offset
                )

                state["target_windows"].append(
                    {
                        "offset": offset,
                        "locals": snapshot_locals(
                            frame
                        ),
                    }
                )

                state["last_target"] = offset

            return runtime_trace

        if event == "return":

            STATE["find_returns"] += 1

            if arg is None:

                STATE["none_returns"] += 1

            else:

                STATE["non_none_returns"] += 1

            print()
            print("=" * 100)
            print(
                f"FIND_FUTURE_PRICE RETURN "
                f"#{STATE['find_returns']}"
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
                safe_repr(arg, 700)
            )

            print()
            print("RETURN LOCALS")
            print("-" * 100)

            print_selected_locals(frame)

            return runtime_trace

    except Exception as exc:

        STATE["runtime_exceptions"] += 1

        print()
        print(
            "TRACE EXCEPTION :",
            repr(exc)
        )

    return runtime_trace


# ============================================================================
# PRODUCTION EXECUTION
# ============================================================================

print()
print("=" * 100)
print("STEP 4 — REAL PRODUCTION RUNTIME")
print("=" * 100)

original_connect = sqlite3.connect

sqlite3.connect = forensic_connect

try:

    sys.settrace(runtime_trace)

    runpy.run_path(
        TARGET_FILE,
        run_name="__main__"
    )

except SystemExit as exc:

    print()
    print(
        "PRODUCTION SYSTEM EXIT :",
        repr(exc)
    )

except Exception as exc:

    STATE["runtime_exceptions"] += 1

    print()
    print("=" * 100)
    print("PRODUCTION RUNTIME EXCEPTION")
    print("=" * 100)

    print(
        repr(exc)
    )

    traceback.print_exc()

finally:

    sys.settrace(None)

    sqlite3.connect = original_connect


# ============================================================================
# FINAL SUMMARY
# ============================================================================

print()
print("=" * 100)
print("STEP 5 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    f"FIND_FUTURE_PRICE CALLS       : "
    f"{STATE['find_calls']}"
)

print(
    f"FIND_FUTURE_PRICE RETURNS     : "
    f"{STATE['find_returns']}"
)

print(
    f"NONE RETURNS                  : "
    f"{STATE['none_returns']}"
)

print(
    f"NON-NONE RETURNS              : "
    f"{STATE['non_none_returns']}"
)

print(
    f"TARGET BRANCH EVENTS         : "
    f"{STATE['target_events']}"
)

print(
    f"OFFSET 206 EVENTS            : "
    f"{STATE['offset_206']}"
)

print(
    f"OFFSET 226 EVENTS            : "
    f"{STATE['offset_226']}"
)

print(
    f"OPCODE EVENTS                : "
    f"{STATE['opcode_events']}"
)

print(
    f"OPERAND WINDOWS              : "
    f"{STATE['operand_windows']}"
)

print(
    f"RUNTIME EXCEPTIONS           : "
    f"{STATE['runtime_exceptions']}"
)


# ============================================================================
# SAFETY
# ============================================================================

print()
print("=" * 100)
print("STEP 6 — SAFETY VERIFICATION")
print("=" * 100)

print(
    "DATABASE WRITES             : NONE"
)

print(
    f"BLOCKED WRITE ATTEMPTS      : "
    f"{STATE['blocked_writes']}"
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
    "PRODUCTION SOURCE MODIFIED : NONE"
)

print(
    "PRODUCTION FORMULA MODIFIED: NONE"
)

print(
    "PRODUCTION MAIN MODIFIED   : NONE"
)


# ============================================================================
# FORENSIC CONCLUSION
# ============================================================================

print()
print("=" * 100)
print("FINAL FORENSIC CONCLUSION")
print("=" * 100)


if STATE["find_calls"] == 0:

    status = (
        "FIND_FUTURE_PRICE_RUNTIME_NOT_REACHED"
    )

    meaning = (
        "No genuine production invocation of "
        "find_future_price() was captured."
    )

    frontier = (
        "Reproduce the real production invocation "
        "before continuing operand localization."
    )

elif STATE["target_events"] == 0:

    status = (
        "POP_JUMP_IF_TRUE_RUNTIME_OPERAND_NOT_REACHED"
    )

    meaning = (
        "Real find_future_price() invocations were captured, "
        "but target POP_JUMP_IF_TRUE offsets were not reached."
    )

    frontier = (
        "Continue tracing the real invocation toward "
        "offset 206/226."
    )

else:

    status = (
        "POP_JUMP_IF_TRUE_RUNTIME_OPERAND_CONSTRUCTION_CAPTURED"
    )

    meaning = (
        "The target POP_JUMP_IF_TRUE instruction was reached "
        "during genuine production execution. The complete "
        "preceding opcode window and runtime local state were "
        "captured without fabricating the evaluation-stack operand."
    )

    frontier = (
        "Compare the captured LOAD/COMPARE/IS/BUILD sequence "
        "immediately preceding offset 206 and identify the exact "
        "runtime operand construction. Do not infer an operand "
        "value that is not directly supported by runtime evidence."
    )


print(
    "STATUS :",
    status
)

print(
    "MEANING :",
    meaning
)

print(
    "NEXT FRONTIER :",
    frontier
)

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)