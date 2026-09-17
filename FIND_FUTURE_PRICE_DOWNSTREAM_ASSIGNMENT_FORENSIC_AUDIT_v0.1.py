import ast
import os
import sys
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA
# FIND FUTURE PRICE
# DOWNSTREAM ASSIGNMENT FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Resolve what production code does with the REAL return value
# of:
#
#     find_future_price(...)
#
# The previous frontier proved:
#
#     find_future_price()
#     -> REAL RUNTIME INPUT CAPTURED
#     -> REAL RUNTIME OUTPUT CAPTURED
#
# This audit now traces the next static step:
#
#     future_price = find_future_price(...)
#                    |
#                    v
#     assignment / comparison / return / object field /
#     dictionary / function argument / downstream consumer
#
# SAFETY
# ------
# STATIC READ-ONLY FORENSICS
#
# NO production execution
# NO production main()
# NO database connection
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
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

TARGET_FUNCTION = "create_outcome"
TARGET_CALL = "find_future_price"

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# FORENSIC STATE
# ============================================================

functions = {}
classes = {}

find_future_price_calls = []
assignment_observations = []
downstream_observations = []
return_observations = []
comparison_observations = []
argument_observations = []
attribute_observations = []
subscript_observations = []

parse_errors = []

python_files = []
parsed_files = []

excluded_files = []


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


def safe_repr(value, limit=1600):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


# ============================================================
# FILE EXCLUSION
# ============================================================

EXCLUDED_NAME_PARTS = (
    "forensic",
    "audit",
    "diagnostic",
    "discovery",
    "trace",
    "repair",
    "test",
    "backup",
    "before_",
    "after_",
    "snapshot",
    "probe",
    "debug",
    "verify",
    "verification",
    "inspection",
    "inspect",
    "temporary",
    "tmp",
)


def should_exclude_file(path):
    name = os.path.basename(path).lower()

    if name == os.path.basename(__file__).lower():
        return True

    for part in EXCLUDED_NAME_PARTS:
        if part in name:
            return True

    return False


# ============================================================
# PROJECT FILE DISCOVERY
# ============================================================

def discover_python_files():

    section(
        "STEP 1 — PRODUCTION PYTHON FILE DISCOVERY"
    )

    discovered = []

    for root, dirs, files in os.walk(PROJECT_DIR):

        dirs[:] = [
            directory
            for directory in dirs
            if directory not in {
                "__pycache__",
                ".git",
                ".venv",
                "venv",
                "env",
                "node_modules",
            }
        ]

        for filename in files:

            if not filename.endswith(".py"):
                continue

            full_path = os.path.join(
                root,
                filename
            )

            if should_exclude_file(full_path):

                excluded_files.append(
                    full_path
                )

                continue

            discovered.append(
                full_path
            )

    # Always include the real target file.
    if os.path.isfile(TARGET_FILE):
        if TARGET_FILE not in discovered:
            discovered.append(TARGET_FILE)

    python_files.extend(
        sorted(set(discovered))
    )

    print(
        f"PYTHON FILES SELECTED : "
        f"{len(python_files)}"
    )

    print(
        f"EXCLUDED FILES        : "
        f"{len(excluded_files)}"
    )

    return python_files


# ============================================================
# STATIC PARSING
# ============================================================

source_cache = {}


def parse_python_file(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8-sig"
        ) as handle:

            source = handle.read()

        source_cache[path] = source

        tree = ast.parse(
            source,
            filename=path
        )

        parsed_files.append(path)

        return tree

    except Exception as exc:

        parse_errors.append(
            {
                "file": path,
                "exception": repr(exc),
            }
        )

        return None


def parse_all_files():

    section(
        "STEP 2 — STATIC PARSING"
    )

    trees = {}

    for path in python_files:

        tree = parse_python_file(
            path
        )

        if tree is not None:
            trees[path] = tree

    print(
        f"FILES PARSED : "
        f"{len(parsed_files)}"
    )

    print(
        f"PARSE ERRORS : "
        f"{len(parse_errors)}"
    )

    return trees


