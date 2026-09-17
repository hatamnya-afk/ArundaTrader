import ast
import sqlite3
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"
DB_PATH = BASE_DIR / "arunda.db"

TARGETS = ["BTC", "ETH", "SOL", "XRP"]


def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def node_line(node):
    return getattr(node, "lineno", None)


def end_line(node):
    return getattr(node, "end_lineno", node_line(node))


def source_segment(lines, node, radius=2):
    line = node_line(node)
    if line is None:
        return []

    start = max(1, line - radius)
    end = min(len(lines), end_line(node) + radius)

    result = []
    for i in range(start, end + 1):
        marker = ">>> " if line <= i <= end_line(node) else "    "
        result.append(f"{marker}{i:4d}: {lines[i - 1].rstrip()}")

    return result


def load_engine():
    if not ENGINE_PATH.exists():
        raise FileNotFoundError(f"ENGINE NOT FOUND: {ENGINE_PATH}")

    text = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(ENGINE_PATH))
    lines = text.splitlines()

    return text, tree, lines


def function_inventory(tree):
    inventory = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inventory[node.name] = node

    return inventory


def find_function_calls(tree, function_name):
    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == function_name:
                    found.append(node)

            elif isinstance(node.func, ast.Attribute):
                if node.func.attr == function_name:
                    found.append(node)

    return found


def find_assignments_to_name(function_node, name):
    found = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    found.append(node)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                found.append(node)

        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                found.append(node)

    return found


def find_name_uses(function_node, name):
    found = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Name) and node.id == name:
            found.append(node)

    return found


def find_rows_parameter_functions(tree):
    result = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args:
                if arg.arg == "rows":
                    result.append(node)
                    break

    return result


def call_arguments(call_node):
    args = []

    for arg in call_node.args:
        args.append(safe_unparse(arg))

    for kw in call_node.keywords:
        if kw.arg is None:
            args.append("**" + safe_unparse(kw.value))
        else:
            args.append(f"{kw.arg}={safe_unparse(kw.value)}")

    return args


def resolve_calculate_analysis(tree, inventory):
    calls = find_function_calls(tree, "calculate_analysis")

    result = []

    for call in calls:
        caller = None

        for fn in inventory.values():
            if call in ast.walk(fn):
                caller = fn
                break

        result.append(
            {
                "call": call,
                "caller": caller,
                "line": node_line(call),
                "args": call_arguments(call),
            }
        )

    return result


def resolve_rows_assignments(caller):
    if caller is None:
        return []

    return find_assignments_to_name(caller, "rows")


def resolve_rows_uses(caller):
    if caller is None:
        return []

    return find_name_uses(caller, "rows")


def describe_assignment(node):
    if isinstance(node, ast.Assign):
        targets = [safe_unparse(x) for x in node.targets]
        value = safe_unparse(node.value)
        return f"{', '.join(targets)} = {value}"

    if isinstance(node, ast.AnnAssign):
        target = safe_unparse(node.target)
        value = safe_unparse(node.value) if node.value else "<NO VALUE>"
        return f"{target} = {value}"

    if isinstance(node, ast.AugAssign):
        return safe_unparse(node)

    return safe_unparse(node)


def identify_source_patterns(node):
    patterns = []

    text = safe_unparse(node)

    keywords = [
        "execute",
        "fetchall",
        "fetchone",
        "sqlite3",
        "cursor",
        "SELECT",
        "market_history",
        "market_data",
        "requests",
        "get(",
        "post(",
        "api",
        "history",
        "rows",
        "prices",
        "closes",
    ]

    for keyword in keywords:
        if keyword.lower() in text.lower():
            patterns.append(keyword)

    return patterns


