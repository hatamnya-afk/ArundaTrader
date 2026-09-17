# -*- coding: utf-8 -*-

"""
ARUNDA — RISK_v0.1 ACTUAL DB WRITE BACKWARD CHAIN FORENSIC v2.4

OBJECTIVE
---------
Find actual/static production DB WRITE paths targeting:

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

v2.4 FOCUS
----------
INDIRECT / DYNAMIC WRITER RESOLUTION

This version specifically improves:

    - cycle-safe variable resolution
    - bounded recursive resolution
    - variable aliases
    - string concatenation
    - f-strings
    - .format()
    - SQL passed through variables
    - SQL returned from functions
    - SQL builder calls
    - execute / executemany / executescript
    - indirect target propagation
    - parameter/object flow
    - caller tracing

IMPORTANT
---------
STATIC FORENSIC ANALYSIS ONLY.

NO:
    - production imports
    - production execution
    - database connection
    - database reads
    - database writes
    - network
    - orders
    - trades

SELECT statements are NOT producer candidates.

The analyzer starts from DB execution primitives.
It does NOT start from "risk" variable names.
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
MAX_RESOLVE_DEPTH = 40

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


def clean(text, limit=1600):

    if text is None:
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def separator(char="=", width=110):
    print(char * width)


def source_window(
    lines,
    line,
    radius=5,
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
    name = path.name.lower()

    if any(
        marker in normalized
        for marker in QUARANTINE_MARKERS
    ):
        return "QUARANTINE"

    if (
        "\\backup" in normalized
        or "\\_backups" in normalized
        or any(
            marker in name
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
# SOURCE DISCOVERY
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
# AST NAME HELPERS
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


# =============================================================================
# SAFE LITERAL RESOLUTION
# =============================================================================

def literal_string(node):

    """
    Python 3.13 safe literal resolver.

    IMPORTANT:
    Do NOT use ast.Str.

    Python 3.13 deprecates ast.Str
    instance checks and they can trigger
    warnings/deprecation machinery.

    ast.Constant is sufficient.
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


# =============================================================================
# CYCLE-SAFE STRING RESOLVER
# =============================================================================

