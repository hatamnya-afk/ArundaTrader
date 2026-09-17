from pathlib import Path
import ast
import sqlite3
import re

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGETS = {
    "EMA20": "ema20",
    "EMA50": "ema50",
    "RSI14": "rsi14",
}

EXPECTED_ENGINE_VERSION = "MARKET_DATA_CMC_SNAPSHOT_v0.2"


def line_no(node):
    return getattr(node, "lineno", None)


def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse_failed>"


def build_parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def get_function_map(tree):
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node
    return result


def get_assignment_target_names(node):
    names = []

    targets = []

    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]

    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)

        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                if isinstance(item, ast.Name):
                    names.append(item.id)

        elif isinstance(target, ast.Attribute):
            names.append(target.attr)

    return names


def get_call_name(node):
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        return func.attr

    return None


def find_calls(tree):
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(node)

    return calls


def find_assignments(tree):
    assignments = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            assignments.append(node)

    return assignments


def find_return_nodes(function_node):
    return [
        node
        for node in ast.walk(function_node)
        if isinstance(node, ast.Return)
    ]


def find_calls_inside(function_node):
    return [
        node
        for node in ast.walk(function_node)
        if isinstance(node, ast.Call)
    ]


def find_target_assignments(tree, target_field):
    matches = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        names = get_assignment_target_names(node)

        for name in names:
            if name == target_field:
                matches.append(node)

    return matches


def find_storage_assignments(tree, target_field):
    matches = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Subscript):
                text = safe_unparse(target)

                if target_field in text:
                    matches.append(node)

            elif isinstance(target, ast.Attribute):
                if target.attr == target_field:
                    matches.append(node)

    return matches


def find_producer_variables(tree, target_field):
    producers = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        names = get_assignment_target_names(node)

        if target_field not in names:
            continue

        value = node.value

        if isinstance(value, ast.Call):
            producers.append(
                {
                    "variable": target_field,
                    "call_name": get_call_name(value),
                    "line": line_no(node),
                    "expression": safe_unparse(value),
                }
            )

        else:
            producers.append(
                {
                    "variable": target_field,
                    "call_name": None,
                    "line": line_no(node),
                    "expression": safe_unparse(value),
                }
            )

    return producers


def find_function_call_sites(tree, function_name):
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = get_call_name(node)

        if name == function_name:
            results.append(node)

    return results


def function_contains_call(function_node, function_name):
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            if get_call_name(node) == function_name:
                return True
    return False


def function_return_summary(function_node):
    returns = []

    for node in find_return_nodes(function_node):
        returns.append(
            {
                "line": line_no(node),
                "value": safe_unparse(node.value) if node.value else "None",
            }
        )

    return returns


def inspect_function(function_name, function_map):
    fn = function_map.get(function_name)

    if fn is None:
        return {
            "found": False,
            "name": function_name,
            "line": None,
            "returns": [],
            "calls": [],
        }

    return {
        "found": True,
        "name": function_name,
        "line": line_no(fn),
        "returns": function_return_summary(fn),
        "calls": [
            {
                "line": line_no(call),
                "name": get_call_name(call),
                "expression": safe_unparse(call),
            }
            for call in find_calls_inside(fn)
        ],
    }


def normalize_engine_versions(values):
    clean = []

    for value in values:
        if value is None:
            continue

        value = str(value).strip()

        if value:
            clean.append(value)

    return sorted(set(clean))


def print_rule():
    print("=" * 100)
    print("PATH RESOLUTION RULE")
    print("=" * 100)
    print("A convention cause is considered PROVEN only if all of the following are traceable:")
    print("  1. TARGET FIELD")
    print("  2. PRODUCER FUNCTION")
    print("  3. INDICATOR FUNCTION CALL")
    print("  4. INDICATOR IMPLEMENTATION")
    print("  5. RETURN VALUE")
    print("  6. STORAGE ASSIGNMENT")
    print()
    print("Presence of helper functions or keywords alone does NOT prove that they produced the stored value.")
    print()


