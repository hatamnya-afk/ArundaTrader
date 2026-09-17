import ast
import inspect
import os
import re
import sqlite3
import sys
import time
import traceback
from collections import defaultdict

# =============================================================================
# ARUNDA
# INDICATOR_RUNTIME_ROWS_VS_STORED_POSTCALC_ASSIGNMENT_FORENSIC_AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Compare the ACTUAL runtime rows entering calculate_analysis() against the
# corresponding stored market_data rows, then trace:
#
#     runtime rows
#          |
#          v
#     calculate_analysis()
#          |
#          v
#     returned analysis dict
#          |
#          v
#     post-calculation assignment
#          |
#          v
#     SQL parameter tuple
#          |
#          v
#     stored market_data row
#
# SAFETY
# ------
# READ ONLY FORENSICS
# No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP / REPLACE
# All production writes are intercepted.
#
# IMPORTANT
# ---------
# This script does NOT modify market_data_engine.py.
# This script does NOT modify arunda.db.
# Runtime production execution is observed in memory only.
#
# =============================================================================


PROJECT_PATH = r"C:\Users\ASUS\ArundaTrader"
ENGINE_PATH = os.path.join(PROJECT_PATH, "market_data_engine.py")
DATABASE_PATH = os.path.join(PROJECT_PATH, "arunda.db")

TARGETS = ["BTC", "ETH", "SOL", "XRP"]

OUTPUT_SEPARATOR = "=" * 100
SUB_SEPARATOR = "-" * 100

START_TIME = time.time()


# =============================================================================
# GLOBAL FORENSIC STATE
# =============================================================================

runtime_rows_captured = []
runtime_returns = []
runtime_exceptions = []

sql_trace = []
blocked_write_operations = []

calculate_analysis_call_count = 0

current_runtime_symbol = None
current_runtime_rows = None

postcalc_assignment_observations = []

original_sqlite_connect = sqlite3.connect
original_calculate_analysis = None


# =============================================================================
# SAFETY CLASSIFICATION
# =============================================================================

WRITE_SQL_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)

WRITE_SQL_WORDS = (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "ALTER ",
    "CREATE ",
    "DROP ",
    "REPLACE ",
    "VACUUM ",
    "REINDEX ",
    "ATTACH ",
    "DETACH ",
)


def normalize_sql(sql):
    if sql is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(sql).strip()
    ).upper()


def is_write_like_sql(sql):
    normalized = normalize_sql(sql)

    if not normalized:
        return False

    for prefix in WRITE_SQL_PREFIXES:
        if normalized.startswith(prefix):
            return True

    for word in WRITE_SQL_WORDS:
        if word in normalized:
            return True

    return False


# =============================================================================
# READ-ONLY FORENSIC CURSOR
# =============================================================================

class ForensicCursor:
    """
    Cursor wrapper.

    SELECT / PRAGMA / EXPLAIN are executed against the real read-only
    connection.

    Write-like SQL is NEVER sent to SQLite.

    Instead it is recorded and converted into a harmless no-op so that the
    genuine production runtime can continue far enough to reach
    calculate_analysis() and its post-calculation path.
    """

    def __init__(self, real_cursor):
        self._cursor = real_cursor
        self._last_write_blocked = False

    def execute(self, sql, parameters=()):
        normalized = normalize_sql(sql)
        write_like = is_write_like_sql(sql)

        trace = {
            "sql": str(sql),
            "normalized_sql": normalized,
            "parameters": safe_repr(parameters),
            "write_like": write_like,
            "blocked": False,
            "runtime_symbol": current_runtime_symbol,
        }

        if write_like:
            trace["blocked"] = True
            blocked_write_operations.append(trace)
            sql_trace.append(trace)

            self._last_write_blocked = True

            return self

        self._last_write_blocked = False

        sql_trace.append(trace)

        self._cursor.execute(
            sql,
            parameters
        )

        return self

    def executemany(self, sql, seq_of_parameters):
        write_like = is_write_like_sql(sql)

        materialized = list(seq_of_parameters)

        trace = {
            "sql": str(sql),
            "normalized_sql": normalize_sql(sql),
            "parameters": safe_repr(materialized),
            "write_like": write_like,
            "blocked": write_like,
            "executemany": True,
            "runtime_symbol": current_runtime_symbol,
        }

        sql_trace.append(trace)

        if write_like:
            blocked_write_operations.append(trace)
            return self

        self._cursor.executemany(
            sql,
            materialized
        )

        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size=None):
        if size is None:
            return self._cursor.fetchmany()

        return self._cursor.fetchmany(size)

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def __getattr__(self, name):
        return getattr(self._cursor, name)


