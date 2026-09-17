import ast
import hashlib
import sqlite3
import types
import copy
from pathlib import Path


# =============================================================================
# ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VERIFY v0.2
# =============================================================================
#
# PURPOSE:
#
#   Runtime verification of the ACTUAL production acquire_real_rows()
#   after TECHNICAL_v0.5 contract integration.
#
# HARD SAFETY RULES:
#
#   - READ ONLY database access
#   - Production module is NOT imported
#   - Production main() is NOT executed
#   - No database write
#   - No source write
#   - No source modification
#   - Exact production acquire_real_rows() is extracted through AST
#   - Runtime execution uses only controlled dependencies
#
# VERIFY:
#
#   1. Production source SHA256
#   2. Database SHA256 / size
#   3. Database contract population
#   4. Exact acquire_real_rows() AST discovery
#   5. Semantic function fingerprint
#   6. f-string SQL reconstruction
#   7. Contract predicates
#   8. SELECT-only behavior
#   9. Runtime execution against REAL DB
#  10. Runtime result count
#  11. Runtime result IDs
#  12. Runtime contract values
#  13. No museum rows returned
#  14. Returned rows are REAL persisted rows
#  15. Production source unchanged after runtime
#  16. Database unchanged after runtime
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

# The production function normally receives TRACE_LIMIT.
# The contract population itself is 987.
RUNTIME_LIMIT = EXPECTED_CONTRACT_ROWS


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):

    print(f"{key:<55}: {value}")


# =============================================================================
# HASH
# =============================================================================

def sha256_file(path):

    digest = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# =============================================================================
# SOURCE
# =============================================================================

def read_production_source():

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
# AST FUNCTION DISCOVERY
# =============================================================================

def find_unique_function(tree, name):

    matches = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            if node.name == name:

                matches.append(node)

    if not matches:

        raise RuntimeError(
            f"Production function not found: {name}"
        )

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one {name}(), "
            f"found {len(matches)}"
        )

    return matches[0]


# =============================================================================
# AST SEMANTIC FINGERPRINT
# =============================================================================

def semantic_dump(node):

    normalized = ast.parse(
        ast.unparse(node)
    )

    return ast.dump(
        normalized,
        annotate_fields=True,
        include_attributes=False
    )


def semantic_sha256(node):

    return hashlib.sha256(
        semantic_dump(node).encode("utf-8")
    ).hexdigest()


# =============================================================================
# F-STRING SQL RECONSTRUCTION
# =============================================================================

class SQLReconstructor(ast.NodeVisitor):
    """
    Reconstruct SQL contained inside f-strings.

    Example:

        f'''
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
        '''

    AST stores:
        Constant("... FROM \"")
        FormattedValue(TARGET_TABLE)
        Constant("\" ...")

    This visitor resolves only known safe identifiers.
    """

    def __init__(self, environment):

        self.environment = environment

        self.sql_fragments = []

    def resolve_name(self, node):

        if not isinstance(node, ast.Name):

            raise RuntimeError(
                "Unsupported SQL f-string expression: "
                + ast.dump(node)
            )

        if node.id not in self.environment:

            raise RuntimeError(
                f"Unresolved SQL f-string variable: {node.id}"
            )

        return str(
            self.environment[node.id]
        )

    def visit_JoinedStr(self, node):

        parts = []

        for value in node.values:

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

            elif isinstance(
                value,
                ast.FormattedValue
            ):

                parts.append(
                    self.resolve_name(
                        value.value
                    )
                )

            else:

                raise RuntimeError(
                    "Unsupported JoinedStr node: "
                    + ast.dump(value)
                )

        sql = "".join(parts)

        self.sql_fragments.append(
            normalize_sql(sql)
        )

    def visit_Constant(self, node):

        # Standalone SQL string literals.
        if isinstance(
            node.value,
            str
        ):

            normalized = normalize_sql(
                node.value
            )

            if (
                "select" in normalized
                or
                "insert" in normalized
                or
                "update" in normalized
                or
                "delete" in normalized
                or
                "alter" in normalized
                or
                "create" in normalized
                or
                "drop" in normalized
            ):

                self.sql_fragments.append(
                    normalized
                )