# ============================================================
# SYMBOL DISCOVERY
# ============================================================

def discover_symbols(trees):

    section(
        "STEP 3 — SYMBOL DISCOVERY"
    )

    for path, tree in trees.items():

        for node in ast.walk(tree):

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            ):

                qualified = (
                    f"{os.path.basename(path)}"
                    f"::{node.name}"
                )

                functions[qualified] = {
                    "file": path,
                    "name": node.name,
                    "line": node.lineno,
                    "node": node,
                }

            elif isinstance(
                node,
                ast.ClassDef
            ):

                qualified = (
                    f"{os.path.basename(path)}"
                    f"::{node.name}"
                )

                classes[qualified] = {
                    "file": path,
                    "name": node.name,
                    "line": node.lineno,
                    "node": node,
                }

    print(
        f"FUNCTIONS DISCOVERED : "
        f"{len(functions)}"
    )

    print(
        f"CLASSES DISCOVERED    : "
        f"{len(classes)}"
    )


# ============================================================
# SOURCE SEGMENT HELPERS
# ============================================================

def source_segment(path, node):

    source = source_cache.get(path)

    if source is None:
        return "<SOURCE UNAVAILABLE>"

    try:

        segment = ast.get_source_segment(
            source,
            node
        )

        if segment:
            return segment

    except Exception:
        pass

    return "<SOURCE SEGMENT UNAVAILABLE>"


