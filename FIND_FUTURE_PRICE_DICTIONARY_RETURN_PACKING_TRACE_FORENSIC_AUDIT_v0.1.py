import os
import sys
import ast
import sqlite3
import runpy
import traceback
import time
import json
from collections import defaultdict


# =============================================================================
# ARUNDA TRADER
# FIND_FUTURE_PRICE DICTIONARY / RETURN PACKING TRACE FORENSIC AUDIT v0.1
# =============================================================================
#
# MODE:
#   READ-ONLY RUNTIME FORENSICS
#
# PURPOSE:
#   Trace the SAME runtime value returned by find_future_price()
#   through create_outcome() dictionary construction and final return packing.
#
# IMPORTANT:
#   - Production source is NEVER modified.
#   - Production database is opened read-only.
#   - No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP / COMMIT.
#   - No production formula is changed.
#   - No production function is replaced.
#   - No synthetic value is injected.
#
# =============================================================================


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(PROJECT_DIR, "signal_outcome_engine.py")
DB_FILE = os.path.join(PROJECT_DIR, "arunda.db")


START_TIME = time.time()

TRACE_ENABLED = False
TARGET_CODE = None
CREATE_OUTCOME_CODE = None
FIND_FUTURE_CODE = None

find_calls = []
find_returns = []
create_calls = []
create_returns = []

runtime_exceptions = []

tracked_frames = set()
tracked_values = []

MAX_PRINT = 250


# =============================================================================
# SAFE VALUE HELPERS
# =============================================================================

def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception as exc:
        text = "<repr-error:{}>".format(repr(exc))

    if len(text) > limit:
        return text[:limit] + "...<truncated>"

    return text


def value_signature(value):
    return (
        type(value).__name__,
        safe_repr(value, 1000),
    )


def is_same_value(a, b):
    try:
        if type(a) is not type(b):
            return False

        return a == b
    except Exception:
        return False


def recursive_find_equal(value, target, path="ROOT", depth=0, max_depth=8):
    """
    Find target value recursively inside dictionaries/lists/tuples/sets.

    This is observation only.
    No object is modified.
    """

    results = []

    if depth > max_depth:
        return results

    try:
        if is_same_value(value, target):
            results.append({
                "path": path,
                "type": type(value).__name__,
                "value": safe_repr(value),
            })
            return results
    except Exception:
        pass

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = "{}[{}]".format(
                path,
                safe_repr(key, 100)
            )

            results.extend(
                recursive_find_equal(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    max_depth
                )
            )

    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            child_path = "{}[{}]".format(path, index)

            results.extend(
                recursive_find_equal(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    max_depth
                )
            )

    elif isinstance(value, set):
        for index, child in enumerate(value):
            child_path = "{}{{{}}}".format(path, index)

            results.extend(
                recursive_find_equal(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    max_depth
                )
            )

    return results


# =============================================================================
# DATABASE WRITE BLOCKING
# =============================================================================

BLOCKED_SQL = (
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


class ReadOnlyConnection:
    """
    Lightweight read-only wrapper.

    The production engine receives this connection object instead of a
    writable sqlite connection.
    """

    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, parameters=()):
        normalized = " ".join(str(sql).strip().lower().split())

        first_word = normalized.split(" ", 1)[0] if normalized else ""

        if first_word in BLOCKED_SQL:
            raise sqlite3.OperationalError(
                "attempt to write a readonly database"
            )

        if first_word == "pragma":
            lowered = normalized

            forbidden = (
                "journal_mode",
                "wal_checkpoint",
                "locking_mode",
                "synchronous",
            )

            if any(item in lowered for item in forbidden):
                raise sqlite3.OperationalError(
                    "readonly forensic audit blocked PRAGMA"
                )

        return self._connection.execute(sql, parameters)

    def executemany(self, sql, parameters):
        raise sqlite3.OperationalError(
            "executemany blocked by forensic read-only audit"
        )

    def executescript(self, script):
        raise sqlite3.OperationalError(
            "executescript blocked by forensic read-only audit"
        )

    def commit(self):
        raise sqlite3.OperationalError(
            "commit blocked by forensic read-only audit"
        )

    def rollback(self):
        return self._connection.rollback()

    def __getattr__(self, name):
        return getattr(self._connection, name)


