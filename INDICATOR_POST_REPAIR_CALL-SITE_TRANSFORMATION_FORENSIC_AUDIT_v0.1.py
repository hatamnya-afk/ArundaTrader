import ast
import inspect
import os
import re
import sqlite3
import traceback
from datetime import datetime, timezone


# =============================================================================
# ARUNDA INDICATOR POST-REPAIR CALL-SITE TRANSFORMATION FORENSIC AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Trace the production path AFTER the previously confirmed direct
# calculate_analysis() return difference.
#
# FRONTIER
# --------
# stored DB value
#       |
#       v
# production call-site
#       |
#       v
# call-site input construction
#       |
#       v
# calculate_analysis()
#       |
#       v
# returned indicator
#       |
#       v
# post-calculation transformation
#       |
#       v
# rounding / casting / normalization
#       |
#       v
# database assignment / SQL parameter
#
# SAFETY
# ------
# READ ONLY
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
# NO VACUUM
# NO COMMIT
# NO PRODUCTION ENGINE MODIFICATION
#
# This script performs:
#   - source AST inspection
#   - SQL/schema inspection
#   - production call-site discovery
#   - static assignment tracing
#   - database read-only comparison
#
# =============================================================================


ENGINE_PATH = r"C:\Users\ASUS\ArundaTrader\market_data_engine.py"
DATABASE_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

TARGET_INDICATORS = [
    "ema20",
    "ema50",
    "rsi14",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr14",
    "adx14",
    "bb_middle",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "volume_sma20",
    "volume_ratio",
    "volatility",
    "technical_score",
]


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

WIDTH = 100


def line():
    print("=" * WIDTH)


def section(title):
    print()
    line()
    print(title)
    line()


def subsection(title):
    print()
    print("-" * WIDTH)
    print(title)
    print("-" * WIDTH)


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def normalize_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def compare_values(stored, produced):
    s = normalize_float(stored)
    p = normalize_float(produced)

    if s is None or p is None:
        return {
            "stored": stored,
            "produced": produced,
            "abs_error": None,
            "rel_error": None,
            "match": stored == produced,
        }

    abs_error = abs(s - p)

    if s != 0:
        rel_error = abs_error / abs(s)
    else:
        rel_error = 0.0 if abs_error == 0 else float("inf")

    return {
        "stored": s,
        "produced": p,
        "abs_error": abs_error,
        "rel_error": rel_error,
        "match": abs_error == 0.0,
    }


# =============================================================================
# AST HELPERS
# =============================================================================

def get_source_lines(source):
    return source.splitlines()


def node_line(node):
    return getattr(node, "lineno", None)


def node_end_line(node):
    return getattr(node, "end_lineno", None)


def ast_segment(source, node):
    try:
        segment = ast.get_source_segment(source, node)
        if segment is None:
            return ""
        return segment
    except Exception:
        return ""


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return left + "." + node.attr
        return node.attr

    return ""


def assignment_targets(node):
    targets = []

    if isinstance(node, ast.Assign):
        raw_targets = node.targets

    elif isinstance(node, ast.AnnAssign):
        raw_targets = [node.target]

    elif isinstance(node, ast.AugAssign):
        raw_targets = [node.target]

    else:
        return targets

    for target in raw_targets:
        if isinstance(target, ast.Name):
            targets.append(target.id)

        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                if isinstance(item, ast.Name):
                    targets.append(item.id)
                else:
                    targets.append(ast_segment("", item))

        elif isinstance(target, ast.Attribute):
            targets.append(dotted_name(target))

        else:
            targets.append(ast_segment("", target))

    return targets


def constant_strings(node):
    result = []

    for child in ast.walk(node):
        if isinstance(child, ast.Constant):
            if isinstance(child.value, str):
                result.append(child.value)

    return result


# =============================================================================
# SOURCE LOADING
# =============================================================================

