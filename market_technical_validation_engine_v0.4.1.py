import ast
import inspect
import importlib.util
import sqlite3
import sys
import traceback
from pathlib import Path
from collections import Counter


# =============================================================================
# ARUNDA
# MARKET_TECHNICAL_VALIDATION_REAL_RUNTIME_EXECUTION_TRACE_FORENSIC v0.1
# =============================================================================
#
# MODE:
#     READ ONLY
#
# PURPOSE:
#     Trace the REAL validation function execution inside
#     market_technical_engine.py without executing its production main().
#
# IMPORTANT:
#     This forensic intentionally DOES NOT call:
#
#         market_technical_engine.main()
#
#     because main() performs:
#
#         ALTER TABLE
#         UPDATE market_technical
#         COMMIT
#
#     Instead, this script:
#
#         1. Loads the actual production module.
#         2. Resolves the actual validate_row() function.
#         3. Reads REAL persisted market_technical rows.
#         4. Executes the REAL validate_row() against those rows.
#         5. Captures exact input/output relationships.
#         6. Does not execute production writes.
#
# NO:
#     INSERT
#     UPDATE
#     DELETE
#     ALTER
#     CREATE
#     DROP
#     REPLACE
#     COMMIT
#     ROLLBACK
#     SYNTHETIC DATA
#     INTERPOLATION
#     FORWARD FILL
#     BACK FILL
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "arunda.db"

ENGINE_FILE = PROJECT_DIR / "market_technical_engine.py"
TARGET_TABLE = "market_technical"

ENGINE_VERSION_EXPECTED = "0.4.1"

TRACE_LIMIT = 50


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<45}: {value}")


def safe(value):
    if value is None:
        return "NULL"
    return str(value)


# =============================================================================
# READ ONLY DATABASE
# =============================================================================

