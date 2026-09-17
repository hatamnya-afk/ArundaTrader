
# -*- coding: utf-8 -*-

"""
================================================================================
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.8
================================================================================

PURPOSE
-------
READ-ONLY production runtime verification of the real TECHNICAL_v0.5 contract.

Execution chain:

    acquire_real_rows()
        |
        v
    987 REAL persisted market_technical rows
        |
        v
    trace_real_validation()
        |
        v
    exact call:
        validate_row(row, columns)
        |
        v
    resolve REAL production import binding
        |
        v
    locate actual production validator source
        |
        v
    AST-resolve exact validate_row()
        |
        v
    execute exact production validate_row(row, columns)
        |
        v
    PASS / FAIL

STRICT SAFETY
-------------
- Production main() is NEVER executed.
- Production modules are NEVER imported.
- Database is opened read-only.
- PRAGMA query_only must equal 1.
- No database write is permitted.
- Only AST-extracted production functions are compiled/executed.
- No synthetic rows.
- No DB mutation.
- No production source mutation.
- No SQL write operation is executed.

IMPORTANT
---------
This version intentionally does NOT attempt to reconstruct f-string SQL
by substituting AST placeholders. SQL safety is verified structurally
from the actual AST.

The validator is NOT assumed to exist in the acquisition file.
The trace function is used as the authoritative production call boundary.
Its import bindings are resolved through AST.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

PRODUCTION_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

TRACE_FUNCTION = "trace_real_validation"
ACQUIRE_FUNCTION = "acquire_real_rows"
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

CONTRACT_MIN_ID = 5923
CONTRACT_MAX_ID = 6909

TARGET_TABLE = "market_technical"

# Runtime trace must cover all real contract rows.
TRACE_LIMIT = EXPECTED_CONTRACT_ROWS


# =============================================================================
# OUTPUT
# =============================================================================

WIDTH = 100


def banner(title: str) -> None:
    print()
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def kv(key: str, value: Any) -> None:
    print(f"{key:<55} {value}")


def passed(message: str) -> None:
    print(f"[PASS] {message}")


def failed(message: str) -> None:
    raise RuntimeError(message)


def safe(value: Any) -> str:
    try:
        return repr(value)
    except Exception:
        return "<UNPRINTABLE>"


# =============================================================================
# HASHING
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# AST SOURCE HELPERS
# =============================================================================

def load_source(path: Path) -> str:
    if not path.exists():
        failed(f"Production source file not found: {path}")

    if not path.is_file():
        failed(f"Production source path is not a file: {path}")

    return path.read_text(
        encoding="utf-8",
        errors="strict",
    )


def parse_source(path: Path) -> tuple[str, ast.Module]:
    source = load_source(path)

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        failed(
            f"Cannot parse production source {path}: "
            f"{exc}"
        )

    return source, tree


def semantic_sha256(node: ast.AST) -> str:
    text = ast.unparse(node)

    normalized = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def find_unique_function(
    tree: ast.AST,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:

    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == name
    ]

    if not matches:
        failed(
            f"Production function not found: {name}"
        )

    if len(matches) != 1:
        failed(
            f"Expected exactly one production function "
            f"{name}, found {len(matches)}"
        )

    return matches[0]


# =============================================================================
# FUNCTION DISPLAY
# =============================================================================

def print_function_source(
    node: ast.AST,
    source: str,
    title: str,
) -> None:

    banner(title)

    start = getattr(
        node,
        "lineno",
        None,
    )

    end = getattr(
        node,
        "end_lineno",
        None,
    )

    if start is None or end is None:
        print(ast.unparse(node))
        return

    lines = source.splitlines()

    for number in range(
        start,
        end + 1,
    ):
        print(
            f"{number:5d}: {lines[number - 1]}"
        )


# =============================================================================
# ACQUIRE AST SQL SAFETY
# =============================================================================

WRITE_SQL = {
    "insert",
    "update",
    "delete",
    "alter",
    "create",
    "drop",
    "replace",
    "vacuum",
    "reindex",
    "attach",
    "detach",
    "pragma",
}


def collect_execute_sql_fragments(
    node: ast.AST,
) -> list[str]:

    fragments: list[str] = []

    for call in ast.walk(node):

        if not isinstance(call, ast.Call):
            continue

        func = call.func

        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "execute"
        ):
            continue

        if not call.args:
            continue

        sql_node = call.args[0]

        try:
            text = ast.unparse(sql_node)
        except Exception:
            continue

        fragments.append(text)

    return fragments


def normalize_sql_literal(text: str) -> str:
    """
    Normalize AST representation without pretending that f-string
    expressions have already been evaluated.

    This function deliberately preserves placeholders.
    """

    text = text.replace(
        "\\n",
        " ",
    )

    text = text.replace(
        "\\t",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip().lower()


def sql_structure_from_ast(
    acquire_node: ast.AST,
) -> dict[str, Any]:

    execute_calls = []

    for call in ast.walk(acquire_node):

        if not isinstance(call, ast.Call):
            continue

        if not (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "execute"
        ):
            continue

        execute_calls.append(call)

    if len(execute_calls) != 1:
        failed(
            "Expected exactly one conn.execute() "
            f"in {ACQUIRE_FUNCTION}; found "
            f"{len(execute_calls)}"
        )

    call = execute_calls[0]

    if not call.args:
        failed(
            "conn.execute() has no SQL argument"
        )

    sql_node = call.args[0]

    if not isinstance(
        sql_node,
        ast.JoinedStr,
    ):
        failed(
            "Production acquire SQL is expected "
            "to be an f-string JoinedStr"
        )

    literal_parts: list[str] = []
    dynamic_names: list[str] = []

    for value in sql_node.values:

        if isinstance(
            value,
            ast.Constant,
        ):
            if isinstance(
                value.value,
                str,
            ):
                literal_parts.append(
                    value.value
                )

        elif isinstance(
            value,
            ast.FormattedValue,
        ):
            dynamic_names.append(
                ast.unparse(
                    value.value
                )
            )

    sql_literal = normalize_sql_literal(
        " ".join(literal_parts)
    )

    return {
        "sql_node": sql_node,
        "literal": sql_literal,
        "dynamic_names": dynamic_names,
        "call": call,
    }


def verify_acquire_sql_contract(
    acquire_node: ast.AST,
) -> None:

    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    structure = sql_structure_from_ast(
        acquire_node
    )

    literal = structure["literal"]
    dynamic_names = structure["dynamic_names"]

    print()
    print(
        "AST SQL LITERAL CONTENT:"
    )
    print(literal)

    print()
    print(
        "AST SQL DYNAMIC EXPRESSIONS:"
    )

    for name in dynamic_names:
        print(f"  {name}")

    required_literals = [
        "select *",
        "from",
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in required_literals:

        if fragment not in literal:
            failed(
                "Expected SQL contract fragment missing: "
                + fragment
            )

        passed(
            "SQL contract fragment: "
            + fragment
        )

    forbidden = [
        word
        for word in WRITE_SQL
        if re.search(
            rf"\b{re.escape(word)}\b",
            literal,
            flags=re.IGNORECASE,
        )
    ]

    if forbidden:
        failed(
            "Potential SQL write operation detected: "
            + ", ".join(sorted(forbidden))
        )

    # The table is represented dynamically through TARGET_TABLE.
    if "target_table" not in [
        name.lower()
        for name in dynamic_names
    ]:
        failed(
            "Production acquire SQL does not contain "
            "the expected TARGET_TABLE expression."
        )

    passed(
        "TARGET_TABLE expression preserved in AST"
    )

    passed(
        "No SQL write operation detected"
    )

    # Verify parameter tuple structurally.
    execute_call = structure["call"]

    if len(execute_call.args) < 2:
        failed(
            "Production conn.execute() does not provide "
            "the expected parameter tuple."
        )

    parameter_node = execute_call.args[1]

    if not isinstance(
        parameter_node,
        ast.Tuple,
    ):
        failed(
            "Production SQL parameter binding is not "
            "an AST tuple."
        )

    parameter_names = [
        ast.unparse(element)
        for element in parameter_node.elts
    ]

    expected_parameter_names = [
        "CONTRACT_TECHNICAL_VERSION",
        "CONTRACT_ENGINE_VERSION",
        "CONTRACT_SOURCE",
        "limit",
    ]

    if parameter_names != expected_parameter_names:
        failed(
            "Unexpected production SQL parameter binding.\n"
            f"Expected: {expected_parameter_names}\n"
            f"Actual:   {parameter_names}"
        )

    passed(
        "SQL parameter binding = "
        + repr(parameter_names)
    )


# =============================================================================
# READ-ONLY DATABASE
# =============================================================================

def open_read_only_database() -> sqlite3.Connection:

    if not DATABASE_FILE.exists():
        failed(
            f"Database not found: {DATABASE_FILE}"
        )

    uri = (
        "file:"
        + DATABASE_FILE.resolve().as_posix()
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    # IMPORTANT:
    # PRAGMA query_only is connection-local.
    # It must be enabled on THIS exact connection.
    conn.execute(
        "PRAGMA query_only = 1"
    )

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    kv(
        "SQLite query_only",
        value,
    )

    if value != 1:
        conn.close()

        failed(
            "SQLite PRAGMA query_only is not 1."
        )

    return conn


# =============================================================================
# DATABASE PREFLIGHT
# =============================================================================

def verify_database_preflight(
    conn: sqlite3.Connection,
) -> None:

    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    row = conn.execute(
        """
        SELECT
            COUNT(*)
        FROM market_technical
        """
    ).fetchone()

    total = int(row[0])

    contract = conn.execute(
        """
        SELECT
            COUNT(*)
        FROM market_technical
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

    min_id, max_id, distinct_ids = conn.execute(
        """
        SELECT
            MIN(id),
            MAX(id),
            COUNT(DISTINCT id)
        FROM market_technical
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        """,
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

    if total != EXPECTED_TOTAL_ROWS:
        failed(
            f"DATABASE TOTAL expected "
            f"{EXPECTED_TOTAL_ROWS}, got {total}"
        )

    passed(
        f"DATABASE TOTAL = {EXPECTED_TOTAL_ROWS}"
    )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            f"CONTRACT expected "
            f"{EXPECTED_CONTRACT_ROWS}, got {contract}"
        )

    passed(
        f"CONTRACT = {EXPECTED_CONTRACT_ROWS}"
    )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            f"MUSEUM expected "
            f"{EXPECTED_MUSEUM_ROWS}, got {museum}"
        )

    passed(
        f"MUSEUM = {EXPECTED_MUSEUM_ROWS}"
    )

    if (
        min_id != CONTRACT_MIN_ID
        or max_id != CONTRACT_MAX_ID
    ):
        failed(
            "CONTRACT ID RANGE mismatch: "
            f"{min_id}..{max_id}"
        )

    passed(
        f"CONTRACT ID RANGE = "
        f"{CONTRACT_MIN_ID}..{CONTRACT_MAX_ID}"
    )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            "CONTRACT DISTINCT ID COUNT mismatch"
        )

    passed(
        "CONTRACT DISTINCT IDs = "
        f"{EXPECTED_CONTRACT_ROWS}"
    )


