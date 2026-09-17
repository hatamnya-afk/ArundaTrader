# ARUNDA INDICATOR POST REPAIR CALCULATION IMPLEMENTATION
# LINE-BY-LINE FORENSIC TRACE AUDIT v0.1
#
# MODE:
#   READ ONLY / FORENSIC ONLY
#
# DATABASE:
#   READ ONLY
#
# ENGINE:
#   READ ONLY
#
# NO:
#   INSERT
#   UPDATE
#   DELETE
#   ALTER
#   CREATE
#   VACUUM
#   PRAGMA write
#   recalculation
#   monkey patch
#
# PURPOSE:
#   Trace the exact production indicator implementation line-by-line.
#
# TARGET:
#   calculate_analysis()
#   ema()
#   ema_series()
#   rsi()
#   macd()
#
# IMPORTANT:
#   This audit does NOT attempt to guess the production formula.
#   It extracts and reports the actual implementation path.

import ast
import inspect
import os
import sqlite3
import textwrap
import traceback
from collections import Counter, defaultdict


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINE_PATH = os.path.join(
    BASE_DIR,
    "market_data_engine.py"
)

DB_PATH = os.path.join(
    BASE_DIR,
    "arunda.db"
)

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

TARGET_FUNCTIONS = [
    "calculate_analysis",
    "ema",
    "ema_series",
    "rsi",
    "macd",
]

MARKET_DATA_TABLE = "market_data"


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

WIDTH = 100


def line():
    print("=" * WIDTH)


def subline():
    print("-" * WIDTH)


def title(text):
    print()
    line()
    print(text)
    line()


def section(text):
    print()
    print("=" * WIDTH)
    print(text)
    print("=" * WIDTH)


def subsection(text):
    print()
    print("-" * WIDTH)
    print(text)
    print("-" * WIDTH)


def safe_repr(value, max_len=500):
    try:
        result = repr(value)
    except Exception:
        result = "<UNREPRESENTABLE>"

    if len(result) > max_len:
        result = result[:max_len] + "...<TRUNCATED>"

    return result


# =============================================================================
# FILE RESOLUTION
# =============================================================================

def resolve_engine():
    print(f"ENGINE PATH        : {ENGINE_PATH}")
    print(f"ENGINE FOUND       : {os.path.exists(ENGINE_PATH)}")

    if not os.path.exists(ENGINE_PATH):
        raise FileNotFoundError(
            f"Engine not found: {ENGINE_PATH}"
        )

    with open(
        ENGINE_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        source = f.read()

    print(f"ENGINE SIZE        : {len(source)} characters")
    print(f"ENGINE LINES       : {len(source.splitlines())}")

    return source


# =============================================================================
# AST PARSING
# =============================================================================

def parse_source(source):
    try:
        tree = ast.parse(
            source,
            filename=ENGINE_PATH
        )

        print("AST STATUS         : SUCCESS")

        return tree

    except SyntaxError as exc:
        print("AST STATUS         : FAILED")
        print(f"LINE               : {exc.lineno}")
        print(f"OFFSET             : {exc.offset}")
        print(f"TEXT               : {exc.text}")

        raise


# =============================================================================
# FUNCTION COLLECTION
# =============================================================================

def collect_functions(tree):

    functions = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):
            functions[node.name] = node

    return functions


# =============================================================================
# SOURCE EXTRACTION
# =============================================================================

def node_source(source, node):

    try:
        segment = ast.get_source_segment(
            source,
            node
        )

        if segment:
            return segment

    except Exception:
        pass

    lines = source.splitlines()

    start = max(
        0,
        node.lineno - 1
    )

    end = getattr(
        node,
        "end_lineno",
        node.lineno
    )

    return "\n".join(
        lines[start:end]
    )


# =============================================================================
# FUNCTION SIGNATURE
# =============================================================================

def format_arguments(node):

    args = node.args

    positional = []

    for arg in args.posonlyargs:
        positional.append(arg.arg)

    for arg in args.args:
        positional.append(arg.arg)

    if args.vararg:
        positional.append(
            "*" + args.vararg.arg
        )

    for arg in args.kwonlyargs:
        positional.append(arg.arg)

    if args.kwarg:
        positional.append(
            "**" + args.kwarg.arg
        )

    return positional


# =============================================================================
# DECORATOR TRACE
# =============================================================================

