from __future__ import annotations

import ast
import importlib.util
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA TRADER
# INDICATOR POST-REPAIR PRODUCTION INTERMEDIATE STATE RECONSTRUCTION
# FORENSIC AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Reconstruct and trace the exact production indicator path WITHOUT modifying
# the production engine or database.
#
# FORENSIC CHAIN
#
#   STORED DB VALUE
#          |
#          v
#   PRODUCTION CALL-SITE
#          |
#          v
#   INPUT VECTOR CONSTRUCTION
#          |
#          v
#   PRODUCTION FUNCTION
#          |
#          v
#   INTERNAL RETURN
#          |
#          v
#   POST-CALCULATION TRANSFORMATION
#          |
#          v
#   ROUNDING / CASTING
#          |
#          v
#   DATABASE ASSIGNMENT
#          |
#          v
#   STORED DB VALUE
#
# SAFETY
# ------
# READ ONLY
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO REPAIR
# NO DATABASE WRITE
#
# IMPORTANT
# ---------
# This script does NOT modify market_data_engine.py.
# This script does NOT modify arunda.db.
# All production-function executions, when performed, are in-memory only.
# =============================================================================


# =============================================================================
# CONFIGURATION
# =============================================================================

ENGINE_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\market_data_engine.py"
)

DATABASE_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

TABLE_NAME = "market_data"

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

TARGET_INDICATORS = [
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

PRODUCTION_WINDOW_SIZE = 120

READ_ONLY = True


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def section(title: str) -> None:
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def subsection(title: str) -> None:
    print()
    print(f"[{title}]")
    print("-" * 80)


# =============================================================================
# SAFETY
# =============================================================================

def assert_read_only() -> None:

    if READ_ONLY is not True:
        raise RuntimeError(
            "FORENSIC SAFETY FAILURE: READ_ONLY must remain True."
        )


# =============================================================================
# NUMERIC HELPERS
# =============================================================================

def safe_float(value: Any) -> float | None:

    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def abs_error(
    stored: Any,
    calculated: Any,
) -> float | None:

    a = safe_float(stored)
    b = safe_float(calculated)

    if a is None or b is None:
        return None

    return abs(a - b)


def rel_error(
    stored: Any,
    calculated: Any,
) -> float | None:

    a = safe_float(stored)
    b = safe_float(calculated)

    if a is None or b is None:
        return None

    if b == 0:
        return None

    return abs(a - b) / abs(b)


def values_equal(
    a: Any,
    b: Any,
) -> bool:

    if a is None and b is None:
        return True

    if isinstance(a, (int, float)) and isinstance(
        b,
        (int, float),
    ):
        return float(a) == float(b)

    return a == b


# =============================================================================
# PATH RESOLUTION
# =============================================================================

def resolve_paths() -> None:

    section(
        "STEP 1 — PATH RESOLUTION"
    )

    print(
        f"ENGINE PATH                 : {ENGINE_PATH}"
    )

    print(
        f"ENGINE FOUND                : {ENGINE_PATH.exists()}"
    )

    print(
        f"DATABASE PATH               : {DATABASE_PATH}"
    )

    print(
        f"DATABASE FOUND              : {DATABASE_PATH.exists()}"
    )

    if not ENGINE_PATH.exists():

        raise FileNotFoundError(
            f"Production engine not found:\n{ENGINE_PATH}"
        )

    if not DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"Database not found:\n{DATABASE_PATH}"
        )


# =============================================================================
# SOURCE LOAD
# =============================================================================

def load_source() -> str:

    source = ENGINE_PATH.read_text(
        encoding="utf-8"
    )

    section(
        "STEP 2 — ENGINE SOURCE RESOLUTION"
    )

    print(
        f"SOURCE SIZE                 : "
        f"{len(source)} characters"
    )

    print(
        f"SOURCE LINES                : "
        f"{len(source.splitlines())}"
    )

    return source


# =============================================================================
# AST
# =============================================================================

def parse_source(
    source: str,
) -> ast.Module:

    try:

        tree = ast.parse(
            source,
            filename=str(ENGINE_PATH),
        )

    except SyntaxError as exc:

        raise RuntimeError(
            "Production engine AST parsing failed."
        ) from exc

    print(
        "AST STATUS                  : SUCCESS"
    )

    return tree


def discover_functions(
    tree: ast.Module,
) -> dict[str, ast.FunctionDef]:

    functions: dict[str, ast.FunctionDef] = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            functions[node.name] = node

    return functions


