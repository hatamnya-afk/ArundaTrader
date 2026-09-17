# INDICATOR_RUNTIME_CALLER_SQL_PARAMETER_ASSIGNMENT_FORENSIC_AUDIT_v0.1.py

import ast
import os
import re
import sqlite3
import time
from pathlib import Path


# =============================================================================
# ARUNDA INDICATOR RUNTIME CALLER + SQL PARAMETER ASSIGNMENT FORENSIC AUDIT v0.1
# =============================================================================
#
# MODE:
#     READ ONLY / FORENSIC ONLY
#
# PURPOSE:
#     Trace the exact runtime production caller path around calculate_analysis,
#     including:
#
#       runtime caller
#       -> input construction
#       -> SQL execution
#       -> SQL parameter construction
#       -> rows retrieval
#       -> calculate_analysis invocation
#       -> returned indicator dictionary
#       -> post-calculation assignment
#       -> database UPDATE/INSERT target
#
# IMPORTANT:
#     This script DOES NOT modify:
#         - production engine
#         - database
#         - formulas
#         - stored values
#
# DATABASE:
#     C:\Users\ASUS\ArundaTrader\arunda.db
#
# ENGINE:
#     C:\Users\ASUS\ArundaTrader\market_data_engine.py
#
# TARGETS:
#     BTC / ETH / SOL / XRP
#
# =============================================================================


BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

ENGINE_PATH = BASE_DIR / "market_data_engine.py"
DATABASE_PATH = BASE_DIR / "arunda.db"

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

TARGET_FUNCTION = "calculate_analysis"

START_TIME = time.perf_counter()


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def safe_text(value):
    if value is None:
        return "None"

    text = repr(value)

    if len(text) > 500:
        return text[:500] + "...<TRUNCATED>"

    return text


# =============================================================================
# FILE RESOLUTION
# =============================================================================

banner(
    "ARUNDA INDICATOR RUNTIME CALLER SQL PARAMETER ASSIGNMENT FORENSIC AUDIT v0.1"
)

print("MODE                         : READ ONLY")
print("DATABASE WRITE              : NONE")
print("ENGINE WRITE                : NONE")
print("FORMULA WRITE               : NONE")
print("PRODUCTION RECALCULATION    : NONE")
print("PURPOSE                     : TRACE RUNTIME CALLER + SQL PARAMETERS + ASSIGNMENT")


section("STEP 1 — PATH RESOLUTION")

print(f"ENGINE PATH                 : {ENGINE_PATH}")
print(f"ENGINE FOUND                : {ENGINE_PATH.exists()}")

print(f"DATABASE PATH               : {DATABASE_PATH}")
print(f"DATABASE FOUND              : {DATABASE_PATH.exists()}")

if not ENGINE_PATH.exists():
    raise FileNotFoundError(
        f"Production engine not found: {ENGINE_PATH}"
    )

if not DATABASE_PATH.exists():
    raise FileNotFoundError(
        f"Database not found: {DATABASE_PATH}"
    )


# =============================================================================
# ENGINE SOURCE
# =============================================================================

section("STEP 2 — ENGINE SOURCE / AST RESOLUTION")

source = ENGINE_PATH.read_text(
    encoding="utf-8"
)

print(f"SOURCE SIZE                 : {len(source)} characters")
print(f"SOURCE LINES                : {len(source.splitlines())}")

tree = ast.parse(
    source,
    filename=str(ENGINE_PATH)
)

print("AST STATUS                  : SUCCESS")


# =============================================================================
# AST UTILITIES
# =============================================================================

def node_line(node):
    return getattr(node, "lineno", None)


def node_end_line(node):
    return getattr(node, "end_lineno", None)


def source_segment(node):
    try:
        value = ast.get_source_segment(source, node)
    except Exception:
        value = None

    return value or ""


def function_nodes(tree):
    result = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result.append(node)

    return result


functions = function_nodes(tree)

target_function_node = None

