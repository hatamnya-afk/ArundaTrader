import os
import sys
import sqlite3
import time
import importlib
import traceback


# =============================================================================
# ARUNDA INDICATOR RUNTIME ROWS EXACT SQL RESULT FIRST DIVERGENCE FORENSIC AUDIT
# v0.1
# =============================================================================
#
# PURPOSE
# -------
# This audit observes the REAL production runtime path of:
#
#     market_data_engine.main()
#             |
#             +--> get_snapshot_history()
#             |
#             +--> calculate_analysis(rows)
#
# The audit captures the EXACT runtime `rows` object passed into
# calculate_analysis(), then independently executes the exact production
# SELECT against a separate READ-ONLY SQLite connection.
#
# It then compares:
#
#     ACTUAL RUNTIME ROWS
#              VS
#     INDEPENDENT EXACT SQL RESULT
#
# row-by-row and field-by-field.
#
# SAFETY CONTRACT
# ---------------
# READ ONLY FORENSICS
#
# NO production engine modification on disk.
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
# NO REPLACE
# NO VACUUM
# NO PRAGMA write operations
# NO fabricated runtime rows
# NO reconstructed runtime rows
# NO formula modification
#
# Production functions are patched ONLY IN MEMORY for this audit process.
#
# IMPORTANT
# ---------
# This file does NOT attempt to "fix" the production engine.
#
# It only observes the real execution path.
# =============================================================================


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENGINE_FILE = os.path.join(
    PROJECT_DIR,
    "market_data_engine.py"
)

DATABASE_FILE = os.path.join(
    PROJECT_DIR,
    "arunda.db"
)

ENGINE_MODULE_NAME = "market_data_engine"

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

SNAPSHOT_SOURCE = "COINMARKETCAP"

LOOKBACK = 150

MIN_HISTORY = 60

TIMEFRAME = "SNAPSHOT"


# =============================================================================
# AUDIT STATE
# =============================================================================

runtime_rows_by_symbol = {}

runtime_row_object_ids = {}

runtime_calculate_calls = []

runtime_returns = []

runtime_exceptions = []

runtime_sql_traces = []

runtime_select_traces = []

runtime_cursor_fetch_traces = []

blocked_write_operations = []

production_entrypoint_status = {
    "executed": False,
    "entrypoint": None,
    "return_value": None,
    "exception": None,
}

stored_target_rows = {}

exact_sql_rows = {}

comparison_results = {}


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def line(char="-", width=100):
    print(char * width)


def title(text):
    print()
    line("=")
    print(text)
    line("=")


def section(text):
    print()
    line("-")
    print(text)
    line("-")


# =============================================================================
# WRITE SQL CLASSIFICATION
# =============================================================================

WRITE_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "CREATE",
    "ALTER",
    "DROP",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)

WRITE_PRAGMA_PREFIXES = (
    "PRAGMA JOURNAL_MODE",
    "PRAGMA WAL_CHECKPOINT",
    "PRAGMA AUTO_VACUUM",
    "PRAGMA USER_VERSION",
)


def normalize_sql(sql):
    if sql is None:
        return ""

    return " ".join(
        str(sql)
        .strip()
        .split()
    )


def is_write_like_sql(sql):

    normalized = normalize_sql(sql)

    upper = normalized.upper()

    if not upper:
        return False

    for prefix in WRITE_PREFIXES:

        if upper.startswith(prefix):
            return True

    for prefix in WRITE_PRAGMA_PREFIXES:

        if upper.startswith(prefix):
            return True

    return False


# =============================================================================
# READ-ONLY SQLITE CONNECTION
# =============================================================================

