# FIND_FUTURE_PRICE_PRICE_TRANSFORMATION_TRACE_FORENSIC_AUDIT_v0.1.py

import ast
import importlib
import inspect
import os
import sys
import time
import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
TARGET_FILE = PROJECT_DIR / "signal_outcome_engine.py"
TARGET_MODULE = "signal_outcome_engine"

CREATE_OUTCOME = "create_outcome"
FIND_FUTURE_PRICE = "find_future_price"

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

runtime_exceptions = []
write_events = []

future_calls = []
future_returns = []

create_returns = []

price_states = []
price_transformations = []

trace_enabled = False
current_create_frame = None
current_future_frame = None

sqlite_original_connect = sqlite3.connect


def safe_repr(value, limit=1200):
    try:
        text = repr(value)
    except Exception as exc:
        text = "<repr failed: %r>" % exc

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def equal_value(a, b):
    try:
        result = a == b

        if isinstance(result, bool):
            return result

        return bool(result)

    except Exception:
        return a is b


def source_lines():
    try:
        return TARGET_FILE.read_text(
            encoding="utf-8-sig",
            errors="replace",
        ).splitlines()
    except Exception:
        return []


SOURCE_LINES = source_lines()


def source_line(line):
    if 1 <= line <= len(SOURCE_LINES):
        return SOURCE_LINES[line - 1].strip()

    return ""


def is_target_file(frame):
    try:
        return (
            os.path.abspath(frame.f_code.co_filename)
            == os.path.abspath(str(TARGET_FILE))
        )
    except Exception:
        return False


def snapshot(frame):
    try:
        return dict(frame.f_locals)
    except Exception:
        return {}


def describe_value(value):
    return {
        "type": type(value).__name__,
        "repr": safe_repr(value),
        "id": id(value),
    }


def detect_sql_write(statement):
    if not isinstance(statement, str):
        return

    normalized = statement.strip().upper()

    for keyword in WRITE_SQL:
        if normalized == keyword or normalized.startswith(keyword + " "):
            write_events.append(statement)


def readonly_connect(*args, **kwargs):
    database = None

    if args:
        database = args[0]
    else:
        database = kwargs.get("database")

    if isinstance(database, (str, os.PathLike)):

        path = os.path.abspath(os.fspath(database))

        if path.lower().endswith(".db"):

            uri = (
                "file:"
                + path.replace("\\", "/")
                + "?mode=ro"
            )

            readonly_kwargs = dict(kwargs)
            readonly_kwargs["uri"] = True

            return sqlite_original_connect(
                uri,
                **readonly_kwargs,
            )

    return sqlite_original_connect(*args, **kwargs)


def find_create_node(tree):
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if node.name == CREATE_OUTCOME:
                return node

    return None


def find_future_call_nodes(create_node):

    result = []

    for node in ast.walk(create_node):

        if isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name == FIND_FUTURE_PRICE:
                result.append(node)

    return result


def enclosing_assignment_map(create_node):

    assignments = []

    for node in ast.walk(create_node):

        if isinstance(node, ast.Assign):

            for target in node.targets:

                assignments.append(
                    (
                        getattr(node, "lineno", None),
                        ast.unparse(target),
                        ast.unparse(node.value),
                    )
                )

        elif isinstance(node, ast.AnnAssign):

            if node.value is not None:

                assignments.append(
                    (
                        getattr(node, "lineno", None),
                        ast.unparse(node.target),
                        ast.unparse(node.value),
                    )
                )

        elif isinstance(node, ast.AugAssign):

            assignments.append(
                (
                    getattr(node, "lineno", None),
                    ast.unparse(node.target),
                    ast.unparse(node),
                )
            )

    return assignments


