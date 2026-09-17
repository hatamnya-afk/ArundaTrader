import ast
import importlib.util
import os
import sqlite3
import sys
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA
# INDICATOR CALCULATE OUTPUT VS STORED ASSIGNMENT
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Trace and compare:
#
#   REAL production calculate_analysis() output
#           ↓
#   REAL save_analysis() assignment argument
#           ↓
#   STORED market_data row
#
# This audit does NOT modify production code.
# This audit does NOT execute production save_analysis().
# This audit does NOT write to the database.
#
# READ ONLY
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENGINE_FILE = os.path.join(
    PROJECT_DIR,
    "market_data_engine.py"
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "arunda.db"
)

MODULE_NAME = (
    "arunda_market_data_engine_assignment_forensic_v01"
)

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

ANALYSIS_SOURCE = (
    "CMC_SNAPSHOT_ANALYSIS_v0.2"
)

ANALYSIS_TIMEFRAME = (
    "SNAPSHOT"
)


# ============================================================
# FORENSIC STATE
# ============================================================

calculate_calls = []

runtime_returns = defaultdict(list)

runtime_save_arguments = defaultdict(list)

runtime_exceptions = []

sql_trace = []

blocked_writes = []

entrypoint_status = {
    "executed": False,
    "exception": None,
}


# ============================================================
# COMPARISON FIELDS
# ============================================================

COMPARE_FIELDS = [
    "timestamp",
    "source_timestamp",
    "close",
    "volume",
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
    "price_change_1h",
    "price_change_24h",
    "market_cap",
    "volume_24h",
    "source_latency_ms",
]


# ============================================================
# OUTPUT HELPERS
# ============================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=1500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return (
            text[:limit]
            + "...<TRUNCATED>"
        )

    return text


# ============================================================
# PATH SAFETY
# ============================================================

def verify_paths():

    section(
        "STEP 1 — PATH SAFETY RESOLUTION"
    )

    print(
        "PROJECT PATH                 : "
        f"{PROJECT_DIR}"
    )

    print(
        "ENGINE PATH                  : "
        f"{ENGINE_FILE}"
    )

    print(
        "ENGINE FOUND                 : "
        f"{os.path.isfile(ENGINE_FILE)}"
    )

    print(
        "DATABASE PATH                : "
        f"{DB_FILE}"
    )

    print(
        "DATABASE FOUND               : "
        f"{os.path.isfile(DB_FILE)}"
    )

    if not os.path.isfile(
        ENGINE_FILE
    ):
        raise FileNotFoundError(
            f"Production engine not found: {ENGINE_FILE}"
        )

    if not os.path.isfile(
        DB_FILE
    ):
        raise FileNotFoundError(
            f"Database not found: {DB_FILE}"
        )


# ============================================================
# STATIC PRODUCTION SOURCE AUDIT
# ============================================================

def inspect_engine_source():

    section(
        "STEP 2 — PRODUCTION SOURCE RESOLUTION"
    )

    with open(
        ENGINE_FILE,
        "r",
        encoding="utf-8"
    ) as handle:

        source = handle.read()

    tree = ast.parse(
        source,
        filename=ENGINE_FILE
    )

    calculate_defs = []
    save_defs = []
    main_defs = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            if node.name == "calculate_analysis":
                calculate_defs.append(node)

            elif node.name == "save_analysis":
                save_defs.append(node)

            elif node.name == "main":
                main_defs.append(node)

    print(
        "calculate_analysis definitions : "
        f"{len(calculate_defs)}"
    )

    print(
        "save_analysis definitions      : "
        f"{len(save_defs)}"
    )

    print(
        "main definitions               : "
        f"{len(main_defs)}"
    )

    if calculate_defs:
        print(
            "calculate_analysis line        : "
            f"{calculate_defs[0].lineno}"
        )

    if save_defs:
        print(
            "save_analysis line             : "
            f"{save_defs[0].lineno}"
        )

    if main_defs:
        print(
            "main line                      : "
            f"{main_defs[0].lineno}"
        )

    if not calculate_defs:
        raise RuntimeError(
            "calculate_analysis() not found"
        )

    if not save_defs:
        raise RuntimeError(
            "save_analysis() not found"
        )

    if not main_defs:
        raise RuntimeError(
            "main() not found"
        )


