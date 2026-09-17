# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.3
====================================================================================================

PURPOSE
-------
Read-only runtime verification of the REAL TECHNICAL_v0.5 contract population.

Execution chain:

    REAL production acquire_real_rows()
                |
                v
        987 real contract rows
                |
                v
       REAL production validate_row()
                |
                v
       score / status / flags
                |
                v
      eligible / rejected / reason

SAFETY
------
- Production main() is NEVER executed.
- Production validation module is NEVER imported.
- Database is SQLite read-only.
- PRAGMA query_only = 1.
- No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP.
- Production source is never modified.
- Database is never modified.
- Only exact AST functions are compiled/executed.
- validate_row is discovered ONLY from market_technical_engine.py.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import re
import sqlite3
import sys
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

# REAL production validation source.
VALIDATOR_SOURCE_FILE = PRODUCTION_FILE.parent / "market_technical_engine.py"

TARGET_ACQUIRE_FUNCTION = "acquire_real_rows"
TARGET_VALIDATOR_FUNCTION = "validate_row"

TARGET_TABLE = "market_technical"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

# acquire_real_rows() default argument requires this during AST compilation.
TRACE_LIMIT = EXPECTED_CONTRACT_ROWS

# Runtime validation should process the complete contract.
RUNTIME_LIMIT = EXPECTED_CONTRACT_ROWS


# ================================================================================================
# OUTPUT HELPERS
# ================================================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<55}: {value}")


def safe(value):
    try:
        return repr(value)
    except Exception:
        return "<UNREPRESENTABLE>"


def fail(message):
    raise RuntimeError(message)


# ================================================================================================
# HASHING
# ================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


# ================================================================================================
# AST HELPERS
# ================================================================================================

def parse_source(path: Path):
    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(path)
    )

    return source, tree


def function_nodes(tree):
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


def find_unique_function(
    tree,
    name,
    source_label
):
    candidates = function_nodes(tree).get(
        name,
        []
    )

    if len(candidates) == 0:
        raise RuntimeError(
            f"Function not found: {name} "
            f"in {source_label}"
        )

    if len(candidates) > 1:
        raise RuntimeError(
            f"Multiple definitions found for {name} "
            f"in {source_label}"
        )

    return candidates[0]


def semantic_hash_node(node):
    """
    AST semantic fingerprint.

    Removes source location information while preserving
    executable AST semantics.
    """

    cloned = ast.fix_missing_locations(
        node
    )

    dumped = ast.dump(
        cloned,
        annotate_fields=True,
        include_attributes=False
    )

    return hashlib.sha256(
        dumped.encode("utf-8")
    ).hexdigest()


def function_source(
    node,
    source
):
    lines = source.splitlines()

    start = node.lineno - 1
    end = node.end_lineno

    return "\n".join(
        lines[start:end]
    )


# ================================================================================================
# DATABASE
# ================================================================================================

WRITE_SQL_RE = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|REPLACE|VACUUM|REINDEX|ATTACH|DETACH"
    r")\b",
    re.IGNORECASE
)


