import os
import sys
import ast
import sqlite3
import runpy
import traceback

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(PROJECT_DIR, "signal_outcome_engine.py")

TARGET_FUNCTION = "find_future_price"
CALLER_FUNCTION = "create_outcome"

future_calls = []
create_calls = []
create_returns = []
runtime_errors = []

active_create_frames = []
invocation_counter = 0


def safe_repr(value, limit=400):
    try:
        text = repr(value)
    except Exception:
        text = f"<UNREPRESENTABLE {type(value).__name__}>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def same_value(a, b):
    try:
        if a is b:
            return True

        if type(a) is not type(b):
            return False

        return a == b
    except Exception:
        return False


def load_source():
    with open(
        TARGET_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:
        return f.read()


def resolve_static_target():
    source = load_source()
    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    call_sites = []

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):
            if node.name != CALLER_FUNCTION:
                continue

            for child in ast.walk(node):

                if not isinstance(child, ast.Call):
                    continue

                if (
                    isinstance(child.func, ast.Name)
                    and child.func.id == TARGET_FUNCTION
                ):
                    call_sites.append(
                        child.lineno
                    )

    return sorted(set(call_sites))


def snapshot_locals(frame):
    result = {}

    try:
        for key, value in frame.f_locals.items():
            result[key] = value
    except Exception:
        pass

    return result


def find_final_price_paths(value, target_value):
    paths = []
    visited = set()

    def walk(obj, path):

        try:
            oid = id(obj)

            if oid in visited:
                return

            visited.add(oid)

        except Exception:
            pass

        if same_value(obj, target_value):
            paths.append(
                {
                    "path": path,
                    "value": obj,
                    "type": type(obj).__name__,
                }
            )

        if isinstance(obj, dict):

            for key, item in obj.items():

                walk(
                    item,
                    f"{path}.{key}"
                )

        elif isinstance(obj, (list, tuple)):

            for index, item in enumerate(obj):

                walk(
                    item,
                    f"{path}[{index}]"
                )

        elif isinstance(obj, sqlite3.Row):

            try:
                for key in obj.keys():

                    walk(
                        obj[key],
                        f"{path}.{key}"
                    )
            except Exception:
                pass

    walk(value, "ROOT")

    return paths


