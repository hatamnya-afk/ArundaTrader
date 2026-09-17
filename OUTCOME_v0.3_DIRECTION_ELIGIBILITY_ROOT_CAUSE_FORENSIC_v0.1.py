import sqlite3
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone


# ==============================================================================
# OUTCOME v0.3 DIRECTION ELIGIBILITY ROOT-CAUSE FORENSIC v0.1
# ==============================================================================

DB_PATH = "arunda.db"
ENGINE_PATH = "signal_outcome_engine.py"

EXPECTED_ENGINE_VERSION = "OUTCOME_v0.3.2"

VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}


# ==============================================================================
# HELPERS
# ==============================================================================

def print_header(title):
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_section(title):
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


def normalize_direction(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if value in VALID_DIRECTIONS:
        return value

    return value


def safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def parse_timestamp(value):
    if value is None:
        return None

    try:
        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def source_line_matches(source, patterns):
    results = []

    for line_no, line in enumerate(source.splitlines(), start=1):
        lower = line.lower()

        if any(pattern.lower() in lower for pattern in patterns):
            results.append((line_no, line.rstrip()))

    return results


# ==============================================================================
# SOURCE FORENSIC
# ==============================================================================

def inspect_engine_source():

    print_section("PRODUCTION ENGINE SOURCE CHECK")

    if not os.path.exists(ENGINE_PATH):
        print("Engine exists       : FAIL")
        print(f"Missing             : {ENGINE_PATH}")
        return

    print("Engine exists       : PASS")

    size = os.path.getsize(ENGINE_PATH)

    print(f"Engine size         : {size:,} bytes")

    try:
        with open(
            ENGINE_PATH,
            "r",
            encoding="utf-8",
            errors="replace",
        ) as f:
            source = f.read()

    except Exception as exc:
        print(f"Source read         : FAIL | {exc}")
        return

    print("Expected version    :", end=" ")

    if EXPECTED_ENGINE_VERSION in source:
        print("FOUND")
    else:
        print("NOT FOUND")

    print_section("DIRECTION-RELATED SOURCE LOCATIONS")

    patterns = [
        "direction",
        "fused_score",
        "fusion_signals",
        "SELECT",
        "FROM fusion_signals",
        "INSERT INTO fusion_signals",
        "UPDATE fusion_signals",
        "direction =",
        '"direction"',
        "'direction'",
    ]

    matches = source_line_matches(source, patterns)

    if not matches:
        print("No direction-related source locations found.")
        return

    for line_no, line in matches:
        print(f"{line_no:5d} | {line[:220]}")


# ==============================================================================
# DATABASE STRUCTURE
# ==============================================================================

def inspect_structure(conn):

    print_section("DATABASE STRUCTURE CHECK")

    required_tables = [
        "fusion_signals",
        "signal_outcomes",
    ]

    for table in required_tables:

        exists = table_exists(conn, table)

        print(
            f"{table:<30} | "
            f"{'PASS' if exists else 'FAIL'}"
        )

        if not exists:
            continue

        columns = get_columns(conn, table)

        print(
            f"  Columns: {', '.join(columns)}"
        )


# ==============================================================================
# FUSION SIGNAL COLUMN DISCOVERY
# ==============================================================================

def discover_columns(conn):

    print_section("FUSION SIGNAL COLUMN MAP")

    columns = get_columns(conn, "fusion_signals")

    expected = [
        "id",
        "asset",
        "symbol",
        "timestamp",
        "direction",
        "fused_score",
        "score",
        "confidence",
        "regime",
        "snapshot_id",
        "entry_price",
    ]

    for name in expected:

        if name in columns:
            print(
                f"{name:<18} | FOUND"
            )
        else:
            print(
                f"{name:<18} | NOT FOUND"
            )

    return columns


# ==============================================================================
# RAW POPULATION
# ==============================================================================

def raw_population(conn):

    print_section("RAW FUSION SIGNAL POPULATION")

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        """
    ).fetchone()[0]

    distinct_ids = conn.execute(
        """
        SELECT COUNT(DISTINCT id)
        FROM fusion_signals
        WHERE id IS NOT NULL
        """
    ).fetchone()[0]

    print(f"Total fusion_signals rows : {total}")
    print(f"Distinct signal IDs       : {distinct_ids}")


# ==============================================================================
# QUALITY FORENSIC
# ==============================================================================

def quality_forensic(conn):

    print_section("SIGNAL QUALITY FORENSIC")

    checks = {
        "Duplicate IDs":
            """
            SELECT COUNT(*)
            FROM (
                SELECT id
                FROM fusion_signals
                GROUP BY id
                HAVING COUNT(*) > 1
            )
            """,

        "NULL IDs":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE id IS NULL
            """,

        "NULL assets":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE asset IS NULL
               OR TRIM(asset) = ''
            """,

        "NULL timestamps":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE timestamp IS NULL
               OR TRIM(timestamp) = ''
            """,

        "NULL directions":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE direction IS NULL
            """,

        "Invalid directions":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE direction IS NOT NULL
              AND UPPER(TRIM(direction))
                  NOT IN ('LONG', 'SHORT', 'FLAT')
            """,
    }

    for label, sql in checks.items():

        count = conn.execute(sql).fetchone()[0]

        print(
            f"{label:<22} : {count}"
        )