for node in functions:
    if node.name == TARGET_FUNCTION:
        target_function_node = node
        break

print(f"FUNCTIONS DISCOVERED        : {len(functions)}")

if target_function_node is None:
    print(
        f"[MISSING] {TARGET_FUNCTION}"
    )
else:
    print(
        f"[FOUND] {TARGET_FUNCTION} "
        f"LINE {node_line(target_function_node)}-"
        f"{node_end_line(target_function_node)}"
    )


# =============================================================================
# CALL-SITE DISCOVERY
# =============================================================================

section("STEP 3 — STATIC RUNTIME CALL-SITE DISCOVERY")


call_sites = []

for node in ast.walk(tree):

    if not isinstance(node, ast.Call):
        continue

    func = node.func

    called_name = None

    if isinstance(func, ast.Name):
        called_name = func.id

    elif isinstance(func, ast.Attribute):
        called_name = func.attr

    if called_name != TARGET_FUNCTION:
        continue

    call_sites.append(node)


print(
    f"CALCULATE_ANALYSIS CALLS     : {len(call_sites)}"
)

for index, call in enumerate(call_sites, start=1):

    print()
    print(
        f"[CALL SITE {index}]"
    )

    print(
        f"LINE                        : {node_line(call)}"
    )

    print(
        f"SOURCE                      : "
        f"{source_segment(call).strip()}"
    )

    print(
        f"ARGUMENT COUNT              : "
        f"{len(call.args)}"
    )

    for arg_index, arg in enumerate(
        call.args,
        start=1,
    ):

        print(
            f"ARG {arg_index} SOURCE         : "
            f"{source_segment(arg).strip()}"
        )


# =============================================================================
# PARENT / SURROUNDING FUNCTION MAP
# =============================================================================

section("STEP 4 — CALL-SITE SURROUNDING FUNCTION MAP")


def find_parent_function(call_node):

    target_line = node_line(call_node)

    candidates = []

    for fn in functions:

        start = node_line(fn)
        end = node_end_line(fn)

        if (
            start is not None
            and end is not None
            and target_line is not None
            and start <= target_line <= end
        ):
            candidates.append(fn)

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            node_end_line(x) - node_line(x)
        )
    )

    return candidates[0]


parent_functions = []

for call in call_sites:

    parent = find_parent_function(call)

    if parent is not None:

        parent_functions.append(parent)

        print(
            f"CALL LINE                   : {node_line(call)}"
        )

        print(
            f"RUNTIME FUNCTION             : {parent.name}"
        )

        print(
            f"FUNCTION RANGE               : "
            f"{node_line(parent)}-{node_end_line(parent)}"
        )


# =============================================================================
# SQL DISCOVERY
# =============================================================================

section("STEP 5 — SQL EXECUTION SITE DISCOVERY")


SQL_METHODS = {
    "execute",
    "executemany",
    "executescript",
}


sql_calls = []

for node in ast.walk(tree):

    if not isinstance(node, ast.Call):
        continue

    func = node.func

    if not isinstance(func, ast.Attribute):
        continue

    if func.attr not in SQL_METHODS:
        continue

    sql_calls.append(node)


print(
    f"SQL EXECUTION CALLS          : {len(sql_calls)}"
)


def normalize_sql(text):
    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text.strip(),
    )

    return text


for index, node in enumerate(
    sql_calls,
    start=1,
):

    print()
    print(
        f"[SQL SITE {index}]"
    )

    print(
        f"LINE                        : "
        f"{node_line(node)}"
    )

    print(
        f"METHOD                      : "
        f"{node.func.attr}"
    )

    if node.args:

        sql_arg = node.args[0]

        sql_source = source_segment(
            sql_arg
        )

        print(
            f"SQL SOURCE                  : "
            f"{normalize_sql(sql_source)}"
        )

    if len(node.args) >= 2:

        params_source = source_segment(
            node.args[1]
        )

        print(
            f"PARAMETER SOURCE            : "
            f"{normalize_sql(params_source)}"
        )

    else:

        print(
            "PARAMETER SOURCE            : <NONE>"
        )


