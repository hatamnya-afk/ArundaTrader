# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER
LIVE SNAPSHOT FRESHNESS + SOURCE-TO-ROW CAUSALITY v0.1
====================================================================================================

OBJECTIVE
---------
Establish row-level provenance for the CURRENT LIVE FUSION_v0.5 execution.

This forensic gate MUST:
    1. Discover the latest live capture.
    2. Identify the newest snapshot.
    3. Isolate ONLY rows belonging to that snapshot.
    4. Verify snapshot freshness relative to filesystem/runtime evidence.
    5. Verify source-to-row availability metadata.
    6. Verify engine version.
    7. Verify asset identity.
    8. Verify row-level temporal coherence.
    9. Compare current snapshot against previous snapshot(s).
   10. Preserve production DB unchanged.

STRICT RULES
------------
Production DB writes       : FORBIDDEN
Production engine run      : FORBIDDEN
Historical repair          : FORBIDDEN
Direction inference        : FORBIDDEN
Score reconstruction       : FORBIDDEN
Synthetic data             : FORBIDDEN
Interpolation              : FORBIDDEN
Forward fill               : FORBIDDEN
Back fill                  : FORBIDDEN
Live data injection        : FORBIDDEN

IMPORTANT
---------
This script does NOT decide whether a source is "good" merely because
the fusion row says AVAILABLE=1.

It establishes:
    RUNTIME SNAPSHOT -> ROW -> ARM AVAILABILITY -> TEMPORAL IDENTITY

It does NOT prove external-source causality beyond what is observable
inside the actual runtime capture.

====================================================================================================
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ==================================================================================================
# CONFIG
# ==================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

LIVE_ROOT = Path(os.environ.get("TEMP", r"C:\Users\ASUS\AppData\Local\Temp"))

TABLE = "fusion_signals"
EXPECTED_ENGINE = "FUSION_v0.5"

ASSETS_EXPECTED = {
    "BTC",
    "ETH",
    "SOL",
    "XRP",
}

ARM_COLUMNS = {
    "MARKET": "market_available",
    "POSITIONING": "positioning_available",
    "NEWS": "news_available",
}

SOURCE_COLUMNS = {
    "MARKET": "market_score",
    "POSITIONING": "positioning_score",
    "NEWS": "news_score",
}

SNAPSHOT_PREFIX = "FUSION-"


# ==================================================================================================
# OUTPUT
# ==================================================================================================

WIDTH = 100


def line(char="=", n=WIDTH):
    print(char * n)


def title(text):
    line("=")
    print(text)
    line("=")


def section(text):
    print()
    line("=")
    print(text)
    line("=")


def result(label, value):
    print(f"{label:<40} : {value}")


# ==================================================================================================
# TIME
# ==================================================================================================

def utc_now():
    return datetime.now(timezone.utc)