# =============================================================================
# READ-ONLY FORENSIC CONNECTION
# =============================================================================

class ForensicConnection:
    """
    Real SQLite connection opened read-only.

    The connection itself cannot write.

    The cursor additionally intercepts write-like statements before they reach
    SQLite, allowing production execution to continue for forensic purposes.
    """

    def __init__(self, real_connection):
        self._connection = real_connection

    def cursor(self, *args, **kwargs):
        return ForensicCursor(
            self._connection.cursor(*args, **kwargs)
        )

    def execute(self, sql, parameters=()):
        cursor = self.cursor()

        cursor.execute(
            sql,
            parameters
        )

        return cursor

    def executemany(self, sql, seq_of_parameters):
        cursor = self.cursor()

        cursor.executemany(
            sql,
            seq_of_parameters
        )

        return cursor

    def executescript(self, script):
        statements = [
            part.strip()
            for part in script.split(";")
            if part.strip()
        ]

        cursor = self.cursor()

        for statement in statements:
            cursor.execute(statement)

        return cursor

    def commit(self):
        blocked_write_operations.append({
            "operation": "commit",
            "blocked": True,
            "runtime_symbol": current_runtime_symbol,
        })

        return None

    def rollback(self):
        return self._connection.rollback()

    def close(self):
        return self._connection.close()

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback_obj):
        return self._connection.__exit__(
            exc_type,
            exc_value,
            traceback_obj
        )

    def __getattr__(self, name):
        return getattr(self._connection, name)


# =============================================================================
# SQLITE READ-ONLY CONNECTION FACTORY
# =============================================================================

def forensic_sqlite_connect(database, *args, **kwargs):
    """
    Force every production connection to SQLite URI read-only mode.
    """

    database_string = str(database)

    if database_string.startswith("file:"):
        uri = database_string

    else:
        absolute_path = os.path.abspath(database_string)

        uri = (
            "file:"
            + absolute_path.replace("\\", "/")
            + "?mode=ro"
        )

    connection = original_sqlite_connect(
        uri,
        uri=True
    )

    try:
        connection.row_factory = sqlite3.Row
    except Exception:
        pass

    return ForensicConnection(connection)


# =============================================================================
# SAFE REPRESENTATION
# =============================================================================

def safe_repr(value, max_length=12000):
    try:
        text = repr(value)
    except Exception:
        text = "<UNREPRESENTABLE>"

    if len(text) > max_length:
        return text[:max_length] + "...<TRUNCATED>"

    return text


# =============================================================================
# ROW NORMALIZATION
# =============================================================================

def row_to_dict(row):
    if isinstance(row, sqlite3.Row):
        return {
            key: row[key]
            for key in row.keys()
        }

    if isinstance(row, dict):
        return dict(row)

    if hasattr(row, "keys"):
        try:
            return {
                key: row[key]
                for key in row.keys()
            }
        except Exception:
            pass

    if isinstance(row, (tuple, list)):
        return {
            str(index): value
            for index, value in enumerate(row)
        }

    return {
        "__value__": row
    }


def normalize_rows(rows):
    normalized = []

    for row in rows:
        normalized.append(
            row_to_dict(row)
        )

    return normalized


# =============================================================================
# SYMBOL RESOLUTION
# =============================================================================

def resolve_symbol_from_rows(rows):
    if not rows:
        return None

    first = row_to_dict(rows[0])

    for key in (
        "symbol",
        "ticker",
        "asset",
        "name",
    ):
        if key in first:
            value = first.get(key)

            if value is not None:
                text = str(value).upper()

                if text in TARGETS:
                    return text

                for target in TARGETS:
                    if text.startswith(target):
                        return target

    return None


# =============================================================================
# RUNTIME calculate_analysis WRAPPER
# =============================================================================

