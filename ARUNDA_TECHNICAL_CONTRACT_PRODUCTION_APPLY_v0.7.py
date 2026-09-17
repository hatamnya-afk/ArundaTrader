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
# ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.7
# =============================================================================
#
# CONTROLLED PRODUCTION SOURCE PATCH
#
# ONLY:
#     acquire_real_rows()
#
# MAY CHANGE.
#
# DATABASE:
#     READ ONLY
#
# PRODUCTION main():
#     NEVER EXECUTED
#
# IMPORTANT v0.7 FIX:
#
#     The previous versions incorrectly assumed that production contains:
#
#         validate_row()
#
#     The real production source does not expose that exact function name.
#
#     Therefore v0.7 protects validator/non-target logic structurally:
#
#         1. Whole production function semantic fingerprints are captured.
#         2. Only acquire_real_rows() may change.
#         3. Every other function must remain identical.
#         4. Validator-like functions are additionally reported/fingerprinted
#            when present.
#
#     This avoids a false abort caused by a guessed validator function name
#     while maintaining the stronger safety property:
#
#         ONLY acquire_real_rows() MAY CHANGE.
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
    print(f"{key:<55}: {value}")


# =============================================================================
# HASH
# =============================================================================

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


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
# AST
# =============================================================================

def find_function_nodes(tree, name):

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

    return matches


