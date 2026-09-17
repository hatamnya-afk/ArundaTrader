# -*- coding: utf-8 -*-

"""
ARUNDA — RISK_v0.1 ACTUAL DB WRITE BACKWARD CHAIN FORENSIC v2.8

TARGET:
    risk_decisions

METHOD:
    TARGET-ORIENTED BACKWARD DATAFLOW

CHAIN:
    risk_decisions
        ↓
    dynamic SQL / write primitive
        ↓
    SQL expression
        ↓
    SQL builder / helper
        ↓
    returned value
        ↓
    receiving variable
        ↓
    caller
        ↓
    argument
        ↓
    parameter
        ↓
    upstream producer

SAFETY:
    STATIC SOURCE ANALYSIS ONLY.

    NO production imports
    NO production execution
    NO database connection
    NO database reads
    NO database writes
    NO network
    NO orders
    NO trades
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from collections import defaultdict, deque


# =============================================================================
# CONFIG
# =============================================================================

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_TABLE = "risk_decisions"

MAX_BACKWARD_DEPTH = 12
MAX_RETURN_DEPTH = 8
MAX_OUTPUT_ITEMS = 250

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

BACKUP_MARKERS = {
    "backup",
    "*backup",
    "*backups",
    "before*",
    "pre*",
    "old_",
    "copy",
}

FORENSIC_MARKERS = {
    "audit",
    "forensic",
    "diagnostic",
    "diagnostics",
    "repair",
    "reconcile",
    "reconciliation",
    "validation",
    "verify",
    "verification",
    "integrity",
    "trace",
    "probe",
    "inspect",
    "inspection",
    "step",
}

QUARANTINE_MARKERS = {
    "quarantine",
    "broken",
    "corrupt",
    "failed",
    "syntax_failure",
}


# =============================================================================
# SQL PATTERNS
# =============================================================================

WRITE_RE = re.compile(
    r"\b(INSERT|UPDATE|REPLACE|UPSERT)\b",
    re.IGNORECASE,
)

SELECT_RE = re.compile(
    r"\bSELECT\b",
    re.IGNORECASE,
)

DELETE_RE = re.compile(
    r"\bDELETE\b",
    re.IGNORECASE,
)

TARGET_RE = re.compile(
    r"""
    (?:
        \bINTO\s+["'`]?risk_decisions["'`]?
        |
        \bUPDATE\s+["'`]?risk_decisions["'`]?
        |
        \bFROM\s+["'`]?risk_decisions["'`]?
        |
        \bTABLE\s+["'`]?risk_decisions["'`]?
        |
        \bREPLACE\s+(?:INTO\s+)?["'`]?risk_decisions["'`]?
        |
        \bUPSERT\s+(?:INTO\s+)?["'`]?risk_decisions["'`]?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# =============================================================================
# NAME HINTS
# =============================================================================

SQL_HINTS = {
    "sql",
    "query",
    "statement",
    "stmt",
    "command",
    "sql_query",
    "insert_sql",
    "update_sql",
    "replace_sql",
    "upsert_sql",
    "insert_query",
    "update_query",
    "query_sql",
}

PARAM_HINTS = {
    "params",
    "parameters",
    "values",
    "payload",
    "record",
    "row",
    "data",
    "records",
    "rows",
}

RISK_HINTS = {
    "risk",
    "risk_record",
    "risk_result",
    "risk_data",
    "risk_snapshot",
    "risk_decision",
    "risk_decisions",
}


# =============================================================================
# BASIC HELPERS
# =============================================================================

def line_no(node):
    return getattr(node, "lineno", 0)


def end_line(node):
    return getattr(node, "end_lineno", line_no(node))


def clean(text, limit=1000):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def separator(char="=", width=110):
    print(char * width)


def safe_unparse(node):
    if node is None:
        return ""

    try:
        return ast.unparse(node)
    except Exception:
        return ""


# =============================================================================
# FILE CLASSIFICATION
# =============================================================================

def classify_file(path: Path):

    normalized = str(path).lower()
    filename = path.name.lower()

    if any(
        marker in normalized
        for marker in QUARANTINE_MARKERS
    ):
        return "QUARANTINE"

    if (
        "\\backup" in normalized
        or "\\_backups" in normalized
        or any(
            marker in filename
            for marker in BACKUP_MARKERS
        )
    ):
        return "BACKUP"

    if any(
        marker in normalized
        for marker in FORENSIC_MARKERS
    ):
        return "FORENSIC"

    return "PRODUCTION"


# =============================================================================
# SOURCE
# =============================================================================

def discover_python_files():

    if not ROOT.exists():
        return []

    result = []

    for path in ROOT.rglob("*.py"):

        if any(
            part.lower() in SKIP_DIRS
            for part in path.parts
        ):
            continue

        result.append(path)

    return sorted(result)


def read_source(path):

    try:

        raw = path.read_bytes()

        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]

        return raw.decode("utf-8")

    except UnicodeDecodeError:

        try:
            return path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )

        except Exception:
            return None

    except Exception:
        return None


def parse_source(source, path):

    try:

        return ast.parse(
            source,
            filename=str(path),
        )

    except Exception:
        return None


# =============================================================================
# AST HELPERS
# =============================================================================

def dotted_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def literal_string(node):

    if isinstance(node, ast.Constant):

        if isinstance(node.value, str):
            return node.value

    return None


def assignment_targets(node):

    result = []

    if isinstance(node, ast.Name):

        result.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):

        for item in node.elts:
            result.extend(
                assignment_targets(item)
            )

    return result


def node_contains_target(node):

    if node is None:
        return False

    try:

        text = safe_unparse(node)

        if TARGET_TABLE.lower() in text.lower():
            return True

    except Exception:
        pass

    return False


def expression_names(node):

    result = []

    if node is None:
        return result

    class Visitor(ast.NodeVisitor):

        def visit_Name(self, n):
            result.append(n.id)

    Visitor().visit(node)

    return result


# =============================================================================
# STATIC STRING RESOLUTION
# =============================================================================

def resolve_string(
    node,
    env=None,
    visited=None,
    depth=0,
):

    if node is None:
        return ""

    if env is None:
        env = {}

    if visited is None:
        visited = set()

    if depth > 20:
        return "{DEPTH_LIMIT}"

    node_id = id(node)

    if node_id in visited:
        return "{CYCLE}"

    visited.add(node_id)

    try:

        literal = literal_string(node)

        if literal is not None:
            return literal

        if isinstance(node, ast.Name):

            if node.id in env:

                return resolve_string(
                    env[node.id],
                    env,
                    visited,
                    depth + 1,
                )

            return "{" + node.id + "}"

        if isinstance(node, ast.JoinedStr):

            parts = []

            for value in node.values:

                if isinstance(value, ast.Constant):

                    parts.append(
                        str(value.value)
                    )

                elif isinstance(
                    value,
                    ast.FormattedValue,
                ):

                    name = dotted_name(
                        value.value
                    )

                    if name:

                        parts.append(
                            "{" + name + "}"
                        )

                    else:

                        parts.append(
                            "{DYNAMIC}"
                        )

            return "".join(parts)

        if isinstance(node, ast.BinOp):

            if isinstance(node.op, ast.Add):

                left = resolve_string(
                    node.left,
                    env,
                    visited.copy(),
                    depth + 1,
                )

                right = resolve_string(
                    node.right,
                    env,
                    visited.copy(),
                    depth + 1,
                )

                return left + right

        if isinstance(node, ast.Call):

            fn = dotted_name(node.func)

            if fn:

                if fn.endswith(".format"):

                    base = resolve_string(
                        node.func.value,
                        env,
                        visited.copy(),
                        depth + 1,
                    )

                    return base + " {FORMAT}"

                if fn in {
                    "str",
                    "str.strip",
                    "str.upper",
                    "str.lower",
                    "str.replace",
                    "str.join",
                }:

                    if node.args:

                        base = resolve_string(
                            node.args[0],
                            env,
                            visited.copy(),
                            depth + 1,
                        )

                        return (
                            "{CALL:"
                            + fn
                            + "} "
                            + base
                        )

                    return "{CALL:" + fn + "}"

                return "{CALL:" + fn + "}"

        if isinstance(node, ast.Attribute):

            name = dotted_name(node)

            if name:
                return "{" + name + "}"

        if isinstance(node, ast.Subscript):

            base = resolve_string(
                node.value,
                env,
                visited.copy(),
                depth + 1,
            )

            return base + "[DYNAMIC]"

        if isinstance(node, ast.Dict):
            return "{DICT}"

        if isinstance(node, ast.Tuple):
            return "{TUPLE}"

        if isinstance(node, ast.List):
            return "{LIST}"

    finally:

        visited.discard(node_id)

    return ""


# =============================================================================
# SQL CLASSIFICATION
# =============================================================================

def sql_operation(sql):

    if not sql:
        return "UNKNOWN"

    match = WRITE_RE.search(sql)

    if match:
        return match.group(1).upper()

    if SELECT_RE.search(sql):
        return "SELECT"

    if DELETE_RE.search(sql):
        return "DELETE"

    return "UNKNOWN"


def is_write_operation(sql):

    return sql_operation(sql) in {
        "INSERT",
        "UPDATE",
        "REPLACE",
        "UPSERT",
    }


def targets_risk_decisions(sql):

    if not sql:
        return False

    return bool(
        TARGET_RE.search(sql)
    )


def is_db_execution(node):

    if not isinstance(node, ast.Call):
        return False

    method = dotted_name(node.func)

    if not method:
        return False

    return (
        method.endswith(".execute")
        or method.endswith(".executemany")
        or method.endswith(".executescript")
    )


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class FunctionInfo:

    def __init__(
        self,
        analysis,
        node,
    ):

        self.analysis = analysis
        self.node = node
        self.name = node.name

        self.parameters = []
        self.returns = []
        self.assignments = []
        self.calls = []
        self.write_primitives = []

        self.local_env = {}

        self.return_names = set()
        self.sql_names = set()
        self.target_names = set()


class FileAnalysis:

    def __init__(
        self,
        path,
        source,
        tree,
    ):

        self.path = path
        self.source = source
        self.lines = source.splitlines()
        self.tree = tree

        self.category = classify_file(path)

        self.functions = {}
        self.function_calls = []
        self.assignments = []
        self.returns = []
        self.write_primitives = []

        self.target_hits = []


# =============================================================================
# FUNCTION CONTAINMENT
# =============================================================================

def containing_function(
    analysis,
    line,
):

    best = None

    for info in analysis.functions.values():

        start = line_no(info.node)
        end = end_line(info.node)

        if start <= line <= end:

            if best is None:
                best = info

            else:

                current_size = (
                    end_line(best.node)
                    - line_no(best.node)
                )

                candidate_size = (
                    end - start
                )

                if candidate_size < current_size:
                    best = info

    return best


# =============================================================================
# AST ANALYZER
# =============================================================================

class Analyzer(ast.NodeVisitor):

    def __init__(self, analysis):

        self.analysis = analysis
        self.function_stack = []
        self.environment_stack = []

    @property
    def current_function(self):

        if not self.function_stack:
            return None

        return self.function_stack[-1]

    @property
    def current_env(self):

        if not self.environment_stack:
            return {}

        return self.environment_stack[-1]

    def visit_FunctionDef(self, node):

        info = FunctionInfo(
            self.analysis,
            node,
        )

        self.analysis.functions[node.name] = info

        args = []

        args.extend(node.args.posonlyargs)
        args.extend(node.args.args)
        args.extend(node.args.kwonlyargs)

        if node.args.vararg:
            args.append(node.args.vararg)

        if node.args.kwarg:
            args.append(node.args.kwarg)

        info.parameters = [
            arg.arg
            for arg in args
        ]

        self.function_stack.append(info)
        self.environment_stack.append({})

        for statement in node.body:
            self.visit(statement)

        info.local_env = dict(
            self.current_env
        )

        self.environment_stack.pop()
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Assign(self, node):

        targets = []

        for target in node.targets:

            targets.extend(
                assignment_targets(target)
            )

        for variable in targets:

            self.current_env[
                variable
            ] = node.value

            function_name = (
                self.current_function.name
                if self.current_function
                else "<module>"
            )

            resolved = resolve_string(
                node.value,
                self.current_env,
            )

            record = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": function_name,
                "variable": variable,
                "value": clean(resolved),
                "expression": clean(
                    safe_unparse(node.value)
                ),
                "node": node,
            }

            self.analysis.assignments.append(
                record
            )

            if self.current_function:

                self.current_function.assignments.append(
                    record
                )

                lowered = variable.lower()

                if (
                    lowered in SQL_HINTS
                    or "sql" in lowered
                    or "query" in lowered
                    or "statement" in lowered
                ):

                    self.current_function.sql_names.add(
                        variable
                    )

                if (
                    lowered in RISK_HINTS
                    or "risk" in lowered
                ):

                    self.current_function.target_names.add(
                        variable
                    )

        self.generic_visit(node)

    def visit_AnnAssign(self, node):

        if (
            isinstance(
                node.target,
                ast.Name,
            )
            and node.value is not None
        ):

            variable = node.target.id

            self.current_env[
                variable
            ] = node.value

            function_name = (
                self.current_function.name
                if self.current_function
                else "<module>"
            )

            record = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": function_name,
                "variable": variable,
                "value": clean(
                    resolve_string(
                        node.value,
                        self.current_env,
                    )
                ),
                "expression": clean(
                    safe_unparse(node.value)
                ),
                "node": node,
            }

            self.analysis.assignments.append(
                record
            )

            if self.current_function:
                self.current_function.assignments.append(
                    record
                )

        self.generic_visit(node)

    def visit_Call(self, node):

        called = dotted_name(node.func)

        if called:

            caller = (
                self.current_function.name
                if self.current_function
                else "<module>"
            )

            record = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "caller": caller,
                "called": called,
                "node": node,
            }

            self.analysis.function_calls.append(
                record
            )

            if self.current_function:
                self.current_function.calls.append(
                    record
                )

        if is_db_execution(node):

            sql_node = (
                node.args[0]
                if node.args
                else None
            )

            sql = resolve_string(
                sql_node,
                self.current_env,
            )

            primitive = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": (
                    self.current_function.name
                    if self.current_function
                    else "<module>"
                ),
                "method": called,
                "sql": clean(sql),
                "operation": sql_operation(sql),
                "target": targets_risk_decisions(sql),
                "is_write": is_write_operation(sql),
                "node": node,
                "sql_node": sql_node,
                "params_nodes": list(
                    node.args[1:]
                ),
            }

            self.analysis.write_primitives.append(
                primitive
            )

            if self.current_function:
                self.current_function.write_primitives.append(
                    primitive
                )

        self.generic_visit(node)

    def visit_Return(self, node):

        function_name = (
            self.current_function.name
            if self.current_function
            else "<module>"
        )

        value = resolve_string(
            node.value,
            self.current_env,
        )

        record = {
            "path": self.analysis.path,
            "category": self.analysis.category,
            "line": line_no(node),
            "function": function_name,
            "value": clean(value),
            "expression": clean(
                safe_unparse(node.value)
            ),
            "node": node,
        }

        self.analysis.returns.append(
            record
        )

        if self.current_function:

            self.current_function.returns.append(
                record
            )

            for name in expression_names(
                node.value
            ):

                self.current_function.return_names.add(
                    name
                )

        self.generic_visit(node)


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_file(path):

    source = read_source(path)

    if source is None:
        return None, "READ_FAILURE"

    tree = parse_source(
        source,
        path,
    )

    if tree is None:
        return None, "AST_FAILURE"

    analysis = FileAnalysis(
        path,
        source,
        tree,
    )

    Analyzer(analysis).visit(tree)

    for index, text in enumerate(
        analysis.lines,
        1,
    ):

        if TARGET_TABLE.lower() in text.lower():

            analysis.target_hits.append(
                {
                    "path": path,
                    "category": analysis.category,
                    "line": index,
                    "text": clean(text),
                }
            )

    return analysis, None


