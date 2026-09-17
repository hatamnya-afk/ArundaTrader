import ast
import os
import sys
import time
import traceback
import importlib.util
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
TARGET_FILE = PROJECT_DIR / "signal_outcome_engine.py"

TARGET_FUNCTION = "create_outcome"
TARGET_CALLEE = "find_future_price"

TRACE_LIMIT = 200000


def read_source(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def find_function_node(tree, function_name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                return node
    return None


def get_source_segment(source, node):
    try:
        value = ast.get_source_segment(source, node)
        return value.strip() if value else ""
    except Exception:
        return ""


def find_future_price_calls(function_node):
    calls = []

    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        name = None

        if isinstance(func, ast.Name):
            name = func.id

        elif isinstance(func, ast.Attribute):
            name = func.attr

        if name == TARGET_CALLEE:
            calls.append(node)

    return calls


def find_enclosing_assignment(function_node, target_call):
    assignments = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):
            for value in ast.walk(node.value):
                if value is target_call:
                    targets = []

                    for target in node.targets:
                        targets.append(
                            ast.unparse(target)
                            if hasattr(ast, "unparse")
                            else "<assignment-target>"
                        )

                    assignments.append(
                        {
                            "line": node.lineno,
                            "targets": targets,
                            "statement": ast.get_source_segment(
                                SOURCE,
                                node,
                            ) or "",
                        }
                    )

        elif isinstance(node, ast.AnnAssign):
            value = node.value

            if value is None:
                continue

            for value_node in ast.walk(value):
                if value_node is target_call:

                    target = (
                        ast.unparse(node.target)
                        if hasattr(ast, "unparse")
                        else "<assignment-target>"
                    )

                    assignments.append(
                        {
                            "line": node.lineno,
                            "targets": [target],
                            "statement": ast.get_source_segment(
                                SOURCE,
                                node,
                            ) or "",
                        }
                    )

        elif isinstance(node, ast.NamedExpr):
            if node.value is target_call:

                target = (
                    ast.unparse(node.target)
                    if hasattr(ast, "unparse")
                    else "<assignment-target>"
                )

                assignments.append(
                    {
                        "line": node.lineno,
                        "targets": [target],
                        "statement": ast.get_source_segment(
                            SOURCE,
                            node,
                        ) or "",
                    }
                )

    return assignments


def collect_assignment_map(function_node):
    result = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):
            result.append(
                {
                    "line": node.lineno,
                    "type": "Assign",
                    "targets": [
                        ast.unparse(t)
                        if hasattr(ast, "unparse")
                        else "<target>"
                        for t in node.targets
                    ],
                    "statement": (
                        ast.get_source_segment(SOURCE, node)
                        or ""
                    ).strip(),
                }
            )

        elif isinstance(node, ast.AnnAssign):
            result.append(
                {
                    "line": node.lineno,
                    "type": "AnnAssign",
                    "targets": [
                        ast.unparse(node.target)
                        if hasattr(ast, "unparse")
                        else "<target>"
                    ],
                    "statement": (
                        ast.get_source_segment(SOURCE, node)
                        or ""
                    ).strip(),
                }
            )

        elif isinstance(node, ast.AugAssign):
            result.append(
                {
                    "line": node.lineno,
                    "type": "AugAssign",
                    "targets": [
                        ast.unparse(node.target)
                        if hasattr(ast, "unparse")
                        else "<target>"
                    ],
                    "statement": (
                        ast.get_source_segment(SOURCE, node)
                        or ""
                    ).strip(),
                }
            )

    result.sort(key=lambda x: x["line"])

    return result


def value_signature(value):
    try:
        return repr(value)
    except Exception:
        try:
            return str(value)
        except Exception:
            return "<UNREPRESENTABLE>"


def safe_equal(a, b):
    try:
        result = a == b

        if isinstance(result, bool):
            return result

        return bool(result)

    except Exception:
        return False


