import ast
import difflib
import hashlib
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path


# =============================================================================
# ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.5
# =============================================================================
#
# PURPOSE
# -------
# Controlled production source integration of TECHNICAL_v0.5 into the
# production acquire_real_rows() input boundary.
#
# DATABASE
# --------
# READ ONLY
#
# PRODUCTION WRITE
# ----------------
# ONLY the production Python source file may be modified.
#
# TARGET
# ------
# acquire_real_rows()
#
# PROTECTED
# ---------
# validate_row()
# all non-target functions
# database
# historical museum population
#
# CONTRACT
# --------
# technical_version = TECHNICAL_v0.5
# engine_version    = TECHNICAL_v0.5
# source            = REAL_MARKET_HISTORY
#
# EXPECTED DATABASE STATE
# -----------------------
# total       = 6909
# contract    = 987
# museum      = 5922
# min id      = 5923
# max id      = 6909
# distinct ids= 987
#
# =============================================================================


# =============================================================================
# PATHS / CONTRACT
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = PROJECT_DIR / "arunda.db"

PRODUCTION_FILE = (
    PROJECT_DIR /
    "market_technical_validation_engine_v0.4.1.py"
)

TARGET_FUNCTION = "acquire_real_rows"
VALIDATOR_FUNCTION = "validate_row"
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
    print(f"{key:<55}: {value}")


# =============================================================================
# HASH
# =============================================================================

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


# =============================================================================
# SOURCE IO
# =============================================================================

def read_source():
    if not PRODUCTION_FILE.exists():
        raise FileNotFoundError(
            f"Production file not found: {PRODUCTION_FILE}"
        )

    return PRODUCTION_FILE.read_text(
        encoding="utf-8-sig",
        errors="strict",
    )


def parse_source(source):
    return ast.parse(
        source,
        filename=str(PRODUCTION_FILE),
    )


# =============================================================================
# AST FUNCTION DISCOVERY
# =============================================================================

def find_function_nodes(tree, name):

    matches = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name == name:
                matches.append(node)

    return matches


def resolve_unique_function(tree, name):

    matches = find_function_nodes(
        tree,
        name,
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


# =============================================================================
# AST SEMANTIC FINGERPRINT
# =============================================================================

def semantic_dump(node):

    """
    Quote/whitespace/line-number independent AST representation.
    """

    normalized = ast.parse(
        ast.unparse(node)
    )

    return ast.dump(
        normalized,
        annotate_fields=True,
        include_attributes=False,
    )


def function_semantic_fingerprint(node):

    return sha256_bytes(
        semantic_dump(node).encode("utf-8")
    )


# =============================================================================
# FUNCTION SOURCE EXTRACTION
# =============================================================================

def function_source(
    source,
    node,
):

    lines = source.splitlines()

    return "\n".join(
        lines[
            node.lineno - 1:
            node.end_lineno
        ]
    )


def print_function_source(
    source,
    node,
    title,
):

    banner(title)

    kv(
        "Function",
        node.name,
    )

    kv(
        "Start Line",
        node.lineno,
    )

    kv(
        "End Line",
        node.end_lineno,
    )

    print()

    lines = source.splitlines()

    for number in range(
        node.lineno,
        node.end_lineno + 1,
    ):

        print(
            f"{number:5d}: "
            f"{lines[number - 1]}"
        )


# =============================================================================
# CURRENT TARGET FUNCTION
# =============================================================================

def inspect_current_target_function(
    source,
    tree,
):

    node = resolve_unique_function(
        tree,
        TARGET_FUNCTION,
    )

    print_function_source(
        source,
        node,
        "CURRENT PRODUCTION acquire_real_rows()",
    )

    kv(
        "Current Semantic SHA256",
        function_semantic_fingerprint(node),
    )

    return node


# =============================================================================
# PROPOSED TARGET FUNCTION
# =============================================================================

def build_contract_function_source():

    return f'''
def acquire_real_rows(
    conn,
    columns,
    limit=TRACE_LIMIT
):

    banner(
        "REAL PERSISTED MARKET_TECHNICAL INPUT ACQUISITION"
    )

    rows = conn.execute(
        f"""
        SELECT *
        FROM "{{TARGET_TABLE}}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
            limit,
        )
    ).fetchall()

    kv(
        "Rows Acquired",
        len(rows)
    )

    if not rows:
        raise RuntimeError(
            "No market_technical contract rows available"
        )

    kv(
        "Synthetic Rows",
        "NONE"
    )

    kv(
        "Source",
        "REAL persisted market_technical / TECHNICAL_v0.5 contract"
    )

    return rows
'''


def build_expected_target_node():

    source = build_contract_function_source()

    tree = ast.parse(source)

    return resolve_unique_function(
        tree,
        TARGET_FUNCTION,
    )


def inspect_proposed_target_function():

    proposed_source = build_contract_function_source()

    tree = ast.parse(
        proposed_source,
    )

    node = resolve_unique_function(
        tree,
        TARGET_FUNCTION,
    )

    banner(
        "PROPOSED CONTRACT acquire_real_rows()"
    )

    print(proposed_source)

    kv(
        "Proposed Semantic SHA256",
        function_semantic_fingerprint(node),
    )

    return proposed_source, node


# =============================================================================
# SQL EXTRACTION
# =============================================================================

def normalize_sql(sql):

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
            ast.Constant,
        ):

            value = child.value

            if not isinstance(
                value,
                str,
            ):
                continue

            normalized = normalize_sql(
                value
            )

            if "select" in normalized:
                result.append(normalized)

    return result