def build_repository_index(files):

    analyses = []
    failures = []

    for path in files:

        analysis, error = analyze_file(
            path
        )

        if analysis is not None:

            analyses.append(
                analysis
            )

        else:

            failures.append(
                {
                    "path": path,
                    "error": error,
                }
            )

    return analyses, failures


# =============================================================================
# FUNCTION INDEX
# =============================================================================

def build_function_index(analyses):

    index = defaultdict(list)

    for analysis in analyses:

        for name, info in analysis.functions.items():

            index[name].append(
                {
                    "analysis": analysis,
                    "function": info,
                }
            )

    return index


# =============================================================================
# CALL INDEX
# =============================================================================

def build_call_index(analyses):

    calls_by_callee = defaultdict(list)

    function_names = set()

    for analysis in analyses:

        function_names.update(
            analysis.functions.keys()
        )

    for analysis in analyses:

        for call in analysis.function_calls:

            short = (
                call["called"]
                .split(".")[-1]
            )

            if short not in function_names:
                continue

            caller = containing_function(
                analysis,
                call["line"],
            )

            caller_name = (
                caller.name
                if caller
                else "<module>"
            )

            calls_by_callee[
                short
            ].append(
                {
                    "path": analysis.path,
                    "category": analysis.category,
                    "line": call["line"],
                    "caller": caller_name,
                    "called": call["called"],
                    "node": call["node"],
                }
            )

    return calls_by_callee