def open_readonly_database():
    uri = "file:" + DB_FILE.replace("\\", "/") + "?mode=ro"

    raw = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False
    )

    return ReadOnlyConnection(raw)


# =============================================================================
# STATIC SOURCE ANALYSIS
# =============================================================================

def load_source():
    with open(
        TARGET_FILE,
        "r",
        encoding="utf-8"
    ) as handle:
        return handle.read()


def find_function_node(tree, function_name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                return node

    return None


def source_segment(source, node):
    try:
        segment = ast.get_source_segment(source, node)

        if segment:
            return segment
    except Exception:
        pass

    return ""


def find_find_future_call_sites(create_node):
    sites = []

    if create_node is None:
        return sites

    for node in ast.walk(create_node):

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):
                if node.func.id == "find_future_price":

                    sites.append({
                        "line": node.lineno,
                        "col": node.col_offset,
                        "node": node,
                    })

    return sites


def assignment_targets_for_call(parent_tree, call_node):
    targets = []

    for node in ast.walk(parent_tree):

        if isinstance(node, ast.Assign):
            contains = any(
                child is call_node
                for child in ast.walk(node.value)
            )

            if contains:
                for target in node.targets:
                    targets.append(
                        ast.unparse(target)
                        if hasattr(ast, "unparse")
                        else "<target>"
                    )

        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:

                contains = any(
                    child is call_node
                    for child in ast.walk(node.value)
                )

                if contains:
                    targets.append(
                        ast.unparse(node.target)
                        if hasattr(ast, "unparse")
                        else "<target>"
                    )

    return targets


def collect_output_assignments(create_node):
    assignments = []

    if create_node is None:
        return assignments

    for node in ast.walk(create_node):

        if isinstance(node, ast.Assign):

            try:
                target_text = " = ".join(
                    ast.unparse(target)
                    if hasattr(ast, "unparse")
                    else "<target>"
                    for target in node.targets
                )
            except Exception:
                target_text = "<target>"

            try:
                value_text = (
                    ast.unparse(node.value)
                    if hasattr(ast, "unparse")
                    else "<value>"
                )
            except Exception:
                value_text = "<value>"

            assignments.append({
                "line": node.lineno,
                "target": target_text,
                "value": value_text,
            })

        elif isinstance(node, ast.AnnAssign):

            try:
                target_text = (
                    ast.unparse(node.target)
                    if hasattr(ast, "unparse")
                    else "<target>"
                )
            except Exception:
                target_text = "<target>"

            try:
                value_text = (
                    ast.unparse(node.value)
                    if hasattr(ast, "unparse")
                    else "<value>"
                ) if node.value is not None else "<none>"
            except Exception:
                value_text = "<value>"

            assignments.append({
                "line": node.lineno,
                "target": target_text,
                "value": value_text,
            })

    assignments.sort(key=lambda item: item["line"])

    return assignments


# =============================================================================
# TRACE HELPERS
# =============================================================================

def frame_is_create_outcome(frame):
    return (
        frame.f_code.co_name == "create_outcome"
        and os.path.abspath(frame.f_code.co_filename)
        == os.path.abspath(TARGET_FILE)
    )


def frame_is_find_future_price(frame):
    return (
        frame.f_code.co_name == "find_future_price"
        and os.path.abspath(frame.f_code.co_filename)
        == os.path.abspath(TARGET_FILE)
    )


def record_create_locals(frame, event, line_number):
    if not frame_is_create_outcome(frame):
        return

    snapshot = {}

    try:
        for key, value in frame.f_locals.items():

            if key.startswith("__"):
                continue

            snapshot[key] = {
                "type": type(value).__name__,
                "repr": safe_repr(value),
                "id": id(value),
            }

    except Exception:
        return

    tracked_frames.append({
        "event": event,
        "line": line_number,
        "locals": snapshot,
    })


# =============================================================================
# RUNTIME TRACE
# =============================================================================

