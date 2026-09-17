import ast
import inspect
import os
import re
import runpy
import sqlite3
import sys
import time
import traceback
from pathlib import Path


# =============================================================================
# ARUNDA
# INDICATOR RUNTIME CALLER SQL PARAMETER ASSIGNMENT
# RUNTIME INSTRUMENTATION FORENSIC AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Trace the ACTUAL runtime caller path around calculate_analysis and capture:
#
#   1. Runtime calculate_analysis arguments
#   2. Runtime rows contents
#   3. Runtime production return value
#   4. Runtime SQL statements
#   5. Runtime SQL parameter tuples
#   6. Stored database indicator values
#   7. Runtime transformation / assignment evidence
#
# SAFETY
# ------
# READ ONLY
# No INSERT
# No UPDATE
# No DELETE
# No ALTER
# No CREATE
# No DROP
# No REPLACE
#
# Any write-like SQLite operation is BLOCKED by SQLite authorizer.
#
# IMPORTANT
# ---------
# This script does NOT repair anything.
# This script does NOT recalculate production data into the DB.
# This script does NOT modify market_data.
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

TARGET_TABLE = "market_data"

START = time.perf_counter()


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def sub_section(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=1000):
    try:
        text = repr(value)
    except Exception:
        text = "<UNREPRESENTABLE>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def rel_error(a, b):
    a = safe_float(a)
    b = safe_float(b)

    if a is None or b is None:
        return None

    denominator = max(abs(b), 1e-15)

    return abs(a - b) / denominator


# =============================================================================
# PATH VALIDATION
# =============================================================================

section("ARUNDA INDICATOR RUNTIME CALLER SQL PARAMETER ASSIGNMENT")
print("RUNTIME INSTRUMENTATION FORENSIC AUDIT v0.1")

print()
print("MODE                         : READ ONLY")
print("DATABASE WRITE               : BLOCKED")
print("ENGINE WRITE                 : NONE")
print("FORMULA WRITE                : NONE")
print("PRODUCTION RECALCULATION     : RUNTIME OBSERVATION ONLY")
print("PURPOSE                      : TRACE ACTUAL RUNTIME CALLER + SQL PARAMETERS")

if not ENGINE_PATH.exists():
    print()
    print("[FATAL] ENGINE NOT FOUND :", ENGINE_PATH)
    sys.exit(1)

if not DATABASE_PATH.exists():
    print()
    print("[FATAL] DATABASE NOT FOUND :", DATABASE_PATH)
    sys.exit(1)

print()
print("ENGINE PATH                 :", ENGINE_PATH)
print("ENGINE FOUND                :", True)
print("DATABASE PATH               :", DATABASE_PATH)
print("DATABASE FOUND              :", True)


# =============================================================================
# DATABASE AUTHORITATIVE READ-ONLY CONNECTION
# =============================================================================

section("STEP 1 — READ-ONLY DATABASE CONNECTION")

DB_URI = DATABASE_PATH.resolve().as_uri() + "?mode=ro"

try:
    db = sqlite3.connect(
        DB_URI,
        uri=True,
        check_same_thread=False,
    )

    db.row_factory = sqlite3.Row

    print("READ-ONLY CONNECTION        : SUCCESS")

except Exception as exc:
    print("READ-ONLY CONNECTION        : FAILED")
    print("ERROR                       :", repr(exc))
    sys.exit(1)


# =============================================================================
# SQLITE AUTHORITATIVE WRITE BLOCK
# =============================================================================

