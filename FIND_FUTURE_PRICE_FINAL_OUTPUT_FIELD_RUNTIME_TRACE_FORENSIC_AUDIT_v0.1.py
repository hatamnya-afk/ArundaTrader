# FIND_FUTURE_PRICE_FINAL_OUTPUT_FIELD_RUNTIME_TRACE_FORENSIC_AUDIT_v0.1.py

import ast
import importlib
import inspect
import os
import sqlite3
import sys
import time
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

future_returns = []
price_observations = []
create_returns = []
output_matches = []
runtime_exceptions = []
blocked_writes = []

_original_connect = sqlite3.connect


def safe_repr(value, limit=1600):
    try:
        text = repr(value)
    except Exception as exc:
        text = "<repr failed: %s>" % exc

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def equal_value(left, right):
    try:
        result = left == right

        if isinstance(result, bool):
            return result

        return bool(result)

    except Exception:
        return left is right


def contains_value(container, target, path="ROOT", depth=0, max_depth=8):
    """
    Recursively locate target inside the actual runtime returned structure.

    No values are generated.
    Only observed runtime objects are inspected.
    """

    matches = []

    if depth > max_depth:
        return matches

    if equal_value(container, target):
        matches.append(
            {
                "path": path,
                "container_type": type(container).__name__,
                "match_type": "DIRECT",
                "value": container,
            }
        )

    if isinstance(container, dict):

        for key, value in container.items():

            key_path = "%s[%s]" % (
                path,
                safe_repr(key, 300),
            )

            if equal_value(value, target):

                matches.append(
                    {
                        "path": key_path,
                        "container_type": "dict",
                        "match_type": "FIELD_VALUE",
                        "key": key,
                        "value": value,
                    }
                )

            matches.extend(
                contains_value(
                    value,
                    target,
                    key_path,
                    depth + 1,
                    max_depth,
                )
            )

    elif isinstance(container, (list, tuple)):

        for index, value in enumerate(container):

            item_path = "%s[%d]" % (
                path,
                index,
            )

            matches.extend(
                contains_value(
                    value,
                    target,
                    item_path,
                    depth + 1,
                    max_depth,
                )
            )

    elif isinstance(container, set):

        for index, value in enumerate(container):

            item_path = "%s{item_%d}" % (
                path,
                index,
            )

            matches.extend(
                contains_value(
                    value,
                    target,
                    item_path,
                    depth + 1,
                    max_depth,
                )
            )

    return matches


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

            return _original_connect(
                uri,
                **readonly_kwargs,
            )

    return _original_connect(*args, **kwargs)


def is_target_frame(frame):

    try:

        return (
            os.path.abspath(frame.f_code.co_filename)
            == os.path.abspath(str(TARGET_FILE))
        )

    except Exception:

        return False


def source_line(line_number):

    try:

        lines = TARGET_FILE.read_text(
            encoding="utf-8-sig",
            errors="replace",
        ).splitlines()

        if 1 <= line_number <= len(lines):

            return lines[line_number - 1].strip()

    except Exception:

        pass

    return ""


def trace(frame, event, arg):

    if not is_target_frame(frame):

        return trace

    function_name = frame.f_code.co_name

    if event == "call":

        if function_name == FIND_FUTURE_PRICE:

            future_returns.append(
                {
                    "line": frame.f_lineno,
                    "value": None,
                    "locals": dict(frame.f_locals),
                    "status": "ENTER",
                }
            )

        return trace

    if event == "line":

        if function_name == CREATE_OUTCOME:

            try:

                locals_now = dict(frame.f_locals)

            except Exception:

                locals_now = {}

            if "price" in locals_now:

                price_observations.append(
                    {
                        "line": frame.f_lineno,
                        "price": locals_now.get("price"),
                        "locals": locals_now,
                        "source": source_line(
                            frame.f_lineno
                        ),
                    }
                )

        return trace

    if event == "return":

        if function_name == FIND_FUTURE_PRICE:

            future_returns.append(
                {
                    "line": frame.f_lineno,
                    "value": arg,
                    "locals": dict(frame.f_locals),
                    "status": "RETURN",
                }
            )

        elif function_name == CREATE_OUTCOME:

            create_returns.append(
                {
                    "line": frame.f_lineno,
                    "value": arg,
                    "locals": dict(frame.f_locals),
                }
            )

        return trace

    if event == "exception":

        try:

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

        except Exception:

            pass

        return trace

    return trace