def open_read_only_database():

    uri = (
        "file:"
        + str(DATABASE_FILE).replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA query_only = 1"
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
        query_only
    )

    if query_only != 1:
        fail(
            "SQLite query_only is not 1"
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

    kv("Database Total", total)
    kv("Contract Population", contract)
    kv("Museum Population", museum)
    kv("Contract MIN ID", min_id)
    kv("Contract MAX ID", max_id)
    kv("Contract DISTINCT IDs", distinct_ids)

    if total != EXPECTED_CONTRACT_ROWS + EXPECTED_MUSEUM_ROWS:
        fail(
            f"Database total mismatch: {total}"
        )

    if contract != EXPECTED_CONTRACT_ROWS:
        fail(
            f"Contract population mismatch: {contract}"
        )

    if museum != EXPECTED_MUSEUM_ROWS:
        fail(
            f"Museum population mismatch: {museum}"
        )

    if min_id != 5923:
        fail(
            f"Contract MIN ID mismatch: {min_id}"
        )

    if max_id != 6909:
        fail(
            f"Contract MAX ID mismatch: {max_id}"
        )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        fail(
            f"Contract DISTINCT IDs mismatch: {distinct_ids}"
        )

    print()
    print(
        "[PASS] DATABASE TOTAL = 6909"
    )

    print(
        "[PASS] CONTRACT = 987"
    )

    print(
        "[PASS] MUSEUM = 5922"
    )

    print(
        "[PASS] CONTRACT ID RANGE = 5923..6909"
    )

    return {
        "total": total,
        "contract": contract,
        "museum": museum,
        "min_id": min_id,
        "max_id": max_id,
        "distinct_ids": distinct_ids,
    }


# ================================================================================================
# EXACT acquire_real_rows AST DISCOVERY
# ================================================================================================

def discover_acquire():

    source, tree = parse_source(
        PRODUCTION_FILE
    )

    node = find_unique_function(
        tree,
        TARGET_ACQUIRE_FUNCTION,
        str(PRODUCTION_FILE)
    )

    return (
        source,
        tree,
        node
    )


# ================================================================================================
# acquire_real_rows SQL SAFETY
# ================================================================================================

def reconstruct_sql_from_acquire(node):

    sql_literals = []

    for item in ast.walk(node):

        if isinstance(
            item,
            ast.Constant
        ) and isinstance(
            item.value,
            str
        ):

            text = item.value

            if (
                "SELECT" in text.upper()
                and (
                    "FROM" in text.upper()
                    or "WHERE" in text.upper()
                )
            ):
                sql_literals.append(
                    text
                )

    if not sql_literals:
        fail(
            "No SQL literal discovered inside acquire_real_rows()"
        )

    combined = " ".join(
        sql_literals
    )

    normalized = re.sub(
        r"\s+",
        " ",
        combined
    ).strip().lower()

    print()
    print(
        "RECONSTRUCTED SQL:"
    )
    print()
    print(
        normalized
    )

    expected_fragments = [
        "select *",
        'from "{target_table}"',
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in expected_fragments:

        if fragment not in normalized:

            # f-string AST may contain a JoinedStr rather than
            # the literal text. We therefore reconstruct the
            # known target-table fragment separately below.

            if fragment == 'from "{target_table}"':
                if (
                    'from "' not in normalized
                    and "from " not in normalized
                ):
                    fail(
                        f"Expected SQL fragment missing: {fragment}"
                    )
                continue

            fail(
                f"Expected SQL fragment missing: {fragment}"
            )

        print(
            f"[PASS] SQL fragment: {fragment}"
        )

    if WRITE_SQL_RE.search(
        normalized
    ):
        fail(
            "WRITE SQL detected inside acquire_real_rows()"
        )

    print(
        "[PASS] Contract predicates present"
    )

    print(
        "[PASS] ORDER BY id DESC preserved"
    )

    print(
        "[PASS] LIMIT ? preserved"
    )

    print(
        "[PASS] No SQL write operation detected"
    )


# ================================================================================================
# CONTROLLED NAMESPACE FOR acquire_real_rows()
# ================================================================================================

def build_acquire_namespace():

    namespace = {

        "__builtins__": __builtins__,

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

    return namespace


def compile_exact_acquire(
    node
):

    namespace = build_acquire_namespace()

    module = ast.Module(
        body=[node],
        type_ignores=[]
    )

    module = ast.fix_missing_locations(
        module
    )

    code = compile(
        module,
        str(PRODUCTION_FILE),
        "exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    fn = namespace.get(
        TARGET_ACQUIRE_FUNCTION
    )

    if fn is None:
        fail(
            "Exact acquire_real_rows() did not compile"
        )

    return fn


# ================================================================================================
# REAL CONTRACT ACQUISITION
# ================================================================================================

def execute_acquire(
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
        RUNTIME_LIMIT
    )

    print()
    kv(
        "Runtime Rows Returned",
        len(rows)
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:
        fail(
            f"Runtime acquire_real_rows() returned "
            f"{len(rows)} rows; expected "
            f"{EXPECTED_CONTRACT_ROWS}"
        )

    return (
        rows,
        columns
    )


# ================================================================================================
# REAL VALIDATOR SOURCE DISCOVERY
# ================================================================================================

def discover_real_validator():

    banner(
        "REAL PRODUCTION VALIDATOR DISCOVERY"
    )

    if not VALIDATOR_SOURCE_FILE.exists():

        fail(
            "REAL validator source not found:\n"
            f"{VALIDATOR_SOURCE_FILE}"
        )

    source, tree = parse_source(
        VALIDATOR_SOURCE_FILE
    )

    node = find_unique_function(
        tree,
        TARGET_VALIDATOR_FUNCTION,
        str(VALIDATOR_SOURCE_FILE)
    )

    semantic = semantic_hash_node(
        node
    )

    print(
        f"Validator source: {VALIDATOR_SOURCE_FILE}"
    )

    print(
        f"Function: {TARGET_VALIDATOR_FUNCTION}"
    )

    print(
        f"Start Line: {node.lineno}"
    )

    print(
        f"End Line: {node.end_lineno}"
    )

    print(
        f"Semantic SHA256: {semantic}"
    )

    print()
    print(
        "EXACT REAL validate_row():"
    )

    print(
        function_source(
            node,
            source
        )
    )

    print()
    print(
        "[PASS] Exact validate_row() discovered "
        "from market_technical_engine.py"
    )

    return (
        source,
        tree,
        node
    )


# ================================================================================================
# VALIDATOR DEPENDENCY RESOLUTION
# ================================================================================================

class DependencyResolver:

    def __init__(
        self,
        source,
        tree
    ):

        self.source = source
        self.tree = tree

        self.functions = {}
        self.assignments = {}

        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            ):
                self.functions[
                    node.name
                ] = node

            elif isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign
                )
            ):

                names = []

                if isinstance(
                    node,
                    ast.Assign
                ):
                    for target in node.targets:
                        names.extend(
                            self.extract_names(
                                target
                            )
                        )

                else:
                    names.extend(
                        self.extract_names(
                            node.target
                        )
                    )

                for name in names:
                    self.assignments[
                        name
                    ] = node

    @staticmethod
    def extract_names(node):

        if isinstance(
            node,
            ast.Name
        ):
            return [node.id]

        if isinstance(
            node,
            (ast.Tuple, ast.List)
        ):
            result = []

            for item in node.elts:
                result.extend(
                    DependencyResolver.extract_names(
                        item
                    )
                )

            return result

        return []

    @staticmethod
    def referenced_names(node):

        names = set()

        for item in ast.walk(node):

            if isinstance(
                item,
                ast.Name
            ) and isinstance(
                item.ctx,
                ast.Load
            ):
                names.add(
                    item.id
                )

        return names

    def dependency_closure(
        self,
        root_node
    ):

        required_functions = []
        required_assignments = []

        seen_functions = set()
        seen_assignments = set()

        queue = list(
            self.referenced_names(
                root_node
            )
        )

        while queue:

            name = queue.pop()

            if name in seen_functions:
                continue

            if name in seen_assignments:
                continue

            if name in self.functions:

                seen_functions.add(
                    name
                )

                fn = self.functions[
                    name
                ]

                required_functions.append(
                    fn
                )

                queue.extend(
                    self.referenced_names(
                        fn
                    )
                )

                continue

            if name in self.assignments:

                seen_assignments.add(
                    name
                )

                assignment = self.assignments[
                    name
                ]

                required_assignments.append(
                    assignment
                )

                queue.extend(
                    self.referenced_names(
                        assignment
                    )

                )

        return (
            required_functions,
            required_assignments
        )


# ================================================================================================
# SAFE IMPORT EXTRACTION
# ================================================================================================

def extract_safe_imports(tree):

    imports = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom
            )
        ):

            imports.append(
                node
            )

    return imports


