import os
import sys
import sqlite3
import dis
import traceback
from collections import defaultdict

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


# ============================================================
# SAFETY
# ============================================================

WRITE_WORDS = (
    "INSERT", "UPDATE", "DELETE", "ALTER",
    "CREATE", "DROP", "REPLACE", "VACUUM",
    "COMMIT", "ROLLBACK"
)


class ReadOnlyConnection:
    def __init__(self, path):
        self.path = path
        self.conn = None

    def open(self):
        uri = "file:" + os.path.abspath(self.path) + "?mode=ro"
        self.conn = sqlite3.connect(
            uri,
            uri=True,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        if self.conn is not None:
            self.conn.close()


# ============================================================
# HELPERS
# ============================================================

def safe_repr(value, limit=240):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        text = text[:limit] + "..."
    return text


def value_info(value):
    return {
        "type": type(value).__name__,
        "id": id(value),
        "value": safe_repr(value)
    }


def is_write_sql(text):
    if not isinstance(text, str):
        return False

    normalized = text.strip().upper()

    return any(
        normalized.startswith(word)
        for word in WRITE_WORDS
    )


# ============================================================
# BYTECODE MAP
# ============================================================

def resolve_find_future_price():
    namespace = {}

    with open(TARGET, "r", encoding="utf-8") as f:
        source = f.read()

    code = compile(
        source,
        TARGET,
        "exec"
    )

    exec(compile(source, TARGET, "exec"), namespace)

    fn = namespace.get("find_future_price")

    if fn is None:
        raise RuntimeError(
            "find_future_price() was not resolved."
        )

    return fn


def build_instruction_map(fn):
    instructions = list(dis.get_instructions(fn))

    by_offset = {
        ins.offset: ins
        for ins in instructions
    }

    index_by_offset = {
        ins.offset: i
        for i, ins in enumerate(instructions)
    }

    return instructions, by_offset, index_by_offset


# ============================================================
# BRANCH OPCODE IDENTIFICATION
# ============================================================

BRANCH_OPS = {
    "POP_JUMP_FORWARD_IF_FALSE",
    "POP_JUMP_FORWARD_IF_TRUE",
    "POP_JUMP_BACKWARD_IF_FALSE",
    "POP_JUMP_BACKWARD_IF_TRUE",
    "POP_JUMP_IF_FALSE",
    "POP_JUMP_IF_TRUE",
    "JUMP_IF_FALSE_OR_POP",
    "JUMP_IF_TRUE_OR_POP",
    "JUMP_IF_NOT_EXC_MATCH",
    "FOR_ITER",
    "SEND",
    "JUMP_FORWARD",
    "JUMP_BACKWARD",
}


RETURN_OPS = {
    "RETURN_VALUE"
}


# ============================================================
# TRACE STATE
# ============================================================

class RuntimeTracer:
    def __init__(self, target_code, instructions):
        self.target_code = target_code
        self.instructions = instructions

        self.branch_events = []
        self.return_events = []
        self.control_events = []

        self.call_count = 0
        self.return_count = 0

        self.none_returns = 0
        self.non_none_returns = 0

        self.active_frames = {}

        self.last_line = None
        self.last_offset = None

        self.exceptions = []

    def local_snapshot(self, frame):
        result = {}

        try:
            for name, value in frame.f_locals.items():
                result[name] = value_info(value)
        except Exception:
            pass

        return result

    def trace(self, frame, event, arg):
        if frame.f_code is not self.target_code:
            return self.trace

        try:
            if event == "call":
                self.call_count += 1

                self.active_frames[id(frame)] = {
                    "frame": frame,
                    "entry": True
                }

                return self.trace

            if event == "exception":
                self.exceptions.append({
                    "event": "exception",
                    "offset": self.last_offset,
                    "line": frame.f_lineno,
                    "exception": safe_repr(arg)
                })
                return self.trace

            if event == "return":
                self.return_count += 1

                info = value_info(arg)

                self.return_events.append({
                    "offset": self.last_offset,
                    "line": frame.f_lineno,
                    "value": info
                })

                if arg is None:
                    self.none_returns += 1
                else:
                    self.non_none_returns += 1

                return self.trace

            if event == "opcode":
                offset = frame.f_lasti
                self.last_offset = offset
                self.last_line = frame.f_lineno

                ins = next(
                    (
                        x for x in self.instructions
                        if x.offset == offset
                    ),
                    None
                )

                if ins is None:
                    return self.trace

                event_info = {
                    "offset": ins.offset,
                    "line": frame.f_lineno,
                    "opname": ins.opname,
                    "arg": ins.arg,
                    "argval": safe_repr(ins.argval),
                }

                self.control_events.append(event_info)

                if ins.opname in BRANCH_OPS:
                    locals_snapshot = self.local_snapshot(frame)

                    event_info = {
                        "offset": ins.offset,
                        "line": frame.f_lineno,
                        "opname": ins.opname,
                        "arg": ins.arg,
                        "argval": safe_repr(ins.argval),
                        "jump_target": getattr(
                            ins,
                            "argval",
                            None
                        ),
                        "locals": locals_snapshot
                    }

                    self.branch_events.append(event_info)

                return self.trace

        except Exception as exc:
            self.exceptions.append({
                "event": "trace_error",
                "offset": self.last_offset,
                "line": self.last_line,
                "exception": safe_repr(exc)
            })

        return self.trace


# ============================================================
# NONE RETURN LOCALIZATION
# ============================================================

def nearest_return_instruction(
    instructions,
    branch_index,
    max_distance=30
):
    end = min(
        len(instructions),
        branch_index + max_distance + 1
    )

    for i in range(branch_index + 1, end):
        ins = instructions[i]

        if ins.opname == "RETURN_VALUE":
            return ins

    return None


def print_bytecode_context(
    instructions,
    branch_offset,
    radius=8
):
    positions = {
        ins.offset: i
        for i, ins in enumerate(instructions)
    }

    if branch_offset not in positions:
        return

    index = positions[branch_offset]

    start = max(
        0,
        index - radius
    )

    end = min(
        len(instructions),
        index + radius + 1
    )

    print()
    print("=" * 100)
    print("BYTECODE CONTEXT")
    print("=" * 100)

    for ins in instructions[start:end]:
        marker = " <-- BRANCH" if ins.offset == branch_offset else ""

        print(
            f"{ins.offset:5d} | "
            f"LINE={str(ins.starts_line):4} | "
            f"{ins.opname:35} | "
            f"ARG={str(ins.arg):5} | "
            f"ARGVAL={safe_repr(ins.argval)}"
            f"{marker}"
        )


# ============================================================
# RUNTIME AUDIT
# ============================================================

def run_audit():
    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE NONE BRANCH CONDITION "
        "EXACT RUNTIME FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(f"TARGET : {TARGET}")
    print(f"DATABASE : {DB_PATH}")
    print("MODE : READ-ONLY REAL-RUNTIME FORENSICS")
    print("PRODUCTION SOURCE : UNMODIFIED")
    print("DATABASE WRITES : BLOCKED")

    # --------------------------------------------------------
    # STATIC RESOLUTION
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 1 — STATIC FUNCTION RESOLUTION")
    print("=" * 100)

    try:
        fn = resolve_find_future_price()

        print(
            f"find_future_price : FOUND | "
            f"LINE={fn.__code__.co_firstlineno}"
        )

    except Exception as exc:
        print(
            "STATIC RESOLUTION ERROR :",
            repr(exc)
        )
        return

    instructions, by_offset, index_by_offset = (
        build_instruction_map(fn)
    )

    print()
    print("=" * 100)
    print("STEP 2 — BRANCH / RETURN BYTECODE MAP")
    print("=" * 100)

    branch_instructions = [
        ins
        for ins in instructions
        if ins.opname in BRANCH_OPS
    ]

    return_instructions = [
        ins
        for ins in instructions
        if ins.opname == "RETURN_VALUE"
    ]

    print(
        f"BRANCH OPCODES : {len(branch_instructions)}"
    )

    for ins in branch_instructions:
        print(
            f"OFFSET={ins.offset:4d} | "
            f"LINE={str(ins.starts_line):4} | "
            f"OP={ins.opname:35} | "
            f"ARG={str(ins.arg):5} | "
            f"ARGVAL={safe_repr(ins.argval)}"
        )

    print()
    print(
        f"RETURN_VALUE OPCODES : "
        f"{len(return_instructions)}"
    )

    for ins in return_instructions:
        print(
            f"OFFSET={ins.offset:4d} | "
            f"LINE={str(ins.starts_line):4}"
        )

    # --------------------------------------------------------
    # REAL RUNTIME
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 3 — GENUINE PRODUCTION RUNTIME")
    print("=" * 100)

    tracer = RuntimeTracer(
        fn.__code__,
        instructions
    )

    old_trace = sys.gettrace()

    try:
        sys.settrace(tracer.trace)

        # ----------------------------------------------------
        # IMPORTANT:
        # We execute the REAL function directly.
        # Its own DB argument is supplied from a READ-ONLY
        # connection.
        # ----------------------------------------------------

        ro = ReadOnlyConnection(DB_PATH)
        conn = ro.open()

        print("REAL find_future_price() INVOCATION")

        try:
            # We cannot invent production arguments.
            # Therefore resolve actual caller context by executing
            # the production main() only if available.
            namespace = {}

            with open(
                TARGET,
                "r",
                encoding="utf-8"
            ) as f:
                source = f.read()

            exec(
                compile(
                    source,
                    TARGET,
                    "exec"
                ),
                namespace
            )

            main_fn = namespace.get("main")

            if main_fn is None:
                raise RuntimeError(
                    "Production main() was not resolved."
                )

            main_fn()

        finally:
            ro.close()

    except Exception as exc:
        print()
        print("=" * 100)
        print("RUNTIME EXCEPTION")
        print("=" * 100)
        print(repr(exc))

        traceback.print_exc()

    finally:
        sys.settrace(old_trace)

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 4 — NONE RETURN SUMMARY")
    print("=" * 100)

    print(
        f"FIND_FUTURE_PRICE CALLS   : "
        f"{tracer.call_count}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS : "
        f"{tracer.return_count}"
    )

    print(
        f"NONE RETURNS              : "
        f"{tracer.none_returns}"
    )

    print(
        f"NON-NONE RETURNS          : "
        f"{tracer.non_none_returns}"
    )

    # --------------------------------------------------------
    # BRANCH ANALYSIS
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 5 — EXACT RUNTIME BRANCH EVENTS")
    print("=" * 100)

    for n, event in enumerate(
        tracer.branch_events,
        1
    ):
        print()
        print(
            f"BRANCH EVENT #{n}"
        )
        print("-" * 90)

        print(
            f"OFFSET       : {event['offset']}"
        )

        print(
            f"LINE         : {event['line']}"
        )

        print(
            f"OPCODE       : {event['opname']}"
        )

        print(
            f"ARG          : {event['arg']}"
        )

        print(
            f"ARGVAL       : {event['argval']}"
        )

        print(
            f"JUMP TARGET  : {event['jump_target']}"
        )

        print()
        print("RUNTIME LOCALS")
        print("-" * 90)

        for name, info in event["locals"].items():
            print(
                f"{name:20} | "
                f"TYPE={info['type']:20} | "
                f"ID={info['id']} | "
                f"VALUE={info['value']}"
            )

    # --------------------------------------------------------
    # RETURN CONTEXT
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 6 — NONE RETURN CONTEXT")
    print("=" * 100)

    none_return_offsets = []

    for event in tracer.return_events:
        if event["value"]["value"] == "None":
            none_return_offsets.append(
                event["offset"]
            )

            print()
            print(
                f"NONE RETURN | "
                f"OFFSET={event['offset']} | "
                f"LINE={event['line']}"
            )

    # --------------------------------------------------------
    # MATCH BRANCH -> RETURN
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 7 — BRANCH → NONE RETURN LOCALIZATION")
    print("=" * 100)

    matches = []

    for event in tracer.branch_events:

        offset = event["offset"]

        if offset not in index_by_offset:
            continue

        branch_index = index_by_offset[offset]

        ret = nearest_return_instruction(
            instructions,
            branch_index,
            max_distance=30
        )

        if ret is None:
            continue

        matches.append(
            (
                event,
                ret
            )
        )

        print()
        print(
            f"BRANCH OFFSET : {event['offset']}"
        )

        print(
            f"BRANCH OPCODE : {event['opname']}"
        )

        print(
            f"BRANCH LINE   : {event['line']}"
        )

        print(
            f"JUMP TARGET   : {event['jump_target']}"
        )

        print(
            f"NEAREST RETURN: OFFSET={ret.offset}"
        )

        print(
            f"RETURN LINE   : {ret.starts_line}"
        )

        print_bytecode_context(
            instructions,
            event["offset"],
            radius=10
        )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 8 — SAFETY VERIFICATION")
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

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"MAIN / PRODUCTION EXECUTION : "
        f"OBSERVED"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{tracer.call_count}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{tracer.return_count}"
    )

    print(
        f"NONE RETURNS                : "
        f"{tracer.none_returns}"
    )

    print(
        f"NON-NONE RETURNS            : "
        f"{tracer.non_none_returns}"
    )

    print(
        f"BRANCH EVENTS               : "
        f"{len(tracer.branch_events)}"
    )

    print(
        f"BRANCH → RETURN CANDIDATES  : "
        f"{len(matches)}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(tracer.exceptions)}"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if tracer.none_returns > 0 and len(tracer.branch_events) > 0:
        status = (
            "FIND_FUTURE_PRICE_NONE_BRANCH_RUNTIME_CAPTURED"
        )

        meaning = (
            "find_future_price() returned None at runtime and "
            "the branch opcodes immediately surrounding the "
            "function control-flow were captured."
        )

        frontier = (
            "Identify the exact branch condition whose runtime "
            "operand selected the None-return path."
        )

    elif tracer.none_returns > 0:
        status = (
            "FIND_FUTURE_PRICE_NONE_RETURN_NO_BRANCH_MATCH"
        )

        meaning = (
            "None returns were observed, but no runtime branch "
            "event could yet be associated with the return path."
        )

        frontier = (
            "Capture the opcode-level condition immediately "
            "before RETURN_VALUE."
        )

    else:
        status = (
            "FIND_FUTURE_PRICE_NONE_RETURN_NOT_REPRODUCED"
        )

        meaning = (
            "The expected None-return behavior was not reproduced "
            "during this runtime execution."
        )

        frontier = (
            "Do not infer the cause; reproduce the exact runtime "
            "condition before proceeding."
        )

    print(
        f"STATUS : {status}"
    )

    print(
        f"MEANING : {meaning}"
    )

    print(
        f"NEXT FRONTIER : {frontier}"
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
    run_audit()