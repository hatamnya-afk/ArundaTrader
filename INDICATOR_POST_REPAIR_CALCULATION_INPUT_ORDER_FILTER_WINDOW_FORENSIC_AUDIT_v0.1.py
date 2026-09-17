import ast
import os
import sqlite3
import sys
import math
from collections import Counter
from datetime import datetime


# =============================================================================
# ARUNDA INDICATOR POST REPAIR
# CALCULATION INPUT ORDER / FILTER / WINDOW FORENSIC AUDIT v0.1
# =============================================================================
#
# MODE:
#   READ ONLY
#
# GUARANTEES:
#   - NO database writes
#   - NO engine writes
#   - NO formula writes
#   - NO production recalculation
#
# PURPOSE:
#   Resolve the exact input semantics used by calculate_analysis():
#
#       market_data
#           |
#           v
#       get_snapshot_history()
#           |
#           v
#       rows
#           |
#           v
#       calculate_analysis(rows)
#           |
#           v
#       closes
#           |
#           +--> ema20
#           +--> ema50
#           +--> rsi14
#
# =============================================================================


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINE_PATH = os.path.join(
    BASE_DIR,
    "market_data_engine.py",
)

DB_PATH = os.path.join(
    BASE_DIR,
    "arunda.db",
)

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

LOOKBACK = 120

DEFAULT_SOURCE = "COINMARKETCAP"


# =============================================================================
# PRINT HELPERS
# =============================================================================

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


