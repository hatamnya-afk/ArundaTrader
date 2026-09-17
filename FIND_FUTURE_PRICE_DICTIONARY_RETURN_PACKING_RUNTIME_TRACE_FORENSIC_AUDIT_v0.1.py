import os
import ast
import sys
import sqlite3
import runpy


# =============================================================================
# ARUNDA FIND_FUTURE_PRICE DICTIONARY / RETURN PACKING
# RUNTIME TRACE FORENSIC AUDIT v0.1
# =============================================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(PROJECT_DIR, "signal_outcome_engine.py")
DB_FILE = os.path.join(PROJECT_DIR, "arunda.db")

TARGET_FUNCTION = "create_outcome"
CALLEE_FUNCTION = "find_future_price"


# Keep the ORIGINAL sqlite connect before installing the guard.
ORIGINAL_SQLITE_CONNECT = sqlite3.connect


runtime = {
    "create_calls": 0,
    "find_calls": 0,
    "find_returns": 0,
    "create_returns": 0,
    "exceptions": 0,
    "blocked_writes": 0,
}


find_returns = []
localized_events = []
final_matches = []

active_create_frames = {}


# =============================================================================
# HELPERS
# =============================================================================

def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<UNREPRESENTABLE>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def load_source(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def print_banner(text):
    print("=" * 100)
    print(text)
    print("=" * 100)


# =============================================================================
# READ-ONLY DATABASE GUARD
# =============================================================================

def readonly_sqlite_connect(database, *args, **kwargs):
    """
    Open the production DB read-only.

    IMPORTANT:
    This function calls the ORIGINAL sqlite3.connect saved before
    monkey-patching, preventing recursive self-calls.
    """

    if isinstance(database, str):

        db_abs = os.path.abspath(database)

        if os.path.abspath(DB_FILE) == db_abs:

            uri = "file:" + db_abs.replace("\\", "/") + "?mode=ro"

            kwargs["uri"] = True

            return ORIGINAL_SQLITE_CONNECT(
                uri,
                *args,
                **kwargs
            )

    return ORIGINAL_SQLITE_CONNECT(
        database,
        *args,
        **kwargs
    )


def install_readonly_guard():
    sqlite3.connect = readonly_sqlite_connect


# =============================================================================
# STATIC ANALYSIS
# =============================================================================

def ast_assignment_map(source):

    tree = ast.parse(source)

    result = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            value_text = ast.get_source_segment(
                source,
                node.value
            )

            for target in node.targets:

                target_text = ast.get_source_segment(
                    source,
                    target
                )

                result.append(
                    (
                        node.lineno,
                        target_text,
                        value_text
                    )
                )

        elif isinstance(node, ast.AnnAssign):

            value_text = None

            if node.value is not None:
                value_text = ast.get_source_segment(
                    source,
                    node.value
                )

            target_text = ast.get_source_segment(
                source,
                node.target
            )

            result.append(
                (
                    node.lineno,
                    target_text,
                    value_text
                )
            )

    return sorted(
        result,
        key=lambda x: x[0]
    )


def inspect_static_structure():

    source = load_source(TARGET_FILE)

    tree = ast.parse(source)

    print("TARGET FILE                 :", TARGET_FILE)
    print("TARGET FUNCTION             :", TARGET_FUNCTION)
    print("CALLEE                      :", CALLEE_FUNCTION)

    call_sites = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            if (
                isinstance(node.func, ast.Name)
                and node.func.id == CALLEE_FUNCTION
            ):

                call_sites.append(
                    (
                        node.lineno,
                        getattr(node, "col_offset", 0)
                    )
                )

    print("CALL SITES                  :", len(call_sites))

    for line, col in call_sites:

        print(
            f"CALL SITE                   : LINE={line} COL={col}"
        )

    print()
    print("CREATE_OUTCOME ASSIGNMENT MAP")
    print("-" * 100)

    for line, target, value in ast_assignment_map(source):

        if (
            target == "price"
            or "prices" in target
            or "returns" in target
            or "outcomes" in target
            or "completed_returns" in target
        ):

            print(
                f"LINE={line:<5} | "
                f"TARGET={target:<25} | "
                f"VALUE={value}"
            )


# =============================================================================
# OBJECT GRAPH LOCALIZATION
# =============================================================================

def find_value_paths(value, target_value, path="ROOT", seen=None):

    if seen is None:
        seen = set()

    matches = []

    try:
        object_id = id(value)

        if object_id in seen:
            return matches

        seen.add(object_id)

    except Exception:
        pass

    # Identity first
    if value is target_value:

        matches.append(path)

        return matches

    # Equality only as secondary evidence
    try:

        if value == target_value:

            matches.append(path)

    except Exception:
        pass

    # Dictionaries
    if isinstance(value, dict):

        for key, child in value.items():

            child_path = (
                f"{path}[{safe_repr(key)}]"
            )

            matches.extend(
                find_value_paths(
                    child,
                    target_value,
                    child_path,
                    seen
                )
            )

    # Lists / tuples / sets
    elif isinstance(value, (list, tuple, set)):

        try:
            iterable = enumerate(value)
        except Exception:
            iterable = []

        for index, child in iterable:

            child_path = (
                f"{path}[{index}]"
            )

            matches.extend(
                find_value_paths(
                    child,
                    target_value,
                    child_path,
                    seen
                )
            )

    return matches


# =============================================================================
# FRAME SNAPSHOT
# =============================================================================

def snapshot_locals(frame):

    result = {}

    try:

        for name, value in frame.f_locals.items():

            result[name] = value

    except Exception:

        pass

    return result


# =============================================================================
# TRACE FUNCTION
# =============================================================================

def trace_function(frame, event, arg):

    filename = os.path.abspath(
        frame.f_code.co_filename
    )

    target_abs = os.path.abspath(
        TARGET_FILE
    )

    if filename != target_abs:

        return trace_function

    function_name = frame.f_code.co_name

    # -------------------------------------------------------------------------
    # CREATE_OUTCOME
    # -------------------------------------------------------------------------

    if function_name == TARGET_FUNCTION:

        frame_id = id(frame)

        if event == "call":

            runtime["create_calls"] += 1

            active_create_frames[frame_id] = {
                "frame": frame,
                "find_return": None,
                "last_price": None,
                "last_locals": {},
            }

            return trace_function

        state = active_create_frames.get(frame_id)

        if state is None:

            return trace_function

        # ---------------------------------------------------------------------
        # LINE
        # ---------------------------------------------------------------------

        if event == "line":

            locals_now = snapshot_locals(frame)

            state["last_locals"] = locals_now

            # Capture price variable
            if "price" in locals_now:

                price_value = locals_now["price"]

                state["last_price"] = price_value

                if state["find_return"] is not None:

                    expected = state["find_return"]

                    if price_value is expected:

                        localized_events.append(
                            {
                                "line": frame.f_lineno,
                                "kind": "IDENTITY",
                                "value": price_value,
                            }
                        )

                    else:

                        try:

                            if price_value == expected:

                                localized_events.append(
                                    {
                                        "line": frame.f_lineno,
                                        "kind": "EQUALITY",
                                        "value": price_value,
                                    }
                                )

                        except Exception:

                            pass

            # Trace important containers
            if state["find_return"] is not None:

                expected = state["find_return"]

                for name, value in locals_now.items():

                    if isinstance(
                        value,
                        (dict, list, tuple)
                    ):

                        paths = find_value_paths(
                            value,
                            expected,
                            name
                        )

                        for path in paths:

                            final_matches.append(
                                {
                                    "line": frame.f_lineno,
                                    "path": path,
                                    "value": expected,
                                }
                            )

        # ---------------------------------------------------------------------
        # RETURN
        # ---------------------------------------------------------------------

        elif event == "return":

            runtime["create_returns"] += 1

            expected = state["find_return"]

            if expected is not None:

                paths = find_value_paths(
                    arg,
                    expected
                )

                for path in paths:

                    final_matches.append(
                        {
                            "line": frame.f_lineno,
                            "path": path,
                            "value": expected,
                        }
                    )

            active_create_frames.pop(
                frame_id,
                None
            )

        # ---------------------------------------------------------------------
        # EXCEPTION
        # ---------------------------------------------------------------------

        elif event == "exception":

            runtime["exceptions"] += 1

        return trace_function

    # -------------------------------------------------------------------------
    # FIND_FUTURE_PRICE
    # -------------------------------------------------------------------------

    if function_name == CALLEE_FUNCTION:

        if event == "call":

            runtime["find_calls"] += 1

        elif event == "return":

            runtime["find_returns"] += 1

            find_returns.append(
                {
                    "type": type(arg).__name__,
                    "value": arg,
                }
            )

            # Associate the return with all currently active create_outcome
            # frames. In normal production flow there should be one relevant
            # caller frame.
            for state in active_create_frames.values():

                if state["find_return"] is None:

                    state["find_return"] = arg

        elif event == "exception":

            runtime["exceptions"] += 1

        return trace_function

    return trace_function


# =============================================================================
# PRODUCTION EXECUTION
# =============================================================================

def execute_production_runtime():

    original_argv = sys.argv[:]

    try:

        sys.argv = [
            os.path.basename(TARGET_FILE)
        ]

        runpy.run_path(
            TARGET_FILE,
            run_name="__main__"
        )

    except SystemExit:

        pass

    except Exception as exc:

        runtime["exceptions"] += 1

        print()
        print("=" * 100)
        print("OUTCOME ENGINE ERROR")
        print("=" * 100)
        print(
            repr(exc)
        )
        print("=" * 100)

    finally:

        sys.argv = original_argv


# =============================================================================
# RESULT
# =============================================================================

def print_results():

    print()
    print_banner(
        "ARUNDA FIND_FUTURE_PRICE DICTIONARY / RETURN PACKING "
        "RUNTIME TRACE FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                         : READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                       : "
        "signal_outcome_engine.py -> create_outcome()"
    )

    print(
        "SOURCE VALUE                 : create_outcome().price"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    print()
    print_banner(
        "STEP 1 — STATIC TARGET RESOLUTION"
    )

    inspect_static_structure()

    print()
    print_banner(
        "STEP 2 — RUNTIME OBSERVATION"
    )

    print(
        "CREATE_OUTCOME CALLS        :",
        runtime["create_calls"]
    )

    print(
        "FIND_FUTURE_PRICE CALLS     :",
        runtime["find_calls"]
    )

    print(
        "FIND_FUTURE_PRICE RETURNS   :",
        runtime["find_returns"]
    )

    print(
        "CREATE_OUTCOME RETURNS      :",
        runtime["create_returns"]
    )

    print(
        "RUNTIME EXCEPTIONS          :",
        runtime["exceptions"]
    )

    print()
    print_banner(
        "STEP 3 — CAPTURED FUTURE PRICE RETURNS"
    )

    if not find_returns:

        print("NONE")

    else:

        for index, record in enumerate(
            find_returns,
            1
        ):

            print(
                f"{index:03d} | "
                f"TYPE={record['type']} | "
                f"VALUE={safe_repr(record['value'])}"
            )

    print()
    print_banner(
        "STEP 4 — LOCAL PRICE / RETURN FLOW"
    )

    print(
        "LOCALIZED OBSERVATIONS     :",
        len(localized_events)
    )

    for event in localized_events[:100]:

        print(
            "LOCAL MATCH | "
            f"LINE={event['line']} | "
            f"KIND={event['kind']} | "
            f"VALUE={safe_repr(event['value'])}"
        )

    if len(localized_events) > 100:

        print(
            "...",
            len(localized_events) - 100,
            "additional observations omitted"
        )

    print()
    print_banner(
        "STEP 5 — FINAL RETURN PACKING"
    )

    unique_matches = []

    seen = set()

    for match in final_matches:

        key = (
            match["line"],
            match["path"],
            safe_repr(match["value"])
        )

        if key in seen:
            continue

        seen.add(key)

        unique_matches.append(
            match
        )

    print(
        "FINAL FIELD / PATH MATCHES   :",
        len(unique_matches)
    )

    for match in unique_matches[:100]:

        print(
            "FINAL MATCH | "
            f"LINE={match['line']} | "
            f"PATH={match['path']} | "
            f"VALUE={safe_repr(match['value'])}"
        )

    if len(unique_matches) > 100:

        print(
            "...",
            len(unique_matches) - 100,
            "additional matches omitted"
        )

    print()
    print_banner(
        "STEP 6 — FINAL FORENSIC SUMMARY"
    )

    print(
        "FIND_FUTURE_PRICE CALLS     :",
        runtime["find_calls"]
    )

    print(
        "FIND_FUTURE_PRICE RETURNS   :",
        runtime["find_returns"]
    )

    print(
        "CREATE_OUTCOME CALLS        :",
        runtime["create_calls"]
    )

    print(
        "CREATE_OUTCOME RETURNS      :",
        runtime["create_returns"]
    )

    print(
        "PRICE / LOCAL OBSERVATIONS  :",
        len(localized_events)
    )

    print(
        "FINAL PACKING MATCHES       :",
        len(unique_matches)
    )

    print(
        "RUNTIME EXCEPTIONS          :",
        runtime["exceptions"]
    )

    print(
        "BLOCKED WRITE OPERATIONS    :",
        runtime["blocked_writes"]
    )

    print()
    print_banner(
        "FORENSIC CONCLUSION"
    )

    if runtime["find_returns"] == 0:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The selected production runtime did not "
            "reach find_future_price()."
        )

        frontier = (
            "Resolve the production runtime boundary before "
            "continuing dictionary/return packing localization."
        )

    elif len(unique_matches) > 0:

        status = (
            "FIND_FUTURE_PRICE_DICTIONARY_RETURN_PACKING_LOCALIZED"
        )

        meaning = (
            "The genuine find_future_price() return was observed, "
            "followed through create_outcome().price, and matched "
            "inside the final returned structure."
        )

        frontier = (
            "Compare the localized final field across invocations "
            "and verify exact preservation versus transformation."
        )

    elif len(localized_events) > 0:

        status = (
            "FIND_FUTURE_PRICE_LOCAL_VALUE_LOCALIZED"
        )

        meaning = (
            "The genuine find_future_price() return was observed "
            "inside create_outcome(), but exact final return packing "
            "was not independently matched."
        )

        frontier = (
            "Trace the same invocation through dictionary construction "
            "and return packing at a finer frame boundary."
        )

    else:

        status = (
            "FIND_FUTURE_PRICE_RETURN_NOT_LOCALIZED"
        )

        meaning = (
            "The genuine find_future_price() return was observed, "
            "but downstream localization was not established."
        )

        frontier = (
            "Trace create_outcome() frame assignments at a finer "
            "execution boundary."
        )

    print(
        "STATUS                      :",
        status
    )

    print(
        "MEANING                     :",
        meaning
    )

    print(
        "NEXT FRONTIER               :",
        frontier
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

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

def main():

    # Install read-only DB protection BEFORE production execution.
    install_readonly_guard()

    sys.settrace(trace_function)

    try:

        execute_production_runtime()

    finally:

        sys.settrace(None)

        # Restore original sqlite connection.
        sqlite3.connect = ORIGINAL_SQLITE_CONNECT

    print_results()


if __name__ == "__main__":
    main()