# ==============================================================================
# OBJECTIVE POPULATIONS
# ==============================================================================

def objective_populations(conn):

    print_section("OBJECTIVE SIGNAL POPULATIONS")

    queries = {

        "ALL_FUSION":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            """,

        "VALID_ID":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE id IS NOT NULL
            """,

        "VALID_TIMESTAMP":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE timestamp IS NOT NULL
              AND TRIM(timestamp) != ''
            """,

        "VALID_SYMBOL":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE asset IS NOT NULL
              AND TRIM(asset) != ''
            """,

        "VALID_DIRECTION":
            """
            SELECT COUNT(*)
            FROM fusion_signals
            WHERE direction IS NOT NULL
              AND UPPER(TRIM(direction))
                  IN ('LONG', 'SHORT', 'FLAT')
            """,
    }

    populations = {}

    for label, sql in queries.items():

        value = conn.execute(sql).fetchone()[0]

        populations[label] = value

        print(
            f"{label:<20} : {value}"
        )

    return populations


# ==============================================================================
# DIRECTION DISTRIBUTION
# ==============================================================================

def direction_distribution(conn):

    print_section("DIRECTION DISTRIBUTION")

    rows = conn.execute(
        """
        SELECT
            direction,
            COUNT(*) AS count
        FROM fusion_signals
        GROUP BY direction
        ORDER BY direction
        """
    ).fetchall()

    for row in rows:

        direction = row[0]
        count = row[1]

        print(
            f"{str(direction):<12} | {count}"
        )


# ==============================================================================
# SCORE DISTRIBUTION BY DIRECTION STATE
# ==============================================================================

def score_vs_direction(conn):

    print_section("FUSED SCORE VS DIRECTION STATE")

    rows = conn.execute(
        """
        SELECT
            id,
            asset,
            timestamp,
            direction,
            fused_score
        FROM fusion_signals
        ORDER BY id ASC
        """
    ).fetchall()

    for row in rows:

        signal_id = row[0]
        asset = row[1]
        timestamp = row[2]
        direction = row[3]
        score = row[4]

        print(
            f"Signal #{signal_id:<5} | "
            f"{str(asset):<6} | "
            f"direction={str(direction):<7} | "
            f"score={str(score):<12} | "
            f"timestamp={timestamp}"
        )


# ==============================================================================
# NULL-DIRECTION FORENSIC
# ==============================================================================

def null_direction_forensic(conn):

    print_section("NULL-DIRECTION SIGNAL FORENSIC")

    rows = conn.execute(
        """
        SELECT
            id,
            asset,
            timestamp,
            direction,
            fused_score,
            confidence,
            regime,
            snapshot_id,
            entry_price
        FROM fusion_signals
        WHERE direction IS NULL
        ORDER BY id ASC
        """
    ).fetchall()

    print(
        f"NULL-direction rows : {len(rows)}"
    )

    if not rows:
        print("No NULL-direction rows found.")
        return

    print()

    for row in rows:

        (
            signal_id,
            asset,
            timestamp,
            direction,
            fused_score,
            confidence,
            regime,
            snapshot_id,
            entry_price,
        ) = row

        print(
            f"Signal #{signal_id:<5} | "
            f"{str(asset):<6} | "
            f"score={str(fused_score):<12} | "
            f"confidence={str(confidence):<10} | "
            f"regime={str(regime):<12} | "
            f"snapshot={str(snapshot_id):<8} | "
            f"entry={str(entry_price):<14}"
        )

        print(
            f"              timestamp={timestamp}"
        )


# ==============================================================================
# SCORE POLARITY FORENSIC
# ==============================================================================

