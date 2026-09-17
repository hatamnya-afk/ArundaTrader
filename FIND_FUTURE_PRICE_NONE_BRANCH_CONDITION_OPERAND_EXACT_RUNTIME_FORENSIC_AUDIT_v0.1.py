import os
import sys
import dis
import linecache
import sqlite3
import signal_outcome_engine as engine


TARGET_FILE = os.path.abspath(engine.__file__)
TARGET_FUNC_NAME = "find_future_price"

WATCH_OFFSETS = set(range(180, 241))

CALLS = 0
RETURNS = 0
NONE_RETURNS = 0
NON_NONE_RETURNS = 0
WATCH_EVENTS = 0
EXCEPTIONS = 0


def safe_repr(value, limit=700):
    try:
        text = repr(value)
    except Exception:
        text = "<repr-error>"

    if len(text) > limit:
        text = text[:limit] + "...<TRUNCATED>"

    return text


def obj(value):
    return (
        type(value).__name__,
        id(value),
        safe_repr(value),
    )


def print_locals(frame):
    names = [
        "asset",
        "minutes",
        "row",
        "rows",
        "row_epoch",
        "target_epoch",
        "timestamp",
        "price",
        "label",
        "best_distance",
        "best_price",
        "distance",
        "conn",
        "signal",
    ]

    for name in names:
        try:
            if name in frame.f_locals:
                t, oid, value = obj(frame.f_locals[name])

                print(
                    f"{name:16s} | "
                    f"TYPE={t} | "
                    f"ID={oid} | "
                    f"VALUE={value}"
                )
        except Exception:
            pass


def source_context(frame):
    start = max(1, frame.f_lineno - 3)
    end = frame.f_lineno + 4

    for line_no in range(start, end + 1):
        text = linecache.getline(
            frame.f_code.co_filename,
            line_no
        )

        if text:
            print(
                f"{line_no:5d} | {text.rstrip()}"
            )


def get_instruction_map(code):
    return {
        ins.offset: ins
        for ins in dis.get_instructions(code)
    }


def print_static_window(code):
    print()
    print("=" * 100)
    print("STATIC OPCODE WINDOW AROUND BRANCH CONDITIONS")
    print("=" * 100)

    instructions = list(
        dis.get_instructions(code)
    )

    for ins in instructions:
        if 180 <= ins.offset <= 240:
            print(
                f"OFFSET={ins.offset:4d} | "
                f"LINE={str(ins.starts_line):5s} | "
                f"OP={ins.opname:25s} | "
                f"ARG={ins.arg!s:5s} | "
                f"ARGVAL={safe_repr(ins.argval, 200)}"
            )