# =============================================================================
# AST-ONLY RUNTIME NAMESPACE
# =============================================================================

@dataclass
class FunctionSource:
    path: Path
    source: str
    tree: ast.Module
    node: ast.FunctionDef | ast.AsyncFunctionDef


@dataclass
class ImportBinding:
    local_name: str
    module_name: str | None
    imported_name: str | None
    relative_level: int
    is_from_import: bool


# =============================================================================
# IMPORT AST DISCOVERY
# =============================================================================

def discover_import_bindings(
    tree: ast.AST,
) -> list[ImportBinding]:

    bindings: list[ImportBinding] = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            module_name = node.module

            for alias in node.names:

                if alias.name == "*":
                    continue

                local_name = (
                    alias.asname
                    or alias.name
                )

                bindings.append(
                    ImportBinding(
                        local_name=local_name,
                        module_name=module_name,
                        imported_name=alias.name,
                        relative_level=node.level,
                        is_from_import=True,
                    )
                )

        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                local_name = (
                    alias.asname
                    or alias.name.split(".")[0]
                )

                bindings.append(
                    ImportBinding(
                        local_name=local_name,
                        module_name=alias.name,
                        imported_name=None,
                        relative_level=0,
                        is_from_import=False,
                    )
                )

    return bindings


def find_validator_call(
    trace_node: ast.AST,
) -> ast.Call:

    matches: list[ast.Call] = []

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

        if len(node.args) != 2:
            continue

        if not (
            isinstance(
                node.args[0],
                ast.Name,
            )
            and node.args[0].id == "row"
        ):
            continue

        if not (
            isinstance(
                node.args[1],
                ast.Name,
            )
            and node.args[1].id == "columns"
        ):
            continue

        matches.append(node)

    if not matches:
        failed(
            "Exact production validation call "
            "validate_row(row, columns) was not found."
        )

    if len(matches) != 1:
        failed(
            "Expected exactly one "
            "validate_row(row, columns) call; "
            f"found {len(matches)}"
        )

    return matches[0]