def inspect_function_for_rows_production(fn):
    findings = []

    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            targets = [safe_unparse(x) for x in node.targets]

            if any(
                t == "rows"
                or t.endswith(".rows")
                or t.startswith("rows")
                for t in targets
            ):
                findings.append(
                    {
                        "type": "ASSIGNMENT",
                        "line": node_line(node),
                        "text": describe_assignment(node),
                        "patterns": identify_source_patterns(node),
                        "node": node,
                    }
                )

        elif isinstance(node, ast.AnnAssign):
            target = safe_unparse(node.target)

            if (
                target == "rows"
                or target.endswith(".rows")
                or target.startswith("rows")
            ):
                findings.append(
                    {
                        "type": "ASSIGNMENT",
                        "line": node_line(node),
                        "text": describe_assignment(node),
                        "patterns": identify_source_patterns(node),
                        "node": node,
                    }
                )

    return findings


def inspect_database_source_calls(fn):
    findings = []

    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            text = safe_unparse(node)

            lowered = text.lower()

            if (
                "execute" in lowered
                or "fetchall" in lowered
                or "fetchone" in lowered
                or "cursor" in lowered
                or "sqlite" in lowered
                or "market_history" in lowered
                or "market_data" in lowered
                or "select " in lowered
            ):
                findings.append(
                    {
                        "line": node_line(node),
                        "text": text,
                        "node": node,
                    }
                )

    return findings


def inspect_main_flow(tree, inventory):
    findings = []

    main_fn = inventory.get("main")

    if main_fn is None:
        return findings

    for node in ast.walk(main_fn):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "calculate_analysis":
                    findings.append(node)

    return findings


def inspect_rows_lineage(tree, inventory):
    lineage = []

    for fn_name, fn in inventory.items():
        assignments = inspect_function_for_rows_production(fn)

        if assignments:
            lineage.append(
                {
                    "function": fn_name,
                    "function_line": node_line(fn),
                    "assignments": assignments,
                    "db_calls": inspect_database_source_calls(fn),
                }
            )

    return lineage


def resolve_database_schema(conn):
    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    table_names = [row[0] for row in tables]

    schema = {}

    for table in table_names:
        try:
            cols = conn.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            schema[table] = [row[1] for row in cols]
        except Exception:
            schema[table] = []

    return schema


def print_database_schema(schema):
    print(f"TABLE COUNT : {len(schema)}")

    for table in schema:
        if table in ("market_data", "market_history"):
            print()
            print(f"TABLE : {table}")
            print("-" * 100)

            for col in schema[table]:
                print(f"  {col}")


def resolve_market_data_target(conn, symbol):
    columns = [
        row[1]
        for row in conn.execute(
            'PRAGMA table_info("market_data")'
        ).fetchall()
    ]

    if not columns:
        return None

    candidates = [
        "symbol",
        "asset_symbol",
        "ticker",
    ]

    symbol_col = next(
        (x for x in candidates if x in columns),
        None,
    )

    if symbol_col is None:
        return None

    order_candidates = [
        "source_timestamp",
        "timestamp",
        "created_at",
        "id",
    ]

    order_col = next(
        (x for x in order_candidates if x in columns),
        None,
    )

    if order_col is None:
        return None

    query = f"""
        SELECT *
        FROM market_data
        WHERE {symbol_col} = ?
        ORDER BY {order_col} DESC
        LIMIT 1
    """

    row = conn.execute(query, (symbol,)).fetchone()

    if row is None:
        return None

    return {
        "columns": columns,
        "row": row,
        "symbol_column": symbol_col,
        "order_column": order_col,
    }


def resolve_history_schema(conn):
    columns = [
        row[1]
        for row in conn.execute(
            'PRAGMA table_info("market_history")'
        ).fetchall()
    ]

    symbol_candidates = ["symbol", "asset_symbol", "ticker"]
    timestamp_candidates = [
        "timestamp",
        "source_timestamp",
        "created_at",
    ]
    price_candidates = ["price", "close", "close_price"]

    symbol_col = next(
        (x for x in symbol_candidates if x in columns),
        None,
    )

    timestamp_col = next(
        (x for x in timestamp_candidates if x in columns),
        None,
    )

    price_col = next(
        (x for x in price_candidates if x in columns),
        None,
    )

    cmc_col = "cmc_id" if "cmc_id" in columns else None

    return {
        "columns": columns,
        "symbol": symbol_col,
        "timestamp": timestamp_col,
        "price": price_col,
        "cmc_id": cmc_col,
    }


