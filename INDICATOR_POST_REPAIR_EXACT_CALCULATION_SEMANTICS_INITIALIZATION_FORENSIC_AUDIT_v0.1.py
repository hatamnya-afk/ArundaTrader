# -*- coding: utf-8 -*-

"""
ARUNDA INDICATOR POST REPAIR EXACT CALCULATION SEMANTICS INITIALIZATION FORENSIC AUDIT v0.1

READ ONLY FORENSIC AUDIT

PURPOSE:
    Trace the exact mathematical / initialization semantics used by the
    production indicator functions and compare them against independent
    reconstructions from the exact production closes window.

NO DATABASE WRITES
NO ENGINE WRITES
NO FORMULA WRITES
NO PRODUCTION RECALCULATION

TARGETS:
    BTC
    ETH
    SOL
    XRP

FOCUS:
    EMA20
    EMA50
    RSI14
    MACD when discoverable

THIS SCRIPT DOES NOT MODIFY ANY PRODUCTION DATA.
"""

import ast
import inspect
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone


# ======================================================================
# CONFIGURATION
# ======================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

ENGINE_PATH = os.path.join(
    BASE_DIR,
    "market_data_engine.py",
)

DB_PATH = os.path.join(
    BASE_DIR,
    "arunda.db",
)

LOOKBACK = 120

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

SOURCE = "COINMARKETCAP"
TIMEFRAME = "SNAPSHOT"


# ======================================================================
# OUTPUT HELPERS
# ======================================================================

def print_line(char="=", width=100):
    print(char * width)


def print_header(title):
    print_line("=")
    print(title)
    print_line("=")


def print_section(title):
    print()
    print_line("=")
    print(title)
    print_line("=")


def print_subsection(title):
    print()
    print_line("-")
    print(title)
    print_line("-")


def fmt(value):
    if value is None:
        return "None"

    if isinstance(value, float):
        return f"{value:.15g}"

    return str(value)


def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)

    except Exception:
        return None


# ======================================================================
# ENGINE SOURCE
# ======================================================================

