from pathlib import Path
import ast
import sqlite3
import re

# ============================================================
# ARUNDA INDICATOR CURRENT CONVENTION MISSING CHAIN
# FORENSIC AUDIT v0.1
# ============================================================

MODE = "READ ONLY"
DB_NAME = "arunda.db"
ENGINE_NAME = "market_data_engine.py"

TARGETS = {
    "EMA20": "ema20",
    "EMA50": "ema50",
    "RSI14": "rsi14",
}

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / DB_NAME
ENGINE_PATH = BASE_DIR / ENGINE_NAME


def line_of(node):
    return getattr(node, "lineno", None)


def source_segment(lines, start, end):
    start = max(1, start)
    end = min(len(lines), end)
    return "\n".join(
        f"{i:04d}: {lines[i - 1]}"
        for i in range(start, end + 1)
    )


def names_in_node(node):
    result = set()

    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            result.add(item.id)
        elif isinstance(item, ast.Attribute):
            result.add(item.attr)

    return result


def call_name(node):
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        return func.attr

    return None


def target_text(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    if isinstance(node, ast.Subscript):
        return ast.unparse(node)

    return ast.unparse(node)


def get_function_name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    return None


def build_function_inventory(tree):
    functions = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = node

    return functions


def find_function_for_line(functions, lineno):
    candidates = []

    for name, fn in functions.items():
        start = getattr(fn, "lineno", None)
        end = getattr(fn, "end_lineno", None)

        if start is None:
            continue

        if end is None:
            end = start

        if start <= lineno <= end:
            candidates.append((start, end, name))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[1] - x[0], x[0]))
    return candidates[0][2]


def assignment_matches_target(node, target):
    if not isinstance(node, ast.Assign):
        return False

    for target_node in node.targets:
        text = target_text(target_node).lower()

        if target.lower() == text:
            return True

        if target.lower() in text:
            return True

    return False


def annotated_assignment_matches_target(node, target):
    if not isinstance(node, ast.AnnAssign):
        return False

    text = target_text(node.target).lower()

    return target.lower() == text or target.lower() in text


def collect_assignments(tree, target):
    results = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):
            if assignment_matches_target(node, target):
                results.append({
                    "line": line_of(node),
                    "type": "ASSIGNMENT",
                    "text": ast.unparse(node),
                    "node": node,
                })

        elif isinstance(node, ast.AnnAssign):
            if annotated_assignment_matches_target(node, target):
                results.append({
                    "line": line_of(node),
                    "type": "ANNOTATED_ASSIGNMENT",
                    "text": ast.unparse(node),
                    "node": node,
                })

    results.sort(key=lambda x: x["line"] or 0)

    return results


def collect_calls_in_expression(expr):
    calls = []

    if expr is None:
        return calls

    for node in ast.walk(expr):
        if isinstance(node, ast.Call):
            name = call_name(node)

            if name:
                calls.append({
                    "name": name,
                    "line": line_of(node),
                    "text": ast.unparse(node),
                    "node": node,
                })

    return calls


def collect_indicator_calls(tree, indicator_names):
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)

        if not name:
            continue

        if name.lower() not in indicator_names:
            continue

        results.append({
            "name": name,
            "line": line_of(node),
            "text": ast.unparse(node),
            "node": node,
        })

    results.sort(key=lambda x: x["line"] or 0)

    return results


def function_calls_target(function_node, target):
    results = []

    if function_node is None:
        return results

    target_lower = target.lower()

    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            text = ast.unparse(node).lower()

            if target_lower in text:
                results.append({
                    "line": line_of(node),
                    "text": ast.unparse(node),
                    "name": call_name(node),
                })

    return results


def assignment_rhs_calls(assignment):
    node = assignment["node"]

    if isinstance(node, ast.Assign):
        return collect_calls_in_expression(node.value)

    if isinstance(node, ast.AnnAssign):
        return collect_calls_in_expression(node.value)

    return []