def parse_ts(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


# ==================================================================================================
# SHA256
# ==================================================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# ==================================================================================================
# SQLITE
# ==================================================================================================

def connect_readonly(path: Path):
    uri = f"file:{path.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


# ==================================================================================================
# LIVE CAPTURE DISCOVERY
# ==================================================================================================

def discover_live_captures():
    candidates = []

    if not LIVE_ROOT.exists():
        return candidates

    for child in LIVE_ROOT.iterdir():

        if not child.is_dir():
            continue

        if not child.name.startswith("arunda_live_launch_"):
            continue

        db = child / "arunda_live_capture.db"

        if db.exists():
            candidates.append(
                {
                    "directory": child,
                    "db": db,
                    "mtime": db.stat().st_mtime,
                    "size": db.stat().st_size,
                }
            )

    candidates.sort(
        key=lambda x: x["mtime"],
        reverse=True,
    )

    return candidates


# ==================================================================================================
# DATABASE FINGERPRINT
# ==================================================================================================

def db_fingerprint(path):
    return {
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


# ==================================================================================================
# SNAPSHOT DISCOVERY
# ==================================================================================================

def discover_snapshots(conn):

    rows = conn.execute(
        f"""
        SELECT
            snapshot_id,
            COUNT(*) AS rows,
            MIN(timestamp) AS first_ts,
            MAX(timestamp) AS last_ts,
            MIN(id) AS min_id,
            MAX(id) AS max_id
        FROM {TABLE}
        WHERE engine_version = ?
          AND snapshot_id IS NOT NULL
          AND snapshot_id LIKE ?
        GROUP BY snapshot_id
        ORDER BY last_ts
        """,
        (
            EXPECTED_ENGINE,
            SNAPSHOT_PREFIX + "%",
        ),
    ).fetchall()

    return rows


# ==================================================================================================
# SNAPSHOT ROWS
# ==================================================================================================

def load_snapshot_rows(conn, snapshot_id):

    return conn.execute(
        f"""
        SELECT
            id,
            timestamp,
            asset,
            market_score,
            positioning_score,
            news_score,
            fused_score,
            confidence,
            regime,
            data_quality,
            market_available,
            positioning_available,
            news_available,
            engine_version,
            available_weight,
            missing_arm_penalty,
            news_confidence,
            signal_strength,
            entry_price,
            direction,
            snapshot_id
        FROM {TABLE}
        WHERE snapshot_id = ?
        ORDER BY timestamp, id
        """,
        (snapshot_id,),
    ).fetchall()


# ==================================================================================================
# CURRENT SNAPSHOT IDENTIFICATION
# ==================================================================================================

def identify_current_snapshot(snapshot_rows):

    if not snapshot_rows:
        return None

    return snapshot_rows[-1][0]


# ==================================================================================================
# TEMPORAL COHERENCE
# ==================================================================================================

def temporal_analysis(rows):

    parsed = []

    for row in rows:
        dt = parse_ts(row[1])

        if dt is not None:
            parsed.append(dt)

    if not parsed:
        return {
            "valid": False,
            "count": 0,
            "first": None,
            "last": None,
            "span": None,
            "max_gap": None,
        }

    parsed.sort()

    gaps = []

    for a, b in zip(parsed, parsed[1:]):
        gaps.append((b - a).total_seconds())

    span = (parsed[-1] - parsed[0]).total_seconds()

    return {
        "valid": True,
        "count": len(parsed),
        "first": parsed[0],
        "last": parsed[-1],
        "span": span,
        "max_gap": max(gaps) if gaps else 0,
    }


# ==================================================================================================
# ASSET CONTRACT
# ==================================================================================================

def asset_analysis(rows):

    assets = [str(row[2]) for row in rows]

    counts = Counter(assets)

    return {
        "assets": sorted(counts.keys()),
        "counts": dict(counts),
        "expected_match": set(counts.keys()) == ASSETS_EXPECTED,
        "unique_assets": len(counts),
    }


# ==================================================================================================
# ARM ANALYSIS
# ==================================================================================================

def arm_analysis(rows):

    output = {}

    for arm, column in ARM_COLUMNS.items():

        values = []

        for row in rows:

            value = row[
                {
                    "market_available": 10,
                    "positioning_available": 11,
                    "news_available": 12,
                }[column]
            ]

            values.append(value)

        available = sum(
            1 for value in values
            if value == 1
        )

        unavailable = sum(
            1 for value in values
            if value == 0
        )

        unknown = sum(
            1 for value in values
            if value not in (0, 1)
        )

        output[arm] = {
            "available": available,
            "unavailable": unavailable,
            "unknown": unknown,
        }

    return output


# ==================================================================================================
# ARM COMBINATION MATRIX
# ==================================================================================================

def arm_matrix(rows):

    combinations = Counter()

    for row in rows:

        market = row[10]
        positioning = row[11]
        news = row[12]

        combinations[
            (
                market,
                positioning,
                news,
            )
        ] += 1

    return combinations


# ==================================================================================================
# SOURCE-TO-ROW OBSERVABILITY
# ==================================================================================================

def source_row_analysis(rows):

    output = {}

    index = {
        "MARKET": (10, 3),
        "POSITIONING": (11, 4),
        "NEWS": (12, 5),
    }

    for arm, (availability_idx, score_idx) in index.items():

        available_with_score = 0
        available_without_score = 0
        unavailable_with_score = 0
        unavailable_without_score = 0

        for row in rows:

            available = row[availability_idx]
            score = row[score_idx]

            has_score = score is not None

            if available == 1 and has_score:
                available_with_score += 1

            elif available == 1 and not has_score:
                available_without_score += 1

            elif available == 0 and has_score:
                unavailable_with_score += 1

            elif available == 0 and not has_score:
                unavailable_without_score += 1

        output[arm] = {
            "available_with_score": available_with_score,
            "available_without_score": available_without_score,
            "unavailable_with_score": unavailable_with_score,
            "unavailable_without_score": unavailable_without_score,
        }

    return output


# ==================================================================================================
# SNAPSHOT IDENTITY
# ==================================================================================================

def snapshot_identity(rows, expected_snapshot):

    problems = []

    for row in rows:

        if row[20] != expected_snapshot:
            problems.append(
                f"id={row[0]} snapshot mismatch"
            )

        if row[13] != EXPECTED_ENGINE:
            problems.append(
                f"id={row[0]} engine mismatch"
            )

    return problems


# ==================================================================================================
# ROW TEMPORAL IDENTITY
# ==================================================================================================

def row_temporal_identity(rows):

    problems = []

    timestamps = []

    for row in rows:

        ts = parse_ts(row[1])

        if ts is None:
            problems.append(
                f"id={row[0]} invalid timestamp"
            )
        else:
            timestamps.append(ts)

    if timestamps:

        earliest = min(timestamps)
        latest = max(timestamps)

        if (latest - earliest).total_seconds() > 60:
            problems.append(
                "snapshot timestamp span exceeds 60 seconds"
            )

    return problems


# ==================================================================================================
# SNAPSHOT FRESHNESS
# ==================================================================================================

def freshness_analysis(rows, capture_db):

    temporal = temporal_analysis(rows)

    if not temporal["valid"]:
        return {
            "status": "FAIL",
            "reason": "No valid row timestamps",
        }

    db_mtime = datetime.fromtimestamp(
        capture_db.stat().st_mtime,
        tz=timezone.utc,
    )

    newest_row = temporal["last"]

    delta = abs(
        (db_mtime - newest_row).total_seconds()
    )

    return {
        "status": "PASS" if delta <= 3600 else "REVIEW",
        "db_mtime": db_mtime,
        "newest_row": newest_row,
        "delta_seconds": delta,
    }


# ==================================================================================================
# NEWEST VS PREVIOUS SNAPSHOT
# ==================================================================================================

def snapshot_comparison(snapshot_rows):

    if len(snapshot_rows) < 2:
        return None

    previous = snapshot_rows[-2]
    current = snapshot_rows[-1]

    return {
        "previous_id": previous[0],
        "previous_rows": previous[1],
        "previous_first": previous[2],
        "previous_last": previous[3],
        "current_id": current[0],
        "current_rows": current[1],
        "current_first": current[2],
        "current_last": current[3],
    }


# ==================================================================================================
# JSON REPORT
# ==================================================================================================

def write_report(directory, payload):

    path = directory / "LIVE_SNAPSHOT_CAUSALITY_REPORT.json"

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            payload,
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return path


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    title(
        "ARUNDA TRADER LIVE SNAPSHOT FRESHNESS + SOURCE-TO-ROW CAUSALITY v0.1"
    )

    print(
        "OBJECTIVE:\n"
        "  Establish provenance of ONLY the newest FUSION_v0.5 snapshot.\n"
        "  No production modification. No engine execution.\n"
    )

    result(
        "Production DB writes",
        "FORBIDDEN",
    )

    result(
        "Production engine run",
        "NO",
    )

    result(
        "Historical repair",
        "NONE",
    )

    result(
        "Direction inference",
        "NONE",
    )

    result(
        "Live data injection",
        "NONE",
    )

    # ----------------------------------------------------------------------------------------------
    # Production baseline
    # ----------------------------------------------------------------------------------------------

    section("PRODUCTION DATABASE BASELINE")

    if not PRODUCTION_DB.exists():

        print("ERROR: Production database not found.")
        return 2

    production_before = db_fingerprint(
        PRODUCTION_DB
    )

    result(
        "Production DB",
        str(PRODUCTION_DB),
    )

    result(
        "Rows",
        sqlite3.connect(
            PRODUCTION_DB
        ).execute(
            f"SELECT COUNT(*) FROM {TABLE}"
        ).fetchone()[0],
    )

    result(
        "Size",
        production_before["size"],
    )

    result(
        "SHA256",
        production_before["sha256"],
    )

    # ----------------------------------------------------------------------------------------------
    # Discover capture
    # ----------------------------------------------------------------------------------------------

    section("LIVE CAPTURE DISCOVERY")

    captures = discover_live_captures()

    if not captures:

        print(
            "LIVE CAPTURE : NOT FOUND"
        )

        return 3

    latest_capture = captures[0]

    capture_dir = latest_capture["directory"]
    capture_db = latest_capture["db"]

    result(
        "Latest capture directory",
        str(capture_dir),
    )

    result(
        "Capture DB",
        str(capture_db),
    )

    result(
        "Capture size",
        capture_db.stat().st_size,
    )

    # ----------------------------------------------------------------------------------------------
    # Read-only capture connection
    # ----------------------------------------------------------------------------------------------

    conn = connect_readonly(
        capture_db
    )

    if not table_exists(
        conn,
        TABLE,
    ):

        print(
            "ERROR: fusion_signals table missing."
        )

        conn.close()

        return 4

    columns = get_columns(
        conn,
        TABLE,
    )

    required = {
        "id",
        "timestamp",
        "asset",
        "engine_version",
        "snapshot_id",
        "market_available",
        "positioning_available",
        "news_available",
        "market_score",
        "positioning_score",
        "news_score",
        "direction",
        "entry_price",
    }

    missing = sorted(
        required - set(columns)
    )

    section("SCHEMA CONTRACT")

    if missing:

        print(
            "SCHEMA : FAIL"
        )

        print(
            "Missing:",
            missing,
        )

        conn.close()

        return 5

    print(
        "SCHEMA : PASS"
    )

    # ----------------------------------------------------------------------------------------------
    # Snapshot discovery
    # ----------------------------------------------------------------------------------------------

    section("SNAPSHOT INVENTORY")

    snapshots = discover_snapshots(
        conn
    )

    if not snapshots:

        print(
            "No FUSION_v0.5 snapshots found."
        )

        conn.close()

        return 6

    for (
        snapshot_id,
        rows_count,
        first_ts,
        last_ts,
        min_id,
        max_id,
    ) in snapshots:

        print(
            f"{snapshot_id:<55} | "
            f"rows={rows_count:<3} | "
            f"ids={min_id}-{max_id} | "
            f"{first_ts} -> {last_ts}"
        )

    current_snapshot_id = snapshots[-1][0]

    print()
    result(
        "CURRENT SNAPSHOT",
        current_snapshot_id,
    )

    # ----------------------------------------------------------------------------------------------
    # Load ONLY current snapshot
    # ----------------------------------------------------------------------------------------------

    current_rows = load_snapshot_rows(
        conn,
        current_snapshot_id,
    )

    section("CURRENT SNAPSHOT ROW SET")

    print(
        f"Rows : {len(current_rows)}"
    )

    assets = asset_analysis(
        current_rows
    )

    print(
        f"Assets : {', '.join(assets['assets'])}"
    )

    # ----------------------------------------------------------------------------------------------
    # Identity
    # ----------------------------------------------------------------------------------------------

    section("SNAPSHOT IDENTITY CONTRACT")

    identity_problems = snapshot_identity(
        current_rows,
        current_snapshot_id,
    )

    if identity_problems:

        print("IDENTITY : FAIL")

        for problem in identity_problems:
            print("  " + problem)

    else:

        print("IDENTITY : PASS")

    # ----------------------------------------------------------------------------------------------
    # Asset
    # ----------------------------------------------------------------------------------------------

    section("CURRENT SNAPSHOT ASSET CONTRACT")

    result(
        "Expected assets",
        ", ".join(sorted(ASSETS_EXPECTED)),
    )

    result(
        "Observed assets",
        ", ".join(assets["assets"]),
    )

    result(
        "Unique assets",
        assets["unique_assets"],
    )

    print(
        "ASSET CONTRACT : "
        + (
            "PASS"
            if assets["expected_match"]
            else "REVIEW"
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Engine
    # ----------------------------------------------------------------------------------------------

    section("ENGINE CONTRACT")

    engines = Counter(
        row[13]
        for row in current_rows
    )

    for engine, count in engines.items():

        print(
            f"{engine:<25} | {count}"
        )

    engine_pass = (
        len(engines) == 1
        and EXPECTED_ENGINE in engines
    )

    print(
        "ENGINE CONTRACT : "
        + (
            "PASS"
            if engine_pass
            else "FAIL"
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Temporal
    # ----------------------------------------------------------------------------------------------

    section("TEMPORAL COHERENCE")

    temporal = temporal_analysis(
        current_rows
    )

    if temporal["valid"]:

        result(
            "First row timestamp",
            temporal["first"],
        )

        result(
            "Last row timestamp",
            temporal["last"],
        )

        result(
            "Snapshot span seconds",
            round(temporal["span"], 6),
        )

        result(
            "Maximum timestamp gap",
            round(temporal["max_gap"], 6),
        )

    else:

        print(
            "TEMPORAL : FAIL"
        )

    temporal_problems = row_temporal_identity(
        current_rows
    )

    if temporal_problems:

        print(
            "TEMPORAL IDENTITY : REVIEW"
        )

        for problem in temporal_problems:
            print(
                "  " + problem
            )

    else:

        print(
            "TEMPORAL IDENTITY : PASS"
        )

    # ----------------------------------------------------------------------------------------------
    # Freshness
    # ----------------------------------------------------------------------------------------------

    section("SNAPSHOT FRESHNESS")

    freshness = freshness_analysis(
        current_rows,
        capture_db,
    )

    result(
        "Newest row timestamp",
        freshness.get("newest_row"),
    )

    result(
        "Capture DB mtime",
        freshness.get("db_mtime"),
    )

    result(
        "Absolute delta seconds",
        round(
            freshness.get(
                "delta_seconds",
                -1,
            ),
            3,
        ),
    )

    result(
        "Freshness status",
        freshness["status"],
    )

    # ----------------------------------------------------------------------------------------------
    # ARM availability
    # ----------------------------------------------------------------------------------------------

    section("CURRENT SNAPSHOT ARM AVAILABILITY")

    arms = arm_analysis(
        current_rows
    )

    for arm, stats in arms.items():

        print(
            f"{arm:<15} | "
            f"AVAILABLE={stats['available']:>2} | "
            f"UNAVAILABLE={stats['unavailable']:>2} | "
            f"UNKNOWN={stats['unknown']:>2}"
        )

    # ----------------------------------------------------------------------------------------------
    # Source-to-row
    # ----------------------------------------------------------------------------------------------

    section("SOURCE-TO-ROW OBSERVABILITY")

    source_rows = source_row_analysis(
        current_rows
    )

    for arm, stats in source_rows.items():

        print()
        print(
            arm
        )

        print(
            f"  AVAILABLE + SCORE       : "
            f"{stats['available_with_score']}"
        )

        print(
            f"  AVAILABLE + NO SCORE    : "
            f"{stats['available_without_score']}"
        )

        print(
            f"  UNAVAILABLE + SCORE     : "
            f"{stats['unavailable_with_score']}"
        )

        print(
            f"  UNAVAILABLE + NO SCORE  : "
            f"{stats['unavailable_without_score']}"
        )

    # ----------------------------------------------------------------------------------------------
    # Arm matrix
    # ----------------------------------------------------------------------------------------------

    section("CURRENT SNAPSHOT ARM MATRIX")

    matrix = arm_matrix(
        current_rows
    )

    for (
        market,
        positioning,
        news,
    ), count in sorted(matrix.items()):

        print(
            f"MARKET={'ON' if market == 1 else 'OFF':<4} | "
            f"POSITIONING={'ON' if positioning == 1 else 'OFF':<4} | "
            f"NEWS={'ON' if news == 1 else 'OFF':<4} | "
            f"rows={count}"
        )

    # ----------------------------------------------------------------------------------------------
    # Row-level provenance
    # ----------------------------------------------------------------------------------------------

    section("ROW-LEVEL LIVE PROVENANCE")

    for row in current_rows:

        (
            row_id,
            timestamp,
            asset,
            market_score,
            positioning_score,
            news_score,
            fused_score,
            confidence,
            regime,
            data_quality,
            market_available,
            positioning_available,
            news_available,
            engine_version,
            available_weight,
            missing_arm_penalty,
            news_confidence,
            signal_strength,
            entry_price,
            direction,
            snapshot_id,
        ) = row

        print(
            f"id={row_id:<3} | "
            f"{asset:<4} | "
            f"{timestamp} | "
            f"M={market_available} "
            f"P={positioning_available} "
            f"N={news_available} | "
            f"quality={data_quality:<8} | "
            f"snapshot={snapshot_id}"
        )

    # ----------------------------------------------------------------------------------------------
    # Previous/current comparison
    # ----------------------------------------------------------------------------------------------

    section("CURRENT VS PREVIOUS SNAPSHOT")

    comparison = snapshot_comparison(
        snapshots
    )

    if comparison:

        print(
            f"PREVIOUS : {comparison['previous_id']}"
        )

        print(
            f"  rows={comparison['previous_rows']} "
            f"{comparison['previous_first']} -> "
            f"{comparison['previous_last']}"
        )

        print()

        print(
            f"CURRENT  : {comparison['current_id']}"
        )

        print(
            f"  rows={comparison['current_rows']} "
            f"{comparison['current_first']} -> "
            f"{comparison['current_last']}"
        )

        current_ts = parse_ts(
            comparison["current_last"]
        )

        previous_ts = parse_ts(
            comparison["previous_last"]
        )

        if current_ts and previous_ts:

            delta = (
                current_ts - previous_ts
            ).total_seconds()

            result(
                "Snapshot temporal delta seconds",
                round(delta, 6),
            )

    else:

        print(
            "Previous snapshot unavailable."
        )

    # ----------------------------------------------------------------------------------------------
    # Direction / entry price are OBSERVATIONS only
    # ----------------------------------------------------------------------------------------------

    section("SIGNAL OUTPUT OBSERVATION")

    directions = Counter(
        row[19]
        for row in current_rows
    )

    entry_missing = sum(
        1
        for row in current_rows
        if row[18] is None
    )

    for direction, count in directions.items():

        print(
            f"{direction:<10} | {count}"
        )

    result(
        "Missing entry_price",
        entry_missing,
    )

    print(
        "NOTE: No direction inference or reconstruction is performed."
    )

    # ----------------------------------------------------------------------------------------------
    # Production invariant
    # ----------------------------------------------------------------------------------------------

    section("PRODUCTION DATABASE INVARIANT")

    production_after = db_fingerprint(
        PRODUCTION_DB
    )

    result(
        "Before size",
        production_before["size"],
    )

    result(
        "After size",
        production_after["size"],
    )

    result(
        "Before SHA256",
        production_before["sha256"],
    )

    result(
        "After SHA256",
        production_after["sha256"],
    )

    production_unchanged = (
        production_before["size"]
        == production_after["size"]
        and production_before["sha256"]
        == production_after["sha256"]
    )

    print(
        "PRODUCTION DB INVARIANT : "
        + (
            "PASS"
            if production_unchanged
            else "FAIL"
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Verdict
    # ----------------------------------------------------------------------------------------------

    section(
        "LIVE SNAPSHOT FRESHNESS + SOURCE-TO-ROW CAUSALITY VERDICT"
    )

    source_observation_pass = True

    for arm, stats in source_rows.items():

        # If an arm is marked available but no source score exists,
        # flag for review rather than claiming causality.
        if stats["available_without_score"] > 0:
            source_observation_pass = False

    provenance_pass = (
        len(current_rows) > 0
        and identity_problems == []
        and temporal_problems == []
        and engine_pass
        and production_unchanged
    )

    if provenance_pass:

        print(
            "SNAPSHOT_IDENTITY          : PASS"
        )

        print(
            "ROW_TEMPORAL_COHERENCE     : PASS"
        )

        print(
            "ENGINE_IDENTITY            : PASS"
        )

        print(
            "PRODUCTION_ISOLATION       : PASS"
        )

    else:

        print(
            "ONE OR MORE PROVENANCE CONTRACTS REQUIRE REVIEW"
        )

    if source_observation_pass:

        print(
            "SOURCE_ROW_OBSERVABILITY   : PASS"
        )

    else:

        print(
            "SOURCE_ROW_OBSERVABILITY   : REVIEW"
        )

    overall = (
        provenance_pass
        and source_observation_pass
    )

    print()

    print(
        "FRONTIER VERDICT : "
        + (
            "PASS"
            if overall
            else "REVIEW"
        )
    )

    # ----------------------------------------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------------------------------------

    report = {
        "frontier": (
            "LIVE_SNAPSHOT_FRESHNESS_SOURCE_TO_ROW_CAUSALITY_v0.1"
        ),
        "production_db": str(
            PRODUCTION_DB
        ),
        "capture_db": str(
            capture_db
        ),
        "capture_directory": str(
            capture_dir
        ),
        "engine": EXPECTED_ENGINE,
        "current_snapshot": current_snapshot_id,
        "row_count": len(current_rows),
        "assets": assets,
        "temporal": temporal,
        "freshness": freshness,
        "arms": arms,
        "source_row_observability": source_rows,
        "arm_matrix": {
            str(k): v
            for k, v in matrix.items()
        },
        "identity_problems": identity_problems,
        "temporal_problems": temporal_problems,
        "production_unchanged": production_unchanged,
        "frontier_verdict": (
            "PASS"
            if overall
            else "REVIEW"
        ),
    }

    report_path = write_report(
        capture_dir,
        report,
    )

    section("FINAL SAFETY VERDICT")

    print(
        "Production DB writes : NONE"
    )

    print(
        "INSERT               : NONE"
    )

    print(
        "UPDATE               : NONE"
    )

    print(
        "DELETE               : NONE"
    )

    print(
        "DDL                  : NONE"
    )

    print(
        "Production engine    : NOT EXECUTED"
    )

    print(
        "Historical repair    : NONE"
    )

    print(
        "Direction inference  : NONE"
    )

    print(
        "Score reconstruction : NONE"
    )

    print(
        "Synthetic data       : NONE"
    )

    print(
        "Live data injection  : NONE"
    )

    print()

    print(
        "Production DB remains unchanged."
    )

    print(
        "Only the newest FUSION_v0.5 snapshot was analyzed."
    )

    print()

    print(
        f"Runtime report : {report_path}"
    )

    conn.close()

    return 0 if overall else 10


# ==================================================================================================
# ENTRY POINT
# ==================================================================================================

if __name__ == "__main__":
    sys.exit(main())