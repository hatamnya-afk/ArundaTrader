# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.4
====================================================================================================

PURPOSE
-------
Resolve the REAL production validate_row() binding from the AST of
market_technical_validation_engine_v0.4.1.py and execute that exact
validator against the REAL TECHNICAL_v0.5 contract rows acquired through
the production acquire_real_rows() function.

STRICT MODE
-----------
READ ONLY
FAIL CLOSED
NO PRODUCTION MODULE IMPORT
NO PRODUCTION main()
NO DATABASE WRITE
NO SYNTHETIC DATA
NO INFERENCE OF VALIDATOR IDENTITY
NO HARD-CODED VALIDATOR MODULE
NO HARD-CODED VALIDATOR LOCATION

The validator must be proven through AST resolution.

====================================================================================================
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
from types import ModuleType


# ================================================================================================
# CONFIGURATION
# ================================================================================================

PRODUCTION_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

TARGET_TABLE = "market_technical"

TARGET_ACQUIRE_FUNCTION = "acquire_real_rows"
TARGET_TRACE_FUNCTION = "trace_real_validation"

VALIDATOR_SYMBOL = "validate_row"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

EXPECTED_TOTAL_ROWS = (
    EXPECTED_CONTRACT_ROWS +
    EXPECTED_MUSEUM_ROWS
)

DB_READ_URI = (
    "file:"
    + str(DATABASE_FILE).replace("\\", "/")
    + "?mode=ro"
)


# ================================================================================================
# OUTPUT
# ================================================================================================

WIDTH = 100


def banner(title: str) -> None:
    print()
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def section(title: str) -> None:
    print()
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def kv(key: str, value) -> None:
    print(f"{key:<55}: {value}")


def passed(message: str) -> None:
    print(f"[PASS] {message}")


def failed(message: str) -> None:
    raise RuntimeError(message)


# ================================================================================================
# HASHING
# ================================================================================================

def sha256_file(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b""
        ):

            digest.update(chunk)

    return digest.hexdigest()


# ================================================================================================
# SOURCE
# ================================================================================================