def load_engine_source():
    section("STEP 1 — PATH RESOLUTION")

    print(f"ENGINE PATH                 : {ENGINE_PATH}")
    print(f"ENGINE FOUND                : {os.path.exists(ENGINE_PATH)}")

    print(f"DATABASE PATH               : {DATABASE_PATH}")
    print(f"DATABASE FOUND              : {os.path.exists(DATABASE_PATH)}")

    if not os.path.exists(ENGINE_PATH):
        raise FileNotFoundError(
            f"Engine not found: {ENGINE_PATH}"
        )

    if not os.path.exists(DATABASE_PATH):
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    with open(
        ENGINE_PATH,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as f:
        source = f.read()

    print(f"SOURCE SIZE                 : {len(source)} characters")
    print(f"SOURCE LINES                : {len(source.splitlines())}")

    return source


def parse_source(source):
    section("STEP 2 — AST RESOLUTION")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print("AST STATUS                  : FAILED")
        print(f"SYNTAX ERROR                : {exc}")
        raise

    print("AST STATUS                  : SUCCESS")

    functions = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(
                (
                    node.name,
                    node.lineno,
                    node.end_lineno,
                )
            )

    functions.sort(
        key=lambda x: (
            x[1] if x[1] is not None else 0
        )
    )

    print(
        f"FUNCTIONS DISCOVERED       : {len(functions)}"
    )

    for name, start, end in functions:
        if name in {
            "calculate_analysis",
            "ema",
            "ema_series",
            "rsi",
            "macd",
            "atr",
            "adx",
            "bollinger",
            "volume_metrics",
            "volatility",
            "technical_score",
        }:
            print(
                f"[FOUND] {name} LINE {start}-{end}"
            )

    return tree


# =============================================================================
# FUNCTION DISCOVERY
# =============================================================================

def find_function_nodes(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result[node.name] = node

    return result


# =============================================================================
# CALL-SITE DISCOVERY
# =============================================================================

def find_calculate_analysis_calls(
    source,
    tree,
):
    section(
        "STEP 3 — CALCULATE_ANALYSIS PRODUCTION CALL-SITE DISCOVERY"
    )

    calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function_name = dotted_name(node.func)

        if function_name.endswith(
            "calculate_analysis"
        ):
            calls.append(node)

    print(
        f"CALCULATE_ANALYSIS CALL-SITES : {len(calls)}"
    )

    if not calls:
        print(
            "STATUS                      : CALL_SITE_NOT_FOUND"
        )
        return []

    for index, call in enumerate(calls, 1):
        print()
        print(
            f"[CALL-SITE {index}]"
        )

        print(
            f"LINE                        : {node_line(call)}"
        )

        print(
            f"FUNCTION                    : "
            f"{dotted_name(call.func)}"
        )

        print(
            "SOURCE                      :"
        )

        text = ast_segment(source, call)

        for line_text in text.splitlines():
            print(
                f"    {line_text}"
            )

        print(
            "ARGUMENTS                   :"
        )

        for arg_index, arg in enumerate(
            call.args,
            1,
        ):
            print(
                f"    ARG {arg_index}             : "
                f"{ast_segment(source, arg)}"
            )

        for keyword in call.keywords:
            print(
                f"    KW {keyword.arg}             : "
                f"{ast_segment(source, keyword.value)}"
            )

    return calls


# =============================================================================
# ENCLOSING FUNCTION
# =============================================================================

def enclosing_function(tree, target_node):
    candidates = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        start = node.lineno
        end = node.end_lineno

        if (
            start is not None
            and end is not None
            and start <= target_node.lineno <= end
        ):
            candidates.append(node)

    if not candidates:
        return None

    candidates.sort(
        key=lambda n: (
            n.end_lineno - n.lineno
        )
    )

    return candidates[0]


# =============================================================================
# CALL-SITE INPUT CONSTRUCTION TRACE
# =============================================================================

def trace_callsite_input_construction(
    source,
    tree,
    call,
):
    subsection(
        "CALL-SITE INPUT CONSTRUCTION TRACE"
    )

    function_node = enclosing_function(
        tree,
        call,
    )

    if function_node is None:
        print(
            "ENCLOSING FUNCTION           : NOT FOUND"
        )
        return

    print(
        f"ENCLOSING FUNCTION           : "
        f"{function_node.name}"
    )

    print(
        f"FUNCTION LINES               : "
        f"{function_node.lineno}-"
        f"{function_node.end_lineno}"
    )

    call_arguments = []

    for arg in call.args:
        if isinstance(arg, ast.Name):
            call_arguments.append(arg.id)

    for keyword in call.keywords:
        if isinstance(keyword.value, ast.Name):
            call_arguments.append(
                keyword.value.id
            )

    if not call_arguments:
        print(
            "DIRECT VARIABLE ARGUMENTS    : NONE"
        )
    else:
        print(
            "DIRECT VARIABLE ARGUMENTS    :"
        )

        for name in call_arguments:
            print(
                f"    {name}"
            )

    relevant = []

    for node in function_node.body:
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.AugAssign,
                ),
            ):
                targets = assignment_targets(
                    child
                )

                if any(
                    name in targets
                    for name in call_arguments
                ):
                    relevant.append(child)

    if relevant:
        print()
        print(
            "VARIABLE ASSIGNMENTS RELATED TO CALL:"
        )

        for node in sorted(
            relevant,
            key=lambda n: (
                n.lineno
                if n.lineno is not None
                else 0
            ),
        ):
            print(
                f"LINE {node.lineno:<5} | "
                f"{ast_segment(source, node)}"
            )

    # Also inspect every statement immediately
    # preceding the calculate_analysis call.
    print()
    print(
        "STATEMENTS IMMEDIATELY BEFORE CALL:"
    )

    body_nodes = []

    for node in ast.walk(function_node):
        if hasattr(node, "body") and isinstance(
            node.body,
            list,
        ):
            for child in node.body:
                body_nodes.append(child)

    body_nodes.sort(
        key=lambda n: (
            n.lineno
            if n.lineno is not None
            else 0
        )
    )

    previous = [
        node
        for node in body_nodes
        if (
            node.lineno is not None
            and node.lineno < call.lineno
        )
    ]

    for node in previous[-10:]:
        print(
            f"LINE {node.lineno:<5} | "
            f"{ast_segment(source, node)}"
        )


