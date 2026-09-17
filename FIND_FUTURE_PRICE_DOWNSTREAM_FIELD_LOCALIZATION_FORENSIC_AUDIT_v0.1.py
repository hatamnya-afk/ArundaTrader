import ast
import importlib.util
import os
import sys
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA
# FIND_FUTURE_PRICE DOWNSTREAM FIELD LOCALIZATION
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Localize the exact field/key/position in create_outcome()
# receiving the real return value of find_future_price().
#
# SAFETY
# ------
# STATIC + READ-ONLY RUNTIME FORENSICS
#
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
#
# The original production functions are executed unchanged.
# No production formula is modified.
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
    "arunda_signal_outcome_field_localization_v01"
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

runtime_calls = defaultdict(list)
runtime_returns = defaultdict(list)
runtime_create_returns = defaultdict(list)

runtime_exceptions = []

field_observations = []

entrypoint_status = {
    "executed": False,
    "exception": None,
}

original_find_future_price = None
original_create_outcome = None


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


def safe_repr(value, limit=1600):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def normalize(value):
    if value is None:
        return None

    if isinstance(value, dict):
        return dict(value)

    try:
        return dict(value)
    except Exception:
        return value


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


# ============================================================
# STATIC FIELD LOCALIZATION
# ============================================================

def find_function_node(tree, name):
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):
            if node.name == name:
                return node

    return None


def call_contains_target(node):
    if not isinstance(node, ast.Call):
        return False

    func = node.func

    if isinstance(func, ast.Name):
        return func.id == TARGET_FUNCTION

    if isinstance(func, ast.Attribute):
        return func.attr == TARGET_FUNCTION

    return False


def describe_assignment(node):
    if isinstance(node, ast.Assign):
        targets = []

        for target in node.targets:
            targets.append(
                ast.unparse(target)
            )

        return {
            "type": "Assign",
            "targets": targets,
            "statement": ast.unparse(node),
            "line": node.lineno,
        }

    if isinstance(node, ast.AnnAssign):
        return {
            "type": "AnnAssign",
            "targets": [
                ast.unparse(node.target)
            ],
            "statement": ast.unparse(node),
            "line": node.lineno,
        }

    if isinstance(node, ast.Return):
        return {
            "type": "Return",
            "targets": [],
            "statement": ast.unparse(node),
            "line": node.lineno,
        }

    if isinstance(node, ast.Expr):
        return {
            "type": "Expr",
            "targets": [],
            "statement": ast.unparse(node),
            "line": node.lineno,
        }

    return {
        "type": type(node).__name__,
        "targets": [],
        "statement": ast.unparse(node),
        "line": getattr(node, "lineno", None),
    }


def localize_target_assignment(function_node):
    observations = []

    for node in ast.walk(function_node):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.Return,
                ast.Expr,
            )
        ):

            if not isinstance(node, ast.Expr):

                value = getattr(
                    node,
                    "value",
                    None
                )

                if value is not None:

                    for child in ast.walk(value):

                        if call_contains_target(
                            child
                        ):

                            info = (
                                describe_assignment(
                                    node
                                )
                            )

                            info[
                                "target_call_line"
                            ] = child.lineno

                            info[
                                "target_call"
                            ] = ast.unparse(child)

                            observations.append(
                                info
                            )

                            break

    return observations


# ============================================================
# STATIC AUDIT
# ============================================================

