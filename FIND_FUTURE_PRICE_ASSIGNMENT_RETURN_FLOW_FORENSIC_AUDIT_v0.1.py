import ast
import os
import sys
import time
import traceback


# ============================================================
# ARUNDA
# FIND_FUTURE_PRICE ASSIGNMENT / RETURN FLOW
# FORENSIC AUDIT v0.2
# ============================================================
#
# MODE:
#   STATIC READ-ONLY FORENSICS
#
# TARGET:
#   signal_outcome_engine.py -> find_future_price()
#
# PURPOSE:
#   Resolve the exact downstream assignment / return flow of
#   the value produced by find_future_price().
#
# SAFETY:
#   - No production execution
#   - No database access
#   - No database writes
#   - No source modification
#   - No formula reproduction
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

TARGET_FUNCTION = "find_future_price"

TARGET_CALLER = "create_outcome"


# ============================================================
# GLOBAL FORENSIC STATE
# ============================================================

parse_errors = []

call_sites = []
assignment_sites = []
return_sites = []
expression_sites = []
caller_functions = []

resolved_flows = []


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


def safe_repr(value, limit=1200):
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
    """
    Read source without executing it.

    utf-8-sig is intentionally used so files containing a UTF-8
    BOM do not create false parse failures.
    """

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as handle:
        return handle.read()


# ============================================================
# SOURCE LOCATION
# ============================================================

def source_segment(
    source_lines,
    node
):
    """
    Safely retrieve source text for an AST node.
    """

    try:
        start = node.lineno - 1

        if hasattr(node, "end_lineno"):
            end = node.end_lineno
        else:
            end = node.lineno

        selected = source_lines[start:end]

        return "".join(selected).strip()

    except Exception:
        return "<SOURCE_UNAVAILABLE>"


# ============================================================
# AST NAME HELPERS
# ============================================================

def get_function_name(node):
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        return node.name

    return None


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)

        if left:
            return (
                left
                + "."
                + node.attr
            )

        return node.attr

    return None


def call_name(node):
    if not isinstance(node, ast.Call):
        return None

    return dotted_name(node.func)


def contains_target_call(
    node,
    target_name
):

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Call
        ):

            name = call_name(child)

            if name == target_name:
                return True

            if (
                name is not None
                and name.endswith(
                    "." + target_name
                )
            ):
                return True

    return False


# ============================================================
# FUNCTION RANGE
# ============================================================

def function_ranges(tree):

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            result.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": getattr(
                        node,
                        "end_lineno",
                        node.lineno
                    ),
                    "node": node,
                }
            )

    return result


def find_enclosing_function(
    tree,
    lineno
):

    candidates = []

    for item in function_ranges(tree):

        if (
            item["lineno"]
            <= lineno
            <= item["end_lineno"]
        ):

            candidates.append(
                item
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item:
        (
            item["end_lineno"]
            - item["lineno"]
        )
    )

    return candidates[0]


# ============================================================
# STEP 1
# ============================================================

def verify_target():

    section(
        "STEP 1 — TARGET RESOLUTION"
    )

    print(
        f"PROJECT DIRECTORY        : "
        f"{PROJECT_DIR}"
    )

    print(
        f"TARGET FILE              : "
        f"{TARGET_FILE}"
    )

    print(
        f"TARGET EXISTS            : "
        f"{os.path.isfile(TARGET_FILE)}"
    )

    print(
        f"TARGET FUNCTION          : "
        f"{TARGET_FUNCTION}"
    )

    if not os.path.isfile(
        TARGET_FILE
    ):
        raise FileNotFoundError(
            TARGET_FILE
        )


# ============================================================
# STEP 2
# ============================================================

def parse_target():

    section(
        "STEP 2 — STATIC SOURCE PARSING"
    )

    source = load_source(
        TARGET_FILE
    )

    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    print(
        "TARGET SOURCE PARSED     : True"
    )

    print(
        f"SOURCE LINES             : "
        f"{len(source.splitlines())}"
    )

    return source, tree


# ============================================================
# STEP 3
# ============================================================

def locate_target_function(
    tree,
    source_lines
):

    section(
        "STEP 3 — find_future_price() RESOLUTION"
    )

    matches = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            if node.name == TARGET_FUNCTION:

                matches.append(
                    node
                )

    print(
        f"FUNCTION DEFINITIONS     : "
        f"{len(matches)}"
    )

    for node in matches:

        print(
            f"FUNCTION                 : "
            f"{node.name}"
        )

        print(
            f"LINE                     : "
            f"{node.lineno}"
        )

        print(
            f"END LINE                 : "
            f"{getattr(node, 'end_lineno', node.lineno)}"
        )

    if not matches:
        raise RuntimeError(
            "find_future_price() not found"
        )

    return matches