def trace_decorators(node):

    result = []

    for decorator in node.decorator_list:
        result.append(
            ast.unparse(decorator)
        )

    return result


# =============================================================================
# RETURN TRACE
# =============================================================================

class ReturnTracer(ast.NodeVisitor):

    def __init__(self):
        self.returns = []

    def visit_Return(self, node):

        if node.value is None:
            value = "None"

        else:
            try:
                value = ast.unparse(
                    node.value
                )
            except Exception:
                value = "<UNPARSEABLE>"

        self.returns.append(
            {
                "line": node.lineno,
                "value": value,
            }
        )

        self.generic_visit(node)


def trace_returns(node):

    tracer = ReturnTracer()
    tracer.visit(node)

    return tracer.returns


# =============================================================================
# BRANCH TRACE
# =============================================================================

class BranchTracer(ast.NodeVisitor):

    def __init__(self):

        self.if_branches = []
        self.for_loops = []
        self.while_loops = []
        self.try_blocks = []
        self.match_blocks = []

    def visit_If(self, node):

        try:
            condition = ast.unparse(
                node.test
            )
        except Exception:
            condition = "<UNPARSEABLE>"

        self.if_branches.append(
            {
                "line": node.lineno,
                "condition": condition,
                "has_else": bool(node.orelse),
            }
        )

        self.generic_visit(node)

    def visit_For(self, node):

        try:
            target = ast.unparse(
                node.target
            )
        except Exception:
            target = "<UNPARSEABLE>"

        try:
            iterator = ast.unparse(
                node.iter
            )
        except Exception:
            iterator = "<UNPARSEABLE>"

        self.for_loops.append(
            {
                "line": node.lineno,
                "target": target,
                "iterator": iterator,
            }
        )

        self.generic_visit(node)

    def visit_While(self, node):

        try:
            condition = ast.unparse(
                node.test
            )
        except Exception:
            condition = "<UNPARSEABLE>"

        self.while_loops.append(
            {
                "line": node.lineno,
                "condition": condition,
            }
        )

        self.generic_visit(node)

    def visit_Try(self, node):

        self.try_blocks.append(
            {
                "line": node.lineno,
                "handlers": len(node.handlers),
                "has_finally": bool(node.finalbody),
            }
        )

        self.generic_visit(node)

    def visit_Match(self, node):

        self.match_blocks.append(
            {
                "line": node.lineno,
                "cases": len(node.cases),
            }
        )

        self.generic_visit(node)


def trace_branches(node):

    tracer = BranchTracer()
    tracer.visit(node)

    return tracer


# =============================================================================
# CALL GRAPH TRACE
# =============================================================================

class CallTracer(ast.NodeVisitor):

    def __init__(self):

        self.calls = []

    def visit_Call(self, node):

        try:
            expression = ast.unparse(
                node.func
            )
        except Exception:
            expression = "<UNPARSEABLE>"

        arguments = []

        for arg in node.args:

            try:
                arguments.append(
                    ast.unparse(arg)
                )
            except Exception:
                arguments.append(
                    "<UNPARSEABLE>"
                )

        keywords = []

        for kw in node.keywords:

            try:
                value = ast.unparse(
                    kw.value
                )
            except Exception:
                value = "<UNPARSEABLE>"

            keywords.append(
                {
                    "name": kw.arg,
                    "value": value,
                }
            )

        self.calls.append(
            {
                "line": node.lineno,
                "function": expression,
                "arguments": arguments,
                "keywords": keywords,
            }
        )

        self.generic_visit(node)


def trace_calls(node):

    tracer = CallTracer()
    tracer.visit(node)

    return tracer.calls


# =============================================================================
# ASSIGNMENT TRACE
# =============================================================================

class AssignmentTracer(ast.NodeVisitor):

    def __init__(self):

        self.assignments = []

    def visit_Assign(self, node):

        targets = []

        for target in node.targets:

            try:
                targets.append(
                    ast.unparse(target)
                )
            except Exception:
                targets.append(
                    "<UNPARSEABLE>"
                )

        try:
            value = ast.unparse(
                node.value
            )
        except Exception:
            value = "<UNPARSEABLE>"

        self.assignments.append(
            {
                "line": node.lineno,
                "targets": targets,
                "value": value,
            }
        )

        self.generic_visit(node)

    def visit_AnnAssign(self, node):

        try:
            target = ast.unparse(
                node.target
            )
        except Exception:
            target = "<UNPARSEABLE>"

        try:
            value = (
                ast.unparse(node.value)
                if node.value
                else "None"
            )
        except Exception:
            value = "<UNPARSEABLE>"

        self.assignments.append(
            {
                "line": node.lineno,
                "targets": [target],
                "value": value,
            }
        )

        self.generic_visit(node)