def static_localization():

    section(
        "STEP 1 — STATIC DOWNSTREAM FIELD LOCALIZATION"
    )

    if not os.path.isfile(TARGET_FILE):
        raise FileNotFoundError(
            TARGET_FILE
        )

    source = load_source(
        TARGET_FILE
    )

    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    target_node = find_function_node(
        tree,
        TARGET_FUNCTION
    )

    parent_node = find_function_node(
        tree,
        PARENT_FUNCTION
    )

    print(
        f"TARGET FILE              : {TARGET_FILE}"
    )

    print(
        f"TARGET FUNCTION          : {TARGET_FUNCTION}"
    )

    print(
        f"PARENT FUNCTION          : {PARENT_FUNCTION}"
    )

    print(
        f"TARGET EXISTS            : "
        f"{target_node is not None}"
    )

    print(
        f"PARENT EXISTS            : "
        f"{parent_node is not None}"
    )

    if parent_node is None:
        raise RuntimeError(
            "create_outcome() not found"
        )

    observations = (
        localize_target_assignment(
            parent_node
        )
    )

    print()
    print(
        "STATIC DOWNSTREAM OBSERVATIONS"
    )

    line("-")

    if not observations:

        print(
            "NO DIRECT AST ASSIGNMENT "
            "CONTAINING find_future_price() "
            "WAS FOUND."
        )

    else:

        for index, observation in enumerate(
            observations,
            1
        ):

            print()
            print(
                f"OBSERVATION {index}"
            )

            print(
                f"STATEMENT TYPE : "
                f"{observation['type']}"
            )

            print(
                f"LINE           : "
                f"{observation['line']}"
            )

            print(
                f"CALL LINE      : "
                f"{observation['target_call_line']}"
            )

            print(
                f"TARGET CALL    : "
                f"{observation['target_call']}"
            )

            print(
                f"TARGET FIELDS  : "
                f"{observation['targets']}"
            )

            print(
                f"STATEMENT      : "
                f"{observation['statement']}"
            )

    return observations


# ============================================================
# PRODUCTION IMPORT
# ============================================================

def import_production_module():

    section(
        "STEP 2 — PRODUCTION MODULE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            MODULE_NAME,
            TARGET_FILE
        )
    )

    if spec is None:
        raise RuntimeError(
            "Unable to create module specification"
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
        f"MODULE IMPORTED : {MODULE_NAME}"
    )

    return module


# ============================================================
# RUNTIME VALUE COMPARISON
# ============================================================

def recursively_find_equal(
    container,
    target_value,
    path=()
):
    """
    Search recursively for exact equality with target_value.

    This is observational only.
    No production object is modified.
    """

    matches = []

    try:

        if isinstance(
            container,
            dict
        ):

            for key, value in container.items():

                current_path = (
                    path + (key,)
                )

                try:
                    if value == target_value:
                        matches.append(
                            {
                                "path": current_path,
                                "value": value,
                            }
                        )
                except Exception:
                    pass

                matches.extend(
                    recursively_find_equal(
                        value,
                        target_value,
                        current_path
                    )
                )

        elif isinstance(
            container,
            (list, tuple)
        ):

            for index, value in enumerate(
                container
            ):

                current_path = (
                    path + (index,)
                )

                try:
                    if value == target_value:
                        matches.append(
                            {
                                "path": current_path,
                                "value": value,
                            }
                        )
                except Exception:
                    pass

                matches.extend(
                    recursively_find_equal(
                        value,
                        target_value,
                        current_path
                    )
                )

    except Exception:
        pass

    return matches


# ============================================================
# RUNTIME WRAPPERS
# ============================================================

