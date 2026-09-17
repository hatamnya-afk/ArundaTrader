import ast
import hashlib
import sqlite3
from pathlib import Path


# =============================================================================
# ARUNDA TECHNICAL CONTRACT PRODUCTION RUNTIME VERIFY v0.1
# =============================================================================
#
# PURPOSE
# -------
# Runtime verification of the REAL production acquire_real_rows() function
# after TECHNICAL_v0.5 source integration.
#
# IMPORTANT
# ---------
# READ ONLY
#
# This script:
#
#   - DOES NOT execute production main()
#   - DOES NOT import/execute the complete production module
#   - DOES NOT INSERT
#   - DOES NOT UPDATE
#   - DOES NOT DELETE
#   - DOES NOT ALTER
#   - DOES NOT CREATE
#   - DOES NOT DROP
#   - DOES NOT COMMIT
#   - DOES NOT modify arunda.db
#   - DOES NOT modify the production source
#
# It extracts ONLY the real acquire_real_rows() function from the
# production source AST and executes that exact function body against
# a READ-ONLY SQLite connection.
#
# This avoids import-time side effects while still executing the actual
# post-patch production function implementation.
#
# CONTRACT
# --------
#
# technical_version = TECHNICAL_v0.5
# engine_version    = TECHNICAL_v0.5
# source            = REAL_MARKET_HISTORY
#
# EXPECTED
# --------
#
# Database total       = 6909
# Contract population  = 987
# Museum population    = 5922
# Contract MIN ID      = 5923
# Contract MAX ID      = 6909
#
# RUNTIME ASSERTION
# -----------------
#
# acquire_real_rows()
#          |
#          v
#       987 rows
#          |
#          +--> ALL contract scoped
#          +--> NO museum rows
#          +--> IDs 5923..6909
#          +--> 987 distinct IDs
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = (
    PROJECT_DIR /
    "arunda.db"
)

PRODUCTION_FILE = (
    PROJECT_DIR /
    "market_technical_validation_engine_v0.4.1.py"
)


# =============================================================================
# PRODUCTION CONTRACT
# =============================================================================

TARGET_FUNCTION = "acquire_real_rows"

TARGET_TABLE = "market_technical"

TRACE_LIMIT = 987

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_DATABASE_TOTAL = 6909
EXPECTED_CONTRACT_ROWS = 987
EXPECTED_MUSEUM_ROWS = 5922

EXPECTED_MIN_ID = 5923
EXPECTED_MAX_ID = 6909


# =============================================================================
# OUTPUT HELPERS
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


def sha256_database(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


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


def parse_production_source(source):

    return ast.parse(
        source,
        filename=str(PRODUCTION_FILE)
    )


# =============================================================================
# FUNCTION DISCOVERY
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
# FUNCTION FINGERPRINT
# =============================================================================

def function_semantic_fingerprint(node):

    normalized = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# =============================================================================
# PRODUCTION FUNCTION INSPECTION
# =============================================================================

def inspect_production_function(source, node):

    banner(
        "REAL PRODUCTION acquire_real_rows()"
    )

    lines = source.splitlines()

    kv(
        "Production File",
        PRODUCTION_FILE
    )

    kv(
        "Function",
        node.name
    )

    kv(
        "Start Line",
        node.lineno
    )

    kv(
        "End Line",
        node.end_lineno
    )

    kv(
        "Semantic SHA256",
        function_semantic_fingerprint(node)
    )

    print()

    for number in range(
        node.lineno,
        node.end_lineno + 1
    ):

        print(
            f"{number:5d}: "
            f"{lines[number - 1]}"
        )


# =============================================================================
# SQL EXTRACTION FROM FUNCTION
# =============================================================================

def normalize_sql(sql):

    if sql is None:

        return ""

    return " ".join(
        str(sql)
        .replace("\n", " ")
        .split()
    ).lower()


def extract_sql_literals(node):

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
                    or
                    "replace" in normalized
                ):

                    result.append(
                        normalized
                    )

    return result