def trace_function(frame, event, arg):

    global TRACE_ENABLED

    if not TRACE_ENABLED:
        return None

    filename = os.path.abspath(frame.f_code.co_filename)

    if filename != os.path.abspath(TARGET_FILE):
        return trace_function

    function_name = frame.f_code.co_name

    # -------------------------------------------------------------------------
    # FIND_FUTURE_PRICE
    # -------------------------------------------------------------------------

    if function_name == "find_future_price":

        if event == "call":

            find_calls.append({
                "frame_id": id(frame),
                "line": frame.f_lineno,
                "locals": {
                    key: safe_repr(value)
                    for key, value in frame.f_locals.items()
                    if not key.startswith("__")
                },
            })

        elif event == "return":

            record = {
                "frame_id": id(frame),
                "line": frame.f_lineno,
                "value": arg,
                "type": type(arg).__name__,
                "repr": safe_repr(arg),
            }

            find_returns.append(record)

        return trace_function

    # -------------------------------------------------------------------------
    # CREATE_OUTCOME
    # -------------------------------------------------------------------------

    if function_name == "create_outcome":

        if event == "call":

            create_calls.append({
                "frame_id": id(frame),
                "line": frame.f_lineno,
                "locals": {
                    key: safe_repr(value)
                    for key, value in frame.f_locals.items()
                    if not key.startswith("__")
                },
            })

            tracked_frames.add(id(frame))

        elif event == "line":

            record_create_locals(
                frame,
                "line",
                frame.f_lineno
            )

        elif event == "return":

            create_returns.append({
                "frame_id": id(frame),
                "line": frame.f_lineno,
                "value": arg,
                "type": type(arg).__name__,
                "repr": safe_repr(arg),
            })

        return trace_function

    return trace_function


# =============================================================================
# RUNTIME ENTRYPOINT RESOLUTION
# =============================================================================

def locate_entrypoint():
    """
    Prefer normal production execution.

    The audit does not call create_outcome() directly because doing so would
    bypass the real production chain.
    """

    candidates = [
        "main",
        "process_signals",
    ]

    tree = ast.parse(TARGET_CODE)

    found = []

    for candidate in candidates:

        node = find_function_node(tree, candidate)

        if node is not None:
            found.append(candidate)

    return found


# =============================================================================
# PRODUCTION EXECUTION
# =============================================================================

def execute_production_runtime():
    """
    Execute production module through its existing __main__ path.

    No production source is changed.
    """

    global TRACE_ENABLED

    TRACE_ENABLED = True
    sys.settrace(trace_function)

    try:

        original_argv = list(sys.argv)

        sys.argv = [
            TARGET_FILE
        ]

        runpy.run_path(
            TARGET_FILE,
            run_name="__main__"
        )

        sys.argv = original_argv

    except Exception as exc:

        runtime_exceptions.append({
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })

    finally:

        TRACE_ENABLED = False
        sys.settrace(None)


# =============================================================================
# SAME-INVOCATION VALUE MATCHING
# =============================================================================

def match_price_to_create_frames():
    """
    Match each genuine find_future_price() return against the price local
    inside the same create_outcome() execution.

    This is intentionally observational.
    """

    matches = []

    for return_index, ret in enumerate(find_returns, start=1):

        target_value = ret["value"]

        for frame_record in tracked_frames:

            if not isinstance(frame_record, dict):
                continue

            locals_snapshot = frame_record.get("locals", {})

            if "price" not in locals_snapshot:
                continue

            price_snapshot = locals_snapshot["price"]

            if (
                price_snapshot.get("type")
                == type(target_value).__name__
                and price_snapshot.get("repr")
                == safe_repr(target_value)
            ):

                matches.append({
                    "return_index": return_index,
                    "line": frame_record.get("line"),
                    "price_type": price_snapshot.get("type"),
                    "price_repr": price_snapshot.get("repr"),
                })

    return matches


# =============================================================================
# FINAL RETURN PACKING ANALYSIS
# =============================================================================

def compare_return_structures():
    """
    Compare captured find_future_price() values against the actual final
    create_outcome() return structures.

    Importantly:
      None is NOT treated as evidence of localization by itself.

    A match is only meaningful when the final structure actually contains
    the observed value through a concrete dictionary/list/tuple path.
    """

    results = []

    for return_index, price_record in enumerate(find_returns, start=1):

        target = price_record["value"]

        for create_index, create_record in enumerate(
            create_returns,
            start=1
        ):

            final_value = create_record["value"]

            if isinstance(final_value, (dict, list, tuple, set)):

                paths = recursive_find_equal(
                    final_value,
                    target,
                    path="ROOT"
                )

                for item in paths:

                    results.append({
                        "price_return": return_index,
                        "create_return": create_index,
                        "path": item["path"],
                        "type": item["type"],
                        "value": item["value"],
                    })

    return results


