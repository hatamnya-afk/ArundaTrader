import ast
import hashlib
import inspect
import sqlite3
import traceback
from collections import defaultdict, deque
from pathlib import Path


# =============================================================================
# ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VALIDATION v0.1
# =============================================================================
#
# PURPOSE
# -------
# Runtime verification of the REAL production validation boundary for the
# TECHNICAL_v0.5 contract population.
#
# THIS SCRIPT:
#
#   1. Does NOT import the production module.
#   2. Does NOT execute production main().
#   3. Does NOT write to the database.
#   4. Extracts the exact production acquire_real_rows() AST function.
#   5. Executes that exact function.
#   6. Discovers the real validation boundary from production AST.
#   7. Executes the discovered validation logic in an isolated namespace.
#   8. Validates exactly the 987 TECHNICAL_v0.5 rows.
#   9. Captures eligible / rejected / reason.
#  10. Verifies source and database hashes remain unchanged.
#
# IMPORTANT
# ---------
# No validate_row() name is assumed.
#
# If the real validation boundary cannot be resolved unambiguously,
# this script FAILS CLOSED rather than inventing a validator.
#
# DATABASE
# --------
# READ ONLY:
#
#     file:arunda.db?mode=ro
#     PRAGMA query_only = 1
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = PROJECT_DIR / "arunda.db"

PRODUCTION_FILE = (
    PROJECT_DIR /
    "market_technical_validation_engine_v0.4.1.py"
)

TARGET_FUNCTION = "acquire_real_rows"
TARGET_TABLE = "market_technical"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_DATABASE_TOTAL = 6909
EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

EXPECTED_MIN_ID = 5923
EXPECTED_MAX_ID = 6909


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):

    print(
        f"{key:<55}: {value}"
    )


# =============================================================================
# HASH
# =============================================================================

def sha256_file(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


# =============================================================================
# SOURCE
# =============================================================================

def read_source():

    if not PRODUCTION_FILE.exists():

        raise FileNotFoundError(
            f"Production file not found: {PRODUCTION_FILE}"
        )

    return PRODUCTION_FILE.read_text(
        encoding="utf-8-sig",
        errors="strict"
    )


def parse_source(source):

    return ast.parse(
        source,
        filename=str(PRODUCTION_FILE)
    )


# =============================================================================
# AST UTILITIES
# =============================================================================

def function_nodes(tree):

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            result.append(node)

    return result


def find_functions(tree, name):

    return [
        node
        for node in function_nodes(tree)
        if node.name == name
    ]


def resolve_unique_function(tree, name):

    matches = find_functions(
        tree,
        name
    )

    if not matches:

        raise RuntimeError(
            f"Function not found: {name}"
        )

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one {name}(), "
            f"found {len(matches)}"
        )

    return matches[0]


def semantic_dump(node):

    cloned = ast.fix_missing_locations(
        ast.parse(
            ast.unparse(node)
        )
    )

    return ast.dump(
        cloned,
        annotate_fields=True,
        include_attributes=False
    )


def semantic_sha256(node):

    return hashlib.sha256(
        semantic_dump(node).encode(
            "utf-8"
        )
    ).hexdigest()


# =============================================================================
# SQL RECONSTRUCTION
# =============================================================================

def normalize_sql(sql):

    if sql is None:
        return ""

    return " ".join(
        str(sql)
        .replace("\n", " ")
        .split()
    ).lower()


def evaluate_static_string(node):

    """
    Conservative static evaluator.

    Supports:
        Constant strings
        JoinedStr / f-string
        formatted constant pieces
        simple Name substitution for known contract constants

    Does NOT execute arbitrary Python.
    """

    constants = {
        "TARGET_TABLE": TARGET_TABLE,
        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,
        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,
        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,
    }

    def evaluate(n):

        if isinstance(
            n,
            ast.Constant
        ):

            if isinstance(
                n.value,
                str
            ):

                return n.value

            return None

        if isinstance(
            n,
            ast.JoinedStr
        ):

            parts = []

            for value in n.values:

                if isinstance(
                    value,
                    ast.Constant
                ):

                    if isinstance(
                        value.value,
                        str
                    ):

                        parts.append(
                            value.value
                        )

                    else:

                        return None

                elif isinstance(
                    value,
                    ast.FormattedValue
                ):

                    expression = value.value

                    if isinstance(
                        expression,
                        ast.Name
                    ):

                        if expression.id in constants:

                            parts.append(
                                str(
                                    constants[
                                        expression.id
                                    ]
                                )
                            )

                        else:

                            return None

                    else:

                        return None

                else:

                    return None

            return "".join(parts)

        return None

    return evaluate(node)


