import ast
import hashlib
import importlib.util
import inspect
import sqlite3
import sys
import traceback
from pathlib import Path


# =============================================================================
# ARUNDA
# TECHNICAL VALIDATION PERSISTED STATE PROVENANCE + RUNTIME FORENSIC v0.1
# =============================================================================
#
# MODE:
#     READ ONLY
#
# PURPOSE:
#     Open the exact provenance boundary between:
#
#         validate_row()
#              ↓
#         score/status/flags
#              ↓
#         validation_results
#              ↓
#         UPDATE market_technical
#              ↓
#         persisted technical_validation_* state
#
# THIS FORENSIC:
#
#     - DOES NOT execute production main()
#     - DOES NOT execute UPDATE
#     - DOES NOT execute executemany()
#     - DOES NOT execute COMMIT
#     - DOES NOT modify production source
#     - DOES NOT create synthetic rows
#
# It performs:
#
#     1. Source SHA256
#     2. AST provenance discovery
#     3. Exact production validate_row() resolution
#     4. Exact validation persistence-boundary discovery
#     5. REAL persisted row acquisition
#     6. REAL validate_row() execution on ONE persisted row
#     7. validation_results tuple reconstruction
#     8. UPDATE parameter mapping reconstruction
#     9. Existing DB state comparison
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "arunda.db"
ENGINE_FILE = PROJECT_DIR / "market_technical_engine.py"

TARGET_TABLE = "market_technical"

TECHNICAL_VERSION_EXPECTED = "TECHNICAL_v0.5"
ENGINE_VERSION_EXPECTED = "0.4.1"

# One REAL row only for the deep provenance trace.
TRACE_ROWS = 1


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<55}: {value}")


def safe(value):
    if value is None:
        return "NULL"
    return str(value)


# =============================================================================
# SOURCE INTEGRITY
# =============================================================================

def sha256_file(path):

    digest = hashlib.sha256()

    with open(path, "rb") as handle:

        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


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

    conn.execute(
        "PRAGMA query_only = ON"
    )

    return conn


def verify_read_only(conn):

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if int(value) != 1:

        raise RuntimeError(
            "READ-ONLY CONTRACT FAILED"
        )


# =============================================================================
# SOURCE
# =============================================================================

def read_source():

    if not ENGINE_FILE.exists():

        raise FileNotFoundError(
            f"Production engine not found: {ENGINE_FILE}"
        )

    return ENGINE_FILE.read_text(
        encoding="utf-8-sig",
        errors="strict"
    )


def parse_source(source):

    return ast.parse(
        source,
        filename=str(ENGINE_FILE)
    )


# =============================================================================
# AST HELPERS
# =============================================================================

def function_name_map(tree):

    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            result[id(node)] = node.name

    return result


def enclosing_function(tree, target_node):

    functions = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):
            continue

        if not hasattr(
            node,
            "lineno"
        ):
            continue

        start = node.lineno
        end = getattr(
            node,
            "end_lineno",
            start
        )

        if (
            start <= target_node.lineno <= end
        ):

            functions.append(
                (
                    end - start,
                    node
                )
            )

    if not functions:
        return "UNKNOWN"

    functions.sort(
        key=lambda item: item[0]
    )

    return functions[0][1].name


def source_segment(source, node):

    try:

        return ast.get_source_segment(
            source,
            node
        )

    except Exception:

        return None


# =============================================================================
# AST: VALIDATE_ROW
# =============================================================================

def discover_validate_row(tree, source):

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

    if len(matches) == 0:

        raise RuntimeError(
            "validate_row() not found"
        )

    if len(matches) > 1:

        raise RuntimeError(
            f"Multiple validate_row() definitions: {len(matches)}"
        )

    node = matches[0]

    banner(
        "AST VALIDATE_ROW DEFINITION"
    )

    kv(
        "Function",
        node.name
    )

    kv(
        "Start Line",
        node.lineno
    )

    kv(
        "End Line",
        getattr(
            node,
            "end_lineno",
            node.lineno
        )
    )

    return node


# =============================================================================
# AST: VALIDATION STATE SYMBOLS
# =============================================================================

VALIDATION_FIELDS = {
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
}

VALIDATION_LOCAL_SYMBOLS = {
    "score",
    "status",
    "flags",
    "validation_results",
    "update_sql",
    "record_id",
}