def read_source(path: Path) -> str:

    if not path.exists():
        failed(
            f"Production file does not exist: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


def parse_source(source: str) -> ast.Module:

    try:

        return ast.parse(
            source,
            filename=str(PRODUCTION_FILE)
        )

    except SyntaxError as exc:

        failed(
            "Production source AST parse failed: "
            f"{exc}"
        )


# ================================================================================================
# AST FUNCTION DISCOVERY
# ================================================================================================

def top_level_functions(
    tree: ast.Module
):

    result = {}

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            result.setdefault(
                node.name,
                []
            ).append(node)

    return result


def resolve_unique_function(
    tree: ast.Module,
    name: str
):

    functions = top_level_functions(tree)

    matches = functions.get(
        name,
        []
    )

    if len(matches) == 0:

        failed(
            f"Production function not found: {name}"
        )

    if len(matches) > 1:

        failed(
            f"Ambiguous production function: {name} "
            f"count={len(matches)}"
        )

    return matches[0]


# ================================================================================================
# AST SEMANTIC HASH
# ================================================================================================

def semantic_hash(node: ast.AST) -> str:

    normalized = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# ================================================================================================
# AST SOURCE PRINT
# ================================================================================================

def source_segment(
    source: str,
    node: ast.AST
) -> str:

    segment = ast.get_source_segment(
        source,
        node
    )

    if segment is None:
        failed(
            "Unable to recover exact source segment."
        )

    return segment


def print_function_source(
    source: str,
    node: ast.AST
) -> None:

    start = getattr(
        node,
        "lineno",
        None
    )

    end = getattr(
        node,
        "end_lineno",
        None
    )

    kv(
        "Start Line",
        start
    )

    kv(
        "End Line",
        end
    )

    kv(
        "Semantic SHA256",
        semantic_hash(node)
    )

    print()

    for index, line in enumerate(
        source_segment(
            source,
            node
        ).splitlines(),
        start or 1
    ):

        print(
            f"{index:>5}: {line}"
        )


# ================================================================================================
# TRACE VALIDATOR CALL DISCOVERY
# ================================================================================================

def find_validator_calls(
    trace_node: ast.FunctionDef
):

    calls = []

    for node in ast.walk(trace_node):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        func = node.func

        if not isinstance(
            func,
            ast.Name
        ):
            continue

        if func.id != VALIDATOR_SYMBOL:
            continue

        calls.append(node)

    return calls


def resolve_real_validation_call(
    trace_node: ast.FunctionDef
):

    calls = find_validator_calls(
        trace_node
    )

    if len(calls) == 0:

        failed(
            "trace_real_validation() contains no "
            "validate_row(...) call."
        )

    if len(calls) != 1:

        failed(
            "trace_real_validation() contains "
            f"{len(calls)} validate_row() calls; "
            "validator identity is ambiguous."
        )

    call = calls[0]

    if len(call.args) != 2:

        failed(
            "REAL validation call does not contain exactly "
            "two positional arguments."
        )

    first = call.args[0]
    second = call.args[1]

    if not (
        isinstance(first, ast.Name)
        and first.id == "row"
    ):

        failed(
            "REAL validation call first argument is not row."
        )

    if not (
        isinstance(second, ast.Name)
        and second.id == "columns"
    ):

        failed(
            "REAL validation call second argument is not columns."
        )

    if call.keywords:

        failed(
            "REAL validation call contains keyword arguments."
        )

    return call


# ================================================================================================
# IMPORT ANALYSIS
# ================================================================================================

def module_name_from_import(
    node: ast.AST,
    symbol: str
):

    if isinstance(
        node,
        ast.Import
    ):

        for alias in node.names:

            visible_name = (
                alias.asname
                if alias.asname
                else alias.name.split(".")[0]
            )

            if visible_name == symbol:

                return {
                    "kind": "module",
                    "module": alias.name,
                    "name": None,
                }

    if isinstance(
        node,
        ast.ImportFrom
    ):

        if node.module is None:
            return None

        for alias in node.names:

            visible_name = (
                alias.asname
                if alias.asname
                else alias.name
            )

            if visible_name != symbol:
                continue

            if alias.name == "*":

                failed(
                    f"Wildcard import prevents safe resolution of "
                    f"{symbol}."
                )

            return {
                "kind": "from",
                "module": node.module,
                "name": alias.name,
                "level": node.level,
            }

    return None


def discover_validator_import(
    tree: ast.Module
):

    matches = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom
            )
        ):

            result = module_name_from_import(
                node,
                VALIDATOR_SYMBOL
            )

            if result is not None:
                matches.append(
                    result
                )

    return matches


# ================================================================================================
# LOCAL ASSIGNMENT ANALYSIS
# ================================================================================================

def find_top_level_assignments(
    tree: ast.Module,
    symbol: str
):

    matches = []

    for node in tree.body:

        targets = []

        if isinstance(
            node,
            ast.Assign
        ):

            targets = node.targets

        elif isinstance(
            node,
            ast.AnnAssign
        ):

            targets = [node.target]

        elif isinstance(
            node,
            ast.NamedExpr
        ):

            targets = [node.target]

        for target in targets:

            if (
                isinstance(target, ast.Name)
                and target.id == symbol
            ):

                matches.append(
                    node
                )

    return matches


# ================================================================================================
# VALIDATOR BINDING RESOLUTION
# ================================================================================================

def resolve_validator_binding(
    production_tree: ast.Module
):

    section(
        "REAL PRODUCTION VALIDATOR BINDING RESOLUTION"
    )

    local_functions = top_level_functions(
        production_tree
    ).get(
        VALIDATOR_SYMBOL,
        []
    )

    local_assignments = find_top_level_assignments(
        production_tree,
        VALIDATOR_SYMBOL
    )

    imports = discover_validator_import(
        production_tree
    )

    kv(
        "Top-Level validate_row() functions",
        len(local_functions)
    )

    kv(
        "Top-Level validate_row assignments",
        len(local_assignments)
    )

    kv(
        "Imports binding validate_row",
        len(imports)
    )

    candidates = (
        len(local_functions)
        + len(local_assignments)
        + len(imports)
    )

    if candidates == 0:

        failed(
            "No binding for validate_row found in production AST."
        )

    if candidates > 1:

        failed(
            "Multiple possible validate_row bindings detected. "
            "Refusing unsafe inference."
        )

    if local_functions:

        passed(
            "validate_row resolved as a top-level production function."
        )

        return {
            "kind": "local_function",
            "node": local_functions[0],
            "module": PRODUCTION_FILE,
            "symbol": VALIDATOR_SYMBOL,
        }

    if local_assignments:

        failed(
            "validate_row is assignment-bound rather than a direct "
            "function definition. v0.4 refuses unsafe callable inference."
        )

    if imports:

        binding = imports[0]

        passed(
            "validate_row resolved through production import AST."
        )

        return {
            "kind": "import",
            **binding,
        }

    failed(
        "Validator binding resolution reached impossible state."
    )