def resolve_history_for_symbol(conn, symbol, history_schema):
    symbol_col = history_schema["symbol"]
    timestamp_col = history_schema["timestamp"]
    price_col = history_schema["price"]

    if not symbol_col or not timestamp_col or not price_col:
        return []

    query = f"""
        SELECT
            {timestamp_col},
            {price_col},
            source,
            engine_version,
            cmc_id
        FROM market_history
        WHERE {symbol_col} = ?
        ORDER BY {timestamp_col} ASC
    """

    return conn.execute(query, (symbol,)).fetchall()


def print_history_resolution(conn, symbol, history_schema):
    rows = resolve_history_for_symbol(
        conn,
        symbol,
        history_schema,
    )

    print()
    print(f"SYMBOL : {symbol}")
    print("-" * 100)
    print(f"HISTORY ROWS : {len(rows)}")

    if not rows:
        print("[NONE] No history rows found")
        return rows

    print()
    print("FIRST HISTORY ROW")
    print("-" * 100)

    first = rows[0]

    print(
        f"TIME={first[0]} | "
        f"PRICE={first[1]} | "
        f"SOURCE={first[2]} | "
        f"ENGINE={first[3]} | "
        f"CMC_ID={first[4]}"
    )

    print()
    print("LAST HISTORY ROW")
    print("-" * 100)

    last = rows[-1]

    print(
        f"TIME={last[0]} | "
        f"PRICE={last[1]} | "
        f"SOURCE={last[2]} | "
        f"ENGINE={last[3]} | "
        f"CMC_ID={last[4]}"
    )

    print()
    print("LAST 10 HISTORY ROWS")
    print("-" * 100)

    for row in rows[-10:]:
        print(
            f"TIME={row[0]} | "
            f"PRICE={row[1]} | "
            f"SOURCE={row[2]} | "
            f"ENGINE={row[3]} | "
            f"CMC_ID={row[4]}"
        )

    return rows


def print_target_market_data(target):
    row = target["row"]
    columns = target["columns"]

    values = dict(zip(columns, row))

    print()
    print("MARKET_DATA TARGET")
    print("-" * 100)

    for key in [
        "id",
        "symbol",
        "source_timestamp",
        "timestamp",
        "close",
        "price",
        "engine_version",
    ]:
        if key in values:
            print(f"{key.upper():20s}: {values[key]}")


def build_chain_verdict(
    calculate_calls,
    rows_lineage,
):
    calculate_resolved = bool(calculate_calls)
    caller_resolved = any(
        x["caller"] is not None
        for x in calculate_calls
    )

    rows_assignment_resolved = bool(rows_lineage)

    db_source_resolved = any(
        item["db_calls"]
        for item in rows_lineage
    )

    return {
        "calculate_analysis": calculate_resolved,
        "caller": caller_resolved,
        "rows_assignment": rows_assignment_resolved,
        "database_source": db_source_resolved,
    }