def resolve_target_chain(tree, functions, target):
    assignments = collect_assignments(tree, target)

    result = {
        "target": target,
        "target_assignments": assignments,
        "producer_functions": [],
        "indicator_calls": [],
        "implementation": [],
        "return_values": [],
        "storage_assignments": [],
    }

    # --------------------------------------------------------
    # 1. TARGET FIELD
    # --------------------------------------------------------

    for assignment in assignments:
        result["storage_assignments"].append({
            "line": assignment["line"],
            "text": assignment["text"],
        })

        fn_name = find_function_for_line(
            functions,
            assignment["line"],
        )

        if fn_name:
            result["producer_functions"].append({
                "function": fn_name,
                "line": assignment["line"],
                "assignment": assignment["text"],
            })

        # ----------------------------------------------------
        # 2. INDICATOR FUNCTION CALL
        # ----------------------------------------------------

        for call in assignment_rhs_calls(assignment):
            result["indicator_calls"].append({
                "name": call["name"],
                "line": call["line"],
                "text": call["text"],
                "producer_function": fn_name,
            })

    # --------------------------------------------------------
    # 3. FIND POSSIBLE PRODUCER FUNCTIONS BY TARGET REFERENCES
    # --------------------------------------------------------

    for fn_name, fn_node in functions.items():

        fn_text = ast.unparse(fn_node)

        if target.lower() in fn_text.lower():

            result["producer_functions"].append({
                "function": fn_name,
                "line": line_of(fn_node),
                "assignment": None,
                "source_reference": True,
            })

            for node in ast.walk(fn_node):

                if isinstance(node, ast.Call):

                    name = call_name(node)

                    if name:
                        result["indicator_calls"].append({
                            "name": name,
                            "line": line_of(node),
                            "text": ast.unparse(node),
                            "producer_function": fn_name,
                        })

    # --------------------------------------------------------
    # DEDUPLICATE PRODUCERS
    # --------------------------------------------------------

    unique_producers = {}

    for item in result["producer_functions"]:
        key = (
            item.get("function"),
            item.get("line"),
        )

        unique_producers[key] = item

    result["producer_functions"] = list(
        unique_producers.values()
    )

    # --------------------------------------------------------
    # DEDUPLICATE CALLS
    # --------------------------------------------------------

    unique_calls = {}

    for item in result["indicator_calls"]:
        key = (
            item.get("name"),
            item.get("line"),
            item.get("producer_function"),
        )

        unique_calls[key] = item

    result["indicator_calls"] = list(
        unique_calls.values()
    )

    result["producer_functions"].sort(
        key=lambda x: x.get("line") or 0
    )

    result["indicator_calls"].sort(
        key=lambda x: x.get("line") or 0
    )

    return result


def find_returns(functions):
    results = []

    for fn_name, fn_node in functions.items():

        for node in ast.walk(fn_node):

            if isinstance(node, ast.Return):

                value = None

                if node.value is not None:
                    value = ast.unparse(node.value)

                results.append({
                    "function": fn_name,
                    "line": line_of(node),
                    "value": value,
                })

    return results


def find_indicator_implementations(functions):
    indicators = {
        "ema",
        "ema_series",
        "rsi",
        "calculate_ema",
        "calculate_rsi",
    }

    found = {}

    for fn_name, fn_node in functions.items():

        if fn_name.lower() in indicators:

            found[fn_name] = {
                "function": fn_name,
                "line": line_of(fn_node),
                "end_line": getattr(fn_node, "end_lineno", None),
            }

    return found


def find_related_returns(functions, indicator_names):
    results = []

    for fn_name, fn_node in functions.items():

        if fn_name.lower() not in indicator_names:
            continue

        for node in ast.walk(fn_node):

            if isinstance(node, ast.Return):

                results.append({
                    "function": fn_name,
                    "line": line_of(node),
                    "value": (
                        ast.unparse(node.value)
                        if node.value is not None
                        else None
                    ),
                })

    return results


