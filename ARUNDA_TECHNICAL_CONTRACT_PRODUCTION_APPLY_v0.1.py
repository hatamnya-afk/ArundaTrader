import ast
import difflib
import hashlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime


# =============================================================================
# ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.4
# =============================================================================
#
# PURPOSE:
#     Controlled production source integration of TECHNICAL_v0.5 Contract
#     into the REAL production acquire_real_rows() boundary.
#
# CRITICAL RULE:
#
#     ONLY the SQL acquisition boundary may change.
#
#     Everything else inside acquire_real_rows() must remain unchanged:
#
#         - function signature
#         - banner
#         - row acquisition mechanism
#         - ORDER BY
#         - LIMIT
#         - empty-result behavior
#         - logging
#         - return rows
#
#     The ONLY semantic addition is:
#
#         WHERE technical_version = ?
#           AND engine_version = ?
#           AND source = ?
#
#     with corresponding bound parameters.
#
# DATABASE:
#     READ ONLY
#
# PRODUCTION:
#     Source file only
#
# NO DATABASE WRITE
# NO HISTORICAL ROW MODIFICATION
# NO VALIDATOR LOGIC MODIFICATION
#
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


def safe(value):
    if value is None:
        return "NULL"
    return str(value)


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
# AST FUNCTION RESOLUTION
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


def function_semantic_fingerprint(node):

    return sha256_bytes(
        semantic_dump(node).encode("utf-8")
    )


# =============================================================================
# SQL EXTRACTION
# =============================================================================

def render_ast_string(node):
    """
    Reconstruct a string expression represented by Python AST.

    Supports:
        Constant
        JoinedStr / f-string
        FormattedValue
        Name

    This is intentionally structural and does NOT execute production code.
    """

    if isinstance(node, ast.Constant):

        if isinstance(node.value, str):
            return node.value

        return str(node.value)

    if isinstance(node, ast.Name):

        return "{" + node.id + "}"

    if isinstance(node, ast.FormattedValue):

        return render_ast_string(
            node.value
        )

    if isinstance(node, ast.JoinedStr):

        parts = []

        for value in node.values:

            if isinstance(
                value,
                ast.Constant
            ):

                parts.append(
                    str(value.value)
                )

            elif isinstance(
                value,
                ast.FormattedValue
            ):

                parts.append(
                    render_ast_string(
                        value
                    )
                )

        return "".join(parts)

    return ast.unparse(node)


def normalize_sql(sql):

    if sql is None:
        return ""

    return " ".join(
        str(sql)
        .replace("\n", " ")
        .split()
    ).lower()


def extract_sql_expressions(function_node):

    results = []

    for node in ast.walk(function_node):

        if isinstance(
            node,
            ast.Call
        ):

            if (
                isinstance(
                    node.func,
                    ast.Attribute
                )
                and
                node.func.attr == "execute"
                and
                node.args
            ):

                sql_node = node.args[0]

                reconstructed = render_ast_string(
                    sql_node
                )

                normalized = normalize_sql(
                    reconstructed
                )

                results.append(
                    {
                        "raw": reconstructed,
                        "normalized": normalized,
                        "node": sql_node,
                    }
                )

    return results


# =============================================================================
# SQL CONTRACT
# =============================================================================

CURRENT_SQL_NORMALIZED = (
    'select * from "{target_table}" '
    'order by id desc limit ?'
)

PROPOSED_SQL_NORMALIZED = (
    'select * from "{target_table}" '
    'where technical_version = ? '
    'and engine_version = ? '
    'and source = ? '
    'order by id desc limit ?'
)


def get_execute_sql(function_node):

    sqls = extract_sql_expressions(
        function_node
    )

    if len(sqls) != 1:

        raise RuntimeError(
            "Expected exactly one conn.execute() "
            f"SQL statement inside {TARGET_FUNCTION}(), "
            f"found {len(sqls)}"
        )

    return sqls[0]


# =============================================================================
# PRODUCTION FUNCTION REVIEW
# =============================================================================

def print_function_source(
    source,
    node,
    title
):

    banner(title)

    lines = source.splitlines()

    start = node.lineno
    end = node.end_lineno

    kv(
        "Function",
        node.name
    )

    kv(
        "Start Line",
        start
    )

    kv(
        "End Line",
        end
    )

    print()

    for number in range(
        start,
        end + 1
    ):

        print(
            f"{number:5d}: "
            f"{lines[number - 1]}"
        )


