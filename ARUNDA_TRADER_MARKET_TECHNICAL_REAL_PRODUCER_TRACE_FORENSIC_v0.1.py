import ast
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arunda.db")
ENGINE_PATH = os.path.join(BASE_DIR, "market_technical_engine.py")

TARGET_TABLE = "market_technical"

SCRIPT_NAME = (
    "ARUNDA TRADER MARKET TECHNICAL REAL PRODUCER TRACE FORENSIC v0.1"
)


# =============================================================================
# READ ONLY HELPERS
# =============================================================================

def read_text_readonly(path):
    """
    Read source strictly read-only.

    IMPORTANT:
    UTF-8 BOM is stripped IN MEMORY ONLY.
    The source file is never modified.
    """
    with open(path, "rb") as f:
        raw = f.read()

    had_bom = raw.startswith(b"\xef\xbb\xbf")

    if had_bom:
        raw = raw[3:]

    text = raw.decode("utf-8")

    return text, had_bom


def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def node_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = node_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def literal_string(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value

    return None


def get_call_name(node):
    if not isinstance(node, ast.Call):
        return None

    return node_name(node.func)


def line_range(node):
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)

    return start, end


def compact(value, limit=180):
    text = str(value)

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    if len(text) > limit:
        return text[:limit] + "..."

    return text


# =============================================================================
# AST ANALYZER
# =============================================================================