# ============================================================
# READ-ONLY SQLITE
# ============================================================

def open_read_only_database():

    uri = (
        "file:"
        + DB_FILE.replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# SQL CLASSIFICATION
# ============================================================

WRITE_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)


def classify_sql(sql):

    if sql is None:
        return False

    normalized = " ".join(
        str(sql)
        .strip()
        .upper()
        .split()
    )

    if not normalized:
        return False

    return normalized.startswith(
        WRITE_PREFIXES
    )


# ============================================================
# FORENSIC CONNECTION
# ============================================================

class ForensicCursor:

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(
        self,
        sql,
        parameters=()
    ):

        write_like = classify_sql(
            sql
        )

        event = {
            "sql": str(sql),
            "parameters": parameters,
            "write_like": write_like,
        }

        sql_trace.append(
            event
        )

        if write_like:

            blocked_writes.append(
                event
            )

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL blocked"
            )

        return self._cursor.execute(
            sql,
            parameters
        )

    def executemany(
        self,
        sql,
        parameters
    ):

        write_like = classify_sql(
            sql
        )

        event = {
            "sql": str(sql),
            "parameters": "<executemany>",
            "write_like": write_like,
        }

        sql_trace.append(
            event
        )

        if write_like:

            blocked_writes.append(
                event
            )

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL blocked"
            )

        return self._cursor.executemany(
            sql,
            parameters
        )

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size=None):

        if size is None:
            return self._cursor.fetchmany()

        return self._cursor.fetchmany(
            size
        )

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(
            self._cursor
        )

    def __getattr__(self, name):
        return getattr(
            self._cursor,
            name
        )


class ForensicConnection:

    def __init__(self, connection):
        self._connection = connection

    def execute(
        self,
        sql,
        parameters=()
    ):

        cursor = ForensicCursor(
            self._connection.cursor()
        )

        cursor.execute(
            sql,
            parameters
        )

        return cursor

    def cursor(self):

        return ForensicCursor(
            self._connection.cursor()
        )

    def commit(self):

        return None

    def rollback(self):

        return None

    def close(self):

        return self._connection.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback_value
    ):

        self.close()

        return False

    def __getattr__(self, name):
        return getattr(
            self._connection,
            name
        )


def forensic_connection_factory():

    connection = (
        open_read_only_database()
    )

    return ForensicConnection(
        connection
    )


# ============================================================
# VALUE NORMALIZATION
# ============================================================

def normalize_value(value):

    if isinstance(
        value,
        dict
    ):
        return dict(value)

    if isinstance(
        value,
        sqlite3.Row
    ):
        return {
            key: value[key]
            for key in value.keys()
        }

    return value


def normalize_mapping(value):

    if value is None:
        return None

    if isinstance(
        value,
        dict
    ):
        return dict(value)

    if isinstance(
        value,
        sqlite3.Row
    ):
        return {
            key: value[key]
            for key in value.keys()
        }

    try:
        return dict(value)

    except Exception:
        return None


# ============================================================
# FLOAT COMPARISON
# ============================================================

def values_equal(
    left,
    right,
    absolute_tolerance=1e-12,
    relative_tolerance=1e-9
):

    if left is None and right is None:
        return True

    if left is None or right is None:
        return False

    if isinstance(
        left,
        bool
    ) or isinstance(
        right,
        bool
    ):

        return left == right

    if isinstance(
        left,
        (int, float)
    ) and isinstance(
        right,
        (int, float)
    ):

        difference = abs(
            float(left)
            - float(right)
        )

        scale = max(
            abs(float(left)),
            abs(float(right)),
            1.0
        )

        return (
            difference
            <= absolute_tolerance
            + relative_tolerance * scale
        )

    return left == right


# ============================================================
# ROW / SYMBOL HELPERS
# ============================================================

