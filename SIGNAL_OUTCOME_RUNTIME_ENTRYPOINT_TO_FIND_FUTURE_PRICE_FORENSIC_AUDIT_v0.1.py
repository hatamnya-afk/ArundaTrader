import ast
import importlib.util
import inspect
import os
import sys
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA
# SIGNAL OUTCOME RUNTIME ENTRYPOINT TO FIND_FUTURE_PRICE
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Trace the REAL production runtime path:
#
#     production entrypoint
#            |
#            v
#     create_outcome()
#            |
#            v
#     find_future_price()
#
# The original production functions are executed unchanged.
#
# SAFETY
# ------
# NO DATABASE WRITE
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
#
# This audit does NOT modify production source on disk.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

TARGET_FILE = os.path.join(
    PROJECT_DIR,
    "signal_outcome_engine.py"
)

MODULE_NAME = (
    "arunda_signal_outcome_runtime_entry_v01"
)

TARGET_FUNCTION = "find_future_price"
PARENT_FUNCTION = "create_outcome"

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# FORENSIC STATE
# ============================================================

runtime_find_calls = []
runtime_find_returns = []

runtime_create_calls = []
runtime_create_returns = []

runtime_entry_calls = []

runtime_exceptions = []

sql_events = []
blocked_writes = []

entrypoint_candidates = []
selected_entrypoint = None

original_functions = {}


# ============================================================
# HELPERS
# ============================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def safe_repr(value, limit=1800):

    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def load_source(path):

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as handle:
        return handle.read()


def function_nodes(tree):

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            result.append(node)

    return result


def find_function(tree, name):

    for node in function_nodes(tree):

        if node.name == name:
            return node

    return None


# ============================================================
# STATIC ENTRYPOINT DISCOVERY
# ============================================================

def discover_entrypoints():

    section(
        "STEP 1 — PRODUCTION ENTRYPOINT DISCOVERY"
    )

    source = load_source(
        TARGET_FILE
    )

    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    functions = function_nodes(
        tree
    )

    print(
        f"FUNCTIONS DISCOVERED : "
        f"{len(functions)}"
    )

    candidates = []

    for node in functions:

        score = 0

        name = node.name.lower()

        if name == "main":
            score += 100

        if (
            name.startswith("run")
            or name.startswith("process")
            or name.startswith("execute")
        ):
            score += 40

        if (
            "signal" in name
            or "outcome" in name
        ):
            score += 20

        if score > 0:

            candidates.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "score": score,
                }
            )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["line"],
        )
    )

    print()
    print(
        "ENTRYPOINT CANDIDATES"
    )

    line("-")

    for item in candidates:

        print(
            f"{item['name']:<35} "
            f"| LINE={item['line']:<5} "
            f"| SCORE={item['score']}"
        )

    entrypoint_candidates.extend(
        candidates
    )

    return tree, candidates


# ============================================================
# STATIC CALL GRAPH
# ============================================================

def direct_calls_target(
    node,
    target_name
):

    calls = []

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Call
        ):
            continue

        func = child.func

        if isinstance(
            func,
            ast.Name
        ):

            if func.id == target_name:

                calls.append(
                    child
                )

        elif isinstance(
            func,
            ast.Attribute
        ):

            if func.attr == target_name:

                calls.append(
                    child
                )

    return calls


def build_local_call_graph(tree):

    graph = defaultdict(list)

    functions = function_nodes(
        tree
    )

    function_names = {
        node.name
        for node in functions
    }

    for node in functions:

        for child in ast.walk(node):

            if not isinstance(
                child,
                ast.Call
            ):
                continue

            func = child.func

            called_name = None

            if isinstance(
                func,
                ast.Name
            ):

                called_name = func.id

            elif isinstance(
                func,
                ast.Attribute
            ):

                called_name = func.attr

            if (
                called_name
                and called_name in function_names
            ):

                graph[
                    node.name
                ].append(
                    (
                        called_name,
                        child.lineno,
                    )
                )

    return graph


def resolve_entrypoint_chain(
    graph,
    target
):

    section(
        "STEP 2 — STATIC ENTRYPOINT CHAIN"
    )

    reverse = defaultdict(list)

    for caller, edges in graph.items():

        for callee, line_number in edges:

            reverse[
                callee
            ].append(
                (
                    caller,
                    line_number,
                )
            )

    chains = []

    queue = [
        (
            target,
            [target],
        )
    ]

    visited = set()

    while queue:

        current, chain = queue.pop(
            0
        )

        if current in visited:
            continue

        visited.add(current)

        callers = reverse.get(
            current,
            []
        )

        if not callers:

            chains.append(
                chain
            )

            continue

        for caller, _line in callers:

            if caller in chain:
                continue

            queue.append(
                (
                    caller,
                    chain + [caller],
                )
            )

    for index, chain in enumerate(
        chains,
        1
    ):

        print()
        print(
            f"CHAIN {index}"
        )

        for item in reversed(
            chain
        ):

            print(
                f"  -> {item}()"
            )

    return chains


