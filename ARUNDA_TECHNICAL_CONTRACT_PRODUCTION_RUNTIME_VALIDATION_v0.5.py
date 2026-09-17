# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.5
====================================================================================================

PURPOSE
-------
Read-only runtime verification of the REAL TECHNICAL_v0.5 contract rows
through the REAL production validation boundary.

CRITICAL SAFETY RULES
---------------------
1. Production module is NEVER imported.
2. Production main() is NEVER executed.
3. Database is opened SQLite mode=ro.
4. PRAGMA query_only is explicitly forced to 1 and verified.
5. No INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / REPLACE.
6. Only AST-resolved production functions are compiled/executed.
7. acquire_real_rows() is executed against the REAL production database.
8. trace_real_validation() is inspected only to resolve the REAL validator call.
9. The REAL validator is executed exactly as:
       validate_row(row, columns)
10. No synthetic rows.
11. No reconstruction of production SQL by fragile string matching.
12. No eligible/rejected/reason inference is performed in this gate.
    This version only establishes that the REAL validator executes successfully.

NEXT GATE
---------
After this script reaches FINAL STATUS = PASS:

    987 REAL ROWS
        ↓
    REAL validate_row(row, columns)
        ↓
    eligible / rejected / reason / score / flags analysis

====================================================================================================
"""

import ast
import hashlib
import inspect
import os
import re
import sqlite3
import sys
import traceback
from collections import Counter


# ==================================================================================================
# CONFIGURATION
# ==================================================================================================

PRODUCTION_FILE = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\market_technical_validation_engine_v0.4.1.py"
)

DATABASE_FILE = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\arunda.db"
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

EXPECTED_TOTAL_ROWS = (
    EXPECTED_CONTRACT_ROWS +
    EXPECTED_MUSEUM_ROWS
)

EXPECTED_MIN_ID = 5923

EXPECTED_MAX_ID = 6909

# IMPORTANT:
# This is intentionally supplied independently from the production module.
# We do NOT import production constants.
TRACE_LIMIT = EXPECTED_CONTRACT_ROWS


# ==================================================================================================
# OUTPUT HELPERS
# ==================================================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def section(title):
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


# ==================================================================================================
# HASHING
# ==================================================================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# ==================================================================================================
# SOURCE
# ==================================================================================================

def read_production_source():
    with open(
        PRODUCTION_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


# ==================================================================================================
# AST DISCOVERY
# ==================================================================================================

def parse_production_source(source):
    return ast.parse(
        source,
        filename=PRODUCTION_FILE
    )


def top_level_functions(tree):
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


def resolve_unique_top_level_function(
    tree,
    name
):
    functions = top_level_functions(tree)

    nodes = functions.get(name, [])

    if len(nodes) != 1:
        failed(
            f"Expected exactly one top-level function "
            f"'{name}', found {len(nodes)}."
        )

    return nodes[0]


def function_source(
    source,
    node
):
    lines = source.splitlines(
        keepends=True
    )

    start = node.lineno - 1

    if getattr(
        node,
        "end_lineno",
        None
    ) is None:
        failed(
            f"AST node '{getattr(node, 'name', '?')}' "
            f"has no end_lineno."
        )

    end = node.end_lineno

    return "".join(
        lines[start:end]
    )


# ==================================================================================================
# SEMANTIC HASH
# ==================================================================================================

def normalized_ast_for_function(node):
    dumped = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False
    )

    return dumped


def semantic_function_sha256(node):
    return sha256_bytes(
        normalized_ast_for_function(node).encode(
            "utf-8"
        )
    )


# ==================================================================================================
# AST CALL DISCOVERY
# ==================================================================================================

class NameCallVisitor(ast.NodeVisitor):

    def __init__(self):
        self.calls = []

    def visit_Call(self, node):

        if isinstance(
            node.func,
            ast.Name
        ):
            self.calls.append(
                node
            )

        elif isinstance(
            node.func,
            ast.Attribute
        ):
            self.calls.append(
                node
            )

        self.generic_visit(node)


def find_calls(node):
    visitor = NameCallVisitor()
    visitor.visit(node)
    return visitor.calls


def call_name(call):
    if isinstance(
        call.func,
        ast.Name
    ):
        return call.func.id

    if isinstance(
        call.func,
        ast.Attribute
    ):
        return call.func.attr

    return None


# ==================================================================================================
# TRACE VALIDATOR CALL
# ==================================================================================================

def resolve_validator_call_from_trace(
    trace_node
):
    """
    Resolve the actual validator call from inside
    trace_real_validation().

    We do NOT assume validate_row() exists as a
    top-level FunctionDef.

    We require a real call with:

        validate_row(row, columns)

    """

    candidates = []

    for call in find_calls(trace_node):

        name = call_name(call)

        if name != VALIDATOR_SYMBOL:
            continue

        if len(call.args) != 2:
            continue

        first = call.args[0]
        second = call.args[1]

        if not (
            isinstance(first, ast.Name)
            and first.id == "row"
        ):
            continue

        if not (
            isinstance(second, ast.Name)
            and second.id == "columns"
        ):
            continue

        candidates.append(call)

    if len(candidates) != 1:
        failed(
            "Could not uniquely resolve REAL production "
            "validator call validate_row(row, columns). "
            f"Candidates found = {len(candidates)}"
        )

    call = candidates[0]

    print(
        f"Validator Call                                      : "
        f"{ast.unparse(call)}"
    )

    passed(
        "REAL validator call resolved from trace_real_validation()"
    )

    return call


# ==================================================================================================
# SYMBOL REFERENCE DISCOVERY
# ==================================================================================================

class NameLoadVisitor(ast.NodeVisitor):

    def __init__(self):
        self.names = []

    def visit_Name(self, node):

        if isinstance(
            node.ctx,
            ast.Load
        ):
            self.names.append(
                node.id
            )

        self.generic_visit(node)


def loaded_names(node):
    visitor = NameLoadVisitor()
    visitor.visit(node)
    return set(visitor.names)


# ==================================================================================================
# FUNCTION DEPENDENCY DISCOVERY
# ==================================================================================================

def all_function_nodes(tree):
    """
    Discover functions recursively, including nested
    functions.

    Returns:
        {
            function_name: [node, ...]
        }
    """

    result = {}

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):

            result.setdefault(
                node.name,
                []
            ).append(node)

            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):

            result.setdefault(
                node.name,
                []
            ).append(node)

            self.generic_visit(node)

    Visitor().visit(tree)

    return result


def find_validator_definitions(
    tree,
    name
):
    """
    Locate actual FunctionDef nodes named validate_row
    anywhere in production AST.

    This is deliberately separate from top-level lookup.
    """

    functions = all_function_nodes(tree)

    return functions.get(
        name,
        []
    )


# ==================================================================================================
# SAFE FUNCTION RESOLUTION
# ==================================================================================================

def resolve_real_validator(
    tree,
    trace_node,
    validator_call
):
    """
    Resolve the real validator.

    Resolution policy:

    A) First inspect the lexical scope around trace_real_validation.
    B) Then inspect module-level function definitions.
    C) If no unique actual FunctionDef exists, FAIL.

    We never invent a validator.
    """

    validator_name = call_name(
        validator_call
    )

    if validator_name != VALIDATOR_SYMBOL:
        failed(
            "Resolved call does not reference "
            f"{VALIDATOR_SYMBOL!r}."
        )

    definitions = find_validator_definitions(
        tree,
        VALIDATOR_SYMBOL
    )

    print()
    print(
        "Production validator definitions discovered:"
    )

    for node in definitions:

        print(
            f"  {VALIDATOR_SYMBOL}"
            f"  line={node.lineno}"
            f"  end={node.end_lineno}"
            f"  semantic_sha256="
            f"{semantic_function_sha256(node)}"
        )

    if len(definitions) == 0:

        failed(
            "REAL production validator symbol "
            f"'{VALIDATOR_SYMBOL}' was called by "
            "trace_real_validation(), but no corresponding "
            "FunctionDef exists anywhere in production AST."
        )

    if len(definitions) > 1:

        failed(
            "Ambiguous production validator resolution: "
            f"{len(definitions)} definitions named "
            f"'{VALIDATOR_SYMBOL}' found."
        )

    validator_node = definitions[0]

    passed(
        f"REAL production validator resolved: "
        f"{VALIDATOR_SYMBOL} "
        f"(line {validator_node.lineno})"
    )

    return validator_node


# ==================================================================================================
# CONSTANT / GLOBAL EXTRACTION
# ==================================================================================================

def literal_value(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def extract_literal_assignments(
    tree
):
    values = {}

    for node in tree.body:

        if isinstance(
            node,
            ast.Assign
        ):
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
                    values[
                        target.id
                    ] = value

        elif isinstance(
            node,
            ast.AnnAssign
        ):
            if not isinstance(
                node.target,
                ast.Name
            ):
                continue

            value = literal_value(
                node.value
            )

            if value is not None:
                values[
                    node.target.id
                ] = value

    return values


# ==================================================================================================
# SAFE RUNTIME NAMESPACE
# ==================================================================================================

def safe_runtime_namespace(
    tree
):
    """
    Build the smallest useful namespace without importing
    the production module.

    Production constants are NOT trusted blindly.

    Contract-critical constants are explicitly pinned to
    verified values.

    Helper functions are resolved separately.
    """

    namespace = {
        "__name__": "__arunda_runtime_validation__",
        "__file__": PRODUCTION_FILE,
        "__package__": None,

        # Contract constants
        "TARGET_TABLE": TARGET_TABLE,
        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,
        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,
        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,
        "TRACE_LIMIT":
            TRACE_LIMIT,

        # Common runtime helpers
        "Counter": Counter,
    }

    literal_values = extract_literal_assignments(
        tree
    )

    # Only bring in non-critical literals.
    # Critical contract values remain pinned above.

    protected = {
        "TARGET_TABLE",
        "CONTRACT_TECHNICAL_VERSION",
        "CONTRACT_ENGINE_VERSION",
        "CONTRACT_SOURCE",
        "TRACE_LIMIT",
    }

    for name, value in literal_values.items():

        if name in protected:
            continue

        namespace.setdefault(
            name,
            value
        )

    return namespace


# ==================================================================================================
# FUNCTION COMPILATION
# ==================================================================================================

def compile_exact_function(
    node,
    source,
    namespace
):
    """
    Compile exactly one AST function.

    No module import.
    No execution of surrounding module code.
    """

    module = ast.Module(
        body=[node],
        type_ignores=[]
    )

    ast.fix_missing_locations(
        module
    )

    code = compile(
        module,
        filename=PRODUCTION_FILE,
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
            f"Compiled function '{node.name}' "
            "is not callable."
        )

    return function


# ==================================================================================================
# REQUIRED HELPER RESOLUTION
# ==================================================================================================

def resolve_function_dependency(
    tree,
    name,
    namespace,
    source
):
    """
    Resolve a production helper by exact function name.

    Only used when the validator actually references it.

    Ambiguity = FAIL.
    """

    if name in namespace and callable(
        namespace[name]
    ):
        return namespace[name]

    definitions = find_validator_definitions(
        tree,
        name
    )

    if len(definitions) == 0:
        return None

    if len(definitions) > 1:
        failed(
            f"Ambiguous helper function '{name}': "
            f"{len(definitions)} definitions."
        )

    node = definitions[0]

    function = compile_exact_function(
        node,
        source,
        namespace
    )

    return function


def compile_function_with_dependencies(
    node,
    tree,
    source,
    namespace,
    seen=None
):
    """
    Compile the requested production function and its
    same-module function dependencies.

    This is deliberately conservative.

    Unknown names are NOT automatically imported.
    """

    if seen is None:
        seen = set()

    if node.name in seen:
        return namespace.get(
            node.name
        )

    seen.add(
        node.name
    )

    names = loaded_names(
        node
    )

    # Python builtins and known runtime names
    builtin_names = set(
        dir(__builtins__)
        if not isinstance(
            __builtins__,
            dict
        )
        else __builtins__.keys()
    )

    # Names that definitely do not represent function dependencies
    ignored = {
        "True",
        "False",
        "None",
    }

    # First resolve same-module function dependencies.
    for name in sorted(names):

        if name in ignored:
            continue

        if name in namespace:
            continue

        if name in builtin_names:
            continue

        definitions = find_validator_definitions(
            tree,
            name
        )

        if len(definitions) == 0:
            continue

        if len(definitions) > 1:
            failed(
                f"Ambiguous dependency '{name}': "
                f"{len(definitions)} definitions."
            )

        dependency = definitions[0]

        compile_function_with_dependencies(
            dependency,
            tree,
            source,
            namespace,
            seen
        )

    # Compile target itself after dependencies.
    function = compile_exact_function(
        node,
        source,
        namespace
    )

    return function


# ==================================================================================================
# DATABASE
# ==================================================================================================

def open_read_only_database():
    """
    Open SQLite in true read-only URI mode.

    query_only is then explicitly forced to ON and verified.
    """

    uri = (
        "file:"
        + DATABASE_FILE.replace(
            "\\",
            "/"
        )
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    # Explicitly force read-only SQL behavior at connection level.
    conn.execute(
        "PRAGMA query_only = ON"
    )

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if value != 1:
        conn.close()

        failed(
            "SQLite PRAGMA query_only could not be forced "
            "to 1."
        )

    passed(
        "SQLite query_only = 1"
    )

    return conn


# ==================================================================================================
# DATABASE INTEGRITY
# ==================================================================================================

def database_size():
    return os.path.getsize(
        DATABASE_FILE
    )


def database_preflight(
    conn
):
    section(
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
            "SQLite query_only != 1."
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
        )
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
        )
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
        )
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

    if total != EXPECTED_TOTAL_ROWS:
        failed(
            f"DATABASE TOTAL expected "
            f"{EXPECTED_TOTAL_ROWS}, got {total}"
        )

    if contract != EXPECTED_CONTRACT_ROWS:
        failed(
            f"CONTRACT expected "
            f"{EXPECTED_CONTRACT_ROWS}, got {contract}"
        )

    if museum != EXPECTED_MUSEUM_ROWS:
        failed(
            f"MUSEUM expected "
            f"{EXPECTED_MUSEUM_ROWS}, got {museum}"
        )

    if min_id != EXPECTED_MIN_ID:
        failed(
            f"CONTRACT MIN ID expected "
            f"{EXPECTED_MIN_ID}, got {min_id}"
        )

    if max_id != EXPECTED_MAX_ID:
        failed(
            f"CONTRACT MAX ID expected "
            f"{EXPECTED_MAX_ID}, got {max_id}"
        )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        failed(
            f"CONTRACT DISTINCT IDs expected "
            f"{EXPECTED_CONTRACT_ROWS}, got {distinct_ids}"
        )

    passed(
        f"DATABASE TOTAL = {EXPECTED_TOTAL_ROWS}"
    )

    passed(
        f"CONTRACT = {EXPECTED_CONTRACT_ROWS}"
    )

    passed(
        f"MUSEUM = {EXPECTED_MUSEUM_ROWS}"
    )

    passed(
        f"CONTRACT ID RANGE = "
        f"{EXPECTED_MIN_ID}..{EXPECTED_MAX_ID}"
    )


# ==================================================================================================
# EXACT acquire_real_rows() RUNTIME
# ==================================================================================================

def execute_acquire_real_rows(
    acquire_node,
    tree,
    source,
    conn
):
    section(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    namespace = safe_runtime_namespace(
        tree
    )

    # Contract constants are pinned explicitly.
    namespace[
        "TARGET_TABLE"
    ] = TARGET_TABLE

    namespace[
        "CONTRACT_TECHNICAL_VERSION"
    ] = CONTRACT_TECHNICAL_VERSION

    namespace[
        "CONTRACT_ENGINE_VERSION"
    ] = CONTRACT_ENGINE_VERSION

    namespace[
        "CONTRACT_SOURCE"
    ] = CONTRACT_SOURCE

    namespace[
        "TRACE_LIMIT"
    ] = TRACE_LIMIT

    acquire_function = compile_function_with_dependencies(
        acquire_node,
        tree,
        source,
        namespace
    )

    # The production function expects:
    #
    #   conn
    #   columns
    #   limit
    #
    # columns is not used by the actual acquisition SQL,
    # but we supply the real DB column list.

    columns = [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{TARGET_TABLE}")'
        ).fetchall()
    ]

    print(
        f"Runtime acquisition limit                         : "
        f"{TRACE_LIMIT}"
    )

    before_query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if before_query_only != 1:
        failed(
            "query_only was not 1 immediately before "
            "acquire_real_rows() execution."
        )

    rows = acquire_function(
        conn,
        columns,
        TRACE_LIMIT
    )

    if rows is None:
        failed(
            "Production acquire_real_rows() returned None."
        )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        failed(
            "Production acquire_real_rows() returned "
            f"{len(rows)} rows; expected "
            f"{EXPECTED_CONTRACT_ROWS}."
        )

    passed(
        "Exact production acquire_real_rows() executed"
    )

    passed(
        f"Runtime Contract rows = {len(rows)}"
    )

    return rows, columns


# ==================================================================================================
# RUNTIME ROW CONTRACT VERIFICATION
# ==================================================================================================

def verify_runtime_rows(
    rows
):
    section(
        "RUNTIME CONTRACT ROW VERIFICATION"
    )

    if not rows:
        failed(
            "No runtime rows returned."
        )

    first = rows[0]

    if not hasattr(
        first,
        "keys"
    ):
        failed(
            "Runtime row does not expose SQLite Row keys()."
        )

    required = {
        "id",
        "symbol",
        "timestamp",
        "technical_version",
        "engine_version",
        "source",
    }

    available = set(
        first.keys()
    )

    missing = required - available

    if missing:
        failed(
            "Runtime rows missing required fields: "
            f"{sorted(missing)}"
        )

    ids = [
        row["id"]
        for row in rows
    ]

    if len(ids) != len(
        set(ids)
    ):
        failed(
            "Runtime Contract IDs are not distinct."
        )

    if min(ids) != EXPECTED_MIN_ID:
        failed(
            f"Runtime MIN ID expected "
            f"{EXPECTED_MIN_ID}, got {min(ids)}"
        )

    if max(ids) != EXPECTED_MAX_ID:
        failed(
            f"Runtime MAX ID expected "
            f"{EXPECTED_MAX_ID}, got {max(ids)}"
        )

    if ids != sorted(
        ids,
        reverse=True
    ):
        failed(
            "Runtime rows are not ordered id DESC."
        )

    for row in rows:

        if row["technical_version"] != (
            CONTRACT_TECHNICAL_VERSION
        ):
            failed(
                "Runtime row outside technical_version contract."
            )

        if row["engine_version"] != (
            CONTRACT_ENGINE_VERSION
        ):
            failed(
                "Runtime row outside engine_version contract."
            )

        if row["source"] != CONTRACT_SOURCE:
            failed(
                "Runtime row outside source contract."
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


# ==================================================================================================
# EXACT VALIDATOR RUNTIME
# ==================================================================================================

def execute_real_validator(
    validator_node,
    trace_node,
    tree,
    source,
    rows,
    columns
):
    section(
        "REAL PRODUCTION VALIDATOR RESOLUTION + EXECUTION"
    )

    validator_call = resolve_validator_call_from_trace(
        trace_node
    )

    validator = compile_function_with_dependencies(
        validator_node,
        tree,
        source,
        safe_runtime_namespace(tree)
    )

    if not callable(
        validator
    ):
        failed(
            "Resolved production validator is not callable."
        )

    print()
    print(
        "Executing REAL validator exactly as:"
    )

    print(
        "    validate_row(row, columns)"
    )

    print()
    print(
        f"REAL Contract rows entering validator: "
        f"{len(rows)}"
    )

    results = []

    execution_errors = []

    for index, row in enumerate(
        rows,
        1
    ):

        try:

            # CRITICAL:
            # EXACT production invocation.
            result = validator(
                row,
                columns
            )

            results.append(
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
                    "timestamp": (
                        row["timestamp"]
                        if "timestamp" in row.keys()
                        else None
                    ),
                    "raw": result,
                }
            )

        except Exception as exc:

            execution_errors.append(
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

            print()
            print(
                f"[FAIL] Validator execution failed "
                f"at row {index}"
            )

            print(
                f"Exception: "
                f"{type(exc).__name__}: {exc}"
            )

            break

    if execution_errors:
        print()
        print(
            "FIRST VALIDATOR EXECUTION ERROR:"
        )

        print(
            execution_errors[0]["traceback"]
        )

        failed(
            "REAL production validator execution "
            f"failed at row "
            f"{execution_errors[0]['index']}."
        )

    if len(results) != len(rows):
        failed(
            "Validator result count does not match "
            "runtime Contract row count."
        )

    passed(
        "REAL validator resolved from production AST"
    )

    passed(
        "Exact invocation = validate_row(row, columns)"
    )

    passed(
        f"Validator calls = {len(results)}"
    )

    passed(
        "Validator execution errors = 0"
    )

    return results


# ==================================================================================================
# RESULT SHAPE
# ==================================================================================================

def inspect_validator_results(
    results
):
    section(
        "VALIDATOR RESULT SHAPE VERIFICATION"
    )

    if not results:
        failed(
            "Validator returned zero results."
        )

    shape_counter = Counter()

    for item in results:

        raw = item["raw"]

        if not isinstance(
            raw,
            tuple
        ):
            failed(
                "REAL validate_row() did not return tuple "
                f"at row {item['index']}. "
                f"Returned: {raw!r}"
            )

        shape_counter[
            len(raw)
        ] += 1

    print(
        "Validator tuple-length distribution:"
    )

    for length, count in sorted(
        shape_counter.items()
    ):
        print(
            f"  length={length:<5} count={count}"
        )

    # The production trace shown previously explicitly expects:
    #
    #     score, status, flags = result
    #
    # Therefore the runtime gate verifies exactly 3.
    if set(
        shape_counter.keys()
    ) != {3}:
        failed(
            "REAL validate_row() result shape is not "
            "the expected 3-tuple "
            "(score, status, flags)."
        )

    passed(
        "All 987 validator results are 3-tuples"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No eligible/rejected/reason classification "
        "is inferred in v0.5."
    )

    print(
        "The raw production validator results are preserved "
        "for the next analysis gate."
    )


# ==================================================================================================
# WRITE DETECTION
# ==================================================================================================

WRITE_SQL_RE = re.compile(
    r"""
    \b(
        INSERT
        |UPDATE
        |DELETE
        |REPLACE
        |CREATE
        |ALTER
        |DROP
        |VACUUM
        |REINDEX
        |ATTACH
        |DETACH
    )\b
    """,
    re.IGNORECASE |
    re.VERBOSE
)


def assert_no_write_sql_in_function(
    node
):
    source = ast.unparse(
        node
    )

    match = WRITE_SQL_RE.search(
        source
    )

    if match:
        failed(
            "Write SQL keyword detected inside "
            f"production function {node.name}: "
            f"{match.group(0)}"
        )


def assert_no_write_sql_in_target_functions(
    acquire_node,
    trace_node,
    validator_node
):
    section(
        "PRODUCTION FUNCTION WRITE SAFETY"
    )

    for node in (
        acquire_node,
        trace_node,
        validator_node,
    ):
        assert_no_write_sql_in_function(
            node
        )

    passed(
        "No SQL write operation detected in target functions"
    )


# ==================================================================================================
# SOURCE INTEGRITY
# ==================================================================================================

def verify_source_unchanged(
    before_hash
):
    after_hash = sha256_file(
        PRODUCTION_FILE
    )

    section(
        "PRODUCTION SOURCE INTEGRITY AFTER RUNTIME"
    )

    kv(
        "Production SHA256 BEFORE",
        before_hash
    )

    kv(
        "Production SHA256 AFTER",
        after_hash
    )

    if after_hash != before_hash:
        failed(
            "Production source changed during runtime verification."
        )

    passed(
        "Production source unchanged"
    )

    return after_hash


# ==================================================================================================
# DATABASE INTEGRITY
# ==================================================================================================

def verify_database_unchanged(
    before_size,
    before_hash
):
    after_size = database_size()

    after_hash = sha256_file(
        DATABASE_FILE
    )

    section(
        "DATABASE INTEGRITY AFTER RUNTIME"
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
        before_hash
    )

    kv(
        "Database SHA256 AFTER",
        after_hash
    )

    if after_size != before_size:
        failed(
            "Database size changed during runtime validation."
        )

    if after_hash != before_hash:
        failed(
            "Database SHA256 changed during runtime validation."
        )

    passed(
        "Database size unchanged"
    )

    passed(
        "Database SHA256 unchanged"
    )


# ==================================================================================================
# FINAL
# ==================================================================================================

def final_report(
    rows,
    validator_results
):
    section(
        "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
    )

    ids = [
        row["id"]
        for row in rows
    ]

    kv(
        "Runtime Rows",
        len(rows)
    )

    kv(
        "Validator Calls",
        len(validator_results)
    )

    kv(
        "Runtime Distinct IDs",
        len(set(ids))
    )

    kv(
        "Runtime MIN ID",
        min(ids)
    )

    kv(
        "Runtime MAX ID",
        max(ids)
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
        "Production main() NOT EXECUTED"
    )

    passed(
        "Production module NOT IMPORTED"
    )

    passed(
        "Exact acquire_real_rows() EXECUTED"
    )

    passed(
        "Contract scope active at runtime"
    )

    passed(
        "987 REAL Contract rows acquired"
    )

    passed(
        "REAL validate_row(row, columns) resolved"
    )

    passed(
        "REAL validator executed"
    )

    passed(
        "987/987 rows reached validator"
    )

    passed(
        "Validator execution errors = 0"
    )

    passed(
        "No database write path used"
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
        "TECHNICAL CONTRACT v0.5"
    )

    print(
        "REAL PRODUCTION VALIDATOR RUNTIME VERIFIED"
    )

    print()
    print(
        "NEXT FRONTIER:"
    )

    print(
        "987 REAL validator results -> "
        "eligible / rejected / reason / score / flags"
    )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.5"
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
        TARGET_FUNCTION
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
        "Production module will NOT be imported."
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

    # ----------------------------------------------------------------------------------------------
    # SOURCE BEFORE
    # ----------------------------------------------------------------------------------------------

    production_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    database_hash_before = sha256_file(
        DATABASE_FILE
    )

    database_size_before = database_size()

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

    # ----------------------------------------------------------------------------------------------
    # SOURCE / AST
    # ----------------------------------------------------------------------------------------------

    source = read_production_source()

    tree = parse_production_source(
        source
    )

    acquire_node = resolve_unique_top_level_function(
        tree,
        TARGET_FUNCTION
    )

    trace_node = resolve_unique_top_level_function(
        tree,
        TRACE_FUNCTION
    )

    section(
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

    print()

    print(
        "EXACT PRODUCTION acquire_real_rows():"
    )

    print(
        function_source(
            source,
            acquire_node
        )
    )

    print(
        "EXACT PRODUCTION trace_real_validation():"
    )

    print(
        function_source(
            source,
            trace_node
        )
    )

    # ----------------------------------------------------------------------------------------------
    # TRACE -> VALIDATOR
    # ----------------------------------------------------------------------------------------------

    section(
        "REAL PRODUCTION VALIDATOR RESOLUTION"
    )

    validator_call = resolve_validator_call_from_trace(
        trace_node
    )

    validator_node = resolve_real_validator(
        tree,
        trace_node,
        validator_call
    )

    print()

    print(
        "EXACT REAL PRODUCTION VALIDATOR:"
    )

    print(
        function_source(
            source,
            validator_node
        )
    )

    # ----------------------------------------------------------------------------------------------
    # WRITE SAFETY
    # ----------------------------------------------------------------------------------------------

    assert_no_write_sql_in_target_functions(
        acquire_node,
        trace_node,
        validator_node
    )

    # ----------------------------------------------------------------------------------------------
    # DB
    # ----------------------------------------------------------------------------------------------

    conn = None

    try:

        conn = open_read_only_database()

        database_preflight(
            conn
        )

        # ------------------------------------------------------------------------------------------
        # EXACT ACQUISITION
        # ------------------------------------------------------------------------------------------

        rows, columns = execute_acquire_real_rows(
            acquire_node,
            tree,
            source,
            conn
        )

        verify_runtime_rows(
            rows
        )

        # ------------------------------------------------------------------------------------------
        # EXACT VALIDATOR
        # ------------------------------------------------------------------------------------------

        validator_results = execute_real_validator(
            validator_node,
            trace_node,
            tree,
            source,
            rows,
            columns
        )

        inspect_validator_results(
            validator_results
        )

        # ------------------------------------------------------------------------------------------
        # query_only must remain active after execution
        # ------------------------------------------------------------------------------------------

        query_only_after = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        if query_only_after != 1:
            failed(
                "SQLite query_only was not 1 after runtime execution."
            )

        passed(
            "SQLite query_only remained = 1 after runtime"
        )

    finally:

        if conn is not None:
            conn.close()

    # ----------------------------------------------------------------------------------------------
    # SOURCE / DATABASE INTEGRITY
    # ----------------------------------------------------------------------------------------------

    verify_source_unchanged(
        production_hash_before
    )

    verify_database_unchanged(
        database_size_before,
        database_hash_before
    )

    # ----------------------------------------------------------------------------------------------
    # FINAL
    # ----------------------------------------------------------------------------------------------

    final_report(
        rows,
        validator_results
    )


# ==================================================================================================
# ENTRY POINT
# ==================================================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print("=" * 100)
        print(
            "FINAL STATUS           : FAIL"
        )
        print("=" * 100)

        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()
        traceback.print_exc()

        sys.exit(1)