import ast
import os
import sqlite3
import sys
import math
import inspect
from collections import Counter


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

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

LOOKBACK = 120

EMA_PERIODS = [
    20,
    50,
]

RSI_PERIOD = 14

TOLERANCE_ABS = 1e-12
TOLERANCE_REL = 1e-10


# ============================================================
# OUTPUT HELPERS
# ============================================================

def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def print_kv(key, value):
    print(f"{key:<36}: {value}")


def safe_float(value):
    if value is None:
        return None

    try:
        value = float(value)
    except Exception:
        return None

    if not math.isfinite(value):
        return None

    return value


def abs_error(a, b):
    if a is None or b is None:
        return None

    return abs(a - b)


def rel_error(a, b):
    if a is None or b is None:
        return None

    denominator = abs(a)

    if denominator == 0:
        return abs(b)

    return abs(a - b) / denominator


def values_match(a, b):
    if a is None or b is None:
        return False

    ae = abs_error(a, b)
    re = rel_error(a, b)

    return (
        ae <= TOLERANCE_ABS
        or re <= TOLERANCE_REL
    )


# ============================================================
# ENGINE SOURCE
# ============================================================

def load_engine_source():
    if not os.path.isfile(ENGINE_PATH):
        raise FileNotFoundError(
            f"ENGINE NOT FOUND: {ENGINE_PATH}"
        )

    with open(
        ENGINE_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


def parse_engine(source):
    return ast.parse(
        source,
        filename=ENGINE_PATH
    )


def function_inventory(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result[node.name] = node

    return result


# ============================================================
# AST SOURCE EXTRACTION
# ============================================================

def source_segment(source, node):
    try:
        segment = ast.get_source_segment(
            source,
            node
        )

        if segment:
            return segment
    except Exception:
        pass

    return ""


def node_line_range(node):
    start = getattr(
        node,
        "lineno",
        None
    )

    end = getattr(
        node,
        "end_lineno",
        None
    )

    return start, end


def print_function_source(
    source,
    functions,
    name
):
    node = functions.get(name)

    if node is None:
        print(f"[NOT FOUND] {name}()")
        return

    start, end = node_line_range(node)

    print(
        f"[FOUND] {name}() "
        f"LINE {start}-{end}"
    )

    segment = source_segment(
        source,
        node
    )

    print()
    print(segment)


# ============================================================
# AST SEMANTIC FORENSICS
# ============================================================

def describe_constant(node):
    if isinstance(node, ast.Constant):
        return repr(node.value)

    return None


def describe_node(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Constant):
        return repr(node.value)

    if isinstance(node, ast.Attribute):
        base = describe_node(node.value)

        if base:
            return f"{base}.{node.attr}"

        return node.attr

    if isinstance(node, ast.BinOp):
        left = describe_node(node.left)
        right = describe_node(node.right)

        operators = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Pow: "**",
        }

        op = operators.get(
            type(node.op),
            "?"
        )

        return (
            f"({left} {op} {right})"
        )

    if isinstance(node, ast.UnaryOp):
        operand = describe_node(
            node.operand
        )

        if isinstance(
            node.op,
            ast.USub
        ):
            return f"-{operand}"

        if isinstance(
            node.op,
            ast.UAdd
        ):
            return f"+{operand}"

    if isinstance(node, ast.Call):
        function_name = describe_node(
            node.func
        )

        args = [
            describe_node(arg)
            for arg in node.args
        ]

        return (
            f"{function_name}("
            + ", ".join(args)
            + ")"
        )

    if isinstance(node, ast.Compare):
        left = describe_node(
            node.left
        )

        parts = [left]

        operators = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }

        for op, comparator in zip(
            node.ops,
            node.comparators
        ):
            parts.append(
                operators.get(
                    type(op),
                    "?"
                )
            )
            parts.append(
                describe_node(
                    comparator
                )
            )

        return " ".join(parts)

    return ast.dump(
        node,
        include_attributes=False
    )


def collect_assignments(
    function_node
):
    assignments = []

    for node in ast.walk(
        function_node
    ):
        if isinstance(
            node,
            ast.Assign
        ):
            for target in node.targets:
                if isinstance(
                    target,
                    ast.Name
                ):
                    assignments.append(
                        (
                            target.id,
                            node.lineno,
                            describe_node(
                                node.value
                            ),
                            node
                        )
                    )

        elif isinstance(
            node,
            ast.AnnAssign
        ):
            if isinstance(
                node.target,
                ast.Name
            ):
                assignments.append(
                    (
                        node.target.id,
                        node.lineno,
                        describe_node(
                            node.value
                        )
                        if node.value
                        else None,
                        node
                    )
                )

    return assignments


