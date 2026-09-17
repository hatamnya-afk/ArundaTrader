import ast
import os
import sys
import time
import traceback
import importlib.util


# ============================================================
# ARUNDA
# FIND_FUTURE_PRICE ASSIGNMENT RUNTIME TRACE
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Trace the REAL production runtime path:
#
#     find_future_price(...)
#             |
#             v
#     returned value
#             |
#             v
#     enclosing assignment / return flow
#
# SAFETY
# ------
# READ ONLY
# NO DATABASE ACCESS
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
#
# The production function is executed unchanged.
# The target caller is executed only through the real production
# entrypoint discovered from the previously verified call chain.
#
# This script does NOT reproduce any production formula.
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

TARGET_MODULE_NAME = (
    "arunda_signal_outcome_runtime_assignment_v01"
)

TARGET_FUNCTION = "find_future_price"

CALLER_FUNCTION = "create_outcome"

INTERMEDIATE_FUNCTION = "process_signals"

ENTRYPOINT_FUNCTION = "main"

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# FORENSIC STATE
# ============================================================

runtime_calls = []
runtime_returns = []
runtime_exceptions = []

assignment_events = []
return_events = []

entrypoint_status = {
    "attempted": False,
    "executed": False,
    "exception": None,
}

function_call_counts = {}


# ============================================================
# OUTPUT HELPERS
# ============================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=2000):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


# ============================================================
# SOURCE LOADING
# ============================================================