def reconstruct_sql_literals(node):

    result = []

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Constant
        ):

            if isinstance(
                child.value,
                str
            ):

                normalized = normalize_sql(
                    child.value
                )

                if "select" in normalized:

                    result.append(
                        normalized
                    )

        elif isinstance(
            child,
            ast.JoinedStr
        ):

            value = evaluate_static_string(
                child
            )

            if value:

                normalized = normalize_sql(
                    value
                )

                if "select" in normalized:

                    result.append(
                        normalized
                    )

    return result


def verify_contract_sql(node):

    banner(
        "PRODUCTION acquire_real_rows() SQL CONTRACT"
    )

    sqls = reconstruct_sql_literals(
        node
    )

    if not sqls:

        raise RuntimeError(
            "NO SELECT SQL COULD BE RECONSTRUCTED "
            "FROM production acquire_real_rows()"
        )

    combined = "\n".join(sqls)

    print(
        "RECONSTRUCTED SQL:"
    )

    print()

    print(
        combined
    )

    print()

    required = [

        "select *",

        'from "market_technical"',

        "where technical_version = ?",

        "and engine_version = ?",

        "and source = ?",

        "order by id desc",

        "limit ?",
    ]

    for fragment in required:

        if fragment not in combined:

            raise RuntimeError(
                "CONTRACT SQL MISSING: "
                + fragment
            )

        print(
            "[PASS] SQL fragment: "
            + fragment
        )

    forbidden = [

        "insert into",

        "update ",

        "delete from",

        "alter table",

        "create table",

        "drop table",

        "replace into",
    ]

    for token in forbidden:

        if token in combined:

            raise RuntimeError(
                "WRITE SQL DETECTED: "
                + token
            )

    print()

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


# =============================================================================
# DATABASE
# =============================================================================

def connect_database_read_only():

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = (
        f"file:{DB_PATH.as_posix()}"
        f"?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA query_only = ON"
    )

    return conn


def database_fingerprint():

    return {
        "size": DB_PATH.stat().st_size,
        "sha256": sha256_file(DB_PATH),
    }


