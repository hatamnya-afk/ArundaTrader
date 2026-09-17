# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.3
====================================================================================================

PURPOSE
-------
Resolve the REAL production validate_row() function from the REAL
trace_real_validation() call-site and execute it against the REAL
TECHNICAL_v0.5 contract rows acquired through the REAL production
acquire_real_rows() function.

SAFETY CONTRACT
---------------
- READ ONLY
- SQLite mode=ro
- PRAGMA query_only=1
- Production module is NEVER imported
- Production main() is NEVER executed
- No INSERT
- No UPDATE
- No DELETE
- No ALTER
- No CREATE
- No DROP
- Only exact production AST functions are compiled/executed
- Validator is resolved from the real validation call-site
- Single-row probe MUST PASS before 987-row execution
- Production source SHA256 must remain unchanged
- Database SHA256 must remain unchanged
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import sqlite3
import sys
import textwrap
import traceback
from collections import Counter
from pathlib import Path


# ==================================================================================================
# CONFIGURATION
# ==================================================================================================

PRODUCTION_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

TARGET_TABLE = "market_technical"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

TARGET_ACQUIRE_FUNCTION = "acquire_real_rows"
TARGET_TRACE_FUNCTION = "trace_real_validation"

# This is intentionally only a verifier-side execution limit.
# The production function's default is still resolved from production AST.
TRACE_LIMIT = EXPECTED_CONTRACT_ROWS


# ==================================================================================================
# OUTPUT HELPERS
# ==================================================================================================

def banner(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<55}: {value}")


def passed(message):
    print(f"[PASS] {message}")


def failed(message):
    print(f"[FAIL] {message}")
    raise RuntimeError(message)


def safe(value):
    try:
        return repr(value)
    except Exception:
        return "<UNPRINTABLE>"


# ==================================================================================================
# HASHING
# ==================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def semantic_function_sha256(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    source = ast.unparse(node)

    normalized = "\n".join(
        line.strip()
        for line in source.splitlines()
        if line.strip()
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# ==================================================================================================
# SOURCE LOADING
# ==================================================================================================

def load_production_source() -> str:

    if not PRODUCTION_FILE.exists():
        failed(
            f"Production file not found: {PRODUCTION_FILE}"
        )

    return PRODUCTION_FILE.read_text(
        encoding="utf-8"
    )


def parse_production_source(source: str) -> ast.Module:

    try:
        return ast.parse(
            source,
            filename=str(PRODUCTION_FILE)
        )

    except SyntaxError as exc:
        failed(
            f"Production source AST parse failed: {exc}"
        )


# ==================================================================================================
# AST FUNCTION DISCOVERY
# ==================================================================================================

def collect_functions(tree: ast.AST):

    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            result.setdefault(
                node.name,
                []
            ).append(node)

    return result


def resolve_unique_function(
    tree: ast.AST,
    name: str
):

    functions = collect_functions(tree)

    matches = functions.get(name, [])

    if not matches:
        failed(
            f"Production function not found: {name}"
        )

    if len(matches) != 1:
        failed(
            f"Production function '{name}' is not unique: "
            f"{len(matches)} definitions found"
        )

    return matches[0]


def function_source(
    source: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef
) -> str:

    lines = source.splitlines()

    start = node.lineno - 1
    end = node.end_lineno

    return "\n".join(
        lines[start:end]
    )


# ==================================================================================================
# AST CALL-SITE RESOLUTION
# ==================================================================================================

def extract_call_names(
    node: ast.AST,
    function_name: str
):

    calls = []

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Call
        ):
            continue

        func = child.func

        if isinstance(
            func,
            ast.Name
        ):
            if func.id == function_name:
                calls.append(child)

        elif isinstance(
            func,
            ast.Attribute
        ):
            if func.attr == function_name:
                calls.append(child)

    return calls