def discover_validation_state_references(
    tree,
    source
):

    banner(
        "AST PERSISTED VALIDATION STATE PROVENANCE"
    )

    findings = []

    for node in ast.walk(tree):

        segment = source_segment(
            source,
            node
        )

        if not segment:
            continue

        matched = []

        for field in VALIDATION_FIELDS:

            if field in segment:

                matched.append(field)

        if not matched:
            continue

        function = enclosing_function(
            tree,
            node
        )

        findings.append(
            (
                node.lineno,
                function,
                type(node).__name__,
                matched,
                segment.strip(),
            )
        )

    # Deduplicate exact records.
    unique = []

    seen = set()

    for item in findings:

        key = repr(item)

        if key in seen:
            continue

        seen.add(key)

        unique.append(item)

    unique.sort(
        key=lambda item: item[0]
    )

    for (
        line,
        function,
        node_type,
        fields,
        segment,
    ) in unique:

        print(
            f"line={line:<6} "
            f"function={function:<25} "
            f"node={node_type:<18} "
            f"fields={','.join(fields)}"
        )

        print(
            f"    SOURCE: {segment[:240]}"
        )

    kv(
        "Validation-state references",
        len(unique)
    )

    return unique


# =============================================================================
# AST: SCORE / STATUS / FLAGS DATAFLOW
# =============================================================================

def discover_local_dataflow(
    tree,
    source
):

    banner(
        "AST SCORE / STATUS / FLAGS / VALIDATION_RESULTS DATAFLOW"
    )

    findings = []

    for node in ast.walk(tree):

        segment = source_segment(
            source,
            node
        )

        if not segment:
            continue

        matched = []

        for symbol in VALIDATION_LOCAL_SYMBOLS:

            if symbol in segment:

                matched.append(symbol)

        if not matched:
            continue

        function = enclosing_function(
            tree,
            node
        )

        findings.append(
            (
                node.lineno,
                function,
                type(node).__name__,
                matched,
                segment.strip(),
            )
        )

    unique = []

    seen = set()

    for item in findings:

        key = repr(item)

        if key in seen:
            continue

        seen.add(key)

        unique.append(item)

    unique.sort(
        key=lambda item: item[0]
    )

    for (
        line,
        function,
        node_type,
        symbols,
        segment,
    ) in unique:

        print(
            f"line={line:<6} "
            f"function={function:<25} "
            f"node={node_type:<18} "
            f"symbols={','.join(symbols)}"
        )

        print(
            f"    SOURCE: {segment[:240]}"
        )

    kv(
        "Dataflow references",
        len(unique)
    )

    return unique


# =============================================================================
# AST: VALIDATE_ROW CALLS
# =============================================================================

def discover_validate_calls(
    tree,
    source
):

    banner(
        "AST VALIDATE_ROW() CALL SITES"

    )

    calls = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        if not isinstance(
            node.func,
            ast.Name
        ):
            continue

        if node.func.id != "validate_row":
            continue

        function = enclosing_function(
            tree,
            node
        )

        calls.append(
            (
                node.lineno,
                node.col_offset,
                function,
                source_segment(
                    source,
                    node
                ),
            )
        )

    for (
        line,
        column,
        function,
        segment,
    ) in calls:

        print(
            f"Function : {function}"
        )

        print(
            f"Line     : {line}"
        )

        print(
            f"Column   : {column}"
        )

        print(
            f"Source   : {segment}"
        )

        print()

    kv(
        "validate_row() calls",
        len(calls)
    )

    return calls


# =============================================================================
# AST: ASSIGNMENT TO validation_results
# =============================================================================

def discover_validation_results(
    tree,
    source
):

    banner(
        "AST validation_results PROVENANCE"
    )

    findings = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Assign
        ):
            continue

        targets = []

        for target in node.targets:

            if isinstance(
                target,
                ast.Name
            ):

                targets.append(
                    target.id
                )

        if "validation_results" not in targets:
            continue

        findings.append(
            (
                node.lineno,
                enclosing_function(
                    tree,
                    node
                ),
                source_segment(
                    source,
                    node
                ),
            )
        )

    for (
        line,
        function,
        segment,
    ) in findings:

        print(
            f"Function : {function}"
        )

        print(
            f"Line     : {line}"
        )

        print(
            f"Source   : {segment}"
        )

    kv(
        "validation_results assignments",
        len(findings)
    )

    return findings


# =============================================================================
# AST: UPDATE SQL
# =============================================================================