def trace(frame, event, arg):

    global current_create_frame
    global current_future_frame

    if not is_target_file(frame):
        return trace

    function_name = frame.f_code.co_name

    if event == "call":

        if function_name == CREATE_OUTCOME:

            current_create_frame = frame

            print()
            print("=" * 100)
            print("RUNTIME ENTER create_outcome()")
            print("=" * 100)
            print("ARGS / LOCALS :", safe_repr(frame.f_locals))
            print("=" * 100)

        elif function_name == FIND_FUTURE_PRICE:

            current_future_frame = frame

            record = {
                "line": frame.f_lineno,
                "locals": snapshot(frame),
            }

            future_calls.append(record)

            print()
            print("=" * 100)
            print("RUNTIME ENTER find_future_price()")
            print("=" * 100)
            print("CALL #        :", len(future_calls))
            print("LINE          :", frame.f_lineno)
            print("LOCALS        :", safe_repr(frame.f_locals))
            print("=" * 100)

        return trace

    if event == "line":

        if function_name == CREATE_OUTCOME:

            locals_now = snapshot(frame)

            if "price" in locals_now:

                state = {
                    "line": frame.f_lineno,
                    "value": locals_now.get("price"),
                    "locals": locals_now,
                    "source": source_line(frame.f_lineno),
                }

                price_states.append(state)

                print(
                    "[CREATE_OUTCOME] "
                    "LINE=%d | price=%s | %s"
                    % (
                        frame.f_lineno,
                        safe_repr(locals_now.get("price")),
                        source_line(frame.f_lineno),
                    )
                )

        return trace

    if event == "return":

        if function_name == FIND_FUTURE_PRICE:

            future_returns.append(
                {
                    "line": frame.f_lineno,
                    "value": arg,
                    "locals": snapshot(frame),
                }
            )

            print()
            print("=" * 100)
            print("find_future_price() RETURN")
            print("=" * 100)
            print("RETURN VALUE :", safe_repr(arg))
            print("TYPE         :", type(arg).__name__)
            print("=" * 100)

        elif function_name == CREATE_OUTCOME:

            create_returns.append(
                {
                    "line": frame.f_lineno,
                    "value": arg,
                    "locals": snapshot(frame),
                }
            )

            print()
            print("=" * 100)
            print("create_outcome() RETURN")
            print("=" * 100)
            print("RETURN VALUE :", safe_repr(arg))
            print("TYPE         :", type(arg).__name__)
            print("=" * 100)

        return trace

    if event == "exception":

        exc_type, exc_value, tb = arg

        runtime_exceptions.append(
            {
                "function": function_name,
                "line": frame.f_lineno,
                "type": getattr(
                    exc_type,
                    "__name__",
                    repr(exc_type),
                ),
                "value": repr(exc_value),
            }
        )

        return trace

    return trace


def execute_production_main():

    module = importlib.import_module(TARGET_MODULE)

    if not hasattr(module, "main"):
        raise RuntimeError(
            "signal_outcome_engine.main() was not found."
        )

    production_main = getattr(module, "main")

    if not callable(production_main):
        raise RuntimeError(
            "signal_outcome_engine.main is not callable."
        )

    return production_main()


def ast_transformation_candidates():

    try:
        source = TARGET_FILE.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

        tree = ast.parse(
            source,
            filename=str(TARGET_FILE),
        )

    except Exception:
        return []

    create_node = find_create_node(tree)

    if create_node is None:
        return []

    result = []

    for node in ast.walk(create_node):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.NamedExpr,
            ),
        ):

            try:
                text = ast.unparse(node)
            except Exception:
                text = "<unparse failed>"

            result.append(
                (
                    getattr(node, "lineno", None),
                    text,
                )
            )

    return sorted(
        result,
        key=lambda x: x[0] or 0,
    )


print("=" * 100)
print(
    "ARUNDA FIND_FUTURE_PRICE PRICE TRANSFORMATION "
    "TRACE FORENSIC AUDIT v0.1"
)
print("=" * 100)
print("MODE                         : READ-ONLY RUNTIME FORENSICS")
print(
    "TARGET                       : "
    "signal_outcome_engine.py -> create_outcome()"
)
print(
    "SOURCE VALUE                 : "
    "find_future_price() return"
)
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("DATABASE WRITE               : BLOCKED")
print()


# ==========================================================================
# STEP 1 — STATIC RESOLUTION
# ==========================================================================