def connect_read_only(db_path):

    absolute = os.path.abspath(
        db_path
    )

    if not os.path.exists(absolute):

        raise FileNotFoundError(
            f"Database not found: {absolute}"
        )

    uri = (
        "file:"
        + absolute.replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    return conn


# =============================================================================
# AUTHORITATIVE WRITE-BLOCKING CONNECTION
# =============================================================================

class AuditCursor:

    def __init__(
        self,
        cursor,
        connection,
        trace_owner
    ):

        self._cursor = cursor

        self._connection = connection

        self._trace_owner = trace_owner

    def execute(
        self,
        sql,
        parameters=()
    ):

        params = tuple(
            parameters
        ) if parameters is not None else ()

        normalized = normalize_sql(
            sql
        )

        if is_write_like_sql(
            sql
        ):

            event = {
                "sql": str(sql),
                "parameters": repr(params),
                "write_like": True,
            }

            blocked_write_operations.append(
                event
            )

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL blocked"
            )

        trace = {
            "sql": str(sql),
            "parameters": repr(params),
            "write_like": False,
        }

        runtime_sql_traces.append(
            trace
        )

        upper = normalized.upper()

        if upper.startswith("SELECT"):

            runtime_select_traces.append(
                trace
            )

        self._cursor.execute(
            sql,
            params
        )

        return self

    def executemany(
        self,
        sql,
        seq_of_parameters
    ):

        if is_write_like_sql(
            sql
        ):

            event = {
                "sql": str(sql),
                "parameters": "<executemany>",
                "write_like": True,
            }

            blocked_write_operations.append(
                event
            )

            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: "
                "write-like SQL blocked"
            )

        return self._cursor.executemany(
            sql,
            seq_of_parameters
        )

    def fetchone(self):

        row = self._cursor.fetchone()

        runtime_cursor_fetch_traces.append(
            {
                "method": "fetchone",
                "row_count": (
                    0
                    if row is None
                    else 1
                ),
            }
        )

        return row

    def fetchmany(self, size=None):

        if size is None:

            rows = self._cursor.fetchmany()

        else:

            rows = self._cursor.fetchmany(
                size
            )

        runtime_cursor_fetch_traces.append(
            {
                "method": "fetchmany",
                "requested": size,
                "row_count": len(rows),
            }
        )

        return rows

    def fetchall(self):

        rows = self._cursor.fetchall()

        runtime_cursor_fetch_traces.append(
            {
                "method": "fetchall",
                "row_count": len(rows),
            }
        )

        return rows

    def __iter__(self):

        return iter(
            self._cursor
        )

    def __getattr__(
        self,
        name
    ):

        return getattr(
            self._cursor,
            name
        )


class AuditConnection:

    def __init__(
        self,
        real_connection
    ):

        self._conn = real_connection

        self.row_factory = sqlite3.Row

    def cursor(self):

        return AuditCursor(
            self._conn.cursor(),
            self,
            runtime_sql_traces
        )

    def execute(
        self,
        sql,
        parameters=()
    ):

        cursor = self.cursor()

        return cursor.execute(
            sql,
            parameters
        )

    def executemany(
        self,
        sql,
        parameters
    ):

        cursor = self.cursor()

        return cursor.executemany(
            sql,
            parameters
        )

    def commit(self):

        # Commit is deliberately neutralized.
        #
        # No production write is allowed by this audit.
        #
        # The real connection is already read-only.

        return None

    def rollback(self):

        return None

    def close(self):

        return self._conn.close()

    def __enter__(self):

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback_value
    ):

        self.close()

    def __getattr__(
        self,
        name
    ):

        return getattr(
            self._conn,
            name
        )


def audit_connect_database():

    real_conn = connect_read_only(
        DATABASE_FILE
    )

    return AuditConnection(
        real_conn
    )


# =============================================================================
# ROW NORMALIZATION
# =============================================================================

def row_to_tuple(row):

    if isinstance(
        row,
        sqlite3.Row
    ):

        return tuple(
            row
        )

    if isinstance(
        row,
        dict
    ):

        return tuple(
            row.values()
        )

    try:

        return tuple(
            row
        )

    except Exception:

        return (
            repr(row),
        )


