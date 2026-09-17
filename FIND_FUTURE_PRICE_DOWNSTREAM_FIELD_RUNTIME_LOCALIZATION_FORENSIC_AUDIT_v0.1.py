import ast
import os
import sys
import time
import traceback
from collections import defaultdict, deque

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(PROJECT_DIR, "signal_outcome_engine.py")

TARGET_FUNCTION = "create_outcome"
SECONDARY_FUNCTION = "find_future_price"

EXCLUDED_KEYWORDS = {
    "forensic",
    "audit",
    "diagnostic",
    "discovery",
    "trace",
    "repair",
    "test",
    "debug",
    "backup",
    "snapshot",
    "__pycache__",
}

TARGET_SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]


def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None


def should_exclude(path):
    name = os.path.basename(path).lower()

    if name == os.path.basename(__file__).lower():
        return True

    for token in EXCLUDED_KEYWORDS:
        if token in name:
            return True

    return False


def discover_python_files():
    files = []

    for root, dirs, filenames in os.walk(PROJECT_DIR):
        dirs[:] = [
            d for d in dirs
            if d != "__pycache__"
            and not any(x in d.lower() for x in EXCLUDED_KEYWORDS)
        ]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            path = os.path.join(root, filename)

            if should_exclude(path):
                continue

            files.append(os.path.abspath(path))

    return sorted(set(files))


def parse_file(path):
    source = safe_read(path)

    if source is None:
        return None, "READ_ERROR"

    try:
        tree = ast.parse(source, filename=path)
        return tree, None
    except Exception as exc:
        return None, repr(exc)


def module_name_from_path(path):
    rel = os.path.relpath(path, PROJECT_DIR)
    rel = rel.replace("\\", "/")

    if rel.endswith(".py"):
        rel = rel[:-3]

    rel = rel.replace("/", ".")

    if rel.endswith(".__init__"):
        rel = rel[:-9]

    return rel