def print_header():
    print("=" * 100)
    print("ARUNDA INDICATOR CURRENT CONVENTION ASSIGNMENT FORENSIC AUDIT v0.1")
    print("=" * 100)
    print("MODE                  : READ ONLY")
    print("DATABASE WRITE        : NONE")
    print("FORMULA WRITE         : NONE")
    print("PRODUCTION RECALCULATION : NONE")
    print("PURPOSE               : EXACT ASSIGNMENT / RETURN CHAIN FORENSICS")
    print("=" * 100)
    print()


def inspect_database():
    print("=" * 100)
    print("DATABASE INVENTORY")
    print("=" * 100)

    if not DB_PATH.exists():
        print(f"DATABASE PATH          : {DB_PATH}")
        print("DATABASE FOUND         : False")
        return None

    print(f"DATABASE PATH          : {DB_PATH}")
    print("DATABASE FOUND         : True")

    conn = sqlite3.connect(DB_PATH)

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

        names = {row[0] for row in tables}

        print(
            f"MARKET_DATA            : "
            f"{'FOUND' if 'market_data' in names else 'MISSING'}"
        )

        if "market_data" in names:
            columns = conn.execute(
                "PRAGMA table_info(market_data)"
            ).fetchall()

            column_names = {row[1] for row in columns}

            print(f"COLUMN COUNT           : {len(columns)}")

            for field in ["id", "symbol", "source_timestamp",
                          "engine_version", "close",
                          "ema20", "ema50", "rsi14"]:

                print(
                    f"  [{'PRESENT' if field in column_names else 'MISSING':7}] : "
                    f"{field}"
                )

        versions = []

        if "market_data" in names:
            try:
                rows = conn.execute(
                    """
                    SELECT DISTINCT engine_version
                    FROM market_data
                    """
                ).fetchall()

                versions = [row[0] for row in rows]

            except Exception:
                pass

        print()
        print("ENGINE VERSION INVENTORY")
        print("-" * 100)

        normalized = normalize_engine_versions(versions)

        if normalized:
            for version in normalized:
                print(f"  [FOUND] : {version}")
        else:
            print("  [NONE FOUND]")

        return conn

    except Exception as exc:
        print(f"DATABASE INSPECTION ERROR : {exc}")
        conn.close()
        return None


def print_source_inventory(source_text):
    print("=" * 100)
    print("ENGINE SOURCE INVENTORY")
    print("=" * 100)
    print(f"ENGINE PATH             : {ENGINE_PATH}")
    print(f"ENGINE FOUND            : {ENGINE_PATH.exists()}")
    print(f"SOURCE SIZE             : {len(source_text)} characters")
    print(f"SOURCE LINES            : {len(source_text.splitlines())}")
    print()


def print_function_inventory(function_map):
    print("=" * 100)
    print("FUNCTION INVENTORY")
    print("=" * 100)

    candidates = [
        "ema",
        "ema_series",
        "rsi",
        "calculate_ema",
        "calculate_rsi",
    ]

    for name in candidates:
        fn = function_map.get(name)

        if fn is None:
            print(f"  [NOT FOUND] : {name}")
        else:
            print(
                f"  [FOUND]     : {name} "
                f"(line {line_no(fn)})"
            )

    print()


def identify_indicator_call_from_expression(expression):
    if not expression:
        return None

    text = expression.lower()

    if "ema" in text:
        return "EMA"

    if "rsi" in text:
        return "RSI"

    return None


def inspect_target_chain(tree, function_map, target_field):
    print("=" * 100)
    print(f"TARGET FORENSIC : {target_field}")
    print("=" * 100)

    assignments = find_target_assignments(tree, target_field)
    storage = find_storage_assignments(tree, target_field)

    print()
    print("1. TARGET FIELD")
    print("-" * 100)

    if assignments:
        print(f"TARGET ASSIGNMENT FOUND : True")
        for item in assignments:
            print(
                f"  LINE {line_no(item):4} : "
                f"{safe_unparse(item)}"
            )
    else:
        print("TARGET ASSIGNMENT FOUND : False")

    print()
    print("2. PRODUCER FUNCTION")
    print("-" * 100)

    producer_records = find_producer_variables(tree, target_field)

    producer_functions = []

    if producer_records:
        for record in producer_records:
            print(
                f"  LINE {record['line']:4} : "
                f"{record['expression']}"
            )

            call_name = record["call_name"]

            if call_name:
                print(f"    PRODUCER CALL : {call_name}")
                producer_functions.append(call_name)

    else:
        print("  NO DIRECT PRODUCER CALL IDENTIFIED")

    print()
    print("3. INDICATOR FUNCTION CALL")
    print("-" * 100)

    call_sites = []

    for function_name in producer_functions:
        matches = find_function_call_sites(tree, function_name)

        if matches:
            for call in matches:
                call_sites.append(call)

                print(
                    f"  CALL TO {function_name} "
                    f"AT LINE {line_no(call)}"
                )
                print(
                    f"    {safe_unparse(call)}"
                )
        else:
            print(
                f"  NO CALL SITE FOUND FOR {function_name}"
            )

    print()
    print("4. INDICATOR IMPLEMENTATION")
    print("-" * 100)

    implementations = []

    for function_name in producer_functions:
        fn = function_map.get(function_name)

        if fn is None:
            continue

        implementations.append(fn)

        print(
            f"  FUNCTION              : {function_name}"
        )
        print(
            f"  DEFINITION LINE       : {line_no(fn)}"
        )

        for node in ast.walk(fn):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                text = safe_unparse(node)

                if (
                    "alpha" in text.lower()
                    or "ewm" in text.lower()
                    or "rolling" in text.lower()
                    or "mean" in text.lower()
                    or "gain" in text.lower()
                    or "loss" in text.lower()
                    or "rsi" in text.lower()
                ):
                    print(
                        f"    LINE {line_no(node):4} : {text}"
                    )

    if not implementations:
        print("  IMPLEMENTATION NOT RESOLVED")

    print()
    print("5. RETURN VALUE")
    print("-" * 100)

    return_records = []

    for fn in implementations:
        returns = find_return_nodes(fn)

        print(
            f"  FUNCTION : {fn.name}"
        )

        if not returns:
            print("    NO RETURN STATEMENT FOUND")

        for ret in returns:
            value = safe_unparse(ret.value) if ret.value else "None"

            record = {
                "function": fn.name,
                "line": line_no(ret),
                "value": value,
            }

            return_records.append(record)

            print(
                f"    LINE {line_no(ret):4} : return {value}"
            )

    print()
    print("6. STORAGE ASSIGNMENT")
    print("-" * 100)

    if storage:
        print("STORAGE ASSIGNMENT FOUND : True")

        for node in storage:
            print(
                f"  LINE {line_no(node):4} : "
                f"{safe_unparse(node)}"
            )
    else:
        print("STORAGE ASSIGNMENT FOUND : False")

    print()
    print("CHAIN VERDICT")
    print("-" * 100)

    target_ok = bool(assignments)
    producer_ok = bool(producer_functions)
    call_ok = bool(call_sites)
    implementation_ok = bool(implementations)
    return_ok = bool(return_records)
    storage_ok = bool(storage)

    checks = [
        ("TARGET FIELD", target_ok),
        ("PRODUCER FUNCTION", producer_ok),
        ("INDICATOR FUNCTION CALL", call_ok),
        ("INDICATOR IMPLEMENTATION", implementation_ok),
        ("RETURN VALUE", return_ok),
        ("STORAGE ASSIGNMENT", storage_ok),
    ]

    for name, status in checks:
        print(
            f"  [{'FOUND' if status else 'MISSING':7}] : {name}"
        )

    proven = all(status for _, status in checks)

    if proven:
        print()
        print("CHAIN STATUS : COMPLETE")
        print("CAUSE STATUS : EXECUTION_PATH_TRACEABLE")
    else:
        print()
        print("CHAIN STATUS : INCOMPLETE")
        print("CAUSE STATUS : CAUSE_NOT_PROVEN")

    return proven


