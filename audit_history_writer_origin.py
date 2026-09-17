# ============================================================
# ARUNDA TRADER
# HISTORY WRITER ORIGIN AUDIT v0.1
# ============================================================
#
# PURPOSE:
#   Discover the ingestion/writer pattern responsible for
#   market_history lineage contamination.
#
# MODE:
#   READ ONLY
#
# GUARANTEES:
#   - NO INSERT
#   - NO UPDATE
#   - NO DELETE
#   - NO ALTER
#   - NO CREATE
#   - NO schema changes
#
# DATABASE:
#   C:\Users\ASUS\ArundaTrader\arunda.db
#
# ============================================================

import sqlite3
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"
TABLE_NAME = "market_history"

NULL_SOURCE = "<NULL>"

# Number of examples shown in reports
MAX_EXAMPLES = 30


# ============================================================
# READ-ONLY CONNECTION
# ============================================================

def get_connection():
    """
    Open SQLite database in true read-only mode.

    Important:
    sqlite3.connect() does NOT accept read_only=...
    Therefore URI mode is used:
        file:///...?...mode=ro
    """

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found:\n{DB_PATH}"
        )

    absolute_path = os.path.abspath(DB_PATH)
    uri = "file:" + absolute_path.replace("\\", "/") + "?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True
    )


# ============================================================
# HELPERS
# ============================================================

def fmt(value):
    if value is None:
        return NULL_SOURCE
    return str(value)


def parse_timestamp(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def seconds_between(a, b):
    ta = parse_timestamp(a)
    tb = parse_timestamp(b)

    if ta is None or tb is None:
        return None

    return (tb - ta).total_seconds()


def print_header(title):
    print("\n" + "-" * 100)
    print(title)
    print("-" * 100)


# ============================================================
# SCHEMA
# ============================================================

def inspect_schema(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"PRAGMA table_info({TABLE_NAME})"
    ).fetchall()

    columns = [row[1] for row in rows]

    required = [
        "id",
        "timestamp",
        "symbol",
        "source",
        "source_timestamp",
        "engine_version",
        "created_at",
    ]

    missing = [c for c in required if c not in columns]

    if missing:
        raise RuntimeError(
            "Required columns missing: " + ", ".join(missing)
        )

    return columns


# ============================================================
# DATABASE OVERVIEW
# ============================================================

def database_overview(conn):
    cur = conn.cursor()

    total = cur.execute(
        f"SELECT COUNT(*) FROM {TABLE_NAME}"
    ).fetchone()[0]

    assets = cur.execute(
        f"""
        SELECT COUNT(DISTINCT symbol)
        FROM {TABLE_NAME}
        """
    ).fetchone()[0]

    first_ts, last_ts = cur.execute(
        f"""
        SELECT MIN(timestamp), MAX(timestamp)
        FROM {TABLE_NAME}
        """
    ).fetchone()

    min_id, max_id = cur.execute(
        f"""
        SELECT MIN(id), MAX(id)
        FROM {TABLE_NAME}
        """
    ).fetchone()

    return {
        "total": total,
        "assets": assets,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "min_id": min_id,
        "max_id": max_id,
    }


# ============================================================
# GLOBAL LINEAGE
# ============================================================

def global_lineage(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS rows_count,
            MIN(id),
            MAX(id),
            MIN(timestamp),
            MAX(timestamp),
            MIN(created_at),
            MAX(created_at)
        FROM {TABLE_NAME}
        GROUP BY source, engine_version
        ORDER BY rows_count DESC
        """
    ).fetchall()

    return rows


# ============================================================
# ID RANGE BY LINEAGE
# ============================================================

def lineage_id_ranges(conn):
    cur = conn.cursor()

    return cur.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS rows_count,
            MIN(id) AS min_id,
            MAX(id) AS max_id,
            MIN(timestamp) AS first_ts,
            MAX(timestamp) AS last_ts
        FROM {TABLE_NAME}
        GROUP BY source, engine_version
        ORDER BY min_id
        """
    ).fetchall()


# ============================================================
# TIMESTAMP / CREATED_AT RELATION
# ============================================================

def timestamp_created_at_audit(conn):
    cur = conn.cursor()

    return cur.execute(
        f"""
        SELECT
            CASE
                WHEN timestamp IS NULL AND created_at IS NULL
                    THEN 'BOTH_NULL'

                WHEN timestamp IS NULL
                    THEN 'TIMESTAMP_NULL'

                WHEN created_at IS NULL
                    THEN 'CREATED_AT_NULL'

                WHEN timestamp = created_at
                    THEN 'EXACT_MATCH'

                ELSE 'DIFFERENT'
            END AS relation,
            COUNT(*)
        FROM {TABLE_NAME}
        GROUP BY relation
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()


# ============================================================
# ASSET BATCH DISTRIBUTION
# ============================================================

def asset_row_distribution(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT symbol, COUNT(*) AS n
        FROM {TABLE_NAME}
        GROUP BY symbol
        ORDER BY n DESC, symbol
        """
    ).fetchall()

    distribution = Counter(n for _, n in rows)

    return rows, distribution


# ============================================================
# LINEAGE ASSET COVERAGE
# ============================================================

def lineage_asset_coverage(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            CASE
                WHEN source IS NULL
                 AND engine_version IS NULL
                    THEN 'NULL_LINEAGE'
                ELSE 'IDENTIFIED_LINEAGE'
            END AS lineage_status,
            COUNT(DISTINCT symbol),
            COUNT(*)
        FROM {TABLE_NAME}
        GROUP BY lineage_status
        """
    ).fetchall()

    return rows


# ============================================================
# TIMESTAMP CONCENTRATION
# ============================================================

def timestamp_concentration(conn):
    cur = conn.cursor()

    return cur.execute(
        f"""
        SELECT
            timestamp,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT symbol) AS assets
        FROM {TABLE_NAME}
        GROUP BY timestamp
        HAVING COUNT(*) > 1
        ORDER BY rows_count DESC, timestamp
        LIMIT 100
        """
    ).fetchall()


# ============================================================
# ASSET BATCH PATTERNS
# ============================================================

def asset_batch_patterns(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            timestamp,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT symbol) AS assets
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY timestamp
        ORDER BY timestamp
        """
    ).fetchall()

    return rows