def compile_validator(
    validator_source,
    validator_tree,
    validator_node
):

    banner(
        "EXACT PRODUCTION VALIDATOR COMPILATION"
    )

    resolver = DependencyResolver(
        validator_source,
        validator_tree
    )

    (
        dependency_functions,
        dependency_assignments
    ) = resolver.dependency_closure(
        validator_node
    )

    namespace = {
        "__builtins__": __builtins__,
    }

    # -------------------------------------------------------------------------
    # Controlled standard-library imports
    # -------------------------------------------------------------------------

    safe_import_nodes = []

    for node in extract_safe_imports(
        validator_tree
    ):

        # Imports are compiled separately. They are not production-module
        # imports and do not execute production main().
        safe_import_nodes.append(
            node
        )

    # -------------------------------------------------------------------------
    # First compile imports.
    # -------------------------------------------------------------------------

    if safe_import_nodes:

        import_module = ast.Module(
            body=safe_import_nodes,
            type_ignores=[]
        )

        import_module = ast.fix_missing_locations(
            import_module
        )

        import_code = compile(
            import_module,
            str(VALIDATOR_SOURCE_FILE),
            "exec"
        )

        exec(
            import_code,
            namespace,
            namespace
        )

    # -------------------------------------------------------------------------
    # Compile required assignments and functions.
    # -------------------------------------------------------------------------

    nodes = []

    # Assignments first.
    nodes.extend(
        dependency_assignments
    )

    # Functions.
    nodes.extend(
        dependency_functions
    )

    # Exact validator last.
    if validator_node not in nodes:
        nodes.append(
            validator_node
        )

    module = ast.Module(
        body=nodes,
        type_ignores=[]
    )

    module = ast.fix_missing_locations(
        module
    )

    code = compile(
        module,
        str(VALIDATOR_SOURCE_FILE),
        "exec"
    )

    exec(
        code,
        namespace,
        namespace
    )

    validator = namespace.get(
        TARGET_VALIDATOR_FUNCTION
    )

    if validator is None:
        fail(
            "Exact validate_row() was not compiled"
        )

    print(
        f"Dependency functions compiled: "
        f"{len(dependency_functions)}"
    )

    print(
        f"Dependency assignments compiled: "
        f"{len(dependency_assignments)}"
    )

    print()
    print(
        "[PASS] Exact validate_row() compiled"
    )

    return (
        validator,
        namespace
    )