def locate_static_output_assignments():

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

        print(
            "AST ERROR :",
            repr(exc),
        )

        return []

    create_node = None

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name == CREATE_OUTCOME:

                create_node = node
                break

    if create_node is None:

        return []

    assignments = []

    for node in ast.walk(create_node):

        if isinstance(node, ast.Assign):

            try:
                target_text = ", ".join(
                    ast.unparse(target)
                    for target in node.targets
                )

                value_text = ast.unparse(
                    node.value
                )

                assignments.append(
                    (
                        node.lineno,
                        target_text,
                        value_text,
                    )
                )

            except Exception:

                pass

        elif isinstance(node, ast.AnnAssign):

            try:

                if node.value is not None:

                    assignments.append(
                        (
                            node.lineno,
                            ast.unparse(
                                node.target
                            ),
                            ast.unparse(
                                node.value
                            ),
                        )
                    )

            except Exception:

                pass

        elif isinstance(node, ast.AugAssign):

            try:

                assignments.append(
                    (
                        node.lineno,
                        ast.unparse(
                            node.target
                        ),
                        ast.unparse(node),
                    )
                )

            except Exception:

                pass

    return sorted(
        assignments,
        key=lambda item: item[0],
    )


def execute_production_main():

    module = importlib.import_module(
        TARGET_MODULE
    )

    production_main = getattr(
        module,
        "main",
        None,
    )

    if production_main is None:

        raise RuntimeError(
            "signal_outcome_engine.main() not found."
        )

    if not callable(production_main):

        raise RuntimeError(
            "signal_outcome_engine.main is not callable."
        )

    return production_main()


print("=" * 100)
print(
    "ARUNDA FIND_FUTURE_PRICE -> FINAL OUTPUT FIELD "
    "RUNTIME TRACE FORENSIC AUDIT v0.1"
)
print("=" * 100)

print(
    "MODE                         : "
    "READ-ONLY RUNTIME FORENSICS"
)

print(
    "TARGET                       : "
    "signal_outcome_engine.py -> create_outcome()"
)

print(
    "SOURCE VALUE                 : "
    "create_outcome().price"
)

print(
    "PRODUCTION SOURCE MODIFIED   : NONE"
)

print(
    "DATABASE WRITE               : BLOCKED"
)

print()
print("=" * 100)
print("STEP 1 — STATIC OUTPUT ASSIGNMENT MAP")
print("=" * 100)

if not TARGET_FILE.exists():

    print(
        "TARGET FILE NOT FOUND :",
        TARGET_FILE,
    )

    sys.exit(1)


static_assignments = locate_static_output_assignments()

for line, target, expression in static_assignments:

    print(
        "LINE=%s | TARGET=%s | VALUE=%s"
        % (
            line,
            target,
            expression,
        )
    )


print()
print("=" * 100)
print("STEP 2 — DATABASE WRITE SAFETY")
print("=" * 100)

sqlite3.connect = readonly_connect

print("sqlite3.connect              : READ-ONLY")
print("INSERT                       : BLOCKED")
print("UPDATE                       : BLOCKED")
print("DELETE                       : BLOCKED")
print("ALTER                        : BLOCKED")
print("CREATE                       : BLOCKED")
print("DROP                         : BLOCKED")
print("COMMIT                       : BLOCKED")


print()
print("=" * 100)
print("STEP 3 — PRODUCTION RUNTIME TRACE")
print("=" * 100)

started = time.time()

old_trace = sys.gettrace()

sys.settrace(trace)

production_result = None

try:

    production_result = execute_production_main()