def row_to_dict(row):

    if isinstance(
        row,
        sqlite3.Row
    ):

        return {
            key: row[key]
            for key in row.keys()
        }

    if isinstance(
        row,
        dict
    ):

        return dict(row)

    try:
        return dict(row)

    except Exception:

        return {
            "_repr": safe_repr(row)
        }


def snapshot_rows(rows):

    if rows is None:

        return {
            "type": "None",
            "count": 0,
            "rows": [],
        }

    try:

        materialized = list(
            rows
        )

    except Exception:

        return {
            "type": type(rows).__name__,
            "count": None,
            "rows": [],
            "error":
                traceback.format_exc(),
        }

    result = []

    for row in materialized:

        result.append(
            row_to_dict(row)
        )

    return {
        "type": type(rows).__name__,
        "count": len(result),
        "rows": result,
    }


def infer_symbol_from_rows(rows):

    if not rows:
        return None

    first = rows[0]

    try:

        if isinstance(
            first,
            dict
        ):

            return first.get(
                "symbol"
            )

        return first["symbol"]

    except Exception:

        return None


def extract_symbol_from_save(
    args,
    kwargs
):

    if "symbol" in kwargs:
        return kwargs["symbol"]

    if len(args) >= 2:
        return args[1]

    return None


def extract_analysis_from_save(
    args,
    kwargs
):

    if "analysis" in kwargs:
        return kwargs["analysis"]

    if len(args) >= 3:
        return args[2]

    return None


# ============================================================
# PRODUCTION MODULE IMPORT
# ============================================================

def import_production_module():

    section(
        "STEP 3 — PRODUCTION ENGINE IMPORT"
    )

    spec = (
        importlib.util.spec_from_file_location(
            MODULE_NAME,
            ENGINE_FILE
        )
    )

    if spec is None:
        raise RuntimeError(
            "Could not create production module spec"
        )

    if spec.loader is None:
        raise RuntimeError(
            "Production module loader unavailable"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    print(
        "MODULE IMPORTED              : "
        f"{MODULE_NAME}"
    )

    return module


# ============================================================
# INSTALL RUNTIME OBSERVERS
# ============================================================

def install_runtime_observers(
    module
):

    section(
        "STEP 4 — RUNTIME OBSERVER INSTALLATION"
    )

    original_calculate = (
        module.calculate_analysis
    )

    original_save = (
        module.save_analysis
    )

    original_connect = (
        module.connect_database
    )

    original_schema = (
        module.ensure_schema
    )

    print(
        "ORIGINAL calculate_analysis    : FOUND"
    )

    print(
        "ORIGINAL save_analysis         : FOUND"
    )

    print(
        "ORIGINAL connect_database      : FOUND"
    )

    print(
        "ORIGINAL ensure_schema         : FOUND"
    )

    def forensic_calculate_analysis(
        rows
    ):

        call_index = (
            len(calculate_calls)
            + 1
        )

        snapshot = (
            snapshot_rows(rows)
        )

        symbol = (
            infer_symbol_from_rows(
                snapshot["rows"]
            )
        )

        if symbol is None:
            symbol = "UNKNOWN"

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "row_count": snapshot["count"],
            "rows": snapshot["rows"],
        }

        calculate_calls.append(
            event
        )

        print()
        print(
            "[CALCULATE_ANALYSIS INPUT]"
        )

        print(
            f"CALL INDEX : {call_index}"
        )

        print(
            f"SYMBOL     : {symbol}"
        )

        print(
            f"ROW COUNT  : {snapshot['count']}"
        )

        try:

            result = (
                original_calculate(
                    rows
                )
            )

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "stage":
                        "calculate_analysis",
                    "symbol":
                        symbol,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            print(
                "[CALCULATE_ANALYSIS EXCEPTION]"
            )

            print(
                repr(exc)
            )

            raise

        event = {
            "call_index": call_index,
            "symbol": symbol,
            "result": result,
            "result_type":
                type(result).__name__,
        }

        runtime_returns[
            symbol
        ].append(
            event
        )

        print(
            "[CALCULATE_ANALYSIS RETURN]"
        )

        print(
            f"RESULT TYPE : "
            f"{type(result).__name__}"
        )

        print(
            f"RESULT      : "
            f"{safe_repr(result)}"
        )

        return result

    def forensic_save_analysis(
        *args,
        **kwargs
    ):

        symbol = (
            extract_symbol_from_save(
                args,
                kwargs
            )
        )

        analysis = (
            extract_analysis_from_save(
                args,
                kwargs
            )
        )

        event = {
            "symbol": symbol,
            "analysis": analysis,
            "analysis_type":
                type(analysis).__name__,
        }

        runtime_save_arguments[
            symbol or "UNKNOWN"
        ].append(
            event
        )

        print()
        print(
            "[SAVE_ANALYSIS ASSIGNMENT OBSERVED]"
        )

        print(
            f"SYMBOL   : {symbol}"
        )

        print(
            f"ANALYSIS : "
            f"{safe_repr(analysis)}"
        )

        # CRITICAL:
        #
        # NEVER call original_save().
        #
        # This prevents INSERT.
        #

        return False

    def forensic_connect_database():

        return (
            forensic_connection_factory()
        )

    def forensic_ensure_schema(
        conn
    ):

        print(
            "[ENSURE_SCHEMA] "
            "BYPASSED — READ-ONLY FORENSIC"
        )

        return None

    module.calculate_analysis = (
        forensic_calculate_analysis
    )

    module.save_analysis = (
        forensic_save_analysis
    )

    module.connect_database = (
        forensic_connect_database
    )

    module.ensure_schema = (
        forensic_ensure_schema
    )

    module._forensic_original_calculate = (
        original_calculate
    )

    module._forensic_original_save = (
        original_save
    )

    module._forensic_original_connect = (
        original_connect
    )

    module._forensic_original_schema = (
        original_schema
    )

    print(
        "PATCHED calculate_analysis    : OBSERVER"
    )

    print(
        "PATCHED save_analysis          : OBSERVER ONLY"
    )

    print(
        "PATCHED connect_database       : READ ONLY"
    )

    print(
        "PATCHED ensure_schema          : BYPASSED"
    )