class EngineAnalyzer(ast.NodeVisitor):

    TECHNICAL_FEATURES = {
        "price",
        "close",
        "open",
        "high",
        "low",
        "volume",

        "history",
        "history_points",

        "volatility",
        "volatility_5",
        "volatility_10",
        "volatility_20",

        "atr14",
        "atr_14",

        "rsi14",
        "rsi_14",

        "ema20",
        "ema_20",

        "sma20",
        "sma_20",

        "bb_width",
        "cloud_thickness",

        "trend",
        "trend_score",

        "momentum_score",
        "volatility_score",
        "volume_score",

        "range_score",
        "breakout_score",

        "breakout_20",

        "volume_ratio",

        "technical_completeness",
        "completeness",

        "available",
        "technical_available",

        "fib_available",
        "fib_236",
        "fib_382",
        "fib_500",
        "fib_618",
        "fib_786",

        "ichimoku_available",
        "tenkan",
        "kijun",
        "senkou_a",
        "senkou_b",
    }

    INPUT_NAMES = {
        "price",
        "close",
        "open",
        "high",
        "low",
        "volume",
        "history",
        "history_points",
        "symbol",
        "time",
        "timestamp",
        "market",
        "row",
        "columns",
        "data",
    }

    def __init__(self):

        self.functions = {}

        self.classes = {}

        self.calls = []

        self.sql_reads = []

        self.sql_writes = []

        self.feature_reads = defaultdict(set)

        self.feature_writes = defaultdict(set)

        self.function_inputs = defaultdict(set)

        self.function_calls = defaultdict(set)

        self.function_sources = defaultdict(set)

        self.current_function = None

        self.assignments = []

        self.returns = []

        self.constants = {}

    # -------------------------------------------------------------------------
    # FUNCTION
    # -------------------------------------------------------------------------

    def visit_FunctionDef(self, node):

        name = node.name

        self.functions[name] = node

        previous = self.current_function

        self.current_function = name

        for arg in node.args.args:
            self.function_inputs[name].add(arg.arg)

        self.generic_visit(node)

        self.current_function = previous

    def visit_AsyncFunctionDef(self, node):

        name = node.name

        self.functions[name] = node

        previous = self.current_function

        self.current_function = name

        for arg in node.args.args:
            self.function_inputs[name].add(arg.arg)

        self.generic_visit(node)

        self.current_function = previous

    # -------------------------------------------------------------------------
    # CLASS
    # -------------------------------------------------------------------------

    def visit_ClassDef(self, node):

        self.classes[node.name] = node

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    def visit_Call(self, node):

        call_name = get_call_name(node)

        if call_name:

            record = {
                "function": self.current_function,
                "call": call_name,
                "line": getattr(node, "lineno", None),
                "source": safe_unparse(node),
            }

            self.calls.append(record)

            if self.current_function:
                self.function_calls[
                    self.current_function
                ].add(call_name)

            if call_name.endswith(".execute"):

                sql = None

                if node.args:

                    sql = literal_string(node.args[0])

                if sql:

                    sql_clean = re.sub(
                        r"\s+",
                        " ",
                        sql
                    ).strip()

                    upper = sql_clean.upper()

                    if any(
                        keyword in upper
                        for keyword in [
                            "SELECT",
                            "PRAGMA",
                        ]
                    ):

                        self.sql_reads.append(
                            {
                                "function": self.current_function,
                                "line": getattr(
                                    node,
                                    "lineno",
                                    None
                                ),
                                "sql": sql_clean,
                            }
                        )

                    if any(
                        keyword in upper
                        for keyword in [
                            "INSERT",
                            "UPDATE",
                            "DELETE",
                            "ALTER",
                            "CREATE",
                            "DROP",
                            "REPLACE",
                        ]
                    ):

                        self.sql_writes.append(
                            {
                                "function": self.current_function,
                                "line": getattr(
                                    node,
                                    "lineno",
                                    None
                                ),
                                "sql": sql_clean,
                            }
                        )

            if call_name.endswith(".executemany"):

                self.sql_writes.append(
                    {
                        "function": self.current_function,
                        "line": getattr(
                            node,
                            "lineno",
                            None
                        ),
                        "sql": safe_unparse(node),
                    }
                )

            if call_name.endswith(".commit"):

                self.sql_writes.append(
                    {
                        "function": self.current_function,
                        "line": getattr(
                            node,
                            "lineno",
                            None
                        ),
                        "sql": "COMMIT()",
                    }
                )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # SUBSCRIPT / DICT ACCESS
    # -------------------------------------------------------------------------

    def visit_Subscript(self, node):

        if self.current_function:

            value_name = node_name(node.value)

            key = None

            slice_node = node.slice

            if isinstance(slice_node, ast.Constant):
                if isinstance(slice_node.value, str):
                    key = slice_node.value

            if key:

                if key in self.TECHNICAL_FEATURES:

                    self.feature_reads[
                        self.current_function
                    ].add(key)

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # DICT GET
    # -------------------------------------------------------------------------

    def visit_Call_DictGet(self, node):
        pass

    # -------------------------------------------------------------------------
    # STRING CONSTANTS
    # -------------------------------------------------------------------------

    def visit_Constant(self, node):

        if (
            self.current_function
            and isinstance(node.value, str)
        ):

            value = node.value

            if value in self.TECHNICAL_FEATURES:

                self.feature_reads[
                    self.current_function
                ].add(value)

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # ASSIGNMENTS
    # -------------------------------------------------------------------------

    def visit_Assign(self, node):

        if self.current_function:

            target_names = []

            for target in node.targets:

                if isinstance(target, ast.Name):
                    target_names.append(target.id)

                elif isinstance(target, ast.Tuple):
                    for element in target.elts:
                        if isinstance(element, ast.Name):
                            target_names.append(
                                element.id
                            )

            value_text = safe_unparse(node.value)

            record = {
                "function": self.current_function,
                "line": getattr(node, "lineno", None),
                "targets": target_names,
                "value": value_text,
            }

            self.assignments.append(record)

            for target in target_names:

                if target in self.TECHNICAL_FEATURES:
                    self.feature_writes[
                        self.current_function
                    ].add(target)

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # RETURN
    # -------------------------------------------------------------------------

    def visit_Return(self, node):

        if self.current_function:

            self.returns.append(
                {
                    "function": self.current_function,
                    "line": getattr(
                        node,
                        "lineno",
                        None
                    ),
                    "value": safe_unparse(
                        node.value
                    )
                    if node.value is not None
                    else None,
                }
            )

        self.generic_visit(node)


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def extract_feature_mentions(source, analyzer):

    features = set()

    for feature in analyzer.TECHNICAL_FEATURES:

        patterns = [
            rf"""["']{re.escape(feature)}["']""",
            rf"""\b{re.escape(feature)}\b""",
        ]

        for pattern in patterns:

            if re.search(
                pattern,
                source
            ):

                features.add(feature)

                break

    return sorted(features)