def resolve_validator_from_trace(
    trace_node: ast.FunctionDef | ast.AsyncFunctionDef
):

    """
    Resolve validator based on REAL calls inside trace_real_validation().

    We specifically look for a call shaped like:

        validate_row(
            row,
            columns
        )

    The name validate_row is taken from the real call-site.

    We do NOT assume that the function itself must have a hard-coded
    name in the production source.
    """

    candidates = []

    for call in ast.walk(trace_node):

        if not isinstance(
            call,
            ast.Call
        ):
            continue

        if not isinstance(
            call.func,
            ast.Name
        ):
            continue

        if len(call.args) != 2:
            continue

        first = call.args[0]
        second = call.args[1]

        if not isinstance(
            first,
            ast.Name
        ):
            continue

        if not isinstance(
            second,
            ast.Name
        ):
            continue

        if first.id != "row":
            continue

        if second.id != "columns":
            continue

        candidates.append(
            call.func.id
        )

    candidates = sorted(
        set(candidates)
    )

    if not candidates:

        failed(
            "Could not resolve REAL validator from "
            "trace_real_validation() call-site. "
            "Expected a two-argument call using row, columns."
        )

    if len(candidates) != 1:

        failed(
            "Multiple validator candidates resolved from "
            f"trace_real_validation(): {candidates}"
        )

    return candidates[0]


# ==================================================================================================
# AST CONSTANT RESOLUTION
# ==================================================================================================

def literal_value(node):

    try:
        return ast.literal_eval(node)

    except Exception:
        return None


def resolve_module_constants(
    tree: ast.Module
):

    constants = {}

    for node in tree.body:

        if not isinstance(
            node,
            ast.Assign
        ):
            continue

        value = literal_value(
            node.value
        )

        if value is None:
            continue

        for target in node.targets:

            if isinstance(
                target,
                ast.Name
            ):
                constants[target.id] = value

    return constants


# ==================================================================================================
# F-STRING / SQL RECONSTRUCTION
# ==================================================================================================

def reconstruct_ast_string(
    node: ast.AST,
    constants: dict
):

    if isinstance(
        node,
        ast.Constant
    ):

        if isinstance(
            node.value,
            str
        ):
            return node.value

        return str(node.value)

    if isinstance(
        node,
        ast.JoinedStr
    ):

        parts = []

        for value_node in node.values:

            if isinstance(
                value_node,
                ast.Constant
            ):

                parts.append(
                    str(value_node.value)
                )

            elif isinstance(
                value_node,
                ast.FormattedValue
            ):

                expression = value_node.value

                if isinstance(
                    expression,
                    ast.Name
                ):

                    name = expression.id

                    if name in constants:
                        parts.append(
                            str(constants[name])
                        )

                    else:
                        # Runtime contract constants supplied by verifier.
                        runtime_values = {
                            "TARGET_TABLE": TARGET_TABLE,
                            "CONTRACT_TECHNICAL_VERSION":
                                CONTRACT_TECHNICAL_VERSION,
                            "CONTRACT_ENGINE_VERSION":
                                CONTRACT_ENGINE_VERSION,
                            "CONTRACT_SOURCE":
                                CONTRACT_SOURCE,
                        }

                        if name in runtime_values:
                            parts.append(
                                str(runtime_values[name])
                            )

                        else:
                            parts.append(
                                f"<{name}>"
                            )

                else:
                    parts.append(
                        f"<{ast.unparse(expression)}>"
                    )

        return "".join(parts)

    return ast.unparse(node)


def normalize_sql(sql: str):

    return " ".join(
        sql.lower().split()
    )


def reconstruct_sql_from_acquire(
    acquire_node,
    constants
):

    sql_candidates = []

    for node in ast.walk(acquire_node):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        if not isinstance(
            node.func,
            ast.Attribute
        ):
            continue

        if node.func.attr != "execute":
            continue

        if not node.args:
            continue

        sql_node = node.args[0]

        sql = reconstruct_ast_string(
            sql_node,
            constants
        )

        if "select" in sql.lower():

            sql_candidates.append(
                normalize_sql(sql)
            )

    if not sql_candidates:

        failed(
            "Could not reconstruct SELECT SQL from acquire_real_rows()."
        )

    # Prefer the SQL containing the production table.
    matching = [
        sql
        for sql in sql_candidates
        if TARGET_TABLE.lower() in sql
    ]

    if not matching:

        failed(
            "Could not reconstruct SELECT SQL containing "
            f'"{TARGET_TABLE}".'
        )

    return matching[0]


# ==================================================================================================
# SQL SAFETY
# ==================================================================================================

WRITE_SQL_WORDS = (
    "insert ",
    "update ",
    "delete ",
    "alter ",
    "create ",
    "drop ",
    "replace ",
    "vacuum ",
    "attach ",
    "detach ",
)


