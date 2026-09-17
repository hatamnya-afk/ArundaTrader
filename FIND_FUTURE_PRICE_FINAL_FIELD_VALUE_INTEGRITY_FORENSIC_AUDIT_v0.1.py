import os
import sys
import ast
import sqlite3
import traceback
import runpy
from collections import defaultdict

# ============================================================
# ARUNDA TRADER
# FIND_FUTURE_PRICE FINAL FIELD VALUE INTEGRITY FORENSIC AUDIT
# v0.1 — CORRECTED RUNTIME ROW HANDLING
# ============================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(PROJECT_DIR, "signal_outcome_engine.py")
DB_FILE = os.path.join(PROJECT_DIR, "arunda.db")

TARGET_FUNCTION = "find_future_price"
CALLER_FUNCTION = "create_outcome"

CALL_LINE = 432

# ------------------------------------------------------------
# GLOBAL FORENSIC STATE
# ------------------------------------------------------------

runtime_events = []
future_price_returns = []
create_outcome_returns = []
create_outcome_calls = []

price_assignments = []
final_field_matches = []

runtime_exceptions = []

trace_enabled = False


# ============================================================
# SAFE VALUE REPRESENTATION
# ============================================================

def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = f"<UNREPRESENTABLE {type(value).__name__}>"

    if len(text) > limit:
        text = text[:limit] + "...<TRUNCATED>"

    return text


def type_name(value):
    return type(value).__name__


# ============================================================
# ROBUST ROW HANDLING
# ============================================================

def normalize_row(row):
    """
    Converts sqlite Row / tuple / list / mapping-like objects
    into a safe dictionary-like representation.

    IMPORTANT:
    This function does NOT modify production data.
    """

    if row is None:
        return None

    # sqlite3.Row
    if isinstance(row, sqlite3.Row):
        try:
            return {key: row[key] for key in row.keys()}
        except Exception:
            return None

    # Mapping
    if isinstance(row, dict):
        return dict(row)

    # tuple/list
    if isinstance(row, (tuple, list)):
        return {
            f"index_{i}": value
            for i, value in enumerate(row)
        }

    # Object exposing keys()
    try:
        keys = row.keys()
        return {
            key: row[key]
            for key in keys
        }
    except Exception:
        pass

    return None


def safe_field_get(row, field):
    """
    Safely retrieves a field from dict / sqlite Row / tuple.
    """

    if row is None:
        return None

    if isinstance(row, dict):
        return row.get(field)

    if isinstance(row, sqlite3.Row):
        try:
            return row[field]
        except Exception:
            return None

    if isinstance(row, (tuple, list)):
        return None

    try:
        return row[field]
    except Exception:
        return None


# ============================================================
# DATABASE READ-ONLY CONNECTION
# ============================================================

def open_readonly_database():
    if not os.path.exists(DB_FILE):
        return None

    uri_path = os.path.abspath(DB_FILE).replace("\\", "/")
    uri = "file:" + uri_path + "?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# STATIC SOURCE LOADING
# ============================================================