def db_inventory():
    result = {
        "found": DB_PATH.exists(),
        "tables": [],
        "market_data": False,
        "columns": [],
    }

    if not DB_PATH.exists():
        return result

    conn = sqlite3.connect(str(DB_PATH))

    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        )

        result["tables"] = [
            row[0]
            for row in cur.fetchall()
        ]

        result["market_data"] = "market_data" in result["tables"]

        if result["market_data"]:

            cur.execute(
                "PRAGMA table_info(market_data)"
            )

            result["columns"] = [
                row[1]
                for row in cur.fetchall()
            ]

    finally:
        conn.close()

    return result


def runtime_targets():
    rows = []

    if not DB_PATH.exists():
        return rows

    conn = sqlite3.connect(str(DB_PATH))

    try:
        cur = conn.cursor()

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

        cur.execute("PRAGMA table_info(market_data)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        if not required.issubset(columns):
            return rows

        placeholders = ",".join("?" for _ in TARGETS)

        cur.execute(
            f"""
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
            WHERE symbol IN ({placeholders})
            AND source_timestamp IS NOT NULL
            ORDER BY source_timestamp DESC, id DESC
            """,
            tuple(TARGETS.keys()),
        )

        seen = set()

        for row in cur.fetchall():

            symbol = row[1]

            if symbol in seen:
                continue

            seen.add(symbol)

            rows.append({
                "id": row[0],
                "symbol": symbol,
                "source_timestamp": row[2],
                "engine_version": row[3],
                "close": row[4],
                "ema20": row[5],
                "ema50": row[6],
                "rsi14": row[7],
            })

    finally:
        conn.close()

    return rows


def print_header(title):
    print("=" * 100)
    print(title)
    print("=" * 100)


def main():

    print_header(
        "ARUNDA INDICATOR CURRENT CONVENTION "
        "MISSING CHAIN FORENSIC AUDIT v0.1"
    )

    print("MODE                       : READ ONLY")
    print("DATABASE WRITE             : NONE")
    print("FORMULA WRITE              : NONE")
    print("PRODUCTION RECALCULATION   : NONE")
    print(
        "PURPOSE                    : "
        "INSPECT ONLY MISSING CHAIN COMPONENTS"
    )

    print()
    print_header("PATH RESOLUTION RULE")

    print(
        "This audit searches only for the three previously missing "
        "components:"
    )
    print("  1. TARGET FIELD")
    print("  2. PRODUCER FUNCTION")
    print("  3. INDICATOR FUNCTION CALL")
    print()
    print(
        "Existing implementation / return / storage evidence is "
        "NOT reclassified here."
    )

    print()
    print_header("ENGINE SOURCE INVENTORY")

    print(f"ENGINE PATH                 : {ENGINE_PATH}")
    print(f"ENGINE FOUND                : {ENGINE_PATH.exists()}")

    if not ENGINE_PATH.exists():
        print()
        print("FATAL STATUS                : ENGINE_NOT_FOUND")
        return

    source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = source.splitlines()

    print(f"SOURCE SIZE                 : {len(source)} characters")
    print(f"SOURCE LINES                : {len(lines)}")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:

        print()
        print("AST PARSE STATUS             : FAILED")
        print(f"SYNTAX ERROR LINE           : {exc.lineno}")
        print(f"SYNTAX ERROR                : {exc.msg}")
        print()
        print("AUDIT STATUS                : SOURCE_PARSE_BLOCKED")
        print("DATABASE WRITE OPERATIONS   : NONE")
        print("ENGINE MODIFICATIONS        : NONE")
        print("AUDIT COMPLETE")
        return

    functions = build_function_inventory(tree)

    print()
    print_header("FUNCTION INVENTORY")

    for name in [
        "ema",
        "ema_series",
        "rsi",
        "calculate_ema",
        "calculate_rsi",
    ]:

        if name in functions:
            fn = functions[name]

            print(
                f"  [FOUND]     : {name} "
                f"(line {line_of(fn)})"
            )
        else:
            print(f"  [NOT FOUND] : {name}")

    print()
    print_header("DATABASE INVENTORY")

    db = db_inventory()

    print(f"DATABASE PATH              : {DB_PATH}")
    print(f"DATABASE FOUND             : {db['found']}")

    if db["found"]:
        print(f"TABLE COUNT                : {len(db['tables'])}")
        print(
            f"MARKET_DATA               : "
            f"{'FOUND' if db['market_data'] else 'NOT FOUND'}"
        )
        print(
            f"COLUMN COUNT              : "
            f"{len(db['columns'])}"
        )

        required_columns = [
            "id",
            "symbol",
            "source_timestamp",
            "engine_version",
            "close",
            "ema20",
            "ema50",
            "rsi14",
        ]

        for column in required_columns:
            status = (
                "PRESENT"
                if column in db["columns"]
                else "MISSING"
            )

            print(
                f"  [{status}] : {column}"
            )

    print()
    print_header("MISSING CHAIN FORENSIC")

    all_results = {}

    for label, field in TARGETS.items():

        result = resolve_target_chain(
            tree,
            functions,
            field,
        )

        all_results[label] = result

        print()
        print("=" * 100)
        print(f"TARGET : {field}")
        print("=" * 100)

        # ----------------------------------------------------
        # TARGET FIELD
        # ----------------------------------------------------

        print()
        print("1. TARGET FIELD")
        print("-" * 100)

        if result["target_assignments"]:

            print(
                f"TARGET REFERENCES FOUND : "
                f"{len(result['target_assignments'])}"
            )

            for item in result["target_assignments"]:

                print(
                    f"  [FOUND] line {item['line']} "
                    f": {item['text']}"
                )

                start = max(1, item["line"] - 2)
                end = min(
                    len(lines),
                    item["line"] + 2,
                )

                print(
                    source_segment(
                        lines,
                        start,
                        end,
                    )
                )

        else:

            print(
                "TARGET FIELD ASSIGNMENT : "
                "NOT DIRECTLY FOUND"
            )

            # Search textual references as fallback evidence.
            refs = []

            pattern = re.compile(
                rf"\b{re.escape(field)}\b",
                re.IGNORECASE,
            )

            for number, text in enumerate(
                lines,
                start=1,
            ):

                if pattern.search(text):
                    refs.append((number, text))

            if refs:

                print(
                    f"TARGET TEXT REFERENCES : "
                    f"{len(refs)}"
                )

                for number, text in refs[:20]:

                    print(
                        f"  [REFERENCE] line {number} : "
                        f"{text.strip()}"
                    )

            else:

                print(
                    "TARGET TEXT REFERENCES : NONE"
                )

        # ----------------------------------------------------
        # PRODUCER FUNCTION
        # ----------------------------------------------------

        print()
        print("2. PRODUCER FUNCTION")
        print("-" * 100)

        producers = result["producer_functions"]

        if producers:

            unique = {}

            for item in producers:

                key = (
                    item.get("function"),
                    item.get("line"),
                )

                unique[key] = item

            for item in sorted(
                unique.values(),
                key=lambda x: x.get("line") or 0,
            ):

                print(
                    f"  [CANDIDATE] "
                    f"{item.get('function')} "
                    f"(line {item.get('line')})"
                )

                if item.get("assignment"):
                    print(
                        f"    ASSIGNMENT : "
                        f"{item['assignment']}"
                    )

        else:

            print(
                "PRODUCER FUNCTION : "
                "NOT RESOLVED"
            )

        # ----------------------------------------------------
        # INDICATOR CALL
        # ----------------------------------------------------

        print()
        print("3. INDICATOR FUNCTION CALL")
        print("-" * 100)

        calls = result["indicator_calls"]

        if calls:

            unique = {}

            for item in calls:

                key = (
                    item.get("name"),
                    item.get("line"),
                    item.get("producer_function"),
                )

                unique[key] = item

            for item in sorted(
                unique.values(),
                key=lambda x: x.get("line") or 0,
            ):

                print(
                    f"  [CALL] {item.get('name')} "
                    f"(line {item.get('line')})"
                )

                print(
                    f"    EXPRESSION : "
                    f"{item.get('text')}"
                )

                print(
                    f"    PRODUCER   : "
                    f"{item.get('producer_function')}"
                )

        else:

            print(
                "INDICATOR FUNCTION CALL : "
                "NOT RESOLVED"
            )

        # ----------------------------------------------------
        # DIRECT CHAIN INTERPRETATION
        # ----------------------------------------------------

        target_found = bool(
            result["target_assignments"]
        )

        producer_found = bool(
            result["producer_functions"]
        )

        call_found = bool(
            result["indicator_calls"]
        )

        print()
        print("CHAIN COMPONENT STATUS")
        print("-" * 100)

        print(
            f"  [{'FOUND' if target_found else 'MISSING':8}] "
            f": TARGET FIELD"
        )

        print(
            f"  [{'FOUND' if producer_found else 'MISSING':8}] "
            f": PRODUCER FUNCTION"
        )

        print(
            f"  [{'FOUND' if call_found else 'MISSING':8}] "
            f": INDICATOR FUNCTION CALL"
        )

        missing_count = sum(
            [
                not target_found,
                not producer_found,
                not call_found,
            ]
        )

        if missing_count == 0:
            chain_status = "MISSING_COMPONENTS_RESOLVED"
        else:
            chain_status = "INCOMPLETE"

        print()
        print(
            f"CHAIN STATUS : {chain_status}"
        )

    print()
    print_header(
        "FINAL MISSING CHAIN FORENSIC SUMMARY"
    )

    targets_checked = len(TARGETS)

    target_resolved = 0
    producer_resolved = 0
    call_resolved = 0
    complete_missing_components = 0

    for label, result in all_results.items():

        target_ok = bool(
            result["target_assignments"]
        )

        producer_ok = bool(
            result["producer_functions"]
        )

        call_ok = bool(
            result["indicator_calls"]
        )

        if target_ok:
            target_resolved += 1

        if producer_ok:
            producer_resolved += 1

        if call_ok:
            call_resolved += 1

        if (
            target_ok
            and producer_ok
            and call_ok
        ):
            complete_missing_components += 1

    print(
        f"TARGETS CHECKED             : "
        f"{targets_checked}"
    )

    print(
        f"TARGET FIELD RESOLVED       : "
        f"{target_resolved} / {targets_checked}"
    )

    print(
        f"PRODUCER FUNCTION RESOLVED  : "
        f"{producer_resolved} / {targets_checked}"
    )

    print(
        f"INDICATOR CALL RESOLVED     : "
        f"{call_resolved} / {targets_checked}"
    )

    print(
        f"ALL MISSING COMPONENTS      : "
        f"{complete_missing_components} / "
        f"{targets_checked}"
    )

    print()
    print("TARGET MATRIX")
    print("-" * 100)

    for label, result in all_results.items():

        target_ok = bool(
            result["target_assignments"]
        )

        producer_ok = bool(
            result["producer_functions"]
        )

        call_ok = bool(
            result["indicator_calls"]
        )

        if (
            target_ok
            and producer_ok
            and call_ok
        ):
            status = "RESOLVED"
        else:
            status = "INCOMPLETE"

        print(
            f"  [{status:10}] : {label}"
        )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("=" * 100)

    if complete_missing_components == targets_checked:

        print(
            "STATUS                  : "
            "MISSING_CHAIN_RESOLVED"
        )

        print(
            "REASON                  : "
            "ALL PREVIOUSLY MISSING COMPONENTS "
            "ARE TRACEABLE"
        )

        print(
            "NEXT STEP               : "
            "RECONSTRUCT COMPLETE EXECUTION CHAIN"
        )

    else:

        print(
            "STATUS                  : "
            "MISSING_CHAIN_INCOMPLETE"
        )

        print(
            "REASON                  : "
            "ONE OR MORE MISSING COMPONENTS "
            "REMAIN UNRESOLVED"
        )

        print(
            "NEXT STEP               : "
            "INSPECT ONLY THE REMAINING "
            "UNRESOLVED COMPONENTS"
        )

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("ENGINE MODIFICATIONS      : NONE")
    print("FORMULA WRITE             : NONE")
    print("PRODUCTION RECALCULATION  : NONE")
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()