class RuntimeTracer:

    def __init__(self, target_code):
        self.target_code = target_code

        self.enabled = False

        self.future_calls = []
        self.future_returns = []

        self.create_events = []
        self.create_returns = []

        self.local_snapshots = []

        self.assignment_candidates = []

        self.call_depth = 0

        self.trace_events = 0

        self.last_future_return = None

        self.last_future_return_event = None

        self.inside_create = False

        self.create_frame = None

    def snapshot_locals(self, frame, event, line_number):

        if not self.inside_create:
            return

        if self.trace_events >= TRACE_LIMIT:
            return

        self.trace_events += 1

        try:
            locals_copy = dict(frame.f_locals)
        except Exception:
            locals_copy = {}

        self.local_snapshots.append(
            {
                "event": event,
                "line": line_number,
                "locals": locals_copy,
            }
        )

    def trace(self, frame, event, arg):

        if frame.f_code is self.target_code:

            if event == "call":
                self.inside_create = True
                self.create_frame = frame

                self.create_events.append(
                    {
                        "event": "call",
                        "line": frame.f_lineno,
                    }
                )

                self.snapshot_locals(
                    frame,
                    "call",
                    frame.f_lineno,
                )

                return self.trace

            if event == "line":

                self.snapshot_locals(
                    frame,
                    "line",
                    frame.f_lineno,
                )

                return self.trace

            if event == "return":

                self.snapshot_locals(
                    frame,
                    "return",
                    frame.f_lineno,
                )

                self.create_returns.append(
                    {
                        "line": frame.f_lineno,
                        "value": arg,
                        "repr": value_signature(arg),
                    }
                )

                self.inside_create = False
                self.create_frame = None

                return self.trace

            return self.trace

        module_name = frame.f_globals.get(
            "__name__",
            "",
        )

        if module_name == "signal_outcome_engine":

            function_name = frame.f_code.co_name

            if function_name == TARGET_CALLEE:

                if event == "call":

                    args = {}

                    try:
                        arg_info = frame.f_code.co_varnames
                        arg_values = frame.f_locals

                        for name in arg_info:
                            if name in arg_values:
                                args[name] = arg_values[name]

                    except Exception:
                        pass

                    self.future_calls.append(
                        {
                            "line": frame.f_lineno,
                            "args": args,
                            "repr_args": {
                                k: value_signature(v)
                                for k, v in args.items()
                            },
                        }
                    )

                elif event == "return":

                    record = {
                        "line": frame.f_lineno,
                        "value": arg,
                        "repr": value_signature(arg),
                    }

                    self.future_returns.append(record)

                    self.last_future_return = arg
                    self.last_future_return_event = record

                    return self.trace

                return self.trace

        return self.trace


def install_import_and_execute():
    module_name = "signal_outcome_engine"

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(TARGET_FILE),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to create module specification."
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


def resolve_entrypoint(module):
    candidates = [
        "main",
        "run",
        "start",
        "execute",
        "process_signals",
    ]

    for name in candidates:
        value = getattr(module, name, None)

        if callable(value):
            return name, value

    return None, None


def execute_entrypoint(module, tracer):
    name, entrypoint = resolve_entrypoint(module)

    if entrypoint is None:
        raise RuntimeError(
            "No production runtime entrypoint was found."
        )

    sys.settrace(tracer.trace)

    try:
        try:
            entrypoint()
        except SystemExit:
            pass
    finally:
        sys.settrace(None)

    return name


def compare_locals_to_future_return(tracer):
    future_value = tracer.last_future_return

    if not tracer.future_returns:
        return {
            "status": "NO_FUTURE_RETURN",
            "matches": [],
        }

    matches = []

    for snapshot in tracer.local_snapshots:

        locals_dict = snapshot["locals"]

        for name, value in locals_dict.items():

            if safe_equal(
                value,
                future_value,
            ):
                matches.append(
                    {
                        "line": snapshot["line"],
                        "event": snapshot["event"],
                        "variable": name,
                        "value": value,
                        "repr": value_signature(value),
                    }
                )

    return {
        "status": (
            "MATCHES_FOUND"
            if matches
            else "NO_LOCAL_MATCH"
        ),
        "matches": matches,
    }