def normalize_sql(sql):

    return " ".join(
        str(sql)
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    ).lower()


def reconstruct_sql(node):

    environment = {
        "TARGET_TABLE":
            TARGET_TABLE,

        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,

        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,

        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,
    }

    reconstructor = SQLReconstructor(
        environment
    )

    reconstructor.visit(node)

    unique = []

    for sql in reconstructor.sql_fragments:

        if sql not in unique:

            unique.append(sql)

    return unique


# =============================================================================
# SQL SAFETY
# =============================================================================

def verify_sql_contract(function_node):

    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    sql_fragments = reconstruct_sql(
        function_node
    )

    if not sql_fragments:

        raise RuntimeError(
            "NO SQL FOUND INSIDE PRODUCTION "
            "acquire_real_rows()"
        )

    print(
        "RECONSTRUCTED SQL:"
    )

    for sql in sql_fragments:

        print()
        print(sql)

    combined = "\n".join(
        sql_fragments
    )

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
                "EXPECTED CONTRACT SQL FRAGMENT "
                f"MISSING: {fragment}"
            )

        print(
            f"[PASS] SQL fragment: {fragment}"
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
                "SQL WRITE OPERATION DETECTED: "
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

    return combined


# =============================================================================
# FUNCTION RUNTIME ENVIRONMENT
# =============================================================================

def build_runtime_environment():

    """
    Controlled namespace for executing ONLY acquire_real_rows().

    No production module import.
    No main().
    No unrelated production functions.
    """

    def runtime_banner(title):

        print()
        print("=" * 100)
        print(title)
        print("=" * 100)

    def runtime_kv(key, value):

        print(
            f"{key:<55}: {value}"
        )

    return {

        "TARGET_TABLE":
            TARGET_TABLE,

        "TRACE_LIMIT":
            RUNTIME_LIMIT,

        "CONTRACT_TECHNICAL_VERSION":
            CONTRACT_TECHNICAL_VERSION,

        "CONTRACT_ENGINE_VERSION":
            CONTRACT_ENGINE_VERSION,

        "CONTRACT_SOURCE":
            CONTRACT_SOURCE,

        "banner":
            runtime_banner,

        "kv":
            runtime_kv,
    }


# =============================================================================
# EXACT FUNCTION EXECUTION
# =============================================================================

def execute_exact_production_function(
    function_node,
    conn
):

    banner(
        "EXACT PRODUCTION acquire_real_rows() RUNTIME EXECUTION"
    )

    function_module = ast.Module(
        body=[
            copy.deepcopy(function_node)
        ],
        type_ignores=[]
    )

    ast.fix_missing_locations(
        function_module
    )

    source = ast.unparse(
        function_module
    )

    runtime_env = build_runtime_environment()

    compiled = compile(
        source,
        str(PRODUCTION_FILE),
        "exec"
    )

    exec(
        compiled,
        runtime_env,
        runtime_env
    )

    runtime_function = runtime_env.get(
        TARGET_FUNCTION
    )

    if runtime_function is None:

        raise RuntimeError(
            "Extracted production function "
            "was not created"
        )

    rows = runtime_function(
        conn,
        None,
        RUNTIME_LIMIT
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

    return rows


# =============================================================================
# ROW ANALYSIS
# =============================================================================

def row_value(row, key):

    try:

        return row[key]

    except Exception:

        raise RuntimeError(
            f"Required column missing: {key}"
        )


def verify_runtime_rows(rows):

    banner(
        "RUNTIME CONTRACT RESULT VERIFICATION"
    )

    if len(rows) != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "RUNTIME ROW COUNT MISMATCH: "
            f"{len(rows)} != {EXPECTED_CONTRACT_ROWS}"
        )

    print(
        "[PASS] Runtime row count = 987"
    )

    ids = []

    for row in rows:

        row_id = row_value(
            row,
            "id"
        )

        technical_version = row_value(
            row,
            "technical_version"
        )

        engine_version = row_value(
            row,
            "engine_version"
        )

        source = row_value(
            row,
            "source"
        )

        if technical_version != (
            CONTRACT_TECHNICAL_VERSION
        ):

            raise RuntimeError(
                "Runtime returned non-contract "
                "technical_version"
            )

        if engine_version != (
            CONTRACT_ENGINE_VERSION
        ):

            raise RuntimeError(
                "Runtime returned non-contract "
                "engine_version"
            )

        if source != CONTRACT_SOURCE:

            raise RuntimeError(
                "Runtime returned non-contract source"
            )

        ids.append(
            int(row_id)
        )

    distinct_ids = len(
        set(ids)
    )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "Runtime returned duplicate IDs"
        )

    min_id = min(ids)

    max_id = max(ids)

    if min_id != EXPECTED_MIN_ID:

        raise RuntimeError(
            "Runtime MIN ID mismatch: "
            f"{min_id}"
        )

    if max_id != EXPECTED_MAX_ID:

        raise RuntimeError(
            "Runtime MAX ID mismatch: "
            f"{max_id}"
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
        "[PASS] Runtime distinct IDs = 987"
    )

    print(
        "[PASS] Runtime MIN ID = 5923"
    )

    print(
        "[PASS] Runtime MAX ID = 6909"
    )

    # Verify ordering explicitly.
    if ids != sorted(
        ids,
        reverse=True
    ):

        raise RuntimeError(
            "Runtime ORDER BY id DESC violated"
        )

    print(
        "[PASS] Runtime ordering = id DESC"
    )

    return {
        "count": len(rows),
        "distinct": distinct_ids,
        "min_id": min_id,
        "max_id": max_id,
        "ids": ids,
    }


# =============================================================================
# DATABASE PREFLIGHT
# =============================================================================

def open_read_only_database():

    uri = (
        f"file:{DB_PATH.as_posix()}"
        "?mode=ro"
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


def database_preflight():

    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    conn = open_read_only_database()

    try:

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        kv(
            "SQLite query_only",
            query_only
        )

        if int(query_only) != 1:

            raise RuntimeError(
                "SQLite query_only != 1"
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

        ids = conn.execute(
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

        min_id = ids[0]

        max_id = ids[1]

        distinct_ids = ids[2]

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

        if total != EXPECTED_DATABASE_TOTAL:

            raise RuntimeError(
                "DATABASE TOTAL MISMATCH"
            )

        if contract != EXPECTED_CONTRACT_ROWS:

            raise RuntimeError(
                "CONTRACT POPULATION MISMATCH"
            )

        if museum != EXPECTED_MUSEUM_ROWS:

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

    finally:

        conn.close()


# =============================================================================
# DATABASE SNAPSHOT
# =============================================================================

def database_snapshot():

    stat = DB_PATH.stat()

    return {
        "size": stat.st_size,
        "sha256": sha256_file(DB_PATH),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VERIFY v0.2"
    )

    kv(
        "MODE",
        "READ ONLY / RUNTIME VERIFICATION"
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
        "Only the exact acquire_real_rows() AST "
        "function will be executed."
    )

    print(
        "Database connection = SQLite mode=ro."
    )

    print(
        "SQLite PRAGMA query_only = 1."
    )

    # -------------------------------------------------------------------------
    # SOURCE BEFORE
    # -------------------------------------------------------------------------

    banner(
        "PRODUCTION SOURCE INTEGRITY BEFORE"
    )

    source_before = read_production_source()

    source_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        source_hash_before
    )

    # -------------------------------------------------------------------------
    # DATABASE BEFORE
    # -------------------------------------------------------------------------

    banner(
        "DATABASE INTEGRITY BEFORE"
    )

    db_before = database_snapshot()

    kv(
        "Database Size",
        db_before["size"]
    )

    kv(
        "Database SHA256",
        db_before["sha256"]
    )

    # -------------------------------------------------------------------------
    # DATABASE PREFLIGHT
    # -------------------------------------------------------------------------

    database_preflight()

    # -------------------------------------------------------------------------
    # AST DISCOVERY
    # -------------------------------------------------------------------------

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    tree = parse_source(
        source_before
    )

    production_function = find_unique_function(
        tree,
        TARGET_FUNCTION
    )

    kv(
        "Production File",
        PRODUCTION_FILE
    )

    kv(
        "Function",
        TARGET_FUNCTION
    )

    kv(
        "Start Line",
        production_function.lineno
    )

    kv(
        "End Line",
        production_function.end_lineno
    )

    function_hash = semantic_sha256(
        production_function
    )

    kv(
        "Semantic SHA256",
        function_hash
    )

    print()

    print(
        "EXACT PRODUCTION FUNCTION:"
    )

    lines = source_before.splitlines()

    for line_no in range(
        production_function.lineno,
        production_function.end_lineno + 1
    ):

        print(
            f"{line_no:5d}: "
            f"{lines[line_no - 1]}"
        )

    # -------------------------------------------------------------------------
    # SQL SAFETY
    # -------------------------------------------------------------------------

    verify_sql_contract(
        production_function
    )

    # -------------------------------------------------------------------------
    # RUNTIME
    # -------------------------------------------------------------------------

    conn = open_read_only_database()

    try:

        rows = execute_exact_production_function(
            production_function,
            conn
        )

        runtime_info = verify_runtime_rows(
            rows
        )

    finally:

        conn.close()

    # -------------------------------------------------------------------------
    # SOURCE AFTER
    # -------------------------------------------------------------------------

    banner(
        "PRODUCTION SOURCE INTEGRITY AFTER RUNTIME"
    )

    source_after = read_production_source()

    source_hash_after = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        source_hash_before
    )

    kv(
        "Production SHA256 AFTER",
        source_hash_after
    )

    if source_hash_after != source_hash_before:

        raise RuntimeError(
            "PRODUCTION SOURCE CHANGED DURING "
            "RUNTIME VERIFICATION"
        )

    print(
        "[PASS] Production source unchanged"
    )

    # -------------------------------------------------------------------------
    # DATABASE AFTER
    # -------------------------------------------------------------------------

    banner(
        "DATABASE INTEGRITY AFTER RUNTIME"
    )

    db_after = database_snapshot()

    kv(
        "Database Size BEFORE",
        db_before["size"]
    )

    kv(
        "Database Size AFTER",
        db_after["size"]
    )

    kv(
        "Database SHA256 BEFORE",
        db_before["sha256"]
    )

    kv(
        "Database SHA256 AFTER",
        db_after["sha256"]
    )

    if db_after["size"] != db_before["size"]:

        raise RuntimeError(
            "DATABASE SIZE CHANGED DURING "
            "RUNTIME VERIFICATION"
        )

    if db_after["sha256"] != db_before["sha256"]:

        raise RuntimeError(
            "DATABASE SHA256 CHANGED DURING "
            "RUNTIME VERIFICATION"
        )

    print(
        "[PASS] Database size unchanged"
    )

    print(
        "[PASS] Database SHA256 unchanged"
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    banner(
        "FINAL TECHNICAL CONTRACT RUNTIME VERIFICATION"
    )

    kv(
        "Runtime Rows",
        runtime_info["count"]
    )

    kv(
        "Runtime Distinct IDs",
        runtime_info["distinct"]
    )

    kv(
        "Runtime MIN ID",
        runtime_info["min_id"]
    )

    kv(
        "Runtime MAX ID",
        runtime_info["max_id"]
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
        "[PASS] CONTRACT SQL RECONSTRUCTED"
    )

    print(
        "[PASS] CONTRACT SCOPE ACTIVE AT RUNTIME"
    )

    print(
        "[PASS] RUNTIME ROW COUNT = 987"
    )

    print(
        "[PASS] RUNTIME ID RANGE = 5923..6909"
    )

    print(
        "[PASS] RUNTIME IDs DISTINCT"
    )

    print(
        "[PASS] RUNTIME ORDER = id DESC"
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
        "RUNTIME VERIFIED AT "
        "PRODUCTION acquire_real_rows() BOUNDARY"
    )

    print()

    print(
        "=" * 100
    )

    print(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VERIFY v0.2 COMPLETE"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()