# =============================================================================
# CALL ARGUMENT BINDING
# =============================================================================

def bind_call_arguments(
    function_info,
    call_node,
):

    bindings = {}

    params = list(
        function_info.parameters
    )

    for index, argument in enumerate(
        call_node.args
    ):

        if index >= len(params):
            break

        bindings[
            params[index]
        ] = argument

    for keyword in call_node.keywords:

        if keyword.arg is None:
            continue

        bindings[
            keyword.arg
        ] = keyword.value

    return bindings


# =============================================================================
# TARGET SIGNAL SCORING
# =============================================================================

def score_target_expression(
    expression,
):

    if expression is None:
        return 0

    text = clean(
        safe_unparse(expression)
    ).lower()

    score = 0

    if TARGET_TABLE.lower() in text:
        score += 100

    if "insert" in text:
        score += 30

    if "update" in text:
        score += 25

    if "replace" in text:
        score += 25

    if "upsert" in text:
        score += 25

    if "sql" in text:
        score += 10

    if "query" in text:
        score += 10

    if "risk" in text:
        score += 10

    if "param" in text:
        score += 5

    return score


# =============================================================================
# TARGET WRITE CANDIDATES
# =============================================================================

def collect_target_writes(
    analyses,
):

    records = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            if not primitive["is_write"]:
                continue

            if primitive["target"]:

                records.append(
                    primitive
                )

    return records