WRITE_ACTIONS = {
    getattr(sqlite3, "SQLITE_INSERT", -999),
    getattr(sqlite3, "SQLITE_UPDATE", -998),
    getattr(sqlite3, "SQLITE_DELETE", -997),
    getattr(sqlite3, "SQLITE_CREATE_INDEX", -996),
    getattr(sqlite3, "SQLITE_CREATE_TABLE", -995),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_INDEX", -994),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_TABLE", -993),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_TRIGGER", -992),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_VIEW", -991),
    getattr(sqlite3, "SQLITE_CREATE_TRIGGER", -990),
    getattr(sqlite3, "SQLITE_CREATE_VIEW", -989),
    getattr(sqlite3, "SQLITE_DROP_INDEX", -988),
    getattr(sqlite3, "SQLITE_DROP_TABLE", -987),
    getattr(sqlite3, "SQLITE_DROP_TEMP_INDEX", -986),
    getattr(sqlite3, "SQLITE_DROP_TEMP_TABLE", -985),
    getattr(sqlite3, "SQLITE_DROP_TEMP_TRIGGER", -984),
    getattr(sqlite3, "SQLITE_DROP_TEMP_VIEW", -983),
    getattr(sqlite3, "SQLITE_DROP_TRIGGER", -982),
    getattr(sqlite3, "SQLITE_DROP_VIEW", -981),
    getattr(sqlite3, "SQLITE_ALTER_TABLE", -980),
    getattr(sqlite3, "SQLITE_REINDEX", -979),
    getattr(sqlite3, "SQLITE_ANALYZE", -978),
    getattr(sqlite3, "SQLITE_CREATE_VTABLE", -977),
    getattr(sqlite3, "SQLITE_DROP_VTABLE", -976),
}


blocked_sql_operations = []


def sqlite_authorizer(action_code, arg1, arg2, db_name, trigger_name):
    if action_code in WRITE_ACTIONS:
        event = {
            "action_code": action_code,
            "arg1": arg1,
            "arg2": arg2,
            "db_name": db_name,
            "trigger_name": trigger_name,
        }

        blocked_sql_operations.append(event)

        print()
        print("[WRITE BLOCKED]")
        print("ACTION CODE                :", action_code)
        print("ARG1                       :", arg1)
        print("ARG2                       :", arg2)
        print("DATABASE                   :", db_name)
        print("TRIGGER                    :", trigger_name)

        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


db.set_authorizer(sqlite_authorizer)


# =============================================================================
# SQL RUNTIME TRACE
# =============================================================================

sql_runtime_trace = []


def sql_trace(statement):
    sql_runtime_trace.append(statement)

    normalized = re.sub(
        r"\s+",
        " ",
        statement.strip(),
    )

    print()
    print("[RUNTIME SQL]")
    print(normalized)


db.set_trace_callback(sql_trace)


# =============================================================================
# DATABASE TARGET RESOLUTION
# =============================================================================

section("STEP 2 — STORED TARGET RESOLUTION")

stored_targets = {}

