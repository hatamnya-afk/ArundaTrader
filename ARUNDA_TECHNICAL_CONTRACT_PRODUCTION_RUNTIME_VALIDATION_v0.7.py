# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.7
====================================================================================================

PURPOSE
-------
Read-only production runtime verification of the TECHNICAL_v0.5 contract.

Pipeline:

    REAL DATABASE
        |
        v
    exact production acquire_real_rows()
        |
        v
    exact production trace_real_validation()
        |
        v
    exact validation call discovered from trace AST
        |
        v
    exact production import binding resolution
        |
        v
    exact external validate_row() FunctionDef resolution
        |
        v
    AST-only compilation of validator + required dependencies
        |
        v
    REAL validate_row(row, columns)
        |
        v
    PASS / FAIL

HARD SAFETY RULES
-----------------
- Production module is NEVER imported.
- Production main() is NEVER executed.
- Database is opened SQLite mode=ro.
- PRAGMA query_only must be 1.
- No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP / REPLACE.
- No synthetic rows.
- No DB writes.
- No modification to production source.
- No modification to external validator source.
- Validator resolution is fail-closed.
- Ambiguous validator resolution is FAIL.
- Only the exact validator called by trace_real_validation() may be executed.
- First-row probe MUST PASS before the full 987-row execution.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import re
import sqlite3
import sys
import textwrap
import traceback
from collections import Counter
from pathlib import Path


# ================================================================================================
# CONFIGURATION
# ================================================================================================

PRODUCTION_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

PRODUCTION_DIR = PRODUCTION_FILE.parent

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

PROBE_ROWS = 1


# ================================================================================================
# OUTPUT
# ================================================================================================

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


def safe(value):
    try:
        return repr(value)
    except Exception:
        return "<UNREPRESENTABLE>"


# ================================================================================================
# HASHING
# ================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def semantic_sha256(node: ast.AST) -> str:
    normalized = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# ================================================================================================
# SOURCE / AST
# ================================================================================================

def read_source(path: Path) -> str:
    if not path.exists():
        failed(f"Production/source file does not exist: {path}")

    return path.read_text(
        encoding="utf-8"
    )


def parse_source(path: Path):
    source = read_source(path)

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        failed(
            f"AST parse failed for {path}: {exc}"
        )

    return source, tree


def all_function_defs(tree: ast.AST):
    result = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result.append(node)

    return result


def resolve_unique_function(
    tree: ast.AST,
    name: str,
    source_label: str,
):
    matches = [
        node
        for node in all_function_defs(tree)
        if node.name == name
    ]

    if not matches:
        return None

    if len(matches) > 1:
        failed(
            f"AMBIGUOUS function resolution: "
            f"{name!r} exists {len(matches)} times in {source_label}"
        )

    return matches[0]


def source_segment(
    source: str,
    node: ast.AST,
) -> str:
    segment = ast.get_source_segment(
        source,
        node,
    )

    if segment is None:
        failed(
            "Could not recover exact AST source segment."
        )

    return segment


# ================================================================================================
# AST FUNCTION CALL DISCOVERY
# ================================================================================================

def call_name(node: ast.Call):
    fn = node.func

    if isinstance(fn, ast.Name):
        return fn.id

    if isinstance(fn, ast.Attribute):
        return fn.attr

    return None


def discover_exact_validator_call(
    trace_node: ast.AST,
):
    calls = []

    for node in ast.walk(trace_node):

        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)

        if name != VALIDATOR_SYMBOL:
            continue

        calls.append(node)

    if not calls:
        failed(
            f"No call to {VALIDATOR_SYMBOL}(...) "
            f"found inside {TRACE_FUNCTION}()."
        )

    if len(calls) != 1:
        failed(
            f"Expected exactly one production call to "
            f"{VALIDATOR_SYMBOL}(), found {len(calls)}."
        )

    call = calls[0]

    if len(call.args) != 2:
        failed(
            f"Production {VALIDATOR_SYMBOL}() call "
            f"must have exactly two positional arguments."
        )

    arg0 = call.args[0]
    arg1 = call.args[1]

    if not (
        isinstance(arg0, ast.Name)
        and arg0.id == "row"
    ):
        failed(
            "Production validator call first argument "
            "is not exactly 'row'."
        )

    if not (
        isinstance(arg1, ast.Name)
        and arg1.id == "columns"
    ):
        failed(
            "Production validator call second argument "
            "is not exactly 'columns'."
        )

    return call


# ================================================================================================
# IMPORT RESOLUTION
# ================================================================================================

def module_name_from_import_node(
    node,
):
    if isinstance(node, ast.ImportFrom):
        return node.module

    if isinstance(node, ast.Import):
        names = [
            alias.name
            for alias in node.names
        ]

        return names

    return None