def collect_returns(
    function_node
):
    result = []

    for node in ast.walk(
        function_node
    ):
        if isinstance(
            node,
            ast.Return
        ):
            result.append(
                (
                    node.lineno,
                    describe_node(
                        node.value
                    )
                    if node.value
                    else None
                )
            )

    return result


def collect_calls(
    function_node
):
    result = []

    for node in ast.walk(
        function_node
    ):
        if isinstance(
            node,
            ast.Call
        ):
            function_name = describe_node(
                node.func
            )

            arguments = [
                describe_node(arg)
                for arg in node.args
            ]

            result.append(
                (
                    node.lineno,
                    function_name,
                    arguments,
                    node
                )
            )

    return result


# ============================================================
# LOOP / INDEX / SLICE FORENSICS
# ============================================================

def collect_loops(
    function_node
):
    loops = []

    for node in ast.walk(
        function_node
    ):
        if isinstance(
            node,
            ast.For
        ):
            target = describe_node(
                node.target
            )

            iterator = describe_node(
                node.iter
            )

            loops.append(
                (
                    node.lineno,
                    "FOR",
                    target,
                    iterator
                )
            )

        elif isinstance(
            node,
            ast.While
        ):
            loops.append(
                (
                    node.lineno,
                    "WHILE",
                    None,
                    describe_node(
                        node.test
                    )
                )
            )

    return loops


def collect_subscripts(
    function_node
):
    result = []

    for node in ast.walk(
        function_node
    ):
        if isinstance(
            node,
            ast.Subscript
        ):
            value = describe_node(
                node.value
            )

            slice_node = node.slice

            result.append(
                (
                    node.lineno,
                    value,
                    describe_node(
                        slice_node
                    )
                )
            )

    return result


# ============================================================
# ROUNDING / CONVERSION FORENSICS
# ============================================================

def collect_semantic_tokens(
    function_node
):
    tokens = {
        "round": [],
        "float": [],
        "int": [],
        "abs": [],
        "max": [],
        "min": [],
        "len": [],
        "sum": [],
        "None": [],
        "enumerate": [],
        "range": [],
    }

    for node in ast.walk(
        function_node
    ):
        if isinstance(
            node,
            ast.Call
        ):
            name = describe_node(
                node.func
            )

            if name in tokens:
                tokens[name].append(
                    node.lineno
                )

        elif isinstance(
            node,
            ast.Constant
        ):
            if node.value is None:
                tokens["None"].append(
                    node.lineno
                )

    return tokens


# ============================================================
# DATABASE
# ============================================================