# =============================================================================
# PROPOSED CONTRACT SEMANTIC CHECK
# =============================================================================

def assert_proposed_contract_semantics(
    proposed_node,
):

    banner(
        "PROPOSED CONTRACT SEMANTIC SAFETY CHECK"
    )

    sql_literals = extract_sql_literals(
        proposed_node
    )

    if not sql_literals:

        raise RuntimeError(
            "PROPOSED acquire_real_rows() "
            "contains no SELECT SQL literal"
        )

    combined = "\n".join(
        sql_literals
    )

    print(
        "NORMALIZED SQL LITERALS:"
    )

    for sql in sql_literals:
        print()
        print(sql)

    print()

    required_fragments = [
        "select *",
        f'from "{TARGET_TABLE}"',
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
        "order by id desc",
        "limit ?",
    ]

    for fragment in required_fragments:

        if fragment not in combined:

            raise RuntimeError(
                "PROPOSED CONTRACT SQL MISSING: "
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
                "WRITE SQL DETECTED IN PROPOSED "
                f"acquire_real_rows(): {token}"
            )

    kv(
        "SQL Type",
        "SELECT",
    )

    kv(
        "Contract Scope",
        (
            "technical_version + "
            "engine_version + source"
        ),
    )

    kv(
        "Target Table",
        TARGET_TABLE,
    )

    kv(
        "Write SQL",
        "NONE",
    )

    print()
    print(
        "[PASS] Proposed Contract SQL is SELECT-only"
    )

    print(
        "[PASS] Proposed Contract Scope present"
    )

    print(
        "[PASS] No SQL write operation in target"
    )


# =============================================================================
# TARGETED DIFF
# =============================================================================

def targeted_diff(
    before_node,
    proposed_node,
):

    banner(
        "TARGETED acquire_real_rows() DIFF"
    )

    before_text = ast.unparse(
        before_node
    )

    proposed_text = ast.unparse(
        proposed_node
    )

    diff = list(
        difflib.unified_diff(
            before_text.splitlines(),
            proposed_text.splitlines(),
            fromfile="CURRENT acquire_real_rows()",
            tofile="PROPOSED acquire_real_rows()",
            lineterm="",
        )
    )

    if not diff:

        raise RuntimeError(
            "No difference detected between "
            "current and proposed target"
        )

    for line in diff:
        print(line)

    before_sql = "\n".join(
        extract_sql_literals(before_node)
    ).lower()

    proposed_sql = "\n".join(
        extract_sql_literals(proposed_node)
    ).lower()

    if "where technical_version = ?" in before_sql:
        raise RuntimeError(
            "CURRENT production already contains "
            "technical_version Contract Scope"
        )

    required_scope = [
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
    ]

    for fragment in required_scope:

        if fragment not in proposed_sql:

            raise RuntimeError(
                "TARGETED DIFF missing Contract Scope: "
                + fragment
            )

    print()
    print(
        "[PASS] Current target has no Contract Scope"
    )

    print(
        "[PASS] Proposed target adds complete Contract Scope"
    )

    return diff