def discover_validator_import_bindings(
    production_tree: ast.AST,
):
    """
    Find every AST import binding that can define:

        validate_row

    Supported forms:

        from market_technical_engine import validate_row
        from market_technical_engine import validate_row as validate_row

    Also records:

        import market_technical_engine
        import market_technical_engine as mte

    The latter is useful for diagnostics but cannot bind bare validate_row.
    """

    direct = []
    modules = []

    for node in ast.walk(production_tree):

        if isinstance(node, ast.ImportFrom):

            for alias in node.names:

                bound_name = (
                    alias.asname
                    if alias.asname
                    else alias.name
                )

                if bound_name == VALIDATOR_SYMBOL:

                    direct.append(
                        {
                            "node": node,
                            "module": node.module,
                            "imported_name": alias.name,
                            "bound_name": bound_name,
                        }
                    )

        elif isinstance(node, ast.Import):

            for alias in node.names:

                bound_name = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                modules.append(
                    {
                        "node": node,
                        "module": alias.name,
                        "bound_name": bound_name,
                    }
                )

    return direct, modules


# ================================================================================================
# PYTHON MODULE PATH RESOLUTION
# ================================================================================================

def candidate_module_paths(
    module_name: str,
    origin_dir: Path,
):
    """
    Resolve normal Python source module paths without importing them.

    Example:

        market_technical_engine
        ->
        <origin>/market_technical_engine.py
    """

    candidates = []

    if not module_name:
        return candidates

    relative = Path(
        *module_name.split(".")
    )

    candidates.append(
        origin_dir / f"{relative}.py"
    )

    candidates.append(
        origin_dir / relative / "__init__.py"
    )

    return candidates


def resolve_module_source(
    module_name: str,
    origin_dir: Path,
):
    candidates = candidate_module_paths(
        module_name,
        origin_dir,
    )

    existing = [
        path.resolve()
        for path in candidates
        if path.exists()
    ]

    if not existing:
        failed(
            "Could not resolve imported production module "
            f"{module_name!r} from {origin_dir}.\n"
            "Candidates:\n"
            + "\n".join(
                f"  {p}"
                for p in candidates
            )
        )

    if len(existing) > 1:
        failed(
            "Ambiguous module resolution for "
            f"{module_name!r}:\n"
            + "\n".join(
                f"  {p}"
                for p in existing
            )
        )

    return existing[0]


# ================================================================================================
# EXTERNAL VALIDATOR RESOLUTION
# ================================================================================================

def resolve_real_validator():
    """
    Resolve the exact validator through the production AST import binding.

    IMPORTANT:
    We do NOT import the production module.
    """

    production_source, production_tree = parse_source(
        PRODUCTION_FILE
    )

    direct_imports, module_imports = (
        discover_validator_import_bindings(
            production_tree
        )
    )

    banner(
        "REAL PRODUCTION VALIDATOR IMPORT RESOLUTION"
    )

    kv(
        "Validator Symbol",
        VALIDATOR_SYMBOL
    )

    if not direct_imports:

        print()
        print(
            "No direct bare-name import binding found."
        )

        print(
            "Production module imports discovered:"
        )

        for item in module_imports:
            print(
                f"  import {item['module']} "
                f"as {item['bound_name']}"
            )

        failed(
            f"No production import binding for "
            f"{VALIDATOR_SYMBOL} was found."
        )

    if len(direct_imports) != 1:
        failed(
            f"Expected exactly one direct import binding "
            f"for {VALIDATOR_SYMBOL}, found "
            f"{len(direct_imports)}."
        )

    binding = direct_imports[0]

    module_name = binding["module"]
    imported_name = binding["imported_name"]

    if imported_name != VALIDATOR_SYMBOL:
        failed(
            "Import binding does not resolve to the exact "
            f"validator symbol {VALIDATOR_SYMBOL!r}."
        )

    if module_name is None:
        failed(
            "Validator import has no module name."
        )

    kv(
        "Production Import",
        f"from {module_name} import {imported_name}"
    )

    validator_file = resolve_module_source(
        module_name,
        PRODUCTION_DIR,
    )

    kv(
        "Resolved Validator File",
        validator_file
    )

    validator_source, validator_tree = parse_source(
        validator_file
    )

    validator_node = resolve_unique_function(
        validator_tree,
        VALIDATOR_SYMBOL,
        str(validator_file),
    )

    if validator_node is None:
        failed(
            f"Imported production module "
            f"{validator_file} does not define "
            f"{VALIDATOR_SYMBOL}()."
        )

    kv(
        "Validator Start Line",
        getattr(
            validator_node,
            "lineno",
            None,
        )
    )

    kv(
        "Validator End Line",
        getattr(
            validator_node,
            "end_lineno",
            None,
        )
    )

    kv(
        "Validator Semantic SHA256",
        semantic_sha256(
            validator_node
        )
    )

    print()
    print(
        "EXACT REAL validate_row() SOURCE:"
    )

    print(
        source_segment(
            validator_source,
            validator_node,
        )
    )

    passed(
        "Exact external production validate_row() "
        "resolved from import binding."
    )

    return {
        "production_source": production_source,
        "production_tree": production_tree,
        "validator_source": validator_source,
        "validator_tree": validator_tree,
        "validator_node": validator_node,
        "validator_file": validator_file,
        "binding": binding,
    }