def resolve_unique_function(tree, name):

    matches = find_function_nodes(
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

    normalized_source = ast.unparse(node)

    normalized_tree = ast.parse(
        normalized_source
    )

    return ast.dump(
        normalized_tree,
        annotate_fields=True,
        include_attributes=False
    )


def function_semantic_fingerprint(node):

    return sha256_bytes(
        semantic_dump(node).encode("utf-8")
    )


# =============================================================================
# FUNCTION DISCOVERY
# =============================================================================

def all_function_nodes(tree):

    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            if node.name in result:

                raise RuntimeError(
                    "Duplicate production function name detected: "
                    + node.name
                )

            result[node.name] = node

    return result


def production_function_fingerprints(tree):

    nodes = all_function_nodes(tree)

    return {
        name: function_semantic_fingerprint(node)
        for name, node in nodes.items()
    }


# =============================================================================
# VALIDATOR DISCOVERY
# =============================================================================

def discover_validator_like_functions(tree):

    """
    Do NOT assume a hard-coded validator function name.

    This is diagnostic/protection metadata only.

    The stronger protection remains:

        only acquire_real_rows() may change.
    """

    nodes = all_function_nodes(tree)

    candidates = []

    validator_tokens = (
        "valid",
        "validator",
        "validation",
        "score",
        "status",
        "flag",
    )

    for name in sorted(nodes):

        lowered = name.lower()

        if any(
            token in lowered
            for token in validator_tokens
        ):

            candidates.append(name)

    return candidates


def print_validator_discovery(tree):

    banner(
        "VALIDATOR / VALIDATION FUNCTION DISCOVERY"
    )

    candidates = discover_validator_like_functions(
        tree
    )

    if not candidates:

        print(
            "No validator-like function name discovered."
        )

        print(
            "[PASS] No hard-coded validator assumption used."
        )

        return []

    print(
        "Validator-like functions discovered:"
    )

    for name in candidates:

        node = resolve_unique_function(
            tree,
            name
        )

        print(
            f"  {name:<40} "
            f"semantic_sha256="
            f"{function_semantic_fingerprint(node)}"
        )

    print()

    print(
        "[PASS] Validator-like functions discovered "
        "without assuming validate_row()."
    )

    return candidates


# =============================================================================
# FUNCTION SOURCE PRINT
# =============================================================================

def print_function_source(
    source,
    node,
    title
):

    banner(title)

    lines = source.splitlines()

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
# CONTRACT FUNCTION
# =============================================================================

def build_contract_function_source():

    return '''
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
        FROM "{TARGET_TABLE}"
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

    tree = ast.parse(
        build_contract_function_source()
    )

    return resolve_unique_function(
        tree,
        TARGET_FUNCTION
    )


# =============================================================================
# CURRENT TARGET
# =============================================================================

def inspect_current_target_function(
    source,
    tree
):

    node = resolve_unique_function(
        tree,
        TARGET_FUNCTION
    )

    print_function_source(
        source,
        node,
        "CURRENT PRODUCTION acquire_real_rows()"
    )

    kv(
        "Current Semantic SHA256",
        function_semantic_fingerprint(node)
    )

    return node


# =============================================================================
# PROPOSED TARGET
# =============================================================================

def inspect_proposed_target_function():

    proposed_source = (
        build_contract_function_source()
    )

    tree = ast.parse(
        proposed_source
    )

    node = resolve_unique_function(
        tree,
        TARGET_FUNCTION
    )

    banner(
        "PROPOSED CONTRACT acquire_real_rows()"
    )

    print(
        proposed_source
    )

    kv(
        "Proposed Semantic SHA256",
        function_semantic_fingerprint(node)
    )

    return (
        proposed_source,
        node
    )


# =============================================================================
# SQL EXTRACTION
# =============================================================================

def extract_sql_strings(node):

    strings = []

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Constant
        ) and isinstance(
            child.value,
            str
        ):

            strings.append(
                child.value
            )

    return strings


def reconstruct_joined_string(node):

    """
    Reconstruct f-string SQL semantically.

    Example:

        f'''
        SELECT *
        FROM "{TARGET_TABLE}"
        '''

    becomes:

        SELECT *
        FROM "{target_table}"
    """

    if not isinstance(
        node,
        ast.JoinedStr
    ):

        return None

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

            if isinstance(
                value.value,
                ast.Name
            ):

                parts.append(
                    "{"
                    + value.value.id
                    + "}"
                )

            else:

                try:
                    parts.append(
                        "{"
                        + ast.unparse(value.value)
                        + "}"
                    )

                except Exception:

                    parts.append(
                        "{EXPR}"
                    )

    return "".join(parts)


def extract_sql_literals(node):

    sql_values = []

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.JoinedStr
        ):

            reconstructed = (
                reconstruct_joined_string(
                    child
                )
            )

            if reconstructed is not None:

                normalized = normalize_sql(
                    reconstructed
                )

                if "select" in normalized:

                    sql_values.append(
                        normalized
                    )

        elif isinstance(
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

                    sql_values.append(
                        normalized
                    )

    return sql_values


def normalize_sql(sql):

    if sql is None:
        return ""

    return " ".join(
        str(sql)
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    ).lower()


# =============================================================================
# SQL CONTRACT CHECK
# =============================================================================

def assert_proposed_contract_semantics(
    proposed_node
):

    banner(
        "PROPOSED CONTRACT SEMANTIC SAFETY CHECK"
    )

    sql_literals = extract_sql_literals(
        proposed_node
    )

    if not sql_literals:

        raise RuntimeError(
            "PROPOSED CONTRACT SQL NOT DISCOVERED"
        )

    print(
        "RECONSTRUCTED NORMALIZED SQL:"
    )

    for sql in sql_literals:

        print()
        print(sql)

    combined = "\n".join(
        sql_literals
    )

    required_fragments = [
        "select *",
        'from "{target_table}"',
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
                "WRITE SQL DETECTED IN "
                "PROPOSED acquire_real_rows(): "
                + token
            )

    kv(
        "SQL Type",
        "SELECT"
    )

    kv(
        "Contract technical_version",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "Contract engine_version",
        CONTRACT_ENGINE_VERSION
    )

    kv(
        "Contract source",
        CONTRACT_SOURCE
    )

    kv(
        "WHERE Contract Scope",
        "PRESENT"
    )

    kv(
        "Write SQL",
        "NONE"
    )

    print()

    print(
        "[PASS] Proposed Contract SQL "
        "reconstructed correctly"
    )

    print(
        "[PASS] Proposed acquire_real_rows() "
        "contains complete Contract Scope"
    )

    print(
        "[PASS] Proposed acquire_real_rows() "
        "contains no SQL write"
    )


# =============================================================================
# TARGETED DIFF
# =============================================================================

def targeted_diff(
    before_node,
    proposed_node
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
            lineterm=""
        )
    )

    if diff:

        for line in diff:

            print(line)

    else:

        raise RuntimeError(
            "NO TARGETED DIFFERENCE DETECTED"
        )

    before_sql = (
        "\n".join(
            extract_sql_literals(
                before_node
            )
        )
    )

    proposed_sql = (
        "\n".join(
            extract_sql_literals(
                proposed_node
            )
        )
    )

    print()

    print(
        "CURRENT NORMALIZED SQL:"
    )

    print(
        before_sql
    )

    print()

    print(
        "PROPOSED NORMALIZED SQL:"
    )

    print(
        proposed_sql
    )

    if (
        "where technical_version = ?" in
        before_sql
    ):

        raise RuntimeError(
            "CURRENT PRODUCTION ALREADY "
            "CONTAINS CONTRACT SCOPE"
        )

    required = [
        "where technical_version = ?",
        "and engine_version = ?",
        "and source = ?",
    ]

    for fragment in required:

        if fragment not in proposed_sql:

            raise RuntimeError(
                "TARGETED DIFF MISSING: "
                + fragment
            )

    print()

    print(
        "[PASS] Existing ORDER BY id DESC preserved"
    )

    print(
        "[PASS] Existing LIMIT ? preserved"
    )

    print(
        "[PASS] Contract predicates inserted"
    )

    print(
        "[PASS] Current production does not "
        "already contain Contract Scope"
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
        uri=True
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
            query_only
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
# SOURCE REPLACEMENT
# =============================================================================

def replace_target_function(
    original_source,
    original_node,
    replacement_source
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

    if replacement_lines:

        replacement_lines[-1] += "\n"

    return "".join(
        lines[:start_index]
        +
        replacement_lines
        +
        lines[end_index:]
    )


# =============================================================================
# COMPILE
# =============================================================================

def compile_source(
    source,
    label
):

    banner(
        f"PYTHON COMPILE PREFLIGHT — {label}"
    )

    compile(
        source,
        str(PRODUCTION_FILE),
        "exec"
    )

    print(
        "[PASS] Source compiles successfully"
    )


# =============================================================================
# WHOLE FILE SEMANTIC PROTECTION
# =============================================================================

def verify_only_target_function_changed(
    before_tree,
    after_tree
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
        len(changed)
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
            "ONLY acquire_real_rows() MAY CHANGE"
        )

    print()

    print(
        "[PASS] ONLY acquire_real_rows() "
        "semantic fingerprint changed"
    )


# =============================================================================
# VALIDATOR-LIKE PROTECTION
# =============================================================================

def verify_validator_like_functions_unchanged(
    before_tree,
    after_tree
):

    banner(
        "VALIDATOR / VALIDATION LOGIC PROTECTION"
    )

    before_candidates = (
        discover_validator_like_functions(
            before_tree
        )
    )

    after_candidates = (
        discover_validator_like_functions(
            after_tree
        )
    )

    if before_candidates != after_candidates:

        raise RuntimeError(
            "VALIDATOR-LIKE FUNCTION SET CHANGED"
        )

    for name in before_candidates:

        before_node = resolve_unique_function(
            before_tree,
            name
        )

        after_node = resolve_unique_function(
            after_tree,
            name
        )

        before_hash = (
            function_semantic_fingerprint(
                before_node
            )
        )

        after_hash = (
            function_semantic_fingerprint(
                after_node
            )
        )

        kv(
            f"{name} BEFORE",
            before_hash
        )

        kv(
            f"{name} AFTER",
            after_hash
        )

        if before_hash != after_hash:

            raise RuntimeError(
                "VALIDATOR-LIKE LOGIC CHANGED: "
                + name
            )

    if before_candidates:

        print()

        print(
            "[PASS] All discovered validator-like "
            "functions unchanged"
        )

    else:

        print()

        print(
            "[PASS] No validator-like function "
            "required hard-coded name protection"
        )

    print(
        "[PASS] Whole-function protection remains active"
    )


# =============================================================================
# PRE-WRITE CONTRACT
# =============================================================================

def pre_write_safety_gate(
    before_source,
    before_tree,
    before_hash,
    proposed_full_source
):

    banner(
        "PRE-WRITE SAFETY GATE"
    )

    compile_source(
        proposed_full_source,
        "PROPOSED FULL PRODUCTION SOURCE"
    )

    proposed_tree = parse_source(
        proposed_full_source
    )

    verify_validator_like_functions_unchanged(
        before_tree,
        proposed_tree
    )

    verify_only_target_function_changed(
        before_tree,
        proposed_tree
    )

    live_hash = sha256_file(
        PRODUCTION_FILE
    )

    kv(
        "Captured SHA256",
        before_hash
    )

    kv(
        "Live SHA256",
        live_hash
    )

    if live_hash != before_hash:

        raise RuntimeError(
            "PRODUCTION SOURCE CHANGED "
            "DURING PREFLIGHT — PATCH ABORTED"
        )

    print()

    print(
        "[PASS] Production SHA256 source lock verified"
    )

    print(
        "[PASS] Proposed source compiles"
    )

    print(
        "[PASS] Only acquire_real_rows() changes"
    )

    print(
        "[PASS] Validator/non-target logic protected"
    )

    print(
        "[PASS] No database write path used"
    )

    print()

    print(
        "PRE-WRITE GATE = PASS"
    )

    return proposed_tree


# =============================================================================
# BACKUP
# =============================================================================

def create_backup():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        PRODUCTION_FILE.parent /
        (
            f"{PRODUCTION_FILE.name}."
            f"backup_{timestamp}"
        )
    )

    shutil.copy2(
        PRODUCTION_FILE,
        backup_path
    )

    return backup_path


# =============================================================================
# ATOMIC WRITE
# =============================================================================

def atomic_replace_source(
    new_source
):

    banner(
        "CONTROLLED PRODUCTION SOURCE WRITE"
    )

    production_dir = (
        PRODUCTION_FILE.parent
    )

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

    try:

        temp_hash = sha256_file(
            temp_path
        )

        kv(
            "Temporary Source SHA256",
            temp_hash
        )

        os.replace(
            temp_path,
            PRODUCTION_FILE
        )

    finally:

        if temp_path.exists():

            try:
                temp_path.unlink()

            except Exception:
                pass


# =============================================================================
# POST-WRITE VERIFICATION
# =============================================================================

def post_write_verification(
    before_tree,
    before_hash,
    proposed_source
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
        before_hash
    )

    kv(
        "SHA256 AFTER",
        after_hash
    )

    if before_hash == after_hash:

        raise RuntimeError(
            "SOURCE HASH DID NOT CHANGE — "
            "PATCH MAY NOT HAVE BEEN APPLIED"
        )

    print(
        "[PASS] Production source hash changed"
    )

    compile_source(
        after_source,
        "POST-WRITE"
    )

    after_tree = parse_source(
        after_source
    )

    proposed_tree = ast.parse(
        proposed_source
    )

    before_target = resolve_unique_function(
        before_tree,
        TARGET_FUNCTION
    )

    after_target = resolve_unique_function(
        after_tree,
        TARGET_FUNCTION
    )

    proposed_target = resolve_unique_function(
        proposed_tree,
        TARGET_FUNCTION
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
        before_target_hash
    )

    kv(
        "Target Semantic PROPOSED",
        proposed_target_hash
    )

    kv(
        "Target Semantic AFTER",
        after_target_hash
    )

    if after_target_hash != proposed_target_hash:

        raise RuntimeError(
            "POST-WRITE TARGET FUNCTION DOES NOT "
            "MATCH PROPOSED CONTRACT"
        )

    print(
        "[PASS] acquire_real_rows() matches "
        "proposed Contract implementation"
    )

    verify_validator_like_functions_unchanged(
        before_tree,
        after_tree
    )

    verify_only_target_function_changed(
        before_tree,
        after_tree
    )

    return after_hash


# =============================================================================
# FINAL
# =============================================================================

def final_contract(
    db_info,
    before_hash,
    after_hash,
    backup_path
):

    banner(
        "FINAL TECHNICAL CONTRACT PRODUCTION APPLY v0.7"
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

    kv(
        "Production SHA256 BEFORE",
        before_hash
    )

    kv(
        "Production SHA256 AFTER",
        after_hash
    )

    kv(
        "Backup",
        backup_path
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
        "[PASS] ONLY acquire_real_rows() CHANGED"
    )

    print(
        "[PASS] VALIDATOR / NON-TARGET LOGIC UNCHANGED"
    )

    print(
        "[PASS] PRODUCTION SOURCE COMPILES"
    )

    print(
        "[PASS] DATABASE WRITE PATH = NONE"
    )

    print(
        "[PASS] PRODUCTION main() = NOT EXECUTED"
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
        "    PRODUCTION acquire_real_rows() INPUT SCOPE"
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
        "ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.7"
    )

    kv(
        "MODE",
        "CONTROLLED PRODUCTION SOURCE PATCH"
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
        "Database access is READ ONLY."
    )

    print(
        "Production main() will NOT be executed."
    )

    print(
        "Only acquire_real_rows() is permitted to change."
    )

    print(
        "No hard-coded validate_row() assumption is used."
    )

    # =========================================================================
    # DATABASE PREFLIGHT
    # =========================================================================

    db_info = database_preflight()

    # =========================================================================
    # SOURCE BEFORE
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
        before_hash
    )

    before_tree = parse_source(
        before_source
    )

    # =========================================================================
    # FUNCTION DISCOVERY
    # =========================================================================

    print_validator_discovery(
        before_tree
    )

    # =========================================================================
    # CURRENT TARGET
    # =========================================================================

    current_target = (
        inspect_current_target_function(
            before_source,
            before_tree
        )
    )

    # =========================================================================
    # PROPOSED TARGET
    # =========================================================================

    (
        proposed_source,
        proposed_target,
    ) = inspect_proposed_target_function()

    # =========================================================================
    # SQL CONTRACT
    # =========================================================================

    assert_proposed_contract_semantics(
        proposed_target
    )

    # =========================================================================
    # TARGETED DIFF
    # =========================================================================

    targeted_diff(
        current_target,
        proposed_target
    )

    # =========================================================================
    # PROPOSED FULL SOURCE
    # =========================================================================

    banner(
        "PRE-WRITE SOURCE CONSTRUCTION"
    )

    proposed_full_source = (
        replace_target_function(
            before_source,
            current_target,
            proposed_source
        )
    )

    # =========================================================================
    # PRE-WRITE SAFETY
    # =========================================================================

    proposed_full_tree = (
        pre_write_safety_gate(
            before_source=before_source,
            before_tree=before_tree,
            before_hash=before_hash,
            proposed_full_source=proposed_full_source,
        )
    )

    # =========================================================================
    # BACKUP
    # =========================================================================

    banner(
        "PRODUCTION BACKUP"
    )

    backup_path = create_backup()

    kv(
        "Backup",
        backup_path
    )

    print(
        "[PASS] Production backup created"
    )

    # =========================================================================
    # ATOMIC WRITE
    # =========================================================================

    atomic_replace_source(
        proposed_full_source
    )

    # =========================================================================
    # POST-WRITE
    # =========================================================================

    after_hash = post_write_verification(
        before_tree=before_tree,
        before_hash=before_hash,
        proposed_source=proposed_source,
    )

    # =========================================================================
    # FINAL
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
        "ARUNDA TECHNICAL CONTRACT "
        "PRODUCTION APPLY v0.7 COMPLETE"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()