# =============================================================================
# SQL PARAMETER EXPRESSION TRACE
# =============================================================================

section("STEP 6 — SQL PARAMETER EXPRESSION TRACE")


def extract_sql_parameter_expressions(node):

    result = []

    if len(node.args) < 2:
        return result

    params = node.args[1]

    if isinstance(
        params,
        (
            ast.Tuple,
            ast.List,
        ),
    ):

        for element in params.elts:

            result.append(
                source_segment(element).strip()
            )

    else:

        result.append(
            source_segment(params).strip()
        )

    return result


for index, node in enumerate(
    sql_calls,
    start=1,
):

    params = extract_sql_parameter_expressions(
        node
    )

    if not params:
        continue

    print()
    print(
        f"[SQL PARAMETER SITE {index}]"
    )

    print(
        f"LINE                        : "
        f"{node_line(node)}"
    )

    for param_index, param in enumerate(
        params,
        start=1,
    ):

        print(
            f"PARAM {param_index}               : "
            f"{param}"
        )


# =============================================================================
# TARGET SYMBOL SQL REFERENCE DISCOVERY
# =============================================================================

section("STEP 7 — TARGET SYMBOL REFERENCE DISCOVERY")


symbol_references = {}

for symbol in TARGET_SYMBOLS:

    occurrences = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Constant,
        ):
            continue

        if node.value != symbol:
            continue

        occurrences.append(
            node
        )

    symbol_references[symbol] = occurrences

    print()
    print(
        f"SYMBOL                      : {symbol}"
    )

    print(
        f"STATIC REFERENCES           : "
        f"{len(occurrences)}"
    )

    for occurrence in occurrences:

        print(
            f"LINE                        : "
            f"{node_line(occurrence)}"
        )


# =============================================================================
# DATABASE READ-ONLY CONNECTION
# =============================================================================

section("STEP 8 — DATABASE READ-ONLY CONNECTION")


db_uri = (
    "file:"
    + str(DATABASE_PATH).replace("\\", "/")
    + "?mode=ro"
)

connection = sqlite3.connect(
    db_uri,
    uri=True,
)

connection.row_factory = sqlite3.Row

print(
    "SQLITE MODE                 : READ ONLY URI"
)

print(
    "DATABASE WRITE              : BLOCKED BY OPEN MODE"
)


# =============================================================================
# SQLITE AUTHORIZE CALLBACK
# =============================================================================
#
# Important:
#
# Python sqlite3 DOES NOT provide:
#
#     SQLITE_ALTER_INDEX
#
# Therefore the previous script crashed.
#
# We only use constants actually exposed by sqlite3.
#
# More importantly, the database is already opened with:
#
#     ?mode=ro
#
# so write operations cannot be committed anyway.
#
# =============================================================================


WRITE_ACTION_NAMES = {
    "SQLITE_INSERT",
    "SQLITE_UPDATE",
    "SQLITE_DELETE",
    "SQLITE_ALTER_TABLE",
    "SQLITE_CREATE_INDEX",
    "SQLITE_CREATE_TABLE",
    "SQLITE_CREATE_TEMP_INDEX",
    "SQLITE_CREATE_TEMP_TABLE",
    "SQLITE_CREATE_TEMP_TRIGGER",
    "SQLITE_CREATE_TEMP_VIEW",
    "SQLITE_CREATE_TRIGGER",
    "SQLITE_CREATE_VIEW",
    "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TABLE",
    "SQLITE_DROP_TEMP_INDEX",
    "SQLITE_DROP_TEMP_TABLE",
    "SQLITE_DROP_TEMP_TRIGGER",
    "SQLITE_DROP_TEMP_VIEW",
    "SQLITE_DROP_TRIGGER",
    "SQLITE_DROP_VIEW",
    "SQLITE_REINDEX",
    "SQLITE_TRANSACTION",
}


WRITE_ACTION_CODES = set()