def resolve_validator_binding(
    production_tree: ast.AST,
) -> ImportBinding:

    bindings = discover_import_bindings(
        production_tree
    )

    matches = [
        binding
        for binding in bindings
        if binding.local_name == VALIDATOR_SYMBOL
        and binding.is_from_import
        and binding.imported_name == VALIDATOR_SYMBOL
    ]

    if not matches:
        failed(
            "No AST import binding for production "
            f"{VALIDATOR_SYMBOL} was found."
        )

    if len(matches) != 1:
        failed(
            "Expected exactly one import binding for "
            f"{VALIDATOR_SYMBOL}; found {len(matches)}"
        )

    return matches[0]


# =============================================================================
# MODULE PATH RESOLUTION — NO IMPORT
# =============================================================================

def candidate_module_paths(
    production_file: Path,
    module_name: str,
) -> list[Path]:

    parts = module_name.split(".")

    candidates: list[Path] = []

    # Same directory as production module.
    base = production_file.parent

    candidates.append(
        base.joinpath(
            *parts
        ).with_suffix(".py")
    )

    candidates.append(
        base.joinpath(
            *parts,
            "__init__.py",
        )
    )

    # Production project root.
    project_root = production_file.parent

    candidates.append(
        project_root.joinpath(
            parts[-1] + ".py"
        )
    )

    return candidates