def trace_assignments(node):

    tracer = AssignmentTracer()
    tracer.visit(node)

    return tracer.assignments


# =============================================================================
# SUBSCRIPT / INDEX TRACE
# =============================================================================

class SubscriptTracer(ast.NodeVisitor):

    def __init__(self):

        self.subscripts = []

    def visit_Subscript(self, node):

        try:
            expression = ast.unparse(node)
        except Exception:
            expression = "<UNPARSEABLE>"

        self.subscripts.append(
            {
                "line": node.lineno,
                "expression": expression,
            }
        )

        self.generic_visit(node)


def trace_subscripts(node):

    tracer = SubscriptTracer()
    tracer.visit(node)

    return tracer.subscripts


# =============================================================================
# LENGTH / SLICE / WINDOW TRACE
# =============================================================================

class SemanticTracer(ast.NodeVisitor):

    def __init__(self):

        self.length_calls = []
        self.slice_nodes = []
        self.comparisons = []

    def visit_Call(self, node):

        try:
            func = ast.unparse(node.func)
        except Exception:
            func = "<UNPARSEABLE>"

        if func in (
            "len",
            "min",
            "max",
            "sum",
            "sorted",
            "reversed",
            "list",
            "tuple",
        ):

            self.length_calls.append(
                {
                    "line": node.lineno,
                    "function": func,
                    "expression": ast.unparse(node),
                }
            )

        self.generic_visit(node)

    def visit_Subscript(self, node):

        try:
            text = ast.unparse(node)
        except Exception:
            text = "<UNPARSEABLE>"

        if ":" in text:
            self.slice_nodes.append(
                {
                    "line": node.lineno,
                    "expression": text,
                }
            )

        self.generic_visit(node)

    def visit_Compare(self, node):

        try:
            expression = ast.unparse(node)
        except Exception:
            expression = "<UNPARSEABLE>"

        self.comparisons.append(
            {
                "line": node.lineno,
                "expression": expression,
            }
        )

        self.generic_visit(node)


def trace_semantics(node):

    tracer = SemanticTracer()
    tracer.visit(node)

    return tracer


# =============================================================================
# IDENTIFIER / VARIABLE TRACE
# =============================================================================

class NameTracer(ast.NodeVisitor):

    def __init__(self):

        self.names = Counter()

    def visit_Name(self, node):

        self.names[node.id] += 1

        self.generic_visit(node)


def trace_names(node):

    tracer = NameTracer()
    tracer.visit(node)

    return tracer.names


# =============================================================================
# CONSTANT TRACE
# =============================================================================

class ConstantTracer(ast.NodeVisitor):

    def __init__(self):

        self.constants = []

    def visit_Constant(self, node):

        value = node.value

        if isinstance(
            value,
            (
                int,
                float,
                str,
                bool,
                type(None),
            )
        ):

            self.constants.append(
                {
                    "line": node.lineno,
                    "value": value,
                }
            )

        self.generic_visit(node)


def trace_constants(node):

    tracer = ConstantTracer()
    tracer.visit(node)

    return tracer.constants


# =============================================================================
# FUNCTION REPORT
# =============================================================================

