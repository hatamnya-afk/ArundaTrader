# -*- coding: utf-8 -*-

"""
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.6

READ ONLY / NO PRODUCTION MODULE IMPORT

Purpose
-------
1. Resolve acquire_real_rows() from production AST.
2. Execute acquire_real_rows() against the REAL TECHNICAL_v0.5 contract.
3. Resolve the REAL validate_row(row, columns) call from
   trace_real_validation().
4. Follow the production import binding for validate_row.
5. Resolve validate_row from the imported production source by AST.
6. Compile only the required AST dependency closure.
7. Execute the exact production call:

       validate_row(row, columns)

8. Report actual score / status / flags.
9. Verify production source and database are unchanged.

NO production main()
NO production module import
NO database write
NO synthetic rows
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import sqlite3
import sys
import traceback
import importlib.util
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

def banner(title: str):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<55} {value}")


def passed(message):
    print(f"[PASS] {message}")


def failed(message):
    raise RuntimeError(message)


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


# ============================================================================
# AST HELPERS
# ============================================================================

def parse_source(path: Path):
    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(path)
    )

    return source, tree


def all_function_defs(tree):
    return [
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


def find_function_defs(tree, name):
    return [
        node
        for node in all_function_defs(tree)
        if node.name == name
    ]


def resolve_unique_function(tree, name, label):
    matches = find_function_defs(
        tree,
        name
    )

    if not matches:
        failed(
            f"{label}: FunctionDef '{name}' not found."
        )

    if len(matches) != 1:
        failed(
            f"{label}: expected exactly one FunctionDef "
            f"'{name}', found {len(matches)}."
        )

    return matches[0]


def semantic_function_hash(node):
    normalized = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def function_source(source, node):
    return ast.get_source_segment(
        source,
        node
    ) or ""


# ============================================================================
# DATABASE
# ============================================================================

def open_read_only_database():

    if not DATABASE_FILE.exists():
        failed(
            f"Database does not exist: {DATABASE_FILE}"
        )

    uri = (
        "file:"
        + str(DATABASE_FILE.resolve())
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    # Explicitly force query_only.
    conn.execute(
        "PRAGMA query_only = ON"
    )

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if value != 1:
        conn.close()

        failed(
            "SQLite PRAGMA query_only could not be enabled."
        )

    return conn


def database_integrity_snapshot(conn):

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
        )
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
        )
    ).fetchone()

    return {
        "total": total,
        "contract": contract,
        "museum": museum,
        "min_id": min_id,
        "max_id": max_id,
        "distinct_ids": distinct_ids,
    }


def verify_database_preflight(conn):

    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    snapshot = database_integrity_snapshot(
        conn
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

    kv(
        "Database Total",
        snapshot["total"]
    )

    kv(
        "Contract Population",
        snapshot["contract"]
    )

    kv(
        "Museum Population",
        snapshot["museum"]
    )

    kv(
        "Contract MIN ID",
        snapshot["min_id"]
    )

    kv(
        "Contract MAX ID",
        snapshot["max_id"]
    )

    kv(
        "Contract DISTINCT IDs",
        snapshot["distinct_ids"]
    )

    if snapshot["total"] != 6909:
        failed(
            "DATABASE TOTAL != 6909"
        )

    if snapshot["contract"] != EXPECTED_CONTRACT_ROWS:
        failed(
            "CONTRACT POPULATION != 987"
        )

    if snapshot["museum"] != EXPECTED_MUSEUM_ROWS:
        failed(
            "MUSEUM POPULATION != 5922"
        )

    if snapshot["min_id"] != 5923:
        failed(
            "CONTRACT MIN ID != 5923"
        )

    if snapshot["max_id"] != 6909:
        failed(
            "CONTRACT MAX ID != 6909"
        )

    if snapshot["distinct_ids"] != 987:
        failed(
            "CONTRACT DISTINCT IDS != 987"
        )

    passed(
        "DATABASE TOTAL = 6909"
    )

    passed(
        "CONTRACT = 987"
    )

    passed(
        "MUSEUM = 5922"
    )

    passed(
        "CONTRACT ID RANGE = 5923..6909"
    )


# ============================================================================
# SAFE RUNTIME SUPPORT
# ============================================================================

def safe(value):
    try:
        return repr(value)
    except Exception:
        return "<unrepresentable>"


def runtime_banner(message):
    print()
    print(message)


# ============================================================================
# AST IMPORT DISCOVERY
# ============================================================================

def discover_symbol_imports(
    tree,
    symbol
):
    """
    Find bindings such as:

        from market_technical_engine import validate_row

    or:

        from package.module import validate_row as validate_row

    Also records wildcard imports separately.
    """

    exact = []
    wildcard = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.ImportFrom
        ):

            module = node.module or ""

            for alias in node.names:

                if alias.name == symbol:

                    local_name = (
                        alias.asname
                        if alias.asname
                        else alias.name
                    )

                    if local_name == symbol:

                        exact.append(
                            {
                                "kind": "from",
                                "module": module,
                                "name": alias.name,
                                "local": local_name,
                                "node": node,
                            }
                        )

                elif alias.name == "*":

                    wildcard.append(
                        {
                            "kind": "wildcard",
                            "module": module,
                            "node": node,
                        }
                    )

        elif isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                if local_name == symbol:

                    exact.append(
                        {
                            "kind": "import",
                            "module": alias.name,
                            "name": alias.name,
                            "local": local_name,
                            "node": node,
                        }
                    )

    return exact, wildcard


# ============================================================================
# MODULE PATH RESOLUTION — NO IMPORT
# ============================================================================

def resolve_module_source(
    module_name: str,
    production_file: Path
):
    """
    Resolve Python module source without importing it.

    Search order:
      1. production file directory
      2. sys.path entries
      3. importlib spec origin only

    Importlib.util.find_spec is used only for locating the source;
    the module itself is NEVER imported.
    """

    candidates = []

    production_dir = production_file.parent

    parts = module_name.split(".")

    relative_py = (
        production_dir.joinpath(
            *parts
        ).with_suffix(".py")
    )

    candidates.append(
        relative_py
    )

    relative_init = (
        production_dir.joinpath(
            *parts,
            "__init__.py"
        )
    )

    candidates.append(
        relative_init
    )

    for base in sys.path:

        if not base:
            base = os.getcwd()

        base_path = Path(base)

        candidates.append(
            base_path.joinpath(
                *parts
            ).with_suffix(".py")
        )

        candidates.append(
            base_path.joinpath(
                *parts,
                "__init__.py"
            )
        )

    seen = set()

    for candidate in candidates:

        try:
            resolved = candidate.resolve()
        except Exception:
            continue

        if resolved in seen:
            continue

        seen.add(
            resolved
        )

        if resolved.exists():
            return resolved

    # Last locator only.
    try:

        spec = importlib.util.find_spec(
            module_name
        )

        if spec is not None:

            origin = spec.origin

            if (
                origin
                and origin != "built-in"
            ):

                path = Path(origin)

                if path.exists():
                    return path

    except Exception:
        pass

    failed(
        "Could not resolve source for imported "
        f"production module '{module_name}' "
        "without importing it."
    )


# ============================================================================
# VALIDATOR CALL DISCOVERY
# ============================================================================

def discover_validator_call(
    trace_node,
    symbol
):
    """
    Resolve the exact call:

        validate_row(row, columns)

    from trace_real_validation().
    """

    calls = []

    for node in ast.walk(trace_node):

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

        if node.func.id != symbol:
            continue

        calls.append(
            node
        )

    if not calls:
        failed(
            f"No call to {symbol}() found inside "
            f"{TRACE_FUNCTION}()."
        )

    if len(calls) != 1:
        failed(
            f"Expected exactly one {symbol}() call "
            f"inside {TRACE_FUNCTION}(), found "
            f"{len(calls)}."
        )

    call = calls[0]

    if len(call.args) != 2:
        failed(
            f"Production {symbol}() call does not "
            "have exactly two positional arguments."
        )

    arg0 = call.args[0]
    arg1 = call.args[1]

    if not (
        isinstance(arg0, ast.Name)
        and arg0.id == "row"
    ):
        failed(
            "Production validation first argument "
            "is not exactly 'row'."
        )

    if not (
        isinstance(arg1, ast.Name)
        and arg1.id == "columns"
    ):
        failed(
            "Production validation second argument "
            "is not exactly 'columns'."
        )

    return call


# ============================================================================
# ACQUIRE FUNCTION
# ============================================================================

def reconstruct_acquire_sql(
    acquire_node
):
    """
    Semantic reconstruction only.

    Does NOT execute SQL.
    """

    sql_fragments = []

    for node in ast.walk(
        acquire_node
    ):

        if isinstance(
            node,
            ast.Constant
        ):

            if isinstance(
                node.value,
                str
            ):

                text = (
                    node.value
                    .replace(
                        "\n",
                        " "
                    )
                    .strip()
                    .lower()
                )

                if (
                    "select" in text
                    or "where" in text
                    or "order by" in text
                    or "limit" in text
                ):

                    sql_fragments.append(
                        text
                    )

    joined = " ".join(
        sql_fragments
    )

    # The production source uses an f-string:
    # FROM "{TARGET_TABLE}"
    #
    # The literal portions and Name TARGET_TABLE
    # are reconstructed semantically below.

    normalized = " ".join(
        joined.split()
    )

    return normalized


def verify_acquire_contract(
    acquire_node
):

    banner(
        "PRODUCTION acquire_real_rows() CONTRACT"
    )

    source_segment = ast.unparse(
        acquire_node
    )

    normalized = (
        source_segment
        .replace(
            "\n",
            " "
        )
        .lower()
    )

    required_fragments = [
        "select *",
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in required_fragments:

        if fragment not in normalized:

            failed(
                "Expected acquire_real_rows() "
                f"fragment missing: {fragment}"
            )

        passed(
            f"SQL contract fragment: {fragment}"
        )

    upper = normalized.upper()

    write_tokens = [
        " INSERT ",
        " UPDATE ",
        " DELETE ",
        " ALTER ",
        " CREATE ",
        " DROP ",
        " REPLACE ",
    ]

    padded = " " + upper + " "

    for token in write_tokens:

        if token in padded:

            failed(
                "SQL write operation detected "
                f"inside acquire_real_rows(): {token.strip()}"
            )

    passed(
        "No SQL write operation detected"
    )


# ============================================================================
# EXACT ACQUIRE RUNTIME
# ============================================================================

def compile_exact_acquire(
    acquire_node,
    source
):
    """
    Compile only acquire_real_rows().

    Required production constants / helpers are supplied
    explicitly. No production module is imported.
    """

    module = ast.Module(
        body=[
            acquire_node
        ],
        type_ignores=[]
    )

    ast.fix_missing_locations(
        module
    )

    namespace = {
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
        module,
        filename="<production acquire_real_rows>",
        mode="exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    return namespace[
        ACQUIRE_FUNCTION
    ]


def execute_acquisition(
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

    if not isinstance(
        rows,
        list
    ):
        rows = list(rows)

    kv(
        "Runtime Rows Returned",
        len(rows)
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime acquisition returned "
            f"{len(rows)} rows; expected "
            f"{EXPECTED_CONTRACT_ROWS}."
        )

    passed(
        "Runtime acquisition = 987 rows"
    )

    return rows, columns


# ============================================================================
# AST DEPENDENCY EXTRACTION
# ============================================================================

def names_used_by_function(
    node
):
    names = set()

    for child in ast.walk(
        node
    ):

        if isinstance(
            child,
            ast.Name
        ):

            if isinstance(
                child.ctx,
                ast.Load
            ):
                names.add(
                    child.id
                )

    return names


def function_local_names(
    node
):
    names = set()

    args = node.args

    for arg in (
        args.posonlyargs
        + args.args
        + args.kwonlyargs
    ):
        names.add(
            arg.arg
        )

    if args.vararg:
        names.add(
            args.vararg.arg
        )

    if args.kwarg:
        names.add(
            args.kwarg.arg
        )

    for child in ast.walk(
        node
    ):

        if isinstance(
            child,
            ast.Name
        ):

            if isinstance(
                child.ctx,
                ast.Store
            ):
                names.add(
                    child.id
                )

    return names


def collect_top_level_bindings(
    tree
):
    """
    Map production AST top-level symbols to AST nodes.

    Functions and assignments are included.
    """

    bindings = {}

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            bindings.setdefault(
                node.name,
                []
            ).append(
                node
            )

        elif isinstance(
            node,
            ast.Assign
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name
                ):

                    bindings.setdefault(
                        target.id,
                        []
                    ).append(
                        node
                    )

        elif isinstance(
            node,
            ast.AnnAssign
        ):

            if isinstance(
                node.target,
                ast.Name
            ):

                bindings.setdefault(
                    node.target.id,
                    []
                ).append(
                    node
                )

    return bindings


# ============================================================================
# SAFE AST VALIDATION COMPILATION
# ============================================================================

def build_validator_namespace(
    validator_tree,
    validator_node
):
    """
    Build a minimal namespace from the validator source.

    The actual production module is NEVER imported.

    Dependency closure:
      validate_row
        -> helper functions
        -> constant assignments

    External standard-library imports are loaded from their import
    declarations, but the production module itself is not imported.
    """

    bindings = collect_top_level_bindings(
        validator_tree
    )

    selected = {}
    queue = [
        VALIDATOR_SYMBOL
    ]

    # ------------------------------------------------------------
    # Resolve dependency closure.
    # ------------------------------------------------------------

    while queue:

        name = queue.pop()

        if name in selected:
            continue

        candidates = bindings.get(
            name,
            []
        )

        if not candidates:
            continue

        if len(candidates) != 1:
            failed(
                "Ambiguous production binding for "
                f"'{name}'."
            )

        node = candidates[0]

        selected[name] = node

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            used = names_used_by_function(
                node
            )

            local = function_local_names(
                node
            )

            for dependency in sorted(
                used - local
            ):

                if dependency in bindings:
                    queue.append(
                        dependency
                    )

    if VALIDATOR_SYMBOL not in selected:
        failed(
            "Validator dependency closure could not "
            f"resolve '{VALIDATOR_SYMBOL}'."
        )

    # ------------------------------------------------------------
    # External imports.
    # ------------------------------------------------------------

    namespace = {
        "__builtins__": __builtins__,
    }

    for node in validator_tree.body:

        if isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:

                module_name = alias.name

                try:
                    module = __import__(
                        module_name
                    )
                except Exception as exc:
                    failed(
                        "Could not load external dependency "
                        f"'{module_name}' required by validator: "
                        f"{type(exc).__name__}: {exc}"
                    )

                local_name = (
                    alias.asname
                    if alias.asname
                    else module_name.split(".")[0]
                )

                namespace[
                    local_name
                ] = module

        elif isinstance(
            node,
            ast.ImportFrom
        ):

            module_name = node.module

            if not module_name:
                continue

            try:
                module = __import__(
                    module_name,
                    fromlist=[
                        alias.name
                        for alias in node.names
                    ]
                )

            except Exception as exc:
                failed(
                    "Could not load external dependency "
                    f"'{module_name}' required by validator: "
                    f"{type(exc).__name__}: {exc}"
                )

            for alias in node.names:

                if alias.name == "*":
                    continue

                try:
                    value = getattr(
                        module,
                        alias.name
                    )
                except AttributeError as exc:
                    failed(
                        f"External symbol '{alias.name}' "
                        f"not found in '{module_name}'."
                    )

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name
                )

                namespace[
                    local_name
                ] = value

    # ------------------------------------------------------------
    # Compile selected AST nodes.
    # ------------------------------------------------------------

    ordered_nodes = []

    # Preserve original production order.
    for node in validator_tree.body:

        if node in selected.values():
            ordered_nodes.append(
                node
            )

    module = ast.Module(
        body=ordered_nodes,
        type_ignores=[]
    )

    ast.fix_missing_locations(
        module
    )

    code = compile(
        module,
        filename="<AST production validator>",
        mode="exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    return namespace


def resolve_validator_from_import(
    production_tree,
    production_file
):

    banner(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    exact, wildcard = discover_symbol_imports(
        production_tree,
        VALIDATOR_SYMBOL
    )

    kv(
        "Validator Symbol",
        VALIDATOR_SYMBOL
    )

    if exact:

        if len(exact) != 1:
            failed(
                "Multiple direct production import bindings "
                f"found for '{VALIDATOR_SYMBOL}'."
            )

        binding = exact[0]

        if binding["kind"] != "from":
            failed(
                "validate_row is not a direct imported function "
                "binding."
            )

        module_name = binding[
            "module"
        ]

        kv(
            "Production Import",
            f"from {module_name} import {VALIDATOR_SYMBOL}"
        )

        validator_file = resolve_module_source(
            module_name,
            production_file
        )

        kv(
            "Validator Source",
            validator_file
        )

        source, tree = parse_source(
            validator_file
        )

        nodes = find_function_defs(
            tree,
            VALIDATOR_SYMBOL
        )

        if not nodes:

            failed(
                f"Function '{VALIDATOR_SYMBOL}' not found "
                f"in imported source {validator_file}."
            )

        if len(nodes) != 1:

            failed(
                f"Expected exactly one '{VALIDATOR_SYMBOL}' "
                f"in {validator_file}, found {len(nodes)}."
            )

        node = nodes[0]

        passed(
            "REAL validate_row() resolved from imported "
            "production source AST"
        )

        kv(
            "Validator File",
            validator_file
        )

        kv(
            "Validator Start Line",
            node.lineno
        )

        kv(
            "Validator End Line",
            getattr(
                node,
                "end_lineno",
                node.lineno
            )
        )

        kv(
            "Validator Semantic SHA256",
            semantic_function_hash(node)
        )

        return (
            validator_file,
            source,
            tree,
            node
        )

    if wildcard:

        failed(
            "validate_row is available only through wildcard "
            "import; refusing unsafe resolution."
        )

    failed(
        "No production import binding for validate_row "
        "was found."
    )


# ============================================================================
# EXACT VALIDATOR RUNTIME
# ============================================================================

def execute_exact_validator(
    validator_namespace,
    validator_node,
    rows,
    columns
):

    banner(
        "EXACT PRODUCTION validate_row(row, columns) EXECUTION"
    )

    validator = validator_namespace.get(
        VALIDATOR_SYMBOL
    )

    if validator is None:
        failed(
            "Compiled validator namespace does not contain "
            "validate_row."
        )

    if not callable(
        validator
    ):
        failed(
            "Resolved validate_row is not callable."
        )

    signature = inspect.signature(
        validator
    )

    kv(
        "Runtime Validator Signature",
        signature
    )

    results = []

    status_counter = Counter()
    score_counter = Counter()
    flag_counter = Counter()

    execution_errors = []

    for index, row in enumerate(
        rows,
        1
    ):

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
                    f"= {len(result)}, expected 3"
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

                    flag = flag.strip()

                    if flag:
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
                    "index": index,
                    "id": record_id,
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    kv(
        "Rows Attempted",
        len(rows)
    )

    kv(
        "Successful Validation",
        len(results)
    )

    kv(
        "Validation Execution Errors",
        len(execution_errors)
    )

    if execution_errors:

        first = execution_errors[0]

        print()
        print(
            "FIRST VALIDATION EXECUTION ERROR:"
        )

        print(
            first["traceback"]
        )

        failed(
            "Production validate_row() execution "
            f"failed on {len(execution_errors)} row(s)."
        )

    if len(results) != EXPECTED_CONTRACT_ROWS:

        failed(
            "Successful validator results != 987."
        )

    passed(
        "All 987 Contract rows executed by "
        "exact production validate_row(row, columns)"
    )

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
    )


# ============================================================================
# RESULT ANALYSIS
# ============================================================================

def print_validation_summary(
    results,
    status_counter,
    score_counter,
    flag_counter
):

    banner(
        "REAL PRODUCTION VALIDATION SUMMARY"
    )

    kv(
        "Validation Rows",
        len(results)
    )

    print()
    print(
        "STATUS DISTRIBUTION:"
    )

    for status, count in status_counter.most_common():

        print(
            f"  {status:<40} : {count}"
        )

    print()
    print(
        "SCORE DISTRIBUTION:"
    )

    for score, count in score_counter.most_common():

        print(
            f"  {score:<40} : {count}"
        )

    print()
    print(
        "FLAG DISTRIBUTION:"
    )

    if not flag_counter:

        print(
            "  NONE"
        )

    else:

        for flag, count in flag_counter.most_common():

            print(
                f"  {flag:<40} : {count}"
            )

    # ------------------------------------------------------------
    # Do NOT assume the production meaning of status.
    #
    # We expose the REAL statuses first.
    # Only map eligible/rejected after observing exact
    # production vocabulary.
    # ------------------------------------------------------------

    eligible_candidates = Counter()
    rejected_candidates = Counter()

    for result in results:

        status = str(
            result["status"]
        ).strip().lower()

        if status in {
            "eligible",
            "accepted",
            "valid",
            "pass",
            "passed",
            "ok",
        }:

            eligible_candidates[
                result["status"]
            ] += 1

        elif status in {
            "rejected",
            "invalid",
            "fail",
            "failed",
            "reject",
            "no_trade",
            "no-trade",
        }:

            rejected_candidates[
                result["status"]
            ] += 1

    print()
    print(
        "SEMANTIC STATUS CANDIDATES:"
    )

    kv(
        "Eligible-like statuses",
        sum(
            eligible_candidates.values()
        )
    )

    kv(
        "Rejected-like statuses",
        sum(
            rejected_candidates.values()
        )
    )

    if eligible_candidates:

        print(
            "  Eligible-like:"
        )

        for key, value in eligible_candidates.items():

            print(
                f"    {key!r}: {value}"
            )

    if rejected_candidates:

        print(
            "  Rejected-like:"
        )

        for key, value in rejected_candidates.items():

            print(
                f"    {key!r}: {value}"
            )


# ============================================================================
# INTEGRITY AFTER
# ============================================================================

def verify_integrity_after(
    production_hash_before,
    database_hash_before,
    database_size_before,
    conn,
    production_file
):

    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER RUNTIME"
    )

    production_hash_after = sha256_file(
        production_file
    )

    database_size_after = (
        database_file.stat().st_size
        if False
        else DATABASE_FILE.stat().st_size
    )

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

    if (
        production_hash_after
        != production_hash_before
    ):

        failed(
            "Production source changed during runtime."
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

    if (
        database_size_after
        != database_size_before
    ):

        failed(
            "Database size changed during runtime."
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

    if (
        database_hash_after
        != database_hash_before
    ):

        failed(
            "Database SHA256 changed during runtime."
        )

    passed(
        "Database SHA256 unchanged"
    )

    # Query-only remains active until connection close.
    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if query_only != 1:

        failed(
            "SQLite query_only changed during runtime."
        )

    passed(
        "SQLite query_only remained 1"
    )


# ============================================================================
# FINAL
# ============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.6"
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

    # -----------------------------------------------------------------
    # Files
    # -----------------------------------------------------------------

    if not PRODUCTION_FILE.exists():
        failed(
            f"Production file not found: {PRODUCTION_FILE}"
        )

    if not DATABASE_FILE.exists():
        failed(
            f"Database not found: {DATABASE_FILE}"
        )

    production_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    database_size_before = (
        DATABASE_FILE.stat().st_size
    )

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

    # -----------------------------------------------------------------
    # Parse production source.
    # -----------------------------------------------------------------

    production_source, production_tree = parse_source(
        PRODUCTION_FILE
    )

    # -----------------------------------------------------------------
    # Resolve acquire_real_rows.
    # -----------------------------------------------------------------

    banner(
        "PRODUCTION AST DISCOVERY — acquire_real_rows()"
    )

    acquire_node = resolve_unique_function(
        production_tree,
        ACQUIRE_FUNCTION,
        "Production acquisition"
    )

    kv(
        "acquire_real_rows Semantic SHA256",
        semantic_function_hash(
            acquire_node
        )
    )

    print()
    print(
        ast.unparse(
            acquire_node
        )
    )

    verify_acquire_contract(
        acquire_node
    )

    # -----------------------------------------------------------------
    # Resolve trace_real_validation.
    # -----------------------------------------------------------------

    banner(
        "PRODUCTION AST DISCOVERY — trace_real_validation()"
    )

    trace_node = resolve_unique_function(
        production_tree,
        TRACE_FUNCTION,
        "Production validation trace"
    )

    kv(
        "trace_real_validation Semantic SHA256",
        semantic_function_hash(
            trace_node
        )
    )

    # -----------------------------------------------------------------
    # Resolve exact validator call.
    # -----------------------------------------------------------------

    banner(
        "EXACT PRODUCTION VALIDATION CALL DISCOVERY"
    )

    validator_call = discover_validator_call(
        trace_node,
        VALIDATOR_SYMBOL
    )

    kv(
        "Validator Call",
        "validate_row(row, columns)"
    )

    passed(
        "Exact production validation call resolved "
        "from trace_real_validation()"
    )

    # -----------------------------------------------------------------
    # Open DB.
    # -----------------------------------------------------------------

    conn = open_read_only_database()

    try:

        verify_database_preflight(
            conn
        )

        # -------------------------------------------------------------
        # Compile and execute acquisition.
        # -------------------------------------------------------------

        acquire_function = compile_exact_acquire(
            acquire_node,
            production_source
        )

        rows, columns = execute_acquisition(
            acquire_function,
            conn
        )

        # -------------------------------------------------------------
        # Verify acquisition result contract.
        # -------------------------------------------------------------

        banner(
            "RUNTIME ACQUISITION CONTRACT VERIFICATION"
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

        if len(rows) != 987:
            failed(
                "Runtime acquisition row count != 987"
            )

        if len(set(ids)) != 987:
            failed(
                "Runtime acquisition IDs are not distinct"
            )

        if technical_versions != {
            CONTRACT_TECHNICAL_VERSION
        }:
            failed(
                "Runtime acquisition technical_version "
                "scope mismatch"
            )

        if engine_versions != {
            CONTRACT_ENGINE_VERSION
        }:
            failed(
                "Runtime acquisition engine_version "
                "scope mismatch"
            )

        if sources != {
            CONTRACT_SOURCE
        }:
            failed(
                "Runtime acquisition source scope mismatch"
            )

        if min(ids) != 5923:
            failed(
                "Runtime acquisition MIN ID != 5923"
            )

        if max(ids) != 6909:
            failed(
                "Runtime acquisition MAX ID != 6909"
            )

        if ids != sorted(
            ids,
            reverse=True
        ):
            failed(
                "Runtime acquisition ordering is not id DESC"
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

        # -------------------------------------------------------------
        # Resolve REAL validator from imported source.
        # -------------------------------------------------------------

        (
            validator_file,
            validator_source,
            validator_tree,
            validator_node,
        ) = resolve_validator_from_import(
            production_tree,
            PRODUCTION_FILE
        )

        # -------------------------------------------------------------
        # Compile exact validator dependency closure.
        # -------------------------------------------------------------

        banner(
            "EXACT PRODUCTION VALIDATOR AST COMPILATION"
        )

        validator_namespace = build_validator_namespace(
            validator_tree,
            validator_node
        )

        validator = validator_namespace.get(
            VALIDATOR_SYMBOL
        )

        if not callable(
            validator
        ):
            failed(
                "Compiled production validate_row "
                "is not callable."
            )

        passed(
            "REAL validate_row() compiled from "
            "production AST dependency closure"
        )

        # -------------------------------------------------------------
        # Exact runtime execution.
        # -------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
        ) = execute_exact_validator(
            validator_namespace,
            validator_node,
            rows,
            columns
        )

        # -------------------------------------------------------------
        # Summary.
        # -------------------------------------------------------------

        print_validation_summary(
            results,
            status_counter,
            score_counter,
            flag_counter
        )

        # -------------------------------------------------------------
        # Integrity.
        # -------------------------------------------------------------

        verify_integrity_after(
            production_hash_before,
            database_hash_before,
            database_size_before,
            conn,
            PRODUCTION_FILE
        )

        # -------------------------------------------------------------
        # Final.
        # -------------------------------------------------------------

        banner(
            "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
        )

        kv(
            "Runtime Acquisition Rows",
            len(rows)
        )

        kv(
            "Runtime Validation Rows",
            len(results)
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
            "EXACT validate_row(row, columns) CALL "
            "RESOLVED FROM trace_real_validation()"
        )

        passed(
            "REAL validate_row() RESOLVED THROUGH "
            "PRODUCTION IMPORT BINDING"
        )

        passed(
            "REAL validate_row() RESOLVED FROM "
            "IMPORTED SOURCE AST"
        )

        passed(
            "ALL 987 CONTRACT ROWS VALIDATED"
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
            "RUNTIME ACQUISITION + EXACT PRODUCTION "
            "VALIDATOR EXECUTION VERIFIED"
        )

        print()
        print(
            "Next frontier:"
        )

        print(
            "ELIGIBLE / REJECTED / REASON analysis "
            "must use the REAL status/flags produced above."
        )

    finally:

        conn.close()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        banner(
            "FINAL STATUS           : FAIL"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()

        traceback.print_exc()

        sys.exit(1)