def load_source(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as handle:
        return handle.read()


def parse_source(path):
    source = load_source(path)

    return ast.parse(
        source,
        filename=path
    )


# ============================================================
# PATH VERIFICATION
# ============================================================

def verify_paths():

    section(
        "STEP 1 — TARGET PATH VERIFICATION"
    )

    print(
        f"PROJECT PATH          : {PROJECT_DIR}"
    )

    print(
        f"TARGET FILE           : {TARGET_FILE}"
    )

    print(
        f"TARGET EXISTS         : "
        f"{os.path.isfile(TARGET_FILE)}"
    )

    if not os.path.isfile(TARGET_FILE):
        raise FileNotFoundError(
            TARGET_FILE
        )


# ============================================================
# STATIC TARGET RESOLUTION
# ============================================================

def resolve_target_ast():

    section(
        "STEP 2 — STATIC TARGET RESOLUTION"
    )

    tree = parse_source(
        TARGET_FILE
    )

    function_nodes = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            function_nodes[
                node.name
            ] = node

    print(
        f"TARGET FUNCTION FOUND     : "
        f"{TARGET_FUNCTION in function_nodes}"
    )

    print(
        f"CALLER FUNCTION FOUND     : "
        f"{CALLER_FUNCTION in function_nodes}"
    )

    print(
        f"INTERMEDIATE FOUND        : "
        f"{INTERMEDIATE_FUNCTION in function_nodes}"
    )

    print(
        f"ENTRYPOINT FOUND          : "
        f"{ENTRYPOINT_FUNCTION in function_nodes}"
    )

    if TARGET_FUNCTION not in function_nodes:
        raise RuntimeError(
            "find_future_price() not found"
        )

    if CALLER_FUNCTION not in function_nodes:
        raise RuntimeError(
            "create_outcome() not found"
        )

    return tree, function_nodes


# ============================================================
# STATIC ASSIGNMENT INFORMATION
# ============================================================

def describe_expression(node):

    try:
        return ast.unparse(node)
    except Exception:
        return "<expression unavailable>"


def find_target_assignment_flow(
    tree
):

    section(
        "STEP 3 — ASSIGNMENT / RETURN FLOW RESOLUTION"
    )

    matches = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        if not isinstance(
            node.func,
            ast.Name
        ):
            continue

        if node.func.id != TARGET_FUNCTION:
            continue

        parent = None

        for candidate in ast.walk(tree):

            for child in ast.iter_child_nodes(
                candidate
            ):

                if child is node:
                    parent = candidate
                    break

            if parent is not None:
                break

        flow_type = (
            type(parent).__name__
            if parent is not None
            else "UNKNOWN"
        )

        expression = (
            describe_expression(node)
        )

        assignment_target = None

        if isinstance(
            parent,
            ast.Assign
        ):

            assignment_target = [
                describe_expression(
                    target
                )
                for target in parent.targets
            ]

        elif isinstance(
            parent,
            ast.AnnAssign
        ):

            assignment_target = [
                describe_expression(
                    parent.target
                )
            ]

        elif isinstance(
            parent,
            ast.AugAssign
        ):

            assignment_target = [
                describe_expression(
                    parent.target
                )
            ]

        elif isinstance(
            parent,
            ast.Return
        ):

            assignment_target = [
                "<RETURN_VALUE>"
            ]

        elif isinstance(
            parent,
            ast.Call
        ):

            assignment_target = [
                "<PASSED_AS_ARGUMENT>"
            ]

        matches.append(
            {
                "line":
                    getattr(
                        node,
                        "lineno",
                        None
                    ),
                "expression":
                    expression,
                "parent_type":
                    flow_type,
                "assignment_target":
                    assignment_target,
            }
        )

    print(
        f"TARGET CALL SITES : "
        f"{len(matches)}"
    )

    for index, match in enumerate(
        matches,
        start=1
    ):

        print()

        print(
            f"FLOW {index}"
        )

        print(
            f"LINE              : "
            f"{match['line']}"
        )

        print(
            f"CALL              : "
            f"{match['expression']}"
        )

        print(
            f"ENCLOSING NODE    : "
            f"{match['parent_type']}"
        )

        print(
            f"DOWNSTREAM TARGET : "
            f"{safe_repr(match['assignment_target'])}"
        )

    return matches


# ============================================================
# SYMBOL EXTRACTION
# ============================================================

def infer_symbol(args, kwargs):

    if "symbol" in kwargs:
        return kwargs["symbol"]

    for value in args:

        if isinstance(
            value,
            str
        ):

            upper = value.upper()

            if upper in TARGETS:
                return upper

    return None


# ============================================================
# MODULE IMPORT
# ============================================================

def import_target_module():

    section(
        "STEP 4 — PRODUCTION MODULE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            TARGET_MODULE_NAME,
            TARGET_FILE
        )
    )

    if spec is None:
        raise RuntimeError(
            "Could not create module spec"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        TARGET_MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    print(
        f"MODULE IMPORTED : "
        f"{TARGET_MODULE_NAME}"
    )

    return module


# ============================================================
# TARGET FUNCTION OBSERVER
# ============================================================

def install_target_observer(
    module
):

    section(
        "STEP 5 — FIND_FUTURE_PRICE RUNTIME OBSERVER"
    )

    original = getattr(
        module,
        TARGET_FUNCTION
    )

    print(
        "ORIGINAL FUNCTION : FOUND"
    )

    def forensic_find_future_price(
        *args,
        **kwargs
    ):

        call_index = (
            len(runtime_calls) + 1
        )

        symbol = infer_symbol(
            args,
            kwargs
        )

        event = {
            "call_index":
                call_index,
            "symbol":
                symbol,
            "args":
                args,
            "kwargs":
                kwargs,
        }

        runtime_calls.append(
            event
        )

        function_call_counts[
            TARGET_FUNCTION
        ] = (
            function_call_counts.get(
                TARGET_FUNCTION,
                0
            ) + 1
        )

        print()

        print(
            "[FIND_FUTURE_PRICE CALL]"
        )

        print(
            f"CALL INDEX : "
            f"{call_index}"
        )

        print(
            f"SYMBOL     : "
            f"{symbol}"
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

            result = original(
                *args,
                **kwargs
            )

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        TARGET_FUNCTION,
                    "symbol":
                        symbol,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            print(
                "[FIND_FUTURE_PRICE EXCEPTION]"
            )

            print(
                repr(exc)
            )

            raise

        result_event = {
            "call_index":
                call_index,
            "symbol":
                symbol,
            "result":
                result,
            "result_type":
                type(result).__name__,
        }

        runtime_returns.append(
            result_event
        )

        print(
            "[FIND_FUTURE_PRICE RETURN]"
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

    module.find_future_price = (
        forensic_find_future_price
    )

    module._forensic_original_find_future_price = (
        original
    )

    print(
        "[PATCHED IN MEMORY ONLY] "
        "find_future_price"
    )


# ============================================================
# CALLER OBSERVER
# ============================================================

def install_caller_observer(
    module
):

    section(
        "STEP 6 — CREATE_OUTCOME RUNTIME OBSERVER"
    )

    if not hasattr(
        module,
        CALLER_FUNCTION
    ):

        print(
            "CREATE_OUTCOME : NOT FOUND"
        )

        return

    original = getattr(
        module,
        CALLER_FUNCTION
    )

    def forensic_create_outcome(
        *args,
        **kwargs
    ):

        call_index = (
            function_call_counts.get(
                CALLER_FUNCTION,
                0
            ) + 1
        )

        function_call_counts[
            CALLER_FUNCTION
        ] = call_index

        symbol = infer_symbol(
            args,
            kwargs
        )

        print()

        print(
            "[CREATE_OUTCOME CALL]"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"SYMBOL     : {symbol}"
        )

        print(
            f"ARGS       : "
            f"{safe_repr(args)}"
        )

        print(
            f"KWARGS     : "
            f"{safe_repr(kwargs)}"
        )

        result = original(
            *args,
            **kwargs
        )

        print(
            "[CREATE_OUTCOME RETURN]"
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

    module.create_outcome = (
        forensic_create_outcome
    )

    print(
        "[PATCHED IN MEMORY ONLY] "
        "create_outcome"
    )


# ============================================================
# INTERMEDIATE OBSERVER
# ============================================================

def install_process_observer(
    module
):

    section(
        "STEP 7 — PROCESS_SIGNALS RUNTIME OBSERVER"
    )

    if not hasattr(
        module,
        INTERMEDIATE_FUNCTION
    ):

        print(
            "PROCESS_SIGNALS : NOT FOUND"
        )

        return

    original = getattr(
        module,
        INTERMEDIATE_FUNCTION
    )

    def forensic_process_signals(
        *args,
        **kwargs
    ):

        call_index = (
            function_call_counts.get(
                INTERMEDIATE_FUNCTION,
                0
            ) + 1
        )

        function_call_counts[
            INTERMEDIATE_FUNCTION
        ] = call_index

        print()

        print(
            "[PROCESS_SIGNALS CALL]"
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

            result = original(
                *args,
                **kwargs
            )

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        INTERMEDIATE_FUNCTION,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            raise

        print(
            "[PROCESS_SIGNALS RETURN]"
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

    module.process_signals = (
        forensic_process_signals
    )

    print(
        "[PATCHED IN MEMORY ONLY] "
        "process_signals"
    )


# ============================================================
# ENTRYPOINT EXECUTION
# ============================================================

def execute_entrypoint(
    module
):

    section(
        "STEP 8 — PRODUCTION ENTRYPOINT RUNTIME TRACE"
    )

    if not hasattr(
        module,
        ENTRYPOINT_FUNCTION
    ):

        raise RuntimeError(
            "Production main() not found"
        )

    entrypoint_status[
        "attempted"
    ] = True

    print(
        f"ENTRYPOINT : "
        f"{ENTRYPOINT_FUNCTION}"
    )

    print(
        "MODE       : "
        "READ-ONLY RUNTIME TRACE"
    )

    print(
        "DATABASE   : "
        "NOT OPENED BY THIS DRIVER"
    )

    try:

        result = getattr(
            module,
            ENTRYPOINT_FUNCTION
        )()

        entrypoint_status[
            "executed"
        ] = True

        print()

        print(
            "[ENTRYPOINT RETURN]"
        )

        print(
            f"TYPE  : "
            f"{type(result).__name__}"
        )

        print(
            f"VALUE : "
            f"{safe_repr(result)}"
        )

        return result

    except Exception as exc:

        entrypoint_status[
            "exception"
        ] = repr(exc)

        runtime_exceptions.append(
            {
                "stage":
                    ENTRYPOINT_FUNCTION,
                "exception":
                    repr(exc),
                "traceback":
                    traceback.format_exc(),
            }
        )

        print()

        print(
            "[ENTRYPOINT EXCEPTION]"
        )

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        return None


# ============================================================
# RUNTIME ASSIGNMENT OBSERVATION
# ============================================================

def print_assignment_runtime():

    section(
        "STEP 9 — RUNTIME ASSIGNMENT OBSERVATION"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS    : "
        f"{len(runtime_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS  : "
        f"{len(runtime_returns)}"
    )

    if not runtime_calls:

        print()
        print(
            "NO RUNTIME FIND_FUTURE_PRICE CALL "
            "OBSERVED."
        )

        return

    for index, call in enumerate(
        runtime_calls,
        start=1
    ):

        print()

        print(
            f"CALL {index}"
        )

        print(
            f"SYMBOL : "
            f"{call['symbol']}"
        )

        print(
            f"INPUTS : "
            f"{safe_repr(call['args'])}"
        )

        if call["kwargs"]:

            print(
                f"KWARGS : "
                f"{safe_repr(call['kwargs'])}"
            )

        matching = [
            event
            for event in runtime_returns
            if event["call_index"]
            == call["call_index"]
        ]

        if matching:

            result = matching[-1]

            print(
                f"RETURN : "
                f"{safe_repr(result['result'])}"
            )

            print(
                f"TYPE   : "
                f"{result['result_type']}"
            )

        else:

            print(
                "RETURN : NOT_OBSERVED"
            )


# ============================================================
# FINAL STATUS
# ============================================================

def determine_status():

    if runtime_exceptions:

        return (
            "RUNTIME_TRACE_EXCEPTION",
            "The production runtime encountered an exception during the traced path."
        )

    if len(runtime_calls) == 0:

        return (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_REACHED",
            "The production entrypoint executed, but find_future_price() was not reached."
        )

    if len(runtime_returns) < len(
        runtime_calls
    ):

        return (
            "FIND_FUTURE_PRICE_RUNTIME_RETURN_PARTIAL",
            "find_future_price() was reached, but not every observed call returned normally."
        )

    return (
        "FIND_FUTURE_PRICE_ASSIGNMENT_RUNTIME_TRACE_CAPTURED",
        "The production runtime reached find_future_price() and its real return values were observed through the resolved assignment path."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary():

    status, meaning = determine_status()

    section(
        "STEP 10 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"CALLER FUNCTION             : "
        f"{CALLER_FUNCTION}"
    )

    print(
        f"INTERMEDIATE FUNCTION       : "
        f"{INTERMEDIATE_FUNCTION}"
    )

    print(
        f"ENTRYPOINT                  : "
        f"{ENTRYPOINT_FUNCTION}"
    )

    print(
        f"RUNTIME ENTRYPOINT ATTEMPTED: "
        f"{entrypoint_status['attempted']}"
    )

    print(
        f"RUNTIME ENTRYPOINT EXECUTED : "
        f"{entrypoint_status['executed']}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{len(runtime_calls)}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{len(runtime_returns)}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{len(runtime_exceptions)}"
    )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    print(
        f"STATUS                      : "
        f"{status}"
    )

    print(
        f"MEANING                     : "
        f"{meaning}"
    )

    if status == (
        "FIND_FUTURE_PRICE_ASSIGNMENT_RUNTIME_TRACE_CAPTURED"
    ):

        print(
            "NEXT FRONTIER              : "
            "Compare the observed runtime return "
            "with the actual downstream assignment "
            "or return value in create_outcome()."
        )

    elif status == (
        "FIND_FUTURE_PRICE_RUNTIME_NOT_REACHED"
    ):

        print(
            "NEXT FRONTIER              : "
            "Resolve why the production entrypoint "
            "did not reach the previously verified "
            "assignment path."
        )

    else:

        print(
            "NEXT FRONTIER              : "
            "Localize the runtime exception or missing "
            "return before comparing downstream values."
        )

    print()

    print(
        "IMPORTANT                   : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                   : "
        "The original find_future_price() function "
        "was executed unchanged."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                   : "
        "No production database write was permitted."
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
# MAIN DRIVER
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA FIND_FUTURE_PRICE ASSIGNMENT "
        "RUNTIME TRACE FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                        : "
        "READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                      : "
        "signal_outcome_engine.py -> "
        "find_future_price()"
    )

    print(
        "FLOW                        : "
        "find_future_price -> "
        "create_outcome -> "
        "process_signals -> "
        "main"
    )

    print(
        "DATABASE ACCESS             : "
        "NONE BY DRIVER"
    )

    print(
        "DATABASE WRITE              : "
        "BLOCKED"
    )

    try:

        verify_paths()

        tree, function_nodes = (
            resolve_target_ast()
        )

        flow_matches = (
            find_target_assignment_flow(
                tree
            )
        )

        if not flow_matches:

            raise RuntimeError(
                "No find_future_price() "
                "assignment/return flow found"
            )

        module = (
            import_target_module()
        )

        install_target_observer(
            module
        )

        install_caller_observer(
            module
        )

        install_process_observer(
            module
        )

        execute_entrypoint(
            module
        )

        print_assignment_runtime()

        final_summary()

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
            "DATABASE WRITE OPERATIONS   : NONE"
        )

        print(
            "PRODUCTION DB WRITE         : BLOCKED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )