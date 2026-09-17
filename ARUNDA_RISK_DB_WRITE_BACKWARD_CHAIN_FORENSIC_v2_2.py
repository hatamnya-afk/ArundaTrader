# -*- coding: utf-8 -*-
"""
ARUNDA — RISK_v0.1 DB WRITE BACKWARD CHAIN FORENSIC v2.2

MODE        : READ ONLY
TARGET      : risk_decisions

SAFETY:
    - No production imports
    - No production execution
    - No database connection
    - No database writes
    - Static source analysis only
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from collections import defaultdict


# =============================================================================
# CONFIGURATION
# =============================================================================

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_TABLE = "risk_decisions"

MAX_CALL_DEPTH = 8

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

BACKUP_MARKERS = {
    "_backup",
    "backup",
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

WRITE_SQL_RE = re.compile(
    r"\b("
    r"INSERT(?:\s+OR\s+\w+)?"
    r"|UPDATE"
    r"|REPLACE"
    r"|UPSERT"
    r")\b",
    re.IGNORECASE,
)

TARGET_RE = re.compile(
    r"\brisk_decisions\b",
    re.IGNORECASE,
)

SQL_VARIABLE_NAMES = {
    "sql",
    "query",
    "statement",
    "stmt",
    "command",
    "insert_sql",
    "update_sql",
    "upsert_sql",
    "insert_query",
    "update_query",
    "query_sql",
}

PARAMETER_NAMES = {
    "values",
    "params",
    "parameters",
    "payload",
    "record",
    "row",
    "rows",
    "data",
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

RISK_FIELDS = {
    "asset",
    "snapshot_id",
    "status",
    "decision",
    "risk_state",
    "risk_score",
    "risk_percent",
    "position_percent",
    "position_value",
    "position_quantity",
    "stop_loss_percent",
    "take_profit_percent",
    "risk_reward",
    "reason",
}


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def line_no(node):
    return getattr(node, "lineno", 0)


def source_window(lines, line, radius=3):
    start = max(1, line - radius)
    end = min(len(lines), line + radius)

    result = []

    for n in range(start, end + 1):
        marker = ">>>" if n == line else "   "
        result.append(
            f"{marker} {n:5d} | {lines[n - 1].rstrip()}"
        )

    return "\n".join(result)


def clean_text(text, limit=700):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def print_separator(char="=", width=102):
    print(char * width)


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
        "_backups" in normalized
        or "\\backup" in normalized
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
# REPOSITORY INVENTORY
# =============================================================================

def discover_python_files():
    files = []

    for path in ROOT.rglob("*.py"):
        if any(
            part.lower() in SKIP_DIR_NAMES
            for part in path.parts
        ):
            continue

        files.append(path)

    return sorted(files)


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

    except SyntaxError as exc:
        return None

    except Exception:
        return None


# =============================================================================
# AST UTILITIES
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

    if isinstance(node, ast.Str):
        return node.s

    return None


def constant_value(node):
    if isinstance(node, ast.Constant):
        return node.value

    return None


def extract_string_fragments(node):
    """
    Best-effort static extraction of string fragments.
    Dynamic expressions are represented as placeholders.
    """

    if node is None:
        return ""

    literal = literal_string(node)

    if literal is not None:
        return literal

    if isinstance(node, ast.JoinedStr):
        pieces = []

        for value in node.values:
            if isinstance(value, ast.Constant):
                pieces.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                name = dotted_name(value.value)

                if name:
                    pieces.append("{" + name + "}")
                else:
                    pieces.append("{DYNAMIC}")

        return "".join(pieces)

    if isinstance(node, ast.BinOp):
        left = extract_string_fragments(node.left)
        right = extract_string_fragments(node.right)

        if isinstance(node.op, ast.Add):
            return left + right

    if isinstance(node, ast.Call):
        fn = dotted_name(node.func)

        if fn and fn.endswith(".format"):
            base = extract_string_fragments(node.func.value)

            return base + " {FORMAT}"

    return ""


def contains_target(text):
    return bool(
        TARGET_RE.search(text or "")
    )


def is_write_sql(text):
    return bool(
        WRITE_SQL_RE.search(text or "")
    )


def sql_operation(text):
    if not text:
        return "UNKNOWN_DYNAMIC"

    match = WRITE_SQL_RE.search(text)

    if not match:
        if re.search(r"\bSELECT\b", text, re.I):
            return "SELECT"

        if re.search(r"\bDELETE\b", text, re.I):
            return "DELETE"

        return "UNKNOWN_DYNAMIC"

    token = match.group(1).upper()

    if token.startswith("INSERT"):
        return "INSERT"

    if token == "UPDATE":
        return "UPDATE"

    if token == "REPLACE":
        return "REPLACE"

    if token == "UPSERT":
        return "UPSERT"

    return "UNKNOWN_DYNAMIC"


def is_sql_write_call(node):
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


def function_name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name

    return "<module>"


# =============================================================================
# CONTEXT INDEX
# =============================================================================

class FunctionInfo:
    def __init__(self, path, node):
        self.path = path
        self.node = node
        self.name = node.name
        self.calls = []
        self.returns = []
        self.assignments = []
        self.write_calls = []


class FileAnalysis:
    def __init__(self, path, source, tree):
        self.path = path
        self.source = source
        self.lines = source.splitlines()
        self.tree = tree
        self.category = classify_file(path)

        self.functions = {}
        self.calls_to_functions = defaultdict(list)

        self.write_candidates = []
        self.target_refs = []
        self.dynamic_table_refs = []
        self.risk_constructions = []
        self.sql_assignments = []
        self.parameter_assignments = []
        self.return_candidates = []


# =============================================================================
# AST WALK
# =============================================================================

class Analyzer(ast.NodeVisitor):

    def __init__(self, analysis):
        self.analysis = analysis
        self.function_stack = []

    @property
    def current_function(self):
        if not self.function_stack:
            return None

        return self.function_stack[-1]

    def visit_FunctionDef(self, node):
        info = FunctionInfo(
            self.analysis.path,
            node,
        )

        self.analysis.functions[node.name] = info

        self.function_stack.append(info)

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Call(self, node):

        # -------------------------------------------------------------
        # Function calls
        # -------------------------------------------------------------

        called = dotted_name(node.func)

        if called:

            base_name = called.split(".")[-1]

            if base_name in self.analysis.functions:
                self.analysis.calls_to_functions[
                    base_name
                ].append(
                    (
                        self.current_function.name
                        if self.current_function
                        else "<module>",
                        line_no(node),
                    )
                )

        # -------------------------------------------------------------
        # SQL execute / executemany / executescript
        # -------------------------------------------------------------

        if is_sql_write_call(node):

            sql_text = ""

            if node.args:
                sql_text = extract_string_fragments(
                    node.args[0]
                )

            operation = sql_operation(sql_text)

            candidate = {
                "path": self.analysis.path,
                "category": self.analysis.category,
                "line": line_no(node),
                "function": (
                    self.current_function.name
                    if self.current_function
                    else "<module>"
                ),
                "method": called,
                "operation": operation,
                "sql": clean_text(sql_text),
                "target": contains_target(sql_text),
                "args": node.args,
                "node": node,
            }

            self.analysis.write_candidates.append(
                candidate
            )

            if self.current_function:
                self.current_function.write_calls.append(
                    candidate
                )

        # -------------------------------------------------------------
        # Target references
        # -------------------------------------------------------------

        text = extract_string_fragments(node)

        if contains_target(text):

            self.analysis.target_refs.append(
                {
                    "path": self.analysis.path,
                    "category": self.analysis.category,
                    "line": line_no(node),
                    "function": (
                        self.current_function.name
                        if self.current_function
                        else "<module>"
                    ),
                    "text": clean_text(text),
                }
            )

        self.generic_visit(node)

    def visit_Assign(self, node):

        value_text = extract_string_fragments(
            node.value
        )

        target_names = []

        for target in node.targets:

            if isinstance(target, ast.Name):
                target_names.append(target.id)

            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        target_names.append(elt.id)

        for name in target_names:

            lowered = name.lower()

            if (
                lowered in SQL_VARIABLE_NAMES
                or "sql" in lowered
                or "query" in lowered
                or "statement" in lowered
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
                    "variable": name,
                    "value": clean_text(value_text),
                    "contains_target": contains_target(
                        value_text
                    ),
                    "write": is_write_sql(value_text),
                }

                self.analysis.sql_assignments.append(
                    record
                )

            if (
                lowered in PARAMETER_NAMES
                or lowered in RISK_NAMES
                or "risk" in lowered
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
                    "variable": name,
                    "value": clean_text(value_text),
                    "risk_related": (
                        lowered in RISK_NAMES
                        or "risk" in lowered
                    ),
                }

                self.analysis.parameter_assignments.append(
                    record
                )

            if lowered in RISK_NAMES or "risk" in lowered:

                self.analysis.risk_constructions.append(
                    {
                        "path": self.analysis.path,
                        "category": self.analysis.category,
                        "line": line_no(node),
                        "function": (
                            self.current_function.name
                            if self.current_function
                            else "<module>"
                        ),
                        "variable": name,
                        "value": clean_text(value_text),
                    }
                )

        # -------------------------------------------------------------
        # Dynamic table assignment
        # -------------------------------------------------------------

        for name in target_names:

            lowered = name.lower()

            if (
                lowered in {
                    "table",
                    "table_name",
                    "target_table",
                    "db_table",
                    "sql_table",
                    "destination",
                    "destination_table",
                }
                or lowered.endswith("_table")
            ):

                self.analysis.dynamic_table_refs.append(
                    {
                        "path": self.analysis.path,
                        "category": self.analysis.category,
                        "line": line_no(node),
                        "function": (
                            self.current_function.name
                            if self.current_function
                            else "<module>"
                        ),
                        "variable": name,
                        "value": clean_text(value_text),
                        "resolved_target": contains_target(
                            value_text
                        ),
                    }
                )

        self.generic_visit(node)

    def visit_Return(self, node):

        text = extract_string_fragments(
            node.value
        )

        if (
            contains_target(text)
            or any(
                word in text.lower()
                for word in (
                    "risk",
                    "record",
                    "values",
                    "params",
                    "payload",
                    "snapshot",
                )
            )
        ):

            self.analysis.return_candidates.append(
                {
                    "path": self.analysis.path,
                    "category": self.analysis.category,
                    "line": line_no(node),
                    "function": (
                        self.current_function.name
                        if self.current_function
                        else "<module>"
                    ),
                    "value": clean_text(text),
                }
            )

        self.generic_visit(node)


# =============================================================================
# FILE ANALYSIS
# =============================================================================

def analyze_file(path):
    source = read_source(path)

    if source is None:
        return None, "READ_FAILURE"

    tree = parse_source(source, path)

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
# GLOBAL INDEX
# =============================================================================

def build_index(files):

    analyses = []

    ast_failures = []

    for path in files:

        analysis, error = analyze_file(path)

        if analysis is not None:
            analyses.append(analysis)

        elif error == "AST_FAILURE":
            ast_failures.append(path)

    return analyses, ast_failures


# =============================================================================
# WRITE CANDIDATE SCORING
# =============================================================================

def score_candidate(candidate):

    score = 0
    reasons = []

    category = candidate["category"]
    operation = candidate["operation"]
    sql = candidate["sql"]

    if category == "PRODUCTION":
        score += 40
        reasons.append("PRODUCTION")

    elif category == "FORENSIC":
        score += 10
        reasons.append("FORENSIC")

    elif category == "BACKUP":
        score += 5
        reasons.append("BACKUP")

    if operation in {
        "INSERT",
        "UPDATE",
        "REPLACE",
        "UPSERT",
    }:
        score += 30
        reasons.append("WRITE_SQL")

    if contains_target(sql):
        score += 40
        reasons.append("DIRECT_TARGET")

    return score, reasons


# =============================================================================
# TARGET WRITE DISCOVERY
# =============================================================================

def collect_target_writes(analyses):

    results = []

    for analysis in analyses:

        for candidate in analysis.write_candidates:

            score, reasons = score_candidate(
                candidate
            )

            item = dict(candidate)

            item["score"] = score
            item["reasons"] = reasons

            results.append(item)

    results.sort(
        key=lambda item: (
            -item["score"],
            str(item["path"]),
            item["line"],
        )
    )

    return results


# =============================================================================
# CONSUMER DETECTION
# =============================================================================

def collect_target_reads(analyses):

    reads = []

    for analysis in analyses:

        for ref in analysis.target_refs:

            text = ref["text"]

            if (
                re.search(
                    r"\bSELECT\b",
                    text,
                    re.I,
                )
                and contains_target(text)
            ):

                reads.append(ref)

    return reads


# =============================================================================
# DYNAMIC TARGET ANALYSIS
# =============================================================================

def dynamic_target_summary(analyses):

    results = []

    for analysis in analyses:

        for item in analysis.dynamic_table_refs:

            value = item["value"]

            if (
                item["resolved_target"]
                or "table" in item["variable"].lower()
            ):

                results.append(item)

    return results


# =============================================================================
# SQL VARIABLE FLOW
# =============================================================================

def sql_variable_flow(analyses):

    results = []

    for analysis in analyses:

        for item in analysis.sql_assignments:

            if (
                item["write"]
                or item["contains_target"]
                or item["category"] == "PRODUCTION"
            ):
                results.append(item)

    return results


# =============================================================================
# PARAMETER FLOW
# =============================================================================

def parameter_flow(analyses):

    results = []

    for analysis in analyses:

        for item in analysis.parameter_assignments:

            if item["risk_related"]:
                results.append(item)

    return results


# =============================================================================
# RISK OBJECT FLOW
# =============================================================================

def risk_object_flow(analyses):

    results = []

    for analysis in analyses:

        for item in analysis.risk_constructions:
            results.append(item)

    return results


# =============================================================================
# RETURN FLOW
# =============================================================================

def return_flow(analyses):

    results = []

    for analysis in analyses:

        for item in analysis.return_candidates:
            results.append(item)

    return results


# =============================================================================
# FIELD ASSIGNMENT FORENSICS
# =============================================================================

def collect_risk_field_assignments(analyses):

    results = []

    for analysis in analyses:

        source = analysis.source

        try:
            tree = analysis.tree
        except Exception:
            continue

        class FieldVisitor(ast.NodeVisitor):

            def visit_Assign(self, node):

                for target in node.targets:

                    if isinstance(target, ast.Subscript):

                        base = dotted_name(
                            target.value
                        )

                        if base:

                            text = extract_string_fragments(
                                target.slice
                            )

                            if (
                                text
                                and text.lower()
                                in RISK_FIELDS
                            ):

                                results.append(
                                    {
                                        "path": analysis.path,
                                        "category": analysis.category,
                                        "line": line_no(node),
                                        "function": "<unknown>",
                                        "field": text,
                                        "target": base,
                                    }
                                )

                self.generic_visit(node)

            def visit_Dict(self, node):

                for key, value in zip(
                    node.keys,
                    node.values,
                ):

                    key_text = literal_string(key)

                    if (
                        key_text
                        and key_text.lower()
                        in RISK_FIELDS
                    ):

                        results.append(
                            {
                                "path": analysis.path,
                                "category": analysis.category,
                                "line": line_no(node),
                                "function": "<unknown>",
                                "field": key_text,
                                "target": "dict",
                            }
                        )

                self.generic_visit(node)

        FieldVisitor().visit(tree)

    return results


# =============================================================================
# CALLER FLOW
# =============================================================================

def build_global_function_index(analyses):

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


def collect_callers(analyses):

    callers = defaultdict(list)

    function_names = set()

    for analysis in analyses:
        function_names.update(
            analysis.functions.keys()
        )

    for analysis in analyses:

        for node in ast.walk(analysis.tree):

            if not isinstance(node, ast.Call):
                continue

            called = dotted_name(node.func)

            if not called:
                continue

            short = called.split(".")[-1]

            if short in function_names:

                caller = "<module>"

                for fn in analysis.functions.values():

                    if (
                        fn.node.lineno
                        <= line_no(node)
                        <= (
                            getattr(
                                fn.node,
                                "end_lineno",
                                fn.node.lineno,
                            )
                        )
                    ):
                        caller = fn.name
                        break

                callers[short].append(
                    {
                        "path": analysis.path,
                        "category": analysis.category,
                        "caller": caller,
                        "line": line_no(node),
                    }
                )

    return callers


# =============================================================================
# PRINT SECTIONS
# =============================================================================

def print_inventory(files, analyses, ast_failures):

    categories = defaultdict(int)

    for path in files:
        categories[
            classify_file(path)
        ] += 1

    print_separator()
    print("1) REPOSITORY INVENTORY")
    print_separator()

    print(f"PYTHON FILES       : {len(files)}")
    print(f"ANALYZED FILES     : {len(analyses)}")
    print(f"AST FAILURES       : {len(ast_failures)}")
    print(f"PRODUCTION FILES   : {categories['PRODUCTION']}")
    print(f"FORENSIC FILES     : {categories['FORENSIC']}")
    print(f"BACKUP FILES       : {categories['BACKUP']}")
    print(f"QUARANTINE FILES   : {categories['QUARANTINE']}")

    if ast_failures:

        print()
        print("AST FAILURES:")

        for path in ast_failures[:100]:
            print(f"  {path}")

        if len(ast_failures) > 100:
            print(
                f"  ... {len(ast_failures) - 100} more"
            )


def print_write_candidates(candidates, analyses):

    print_separator()
    print("2) WRITE EXECUTE CANDIDATES")
    print_separator()

    print(
        f"WRITE EXECUTE CANDIDATES : "
        f"{len(candidates)}"
    )

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        print()
        print("-" * 102)
        print(f"CANDIDATE #{index}")
        print(f"SCORE    : {item['score']}")
        print(f"FILE     : {item['path']}")
        print(f"TYPE     : {item['category']}")
        print(f"LINE     : {item['line']}")
        print(f"FUNCTION : {item['function']}")
        print(f"METHOD   : {item['method']}")
        print(f"OPERATION: {item['operation']}")
        print(
            f"REASONS  : "
            f"{', '.join(item['reasons'])}"
        )
        print(f"SQL      : {item['sql']}")

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
                    radius=5,
                )
            )


def print_direct_target_refs(analyses):

    print_separator()
    print("3) DIRECT risk_decisions REFERENCES")
    print_separator()

    refs = []

    for analysis in analyses:

        for ref in analysis.target_refs:

            refs.append(ref)

    print(
        f"TARGET REFERENCES : {len(refs)}"
    )

    for item in refs:

        print()
        print(
            f"{item['category']:<12} "
            f"{item['path']} :: "
            f"LINE {item['line']} :: "
            f"{item['function']}"
        )

        print(
            f"  {item['text']}"
        )


def print_dynamic_tables(analyses):

    results = dynamic_target_summary(
        analyses
    )

    print_separator()
    print("4) DYNAMIC TABLE REFERENCES")
    print_separator()

    print(
        f"DYNAMIC TABLE REFERENCES : "
        f"{len(results)}"
    )

    for item in results:

        print()
        print(
            f"{item['category']:<12} "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )
        print(
            f"VARIABLE : {item['variable']}"
        )
        print(
            f"VALUE    : {item['value']}"
        )
        print(
            f"TARGET   : "
            f"{item['resolved_target']}"
        )


def print_sql_flow(analyses):

    results = sql_variable_flow(
        analyses
    )

    print_separator()
    print("5) SQL VARIABLE FLOW")
    print_separator()

    print(
        f"SQL VARIABLE REFERENCES : "
        f"{len(results)}"
    )

    for item in results:

        print()
        print(
            f"{item['category']:<12} "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )
        print(
            f"VARIABLE : {item['variable']}"
        )
        print(
            f"VALUE    : {item['value']}"
        )
        print(
            f"WRITE    : {item['write']}"
        )
        print(
            f"TARGET   : {item['contains_target']}"
        )


def print_parameter_flow(analyses):

    results = parameter_flow(
        analyses
    )

    print_separator()
    print("6) PARAMETER / VALUES FLOW")
    print_separator()

    print(
        f"RISK-RELATED PARAMETER REFERENCES : "
        f"{len(results)}"
    )

    for item in results:

        print()
        print(
            f"{item['category']:<12} "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )
        print(
            f"VARIABLE : {item['variable']}"
        )
        print(
            f"VALUE    : {item['value']}"
        )


def print_risk_flow(analyses):

    results = risk_object_flow(
        analyses
    )

    print_separator()
    print("7) RISK OBJECT CONSTRUCTION")
    print_separator()

    print(
        f"RISK OBJECT REFERENCES : "
        f"{len(results)}"
    )

    for item in results:

        print()
        print(
            f"{item['category']:<12} "
            f"{item['path']} :: "
            f"LINE {item['line']}"
        )
        print(
            f"VARIABLE : {item['variable']}"
        )
        print(
            f"VALUE    : {item['value']}"
        )


def print_returns(analyses):

    results = return_flow(
        analyses
    )

    print_separator()
    print("8) FUNCTION RETURN FLOW")
    print_separator()

    print(
        f"RETURN CANDIDATES : "
        f"{len(results)}"
    )

    for item in results:

        print()
        print(
            f"{item['category']:<12} "
            f"{item['path']} :: "
            f"LINE {item['line']} :: "
            f"{item['function']}"
        )
        print(
            f"RETURN : {item['value']}"
        )


def print_callers(analyses):

    callers = collect_callers(
        analyses
    )

    print_separator()
    print("9) CALLER FLOW")
    print_separator()

    total = sum(
        len(value)
        for value in callers.values()
    )

    print(
        f"CALLER REFERENCES : {total}"
    )

    for function_name, records in sorted(
        callers.items()
    ):

        if not (
            "risk" in function_name.lower()
            or function_name
            in {
                "get_risk",
                "save_result",
                "build_risk_snapshot",
                "evaluate_risk",
            }
        ):
            continue

        print()
        print(
            f"FUNCTION : {function_name}"
        )

        for record in records:

            print(
                f"  {record['category']:<12} "
                f"{record['path']} :: "
                f"LINE {record['line']} :: "
                f"CALLER {record['caller']}"
            )


def print_producer_ranking(candidates):

    target_writes = [
        item
        for item in candidates
        if item["target"]
    ]

    production = [
        item
        for item in target_writes
        if item["category"] == "PRODUCTION"
    ]

    high = [
        item
        for item in production
        if item["score"] >= 100
    ]

    medium = [
        item
        for item in production
        if 70 <= item["score"] < 100
    ]

    low = [
        item
        for item in production
        if item["score"] < 70
    ]

    print_separator()
    print("10) PRODUCER CANDIDATE RANKING")
    print_separator()

    print(
        f"TARGET WRITE CANDIDATES : "
        f"{len(target_writes)}"
    )
    print(
        f"PRODUCTION TARGET WRITES : "
        f"{len(production)}"
    )
    print(f"HIGH   : {len(high)}")
    print(f"MEDIUM : {len(medium)}")
    print(f"LOW    : {len(low)}")

    for index, item in enumerate(
        target_writes,
        start=1,
    ):

        print()
        print(
            f"CANDIDATE #{index}"
        )
        print(
            f"  SCORE    : {item['score']}"
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
        print(
            f"  OPERATION: {item['operation']}"
        )
        print(
            f"  SQL      : {item['sql']}"
        )

    print_separator()
    print("11) PRODUCER STATUS")
    print_separator()

    if high:

        best = high[0]

        print(
            "RESULT : PRODUCTION WRITE CANDIDATE "
            "WITH HIGH STATIC CONFIDENCE"
        )

        print()
        print(
            "IMPORTANT: HIGH STATIC CONFIDENCE "
            "IS NOT YET A DECLARED PRODUCER."
        )

        print(
            "The SQL target and parameter flow "
            "must still be resolved."
        )

        print()
        print(
            f"FILE     : {best['path']}"
        )
        print(
            f"FUNCTION : {best['function']}"
        )
        print(
            f"LINE     : {best['line']}"
        )

    elif medium:

        print(
            "RESULT : PRODUCTION WRITE CANDIDATE(S) "
            "FOUND"
        )

        print(
            "PRODUCER STATUS : NOT DECLARED"
        )

        print(
            "NEXT TARGET : Resolve SQL target "
            "and parameter/object flow."
        )

    else:

        print(
            "RESULT : PRODUCER NOT YET RESOLVED"
        )

        print(
            "PRODUCER STATUS : NOT DECLARED"
        )

        print(
            "NEXT TARGET : Resolve dynamic SQL/table "
            "writer path."
        )


def print_consumer_classification(analyses):

    reads = collect_target_reads(
        analyses
    )

    print_separator()
    print("12) CONSUMER / PRODUCER SEPARATION")
    print_separator()

    print(
        f"SELECT CONSUMERS FOUND : "
        f"{len(reads)}"
    )

    for item in reads:

        print()
        print(
            f"CONSUMER : {item['path']}"
        )
        print(
            f"FUNCTION : {item['function']}"
        )
        print(
            f"LINE     : {item['line']}"
        )
        print(
            f"SQL      : {item['text']}"
        )

    print()
    print(
        "KNOWN CLASSIFICATION:"
    )
    print(
        "trade_gate_engine.get_risk() "
        "= CONSUMER / READER"
    )


def print_safety():

    print_separator()
    print("SAFETY")
    print_separator()

    print("STATIC SOURCE ANALYSIS ONLY")
    print("NO PRODUCTION MODULE IMPORT")
    print("NO PRODUCTION FUNCTION EXECUTION")
    print("NO DATABASE CONNECTION")
    print("NO INSERT")
    print("NO UPDATE")
    print("NO DELETE")
    print("NO ALTER")
    print("NO CREATE")
    print("NO COMMIT")
    print("NO NETWORK")
    print("NO ORDER")
    print("NO TRADE")

    print_separator()


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_separator()

    print(
        "ARUNDA — RISK_v0.1 DB WRITE "
        "BACKWARD CHAIN FORENSIC v2.2"
    )

    print_separator()

    print(f"MODE        : READ ONLY")
    print(f"ROOT        : {ROOT}")
    print(f"TARGET      : {TARGET_TABLE}")
    print(
        "OBJECTIVE   : Resolve exact production "
        "DB write producer and backward flow"
    )

    print_separator()

    if not ROOT.exists():

        print(
            f"ERROR: ROOT DOES NOT EXIST: {ROOT}"
        )

        return

    files = discover_python_files()

    analyses, ast_failures = build_index(
        files
    )

    candidates = collect_target_writes(
        analyses
    )

    print_inventory(
        files,
        analyses,
        ast_failures,
    )

    print_write_candidates(
        candidates,
        analyses,
    )

    print_direct_target_refs(
        analyses
    )

    print_dynamic_tables(
        analyses
    )

    print_sql_flow(
        analyses
    )

    print_parameter_flow(
        analyses
    )

    print_risk_flow(
        analyses
    )

    print_returns(
        analyses
    )

    print_callers(
        analyses
    )

    print_producer_ranking(
        candidates
    )

    print_consumer_classification(
        analyses
    )

    print_safety()

    print(
        "END — RISK_v0.1 DB WRITE BACKWARD "
        "CHAIN FORENSIC v2.2"
    )

    print_separator()


if __name__ == "__main__":
    main()