# ============================================================
# NULL LINEAGE TIMELINE
# ============================================================

def null_lineage_timeline(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            timestamp,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT symbol) AS assets,
            MIN(id),
            MAX(id)
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY timestamp
        ORDER BY timestamp
        """
    ).fetchall()

    return rows


# ============================================================
# ID CONTINUITY
# ============================================================

def id_continuity(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT id
        FROM {TABLE_NAME}
        ORDER BY id
        """
    ).fetchall()

    ids = [r[0] for r in rows]

    if not ids:
        return {
            "rows": 0,
            "gaps": 0,
            "largest_gap": 0,
            "gap_examples": [],
        }

    gaps = []
    largest = 0

    for prev_id, current_id in zip(ids, ids[1:]):
        gap = current_id - prev_id

        if gap > 1:
            gap_size = gap - 1
            gaps.append(
                (prev_id, current_id, gap_size)
            )

            if gap_size > largest:
                largest = gap_size

    return {
        "rows": len(ids),
        "gaps": len(gaps),
        "largest_gap": largest,
        "gap_examples": gaps[:MAX_EXAMPLES],
    }


# ============================================================
# LINEAGE TRANSITIONS BY ID
# ============================================================

def lineage_transitions(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            id,
            source,
            engine_version,
            timestamp,
            symbol
        FROM {TABLE_NAME}
        ORDER BY id
        """
    ).fetchall()

    transitions = []

    previous = None

    for row in rows:
        row_id, source, engine, ts, symbol = row

        current = (
            source if source is not None else NULL_SOURCE,
            engine if engine is not None else NULL_SOURCE
        )

        if previous is not None and current != previous["lineage"]:
            transitions.append({
                "from": previous["lineage"],
                "to": current,
                "previous_id": previous["id"],
                "current_id": row_id,
                "previous_timestamp": previous["timestamp"],
                "current_timestamp": ts,
                "previous_symbol": previous["symbol"],
                "current_symbol": symbol,
            })

        previous = {
            "lineage": current,
            "id": row_id,
            "timestamp": ts,
            "symbol": symbol,
        }

    return transitions


# ============================================================
# NULL LINEAGE ASSET START PATTERN
# ============================================================

def null_asset_origins(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows_count,
            MIN(id) AS min_id,
            MAX(id) AS max_id,
            MIN(timestamp) AS first_ts,
            MAX(timestamp) AS last_ts
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY symbol
        ORDER BY min_id
        """
    ).fetchall()

    return rows