def load_engine_source():
    if not os.path.exists(ENGINE_PATH):
        return None

    with open(
        ENGINE_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def parse_engine(source):
    try:
        return ast.parse(source)

    except Exception as exc:
        print(f"[AST ERROR] {exc}")
        return None


def function_inventory(tree):
    result = {}

    if tree is None:
        return result

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result[node.name] = node

    return result


def source_segment_lines(source, node):
    lines = source.splitlines()

    start = getattr(
        node,
        "lineno",
        None,
    )

    end = getattr(
        node,
        "end_lineno",
        None,
    )

    if start is None:
        return []

    if end is None:
        end = start

    return lines[start - 1:end]


# ======================================================================
# AST CALL / FORMULA FORENSICS
# ======================================================================

def find_calls(function_node, target_name):
    calls = []

    if function_node is None:
        return calls

    for node in ast.walk(function_node):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        func = node.func

        if isinstance(
            func,
            ast.Name,
        ):
            name = func.id

        elif isinstance(
            func,
            ast.Attribute,
        ):
            name = func.attr

        else:
            continue

        if name != target_name:
            continue

        calls.append(node)

    return calls


def ast_expr(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse unavailable>"


def inspect_function_semantics(source, functions, name):
    node = functions.get(name)

    if node is None:
        print(f"[NOT FOUND] {name}()")
        return

    print_subsection(
        f"{name}() SOURCE / SEMANTICS"
    )

    start = node.lineno
    end = node.end_lineno

    print(
        f"LINE RANGE : {start}-{end}"
    )

    lines = source.splitlines()

    for number in range(
        start,
        end + 1,
    ):
        text = lines[number - 1]

        print(
            f"{number:5d}: {text}"
        )


def inspect_indicator_calls(functions):
    calculate = functions.get(
        "calculate_analysis"
    )

    if calculate is None:
        return

    print_subsection(
        "INDICATOR CALL SEMANTICS"
    )

    targets = [
        "ema",
        "rsi",
        "macd",
        "ema_series",
    ]

    for target in targets:

        calls = find_calls(
            calculate,
            target,
        )

        print(
            f"{target}() CALLS : {len(calls)}"
        )

        for call in calls:

            args = [
                ast_expr(arg)
                for arg in call.args
            ]

            print(
                f"  LINE {call.lineno} "
                f"ARGS={args}"
            )


# ======================================================================
# DATABASE
# ======================================================================

def connect_database():
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_market_data_columns(conn):

    cursor = conn.execute(
        "PRAGMA table_info(market_data)"
    )

    return [
        row["name"]
        for row in cursor.fetchall()
    ]


def resolve_production_rows(
    conn,
    symbol,
):
    """
    Resolve the exact production window using
    the same source/timeframe semantics identified
    in get_snapshot_history().
    """

    query = """
        SELECT
            id,
            timestamp,
            symbol,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            ema20,
            ema50,
            rsi14,
            macd,
            macd_signal,
            macd_hist,
            atr14,
            adx14,
            bb_middle,
            bb_upper,
            bb_lower,
            bb_width,
            volume_sma20,
            volume_ratio,
            volatility,
            technical_score,
            source,
            source_timestamp,
            price_change_1h,
            price_change_24h,
            market_cap,
            volume_24h,
            source_latency_ms,
            engine_version
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND close IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
    """

    return conn.execute(
        query,
        (
            symbol,
            SOURCE,
            TIMEFRAME,
            LOOKBACK,
        ),
    ).fetchall()


# ======================================================================
# EXACT STORED INDICATORS
# ======================================================================

def get_target_row(rows):

    if not rows:
        return None

    return rows[-1]


# ======================================================================
# INDEPENDENT EMA RECONSTRUCTIONS
# ======================================================================

def ema_seed_first_value(
    values,
    period,
):
    """
    EMA initialization variant:
        seed = first observation
        EMA_t = alpha*x_t + (1-alpha)*EMA_(t-1)
    """

    values = [
        safe_float(v)
        for v in values
        if safe_float(v) is not None
    ]

    if not values:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    result = values[0]

    for value in values[1:]:
        result = (
            alpha * value
            + (1.0 - alpha) * result
        )

    return result


def ema_seed_sma(
    values,
    period,
):
    """
    EMA initialization variant:
        seed = SMA(first period)
        then recursive EMA
    """

    values = [
        safe_float(v)
        for v in values
        if safe_float(v) is not None
    ]

    if len(values) < period:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    result = sum(
        values[:period]
    ) / period

    for value in values[period:]:
        result = (
            alpha * value
            + (1.0 - alpha) * result
        )

    return result


def ema_pandas_style_recursive(
    values,
    period,
):
    """
    Recursive EMA beginning at first value.
    Explicitly separated so that initialization
    semantics can be compared.
    """

    values = [
        safe_float(v)
        for v in values
        if safe_float(v) is not None
    ]

    if not values:
        return None

    alpha = 2.0 / (
        period + 1.0
    )

    ema_value = values[0]

    for value in values[1:]:
        ema_value = (
            ema_value
            + alpha
            * (
                value
                - ema_value
            )
        )

    return ema_value


# ======================================================================
# RSI RECONSTRUCTIONS
# ======================================================================

def rsi_wilder(
    values,
    period=14,
):
    """
    Standard Wilder RSI.

    Seed:
        arithmetic mean of first period gains/losses

    Smoothing:
        Wilder's alpha = 1 / period
    """

    values = [
        safe_float(v)
        for v in values
        if safe_float(v) is not None
    ]

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(values),
    ):
        delta = (
            values[i]
            - values[i - 1]
        )

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)

        else:
            gains.append(0.0)
            losses.append(-delta)

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains),
    ):

        avg_gain = (
            (
                avg_gain
                * (period - 1)
            )
            + gains[i]
        ) / period

        avg_loss = (
            (
                avg_loss
                * (period - 1)
            )
            + losses[i]
        ) / period

    if avg_loss == 0:
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