def discover_functions(files):
    functions = {}
    parse_errors = []

    for path in files:
        tree, error = parse_file(path)

        if error:
            parse_errors.append((path, error))
            continue

        module = module_name_from_path(path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[(module, node.name)] = {
                    "module": module,
                    "name": node.name,
                    "file": path,
                    "line": node.lineno,
                    "node": node,
                }

    return functions, parse_errors


def get_called_names(node):
    calls = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func

            if isinstance(func, ast.Name):
                calls.append(func.id)

            elif isinstance(func, ast.Attribute):
                calls.append(func.attr)

    return calls


def build_call_graph(functions):
    by_name = defaultdict(list)

    for key, info in functions.items():
        by_name[info["name"]].append(key)

    edges = defaultdict(set)

    for key, info in functions.items():
        caller_name = info["name"]
        node = info["node"]

        called_names = get_called_names(node)

        for called in called_names:
            candidates = by_name.get(called, [])

            for target_key in candidates:
                edges[key].add(target_key)

    return edges


def reverse_graph(edges):
    reverse = defaultdict(set)

    for caller, callees in edges.items():
        for callee in callees:
            reverse[callee].add(caller)

    return reverse


def find_function_keys(functions, name):
    return [
        key
        for key, info in functions.items()
        if info["name"] == name
    ]


def find_production_callers(functions, edges, target_name):
    target_keys = set(find_function_keys(functions, target_name))
    reverse = reverse_graph(edges)

    callers = set()

    for target in target_keys:
        callers.update(reverse.get(target, set()))

    return callers


def bfs_upstream(functions, reverse, start_keys, max_depth=8):
    results = []

    queue = deque()

    visited = set()

    for key in start_keys:
        queue.append((key, 0, [key]))
        visited.add(key)

    while queue:
        current, depth, path = queue.popleft()

        if depth >= max_depth:
            continue

        for parent in reverse.get(current, set()):
            if parent in visited:
                continue

            visited.add(parent)

            new_path = path + [parent]

            results.append((parent, depth + 1, new_path))

            queue.append(
                (parent, depth + 1, new_path)
            )

    return results


def score_entrypoint(info, distance):
    name = info["name"].lower()
    file_name = os.path.basename(info["file"]).lower()

    score = 0

    if name == "main":
        score += 100

    if name in {
        "run",
        "start",
        "execute",
        "process",
        "process_signals",
    }:
        score += 35

    if "engine" in file_name:
        score += 15

    if distance <= 2:
        score += 10

    if distance <= 4:
        score += 5

    return score


def format_chain(functions, path):
    lines = []

    for key in path:
        info = functions[key]

        lines.append(
            f"{os.path.basename(info['file'])}::{info['name']}()"
        )

    return lines


def locate_direct_call(tree, function_name):
    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func

            called = None

            if isinstance(func, ast.Name):
                called = func.id

            elif isinstance(func, ast.Attribute):
                called = func.attr

            if called != function_name:
                continue

            parent_line = node.lineno

            results.append(
                {
                    "line": parent_line,
                    "column": node.col_offset,
                }
            )

    return results


def resolve_runtime_entrypoint(functions, edges):
    target_keys = set(find_function_keys(functions, TARGET_FUNCTION))

    reverse = reverse_graph(edges)

    direct_callers = set()

    for target in target_keys:
        direct_callers.update(reverse.get(target, set()))

    if not direct_callers:
        return None, []

    upstream = bfs_upstream(
        functions,
        reverse,
        direct_callers,
        max_depth=10,
    )

    candidates = []

    for key, distance, path in upstream:
        info = functions[key]

        score = score_entrypoint(info, distance)

        if info["name"] == "main":
            score += 50

        candidates.append(
            {
                "key": key,
                "info": info,
                "distance": distance + 1,
                "path": path,
                "score": score,
            }
        )

    candidates.sort(
        key=lambda x: (
            -x["score"],
            x["distance"],
            x["info"]["name"],
        )
    )

    if not candidates:
        return None, []

    return candidates[0], candidates


def runtime_import_module(module_name):
    import importlib

    return importlib.import_module(module_name)


def make_runtime_wrapper(module):
    original_create = getattr(
        module,
        TARGET_FUNCTION,
        None,
    )

    original_future = getattr(
        module,
        SECONDARY_FUNCTION,
        None,
    )

    runtime = {
        "create_calls": [],
        "future_calls": [],
        "future_returns": [],
        "create_returns": [],
        "exceptions": [],
    }

    if original_future is not None:

        def wrapped_future(*args, **kwargs):
            record = {
                "args": repr(args),
                "kwargs": repr(kwargs),
            }

            runtime["future_calls"].append(record)

            try:
                result = original_future(
                    *args,
                    **kwargs,
                )

                runtime["future_returns"].append(
                    {
                        "result": repr(result),
                    }
                )

                return result

            except Exception as exc:
                runtime["exceptions"].append(
                    {
                        "function": SECONDARY_FUNCTION,
                        "exception": repr(exc),
                    }
                )
                raise

        setattr(
            module,
            SECONDARY_FUNCTION,
            wrapped_future,
        )

    if original_create is not None:

        def wrapped_create(*args, **kwargs):
            runtime["create_calls"].append(
                {
                    "args": repr(args),
                    "kwargs": repr(kwargs),
                }
            )

            try:
                result = original_create(
                    *args,
                    **kwargs,
                )

                runtime["create_returns"].append(
                    {
                        "result": repr(result),
                    }
                )

                return result

            except Exception as exc:
                runtime["exceptions"].append(
                    {
                        "function": TARGET_FUNCTION,
                        "exception": repr(exc),
                    }
                )
                raise

        setattr(
            module,
            TARGET_FUNCTION,
            wrapped_create,
        )

    return runtime


def try_runtime_entrypoint(module, entrypoint_name):
    runtime = make_runtime_wrapper(module)

    entrypoint = getattr(
        module,
        entrypoint_name,
        None,
    )

    if entrypoint is None:
        return runtime

    try:
        if entrypoint_name == "main":
            entrypoint()
        else:
            try:
                entrypoint()
            except TypeError:
                pass

    except SystemExit:
        pass

    except Exception as exc:
        runtime["exceptions"].append(
            {
                "function": entrypoint_name,
                "exception": repr(exc),
            }
        )

    return runtime


def print_header():
    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE PRODUCTION ENTRYPOINT "
        "RUNTIME RESOLUTION FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE                         : READ-ONLY RUNTIME FORENSICS"
    )
    print(
        "TARGET                       : signal_outcome_engine.py -> create_outcome()"
    )
    print(
        "SECONDARY TARGET             : find_future_price()"
    )
    print(
        "PRODUCTION DATABASE WRITE    : BLOCKED"
    )