def node_description(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return (
            f"{node_description(node.value)}"
            f".{node.attr}"
        )

    if isinstance(node, ast.Constant):
        return safe_repr(node.value)

    if isinstance(node, ast.Subscript):
        return (
            f"{node_description(node.value)}[...]"
        )

    if isinstance(node, ast.Call):
        return (
            f"{node_description(node.func)}(...)"
        )

    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__


# ============================================================
# TARGET FUNCTION RESOLUTION
# ============================================================

def resolve_target_function():

    section(
        "STEP 4 — TARGET FUNCTION RESOLUTION"
    )

    target_node = None

    for qualified, info in functions.items():

        if (
            info["file"] == TARGET_FILE
            and info["name"] == TARGET_FUNCTION
        ):

            target_node = info
            break

    if target_node is None:

        raise RuntimeError(
            "create_outcome() not found in signal_outcome_engine.py"
        )

    print(
        f"TARGET FILE     : "
        f"{TARGET_FILE}"
    )

    print(
        f"TARGET FUNCTION : "
        f"{TARGET_FUNCTION}()"
    )

    print(
        f"TARGET LINE     : "
        f"{target_node['line']}"
    )

    return target_node


# ============================================================
# FIND find_future_price CALLS
# ============================================================

def is_target_call(node):

    if not isinstance(node, ast.Call):
        return False

    func = node.func

    if isinstance(func, ast.Name):

        return func.id == TARGET_CALL

    if isinstance(func, ast.Attribute):

        return func.attr == TARGET_CALL

    return False


def find_target_calls(target_info):

    section(
        "STEP 5 — find_future_price() CALL RESOLUTION"
    )

    node = target_info["node"]

    for child in ast.walk(node):

        if not is_target_call(child):
            continue

        observation = {
            "line": child.lineno,
            "column": getattr(
                child,
                "col_offset",
                None
            ),
            "call": node_description(child),
            "source": source_segment(
                TARGET_FILE,
                child
            ),
            "parent": None,
        }

        find_future_price_calls.append(
            observation
        )

    print(
        f"find_future_price CALL SITES : "
        f"{len(find_future_price_calls)}"
    )

    for event in find_future_price_calls:

        print(
            f"LINE={event['line']:<6} "
            f"CALL={event['call']}"
        )

        print(
            f"  SOURCE: "
            f"{event['source']}"
        )

    return find_future_price_calls


# ============================================================
# ASSIGNMENT PARENT DETECTION
# ============================================================

def contains_target_call(node):

    for child in ast.walk(node):

        if child is node:
            continue

        if is_target_call(child):
            return True

    return False


def assignment_target_description(target):

    if isinstance(target, ast.Name):
        return target.id

    if isinstance(target, ast.Attribute):
        return node_description(target)

    if isinstance(target, ast.Subscript):
        return node_description(target)

    if isinstance(target, (ast.Tuple, ast.List)):

        return (
            "["
            + ", ".join(
                assignment_target_description(
                    element
                )
                for element in target.elts
            )
            + "]"
        )

    return node_description(target)


def inspect_assignments(target_info):

    section(
        "STEP 6 — DOWNSTREAM ASSIGNMENT DETECTION"
    )

    node = target_info["node"]

    for parent_candidate in ast.walk(node):

        if isinstance(
            parent_candidate,
            ast.Assign
        ):

            if not contains_target_call(
                parent_candidate.value
            ):
                continue

            for target in parent_candidate.targets:

                observation = {
                    "type": "Assign",
                    "line": parent_candidate.lineno,
                    "target":
                        assignment_target_description(
                            target
                        ),
                    "value":
                        node_description(
                            parent_candidate.value
                        ),
                    "source":
                        source_segment(
                            TARGET_FILE,
                            parent_candidate
                        ),
                }

                assignment_observations.append(
                    observation
                )

        elif isinstance(
            parent_candidate,
            ast.AnnAssign
        ):

            if not contains_target_call(
                parent_candidate.value
            ):
                continue

            observation = {
                "type": "AnnAssign",
                "line": parent_candidate.lineno,
                "target":
                    assignment_target_description(
                        parent_candidate.target
                    ),
                "value":
                    node_description(
                        parent_candidate.value
                    ),
                "source":
                    source_segment(
                        TARGET_FILE,
                        parent_candidate
                    ),
            }

            assignment_observations.append(
                observation
            )

        elif isinstance(
            parent_candidate,
            ast.NamedExpr
        ):

            if not contains_target_call(
                parent_candidate.value
            ):
                continue

            observation = {
                "type": "NamedExpr",
                "line": parent_candidate.lineno,
                "target":
                    assignment_target_description(
                        parent_candidate.target
                    ),
                "value":
                    node_description(
                        parent_candidate.value
                    ),
                "source":
                    source_segment(
                        TARGET_FILE,
                        parent_candidate
                    ),
            }

            assignment_observations.append(
                observation
            )

    # Deduplicate.
    unique = {}

    for event in assignment_observations:

        key = (
            event["type"],
            event["line"],
            event["target"],
            event["source"],
        )

        unique[key] = event

    assignment_observations.clear()

    assignment_observations.extend(
        unique.values()
    )

    print(
        f"ASSIGNMENT OBSERVATIONS : "
        f"{len(assignment_observations)}"
    )

    for event in assignment_observations:

        print(
            f"LINE={event['line']:<6} "
            f"TYPE={event['type']:<10} "
            f"TARGET={event['target']}"
        )

        print(
            f"  VALUE : {event['value']}"
        )

        print(
            f"  SOURCE: {event['source']}"
        )


# ============================================================
# DOWNSTREAM VARIABLE USE
# ============================================================

def assigned_variable_names():

    names = set()

    for event in assignment_observations:

        target = event["target"]

        if (
            target.isidentifier()
        ):

            names.add(target)

    return names


def inspect_downstream_uses(target_info):

    section(
        "STEP 7 — DOWNSTREAM VARIABLE CONSUMPTION"
    )

    names = assigned_variable_names()

    print(
        f"ASSIGNED VARIABLES : "
        f"{len(names)}"
    )

    if not names:

        print(
            "No direct assignment variable "
            "was resolved."
        )

        return

    node = target_info["node"]

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Name
        ):
            continue

        if child.id not in names:
            continue

        # Skip the original Store operation.
        if isinstance(
            child.ctx,
            ast.Store
        ):
            continue

        parent_line = child.lineno

        observation = {
            "line": parent_line,
            "variable": child.id,
            "context": "READ",
            "parent": None,
            "source": source_segment(
                TARGET_FILE,
                child
            ),
        }

        downstream_observations.append(
            observation
        )

    # Deduplicate.
    unique = {}

    for event in downstream_observations:

        key = (
            event["line"],
            event["variable"],
            event["source"],
        )

        unique[key] = event

    downstream_observations.clear()

    downstream_observations.extend(
        unique.values()
    )

    print(
        f"DOWNSTREAM VARIABLE USES : "
        f"{len(downstream_observations)}"
    )

    for event in downstream_observations:

        print(
            f"LINE={event['line']:<6} "
            f"VARIABLE={event['variable']:<20} "
            f"SOURCE={event['source']}"
        )