def collect_dynamic_writes(
    analyses,
):

    records = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            if not primitive["is_write"]:
                continue

            if primitive["target"]:
                continue

            sql = primitive["sql"]

            dynamic = (
                "{"
                in sql
                or "{CALL:"
                in sql
                or "{DYNAMIC}"
                in sql
                or "{CYCLE}"
                in sql
                or "{DEPTH_LIMIT}"
                in sql
            )

            if dynamic:

                records.append(
                    primitive
                )

    return records


# =============================================================================
# TARGET TOKEN SEARCH
# =============================================================================

def collect_target_tokens(
    analyses,
):

    result = []

    for analysis in analyses:

        result.extend(
            analysis.target_hits
        )

    return result


# =============================================================================
# TARGET-RELEVANT FUNCTIONS
# =============================================================================

def collect_target_relevant_functions(
    analyses,
):

    result = []

    for analysis in analyses:

        for info in analysis.functions.values():

            score = 0
            reasons = []

            for assignment in info.assignments:

                expression = assignment[
                    "node"
                ].value

                local_score = score_target_expression(
                    expression
                )

                if local_score:

                    score += local_score

                    reasons.append(
                        f"assignment:{assignment['variable']}"
                    )

            for ret in info.returns:

                local_score = score_target_expression(
                    ret["node"].value
                )

                if local_score:

                    score += local_score

                    reasons.append(
                        f"return:{ret['line']}"
                    )

            for primitive in info.write_primitives:

                if primitive["target"]:

                    score += 100

                    reasons.append(
                        "direct_target_write"
                    )

                elif primitive["is_write"]:

                    score += 20

                    reasons.append(
                        "dynamic_write"
                    )

            if score > 0:

                result.append(
                    {
                        "analysis": analysis,
                        "function": info,
                        "score": score,
                        "reasons": reasons,
                    }
                )

    result.sort(
        key=lambda item: (
            -item["score"],
            str(item["analysis"].path),
            item["function"].name,
        )
    )

    return result