def locate_validator_source(
    production_file: Path,
    binding: ImportBinding,
) -> Path:

    if not binding.module_name:
        failed(
            "Validator import has no module name."
        )

    candidates = candidate_module_paths(
        production_file,
        binding.module_name,
    )

    unique: list[Path] = []

    seen: set[str] = set()

    for candidate in candidates:

        key = str(
            candidate.resolve()
        ).lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(candidate)

    for candidate in unique:

        if candidate.exists() and candidate.is_file():
            return candidate

    failed(
        "Production validator source file could not "
        "be resolved from AST import binding.\n"
        f"Module: {binding.module_name}\n"
        "Candidates:\n"
        + "\n".join(
            f"  {path}"
            for path in unique
        )
    )


def resolve_exact_validator_source(
    production_file: Path,
    binding: ImportBinding,
) -> FunctionSource:

    validator_path = locate_validator_source(
        production_file,
        binding,
    )

    source, tree = parse_source(
        validator_path
    )

    node = find_unique_function(
        tree,
        VALIDATOR_SYMBOL,
    )

    return FunctionSource(
        path=validator_path,
        source=source,
        tree=tree,
        node=node,
    )


# =============================================================================
# SAFE AST FUNCTION COMPILATION
# =============================================================================

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def compile_exact_function(
    function_source: FunctionSource,
    extra_namespace: dict[str, Any] | None = None,
) -> Any:

    node = function_source.node

    module = ast.Module(
        body=[
            ast.fix_missing_locations(
                ast.copy_location(
                    node,
                    node,
                )
            )
        ],
        type_ignores=[],
    )

    ast.fix_missing_locations(
        module
    )

    namespace: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__production_ast__",
        "__file__": str(
            function_source.path
        ),
    }

    if extra_namespace:
        namespace.update(
            extra_namespace
        )

    code = compile(
        module,
        filename=str(
            function_source.path
        ),
        mode="exec",
    )

    exec(
        code,
        namespace,
        namespace,
    )

    if VALIDATOR_SYMBOL not in namespace:
        failed(
            "Exact production validator failed "
            "to compile into namespace."
        )

    return namespace[VALIDATOR_SYMBOL]


# =============================================================================
# AST DEPENDENCY DISCOVERY
# =============================================================================

def referenced_names(
    node: ast.AST,
) -> set[str]:

    names: set[str] = set()

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ) and isinstance(
            child.ctx,
            ast.Load,
        ):
            names.add(
                child.id
            )

    return names


def top_level_definitions(
    tree: ast.Module,
) -> dict[str, ast.AST]:

    result: dict[str, ast.AST] = {}

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            result[node.name] = node

        elif isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name,
                ):
                    result[target.id] = node

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            if isinstance(
                node.target,
                ast.Name,
            ):
                result[node.target.id] = node

    return result


def build_validator_namespace(
    validator_source: FunctionSource,
) -> dict[str, Any]:

    """
    Compile the exact validator plus local production dependencies
    defined in the SAME validator source file.

    We intentionally do not import the module.

    External module dependencies are not silently fabricated.
    If the exact validator needs an unavailable external symbol,
    execution will fail explicitly and safely.
    """

    defs = top_level_definitions(
        validator_source.tree
    )

    needed = referenced_names(
        validator_source.node
    )

    selected: list[ast.AST] = []

    # Iteratively resolve locally defined symbols.
    resolved_names: set[str] = set()

    changed = True

    while changed:

        changed = False

        for name in list(needed):

            if name in resolved_names:
                continue

            if name not in defs:
                continue

            definition = defs[name]

            if definition is validator_source.node:
                continue

            selected.append(
                definition
            )

            resolved_names.add(name)

            for dep in referenced_names(
                definition
            ):
                if dep not in needed:
                    needed.add(dep)
                    changed = True

    body: list[ast.AST] = []

    # Local constants/functions/classes first.
    body.extend(selected)

    body.append(
        validator_source.node
    )

    module = ast.Module(
        body=body,
        type_ignores=[],
    )

    ast.fix_missing_locations(
        module
    )

    namespace: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__production_validator_ast__",
        "__file__": str(
            validator_source.path
        ),
    }

    code = compile(
        module,
        filename=str(
            validator_source.path
        ),
        mode="exec",
    )

    exec(
        code,
        namespace,
        namespace,
    )

    return namespace


# =============================================================================
# ACQUIRE EXACT PRODUCTION FUNCTION
# =============================================================================

def build_acquire_namespace() -> dict[str, Any]:

    source, tree = parse_source(
        PRODUCTION_FILE
    )

    acquire_node = find_unique_function(
        tree,
        ACQUIRE_FUNCTION,
    )

    # Dependencies required by acquire_real_rows.
    namespace: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__production_acquire_ast__",
        "__file__": str(PRODUCTION_FILE),

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

    module = ast.Module(
        body=[
            acquire_node,
        ],
        type_ignores=[],
    )

    ast.fix_missing_locations(
        module
    )

    code = compile(
        module,
        filename=str(PRODUCTION_FILE),
        mode="exec",
    )

    exec(
        code,
        namespace,
        namespace,
    )

    return {
        "function": namespace[ACQUIRE_FUNCTION],
        "node": acquire_node,
        "source": source,
        "tree": tree,
    }


# =============================================================================
# RUNTIME ACQUISITION
# =============================================================================

def execute_acquisition(
    conn: sqlite3.Connection,
) -> tuple[list[sqlite3.Row], list[str]]:

    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    bundle = build_acquire_namespace()

    acquire_function = bundle["function"]

    columns = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_technical)"
        ).fetchall()
    ]

    conn.row_factory = sqlite3.Row

    rows = acquire_function(
        conn,
        columns,
        TRACE_LIMIT,
    )

    if not rows:
        failed(
            "Production acquire_real_rows() returned no rows."
        )

    kv(
        "Runtime Rows Returned",
        len(rows),
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime acquisition expected "
            f"{EXPECTED_CONTRACT_ROWS} rows, got "
            f"{len(rows)}"
        )

    passed(
        f"Runtime acquisition = "
        f"{EXPECTED_CONTRACT_ROWS} rows"
    )

    return rows, columns


# =============================================================================
# RUNTIME ACQUISITION CONTRACT VERIFICATION
# =============================================================================

def verify_runtime_rows(
    rows: list[sqlite3.Row],
) -> None:

    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime row count mismatch."
        )

    ids = [
        row["id"]
        for row in rows
    ]

    if len(set(ids)) != len(ids):
        failed(
            "Runtime IDs are not distinct."
        )

    passed(
        f"Runtime row count = {len(rows)}"
    )

    passed(
        "Runtime distinct IDs = "
        f"{len(set(ids))}"
    )

    if min(ids) != CONTRACT_MIN_ID:
        failed(
            f"Runtime MIN ID expected "
            f"{CONTRACT_MIN_ID}, got {min(ids)}"
        )

    if max(ids) != CONTRACT_MAX_ID:
        failed(
            f"Runtime MAX ID expected "
            f"{CONTRACT_MAX_ID}, got {max(ids)}"
        )

    passed(
        f"Runtime MIN ID = {min(ids)}"
    )

    passed(
        f"Runtime MAX ID = {max(ids)}"
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
            "Runtime technical_version mismatch."
        )

    if engine_versions != {
        CONTRACT_ENGINE_VERSION
    }:
        failed(
            "Runtime engine_version mismatch."
        )

    if sources != {
        CONTRACT_SOURCE
    }:
        failed(
            "Runtime source mismatch."
        )

    passed(
        "Runtime technical_version = "
        f"{CONTRACT_TECHNICAL_VERSION}"
    )

    passed(
        "Runtime engine_version = "
        f"{CONTRACT_ENGINE_VERSION}"
    )

    passed(
        "Runtime source = "
        f"{CONTRACT_SOURCE}"
    )

    runtime_ids = ids

    expected_desc = sorted(
        runtime_ids,
        reverse=True,
    )

    if runtime_ids != expected_desc:
        failed(
            "Runtime ordering is not id DESC."
        )

    passed(
        "Runtime ordering = id DESC"
    )


# =============================================================================
# VALIDATOR RESOLUTION
# =============================================================================

def resolve_real_validator(
    production_tree: ast.Module,
    trace_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[
    ast.Call,
    ImportBinding,
    FunctionSource,
]:

    banner(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    validator_call = find_validator_call(
        trace_node
    )

    print(
        "Validator Call".ljust(55),
        ": validate_row(row, columns)"
    )

    passed(
        "Exact production validation call "
        "resolved from trace_real_validation()"
    )

    binding = resolve_validator_binding(
        production_tree
    )

    kv(
        "Import Binding",
        f"from {binding.module_name} "
        f"import {binding.imported_name}"
    )

    passed(
        "Production import binding resolved by AST"
    )

    validator_source = resolve_exact_validator_source(
        PRODUCTION_FILE,
        binding,
    )

    kv(
        "Validator Source File",
        validator_source.path,
    )

    kv(
        "Validator Function",
        VALIDATOR_SYMBOL,
    )

    kv(
        "Validator Start Line",
        validator_source.node.lineno,
    )

    kv(
        "Validator End Line",
        validator_source.node.end_lineno,
    )

    kv(
        "Validator Semantic SHA256",
        semantic_sha256(
            validator_source.node
        ),
    )

    passed(
        "Exact production validator FunctionDef "
        "resolved from imported production source"
    )

    return (
        validator_call,
        binding,
        validator_source,
    )


# =============================================================================
# VALIDATOR SIGNATURE
# =============================================================================

def verify_validator_signature(
    validator_source: FunctionSource,
) -> None:

    banner(
        "REAL PRODUCTION VALIDATOR SIGNATURE"
    )

    signature = inspect.Signature(
        parameters=[
            inspect.Parameter(
                arg.arg,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            for arg in validator_source.node.args.args
        ]
    )

    print(
        f"Function: {VALIDATOR_SYMBOL}"
    )

    print(
        f"Signature: {signature}"
    )

    parameter_names = [
        arg.arg
        for arg in validator_source.node.args.args
    ]

    if parameter_names != [
        "row",
        "columns",
    ]:
        failed(
            "Production validate_row() signature "
            "is not exactly (row, columns).\n"
            f"Actual parameters: {parameter_names}"
        )

    passed(
        "Production validator signature = "
        "(row, columns)"
    )


# =============================================================================
# EXACT VALIDATOR RUNTIME
# =============================================================================

def execute_exact_validator(
    validator_source: FunctionSource,
    rows: list[sqlite3.Row],
    columns: list[str],
) -> tuple[
    list[dict[str, Any]],
    Counter,
    Counter,
    Counter,
    list[dict[str, Any]],
]:

    banner(
        "EXACT PRODUCTION validate_row(row, columns) RUNTIME"
    )

    print(
        "Validator source:"
    )
    print(
        validator_source.path
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "Only the exact AST-resolved validate_row() "
        "is executed."
    )
    print(
        "No production module import."
    )
    print(
        "No production main()."
    )
    print(
        "Database remains read-only."
    )

    namespace = build_validator_namespace(
        validator_source
    )

    if VALIDATOR_SYMBOL not in namespace:
        failed(
            "Exact validator was not present "
            "after AST compilation."
        )

    validate_row = namespace[
        VALIDATOR_SYMBOL
    ]

    results: list[dict[str, Any]] = []

    status_counter: Counter = Counter()
    score_counter: Counter = Counter()
    flag_counter: Counter = Counter()

    execution_errors: list[
        dict[str, Any]
    ] = []

    for index, row in enumerate(
        rows,
        1,
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

        timestamp = (
            row["timestamp"]
            if "timestamp" in row.keys()
            else None
        )

        try:

            result = validate_row(
                row,
                columns,
            )

            if not isinstance(
                result,
                tuple,
            ):
                raise RuntimeError(
                    "validate_row() did not return tuple"
                )

            if len(result) != 3:
                raise RuntimeError(
                    "validate_row() return tuple length "
                    f"expected 3, got {len(result)}"
                )

            score, status, flags = result

            status_counter[
                safe(status)
            ] += 1

            score_counter[
                safe(score)
            ] += 1

            if flags:
                for flag in str(flags).split(","):
                    flag_counter[
                        flag.strip()
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

            # Do not flood stdout with 987 rows.
            # Print deterministic checkpoints.
            if (
                index <= 5
                or index in (
                    100,
                    250,
                    500,
                    750,
                    900,
                    987,
                )
            ):
                print(
                    f"[PASS] Validator row "
                    f"{index}/{len(rows)} "
                    f"id={record_id} "
                    f"symbol={symbol} "
                    f"score={safe(score)} "
                    f"status={safe(status)} "
                    f"flags={safe(flags)}"
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

            print(
                f"[FAIL] Validator row "
                f"{index}/{len(rows)} "
                f"id={record_id} "
                f"symbol={symbol}"
            )

            print(
                f"       {type(exc).__name__}: {exc}"
            )

    print()
    kv(
        "Rows Submitted",
        len(rows),
    )

    kv(
        "Rows Successfully Validated",
        len(results),
    )

    kv(
        "Execution Errors",
        len(execution_errors),
    )

    if execution_errors:
        failed(
            "REAL validate_row() execution failed "
            f"on {len(execution_errors)} row(s)."
        )

    if len(results) != len(rows):
        failed(
            "Validator result count does not equal "
            "runtime acquisition count."
        )

    passed(
        "Exact validate_row(row, columns) executed "
        f"successfully for all {len(rows)} rows"
    )

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
        execution_errors,
    )


# =============================================================================
# VALIDATION RESULT SUMMARY
# =============================================================================

def print_validation_summary(
    results: list[dict[str, Any]],
    status_counter: Counter,
    score_counter: Counter,
    flag_counter: Counter,
) -> None:

    banner(
        "REAL PRODUCTION VALIDATION RESULT SUMMARY"
    )

    kv(
        "Validated Rows",
        len(results),
    )

    print()
    print(
        "STATUS DISTRIBUTION:"
    )

    if status_counter:

        for status, count in sorted(
            status_counter.items(),
            key=lambda item: (
                str(item[0]),
                item[1],
            ),
        ):
            print(
                f"  {status:<35} : {count}"
            )

    else:
        print(
            "  <none>"
        )

    print()
    print(
        "SCORE DISTRIBUTION:"
    )

    for score, count in sorted(
        score_counter.items(),
        key=lambda item: (
            str(item[0]),
            item[1],
        ),
    ):
        print(
            f"  {score:<35} : {count}"
        )

    print()
    print(
        "FLAG DISTRIBUTION:"
    )

    if flag_counter:

        for flag, count in sorted(
            flag_counter.items(),
            key=lambda item: (
                str(item[0]),
                item[1],
            ),
        ):
            print(
                f"  {flag:<35} : {count}"
            )

    else:
        print(
            "  <none>"
        )


# =============================================================================
# INTEGRITY AFTER
# =============================================================================

def verify_integrity_after(
    production_sha_before: str,
    database_sha_before: str,
    database_size_before: int,
) -> None:

    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER"
    )

    production_sha_after = sha256_file(
        PRODUCTION_FILE
    )

    database_sha_after = sha256_file(
        DATABASE_FILE
    )

    database_size_after = (
        DATABASE_FILE.stat().st_size
    )

    kv(
        "Production SHA256 BEFORE",
        production_sha_before,
    )

    kv(
        "Production SHA256 AFTER",
        production_sha_after,
    )

    if production_sha_before != production_sha_after:
        failed(
            "Production source SHA256 changed."
        )

    passed(
        "Production source unchanged"
    )

    kv(
        "Database Size BEFORE",
        database_size_before,
    )

    kv(
        "Database Size AFTER",
        database_size_after,
    )

    if database_size_before != database_size_after:
        failed(
            "Database size changed."
        )

    passed(
        "Database size unchanged"
    )

    kv(
        "Database SHA256 BEFORE",
        database_sha_before,
    )

    kv(
        "Database SHA256 AFTER",
        database_sha_after,
    )

    if database_sha_before != database_sha_after:
        failed(
            "Database SHA256 changed."
        )

    passed(
        "Database SHA256 unchanged"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    banner(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VALIDATION v0.8"
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

    # -------------------------------------------------------------------------
    # BEFORE INTEGRITY
    # -------------------------------------------------------------------------

    if not PRODUCTION_FILE.exists():
        failed(
            f"Production file not found: {PRODUCTION_FILE}"
        )

    if not DATABASE_FILE.exists():
        failed(
            f"Database file not found: {DATABASE_FILE}"
        )

    production_sha_before = sha256_file(
        PRODUCTION_FILE
    )

    database_sha_before = sha256_file(
        DATABASE_FILE
    )

    database_size_before = (
        DATABASE_FILE.stat().st_size
    )

    banner(
        "PRODUCTION / DATABASE INTEGRITY BEFORE"
    )

    kv(
        "Production SHA256 BEFORE",
        production_sha_before,
    )

    kv(
        "Database Size BEFORE",
        database_size_before,
    )

    kv(
        "Database SHA256 BEFORE",
        database_sha_before,
    )

    # -------------------------------------------------------------------------
    # PRODUCTION AST
    # -------------------------------------------------------------------------

    production_source, production_tree = parse_source(
        PRODUCTION_FILE
    )

    acquire_node = find_unique_function(
        production_tree,
        ACQUIRE_FUNCTION,
    )

    trace_node = find_unique_function(
        production_tree,
        TRACE_FUNCTION,
    )

    banner(
        "PRODUCTION AST DISCOVERY — acquire_real_rows()"
    )

    kv(
        "Semantic SHA256",
        semantic_sha256(
            acquire_node
        ),
    )

    print_function_source(
        acquire_node,
        production_source,
        "EXACT PRODUCTION acquire_real_rows()",
    )

    banner(
        "PRODUCTION AST DISCOVERY — trace_real_validation()"
    )

    kv(
        "Semantic SHA256",
        semantic_sha256(
            trace_node
        ),
    )

    print_function_source(
        trace_node,
        production_source,
        "EXACT PRODUCTION trace_real_validation()",
    )

    # -------------------------------------------------------------------------
    # SQL CONTRACT
    # -------------------------------------------------------------------------

    verify_acquire_sql_contract(
        acquire_node
    )

    # -------------------------------------------------------------------------
    # EXACT VALIDATOR CALL + IMPORT + SOURCE
    # -------------------------------------------------------------------------

    (
        validator_call,
        validator_binding,
        validator_source,
    ) = resolve_real_validator(
        production_tree,
        trace_node,
    )

    verify_validator_signature(
        validator_source
    )

    print_function_source(
        validator_source.node,
        validator_source.source,
        "EXACT REAL PRODUCTION validate_row()",
    )

    # -------------------------------------------------------------------------
    # DATABASE
    # -------------------------------------------------------------------------

    conn = None

    try:

        conn = open_read_only_database()

        verify_database_preflight(
            conn
        )

        # ---------------------------------------------------------------------
        # EXACT PRODUCTION ACQUISITION
        # ---------------------------------------------------------------------

        rows, columns = execute_acquisition(
            conn
        )

        verify_runtime_rows(
            rows
        )

        # ---------------------------------------------------------------------
        # EXACT VALIDATOR RUNTIME
        # ---------------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
            execution_errors,
        ) = execute_exact_validator(
            validator_source,
            rows,
            columns,
        )

        print_validation_summary(
            results,
            status_counter,
            score_counter,
            flag_counter,
        )

    finally:

        if conn is not None:
            conn.close()

    # -------------------------------------------------------------------------
    # AFTER INTEGRITY
    # -------------------------------------------------------------------------

    verify_integrity_after(
        production_sha_before,
        database_sha_before,
        database_size_before,
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    banner(
        "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
    )

    kv(
        "Runtime Rows",
        EXPECTED_CONTRACT_ROWS,
    )

    kv(
        "Runtime MIN ID",
        CONTRACT_MIN_ID,
    )

    kv(
        "Runtime MAX ID",
        CONTRACT_MAX_ID,
    )

    kv(
        "Contract",
        CONTRACT_TECHNICAL_VERSION,
    )

    kv(
        "Engine",
        CONTRACT_ENGINE_VERSION,
    )

    kv(
        "Source",
        CONTRACT_SOURCE,
    )

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
        "EXACT trace_real_validation() CALL DISCOVERED"
    )

    passed(
        "EXACT validate_row(row, columns) CALL DISCOVERED"
    )

    passed(
        "REAL validator import binding resolved"
    )

    passed(
        "REAL validator FunctionDef resolved from production AST"
    )

    passed(
        "EXACT production validate_row(row, columns) EXECUTED"
    )

    passed(
        f"RUNTIME VALIDATION = {EXPECTED_CONTRACT_ROWS} / "
        f"{EXPECTED_CONTRACT_ROWS}"
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
        "PRODUCTION RUNTIME VALIDATION "
        "VERIFIED AT EXACT validate_row(row, columns) BOUNDARY"
    )

    print()
    print(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VALIDATION v0.8 COMPLETE"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as exc:

        print()
        print("=" * WIDTH)
        print(
            "FINAL STATUS           : FAIL"
        )
        print("=" * WIDTH)
        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )

        traceback.print_exc()

        sys.exit(1)