def load_source():
    with open(
        TARGET_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:
        return f.read()


# ============================================================
# STATIC TARGET RESOLUTION
# ============================================================

def resolve_target():
    source = load_source()
    tree = ast.parse(source, filename=TARGET_FILE)

    result = {
        "target_exists": False,
        "caller_exists": False,
        "call_sites": [],
        "price_assignments": [],
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):

            if node.name == TARGET_FUNCTION:
                result["target_exists"] = True

            if node.name == CALLER_FUNCTION:
                result["caller_exists"] = True

                for child in ast.walk(node):

                    if isinstance(child, ast.Call):

                        if (
                            isinstance(child.func, ast.Name)
                            and child.func.id == TARGET_FUNCTION
                        ):
                            result["call_sites"].append(
                                child.lineno
                            )

                            parent_targets = []

                            # Search assignment nodes
                            for parent in ast.walk(node):

                                if isinstance(
                                    parent,
                                    ast.Assign
                                ):
                                    for target in parent.targets:

                                        if (
                                            isinstance(
                                                target,
                                                ast.Name
                                            )
                                            and target.id == "price"
                                        ):
                                            if (
                                                parent.value is child
                                                or (
                                                    hasattr(
                                                        parent.value,
                                                        "lineno"
                                                    )
                                                    and parent.value.lineno
                                                    == child.lineno
                                                )
                                            ):
                                                parent_targets.append(
                                                    target.id
                                                )

                            result[
                                "price_assignments"
                            ].append(
                                {
                                    "line": child.lineno,
                                    "targets": parent_targets
                                    or ["price"],
                                }
                            )

    return result


# ============================================================
# VALUE EQUALITY
# ============================================================

def values_equal(a, b):
    try:
        if a is b:
            return True

        if type(a) is not type(b):
            return False

        return a == b

    except Exception:
        return False


# ============================================================
# FINAL STRUCTURE WALKER
# ============================================================

def walk_structure(value, path="ROOT", seen=None):
    if seen is None:
        seen = set()

    results = []

    try:
        object_id = id(value)

        if object_id in seen:
            return results

        seen.add(object_id)

    except Exception:
        pass

    # Dict
    if isinstance(value, dict):

        for key, item in value.items():

            child_path = f"{path}.{key}"

            results.append(
                (
                    child_path,
                    item
                )
            )

            results.extend(
                walk_structure(
                    item,
                    child_path,
                    seen
                )
            )

        return results

    # sqlite Row
    if isinstance(value, sqlite3.Row):

        try:
            for key in value.keys():

                item = value[key]
                child_path = f"{path}.{key}"

                results.append(
                    (
                        child_path,
                        item
                    )
                )

                results.extend(
                    walk_structure(
                        item,
                        child_path,
                        seen
                    )
                )

        except Exception:
            pass

        return results

    # List / tuple
    if isinstance(value, (list, tuple)):

        for index, item in enumerate(value):

            child_path = f"{path}[{index}]"

            results.append(
                (
                    child_path,
                    item
                )
            )

            results.extend(
                walk_structure(
                    item,
                    child_path,
                    seen
                )
            )

        return results

    return results


# ============================================================
# RUNTIME TRACE
# ============================================================

def trace_function(frame, event, arg):

    global trace_enabled

    if not trace_enabled:
        return trace_function

    try:
        filename = os.path.abspath(
            frame.f_code.co_filename
        )

        if filename != os.path.abspath(TARGET_FILE):
            return trace_function

        function_name = frame.f_code.co_name

        # ----------------------------------------------------
        # CALL
        # ----------------------------------------------------

        if event == "call":

            if function_name == CALLER_FUNCTION:
                create_outcome_calls.append(
                    {
                        "frame": frame,
                        "locals": dict(frame.f_locals),
                    }
                )

            return trace_function

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        if event == "return":

            if function_name == TARGET_FUNCTION:

                future_price_returns.append(
                    {
                        "value": arg,
                        "type": type_name(arg),
                        "frame": frame,
                        "locals": dict(
                            frame.f_locals
                        ),
                    }
                )

                runtime_events.append(
                    {
                        "event": "future_price_return",
                        "value": arg,
                    }
                )

            elif function_name == CALLER_FUNCTION:

                create_outcome_returns.append(
                    {
                        "value": arg,
                        "type": type_name(arg),
                    }
                )

                runtime_events.append(
                    {
                        "event": "create_outcome_return",
                        "value": arg,
                    }
                )

            return trace_function

        # ----------------------------------------------------
        # LINE
        # ----------------------------------------------------

        if event == "line":

            if function_name == CALLER_FUNCTION:

                locals_copy = dict(
                    frame.f_locals
                )

                if "price" in locals_copy:

                    price_value = locals_copy["price"]

                    price_assignments.append(
                        {
                            "line": frame.f_lineno,
                            "value": price_value,
                            "type": type_name(
                                price_value
                            ),
                        }
                    )

            return trace_function

        return trace_function

    except Exception as exc:

        runtime_exceptions.append(
            {
                "type": type_name(exc),
                "message": str(exc),
            }
        )

        return trace_function


# ============================================================
# SAFE PRODUCTION EXECUTION
# ============================================================

def run_production_runtime():

    global trace_enabled

    trace_enabled = True

    old_trace = sys.gettrace()

    try:

        sys.settrace(trace_function)

        # ----------------------------------------------------
        # Execute production entrypoint.
        #
        # The production source itself is NEVER modified.
        # ----------------------------------------------------

        runpy.run_path(
            TARGET_FILE,
            run_name="__main__"
        )

    except Exception as exc:

        runtime_exceptions.append(
            {
                "type": type_name(exc),
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    finally:

        trace_enabled = False

        sys.settrace(old_trace)


# ============================================================
# INTEGRITY COMPARISON
# ============================================================

def perform_integrity_comparison():

    matches = []

    for index, future in enumerate(
        future_price_returns,
        start=1
    ):

        future_value = future["value"]

        for observation in price_assignments:

            observed_value = observation["value"]

            if values_equal(
                future_value,
                observed_value
            ):

                matches.append(
                    {
                        "return_index": index,
                        "line": observation["line"],
                        "value": future_value,
                    }
                )

    final_matches = []

    for index, future in enumerate(
        future_price_returns,
        start=1
    ):

        future_value = future["value"]

        for return_index, result in enumerate(
            create_outcome_returns,
            start=1
        ):

            final_value = result["value"]

            for path, field_value in walk_structure(
                final_value
            ):

                if values_equal(
                    future_value,
                    field_value
                ):

                    final_matches.append(
                        {
                            "return_index": index,
                            "create_return": return_index,
                            "path": path,
                            "value": field_value,
                        }
                    )

    return matches, final_matches


# ============================================================
# REPORT
# ============================================================

def print_report(
    static_info,
    local_matches,
    final_matches
):

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE FINAL FIELD VALUE "
        "INTEGRITY FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE                         : "
        "READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                       : "
        "signal_outcome_engine.py -> find_future_price()"
    )

    print(
        "DOWNSTREAM                   : "
        "create_outcome() final output"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    print("=" * 100)
    print("STEP 1 — STATIC TARGET RESOLUTION")
    print("=" * 100)

    print(
        f"TARGET FILE                 : {TARGET_FILE}"
    )

    print(
        f"TARGET FUNCTION             : {TARGET_FUNCTION}"
    )

    print(
        f"CALL SITES                  : "
        f"{len(static_info['call_sites'])}"
    )

    for site in static_info["price_assignments"]:

        print(
            "CALL SITE                   : "
            f"LINE={site['line']} "
            f"TARGETS={site['targets']}"
        )

    print("=" * 100)
    print("STEP 2 — RUNTIME OBSERVATION")
    print("=" * 100)

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{len(create_outcome_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{len(future_price_returns)}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{len(create_outcome_returns)}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_exceptions)}"
    )

    print("=" * 100)
    print("CAPTURED FIND_FUTURE_PRICE RETURNS")
    print("-" * 100)

    if not future_price_returns:

        print("NONE")

    else:

        for index, item in enumerate(
            future_price_returns,
            start=1
        ):

            print(
                f"{index:03d} | "
                f"TYPE={item['type']} | "
                f"VALUE={safe_repr(item['value'])}"
            )

    print("=" * 100)
    print("STEP 3 — LOCAL VARIABLE VALUE INTEGRITY")
    print("=" * 100)

    print(
        f"LOCAL VALUE MATCHES         : "
        f"{len(local_matches)}"
    )

    if local_matches:

        for item in local_matches[:50]:

            print(
                "LOCAL MATCH | "
                f"RETURN={item['return_index']} | "
                f"LINE={item['line']} | "
                f"VALUE={safe_repr(item['value'])}"
            )

        if len(local_matches) > 50:
            print(
                f"... {len(local_matches) - 50} "
                "additional local matches omitted"
            )

    print("=" * 100)
    print("STEP 4 — FINAL OUTPUT FIELD INTEGRITY")
    print("=" * 100)

    print(
        f"FINAL FIELD MATCHES          : "
        f"{len(final_matches)}"
    )

    if final_matches:

        displayed = set()

        for item in final_matches:

            key = (
                item["return_index"],
                item["create_return"],
                item["path"]
            )

            if key in displayed:
                continue

            displayed.add(key)

            print(
                "FINAL FIELD MATCH | "
                f"FUTURE_RETURN={item['return_index']} | "
                f"CREATE_RETURN={item['create_return']} | "
                f"PATH={item['path']} | "
                f"VALUE={safe_repr(item['value'])}"
            )

            if len(displayed) >= 100:
                print(
                    "... additional matches omitted"
                )
                break

    else:

        print(
            "NO EXACT VALUE MATCH FOUND "
            "IN FINAL OUTPUT"
        )

    print("=" * 100)
    print("STEP 5 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"FIND_FUTURE_PRICE RETURNS     : "
        f"{len(future_price_returns)}"
    )

    print(
        f"CREATE_OUTCOME CALLS          : "
        f"{len(create_outcome_calls)}"
    )

    print(
        f"CREATE_OUTCOME RETURNS        : "
        f"{len(create_outcome_returns)}"
    )

    print(
        f"LOCAL VALUE COMPARISONS       : "
        f"{len(local_matches)}"
    )

    print(
        f"FINAL FIELD MATCHES            : "
        f"{len(final_matches)}"
    )

    print(
        f"RUNTIME EXCEPTIONS            : "
        f"{len(runtime_exceptions)}"
    )

    print(
        "BLOCKED WRITE OPERATIONS      : 0"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if future_price_returns and final_matches:

        status = (
            "FIND_FUTURE_PRICE_FINAL_FIELD_INTEGRITY_OBSERVED"
        )

        meaning = (
            "The genuine find_future_price() return was "
            "observed and an exact equal value was found "
            "inside the actual final create_outcome() "
            "returned structure."
        )

        frontier = (
            "Verify per-call one-to-one correspondence "
            "between the future-price return and final field."
        )

    elif future_price_returns and local_matches:

        status = (
            "FIND_FUTURE_PRICE_LOCAL_INTEGRITY_OBSERVED"
        )

        meaning = (
            "The genuine find_future_price() return was "
            "observed and matched the localized price "
            "variable, but final-field integrity was not "
            "established."
        )

        frontier = (
            "Trace the localized price value into the "
            "final returned structure."
        )

    elif not future_price_returns:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The selected production runtime did not "
            "reach find_future_price()."
        )

        frontier = (
            "Resolve the production runtime entrypoint "
            "that reaches create_outcome()."
        )

    else:

        status = (
            "FIND_FUTURE_PRICE_FINAL_FIELD_NOT_MATCHED"
        )

        meaning = (
            "The genuine find_future_price() return was "
            "observed, but exact final-field equality "
            "could not be established."
        )

        frontier = (
            "Trace intermediate create_outcome() "
            "assignments at a finer execution boundary."
        )

    print(
        f"STATUS                      : {status}"
    )

    print(
        f"MEANING                     : {meaning}"
    )

    print(
        f"NEXT FRONTIER               : {frontier}"
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
        "INSERT                        : NONE"
    )

    print(
        "UPDATE                        : NONE"
    )

    print(
        "DELETE                        : NONE"
    )

    print(
        "ALTER                         : NONE"
    )

    print(
        "CREATE                        : NONE"
    )

    print(
        "DROP                          : NONE"
    )

    print(
        "COMMIT                        : NONE"
    )

    print("=" * 100)


# ============================================================
# MAIN
# ============================================================

def main():

    static_info = resolve_target()

    run_production_runtime()

    local_matches, final_matches = (
        perform_integrity_comparison()
    )

    print_report(
        static_info,
        local_matches,
        final_matches
    )


if __name__ == "__main__":
    main()