# =============================================================================
# SQL SAFETY CHECK
# =============================================================================

def verify_production_function_sql(node):

    banner(
        "PRODUCTION acquire_real_rows() SQL SAFETY"
    )

    literals = extract_sql_literals(
        node
    )

    if not literals:

        raise RuntimeError(
            "No SQL literal discovered in acquire_real_rows()"
        )

    combined = "\n".join(
        literals
    )

    print(
        "DISCOVERED SQL:"
    )

    for sql in literals:

        print()
        print(sql)

    print()

    forbidden = [
        "insert into",
        "update ",
        "delete from",
        "alter table",
        "create table",
        "drop table",
        "replace into",
        "commit",
        "rollback",
    ]

    for token in forbidden:

        if token in combined:

            raise RuntimeError(
                "WRITE TOKEN DETECTED IN "
                f"acquire_real_rows(): {token}"
            )

    required = [
        "select *",
        'from "{target_table}"',
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

    print()

    print(
        "[PASS] acquire_real_rows() = SELECT only"
    )

    print(
        "[PASS] Contract Scope predicates present"
    )

    print(
        "[PASS] No SQL write operation discovered"
    )


# =============================================================================
# READ-ONLY DATABASE CONNECTION
# =============================================================================

def connect_read_only():

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


# =============================================================================
# DATABASE PREFLIGHT
# =============================================================================

def database_preflight():

    banner(
        "REAL DATABASE PREFLIGHT — READ ONLY"
    )

    conn = None

    try:

        conn = connect_read_only()

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        kv(
            "SQLite query_only",
            query_only
        )

        if int(query_only) != 1:

            raise RuntimeError(
                "SQLite query_only is not enabled"
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

        identity = conn.execute(
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

        min_id = identity[0]
        max_id = identity[1]
        distinct_ids = identity[2]

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
# DATABASE SNAPSHOT
# =============================================================================

def database_snapshot():

    stat = DB_PATH.stat()

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_database(DB_PATH),
    }


# =============================================================================
# SAFE RUNTIME GLOBALS
# =============================================================================
#
# We intentionally DO NOT import the entire production module.
#
# acquire_real_rows() requires only these production globals:
#
#   TARGET_TABLE
#   TRACE_LIMIT
#   banner()
#   kv()
#
# The function itself is taken directly from the production AST.
#
# =============================================================================

def runtime_banner(title):

    print()
    print(
        "-" * 100
    )
    print(title)
    print(
        "-" * 100
    )


def runtime_kv(key, value):

    print(
        f"{key:<55}: {value}"
    )


def build_runtime_namespace():

    namespace = {
        "TARGET_TABLE": TARGET_TABLE,
        "TRACE_LIMIT": TRACE_LIMIT,
        "banner": runtime_banner,
        "kv": runtime_kv,
    }

    return namespace


# =============================================================================
# BUILD EXACT PRODUCTION FUNCTION
# =============================================================================

def build_exact_production_function(
    production_tree,
    namespace
):

    node = find_unique_function(
        production_tree,
        TARGET_FUNCTION
    )

    module = ast.Module(
        body=[
            node
        ],
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

    function = namespace.get(
        TARGET_FUNCTION
    )

    if function is None:

        raise RuntimeError(
            "Failed to construct production acquire_real_rows()"
        )

    return function


# =============================================================================
# RUNTIME INPUT VERIFICATION
# =============================================================================

def verify_runtime_rows(rows):

    banner(
        "PRODUCTION RUNTIME INPUT VERIFICATION"
    )

    count = len(rows)

    kv(
        "Rows Returned By acquire_real_rows()",
        count
    )

    if count != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "RUNTIME INPUT COUNT MISMATCH: "
            f"expected {EXPECTED_CONTRACT_ROWS}, "
            f"got {count}"
        )

    print(
        "[PASS] RUNTIME INPUT COUNT = 987"
    )

    if not rows:

        raise RuntimeError(
            "Runtime returned zero rows"
        )

    column_names = rows[0].keys()

    required_columns = {
        "id",
        "technical_version",
        "engine_version",
        "source",
    }

    missing = (
        required_columns -
        set(column_names)
    )

    if missing:

        raise RuntimeError(
            "Runtime rows missing required columns: "
            f"{sorted(missing)}"
        )

    print(
        "[PASS] Required Contract columns present"
    )

    violations = []

    ids = []

    for row in rows:

        row_id = row["id"]

        technical_version = (
            row["technical_version"]
        )

        engine_version = (
            row["engine_version"]
        )

        source = row["source"]

        ids.append(
            row_id
        )

        if technical_version != (
            CONTRACT_TECHNICAL_VERSION
        ):

            violations.append(
                (
                    row_id,
                    "technical_version",
                    technical_version
                )
            )

        if engine_version != (
            CONTRACT_ENGINE_VERSION
        ):

            violations.append(
                (
                    row_id,
                    "engine_version",
                    engine_version
                )
            )

        if source != CONTRACT_SOURCE:

            violations.append(
                (
                    row_id,
                    "source",
                    source
                )
            )

    if violations:

        print()
        print(
            "RUNTIME CONTRACT VIOLATIONS:"
        )

        for violation in violations[:20]:

            print(
                f"  {violation}"
            )

        raise RuntimeError(
            "RUNTIME CONTRACT SCOPE VIOLATION"
        )

    print(
        "[PASS] ALL RUNTIME ROWS SATISFY CONTRACT"
    )

    distinct_ids = len(
        set(ids)
    )

    min_id = min(ids)
    max_id = max(ids)

    kv(
        "Runtime MIN ID",
        min_id
    )

    kv(
        "Runtime MAX ID",
        max_id
    )

    kv(
        "Runtime DISTINCT IDs",
        distinct_ids
    )

    if distinct_ids != EXPECTED_CONTRACT_ROWS:

        raise RuntimeError(
            "RUNTIME DISTINCT ID MISMATCH"
        )

    if min_id != EXPECTED_MIN_ID:

        raise RuntimeError(
            "RUNTIME MIN ID MISMATCH"
        )

    if max_id != EXPECTED_MAX_ID:

        raise RuntimeError(
            "RUNTIME MAX ID MISMATCH"
        )

    print(
        "[PASS] RUNTIME DISTINCT IDS = 987"
    )

    print(
        "[PASS] RUNTIME ID RANGE = 5923..6909"
    )

    return ids


# =============================================================================
# MUSEUM EXCLUSION VERIFICATION
# =============================================================================

def verify_museum_exclusion(
    conn,
    runtime_ids
):

    banner(
        "MUSEUM / OUT-OF-SCOPE EXCLUSION VERIFICATION"
    )

    museum_rows = conn.execute(
        f'''
        SELECT id
        FROM "{TARGET_TABLE}"
        WHERE NOT (
            technical_version = ?
            AND engine_version = ?
            AND source = ?
        )
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchall()

    museum_ids = {
        row[0]
        for row in museum_rows
    }

    overlap = (
        set(runtime_ids) &
        museum_ids
    )

    kv(
        "Museum Population",
        len(museum_ids)
    )

    kv(
        "Runtime Population",
        len(runtime_ids)
    )

    kv(
        "Runtime / Museum Overlap",
        len(overlap)
    )

    if len(museum_ids) != EXPECTED_MUSEUM_ROWS:

        raise RuntimeError(
            "MUSEUM POPULATION MISMATCH"
        )

    if overlap:

        raise RuntimeError(
            "RUNTIME / MUSEUM OVERLAP DETECTED: "
            f"{sorted(overlap)[:20]}"
        )

    print(
        "[PASS] MUSEUM POPULATION = 5922"
    )

    print(
        "[PASS] RUNTIME / MUSEUM OVERLAP = 0"
    )

    print(
        "[PASS] 5922 OUT-OF-SCOPE ROWS "
        "ARE NOT RUNTIME INPUT"
    )


# =============================================================================
# NO-WRITE RUNTIME GUARD
# =============================================================================

def verify_connection_state(conn):

    banner(
        "RUNTIME DATABASE WRITE GUARD"
    )

    query_only = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    kv(
        "SQLite query_only",
        query_only
    )

    if int(query_only) != 1:

        raise RuntimeError(
            "RUNTIME DATABASE IS NOT READ ONLY"
        )

    print(
        "[PASS] Runtime DB connection = READ ONLY"
    )

    print(
        "[PASS] Production acquire_real_rows() "
        "receives read-only connection"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VERIFY v0.1"
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
        "The complete production module will NOT be imported."
    )

    print(
        "Only the exact production acquire_real_rows() "
        "AST function will be executed."
    )

    print(
        "Database connection is SQLite mode=ro "
        "with PRAGMA query_only=1."
    )

    # =========================================================================
    # SOURCE SNAPSHOT BEFORE
    # =========================================================================

    banner(
        "PRODUCTION SOURCE INTEGRITY BEFORE"
    )

    source_hash_before = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Production SHA256 BEFORE",
        source_hash_before
    )

    if not PRODUCTION_FILE.exists():

        raise RuntimeError(
            "Production source disappeared"
        )

    # =========================================================================
    # DATABASE SNAPSHOT BEFORE
    # =========================================================================

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

    # =========================================================================
    # DATABASE PREFLIGHT
    # =========================================================================

    db_info = database_preflight()

    # =========================================================================
    # SOURCE AST
    # =========================================================================

    banner(
        "PRODUCTION AST DISCOVERY"
    )

    production_source = (
        read_production_source()
    )

    production_tree = (
        parse_production_source(
            production_source
        )
    )

    production_function = (
        find_unique_function(
            production_tree,
            TARGET_FUNCTION
        )
    )

    inspect_production_function(
        production_source,
        production_function
    )

    # =========================================================================
    # SQL SAFETY
    # =========================================================================

    verify_production_function_sql(
        production_function
    )

    # =========================================================================
    # RUNTIME FUNCTION CONSTRUCTION
    # =========================================================================

    banner(
        "EXACT PRODUCTION FUNCTION RUNTIME CONSTRUCTION"
    )

    namespace = (
        build_runtime_namespace()
    )

    runtime_function = (
        build_exact_production_function(
            production_tree,
            namespace
        )
    )

    runtime_hash = (
        function_semantic_fingerprint(
            production_function
        )
    )

    kv(
        "Production Function Semantic SHA256",
        runtime_hash
    )

    print()
    print(
        "[PASS] Exact production acquire_real_rows() "
        "function resolved"
    )

    print(
        "[PASS] No production main() execution"
    )

    print(
        "[PASS] No complete-module import"
    )

    # =========================================================================
    # REAL READ-ONLY RUNTIME CONNECTION
    # =========================================================================

    banner(
        "REAL PRODUCTION acquire_real_rows() RUNTIME"
    )

    conn = None

    try:

        conn = connect_read_only()

        verify_connection_state(
            conn
        )

        # ---------------------------------------------------------------------
        # Runtime call
        # ---------------------------------------------------------------------

        rows = runtime_function(
            conn,
            None,
            TRACE_LIMIT
        )

        # ---------------------------------------------------------------------
        # Runtime result verification
        # ---------------------------------------------------------------------

        runtime_ids = verify_runtime_rows(
            rows
        )

        # ---------------------------------------------------------------------
        # Museum exclusion
        # ---------------------------------------------------------------------

        verify_museum_exclusion(
            conn,
            runtime_ids
        )

        # ---------------------------------------------------------------------
        # Runtime DB connection remains read-only
        # ---------------------------------------------------------------------

        verify_connection_state(
            conn
        )

    finally:

        if conn is not None:

            conn.close()

    # =========================================================================
    # SOURCE INTEGRITY AFTER
    # =========================================================================

    banner(
        "PRODUCTION SOURCE INTEGRITY AFTER"
    )

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

    if source_hash_before != source_hash_after:

        raise RuntimeError(
            "PRODUCTION SOURCE CHANGED DURING RUNTIME VERIFY"
        )

    print(
        "[PASS] Production source unchanged"
    )

    # =========================================================================
    # DATABASE INTEGRITY AFTER
    # =========================================================================

    banner(
        "DATABASE INTEGRITY AFTER"
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

    kv(
        "Database mtime_ns BEFORE",
        db_before["mtime_ns"]
    )

    kv(
        "Database mtime_ns AFTER",
        db_after["mtime_ns"]
    )

    if db_before["size"] != db_after["size"]:

        raise RuntimeError(
            "DATABASE SIZE CHANGED"
        )

    if db_before["sha256"] != db_after["sha256"]:

        raise RuntimeError(
            "DATABASE SHA256 CHANGED"
        )

    if db_before["mtime_ns"] != db_after["mtime_ns"]:

        raise RuntimeError(
            "DATABASE MODIFICATION TIME CHANGED"
        )

    print(
        "[PASS] Database size unchanged"
    )

    print(
        "[PASS] Database SHA256 unchanged"
    )

    print(
        "[PASS] Database modification time unchanged"
    )

    # =========================================================================
    # FINAL SOURCE CHECK
    # =========================================================================

    final_source_hash = sha256_file(
        PRODUCTION_FILE
    )

    if final_source_hash != source_hash_before:

        raise RuntimeError(
            "FINAL PRODUCTION SOURCE INTEGRITY FAILURE"
        )

    # =========================================================================
    # FINAL
    # =========================================================================

    banner(
        "FINAL TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VERIFY v0.1"
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
        "Contract MIN ID",
        db_info["min_id"]
    )

    kv(
        "Contract MAX ID",
        db_info["max_id"]
    )

    kv(
        "Contract DISTINCT IDs",
        db_info["distinct_ids"]
    )

    print()

    print(
        "[PASS] DATABASE TOTAL = 6909"
    )

    print(
        "[PASS] CONTRACT POPULATION = 987"
    )

    print(
        "[PASS] MUSEUM POPULATION = 5922"
    )

    print(
        "[PASS] PRODUCTION acquire_real_rows() EXECUTED"
    )

    print(
        "[PASS] RUNTIME INPUT = 987"
    )

    print(
        "[PASS] ALL RUNTIME ROWS CONTRACT-SCOPED"
    )

    print(
        "[PASS] RUNTIME IDS = 5923..6909"
    )

    print(
        "[PASS] RUNTIME DISTINCT IDS = 987"
    )

    print(
        "[PASS] RUNTIME / MUSEUM OVERLAP = 0"
    )

    print(
        "[PASS] DATABASE WRITE = NONE"
    )

    print(
        "[PASS] PRODUCTION SOURCE UNCHANGED"
    )

    print(
        "[PASS] DATABASE SHA256 UNCHANGED"
    )

    print(
        "[PASS] DATABASE MTIME UNCHANGED"
    )

    print(
        "[PASS] PRODUCTION main() = NOT EXECUTED"
    )

    print()

    print(
        "FINAL STATUS           : PASS"
    )

    print()

    print(
        "TECHNICAL_v0.5 "
        "PRODUCTION RUNTIME INPUT BOUNDARY VERIFIED"
    )

    print()

    print(
        "987 Contract records were returned by the "
        "REAL production acquire_real_rows() function."
    )

    print(
        "5922 historical museum records were excluded "
        "from runtime input."
    )

    print(
        "NO DATABASE WRITE OCCURRED."
    )

    print(
        "NO PRODUCTION SOURCE MODIFICATION OCCURRED."
    )

    print()

    print("=" * 100)

    print(
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION RUNTIME VERIFY v0.1 COMPLETE"
    )

    print("=" * 100)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    main()