def forensic_calculate_analysis(rows):
    global calculate_analysis_call_count
    global current_runtime_symbol
    global current_runtime_rows

    calculate_analysis_call_count += 1

    symbol = resolve_symbol_from_rows(rows)

    current_runtime_symbol = symbol
    current_runtime_rows = rows

    normalized_rows = normalize_rows(rows)

    captured = {
        "call_number": calculate_analysis_call_count,
        "symbol": symbol,
        "row_count": len(rows) if rows is not None else 0,
        "rows": normalized_rows,
    }

    runtime_rows_captured.append(
        captured
    )

    try:
        result = original_calculate_analysis(
            rows
        )

        runtime_returns.append({
            "call_number": calculate_analysis_call_count,
            "symbol": symbol,
            "result": row_to_dict(result)
            if isinstance(result, dict)
            else result,
        })

        return result

    except Exception as exc:
        runtime_exceptions.append({
            "call_number": calculate_analysis_call_count,
            "symbol": symbol,
            "exception": repr(exc),
            "traceback": traceback.format_exc(),
        })

        raise

    finally:
        current_runtime_symbol = None
        current_runtime_rows = None


# =============================================================================
# STORED MARKET_DATA RETRIEVAL
# =============================================================================

def open_direct_readonly_database():
    connection = original_sqlite_connect(
        "file:"
        + os.path.abspath(DATABASE_PATH).replace("\\", "/")
        + "?mode=ro",
        uri=True
    )

    connection.row_factory = sqlite3.Row

    return connection


def get_stored_target_rows(symbol, limit=120):
    connection = open_direct_readonly_database()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                *
            FROM market_data
            WHERE symbol = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (
                symbol,
                limit,
            )
        )

        rows = cursor.fetchall()

        return normalize_rows(rows)

    finally:
        connection.close()


# =============================================================================
# STORED TARGET LATEST WINDOW
# =============================================================================

def get_latest_stored_rows(symbol, limit=120):
    connection = open_direct_readonly_database()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                *
            FROM market_data
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                symbol,
                limit,
            )
        )

        rows = cursor.fetchall()

        rows = list(reversed(rows))

        return normalize_rows(rows)

    finally:
        connection.close()


# =============================================================================
# ROW IDENTITY
# =============================================================================

def row_identity(row):
    return (
        row.get("id"),
        row.get("timestamp"),
        row.get("symbol"),
        row.get("timeframe"),
    )


def compare_runtime_rows_to_stored(
    runtime_rows,
    stored_rows
):
    runtime_map = {
        row_identity(row): row
        for row in runtime_rows
    }

    stored_map = {
        row_identity(row): row
        for row in stored_rows
    }

    common_keys = sorted(
        set(runtime_map).intersection(
            set(stored_map)
        ),
        key=lambda value: (
            str(value[0]),
            str(value[1]),
        )
    )

    runtime_only = [
        key
        for key in runtime_map
        if key not in stored_map
    ]

    stored_only = [
        key
        for key in stored_map
        if key not in runtime_map
    ]

    return {
        "runtime_count": len(runtime_rows),
        "stored_count": len(stored_rows),
        "common_count": len(common_keys),
        "runtime_only": runtime_only,
        "stored_only": stored_only,
        "common_keys": common_keys,
        "runtime_map": runtime_map,
        "stored_map": stored_map,
    }


# =============================================================================
# NUMERIC COMPARISON
# =============================================================================