# =============================================================================
# FUNCTION DETAIL
# =============================================================================

def function_detail(name, node, analyzer):

    start, end = line_range(node)

    reads = sorted(
        analyzer.feature_reads.get(
            name,
            set()
        )
    )

    writes = sorted(
        analyzer.feature_writes.get(
            name,
            set()
        )
    )

    inputs = sorted(
        analyzer.function_inputs.get(
            name,
            set()
        )
    )

    calls = sorted(
        analyzer.function_calls.get(
            name,
            set()
        )
    )

    source_refs = sorted(
        analyzer.function_sources.get(
            name,
            set()
        )
    )

    if not source_refs:

        source_refs = []

        for sql in analyzer.sql_reads:

            if sql["function"] == name:

                source_refs.append(
                    "execute"
                )

        for call in analyzer.calls:

            if call["function"] == name:

                call_name = call["call"]

                if call_name in {
                    "fetchone",
                    "fetchall",
                    "fetchmany",
                }:

                    source_refs.append(
                        call_name
                    )

    contract = "UNKNOWN"

    if reads and inputs:
        contract = "PRODUCER_WITH_INPUT_CHAIN"

    elif reads:
        contract = "PRODUCER_FEATURE_ONLY"

    elif inputs:
        contract = "INPUT_ONLY"

    if writes:
        contract = "FEATURE_PRODUCER"

    return {
        "function": name,
        "range": f"{start}-{end}",
        "features": reads,
        "feature_writes": writes,
        "inputs": inputs,
        "calls": calls,
        "sources": sorted(set(source_refs)),
        "contract": contract,
    }


# =============================================================================
# DATABASE FORENSICS
# =============================================================================

def inspect_database(db_path):

    result = {
        "exists": False,
        "table_exists": False,
        "columns": [],
        "row_count": 0,
        "non_null_counts": {},
        "sample_rows": [],
    }

    if not os.path.exists(db_path):
        return result

    result["exists"] = True

    conn = sqlite3.connect(
        f"file:{db_path}?mode=ro",
        uri=True
    )

    try:

        conn.execute(
            "PRAGMA query_only = 1"
        )

        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (TARGET_TABLE,)
        ).fetchone()

        if not table:
            return result

        result["table_exists"] = True

        columns = conn.execute(
            f"PRAGMA table_info({TARGET_TABLE})"
        ).fetchall()

        result["columns"] = [
            row[1]
            for row in columns
        ]

        result["row_count"] = conn.execute(
            f"SELECT COUNT(*) FROM {TARGET_TABLE}"
        ).fetchone()[0]

        technical_features = (
            set(EngineAnalyzer.TECHNICAL_FEATURES)
            & set(result["columns"])
        )

        for feature in sorted(
            technical_features
        ):

            count = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {TARGET_TABLE}
                WHERE "{feature}" IS NOT NULL
                """
            ).fetchone()[0]

            result["non_null_counts"][
                feature
            ] = count

        sample_columns = [
            column
            for column in [
                "id",
                "symbol",
                "price",
                "close",
                "history_points",
                "rsi14",
                "atr14",
                "ema20",
                "trend_score",
                "momentum_score",
                "volatility_score",
                "volume_score",
                "technical_completeness",
                "completeness",
            ]
            if column in result["columns"]
        ]

        if sample_columns:

            sql = f"""
                SELECT
                    {", ".join(
                        f'"{c}"'
                        for c in sample_columns
                    )}
                FROM {TARGET_TABLE}
                ORDER BY id DESC
                LIMIT 20
            """

            rows = conn.execute(sql).fetchall()

            result["sample_rows"] = [
                dict(
                    zip(
                        sample_columns,
                        row
                    )
                )
                for row in rows
            ]

    finally:

        conn.close()

    return result


# =============================================================================
# AST PARSE
# =============================================================================

def analyze_engine(engine_path):

    source, had_bom = read_text_readonly(
        engine_path
    )

    tree = ast.parse(
        source,
        filename=engine_path,
        mode="exec"
    )

    analyzer = EngineAnalyzer()

    analyzer.visit(tree)

    return (
        source,
        tree,
        analyzer,
        had_bom,
    )


# =============================================================================
# PRODUCER TRACE
# =============================================================================

def build_real_producer_trace(
    analyzer,
    db_info
):

    trace = []

    db_columns = set(
        db_info.get(
            "columns",
            []
        )
    )

    populated_features = {
        feature
        for feature, count
        in db_info.get(
            "non_null_counts",
            {}
        ).items()
        if count > 0
    }

    for name, node in analyzer.functions.items():

        detail = function_detail(
            name,
            node,
            analyzer
        )

        evidence = set(
            detail["features"]
        )

        evidence &= db_columns

        populated_evidence = (
            evidence
            & populated_features
        )

        score = 0

        if populated_evidence:
            score += 10

        if detail["inputs"]:
            score += 5

        if detail["sources"]:
            score += 5

        if detail["calls"]:
            score += 2

        if detail["contract"] in {
            "PRODUCER_WITH_INPUT_CHAIN",
            "FEATURE_PRODUCER",
        }:
            score += 5

        if detail["feature_writes"]:
            score += 5

        detail["db_backed_features"] = sorted(
            evidence
        )

        detail["populated_features"] = sorted(
            populated_evidence
        )

        detail["lineage_score"] = score

        if (
            detail["features"]
            or detail["inputs"]
            or detail["sources"]
        ):

            trace.append(detail)

    trace.sort(
        key=lambda x: (
            -x["lineage_score"],
            x["function"],
        )
    )

    return trace


# =============================================================================
# PRINTING
# =============================================================================

def print_header(title):

    print("=" * 100)
    print(title)
    print("=" * 100)


def print_sql_forensics(analyzer):

    print()
    print_header(
        "SQL READ / WRITE REFERENCES"
    )

    if analyzer.sql_reads:

        print(
            f"SQL READ REFERENCES : "
            f"{len(analyzer.sql_reads)}"
        )

        for item in analyzer.sql_reads:

            print()
            print(
                f"FUNCTION : "
                f"{item['function']}"
            )

            print(
                f"LINE     : "
                f"{item['line']}"
            )

            print(
                f"SQL      : "
                f"{compact(item['sql'], 300)}"
            )

    else:

        print(
            "SQL READ REFERENCES : NONE"
        )

    print()

    if analyzer.sql_writes:

        print(
            f"SQL WRITE REFERENCES : "
            f"{len(analyzer.sql_writes)}"
        )

        for item in analyzer.sql_writes:

            print()
            print(
                f"FUNCTION : "
                f"{item['function']}"
            )

            print(
                f"LINE     : "
                f"{item['line']}"
            )

            print(
                f"WRITE    : "
                f"{compact(item['sql'], 300)}"
            )

    else:

        print(
            "SQL WRITE REFERENCES : NONE"
        )


def print_trace(trace):

    print()
    print_header(
        "REAL PRODUCER TRACE CANDIDATES"
    )

    for item in trace:

        print()
        print(
            f"[LINEAGE SCORE "
            f"{item['lineage_score']}]"
        )

        print(
            f"FUNCTION : "
            f"{item['function']}"
        )

        print(
            f"RANGE    : "
            f"{item['range']}"
        )

        print(
            f"CONTRACT : "
            f"{item['contract']}"
        )

        print(
            "FEATURES : "
            + (
                ", ".join(
                    item["features"]
                )
                if item["features"]
                else "NONE"
            )
        )

        print(
            "DB-BACKED FEATURES : "
            + (
                ", ".join(
                    item["db_backed_features"]
                )
                if item["db_backed_features"]
                else "NONE"
            )
        )

        print(
            "POPULATED FEATURES : "
            + (
                ", ".join(
                    item["populated_features"]
                )
                if item["populated_features"]
                else "NONE"
            )
        )

        print(
            "INPUTS   : "
            + (
                ", ".join(
                    item["inputs"]
                )
                if item["inputs"]
                else "NONE"
            )
        )

        print(
            "CALLS    : "
            + (
                ", ".join(
                    item["calls"]
                )
                if item["calls"]
                else "NONE"
            )
        )

        print(
            "SOURCES  : "
            + (
                ", ".join(
                    item["sources"]
                )
                if item["sources"]
                else "NONE"
            )
        )


def print_database_population(db_info):

    print()
    print_header(
        "PERSISTED MARKET TECHNICAL POPULATION"
    )

    if not db_info["exists"]:

        print(
            "DATABASE : NOT FOUND"
        )

        return

    if not db_info["table_exists"]:

        print(
            f"TABLE {TARGET_TABLE} : NOT FOUND"
        )

        return

    print(
        f"TABLE        : {TARGET_TABLE}"
    )

    print(
        f"ROWS         : "
        f"{db_info['row_count']}"
    )

    print()

    print(
        f"{'FEATURE':<32}"
        f"{'NON-NULL':>12}"
        f"{'ROWS':>12}"
    )

    print("-" * 60)

    total = db_info["row_count"]

    for feature, count in sorted(
        db_info["non_null_counts"].items()
    ):

        print(
            f"{feature:<32}"
            f"{count:>12}"
            f"{total:>12}"
        )


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def print_final_contract(
    source,
    had_bom,
    analyzer,
    trace,
    db_info
):

    technical_write_refs = len(
        db_info.get(
            "technical_write_references",
            []
        )
    )

    feature_union = set()

    for item in trace:

        feature_union.update(
            item["db_backed_features"]
        )

    print()
    print_header(
        "FINAL REAL PRODUCER TRACE CONTRACT"
    )

    print(
        f"Target Engine                 : "
        f"market_technical_engine.py"
    )

    print(
        f"Engine Source Lines           : "
        f"{len(source.splitlines())}"
    )

    print(
        f"Producer Functions            : "
        f"{len(trace)}"
    )

    print(
        f"Features With Producer Evidence: "
        f"{len(feature_union)}"
    )

    print(
        f"Persisted market_technical Rows : "
        f"{db_info.get('row_count', 0)}"
    )

    print(
        f"Technical SQL Write References : "
        f"{technical_write_refs}"
    )

    print()

    print(
        f"UTF-8 BOM Present              : "
        f"{'YES' if had_bom else 'NO'}"
    )

    if had_bom:

        print(
            "BOM Handling                   : "
            "STRIPPED IN MEMORY ONLY"
        )

        print(
            "SOURCE MODIFICATION            : NONE"
        )

    print()

    print(
        "READ ONLY                       : YES"
    )

    print(
        "SQLite mode                     : mode=ro"
    )

    print(
        "query_only                      : 1"
    )

    print(
        "INSERT                          : NONE"
    )

    print(
        "UPDATE                          : NONE"
    )

    print(
        "DELETE                          : NONE"
    )

    print(
        "ALTER                           : NONE"
    )

    print(
        "CREATE                          : NONE"
    )

    print(
        "DROP                            : NONE"
    )

    print(
        "REPLACE                         : NONE"
    )

    print(
        "COMMIT                          : NONE"
    )

    print(
        "SOURCE MODIFICATION             : NONE"
    )

    print(
        "SYNTHETIC DATA                  : NONE"
    )

    print(
        "INTERPOLATION                   : NONE"
    )

    print(
        "FORWARD FILL                    : NONE"
    )

    print(
        "BACK FILL                       : NONE"
    )

    print()

    print(
        "FORENSIC STATUS                 : COMPLETE"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This forensic executes no production"
    )

    print(
        "business logic."
    )

    print(
        "It parses the actual production engine"
    )

    print(
        "source and maps real functions to"
    )

    print(
        "persisted technical features."
    )

    print(
        "UTF-8 BOM, when present, is removed"
    )

    print(
        "only from the in-memory AST input."
    )

    print(
        "The production engine file is never"
    )

    print(
        "rewritten."
    )

    print(
        "The production database is never"
    )

    print(
        "modified."
    )

    print(
        "No synthetic data is generated."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        SCRIPT_NAME
    )

    print(
        "MODE            : READ ONLY"
    )

    print(
        "TARGET          : market_technical_engine.py"
    )

    print(
        f"DATABASE        : {DB_PATH}"
    )

    print(
        "EXECUTION       : NO"
    )

    print(
        "SOURCE MODIFY   : NO"
    )

    print(
        "DB MODIFY       : NO"
    )

    print(
        f"TARGET PATH     : {ENGINE_PATH}"
    )

    print()

    if not os.path.exists(
        ENGINE_PATH
    ):

        print_header(
            "TARGET ENGINE NOT FOUND"
        )

        print(
            ENGINE_PATH
        )

        sys.exit(1)

    # -------------------------------------------------------------------------
    # ENGINE AST
    # -------------------------------------------------------------------------

    try:

        (
            source,
            tree,
            analyzer,
            had_bom,
        ) = analyze_engine(
            ENGINE_PATH
        )

    except SyntaxError as exc:

        print_header(
            "TARGET ENGINE AST PARSE ERROR"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        print()

        print(
            "NOTE:"
        )

        print(
            "If this is another genuine source syntax"
        )

        print(
            "error after BOM normalization, production"
        )

        print(
            "source must be inspected before any repair."
        )

        sys.exit(2)

    except Exception as exc:

        print_header(
            "TARGET ENGINE READ ERROR"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        sys.exit(3)

    # -------------------------------------------------------------------------
    # DB
    # -------------------------------------------------------------------------

    db_info = inspect_database(
        DB_PATH
    )

    # -------------------------------------------------------------------------
    # TRACE
    # -------------------------------------------------------------------------

    trace = build_real_producer_trace(
        analyzer,
        db_info
    )

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

    print_header(
        "ENGINE NORMALIZATION"
    )

    print(
        f"UTF-8 BOM PRESENT : "
        f"{'YES' if had_bom else 'NO'}"
    )

    if had_bom:

        print(
            "AST INPUT         : BOM REMOVED IN MEMORY"
        )

        print(
            "FILE WRITE         : NONE"
        )

    else:

        print(
            "AST INPUT         : ORIGINAL UTF-8"
        )

    print()

    print(
        f"AST FUNCTIONS      : "
        f"{len(analyzer.functions)}"
    )

    print(
        f"AST CALLS          : "
        f"{len(analyzer.calls)}"
    )

    print(
        f"SQL READS          : "
        f"{len(analyzer.sql_reads)}"
    )

    print(
        f"SQL WRITES         : "
        f"{len(analyzer.sql_writes)}"
    )

    print(
        f"Technical Features : "
        f"{len(extract_feature_mentions(source, analyzer))}"
    )

    print_sql_forensics(
        analyzer
    )

    print_database_population(
        db_info
    )

    print_trace(
        trace
    )

    # -------------------------------------------------------------------------
    # TECHNICAL WRITE REFERENCES
    # -------------------------------------------------------------------------

    technical_write_references = []

    for item in analyzer.sql_writes:

        sql_text = str(
            item.get(
                "sql",
                ""
            )
        ).lower()

        if TARGET_TABLE.lower() in sql_text:

            technical_write_references.append(
                item
            )

    db_info[
        "technical_write_references"
    ] = technical_write_references

    print()
    print_header(
        "TECHNICAL WRITE FORENSIC"
    )

    if technical_write_references:

        print(
            f"Technical Write References : "
            f"{len(technical_write_references)}"
        )

        for item in technical_write_references:

            print()

            print(
                f"FUNCTION : "
                f"{item['function']}"
            )

            print(
                f"LINE     : "
                f"{item['line']}"
            )

            print(
                f"REFERENCE: "
                f"{compact(item['sql'], 300)}"
            )

    else:

        print(
            "Technical Write References : NONE"
        )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print_final_contract(
        source,
        had_bom,
        analyzer,
        trace,
        db_info
    )

    print()
    print("=" * 100)

    print(
        "ARUNDA TRADER MARKET TECHNICAL "
        "REAL PRODUCER TRACE FORENSIC v0.1 COMPLETE"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()