def print_subsection(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def print_kv(key, value):
    print(f"{key:<35}: {value}")


def safe_text(value):
    if value is None:
        return "None"
    return str(value)


def truncate(value, width=180):
    text = safe_text(value)
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


# =============================================================================
# FILE / SOURCE HELPERS
# =============================================================================

def read_text(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return handle.read()


def get_source_lines(source):
    return source.splitlines()


def get_node_end_lineno(node):
    return getattr(
        node,
        "end_lineno",
        getattr(node, "lineno", 0),
    )


def source_block(lines, start, end, context=0):
    start_index = max(0, start - 1 - context)
    end_index = min(len(lines), end + context)

    output = []

    for index in range(start_index, end_index):
        marker = ">>> " if (index + 1) == start else "    "
        output.append(
            f"{marker}{index + 1:5d}: {lines[index]}"
        )

    return "\n".join(output)


# =============================================================================
# AST HELPERS
# =============================================================================

def parse_engine():
    source = read_text(ENGINE_PATH)

    tree = ast.parse(
        source,
        filename=ENGINE_PATH,
    )

    return source, tree


def function_inventory(tree):
    inventory = {}

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            inventory[node.name] = {
                "node": node,
                "start": node.lineno,
                "end": get_node_end_lineno(node),
            }

    return inventory


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            if node.name == name:
                return node

    return None


def find_calls(tree, function_name):
    results = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            caller = node.name

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    target = child.func

                    target_name = None

                    if isinstance(target, ast.Name):
                        target_name = target.id

                    elif isinstance(target, ast.Attribute):
                        target_name = target.attr

                    if target_name == function_name:
                        results.append(
                            {
                                "caller": caller,
                                "line": child.lineno,
                                "node": child,
                            }
                        )

    return results


def ast_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse unavailable>"


# =============================================================================
# SQL ANALYSIS
# =============================================================================

def normalize_sql(sql):
    if sql is None:
        return ""

    return " ".join(
        str(sql).split()
    )


def extract_sql_strings(function_node):
    results = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                text = node.value

                upper = text.upper()

                if (
                    "SELECT" in upper
                    or "INSERT" in upper
                    or "UPDATE" in upper
                    or "DELETE" in upper
                    or "FROM" in upper
                ):
                    results.append(
                        {
                            "line": node.lineno,
                            "sql": text,
                        }
                    )

    return results


def sql_select_columns(sql):
    normalized = normalize_sql(sql)

    upper = normalized.upper()

    if not upper.startswith("SELECT "):
        return []

    if " FROM " not in upper:
        return []

    select_part = normalized[
        len("SELECT "):
        upper.index(" FROM ")
    ]

    if select_part.strip() == "*":
        return ["*"]

    columns = []

    for item in select_part.split(","):
        item = item.strip()

        if not item:
            continue

        columns.append(item)

    return columns


# =============================================================================
# ROW ACCESS / CLOSES ANALYSIS
# =============================================================================

def find_name_uses(function_node, name):
    results = []

    for node in ast.walk(function_node):
        if isinstance(node, ast.Name):
            if node.id == name:
                results.append(
                    {
                        "line": node.lineno,
                        "ctx": type(node.ctx).__name__,
                        "node": node,
                    }
                )

    return results


def find_assignments(function_node, variable_name):
    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.Assign):
            targets = node.targets

            for target in targets:

                if (
                    isinstance(target, ast.Name)
                    and target.id == variable_name
                ):
                    results.append(
                        {
                            "line": node.lineno,
                            "node": node,
                            "value": node.value,
                        }
                    )

        elif isinstance(node, ast.AnnAssign):

            target = node.target

            if (
                isinstance(target, ast.Name)
                and target.id == variable_name
            ):
                results.append(
                    {
                        "line": node.lineno,
                        "node": node,
                        "value": node.value,
                    }
                )

    return results


def find_append_calls(function_node, variable_name):
    results = []

    for node in ast.walk(function_node):

        if not isinstance(node, ast.Call):
            continue

        func = node.func

        if not isinstance(func, ast.Attribute):
            continue

        if func.attr != "append":
            continue

        if not isinstance(func.value, ast.Name):
            continue

        if func.value.id != variable_name:
            continue

        argument = None

        if node.args:
            argument = node.args[0]

        results.append(
            {
                "line": node.lineno,
                "node": node,
                "argument": argument,
            }
        )

    return results


def find_subscript_accesses(function_node, variable_name):
    results = []

    for node in ast.walk(function_node):

        if not isinstance(node, ast.Subscript):
            continue

        value = node.value

        if not (
            isinstance(value, ast.Name)
            and value.id == variable_name
        ):
            continue

        results.append(
            {
                "line": node.lineno,
                "node": node,
                "expression": ast_unparse(node),
            }
        )

    return results


def find_row_field_accesses(function_node):
    """
    Find common row field access forms:

        row["close"]
        row[4]
        r["close"]
        r[4]

    Does not assume one representation.
    """

    results = []

    for node in ast.walk(function_node):

        if not isinstance(node, ast.Subscript):
            continue

        value = node.value

        if not isinstance(value, ast.Name):
            continue

        name = value.id.lower()

        if name not in {
            "row",
            "r",
            "record",
            "item",
            "data",
        }:
            continue

        results.append(
            {
                "line": node.lineno,
                "variable": value.id,
                "expression": ast_unparse(node),
            }
        )

    return results


# =============================================================================
# FILTER / ORDER FORENSICS
# =============================================================================

def find_control_flow(function_node):
    results = []

    for node in ast.walk(function_node):

        if isinstance(node, ast.If):

            results.append(
                {
                    "type": "IF",
                    "line": node.lineno,
                    "condition": ast_unparse(node.test),
                }
            )

        elif isinstance(node, ast.For):

            results.append(
                {
                    "type": "FOR",
                    "line": node.lineno,
                    "condition": ast_unparse(node.target),
                    "iter": ast_unparse(node.iter),
                }
            )

        elif isinstance(node, ast.While):

            results.append(
                {
                    "type": "WHILE",
                    "line": node.lineno,
                    "condition": ast_unparse(node.test),
                }

            )

        elif isinstance(node, ast.ListComp):

            results.append(
                {
                    "type": "LISTCOMP",
                    "line": node.lineno,
                    "condition": ast_unparse(node),
                }
            )

    return results


def extract_order_by(sql):
    normalized = normalize_sql(sql)

    upper = normalized.upper()

    if " ORDER BY " not in upper:
        return None

    start = upper.index(" ORDER BY ") + len(" ORDER BY ")

    tail = normalized[start:]

    for keyword in [
        " LIMIT ",
        " OFFSET ",
        " WHERE ",
        " GROUP BY ",
    ]:
        pos = tail.upper().find(keyword)

        if pos >= 0:
            tail = tail[:pos]

    return tail.strip()


def extract_limit(sql):
    normalized = normalize_sql(sql)

    upper = normalized.upper()

    if " LIMIT " not in upper:
        return None

    start = upper.index(" LIMIT ") + len(" LIMIT ")

    tail = normalized[start:]

    for keyword in [
        " OFFSET ",
        " WHERE ",
        " GROUP BY ",
        " ORDER BY ",
    ]:
        pos = tail.upper().find(keyword)

        if pos >= 0:
            tail = tail[:pos]

    return tail.strip()


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def connect_db():
    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_table_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_count(conn):
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchone()

    return int(row[0])


# =============================================================================
# PRODUCTION WINDOW
# =============================================================================

def resolve_source_constant(tree):
    """
    Try to resolve SNAPSHOT_SOURCE from the engine source.

    This is intentionally conservative.
    If it cannot be resolved, caller may use the production
    record source instead.
    """

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:

            if not isinstance(target, ast.Name):
                continue

            if target.id != "SNAPSHOT_SOURCE":
                continue

            value = node.value

            if isinstance(value, ast.Constant):
                if isinstance(value.value, str):
                    return value.value

    return None


def get_target_record(conn, symbol):
    row = conn.execute(
        """
        SELECT *
        FROM market_data
        WHERE symbol = ?
          AND timeframe = 'SNAPSHOT'
        ORDER BY id DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()

    return row


def get_actual_production_window(
    conn,
    symbol,
    source,
    limit,
):
    """
    Reconstruct the exact SQL semantics discovered in
    get_snapshot_history():

        symbol = ?
        source = ?
        timeframe = 'SNAPSHOT'
        close IS NOT NULL
        ORDER BY id ASC
        LIMIT ?

    """

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            symbol,
            timeframe,
            close,
            volume,
            price_change_1h,
            price_change_24h,
            market_cap,
            volume_24h,
            source,
            source_timestamp,
            source_latency_ms,
            engine_version
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = 'SNAPSHOT'
            AND close IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (
            symbol,
            source,
            limit,
        ),
    ).fetchall()

    return rows


# =============================================================================
# NUMERIC HELPERS
# =============================================================================

def to_float(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(value):
        return None

    return value


# =============================================================================
# STANDARD INDICATOR RECONSTRUCTION
# =============================================================================

def ema(values, period):
    clean = [
        to_float(x)
        for x in values
        if to_float(x) is not None
    ]

    if not clean:
        return None

    if len(clean) < period:
        return None

    seed = sum(
        clean[:period]
    ) / period

    alpha = 2.0 / (
        period + 1.0
    )

    result = seed

    for value in clean[period:]:
        result = (
            (value - result)
            * alpha
            + result
        )

    return result


def rsi(values, period=14):
    clean = [
        to_float(x)
        for x in values
        if to_float(x) is not None
    ]

    if len(clean) <= period:
        return None

    gains = []
    losses = []

    for index in range(
        1,
        len(clean),
    ):
        delta = (
            clean[index]
            - clean[index - 1]
        )

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)

        else:
            gains.append(0.0)
            losses.append(-delta)

    if len(gains) < period:
        return None

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = (
        avg_gain
        / avg_loss
    )

    return (
        100.0
        - (
            100.0
            / (1.0 + rs)
        )
    )


# =============================================================================
# CLOSES SEMANTICS RECONSTRUCTION
# =============================================================================

def reconstruct_closes_from_rows(rows):
    """
    This function intentionally models the expected production semantic:

        rows
          -> row["close"]
          -> closes

    It does NOT alter ordering.

    SQLite rows are already returned in the production ORDER BY id ASC
    semantics.

    Invalid / NULL closes are excluded, matching:
        close IS NOT NULL
    in the production SQL.

    """

    closes = []

    for row in rows:

        value = to_float(
            row["close"]
        )

        if value is None:
            continue

        closes.append(value)

    return closes


# =============================================================================
# EXACT WINDOW DIAGNOSTICS
# =============================================================================

def summarize_rows(rows):
    if not rows:
        return {
            "count": 0,
            "first_id": None,
            "last_id": None,
            "first_timestamp": None,
            "last_timestamp": None,
            "first_source_timestamp": None,
            "last_source_timestamp": None,
            "first_close": None,
            "last_close": None,
        }

    return {
        "count": len(rows),

        "first_id": rows[0]["id"],
        "last_id": rows[-1]["id"],

        "first_timestamp": rows[0]["timestamp"],
        "last_timestamp": rows[-1]["timestamp"],

        "first_source_timestamp": (
            rows[0]["source_timestamp"]
        ),

        "last_source_timestamp": (
            rows[-1]["source_timestamp"]
        ),

        "first_close": rows[0]["close"],
        "last_close": rows[-1]["close"],
    }


def compare_order(rows):
    ids = [
        int(row["id"])
        for row in rows
    ]

    ascending = (
        ids == sorted(ids)
    )

    strictly_ascending = all(
        ids[index]
        < ids[index + 1]
        for index in range(
            len(ids) - 1
        )
    )

    return {
        "ascending": ascending,
        "strictly_ascending": strictly_ascending,
    }


def engine_distribution(rows):
    counter = Counter()

    for row in rows:
        counter[
            row["engine_version"]
        ] += 1

    return counter


def source_distribution(rows):
    counter = Counter()

    for row in rows:
        counter[
            row["source"]
        ] += 1

    return counter


def timeframe_distribution(rows):
    counter = Counter()

    for row in rows:
        counter[
            row["timeframe"]
        ] += 1

    return counter


# =============================================================================
# PRODUCTION INDICATOR RECONSTRUCTION
# =============================================================================

def reconstruct_indicators(closes):
    return {
        "ema20": ema(
            closes,
            20,
        ),

        "ema50": ema(
            closes,
            50,
        ),

        "rsi14": rsi(
            closes,
            14,
        ),
    }


def relative_error(current, standard):
    if (
        current is None
        or standard is None
    ):
        return None

    if standard == 0:
        return None

    return abs(
        current - standard
    ) / abs(standard)


def absolute_error(current, standard):
    if (
        current is None
        or standard is None
    ):
        return None

    return abs(
        current - standard
    )


# =============================================================================
# SOURCE CODE FORENSICS
# =============================================================================

def audit_engine_source(source, tree):
    lines = get_source_lines(source)
    inventory = function_inventory(tree)

    get_history = inventory.get(
        "get_snapshot_history"
    )

    calculate = inventory.get(
        "calculate_analysis"
    )

    print_section(
        "STEP 1 — ENGINE SOURCE FORENSICS"
    )

    print_kv(
        "ENGINE PATH",
        ENGINE_PATH,
    )

    print_kv(
        "ENGINE FOUND",
        os.path.exists(ENGINE_PATH),
    )

    print_kv(
        "SOURCE SIZE",
        len(source),
    )

    print_kv(
        "SOURCE LINES",
        len(lines),
    )

    print_kv(
        "AST STATUS",
        "SUCCESS",
    )

    if get_history:
        print_kv(
            "get_snapshot_history()",
            f"LINE {get_history['start']}-{get_history['end']}",
        )

    if calculate:
        print_kv(
            "calculate_analysis()",
            f"LINE {calculate['start']}-{calculate['end']}",
        )

    print_subsection(
        "SNAPSHOT_SOURCE RESOLUTION"
    )

    snapshot_source = (
        resolve_source_constant(tree)
    )

    print_kv(
        "SNAPSHOT_SOURCE",
        snapshot_source,
    )

    if get_history:

        print_subsection(
            "get_snapshot_history() SQL"
        )

        sqls = extract_sql_strings(
            get_history["node"]
        )

        for item in sqls:

            print(
                f"LINE {item['line']}"
            )

            print(
                truncate(
                    normalize_sql(
                        item["sql"]
                    ),
                    500,
                )
            )

            print(
                f"SELECT COLUMNS : "
                f"{sql_select_columns(item['sql'])}"
            )

            print(
                f"ORDER BY      : "
                f"{extract_order_by(item['sql'])}"
            )

            print(
                f"LIMIT         : "
                f"{extract_limit(item['sql'])}"
            )

    if calculate:

        print_subsection(
            "calculate_analysis() closes assignments"
        )

        assignments = find_assignments(
            calculate["node"],
            "closes",
        )

        for item in assignments:

            print()
            print(
                f"ASSIGNMENT LINE : {item['line']}"
            )

            print(
                ast_unparse(
                    item["node"]
                )
            )

        appends = find_append_calls(
            calculate["node"],
            "closes",
        )

        print()

        print(
            f"CLOSES APPEND CALLS : {len(appends)}"
        )

        for item in appends:

            print()
            print(
                f"APPEND LINE : {item['line']}"
            )

            print(
                f"ARGUMENT    : "
                f"{ast_unparse(item['argument'])}"
            )

            start = max(
                1,
                item["line"] - 4,
            )

            end = item["line"] + 4

            print(
                source_block(
                    lines,
                    start,
                    end,
                )
            )

        print_subsection(
            "calculate_analysis() row field accesses"
        )

        accesses = find_row_field_accesses(
            calculate["node"]
        )

        if not accesses:
            print(
                "[NONE] No row[...] accesses detected"
            )

        else:

            seen = set()

            for item in accesses:

                key = (
                    item["line"],
                    item["expression"],
                )

                if key in seen:
                    continue

                seen.add(key)

                print(
                    f"LINE {item['line']:<6} "
                    f"{item['expression']}"
                )

        print_subsection(
            "calculate_analysis() control flow"
        )

        controls = find_control_flow(
            calculate["node"]
        )

        for item in controls:

            if item["type"] == "IF":

                print(
                    f"[IF] LINE {item['line']} "
                    f"CONDITION: "
                    f"{item['condition']}"
                )

            elif item["type"] == "FOR":

                print(
                    f"[FOR] LINE {item['line']} "
                    f"TARGET: "
                    f"{item['condition']} "
                    f"ITER: "
                    f"{item['iter']}"
                )

            elif item["type"] == "WHILE":

                print(
                    f"[WHILE] LINE {item['line']} "
                    f"CONDITION: "
                    f"{item['condition']}"
                )

            elif item["type"] == "LISTCOMP":

                print(
                    f"[LISTCOMP] LINE {item['line']} "
                    f"{item['condition']}"
                )

    return {
        "snapshot_source": snapshot_source,
        "calculate": calculate,
        "get_history": get_history,
    }


# =============================================================================
# SYMBOL FORENSICS
# =============================================================================

def verify_symbol(
    conn,
    symbol,
    source,
    calculate_node,
):
    print_section(
        f"SYMBOL : {symbol}"
    )

    target = get_target_record(
        conn,
        symbol,
    )

    if target is None:

        print(
            "[UNRESOLVED] Production record not found"
        )

        return {
            "status": "UNRESOLVED",
            "reason": "NO_PRODUCTION_RECORD",
        }

    print_subsection(
        "PRODUCTION TARGET RECORD"
    )

    print_kv(
        "ID",
        target["id"],
    )

    print_kv(
        "TIMESTAMP",
        target["timestamp"],
    )

    print_kv(
        "SOURCE_TIMESTAMP",
        target["source_timestamp"],
    )

    print_kv(
        "CLOSE",
        target["close"],
    )

    print_kv(
        "EMA20",
        target["ema20"],
    )

    print_kv(
        "EMA50",
        target["ema50"],
    )

    print_kv(
        "RSI14",
        target["rsi14"],
    )

    print_kv(
        "SOURCE",
        target["source"],
    )

    print_kv(
        "TIMEFRAME",
        target["timeframe"],
    )

    print_kv(
        "ENGINE_VERSION",
        target["engine_version"],
    )

    # -------------------------------------------------------------------------
    # Actual production source
    # -------------------------------------------------------------------------

    actual_source = (
        source
        if source
        else target["source"]
    )

    rows = get_actual_production_window(
        conn,
        symbol,
        actual_source,
        LOOKBACK,
    )

    print_subsection(
        "ACTUAL PRODUCTION ROW WINDOW"
    )

    summary = summarize_rows(
        rows
    )

    print_kv(
        "ROW COUNT",
        summary["count"],
    )

    print_kv(
        "FIRST ID",
        summary["first_id"],
    )

    print_kv(
        "LAST ID",
        summary["last_id"],
    )

    print_kv(
        "FIRST TIMESTAMP",
        summary["first_timestamp"],
    )

    print_kv(
        "LAST TIMESTAMP",
        summary["last_timestamp"],
    )

    print_kv(
        "FIRST SOURCE TIME",
        summary["first_source_timestamp"],
    )

    print_kv(
        "LAST SOURCE TIME",
        summary["last_source_timestamp"],
    )

    print_kv(
        "FIRST CLOSE",
        summary["first_close"],
    )

    print_kv(
        "LAST CLOSE",
        summary["last_close"],
    )

    if not rows:

        print(
            "[UNRESOLVED] No production rows"
        )

        return {
            "status": "UNRESOLVED",
            "reason": "NO_PRODUCTION_ROWS",
        }

    # -------------------------------------------------------------------------
    # Order
    # -------------------------------------------------------------------------

    print_subsection(
        "INPUT ORDER FORENSICS"
    )

    order = compare_order(
        rows
    )

    print_kv(
        "ID ORDER ASCENDING",
        order["ascending"],
    )

    print_kv(
        "ID ORDER STRICTLY ASCENDING",
        order["strictly_ascending"],
    )

    # -------------------------------------------------------------------------
    # Distribution
    # -------------------------------------------------------------------------

    print_subsection(
        "ENGINE VERSION DISTRIBUTION"
    )

    for key, count in engine_distribution(
        rows
    ).items():

        print(
            f"ENGINE={safe_text(key)} | ROWS={count}"
        )

    print_subsection(
        "SOURCE DISTRIBUTION"
    )

    for key, count in source_distribution(
        rows
    ).items():

        print(
            f"SOURCE={safe_text(key)} | ROWS={count}"
        )

    print_subsection(
        "TIMEFRAME DISTRIBUTION"
    )

    for key, count in timeframe_distribution(
        rows
    ).items():

        print(
            f"TIMEFRAME={safe_text(key)} | ROWS={count}"
        )

    # -------------------------------------------------------------------------
    # First / last rows
    # -------------------------------------------------------------------------

    print_subsection(
        "FIRST 5 PRODUCTION INPUT ROWS"
    )

    for row in rows[:5]:

        print(
            "ID={id} | TIME={timestamp} | "
            "SOURCE_TIME={source_timestamp} | "
            "CLOSE={close} | SOURCE={source} | "
            "ENGINE={engine_version}".format(
                id=row["id"],
                timestamp=row["timestamp"],
                source_timestamp=row[
                    "source_timestamp"
                ],
                close=row["close"],
                source=row["source"],
                engine_version=row[
                    "engine_version"
                ],
            )
        )

    print_subsection(
        "LAST 5 PRODUCTION INPUT ROWS"
    )

    for row in rows[-5:]:

        print(
            "ID={id} | TIME={timestamp} | "
            "SOURCE_TIME={source_timestamp} | "
            "CLOSE={close} | SOURCE={source} | "
            "ENGINE={engine_version}".format(
                id=row["id"],
                timestamp=row["timestamp"],
                source_timestamp=row[
                    "source_timestamp"
                ],
                close=row["close"],
                source=row["source"],
                engine_version=row[
                    "engine_version"
                ],
            )
        )

    # -------------------------------------------------------------------------
    # Closes reconstruction
    # -------------------------------------------------------------------------

    print_subsection(
        "CALCULATION INPUT 'closes' RECONSTRUCTION"
    )

    closes = reconstruct_closes_from_rows(
        rows
    )

    print_kv(
        "ROWS RETURNED",
        len(rows),
    )

    print_kv(
        "CLOSES COUNT",
        len(closes),
    )

    print_kv(
        "ROWS == CLOSES",
        len(rows) == len(closes),
    )

    if closes:

        print_kv(
            "CLOSES FIRST",
            closes[0],
        )

        print_kv(
            "CLOSES LAST",
            closes[-1],
        )

    # -------------------------------------------------------------------------
    # Production indicator reconstruction
    # -------------------------------------------------------------------------

    print_subsection(
        "INDICATOR RECONSTRUCTION FROM ACTUAL PRODUCTION WINDOW"
    )

    reconstructed = reconstruct_indicators(
        closes
    )

    production = {
        "ema20": to_float(
            target["ema20"]
        ),

        "ema50": to_float(
            target["ema50"]
        ),

        "rsi14": to_float(
            target["rsi14"]
        ),
    }

    for name in [
        "ema20",
        "ema50",
        "rsi14",
    ]:

        current = production[name]
        standard = reconstructed[name]

        print()

        print(
            f"INDICATOR : {name.upper()}"
        )

        print(
            f"PRODUCTION STORED : {current}"
        )

        print(
            f"WINDOW REBUILT     : {standard}"
        )

        print(
            f"ABS ERROR           : "
            f"{absolute_error(current, standard)}"
        )

        print(
            f"REL ERROR           : "
            f"{relative_error(current, standard)}"
        )

        if (
            current is not None
            and standard is not None
        ):

            tolerance = max(
                1e-9,
                abs(standard) * 1e-9,
            )

            if (
                abs(
                    current - standard
                )
                <= tolerance
            ):
                print(
                    "STATUS              : MATCH"
                )

            else:
                print(
                    "STATUS              : MISMATCH"
                )

        else:

            print(
                "STATUS              : UNRESOLVED"
            )

    # -------------------------------------------------------------------------
    # Window semantics
    # -------------------------------------------------------------------------

    print_subsection(
        "WINDOW SEMANTICS VERDICT"
    )

    window_issues = []

    if len(rows) != LOOKBACK:

        window_issues.append(
            f"ROW_COUNT={len(rows)} EXPECTED={LOOKBACK}"
        )

    if not order["strictly_ascending"]:

        window_issues.append(
            "ID_ORDER_NOT_STRICTLY_ASCENDING"
        )

    if len(rows) != len(closes):

        window_issues.append(
            "ROWS_TO_CLOSES_FILTERING_DETECTED"
        )

    if not closes:

        window_issues.append(
            "NO_CLOSES"
        )

    if window_issues:

        for issue in window_issues:
            print(
                f"[ISSUE] {issue}"
            )

        window_status = (
            "SEMANTICS_DIFFERENCE_DETECTED"
        )

    else:

        print(
            "[OK] Production window contains "
            "exactly LOOKBACK valid closes in ascending id order"
        )

        window_status = "WINDOW_SEMANTICS_RESOLVED"

    # -------------------------------------------------------------------------
    # Return
    # -------------------------------------------------------------------------

    reconstruction_matches = {}

    for name in [
        "ema20",
        "ema50",
        "rsi14",
    ]:

        current = production[name]
        rebuilt = reconstructed[name]

        if (
            current is not None
            and rebuilt is not None
        ):

            tolerance = max(
                1e-9,
                abs(rebuilt) * 1e-9,
            )

            reconstruction_matches[name] = (
                abs(
                    current - rebuilt
                )
                <= tolerance
            )

        else:

            reconstruction_matches[name] = None

    return {
        "status": "COMPLETE",

        "rows": len(rows),

        "closes": len(closes),

        "order_ascending": order[
            "strictly_ascending"
        ],

        "window_status": window_status,

        "reconstruction": reconstruction_matches,

        "target": target,
    }


# =============================================================================
# FINAL VERDICT
# =============================================================================

def final_verdict(results):
    print_section(
        "FINAL CALCULATION INPUT ORDER / FILTER / WINDOW FORENSIC SUMMARY"
    )

    print_kv(
        "TARGETS CHECKED",
        len(results),
    )

    complete = 0
    unresolved = 0
    semantics_difference = 0
    indicator_match_all = 0
    indicator_mismatch = 0

    for symbol, result in results.items():

        if result["status"] != "COMPLETE":

            unresolved += 1

            print(
                f"[UNRESOLVED] {symbol}"
            )

            continue

        complete += 1

        if result[
            "window_status"
        ] != "WINDOW_SEMANTICS_RESOLVED":

            semantics_difference += 1

        reconstruction = result[
            "reconstruction"
        ]

        values = list(
            reconstruction.values()
        )

        if all(
            value is True
            for value in values
        ):

            indicator_match_all += 1

        elif any(
            value is False
            for value in values
        ):

            indicator_mismatch += 1

    print()
    print(
        f"COMPLETE TARGETS          : {complete}"
    )

    print(
        f"UNRESOLVED TARGETS        : {unresolved}"
    )

    print(
        f"WINDOW SEMANTIC ISSUES    : "
        f"{semantics_difference}"
    )

    print(
        f"ALL INDICATORS MATCH      : "
        f"{indicator_match_all}"
    )

    print(
        f"INDICATOR MISMATCH TARGETS: "
        f"{indicator_mismatch}"
    )

    print_subsection(
        "TARGET MATRIX"
    )

    for symbol, result in results.items():

        if result["status"] != "COMPLETE":

            print(
                f"  [UNRESOLVED] : {symbol}"
            )

            continue

        if (
            result["window_status"]
            != "WINDOW_SEMANTICS_RESOLVED"
        ):

            print(
                f"  [WINDOW_DIFFERENCE] : {symbol}"
            )

        elif all(
            value is True
            for value in result[
                "reconstruction"
            ].values()
        ):

            print(
                f"  [MATCH] : {symbol}"
            )

        else:

            print(
                f"  [INDICATOR_DIFFERENCE] : {symbol}"
            )

    # -------------------------------------------------------------------------
    # Cause classification
    # -------------------------------------------------------------------------

    if unresolved > 0:

        status = (
            "CALCULATION_INPUT_FORENSICS_INCOMPLETE"
        )

        reason = (
            "ONE OR MORE PRODUCTION INPUT CHAINS "
            "COULD NOT BE RESOLVED"
        )

        next_frontier = (
            "INSPECT ONLY THE UNRESOLVED INPUT COMPONENTS"
        )

    elif semantics_difference > 0:

        status = (
            "CALCULATION_INPUT_WINDOW_SEMANTICS_DIFFERENCE"
        )

        reason = (
            "PRODUCTION ROW ORDER / FILTER / WINDOW "
            "DOES NOT MATCH THE EXPECTED PRODUCTION SEMANTICS"
        )

        next_frontier = (
            "TRACE THE EXACT PRODUCTION ROW FILTER "
            "AND CLOSES CONSTRUCTION INSIDE calculate_analysis()"
        )

    elif indicator_mismatch > 0:

        status = (
            "CALCULATION_SEMANTICS_DIFFERENCE_CONFIRMED"
        )

        reason = (
            "THE ACTUAL PRODUCTION WINDOW IS RESOLVED, "
            "BUT STORED INDICATORS DO NOT RECONSTRUCT "
            "FROM THAT EXACT WINDOW"
        )

        next_frontier = (
            "TRACE EXACT INDICATOR CALCULATION "
            "SEMANTICS / INITIALIZATION / FORMULA PATH"
        )

    else:

        status = (
            "CALCULATION_INPUT_SEMANTICS_MATCH"
        )

        reason = (
            "ACTUAL PRODUCTION ROW ORDER, FILTER, "
            "WINDOW AND INDICATOR RECONSTRUCTION MATCH"
        )

        next_frontier = (
            "NO INPUT-ORDER/FILTER/WINDOW CAUSE DETECTED; "
            "PROCEED TO NEXT VERIFIED CAUSE FRONTIER"
        )

    print_section(
        "FORENSIC CONCLUSION"
    )

    print_kv(
        "STATUS",
        status,
    )

    print_kv(
        "REASON",
        reason,
    )

    print_kv(
        "NEXT FRONTIER",
        next_frontier,
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

    return 0


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "ARUNDA INDICATOR POST REPAIR CALCULATION "
        "INPUT ORDER FILTER WINDOW FORENSIC AUDIT v0.1"
    )

    print_kv(
        "MODE",
        "READ ONLY",
    )

    print_kv(
        "DATABASE WRITE",
        "NONE",
    )

    print_kv(
        "ENGINE WRITE",
        "NONE",
    )

    print_kv(
        "FORMULA WRITE",
        "NONE",
    )

    print_kv(
        "PRODUCTION RECALCULATION",
        "NONE",
    )

    print_kv(
        "PURPOSE",
        "TRACE EXACT CALCULATION INPUT ORDER / FILTER / WINDOW",
    )

    # -------------------------------------------------------------------------
    # Engine
    # -------------------------------------------------------------------------

    if not os.path.exists(
        ENGINE_PATH
    ):

        print()
        print(
            "[FATAL] market_data_engine.py not found"
        )

        return 1

    try:

        source, tree = parse_engine()

    except Exception as exc:

        print()
        print(
            "[FATAL] ENGINE AST PARSE FAILED"
        )

        print(
            f"ERROR : {exc}"
        )

        return 1

    source_info = audit_engine_source(
        source,
        tree,
    )

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------

    print_section(
        "STEP 2 — DATABASE RESOLUTION"
    )

    if not os.path.exists(
        DB_PATH
    ):

        print(
            "[FATAL] arunda.db not found"
        )

        return 1

    print_kv(
        "DATABASE PATH",
        DB_PATH,
    )

    print_kv(
        "DATABASE FOUND",
        True,
    )

    try:

        conn = connect_db()

    except Exception as exc:

        print(
            f"[FATAL] DATABASE CONNECTION FAILED: {exc}"
        )

        return 1

    try:

        print_kv(
            "TABLE COUNT",
            get_table_count(conn),
        )

        print_subsection(
            "MARKET_DATA SCHEMA"
        )

        if not table_exists(
            conn,
            "market_data",
        ):

            print(
                "[FATAL] market_data table not found"
            )

            return 1

        columns = get_table_columns(
            conn,
            "market_data",
        )

        print(
            f"COLUMN COUNT : {len(columns)}"
        )

        for index, column in enumerate(
            columns
        ):

            print(
                f"{index:02d} : {column}"
            )

        required = [
            "id",
            "timestamp",
            "symbol",
            "timeframe",
            "close",
            "source",
            "source_timestamp",
            "engine_version",
        ]

        missing = [
            column
            for column in required
            if column not in columns
        ]

        if missing:

            print()
            print(
                "[FATAL] REQUIRED COLUMNS MISSING"
            )

            for column in missing:
                print(
                    f"  - {column}"
                )

            return 1

    # -------------------------------------------------------------------------
    # Production source
    # -------------------------------------------------------------------------

        snapshot_source = (
            source_info[
                "snapshot_source"
            ]
        )

        print_section(
            "STEP 3 — PRODUCTION SOURCE RESOLUTION"
        )

        if snapshot_source:

            production_source = (
                snapshot_source
            )

            print_kv(
                "SNAPSHOT_SOURCE FROM ENGINE",
                snapshot_source,
            )

        else:

            production_source = (
                DEFAULT_SOURCE
            )

            print_kv(
                "SNAPSHOT_SOURCE FROM ENGINE",
                "[NOT STATICALLY RESOLVED]",
            )

            print_kv(
                "FALLBACK SOURCE",
                DEFAULT_SOURCE,
            )

        # ---------------------------------------------------------------------
        # Verify targets
        # ---------------------------------------------------------------------

        print_section(
            "STEP 4 — TARGET PRODUCTION WINDOW FORENSICS"
        )

        results = {}

        for symbol in TARGET_SYMBOLS:

            try:

                results[symbol] = verify_symbol(
                    conn,
                    symbol,
                    production_source,
                    source_info[
                        "calculate"
                    ],
                )

            except Exception as exc:

                print()
                print(
                    f"[ERROR] SYMBOL {symbol}"
                )

                print(
                    f"ERROR TYPE : {type(exc).__name__}"
                )

                print(
                    f"ERROR      : {exc}"
                )

                results[symbol] = {
                    "status": "UNRESOLVED",
                    "reason": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }

        return final_verdict(
            results
        )

    finally:

        conn.close()


if __name__ == "__main__":
    sys.exit(
        main()
    )