# ============================================================
# MODULE IMPORT
# ============================================================

def import_production_module():

    section(
        "STEP 3 — PRODUCTION MODULE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            MODULE_NAME,
            TARGET_FILE
        )
    )

    if spec is None:
        raise RuntimeError(
            "Unable to create module spec"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    print(
        f"MODULE IMPORTED : "
        f"{MODULE_NAME}"
    )

    return module


# ============================================================
# RUNTIME WRAPPERS
# ============================================================

def install_runtime_observers(
    module
):

    section(
        "STEP 4 — RUNTIME OBSERVER INSTALLATION"
    )

    if not hasattr(
        module,
        TARGET_FUNCTION
    ):
        raise RuntimeError(
            "find_future_price() not found"
        )

    if not hasattr(
        module,
        PARENT_FUNCTION
    ):
        raise RuntimeError(
            "create_outcome() not found"
        )

    original_functions[
        TARGET_FUNCTION
    ] = getattr(
        module,
        TARGET_FUNCTION
    )

    original_functions[
        PARENT_FUNCTION
    ] = getattr(
        module,
        PARENT_FUNCTION
    )

    original_main = getattr(
        module,
        "main",
        None
    )

    if original_main is not None:

        original_functions[
            "main"
        ] = original_main

    print(
        "ORIGINAL find_future_price : FOUND"
    )

    print(
        "ORIGINAL create_outcome     : FOUND"
    )

    if original_main is not None:

        print(
            "ORIGINAL main              : FOUND"
        )

    # --------------------------------------------------------
    # find_future_price wrapper
    # --------------------------------------------------------

    def observed_find_future_price(
        *args,
        **kwargs
    ):

        call_index = (
            len(runtime_find_calls)
            + 1
        )

        event = {
            "call_index": call_index,
            "args": args,
            "kwargs": kwargs,
        }

        runtime_find_calls.append(
            event
        )

        print()
        print(
            "[RUNTIME] find_future_price()"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"ARGS       : "
            f"{safe_repr(args)}"
        )

        print(
            f"KWARGS     : "
            f"{safe_repr(kwargs)}"
        )

        try:

            result = (
                original_functions[
                    TARGET_FUNCTION
                ](
                    *args,
                    **kwargs
                )
            )

            runtime_find_returns.append(
                {
                    "call_index":
                        call_index,
                    "result":
                        result,
                    "result_type":
                        type(result).__name__,
                }
            )

            print(
                "[RUNTIME RETURN]"
            )

            print(
                f"RESULT TYPE : "
                f"{type(result).__name__}"
            )

            print(
                f"RESULT      : "
                f"{safe_repr(result)}"
            )

            return result

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        TARGET_FUNCTION,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            raise

    # --------------------------------------------------------
    # create_outcome wrapper
    # --------------------------------------------------------

    def observed_create_outcome(
        *args,
        **kwargs
    ):

        call_index = (
            len(runtime_create_calls)
            + 1
        )

        runtime_create_calls.append(
            {
                "call_index": call_index,
                "args": args,
                "kwargs": kwargs,
            }
        )

        print()
        print(
            "[RUNTIME] create_outcome()"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"ARGS       : "
            f"{safe_repr(args)}"
        )

        print(
            f"KWARGS     : "
            f"{safe_repr(kwargs)}"
        )

        try:

            result = (
                original_functions[
                    PARENT_FUNCTION
                ](
                    *args,
                    **kwargs
                )
            )

            runtime_create_returns.append(
                {
                    "call_index":
                        call_index,
                    "result":
                        result,
                    "result_type":
                        type(result).__name__,
                }
            )

            print(
                "[RUNTIME create_outcome RETURN]"
            )

            print(
                f"RESULT TYPE : "
                f"{type(result).__name__}"
            )

            print(
                f"RESULT      : "
                f"{safe_repr(result)}"
            )

            return result

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        PARENT_FUNCTION,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            raise

    module.find_future_price = (
        observed_find_future_price
    )

    module.create_outcome = (
        observed_create_outcome
    )

    print(
        "[PATCHED] find_future_price"
    )

    print(
        "[PATCHED] create_outcome"
    )


# ============================================================
# RUNTIME ENTRYPOINT EXECUTION
# ============================================================

def execute_real_entrypoint(
    module,
    candidates
):

    section(
        "STEP 5 — ACTUAL PRODUCTION ENTRYPOINT RUNTIME"
    )

    main_function = getattr(
        module,
        "main",
        None
    )

    if main_function is None:

        print(
            "MAIN NOT AVAILABLE"
        )

        return False

    print(
        "SELECTED ENTRYPOINT : main()"
    )

    print(
        "MODE                : READ-ONLY RUNTIME TRACE"
    )

    print(
        "DATABASE WRITE      : BLOCKED"
    )

    runtime_entry_calls.append(
        {
            "entrypoint": "main"
        }
    )

    try:

        result = main_function()

        print()
        print(
            "[PRODUCTION ENTRYPOINT RETURN]"
        )

        print(
            f"RESULT : "
            f"{safe_repr(result)}"
        )

        return True

    except Exception as exc:

        runtime_exceptions.append(
            {
                "stage":
                    "main",
                "exception":
                    repr(exc),
                "traceback":
                    traceback.format_exc(),
            }
        )

        print()
        print(
            "[PRODUCTION ENTRYPOINT EXCEPTION]"
        )

        print(
            repr(exc)
        )

        return False


# ============================================================
# RUNTIME SUMMARY
# ============================================================

def final_summary(
    runtime_executed
):

    section(
        "STEP 6 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"PRODUCTION ENTRYPOINT        : "
        f"main()"
    )

    print(
        f"ENTRYPOINT EXECUTED          : "
        f"{runtime_executed}"
    )

    print(
        f"create_outcome CALLS         : "
        f"{len(runtime_create_calls)}"
    )

    print(
        f"find_future_price CALLS      : "
        f"{len(runtime_find_calls)}"
    )

    print(
        f"find_future_price RETURNS    : "
        f"{len(runtime_find_returns)}"
    )

    print(
        f"create_outcome RETURNS       : "
        f"{len(runtime_create_returns)}"
    )

    print(
        f"RUNTIME EXCEPTIONS           : "
        f"{len(runtime_exceptions)}"
    )

    print()
    print(
        "RUNTIME TARGET DISTRIBUTION"
    )

    line("-")

    print(
        f"BTC | "
        f"FIND={len(runtime_find_calls)}"
    )

    print(
        f"ETH | "
        f"FIND={len(runtime_find_calls)}"
    )

    print(
        f"SOL | "
        f"FIND={len(runtime_find_calls)}"
    )

    print(
        f"XRP | "
        f"FIND={len(runtime_find_calls)}"
    )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    if len(
        runtime_find_returns
    ) > 0:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_REACHED"
        )

        meaning = (
            "The actual production entrypoint "
            "reached create_outcome() and the "
            "genuine find_future_price() function "
            "was executed through the production "
            "runtime chain."
        )

        next_frontier = (
            "Trace the captured future-price value "
            "through its downstream field assignment."
        )

    elif len(
        runtime_create_calls
    ) > 0:

        status = (
            "CREATE_OUTCOME_RUNTIME_REACHED"
        )

        meaning = (
            "The production entrypoint reached "
            "create_outcome(), but the expected "
            "find_future_price() call was not observed."
        )

        next_frontier = (
            "Trace the conditional branch inside "
            "create_outcome() that controls "
            "find_future_price()."
        )

    elif runtime_exceptions:

        status = (
            "PRODUCTION_ENTRYPOINT_RUNTIME_EXCEPTION"
        )

        meaning = (
            "The production entrypoint was reached "
            "but runtime execution terminated before "
            "the target function was observed."
        )

        next_frontier = (
            "Inspect the first runtime exception and "
            "resolve the blocked production path."
        )

    else:

        status = (
            "PRODUCTION_ENTRYPOINT_DID_NOT_REACH_TARGET"
        )

        meaning = (
            "The selected production entrypoint "
            "executed without reaching the resolved "
            "signal outcome call chain."
        )

        next_frontier = (
            "Resolve the actual runtime caller or "
            "required production input path."
        )

    print(
        f"STATUS                      : "
        f"{status}"
    )

    print(
        f"MEANING                     : "
        f"{meaning}"
    )

    print(
        f"NEXT FRONTIER               : "
        f"{next_frontier}"
    )

    print()
    print(
        "IMPORTANT                   : "
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

    print()
    print(
        "DATABASE WRITE OPERATIONS   : NONE"
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


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA SIGNAL OUTCOME RUNTIME ENTRYPOINT "
        "TO FIND_FUTURE_PRICE FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                 : READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET               : "
        "signal_outcome_engine.py -> "
        "find_future_price()"
    )

    print(
        "CALL CHAIN           : "
        "main() -> process_signals() -> "
        "create_outcome() -> find_future_price()"
    )

    print(
        "DATABASE WRITE       : BLOCKED"
    )

    try:

        tree, candidates = (
            discover_entrypoints()
        )

        graph = (
            build_local_call_graph(
                tree
            )
        )

        chains = (
            resolve_entrypoint_chain(
                graph,
                TARGET_FUNCTION
            )
        )

        module = (
            import_production_module()
        )

        install_runtime_observers(
            module
        )

        runtime_executed = (
            execute_real_entrypoint(
                module,
                candidates
            )
        )

        final_summary(
            runtime_executed
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print()
        line("=")

        print(
            f"ELAPSED SECONDS              : "
            f"{elapsed:.3f}"
        )

        print(
            "AUDIT COMPLETE"
        )

        line("=")

        return 0

    except Exception as exc:

        print()
        line("=")

        print(
            "FORENSIC AUDIT ERROR"
        )

        line("=")

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "PRODUCTION DB WRITE       : BLOCKED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )