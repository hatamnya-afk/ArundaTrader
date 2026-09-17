# -*- coding: utf-8 -*-

"""
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v1.2

PURPOSE
-------
READ-ONLY production runtime validation.

Execution chain:

    exact production AST
        |
        +--> acquire_real_rows()
        |
        +--> real persisted TECHNICAL_v0.5 rows
        |
        +--> exact trace_real_validation()
        |
        +--> exact validator call:
                validate_row(row, columns)
        |
        +--> exact production validate_row()
        |
        +--> PASS / FAIL

IMPORTANT
---------
- production main() is NEVER executed
- production module is NEVER imported
- database is opened using SQLite URI mode=ro
- PRAGMA query_only=1 is explicitly activated
- no INSERT / UPDATE / DELETE / ALTER / CREATE / DROP
- no synthetic rows
- no interpolation
- no forward/back fill
- no eligible/rejected interpretation before validator execution succeeds
"""

import ast
import hashlib
import inspect
import os
import re
import sqlite3
import sys
import traceback
import importlib.util
from collections import Counter


# ============================================================================
# CONFIG
# ============================================================================

VERSION = "v1.2"

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

PRODUCTION_FILE = os.path.join(
    BASE_DIR,
    "market_technical_validation_engine_v0.4.1.py",
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "arunda.db",
)

TARGET_TABLE = "market_technical"

TRACE_LIMIT = 987

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

TRACE_FUNCTION = "trace_real_validation"
ACQUIRE_FUNCTION = "acquire_real_rows"
VALIDATOR_SYMBOL = "validate_row"


# ============================================================================
# OUTPUT
# ============================================================================

def banner(text):
    print()
    print("=" * 100)
    print(text)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<58} {value}")


def passed(text):
    print(f"[PASS] {text}")


def failed(text):
    raise RuntimeError(text)


def safe(value):
    try:
        return repr(value)
    except Exception:
        return "<UNREPRESENTABLE>"


# ============================================================================
# HASHING
# ============================================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def semantic_sha256(node):
    text = ast.unparse(node)

    normalized = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# ============================================================================
# SOURCE / AST
# ============================================================================

def read_source(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def parse_source(source):
    return ast.parse(
        source,
        filename=PRODUCTION_FILE,
    )


def unique_function(tree, name):
    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]

    if len(nodes) == 0:
        failed(
            f"Production function '{name}' was not found."
        )

    if len(nodes) > 1:
        failed(
            f"Production function '{name}' is ambiguous: "
            f"{len(nodes)} definitions found."
        )

    return nodes[0]


def source_segment(source, node):
    segment = ast.get_source_segment(
        source,
        node,
    )

    if not segment:
        failed(
            f"Cannot recover exact source segment for "
            f"{type(node).__name__}."
        )

    return segment


# ============================================================================
# AST CALL RESOLUTION
# ============================================================================

def resolve_exact_validator_call(
    trace_node,
):
    """
    Resolve the REAL Call node inside trace_real_validation().

    Required call:

        validate_row(
            row,
            columns
        )

    No guessing based on function names elsewhere.
    """

    candidates = []

    for node in ast.walk(trace_node):

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

        if node.func.id != VALIDATOR_SYMBOL:
            continue

        candidates.append(node)

    if len(candidates) == 0:
        failed(
            "No exact validate_row(...) Call was found "
            "inside trace_real_validation()."
        )

    if len(candidates) > 1:
        failed(
            "Multiple validate_row(...) Calls were found "
            "inside trace_real_validation(); resolution is ambiguous."
        )

    call = candidates[0]

    if len(call.args) != 2:
        failed(
            "Production validate_row call does not have "
            "exactly two positional arguments."
        )

    arg0 = call.args[0]
    arg1 = call.args[1]

    if not isinstance(
        arg0,
        ast.Name,
    ) or arg0.id != "row":
        failed(
            "First validate_row() argument is not exact 'row'."
        )

    if not isinstance(
        arg1,
        ast.Name,
    ) or arg1.id != "columns":
        failed(
            "Second validate_row() argument is not exact 'columns'."
        )

    return call


# ============================================================================
# SQL AST STRUCTURAL ANALYSIS
# ============================================================================