# =============================================================================
# FUNCTION FINGERPRINTS
# =============================================================================

def production_function_fingerprints(tree):

    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name in result:

                raise RuntimeError(
                    "Duplicate function name detected: "
                    + node.name
                )

            result[node.name] = (
                function_semantic_fingerprint(node)
            )

    return result


# =============================================================================
# VALIDATOR PROTECTION
# =============================================================================

def verify_validator_unchanged(
    before_tree,
    after_tree,
):

    banner(
        "VALIDATOR LOGIC NON-INTERFERENCE"
    )

    before = resolve_unique_function(
        before_tree,
        VALIDATOR_FUNCTION,
    )

    after = resolve_unique_function(
        after_tree,
        VALIDATOR_FUNCTION,
    )

    before_hash = (
        function_semantic_fingerprint(before)
    )

    after_hash = (
        function_semantic_fingerprint(after)
    )

    kv(
        "Validator",
        VALIDATOR_FUNCTION,
    )

    kv(
        "Before Semantic SHA256",
        before_hash,
    )

    kv(
        "After Semantic SHA256",
        after_hash,
    )

    if before_hash != after_hash:

        raise RuntimeError(
            "VALIDATOR LOGIC CHANGED"
        )

    print(
        "[PASS] validate_row() unchanged"
    )


# =============================================================================
# WHOLE PRODUCTION SEMANTIC PROTECTION
# =============================================================================

def verify_only_target_function_changed(
    before_tree,
    after_tree,
):

    banner(
        "WHOLE-PRODUCTION SEMANTIC DIFF"
    )

    before = production_function_fingerprints(
        before_tree
    )

    after = production_function_fingerprints(
        after_tree
    )

    all_names = sorted(
        set(before) |
        set(after)
    )

    changed = []

    for name in all_names:

        if before.get(name) != after.get(name):

            changed.append(name)

    kv(
        "Changed Function Count",
        len(changed),
    )

    if changed:

        print()
        print(
            "Changed Functions:"
        )

        for name in changed:
            print(
                f"  {name}"
            )

    if changed != [
        TARGET_FUNCTION
    ]:

        raise RuntimeError(
            "SEMANTIC DIFF VIOLATION — "
            "ONLY acquire_real_rows() may change"
        )

    print()
    print(
        "[PASS] ONLY acquire_real_rows() changed"
    )


# =============================================================================
# FULL SOURCE DIFF
# =============================================================================

def print_full_source_diff(
    before_source,
    after_source,
):

    banner(
        "FULL PRODUCTION SOURCE DIFF"
    )

    diff = list(
        difflib.unified_diff(
            before_source.splitlines(),
            after_source.splitlines(),
            fromfile="PRODUCTION BEFORE",
            tofile="PRODUCTION PROPOSED",
            lineterm="",
        )
    )

    if not diff:

        raise RuntimeError(
            "Full production source diff is empty"
        )

    for line in diff:
        print(line)

    print()

    print(
        "[PASS] Full source diff generated"
    )

    return diff


# =============================================================================
# DATABASE READ ONLY
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
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA query_only = ON"
    )

    return conn


