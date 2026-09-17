
# -*- coding: utf-8 -*-

"""
ARUNDA — RISK_v0.1 ACTUAL DB WRITE BACKWARD CHAIN FORENSIC v2.5

OBJECTIVE
---------
Resolve INDIRECT / DYNAMIC DB WRITE paths targeting:

    risk_decisions

Backward chain:

    DB WRITE PRIMITIVE
        ↓
    SQL EXPRESSION
        ↓
    TARGET TABLE
        ↓
    PARAMS / OBJECT
        ↓
    PRODUCER FUNCTION
        ↓
    CALLER
        ↓
    CALL-RETURN PROPAGATION
        ↓
    SQL BUILDER PROPAGATION

IMPORTANT
---------
STATIC FORENSIC ANALYSIS ONLY.

No:
    - production imports
    - production execution
    - database connection
    - database reads
    - database writes
    - network
    - orders
    - trades

v2.5 PURPOSE
------------
v2.4 identified many INDIRECT/DYNAMIC signals.

v2.5 DOES NOT treat every unknown Call as a writer.

It distinguishes:

    TRUE_DYNAMIC_WRITE
    SQL_BUILDER
    CALL_RETURN_PROPAGATION
    NON_SQL_DYNAMIC_CALL
    FALSE_POSITIVE

The discovery root remains the DB execution primitive.

SELECT is never a producer.

Risk variable names are never the discovery root.
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

MAX_CALL_DEPTH = 12
MAX_RESOLVE_DEPTH = 30

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

SELECT_RE = re.compile(r"\bSELECT\b", re.IGNORECASE)

DELETE_RE = re.compile(r"\bDELETE\b", re.IGNORECASE)

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

SQL_TOKEN_RE = re.compile(
    r"""
    \b(
        INSERT
        |
        UPDATE
        |
        REPLACE
        |
        UPSERT
        |
        SELECT
        |
        DELETE
    )\b
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