# ================================================================================================
# MODULE FILE RESOLUTION
# ================================================================================================

def resolve_relative_module(
    module_name: str,
    level: int,
    production_file: Path
):

    if level <= 0:

        return None

    base = production_file.parent

    for _ in range(
        level - 1
    ):

        base = base.parent

    if module_name:

        parts = module_name.split(".")

    else:

        parts = []

    candidate = base.joinpath(
        *parts
    )

    py_file = candidate.with_suffix(
        ".py"
    )

    if py_file.exists():
        return py_file

    init_file = candidate / "__init__.py"

    if init_file.exists():
        return init_file

    return None


def resolve_absolute_module(
    module_name: str,
    production_file: Path
):

    parts = module_name.split(".")

    roots = [
        production_file.parent,
        Path.cwd(),
    ]

    candidates = []

    for root in roots:

        candidate = root.joinpath(
            *parts
        )

        candidates.append(
            candidate.with_suffix(".py")
        )

        candidates.append(
            candidate / "__init__.py"
        )

    existing = [
        p
        for p in candidates
        if p.exists()
    ]

    unique = []

    seen = set()

    for path in existing:

        resolved = path.resolve()

        if resolved not in seen:

            seen.add(
                resolved
            )

            unique.append(
                path
            )

    if len(unique) == 0:

        return None

    if len(unique) > 1:

        failed(
            "Multiple filesystem candidates found for module "
            f"{module_name}: {unique}"
        )

    return unique[0]


def resolve_imported_validator_file(
    binding: dict
):

    module_name = binding["module"]
    level = binding.get(
        "level",
        0
    )

    if level:

        path = resolve_relative_module(
            module_name,
            level,
            PRODUCTION_FILE
        )

    else:

        path = resolve_absolute_module(
            module_name,
            PRODUCTION_FILE
        )

    if path is None:

        failed(
            "Unable to resolve imported validator module "
            f"'{module_name}' to a local source file."
        )

    return path


# ================================================================================================
# VALIDATOR SOURCE DISCOVERY
# ================================================================================================

def resolve_validator_from_module(
    path: Path,
    symbol: str
):

    source = read_source(
        path
    )

    tree = parse_source(
        source
    )

    functions = top_level_functions(
        tree
    ).get(
        symbol,
        []
    )

    if len(functions) == 0:

        failed(
            f"Imported validator source does not define "
            f"top-level {symbol}(): {path}"
        )

    if len(functions) != 1:

        failed(
            f"Imported validator source contains "
            f"{len(functions)} definitions of {symbol}(): {path}"
        )

    node = functions[0]

    return {
        "path": path,
        "source": source,
        "tree": tree,
        "node": node,
    }


# ================================================================================================
# SAFE FUNCTION COMPILATION
# ================================================================================================

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
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def compile_single_function(
    source: str,
    node: ast.FunctionDef,
    extra_namespace=None,
    filename="<production-function>"
):

    function_source = source_segment(
        source,
        node
    )

    isolated_tree = ast.parse(
        function_source,
        filename=filename
    )

    namespace = {
        "__builtins__": SAFE_BUILTINS
    }

    if extra_namespace:
        namespace.update(
            extra_namespace
        )

    code = compile(
        isolated_tree,
        filename=filename,
        mode="exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    function = namespace.get(
        node.name
    )

    if not callable(function):

        failed(
            f"Compiled object {node.name} is not callable."
        )

    return function