def inspect_runtime_targets(conn):
    print("=" * 100)
    print("RUNTIME TARGET ASSIGNMENT CHECK")
    print("=" * 100)

    if conn is None:
        print("DATABASE CONNECTION : UNAVAILABLE")
        return

    for symbol in ["BTC", "ETH", "SOL", "XRP"]:
        print()
        print(f"SYMBOL : {symbol}")
        print("-" * 100)

        try:
            row = conn.execute(
                """
                SELECT
                    id,
                    symbol,
                    source_timestamp,
                    engine_version,
                    ema20,
                    ema50,
                    rsi14
                FROM market_data
                WHERE symbol = ?
                AND engine_version = ?
                ORDER BY source_timestamp DESC, id DESC
                LIMIT 1
                """,
                (symbol, EXPECTED_ENGINE_VERSION),
            ).fetchone()

            if row is None:
                print("TARGET : NOT FOUND")
                continue

            (
                row_id,
                db_symbol,
                timestamp,
                engine_version,
                ema20,
                ema50,
                rsi14,
            ) = row

            print(f"ID              : {row_id}")
            print(f"SYMBOL          : {db_symbol}")
            print(f"SOURCE TIME     : {timestamp}")
            print(f"ENGINE VERSION  : {engine_version}")
            print(f"EMA20           : {ema20}")
            print(f"EMA50           : {ema50}")
            print(f"RSI14           : {rsi14}")

        except Exception as exc:
            print(f"RUNTIME CHECK ERROR : {exc}")


def main():
    print_header()
    print_rule()

    conn = inspect_database()

    print()

    if not ENGINE_PATH.exists():
        print("=" * 100)
        print("FINAL FORENSIC CONCLUSION")
        print("=" * 100)
        print("STATUS : CAUSE_NOT_PROVEN")
        print("REASON : ENGINE SOURCE NOT FOUND")
        print()
        print("DATABASE WRITE OPERATIONS : NONE")
        print("ENGINE MODIFICATIONS      : NONE")
        print("PRODUCTION RECALCULATION  : NONE")
        return

    try:
        source_text = ENGINE_PATH.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        print("=" * 100)
        print("SOURCE READ ERROR")
        print("=" * 100)
        print(exc)

        if conn:
            conn.close()

        return

    print_source_inventory(source_text)

    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        print("=" * 100)
        print("SOURCE PARSE ERROR")
        print("=" * 100)
        print(f"LINE : {exc.lineno}")
        print(f"TEXT : {exc.text}")
        print(f"ERROR: {exc.msg}")

        if conn:
            conn.close()

        return

    function_map = get_function_map(tree)

    print_function_inventory(function_map)

    results = {}

    for target in TARGETS:
        results[target] = inspect_target_chain(
            tree,
            function_map,
            TARGETS[target],
        )

    print()
    inspect_runtime_targets(conn)

    if conn:
        conn.close()

    print()
    print("=" * 100)
    print("FINAL ASSIGNMENT FORENSIC SUMMARY")
    print("=" * 100)

    complete_count = sum(
        1 for value in results.values()
        if value
    )

    incomplete_count = len(results) - complete_count

    print(f"TARGETS CHECKED        : {len(results)}")
    print(f"COMPLETE CHAINS        : {complete_count}")
    print(f"INCOMPLETE CHAINS      : {incomplete_count}")

    print()
    print("TARGET MATRIX")
    print("-" * 100)

    for target, status in results.items():
        print(
            f"  [{'COMPLETE' if status else 'INCOMPLETE':10}] : "
            f"{target}"
        )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("=" * 100)

    if complete_count == len(results):
        print("STATUS                  : EXECUTION_PATH_PROVEN")
        print("REASON                  : TARGET → PRODUCER → CALL → IMPLEMENTATION → RETURN → STORAGE")
        print("NEXT STEP               : CLASSIFY EXACT CURRENT CONVENTION")
    else:
        print("STATUS                  : CAUSE_NOT_PROVEN")
        print("REASON                  : ONE OR MORE EXECUTION CHAINS REMAIN INCOMPLETE")
        print("NEXT STEP               : INSPECT ONLY THE MISSING CHAIN COMPONENTS")

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("ENGINE MODIFICATIONS      : NONE")
    print("FORMULA WRITE             : NONE")
    print("PRODUCTION RECALCULATION  : NONE")
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()