def rsi_ema_smoothing(
    values,
    period=14,
):
    """
    RSI variant using EMA smoothing
    with alpha = 2/(period+1).
    """

    values = [
        safe_float(v)
        for v in values
        if safe_float(v) is not None
    ]

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(values),
    ):

        delta = (
            values[i]
            - values[i - 1]
        )

        gains.append(
            max(delta, 0.0)
        )

        losses.append(
            max(-delta, 0.0)
        )

    alpha = 2.0 / (
        period + 1.0
    )

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains),
    ):

        avg_gain = (
            alpha * gains[i]
            + (1.0 - alpha)
            * avg_gain
        )

        avg_loss = (
            alpha * losses[i]
            + (1.0 - alpha)
            * avg_loss
        )

    if avg_loss == 0:
        return 100.0

    rs = (
        avg_gain
        / avg_loss
    )

    return (
        100.0
        - 100.0
        / (1.0 + rs)
    )


def rsi_simple_rolling(
    values,
    period=14,
):
    """
    Simple rolling RSI using the
    most recent period changes.
    """

    values = [
        safe_float(v)
        for v in values
        if safe_float(v) is not None
    ]

    if len(values) <= period:
        return None

    changes = []

    for i in range(
        len(values) - period,
        len(values),
    ):

        delta = (
            values[i]
            - values[i - 1]
        )

        changes.append(delta)

    gains = [
        max(x, 0.0)
        for x in changes
    ]

    losses = [
        max(-x, 0.0)
        for x in changes
    ]

    avg_gain = (
        sum(gains)
        / period
    )

    avg_loss = (
        sum(losses)
        / period
    )

    if avg_loss == 0:
        return 100.0

    rs = (
        avg_gain
        / avg_loss
    )

    return (
        100.0
        - 100.0
        / (1.0 + rs)
    )


# ======================================================================
# TRACE RSI SOURCE CODE STRUCTURE
# ======================================================================

def inspect_rsi_ast(functions):

    node = functions.get(
        "rsi"
    )

    print_subsection(
        "RSI FUNCTION AST SEMANTICS"
    )

    if node is None:
        print(
            "[NOT FOUND] rsi()"
        )
        return

    lines = source_segment_lines(
        ENGINE_SOURCE,
        node,
    )

    for number, text in enumerate(
        lines,
        start=node.lineno,
    ):
        print(
            f"{number:5d}: {text}"
        )

    print()

    print(
        "RSI ASSIGNMENTS / CONSTANTS"
    )

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Assign,
        ):

            target_text = [
                ast_expr(t)
                for t in child.targets
            ]

            value_text = ast_expr(
                child.value
            )

            print(
                f"LINE {child.lineno}: "
                f"{target_text} = {value_text}"
            )

        elif isinstance(
            child,
            ast.AugAssign,
        ):

            print(
                f"LINE {child.lineno}: "
                f"{ast_expr(child.target)} "
                f"{type(child.op).__name__}= "
                f"{ast_expr(child.value)}"
            )


# ======================================================================
# ERROR COMPARISON
# ======================================================================

def compare(
    stored,
    rebuilt,
    tolerance_abs=1e-10,
):
    if (
        stored is None
        or rebuilt is None
    ):
        return {
            "status": "UNRESOLVED",
            "abs_error": None,
            "rel_error": None,
        }

    abs_error = abs(
        stored - rebuilt
    )

    denominator = max(
        abs(stored),
        1e-15,
    )

    rel_error = (
        abs_error
        / denominator
    )

    if abs_error <= tolerance_abs:
        status = "MATCH"

    else:
        status = "MISMATCH"

    return {
        "status": status,
        "abs_error": abs_error,
        "rel_error": rel_error,
    }


# ======================================================================
# ONE SYMBOL FORENSICS
# ======================================================================

