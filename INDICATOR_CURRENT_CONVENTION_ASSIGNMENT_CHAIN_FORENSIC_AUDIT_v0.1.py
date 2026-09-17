from pathlib import Path
import ast
import sqlite3
import re
from collections import defaultdict


VERSION = "v0.1"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGETS = {
    "ema20": ["ema20", "EMA20"],
    "ema50": ["ema50", "EMA50"],
    "rsi14": ["rsi14", "RSI14"],
}

INDICATOR_FUNCTIONS = {
    "ema": "EMA",
    "ema_series": "EMA_SERIES",
    "rsi": "RSI",
}

SEPARATOR = "=" * 100
SUBSEP = "-" * 100


def line_of(node):
    return getattr(node, "lineno", None)


def end_line_of(node):
    return getattr(node, "end_lineno", line_of(node))


def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


def source_segment(source, node):
    try:
        text = ast.get_source_segment(source, node)
        return text if text else safe_unparse(node)
    except Exception:
        return safe_unparse(node)


def is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def is_string_constant(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def constant_string(node):
    if is_string_constant(node):
        return node.value
    return None


def call_function_name(node):
    if not isinstance(node, ast.Call):
        return None

    fn = node.func

    if isinstance(fn, ast.Name):
        return fn.id

    if isinstance(fn, ast.Attribute):
        return fn.attr

    return None


def target_name_from_subscript(node):
    if not isinstance(node, ast.Subscript):
        return None

    value = node.value

    if isinstance(value, ast.Name):
        return value.id

    return None


def assignment_target_names(node):
    names = []

    if isinstance(node, ast.Name):
        names.append(node.id)

    elif isinstance(node, (ast.Tuple, ast.List)):
        for item in node.elts:
            names.extend(assignment_target_names(item))

    elif isinstance(node, ast.Starred):
        names.extend(assignment_target_names(node.value))

    elif isinstance(node, ast.Subscript):
        names.append(safe_unparse(node))

    elif isinstance(node, ast.Attribute):
        names.append(safe_unparse(node))

    return names


def collect_function_defs(tree):
    functions = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = node

    return functions


def collect_calls(tree):
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = call_function_name(node)

            if fn:
                calls.append({
                    "node": node,
                    "function": fn,
                    "line": line_of(node),
                    "source": safe_unparse(node),
                })

    return calls


def collect_assignments(tree):
    assignments = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):
            targets = []

            for target in node.targets:
                targets.extend(assignment_target_names(target))

            assignments.append({
                "node": node,
                "targets": targets,
                "value": node.value,
                "line": line_of(node),
                "source": safe_unparse(node),
            })

        elif isinstance(node, ast.AnnAssign):
            targets = assignment_target_names(node.target)

            assignments.append({
                "node": node,
                "targets": targets,
                "value": node.value,
                "line": line_of(node),
                "source": safe_unparse(node),
            })

        elif isinstance(node, ast.AugAssign):
            targets = assignment_target_names(node.target)

            assignments.append({
                "node": node,
                "targets": targets,
                "value": node.value,
                "line": line_of(node),
                "source": safe_unparse(node),
            })

    return assignments


def collect_returns(function_node):
    returns = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Return):
            returns.append({
                "node": node,
                "line": line_of(node),
                "value": node.value,
                "source": safe_unparse(node),
            })

    return returns


def expression_contains_function_call(node, function_names):
    if node is None:
        return False

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = call_function_name(child)
            if fn in function_names:
                return True

    return False


def find_indicator_calls_in_expression(node, function_names):
    result = []

    if node is None:
        return result

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = call_function_name(child)

            if fn in function_names:
                result.append({
                    "node": child,
                    "function": fn,
                    "line": line_of(child),
                    "source": safe_unparse(child),
                })

    return result


def normalize_identifier(text):
    return re.sub(r"[^a-z0-9_]", "", text.lower())


def target_matches_name(name, target):
    normalized = normalize_identifier(name)
    aliases = {
        target,
        target.lower(),
        target.upper(),
    }

    normalized_aliases = {
        normalize_identifier(x)
        for x in aliases
    }

    return normalized in normalized_aliases


def find_target_assignments(assignments, target):
    matches = []

    for item in assignments:
        for name in item["targets"]:
            if target_matches_name(name, target):
                matches.append(item)
                break

    return matches