def discover_update_sql(
    tree,
    source
):

    banner(
        "AST UPDATE SQL PERSISTENCE BOUNDARY"
    )

    findings = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Constant
        ):

            value = node.value

            if not isinstance(
                value,
                str
            ):
                continue

            upper = value.upper()

            if (
                "UPDATE MARKET_TECHNICAL"
                in upper
            ):

                findings.append(
                    (
                        node.lineno,
                        enclosing_function(
                            tree,
                            node
                        ),
                        value,
                    )
                )

    for (
        line,
        function,
        sql,
    ) in findings:

        print(
            f"Function : {function}"
        )

        print(
            f"Line     : {line}"
        )

        print(
            "SQL:"
        )

        print(
            sql
        )

        print()

    kv(
        "UPDATE market_technical statements",
        len(findings)
    )

    return findings


# =============================================================================
# AST: EXECUTEMANY / COMMIT
# =============================================================================

def discover_write_operations(
    tree,
    source
):

    banner(
        "AST PRODUCTION WRITE OPERATIONS"

    )

    tokens = [
        "executemany",
        "execute",
        "commit",
        "rollback",
        "ALTER TABLE",
        "UPDATE market_technical",
    ]

    findings = []

    for node in ast.walk(tree):

        segment = source_segment(
            source,
            node
        )

        if not segment:
            continue

        upper = segment.upper()

        matched = []

        for token in tokens:

            if token.upper() in upper:

                matched.append(token)

        if not matched:
            continue

        findings.append(
            (
                node.lineno,
                enclosing_function(
                    tree,
                    node
                ),
                type(node).__name__,
                matched,
                segment.strip(),
            )
        )

    unique = []

    seen = set()

    for item in findings:

        key = repr(item)

        if key in seen:
            continue

        seen.add(key)

        unique.append(item)

    unique.sort(
        key=lambda item: item[0]
    )

    for (
        line,
        function,
        node_type,
        matched,
        segment,
    ) in unique:

        print(
            f"line={line:<6} "
            f"function={function:<25} "
            f"node={node_type:<15} "
            f"tokens={','.join(matched)}"
        )

        print(
            f"    SOURCE: {segment[:260]}"
        )

    return unique


# =============================================================================
# DATABASE DISCOVERY
# =============================================================================

def table_exists(
    conn,
    table
):

    return (
        conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (table,),
        ).fetchone()
        is not None
    )


