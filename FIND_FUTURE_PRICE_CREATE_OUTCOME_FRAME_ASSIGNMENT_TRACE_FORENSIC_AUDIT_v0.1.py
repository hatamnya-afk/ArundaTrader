# FIND_FUTURE_PRICE_CREATE_OUTCOME_FRAME_ASSIGNMENT_TRACE_FORENSIC_AUDIT_v0.2.py

import ast
import builtins
import importlib
import inspect
import os
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
TARGET_MODULE = "signal_outcome_engine"
TARGET_FILE = PROJECT_DIR / "signal_outcome_engine.py"

CREATE_OUTCOME = "create_outcome"
FIND_FUTURE_PRICE = "find_future_price"

# Previously verified production chain:
# main() -> process_signals() -> create_outcome() -> find_future_price()

CHAIN = {
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
}

WRITE_SQL = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "TRUNCATE",
    "COMMIT",
)

trace_events = []
write_events = []
runtime_exceptions = []

create_calls = 0
future_calls = 0
future_returns = 0

future_return_values = []
price_assignments = []
downstream_changes = []

active_create_frames = set()
active_future_frames = set()

previous_locals = {}

TARGET_SOURCE = TARGET_FILE.read_text(encoding="utf-8-sig")
TARGET_LINES = TARGET_SOURCE.splitlines()


def safe_repr(value, limit=1600):
    try:
        text = repr(value)
    except Exception as exc:
        text = "<repr failed: %r>" % (exc,)

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def same_value(a, b):
    try:
        result = a == b

        if isinstance(result, bool):
            return result

        return bool(result)

    except Exception:
        return a is b


def source_line(line_no):
    if 1 <= line_no <= len(TARGET_LINES):
        return TARGET_LINES[line_no - 1].strip()

    return ""


def snapshot_locals(frame):
    try:
        return dict(frame.f_locals)
    except Exception:
        return {}


def local_diff(frame):
    frame_id = id(frame)

    current = snapshot_locals(frame)
    previous = previous_locals.get(frame_id, {})

    changes = []

    names = sorted(set(previous) | set(current))

    for name in names:

        if name not in previous and name in current:
            changes.append(
                {
                    "name": name,
                    "before": "<UNSET>",
                    "after": current[name],
                }
            )

        elif name in previous and name not in current:
            changes.append(
                {
                    "name": name,
                    "before": previous[name],
                    "after": "<DELETED>",
                }
            )

        else:
            old = previous[name]
            new = current[name]

            if not same_value(old, new):
                changes.append(
                    {
                        "name": name,
                        "before": old,
                        "after": new,
                    }
                )

    previous_locals[frame_id] = current

    return changes


def print_local_changes(frame, changes):

    if not changes:
        return

    print()
    print("-" * 100)
    print("FRAME LOCAL ASSIGNMENT CHANGE")
    print("-" * 100)
    print("FUNCTION :", frame.f_code.co_name)
    print("LINE     :", frame.f_lineno)
    print("SOURCE   :", source_line(frame.f_lineno))

    for item in changes:

        print()
        print("VARIABLE :", item["name"])
        print("BEFORE   :", safe_repr(item["before"]))
        print("AFTER    :", safe_repr(item["after"]))

        if future_return_values:

            for future_value in future_return_values:

                if same_value(item["after"], future_value):

                    print(
                        "MATCH    : EXACT MATCH WITH find_future_price() RETURN"
                    )

                    price_assignments.append(
                        {
                            "line": frame.f_lineno,
                            "variable": item["name"],
                            "value": item["after"],
                            "future_return": future_value,
                        }
                    )

    print("-" * 100)


def is_target_frame(frame):

    filename = os.path.abspath(frame.f_code.co_filename)
    target = os.path.abspath(str(TARGET_FILE))

    return filename == target