def score_polarity_forensic(conn):

    print_section("SCORE POLARITY / DIRECTION CONSISTENCY FORENSIC")

    rows = conn.execute(
        """
        SELECT
            direction,
            fused_score
        FROM fusion_signals
        WHERE fused_score IS NOT NULL
        ORDER BY id ASC
        """
    ).fetchall()

    valid = []
    invalid = []
    null_direction = []

    for direction, score in rows:

        score_value = safe_float(score)

        if score_value is None:
            continue

        normalized = normalize_direction(direction)

        if normalized is None:
            null_direction.append(score_value)
            continue

        valid.append(
            (
                normalized,
                score_value
            )
        )

        # IMPORTANT:
        # This is diagnostic ONLY.
        # No direction is inferred or written.
        if normalized == "LONG" and score_value < 0:
            invalid.append(
                ("LONG", score_value)
            )

        elif normalized == "SHORT" and score_value > 0:
            invalid.append(
                ("SHORT", score_value)
            )

    print(
        f"Valid directional score rows : {len(valid)}"
    )

    print(
        f"NULL-direction score rows    : {len(null_direction)}"
    )

    print(
        f"Polarity inconsistencies      : {len(invalid)}"
    )

    if invalid:

        print()
        print(
            "POLARITY INCONSISTENCIES — DIAGNOSTIC ONLY"
        )

        for direction, score in invalid:

            print(
                f"direction={direction:<6} | "
                f"score={score}"
            )

    if null_direction:

        positives = sum(
            1
            for score in null_direction
            if score > 0
        )

        negatives = sum(
            1
            for score in null_direction
            if score < 0
        )

        zeros = sum(
            1
            for score in null_direction
            if score == 0
        )

        print()
        print(
            "NULL-DIRECTION SCORE POLARITY"
        )

        print(
            f"Positive scores : {positives}"
        )

        print(
            f"Negative scores : {negatives}"
        )

        print(
            f"Zero scores     : {zeros}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "Score polarity is NOT treated as a reconstructed direction."
        )


# ==============================================================================
# TEMPORAL / BATCH FORENSIC
# ==============================================================================

def batch_temporal_forensic(conn):

    print_section("DIRECTION STATE BY TEMPORAL ORDER")

    rows = conn.execute(
        """
        SELECT
            id,
            asset,
            timestamp,
            direction
        FROM fusion_signals
        ORDER BY timestamp ASC, id ASC
        """
    ).fetchall()

    if not rows:
        print("No rows.")
        return

    current_state = None
    block_start = None
    block_count = 0

    blocks = []

    for row in rows:

        signal_id = row[0]
        direction = normalize_direction(row[3])

        state = (
            "NULL"
            if direction is None
            else direction
        )

        if current_state is None:

            current_state = state
            block_start = signal_id
            block_count = 1

        elif state == current_state:

            block_count += 1

        else:

            blocks.append(
                (
                    current_state,
                    block_start,
                    signal_id - 1,
                    block_count,
                )
            )

            current_state = state
            block_start = signal_id
            block_count = 1

    blocks.append(
        (
            current_state,
            block_start,
            rows[-1][0],
            block_count,
        )
    )

    print(
        "State blocks:"
    )

    for state, start, end, count in blocks:

        print(
            f"{state:<8} | "
            f"Signal IDs {start} -> {end} | "
            f"Count={count}"
        )


# ==============================================================================
# TIMESTAMP BATCH GROUPING
# ==============================================================================

