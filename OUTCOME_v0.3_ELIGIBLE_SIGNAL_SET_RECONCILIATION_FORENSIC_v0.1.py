# ==============================================================================
# OUTCOME v0.3 ELIGIBLE SIGNAL SET RECONCILIATION FORENSIC v0.1
# ==============================================================================
#
# MODE:
#     READ ONLY / FORENSIC ONLY
#
# PURPOSE:
#     Reconcile the production Outcome Engine's eligible Fusion signal set
#     against the raw fusion_signals population and the actual eligibility
#     logic present in signal_outcome_engine.py.
#
# SAFETY:
#     Production DB is NEVER modified.
#     Production source is NEVER modified.
#     No INSERT
#     No UPDATE
#     No DELETE
#     No ALTER
#     No CREATE
#     No synthetic data
#     No interpolation
#     No forward fill
#     No back fill
#
# ==============================================================================

from __future__ import annotations

import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone


# ==============================================================================
# CONFIGURATION
# ==============================================================================

DB_PATH = "arunda.db"
ENGINE_PATH = "signal_outcome_engine.py"

EXPECTED_OUTCOME_VERSION = "OUTCOME_v0.3.2"

HORIZONS = {
    "5m": {
        "seconds": 5 * 60,
        "tolerance": 600,
    },
    "15m": {
        "seconds": 15 * 60,
        "tolerance": 300,
    },
    "30m": {
        "seconds": 30 * 60,
        "tolerance": 600,
    },
    "60m": {
        "seconds": 60 * 60,
        "tolerance": 900,
    },
}


# ==============================================================================
# OUTPUT HELPERS
# ==============================================================================

WIDTH = 90


def line(char="=", width=WIDTH):
    print(char * width)


def title(text):
    line("=")
    print(text)
    line("=")


def section(text):
    print()
    line("=")
    print(text)
    line("=")


def subsection(text):
    print()
    line("-")
    print(text)
    line("-")


def fmt_value(value, width=0):
    if value is None:
        text = "None"
    else:
        text = str(value)

    if width:
        return f"{text:<{width}}"

    return text


# ==============================================================================
# DATABASE HELPERS
# ==============================================================================

def connect_readonly(db_path):
    """
    Open SQLite database in READ ONLY mode.

    The URI mode=ro prevents accidental writes.
    """

    absolute = os.path.abspath(db_path)

    if not os.path.exists(absolute):
        raise FileNotFoundError(
            f"Database not found: {absolute}"
        )

    uri = f"file:{absolute}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )

    conn.row_factory = sqlite3.Row

    return conn


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row["name"] for row in rows]


def resolve_column(columns, candidates):
    """
    Resolve a column name using case-insensitive matching.
    """

    lookup = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in candidates:
        found = lookup.get(candidate.lower())

        if found is not None:
            return found

    return None


# ==============================================================================
# SOURCE HELPERS
# ==============================================================================

def read_engine_source(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Production engine not found: {os.path.abspath(path)}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        return handle.read()


def get_source_line_number(source, position):
    return source.count("\n", 0, position) + 1


def find_source_lines(source, patterns):
    """
    Read-only source inspection.

    Returns matching source lines and their line numbers.
    """

    results = []

    lines = source.splitlines()

    compiled = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in patterns
    ]

    for index, text in enumerate(lines, start=1):

        for pattern in compiled:

            if pattern.search(text):
                results.append(
                    (
                        index,
                        text.rstrip(),
                    )
                )
                break

    return results


# ==============================================================================
# SAFE SQL EXTRACTION
# ==============================================================================