# =============================================================================
# RETURN ASSIGNMENT TRACE
# =============================================================================

def trace_return_assignment(
    source,
    tree,
    call,
):
    subsection(
        "POST-CALCULATION RETURN ASSIGNMENT TRACE"
    )

    function_node = enclosing_function(
        tree,
        call,
    )

    if function_node is None:
        return

    # Find assignments where RHS contains
    # calculate_analysis().
    matches = []

    for node in ast.walk(function_node):
        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
            ),
        ):
            for child in ast.walk(node):
                if child is call:
                    matches.append(node)
                    break

    if not matches:
        print(
            "DIRECT RETURN ASSIGNMENT      : NOT FOUND"
        )
    else:
        for node in matches:
            print(
                f"LINE {node.lineno:<5} | "
                f"{ast_segment(source, node)}"
            )


# =============================================================================
# POST-CALCULATION TRANSFORMATION DISCOVERY
# =============================================================================

TRANSFORMATION_NAMES = {
    "round",
    "float",
    "int",
    "str",
    "Decimal",
    "abs",
    "min",
    "max",
    "format",
    "numpy.round",
    "np.round",
}


def trace_post_calculation_transformations(
    source,
    tree,
):
    section(
        "STEP 4 — POST-CALCULATION TRANSFORMATION DISCOVERY"
    )

    findings = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Call,
        ):
            name = dotted_name(node.func)

            if (
                name in TRANSFORMATION_NAMES
                or name.endswith(".round")
                or name.endswith(".astype")
                or name.endswith(".item")
            ):
                findings.append(
                    (
                        node.lineno,
                        name,
                        ast_segment(source, node),
                    )
                )

        elif isinstance(
            node,
            ast.Assign,
        ):
            text = ast_segment(
                source,
                node,
            )

            lowered = text.lower()

            keywords = [
                "round(",
                "float(",
                "int(",
                "decimal",
                "astype",
                "item(",
                "format(",
                "quantize(",
            ]

            if any(
                key in lowered
                for key in keywords
            ):
                findings.append(
                    (
                        node.lineno,
                        "ASSIGNMENT_TRANSFORMATION",
                        text,
                    )
                )

    # Remove duplicates
    unique = []
    seen = set()

    for item in findings:
        key = item

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    unique.sort(
        key=lambda x: (
            x[0] if x[0] is not None else 0
        )
    )

    if not unique:
        print(
            "TRANSFORMATIONS FOUND        : 0"
        )
        return

    print(
        f"TRANSFORMATIONS FOUND        : "
        f"{len(unique)}"
    )

    for line_number, name, text in unique:
        print()
        print(
            f"LINE {line_number:<5} | "
            f"{name}"
        )
        print(
            f"    {text}"
        )