placeholders = ",".join("?" for _ in TARGET_SYMBOLS)

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
ORDER BY symbol, id DESC
"""

rows_db = db.execute(
    query,
    TARGET_SYMBOLS,
).fetchall()

for row in rows_db:

    symbol = row["symbol"]

    if symbol not in stored_targets:
        stored_targets[symbol] = row

for symbol in TARGET_SYMBOLS:

    if symbol in stored_targets:
        row = stored_targets[symbol]

        print(
            f"[STORED_TARGET_RESOLVED]     : {symbol}"
        )

        print(
            f"  ID                       : {row['id']}"
        )

        print(
            f"  TIMESTAMP                : {row['timestamp']}"
        )

        print(
            f"  CLOSE                    : {row['close']}"
        )

        print(
            f"  ENGINE_VERSION           : {row['engine_version']}"
        )

    else:

        print(
            f"[MISSING_TARGET]           : {symbol}"
        )


# =============================================================================
# AST SOURCE ANALYSIS
# =============================================================================

section("STEP 3 — SOURCE / AST RUNTIME TARGET DISCOVERY")

source_text = ENGINE_PATH.read_text(
    encoding="utf-8",
)

print(
    "SOURCE SIZE                 :",
    len(source_text),
)

print(
    "SOURCE LINES                :",
    len(source_text.splitlines()),
)

try:
    tree = ast.parse(
        source_text,
        filename=str(ENGINE_PATH),
    )

    print("AST STATUS                  : SUCCESS")

except Exception as exc:

    print("AST STATUS                  : FAILED")
    print("ERROR                       :", repr(exc))

    db.close()
    sys.exit(1)


# =============================================================================
# FUNCTION MAP
# =============================================================================

function_defs = {}

for node in ast.walk(tree):

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

        function_defs[node.name] = node


print(
    "FUNCTIONS DISCOVERED        :",
    len(function_defs),
)


if "calculate_analysis" in function_defs:

    calc_node = function_defs["calculate_analysis"]

    print(
        "[FOUND] calculate_analysis LINE",
        f"{calc_node.lineno}-{getattr(calc_node, 'end_lineno', '?')}",
    )

else:

    print("[FATAL] calculate_analysis NOT FOUND")

    db.close()
    sys.exit(1)


# =============================================================================
# CALL-SITE DISCOVERY
# =============================================================================

call_sites = []


for node in ast.walk(tree):

    if isinstance(node, ast.Call):

        func_name = None

        if isinstance(node.func, ast.Name):

            func_name = node.func.id

        elif isinstance(node.func, ast.Attribute):

            func_name = node.func.attr

        if func_name == "calculate_analysis":

            call_sites.append(node)


print()
print(
    "CALCULATE_ANALYSIS CALL SITES:",
    len(call_sites),
)

for index, node in enumerate(call_sites, 1):

    print(
        f"[CALL SITE {index}] LINE {node.lineno}"
    )

    try:
        print(
            "  SOURCE:",
            ast.get_source_segment(
                source_text,
                node,
            ),
        )
    except Exception:
        pass


# =============================================================================
# RUNTIME OBSERVATION STATE
# =============================================================================

runtime_events = []

runtime_calculate_calls = []

runtime_sql_parameters = []

runtime_returns = []


# =============================================================================
# RUNTIME TRACE FUNCTION
# =============================================================================
#
# sys.settrace is intentionally used here.
#
# It observes Python frames without modifying function source.
#
# We only collect frames belonging to the production engine.
#
# =============================================================================

TRACE_ENGINE_FILE = str(
    ENGINE_PATH.resolve()
)


def summarize_rows(rows):

    result = {
        "type": type(rows).__name__,
        "count": None,
        "first": None,
        "last": None,
    }

    try:
        result["count"] = len(rows)
    except Exception:
        return result

    if result["count"]:

        try:
            first = rows[0]
            last = rows[-1]

            result["first"] = {
                "type": type(first).__name__,
                "repr": safe_repr(first, 1500),
            }

            result["last"] = {
                "type": type(last).__name__,
                "repr": safe_repr(last, 1500),
            }

        except Exception as exc:

            result["error"] = repr(exc)

    return result


def trace_runtime(frame, event, arg):

    try:

        filename = os.path.abspath(
            frame.f_code.co_filename
        )

        if filename != TRACE_ENGINE_FILE:
            return trace_runtime

        function_name = frame.f_code.co_name

        # ---------------------------------------------------------------------
        # ENTER calculate_analysis
        # ---------------------------------------------------------------------

        if function_name == "calculate_analysis" and event == "call":

            local_snapshot = dict(frame.f_locals)

            rows_value = local_snapshot.get(
                "rows"
            )

            event_record = {
                "event": "calculate_analysis_call",
                "filename": filename,
                "line": frame.f_lineno,
                "rows_summary": summarize_rows(
                    rows_value
                ),
            }

            runtime_calculate_calls.append(
                event_record
            )

            runtime_events.append(
                event_record
            )

            print()
            print(
                "[RUNTIME calculate_analysis CALL]"
            )

            print(
                "LINE                       :",
                frame.f_lineno,
            )

            print(
                "ROWS TYPE                  :",
                type(rows_value).__name__,
            )

            try:
                print(
                    "ROWS COUNT                 :",
                    len(rows_value),
                )
            except Exception:
                print(
                    "ROWS COUNT                 : UNKNOWN"
                )

            return trace_runtime

        # ---------------------------------------------------------------------
        # RETURN calculate_analysis
        # ---------------------------------------------------------------------

        if function_name == "calculate_analysis" and event == "return":

            record = {
                "event": "calculate_analysis_return",
                "filename": filename,
                "line": frame.f_lineno,
                "return_value": arg,
            }

            runtime_returns.append(record)
            runtime_events.append(record)

            print()
            print(
                "[RUNTIME calculate_analysis RETURN]"
            )

            print(
                "RETURN TYPE                :",
                type(arg).__name__,
            )

            print(
                "RETURN                    :",
                safe_repr(arg, 5000),
            )

            return trace_runtime

        # ---------------------------------------------------------------------
        # SQL PARAMETER / EXECUTE FUNCTIONS
        # ---------------------------------------------------------------------
        #
        # If production code calls sqlite execute indirectly, Python tracing
        # can still reveal the arguments when those calls are Python-level.
        #
        # sqlite3's native execute implementation itself is not always exposed
        # as a Python frame, therefore the SQLite trace callback above is the
        # authoritative SQL statement observation layer.
        # ---------------------------------------------------------------------

        if function_name in {
            "execute",
            "executemany",
            "executescript",
        }:

            local_snapshot = dict(frame.f_locals)

            record = {
                "event": function_name,
                "filename": filename,
                "line": frame.f_lineno,
                "locals": {
                    key: safe_repr(value, 1500)
                    for key, value in local_snapshot.items()
                    if key in {
                        "sql",
                        "query",
                        "statement",
                        "params",
                        "parameters",
                        "values",
                        "args",
                        "row",
                        "rows",
                    }
                },
            }

            runtime_sql_parameters.append(
                record
            )

            runtime_events.append(
                record
            )

            print()
            print(
                "[RUNTIME SQL PARAMETER FRAME]"
            )

            print(
                "FUNCTION                   :",
                function_name,
            )

            print(
                "LINE                       :",
                frame.f_lineno,
            )

            print(
                "LOCALS                     :",
                safe_repr(
                    record["locals"],
                    4000,
                ),
            )

    except Exception:
        # Forensic tracing must never interfere with production execution.
        pass

    return trace_runtime


# =============================================================================
# ENGINE IMPORT
# =============================================================================

section("STEP 4 — PRODUCTION ENGINE LOAD")

module_name = "arunda_market_data_engine_runtime_audit"

engine_module = None

try:

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        module_name,
        ENGINE_PATH,
    )

    engine_module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[module_name] = engine_module

    # IMPORTANT:
    # We do not execute calculate_analysis manually here.
    # We only load the production module so its real caller can be observed
    # if the module itself executes a runtime path during import.
    #
    # Runtime tracing starts immediately before exec_module.

    sys.settrace(trace_runtime)

    spec.loader.exec_module(
        engine_module
    )

    sys.settrace(None)

    print(
        "ENGINE LOAD                : SUCCESS"
    )

except Exception as exc:

    sys.settrace(None)

    print(
        "ENGINE LOAD                : FAILED"
    )

    print(
        "ERROR                      :",
        repr(exc),
    )

    print()
    traceback.print_exc()

    db.close()
    sys.exit(1)


# =============================================================================
# CHECK FOR PRODUCTION FUNCTION
# =============================================================================

section("STEP 5 — RUNTIME FUNCTION AVAILABILITY")

if not hasattr(
    engine_module,
    "calculate_analysis",
):

    print(
        "[MISSING] calculate_analysis"
    )

else:

    print(
        "[FOUND] calculate_analysis"
    )

    try:

        function_object = getattr(
            engine_module,
            "calculate_analysis",
        )

        print(
            "FUNCTION                   :",
            function_object,
        )

        print(
            "MODULE                     :",
            getattr(
                function_object,
                "__module__",
                None,
            ),
        )

        print(
            "QUALNAME                   :",
            getattr(
                function_object,
                "__qualname__",
                None,
            ),
        )

    except Exception as exc:

        print(
            "FUNCTION INSPECTION ERROR  :",
            repr(exc),
        )


# =============================================================================
# RUNTIME CALL RESULT
# =============================================================================

section("STEP 6 — ACTUAL RUNTIME CALL OBSERVATION")

print(
    "CALCULATE_ANALYSIS CALLS OBSERVED:",
    len(runtime_calculate_calls),
)

if not runtime_calculate_calls:

    print()
    print(
        "[IMPORTANT]"
    )

    print(
        "No actual calculate_analysis runtime invocation was observed during"
    )

    print(
        "module loading."
    )

    print()
    print(
        "This means the real production caller is outside the import-time"
    )

    print(
        "execution path and must be invoked by the production runtime."
    )

    print()
    print(
        "The audit therefore does NOT fabricate a runtime call."
    )

else:

    for index, event in enumerate(
        runtime_calculate_calls,
        1,
    ):

        print()
        print(
            f"[RUNTIME CALL {index}]"
        )

        print(
            "LINE                       :",
            event["line"],
        )

        print(
            "ROWS SUMMARY               :",
            safe_repr(
                event["rows_summary"],
                4000,
            ),
        )


# =============================================================================
# RUNTIME RETURN OBSERVATION
# =============================================================================

section("STEP 7 — PRODUCTION RETURN OBSERVATION")

print(
    "RUNTIME RETURNS OBSERVED    :",
    len(runtime_returns),
)

for index, event in enumerate(
    runtime_returns,
    1,
):

    print()
    print(
        f"[RETURN {index}]"
    )

    print(
        "RETURN TYPE                :",
        type(
            event["return_value"]
        ).__name__,
    )

    print(
        "RETURN                     :",
        safe_repr(
            event["return_value"],
            8000,
        ),
    )


# =============================================================================
# SQL PARAMETER OBSERVATION
# =============================================================================

section("STEP 8 — RUNTIME SQL PARAMETER OBSERVATION")

print(
    "SQL EXECUTION TRACE COUNT   :",
    len(sql_runtime_trace),
)

print(
    "PYTHON SQL PARAMETER FRAMES :",
    len(runtime_sql_parameters),
)

print(
    "BLOCKED WRITE OPERATIONS    :",
    len(blocked_sql_operations),
)

for index, item in enumerate(
    runtime_sql_parameters,
    1,
):

    print()
    print(
        f"[SQL PARAMETER FRAME {index}]"
    )

    print(
        "FUNCTION                   :",
        item["event"],
    )

    print(
        "LINE                       :",
        item["line"],
    )

    print(
        "LOCALS                     :",
        safe_repr(
            item["locals"],
            5000,
        ),
    )


# =============================================================================
# SQL TRACE OUTPUT
# =============================================================================

section("STEP 9 — RUNTIME SQL STATEMENT TRACE")

for index, statement in enumerate(
    sql_runtime_trace,
    1,
):

    print(
        f"[SQL {index}]",
        statement,
    )


# =============================================================================
# STORED TARGET FINAL SNAPSHOT
# =============================================================================

section("STEP 10 — STORED TARGET SNAPSHOT")

for symbol in TARGET_SYMBOLS:

    row = stored_targets.get(symbol)

    if row is None:
        print(
            f"[MISSING] {symbol}"
        )
        continue

    print()
    print(
        f"SYMBOL : {symbol}"
    )

    for indicator in TARGET_INDICATORS:

        try:
            value = row[indicator]
        except Exception:
            value = None

        print(
            f"  {indicator:<20} : {value}"
        )


# =============================================================================
# RETURN VS STORED COMPARISON
# =============================================================================

section("STEP 11 — RUNTIME RETURN VS STORED VALUE")

comparison_count = 0
comparison_matches = 0
comparison_differences = 0


for event in runtime_returns:

    result = event["return_value"]

    if not isinstance(
        result,
        dict,
    ):
        continue

    symbol = None

    # Production calculate_analysis does not necessarily return symbol.
    #
    # Therefore identify symbol through close/timestamp when possible.
    #
    # We intentionally do not invent identity.

    timestamp = result.get(
        "timestamp"
    )

    close_value = result.get(
        "close"
    )

    candidate_symbols = []

    for target_symbol, stored_row in stored_targets.items():

        same_timestamp = (
            timestamp is not None
            and stored_row["timestamp"] == timestamp
        )

        same_close = (
            close_value is not None
            and safe_float(
                stored_row["close"]
            ) is not None
            and abs(
                safe_float(
                    stored_row["close"]
                )
                - safe_float(
                    close_value
                )
            ) <= max(
                abs(
                    safe_float(
                        stored_row["close"]
                    )
                ) * 1e-12,
                1e-12,
            )
        )

        if same_timestamp or same_close:

            candidate_symbols.append(
                target_symbol
            )

    if len(candidate_symbols) != 1:

        print()
        print(
            "[RUNTIME_RETURN_IDENTITY_UNRESOLVED]"
        )

        print(
            "TIMESTAMP                  :",
            timestamp,
        )

        print(
            "CLOSE                      :",
            close_value,
        )

        print(
            "CANDIDATES                 :",
            candidate_symbols,
        )

        continue

    symbol = candidate_symbols[0]

    stored_row = stored_targets[symbol]

    print()
    print(
        f"SYMBOL : {symbol}"
    )

    for indicator in TARGET_INDICATORS:

        if indicator not in result:
            continue

        stored_value = stored_row[indicator]
        runtime_value = result.get(indicator)

        comparison_count += 1

        if (
            stored_value is None
            and runtime_value is None
        ):

            comparison_matches += 1

            print(
                f"{indicator:<20} MATCH | both NULL"
            )

            continue

        if (
            stored_value is None
            or runtime_value is None
        ):

            comparison_differences += 1

            print(
                f"{indicator:<20} DIFFERENCE | "
                f"STORED={stored_value} | "
                f"RUNTIME={runtime_value}"
            )

            continue

        abs_err = abs(
            float(runtime_value)
            - float(stored_value)
        )

        rel_err = rel_error(
            runtime_value,
            stored_value,
        )

        if abs_err == 0:

            comparison_matches += 1

            status = "MATCH"

        else:

            comparison_differences += 1

            status = "DIFFERENCE"

        print(
            f"{indicator:<20} {status} | "
            f"STORED={stored_value} | "
            f"RUNTIME={runtime_value} | "
            f"ABS={abs_err} | "
            f"REL={rel_err}"
        )


# =============================================================================
# STATIC ASSIGNMENT TRANSFORMATION SEARCH
# =============================================================================

section("STEP 12 — POST-CALCULATION ASSIGNMENT TRACE")

assignment_hits = []


for node in ast.walk(tree):

    if isinstance(
        node,
        ast.Assign,
    ):

        source = None

        try:
            source = ast.get_source_segment(
                source_text,
                node,
            )
        except Exception:
            pass

        if source and any(
            indicator in source
            for indicator in TARGET_INDICATORS
        ):

            assignment_hits.append(
                (
                    node.lineno,
                    source.strip(),
                )
            )


for lineno, source in sorted(
    assignment_hits,
    key=lambda x: x[0],
):

    print(
        f"[ASSIGNMENT] LINE {lineno} : {source}"
    )


# =============================================================================
# WRITE SAFETY VERIFICATION
# =============================================================================

section("STEP 13 — WRITE SAFETY VERIFICATION")

print(
    "DATABASE CONNECTION MODE    : READ ONLY"
)

print(
    "SQLITE AUTHORITATIVE BLOCK  : ENABLED"
)

print(
    "BLOCKED WRITE OPERATIONS    :",
    len(blocked_sql_operations),
)

if blocked_sql_operations:

    print()
    print(
        "[WARNING]"
    )

    print(
        "A production path attempted a write-like SQLite operation."
    )

    print(
        "The operation was BLOCKED."
    )

else:

    print(
        "WRITE ATTEMPTS              : NONE OBSERVED"
    )


# =============================================================================
# FINAL CLASSIFICATION
# =============================================================================

section(
    "FINAL RUNTIME CALLER SQL PARAMETER ASSIGNMENT FORENSIC SUMMARY"
)


print(
    "TARGETS REQUESTED            :",
    len(TARGET_SYMBOLS),
)

print(
    "TARGETS FOUND IN DATABASE    :",
    len(stored_targets),
)

print(
    "CALCULATE_ANALYSIS CALLS     :",
    len(runtime_calculate_calls),
)

print(
    "RUNTIME RETURNS              :",
    len(runtime_returns),
)

print(
    "SQL EXECUTION TRACE COUNT    :",
    len(sql_runtime_trace),
)

print(
    "PYTHON SQL PARAMETER FRAMES  :",
    len(runtime_sql_parameters),
)

print(
    "BLOCKED WRITE-LIKE OPERATIONS:",
    len(blocked_sql_operations),
)

print()
print("TARGET MATRIX")

for symbol in TARGET_SYMBOLS:

    if symbol in stored_targets:

        print(
            f"[STORED_TARGET_RESOLVED]     : {symbol}"
        )

    else:

        print(
            f"[STORED_TARGET_MISSING]      : {symbol}"
        )


# =============================================================================
# CONCLUSION LOGIC
# =============================================================================

if len(runtime_calculate_calls) > 0:

    if len(runtime_sql_parameters) > 0:

        final_status = (
            "RUNTIME_CALLER_AND_SQL_PARAMETER_RUNTIME_TRACE_OBSERVED"
        )

        final_meaning = (
            "Actual runtime calculate_analysis invocation and runtime "
            "SQL parameter frames were observed."
        )

    else:

        final_status = (
            "RUNTIME_CALLER_OBSERVED_SQL_PARAMETER_RUNTIME_FRAME_UNRESOLVED"
        )

        final_meaning = (
            "Actual runtime calculate_analysis invocation was observed, "
            "but Python-level SQL parameter frames were not exposed."
        )

else:

    final_status = (
        "RUNTIME_CALLER_NOT_EXECUTED_DURING_AUDIT_IMPORT_PATH"
    )

    final_meaning = (
        "The actual production caller was not invoked during module import; "
        "therefore no runtime caller contents were fabricated."
    )


print()
print(
    "FORENSIC CONCLUSION"
)

print(
    "STATUS                       :",
    final_status,
)

print(
    "MEANING                      :",
    final_meaning,
)

print(
    "IMPORTANT                    : "
    "No runtime object contents are inferred when they were not observed."
)

print(
    "NEXT FRONTIER                : "
    "If runtime caller was not observed, invoke the exact production "
    "entry-point under the same read-only instrumentation and capture "
    "the actual rows object + SQL parameter tuple."
)

print()
print(
    "DATABASE WRITE OPERATIONS    : NONE"
)

print(
    "ENGINE MODIFICATIONS        : NONE"
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
    "DROP                         : NONE"
)

print(
    "SQL MODE                     : READ ONLY"
)

print(
    "WRITE BLOCKER                : ENABLED"
)

print(
    "ELAPSED SECONDS              :",
    round(
        time.perf_counter() - START,
        3,
    ),
)

print(
    "AUDIT COMPLETE"
)


# =============================================================================
# CLOSE DATABASE
# =============================================================================

try:
    db.set_trace_callback(None)
except Exception:
    pass

try:
    db.set_authorizer(None)
except Exception:
    pass

db.close()