def database_preflight():

    banner(
        "REAL DATABASE CONTRACT PREFLIGHT — READ ONLY"
    )

    conn = None

    try:

        conn = connect_database_read_only()

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        kv(
            "SQLite query_only",
            query_only,
        )

        if int(query_only) != 1:

            raise RuntimeError(
                "DATABASE READ-ONLY CONTRACT FAILED"
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
            ),
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
            ),
        ).fetchone()

        min_id = id_row[0]
        max_id = id_row[1]
        distinct_ids = id_row[2]

        kv(
            "Database Total",
            total,
        )

        kv(
            "Contract Population",
            contract_count,
        )

        kv(
            "Museum Population",
            museum_count,
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
# SOURCE REPLACEMENT
# =============================================================================

def replace_target_function(
    original_source,
    original_node,
    replacement_source,
):

    lines = original_source.splitlines(
        keepends=True
    )

    start_index = (
        original_node.lineno - 1
    )

    end_index = (
        original_node.end_lineno
    )

    replacement_lines = (
        replacement_source
        .strip("\n")
        .splitlines(
            keepends=True
        )
    )

    replacement_lines = [
        line + "\n"
        if not line.endswith("\n")
        else line
        for line in replacement_lines
    ]

    new_lines = (
        lines[:start_index]
        +
        replacement_lines
        +
        lines[end_index:]
    )

    return "".join(
        new_lines
    )


# =============================================================================
# COMPILE
# =============================================================================

def compile_source(
    source,
    label,
):

    banner(
        f"PYTHON COMPILE PREFLIGHT — {label}"
    )

    compile(
        source,
        str(PRODUCTION_FILE),
        "exec",
    )

    print(
        "[PASS] Source compiles successfully"
    )


# =============================================================================
# BACKUP
# =============================================================================

def create_backup():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        PRODUCTION_FILE.parent /
        f"{PRODUCTION_FILE.name}."
        f"backup_{timestamp}"
    )

    shutil.copy2(
        PRODUCTION_FILE,
        backup_path,
    )

    return backup_path


# =============================================================================
# ATOMIC WRITE
# =============================================================================

def atomic_replace_source(
    new_source,
):

    banner(
        "CONTROLLED PRODUCTION SOURCE WRITE"
    )

    production_dir = (
        PRODUCTION_FILE.parent
    )

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            delete=False,
            dir=production_dir,
            prefix=".arunda_technical_patch_",
            suffix=".tmp",
        ) as temp_file:

            temp_path = Path(
                temp_file.name
            )

            temp_file.write(
                new_source
            )

            temp_file.flush()

            os.fsync(
                temp_file.fileno()
            )

        temp_hash = sha256_file(
            temp_path
        )

        kv(
            "Temporary Source SHA256",
            temp_hash,
        )

        os.replace(
            temp_path,
            PRODUCTION_FILE,
        )

        temp_path = None

        print(
            "[PASS] Atomic production replacement completed"
        )

    finally:

        if temp_path is not None:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass


# =============================================================================
# POST WRITE
# =============================================================================

def post_write_verification(
    before_source,
    before_tree,
    before_hash,
    proposed_source,
):

    banner(
        "POST-WRITE PRODUCTION VERIFICATION"
    )

    after_source = read_source()

    after_hash = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "SHA256 BEFORE",
        before_hash,
    )

    kv(
        "SHA256 AFTER",
        after_hash,
    )

    if before_hash == after_hash:

        raise RuntimeError(
            "SOURCE HASH DID NOT CHANGE"
        )

    print(
        "[PASS] Production source hash changed"
    )

    compile_source(
        after_source,
        "POST-WRITE",
    )

    after_tree = parse_source(
        after_source
    )

    proposed_tree = ast.parse(
        proposed_source
    )

    before_target = resolve_unique_function(
        before_tree,
        TARGET_FUNCTION,
    )

    after_target = resolve_unique_function(
        after_tree,
        TARGET_FUNCTION,
    )

    proposed_target = resolve_unique_function(
        proposed_tree,
        TARGET_FUNCTION,
    )

    before_target_hash = (
        function_semantic_fingerprint(
            before_target
        )
    )

    after_target_hash = (
        function_semantic_fingerprint(
            after_target
        )
    )

    proposed_target_hash = (
        function_semantic_fingerprint(
            proposed_target
        )
    )

    kv(
        "Target Semantic BEFORE",
        before_target_hash,
    )

    kv(
        "Target Semantic PROPOSED",
        proposed_target_hash,
    )

    kv(
        "Target Semantic AFTER",
        after_target_hash,
    )

    if after_target_hash != proposed_target_hash:

        raise RuntimeError(
            "POST-WRITE TARGET FUNCTION DOES NOT "
            "MATCH PROPOSED CONTRACT"
        )

    print(
        "[PASS] acquire_real_rows() matches proposal"
    )

    verify_validator_unchanged(
        before_tree,
        after_tree,
    )

    verify_only_target_function_changed(
        before_tree,
        after_tree,
    )

    return after_hash