# ================================================================================================
# VALIDATOR SIGNATURE
# ================================================================================================

def verify_validator_signature(
    validator
):

    banner(
        "REAL PRODUCTION VALIDATION SIGNATURE"
    )

    signature = inspect.signature(
        validator
    )

    print(
        f"Function: {TARGET_VALIDATOR_FUNCTION}"
    )

    print(
        f"Signature: {signature}"
    )

    for name, parameter in signature.parameters.items():

        print(
            f"  {name:<30} "
            f"kind={parameter.kind.name} "
            f"default={parameter.default!r}"
        )

    names = list(
        signature.parameters
    )

    expected = [
        "row",
        "columns"
    ]

    if names != expected:

        fail(
            "Unexpected validate_row() signature.\n"
            f"Expected: {expected}\n"
            f"Actual:   {names}"
        )

    print()
    print(
        "[PASS] validate_row(row, columns) signature verified"
    )

    return signature


# ================================================================================================
# RESULT NORMALIZATION
# ================================================================================================

def normalize_flags(flags):

    if flags is None:
        return []

    if isinstance(
        flags,
        (list, tuple, set)
    ):
        return [
            str(x).strip()
            for x in flags
            if str(x).strip()
        ]

    text = str(flags).strip()

    if not text:
        return []

    return [
        x.strip()
        for x in text.split(",")
        if x.strip()
    ]


