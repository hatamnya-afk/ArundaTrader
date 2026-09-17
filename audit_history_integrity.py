from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# =============================================================================
# ARUNDA TRADER — MARKET HISTORY INTEGRITY AUDIT
# Version: v0.1
#
# PURPOSE:
#   Forensic audit of market_history.
#
# GUARANTEE:
#   READ ONLY
#   NO INSERT
#   NO UPDATE
#   NO DELETE
#   NO ALTER
#   NO CREATE
#
# THIS ENGINE DOES NOT MODIFY arunda.db.
# =============================================================================


DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")


# =============================================================================
# CONTRACT
# =============================================================================

MIN_ASSET_DEPTH = 100

# Maximum acceptable gap between consecutive observations.
# This is intentionally configurable because the actual collection interval
# may evolve later.
MAX_GAP_SECONDS = 15 * 60

# Minimum number of records required before continuity is evaluated.
MIN_CONTINUITY_DEPTH = 10

# Maximum percentage of records with NULL source/engine metadata
# before lineage is considered contaminated.
MAX_NULL_LINEAGE_PCT = 5.0

# Maximum percentage of records belonging to a secondary source
# before source contamination is flagged.
MAX_SECONDARY_SOURCE_PCT = 5.0


# =============================================================================
# HELPERS
# =============================================================================

def safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_timestamp(value) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        # ISO-8601 Z support
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except ValueError:
        return None


def pct(part: int, total: int) -> float:
    if total == 0:
        return 0.0

    return (part / total) * 100.0


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def print_separator(char="=", length=100):
    print(char * length)


# =============================================================================
# DATABASE
# =============================================================================

def open_readonly_database() -> sqlite3.Connection:
    """
    Open SQLite database using SQLite URI read-only mode.

    mode=ro guarantees that SQLite opens the database read-only.
    """

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    connection = sqlite3.connect(
        uri,
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    return connection


# =============================================================================
# SCHEMA DISCOVERY
# =============================================================================

def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row["name"] for row in rows]


def require_columns(
    columns: list[str],
    required: list[str],
) -> None:

    missing = [
        column
        for column in required
        if column not in columns
    ]

    if missing:
        raise RuntimeError(
            "market_history is missing required columns: "
            + ", ".join(missing)
        )


# =============================================================================
# OVERVIEW
# =============================================================================

def audit_overview(
    connection: sqlite3.Connection,
) -> dict:

    row = connection.execute(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT symbol) AS distinct_symbols,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM market_history
        """
    ).fetchone()

    return dict(row)


# =============================================================================
# DUPLICATE AUDIT
# =============================================================================

def audit_duplicates(
    connection: sqlite3.Connection,
) -> dict:

    row = connection.execute(
        """
        SELECT
            COUNT(*) AS duplicate_groups,
            COALESCE(SUM(cnt - 1), 0) AS duplicate_rows
        FROM (
            SELECT
                timestamp,
                symbol,
                COUNT(*) AS cnt
            FROM market_history
            GROUP BY timestamp, symbol
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()

    worst = connection.execute(
        """
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS cnt
        FROM market_history
        GROUP BY timestamp, symbol
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 10
        """
    ).fetchall()

    return {
        "duplicate_groups": row["duplicate_groups"],
        "duplicate_rows": row["duplicate_rows"],
        "worst": [dict(x) for x in worst],
    }


# =============================================================================
# LINEAGE AUDIT
# =============================================================================

def audit_lineage(
    connection: sqlite3.Connection,
) -> dict:

    total = connection.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM market_history
        """
    ).fetchone()["cnt"]

    source_rows = connection.execute(
        """
        SELECT
            COALESCE(source, '<NULL>') AS source,
            COUNT(*) AS cnt
        FROM market_history
        GROUP BY source
        ORDER BY cnt DESC
        """
    ).fetchall()

    engine_rows = connection.execute(
        """
        SELECT
            COALESCE(engine_version, '<NULL>') AS engine_version,
            COUNT(*) AS cnt
        FROM market_history
        GROUP BY engine_version
        ORDER BY cnt DESC
        """
    ).fetchall()

    null_source = connection.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM market_history
        WHERE source IS NULL
        """
    ).fetchone()["cnt"]

    null_engine = connection.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM market_history
        WHERE engine_version IS NULL
        """
    ).fetchone()["cnt"]

    null_lineage = connection.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM market_history
        WHERE source IS NULL
           OR engine_version IS NULL
        """
    ).fetchone()["cnt"]

    return {
        "total": total,
        "sources": [dict(x) for x in source_rows],
        "engines": [dict(x) for x in engine_rows],
        "null_source": null_source,
        "null_engine": null_engine,
        "null_lineage": null_lineage,
        "null_source_pct": pct(null_source, total),
        "null_engine_pct": pct(null_engine, total),
        "null_lineage_pct": pct(null_lineage, total),
    }