def main():
    print_header(
        "ARUNDA INDICATOR POST REPAIR ACTUAL ROWS PRODUCER CHAIN FORENSIC AUDIT v0.1"
    )

    print("MODE                  : READ ONLY")
    print("DATABASE WRITE        : NONE")
    print("ENGINE WRITE          : NONE")
    print("FORMULA WRITE         : NONE")
    print("PRODUCTION RECALCULATION : NONE")
    print("PURPOSE               : TRACE ACTUAL PRODUCTION ROWS PRODUCER CHAIN")

    print_section("STEP 1 — ENGINE SOURCE RESOLUTION")

    try:
        source_text, tree, lines = load_engine()
    except Exception as exc:
        print(f"ENGINE RESOLUTION FAILED : {exc}")
        return 1

    print(f"ENGINE PATH           : {ENGINE_PATH}")
    print("ENGINE FOUND          : True")
    print(f"SOURCE SIZE           : {len(source_text)} characters")
    print(f"SOURCE LINES          : {len(lines)}")
    print("AST STATUS            : SUCCESS")

    print_section("STEP 2 — FUNCTION INVENTORY")

    inventory = function_inventory(tree)

    for name in [
        "calculate_analysis",
        "main",
        "ema",
        "ema_series",
        "rsi",
        "macd",
    ]:
        fn = inventory.get(name)

        if fn:
            print(
                f"[FOUND] {name}() "
                f"LINE {node_line(fn)}-{end_line(fn)}"
            )
        else:
            print(f"[MISSING] {name}()")

    print_section(
        "STEP 3 — calculate_analysis() CALL GRAPH"
    )

    calculate_calls = resolve_calculate_analysis(
        tree,
        inventory,
    )

    print(
        f"calculate_analysis() CALLS FOUND : "
        f"{len(calculate_calls)}"
    )

    for idx, item in enumerate(
        calculate_calls,
        start=1,
    ):
        print()
        print(f"CALL #{idx}")
        print("-" * 100)
        print(f"CALL LINE       : {item['line']}")
        print(
            "CALLER FUNCTION : "
            + (
                item["caller"].name
                if item["caller"]
                else "<UNRESOLVED>"
            )
        )
        print(
            f"CALL ARGUMENTS  : {item['args']}"
        )

        if item["caller"]:
            for line in source_segment(
                lines,
                item["call"],
                radius=4,
            ):
                print(line)

    print_section(
        "STEP 4 — ACTUAL 'rows' PRODUCER CHAIN"
    )

    rows_lineage = inspect_rows_lineage(
        tree,
        inventory,
    )

    print(
        f"FUNCTIONS WITH rows ASSIGNMENTS : "
        f"{len(rows_lineage)}"
    )

    for item in rows_lineage:
        print()
        print(
            f"FUNCTION : {item['function']}() "
            f"LINE {item['function_line']}"
        )
        print("-" * 100)

        for assignment in item["assignments"]:
            print(
                f"[ASSIGNMENT] LINE "
                f"{assignment['line']}"
            )
            print(
                f"  {assignment['text']}"
            )

            patterns = assignment["patterns"]

            if patterns:
                print(
                    "  SOURCE PATTERNS : "
                    + ", ".join(patterns)
                )
            else:
                print(
                    "  SOURCE PATTERNS : NONE"
                )

            for line in source_segment(
                lines,
                assignment["node"],
                radius=3,
            ):
                print(line)

    print_section(
        "STEP 5 — DATABASE / API SOURCE CALLS IN ROWS PRODUCERS"
    )

    total_db_calls = 0

    for item in rows_lineage:
        print()
        print(
            f"FUNCTION : {item['function']}()"
        )
        print("-" * 100)

        calls = item["db_calls"]

        if not calls:
            print("[NONE] No database/API-like calls detected")
            continue

        for call in calls:
            total_db_calls += 1

            print(
                f"[FOUND] LINE {call['line']}"
            )
            print(
                f"  {call['text']}"
            )

    print()
    print(
        f"TOTAL DATABASE/API SOURCE CALL CANDIDATES : "
        f"{total_db_calls}"
    )

    print_section(
        "STEP 6 — DATABASE RESOLUTION"
    )

    if not DB_PATH.exists():
        print(f"DATABASE FOUND : False")
        return 1

    print(f"DATABASE PATH  : {DB_PATH}")
    print("DATABASE FOUND : True")

    conn = sqlite3.connect(str(DB_PATH))

    try:
        schema = resolve_database_schema(conn)

        print_database_schema(schema)

        if "market_history" not in schema:
            print(
                "[MISSING] market_history table"
            )
            return 1

        history_schema = resolve_history_schema(
            conn
        )

        print()
        print(
            "HISTORY SCHEMA RESOLUTION"
        )
        print("-" * 100)

        print(
            f"SYMBOL COLUMN    : "
            f"{history_schema['symbol']}"
        )
        print(
            f"TIMESTAMP COLUMN : "
            f"{history_schema['timestamp']}"
        )
        print(
            f"PRICE COLUMN     : "
            f"{history_schema['price']}"
        )
        print(
            f"CMC_ID COLUMN    : "
            f"{history_schema['cmc_id']}"
        )

        print_section(
            "STEP 7 — TARGET PRODUCTION RECORDS"
        )

        target_results = []

        for symbol in TARGETS:
            target = resolve_market_data_target(
                conn,
                symbol,
            )

            if target is None:
                print()
                print(
                    f"SYMBOL : {symbol}"
                )
                print(
                    "[UNRESOLVED] market_data target not found"
                )

                target_results.append(
                    {
                        "symbol": symbol,
                        "status": "UNRESOLVED",
                    }
                )

                continue

            print()
            print(
                f"SYMBOL : {symbol}"
            )
            print("-" * 100)

            print_target_market_data(
                target
            )

            history_rows = print_history_resolution(
                conn,
                symbol,
                history_schema,
            )

            target_results.append(
                {
                    "symbol": symbol,
                    "status": "RESOLVED",
                    "history_count": len(history_rows),
                }
            )

        print_section(
            "STEP 8 — CHAIN VERDICT"
        )

        verdict = build_chain_verdict(
            calculate_calls,
            rows_lineage,
        )

        print(
            f"calculate_analysis() : "
            f"{'RESOLVED' if verdict['calculate_analysis'] else 'MISSING'}"
        )

        print(
            f"CALLER              : "
            f"{'RESOLVED' if verdict['caller'] else 'MISSING'}"
        )

        print(
            f"rows ASSIGNMENT     : "
            f"{'RESOLVED' if verdict['rows_assignment'] else 'MISSING'}"
        )

        print(
            f"DATABASE/API SOURCE : "
            f"{'RESOLVED' if verdict['database_source'] else 'MISSING'}"
        )

        complete = all(
            verdict.values()
        )

        print()

        if complete:
            print(
                "CHAIN STATUS : COMPLETE"
            )
            print(
                "CAUSE STATUS : ACTUAL_ROWS_PRODUCER_PATH_RESOLVED"
            )
        else:
            print(
                "CHAIN STATUS : INCOMPLETE"
            )
            print(
                "CAUSE STATUS : CAUSE_NOT_PROVEN"
            )

        print_section(
            "FINAL ACTUAL ROWS PRODUCER CHAIN FORENSIC SUMMARY"
        )

        print(
            f"TARGETS CHECKED              : "
            f"{len(TARGETS)}"
        )

        print(
            f"calculate_analysis() RESOLVED : "
            f"{'YES' if verdict['calculate_analysis'] else 'NO'}"
        )

        print(
            f"CALLER RESOLVED              : "
            f"{'YES' if verdict['caller'] else 'NO'}"
        )

        print(
            f"ROWS ASSIGNMENT RESOLVED     : "
            f"{'YES' if verdict['rows_assignment'] else 'NO'}"
        )

        print(
            f"SOURCE RESOLVED              : "
            f"{'YES' if verdict['database_source'] else 'NO'}"
        )

        print()
        print(
            "FORENSIC RULE"
        )
        print("-" * 100)
        print(
            "Actual production rows are considered RESOLVED only when:"
        )
        print(
            "1. calculate_analysis(rows) is resolved"
        )
        print(
            "2. caller of calculate_analysis() is resolved"
        )
        print(
            "3. actual rows assignment is resolved"
        )
        print(
            "4. database/API/source producing rows is resolved"
        )
        print(
            "5. rows are traceable to indicator closes input"
        )

        print()

        if complete:
            print(
                "STATUS : ACTUAL_ROWS_PRODUCER_CHAIN_RESOLVED"
            )
            print(
                "NEXT STEP : DETERMINE WHETHER PRODUCTION rows "
                "ARE ACTUALLY THE SAME PRICE SERIES USED BY "
                "THE REPAIRED INDICATOR CONVENTION"
            )
        else:
            print(
                "STATUS : ACTUAL_ROWS_PRODUCER_CHAIN_INCOMPLETE"
            )
            print(
                "NEXT STEP : INSPECT ONLY THE REMAINING "
                "UNRESOLVED rows PRODUCER COMPONENT"
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