for action_name in WRITE_ACTION_NAMES:

    action_code = getattr(
        sqlite3,
        action_name,
        None,
    )

    if action_code is not None:
        WRITE_ACTION_CODES.add(
            action_code
        )


def sqlite_authorizer(
    action,
    arg1,
    arg2,
    db_name,
    trigger_name,
):

    if action in WRITE_ACTION_CODES:

        print()
        print(
            "[WRITE OPERATION BLOCKED]"
        )

        print(
            f"ACTION                      : "
            f"{action}"
        )

        print(
            f"ARG1                        : "
            f"{safe_text(arg1)}"
        )

        print(
            f"ARG2                        : "
            f"{safe_text(arg2)}"
        )

        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


connection.set_authorizer(
    sqlite_authorizer
)


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

section("STEP 9 — DATABASE SCHEMA RESOLUTION")


tables = connection.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """
).fetchall()


print(
    f"TABLE COUNT                 : {len(tables)}"
)


for table in tables:

    table_name = table["name"]

    print(
        f"[TABLE] {table_name}"
    )


# =============================================================================
# MARKET_DATA TARGET RESOLUTION
# =============================================================================

section("STEP 10 — STORED TARGET RESOLUTION")


existing_tables = {
    row["name"]
    for row in tables
}


if "market_data" not in existing_tables:

    print(
        "[MISSING] market_data"
    )

    target_rows = []

else:

    placeholders = ",".join(
        "?"
        for _ in TARGET_SYMBOLS
    )

    query = f"""
        SELECT
            id,
            timestamp,
            symbol,
            timeframe,
            close,
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
        WHERE symbol IN ({placeholders})
        ORDER BY
            symbol,
            id DESC
    """

    target_rows = connection.execute(
        query,
        TARGET_SYMBOLS,
    ).fetchall()


resolved_targets = {}

for row in target_rows:

    symbol = row["symbol"]

    if symbol not in resolved_targets:

        resolved_targets[symbol] = row


for symbol in TARGET_SYMBOLS:

    row = resolved_targets.get(
        symbol
    )

    if row is None:

        print(
            f"[MISSING_TARGET]            : "
            f"{symbol}"
        )

        continue

    print(
        f"[STORED_TARGET_RESOLVED]     : "
        f"{symbol}"
    )

    print(
        f"ID                          : "
        f"{row['id']}"
    )

    print(
        f"TIMESTAMP                   : "
        f"{row['timestamp']}"
    )

    print(
        f"CLOSE                       : "
        f"{row['close']}"
    )

    print(
        f"EMA20                       : "
        f"{row['ema20']}"
    )

    print(
        f"EMA50                       : "
        f"{row['ema50']}"
    )

    print(
        f"RSI14                       : "
        f"{row['rsi14']}"
    )

    print(
        f"ENGINE_VERSION              : "
        f"{row['engine_version']}"
    )


# =============================================================================
# RUNTIME CALLER / SQL CORRELATION
# =============================================================================

section(
    "STEP 11 — RUNTIME CALLER + SQL PARAMETER CORRELATION"
)


print(
    "NOTE                        : "
    "Static AST tracing cannot observe a runtime Python argument value "
    "unless the production caller exposes it through source-level construction."
)

print(
    "Therefore this section searches for:"
)

print(
    "  1. calculate_analysis caller"
)

print(
    "  2. rows construction"
)

print(
    "  3. SQL execution"
)

print(
    "  4. symbol filtering"
)

print(
    "  5. database assignment"
)


# =============================================================================
# SOURCE TEXT WINDOWS AROUND CALL SITES
# =============================================================================

lines = source.splitlines()

for index, call in enumerate(
    call_sites,
    start=1,
):

    line_no = node_line(call)

    if line_no is None:
        continue

    start = max(
        1,
        line_no - 25,
    )

    end = min(
        len(lines),
        line_no + 25,
    )

    print()
    print(
        f"[CALLER WINDOW {index}]"
    )

    print(
        f"LINES                       : "
        f"{start}-{end}"
    )

    for current in range(
        start,
        end + 1,
    ):

        marker = (
            ">>"
            if current == line_no
            else "  "
        )

        print(
            f"{marker} {current:04d}: "
            f"{lines[current - 1]}"
        )


# =============================================================================
# DATABASE ASSIGNMENT DISCOVERY
# =============================================================================

section(
    "STEP 12 — INDICATOR DATABASE ASSIGNMENT DISCOVERY"
)


INDICATOR_COLUMNS = {
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
}


assignment_hits = []

for node in ast.walk(tree):

    if not isinstance(
        node,
        ast.Subscript,
    ):
        continue

    text = source_segment(node)

    if not text:
        continue

    for column in INDICATOR_COLUMNS:

        if (
            f"['{column}']" in text
            or f'["{column}"]' in text
        ):

            assignment_hits.append(
                (
                    column,
                    node,
                )
            )


print(
    f"INDICATOR SUBSCRIPT REFERENCES: "
    f"{len(assignment_hits)}"
)


seen_assignment_lines = set()

for column, node in assignment_hits:

    line = node_line(node)

    key = (
        column,
        line,
    )

    if key in seen_assignment_lines:
        continue

    seen_assignment_lines.add(key)

    print(
        f"[INDICATOR REFERENCE]         "
        f"{column}"
    )

    print(
        f"LINE                        : "
        f"{line}"
    )

    print(
        f"SOURCE                      : "
        f"{source_segment(node).strip()}"
    )


# =============================================================================
# SQL WRITE-LIKE SOURCE DISCOVERY
# =============================================================================

section(
    "STEP 13 — PRODUCTION DATABASE ASSIGNMENT PATH DISCOVERY"
)


write_like_calls = []

for node in ast.walk(tree):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    if not isinstance(
        node.func,
        ast.Attribute,
    ):
        continue

    method = node.func.attr

    if method in {
        "execute",
        "executemany",
        "executescript",
    }:

        sql_text = ""

        if node.args:

            sql_text = source_segment(
                node.args[0]
            )

        normalized = normalize_sql(
            sql_text
        ).upper()

        if any(
            keyword in normalized
            for keyword in (
                "INSERT ",
                "UPDATE ",
                "REPLACE ",
            )
        ):

            write_like_calls.append(
                node
            )


print(
    f"WRITE-LIKE SQL CALLS          : "
    f"{len(write_like_calls)}"
)


for index, node in enumerate(
    write_like_calls,
    start=1,
):

    print()
    print(
        f"[WRITE-LIKE SQL SITE {index}]"
    )

    print(
        f"LINE                        : "
        f"{node_line(node)}"
    )

    print(
        f"SQL                         : "
        f"{normalize_sql(source_segment(node.args[0]))}"
    )

    if len(node.args) >= 2:

        print(
            f"PARAMETERS                  : "
            f"{normalize_sql(source_segment(node.args[1]))}"
        )

    else:

        print(
            "PARAMETERS                  : <NONE>"
        )


# =============================================================================
# TARGET SPECIFIC DB RECORD CONTEXT
# =============================================================================

section(
    "STEP 14 — TARGET DATABASE RECORD CONTEXT"
)


for symbol in TARGET_SYMBOLS:

    row = resolved_targets.get(
        symbol
    )

    if row is None:
        continue

    print()
    print(
        f"SYMBOL                      : {symbol}"
    )

    print(
        f"ID                          : {row['id']}"
    )

    print(
        f"TIMESTAMP                   : {row['timestamp']}"
    )

    print(
        f"SOURCE_TIMESTAMP            : {row['source_timestamp']}"
    )

    print(
        f"CLOSE                       : {row['close']}"
    )

    print(
        f"EMA20                       : {row['ema20']}"
    )

    print(
        f"EMA50                       : {row['ema50']}"
    )

    print(
        f"RSI14                       : {row['rsi14']}"
    )

    print(
        f"MACD                        : {row['macd']}"
    )

    print(
        f"MACD_SIGNAL                 : {row['macd_signal']}"
    )

    print(
        f"MACD_HIST                   : {row['macd_hist']}"
    )

    print(
        f"ATR14                       : {row['atr14']}"
    )

    print(
        f"ADX14                       : {row['adx14']}"
    )

    print(
        f"BB_MIDDLE                   : {row['bb_middle']}"
    )

    print(
        f"BB_UPPER                    : {row['bb_upper']}"
    )

    print(
        f"BB_LOWER                    : {row['bb_lower']}"
    )

    print(
        f"BB_WIDTH                    : {row['bb_width']}"
    )

    print(
        f"VOLUME_SMA20                : {row['volume_sma20']}"
    )

    print(
        f"VOLUME_RATIO                : {row['volume_ratio']}"
    )

    print(
        f"VOLATILITY                  : {row['volatility']}"
    )

    print(
        f"TECHNICAL_SCORE             : {row['technical_score']}"
    )


# =============================================================================
# FINAL FORENSIC MATRIX
# =============================================================================

section(
    "FINAL RUNTIME CALLER SQL PARAMETER ASSIGNMENT FORENSIC SUMMARY"
)


for symbol in TARGET_SYMBOLS:

    if symbol in resolved_targets:

        print(
            f"[STORED_TARGET_RESOLVED]     : "
            f"{symbol}"
        )

    else:

        print(
            f"[TARGET_MISSING]              : "
            f"{symbol}"
        )


print()
print(
    f"TARGETS REQUESTED            : "
    f"{len(TARGET_SYMBOLS)}"
)

print(
    f"TARGETS FOUND IN DATABASE    : "
    f"{len(resolved_targets)}"
)

print(
    f"CALCULATE_ANALYSIS CALLS     : "
    f"{len(call_sites)}"
)

print(
    f"SQL EXECUTION CALLS          : "
    f"{len(sql_calls)}"
)

print(
    f"WRITE-LIKE SQL CALLS         : "
    f"{len(write_like_calls)}"
)


# =============================================================================
# CONCLUSION
# =============================================================================

if len(call_sites) == 0:

    conclusion = (
        "RUNTIME_CALLER_NOT_FOUND"
    )

elif len(call_sites) == 1:

    conclusion = (
        "RUNTIME_CALLER_STATICALLY_RESOLVED"
    )

else:

    conclusion = (
        "MULTIPLE_RUNTIME_CALLERS_FOUND"
    )


print()
print(
    "FORENSIC CONCLUSION"
)

print(
    f"STATUS                       : "
    f"{conclusion}"
)

print(
    "MEANING                      : "
    "The script traced the production source path around "
    "calculate_analysis and identified SQL execution and "
    "parameter-expression sites without modifying production."
)

print(
    "IMPORTANT                    : "
    "Static source tracing does NOT prove the exact runtime "
    "Python object contents of dynamically constructed parameters."
)

print(
    "NEXT FRONTIER                : "
    "If the SQL parameter expressions remain dynamic, the next "
    "audit must instrument the actual runtime caller in memory "
    "without permitting database writes."
)

print()
print(
    "DATABASE WRITE OPERATIONS    : NONE"
)

print(
    "ENGINE MODIFICATIONS         : NONE"
)

print(
    "INSERT                       : NONE"
)

print(
    "UPDATE                       : NONE"
)

print(
    "DELETE                       : NONE"
)

print(
    "ALTER                        : NONE"
)

print(
    "CREATE                       : NONE"
)

print(
    "PRODUCTION RECALCULATION     : NONE"
)

print(
    "SQL MODE                     : READ ONLY"
)

print(
    f"ELAPSED SECONDS              : "
    f"{time.perf_counter() - START_TIME:.3f}"
)

print(
    "AUDIT COMPLETE"
)


# =============================================================================
# CLEAN CLOSE
# =============================================================================

connection.close()