# =============================================================================
# SOURCE CONTAMINATION
# =============================================================================

def audit_source_contamination(
    connection: sqlite3.Connection,
) -> list[dict]:

    assets = connection.execute(
        """
        SELECT DISTINCT symbol
        FROM market_history
        WHERE symbol IS NOT NULL
        ORDER BY symbol
        """
    ).fetchall()

    results = []

    for row in assets:

        symbol = row["symbol"]

        total = connection.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM market_history
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()["cnt"]

        sources = connection.execute(
            """
            SELECT
                COALESCE(source, '<NULL>') AS source,
                COUNT(*) AS cnt
            FROM market_history
            WHERE symbol = ?
            GROUP BY source
            ORDER BY cnt DESC
            """,
            (symbol,),
        ).fetchall()

        source_data = [dict(x) for x in sources]

        if not source_data:
            continue

        dominant = source_data[0]["source"]
        dominant_count = source_data[0]["cnt"]

        secondary_count = total - dominant_count

        secondary_pct = pct(
            secondary_count,
            total,
        )

        null_source_count = sum(
            x["cnt"]
            for x in source_data
            if x["source"] == "<NULL>"
        )

        null_source_pct = pct(
            null_source_count,
            total,
        )

        contaminated = (
            secondary_pct > MAX_SECONDARY_SOURCE_PCT
            or null_source_pct > MAX_NULL_LINEAGE_PCT
        )

        results.append(
            {
                "symbol": symbol,
                "total": total,
                "dominant_source": dominant,
                "dominant_count": dominant_count,
                "secondary_count": secondary_count,
                "secondary_pct": secondary_pct,
                "null_source_count": null_source_count,
                "null_source_pct": null_source_pct,
                "contaminated": contaminated,
                "sources": source_data,
            }
        )

    return results


# =============================================================================
# DEPTH AUDIT
# =============================================================================

def audit_depth(
    connection: sqlite3.Connection,
) -> list[dict]:

    rows = connection.execute(
        """
        SELECT
            symbol,
            COUNT(*) AS depth,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM market_history
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        ORDER BY depth DESC
        """
    ).fetchall()

    return [dict(x) for x in rows]


# =============================================================================
# TIMESTAMP CONTINUITY
# =============================================================================

def audit_asset_continuity(
    connection: sqlite3.Connection,
    symbol: str,
) -> dict:

    rows = connection.execute(
        """
        SELECT timestamp
        FROM market_history
        WHERE symbol = ?
          AND timestamp IS NOT NULL
        ORDER BY timestamp
        """,
        (symbol,),
    ).fetchall()

    timestamps = []

    invalid_timestamps = 0

    for row in rows:

        dt = parse_timestamp(row["timestamp"])

        if dt is None:
            invalid_timestamps += 1
        else:
            timestamps.append(dt)

    if len(timestamps) < MIN_CONTINUITY_DEPTH:

        return {
            "symbol": symbol,
            "records": len(rows),
            "valid_timestamps": len(timestamps),
            "invalid_timestamps": invalid_timestamps,
            "gaps": 0,
            "max_gap_seconds": None,
            "avg_gap_seconds": None,
            "continuity_pct": None,
            "status": "INSUFFICIENT",
        }

    gaps = []

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):

        delta = (
            current - previous
        ).total_seconds()

        if delta >= 0:
            gaps.append(delta)

    if not gaps:

        return {
            "symbol": symbol,
            "records": len(rows),
            "valid_timestamps": len(timestamps),
            "invalid_timestamps": invalid_timestamps,
            "gaps": 0,
            "max_gap_seconds": None,
            "avg_gap_seconds": None,
            "continuity_pct": 100.0,
            "status": "VALID",
        }

    large_gaps = [
        gap
        for gap in gaps
        if gap > MAX_GAP_SECONDS
    ]

    continuity = (
        100.0
        * (len(gaps) - len(large_gaps))
        / len(gaps)
    )

    max_gap = max(gaps)
    avg_gap = sum(gaps) / len(gaps)

    if invalid_timestamps > 0:
        status = "DEGRADED"

    elif large_gaps:
        status = "GAPPED"

    else:
        status = "VALID"

    return {
        "symbol": symbol,
        "records": len(rows),
        "valid_timestamps": len(timestamps),
        "invalid_timestamps": invalid_timestamps,
        "gaps": len(large_gaps),
        "max_gap_seconds": max_gap,
        "avg_gap_seconds": avg_gap,
        "continuity_pct": continuity,
        "status": status,
    }


