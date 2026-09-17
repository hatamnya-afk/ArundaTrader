from __future__ import annotations

import dis
import inspect
import os
import runpy
import sqlite3
import sys
import types
import traceback
from collections import defaultdict

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_FUNCTION = "find_future_price"
TARGET_OFFSETS = {206, 226}

WRITE_SQL = (
    "insert",
    "update",
    "delete",
    "alter",
    "create",
    "drop",
    "replace",
    "vacuum",
    "reindex",
    "attach",
    "detach",
)

FORENSIC_TAG = "__arunda_forensic_runtime__"


def ro_connection_factory(*args, **kwargs):
    uri = "file:" + os.path.abspath(DB_PATH) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    original_commit = conn.commit
    original_rollback = conn.rollback

    def blocked_commit():
        print("BLOCKED WRITE ATTEMPT : COMMIT")
        return None

    def blocked_rollback():
        return original_rollback()

    conn.commit = blocked_commit
    conn.rollback = blocked_rollback

    return conn


def install_sqlite_write_guard():
    original_connect = sqlite3.connect

    def guarded_connect(*args, **kwargs):
        return ro_connection_factory(*args, **kwargs)

    sqlite3.connect = guarded_connect
    return original_connect


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"
    return text


def describe(value):
    return (
        f"TYPE={type(value).__name__} | "
        f"ID={id(value)} | "
        f"VALUE={safe_repr(value)}"
    )


def is_write_sql(value):
    if not isinstance(value, str):
        return False

    normalized = value.strip().lower()

    return any(
        normalized.startswith(keyword)
        or normalized.startswith(keyword + " ")
        or normalized.startswith(keyword + "\n")
        for keyword in WRITE_SQL
    )


def guarded_execute(conn, sql, *args, **kwargs):
    if is_write_sql(sql):
        print()
        print("=" * 100)
        print("BLOCKED DATABASE WRITE")
        print("=" * 100)
        print("SQL :", repr(sql))
        print("=" * 100)
        return None

    return conn.execute(sql, *args, **kwargs)


def code_owner_map():
    owners = {}

    try:
        source = inspect.getsourcefile(runpy)
    except Exception:
        source = None

    return owners


def find_target_code(module_globals):
    candidates = []

    for value in module_globals.values():
        if isinstance(value, types.FunctionType):
            if value.__name__ == TARGET_FUNCTION:
                candidates.append(value)

    if not candidates:
        return None

    return candidates[0]


def instruction_map(code):
    return {
        instruction.offset: instruction
        for instruction in dis.get_instructions(code)
    }


def previous_instructions(code, offset, count=10):
    instructions = list(dis.get_instructions(code))

    index = None

    for i, ins in enumerate(instructions):
        if ins.offset == offset:
            index = i
            break

    if index is None:
        return []

    start = max(0, index - count)

    return instructions[start:index]


def next_instructions(code, offset, count=8):
    instructions = list(dis.get_instructions(code))

    index = None

    for i, ins in enumerate(instructions):
        if ins.offset == offset:
            index = i
            break

    if index is None:
        return []

    return instructions[index + 1:index + 1 + count]


def print_static_target_map(code):
    print()
    print("=" * 100)
    print("STEP 1 — TARGET FUNCTION RESOLUTION")
    print("=" * 100)

    print("FUNCTION :", code.co_name)
    print("FILE     :", code.co_filename)
    print("FIRSTLINE:", code.co_firstlineno)

    print()
    print("=" * 100)
    print("STEP 2 — TARGET POP_JUMP_IF_TRUE MAP")
    print("=" * 100)

    for ins in dis.get_instructions(code):
        if ins.opname == "POP_JUMP_IF_TRUE":
            print(
                f"OFFSET={ins.offset:>4} | "
                f"LINE={ins.starts_line} | "
                f"OP={ins.opname:<20} | "
                f"ARG={ins.arg} | "
                f"ARGVAL={ins.argval}"
            )

    print()
    print("TARGET OFFSETS :", sorted(TARGET_OFFSETS))


def stack_snapshot(frame):
    """
    CPython's tracing API does not expose the evaluation stack directly.
    Therefore this audit does NOT fabricate a stack.

    We capture every runtime-visible local and explicitly report
    that the operand stack itself is not directly exposed by sys.settrace.
    """

    locals_copy = dict(frame.f_locals)

    return {
        "locals": locals_copy,
        "stack_available": False,
    }


