
# -*- coding: utf-8 -*-

"""
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.9

PURPOSE
-------
READ-ONLY runtime verification of:

    acquire_real_rows()
        ->
    exact production validate_row(row, columns)
        ->
    PASS / FAIL

IMPORTANT
---------
- Production main() is NEVER executed.
- Production modules are NEVER imported.
- SQLite is opened read-only.
- PRAGMA query_only must equal 1.
- The validator is resolved from AST, not by importing production modules.
- No synthetic rows.
- No DB writes.
- No fallback validator.
- No guessed import binding.
- If validator resolution is ambiguous -> FAIL.
- If validator dependencies cannot be safely resolved -> FAIL.

NEXT STAGE
----------
Only if this script finishes PASS should we analyze:
    eligible / rejected / reason
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
from pathlib import Path


# ============================================================================
# CONFIG
# ============================================================================

PRODUCTION_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

PROJECT_ROOT = PRODUCTION_FILE.parent

TARGET_TABLE = "market_technical"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

VALIDATOR_SYMBOL = "validate_row"
TRACE_SYMBOL = "trace_real_validation"
ACQUIRE_SYMBOL = "acquire_real_rows"

# We deliberately do not trust a production TRACE_LIMIT value.
# Acquisition must cover the entire contract population.
TRACE_LIMIT = EXPECTED_CONTRACT_ROWS


# ============================================================================
# OUTPUT
# ============================================================================

LINE = "=" * 100


def banner(title):
    print()
    print(LINE)
    print(title)
    print(LINE)


def kv(key, value):
    print(f"{key:<55} {value}")


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


# ============================================================================
# HASHING
# ============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def semantic_sha256(node) -> str:
    source = ast.unparse(node)

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()


# ============================================================================
# AST LOADING
# ============================================================================

def load_ast(path: Path):
    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(path)
    )

    return source, tree


def function_defs(tree, name):
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]


def unique_function(tree, name, path):
    nodes = function_defs(tree, name)

    if not nodes:
        failed(
            f"No FunctionDef '{name}' found in {path}"
        )

    if len(nodes) > 1:
        locations = [
            getattr(node, "lineno", "?")
            for node in nodes
        ]

        failed(
            f"Ambiguous FunctionDef '{name}' in {path}; "
            f"locations={locations}"
        )

    return nodes[0]


# ============================================================================
# CALL DISCOVERY
# ============================================================================

def find_exact_call(node, function_name):
    matches = []

    for child in ast.walk(node):

        if not isinstance(child, ast.Call):
            continue

        func = child.func

        if isinstance(func, ast.Name):
            if func.id == function_name:
                matches.append(child)

        elif isinstance(func, ast.Attribute):
            if func.attr == function_name:
                matches.append(child)

    return matches


def resolve_validator_call(trace_node):
    calls = find_exact_call(
        trace_node,
        VALIDATOR_SYMBOL
    )

    exact = []

    for call in calls:

        if not isinstance(
            call.func,
            ast.Name
        ):
            continue

        if call.func.id != VALIDATOR_SYMBOL:
            continue

        exact.append(call)

    if len(exact) != 1:

        failed(
            "Expected exactly one direct production "
            f"call to {VALIDATOR_SYMBOL}() inside "
            f"{TRACE_SYMBOL}(); found {len(exact)}."
        )

    call = exact[0]

    if len(call.args) != 2:

        failed(
            f"Production validator call must have exactly "
            f"2 positional arguments; found {len(call.args)}."
        )

    first = call.args[0]
    second = call.args[1]

    if not (
        isinstance(first, ast.Name)
        and first.id == "row"
    ):
        failed(
            "Production validator first argument is not "
            "exactly variable 'row'."
        )

    if not (
        isinstance(second, ast.Name)
        and second.id == "columns"
    ):
        failed(
            "Production validator second argument is not "
            "exactly variable 'columns'."
        )

    return call


# ============================================================================
# SOURCE DISCOVERY
# ============================================================================

def python_files(root: Path):
    files = []

    for path in root.rglob("*.py"):

        if "__pycache__" in path.parts:
            continue

        if path.name.startswith("ARUNDA_TECHNICAL_CONTRACT_PRODUCTION_RUNTIME_VALIDATION_"):
            continue

        files.append(path)

    return sorted(files)


def discover_validator_sources(root: Path):
    """
    Search project ASTs for validate_row definitions.

    We do NOT execute anything.

    A candidate is acceptable only if:
        - it is a real FunctionDef
        - it has exactly 2 positional parameters
        - the parameter names are row, columns
    """

    candidates = []

    for path in python_files(root):

        try:
            source, tree = load_ast(path)

        except Exception:
            continue

        for node in function_defs(
            tree,
            VALIDATOR_SYMBOL
        ):

            args = node.args

            positional = (
                list(args.posonlyargs)
                + list(args.args)
            )

            if len(positional) != 2:
                continue

            names = [
                arg.arg
                for arg in positional
            ]

            if names != [
                "row",
                "columns"
            ]:
                continue

            candidates.append(
                {
                    "path": path,
                    "source": source,
                    "tree": tree,
                    "node": node,
                }
            )

    return candidates


def resolve_real_validator(root: Path):
    banner(
        "REAL PRODUCTION VALIDATOR AST RESOLUTION"
    )

    candidates = discover_validator_sources(
        root
    )

    print(
        "AST validator candidates:"
    )

    for candidate in candidates:

        node = candidate["node"]

        print(
            f"  {candidate['path']}"
            f":{node.lineno}-{node.end_lineno}"
            f"  semantic_sha256="
            f"{semantic_sha256(node)}"
        )

    if not candidates:

        failed(
            "No AST FunctionDef validate_row(row, columns) "
            "was found anywhere in the production project."
        )

    # ------------------------------------------------------------------
    # Prefer the file explicitly named by trace_real_validation's text.
    # The production trace itself says:
    #
    # "validate_row() imported from market_technical_engine.py"
    #
    # We use this as evidence, not as an import binding.
    # ------------------------------------------------------------------

    explicit = [
        candidate
        for candidate in candidates
        if candidate["path"].name
        == "market_technical_engine.py"
    ]

    if len(explicit) == 1:

        candidate = explicit[0]

        passed(
            "Exact validator resolved from "
            "market_technical_engine.py by AST."
        )

        return candidate

    if len(explicit) > 1:

        failed(
            "Multiple market_technical_engine.py "
            "validator candidates detected."
        )

    # ------------------------------------------------------------------
    # No explicitly named file.
    #
    # Accept only one globally unique candidate.
    # ------------------------------------------------------------------

    if len(candidates) != 1:

        failed(
            "validate_row(row, columns) exists in multiple "
            "production AST files and no unique source can "
            "be established safely."
        )

    passed(
        "Exact validator resolved from the only "
        "unique AST FunctionDef candidate."
    )

    return candidates[0]


# ============================================================================
# DEPENDENCY ANALYSIS
# ============================================================================

BUILTIN_SAFE_NAMES = {
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
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
    "isinstance",
    "type",
    "ValueError",
    "TypeError",
    "RuntimeError",
    "Exception",
    "True",
    "False",
    "None",
}


def load_bound_names(tree):
    """
    Static AST symbol table.

    No code is executed.
    """

    bound = set()

    for node in tree.body:

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            bound.add(node.name)

        elif isinstance(
            node,
            (ast.Assign, ast.AnnAssign)
        ):

            targets = []

            if isinstance(node, ast.Assign):
                targets = node.targets

            else:
                targets = [node.target]

            for target in targets:

                if isinstance(
                    target,
                    ast.Name
                ):
                    bound.add(target.id)

        elif isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:
                bound.add(
                    alias.asname or alias.name.split(".")[0]
                )

        elif isinstance(
            node,
            ast.ImportFrom
        ):

            for alias in node.names:

                if alias.name == "*":
                    continue

                bound.add(
                    alias.asname or alias.name
                )

    return bound


def validator_global_names(node):
    """
    Find global names referenced by validate_row.

    Local parameters and locally assigned variables
    are excluded.
    """

    local = {
        "row",
        "columns",
    }

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Assign
        ):
            for target in child.targets:

                if isinstance(
                    target,
                    ast.Name
                ):
                    local.add(target.id)

        elif isinstance(
            child,
            ast.AnnAssign
        ):

            if isinstance(
                child.target,
                ast.Name
            ):
                local.add(
                    child.target.id
                )

        elif isinstance(
            child,
            ast.For
        ):

            if isinstance(
                child.target,
                ast.Name
            ):
                local.add(
                    child.target.id
                )

    names = set()

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Name
        ):
            continue

        if not isinstance(
            child.ctx,
            ast.Load
        ):
            continue

        if child.id in local:
            continue

        names.add(
            child.id
        )

    return names


# ============================================================================
# AST-ONLY NAMESPACE BUILDER
# ============================================================================

def compile_exact_function(
    validator_candidate
):
    """
    Compile ONLY the validator FunctionDef.

    No production module import occurs.

    Required globals are resolved from AST definitions
    in the same source file where possible.
    """

    source = validator_candidate["source"]
    tree = validator_candidate["tree"]
    validator_node = validator_candidate["node"]

    namespace = {
        name: __builtins__[name]
        for name in BUILTIN_SAFE_NAMES
        if isinstance(__builtins__, dict)
        and name in __builtins__
    }

    # Python exposes __builtins__ as module in some contexts.
    import builtins

    namespace = {
        name: getattr(
            builtins,
            name
        )
        for name in BUILTIN_SAFE_NAMES
        if hasattr(
            builtins,
            name
        )
    }

    # ---------------------------------------------------------------
    # First collect literal/simple module constants.
    # ---------------------------------------------------------------

    for statement in tree.body:

        if not isinstance(
            statement,
            ast.Assign
        ):
            continue

        if len(statement.targets) != 1:
            continue

        target = statement.targets[0]

        if not isinstance(
            target,
            ast.Name
        ):
            continue

        name = target.id

        try:

            code = compile(
                ast.Module(
                    body=[statement],
                    type_ignores=[]
                ),
                filename=str(
                    validator_candidate["path"]
                ),
                mode="exec"
            )

            exec(
                code,
                namespace,
                namespace
            )

        except Exception:
            # Do NOT guess.
            # The missing symbol will be reported below.
            continue

    # ---------------------------------------------------------------
    # Compile functions from the same source file.
    #
    # We compile definitions but never execute module main().
    # ---------------------------------------------------------------

    functions = {}

    for statement in tree.body:

        if not isinstance(
            statement,
            ast.FunctionDef
        ):
            continue

        if statement.name == validator_node.name:
            continue

        functions[
            statement.name
        ] = statement

    required = validator_global_names(
        validator_node
    )

    # Resolve direct function dependencies recursively.
    queue = list(required)
    included = set()

    while queue:

        name = queue.pop()

        if name in included:
            continue

        if name not in functions:
            continue

        included.add(name)

        nested_required = validator_global_names(
            functions[name]
        )

        for dep in nested_required:

            if dep not in included:
                queue.append(dep)

    # Compile dependency functions.
    for name in sorted(included):

        node = functions[name]

        try:

            code = compile(
                ast.Module(
                    body=[node],
                    type_ignores=[]
                ),
                filename=str(
                    validator_candidate["path"]
                ),
                mode="exec"
            )

            exec(
                code,
                namespace,
                namespace
            )

        except Exception as exc:

            failed(
                f"Could not safely compile AST dependency "
                f"'{name}': {type(exc).__name__}: {exc}"
            )

    # ---------------------------------------------------------------
    # Check unresolved globals BEFORE validator execution.
    # ---------------------------------------------------------------

    unresolved = set()

    for name in required:

        if name in namespace:
            continue

        if name in functions:
            continue

        unresolved.add(name)

    if unresolved:

        failed(
            "Exact validate_row() has unresolved production "
            "dependencies: "
            + ", ".join(
                sorted(unresolved)
            )
            + ". "
            "Refusing fallback or guessed implementation."
        )

    # ---------------------------------------------------------------
    # Compile exact validator.
    # ---------------------------------------------------------------

    code = compile(
        ast.Module(
            body=[validator_node],
            type_ignores=[]
        ),
        filename=str(
            validator_candidate["path"]
        ),
        mode="exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    validator = namespace.get(
        VALIDATOR_SYMBOL
    )

    if not callable(validator):

        failed(
            "Exact AST validator compiled but did not "
            "produce callable validate_row."
        )

    return (
        validator,
        namespace,
        validator_node
    )


# ============================================================================
# READ-ONLY DATABASE
# ============================================================================

def open_read_only_database():
    uri = (
        "file:"
        + str(
            DATABASE_FILE.resolve()
        ).replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if query_only != 1:

        conn.close()

        failed(
            "SQLite PRAGMA query_only is not 1."
        )

    passed(
        "SQLite PRAGMA query_only = 1"
    )

    return conn


# ============================================================================
# DATABASE PREFLIGHT
# ============================================================================

def database_preflight(conn):
    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
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
        )
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
        )
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
        )
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
        )
    ).fetchone()[0]

    kv("Database Total", total)
    kv("Contract Population", contract)
    kv("Museum Population", museum)
    kv("Contract MIN ID", min_id)
    kv("Contract MAX ID", max_id)
    kv("Contract DISTINCT IDs", distinct_ids)

    if total != EXPECTED_CONTRACT_ROWS + EXPECTED_MUSEUM_ROWS:
        failed(
            f"Database total mismatch: {total}"
        )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Contract population mismatch: {contract}"
        )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            f"Museum population mismatch: {museum}"
        )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Contract distinct ID mismatch: {distinct_ids}"
        )

    passed(
        "DATABASE POPULATION = 6909"
    )

    passed(
        "CONTRACT POPULATION = 987"
    )

    passed(
        "MUSEUM POPULATION = 5922"
    )


# ============================================================================
# EXACT acquire_real_rows
# ============================================================================

def execute_acquire_real_rows(
    conn,
    acquire_function
):
    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    columns = [
        row[1]
        for row in conn.execute(
            f"""
            PRAGMA table_info("{TARGET_TABLE}")
            """
        ).fetchall()
    ]

    if not columns:
        failed(
            f"No columns discovered for {TARGET_TABLE}"
        )

    rows = acquire_function(
        conn,
        columns,
        EXPECTED_CONTRACT_ROWS
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:

        failed(
            "Runtime acquisition count mismatch: "
            f"{len(rows)}"
        )

    passed(
        f"Runtime acquisition = {EXPECTED_CONTRACT_ROWS} rows"
    )

    return rows, columns


# ============================================================================
# ACQUISITION CONTRACT VERIFICATION
# ============================================================================

def verify_acquired_rows(
    rows,
    columns
):
    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime row count != 987"
        )

    ids = [
        row["id"]
        for row in rows
    ]

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
            "Runtime technical_version contract mismatch."
        )

    if engine_versions != {
        CONTRACT_ENGINE_VERSION
    }:
        failed(
            "Runtime engine_version contract mismatch."
        )

    if sources != {
        CONTRACT_SOURCE
    }:
        failed(
            "Runtime source contract mismatch."
        )

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime IDs are not distinct."
        )

    if min(ids) != 5923:
        failed(
            f"Runtime MIN ID mismatch: {min(ids)}"
        )

    if max(ids) != 6909:
        failed(
            f"Runtime MAX ID mismatch: {max(ids)}"
        )

    if ids != sorted(
        ids,
        reverse=True
    ):
        failed(
            "Runtime ordering is not id DESC."
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
# EXACT VALIDATOR EXECUTION
# ============================================================================

def execute_exact_validator(
    validator,
    rows,
    columns
):
    banner(
        "EXACT PRODUCTION validate_row(row, columns) RUNTIME"
    )

    kv(
        "Validator",
        VALIDATOR_SYMBOL
    )

    kv(
        "Input Rows",
        len(rows)
    )

    kv(
        "Call",
        "validate_row(row, columns)"
    )

    try:

        signature = inspect.signature(
            validator
        )

    except Exception as exc:

        failed(
            "Could not inspect exact validator signature: "
            f"{type(exc).__name__}: {exc}"
        )

    print()
    print(
        "EXACT VALIDATOR SIGNATURE:"
    )

    print(
        signature
    )

    parameters = list(
        signature.parameters.values()
    )

    if len(parameters) != 2:
        failed(
            "Exact validator does not have exactly "
            "2 parameters."
        )

    if [
        parameter.name
        for parameter in parameters
    ] != [
        "row",
        "columns"
    ]:
        failed(
            "Exact validator parameter names are not "
            "exactly (row, columns)."
        )

    passed(
        "Exact validator signature = (row, columns)"
    )

    results = []

    errors = []

    status_counter = Counter()
    score_counter = Counter()
    flag_counter = Counter()

    # ------------------------------------------------------------------
    # IMPORTANT:
    # We execute every row.
    # We do NOT silently discard errors.
    # ------------------------------------------------------------------

    for index, row in enumerate(
        rows,
        1
    ):

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
                    "validate_row() did not return tuple"
                )

            if len(result) != 3:
                raise RuntimeError(
                    "validate_row() return tuple length "
                    f"= {len(result)}"
                )

            score, status, flags = result

            results.append(
                {
                    "id": record_id,
                    "symbol": symbol,
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

                    flag = flag.strip()

                    if flag:
                        flag_counter[
                            flag
                        ] += 1

        except Exception as exc:

            errors.append(
                {
                    "index": index,
                    "id": record_id,
                    "symbol": symbol,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            print()
            print(
                f"[FAIL] Validator execution row "
                f"{index}"
            )

            print(
                f"  id      : {record_id}"
            )

            print(
                f"  symbol  : {symbol}"
            )

            print(
                f"  error   : "
                f"{type(exc).__name__}: {exc}"
            )

            # Do not continue pretending this is valid.
            # One production execution error means FAIL.
            break

    if errors:

        failed(
            "REAL validate_row(row, columns) execution "
            f"failed; errors={len(errors)}."
        )

    if len(results) != len(rows):

        failed(
            "Validator result count does not equal "
            "input row count."
        )

    banner(
        "REAL VALIDATOR EXECUTION SUMMARY"
    )

    kv(
        "Rows Input",
        len(rows)
    )

    kv(
        "Rows Validated",
        len(results)
    )

    kv(
        "Execution Errors",
        len(errors)
    )

    print()
    print(
        "STATUS DISTRIBUTION:"
    )

    for key, value in status_counter.items():
        print(
            f"  {key:<35} {value}"
        )

    print()
    print(
        "SCORE DISTRIBUTION:"
    )

    for key, value in score_counter.items():
        print(
            f"  {key:<35} {value}"
        )

    print()
    print(
        "FLAG DISTRIBUTION:"
    )

    if flag_counter:

        for key, value in flag_counter.items():
            print(
                f"  {key:<35} {value}"
            )

    else:
        print(
            "  NONE"
        )

    passed(
        "REAL validate_row(row, columns) "
        "executed successfully on all 987 rows."
    )

    return results


# ============================================================================
# INTEGRITY
# ============================================================================

def verify_database_unchanged(
    before_size,
    before_sha
):
    banner(
        "DATABASE INTEGRITY AFTER RUNTIME"
    )

    after_size = DATABASE_FILE.stat().st_size
    after_sha = sha256_file(
        DATABASE_FILE
    )

    kv(
        "Database Size BEFORE",
        before_size
    )

    kv(
        "Database Size AFTER",
        after_size
    )

    kv(
        "Database SHA256 BEFORE",
        before_sha
    )

    kv(
        "Database SHA256 AFTER",
        after_sha
    )

    if before_size != after_size:
        failed(
            "Database size changed."
        )

    if before_sha != after_sha:
        failed(
            "Database SHA256 changed."
        )

    passed(
        "Database size unchanged"
    )

    passed(
        "Database SHA256 unchanged"
    )


def verify_production_unchanged(
    before_sha
):
    banner(
        "PRODUCTION SOURCE INTEGRITY AFTER RUNTIME"
    )

    after_sha = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        before_sha
    )

    kv(
        "Production SHA256 AFTER",
        after_sha
    )

    if before_sha != after_sha:
        failed(
            "Production source changed."
        )

    passed(
        "Production source unchanged"
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    production_before_sha = sha256_file(
        PRODUCTION_FILE
    )

    database_before_size = (
        DATABASE_FILE.stat().st_size
    )

    database_before_sha = sha256_file(
        DATABASE_FILE
    )

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.9"
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
        ACQUIRE_SYMBOL
    )

    kv(
        "Trace Function",
        TRACE_SYMBOL
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
        "Only AST-resolved production functions are executed."
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

    banner(
        "PRODUCTION / DATABASE INTEGRITY BEFORE"
    )

    kv(
        "Production SHA256 BEFORE",
        production_before_sha
    )

    kv(
        "Database Size BEFORE",
        database_before_size
    )

    kv(
        "Database SHA256 BEFORE",
        database_before_sha
    )

    # ------------------------------------------------------------------
    # PRODUCTION AST
    # ------------------------------------------------------------------

    production_source, production_tree = load_ast(
        PRODUCTION_FILE
    )

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    acquire_node = unique_function(
        production_tree,
        ACQUIRE_SYMBOL,
        PRODUCTION_FILE
    )

    trace_node = unique_function(
        production_tree,
        TRACE_SYMBOL,
        PRODUCTION_FILE
    )

    kv(
        "acquire_real_rows semantic SHA256",
        semantic_sha256(acquire_node)
    )

    kv(
        "trace_real_validation semantic SHA256",
        semantic_sha256(trace_node)
    )

    # ------------------------------------------------------------------
    # EXACT TRACE CALL
    # ------------------------------------------------------------------

    banner(
        "EXACT PRODUCTION VALIDATION CALL DISCOVERY"
    )

    validator_call = resolve_validator_call(
        trace_node
    )

    kv(
        "Validator Call",
        "validate_row(row, columns)"
    )

    passed(
        "Exact production validation call "
        "resolved from trace_real_validation()."
    )

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------

    conn = open_read_only_database()

    try:

        database_preflight(
            conn
        )

        # --------------------------------------------------------------
        # Compile exact acquire_real_rows.
        #
        # We inject ONLY the constants/helpers required by its body.
        # --------------------------------------------------------------

        banner(
            "EXACT PRODUCTION acquire_real_rows() COMPILATION"
        )

        acquire_namespace = {
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
            "RuntimeError": RuntimeError,
        }

        acquire_code = compile(
            ast.Module(
                body=[acquire_node],
                type_ignores=[]
            ),
            filename=str(
                PRODUCTION_FILE
            ),
            mode="exec"
        )

        exec(
            acquire_code,
            acquire_namespace,
            acquire_namespace
        )

        acquire_function = acquire_namespace.get(
            ACQUIRE_SYMBOL
        )

        if not callable(
            acquire_function
        ):
            failed(
                "Exact acquire_real_rows() did not "
                "compile into callable."
            )

        passed(
            "Exact acquire_real_rows() compiled."
        )

        # --------------------------------------------------------------
        # REAL ACQUISITION
        # --------------------------------------------------------------

        rows, columns = execute_acquire_real_rows(
            conn,
            acquire_function
        )

        verify_acquired_rows(
            rows,
            columns
        )

        # --------------------------------------------------------------
        # EXACT VALIDATOR RESOLUTION
        # --------------------------------------------------------------

        validator_candidate = resolve_real_validator(
            PROJECT_ROOT
        )

        banner(
            "EXACT VALIDATOR SOURCE"
        )

        validator_node = validator_candidate[
            "node"
        ]

        kv(
            "Validator File",
            validator_candidate["path"]
        )

        kv(
            "Validator Lines",
            f"{validator_node.lineno}-"
            f"{validator_node.end_lineno}"
        )

        kv(
            "Validator Semantic SHA256",
            semantic_sha256(
                validator_node
            )
        )

        # --------------------------------------------------------------
        # EXACT VALIDATOR COMPILATION
        # --------------------------------------------------------------

        banner(
            "EXACT PRODUCTION VALIDATOR COMPILATION"
        )

        (
            validator,
            validator_namespace,
            validator_node
        ) = compile_exact_function(
            validator_candidate
        )

        passed(
            "Exact validate_row() AST compiled "
            "without importing production module."
        )

        # --------------------------------------------------------------
        # EXACT RUNTIME EXECUTION
        # --------------------------------------------------------------

        results = execute_exact_validator(
            validator,
            rows,
            columns
        )

        # --------------------------------------------------------------
        # INTEGRITY
        # --------------------------------------------------------------

        verify_production_unchanged(
            production_before_sha
        )

        verify_database_unchanged(
            database_before_size,
            database_before_sha
        )

        # --------------------------------------------------------------
        # FINAL
        # --------------------------------------------------------------

        banner(
            "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
        )

        kv(
            "Runtime Rows",
            len(rows)
        )

        kv(
            "Validator Rows",
            len(results)
        )

        kv(
            "Validator",
            "validate_row(row, columns)"
        )

        kv(
            "Contract",
            CONTRACT_TECHNICAL_VERSION
        )

        print()

        passed(
            "DATABASE READ ONLY"
        )

        passed(
            "PRODUCTION main() NOT EXECUTED"
        )

        passed(
            "PRODUCTION MODULES NOT IMPORTED"
        )

        passed(
            "EXACT acquire_real_rows() EXECUTED"
        )

        passed(
            "EXACT trace_real_validation() CALL "
            "DISCOVERED"
        )

        passed(
            "EXACT validate_row(row, columns) "
            "RESOLVED FROM AST"
        )

        passed(
            "EXACT validate_row(row, columns) "
            "EXECUTED"
        )

        passed(
            "ALL 987 REAL CONTRACT ROWS VALIDATED"
        )

        passed(
            "PRODUCTION SOURCE UNCHANGED"
        )

        passed(
            "DATABASE UNCHANGED"
        )

        print()
        print(
            "FINAL STATUS           : PASS"
        )

        print()
        print(
            "TECHNICAL CONTRACT v0.5"
        )

        print(
            "RUNTIME ACQUISITION + EXACT VALIDATOR "
            "RESOLUTION + EXACT VALIDATION PASSED"
        )

        print()
        print(
            "NEXT FRONTIER:"
        )

        print(
            "eligible / rejected / reason analysis"
        )

    finally:

        conn.close()


if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print(LINE)
        print(
            "FINAL STATUS           : FAIL"
        )
        print(LINE)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()

        traceback.print_exc()

        sys.exit(1)
