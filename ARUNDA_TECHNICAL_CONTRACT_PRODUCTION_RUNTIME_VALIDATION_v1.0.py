from __future__ import annotations

import ast
import hashlib
import inspect
import os
import sqlite3
import sys
import traceback
from collections import Counter
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

PRODUCTION_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

TARGET_TABLE = "market_technical"

TRACE_FUNCTION = "trace_real_validation"
ACQUIRE_FUNCTION = "acquire_real_rows"
VALIDATOR_SYMBOL = "validate_row"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

TRACE_LIMIT = EXPECTED_CONTRACT_ROWS


# ============================================================================
# OUTPUT
# ============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<58} {value}")


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
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def semantic_hash(node):
    text = ast.unparse(node)

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================================
# AST
# ============================================================================

def read_source(path):
    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


def parse_source(path):
    source = read_source(path)

    return source, ast.parse(
        source,
        filename=str(path)
    )


def find_unique_function(tree, name):
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]

    if not matches:
        failed(
            f"Production FunctionDef not found: {name}"
        )

    if len(matches) != 1:
        failed(
            f"Expected exactly one FunctionDef for {name}; "
            f"found {len(matches)}"
        )

    return matches[0]


# ============================================================================
# EXACT VALIDATION CALL DISCOVERY
# ============================================================================

def discover_validation_call(trace_node):
    calls = []

    for node in ast.walk(trace_node):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Name):
            continue

        if node.func.id != VALIDATOR_SYMBOL:
            continue

        if len(node.args) != 2:
            continue

        if not all(
            isinstance(arg, ast.Name)
            for arg in node.args
        ):
            continue

        if (
            node.args[0].id == "row"
            and node.args[1].id == "columns"
        ):
            calls.append(node)

    if len(calls) != 1:
        failed(
            "Could not resolve exactly one production call "
            "validate_row(row, columns). "
            f"Found {len(calls)} matching calls."
        )

    return calls[0]


# ============================================================================
# IMPORT BINDING RESOLUTION
# ============================================================================

def resolve_import_binding(tree, symbol):
    """
    Resolve:

        from X import validate_row
        from X import validate_row as something

    and:

        import X
        X.validate_row(...)

    The trace currently proves the first form must ultimately provide
    the callable used as validate_row().
    """

    candidates = []

    for node in tree.body:

        # ------------------------------------------------------------
        # from module import validate_row
        # ------------------------------------------------------------

        if isinstance(node, ast.ImportFrom):

            for alias in node.names:

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name
                )

                if local_name == symbol:

                    candidates.append(
                        {
                            "kind": "from",
                            "module": node.module,
                            "level": node.level,
                            "name": alias.name,
                            "local": local_name,
                        }
                    )

        # ------------------------------------------------------------
        # import module as alias
        # ------------------------------------------------------------

        if isinstance(node, ast.Import):

            for alias in node.names:

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                if local_name == symbol:

                    candidates.append(
                        {
                            "kind": "module",
                            "module": alias.name,
                            "level": 0,
                            "name": symbol,
                            "local": local_name,
                        }
                    )

    if not candidates:
        return None

    if len(candidates) != 1:
        failed(
            f"Ambiguous AST import binding for "
            f"{symbol}: {candidates}"
        )

    return candidates[0]


# ============================================================================
# MODULE PATH RESOLUTION
# ============================================================================

def module_candidates(module_name, production_file):
    candidates = []

    base_dir = production_file.parent

    module_path = module_name.replace(".", os.sep)

    candidates.append(
        base_dir / f"{module_path}.py"
    )

    candidates.append(
        base_dir / module_path / "__init__.py"
    )

    # Current working directory fallback.
    cwd = Path.cwd()

    candidates.append(
        cwd / f"{module_path}.py"
    )

    candidates.append(
        cwd / module_path / "__init__.py"
    )

    # Project root fallback.
    candidates.append(
        production_file.parent / f"{module_name}.py"
    )

    # De-duplicate.
    unique = []

    for path in candidates:

        path = path.resolve()

        if path not in unique:
            unique.append(path)

    return unique