def get_columns(
    conn,
    table
):

    rows = conn.execute(
        f'''
        PRAGMA table_info("{table}")
        '''
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


# =============================================================================
# REAL CONTRACT ROW
# =============================================================================

def acquire_one_real_row(
    conn,
    columns
):

    banner(
        "REAL PERSISTED CONTRACT ROW"
    )

    query = f"""
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ORDER BY id DESC
        LIMIT 1
    """

    # These are the contract values already established
    # by the preceding forensic.
    #
    # We intentionally discover source/version values rather
    # than inventing alternate records.

    rows = conn.execute(
        f"""
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            TECHNICAL_VERSION_EXPECTED,
        ),
    ).fetchall()

    if not rows:

        raise RuntimeError(
            "No REAL TECHNICAL_v0.5 row found"
        )

    row = rows[0]

    kv(
        "Rows acquired",
        len(rows)
    )

    kv(
        "id",
        safe(row["id"])
    )

    kv(
        "symbol",
        safe(
            row["symbol"]
            if "symbol" in row.keys()
            else None
        )
    )

    kv(
        "timestamp",
        safe(
            row["timestamp"]
            if "timestamp" in row.keys()
            else None
        )
    )

    kv(
        "technical_version",
        safe(
            row["technical_version"]
        )
    )

    kv(
        "engine_version",
        safe(
            row["engine_version"]
        )
    )

    kv(
        "source",
        safe(
            row["source"]
        )
    )

    return row


# =============================================================================
# PRODUCTION MODULE LOAD
# =============================================================================

def load_production_module():

    banner(
        "REAL PRODUCTION MODULE LOAD"
    )

    spec = importlib.util.spec_from_file_location(
        "arunda_market_technical_persisted_state_runtime",
        ENGINE_FILE
    )

    if spec is None:
        raise RuntimeError(
            "Unable to create module spec"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        "arunda_market_technical_persisted_state_runtime"
    ] = module

    spec.loader.exec_module(module)

    kv(
        "Production module",
        ENGINE_FILE.name
    )

    kv(
        "Loaded",
        "YES"
    )

    kv(
        "main() executed",
        "NO"
    )

    return module


# =============================================================================
# RUNTIME VALIDATOR
# =============================================================================

def resolve_validator(module):

    banner(
        "REAL validate_row() RUNTIME RESOLUTION"
    )

    if not hasattr(
        module,
        "validate_row"
    ):

        raise RuntimeError(
            "Production module has no validate_row()"
        )

    function = module.validate_row

    kv(
        "Function",
        repr(function)
    )

    kv(
        "Callable",
        callable(function)
    )

    kv(
        "Signature",
        str(
            inspect.signature(function)
        )
    )

    kv(
        "Runtime source",
        safe(
            inspect.getsourcefile(function)
        )
    )

    return function


# =============================================================================
# PERSISTED STATE EXTRACTION
# =============================================================================

def extract_persisted_state(row):

    return {
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


# =============================================================================
# RUNTIME TRACE
# =============================================================================

def runtime_single_row_trace(
    validate_row,
    row,
    columns,
    module,
):

    banner(
        "REAL SINGLE-ROW END-TO-END VALIDATION TRACE"
    )

    record_id = row["id"]

    symbol = (
        row["symbol"]
        if "symbol" in row.keys()
        else None
    )

    timestamp = (
        row["timestamp"]
        if "timestamp" in row.keys()
        else None
    )

    print("STEP 1 — REAL INPUT ROW")
    print("-" * 100)

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

    print()

    print(
        "STEP 2 — validate_row() INPUT"
    )

    data = dict(
        zip(
            columns,
            row
        )
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
                f"  {field:<32}: "
                f"{safe(data[field])}"
            )

    print()

    print(
        "STEP 3 — REAL PRODUCTION validate_row(row, columns)"
    )

    try:

        runtime_output = validate_row(
            row,
            columns
        )

    except Exception as exc:

        print(
            "RUNTIME VALIDATION ERROR"
        )

        print(
            traceback.format_exc()
        )

        raise

    print(
        f"  raw output: {runtime_output!r}"
    )

    if not isinstance(
        runtime_output,
        tuple
    ):

        raise RuntimeError(
            "validate_row() did not return tuple"
        )

    if len(runtime_output) != 3:

        raise RuntimeError(
            f"Unexpected validate_row() tuple length: "
            f"{len(runtime_output)}"
        )

    score, status, flags = runtime_output

    print()
    print(
        "STEP 4 — REAL VALIDATOR OUTPUT"
    )

    kv(
        "score",
        safe(score)
    )

    kv(
        "status",
        safe(status)
    )

    kv(
        "flags",
        safe(flags)
    )

    # -------------------------------------------------------------------------
    # utc_now()
    # -------------------------------------------------------------------------

    utc_now = getattr(
        module,
        "utc_now",
        None
    )

    if callable(utc_now):

        try:
            validated_at = utc_now()

        except Exception:

            validated_at = "<utc_now() EXECUTION ERROR>"

    else:

        validated_at = "<utc_now() NOT RESOLVED>"

    # -------------------------------------------------------------------------
    # ENGINE_VERSION
    # -------------------------------------------------------------------------

    runtime_engine_version = getattr(
        module,
        "ENGINE_VERSION",
        None
    )

    print()
    print(
        "STEP 5 — RECONSTRUCTED validation_results TUPLE"
    )

    reconstructed = (
        score,
        status,
        flags,
        runtime_engine_version,
        validated_at,
        record_id,
    )

    print(
        "  validation_results.append("
    )

    print(
        f"      {reconstructed!r}"
    )

    print(
        "  )"
    )

    # -------------------------------------------------------------------------
    # UPDATE SQL PARAMETER ORDER
    # -------------------------------------------------------------------------

    print()
    print(
        "STEP 6 — RECONSTRUCTED UPDATE PARAMETER MAPPING"
    )

    print(
        "  UPDATE market_technical"
    )

    print(
        "  SET"
    )

    print(
        "      technical_validation_score = ?"
    )

    print(
        "      technical_validation_status = ?"
    )

    print(
        "      technical_validation_flags = ?"
    )

    print(
        "      technical_validation_version = ?"
    )

    print(
        "      technical_validated_at = ?"
    )

    print(
        "  WHERE id = ?"
    )

    mapping = [
        (
            "technical_validation_score",
            score,
        ),
        (
            "technical_validation_status",
            status,
        ),
        (
            "technical_validation_flags",
            flags,
        ),
        (
            "technical_validation_version",
            runtime_engine_version,
        ),
        (
            "technical_validated_at",
            validated_at,
        ),
        (
            "WHERE id",
            record_id,
        ),
    ]

    print()

    for field, value in mapping:

        print(
            f"  {field:<40}: {safe(value)}"
        )

    # -------------------------------------------------------------------------
    # EXISTING DB STATE
    # -------------------------------------------------------------------------

    print()
    print(
        "STEP 7 — EXISTING PERSISTED DATABASE STATE"
    )

    persisted = extract_persisted_state(
        row
    )

    for key, value in persisted.items():

        print(
            f"  {key:<40}: {safe(value)}"
        )

    # -------------------------------------------------------------------------
    # COMPARISON
    # -------------------------------------------------------------------------

    print()
    print(
        "STEP 8 — RUNTIME VS PERSISTED FIELD-BY-FIELD"
    )

    comparisons = [
        (
            "technical_validation_score",
            score,
            persisted["score"],
        ),
        (
            "technical_validation_status",
            status,
            persisted["status"],
        ),
        (
            "technical_validation_flags",
            flags,
            persisted["flags"],
        ),
        (
            "technical_validation_version",
            runtime_engine_version,
            persisted["version"],
        ),
    ]

    exact_count = 0

    for field, runtime, db in comparisons:

        exact = (
            runtime == db
        )

        if exact:
            exact_count += 1

        state = (
            "MATCH"
            if exact
            else "MISMATCH"
        )

        print(
            f"  [{state:<9}] "
            f"{field:<38} "
            f"runtime={safe(runtime):<30} "
            f"db={safe(db)}"
        )

    print()
    print(
        "NOTE: technical_validated_at is intentionally NOT treated "
        "as an exact-value comparison because runtime utc_now() "
        "naturally produces a new timestamp."
    )

    # -------------------------------------------------------------------------
    # IMPORTANT: NO WRITE
    # -------------------------------------------------------------------------

    print()
    print(
        "STEP 9 — WRITE PATH SIMULATION"
    )

    print(
        "  executemany(update_sql, validation_results)"
    )

    print(
        "  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    )

    print(
        "  SIMULATED ONLY"
    )

    print()

    print(
        "  conn.commit()"
    )

    print(
        "  ^^^^^^^^^^^^^^"
    )

    print(
        "  NOT EXECUTED"
    )

    return {
        "runtime": {
            "score": score,
            "status": status,
            "flags": flags,
            "version": runtime_engine_version,
            "validated_at": validated_at,
        },
        "persisted": persisted,
        "exact_fields": exact_count,
        "mapping": mapping,
    }


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(
    before_sha,
    after_sha,
    runtime_trace,
):

    banner(
        "FINAL FORENSIC CONTRACT"
    )

    kv(
        "Production SHA256 BEFORE",
        before_sha
    )

    kv(
        "Production SHA256 AFTER",
        after_sha
    )

    kv(
        "Production source unchanged",
        before_sha == after_sha
    )

    print()

    kv(
        "Runtime score",
        safe(
            runtime_trace["runtime"]["score"]
        )
    )

    kv(
        "Runtime status",
        safe(
            runtime_trace["runtime"]["status"]
        )
    )

    kv(
        "Runtime flags",
        safe(
            runtime_trace["runtime"]["flags"]
        )
    )

    print()

    kv(
        "Persisted score",
        safe(
            runtime_trace["persisted"]["score"]
        )
    )

    kv(
        "Persisted status",
        safe(
            runtime_trace["persisted"]["status"]
        )

    )

    kv(
        "Persisted flags",
        safe(
            runtime_trace["persisted"]["flags"]
        )
    )

    kv(
        "Persisted validation version",
        safe(
            runtime_trace["persisted"]["version"]
        )
    )

    print()

    print(
        "READ ONLY                                      : YES"
    )

    print(
        "SQLite URI                                    : mode=ro"
    )

    print(
        "SQLite query_only                             : 1"
    )

    print(
        "PRODUCTION main()                             : NOT EXECUTED"
    )

    print(
        "UPDATE market_technical                       : NOT EXECUTED"
    )

    print(
        "executemany()                                 : NOT EXECUTED"
    )

    print(
        "COMMIT                                         : NOT EXECUTED"
    )

    print(
        "SOURCE MODIFICATION                            : NONE"
    )

    print(
        "SYNTHETIC DATA                                 : NONE"
    )

    print(
        "INTERPOLATION                                 : NONE"
    )

    print(
        "FORWARD FILL                                  : NONE"
    )

    print(
        "BACK FILL                                     : NONE"
    )

    print()

    print(
        "FORENSIC RESULT:"
    )

    print(
        "The exact production validator was executed against "
        "one REAL persisted contract row."
    )

    print(
        "The persistence tuple and UPDATE parameter mapping "
        "were reconstructed without executing the write."
    )

    print(
        "Existing persisted validation state was compared "
        "field-by-field against the reconstructed runtime state."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL VALIDATION PERSISTED STATE "
        "PROVENANCE + RUNTIME FORENSIC v0.1"
    )

    print(
        "MODE                     : READ ONLY / AST + RUNTIME"
    )

    print(
        f"Production Engine        : {ENGINE_FILE}"
    )

    print(
        f"Database                 : {DB_PATH}"
    )

    print(
        f"Target                   : {TARGET_TABLE}"
    )

    print(
        "Production main()        : WILL NOT BE EXECUTED"
    )

    print(
        "Production write path    : WILL NOT BE EXECUTED"
    )

    # -------------------------------------------------------------------------
    # SOURCE BEFORE
    # -------------------------------------------------------------------------

    before_sha = sha256_file(
        ENGINE_FILE
    )

    banner(
        "PRODUCTION SOURCE INTEGRITY BEFORE"
    )

    kv(
        "SHA256",
        before_sha
    )

    source = read_source()

    # -------------------------------------------------------------------------
    # AST
    # -------------------------------------------------------------------------

    tree = parse_source(
        source
    )

    banner(
        "PRODUCTION AST"
    )

    print(
        "AST Parse                                      : SUCCESS"
    )

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        )
    ]

    kv(
        "Production Functions",
        len(functions)
    )

    discover_validate_row(
        tree,
        source
    )

    discover_validate_calls(
        tree,
        source
    )

    discover_validation_state_references(
        tree,
        source
    )

    discover_local_dataflow(
        tree,
        source
    )

    discover_validation_results(
        tree,
        source
    )

    discover_update_sql(
        tree,
        source
    )

    discover_write_operations(
        tree,
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
            conn,
            TARGET_TABLE
        )

        kv(
            "Target table",
            TARGET_TABLE
        )

        kv(
            "Column count",
            len(columns)
        )

        # ---------------------------------------------------------------------
        # CONTRACT POPULATION
        # ---------------------------------------------------------------------

        total = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM "{TARGET_TABLE}"
            WHERE technical_version = ?
            """,
            (
                TECHNICAL_VERSION_EXPECTED,
            ),
        ).fetchone()[0]

        kv(
            "TECHNICAL_v0.5 rows",
            total
        )

        if total == 0:

            raise RuntimeError(
                "No TECHNICAL_v0.5 contract rows found"
            )

        # ---------------------------------------------------------------------
        # MODULE
        # ---------------------------------------------------------------------

        module = load_production_module()

        runtime_engine_version = getattr(
            module,
            "ENGINE_VERSION",
            None
        )

        banner(
            "ENGINE VERSION"
        )

        kv(
            "Runtime ENGINE_VERSION",
            safe(runtime_engine_version)
        )

        kv(
            "Expected",
            ENGINE_VERSION_EXPECTED
        )

        # ---------------------------------------------------------------------
        # REAL ROW
        # ---------------------------------------------------------------------

        row = acquire_one_real_row(
            conn,
            columns
        )

        # ---------------------------------------------------------------------
        # VALIDATOR
        # ---------------------------------------------------------------------

        validate_row = resolve_validator(
            module
        )

        # ---------------------------------------------------------------------
        # DEEP TRACE
        # ---------------------------------------------------------------------

        runtime_trace = runtime_single_row_trace(
            validate_row,
            row,
            columns,
            module,
        )

    finally:

        if conn is not None:

            conn.close()

    # -------------------------------------------------------------------------
    # SOURCE AFTER
    # -------------------------------------------------------------------------

    after_sha = sha256_file(
        ENGINE_FILE
    )

    banner(
        "PRODUCTION SOURCE INTEGRITY AFTER"
    )

    kv(
        "SHA256 BEFORE",
        before_sha
    )

    kv(
        "SHA256 AFTER",
        after_sha
    )

    if before_sha == after_sha:

        print(
            "[PASS] Production source unchanged."
        )

    else:

        print(
            "[FAIL] Production source changed."
        )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    final_contract(
        before_sha,
        after_sha,
        runtime_trace,
    )

    print()
    print("=" * 100)

    print(
        "ARUNDA TECHNICAL VALIDATION PERSISTED STATE "
        "PROVENANCE + RUNTIME FORENSIC v0.1 COMPLETE"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()