def verify_symbol(
    conn,
    symbol,
):

    print_section(
        f"SYMBOL : {symbol}"
    )

    rows = resolve_production_rows(
        conn,
        symbol,
    )

    print_subsection(
        "ACTUAL PRODUCTION WINDOW"
    )

    print(
        f"ROWS RETURNED : {len(rows)}"
    )

    if len(rows) != LOOKBACK:
        print(
            "[WARNING] "
            "Production window length differs "
            f"from LOOKBACK={LOOKBACK}"
        )

    if not rows:
        print(
            "[UNRESOLVED] "
            "No production rows"
        )

        return {
            "symbol": symbol,
            "status": "UNRESOLVED",
        }

    closes = [
        safe_float(
            row["close"]
        )
        for row in rows
    ]

    closes = [
        x
        for x in closes
        if x is not None
    ]

    target = rows[-1]

    stored_ema20 = safe_float(
        target["ema20"]
    )

    stored_ema50 = safe_float(
        target["ema50"]
    )

    stored_rsi14 = safe_float(
        target["rsi14"]
    )

    print(
        f"FIRST ID       : {rows[0]['id']}"
    )

    print(
        f"LAST ID        : {rows[-1]['id']}"
    )

    print(
        f"FIRST TIMESTAMP: {rows[0]['timestamp']}"
    )

    print(
        f"LAST TIMESTAMP : {rows[-1]['timestamp']}"
    )

    print(
        f"CLOSES COUNT   : {len(closes)}"
    )

    print(
        f"CLOSE FIRST    : {fmt(closes[0])}"
    )

    print(
        f"CLOSE LAST     : {fmt(closes[-1])}"
    )

    # --------------------------------------------------------------
    # EMA
    # --------------------------------------------------------------

    print_subsection(
        "EMA INITIALIZATION COMPARISON"
    )

    ema20_variants = {
        "FIRST_VALUE": ema_seed_first_value(
            closes,
            20,
        ),
        "SMA_SEED": ema_seed_sma(
            closes,
            20,
        ),
        "RECURSIVE_FIRST": ema_pandas_style_recursive(
            closes,
            20,
        ),
    }

    ema50_variants = {
        "FIRST_VALUE": ema_seed_first_value(
            closes,
            50,
        ),
        "SMA_SEED": ema_seed_sma(
            closes,
            50,
        ),
        "RECURSIVE_FIRST": ema_pandas_style_recursive(
            closes,
            50,
        ),
    }

    print(
        f"STORED EMA20 : {fmt(stored_ema20)}"
    )

    best_ema20 = None

    for name, value in ema20_variants.items():

        result = compare(
            stored_ema20,
            value,
        )

        print(
            f"{name:18s} "
            f"VALUE={fmt(value)} "
            f"ABS_ERR={fmt(result['abs_error'])} "
            f"REL_ERR={fmt(result['rel_error'])} "
            f"STATUS={result['status']}"
        )

        if (
            value is not None
            and (
                best_ema20 is None
                or result["abs_error"]
                < best_ema20[1]
            )
        ):
            best_ema20 = (
                name,
                result["abs_error"],
            )

    print()

    print(
        f"STORED EMA50 : {fmt(stored_ema50)}"
    )

    best_ema50 = None

    for name, value in ema50_variants.items():

        result = compare(
            stored_ema50,
            value,
        )

        print(
            f"{name:18s} "
            f"VALUE={fmt(value)} "
            f"ABS_ERR={fmt(result['abs_error'])} "
            f"REL_ERR={fmt(result['rel_error'])} "
            f"STATUS={result['status']}"
        )

        if (
            value is not None
            and (
                best_ema50 is None
                or result["abs_error"]
                < best_ema50[1]
            )
        ):
            best_ema50 = (
                name,
                result["abs_error"],
            )

    # --------------------------------------------------------------
    # RSI
    # --------------------------------------------------------------

    print_subsection(
        "RSI INITIALIZATION / SMOOTHING COMPARISON"
    )

    rsi_variants = {
        "WILDER": rsi_wilder(
            closes,
            14,
        ),
        "EMA_SMOOTHING": rsi_ema_smoothing(
            closes,
            14,
        ),
        "SIMPLE_ROLLING": rsi_simple_rolling(
            closes,
            14,
        ),
    }

    print(
        f"STORED RSI14 : {fmt(stored_rsi14)}"
    )

    best_rsi = None

    for name, value in rsi_variants.items():

        result = compare(
            stored_rsi14,
            value,
        )

        print(
            f"{name:18s} "
            f"VALUE={fmt(value)} "
            f"ABS_ERR={fmt(result['abs_error'])} "
            f"REL_ERR={fmt(result['rel_error'])} "
            f"STATUS={result['status']}"
        )

        if (
            value is not None
            and (
                best_rsi is None
                or result["abs_error"]
                < best_rsi[1]
            )
        ):
            best_rsi = (
                name,
                result["abs_error"],
            )

    # --------------------------------------------------------------
    # DELTA DISTRIBUTION
    # --------------------------------------------------------------

    print_subsection(
        "PRICE DELTA / DIRECTION FORENSICS"
    )

    deltas = []

    positive = 0
    negative = 0
    zero = 0

    for i in range(
        1,
        len(closes),
    ):

        delta = (
            closes[i]
            - closes[i - 1]
        )

        deltas.append(delta)

        if delta > 0:
            positive += 1

        elif delta < 0:
            negative += 1

        else:
            zero += 1

    print(
        f"DELTA COUNT       : {len(deltas)}"
    )

    print(
        f"POSITIVE DELTAS   : {positive}"
    )

    print(
        f"NEGATIVE DELTAS   : {negative}"
    )

    print(
        f"ZERO DELTAS       : {zero}"
    )

    print()

    print(
        f"FIRST DELTA       : "
        f"{fmt(deltas[0]) if deltas else 'None'}"
    )

    print(
        f"LAST DELTA        : "
        f"{fmt(deltas[-1]) if deltas else 'None'}"
    )

    # --------------------------------------------------------------
    # RESULT
    # --------------------------------------------------------------

    indicator_mismatch = any(
        [
            compare(
                stored_ema20,
                ema20_variants["FIRST_VALUE"],
            )["status"]
            == "MISMATCH",

            compare(
                stored_ema50,
                ema50_variants["FIRST_VALUE"],
            )["status"]
            == "MISMATCH",

            compare(
                stored_rsi14,
                rsi_variants["WILDER"],
            )["status"]
            == "MISMATCH",
        ]
    )

    return {
        "symbol": symbol,
        "status": (
            "SEMANTICS_DIFFERENCE"
            if indicator_mismatch
            else "MATCH"
        ),
        "best_ema20": best_ema20,
        "best_ema50": best_ema50,
        "best_rsi": best_rsi,
    }