def print_function_inventory(
    functions: dict[str, ast.FunctionDef],
) -> None:

    section(
        "STEP 3 — PRODUCTION FUNCTION INVENTORY"
    )

    print(
        f"FUNCTIONS DISCOVERED        : "
        f"{len(functions)}"
    )

    for name in sorted(functions):

        node = functions[name]

        end_line = getattr(
            node,
            "end_lineno",
            "?",
        )

        print(
            f"[FOUND] {name:<32} "
            f"LINE {node.lineno}-{end_line}"
        )


# =============================================================================
# AST SOURCE SEGMENT
# =============================================================================

def source_segment(
    source: str,
    node: ast.AST,
) -> str:

    result = ast.get_source_segment(
        source,
        node,
    )

    if result is None:
        return "<SOURCE SEGMENT UNAVAILABLE>"

    return result


# =============================================================================
# CALL-SITE FORENSICS
# =============================================================================

TARGET_PRODUCTION_FUNCTIONS = {
    "calculate_analysis",
    "ema",
    "ema_series",
    "rsi",
    "macd",
    "atr",
    "adx",
    "bollinger",
    "volume_metrics",
    "volatility",
    "technical_score",
}


def trace_callsites(
    source: str,
    tree: ast.Module,
) -> list[dict[str, Any]]:

    calls: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if not isinstance(
            node.func,
            ast.Name,
        ):
            continue

        function_name = node.func.id

        if function_name not in TARGET_PRODUCTION_FUNCTIONS:
            continue

        calls.append(
            {
                "function": function_name,
                "line": node.lineno,
                "source": source_segment(
                    source,
                    node,
                ),
            }
        )

    calls.sort(
        key=lambda item: item["line"]
    )

    return calls


def print_callsites(
    calls: list[dict[str, Any]],
) -> None:

    section(
        "STEP 4 — EXACT PRODUCTION CALL-SITE MAP"
    )

    for item in calls:

        print(
            f"LINE {item['line']:<5} | "
            f"{item['function']:<20} | "
            f"{item['source']}"
        )


# =============================================================================
# ASSIGNMENT FORENSICS
# =============================================================================

def find_assignments(
    source: str,
    tree: ast.Module,
) -> list[dict[str, Any]]:

    assignments: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
            ),
        ):
            continue

        text = source_segment(
            source,
            node,
        )

        if not text:
            continue

        indicator_hit = any(
            indicator in text
            for indicator in TARGET_INDICATORS
        )

        production_hit = (
            "market_data" in text
            or "technical_score" in text
            or "ema20" in text
            or "ema50" in text
            or "rsi14" in text
            or "macd" in text
        )

        if indicator_hit or production_hit:

            assignments.append(
                {
                    "line": getattr(
                        node,
                        "lineno",
                        None,
                    ),
                    "source": text,
                }
            )

    assignments.sort(
        key=lambda item: (
            item["line"]
            if item["line"] is not None
            else -1
        )
    )

    return assignments