def flatten_string_expression(node):
    """
    Recover SQL from:

        f'''
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE ...
        '''

    correctly.

    IMPORTANT:
    Do NOT inspect only ast.Constant nodes.

    f-string SQL is represented as JoinedStr + FormattedValue.
    """

    if isinstance(
        node,
        ast.Constant,
    ):
        if isinstance(
            node.value,
            str,
        ):
            return node.value

        return ""

    if isinstance(
        node,
        ast.JoinedStr,
    ):

        parts = []

        for value in node.values:

            if isinstance(
                value,
                ast.Constant,
            ):
                if isinstance(
                    value.value,
                    str,
                ):
                    parts.append(
                        value.value
                    )

            elif isinstance(
                value,
                ast.FormattedValue,
            ):

                if isinstance(
                    value.value,
                    ast.Name,
                ):
                    parts.append(
                        "{"
                        + value.value.id
                        + "}"
                    )

                else:
                    parts.append(
                        "{"
                        + ast.unparse(
                            value.value
                        )
                        + "}"
                    )

        return "".join(parts)

    return ast.unparse(node)


def normalize_sql(text):
    text = text.lower()

    text = text.replace(
        "\r",
        " ",
    )

    text = text.replace(
        "\n",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def extract_execute_sql(acquire_node):
    """
    Find the exact SQL expression passed to conn.execute().
    """

    execute_calls = []

    for node in ast.walk(
        acquire_node
    ):

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

        if node.func.attr != "execute":
            continue

        if not node.args:
            continue

        execute_calls.append(node)

    if len(execute_calls) != 1:
        failed(
            "Expected exactly one conn.execute() call "
            f"inside acquire_real_rows(); found "
            f"{len(execute_calls)}."
        )

    execute_call = execute_calls[0]

    sql_expression = execute_call.args[0]

    sql_text = flatten_string_expression(
        sql_expression
    )

    return (
        sql_text,
        sql_expression,
        execute_call,
    )


def verify_sql_contract(
    acquire_node,
):
    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    sql_text, sql_expression, execute_call = (
        extract_execute_sql(
            acquire_node
        )
    )

    normalized = normalize_sql(
        sql_text
    )

    print()
    print(
        "AST SQL RECONSTRUCTION:"
    )

    print(
        normalized
    )

    print()
    print(
        "AST SQL DYNAMIC EXPRESSIONS:"
    )

    dynamic_names = []

    for node in ast.walk(
        sql_expression
    ):

        if isinstance(
            node,
            ast.FormattedValue,
        ):

            dynamic = ast.unparse(
                node.value
            )

            dynamic_names.append(
                dynamic
            )

    for item in dynamic_names:
        print(
            f"  {item}"
        )

    # ------------------------------------------------------------------
    # Structural fragments
    # ------------------------------------------------------------------

    required_fragments = [
        "select *",
        "from",
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in required_fragments:

        if fragment not in normalized:
            failed(
                "Expected SQL fragment missing: "
                + fragment
            )

        passed(
            "SQL contract fragment: "
            + fragment
        )

    # ------------------------------------------------------------------
    # TARGET_TABLE must remain dynamic
    # ------------------------------------------------------------------

    target_table_found = False

    for node in ast.walk(
        sql_expression
    ):

        if isinstance(
            node,
            ast.FormattedValue,
        ):

            if isinstance(
                node.value,
                ast.Name,
            ):

                if node.value.id == "TARGET_TABLE":
                    target_table_found = True

    if not target_table_found:
        failed(
            "TARGET_TABLE dynamic expression was not "
            "preserved in production SQL AST."
        )

    passed(
        "TARGET_TABLE expression preserved"
    )

    # ------------------------------------------------------------------
    # SQL write safety
    # ------------------------------------------------------------------

    forbidden_sql = re.compile(
        r"\b("
        r"insert|update|delete|alter|drop|create|replace|"
        r"vacuum|reindex|attach|detach"
        r")\b",
        re.IGNORECASE,
    )

    if forbidden_sql.search(
        normalized
    ):
        failed(
            "Forbidden SQL write/DDL operation detected "
            "inside acquire_real_rows()."
        )

    passed(
        "No SQL write operation detected"
    )

    # ------------------------------------------------------------------
    # Exact parameter tuple
    # ------------------------------------------------------------------

    if len(
        execute_call.args
    ) < 2:

        failed(
            "conn.execute() does not have the expected "
            "SQL parameter argument."
        )

    parameter_expression = (
        execute_call.args[1]
    )

    parameter_names = []

    for node in ast.walk(
        parameter_expression
    ):

        if isinstance(
            node,
            ast.Name,
        ):

            parameter_names.append(
                node.id
            )

    expected_parameters = [
        "CONTRACT_TECHNICAL_VERSION",
        "CONTRACT_ENGINE_VERSION",
        "CONTRACT_SOURCE",
        "limit",
    ]

    for name in expected_parameters:

        if name not in parameter_names:
            failed(
                "Expected SQL parameter binding missing: "
                + name
            )

    passed(
        "SQL parameter binding preserved"
    )

    return normalized


# ============================================================================
# READ-ONLY DATABASE
# ============================================================================

def open_read_only_database():
    """
    Open SQLite through URI mode=ro.

    Then explicitly activate query_only.

    We verify the actual connection state rather than assuming
    mode=ro alone is sufficient.
    """

    if not os.path.exists(
        DATABASE_FILE
    ):
        failed(
            f"Database not found: {DATABASE_FILE}"
        )

    uri = (
        "file:"
        + DATABASE_FILE.replace(
            "\\",
            "/",
        )
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    # Production returns rows that are accessed as row["field"].
    conn.row_factory = sqlite3.Row

    # Explicitly activate query_only.
    conn.execute(
        "PRAGMA query_only = 1"
    )

    state = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if state != 1:
        conn.close()

        failed(
            "SQLite PRAGMA query_only is not 1."
        )

    return conn


def database_preflight(conn):
    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    kv(
        "SQLite query_only",
        query_only,
    )

    if query_only != 1:
        failed(
            "Database is not in query_only mode."
        )

    total = conn.execute(
        f'''
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        '''
    ).fetchone()[0]

    contract = conn.execute(
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
        ),
    ).fetchone()[0]

    museum = total - contract

    min_id, max_id, distinct_ids = conn.execute(
        f'''
        SELECT
            MIN(id),
            MAX(id),
            COUNT(DISTINCT id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        ),
    ).fetchone()

    kv(
        "Database Total",
        total,
    )

    kv(
        "Contract Population",
        contract,
    )

    kv(
        "Museum Population",
        museum,
    )

    kv(
        "Contract MIN ID",
        min_id,
    )

    kv(
        "Contract MAX ID",
        max_id,
    )

    kv(
        "Contract DISTINCT IDs",
        distinct_ids,
    )

    if total != (
        EXPECTED_CONTRACT_ROWS
        + EXPECTED_MUSEUM_ROWS
    ):
        failed(
            f"DATABASE TOTAL mismatch: "
            f"{total}"
        )

    passed(
        f"DATABASE TOTAL = {total}"
    )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            f"CONTRACT population mismatch: "
            f"{contract}"
        )

    passed(
        f"CONTRACT = {contract}"
    )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            f"MUSEUM population mismatch: "
            f"{museum}"
        )

    passed(
        f"MUSEUM = {museum}"
    )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            "CONTRACT DISTINCT IDS mismatch."
        )

    passed(
        f"CONTRACT DISTINCT IDS = {distinct_ids}"
    )


# ============================================================================
# EXACT PRODUCTION FUNCTION COMPILATION
# ============================================================================

def compile_exact_function(
    node,
    source,
    runtime_globals,
):
    """
    Compile ONLY the requested production FunctionDef.

    No production module import.
    No production main().
    """

    function_source = source_segment(
        source,
        node,
    )

    wrapper = (
        "def __arunda_compile_wrapper__():\n"
        + "\n".join(
            "    " + line
            for line in function_source.splitlines()
        )
        + "\n"
    )

    namespace = dict(
        runtime_globals
    )

    code = compile(
        wrapper,
        PRODUCTION_FILE,
        "exec",
    )

    exec(
        code,
        namespace,
        namespace,
    )

    # The nested definition is created when wrapper executes.
    wrapper_fn = namespace[
        "__arunda_compile_wrapper__"
    ]

    # We need to extract the resulting function.
    local_namespace = {}

    exec(
        function_source,
        namespace,
        local_namespace,
    )

    if node.name not in local_namespace:
        failed(
            "Exact production function compilation "
            f"did not produce '{node.name}'."
        )

    return local_namespace[
        node.name
    ]


# ============================================================================
# ACQUIRE RUNTIME
# ============================================================================

def production_runtime_globals():
    def runtime_banner(text):
        banner(text)

    def runtime_kv(key, value):
        kv(key, value)

    return {
        "TRACE_LIMIT": TRACE_LIMIT,
        "TARGET_TABLE": TARGET_TABLE,
        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,
        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,
        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,
        "banner": runtime_banner,
        "kv": runtime_kv,
    }


def execute_exact_acquisition(
    acquire_function,
    conn,
):
    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    # Exact production signature:
    #
    # acquire_real_rows(
    #     conn,
    #     columns,
    #     limit=TRACE_LIMIT
    # )
    #
    # Production body does not actually use columns.
    # We nevertheless provide the actual DB columns.

    columns = [
        row[1]
        for row in conn.execute(
            f'''
            PRAGMA table_info("{TARGET_TABLE}")
            '''
        ).fetchall()
    ]

    rows = acquire_function(
        conn,
        columns,
        TRACE_LIMIT,
    )

    kv(
        "Runtime Rows Returned",
        len(rows),
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Runtime acquisition returned "
            f"{len(rows)} rows; expected "
            f"{EXPECTED_CONTRACT_ROWS}."
        )

    passed(
        f"Runtime acquisition = {len(rows)} rows"
    )

    return (
        rows,
        columns,
    )


# ============================================================================
# RUNTIME ACQUISITION VERIFICATION
# ============================================================================

def verify_acquired_rows(
    rows,
):
    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime row count mismatch."
        )

    ids = []

    previous_id = None

    for row in rows:

        # sqlite3.Row is required.
        if not isinstance(
            row,
            sqlite3.Row,
        ):
            failed(
                "Production acquisition rows are not "
                "sqlite3.Row objects."
            )

        record_id = row["id"]

        ids.append(
            record_id
        )

        if previous_id is not None:

            if record_id >= previous_id:
                failed(
                    "Runtime ordering is not strict "
                    "id DESC."
                )

        previous_id = record_id

        if row["technical_version"] != (
            CONTRACT_TECHNICAL_VERSION
        ):
            failed(
                "Runtime technical_version mismatch."
            )

        if row["engine_version"] != (
            CONTRACT_ENGINE_VERSION
        ):
            failed(
                "Runtime engine_version mismatch."
            )

        if row["source"] != (
            CONTRACT_SOURCE
        ):
            failed(
                "Runtime source mismatch."
            )

    passed(
        f"Runtime row count = {len(rows)}"
    )

    if len(
        set(ids)
    ) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime distinct IDs mismatch."
        )

    passed(
        f"Runtime distinct IDs = {len(set(ids))}"
    )

    passed(
        f"Runtime MIN ID = {min(ids)}"
    )

    passed(
        f"Runtime MAX ID = {max(ids)}"
    )

    passed(
        "Runtime ordering = id DESC"
    )

    passed(
        "Runtime technical_version = "
        + CONTRACT_TECHNICAL_VERSION
    )

    passed(
        "Runtime engine_version = "
        + CONTRACT_ENGINE_VERSION
    )

    passed(
        "Runtime source = "
        + CONTRACT_SOURCE
    )


# ============================================================================
# VALIDATOR MODULE DISCOVERY
# ============================================================================

def candidate_python_files():
    result = []

    for name in os.listdir(
        BASE_DIR
    ):

        if not name.endswith(
            ".py"
        ):
            continue

        full = os.path.join(
            BASE_DIR,
            name,
        )

        if os.path.isfile(
            full
        ):
            result.append(
                full
            )

    return sorted(
        result
    )


def find_validator_definitions():
    """
    Search local production Python source for validate_row.

    This is NOT execution.

    It is AST discovery only.
    """

    candidates = []

    for path in candidate_python_files():

        # Never treat this validation script itself
        # as production validator source.
        if os.path.abspath(
            path
        ) == os.path.abspath(
            __file__
        ):
            continue

        try:
            source = read_source(
                path
            )

            tree = ast.parse(
                source,
                filename=path,
            )

        except Exception:
            continue

        for node in ast.walk(
            tree
        ):

            if isinstance(
                node,
                ast.FunctionDef,
            ) and node.name == VALIDATOR_SYMBOL:

                candidates.append(
                    (
                        path,
                        source,
                        tree,
                        node,
                    )
                )

    return candidates


def resolve_real_validator_source(
    production_tree,
):
    """
    Resolve validate_row from the production dependency graph.

    Priority:
      1. actual imported module binding
      2. production-local definition
      3. unique project source definition

    If multiple external definitions exist, FAIL.
    """

    banner(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    # ------------------------------------------------------------------
    # First: inspect actual production imports.
    # ------------------------------------------------------------------

    import_candidates = []

    for node in production_tree.body:

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            for alias in node.names:

                if alias.name == VALIDATOR_SYMBOL:

                    import_candidates.append(
                        (
                            node.module,
                            alias.name,
                            alias.asname,
                        )
                    )

        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if alias.asname == VALIDATOR_SYMBOL:

                    import_candidates.append(
                        (
                            alias.name,
                            VALIDATOR_SYMBOL,
                            alias.asname,
                        )
                    )

    if import_candidates:
        print()
        print(
            "PRODUCTION IMPORT BINDINGS:"
        )

        for item in import_candidates:
            print(
                f"  module={item[0]!r} "
                f"symbol={item[1]!r} "
                f"alias={item[2]!r}"
            )

    # ------------------------------------------------------------------
    # Production-local definition
    # ------------------------------------------------------------------

    local_defs = [
        node
        for node in production_tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
        and node.name == VALIDATOR_SYMBOL
    ]

    if len(local_defs) == 1:

        passed(
            "validate_row() resolved as "
            "production-local FunctionDef."
        )

        return (
            PRODUCTION_FILE,
            read_source(PRODUCTION_FILE),
            production_tree,
            local_defs[0],
        )

    # ------------------------------------------------------------------
    # Search project source.
    # ------------------------------------------------------------------

    candidates = find_validator_definitions()

    if len(candidates) == 0:
        failed(
            "No production validate_row() definition "
            "could be resolved from project AST."
        )

    # If actual import binding exists, restrict to its module.
    if import_candidates:

        modules = {
            item[0]
            for item in import_candidates
            if item[0]
        }

        filtered = []

        for candidate in candidates:

            path = candidate[0]
            basename = os.path.splitext(
                os.path.basename(path)
            )[0]

            if basename in modules:
                filtered.append(
                    candidate
                )

        if len(filtered) == 1:

            candidates = filtered

        elif len(filtered) > 1:

            failed(
                "Multiple validate_row() definitions "
                "match the production import binding."
            )

    # ------------------------------------------------------------------
    # Unique project definition
    # ------------------------------------------------------------------

    if len(candidates) != 1:

        details = []

        for path, _, _, node in candidates:

            details.append(
                f"{path}:{node.lineno}"
            )

        failed(
            "validate_row() resolution is ambiguous. "
            "Candidates:\n  "
            + "\n  ".join(details)
        )

    path, source, tree, node = candidates[0]

    passed(
        "REAL validate_row() source resolved:"
    )

    kv(
        "Validator File",
        path,
    )

    kv(
        "Validator Definition Line",
        node.lineno,
    )

    return (
        path,
        source,
        tree,
        node,
    )


# ============================================================================
# VALIDATOR DEPENDENCY COMPILATION
# ============================================================================

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def collect_called_names(function_node):
    names = set()

    for node in ast.walk(
        function_node
    ):

        if isinstance(
            node,
            ast.Call,
        ):

            if isinstance(
                node.func,
                ast.Name,
            ):
                names.add(
                    node.func.id
                )

    return names


def collect_global_names(function_node):
    names = set()

    arguments = set()

    for arg in (
        list(function_node.args.posonlyargs)
        + list(function_node.args.args)
        + list(function_node.args.kwonlyargs)
    ):
        arguments.add(
            arg.arg
        )

    if function_node.args.vararg:
        arguments.add(
            function_node.args.vararg.arg
        )

    if function_node.args.kwarg:
        arguments.add(
            function_node.args.kwarg.arg
        )

    for node in ast.walk(
        function_node
    ):

        if isinstance(
            node,
            ast.Name,
        ):

            if isinstance(
                node.ctx,
                ast.Load,
            ):

                if node.id not in arguments:
                    names.add(
                        node.id
                    )

    return names


def extract_definitions(
    tree,
):
    functions = {}
    assignments = {}

    for node in tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):
            functions[
                node.name
            ] = node

        elif isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name,
                ):
                    assignments[
                        target.id
                    ] = node

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            if isinstance(
                node.target,
                ast.Name,
            ):
                assignments[
                    node.target.id
                ] = node

    return (
        functions,
        assignments,
    )


def compile_validator_exact(
    validator_path,
    validator_source,
    validator_tree,
    validator_node,
):
    """
    Compile the exact validator FunctionDef and only the
    required AST dependencies.

    No importlib import of the production module.
    No module top-level execution.
    """

    banner(
        "EXACT PRODUCTION VALIDATOR COMPILATION"
    )

    functions, assignments = extract_definitions(
        validator_tree
    )

    namespace = dict(
        SAFE_BUILTINS
    )

    namespace[
        "__builtins__"
    ] = {
        name: SAFE_BUILTINS[name]
        for name in SAFE_BUILTINS
    }

    required = set()

    queue = [
        validator_node
    ]

    visited = set()

    while queue:

        current = queue.pop()

        identity = id(
            current
        )

        if identity in visited:
            continue

        visited.add(
            identity
        )

        names = collect_global_names(
            current
        )

        for name in names:

            if name in SAFE_BUILTINS:
                continue

            if name in functions:

                if name == VALIDATOR_SYMBOL:
                    continue

                required.add(
                    name
                )

                queue.append(
                    functions[name]
                )

            elif name in assignments:

                required.add(
                    name
                )

    # ------------------------------------------------------------------
    # Compile assignments required by validator.
    # ------------------------------------------------------------------

    assignment_nodes = []

    for name in sorted(
        required
    ):

        if name in assignments:

            assignment_nodes.append(
                assignments[name]
            )

    # ------------------------------------------------------------------
    # Compile required helper functions.
    # ------------------------------------------------------------------

    helper_nodes = []

    for name in sorted(
        required
    ):

        if name in functions:

            helper_nodes.append(
                functions[name]
            )

    # ------------------------------------------------------------------
    # Build exact AST module.
    # ------------------------------------------------------------------

    module_body = []

    # Required assignments first.
    module_body.extend(
        assignment_nodes
    )

    # Helper functions.
    module_body.extend(
        helper_nodes
    )

    # Exact validator last.
    module_body.append(
        validator_node
    )

    module = ast.Module(
        body=module_body,
        type_ignores=[],
    )

    ast.fix_missing_locations(
        module
    )

    namespace[
        "__name__"
    ] = "__arunda_exact_validator__"

    try:

        code = compile(
            module,
            validator_path,
            "exec",
        )

        exec(
            code,
            namespace,
            namespace,
        )

    except Exception as exc:

        print()
        print(
            "EXACT VALIDATOR COMPILATION ERROR:"
        )

        print(
            traceback.format_exc()
        )

        failed(
            "Exact production validate_row() "
            "could not be compiled."
        )

    if VALIDATOR_SYMBOL not in namespace:
        failed(
            "Compiled namespace does not contain "
            "exact validate_row()."
        )

    validator = namespace[
        VALIDATOR_SYMBOL
    ]

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    signature = inspect.signature(
        validator
    )

    kv(
        "Resolved Validator Signature",
        signature,
    )

    parameters = list(
        signature.parameters.values()
    )

    if len(parameters) != 2:
        failed(
            "Production validate_row() does not have "
            "exactly two parameters."
        )

    if parameters[0].name != "row":
        failed(
            "Production validator first parameter is not 'row'."
        )

    if parameters[1].name != "columns":
        failed(
            "Production validator second parameter is not 'columns'."
        )

    passed(
        "Exact validator signature = "
        "(row, columns)"
    )

    passed(
        "Exact production validate_row() compiled."
    )

    return validator


# ============================================================================
# VALIDATOR RUNTIME
# ============================================================================

def execute_exact_validator(
    validator,
    rows,
    columns,
):
    """
    IMPORTANT:

    This is the first point where the REAL validator is executed.

    We deliberately do NOT calculate eligible/rejected/reason here.

    We only verify:

        validate_row(row, columns)

    and capture its exact return value.
    """

    banner(
        "EXACT PRODUCTION validate_row(row, columns) RUNTIME"
    )

    results = []
    execution_errors = []

    status_counter = Counter()
    score_counter = Counter()
    flag_counter = Counter()

    for index, row in enumerate(
        rows,
        1,
    ):

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

        try:

            result = validator(
                row,
                columns,
            )

            if not isinstance(
                result,
                tuple,
            ):
                raise RuntimeError(
                    "validate_row() did not return tuple."
                )

            if len(result) != 3:
                raise RuntimeError(
                    "validate_row() return tuple "
                    f"length = {len(result)}; expected 3."
                )

            score, status, flags = result

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

            status_counter[
                safe(status)
            ] += 1

            score_counter[
                safe(score)
            ] += 1

            if flags:
                for flag in str(
                    flags
                ).split(","):
                    flag_counter[
                        flag.strip()
                    ] += 1

            # Compact progress only.
            if index == 1:
                print()
                print(
                    "FIRST REAL VALIDATOR OUTPUT:"
                )

                kv(
                    "id",
                    record_id,
                )

                kv(
                    "symbol",
                    symbol,
                )

                kv(
                    "timestamp",
                    timestamp,
                )

                kv(
                    "score",
                    score,
                )

                kv(
                    "status",
                    status,
                )

                kv(
                    "flags",
                    flags,
                )

            if index % 100 == 0:
                print(
                    f"[PASS] validate_row execution "
                    f"{index}/{len(rows)}"
                )

        except Exception as exc:

            execution_errors.append(
                {
                    "id": record_id,
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            print()
            print(
                f"[FAIL] validate_row execution "
                f"at row {index}"
            )

            print(
                f"  id      : {record_id}"
            )

            print(
                f"  symbol  : {symbol}"
            )

            print(
                f"  error   : {type(exc).__name__}: {exc}"
            )

            # Fail immediately.
            # We do NOT continue to interpretation.
            raise RuntimeError(
                "REAL production validate_row() "
                f"execution failed at row {index}."
            ) from exc

    if execution_errors:
        failed(
            "Validator execution completed with errors."
        )

    if len(results) != len(rows):
        failed(
            "Validator result population does not match "
            "runtime acquisition population."
        )

    banner(
        "EXACT VALIDATOR EXECUTION RESULT"
    )

    kv(
        "Rows Sent To validate_row()",
        len(rows),
    )

    kv(
        "Validator Results",
        len(results),
    )

    kv(
        "Execution Errors",
        len(execution_errors),
    )

    passed(
        "ALL REAL CONTRACT ROWS EXECUTED THROUGH "
        "validate_row(row, columns)."
    )

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
    )


# ============================================================================
# FINAL INTEGRITY
# ============================================================================

def verify_integrity_after():
    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER"
    )

    production_after = sha256_file(
        PRODUCTION_FILE
    )

    database_size_after = os.path.getsize(
        DATABASE_FILE
    )

    database_after = sha256_file(
        DATABASE_FILE
    )

    kv(
        "Production SHA256 AFTER",
        production_after,
    )

    kv(
        "Database Size AFTER",
        database_size_after,
    )

    kv(
        "Database SHA256 AFTER",
        database_after,
    )

    return (
        production_after,
        database_size_after,
        database_after,
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT "
        f"PRODUCTION RUNTIME VALIDATION {VERSION}"
    )

    kv(
        "MODE",
        "READ ONLY / RUNTIME VALIDATION",
    )

    kv(
        "Production File",
        PRODUCTION_FILE,
    )

    kv(
        "Database",
        DATABASE_FILE,
    )

    kv(
        "Target Function",
        ACQUIRE_FUNCTION,
    )

    kv(
        "Trace Function",
        TRACE_FUNCTION,
    )

    kv(
        "Validator Symbol",
        VALIDATOR_SYMBOL,
    )

    kv(
        "Contract",
        CONTRACT_TECHNICAL_VERSION,
    )

    kv(
        "Expected Contract Rows",
        EXPECTED_CONTRACT_ROWS,
    )

    kv(
        "Expected Museum Rows",
        EXPECTED_MUSEUM_ROWS,
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
        "Only exact AST-resolved production functions "
        "will be compiled/executed."
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

    # ------------------------------------------------------------------
    # BEFORE INTEGRITY
    # ------------------------------------------------------------------

    banner(
        "PRODUCTION / DATABASE INTEGRITY BEFORE"
    )

    production_before = sha256_file(
        PRODUCTION_FILE
    )

    database_size_before = os.path.getsize(
        DATABASE_FILE
    )

    database_before = sha256_file(
        DATABASE_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        production_before,
    )

    kv(
        "Database Size BEFORE",
        database_size_before,
    )

    kv(
        "Database SHA256 BEFORE",
        database_before,
    )

    # ------------------------------------------------------------------
    # PRODUCTION AST
    # ------------------------------------------------------------------

    production_source = read_source(
        PRODUCTION_FILE
    )

    production_tree = parse_source(
        production_source
    )

    acquire_node = unique_function(
        production_tree,
        ACQUIRE_FUNCTION,
    )

    trace_node = unique_function(
        production_tree,
        TRACE_FUNCTION,
    )

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    kv(
        "acquire_real_rows semantic SHA256",
        semantic_sha256(
            acquire_node
        ),
    )

    kv(
        "trace_real_validation semantic SHA256",
        semantic_sha256(
            trace_node
        ),
    )

    # ------------------------------------------------------------------
    # TRACE CALL
    # ------------------------------------------------------------------

    banner(
        "EXACT PRODUCTION VALIDATION CALL DISCOVERY"
    )

    validator_call = resolve_exact_validator_call(
        trace_node
    )

    kv(
        "Validator Call",
        "validate_row(row, columns)",
    )

    passed(
        "Exact production validation call resolved "
        "from trace_real_validation()."
    )

    # ------------------------------------------------------------------
    # SQL CONTRACT
    # ------------------------------------------------------------------

    verify_sql_contract(
        acquire_node
    )

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------

    conn = None

    try:

        conn = open_read_only_database()

        database_preflight(
            conn
        )

        # ------------------------------------------------------------------
        # COMPILE EXACT ACQUIRE FUNCTION
        # ------------------------------------------------------------------

        banner(
            "EXACT PRODUCTION acquire_real_rows() COMPILATION"
        )

        acquire_function = compile_exact_function(
            acquire_node,
            production_source,
            production_runtime_globals(),
        )

        passed(
            "Exact production acquire_real_rows() compiled."
        )

        # ------------------------------------------------------------------
        # RUNTIME ACQUISITION
        # ------------------------------------------------------------------

        rows, columns = execute_exact_acquisition(
            acquire_function,
            conn,
        )

        verify_acquired_rows(
            rows
        )

        # ------------------------------------------------------------------
        # RESOLVE REAL VALIDATOR SOURCE
        # ------------------------------------------------------------------

        (
            validator_path,
            validator_source,
            validator_tree,
            validator_node,
        ) = resolve_real_validator_source(
            production_tree
        )

        banner(
            "REAL VALIDATOR AST DISCOVERY"
        )

        kv(
            "Validator semantic SHA256",
            semantic_sha256(
                validator_node
            ),
        )

        kv(
            "Validator source",
            validator_path,
        )

        kv(
            "Validator line",
            validator_node.lineno,
        )

        # ------------------------------------------------------------------
        # COMPILE EXACT VALIDATOR
        # ------------------------------------------------------------------

        validator = compile_validator_exact(
            validator_path,
            validator_source,
            validator_tree,
            validator_node,
        )

        # ------------------------------------------------------------------
        # EXECUTE REAL VALIDATOR
        # ------------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
        ) = execute_exact_validator(
            validator,
            rows,
            columns,
        )

        # ------------------------------------------------------------------
        # DO NOT INTERPRET YET
        # ------------------------------------------------------------------

        banner(
            "VALIDATION GATE"
        )

        passed(
            "Runtime acquisition PASS."
        )

        passed(
            "Exact validator resolution PASS."
        )

        passed(
            "Exact validate_row(row, columns) "
            "execution PASS."
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "eligible / rejected / reason analysis "
            "has NOT been performed yet."
        )

        print(
            "The next frontier is now permitted."
        )

        # ------------------------------------------------------------------
        # AFTER INTEGRITY
        # ------------------------------------------------------------------

        (
            production_after,
            database_size_after,
            database_after,
        ) = verify_integrity_after()

        banner(
            "INTEGRITY COMPARISON"
        )

        if production_after != production_before:
            failed(
                "PRODUCTION FILE CHANGED DURING "
                "READ-ONLY VALIDATION."
            )

        passed(
            "Production SHA256 unchanged."
        )

        if database_size_after != database_size_before:
            failed(
                "DATABASE SIZE CHANGED DURING "
                "READ-ONLY VALIDATION."
            )

        passed(
            "Database size unchanged."
        )

        if database_after != database_before:
            failed(
                "DATABASE SHA256 CHANGED DURING "
                "READ-ONLY VALIDATION."
            )

        passed(
            "Database SHA256 unchanged."
        )

        banner(
            "FINAL STATUS : PASS"
        )

        print(
            "Runtime acquisition + exact validator "
            "resolution + exact validate_row(row, columns) "
            "execution completed successfully."
        )

        print()
        print(
            "NEXT AUTHORIZED FRONTIER:"
        )

        print(
            "eligible / rejected / reason forensic analysis "
            "on the REAL validator outputs."
        )

    finally:

        if conn is not None:
            conn.close()


# ============================================================================
# ENTRYPOINT
# ============================================================================

if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        banner(
            "FINAL STATUS : FAIL"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()
        print(
            traceback.format_exc()
        )

        sys.exit(1)