# =============================================================================
# INDICATOR DICT ASSIGNMENT TRACE
# =============================================================================

def trace_indicator_assignments(
    source,
    tree,
):
    section(
        "STEP 5 — INDICATOR RETURN / DICT / ATTRIBUTE ASSIGNMENT TRACE"
    )

    indicator_hits = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Subscript,
        ):
            text = ast_segment(
                source,
                node,
            )

            for indicator in TARGET_INDICATORS:
                if (
                    f"'{indicator}'" in text
                    or f'"{indicator}"' in text
                ):
                    indicator_hits.append(
                        (
                            node.lineno,
                            indicator,
                            text,
                        )
                    )

        elif isinstance(
            node,
            ast.Constant,
        ):
            if (
                isinstance(
                    node.value,
                    str,
                )
                and node.value
                in TARGET_INDICATORS
            ):
                parent_text = ""

                # Parent lookup is not directly
                # available in AST. The constant itself
                # is therefore recorded as a key hit.
                indicator_hits.append(
                    (
                        node.lineno,
                        node.value,
                        parent_text,
                    )
                )

    unique = []
    seen = set()

    for item in indicator_hits:
        if item in seen:
            continue

        seen.add(item)
        unique.append(item)

    unique.sort(
        key=lambda x: (
            x[0] if x[0] is not None else 0
        )
    )

    for line_number, indicator, text in unique:
        print(
            f"LINE {line_number:<5} | "
            f"{indicator:<18} | "
            f"{text}"
        )


# =============================================================================
# SQL WRITE-PATH STATIC AUDIT
# =============================================================================

SQL_WRITE_WORDS = {
    "insert",
    "update",
    "delete",
    "alter",
    "create",
    "drop",
    "replace",
    "vacuum",
}


def audit_sql_write_paths(
    source,
    tree,
):
    section(
        "STEP 6 — DATABASE ASSIGNMENT / SQL WRITE-PATH FORENSICS"
    )

    findings = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Call,
        ):
            function_name = dotted_name(
                node.func
            )

            if function_name.endswith(
                (
                    ".execute",
                    ".executemany",
                    ".executescript",
                )
            ):
                text = ast_segment(
                    source,
                    node,
                )

                lowered = text.lower()

                if any(
                    re.search(
                        r"\b" + word + r"\b",
                        lowered,
                    )
                    for word
                    in SQL_WRITE_WORDS
                ):
                    findings.append(
                        (
                            node.lineno,
                            function_name,
                            text,
                        )
                    )

    if not findings:
        print(
            "WRITE-PATH REFERENCES          : NONE FOUND"
        )
        return

    print(
        f"WRITE-PATH REFERENCES          : "
        f"{len(findings)}"
    )

    for line_number, function_name, text in findings:
        print()
        print(
            f"LINE {line_number:<5} | "
            f"{function_name}"
        )
        print(
            f"    {text}"
        )


# =============================================================================
# DATABASE READ-ONLY CONNECTION
# =============================================================================

def readonly_connection():
    uri = (
        "file:"
        + DATABASE_PATH.replace(
            "\\",
            "/",
        )
        + "?mode=ro"
    )

    return sqlite3.connect(
        uri,
        uri=True,
    )


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