def resolve_string(
    node,
    env=None,
    visited=None,
    depth=0,
):

    """
    Resolve string-like AST expressions.

    v2.4 safety properties:

        1. MAX_RESOLVE_DEPTH
        2. visited node identity
        3. visited variable names
        4. no ast.Str
        5. no unbounded recursive alias chain

    Returns a forensic representation.

    Unknown/dynamic values are represented as
    placeholders instead of causing recursion.
    """

    if node is None:
        return ""

    if env is None:
        env = {}

    if visited is None:
        visited = set()

    if depth >= MAX_RESOLVE_DEPTH:
        return "{RESOLVE_DEPTH_LIMIT}"

    node_key = (
        "NODE",
        id(node),
    )

    if node_key in visited:
        return "{RESOLVE_CYCLE}"

    visited.add(node_key)

    # -------------------------------------------------------------------------
    # Literal
    # -------------------------------------------------------------------------

    literal = literal_string(node)

    if literal is not None:
        return literal

    # -------------------------------------------------------------------------
    # Name
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.Name,
    ):

        name_key = (
            "NAME",
            node.id,
        )

        if name_key in visited:
            return (
                "{VARIABLE_CYCLE:"
                f"{node.id}"
                "}"
            )

        if node.id in env:

            next_visited = set(
                visited
            )

            next_visited.add(
                name_key
            )

            return resolve_string(
                env[node.id],
                env,
                next_visited,
                depth + 1,
            )

        return (
            "{VAR:"
            f"{node.id}"
            "}"
        )

    # -------------------------------------------------------------------------
    # Attribute
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.Attribute,
    ):

        name = dotted_name(node)

        if name:
            return (
                "{ATTR:"
                f"{name}"
                "}"
            )

        return "{ATTRIBUTE}"

    # -------------------------------------------------------------------------
    # f-string
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

                else:
                    parts.append(
                        str(value.value)
                    )

            elif isinstance(
                value,
                ast.FormattedValue,
            ):

                rendered = resolve_string(
                    value.value,
                    env,
                    set(visited),
                    depth + 1,
                )

                parts.append(
                    "{"
                    + rendered
                    + "}"
                )

        return "".join(parts)

    # -------------------------------------------------------------------------
    # Binary string concatenation
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
                set(visited),
                depth + 1,
            )

            right = resolve_string(
                node.right,
                env,
                set(visited),
                depth + 1,
            )

            return left + right

    # -------------------------------------------------------------------------
    # .format(...)
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
            and fn.endswith(".format")
        ):

            base = resolve_string(
                node.func.value,
                env,
                set(visited),
                depth + 1,
            )

            arguments = []

            for arg in node.args:

                arguments.append(
                    resolve_string(
                        arg,
                        env,
                        set(visited),
                        depth + 1,
                    )
                )

            if arguments:

                return (
                    base
                    + " {FORMAT:"
                    + ", ".join(arguments)
                    + "}"
                )

            return (
                base
                + " {FORMAT}"
            )

        # ---------------------------------------------------------------------
        # str(...)
        # ---------------------------------------------------------------------

        if fn == "str":

            if node.args:

                return resolve_string(
                    node.args[0],
                    env,
                    set(visited),
                    depth + 1,
                )

            return "{STR}"

        # ---------------------------------------------------------------------
        # SQL helper / builder calls
        # ---------------------------------------------------------------------

        if fn:

            return (
                "{CALL:"
                f"{fn}"
                "}"
            )

    # -------------------------------------------------------------------------
    # Tuple / list
    # -------------------------------------------------------------------------

    if isinstance(
        node,
        ast.Tuple,
    ):

        values = []

        for element in node.elts:

            values.append(
                resolve_string(
                    element,
                    env,
                    set(visited),
                    depth + 1,
                )
            )

        return (
            "("
            + ", ".join(values)
            + ")"
        )

    if isinstance(
        node,
        ast.List,
    ):

        values = []

        for element in node.elts:

            values.append(
                resolve_string(
                    element,
                    env,
                    set(visited),
                    depth + 1,
                )
            )

        return (
            "["
            + ", ".join(values)
            + "]"
        )

    return (
        "{"
        + type(node).__name__
        + "}"
    )


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


# =============================================================================
# DB WRITE PRIMITIVE
# =============================================================================

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

        self.calls = []
        self.returns = []
        self.assignments = []
        self.arguments = []
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

        self.write_primitives = []
        self.sql_assignments = []
        self.parameter_assignments = []
        self.target_refs = []
        self.function_calls = []
        self.return_nodes = []
        self.field_nodes = []

        self.dynamic_sql_candidates = []


# =============================================================================
# FUNCTION RANGE
# =============================================================================

def containing_function(
    analysis,
    line,
):

    best = None

    for info in (
        analysis.functions.values()
    ):

        start = line_no(
            info.node
        )

        end = end_line(
            info.node
        )

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

                if (
                    candidate_size
                    < current_size
                ):
                    best = info

    return best


# =============================================================================
# AST ANALYZER
# =============================================================================