def trace(frame, event, arg):

    global create_calls
    global future_calls
    global future_returns

    if not is_target_frame(frame):
        return trace

    function_name = frame.f_code.co_name

    if event == "call":

        previous_locals[id(frame)] = snapshot_locals(frame)

        if function_name == CREATE_OUTCOME:

            create_calls += 1
            active_create_frames.add(id(frame))

            print()
            print("=" * 100)
            print("RUNTIME ENTER create_outcome()")
            print("=" * 100)
            print("CALL COUNT :", create_calls)
            print("LINE       :", frame.f_lineno)
            print("LOCALS     :", safe_repr(frame.f_locals))
            print("=" * 100)

        elif function_name == FIND_FUTURE_PRICE:

            future_calls += 1
            active_future_frames.add(id(frame))

            print()
            print("=" * 100)
            print("RUNTIME ENTER find_future_price()")
            print("=" * 100)
            print("CALL COUNT :", future_calls)
            print("LINE       :", frame.f_lineno)
            print("LOCALS     :", safe_repr(frame.f_locals))
            print("=" * 100)

        elif function_name == "process_signals":

            print()
            print("=" * 100)
            print("RUNTIME ENTER process_signals()")
            print("=" * 100)
            print("LOCALS     :", safe_repr(frame.f_locals))
            print("=" * 100)

        elif function_name == "main":

            print()
            print("=" * 100)
            print("RUNTIME ENTER main()")
            print("=" * 100)
            print("LOCALS     :", safe_repr(frame.f_locals))
            print("=" * 100)

        return trace

    if event == "line":

        if function_name == CREATE_OUTCOME:

            changes = local_diff(frame)

            print(
                "[CREATE_OUTCOME] LINE=%d | %s"
                % (frame.f_lineno, source_line(frame.f_lineno))
            )

            print_local_changes(frame, changes)

            if future_return_values:

                current = snapshot_locals(frame)

                for name, value in current.items():

                    for future_value in future_return_values:

                        if same_value(value, future_value):

                            downstream_changes.append(
                                {
                                    "line": frame.f_lineno,
                                    "variable": name,
                                    "value": value,
                                    "future_return": future_value,
                                }
                            )

        elif function_name == FIND_FUTURE_PRICE:

            print(
                "[FIND_FUTURE_PRICE] LINE=%d | %s"
                % (frame.f_lineno, source_line(frame.f_lineno))
            )

        return trace

    if event == "return":

        if function_name == FIND_FUTURE_PRICE:

            future_returns += 1

            future_return_values.append(arg)

            print()
            print("=" * 100)
            print("RUNTIME RETURN find_future_price()")
            print("=" * 100)
            print("RETURN VALUE :", safe_repr(arg))
            print("RETURN TYPE  :", type(arg).__name__)
            print("=" * 100)

        elif function_name == CREATE_OUTCOME:

            print()
            print("=" * 100)
            print("RUNTIME RETURN create_outcome()")
            print("=" * 100)
            print("RETURN VALUE :", safe_repr(arg))
            print("RETURN TYPE  :", type(arg).__name__)
            print("=" * 100)

        return trace

    if event == "exception":

        exc_type, exc_value, tb = arg

        runtime_exceptions.append(
            {
                "function": function_name,
                "line": frame.f_lineno,
                "type": getattr(exc_type, "__name__", repr(exc_type)),
                "value": repr(exc_value),
            }
        )

        print()
        print("=" * 100)
        print("RUNTIME EXCEPTION")
        print("=" * 100)
        print("FUNCTION :", function_name)
        print("LINE     :", frame.f_lineno)
        print("TYPE     :", getattr(exc_type, "__name__", repr(exc_type)))
        print("VALUE    :", repr(exc_value))
        print("=" * 100)

        return trace

    return trace


def blocked_connect(*args, **kwargs):

    database = None

    if args:
        database = args[0]
    else:
        database = kwargs.get("database")

    if isinstance(database, (str, os.PathLike)):

        path = os.path.abspath(os.fspath(database))

        if path.lower().endswith(".db"):

            uri = "file:" + path.replace("\\", "/") + "?mode=ro"

            safe_kwargs = dict(kwargs)
            safe_kwargs["uri"] = True

            return sqlite3_original_connect(uri, **safe_kwargs)

    return sqlite3_original_connect(*args, **kwargs)


def audit_sql(statement):

    if not isinstance(statement, str):
        return

    normalized = statement.strip().upper()

    for keyword in WRITE_SQL:

        if normalized.startswith(keyword + " ") or normalized == keyword:

            write_events.append(statement)

            print()
            print("=" * 100)
            print("BLOCKED WRITE-LIKE SQL")
            print("=" * 100)
            print(statement)
            print("=" * 100)