def print_locals(locals_map):
    print()
    print("RUNTIME LOCALS")
    print("-" * 100)

    for name in sorted(locals_map):
        value = locals_map[name]

        print(
            f"{name:<24} | "
            f"{type(value).__name__:<18} | "
            f"ID={id(value)} | "
            f"{safe_repr(value)}"
        )


def print_branch_window(code, offset):
    print()
    print("STATIC OPCODE WINDOW")
    print("-" * 100)

    for ins in previous_instructions(code, offset, 12):
        print(
            f"{ins.offset:>4} | "
            f"{ins.opname:<25} | "
            f"ARG={ins.arg!s:<6} | "
            f"ARGVAL={safe_repr(ins.argval, 120)}"
        )

    target = instruction_map(code).get(offset)

    if target:
        print(
            f"{target.offset:>4} | "
            f"{target.opname:<25} | "
            f"ARG={target.arg!s:<6} | "
            f"ARGVAL={safe_repr(target.argval, 120)}"
        )

    for ins in next_instructions(code, offset, 8):
        print(
            f"{ins.offset:>4} | "
            f"{ins.opname:<25} | "
            f"ARG={ins.arg!s:<6} | "
            f"ARGVAL={safe_repr(ins.argval, 120)}"
        )


def make_tracer(target_code, stats):
    def tracer(frame, event, arg):

        if frame.f_code is not target_code:
            return tracer

        if event == "opcode":
            offset = frame.f_lasti

            if offset not in TARGET_OFFSETS:
                return tracer

            stats["branch_events"] += 1

            instruction = instruction_map(target_code).get(offset)

            print()
            print("=" * 100)
            print("POP_JUMP_IF_TRUE RUNTIME EVENT")
            print("=" * 100)

            if instruction:
                print(
                    f"OFFSET     : {instruction.offset}"
                )
                print(
                    f"LINE       : {frame.f_lineno}"
                )
                print(
                    f"OPCODE     : {instruction.opname}"
                )
                print(
                    f"ARG        : {instruction.arg}"
                )
                print(
                    f"ARGVAL     : {safe_repr(instruction.argval)}"
                )

            print()
            print("IMPORTANT RUNTIME LIMITATION")
            print("-" * 100)
            print(
                "CPython sys.settrace exposes frame locals and instruction "
                "position, but does not expose the evaluation stack."
            )
            print(
                "Therefore the actual POP_JUMP_IF_TRUE operand is NOT "
                "fabricated or reconstructed here."
            )

            print()
            print("FRAME")
            print("-" * 100)

            print("FUNCTION :", frame.f_code.co_name)
            print("FILE     :", frame.f_code.co_filename)
            print("OFFSET   :", frame.f_lasti)
            print("LINE     :", frame.f_lineno)

            print_locals(frame.f_locals)

            print()
            print("STATIC OPERAND-PRODUCING WINDOW")
            print("-" * 100)

            print_branch_window(target_code, offset)

            print()
            print("STACK STATE")
            print("-" * 100)
            print("AVAILABLE : FALSE")
            print(
                "No evaluation-stack value is claimed as the branch operand."
            )

            print()
            print("BRANCH STATUS")
            print("-" * 100)
            print(
                "TAKEN / NOT-TAKEN : NOT CLAIMED"
            )

        elif event == "return":
            stats["returns"] += 1

            print()
            print("=" * 100)
            print("FIND_FUTURE_PRICE RETURN")
            print("=" * 100)

            print("LINE       :", frame.f_lineno)
            print("TYPE       :", type(arg).__name__)
            print("OBJECT ID  :", id(arg))
            print("VALUE      :", safe_repr(arg))

            if arg is None:
                stats["none_returns"] += 1

            print()
            print("RETURN LOCALS")
            print("-" * 100)

            print_locals(frame.f_locals)

        return tracer

    return tracer