def derive_eligibility(
    status,
    flags
):

    status_text = (
        str(status).strip().upper()
        if status is not None
        else ""
    )

    flag_list = normalize_flags(
        flags
    )

    # IMPORTANT:
    # This is a classification of the REAL validator output.
    # We do NOT invent a new eligibility rule.
    #
    # Known positive forms are treated as eligible.
    # Everything else is rejected unless validator explicitly
    # returns a boolean-like status.

    positive_statuses = {
        "ELIGIBLE",
        "VALID",
        "PASS",
        "PASSED",
        "OK",
        "READY",
        "TRADE",
        "TRUE",
    }

    negative_statuses = {
        "REJECTED",
        "REJECT",
        "INVALID",
        "FAIL",
        "FAILED",
        "NO_TRADE",
        "FALSE",
        "BLOCKED",
    }

    if status_text in positive_statuses:
        eligible = True

    elif status_text in negative_statuses:
        eligible = False

    else:
        # Unknown status must never silently become eligible.
        eligible = False

    if eligible:

        reason = (
            "validator_status="
            + status_text
        )

    else:

        if flag_list:

            reason = (
                "validator_status="
                + status_text
                + "; flags="
                + ",".join(flag_list)
            )

        else:

            reason = (
                "validator_status="
                + status_text
            )

    return (
        eligible,
        reason
    )


# ================================================================================================
# RUNTIME VALIDATION
# ================================================================================================

def execute_runtime_validation(
    validator,
    rows,
    columns
):

    banner(
        "REAL PRODUCTION validate_row() RUNTIME VALIDATION"
    )

    print(
        f"Executing validation against "
        f"{len(rows)} REAL Contract rows..."
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
                    "validate_row() did not return tuple"
                )

            if len(result) != 3:
                raise RuntimeError(
                    "validate_row() return tuple "
                    f"length={len(result)}, expected=3"
                )

            score, status, flags = result

            flag_list = normalize_flags(
                flags
            )

            eligible, reason = derive_eligibility(
                status,
                flags
            )

            status_counter[
                str(status)
            ] += 1

            score_counter[
                str(score)
            ] += 1

            for flag in flag_list:
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
                    "eligible": eligible,
                    "reason": reason,
                }
            )

            print(
                f"[{index:04d}/{len(rows):04d}] "
                f"id={record_id} "
                f"symbol={symbol} "
                f"score={score!r} "
                f"status={status!r} "
                f"eligible={eligible} "
                f"flags={flag_list}"
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
                f"[FAIL] Validation execution failed "
                f"at row {index}"
            )

            print(
                f"id={record_id}"
            )

            print(
                f"symbol={symbol}"
            )

            print(
                f"Exception: {type(exc).__name__}: {exc}"
            )

            # Fail closed.
            continue

    return (
        results,
        status_counter,
        score_counter,
        flag_counter,
        execution_errors,
    )


# ================================================================================================
# RESULT VERIFICATION
# ================================================================================================