class Analyzer(ast.NodeVisitor):

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

        self.generic_visit(node)

        info.local_env = dict(
            self.current_env
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

            if not isinstance(
                target,
                ast.Name,
            ):
                continue

            variable = target.id

            self.current_env[
                variable
            ] = node.value

            if self.current_function:

                self.current_function.assignments.append(
                    {
                        "variable": variable,
                        "line": line_no(node),
                        "node": node.value,
                    }
                )

            value = resolve_string(
                node.value,
                self.current_env,
            )

            lowered = variable.lower()

            # -----------------------------------------------------------------
            # SQL assignment detection
            # -----------------------------------------------------------------

            looks_like_sql_name = (
                lowered in SQL_NAMES
                or "sql" in lowered
                or "query" in lowered
                or "statement" in lowered
            )

            sql_like_value = (
                bool(
                    WRITE_RE.search(
                        value
                    )
                )
                or
                bool(
                    SELECT_RE.search(
                        value
                    )
                )
                or
                bool(
                    TARGET_RE.search(
                        value
                    )
                )
            )

            if (
                looks_like_sql_name
                or sql_like_value
            ):

                record = {
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
                    "dynamic": (
                        "{VAR:" in value
                        or "{ATTR:" in value
                        or "{CALL:" in value
                        or "{FORMAT" in value
                        or "{RESOLVE_" in value
                    ),
                }

                self.analysis.sql_assignments.append(
                    record
                )

                if record["dynamic"]:

                    self.analysis.dynamic_sql_candidates.append(
                        record
                    )

            # -----------------------------------------------------------------
            # Parameter / risk assignment
            # -----------------------------------------------------------------

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
                        "value": clean(value),
                    }
                )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # AUGMENTED ASSIGNMENT
    # -------------------------------------------------------------------------

    def visit_AnnAssign(
        self,
        node,
    ):

        if isinstance(
            node.target,
            ast.Name,
        ) and node.value is not None:

            self.current_env[
                node.target.id
            ] = node.value

        self.generic_visit(node)

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
                    "keywords": node.keywords,
                    "node": node,
                }
            )

        # ---------------------------------------------------------------------
        # DB execution primitive
        # ---------------------------------------------------------------------

        if is_db_write_primitive(node):

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
                "dynamic": (
                    "{VAR:" in sql
                    or "{ATTR:" in sql
                    or "{CALL:" in sql
                    or "{FORMAT" in sql
                    or "{RESOLVE_" in sql
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

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # RETURN
    # -------------------------------------------------------------------------

    def visit_Return(
        self,
        node,
    ):

        value = resolve_string(
            node.value,
            self.current_env,
        )

        record = {
            "path": self.analysis.path,
            "category": self.analysis.category,
            "line": line_no(node),
            "function": (
                self.current_function.name
                if self.current_function
                else "<module>"
            ),
            "node": node,
            "value": value,
        }

        self.analysis.return_nodes.append(
            record
        )

        if self.current_function:

            self.current_function.returns.append(
                node
            )

        self.generic_visit(node)


# =============================================================================
# FILE ANALYSIS
# =============================================================================

def analyze_file(path):

    source = read_source(
        path
    )

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

    return analyses, failures


# =============================================================================
# GLOBAL FUNCTION INDEX
# =============================================================================

def build_function_index(
    analyses,
):

    index = defaultdict(list)

    for analysis in analyses:

        for name, info in (
            analysis.functions.items()
        ):

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
                    "called": called,
                }
            )

    return callers


# =============================================================================
# PARAM DESCRIPTION
# =============================================================================