def source_window(lines, line, radius=4):

    if not lines or line <= 0:
        return ""

    start = max(1, line - radius)
    end = min(len(lines), line + radius)

    result = []

    for number in range(start, end + 1):

        marker = ">>>" if number == line else "   "

        result.append(
            f"{marker} {number:5d} | {lines[number - 1].rstrip()}"
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
# AST STRING / VALUE RESOLUTION
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

    # Python 3.13-safe:
    # DO NOT use ast.Str because it triggers deprecation machinery.

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


def contains_sql_token(text):

    if not text:
        return False

    return bool(
        SQL_TOKEN_RE.search(text)
    )


def looks_like_sql(text):

    if not text:
        return False

    text_upper = text.upper()

    if contains_sql_token(text):
        return True

    sql_fragments = (
        " INTO ",
        " FROM ",
        " WHERE ",
        " SET ",
        " VALUES ",
        " UPDATE ",
        " INSERT ",
        " SELECT ",
        " REPLACE ",
        " UPSERT ",
        " RISK_DECISIONS",
    )

    return any(
        fragment in f" {text_upper} "
        for fragment in sql_fragments
    )


def resolve_string(
    node,
    env=None,
    depth=0,
    active=None,
):

    if node is None:
        return ""

    if env is None:
        env = {}

    if active is None:
        active = set()

    if depth >= MAX_RESOLVE_DEPTH:
        return "{RESOLUTION_DEPTH_LIMIT}"

    # -------------------------------------------------------------------------
    # Constant string
    # -------------------------------------------------------------------------

    literal = literal_string(node)

    if literal is not None:
        return literal

    # -------------------------------------------------------------------------
    # Name
    # -------------------------------------------------------------------------

    if isinstance(node, ast.Name):

        if node.id in active:
            return "{RECURSIVE_REF:" + node.id + "}"

        if node.id in env:

            next_active = set(active)
            next_active.add(node.id)

            return resolve_string(
                env[node.id],
                env,
                depth + 1,
                next_active,
            )

        return "{VAR:" + node.id + "}"

    # -------------------------------------------------------------------------
    # f-string
    # -------------------------------------------------------------------------

    if isinstance(node, ast.JoinedStr):

        parts = []

        for value in node.values:

            if isinstance(value, ast.Constant):

                parts.append(
                    str(value.value)
                )

            elif isinstance(value, ast.FormattedValue):

                name = dotted_name(
                    value.value
                )

                if name:
                    parts.append(
                        "{"
                        + name
                        + "}"
                    )

                else:
                    parts.append(
                        "{DYNAMIC}"
                    )

        return "".join(parts)

    # -------------------------------------------------------------------------
    # String concatenation
    # -------------------------------------------------------------------------

    if isinstance(node, ast.BinOp):

        if isinstance(node.op, ast.Add):

            left = resolve_string(
                node.left,
                env,
                depth + 1,
                active,
            )

            right = resolve_string(
                node.right,
                env,
                depth + 1,
                active,
            )

            return left + right

    # -------------------------------------------------------------------------
    # "%" formatting
    # -------------------------------------------------------------------------

    if isinstance(node, ast.BinOp):

        if isinstance(node.op, ast.Mod):

            left = resolve_string(
                node.left,
                env,
                depth + 1,
                active,
            )

            return left + " {FORMAT_%}"

    # -------------------------------------------------------------------------
    # .format(...)
    # -------------------------------------------------------------------------

    if isinstance(node, ast.Call):

        fn = dotted_name(node.func)

        if fn and fn.endswith(".format"):

            base = resolve_string(
                node.func.value,
                env,
                depth + 1,
                active,
            )

            return base + " {FORMAT}"

        # ---------------------------------------------------------------------
        # SQL builder function call.
        #
        # IMPORTANT:
        # Unknown calls are represented as calls.
        # They are NOT automatically classified as DB writers.
        # ---------------------------------------------------------------------

        if fn:

            return (
                "{CALL:"
                + fn
                + "}"
            )

    return ""


def resolve_any(
    node,
    env=None,
    depth=0,
    active=None,
):

    if node is None:
        return ""

    if env is None:
        env = {}

    if active is None:
        active = set()

    if depth >= MAX_RESOLVE_DEPTH:
        return "{RESOLUTION_DEPTH_LIMIT}"

    if isinstance(node, ast.Name):

        if node.id in active:
            return "{RECURSIVE_REF:" + node.id + "}"

        if node.id in env:

            next_active = set(active)
            next_active.add(node.id)

            return resolve_any(
                env[node.id],
                env,
                depth + 1,
                next_active,
            )

    text = resolve_string(
        node,
        env,
        depth,
        active,
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

def is_db_execution_primitive(node):

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

    def __init__(self, analysis, node):

        self.analysis = analysis
        self.node = node

        self.name = node.name

        self.calls = []
        self.returns = []
        self.assignments = []
        self.arguments = []
        self.write_primitives = []

        self.sql_builder_returns = []
        self.call_returns = []


class FileAnalysis:

    def __init__(self, path, source, tree):

        self.path = path
        self.source = source
        self.lines = source.splitlines()
        self.tree = tree

        self.category = classify_file(path)

        self.functions = {}

        self.write_primitives = []
        self.sql_assignments = []
        self.parameter_assignments = []
        self.target_refs = []
        self.function_calls = []
        self.return_nodes = []
        self.field_nodes = []

        self.call_return_nodes = []
        self.sql_builder_nodes = []


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
                    end
                    - start
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

        self.analysis.functions[node.name] = info

        for arg in node.args.args:

            info.arguments.append(
                arg.arg
            )

        self.function_stack.append(info)
        self.environment_stack.append({})

        self.generic_visit(node)

        self.environment_stack.pop()
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):

        self.visit_FunctionDef(node)

    # -------------------------------------------------------------------------
    # ASSIGNMENT
    # -------------------------------------------------------------------------

    def visit_Assign(self, node):

        for target in node.targets:

            if not isinstance(target, ast.Name):
                continue

            variable = target.id

            self.current_env[
                variable
            ] = node.value

            value = resolve_any(
                node.value,
                self.current_env,
            )

            lowered = variable.lower()

            # -------------------------------------------------------------
            # SQL variable
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
            # Parameters / risk objects
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
                        "value": clean(value),
                    }
                )

            # -------------------------------------------------------------
            # SQL-builder candidate
            # -------------------------------------------------------------

            if (
                isinstance(node.value, ast.Call)
                or isinstance(node.value, ast.BinOp)
                or isinstance(node.value, ast.JoinedStr)
            ):

                if looks_like_sql(value):

                    self.analysis.sql_builder_nodes.append(
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
                            "expression": clean(value),
                        }
                    )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    def visit_Call(self, node):

        called = dotted_name(node.func)

        if called:

            caller_name = (
                self.current_function.name
                if self.current_function
                else "<module>"
            )

            record = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": caller_name,
                "called": called,
                "args": node.args,
                "keywords": node.keywords,
                "node": node,
            }

            self.analysis.function_calls.append(
                record
            )

            if self.current_function:

                self.current_function.calls.append(
                    record
                )

        # ---------------------------------------------------------------------
        # DB EXECUTION PRIMITIVE
        # ---------------------------------------------------------------------

        if is_db_execution_primitive(node):

            sql_node = (
                node.args[0]
                if node.args
                else None
            )

            sql = resolve_any(
                sql_node,
                self.current_env,
            )

            operation = sql_operation(sql)

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
                "target": targets_risk_decisions(sql),
                "is_write": is_write_operation(sql),
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

    def visit_Return(self, node):

        value = resolve_any(
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
            "value": clean(value),
            "value_node": node.value,
        }

        self.analysis.return_nodes.append(
            record
        )

        # -------------------------------------------------------------
        # CALL RETURN
        # -------------------------------------------------------------

        if isinstance(node.value, ast.Call):

            call_name = dotted_name(
                node.value.func
            )

            record["return_kind"] = "CALL"
            record["called"] = call_name

            self.analysis.call_return_nodes.append(
                record
            )

            if self.current_function:

                self.current_function.call_returns.append(
                    record
                )

        # -------------------------------------------------------------
        # SQL-builder return
        # -------------------------------------------------------------

        if looks_like_sql(value):

            self.analysis.sql_builder_nodes.append(
                {
                    "path": self.analysis.path,
                    "category": self.analysis.category,
                    "line": line_no(node),
                    "function": (
                        self.current_function.name
                        if self.current_function
                        else "<module>"
                    ),
                    "variable": "<return>",
                    "expression": clean(value),
                }
            )

            if self.current_function:

                self.current_function.sql_builder_returns.append(
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

    return analysis, None


# =============================================================================
# REPOSITORY INDEX
# =============================================================================

def build_repository_index(files):

    analyses = []
    failures = []

    for path in files:

        analysis, error = analyze_file(path)

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

            callers[short].append(
                {
                    "path": analysis.path,
                    "category": analysis.category,
                    "line": call["line"],
                    "caller": caller_name,
                    "called": called,
                    "args": call["args"],
                    "keywords": call["keywords"],
                    "node": call["node"],
                }
            )

    return callers


# =============================================================================
# FUNCTION RETURN INDEX
# =============================================================================

def build_return_index(analyses):

    returns = defaultdict(list)

    for analysis in analyses:

        for record in analysis.return_nodes:

            function_name = record[
                "function"
            ]

            if function_name == "<module>":
                continue

            returns[function_name].append(
                {
                    "analysis": analysis,
                    "record": record,
                }
            )

    return returns


# =============================================================================
# SQL BUILDER INDEX
# =============================================================================

def build_sql_builder_index(analyses):

    builders = []

    for analysis in analyses:

        for item in analysis.sql_builder_nodes:

            builders.append(
                item
            )

    return builders


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

    if isinstance(node, ast.Name):

        return {
            "kind": "VARIABLE",
            "value": node.id,
        }

    if isinstance(node, ast.Dict):

        keys = []

        for key in node.keys:

            value = literal_string(key)

            if value is not None:
                keys.append(value)

        return {
            "kind": "DICT",
            "value": keys,
        }

    if isinstance(node, ast.Tuple):

        return {
            "kind": "TUPLE",
            "value": len(node.elts),
        }

    if isinstance(node, ast.List):

        return {
            "kind": "LIST",
            "value": len(node.elts),
        }

    if isinstance(node, ast.Call):

        return {
            "kind": "CALL",
            "value": dotted_name(node.func),
        }

    if isinstance(node, ast.Constant):

        return {
            "kind": "CONSTANT",
            "value": repr(node.value),
        }

    return {
        "kind": type(node).__name__,
        "value": "",
    }


# =============================================================================
# PARAM FLOW
# =============================================================================

def extract_param_flow(candidate):

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
# DIRECT TARGET WRITES
# =============================================================================

def collect_actual_write_candidates(
    analyses,
):

    candidates = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            if not primitive["is_write"]:
                continue

            if not primitive["target"]:
                continue

            candidate = dict(
                primitive
            )

            score = 0
            reasons = []

            if analysis.category == "PRODUCTION":

                score += 50
                reasons.append(
                    "PRODUCTION"
                )

            elif analysis.category == "FORENSIC":

                score += 10
                reasons.append(
                    "FORENSIC"
                )

            elif analysis.category == "BACKUP":

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

            candidate["score"] = score
            candidate["reasons"] = reasons

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
# SELECT CONSUMERS
# =============================================================================

def collect_select_consumers(
    analyses,
):

    result = []

    for analysis in analyses:

        for primitive in analysis.write_primitives:

            sql = primitive["sql"]

            if (
                primitive["operation"] == "SELECT"
                and targets_risk_decisions(sql)
            ):

                result.append(
                    primitive
                )

    return result


# =============================================================================
# DYNAMIC CLASSIFICATION
# =============================================================================

def classify_dynamic_expression(
    expression,
):

    if not expression:
        return "UNKNOWN"

    # -------------------------------------------------------------
    # Strong non-SQL utility calls.
    # -------------------------------------------------------------

    utility_suffixes = (
        ".upper",
        ".lower",
        ".join",
        ".replace",
        ".strip",
        ".split",
        ".format",
        ".read_text",
        ".read_source",
        ".decode",
        ".encode",
        ".startswith",
        ".endswith",
        ".get",
        ".items",
        ".keys",
        ".values",
    )

    lowered = expression.lower()

    if (
        lowered.startswith("{call:")
        and any(
            lowered.endswith(suffix + "}")
            for suffix in utility_suffixes
        )
    ):

        return "NON_SQL_DYNAMIC_CALL"

    if lowered.startswith(
        "{call:"
    ):

        return "CALL_RETURN_PROPAGATION"

    if looks_like_sql(expression):

        return "SQL_BUILDER"

    return "UNKNOWN"


def collect_indirect_dynamic_signals(
    analyses,
):

    records = []

    for analysis in analyses:

        # -------------------------------------------------------------
        # SQL assignments
        # -------------------------------------------------------------

        for item in analysis.sql_assignments:

            sql = item["sql"]

            if not sql:
                continue

            if item["operation"] == "UNKNOWN":

                if "{CALL:" in sql:

                    classification = (
                        classify_dynamic_expression(
                            sql
                        )
                    )

                    records.append(
                        {
                            **item,
                            "classification":
                                classification,
                        }
                    )

        # -------------------------------------------------------------
        # SQL builder nodes
        # -------------------------------------------------------------

        for item in analysis.sql_builder_nodes:

            expression = item[
                "expression"
            ]

            if looks_like_sql(
                expression
            ):

                records.append(
                    {
                        **item,
                        "classification":
                            "SQL_BUILDER",
                    }
                )

    # Deduplicate
    unique = []
    seen = set()

    for item in records:

        key = (
            str(item.get("path")),
            item.get("line"),
            item.get("function"),
            item.get("variable"),
            item.get("classification"),
            item.get("expression", item.get("sql")),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


# =============================================================================
# CALL-RETURN PROPAGATION
# =============================================================================

def resolve_function_return_sql(
    function_name,
    function_index,
    return_index,
    visited=None,
    depth=0,
):

    if visited is None:
        visited = set()

    if depth >= MAX_CALL_DEPTH:
        return []

    if function_name is None:
        return []

    key = (
        function_name,
        depth,
    )

    if key in visited:
        return []

    visited.add(key)

    results = []

    return_records = return_index.get(
        function_name,
        [],
    )

    for item in return_records:

        analysis = item["analysis"]
        record = item["record"]

        value = record["value"]

        # -------------------------------------------------------------
        # Direct SQL return
        # -------------------------------------------------------------

        if looks_like_sql(value):

            results.append(
                {
                    "classification":
                        "SQL_BUILDER",
                    "function":
                        function_name,
                    "path":
                        analysis.path,
                    "line":
                        record["line"],
                    "value":
                        value,
                }
            )

        # -------------------------------------------------------------
        # Return another function call
        # -------------------------------------------------------------

        if record.get(
            "return_kind"
        ) == "CALL":

            called = record.get(
                "called"
            )

            if called:

                short = called.split(
                    "."
                )[-1]

                nested = (
                    resolve_function_return_sql(
                        short,
                        function_index,
                        return_index,
                        visited,
                        depth + 1,
                    )
                )

                results.extend(
                    nested
                )

    return results


def collect_call_return_propagation(
    analyses,
    function_index,
    return_index,
):

    records = []

    for analysis in analyses:

        for call in analysis.function_calls:

            called = call["called"]
            short = called.split(".")[-1]

            if short not in function_index:
                continue

            returned_sql = (
                resolve_function_return_sql(
                    short,
                    function_index,
                    return_index,
                )
            )

            if not returned_sql:
                continue

            caller = call[
                "function"
            ]

            records.append(
                {
                    "path":
                        analysis.path,
                    "category":
                        analysis.category,
                    "line":
                        call["line"],
                    "caller":
                        caller,
                    "called":
                        called,
                    "classification":
                        "CALL_RETURN_PROPAGATION",
                    "resolved_returns":
                        returned_sql,
                }
            )

    return records


# =============================================================================
# TARGET PROPAGATION
# =============================================================================

def collect_resolved_indirect_targets(
    analyses,
    function_index,
    return_index,
):

    records = []

    # -------------------------------------------------------------
    # Function returns
    # -------------------------------------------------------------

    for analysis in analyses:

        for info in analysis.functions.values():

            returned = (
                resolve_function_return_sql(
                    info.name,
                    function_index,
                    return_index,
                )
            )

            for item in returned:

                value = item["value"]

                if (
                    targets_risk_decisions(
                        value
                    )
                    and is_write_operation(
                        value
                    )
                ):

                    records.append(
                        {
                            "classification":
                                "TRUE_DYNAMIC_WRITE",
                            "path":
                                item["path"],
                            "category":
                                analysis.category,
                            "line":
                                item["line"],
                            "function":
                                info.name,
                            "sql":
                                value,
                            "reason":
                                "FUNCTION_RETURN_RESOLVES_TO_TARGET_WRITE",
                        }
                    )

    # -------------------------------------------------------------
    # Calls receiving resolved SQL
    # -------------------------------------------------------------

    for analysis in analyses:

        for call in analysis.function_calls:

            called = call["called"]
            short = called.split(".")[-1]

            if short not in function_index:
                continue

            returned = (
                resolve_function_return_sql(
                    short,
                    function_index,
                    return_index,
                )
            )

            for item in returned:

                value = item["value"]

                if (
                    targets_risk_decisions(value)
                    and is_write_operation(value)
                ):

                    records.append(
                        {
                            "classification":
                                "TRUE_DYNAMIC_WRITE",
                            "path":
                                analysis.path,
                            "category":
                                analysis.category,
                            "line":
                                call["line"],
                            "function":
                                call["function"],
                            "called":
                                called,
                            "sql":
                                value,
                            "reason":
                                "CALL_RETURN_PROPAGATES_TARGET_WRITE",
                        }
                    )

    # Deduplicate

    unique = []
    seen = set()

    for item in records:

        key = (
            str(item.get("path")),
            item.get("line"),
            item.get("function"),
            item.get("called"),
            item.get("sql"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


# =============================================================================
# OBJECT / DICT FORENSICS
# =============================================================================

def collect_dict_fields(
    analyses,
):

    results = []

    class Visitor(ast.NodeVisitor):

        def __init__(self, analysis):

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

            self.visit_FunctionDef(node)

        def visit_Dict(
            self,
            node,
        ):

            fields = []

            for key in node.keys:

                text = literal_string(
                    key
                )

                if text is not None:
                    fields.append(text)

            if fields:

                results.append(
                    {
                        "path":
                            self.analysis.path,
                        "category":
                            self.analysis.category,
                        "line":
                            line_no(node),
                        "function": (
                            self.function_stack[-1]
                            if self.function_stack
                            else "<module>"
                        ),
                        "fields":
                            fields,
                    }
                )

            self.generic_visit(node)

    for analysis in analyses:

        Visitor(analysis).visit(
            analysis.tree
        )

    return results


# =============================================================================
# REPORT
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
        f"TARGET WRITE CANDIDATES : {len(candidates)}"
    )

    if not candidates:

        print()
        print(
            "NO STATIC risk_decisions WRITE FOUND."
        )

        print(
            "SELECT consumers were excluded."
        )

        print(
            "Risk-variable names were NOT used "
            "as the discovery root."
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
            f"SCORE     : {item['score']}"
        )

        print(
            f"TYPE      : {item['category']}"
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
            f"METHOD    : {item['method']}"
        )

        print(
            f"OPERATION : {item['operation']}"
        )

        print(
            f"TARGET    : {item['target']}"
        )

        print(
            f"SQL       : {item['sql']}"
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
        f"SELECT CONSUMERS : {len(consumers)}"
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
# BACKWARD CHAIN REPORT
# =============================================================================

def print_backward_chains(
    candidates,
    callers,
):

    separator()

    print(
        "5) DIRECT BACKWARD CHAIN"
    )

    separator()

    if not candidates:

        print(
            "NO DIRECT WRITE CHAIN AVAILABLE."
        )

        return

    for index, candidate in enumerate(
        candidates,
        1,
    ):

        print()
        print(
            "#" * 110
        )

        print(
            f"BACKWARD TRACE #{index}"
        )

        print()

        print(
            "DB WRITE PRIMITIVE"
        )

        print(
            f"  METHOD   : {candidate['method']}"
        )

        print(
            f"  FILE     : {candidate['path']}"
        )

        print(
            f"  LINE     : {candidate['line']}"
        )

        print(
            f"  FUNCTION : {candidate['function']}"
        )

        print()

        print(
            "↓ SQL EXPRESSION"
        )

        print(
            f"  SQL       : {candidate['sql']}"
        )

        print(
            f"  OPERATION : {candidate['operation']}"
        )

        print()

        print(
            "↓ TARGET TABLE"
        )

        print(
            f"  TARGET : {TARGET_TABLE}"
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
                    f"    KIND  : {param['kind']}"
                )

                print(
                    f"    VALUE : {param['value']}"
                )

        print()

        print(
            "↓ PRODUCER FUNCTION"
        )

        print(
            f"  FILE     : {candidate['path']}"
        )

        print(
            f"  FUNCTION : {candidate['function']}"
        )

        print(
            f"  LINE     : {candidate['line']}"
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
                    f"    LINE   : {record['line']}"
                )

                print(
                    f"    CALLER : {record['caller']}"
                )


# =============================================================================
# INDIRECT REPORT
# =============================================================================

def print_indirect_report(
    analyses,
    function_index,
    return_index,
):

    separator()

    print(
        "6) INDIRECT / DYNAMIC RESOLUTION"
    )

    separator()

    signals = (
        collect_indirect_dynamic_signals(
            analyses
        )
    )

    propagation = (
        collect_call_return_propagation(
            analyses,
            function_index,
            return_index,
        )
    )

    resolved_targets = (
        collect_resolved_indirect_targets(
            analyses,
            function_index,
            return_index,
        )
    )

    true_dynamic = [
        item
        for item in resolved_targets
        if item["classification"]
        == "TRUE_DYNAMIC_WRITE"
    ]

    sql_builders = [
        item
        for item in signals
        if item.get("classification")
        == "SQL_BUILDER"
    ]

    call_returns = [
        item
        for item in propagation
        if item.get("classification")
        == "CALL_RETURN_PROPAGATION"
    ]

    non_sql = [
        item
        for item in signals
        if item.get("classification")
        == "NON_SQL_DYNAMIC_CALL"
    ]

    unknown = [
        item
        for item in signals
        if item.get("classification")
        == "UNKNOWN"
    ]

    print(
        f"INDIRECT/DYNAMIC SIGNALS : {len(signals)}"
    )

    print(
        f"TRUE DYNAMIC WRITES      : {len(true_dynamic)}"
    )

    print(
        f"SQL BUILDERS             : {len(sql_builders)}"
    )

    print(
        f"CALL-RETURN PROPAGATION  : {len(call_returns)}"
    )

    print(
        f"NON-SQL DYNAMIC CALLS    : {len(non_sql)}"
    )

    print(
        f"UNKNOWN                  : {len(unknown)}"
    )

    print()

    # -------------------------------------------------------------------------
    # TRUE DYNAMIC WRITES
    # -------------------------------------------------------------------------

    separator(
        "-",
        110,
    )

    print(
        "6A) TRUE DYNAMIC risk_decisions WRITES"
    )

    separator(
        "-",
        110,
    )

    if not true_dynamic:

        print(
            "NONE"
        )

    else:

        for index, item in enumerate(
            true_dynamic,
            1,
        ):

            print()

            print(
                f"DYNAMIC WRITE #{index}"
            )

            print(
                f"  CATEGORY : {item['category']}"
            )

            print(
                f"  FILE     : {item['path']}"
            )

            print(
                f"  LINE     : {item['line']}"
            )

            print(
                f"  FUNCTION : {item['function']}"
            )

            if item.get("called"):

                print(
                    f"  CALLED   : {item['called']}"
                )

            print(
                f"  SQL      : {item['sql']}"
            )

            print(
                f"  REASON   : {item['reason']}"
            )

    # -------------------------------------------------------------------------
    # SQL BUILDERS
    # -------------------------------------------------------------------------

    separator(
        "-",
        110,
    )

    print(
        "6B) SQL BUILDER CANDIDATES"
    )

    separator(
        "-",
        110,
    )

    if not sql_builders:

        print(
            "NONE"
        )

    else:

        for item in sql_builders[:300]:

            print()

            print(
                f"{item['category']} :: "
                f"{item['path']} :: "
                f"LINE {item['line']} :: "
                f"{item['function']}"
            )

            print(
                f"  VARIABLE   : "
                f"{item.get('variable', '')}"
            )

            print(
                f"  EXPRESSION : "
                f"{item.get('expression', item.get('sql', ''))}"
            )

    # -------------------------------------------------------------------------
    # CALL RETURN
    # -------------------------------------------------------------------------

    separator(
        "-",
        110,
    )

    print(
        "6C) CALL-RETURN PROPAGATION"
    )

    separator(
        "-",
        110,
    )

    if not call_returns:

        print(
            "NONE"
        )

    else:

        for item in call_returns[:300]:

            print()

            print(
                f"{item['category']} :: "
                f"{item['path']} :: "
                f"LINE {item['line']}"
            )

            print(
                f"  CALLER : {item['caller']}"
            )

            print(
                f"  CALLED : {item['called']}"
            )

            for returned in item[
                "resolved_returns"
            ]:

                print(
                    f"    RETURN :: "
                    f"{returned['classification']} :: "
                    f"{returned['value']}"
                )

    # -------------------------------------------------------------------------
    # NON SQL
    # -------------------------------------------------------------------------

    separator(
        "-",
        110,
    )

    print(
        "6D) NON-SQL DYNAMIC CALLS"
    )

    separator(
        "-",
        110,
    )

    if not non_sql:

        print(
            "NONE"
        )

    else:

        for item in non_sql[:200]:

            print()

            print(
                f"{item['category']} :: "
                f"{item['path']} :: "
                f"LINE {item['line']}"
            )

            print(
                f"  FUNCTION : {item['function']}"
            )

            print(
                f"  VARIABLE : {item.get('variable', '')}"
            )

            print(
                f"  VALUE    : {item.get('sql', '')}"
            )


# =============================================================================
# SQL VARIABLE REPORT
# =============================================================================

def print_sql_resolution(
    analyses,
):

    separator()

    print(
        "7) SQL EXPRESSION RESOLUTION"
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
        f"RESOLVED TARGET WRITE SQL VARIABLES : "
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
            f"FUNCTION  : {item['function']}"
        )

        print(
            f"VARIABLE  : {item['variable']}"
        )

        print(
            f"OPERATION : {item['operation']}"
        )

        print(
            f"SQL       : {item['sql']}"
        )


# =============================================================================
# OBJECT CONTEXT
# =============================================================================

def print_object_context(
    analyses,
):

    separator()

    print(
        "8) OBJECT / DICT CONTEXT"
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
        f"RISK-RELEVANT OBJECT CONTEXT : "
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
# FINAL STATUS
# =============================================================================

def print_final_status(
    candidates,
    analyses,
    function_index,
    return_index,
):

    separator()

    print(
        "9) FINAL PRODUCER STATUS"
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

    true_dynamic = (
        collect_resolved_indirect_targets(
            analyses,
            function_index,
            return_index,
        )
    )

    true_dynamic = [
        item
        for item in true_dynamic
        if item["classification"]
        == "TRUE_DYNAMIC_WRITE"
    ]

    print(
        f"DIRECT TARGET WRITE PRIMITIVES : "
        f"{len(candidates)}"
    )

    print(
        f"PRODUCTION DIRECT              : "
        f"{len(production)}"
    )

    print(
        f"FORENSIC DIRECT                : "
        f"{len(forensic)}"
    )

    print(
        f"BACKUP DIRECT                  : "
        f"{len(backup)}"
    )

    print(
        f"TRUE DYNAMIC TARGET WRITES     : "
        f"{len(true_dynamic)}"
    )

    print()

    if production:

        best = production[0]

        print(
            "RESULT : PRODUCTION "
            "risk_decisions WRITE PATH FOUND"
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
            "STATUS : DIRECT WRITE PATH IDENTIFIED."
        )

    elif true_dynamic:

        production_dynamic = [
            item
            for item in true_dynamic
            if item["category"]
            == "PRODUCTION"
        ]

        if production_dynamic:

            print(
                "RESULT : PRODUCTION "
                "INDIRECT/DYNAMIC risk_decisions "
                "WRITE PATH IDENTIFIED"
            )

            print(
                "PRODUCER STATUS : INDIRECT PATH RESOLVED"
            )

        else:

            print(
                "RESULT : risk_decisions INDIRECT "
                "WRITE PATH FOUND OUTSIDE PRODUCTION"
            )

            print(
                "PRODUCER STATUS : PRODUCTION DIRECT "
                "WRITER NOT IDENTIFIED"
            )

    elif any(
        analysis.sql_builder_nodes
        for analysis in analyses
    ):

        print(
            "RESULT : SQL BUILDER / "
            "CALL-RETURN PATHS EXIST"
        )

        print(
            "PRODUCER STATUS : TARGET NOT YET RESOLVED"
        )

        print(
            "NEXT TARGET : ARGUMENT-TO-PARAMETER "
            "DATAFLOW PROPAGATION"
        )

    else:

        print(
            "RESULT : NO STATIC OR RESOLVED "
            "risk_decisions WRITE FOUND"
        )

        print(
            "PRODUCER STATUS : NOT FOUND"
        )

        print(
            "NEXT TARGET : INDIRECT DB WRITER "
            "PROPAGATION"
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
        "BACKWARD CHAIN FORENSIC v2.5"
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
        "PRODUCER → CALLER → CALL-RETURN → "
        "SQL-BUILDER"
    )

    print()

    print(
        "IMPORTANT    : SELECT IS NOT A PRODUCER"
    )

    print(
        "IMPORTANT    : RISK NAME SEARCH IS NOT "
        "THE DISCOVERY ROOT"
    )

    print(
        "IMPORTANT    : UNKNOWN CALL != WRITE"
    )

    print()

    separator()

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

    callers = build_caller_index(
        analyses
    )

    return_index = build_return_index(
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
        callers,
    )

    print_indirect_report(
        analyses,
        function_index,
        return_index,
    )

    print_sql_resolution(
        analyses
    )

    print_object_context(
        analyses
    )

    print_final_status(
        candidates,
        analyses,
        function_index,
        return_index,
    )

    print_safety()

    separator()

    print(
        "END — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.5"
    )

    separator()


if __name__ == "__main__":
    main()