# =============================================================================
# FINAL
# =============================================================================

def final_contract(
    db_info,
    before_hash,
    after_hash,
    backup_path,
):

    banner(
        "FINAL TECHNICAL CONTRACT PRODUCTION APPLY v0.5"
    )

    kv(
        "Production File",
        PRODUCTION_FILE,
    )

    kv(
        "Database",
        DB_PATH,
    )

    kv(
        "Contract",
        CONTRACT_TECHNICAL_VERSION,
    )

    kv(
        "Database Total",
        db_info["total"],
    )

    kv(
        "Contract Population",
        db_info["contract"],
    )

    kv(
        "Museum Population",
        db_info["museum"],
    )

    kv(
        "Contract MIN ID",
        db_info["min_id"],
    )

    kv(
        "Contract MAX ID",
        db_info["max_id"],
    )

    kv(
        "Contract DISTINCT IDs",
        db_info["distinct_ids"],
    )

    print()

    kv(
        "SHA256 BEFORE",
        before_hash,
    )

    kv(
        "SHA256 AFTER",
        after_hash,
    )

    kv(
        "Backup",
        backup_path,
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
        "[PASS] acquire_real_rows() = CONTRACT-FIRST"
    )

    print(
        "[PASS] validate_row() = UNCHANGED"
    )

    print(
        "[PASS] ONLY TARGET FUNCTION CHANGED"
    )

    print(
        "[PASS] PRODUCTION SOURCE COMPILES"
    )

    print(
        "[PASS] DATABASE WRITE PATH = NONE"
    )

    print()

    print(
        "5922 HISTORICAL MUSEUM RECORDS:"
    )

    print(
        "    NOT DELETED"
    )

    print(
        "    NOT UPDATED"
    )

    print(
        "    NOT INVALIDATED"
    )

    print(
        "    NOT SENT TO VALIDATOR"
    )

    print()

    print(
        "987 TECHNICAL_v0.5 RECORDS:"
    )

    print(
        "    NOW DEFINE THE PRODUCTION "
        "acquire_real_rows() INPUT SCOPE"
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
        "SUCCESSFULLY CONNECTED "
        "TO PRODUCTION INPUT BOUNDARY"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.5"
    )

    kv(
        "MODE",
        "CONTROLLED PRODUCTION SOURCE PATCH",
    )

    kv(
        "Production File",
        PRODUCTION_FILE,
    )

    kv(
        "Database",
        DB_PATH,
    )

    kv(
        "Target Function",
        TARGET_FUNCTION,
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
        "This script performs a controlled source patch."
    )

    print(
        "Database access is READ ONLY."
    )

    print(
        "Only acquire_real_rows() is permitted to change."
    )

    # =========================================================================
    # 1. DATABASE PREFLIGHT
    # =========================================================================

    db_info = database_preflight()

    # =========================================================================
    # 2. SOURCE BEFORE
    # =========================================================================

    banner(
        "PRODUCTION SOURCE BEFORE"
    )

    before_source = read_source()

    before_hash = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "SHA256 BEFORE",
        before_hash,
    )

    before_tree = parse_source(
        before_source
    )

    current_target = (
        inspect_current_target_function(
            before_source,
            before_tree,
        )
    )

    # =========================================================================
    # 3. PROPOSED TARGET
    # =========================================================================

    (
        proposed_source,
        proposed_target,
    ) = inspect_proposed_target_function()

    # =========================================================================
    # 4. PROPOSED SQL CONTRACT
    # =========================================================================

    assert_proposed_contract_semantics(
        proposed_target
    )

    # =========================================================================
    # 5. TARGETED DIFF
    # =========================================================================

    targeted_diff(
        current_target,
        proposed_target,
    )

    # =========================================================================
    # 6. BUILD PROPOSED FULL SOURCE
    # =========================================================================

    banner(
        "BUILDING PROPOSED FULL PRODUCTION SOURCE"
    )

    proposed_full_source = (
        replace_target_function(
            before_source,
            current_target,
            proposed_source,
        )
    )

    print(
        "[PASS] Proposed source constructed"
    )

    # =========================================================================
    # 7. COMPILE BEFORE WRITE
    # =========================================================================

    compile_source(
        proposed_full_source,
        "PROPOSED FULL PRODUCTION SOURCE",
    )

    proposed_full_tree = parse_source(
        proposed_full_source
    )

    # =========================================================================
    # 8. VALIDATOR LOCK
    # =========================================================================

    verify_validator_unchanged(
        before_tree,
        proposed_full_tree,
    )

    # =========================================================================
    # 9. ONLY TARGET FUNCTION LOCK
    # =========================================================================

    verify_only_target_function_changed(
        before_tree,
        proposed_full_tree,
    )

    # =========================================================================
    # 10. FULL SOURCE DIFF
    # =========================================================================

    print_full_source_diff(
        before_source,
        proposed_full_source,
    )

    # =========================================================================
    # 11. PRE-WRITE HASH LOCK
    # =========================================================================

    banner(
        "PRE-WRITE SOURCE INTEGRITY LOCK"
    )

    live_hash = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Captured SHA256",
        before_hash,
    )

    kv(
        "Live SHA256",
        live_hash,
    )

    if live_hash != before_hash:

        raise RuntimeError(
            "PRODUCTION SOURCE CHANGED DURING "
            "PREFLIGHT — PATCH ABORTED"
        )

    print(
        "[PASS] Production source unchanged"
    )

    # =========================================================================
    # 12. FINAL PRE-WRITE SAFETY GATE
    # =========================================================================

    banner(
        "FINAL PRE-WRITE SAFETY GATE"
    )

    print(
        "[PASS] Database contract verified"
    )

    print(
        "[PASS] Contract population = 987"
    )

    print(
        "[PASS] Museum population = 5922"
    )

    print(
        "[PASS] Contract Scope verified"
    )

    print(
        "[PASS] Proposed source compiles"
    )

    print(
        "[PASS] validate_row() unchanged"
    )

    print(
        "[PASS] Only acquire_real_rows() changes"
    )

    print(
        "[PASS] Proposed target contains SELECT only"
    )

    print(
        "[PASS] Production SHA256 lock verified"
    )

    print()
    print(
        "PRE-WRITE GATE = PASS"
    )

    print(
        "PRODUCTION WRITE MAY NOW PROCEED"
    )

    # =========================================================================
    # 13. BACKUP
    # =========================================================================

    backup_path = create_backup()

    banner(
        "PRODUCTION BACKUP CREATED"
    )

    kv(
        "Backup",
        backup_path,
    )

    # =========================================================================
    # 14. ATOMIC WRITE
    # =========================================================================

    atomic_replace_source(
        proposed_full_source
    )

    # =========================================================================
    # 15. POST WRITE VERIFICATION
    # =========================================================================

    after_hash = post_write_verification(
        before_source=before_source,
        before_tree=before_tree,
        before_hash=before_hash,
        proposed_source=proposed_source,
    )

    # =========================================================================
    # 16. FINAL CONTRACT
    # =========================================================================

    final_contract(
        db_info=db_info,
        before_hash=before_hash,
        after_hash=after_hash,
        backup_path=backup_path,
    )

    print()
    print("=" * 100)
    print(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.5 COMPLETE"
    )
    print("=" * 100)


# =============================================================================
# ENTRY
# =============================================================================

if __name__ == "__main__":
    main()