def resolve_module_source(
    module_name,
    production_file
):
    candidates = module_candidates(
        module_name,
        production_file
    )

    existing = [
        path
        for path in candidates
        if path.exists()
        and path.is_file()
    ]

    if len(existing) == 0:
        failed(
            f"Could not resolve source file for "
            f"production module '{module_name}'.\n"
            f"Searched:\n"
            + "\n".join(
                f"  {p}"
                for p in candidates
            )
        )

    if len(existing) > 1:
        # Prefer exact project-local source.
        exact = [
            p
            for p in existing
            if p.parent == production_file.parent
            and p.name == f"{module_name}.py"
        ]

        if len(exact) == 1:
            return exact[0]

        failed(
            f"Ambiguous source resolution for "
            f"'{module_name}':\n"
            + "\n".join(
                f"  {p}"
                for p in existing
            )
        )

    return existing[0]


# ============================================================================
# EXACT VALIDATOR SOURCE RESOLUTION
# ============================================================================

def resolve_validator_source(
    production_tree,
    production_file,
    symbol
):
    binding = resolve_import_binding(
        production_tree,
        symbol
    )

    if binding is None:
        failed(
            f"No AST import binding found for "
            f"production validator '{symbol}'."
        )

    print()
    kv(
        "Import Binding Kind",
        binding["kind"]
    )

    kv(
        "Import Module",
        binding["module"]
    )

    kv(
        "Imported Symbol",
        binding["name"]
    )

    if binding["kind"] == "from":

        if binding["name"] != symbol:
            failed(
                f"Import binding mismatch: "
                f"expected {symbol}, got {binding['name']}"
            )

        module_path = resolve_module_source(
            binding["module"],
            production_file
        )

        return module_path

    failed(
        "Production validator is not a direct "
        "'from module import validate_row' binding. "
        "The observed trace requires an explicit callable "
        "binding and this version refuses to guess."
    )


# ============================================================================
# VALIDATOR FUNCTION
# ============================================================================

def resolve_validator_function(module_path):
    source, tree = parse_source(module_path)

    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and node.name == VALIDATOR_SYMBOL
    ]

    if not matches:
        failed(
            f"Validator module '{module_path}' contains "
            f"no FunctionDef named '{VALIDATOR_SYMBOL}'."
        )

    if len(matches) != 1:
        failed(
            f"Validator module '{module_path}' contains "
            f"{len(matches)} definitions named "
            f"'{VALIDATOR_SYMBOL}'."
        )

    node = matches[0]

    return source, tree, node


# ============================================================================
# STATIC GLOBAL EXTRACTION
# ============================================================================

SAFE_BUILTINS = {
    name: getattr(__builtins__, name)
    for name in [
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "isinstance",
        "len",
        "list",
        "max",
        "min",
        "round",
        "set",
        "str",
        "sum",
        "tuple",
        "zip",
        "sorted",
        "range",
        "print",
        "Exception",
        "RuntimeError",
        "ValueError",
        "TypeError",
    ]
    if hasattr(__builtins__, name)
}


def collect_name_loads(function_node):
    names = set()

    for node in ast.walk(function_node):

        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                names.add(node.id)

    return names


def top_level_function_map(tree):
    result = {}

    for node in tree.body:

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            result[node.name] = node

    return result


def top_level_assignments(tree):
    result = {}

    for node in tree.body:

        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign)
        ):
            targets = []

            if isinstance(node, ast.Assign):

                for target in node.targets:
                    if isinstance(target, ast.Name):
                        targets.append(target.id)

            else:

                if isinstance(node.target, ast.Name):
                    targets.append(node.target.id)

            for target in targets:
                result[target] = node

    return result


# ============================================================================
# COMPILE EXACT VALIDATOR CLOSURE
# ============================================================================

def build_validator_namespace(
    tree,
    validator_node
):
    """
    Build a controlled namespace without importing the production module.

    Only:
      - exact validator
      - locally defined helper functions required by validator
      - statically evaluable constants
      - safe builtins

    are admitted.

    Import statements are deliberately NOT executed.
    """

    namespace = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__arunda_exact_validator__",
    }

    functions = top_level_function_map(tree)
    assignments = top_level_assignments(tree)

    required = collect_name_loads(
        validator_node
    )

    resolved_functions = set()

    # ------------------------------------------------------------
    # Resolve local helper closure.
    # ------------------------------------------------------------

    changed = True

    while changed:

        changed = False

        for name in list(required):

            if name in resolved_functions:
                continue

            if name not in functions:
                continue

            if name == VALIDATOR_SYMBOL:
                resolved_functions.add(name)
                continue

            helper = functions[name]

            required.update(
                collect_name_loads(helper)
            )

            resolved_functions.add(name)
            changed = True

    # ------------------------------------------------------------
    # Compile helper functions first.
    # ------------------------------------------------------------

    helper_names = [
        name
        for name in resolved_functions
        if name != VALIDATOR_SYMBOL
    ]

    for name in helper_names:

        node = functions[name]

        code = compile(
            ast.Module(
                body=[node],
                type_ignores=[]
            ),
            filename="<exact-validator-helper>",
            mode="exec",
        )

        exec(
            code,
            namespace,
            namespace
        )

    # ------------------------------------------------------------
    # Static constants.
    # ------------------------------------------------------------

    unresolved = set()

    for name in required:

        if name in namespace:
            continue

        if name not in assignments:
            unresolved.add(name)
            continue

        node = assignments[name]

        # Only allow assignments that can be safely evaluated.
        try:

            if isinstance(node, ast.Assign):
                value_node = node.value

            else:
                value_node = node.value

            value = ast.literal_eval(
                value_node
            )

            namespace[name] = value

        except Exception:
            unresolved.add(name)

    # ------------------------------------------------------------
    # Safe stdlib names frequently used by validators.
    # ------------------------------------------------------------

    try:
        import math
        namespace["math"] = math
    except Exception:
        pass

    try:
        import statistics
        namespace["statistics"] = statistics
    except Exception:
        pass

    # ------------------------------------------------------------
    # Exact validator.
    # ------------------------------------------------------------

    validator_code = compile(
        ast.Module(
            body=[validator_node],
            type_ignores=[]
        ),
        filename="<exact-production-validate-row>",
        mode="exec",
    )

    exec(
        validator_code,
        namespace,
        namespace
    )

    # ------------------------------------------------------------
    # Hard safety check.
    # ------------------------------------------------------------

    if VALIDATOR_SYMBOL not in namespace:
        failed(
            "Exact validator compilation completed but "
            f"'{VALIDATOR_SYMBOL}' is absent from namespace."
        )

    if unresolved:

        # Ignore names that are merely annotations.
        ignored = {
            "True",
            "False",
            "None",
        }

        unresolved -= ignored

        if unresolved:

            failed(
                "Exact validator requires unresolved "
                "production globals/imports:\n"
                + "\n".join(
                    f"  {name}"
                    for name in sorted(unresolved)
                )
                + "\n\n"
                "No guessed replacement is permitted."
            )

    return namespace


# ============================================================================
# READ ONLY SQLITE
# ============================================================================

def open_read_only_database():
    """
    SQLite URI mode=ro prevents writes at connection level.

    PRAGMA query_only is then explicitly enabled on THIS connection.
    """

    uri = (
        "file:"
        + str(DATABASE_FILE.resolve()).replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False
    )

    # Explicitly activate query_only.
    conn.execute(
        "PRAGMA query_only = 1"
    )

    conn.commit()

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if value != 1:
        conn.close()

        failed(
            "SQLite PRAGMA query_only could not be activated."
        )

    return conn