# ============================================================
# RETURN FLOW
# ============================================================

def inspect_return_flow(target_info):

    section(
        "STEP 8 — RETURN FLOW DETECTION"
    )

    node = target_info["node"]

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Return
        ):
            continue

        if child.value is None:
            continue

        value_description = (
            node_description(
                child.value
            )
        )

        target_names = (
            assigned_variable_names()
        )

        related = False

        for target_name in target_names:

            for subnode in ast.walk(
                child.value
            ):

                if (
                    isinstance(
                        subnode,
                        ast.Name
                    )
                    and subnode.id == target_name
                ):

                    related = True
                    break

            if related:
                break

        if related:

            event = {
                "line": child.lineno,
                "value": value_description,
                "source": source_segment(
                    TARGET_FILE,
                    child
                ),
            }

            return_observations.append(
                event
            )

    print(
        f"RETURN OBSERVATIONS : "
        f"{len(return_observations)}"
    )

    for event in return_observations:

        print(
            f"LINE={event['line']:<6} "
            f"RETURN={event['value']}"
        )

        print(
            f"  SOURCE: {event['source']}"
        )


# ============================================================
# COMPARISON FLOW
# ============================================================

def inspect_comparisons(target_info):

    section(
        "STEP 9 — FUTURE PRICE COMPARISON / DECISION FLOW"
    )

    names = assigned_variable_names()

    node = target_info["node"]

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Compare
        ):
            continue

        relevant = False

        for subnode in ast.walk(child):

            if (
                isinstance(
                    subnode,
                    ast.Name
                )
                and subnode.id in names
            ):

                relevant = True
                break

        if not relevant:
            continue

        observation = {
            "line": child.lineno,
            "comparison":
                node_description(child),
            "source":
                source_segment(
                    TARGET_FILE,
                    child
                ),
        }

        comparison_observations.append(
            observation
        )

    print(
        f"COMPARISON OBSERVATIONS : "
        f"{len(comparison_observations)}"
    )

    for event in comparison_observations:

        print(
            f"LINE={event['line']:<6} "
            f"COMPARISON={event['comparison']}"
        )

        print(
            f"  SOURCE: {event['source']}"
        )


# ============================================================
# FUNCTION ARGUMENT FLOW
# ============================================================

def inspect_argument_flow(target_info):

    section(
        "STEP 10 — FUTURE PRICE FUNCTION-ARGUMENT FLOW"
    )

    names = assigned_variable_names()

    node = target_info["node"]

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Call
        ):
            continue

        relevant_arguments = []

        for index, argument in enumerate(
            child.args
        ):

            for subnode in ast.walk(
                argument
            ):

                if (
                    isinstance(
                        subnode,
                        ast.Name
                    )
                    and subnode.id in names
                ):

                    relevant_arguments.append(
                        {
                            "kind": "positional",
                            "index": index,
                            "variable": subnode.id,
                        }
                    )

        for keyword in child.keywords:

            if keyword.value is None:
                continue

            for subnode in ast.walk(
                keyword.value
            ):

                if (
                    isinstance(
                        subnode,
                        ast.Name
                    )
                    and subnode.id in names
                ):

                    relevant_arguments.append(
                        {
                            "kind": "keyword",
                            "name": keyword.arg,
                            "variable": subnode.id,
                        }
                    )

        if not relevant_arguments:
            continue

        observation = {
            "line": child.lineno,
            "call": node_description(child),
            "arguments": relevant_arguments,
            "source":
                source_segment(
                    TARGET_FILE,
                    child
                ),
        }

        argument_observations.append(
            observation
        )

    print(
        f"FUNCTION ARGUMENT OBSERVATIONS : "
        f"{len(argument_observations)}"
    )

    for event in argument_observations:

        print(
            f"LINE={event['line']:<6} "
            f"CALL={event['call']}"
        )

        print(
            f"  ARGUMENTS: "
            f"{safe_repr(event['arguments'])}"
        )

        print(
            f"  SOURCE: "
            f"{event['source']}"
        )