def detect_value_propagation(tracer):
    if tracer.last_future_return is None:
        return []

    future_value = tracer.last_future_return

    observations = []

    for snapshot in tracer.local_snapshots:

        locals_dict = snapshot["locals"]

        for name, value in locals_dict.items():

            if safe_equal(
                value,
                future_value,
            ):
                observations.append(
                    {
                        "line": snapshot["line"],
                        "event": snapshot["event"],
                        "variable": name,
                        "value": value,
                        "repr": value_signature(value),
                        "exact": True,
                    }
                )

    unique = []

    seen = set()

    for item in observations:

        key = (
            item["line"],
            item["event"],
            item["variable"],
            item["repr"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


def find_final_field_in_return(return_value, target_value, path="root"):
    matches = []

    if safe_equal(
        return_value,
        target_value,
    ):
        matches.append(
            {
                "path": path,
                "value": return_value,
                "exact": True,
            }
        )

    if isinstance(return_value, dict):

        for key, value in return_value.items():

            child_path = (
                f"{path}[{key!r}]"
            )

            matches.extend(
                find_final_field_in_return(
                    value,
                    target_value,
                    child_path,
                )
            )

    elif isinstance(return_value, (list, tuple)):

        for index, value in enumerate(return_value):

            child_path = (
                f"{path}[{index}]"
            )

            matches.extend(
                find_final_field_in_return(
                    value,
                    target_value,
                    child_path,
                )
            )

    return matches


def print_assignment_map(assignments):
    print("\nSTATIC ASSIGNMENT MAP")
    print("-" * 100)

    if not assignments:
        print("NO ASSIGNMENTS FOUND")
        return

    for item in assignments:
        print(
            f"LINE={item['line']} | "
            f"TYPE={item['type']} | "
            f"TARGETS={item['targets']} | "
            f"STATEMENT={item['statement']}"
        )


def main():

    started = time.time()

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE DOWNSTREAM FIELD "
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
        "SECONDARY TARGET             : "
        "find_future_price()"
    )

    print(
        "PRODUCTION SOURCE MODIFIED   : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    if not TARGET_FILE.exists():

        print(
            "\nERROR: signal_outcome_engine.py was not found."
        )

        return

    global SOURCE

    SOURCE = read_source(TARGET_FILE)

    tree = ast.parse(
        SOURCE,
        filename=str(TARGET_FILE),
    )

    create_node = find_function_node(
        tree,
        TARGET_FUNCTION,
    )

    if create_node is None:

        print(
            "\nERROR: create_outcome() not found."
        )

        return

    future_calls = find_future_price_calls(
        create_node
    )

    assignments = collect_assignment_map(
        create_node
    )

    print("\n" + "=" * 100)
    print("STEP 1 — STATIC TARGET RESOLUTION")
    print("=" * 100)

    print(
        f"TARGET FILE                  : {TARGET_FILE}"
    )

    print(
        f"TARGET FUNCTION              : "
        f"{TARGET_FUNCTION}()"
    )

    print(
        f"find_future_price CALL SITES : "
        f"{len(future_calls)}"
    )

    for index, call in enumerate(
        future_calls,
        start=1,
    ):

        call_source = get_source_segment(
            SOURCE,
            call,
        )

        print(
            f"{index:03d} | "
            f"LINE={call.lineno} | "
            f"CALL={call_source}"
        )

    print_assignment_map(
        assignments
    )

    print("\n" + "=" * 100)
    print("STEP 2 — READ-ONLY PRODUCTION RUNTIME")
    print("=" * 100)

    tracer = RuntimeTracer(
        create_node
    )

    runtime_exception = None
    entrypoint_name = None

    try:

        module = install_import_and_execute()

        entrypoint_name = execute_entrypoint(
            module,
            tracer,
        )

    except Exception as exc:

        runtime_exception = exc

        print(
            "\nRUNTIME EXCEPTION:"
        )

        print(
            repr(exc)
        )

        traceback.print_exc()

    print(
        f"RUNTIME ENTRYPOINT           : "
        f"{entrypoint_name or 'UNRESOLVED'}"
    )

    print(
        f"CREATE_OUTCOME CALLS         : "
        f"{len(tracer.create_events)}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS      : "
        f"{len(tracer.future_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS    : "
        f"{len(tracer.future_returns)}"
    )

    print(
        f"CREATE_OUTCOME RETURNS       : "
        f"{len(tracer.create_returns)}"
    )

    print("\n" + "=" * 100)
    print("STEP 3 — REAL FIND_FUTURE_PRICE RETURN")
    print("=" * 100)

    if tracer.future_returns:

        for index, record in enumerate(
            tracer.future_returns,
            start=1,
        ):

            print(
                f"RETURN {index:03d}"
            )

            print(
                f"LINE        : {record['line']}"
            )

            print(
                f"VALUE       : {record['repr']}"
            )

    else:

        print(
            "NO RUNTIME RETURN OBSERVED"
        )

    print("\n" + "=" * 100)
    print("STEP 4 — INTERMEDIATE LOCALIZATION")
    print("=" * 100)

    propagation = detect_value_propagation(
        tracer
    )

    if propagation:

        for index, item in enumerate(
            propagation,
            start=1,
        ):

            print(
                f"{index:03d} | "
                f"LINE={item['line']} | "
                f"EVENT={item['event']} | "
                f"VARIABLE={item['variable']} | "
                f"VALUE={item['repr']} | "
                f"EXACT={item['exact']}"
            )

    else:

        print(
            "NO INTERMEDIATE LOCAL MATCH FOUND"
        )

    print("\n" + "=" * 100)
    print("STEP 5 — FINAL RETURN FIELD LOCALIZATION")
    print("=" * 100)

    final_matches = []

    if tracer.future_returns:

        future_value = tracer.future_returns[-1][
            "value"
        ]

        for record in tracer.create_returns:

            final_matches.extend(
                find_final_field_in_return(
                    record["value"],
                    future_value,
                )
            )

    if final_matches:

        for index, item in enumerate(
            final_matches,
            start=1,
        ):

            print(
                f"{index:03d} | "
                f"PATH={item['path']} | "
                f"VALUE={value_signature(item['value'])} | "
                f"EXACT={item['exact']}"
            )

    else:

        print(
            "FINAL FIELD NOT FOUND BY EXACT VALUE MATCH"
        )

    print("\n" + "=" * 100)
    print("STEP 6 — FORENSIC CONCLUSION")
    print("=" * 100)

    if not tracer.future_returns:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The selected production runtime path "
            "did not reach find_future_price()."
        )

        frontier = (
            "Resolve the actual production runtime "
            "invocation inputs required to reach "
            "create_outcome()."
        )

    elif propagation and final_matches:

        status = (
            "FIND_FUTURE_PRICE_DOWNSTREAM_FIELD_RUNTIME_LOCALIZED"
        )

        meaning = (
            "The genuine find_future_price() return "
            "was observed in the production runtime, "
            "matched to an intermediate local variable, "
            "and localized to the final returned field."
        )

        frontier = (
            "Compare the localized field's downstream "
            "consumer without modifying production code."
        )

    elif propagation:

        status = (
            "FIND_FUTURE_PRICE_INTERMEDIATE_RUNTIME_LOCALIZED"
        )

        meaning = (
            "The genuine find_future_price() return "
            "was localized to one or more intermediate "
            "create_outcome() locals, but exact final "
            "field localization remains unresolved."
        )

        frontier = (
            "Trace subsequent transformations from the "
            "localized intermediate variable."
        )

    else:

        status = (
            "FIND_FUTURE_PRICE_RETURN_NOT_LOCALIZED"
        )

        meaning = (
            "The genuine find_future_price() return was "
            "observed, but no exact intermediate local "
            "variable containing that value was identified."
        )

        frontier = (
            "Trace create_outcome() frame assignments "
            "at a finer execution boundary."
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

    print(
        "\nSOURCE_FUNCTION             : "
        "signal_outcome_engine.py::find_future_price()"
    )

    if future_calls:

        print(
            f"CALL_SITE                   : "
            f"line {future_calls[0].lineno}"
        )

    else:

        print(
            "CALL_SITE                   : NOT OBSERVED"
        )

    if tracer.future_returns:

        print(
            f"RETURN_VALUE                : "
            f"{tracer.future_returns[-1]['repr']}"
        )

    else:

        print(
            "RETURN_VALUE                : NOT OBSERVED"
        )

    if propagation:

        variables = sorted(
            {
                item["variable"]
                for item in propagation
            }
        )

        print(
            f"INTERMEDIATE_VARIABLE       : "
            f"{variables}"
        )

    else:

        print(
            "INTERMEDIATE_VARIABLE       : "
            "NOT LOCALIZED"
        )

    if final_matches:

        paths = sorted(
            {
                item["path"]
                for item in final_matches
            }
        )

        print(
            f"FINAL_FIELD                 : "
            f"{paths}"
        )

    else:

        print(
            "FINAL_FIELD                 : "
            "NOT LOCALIZED"
        )

    if propagation and final_matches:

        print(
            "TRANSFORMATION              : "
            "VALUE PRESERVED THROUGH OBSERVED PATH"
        )

        print(
            "EQUALITY_STATUS             : "
            "EXACT_MATCH"
        )

    elif propagation:

        print(
            "TRANSFORMATION              : "
            "INTERMEDIATE VALUE OBSERVED; "
            "FINAL TRANSFORMATION UNRESOLVED"
        )

        print(
            "EQUALITY_STATUS             : "
            "PARTIAL_LOCALIZATION"
        )

    else:

        print(
            "TRANSFORMATION              : "
            "UNRESOLVED"
        )

        print(
            "EQUALITY_STATUS             : "
            "UNRESOLVED"
        )

    print(
        "\nDATABASE_WRITES              : NONE"
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

    if runtime_exception is not None:

        print(
            "\nRUNTIME_EXCEPTION             : "
            f"{repr(runtime_exception)}"
        )

    print("=" * 100)

    print(
        f"ELAPSED SECONDS              : "
        f"{time.time() - started:.3f}"
    )

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()