# -*- coding: utf-8 -*-

"""
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v1.3

Purpose
-------
READ-ONLY production runtime validation.

Execution chain:

    REAL SQLite rows
        ->
    exact production acquire_real_rows()
        ->
    exact production validator resolution
        ->
    exact production validate_row(row, columns)
        ->
    PASS / FAIL

Critical rule
-------------
Production modules are NEVER imported.

Only exact AST-resolved production functions are compiled/executed.

This version fixes the v1.2 failure where the exact validator was found
but its AST execution environment did not contain imported dependencies
such as:

    import math

The resolver therefore constructs a minimal production dependency closure
from the validator's own source file.

NO production source is modified.
NO production database is modified.
"""

import ast
import copy
import hashlib
import inspect
import json
import math
import os
import sqlite3
import sys
import traceback
from collections import Counter
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION = "v1.3"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_FILE = (
    BASE_DIR /
    "market_technical_validation_engine_v0.4.1.py"
)

VALIDATOR_FILE = (
    BASE_DIR /
    "ARUNDA_TECHNICAL_ENGINE_v0.5.py"
)

DATABASE_FILE = (
    BASE_DIR /
    "arunda.db"
)

TARGET_TABLE = "market_technical"

TARGET_FUNCTION = "acquire_real_rows"
TRACE_FUNCTION = "trace_real_validation"
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
    print(f"{key:<60} {value}")


def passed(message):
    print(f"[PASS] {message}")


def failed(message):
    raise RuntimeError(message)


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