# =============================================================================
# CONTRACT FUNCTION CONSTRUCTION
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
            limit
        )
    ).fetchall()

    kv(
        "Rows Acquired",
        len(rows)
    )

    if not rows:
        raise RuntimeError(
            "No market_technical rows available"
        )

    kv(
        "Synthetic Rows",
        "NONE"
    )

    kv(
        "Source",
        "REAL persisted market_technical"
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
# TARGETED SEMANTIC CONTRACT CHECK
# =============================================================================

def assert_target_sql_contract(
    current_node,
    proposed_node
):

    banner(
        "TARGET SQL SEMANTIC CONTRACT CHECK"
    )

    current_sql = get_execute_sql(
        current_node
    )

    proposed_sql = get_execute_sql(
        proposed_node
    )

    print(
        "CURRENT SQL:"
    )

    print(
        current_sql["raw"]
    )

    print()

    print(
        "PROPOSED SQL:"
    )

    print(
        proposed_sql["raw"]
    )

    current_normalized = (
        current_sql["normalized"]
        .replace(
            '"market_technical"',
            '"{target_table}"'
        )
    )

    proposed_normalized = (
        proposed_sql["normalized"]
        .replace(
            '"market_technical"',
            '"{target_table}"'
        )
    )

    print()

    print(
        "CURRENT NORMALIZED:"
    )

    print(
        current_normalized
    )

    print()

    print(
        "PROPOSED NORMALIZED:"
    )

    print(
        proposed_normalized
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

        if fragment not in proposed_normalized:

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

        if token in proposed_normalized:

            raise RuntimeError(
                "WRITE SQL DETECTED IN PROPOSED "
                f"acquire_real_rows(): {token}"
            )

    if (
        "where technical_version = ?" in
        current_normalized
    ):

        raise RuntimeError(
            "CURRENT PRODUCTION ALREADY CONTAINS "
            "TECHNICAL CONTRACT SCOPE"
        )

    print()

    print(
        "[PASS] Proposed SQL is SELECT-only"
    )

    print(
        "[PASS] Proposed SQL targets market_technical"
    )

    print(
        "[PASS] Contract WHERE scope present"
    )

    print(
        "[PASS] ORDER BY id DESC preserved"
    )

    print(
        "[PASS] LIMIT ? preserved"
    )

    print(
        "[PASS] No SQL write operation"
    )


# =============================================================================
# MINIMAL TARGET FUNCTION CHECK
# =============================================================================

def assert_minimal_target_change(
    current_node,
    proposed_node
):

    banner(
        "MINIMAL acquire_real_rows() CHANGE CONTRACT"
    )

    current = ast.unparse(
        current_node
    ).splitlines()

    proposed = ast.unparse(
        proposed_node
    ).splitlines()

    diff = list(
        difflib.unified_diff(
            current,
            proposed,
            fromfile="CURRENT acquire_real_rows()",
            tofile="PROPOSED acquire_real_rows()",
            lineterm=""
        )
    )

    print(
        "TARGETED DIFF:"
    )

    for line in diff:
        print(line)

    # -------------------------------------------------------------------------
    # Normalize away the exact expected Contract insertion.
    # -------------------------------------------------------------------------

    current_body = ast.unparse(
        current_node
    )

    proposed_body = ast.unparse(
        proposed_node
    )

    # These are the ONLY semantic changes allowed:
    allowed_removals = [
        (
            'SELECT *\n'
            '        FROM "{TARGET_TABLE}"\n'
            '        ORDER BY id DESC\n'
            '        LIMIT ?'
        ),
        (
            'SELECT *\n'
            '        FROM "{TARGET_TABLE}"\n'
            '        ORDER BY id DESC\n'
            '        LIMIT ?'
        ),
    ]

    # -------------------------------------------------------------------------
    # Structural comparison of all non-SQL statements.
    # -------------------------------------------------------------------------

    def strip_sql_scope(node):

        cloned = ast.parse(
            ast.unparse(node)
        )

        for child in ast.walk(
            cloned
        ):

            if isinstance(
                child,
                ast.Call
            ):

                if (
                    isinstance(
                        child.func,
                        ast.Attribute
                    )
                    and
                    child.func.attr == "execute"
                    and
                    child.args
                ):

                    sql_node = child.args[0]

                    sql_text = render_ast_string(
                        sql_node
                    )

                    normalized = normalize_sql(
                        sql_text
                    )

                    normalized = normalized.replace(
                        " where technical_version = ? "
                        "and engine_version = ? "
                        "and source = ?",
                        ""
                    )

                    normalized = normalized.replace(
                        " from \"market_technical\" ",
                        ' from "{target_table}" '
                    )

                    # Replace SQL expression with stable marker.
                    child.args[0] = ast.Constant(
                        value=normalized
                    )

                    # The corresponding parameter tuple is allowed
                    # to grow by exactly three Contract parameters.
                    if len(child.args) >= 2:

                        parameter_node = child.args[1]

                        if isinstance(
                            parameter_node,
                            ast.Tuple
                        ):

                            names = []

                            for elt in parameter_node.elts:

                                if isinstance(
                                    elt,
                                    ast.Name
                                ):

                                    names.append(
                                        elt.id
                                    )

                                else:

                                    names.append(
                                        ast.unparse(elt)
                                    )

                            # Remove Contract parameters only.
                            filtered = [
                                name
                                for name in names
                                if name not in {
                                    "CONTRACT_TECHNICAL_VERSION",
                                    "CONTRACT_ENGINE_VERSION",
                                    "CONTRACT_SOURCE",
                                }
                            ]

                            parameter_node.elts = [
                                ast.Name(
                                    id=name,
                                    ctx=ast.Load()
                                )
                                for name in filtered
                            ]

        return ast.dump(
            cloned,
            annotate_fields=True,
            include_attributes=False
        )

    current_structural = (
        strip_sql_scope(
            current_node
        )
    )

    proposed_structural = (
        strip_sql_scope(
            proposed_node
        )
    )

    if current_structural != proposed_structural:

        print()
        print(
            "[FAIL] Non-contract semantic change detected"
        )

        raise RuntimeError(
            "acquire_real_rows() contains changes "
            "outside the allowed Contract Scope"
        )

    print()
    print(
        "[PASS] Function signature unchanged"
    )

    print(
        "[PASS] Banner unchanged"
    )

    print(
        "[PASS] Row acquisition mechanism unchanged"
    )

    print(
        "[PASS] ORDER BY unchanged"
    )

    print(
        "[PASS] LIMIT unchanged"
    )

    print(
        "[PASS] Empty-result behavior unchanged"
    )

    print(
        "[PASS] Logging unchanged"
    )

    print(
        "[PASS] Return behavior unchanged"
    )

    print(
        "[PASS] ONLY Contract Scope + parameters changed"
    )


# =============================================================================
# FUNCTION SET FINGERPRINT
# =============================================================================

def production_function_fingerprints(
    tree
):

    result = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            result[node.name] = (
                function_semantic_fingerprint(
                    node
                )
            )

    return result


# =============================================================================
# VALIDATOR PROTECTION
# =============================================================================

def verify_validator_unchanged(
    before_tree,
    after_tree
):

    banner(
        "VALIDATOR LOGIC NON-INTERFERENCE"
    )

    before = resolve_unique_function(
        before_tree,
        VALIDATOR_FUNCTION
    )

    after = resolve_unique_function(
        after_tree,
        VALIDATOR_FUNCTION
    )

    before_hash = (
        function_semantic_fingerprint(
            before
        )
    )

    after_hash = (
        function_semantic_fingerprint(
            after
        )
    )

    kv(
        "Validator Function",
        VALIDATOR_FUNCTION
    )

    kv(
        "Before Semantic SHA256",
        before_hash
    )

    kv(
        "After Semantic SHA256",
        after_hash
    )

    if before_hash != after_hash:

        raise RuntimeError(
            "VALIDATOR LOGIC CHANGED"
        )

    print(
        "[PASS] validate_row() semantic fingerprint unchanged"
    )


# =============================================================================
# NON-TARGET FUNCTION PROTECTION
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
            "MORE THAN acquire_real_rows() CHANGED"
        )

    print()
    print(
        "[PASS] ONLY acquire_real_rows() changed"
    )


# =============================================================================
# DATABASE READ-ONLY PREFLIGHT
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

    temp_path = None

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

        if (
            temp_path is not None
            and
            temp_path.exists()
        ):

            try:
                temp_path.unlink()
            except Exception:
                pass


# =============================================================================
# POST-WRITE
# =============================================================================

def post_write_verification(
    before_source,
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
            "SOURCE HASH DID NOT CHANGE"
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

    after_target = resolve_unique_function(
        after_tree,
        TARGET_FUNCTION
    )

    proposed_target = resolve_unique_function(
        proposed_tree,
        TARGET_FUNCTION
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

    verify_validator_unchanged(
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
        "FINAL TECHNICAL CONTRACT PRODUCTION APPLY v0.4"
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
        "SHA256 BEFORE",
        before_hash
    )

    kv(
        "SHA256 AFTER",
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
        "[PASS] validate_row() = UNCHANGED"
    )

    print(
        "[PASS] ONLY TARGET FUNCTION CHANGED"
    )

    print(
        "[PASS] SOURCE COMPILES"
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
        "    PRODUCTION VALIDATOR INPUT SCOPE"
    )

    print()

    print(
        "FINAL STATUS           : PASS"
    )

    print(
        "TECHNICAL CONTRACT v0.5"
    )

    print(
        "CONNECTED TO PRODUCTION "
        "INPUT BOUNDARY"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.4"
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

    # -------------------------------------------------------------------------
    # DATABASE PREFLIGHT
    # -------------------------------------------------------------------------

    db_info = database_preflight()

    # -------------------------------------------------------------------------
    # SOURCE
    # -------------------------------------------------------------------------

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

    current_target = (
        inspect_current_target_function(
            before_source,
            before_tree
        )
    )

    # -------------------------------------------------------------------------
    # PROPOSED TARGET
    # -------------------------------------------------------------------------

    proposed_source = (
        build_contract_function_source()
    )

    proposed_tree = ast.parse(
        proposed_source
    )

    proposed_target = resolve_unique_function(
        proposed_tree,
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
        function_semantic_fingerprint(
            proposed_target
        )
    )

    # -------------------------------------------------------------------------
    # TARGET SQL
    # -------------------------------------------------------------------------

    assert_target_sql_contract(
        current_target,
        proposed_target
    )

    # -------------------------------------------------------------------------
    # MINIMAL CHANGE
    # -------------------------------------------------------------------------

    assert_minimal_target_change(
        current_target,
        proposed_target
    )

    # -------------------------------------------------------------------------
    # FULL PROPOSED SOURCE
    # -------------------------------------------------------------------------

    proposed_full_source = (
        replace_target_function(
            before_source,
            current_target,
            proposed_source
        )
    )

    # -------------------------------------------------------------------------
    # COMPILE BEFORE WRITE
    # -------------------------------------------------------------------------

    compile_source(
        proposed_full_source,
        "PROPOSED FULL PRODUCTION SOURCE"
    )

    proposed_full_tree = parse_source(
        proposed_full_source
    )

    # -------------------------------------------------------------------------
    # VALIDATOR
    # -------------------------------------------------------------------------

    verify_validator_unchanged(
        before_tree,
        proposed_full_tree
    )

    # -------------------------------------------------------------------------
    # WHOLE FILE
    # -------------------------------------------------------------------------

    verify_only_target_function_changed(
        before_tree,
        proposed_full_tree
    )

    # -------------------------------------------------------------------------
    # SOURCE LOCK
    # -------------------------------------------------------------------------

    banner(
        "PRE-WRITE SOURCE INTEGRITY LOCK"
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
            "PRODUCTION SOURCE CHANGED DURING PREFLIGHT — "
            "PATCH ABORTED"
        )

    print(
        "[PASS] Production source unchanged "
        "since preflight"
    )

    # -------------------------------------------------------------------------
    # FINAL SAFETY GATE
    # -------------------------------------------------------------------------

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
        "[PASS] Contract SQL verified"
    )

    print(
        "[PASS] Minimal target change verified"
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
        "[PASS] No SQL write path in target"
    )

    print(
        "[PASS] SHA256 source lock verified"
    )

    print()
    print(
        "PRE-WRITE GATE = PASS"
    )

    # -------------------------------------------------------------------------
    # BACKUP
    # -------------------------------------------------------------------------

    backup_path = create_backup()

    banner(
        "PRODUCTION BACKUP CREATED"
    )

    kv(
        "Backup",
        backup_path
    )

    # -------------------------------------------------------------------------
    # WRITE
    # -------------------------------------------------------------------------

    atomic_replace_source(
        proposed_full_source
    )

    # -------------------------------------------------------------------------
    # POST WRITE
    # -------------------------------------------------------------------------

    after_hash = post_write_verification(
        before_source=before_source,
        before_tree=before_tree,
        before_hash=before_hash,
        proposed_source=proposed_source,
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    final_contract(
        db_info=db_info,
        before_hash=before_hash,
        after_hash=after_hash,
        backup_path=backup_path,
    )

    print()
    print("=" * 100)
    print(
        "ARUNDA TECHNICAL CONTRACT PRODUCTION APPLY v0.4 COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()