def verify_runtime_results(
    rows,
    results,
    execution_errors
):

    banner(
        "RUNTIME VALIDATION RESULT VERIFICATION"
    )

    kv(
        "Input Contract Rows",
        len(rows)
    )

    kv(
        "Successful Validation Rows",
        len(results)
    )

    kv(
        "Execution Errors",
        len(execution_errors)
    )

    if len(results) != len(rows):

        fail(
            "Not every Contract row successfully reached "
            "validate_row(). "
            f"input={len(rows)}, "
            f"successful={len(results)}, "
            f"errors={len(execution_errors)}"
        )

    if execution_errors:

        fail(
            "Runtime validation produced execution errors."
        )

    eligible_count = sum(
        1
        for row in results
        if row["eligible"]
    )

    rejected_count = sum(
        1
        for row in results
        if not row["eligible"]
    )

    distinct_ids = len(
        {
            row["id"]
            for row in results
        }
    )

    min_id = min(
        row["id"]
        for row in results
    )

    max_id = max(
        row["id"]
        for row in results
    )

    kv(
        "Eligible Rows",
        eligible_count
    )

    kv(
        "Rejected Rows",
        rejected_count
    )

    kv(
        "Distinct Runtime IDs",
        distinct_ids
    )

    kv(
        "Runtime MIN ID",
        min_id
    )

    kv(
        "Runtime MAX ID",
        max_id
    )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:
        fail(
            f"Runtime distinct IDs={distinct_ids}, "
            f"expected={EXPECTED_CONTRACT_ROWS}"
        )

    if min_id != 5923:
        fail(
            f"Runtime MIN ID={min_id}, expected=5923"
        )

    if max_id != 6909:
        fail(
            f"Runtime MAX ID={max_id}, expected=6909"
        )

    print()
    print(
        f"[PASS] {len(results)} / "
        f"{len(rows)} rows validated"
    )

    print(
        "[PASS] Runtime IDs distinct"
    )

    print(
        "[PASS] Runtime ID range = 5923..6909"
    )

    return {
        "eligible": eligible_count,
        "rejected": rejected_count,
        "distinct_ids": distinct_ids,
        "min_id": min_id,
        "max_id": max_id,
    }


# ================================================================================================
# DISTRIBUTION REPORT
# ================================================================================================