def semantic_hash(node):
    """
    Hash normalized AST structure rather than source formatting.
    """

    cloned = copy.deepcopy(node)

    for item in ast.walk(cloned):

        if isinstance(item, ast.Constant):
            if isinstance(item.value, str):
                item.value = "STR"
            elif isinstance(item.value, (int, float, complex)):
                item.value = "NUM"

    payload = ast.dump(
        cloned,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


# ============================================================================
# SOURCE / AST
# ============================================================================

def read_source(path):
    if not path.exists():
        failed(
            f"Production source does not exist: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


def parse_source(source, path):
    try:
        return ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        failed(
            f"AST parse failed for {path}: {exc}"
        )


def get_function_defs(tree):
    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result.setdefault(
                node.name,
                []
            ).append(node)

    return result


def resolve_unique_function(tree, name):
    definitions = get_function_defs(tree)

    nodes = definitions.get(name, [])

    if not nodes:
        failed(
            f"Production function not found: {name}"
        )

    if len(nodes) != 1:
        failed(
            f"Production function '{name}' is ambiguous: "
            f"{len(nodes)} definitions found."
        )

    return nodes[0]


# ============================================================================
# EXACT TRACE VALIDATOR CALL DISCOVERY
# ============================================================================

def discover_validator_call(trace_node, expected_symbol):
    matches = []

    for node in ast.walk(trace_node):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(
            node.func,
            ast.Name,
        ):
            continue

        if node.func.id != expected_symbol:
            continue

        args = node.args

        if len(args) != 2:
            continue

        first = args[0]
        second = args[1]

        if (
            isinstance(first, ast.Name)
            and first.id == "row"
            and isinstance(second, ast.Name)
            and second.id == "columns"
        ):
            matches.append(node)

    if len(matches) != 1:
        failed(
            "Could not uniquely resolve exact production "
            f"call {expected_symbol}(row, columns). "
            f"Matches={len(matches)}"
        )

    return matches[0]


# ============================================================================
# IMPORT / GLOBAL DEPENDENCY EXTRACTION
# ============================================================================

class DependencyResolver:
    """
    Builds the minimal execution environment needed by an exact AST
    production function.

    It deliberately does NOT import the production module.

    Standard-library imports are loaded individually.

    Local helper functions are recursively extracted from the same
    production source file.
    """

    SAFE_BUILTINS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "frozenset": frozenset,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "object": object,
        "print": print,
        "range": range,
        "repr": repr,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
    }

    def __init__(
        self,
        tree,
        source_path,
    ):
        self.tree = tree
        self.source_path = Path(source_path)

        self.function_defs = {}
        self.class_defs = {}
        self.import_nodes = []
        self.assignments = {}

        self.namespace = {
            "__name__": "__arunda_ast_production__",
            "__file__": str(self.source_path),
            "__package__": None,
            "__builtins__": self.SAFE_BUILTINS,
        }

        self._index_tree()

        # Explicit compatibility for dependencies that are common
        # and already observed in this production validator.
        self.namespace["math"] = math

    # ----------------------------------------------------------------------

    def _index_tree(self):

        for node in self.tree.body:

            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                self.function_defs[
                    node.name
                ] = node

            elif isinstance(
                node,
                ast.ClassDef,
            ):
                self.class_defs[
                    node.name
                ] = node

            elif isinstance(
                node,
                (
                    ast.Import,
                    ast.ImportFrom,
                ),
            ):
                self.import_nodes.append(node)

            elif isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.AugAssign,
                ),
            ):

                names = self._assignment_names(node)

                for name in names:
                    self.assignments[name] = node

    # ----------------------------------------------------------------------

    @staticmethod
    def _assignment_names(node):

        names = []

        if isinstance(node, ast.Assign):

            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)

        elif isinstance(node, ast.AnnAssign):

            if isinstance(
                node.target,
                ast.Name,
            ):
                names.append(node.target.id)

        elif isinstance(node, ast.AugAssign):

            if isinstance(
                node.target,
                ast.Name,
            ):
                names.append(node.target.id)

        return names

    # ----------------------------------------------------------------------

    @staticmethod
    def _load_import(node):

        if isinstance(node, ast.Import):

            for alias in node.names:

                module_name = alias.name
                local_name = alias.asname or module_name.split(".")[0]

                try:
                    module = __import__(
                        module_name
                    )
                except Exception as exc:
                    failed(
                        f"Could not load standard dependency "
                        f"'{module_name}': {exc}"
                    )

                yield local_name, module

        elif isinstance(node, ast.ImportFrom):

            module_name = node.module

            if not module_name:
                return

            if node.level:
                # Relative imports cannot safely be reconstructed
                # without importing the production package.
                failed(
                    "Relative production import encountered: "
                    f"from {'.' * node.level}{module_name} import ..."
                )

            try:
                module = __import__(
                    module_name,
                    fromlist=[
                        alias.name
                        for alias in node.names
                    ],
                )
            except Exception as exc:
                failed(
                    f"Could not load dependency "
                    f"'{module_name}': {exc}"
                )

            for alias in node.names:

                if alias.name == "*":
                    for name in dir(module):

                        if not name.startswith("_"):
                            yield (
                                name,
                                getattr(module, name),
                            )

                else:

                    local_name = (
                        alias.asname
                        or alias.name
                    )

                    if not hasattr(
                        module,
                        alias.name,
                    ):
                        failed(
                            f"Imported symbol '{alias.name}' "
                            f"not found in module '{module_name}'."
                        )

                    yield (
                        local_name,
                        getattr(module, alias.name),
                    )

    # ----------------------------------------------------------------------

    def load_all_imports(self):

        for node in self.import_nodes:

            for name, value in self._load_import(node):
                self.namespace[name] = value

        # Explicit known dependency.
        self.namespace["math"] = math

    # ----------------------------------------------------------------------

    @staticmethod
    def _collect_loaded_names(node):

        loaded = set()

        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Name,
            ):
                if isinstance(
                    child.ctx,
                    ast.Load,
                ):
                    loaded.add(
                        child.id
                    )

        return loaded

    # ----------------------------------------------------------------------

    def _compile_node(self, node):

        module = ast.Module(
            body=[node],
            type_ignores=[],
        )

        ast.fix_missing_locations(module)

        code = compile(
            module,
            filename=str(
                self.source_path
            ),
            mode="exec",
        )

        exec(
            code,
            self.namespace,
            self.namespace,
        )

    # ----------------------------------------------------------------------

    def _resolve_function(
        self,
        name,
        resolving,
    ):

        if name in self.namespace:
            return

        if name in resolving:
            failed(
                "Circular production dependency detected: "
                + " -> ".join(
                    list(resolving) + [name]
                )
            )

        node = self.function_defs.get(name)

        if node is None:
            return

        resolving.add(name)

        dependencies = self._collect_loaded_names(
            node
        )

        # First resolve local functions.
        for dependency in sorted(
            dependencies
        ):

            if dependency == name:
                continue

            if dependency in self.function_defs:
                self._resolve_function(
                    dependency,
                    resolving,
                )

        # Then constants / module-level assignments.
        for dependency in sorted(
            dependencies
        ):

            if dependency in self.namespace:
                continue

            assignment = self.assignments.get(
                dependency
            )

            if assignment is None:
                continue

            try:
                self._compile_node(
                    assignment
                )
            except Exception:
                raise

        self._compile_node(node)

        resolving.remove(name)

    # ----------------------------------------------------------------------

    def resolve_function(
        self,
        function_name,
    ):

        self.load_all_imports()

        if function_name not in self.function_defs:
            failed(
                f"Validator function '{function_name}' "
                "does not exist in validator AST."
            )

        self._resolve_function(
            function_name,
            set(),
        )

        if function_name not in self.namespace:
            failed(
                f"Function '{function_name}' failed to compile."
            )

        return self.namespace[
            function_name
        ]

    # ----------------------------------------------------------------------

    def dependency_report(self):

        banner(
            "VALIDATOR EXECUTION DEPENDENCY ENVIRONMENT"
        )

        imports = sorted(
            [
                key
                for key in self.namespace
                if not key.startswith("__")
            ]
        )

        kv(
            "Resolved namespace symbols",
            len(imports),
        )

        for name in imports:

            value = self.namespace[name]

            print(
                f"  {name:<35} "
                f"{type(value).__name__}"
            )

        if "math" not in self.namespace:
            failed(
                "CRITICAL: math dependency was not resolved."
            )

        passed(
            "Dependency environment contains math."
        )