def install_runtime_observers(module):

    section(
        "STEP 3 — RUNTIME OBSERVER INSTALLATION"
    )

    global original_find_future_price
    global original_create_outcome

    original_find_future_price = (
        module.find_future_price
    )

    original_create_outcome = (
        module.create_outcome
    )

    print(
        "ORIGINAL find_future_price : FOUND"
    )

    print(
        "ORIGINAL create_outcome     : FOUND"
    )

    def forensic_find_future_price(
        *args,
        **kwargs
    ):

        call_index = (
            sum(
                len(v)
                for v in runtime_calls.values()
            )
            + 1
        )

        event = {
            "call_index": call_index,
            "args": args,
            "kwargs": kwargs,
        }

        runtime_calls[
            "GLOBAL"
        ].append(
            event
        )

        print()
        print(
            "[RUNTIME find_future_price]"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"ARGS       : {safe_repr(args)}"
        )

        print(
            f"KWARGS     : {safe_repr(kwargs)}"
        )

        try:

            result = (
                original_find_future_price(
                    *args,
                    **kwargs
                )
            )

            runtime_returns[
                "GLOBAL"
            ].append(
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
                "[RETURN CAPTURED]"
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
                        "find_future_price",
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            raise

    def forensic_create_outcome(
        *args,
        **kwargs
    ):

        call_index = (
            len(
                runtime_create_returns[
                    "GLOBAL"
                ]
            )
            + 1
        )

        print()
        print(
            "[RUNTIME create_outcome]"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"ARGS       : {safe_repr(args)}"
        )

        print(
            f"KWARGS     : {safe_repr(kwargs)}"
        )

        try:

            result = (
                original_create_outcome(
                    *args,
                    **kwargs
                )
            )

            runtime_create_returns[
                "GLOBAL"
            ].append(
                {
                    "call_index":
                        call_index,
                    "args":
                        args,
                    "kwargs":
                        kwargs,
                    "result":
                        result,
                    "result_type":
                        type(result).__name__,
                }
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

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        "create_outcome",
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            raise

    module.find_future_price = (
        forensic_find_future_price
    )

    module.create_outcome = (
        forensic_create_outcome
    )

    print(
        "[PATCHED] find_future_price"
    )

    print(
        "[PATCHED] create_outcome"
    )


# ============================================================
# SAFE RUNTIME INVOCATION
# ============================================================

def execute_safe_runtime(
    module
):

    section(
        "STEP 4 — READ-ONLY RUNTIME TRACE"
    )

    print(
        "PRODUCTION main() : NOT CALLED"
    )

    print(
        "TARGET             : create_outcome()"
    )

    print(
        "MODE               : SAFE OBSERVATION"
    )

    # --------------------------------------------------------
    # We intentionally do not guess arguments.
    #
    # The purpose is to use an already exposed test-safe
    # production path only if one exists.
    # --------------------------------------------------------

    candidates = []

    for name in dir(module):

        if name.startswith("_"):
            continue

        try:
            value = getattr(
                module,
                name
            )
        except Exception:
            continue

        if callable(value):

            lowered = name.lower()

            if (
                "test" in lowered
                or "debug" in lowered
                or "diagnostic" in lowered
            ):

                candidates.append(
                    name
                )

    if candidates:

        print(
            "SAFE HELPER CANDIDATES :"
        )

        for name in candidates[:20]:
            print(
                f"  {name}"
            )

    else:

        print(
            "SAFE HELPER CANDIDATES : NONE"
        )

    print()
    print(
        "NO ARGUMENTS WILL BE INVENTED."
    )

    print(
        "NO production main() WILL BE CALLED."
    )

    print(
        "NO blind create_outcome() invocation "
        "will be performed."
    )

    return None


# ============================================================
# FIELD LOCALIZATION FROM CAPTURED RETURN
# ============================================================

def localize_runtime_field():

    section(
        "STEP 5 — RUNTIME DOWNSTREAM FIELD LOCALIZATION"
    )

    returns = (
        runtime_returns.get(
            "GLOBAL",
            []
        )
    )

    create_returns = (
        runtime_create_returns.get(
            "GLOBAL",
            []
        )
    )

    print(
        f"find_future_price RETURNS : "
        f"{len(returns)}"
    )

    print(
        f"create_outcome RETURNS    : "
        f"{len(create_returns)}"
    )

    if not returns:

        print()
        print(
            "No find_future_price() runtime "
            "return was captured."
        )

        return []

    if not create_returns:

        print()
        print(
            "No create_outcome() runtime return "
            "was captured."
        )

        return []

    matches = []

    for future_event in returns:

        future_value = (
            future_event["result"]
        )

        print()
        print(
            "CAPTURED FUTURE PRICE"
        )

        print(
            f"CALL INDEX : "
            f"{future_event['call_index']}"
        )

        print(
            f"VALUE      : "
            f"{safe_repr(future_value)}"
        )

        for create_event in create_returns:

            result = (
                create_event["result"]
            )

            normalized = normalize(
                result
            )

            found = (
                recursively_find_equal(
                    normalized,
                    future_value
                )
            )

            if found:

                for match in found:

                    observation = {
                        "future_price":
                            future_value,
                        "create_outcome_call":
                            create_event[
                                "call_index"
                            ],
                        "path":
                            match["path"],
                        "assigned_value":
                            match["value"],
                    }

                    matches.append(
                        observation
                    )

                    print()
                    print(
                        "[FIELD MATCH]"
                    )

                    print(
                        f"PATH          : "
                        f"{match['path']}"
                    )

                    print(
                        f"VALUE         : "
                        f"{safe_repr(match['value'])}"
                    )

            else:

                print(
                    "NO EXACT VALUE MATCH "
                    "FOUND IN create_outcome RETURN"
                )

    field_observations.extend(
        matches
    )

    return matches


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary(
    static_observations,
    runtime_matches
):

    section(
        "STEP 6 — FINAL FORENSIC SUMMARY"
    )

    future_calls = (
        sum(
            len(v)
            for v in runtime_calls.values()
        )
    )

    future_returns = (
        sum(
            len(v)
            for v in runtime_returns.values()
        )
    )

    create_calls = (
        len(
            runtime_create_returns[
                "GLOBAL"
            ]
        )
    )

    print(
        f"STATIC FIELD OBSERVATIONS : "
        f"{len(static_observations)}"
    )

    print(
        f"find_future_price CALLS   : "
        f"{future_calls}"
    )

    print(
        f"find_future_price RETURNS : "
        f"{future_returns}"
    )

    print(
        f"create_outcome RETURNS    : "
        f"{create_calls}"
    )

    print(
        f"FIELD VALUE MATCHES       : "
        f"{len(runtime_matches)}"
    )

    print(
        f"RUNTIME EXCEPTIONS        : "
        f"{len(runtime_exceptions)}"
    )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    if runtime_matches:

        status = (
            "FIND_FUTURE_PRICE_DOWNSTREAM_FIELD_LOCALIZED"
        )

        meaning = (
            "The captured production future-price "
            "value was located inside the downstream "
            "create_outcome() return structure."
        )

        next_frontier = (
            "Compare the localized downstream field "
            "against the final persisted or consumed "
            "value."
        )

    elif future_returns > 0:

        status = (
            "FIND_FUTURE_PRICE_DOWNSTREAM_FIELD_NOT_MATCHED"
        )

        meaning = (
            "The genuine future-price return was "
            "captured, but an exact value match was "
            "not found in the observed create_outcome() "
            "return structure."
        )

        next_frontier = (
            "Trace object construction between the "
            "find_future_price() assignment and the "
            "final create_outcome() return."
        )

    elif future_calls == 0:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The selected runtime path did not reach "
            "find_future_price()."
        )

        next_frontier = (
            "Resolve the production runtime entrypoint "
            "that reaches create_outcome()."
        )

    else:

        status = (
            "FIND_FUTURE_PRICE_FIELD_LOCALIZATION_INCOMPLETE"
        )

        meaning = (
            "Runtime observation was incomplete."
        )

        next_frontier = (
            "Resolve the missing downstream runtime "
            "assignment path."
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
        "No production main() was called."
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
        "ARUNDA FIND_FUTURE_PRICE DOWNSTREAM "
        "FIELD LOCALIZATION FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                        : "
        "STATIC + READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                      : "
        "signal_outcome_engine.py -> "
        "find_future_price()"
    )

    print(
        "DOWNSTREAM                  : "
        "create_outcome()"
    )

    print(
        "PRODUCTION WRITE            : BLOCKED"
    )

    try:

        static_observations = (
            static_localization()
        )

        module = (
            import_production_module()
        )

        install_runtime_observers(
            module
        )

        execute_safe_runtime(
            module
        )

        runtime_matches = (
            localize_runtime_field()
        )

        final_summary(
            static_observations,
            runtime_matches
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