# ======================================================================
# MAIN
# ======================================================================

def main():

    global ENGINE_SOURCE

    print_header(
        "ARUNDA INDICATOR POST REPAIR EXACT CALCULATION SEMANTICS INITIALIZATION FORENSIC AUDIT v0.1"
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
        "PURPOSE               : "
        "TRACE EXACT INDICATOR CALCULATION "
        "SEMANTICS / INITIALIZATION / FORMULA PATH"
    )

    print_section(
        "STEP 1 — ENGINE SOURCE RESOLUTION"
    )

    ENGINE_SOURCE = load_engine_source()

    if ENGINE_SOURCE is None:

        print(
            "ENGINE FOUND : False"
        )

        return 1

    print(
        f"ENGINE PATH   : {ENGINE_PATH}"
    )

    print(
        "ENGINE FOUND  : True"
    )

    print(
        f"SOURCE SIZE   : "
        f"{len(ENGINE_SOURCE)} characters"
    )

    print(
        f"SOURCE LINES  : "
        f"{len(ENGINE_SOURCE.splitlines())}"
    )

    tree = parse_engine(
        ENGINE_SOURCE
    )

    if tree is None:
        return 1

    print(
        "AST STATUS    : SUCCESS"
    )

    functions = function_inventory(
        tree
    )

    print_section(
        "STEP 2 — EXACT INDICATOR FUNCTION INVENTORY"
    )

    for name in [
        "calculate_analysis",
        "ema",
        "ema_series",
        "rsi",
        "macd",
    ]:

        node = functions.get(name)

        if node is None:
            print(
                f"[NOT FOUND] {name}()"
            )

        else:
            print(
                f"[FOUND] {name}() "
                f"LINE {node.lineno}-"
                f"{node.end_lineno}"
            )

    print_section(
        "STEP 3 — CALCULATION CALL SEMANTICS"
    )

    inspect_indicator_calls(
        functions
    )

    print_section(
        "STEP 4 — EMA / RSI SOURCE SEMANTICS"
    )

    inspect_function_semantics(
        ENGINE_SOURCE,
        functions,
        "ema",
    )

    inspect_function_semantics(
        ENGINE_SOURCE,
        functions,
        "rsi",
    )

    print_section(
        "STEP 5 — RSI AST / INITIALIZATION FORENSICS"
    )

    inspect_rsi_ast(
        functions
    )

    print_section(
        "STEP 6 — DATABASE RESOLUTION"
    )

    conn = connect_database()

    if conn is None:

        print(
            "DATABASE FOUND : False"
        )

        return 1

    print(
        f"DATABASE PATH  : {DB_PATH}"
    )

    print(
        "DATABASE FOUND : True"
    )

    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    print(
        f"TABLE COUNT : {len(tables)}"
    )

    print_section(
        "STEP 7 — TARGET SEMANTICS RECONSTRUCTION"
    )

    results = {}

    for symbol in TARGETS:

        try:

            results[symbol] = verify_symbol(
                conn,
                symbol,
            )

        except Exception as exc:

            print()
            print(
                f"[ERROR] {symbol}: {exc}"
            )

            results[symbol] = {
                "symbol": symbol,
                "status": "ERROR",
            }

    conn.close()

    print_section(
        "FINAL EXACT CALCULATION SEMANTICS FORENSIC SUMMARY"
    )

    complete = 0
    semantics_difference = 0
    unresolved = 0

    for symbol in TARGETS:

        result = results.get(
            symbol,
            {},
        )

        status = result.get(
            "status"
        )

        if status == "MATCH":
            complete += 1

        elif status == "SEMANTICS_DIFFERENCE":
            semantics_difference += 1

        else:
            unresolved += 1

    print(
        f"TARGETS CHECKED                    : "
        f"{len(TARGETS)}"
    )

    print(
        f"CALCULATION MATCH                  : "
        f"{complete}"
    )

    print(
        f"SEMANTICS DIFFERENCE               : "
        f"{semantics_difference}"
    )

    print(
        f"UNRESOLVED                          : "
        f"{unresolved}"
    )

    print()

    print(
        "TARGET MATRIX"
    )

    print_line("-")

    for symbol in TARGETS:

        status = results.get(
            symbol,
            {},
        ).get(
            "status",
            "UNRESOLVED",
        )

        print(
            f"  [{status:28s}] : {symbol}"
        )

    print()

    print_section(
        "FORENSIC CONCLUSION"
    )

    if unresolved > 0:

        print(
            "STATUS : "
            "CALCULATION_SEMANTICS_UNRESOLVED"
        )

        print(
            "REASON : "
            "ONE OR MORE TARGETS COULD NOT BE "
            "RECONSTRUCTED"
        )

        print(
            "NEXT FRONTIER : "
            "TRACE ONLY THE UNRESOLVED CALCULATION PATHS"
        )

    elif semantics_difference > 0:

        print(
            "STATUS : "
            "EXACT_CALCULATION_SEMANTICS_DIFFERENCE_CONFIRMED"
        )

        print(
            "REASON : "
            "PRODUCTION INDICATORS DO NOT MATCH "
            "THE STANDARD INITIALIZATION / SMOOTHING "
            "RECONSTRUCTIONS FROM THE EXACT PRODUCTION WINDOW"
        )

        print(
            "NEXT FRONTIER : "
            "TRACE THE EXACT PRODUCTION FUNCTION "
            "IMPLEMENTATION INCLUDING SEED, "
            "SMOOTHING, START INDEX, AND ROUNDING"
        )

    else:

        print(
            "STATUS : "
            "STANDARD_CALCULATION_SEMANTICS_MATCH"
        )

        print(
            "REASON : "
            "PRODUCTION INDICATORS RECONSTRUCT FROM "
            "THE EXACT PRODUCTION WINDOW"
        )

        print(
            "NEXT FRONTIER : "
            "NO CALCULATION SEMANTICS REGRESSION IDENTIFIED"
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

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )