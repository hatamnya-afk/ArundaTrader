import ast
import difflib
import hashlib
import inspect
import sqlite3
import sys
import importlib.util
from pathlib import Path


# =============================================================================
# ARUNDA
# TECHNICAL CONTRACT INTEGRATION REVIEW v0.1
# =============================================================================
#
# PURPOSE:
#     READ-ONLY review of the minimal integration patch for
#     acquire_real_rows().
#
# CONTRACT:
#     TECHNICAL_v0.5
#
# TRUSTED POPULATION:
#     987 records
#
# HISTORICAL MUSEUM:
#     5922 records
#
# IMPORTANT:
#     THIS SCRIPT DOES NOT APPLY ANY PATCH.
#
#     It does NOT:
#         UPDATE
#         DELETE
#         INSERT
#         ALTER
#         CREATE
#         DROP
#         REPLACE
#         COMMIT
#
#     It does NOT modify production source.
#
#     It does NOT modify the database.
#
# =============================================================================


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = PROJECT_DIR / "arunda.db"

PRODUCTION_ENGINE = PROJECT_DIR / "market_technical_validation_engine_v0.4.1.py"

TARGET_TABLE = "market_technical"

FUNCTION_NAME = "acquire_real_rows"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_DATABASE_TOTAL = 6909
EXPECTED_IN_SCOPE = 987
EXPECTED_OUT_OF_SCOPE = 5922

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


def section(title):

    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def kv(key, value):

    print(f"{key:<50}: {value}")


def status(label, condition):

    print(
        f"[{'PASS' if condition else 'FAIL'}] "
        f"{label}"
    )

    return condition


# =============================================================================
# READ-ONLY DATABASE
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


def verify_read_only(conn):

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if int(value) != 1:

        raise RuntimeError(
            "SQLite query_only is not enabled"
        )

    return True


# =============================================================================
# SOURCE
# =============================================================================

def read_production_source():

    if not PRODUCTION_ENGINE.exists():

        raise FileNotFoundError(
            f"Production engine not found: "
            f"{PRODUCTION_ENGINE}"
        )

    return PRODUCTION_ENGINE.read_text(
        encoding="utf-8-sig",
        errors="strict"
    )


# =============================================================================
# AST FUNCTION RESOLUTION
# =============================================================================

def resolve_function_node(
    source,
    function_name
):

    tree = ast.parse(
        source,
        filename=str(PRODUCTION_ENGINE)
    )

    matches = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            if node.name == function_name:

                matches.append(node)

    if not matches:

        raise RuntimeError(
            f"{function_name}() not found"
        )

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one "
            f"{function_name}(), "
            f"found {len(matches)}"
        )

    return matches[0]


# =============================================================================
# FUNCTION SOURCE
# =============================================================================

def get_function_lines(
    source,
    node
):

    lines = source.splitlines()

    start = node.lineno
    end = getattr(
        node,
        "end_lineno",
        node.lineno
    )

    return (
        start,
        end,
        lines[start - 1:end]
    )


def print_function_source(
    source,
    node
):

    start, end, lines = get_function_lines(
        source,
        node
    )

    banner(
        "REAL PRODUCTION acquire_real_rows()"
    )

    kv(
        "Production File",
        PRODUCTION_ENGINE.name
    )

    kv(
        "Function",
        FUNCTION_NAME
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

    for number, line in enumerate(
        lines,
        start
    ):

        print(
            f"{number:5d}: {line}"
        )

    return (
        start,
        end,
        lines
    )


# =============================================================================
# QUERY EXTRACTION
# =============================================================================

def extract_sql_literals(node):

    literals = []

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Constant
        ):

            value = child.value

            if isinstance(
                value,
                str
            ):

                text = value.strip()

                upper = text.upper()

                if (
                    "SELECT" in upper
                    or "FROM" in upper
                    or "WHERE" in upper
                    or "ORDER BY" in upper
                    or "LIMIT" in upper
                ):

                    literals.append(
                        text
                    )

    return literals


def print_current_query(
    node
):

    section(
        "CURRENT PRODUCTION QUERY DISCOVERY"
    )

    queries = extract_sql_literals(
        node
    )

    if not queries:

        print(
            "[FAIL] No SQL query literal "
            "found inside acquire_real_rows()"
        )

        return None

    for index, query in enumerate(
        queries,
        1
    ):

        print(
            f"\nCURRENT QUERY #{index}"
        )

        print(
            "-" * 80
        )

        print(query)

    if len(queries) > 1:

        print()

        print(
            "[WARNING] Multiple SQL literals "
            "found inside acquire_real_rows()."
        )

    return queries[0]


# =============================================================================
# CONTRACT QUERY
# =============================================================================

def build_contract_query():

    return """
SELECT *
FROM "market_technical"
WHERE technical_version = ?
  AND engine_version = ?
  AND source = ?
ORDER BY id DESC
LIMIT ?
""".strip()


def print_contract_query():

    section(
        "PROPOSED CONTRACT QUERY"
    )

    query = build_contract_query()

    print(query)

    print()

    print(
        "BOUND PARAMETERS:"
    )

    kv(
        "technical_version",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "engine_version",
        CONTRACT_ENGINE_VERSION
    )

    kv(
        "source",
        CONTRACT_SOURCE
    )

    kv(
        "LIMIT",
        EXPECTED_IN_SCOPE
    )

    return query


# =============================================================================
# NORMALIZATION
# =============================================================================

def normalize_sql(sql):

    if sql is None:

        return ""

    lines = []

    for line in sql.splitlines():

        stripped = line.strip()

        if not stripped:

            continue

        lines.append(
            " ".join(
                stripped.split()
            ).lower()
        )

    return "\n".join(lines)


# =============================================================================
# DIFF
# =============================================================================

def print_query_diff(
    current_query,
    proposed_query
):

    section(
        "LINE-BY-LINE QUERY DIFF"
    )

    current_lines = (
        current_query.splitlines()
        if current_query
        else []
    )

    proposed_lines = (
        proposed_query.splitlines()
        if proposed_query
        else []
    )

    diff = list(
        difflib.unified_diff(
            current_lines,
            proposed_lines,
            fromfile="PRODUCTION CURRENT",
            tofile="CONTRACT PROPOSED",
            lineterm=""
        )
    )

    if not diff:

        print(
            "[INFO] Queries are identical."
        )

    else:

        for line in diff:

            print(line)

    return diff


# =============================================================================
# CONTRACT CHANGE ANALYSIS
# =============================================================================

def analyze_change(
    current_query,
    proposed_query
):

    section(
        "MINIMAL CONTRACT CHANGE ANALYSIS"
    )

    current_normalized = normalize_sql(
        current_query
    )

    proposed_normalized = normalize_sql(
        proposed_query
    )

    print(
        "CURRENT QUERY NORMALIZED:"
    )

    print(
        current_normalized
    )

    print()

    print(
        "PROPOSED QUERY NORMALIZED:"
    )

    print(
        proposed_normalized
    )

    print()

    has_select = (
        "select" in proposed_normalized
    )

    has_target_table = (
        'from "market_technical"'
        in proposed_normalized
    )

    has_contract_filter = all(
        token in proposed_normalized
        for token in [
            "technical_version",
            "engine_version",
            "source",
        ]
    )

    no_write_sql = not any(
        token in proposed_normalized.upper()
        for token in [
            "INSERT ",
            "UPDATE ",
            "DELETE ",
            "ALTER ",
            "CREATE ",
            "DROP ",
            "REPLACE ",
        ]
    )

    status(
        "PROPOSED QUERY IS SELECT",
        has_select
    )

    status(
        "PROPOSED QUERY TARGETS market_technical",
        has_target_table
    )

    status(
        "PROPOSED QUERY CONTAINS CONTRACT SCOPE",
        has_contract_filter
    )

    status(
        "PROPOSED QUERY CONTAINS NO WRITE SQL",
        no_write_sql
    )

    return (
        has_select
        and has_target_table
        and has_contract_filter
        and no_write_sql
    )


# =============================================================================
# VALIDATOR LOGIC STATIC CHECK
# =============================================================================

def inspect_validator_dependency(
    source,
    acquire_node
):

    section(
        "VALIDATOR LOGIC NON-INTERFERENCE REVIEW"
    )

    acquire_end = getattr(
        acquire_node,
        "end_lineno",
        acquire_node.lineno
    )

    tree = ast.parse(
        source,
        filename=str(PRODUCTION_ENGINE)
    )

    validator_nodes = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            if node.name in [
                "validate_row",
                "validate_rows",
                "run_validator",
                "validator",
            ]:

                validator_nodes.append(
                    node
                )

    if validator_nodes:

        print(
            "Validator-related functions discovered:"
        )

        for node in validator_nodes:

            print(
                f"  {node.name:<25} "
                f"line={node.lineno}"
            )

    else:

        print(
            "No additional Validator function "
            "definition discovered by name."
        )

    print()

    print(
        "ACQUIRE FUNCTION BOUNDARY:"
    )

    kv(
        "Start",
        acquire_node.lineno
    )

    kv(
        "End",
        acquire_end
    )

    print()

    print(
        "CONTRACT PRINCIPLE:"
    )

    print(
        "The patch must alter only the data acquisition boundary."
    )

    print(
        "Validator scoring/status/flag logic must remain untouched."
    )

    return True


# =============================================================================
# WRITE PATH STATIC SCAN
# =============================================================================

WRITE_TOKENS = [
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "ALTER TABLE",
    "CREATE TABLE",
    "DROP TABLE",
    "REPLACE INTO",
    "EXECUTEMANY(",
    "COMMIT(",
]


def scan_write_paths(source):

    section(
        "PRODUCTION SQL WRITE-PATH REVIEW"
    )

    lines = source.splitlines()

    found = []

    for number, line in enumerate(
        lines,
        1
    ):

        upper = line.upper()

        for token in WRITE_TOKENS:

            if token in upper:

                found.append(
                    (
                        number,
                        token,
                        line.strip()
                    )
                )

    if not found:

        print(
            "[PASS] No production write tokens discovered."
        )

        return found

    print(
        "Write references discovered:"
    )

    for number, token, line in found:

        print(
            f"  line={number:<6} "
            f"token={token:<20} "
            f"{line[:160]}"
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "These references belong to production source discovery."
    )

    print(
        "This review DOES NOT execute them."
    )

    return found


# =============================================================================
# REAL DB CONTRACT POPULATION CHECK
# =============================================================================

def verify_contract_population(
    conn
):

    section(
        "REAL DATABASE CONTRACT POPULATION"

    )

    total = conn.execute(
        f'''
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        '''
    ).fetchone()[0]

    in_scope = conn.execute(
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

    out_scope = total - in_scope

    min_id, max_id, distinct_ids = conn.execute(
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

    kv(
        "Database Total",
        total
    )

    kv(
        "Contract Population",
        in_scope
    )

    kv(
        "Out-of-Scope",
        out_scope
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

    status(
        "DATABASE TOTAL = 6909",
        total == EXPECTED_DATABASE_TOTAL
    )

    status(
        "CONTRACT POPULATION = 987",
        in_scope == EXPECTED_IN_SCOPE
    )

    status(
        "OUT-OF-SCOPE = 5922",
        out_scope == EXPECTED_OUT_OF_SCOPE
    )

    status(
        "MIN ID = 5923",
        min_id == EXPECTED_MIN_ID
    )

    status(
        "MAX ID = 6909",
        max_id == EXPECTED_MAX_ID
    )

    status(
        "DISTINCT IDS = 987",
        distinct_ids == EXPECTED_IN_SCOPE
    )

    return (
        total,
        in_scope,
        out_scope,
        min_id,
        max_id,
        distinct_ids,
    )


# =============================================================================
# PROPOSED INPUT SEMANTICS
# =============================================================================

def verify_contract_semantics(
    conn
):

    section(
        "PROPOSED acquire_real_rows() SEMANTICS"

    )

    query = f'''
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ORDER BY id DESC
        LIMIT ?
    '''

    rows = conn.execute(
        query,
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
            EXPECTED_IN_SCOPE,
        )
    ).fetchall()

    ids = [
        row["id"]
        for row in rows
    ]

    print(
        f"Rows Returned With LIMIT 987      : {len(rows)}"
    )

    if ids:

        print(
            f"MIN returned ID                   : "
            f"{min(ids)}"
        )

        print(
            f"MAX returned ID                   : "
            f"{max(ids)}"
        )

        print(
            f"DISTINCT returned IDs             : "
            f"{len(set(ids))}"
        )

    print()

    status(
        "PROPOSED INPUT SIZE = 987",
        len(rows) == EXPECTED_IN_SCOPE
    )

    status(
        "ALL RETURNED ROWS ARE CONTRACT-SCOPED",
        all(
            row["technical_version"]
            == CONTRACT_TECHNICAL_VERSION
            and
            row["engine_version"]
            == CONTRACT_ENGINE_VERSION
            and
            row["source"]
            == CONTRACT_SOURCE
            for row in rows
        )
    )

    status(
        "RETURNED IDS DISTINCT",
        len(set(ids)) == len(ids)
    )

    status(
        "RETURNED ID RANGE = 5923..6909",
        (
            bool(ids)
            and min(ids) == EXPECTED_MIN_ID
            and max(ids) == EXPECTED_MAX_ID
        )
    )

    return rows


# =============================================================================
# LIMIT SEMANTICS REVIEW
# =============================================================================

def review_limit_semantics(
    current_query,
    proposed_query
):

    section(
        "LIMIT / ACQUISITION SEMANTICS REVIEW"
    )

    current_upper = (
        current_query.upper()
        if current_query
        else ""
    )

    proposed_upper = proposed_query.upper()

    current_has_limit = (
        "LIMIT" in current_upper
    )

    proposed_has_limit = (
        "LIMIT" in proposed_upper
    )

    print(
        f"Current query has LIMIT   : "
        f"{current_has_limit}"
    )

    print(
        f"Proposed query has LIMIT  : "
        f"{proposed_has_limit}"
    )

    print()

    print(
        "CONTRACT RULE:"
    )

    print(
        "Contract membership must determine the population."
    )

    print(
        "LIMIT must not be used as a substitute for Contract scope."
    )

    # Important:
    # LIMIT 987 is acceptable only because the verified
    # Contract population itself is exactly 987.
    #
    # The WHERE clause remains the actual membership boundary.

    proposed_has_where = (
        "WHERE" in proposed_upper
    )

    proposed_has_contract = all(
        token in proposed_upper
        for token in [
            "TECHNICAL_VERSION",
            "ENGINE_VERSION",
            "SOURCE",
        ]
    )

    status(
        "PROPOSED QUERY HAS WHERE CONTRACT BOUNDARY",
        proposed_has_where
        and proposed_has_contract
    )

    return (
        proposed_has_where
        and proposed_has_contract
    )


# =============================================================================
# PATCH SAFETY CONTRACT
# =============================================================================

def print_patch_contract():

    section(
        "INTEGRATION PATCH SAFETY CONTRACT"
    )

    print(
        "PATCH MAY:"
    )

    print(
        "    Modify only acquire_real_rows() input acquisition."
    )

    print(
        "    Add Contract Scope predicates."
    )

    print(
        "    Preserve existing row ordering."
    )

    print(
        "    Preserve existing downstream row representation."
    )

    print()

    print(
        "PATCH MUST NOT:"
    )

    print(
        "    Change validate_row()."
    )

    print(
        "    Change scoring."
    )

    print(
        "    Change status classification."
    )

    print(
        "    Change flags."
    )

    print(
        "    Change Validator logic."
    )

    print(
        "    Modify 5922 historical rows."
    )

    print(
        "    Add UPDATE / DELETE / INSERT."
    )

    print(
        "    Execute production main()."
    )

    print(
        "    Apply this patch."
    )


# =============================================================================
# SOURCE HASH
# =============================================================================

def source_hash(source):

    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(
    source_before,
    current_query,
    proposed_query,
    database_total,
    in_scope,
    out_scope,
    semantics_rows,
    analysis_ok,
    limit_ok,
):

    banner(
        "FINAL TECHNICAL CONTRACT INTEGRATION REVIEW"
    )

    kv(
        "Production Source",
        PRODUCTION_ENGINE.name
    )

    kv(
        "Target Function",
        FUNCTION_NAME
    )

    kv(
        "Database Total",
        database_total
    )

    kv(
        "Contract Population",
        in_scope
    )

    kv(
        "Historical Museum",
        out_scope
    )

    kv(
        "Proposed Validator Input",
        semantics_rows
    )

    print()

    kv(
        "Contract Technical Version",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "Contract Engine Version",
        CONTRACT_ENGINE_VERSION
    )

    kv(
        "Contract Source",
        CONTRACT_SOURCE
    )

    print()

    status(
        "DATABASE TOTAL = 6909",
        database_total == EXPECTED_DATABASE_TOTAL
    )

    status(
        "CONTRACT = 987",
        in_scope == EXPECTED_IN_SCOPE
    )

    status(
        "MUSEUM = 5922",
        out_scope == EXPECTED_OUT_OF_SCOPE
    )

    status(
        "PROPOSED VALIDATOR INPUT = 987",
        semantics_rows == EXPECTED_IN_SCOPE
    )

    status(
        "CONTRACT CHANGE ANALYSIS PASS",
        analysis_ok
    )

    status(
        "LIMIT / BOUNDARY SEMANTICS PASS",
        limit_ok
    )

    print()

    print(
        "SOURCE HASH BEFORE REVIEW:"
    )

    print(
        source_hash(source_before)
    )

    print()

    print(
        "PATCH STATUS:"
    )

    print(
        "    NOT APPLIED"
    )

    print(
        "PRODUCTION SOURCE:"
    )

    print(
        "    UNMODIFIED"
    )

    print(
        "DATABASE:"
    )

    print(
        "    UNMODIFIED"
    )

    print()

    final_ok = (
        database_total
        == EXPECTED_DATABASE_TOTAL
        and in_scope
        == EXPECTED_IN_SCOPE
        and out_scope
        == EXPECTED_OUT_OF_SCOPE
        and semantics_rows
        == EXPECTED_IN_SCOPE
        and analysis_ok
        and limit_ok
    )

    print()

    if final_ok:

        print(
            "FINAL STATUS           : PASS"
        )

        print()

        print(
            "TECHNICAL CONTRACT INTEGRATION REVIEW PASSED"
        )

        print()

        print(
            "The proposed change is limited to "
            "the acquire_real_rows() data boundary."
        )

        print(
            "987 Contract records are the proposed Validator input."
        )

        print(
            "5922 historical records remain outside the Validator."
        )

        print(
            "No patch was applied."
        )

    else:

        print(
            "FINAL STATUS           : FAIL"
        )

        print()

        print(
            "INTEGRATION REVIEW FAILED"
        )

        print(
            "DO NOT APPLY PATCH."
        )

    return final_ok


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT INTEGRATION REVIEW v0.1"
    )

    kv(
        "MODE",
        "READ ONLY"
    )

    kv(
        "DATABASE",
        str(DB_PATH)
    )

    kv(
        "PRODUCTION ENGINE",
        str(PRODUCTION_ENGINE)
    )

    kv(
        "TARGET FUNCTION",
        FUNCTION_NAME
    )

    kv(
        "CONTRACT",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "EXPECTED CONTRACT ROWS",
        EXPECTED_IN_SCOPE
    )

    kv(
        "EXPECTED MUSEUM ROWS",
        EXPECTED_OUT_OF_SCOPE
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This script reviews the proposed integration only."
    )

    print(
        "NO PATCH WILL BE APPLIED."
    )

    # -------------------------------------------------------------------------
    # SOURCE
    # -------------------------------------------------------------------------

    source = read_production_source()

    original_hash = source_hash(
        source
    )

    node = resolve_function_node(
        source,
        FUNCTION_NAME
    )

    (
        function_start,
        function_end,
        function_lines,
    ) = print_function_source(
        source,
        node
    )

    # -------------------------------------------------------------------------
    # CURRENT QUERY
    # -------------------------------------------------------------------------

    current_query = print_current_query(
        node
    )

    if current_query is None:

        raise RuntimeError(
            "Cannot continue without current production query"
        )

    # -------------------------------------------------------------------------
    # PROPOSED CONTRACT QUERY
    # -------------------------------------------------------------------------

    proposed_query = print_contract_query()

    # -------------------------------------------------------------------------
    # DIFF
    # -------------------------------------------------------------------------

    diff = print_query_diff(
        current_query,
        proposed_query
    )

    # -------------------------------------------------------------------------
    # CHANGE ANALYSIS
    # -------------------------------------------------------------------------

    analysis_ok = analyze_change(
        current_query,
        proposed_query
    )

    # -------------------------------------------------------------------------
    # VALIDATOR NON-INTERFERENCE
    # -------------------------------------------------------------------------

    inspect_validator_dependency(
        source,
        node
    )

    # -------------------------------------------------------------------------
    # WRITE PATH
    # -------------------------------------------------------------------------

    write_refs = scan_write_paths(
        source
    )

    # -------------------------------------------------------------------------
    # DATABASE
    # -------------------------------------------------------------------------

    conn = None

    try:

        conn = connect_read_only()

        verify_read_only(
            conn
        )

        banner(
            "READ-ONLY DATABASE CONTRACT"
        )

        kv(
            "Connected",
            "YES"
        )

        kv(
            "SQLite query_only",
            conn.execute(
                "PRAGMA query_only"
            ).fetchone()[0]
        )

        (
            database_total,
            in_scope,
            out_scope,
            min_id,
            max_id,
            distinct_ids,
        ) = verify_contract_population(
            conn
        )

        # ---------------------------------------------------------------------
        # PROPOSED SEMANTICS
        # ---------------------------------------------------------------------

        semantics_rows = verify_contract_semantics(
            conn
        )

        # ---------------------------------------------------------------------
        # LIMIT
        # ---------------------------------------------------------------------

        limit_ok = review_limit_semantics(
            current_query,
            proposed_query
        )

        # ---------------------------------------------------------------------
        # PATCH CONTRACT
        # ---------------------------------------------------------------------

        print_patch_contract()

        # ---------------------------------------------------------------------
        # FINAL
        # ---------------------------------------------------------------------

        result = final_contract(
            source_before=source,
            current_query=current_query,
            proposed_query=proposed_query,
            database_total=database_total,
            in_scope=in_scope,
            out_scope=out_scope,
            semantics_rows=len(
                semantics_rows
            ),
            analysis_ok=analysis_ok,
            limit_ok=limit_ok,
        )

    finally:

        if conn is not None:

            conn.close()

    # -------------------------------------------------------------------------
    # SOURCE INTEGRITY
    # -------------------------------------------------------------------------

    source_after = read_production_source()

    after_hash = source_hash(
        source_after
    )

    section(
        "PRODUCTION SOURCE INTEGRITY AFTER REVIEW"
    )

    kv(
        "Hash Before",
        original_hash
    )

    kv(
        "Hash After",
        after_hash
    )

    status(
        "PRODUCTION SOURCE UNCHANGED",
        original_hash == after_hash
    )

    print()

    banner(
        "ARUNDA TECHNICAL CONTRACT INTEGRATION REVIEW v0.1 COMPLETE"
    )

    print(
        "PATCH APPLIED : NO"
    )

    print(
        "DATABASE MODIFIED : NO"
    )

    print(
        "PRODUCTION SOURCE MODIFIED : NO"
    )


if __name__ == "__main__":
    main()