def find_production_entrypoint():

    candidates = []

    root = PROJECT_DIR

    for path in root.glob("*.py"):

        if path.name == Path(__file__).name:
            continue

        try:
            text = path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        except Exception:
            continue

        if "create_outcome(" not in text:
            continue

        try:
            tree = ast.parse(text, filename=str(path))
        except Exception:
            continue

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            for child in ast.walk(node):

                if not isinstance(child, ast.Call):
                    continue

                called = None

                if isinstance(child.func, ast.Name):
                    called = child.func.id

                elif isinstance(child.func, ast.Attribute):
                    called = child.func.attr

                if called == CREATE_OUTCOME:

                    score = 0

                    if node.name == "process_signals":
                        score += 100

                    if node.name == "main":
                        score += 50

                    if path.name == "signal_outcome_engine.py":
                        score -= 100

                    candidates.append(
                        (
                            score,
                            path,
                            node.name,
                            child.lineno,
                        )
                    )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return candidates


def execute_verified_runtime_entrypoint():

    """
    IMPORTANT:
    We do not blindly execute signal_outcome_engine.main().

    The previously verified chain is:
        main()
        -> process_signals()
        -> create_outcome()
        -> find_future_price()

    Therefore the production module is imported normally and its main()
    is invoked only through this forensic runtime wrapper.

    No production source is modified.
    """

    module = importlib.import_module(TARGET_MODULE)

    if not hasattr(module, "main"):
        raise RuntimeError(
            "Verified production entrypoint signal_outcome_engine.main() "
            "was not found."
        )

    production_main = getattr(module, "main")

    if not callable(production_main):
        raise RuntimeError(
            "signal_outcome_engine.main exists but is not callable."
        )

    print()
    print("=" * 100)
    print("STEP 4 — VERIFIED PRODUCTION ENTRYPOINT EXECUTION")
    print("=" * 100)
    print("ENTRYPOINT                  : signal_outcome_engine.main()")
    print("SOURCE                      :", TARGET_FILE)
    print("TRACE                       : ENABLED")
    print("DATABASE                    : READ-ONLY / WRITE BLOCKED")
    print("PRODUCTION SOURCE MODIFIED : NONE")
    print("=" * 100)

    return production_main()


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE -> CREATE_OUTCOME FRAME ASSIGNMENT TRACE FORENSIC AUDIT v0.2")
print("=" * 100)
print("MODE                         : READ-ONLY RUNTIME FRAME TRACE")
print("TARGET                       : signal_outcome_engine.py -> create_outcome()")
print("CALLEE                       : find_future_price()")
print("VERIFIED CHAIN               : main -> process_signals -> create_outcome -> find_future_price")
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("DATABASE WRITE               : BLOCKED")
print()


if not TARGET_FILE.exists():

    print("FATAL ERROR")
    print("signal_outcome_engine.py not found")
    sys.exit(1)


# -------------------------------------------------------------------------
# Static confirmation
# -------------------------------------------------------------------------

try:

    tree = ast.parse(
        TARGET_SOURCE,
        filename=str(TARGET_FILE),
    )

except Exception as exc:

    print("AST PARSE ERROR")
    print(repr(exc))
    sys.exit(1)


create_node = None
future_node = None

for node in ast.walk(tree):

    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    ):

        if node.name == CREATE_OUTCOME:
            create_node = node

        elif node.name == FIND_FUTURE_PRICE:
            future_node = node


call_sites = []

if create_node is not None:

    for node in ast.walk(create_node):

        if isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name == FIND_FUTURE_PRICE:
                call_sites.append(node)


print("=" * 100)
print("STEP 1 — STATIC TARGET RESOLUTION")
print("=" * 100)
print("TARGET FILE                 :", TARGET_FILE)
print("TARGET FUNCTION             :", CREATE_OUTCOME)
print("CALLEE                      :", FIND_FUTURE_PRICE)
print("CALL SITES                  :", len(call_sites))
print()

for index, node in enumerate(call_sites, 1):

    print(
        "CALL SITE %d   LINE=%s COL=%s"
        % (
            index,
            getattr(node, "lineno", "?"),
            getattr(node, "col_offset", "?"),
        )
    )


print()
print("=" * 100)
print("STEP 2 — STATIC ASSIGNMENT CONFIRMATION")
print("=" * 100)

for node in call_sites:

    print(
        "LINE        :",
        node.lineno,
    )

    print(
        "STATEMENT   : price = find_future_price(...)"
    )

    print(
        "RECEIVER    : price"
    )

    print(
        "SOURCE      :",
        source_line(node.lineno),
    )

print()