# ============================================================
# PER-TIMESTAMP ASSET DISTRIBUTION
# ============================================================

def timestamp_asset_distribution(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            timestamp,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT symbol) AS assets,
            MIN(id),
            MAX(id)
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY timestamp
        ORDER BY timestamp
        """
    ).fetchall()

    distribution = Counter(
        (r[1], r[2])
        for r in rows
    )

    return rows, distribution


# ============================================================
# DUPLICATE NULL-LINEAGE STRUCTURE
# ============================================================

def null_duplicate_structure(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS n,
            MIN(id),
            MAX(id),
            MIN(price),
            MAX(price)
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
        ORDER BY n DESC, symbol, timestamp
        LIMIT 100
        """
    ).fetchall()

    return rows


# ============================================================
# PRICE STREAM FINGERPRINT
# ============================================================

def price_stream_fingerprint(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT price) AS distinct_prices,
            MIN(price),
            MAX(price)
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY symbol
        ORDER BY rows_count DESC, symbol
        """
    ).fetchall()

    return rows


# ============================================================
# WRITER BATCH SIGNATURE
# ============================================================

def writer_batch_signature(conn):
    cur = conn.cursor()

    rows = cur.execute(
        f"""
        SELECT
            timestamp,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT symbol) AS assets,
            MIN(id),
            MAX(id),
            MIN(price),
            MAX(price)
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY timestamp
        ORDER BY timestamp
        """
    ).fetchall()

    return rows


# ============================================================
# REPORT
# ============================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — HISTORY WRITER ORIGIN AUDIT v0.1")
    print("=" * 100)
    print("MODE                 : READ ONLY")
    print(f"DATABASE             : {DB_PATH}")
    print("WRITE OPERATIONS     : NONE")
    print("SCHEMA CHANGES       : NONE")
    print("DELETE OPERATIONS    : NONE")
    print("INSERT OPERATIONS    : NONE")
    print("UPDATE OPERATIONS    : NONE")
    print("=" * 100)

    conn = None

    try:

        conn = get_connection()

        print("\nREAD-ONLY CONNECTION  : ESTABLISHED")
        print(f"TABLE                 : {TABLE_NAME}")

        columns = inspect_schema(conn)

        print_header("DATABASE / TABLE OVERVIEW")

        overview = database_overview(conn)

        print(f"Total History Rows : {overview['total']:,}")
        print(f"Historical Assets  : {overview['assets']:,}")
        print(f"First Timestamp    : {overview['first_ts']}")
        print(f"Last Timestamp     : {overview['last_ts']}")
        print(f"Minimum ID         : {overview['min_id']:,}")
        print(f"Maximum ID         : {overview['max_id']:,}")

        # ----------------------------------------------------
        # GLOBAL LINEAGE
        # ----------------------------------------------------

        print_header("GLOBAL LINEAGE / WRITER DISTRIBUTION")

        print(
            f"{'SOURCE':<30}"
            f"{'ENGINE':<40}"
            f"{'ROWS':>12}"
            f"{'MIN ID':>12}"
            f"{'MAX ID':>12}"
        )

        for row in global_lineage(conn):
            source, engine, count, min_id, max_id, *_ = row

            print(
                f"{fmt(source):<30}"
                f"{fmt(engine):<40}"
                f"{count:>12,}"
                f"{min_id:>12,}"
                f"{max_id:>12,}"
            )

        # ----------------------------------------------------
        # ID RANGES
        # ----------------------------------------------------

        print_header("LINEAGE ID RANGE AUDIT")

        for row in lineage_id_ranges(conn):

            (
                source,
                engine,
                count,
                min_id,
                max_id,
                first_ts,
                last_ts
            ) = row

            print(
                f"\nSOURCE        : {fmt(source)}"
                f"\nENGINE        : {fmt(engine)}"
                f"\nROWS          : {count:,}"
                f"\nID RANGE      : {min_id:,} → {max_id:,}"
                f"\nTIMESTAMP     : {first_ts} → {last_ts}"
            )

        # ----------------------------------------------------
        # TIMESTAMP / CREATED_AT
        # ----------------------------------------------------

        print_header("TIMESTAMP / CREATED_AT RELATIONSHIP")

        for relation, count in timestamp_created_at_audit(conn):

            print(
                f"{relation:<20} : {count:,}"
            )

        # ----------------------------------------------------
        # ASSET DISTRIBUTION
        # ----------------------------------------------------

        print_header("ASSET ROW COUNT DISTRIBUTION")

        asset_rows, distribution = asset_row_distribution(conn)

        print(
            f"Distinct asset row-count patterns : "
            f"{len(distribution):,}"
        )

        print("\nROWS PER ASSET        ASSETS")
        print("-" * 35)

        for rows_count, assets in sorted(distribution.items()):
            print(
                f"{rows_count:>15,}"
                f"{assets:>15,}"
            )

        # ----------------------------------------------------
        # LINEAGE ASSET COVERAGE
        # ----------------------------------------------------

        print_header("LINEAGE ASSET COVERAGE")

        for status, assets, rows in lineage_asset_coverage(conn):

            print(
                f"{status:<25}"
                f" ASSETS={assets:,}"
                f" ROWS={rows:,}"
            )

        # ----------------------------------------------------
        # NULL LINEAGE ORIGIN
        # ----------------------------------------------------

        print_header("NULL-LINEAGE WRITER ORIGIN")

        null_stats = conn.execute(
            f"""
            SELECT
                COUNT(*),
                COUNT(DISTINCT symbol),
                MIN(timestamp),
                MAX(timestamp),
                MIN(id),
                MAX(id),
                MIN(created_at),
                MAX(created_at)
            FROM {TABLE_NAME}
            WHERE source IS NULL
              AND engine_version IS NULL
            """
        ).fetchone()

        (
            null_rows,
            null_assets,
            null_first,
            null_last,
            null_min_id,
            null_max_id,
            null_created_first,
            null_created_last
        ) = null_stats

        print(f"NULL-lineage rows     : {null_rows:,}")
        print(f"NULL-lineage assets   : {null_assets:,}")
        print(f"First timestamp       : {null_first}")
        print(f"Last timestamp        : {null_last}")
        print(f"ID range              : {null_min_id:,} → {null_max_id:,}")
        print(f"First created_at      : {fmt(null_created_first)}")
        print(f"Last created_at       : {fmt(null_created_last)}")

        # ----------------------------------------------------
        # NULL ASSET ORIGINS
        # ----------------------------------------------------

        print_header("NULL-LINEAGE ASSET ORIGIN / BATCH PATTERN")

        rows = null_asset_origins(conn)

        print(
            f"{'ASSET':<12}"
            f"{'ROWS':>10}"
            f"{'MIN ID':>12}"
            f"{'MAX ID':>12}"
            f"  FIRST TIMESTAMP"
        )

        print("-" * 100)

        for row in rows[:MAX_EXAMPLES]:

            symbol, count, min_id, max_id, first_ts, last_ts = row

            print(
                f"{symbol:<12}"
                f"{count:>10,}"
                f"{min_id:>12,}"
                f"{max_id:>12,}"
                f"  {first_ts}"
            )

        if len(rows) > MAX_EXAMPLES:
            print(
                f"\n... {len(rows) - MAX_EXAMPLES:,} "
                f"additional assets not displayed."
            )

        # ----------------------------------------------------
        # TIMESTAMP BATCH STRUCTURE
        # ----------------------------------------------------

        print_header("NULL-LINEAGE TIMESTAMP BATCH STRUCTURE")

        batch_rows, batch_distribution = (
            timestamp_asset_distribution(conn)
        )

        print(
            f"Distinct NULL timestamps : {len(batch_rows):,}"
        )

        print("\nCOMMON (ROWS, ASSETS) PATTERNS")

        for pattern, count in batch_distribution.most_common(20):

            rows_count, assets = pattern

            print(
                f"  rows={rows_count:,}"
                f" assets={assets:,}"
                f" occurrences={count:,}"
            )

        print("\nFirst timestamp batches:")

        for row in batch_rows[:MAX_EXAMPLES]:

            timestamp, rows_count, assets, min_id, max_id = row

            print(
                f"  {timestamp}"
                f" rows={rows_count:,}"
                f" assets={assets:,}"
                f" id={min_id:,}→{max_id:,}"
            )

        # ----------------------------------------------------
        # TIMESTAMP CONCENTRATION
        # ----------------------------------------------------

        print_header("GLOBAL TIMESTAMP CONCENTRATION")

        rows = timestamp_concentration(conn)

        for row in rows[:MAX_EXAMPLES]:

            timestamp, count, assets = row

            print(
                f"{timestamp}"
                f" rows={count:,}"
                f" assets={assets:,}"
            )

        # ----------------------------------------------------
        # ID CONTINUITY
        # ----------------------------------------------------

        print_header("ID CONTINUITY AUDIT")

        continuity = id_continuity(conn)

        print(f"Rows scanned      : {continuity['rows']:,}")
        print(f"ID gaps           : {continuity['gaps']:,}")
        print(f"Largest ID gap    : {continuity['largest_gap']:,}")

        if continuity["gap_examples"]:

            print("\nGap examples:")

            for previous_id, current_id, gap_size in (
                continuity["gap_examples"]
            ):

                print(
                    f"  {previous_id:,} → {current_id:,}"
                    f" missing={gap_size:,}"
                )

        # ----------------------------------------------------
        # LINEAGE TRANSITIONS
        # ----------------------------------------------------

        print_header("LINEAGE TRANSITIONS BY ID ORDER")

        transitions = lineage_transitions(conn)

        print(
            f"Total lineage transitions : {len(transitions):,}"
        )

        for item in transitions[:MAX_EXAMPLES]:

            print(
                f"\nID {item['previous_id']:,}"
                f" → {item['current_id']:,}"
            )

            print(
                f"  FROM : {item['from']}"
            )

            print(
                f"  TO   : {item['to']}"
            )

            print(
                f"  TIME : "
                f"{item['previous_timestamp']}"
                f" → "
                f"{item['current_timestamp']}"
            )

            print(
                f"  ASSET: "
                f"{item['previous_symbol']}"
                f" → "
                f"{item['current_symbol']}"
            )

        # ----------------------------------------------------
        # NULL DUPLICATE STRUCTURE
        # ----------------------------------------------------

        print_header("NULL-LINEAGE DUPLICATE / MULTI-ROW STRUCTURE")

        rows = null_duplicate_structure(conn)

        print(
            f"Duplicate timestamp groups displayed : "
            f"{len(rows):,}"
        )

        for row in rows[:MAX_EXAMPLES]:

            (
                symbol,
                timestamp,
                count,
                min_id,
                max_id,
                min_price,
                max_price
            ) = row

            print(
                f"\n{symbol} | {timestamp}"
            )

            print(
                f"  rows={count}"
                f" id={min_id:,}→{max_id:,}"
            )

            print(
                f"  price={min_price} → {max_price}"
            )

        # ----------------------------------------------------
        # PRICE FINGERPRINT
        # ----------------------------------------------------

        print_header("NULL-LINEAGE PRICE STREAM FINGERPRINT")

        rows = price_stream_fingerprint(conn)

        print(
            f"{'ASSET':<12}"
            f"{'ROWS':>10}"
            f"{'DISTINCT PRICE':>18}"
            f"{'MIN PRICE':>22}"
            f"{'MAX PRICE':>22}"
        )

        print("-" * 90)

        for row in rows[:MAX_EXAMPLES]:

            symbol, count, distinct_prices, min_price, max_price = row

            print(
                f"{symbol:<12}"
                f"{count:>10,}"
                f"{distinct_prices:>18,}"
                f"{str(min_price):>22}"
                f"{str(max_price):>22}"
            )

        # ----------------------------------------------------
        # WRITER BATCH SIGNATURE
        # ----------------------------------------------------

        print_header("WRITER BATCH SIGNATURE")

        rows = writer_batch_signature(conn)

        print(
            f"Total NULL writer batches : {len(rows):,}"
        )

        print(
            "\nFirst 30 writer batches:"
        )

        for row in rows[:MAX_EXAMPLES]:

            (
                timestamp,
                rows_count,
                assets,
                min_id,
                max_id,
                min_price,
                max_price
            ) = row

            print(
                f"  {timestamp}"
                f" | rows={rows_count:,}"
                f" | assets={assets:,}"
                f" | id={min_id:,}→{max_id:,}"
            )

        # ----------------------------------------------------
        # FINAL ROOT-CAUSE INDICATORS
        # ----------------------------------------------------

        print_header("ROOT CAUSE INDICATORS")

        print(
            f"Total rows                 : "
            f"{overview['total']:,}"
        )

        print(
            f"NULL-lineage rows         : "
            f"{null_rows:,}"
        )

        print(
            f"NULL-lineage assets       : "
            f"{null_assets:,}"
        )

        print(
            f"NULL-lineage ID range     : "
            f"{null_min_id:,} → {null_max_id:,}"
        )

        print(
            f"Lineage transitions       : "
            f"{len(transitions):,}"
        )

        print(
            f"ID gaps                   : "
            f"{continuity['gaps']:,}"
        )

        if batch_distribution:

            dominant_pattern, dominant_count = (
                batch_distribution.most_common(1)[0]
            )

            rows_per_batch, assets_per_batch = dominant_pattern

            print(
                f"Dominant NULL batch       : "
                f"{rows_per_batch:,} rows / "
                f"{assets_per_batch:,} assets"
            )

            print(
                f"Dominant batch frequency  : "
                f"{dominant_count:,}"
            )

        print("\nInterpretation:")
        print(
            "  This audit identifies ingestion/writer patterns only."
        )
        print(
            "  It does NOT delete, rewrite, repair or rebuild data."
        )
        print(
            "  No database modification was performed."
        )

        print("\n" + "=" * 100)
        print("ARUNDA HISTORY WRITER ORIGIN AUDIT COMPLETE")
        print("=" * 100)
        print(
            "\nDatabase was opened in READ-ONLY mode."
        )
        print(
            "No INSERT / UPDATE / DELETE / ALTER / CREATE operation was executed."
        )

    except Exception as exc:

        print("\n" + "=" * 100)
        print("AUDIT FAILED")
        print("=" * 100)
        print(type(exc).__name__)
        print(str(exc))

        raise

    finally:

        if conn is not None:
            conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()