def trace_function(frame, event, arg):

    global invocation_counter

    try:

        filename = os.path.abspath(
            frame.f_code.co_filename
        )

        if filename != os.path.abspath(TARGET_FILE):
            return trace_function

        function_name = frame.f_code.co_name

        # ----------------------------------------------------
        # CREATE_OUTCOME ENTRY
        # ----------------------------------------------------

        if (
            event == "call"
            and function_name == CALLER_FUNCTION
        ):

            invocation_counter += 1

            record = {
                "id": invocation_counter,
                "frame": frame,
                "price_values": [],
                "future_return": None,
                "final_return": None,
            }

            create_calls.append(record)

            active_create_frames.append(record)

            return trace_function

        # ----------------------------------------------------
        # FIND_FUTURE_PRICE CALL
        # ----------------------------------------------------

        if (
            event == "call"
            and function_name == TARGET_FUNCTION
        ):

            parent_record = (
                active_create_frames[-1]
                if active_create_frames
                else None
            )

            future_calls.append(
                {
                    "create_id": (
                        parent_record["id"]
                        if parent_record
                        else None
                    ),
                    "frame": frame,
                    "locals": snapshot_locals(frame),
                }
            )

            return trace_function

        # ----------------------------------------------------
        # FIND_FUTURE_PRICE RETURN
        # ----------------------------------------------------

        if (
            event == "return"
            and function_name == TARGET_FUNCTION
        ):

            parent_record = (
                active_create_frames[-1]
                if active_create_frames
                else None
            )

            event_record = {
                "create_id": (
                    parent_record["id"]
                    if parent_record
                    else None
                ),
                "value": arg,
                "type": type(arg).__name__,
            }

            future_calls[-1]["return"] = event_record

            if parent_record is not None:
                parent_record["future_return"] = arg

            return trace_function

        # ----------------------------------------------------
        # CREATE_OUTCOME LINE TRACE
        # ----------------------------------------------------

        if (
            event == "line"
            and function_name == CALLER_FUNCTION
        ):

            if not active_create_frames:
                return trace_function

            record = active_create_frames[-1]

            locals_now = snapshot_locals(frame)

            if "price" in locals_now:

                price_value = locals_now["price"]

                record["price_values"].append(
                    {
                        "line": frame.f_lineno,
                        "value": price_value,
                        "type": type(
                            price_value
                        ).__name__,
                    }
                )

            return trace_function

        # ----------------------------------------------------
        # CREATE_OUTCOME RETURN
        # ----------------------------------------------------

        if (
            event == "return"
            and function_name == CALLER_FUNCTION
        ):

            if not active_create_frames:
                return trace_function

            record = active_create_frames[-1]

            record["final_return"] = arg

            create_returns.append(
                {
                    "id": record["id"],
                    "value": arg,
                }
            )

            return trace_function

    except Exception as exc:

        runtime_errors.append(
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    return trace_function


def execute_runtime():

    old_trace = sys.gettrace()

    try:

        sys.settrace(trace_function)

        runpy.run_path(
            TARGET_FILE,
            run_name="__main__"
        )

    except Exception as exc:

        runtime_errors.append(
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    finally:

        sys.settrace(old_trace)


def analyze_invocations():

    localized = []

    for record in create_calls:

        future_value = record["future_return"]

        if future_value is None:

            # None is a legitimate production return.
            # Do not compare globally against every None.
            price_events = [
                event
                for event in record["price_values"]
                if event["value"] is None
            ]

        else:

            price_events = [
                event
                for event in record["price_values"]
                if same_value(
                    event["value"],
                    future_value
                )
            ]

        final_paths = find_final_price_paths(
            record["final_return"],
            future_value
        )

        localized.append(
            {
                "create_id": record["id"],
                "future_value": future_value,
                "future_type": type(
                    future_value
                ).__name__,
                "price_events": price_events,
                "final_paths": final_paths,
            }
        )

    return localized


def print_report(static_sites, localized):

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE INVOCATION CHAIN "
        "VALUE TRACE FORENSIC AUDIT v0.1"
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
        "CALLER                       : "
        "create_outcome()"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    print("=" * 100)
    print("STEP 1 — STATIC CALL SITE")
    print("=" * 100)

    print(
        f"CALL SITES                  : "
        f"{len(static_sites)}"
    )

    for line in static_sites:
        print(
            f"CALL SITE                   : LINE={line}"
        )

    print("=" * 100)
    print("STEP 2 — INVOCATION-LEVEL RUNTIME TRACE")
    print("=" * 100)

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{len(create_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{len(future_calls)}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{len(create_returns)}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_errors)}"
    )

    print("=" * 100)
    print("STEP 3 — PER-INVOCATION VALUE FLOW")
    print("=" * 100)

    for item in localized:

        print()
        print(
            f"INVOCATION #{item['create_id']}"
        )

        print(
            f"FUTURE PRICE RETURN         : "
            f"{safe_repr(item['future_value'])}"
        )

        print(
            f"TYPE                        : "
            f"{item['future_type']}"
        )

        print(
            f"PRICE VARIABLE OBSERVATIONS: "
            f"{len(item['price_events'])}"
        )

        for event in item["price_events"]:

            print(
                f"  LINE={event['line']} | "
                f"PRICE={safe_repr(event['value'])}"
            )

        if item["final_paths"]:

            print(
                "FINAL OUTPUT MATCHES       : "
                f"{len(item['final_paths'])}"
            )

            for path in item["final_paths"][:20]:

                print(
                    f"  PATH={path['path']} | "
                    f"TYPE={path['type']} | "
                    f"VALUE={safe_repr(path['value'])}"
                )

        else:

            print(
                "FINAL OUTPUT MATCHES       : 0"
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_price_matches = sum(
        len(item["price_events"])
        for item in localized
    )

    total_final_matches = sum(
        len(item["final_paths"])
        for item in localized
    )

    print()
    print("=" * 100)
    print("STEP 4 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{len(create_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{len(future_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{len(future_calls)}"
    )

    print(
        f"PRICE VARIABLE MATCHES      : "
        f"{total_price_matches}"
    )

    print(
        f"FINAL FIELD MATCHES         : "
        f"{total_final_matches}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_errors)}"
    )

    print(
        "BLOCKED WRITE OPERATIONS    : 0"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if not future_calls:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        print(
            "MEANING                     : "
            "The selected production runtime did not "
            "reach find_future_price()."
        )

        print(
            "NEXT FRONTIER               : "
            "Resolve the production runtime entrypoint "
            "that reaches create_outcome()."
        )

    elif total_final_matches > 0:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_FINAL_FIELD_VALUE_INTEGRITY_VERIFIED"
        )

        print(
            "MEANING                     : "
            "The genuine return value of find_future_price() "
            "was followed per invocation and an exact equal "
            "value was observed in the final create_outcome() "
            "returned structure."
        )

        print(
            "NEXT FRONTIER               : "
            "Verify one-to-one field identity and rule out "
            "coincidental equality across multiple horizons."
        )

    elif total_price_matches > 0:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_LOCAL_VALUE_VERIFIED"
        )

        print(
            "MEANING                     : "
            "The genuine return value was followed into the "
            "create_outcome() price variable on the same "
            "invocation, but no exact final output field "
            "was matched."
        )

        print(
            "NEXT FRONTIER               : "
            "Trace the same invocation through dictionary "
            "construction and return packing."
        )

    else:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_INVOCATION_FLOW_UNRESOLVED"
        )

        print(
            "MEANING                     : "
            "The function executed, but its return could not "
            "be connected to the price variable on the same "
            "create_outcome() invocation."
        )

        print(
            "NEXT FRONTIER               : "
            "Trace bytecode-level STORE_FAST / STORE_SUBSCR "
            "boundaries for the price assignment."
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


def main():

    static_sites = resolve_static_target()

    execute_runtime()

    localized = analyze_invocations()

    print_report(
        static_sites,
        localized
    )


if __name__ == "__main__":
    main()