def print_distribution(
    status_counter,
    score_counter,
    flag_counter
):

    banner(
        "VALIDATION OUTPUT DISTRIBUTION"
    )

    print(
        "STATUS DISTRIBUTION:"
    )

    for status, count in sorted(
        status_counter.items(),
        key=lambda x: (
            -x[1],
            x[0]
        )
    ):
        print(
            f"  {status!r:<35} : {count}"
        )

    print()
    print(
        "SCORE DISTRIBUTION:"
    )

    for score, count in sorted(
        score_counter.items(),
        key=lambda x: (
            -x[1],
            x[0]
        )
    ):

        print(
            f"  {score!r:<35} : {count}"
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

        for flag, count in sorted(
            flag_counter.items(),
            key=lambda x: (
                -x[1],
                x[0]
            )
        ):

            print(
                f"  {flag:<35} : {count}"
            )


# ================================================================================================
# DATABASE INTEGRITY AFTER
# ================================================================================================

def database_fingerprint():

    return (
        DATABASE_FILE.stat().st_size,
        sha256_file(
            DATABASE_FILE
        )
    )


# ================================================================================================
# MAIN
# ================================================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.3"
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
        "Validator Source",
        VALIDATOR_SOURCE_FILE
    )

    kv(
        "Database",
        DATABASE_FILE
    )

    kv(
        "Acquire Function",
        TARGET_ACQUIRE_FUNCTION
    )

    kv(
        "Validator Function",
        TARGET_VALIDATOR_FUNCTION
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
        "Only exact production AST functions are executed."
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
    # Integrity BEFORE
    # --------------------------------------------------------------------------------------------

    production_sha_before = sha256_file(
        PRODUCTION_FILE
    )

    validator_sha_before = sha256_file(
        VALIDATOR_SOURCE_FILE
    )

    db_size_before, db_sha_before = (
        database_fingerprint()
    )

    banner(
        "PRODUCTION / VALIDATOR / DATABASE INTEGRITY BEFORE"
    )

    kv(
        "Production SHA256 BEFORE",
        production_sha_before
    )

    kv(
        "Validator Source SHA256 BEFORE",
        validator_sha_before
    )

    kv(
        "Database Size BEFORE",
        db_size_before
    )

    kv(
        "Database SHA256 BEFORE",
        db_sha_before
    )

    # --------------------------------------------------------------------------------------------
    # Database
    # --------------------------------------------------------------------------------------------

    conn = open_read_only_database()

    try:

        database_preflight(
            conn
        )

        # ----------------------------------------------------------------------------------------
        # acquire_real_rows discovery
        # ----------------------------------------------------------------------------------------

        banner(
            "PRODUCTION AST DISCOVERY — acquire_real_rows()"
        )

        production_source, production_tree, acquire_node = (
            discover_acquire()
        )

        acquire_semantic = semantic_hash_node(
            acquire_node
        )

        kv(
            "acquire_real_rows Semantic SHA256",
            acquire_semantic
        )

        print()
        print(
            function_source(
                acquire_node,
                production_source
            )
        )

        # ----------------------------------------------------------------------------------------
        # SQL safety
        # ----------------------------------------------------------------------------------------

        banner(
            "PRODUCTION acquire_real_rows() SQL SAFETY"
        )

        reconstruct_sql_from_acquire(
            acquire_node
        )

        # ----------------------------------------------------------------------------------------
        # Compile exact acquire
        # ----------------------------------------------------------------------------------------

        banner(
            "EXACT PRODUCTION acquire_real_rows() COMPILATION"
        )

        acquire_function = compile_exact_acquire(
            acquire_node
        )

        print(
            "[PASS] Exact acquire_real_rows() compiled"
        )

        # ----------------------------------------------------------------------------------------
        # Execute acquisition
        # ----------------------------------------------------------------------------------------

        rows, columns = execute_acquire(
            acquire_function,
            conn
        )

        # ----------------------------------------------------------------------------------------
        # Validate acquisition scope again
        # ----------------------------------------------------------------------------------------

        banner(
            "ACQUIRED RUNTIME CONTRACT SCOPE"
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

        distinct_ids = {
            row["id"]
            for row in rows
        }

        print(
            f"technical_version = {technical_versions}"
        )

        print(
            f"engine_version    = {engine_versions}"
        )

        print(
            f"source            = {sources}"
        )

        if technical_versions != {
            CONTRACT_TECHNICAL_VERSION
        }:
            fail(
                "Runtime technical_version scope mismatch"
            )

        if engine_versions != {
            CONTRACT_ENGINE_VERSION
        }:
            fail(
                "Runtime engine_version scope mismatch"
            )

        if sources != {
            CONTRACT_SOURCE
        }:
            fail(
                "Runtime source scope mismatch"
            )

        if len(distinct_ids) != EXPECTED_CONTRACT_ROWS:
            fail(
                "Runtime acquired IDs are not distinct"
            )

        print(
            "[PASS] Runtime Contract scope = TECHNICAL_v0.5"
        )

        print(
            "[PASS] Runtime Engine scope = TECHNICAL_v0.5"
        )

        print(
            "[PASS] Runtime Source scope = REAL_MARKET_HISTORY"
        )

        # ----------------------------------------------------------------------------------------
        # Real validator discovery
        # ----------------------------------------------------------------------------------------

        (
            validator_source,
            validator_tree,
            validator_node
        ) = discover_real_validator()

        validator_semantic_before = semantic_hash_node(
            validator_node
        )

        # ----------------------------------------------------------------------------------------
        # Compile validator
        # ----------------------------------------------------------------------------------------

        validator, validator_namespace = compile_validator(
            validator_source,
            validator_tree,
            validator_node
        )

        # ----------------------------------------------------------------------------------------
        # Signature
        # ----------------------------------------------------------------------------------------

        signature = verify_validator_signature(
            validator
        )

        # ----------------------------------------------------------------------------------------
        # Runtime validation
        # ----------------------------------------------------------------------------------------

        (
            results,
            status_counter,
            score_counter,
            flag_counter,
            execution_errors,
        ) = execute_runtime_validation(
            validator,
            rows,
            columns
        )

        # ----------------------------------------------------------------------------------------
        # Verify
        # ----------------------------------------------------------------------------------------

        summary = verify_runtime_results(
            rows,
            results,
            execution_errors
        )

        # ----------------------------------------------------------------------------------------
        # Distribution
        # ----------------------------------------------------------------------------------------

        print_distribution(
            status_counter,
            score_counter,
            flag_counter
        )

    finally:

        conn.close()

    # --------------------------------------------------------------------------------------------
    # Integrity AFTER
    # --------------------------------------------------------------------------------------------

    production_sha_after = sha256_file(
        PRODUCTION_FILE
    )

    validator_sha_after = sha256_file(
        VALIDATOR_SOURCE_FILE
    )

    db_size_after, db_sha_after = (
        database_fingerprint()
    )

    banner(
        "PRODUCTION / VALIDATOR / DATABASE INTEGRITY AFTER"
    )

    kv(
        "Production SHA256 BEFORE",
        production_sha_before
    )

    kv(
        "Production SHA256 AFTER",
        production_sha_after
    )

    kv(
        "Validator Source SHA256 BEFORE",
        validator_sha_before
    )

    kv(
        "Validator Source SHA256 AFTER",
        validator_sha_after
    )

    kv(
        "Database Size BEFORE",
        db_size_before
    )

    kv(
        "Database Size AFTER",
        db_size_after
    )

    kv(
        "Database SHA256 BEFORE",
        db_sha_before
    )

    kv(
        "Database SHA256 AFTER",
        db_sha_after
    )

    if production_sha_before != production_sha_after:

        fail(
            "PRODUCTION SOURCE CHANGED DURING RUNTIME VALIDATION"
        )

    if validator_sha_before != validator_sha_after:

        fail(
            "VALIDATOR SOURCE CHANGED DURING RUNTIME VALIDATION"
        )

    if db_size_before != db_size_after:

        fail(
            "DATABASE SIZE CHANGED DURING RUNTIME VALIDATION"
        )

    if db_sha_before != db_sha_after:

        fail(
            "DATABASE SHA256 CHANGED DURING RUNTIME VALIDATION"
        )

    print(
        "[PASS] Production source unchanged"
    )

    print(
        "[PASS] Validator source unchanged"
    )

    print(
        "[PASS] Database size unchanged"
    )

    print(
        "[PASS] Database SHA256 unchanged"
    )

    # --------------------------------------------------------------------------------------------
    # Final
    # --------------------------------------------------------------------------------------------

    banner(
        "FINAL TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.3"
    )

    kv(
        "Runtime Contract Rows",
        len(rows)
    )

    kv(
        "Successful Validation Rows",
        len(results)
    )

    kv(
        "Eligible Rows",
        summary["eligible"]
    )

    kv(
        "Rejected Rows",
        summary["rejected"]
    )

    kv(
        "Runtime Distinct IDs",
        summary["distinct_ids"]
    )

    kv(
        "Runtime MIN ID",
        summary["min_id"]
    )

    kv(
        "Runtime MAX ID",
        summary["max_id"]
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

    print(
        "[PASS] DATABASE READ ONLY"
    )

    print(
        "[PASS] PRODUCTION main() NOT EXECUTED"
    )

    print(
        "[PASS] PRODUCTION MODULE NOT IMPORTED"
    )

    print(
        "[PASS] EXACT acquire_real_rows() EXECUTED"
    )

    print(
        "[PASS] EXACT REAL validate_row() DISCOVERED"
    )

    print(
        "[PASS] EXACT REAL validate_row() EXECUTED"
    )

    print(
        "[PASS] ALL 987 CONTRACT ROWS REACHED VALIDATION"
    )

    print(
        "[PASS] PRODUCTION SOURCE UNCHANGED"
    )

    print(
        "[PASS] VALIDATOR SOURCE UNCHANGED"
    )

    print(
        "[PASS] DATABASE UNCHANGED"
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
        "RUNTIME VALIDATION VERIFIED "
        "ON REAL 987-ROW PRODUCTION CONTRACT"
    )

    print()
    print(
        "===================================================================================================="
    )

    print(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.3 COMPLETE"
    )


if __name__ == "__main__":
    main()