def inspect_database_schema():
    section(
        "STEP 7 — READ-ONLY DATABASE SCHEMA RESOLUTION"
    )

    conn = readonly_connection()

    try:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        print(
            f"TABLE COUNT                 : "
            f"{len(tables)}"
        )

        for row in tables:
            print(
                f"  {row[0]}"
            )

    finally:
        conn.close()


# =============================================================================
# FIND LATEST TARGET ROWS
# =============================================================================

def get_latest_market_data_rows():
    section(
        "STEP 8 — STORED PRODUCTION TARGET RESOLUTION"
    )

    conn = readonly_connection()

    result = {}

    try:
        columns = conn.execute(
            "PRAGMA table_info(market_data)"
        ).fetchall()

        column_names = [
            row[1]
            for row in columns
        ]

        print(
            f"MARKET_DATA COLUMNS         : "
            f"{len(column_names)}"
        )

        required = {
            "id",
            "timestamp",
            "symbol",
            "close",
        }

        missing = sorted(
            required
            - set(column_names)
        )

        if missing:
            print(
                f"REQUIRED COLUMNS MISSING    : "
                f"{missing}"
            )
            return result

        select_columns = [
            "id",
            "timestamp",
            "symbol",
            "close",
        ]

        for indicator in TARGET_INDICATORS:
            if indicator in column_names:
                select_columns.append(
                    indicator
                )

        if "engine_version" in column_names:
            select_columns.append(
                "engine_version"
            )

        query = (
            "SELECT "
            + ", ".join(
                '"' + c + '"'
                for c in select_columns
            )
            + """
              FROM market_data
              WHERE symbol = ?
              ORDER BY id DESC
              LIMIT 1
            """
        )

        for symbol in TARGET_SYMBOLS:

            row = conn.execute(
                query,
                (symbol,),
            ).fetchone()

            if row is None:
                print()
                print(
                    f"[MISSING] {symbol}"
                )
                continue

            record = dict(
                zip(
                    select_columns,
                    row,
                )
            )

            result[symbol] = record

            print()
            print(
                f"[FOUND] {symbol}"
            )

            for key in select_columns:
                print(
                    f"    {key:<20}: "
                    f"{record.get(key)}"
                )

    finally:
        conn.close()

    return result


# =============================================================================
# SEARCH SOURCE FOR TARGET-SPECIFIC DATABASE ASSIGNMENTS
# =============================================================================

def target_assignment_search(
    source,
):
    section(
        "STEP 9 — TARGET INDICATOR DATABASE ASSIGNMENT SEARCH"
    )

    lines = source.splitlines()

    for index, text in enumerate(
        lines,
        1,
    ):
        lowered = text.lower()

        hits = []

        for indicator in TARGET_INDICATORS:
            if indicator.lower() in lowered:
                hits.append(indicator)

        if hits:
            print()
            print(
                f"LINE {index:<5} | "
                f"{', '.join(hits)}"
            )
            print(
                f"    {text.strip()}"
            )


# =============================================================================
# LOOK FOR ROW / DICT TRANSFORMATIONS
# =============================================================================

def trace_dict_transformations(
    source,
    tree,
):
    section(
        "STEP 10 — DICT / ROW TRANSFORMATION FORENSICS"
    )

    keywords = [
        "analysis",
        "result",
        "indicator",
        "record",
        "row",
        "data",
        "values",
    ]

    findings = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
            ),
        ):
            text = ast_segment(
                source,
                node,
            )

            lowered = text.lower()

            if (
                "analysis" in lowered
                or "technical_score" in lowered
                or "ema20" in lowered
                or "ema50" in lowered
                or "rsi14" in lowered
            ):
                findings.append(
                    (
                        node.lineno,
                        text,
                    )
                )

    findings.sort(
        key=lambda x: (
            x[0] if x[0] is not None else 0
        )
    )

    print(
        f"RELEVANT ASSIGNMENTS         : "
        f"{len(findings)}"
    )

    for line_number, text in findings:
        print(
            f"LINE {line_number:<5} | "
            f"{text}"
        )


# =============================================================================
# NUMERIC TRANSFORMATION HEURISTICS
# =============================================================================

