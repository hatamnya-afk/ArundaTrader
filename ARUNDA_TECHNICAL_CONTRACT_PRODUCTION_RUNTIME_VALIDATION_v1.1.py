# -*- coding: utf-8 -*-

"""
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v1.1

PURPOSE
-------
Production Runtime Validation on REAL persisted TECHNICAL_v0.5 rows.

STRICT RULES
------------
1. READ ONLY.
2. SQLite URI mode=ro.
3. PRAGMA query_only = 1.
4. Production module is NEVER imported.
5. Production main() is NEVER executed.
6. Only exact AST-resolved production functions are compiled/executed.
7. acquire_real_rows() is executed exactly as production.
8. trace_real_validation() is used to discover the exact validator call.
9. Exact production call must be:
       validate_row(row, columns)
10. The REAL validator is resolved through the actual production binding
    used by trace_real_validation().
11. No synthetic rows.
12. No database writes.
13. No reconstruction/reset/redesign.
14. This version stops after exact validator execution.
15. eligible/rejected/reason analysis is intentionally NOT performed yet.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import re
import sqlite3
import sys
import traceback
from collections import Counter
from types import SimpleNamespace


# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION = "v1.1"

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

PRODUCTION_FILE = os.path.join(
    BASE_DIR,
    "market_technical_validation_engine_v0.4.1.py",
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "arunda.db",
)

TARGET_FUNCTION = "acquire_real_rows"
TRACE_FUNCTION = "trace_real_validation"
VALIDATOR_SYMBOL = "validate_row"

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

TARGET_TABLE = "market_technical"

TRACE_LIMIT = EXPECTED_CONTRACT_ROWS


# ============================================================================
# OUTPUT
# ============================================================================

WIDTH = 100


def banner(title):
    print()
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def kv(key, value):
    print(f"{key:<58}{value}")


def passed(message):
    print(f"[PASS] {message}")


def failed(message):
    raise RuntimeError(message)


def safe(value):
    try:
        return repr(value)
    except Exception:
        return "<UNPRINTABLE>"


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


def semantic_hash(node):
    """
    Hash AST structure rather than formatting.
    """

    dumped = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        dumped.encode("utf-8")
    ).hexdigest()


# ============================================================================
# SOURCE / AST
# ============================================================================

def read_production_source():
    with open(
        PRODUCTION_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def parse_production_tree(source):
    return ast.parse(
        source,
        filename=PRODUCTION_FILE,
    )


def all_function_defs(tree):
    return [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


def resolve_unique_function(tree, name):
    matches = [
        node
        for node in all_function_defs(tree)
        if node.name == name
    ]

    if not matches:
        failed(
            f"Production function not found: {name}"
        )

    if len(matches) != 1:
        failed(
            f"Expected exactly one production FunctionDef "
            f"for {name}, found {len(matches)}"
        )

    return matches[0]


def function_source_segment(source, node):
    segment = ast.get_source_segment(
        source,
        node,
    )

    if not segment:
        failed(
            f"Could not extract exact source segment "
            f"for {getattr(node, 'name', '<unknown>')}"
        )

    return segment


# ============================================================================
# EXACT FUNCTION COMPILATION
# ============================================================================

def compile_exact_function(
    node,
    source,
    namespace,
):
    """
    Compile ONLY one exact FunctionDef.

    No module import.
    No production main().
    """

    function_code = function_source_segment(
        source,
        node,
    )

    module = ast.parse(
        function_code,
        filename=PRODUCTION_FILE,
    )

    code = compile(
        module,
        filename=PRODUCTION_FILE,
        mode="exec",
    )

    exec(
        code,
        namespace,
        namespace,
    )

    if node.name not in namespace:
        failed(
            f"Compiled production function "
            f"{node.name} was not found in namespace."
        )

    return namespace[node.name]


# ============================================================================
# SAFE CONSTANT / NAME RESOLUTION
# ============================================================================

def build_runtime_namespace():
    """
    Namespace intentionally contains only the symbols required by the
    exact production functions.

    This is NOT a module import.
    """

    return {
        "__name__": "__arunda_ast_runtime__",

        "TRACE_LIMIT": TRACE_LIMIT,

        "TARGET_TABLE": TARGET_TABLE,

        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,

        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,

        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,

        "banner": banner,
        "kv": kv,
        "safe": safe,

        "Counter": Counter,

        "traceback": traceback,
    }


# ============================================================================
# SQL SAFETY
# ============================================================================

def extract_sql_texts(acquire_node):
    literals = []

    dynamic_names = []

    for node in ast.walk(acquire_node):

        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                literals.append(
                    node.value
                )

        elif isinstance(node, ast.Name):
            dynamic_names.append(
                node.id
            )

    return literals, dynamic_names


def reconstruct_sql_from_acquire(
    acquire_node,
):
    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    literals, dynamic_names = extract_sql_texts(
        acquire_node
    )

    sql_candidates = [
        x
        for x in literals
        if "SELECT" in x.upper()
    ]

    if not sql_candidates:
        failed(
            "No production SQL literal found "
            "inside acquire_real_rows()."
        )

    sql = " ".join(
        sql_candidates[0].split()
    )

    print()
    print("AST SQL LITERAL CONTENT:")
    print(sql)

    print()
    print("AST SQL DYNAMIC EXPRESSIONS:")

    if "TARGET_TABLE" in dynamic_names:
        print("  TARGET_TABLE")
    else:
        print("  <none>")

    normalized = sql.lower()

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

    if "target_table" not in dynamic_names:
        failed(
            "TARGET_TABLE expression not preserved "
            "in production acquire_real_rows()."
        )

    passed(
        "TARGET_TABLE expression preserved in AST"
    )

    forbidden = [
        "insert ",
        "update ",
        "delete ",
        "replace ",
        "alter ",
        "create ",
        "drop ",
    ]

    for word in forbidden:

        if word in normalized:
            failed(
                "Forbidden SQL write operation detected: "
                + word
            )

    passed(
        "No SQL write operation detected"
    )

    passed(
        "Production acquisition SQL contract verified"
    )


# ============================================================================
# TRACE VALIDATION CALL DISCOVERY
# ============================================================================

def find_validator_calls(trace_node):
    calls = []

    for node in ast.walk(trace_node):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        func = node.func

        if not isinstance(
            func,
            ast.Name,
        ):
            continue

        if func.id != VALIDATOR_SYMBOL:
            continue

        calls.append(node)

    return calls


def resolve_exact_validator_call(
    trace_node,
):
    calls = find_validator_calls(
        trace_node
    )

    if not calls:
        failed(
            f"No call to {VALIDATOR_SYMBOL} "
            f"found inside {TRACE_FUNCTION}()."
        )

    if len(calls) != 1:
        failed(
            f"Expected exactly one call to "
            f"{VALIDATOR_SYMBOL} inside "
            f"{TRACE_FUNCTION}(), found {len(calls)}"
        )

    call = calls[0]

    if len(call.args) != 2:
        failed(
            f"Production validation call must have "
            f"exactly 2 positional arguments; "
            f"found {len(call.args)}"
        )

    first = call.args[0]
    second = call.args[1]

    if not (
        isinstance(first, ast.Name)
        and first.id == "row"
    ):
        failed(
            "First validator argument is not exact "
            "production symbol 'row'."
        )

    if not (
        isinstance(second, ast.Name)
        and second.id == "columns"
    ):
        failed(
            "Second validator argument is not exact "
            "production symbol 'columns'."
        )

    passed(
        "Exact production validation call resolved "
        f"from {TRACE_FUNCTION}()."
    )

    kv(
        "Validator Call",
        "validate_row(row, columns)",
    )

    return call


# ============================================================================
# REAL VALIDATOR RESOLUTION
# ============================================================================

def collect_import_bindings(tree):
    bindings = []

    for node in tree.body:

        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                bindings.append(
                    {
                        "local": local_name,
                        "module": alias.name,
                        "name": None,
                        "node": node,
                    }
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):
            for alias in node.names:

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name
                )

                bindings.append(
                    {
                        "local": local_name,
                        "module": node.module,
                        "name": alias.name,
                        "node": node,
                    }
                )

    return bindings


def resolve_validator_import_binding(
    production_tree,
):
    """
    Resolve the actual import binding if production source imports
    validate_row.

    This function intentionally does NOT import the module.
    """

    bindings = collect_import_bindings(
        production_tree
    )

    matches = [
        binding
        for binding in bindings
        if binding["local"] == VALIDATOR_SYMBOL
    ]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        failed(
            f"Multiple production import bindings "
            f"found for {VALIDATOR_SYMBOL}."
        )

    return None


# ============================================================================
# IMPORTANT:
# VALIDATOR MAY BE REFERENCED THROUGH AN IMPORTED MODULE ALIAS
# ============================================================================

def resolve_module_alias_validator(
    production_tree,
):
    """
    Detect patterns such as:

        import market_technical_engine as mte

        ...
        mte.validate_row(row, columns)

    This is only discovery. No import occurs.
    """

    aliases = {}

    for node in production_tree.body:

        if isinstance(
            node,
            ast.Import,
        ):
            for alias in node.names:

                local = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                aliases[local] = alias.name

    matches = []

    for node in ast.walk(production_tree):

        if not isinstance(
            node,
            ast.Attribute,
        ):
            continue

        if node.attr != VALIDATOR_SYMBOL:
            continue

        if not isinstance(
            node.value,
            ast.Name,
        ):
            continue

        alias = node.value.id

        if alias in aliases:
            matches.append(
                {
                    "alias": alias,
                    "module": aliases[alias],
                    "node": node,
                }
            )

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        failed(
            f"Multiple module-qualified production "
            f"validator references found for "
            f"{VALIDATOR_SYMBOL}."
        )

    return None


# ============================================================================
# VALIDATOR FUNCTION SOURCE DISCOVERY
# ============================================================================

def find_local_validator_function(
    production_tree,
):
    matches = [
        node
        for node in all_function_defs(
            production_tree
        )
        if node.name == VALIDATOR_SYMBOL
    ]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        failed(
            f"Multiple local FunctionDef objects named "
            f"{VALIDATOR_SYMBOL} found."
        )

    return None


def locate_external_validator_file():
    """
    Production trace explicitly states that validate_row() comes from
    market_technical_engine.py.

    We discover the file only.

    We do NOT import it.
    """

    candidates = [
        os.path.join(
            BASE_DIR,
            "market_technical_engine.py",
        ),
    ]

    existing = [
        path
        for path in candidates
        if os.path.isfile(path)
    ]

    if len(existing) == 1:
        return existing[0]

    if len(existing) > 1:
        failed(
            "Multiple external validator source files "
            "were discovered."
        )

    return None


def resolve_external_validator_node(
    validator_file,
):
    source = read_file(
        validator_file
    )

    tree = ast.parse(
        source,
        filename=validator_file,
    )

    matches = [
        node
        for node in all_function_defs(tree)
        if node.name == VALIDATOR_SYMBOL
    ]

    if len(matches) == 1:
        return (
            validator_file,
            source,
            tree,
            matches[0],
        )

    if len(matches) == 0:
        return None

    failed(
        f"Multiple {VALIDATOR_SYMBOL} FunctionDef "
        f"objects found in {validator_file}."
    )


def read_file(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def resolve_real_validator(
    production_tree,
    trace_node,
    validator_call,
):
    """
    Resolution order:

    1. Local exact FunctionDef.
    2. Direct import binding.
    3. Module-qualified import alias.
    4. Explicit external validator source stated by production trace.

    The key point:
    production trace already tells us:
        validate_row() imported from market_technical_engine.py

    Therefore, if production has no local FunctionDef and no direct
    binding named validate_row, we inspect the explicitly referenced
    production dependency rather than inventing a new validator.
    """

    banner(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    kv(
        "Validator Symbol",
        VALIDATOR_SYMBOL,
    )

    local = find_local_validator_function(
        production_tree
    )

    if local is not None:

        passed(
            "Local production validate_row() "
            "FunctionDef resolved."
        )

        return {
            "file": PRODUCTION_FILE,
            "source": read_production_source(),
            "tree": production_tree,
            "node": local,
            "resolution": "LOCAL_FUNCTIONDEF",
        }

    direct_binding = resolve_validator_import_binding(
        production_tree
    )

    if direct_binding is not None:

        passed(
            "Direct production import binding "
            "for validate_row resolved."
        )

        module = direct_binding["module"]

        if not module:
            failed(
                "Production validate_row binding "
                "has no module."
            )

        external_file = os.path.join(
            BASE_DIR,
            module.replace(".", os.sep)
            + ".py",
        )

        if not os.path.isfile(
            external_file
        ):
            failed(
                "Production validator dependency file "
                f"not found: {external_file}"
            )

        resolved = resolve_external_validator_node(
            external_file
        )

        if resolved is None:
            failed(
                "No exact validate_row() FunctionDef "
                f"found in {external_file}"
            )

        (
            validator_file,
            validator_source,
            validator_tree,
            validator_node,
        ) = resolved

        return {
            "file": validator_file,
            "source": validator_source,
            "tree": validator_tree,
            "node": validator_node,
            "resolution": "DIRECT_IMPORT",
        }

    qualified = resolve_module_alias_validator(
        production_tree
    )

    if qualified is not None:

        passed(
            "Module-qualified production "
            "validate_row() reference resolved."
        )

        module = qualified["module"]

        external_file = os.path.join(
            BASE_DIR,
            module.replace(".", os.sep)
            + ".py",
        )

        if not os.path.isfile(
            external_file
        ):
            failed(
                "Qualified validator dependency file "
                f"not found: {external_file}"
            )

        resolved = resolve_external_validator_node(
            external_file
        )

        if resolved is None:
            failed(
                "No exact validate_row() FunctionDef "
                f"found in {external_file}"
            )

        (
            validator_file,
            validator_source,
            validator_tree,
            validator_node,
        ) = resolved

        return {
            "file": validator_file,
            "source": validator_source,
            "tree": validator_tree,
            "node": validator_node,
            "resolution": "MODULE_QUALIFIED_IMPORT",
        }

    # ----------------------------------------------------------------------
    # FALLBACK IS NOT A GUESS:
    #
    # trace_real_validation() itself explicitly identifies:
    #
    #   validate_row() imported from market_technical_engine.py
    #
    # ----------------------------------------------------------------------

    validator_file = locate_external_validator_file()

    if validator_file is None:

        failed(
            "trace_real_validation() requires the REAL "
            "validate_row() from market_technical_engine.py, "
            "but market_technical_engine.py was not found."
        )

    passed(
        "Explicit production trace dependency "
        "market_technical_engine.py discovered."
    )

    resolved = resolve_external_validator_node(
        validator_file
    )

    if resolved is None:

        failed(
            "Production trace identifies "
            "market_technical_engine.py as the validator "
            "provider, but no exact validate_row() "
            "FunctionDef exists there."
        )

    (
        validator_file,
        validator_source,
        validator_tree,
        validator_node,
    ) = resolved

    passed(
        "Exact external production validate_row() "
        "FunctionDef resolved from "
        "market_technical_engine.py."
    )

    return {
        "file": validator_file,
        "source": validator_source,
        "tree": validator_tree,
        "node": validator_node,
        "resolution": "TRACE_DECLARED_EXTERNAL_DEPENDENCY",
    }


# ============================================================================
# DATABASE
# ============================================================================

def open_read_only_database():
    """
    Open SQLite in URI mode=ro.

    Then activate query_only explicitly on this connection.

    NOTE:
    SQLite query_only is connection-local.
    Therefore we set it AFTER opening the actual validation connection.
    """

    uri = (
        "file:"
        + DATABASE_FILE.replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    conn.row_factory = None

    conn.execute(
        "PRAGMA query_only = 1"
    )

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if query_only != 1:
        conn.close()

        failed(
            "SQLite PRAGMA query_only is not 1."
        )

    return conn


# ============================================================================
# DATABASE PREFLIGHT
# ============================================================================

def database_preflight(
    conn,
):
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
            "SQLite query_only is not 1."
        )

    total = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        """
    ).fetchone()[0]

    contract = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        ),
    ).fetchone()[0]

    museum = total - contract

    min_id = conn.execute(
        f"""
        SELECT MIN(id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        ),
    ).fetchone()[0]

    max_id = conn.execute(
        f"""
        SELECT MAX(id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        ),
    ).fetchone()[0]

    distinct_ids = conn.execute(
        f"""
        SELECT COUNT(DISTINCT id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        ),
    ).fetchone()[0]

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

    if total != EXPECTED_CONTRACT_ROWS + EXPECTED_MUSEUM_ROWS:
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
            "CONTRACT DISTINCT IDS mismatch"
        )

    passed(
        f"CONTRACT DISTINCT IDS = {distinct_ids}"
    )

    if min_id != 5923:
        failed(
            f"Unexpected contract MIN ID: {min_id}"
        )

    if max_id != 6909:
        failed(
            f"Unexpected contract MAX ID: {max_id}"
        )

    passed(
        "CONTRACT ID RANGE = 5923..6909"
    )


# ============================================================================
# ACQUISITION RUNTIME
# ============================================================================

def execute_acquisition(
    acquire_function,
    conn,
):
    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    # The production function signature is:
    #
    # acquire_real_rows(
    #     conn,
    #     columns,
    #     limit=TRACE_LIMIT
    # )
    #
    # We must supply the REAL production columns.
    #
    # Since production does SELECT *, obtain exact SQLite column order.

    columns = [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{TARGET_TABLE}")'
        ).fetchall()
    ]

    if not columns:
        failed(
            "Could not resolve production "
            "market_technical columns."
        )

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
            "Runtime acquisition row count mismatch: "
            f"{len(rows)}"
        )

    passed(
        f"Runtime acquisition = "
        f"{EXPECTED_CONTRACT_ROWS} rows"
    )

    return rows, columns


# ============================================================================
# IMPORTANT FIX:
# ROWS ARE TUPLES
# ============================================================================

def row_as_mapping(
    row,
    columns,
):
    """
    Wrapper-only row mapping.

    NEVER changes the object passed to validate_row().

    Production receives:
        validate_row(row, columns)

    exactly.

    This mapping exists ONLY for audit/preflight access by column name.
    """

    if len(row) != len(columns):
        failed(
            "Runtime row length does not match "
            "production column count."
        )

    return dict(
        zip(
            columns,
            row,
        )
    )


def verify_acquisition_contract(
    rows,
    columns,
):
    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime row count mismatch."
        )

    passed(
        f"Runtime row count = {len(rows)}"
    )

    first_mapping = row_as_mapping(
        rows[0],
        columns,
    )

    last_mapping = row_as_mapping(
        rows[-1],
        columns,
    )

    # ----------------------------------------------------------------------
    # These checks are performed against wrapper mappings.
    # The production validator still receives the original tuple.
    # ----------------------------------------------------------------------

    for field, expected in [
        (
            "technical_version",
            CONTRACT_TECHNICAL_VERSION,
        ),
        (
            "engine_version",
            CONTRACT_ENGINE_VERSION,
        ),
        (
            "source",
            CONTRACT_SOURCE,
        ),
    ]:

        if field not in first_mapping:
            failed(
                f"Required production column missing: "
                f"{field}"
            )

        values = {
            row_as_mapping(
                row,
                columns,
            ).get(field)
            for row in rows
        }

        if values != {expected}:
            failed(
                f"Runtime {field} mismatch: "
                f"{values}"
            )

        passed(
            f"Runtime {field} = {expected}"
        )

    ids = [
        row_as_mapping(
            row,
            columns,
        )["id"]
        for row in rows
    ]

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime distinct IDs mismatch."
        )

    passed(
        f"Runtime distinct IDs = "
        f"{len(set(ids))}"
    )

    if min(ids) != 5923:
        failed(
            f"Runtime MIN ID mismatch: {min(ids)}"
        )

    passed(
        f"Runtime MIN ID = {min(ids)}"
    )

    if max(ids) != 6909:
        failed(
            f"Runtime MAX ID mismatch: {max(ids)}"
        )

    passed(
        f"Runtime MAX ID = {max(ids)}"
    )

    # Production query is ORDER BY id DESC.
    if ids != sorted(
        ids,
        reverse=True,
    ):
        failed(
            "Runtime ordering is not id DESC."
        )

    passed(
        "Runtime ordering = id DESC"
    )

    # Validate tuple shape only.
    for index, row in enumerate(
        rows,
        1,
    ):
        if not isinstance(
            row,
            tuple,
        ):
            failed(
                f"Production acquisition row {index} "
                f"is not tuple: {type(row).__name__}"
            )

        if len(row) != len(columns):
            failed(
                f"Production acquisition row {index} "
                f"column length mismatch."
            )

    passed(
        "Runtime row representation = tuple "
        "(preserved exactly)"
    )

    # Keep these variables intentionally referenced so that accidental
    # optimization/refactoring does not obscure that first/last mappings
    # were materialized from exact tuples.
    _ = first_mapping
    _ = last_mapping


# ============================================================================
# EXACT VALIDATOR EXECUTION
# ============================================================================

def execute_exact_validator(
    validator_function,
    rows,
    columns,
):
    """
    CRITICAL:

    The exact production call is:

        validate_row(row, columns)

    No dict row.
    No reconstructed row.
    No synthetic row.
    No transformation.
    """

    banner(
        "EXACT REAL validate_row(row, columns) EXECUTION"
    )

    kv(
        "Rows",
        len(rows),
    )

    kv(
        "Call",
        "validate_row(row, columns)",
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

        mapping = row_as_mapping(
            row,
            columns,
        )

        record_id = mapping.get(
            "id"
        )

        symbol = mapping.get(
            "symbol"
        )

        timestamp = mapping.get(
            "timestamp"
        )

        try:

            # ==============================================================
            # THIS IS THE ONLY REAL VALIDATOR CALL
            # ==============================================================

            result = validator_function(
                row,
                columns,
            )

            # ==============================================================
            # CONTRACT OF RETURN
            # ==============================================================

            if not isinstance(
                result,
                tuple,
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
                    "row_index": index,
                    "id": record_id,
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "error": repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )

            # Fail-fast.
            #
            # We do NOT continue to manufacture a partial PASS.
            failed(
                "REAL validate_row() execution failed "
                f"at row {index}: "
                f"{type(exc).__name__}: {exc}"
            )

    if len(results) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Validator execution result count mismatch: "
            f"{len(results)}"
        )

    passed(
        f"REAL validate_row() executed successfully "
        f"for all {len(results)} rows."
    )

    kv(
        "Execution Errors",
        len(execution_errors),
    )

    if execution_errors:
        failed(
            "Validator execution errors detected."
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

def verify_database_unchanged(
    before_size,
    before_sha256,
):
    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER"
    )

    after_size = os.path.getsize(
        DATABASE_FILE
    )

    after_sha256 = sha256_file(
        DATABASE_FILE
    )

    kv(
        "Database Size AFTER",
        after_size,
    )

    kv(
        "Database SHA256 AFTER",
        after_sha256,
    )

    if after_size != before_size:
        failed(
            "DATABASE SIZE CHANGED."
        )

    passed(
        "Database size unchanged"
    )

    if after_sha256 != before_sha256:
        failed(
            "DATABASE SHA256 CHANGED."
        )

    passed(
        "Database SHA256 unchanged"
    )


def verify_production_unchanged(
    before_sha256,
):
    after_sha256 = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 AFTER",
        after_sha256,
    )

    if after_sha256 != before_sha256:
        failed(
            "PRODUCTION FILE SHA256 CHANGED."
        )

    passed(
        "Production SHA256 unchanged"
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    banner(
        f"ARUNDA TECHNICAL CONTRACT "
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
        TARGET_FUNCTION,
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

    # ----------------------------------------------------------------------
    # INTEGRITY BEFORE
    # ----------------------------------------------------------------------

    banner(
        "PRODUCTION / DATABASE INTEGRITY BEFORE"
    )

    production_before = sha256_file(
        PRODUCTION_FILE
    )

    database_before_size = os.path.getsize(
        DATABASE_FILE
    )

    database_before_sha256 = sha256_file(
        DATABASE_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        production_before,
    )

    kv(
        "Database Size BEFORE",
        database_before_size,
    )

    kv(
        "Database SHA256 BEFORE",
        database_before_sha256,
    )

    # ----------------------------------------------------------------------
    # PRODUCTION AST
    # ----------------------------------------------------------------------

    source = read_production_source()

    production_tree = parse_production_tree(
        source
    )

    acquire_node = resolve_unique_function(
        production_tree,
        TARGET_FUNCTION,
    )

    trace_node = resolve_unique_function(
        production_tree,
        TRACE_FUNCTION,
    )

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    kv(
        "acquire_real_rows semantic SHA256",
        semantic_hash(acquire_node),
    )

    kv(
        "trace_real_validation semantic SHA256",
        semantic_hash(trace_node),
    )

    # ----------------------------------------------------------------------
    # EXACT VALIDATION CALL
    # ----------------------------------------------------------------------

    banner(
        "EXACT PRODUCTION VALIDATION CALL DISCOVERY"
    )

    validator_call = resolve_exact_validator_call(
        trace_node
    )

    # ----------------------------------------------------------------------
    # SQL
    # ----------------------------------------------------------------------

    reconstruct_sql_from_acquire(
        acquire_node
    )

    # ----------------------------------------------------------------------
    # DATABASE
    # ----------------------------------------------------------------------

    conn = open_read_only_database()

    try:

        database_preflight(
            conn
        )

        # ------------------------------------------------------------------
        # EXACT ACQUISITION
        # ------------------------------------------------------------------

        runtime_namespace = build_runtime_namespace()

        acquire_function = compile_exact_function(
            acquire_node,
            source,
            runtime_namespace,
        )

        rows, columns = execute_acquisition(
            acquire_function,
            conn,
        )

        verify_acquisition_contract(
            rows,
            columns,
        )

        # ------------------------------------------------------------------
        # REAL VALIDATOR RESOLUTION
        # ------------------------------------------------------------------

        validator_info = resolve_real_validator(
            production_tree,
            trace_node,
            validator_call,
        )

        validator_file = validator_info[
            "file"
        ]

        validator_source = validator_info[
            "source"
        ]

        validator_node = validator_info[
            "node"
        ]

        banner(
            "EXACT PRODUCTION VALIDATOR"
        )

        kv(
            "Validator File",
            validator_file,
        )

        kv(
            "Resolution",
            validator_info[
                "resolution"
            ],
        )

        kv(
            "Validator semantic SHA256",
            semantic_hash(
                validator_node
            ),
        )

        validator_namespace = {
            "__name__":
                "__arunda_validator_ast_runtime__",

            "Counter": Counter,

            "traceback": traceback,

            "safe": safe,

            "banner": banner,

            "kv": kv,
        }

        validator_function = compile_exact_function(
            validator_node,
            validator_source,
            validator_namespace,
        )

        # ------------------------------------------------------------------
        # EXACT REAL EXECUTION
        # ------------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
        ) = execute_exact_validator(
            validator_function,
            rows,
            columns,
        )

        # ------------------------------------------------------------------
        # NO ELIGIBILITY ANALYSIS YET
        # ------------------------------------------------------------------

        banner(
            "RUNTIME VALIDATOR EXECUTION CONTRACT"
        )

        passed(
            "REAL validate_row(row, columns) "
            "execution completed."
        )

        passed(
            f"Validated rows = {len(results)}"
        )

        passed(
            "No synthetic rows were introduced."
        )

        passed(
            "No row transformation was passed "
            "into validate_row()."
        )

        passed(
            "eligible/rejected/reason analysis "
            "NOT performed in this version."
        )

        # ------------------------------------------------------------------
        # COUNTERS — OBSERVATION ONLY
        # ------------------------------------------------------------------

        banner(
            "REAL VALIDATOR OUTPUT OBSERVATION"
        )

        kv(
            "Distinct status values",
            len(status_counter),
        )

        kv(
            "Distinct score values",
            len(score_counter),
        )

        kv(
            "Distinct flag values",
            len(flag_counter),
        )

        # ------------------------------------------------------------------
        # FINAL INTEGRITY
        # ------------------------------------------------------------------

        verify_database_unchanged(
            database_before_size,
            database_before_sha256,
        )

        verify_production_unchanged(
            production_before
        )

        banner(
            "FINAL STATUS"
        )

        print(
            "PASS"
        )

        print()
        print(
            "NEXT FRONTIER:"
        )

        print(
            "REAL validator outputs are now available "
            "for the next isolated eligible/rejected/reason "
            "analysis stage."
        )

    finally:
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

        traceback.print_exc()

        sys.exit(1)