def describe_param_node(
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

            text = literal_string(
                key
            )

            if text:
                keys.append(
                    text
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

    if isinstance(
        node,
        ast.Attribute,
    ):

        return {
            "kind": "ATTRIBUTE",
            "value": dotted_name(
                node
            ),
        }

    return {
        "kind": type(node).__name__,
        "value": "",
    }


# =============================================================================
# TARGET WRITE CANDIDATES
# =============================================================================

def collect_actual_write_candidates(
    analyses,
):

    candidates = []

    for analysis in analyses:

        for primitive in (
            analysis.write_primitives
        ):

            if not primitive["is_write"]:
                continue

            if not primitive["target"]:
                continue

            candidate = dict(
                primitive
            )

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

            if primitive.get(
                "dynamic"
            ):

                score += 20
                reasons.append(
                    "DYNAMIC_SQL_RESOLVED"
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
# INDIRECT / DYNAMIC WRITE CANDIDATES
# =============================================================================

def collect_dynamic_write_candidates(
    analyses,
):

    results = []

    for analysis in analyses:

        for primitive in (
            analysis.write_primitives
        ):

            if not primitive.get(
                "dynamic"
            ):
                continue

            results.append(
                primitive
            )

    return results


# =============================================================================
# SELECT CONSUMERS
# =============================================================================

def collect_select_consumers(
    analyses,
):

    result = []

    for analysis in analyses:

        for primitive in (
            analysis.write_primitives
        ):

            sql = primitive["sql"]

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
                node
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

            self.generic_visit(node)

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

            self.generic_visit(node)

    for analysis in analyses:

        Visitor(
            analysis
        ).visit(
            analysis.tree
        )

    return results


# =============================================================================
# RETURN PRODUCER MAP
# =============================================================================

def build_return_map(
    analyses,
):

    result = defaultdict(list)

    for analysis in analyses:

        for record in (
            analysis.return_nodes
        ):

            result[
                record["function"]
            ].append(
                record
            )

    return result


# =============================================================================
# INDIRECT SQL REPORT
# =============================================================================

def print_dynamic_sql_report(
    analyses,
):

    separator()

    print(
        "9) INDIRECT / DYNAMIC SQL RESOLUTION"
    )

    separator()

    records = []

    for analysis in analyses:

        for item in (
            analysis.dynamic_sql_candidates
        ):

            records.append(
                item
            )

    print(
        "DYNAMIC SQL CANDIDATES : "
        f"{len(records)}"
    )

    if not records:

        print(
            "NONE"
        )

        return

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
            f"VARIABLE : "
            f"{item['variable']}"
        )

        print(
            f"OPERATION : "
            f"{item['operation']}"
        )

        print(
            f"TARGET : "
            f"{item['target']}"
        )

        print(
            f"SQL : "
            f"{item['sql']}"
        )


# =============================================================================
# ACTUAL WRITE REPORT
# =============================================================================

def print_actual_writes(
    candidates,
    analyses,
):

    separator()

    print(
        "3) ACTUAL risk_decisions WRITE CANDIDATES"
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
            "used as discovery root."
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
            f"DYNAMIC   : "
            f"{item.get('dynamic', False)}"
        )

        print(
            f"SQL       : "
            f"{item['sql']}"
        )

        print(
            "REASONS   : "
            + ", ".join(
                item["reasons"]
            )
        )

        analysis = next(
            (
                a
                for a in analyses
                if a.path
                == item["path"]
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
# SELECT CONSUMER REPORT
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
        "4) risk_decisions SELECT CONSUMERS"
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
# BACKWARD CHAIN
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

        print(
            f"  DYNAMIC   : "
            f"{candidate.get('dynamic', False)}"
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

                print(
                    f"    CALLED : "
                    f"{record['called']}"
                )


# =============================================================================
# SQL RESOLUTION REPORT
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

        for item in (
            analysis.sql_assignments
        ):

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
            f"DYNAMIC   : "
            f"{item.get('dynamic', False)}"
        )

        print(
            f"SQL       : "
            f"{item['sql']}"
        )


# =============================================================================
# OBJECT CONTEXT
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

        joined = " ".join(
            fields
        )

        if (
            "risk" in joined
            or "decision" in joined
            or "snapshot_id" in fields
            or "asset" in fields
            or "status" in fields
            or "reason" in fields
        ):

            relevant.append(
                item
            )

    print(
        "RISK-RELEVANT OBJECT CONTEXT : "
        f"{len(relevant)}"
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
# FUNCTION RETURN REPORT
# =============================================================================

def print_return_resolution(
    analyses,
):

    separator()

    print(
        "8) FUNCTION RETURN / INDIRECT SQL FLOW"
    )

    separator()

    records = []

    for analysis in analyses:

        for record in (
            analysis.return_nodes
        ):

            value = record["value"]

            if (
                WRITE_RE.search(value)
                or TARGET_RE.search(value)
                or "{VAR:" in value
                or "{CALL:" in value
                or "{FORMAT" in value
            ):

                records.append(
                    record
                )

    print(
        "INDIRECT RETURN CANDIDATES : "
        f"{len(records)}"
    )

    if not records:

        print(
            "NONE"
        )

        return

    for record in records:

        print()

        print(
            f"{record['category']} :: "
            f"{record['path']} :: "
            f"LINE {record['line']}"
        )

        print(
            f"FUNCTION : "
            f"{record['function']}"
        )

        print(
            f"RETURN   : "
            f"{clean(record['value'])}"
        )


# =============================================================================
# FINAL PRODUCER STATUS
# =============================================================================

def print_final_status(
    candidates,
    dynamic_candidates,
):

    separator()

    print(
        "10) FINAL PRODUCER STATUS"
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
        f"INDIRECT/DYNAMIC WRITES  : "
        f"{len(dynamic_candidates)}"
    )

    print()

    if production:

        best = production[0]

        print(
            "RESULT : PRODUCTION "
            "risk_decisions WRITE "
            "CANDIDATE FOUND"
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
            "RESULT : risk_decisions WRITE "
            "FOUND OUTSIDE PRODUCTION"
        )

        print(
            "PRODUCER STATUS : "
            "PRODUCTION PRODUCER NOT FOUND"
        )

    elif dynamic_candidates:

        print(
            "RESULT : INDIRECT/DYNAMIC "
            "risk_decisions WRITE SIGNAL "
            "FOUND BUT TARGET NOT FULLY "
            "RESOLVED"
        )

        print(
            "PRODUCER STATUS : "
            "PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : CALL-RETURN / "
            "SQL-BUILDER PROPAGATION"
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
            "NEXT TARGET : DB WRAPPER / "
            "INDIRECT EXECUTOR / "
            "DYNAMIC SQL CONSTRUCTION"
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
        "MODE        : READ ONLY"
    )

    print(
        f"ROOT        : {ROOT}"
    )

    print(
        f"TARGET      : {TARGET_TABLE}"
    )

    print(
        "ROOT METHOD : DB WRITE PRIMITIVE"
    )

    print(
        "CHAIN       : "
        "WRITE → SQL → TARGET → PARAMS → "
        "PRODUCER → CALLER"
    )

    print()

    print(
        "FOCUS       : "
        "INDIRECT / DYNAMIC WRITER RESOLUTION"
    )

    print(
        "RESOLVER    : "
        "CYCLE-SAFE / BOUNDED"
    )

    print()

    print(
        "IMPORTANT   : SELECT IS NOT A PRODUCER"
    )

    print(
        "IMPORTANT   : RISK NAME SEARCH IS NOT "
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

    dynamic_candidates = (
        collect_dynamic_write_candidates(
            analyses
        )
    )

    # -------------------------------------------------------------------------
    # 1
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # 2
    # -------------------------------------------------------------------------

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

        for item in (
            analysis.write_primitives
        ):

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

    # -------------------------------------------------------------------------
    # 3
    # -------------------------------------------------------------------------

    print_actual_writes(
        candidates,
        analyses,
    )

    # -------------------------------------------------------------------------
    # 4
    # -------------------------------------------------------------------------

    print_select_consumers(
        analyses
    )

    # -------------------------------------------------------------------------
    # 5
    # -------------------------------------------------------------------------

    print_backward_chains(
        candidates,
        analyses,
        function_index,
        callers,
    )

    # -------------------------------------------------------------------------
    # 6
    # -------------------------------------------------------------------------

    print_sql_resolution(
        analyses
    )

    # -------------------------------------------------------------------------
    # 7
    # -------------------------------------------------------------------------

    print_object_context(
        analyses
    )

    # -------------------------------------------------------------------------
    # 8
    # -------------------------------------------------------------------------

    print_return_resolution(
        analyses
    )

    # -------------------------------------------------------------------------
    # 9
    # -------------------------------------------------------------------------

    print_dynamic_sql_report(
        analyses
    )

    # -------------------------------------------------------------------------
    # 10
    # -------------------------------------------------------------------------

    print_final_status(
        candidates,
        dynamic_candidates,
    )

    # -------------------------------------------------------------------------
    # SAFETY
    # -------------------------------------------------------------------------

    print_safety()

    separator()

    print(
        "END — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.4"
    )

    separator()


if __name__ == "__main__":
    main()