def numeric_transformation_search(
    source,
):
    section(
        "STEP 11 — NUMERIC TRANSFORMATION / ROUNDING SEARCH"
    )

    patterns = [
        r"\bround\s*\(",
        r"\bfloat\s*\(",
        r"\bint\s*\(",
        r"\bDecimal\s*\(",
        r"\bquantize\s*\(",
        r"\bastype\s*\(",
        r"\.item\s*\(",
        r"\bformat\s*\(",
        r"\bf'{[^}]*}'",
        r'\bf"{[^}]*}"',
    ]

    lines = source.splitlines()

    found = []

    for index, text in enumerate(
        lines,
        1,
    ):
        for pattern in patterns:
            if re.search(
                pattern,
                text,
            ):
                found.append(
                    (
                        index,
                        text.strip(),
                    )
                )
                break

    print(
        f"NUMERIC TRANSFORMATION HITS : "
        f"{len(found)}"
    )

    for line_number, text in found:
        print(
            f"LINE {line_number:<5} | "
            f"{text}"
        )


# =============================================================================
# PRODUCTION PATH CLASSIFICATION
# =============================================================================

def classify_frontier(
    source,
    tree,
):
    section(
        "STEP 12 — FORENSIC FRONTIER CLASSIFICATION"
    )

    source_lower = source.lower()

    has_calculate_call = (
        "calculate_analysis("
        in source
    )

    transformation_hits = []

    for token in [
        "round(",
        "float(",
        "int(",
        "decimal",
        "quantize(",
        "astype(",
        "item(",
    ]:
        if token in source_lower:
            transformation_hits.append(
                token
            )

    sql_hits = []

    for word in SQL_WRITE_WORDS:
        if re.search(
            r"\b"
            + word
            + r"\b",
            source_lower,
        ):
            sql_hits.append(word)

    print(
        f"CALCULATE_ANALYSIS PRESENT   : "
        f"{has_calculate_call}"
    )

    print(
        f"NUMERIC TRANSFORMATIONS      : "
        f"{len(transformation_hits)}"
    )

    if transformation_hits:
        print(
            "TRANSFORMATION TOKENS        : "
            + ", ".join(
                transformation_hits
            )
        )

    print(
        f"SQL WRITE TOKENS FOUND       : "
        f"{len(sql_hits)}"
    )

    if sql_hits:
        print(
            "WRITE TOKENS                 : "
            + ", ".join(
                sorted(sql_hits)
            )
        )


# =============================================================================
# FINAL SAFETY CHECK
# =============================================================================

def safety_verification():
    section(
        "STEP 13 — SAFETY VERIFICATION"
    )

    print(
        "DATABASE MODE                : READ ONLY"
    )

    print(
        "DATABASE WRITE               : NONE"
    )

    print(
        "INSERT                       : NONE"
    )

    print(
        "UPDATE                       : NONE"
    )

    print(
        "DELETE                       : NONE"
    )

    print(
        "ALTER                        : NONE"
    )

    print(
        "CREATE                       : NONE"
    )

    print(
        "DROP                         : NONE"
    )

    print(
        "VACUUM                       : NONE"
    )

    print(
        "ENGINE MODIFICATION         : NONE"
    )

    print(
        "FORMULA MODIFICATION        : NONE"
    )


# =============================================================================
# FINAL REPORT
# =============================================================================