# ============================================================
# RESOLVE TARGETS
# ============================================================

def resolve_targets():

    section(
        "STEP 5 — TARGET RESOLUTION"
    )

    conn = open_read_only_database()

    resolved = []

    try:

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT
                    symbol,
                    COUNT(*) AS row_count
                FROM market_data
                WHERE symbol = ?
                GROUP BY symbol
                LIMIT 1
                """,
                (symbol,)
            ).fetchone()

            if row is None:

                print(
                    f"{symbol:<6} | NOT FOUND"
                )

                continue

            resolved.append(
                symbol
            )

            print(
                f"{symbol:<6} | FOUND | "
                f"ROWS={row['row_count']}"
            )

    finally:

        conn.close()

    return resolved


# ============================================================
# EXECUTE REAL PRODUCTION MAIN
# ============================================================

def execute_production_main(
    module
):

    section(
        "STEP 6 — ACTUAL PRODUCTION MAIN EXECUTION"
    )

    print(
        "MODE                       : READ ONLY"
    )

    print(
        "PRODUCTION FUNCTIONS       : ORIGINAL"
    )

    print(
        "DATABASE WRITES            : BLOCKED"
    )

    entrypoint_status[
        "executed"
    ] = True

    try:

        result = module.main()

        print()

        print(
            "[PRODUCTION MAIN RETURN]"
        )

        print(
            f"RETURN : {safe_repr(result)}"
        )

        return result

    except Exception as exc:

        entrypoint_status[
            "exception"
        ] = repr(exc)

        runtime_exceptions.append(
            {
                "stage":
                    "main",
                "exception":
                    repr(exc),
                "traceback":
                    traceback.format_exc(),
            }
        )

        print()

        print(
            "[PRODUCTION MAIN EXCEPTION]"
        )

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        return None


# ============================================================
# STORED ROW RESOLUTION
# ============================================================

def get_stored_analysis_row(
    symbol,
    source_timestamp
):

    conn = open_read_only_database()

    try:

        if source_timestamp is not None:

            row = conn.execute(
                """
                SELECT *
                FROM market_data
                WHERE
                    symbol = ?
                    AND timeframe = ?
                    AND source = ?
                    AND source_timestamp = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    symbol,
                    ANALYSIS_TIMEFRAME,
                    ANALYSIS_SOURCE,
                    source_timestamp,
                )
            ).fetchone()

            if row is not None:
                return row_to_dict(row)

        row = conn.execute(
            """
            SELECT *
            FROM market_data
            WHERE
                symbol = ?
                AND timeframe = ?
                AND source = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                symbol,
                ANALYSIS_TIMEFRAME,
                ANALYSIS_SOURCE,
            )
        ).fetchone()

        if row is None:
            return None

        return row_to_dict(row)

    finally:

        conn.close()


# ============================================================
# ASSIGNMENT VS STORED COMPARISON
# ============================================================

def compare_mapping_to_stored(
    symbol,
    runtime_mapping,
    stored_mapping
):

    differences = []

    if runtime_mapping is None:

        return {
            "status":
                "RUNTIME_ASSIGNMENT_MISSING",
            "differences": [],
        }

    if stored_mapping is None:

        return {
            "status":
                "STORED_ROW_MISSING",
            "differences": [],
        }

    for field in COMPARE_FIELDS:

        runtime_value = (
            runtime_mapping.get(
                field
            )
        )

        stored_value = (
            stored_mapping.get(
                field
            )
        )

        if not values_equal(
            runtime_value,
            stored_value
        ):

            differences.append(
                {
                    "field": field,
                    "runtime":
                        runtime_value,
                    "stored":
                        stored_value,
                }
            )

    if differences:

        return {
            "status":
                "DIVERGENCE",
            "differences":
                differences,
        }

    return {
        "status":
            "EXACT_MATCH",
        "differences": [],
    }


# ============================================================
# TARGET FORENSIC ANALYSIS
# ============================================================

def analyze_target(
    symbol
):

    section(
        f"TARGET FORENSIC : {symbol}"
    )

    returns = (
        runtime_returns.get(
            symbol,
            []
        )
    )

    saves = (
        runtime_save_arguments.get(
            symbol,
            []
        )
    )

    print(
        f"CALCULATE RETURNS : "
        f"{len(returns)}"
    )

    print(
        f"SAVE ASSIGNMENTS  : "
        f"{len(saves)}"
    )

    if not returns:

        print(
            "STATUS : NO_RUNTIME_RETURN"
        )

        return {
            "status":
                "NO_RUNTIME_RETURN",
            "symbol":
                symbol,
        }

    if not saves:

        print(
            "STATUS : NO_SAVE_ASSIGNMENT"
        )

        return {
            "status":
                "NO_SAVE_ASSIGNMENT",
            "symbol":
                symbol,
        }

    runtime_event = returns[-1]

    save_event = saves[-1]

    runtime_result = (
        normalize_mapping(
            runtime_event["result"]
        )
    )

    save_analysis = (
        normalize_mapping(
            save_event["analysis"]
        )
    )

    print()
    print(
        "RUNTIME CALCULATE OUTPUT"
    )

    print(
        safe_repr(runtime_result)
    )

    print()
    print(
        "SAVE ASSIGNMENT"
    )

    print(
        safe_repr(save_analysis)
    )

    if runtime_result is None:

        print(
            "STATUS : RUNTIME_RETURN_NOT_MAPPING"
        )

        return {
            "status":
                "RUNTIME_RETURN_NOT_MAPPING",
            "symbol":
                symbol,
        }

    if save_analysis is None:

        print(
            "STATUS : SAVE_ASSIGNMENT_NOT_MAPPING"
        )

        return {
            "status":
                "SAVE_ASSIGNMENT_NOT_MAPPING",
            "symbol":
                symbol,
        }

    # --------------------------------------------------------
    # First comparison:
    #
    # calculate_analysis return
    #             VS
    # save_analysis assignment
    #
    # --------------------------------------------------------

    runtime_vs_assignment = (
        compare_mapping_to_stored(
            symbol,
            runtime_result,
            save_analysis
        )
    )

    print()
    print(
        "CALCULATE OUTPUT VS SAVE ASSIGNMENT"
    )

    print(
        f"STATUS : "
        f"{runtime_vs_assignment['status']}"
    )

    if runtime_vs_assignment[
        "differences"
    ]:

        for difference in (
            runtime_vs_assignment[
                "differences"
            ]
        ):

            print(
                f"FIELD={difference['field']}"
            )

            print(
                f"  RUNTIME : "
                f"{safe_repr(difference['runtime'])}"
            )

            print(
                f"  ASSIGN  : "
                f"{safe_repr(difference['stored'])}"
            )

    source_timestamp = (
        save_analysis.get(
            "source_timestamp"
        )
    )

    stored = (
        get_stored_analysis_row(
            symbol,
            source_timestamp
        )
    )

    print()
    print(
        "STORED MARKET_DATA ROW"
    )

    print(
        safe_repr(stored)
    )

    assignment_vs_stored = (
        compare_mapping_to_stored(
            symbol,
            save_analysis,
            stored
        )
    )

    print()
    print(
        "SAVE ASSIGNMENT VS STORED ROW"
    )

    print(
        f"STATUS : "
        f"{assignment_vs_stored['status']}"
    )

    if assignment_vs_stored[
        "differences"
    ]:

        print()
        print(
            "DIVERGENT FIELDS"
        )

        for difference in (
            assignment_vs_stored[
                "differences"
            ]
        ):

            print(
                f"FIELD={difference['field']}"
            )

            print(
                f"  ASSIGN : "
                f"{safe_repr(difference['runtime'])}"
            )

            print(
                f"  STORED : "
                f"{safe_repr(difference['stored'])}"
            )

    # --------------------------------------------------------
    # Determine first divergence.
    # --------------------------------------------------------

    if runtime_vs_assignment[
        "differences"
    ]:

        first = (
            runtime_vs_assignment[
                "differences"
            ][0]
        )

        final_status = (
            "CALCULATE_OUTPUT_VS_ASSIGNMENT_DIVERGENCE"
        )

        first_field = first[
            "field"
        ]

    elif assignment_vs_stored[
        "differences"
    ]:

        first = (
            assignment_vs_stored[
                "differences"
            ][0]
        )

        final_status = (
            "ASSIGNMENT_VS_STORED_DIVERGENCE"
        )

        first_field = first[
            "field"
        ]

    else:

        final_status = (
            "CALCULATE_ASSIGNMENT_STORED_EXACT_MATCH"
        )

        first_field = None

    print()
    print(
        "TARGET CONCLUSION"
    )

    print(
        f"STATUS        : {final_status}"
    )

    print(
        f"FIRST FIELD   : "
        f"{first_field if first_field is not None else 'NONE'}"
    )

    return {
        "status":
            final_status,
        "symbol":
            symbol,
        "runtime_result":
            runtime_result,
        "save_assignment":
            save_analysis,
        "stored":
            stored,
        "runtime_vs_assignment":
            runtime_vs_assignment,
        "assignment_vs_stored":
            assignment_vs_stored,
        "first_field":
            first_field,
    }


# ============================================================
# GLOBAL INVENTORY
# ============================================================

def print_inventory():

    section(
        "STEP 7 — RUNTIME FORENSIC INVENTORY"
    )

    total_returns = sum(
        len(events)
        for events in runtime_returns.values()
    )

    total_saves = sum(
        len(events)
        for events in runtime_save_arguments.values()
    )

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{len(calculate_calls)}"
    )

    print(
        f"RUNTIME RETURN EVENTS         : "
        f"{total_returns}"
    )

    print(
        f"SAVE ASSIGNMENT EVENTS        : "
        f"{total_saves}"
    )

    print(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(sql_trace)}"
    )

    print(
        f"BLOCKED WRITE-LIKE OPERATIONS : "
        f"{len(blocked_writes)}"
    )

    print(
        f"RUNTIME EXCEPTIONS            : "
        f"{len(runtime_exceptions)}"
    )

    print()

    print(
        "TARGET DISTRIBUTION"
    )

    for symbol in TARGETS:

        print(
            f"{symbol:<6}"
            f" | CALLS="
            f"{len(runtime_returns.get(symbol, [])):<3}"
            f" | SAVES="
            f"{len(runtime_save_arguments.get(symbol, [])):<3}"
        )


# ============================================================
# FINAL STATUS
# ============================================================

def determine_final_status(
    results,
    resolved_targets
):

    if not resolved_targets:

        return (
            "NO_TARGETS_RESOLVED"
        )

    statuses = [
        result["status"]
        for result in results
    ]

    if any(
        status == "CALCULATE_OUTPUT_VS_ASSIGNMENT_DIVERGENCE"
        for status in statuses
    ):

        return (
            "RUNTIME_TO_ASSIGNMENT_DIVERGENCE_OBSERVED"
        )

    if any(
        status == "ASSIGNMENT_VS_STORED_DIVERGENCE"
        for status in statuses
    ):

        return (
            "ASSIGNMENT_TO_STORED_DIVERGENCE_OBSERVED"
        )

    if all(
        status == "CALCULATE_ASSIGNMENT_STORED_EXACT_MATCH"
        for status in statuses
    ):

        return (
            "CALCULATE_ASSIGNMENT_STORED_EXACT_MATCH"
        )

    if any(
        status == "NO_RUNTIME_RETURN"
        for status in statuses
    ):

        return (
            "RUNTIME_CALCULATE_OUTPUT_NOT_OBSERVED"
        )

    return (
        "FORENSIC_PARTIALLY_RESOLVED"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary(
    results,
    resolved_targets
):

    status = determine_final_status(
        results,
        resolved_targets
    )

    section(
        "STEP 8 — FINAL FORENSIC SUMMARY"
    )

    exact_matches = sum(
        1
        for result in results
        if result["status"]
        == "CALCULATE_ASSIGNMENT_STORED_EXACT_MATCH"
    )

    divergence_count = sum(
        1
        for result in results
        if "DIVERGENCE"
        in result["status"]
    )

    no_runtime = sum(
        1
        for result in results
        if result["status"]
        == "NO_RUNTIME_RETURN"
    )

    print(
        f"TARGETS REQUESTED             : "
        f"{len(TARGETS)}"
    )

    print(
        f"TARGETS FOUND IN DATABASE     : "
        f"{len(resolved_targets)}"
    )

    print(
        f"TARGETS EXACTLY MATCHED       : "
        f"{exact_matches}"
    )

    print(
        f"TARGETS WITH DIVERGENCE       : "
        f"{divergence_count}"
    )

    print(
        f"TARGETS WITHOUT RUNTIME OUTPUT: "
        f"{no_runtime}"
    )

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{len(calculate_calls)}"
    )

    print(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(sql_trace)}"
    )

    print(
        f"BLOCKED WRITE-LIKE OPERATIONS : "
        f"{len(blocked_writes)}"
    )

    print(
        f"RUNTIME EXCEPTIONS            : "
        f"{len(runtime_exceptions)}"
    )

    print()
    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    print(
        f"STATUS                        : "
        f"{status}"
    )

    if status == (
        "RUNTIME_TO_ASSIGNMENT_DIVERGENCE_OBSERVED"
    ):

        print(
            "MEANING                       : "
            "The real calculate_analysis return "
            "differs from the object passed into "
            "save_analysis."
        )

        print(
            "NEXT FRONTIER                 : "
            "Localize the first divergent field "
            "inside the production assignment path."
        )

    elif status == (
        "ASSIGNMENT_TO_STORED_DIVERGENCE_OBSERVED"
    ):

        print(
            "MEANING                       : "
            "The real save_analysis assignment "
            "differs from the independently stored "
            "market_data row."
        )

        print(
            "NEXT FRONTIER                 : "
            "Trace the exact persistence assignment "
            "path for the first divergent field."
        )

    elif status == (
        "CALCULATE_ASSIGNMENT_STORED_EXACT_MATCH"
    ):

        print(
            "MEANING                       : "
            "The genuine calculate_analysis return, "
            "the save_analysis assignment, and the "
            "stored market_data values match exactly "
            "for all resolved targets."
        )

        print(
            "NEXT FRONTIER                 : "
            "The indicator calculation and persistence "
            "path are verified for the requested targets."
        )

    elif status == (
        "RUNTIME_CALCULATE_OUTPUT_NOT_OBSERVED"
    ):

        print(
            "MEANING                       : "
            "The production runtime did not expose "
            "usable calculate_analysis output for "
            "one or more targets."
        )

        print(
            "NEXT FRONTIER                 : "
            "Trace the missing runtime return path."
        )

    else:

        print(
            "MEANING                       : "
            "The forensic chain is only partially resolved."
        )

    print()

    print(
        "IMPORTANT                     : "
        "No runtime result is fabricated."
    )

    print(
        "IMPORTANT                     : "
        "The original production calculate_analysis "
        "function is executed unchanged."
    )

    print(
        "IMPORTANT                     : "
        "The original production save_analysis "
        "function is NEVER executed."
    )

    print(
        "IMPORTANT                     : "
        "Stored rows are independently read in "
        "SQLite read-only mode."
    )

    print(
        "IMPORTANT                     : "
        "No production formula is modified."
    )

    print(
        "IMPORTANT                     : "
        "No production database write is permitted."
    )

    print()

    print(
        "DATABASE WRITE OPERATIONS     : NONE"
    )

    print(
        "ENGINE MODIFICATIONS          : NONE ON DISK"
    )

    print(
        "INSERT                        : NONE"
    )

    print(
        "UPDATE                        : NONE"
    )

    print(
        "DELETE                        : NONE"
    )

    print(
        "ALTER                         : NONE"
    )

    print(
        "CREATE                        : BYPASSED / BLOCKED"
    )

    print(
        "DROP                          : NONE"
    )

    print(
        "PRODUCTION DB WRITE           : BLOCKED"
    )


# ============================================================
# MAIN FORENSIC DRIVER
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA INDICATOR CALCULATE OUTPUT "
        "VS STORED ASSIGNMENT FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                         : "
        "READ ONLY RUNTIME FORENSICS"
    )

    print(
        "DATABASE WRITE               : "
        "BLOCKED"
    )

    print(
        "ENGINE WRITE                 : "
        "NONE"
    )

    print(
        "PRODUCTION CALCULATION      : "
        "REAL IN-MEMORY EXECUTION"
    )

    print(
        "TARGETS                      : "
        "BTC / ETH / SOL / XRP"
    )

    results = []

    try:

        verify_paths()

        inspect_engine_source()

        resolved_targets = (
            resolve_targets()
        )

        if not resolved_targets:

            raise RuntimeError(
                "No requested targets resolved from database"
            )

        module = (
            import_production_module()
        )

        install_runtime_observers(
            module
        )

        execute_production_main(
            module
        )

        print_inventory()

        section(
            "STEP 7B — TARGET-BY-TARGET "
            "RETURN / ASSIGNMENT / STORED COMPARISON"
        )

        for symbol in resolved_targets:

            try:

                result = analyze_target(
                    symbol
                )

                results.append(
                    result
                )

            except Exception as exc:

                print()
                print(
                    f"[TARGET FORENSIC ERROR] "
                    f"{symbol}"
                )

                print(
                    repr(exc)
                )

                print(
                    traceback.format_exc()
                )

                results.append(
                    {
                        "status":
                            "TARGET_FORENSIC_ERROR",
                        "symbol":
                            symbol,
                    }
                )

        final_summary(
            results,
            resolved_targets
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print()

        line("=")

        print(
            f"ELAPSED SECONDS              : "
            f"{elapsed:.3f}"
        )

        print(
            "AUDIT COMPLETE"
        )

        line("=")

        return 0

    except Exception as exc:

        elapsed = (
            time.perf_counter()
            - started
        )

        print()

        line("=")

        print(
            "FORENSIC AUDIT ERROR"
        )

        line("=")

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        print()

        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS      : NONE ON DISK"
        )

        print(
            "PRODUCTION DB WRITE       : BLOCKED"
        )

        print(
            f"ELAPSED SECONDS           : "
            f"{elapsed:.3f}"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )