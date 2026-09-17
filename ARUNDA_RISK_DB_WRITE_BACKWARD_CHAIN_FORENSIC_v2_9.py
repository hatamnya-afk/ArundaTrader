# -*- coding: utf-8 -*-

"""
ARUNDA — RISK_v0.1 ACTUAL DB WRITE BACKWARD CHAIN FORENSIC v4.0

PURPOSE
-------
Static forensic analysis of dynamic SQL write paths reaching:

    risk_decisions

v4.0 repairs
------------

1. Recursive symbolic string resolution
2. Global/module environment propagation into functions
3. Local environment resolution
4. Recursive f-string / FormattedValue resolution
5. Name -> assignment -> expression resolution
6. Attribute symbolic resolution
7. String concatenation resolution
8. .format(...) resolution
9. Direct execute(builder(...)) detection
10. Builder return-path propagation
11. Caller -> parameter -> builder propagation
12. Caller environment preservation
13. Reduced target false positives
14. Reduced SQL-builder false positives
15. Function-name collision resistance
16. Targeted backward propagation only
17. No global dataflow cross-product
18. Production / forensic separation
19. READ-ONLY source analysis

SAFETY
------

STATIC SOURCE ANALYSIS ONLY

NO production imports
NO production execution
NO database connection
NO database reads
NO database writes
NO SELECT execution
NO INSERT
NO UPDATE
NO DELETE
NO ALTER
NO CREATE
NO COMMIT
NO NETWORK
NO ORDER
NO TRADE
"""

import ast
import re
from pathlib import Path
from collections import defaultdict, deque


# =============================================================================
# CONFIG
# =============================================================================

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_TABLE = "risk_decisions"

MAX_PROPAGATION_DEPTH = 14
MAX_RESULTS_PER_SIGNAL = 250
MAX_GLOBAL_OUTPUT = 150


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
    "backups",
    "before",
    "pre",
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
        \bREPLACE\s+(?:INTO\s+)?["'`]?risk_decISIONS["'`]?
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


BUILDER_HINTS = {
    "build",
    "builder",
    "make",
    "generate",
    "compose",
    "construct",
    "render",
    "compile",
    "format",
    "insert",
    "update",
    "replace",
    "upsert",
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


def expression_names(node):
    result = []

    if node is None:
        return result

    class Visitor(ast.NodeVisitor):

        def visit_Name(self, n):
            result.append(n.id)

    Visitor().visit(node)

    return list(dict.fromkeys(result))


def node_contains_target(node):
    if node is None:
        return False

    text = safe_unparse(node)

    return TARGET_TABLE.lower() in text.lower()


def merge_environments(*environments):
    """
    Merge environments from broadest to narrowest scope.

    Later environments override earlier environments.
    """

    merged = {}

    for environment in environments:
        if environment:
            merged.update(environment)

    return merged


# =============================================================================
# FILE CLASSIFICATION
# =============================================================================

def classify_file(path):

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


def is_real_production(category):
    return category == "PRODUCTION"


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
# STATIC SYMBOLIC RESOLUTION
# =============================================================================

def resolve_string(
    node,
    env=None,
    visited=None,
    depth=0,
):
    """
    Resolve statically-known string expressions.

    Examples
    --------

    TARGET_TABLE = "risk_decisions"

    sql = f"UPDATE {TARGET_TABLE} SET x=?"

    resolves to:

        UPDATE risk_decisions SET x=?

    Also supports:

        sql = PREFIX + TARGET_TABLE + SUFFIX

        sql = "UPDATE {table}".format(
            table=TARGET_TABLE
        )

        sql = build_sql(TARGET_TABLE)
    """

    if node is None:
        return ""

    if env is None:
        env = {}

    if visited is None:
        visited = set()

    if depth > 50:
        return "{DEPTH_LIMIT}"

    node_id = id(node)

    if node_id in visited:
        return "{CYCLE}"

    visited.add(node_id)

    try:

        # -----------------------------------------------------------------
        # Literal
        # -----------------------------------------------------------------

        literal = literal_string(node)

        if literal is not None:
            return literal

        # -----------------------------------------------------------------
        # Name
        # -----------------------------------------------------------------

        if isinstance(node, ast.Name):

            if node.id in env:

                return resolve_string(
                    env[node.id],
                    env,
                    visited,
                    depth + 1,
                )

            return "{" + node.id + "}"

        # -----------------------------------------------------------------
        # Attribute
        # -----------------------------------------------------------------

        if isinstance(node, ast.Attribute):

            name = dotted_name(node)

            if name in env:

                return resolve_string(
                    env[name],
                    env,
                    visited,
                    depth + 1,
                )

            return "{" + (name or "ATTRIBUTE") + "}"

        # -----------------------------------------------------------------
        # f-string
        # -----------------------------------------------------------------

        if isinstance(node, ast.JoinedStr):

            parts = []

            for value in node.values:

                if isinstance(
                    value,
                    ast.Constant,
                ):

                    parts.append(
                        str(value.value)
                    )

                    continue

                if isinstance(
                    value,
                    ast.FormattedValue,
                ):

                    resolved_value = resolve_string(
                        value.value,
                        env,
                        visited.copy(),
                        depth + 1,
                    )

                    if resolved_value:
                        parts.append(
                            resolved_value
                        )
                    else:
                        parts.append(
                            "{DYNAMIC}"
                        )

            return "".join(parts)

        # -----------------------------------------------------------------
        # Binary string concatenation
        # -----------------------------------------------------------------

        if isinstance(node, ast.BinOp):

            if isinstance(
                node.op,
                ast.Add,
            ):

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

        # -----------------------------------------------------------------
        # .format(...)
        # -----------------------------------------------------------------

        if isinstance(node, ast.Call):

            # -------------------------------------------------------------
            # Method call such as:
            #
            # "UPDATE {} SET {}".format(...)
            # -------------------------------------------------------------

            if isinstance(
                node.func,
                ast.Attribute,
            ) and node.func.attr == "format":

                base = resolve_string(
                    node.func.value,
                    env,
                    visited.copy(),
                    depth + 1,
                )

                positional_values = []

                for argument in node.args:

                    positional_values.append(
                        resolve_string(
                            argument,
                            env,
                            visited.copy(),
                            depth + 1,
                        )
                    )

                for index, value in enumerate(
                    positional_values
                ):

                    base = base.replace(
                        "{" + str(index) + "}",
                        value,
                    )

                    base = base.replace(
                        "{"
                        + str(index)
                        + ":}"
                        ,
                        value,
                    )

                for keyword in node.keywords:

                    if keyword.arg is None:
                        continue

                    value = resolve_string(
                        keyword.value,
                        env,
                        visited.copy(),
                        depth + 1,
                    )

                    base = base.replace(
                        "{" + keyword.arg + "}",
                        value,
                    )

                return base

            # -------------------------------------------------------------
            # Static wrappers
            # -------------------------------------------------------------

            fn = dotted_name(node.func)

            if fn in {
                "str",
                "str.strip",
                "str.upper",
                "str.lower",
                "str.replace",
            }:

                if node.args:

                    return resolve_string(
                        node.args[0],
                        env,
                        visited.copy(),
                        depth + 1,
                    )

                return "{CALL:" + str(fn) + "}"

            return (
                "{CALL:"
                + str(fn or "DYNAMIC")
                + "}"
            )

        # -----------------------------------------------------------------
        # Conditional expression
        # -----------------------------------------------------------------

        if isinstance(node, ast.IfExp):

            body = resolve_string(
                node.body,
                env,
                visited.copy(),
                depth + 1,
            )

            orelse = resolve_string(
                node.orelse,
                env,
                visited.copy(),
                depth + 1,
            )

            if body == orelse:
                return body

            return (
                "{IFEXP:"
                + body
                + "|"
                + orelse
                + "}"
            )

        # -----------------------------------------------------------------
        # Subscript
        # -----------------------------------------------------------------

        if isinstance(node, ast.Subscript):

            base = resolve_string(
                node.value,
                env,
                visited.copy(),
                depth + 1,
            )

            return (
                base
                + "[DYNAMIC]"
            )

        # -----------------------------------------------------------------
        # Containers
        # -----------------------------------------------------------------

        if isinstance(node, ast.Dict):
            return "{DICT}"

        if isinstance(node, ast.Tuple):
            return "{TUPLE}"

        if isinstance(node, ast.List):
            return "{LIST}"

        # -----------------------------------------------------------------
        # Unary
        # -----------------------------------------------------------------

        if isinstance(node, ast.UnaryOp):

            operand = resolve_string(
                node.operand,
                env,
                visited.copy(),
                depth + 1,
            )

            return operand

    finally:

        visited.discard(node_id)

    return ""


def resolve_sql(
    node,
    env=None,
):
    """
    Resolve SQL with recursive environment substitution.

    Important:
    this function does NOT assume that every variable in the
    environment is relevant. It resolves the supplied node only.
    """

    if node is None:
        return ""

    if env is None:
        env = {}

    result = resolve_string(
        node,
        env,
    )

    previous = None

    for _ in range(20):

        if result == previous:
            break

        previous = result

        changed = False

        for name, value_node in env.items():

            if not isinstance(name, str):
                continue

            value = resolve_string(
                value_node,
                env,
            )

            if not value:
                continue

            placeholder = (
                "{"
                + re.escape(name)
                + "}"
            )

            new_result = re.sub(
                placeholder,
                lambda _match: value,
                result,
            )

            if new_result != result:
                changed = True
                result = new_result

        if not changed:
            break

    return result
# =============================================================================
# SQL CLASSIFICATION
# =============================================================================

def sql_operation(sql):

    if not sql:
        return "UNKNOWN"

    match = WRITE_RE.search(sql)

    if match:
        return match.group(1).upper()

    if DELETE_RE.search(sql):
        return "DELETE"

    if SELECT_RE.search(sql):
        return "SELECT"

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


def dynamic_sql(sql):

    if not sql:
        return True

    markers = {
        "{",
        "}",
        "{CALL:",
        "{DYNAMIC}",
        "{CYCLE}",
        "{DEPTH_LIMIT}",
    }

    return any(
        marker in sql
        for marker in markers
    )


def is_db_execution(node):

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
        qualname,
    ):

        self.analysis = analysis
        self.node = node

        self.name = node.name
        self.qualname = qualname

        self.parameters = []

        self.assignments = []
        self.returns = []
        self.calls = []
        self.write_primitives = []

        self.local_env = {}

        self.return_names = set()
        self.sql_names = set()


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
        self.assignments = []
        self.returns = []
        self.write_primitives = []

        self.target_hits = []

        # Module/global static environment.
        self.module_env = {}


# =============================================================================
# FUNCTION CONTAINMENT
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

    def __init__(
        self,
        analysis,
    ):

        self.analysis = analysis

        self.function_stack = []

        self.environment_stack = []

        self.qualname_stack = []

    @property
    def current_function(self):

        if not self.function_stack:
            return None

        return self.function_stack[-1]

    @property
    def current_env(self):

        if not self.environment_stack:
            return self.analysis.module_env

        return self.environment_stack[-1]

    @property
    def current_qualname(self):

        if not self.qualname_stack:
            return "<module>"

        return self.qualname_stack[-1]

    def visit_FunctionDef(
        self,
        node,
    ):

        if self.qualname_stack:

            qualname = (
                self.qualname_stack[-1]
                + "."
                + node.name
            )

        else:

            qualname = node.name

        info = FunctionInfo(
            self.analysis,
            node,
            qualname,
        )

        self.analysis.functions[
            qualname
        ] = info

        args = []

        args.extend(
            node.args.posonlyargs
        )

        args.extend(
            node.args.args
        )

        args.extend(
            node.args.kwonlyargs
        )

        if node.args.vararg:
            args.append(
                node.args.vararg
            )

        if node.args.kwarg:
            args.append(
                node.args.kwarg
            )

        info.parameters = [
            arg.arg
            for arg in args
        ]

        self.function_stack.append(
            info
        )

        self.environment_stack.append(
            {}
        )

        self.qualname_stack.append(
            qualname
        )

        for statement in node.body:
            self.visit(statement)

        info.local_env = dict(
            self.current_env
        )

        self.qualname_stack.pop()
        self.environment_stack.pop()
        self.function_stack.pop()

    def visit_AsyncFunctionDef(
        self,
        node,
    ):

        self.visit_FunctionDef(
            node
        )

    def _record_assignment(
        self,
        node,
        variable,
    ):

        self.current_env[
            variable
        ] = node.value

        function_name = (
            self.current_function.name
            if self.current_function
            else "<module>"
        )

        combined_env = merge_environments(
            self.analysis.module_env,
            self.current_env,
        )

        resolved = resolve_sql(
            node.value,
            combined_env,
        )

        record = {
            "path": self.analysis.path,
            "category": self.analysis.category,
            "line": line_no(node),
            "function": function_name,
            "qualname": self.current_qualname,
            "variable": variable,
            "value": clean(resolved),
            "expression": clean(
                safe_unparse(
                    node.value
                )
            ),
            "node": node,
            "environment": dict(
                combined_env
            ),
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

    def visit_Assign(
        self,
        node,
    ):

        targets = []

        for target in node.targets:

            targets.extend(
                assignment_targets(
                    target
                )
            )

        for variable in targets:

            self._record_assignment(
                node,
                variable,
            )

        self.generic_visit(
            node
        )

    def visit_AnnAssign(
        self,
        node,
    ):

        if (
            isinstance(
                node.target,
                ast.Name,
            )
            and node.value is not None
        ):

            self._record_assignment(
                node,
                node.target.id,
            )

        self.generic_visit(
            node
        )

    def visit_Call(
        self,
        node,
    ):

        called = dotted_name(
            node.func
        )

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
                "caller_qualname": self.current_qualname,
                "called": called,
                "node": node,
                "environment": dict(
                    merge_environments(
                        self.analysis.module_env,
                        self.current_env,
                    )
                ),
            }

            self.analysis.function_calls.append(
                record
            )

            if self.current_function:

                self.current_function.calls.append(
                    record
                )

        # -----------------------------------------------------------------
        # DB execution primitive
        # -----------------------------------------------------------------

        if is_db_execution(node):

            sql_node = (
                node.args[0]
                if node.args
                else None
            )

            combined_env = merge_environments(
                self.analysis.module_env,
                self.current_env,
            )

            sql = resolve_sql(
                sql_node,
                combined_env,
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
                "qualname": self.current_qualname,
                "method": called,
                "sql": clean(sql),
                "operation": sql_operation(sql),
                "target": targets_risk_decisions(sql),
                "is_write": is_write_operation(sql),
                "dynamic": dynamic_sql(sql),
                "node": node,
                "sql_node": sql_node,
                "params_nodes": list(
                    node.args[1:]
                ),
                "environment": dict(
                    combined_env
                ),
            }

            self.analysis.write_primitives.append(
                primitive
            )

            if self.current_function:

                self.current_function.write_primitives.append(
                    primitive
                )

        self.generic_visit(
            node
        )

    def visit_Return(
        self,
        node,
    ):

        function_name = (
            self.current_function.name
            if self.current_function
            else "<module>"
        )

        combined_env = merge_environments(
            self.analysis.module_env,
            self.current_env,
        )

        value = resolve_sql(
            node.value,
            combined_env,
        )

        record = {
            "path": self.analysis.path,
            "category": self.analysis.category,
            "line": line_no(node),
            "function": function_name,
            "qualname": self.current_qualname,
            "value": clean(value),
            "expression": clean(
                safe_unparse(
                    node.value
                )
            ),
            "node": node,
            "environment": dict(
                combined_env
            ),
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

        self.generic_visit(
            node
        )


# =============================================================================
# ANALYSIS
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

    # -------------------------------------------------------------------------
    # First pass:
    # collect module-level assignments.
    #
    # This is critical for:
    #
    # TARGET_TABLE = "risk_decisions"
    #
    # used inside functions.
    # -------------------------------------------------------------------------

    for statement in tree.body:

        if isinstance(
            statement,
            ast.Assign,
        ):

            targets = []

            for target in statement.targets:
                targets.extend(
                    assignment_targets(
                        target
                    )
                )

            for variable in targets:
                analysis.module_env[
                    variable
                ] = statement.value

        elif isinstance(
            statement,
            ast.AnnAssign,
        ):

            if (
                isinstance(
                    statement.target,
                    ast.Name,
                )
                and statement.value is not None
            ):

                analysis.module_env[
                    statement.target.id
                ] = statement.value

    Analyzer(
        analysis
    ).visit(
        tree
    )

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
# FUNCTION INDEX
# =============================================================================

def build_function_index(
    analyses,
):

    index = defaultdict(list)

    for analysis in analyses:

        for qualname, info in (
            analysis.functions.items()
        ):

            index[
                info.name
            ].append(
                {
                    "analysis": analysis,
                    "function": info,
                    "qualname": qualname,
                }
            )

    return index


# =============================================================================
# CALL INDEX
# =============================================================================

def build_call_index(
    analyses,
):

    calls_by_callee = defaultdict(list)

    function_names = set()

    for analysis in analyses:

        for info in (
            analysis.functions.values()
        ):

            function_names.add(
                info.name
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

            caller_qualname = (
                caller.qualname
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
                    "caller_qualname": caller_qualname,
                    "called": call["called"],
                    "node": call["node"],
                    "environment": call.get(
                        "environment",
                        {},
                    ),
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

    positional = list(
        function_info.parameters
    )

    # -------------------------------------------------------------------------
    # Positional arguments
    # -------------------------------------------------------------------------

    for index, argument in enumerate(
        call_node.args
    ):

        if index >= len(positional):
            break

        bindings[
            positional[index]
        ] = argument

    # -------------------------------------------------------------------------
    # Keyword arguments
    # -------------------------------------------------------------------------

    for keyword in call_node.keywords:

        if keyword.arg is None:
            continue

        bindings[
            keyword.arg
        ] = keyword.value

    return bindings


# =============================================================================
# FUNCTION MATCHING
# =============================================================================

def candidate_functions(
    function_index,
    called,
    caller_analysis=None,
):

    short = (
        called.split(".")[-1]
    )

    candidates = function_index.get(
        short,
        [],
    )

    if not candidates:
        return []

    # Prefer same-file definitions.
    if caller_analysis is not None:

        same_file = [
            item
            for item in candidates
            if item["analysis"].path
            == caller_analysis.path
        ]

        if same_file:
            return same_file

    return candidates


# =============================================================================
# SQL BUILDER EVIDENCE
# =============================================================================

def assignment_sql_evidence(
    assignment,
):

    expression = assignment[
        "node"
    ].value

    text = safe_unparse(
        expression
    )

    resolved = assignment.get(
        "value",
        "",
    )

    combined = (
        text
        + " "
        + resolved
    )

    reasons = []
    score = 0

    if WRITE_RE.search(
        combined
    ):

        score += 40

        reasons.append(
            "write_sql"
        )

    if TARGET_RE.search(
        combined
    ):

        score += 180

        reasons.append(
            "risk_decisions_target"
        )

    if (
        "sql"
        in combined.lower()
    ):

        score += 20

        reasons.append(
            "sql_token"
        )

    if (
        "query"
        in combined.lower()
    ):

        score += 15

        reasons.append(
            "query_token"
        )

    if (
        "execute"
        in combined.lower()
    ):

        score += 20

        reasons.append(
            "execute_token"
        )

    return score, reasons


def score_builder_function(
    info,
):

    score = 0
    reasons = []

    name = info.name.lower()

    # -------------------------------------------------------------------------
    # Name hints are weak evidence.
    # -------------------------------------------------------------------------

    for hint in BUILDER_HINTS:

        if hint in name:

            score += 2

            reasons.append(
                f"name:{hint}"
            )

    # -------------------------------------------------------------------------
    # Parameters
    # -------------------------------------------------------------------------

    for parameter in info.parameters:

        lowered = parameter.lower()

        if (
            lowered in SQL_HINTS
            or "sql" in lowered
            or "query" in lowered
            or "statement" in lowered
        ):

            score += 20

            reasons.append(
                f"sql_parameter:{parameter}"
            )

        if (
            lowered in PARAM_HINTS
            or "param" in lowered
            or "value" in lowered
        ):

            score += 5

            reasons.append(
                f"parameter:{parameter}"
            )

        if lowered in RISK_HINTS:

            score += 10

            reasons.append(
                f"risk_parameter:{parameter}"
            )

    # -------------------------------------------------------------------------
    # Actual SQL assignments
    # -------------------------------------------------------------------------

    actual_sql_evidence = False

    for assignment in info.assignments:

        assignment_score, assignment_reasons = (
            assignment_sql_evidence(
                assignment
            )
        )

        if assignment_score > 0:

            actual_sql_evidence = True

            score += assignment_score

            reasons.extend(
                assignment_reasons
            )

    # -------------------------------------------------------------------------
    # Return evidence
    # -------------------------------------------------------------------------

    for ret in info.returns:

        text = safe_unparse(
            ret["node"].value
        )

        resolved = ret.get(
            "value",
            "",
        )

        combined = (
            text
            + " "
            + resolved
        )

        if WRITE_RE.search(
            combined
        ):

            score += 40

            reasons.append(
                "write_return"
            )

            actual_sql_evidence = True

        if TARGET_RE.search(
            combined
        ):

            score += 180

            reasons.append(
                "target_return"
            )

            actual_sql_evidence = True

        if (
            "sql"
            in combined.lower()
        ):

            score += 20

            reasons.append(
                "sql_return"
            )

    # -------------------------------------------------------------------------
    # Direct return of a dynamic builder is also useful.
    # -------------------------------------------------------------------------

    if info.returns:

        for ret in info.returns:

            if isinstance(
                ret["node"].value,
                ast.Call,
            ):

                called = dotted_name(
                    ret["node"].value.func
                )

                if called:

                    score += 15

                    reasons.append(
                        "return_call"
                    )

    # -------------------------------------------------------------------------
    # Anti-noise rule
    # -------------------------------------------------------------------------

    if not actual_sql_evidence:

        return 0, []

    return (
        score,
        list(
            dict.fromkeys(
                reasons
            )
        ),
    )


def build_builder_index(
    analyses,
):

    result = []

    for analysis in analyses:

        for info in (
            analysis.functions.values()
        ):

            score, reasons = (
                score_builder_function(
                    info
                )
            )

            if score <= 0:
                continue

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
            str(
                item["analysis"].path
            ),
            item["function"].qualname,
        )
    )

    return result


# =============================================================================
# DYNAMIC WRITE SIGNALS
# =============================================================================

def collect_dynamic_write_signals(
    analyses,
):

    records = []

    for analysis in analyses:

        for primitive in (
            analysis.write_primitives
        ):

            if not primitive[
                "is_write"
            ]:
                continue

            if primitive[
                "target"
            ]:
                continue

            if not primitive[
                "dynamic"
            ]:
                continue

            records.append(
                primitive
            )

    return records


# =============================================================================
# SQL ARGUMENT PROVENANCE
# =============================================================================

def sql_argument_provenance(
    primitive,
):

    node = primitive[
        "sql_node"
    ]

    if isinstance(
        node,
        ast.Name,
    ):

        return {
            "kind": "NAME",
            "name": node.id,
            "expression": node.id,
        }

    if isinstance(
        node,
        ast.Call,
    ):

        return {
            "kind": "CALL",
            "name": dotted_name(
                node.func
            ),
            "expression": safe_unparse(
                node
            ),
        }

    if isinstance(
        node,
        ast.JoinedStr,
    ):

        return {
            "kind": "FSTRING",
            "name": None,
            "expression": safe_unparse(
                node
            ),
        }

    if isinstance(
        node,
        ast.Attribute,
    ):

        return {
            "kind": "ATTRIBUTE",
            "name": dotted_name(
                node
            ),
            "expression": safe_unparse(
                node
            ),
        }

    return {
        "kind": (
            type(node).__name__
            if node is not None
            else "NONE"
        ),
        "name": None,
        "expression": safe_unparse(
            node
        ),
    }


# =============================================================================
# ASSIGNMENT LOOKUP
# =============================================================================

def assignment_by_name(
    analysis,
    function_name,
    variable_name,
):

    candidates = []

    for assignment in (
        analysis.assignments
    ):

        if (
            assignment["function"]
            == function_name
            and assignment["variable"]
            == variable_name
        ):

            candidates.append(
                assignment
            )

    candidates.sort(
        key=lambda item: item[
            "line"
        ],
        reverse=True,
    )

    return candidates


# =============================================================================
# TARGET ENVIRONMENT SEARCH
# =============================================================================

def direct_target_environment_evidence(
    node,
    environment,
):
    """
    Only inspect the symbolic value actually feeding the SQL expression.

    This avoids the previous false positive where:

        unrelated_variable = "risk_decisions"

    anywhere in the function caused a dynamic write to be marked
    as reaching the target.
    """

    evidence = []

    if node is None:
        return evidence

    resolved = resolve_sql(
        node,
        environment,
    )

    if targets_risk_decisions(
        resolved
    ):

        evidence.append(
            {
                "variable": (
                    node.id
                    if isinstance(
                        node,
                        ast.Name,
                    )
                    else None
                ),
                "expression": safe_unparse(
                    node
                ),
                "resolved": resolved,
            }
        )

    return evidence


# =============================================================================
# BUILDER INTERNAL SQL EVIDENCE
# =============================================================================

def inspect_builder_sql(
    builder_info,
):

    info = builder_info[
        "function"
    ]

    records = []

    # -------------------------------------------------------------------------
    # Assignments
    # -------------------------------------------------------------------------

    for assignment in (
        info.assignments
    ):

        expression = assignment[
            "node"
        ].value

        text = safe_unparse(
            expression
        )

        resolved = assignment.get(
            "value",
            "",
        )

        combined = (
            text
            + " "
            + resolved
        )

        sql_score = 0
        reasons = []

        if WRITE_RE.search(
            combined
        ):

            sql_score += 40
            reasons.append(
                "write_keyword"
            )

        if TARGET_RE.search(
            combined
        ):

            sql_score += 180
            reasons.append(
                "risk_decisions_target"
            )

        if (
            "sql"
            in combined.lower()
        ):

            sql_score += 20
            reasons.append(
                "sql_token"
            )

        if (
            "query"
            in combined.lower()
        ):

            sql_score += 15
            reasons.append(
                "query_token"
            )

        if sql_score:

            records.append(
                {
                    "line": assignment[
                        "line"
                    ],
                    "variable": assignment[
                        "variable"
                    ],
                    "expression": clean(
                        text
                    ),
                    "resolved": clean(
                        resolved
                    ),
                    "score": sql_score,
                    "reasons": reasons,
                }
            )

    # -------------------------------------------------------------------------
    # Returns
    # -------------------------------------------------------------------------

    for ret in info.returns:

        expression = ret[
            "node"
        ].value

        text = safe_unparse(
            expression
        )

        resolved = ret.get(
            "value",
            "",
        )

        combined = (
            text
            + " "
            + resolved
        )

        sql_score = 0
        reasons = []

        if WRITE_RE.search(
            combined
        ):

            sql_score += 40

            reasons.append(
                "write_return"
            )

        if TARGET_RE.search(
            combined
        ):

            sql_score += 180

            reasons.append(
                "target_return"
            )

        if (
            "sql"
            in combined.lower()
        ):

            sql_score += 20

            reasons.append(
                "sql_return"
            )

        if (
            "query"
            in combined.lower()
        ):

            sql_score += 15

            reasons.append(
                "query_return"
            )

        if sql_score:

            records.append(
                {
                    "line": ret[
                        "line"
                    ],
                    "variable": "<RETURN>",
                    "expression": clean(
                        text
                    ),
                    "resolved": clean(
                        resolved
                    ),
                    "score": sql_score,
                    "reasons": reasons,
                }
            )

    records.sort(
        key=lambda item: -item[
            "score"
        ]
    )

    return records


# =============================================================================
# PROPAGATION HELPERS
# =============================================================================

def resolve_argument_in_caller(
    argument,
    call,
    analyses,
):

    caller_environment = call.get(
        "environment",
        {},
    )

    resolved = resolve_sql(
        argument,
        caller_environment,
    )

    return (
        resolved,
        caller_environment,
    )


def function_return_target_evidence(
    info,
    environment,
):

    evidence = []

    for ret in info.returns:

        resolved = resolve_sql(
            ret["node"].value,
            environment,
        )

        if targets_risk_decisions(
            resolved
        ):

            evidence.append(
                {
                    "line": ret["line"],
                    "expression": safe_unparse(
                        ret["node"].value
                    ),
                    "resolved": resolved,
                }
            )

    return evidence


# =============================================================================
# TARGETED PROPAGATION
# =============================================================================

def propagate_dynamic_signal(
    signal,
    analyses,
    function_index,
    calls_by_callee,
    builder_index,
):

    source_analysis = None

    for analysis in analyses:

        if (
            analysis.path
            == signal["path"]
        ):

            source_analysis = analysis
            break

    if source_analysis is None:

        return {
            "signal": signal,
            "steps": [],
            "confidence": 0,
            "target_reached": False,
        }

    provenance = (
        sql_argument_provenance(
            signal
        )
    )

    steps = []

    visited = set()

    queue = deque()

    # -------------------------------------------------------------------------
    # Initial state
    # -------------------------------------------------------------------------

    queue.append(
        {
            "analysis": source_analysis,
            "function": signal[
                "function"
            ],
            "qualname": signal.get(
                "qualname",
                signal["function"],
            ),
            "variable": provenance.get(
                "name"
            ),
            "role": "SQL_ARGUMENT",
            "depth": 0,
            "expression": provenance.get(
                "expression"
            ),
            "node": signal[
                "sql_node"
            ],
            "environment": signal.get(
                "environment",
                {},
            ),
        }
    )

    confidence = 0
    target_reached = False

    while queue:

        state = queue.popleft()

        state_key = (
            str(
                state["analysis"].path
            ),
            state["function"],
            state.get(
                "qualname"
            ),
            state["variable"],
            state["role"],
            state["depth"],
            clean(
                state.get(
                    "expression"
                )
            ),
        )

        if state_key in visited:
            continue

        visited.add(
            state_key
        )

        if (
            state["depth"]
            > MAX_PROPAGATION_DEPTH
        ):
            continue

        analysis = state[
            "analysis"
        ]

        function_name = state[
            "function"
        ]

        variable_name = state[
            "variable"
        ]

        environment = state.get(
            "environment",
            {},
        )

        # ---------------------------------------------------------------------
        # Generic state step
        # ---------------------------------------------------------------------

        step = {
            "depth": state[
                "depth"
            ],
            "path": analysis.path,
            "category": analysis.category,
            "function": function_name,
            "variable": variable_name,
            "role": state[
                "role"
            ],
            "expression": clean(
                state.get(
                    "expression"
                )
            ),
        }

        steps.append(
            step
        )

        # =====================================================================
        # A) INITIAL SQL ARGUMENT TARGET CHECK
        # =====================================================================

        if state[
            "depth"
        ] == 0:

            resolved = resolve_sql(
                state.get(
                    "node"
                ),
                environment,
            )

            if targets_risk_decisions(
                resolved
            ):

                target_reached = True

                confidence += 500

                steps.append(
                    {
                        "depth": 1,
                        "path": analysis.path,
                        "category": analysis.category,
                        "function": function_name,
                        "variable": variable_name,
                        "role": "DIRECT_RESOLVED_TARGET",
                        "expression": clean(
                            safe_unparse(
                                state.get(
                                    "node"
                                )
                            )
                        ),
                        "resolved": clean(
                            resolved
                        ),
                        "score": 500,
                        "reasons": [
                            "sql_argument_resolves_to_target"
                        ],
                    }
                )

        # =====================================================================
        # B) VARIABLE -> LOCAL ASSIGNMENT
        # =====================================================================

        if variable_name:

            local_assignments = (
                assignment_by_name(
                    analysis,
                    function_name,
                    variable_name,
                )
            )

            for assignment in local_assignments:

                expression = assignment[
                    "node"
                ].value

                text = safe_unparse(
                    expression
                )

                assignment_environment = (
                    assignment.get(
                        "environment",
                        environment,
                    )
                )

                resolved = resolve_sql(
                    expression,
                    assignment_environment,
                )

                local_step = {
                    "depth": state[
                        "depth"
                    ] + 1,
                    "path": analysis.path,
                    "category": analysis.category,
                    "function": function_name,
                    "variable": variable_name,
                    "role": "LOCAL_ASSIGNMENT",
                    "line": assignment[
                        "line"
                    ],
                    "expression": clean(
                        text
                    ),
                    "resolved": clean(
                        resolved
                    ),
                }

                steps.append(
                    local_step
                )

                # -------------------------------------------------------------
                # Target after exact assignment resolution
                # -------------------------------------------------------------

                if targets_risk_decisions(
                    resolved
                ):

                    target_reached = True

                    confidence += 400

                    steps.append(
                        {
                            "depth": state[
                                "depth"
                            ] + 1,
                            "path": analysis.path,
                            "category": analysis.category,
                            "function": function_name,
                            "variable": variable_name,
                            "role": "TARGET_RESOLVED_SQL",
                            "line": assignment[
                                "line"
                            ],
                            "expression": clean(
                                text
                            ),
                            "resolved": clean(
                                resolved
                            ),
                            "score": 400,
                            "reasons": [
                                "resolved_sql_targets_risk_decisions"
                            ],
                        }
                    )

                elif (
                    TARGET_TABLE.lower()
                    in resolved.lower()
                ):

                    # We distinguish a literal table token from a complete
                    # SQL target pattern. It is evidence, but weaker.
                    confidence += 120

                    steps.append(
                        {
                            "depth": state[
                                "depth"
                            ] + 1,
                            "path": analysis.path,
                            "category": analysis.category,
                            "function": function_name,
                            "variable": variable_name,
                            "role": "TARGET_TOKEN_EVIDENCE",
                            "line": assignment[
                                "line"
                            ],
                            "expression": clean(
                                text
                            ),
                            "resolved": clean(
                                resolved
                            ),
                            "score": 120,
                            "reasons": [
                                "target_table_token"
                            ],
                        }
                    )

                if WRITE_RE.search(
                    resolved
                ):

                    confidence += 50

                # =================================================================
                # C) ASSIGNMENT RHS = FUNCTION CALL
                # =================================================================

                if isinstance(
                    expression,
                    ast.Call,
                ):

                    called = dotted_name(
                        expression.func
                    )

                    if called:

                        candidates = (
                            candidate_functions(
                                function_index,
                                called,
                                analysis,
                            )
                        )

                        for candidate in candidates:

                            builder_info = candidate[
                                "function"
                            ]

                            builder_analysis = candidate[
                                "analysis"
                            ]

                            builder_score, reasons = (
                                score_builder_function(
                                    builder_info
                                )
                            )

                            if builder_score <= 0:
                                continue

                            builder_step = {
                                "depth": state[
                                    "depth"
                                ] + 1,
                                "path": builder_analysis.path,
                                "category": builder_analysis.category,
                                "function": builder_info.name,
                                "variable": "<RETURN>",
                                "role": "BUILDER_CALL",
                                "line": line_no(
                                    expression
                                ),
                                "called": called,
                                "builder_score": builder_score,
                                "builder_reasons": reasons[
                                    :20
                                ],
                            }

                            steps.append(
                                builder_step
                            )

                            confidence += (
                                builder_score
                            )

                            # -----------------------------------------------------
                            # Builder internal SQL
                            # -----------------------------------------------------

                            internal_sql = (
                                inspect_builder_sql(
                                    {
                                        "analysis": builder_analysis,
                                        "function": builder_info,
                                        "score": builder_score,
                                    }
                                )
                            )

                            for sql_record in internal_sql[
                                :MAX_RESULTS_PER_SIGNAL
                            ]:

                                sql_expression = (
                                    sql_record[
                                        "expression"
                                    ]
                                )

                                sql_resolved = (
                                    sql_record[
                                        "resolved"
                                    ]
                                )

                                combined = (
                                    sql_expression
                                    + " "
                                    + sql_resolved
                                )

                                if (
                                    TARGET_RE.search(
                                        combined
                                    )
                                ):

                                    target_reached = True

                                    confidence += 300

                                steps.append(
                                    {
                                        "depth": state[
                                            "depth"
                                        ] + 2,
                                        "path": builder_analysis.path,
                                        "category": builder_analysis.category,
                                        "function": builder_info.name,
                                        "variable": sql_record[
                                            "variable"
                                        ],
                                        "role": "BUILDER_SQL_EVIDENCE",
                                        "line": sql_record[
                                            "line"
                                        ],
                                        "expression": sql_expression,
                                        "resolved": sql_resolved,
                                        "score": sql_record[
                                            "score"
                                        ],
                                        "reasons": sql_record[
                                            "reasons"
                                        ],
                                    }
                                )

                                confidence += (
                                    sql_record[
                                        "score"
                                    ]
                                )

                            # -----------------------------------------------------
                            # Builder parameter bindings
                            # -----------------------------------------------------

                            bindings = (
                                bind_call_arguments(
                                    builder_info,
                                    expression,
                                )
                            )

                            caller_environment = (
                                assignment.get(
                                    "environment",
                                    environment,
                                )
                            )

                            for parameter, argument in (
                                bindings.items()
                            ):

                                parameter_lower = (
                                    parameter.lower()
                                )

                                parameter_score = 0
                                parameter_reasons = []

                                if (
                                    parameter_lower
                                    in SQL_HINTS
                                    or "sql"
                                    in parameter_lower
                                    or "query"
                                    in parameter_lower
                                    or "statement"
                                    in parameter_lower
                                ):

                                    parameter_score += 50

                                    parameter_reasons.append(
                                        "sql_parameter"
                                    )

                                if (
                                    "risk"
                                    in parameter_lower
                                ):

                                    parameter_score += 25

                                    parameter_reasons.append(
                                        "risk_parameter"
                                    )

                                argument_resolved = (
                                    resolve_sql(
                                        argument,
                                        caller_environment,
                                    )
                                )

                                if (
                                    node_contains_target(
                                        argument
                                    )
                                ):

                                    parameter_score += 100

                                    parameter_reasons.append(
                                        "target_argument_literal"
                                    )

                                if targets_risk_decisions(
                                    argument_resolved
                                ):

                                    parameter_score += 250

                                    parameter_reasons.append(
                                        "resolved_target_argument"
                                    )

                                    target_reached = True

                                elif (
                                    TARGET_TABLE.lower()
                                    in argument_resolved.lower()
                                ):

                                    parameter_score += 120

                                    parameter_reasons.append(
                                        "target_token_argument"
                                    )

                                steps.append(
                                    {
                                        "depth": state[
                                            "depth"
                                        ] + 2,
                                        "path": builder_analysis.path,
                                        "category": builder_analysis.category,
                                        "function": builder_info.name,
                                        "variable": parameter,
                                        "role": "BUILDER_PARAMETER_BINDING",
                                        "argument": clean(
                                            safe_unparse(
                                                argument
                                            )
                                        ),
                                        "resolved_argument": clean(
                                            argument_resolved
                                        ),
                                        "score": parameter_score,
                                        "reasons": parameter_reasons,
                                    }
                                )

                                confidence += (
                                    parameter_score
                                )

                                # -------------------------------------------------
                                # Continue into builder parameter.
                                # -------------------------------------------------

                                queue.append(
                                    {
                                        "analysis": builder_analysis,
                                        "function": builder_info.name,
                                        "qualname": builder_info.qualname,
                                        "variable": parameter,
                                        "role": "BUILDER_PARAMETER",
                                        "depth": state[
                                            "depth"
                                        ] + 2,
                                        "expression": safe_unparse(
                                            argument
                                        ),
                                        "node": argument,
                                        "environment": merge_environments(
                                            builder_analysis.module_env,
                                            builder_info.local_env,
                                        ),
                                    }
                                )

                            # -----------------------------------------------------
                            # Builder return evidence
                            # -----------------------------------------------------

                            return_evidence = (
                                function_return_target_evidence(
                                    builder_info,
                                    merge_environments(
                                        builder_analysis.module_env,
                                        builder_info.local_env,
                                    ),
                                )
                            )

                            for item in return_evidence:

                                target_reached = True

                                confidence += 250

                                steps.append(
                                    {
                                        "depth": state[
                                            "depth"
                                        ] + 2,
                                        "path": builder_analysis.path,
                                        "category": builder_analysis.category,
                                        "function": builder_info.name,
                                        "variable": "<RETURN>",
                                        "role": "BUILDER_TARGET_RETURN",
                                        "line": item[
                                            "line"
                                        ],
                                        "expression": clean(
                                            item[
                                                "expression"
                                            ]
                                        ),
                                        "resolved": clean(
                                            item[
                                                "resolved"
                                            ]
                                        ),
                                        "score": 250,
                                        "reasons": [
                                            "builder_return_resolves_to_target"
                                        ],
                                    }
                                )

                # =================================================================
                # D) ASSIGNMENT DEPENDENCIES
                # =================================================================

                names = expression_names(
                    expression
                )

                for dependency in names:

                    if dependency == variable_name:
                        continue

                    queue.append(
                        {
                            "analysis": analysis,
                            "function": function_name,
                            "qualname": state.get(
                                "qualname",
                                function_name,
                            ),
                            "variable": dependency,
                            "role": "UPSTREAM_LOCAL",
                            "depth": state[
                                "depth"
                            ] + 1,
                            "expression": safe_unparse(
                                expression
                            ),
                            "node": expression,
                            "environment": assignment_environment,
                        }
                    )

        # =====================================================================
        # E) DIRECT CALL SQL ARGUMENT
        #
        # Handles:
        #
        # cursor.execute(
        #     build_risk_sql(record)
        # )
        # =====================================================================

        current_node = state.get(
            "node"
        )

        if isinstance(
            current_node,
            ast.Call,
        ):

            called = dotted_name(
                current_node.func
            )

            if called:

                candidates = (
                    candidate_functions(
                        function_index,
                        called,
                        analysis,
                    )
                )

                for candidate in candidates:

                    builder_info = candidate[
                        "function"
                    ]

                    builder_analysis = candidate[
                        "analysis"
                    ]

                    builder_score, reasons = (
                        score_builder_function(
                            builder_info
                        )
                    )

                    if builder_score <= 0:
                        continue

                    steps.append(
                        {
                            "depth": state[
                                "depth"
                            ] + 1,
                            "path": builder_analysis.path,
                            "category": builder_analysis.category,
                            "function": builder_info.name,
                            "variable": "<RETURN>",
                            "role": "DIRECT_BUILDER_CALL",
                            "line": line_no(
                                current_node
                            ),
                            "called": called,
                            "builder_score": builder_score,
                            "builder_reasons": reasons[
                                :20
                            ],
                        }
                    )

                    confidence += (
                        builder_score
                    )

                    # ---------------------------------------------------------
                    # Bind builder parameters
                    # ---------------------------------------------------------

                    bindings = (
                        bind_call_arguments(
                            builder_info,
                            current_node,
                        )
                    )

                    for parameter, argument in (
                        bindings.items()
                    ):

                        argument_resolved = (
                            resolve_sql(
                                argument,
                                environment,
                            )
                        )

                        parameter_score = 0
                        parameter_reasons = []

                        if (
                            "sql"
                            in parameter.lower()
                            or "query"
                            in parameter.lower()
                            or "statement"
                            in parameter.lower()
                        ):

                            parameter_score += 50

                            parameter_reasons.append(
                                "sql_parameter"
                            )

                        if targets_risk_decisions(
                            argument_resolved
                        ):

                            parameter_score += 250

                            parameter_reasons.append(
                                "resolved_target_argument"
                            )

                            target_reached = True

                        steps.append(
                            {
                                "depth": state[
                                    "depth"
                                ] + 2,
                                "path": builder_analysis.path,
                                "category": builder_analysis.category,
                                "function": builder_info.name,
                                "variable": parameter,
                                "role": "DIRECT_BUILDER_PARAMETER",
                                "argument": clean(
                                    safe_unparse(
                                        argument
                                    )
                                ),
                                "resolved_argument": clean(
                                    argument_resolved
                                ),
                                "score": parameter_score,
                                "reasons": parameter_reasons,
                            }
                        )

                        confidence += (
                            parameter_score
                        )

                        queue.append(
                            {
                                "analysis": builder_analysis,
                                "function": builder_info.name,
                                "qualname": builder_info.qualname,
                                "variable": parameter,
                                "role": "BUILDER_PARAMETER",
                                "depth": state[
                                    "depth"
                                ] + 2,
                                "expression": safe_unparse(
                                    argument
                                ),
                                "node": argument,
                                "environment": merge_environments(
                                    builder_analysis.module_env,
                                    builder_info.local_env,
                                ),
                            }
                        )

                    # ---------------------------------------------------------
                    # Return target evidence
                    # ---------------------------------------------------------

                    for ret in builder_info.returns:

                        builder_env = merge_environments(
                            builder_analysis.module_env,
                            builder_info.local_env,
                        )

                        resolved_return = resolve_sql(
                            ret["node"].value,
                            builder_env,
                        )

                        if targets_risk_decisions(
                            resolved_return
                        ):

                            target_reached = True

                            confidence += 300

                            steps.append(
                                {
                                    "depth": state[
                                        "depth"
                                    ] + 2,
                                    "path": builder_analysis.path,
                                    "category": builder_analysis.category,
                                    "function": builder_info.name,
                                    "variable": "<RETURN>",
                                    "role": "DIRECT_BUILDER_TARGET_RETURN",
                                    "line": ret[
                                        "line"
                                    ],
                                    "expression": clean(
                                        safe_unparse(
                                            ret[
                                                "node"
                                            ].value
                                        )
                                    ),
                                    "resolved": clean(
                                        resolved_return
                                    ),
                                    "score": 300,
                                    "reasons": [
                                        "direct_builder_return_target"
                                    ],
                                }
                            )

        # =====================================================================
        # F) FUNCTION PARAMETER -> CALLER ARGUMENT
        # =====================================================================

        info = analysis.functions.get(
            state.get(
                "qualname"
            )
        )

        if info is None:

            # Fallback to short function name.
            info = analysis.functions.get(
                function_name
            )

        if (
            info
            and variable_name
            and variable_name in info.parameters
        ):

            calls = calls_by_callee.get(
                info.name,
                [],
            )

            for call in calls:

                bound = bind_call_arguments(
                    info,
                    call["node"],
                )

                if (
                    variable_name
                    not in bound
                ):
                    continue

                argument = bound[
                    variable_name
                ]

                caller_name = call[
                    "caller"
                ]

                argument_text = safe_unparse(
                    argument
                )

                caller_analysis = next(
                    (
                        item
                        for item in analyses
                        if item.path
                        == call["path"]
                    ),
                    analysis,
                )

                argument_resolved = resolve_sql(
                    argument,
                    call.get(
                        "environment",
                        {},
                    ),
                )

                if targets_risk_decisions(
                    argument_resolved
                ):

                    target_reached = True

                    confidence += 250

                caller_step = {
                    "depth": state[
                        "depth"
                    ] + 1,
                    "path": call["path"],
                    "category": call["category"],
                    "function": caller_name,
                    "variable": variable_name,
                    "role": "CALLER_ARGUMENT",
                    "line": call["line"],
                    "argument": clean(
                        argument_text
                    ),
                    "resolved_argument": clean(
                        argument_resolved
                    ),
                    "callee": info.name,
                    "score": 20,
                }

                steps.append(
                    caller_step
                )

                confidence += 20

                argument_names = expression_names(
                    argument
                )

                for name in argument_names:

                    caller_function = (
                        caller_analysis.functions.get(
                            call.get(
                                "caller_qualname"
                            )
                        )
                    )

                    caller_environment = (
                        call.get(
                            "environment",
                            {},
                        )
                    )

                    queue.append(
                        {
                            "analysis": caller_analysis,
                            "function": caller_name,
                            "qualname": call.get(
                                "caller_qualname",
                                caller_name,
                            ),
                            "variable": name,
                            "role": "UPSTREAM_ARGUMENT",
                            "depth": state[
                                "depth"
                            ] + 1,
                            "expression": argument_text,
                            "node": argument,
                            "environment": caller_environment,
                        }
                    )

        # =====================================================================
        # G) TARGET EVIDENCE INSIDE CURRENT FUNCTION
        # =====================================================================

        if info:

            function_environment = merge_environments(
                analysis.module_env,
                info.local_env,
            )

            # ---------------------------------------------------------------
            # Assignments
            # ---------------------------------------------------------------

            for assignment in info.assignments:

                text = safe_unparse(
                    assignment[
                        "node"
                    ].value
                )

                resolved = resolve_sql(
                    assignment[
                        "node"
                    ].value,
                    assignment.get(
                        "environment",
                        function_environment,
                    ),
                )

                combined = (
                    text
                    + " "
                    + resolved
                )

                if TARGET_RE.search(
                    combined
                ):

                    target_reached = True

                    steps.append(
                        {
                            "depth": state[
                                "depth"
                            ] + 1,
                            "path": analysis.path,
                            "category": analysis.category,
                            "function": function_name,
                            "variable": assignment[
                                "variable"
                            ],
                            "role": "TARGET_EVIDENCE",
                            "line": assignment[
                                "line"
                            ],
                            "expression": clean(
                                text
                            ),
                            "resolved": clean(
                                resolved
                            ),
                            "score": 200,
                            "reasons": [
                                "target_sql_pattern"
                            ],
                        }
                    )

                    confidence += 200

            # ---------------------------------------------------------------
            # Returns
            # ---------------------------------------------------------------

            for ret in info.returns:

                text = safe_unparse(
                    ret[
                        "node"
                    ].value
                )

                resolved = resolve_sql(
                    ret[
                        "node"
                    ].value,
                    ret.get(
                        "environment",
                        function_environment,
                    ),
                )

                combined = (
                    text
                    + " "
                    + resolved
                )

                if TARGET_RE.search(
                    combined
                ):

                    target_reached = True

                    steps.append(
                        {
                            "depth": state[
                                "depth"
                            ] + 1,
                            "path": analysis.path,
                            "category": analysis.category,
                            "function": function_name,
                            "variable": "<RETURN>",
                            "role": "TARGET_RETURN_EVIDENCE",
                            "line": ret[
                                "line"
                            ],
                            "expression": clean(
                                text
                            ),
                            "resolved": clean(
                                resolved
                            ),
                            "score": 250,
                            "reasons": [
                                "target_return"
                            ],
                        }
                    )

                    confidence += 250

    # =============================================================================
    # DEDUPLICATION
    # =============================================================================

    deduped = []

    seen_steps = set()

    for item in steps:

        key = (
            str(
                item.get(
                    "path"
                )
            ),
            item.get(
                "function"
            ),
            item.get(
                "variable"
            ),
            item.get(
                "role"
            ),
            item.get(
                "line"
            ),
            item.get(
                "expression"
            ),
            item.get(
                "argument"
            ),
            item.get(
                "resolved"
            ),
            item.get(
                "resolved_argument"
            ),
        )

        if key in seen_steps:
            continue

        seen_steps.add(
            key
        )

        deduped.append(
            item
        )

    # -------------------------------------------------------------------------
    # Strongest evidence first
    # -------------------------------------------------------------------------

    deduped.sort(
        key=lambda item: (
            -int(
                item.get(
                    "score",
                    0,
                )
            ),
            int(
                item.get(
                    "depth",
                    0,
                )
            ),
            str(
                item.get(
                    "path",
                    "",
                )
            ),
            item.get(
                "function",
                "",
            ),
        )
    )

    return {
        "signal": signal,
        "steps": deduped[
            :MAX_RESULTS_PER_SIGNAL
        ],
        "confidence": confidence,
        "target_reached": target_reached,
    }


# =============================================================================
# GLOBAL TARGETED PROPAGATION
# =============================================================================

def run_targeted_propagation(
    signals,
    analyses,
    function_index,
    calls_by_callee,
    builder_index,
):

    results = []

    for index, signal in enumerate(
        signals,
        1,
    ):

        result = propagate_dynamic_signal(
            signal,
            analyses,
            function_index,
            calls_by_callee,
            builder_index,
        )

        result[
            "signal_index"
        ] = index

        results.append(
            result
        )

    results.sort(
        key=lambda item: (
            -item[
                "confidence"
            ],
            str(
                item[
                    "signal"
                ][
                    "path"
                ]
            ),
            item[
                "signal"
            ][
                "line"
            ],
        )
    )

    return results


# =============================================================================
# CLASSIFICATION
# =============================================================================

def confidence_label(
    score,
):

    if score >= 900:
        return "VERY_HIGH"

    if score >= 600:
        return "HIGH"

    if score >= 300:
        return "MEDIUM"

    if score >= 80:
        return "LOW"

    return "TRACE_ONLY"


def result_target_reached(
    result,
):

    if result.get(
        "target_reached",
        False,
    ):

        return True

    target_roles = {
        "TARGET_EVIDENCE",
        "TARGET_RETURN_EVIDENCE",
        "TARGET_RESOLVED_SQL",
        "DIRECT_RESOLVED_TARGET",
        "BUILDER_TARGET_RETURN",
        "DIRECT_BUILDER_TARGET_RETURN",
    }

    for step in result[
        "steps"
    ]:

        role = step.get(
            "role",
            "",
        )

        if role in target_roles:
            return True

        expression = (
            str(
                step.get(
                    "expression",
                    "",
                )
            )
            + " "
            + str(
                step.get(
                    "resolved",
                    "",
                )
            )
            + " "
            + str(
                step.get(
                    "argument",
                    "",
                )
            )
            + " "
            + str(
                step.get(
                    "resolved_argument",
                    "",
                )
            )
        )

        # Stronger condition:
        # require actual SQL target pattern, not merely the bare word.
        if TARGET_RE.search(
            expression
        ):

            return True

    return False


def result_has_builder(
    result,
):

    builder_roles = {
        "BUILDER_CALL",
        "BUILDER_SQL_EVIDENCE",
        "BUILDER_PARAMETER_BINDING",
        "BUILDER_PARAMETER",
        "DIRECT_BUILDER_CALL",
        "DIRECT_BUILDER_PARAMETER",
    }

    for step in result[
        "steps"
    ]:

        if step.get(
            "role"
        ) in builder_roles:

            return True

    return False


# =============================================================================
# REPORT
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


def print_dynamic_signals(
    signals,
):

    separator()

    print(
        "2) TARGETED DYNAMIC WRITE SIGNALS"
    )

    separator()

    print(
        f"DYNAMIC WRITE SIGNALS : {len(signals)}"
    )

    for index, item in enumerate(
        signals,
        1,
    ):

        provenance = (
            sql_argument_provenance(
                item
            )
        )

        print()
        print(
            f"DYNAMIC WRITE #{index}"
        )

        print(
            f"FILE       : {item['path']}"
        )

        print(
            f"CATEGORY   : {item['category']}"
        )

        print(
            f"LINE       : {item['line']}"
        )

        print(
            f"FUNCTION   : {item['function']}"
        )

        print(
            f"METHOD     : {item['method']}"
        )

        print(
            f"OPERATION  : {item['operation']}"
        )

        print(
            f"SQL        : {item['sql']}"
        )

        print(
            f"SQL KIND   : {provenance['kind']}"
        )

        print(
            f"SQL SOURCE : "
            f"{provenance['expression']}"
        )

        resolved_direct = resolve_sql(
            item["sql_node"],
            item.get(
                "environment",
                {},
            ),
        )

        print(
            f"RESOLVED   : "
            f"{clean(resolved_direct)}"
        )

        print(
            "TARGET DIRECT: "
            + (
                "YES"
                if targets_risk_decisions(
                    resolved_direct
                )
                else "NO"
            )
        )


def print_builder_inventory(
    builder_index,
):

    separator()

    print(
        "3) SQL BUILDER / HELPER INVENTORY"
    )

    separator()

    meaningful = [
        item
        for item in builder_index
        if item[
            "score"
        ] >= 40
    ]

    print(
        f"MEANINGFUL SQL BUILDERS : "
        f"{len(meaningful)}"
    )

    print(
        f"RAW BUILDER CANDIDATES  : "
        f"{len(builder_index)}"
    )

    for index, item in enumerate(
        meaningful[
            :MAX_GLOBAL_OUTPUT
        ],
        1,
    ):

        info = item[
            "function"
        ]

        print()
        print(
            f"BUILDER #{index}"
        )

        print(
            f"FILE       : "
            f"{item['analysis'].path}"
        )

        print(
            f"CATEGORY   : "
            f"{item['analysis'].category}"
        )

        print(
            f"LINE       : "
            f"{line_no(info.node)}"
        )

        print(
            f"FUNCTION   : "
            f"{info.qualname}"
        )

        print(
            f"SCORE      : "
            f"{item['score']}"
        )

        print(
            "REASONS    : "
            + ", ".join(
                item["reasons"][:20]
            )
        )


def print_propagation_results(
    results,
):

    separator()

    print(
        "4) DYNAMIC WRITE → SQL BUILDER "
        "SEMANTIC PROPAGATION"
    )

    separator()

    print(
        f"SIGNALS ANALYZED : {len(results)}"
    )

    for result in results:

        signal = result[
            "signal"
        ]

        score = result[
            "confidence"
        ]

        print()
        print(
            "=" * 110
        )

        print(
            f"SIGNAL #{result['signal_index']}"
        )

        print(
            f"WRITE       : "
            f"{signal['path']} "
            f"LINE {signal['line']}"
        )

        print(
            f"CATEGORY    : "
            f"{signal['category']}"
        )

        print(
            f"FUNCTION    : "
            f"{signal['function']}"
        )

        print(
            f"METHOD      : "
            f"{signal['method']}"
        )

        print(
            f"SQL         : "
            f"{signal['sql']}"
        )

        print(
            f"CONFIDENCE  : "
            f"{score}"
        )

        print(
            f"LEVEL       : "
            f"{confidence_label(score)}"
        )

        print(
            f"BUILDER PATH: "
            f"{'YES' if result_has_builder(result) else 'NO'}"
        )

        print(
            f"TARGET HIT  : "
            f"{'YES' if result_target_reached(result) else 'NO'}"
        )

        print()

        for step in result[
            "steps"
        ][
            :MAX_RESULTS_PER_SIGNAL
        ]:

            depth = step.get(
                "depth",
                0,
            )

            role = step.get(
                "role",
                "",
            )

            path = step.get(
                "path",
                "",
            )

            function = step.get(
                "function",
                "",
            )

            variable = step.get(
                "variable",
                "",
            )

            line = step.get(
                "line",
                "",
            )

            expression = step.get(
                "expression",
                "",
            )

            resolved = step.get(
                "resolved",
                "",
            )

            argument = step.get(
                "argument",
                "",
            )

            resolved_argument = step.get(
                "resolved_argument",
                "",
            )

            step_score = step.get(
                "score",
                0,
            )

            print(
                f"DEPTH {depth:<2} "
                f"ROLE={role:<38} "
                f"FUNCTION={function:<35} "
                f"VARIABLE={str(variable):<25} "
                f"LINE={line}"
            )

            if expression:

                print(
                    f"    EXPRESSION : "
                    f"{clean(expression, 700)}"
                )

            if resolved:

                print(
                    f"    RESOLVED   : "
                    f"{clean(resolved, 700)}"
                )

            if argument:

                print(
                    f"    ARGUMENT   : "
                    f"{clean(argument, 700)}"
                )

            if resolved_argument:

                print(
                    f"    ARG RESOLVED: "
                    f"{clean(resolved_argument, 700)}"
                )

            if step_score:

                print(
                    f"    SCORE      : "
                    f"{step_score}"
                )

            if step.get(
                "reasons"
            ):

                print(
                    f"    REASONS    : "
                    f"{', '.join(step['reasons'][:15])}"
                )


def print_final_status(
    signals,
    results,
):

    separator()

    print(
        "5) FINAL PRODUCER STATUS"
    )

    separator()

    total = len(
        results
    )

    target_reached = sum(
        1
        for result in results
        if result_target_reached(
            result
        )
    )

    builder_reached = sum(
        1
        for result in results
        if result_has_builder(
            result
        )
    )

    production_signals = sum(
        1
        for signal in signals
        if signal[
            "category"
        ] == "PRODUCTION"
    )

    production_target_reached = sum(
        1
        for result in results
        if (
            result[
                "signal"
            ][
                "category"
            ]
            == "PRODUCTION"
            and result_target_reached(
                result
            )
        )
    )

    print(
        f"DYNAMIC WRITE SIGNALS        : "
        f"{len(signals)}"
    )

    print(
        f"PRODUCTION DYNAMIC SIGNALS   : "
        f"{production_signals}"
    )

    print(
        f"SIGNALS WITH BUILDER PATH    : "
        f"{builder_reached}"
    )

    print(
        f"SIGNALS REACHING TARGET      : "
        f"{target_reached}"
    )

    print(
        f"PRODUCTION TARGET PATHS      : "
        f"{production_target_reached}"
    )

    print(
        f"RESULTS                       : "
        f"{total}"
    )

    print()

    for result in results:

        signal = result[
            "signal"
        ]

        print(
            f"SIGNAL #{result['signal_index']} "
            f":: "
            f"CATEGORY={signal['category']} "
            f":: "
            f"CONFIDENCE="
            f"{confidence_label(result['confidence'])} "
            f":: "
            f"BUILDER="
            f"{'YES' if result_has_builder(result) else 'NO'} "
            f":: "
            f"TARGET="
            f"{'YES' if result_target_reached(result) else 'NO'} "
            f":: "
            f"{signal['path']}:{signal['line']}"
        )

    print()

    # -------------------------------------------------------------------------
    # Production target reached
    # -------------------------------------------------------------------------

    if production_target_reached > 0:

        print(
            "RESULT : "
            "PRODUCTION DYNAMIC SQL PATH "
            "REACHING risk_decisions FOUND"
        )

        print(
            "PRODUCER STATUS : "
            "SUBSTANTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : "
            "verify exact production SQL payload, "
            "parameter values, and write boundary."
        )

        return

    # -------------------------------------------------------------------------
    # Any target path
    # -------------------------------------------------------------------------

    if target_reached > 0:

        print(
            "RESULT : "
            "DYNAMIC SQL PATH REACHING "
            "risk_decisions FOUND"
        )

        print(
            "PRODUCER STATUS : "
            "TARGET SEMANTICALLY RESOLVED"
        )

        print(
            "NOTE : "
            "TARGET PATH MAY BE FORENSIC/REPAIR CODE; "
            "PRODUCTION STATUS MUST BE CHECKED SEPARATELY."
        )

        return

    # -------------------------------------------------------------------------
    # Builder path
    # -------------------------------------------------------------------------

    if builder_reached > 0:

        print(
            "RESULT : "
            "DYNAMIC WRITE → SQL BUILDER PATH FOUND"
        )

        print(
            "PRODUCER STATUS : "
            "PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : "
            "trace builder parameter values "
            "to final SQL expression."
        )

        return

    # -------------------------------------------------------------------------
    # Signals exist
    # -------------------------------------------------------------------------

    if signals:

        print(
            "RESULT : "
            "DYNAMIC WRITE SIGNALS FOUND "
            "BUT TARGET PATH NOT YET RESOLVED"
        )

        print(
            "PRODUCER STATUS : "
            "PARTIALLY RESOLVED"
        )

        print(
            "NEXT TARGET : "
            "inspect highest-confidence SQL argument "
            "construction."
        )

        return

    # -------------------------------------------------------------------------
    # No signals
    # -------------------------------------------------------------------------

    print(
        "RESULT : "
        "NO DYNAMIC WRITE SIGNALS"
    )

    print(
        "PRODUCER STATUS : "
        "NOT RESOLVED"
    )

    print(
        "NEXT TARGET : "
        "recheck DB execution primitives."
    )


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
        "BACKWARD CHAIN FORENSIC v4.0"
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
        "METHOD      : "
        "TARGETED DYNAMIC SQL BUILDER "
        "SEMANTIC PROPAGATION"
    )

    print()

    print(
        "START POINT : "
        "DYNAMIC WRITE SIGNALS"
    )

    print(
        "CHAIN       : "
        "DYNAMIC WRITE → SQL ARGUMENT → "
        "VARIABLE → BUILDER → PARAMETER → SQL"
    )

    print()

    print(
        "v4.0 REPAIR  : "
        "GLOBAL + LOCAL SYMBOLIC ENVIRONMENT"
    )

    print(
        "v4.0 REPAIR  : "
        "RECURSIVE F-STRING / NAME RESOLUTION"
    )

    print(
        "v4.0 REPAIR  : "
        "DIRECT execute(builder(...)) PROPAGATION"
    )

    print(
        "v4.0 REPAIR  : "
        "CALLER ENVIRONMENT PRESERVATION"
    )

    print(
        "v4.0 REPAIR  : "
        "TARGET FALSE-POSITIVE REDUCTION"
    )

    print()

    print(
        "IMPORTANT   : "
        "NO BROAD GLOBAL DATAFLOW CROSS-PRODUCT"
    )

    print(
        "IMPORTANT   : "
        "NO PRODUCTION EXECUTION"
    )

    print()

    if not ROOT.exists():

        print(
            f"ERROR: ROOT DOES NOT EXIST: {ROOT}"
        )

        return

    # =========================================================================
    # Repository parse
    # =========================================================================

    files = discover_python_files()

    analyses, failures = (
        build_repository_index(
            files
        )
    )

    # =========================================================================
    # Indexes
    # =========================================================================

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

    builder_index = (
        build_builder_index(
            analyses
        )
    )

    # =========================================================================
    # Critical starting point:
    # ONLY dynamic writes
    # =========================================================================

    dynamic_signals = (
        collect_dynamic_write_signals(
            analyses
        )
    )

    # =========================================================================
    # Targeted propagation
    # =========================================================================

    propagation_results = (
        run_targeted_propagation(
            dynamic_signals,
            analyses,
            function_index,
            calls_by_callee,
            builder_index,
        )
    )

    # =========================================================================
    # Report
    # =========================================================================

    print_inventory(
        files,
        analyses,
        failures,
    )

    print_dynamic_signals(
        dynamic_signals
    )

    print_builder_inventory(
        builder_index
    )

    print_propagation_results(
        propagation_results
    )

    print_final_status(
        dynamic_signals,
        propagation_results,
    )

    print_safety()

    separator()

    print(
        "END — RISK_v0.1 ACTUAL DB WRITE "
        "BACKWARD CHAIN FORENSIC v4.0"
    )

    separator()


if __name__ == "__main__":
    main()