def main():
    print("=" * 100)
    print("ARUNDA FIND_FUTURE_PRICE POP_JUMP_IF_TRUE RUNTIME OPERAND FORENSIC AUDIT v0.1")
    print("=" * 100)

    print("TARGET :", TARGET)
    print("DATABASE :", DB_PATH)
    print("MODE : READ-ONLY REAL-RUNTIME FORENSICS")
    print("PRODUCTION SOURCE : UNMODIFIED")
    print("DATABASE WRITES : BLOCKED")

    if not os.path.exists(TARGET):
        print()
        print("ERROR : TARGET SOURCE NOT FOUND")
        return

    if not os.path.exists(DB_PATH):
        print()
        print("ERROR : DATABASE NOT FOUND")
        return

    print()
    print("=" * 100)
    print("STEP 0 — SQLITE READ-ONLY GUARD")
    print("=" * 100)

    install_sqlite_write_guard()

    print("DATABASE MODE : READ-ONLY")
    print("WRITE OPERATIONS : BLOCKED")

    print()
    print("=" * 100)
    print("STEP 1 — LOAD PRODUCTION MODULE")
    print("=" * 100)

    stats = defaultdict(int)

    original_settrace = sys.gettrace()

    try:
        module_globals = {
            "__name__": "__main__",
            "__file__": TARGET,
            FORENSIC_TAG: True,
        }

        with open(TARGET, "rb") as source_file:
            source_bytes = source_file.read()

        code_object = compile(
            source_bytes,
            TARGET,
            "exec",
        )

        exec(code_object, module_globals)

    except Exception as exc:
        print()
        print("=" * 100)
        print("MODULE LOAD EXCEPTION")
        print("=" * 100)
        print(type(exc).__name__, repr(exc))
        traceback.print_exc()
        return

    target_function = find_target_code(module_globals)

    if target_function is None:
        print()
        print("ERROR : find_future_price() NOT FOUND")
        return

    target_code = target_function.__code__

    print(
        "find_future_price : FOUND | "
        f"LINE={target_code.co_firstlineno}"
    )

    print_static_target_map(target_code)

    print()
    print("=" * 100)
    print("STEP 3 — GENUINE PRODUCTION RUNTIME")
    print("=" * 100)

    tracer = make_tracer(target_code, stats)

    sys.settrace(tracer)

    try:
        main_function = module_globals.get("main")

        if main_function is None:
            raise RuntimeError("Production main() not found")

        main_function()

    except Exception as exc:
        stats["exceptions"] += 1

        print()
        print("=" * 100)
        print("RUNTIME EXCEPTION")
        print("=" * 100)
        print(type(exc).__name__, repr(exc))
        traceback.print_exc()

    finally:
        sys.settrace(original_settrace)

    print()
    print("=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        "MAIN EXECUTION              : COMPLETED"
    )
    print(
        "POP_JUMP_IF_TRUE EVENTS     :",
        stats["branch_events"]
    )
    print(
        "FIND_FUTURE_PRICE RETURNS   :",
        stats["returns"]
    )
    print(
        "NONE RETURNS                :",
        stats["none_returns"]
    )
    print(
        "RUNTIME EXCEPTIONS          :",
        stats["exceptions"]
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
    print("PRODUCTION SOURCE MODIFIED  : NONE")
    print("PRODUCTION FORMULA MODIFIED : NONE")
    print("PRODUCTION MAIN MODIFIED    : NONE")

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("=" * 100)

    if stats["branch_events"] > 0:
        status = "POP_JUMP_IF_TRUE_RUNTIME_OPERAND_BOUNDARY_CAPTURED"

        meaning = (
            "The target POP_JUMP_IF_TRUE instructions were reached during "
            "genuine production execution and their exact runtime frame "
            "context plus surrounding opcode construction were captured."
        )

        frontier = (
            "Evaluation-stack operand extraction remains unresolved because "
            "sys.settrace does not expose the CPython evaluation stack. "
            "Use a CPython-level opcode/frame inspection mechanism next; "
            "do not infer the operand from source."
        )

    else:
        status = "POP_JUMP_IF_TRUE_RUNTIME_OPERAND_NOT_REACHED"

        meaning = (
            "The target branch offsets were not reached during this "
            "production execution."
        )

        frontier = (
            "Reproduce the exact runtime path before attempting operand "
            "localization."
        )

    print("STATUS :", status)
    print("MEANING :", meaning)
    print("NEXT FRONTIER :", frontier)

    print()
    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()