# ================================================================================================
# CONSTANT EXTRACTION
# ================================================================================================

def extract_simple_constants(
    tree: ast.Module
):

    namespace = {}

    for node in tree.body:

        if not isinstance(
            node,
            ast.Assign
        ):
            continue

        if len(node.targets) != 1:
            continue

        target = node.targets[0]

        if not isinstance(
            target,
            ast.Name
        ):
            continue

        try:

            value = ast.literal_eval(
                node.value
            )

        except Exception:

            continue

        namespace[target.id] = value

    return namespace


# ================================================================================================
# VALIDATOR DEPENDENCY EXTRACTION
# ================================================================================================

def collect_global_names(
    function_node: ast.FunctionDef
):

    arguments = {
        arg.arg
        for arg in (
            function_node.args.posonlyargs
            + function_node.args.args
            + function_node.args.kwonlyargs
        )
    }

    if function_node.args.vararg:
        arguments.add(
            function_node.args.vararg.arg
        )

    if function_node.args.kwarg:
        arguments.add(
            function_node.args.kwarg.arg
        )

    local_names = set(
        arguments
    )

    globals_used = set()

    for node in ast.walk(
        function_node
    ):

        if isinstance(
            node,
            ast.Name
        ):

            if isinstance(
                node.ctx,
                ast.Load
            ):

                if node.id not in local_names:

                    globals_used.add(
                        node.id
                    )

            elif isinstance(
                node.ctx,
                (
                    ast.Store,
                    ast.Del
                )
            ):

                local_names.add(
                    node.id
                )

    return globals_used


def build_validator_namespace(
    validator_source: str,
    validator_tree: ast.Module,
    validator_node: ast.FunctionDef
):

    namespace = {}

    constants = extract_simple_constants(
        validator_tree
    )

    namespace.update(
        constants
    )

    globals_needed = collect_global_names(
        validator_node
    )

    missing = []

    for name in sorted(
        globals_needed
    ):

        if name in namespace:
            continue

        if name in SAFE_BUILTINS:
            continue

        missing.append(
            name
        )

    if missing:

        failed(
            "Validator has unresolved global dependencies: "
            + ", ".join(missing)
        )

    return namespace


# ================================================================================================
# ACQUIRE FUNCTION NAMESPACE
# ================================================================================================

def build_acquire_namespace(
    production_tree: ast.Module
):

    namespace = extract_simple_constants(
        production_tree
    )

    namespace.update(
        {
            "TRACE_LIMIT": EXPECTED_CONTRACT_ROWS,
            "TARGET_TABLE": TARGET_TABLE,
            "CONTRACT_TECHNICAL_VERSION":
                CONTRACT_TECHNICAL_VERSION,
            "CONTRACT_ENGINE_VERSION":
                CONTRACT_ENGINE_VERSION,
            "CONTRACT_SOURCE":
                CONTRACT_SOURCE,
        }
    )

    namespace.update(
        {
            "banner": banner,
            "kv": kv,
        }
    )

    return namespace


# ================================================================================================
# ACQUIRE FUNCTION
# ================================================================================================

def compile_acquire_function(
    source: str,
    node: ast.FunctionDef,
    production_tree: ast.Module
):

    namespace = build_acquire_namespace(
        production_tree
    )

    return compile_single_function(
        source,
        node,
        namespace,
        filename=str(PRODUCTION_FILE)
    )


# ================================================================================================
# SQLITE
# ================================================================================================

def open_read_only_database():

    connection = sqlite3.connect(
        DB_READ_URI,
        uri=True
    )

    connection.row_factory = sqlite3.Row

    query_only = connection.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if query_only != 1:

        connection.close()

        failed(
            "SQLite PRAGMA query_only is not 1."
        )

    return connection


def database_counts(
    conn: sqlite3.Connection
):

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