# =============================================================================
# BACKWARD CALL GRAPH
# =============================================================================

def backward_function_chain(
    start_function,
    calls_by_callee,
    max_depth=MAX_BACKWARD_DEPTH,
):

    """
    Iterative BFS.

    v2.8:
        No recursive caller traversal.

    State:
        (function_name, path, depth)
    """

    queue = deque()

    queue.append(
        (
            start_function,
            None,
            0,
        )
    )

    visited = set()
    results = []

    while queue:

        function_name, current_path, depth = (
            queue.popleft()
        )

        if depth >= max_depth:
            continue

        direct = calls_by_callee.get(
            function_name,
            [],
        )

        for caller in direct:

            caller_name = caller[
                "caller"
            ]

            state = (
                function_name,
                str(caller["path"]),
                caller["line"],
                caller_name,
            )

            if state in visited:
                continue

            visited.add(state)

            item = {
                "depth": depth + 1,
                "callee": function_name,
                "caller": caller_name,
                "path": caller["path"],
                "category": caller["category"],
                "line": caller["line"],
            }

            results.append(
                item
            )

            if (
                caller_name
                != "<module>"
            ):

                queue.append(
                    (
                        caller_name,
                        caller["path"],
                        depth + 1,
                    )
                )

    return results


# =============================================================================
# RETURN → CALLER ASSIGNMENT DETECTION
# =============================================================================

def assignment_receives_call(
    assignment_record,
):

    node = assignment_record[
        "node"
    ]

    if not isinstance(
        node,
        ast.Assign,
    ):
        return False

    return isinstance(
        node.value,
        ast.Call,
    )


def collect_return_assignment_flows(
    analyses,
    function_index,
):

    result = []

    for analysis in analyses:

        for assignment in analysis.assignments:

            if not assignment_receives_call(
                assignment
            ):
                continue

            node = assignment[
                "node"
            ]

            called = dotted_name(
                node.value.func
            )

            if not called:
                continue

            short = called.split(".")[-1]

            candidates = function_index.get(
                short,
                [],
            )

            for candidate in candidates:

                info = candidate[
                    "function"
                ]

                if not info.returns:
                    continue

                result.append(
                    {
                        "path": analysis.path,
                        "category": analysis.category,
                        "line": assignment["line"],
                        "caller": assignment["function"],
                        "variable": assignment["variable"],
                        "callee": info.name,
                        "callee_path": info.analysis.path,
                        "return_count": len(
                            info.returns
                        ),
                    }
                )

    return result


# =============================================================================
# TARGET FUNCTION PARAMETER FLOWS
# =============================================================================

def collect_target_parameter_flows(
    target_functions,
    calls_by_callee,
    function_index,
):

    result = []

    seen = set()

    for target in target_functions:

        info = target[
            "function"
        ]

        function_name = info.name

        calls = calls_by_callee.get(
            function_name,
            [],
        )

        for call in calls:

            key = (
                function_name,
                str(call["path"]),
                call["line"],
                call["caller"],
            )

            if key in seen:
                continue

            seen.add(key)

            matching = function_index.get(
                function_name,
                [],
            )

            for candidate in matching:

                candidate_info = candidate[
                    "function"
                ]

                bindings = bind_call_arguments(
                    candidate_info,
                    call["node"],
                )

                for parameter, argument in bindings.items():

                    result.append(
                        {
                            "callee": function_name,
                            "callee_path": candidate_info.analysis.path,
                            "caller": call["caller"],
                            "caller_path": call["path"],
                            "line": call["line"],
                            "parameter": parameter,
                            "argument": clean(
                                safe_unparse(argument)
                            ),
                            "argument_name": (
                                dotted_name(argument)
                                if isinstance(
                                    argument,
                                    (
                                        ast.Name,
                                        ast.Attribute,
                                    ),
                                )
                                else None
                            ),
                        }
                    )

    return result


