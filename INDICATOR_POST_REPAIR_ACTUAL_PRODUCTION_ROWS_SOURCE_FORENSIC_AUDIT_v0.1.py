from pathlib import Path
import ast
import sqlite3
import re
import sys

# ============================================================
# ARUNDA
# INDICATOR POST REPAIR ACTUAL PRODUCTION ROWS SOURCE
# FORENSIC AUDIT v0.1
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"
DB_PATH = BASE_DIR / "arunda.db"

TARGET_SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]


# ============================================================
# HELPERS
# ============================================================

def line_of(node):
    return getattr(node, "lineno", None)


def end_line_of(node):
    return getattr(node, "end_lineno", line_of(node))


def source_segment(source, node):
    try:
        return ast.get_source_segment(source, node)
    except Exception:
        return None


def function_inventory(tree):
    result = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append(
                (
                    node.name,
                    line_of(node),
                    end_line_of(node),
                )
            )

    return sorted(result, key=lambda x: (x[1] or 0, x[0]))


def get_function_nodes(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr

    return None


def print_separator(char="=", width=100):
    print(char * width)


def print_header(title):
    print_separator("=")
    print(title)
    print_separator("=")


def print_section(title):
    print()
    print_separator("=")
    print(title)
    print_separator("=")


def normalize_sql(sql):
    if not sql:
        return ""

    sql = re.sub(r"\s+", " ", sql)
    return sql.strip()


# ============================================================
# AST: FIND ASSIGNMENTS TO A VARIABLE
# ============================================================

def find_variable_assignments(function_node, variable_name):
    found = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == variable_name:
                        found.append(node)

        elif isinstance(node, ast.AnnAssign):
            target = node.target

            if isinstance(target, ast.Name):
                if target.id == variable_name:
                    found.append(node)

        elif isinstance(node, ast.NamedExpr):
            target = node.target

            if isinstance(target, ast.Name):
                if target.id == variable_name:
                    found.append(node)

    return sorted(
        found,
        key=lambda x: line_of(x) or 0
    )


# ============================================================
# AST: FIND CALLS THAT PRODUCE A VARIABLE
# ============================================================

def assignment_call_details(source, function_node, variable_name):
    results = []

    for node in find_variable_assignments(
        function_node,
        variable_name
    ):
        value = None

        if isinstance(node, ast.Assign):
            value = node.value

        elif isinstance(node, ast.AnnAssign):
            value = node.value

        elif isinstance(node, ast.NamedExpr):
            value = node.value

        if isinstance(value, ast.Call):
            results.append(
                {
                    "line": line_of(node),
                    "function": call_name(value),
                    "dotted": dotted_name(value),
                    "source": source_segment(source, node),
                }
            )

    return results


# ============================================================
# AST: FIND ALL CALLS TO A FUNCTION
# ============================================================

def find_calls(function_node, target_name):
    found = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            name = call_name(node)

            if name == target_name:
                found.append(node)

    return sorted(
        found,
        key=lambda x: line_of(x) or 0
    )


# ============================================================
# AST: FIND CALLERS OF FUNCTION
# ============================================================

def find_function_callers(tree, target_name):
    callers = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        for call in find_calls(node, target_name):
            callers.append(
                {
                    "caller": node.name,
                    "caller_line": line_of(node),
                    "call_line": line_of(call),
                    "source": None,
                }
            )

    return callers


# ============================================================
# AST: TRACE ROWS PARAMETER
# ============================================================

def inspect_rows_parameter(source, calculate_node):
    print_section(
        "STEP 4 — calculate_analysis(rows) INPUT CONTRACT"
    )

    args = calculate_node.args.args

    print(
        f"FUNCTION : calculate_analysis() "
        f"LINE {line_of(calculate_node)}-{end_line_of(calculate_node)}"
    )

    print()

    for arg in args:
        print(f"PARAMETER : {arg.arg}")

    rows_arg = None

    for arg in args:
        if arg.arg == "rows":
            rows_arg = arg
            break

    if rows_arg is None:
        print()
        print("[MISSING] calculate_analysis() has no parameter named rows")
        return False

    print()
    print("[FOUND] calculate_analysis(rows)")

    return True


# ============================================================
# AST: TRACE CALL ARGUMENT TO calculate_analysis()
# ============================================================

def inspect_calculate_callers(source, tree):
    print_section(
        "STEP 5 — calculate_analysis() CALL-SITE FORENSICS"
    )

    callers = find_function_callers(
        tree,
        "calculate_analysis"
    )

    if not callers:
        print("[MISSING] No calculate_analysis() caller found")
        return []

    functions = get_function_nodes(tree)
    detailed = []

    for item in callers:

        caller_name = item["caller"]
        caller_node = functions.get(caller_name)

        if caller_node is None:
            continue

        for call in find_calls(
            caller_node,
            "calculate_analysis"
        ):

            call_line = line_of(call)

            print()
            print(f"CALLER FUNCTION : {caller_name}()")
            print(f"CALL LINE       : {call_line}")

            if call.args:

                for index, arg in enumerate(call.args):

                    print(
                        f"ARG #{index + 1} : "
                        f"{source_segment(source, arg)}"
                    )

                    if isinstance(arg, ast.Name):
                        variable = arg.id

                        print(
                            f"ARG VARIABLE    : {variable}"
                        )

                        assignments = find_variable_assignments(
                            caller_node,
                            variable
                        )

                        if assignments:
                            print(
                                "VARIABLE ASSIGNMENTS:"
                            )

                            for assignment in assignments:
                                print(
                                    f"  LINE {line_of(assignment)} : "
                                    f"{source_segment(source, assignment)}"
                                )

                        else:
                            print(
                                "  [NONE] Assignment to "
                                f"{variable} not found in caller"
                            )

            else:
                print("[WARNING] calculate_analysis() called without arguments")

            detailed.append(
                (
                    caller_name,
                    call,
                )
            )

    return detailed


# ============================================================
# AST: TRACE VARIABLE BACKWARDS
# ============================================================

def trace_variable_backwards(
    source,
    function_node,
    variable_name,
    depth=0,
    visited=None,
):
    if visited is None:
        visited = set()

    key = (
        function_node.name,
        variable_name,
    )

    if key in visited:
        return

    visited.add(key)

    indent = "    " * depth

    assignments = find_variable_assignments(
        function_node,
        variable_name
    )

    print(
        f"{indent}VARIABLE : {variable_name}"
    )

    if not assignments:
        print(
            f"{indent}[NO ASSIGNMENT FOUND]"
        )
        return

    for assignment in assignments:

        print(
            f"{indent}[ASSIGNMENT] "
            f"LINE {line_of(assignment)}"
        )

        print(
            f"{indent}SOURCE : "
            f"{source_segment(source, assignment)}"
        )

        value = None

        if isinstance(assignment, ast.Assign):
            value = assignment.value

        elif isinstance(assignment, ast.AnnAssign):
            value = assignment.value

        elif isinstance(assignment, ast.NamedExpr):
            value = assignment.value

        if isinstance(value, ast.Call):

            name = call_name(value)

            print(
                f"{indent}CALL     : {name}"
            )

            print(
                f"{indent}CALL LINE : {line_of(value)}"
            )

            for index, arg in enumerate(value.args):

                if isinstance(arg, ast.Name):

                    print(
                        f"{indent}ARG #{index + 1} "
                        f"VARIABLE : {arg.id}"
                    )

                    trace_variable_backwards(
                        source,
                        function_node,
                        arg.id,
                        depth + 1,
                        visited,
                    )

        elif isinstance(value, ast.Name):

            print(
                f"{indent}SOURCE VARIABLE : {value.id}"
            )

            trace_variable_backwards(
                source,
                function_node,
                value.id,
                depth + 1,
                visited,
            )

        elif isinstance(value, (ast.List, ast.Tuple)):

            print(
                f"{indent}SOURCE : literal "
                f"{type(value).__name__}"
            )


# ============================================================
# AST: SQL / DATABASE READS
# ============================================================

def find_database_reads(source, tree):
    print_section(
        "STEP 6 — DATABASE READ SOURCE FORENSICS"
    )

    results = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        name = dotted_name(node.func)

        if name not in {
            "conn.execute",
            "connection.execute",
            "cursor.execute",
            "cur.execute",
            "db.execute",
        }:
            continue

        sql = None

        if node.args:
            first = node.args[0]

            if isinstance(first, ast.Constant):
                if isinstance(first.value, str):
                    sql = first.value

            elif isinstance(first, ast.JoinedStr):
                sql = source_segment(source, first)

        if sql is None:
            sql = source_segment(source, node.args[0]) \
                if node.args else None

        sql_normalized = normalize_sql(sql)

        results.append(
            {
                "line": line_of(node),
                "name": name,
                "sql": sql_normalized,
                "source": source_segment(source, node),
            }
        )

    if not results:
        print(
            "[NONE] No direct execute() database reads resolved"
        )
        return []

    for item in sorted(
        results,
        key=lambda x: x["line"] or 0
    ):

        print()
        print(
            f"[FOUND] {item['name']} "
            f"LINE {item['line']}"
        )

        if item["sql"]:
            print(
                f"SQL : {item['sql']}"
            )

        else:
            print(
                f"SOURCE : {item['source']}"
            )

    return results


# ============================================================
# DATABASE SCHEMA
# ============================================================

def table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def resolve_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    return [
        row[0]
        for row in rows
    ]


# ============================================================
# DATABASE: FIND MARKET_DATA TARGETS
# ============================================================

def resolve_market_data(conn, symbol):
    columns = table_columns(
        conn,
        "market_data"
    )

    required = {
        "id",
        "symbol",
        "source_timestamp",
        "engine_version",
        "close",
        "ema20",
        "ema50",
        "rsi14",
    }

    missing = required - set(columns)

    if missing:
        return None, columns, missing

    query = """
        SELECT
            id,
            symbol,
            source_timestamp,
            engine_version,
            close,
            ema20,
            ema50,
            rsi14
        FROM market_data
        WHERE symbol = ?
        ORDER BY source_timestamp DESC
        LIMIT 1
    """

    row = conn.execute(
        query,
        (symbol,)
    ).fetchone()

    return row, columns, set()


# ============================================================
# DATABASE: IDENTIFY POSSIBLE SOURCE TABLES
# ============================================================

def inspect_source_tables(conn):
    print_section(
        "STEP 7 — DATABASE SOURCE TABLE INVENTORY"
    )

    tables = resolve_tables(conn)

    for table in tables:

        try:
            columns = table_columns(
                conn,
                table
            )
        except Exception:
            continue

        interesting = []

        for column in columns:
            lower = column.lower()

            if any(
                token in lower
                for token in (
                    "price",
                    "close",
                    "timestamp",
                    "symbol",
                    "cmc",
                    "market",
                )
            ):
                interesting.append(column)

        if interesting:

            print()
            print(
                f"[TABLE] {table}"
            )

            print(
                "COLUMNS : "
                + ", ".join(interesting)
            )


# ============================================================
# DATABASE: RESOLVE ACTUAL ROW SOURCE CANDIDATES
# ============================================================

def inspect_symbol_source_candidates(
    conn,
    symbol,
    production_time,
):
    print_section(
        f"STEP 8 — ACTUAL ROW SOURCE CANDIDATES : {symbol}"
    )

    tables = resolve_tables(conn)

    timestamp_tokens = {
        "source_timestamp",
        "timestamp",
        "time",
        "created_at",
        "updated_at",
    }

    symbol_tokens = {
        "symbol",
        "ticker",
        "asset",
    }

    price_tokens = {
        "price",
        "close",
        "last_price",
        "current_price",
    }

    candidates = []

    for table in tables:

        try:
            columns = table_columns(
                conn,
                table
            )
        except Exception:
            continue

        lower_map = {
            c.lower(): c
            for c in columns
        }

        timestamp_col = None
        symbol_col = None
        price_col = None

        for token in timestamp_tokens:
            if token in lower_map:
                timestamp_col = lower_map[token]
                break

        for token in symbol_tokens:
            if token in lower_map:
                symbol_col = lower_map[token]
                break

        for token in price_tokens:
            if token in lower_map:
                price_col = lower_map[token]
                break

        if not (
            timestamp_col
            and symbol_col
            and price_col
        ):
            continue

        query = f"""
            SELECT
                "{timestamp_col}",
                "{price_col}"
            FROM "{table}"
            WHERE "{symbol_col}" = ?
            ORDER BY "{timestamp_col}" DESC
            LIMIT 5
        """

        try:
            rows = conn.execute(
                query,
                (symbol,)
            ).fetchall()

        except Exception:
            continue

        if not rows:
            continue

        print()
        print(
            f"[CANDIDATE TABLE] {table}"
        )

        print(
            f"SYMBOL COLUMN    : {symbol_col}"
        )

        print(
            f"TIMESTAMP COLUMN : {timestamp_col}"
        )

        print(
            f"PRICE COLUMN     : {price_col}"
        )

        print(
            f"ROWS FOUND       : {len(rows)}"
        )

        for row in rows:
            print(
                f"  TIME={row[0]} | PRICE={row[1]}"
            )

        candidates.append(
            {
                "table": table,
                "symbol_column": symbol_col,
                "timestamp_column": timestamp_col,
                "price_column": price_col,
                "rows": rows,
            }
        )

    if not candidates:
        print(
            "[NONE] No database table with "
            "symbol + timestamp + price/close "
            "source pattern resolved"
        )

    return candidates


# ============================================================
# MAIN
# ============================================================

def main():

    print_header(
        "ARUNDA INDICATOR POST REPAIR ACTUAL PRODUCTION "
        "ROWS SOURCE FORENSIC AUDIT v0.1"
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
        "PURPOSE               : TRACE ACTUAL PRODUCTION "
        "ROWS SOURCE"
    )

    print_section(
        "STEP 1 — ENGINE SOURCE RESOLUTION"
    )

    print(
        f"ENGINE PATH           : {ENGINE_PATH}"
    )

    print(
        f"ENGINE FOUND          : {ENGINE_PATH.exists()}"
    )

    if not ENGINE_PATH.exists():
        print(
            "STATUS                : ENGINE_NOT_FOUND"
        )
        return 1

    source = ENGINE_PATH.read_text(
        encoding="utf-8"
    )

    print(
        f"SOURCE SIZE           : {len(source)} characters"
    )

    print(
        f"SOURCE LINES          : {len(source.splitlines())}"
    )

    try:
        tree = ast.parse(source)
        print(
            "AST STATUS            : SUCCESS"
        )
    except SyntaxError as exc:
        print(
            "AST STATUS            : FAILED"
        )
        print(
            f"ERROR                 : {exc}"
        )
        return 1

    print_section(
        "STEP 2 — PRODUCTION FUNCTION INVENTORY"
    )

    functions = function_inventory(tree)

    for name, start, end in functions:

        if name in {
            "main",
            "calculate_analysis",
            "ema",
            "ema_series",
            "rsi",
            "macd",
        }:

            print(
                f"[FOUND] {name}() "
                f"LINE {start}-{end}"
            )

    function_nodes = get_function_nodes(tree)

    calculate_node = function_nodes.get(
        "calculate_analysis"
    )

    main_node = function_nodes.get(
        "main"
    )

    if calculate_node is None:
        print(
            "[MISSING] calculate_analysis()"
        )
        return 1

    if main_node is None:
        print(
            "[MISSING] main()"
        )
        return 1

    inspect_rows_parameter(
        source,
        calculate_node
    )

    print_section(
        "STEP 3 — PRODUCTION INDICATOR CONSUMPTION"
    )

    indicator_calls = {
        "EMA20": [],
        "EMA50": [],
        "RSI14": [],
    }

    for node in ast.walk(calculate_node):

        if not isinstance(node, ast.Assign):
            continue

        if not isinstance(node.value, ast.Call):
            continue

        target_names = []

        for target in node.targets:
            if isinstance(target, ast.Name):
                target_names.append(
                    target.id
                )

        call = node.value

        name = call_name(call)

        if name == "ema":

            if len(call.args) >= 2:

                period_arg = call.args[1]

                if (
                    isinstance(
                        period_arg,
                        ast.Constant
                    )
                    and period_arg.value == 20
                ):
                    indicator_calls["EMA20"].append(node)

                elif (
                    isinstance(
                        period_arg,
                        ast.Constant
                    )
                    and period_arg.value == 50
                ):
                    indicator_calls["EMA50"].append(node)

        elif name == "rsi":

            if len(call.args) >= 2:

                period_arg = call.args[1]

                if (
                    isinstance(
                        period_arg,
                        ast.Constant
                    )
                    and period_arg.value == 14
                ):
                    indicator_calls["RSI14"].append(node)

    for indicator, nodes in indicator_calls.items():

        print()
        print(
            f"INDICATOR : {indicator}"
        )

        if not nodes:
            print(
                "[MISSING] No exact production call resolved"
            )
            continue

        for node in nodes:

            print(
                f"[FOUND] LINE {line_of(node)}"
            )

            print(
                f"SOURCE : "
                f"{source_segment(source, node)}"
            )

    print_section(
        "STEP 4 — calculate_analysis(rows) INPUT CONTRACT"
    )

    print(
        "Tracing the actual parameter named 'rows' "
        "without modifying production code."
    )

    print_section(
        "STEP 5 — calculate_analysis() CALL-SITE FORENSICS"
    )

    call_details = inspect_calculate_callers(
        source,
        tree
    )

    print_section(
        "STEP 6 — BACKWARD VARIABLE TRACE"
    )

    for caller_name, call in call_details:

        if not call.args:
            continue

        first_arg = call.args[0]

        if not isinstance(
            first_arg,
            ast.Name
        ):
            print(
                f"CALL LINE {line_of(call)} "
                f"uses non-variable argument:"
            )

            print(
                source_segment(
                    source,
                    first_arg
                )
            )

            continue

        variable_name = first_arg.id

        caller_node = function_nodes.get(
            caller_name
        )

        if caller_node is None:
            continue

        print()
        print(
            f"TRACE FROM : "
            f"{caller_name}() "
            f"LINE {line_of(call)}"
        )

        trace_variable_backwards(
            source,
            caller_node,
            variable_name,
        )

    database_reads = find_database_reads(
        source,
        tree
    )

    print_section(
        "STEP 7 — DATABASE RESOLUTION"
    )

    print(
        f"DATABASE PATH          : {DB_PATH}"
    )

    print(
        f"DATABASE FOUND         : {DB_PATH.exists()}"
    )

    if not DB_PATH.exists():
        print(
            "STATUS                 : DATABASE_NOT_FOUND"
        )
        return 1

    try:
        conn = sqlite3.connect(
            str(DB_PATH)
        )
    except Exception as exc:
        print(
            f"DATABASE CONNECTION ERROR : {exc}"
        )
        return 1

    try:

        tables = resolve_tables(conn)

        print(
            f"TABLE COUNT            : {len(tables)}"
        )

        print()

        print(
            "TABLES"
        )

        for table in tables:
            print(
                f"  {table}"
            )

        print_section(
            "STEP 8 — MARKET_DATA PRODUCTION TARGETS"
        )

        target_rows = {}

        for symbol in TARGET_SYMBOLS:

            row, columns, missing = resolve_market_data(
                conn,
                symbol
            )

            print()
            print(
                f"SYMBOL : {symbol}"
            )

            if missing:

                print(
                    "[SCHEMA ERROR] Missing fields:"
                )

                for field in sorted(missing):
                    print(
                        f"  {field}"
                    )

                continue

            if row is None:

                print(
                    "[NONE] No market_data record"
                )

                continue

            (
                record_id,
                db_symbol,
                source_time,
                engine_version,
                close,
                ema20,
                ema50,
                rsi14,
            ) = row

            print(
                f"ID              : {record_id}"
            )

            print(
                f"SOURCE TIME     : {source_time}"
            )

            print(
                f"ENGINE VERSION  : {engine_version}"
            )

            print(
                f"CLOSE           : {close}"
            )

            print(
                f"EMA20           : {ema20}"
            )

            print(
                f"EMA50           : {ema50}"
            )

            print(
                f"RSI14           : {rsi14}"
            )

            target_rows[symbol] = {
                "id": record_id,
                "source_time": source_time,
                "close": close,
                "engine_version": engine_version,
            }

        inspect_source_tables(
            conn
        )

        print_section(
            "STEP 9 — ACTUAL PRODUCTION ROW SOURCE CANDIDATES"
        )

        total_candidates = 0

        for symbol, target in target_rows.items():

            candidates = inspect_symbol_source_candidates(
                conn,
                symbol,
                target["source_time"],
            )

            total_candidates += len(candidates)

        print_section(
            "FINAL ACTUAL PRODUCTION ROWS SOURCE "
            "FORENSIC SUMMARY"
        )

        print(
            f"TARGETS CHECKED              : "
            f"{len(target_rows)}"
        )

        print(
            f"DATABASE READ CALLS FOUND    : "
            f"{len(database_reads)}"
        )

        print(
            f"SOURCE TABLE CANDIDATES      : "
            f"{total_candidates}"
        )

        print()
        print(
            "FORENSIC RULE"
        )

        print(
            "The actual production input is considered "
            "RESOLVED only when:"
        )

        print(
            "  1. calculate_analysis(rows) is resolved"
        )

        print(
            "  2. caller of calculate_analysis() is resolved"
        )

        print(
            "  3. the actual 'rows' variable assignment is resolved"
        )

        print(
            "  4. the database/API/source producing rows is resolved"
        )

        print(
            "  5. the production rows are traceable to the "
            "indicator closes input"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "This audit does NOT modify the engine."
        )

        print(
            "This audit does NOT modify the database."
        )

        print(
            "This audit does NOT recalculate production records."
        )

        print()
        print(
            "STATUS : ACTUAL_ROWS_SOURCE_FORENSICS_COMPLETE"
        )

        print(
            "NEXT STEP : USE ONLY THE RESOLVED ACTUAL "
            "ROWS SOURCE FOR CAUSE DETERMINATION"
        )

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS      : NONE"
        )

        print(
            "PRODUCTION RECALCULATION  : NONE"
        )

        print(
            "AUDIT COMPLETE"
        )

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())