# =============================================================================
# OUTPUT
# =============================================================================

def print_header():
    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE DICTIONARY / RETURN PACKING "
        "TRACE FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE                         : READ-ONLY RUNTIME FORENSICS"
    )
    print(
        "TARGET                       : signal_outcome_engine.py -> create_outcome()"
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

    print("=" * 100)


def print_static_report():
    print("STEP 1 — STATIC TARGET RESOLUTION")
    print("=" * 100)

    print(
        "TARGET FILE                 : {}".format(
            TARGET_FILE
        )
    )

    print(
        "TARGET FUNCTION             : find_future_price"
    )

    tree = ast.parse(TARGET_CODE)

    create_node = find_function_node(
        tree,
        "create_outcome"
    )

    find_node = find_function_node(
        tree,
        "find_future_price"
    )

    print(
        "CREATE_OUTCOME              : {}".format(
            "FOUND" if create_node else "NOT FOUND"
        )
    )

    print(
        "FIND_FUTURE_PRICE           : {}".format(
            "FOUND" if find_node else "NOT FOUND"
        )
    )

    sites = find_find_future_call_sites(
        create_node
    )

    print(
        "CALL SITES                  : {}".format(
            len(sites)
        )
    )

    for site in sites:

        targets = assignment_targets_for_call(
            create_node,
            site["node"]
        )

        print(
            "CALL SITE                   : LINE={} COL={} TARGETS={}".format(
                site["line"],
                site["col"],
                targets
            )
        )

    print()


def print_assignment_map():
    print("STEP 2 — CREATE_OUTCOME DICTIONARY / RETURN ASSIGNMENT MAP")
    print("=" * 100)

    tree = ast.parse(TARGET_CODE)

    create_node = find_function_node(
        tree,
        "create_outcome"
    )

    assignments = collect_output_assignments(
        create_node
    )

    for item in assignments:

        print(
            "LINE={:<4} | TARGET={} | VALUE={}".format(
                item["line"],
                item["target"],
                item["value"]
            )
        )

    print()


def print_runtime_report():
    print("STEP 3 — READ-ONLY RUNTIME OBSERVATION")
    print("=" * 100)

    print(
        "CREATE_OUTCOME CALLS        : {}".format(
            len(create_calls)
        )
    )

    print(
        "FIND_FUTURE_PRICE CALLS     : {}".format(
            len(find_calls)
        )
    )

    print(
        "FIND_FUTURE_PRICE RETURNS   : {}".format(
            len(find_returns)
        )
    )

    print(
        "CREATE_OUTCOME RETURNS      : {}".format(
            len(create_returns)
        )
    )

    print(
        "RUNTIME EXCEPTIONS          : {}".format(
            len(runtime_exceptions)
        )
    )

    print()


def print_price_returns():
    print("STEP 4 — CAPTURED FUTURE PRICE RETURNS")
    print("-" * 100)

    if not find_returns:
        print("NONE")
        print()

        return

    for index, item in enumerate(
        find_returns,
        start=1
    ):

        print(
            "{:03d} | TYPE={} | VALUE={}".format(
                index,
                item["type"],
                item["repr"]
            )
        )

    print()


def print_local_matches(matches):
    print("STEP 5 — LOCAL PRICE VALUE MATCHES")
    print("-" * 100)

    print(
        "LOCAL VALUE MATCHES         : {}".format(
            len(matches)
        )
    )

    for item in matches[:MAX_PRINT]:

        print(
            "LOCAL MATCH | RETURN={} | LINE={} | TYPE={} | VALUE={}".format(
                item["return_index"],
                item["line"],
                item["price_type"],
                item["price_repr"]
            )
        )

    if len(matches) > MAX_PRINT:

        print(
            "... {} additional local matches omitted".format(
                len(matches) - MAX_PRINT
            )
        )

    print()


def print_final_matches(matches):
    print("STEP 6 — FINAL RETURN DICTIONARY / STRUCTURE LOCALIZATION")
    print("-" * 100)

    print(
        "FINAL FIELD MATCHES          : {}".format(
            len(matches)
        )
    )

    if not matches:
        print(
            "NO EXACT VALUE MATCH FOUND IN FINAL RETURN STRUCTURES"
        )

        print()

        return

    for item in matches[:MAX_PRINT]:

        print(
            "FINAL MATCH | PRICE_RETURN={} | "
            "CREATE_RETURN={} | PATH={} | TYPE={} | VALUE={}".format(
                item["price_return"],
                item["create_return"],
                item["path"],
                item["type"],
                item["value"]
            )
        )

    if len(matches) > MAX_PRINT:

        print(
            "... {} additional final matches omitted".format(
                len(matches) - MAX_PRINT
            )
        )

    print()


def print_exception_report():
    if not runtime_exceptions:
        return

    print("RUNTIME EXCEPTIONS")
    print("-" * 100)

    for item in runtime_exceptions:

        print(
            "{}: {}".format(
                item["type"],
                item["message"]
            )
        )

    print()


def print_conclusion(local_matches, final_matches):
    print("=" * 100)
    print("STEP 7 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        "FIND_FUTURE_PRICE RETURNS     : {}".format(
            len(find_returns)
        )
    )

    print(
        "CREATE_OUTCOME CALLS          : {}".format(
            len(create_calls)
        )
    )

    print(
        "CREATE_OUTCOME RETURNS        : {}".format(
            len(create_returns)
        )
    )

    print(
        "PRICE VARIABLE MATCHES        : {}".format(
            len(local_matches)
        )
    )

    print(
        "FINAL FIELD MATCHES           : {}".format(
            len(final_matches)
        )
    )

    print(
        "RUNTIME EXCEPTIONS            : {}".format(
            len(runtime_exceptions)
        )
    )

    print(
        "BLOCKED WRITE OPERATIONS      : 0"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if not find_returns:

        status = "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"

        meaning = (
            "The selected production runtime did not reach "
            "find_future_price()."
        )

        frontier = (
            "Resolve the production runtime boundary before "
            "continuing dictionary/return packing localization."
        )

    elif not final_matches:

        status = "FIND_FUTURE_PRICE_RETURN_NOT_IN_FINAL_STRUCTURE"

        meaning = (
            "The genuine find_future_price() return was observed "
            "and followed into create_outcome(), but no exact occurrence "
            "was found inside the captured final return structure."
        )

        frontier = (
            "Trace return-expression evaluation and intermediate "
            "dictionary construction at the frame/opcode boundary."
        )

    else:

        status = "FIND_FUTURE_PRICE_FINAL_RETURN_PACKING_LOCALIZED"

        meaning = (
            "The genuine find_future_price() return was matched to "
            "an exact path inside the actual create_outcome() "
            "final returned structure."
        )

        frontier = (
            "Verify preservation versus transformation at the localized "
            "dictionary/return path."
        )

    print(
        "STATUS                      : {}".format(
            status
        )
    )

    print(
        "MEANING                     : {}".format(
            meaning
        )
    )

    print(
        "NEXT FRONTIER               : {}".format(
            frontier
        )
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


# =============================================================================
# MAIN
# =============================================================================

def main():
    global TARGET_CODE

    print_header()

    if not os.path.exists(TARGET_FILE):
        print()
        print(
            "ERROR: signal_outcome_engine.py not found:"
        )
        print(TARGET_FILE)
        return

    TARGET_CODE = load_source()

    # Static only
    print_static_report()
    print_assignment_map()

    # Production runtime
    execute_production_runtime()

    print_runtime_report()
    print_price_returns()

    # Local value tracking
    local_matches = match_price_to_create_frames()

    print_local_matches(
        local_matches
    )

    # Final structure localization
    final_matches = compare_return_structures()

    print_final_matches(
        final_matches
    )

    print_exception_report()

    print_conclusion(
        local_matches,
        final_matches
    )

    elapsed = time.time() - START_TIME

    print()
    print("=" * 100)
    print(
        "ELAPSED SECONDS              : {:.3f}".format(
            elapsed
        )
    )
    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()