def find_assignments_from_function_calls(assignments, function_names):
    matches = []

    for item in assignments:
        calls = find_indicator_calls_in_expression(
            item["value"],
            function_names,
        )

        if calls:
            matches.append({
                "assignment": item,
                "calls": calls,
            })

    return matches


def find_variable_producers(assignments, variable_names):
    producers = []

    normalized = {
        normalize_identifier(x)
        for x in variable_names
    }

    for item in assignments:
        for name in item["targets"]:
            if normalize_identifier(name) in normalized:
                producers.append(item)

    return producers


def find_calls_using_variable(tree, variable_names):
    normalized = {
        normalize_identifier(x)
        for x in variable_names
    }

    result = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            for arg in list(node.args) + list(node.keywords):

                candidate = arg.value if isinstance(arg, ast.keyword) else arg

                if isinstance(candidate, ast.Name):
                    if normalize_identifier(candidate.id) in normalized:
                        result.append({
                            "node": node,
                            "function": call_function_name(node),
                            "line": line_of(node),
                            "source": safe_unparse(node),
                            "variable": candidate.id,
                        })

    return result


def find_storage_assignments_from_value(assignments, variable_names):
    normalized = {
        normalize_identifier(x)
        for x in variable_names
    }

    result = []

    for item in assignments:

        value = item["value"]

        if isinstance(value, ast.Name):
            if normalize_identifier(value.id) in normalized:
                result.append(item)

        elif isinstance(value, (ast.Dict, ast.Call, ast.Attribute, ast.Subscript)):
            for child in ast.walk(value):
                if isinstance(child, ast.Name):
                    if normalize_identifier(child.id) in normalized:
                        result.append(item)
                        break

    return result


def function_contains_target_assignment(function_node, target):
    assignments = collect_assignments(function_node)

    return find_target_assignments(assignments, target)


def function_call_chain(functions, function_name):
    if function_name not in functions:
        return None

    return {
        "name": function_name,
        "function": functions[function_name],
        "line": line_of(functions[function_name]),
    }


def find_direct_target_calls(tree, target):
    result = []

    target_lower = target.lower()

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        fn = call_function_name(node)

        if not fn:
            continue

        text = safe_unparse(node).lower()

        if target_lower in text:
            result.append({
                "function": fn,
                "line": line_of(node),
                "source": safe_unparse(node),
            })

    return result


def print_function_excerpt(source_lines, function_node, padding=2):
    start = max(1, line_of(function_node) - padding)
    end = min(
        len(source_lines),
        end_line_of(function_node) + padding,
    )

    for idx in range(start, end + 1):
        print(f"      {idx:5d} | {source_lines[idx - 1].rstrip()}")


def print_call(call):
    print(f"      FUNCTION : {call.get('function')}")
    print(f"      LINE     : {call.get('line')}")
    print(f"      SOURCE   : {call.get('source')}")


def print_assignment(item):
    print(f"      LINE     : {item.get('line')}")
    print(f"      TARGETS  : {item.get('targets')}")
    print(f"      SOURCE   : {item.get('source')}")


def inspect_indicator_implementation(
    functions,
    function_name,
    source_lines,
):
    print(SUBSEP)
    print(f"INDICATOR IMPLEMENTATION : {function_name}")

    if function_name not in functions:
        print("  STATUS : NOT_FOUND")
        return None

    fn = functions[function_name]

    print(f"  FUNCTION FOUND : True")
    print(f"  START LINE     : {line_of(fn)}")
    print(f"  END LINE       : {end_line_of(fn)}")

    returns = collect_returns(fn)

    if not returns:
        print("  RETURN FOUND   : False")
    else:
        print("  RETURN FOUND   : True")

        for ret in returns:
            print(f"  RETURN LINE    : {ret['line']}")
            print(f"  RETURN SOURCE  : {ret['source']}")

    print()
    print("  FUNCTION SOURCE EXCERPT")
    print_function_excerpt(source_lines, fn)

    return {
        "function": fn,
        "returns": returns,
    }