def database_preflight():

    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    conn = None

    try:

        conn = connect_database_read_only()

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        kv(
            "SQLite query_only",
            query_only
        )

        if int(query_only) != 1:

            raise RuntimeError(
                "DATABASE IS NOT READ ONLY"
            )

        total = conn.execute(
            f'''
            SELECT COUNT(*)
            FROM "{TARGET_TABLE}"
            '''
        ).fetchone()[0]

        contract_count = conn.execute(
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

        museum_count = (
            total -
            contract_count
        )

        id_row = conn.execute(
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

        min_id = id_row[0]
        max_id = id_row[1]
        distinct_ids = id_row[2]

        kv(
            "Database Total",
            total
        )

        kv(
            "Contract Population",
            contract_count
        )

        kv(
            "Museum Population",
            museum_count
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

        if total != EXPECTED_DATABASE_TOTAL:

            raise RuntimeError(
                "DATABASE TOTAL MISMATCH"
            )

        if contract_count != EXPECTED_CONTRACT_ROWS:

            raise RuntimeError(
                "CONTRACT POPULATION MISMATCH"
            )

        if museum_count != EXPECTED_MUSEUM_ROWS:

            raise RuntimeError(
                "MUSEUM POPULATION MISMATCH"
            )

        if min_id != EXPECTED_MIN_ID:

            raise RuntimeError(
                "CONTRACT MIN ID MISMATCH"
            )

        if max_id != EXPECTED_MAX_ID:

            raise RuntimeError(
                "CONTRACT MAX ID MISMATCH"
            )

        if distinct_ids != EXPECTED_CONTRACT_ROWS:

            raise RuntimeError(
                "CONTRACT DISTINCT ID MISMATCH"
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
            "contract": contract_count,
            "museum": museum_count,
            "min_id": min_id,
            "max_id": max_id,
            "distinct_ids": distinct_ids,
        }

    finally:

        if conn is not None:

            conn.close()


# =============================================================================
# SAFE PRODUCTION ENVIRONMENT
# =============================================================================

class RuntimeBanner:

    @staticmethod
    def banner(title):

        banner(title)

    @staticmethod
    def kv(key, value):

        kv(key, value)


def runtime_kv(key, value):

    kv(key, value)


# =============================================================================
# PRODUCTION CONSTANTS
# =============================================================================

RUNTIME_GLOBALS = {

    "__name__":
        "__arunda_runtime_validation__",

    "__file__":
        str(PRODUCTION_FILE),

    "TARGET_TABLE":
        TARGET_TABLE,

    "CONTRACT_TECHNICAL_VERSION":
        CONTRACT_TECHNICAL_VERSION,

    "CONTRACT_ENGINE_VERSION":
        CONTRACT_ENGINE_VERSION,

    "CONTRACT_SOURCE":
        CONTRACT_SOURCE,

    "TRACE_LIMIT":
        EXPECTED_CONTRACT_ROWS,

    "banner":
        banner,

    "kv":
        kv,

    "RuntimeBanner":
        RuntimeBanner,

    "runtime_kv":
        runtime_kv,
}


# =============================================================================
# AST NAME DISCOVERY
# =============================================================================

def called_function_names(node):

    result = []

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Call
        ):

            function = child.func

            if isinstance(
                function,
                ast.Name
            ):

                result.append(
                    function.id
                )

            elif isinstance(
                function,
                ast.Attribute
            ):

                result.append(
                    function.attr
                )

    return result


def function_call_graph(tree):

    graph = defaultdict(set)

    for node in function_nodes(tree):

        graph[node.name].update(
            called_function_names(node)
        )

    return graph


# =============================================================================
# VALIDATION-LIKE DISCOVERY
# =============================================================================

VALIDATION_NAME_TOKENS = (

    "valid",

    "validation",

    "validate",

    "eligib",

    "eligible",

    "technical",
)


def validation_like_functions(tree):

    result = []

    for node in function_nodes(tree):

        name = node.name.lower()

        if any(
            token in name
            for token in VALIDATION_NAME_TOKENS
        ):

            result.append(
                node
            )

    return result


def print_validation_discovery(tree):

    banner(
        "VALIDATOR / VALIDATION FUNCTION DISCOVERY"
    )

    candidates = validation_like_functions(
        tree
    )

    if not candidates:

        raise RuntimeError(
            "NO VALIDATION-LIKE PRODUCTION FUNCTION FOUND"
        )

    print(
        "Validation-like functions discovered:"
    )

    for node in candidates:

        calls = called_function_names(
            node
        )

        print()

        print(
            f"  {node.name}"
        )

        print(
            f"      semantic_sha256="
            f"{semantic_sha256(node)}"
        )

        if calls:

            print(
                "      calls="
                + ", ".join(
                    sorted(
                        set(calls)
                    )
                )
            )

    return candidates


# =============================================================================
# VALIDATION BOUNDARY RESOLUTION
# =============================================================================

def score_validation_function(
    node,
    graph,
    tree
):

    name = node.name.lower()

    score = 0

    if "validation" in name:
        score += 50

    if "validate" in name:
        score += 45

    if "eligible" in name:
        score += 35

    if "eligib" in name:
        score += 35

    if "technical" in name:
        score += 15

    params = (
        list(
            node.args.posonlyargs
        )
        +
        list(
            node.args.args
        )
    )

    param_names = {
        p.arg.lower()
        for p in params
    }

    if "row" in param_names:
        score += 30

    if any(
        "row" in p
        for p in param_names
    ):
        score += 20

    if "record" in param_names:
        score += 20

    if "technical" in param_names:
        score += 15

    if "columns" in param_names:
        score += 5

    calls = graph.get(
        node.name,
        set()
    )

    if calls:
        score += min(
            len(calls),
            5
        )

    return score


def resolve_validation_boundary(
    tree,
    candidates
):

    banner(
        "VALIDATION BOUNDARY RESOLUTION"
    )

    graph = function_call_graph(
        tree
    )

    scored = []

    for node in candidates:

        score = score_validation_function(
            node,
            graph,
            tree
        )

        scored.append(
            (
                score,
                node
            )
        )

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].name,
        ),
        reverse=True
    )

    for score, node in scored:

        print(
            f"Candidate: {node.name:<45} "
            f"score={score}"
        )

    if not scored:

        raise RuntimeError(
            "NO VALIDATION CANDIDATES"
        )

    best_score = scored[0][0]

    best = [
        node
        for score, node in scored
        if score == best_score
    ]

    if len(best) != 1:

        names = [
            node.name
            for node in best
        ]

        raise RuntimeError(
            "AMBIGUOUS VALIDATION BOUNDARY: "
            + ", ".join(names)
        )

    selected = best[0]

    print()

    print(
        "[PASS] Validation boundary resolved:"
    )

    print(
        f"    {selected.name}"
    )

    print(
        f"    Semantic SHA256 = "
        f"{semantic_sha256(selected)}"
    )

    return selected


# =============================================================================
# DEPENDENCY CLOSURE
# =============================================================================

def resolve_function_map(tree):

    result = {}

    for node in function_nodes(tree):

        if node.name in result:

            raise RuntimeError(
                "DUPLICATE FUNCTION NAME IN PRODUCTION: "
                + node.name
            )

        result[node.name] = node

    return result


def dependency_closure(
    root,
    function_map
):

    closure = set()

    queue = deque(
        [root.name]
    )

    while queue:

        name = queue.popleft()

        if name in closure:
            continue

        closure.add(name)

        node = function_map.get(
            name
        )

        if node is None:
            continue

        for called in called_function_names(
            node
        ):

            if called in function_map:

                if called not in closure:

                    queue.append(
                        called
                    )

    return closure


# =============================================================================
# SANDBOX CONSTRUCTION
# =============================================================================

def build_runtime_namespace(
    source_tree,
    root_validation,
    acquire_node,
    db_conn
):

    banner(
        "ISOLATED PRODUCTION RUNTIME SANDBOX"
    )

    function_map = resolve_function_map(
        source_tree
    )

    closure = dependency_closure(
        root_validation,
        function_map
    )

    acquire_closure = dependency_closure(
        acquire_node,
        function_map
    )

    closure.update(
        acquire_closure
    )

    print(
        "Functions included in isolated runtime:"
    )

    for name in sorted(closure):

        print(
            f"  {name}"
        )

    namespace = dict(
        RUNTIME_GLOBALS
    )

    namespace["sqlite3"] = sqlite3

    namespace["conn"] = db_conn

    namespace["DB_PATH"] = DB_PATH

    # -------------------------------------------------------------------------
    # Standard library imports that may legitimately be required by validation.
    # These are imported INTO THE SANDBOX, not the production module.
    # -------------------------------------------------------------------------

    import math
    import statistics
    import datetime

    namespace["math"] = math
    namespace["statistics"] = statistics
    namespace["datetime"] = datetime

    nodes = []

    for name in sorted(closure):

        node = function_map[name]

        nodes.append(
            ast.fix_missing_locations(
                ast.parse(
                    ast.unparse(node)
                ).body[0]
            )
        )

    module = ast.Module(
        body=nodes,
        type_ignores=[]
    )

    ast.fix_missing_locations(
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

    if root_validation.name not in namespace:

        raise RuntimeError(
            "Resolved validation function was not "
            "created inside runtime sandbox"
        )

    if acquire_node.name not in namespace:

        raise RuntimeError(
            "Production acquire_real_rows() was not "
            "created inside runtime sandbox"
        )

    print()

    print(
        "[PASS] Isolated runtime namespace compiled"
    )

    print(
        "[PASS] Production module was NOT imported"
    )

    return namespace


# =============================================================================
# ACQUIRE REAL ROWS
# =============================================================================

def execute_exact_acquire(
    namespace,
    db_conn,
    acquire_node
):

    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME"
    )

    function = namespace[
        acquire_node.name
    ]

    signature = inspect.signature(
        function
    )

    print(
        f"Signature: {signature}"
    )

    kwargs = {}

    positional = []

    for parameter in signature.parameters.values():

        if parameter.name == "conn":

            positional.append(
                db_conn
            )

        elif parameter.name == "columns":

            positional.append(
                None
            )

        elif parameter.name == "limit":

            positional.append(
                EXPECTED_CONTRACT_ROWS
            )

        elif parameter.default is not inspect.Parameter.empty:

            continue

        else:

            raise RuntimeError(
                "Cannot safely execute production "
                f"acquire_real_rows(): unsupported "
                f"required parameter '{parameter.name}'"
            )

    rows = function(
        *positional,
        **kwargs
    )

    if rows is None:

        raise RuntimeError(
            "Production acquire_real_rows() returned None"
        )

    rows = list(rows)

    kv(
        "Runtime Rows Returned",
        len(rows)
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "PRODUCTION acquire_real_rows() "
            f"RETURNED {len(rows)} ROWS; "
            f"EXPECTED {EXPECTED_CONTRACT_ROWS}"
        )

    print()

    print(
        "[PASS] Exact production acquire_real_rows() "
        "returned 987 rows"
    )

    return rows


# =============================================================================
# SQLITE ROW ACCESS
# =============================================================================

def row_value(
    row,
    key,
    description=None
):

    if isinstance(
        row,
        sqlite3.Row
    ):

        keys = row.keys()

        if key in keys:

            return row[key]

    if isinstance(
        row,
        dict
    ):

        if key in row:

            return row[key]

    if isinstance(
        row,
        (tuple, list)
    ):

        return None

    return None


# =============================================================================
# ROW NORMALIZATION
# =============================================================================

def normalize_runtime_row(
    row,
    columns=None
):

    """
    Preserve the real production row object.

    Also expose a dictionary where possible for validation adapters.
    """

    result = {
        "raw": row,
        "row": row,
    }

    if isinstance(
        row,
        sqlite3.Row
    ):

        for key in row.keys():

            result[key] = row[key]

    elif isinstance(
        row,
        dict
    ):

        result.update(
            row
        )

    elif columns:

        try:

            for index, key in enumerate(
                columns
            ):

                result[key] = row[index]

        except Exception:

            pass

    return result


# =============================================================================
# VALIDATION INVOCATION
# =============================================================================

def validation_signature_report(
    validation_function
):

    signature = inspect.signature(
        validation_function
    )

    banner(
        "REAL PRODUCTION VALIDATION SIGNATURE"
    )

    print(
        f"Function: {validation_function.__name__}"
    )

    print(
        f"Signature: {signature}"
    )

    print()

    for parameter in signature.parameters.values():

        print(
            f"  {parameter.name:<30}"
            f" kind={parameter.kind}"
            f" default={parameter.default}"
        )

    return signature


def build_validation_arguments(
    signature,
    row,
    columns
):

    args = []

    kwargs = {}

    for parameter in signature.parameters.values():

        name = parameter.name.lower()

        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):

            continue

        value_found = True

        if (
            name == "row"
            or
            name.endswith("_row")
            or
            "row" == name
        ):

            value = row

        elif (
            "record" in name
            or
            name.endswith("_record")
        ):

            value = row

        elif name in (
            "columns",
            "column_names",
            "cols",
        ):

            value = columns

        elif name in (
            "contract",
            "contract_version",
        ):

            value = CONTRACT_TECHNICAL_VERSION

        elif name in (
            "technical_version",
            "technical",
        ):

            value = CONTRACT_TECHNICAL_VERSION

        elif name in (
            "engine_version",
            "engine",
        ):

            value = CONTRACT_ENGINE_VERSION

        elif name == "source":

            value = CONTRACT_SOURCE

        elif name in (
            "conn",
            "connection",
            "db",
            "database",
        ):

            raise RuntimeError(
                "Validation function requires database "
                "connection; runtime validator refuses "
                "to inject a writable/unknown connection"
            )

        elif parameter.default is not inspect.Parameter.empty:

            continue

        else:

            value_found = False

        if not value_found:

            raise RuntimeError(
                "Cannot safely map production validation "
                f"parameter '{parameter.name}'"
            )

        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):

            args.append(
                value
            )

        elif parameter.kind == (
            inspect.Parameter.KEYWORD_ONLY
        ):

            kwargs[
                parameter.name
            ] = value

    return args, kwargs


# =============================================================================
# VALIDATION RESULT NORMALIZATION
# =============================================================================

def classify_boolean(
    value
):

    if isinstance(
        value,
        bool
    ):

        return value

    if isinstance(
        value,
        int
    ) and value in (
        0,
        1,
    ):

        return bool(value)

    if isinstance(
        value,
        str
    ):

        normalized = (
            value
            .strip()
            .lower()
        )

        if normalized in (
            "true",
            "yes",
            "eligible",
            "pass",
            "passed",
            "valid",
            "approved",
        ):

            return True

        if normalized in (
            "false",
            "no",
            "rejected",
            "reject",
            "invalid",
            "fail",
            "failed",
        ):

            return False

    return None


def normalize_validation_result(
    result
):

    """
    Normalize common production validation return shapes.

    Supported:
        bool
        tuple(bool, reason)
        dict with eligible/is_eligible/valid/pass
        object attributes with same semantics

    Ambiguous results FAIL CLOSED.
    """

    eligible = None
    reason = None
    rejected = None

    if isinstance(
        result,
        bool
    ):

        eligible = result

    elif isinstance(
        result,
        tuple
    ):

        if len(result) == 0:

            raise RuntimeError(
                "Validation returned empty tuple"
            )

        eligible = classify_boolean(
            result[0]
        )

        if len(result) >= 2:

            reason = result[1]

    elif isinstance(
        result,
        dict
    ):

        for key in (
            "eligible",
            "is_eligible",
            "valid",
            "is_valid",
            "passed",
            "pass",
            "approved",
        ):

            if key in result:

                eligible = classify_boolean(
                    result[key]
                )

                break

        for key in (
            "rejected",
            "is_rejected",
        ):

            if key in result:

                rejected = classify_boolean(
                    result[key]
                )

                break

        for key in (
            "reason",
            "rejection_reason",
            "reject_reason",
            "validation_reason",
            "message",
            "error",
        ):

            if key in result:

                reason = result[key]

                break

    else:

        for key in (
            "eligible",
            "is_eligible",
            "valid",
            "is_valid",
            "passed",
            "approved",
        ):

            if hasattr(
                result,
                key
            ):

                eligible = classify_boolean(
                    getattr(
                        result,
                        key
                    )
                )

                break

        for key in (
            "rejected",
            "is_rejected",
        ):

            if hasattr(
                result,
                key
            ):

                rejected = classify_boolean(
                    getattr(
                        result,
                        key
                    )
                )

                break

        for key in (
            "reason",
            "rejection_reason",
            "reject_reason",
            "validation_reason",
            "message",
            "error",
        ):

            if hasattr(
                result,
                key
            ):

                reason = getattr(
                    result,
                    key
                )

                break

    if eligible is None and rejected is not None:

        eligible = not rejected

    if eligible is None:

        raise RuntimeError(
            "AMBIGUOUS VALIDATION RESULT — "
            "could not determine eligible/rejected"
        )

    if rejected is None:

        rejected = not eligible

    return {
        "eligible": bool(
            eligible
        ),
        "rejected": bool(
            rejected
        ),
        "reason": (
            "UNKNOWN"
            if reason is None
            else str(reason)
        ),
        "raw": result,
    }


# =============================================================================
# RUNTIME VALIDATION
# =============================================================================

def execute_runtime_validation(
    namespace,
    validation_node,
    rows
):

    banner(
        "REAL PRODUCTION VALIDATION RUNTIME"
    )

    validation_function = namespace[
        validation_node.name
    ]

    signature = validation_signature_report(
        validation_function
    )

    results = []

    columns = None

    if rows:

        first = rows[0]

        if isinstance(
            first,
            sqlite3.Row
        ):

            columns = list(
                first.keys()
            )

    print()

    print(
        "Executing validation against "
        f"{len(rows)} REAL Contract rows..."
    )

    for index, row in enumerate(
        rows,
        start=1
    ):

        try:

            args, kwargs = (
                build_validation_arguments(
                    signature,
                    row,
                    columns
                )
            )

            raw_result = validation_function(
                *args,
                **kwargs
            )

            normalized = (
                normalize_validation_result(
                    raw_result
                )
            )

        except Exception as exc:

            print()

            print(
                f"[FAIL] Validation execution failed "
                f"at row {index}"
            )

            print(
                f"Exception: {type(exc).__name__}: {exc}"
            )

            raise RuntimeError(
                "REAL PRODUCTION VALIDATION "
                "EXECUTION FAILED"
            ) from exc

        record_id = None

        if isinstance(
            row,
            sqlite3.Row
        ):

            if "id" in row.keys():

                record_id = row["id"]

        results.append(
            {
                "index": index,
                "id": record_id,
                "eligible":
                    normalized["eligible"],
                "rejected":
                    normalized["rejected"],
                "reason":
                    normalized["reason"],
                "raw":
                    normalized["raw"],
            }
        )

        if index <= 5:

            print()

            print(
                f"Row {index}"
            )

            print(
                f"    id        = {record_id}"
            )

            print(
                f"    eligible  = "
                f"{normalized['eligible']}"
            )

            print(
                f"    rejected  = "
                f"{normalized['rejected']}"
            )

            print(
                f"    reason    = "
                f"{normalized['reason']}"
            )

    print()

    print(
        "[PASS] All 987 rows reached "
        "the real production validation function"
    )

    return results


# =============================================================================
# CONTRACT INPUT VERIFICATION
# =============================================================================

def verify_runtime_input_population(
    rows
):

    banner(
        "RUNTIME VALIDATION INPUT POPULATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "RUNTIME INPUT COUNT MISMATCH"
        )

    ids = []

    for row in rows:

        if isinstance(
            row,
            sqlite3.Row
        ):

            keys = row.keys()

            if "id" not in keys:

                raise RuntimeError(
                    "Runtime row has no id column"
                )

            ids.append(
                row["id"]
            )

            if (
                row["technical_version"]
                != CONTRACT_TECHNICAL_VERSION
            ):

                raise RuntimeError(
                    "RUNTIME CONTRACT TECHNICAL VERSION "
                    "MISMATCH"
                )

            if (
                row["engine_version"]
                != CONTRACT_ENGINE_VERSION
            ):

                raise RuntimeError(
                    "RUNTIME CONTRACT ENGINE VERSION "
                    "MISMATCH"
                )

            if (
                row["source"]
                != CONTRACT_SOURCE
            ):

                raise RuntimeError(
                    "RUNTIME CONTRACT SOURCE MISMATCH"
                )

    if len(
        set(ids)
    ) != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "RUNTIME CONTRACT IDS ARE NOT DISTINCT"
        )

    if min(ids) != EXPECTED_MIN_ID:

        raise RuntimeError(
            "RUNTIME CONTRACT MIN ID MISMATCH"
        )

    if max(ids) != EXPECTED_MAX_ID:

        raise RuntimeError(
            "RUNTIME CONTRACT MAX ID MISMATCH"
        )

    if ids != sorted(
        ids,
        reverse=True
    ):

        raise RuntimeError(
            "RUNTIME CONTRACT ORDER IS NOT id DESC"
        )

    print(
        "[PASS] Runtime input count = 987"
    )

    print(
        "[PASS] Runtime technical_version = TECHNICAL_v0.5"
    )

    print(
        "[PASS] Runtime engine_version = TECHNICAL_v0.5"
    )

    print(
        "[PASS] Runtime source = REAL_MARKET_HISTORY"
    )

    print(
        "[PASS] Runtime IDs distinct"
    )

    print(
        "[PASS] Runtime ID range = 5923..6909"
    )

    print(
        "[PASS] Runtime order = id DESC"
    )


# =============================================================================
# RESULT AGGREGATION
# =============================================================================

def aggregate_results(
    results
):

    banner(
        "RUNTIME VALIDATION RESULT AGGREGATION"
    )

    total = len(
        results
    )

    eligible = sum(
        1
        for result in results
        if result["eligible"]
    )

    rejected = sum(
        1
        for result in results
        if result["rejected"]
    )

    unclassified = (
        total -
        eligible -
        rejected
    )

    reasons = defaultdict(int)

    for result in results:

        if result["rejected"]:

            reasons[
                result["reason"]
            ] += 1

    kv(
        "TOTAL",
        total
    )

    kv(
        "ELIGIBLE",
        eligible
    )

    kv(
        "REJECTED",
        rejected
    )

    kv(
        "UNCLASSIFIED",
        unclassified
    )

    if total != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "VALIDATION TOTAL != 987"
        )

    if eligible + rejected != total:

        raise RuntimeError(
            "ELIGIBLE + REJECTED != TOTAL"
        )

    if unclassified != 0:

        raise RuntimeError(
            "UNCLASSIFIED VALIDATION RESULTS DETECTED"
        )

    print()

    print(
        "[PASS] TOTAL = 987"
    )

    print(
        "[PASS] ELIGIBLE + REJECTED = 987"
    )

    print(
        "[PASS] UNCLASSIFIED = 0"
    )

    print()

    print(
        "REJECTION REASONS:"
    )

    if not reasons:

        print(
            "  NONE"
        )

    else:

        for reason, count in sorted(
            reasons.items(),
            key=lambda item: (
                -item[1],
                item[0],
            )
        ):

            print(
                f"  {reason:<50} : {count}"
            )

    return {
        "total": total,
        "eligible": eligible,
        "rejected": rejected,
        "unclassified": unclassified,
        "reasons": dict(reasons),
    }


# =============================================================================
# DATABASE POST-FINGERPRINT
# =============================================================================

def verify_database_unchanged(
    before
):

    banner(
        "DATABASE INTEGRITY AFTER RUNTIME VALIDATION"
    )

    after = database_fingerprint()

    kv(
        "Database Size BEFORE",
        before["size"]
    )

    kv(
        "Database Size AFTER",
        after["size"]
    )

    kv(
        "Database SHA256 BEFORE",
        before["sha256"]
    )

    kv(
        "Database SHA256 AFTER",
        after["sha256"]
    )

    if before["size"] != after["size"]:

        raise RuntimeError(
            "DATABASE SIZE CHANGED"
        )

    if before["sha256"] != after["sha256"]:

        raise RuntimeError(
            "DATABASE SHA256 CHANGED"
        )

    print()

    print(
        "[PASS] Database size unchanged"
    )

    print(
        "[PASS] Database SHA256 unchanged"
    )


# =============================================================================
# SOURCE POST-FINGERPRINT
# =============================================================================