# ============================================================================
# EXACT VALIDATOR RESOLUTION
# ============================================================================

def resolve_exact_validator():

    banner(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    if not VALIDATOR_FILE.exists():
        failed(
            f"Validator source not found: {VALIDATOR_FILE}"
        )

    validator_source = read_source(
        VALIDATOR_FILE
    )

    validator_tree = parse_source(
        validator_source,
        VALIDATOR_FILE,
    )

    validator_node = resolve_unique_function(
        validator_tree,
        VALIDATOR_SYMBOL,
    )

    signature = inspect.Signature.from_callable(
        compile_signature_probe(
            validator_node
        )
    )

    semantic = semantic_hash(
        validator_node
    )

    kv(
        "Validator File",
        VALIDATOR_FILE,
    )

    kv(
        "Validator Definition Line",
        validator_node.lineno,
    )

    kv(
        "Validator semantic SHA256",
        semantic,
    )

    kv(
        "Validator Signature",
        signature,
    )

    if str(signature) != "(row, columns)":
        failed(
            "Exact production validate_row signature mismatch: "
            f"{signature}"
        )

    passed(
        "Exact validator signature = (row, columns)"
    )

    resolver = DependencyResolver(
        validator_tree,
        VALIDATOR_FILE,
    )

    validator = resolver.resolve_function(
        VALIDATOR_SYMBOL
    )

    resolver.dependency_report()

    passed(
        "Exact production validate_row() compiled "
        "with its AST dependency closure."
    )

    return (
        validator,
        validator_node,
        validator_tree,
        validator_source,
    )


# ============================================================================
# SIGNATURE PROBE
# ============================================================================

def compile_signature_probe(node):

    """
    Compile only a harmless replacement body to obtain the exact
    Python signature without executing production code.
    """

    cloned = copy.deepcopy(node)

    cloned.body = [
        ast.Pass()
    ]

    module = ast.Module(
        body=[cloned],
        type_ignores=[],
    )

    ast.fix_missing_locations(
        module
    )

    namespace = {}

    exec(
        compile(
            module,
            filename="<signature-probe>",
            mode="exec",
        ),
        namespace,
        namespace,
    )

    return namespace[
        node.name
    ]


# ============================================================================
# PRODUCTION TRACE / ACQUISITION AST
# ============================================================================

def discover_production_nodes():

    source = read_source(
        PRODUCTION_FILE
    )

    tree = parse_source(
        source,
        PRODUCTION_FILE
    )

    acquire_node = resolve_unique_function(
        tree,
        TARGET_FUNCTION,
    )

    trace_node = resolve_unique_function(
        tree,
        TRACE_FUNCTION,
    )

    validator_call = discover_validator_call(
        trace_node,
        VALIDATOR_SYMBOL,
    )

    return (
        source,
        tree,
        acquire_node,
        trace_node,
        validator_call,
    )


# ============================================================================
# SQL SAFETY
# ============================================================================

def reconstruct_sql_from_acquire(
    acquire_node
):

    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    sql_strings = []

    dynamic_names = []

    for node in ast.walk(
        acquire_node
    ):

        if isinstance(
            node,
            ast.Constant,
        ) and isinstance(
            node.value,
            str,
        ):

            text = node.value.strip()

            lowered = text.lower()

            if (
                "select" in lowered
                or "where" in lowered
                or "order by" in lowered
                or "limit" in lowered
            ):
                sql_strings.append(
                    text
                )

        elif isinstance(
            node,
            ast.Name,
        ):

            if node.id == "TARGET_TABLE":
                dynamic_names.append(
                    node.id
                )

    if not sql_strings:
        failed(
            "No SQL literal found inside acquire_real_rows()."
        )

    sql = " ".join(
        sql_strings
    )

    normalized = " ".join(
        sql.lower().split()
    )

    print()
    print(
        "AST SQL RECONSTRUCTION:"
    )
    print(
        normalized
    )

    if dynamic_names:
        print()
        print(
            "AST SQL DYNAMIC EXPRESSIONS:"
        )

        for name in sorted(
            set(dynamic_names)
        ):
            print(
                f"  {name}"
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
                "Expected SQL fragment missing: "
                + fragment
            )

        passed(
            "SQL contract fragment: "
            + fragment
        )

    if "TARGET_TABLE" not in dynamic_names:
        failed(
            "TARGET_TABLE expression not preserved "
            "in production AST."
        )

    passed(
        "TARGET_TABLE expression preserved"
    )

    forbidden = [
        "insert into",
        "insert or",
        "update ",
        "delete from",
        "alter table",
        "create table",
        "drop table",
        "replace into",
    ]

    for fragment in forbidden:

        if fragment in normalized:
            failed(
                "Potential SQL write operation detected: "
                + fragment
            )

    passed(
        "No SQL write operation detected"
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
        uri=True,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

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
            "Database is not query_only."
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
        ),
    ).fetchone()[0]

    museum = total - contract

    ids = conn.execute(
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
        ),
    ).fetchone()

    min_id = ids[0]
    max_id = ids[1]
    distinct_ids = ids[2]

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
            f"DATABASE TOTAL mismatch: {total}"
        )

    passed(
        f"DATABASE TOTAL = {total}"
    )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            f"CONTRACT population mismatch: {contract}"
        )

    passed(
        f"CONTRACT = {contract}"
    )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            f"MUSEUM population mismatch: {museum}"
        )

    passed(
        f"MUSEUM = {museum}"
    )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            f"CONTRACT DISTINCT IDS mismatch: {distinct_ids}"
        )

    passed(
        f"CONTRACT DISTINCT IDS = {distinct_ids}"
    )

    if min_id is None or max_id is None:
        failed(
            "Contract ID range is empty."
        )

    return (
        total,
        contract,
        museum,
        min_id,
        max_id,
        distinct_ids,
    )