# =============================================================================
# TARGET-RELEVANT ASSIGNMENTS
# =============================================================================

def collect_target_assignments(
    target_functions,
):

    result = []

    for target in target_functions:

        info = target[
            "function"
        ]

        for assignment in info.assignments:

            text = clean(
                safe_unparse(
                    assignment["node"].value
                )
            ).lower()

            relevant = (
                TARGET_TABLE.lower()
                in text
                or "sql" in text
                or "query" in text
                or "risk" in text
                or "param" in text
                or assignment["variable"].lower()
                in SQL_HINTS
                or assignment["variable"].lower()
                in RISK_HINTS
            )

            if relevant:

                result.append(
                    assignment
                )

    return result


# =============================================================================
# REPORT HELPERS
# =============================================================================

def print_inventory(
    files,
    analyses,
    failures,
):

    separator()

    print(
        "1) REPOSITORY INVENTORY"
    )

    separator()

    counts = defaultdict(int)

    for path in files:

        counts[
            classify_file(path)
        ] += 1

    print(
        f"PYTHON FILES       : {len(files)}"
    )

    print(
        f"ANALYZED FILES     : {len(analyses)}"
    )

    print(
        f"AST/READ FAILURES  : {len(failures)}"
    )

    print(
        f"PRODUCTION FILES   : {counts['PRODUCTION']}"
    )

    print(
        f"FORENSIC FILES     : {counts['FORENSIC']}"
    )

    print(
        f"BACKUP FILES       : {counts['BACKUP']}"
    )

    print(
        f"QUARANTINE FILES   : {counts['QUARANTINE']}"
    )


def print_dynamic_writes(
    dynamic,
):

    separator()

    print(
        "2) DYNAMIC WRITE CANDIDATES"
    )

    separator()

    print(
        f"DYNAMIC WRITE SIGNALS : {len(dynamic)}"
    )

    for index, item in enumerate(
        dynamic[:MAX_OUTPUT_ITEMS],
        1,
    ):

        print()

        print(
            f"DYNAMIC #{index}"
        )

        print(
            f"FILE      : {item['path']}"
        )

        print(
            f"CATEGORY  : {item['category']}"
        )

        print(
            f"LINE      : {item['line']}"
        )

        print(
            f"FUNCTION  : {item['function']}"
        )

        print(
            f"METHOD    : {item['method']}"
        )

        print(
            f"OPERATION : {item['operation']}"
        )

        print(
            f"SQL       : {item['sql']}"
        )


def print_relevant_functions(
    functions,
):

    separator()

    print(
        "3) TARGET-RELEVANT FUNCTIONS"
    )

    separator()

    print(
        f"FUNCTIONS : {len(functions)}"
    )

    for index, item in enumerate(
        functions[:MAX_OUTPUT_ITEMS],
        1,
    ):

        info = item[
            "function"
        ]

        print()

        print(
            f"FUNCTION #{index}"
        )

        print(
            f"FILE      : {item['analysis'].path}"
        )

        print(
            f"CATEGORY  : {item['analysis'].category}"
        )

        print(
            f"LINE      : {line_no(info.node)}"
        )

        print(
            f"FUNCTION  : {info.name}"
        )

        print(
            f"SCORE     : {item['score']}"
        )

        print(
            "REASONS    : "
            + ", ".join(
                item["reasons"][:20]
            )
        )


def print_target_assignments(
    assignments,
):

    separator()

    print(
        "4) TARGET-RELEVANT LOCAL ASSIGNMENTS"
    )

    separator()

    print(
        f"ASSIGNMENTS : {len(assignments)}"
    )

    for index, item in enumerate(
        assignments[:MAX_OUTPUT_ITEMS],
        1,
    ):

        print()

        print(
            f"ASSIGNMENT #{index}"
        )

        print(
            f"FILE      : {item['path']}"
        )

        print(
            f"LINE      : {item['line']}"
        )

        print(
            f"FUNCTION  : {item['function']}"
        )

        print(
            f"VARIABLE  : {item['variable']}"
        )

        print(
            f"VALUE     : {item['value']}"
        )

        print(
            f"EXPRESSION: {item['expression']}"
        )