# ============================================================
# ATTRIBUTE ASSIGNMENT FLOW
# ============================================================

def inspect_attribute_flow(target_info):

    section(
        "STEP 11 — OBJECT ATTRIBUTE ASSIGNMENT FLOW"
    )

    names = assigned_variable_names()

    node = target_info["node"]

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Attribute
        ):
            continue

        if not isinstance(
            child.ctx,
            ast.Store
        ):
            continue

        if not contains_target_call(
            child
        ):

            # Check if the value side contains
            # one of the assigned variables.
            relevant = False

            for subnode in ast.walk(
                child
            ):

                if (
                    isinstance(
                        subnode,
                        ast.Name
                    )
                    and subnode.id in names
                ):

                    relevant = True
                    break

            if not relevant:
                continue

        observation = {
            "line": child.lineno,
            "attribute": node_description(child),
            "source":
                source_segment(
                    TARGET_FILE,
                    child
                ),
        }

        attribute_observations.append(
            observation
        )

    print(
        f"ATTRIBUTE OBSERVATIONS : "
        f"{len(attribute_observations)}"
    )

    for event in attribute_observations:

        print(
            f"LINE={event['line']:<6} "
            f"ATTRIBUTE={event['attribute']}"
        )

        print(
            f"  SOURCE: {event['source']}"
        )


# ============================================================
# SUBSCRIPT / DICT / LIST FLOW
# ============================================================

def inspect_subscript_flow(target_info):

    section(
        "STEP 12 — DICT / LIST / SUBSCRIPT FLOW"
    )

    names = assigned_variable_names()

    node = target_info["node"]

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Subscript
        ):
            continue

        relevant = False

        for subnode in ast.walk(
            child
        ):

            if (
                isinstance(
                    subnode,
                    ast.Name
                )
                and subnode.id in names
            ):

                relevant = True
                break

        if not relevant:
            continue

        observation = {
            "line": child.lineno,
            "expression":
                node_description(child),
            "source":
                source_segment(
                    TARGET_FILE,
                    child
                ),
        }

        subscript_observations.append(
            observation
        )

    print(
        f"SUBSCRIPT OBSERVATIONS : "
        f"{len(subscript_observations)}"
    )

    for event in subscript_observations:

        print(
            f"LINE={event['line']:<6} "
            f"EXPRESSION={event['expression']}"
        )

        print(
            f"  SOURCE: {event['source']}"
        )


# ============================================================
# CONTEXTUAL FUNCTION BODY
# ============================================================

def print_target_context(target_info):

    section(
        "STEP 13 — TARGET FUNCTION SOURCE CONTEXT"
    )

    source = source_cache.get(
        TARGET_FILE,
        ""
    )

    lines = source.splitlines()

    start = max(
        0,
        target_info["line"] - 5
    )

    end = min(
        len(lines),
        target_info["node"].end_lineno + 5
        if hasattr(
            target_info["node"],
            "end_lineno"
        )
        else target_info["line"] + 20
    )

    print(
        f"SOURCE LINES {start + 1} "
        f"TO {end}"
    )

    print()

    for index in range(
        start,
        end
    ):

        print(
            f"{index + 1:>6} | "
            f"{lines[index]}"
        )


# ============================================================
# FRONTIER DETERMINATION
# ============================================================