# ============================================================================
# EXACT ACQUIRE FUNCTION COMPILATION
# ============================================================================

def compile_exact_acquire(
    acquire_node,
    production_source,
):

    namespace = {
        "__name__": "__arunda_acquire__",
        "__file__": str(PRODUCTION_FILE),
        "__builtins__": DependencyResolver.SAFE_BUILTINS,
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
        body=[acquire_node],
        type_ignores=[],
    )

    ast.fix_missing_locations(
        module
    )

    exec(
        compile(
            module,
            filename=str(
                PRODUCTION_FILE
            ),
            mode="exec",
        ),
        namespace,
        namespace,
    )

    if TARGET_FUNCTION not in namespace:
        failed(
            "Exact acquire_real_rows() failed to compile."
        )

    passed(
        "Exact production acquire_real_rows() compiled."
    )

    return namespace[
        TARGET_FUNCTION
    ]


# ============================================================================
# EXACT ACQUISITION RUNTIME
# ============================================================================

def execute_exact_acquisition(
    acquire_function,
    conn,
    columns,
):

    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
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
        f"Runtime acquisition = {len(rows)} rows"
    )

    return rows


# ============================================================================
# COLUMN ACQUISITION
# ============================================================================

def get_columns(conn):

    cursor = conn.execute(
        f'SELECT * FROM "{TARGET_TABLE}" LIMIT 0'
    )

    return [
        description[0]
        for description in cursor.description
    ]


# ============================================================================
# ACQUISITION CONTRACT
# ============================================================================

