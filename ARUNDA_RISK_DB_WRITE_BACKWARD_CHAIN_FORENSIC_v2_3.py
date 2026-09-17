# -*- coding: utf-8 -*-

"""
ARUNDA — RISK_v0.1 ACTUAL DB WRITE BACKWARD CHAIN FORENSIC v2.3

OBJECTIVE
---------
Find ONLY actual/static production DB WRITE paths targeting:

    risk_decisions

Backward chain:

    DB WRITE PRIMITIVE
        ->
    SQL EXPRESSION
        ->
    TARGET TABLE
        ->
    PARAMS / OBJECT
        ->
    PRODUCER FUNCTION
        ->
    CALLER

IMPORTANT
---------
This is STATIC FORENSIC ANALYSIS ONLY.

No:
    - production imports
    - production execution
    - database connection
    - database reads
    - database writes
    - network
    - orders
    - trades

SELECT statements are NOT producer candidates.

The analyzer starts from DB execution primitives and works backward.
It does NOT start from "risk" variable names.

v2.4 REPAIR
------------
- Python 3.13-safe AST string handling
- Removed deprecated ast.Str dependency
- Added variable-resolution cycle protection
- Added hard recursion-depth protection
- Preserved static-only architecture
- Preserved DB WRITE primitive discovery root
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

MAX_CALL_DEPTH = 10

MAX_RESOLUTION_DEPTH = 50

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
# SQL
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
# VARIABLE GROUPS
# =============================================================================

SQL_NAMES = {
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

PARAM_NAMES = {
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

RISK_NAMES = {
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


def clean(text, limit=1000):

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\n",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def separator(
    char="=",
    width=110,
):

    print(
        char * width
    )


def source_window(
    lines,
    line,
    radius=4,
):

    if not lines or line <= 0:
        return ""

    start = max(
        1,
        line - radius,
    )

    end = min(
        len(lines),
        line + radius,
    )

    result = []

    for number in range(
        start,
        end + 1,
    ):

        marker = (
            ">>>"
            if number == line
            else "   "
        )

        result.append(
            f"{marker} {number:5d} | "
            f"{lines[number - 1].rstrip()}"
        )

    return "\n".join(result)


# =============================================================================
# FILE CLASSIFICATION
# =============================================================================

def classify_file(path: Path):

    normalized = str(path).lower()

    if any(
        marker in normalized
        for marker in QUARANTINE_MARKERS
    ):
        return "QUARANTINE"

    if (
        "\\backup" in normalized
        or "\\_backups" in normalized
        or any(
            marker in path.name.lower()
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

        if raw.startswith(
            b"\xef\xbb\xbf"
        ):
            raw = raw[3:]

        return raw.decode(
            "utf-8"
        )

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


def parse_source(
    source,
    path,
):

    try:

        return ast.parse(
            source,
            filename=str(path),
        )

    except Exception:

        return None


# =============================================================================
# AST STRING RESOLUTION
# =============================================================================

def dotted_name(node):

    if isinstance(
        node,
        ast.Name,
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute,
    ):

        parent = dotted_name(
            node.value
        )

        if parent:
            return (
                f"{parent}.{node.attr}"
            )

        return node.attr

    return None


def literal_string(node):

    """
    Python 3.13-safe string extraction.

    IMPORTANT:
    Do NOT use ast.Str here.
    In Python 3.13 ast.Str is deprecated
    and its isinstance machinery emits
    deprecation behavior.
    """

    if isinstance(
        node,
        ast.Constant,
    ):

        if isinstance(
            node.value,
            str,
        ):
            return node.value

    return None


def literal_value(node):

    if isinstance(
        node,
        ast.Constant,
    ):
        return node.value

    return None


def resolve_string(
    node,
    env=None,
    visited=None,
    depth=0,
):

    """
    Resolve statically-known strings.

    Safety mechanisms:

        1. MAX_RESOLUTION_DEPTH
        2. variable cycle detection

    Example cycle:

        a = b
        b = c
        c = a

    becomes:

        {CYCLE:a}

    instead of infinite recursion.
    """

    if node is None:
        return ""

    if env is None:
        env = {}

    if visited is None:
        visited = set()

    # -------------------------------------------------------------------------
    # HARD DEPTH GUARD
    # -------------------------------------------------------------------------

    if depth >= MAX_RESOLUTION_DEPTH:

        return (
            "{RESOLUTION_DEPTH_LIMIT}"
        )

    # -------------------------------------------------------------------------
    # LITERAL
    # -------------------------------------------------------------------------

    literal = literal_string(
        node
    )

    if literal is not None:
        return literal

    # -------------------------------------------------------------------------
    # VARIABLE
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.Name,
    ):

        name = node.id

        if name not in env:
            return ""

        # ---------------------------------------------------------------------
        # CYCLE DETECTION
        # ---------------------------------------------------------------------

        if name in visited:

            return (
                f"{{CYCLE:{name}}}"
            )

        visited.add(name)

        try:

            return resolve_string(
                env[name],
                env,
                visited,
                depth + 1,
            )

        finally:

            visited.remove(name)

    # -------------------------------------------------------------------------
    # F-STRING
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.JoinedStr,
    ):

        parts = []

        for value in node.values:

            if isinstance(
                value,
                ast.Constant,
            ):

                if isinstance(
                    value.value,
                    str,
                ):

                    parts.append(
                        value.value
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

        return "".join(
            parts
        )

    # -------------------------------------------------------------------------
    # STRING CONCATENATION
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.BinOp,
    ):

        if isinstance(
            node.op,
            ast.Add,
        ):

            left = resolve_string(
                node.left,
                env,
                visited,
                depth + 1,
            )

            right = resolve_string(
                node.right,
                env,
                visited,
                depth + 1,
            )

            return (
                left + right
            )

    # -------------------------------------------------------------------------
    # .format()
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.Call,
    ):

        fn = dotted_name(
            node.func
        )

        if (
            fn
            and fn.endswith(
                ".format"
            )
        ):

            base = resolve_string(
                node.func.value,
                env,
                visited,
                depth + 1,
            )

            return (
                base + " {FORMAT}"
            )

    return ""


def resolve_any(
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

    if depth >= MAX_RESOLUTION_DEPTH:

        return (
            "{RESOLUTION_DEPTH_LIMIT}"
        )

    if isinstance(
        node,
        ast.Name,
    ):

        name = node.id

        if name in env:

            if name in visited:

                return (
                    f"{CYCLE:{name}}"
                )

            visited.add(name)

            try:

                return resolve_any(
                    env[name],
                    env,
                    visited,
                    depth + 1,
                )

            finally:

                visited.remove(name)

    text = resolve_string(
        node,
        env,
        visited,
        depth,
    )

    if text:
        return text

    return ""


# =============================================================================
# SQL CLASSIFICATION
# =============================================================================

def sql_operation(sql):

    if not sql:
        return "UNKNOWN"

    match = WRITE_RE.search(
        sql
    )

    if match:

        token = (
            match.group(1)
            .upper()
        )

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


def is_db_write_primitive(node):

    if not isinstance(
        node,
        ast.Call,
    ):
        return False

    method = dotted_name(
        node.func
    )

    if not method:
        return False

    return (
        method.endswith(
            ".execute"
        )
        or method.endswith(
            ".executemany"
        )
        or method.endswith(
            ".executescript"
        )
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

        self.calls = []

        self.returns = []

        self.assignments = []

        self.arguments = []

        self.write_primitives = []


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

        self.write_primitives = []

        self.sql_assignments = []

        self.parameter_assignments = []

        self.target_refs = []

        self.function_calls = []

        self.return_nodes = []

        self.field_nodes = []


# =============================================================================
# FUNCTION RANGE
# =============================================================================

def containing_function(
    analysis,
    line,
):

    best = None

    for info in analysis.functions.values():

        start = line_no(
            info.node
        )

        end = end_line(
            info.node
        )

        if (
            start <= line <= end
        ):

            if best is None:

                best = info

            else:

                current_size = (
                    end_line(
                        best.node
                    )
                    - line_no(
                        best.node
                    )
                )

                candidate_size = (
                    end
                    - start
                )

                if (
                    candidate_size
                    < current_size
                ):

                    best = info

    return best


# =============================================================================
# AST ANALYZER
# =============================================================================

class Analyzer(
    ast.NodeVisitor
):

    def __init__(
        self,
        analysis,
    ):

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

    def visit_FunctionDef(
        self,
        node,
    ):

        info = FunctionInfo(
            self.analysis,
            node,
        )

        self.analysis.functions[
            node.name
        ] = info

        for arg in node.args.args:

            info.arguments.append(
                arg.arg
            )

        self.function_stack.append(
            info
        )

        self.environment_stack.append(
            {}
        )

        self.generic_visit(
            node
        )

        self.environment_stack.pop()

        self.function_stack.pop()

    def visit_AsyncFunctionDef(
        self,
        node,
    ):

        self.visit_FunctionDef(
            node
        )

    # -------------------------------------------------------------------------
    # ASSIGNMENT
    # -------------------------------------------------------------------------

    def visit_Assign(
        self,
        node,
    ):

        for target in node.targets:

            if isinstance(
                target,
                ast.Name,
            ):

                self.current_env[
                    target.id
                ] = node.value

                variable = target.id

                value = resolve_string(
                    node.value,
                    self.current_env,
                )

                lowered = (
                    variable.lower()
                )

                # -------------------------------------------------------------
                # SQL VARIABLE
                # -------------------------------------------------------------

                if (
                    lowered in SQL_NAMES
                    or "sql" in lowered
                    or "query" in lowered
                    or "statement" in lowered
                ):

                    self.analysis.sql_assignments.append(
                        {
                            "path": self.analysis.path,
                            "category": self.analysis.category,
                            "line": line_no(node),
                            "function": (
                                self.current_function.name
                                if self.current_function
                                else "<module>"
                            ),
                            "variable": variable,
                            "sql": clean(value),
                            "operation": sql_operation(value),
                            "target": targets_risk_decisions(value),
                        }
                    )

                # -------------------------------------------------------------
                # PARAMETER / RISK VARIABLE
                # -------------------------------------------------------------

                if (
                    lowered in PARAM_NAMES
                    or lowered in RISK_NAMES
                    or "risk" in lowered
                    or "param" in lowered
                    or "payload" in lowered
                ):

                    self.analysis.parameter_assignments.append(
                        {
                            "path": self.analysis.path,
                            "category": self.analysis.category,
                            "line": line_no(node),
                            "function": (
                                self.current_function.name
                                if self.current_function
                                else "<module>"
                            ),
                            "variable": variable,
                            "value": clean(
                                resolve_string(
                                    node.value,
                                    self.current_env,
                                )
                            ),
                        }
                    )

        self.generic_visit(
            node
        )

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    def visit_Call(
        self,
        node,
    ):

        called = dotted_name(
            node.func
        )

        if called:

            self.analysis.function_calls.append(
                {
                    "path": self.analysis.path,
                    "category": self.analysis.category,
                    "line": line_no(node),
                    "function": (
                        self.current_function.name
                        if self.current_function
                        else "<module>"
                    ),
                    "called": called,
                    "args": node.args,
                    "node": node,
                }
            )

        # ---------------------------------------------------------------------
        # DB EXECUTION PRIMITIVE
        # ---------------------------------------------------------------------

        if is_db_write_primitive(
            node
        ):

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
                "params_nodes": node.args[1:],
            }

            self.analysis.write_primitives.append(
                item
            )

            if self.current_function:

                self.current_function.write_primitives.append(
                    item
                )

        self.generic_visit(
            node
        )

    # -------------------------------------------------------------------------
    # RETURN
    # -------------------------------------------------------------------------

    def visit_Return(
        self,
        node,
    ):

        self.analysis.return_nodes.append(
            {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": (
                    self.current_function.name
                    if self.current_function
                    else "<module>"
                ),
                "node": node,
                "value": resolve_string(
                    node.value,
                    self.current_env,
                ),
            }
        )

        if self.current_function:

            self.current_function.returns.append(
                node
            )

        self.generic_visit(
            node
        )


# =============================================================================
# FILE ANALYSIS
# =============================================================================

def analyze_file(
    path,
):

    source = read_source(
        path
    )

    if source is None:

        return (
            None,
            "READ_FAILURE",
        )

    tree = parse_source(
        source,
        path,
    )

    if tree is None:

        return (
            None,
            "AST_FAILURE",
        )

    analysis = FileAnalysis(
        path,
        source,
        tree,
    )

    Analyzer(
        analysis
    ).visit(
        tree
    )

    return (
        analysis,
        None,
    )


# =============================================================================
# REPOSITORY INDEX
# =============================================================================

def build_repository_index(
    files,
):

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

    return (
        analyses,
        failures,
    )


# =============================================================================
# GLOBAL FUNCTION INDEX
# =============================================================================

def build_function_index(
    analyses,
):

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

def build_caller_index(
    analyses,
):

    callers = defaultdict(list)

    function_names = set()

    for analysis in analyses:

        function_names.update(
            analysis.functions.keys()
        )

    for analysis in analyses:

        for call in analysis.function_calls:

            called = call["called"]

            short = called.split(
                "."
            )[-1]

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

            callers[short].append(
                {
                    "path": analysis.path,
                    "category": analysis.category,
                    "line": call["line"],
                    "caller": caller_name,
                }
            )

    return callers


# =============================================================================
# BACKWARD PARAM RESOLUTION
# =============================================================================

def resolve_argument_name(
    function_info,
    arg_index,
    call_node,
):

    if arg_index >= len(
        call_node.args
    ):

        return None

    arg = call_node.args[
        arg_index
    ]

    if isinstance(
        arg,
        ast.Name,
    ):

        return arg.id

    return None


def describe_param_node(
    analysis,
    node,
):

    if node is None:

        return {
            "kind": "UNKNOWN",
            "value": "",
        }

    if isinstance(
        node,
        ast.Name,
    ):

        return {
            "kind": "VARIABLE",
            "value": node.id,
        }

    if isinstance(
        node,
        ast.Dict,
    ):

        keys = []

        for key in node.keys:

            value = literal_string(
                key
            )

            if value:
                keys.append(
                    value
                )

        return {
            "kind": "DICT",
            "value": keys,
        }

    if isinstance(
        node,
        ast.Tuple,
    ):

        return {
            "kind": "TUPLE",
            "value": len(
                node.elts
            ),
        }

    if isinstance(
        node,
        ast.List,
    ):

        return {
            "kind": "LIST",
            "value": len(
                node.elts
            ),
        }

    if isinstance(
        node,
        ast.Call,
    ):

        return {
            "kind": "CALL",
            "value": dotted_name(
                node.func
            ),
        }

    return {
        "kind": type(node).__name__,
        "value": "",
    }


# =============================================================================
# WRITE CANDIDATES
# =============================================================================

def collect_actual_write_candidates(
    analyses,
):

    candidates = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            # -----------------------------------------------------------------
            # HARD FILTER:
            # ONLY ACTUAL SQL WRITE
            # -----------------------------------------------------------------

            if not primitive["is_write"]:
                continue

            # -----------------------------------------------------------------
            # HARD FILTER:
            # ONLY TARGET TABLE
            # -----------------------------------------------------------------

            if not primitive["target"]:
                continue

            candidate = dict(
                primitive
            )

            # -----------------------------------------------------------------
            # SCORE
            # -----------------------------------------------------------------

            score = 0

            reasons = []

            if (
                analysis.category
                == "PRODUCTION"
            ):

                score += 50

                reasons.append(
                    "PRODUCTION"
                )

            elif (
                analysis.category
                == "FORENSIC"
            ):

                score += 10

                reasons.append(
                    "FORENSIC"
                )

            elif (
                analysis.category
                == "BACKUP"
            ):

                score += 5

                reasons.append(
                    "BACKUP"
                )

            score += 50

            reasons.append(
                "DB_WRITE_PRIMITIVE"
            )

            score += 50

            reasons.append(
                "WRITE_OPERATION"
            )

            score += 50

            reasons.append(
                "TARGET_risk_decisions"
            )

            candidate[
                "score"
            ] = score

            candidate[
                "reasons"
            ] = reasons

            candidates.append(
                candidate
            )

    candidates.sort(
        key=lambda x: (
            -x["score"],
            str(x["path"]),
            x["line"],
        )
    )

    return candidates


# =============================================================================
# TARGET READS
# =============================================================================

def collect_select_consumers(
    analyses,
):

    result = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            sql = primitive[
                "sql"
            ]

            if (
                primitive["operation"]
                == "SELECT"
                and targets_risk_decisions(
                    sql
                )
            ):

                result.append(
                    primitive
                )

    return result


# =============================================================================
# PARAM FLOW
# =============================================================================

def extract_param_flow(
    candidate,
):

    params = []

    for node in candidate[
        "params_nodes"
    ]:

        params.append(
            describe_param_node(
                None,
                node,
            )
        )

    return params


# =============================================================================
# FIELD / DICT FORENSICS
# =============================================================================

def collect_dict_fields(
    analyses,
):

    results = []

    class Visitor(
        ast.NodeVisitor
    ):

        def __init__(
            self,
            analysis,
        ):

            self.analysis = analysis

            self.function_stack = []

        def visit_FunctionDef(
            self,
            node,
        ):

            self.function_stack.append(
                node.name
            )

            self.generic_visit(
                node
            )

            self.function_stack.pop()

        def visit_AsyncFunctionDef(
            self,
            node,
        ):

            self.visit_FunctionDef(
                node
            )

        def visit_Dict(
            self,
            node,
        ):

            fields = []

            for key in node.keys:

                text = literal_string(
                    key
                )

                if text:
                    fields.append(
                        text
                    )

            if fields:

                results.append(
                    {
                        "path": self.analysis.path,
                        "category": self.analysis.category,
                        "line": line_no(node),
                        "function": (
                            self.function_stack[-1]
                            if self.function_stack
                            else "<module>"
                        ),
                        "fields": fields,
                    }
                )

            self.generic_visit(
                node
            )

    for analysis in analyses:

        Visitor(
            analysis
        ).visit(
            analysis.tree
        )

    return results


# =============================================================================
# BACKWARD CALLER CHAIN
# =============================================================================

def find_callers_of_function(
    callers,
    function_name,
):

    return callers.get(
        function_name,
        [],
    )


def backward_caller_chain(
    analysis,
    function_name,
    callers,
    depth=0,
    visited=None,
):

    if visited is None:
        visited = set()

    if depth >= MAX_CALL_DEPTH:
        return []

    key = (
        str(analysis.path),
        function_name,
    )

    if key in visited:
        return []

    visited.add(
        key
    )

    records = []

    for caller in callers.get(
        function_name,
        [],
    ):

        records.append(
            {
                "depth": depth + 1,
                "path": caller["path"],
                "category": caller["category"],
                "line": caller["line"],
                "caller": caller["caller"],
            }
        )

    return records


# =============================================================================
# BACKWARD TRACE
# =============================================================================

def build_backward_trace(
    candidate,
    analyses,
    function_index,
    callers,
):

    path = candidate[
        "path"
    ]

    function_name = candidate[
        "function"
    ]

    analysis = next(
        (
            item
            for item in analyses
            if item.path == path
        ),
        None,
    )

    if analysis is None:

        return {
            "candidate": candidate,
            "params": [],
            "producer": None,
            "callers": [],
        }

    producer = None

    infos = function_index.get(
        function_name,
        [],
    )

    for item in infos:

        if (
            item["analysis"].path
            == analysis.path
        ):

            producer = item[
                "function"
            ]

            break

    caller_records = []

    if producer:

        caller_records = callers.get(
            producer.name,
            [],
        )

    return {
        "candidate": candidate,
        "params": extract_param_flow(
            candidate
        ),
        "producer": producer,
        "callers": caller_records,
    }


# =============================================================================
# INVENTORY
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
        f"PYTHON FILES       : "
        f"{len(files)}"
    )

    print(
        f"ANALYZED FILES     : "
        f"{len(analyses)}"
    )

    print(
        f"AST/READ FAILURES  : "
        f"{len(failures)}"
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

        print(
            "FAILURES:"
        )

        for item in failures[:100]:

            print(
                f"  {item['error']} :: "
                f"{item['path']}"
            )


# =============================================================================
# WRITE PRIMITIVE REPORT
# =============================================================================

def print_write_primitive_summary(
    analyses,
):

    separator()

    print(
        "2) ALL DB EXECUTION PRIMITIVES"
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
# ACTUAL TARGET WRITES
# =============================================================================

def print_actual_writes(
    candidates,
    analyses,
):

    separator()

    print(
        "3) ACTUAL risk_decisions "
        "WRITE CANDIDATES"
    )

    separator()

    print(
        f"TARGET WRITE CANDIDATES : "
        f"{len(candidates)}"
    )

    if not candidates:

        print()

        print(
            "NO STATIC risk_decisions "
            "WRITE FOUND."
        )

        print(
            "SELECT consumers were excluded."
        )

        print(
            "Risk-variable names were NOT "
            "used as the discovery root."
        )

        return

    for index, item in enumerate(
        candidates,
        1,
    ):

        print()

        print(
            "-" * 110
        )

        print(
            f"WRITE #{index}"
        )

        print(
            f"SCORE     : "
            f"{item['score']}"
        )

        print(
            f"TYPE      : "
            f"{item['category']}"
        )

        print(
            f"FILE      : "
            f"{item['path']}"
        )

        print(
            f"LINE      : "
            f"{item['line']}"
        )

        print(
            f"FUNCTION  : "
            f"{item['function']}"
        )

        print(
            f"METHOD    : "
            f"{item['method']}"
        )

        print(
            f"OPERATION : "
            f"{item['operation']}"
        )

        print(
            f"TARGET    : "
            f"{item['target']}"
        )

        print(
            f"SQL       : "
            f"{item['sql']}"
        )

        print(
            f"REASONS   : "
            f"{', '.join(item['reasons'])}"
        )

        analysis = next(
            (
                a
                for a in analyses
                if a.path == item["path"]
            ),
            None,
        )

        if analysis:

            print()

            print(
                source_window(
                    analysis.lines,
                    item["line"],
                    5,
                )
            )


# =============================================================================
# SELECT CONSUMERS
# =============================================================================

def print_select_consumers(
    analyses,
):

    consumers = (
        collect_select_consumers(
            analyses
        )
    )

    separator()

    print(
        "4) risk_decisions "
        "SELECT CONSUMERS"
    )

    separator()

    print(
        f"SELECT CONSUMERS : "
        f"{len(consumers)}"
    )

    if not consumers:

        print(
            "NONE"
        )

        return

    for item in consumers:

        print()

        print(
            f"{item['category']} :: "
            f"{item['path']} :: "
            f"LINE {item['line']} :: "
            f"{item['function']}"
        )

        print(
            f"SQL : {item['sql']}"
        )


# =============================================================================
# BACKWARD CHAINS
# =============================================================================

def print_backward_chains(
    candidates,
    analyses,
    function_index,
    callers,
):

    separator()

    print(
        "5) BACKWARD CHAIN"
    )

    separator()

    if not candidates:

        print(
            "NO WRITE CHAIN AVAILABLE."
        )

        return

    for index, candidate in enumerate(
        candidates,
        1,
    ):

        print()

        separator(
            "#",
            110,
        )

        print(
            f"BACKWARD TRACE #{index}"
        )

        print()

        print(
            "DB WRITE PRIMITIVE"
        )

        print(
            f"  METHOD   : "
            f"{candidate['method']}"
        )

        print(
            f"  FILE     : "
            f"{candidate['path']}"
        )

        print(
            f"  LINE     : "
            f"{candidate['line']}"
        )

        print(
            f"  FUNCTION : "
            f"{candidate['function']}"
        )

        print()

        print(
            "↓ SQL EXPRESSION"
        )

        print(
            f"  SQL       : "
            f"{candidate['sql']}"
        )

        print(
            f"  OPERATION : "
            f"{candidate['operation']}"
        )

        print()

        print(
            "↓ TARGET TABLE"
        )

        print(
            f"  TARGET : "
            f"{TARGET_TABLE}"
        )

        print()

        print(
            "↓ PARAMS / OBJECT"
        )

        params = extract_param_flow(
            candidate
        )

        if not params:

            print(
                "  NOT RESOLVED"
            )

        else:

            for pindex, param in enumerate(
                params,
                1,
            ):

                print(
                    f"  PARAM #{pindex}"
                )

                print(
                    f"    KIND  : "
                    f"{param['kind']}"
                )

                print(
                    f"    VALUE : "
                    f"{param['value']}"
                )

        print()

        print(
            "↓ PRODUCER FUNCTION"
        )

        print(
            f"  FILE     : "
            f"{candidate['path']}"
        )

        print(
            f"  FUNCTION : "
            f"{candidate['function']}"
        )

        print(
            f"  LINE     : "
            f"{candidate['line']}"
        )

        print()

        print(
            "↓ CALLER"
        )

        records = callers.get(
            candidate["function"],
            [],
        )

        if not records:

            print(
                "  NOT RESOLVED"
            )

        else:

            for record in records:

                print(
                    f"  {record['category']} :: "
                    f"{record['path']}"
                )

                print(
                    f"    LINE   : "
                    f"{record['line']}"
                )

                print(
                    f"    CALLER : "
                    f"{record['caller']}"
                )


# =============================================================================
# SQL VARIABLE REPORT
# =============================================================================

def print_sql_resolution(
    analyses,
):

    separator()

    print(
        "6) SQL EXPRESSION RESOLUTION"
    )

    separator()

    records = []

    for analysis in analyses:

        for item in analysis.sql_assignments:

            if (
                item["target"]
                and item["operation"]
                in {
                    "INSERT",
                    "UPDATE",
                    "REPLACE",
                    "UPSERT",
                }
            ):

                records.append(
                    item
                )

    print(
        "RESOLVED TARGET WRITE "
        "SQL VARIABLES : "
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
            f"FUNCTION  : "
            f"{item['function']}"
        )

        print(
            f"VARIABLE  : "
            f"{item['variable']}"
        )

        print(
            f"OPERATION : "
            f"{item['operation']}"
        )

        print(
            f"SQL       : "
            f"{item['sql']}"
        )


# =============================================================================
# DICT / OBJECT CONTEXT
# =============================================================================

def print_object_context(
    analyses,
):

    separator()

    print(
        "7) OBJECT / DICT CONTEXT"
    )

    separator()

    records = collect_dict_fields(
        analyses
    )

    relevant = []

    for item in records:

        fields = [
            str(field).lower()
            for field in item["fields"]
        ]

        field_text = " ".join(
            fields
        )

        if (
            "risk" in field_text
            or "decision" in field_text
            or "snapshot_id" in fields
            or "asset" in fields
            or "status" in fields
            or "reason" in fields
        ):

            relevant.append(
                item
            )

    print(
        f"RISK-RELEVANT OBJECT "
        f"CONTEXT : {len(relevant)}"
    )

    for item in relevant:

        print()

        print(
            f"{item['category']} :: "
            f"{item['path']} :: "
            f"LINE {item['line']} :: "
            f"{item['function']}"
        )

        print(
            "FIELDS : "
            + ", ".join(
                item["fields"]
            )
        )


# =============================================================================
# PRODUCER STATUS
# =============================================================================

def print_final_status(
    candidates,
):

    separator()

    print(
        "8) FINAL PRODUCER STATUS"
    )

    separator()

    production = [
        item
        for item in candidates
        if item["category"]
        == "PRODUCTION"
    ]

    forensic = [
        item
        for item in candidates
        if item["category"]
        == "FORENSIC"
    ]

    backup = [
        item
        for item in candidates
        if item["category"]
        == "BACKUP"
    ]

    quarantine = [
        item
        for item in candidates
        if item["category"]
        == "QUARANTINE"
    ]

    print(
        f"TARGET WRITE PRIMITIVES : "
        f"{len(candidates)}"
    )

    print(
        f"PRODUCTION               : "
        f"{len(production)}"
    )

    print(
        f"FORENSIC                 : "
        f"{len(forensic)}"
    )

    print(
        f"BACKUP                   : "
        f"{len(backup)}"
    )

    print(
        f"QUARANTINE              : "
        f"{len(quarantine)}"
    )

    print()

    if production:

        best = production[0]

        print(
            "RESULT : PRODUCTION "
            "risk_decisions "
            "WRITE CANDIDATE FOUND"
        )

        print()

        print(
            f"PRODUCER FUNCTION : "
            f"{best['function']}"
        )

        print(
            f"FILE              : "
            f"{best['path']}"
        )

        print(
            f"LINE              : "
            f"{best['line']}"
        )

        print(
            f"METHOD            : "
            f"{best['method']}"
        )

        print(
            f"OPERATION         : "
            f"{best['operation']}"
        )

        print(
            f"SQL               : "
            f"{best['sql']}"
        )

        print()

        print(
            "STATUS : WRITE PATH IDENTIFIED."
        )

    elif candidates:

        print(
            "RESULT : risk_decisions "
            "WRITE FOUND OUTSIDE PRODUCTION"
        )

        print(
            "PRODUCER STATUS : "
            "PRODUCTION PRODUCER NOT FOUND"
        )

    else:

        print(
            "RESULT : NO STATIC "
            "risk_decisions WRITE FOUND"
        )

        print(
            "PRODUCER STATUS : NOT FOUND"
        )

        print()

        print(
            "NEXT TARGET : dynamic SQL / "
            "indirect DB writer resolution"
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
        "BACKWARD CHAIN FORENSIC v2.4"
    )

    separator()

    print(
        "MODE         : READ ONLY"
    )

    print(
        f"ROOT         : {ROOT}"
    )

    print(
        f"TARGET       : {TARGET_TABLE}"
    )

    print(
        "ROOT METHOD  : DB WRITE PRIMITIVE"
    )

    print(
        "CHAIN        : "
        "WRITE → SQL → TARGET → PARAMS → "
        "PRODUCER → CALLER"
    )

    print()

    print(
        "IMPORTANT    : SELECT IS NOT A PRODUCER"
    )

    print(
        "IMPORTANT    : RISK NAME SEARCH IS NOT "
        "THE DISCOVERY ROOT"
    )

    separator()

    if not ROOT.exists():

        print(
            f"ERROR: ROOT DOES NOT EXIST: "
            f"{ROOT}"
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

    callers = build_caller_index(
        analyses
    )

    candidates = (
        collect_actual_write_candidates(
            analyses
        )
    )

    print_inventory(
        files,
        analyses,
        failures,
    )

    print_write_primitive_summary(
        analyses
    )

    print_actual_writes(
        candidates,
        analyses,
    )

    print_select_consumers(
        analyses
    )

    print_backward_chains(
        candidates,
        analyses,
        function_index,
        callers,
    )

    print_sql_resolution(
        analyses
    )

    print_object_context(
        analyses
    )

    print_final_status(
        candidates
    )

    print_safety()

    separator()

    print(
        "END — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.3"
    )

    separator()


if __name__ == "__main__":
    main()