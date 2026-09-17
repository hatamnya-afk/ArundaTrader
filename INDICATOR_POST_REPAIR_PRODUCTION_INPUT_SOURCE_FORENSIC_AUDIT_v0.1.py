import ast
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path.cwd()
ENGINE_PATH = BASE_DIR / "market_data_engine.py"
DB_PATH = BASE_DIR / "arunda.db"

TARGETS = ["BTC", "ETH", "SOL", "XRP"]


def line_end(node):
    return getattr(node, "end_lineno", node.lineno)


def source_lines(text):
    return text.splitlines()


def print_block(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_source_context(lines, start, end, padding=5):
    a = max(1, start - padding)
    b = min(len(lines), end + padding)

    for n in range(a, b + 1):
        marker = ">>>" if start <= n <= end else "   "
        print(f"{marker} {n:4d}: {lines[n - 1]}")


def find_functions(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def find_function_calls(tree, function_names):
    result = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            else:
                continue

            if name in function_names:
                result.append((name, node))

    return result


def assignment_text(node, lines):
    if isinstance(node, ast.Assign):
        return lines[node.lineno - 1].strip()

    if isinstance(node, ast.AnnAssign):
        return lines[node.lineno - 1].strip()

    return ""


def names_in_expression(node):
    names = []

    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            names.append(item.id)

    return names


def find_variable_assignments(tree, variable_names):
    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in variable_names:
                    found.append((target.id, node))

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in variable_names:
                found.append((node.target.id, node))

    return found


def find_parameter_usage(function_node, parameter_name):
    found = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Name):
            if node.id == parameter_name:
                found.append(node)

    return found


def find_calls_to_function(tree, function_name):
    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == function_name:
                found.append(node)

    return found


def nearest_function(tree, target_node):
    result = None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= target_node.lineno <= line_end(node):
                if result is None or node.lineno >= result.lineno:
                    result = node

    return result


def ast_call_signature(call_node):
    parts = []

    for arg in call_node.args:
        try:
            parts.append(ast.unparse(arg))
        except Exception:
            parts.append("<unparse-failed>")

    return ", ".join(parts)


def inspect_engine_source():
    print_block("ARUNDA INDICATOR POST REPAIR PRODUCTION INPUT SOURCE FORENSIC AUDIT v0.1")

    print("MODE                  : READ ONLY")
    print("DATABASE WRITE        : NONE")
    print("ENGINE WRITE          : NONE")
    print("FORMULA WRITE         : NONE")
    print("PRODUCTION RECALCULATION : NONE")
    print("PURPOSE               : TRACE ACTUAL PRODUCTION PRICE INPUT SOURCE")
    print("=" * 100)

    print_block("STEP 1 — ENGINE SOURCE RESOLUTION")

    print(f"ENGINE PATH           : {ENGINE_PATH}")
    print(f"ENGINE FOUND          : {ENGINE_PATH.exists()}")

    if not ENGINE_PATH.exists():
        print("STATUS                : ENGINE_NOT_FOUND")
        return None, None, None

    text = ENGINE_PATH.read_text(encoding="utf-8", errors="replace")
    lines = source_lines(text)

    print(f"SOURCE SIZE           : {len(text)} characters")
    print(f"SOURCE LINES          : {len(lines)}")

    try:
        tree = ast.parse(text)
        print("AST STATUS            : SUCCESS")
    except SyntaxError as exc:
        print("AST STATUS            : FAILED")
        print(f"SYNTAX ERROR          : {exc}")
        return None, None, None

    functions = find_functions(tree)

    print_block("STEP 2 — PRODUCTION FUNCTION INVENTORY")

    for name in [
        "calculate_analysis",
        "ema",
        "ema_series",
        "rsi",
        "macd",
    ]:
        if name in functions:
            node = functions[name]
            print(f"[FOUND] {name}() LINE {node.lineno}-{line_end(node)}")
        else:
            print(f"[NOT FOUND] {name}()")

    print_block("STEP 3 — INDICATOR CONSUMPTION PATH")

    calc = functions.get("calculate_analysis")

    if calc is None:
        print("calculate_analysis() NOT FOUND")
        return tree, functions, lines

    print(
        f"calculate_analysis() : LINE {calc.lineno}-{line_end(calc)}"
    )

    calls = []

    for node in ast.walk(calc):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id

                if name in {"ema", "rsi", "ema_series"}:
                    calls.append((name, node))

    for name, node in calls:
        print()
        print(f"INDICATOR CALL : {name}()")
        print(f"LINE           : {node.lineno}")
        print(f"ARGUMENTS      : {ast_call_signature(node)}")

        print_source_context(
            lines,
            node.lineno,
            line_end(node),
            padding=3
        )

    print_block("STEP 4 — CLOSES VARIABLE ORIGIN")

    close_assignments = find_variable_assignments(
        calc,
        {"closes", "close_prices", "prices", "values"}
    )

    if close_assignments:
        for name, node in close_assignments:
            print(f"[FOUND] VARIABLE : {name}")
            print(f"LINE             : {node.lineno}")
            print(f"ASSIGNMENT       : {assignment_text(node, lines)}")

            print_source_context(
                lines,
                node.lineno,
                line_end(node),
                padding=6
            )
    else:
        print("[NONE] No direct closes/prices assignment found inside calculate_analysis()")

    print_block("STEP 5 — calculate_analysis() CALLERS")

    callers = find_calls_to_function(tree, "calculate_analysis")

    if not callers:
        print("[NONE] No calculate_analysis() call sites found")
    else:
        for index, call in enumerate(callers, 1):
            parent_function = nearest_function(tree, call)

            print()
            print(f"CALLER #{index}")
            print(f"CALL LINE          : {call.lineno}")

            if parent_function:
                print(
                    f"CALLER FUNCTION    : {parent_function.name}() "
                    f"LINE {parent_function.lineno}-{line_end(parent_function)}"
                )
            else:
                print("CALLER FUNCTION    : <module level>")

            print(f"CALL ARGUMENTS     : {ast_call_signature(call)}")

            print_source_context(
                lines,
                call.lineno,
                line_end(call),
                padding=8
            )

    print_block("STEP 6 — FUNCTIONS THAT PRODUCE CLOSES-LIKE DATA")

    candidate_names = {
        "closes",
        "close_prices",
        "prices",
        "values",
        "price_values",
        "price_series",
        "history",
        "market_data",
        "data",
    }

    candidates = find_variable_assignments(tree, candidate_names)

    if candidates:
        for name, node in candidates:
            print(
                f"[FOUND] {name} "
                f"LINE {node.lineno} : {assignment_text(node, lines)}"
            )
    else:
        print("[NONE] No candidate price-series assignments found")

    print_block("STEP 7 — PRODUCTION INPUT CALL GRAPH CANDIDATES")

    relevant_functions = {
        "calculate_analysis",
        "market_data",
        "fetch_market_data",
        "get_market_data",
        "get_prices",
        "get_history",
        "fetch_history",
        "load_history",
        "build_market_data",
        "build_analysis",
        "process_market",
        "process_snapshot",
        "run_snapshot",
        "run",
        "main",
    }

    for name in sorted(relevant_functions):
        if name not in functions:
            continue

        node = functions[name]

        print()
        print(
            f"FUNCTION : {name}() "
            f"LINE {node.lineno}-{line_end(node)}"
        )

        local_calls = []

        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                if isinstance(item.func, ast.Name):
                    called = item.func.id

                    if called in {
                        "calculate_analysis",
                        "get_history",
                        "fetch_history",
                        "load_history",
                        "get_market_data",
                        "fetch_market_data",
                        "get_prices",
                    }:
                        local_calls.append((called, item))

        for called, item in local_calls:
            print(
                f"  -> CALL {called}() "
                f"LINE {item.lineno} "
                f"ARGS [{ast_call_signature(item)}]"
            )

    return tree, functions, lines


def inspect_database():
    print_block("STEP 8 — DATABASE PRODUCTION RECORD RESOLUTION")

    print(f"DATABASE PATH          : {DB_PATH}")
    print(f"DATABASE FOUND         : {DB_PATH.exists()}")

    if not DB_PATH.exists():
        print("STATUS                 : DATABASE_NOT_FOUND")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        print(f"TABLE COUNT            : {len(tables)}")

        for symbol in TARGETS:
            print_block(f"SYMBOL : {symbol}")

            row = conn.execute(
                """
                SELECT *
                FROM market_data
                WHERE symbol = ?
                ORDER BY source_timestamp DESC, id DESC
                LIMIT 1
                """,
                (symbol,)
            ).fetchone()

            if row is None:
                print("[NOT FOUND] market_data production record")
                continue

            print(f"ID                    : {row['id']}")
            print(f"SOURCE TIME           : {row['source_timestamp']}")
            print(f"ENGINE VERSION        : {row['engine_version']}")
            print(f"CLOSE                 : {row['close']}")
            print(f"EMA20                 : {row['ema20']}")
            print(f"EMA50                 : {row['ema50']}")
            print(f"RSI14                 : {row['rsi14']}")

            print()
            print("PRODUCTION INPUT SOURCE REFERENCES")
            print("-" * 100)

            source_time = row["source_timestamp"]

            history_rows = conn.execute(
                """
                SELECT
                    timestamp,
                    price,
                    source,
                    engine_version,
                    cmc_id,
                    symbol
                FROM market_history
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 10
                """,
                (symbol,)
            ).fetchall()

            print(f"HISTORY ROWS RETURNED : {len(history_rows)}")

            for h in history_rows:
                print(
                    f"TIME={h['timestamp']} | "
                    f"PRICE={h['price']} | "
                    f"SOURCE={h['source']} | "
                    f"ENGINE={h['engine_version']} | "
                    f"CMC_ID={h['cmc_id']}"
                )

            print()
            print("EXACT TIMESTAMP CHECK")

            exact = conn.execute(
                """
                SELECT timestamp, price, source, engine_version
                FROM market_history
                WHERE symbol = ?
                  AND timestamp = ?
                LIMIT 5
                """,
                (symbol, source_time)
            ).fetchall()

            print(f"EXACT HISTORY ROWS    : {len(exact)}")

            if exact:
                for item in exact:
                    print(
                        f"[FOUND] {item['timestamp']} | "
                        f"PRICE={item['price']} | "
                        f"SOURCE={item['source']} | "
                        f"ENGINE={item['engine_version']}"
                    )
            else:
                print("[NONE] No exact history timestamp")

            print()
            print("LATEST HISTORY BEFORE PRODUCTION TIME")

            previous = conn.execute(
                """
                SELECT timestamp, price, source, engine_version
                FROM market_history
                WHERE symbol = ?
                  AND timestamp < ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (symbol, source_time)
            ).fetchone()

            if previous:
                print(f"TIMESTAMP             : {previous['timestamp']}")
                print(f"PRICE                 : {previous['price']}")
                print(f"SOURCE                : {previous['source']}")
                print(f"ENGINE                : {previous['engine_version']}")
            else:
                print("[NONE] No history row before production timestamp")

    finally:
        conn.close()


def main():
    tree, functions, lines = inspect_engine_source()

    if tree is None:
        return

    inspect_database()

    print_block("FINAL PRODUCTION INPUT SOURCE FORENSIC SUMMARY")

    print("TARGETS CHECKED        : 4")
    print()
    print("IMPORTANT:")
    print("This audit does NOT modify the engine.")
    print("This audit does NOT modify the database.")
    print("This audit does NOT recalculate production records.")
    print()
    print("The purpose is to establish:")
    print("TARGET -> calculate_analysis() -> closes/prices input -> ACTUAL SOURCE")
    print()
    print("STATUS                 : INPUT_SOURCE_FORENSICS_COMPLETE")
    print("NEXT STEP              : CLASSIFY ACTUAL PRODUCTION INPUT SOURCE")

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("ENGINE MODIFICATIONS      : NONE")
    print("PRODUCTION RECALCULATION  : NONE")
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()