def verify_acquisition_contract(
    rows,
    columns,
):

    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Runtime row count = {len(rows)}"
        )

    passed(
        f"Runtime row count = {len(rows)}"
    )

    data_rows = []

    for row in rows:

        if isinstance(
            row,
            sqlite3.Row,
        ):
            data_rows.append(
                dict(
                    zip(
                        columns,
                        tuple(row),
                    )
                )
            )

        elif isinstance(
            row,
            tuple,
        ):
            data_rows.append(
                dict(
                    zip(
                        columns,
                        row,
                    )
                )
            )

        else:
            failed(
                "Unsupported production row type: "
                f"{type(row).__name__}"
            )

    ids = [
        row["id"]
        for row in data_rows
    ]

    if len(set(ids)) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Runtime distinct IDs mismatch."
        )

    passed(
        f"Runtime distinct IDs = {len(set(ids))}"
    )

    if min(ids) != 5923:
        failed(
            f"Runtime MIN ID = {min(ids)}"
        )

    passed(
        f"Runtime MIN ID = {min(ids)}"
    )

    if max(ids) != 6909:
        failed(
            f"Runtime MAX ID = {max(ids)}"
        )

    passed(
        f"Runtime MAX ID = {max(ids)}"
    )

    if any(
        ids[i] <= ids[i + 1]
        for i in range(len(ids) - 1)
    ):
        failed(
            "Runtime ordering is not id DESC."
        )

    passed(
        "Runtime ordering = id DESC"
    )

    for row in data_rows:

        if row.get(
            "technical_version"
        ) != CONTRACT_TECHNICAL_VERSION:

            failed(
                "Runtime technical_version mismatch."
            )

        if row.get(
            "engine_version"
        ) != CONTRACT_ENGINE_VERSION:

            failed(
                "Runtime engine_version mismatch."
            )

        if row.get(
            "source"
        ) != CONTRACT_SOURCE:

            failed(
                "Runtime source mismatch."
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

    return data_rows


# ============================================================================
# EXACT VALIDATOR EXECUTION
# ============================================================================

def execute_exact_validator(
    validator,
    rows,
    columns,
):

    banner(
        "EXACT PRODUCTION validate_row(row, columns) RUNTIME"
    )

    results = []

    status_counter = Counter()
    score_counter = Counter()
    flag_counter = Counter()

    errors = []

    for index, row in enumerate(
        rows,
        1,
    ):

        record_id = None
        symbol = None

        try:

            if isinstance(
                row,
                sqlite3.Row,
            ):
                record_id = row["id"]
                symbol = (
                    row["symbol"]
                    if "symbol" in row.keys()
                    else None
                )

            elif isinstance(
                row,
                tuple,
            ):
                data = dict(
                    zip(
                        columns,
                        row,
                    )
                )

                record_id = data.get(
                    "id"
                )

                symbol = data.get(
                    "symbol"
                )

            else:
                failed(
                    "Unsupported row type."
                )

            result = validator(
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
                    "validate_row() returned tuple "
                    f"length {len(result)} instead of 3"
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
                        flag.strip()
                    ] += 1

            results.append(
                {
                    "id": record_id,
                    "symbol": symbol,
                    "score": score,
                    "status": status,
                    "flags": flags,
                }
            )

            if index <= 5:

                print()
                print(
                    f"TRACE ROW {index}"
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

        except Exception as exc:

            error = {
                "index": index,
                "id": record_id,
                "symbol": symbol,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }

            errors.append(
                error
            )

            print()
            print(
                f"[FAIL] validate_row execution at row {index}"
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
                "error",
                f"{type(exc).__name__}: {exc}",
            )

            print(
                traceback.format_exc()
            )

            # Fail immediately.
            # We are validating production runtime integrity,
            # not producing a partial result.
            raise RuntimeError(
                "REAL production validate_row() execution "
                f"failed at row {index}."
            ) from exc

    if len(results) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Validator result count mismatch: "
            f"{len(results)}"
        )

    passed(
        f"Exact validate_row() executed successfully "
        f"against all {len(results)} REAL contract rows."
    )

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
        errors,
    )


# ============================================================================
# FINAL RESULT
# ============================================================================