INDICATOR_COLUMNS = [
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


def numeric_difference(a, b):
    try:
        if a is None or b is None:
            if a is None and b is None:
                return 0.0

            return None

        return abs(
            float(a) - float(b)
        )

    except Exception:
        return None


def compare_stored_indicator_values(
    runtime_result,
    stored_latest
):
    comparison = []

    if not isinstance(runtime_result, dict):
        return comparison

    for column in INDICATOR_COLUMNS:
        runtime_value = runtime_result.get(
            column
        )

        stored_value = stored_latest.get(
            column
        )

        difference = numeric_difference(
            runtime_value,
            stored_value
        )

        comparison.append({
            "indicator": column,
            "runtime_return": runtime_value,
            "stored_value": stored_value,
            "absolute_difference": difference,
        })

    return comparison


# =============================================================================
# SQL PARAMETER EXTRACTION
# =============================================================================

def get_insert_sql_traces():
    results = []

    for trace in sql_trace:
        sql = trace.get(
            "normalized_sql",
            ""
        )

        if (
            sql.startswith("INSERT ")
            or sql.startswith("REPLACE ")
            or sql.startswith("UPDATE ")
        ):
            results.append(trace)

    return results


# =============================================================================
# SQL PARAMETER HEURISTIC MAPPING
# =============================================================================

def infer_parameter_mapping(sql, parameters):
    """
    Best-effort forensic mapping.

    This does NOT invent values.

    Only positional mappings that can be directly inferred from the INSERT
    column list are reported.
    """

    result = {
        "resolved": False,
        "columns": [],
        "parameters": [],
        "mapping": [],
    }

    if not sql:
        return result

    normalized = str(sql)

    match = re.search(
        r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+\w+\s*"
        r"\((.*?)\)\s*VALUES\s*\((.*?)\)",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return result

    columns_text = match.group(1)
    values_text = match.group(2)

    columns = [
        item.strip().strip('"')
        for item in columns_text.split(",")
    ]

    values = [
        item.strip()
        for item in values_text.split(",")
    ]

    if len(columns) != len(values):
        return result

    if not isinstance(parameters, (tuple, list)):
        return result

    result["columns"] = columns
    result["parameters"] = list(parameters)

    if len(columns) != len(parameters):
        return result

    result["resolved"] = True

    result["mapping"] = [
        {
            "column": column,
            "parameter": parameter,
        }
        for column, parameter in zip(
            columns,
            parameters
        )
    ]

    return result


# =============================================================================
# POST-CALCULATION ASSIGNMENT STATIC TRACE
# =============================================================================

def trace_postcalc_assignment_source():
    observations = []

    if not os.path.exists(ENGINE_PATH):
        return observations

    try:
        with open(
            ENGINE_PATH,
            "r",
            encoding="utf-8"
        ) as handle:
            source = handle.read()

        tree = ast.parse(
            source,
            filename=ENGINE_PATH
        )

    except Exception:
        return observations

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Assign
        ):
            value_text = ast.unparse(
                node.value
            )

            if any(
                token in value_text
                for token in (
                    "analysis",
                    "calculate_analysis",
                    "result",
                    "technical_score",
                    "ema20",
                    "ema50",
                    "rsi14",
                )
            ):
                observations.append({
                    "line": node.lineno,
                    "type": "ASSIGN",
                    "target": ast.unparse(
                        node.targets[0]
                    ),
                    "value": value_text,
                })

        elif isinstance(
            node,
            ast.AnnAssign
        ):
            if node.value is not None:
                value_text = ast.unparse(
                    node.value
                )

                if any(
                    token in value_text
                    for token in (
                        "analysis",
                        "calculate_analysis",
                        "result",
                        "technical_score",
                        "ema20",
                        "ema50",
                        "rsi14",
                    )
                ):
                    observations.append({
                        "line": node.lineno,
                        "type": "ANN_ASSIGN",
                        "target": ast.unparse(
                            node.target
                        ),
                        "value": value_text,
                    })

    return observations


# =============================================================================
# TARGET OUTPUT REPORT
# =============================================================================

def print_target_runtime_report(
    target,
    runtime_capture,
    runtime_result,
    stored_rows,
):
    print()
    print(SUB_SEPARATOR)
    print(
        f"TARGET : {target}"
    )
    print(SUB_SEPARATOR)

    print()
    print("RUNTIME ROW INPUT")
    print("-" * 60)

    print(
        "RUNTIME ROW COUNT :",
        runtime_capture["row_count"]
    )

    if runtime_capture["rows"]:
        first = runtime_capture["rows"][0]
        last = runtime_capture["rows"][-1]

        print(
            "RUNTIME FIRST ID :",
            first.get("id")
        )

        print(
            "RUNTIME LAST ID  :",
            last.get("id")
        )

        print(
            "RUNTIME FIRST TIMESTAMP :",
            first.get("timestamp")
        )

        print(
            "RUNTIME LAST TIMESTAMP  :",
            last.get("timestamp")
        )

    print()
    print("STORED ROW INPUT")
    print("-" * 60)

    print(
        "STORED ROW COUNT :",
        len(stored_rows)
    )

    if stored_rows:
        first = stored_rows[0]
        last = stored_rows[-1]

        print(
            "STORED FIRST ID :",
            first.get("id")
        )

        print(
            "STORED LAST ID  :",
            last.get("id")
        )

        print(
            "STORED FIRST TIMESTAMP :",
            first.get("timestamp")
        )

        print(
            "STORED LAST TIMESTAMP  :",
            last.get("timestamp")
        )

    comparison = compare_runtime_rows_to_stored(
        runtime_capture["rows"],
        stored_rows
    )

    print()
    print("RUNTIME ROWS VS STORED ROWS")
    print("-" * 60)

    print(
        "RUNTIME COUNT :",
        comparison["runtime_count"]
    )

    print(
        "STORED COUNT  :",
        comparison["stored_count"]
    )

    print(
        "COMMON ROWS   :",
        comparison["common_count"]
    )

    print(
        "RUNTIME ONLY  :",
        len(comparison["runtime_only"])
    )

    print(
        "STORED ONLY   :",
        len(comparison["stored_only"])
    )

    if (
        comparison["runtime_count"]
        == comparison["stored_count"]
        == comparison["common_count"]
        and not comparison["runtime_only"]
        and not comparison["stored_only"]
    ):
        print(
            "ROW INPUT STATUS : EXACT_RUNTIME_STORED_MATCH"
        )

    elif comparison["common_count"] > 0:
        print(
            "ROW INPUT STATUS : PARTIAL_RUNTIME_STORED_OVERLAP"
        )

    else:
        print(
            "ROW INPUT STATUS : RUNTIME_STORED_INPUT_DIFFERENCE"
        )

    print()
    print("RUNTIME RETURN")
    print("-" * 60)

    if isinstance(runtime_result, dict):
        for key in (
            "close",
            "volume",
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
        ):
            print(
                f"{key:20s}:",
                runtime_result.get(key)
            )

    else:
        print(
            "RUNTIME RETURN :",
            safe_repr(runtime_result)
        )

    if stored_rows:
        stored_latest = stored_rows[-1]

        indicator_comparison = (
            compare_stored_indicator_values(
                runtime_result,
                stored_latest
            )
        )

        print()
        print("POST-CALCULATION RETURN VS STORED INDICATORS")
        print("-" * 60)

        for item in indicator_comparison:
            print()
            print(
                "INDICATOR :",
                item["indicator"]
            )

            print(
                "RUNTIME RETURN :",
                item["runtime_return"]
            )

            print(
                "STORED VALUE   :",
                item["stored_value"]
            )

            print(
                "ABS DIFFERENCE :",
                item["absolute_difference"]
            )


# =============================================================================
# MAIN FORENSIC EXECUTION
# =============================================================================

def main():
    global original_calculate_analysis

    print(OUTPUT_SEPARATOR)
    print(
        "ARUNDA INDICATOR RUNTIME ROWS VS STORED "
        "POSTCALC ASSIGNMENT FORENSIC AUDIT v0.1"
    )
    print(OUTPUT_SEPARATOR)

    print()
    print("MODE                         : READ ONLY RUNTIME FORENSICS")
    print("DATABASE WRITE               : BLOCKED")
    print("ENGINE WRITE                 : NONE")
    print("PRODUCTION RECALCULATION     : IN-MEMORY OBSERVATION ONLY")
    print(
        "TARGETS                      :",
        " / ".join(TARGETS)
    )

    print()
    print("STEP 1 — PATH SAFETY RESOLUTION")
    print(OUTPUT_SEPARATOR)

    print(
        "PROJECT PATH                 :",
        PROJECT_PATH
    )

    print(
        "ENGINE PATH                  :",
        ENGINE_PATH
    )

    print(
        "ENGINE FOUND                 :",
        os.path.exists(ENGINE_PATH)
    )

    print(
        "DATABASE PATH                :",
        DATABASE_PATH
    )

    print(
        "DATABASE FOUND               :",
        os.path.exists(DATABASE_PATH)
    )

    if not os.path.exists(ENGINE_PATH):
        print("FATAL : ENGINE NOT FOUND")
        return 1

    if not os.path.exists(DATABASE_PATH):
        print("FATAL : DATABASE NOT FOUND")
        return 1

    print()
    print("STEP 2 — STATIC PRODUCTION SOURCE RESOLUTION")
    print(OUTPUT_SEPARATOR)

    try:
        with open(
            ENGINE_PATH,
            "r",
            encoding="utf-8"
        ) as handle:
            source = handle.read()

        tree = ast.parse(
            source,
            filename=ENGINE_PATH
        )

    except Exception as exc:
        print(
            "SOURCE PARSE ERROR :",
            repr(exc)
        )
        return 1

    calculate_defs = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):
            if node.name == "calculate_analysis":
                calculate_defs.append(node)

    print(
        "CALCULATE_ANALYSIS DEFINITIONS :",
        len(calculate_defs)
    )

    if not calculate_defs:
        print("FATAL : calculate_analysis NOT FOUND")
        return 1

    calculate_node = calculate_defs[0]

    print(
        "CALCULATE_ANALYSIS LINE        :",
        calculate_node.lineno
    )

    print()
    print("STEP 3 — POST-CALCULATION STATIC ASSIGNMENT MAP")
    print(OUTPUT_SEPARATOR)

    global postcalc_assignment_observations

    postcalc_assignment_observations = (
        trace_postcalc_assignment_source()
    )

    print(
        "ASSIGNMENT OBSERVATIONS :",
        len(postcalc_assignment_observations)
    )

    for item in postcalc_assignment_observations[:100]:
        print(
            f"[{item['type']}] "
            f"LINE={item['line']} "
            f"{item['target']} = {item['value']}"
        )

    print()
    print("STEP 4 — STORED TARGET RESOLUTION")
    print(OUTPUT_SEPARATOR)

    stored_targets = {}

    for target in TARGETS:
        try:
            rows = get_latest_stored_rows(
                target,
                limit=120
            )

            stored_targets[target] = rows

            if rows:
                print(
                    "[STORED_TARGET_RESOLVED] :",
                    target
                )
            else:
                print(
                    "[STORED_TARGET_MISSING] :",
                    target
                )

        except Exception as exc:
            print(
                "[STORED_TARGET_ERROR] :",
                target,
                repr(exc)
            )

    print()
    print("STEP 5 — SQLITE WRITE BLOCK ACTIVATION")
    print(OUTPUT_SEPARATOR)

    sqlite3.connect = forensic_sqlite_connect

    print(
        "READ-ONLY CONNECTION FACTORY  : ENABLED"
    )

    print(
        "SQLITE AUTHORITATIVE BLOCK     : ENABLED"
    )

    print(
        "WRITE-LIKE SQL BLOCK           : ENABLED"
    )

    print()
    print("STEP 6 — PRODUCTION ENGINE IMPORT")
    print(OUTPUT_SEPARATOR)

    try:
        if PROJECT_PATH not in sys.path:
            sys.path.insert(
                0,
                PROJECT_PATH
            )

        import market_data_engine

        print(
            "MODULE IMPORTED               :",
            "market_data_engine"
        )

    except Exception as exc:
        print(
            "ENGINE IMPORT ERROR :",
            repr(exc)
        )

        traceback.print_exc()

        return 1

    print()
    print("STEP 7 — RUNTIME calculate_analysis PATCH")
    print(OUTPUT_SEPARATOR)

    if not hasattr(
        market_data_engine,
        "calculate_analysis"
    ):
        print(
            "FATAL : calculate_analysis missing"
        )

        return 1

    original_calculate_analysis = (
        market_data_engine.calculate_analysis
    )

    market_data_engine.calculate_analysis = (
        forensic_calculate_analysis
    )

    patched_count = 1

    if hasattr(
        market_data_engine,
        "__dict__"
    ):
        patched_count += 0

    print(
        "PATCHED REFERENCES             :",
        patched_count
    )

    print(
        "[PATCHED] market_data_engine.calculate_analysis"
    )

    print()
    print("STEP 8 — PRODUCTION ENTRYPOINT RESOLUTION")
    print(OUTPUT_SEPARATOR)

    entrypoint = None

    if hasattr(
        market_data_engine,
        "main"
    ):
        entrypoint = market_data_engine.main

        try:
            source_lines, start_line = (
                inspect.getsourcelines(
                    market_data_engine.main
                )
            )

            print(
                "ENTRYPOINT : main"
            )

            print(
                "LINE       :",
                start_line
            )

        except Exception:
            print(
                "ENTRYPOINT : main"
            )

    else:
        print(
            "FATAL : production main() not found"
        )

        return 1

    print()
    print("STEP 9 — ACTUAL PRODUCTION RUNTIME")
    print(OUTPUT_SEPARATOR)

    try:
        entrypoint()

    except Exception as exc:
        runtime_exceptions.append({
            "stage": "production_entrypoint",
            "exception": repr(exc),
            "traceback": traceback.format_exc(),
        })

        print()
        print(
            "PRODUCTION ENTRYPOINT EXCEPTION :",
            repr(exc)
        )

    print()
    print("STEP 10 — RUNTIME ROW CAPTURE SUMMARY")
    print(OUTPUT_SEPARATOR)

    print(
        "CALCULATE_ANALYSIS CALLS :",
        calculate_analysis_call_count
    )

    print(
        "RUNTIME ROW CAPTURES      :",
        len(runtime_rows_captured)
    )

    print(
        "RUNTIME RETURNS           :",
        len(runtime_returns)
    )

    print(
        "RUNTIME EXCEPTIONS        :",
        len(runtime_exceptions)
    )

    print()
    print("STEP 11 — TARGET RUNTIME / STORED COMPARISON")
    print(OUTPUT_SEPARATOR)

    target_runtime_map = {}

    for capture in runtime_rows_captured:

        symbol = capture.get(
            "symbol"
        )

        if symbol not in TARGETS:
            continue

        target_runtime_map[symbol] = capture

    target_return_map = {}

    for item in runtime_returns:

        symbol = item.get(
            "symbol"
        )

        if symbol not in TARGETS:
            continue

        target_return_map[symbol] = item.get(
            "result"
        )

    for target in TARGETS:

        capture = target_runtime_map.get(
            target
        )

        result = target_return_map.get(
            target
        )

        stored_rows = stored_targets.get(
            target,
            []
        )

        if capture is None:
            print()
            print(
                "[RUNTIME_TARGET_NOT_OBSERVED] :",
                target
            )
            continue

        print_target_runtime_report(
            target,
            capture,
            result,
            stored_rows
        )

    print()
    print("STEP 12 — POST-CALCULATION SQL TRACE")
    print(OUTPUT_SEPARATOR)

    insert_traces = (
        get_insert_sql_traces()
    )

    print(
        "SQL TRACE COUNT :",
        len(sql_trace)
    )

    print(
        "INSERT/UPDATE/REPLACE TRACES :",
        len(insert_traces)
    )

    for index, trace in enumerate(
        insert_traces,
        start=1
    ):
        print()
        print(
            f"SQL POSTCALC WRITE TRACE #{index}"
        )

        print(
            "WRITE-LIKE :",
            trace.get("write_like")
        )

        print(
            "BLOCKED    :",
            trace.get("blocked")
        )

        print(
            "SYMBOL     :",
            trace.get("runtime_symbol")
        )

        print(
            "SQL        :"
        )

        print(
            trace.get("sql")
        )

        print(
            "PARAMETERS :",
            trace.get("parameters")
        )

    print()
    print("STEP 13 — WRITE SAFETY VERIFICATION")
    print(OUTPUT_SEPARATOR)

    print(
        "DATABASE CONNECTION MODE       :",
        "READ ONLY"
    )

    print(
        "SQLITE AUTHORITATIVE BLOCK     :",
        "ENABLED"
    )

    print(
        "BLOCKED WRITE OPERATIONS       :",
        len(blocked_write_operations)
    )

    print(
        "WRITE ATTEMPTS                 :",
        "NONE SENT TO SQLITE"
    )

    print()
    print("STEP 14 — FINAL FRONTIER CLASSIFICATION")
    print(OUTPUT_SEPARATOR)

    resolved_targets = 0
    exact_row_matches = 0
    partial_row_matches = 0
    runtime_row_differences = 0
    runtime_returns_observed = 0

    for target in TARGETS:

        capture = target_runtime_map.get(
            target
        )

        result = target_return_map.get(
            target
        )

        stored_rows = stored_targets.get(
            target,
            []
        )

        if capture is None:
            continue

        resolved_targets += 1

        comparison = compare_runtime_rows_to_stored(
            capture["rows"],
            stored_rows
        )

        if (
            comparison["runtime_count"]
            == comparison["stored_count"]
            == comparison["common_count"]
            and not comparison["runtime_only"]
            and not comparison["stored_only"]
        ):
            exact_row_matches += 1

        elif comparison["common_count"] > 0:
            partial_row_matches += 1

        else:
            runtime_row_differences += 1

        if result is not None:
            runtime_returns_observed += 1

    print()
    print(
        "TARGETS REQUESTED             :",
        len(TARGETS)
    )

    print(
        "RUNTIME TARGETS OBSERVED      :",
        resolved_targets
    )

    print(
        "EXACT ROW INPUT MATCHES       :",
        exact_row_matches
    )

    print(
        "PARTIAL ROW INPUT MATCHES     :",
        partial_row_matches
    )

    print(
        "RUNTIME/STORED ROW DIFFERENCES:",
        runtime_row_differences
    )

    print(
        "RUNTIME RETURNS OBSERVED      :",
        runtime_returns_observed
    )

    print()
    print("TARGET MATRIX")
    print(SUB_SEPARATOR)

    for target in TARGETS:

        capture = target_runtime_map.get(
            target
        )

        result = target_return_map.get(
            target
        )

        stored_rows = stored_targets.get(
            target,
            []
        )

        if capture is None:
            print(
                "[RUNTIME_NOT_OBSERVED] :",
                target
            )
            continue

        comparison = compare_runtime_rows_to_stored(
            capture["rows"],
            stored_rows
        )

        if (
            comparison["runtime_count"]
            == comparison["stored_count"]
            == comparison["common_count"]
            and not comparison["runtime_only"]
            and not comparison["stored_only"]
        ):
            print(
                "[RUNTIME_ROWS_EXACTLY_MATCH_STORED] :",
                target
            )

        elif comparison["common_count"] > 0:
            print(
                "[RUNTIME_ROWS_PARTIALLY_MATCH_STORED] :",
                target
            )

        else:
            print(
                "[RUNTIME_ROWS_DIFFER_FROM_STORED] :",
                target
            )

        if result is not None:
            print(
                "[RUNTIME_RETURN_OBSERVED] :",
                target
            )
        else:
            print(
                "[RUNTIME_RETURN_NOT_OBSERVED] :",
                target
            )

    print()
    print("FORENSIC CONCLUSION")
    print(SUB_SEPARATOR)

    if (
        resolved_targets == 0
    ):
        status = (
            "RUNTIME_TARGETS_NOT_OBSERVED"
        )

        meaning = (
            "The production runtime did not expose "
            "target-specific calculate_analysis rows."
        )

        next_frontier = (
            "Trace the exact runtime target-selection and "
            "row-dispatch path."
        )

    elif (
        exact_row_matches == resolved_targets
        and runtime_returns_observed == resolved_targets
    ):
        status = (
            "RUNTIME_ROWS_MATCH_STORED"
        )

        meaning = (
            "The actual runtime rows entering calculate_analysis "
            "match the corresponding stored market_data rows."
        )

        next_frontier = (
            "Trace post-calculation assignment and SQL parameter "
            "mapping because the input rows are no longer the "
            "primary unexplained variable."
        )

    elif (
        runtime_row_differences > 0
    ):
        status = (
            "RUNTIME_ROWS_DIFFER_FROM_STORED"
        )

        meaning = (
            "The actual runtime input rows differ from the "
            "stored market_data reconstruction."
        )

        next_frontier = (
            "Trace runtime row construction / SELECT ordering / "
            "window selection before calculate_analysis."
        )

    else:
        status = (
            "RUNTIME_ROWS_PARTIALLY_MATCHED"
        )

        meaning = (
            "Runtime and stored rows overlap but are not identical."
        )

        next_frontier = (
            "Trace exact runtime SQL result construction, "
            "ordering, filtering and row-window selection."
        )

    print(
        "STATUS                       :",
        status
    )

    print(
        "MEANING                      :",
        meaning
    )

    print(
        "IMPORTANT                    :",
        "No runtime row contents are fabricated."
    )

    print(
        "IMPORTANT                    :",
        "No production formula is modified."
    )

    print(
        "IMPORTANT                    :",
        "No database write is permitted."
    )

    print(
        "NEXT FRONTIER                :",
        next_frontier
    )

    print()
    print(
        "DATABASE WRITE OPERATIONS    : NONE"
    )

    print(
        "ENGINE MODIFICATIONS         : NONE"
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
        "PRODUCTION DB WRITE          : BLOCKED"
    )

    print(
        "ELAPSED SECONDS              :",
        round(
            time.time() - START_TIME,
            3
        )
    )

    print(
        "AUDIT COMPLETE"
    )

    return 0


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    try:
        exit_code = main()

    except Exception as exc:
        print()
        print(
            "FATAL FORENSIC AUDIT ERROR :",
            repr(exc)
        )

        traceback.print_exc()

        exit_code = 1

    finally:
        sqlite3.connect = original_sqlite_connect

    sys.exit(exit_code)