def rows_to_tuples(rows):

    return [
        row_to_tuple(row)
        for row in rows
    ]


# =============================================================================
# ROW DIAGNOSTIC REPRESENTATION
# =============================================================================

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

        return {
            str(index): value
            for index, value
            in enumerate(row)
        }

    except Exception:

        return {
            "repr": repr(row)
        }


# =============================================================================
# EXACT PRODUCTION SQL
# =============================================================================
#
# This is copied from market_data_engine.get_snapshot_history().
#
# No guessed SQL.
# No alternate ordering.
# No alternate filtering.
# No alternate window.
# =============================================================================

EXACT_SQL = """
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
    source_latency_ms
FROM market_data
WHERE
    symbol = ?
    AND source = ?
    AND timeframe = 'SNAPSHOT'
    AND close IS NOT NULL
ORDER BY id ASC
LIMIT ?
"""


# =============================================================================
# EXACT STORED SQL EXECUTION
# =============================================================================

def execute_exact_sql(
    symbol
):

    conn = connect_read_only(
        DATABASE_FILE
    )

    try:

        cursor = conn.cursor()

        parameters = (
            symbol,
            SNAPSHOT_SOURCE,
            LOOKBACK,
        )

        cursor.execute(
            EXACT_SQL,
            parameters
        )

        rows = cursor.fetchall()

        exact_sql_rows[
            symbol
        ] = rows

        return rows

    finally:

        conn.close()


# =============================================================================
# RUNTIME calculate_analysis PATCH
# =============================================================================

def build_forensic_calculate_analysis(
    original_function
):

    def forensic_calculate_analysis(
        rows
    ):

        call_number = (
            len(runtime_calculate_calls)
            + 1
        )

        symbol = None

        if rows:

            try:

                symbol = rows[0]["symbol"]

            except Exception:

                try:

                    symbol = rows[-1]["symbol"]

                except Exception:

                    symbol = None

        # Capture the EXACT object identity.

        object_id = id(
            rows
        )

        runtime_row_object_ids[
            call_number
        ] = object_id

        # Capture the exact rows object content.
        #
        # This is not fabricated.
        # These are the actual rows passed by production code.

        captured_rows = list(
            rows
        )

        if symbol is not None:

            runtime_rows_by_symbol[
                symbol
            ] = captured_rows

        runtime_calculate_calls.append(
            {
                "call_number": call_number,
                "symbol": symbol,
                "row_count": len(captured_rows),
                "object_id": object_id,
            }
        )

        print(
            f"[RUNTIME_CAPTURE] "
            f"CALL={call_number:<3} "
            f"SYMBOL={symbol} "
            f"ROWS={len(captured_rows):<4} "
            f"OBJECT_ID={object_id}"
        )

        try:

            result = original_function(
                rows
            )

            runtime_returns.append(
                {
                    "call_number": call_number,
                    "symbol": symbol,
                    "returned": result,
                }
            )

            return result

        except Exception as exc:

            runtime_exceptions.append(
                {
                    "call_number": call_number,
                    "symbol": symbol,
                    "exception": repr(exc),
                }
            )

            raise

    return forensic_calculate_analysis


# =============================================================================
# NO-OP SCHEMA
# =============================================================================
#
# Production main() calls ensure_schema().
#
# We neutralize ONLY that write-producing operation in memory.
#
# The production source file is NOT changed.
# =============================================================================

def forensic_ensure_schema(
    conn
):

    print(
        "[FORENSIC] ensure_schema() "
        "neutralized in-memory"
    )

    return None


# =============================================================================
# NO-OP SAVE
# =============================================================================
#
# Production main() calls save_analysis().
#
# We prevent the INSERT while allowing main() to continue through the real
# calculate_analysis path.
# =============================================================================

def forensic_save_analysis(
    conn,
    symbol,
    analysis
):

    print(
        f"[FORENSIC] save_analysis() "
        f"blocked for {symbol}"
    )

    return False