def print_validator_summary(
    results,
    status_counter,
    score_counter,
    flag_counter,
):

    banner(
        "VALIDATOR RUNTIME SUMMARY"
    )

    kv(
        "Validated REAL contract rows",
        len(results),
    )

    print()
    print(
        "STATUS DISTRIBUTION:"
    )

    for key, value in status_counter.most_common():
        print(
            f"  {key:<35} {value}"
        )

    print()
    print(
        "SCORE DISTRIBUTION:"
    )

    for key, value in score_counter.most_common():
        print(
            f"  {key:<35} {value}"
        )

    print()
    print(
        "FLAG DISTRIBUTION:"
    )

    for key, value in flag_counter.most_common():
        print(
            f"  {key:<35} {value}"
        )


# ============================================================================
# INTEGRITY AFTER
# ============================================================================

def verify_integrity_after(
    production_hash_before,
    database_hash_before,
    database_size_before,
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
        "Production SHA256 AFTER",
        production_hash_after,
    )

    kv(
        "Database Size AFTER",
        database_size_after,
    )

    kv(
        "Database SHA256 AFTER",
        database_hash_after,
    )

    if production_hash_before != production_hash_after:
        failed(
            "PRODUCTION FILE CHANGED DURING VALIDATION."
        )

    passed(
        "Production file unchanged."
    )

    if database_size_before != database_size_after:
        failed(
            "DATABASE SIZE CHANGED DURING VALIDATION."
        )

    passed(
        "Database size unchanged."
    )

    if database_hash_before != database_hash_after:
        failed(
            "DATABASE CONTENT HASH CHANGED DURING VALIDATION."
        )

    passed(
        "Database SHA256 unchanged."
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
        "Validator File",
        VALIDATOR_FILE,
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

    # ------------------------------------------------------------------
    # BEFORE INTEGRITY
    # ------------------------------------------------------------------

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
        production_hash_before,
    )

    kv(
        "Database Size BEFORE",
        database_size_before,
    )

    kv(
        "Database SHA256 BEFORE",
        database_hash_before,
    )

    # ------------------------------------------------------------------
    # AST DISCOVERY
    # ------------------------------------------------------------------

    (
        production_source,
        production_tree,
        acquire_node,
        trace_node,
        validator_call,
    ) = discover_production_nodes()

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

    banner(
        "EXACT PRODUCTION VALIDATION CALL DISCOVERY"
    )

    print(
        "Validator Call "
        "validate_row(row, columns)"
    )

    passed(
        "Exact production validation call resolved "
        "from trace_real_validation()."
    )

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    reconstruct_sql_from_acquire(
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

        columns = get_columns(
            conn
        )

        # --------------------------------------------------------------
        # ACQUIRE
        # --------------------------------------------------------------

        acquire_function = compile_exact_acquire(
            acquire_node,
            production_source,
        )

        rows = execute_exact_acquisition(
            acquire_function,
            conn,
            columns,
        )

        data_rows = verify_acquisition_contract(
            rows,
            columns,
        )

        # --------------------------------------------------------------
        # VALIDATOR
        # --------------------------------------------------------------

        validator, validator_node, validator_tree, validator_source = (
            resolve_exact_validator()
        )

        # Explicit production validator integrity.
        banner(
            "EXACT PRODUCTION VALIDATOR SOURCE"
        )

        kv(
            "Validator semantic SHA256",
            semantic_hash(
                validator_node
            ),
        )

        kv(
            "Validator source",
            VALIDATOR_FILE,
        )

        kv(
            "Validator definition line",
            validator_node.lineno,
        )

        # --------------------------------------------------------------
        # EXACT EXECUTION
        # --------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
            execution_errors,
        ) = execute_exact_validator(
            validator,
            rows,
            columns,
        )

        # --------------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------------

        print_validator_summary(
            results,
            status_counter,
            score_counter,
            flag_counter,
        )

    finally:

        if conn is not None:
            conn.close()

    # ------------------------------------------------------------------
    # AFTER INTEGRITY
    # ------------------------------------------------------------------

    verify_integrity_after(
        production_hash_before,
        database_hash_before,
        database_size_before,
    )

    # ------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------

    banner(
        "FINAL STATUS : PASS"
    )

    print(
        "REAL PRODUCTION TECHNICAL CONTRACT RUNTIME "
        "VALIDATION PASSED."
    )

    print(
        "Exact production acquire_real_rows() executed."
    )

    print(
        "Exact production validate_row(row, columns) "
        "executed against all REAL contract rows."
    )

    print(
        "Production source unchanged."
    )

    print(
        "Database unchanged."
    )


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