def connect_db():
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(
            f"DATABASE NOT FOUND: {DB_PATH}"
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_table_count(conn):
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchone()

    return int(row[0])


def get_market_data_columns(conn):
    rows = conn.execute(
        """
        PRAGMA table_info(market_data)
        """
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


# ============================================================
# ACTUAL PRODUCTION WINDOW
# ============================================================

def get_production_record(
    conn,
    symbol
):
    row = conn.execute(
        """
        SELECT
            *
        FROM market_data
        WHERE
            symbol = ?
            AND timeframe = 'SNAPSHOT'
            AND source = 'COINMARKETCAP'
        ORDER BY id DESC
        LIMIT 1
        """,
        (symbol,)
    ).fetchone()

    return row


def get_production_window(
    conn,
    symbol,
    lookback
):
    rows = conn.execute(
        """
        SELECT
            *
        FROM market_data
        WHERE
            symbol = ?
            AND timeframe = 'SNAPSHOT'
            AND source = 'COINMARKETCAP'
            AND close IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            symbol,
            lookback
        )
    ).fetchall()

    rows = list(
        reversed(rows)
    )

    return rows


# ============================================================
# NUMERIC RECONSTRUCTION
# ============================================================

def ema_first_value(
    values,
    period
):
    if not values:
        return None

    if len(values) < period:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    ema_value = values[0]

    for value in values[1:]:
        ema_value = (
            alpha * value
            + (1.0 - alpha)
            * ema_value
        )

    return ema_value


def ema_sma_seed(
    values,
    period
):
    if len(values) < period:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    seed = sum(
        values[:period]
    ) / period

    ema_value = seed

    for value in values[period:]:
        ema_value = (
            alpha * value
            + (1.0 - alpha)
            * ema_value
        )

    return ema_value


def ema_recursive_start(
    values,
    period
):
    if not values:
        return None

    if len(values) < period:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    ema_value = values[0]

    for index in range(
        1,
        len(values)
    ):
        ema_value = (
            alpha * values[index]
            + (1.0 - alpha)
            * ema_value
        )

    return ema_value


def ema_series(
    values,
    period
):
    if not values:
        return []

    alpha = 2.0 / (
        period + 1.0
    )

    result = []

    ema_value = values[0]

    result.append(
        ema_value
    )

    for value in values[1:]:
        ema_value = (
            alpha * value
            + (1.0 - alpha)
            * ema_value
        )

        result.append(
            ema_value
        )

    return result


# ============================================================
# RSI RECONSTRUCTIONS
# ============================================================

def rsi_wilder(
    values,
    period
):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for index in range(
        1,
        len(values)
    ):
        delta = (
            values[index]
            - values[index - 1]
        )

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)

        elif delta < 0:
            gains.append(0.0)
            losses.append(-delta)

        else:
            gains.append(0.0)
            losses.append(0.0)

    if len(gains) < period:
        return None

    average_gain = (
        sum(gains[:period])
        / period
    )

    average_loss = (
        sum(losses[:period])
        / period
    )

    for index in range(
        period,
        len(gains)
    ):
        average_gain = (
            (
                average_gain
                * (period - 1)
            )
            + gains[index]
        ) / period

        average_loss = (
            (
                average_loss
                * (period - 1)
            )
            + losses[index]
        ) / period

    if average_loss == 0:
        return 100.0

    rs = (
        average_gain
        / average_loss
    )

    return 100.0 - (
        100.0
        / (1.0 + rs)
    )


def rsi_ema_smoothing(
    values,
    period
):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for index in range(
        1,
        len(values)
    ):
        delta = (
            values[index]
            - values[index - 1]
        )

        gains.append(
            max(delta, 0.0)
        )

        losses.append(
            max(-delta, 0.0)
        )

    if len(gains) < period:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    average_gain = (
        sum(gains[:period])
        / period
    )

    average_loss = (
        sum(losses[:period])
        / period
    )

    for index in range(
        period,
        len(gains)
    ):
        average_gain = (
            alpha * gains[index]
            + (1.0 - alpha)
            * average_gain
        )

        average_loss = (
            alpha * losses[index]
            + (1.0 - alpha)
            * average_loss
        )

    if average_loss == 0:
        return 100.0

    rs = (
        average_gain
        / average_loss
    )

    return 100.0 - (
        100.0
        / (1.0 + rs)
    )


def rsi_simple_rolling(
    values,
    period
):
    if len(values) <= period:
        return None

    deltas = []

    for index in range(
        1,
        len(values)
    ):
        deltas.append(
            values[index]
            - values[index - 1]
        )

    if len(deltas) < period:
        return None

    window = deltas[-period:]

    gains = [
        max(x, 0.0)
        for x in window
    ]

    losses = [
        max(-x, 0.0)
        for x in window
    ]

    average_gain = (
        sum(gains)
        / period
    )

    average_loss = (
        sum(losses)
        / period
    )

    if average_loss == 0:
        return 100.0

    rs = (
        average_gain
        / average_loss
    )

    return 100.0 - (
        100.0
        / (1.0 + rs)
    )


# ============================================================
# FUNCTION SEMANTICS FORENSICS
# ============================================================

def print_function_semantics(
    source,
    functions,
    function_name
):
    print_section(
        f"FUNCTION SEMANTICS : {function_name}()"
    )

    node = functions.get(
        function_name
    )

    if node is None:
        print(
            f"[NOT FOUND] {function_name}()"
        )
        return

    start, end = node_line_range(
        node
    )

    print_kv(
        "LINE RANGE",
        f"{start}-{end}"
    )

    assignments = collect_assignments(
        node
    )

    print()
    print("ASSIGNMENTS")
    print("-" * 60)

    if not assignments:
        print("[NONE]")

    for (
        name,
        line,
        expression,
        _node
    ) in assignments:

        print(
            f"LINE {line:<5} "
            f"{name} = {expression}"
        )

    calls = collect_calls(
        node
    )

    print()
    print("CALLS")
    print("-" * 60)

    if not calls:
        print("[NONE]")

    for (
        line,
        function_name_called,
        arguments,
        _node
    ) in calls:

        print(
            f"LINE {line:<5} "
            f"{function_name_called}("
            + ", ".join(arguments)
            + ")"
        )

    loops = collect_loops(
        node
    )

    print()
    print("LOOPS")
    print("-" * 60)

    if not loops:
        print("[NONE]")

    for (
        line,
        kind,
        target,
        iterator
    ) in loops:

        if target is None:
            print(
                f"LINE {line:<5} "
                f"{kind} {iterator}"
            )
        else:
            print(
                f"LINE {line:<5} "
                f"{kind} "
                f"{target} IN {iterator}"
            )

    subscripts = collect_subscripts(
        node
    )

    print()
    print("INDEX / SLICE ACCESS")
    print("-" * 60)

    if not subscripts:
        print("[NONE]")

    for (
        line,
        value,
        slice_expression
    ) in subscripts:

        print(
            f"LINE {line:<5} "
            f"{value}[{slice_expression}]"
        )

    tokens = collect_semantic_tokens(
        node
    )

    print()
    print("ROUNDING / TYPE / NUMERIC OPERATIONS")
    print("-" * 60)

    for key, lines in tokens.items():
        if lines:
            print(
                f"{key:<12}: "
                + ", ".join(
                    str(x)
                    for x in lines
                )
            )


# ============================================================
# ACTUAL STORED INDICATOR VALUES
# ============================================================

def get_stored_indicators(
    production_row
):
    return {
        "ema20": safe_float(
            production_row["ema20"]
        ),
        "ema50": safe_float(
            production_row["ema50"]
        ),
        "rsi14": safe_float(
            production_row["rsi14"]
        ),
    }


# ============================================================
# PRODUCTION WINDOW FORENSICS
# ============================================================

def extract_closes(
    rows
):
    result = []

    for row in rows:
        value = safe_float(
            row["close"]
        )

        if value is None:
            continue

        result.append(
            value
        )

    return result


def print_window_identity(
    rows,
    closes
):
    print_section(
        "ACTUAL PRODUCTION WINDOW"
    )

    print_kv(
        "ROWS RETURNED",
        len(rows)
    )

    if not rows:
        print("[EMPTY WINDOW]")
        return

    first = rows[0]
    last = rows[-1]

    print_kv(
        "FIRST ID",
        first["id"]
    )

    print_kv(
        "LAST ID",
        last["id"]
    )

    print_kv(
        "FIRST TIMESTAMP",
        first["timestamp"]
    )

    print_kv(
        "LAST TIMESTAMP",
        last["timestamp"]
    )

    print_kv(
        "FIRST SOURCE TIMESTAMP",
        first["source_timestamp"]
    )

    print_kv(
        "LAST SOURCE TIMESTAMP",
        last["source_timestamp"]
    )

    print_kv(
        "CLOSE COUNT",
        len(closes)
    )

    if closes:
        print_kv(
            "CLOSE FIRST",
            closes[0]
        )

        print_kv(
            "CLOSE LAST",
            closes[-1]
        )


# ============================================================
# EXACT SEMANTICS COMPARISON
# ============================================================

def compare_indicator(
    name,
    stored,
    candidates
):
    print()
    print(
        f"INDICATOR : {name}"
    )

    print(
        f"STORED VALUE : {stored}"
    )

    matches = []

    for candidate_name, value in candidates.items():

        ae = abs_error(
            stored,
            value
        )

        re = rel_error(
            stored,
            value
        )

        status = (
            "MATCH"
            if values_match(
                stored,
                value
            )
            else "MISMATCH"
        )

        if status == "MATCH":
            matches.append(
                candidate_name
            )

        print(
            f"{candidate_name:<24}"
            f"VALUE={value} "
            f"ABS_ERR={ae} "
            f"REL_ERR={re} "
            f"STATUS={status}"
        )

    return matches


# ============================================================
# EXACT IMPLEMENTATION HYPOTHESES
# ============================================================

def test_ema_semantics(
    closes,
    period
):
    return {
        "FIRST_VALUE":
            ema_first_value(
                closes,
                period
            ),

        "SMA_SEED":
            ema_sma_seed(
                closes,
                period
            ),

        "RECURSIVE_FIRST":
            ema_recursive_start(
                closes,
                period
            ),

        "EMA_SERIES_LAST":
            (
                ema_series(
                    closes,
                    period
                )[-1]
                if closes
                else None
            ),
    }


def test_rsi_semantics(
    closes,
    period
):
    return {
        "WILDER":
            rsi_wilder(
                closes,
                period
            ),

        "EMA_SMOOTHING":
            rsi_ema_smoothing(
                closes,
                period
            ),

        "SIMPLE_ROLLING":
            rsi_simple_rolling(
                closes,
                period
            ),
    }


# ============================================================
# SOURCE CODE SEMANTIC REPORT
# ============================================================

def print_target_function_sources(
    source,
    functions
):
    print_header(
        "EXACT PRODUCTION FUNCTION SOURCE FORENSICS"
    )

    for name in [
        "ema",
        "ema_series",
        "rsi",
        "calculate_analysis",
    ]:

        print_function_source(
            source,
            functions,
            name
        )


# ============================================================
# SYMBOL FORENSIC
# ============================================================

def verify_symbol(
    conn,
    symbol
):
    print_header(
        f"SYMBOL : {symbol}"
    )

    production = get_production_record(
        conn,
        symbol
    )

    if production is None:
        print(
            "[UNRESOLVED] "
            "Production record not found"
        )

        return {
            "status":
                "UNRESOLVED"
        }

    rows = get_production_window(
        conn,
        symbol,
        LOOKBACK
    )

    closes = extract_closes(
        rows
    )

    print_section(
        "PRODUCTION TARGET"
    )

    print_kv(
        "ID",
        production["id"]
    )

    print_kv(
        "TIMESTAMP",
        production["timestamp"]
    )

    print_kv(
        "SOURCE_TIMESTAMP",
        production["source_timestamp"]
    )

    print_kv(
        "CLOSE",
        production["close"]
    )

    print_kv(
        "EMA20",
        production["ema20"]
    )

    print_kv(
        "EMA50",
        production["ema50"]
    )

    print_kv(
        "RSI14",
        production["rsi14"]
    )

    print_kv(
        "ENGINE_VERSION",
        production["engine_version"]
    )

    print_window_identity(
        rows,
        closes
    )

    print_section(
        "CALCULATION INPUT 'closes'"
    )

    print_kv(
        "ROWS RETURNED",
        len(rows)
    )

    print_kv(
        "CLOSES COUNT",
        len(closes)
    )

    print_kv(
        "ROWS == CLOSES",
        len(rows) == len(closes)
    )

    if len(rows) != LOOKBACK:
        print(
            "[WARNING] "
            "Production window length differs "
            "from configured LOOKBACK"
        )

    if not closes:
        return {
            "status":
                "UNRESOLVED"
        }

    print_section(
        "EXACT EMA SEMANTICS"
    )

    stored = get_stored_indicators(
        production
    )

    ema20_candidates = test_ema_semantics(
        closes,
        20
    )

    ema50_candidates = test_ema_semantics(
        closes,
        50
    )

    ema20_matches = compare_indicator(
        "EMA20",
        stored["ema20"],
        ema20_candidates
    )

    ema50_matches = compare_indicator(
        "EMA50",
        stored["ema50"],
        ema50_candidates
    )

    print_section(
        "EXACT RSI SEMANTICS"
    )

    rsi_candidates = test_rsi_semantics(
        closes,
        14
    )

    rsi_matches = compare_indicator(
        "RSI14",
        stored["rsi14"],
        rsi_candidates
    )

    print_section(
        "START INDEX / WINDOW LENGTH FORENSICS"
    )

    start_candidates = []

    for start in range(
        0,
        min(
            10,
            len(closes)
        )
    ):
        candidate = closes[start:]

        if len(candidate) < 50:
            continue

        ema20 = ema_sma_seed(
            candidate,
            20
        )

        ema50 = ema_sma_seed(
            candidate,
            50
        )

        rsi14 = rsi_wilder(
            candidate,
            14
        )

        score = 0

        if values_match(
            stored["ema20"],
            ema20
        ):
            score += 1

        if values_match(
            stored["ema50"],
            ema50
        ):
            score += 1

        if values_match(
            stored["rsi14"],
            rsi14
        ):
            score += 1

        start_candidates.append(
            (
                start,
                len(candidate),
                ema20,
                ema50,
                rsi14,
                score
            )
        )

    for (
        start,
        length,
        ema20,
        ema50,
        rsi14,
        score
    ) in start_candidates:

        print(
            f"START={start:<3} "
            f"LENGTH={length:<3} "
            f"EMA20={ema20} "
            f"EMA50={ema50} "
            f"RSI14={rsi14} "
            f"MATCH_SCORE={score}/3"
        )

    max_score = max(
        (
            x[-1]
            for x in start_candidates
        ),
        default=0
    )

    if (
        ema20_matches
        or ema50_matches
        or rsi_matches
    ):
        status = (
            "PARTIAL_FUNCTION_SEMANTICS_MATCH"
        )

    elif max_score > 0:
        status = (
            "PARTIAL_START_INDEX_MATCH"
        )

    else:
        status = (
            "EXACT_FUNCTION_SEMANTICS_NOT_IDENTIFIED"
        )

    print_section(
        "SYMBOL SEMANTICS VERDICT"
    )

    print_kv(
        "EMA20 MATCHES",
        ema20_matches
    )

    print_kv(
        "EMA50 MATCHES",
        ema50_matches
    )

    print_kv(
        "RSI14 MATCHES",
        rsi_matches
    )

    print_kv(
        "BEST START INDEX SCORE",
        f"{max_score}/3"
    )

    print_kv(
        "STATUS",
        status
    )

    return {
        "status": status,
        "ema20_matches": ema20_matches,
        "ema50_matches": ema50_matches,
        "rsi_matches": rsi_matches,
        "best_start_score": max_score,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print_header(
        "ARUNDA INDICATOR POST REPAIR EXACT PRODUCTION FUNCTION "
        "SEED SMOOTHING START ROUNDING FORENSIC AUDIT v0.1"
    )

    print_kv(
        "MODE",
        "READ ONLY"
    )

    print_kv(
        "DATABASE WRITE",
        "NONE"
    )

    print_kv(
        "ENGINE WRITE",
        "NONE"
    )

    print_kv(
        "FORMULA WRITE",
        "NONE"
    )

    print_kv(
        "PRODUCTION RECALCULATION",
        "NONE"
    )

    print_kv(
        "PURPOSE",
        "TRACE EXACT PRODUCTION FUNCTION IMPLEMENTATION "
        "INCLUDING SEED, SMOOTHING, START INDEX AND ROUNDING"
    )

    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    print_header(
        "STEP 1 — ENGINE SOURCE RESOLUTION"
    )

    print_kv(
        "ENGINE PATH",
        ENGINE_PATH
    )

    print_kv(
        "ENGINE FOUND",
        os.path.isfile(
            ENGINE_PATH
        )
    )

    source = load_engine_source()

    print_kv(
        "SOURCE SIZE",
        f"{len(source)} characters"
    )

    print_kv(
        "SOURCE LINES",
        len(
            source.splitlines()
        )
    )

    try:
        tree = parse_engine(
            source
        )

        print_kv(
            "AST STATUS",
            "SUCCESS"
        )

    except SyntaxError as exc:
        print_kv(
            "AST STATUS",
            "FAILED"
        )

        print(
            exc
        )

        return 1

    functions = function_inventory(
        tree
    )

    print()

    for name in [
        "ema",
        "ema_series",
        "rsi",
        "calculate_analysis",
        "main",
    ]:

        node = functions.get(
            name
        )

        if node is None:
            print(
                f"[NOT FOUND] {name}()"
            )

        else:
            start, end = node_line_range(
                node
            )

            print(
                f"[FOUND] "
                f"{name}() "
                f"LINE {start}-{end}"
            )

    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    print_header(
        "STEP 2 — EXACT FUNCTION SEMANTIC INVENTORY"
    )

    print_target_function_sources(
        source,
        functions
    )

    # --------------------------------------------------------
    # STEP 3
    # --------------------------------------------------------

    print_header(
        "STEP 3 — DATABASE RESOLUTION"
    )

    print_kv(
        "DATABASE PATH",
        DB_PATH
    )

    print_kv(
        "DATABASE FOUND",
        os.path.isfile(
            DB_PATH
        )
    )

    conn = connect_db()

    try:

        table_count = get_table_count(
            conn
        )

        print_kv(
            "TABLE COUNT",
            table_count
        )

        columns = get_market_data_columns(
            conn
        )

        print()
        print(
            "MARKET_DATA COLUMNS"
        )

        print("-" * 60)

        for index, column in enumerate(
            columns
        ):
            print(
                f"{index:>3} : {column}"
            )

        # ----------------------------------------------------
        # STEP 4
        # ----------------------------------------------------

        print_header(
            "STEP 4 — TARGET SYMBOL SEMANTICS RECONSTRUCTION"
        )

        results = {}

        for symbol in TARGET_SYMBOLS:

            results[symbol] = verify_symbol(
                conn,
                symbol
            )

        # ----------------------------------------------------
        # STEP 5
        # ----------------------------------------------------

        print_header(
            "STEP 5 — FINAL EXACT FUNCTION SEMANTICS SUMMARY"
        )

        print_kv(
            "TARGETS CHECKED",
            len(TARGET_SYMBOLS)
        )

        complete = 0
        partial = 0
        unresolved = 0

        for symbol in TARGET_SYMBOLS:

            result = results.get(
                symbol,
                {}
            )

            status = result.get(
                "status"
            )

            if status == (
                "EXACT_FUNCTION_SEMANTICS_NOT_IDENTIFIED"
            ):
                unresolved += 1

            elif status in (
                "PARTIAL_FUNCTION_SEMANTICS_MATCH",
                "PARTIAL_START_INDEX_MATCH",
            ):
                partial += 1

            else:
                complete += 1

        print()
        print(
            f"COMPLETE / MATCH TARGETS : "
            f"{complete}"
        )

        print(
            f"PARTIAL TARGETS          : "
            f"{partial}"
        )

        print(
            f"UNRESOLVED TARGETS       : "
            f"{unresolved}"
        )

        print()
        print(
            "TARGET MATRIX"
        )

        print("-" * 60)

        for symbol in TARGET_SYMBOLS:

            status = results[
                symbol
            ].get(
                "status",
                "UNRESOLVED"
            )

            print(
                f"  [{status:<42}] : {symbol}"
            )

        # ----------------------------------------------------
        # STEP 6
        # ----------------------------------------------------

        print_header(
            "FORENSIC CONCLUSION"
        )

        if unresolved == len(
            TARGET_SYMBOLS
        ):

            print(
                "STATUS : "
                "EXACT_PRODUCTION_FUNCTION_SEMANTICS_NOT_IDENTIFIED"
            )

            print(
                "REASON : "
                "NONE OF THE TESTED INITIALIZATION / "
                "SMOOTHING / START-INDEX SEMANTICS "
                "REPRODUCED THE STORED INDICATORS"
            )

            print(
                "NEXT FRONTIER : "
                "TRACE INTERNAL PRODUCTION FUNCTION "
                "IMPLEMENTATION LINE-BY-LINE INCLUDING "
                "ALL BRANCHES AND RETURN PATHS"
            )

        elif partial > 0:

            print(
                "STATUS : "
                "PARTIAL_PRODUCTION_FUNCTION_SEMANTICS_IDENTIFIED"
            )

            print(
                "REASON : "
                "ONE OR MORE INDICATORS OR START-INDEX "
                "PATHS MATCHED BUT THE COMPLETE INDICATOR "
                "SET REMAINS UNRESOLVED"
            )

            print(
                "NEXT FRONTIER : "
                "ISOLATE THE REMAINING NON-MATCHING "
                "INDICATOR IMPLEMENTATION"
            )

        else:

            print(
                "STATUS : "
                "PRODUCTION_FUNCTION_SEMANTICS_MATCHED"
            )

            print(
                "REASON : "
                "THE STORED INDICATORS ARE REPRODUCIBLE "
                "FROM IDENTIFIED PRODUCTION SEMANTICS"
            )

            print(
                "NEXT FRONTIER : "
                "TRACE PRODUCTION WRITE PATH AND "
                "FORMULA PERSISTENCE"
            )

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS : NONE"
        )

        print(
            "PRODUCTION RECALCULATION : NONE"
        )

        print(
            "AUDIT COMPLETE"
        )

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )