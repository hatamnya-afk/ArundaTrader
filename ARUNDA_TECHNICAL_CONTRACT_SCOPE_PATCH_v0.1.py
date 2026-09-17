
import sqlite3
from pathlib import Path
from collections import Counter


# =============================================================================
# ARUNDA
# TECHNICAL CONTRACT SCOPE PATCH v0.2
# =============================================================================
#
# MODE
# ----
# READ ONLY
#
# PURPOSE
# -------
# Verify the exact trusted population that is allowed to cross the
# Technical Contract boundary.
#
#
# AUTHORITATIVE CONTRACT
# ----------------------
#
# technical_version = TECHNICAL_v0.5
# engine_version    = TECHNICAL_v0.5
# source            = REAL_MARKET_HISTORY
#
#
# EXPECTED TRUSTED POPULATION
# ---------------------------
#
# COUNT      = 987
# MIN ID     = 5923
# MAX ID     = 6909
#
#
# IMPORTANT ARCHITECTURAL RULE
# ----------------------------
#
# Contract membership is defined by the trusted Contract predicate.
#
# OUT-OF-SCOPE is the mathematical complement of the trusted population:
#
#     OUT_OF_SCOPE = ALL_DATABASE_IDS - CONTRACT_IDS
#
# Therefore:
#
#     TOTAL = IN_SCOPE + OUT_OF_SCOPE
#
#     6909 = 987 + 5922
#
#
# OUT-OF-SCOPE != INVALID
#
# Historical / foreign / pre-contract rows are simply excluded from
# Validator input.
#
#
# NO DATABASE WRITES
# ------------------
#
# INSERT      : NONE
# UPDATE      : NONE
# DELETE      : NONE
# ALTER       : NONE
# CREATE      : NONE
# DROP        : NONE
# REPLACE     : NONE
# COMMIT      : NONE
#
# NO SYNTHETIC DATA
# NO INTERPOLATION
# NO FORWARD FILL
# NO BACK FILL
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = PROJECT_DIR / "arunda.db"

TARGET_TABLE = "market_technical"


# =============================================================================
# CONTRACT
# =============================================================================

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"

CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"

CONTRACT_SOURCE = "REAL_MARKET_HISTORY"


# =============================================================================
# EXPECTED POPULATION
# =============================================================================

EXPECTED_DATABASE_TOTAL = 6909

EXPECTED_IN_SCOPE = 987

EXPECTED_OUT_OF_SCOPE = 5922

EXPECTED_MIN_ID = 5923

EXPECTED_MAX_ID = 6909


# =============================================================================
# REQUIRED COLUMNS
# =============================================================================

REQUIRED_COLUMNS = [
    "id",
    "technical_version",
    "engine_version",
    "source",
]


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

    print(
        f"{key:<50}: {value}"
    )


def status(label, condition):

    print(
        f"[{'PASS' if condition else 'FAIL'}] "
        f"{label}"
    )


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

    # SQLite-level write protection.
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
            "READ-ONLY CONTRACT FAILED"
        )

    return True


# =============================================================================
# SCHEMA DISCOVERY
# =============================================================================

def table_exists(conn):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (TARGET_TABLE,)
    ).fetchone()

    return row is not None


def get_columns(conn):

    rows = conn.execute(
        f'''
        PRAGMA table_info("{TARGET_TABLE}")
        '''
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def verify_required_columns(columns):

    section(
        "CONTRACT SCHEMA REQUIREMENTS"
    )

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in columns
    ]

    kv(
        "Required Columns",
        len(REQUIRED_COLUMNS)
    )

    kv(
        "Missing Columns",
        missing
    )

    status(
        "Required Contract columns exist",
        len(missing) == 0
    )

    if missing:

        raise RuntimeError(
            f"Missing Contract columns: {missing}"
        )


# =============================================================================
# DATABASE TOTAL
# =============================================================================

def get_database_total(conn):

    row = conn.execute(
        f'''
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        '''
    ).fetchone()

    return int(row[0])


# =============================================================================
# AUTHORITATIVE CONTRACT QUERY
# =============================================================================
#
# THIS is the only population query used to define IN-SCOPE.
#
# No LIMIT.
# No ID range restriction.
# No assumption that IDs are contiguous.
#
# =============================================================================

def acquire_contract_rows(conn):

    rows = conn.execute(
        f'''
        SELECT *
        FROM "{TARGET_TABLE}"
        WHERE
            technical_version = ?
            AND engine_version = ?
            AND source = ?
        ORDER BY id ASC
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        )
    ).fetchall()

    return rows


# =============================================================================
# CONTRACT ID SET
# =============================================================================

def build_contract_id_set(contract_rows):

    contract_ids = set()

    null_id_rows = []

    duplicate_ids = []

    for row in contract_rows:

        record_id = row["id"]

        if record_id is None:

            null_id_rows.append(
                row
            )

            continue

        if record_id in contract_ids:

            duplicate_ids.append(
                record_id
            )

        contract_ids.add(
            record_id
        )

    if null_id_rows:

        raise RuntimeError(
            "Contract population contains NULL id"
        )

    if duplicate_ids:

        raise RuntimeError(
            "Contract population contains duplicate IDs"
        )

    return contract_ids


# =============================================================================
# CONTRACT POPULATION VERIFICATION
# =============================================================================

def verify_contract_population(
    contract_rows,
    contract_ids
):

    section(
        "TRUSTED CONTRACT POPULATION VERIFICATION"
    )

    actual_count = len(
        contract_rows
    )

    distinct_ids = len(
        contract_ids
    )

    actual_min = (
        min(contract_ids)
        if contract_ids
        else None
    )

    actual_max = (
        max(contract_ids)
        if contract_ids
        else None
    )

    kv(
        "Expected Contract Rows",
        EXPECTED_IN_SCOPE
    )

    kv(
        "Actual Contract Rows",
        actual_count
    )

    status(
        "COUNT = 987",
        actual_count == EXPECTED_IN_SCOPE
    )

    kv(
        "Expected MIN ID",
        EXPECTED_MIN_ID
    )

    kv(
        "Actual MIN ID",
        actual_min
    )

    status(
        "MIN ID = 5923",
        actual_min == EXPECTED_MIN_ID
    )

    kv(
        "Expected MAX ID",
        EXPECTED_MAX_ID
    )

    kv(
        "Actual MAX ID",
        actual_max
    )

    status(
        "MAX ID = 6909",
        actual_max == EXPECTED_MAX_ID
    )

    kv(
        "Distinct IDs",
        distinct_ids
    )

    status(
        "DISTINCT IDS = 987",
        distinct_ids == EXPECTED_IN_SCOPE
    )

    if actual_count != EXPECTED_IN_SCOPE:

        raise RuntimeError(
            "CONTRACT POPULATION COUNT VIOLATION"
        )

    if distinct_ids != EXPECTED_IN_SCOPE:

        raise RuntimeError(
            "CONTRACT DISTINCT ID VIOLATION"
        )

    if actual_min != EXPECTED_MIN_ID:

        raise RuntimeError(
            "CONTRACT MIN ID VIOLATION"
        )

    if actual_max != EXPECTED_MAX_ID:

        raise RuntimeError(
            "CONTRACT MAX ID VIOLATION"
        )


# =============================================================================
# CONTRACT FIELD INTEGRITY
# =============================================================================

def verify_contract_fields(
    contract_rows
):

    section(
        "CONTRACT FIELD INTEGRITY"
    )

    counters = {
        "technical_version": Counter(),
        "engine_version": Counter(),
        "source": Counter(),
    }

    violations = []

    for row in contract_rows:

        technical_version = row[
            "technical_version"
        ]

        engine_version = row[
            "engine_version"
        ]

        source = row[
            "source"
        ]

        counters[
            "technical_version"
        ][technical_version] += 1

        counters[
            "engine_version"
        ][engine_version] += 1

        counters[
            "source"
        ][source] += 1

        if technical_version != (
            CONTRACT_TECHNICAL_VERSION
        ):

            violations.append(
                (
                    row["id"],
                    "technical_version",
                    technical_version,
                )
            )

        if engine_version != (
            CONTRACT_ENGINE_VERSION
        ):

            violations.append(
                (
                    row["id"],
                    "engine_version",
                    engine_version,
                )
            )

        if source != CONTRACT_SOURCE:

            violations.append(
                (
                    row["id"],
                    "source",
                    source,
                )
            )

    print()

    print(
        "technical_version:"
    )

    for value, count in (
        counters[
            "technical_version"
        ].most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    print(
        "engine_version:"
    )

    for value, count in (
        counters[
            "engine_version"
        ].most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    print(
        "source:"
    )

    for value, count in (
        counters[
            "source"
        ].most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    kv(
        "Contract Violations",
        len(violations)
    )

    status(
        "ALL CONTRACT ROWS SATISFY CONTRACT",
        len(violations) == 0
    )

    if violations:

        print()

        print(
            "FIRST CONTRACT VIOLATIONS:"
        )

        for item in violations[:20]:

            print(
                f"  id={item[0]} "
                f"field={item[1]} "
                f"value={item[2]!r}"
            )

        raise RuntimeError(
            "CONTRACT FIELD INTEGRITY VIOLATION"
        )


# =============================================================================
# DATABASE ID POPULATION
# =============================================================================

def acquire_all_database_ids(conn):

    rows = conn.execute(
        f'''
        SELECT id
        FROM "{TARGET_TABLE}"
        ORDER BY id ASC
        '''
    ).fetchall()

    all_ids = set()

    null_ids = []

    duplicate_ids = []

    for row in rows:

        record_id = row["id"]

        if record_id is None:

            null_ids.append(
                row
            )

            continue

        if record_id in all_ids:

            duplicate_ids.append(
                record_id
            )

        all_ids.add(
            record_id
        )

    if null_ids:

        raise RuntimeError(
            "Database contains NULL primary IDs"
        )

    if duplicate_ids:

        raise RuntimeError(
            "Database contains duplicate IDs"
        )

    return all_ids


# =============================================================================
# OUT-OF-SCOPE COMPLEMENT
# =============================================================================
#
# AUTHORITATIVE DEFINITION:
#
#     OUT_OF_SCOPE = ALL_DATABASE_IDS - CONTRACT_IDS
#
# CRITICAL:
#
# We NEVER calculate OUT_OF_SCOPE as:
#
#     technical_version != ...
#
# or:
#
#     source != ...
#
# or:
#
#     history_points != ...
#
# because those are field classifications, not population membership.
#
# =============================================================================

def verify_out_of_scope_population(
    all_ids,
    contract_ids,
    database_total
):

    section(
        "OUT-OF-SCOPE POPULATION COMPLEMENT"
    )

    outside_ids = (
        all_ids - contract_ids
    )

    # -------------------------------------------------------------------------
    # CORRECT OVERLAP TEST
    # -------------------------------------------------------------------------
    #
    # This MUST be:
    #
    #     outside_ids & contract_ids
    #
    # NOT:
    #
    #     all_ids & contract_ids
    #
    # because all Contract IDs necessarily belong to the database.
    #
    # -------------------------------------------------------------------------

    overlap = (
        outside_ids & contract_ids
    )

    in_scope_count = len(
        contract_ids
    )

    out_scope_count = len(
        outside_ids
    )

    expected_out_scope = (
        database_total
        - in_scope_count
    )

    kv(
        "Database Total",
        database_total
    )

    kv(
        "Contract Population",
        in_scope_count
    )

    kv(
        "Excluded Population",
        out_scope_count
    )

    kv(
        "Expected Excluded",
        expected_out_scope
    )

    kv(
        "Contract/Excluded Overlap",
        len(overlap)
    )

    status(
        "Excluded = Database Total - Contract",
        out_scope_count == expected_out_scope
    )

    status(
        "Excluded = 5922",
        out_scope_count == EXPECTED_OUT_OF_SCOPE
    )

    status(
        "Contract/Excluded Overlap = 0",
        len(overlap) == 0
    )

    if out_scope_count != expected_out_scope:

        raise RuntimeError(
            "OUT-OF-SCOPE POPULATION VIOLATION"
        )

    if out_scope_count != EXPECTED_OUT_OF_SCOPE:

        raise RuntimeError(
            "OUT-OF-SCOPE EXPECTED COUNT VIOLATION"
        )

    if overlap:

        print()

        print(
            "OVERLAPPING IDS:"
        )

        for record_id in sorted(
            overlap
        )[:20]:

            print(
                f"  {record_id}"
            )

        raise RuntimeError(
            "CONTRACT / OUT-OF-SCOPE OVERLAP"
        )

    return outside_ids


# =============================================================================
# OUT-OF-SCOPE DESCRIPTIVE FORENSICS
# =============================================================================
#
# This section is intentionally NON-AUTHORITATIVE.
#
# It describes the 5922 excluded records.
#
# It does NOT validate them.
# It does NOT classify them as INVALID.
# It does NOT send them to Validator.
#
# =============================================================================

def inspect_out_of_scope_shape(
    conn,
    outside_ids
):

    section(
        "OUT-OF-SCOPE HISTORICAL SHAPE"
    )

    if not outside_ids:

        print(
            "No OUT-OF-SCOPE records."
        )

        return

    # SQLite has a bound-variable limit on many builds.
    # We therefore inspect by joining through the IDs using a
    # temporary in-memory Python-side classification rather than
    # creating a database temporary table.
    #
    # To keep this forensic strictly read-only, query the full
    # descriptive fields and classify them in memory.

    rows = conn.execute(
        f'''
        SELECT
            id,
            technical_version,
            engine_version,
            source,
            history_points
        FROM "{TARGET_TABLE}"
        ORDER BY id ASC
        '''
    ).fetchall()

    technical_versions = Counter()

    engine_versions = Counter()

    sources = Counter()

    history_points = Counter()

    observed_out_scope = 0

    for row in rows:

        record_id = row["id"]

        if record_id not in outside_ids:

            continue

        observed_out_scope += 1

        technical_versions[
            row["technical_version"]
        ] += 1

        engine_versions[
            row["engine_version"]
        ] += 1

        sources[
            row["source"]
        ] += 1

        history_points[
            row["history_points"]
        ] += 1

    kv(
        "Observed OUT-OF-SCOPE Rows",
        observed_out_scope
    )

    status(
        "Observed OUT-OF-SCOPE = 5922",
        observed_out_scope == EXPECTED_OUT_OF_SCOPE
    )

    print()

    print(
        "technical_version:"
    )

    for value, count in (
        technical_versions.most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    print(
        "engine_version:"
    )

    for value, count in (
        engine_versions.most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    print(
        "source:"
    )

    for value, count in (
        sources.most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    print(
        "history_points:"
    )

    for value, count in (
        history_points.most_common()
    ):

        print(
            f"  {value!r:<35} {count}"
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "OUT-OF-SCOPE distribution is descriptive only."
    )

    print(
        "It does NOT define Contract membership."
    )

    print(
        "OUT-OF-SCOPE != INVALID."
    )

    print(
        "These records are not Validator input."
    )


# =============================================================================
# VALIDATOR INPUT CONTRACT
# =============================================================================

def verify_validator_input_boundary(
    contract_rows,
    outside_ids
):

    section(
        "CONTRACT-FIRST VALIDATOR INPUT BOUNDARY"
    )

    validator_input_ids = {
        row["id"]
        for row in contract_rows
    }

    excluded_ids = set(
        outside_ids
    )

    overlap = (
        validator_input_ids
        & excluded_ids
    )

    kv(
        "Rows Sent To Validator",
        len(validator_input_ids)
    )

    kv(
        "Expected Validator Input",
        EXPECTED_IN_SCOPE
    )

    kv(
        "Rows Excluded",
        len(excluded_ids)
    )

    kv(
        "Expected Excluded",
        EXPECTED_OUT_OF_SCOPE
    )

    kv(
        "Validator Input / Excluded Overlap",
        len(overlap)
    )

    status(
        "VALIDATOR INPUT = 987",
        len(validator_input_ids)
        == EXPECTED_IN_SCOPE
    )

    status(
        "EXCLUDED = 5922",
        len(excluded_ids)
        == EXPECTED_OUT_OF_SCOPE
    )

    status(
        "VALIDATOR INPUT / EXCLUDED OVERLAP = 0",
        len(overlap) == 0
    )

    if len(validator_input_ids) != EXPECTED_IN_SCOPE:

        raise RuntimeError(
            "VALIDATOR INPUT COUNT VIOLATION"
        )

    if len(excluded_ids) != EXPECTED_OUT_OF_SCOPE:

        raise RuntimeError(
            "VALIDATOR EXCLUSION COUNT VIOLATION"
        )

    if overlap:

        raise RuntimeError(
            "VALIDATOR INPUT / EXCLUDED OVERLAP"
        )


# =============================================================================
# SCOPE CONSERVATION
# =============================================================================

def verify_scope_conservation(
    database_total,
    contract_ids,
    outside_ids
):

    section(
        "SCOPE CONSERVATION"
    )

    in_scope = len(
        contract_ids
    )

    out_scope = len(
        outside_ids
    )

    reconstructed_total = (
        in_scope
        + out_scope
    )

    kv(
        "IN-SCOPE",
        in_scope
    )

    kv(
        "OUT-OF-SCOPE",
        out_scope
    )

    kv(
        "SUM",
        f"{in_scope} + {out_scope} = {reconstructed_total}"
    )

    kv(
        "DATABASE TOTAL",
        database_total
    )

    status(
        "IN-SCOPE + OUT-OF-SCOPE = DATABASE TOTAL",
        reconstructed_total == database_total
    )

    status(
        "987 + 5922 = 6909",
        (
            in_scope == EXPECTED_IN_SCOPE
            and out_scope == EXPECTED_OUT_OF_SCOPE
            and reconstructed_total == EXPECTED_DATABASE_TOTAL
        )
    )

    if reconstructed_total != database_total:

        raise RuntimeError(
            "SCOPE CONSERVATION VIOLATION"
        )

    if reconstructed_total != EXPECTED_DATABASE_TOTAL:

        raise RuntimeError(
            "EXPECTED TOTAL CONSERVATION VIOLATION"
        )


# =============================================================================
# CONTRACT ACQUISITION SUMMARY
# =============================================================================

def print_acquisition_summary(
    contract_rows
):

    section(
        "CONTRACT-FIRST REAL ROW ACQUISITION"
    )

    kv(
        "Rows Acquired",
        len(contract_rows)
    )

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

    kv(
        "Synthetic Rows",
        "NONE"
    )

    kv(
        "Interpolation",
        "NONE"
    )

    kv(
        "Forward Fill",
        "NONE"
    )

    kv(
        "Back Fill",
        "NONE"
    )

    kv(
        "Database Writes",
        "NONE"
    )

    status(
        "ROWS ACQUIRED FOR VALIDATOR = 987",
        len(contract_rows)
        == EXPECTED_IN_SCOPE
    )


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(
    database_total,
    contract_ids,
    outside_ids
):

    banner(
        "FINAL TECHNICAL CONTRACT SCOPE PATCH v0.2"
    )

    in_scope = len(
        contract_ids
    )

    out_scope = len(
        outside_ids
    )

    kv(
        "DATABASE TOTAL",
        database_total
    )

    kv(
        "IN-SCOPE",
        in_scope
    )

    kv(
        "OUT-OF-SCOPE",
        out_scope
    )

    kv(
        "CONTRACT TECHNICAL VERSION",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "CONTRACT ENGINE VERSION",
        CONTRACT_ENGINE_VERSION
    )

    kv(
        "CONTRACT SOURCE",
        CONTRACT_SOURCE
    )

    print()

    status(
        "DATABASE TOTAL = 6909",
        database_total == EXPECTED_DATABASE_TOTAL
    )

    status(
        "IN-SCOPE = 987",
        in_scope == EXPECTED_IN_SCOPE
    )

    status(
        "OUT-OF-SCOPE = 5922",
        out_scope == EXPECTED_OUT_OF_SCOPE
    )

    status(
        "CONSERVATION = 987 + 5922 = 6909",
        (
            in_scope
            + out_scope
            == database_total
        )
    )

    print()

    kv(
        "5922 HISTORICAL RECORDS",
        "EXCLUDED FROM VALIDATOR INPUT"
    )

    kv(
        "5922 CLASSIFIED AS INVALID",
        "NO"
    )

    kv(
        "DATABASE WRITES",
        "NONE"
    )

    kv(
        "PRODUCTION EXECUTION",
        "NONE"
    )

    kv(
        "NETWORK",
        "NONE"
    )

    print()

    if (
        database_total == EXPECTED_DATABASE_TOTAL
        and in_scope == EXPECTED_IN_SCOPE
        and out_scope == EXPECTED_OUT_OF_SCOPE
        and (
            in_scope
            + out_scope
            == database_total
        )
    ):

        print(
            "FINAL STATUS           : PASS"
        )

        print()

        print(
            "TECHNICAL CONTRACT SCOPE VERIFIED"
        )

        print()

        print(
            "987 records are IN-SCOPE."
        )

        print(
            "5922 records are OUT-OF-SCOPE."
        )

        print(
            "OUT-OF-SCOPE != INVALID."
        )

        print()

        print(
            "CONTRACT-FIRST VALIDATOR INPUT = 987"
        )

        print(
            "HISTORICAL MUSEUM POPULATION = 5922"
        )

    else:

        print(
            "FINAL STATUS           : FAIL"
        )

        raise RuntimeError(
            "FINAL CONTRACT SCOPE FAILURE"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL CONTRACT SCOPE PATCH v0.2"
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
        "TARGET TABLE",
        TARGET_TABLE
    )

    kv(
        "CONTRACT",
        CONTRACT_TECHNICAL_VERSION
    )

    kv(
        "EXPECTED DATABASE TOTAL",
        EXPECTED_DATABASE_TOTAL
    )

    kv(
        "EXPECTED CONTRACT ROWS",
        EXPECTED_IN_SCOPE
    )

    kv(
        "EXPECTED OUT-OF-SCOPE",
        EXPECTED_OUT_OF_SCOPE
    )

    kv(
        "EXPECTED MIN ID",
        EXPECTED_MIN_ID
    )

    kv(
        "EXPECTED MAX ID",
        EXPECTED_MAX_ID
    )

    conn = None

    try:

        # =====================================================================
        # DATABASE
        # =====================================================================

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

        if not table_exists(
            conn
        ):

            raise RuntimeError(
                f"Missing table: {TARGET_TABLE}"
            )

        columns = get_columns(
            conn
        )

        kv(
            "Target Table",
            TARGET_TABLE
        )

        kv(
            "Column Count",
            len(columns)
        )

        verify_required_columns(
            columns
        )

        # =====================================================================
        # DATABASE TOTAL
        # =====================================================================

        database_total = get_database_total(
            conn
        )

        banner(
            "DATABASE TOTAL"
        )

        kv(
            "Total market_technical rows",
            database_total
        )

        status(
            "DATABASE TOTAL = 6909",
            database_total == EXPECTED_DATABASE_TOTAL
        )

        if database_total != EXPECTED_DATABASE_TOTAL:

            raise RuntimeError(
                "DATABASE TOTAL VIOLATION"
            )

        # =====================================================================
        # CONTRACT POPULATION
        # =====================================================================

        contract_rows = acquire_contract_rows(
            conn
        )

        contract_ids = build_contract_id_set(
            contract_rows
        )

        print_acquisition_summary(
            contract_rows
        )

        verify_contract_population(
            contract_rows,
            contract_ids
        )

        verify_contract_fields(
            contract_rows
        )

        # =====================================================================
        # ALL DATABASE IDS
        # =====================================================================

        all_ids = acquire_all_database_ids(
            conn
        )

        status(
            "ALL DATABASE IDS = DATABASE TOTAL",
            len(all_ids) == database_total
        )

        if len(all_ids) != database_total:

            raise RuntimeError(
                "DATABASE ID POPULATION VIOLATION"
            )

        # =====================================================================
        # OUT-OF-SCOPE COMPLEMENT
        # =====================================================================

        outside_ids = verify_out_of_scope_population(
            all_ids,
            contract_ids,
            database_total
        )

        # =====================================================================
        # DESCRIPTIVE ONLY
        # =====================================================================

        inspect_out_of_scope_shape(
            conn,
            outside_ids
        )

        # =====================================================================
        # VALIDATOR INPUT
        # =====================================================================

        verify_validator_input_boundary(
            contract_rows,
            outside_ids
        )

        # =====================================================================
        # CONSERVATION
        # =====================================================================

        verify_scope_conservation(
            database_total,
            contract_ids,
            outside_ids
        )

        # =====================================================================
        # FINAL
        # =====================================================================

        final_contract(
            database_total,
            contract_ids,
            outside_ids
        )

    finally:

        if conn is not None:

            conn.close()

    print()

    print(
        "=" * 100
    )

    print(
        "ARUNDA TECHNICAL CONTRACT SCOPE PATCH v0.2 COMPLETE"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()