# ================================================================================================
# STATIC DEPENDENCY ANALYSIS
# ================================================================================================

class DependencyResolver:
    """
    AST-only dependency resolver.

    Goal:
        compile exact validator without importing its module.

    We resolve:
        - functions defined in same module
        - simple literal / constant assignments
        - imported function bindings
        - imported constants
        - classes defined in same module

    Ambiguity / unsupported constructs fail closed.
    """

    def __init__(
        self,
        root_file: Path,
    ):
        self.root_file = root_file

        self.modules = {}
        self.namespaces = {}

        self.visited_functions = set()
        self.visited_files = set()

        self.global_nodes = {}

    # --------------------------------------------------------------------------------------------
    # LOAD
    # --------------------------------------------------------------------------------------------

    def load_module(
        self,
        path: Path,
    ):
        path = path.resolve()

        if path in self.modules:
            return self.modules[path]

        source, tree = parse_source(path)

        self.modules[path] = {
            "source": source,
            "tree": tree,
        }

        self.visited_files.add(path)

        return self.modules[path]

    # --------------------------------------------------------------------------------------------
    # NODE MAP
    # --------------------------------------------------------------------------------------------

    def index_module(
        self,
        path: Path,
    ):
        module = self.load_module(path)

        tree = module["tree"]

        mapping = {}

        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                mapping[node.name] = node

            elif isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                ),
            ):

                names = []

                if isinstance(
                    node,
                    ast.Assign,
                ):
                    for target in node.targets:
                        if isinstance(
                            target,
                            ast.Name,
                        ):
                            names.append(
                                target.id
                            )

                else:

                    if isinstance(
                        node.target,
                        ast.Name,
                    ):
                        names.append(
                            node.target.id
                        )

                for name in names:
                    mapping[name] = node

        self.global_nodes[path] = mapping

        return mapping

    # --------------------------------------------------------------------------------------------
    # SAFE CONSTANTS
    # --------------------------------------------------------------------------------------------

    def compile_constant(
        self,
        node,
    ):
        if isinstance(
            node,
            ast.Assign,
        ):

            if not isinstance(
                node.value,
                ast.Constant,
            ):
                return None

            return node.value.value

        if isinstance(
            node,
            ast.AnnAssign,
        ):

            if not isinstance(
                node.value,
                ast.Constant,
            ):
                return None

            return node.value.value

        return None

    # --------------------------------------------------------------------------------------------
    # IMPORTS
    # --------------------------------------------------------------------------------------------

    def imported_bindings(
        self,
        tree,
    ):
        result = {}

        for node in ast.walk(tree):

            if isinstance(
                node,
                ast.ImportFrom,
            ):

                for alias in node.names:

                    if alias.name == "*":
                        continue

                    bound = (
                        alias.asname
                        if alias.asname
                        else alias.name
                    )

                    result[bound] = {
                        "kind": "from",
                        "module": node.module,
                        "name": alias.name,
                    }

            elif isinstance(
                node,
                ast.Import,
            ):

                for alias in node.names:

                    bound = (
                        alias.asname
                        if alias.asname
                        else alias.name.split(".")[0]
                    )

                    result[bound] = {
                        "kind": "import",
                        "module": alias.name,
                    }

        return result

    # --------------------------------------------------------------------------------------------
    # NAMES USED BY FUNCTION
    # --------------------------------------------------------------------------------------------

    def names_used_by_function(
        self,
        function_node,
    ):
        loads = set()

        stores = set()

        for node in ast.walk(function_node):

            if isinstance(
                node,
                ast.Name,
            ):

                if isinstance(
                    node.ctx,
                    ast.Load,
                ):
                    loads.add(node.id)

                elif isinstance(
                    node.ctx,
                    ast.Store,
                ):
                    stores.add(node.id)

        return loads - stores

    # --------------------------------------------------------------------------------------------
    # FIND DEF
    # --------------------------------------------------------------------------------------------

    def find_function(
        self,
        path: Path,
        name: str,
    ):
        mapping = self.index_module(
            path
        )

        node = mapping.get(name)

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            return node

        return None

    # --------------------------------------------------------------------------------------------
    # RESOLVE IMPORTED FUNCTION
    # --------------------------------------------------------------------------------------------

    def resolve_imported_function(
        self,
        current_file: Path,
        binding,
    ):
        if binding["kind"] != "from":
            return None

        module_name = binding["module"]
        symbol_name = binding["name"]

        if not module_name:
            return None

        module_file = resolve_module_source(
            module_name,
            current_file.parent,
        )

        node = self.find_function(
            module_file,
            symbol_name,
        )

        if node is None:
            return None

        return module_file, node

    # --------------------------------------------------------------------------------------------
    # COLLECT FUNCTION DEPENDENCIES
    # --------------------------------------------------------------------------------------------

    def collect_function_dependencies(
        self,
        path: Path,
        function_node,
    ):
        path = path.resolve()

        key = (
            str(path),
            function_node.name,
        )

        if key in self.visited_functions:
            return

        self.visited_functions.add(key)

        module = self.load_module(
            path
        )

        tree = module["tree"]

        mapping = self.index_module(
            path
        )

        imports = self.imported_bindings(
            tree
        )

        used = self.names_used_by_function(
            function_node
        )

        # local globals
        for name in sorted(used):

            if name in mapping:

                dep = mapping[name]

                if isinstance(
                    dep,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):

                    self.collect_function_dependencies(
                        path,
                        dep,
                    )

                elif isinstance(
                    dep,
                    ast.ClassDef,
                ):

                    # Classes are included as AST objects
                    # but their internal dependencies are not
                    # recursively executed unless referenced.
                    continue

                elif isinstance(
                    dep,
                    (
                        ast.Assign,
                        ast.AnnAssign,
                    ),
                ):

                    value = self.compile_constant(
                        dep
                    )

                    if value is None:
                        failed(
                            "Validator dependency "
                            f"{name!r} is not a simple constant "
                            "assignment and cannot be safely "
                            "resolved AST-only."
                        )

            elif name in imports:

                binding = imports[name]

                if binding["kind"] == "from":

                    resolved = (
                        self.resolve_imported_function(
                            path,
                            binding,
                        )
                    )

                    if resolved is not None:

                        dep_file, dep_node = (
                            resolved
                        )

                        self.collect_function_dependencies(
                            dep_file,
                            dep_node,
                        )

                    else:

                        # Some imported symbols are standard
                        # library modules/constants. They are
                        # handled separately by safe runtime
                        # namespace construction.
                        continue

                elif binding["kind"] == "import":

                    continue

    # --------------------------------------------------------------------------------------------
    # BUILD NAMESPACE
    # --------------------------------------------------------------------------------------------

    def build_namespace(
        self,
        root_path: Path,
    ):
        namespace = {
            "__builtins__": __builtins__,
        }

        # Safe standard-library objects commonly used by
        # technical validation functions.
        safe_stdlib = {
            "math": __import__("math"),
            "statistics": __import__("statistics"),
            "datetime": __import__("datetime"),
            "re": __import__("re"),
            "decimal": __import__("decimal"),
            "numpy": None,
        }

        namespace.update(
            {
                k: v
                for k, v in safe_stdlib.items()
                if v is not None
            }
        )

        # We collect all visited modules.
        for path in list(
            self.visited_files
        ):

            module = self.load_module(
                path
            )

            tree = module["tree"]

            mapping = self.index_module(
                path
            )

            # Constants
            for name, node in mapping.items():

                if isinstance(
                    node,
                    (
                        ast.Assign,
                        ast.AnnAssign,
                    ),
                ):

                    value = self.compile_constant(
                        node
                    )

                    if value is not None:
                        namespace[name] = value

        # Functions
        for path in list(
            self.visited_files
        ):

            mapping = self.index_module(
                path
            )

            for name, node in mapping.items():

                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):

                    # compile exact function in a temporary
                    # namespace containing current dependencies
                    module = self.modules[path]

                    fn_source = source_segment(
                        module["source"],
                        node,
                    )

                    try:
                        code = compile(
                            textwrap.dedent(
                                fn_source
                            ),
                            str(path),
                            "exec",
                        )
                    except Exception as exc:
                        failed(
                            f"Failed compiling dependency "
                            f"{name!r} from {path}: {exc}"
                        )

                    local_ns = dict(
                        namespace
                    )

                    try:
                        exec(
                            code,
                            local_ns,
                            local_ns,
                        )
                    except Exception as exc:
                        failed(
                            f"Failed defining dependency "
                            f"{name!r} from {path}: "
                            f"{type(exc).__name__}: {exc}"
                        )

                    if name in local_ns:
                        namespace[name] = (
                            local_ns[name]
                        )

        return namespace