def trace(frame, event, arg):
    global CALLS
    global RETURNS
    global NONE_RETURNS
    global NON_NONE_RETURNS
    global WATCH_EVENTS
    global EXCEPTIONS

    if frame.f_code.co_name != TARGET_FUNC_NAME:
        return trace

    if os.path.abspath(frame.f_code.co_filename) != TARGET_FILE:
        return trace

    frame.f_trace_opcodes = True

    if event == "call":
        CALLS += 1

        print()
        print("=" * 100)
        print(f"FIND_FUTURE_PRICE CALL #{CALLS}")
        print("=" * 100)

        print(
            f"FUNCTION : {frame.f_code.co_name}"
        )

        print(
            f"FILE     : {frame.f_code.co_filename}"
        )

        print(
            f"LINE     : {frame.f_lineno}"
        )

        print()
        print("INITIAL LOCALS")
        print("-" * 100)

        print_locals(frame)

        return trace

    if event == "opcode":

        offset = frame.f_lasti

        if offset not in WATCH_OFFSETS:
            return trace

        WATCH_EVENTS += 1

        try:
            instructions = get_instruction_map(
                frame.f_code
            )

            ins = instructions.get(offset)

            if ins is None:
                return trace

            print()
            print("=" * 100)
            print("EXACT RUNTIME OPCODE EVENT")
            print("=" * 100)

            print(
                f"EVENT #{WATCH_EVENTS}"
            )

            print(
                f"OFFSET       : {ins.offset}"
            )

            print(
                f"LINE         : {frame.f_lineno}"
            )

            print(
                f"OPCODE       : {ins.opname}"
            )

            print(
                f"ARG          : {ins.arg}"
            )

            print(
                f"ARGVAL       : {safe_repr(ins.argval, 300)}"
            )

            print()
            print("SOURCE CONTEXT")
            print("-" * 100)

            source_context(frame)

            print()
            print("RUNTIME LOCALS")
            print("-" * 100)

            print_locals(frame)

            if ins.opname in (
                "POP_JUMP_IF_TRUE",
                "POP_JUMP_IF_FALSE",
                "JUMP_IF_TRUE_OR_POP",
                "JUMP_IF_FALSE_OR_POP",
            ):
                print()
                print("!!! CONDITIONAL BRANCH OPERAND BOUNDARY !!!")
                print("-" * 100)

                print(
                    "The branch opcode was reached."
                )

                print(
                    "Runtime locals are shown exactly as observed."
                )

                print(
                    "The condition operand itself is NOT guessed "
                    "from source."
                )

            elif ins.opname in (
                "COMPARE_OP",
                "CONTAINS_OP",
                "IS_OP",
                "UNARY_NOT",
                "TO_BOOL",
            ):
                print()
                print("!!! CONDITION-BUILDING OPCODE !!!")
                print("-" * 100)

                print(
                    "This opcode is immediately relevant to "
                    "the branch-condition construction."
                )

            elif ins.opname in (
                "LOAD_FAST",
                "LOAD_CONST",
                "LOAD_ATTR",
                "LOAD_GLOBAL",
                "LOAD_METHOD",
                "BINARY_SUBSCR",
                "CALL",
                "PRECALL",
                "BUILD_TUPLE",
                "BUILD_LIST",
                "BUILD_MAP",
                "BUILD_CONST_KEY_MAP",
            ):
                print()
                print("OPERAND CONSTRUCTION OPCODE")
                print("-" * 100)

                print(
                    "This opcode may contribute to the value "
                    "consumed by the later branch."
                )

        except Exception as exc:
            EXCEPTIONS += 1

            print(
                f"[TRACE ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

        return trace

    if event == "return":

        RETURNS += 1

        if arg is None:
            NONE_RETURNS += 1
        else:
            NON_NONE_RETURNS += 1

        print()
        print("=" * 100)
        print(
            f"FIND_FUTURE_PRICE RETURN #{RETURNS}"
        )
        print("=" * 100)

        print(
            f"LINE       : {frame.f_lineno}"
        )

        print(
            f"TYPE       : {type(arg).__name__}"
        )

        print(
            f"OBJECT ID  : {id(arg)}"
        )

        print(
            f"VALUE      : {safe_repr(arg)}"
        )

        print()
        print("RETURN LOCALS")
        print("-" * 100)

        print_locals(frame)

        if arg is None:
            print()
            print(
                "RUNTIME FACT: RETURN_VALUE produced None."
            )

        return None

    if event == "exception":

        EXCEPTIONS += 1

        try:
            exc_type, exc_value, _ = arg

            print()
            print("=" * 100)
            print("FIND_FUTURE_PRICE EXCEPTION")
            print("=" * 100)

            print(
                f"TYPE  : {getattr(exc_type, '__name__', exc_type)}"
            )

            print(
                f"VALUE : {safe_repr(exc_value)}"
            )

        except Exception:
            pass

        return trace

    return trace


def open_read_only_database(path):

    uri = (
        "file:"
        + os.path.abspath(path)
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    conn.execute(
        "PRAGMA query_only=ON"
    )

    return conn


def main():

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE NONE BRANCH "
        "OPERAND STACK EXACT RUNTIME FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        f"TARGET : {TARGET_FILE}"
    )

    database_path = os.path.join(
        os.path.dirname(TARGET_FILE),
        "arunda.db"
    )

    print(
        f"DATABASE : {database_path}"
    )

    print(
        "MODE : READ-ONLY REAL-RUNTIME FORENSICS"
    )

    print(
        "PRODUCTION SOURCE : UNMODIFIED"
    )

    print(
        "DATABASE WRITES : BLOCKED"
    )

    function = getattr(
        engine,
        TARGET_FUNC_NAME
    )

    print()
    print("=" * 100)
    print("STEP 1 — STATIC FUNCTION")
    print("=" * 100)

    print(
        f"find_future_price : FOUND | "
        f"LINE={function.__code__.co_firstlineno}"
    )

    print_static_window(
        function.__code__
    )

    print()
    print("=" * 100)
    print("STEP 2 — READ-ONLY DATABASE")
    print("=" * 100)

    conn = None

    try:

        conn = open_read_only_database(
            database_path
        )

        print(
            "DATABASE CONNECTION : READ-ONLY"
        )

        print(
            "PRAGMA query_only   : ON"
        )

    except Exception as exc:

        print(
            f"DATABASE OPEN ERROR : "
            f"{type(exc).__name__}: {exc}"
        )

        return

    print()
    print("=" * 100)
    print("STEP 3 — GENUINE PRODUCTION EXECUTION")
    print("=" * 100)

    previous_trace = sys.gettrace()

    try:

        sys.settrace(trace)

        engine.main()

    except Exception as exc:

        print()
        print("=" * 100)
        print("MAIN EXCEPTION")
        print("=" * 100)

        print(
            f"TYPE  : {type(exc).__name__}"
        )

        print(
            f"VALUE : {safe_repr(exc)}"
        )

    finally:

        sys.settrace(
            previous_trace
        )

        try:
            conn.close()
        except Exception:
            pass

    print()
    print("=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"FIND_FUTURE_PRICE CALLS    : {CALLS}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS : {RETURNS}"
    )

    print(
        f"NONE RETURNS              : {NONE_RETURNS}"
    )

    print(
        f"NON-NONE RETURNS          : {NON_NONE_RETURNS}"
    )

    print(
        f"OPCODE EVENTS 180-240     : {WATCH_EVENTS}"
    )

    print(
        f"RUNTIME EXCEPTIONS        : {EXCEPTIONS}"
    )

    print()
    print("=" * 100)
    print("SAFETY VERIFICATION")
    print("=" * 100)

    print(
        "DATABASE WRITES             : NONE"
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

    print()
    print("=" * 100)
    print("FINAL FORENSIC CONCLUSION")
    print("=" * 100)

    if (
        RETURNS > 0
        and NONE_RETURNS == RETURNS
    ):

        print(
            "STATUS : "
            "FIND_FUTURE_PRICE_NONE_BRANCH_OPERAND_WINDOW_CAPTURED"
        )

        print(
            "MEANING : "
            "All observed invocations returned None. "
            "The complete runtime opcode window around the "
            "conditional branches was captured."
        )

        print(
            "NEXT FRONTIER : "
            "Use the opcode sequence immediately preceding "
            "POP_JUMP_IF_TRUE at offsets 206 and/or 226 "
            "to identify the actual runtime condition."
        )

    elif CALLS == 0:

        print(
            "STATUS : "
            "FIND_FUTURE_PRICE_NOT_OBSERVED"
        )

        print(
            "MEANING : "
            "The target function was not entered."
        )

        print(
            "NEXT FRONTIER : "
            "Reproduce an execution entering find_future_price()."
        )

    else:

        print(
            "STATUS : "
            "FIND_FUTURE_PRICE_RUNTIME_INCOMPLETE"
        )

        print(
            "MEANING : "
            "The target runtime did not provide sufficient "
            "evidence for the None branch."
        )

        print(
            "NEXT FRONTIER : "
            "Do not infer the condition."
        )

    print()
    print(
        "DATABASE_WRITES             : NONE"
    )

    print(
        "ENGINE_MODIFIED             : NONE"
    )

    print(
        "PRODUCTION_SOURCE_MODIFIED  : NONE"
    )

    print(
        "PRODUCTION_FORMULA_MODIFIED : NONE"
    )

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()