def print_function_report(
    function_name,
    node,
    source
):

    section(
        f"FUNCTION IMPLEMENTATION TRACE : {function_name}"
    )

    print(
        f"DEFINITION LINE     : {node.lineno}"
    )

    print(
        f"END LINE            : "
        f"{getattr(node, 'end_lineno', node.lineno)}"
    )

    print(
        f"ARGUMENTS           : "
        f"{format_arguments(node)}"
    )

    decorators = trace_decorators(node)

    print(
        f"DECORATORS          : "
        f"{decorators if decorators else 'NONE'}"
    )

    # -------------------------------------------------------------------------
    # RETURNS
    # -------------------------------------------------------------------------

    subsection(
        "RETURN PATHS"
    )

    returns = trace_returns(node)

    if not returns:

        print(
            "NO EXPLICIT RETURN FOUND"
        )

    else:

        for item in returns:

            print(
                f"LINE {item['line']:>5} "
                f"RETURN {item['value']}"
            )

    # -------------------------------------------------------------------------
    # BRANCHES
    # -------------------------------------------------------------------------

    subsection(
        "BRANCH / CONTROL FLOW"
    )

    branches = trace_branches(node)

    if not branches.if_branches:
        print("IF BRANCHES          : NONE")

    else:

        for item in branches.if_branches:

            print(
                f"IF LINE {item['line']:>5} "
                f"CONDITION={item['condition']} "
                f"ELSE={item['has_else']}"
            )

    if branches.for_loops:

        for item in branches.for_loops:

            print(
                f"FOR LINE {item['line']:>5} "
                f"{item['target']} IN {item['iterator']}"
            )

    else:

        print(
            "FOR LOOPS            : NONE"
        )

    if branches.while_loops:

        for item in branches.while_loops:

            print(
                f"WHILE LINE {item['line']:>5} "
                f"CONDITION={item['condition']}"
            )

    else:

        print(
            "WHILE LOOPS          : NONE"
        )

    if branches.try_blocks:

        for item in branches.try_blocks:

            print(
                f"TRY LINE {item['line']:>5} "
                f"HANDLERS={item['handlers']} "
                f"FINALLY={item['has_finally']}"
            )

    else:

        print(
            "TRY BLOCKS           : NONE"
        )

    if branches.match_blocks:

        for item in branches.match_blocks:

            print(
                f"MATCH LINE {item['line']:>5} "
                f"CASES={item['cases']}"
            )

    # -------------------------------------------------------------------------
    # CALL GRAPH
    # -------------------------------------------------------------------------

    subsection(
        "INTERNAL / EXTERNAL CALLS"
    )

    calls = trace_calls(node)

    if not calls:

        print(
            "CALLS                : NONE"
        )

    else:

        for call in calls:

            print(
                f"LINE {call['line']:>5} "
                f"CALL={call['function']}"
            )

            if call["arguments"]:

                print(
                    f"  ARGS              : "
                    f"{call['arguments']}"
                )

            if call["keywords"]:

                print(
                    f"  KEYWORDS          : "
                    f"{call['keywords']}"
                )

    # -------------------------------------------------------------------------
    # ASSIGNMENTS
    # -------------------------------------------------------------------------

    subsection(
        "ASSIGNMENT TRACE"
    )

    assignments = trace_assignments(node)

    if not assignments:

        print(
            "ASSIGNMENTS          : NONE"
        )

    else:

        for item in assignments:

            print(
                f"LINE {item['line']:>5} "
                f"{item['targets']} = "
                f"{item['value']}"
            )

    # -------------------------------------------------------------------------
    # SUBSCRIPTS
    # -------------------------------------------------------------------------

    subsection(
        "INDEX / SLICE / WINDOW TRACE"
    )

    subscripts = trace_subscripts(node)

    if not subscripts:

        print(
            "INDEX OPERATIONS     : NONE"
        )

    else:

        for item in subscripts:

            print(
                f"LINE {item['line']:>5} "
                f"{item['expression']}"
            )

    # -------------------------------------------------------------------------
    # SEMANTIC CALLS
    # -------------------------------------------------------------------------

    subsection(
        "LENGTH / SORT / SLICE SEMANTICS"
    )

    semantics = trace_semantics(node)

    if semantics.length_calls:

        for item in semantics.length_calls:

            print(
                f"LINE {item['line']:>5} "
                f"{item['expression']}"
            )

    else:

        print(
            "LENGTH/SORT CALLS    : NONE"
        )

    if semantics.slice_nodes:

        for item in semantics.slice_nodes:

            print(
                f"SLICE LINE {item['line']:>5} "
                f"{item['expression']}"
            )

    else:

        print(
            "SLICE OPERATIONS     : NONE"
        )

    # -------------------------------------------------------------------------
    # COMPARISONS
    # -------------------------------------------------------------------------

    subsection(
        "COMPARISON / GUARD EXPRESSIONS"
    )

    if semantics.comparisons:

        for item in semantics.comparisons:

            print(
                f"LINE {item['line']:>5} "
                f"{item['expression']}"
            )

    else:

        print(
            "COMPARISONS          : NONE"
        )

    # -------------------------------------------------------------------------
    # CONSTANTS
    # -------------------------------------------------------------------------

    subsection(
        "NUMERIC / FORMULA CONSTANTS"
    )

    constants = trace_constants(node)

    interesting = []

    for item in constants:

        value = item["value"]

        if isinstance(
            value,
            (
                int,
                float
            )
        ):

            interesting.append(
                item
            )

    if interesting:

        for item in interesting:

            print(
                f"LINE {item['line']:>5} "
                f"VALUE={item['value']!r}"
            )

    else:

        print(
            "NUMERIC CONSTANTS    : NONE"
        )

    # -------------------------------------------------------------------------
    # IDENTIFIERS
    # -------------------------------------------------------------------------

    subsection(
        "IDENTIFIER FREQUENCY"
    )

    names = trace_names(node)

    for name, count in names.most_common():

        print(
            f"{name:<35} : {count}"
        )

    # -------------------------------------------------------------------------
    # RAW SOURCE
    # -------------------------------------------------------------------------

    subsection(
        "EXACT FUNCTION SOURCE"
    )

    exact = node_source(
        source,
        node
    )

    print(exact)