def verify_database_preflight(
    conn
):

    section(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    counts = database_counts(
        conn
    )

    kv(
        "SQLite query_only",
        query_only
    )

    for key in (
        "total",
        "contract",
        "museum",
        "min_id",
        "max_id",
        "distinct_ids",
    ):

        kv(
            key,
            counts[key]
        )

    if query_only != 1:
        failed(
            "Database query_only != 1"
        )

    if counts["total"] != EXPECTED_TOTAL_ROWS:
        failed(
            f"Database total expected {EXPECTED_TOTAL_ROWS}, "
            f"got {counts['total']}"
        )

    if counts["contract"] != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Contract population expected "
            f"{EXPECTED_CONTRACT_ROWS}, "
            f"got {counts['contract']}"
        )

    if counts["museum"] != EXPECTED_MUSEUM_ROWS:
        failed(
            f"Museum population expected "
            f"{EXPECTED_MUSEUM_ROWS}, "
            f"got {counts['museum']}"
        )

    if counts["min_id"] != 5923:
        failed(
            f"Contract MIN ID expected 5923, "
            f"got {counts['min_id']}"
        )

    if counts["max_id"] != 6909:
        failed(
            f"Contract MAX ID expected 6909, "
            f"got {counts['max_id']}"
        )

    if counts["distinct_ids"] != EXPECTED_CONTRACT_ROWS:
        failed(
            "Contract IDs are not distinct."
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


# ================================================================================================
# ACQUIRE SQL CONTRACT
# ================================================================================================

def normalize_sql(
    sql: str
):

    return re.sub(
        r"\s+",
        " ",
        sql.lower()
    ).strip()


def reconstruct_acquire_sql(
    node: ast.FunctionDef
):

    sql_fragments = []

    for child in ast.walk(
        node
    ):

        if isinstance(
            child,
            ast.JoinedStr
        ):

            values = []

            for part in child.values:

                if isinstance(
                    part,
                    ast.Constant
                ) and isinstance(
                    part.value,
                    str
                ):

                    values.append(
                        part.value
                    )

                elif isinstance(
                    part,
                    ast.FormattedValue
                ):

                    if (
                        isinstance(
                            part.value,
                            ast.Name
                        )
                        and part.value.id == TARGET_TABLE
                    ):

                        values.append(
                            TARGET_TABLE
                        )

                    else:

                        values.append(
                            "?"
                        )

            sql_fragments.append(
                "".join(values)
            )

        elif isinstance(
            child,
            ast.Constant
        ):

            if isinstance(
                child.value,
                str
            ):

                value = child.value

                if "SELECT" in value.upper():

                    sql_fragments.append(
                        value
                    )

    if not sql_fragments:

        failed(
            "No SQL literal found in acquire_real_rows()."
        )

    normalized = normalize_sql(
        " ".join(sql_fragments)
    )

    expected = (
        'select * '
        'from "market_technical" '
        'where technical_version = ? '
        'and engine_version = ? '
        'and source = ? '
        'order by id desc '
        'limit ?'
    )

    if expected not in normalized:

        print()
        print(
            "RECONSTRUCTED SQL:"
        )
        print(
            normalized
        )

        failed(
            "Expected TECHNICAL_v0.5 contract SQL "
            "not found in reconstructed SQL."
        )

    print()
    print(
        "RECONSTRUCTED SQL:"
    )
    print(
        normalized
    )

    for fragment in (
        "select *",
        'from "market_technical"',
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ):

        if fragment not in normalized:

            failed(
                f"Expected SQL fragment missing: {fragment}"
            )

        passed(
            f"SQL fragment: {fragment}"
        )

    if re.search(
        r"\b(insert|update|delete|replace|alter|drop|create)\b",
        normalized,
        re.IGNORECASE
    ):

        failed(
            "Write SQL detected in acquire_real_rows()."
        )

    passed(
        "Contract SQL reconstructed correctly"
    )


# ================================================================================================
# RUNTIME ACQUISITION
# ================================================================================================

def execute_acquire(
    acquire_function,
    conn
):

    section(
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
            f"acquire_real_rows() returned "
            f"{len(rows)} rows; expected "
            f"{EXPECTED_CONTRACT_ROWS}"
        )

    passed(
        "acquire_real_rows() returned exactly 987 rows"
    )

    return rows, columns


# ================================================================================================
# ROW CONTRACT
# ================================================================================================

def verify_runtime_rows(
    rows
):

    section(
        "RUNTIME CONTRACT RESULT"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime row count mismatch."
        )

    ids = [
        row["id"]
        for row in rows
    ]

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime IDs are not distinct."
        )

    if min(ids) != 5923:
        failed(
            "Runtime minimum ID mismatch."
        )

    if max(ids) != 6909:
        failed(
            "Runtime maximum ID mismatch."
        )

    for row in rows:

        if row["technical_version"] != CONTRACT_TECHNICAL_VERSION:
            failed(
                "Runtime technical_version contract violation."
            )

        if row["engine_version"] != CONTRACT_ENGINE_VERSION:
            failed(
                "Runtime engine_version contract violation."
            )

        if row["source"] != CONTRACT_SOURCE:
            failed(
                "Runtime source contract violation."
            )

    ordered = [
        row["id"]
        for row in rows
    ]

    if ordered != sorted(
        ordered,
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


# ================================================================================================
# VALIDATOR EXECUTION
# ================================================================================================

def execute_real_validator(
    validator_function,
    rows,
    columns
):

    section(
        "REAL validate_row(row, columns) RUNTIME EXECUTION"
    )

    signature = inspect.signature(
        validator_function
    )

    kv(
        "Resolved Function",
        validator_function.__name__
    )

    kv(
        "Signature",
        signature
    )

    parameters = list(
        signature.parameters.values()
    )

    if len(parameters) != 2:

        failed(
            "Resolved validate_row() does not expose "
            "exactly two parameters."
        )

    for expected, actual in zip(
        (
            "row",
            "columns",
        ),
        parameters
    ):

        if actual.name != expected:

            failed(
                "Resolved validator parameter mismatch: "
                f"expected {expected}, got {actual.name}"
            )

    passed(
        "Resolved validator signature = (row, columns)"
    )

    results = []

    errors = []

    for index, row in enumerate(
        rows,
        start=1
    ):

        try:

            result = validator_function(
                row,
                columns
            )

            results.append(
                {
                    "index": index,
                    "id": row["id"],
                    "symbol": (
                        row["symbol"]
                        if "symbol" in row.keys()
                        else None
                    ),
                    "result": result,
                }
            )

        except Exception as exc:

            errors.append(
                {
                    "index": index,
                    "id": (
                        row["id"]
                        if "id" in row.keys()
                        else None
                    ),
                    "symbol": (
                        row["symbol"]
                        if "symbol" in row.keys()
                        else None
                    ),
                    "exception": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    kv(
        "Rows Executed",
        len(results)
    )

    kv(
        "Execution Errors",
        len(errors)
    )

    if errors:

        first = errors[0]

        print()
        print(
            "FIRST VALIDATION ERROR:"
        )

        print(
            f"Row       : {first['index']}"
        )

        print(
            f"ID        : {first['id']}"
        )

        print(
            f"Symbol    : {first['symbol']}"
        )

        print(
            f"Exception : {first['exception']}"
        )

        print(
            first["traceback"]
        )

        failed(
            "REAL validate_row(row, columns) execution "
            f"failed for {len(errors)} rows."
        )

    if len(results) != EXPECTED_CONTRACT_ROWS:

        failed(
            "Not all 987 contract rows were validated."
        )

    passed(
        "REAL validate_row(row, columns) executed against all 987 rows"
    )

    return results


# ================================================================================================
# RESULT SHAPE
# ================================================================================================

def verify_validator_return_shape(
    results
):

    section(
        "REAL VALIDATOR RETURN SHAPE"
    )

    shape_counter = Counter()

    for item in results:

        result = item["result"]

        if not isinstance(
            result,
            tuple
        ):

            failed(
                f"Validator return at row "
                f"{item['index']} is not tuple: "
                f"{result!r}"
            )

        shape_counter[
            len(result)
        ] += 1

    kv(
        "Return tuple shapes",
        dict(shape_counter)
    )

    if set(
        shape_counter.keys()
    ) != {3}:

        failed(
            "Validator does not consistently return "
            "a 3-element tuple."
        )

    if shape_counter[3] != EXPECTED_CONTRACT_ROWS:

        failed(
            "Not all validator results are 3-tuples."
        )

    passed(
        "All 987 validator results are 3-tuples"
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "Business classification analysis "
        "(eligible/rejected/reason) is intentionally "
        "NOT performed in v0.4."
    )


# ================================================================================================
# INTEGRITY
# ================================================================================================

def verify_integrity_after(
    production_hash_before,
    database_hash_before,
    database_size_before
):

    section(
        "PRODUCTION / DATABASE INTEGRITY AFTER"
    )

    production_hash_after = sha256_file(
        PRODUCTION_FILE
    )

    database_hash_after = sha256_file(
        DATABASE_FILE
    )

    database_size_after = (
        DATABASE_FILE.stat().st_size
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
            "Production source changed during runtime verification."
        )

    if database_hash_before != database_hash_after:

        failed(
            "Database SHA256 changed during runtime verification."
        )

    if database_size_before != database_size_after:

        failed(
            "Database size changed during runtime verification."
        )

    passed(
        "Production source unchanged"
    )

    passed(
        "Database unchanged"
    )


# ================================================================================================
# MAIN
# ================================================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.4"
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
        TARGET_ACQUIRE_FUNCTION
    )

    kv(
        "Trace Function",
        TARGET_TRACE_FUNCTION
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
        "will be executed."
    )
    print(
        "Database access is READ ONLY."
    )
    print(
        "No database write is permitted."
    )

    # --------------------------------------------------------------------------------------------
    # INTEGRITY BEFORE
    # --------------------------------------------------------------------------------------------

    production_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    database_hash_before = sha256_file(
        DATABASE_FILE
    )

    database_size_before = (
        DATABASE_FILE.stat().st_size
    )

    section(
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

    # --------------------------------------------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------------------------------------------

    source = read_source(
        PRODUCTION_FILE
    )

    tree = parse_source(
        source
    )

    # --------------------------------------------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------------------------------------------

    conn = open_read_only_database()

    try:

        verify_database_preflight(
            conn
        )

        # ----------------------------------------------------------------------------------------
        # AST DISCOVERY
        # ----------------------------------------------------------------------------------------

        section(
            "PRODUCTION AST DISCOVERY"
        )

        acquire_node = resolve_unique_function(
            tree,
            TARGET_ACQUIRE_FUNCTION
        )

        trace_node = resolve_unique_function(
            tree,
            TARGET_TRACE_FUNCTION
        )

        kv(
            "acquire_real_rows semantic SHA256",
            semantic_hash(acquire_node)
        )

        kv(
            "trace_real_validation semantic SHA256",
            semantic_hash(trace_node)
        )

        section(
            "REAL PRODUCTION acquire_real_rows()"
        )

        print_function_source(
            source,
            acquire_node
        )

        section(
            "REAL PRODUCTION trace_real_validation()"
        )

        print_function_source(
            source,
            trace_node
        )

        # ----------------------------------------------------------------------------------------
        # TRACE CALL
        # ----------------------------------------------------------------------------------------

        section(
            "REAL VALIDATION CALL DISCOVERY"
        )

        validation_call = resolve_real_validation_call(
            trace_node
        )

        kv(
            "REAL Validation Call",
            "validate_row(row, columns)"
        )

        passed(
            "Exact validate_row(row, columns) call discovered "
            "inside trace_real_validation()"
        )

        # ----------------------------------------------------------------------------------------
        # ACQUIRE SQL
        # ----------------------------------------------------------------------------------------

        section(
            "PRODUCTION acquire_real_rows() CONTRACT"
        )

        reconstruct_acquire_sql(
            acquire_node
        )

        # ----------------------------------------------------------------------------------------
        # VALIDATOR BINDING
        # ----------------------------------------------------------------------------------------

        binding = resolve_validator_binding(
            tree
        )

        validator_path = None
        validator_source = source
        validator_tree = tree
        validator_node = None

        if binding["kind"] == "local_function":

            validator_node = binding["node"]

            passed(
                "Validator source = production file"
            )

        elif binding["kind"] == "import":

            validator_path = resolve_imported_validator_file(
                binding
            )

            kv(
                "Resolved Validator Module",
                validator_path
            )

            if validator_path.resolve() == PRODUCTION_FILE.resolve():

                failed(
                    "Validator import resolves back to production file "
                    "but binding was not locally resolved."
                )

            validator_info = resolve_validator_from_module(
                validator_path,
                binding["name"]
            )

            validator_source = validator_info["source"]
            validator_tree = validator_info["tree"]
            validator_node = validator_info["node"]

            passed(
                "Imported validator source AST resolved"
            )

        else:

            failed(
                "Unsupported validator binding kind."
            )

        # ----------------------------------------------------------------------------------------
        # VALIDATOR SOURCE
        # ----------------------------------------------------------------------------------------

        section(
            "REAL PRODUCTION VALIDATOR SOURCE"
        )

        kv(
            "Validator Source File",
            (
                PRODUCTION_FILE
                if validator_path is None
                else validator_path
            )
        )

        kv(
            "Validator Function",
            validator_node.name
        )

        kv(
            "Validator Semantic SHA256",
            semantic_hash(validator_node)
        )

        print()

        print(
            source_segment(
                validator_source,
                validator_node
            )
        )

        # ----------------------------------------------------------------------------------------
        # COMPILE VALIDATOR
        # ----------------------------------------------------------------------------------------

        section(
            "EXACT PRODUCTION VALIDATOR COMPILATION"
        )

        validator_namespace = build_validator_namespace(
            validator_source,
            validator_tree,
            validator_node
        )

        validator_function = compile_single_function(
            validator_source,
            validator_node,
            validator_namespace,
            filename=(
                str(PRODUCTION_FILE)
                if validator_path is None
                else str(validator_path)
            )
        )

        passed(
            "Exact production validate_row() compiled successfully"
        )

        # ----------------------------------------------------------------------------------------
        # COMPILE ACQUIRE
        # ----------------------------------------------------------------------------------------

        section(
            "EXACT PRODUCTION acquire_real_rows() COMPILATION"
        )

        acquire_function = compile_acquire_function(
            source,
            acquire_node,
            tree
        )

        passed(
            "Exact production acquire_real_rows() compiled successfully"
        )

        # ----------------------------------------------------------------------------------------
        # ACQUIRE
        # ----------------------------------------------------------------------------------------

        rows, columns = execute_acquire(
            acquire_function,
            conn
        )

        verify_runtime_rows(
            rows
        )

        # ----------------------------------------------------------------------------------------
        # VALIDATOR
        # ----------------------------------------------------------------------------------------

        results = execute_real_validator(
            validator_function,
            rows,
            columns
        )

        verify_validator_return_shape(
            results
        )

    finally:

        conn.close()

    # --------------------------------------------------------------------------------------------
    # INTEGRITY AFTER
    # --------------------------------------------------------------------------------------------

    verify_integrity_after(
        production_hash_before,
        database_hash_before,
        database_size_before
    )

    # --------------------------------------------------------------------------------------------
    # FINAL
    # --------------------------------------------------------------------------------------------

    section(
        "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
    )

    kv(
        "Runtime Rows",
        EXPECTED_CONTRACT_ROWS
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
        "trace_real_validation() AST CALL RESOLVED"
    )

    passed(
        "REAL validate_row(row, columns) RESOLVED"
    )

    passed(
        "REAL validate_row(row, columns) COMPILED"
    )

    passed(
        "EXACT acquire_real_rows() EXECUTED"
    )

    passed(
        "987 REAL Contract rows acquired"
    )

    passed(
        "REAL validator executed against all 987 rows"
    )

    passed(
        "ALL validator results have expected 3-tuple shape"
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
        "REAL validate_row(row, columns)"
    )

    print(
        "RUNTIME VERIFIED AGAINST 987 REAL CONTRACT ROWS"
    )

    print()
    print(
        "NEXT STAGE:"
    )

    print(
        "Analyze actual validator outputs for "
        "eligible / rejected / reason."
    )

    print()
    print(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.4 COMPLETE"
    )


if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print("=" * WIDTH)
        print("FINAL STATUS           : FAIL")
        print("=" * WIDTH)
        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()

        traceback.print_exc()

        sys.exit(1)