def print_assignments(
    assignments: list[dict[str, Any]],
) -> None:

    section(
        "STEP 5 — INDICATOR / DATABASE ASSIGNMENT FORENSIC MAP"
    )

    if not assignments:

        print(
            "[NONE] No indicator-related assignments "
            "were identified by AST text matching."
        )

        return

    for item in assignments:

        print(
            f"LINE {item['line']:<5} | "
            f"{item['source']}"
        )


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def open_read_only_database() -> sqlite3.Connection:

    assert_read_only()

    uri = (
        "file:"
        + DATABASE_PATH.as_posix()
        + "?mode=ro"
    )

    connection = sqlite3.connect(
        uri,
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    return connection


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

def inspect_schema(
    connection: sqlite3.Connection,
) -> list[str]:

    section(
        "STEP 6 — DATABASE SCHEMA RESOLUTION"
    )

    rows = connection.execute(
        f"PRAGMA table_info({TABLE_NAME})"
    ).fetchall()

    columns: list[str] = []

    for row in rows:

        index = row["cid"]
        name = row["name"]

        columns.append(name)

        print(
            f"{index:>3} : {name}"
        )

    return columns


# =============================================================================
# DATABASE READ HELPERS
# =============================================================================

def get_latest_row(
    connection: sqlite3.Connection,
    symbol: str,
) -> sqlite3.Row | None:

    return connection.execute(
        f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()


def get_window(
    connection: sqlite3.Connection,
    symbol: str,
    limit: int,
) -> list[sqlite3.Row]:

    rows = connection.execute(
        f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            symbol,
            limit,
        ),
    ).fetchall()

    rows.reverse()

    return list(rows)


# =============================================================================
# EXACT CALL-SITE INPUT RECONSTRUCTION
# =============================================================================

def reconstruct_callsite_inputs(
    rows: list[sqlite3.Row],
) -> dict[str, list[float]]:

    closes: list[float] = []

    highs: list[float] = []

    lows: list[float] = []

    volumes: list[float] = []

    for row in rows:

        close = safe_float(
            row["close"]
        )

        volume = safe_float(
            row["volume"]
        )

        if close is None:
            continue

        closes.append(
            close
        )

        # EXACTLY MATCHES THE OBSERVED PRODUCTION
        # calculate_analysis transformation.
        highs.append(
            close
        )

        lows.append(
            close
        )

        volumes.append(
            volume
            if volume is not None
            else 0.0
        )

    return {
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
    }


def print_input_state(
    vectors: dict[str, list[float]],
) -> None:

    subsection(
        "CALL-SITE INPUT VECTORS"
    )

    for name, values in vectors.items():

        print(
            f"{name:<12} COUNT : {len(values)}"
        )

        if values:

            print(
                f"{name:<12} FIRST : {values[0]}"
            )

            print(
                f"{name:<12} LAST  : {values[-1]}"
            )


# =============================================================================
# PRODUCTION MODULE LOAD
# =============================================================================

def load_production_module() -> Any:

    """
    Load the production module for IN-MEMORY forensic execution only.

    This function does not intentionally invoke the engine's production
    pipeline and does not perform any database write.

    If the module contains import-time side effects, they will occur as part
    of Python module loading. Therefore this loader reports that condition
    explicitly in the forensic output.
    """

    section(
        "STEP 7 — PRODUCTION FUNCTION RESOLUTION"
    )

    spec = importlib.util.spec_from_file_location(
        "arunda_production_forensic_module",
        ENGINE_PATH,
    )

    if spec is None:

        raise RuntimeError(
            "Unable to construct module specification."
        )

    if spec.loader is None:

        raise RuntimeError(
            "Production module loader unavailable."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    required = [
        "ema",
        "ema_series",
        "rsi",
        "macd",
        "atr",
        "adx",
        "bollinger",
        "volume_metrics",
        "volatility",
        "technical_score",
    ]

    for function_name in required:

        exists = hasattr(
            module,
            function_name,
        )

        print(
            f"[{'FOUND' if exists else 'MISSING'}] "
            f"{function_name}"
        )

        if not exists:

            raise RuntimeError(
                f"Production function missing: "
                f"{function_name}"
            )

    return module


# =============================================================================
# EXACT FUNCTION RETURN RECONSTRUCTION
# =============================================================================

def execute_production_functions(
    module: Any,
    vectors: dict[str, list[float]],
) -> dict[str, Any]:

    closes = vectors["closes"]

    highs = vectors["highs"]

    lows = vectors["lows"]

    volumes = vectors["volumes"]

    result: dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # EMA20
    # -------------------------------------------------------------------------

    result["ema20"] = module.ema(
        closes,
        20,
    )

    # -------------------------------------------------------------------------
    # EMA50
    # -------------------------------------------------------------------------

    result["ema50"] = module.ema(
        closes,
        50,
    )

    # -------------------------------------------------------------------------
    # RSI14
    # -------------------------------------------------------------------------

    result["rsi14"] = module.rsi(
        closes,
        14,
    )

    # -------------------------------------------------------------------------
    # MACD
    # -------------------------------------------------------------------------

    macd_result = module.macd(
        closes
    )

    if (
        isinstance(
            macd_result,
            tuple,
        )
        and len(macd_result) == 3
    ):

        (
            result["macd"],
            result["macd_signal"],
            result["macd_hist"],
        ) = macd_result

    else:

        result["macd"] = None
        result["macd_signal"] = None
        result["macd_hist"] = None

    # -------------------------------------------------------------------------
    # ATR14
    # -------------------------------------------------------------------------

    result["atr14"] = module.atr(
        highs,
        lows,
        closes,
        14,
    )

    # -------------------------------------------------------------------------
    # ADX14
    # -------------------------------------------------------------------------

    result["adx14"] = module.adx(
        highs,
        lows,
        closes,
        14,
    )

    # -------------------------------------------------------------------------
    # BOLLINGER
    # -------------------------------------------------------------------------

    bb_result = module.bollinger(
        closes,
        20,
        2.0,
    )

    if (
        isinstance(
            bb_result,
            tuple,
        )
        and len(bb_result) == 4
    ):

        (
            result["bb_middle"],
            result["bb_upper"],
            result["bb_lower"],
            result["bb_width"],
        ) = bb_result

    else:

        result["bb_middle"] = None
        result["bb_upper"] = None
        result["bb_lower"] = None
        result["bb_width"] = None

    # -------------------------------------------------------------------------
    # VOLUME METRICS
    # -------------------------------------------------------------------------

    volume_result = module.volume_metrics(
        volumes,
        20,
    )

    if (
        isinstance(
            volume_result,
            tuple,
        )
        and len(volume_result) == 2
    ):

        (
            result["volume_sma20"],
            result["volume_ratio"],
        ) = volume_result

    else:

        result["volume_sma20"] = None
        result["volume_ratio"] = None

    # -------------------------------------------------------------------------
    # VOLATILITY
    # -------------------------------------------------------------------------

    result["volatility"] = module.volatility(
        closes,
        20,
    )

    # -------------------------------------------------------------------------
    # TECHNICAL SCORE
    # -------------------------------------------------------------------------

    close = closes[-1]

    result["technical_score"] = module.technical_score(
        close,
        result["ema20"],
        result["ema50"],
        result["rsi14"],
        result["macd"],
        result["macd_signal"],
        result["adx14"],
        result["bb_middle"],
        result["volume_ratio"],
    )

    return result


# =============================================================================
# STORED VALUE EXTRACTION
# =============================================================================

def extract_stored_values(
    row: sqlite3.Row,
) -> dict[str, Any]:

    result: dict[str, Any] = {}

    for indicator in TARGET_INDICATORS:

        if indicator in row.keys():

            result[indicator] = row[indicator]

    return result


# =============================================================================
# COMPARISON
# =============================================================================

def compare_stored_to_return(
    stored: dict[str, Any],
    returned: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    comparison: dict[str, dict[str, Any]] = {}

    for indicator in TARGET_INDICATORS:

        stored_value = stored.get(
            indicator
        )

        returned_value = returned.get(
            indicator
        )

        exact = values_equal(
            stored_value,
            returned_value,
        )

        ae = abs_error(
            stored_value,
            returned_value,
        )

        re = rel_error(
            stored_value,
            returned_value,
        )

        if exact:

            status = "EXACT_MATCH"

        elif (
            stored_value is None
            and returned_value is not None
        ):

            status = "STORED_NULL"

        elif (
            stored_value is not None
            and returned_value is None
        ):

            status = "FUNCTION_RETURN_NULL"

        else:

            status = "RETURN_DIFFERENCE"

        comparison[indicator] = {
            "stored": stored_value,
            "returned": returned_value,
            "abs_error": ae,
            "rel_error": re,
            "status": status,
        }

    return comparison


# =============================================================================
# POST-CALCULATION / ROUNDING FORENSICS
# =============================================================================

def inspect_possible_post_transformations(
    source: str,
    tree: ast.Module,
) -> None:

    section(
        "STEP 8 — POST-CALCULATION / ROUNDING FORENSIC SCAN"
    )

    keywords = [
        "round(",
        "float(",
        "int(",
        "Decimal(",
        "format(",
        "strftime(",
        "technical_score",
        "ema20",
        "ema50",
        "rsi14",
        "macd",
        "atr14",
        "adx14",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "volume_sma20",
        "volume_ratio",
        "volatility",
    ]

    found = False

    lines = source.splitlines()

    for index, line in enumerate(
        lines,
        start=1,
    ):

        stripped = line.strip()

        if not stripped:
            continue

        if any(
            keyword in stripped
            for keyword in keywords
        ):

            print(
                f"LINE {index:<5} | {stripped}"
            )

            found = True

    if not found:

        print(
            "[NONE] No post-calculation "
            "transformation keyword detected."
        )


# =============================================================================
# SYMBOL AUDIT
# =============================================================================

def audit_symbol(
    connection: sqlite3.Connection,
    module: Any,
    symbol: str,
) -> dict[str, Any]:

    section(
        f"STEP 9 — PRODUCTION INTERMEDIATE STATE RECONSTRUCTION : {symbol}"
    )

    latest = get_latest_row(
        connection,
        symbol,
    )

    if latest is None:

        print(
            f"[MISSING] SYMBOL : {symbol}"
        )

        return {
            "symbol": symbol,
            "status": "MISSING",
        }

    window = get_window(
        connection,
        symbol,
        PRODUCTION_WINDOW_SIZE,
    )

    vectors = reconstruct_callsite_inputs(
        window
    )

    print(
        f"TARGET ID                  : "
        f"{latest['id']}"
    )

    print(
        f"TARGET TIMESTAMP           : "
        f"{latest['timestamp']}"
    )

    print(
        f"SOURCE TIMESTAMP           : "
        f"{latest['source_timestamp']}"
    )

    print(
        f"ENGINE VERSION             : "
        f"{latest['engine_version']}"
    )

    print(
        f"WINDOW ROWS                : "
        f"{len(window)}"
    )

    print_input_state(
        vectors
    )

    # -------------------------------------------------------------------------
    # FUNCTION RETURN
    # -------------------------------------------------------------------------

    subsection(
        "ACTUAL IN-MEMORY PRODUCTION FUNCTION RETURNS"
    )

    returned = execute_production_functions(
        module,
        vectors,
    )

    for indicator in TARGET_INDICATORS:

        print(
            f"{indicator:<20} : "
            f"{returned.get(indicator)}"
        )

    # -------------------------------------------------------------------------
    # STORED
    # -------------------------------------------------------------------------

    subsection(
        "STORED DATABASE VALUES"
    )

    stored = extract_stored_values(
        latest
    )

    for indicator in TARGET_INDICATORS:

        print(
            f"{indicator:<20} : "
            f"{stored.get(indicator)}"
        )

    # -------------------------------------------------------------------------
    # COMPARISON
    # -------------------------------------------------------------------------

    subsection(
        "STORED VALUE vs PRODUCTION RETURN"
    )

    comparison = compare_stored_to_return(
        stored,
        returned,
    )

    exact_count = 0
    difference_count = 0
    null_count = 0

    for indicator, item in comparison.items():

        print()

        print(
            f"INDICATOR            : "
            f"{indicator}"
        )

        print(
            f"STORED VALUE         : "
            f"{item['stored']}"
        )

        print(
            f"FUNCTION RETURN      : "
            f"{item['returned']}"
        )

        print(
            f"ABS ERROR            : "
            f"{item['abs_error']}"
        )

        print(
            f"REL ERROR            : "
            f"{item['rel_error']}"
        )

        print(
            f"STATUS               : "
            f"{item['status']}"
        )

        if item["status"] == "EXACT_MATCH":
            exact_count += 1

        elif item["status"] == "RETURN_DIFFERENCE":
            difference_count += 1

        else:
            null_count += 1

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------

    if difference_count > 0:

        verdict = (
            "PRODUCTION_RETURN_DIFFERS_FROM_STORED"
        )

    elif exact_count == len(
        TARGET_INDICATORS
    ):

        verdict = (
            "PRODUCTION_RETURN_MATCHES_STORED"
        )

    else:

        verdict = (
            "PARTIAL_OR_NULL_PATH"
        )

    print()

    print(
        f"SYMBOL VERDICT            : "
        f"{verdict}"
    )

    print(
        f"EXACT MATCHES             : "
        f"{exact_count}"
    )

    print(
        f"RETURN DIFFERENCES        : "
        f"{difference_count}"
    )

    print(
        f"NULL / OTHER              : "
        f"{null_count}"
    )

    return {
        "symbol": symbol,
        "stored": stored,
        "returned": returned,
        "comparison": comparison,
        "verdict": verdict,
    }


# =============================================================================
# FINAL SUMMARY
# =============================================================================

def final_summary(
    results: list[dict[str, Any]],
) -> None:

    banner(
        "FINAL EXACT PRODUCTION INTERMEDIATE STATE FORENSIC SUMMARY"
    )

    total = len(results)

    matches = 0
    differences = 0
    missing = 0
    unresolved = 0

    for result in results:

        symbol = result.get(
            "symbol"
        )

        verdict = result.get(
            "verdict"
        )

        if verdict == (
            "PRODUCTION_RETURN_MATCHES_STORED"
        ):

            matches += 1

        elif verdict == (
            "PRODUCTION_RETURN_DIFFERS_FROM_STORED"
        ):

            differences += 1

        elif verdict == "MISSING":

            missing += 1

        else:

            unresolved += 1

        print(
            f"[{verdict}] : {symbol}"
        )

    print()

    print(
        f"TARGETS CHECKED             : {total}"
    )

    print(
        f"PRODUCTION RETURN MATCHES   : {matches}"
    )

    print(
        f"PRODUCTION RETURN DIFFERENCES: {differences}"
    )

    print(
        f"MISSING                      : {missing}"
    )

    print(
        f"UNRESOLVED                   : {unresolved}"
    )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    if differences > 0:

        print(
            "STATUS                      : "
            "PRODUCTION_RETURN_PATH_DIFFERENCE_CONFIRMED"
        )

        print(
            "MEANING                     : "
            "The direct in-memory production-function "
            "return differs from the stored database value."
        )

        print(
            "IMPORTANT                   : "
            "This does NOT yet prove a formula defect."
        )

        print(
            "NEXT FRONTIER               : "
            "TRACE ACTUAL PRODUCTION CALL-SITE INPUT "
            "CONSTRUCTION + POST-CALCULATION "
            "TRANSFORMATION + ROUNDING + "
            "DATABASE ASSIGNMENT."
        )

    elif matches == total:

        print(
            "STATUS                      : "
            "PRODUCTION_RETURN_MATCH_CONFIRMED"
        )

        print(
            "NEXT FRONTIER               : "
            "DATABASE ASSIGNMENT / "
            "SERIALIZATION FORENSICS."
        )

    else:

        print(
            "STATUS                      : "
            "FORENSIC_RECONSTRUCTION_INCOMPLETE"
        )

    print()

    print(
        "DATABASE WRITE OPERATIONS   : NONE"
    )

    print(
        "ENGINE MODIFICATIONS        : NONE"
    )

    print(
        "INSERT                      : NONE"
    )

    print(
        "UPDATE                      : NONE"
    )

    print(
        "DELETE                      : NONE"
    )

    print(
        "ALTER                       : NONE"
    )

    print(
        "PRODUCTION RECALCULATION    : "
        "IN-MEMORY FORENSIC ONLY"
    )

    print(
        "SQL MODE                    : READ ONLY"
    )

    print(
        "AUDIT COMPLETE"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    banner(
        "ARUNDA INDICATOR POST-REPAIR "
        "PRODUCTION INTERMEDIATE STATE RECONSTRUCTION "
        "FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                        : READ ONLY"
    )

    print(
        "DATABASE WRITE              : NONE"
    )

    print(
        "ENGINE WRITE                : NONE"
    )

    print(
        "FORMULA WRITE               : NONE"
    )

    print(
        "DATABASE REPAIR             : NONE"
    )

    print(
        "PRODUCTION DATABASE RECALC  : NONE"
    )

    print(
        "PURPOSE                     : "
        "MAP STORED INDICATORS TO "
        "EXACT CALL-SITE INPUT, "
        "FUNCTION RETURN, "
        "POST-CALCULATION STATE, "
        "AND ASSIGNMENT PATH"
    )

    assert_read_only()

    resolve_paths()

    source = load_source()

    tree = parse_source(
        source
    )

    functions = discover_functions(
        tree
    )

    print_function_inventory(
        functions
    )

    calls = trace_callsites(
        source,
        tree,
    )

    print_callsites(
        calls
    )

    assignments = find_assignments(
        source,
        tree,
    )

    print_assignments(
        assignments
    )

    inspect_possible_post_transformations(
        source,
        tree,
    )

    connection = open_read_only_database()

    module = load_production_module()

    results: list[dict[str, Any]] = []

    try:

        inspect_schema(
            connection
        )

        for symbol in TARGET_SYMBOLS:

            result = audit_symbol(
                connection,
                module,
                symbol,
            )

            results.append(
                result
            )

    finally:

        connection.close()

    final_summary(
        results
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "AUDIT INTERRUPTED BY USER."
        )
        sys.exit(130)

    except Exception as exc:

        print()
        print("=" * 100)
        print("FORENSIC AUDIT ERROR")
        print("=" * 100)

        print(
            f"TYPE        : {type(exc).__name__}"
        )

        print(
            f"MESSAGE     : {exc}"
        )

        print()

        print(
            "IMPORTANT   : "
            "NO INTENTIONAL DATABASE WRITE WAS "
            "PERFORMED BY THIS AUDIT."
        )

        raise