def inspect_target(
    target,
    tree,
    source,
    source_lines,
    functions,
    assignments,
):
    print(SEPARATOR)
    print(f"TARGET FORENSIC : {target}")
    print(SEPARATOR)

    result = {
        "target": target,
        "target_assignment": False,
        "producer": False,
        "indicator_call": False,
        "implementation": False,
        "return_value": False,
        "storage_assignment": False,
    }

    print()
    print("1. TARGET FIELD")
    print(SUBSEP)

    target_assignments = find_target_assignments(
        assignments,
        target,
    )

    if target_assignments:
        result["target_assignment"] = True

        print("TARGET ASSIGNMENT FOUND : True")

        for item in target_assignments:
            print_assignment(item)
    else:
        print("TARGET ASSIGNMENT FOUND : False")

    print()
    print("2. PRODUCER FUNCTION")
    print(SUBSEP)

    producer_assignments = []

    for item in assignments:

        calls = find_indicator_calls_in_expression(
            item["value"],
            set(INDICATOR_FUNCTIONS.keys()),
        )

        if calls:
            producer_assignments.append({
                "assignment": item,
                "calls": calls,
            })

    target_related_producers = []

    for item in producer_assignments:

        text = item["assignment"]["source"].lower()

        if target.lower() in text:
            target_related_producers.append(item)

    if target_related_producers:

        result["producer"] = True

        print("PRODUCER ASSIGNMENT FOUND : True")

        for item in target_related_producers:
            print_assignment(item["assignment"])

            for call in item["calls"]:
                print("      INDICATOR CALL")
                print_call(call)

    else:
        print("NO DIRECT TARGET PRODUCER ASSIGNMENT IDENTIFIED")

    print()
    print("3. INDICATOR FUNCTION CALL")
    print(SUBSEP)

    relevant_functions = set()

    if target.startswith("ema"):
        relevant_functions.update({
            "ema",
            "ema_series",
        })

    elif target.startswith("rsi"):
        relevant_functions.add("rsi")

    calls = find_indicator_calls_in_expression(
        tree,
        relevant_functions,
    )

    target_calls = []

    for call in calls:

        text = call["source"].lower()

        if target.lower() in text:
            target_calls.append(call)

    if target_calls:

        result["indicator_call"] = True

        for call in target_calls:
            print_call(call)

    else:
        print("TARGET-SPECIFIC INDICATOR CALL : NOT RESOLVED")

    print()
    print("4. INDICATOR IMPLEMENTATION")
    print(SUBSEP)

    implementation_names = []

    if target.startswith("ema"):
        implementation_names = [
            "ema",
            "ema_series",
        ]

    elif target.startswith("rsi"):
        implementation_names = [
            "rsi",
        ]

    implementations = []

    for name in implementation_names:

        if name in functions:
            info = inspect_indicator_implementation(
                functions,
                name,
                source_lines,
            )

            implementations.append(info)

    if implementations:
        result["implementation"] = True
    else:
        print("IMPLEMENTATION NOT RESOLVED")

    print()
    print("5. RETURN VALUE")
    print(SUBSEP)

    return_evidence = []

    for info in implementations:

        for ret in info["returns"]:

            print(f"FUNCTION : {info['function'].name}")
            print(f"LINE     : {ret['line']}")
            print(f"RETURN   : {ret['source']}")

            return_evidence.append(ret)

    if return_evidence:
        result["return_value"] = True
    else:
        print("RETURN VALUE NOT RESOLVED")

    print()
    print("6. STORAGE ASSIGNMENT")
    print(SUBSEP)

    storage_candidates = []

    for item in assignments:

        text = item["source"].lower()

        if target.lower() in text:

            value = item["value"]

            if (
                isinstance(value, ast.Name)
                or isinstance(value, ast.Call)
                or isinstance(value, ast.Attribute)
                or isinstance(value, ast.Subscript)
                or isinstance(value, ast.Dict)
            ):
                storage_candidates.append(item)

    if storage_candidates:

        result["storage_assignment"] = True

        print("STORAGE ASSIGNMENT CANDIDATES :")

        for item in storage_candidates:
            print_assignment(item)

    else:
        print("STORAGE ASSIGNMENT : NOT RESOLVED")

    print()
    print("CHAIN VERDICT")
    print(SUBSEP)

    labels = [
        ("TARGET FIELD", result["target_assignment"]),
        ("PRODUCER FUNCTION", result["producer"]),
        ("INDICATOR FUNCTION CALL", result["indicator_call"]),
        ("INDICATOR IMPLEMENTATION", result["implementation"]),
        ("RETURN VALUE", result["return_value"]),
        ("STORAGE ASSIGNMENT", result["storage_assignment"]),
    ]

    for label, status in labels:
        marker = "FOUND" if status else "MISSING"
        print(f"  [{marker:7s}] : {label}")

    complete = all(value for value in result.values() if isinstance(value, bool))

    if complete:
        print()
        print("CHAIN STATUS : COMPLETE")
        print("CAUSE STATUS : EXECUTION_PATH_TRACEABLE")
    else:
        print()
        print("CHAIN STATUS : INCOMPLETE")
        print("CAUSE STATUS : CAUSE_NOT_PROVEN")

    return result