def extract_sql_statements(source):
    """
    Extract SQL-looking statements from the production source.

    IMPORTANT:
        This function NEVER executes SQL.

    This implementation intentionally avoids fragile inline regex flags such
    as (?is), which caused Python 3.13's:

        re.PatternError:
        global flags not at the start of the expression

    All regex flags are supplied explicitly through re.IGNORECASE and
    re.DOTALL.
    """

    statements = []

    # ------------------------------------------------------------------
    # conn.execute(""" ... """)
    # conn.execute(''' ... ''')
    # ------------------------------------------------------------------

    pattern_triple = re.compile(
        r"""
        \b
        (?:conn|connection|db|database)
        \s*
        \.
        \s*
        execute
        \s*
        \(
        \s*
        (?P<quote>""" + '"""' + r"|'''"
        + r""")
        (?P<sql>.*?)
        (?P=quote)
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    for match in pattern_triple.finditer(source):

        sql = match.group("sql").strip()

        if sql:
            statements.append(
                {
                    "kind": "execute",
                    "sql": sql,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    # ------------------------------------------------------------------
    # conn.execute("SELECT ...")
    # conn.execute('SELECT ...')
    # ------------------------------------------------------------------

    pattern_single = re.compile(
        r"""
        \b
        (?:conn|connection|db|database)
        \s*
        \.
        \s*
        execute
        \s*
        \(
        \s*
        (?P<quote>"|')
        (?P<sql>.*?)
        (?P=quote)
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    for match in pattern_single.finditer(source):

        sql = match.group("sql").strip()

        if sql:
            statements.append(
                {
                    "kind": "execute",
                    "sql": sql,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    # ------------------------------------------------------------------
    # conn.executemany(""" ... """)
    # conn.executemany(''' ... ''')
    # ------------------------------------------------------------------

    pattern_executemany = re.compile(
        r"""
        \b
        (?:conn|connection|db|database)
        \s*
        \.
        \s*
        executemany
        \s*
        \(
        \s*
        (?P<quote>""" + '"""' + r"|'''"
        + r""")
        (?P<sql>.*?)
        (?P=quote)
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    for match in pattern_executemany.finditer(source):

        sql = match.group("sql").strip()

        if sql:
            statements.append(
                {
                    "kind": "executemany",
                    "sql": sql,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    # ------------------------------------------------------------------
    # Deduplicate and restore source order.
    # ------------------------------------------------------------------

    unique = []
    seen = set()

    for item in sorted(
        statements,
        key=lambda item: item["start"],
    ):

        key = (
            item["kind"],
            item["start"],
            item["end"],
            item["sql"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


# ==============================================================================
# SQL CLASSIFICATION
# ==============================================================================

def classify_sql(sql):
    normalized = " ".join(
        sql.strip().upper().split()
    )

    if normalized.startswith("SELECT"):
        return "SELECT"

    if normalized.startswith("INSERT"):
        return "INSERT"

    if normalized.startswith("UPDATE"):
        return "UPDATE"

    if normalized.startswith("DELETE"):
        return "DELETE"

    if normalized.startswith("ALTER"):
        return "ALTER"

    if normalized.startswith("CREATE"):
        return "CREATE"

    if normalized.startswith("DROP"):
        return "DROP"

    if normalized.startswith("REPLACE"):
        return "REPLACE"

    return "OTHER"


# ==============================================================================
# TIMESTAMP HELPERS
# ==============================================================================

def parse_timestamp(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()

        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


# ==============================================================================
# SIGNAL COLUMN MAP
# ==============================================================================

def build_fusion_column_map(columns):

    return {
        "id": resolve_column(
            columns,
            [
                "id",
                "signal_id",
            ],
        ),

        "asset": resolve_column(
            columns,
            [
                "asset",
                "symbol",
                "ticker",
            ],
        ),

        "timestamp": resolve_column(
            columns,
            [
                "timestamp",
                "entry_timestamp",
                "created_at",
                "time",
            ],
        ),

        "direction": resolve_column(
            columns,
            [
                "direction",
                "signal_direction",
                "side",
            ],
        ),

        "score": resolve_column(
            columns,
            [
                "fused_score",
                "score",
                "signal_score",
                "confidence_score",
            ],
        ),
    }


# ==============================================================================
# QUALITY FORENSIC
# ==============================================================================

def fetch_fusion_rows(conn, column_map):

    required = [
        column_map["id"],
        column_map["asset"],
        column_map["timestamp"],
        column_map["direction"],
    ]

    if any(column is None for column in required):
        return []

    id_col = column_map["id"]
    asset_col = column_map["asset"]
    timestamp_col = column_map["timestamp"]
    direction_col = column_map["direction"]

    query = f"""
        SELECT
            "{id_col}" AS signal_id,
            "{asset_col}" AS asset,
            "{timestamp_col}" AS timestamp,
            "{direction_col}" AS direction
        FROM fusion_signals
    """

    return conn.execute(query).fetchall()


def quality_counts(rows):

    ids = [
        row["signal_id"]
        for row in rows
    ]

    symbols = [
        row["asset"]
        for row in rows
    ]

    timestamps = [
        row["timestamp"]
        for row in rows
    ]

    directions = [
        row["direction"]
        for row in rows
    ]

    duplicate_ids = sum(
        count - 1
        for count in Counter(ids).values()
        if count > 1
    )

    null_ids = sum(
        value is None
        for value in ids
    )

    null_symbols = sum(
        value is None
        or str(value).strip() == ""
        for value in symbols
    )

    null_timestamps = sum(
        value is None
        or str(value).strip() == ""
        for value in timestamps
    )

    null_directions = sum(
        value is None
        or str(value).strip() == ""
        for value in directions
    )

    return {
        "duplicate_ids": duplicate_ids,
        "null_ids": null_ids,
        "null_symbols": null_symbols,
        "null_timestamps": null_timestamps,
        "null_directions": null_directions,
    }


# ==============================================================================
# OBJECTIVE POPULATION
# ==============================================================================

def is_valid_id(value):
    return value is not None


def is_valid_timestamp(value):
    if value is None:
        return False

    return parse_timestamp(value) is not None


def is_valid_symbol(value):
    if value is None:
        return False

    return bool(str(value).strip())


def normalize_direction(value):
    if value is None:
        return None

    text = str(value).strip().upper()

    if text in {
        "LONG",
        "SHORT",
        "FLAT",
    }:
        return text

    return None


def build_objective_populations(rows):

    all_rows = list(rows)

    valid_id = [
        row
        for row in all_rows
        if is_valid_id(row["signal_id"])
    ]

    valid_timestamp = [
        row
        for row in valid_id
        if is_valid_timestamp(row["timestamp"])
    ]

    valid_symbol = [
        row
        for row in valid_timestamp
        if is_valid_symbol(row["asset"])
    ]

    valid_direction = [
        row
        for row in valid_symbol
        if normalize_direction(row["direction"]) is not None
    ]

    return {
        "ALL_FUSION": all_rows,
        "VALID_ID": valid_id,
        "VALID_TIMESTAMP": valid_timestamp,
        "VALID_SYMBOL": valid_symbol,
        "VALID_DIRECTION": valid_direction,
    }


# ==============================================================================
# OUTCOME TABLE DISCOVERY
# ==============================================================================

def discover_signal_tables(conn):

    candidates = [
        "fusion_signals",
        "hunter_signals",
        "news_signals",
        "opportunity_signals",
        "signal_outcomes",
    ]

    result = {}

    for table in candidates:
        result[table] = table_exists(
            conn,
            table,
        )

    return result


# ==============================================================================
# OUTCOME SIGNAL ID FORENSIC
# ==============================================================================

def outcome_signal_id_population(conn):

    if not table_exists(
        conn,
        "signal_outcomes",
    ):
        return {
            "column": None,
            "distinct_ids": 0,
        }

    columns = get_columns(
        conn,
        "signal_outcomes",
    )

    signal_id_col = resolve_column(
        columns,
        [
            "signal_id",
            "id",
        ],
    )

    if signal_id_col is None:
        return {
            "column": None,
            "distinct_ids": 0,
        }

    row = conn.execute(
        f"""
        SELECT COUNT(DISTINCT "{signal_id_col}")
        FROM signal_outcomes
        WHERE "{signal_id_col}" IS NOT NULL
        """
    ).fetchone()

    return {
        "column": signal_id_col,
        "distinct_ids": int(row[0] or 0),
    }


# ==============================================================================
# SOURCE ELIGIBILITY FORENSIC
# ==============================================================================

def print_eligibility_source_locations(source):

    patterns = [
        r"def\s+process_signals",
        r"FROM\s+fusion_signals",
        r"direction",
        r"Eligible Fusion signals",
        r"WHERE",
        r"ORDER BY",
        r"fused_score",
        r"signal_outcomes",
    ]

    matches = find_source_lines(
        source,
        patterns,
    )

    print(
        "Eligibility-related source locations"
    )

    for line_number, text in matches:

        print(
            f"{line_number:4d} | {text}"
        )


# ==============================================================================
# SOURCE ELIGIBILITY QUERY ANALYSIS
# ==============================================================================

def analyze_source_sql(source):

    statements = extract_sql_statements(
        source
    )

    classifications = Counter()

    relevant = []

    for item in statements:

        sql = item["sql"]

        classification = classify_sql(
            sql
        )

        classifications[
            classification
        ] += 1

        upper = sql.upper()

        if (
            "FUSION_SIGNALS" in upper
            or "SIGNAL_OUTCOMES" in upper
            or "DIRECTION" in upper
            or "FUSED_SCORE" in upper
        ):
            relevant.append(
                item
            )

    return statements, classifications, relevant


# ==============================================================================
# RECONCILIATION
# ==============================================================================

def reconcile_signal_sets(
    rows,
    populations,
):

    all_ids = {
        row["signal_id"]
        for row in populations["ALL_FUSION"]
        if row["signal_id"] is not None
    }

    valid_direction_ids = {
        row["signal_id"]
        for row in populations["VALID_DIRECTION"]
        if row["signal_id"] is not None
    }

    excluded_ids = sorted(
        all_ids - valid_direction_ids
    )

    return {
        "all_count": len(
            populations["ALL_FUSION"]
        ),

        "valid_id_count": len(
            populations["VALID_ID"]
        ),

        "valid_timestamp_count": len(
            populations["VALID_TIMESTAMP"]
        ),

        "valid_symbol_count": len(
            populations["VALID_SYMBOL"]
        ),

        "valid_direction_count": len(
            populations["VALID_DIRECTION"]
        ),

        "excluded_ids": excluded_ids,
    }


# ==============================================================================
# PRINT RECONCILIATION DETAIL
# ==============================================================================

def print_excluded_signal_detail(
    rows,
    excluded_ids,
):

    if not excluded_ids:
        print(
            "No signals excluded by direction eligibility."
        )
        return

    subsection(
        "SIGNALS EXCLUDED BY DIRECTION ELIGIBILITY"
    )

    row_map = {
        row["signal_id"]: row
        for row in rows
        if row["signal_id"] is not None
    }

    for signal_id in excluded_ids:

        row = row_map.get(
            signal_id
        )

        if row is None:
            continue

        print(
            f"Signal #{signal_id:<5} | "
            f"{str(row['asset']):<6} | "
            f"timestamp={row['timestamp']} | "
            f"direction={row['direction']!r}"
        )


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    title(
        "OUTCOME v0.3 ELIGIBLE SIGNAL SET "
        "RECONCILIATION FORENSIC v0.1"
    )

    print(
        f"Database          : {DB_PATH}"
    )

    print(
        f"Engine            : {ENGINE_PATH}"
    )

    print(
        f"Outcome version   : "
        f"{EXPECTED_OUTCOME_VERSION}"
    )

    print(
        "Mode              : READ ONLY"
    )

    print(
        "Production DB     : UNMODIFIED"
    )

    print(
        "Production source : UNMODIFIED"
    )

    print(
        "Synthetic data    : FORBIDDEN"
    )

    print(
        "Interpolation     : FORBIDDEN"
    )

    print(
        "Forward fill      : FORBIDDEN"
    )

    print(
        "Back fill         : FORBIDDEN"
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    conn = None

    try:

        conn = connect_readonly(
            DB_PATH
        )

        # ==============================================================
        # DATABASE STRUCTURE
        # ==============================================================

        section(
            "DATABASE STRUCTURE CHECK"
        )

        required_tables = [
            "fusion_signals",
            "market_data",
        ]

        structure_ok = True

        for table in required_tables:

            exists = table_exists(
                conn,
                table,
            )

            print(
                f"{table:<20} | "
                f"{'PASS' if exists else 'FAIL'}"
            )

            if not exists:
                structure_ok = False

        if not structure_ok:

            print()
            print(
                "VERDICT: REQUIRED DATABASE "
                "STRUCTURE NOT AVAILABLE."
            )

            return

        # ==============================================================
        # FUSION COLUMN MAP
        # ==============================================================

        section(
            "FUSION SIGNAL COLUMN MAP"
        )

        fusion_columns = get_columns(
            conn,
            "fusion_signals",
        )

        column_map = build_fusion_column_map(
            fusion_columns
        )

        for logical_name in [
            "id",
            "asset",
            "timestamp",
            "direction",
            "score",
        ]:

            physical = column_map[
                logical_name
            ]

            print(
                f"{logical_name:<12} | "
                f"{physical if physical else 'NOT FOUND'}"
            )

        # ==============================================================
        # RAW SIGNAL POPULATION
        # ==============================================================

        rows = fetch_fusion_rows(
            conn,
            column_map,
        )

        section(
            "RAW FUSION SIGNAL POPULATION"
        )

        distinct_ids = len(
            {
                row["signal_id"]
                for row in rows
                if row["signal_id"] is not None
            }
        )

        print(
            f"Total fusion_signals rows : "
            f"{len(rows)}"
        )

        print(
            f"Distinct signal IDs       : "
            f"{distinct_ids}"
        )

        # ==============================================================
        # SIGNAL QUALITY
        # ==============================================================

        section(
            "SIGNAL QUALITY FORENSIC"
        )

        quality = quality_counts(
            rows
        )

        print(
            f"Duplicate IDs       : "
            f"{quality['duplicate_ids']}"
        )

        print(
            f"NULL IDs            : "
            f"{quality['null_ids']}"
        )

        print(
            f"NULL symbols        : "
            f"{quality['null_symbols']}"
        )

        print(
            f"NULL timestamps     : "
            f"{quality['null_timestamps']}"
        )

        print(
            f"NULL directions     : "
            f"{quality['null_directions']}"
        )

        # ==============================================================
        # OBJECTIVE POPULATIONS
        # ==============================================================

        populations = (
            build_objective_populations(
                rows
            )
        )

        section(
            "OBJECTIVE SIGNAL POPULATIONS"
        )

        for name in [
            "ALL_FUSION",
            "VALID_ID",
            "VALID_TIMESTAMP",
            "VALID_SYMBOL",
            "VALID_DIRECTION",
        ]:

            print(
                f"{name:<20} : "
                f"{len(populations[name])}"
            )

        # ==============================================================
        # TABLE DISCOVERY
        # ==============================================================

        section(
            "OUTCOME / SIGNAL TABLE DISCOVERY"
        )

        discovered = discover_signal_tables(
            conn
        )

        for table, exists in discovered.items():

            print(
                f"{table:<30} | "
                f"{'FOUND' if exists else 'NOT FOUND'}"
            )

        # ==============================================================
        # OUTCOME SIGNAL IDS
        # ==============================================================

        section(
            "OUTCOME SIGNAL-ID POPULATION"
        )

        outcome_ids = (
            outcome_signal_id_population(
                conn
            )
        )

        if outcome_ids["column"]:

            print(
                f"signal_outcomes"
                f"{' ':<16} | "
                f"Column={outcome_ids['column']} | "
                f"Distinct IDs="
                f"{outcome_ids['distinct_ids']}"
            )

        else:

            print(
                "signal_outcomes | "
                "signal_id column NOT FOUND"
            )

        # ==============================================================
        # SOURCE CHECK
        # ==============================================================

        section(
            "PRODUCTION ENGINE SOURCE CHECK"
        )

        source = read_engine_source(
            ENGINE_PATH
        )

        print(
            "Engine exists       : PASS"
        )

        print(
            f"Engine size         : "
            f"{os.path.getsize(ENGINE_PATH):,} bytes"
        )

        version_found = (
            EXPECTED_OUTCOME_VERSION
            in source
        )

        print(
            f"Expected version    : "
            f"{'FOUND' if version_found else 'NOT FOUND'}"
        )

        # ==============================================================
        # ELIGIBILITY SOURCE LOCATIONS
        # ==============================================================

        section(
            "ELIGIBILITY-RELATED SOURCE LOCATIONS"
        )

        print_eligibility_source_locations(
            source
        )

        # ==============================================================
        # SQL FORENSIC
        # ==============================================================

        section(
            "READ-ONLY SOURCE SQL FORENSIC"
        )

        statements, classifications, relevant = (
            analyze_source_sql(
                source
            )
        )

        print(
            f"SQL-like statements detected : "
            f"{len(statements)}"
        )

        print(
            f"SELECT statements             : "
            f"{classifications.get('SELECT', 0)}"
        )

        print(
            f"INSERT statements             : "
            f"{classifications.get('INSERT', 0)}"
        )

        print(
            f"UPDATE statements             : "
            f"{classifications.get('UPDATE', 0)}"
        )

        print(
            f"DELETE statements             : "
            f"{classifications.get('DELETE', 0)}"
        )

        print(
            f"ALTER statements              : "
            f"{classifications.get('ALTER', 0)}"
        )

        print(
            f"CREATE statements             : "
            f"{classifications.get('CREATE', 0)}"
        )

        # --------------------------------------------------------------
        # Show relevant statements, but NEVER execute them.
        # --------------------------------------------------------------

        subsection(
            "RELEVANT SOURCE SQL — NOT EXECUTED"
        )

        if not relevant:

            print(
                "No relevant SQL statement "
                "was extracted."
            )

        else:

            for index, item in enumerate(
                relevant,
                start=1,
            ):

                line_number = (
                    get_source_line_number(
                        source,
                        item["start"],
                    )
                )

                classification = (
                    classify_sql(
                        item["sql"]
                    )
                )

                print()
                print(
                    f"[{index}] "
                    f"Line={line_number} | "
                    f"Type={classification}"
                )

                compact = " ".join(
                    item["sql"].split()
                )

                if len(compact) > 500:
                    compact = (
                        compact[:500]
                        + " ..."
                    )

                print(
                    f"    {compact}"
                )

        # ==============================================================
        # SIGNAL SET RECONCILIATION
        # ==============================================================

        section(
            "ELIGIBLE SIGNAL SET RECONCILIATION"
        )

        reconciliation = (
            reconcile_signal_sets(
                rows,
                populations,
            )
        )

        print(
            f"ALL_FUSION             : "
            f"{reconciliation['all_count']}"
        )

        print(
            f"VALID_ID               : "
            f"{reconciliation['valid_id_count']}"
        )

        print(
            f"VALID_TIMESTAMP        : "
            f"{reconciliation['valid_timestamp_count']}"
        )

        print(
            f"VALID_SYMBOL           : "
            f"{reconciliation['valid_symbol_count']}"
        )

        print(
            f"VALID_DIRECTION        : "
            f"{reconciliation['valid_direction_count']}"
        )

        excluded_count = len(
            reconciliation["excluded_ids"]
        )

        print(
            f"EXCLUDED_BY_DIRECTION : "
            f"{excluded_count}"
        )

        # ==============================================================
        # EXCLUDED SIGNAL DETAIL
        # ==============================================================

        print_excluded_signal_detail(
            rows,
            reconciliation["excluded_ids"],
        )

        # ==============================================================
        # DIRECT ID RECONCILIATION
        # ==============================================================

        section(
            "SIGNAL-ID RECONCILIATION"
        )

        fusion_ids = {
            row["signal_id"]
            for row in rows
            if row["signal_id"] is not None
        }

        eligible_ids = {
            row["signal_id"]
            for row in populations[
                "VALID_DIRECTION"
            ]
            if row["signal_id"] is not None
        }

        outcome_id_set = set()

        if table_exists(
            conn,
            "signal_outcomes",
        ):

            columns = get_columns(
                conn,
                "signal_outcomes",
            )

            outcome_id_column = resolve_column(
                columns,
                [
                    "signal_id",
                    "id",
                ],
            )

            if outcome_id_column:

                outcome_rows = conn.execute(
                    f"""
                    SELECT DISTINCT
                        "{outcome_id_column}"
                    FROM signal_outcomes
                    WHERE "{outcome_id_column}" IS NOT NULL
                    """
                ).fetchall()

                outcome_id_set = {
                    row[0]
                    for row in outcome_rows
                }

        missing_from_outcomes = sorted(
            eligible_ids - outcome_id_set
        )

        outcomes_without_current_fusion = sorted(
            outcome_id_set - fusion_ids
        )

        print(
            f"Fusion signal IDs         : "
            f"{len(fusion_ids)}"
        )

        print(
            f"Eligible signal IDs       : "
            f"{len(eligible_ids)}"
        )

        print(
            f"Outcome signal IDs        : "
            f"{len(outcome_id_set)}"
        )

        print(
            f"Eligible IDs missing from "
            f"outcomes                  : "
            f"{len(missing_from_outcomes)}"
        )

        print(
            f"Outcome IDs absent from "
            f"current Fusion           : "
            f"{len(outcomes_without_current_fusion)}"
        )

        if missing_from_outcomes:

            print()
            print(
                "Eligible IDs missing from "
                "signal_outcomes:"
            )

            print(
                missing_from_outcomes
            )

        if outcomes_without_current_fusion:

            print()
            print(
                "Outcome IDs absent from "
                "current fusion_signals:"
            )

            print(
                outcomes_without_current_fusion
            )

        # ==============================================================
        # PRODUCTION ELIGIBILITY INTERPRETATION
        # ==============================================================

        section(
            "ELIGIBILITY INTERPRETATION"
        )

        if quality["null_directions"] > 0:

            print(
                "Finding:"
            )

            print(
                "Raw fusion_signals contains rows "
                "without a valid direction."
            )

            print()

            print(
                "The objective VALID_DIRECTION set "
                "contains only rows with:"
            )

            print(
                "  LONG / SHORT / FLAT"
            )

            print()

            print(
                "These direction-invalid rows are "
                "not considered eligible by this "
                "reconciliation."
            )

        else:

            print(
                "No NULL direction rows found."
            )

        # ==============================================================
        # SAFETY VERDICT
        # ==============================================================

        section(
            "FINAL SAFETY VERDICT"
        )

        print(
            "Database writes       : NONE"
        )

        print(
            "INSERT                 : NONE"
        )

        print(
            "UPDATE                 : NONE"
        )

        print(
            "DELETE                 : NONE"
        )

        print(
            "ALTER                  : NONE"
        )

        print(
            "CREATE                 : NONE"
        )

        print(
            "Tolerance modified    : NO"
        )

        print(
            "Production source     : UNMODIFIED"
        )

        print(
            "Production DB         : UNMODIFIED"
        )

        print(
            "Synthetic data        : NOT USED"
        )

        print(
            "Interpolation         : NOT USED"
        )

        print(
            "Forward fill          : NOT USED"
        )

        print(
            "Back fill             : NOT USED"
        )

        # ==============================================================
        # FINAL FORENSIC CONCLUSION
        # ==============================================================

        section(
            "FORENSIC CONCLUSION"
        )

        print(
            f"Raw Fusion signals     : "
            f"{len(populations['ALL_FUSION'])}"
        )

        print(
            f"Valid directional set  : "
            f"{len(populations['VALID_DIRECTION'])}"
        )

        print(
            f"Direction-invalid rows : "
            f"{excluded_count}"
        )

        if (
            len(populations["ALL_FUSION"])
            == len(
                populations["VALID_DIRECTION"]
            )
        ):

            print()
            print(
                "ELIGIBLE SIGNAL SET:"
            )

            print(
                "NO DISCREPANCY DETECTED "
                "AT DIRECTION LEVEL."
            )

        else:

            print()
            print(
                "ELIGIBLE SIGNAL SET:"
            )

            print(
                "RECONCILIATION DISCREPANCY "
                "EXISTS."
            )

            print()

            print(
                "The raw Fusion population is "
                "larger than the direction-valid "
                "production candidate population."
            )

            print(
                "This must be resolved as a signal "
                "eligibility issue before any "
                "additional Outcome repair."
            )

        print()
        print(
            "FORENSIC COMPLETE."
        )

    finally:

        if conn is not None:

            conn.close()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()