# ============================================================
# STEP 4
# ============================================================

def locate_calls(
    tree,
    source_lines
):

    section(
        "STEP 4 — find_future_price() CALL SITE DISCOVERY"
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        name = call_name(node)

        if name is None:
            continue

        if not (
            name == TARGET_FUNCTION
            or name.endswith(
                "." + TARGET_FUNCTION
            )
        ):
            continue

        enclosing = find_enclosing_function(
            tree,
            node.lineno
        )

        caller = (
            enclosing["name"]
            if enclosing
            else "<MODULE>"
        )

        event = {
            "line": node.lineno,
            "column": getattr(
                node,
                "col_offset",
                0
            ),
            "caller": caller,
            "call_name": name,
            "source": source_segment(
                source_lines,
                node
            ),
            "node": node,
        }

        call_sites.append(
            event
        )

        if caller not in caller_functions:
            caller_functions.append(
                caller
            )

        print(
            f"CALLER={caller:<25} "
            f"LINE={node.lineno:<5} "
            f"CALL={name}"
        )

    print()
    print(
        f"STATIC CALL SITES        : "
        f"{len(call_sites)}"
    )

    return call_sites


# ============================================================
# STEP 5
# ============================================================

class FlowVisitor(ast.NodeVisitor):

    def __init__(
        self,
        tree,
        source_lines,
        target_call
    ):

        self.tree = tree
        self.source_lines = source_lines
        self.target_call = target_call

        self.parent_stack = []
        self.current_function = None

    def generic_visit(self, node):

        self.parent_stack.append(
            node
        )

        previous_function = (
            self.current_function
        )

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            self.current_function = node.name

        # ----------------------------------------------------
        # Detect assignments containing target call
        # ----------------------------------------------------

        if isinstance(
            node,
            ast.Assign
        ):

            if contains_target_call(
                node.value,
                TARGET_FUNCTION
            ):

                event = {
                    "type": "Assign",
                    "line": node.lineno,
                    "function":
                        self.current_function
                        or "<MODULE>",
                    "targets": [
                        source_segment(
                            self.source_lines,
                            target
                        )
                        for target
                        in node.targets
                    ],
                    "value":
                        source_segment(
                            self.source_lines,
                            node.value
                        ),
                    "statement":
                        source_segment(
                            self.source_lines,
                            node
                        ),
                    "node": node,
                }

                assignment_sites.append(
                    event
                )

        # ----------------------------------------------------
        # Annotated assignment
        # ----------------------------------------------------

        elif isinstance(
            node,
            ast.AnnAssign
        ):

            if contains_target_call(
                node.value,
                TARGET_FUNCTION
            ):

                event = {
                    "type": "AnnAssign",
                    "line": node.lineno,
                    "function":
                        self.current_function
                        or "<MODULE>",
                    "targets": [
                        source_segment(
                            self.source_lines,
                            node.target
                        )
                    ],
                    "value":
                        source_segment(
                            self.source_lines,
                            node.value
                        ),
                    "statement":
                        source_segment(
                            self.source_lines,
                            node
                        ),
                    "node": node,
                }

                assignment_sites.append(
                    event
                )

        # ----------------------------------------------------
        # Named expression / walrus
        # ----------------------------------------------------

        elif isinstance(
            node,
            ast.NamedExpr
        ):

            if contains_target_call(
                node.value,
                TARGET_FUNCTION
            ):

                event = {
                    "type": "NamedExpr",
                    "line": node.lineno,
                    "function":
                        self.current_function
                        or "<MODULE>",
                    "targets": [
                        source_segment(
                            self.source_lines,
                            node.target
                        )
                    ],
                    "value":
                        source_segment(
                            self.source_lines,
                            node.value
                        ),
                    "statement":
                        source_segment(
                            self.source_lines,
                            node
                        ),
                    "node": node,
                }

                assignment_sites.append(
                    event
                )

        # ----------------------------------------------------
        # Return containing target call
        # ----------------------------------------------------

        elif isinstance(
            node,
            ast.Return
        ):

            if node.value is not None:

                if contains_target_call(
                    node.value,
                    TARGET_FUNCTION
                ):

                    event = {
                        "type": "Return",
                        "line": node.lineno,
                        "function":
                            self.current_function
                            or "<MODULE>",
                        "value":
                            source_segment(
                                self.source_lines,
                                node.value
                            ),
                        "statement":
                            source_segment(
                                self.source_lines,
                                node
                            ),
                        "node": node,
                    }

                    return_sites.append(
                        event
                    )

        # ----------------------------------------------------
        # Expression containing target call
        # ----------------------------------------------------

        elif isinstance(
            node,
            ast.Expr
        ):

            if contains_target_call(
                node.value,
                TARGET_FUNCTION
            ):

                event = {
                    "type": "Expression",
                    "line": node.lineno,
                    "function":
                        self.current_function
                        or "<MODULE>",
                    "value":
                        source_segment(
                            self.source_lines,
                            node.value
                        ),
                    "statement":
                        source_segment(
                            self.source_lines,
                            node
                        ),
                    "node": node,
                }

                expression_sites.append(
                    event
                )

        ast.NodeVisitor.generic_visit(
            self,
            node
        )

        self.parent_stack.pop()

        self.current_function = (
            previous_function
        )


# ============================================================
# STEP 5
# ============================================================

def resolve_direct_flow(
    tree,
    source_lines
):

    section(
        "STEP 5 — DIRECT ASSIGNMENT / RETURN FLOW"
    )

    visitor = FlowVisitor(
        tree,
        source_lines,
        TARGET_FUNCTION
    )

    visitor.visit(
        tree
    )

    print(
        f"DIRECT ASSIGNMENT SITES  : "
        f"{len(assignment_sites)}"
    )

    print(
        f"DIRECT RETURN SITES      : "
        f"{len(return_sites)}"
    )

    print(
        f"DIRECT EXPRESSION SITES  : "
        f"{len(expression_sites)}"
    )

    return visitor


# ============================================================
# STEP 6
# ============================================================

def resolve_call_context(
    tree,
    source_lines
):

    section(
        "STEP 6 — CALL EXPRESSION ENCLOSING STATEMENT"
    )

    for event in call_sites:

        node = event["node"]

        enclosing = find_enclosing_function(
            tree,
            node.lineno
        )

        print()

        print(
            f"CALL LINE                : "
            f"{node.lineno}"
        )

        print(
            f"CALLER FUNCTION          : "
            f"{event['caller']}"
        )

        print(
            "CALL EXPRESSION          : "
            f"{event['source']}"
        )

        if enclosing:

            print(
                f"FUNCTION RANGE           : "
                f"{enclosing['lineno']} - "
                f"{enclosing['end_lineno']}"
            )

        else:

            print(
                "FUNCTION RANGE           : "
                "<MODULE>"
            )

        parent = None

        for candidate in ast.walk(
            tree
        ):

            for child in ast.iter_child_nodes(
                candidate
            ):

                if child is node:

                    parent = candidate
                    break

            if parent is not None:
                break

        if parent is not None:

            print(
                "IMMEDIATE AST PARENT     : "
                f"{type(parent).__name__}"
            )

            print(
                "PARENT SOURCE            : "
                f"{source_segment(source_lines, parent)}"
            )


# ============================================================
# STEP 7
# ============================================================

def print_assignment_flow():

    section(
        "STEP 7 — RESOLVED ASSIGNMENT FLOW"
    )

    if not assignment_sites:

        print(
            "NO DIRECT ASSIGNMENT RESOLVED"
        )

    else:

        for index, event in enumerate(
            assignment_sites,
            start=1
        ):

            print()
            print(
                f"FLOW {index}"
            )

            print(
                f"TYPE                     : "
                f"{event['type']}"
            )

            print(
                f"FUNCTION                 : "
                f"{event['function']}"
            )

            print(
                f"LINE                     : "
                f"{event['line']}"
            )

            print(
                f"TARGET(S)                : "
                f"{safe_repr(event['targets'])}"
            )

            print(
                f"VALUE                    : "
                f"{event['value']}"
            )

            print(
                f"STATEMENT                : "
                f"{event['statement']}"
            )


# ============================================================
# STEP 8
# ============================================================

def print_return_flow():

    section(
        "STEP 8 — RESOLVED RETURN FLOW"
    )

    if not return_sites:

        print(
            "NO DIRECT RETURN CONTAINING "
            "find_future_price() RESOLVED"
        )

    else:

        for index, event in enumerate(
            return_sites,
            start=1
        ):

            print()
            print(
                f"RETURN FLOW {index}"
            )

            print(
                f"FUNCTION                 : "
                f"{event['function']}"
            )

            print(
                f"LINE                     : "
                f"{event['line']}"
            )

            print(
                f"VALUE                    : "
                f"{event['value']}"
            )

            print(
                f"STATEMENT                : "
                f"{event['statement']}"
            )


# ============================================================
# STEP 9
# ============================================================

def resolve_intermediate_variables(
    tree,
    source_lines
):

    section(
        "STEP 9 — INTERMEDIATE VARIABLE FLOW DISCOVERY"
    )

    if not call_sites:

        print(
            "NO TARGET CALLS AVAILABLE"
        )

        return

    interesting_names = set()

    for event in assignment_sites:

        for target in event["targets"]:

            text = target.strip()

            if text.isidentifier():

                interesting_names.add(
                    text
                )

    if not interesting_names:

        print(
            "NO SIMPLE INTERMEDIATE VARIABLE "
            "ASSIGNMENT IDENTIFIED"
        )

        return

    print(
        f"INTERMEDIATE VARIABLES    : "
        f"{len(interesting_names)}"
    )

    for name in sorted(
        interesting_names
    ):

        print()
        print(
            f"VARIABLE : {name}"
        )

        for node in ast.walk(
            tree
        ):

            if isinstance(
                node,
                ast.Name
            ):

                if (
                    node.id == name
                    and isinstance(
                        node.ctx,
                        ast.Load
                    )
                ):

                    enclosing = (
                        find_enclosing_function(
                            tree,
                            node.lineno
                        )
                    )

                    function_name = (
                        enclosing["name"]
                        if enclosing
                        else "<MODULE>"
                    )

                    print(
                        f"  LOAD LINE={node.lineno:<5} "
                        f"FUNCTION={function_name}"
                    )


# ============================================================
# STEP 10
# ============================================================

def determine_status():

    if assignment_sites:

        status = (
            "FIND_FUTURE_PRICE_ASSIGNMENT_FLOW_RESOLVED"
        )

        meaning = (
            "The direct downstream assignment "
            "containing find_future_price() was "
            "resolved statically."
        )

        next_frontier = (
            "Build a READ-ONLY runtime trace for "
            "the resolved assignment path."
        )

        return (
            status,
            meaning,
            next_frontier
        )

    if return_sites:

        status = (
            "FIND_FUTURE_PRICE_RETURN_FLOW_RESOLVED"
        )

        meaning = (
            "The find_future_price() return flow "
            "was resolved statically."
        )

        next_frontier = (
            "Trace the runtime return propagation "
            "through the resolved caller."
        )

        return (
            status,
            meaning,
            next_frontier
        )

    if expression_sites:

        status = (
            "FIND_FUTURE_PRICE_EXPRESSION_FLOW_RESOLVED"
        )

        meaning = (
            "find_future_price() is used as an "
            "expression without a direct assignment "
            "or return statement."
        )

        next_frontier = (
            "Trace the runtime expression consumer."
        )

        return (
            status,
            meaning,
            next_frontier
        )

    if call_sites:

        status = (
            "FIND_FUTURE_PRICE_CALL_CONTEXT_RESOLVED"
        )

        meaning = (
            "The real find_future_price() call was "
            "located, but its downstream assignment "
            "or return flow was not directly resolved."
        )

        next_frontier = (
            "Trace the enclosing statement and "
            "caller return propagation."
        )

        return (
            status,
            meaning,
            next_frontier
        )

    status = (
        "FIND_FUTURE_PRICE_ASSIGNMENT_NOT_FOUND"
    )

    meaning = (
        "No static find_future_price() call was "
        "resolved in the target source."
    )

    next_frontier = (
        "Re-resolve the target call site."
    )

    return (
        status,
        meaning,
        next_frontier
    )


# ============================================================
# STEP 11
# ============================================================

def final_summary():

    status, meaning, next_frontier = (
        determine_status()
    )

    section(
        "STEP 11 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"TARGET FILE                 : "
        f"{TARGET_FILE}"
    )

    print(
        f"STATIC CALL SITES           : "
        f"{len(call_sites)}"
    )

    print(
        f"DIRECT ASSIGNMENT SITES     : "
        f"{len(assignment_sites)}"
    )

    print(
        f"DIRECT RETURN SITES         : "
        f"{len(return_sites)}"
    )

    print(
        f"EXPRESSION SITES            : "
        f"{len(expression_sites)}"
    )

    print(
        f"CALLER FUNCTIONS            : "
        f"{len(caller_functions)}"
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
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA FIND_FUTURE_PRICE "
        "ASSIGNMENT / RETURN FLOW "
        "FORENSIC AUDIT v0.2"
    )

    print(
        "MODE                          : "
        "STATIC READ-ONLY FORENSICS"
    )

    print(
        "TARGET                        : "
        "signal_outcome_engine.py -> "
        "find_future_price()"
    )

    print(
        "PRODUCTION EXECUTION          : "
        "NONE"
    )

    print(
        "DATABASE ACCESS               : "
        "NONE"
    )

    print(
        "DATABASE WRITE                : "
        "BLOCKED"
    )

    try:

        verify_target()

        source, tree = (
            parse_target()
        )

        source_lines = (
            source.splitlines(
                keepends=True
            )
        )

        locate_target_function(
            tree,
            source_lines
        )

        locate_calls(
            tree,
            source_lines
        )

        resolve_direct_flow(
            tree,
            source_lines
        )

        resolve_call_context(
            tree,
            source_lines
        )

        print_assignment_flow()

        print_return_flow()

        resolve_intermediate_variables(
            tree,
            source_lines
        )

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