# =============================================================================
# DATABASE READ ONLY
# =============================================================================

def open_database():

    print(
        f"DATABASE PATH      : {DB_PATH}"
    )

    print(
        f"DATABASE FOUND     : {os.path.exists(DB_PATH)}"
    )

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True
    )

    return conn


def database_schema(conn):

    section(
        "DATABASE SCHEMA RESOLUTION"
    )

    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    print(
        f"TABLE COUNT        : {len(tables)}"
    )

    for table in tables:

        print(
            f"TABLE              : {table[0]}"
        )

    if MARKET_DATA_TABLE in [
        row[0] for row in tables
    ]:

        rows = conn.execute(
            f"""
            PRAGMA table_info({MARKET_DATA_TABLE})
            """
        ).fetchall()

        subsection(
            "MARKET_DATA COLUMNS"
        )

        for row in rows:

            print(
                f"{row[0]:>3} : {row[1]:<30} "
                f"TYPE={row[2]}"
            )


# =============================================================================
# DATABASE PRODUCTION TARGET TRACE
# =============================================================================

def production_targets(conn):

    section(
        "PRODUCTION TARGET RESOLUTION"
    )

    for symbol in TARGET_SYMBOLS:

        subsection(
            f"SYMBOL : {symbol}"
        )

        columns = [
            row[1]
            for row in conn.execute(
                f"""
                PRAGMA table_info({MARKET_DATA_TABLE})
                """
            ).fetchall()
        ]

        sql = f"""
            SELECT
                id,
                timestamp,
                symbol,
                timeframe,
                close,
                ema20,
                ema50,
                rsi14,
                source,
                source_timestamp,
                engine_version
            FROM {MARKET_DATA_TABLE}
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT 1
        """

        row = conn.execute(
            sql,
            (symbol,)
        ).fetchone()

        if row is None:

            print(
                "TARGET NOT FOUND"
            )

            continue

        print(
            f"ID                 : {row[0]}"
        )

        print(
            f"TIMESTAMP          : {row[1]}"
        )

        print(
            f"TIMEFRAME          : {row[3]}"
        )

        print(
            f"CLOSE              : {row[4]}"
        )

        print(
            f"EMA20              : {row[5]}"
        )

        print(
            f"EMA50              : {row[6]}"
        )

        print(
            f"RSI14              : {row[7]}"
        )

        print(
            f"SOURCE             : {row[8]}"
        )

        print(
            f"SOURCE_TIMESTAMP   : {row[9]}"
        )

        print(
            f"ENGINE_VERSION     : {row[10]}"
        )


# =============================================================================
# FUNCTION RELATIONSHIP MAP
# =============================================================================

def function_relationship_map(functions):

    section(
        "FUNCTION RELATIONSHIP MAP"
    )

    graph = defaultdict(list)

    for function_name, node in functions.items():

        calls = trace_calls(node)

        for call in calls:

            called = call["function"]

            if called in functions:

                graph[function_name].append(
                    called
                )

    for function_name in TARGET_FUNCTIONS:

        if function_name not in functions:

            print(
                f"{function_name:<30} : NOT FOUND"
            )

            continue

        targets = graph.get(
            function_name,
            []
        )

        if targets:

            print(
                f"{function_name:<30} -> "
                f"{', '.join(targets)}"
            )

        else:

            print(
                f"{function_name:<30} -> "
                f"NO_INTERNAL_TARGET_CALL"
            )