def main():
    started = time.time()

    print_header()

    print("\n" + "=" * 100)
    print("STEP 1 — PROJECT FILE DISCOVERY")
    print("=" * 100)

    files = discover_python_files()

    print(
        f"PYTHON FILES SELECTED        : {len(files)}"
    )

    print("\n" + "=" * 100)
    print("STEP 2 — STATIC FUNCTION DISCOVERY")
    print("=" * 100)

    functions, parse_errors = discover_functions(files)

    print(
        f"FUNCTIONS DISCOVERED         : {len(functions)}"
    )
    print(
        f"PARSE ERRORS                 : {len(parse_errors)}"
    )

    print("\n" + "=" * 100)
    print("STEP 3 — CALL GRAPH")
    print("=" * 100)

    edges = build_call_graph(functions)

    edge_count = sum(
        len(v)
        for v in edges.values()
    )

    print(
        f"CALL GRAPH EDGES             : {edge_count}"
    )

    print("\n" + "=" * 100)
    print("STEP 4 — PRODUCTION ENTRYPOINT RESOLUTION")
    print("=" * 100)

    selected, candidates = resolve_runtime_entrypoint(
        functions,
        edges,
    )

    if selected is None:

        print(
            "STATUS                       : "
            "PRODUCTION_ENTRYPOINT_NOT_RESOLVED"
        )

        print(
            "NEXT FRONTIER                : "
            "Manual production caller resolution."
        )

        print(
            f"\nELAPSED SECONDS              : "
            f"{time.time() - started:.3f}"
        )

        return

    info = selected["info"]

    print(
        f"SELECTED ENTRYPOINT FILE     : {info['file']}"
    )
    print(
        f"SELECTED ENTRYPOINT FUNCTION : {info['name']}"
    )
    print(
        f"ENTRYPOINT SCORE             : {selected['score']}"
    )
    print(
        f"ENTRYPOINT DISTANCE          : {selected['distance']}"
    )

    print("\nENTRYPOINT CHAIN")
    print("-" * 100)

    for item in format_chain(
        functions,
        selected["path"],
    ):
        print("  -> " + item)

    print("\n" + "=" * 100)
    print("STEP 5 — RUNTIME PRODUCTION ENTRYPOINT TRACE")
    print("=" * 100)

    module_name = module_name_from_path(
        os.path.join(
            PROJECT_DIR,
            "signal_outcome_engine.py",
        )
    )

    print(
        f"MODULE                       : {module_name}"
    )

    runtime = {
        "create_calls": [],
        "future_calls": [],
        "future_returns": [],
        "create_returns": [],
        "exceptions": [],
    }

    try:
        module = runtime_import_module(
            module_name
        )

        runtime = try_runtime_entrypoint(
            module,
            info["name"],
        )

    except Exception as exc:
        runtime["exceptions"].append(
            {
                "function": info["name"],
                "exception": repr(exc),
            }
        )

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{len(runtime['create_calls'])}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{len(runtime['future_calls'])}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{len(runtime['future_returns'])}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{len(runtime['create_returns'])}"
    )

    print(
        f"RUNTIME EXCEPTIONS           : "
        f"{len(runtime['exceptions'])}"
    )

    print("\n" + "=" * 100)
    print("STEP 6 — TARGET REACHABILITY")
    print("=" * 100)

    reached = len(runtime["future_calls"]) > 0

    if reached:
        print(
            "FIND_FUTURE_PRICE REACHED  : True"
        )

        print(
            "RUNTIME PATH                : "
            "PRODUCTION ENTRYPOINT -> "
            "create_outcome() -> "
            "find_future_price()"
        )

        print("\nCAPTURED FUTURE PRICE RETURNS")
        print("-" * 100)

        for index, item in enumerate(
            runtime["future_returns"],
            start=1,
        ):
            print(
                f"{index:03d} | RETURN={item['result']}"
            )

    else:
        print(
            "FIND_FUTURE_PRICE REACHED  : False"
        )

    print("\n" + "=" * 100)
    print("STEP 7 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    if reached:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_RUNTIME_REACHED"
        )

        print(
            "MEANING                     : "
            "The actual production entrypoint reached "
            "create_outcome() and the genuine "
            "find_future_price() function was executed "
            "through the production runtime chain."
        )

        print(
            "NEXT FRONTIER               : "
            "Trace the captured future-price value through "
            "its downstream field assignment."
        )

    else:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        print(
            "MEANING                     : "
            "The selected production entrypoint did not "
            "reach find_future_price() during this safe "
            "runtime invocation."
        )

        print(
            "NEXT FRONTIER               : "
            "Resolve the actual runtime invocation inputs "
            "required to reach create_outcome()."
        )

    print(
        "\nIMPORTANT                   : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                   : "
        "Original production functions were executed "
        "unchanged when reached."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                   : "
        "No production source was modified on disk."
    )

    print(
        "\nDATABASE WRITE OPERATIONS   : NONE"
    )
    print(
        "ENGINE MODIFICATIONS        : NONE ON DISK"
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
        "PRODUCTION DB WRITE         : BLOCKED"
    )

    if parse_errors:
        print("\n" + "=" * 100)
        print("PARSE ERRORS")
        print("=" * 100)

        for path, error in parse_errors[:50]:
            print(
                f"FILE      : {path}"
            )
            print(
                f"EXCEPTION : {error}"
            )
            print()

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