def timestamp_grouping(conn):

    print_section("TIMESTAMP / DIRECTION GROUPING")

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN direction IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_direction,
            SUM(
                CASE
                    WHEN direction IS NOT NULL
                     AND UPPER(TRIM(direction))
                         IN ('LONG','SHORT','FLAT')
                    THEN 1
                    ELSE 0
                END
            ) AS valid_direction
        FROM fusion_signals
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """
    ).fetchall()

    for row in rows:

        timestamp = row[0]
        total = row[1]
        null_direction = row[2]
        valid_direction = row[3]

        print(
            f"{timestamp} | "
            f"Total={total:<3} | "
            f"NULL={null_direction:<3} | "
            f"VALID={valid_direction:<3}"
        )


# ==============================================================================
# OUTCOME RECONCILIATION
# ==============================================================================

def outcome_reconciliation(conn):

    print_section("OUTCOME / ELIGIBLE SIGNAL RECONCILIATION")

    eligible_rows = conn.execute(
        """
        SELECT id
        FROM fusion_signals
        WHERE id IS NOT NULL
          AND timestamp IS NOT NULL
          AND asset IS NOT NULL
          AND direction IS NOT NULL
          AND UPPER(TRIM(direction))
              IN ('LONG','SHORT','FLAT')
        ORDER BY id
        """
    ).fetchall()

    eligible_ids = {
        row[0]
        for row in eligible_rows
    }

    outcome_columns = get_columns(
        conn,
        "signal_outcomes"
    )

    if "signal_id" not in outcome_columns:

        print(
            "signal_outcomes.signal_id : NOT FOUND"
        )
        return

    outcome_rows = conn.execute(
        """
        SELECT DISTINCT signal_id
        FROM signal_outcomes
        WHERE signal_id IS NOT NULL
        """
    ).fetchall()

    outcome_ids = {
        row[0]
        for row in outcome_rows
    }

    missing = sorted(
        eligible_ids - outcome_ids
    )

    stale = sorted(
        outcome_ids - {
            row[0]
            for row in conn.execute(
                """
                SELECT id
                FROM fusion_signals
                WHERE id IS NOT NULL
                """
            ).fetchall()
        }
    )

    print(
        f"Eligible signal IDs       : {len(eligible_ids)}"
    )

    print(
        f"Outcome signal IDs        : {len(outcome_ids)}"
    )

    print(
        f"Eligible IDs missing      : {len(missing)}"
    )

    print(
        f"Outcome IDs absent Fusion : {len(stale)}"
    )

    if missing:

        print()
        print(
            "MISSING ELIGIBLE SIGNAL IDs:"
        )

        print(missing)

    if stale:

        print()
        print(
            "OUTCOME IDs ABSENT FROM CURRENT FUSION:"
        )

        print(stale)


# ==============================================================================
# ROOT-CAUSE CLASSIFICATION
# ==============================================================================

def root_cause_classification(conn):

    print_section("ROOT-CAUSE CLASSIFICATION")

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        """
    ).fetchone()[0]

    null_direction = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NULL
        """
    ).fetchone()[0]

    valid_direction = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NOT NULL
          AND UPPER(TRIM(direction))
              IN ('LONG','SHORT','FLAT')
        """
    ).fetchone()[0]

    invalid_direction = conn.execute(
        """
        SELECT COUNT(*)
        FROM fusion_signals
        WHERE direction IS NOT NULL
          AND UPPER(TRIM(direction))
              NOT IN ('LONG','SHORT','FLAT')
        """
    ).fetchone()[0]

    print(
        f"Total Fusion rows       : {total}"
    )

    print(
        f"Valid direction rows    : {valid_direction}"
    )

    print(
        f"NULL direction rows     : {null_direction}"
    )

    print(
        f"Invalid direction rows : {invalid_direction}"
    )

    print()

    if null_direction > 0:

        print(
            "FINDING:"
        )

        print(
            "A direction eligibility discrepancy exists in the raw Fusion population."
        )

        print()

        print(
            "The NULL-direction rows are excluded from the production "
            "direction-valid candidate set."
        )

        print()

        print(
            "No direction reconstruction is permitted at this stage."
        )

    elif invalid_direction > 0:

        print(
            "FINDING:"
        )

        print(
            "Non-null but invalid direction values exist."
        )

    else:

        print(
            "No direction eligibility defect detected."
        )


# ==============================================================================
# SAFETY VERDICT
# ==============================================================================

def safety_verdict():

    print_section("FINAL SAFETY VERDICT")

    print("Database writes       : NONE")
    print("INSERT                 : NONE")
    print("UPDATE                 : NONE")
    print("DELETE                 : NONE")
    print("ALTER                  : NONE")
    print("CREATE                 : NONE")
    print("Tolerance modified    : NO")
    print("Production source     : UNMODIFIED")
    print("Production DB         : UNMODIFIED")
    print("Synthetic data        : NOT USED")
    print("Interpolation         : NOT USED")
    print("Forward fill          : NOT USED")
    print("Back fill             : NOT USED")


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print_header(
        "OUTCOME v0.3 DIRECTION ELIGIBILITY ROOT-CAUSE FORENSIC v0.1"
    )

    print(
        f"Database          : {DB_PATH}"
    )

    print(
        f"Engine            : {ENGINE_PATH}"
    )

    print(
        f"Outcome version   : {EXPECTED_ENGINE_VERSION}"
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

    if not os.path.exists(DB_PATH):

        print()
        print(
            f"ERROR: Database not found: {DB_PATH}"
        )

        return 1

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    try:

        # ------------------------------------------------------------------
        # Safety: explicit read-only transaction
        # ------------------------------------------------------------------

        conn.execute(
            "PRAGMA query_only = ON"
        )

        inspect_structure(conn)

        if not table_exists(
            conn,
            "fusion_signals"
        ):

            print(
                "ERROR: fusion_signals table missing."
            )

            return 1

        discover_columns(conn)

        raw_population(conn)

        quality_forensic(conn)

        objective_populations(conn)

        direction_distribution(conn)

        score_vs_direction(conn)

        null_direction_forensic(conn)

        score_polarity_forensic(conn)

        batch_temporal_forensic(conn)

        timestamp_grouping(conn)

        if table_exists(
            conn,
            "signal_outcomes"
        ):

            outcome_reconciliation(conn)

        root_cause_classification(conn)

        inspect_engine_source()

        safety_verdict()

        print()
        print("=" * 90)
        print("FORENSIC COMPLETE.")
        print("=" * 90)

        return 0

    finally:

        conn.close()


if __name__ == "__main__":

    raise SystemExit(
        main()
    )