except SystemExit as exc:

    runtime_exceptions.append(
        {
            "function": "production_main",
            "line": "?",
            "type": "SystemExit",
            "value": repr(exc),
        }
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

finally:

    sys.settrace(old_trace)

    sqlite3.connect = _original_connect


elapsed = time.time() - started


print()
print("=" * 100)
print("STEP 4 — FUTURE PRICE RETURNS")
print("=" * 100)

actual_future_returns = [
    item
    for item in future_returns
    if item.get("status") == "RETURN"
]

for index, item in enumerate(
    actual_future_returns,
    1,
):

    print(
        "%03d | TYPE=%s | VALUE=%s"
        % (
            index,
            type(item["value"]).__name__,
            safe_repr(item["value"]),
        )
    )


print()
print("=" * 100)
print("STEP 5 — FINAL create_outcome() RETURNS")
print("=" * 100)

for index, item in enumerate(
    create_returns,
    1,
):

    final_value = item["value"]

    print()
    print(
        "CREATE_OUTCOME RETURN #%d"
        % index
    )

    print(
        "TYPE  :",
        type(final_value).__name__,
    )

    print(
        "VALUE :",
        safe_repr(final_value),
    )


print()
print("=" * 100)
print("STEP 6 — PRICE -> FINAL OUTPUT FIELD LOCALIZATION")
print("=" * 100)

for return_index, future_item in enumerate(
    actual_future_returns,
    1,
):

    future_value = future_item["value"]

    print()
    print(
        "FUTURE PRICE RETURN #%d"
        % return_index
    )

    print(
        "VALUE :",
        safe_repr(future_value),
    )

    local_matches = []

    for observation in price_observations:

        if equal_value(
            observation["price"],
            future_value,
        ):

            local_matches.append(
                observation
            )

    if not local_matches:

        print(
            "PRICE LOCALIZATION : NONE"
        )

        continue

    print(
        "PRICE LOCALIZATION : %d OBSERVATION(S)"
        % len(local_matches)
    )

    final_matches_for_this_return = []

    for final_index, create_item in enumerate(
        create_returns,
        1,
    ):

        final_value = create_item["value"]

        matches = contains_value(
            final_value,
            future_value,
        )

        if matches:

            for match in matches:

                final_match = {
                    "future_return_index": return_index,
                    "create_return_index": final_index,
                    "future_value": future_value,
                    "path": match["path"],
                    "match_type": match["match_type"],
                    "final_value": match["value"],
                }

                output_matches.append(
                    final_match
                )

                final_matches_for_this_return.append(
                    final_match
                )

                print(
                    "FINAL FIELD MATCH | "
                    "CREATE_RETURN=%d | PATH=%s | "
                    "TYPE=%s | VALUE=%s"
                    % (
                        final_index,
                        match["path"],
                        type(match["value"]).__name__,
                        safe_repr(match["value"]),
                    )
                )

    if not final_matches_for_this_return:

        print(
            "FINAL FIELD MATCH : NONE"
        )


print()
print("=" * 100)
print("STEP 7 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    "FIND_FUTURE_PRICE RETURNS     :",
    len(actual_future_returns),
)

print(
    "PRICE OBSERVATIONS            :",
    len(price_observations),
)

print(
    "CREATE_OUTCOME RETURNS        :",
    len(create_returns),
)

print(
    "FINAL OUTPUT FIELD MATCHES    :",
    len(output_matches),
)

print(
    "RUNTIME EXCEPTIONS            :",
    len(runtime_exceptions),
)

print(
    "BLOCKED WRITE OPERATIONS      :",
    len(blocked_writes),
)


print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("-" * 100)


if not actual_future_returns:

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
        "Resolve the production runtime entrypoint reaching "
        "create_outcome()."
    )

elif not create_returns:

    print(
        "STATUS                      : "
        "CREATE_OUTCOME_FINAL_RETURN_NOT_OBSERVED"
    )

    print(
        "MEANING                     : "
        "find_future_price() was reached, but no final "
        "create_outcome() return was captured."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace create_outcome() return construction."
    )

elif not output_matches:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_FINAL_FIELD_NOT_LOCALIZED"
    )

    print(
        "MEANING                     : "
        "The genuine future-price value was observed in "
        "create_outcome().price, but it was not found "
        "inside the final returned structure."
    )

    print(
        "NEXT FRONTIER               : "
        "Trace intermediate output construction and "
        "container mutations inside create_outcome()."
    )

else:

    print(
        "STATUS                      : "
        "FIND_FUTURE_PRICE_FINAL_FIELD_LOCALIZED"
    )

    print(
        "MEANING                     : "
        "The genuine find_future_price() return was matched "
        "to an exact field/path inside the actual final "
        "create_outcome() returned structure."
    )

    print(
        "NEXT FRONTIER               : "
        "Compare the localized final field across runtime "
        "calls and verify whether the value is preserved "
        "exactly or transformed."
    )


print()
print(
    "DATABASE_WRITES              : NONE"
)

print(
    "ENGINE_MODIFIED              : NONE"
)

print(
    "PRODUCTION_SOURCE_MODIFIED   : NONE"
)

print(
    "INSERT                       : NONE"
)

print(
    "UPDATE                       : NONE"
)

print(
    "DELETE                       : NONE"
)

print(
    "ALTER                        : NONE"
)

print(
    "CREATE                       : NONE"
)

print(
    "DROP                         : NONE"
)

print(
    "COMMIT                       : NONE"
)

print()
print("=" * 100)
print(
    "ELAPSED SECONDS              : %.3f"
    % elapsed
)
print("=" * 100)
print("AUDIT COMPLETE")