# =============================================================================
# INDICATOR SEMANTICS CROSS CHECK
# =============================================================================

def semantic_keyword_audit(functions):

    section(
        "INDICATOR IMPLEMENTATION KEYWORD FORENSICS"
    )

    keywords = [
        "ema",
        "ema_series",
        "rsi",
        "macd",
        "alpha",
        "period",
        "window",
        "seed",
        "sma",
        "mean",
        "rolling",
        "previous",
        "prev",
        "close",
        "closes",
        "prices",
        "values",
        "round",
        "float",
        "numpy",
        "statistics",
    ]

    for function_name in TARGET_FUNCTIONS:

        subsection(
            f"FUNCTION : {function_name}"
        )

        node = functions.get(
            function_name
        )

        if node is None:

            print(
                "FUNCTION NOT FOUND"
            )

            continue

        names = trace_names(node)

        found = []

        for keyword in keywords:

            if names.get(keyword, 0) > 0:

                found.append(
                    (
                        keyword,
                        names[keyword]
                    )
                )

        if found:

            for keyword, count in found:

                print(
                    f"{keyword:<20} : {count}"
                )

        else:

            print(
                "NO TARGET KEYWORDS FOUND"
            )


# =============================================================================
# AST CONSTANT / FORMULA FORENSICS
# =============================================================================

def formula_constant_audit(functions):

    section(
        "FORMULA / INITIALIZATION CONSTANT FORENSICS"
    )

    for function_name in TARGET_FUNCTIONS:

        subsection(
            f"FUNCTION : {function_name}"
        )

        node = functions.get(
            function_name
        )

        if node is None:
            continue

        constants = trace_constants(node)

        numeric = [
            item
            for item in constants
            if isinstance(
                item["value"],
                (
                    int,
                    float
                )
            )
        ]

        if not numeric:

            print(
                "NO NUMERIC CONSTANTS"
            )

            continue

        for item in numeric:

            print(
                f"LINE {item['line']:>5} "
                f"VALUE={item['value']!r}"
            )


# =============================================================================
# LINE-BY-LINE EXECUTION PATH MODEL
# =============================================================================

class StatementTracer(ast.NodeVisitor):

    def __init__(self):

        self.statements = []

    def generic_visit(self, node):

        if hasattr(
            node,
            "lineno"
        ):

            try:
                source = ast.unparse(node)
            except Exception:
                source = type(node).__name__

            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.AugAssign,
                    ast.Return,
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.Call,
                    ast.Expr,
                )
            ):

                self.statements.append(
                    {
                        "line": node.lineno,
                        "type": type(node).__name__,
                        "source": source,
                    }
                )

        super().generic_visit(node)