def database_inventory():
    print(SEPARATOR)
    print("DATABASE INVENTORY")
    print(SEPARATOR)

    print(f"DATABASE PATH          : {DB_PATH}")
    print(f"DATABASE FOUND         : {DB_PATH.exists()}")

    if not DB_PATH.exists():
        return None

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

        table_names = [row[0] for row in tables]

        print(f"TABLE COUNT            : {len(table_names)}")
        print(
            f"MARKET_DATA            : "
            f"{'FOUND' if 'market_data' in table_names else 'NOT_FOUND'}"
        )

        if "market_data" not in table_names:
            return conn

        columns = conn.execute(
            "PRAGMA table_info(market_data)"
        ).fetchall()

        print(f"COLUMN COUNT           : {len(columns)}")

        required = [
            "id",
            "symbol",
            "source_timestamp",
            "engine_version",
            "close",
            "ema20",
            "ema50",
            "rsi14",
        ]

        column_names = {
            row[1]
            for row in columns
        }

        for field in required:
            state = "PRESENT" if field in column_names else "MISSING"
            print(f"  [{state:7s}] : {field}")

    except Exception as exc:
        print(f"DATABASE INVENTORY ERROR : {exc}")

    return conn


def runtime_targets(conn):
    print(SEPARATOR)
    print("RUNTIME TARGET INVENTORY")
    print(SEPARATOR)

    if conn is None:
        return []

    if "market_data" not in [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        ).fetchall()
    ]:
        return []

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
        WHERE symbol IN ('BTC', 'ETH', 'SOL', 'XRP')
        ORDER BY symbol
    """

    rows = conn.execute(query).fetchall()

    for row in rows:

        (
            row_id,
            symbol,
            timestamp,
            engine_version,
            close,
            ema20,
            ema50,
            rsi14,
        ) = row

        print()
        print(f"SYMBOL : {symbol}")
        print(SUBSEP)
        print(f"ID              : {row_id}")
        print(f"SOURCE TIME     : {timestamp}")
        print(f"ENGINE VERSION  : {engine_version}")
        print(f"CLOSE           : {close}")
        print(f"EMA20           : {ema20}")
        print(f"EMA50           : {ema50}")
        print(f"RSI14           : {rsi14}")

    return rows


def main():

    print(SEPARATOR)
    print(
        "ARUNDA INDICATOR CURRENT CONVENTION "
        "ASSIGNMENT CHAIN FORENSIC AUDIT "
        f"{VERSION}"
    )
    print(SEPARATOR)

    print("MODE                  : READ ONLY")
    print("DATABASE WRITE        : NONE")
    print("FORMULA WRITE         : NONE")
    print("PRODUCTION RECALCULATION : NONE")
    print("PURPOSE               : EXACT ASSIGNMENT / RETURN CHAIN FORENSICS")

    print(SEPARATOR)
    print("PATH RESOLUTION RULE")
    print(SEPARATOR)

    print(
        "A convention cause is considered PROVEN only if all of the following are traceable:"
    )
    print("  1. TARGET FIELD")
    print("  2. PRODUCER FUNCTION")
    print("  3. INDICATOR FUNCTION CALL")
    print("  4. INDICATOR IMPLEMENTATION")
    print("  5. RETURN VALUE")
    print("  6. STORAGE ASSIGNMENT")
    print()
    print(
        "Presence of helper functions or keywords alone does NOT prove "
        "that they produced the stored value."
    )

    print(SEPARATOR)
    print("ENGINE SOURCE INVENTORY")
    print(SEPARATOR)

    print(f"ENGINE PATH             : {ENGINE_PATH}")
    print(f"ENGINE FOUND            : {ENGINE_PATH.exists()}")

    if not ENGINE_PATH.exists():
        print()
        print("FORENSIC CONCLUSION")
        print(SUBSEP)
        print("STATUS                  : BLOCKED")
        print("REASON                  : ENGINE SOURCE NOT FOUND")
        return

    try:
        source = ENGINE_PATH.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        print()
        print("FORENSIC CONCLUSION")
        print(SUBSEP)
        print("STATUS                  : BLOCKED")
        print(f"REASON                  : SOURCE READ ERROR: {exc}")
        return

    source_lines = source.splitlines()

    print(f"SOURCE SIZE             : {len(source)} characters")
    print(f"SOURCE LINES            : {len(source_lines)}")

    try:
        tree = ast.parse(
            source,
            filename=str(ENGINE_PATH),
        )
    except SyntaxError as exc:
        print()
        print("FORENSIC CONCLUSION")
        print(SUBSEP)
        print("STATUS                  : BLOCKED")
        print(f"REASON                  : AST PARSE ERROR")
        print(f"LINE                    : {exc.lineno}")
        print(f"OFFSET                  : {exc.offset}")
        print(f"DETAIL                  : {exc.msg}")
        return

    functions = collect_function_defs(tree)
    assignments = collect_assignments(tree)

    print()
    print(SEPARATOR)
    print("FUNCTION INVENTORY")
    print(SEPARATOR)

    for name in [
        "ema",
        "ema_series",
        "rsi",
        "calculate_ema",
        "calculate_rsi",
    ]:
        if name in functions:
            print(
                f"  [FOUND]     : {name} "
                f"(line {line_of(functions[name])})"
            )
        else:
            print(f"  [NOT FOUND] : {name}")

    conn = database_inventory()

    runtime_targets(conn)

    print(SEPARATOR)
    print("TARGET ASSIGNMENT CHAIN FORENSICS")
    print(SEPARATOR)

    results = []

    for target in [
        "ema20",
        "ema50",
        "rsi14",
    ]:

        result = inspect_target(
            target=target,
            tree=tree,
            source=source,
            source_lines=source_lines,
            functions=functions,
            assignments=assignments,
        )

        results.append(result)

    print()
    print(SEPARATOR)
    print("FINAL ASSIGNMENT CHAIN FORENSIC SUMMARY")
    print(SEPARATOR)

    complete = sum(
        1
        for result in results
        if all(
            value
            for key, value in result.items()
            if isinstance(value, bool)
        )
    )

    incomplete = len(results) - complete

    print(f"TARGETS CHECKED        : {len(results)}")
    print(f"COMPLETE CHAINS        : {complete}")
    print(f"INCOMPLETE CHAINS      : {incomplete}")

    print()
    print("TARGET MATRIX")
    print(SUBSEP)

    for result in results:

        target = result["target"]

        chain_complete = all(
            value
            for key, value in result.items()
            if isinstance(value, bool)
        )

        if chain_complete:
            print(f"  [COMPLETE  ] : {target.upper()}")
        else:
            print(f"  [INCOMPLETE] : {target.upper()}")

    print()
    print(SEPARATOR)
    print("FORENSIC CONCLUSION")
    print(SEPARATOR)

    if complete == len(results):
        print("STATUS                  : EXECUTION_PATH_TRACEABLE")
        print(
            "REASON                  : "
            "TARGET → PRODUCER → CALL → IMPLEMENTATION → "
            "RETURN → STORAGE CHAIN TRACEABLE"
        )
        print(
            "NEXT STEP               : "
            "CLASSIFY EXACT CURRENT CONVENTION"
        )
    else:
        print("STATUS                  : CAUSE_NOT_PROVEN")
        print(
            "REASON                  : "
            "ONE OR MORE ASSIGNMENT CHAINS REMAIN INCOMPLETE"
        )
        print(
            "NEXT STEP               : "
            "INSPECT ONLY THE MISSING CHAIN COMPONENTS"
        )

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("ENGINE MODIFICATIONS      : NONE")
    print("FORMULA WRITE             : NONE")
    print("PRODUCTION RECALCULATION  : NONE")
    print("AUDIT COMPLETE")

    if conn is not None:
        conn.close()


if __name__ == "__main__":
    main()