# ================================================================================================
# EXACT VALIDATOR COMPILATION
# ================================================================================================

def compile_exact_validator(
    validator_file: Path,
    validator_node,
):
    banner(
        "EXACT PRODUCTION VALIDATOR AST COMPILATION"
    )

    resolver = DependencyResolver(
        validator_file
    )

    resolver.collect_function_dependencies(
        validator_file,
        validator_node,
    )

    namespace = resolver.build_namespace(
        validator_file
    )

    source = resolver.modules[
        validator_file.resolve()
    ]["source"]

    fn_source = source_segment(
        source,
        validator_node,
    )

    try:
        code = compile(
            textwrap.dedent(
                fn_source
            ),
            str(validator_file),
            "exec",
        )
    except Exception as exc:
        failed(
            "Exact validator compilation failed: "
            f"{type(exc).__name__}: {exc}"
        )

    local_ns = dict(
        namespace
    )

    try:
        exec(
            code,
            local_ns,
            local_ns,
        )
    except Exception as exc:
        failed(
            "Exact validator definition execution failed: "
            f"{type(exc).__name__}: {exc}"
        )

    validator = local_ns.get(
        validator_node.name
    )

    if validator is None:
        failed(
            "Compiled validator function was not "
            "created in isolated namespace."
        )

    if not callable(validator):
        failed(
            "Resolved validator object is not callable."
        )

    passed(
        "Exact validate_row() compiled "
        "without importing production module."
    )

    return validator


# ================================================================================================
# PRODUCTION acquire_real_rows AST COMPILATION
# ================================================================================================

def compile_exact_acquire_function(
    production_source: str,
    acquire_node,
    conn,
    columns,
):
    banner(
        "EXACT PRODUCTION acquire_real_rows() AST EXECUTION"
    )

    fn_source = source_segment(
        production_source,
        acquire_node,
    )

    # Exact production globals required by acquire_real_rows.
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

    try:
        code = compile(
            textwrap.dedent(
                fn_source
            ),
            str(PRODUCTION_FILE),
            "exec",
        )
    except Exception as exc:
        failed(
            "acquire_real_rows compilation failed: "
            f"{type(exc).__name__}: {exc}"
        )

    local_ns = dict(namespace)

    try:
        exec(
            code,
            local_ns,
            local_ns,
        )
    except Exception as exc:
        failed(
            "acquire_real_rows definition execution failed: "
            f"{type(exc).__name__}: {exc}"
        )

    fn = local_ns.get(
        TARGET_FUNCTION
    )

    if fn is None:
        failed(
            "Compiled acquire_real_rows() missing."
        )

    return fn


# ================================================================================================
# DATABASE
# ================================================================================================

def database_sha256(
    path: Path,
):
    return sha256_file(path)


def open_read_only_database():
    if not DATABASE_FILE.exists():
        failed(
            f"Database does not exist: {DATABASE_FILE}"
        )

    uri = (
        "file:"
        + DATABASE_FILE.as_posix()
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if query_only != 1:
        # Explicitly force query_only even though mode=ro
        # should already prevent writes.
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


# ================================================================================================
# DATABASE PREFLIGHT
# ================================================================================================

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
            "Database is not query_only."
        )

    total = conn.execute(
        f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
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

    min_id = conn.execute(
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
        ),
    ).fetchone()[0]

    max_id = conn.execute(
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
        ),
    ).fetchone()[0]

    distinct_ids = conn.execute(
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

    if total != (
        EXPECTED_CONTRACT_ROWS
        + EXPECTED_MUSEUM_ROWS
    ):
        failed(
            "DATABASE TOTAL mismatch."
        )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            "CONTRACT population mismatch."
        )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            "MUSEUM population mismatch."
        )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            "CONTRACT distinct ID count mismatch."
        )

    if min_id != 5923 or max_id != 6909:
        failed(
            "CONTRACT ID range mismatch."
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
        "CONTRACT ID RANGE = 5923..6909"
    )


# ================================================================================================
# ACQUIRE RUNTIME
# ================================================================================================

def execute_exact_acquisition(
    conn,
    columns,
    acquire_function,
):
    rows = acquire_function(
        conn,
        columns,
        TRACE_LIMIT,
    )

    if not isinstance(
        rows,
        list,
    ):
        rows = list(rows)

    return rows