def print_statement_trace(
    function_name,
    node
):

    subsection(
        f"STATEMENT PATH : {function_name}"
    )

    tracer = StatementTracer()
    tracer.visit(node)

    statements = sorted(
        tracer.statements,
        key=lambda x: x["line"]
    )

    for item in statements:

        print(
            f"LINE {item['line']:>5} "
            f"[{item['type']:<10}] "
            f"{item['source']}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    title(
        "ARUNDA INDICATOR POST REPAIR CALCULATION "
        "INPUT ORDER FILTER WINDOW FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                  : READ ONLY"
    )

    print(
        "DATABASE WRITE        : NONE"
    )

    print(
        "ENGINE WRITE          : NONE"
    )

    print(
        "FORMULA WRITE         : NONE"
    )

    print(
        "PRODUCTION RECALCULATION : NONE"
    )

    print(
        "PURPOSE               : "
        "TRACE EXACT PRODUCTION FUNCTION IMPLEMENTATION"
    )

    # -------------------------------------------------------------------------
    # STEP 1
    # -------------------------------------------------------------------------

    section(
        "STEP 1 — ENGINE SOURCE RESOLUTION"
    )

    source = resolve_engine()

    # -------------------------------------------------------------------------
    # STEP 2
    # -------------------------------------------------------------------------

    section(
        "STEP 2 — AST RESOLUTION"
    )

    tree = parse_source(
        source
    )

    functions = collect_functions(
        tree
    )

    print(
        f"FUNCTION COUNT       : {len(functions)}"
    )

    # -------------------------------------------------------------------------
    # STEP 3
    # -------------------------------------------------------------------------

    section(
        "STEP 3 — TARGET FUNCTION RESOLUTION"
    )

    for function_name in TARGET_FUNCTIONS:

        if function_name in functions:

            node = functions[
                function_name
            ]

            print(
                f"[FOUND] {function_name} "
                f"LINE {node.lineno}-"
                f"{getattr(node, 'end_lineno', node.lineno)}"
            )

        else:

            print(
                f"[MISSING] {function_name}"
            )

    # -------------------------------------------------------------------------
    # STEP 4
    # -------------------------------------------------------------------------

    section(
        "STEP 4 — EXACT IMPLEMENTATION TRACE"
    )

    for function_name in TARGET_FUNCTIONS:

        node = functions.get(
            function_name
        )

        if node is None:
            continue

        print_function_report(
            function_name,
            node,
            source
        )

        print_statement_trace(
            function_name,
            node
        )

    # -------------------------------------------------------------------------
    # STEP 5
    # -------------------------------------------------------------------------

    function_relationship_map(
        functions
    )

    # -------------------------------------------------------------------------
    # STEP 6
    # -------------------------------------------------------------------------

    section(
        "STEP 6 — DATABASE RESOLUTION"
    )

    conn = None

    try:

        conn = open_database()

        database_schema(
            conn
        )

        # ---------------------------------------------------------------------
        # STEP 7
        # ---------------------------------------------------------------------

        section(
            "STEP 7 — PRODUCTION TARGET RESOLUTION"
        )

        production_targets(
            conn
        )

    finally:

        if conn is not None:

            conn.close()

    # -------------------------------------------------------------------------
    # STEP 8
    # -------------------------------------------------------------------------

    semantic_keyword_audit(
        functions
    )

    # -------------------------------------------------------------------------
    # STEP 9
    # -------------------------------------------------------------------------

    formula_constant_audit(
        functions
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    section(
        "FINAL EXACT PRODUCTION FUNCTION IMPLEMENTATION FORENSIC SUMMARY"
    )

    found = [
        name
        for name in TARGET_FUNCTIONS
        if name in functions
    ]

    missing = [
        name
        for name in TARGET_FUNCTIONS
        if name not in functions
    ]

    print(
        f"TARGET FUNCTIONS CHECKED : "
        f"{len(TARGET_FUNCTIONS)}"
    )

    print(
        f"FUNCTIONS FOUND          : "
        f"{len(found)}"
    )

    print(
        f"FUNCTIONS MISSING        : "
        f"{len(missing)}"
    )

    if missing:

        print(
            f"MISSING                  : "
            f"{missing}"
        )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    print(
        "STATUS                   : "
        "IMPLEMENTATION_TRACE_COMPLETE"
    )

    print(
        "REASON                   : "
        "ACTUAL PRODUCTION FUNCTION SOURCE, "
        "BRANCHES, CALLS, RETURNS, ASSIGNMENTS, "
        "INDEXING, CONSTANTS AND DATABASE TARGETS "
        "HAVE BEEN TRACED WITHOUT MODIFYING THE ENGINE "
        "OR DATABASE"
    )

    print(
        "NEXT FRONTIER            : "
        "MAP EACH STORED INDICATOR VALUE TO THE "
        "EXACT INTERNAL RETURN PATH AND INTERMEDIATE "
        "STATE OF THE PRODUCTION FUNCTION"
    )

    print()
    print(
        "DATABASE WRITE OPERATIONS : NONE"
    )

    print(
        "ENGINE MODIFICATIONS      : NONE"
    )

    print(
        "FORMULA WRITE             : NONE"
    )

    print(
        "PRODUCTION RECALCULATION  : NONE"
    )

    print(
        "AUDIT COMPLETE"
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        line()

        print(
            "AUDIT ERROR"
        )

        line()

        print(
            f"TYPE : {type(exc).__name__}"
        )

        print(
            f"ERROR: {exc}"
        )

        print()

        traceback.print_exc()

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS      : NONE"
        )

        raise