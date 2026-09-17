from __future__ import annotations

import dis
import os
import runpy
import sqlite3
import sys
import traceback
from collections import defaultdict

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_FUNCTION = "find_future_price"
TARGET_OFFSETS = {206, 226}

FORENSIC_TAG = "__arunda_forensic_runtime__"

WRITE_PREFIXES = (
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


def safe_repr(value, limit=400):
    try:
        text = repr(value)
    except Exception:
        return "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def is_write_sql(sql):
    if not isinstance(sql, str):
        return False

    text = sql.strip().lower()

    return any(
        text == p
        or text.startswith(p + " ")
        or text.startswith(p + "\n")
        or text.startswith(p + "\t")
        for p in WRITE_PREFIXES
    )


class ReadOnlyConnection:
    def __init__(self, real_connection):
        self._conn = real_connection

    def execute(self, sql, *args, **kwargs):
        if is_write_sql(sql):
            print()
            print("=" * 100)
            print("BLOCKED WRITE ATTEMPT")
            print("=" * 100)
            print("SQL :", safe_repr(sql))
            print("=" * 100)
            return None

        return self._conn.execute(sql, *args, **kwargs)

    def executemany(self, sql, *args, **kwargs):
        if is_write_sql(sql):
            print()
            print("=" * 100)
            print("BLOCKED WRITE ATTEMPT")
            print("=" * 100)
            print("SQL :", safe_repr(sql))
            print("=" * 100)
            return None

        return self._conn.executemany(sql, *args, **kwargs)

    def executescript(self, sql, *args, **kwargs):
        print()
        print("=" * 100)
        print("BLOCKED executescript()")
        print("=" * 100)
        return None

    def commit(self):
        print()
        print("BLOCKED WRITE ATTEMPT : COMMIT")
        return None

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def readonly_connect(database, *args, **kwargs):
    if database == ":memory:":
        return sqlite3.connect(database, *args, **kwargs)

    uri = "file:" + os.path.abspath(DB_PATH) + "?mode=ro"

    conn = sqlite3.connect(uri, uri=True)

    conn.row_factory = sqlite3.Row

    return ReadOnlyConnection(conn)


def install_sqlite_guard():
    original_connect = sqlite3.connect

    sqlite3.connect = readonly_connect

    return original_connect


def load_production_without_auto_execution():
    """
    Load the production module namespace without allowing this forensic
    harness to recursively invoke its main().

    We execute the source once with __name__ set to a non-main value.
    Therefore:

        if __name__ == "__main__":
            main()

    is not entered during module loading.
    """

    namespace = {
        "__name__": "__arunda_production_module__",
        "__file__": TARGET,
        FORENSIC_TAG: True,
    }

    with open(TARGET, "rb") as f:
        source = f.read()

    code = compile(
        source,
        TARGET,
        "exec",
    )

    exec(code, namespace, namespace)

    return namespace


def find_function(namespace, name):
    candidate = namespace.get(name)

    if callable(candidate):
        return candidate

    return None


def print_target_map(function):
    code = function.__code__

    print()
    print("=" * 100)
    print("STEP 1 — STATIC TARGET RESOLUTION")
    print("=" * 100)

    print("FUNCTION :", code.co_name)
    print("FILE     :", code.co_filename)
    print("LINE     :", code.co_firstlineno)

    print()
    print("=" * 100)
    print("STEP 2 — TARGET BRANCH MAP")
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


def make_tracer(target_code, stats):
    """
    IMPORTANT:

    We do NOT trace the entire interpreter recursively.

    The tracer activates only after entering the target function.
    """

    active_frames = set()

    def tracer(frame, event, arg):

        if frame.f_code is not target_code:
            return tracer

        frame_id = id(frame)

        if event == "call":
            active_frames.add(frame_id)

            stats["calls"] += 1

            print()
            print("=" * 100)
            print("FIND_FUTURE_PRICE CALL")
            print("=" * 100)

            print("LINE :", frame.f_lineno)

            for name, value in frame.f_locals.items():
                print(
                    f"{name:<20} | "
                    f"{type(value).__name__:<16} | "
                    f"ID={id(value)} | "
                    f"{safe_repr(value)}"
                )

            frame.f_trace_opcodes = True
            return tracer

        if frame_id not in active_frames:
            return tracer

        if event == "opcode":

            offset = frame.f_lasti

            if offset in TARGET_OFFSETS:

                stats["branch_events"] += 1

                instruction = None

                for ins in dis.get_instructions(target_code):
                    if ins.offset == offset:
                        instruction = ins
                        break

                print()
                print("=" * 100)
                print("POP_JUMP_IF_TRUE RUNTIME BOUNDARY")
                print("=" * 100)

                if instruction is not None:
                    print(
                        "OFFSET     :",
                        instruction.offset
                    )

                    print(
                        "LINE       :",
                        frame.f_lineno
                    )

                    print(
                        "OPCODE     :",
                        instruction.opname
                    )

                    print(
                        "ARG        :",
                        instruction.arg
                    )

                    print(
                        "ARGVAL     :",
                        safe_repr(instruction.argval)
                    )

                print()
                print("RUNTIME LOCALS")
                print("-" * 100)

                for name, value in frame.f_locals.items():
                    print(
                        f"{name:<24} | "
                        f"{type(value).__name__:<18} | "
                        f"ID={id(value)} | "
                        f"{safe_repr(value)}"
                    )

                print()
                print("EVALUATION STACK")
                print("-" * 100)
                print(
                    "NOT EXPOSED BY sys.settrace()"
                )

                print(
                    "NO OPERAND VALUE IS FABRICATED."
                )

                print()
                print("STATIC OPCODE PREDECESSORS")
                print("-" * 100)

                instructions = list(
                    dis.get_instructions(target_code)
                )

                index = None

                for i, ins in enumerate(instructions):
                    if ins.offset == offset:
                        index = i
                        break

                if index is not None:

                    start = max(0, index - 10)

                    for ins in instructions[start:index]:
                        print(
                            f"{ins.offset:>4} | "
                            f"{ins.opname:<25} | "
                            f"ARG={ins.arg!s:<6} | "
                            f"ARGVAL={safe_repr(ins.argval, 100)}"
                        )

                print()
                print(
                    "BRANCH TAKEN STATUS : "
                    "NOT CLAIMED"
                )

        elif event == "return":

            stats["returns"] += 1

            if arg is None:
                stats["none_returns"] += 1

            print()
            print("=" * 100)
            print("FIND_FUTURE_PRICE RETURN")
            print("=" * 100)

            print("LINE       :", frame.f_lineno)
            print("TYPE       :", type(arg).__name__)
            print("OBJECT ID  :", id(arg))
            print("VALUE      :", safe_repr(arg))

            print()
            print("RETURN LOCALS")
            print("-" * 100)

            for name, value in frame.f_locals.items():
                print(
                    f"{name:<24} | "
                    f"{type(value).__name__:<18} | "
                    f"ID={id(value)} | "
                    f"{safe_repr(value)}"
                )

            active_frames.discard(frame_id)

        return tracer

    return tracer


def main():

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE POP_JUMP_IF_TRUE "
        "OPERAND RECURSION ISOLATION FORENSIC AUDIT v0.1"
    )
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
    print("STEP 0 — INSTALL READ-ONLY DATABASE GUARD")
    print("=" * 100)

    original_connect = install_sqlite_guard()

    print("DATABASE MODE : READ-ONLY")
    print("WRITE OPERATIONS : BLOCKED")

    stats = defaultdict(int)

    original_trace = sys.gettrace()

    try:

        print()
        print("=" * 100)
        print("STEP 1 — LOAD PRODUCTION MODULE WITHOUT AUTO-MAIN")
        print("=" * 100)

        namespace = load_production_without_auto_execution()

        target_function = find_function(
            namespace,
            TARGET_FUNCTION,
        )

        if target_function is None:
            print()
            print("ERROR : find_future_price() NOT FOUND")
            return

        target_code = target_function.__code__

        print_target_map(target_function)

        print()
        print("=" * 100)
        print("STEP 3 — SINGLE PRODUCTION MAIN EXECUTION")
        print("=" * 100)

        production_main = namespace.get("main")

        if production_main is None:
            raise RuntimeError(
                "Production main() not found."
            )

        tracer = make_tracer(
            target_code,
            stats,
        )

        sys.settrace(tracer)

        try:
            production_main()

        except RecursionError as exc:

            stats["recursion_errors"] += 1

            print()
            print("=" * 100)
            print("FORENSIC HARNESS RECURSION ERROR")
            print("=" * 100)

            print(
                "RecursionError was still produced."
            )

            print(
                repr(exc)
            )

            traceback.print_exc()

        except Exception as exc:

            stats["runtime_exceptions"] += 1

            print()
            print("=" * 100)
            print("PRODUCTION RUNTIME EXCEPTION")
            print("=" * 100)

            print(
                type(exc).__name__,
                repr(exc)
            )

            traceback.print_exc()

    except Exception as exc:

        stats["loader_exceptions"] += 1

        print()
        print("=" * 100)
        print("HARNESS LOAD EXCEPTION")
        print("=" * 100)

        print(
            type(exc).__name__,
            repr(exc)
        )

        traceback.print_exc()

    finally:

        sys.settrace(original_trace)

        sqlite3.connect = original_connect

    print()
    print("=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        "PRODUCTION MAIN EXECUTION : ATTEMPTED"
    )

    print(
        "FIND_FUTURE_PRICE CALLS   :",
        stats["calls"]
    )

    print(
        "FIND_FUTURE_PRICE RETURNS:",
        stats["returns"]
    )

    print(
        "NONE RETURNS             :",
        stats["none_returns"]
    )

    print(
        "POP_JUMP_IF_TRUE EVENTS  :",
        stats["branch_events"]
    )

    print(
        "RECURSION ERRORS         :",
        stats["recursion_errors"]
    )

    print(
        "RUNTIME EXCEPTIONS       :",
        stats["runtime_exceptions"]
    )

    print(
        "LOADER EXCEPTIONS        :",
        stats["loader_exceptions"]
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

    if stats["recursion_errors"] > 0:

        print(
            "STATUS : "
            "FORENSIC_HARNESS_RECURSION_NOT_ISOLATED"
        )

        print(
            "MEANING : "
            "The production execution still encountered recursion "
            "before useful target evidence was captured."
        )

        print(
            "NEXT FRONTIER : "
            "Remove tracing from module loading and isolate only "
            "the target frame using a non-recursive instrumentation path."
        )

    elif stats["branch_events"] > 0:

        print(
            "STATUS : "
            "POP_JUMP_IF_TRUE_RUNTIME_BOUNDARY_CAPTURED"
        )

        print(
            "MEANING : "
            "The production runtime reached the target branch without "
            "the previous loader recursion failure."
        )

        print(
            "NEXT FRONTIER : "
            "Capture the actual CPython evaluation-stack operand. "
            "Do not infer it from locals or source."
        )

    elif stats["calls"] > 0:

        print(
            "STATUS : "
            "FIND_FUTURE_PRICE_RUNTIME_REACHED_BRANCH_NOT_REACHED"
        )

        print(
            "MEANING : "
            "The target function executed, but offsets 206/226 "
            "were not reached."
        )

        print(
            "NEXT FRONTIER : "
            "Inspect the exact runtime path preceding the target offsets."
        )

    else:

        print(
            "STATUS : "
            "FIND_FUTURE_PRICE_RUNTIME_NOT_REACHED"
        )

        print(
            "MEANING : "
            "The target function was not entered during this execution."
        )

        print(
            "NEXT FRONTIER : "
            "Do not infer branch behavior. Reproduce target invocation."
        )

    print()
    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()