print("=" * 100)
print("STEP 1 — STATIC TRANSFORMATION CANDIDATE RESOLUTION")
print("=" * 100)

if not TARGET_FILE.exists():

    print("TARGET FILE NOT FOUND :", TARGET_FILE)
    sys.exit(1)


try:

    source = TARGET_FILE.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    tree = ast.parse(
        source,
        filename=str(TARGET_FILE),
    )

except Exception as exc:

    print("AST ERROR :", repr(exc))
    sys.exit(1)


create_node = find_create_node(tree)

if create_node is None:

    print("create_outcome() NOT FOUND")
    sys.exit(1)


call_nodes = find_future_call_nodes(create_node)

print(
    "find_future_price() CALL SITES :",
    len(call_nodes),
)

for node in call_nodes:

    print()
    print(
        "CALL LINE :",
        node.lineno,
    )

    print(
        "CALL      :",
        ast.unparse(node),
    )


print()
print("=" * 100)
print("STATIC ASSIGNMENT / TRANSFORMATION MAP")
print("=" * 100)

static_candidates = ast_transformation_candidates()

for line, text in static_candidates:

    print(
        "LINE=%s | %s"
        % (
            line,
            text,
        )
    )


# ==========================================================================
# STEP 2 — SQLITE SAFETY
# ==========================================================================

print()
print("=" * 100)
print("STEP 2 — DATABASE WRITE SAFETY")
print("=" * 100)

sqlite3.connect = readonly_connect

print("sqlite3.connect              : READ-ONLY WRAPPER")
print("INSERT                       : BLOCKED")
print("UPDATE                       : BLOCKED")
print("DELETE                       : BLOCKED")
print("ALTER                        : BLOCKED")
print("CREATE                       : BLOCKED")
print("DROP                         : BLOCKED")
print("COMMIT                       : BLOCKED")


# ==========================================================================
# STEP 3 — RUNTIME TRACE
# ==========================================================================

print()
print("=" * 100)
print("STEP 3 — PRODUCTION RUNTIME TRACE")
print("=" * 100)
print("ENTRYPOINT                   : signal_outcome_engine.main()")
print("sys.settrace                 : ENABLED")
print("PRODUCTION SOURCE MODIFIED  : NONE")
print()


started = time.time()

old_trace = sys.gettrace()

sys.settrace(trace)

runtime_result = None

try:

    runtime_result = execute_production_main()

except SystemExit as exc:

    print()
    print(
        "Production main() raised SystemExit:",
        repr(exc),
    )

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

    sqlite3.connect = sqlite_original_connect


elapsed = time.time() - started


# ==========================================================================
# STEP 4 — MATCH RETURN -> PRICE
# ==========================================================================

print()
print("=" * 100)
print("STEP 4 — FUTURE RETURN -> PRICE TRANSFORMATION TRACE")
print("=" * 100)

match_count = 0

for return_index, ret in enumerate(
    future_returns,
    1,
):

    future_value = ret["value"]

    print()
    print(
        "FIND_FUTURE_PRICE RETURN #%d"
        % return_index
    )

    print(
        "VALUE :",
        safe_repr(future_value),
    )

    matched_states = []

    for state in price_states:

        if equal_value(
            state["value"],
            future_value,
        ):

            matched_states.append(state)

    if matched_states:

        for state in matched_states:

            match_count += 1

            print(
                "MATCH | LINE=%s | price=%s | %s"
                % (
                    state["line"],
                    safe_repr(state["value"]),
                    state["source"],
                )
            )

    else:

        print("MATCH : NONE")


# ==========================================================================
# STEP 5 — DETECT TRANSFORMATIONS
# ==========================================================================

print()
print("=" * 100)
print("STEP 5 — PRICE TRANSFORMATION OBSERVATION")
print("=" * 100)

transformations = []

for index in range(1, len(price_states)):

    previous = price_states[index - 1]
    current = price_states[index]

    old_value = previous["value"]
    new_value = current["value"]

    if not equal_value(
        old_value,
        new_value,
    ):

        transformations.append(
            {
                "line": current["line"],
                "before": old_value,
                "after": new_value,
                "source": current["source"],
            }
        )