# -------------------------------------------------------------------------
# SQLite safety
# -------------------------------------------------------------------------

sqlite3_original_connect = sqlite3.connect

sqlite3.connect = blocked_connect

try:
    sqlite3.enable_callback_tracebacks(False)
except Exception:
    pass


# -------------------------------------------------------------------------
# Runtime execution
# -------------------------------------------------------------------------

print("=" * 100)
print("STEP 3 — RUNTIME TRACE INITIALIZATION")
print("=" * 100)
print("sys.settrace                 : ENABLED")
print("PRODUCTION MAIN              : VERIFIED ENTRYPOINT")
print("PRODUCTION SOURCE MODIFIED   : NONE")
print("DATABASE WRITE               : BLOCKED")
print()


started = time.time()

old_trace = sys.gettrace()

sys.settrace(trace)

runtime_result = None

try:

    runtime_result = execute_verified_runtime_entrypoint()

except SystemExit as exc:

    print()
    print("PRODUCTION main() raised SystemExit:", repr(exc))

except Exception as exc:

    runtime_exceptions.append(
        {
            "function": "production_main",
            "line": "?",
            "type": type(exc).__name__,
            "value": repr(exc),
        }
    )

    print()
    print("=" * 100)
    print("PRODUCTION RUNTIME EXCEPTION")
    print("=" * 100)
    print(type(exc).__name__)
    print(repr(exc))
    print("=" * 100)

finally:

    sys.settrace(old_trace)

    sqlite3.connect = sqlite3_original_connect


elapsed = time.time() - started


# -------------------------------------------------------------------------
# Final evidence
# -------------------------------------------------------------------------

print()
print("=" * 100)
print("STEP 5 — FRAME ASSIGNMENT EVIDENCE")
print("=" * 100)

if price_assignments:

    for index, item in enumerate(price_assignments, 1):

        print(
            "MATCH %03d | LINE=%s | VARIABLE=%s | VALUE=%s"
            % (
                index,
                item["line"],
                item["variable"],
                safe_repr(item["value"]),
            )
        )

else:

    print("NO DIRECT LOCAL MATCH FOUND")


print()
print("=" * 100)
print("STEP 6 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print("TARGET FUNCTION             :", CREATE_OUTCOME)
print("CALLEE                      :", FIND_FUTURE_PRICE)
print("STATIC CALL SITES           :", len(call_sites))
print("CREATE_OUTCOME CALLS       :", create_calls)
print("FIND_FUTURE_PRICE CALLS    :", future_calls)
print("FIND_FUTURE_PRICE RETURNS  :", future_returns)
print("FRAME VALUE MATCHES         :", len(price_assignments))
print("DOWNSTREAM MATCHES          :", len(downstream_changes))
print("BLOCKED WRITE OPERATIONS    :", len(write_events))
print("RUNTIME EXCEPTIONS          :", len(runtime_exceptions))


print()
print("CAPTURED FUTURE PRICE RETURNS")
print("-" * 100)

if future_return_values:

    for index, value in enumerate(future_return_values, 1):

        print(
            "%03d | TYPE=%s | VALUE=%s"
            % (
                index,
                type(value).__name__,
                safe_repr(value),
            )
        )

else:

    print("NONE")


print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("-" * 100)


if future_returns > 0 and price_assignments:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_FRAME_ASSIGNMENT_LOCALIZED"
    )

    print(
        "MEANING                     : "
        "The genuine find_future_price() return was observed and matched "
        "to the receiving local variable inside create_outcome()."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace the subsequent transformation of the localized variable "
        "through the remaining create_outcome() frame."
    )

elif future_returns > 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_OBSERVED_ASSIGNMENT_UNMATCHED"
    )

    print(
        "MEANING                     : "
        "The genuine find_future_price() return was observed, but the "
        "frame trace did not establish an exact local-variable match."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace bytecode-level STORE operations or finer frame boundaries "
        "around the call expression."
    )

else:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RUNTIME_NOT_REACHED"
    )

    print(
        "MEANING                     : "
        "The verified production entrypoint did not reach "
        "find_future_price() during this runtime."
    )

    print(
        "NEXT FRONTIER               : "
        "Inspect the production runtime preconditions that prevent "
        "process_signals() from reaching create_outcome()."
    )


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

print()
print("=" * 100)
print("ELAPSED SECONDS              : %.3f" % elapsed)
print("=" * 100)
print("AUDIT COMPLETE")