def verify_source_unchanged(
    before_hash
):

    banner(
        "PRODUCTION SOURCE INTEGRITY AFTER RUNTIME"
    )

    after_hash = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        before_hash
    )

    kv(
        "Production SHA256 AFTER",
        after_hash
    )

    if before_hash != after_hash:

        raise RuntimeError(
            "PRODUCTION SOURCE CHANGED DURING "
            "RUNTIME VALIDATION"
        )

    print()

    print(
        "[PASS] Production source unchanged"
    )

    return after_hash


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(
    db_info,
    runtime_summary,
    validation_function,
    source_hash,
    db_hash
):

    banner(
        "FINAL TECHNICAL CONTRACT RUNTIME VALIDATION"
    )

    kv(
        "Database Total",
        db_info["total"]
    )

    kv(
        "Contract Population",
        db_info["contract"]
    )

    kv(
        "Museum Population",
        db_info["museum"]
    )

    kv(
        "Runtime Validation Function",
        validation_function.name
    )

    kv(
        "Runtime Rows",
        runtime_summary["total"]
    )

    kv(
        "Eligible",
        runtime_summary["eligible"]
    )

    kv(
        "Rejected",
        runtime_summary["rejected"]
    )

    kv(
        "Unclassified",
        runtime_summary["unclassified"]
    )

    kv(
        "Production SHA256",
        source_hash
    )

    kv(
        "Database SHA256",
        db_hash
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
        "[PASS] CONTRACT SCOPE = 987"
    )

    print(
        "[PASS] REAL PRODUCTION VALIDATION FUNCTION "
        "RESOLVED"
    )

    print(
        "[PASS] ALL 987 ROWS VALIDATED"
    )

    print(
        "[PASS] ELIGIBLE + REJECTED = 987"
    )

    print(
        "[PASS] UNCLASSIFIED = 0"
    )

    print(
        "[PASS] PRODUCTION SOURCE UNCHANGED"
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
        "AT PRODUCTION VALIDATION BOUNDARY"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.1"
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
        DB_PATH
    )

    kv(
        "Target Function",
        TARGET_FUNCTION
    )

    kv(
        "Contract",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "Contract Engine",
        CONTRACT_ENGINE_VERSION
    )

    kv(
        "Contract Source",
        CONTRACT_SOURCE
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
        "Database access is READ ONLY."
    )

    print(
        "No validate_row() name is assumed."
    )

    print(
        "Validation boundary is discovered "
        "from production AST."
    )

    # =========================================================================
    # SOURCE INTEGRITY BEFORE
    # =========================================================================

    banner(
        "PRODUCTION SOURCE INTEGRITY BEFORE"
    )

    before_source_hash = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        before_source_hash
    )

    # =========================================================================
    # DATABASE INTEGRITY BEFORE
    # =========================================================================

    banner(
        "DATABASE INTEGRITY BEFORE"
    )

    before_db_fingerprint = (
        database_fingerprint()
    )

    kv(
        "Database Size",
        before_db_fingerprint["size"]
    )

    kv(
        "Database SHA256",
        before_db_fingerprint["sha256"]
    )

    # =========================================================================
    # DATABASE PREFLIGHT
    # =========================================================================

    db_info = database_preflight()

    # =========================================================================
    # PRODUCTION AST
    # =========================================================================

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    source = read_source()

    tree = parse_source(
        source
    )

    acquire_node = resolve_unique_function(
        tree,
        TARGET_FUNCTION
    )

    print()

    print(
        "EXACT PRODUCTION acquire_real_rows():"
    )

    print()

    lines = source.splitlines()

    for number in range(
        acquire_node.lineno,
        acquire_node.end_lineno + 1
    ):

        print(
            f"{number:5d}: "
            f"{lines[number - 1]}"
        )

    print()

    kv(
        "Function",
        acquire_node.name
    )

    kv(
        "Start Line",
        acquire_node.lineno
    )

    kv(
        "End Line",
        acquire_node.end_lineno
    )

    kv(
        "Semantic SHA256",
        semantic_sha256(acquire_node)
    )

    # =========================================================================
    # SQL CONTRACT
    # =========================================================================

    verify_contract_sql(
        acquire_node
    )

    # =========================================================================
    # VALIDATION DISCOVERY
    # =========================================================================

    candidates = print_validation_discovery(
        tree
    )

    validation_node = resolve_validation_boundary(
        tree,
        candidates
    )

    # =========================================================================
    # DATABASE CONNECTION
    # =========================================================================

    conn = None

    try:

        conn = connect_database_read_only()

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        if int(query_only) != 1:

            raise RuntimeError(
                "Runtime database connection is not "
                "query_only"
            )

        # =====================================================================
        # SANDBOX
        # =====================================================================

        namespace = build_runtime_namespace(
            source_tree=tree,
            root_validation=validation_node,
            acquire_node=acquire_node,
            db_conn=conn,
        )

        # =====================================================================
        # EXACT ACQUISITION
        # =====================================================================

        rows = execute_exact_acquire(
            namespace=namespace,
            db_conn=conn,
            acquire_node=acquire_node,
        )

        # =====================================================================
        # CONTRACT INPUT VERIFICATION
        # =====================================================================

        verify_runtime_input_population(
            rows
        )

        # =====================================================================
        # REAL VALIDATION
        # =====================================================================

        results = execute_runtime_validation(
            namespace=namespace,
            validation_node=validation_node,
            rows=rows,
        )

        # =====================================================================
        # AGGREGATION
        # =====================================================================

        runtime_summary = aggregate_results(
            results
        )

    finally:

        if conn is not None:

            conn.close()

    # =========================================================================
    # SOURCE INTEGRITY AFTER
    # =========================================================================

    after_source_hash = verify_source_unchanged(
        before_source_hash
    )

    # =========================================================================
    # DATABASE INTEGRITY AFTER
    # =========================================================================

    verify_database_unchanged(
        before_db_fingerprint
    )

    # =========================================================================
    # FINAL
    # =========================================================================

    final_contract(
        db_info=db_info,
        runtime_summary=runtime_summary,
        validation_function=validation_node,
        source_hash=after_source_hash,
        db_hash=before_db_fingerprint["sha256"],
    )

    print()

    print(
        "=" * 100
    )

    print(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION "
        "RUNTIME VALIDATION v0.1 COMPLETE"
    )

    print(
        "=" * 100
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    main()