def audit_continuity(
    connection: sqlite3.Connection,
) -> list[dict]:

    symbols = connection.execute(
        """
        SELECT DISTINCT symbol
        FROM market_history
        WHERE symbol IS NOT NULL
        ORDER BY symbol
        """
    ).fetchall()

    results = []

    for row in symbols:

        results.append(
            audit_asset_continuity(
                connection,
                row["symbol"],
            )
        )

    return results


# =============================================================================
# PER-ASSET LINEAGE
# =============================================================================

def audit_asset_lineage(
    connection: sqlite3.Connection,
    symbol: str,
) -> dict:

    total = connection.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM market_history
        WHERE symbol = ?
        """,
        (symbol,),
    ).fetchone()["cnt"]

    source_rows = connection.execute(
        """
        SELECT
            COALESCE(source, '<NULL>') AS source,
            COUNT(*) AS cnt
        FROM market_history
        WHERE symbol = ?
        GROUP BY source
        ORDER BY cnt DESC
        """,
        (symbol,),
    ).fetchall()

    engine_rows = connection.execute(
        """
        SELECT
            COALESCE(engine_version, '<NULL>') AS engine_version,
            COUNT(*) AS cnt
        FROM market_history
        WHERE symbol = ?
        GROUP BY engine_version
        ORDER BY cnt DESC
        """,
        (symbol,),
    ).fetchall()

    return {
        "symbol": symbol,
        "total": total,
        "sources": [dict(x) for x in source_rows],
        "engines": [dict(x) for x in engine_rows],
    }


# =============================================================================
# QUALITY CLASSIFICATION
# =============================================================================

def classify_asset(
    depth: int,
    duplicate_rows: int,
    continuity: dict,
    contamination: dict,
    lineage_null_pct: float,
) -> str:

    if depth < MIN_ASSET_DEPTH:
        return "INSUFFICIENT"

    if duplicate_rows > 0:
        return "DEGRADED"

    if contamination["contaminated"]:
        return "CONTAMINATED"

    if lineage_null_pct > MAX_NULL_LINEAGE_PCT:
        return "CONTAMINATED"

    if continuity["status"] in {
        "GAPPED",
        "DEGRADED",
    }:
        return "DEGRADED"

    if continuity["status"] == "INSUFFICIENT":
        return "INSUFFICIENT"

    return "HEALTHY"


def build_quality_report(
    connection: sqlite3.Connection,
) -> list[dict]:

    depth_rows = audit_depth(connection)
    continuity_rows = audit_continuity(connection)
    contamination_rows = audit_source_contamination(connection)

    continuity_map = {
        row["symbol"]: row
        for row in continuity_rows
    }

    contamination_map = {
        row["symbol"]: row
        for row in contamination_rows
    }

    report = []

    for depth_row in depth_rows:

        symbol = depth_row["symbol"]
        depth = depth_row["depth"]

        duplicate_row = connection.execute(
            """
            SELECT COALESCE(SUM(cnt - 1), 0) AS duplicate_rows
            FROM (
                SELECT
                    timestamp,
                    symbol,
                    COUNT(*) AS cnt
                FROM market_history
                WHERE symbol = ?
                GROUP BY timestamp, symbol
                HAVING COUNT(*) > 1
            )
            """,
            (symbol,),
        ).fetchone()

        duplicate_rows = duplicate_row["duplicate_rows"]

        lineage = audit_asset_lineage(
            connection,
            symbol,
        )

        null_lineage_count = 0

        for source in lineage["sources"]:
            if source["source"] == "<NULL>":
                null_lineage_count += source["cnt"]

        for engine in lineage["engines"]:
            if engine["engine_version"] == "<NULL>":
                pass

        lineage_null_pct = pct(
            null_lineage_count,
            depth,
        )

        continuity = continuity_map[symbol]
        contamination = contamination_map[symbol]

        quality = classify_asset(
            depth=depth,
            duplicate_rows=duplicate_rows,
            continuity=continuity,
            contamination=contamination,
            lineage_null_pct=lineage_null_pct,
        )

        report.append(
            {
                "symbol": symbol,
                "depth": depth,
                "first_timestamp": depth_row["first_timestamp"],
                "last_timestamp": depth_row["last_timestamp"],
                "duplicate_rows": duplicate_rows,
                "continuity_status": continuity["status"],
                "continuity_pct": continuity["continuity_pct"],
                "max_gap_seconds": continuity["max_gap_seconds"],
                "dominant_source": contamination["dominant_source"],
                "secondary_pct": contamination["secondary_pct"],
                "null_source_pct": contamination["null_source_pct"],
                "lineage_null_pct": lineage_null_pct,
                "quality": quality,
            }
        )

    return report


# =============================================================================
# PRINT FUNCTIONS
# =============================================================================

def print_overview(overview: dict):

    print_separator()
    print("DATABASE / MARKET HISTORY OVERVIEW")
    print_separator()

    print(f"Total History Rows : {overview['total_rows']}")
    print(f"Historical Assets  : {overview['distinct_symbols']}")
    print(f"First Timestamp    : {overview['first_timestamp']}")
    print(f"Last Timestamp     : {overview['last_timestamp']}")


def print_duplicates(data: dict):

    print_separator("-")
    print("DUPLICATE AUDIT")
    print_separator("-")

    print(
        f"Duplicate Groups   : {data['duplicate_groups']}"
    )

    print(
        f"Duplicate Rows     : {data['duplicate_rows']}"
    )

    if data["worst"]:

        print()
        print("Worst duplicate groups:")

        for row in data["worst"]:

            print(
                f"  {row['symbol']:<15} "
                f"{row['timestamp']}  "
                f"x{row['cnt']}"
            )


def print_lineage(data: dict):

    print_separator("-")
    print("LINEAGE AUDIT")
    print_separator("-")

    print(
        f"NULL source       : "
        f"{data['null_source']} "
        f"({fmt_pct(data['null_source_pct'])})"
    )

    print(
        f"NULL engine       : "
        f"{data['null_engine']} "
        f"({fmt_pct(data['null_engine_pct'])})"
    )

    print(
        f"NULL lineage      : "
        f"{data['null_lineage']} "
        f"({fmt_pct(data['null_lineage_pct'])})"
    )

    print()
    print("Sources:")

    for row in data["sources"]:

        print(
            f"  {row['source']:<30} "
            f"{row['cnt']:>10}"
        )

    print()
    print("Engine versions:")

    for row in data["engines"]:

        print(
            f"  {row['engine_version']:<35} "
            f"{row['cnt']:>10}"
        )


def print_depth_summary(
    depth_rows: list[dict],
):

    print_separator("-")
    print("DEPTH AUDIT")
    print_separator("-")

    if not depth_rows:
        return

    depths = [
        row["depth"]
        for row in depth_rows
    ]

    print(
        f"Minimum Depth      : {min(depths)}"
    )

    print(
        f"Maximum Depth      : {max(depths)}"
    )

    print(
        f"Average Depth      : "
        f"{sum(depths) / len(depths):.2f}"
    )

    print()

    print(
        "Assets with insufficient depth "
        f"(< {MIN_ASSET_DEPTH}): "
        f"{sum(1 for x in depths if x < MIN_ASSET_DEPTH)}"
    )


def print_continuity_summary(
    continuity_rows: list[dict],
):

    print_separator("-")
    print("TIMESTAMP CONTINUITY AUDIT")
    print_separator("-")

    counter = Counter(
        row["status"]
        for row in continuity_rows
    )

    for status in [
        "VALID",
        "GAPPED",
        "DEGRADED",
        "INSUFFICIENT",
    ]:

        print(
            f"{status:<15} : "
            f"{counter.get(status, 0)}"
        )

    gapped = [
        row
        for row in continuity_rows
        if row["status"] == "GAPPED"
    ]

    if gapped:

        print()
        print("Largest gaps:")

        ranked = sorted(
            gapped,
            key=lambda x: (
                x["max_gap_seconds"] or 0
            ),
            reverse=True,
        )

        for row in ranked[:20]:

            print(
                f"  {row['symbol']:<15} "
                f"max_gap="
                f"{row['max_gap_seconds']:.0f}s "
                f"continuity="
                f"{row['continuity_pct']:.2f}%"
            )


def print_contamination(
    contamination_rows: list[dict],
):

    print_separator("-")
    print("SOURCE CONTAMINATION AUDIT")
    print_separator("-")

    contaminated = [
        row
        for row in contamination_rows
        if row["contaminated"]
    ]

    print(
        f"Contaminated Assets : "
        f"{len(contaminated)}"
    )

    if contaminated:

        print()

        ranked = sorted(
            contaminated,
            key=lambda x: (
                x["secondary_pct"],
                x["null_source_pct"],
            ),
            reverse=True,
        )

        for row in ranked[:30]:

            print(
                f"  {row['symbol']:<15} "
                f"dominant={row['dominant_source']:<20} "
                f"secondary={row['secondary_pct']:.2f}% "
                f"NULL={row['null_source_pct']:.2f}%"
            )


def print_quality_report(
    report: list[dict],
):

    print_separator()
    print("ASSET QUALITY CLASSIFICATION")
    print_separator()

    counter = Counter(
        row["quality"]
        for row in report
    )

    print(
        f"HEALTHY          : "
        f"{counter.get('HEALTHY', 0)}"
    )

    print(
        f"DEGRADED         : "
        f"{counter.get('DEGRADED', 0)}"
    )

    print(
        f"CONTAMINATED     : "
        f"{counter.get('CONTAMINATED', 0)}"
    )

    print(
        f"INSUFFICIENT     : "
        f"{counter.get('INSUFFICIENT', 0)}"
    )

    print()

    print(
        "Top degraded / contaminated assets:"
    )

    priority = {
        "CONTAMINATED": 0,
        "DEGRADED": 1,
        "INSUFFICIENT": 2,
        "HEALTHY": 3,
    }

    ranked = sorted(
        report,
        key=lambda x: (
            priority[x["quality"]],
            -x["depth"],
        ),
    )

    for row in ranked[:50]:

        print(
            f"  {row['symbol']:<15} "
            f"depth={row['depth']:<5} "
            f"dup={row['duplicate_rows']:<5} "
            f"continuity="
            f"{str(row['continuity_status']):<12} "
            f"source="
            f"{str(row['dominant_source']):<18} "
            f"quality={row['quality']}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print()
    print_separator()
    print("ARUNDA TRADER — MARKET HISTORY INTEGRITY AUDIT v0.1")
    print_separator()

    print("MODE                 : READ ONLY")
    print(f"DATABASE             : {DB_PATH}")
    print("WRITE OPERATIONS     : NONE")
    print("SCHEMA CHANGES       : NONE")
    print("DELETE OPERATIONS    : NONE")

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = open_readonly_database()

    try:

        columns = get_table_columns(
            connection,
            "market_history",
        )

        require_columns(
            columns,
            [
                "timestamp",
                "symbol",
                "price",
            ],
        )

        # Optional lineage columns.
        has_source = "source" in columns
        has_engine = "engine_version" in columns

        if not has_source or not has_engine:

            print()
            print(
                "WARNING: lineage columns are incomplete."
            )

        overview = audit_overview(
            connection
        )

        duplicate_data = audit_duplicates(
            connection
        )

        lineage_data = audit_lineage(
            connection
        )

        depth_rows = audit_depth(
            connection
        )

        continuity_rows = audit_continuity(
            connection
        )

        contamination_rows = (
            audit_source_contamination(
                connection
            )
        )

        quality_report = build_quality_report(
            connection
        )

        print_overview(
            overview
        )

        print_duplicates(
            duplicate_data
        )

        print_lineage(
            lineage_data
        )

        print_depth_summary(
            depth_rows
        )

        print_continuity_summary(
            continuity_rows
        )

        print_contamination(
            contamination_rows
        )

        print_quality_report(
            quality_report
        )

        # =====================================================================
        # FINAL INTEGRITY VERDICT
        # =====================================================================

        print_separator()
        print("FINAL MARKET HISTORY INTEGRITY VERDICT")
        print_separator()

        healthy = sum(
            1
            for row in quality_report
            if row["quality"] == "HEALTHY"
        )

        degraded = sum(
            1
            for row in quality_report
            if row["quality"] == "DEGRADED"
        )

        contaminated = sum(
            1
            for row in quality_report
            if row["quality"] == "CONTAMINATED"
        )

        insufficient = sum(
            1
            for row in quality_report
            if row["quality"] == "INSUFFICIENT"
        )

        total_assets = len(
            quality_report
        )

        print(
            f"Assets Audited      : "
            f"{total_assets}"
        )

        print(
            f"Healthy Assets      : "
            f"{healthy}"
        )

        print(
            f"Degraded Assets     : "
            f"{degraded}"
        )

        print(
            f"Contaminated Assets : "
            f"{contaminated}"
        )

        print(
            f"Insufficient Assets : "
            f"{insufficient}"
        )

        if contaminated > 0:
            verdict = "CONTAMINATED"

        elif degraded > 0:
            verdict = "DEGRADED"

        elif insufficient > 0:
            verdict = "INCOMPLETE"

        else:
            verdict = "HEALTHY"

        print()
        print(
            f"MARKET HISTORY STATUS : {verdict}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "This audit does NOT modify market_history."
        )

        print(
            "No records were inserted, updated or deleted."
        )

        print_separator()
        print(
            "ARUNDA MARKET HISTORY INTEGRITY AUDIT COMPLETE"
        )
        print_separator()

    finally:

        connection.close()


if __name__ == "__main__":
    main()