def verify_acquired_rows(
    rows,
):
    banner(
        "RUNTIME ACQUISITION CONTRACT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Runtime row count = {len(rows)}, "
            f"expected {EXPECTED_CONTRACT_ROWS}."
        )

    for row in rows:

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

        if row["source"] != CONTRACT_SOURCE:
            failed(
                "Runtime source mismatch."
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

    if ids != sorted(
        ids,
        reverse=True,
    ):
        failed(
            "Runtime ordering is not id DESC."
        )

    passed(
        f"Runtime row count = {len(rows)}"
    )

    passed(
        f"Runtime technical_version = "
        f"{CONTRACT_TECHNICAL_VERSION}"
    )

    passed(
        f"Runtime engine_version = "
        f"{CONTRACT_ENGINE_VERSION}"
    )

    passed(
        f"Runtime source = {CONTRACT_SOURCE}"
    )

    passed(
        f"Runtime distinct IDs = {len(set(ids))}"
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
# VALIDATOR SIGNATURE
# ================================================================================================

def verify_validator_signature(
    validator,
):
    banner(
        "REAL validate_row() SIGNATURE"
    )

    try:
        signature = inspect.signature(
            validator
        )
    except Exception as exc:
        failed(
            "Could not inspect exact validator signature: "
            f"{exc}"
        )

    kv(
        "Signature",
        signature,
    )

    params = list(
        signature.parameters.values()
    )

    if len(params) != 2:
        failed(
            "Exact validate_row() must expose "
            "exactly two parameters."
        )

    if params[0].name != "row":
        failed(
            f"First validator parameter is "
            f"{params[0].name!r}, expected 'row'."
        )

    if params[1].name != "columns":
        failed(
            f"Second validator parameter is "
            f"{params[1].name!r}, expected 'columns'."
        )

    passed(
        "Validator signature = (row, columns)"
    )

    return signature


# ================================================================================================
# PROBE
# ================================================================================================

def execute_validator_probe(
    validator,
    row,
    columns,
):
    banner(
        "REAL validate_row(row, columns) PROBE"
    )

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

    kv(
        "Probe ID",
        record_id,
    )

    kv(
        "Probe Symbol",
        symbol,
    )

    kv(
        "Probe Timestamp",
        timestamp,
    )

    try:
        result = validator(
            row,
            columns,
        )
    except Exception as exc:
        print()
        print(
            "[FAIL] Exact production validator "
            "execution failed during probe."
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print(
            traceback.format_exc()
        )

        failed(
            "REAL validate_row(row, columns) probe FAILED."
        )

    print()
    print(
        "REAL validate_row() PROBE OUTPUT:"
    )

    print(
        f"raw_return : {result!r}"
    )

    if not isinstance(
        result,
        tuple,
    ):
        failed(
            "validate_row() did not return tuple."
        )

    if len(result) != 3:
        failed(
            "validate_row() returned tuple length "
            f"{len(result)}, expected 3."
        )

    score, status, flags = result

    kv(
        "score",
        safe(score),
    )

    kv(
        "status",
        safe(status),
    )

    kv(
        "flags",
        safe(flags),
    )

    passed(
        "REAL validate_row(row, columns) probe PASS"
    )

    return result


# ================================================================================================
# FULL RUNTIME VALIDATION
# ================================================================================================

def execute_full_runtime_validation(
    validator,
    rows,
    columns,
):
    banner(
        "FULL REAL PRODUCTION VALIDATION — 987 CONTRACT ROWS"
    )

    results = []

    status_counter = Counter()
    score_counter = Counter()
    flag_counter = Counter()

    execution_errors = []

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
                for flag in str(flags).split(","):
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
                    "traceback":
                        traceback.format_exc(),
                }
            )

            print()
            print(
                "-" * 100
            )

            print(
                f"[FAIL] Validation row {index}"
            )

            print(
                f"id       : {record_id}"
            )

            print(
                f"symbol   : {symbol}"
            )

            print(
                f"timestamp: {timestamp}"
            )

            print(
                f"error    : {type(exc).__name__}: {exc}"
            )

            # Fail immediately.
            # Launch-critical verification must not silently
            # continue after validator execution failure.
            break

    if execution_errors:
        failed(
            "REAL production validation execution FAILED "
            f"at row {execution_errors[0]['index']}."
        )

    if len(results) != EXPECTED_CONTRACT_ROWS:
        failed(
            f"Validator returned {len(results)} successful "
            f"results, expected {EXPECTED_CONTRACT_ROWS}."
        )

    banner(
        "RUNTIME VALIDATION RESULT SUMMARY"
    )

    kv(
        "Rows Validated",
        len(results),
    )

    kv(
        "Execution Errors",
        len(execution_errors),
    )

    kv(
        "Distinct Statuses",
        len(status_counter),
    )

    print()
    print(
        "STATUS DISTRIBUTION:"
    )

    for key, value in status_counter.items():
        print(
            f"  {key:<40} {value}"
        )

    print()
    print(
        "SCORE DISTRIBUTION:"
    )

    for key, value in score_counter.items():
        print(
            f"  {key:<40} {value}"
        )

    print()
    print(
        "FLAG DISTRIBUTION:"
    )

    if flag_counter:
        for key, value in flag_counter.items():
            print(
                f"  {key:<40} {value}"
            )
    else:
        print(
            "  NONE"
        )

    passed(
        "All 987 Contract rows executed through "
        "exact production validate_row(row, columns)."
    )

    return results


# ================================================================================================
# PRODUCTION TRACE VALIDATION
# ================================================================================================

def verify_trace_function(
    production_source,
    production_tree,
):
    banner(
        "PRODUCTION AST DISCOVERY — trace_real_validation()"
    )

    trace_node = resolve_unique_function(
        production_tree,
        TRACE_FUNCTION,
        str(PRODUCTION_FILE),
    )

    if trace_node is None:
        failed(
            f"{TRACE_FUNCTION}() not found."
        )

    kv(
        "Semantic SHA256",
        semantic_sha256(
            trace_node
        ),
    )

    call = discover_exact_validator_call(
        trace_node
    )

    passed(
        "Exact production validation call "
        "resolved from trace_real_validation()."
    )

    kv(
        "Validator Call",
        "validate_row(row, columns)",
    )

    return trace_node, call


# ================================================================================================
# SOURCE / DATABASE INTEGRITY
# ================================================================================================

def verify_integrity_unchanged(
    production_hash_before,
    database_hash_before,
    database_size_before,
):
    banner(
        "PRODUCTION / DATABASE INTEGRITY AFTER RUNTIME"
    )

    production_hash_after = sha256_file(
        PRODUCTION_FILE
    )

    database_size_after = (
        DATABASE_FILE.stat().st_size
    )

    database_hash_after = (
        database_sha256(
            DATABASE_FILE
        )
    )

    kv(
        "Production SHA256 BEFORE",
        production_hash_before,
    )

    kv(
        "Production SHA256 AFTER",
        production_hash_after,
    )

    if (
        production_hash_before
        != production_hash_after
    ):
        failed(
            "Production source changed during runtime."
        )

    passed(
        "Production source unchanged."
    )

    kv(
        "Database Size BEFORE",
        database_size_before,
    )

    kv(
        "Database Size AFTER",
        database_size_after,
    )

    kv(
        "Database SHA256 BEFORE",
        database_hash_before,
    )

    kv(
        "Database SHA256 AFTER",
        database_hash_after,
    )

    if database_size_before != database_size_after:
        failed(
            "Database size changed during runtime."
        )

    if database_hash_before != database_hash_after:
        failed(
            "Database SHA256 changed during runtime."
        )

    passed(
        "Database size unchanged."
    )

    passed(
        "Database SHA256 unchanged."
    )


# ================================================================================================
# MAIN
# ================================================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.7"
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

    # --------------------------------------------------------------------------------------------
    # INTEGRITY BEFORE
    # --------------------------------------------------------------------------------------------

    if not PRODUCTION_FILE.exists():
        failed(
            f"Production file does not exist: "
            f"{PRODUCTION_FILE}"
        )

    if not DATABASE_FILE.exists():
        failed(
            f"Database does not exist: "
            f"{DATABASE_FILE}"
        )

    production_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    database_size_before = (
        DATABASE_FILE.stat().st_size
    )

    database_hash_before = (
        database_sha256(
            DATABASE_FILE
        )
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

    # --------------------------------------------------------------------------------------------
    # PARSE PRODUCTION
    # --------------------------------------------------------------------------------------------

    production_source, production_tree = (
        parse_source(
            PRODUCTION_FILE
        )
    )

    # --------------------------------------------------------------------------------------------
    # DISCOVER ACQUIRE
    # --------------------------------------------------------------------------------------------

    banner(
        "PRODUCTION AST DISCOVERY — acquire_real_rows()"
    )

    acquire_node = resolve_unique_function(
        production_tree,
        TARGET_FUNCTION,
        str(PRODUCTION_FILE),
    )

    if acquire_node is None:
        failed(
            "Production acquire_real_rows() not found."
        )

    kv(
        "Semantic SHA256",
        semantic_sha256(
            acquire_node
        ),
    )

    print()
    print(
        "EXACT PRODUCTION acquire_real_rows():"
    )

    print(
        source_segment(
            production_source,
            acquire_node,
        )
    )

    # --------------------------------------------------------------------------------------------
    # VERIFY TRACE AND CALL SITE
    # --------------------------------------------------------------------------------------------

    trace_node, validator_call = (
        verify_trace_function(
            production_source,
            production_tree,
        )
    )

    # --------------------------------------------------------------------------------------------
    # SQL SAFETY — STRUCTURAL ONLY
    # --------------------------------------------------------------------------------------------

    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    acquire_calls = []

    for node in ast.walk(
        acquire_node
    ):
        if isinstance(
            node,
            ast.Call,
        ):
            if (
                isinstance(
                    node.func,
                    ast.Attribute,
                )
                and node.func.attr == "execute"
            ):
                acquire_calls.append(node)

    if len(acquire_calls) != 1:
        failed(
            "Expected exactly one conn.execute() "
            "inside acquire_real_rows()."
        )

    execute_call = acquire_calls[0]

    sql_node = (
        execute_call.args[0]
        if execute_call.args
        else None
    )

    if not isinstance(
        sql_node,
        ast.JoinedStr,
    ):
        failed(
            "acquire_real_rows() SQL is not an f-string."
        )

    sql_parts = []

    for value in sql_node.values:

        if isinstance(
            value,
            ast.Constant,
        ):
            sql_parts.append(
                str(value.value)
            )

        elif isinstance(
            value,
            ast.FormattedValue,
        ):

            if isinstance(
                value.value,
                ast.Name,
            ):
                sql_parts.append(
                    "{"
                    + value.value.id
                    + "}"
                )
            else:
                sql_parts.append(
                    "{EXPRESSION}"
                )

    reconstructed_sql = " ".join(
        sql_parts
    )

    normalized_sql = re.sub(
        r"\s+",
        " ",
        reconstructed_sql,
    ).strip().lower()

    print()
    print(
        "RECONSTRUCTED SQL:"
    )

    print(
        normalized_sql
    )

    expected_fragments = [
        "select *",
        "from {target_table}",
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in expected_fragments:

        if fragment not in normalized_sql:
            failed(
                "Expected SQL fragment missing: "
                + fragment
            )

        passed(
            f"SQL fragment: {fragment}"
        )

    forbidden = [
        "insert ",
        "update ",
        "delete ",
        "alter ",
        "create ",
        "drop ",
        "replace ",
    ]

    for keyword in forbidden:

        if keyword in normalized_sql:
            failed(
                f"SQL write operation detected: "
                f"{keyword.strip()}"
            )

    passed(
        "Contract predicates present"
    )

    passed(
        "ORDER BY id DESC preserved"
    )

    passed(
        "LIMIT ? preserved"
    )

    passed(
        "No SQL write operation detected"
    )

    # --------------------------------------------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------------------------------------------

    conn = open_read_only_database()

    try:

        database_preflight(
            conn
        )

        # ----------------------------------------------------------------------------------------
        # COLUMN ORDER
        # ----------------------------------------------------------------------------------------

        columns = [
            row[1]
            for row in conn.execute(
                f'PRAGMA table_info("{TARGET_TABLE}")'
            ).fetchall()
        ]

        if not columns:
            failed(
                "Could not determine market_technical columns."
            )

        # ----------------------------------------------------------------------------------------
        # ACQUIRE EXACT PRODUCTION FUNCTION
        # ----------------------------------------------------------------------------------------

        acquire_function = (
            compile_exact_acquire_function(
                production_source,
                acquire_node,
                conn,
                columns,
            )
        )

        banner(
            "EXACT PRODUCTION acquire_real_rows() RUNTIME"
        )

        rows = execute_exact_acquisition(
            conn,
            columns,
            acquire_function,
        )

        kv(
            "Runtime Rows Returned",
            len(rows),
        )

        if len(rows) != EXPECTED_CONTRACT_ROWS:
            failed(
                "Runtime acquisition did not return "
                f"{EXPECTED_CONTRACT_ROWS} rows."
            )

        passed(
            f"Runtime acquisition = "
            f"{EXPECTED_CONTRACT_ROWS} rows"
        )

        verify_acquired_rows(
            rows
        )

        # ----------------------------------------------------------------------------------------
        # RESOLVE REAL VALIDATOR
        # ----------------------------------------------------------------------------------------

        resolved = resolve_real_validator()

        validator_file = resolved[
            "validator_file"
        ]

        validator_node = resolved[
            "validator_node"
        ]

        # ----------------------------------------------------------------------------------------
        # COMPILE EXACT VALIDATOR
        # ----------------------------------------------------------------------------------------

        validator = compile_exact_validator(
            validator_file,
            validator_node,
        )

        verify_validator_signature(
            validator
        )

        # ----------------------------------------------------------------------------------------
        # FIRST ROW PROBE — MANDATORY
        # ----------------------------------------------------------------------------------------

        execute_validator_probe(
            validator,
            rows[0],
            columns,
        )

        # ----------------------------------------------------------------------------------------
        # FULL 987 ROW EXECUTION
        # ----------------------------------------------------------------------------------------

        results = (
            execute_full_runtime_validation(
                validator,
                rows,
                columns,
            )
        )

        # ----------------------------------------------------------------------------------------
        # FINAL INTEGRITY
        # ----------------------------------------------------------------------------------------

        verify_integrity_unchanged(
            production_hash_before,
            database_hash_before,
            database_size_before,
        )

        # ----------------------------------------------------------------------------------------
        # FINAL
        # ----------------------------------------------------------------------------------------

        banner(
            "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
        )

        kv(
            "Runtime Rows",
            len(rows),
        )

        kv(
            "Validated Rows",
            len(results),
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
            "PRODUCTION MODULE NOT IMPORTED"
        )

        passed(
            "EXACT acquire_real_rows() EXECUTED"
        )

        passed(
            "EXACT trace_real_validation() "
            "CALL-SITE RESOLVED"
        )

        passed(
            "EXACT validate_row(row, columns) "
            "RESOLVED THROUGH PRODUCTION IMPORT BINDING"
        )

        passed(
            "EXACT validator AST compiled "
            "without importing production module"
        )

        passed(
            "FIRST-ROW REAL VALIDATOR PROBE PASS"
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
            "RUNTIME VALIDATION VERIFIED AT "
            "PRODUCTION acquire_real_rows() -> "
            "validate_row(row, columns) BOUNDARY"
        )

        print()
        print(
            "NEXT FRONTIER:"
        )

        print(
            "ELIGIBLE / REJECTED / REASON ANALYSIS"
        )

        print()
        print(
            "=" * 100
        )

        print(
            "ARUNDA TECHNICAL CONTRACT PRODUCTION "
            "RUNTIME VALIDATION v0.7 COMPLETE"
        )

    finally:

        try:
            conn.close()
        except Exception:
            pass


# ================================================================================================
# ENTRY POINT
# ================================================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print(
            "=" * 100
        )

        print(
            "FINAL STATUS           : FAIL"
        )

        print(
            "=" * 100
        )

        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()
        print(
            traceback.format_exc()
        )

        sys.exit(1)