def final_report(
    callsites,
    stored_rows,
):
    section(
        "FINAL CALL-SITE TRANSFORMATION FORENSIC SUMMARY"
    )

    print(
        f"TARGETS REQUESTED            : "
        f"{len(TARGET_SYMBOLS)}"
    )

    print(
        f"TARGETS FOUND IN DATABASE    : "
        f"{len(stored_rows)}"
    )

    print(
        f"CALCULATE_ANALYSIS CALLS     : "
        f"{len(callsites)}"
    )

    print()
    print(
        "TARGET MATRIX"
    )

    for symbol in TARGET_SYMBOLS:

        if symbol not in stored_rows:
            print(
                f"[MISSING_STORED_TARGET]      : "
                f"{symbol}"
            )
        else:
            print(
                f"[STORED_TARGET_RESOLVED]     : "
                f"{symbol}"
            )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    if not callsites:
        print(
            "STATUS                       : "
            "CALL_SITE_NOT_RESOLVED"
        )

        print(
            "MEANING                      : "
            "calculate_analysis() call-site "
            "was not statically resolved."
        )

        print(
            "NEXT FRONTIER                : "
            "LOCATE ACTUAL PRODUCTION "
            "ANALYSIS INVOCATION PATH."
        )

    else:
        print(
            "STATUS                       : "
            "CALL_SITE_TRACE_RESOLVED"
        )

        print(
            "MEANING                      : "
            "The production invocation path "
            "was located and its surrounding "
            "input/assignment transformations "
            "were statically traced."
        )

        print(
            "IMPORTANT                    : "
            "This audit does NOT modify the "
            "production engine or database."
        )

        print(
            "NEXT FRONTIER                : "
            "If a dynamic production caller "
            "still remains unresolved, trace "
            "the exact runtime caller and "
            "SQL parameter tuple."
        )

    print()
    print(
        "DATABASE WRITE OPERATIONS    : NONE"
    )

    print(
        "ENGINE MODIFICATIONS         : NONE"
    )

    print(
        "FORMULA WRITE                : NONE"
    )

    print(
        "PRODUCTION RECALCULATION     : NONE"
    )

    print(
        "SQL MODE                     : READ ONLY"
    )

    print(
        "AUDIT COMPLETE"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    started = datetime.now(
        timezone.utc
    )

    line()

    print(
        "ARUNDA INDICATOR POST-REPAIR "
        "CALL-SITE TRANSFORMATION "
        "FORENSIC AUDIT v0.1"
    )

    line()

    print(
        "MODE                         : READ ONLY"
    )

    print(
        "PURPOSE                      : "
        "TRACE ACTUAL PRODUCTION "
        "CALL-SITE INPUT CONSTRUCTION "
        "AND POST-CALCULATION "
        "TRANSFORMATION"
    )

    print(
        "TARGETS                      : "
        + ", ".join(
            TARGET_SYMBOLS
        )
    )

    print(
        "DATABASE WRITE               : NONE"
    )

    print(
        "ENGINE WRITE                 : NONE"
    )

    print(
        "FORMULA WRITE                : NONE"
    )

    print(
        "PRODUCTION RECALCULATION     : NONE"
    )

    try:

        source = load_engine_source()

        tree = parse_source(
            source
        )

        callsites = (
            find_calculate_analysis_calls(
                source,
                tree,
            )
        )

        for call in callsites:

            trace_callsite_input_construction(
                source,
                tree,
                call,
            )

            trace_return_assignment(
                source,
                tree,
                call,
            )

        trace_post_calculation_transformations(
            source,
            tree,
        )

        trace_indicator_assignments(
            source,
            tree,
        )

        audit_sql_write_paths(
            source,
            tree,
        )

        inspect_database_schema()

        stored_rows = (
            get_latest_market_data_rows()
        )

        target_assignment_search(
            source,
        )

        trace_dict_transformations(
            source,
            tree,
        )

        numeric_transformation_search(
            source,
        )

        classify_frontier(
            source,
            tree,
        )

        safety_verification()

        final_report(
            callsites,
            stored_rows,
        )

        finished = datetime.now(
            timezone.utc
        )

        elapsed = (
            finished - started
        ).total_seconds()

        print()
        print(
            f"ELAPSED SECONDS              : "
            f"{elapsed:.3f}"
        )

    except Exception as exc:

        section(
            "AUDIT EXECUTION ERROR"
        )

        print(
            f"ERROR TYPE                   : "
            f"{type(exc).__name__}"
        )

        print(
            f"ERROR                        : "
            f"{exc}"
        )

        print()
        print(
            "TRACEBACK"
        )

        traceback.print_exc()

        print()
        print(
            "IMPORTANT                    : "
            "NO DATABASE WRITE WAS "
            "PERFORMED BY THIS SCRIPT."
        )


if __name__ == "__main__":
    main()