def verify_sql_safety(sql: str):

    normalized = normalize_sql(sql)

    print()
    print("RECONSTRUCTED SQL:")
    print()
    print(normalized)

    required_fragments = [
        "select *",
        f'from "{TARGET_TABLE}"',
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in required_fragments:

        if fragment not in normalized:

            failed(
                f"Expected SQL fragment missing: {fragment}"
            )

        passed(
            f"SQL fragment: {fragment}"
        )

    for word in WRITE_SQL_WORDS:

        if word in normalized:

            failed(
                f"WRITE SQL detected: {word.strip()}"
            )

    passed("Contract predicates present")
    passed("ORDER BY id DESC preserved")
    passed("LIMIT ? preserved")
    passed("No SQL write operation detected")


# ==================================================================================================
# PRODUCTION AST COMPILATION
# ==================================================================================================

def compile_exact_function(
    node,
    source,
    namespace
):

    function_source_text = function_source(
        source,
        node
    )

    function_source_text = (
        "from __future__ import annotations\n\n"
        + function_source_text
    )

    code = compile(
        function_source_text,
        filename=str(PRODUCTION_FILE),
        mode="exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    if node.name not in namespace:

        failed(
            f"Compiled function missing from namespace: {node.name}"
        )

    return namespace[node.name]


# ==================================================================================================
# SAFE PRODUCTION HELPER DISCOVERY
# ==================================================================================================

def discover_helper_names_for_validator(
    validator_node
):

    names = set()

    for node in ast.walk(
        validator_node
    ):

        if isinstance(
            node,
            ast.Name
        ):

            if isinstance(
                node.ctx,
                ast.Load
            ):

                names.add(
                    node.id
                )

    return names


# ==================================================================================================
# NAMESPACE
# ==================================================================================================

def build_base_namespace(
    constants
):

    namespace = {
        "__name__": "__arunda_runtime_validation__",
        "__file__": str(PRODUCTION_FILE),

        "Counter": Counter,

        "TRACE_LIMIT": TRACE_LIMIT,

        "TARGET_TABLE": TARGET_TABLE,

        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,

        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,

        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,
    }

    namespace.update(
        constants
    )

    # Runtime-safe production helpers.
    namespace["banner"] = banner
    namespace["kv"] = kv
    namespace["safe"] = safe

    return namespace


# ==================================================================================================
# ACQUIRE FUNCTION RUNTIME
# ==================================================================================================

def acquire_real_rows_runtime(
    acquire_function,
    connection
):

    columns = [
        row[1]
        for row in connection.execute(
            f'PRAGMA table_info("{TARGET_TABLE}")'
        ).fetchall()
    ]

    if not columns:

        failed(
            f"No columns discovered for {TARGET_TABLE}"
        )

    rows = acquire_function(
        connection,
        columns,
        EXPECTED_CONTRACT_ROWS
    )

    return columns, rows


# ==================================================================================================
# RUNTIME ROW CONTRACT
# ==================================================================================================

def verify_runtime_rows(
    rows
):

    if len(rows) != EXPECTED_CONTRACT_ROWS:

        failed(
            f"Runtime row count = {len(rows)}, "
            f"expected {EXPECTED_CONTRACT_ROWS}"
        )

    passed(
        f"Runtime row count = {EXPECTED_CONTRACT_ROWS}"
    )

    ids = [
        row["id"]
        for row in rows
    ]

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:

        failed(
            "Runtime IDs are not distinct"
        )

    passed(
        "Runtime distinct IDs = 987"
    )

    if min(ids) != 5923:

        failed(
            f"Runtime MIN ID = {min(ids)}"
        )

    passed(
        "Runtime MIN ID = 5923"
    )

    if max(ids) != 6909:

        failed(
            f"Runtime MAX ID = {max(ids)}"
        )

    passed(
        "Runtime MAX ID = 6909"
    )

    if ids != sorted(
        ids,
        reverse=True
    ):

        failed(
            "Runtime ordering is not id DESC"
        )

    passed(
        "Runtime ordering = id DESC"
    )

    for row in rows:

        if row["technical_version"] != \
                CONTRACT_TECHNICAL_VERSION:

            failed(
                f"Invalid technical_version at id={row['id']}"
            )

        if row["engine_version"] != \
                CONTRACT_ENGINE_VERSION:

            failed(
                f"Invalid engine_version at id={row['id']}"
            )

        if row["source"] != CONTRACT_SOURCE:

            failed(
                f"Invalid source at id={row['id']}"
            )

    passed(
        "Runtime technical_version = TECHNICAL_v0.5"
    )

    passed(
        "Runtime engine_version = TECHNICAL_v0.5"
    )

    passed(
        "Runtime source = REAL_MARKET_HISTORY"
    )


# ==================================================================================================
# VALIDATOR RETURN NORMALIZATION
# ==================================================================================================

def normalize_validation_result(
    result
):

    if not isinstance(
        result,
        tuple
    ):

        raise RuntimeError(
            "validate_row() did not return tuple"
        )

    if len(result) != 3:

        raise RuntimeError(
            "validate_row() return tuple length = "
            f"{len(result)}"
        )

    score, status, flags = result

    return score, status, flags


# ==================================================================================================
# SINGLE ROW PROBE
# ==================================================================================================

def run_validator_probe(
    validator_function,
    row,
    columns
):

    banner(
        "REAL PRODUCTION VALIDATOR — SINGLE ROW PROBE"
    )

    print(
        "The validator is resolved from the REAL "
        "trace_real_validation() call-site."
    )

    print()
    kv(
        "Probe id",
        row["id"]
    )

    kv(
        "Probe symbol",
        row["symbol"]
    )

    kv(
        "Probe timestamp",
        row["timestamp"]
    )

    print()
    print(
        "Executing REAL validate_row(row, columns)..."
    )

    try:

        result = validator_function(
            row,
            columns
        )

        score, status, flags = \
            normalize_validation_result(
                result
            )

    except Exception as exc:

        print()
        print(
            "[FAIL] REAL validator probe failed"
        )

        print(
            f"Exception: {type(exc).__name__}: {exc}"
        )

        print(
            traceback.format_exc()
        )

        raise

    print()
    print(
        "REAL VALIDATOR PROBE OUTPUT:"
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

    passed(
        "REAL validate_row(row, columns) executed successfully"
    )

    passed(
        "Validator returned tuple(score, status, flags)"
    )

    return score, status, flags


# ==================================================================================================
# 987 ROW VALIDATION
# ==================================================================================================

def execute_987_validation(
    validator_function,
    rows,
    columns
):

    banner(
        "987-ROW REAL PRODUCTION RUNTIME VALIDATION"
    )

    print(
        "Executing the SAME REAL production validator "
        "against all REAL Contract rows."
    )

    results = []

    status_counter = Counter()
    flag_counter = Counter()
    score_counter = Counter()

    execution_errors = []

    for index, row in enumerate(
        rows,
        1
    ):

        try:

            result = validator_function(
                row,
                columns
            )

            score, status, flags = \
                normalize_validation_result(
                    result
                )

            status_key = safe(
                status
            )

            score_key = safe(
                score
            )

            status_counter[
                status_key
            ] += 1

            score_counter[
                score_key
            ] += 1

            if flags:

                for flag in str(
                    flags
                ).split(","):

                    flag = flag.strip()

                    if flag:
                        flag_counter[
                            flag
                        ] += 1

            results.append(
                {
                    "id":
                        row["id"],

                    "symbol":
                        row["symbol"],

                    "timestamp":
                        row["timestamp"],

                    "score":
                        score,

                    "status":
                        status,

                    "flags":
                        flags,
                }
            )

        except Exception as exc:

            execution_errors.append(
                {
                    "index":
                        index,

                    "id":
                        row["id"],

                    "symbol":
                        row["symbol"],

                    "error":
                        repr(exc),

                    "traceback":
                        traceback.format_exc(),
                }
            )

    print()
    kv(
        "Rows Submitted",
        len(rows)
    )

    kv(
        "Successful",
        len(results)
    )

    kv(
        "Execution Errors",
        len(execution_errors)
    )

    if execution_errors:

        print()
        print(
            "VALIDATION EXECUTION ERRORS:"
        )

        for error in execution_errors:

            print()
            print(
                f"ROW {error['index']} "
                f"id={error['id']} "
                f"symbol={error['symbol']}"
            )

            print(
                error["error"]
            )

        failed(
            "REAL production validation encountered "
            "execution errors."
        )

    if len(results) != EXPECTED_CONTRACT_ROWS:

        failed(
            f"Successful validation rows = {len(results)}, "
            f"expected {EXPECTED_CONTRACT_ROWS}"
        )

    passed(
        "All 987 Contract rows validated successfully"
    )

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
        execution_errors,
    )


# ==================================================================================================
# ELIGIBLE / REJECTED / REASON ANALYSIS
# ==================================================================================================

def classify_validation_results(
    results
):

    banner(
        "PRODUCTION VALIDATION RESULT ANALYSIS"
    )

    eligible = []
    rejected = []

    reason_counter = Counter()

    for result in results:

        status = str(
            result["status"]
        ).strip().lower()

        flags = result["flags"]

        # ------------------------------------------------------------------
        # IMPORTANT:
        #
        # We do NOT invent a new eligibility rule.
        #
        # The production validator's returned status is the authority.
        #
        # "eligible" is therefore only assigned when the REAL production
        # validator explicitly returns a status whose normalized value
        # is "eligible".
        # ------------------------------------------------------------------

        if status == "eligible":

            eligible.append(
                result
            )

        else:

            rejected.append(
                result
            )

            if flags:

                for flag in str(
                    flags
                ).split(","):

                    flag = flag.strip()

                    if flag:
                        reason_counter[
                            flag
                        ] += 1

            else:

                reason_counter[
                    status
                ] += 1

    kv(
        "Total Validated",
        len(results)
    )

    kv(
        "Eligible",
        len(eligible)
    )

    kv(
        "Rejected / Non-Eligible",
        len(rejected)
    )

    print()
    print(
        "STATUS DISTRIBUTION:"
    )

    status_counter = Counter(
        str(
            row["status"]
        )
        for row in results
    )

    for status, count in status_counter.most_common():

        print(
            f"  {status:<40}: {count}"
        )

    print()
    print(
        "REJECTION / NON-ELIGIBILITY REASONS:"
    )

    if reason_counter:

        for reason, count in \
                reason_counter.most_common():

            print(
                f"  {reason:<40}: {count}"
            )

    else:

        print(
            "  NONE"
        )

    return (
        eligible,
        rejected,
        reason_counter,
    )


# ==================================================================================================
# DATABASE PREFLIGHT
# ==================================================================================================

def open_read_only_database():

    uri = (
        "file:"
        + str(
            DATABASE_FILE.resolve()
        ).replace(
            "\\",
            "/"
        )
        + "?mode=ro"
    )

    connection = sqlite3.connect(
        uri,
        uri=True
    )

    connection.row_factory = sqlite3.Row

    query_only = connection.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if query_only != 1:

        connection.close()

        failed(
            "SQLite PRAGMA query_only is not 1"
        )

    return connection


def database_preflight(
    connection
):

    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    query_only = connection.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    kv(
        "SQLite query_only",
        query_only
    )

    if query_only != 1:

        failed(
            "Database is not query_only"
        )

    total = connection.execute(
        f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
    ).fetchone()[0]

    contract = connection.execute(
        f'''
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchone()[0]

    museum = total - contract

    min_id = connection.execute(
        f'''
        SELECT MIN(id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchone()[0]

    max_id = connection.execute(
        f'''
        SELECT MAX(id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchone()[0]

    distinct_ids = connection.execute(
        f'''
        SELECT COUNT(DISTINCT id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchone()[0]

    kv(
        "Database Total",
        total
    )

    kv(
        "Contract Population",
        contract
    )

    kv(
        "Museum Population",
        museum
    )

    kv(
        "Contract MIN ID",
        min_id
    )

    kv(
        "Contract MAX ID",
        max_id
    )

    kv(
        "Contract DISTINCT IDs",
        distinct_ids
    )

    if total != 6909:
        failed("DATABASE TOTAL mismatch")

    passed(
        "DATABASE TOTAL = 6909"
    )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed("CONTRACT population mismatch")

    passed(
        "CONTRACT = 987"
    )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed("MUSEUM population mismatch")

    passed(
        "MUSEUM = 5922"
    )

    if min_id != 5923:
        failed("CONTRACT MIN ID mismatch")

    if max_id != 6909:
        failed("CONTRACT MAX ID mismatch")

    if distinct_ids != 987:
        failed("CONTRACT DISTINCT ID mismatch")

    passed(
        "CONTRACT ID RANGE = 5923..6909"
    )


# ==================================================================================================
# DATABASE HASH / SIZE
# ==================================================================================================

def database_integrity():

    size = DATABASE_FILE.stat().st_size

    digest = sha256_file(
        DATABASE_FILE
    )

    return size, digest


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.3"
    )

    kv(
        "MODE",
        "READ ONLY / RUNTIME VALIDATION"
    )

    kv(
        "Production File",
        str(PRODUCTION_FILE)
    )

    kv(
        "Database",
        str(DATABASE_FILE)
    )

    kv(
        "Target Function",
        TARGET_ACQUIRE_FUNCTION
    )

    kv(
        "Trace Function",
        TARGET_TRACE_FUNCTION
    )

    kv(
        "Contract",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "Expected Contract Rows",
        EXPECTED_CONTRACT_ROWS
    )

    kv(
        "Expected Museum Rows",
        EXPECTED_MUSEUM_ROWS
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Production main() will NOT be executed."
    )

    print(
        "Production module will NOT be imported."
    )

    print(
        "Only exact production AST functions are executed."
    )

    print(
        "Database = SQLite mode=ro."
    )

    print(
        "PRAGMA query_only = 1."
    )

    print(
        "No database write is permitted."
    )

    # ----------------------------------------------------------------------------------------------
    # SOURCE BEFORE
    # ----------------------------------------------------------------------------------------------

    source_before = load_production_source()

    production_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    banner(
        "PRODUCTION / DATABASE INTEGRITY BEFORE"
    )

    kv(
        "Production SHA256 BEFORE",
        production_hash_before
    )

    database_size_before, database_hash_before = \
        database_integrity()

    kv(
        "Database Size BEFORE",
        database_size_before
    )

    kv(
        "Database SHA256 BEFORE",
        database_hash_before
    )

    # ----------------------------------------------------------------------------------------------
    # AST
    # ----------------------------------------------------------------------------------------------

    tree = parse_production_source(
        source_before
    )

    constants = resolve_module_constants(
        tree
    )

    acquire_node = resolve_unique_function(
        tree,
        TARGET_ACQUIRE_FUNCTION
    )

    trace_node = resolve_unique_function(
        tree,
        TARGET_TRACE_FUNCTION
    )

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    kv(
        "acquire_real_rows semantic SHA256",
        semantic_function_sha256(
            acquire_node
        )
    )

    kv(
        "trace_real_validation semantic SHA256",
        semantic_function_sha256(
            trace_node
        )
    )

    # ----------------------------------------------------------------------------------------------
    # REAL VALIDATOR RESOLUTION
    # ----------------------------------------------------------------------------------------------

    banner(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    validator_name = resolve_validator_from_trace(
        trace_node
    )

    kv(
        "Trace Function",
        TARGET_TRACE_FUNCTION
    )

    kv(
        "REAL Validation Call",
        f"{validator_name}(row, columns)"
    )

    validator_node = resolve_unique_function(
        tree,
        validator_name
    )

    kv(
        "Resolved Validator",
        validator_name
    )

    kv(
        "Validator Start Line",
        validator_node.lineno
    )

    kv(
        "Validator End Line",
        validator_node.end_lineno
    )

    kv(
        "Validator Semantic SHA256",
        semantic_function_sha256(
            validator_node
        )
    )

    passed(
        "Validator resolved from REAL production call-site"
    )

    # ----------------------------------------------------------------------------------------------
    # SQL CONTRACT
    # ----------------------------------------------------------------------------------------------

    banner(
        "PRODUCTION acquire_real_rows() SQL CONTRACT"
    )

    reconstructed_sql = reconstruct_sql_from_acquire(
        acquire_node,
        constants
    )

    verify_sql_safety(
        reconstructed_sql
    )

    # ----------------------------------------------------------------------------------------------
    # DATABASE
    # ----------------------------------------------------------------------------------------------

    connection = open_read_only_database()

    try:

        database_preflight(
            connection
        )

        # ------------------------------------------------------------------------------------------
        # NAMESPACE
        # ------------------------------------------------------------------------------------------

        namespace = build_base_namespace(
            constants
        )

        # ------------------------------------------------------------------------------------------
        # COMPILE ACQUIRE
        # ------------------------------------------------------------------------------------------

        banner(
            "EXACT PRODUCTION acquire_real_rows() COMPILATION"
        )

        acquire_function = compile_exact_function(
            acquire_node,
            source_before,
            namespace
        )

        passed(
            "Exact production acquire_real_rows() compiled"
        )

        # ------------------------------------------------------------------------------------------
        # RUNTIME ACQUIRE
        # ------------------------------------------------------------------------------------------

        banner(
            "EXACT PRODUCTION acquire_real_rows() RUNTIME"
        )

        columns, rows = acquire_real_rows_runtime(
            acquire_function,
            connection
        )

        kv(
            "Runtime Rows Returned",
            len(rows)
        )

        verify_runtime_rows(
            rows
        )

        # ------------------------------------------------------------------------------------------
        # COMPILE VALIDATOR
        # ------------------------------------------------------------------------------------------

        banner(
            "EXACT PRODUCTION VALIDATOR COMPILATION"
        )

        validator_function = compile_exact_function(
            validator_node,
            source_before,
            namespace
        )

        passed(
            "Exact production validator compiled"
        )

        # ------------------------------------------------------------------------------------------
        # PROBE
        # ------------------------------------------------------------------------------------------

        run_validator_probe(
            validator_function,
            rows[0],
            columns
        )

        # ------------------------------------------------------------------------------------------
        # 987 ROW VALIDATION
        # ------------------------------------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
            execution_errors,
        ) = execute_987_validation(
            validator_function,
            rows,
            columns
        )

        # ------------------------------------------------------------------------------------------
        # ANALYSIS
        # ------------------------------------------------------------------------------------------

        (
            eligible,
            rejected,
            reason_counter,
        ) = classify_validation_results(
            results
        )

    finally:

        connection.close()

    # ----------------------------------------------------------------------------------------------
    # SOURCE AFTER
    # ----------------------------------------------------------------------------------------------

    production_hash_after = sha256_file(
        PRODUCTION_FILE
    )

    database_size_after, database_hash_after = \
        database_integrity()

    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER"
    )

    kv(
        "Production SHA256 BEFORE",
        production_hash_before
    )

    kv(
        "Production SHA256 AFTER",
        production_hash_after
    )

    if production_hash_before != production_hash_after:

        failed(
            "Production source changed during runtime verification"
        )

    passed(
        "Production source unchanged"
    )

    kv(
        "Database Size BEFORE",
        database_size_before
    )

    kv(
        "Database Size AFTER",
        database_size_after
    )

    if database_size_before != database_size_after:

        failed(
            "Database size changed during runtime validation"
        )

    passed(
        "Database size unchanged"
    )

    kv(
        "Database SHA256 BEFORE",
        database_hash_before
    )

    kv(
        "Database SHA256 AFTER",
        database_hash_after
    )

    if database_hash_before != database_hash_after:

        failed(
            "Database SHA256 changed during runtime validation"
        )

    passed(
        "Database SHA256 unchanged"
    )

    # ----------------------------------------------------------------------------------------------
    # FINAL
    # ----------------------------------------------------------------------------------------------

    banner(
        "FINAL TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION"
    )

    kv(
        "Runtime Rows",
        len(rows)
    )

    kv(
        "Validated Rows",
        len(results)
    )

    kv(
        "Eligible",
        len(eligible)
    )

    kv(
        "Rejected / Non-Eligible",
        len(rejected)
    )

    kv(
        "Execution Errors",
        len(execution_errors)
    )

    kv(
        "Validator",
        validator_name
    )

    kv(
        "Contract",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "Engine",
        CONTRACT_ENGINE_VERSION
    )

    kv(
        "Source",
        CONTRACT_SOURCE
    )

    print()

    passed(
        "DATABASE READ ONLY"
    )

    passed(
        "PRODUCTION main() NOT EXECUTED"
    )

    passed(
        "PRODUCTION MODULE NOT IMPORTED"
    )

    passed(
        "REAL acquire_real_rows() EXECUTED"
    )

    passed(
        "REAL validator resolved from trace_real_validation()"
    )

    passed(
        "REAL validator single-row probe PASS"
    )

    passed(
        "987 REAL Contract rows validated"
    )

    passed(
        "Production source unchanged"
    )

    passed(
        "Database unchanged"
    )

    print()
    print(
        "FINAL STATUS           : PASS"
    )

    print()
    print(
        f"TECHNICAL CONTRACT {CONTRACT_TECHNICAL_VERSION}"
    )

    print(
        "PRODUCTION RUNTIME VALIDATION COMPLETED"
    )

    print()
    print(
        "===================================================================================================="
    )

    print(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.3 COMPLETE"
    )


# ==================================================================================================
# ENTRYPOINT
# ==================================================================================================

if __name__ == "__main__":

    main()