def determine_frontier():

    if not find_future_price_calls:

        return (
            "FIND_FUTURE_PRICE_CALL_NOT_RESOLVED",
            "No find_future_price() call site was resolved.",
            "Resolve the target call site."
        )

    if not assignment_observations:

        return (
            "FIND_FUTURE_PRICE_ASSIGNMENT_NOT_RESOLVED",
            "The real find_future_price() call was found, but no direct downstream assignment was resolved.",
            "Trace the call expression's enclosing statement and return flow."
        )

    if (
        downstream_observations
        or argument_observations
        or return_observations
        or comparison_observations
    ):

        return (
            "FIND_FUTURE_PRICE_DOWNSTREAM_ASSIGNMENT_RESOLVED",
            "The production assignment and downstream uses of the find_future_price() result were statically resolved.",
            "Trace the first real downstream consumer of the assigned future price."
        )

    return (
        "FIND_FUTURE_PRICE_ASSIGNMENT_CAPTURED",
        "A production assignment receiving find_future_price() was identified.",
        "Trace how the assigned value is consumed."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary():

    section(
        "STEP 14 — FINAL FORENSIC SUMMARY"
    )

    status, meaning, next_frontier = (
        determine_frontier()
    )

    print(
        f"TARGET FILE                 : "
        f"{TARGET_FILE}"
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"TARGET CALL                 : "
        f"{TARGET_CALL}()"
    )

    print(
        f"find_future_price CALLS     : "
        f"{len(find_future_price_calls)}"
    )

    print(
        f"ASSIGNMENT OBSERVATIONS     : "
        f"{len(assignment_observations)}"
    )

    print(
        f"DOWNSTREAM VARIABLE USES    : "
        f"{len(downstream_observations)}"
    )

    print(
        f"FUNCTION ARGUMENT USES      : "
        f"{len(argument_observations)}"
    )

    print(
        f"RETURN FLOW OBSERVATIONS    : "
        f"{len(return_observations)}"
    )

    print(
        f"COMPARISON OBSERVATIONS     : "
        f"{len(comparison_observations)}"
    )

    print(
        f"ATTRIBUTE OBSERVATIONS      : "
        f"{len(attribute_observations)}"
    )

    print(
        f"SUBSCRIPT OBSERVATIONS      : "
        f"{len(subscript_observations)}"
    )

    print(
        f"PYTHON FILES SCANNED        : "
        f"{len(python_files)}"
    )

    print(
        f"FILES PARSED                : "
        f"{len(parsed_files)}"
    )

    print(
        f"PARSE ERRORS                : "
        f"{len(parse_errors)}"
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
        "This audit is static only."
    )

    print(
        "IMPORTANT                   : "
        "No production function was executed."
    )

    print(
        "IMPORTANT                   : "
        "No production main() was executed."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                   : "
        "The production database was not opened."
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
# PARSE ERROR REPORT
# ============================================================

def print_parse_errors():

    if not parse_errors:
        return

    section(
        "PARSE ERRORS"
    )

    for event in parse_errors:

        print(
            f"FILE      : "
            f"{event['file']}"
        )

        print(
            f"EXCEPTION : "
            f"{event['exception']}"
        )

        print()


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA FIND FUTURE PRICE "
        "DOWNSTREAM ASSIGNMENT "
        "FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                     : "
        "STATIC READ-ONLY FORENSICS"
    )

    print(
        "TARGET                   : "
        "signal_outcome_engine.py"
        " -> create_outcome()"
    )

    print(
        "TARGET CALL              : "
        "find_future_price()"
    )

    print(
        "PRODUCTION EXECUTION     : NONE"
    )

    print(
        "DATABASE WRITE            : BLOCKED"
    )

    try:

        discover_python_files()

        trees = parse_all_files()

        discover_symbols(
            trees
        )

        target_info = (
            resolve_target_function()
        )

        find_target_calls(
            target_info
        )

        inspect_assignments(
            target_info
        )

        inspect_downstream_uses(
            target_info
        )

        inspect_return_flow(
            target_info
        )

        inspect_comparisons(
            target_info
        )

        inspect_argument_flow(
            target_info
        )

        inspect_attribute_flow(
            target_info
        )

        inspect_subscript_flow(
            target_info
        )

        print_target_context(
            target_info
        )

        final_summary()

        print_parse_errors()

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