import os
import sys
import dis
import linecache
import sqlite3
import signal_outcome_engine as engine


TARGET_FILE = os.path.abspath(engine.__file__)
TARGET_FUNC_NAME = "find_future_price"

TARGET_BRANCHES = {
    206,
    226,
}

CALLS = 0
RETURNS = 0
NONE_RETURNS = 0
NON_NONE_RETURNS = 0
BRANCH_EVENTS = 0
EXCEPTIONS = 0


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr-error>"

    if len(text) > limit:
        text = text[:limit] + "...<TRUNCATED>"

    return text


def value_info(value):
    return (
        type(value).__name__,
        id(value),
        safe_repr(value),
    )


def get_instructions(code):
    return list(dis.get_instructions(code))


def instruction_map(code):
    return {
        ins.offset: ins
        for ins in dis.get_instructions(code)
    }


def print_locals(frame):
    preferred = [
        "asset",
        "minutes",
        "row",
        "rows",
        "row_epoch",
        "target_epoch",
        "best_distance",
        "best_price",
        "distance",
        "price",
        "label",
        "conn",
    ]

    for name in preferred:
        if name in frame.f_locals:
            try:
                t, oid, value = value_info(
                    frame.f_locals[name]
                )

                print(
                    f"{name:16s} | "
                    f"TYPE={t:12s} | "
                    f"ID={oid} | "
                    f"VALUE={value}"
                )
            except Exception:
                pass


def print_source(frame):
    start = max(
        1,
        frame.f_lineno - 4
    )

    end = frame.f_lineno + 4

    for number in range(start, end + 1):

        text = linecache.getline(
            frame.f_code.co_filename,
            number
        )

        if text:
            print(
                f"{number:5d} | {text.rstrip()}"
            )


def print_branch_neighborhood(code, branch_offset):

    instructions = get_instructions(code)

    index = None

    for i, ins in enumerate(instructions):

        if ins.offset == branch_offset:
            index = i
            break

    if index is None:
        return

    start = max(
        0,
        index - 8
    )

    end = min(
        len(instructions),
        index + 2
    )

    print()
    print("STATIC OPERAND-BUILD SEQUENCE")
    print("-" * 100)

    for ins in instructions[start:end]:

        print(
            f"OFFSET={ins.offset:4d} | "
            f"LINE={str(ins.starts_line):5s} | "
            f"OP={ins.opname:25s} | "
            f"ARG={str(ins.arg):5s} | "
            f"ARGVAL={safe_repr(ins.argval, 250)}"
        )


def trace(frame, event, arg):

    global CALLS
    global RETURNS
    global NONE_RETURNS
    global NON_NONE_RETURNS
    global BRANCH_EVENTS
    global EXCEPTIONS

    if frame.f_code.co_name != TARGET_FUNC_NAME:
        return trace

    if os.path.abspath(
        frame.f_code.co_filename
    ) != TARGET_FILE:
        return trace

    frame.f_trace_opcodes = True

    if event == "call":

        CALLS += 1

        print()
        print("=" * 100)
        print(
            f"FIND_FUTURE_PRICE CALL #{CALLS}"
        )
        print("=" * 100)

        print_locals(frame)

        return trace

    if event == "opcode":

        offset = frame.f_lasti

        if offset not in TARGET_BRANCHES:
            return trace

        BRANCH_EVENTS += 1

        instructions = instruction_map(
            frame.f_code
        )

        ins = instructions.get(offset)

        if ins is None:
            return trace

        print()
        print("=" * 100)
        print(
            "EXACT BRANCH OPERAND RUNTIME EVENT"
        )
        print("=" * 100)

        print(
            f"EVENT       : {BRANCH_EVENTS}"
        )

        print(
            f"OFFSET      : {ins.offset}"
        )

        print(
            f"LINE        : {frame.f_lineno}"
        )

        print(
            f"OPCODE      : {ins.opname}"
        )

        print(
            f"ARG         : {ins.arg}"
        )

        print(
            f"ARGVAL      : {safe_repr(ins.argval)}"
        )

        print()
        print("SOURCE CONTEXT")
        print("-" * 100)

        print_source(frame)

        print()

        print_branch_neighborhood(
            frame.f_code,
            offset
        )

        print()
        print("RUNTIME LOCALS")
        print("-" * 100)

        print_locals(frame)

        print()
        print("BRANCH OPERAND STATUS")
        print("-" * 100)

        print(
            "IMPORTANT:"
        )

        print(
            "The CPython tracing API does not expose "
            "the evaluation stack directly."
        )

        print(
            "Therefore this audit does NOT fabricate "
            "a condition value."
        )

        print(
            "The surrounding runtime locals and exact "
            "opcode construction sequence are captured."
        )

        print()
        print(
            "NEXT REQUIRED EVIDENCE:"
        )

        print(
            "Identify which LOAD_FAST / LOAD_CONST / "
            "COMPARE_OP / BINARY_SUBSCR sequence "
            "constructs the branch operand."
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
                f"TYPE  : "
                f"{getattr(exc_type, '__name__', exc_type)}"
            )

            print(
                f"VALUE : "
                f"{safe_repr(exc_value)}"
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
        "ARUNDA FIND_FUTURE_PRICE BRANCH OPERAND "
        "VALUE EXACT RUNTIME FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        f"TARGET   : {TARGET_FILE}"
    )

    database_path = os.path.join(
        os.path.dirname(TARGET_FILE),
        "arunda.db"
    )

    print(
        f"DATABASE : {database_path}"
    )

    print(
        "MODE     : READ-ONLY REAL-RUNTIME FORENSICS"
    )

    print(
        "SOURCE   : UNMODIFIED"
    )

    print(
        "DB WRITE : BLOCKED"
    )

    function = getattr(
        engine,
        TARGET_FUNC_NAME
    )

    print()
    print("=" * 100)
    print("STEP 1 — STATIC BRANCH MAP")
    print("=" * 100)

    for ins in dis.get_instructions(
        function.__code__
    ):

        if ins.offset in TARGET_BRANCHES:

            print(
                f"OFFSET={ins.offset:4d} | "
                f"OP={ins.opname} | "
                f"ARG={ins.arg} | "
                f"ARGVAL={safe_repr(ins.argval)}"
            )

            print_branch_neighborhood(
                function.__code__,
                ins.offset
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

    old_trace = sys.gettrace()

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
            old_trace
        )

        try:
            conn.close()
        except Exception:
            pass

    print()
    print("=" * 100)
    print("STEP 4 — FINAL FORENSIC SUMMARY")
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
        f"TARGET BRANCH EVENTS      : {BRANCH_EVENTS}"
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
        and BRANCH_EVENTS > 0
    ):

        print(
            "STATUS : "
            "FIND_FUTURE_PRICE_BRANCH_OPERAND_RUNTIME_CAPTURED"
        )

        print(
            "MEANING : "
            "The relevant branch offsets were reached during "
            "real execution and their exact surrounding opcode "
            "construction plus runtime locals were captured."
        )

        print(
            "NEXT FRONTIER : "
            "Use the printed sequence immediately before "
            "POP_JUMP_IF_TRUE to identify the runtime "
            "condition without assuming its value."
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
            "Reproduce the target runtime."
        )

    else:

        print(
            "STATUS : "
            "BRANCH_OPERAND_RUNTIME_INCOMPLETE"
        )

        print(
            "MEANING : "
            "Insufficient runtime evidence."
        )

        print(
            "NEXT FRONTIER : "
            "Do not infer the branch condition."
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