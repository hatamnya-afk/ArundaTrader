# -*- coding: utf-8 -*-

"""
ARUNDA — RISK_v0.1 ACTUAL DB WRITE BACKWARD CHAIN FORENSIC v2.7

OBJECTIVE
---------
Continue from v2.6.

v2.6 established:

    SQL BUILDER / CALL-RETURN PATHS EXIST
    TARGET NOT YET RESOLVED

v2.7 hardens the backward dataflow analysis:

    DB WRITE
        ↓
    SQL
        ↓
    SQL BUILDER
        ↓
    RETURN
        ↓
    CALLER
        ↓
    ARGUMENT
        ↓
    PARAMETER
        ↓
    LOCAL VARIABLE

IMPORTANT
---------
STATIC FORENSIC ANALYSIS ONLY.

NO:
    production imports
    production execution
    database connection
    database reads
    database writes
    network
    orders
    trades

This analyzer never executes production code.

v2.7 HARDENING
--------------
1. Cycle-safe caller traversal.
2. Caller identity uses:
       absolute path + function + definition line
3. <module> is a terminal node.
4. Maximum caller depth.
5. Maximum total traversal nodes.
6. No recursive path explosion.
7. Same function name in different files is NOT treated as
   the same function.
8. Parameter binding supports positional and keyword arguments.
9. *args / **kwargs are conservatively represented.
10. Return -> assignment propagation is explicit.
11. SQL builder candidates are target-oriented.
12. Dynamic SQL remains UNKNOWN instead of being invented.
13. SELECT is never treated as a producer.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from collections import defaultdict


# =============================================================================
# CONFIG
# =============================================================================

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_TABLE = "risk_decisions"

MAX_RESOLVE_DEPTH = 30
MAX_CALL_DEPTH = 15
MAX_TRACE_NODES = 5000

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
    "_backup",
    "_backups",
    "before_",
    "pre_",
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
# SQL REGEX
# =============================================================================

WRITE_RE = re.compile(
    r"""
    \b(
        INSERT
        |
        UPDATE
        |
        REPLACE
        |
        UPSERT
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
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
# IDENTIFIER HINTS
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
    return getattr(
        node,
        "end_lineno",
        line_no(node),
    )


def clean(text, limit=1600):

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
        if hasattr(ast, "unparse"):
            return ast.unparse(node)
    except Exception:
        pass

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

    result = []

    if not ROOT.exists():
        return result

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

    if node is None:
        return None

    if isinstance(node, ast.Constant):

        if isinstance(node.value, str):
            return node.value

    return None


def literal_value(node):

    if node is None:
        return None

    if isinstance(node, ast.Constant):
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


def expression_names(node):

    result = []

    if node is None:
        return result

    class NameVisitor(ast.NodeVisitor):

        def visit_Name(self, name_node):

            result.append(
                name_node.id
            )

    NameVisitor().visit(node)

    return result


# =============================================================================
# SAFE STRING RESOLUTION
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

    if depth > MAX_RESOLVE_DEPTH:
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

                    return (
                        "{CALL:"
                        + fn
                        + "}"
                    )

                return (
                    "{CALL:"
                    + fn
                    + "}"
                )

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

        token = match.group(1).upper()

        if token == "INSERT":
            return "INSERT"

        if token == "UPDATE":
            return "UPDATE"

        if token == "REPLACE":
            return "REPLACE"

        if token == "UPSERT":
            return "UPSERT"

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

    method = dotted_name(
        node.func
    )

    if not method:
        return False

    return (
        method.endswith(".execute")
        or method.endswith(".executemany")
        or method.endswith(".executescript")
    )


# =============================================================================
# FUNCTION IDENTITY
# =============================================================================

def function_identity(
    analysis,
    function_info,
):
    """
    Critical v2.7 rule:

    Function identity is NOT merely function name.

    It is:

        absolute file path
        +
        function name
        +
        definition line
    """

    return (
        str(
            analysis.path.resolve()
        ).lower(),
        function_info.name,
        line_no(function_info.node),
    )


def caller_identity(record):

    return (
        str(
            Path(record["path"]).resolve()
        ).lower(),
        record["caller"],
        record["caller_line"],
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

        self.posonly_parameters = []

        self.kwonly_parameters = []

        self.vararg = None
        self.kwarg = None

        self.calls = []
        self.returns = []

        self.assignments = []

        self.write_primitives = []

        self.local_env = {}


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

        self.category = classify_file(
            path
        )

        self.functions = {}

        self.function_calls = []

        self.write_primitives = []

        self.sql_assignments = []

        self.assignments = []

        self.returns = []

        self.dynamic_sql_candidates = []


# =============================================================================
# FUNCTION RANGE
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

    # -------------------------------------------------------------------------
    # FUNCTIONS
    # -------------------------------------------------------------------------

    def visit_FunctionDef(self, node):

        info = FunctionInfo(
            self.analysis,
            node,
        )

        self.analysis.functions[
            node.name
        ] = info

        for arg in node.args.posonlyargs:

            info.parameters.append(
                arg.arg
            )

            info.posonly_parameters.append(
                arg.arg
            )

        for arg in node.args.args:

            info.parameters.append(
                arg.arg
            )

        for arg in node.args.kwonlyargs:

            info.parameters.append(
                arg.arg
            )

            info.kwonly_parameters.append(
                arg.arg
            )

        if node.args.vararg:

            info.vararg = (
                node.args.vararg.arg
            )

        if node.args.kwarg:

            info.kwarg = (
                node.args.kwarg.arg
            )

        self.function_stack.append(
            info
        )

        self.environment_stack.append(
            {}
        )

        for default in node.args.defaults:

            self.visit(default)

        for default in node.args.kw_defaults:

            if default is not None:
                self.visit(default)

        for statement in node.body:
            self.visit(statement)

        info.local_env = dict(
            self.current_env
        )

        self.environment_stack.pop()
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):

        self.visit_FunctionDef(node)

    # -------------------------------------------------------------------------
    # ASSIGNMENT
    # -------------------------------------------------------------------------

    def visit_Assign(self, node):

        targets = []

        for target in node.targets:

            targets.extend(
                assignment_targets(
                    target
                )
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
                    safe_unparse(
                        node.value
                    )
                ),
                "node": node,
            }

            if self.current_function:

                record["function_line"] = (
                    line_no(
                        self.current_function.node
                    )
                )

            else:

                record["function_line"] = 0

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

                self.analysis.sql_assignments.append(
                    {
                        "path": self.analysis.path,
                        "category": self.analysis.category,
                        "line": line_no(node),
                        "function": function_name,
                        "variable": variable,
                        "sql": clean(resolved),
                        "operation": sql_operation(
                            resolved
                        ),
                        "target": targets_risk_decisions(
                            resolved
                        ),
                        "node": node,
                    }
                )

            if (
                lowered in PARAM_HINTS
                or lowered in RISK_HINTS
                or "risk" in lowered
                or "param" in lowered
                or "payload" in lowered
            ):

                self.analysis.dynamic_sql_candidates.append(
                    {
                        "path": self.analysis.path,
                        "category": self.analysis.category,
                        "line": line_no(node),
                        "function": function_name,
                        "variable": variable,
                        "value": clean(resolved),
                        "expression": clean(
                            safe_unparse(
                                node.value
                            )
                        ),
                    }
                )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # ANNOTATED ASSIGNMENT
    # -------------------------------------------------------------------------

    def visit_AnnAssign(self, node):

        if isinstance(
            node.target,
            ast.Name,
        ):

            variable = node.target.id

            if node.value is not None:

                self.current_env[
                    variable
                ] = node.value

                function_name = (
                    self.current_function.name
                    if self.current_function
                    else "<module>"
                )

                self.analysis.assignments.append(
                    {
                        "path": self.analysis.path,
                        "category": self.analysis.category,
                        "line": line_no(node),
                        "function": function_name,
                        "function_line": (
                            line_no(
                                self.current_function.node
                            )
                            if self.current_function
                            else 0
                        ),
                        "variable": variable,
                        "value": clean(
                            resolve_string(
                                node.value,
                                self.current_env,
                            )
                        ),
                        "expression": clean(
                            safe_unparse(
                                node.value
                            )
                        ),
                        "node": node,
                    }
                )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    def visit_Call(self, node):

        called = dotted_name(
            node.func
        )

        if called:

            caller = (
                self.current_function.name
                if self.current_function
                else "<module>"
            )

            caller_line = (
                line_no(
                    self.current_function.node
                )
                if self.current_function
                else 0
            )

            record = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "caller": caller,
                "caller_line": caller_line,
                "called": called,
                "node": node,
                "args": list(node.args),
                "keywords": list(node.keywords),
            }

            self.analysis.function_calls.append(
                record
            )

            if self.current_function:

                self.current_function.calls.append(
                    record
                )

        # ---------------------------------------------------------------------
        # DB EXECUTION
        # ---------------------------------------------------------------------

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

            operation = sql_operation(
                sql
            )

            item = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": (
                    self.current_function.name
                    if self.current_function
                    else "<module>"
                ),
                "function_line": (
                    line_no(
                        self.current_function.node
                    )
                    if self.current_function
                    else 0
                ),
                "method": called,
                "sql": clean(sql),
                "operation": operation,
                "target": targets_risk_decisions(
                    sql
                ),
                "is_write": is_write_operation(
                    sql
                ),
                "node": node,
                "sql_node": sql_node,
                "params_nodes": list(
                    node.args[1:]
                ),
            }

            self.analysis.write_primitives.append(
                item
            )

            if self.current_function:

                self.current_function.write_primitives.append(
                    item
                )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # RETURN
    # -------------------------------------------------------------------------

    def visit_Return(self, node):

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
            "function_line": (
                line_no(
                    self.current_function.node
                )
                if self.current_function
                else 0
            ),
            "value": clean(resolved),
            "expression": clean(
                safe_unparse(
                    node.value
                )
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

        self.generic_visit(node)


# =============================================================================
# FILE ANALYSIS
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

    Analyzer(
        analysis
    ).visit(tree)

    return analysis, None


# =============================================================================
# REPOSITORY INDEX
# =============================================================================

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
# GLOBAL FUNCTION INDEX
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
# CALLER INDEX
# =============================================================================

def build_caller_index(analyses):

    callers = defaultdict(list)

    function_names = set()

    for analysis in analyses:

        function_names.update(
            analysis.functions.keys()
        )

    for analysis in analyses:

        for call in analysis.function_calls:

            called = call["called"]

            short = called.split(".")[-1]

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

            caller_line = (
                line_no(caller.node)
                if caller
                else 0
            )

            callers[short].append(
                {
                    "path": analysis.path,
                    "category": analysis.category,
                    "line": call["line"],
                    "caller": caller_name,
                    "caller_line": caller_line,
                    "called": called,
                    "node": call["node"],
                }
            )

    return callers


# =============================================================================
# FUNCTION LOOKUP
# =============================================================================

def lookup_function(
    function_index,
    name,
    preferred_path=None,
):

    candidates = function_index.get(
        name,
        [],
    )

    if not candidates:
        return []

    if preferred_path is None:
        return candidates

    preferred = [
        item
        for item in candidates
        if item["analysis"].path
        == preferred_path
    ]

    return preferred or candidates


# =============================================================================
# CALL PARAMETER BINDING
# =============================================================================

def bind_call_arguments(
    function_info,
    call_node,
):

    bindings = {}

    params = list(
        function_info.parameters
    )

    positional = list(
        call_node.args
    )

    # -------------------------------------------------------------------------
    # POSITIONAL
    # -------------------------------------------------------------------------

    for index, arg_node in enumerate(
        positional
    ):

        if index >= len(params):

            if function_info.vararg:

                bindings.setdefault(
                    function_info.vararg,
                    [],
                ).append(
                    arg_node
                )

            continue

        bindings[
            params[index]
        ] = arg_node

    # -------------------------------------------------------------------------
    # KEYWORD
    # -------------------------------------------------------------------------

    keyword_map = {}

    for keyword in call_node.keywords:

        if keyword.arg is not None:

            keyword_map[
                keyword.arg
            ] = keyword.value

        else:

            # **kwargs
            if function_info.kwarg:

                bindings[
                    function_info.kwarg
                ] = keyword.value

    for parameter in params:

        if parameter in keyword_map:

            bindings[
                parameter
            ] = keyword_map[
                parameter
            ]

    return bindings


# =============================================================================
# PARAMETER DATAFLOW
# =============================================================================

def parameter_flow_records(
    call_record,
    function_info,
):

    bindings = bind_call_arguments(
        function_info,
        call_record["node"],
    )

    records = []

    for parameter in function_info.parameters:

        if parameter not in bindings:
            continue

        argument = bindings[
            parameter
        ]

        records.append(
            {
                "caller_path": call_record[
                    "path"
                ],
                "caller": call_record[
                    "caller"
                ],
                "caller_line": call_record[
                    "caller_line"
                ],
                "call_line": call_record[
                    "line"
                ],
                "callee": function_info.name,
                "callee_path": function_info.analysis.path,
                "callee_line": line_no(
                    function_info.node
                ),
                "parameter": parameter,
                "argument_kind": type(
                    argument
                ).__name__,
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
                "argument_expression": clean(
                    safe_unparse(argument)
                ),
                "argument_node": argument,
            }
        )

    return records


def collect_parameter_dataflow(
    analyses,
    function_index,
):

    records = []

    for analysis in analyses:

        for call in analysis.function_calls:

            called_short = (
                call["called"].split(".")[-1]
            )

            candidates = lookup_function(
                function_index,
                called_short,
                analysis.path,
            )

            for item in candidates:

                function_info = item[
                    "function"
                ]

                records.extend(
                    parameter_flow_records(
                        call,
                        function_info,
                    )
                )

    return records


# =============================================================================
# RETURN CONSUMERS
# =============================================================================

def collect_return_consumers(
    analyses,
    function_index,
):

    results = []

    for analysis in analyses:

        for call in analysis.function_calls:

            called_short = (
                call["called"].split(".")[-1]
            )

            candidates = lookup_function(
                function_index,
                called_short,
                analysis.path,
            )

            if not candidates:
                continue

            for item in candidates:

                function_info = item[
                    "function"
                ]

                if not function_info.returns:
                    continue

                results.append(
                    {
                        "caller_path": analysis.path,
                        "caller_category": analysis.category,
                        "caller_function": call[
                            "caller"
                        ],
                        "caller_line": call[
                            "caller_line"
                        ],
                        "call_line": call[
                            "line"
                        ],
                        "callee_path": function_info.analysis.path,
                        "callee_function": function_info.name,
                        "callee_line": line_no(
                            function_info.node
                        ),
                        "return_count": len(
                            function_info.returns
                        ),
                        "call_node": call["node"],
                    }
                )

    return results


# =============================================================================
# RETURN → ASSIGNMENT FLOW
# =============================================================================

def collect_return_assignment_flow(
    analyses,
    function_index,
):

    results = []

    for analysis in analyses:

        for assignment in analysis.assignments:

            node = assignment["node"]

            value = (
                node.value
                if isinstance(
                    node,
                    ast.Assign,
                )
                else None
            )

            if value is None:
                continue

            if not isinstance(
                value,
                ast.Call,
            ):
                continue

            called = dotted_name(
                value.func
            )

            if not called:
                continue

            short = called.split(".")[-1]

            candidates = lookup_function(
                function_index,
                short,
                analysis.path,
            )

            if not candidates:
                continue

            for item in candidates:

                function_info = item[
                    "function"
                ]

                if not function_info.returns:
                    continue

                results.append(
                    {
                        "path": analysis.path,
                        "category": analysis.category,
                        "line": assignment["line"],
                        "caller": assignment[
                            "function"
                        ],
                        "caller_line": assignment[
                            "function_line"
                        ],
                        "variable": assignment[
                            "variable"
                        ],
                        "callee": function_info.name,
                        "callee_path": function_info.analysis.path,
                        "callee_line": line_no(
                            function_info.node
                        ),
                        "return_count": len(
                            function_info.returns
                        ),
                        "node": node,
                    }
                )

    return results


# =============================================================================
# SQL BUILDER DETECTION
# =============================================================================

def function_has_sql_target(
    function_info,
):

    for record in function_info.assignments:

        if targets_risk_decisions(
            record["value"]
        ):
            return True

    for record in function_info.returns:

        if targets_risk_decisions(
            record["value"]
        ):
            return True

    return False


def function_has_sql_keyword(
    function_info,
):

    for record in function_info.assignments:

        value = record["value"]

        if (
            sql_operation(value)
            != "UNKNOWN"
            or "SQL" in value.upper()
        ):
            return True

    for record in function_info.returns:

        value = record["value"]

        if (
            sql_operation(value)
            != "UNKNOWN"
            or "SQL" in value.upper()
        ):
            return True

    return False


def collect_sql_builder_functions(
    analyses,
):

    records = []

    for analysis in analyses:

        for info in analysis.functions.values():

            has_target = (
                function_has_sql_target(
                    info
                )
            )

            has_sql = (
                function_has_sql_keyword(
                    info
                )
            )

            has_return = bool(
                info.returns
            )

            if has_sql or has_target:

                records.append(
                    {
                        "path": analysis.path,
                        "category": analysis.category,
                        "function": info.name,
                        "line": line_no(
                            info.node
                        ),
                        "has_sql": has_sql,
                        "has_target": has_target,
                        "has_return": has_return,
                        "returns": info.returns,
                    }
                )

    return records


# =============================================================================
# SAFE CALLER TRACE
# =============================================================================

def trace_function_to_callers(
    function_name,
    callers,
    function_index=None,
    preferred_path=None,
    depth=0,
    visited=None,
    node_budget=None,
):

    """
    v2.7 SAFE CALLER TRACE.

    IMPORTANT:

    Old v2.6 used:

        visited = {function_name}

    That is insufficient because:

        foo.py::build()
        bar.py::build()

    are different functions.

    It also allowed caller expansion to repeatedly traverse
    cycles such as:

        A -> B -> C -> A

    v2.7 therefore uses a structural identity:

        path + function + definition line

    and a hard global node budget.
    """

    if visited is None:
        visited = set()

    if node_budget is None:
        node_budget = [
            MAX_TRACE_NODES
        ]

    if depth >= MAX_CALL_DEPTH:
        return []

    if node_budget[0] <= 0:
        return []

    candidates = lookup_function(
        function_index or {},
        function_name,
        preferred_path,
    )

    if not candidates:

        # Fallback for caller names when function index
        # is unavailable.
        candidates = [
            {
                "analysis": None,
                "function": None,
            }
        ]

    results = []

    for candidate in candidates:

        if node_budget[0] <= 0:
            break

        analysis = candidate[
            "analysis"
        ]

        function_info = candidate[
            "function"
        ]

        if analysis is not None:

            identity = function_identity(
                analysis,
                function_info,
            )

        else:

            identity = (
                "<UNKNOWN>",
                function_name,
                0,
            )

        if identity in visited:
            continue

        visited_next = set(
            visited
        )

        visited_next.add(
            identity
        )

        direct = []

        if analysis is not None:

            direct = [
                item
                for item in callers.get(
                    function_name,
                    [],
                )
                if item["path"]
                == analysis.path
                or preferred_path is None
            ]

        else:

            direct = callers.get(
                function_name,
                [],
            )

        for caller in direct:

            if node_budget[0] <= 0:
                break

            node_budget[0] -= 1

            parent = caller[
                "caller"
            ]

            record = {
                "depth": depth + 1,
                "function": function_name,
                "function_path": (
                    analysis.path
                    if analysis is not None
                    else None
                ),
                "function_line": (
                    line_no(
                        function_info.node
                    )
                    if function_info is not None
                    else 0
                ),
                "caller_path": caller[
                    "path"
                ],
                "caller": parent,
                "caller_line": caller[
                    "caller_line"
                ],
                "call_line": caller[
                    "line"
                ],
                "category": caller[
                    "category"
                ],
            }

            results.append(
                record
            )

            # <module> is a terminal boundary.
            if parent == "<module>":
                continue

            if depth + 1 >= MAX_CALL_DEPTH:
                continue

            parent_candidates = lookup_function(
                function_index or {},
                parent,
                caller["path"],
            )

            for parent_candidate in parent_candidates:

                if node_budget[0] <= 0:
                    break

                parent_analysis = (
                    parent_candidate[
                        "analysis"
                    ]
                )

                parent_info = (
                    parent_candidate[
                        "function"
                    ]
                )

                parent_identity = function_identity(
                    parent_analysis,
                    parent_info,
                )

                if parent_identity in visited_next:
                    continue

                parent_trace = (
                    trace_function_to_callers(
                        parent,
                        callers,
                        function_index,
                        caller["path"],
                        depth + 1,
                        visited_next,
                        node_budget,
                    )
                )

                results.extend(
                    parent_trace
                )

    return results


# =============================================================================
# BUILDER CHAIN
# =============================================================================

def build_sql_builder_chain(
    analyses,
    function_index,
    callers,
):

    chains = []

    builders = collect_sql_builder_functions(
        analyses
    )

    for builder in builders:

        if not builder["has_return"]:
            continue

        function_name = builder[
            "function"
        ]

        builder_analysis = next(
            (
                analysis
                for analysis in analyses
                if analysis.path
                == builder["path"]
            ),
            None,
        )

        if builder_analysis is None:
            continue

        builder_info = builder_analysis.functions.get(
            function_name
        )

        if builder_info is None:
            continue

        direct_callers = [
            item
            for item in callers.get(
                function_name,
                [],
            )
            if item["path"]
            == builder_analysis.path
            or item["category"]
            in {
                "PRODUCTION",
                "FORENSIC",
                "BACKUP",
                "QUARANTINE",
            }
        ]

        upstream = trace_function_to_callers(
            function_name,
            callers,
            function_index,
            builder_analysis.path,
        )

        chains.append(
            {
                "builder": builder,
                "direct_callers": direct_callers,
                "upstream": upstream,
            }
        )

    return chains


# =============================================================================
# WRITE PATH CANDIDATES
# =============================================================================

def collect_write_paths(
    analyses,
):

    result = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            if not primitive["is_write"]:
                continue

            sql = primitive["sql"]

            direct_target = (
                targets_risk_decisions(
                    sql
                )
            )

            dynamic = (
                not direct_target
                and (
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
            )

            if direct_target or dynamic:

                result.append(
                    {
                        "primitive": primitive,
                        "direct_target": direct_target,
                        "dynamic": dynamic,
                    }
                )

    return result


# =============================================================================
# TARGET TOKEN SEARCH
# =============================================================================

def target_token_hits(
    analyses,
):

    hits = []

    for analysis in analyses:

        for index, text in enumerate(
            analysis.lines,
            1,
        ):

            if (
                TARGET_TABLE.lower()
                not in text.lower()
            ):
                continue

            hits.append(
                {
                    "path": analysis.path,
                    "category": analysis.category,
                    "line": index,
                    "text": clean(text),
                }
            )

    return hits


# =============================================================================
# REPORT: INVENTORY
# =============================================================================

def print_inventory(
    files,
    analyses,
    failures,
):

    counts = defaultdict(int)

    for path in files:

        counts[
            classify_file(path)
        ] += 1

    separator()

    print(
        "1) REPOSITORY INVENTORY"
    )

    separator()

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
        f"PRODUCTION FILES   : "
        f"{counts['PRODUCTION']}"
    )

    print(
        f"FORENSIC FILES     : "
        f"{counts['FORENSIC']}"
    )

    print(
        f"BACKUP FILES       : "
        f"{counts['BACKUP']}"
    )

    print(
        f"QUARANTINE FILES   : "
        f"{counts['QUARANTINE']}"
    )

    if failures:

        print()
        print("FAILURES:")

        for item in failures[:100]:

            print(
                f"  {item['error']} :: "
                f"{item['path']}"
            )


# =============================================================================
# REPORT: PARAMETER FLOW
# =============================================================================

def print_parameter_dataflow(
    records,
):

    separator()

    print(
        "2) ARGUMENT → PARAMETER DATAFLOW"
    )

    separator()

    print(
        f"DATAFLOW RECORDS : {len(records)}"
    )

    if not records:

        print("NONE")
        return

    for index, item in enumerate(
        records,
        1,
    ):

        print()
        print(
            f"FLOW #{index}"
        )

        print(
            f"CALLER PATH         : "
            f"{item['caller_path']}"
        )

        print(
            f"CALLER FUNCTION     : "
            f"{item['caller']}"
        )

        print(
            f"CALLER DEF LINE     : "
            f"{item['caller_line']}"
        )

        print(
            f"CALL LINE           : "
            f"{item['call_line']}"
        )

        print(
            f"CALLEE PATH         : "
            f"{item['callee_path']}"
        )

        print(
            f"CALLEE FUNCTION     : "
            f"{item['callee']}"
        )

        print(
            f"CALLEE DEF LINE     : "
            f"{item['callee_line']}"
        )

        print(
            f"PARAMETER           : "
            f"{item['parameter']}"
        )

        print(
            f"ARGUMENT KIND       : "
            f"{item['argument_kind']}"
        )

        print(
            f"ARGUMENT NAME       : "
            f"{item['argument_name']}"
        )

        print(
            f"ARGUMENT EXPRESSION : "
            f"{item['argument_expression']}"
        )


# =============================================================================
# REPORT: RETURN FLOW
# =============================================================================

def print_return_flow(
    return_consumers,
    return_assignments,
):

    separator()

    print(
        "3) RETURN VALUE PROPAGATION"
    )

    separator()

    print(
        f"RETURN CONSUMERS        : "
        f"{len(return_consumers)}"
    )

    print(
        f"RETURN→ASSIGNMENT FLOWS : "
        f"{len(return_assignments)}"
    )

    for index, item in enumerate(
        return_consumers,
        1,
    ):

        print()

        print(
            f"RETURN CONSUMER #{index}"
        )

        print(
            f"CALLER PATH : "
            f"{item['caller_path']}"
        )

        print(
            f"CALLER      : "
            f"{item['caller_function']}"
        )

        print(
            f"CALL LINE   : "
            f"{item['call_line']}"
        )

        print(
            f"CALLEE PATH : "
            f"{item['callee_path']}"
        )

        print(
            f"CALLEE      : "
            f"{item['callee_function']}"
        )

        print(
            f"RETURNS     : "
            f"{item['return_count']}"
        )

    for index, item in enumerate(
        return_assignments,
        1,
    ):

        print()

        print(
            f"RETURN ASSIGNMENT #{index}"
        )

        print(
            f"PATH        : "
            f"{item['path']}"
        )

        print(
            f"LINE        : "
            f"{item['line']}"
        )

        print(
            f"CALLER      : "
            f"{item['caller']}"
        )

        print(
            f"VARIABLE    : "
            f"{item['variable']}"
        )

        print(
            f"CALLEE      : "
            f"{item['callee']}"
        )

        print(
            f"CALLEE PATH  : "
            f"{item['callee_path']}"
        )


# =============================================================================
# REPORT: SQL BUILDERS
# =============================================================================

def print_sql_builders(
    builders,
    chains,
):

    separator()

    print(
        "4) SQL BUILDER / CALL-RETURN CHAINS"
    )

    separator()

    print(
        f"SQL BUILDER FUNCTIONS : "
        f"{len(builders)}"
    )

    print(
        f"BUILDER CHAINS        : "
        f"{len(chains)}"
    )

    for index, builder in enumerate(
        builders,
        1,
    ):

        print()

        print(
            f"BUILDER #{index}"
        )

        print(
            f"TYPE       : "
            f"{builder['category']}"
        )

        print(
            f"FILE       : "
            f"{builder['path']}"
        )

        print(
            f"LINE       : "
            f"{builder['line']}"
        )

        print(
            f"FUNCTION   : "
            f"{builder['function']}"
        )

        print(
            f"HAS SQL    : "
            f"{builder['has_sql']}"
        )

        print(
            f"HAS TARGET : "
            f"{builder['has_target']}"
        )

        print(
            f"HAS RETURN : "
            f"{builder['has_return']}"
        )

        for ret in builder[
            "returns"
        ]:

            print(
                f"RETURN {ret['line']} : "
                f"{ret['value']}"
            )

        matching = [
            chain
            for chain in chains
            if (
                chain["builder"]
                is builder
            )
        ]

        if not matching:
            continue

        chain = matching[0]

        if chain["direct_callers"]:

            print("DIRECT CALLERS:")

            for caller in chain[
                "direct_callers"
            ]:

                print(
                    f"  {caller['category']} :: "
                    f"{caller['path']}"
                )

                print(
                    f"    CALL LINE : "
                    f"{caller['line']}"
                )

                print(
                    f"    CALLER    : "
                    f"{caller['caller']}"
                )

        if chain["upstream"]:

            print("UPSTREAM TRACE:")

            for item in chain[
                "upstream"
            ]:

                print(
                    f"  DEPTH {item['depth']} :: "
                    f"{item['function']}"
                )

                print(
                    f"    FUNCTION PATH : "
                    f"{item['function_path']}"
                )

                print(
                    f"    CALLER PATH   : "
                    f"{item['caller_path']}"
                )

                print(
                    f"    CALLER        : "
                    f"{item['caller']}"
                )

                print(
                    f"    CALL LINE     : "
                    f"{item['call_line']}"
                )

        else:

            print(
                "UPSTREAM TRACE: NONE"
            )


# =============================================================================
# REPORT: WRITE PATHS
# =============================================================================

def print_write_paths(
    paths,
):

    separator()

    print(
        "5) WRITE PATH ANALYSIS"
    )

    separator()

    print(
        f"WRITE PATH SIGNALS : "
        f"{len(paths)}"
    )

    if not paths:

        print("NONE")
        return

    for index, item in enumerate(
        paths,
        1,
    ):

        primitive = item[
            "primitive"
        ]

        print()

        print(
            f"WRITE PATH #{index}"
        )

        print(
            f"FILE          : "
            f"{primitive['path']}"
        )

        print(
            f"CATEGORY      : "
            f"{primitive['category']}"
        )

        print(
            f"LINE          : "
            f"{primitive['line']}"
        )

        print(
            f"FUNCTION      : "
            f"{primitive['function']}"
        )

        print(
            f"METHOD        : "
            f"{primitive['method']}"
        )

        print(
            f"OPERATION     : "
            f"{primitive['operation']}"
        )

        print(
            f"SQL           : "
            f"{primitive['sql']}"
        )

        print(
            f"DIRECT TARGET : "
            f"{item['direct_target']}"
        )

        print(
            f"DYNAMIC       : "
            f"{item['dynamic']}"
        )


# =============================================================================
# REPORT: TARGET TOKENS
# =============================================================================

def print_target_hits(
    hits,
):

    separator()

    print(
        "6) ALL risk_decisions STATIC TOKENS"
    )

    separator()

    print(
        f"TOKEN HITS : {len(hits)}"
    )

    for item in hits:

        print()

        print(
            f"{item['category']} :: "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )

        print(
            f"TEXT : {item['text']}"
        )


# =============================================================================
# REPORT: DIRECT WRITES
# =============================================================================

def print_direct_writes(
    analyses,
):

    separator()

    print(
        "7) DIRECT risk_decisions WRITE PRIMITIVES"
    )

    separator()

    records = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            if (
                primitive["is_write"]
                and primitive["target"]
            ):

                records.append(
                    primitive
                )

    print(
        f"DIRECT TARGET WRITES : "
        f"{len(records)}"
    )

    for item in records:

        print()

        print(
            f"{item['category']} :: "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )

        print(
            f"FUNCTION : "
            f"{item['function']}"
        )

        print(
            f"METHOD   : "
            f"{item['method']}"
        )

        print(
            f"SQL      : "
            f"{item['sql']}"
        )


# =============================================================================
# REPORT: EXECUTION
# =============================================================================

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
        f"DB EXECUTION PRIMITIVES : "
        f"{total}"
    )

    print(
        f"WRITE PRIMITIVES         : "
        f"{writes}"
    )

    print(
        f"SELECT PRIMITIVES        : "
        f"{selects}"
    )

    print(
        f"UNKNOWN / DYNAMIC        : "
        f"{unknown}"
    )