# =============================================================================
# LOAD PRODUCTION MODULE
# =============================================================================

def load_engine():

    if not os.path.exists(
        ENGINE_FILE
    ):

        raise FileNotFoundError(
            ENGINE_FILE
        )

    if PROJECT_DIR not in sys.path:

        sys.path.insert(
            0,
            PROJECT_DIR
        )

    # Ensure the module is loaded fresh.

    if ENGINE_MODULE_NAME in sys.modules:

        del sys.modules[
            ENGINE_MODULE_NAME
        ]

    engine = importlib.import_module(
        ENGINE_MODULE_NAME
    )

    return engine


# =============================================================================
# PATCH PRODUCTION MODULE IN MEMORY
# =============================================================================

def patch_engine(
    engine
):

    original_calculate_analysis = (
        engine.calculate_analysis
    )

    forensic_calculate_analysis = (
        build_forensic_calculate_analysis(
            original_calculate_analysis
        )
    )

    engine.calculate_analysis = (
        forensic_calculate_analysis
    )

    engine.connect_database = (
        audit_connect_database
    )

    engine.ensure_schema = (
        forensic_ensure_schema
    )

    engine.save_analysis = (
        forensic_save_analysis
    )

    return {
        "original_calculate_analysis":
            original_calculate_analysis,

        "forensic_calculate_analysis":
            forensic_calculate_analysis,
    }


# =============================================================================
# TARGET RESOLUTION
# =============================================================================