def print_parameter_flows(
    flows,
):

    separator()

    print(
        "5) TARGET-ORIENTED ARGUMENT → PARAMETER"
    )

    separator()

    print(
        f"FLOWS : {len(flows)}"
    )

    for index, item in enumerate(
        flows[:MAX_OUTPUT_ITEMS],
        1,
    ):

        print()

        print(
            f"FLOW #{index}"
        )

        print(
            f"CALLEE       : {item['callee']}"
        )

        print(
            f"CALLEE PATH  : {item['callee_path']}"
        )

        print(
            f"CALLER       : {item['caller']}"
        )

        print(
            f"CALLER PATH  : {item['caller_path']}"
        )

        print(
            f"CALL LINE    : {item['line']}"
        )

        print(
            f"PARAMETER    : {item['parameter']}"
        )

        print(
            f"ARGUMENT     : {item['argument']}"
        )

        print(
            f"ARGUMENT NAME: {item['argument_name']}"
        )


def print_backward_chains(
    relevant_functions,
    calls_by_callee,
):

    separator()

    print(
        "6) TARGET-ORIENTED BACKWARD CALL CHAINS"
    )

    separator()

    total = 0

    for index, item in enumerate(
        relevant_functions[:MAX_OUTPUT_ITEMS],
        1,
    ):

        info = item[
            "function"
        ]

        chain = backward_function_chain(
            info.name,
            calls_by_callee,
        )

        if not chain:
            continue

        print()

        print(
            f"CHAIN #{index}"
        )

        print(
            f"START FUNCTION : {info.name}"
        )

        print(
            f"START FILE     : {item['analysis'].path}"
        )

        print(
            f"SCORE          : {item['score']}"
        )

        for hop in chain[:MAX_OUTPUT_ITEMS]:

            total += 1

            print(
                f"  DEPTH {hop['depth']} :: "
                f"{hop['callee']} "
                f"<- "
                f"{hop['caller']} "
                f":: "
                f"{hop['path']} "
                f"LINE {hop['line']}"
            )

    print()

    print(
        f"TOTAL BACKWARD HOPS : {total}"
    )


def print_target_tokens(
    tokens,
):

    separator()

    print(
        "7) risk_decisions TOKEN LOCATIONS"
    )

    separator()

    print(
        f"TOKEN HITS : {len(tokens)}"
    )

    for item in tokens[:MAX_OUTPUT_ITEMS]:

        print()

        print(
            f"{item['category']} :: "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )

        print(
            f"TEXT : {item['text']}"
        )


def print_execution_summary(
    analyses,
):

    separator()

    print(
        "8) DB EXECUTION PRIMITIVE SUMMARY"
    )

    separator()

    total = 0
    writes = 0
    selects = 0
    unknown = 0

    for analysis in analyses:

        for item in analysis.write_primitives:

            total += 1

            operation = item[
                "operation"
            ]

            if operation in {
                "INSERT",
                "UPDATE",
                "REPLACE",
                "UPSERT",
            }:

                writes += 1

            elif operation == "SELECT":

                selects += 1

            else:

                unknown += 1

    print(
        f"DB EXECUTION PRIMITIVES : {total}"
    )

    print(
        f"WRITE PRIMITIVES         : {writes}"
    )

    print(
        f"SELECT PRIMITIVES        : {selects}"
    )

    print(
        f"UNKNOWN / DYNAMIC        : {unknown}"
    )


# =============================================================================
# FINAL STATUS
# =============================================================================

def print_final_status(
    analyses,
    dynamic_writes,
    relevant_functions,
    parameter_flows,
    return_flows,
    target_assignments,
    target_tokens,
):

    separator()

    print(
        "9) FINAL PRODUCER STATUS"
    )

    separator()

    direct = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            if (
                primitive["is_write"]
                and primitive["target"]
            ):

                direct.append(
                    primitive
                )

    production_direct = [
        item
        for item in direct
        if item["category"]
        == "PRODUCTION"
    ]

    target_relevant_production = [
        item
        for item in relevant_functions
        if item["analysis"].category
        == "PRODUCTION"
    ]

    print(
        f"DIRECT risk_decisions WRITES : {len(direct)}"
    )

    print(
        f"PRODUCTION DIRECT             : {len(production_direct)}"
    )

    print(
        f"DYNAMIC WRITE SIGNALS         : {len(dynamic_writes)}"
    )

    print(
        f"TARGET-RELEVANT FUNCTIONS     : {len(relevant_functions)}"
    )

    print(
        f"TARGET-RELEVANT PRODUCTION    : "
        f"{len(target_relevant_production)}"
    )

    print(
        f"TARGET PARAMETER FLOWS        : {len(parameter_flows)}"
    )

    print(
        f"RETURN→ASSIGNMENT FLOWS       : {len(return_flows)}"
    )

    print(
        f"TARGET LOCAL ASSIGNMENTS      : {len(target_assignments)}"
    )

    print(
        f"risk_decisions TOKEN HITS     : {len(target_tokens)}"
    )

    print()

    if production_direct:

        print(
            "RESULT : PRODUCTION DIRECT "
            "risk_decisions WRITE FOUND"
        )

        print(
            "PRODUCER STATUS : RESOLVED"
        )

        print(
            "NEXT TARGET : verify payload semantics."
        )

        return

    if (
        dynamic_writes
        and relevant_functions
    ):

        print(
            "RESULT : DYNAMIC WRITE + "
            "TARGET-RELEVANT FUNCTION PATH FOUND"
        )

        print(
            "PRODUCER STATUS : PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : "
            "resolve dynamic SQL builder arguments "
            "for the ranked target functions."
        )

        return

    if (
        parameter_flows
        and relevant_functions
    ):

        print(
            "RESULT : TARGET-ORIENTED "
            "PARAMETER DATAFLOW FOUND"
        )

        print(
            "PRODUCER STATUS : PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : "
            "resolve argument expression provenance."
        )

        return

    if target_assignments:

        print(
            "RESULT : TARGET-RELEVANT LOCAL "
            "PRODUCERS FOUND"
        )

        print(
            "PRODUCER STATUS : PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : "
            "connect local producers to DB execution."
        )

        return

    print(
        "RESULT : TARGET PRODUCER NOT YET RESOLVED"
    )

    print(
        "PRODUCER STATUS : NOT YET RESOLVED"
    )

    print(
        "NEXT TARGET : inspect the highest-confidence "
        "dynamic write candidates."
    )


# =============================================================================
# SAFETY
# =============================================================================

def print_safety():

    separator()

    print(
        "SAFETY"
    )

    separator()

    print(
        "STATIC SOURCE ANALYSIS ONLY"
    )

    print(
        "NO PRODUCTION MODULE IMPORT"
    )

    print(
        "NO PRODUCTION FUNCTION EXECUTION"
    )

    print(
        "NO DATABASE CONNECTION"
    )

    print(
        "NO DATABASE READ"
    )

    print(
        "NO SELECT EXECUTION"
    )

    print(
        "NO INSERT"
    )

    print(
        "NO UPDATE"
    )

    print(
        "NO DELETE"
    )

    print(
        "NO ALTER"
    )

    print(
        "NO CREATE"
    )

    print(
        "NO COMMIT"
    )

    print(
        "NO NETWORK"
    )

    print(
        "NO ORDER"
    )

    print(
        "NO TRADE"
    )

    separator()


# =============================================================================
# MAIN
# =============================================================================

def main():

    separator()

    print(
        "ARUNDA — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.8"
    )

    separator()

    print(
        "MODE        : READ ONLY"
    )

    print(
        f"ROOT        : {ROOT}"
    )

    print(
        f"TARGET      : {TARGET_TABLE}"
    )

    print(
        "METHOD      : TARGET-ORIENTED "
        "BACKWARD DATAFLOW"
    )

    print(
        "CHAIN       : "
        "WRITE → SQL → BUILDER → RETURN → "
        "CALLER → ARGUMENT → PARAMETER"
    )

    print()

    print(
        "IMPORTANT   : SELECT IS NOT A PRODUCER"
    )

    print(
        "IMPORTANT   : NO PRODUCTION EXECUTION"
    )

    print()

    if not ROOT.exists():

        print(
            f"ERROR: ROOT DOES NOT EXIST: {ROOT}"
        )

        return

    files = discover_python_files()

    analyses, failures = (
        build_repository_index(
            files
        )
    )

    function_index = (
        build_function_index(
            analyses
        )
    )

    calls_by_callee = (
        build_call_index(
            analyses
        )
    )

    dynamic_writes = (
        collect_dynamic_writes(
            analyses
        )
    )

    relevant_functions = (
        collect_target_relevant_functions(
            analyses
        )
    )

    parameter_flows = (
        collect_target_parameter_flows(
            relevant_functions,
            calls_by_callee,
            function_index,
        )
    )

    return_flows = (
        collect_return_assignment_flows(
            analyses,
            function_index,
        )
    )

    target_assignments = (
        collect_target_assignments(
            relevant_functions
        )
    )

    target_tokens = (
        collect_target_tokens(
            analyses
        )
    )

    print_inventory(
        files,
        analyses,
        failures,
    )

    print_dynamic_writes(
        dynamic_writes
    )

    print_relevant_functions(
        relevant_functions
    )

    print_target_assignments(
        target_assignments
    )

    print_parameter_flows(
        parameter_flows
    )

    print_backward_chains(
        relevant_functions,
        calls_by_callee,
    )

    print_target_tokens(
        target_tokens
    )

    print_execution_summary(
        analyses
    )

    print_final_status(
        analyses,
        dynamic_writes,
        relevant_functions,
        parameter_flows,
        return_flows,
        target_assignments,
        target_tokens,
    )

    print_safety()

    separator()

    print(
        "END — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.8"
    )

    separator()


if __name__ == "__main__":
    main()