# =============================================================================
# FINAL STATUS
# =============================================================================

def print_final_status(
    analyses,
    parameter_records,
    return_consumers,
    return_assignments,
    builders,
    chains,
    write_paths,
    target_hits,
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

    dynamic_paths = [
        item
        for item in write_paths
        if item["dynamic"]
    ]

    target_builder_count = sum(
        1
        for builder in builders
        if builder["has_target"]
    )

    print(
        f"DIRECT TARGET WRITE PRIMITIVES : "
        f"{len(direct)}"
    )

    print(
        f"PRODUCTION DIRECT              : "
        f"{len(production_direct)}"
    )

    print(
        f"ARGUMENT→PARAMETER FLOWS       : "
        f"{len(parameter_records)}"
    )

    print(
        f"RETURN CONSUMERS               : "
        f"{len(return_consumers)}"
    )

    print(
        f"RETURN→ASSIGNMENT FLOWS        : "
        f"{len(return_assignments)}"
    )

    print(
        f"SQL BUILDER FUNCTIONS          : "
        f"{len(builders)}"
    )

    print(
        f"TARGET-AWARE SQL BUILDERS      : "
        f"{target_builder_count}"
    )

    print(
        f"BUILDER CALL CHAINS            : "
        f"{len(chains)}"
    )

    print(
        f"DYNAMIC WRITE PATH SIGNALS     : "
        f"{len(dynamic_paths)}"
    )

    print(
        f"risk_decisions TOKEN HITS      : "
        f"{len(target_hits)}"
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
            "NEXT TARGET : verify parameter/object "
            "payload semantics."
        )

        return

    if (
        target_builder_count > 0
        and len(parameter_records) > 0
    ):

        print(
            "RESULT : TARGET-AWARE SQL BUILDER "
            "WITH PARAMETER DATAFLOW FOUND"
        )

        print(
            "PRODUCER STATUS : SUBSTANTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : connect builder return "
            "to final DB execution primitive."
        )

        return

    if (
        len(parameter_records) > 0
        and len(return_consumers) > 0
    ):

        print(
            "RESULT : ARGUMENT/PARAMETER AND "
            "CALL-RETURN DATAFLOW FOUND"
        )

        print(
            "PRODUCER STATUS : PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : PARAMETER → SQL BUILDER "
            "SEMANTIC PROPAGATION."
        )

        return

    if (
        len(chains) > 0
        or len(dynamic_paths) > 0
    ):

        print(
            "RESULT : SQL BUILDER / INDIRECT "
            "CALL PATHS EXIST"
        )

        print(
            "PRODUCER STATUS : PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : ARGUMENT → PARAMETER "
            "→ LOCAL VARIABLE PROPAGATION."
        )

        return

    print(
        "RESULT : NO RESOLVED risk_decisions "
        "PRODUCTION WRITE PATH"
    )

    print(
        "PRODUCER STATUS : NOT YET RESOLVED"
    )

    print(
        "NEXT TARGET : unresolved dynamic SQL "
        "and indirect DB writer propagation."
    )


# =============================================================================
# SAFETY
# =============================================================================

def print_safety():

    separator()

    print("SAFETY")

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

    print("NO INSERT")
    print("NO UPDATE")
    print("NO DELETE")
    print("NO ALTER")
    print("NO CREATE")
    print("NO COMMIT")
    print("NO NETWORK")
    print("NO ORDER")
    print("NO TRADE")

    separator()


# =============================================================================
# MAIN
# =============================================================================

def main():

    separator()

    print(
        "ARUNDA — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.7"
    )

    separator()

    print("MODE        : READ ONLY")
    print(f"ROOT        : {ROOT}")
    print(f"TARGET      : {TARGET_TABLE}")

    print(
        "ROOT METHOD : DB WRITE / CALL-RETURN "
        "DATAFLOW"
    )

    print(
        "CHAIN       : WRITE → SQL → BUILDER → "
        "RETURN → CALLER → ARGUMENT → PARAMETER "
        "→ LOCAL"
    )

    print()

    print(
        "IMPORTANT   : SELECT IS NOT A PRODUCER"
    )

    print(
        "IMPORTANT   : NO PRODUCTION EXECUTION"
    )

    print(
        "IMPORTANT   : CALLER TRACE IS CYCLE-SAFE"
    )

    print(
        f"MAX CALL DEPTH : {MAX_CALL_DEPTH}"
    )

    print(
        f"MAX TRACE NODES: {MAX_TRACE_NODES}"
    )

    print()

    if not ROOT.exists():

        print(
            f"ERROR: ROOT DOES NOT EXIST: {ROOT}"
        )

        return

    # -------------------------------------------------------------------------
    # 1. DISCOVERY
    # -------------------------------------------------------------------------

    files = discover_python_files()

    analyses, failures = (
        build_repository_index(
            files
        )
    )

    # -------------------------------------------------------------------------
    # 2. FUNCTION INDEX
    # -------------------------------------------------------------------------

    function_index = (
        build_function_index(
            analyses
        )
    )

    # -------------------------------------------------------------------------
    # 3. CALLER INDEX
    # -------------------------------------------------------------------------

    callers = build_caller_index(
        analyses
    )

    # -------------------------------------------------------------------------
    # 4. ARGUMENT → PARAMETER
    # -------------------------------------------------------------------------

    parameter_records = (
        collect_parameter_dataflow(
            analyses,
            function_index,
        )
    )

    # -------------------------------------------------------------------------
    # 5. RETURN CONSUMERS
    # -------------------------------------------------------------------------

    return_consumers = (
        collect_return_consumers(
            analyses,
            function_index,
        )
    )

    # -------------------------------------------------------------------------
    # 6. RETURN → ASSIGNMENT
    # -------------------------------------------------------------------------

    return_assignments = (
        collect_return_assignment_flow(
            analyses,
            function_index,
        )
    )

    # -------------------------------------------------------------------------
    # 7. SQL BUILDERS
    # -------------------------------------------------------------------------

    builders = (
        collect_sql_builder_functions(
            analyses
        )
    )

    # -------------------------------------------------------------------------
    # 8. BUILDER CALL CHAINS
    # -------------------------------------------------------------------------

    chains = (
        build_sql_builder_chain(
            analyses,
            function_index,
            callers,
        )
    )

    # -------------------------------------------------------------------------
    # 9. WRITE PATHS
    # -------------------------------------------------------------------------

    write_paths = (
        collect_write_paths(
            analyses
        )
    )

    # -------------------------------------------------------------------------
    # 10. TARGET TOKENS
    # -------------------------------------------------------------------------

    target_hits = (
        target_token_hits(
            analyses
        )
    )

    # -------------------------------------------------------------------------
    # REPORTS
    # -------------------------------------------------------------------------

    print_inventory(
        files,
        analyses,
        failures,
    )

    print_parameter_dataflow(
        parameter_records
    )

    print_return_flow(
        return_consumers,
        return_assignments,
    )

    print_sql_builders(
        builders,
        chains,
    )

    print_write_paths(
        write_paths
    )

    print_target_hits(
        target_hits
    )

    print_direct_writes(
        analyses
    )

    print_execution_summary(
        analyses
    )

    print_final_status(
        analyses,
        parameter_records,
        return_consumers,
        return_assignments,
        builders,
        chains,
        write_paths,
        target_hits,
    )

    print_safety()

    separator()

    print(
        "END — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.7"
    )

    separator()


if __name__ == "__main__":
    main()