def resolve_targets():

    conn = connect_read_only(
        DATABASE_FILE
    )

    try:

        found = {}

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT
                    symbol,
                    COUNT(*) AS row_count
                FROM market_data
                WHERE
                    symbol = ?
                    AND source = ?
                    AND timeframe = 'SNAPSHOT'
                    AND close IS NOT NULL
                """,
                (
                    symbol,
                    SNAPSHOT_SOURCE,
                )
            ).fetchone()

            count = int(
                row["row_count"]
            )

            if count > 0:

                found[
                    symbol
                ] = count

                print(
                    f"[STORED_TARGET_RESOLVED] "
                    f": {symbol}"
                )

        return found

    finally:

        conn.close()


# =============================================================================
# RUNTIME ENTRYPOINT EXECUTION
# =============================================================================

def execute_real_production_main(
    engine
):

    production_entrypoint_status[
        "executed"
    ] = True

    production_entrypoint_status[
        "entrypoint"
    ] = "main"

    print()
    line("=")
    print(
        "RUNTIME PRODUCTION ENTRYPOINT"
    )
    line("=")

    print(
        "ENTRYPOINT : main"
    )

    print(
        "MODE       : IN-MEMORY FORENSIC"
    )

    try:

        result = engine.main()

        production_entrypoint_status[
            "return_value"
        ] = result

        print(
            f"[RUNTIME] main() returned: "
            f"{repr(result)}"
        )

        return result

    except Exception as exc:

        production_entrypoint_status[
            "exception"
        ] = repr(exc)

        runtime_exceptions.append(
            {
                "call_number": None,
                "symbol": None,
                "exception": repr(exc),
            }
        )

        print(
            "[RUNTIME] main() exception:"
        )

        print(
            repr(exc)
        )

        traceback.print_exc()

        return None


# =============================================================================
# INDEPENDENT EXACT SQL RECONSTRUCTION
# =============================================================================

def reconstruct_exact_results():

    section(
        "STEP 10 — INDEPENDENT EXACT SQL RESULT"
    )

    for symbol in TARGETS:

        rows = execute_exact_sql(
            symbol
        )

        print(
            f"[EXACT_SQL_RESULT] "
            f"{symbol:<5} "
            f"ROWS={len(rows)}"
        )


# =============================================================================
# FIRST DIVERGENCE
# =============================================================================

def values_equal(
    left,
    right
):

    if left == right:

        return True

    if (
        isinstance(left, float)
        and isinstance(right, float)
    ):

        if (
            math_isfinite(left)
            and math_isfinite(right)
        ):

            return abs(
                left - right
            ) <= 1e-12

    return False


def math_isfinite(
    value
):

    try:

        return bool(
            __import__(
                "math"
            ).isfinite(value)
        )

    except Exception:

        return False


def compare_rows(
    runtime_rows,
    exact_rows,
    symbol
):

    result = {
        "symbol": symbol,
        "runtime_count": len(
            runtime_rows
        ),
        "exact_count": len(
            exact_rows
        ),
        "status": None,
        "first_divergence": None,
    }

    if len(runtime_rows) != len(exact_rows):

        result[
            "status"
        ] = "ROW_COUNT_DIVERGENCE"

        result[
            "first_divergence"
        ] = {
            "type": "ROW_COUNT",
            "runtime_count":
                len(runtime_rows),
            "exact_count":
                len(exact_rows),
        }

        return result

    for row_index in range(
        len(runtime_rows)
    ):

        runtime_row = (
            runtime_rows[
                row_index
            ]
        )

        exact_row = (
            exact_rows[
                row_index
            ]
        )

        runtime_dict = row_to_dict(
            runtime_row
        )

        exact_dict = row_to_dict(
            exact_row
        )

        runtime_keys = list(
            runtime_dict.keys()
        )

        exact_keys = list(
            exact_dict.keys()
        )

        if runtime_keys != exact_keys:

            result[
                "status"
            ] = "COLUMN_STRUCTURE_DIVERGENCE"

            result[
                "first_divergence"
            ] = {
                "type":
                    "COLUMN_STRUCTURE",
                "row_index":
                    row_index,
                "runtime_keys":
                    runtime_keys,
                "exact_keys":
                    exact_keys,
            }

            return result

        for key in runtime_keys:

            left = runtime_dict[
                key
            ]

            right = exact_dict[
                key
            ]

            if not values_equal(
                left,
                right
            ):

                result[
                    "status"
                ] = "FIRST_VALUE_DIVERGENCE"

                result[
                    "first_divergence"
                ] = {
                    "type":
                        "VALUE",
                    "row_index":
                        row_index,
                    "column":
                        key,
                    "runtime_value":
                        left,
                    "exact_sql_value":
                        right,
                    "runtime_row":
                        runtime_dict,
                    "exact_sql_row":
                        exact_dict,
                }

                return result

    result[
        "status"
    ] = "EXACT_MATCH"

    return result


# =============================================================================
# COMPARISON
# =============================================================================

def perform_comparison():

    section(
        "STEP 11 — RUNTIME VS EXACT SQL FIRST DIVERGENCE"
    )

    for symbol in TARGETS:

        runtime_rows = (
            runtime_rows_by_symbol.get(
                symbol
            )
        )

        exact_rows = (
            exact_sql_rows.get(
                symbol,
                []
            )
        )

        print()
        print(
            "=" * 100
        )

        print(
            f"SYMBOL : {symbol}"
        )

        print(
            "=" * 100
        )

        if runtime_rows is None:

            comparison_results[
                symbol
            ] = {
                "symbol": symbol,
                "runtime_count": None,
                "exact_count": len(
                    exact_rows
                ),
                "status":
                    "RUNTIME_ROWS_MISSING",
                "first_divergence":
                    None,
            }

            print(
                "RUNTIME ROW COUNT : MISSING"
            )

            print(
                f"EXACT SQL ROW COUNT : "
                f"{len(exact_rows)}"
            )

            print(
                "STATUS : RUNTIME_ROWS_MISSING"
            )

            continue

        result = compare_rows(
            runtime_rows,
            exact_rows,
            symbol
        )

        comparison_results[
            symbol
        ] = result

        print(
            f"RUNTIME ROW COUNT : "
            f"{result['runtime_count']}"
        )

        print(
            f"EXACT SQL ROW COUNT : "
            f"{result['exact_count']}"
        )

        print(
            f"STATUS : "
            f"{result['status']}"
        )

        divergence = (
            result[
                "first_divergence"
            ]
        )

        if divergence is not None:

            print()

            print(
                "FIRST DIVERGENCE"
            )

            print(
                f"TYPE        : "
                f"{divergence.get('type')}"
            )

            if (
                "row_index"
                in divergence
            ):

                print(
                    f"ROW INDEX   : "
                    f"{divergence['row_index']}"
                )

            if (
                "column"
                in divergence
            ):

                print(
                    f"COLUMN      : "
                    f"{divergence['column']}"
                )

                print(
                    f"RUNTIME     : "
                    f"{repr(divergence['runtime_value'])}"
                )

                print(
                    f"EXACT SQL   : "
                    f"{repr(divergence['exact_sql_value'])}"
                )


# =============================================================================
# FINAL SUMMARY
# =============================================================================

def final_summary():

    section(
        "STEP 12 — WRITE SAFETY VERIFICATION"
    )

    print(
        "DATABASE CONNECTION MODE      : READ ONLY"
    )

    print(
        "SQLITE AUTHORITATIVE BLOCK   : ENABLED"
    )

    print(
        f"BLOCKED WRITE OPERATIONS      : "
        f"{len(blocked_write_operations)}"
    )

    section(
        "STEP 13 — RUNTIME CAPTURE SUMMARY"
    )

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{len(runtime_calculate_calls)}"
    )

    print(
        f"RUNTIME RETURNS                : "
        f"{len(runtime_returns)}"
    )

    print(
        f"RUNTIME EXCEPTIONS            : "
        f"{len(runtime_exceptions)}"
    )

    print(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(runtime_sql_traces)}"
    )

    print(
        f"SELECT EXECUTION TRACE COUNT  : "
        f"{len(runtime_select_traces)}"
    )

    print(
        f"CURSOR FETCH TRACE COUNT      : "
        f"{len(runtime_cursor_fetch_traces)}"
    )

    section(
        "STEP 14 — TARGET MATRIX"
    )

    exact_matches = 0

    first_divergences = 0

    runtime_missing = 0

    stored_missing = 0

    row_count_divergence = 0

    for symbol in TARGETS:

        result = comparison_results.get(
            symbol
        )

        if result is None:

            print(
                f"[NO_COMPARISON]            : "
                f"{symbol}"
            )

            continue

        status = result[
            "status"
        ]

        if status == "EXACT_MATCH":

            exact_matches += 1

            print(
                f"[EXACT_MATCH]              : "
                f"{symbol}"
            )

        elif status == "RUNTIME_ROWS_MISSING":

            runtime_missing += 1

            print(
                f"[RUNTIME_ROWS_MISSING]     : "
                f"{symbol}"
            )

        elif status == "ROW_COUNT_DIVERGENCE":

            row_count_divergence += 1

            print(
                f"[ROW_COUNT_DIVERGENCE]     : "
                f"{symbol}"
            )

        elif status in (
            "FIRST_VALUE_DIVERGENCE",
            "COLUMN_STRUCTURE_DIVERGENCE",
        ):

            first_divergences += 1

            print(
                f"[FIRST_DIVERGENCE]         : "
                f"{symbol}"
            )

        else:

            print(
                f"[{status}]"
                f" : {symbol}"
            )

        if result[
            "exact_count"
        ] == 0:

            stored_missing += 1

    section(
        "STEP 15 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"TARGETS REQUESTED             : "
        f"{len(TARGETS)}"
    )

    print(
        f"TARGETS WITH EXACT MATCH      : "
        f"{exact_matches}"
    )

    print(
        f"TARGETS WITH FIRST DIVERGENCE : "
        f"{first_divergences}"
    )

    print(
        f"ROW COUNT DIVERGENCES         : "
        f"{row_count_divergence}"
    )

    print(
        f"RUNTIME ROWS MISSING          : "
        f"{runtime_missing}"
    )

    print(
        f"STORED ROWS MISSING           : "
        f"{stored_missing}"
    )

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{len(runtime_calculate_calls)}"
    )

    print(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(runtime_sql_traces)}"
    )

    print(
        f"SELECT EXECUTION TRACE COUNT  : "
        f"{len(runtime_select_traces)}"
    )

    print(
        f"CURSOR FETCH TRACE COUNT      : "
        f"{len(runtime_cursor_fetch_traces)}"
    )

    print(
        f"BLOCKED WRITE-LIKE OPERATIONS : "
        f"{len(blocked_write_operations)}"
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

    if (
        exact_matches == len(TARGETS)
        and runtime_missing == 0
        and first_divergences == 0
        and row_count_divergence == 0
    ):

        status = (
            "RUNTIME_ROWS_EXACTLY_MATCH_EXACT_SQL"
        )

        meaning = (
            "The actual runtime rows passed into "
            "calculate_analysis are identical to "
            "the independently executed exact "
            "production SQL result for all requested targets."
        )

        next_frontier = (
            "Trace calculate_analysis output versus "
            "stored market_data assignment."
        )

    elif first_divergences > 0:

        status = (
            "FIRST_RUNTIME_SQL_RESULT_DIVERGENCE_CONFIRMED"
        )

        meaning = (
            "At least one target contains a first "
            "row or field divergence between the "
            "actual runtime rows and the independently "
            "executed exact SQL result."
        )

        next_frontier = (
            "Trace the exact runtime result construction "
            "before calculate_analysis."
        )

    elif row_count_divergence > 0:

        status = (
            "RUNTIME_SQL_ROW_COUNT_DIVERGENCE_CONFIRMED"
        )

        meaning = (
            "The actual runtime result window contains "
            "a different number of rows than the exact "
            "production SQL reconstruction."
        )

        next_frontier = (
            "Trace runtime connection, cursor consumption, "
            "query parameters and row-window mutation."
        )

    elif runtime_missing > 0:

        status = (
            "RUNTIME_CALCULATE_ANALYSIS_NOT_OBSERVED"
        )

        meaning = (
            "The production entrypoint executed, but "
            "usable runtime rows were not captured for "
            "one or more requested targets."
        )

        next_frontier = (
            "Trace the exact runtime object passed into "
            "calculate_analysis."
        )

    else:

        status = (
            "SQL_RESULT_INSUFFICIENT_FOR_COMPARISON"
        )

        meaning = (
            "The audit did not obtain sufficient actual "
            "runtime and SQL result material to establish "
            "a divergence."
        )

        next_frontier = (
            "Trace exact runtime SQL result construction."
        )

    print(
        f"STATUS                        : {status}"
    )

    print(
        f"MEANING                       : {meaning}"
    )

    print(
        "IMPORTANT                     : "
        "No runtime row contents are fabricated."
    )

    print(
        "IMPORTANT                     : "
        "No SQL result is reconstructed from assumptions."
    )

    print(
        "IMPORTANT                     : "
        "No production formula is modified."
    )

    print(
        "IMPORTANT                     : "
        "No production database write is permitted."
    )

    print(
        f"NEXT FRONTIER                 : "
        f"{next_frontier}"
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
        "CREATE                        : "
        + (
            "BLOCKED"
            if blocked_write_operations
            else "NONE"
        )
    )

    print(
        "DROP                          : NONE"
    )

    print(
        "PRODUCTION DB WRITE           : BLOCKED"
    )


# =============================================================================
# MAIN AUDIT
# =============================================================================

def main():

    started = time.perf_counter()

    title(
        "ARUNDA INDICATOR RUNTIME ROWS EXACT SQL RESULT "
        "FIRST DIVERGENCE FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                          : "
        "READ ONLY RUNTIME FORENSICS"
    )

    print(
        "DATABASE WRITE                : BLOCKED"
    )

    print(
        "ENGINE WRITE                  : NONE"
    )

    print(
        "PRODUCTION RECALCULATION      : "
        "IN-MEMORY OBSERVATION ONLY"
    )

    print(
        "TARGETS                       : "
        + " / ".join(TARGETS)
    )

    section(
        "STEP 1 — PATH SAFETY RESOLUTION"
    )

    print(
        f"PROJECT PATH                  : "
        f"{PROJECT_DIR}"
    )

    print(
        f"ENGINE PATH                   : "
        f"{ENGINE_FILE}"
    )

    print(
        f"ENGINE FOUND                  : "
        f"{os.path.exists(ENGINE_FILE)}"
    )

    print(
        f"DATABASE PATH                 : "
        f"{DATABASE_FILE}"
    )

    print(
        f"DATABASE FOUND                : "
        f"{os.path.exists(DATABASE_FILE)}"
    )

    if not os.path.exists(
        ENGINE_FILE
    ):

        raise FileNotFoundError(
            ENGINE_FILE
        )

    if not os.path.exists(
        DATABASE_FILE
    ):

        raise FileNotFoundError(
            DATABASE_FILE
        )

    section(
        "STEP 2 — STORED TARGET RESOLUTION"
    )

    resolve_targets()

    section(
        "STEP 3 — PRODUCTION ENGINE IMPORT"
    )

    engine = load_engine()

    print(
        f"MODULE IMPORTED              : "
        f"{ENGINE_MODULE_NAME}"
    )

    section(
        "STEP 4 — IN-MEMORY PRODUCTION PATCH"
    )

    patch_engine(
        engine
    )

    print(
        "[PATCHED] market_data_engine.calculate_analysis"
    )

    print(
        "[PATCHED] market_data_engine.connect_database"
    )

    print(
        "[PATCHED] market_data_engine.ensure_schema"
    )

    print(
        "[PATCHED] market_data_engine.save_analysis"
    )

    print(
        "PATCH TYPE                    : IN MEMORY ONLY"
    )

    print(
        "SOURCE FILE MODIFIED          : NO"
    )

    section(
        "STEP 5 — ACTUAL PRODUCTION ENTRYPOINT"
    )

    execute_real_production_main(
        engine
    )

    section(
        "STEP 6 — RUNTIME CAPTURE INVENTORY"
    )

    print(
        f"CALCULATE_ANALYSIS CALLS      : "
        f"{len(runtime_calculate_calls)}"
    )

    for event in runtime_calculate_calls:

        print(
            f"[CAPTURED] "
            f"CALL={event['call_number']} "
            f"SYMBOL={event['symbol']} "
            f"ROWS={event['row_count']} "
            f"OBJECT_ID={event['object_id']}"
        )

    section(
        "STEP 7 — EXACT SQL RECONSTRUCTION"
    )

    print(
        "SQL SOURCE                    : "
        "market_data_engine.get_snapshot_history()"
    )

    print(
        "ORDER                         : id ASC"
    )

    print(
        "LIMIT                         : 150"
    )

    print(
        "TIMEFRAME                     : SNAPSHOT"
    )

    print(
        "SOURCE                        : COINMARKETCAP"
    )

    print(
        "CLOSE FILTER                  : IS NOT NULL"
    )

    reconstruct_exact_results()

    section(
        "STEP 8 — RUNTIME VS SQL COMPARISON"
    )

    perform_comparison()

    final_summary()

    elapsed = (
        time.perf_counter()
        - started
    )

    print()

    print(
        f"ELAPSED SECONDS               : "
        f"{elapsed:.3f}"
    )

    print(
        "AUDIT COMPLETE"
    )

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except Exception as exc:

        print()

        title(
            "AUDIT FATAL ERROR"
        )

        print(
            repr(exc)
        )

        traceback.print_exc()

        print()

        print(
            "DATABASE WRITE OPERATIONS     : NONE"
        )

        print(
            "PRODUCTION DB WRITE           : BLOCKED"
        )

        raise