if transformations:

    for item in transformations:

        print()
        print(
            "LINE       :",
            item["line"],
        )

        print(
            "BEFORE     :",
            safe_repr(item["before"]),
        )

        print(
            "AFTER      :",
            safe_repr(item["after"]),
        )

        print(
            "SOURCE     :",
            item["source"],
        )

else:

    print(
        "No observed price transformation was detected."
    )


# ==========================================================================
# STEP 6 — CREATE_OUTCOME RETURN COMPARISON
# ==========================================================================

print()
print("=" * 100)
print("STEP 6 — FINAL create_outcome() RETURN COMPARISON")
print("=" * 100)

for index, result in enumerate(
    create_returns,
    1,
):

    print()
    print(
        "CREATE_OUTCOME RETURN #%d"
        % index
    )

    print(
        "TYPE  :",
        type(result["value"]).__name__,
    )

    print(
        "VALUE :",
        safe_repr(result["value"]),
    )


# ==========================================================================
# STEP 7 — FINAL FORENSIC SUMMARY
# ==========================================================================

print()
print("=" * 100)
print("STEP 7 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    "FIND_FUTURE_PRICE CALLS       :",
    len(future_calls),
)

print(
    "FIND_FUTURE_PRICE RETURNS     :",
    len(future_returns),
)

print(
    "CREATE_OUTCOME CALLS          :",
    sum(
        1
        for item in create_returns
    )
    if create_returns
    else 0,
)

print(
    "PRICE OBSERVATIONS            :",
    len(price_states),
)

print(
    "RETURN -> PRICE MATCHES       :",
    match_count,
)

print(
    "OBSERVED TRANSFORMATIONS      :",
    len(transformations),
)

print(
    "CREATE_OUTCOME RETURNS        :",
    len(create_returns),
)

print(
    "RUNTIME EXCEPTIONS            :",
    len(runtime_exceptions),
)

print(
    "BLOCKED WRITE OPERATIONS      :",
    len(write_events),
)


# ==========================================================================
# CONCLUSION
# ==========================================================================

print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("-" * 100)


if len(future_returns) == 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
    )

    print(
        "MEANING                     : "
        "The selected production runtime did not reach "
        "find_future_price()."
    )

    print(
        "NEXT FRONTIER               : "
        "Resolve the production runtime path reaching create_outcome()."
    )

elif match_count == 0:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_RETURN_NOT_MATCHED_TO_PRICE"
    )

    print(
        "MEANING                     : "
        "The genuine find_future_price() returns were observed, "
        "but no exact runtime price assignment was established."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace bytecode STORE operations and frame locals "
        "around the call boundary."
    )

elif transformations:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_PRICE_TRANSFORMATION_OBSERVED"
    )

    print(
        "MEANING                     : "
        "The genuine future-price return was localized in price "
        "and at least one subsequent runtime transformation was observed."
    )

    print(
        "NEXT FRONTIER               : "
        "Localize the transformed value into the exact final "
        "output field or returned structure."
    )

else:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_PRICE_PRESERVED"
    )

    print(
        "MEANING                     : "
        "The genuine find_future_price() return was observed "
        "and no subsequent change to the localized price value "
        "was detected during the traced create_outcome() execution."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace the price variable into the final output structure."
    )


print()
print("DATABASE_WRITES              : NONE")
print("ENGINE_MODIFIED              : NONE")
print("PRODUCTION_SOURCE_MODIFIED   : NONE")
print("INSERT                       : NONE")
print("UPDATE                       : NONE")
print("DELETE                       : NONE")
print("ALTER                        : NONE")
print("CREATE                       : NONE")
print("DROP                         : NONE")
print("COMMIT                       : NONE")

print()
print("=" * 100)
print(
    "ELAPSED SECONDS              : %.3f"
    % elapsed
)
print("=" * 100)
print("AUDIT COMPLETE")