# ============================================================================
# DATABASE PREFLIGHT
# ============================================================================

def database_preflight(conn):
    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    kv(
        "SQLite query_only",
        query_only
    )

    if query_only != 1:
        failed(
            "SQLite query_only != 1"
        )

    total = conn.execute(
        f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
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
        )
    ).fetchone()[0]

    museum = total - contract

    min_id, max_id, distinct_ids = conn.execute(
        f"""
        SELECT
            MIN(id),
            MAX(id),
            COUNT(DISTINCT id)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchone()

    kv("Database Total", total)
    kv("Contract Population", contract)
    kv("Museum Population", museum)
    kv("Contract MIN ID", min_id)
    kv("Contract MAX ID", max_id)
    kv("Contract DISTINCT IDs", distinct_ids)

    if total != EXPECTED_CONTRACT_ROWS + EXPECTED_MUSEUM_ROWS:
        failed(
            f"Unexpected database total: {total}"
        )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Unexpected contract population: {contract}"
        )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            f"Unexpected museum population: {museum}"
        )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            "Contract IDs are not distinct."
        )

    passed(
        f"DATABASE TOTAL = {total}"
    )

    passed(
        f"CONTRACT = {contract}"
    )

    passed(
        f"MUSEUM = {museum}"
    )

    passed(
        f"CONTRACT DISTINCT IDS = {distinct_ids}"
    )


# ============================================================================
# ACQUIRE EXACT PRODUCTION FUNCTION
# ============================================================================

def compile_acquire_function(
    acquire_node,
    production_source
):
    """
    Compile only acquire_real_rows().

    Production main() is never executed.
    """

    namespace = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__arunda_acquire__",

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
    }

    code = compile(
        ast.Module(
            body=[acquire_node],
            type_ignores=[]
        ),
        filename=str(PRODUCTION_FILE),
        mode="exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    return namespace[ACQUIRE_FUNCTION]


# ============================================================================
# RUNTIME ACQUISITION
# ============================================================================

def runtime_acquisition(
    acquire_function,
    conn
):
    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    columns = [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{TARGET_TABLE}")'
        ).fetchall()
    ]

    rows = acquire_function(
        conn,
        columns,
        EXPECTED_CONTRACT_ROWS
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Runtime acquisition returned "
            f"{len(rows)} rows; expected "
            f"{EXPECTED_CONTRACT_ROWS}"
        )

    passed(
        f"Runtime acquisition = {len(rows)} rows"
    )

    return rows, columns


# ============================================================================
# ACQUISITION CONTRACT
# ============================================================================

def verify_acquisition_contract(rows):
    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    ids = [
        row["id"]
        for row in rows
    ]

    if len(ids) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime row count mismatch."
        )

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime IDs are not distinct."
        )

    if min(ids) != 5923:
        failed(
            f"Unexpected runtime MIN ID: {min(ids)}"
        )

    if max(ids) != 6909:
        failed(
            f"Unexpected runtime MAX ID: {max(ids)}"
        )

    technical_versions = {
        row["technical_version"]
        for row in rows
    }

    engine_versions = {
        row["engine_version"]
        for row in rows
    }

    sources = {
        row["source"]
        for row in rows
    }

    if technical_versions != {
        CONTRACT_TECHNICAL_VERSION
    }:
        failed(
            f"Runtime technical_version mismatch: "
            f"{technical_versions}"
        )

    if engine_versions != {
        CONTRACT_ENGINE_VERSION
    }:
        failed(
            f"Runtime engine_version mismatch: "
            f"{engine_versions}"
        )

    if sources != {
        CONTRACT_SOURCE
    }:
        failed(
            f"Runtime source mismatch: "
            f"{sources}"
        )

    for earlier, later in zip(ids, ids[1:]):

        if earlier <= later:
            failed(
                "Runtime acquisition ordering is not "
                "strictly id DESC."
            )

    passed(
        "Runtime row count = 987"
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

    passed(
        "Runtime distinct IDs = 987"
    )

    passed(
        "Runtime MIN ID = 5923"
    )

    passed(
        "Runtime MAX ID = 6909"
    )

    passed(
        "Runtime ordering = id DESC"
    )


# ============================================================================
# RUNTIME VALIDATOR EXECUTION
# ============================================================================

def execute_validator(
    validator,
    rows,
    columns
):
    banner(
        "EXACT PRODUCTION validate_row(row, columns) RUNTIME"
    )

    results = []
    errors = []

    status_counter = Counter()

    print(
        "IMPORTANT: Executing the exact resolved production "
        "validate_row() only."
    )

    print(
        "No production main() is executed."
    )

    print(
        "No production module is imported."
    )

    print(
        "No database write is permitted."
    )

    for index, row in enumerate(rows, 1):

        record_id = (
            row["id"]
            if "id" in row.keys()
            else None
        )

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
                columns
            )

            if not isinstance(
                result,
                tuple
            ):
                raise RuntimeError(
                    "validate_row() did not return tuple."
                )

            if len(result) != 3:
                raise RuntimeError(
                    "validate_row() returned tuple length "
                    f"{len(result)}; expected 3."
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

        except Exception as exc:

            errors.append(
                {
                    "row_index": index,
                    "id": record_id,
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "exception": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            # Fail fast.
            raise RuntimeError(
                "EXACT validate_row(row, columns) "
                f"FAILED at row {index}, "
                f"id={record_id}, "
                f"symbol={symbol}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    return results, errors, status_counter


# ============================================================================
# RUNTIME RESULT VALIDATION
# ============================================================================

def verify_validator_execution(
    results,
    errors
):
    banner(
        "VALIDATOR RUNTIME EXECUTION RESULT"
    )

    if errors:
        failed(
            f"Validator execution produced "
            f"{len(errors)} execution errors."
        )

    if len(results) != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Validator produced {len(results)} results; "
            f"expected {EXPECTED_CONTRACT_ROWS}."
        )

    ids = [
        item["id"]
        for item in results
    ]

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Validator result IDs are not distinct."
        )

    passed(
        "Exact validate_row(row, columns) executed = 987 rows"
    )

    passed(
        "Validator execution errors = 0"
    )

    passed(
        "Every validator result contains "
        "(score, status, flags)"
    )


# ============================================================================
# INTEGRITY AFTER
# ============================================================================

def verify_integrity_after(
    production_hash_before,
    database_size_before,
    database_hash_before
):
    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER"
    )

    production_hash_after = sha256_file(
        PRODUCTION_FILE
    )

    database_size_after = DATABASE_FILE.stat().st_size

    database_hash_after = sha256_file(
        DATABASE_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        production_hash_before
    )

    kv(
        "Production SHA256 AFTER",
        production_hash_after
    )

    kv(
        "Database Size BEFORE",
        database_size_before
    )

    kv(
        "Database Size AFTER",
        database_size_after
    )

    kv(
        "Database SHA256 BEFORE",
        database_hash_before
    )

    kv(
        "Database SHA256 AFTER",
        database_hash_after
    )

    if production_hash_before != production_hash_after:
        failed(
            "Production source changed."
        )

    if database_size_before != database_size_after:
        failed(
            "Database size changed."
        )

    if database_hash_before != database_hash_after:
        failed(
            "Database SHA256 changed."
        )

    passed(
        "Production source unchanged"
    )

    passed(
        "Database size unchanged"
    )

    passed(
        "Database SHA256 unchanged"
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VALIDATION v1.0"
    )

    kv(
        "MODE",
        "READ ONLY / RUNTIME VALIDATION"
    )

    kv(
        "Production File",
        PRODUCTION_FILE
    )

    kv(
        "Database",
        DATABASE_FILE
    )

    kv(
        "Target Function",
        ACQUIRE_FUNCTION
    )

    kv(
        "Trace Function",
        TRACE_FUNCTION
    )

    kv(
        "Validator Symbol",
        VALIDATOR_SYMBOL
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
        "Production modules will NOT be imported."
    )
    print(
        "Only exact AST-resolved production functions "
        "will be compiled/executed."
    )
    print(
        "Database = SQLite mode=ro."
    )
    print(
        "PRAGMA query_only = 1 is explicitly activated."
    )
    print(
        "No database write is permitted."
    )

    # ------------------------------------------------------------
    # PRE-INTEGRITY
    # ------------------------------------------------------------

    production_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    database_size_before = DATABASE_FILE.stat().st_size

    database_hash_before = sha256_file(
        DATABASE_FILE
    )

    banner(
        "PRODUCTION / DATABASE INTEGRITY BEFORE"
    )

    kv(
        "Production SHA256 BEFORE",
        production_hash_before
    )

    kv(
        "Database Size BEFORE",
        database_size_before
    )

    kv(
        "Database SHA256 BEFORE",
        database_hash_before
    )

    # ------------------------------------------------------------
    # PRODUCTION AST
    # ------------------------------------------------------------

    source, production_tree = parse_source(
        PRODUCTION_FILE
    )

    acquire_node = find_unique_function(
        production_tree,
        ACQUIRE_FUNCTION
    )

    trace_node = find_unique_function(
        production_tree,
        TRACE_FUNCTION
    )

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    kv(
        "acquire_real_rows semantic SHA256",
        semantic_hash(acquire_node)
    )

    kv(
        "trace_real_validation semantic SHA256",
        semantic_hash(trace_node)
    )

    # ------------------------------------------------------------
    # EXACT VALIDATION CALL
    # ------------------------------------------------------------

    banner(
        "EXACT PRODUCTION VALIDATION CALL DISCOVERY"
    )

    validation_call = discover_validation_call(
        trace_node
    )

    call_text = ast.unparse(
        validation_call
    )

    kv(
        "Validator Call",
        call_text
    )

    if call_text != "validate_row(row, columns)":
        failed(
            "Unexpected validator call."
        )

    passed(
        "Exact production validation call "
        "resolved from trace_real_validation()."
    )

    # ------------------------------------------------------------
    # DB
    # ------------------------------------------------------------

    conn = None

    try:

        conn = open_read_only_database()

        database_preflight(
            conn
        )

        # --------------------------------------------------------
        # ACQUIRE
        # --------------------------------------------------------

        acquire_function = compile_acquire_function(
            acquire_node,
            source
        )

        rows, columns = runtime_acquisition(
            acquire_function,
            conn
        )

        verify_acquisition_contract(
            rows
        )

        # --------------------------------------------------------
        # VALIDATOR RESOLUTION
        # --------------------------------------------------------

        banner(
            "REAL PRODUCTION VALIDATOR RESOLUTION"
        )

        validator_module = resolve_validator_source(
            production_tree,
            PRODUCTION_FILE,
            VALIDATOR_SYMBOL
        )

        kv(
            "Resolved Validator Module",
            validator_module
        )

        if validator_module.resolve() == PRODUCTION_FILE.resolve():
            failed(
                "Validator source resolves to validation "
                "engine itself; expected the actual imported "
                "validator source module."
            )

        passed(
            "Validator source module resolved from "
            "production AST import binding."
        )

        validator_source, validator_tree, validator_node = (
            resolve_validator_function(
                validator_module
            )
        )

        kv(
            "Validator Function",
            VALIDATOR_SYMBOL
        )

        kv(
            "Validator Start Line",
            getattr(
                validator_node,
                "lineno",
                "UNKNOWN"
            )
        )

        kv(
            "Validator End Line",
            getattr(
                validator_node,
                "end_lineno",
                "UNKNOWN"
            )
        )

        kv(
            "Validator Semantic SHA256",
            semantic_hash(
                validator_node
            )
        )

        passed(
            "Exact production validate_row() "
            "FunctionDef resolved."
        )

        # --------------------------------------------------------
        # COMPILE EXACT VALIDATOR
        # --------------------------------------------------------

        banner(
            "EXACT PRODUCTION VALIDATOR COMPILATION"
        )

        validator_namespace = build_validator_namespace(
            validator_tree,
            validator_node
        )

        validator = validator_namespace[
            VALIDATOR_SYMBOL
        ]

        if not callable(validator):
            failed(
                "Resolved validate_row is not callable."
            )

        try:
            signature = inspect.signature(
                validator
            )
        except Exception as exc:
            failed(
                f"Could not inspect exact validator "
                f"signature: {exc}"
            )

        kv(
            "Resolved Runtime Signature",
            signature
        )

        expected_signature = "(row, columns)"

        if str(signature) != expected_signature:
            failed(
                "Exact validator signature mismatch.\n"
                f"Expected: {expected_signature}\n"
                f"Actual:   {signature}"
            )

        passed(
            "Exact validator signature = (row, columns)"
        )

        # --------------------------------------------------------
        # EXACT RUNTIME EXECUTION
        # --------------------------------------------------------

        results, errors, status_counter = (
            execute_validator(
                validator,
                rows,
                columns
            )
        )

        verify_validator_execution(
            results,
            errors
        )

        # --------------------------------------------------------
        # IMPORTANT:
        # NO eligible/rejected/reason analysis here.
        # --------------------------------------------------------

        banner(
            "FRONTIER GATE"
        )

        print(
            "eligible/rejected/reason analysis NOT executed."
        )

        print(
            "It is intentionally blocked until exact "
            "validate_row(row, columns) runtime execution "
            "passes across all 987 Contract rows."
        )

        # --------------------------------------------------------
        # INTEGRITY
        # --------------------------------------------------------

        verify_integrity_after(
            production_hash_before,
            database_size_before,
            database_hash_before
        )

        # --------------------------------------------------------
        # FINAL
        # --------------------------------------------------------

        banner(
            "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
        )

        kv(
            "Runtime Acquisition Rows",
            len(rows)
        )

        kv(
            "Validator Runtime Rows",
            len(results)
        )

        kv(
            "Validator Runtime Errors",
            len(errors)
        )

        kv(
            "Validator",
            "validate_row(row, columns)"
        )

        kv(
            "Contract",
            CONTRACT_TECHNICAL_VERSION
        )

        kv(
            "Source",
            CONTRACT_SOURCE
        )

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
            "EXACT acquire_real_rows() EXECUTED"
        )

        passed(
            "987 REAL CONTRACT ROWS ACQUIRED"
        )

        passed(
            "EXACT validator import binding resolved"
        )

        passed(
            "EXACT validate_row() FunctionDef resolved"
        )

        passed(
            "EXACT validator signature verified"
        )

        passed(
            "EXACT validate_row(row, columns) "
            "executed against all 987 rows"
        )

        passed(
            "987 validator results produced"
        )

        passed(
            "ZERO validator execution errors"
        )

        passed(
            "PRODUCTION SOURCE UNCHANGED"
        )

        passed(
            "DATABASE UNCHANGED"
        )

        banner(
            "FINAL STATUS : PASS"
        )

        print(
            "TECHNICAL CONTRACT v0.5"
        )

        print(
            "RUNTIME ACQUISITION + EXACT VALIDATOR "
            "RESOLUTION + EXACT validate_row(row, columns) "
            "EXECUTION VERIFIED."
        )

        print()
        print(
            "NEXT FRONTIER:"
        )
        print(
            "eligible / rejected / reason analysis"
        )

    except Exception:

        banner(
            "FINAL STATUS : FAIL"
        )

        traceback.print_exc()

        raise

    finally:

        if conn is not None:

            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()