def connect_read_only():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = (
        f"file:{DB_PATH.as_posix()}"
        f"?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    # Extra SQLite-level protection.
    conn.execute(
        "PRAGMA query_only = ON"
    )

    return conn


def verify_read_only(conn):

    row = conn.execute(
        "PRAGMA query_only"
    ).fetchone()

    if row is None or int(row[0]) != 1:
        raise RuntimeError(
            "READ-ONLY CONTRACT FAILED"
        )


# =============================================================================
# DATABASE DISCOVERY
# =============================================================================

def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def get_columns(conn):

    rows = conn.execute(
        f'''
        PRAGMA table_info("{TARGET_TABLE}")
        '''
    ).fetchall()

    return [row["name"] for row in rows]


# =============================================================================
# SOURCE STATIC RESOLUTION
# =============================================================================

def read_engine_source():

    if not ENGINE_FILE.exists():
        raise FileNotFoundError(
            f"Production engine not found: {ENGINE_FILE}"
        )

    return ENGINE_FILE.read_text(
        encoding="utf-8-sig",
        errors="strict"
    )


def resolve_validate_row_ast(source):

    tree = ast.parse(
        source,
        filename=str(ENGINE_FILE)
    )

    matches = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            if node.name == "validate_row":
                matches.append(node)

    if not matches:
        raise RuntimeError(
            "validate_row() was not found in production engine"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple validate_row() definitions found: "
            f"{len(matches)}"
        )

    node = matches[0]

    return node


def print_validate_row_source(source, node):

    banner(
        "REAL PRODUCTION VALIDATION FUNCTION RESOLUTION"
    )

    lines = source.splitlines()

    start = node.lineno
    end = getattr(node, "end_lineno", node.lineno)

    kv(
        "Function",
        node.name
    )

    kv(
        "Source",
        ENGINE_FILE.name
    )

    kv(
        "Start Line",
        start
    )

    kv(
        "End Line",
        end
    )

    print()

    for line_number in range(
        start,
        min(end, start + 220) + 1
    ):

        print(
            f"{line_number:5d}: "
            f"{lines[line_number - 1]}"
        )


# =============================================================================
# MODULE LOAD
# =============================================================================

def load_production_module():

    banner(
        "REAL PRODUCTION MODULE LOAD"
    )

    spec = importlib.util.spec_from_file_location(
        "arunda_market_technical_engine_runtime_trace",
        ENGINE_FILE
    )

    if spec is None:
        raise RuntimeError(
            "Unable to create import specification"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        "arunda_market_technical_engine_runtime_trace"
    ] = module

    spec.loader.exec_module(module)

    kv(
        "Module",
        ENGINE_FILE.name
    )

    kv(
        "Module Loaded",
        "YES"
    )

    kv(
        "Production main() executed",
        "NO"
    )

    return module


# =============================================================================
# FUNCTION CONTRACT
# =============================================================================

def inspect_validation_function(module):

    banner(
        "VALIDATE_ROW RUNTIME CONTRACT"
    )

    if not hasattr(module, "validate_row"):
        raise RuntimeError(
            "Loaded production module has no validate_row()"
        )

    function = module.validate_row

    kv(
        "Function Object",
        repr(function)
    )

    kv(
        "Callable",
        callable(function)
    )

    try:
        signature = inspect.signature(
            function
        )

        kv(
            "Signature",
            str(signature)
        )

    except Exception as exc:

        kv(
            "Signature",
            f"ERROR: {exc}"
        )

    try:

        source_file = inspect.getsourcefile(
            function
        )

        source_lines = inspect.getsourcelines(
            function
        )

        kv(
            "Runtime Source",
            source_file
        )

        kv(
            "Runtime Source Line",
            source_lines[1]
        )

    except Exception as exc:

        kv(
            "Runtime Source",
            f"ERROR: {exc}"
        )

    return function


# =============================================================================
# PRODUCTION WRITE BOUNDARY STATIC CHECK
# =============================================================================

def inspect_main_write_boundary(source):

    banner(
        "PRODUCTION MAIN WRITE-BOUNDARY CONFIRMATION"
    )

    write_tokens = [
        "ALTER TABLE",
        "INSERT INTO",
        "UPDATE ",
        "DELETE FROM",
        "CREATE TABLE",
        "DROP TABLE",
        "REPLACE INTO",
        "executemany(",
        "commit(",
    ]

    lines = source.splitlines()

    found = []

    for number, line in enumerate(
        lines,
        1
    ):

        upper = line.upper()

        for token in write_tokens:

            if token in upper:

                found.append(
                    (
                        number,
                        token,
                        line.strip()
                    )
                )

    for number, token, line in found:

        print(
            f"line={number:<6} "
            f"token={token:<20} "
            f"{line[:160]}"
        )

    kv(
        "Write References Found",
        len(found)
    )

    print()
    print(
        "CONTRACT:"
    )

    print(
        "Production main() MUST NOT be executed by this forensic."
    )


# =============================================================================
# REAL ROW ACQUISITION
# =============================================================================

def acquire_real_rows(
    conn,
    columns,
    limit=TRACE_LIMIT
):

    banner(
        "REAL PERSISTED MARKET_TECHNICAL INPUT ACQUISITION"
    )

    rows = conn.execute(
        f"""
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
            limit,
        )
    ).fetchall()

    kv(
        "Rows Acquired",
        len(rows)
    )

    if not rows:
        raise RuntimeError(
            "No market_technical contract rows available"
        )

    kv(
        "Synthetic Rows",
        "NONE"
    )

    kv(
        "Source",
        "REAL persisted market_technical / TECHNICAL_v0.5 contract"
    )

    return rows


# =============================================================================
# RUNTIME VALIDATION TRACE
# =============================================================================

def trace_real_validation(
    validate_row,
    rows,
    columns
):

    banner(
        "REAL VALIDATE_ROW() EXECUTION TRACE"
    )

    print(
        "IMPORTANT: The function below is the REAL production "
        "validate_row() imported from market_technical_engine.py."
    )

    print(
        "Only the function is executed."
    )

    print(
        "Production main() and all production SQL writes are NOT executed."
    )

    print()

    results = []

    status_counter = Counter()
    score_counter = Counter()
    flag_counter = Counter()

    execution_errors = []

    for index, row in enumerate(rows, 1):

        symbol = (
            row["symbol"]
            if "symbol" in row.keys()
            else None
        )

        record_id = (
            row["id"]
            if "id" in row.keys()
            else None
        )

        timestamp = (
            row["timestamp"]
            if "timestamp" in row.keys()
            else None
        )

        print()
        print("-" * 100)

        kv(
            "TRACE ROW",
            index
        )

        kv(
            "id",
            safe(record_id)
        )

        kv(
            "symbol",
            safe(symbol)
        )

        kv(
            "timestamp",
            safe(timestamp)
        )

        # -------------------------------------------------------------
        # EXACT INPUTS USED BY validate_row()
        # -------------------------------------------------------------

        data = dict(
            zip(
                columns,
                row
            )
        )

        print()
        print(
            "CRITICAL VALIDATION INPUTS:"
        )

        for field in [
            "price",
            "close",
            "history_points",
            "technical_available",
            "available",
            "technical_completeness",
            "completeness",
            "rsi14",
            "rsi_14",
            "atr14",
            "atr_14",
            "trend_score",
            "momentum_score",
            "volatility_score",
            "volume_score",
            "range_score",
            "breakout_score",
            "fib_available",
            "ichimoku_available",
        ]:

            if field in data:

                print(
                    f"  {field:<30}: "
                    f"{safe(data[field])}"
                )

        # -------------------------------------------------------------
        # REAL FUNCTION EXECUTION
        # -------------------------------------------------------------

        try:

            result = validate_row(
                row,
                columns
            )

            print()
            print(
                "REAL validate_row() OUTPUT:"
            )

            print(
                f"  raw_return : {result!r}"
            )

            if not isinstance(
                result,
                tuple
            ):

                raise RuntimeError(
                    "validate_row() did not return tuple"
                )

            if len(result) != 3:

                raise RuntimeError(
                    "validate_row() return tuple "
                    f"length = {len(result)}"
                )

            score, status, flags = result

            print(
                f"  score      : {safe(score)}"
            )

            print(
                f"  status     : {safe(status)}"
            )

            print(
                f"  flags      : {safe(flags)}"
            )

            status_counter[
                safe(status)
            ] += 1

            score_counter[
                safe(score)
            ] += 1

            if flags:
                for flag in str(flags).split(","):
                    flag_counter[
                        flag
                    ] += 1

            results.append(
                {
                    "id": record_id,
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "score": score,
                    "status": status,
                    "flags": flags,
                }
            )

        except Exception as exc:

            execution_errors.append(
                {
                    "id": record_id,
                    "symbol": symbol,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            print()
            print(
                "REAL VALIDATION EXECUTION ERROR:"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
        execution_errors,
    )


# =============================================================================
# PERSISTED VS RUNTIME COMPARISON
# =============================================================================

def compare_runtime_with_persisted(
    rows,
    results
):

    banner(
        "RUNTIME OUTPUT vs PERSISTED VALIDATION COMPARISON"
    )

    persisted_by_id = {}

    for row in rows:

        if "id" not in row.keys():
            continue

        persisted_by_id[
            row["id"]
        ] = {
            "score":
                row["technical_validation_score"]
                if "technical_validation_score"
                in row.keys()
                else None,

            "status":
                row["technical_validation_status"]
                if "technical_validation_status"
                in row.keys()
                else None,

            "flags":
                row["technical_validation_flags"]
                if "technical_validation_flags"
                in row.keys()
                else None,

            "version":
                row["technical_validation_version"]
                if "technical_validation_version"
                in row.keys()
                else None,

            "validated_at":
                row["technical_validated_at"]
                if "technical_validated_at"
                in row.keys()
                else None,
        }

    exact_matches = 0
    mismatches = 0

    print(
        f"{'ID':<10}"
        f"{'SYMBOL':<14}"
        f"{'RUNTIME STATUS':<18}"
        f"{'DB STATUS':<18}"
        f"{'RUNTIME SCORE':<16}"
        f"{'DB SCORE':<16}"
    )

    print("-" * 100)

    for result in results:

        record_id = result["id"]

        persisted = persisted_by_id.get(
            record_id
        )

        if persisted is None:
            continue

        runtime_status = result["status"]
        db_status = persisted["status"]

        runtime_score = result["score"]
        db_score = persisted["score"]

        runtime_flags = result["flags"]
        db_flags = persisted["flags"]

        same_status = (
            runtime_status == db_status
        )

        same_flags = (
            runtime_flags == db_flags
        )

        try:
            same_score = (
                runtime_score == db_score
            )
        except Exception:
            same_score = False

        exact = (
            same_status
            and same_flags
            and same_score
        )

        if exact:
            exact_matches += 1
        else:
            mismatches += 1

        print(
            f"{str(record_id):<10}"
            f"{safe(result['symbol']):<14}"
            f"{safe(runtime_status):<18}"
            f"{safe(db_status):<18}"
            f"{safe(runtime_score):<16}"
            f"{safe(db_score):<16}"
        )

        if not exact:

            print(
                f"  >>> MISMATCH"
            )

            print(
                f"      runtime flags : "
                f"{safe(runtime_flags)}"
            )

            print(
                f"      DB flags      : "
                f"{safe(db_flags)}"
            )

            print(
                f"      DB version    : "
                f"{safe(persisted['version'])}"
            )

            print(
                f"      DB validated  : "
                f"{safe(persisted['validated_at'])}"
            )

    print()

    kv(
        "Exact Runtime/DB Matches",
        exact_matches
    )

    kv(
        "Runtime/DB Mismatches",
        mismatches
    )

    return (
        exact_matches,
        mismatches,
    )


# =============================================================================
# STATUS DISTRIBUTION
# =============================================================================

def print_runtime_distribution(
    status_counter,
    flag_counter,
    errors
):

    banner(
        "REAL RUNTIME VALIDATION DISTRIBUTION"
    )

    print(
        "[STATUS]"
    )

    for status, count in (
        status_counter
        .most_common()
    ):

        print(
            f"  {safe(status):<25}"
            f"{count}"
        )

    print()

    print(
        "[FLAGS]"
    )

    for flag, count in (
        flag_counter
        .most_common(30)
    ):

        print(
            f"  {safe(flag):<40}"
            f"{count}"
        )

    print()

    kv(
        "Runtime Errors",
        len(errors)
    )


# =============================================================================
# RUNTIME CALLCHAIN CONTRACT
# =============================================================================

def print_callchain_contract():

    banner(
        "MARKET_TECHNICAL VALIDATION REAL RUNTIME CALLCHAIN"
    )

    print(
        "RESOLVED FUNCTION:"
    )

    print(
        "    market_technical_engine.validate_row()"
    )

    print()

    print(
        "TRACE PATH PROVEN:"
    )

    print(
        "    REAL market_technical DB row"
    )

    print(
        "          ↓"
    )

    print(
        "    dict(zip(columns, row))"
    )

    print(
        "          ↓"
    )

    print(
        "    REAL production validate_row(row, columns)"
    )

    print(
        "          ↓"
    )

    print(
        "    (score, status, flags)"
    )

    print()

    print(
        "NOT EXECUTED:"
    )

    print(
        "    market_technical_engine.main()"
    )

    print(
        "    ALTER TABLE"
    )

    print(
        "    UPDATE market_technical"
    )

    print(
        "    executemany()"
    )

    print(
        "    commit()"
    )


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(
    total_rows,
    runtime_rows,
    exact_matches,
    mismatches,
    errors
):

    banner(
        "FINAL FORENSIC CONTRACT"
    )

    kv(
        "Database",
        str(DB_PATH)
    )

    kv(
        "Target",
        TARGET_TABLE
    )

    kv(
        "Persisted Rows Available",
        total_rows
    )

    kv(
        "Rows Runtime Traced",
        runtime_rows
    )

    kv(
        "Runtime Validation Errors",
        errors
    )

    kv(
        "Exact Runtime/DB Matches",
        exact_matches
    )

    kv(
        "Runtime/DB Mismatches",
        mismatches
    )

    print()

    kv(
        "READ ONLY",
        "YES"
    )

    kv(
        "SQLite mode",
        "mode=ro"
    )

    kv(
        "query_only",
        "1"
    )

    kv(
        "INSERT",
        "NONE"
    )

    kv(
        "UPDATE",
        "NONE"
    )

    kv(
        "DELETE",
        "NONE"
    )

    kv(
        "ALTER",
        "NONE"
    )

    kv(
        "CREATE",
        "NONE"
    )

    kv(
        "DROP",
        "NONE"
    )

    kv(
        "REPLACE",
        "NONE"
    )

    kv(
        "COMMIT",
        "NONE"
    )

    kv(
        "SOURCE MODIFICATION",
        "NONE"
    )

    kv(
        "SYNTHETIC DATA",
        "NONE"
    )

    kv(
        "INTERPOLATION",
        "NONE"
    )

    kv(
        "FORWARD FILL",
        "NONE"
    )

    kv(
        "BACK FILL",
        "NONE"
    )

    print()

    if errors == 0:

        if mismatches == 0:

            print(
                "FORENSIC RESULT : "
                "REAL VALIDATION FUNCTION REPRODUCES "
                "PERSISTED STATE FOR TRACED ROWS"
            )

        else:

            print(
                "FORENSIC RESULT : "
                "REAL VALIDATION FUNCTION EXECUTES, "
                "BUT RUNTIME OUTPUT DIVERGES FROM "
                "PERSISTED VALIDATION STATE"
            )

    else:

        print(
            "FORENSIC RESULT : "
            "REAL VALIDATION EXECUTION ERRORS DETECTED"
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This result proves execution of the real "
        "validate_row() function against real persisted "
        "market_technical rows."
    )

    print(
        "It deliberately does NOT execute the production "
        "write path."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA MARKET_TECHNICAL_VALIDATION_REAL_RUNTIME_EXECUTION_TRACE_FORENSIC v0.1"
    )

    kv(
        "Mode",
        "READ ONLY"
    )

    kv(
        "Database",
        str(DB_PATH)
    )

    kv(
        "Production Engine",
        str(ENGINE_FILE)
    )

    kv(
        "Target Table",
        TARGET_TABLE
    )

    kv(
        "Production main()",
        "NOT EXECUTED"
    )

    # -------------------------------------------------------------------------
    # SOURCE
    # -------------------------------------------------------------------------

    source = read_engine_source()

    node = resolve_validate_row_ast(
        source
    )

    print_validate_row_source(
        source,
        node
    )

    inspect_main_write_boundary(
        source
    )

    # -------------------------------------------------------------------------
    # DATABASE
    # -------------------------------------------------------------------------

    conn = None

    try:

        conn = connect_read_only()

        verify_read_only(
            conn
        )

        banner(
            "READ-ONLY DATABASE CONTRACT"
        )

        kv(
            "Connected",
            "YES"
        )

        kv(
            "SQLite query_only",
            conn.execute(
                "PRAGMA query_only"
            ).fetchone()[0]
        )

        if not table_exists(
            conn,
            TARGET_TABLE
        ):

            raise RuntimeError(
                f"Missing table: {TARGET_TABLE}"
            )

        columns = get_columns(
            conn
        )

        kv(
            "Target Table",
            TARGET_TABLE
        )

        kv(
            "Column Count",
            len(columns)
        )

        # ---------------------------------------------------------------------
        # MODULE
        # ---------------------------------------------------------------------

        module = load_production_module()

        validate_row = inspect_validation_function(
            module
        )

        # ---------------------------------------------------------------------
        # VERSION
        # ---------------------------------------------------------------------

        banner(
            "ENGINE VERSION"
        )

        engine_version = getattr(
            module,
            "ENGINE_VERSION",
            None
        )

        kv(
            "Runtime ENGINE_VERSION",
            safe(engine_version)
        )

        kv(
            "Expected",
            ENGINE_VERSION_EXPECTED
        )

        # ---------------------------------------------------------------------
        # REAL ROWS
        # ---------------------------------------------------------------------

        rows = acquire_real_rows(
            conn,
            columns,
            TRACE_LIMIT
        )

        # ---------------------------------------------------------------------
        # REAL VALIDATION
        # ---------------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
            errors,
        ) = trace_real_validation(
            validate_row,
            rows,
            columns
        )

        # ---------------------------------------------------------------------
        # COMPARISON
        # ---------------------------------------------------------------------

        (
            exact_matches,
            mismatches,
        ) = compare_runtime_with_persisted(
            rows,
            results
        )

        # ---------------------------------------------------------------------
        # DISTRIBUTION
        # ---------------------------------------------------------------------

        print_runtime_distribution(
            status_counter,
            flag_counter,
            errors
        )

        # ---------------------------------------------------------------------
        # CONTRACT
        # ---------------------------------------------------------------------

        print_callchain_contract()

        total_rows = conn.execute(
            f'''
            SELECT COUNT(*)
            FROM "{TARGET_TABLE}"
            '''
        ).fetchone()[0]

        final_contract(
            total_rows=total_rows,
            runtime_rows=len(rows),
            exact_matches=exact_matches,
            mismatches=mismatches,
            errors=len(errors),
        )

    finally:

        if conn is not None:
            conn.close()

    print()
    print("=" * 100)
    print(
        "ARUNDA MARKET_TECHNICAL_VALIDATION_REAL_RUNTIME_EXECUTION_TRACE_FORENSIC v0.1 COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()