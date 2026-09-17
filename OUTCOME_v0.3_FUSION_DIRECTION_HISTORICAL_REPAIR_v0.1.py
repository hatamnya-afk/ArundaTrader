# -*- coding: utf-8 -*-

"""
====================================================================================================
OUTCOME_v0.3 FUSION DIRECTION HISTORICAL REPAIR v0.2
====================================================================================================

Purpose:
    Repair ONLY historical NULL direction rows in fusion_signals.

Scope:
    FUSION_v0.2
    FUSION_v0.3
    FUSION_v0.4

Excluded:
    FUSION_v0.5

Rules:
    - No synthetic data
    - No interpolation
    - No forward fill
    - No back fill
    - No score reconstruction
    - No production fusion_engine.main() execution
    - Direction is generated ONLY by the existing production
      determine_direction(score) function.
    - Only rows with direction IS NULL are eligible.
    - Database is backed up before mutation.
    - Transactional UPDATE with rollback on invariant failure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import sqlite3
from datetime import datetime, timezone


# ==================================================================================================
# CONFIG
# ==================================================================================================

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
DB_PATH = os.path.join(PROJECT_ROOT, "arunda.db")
WRITER_PATH = os.path.join(PROJECT_ROOT, "fusion_engine.py")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "_backups")

TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

REPAIR_ENGINES = (
    "FUSION_v0.2",
    "FUSION_v0.3",
    "FUSION_v0.4",
)

EXCLUDED_ENGINES = (
    "FUSION_v0.5",
)


# ==================================================================================================
# OUTPUT
# ==================================================================================================

SEP = "=" * 100
SUB = "-" * 100


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def print_header(title):
    print(SEP)
    print(title)
    print(SEP)


# ==================================================================================================
# LOAD PRODUCTION determine_direction
# ==================================================================================================

def load_determine_direction():
    """
    Load determine_direction from production fusion_engine.py
    WITHOUT executing fusion_engine.main().
    """

    if not os.path.exists(WRITER_PATH):
        raise FileNotFoundError(
            f"Writer source not found: {WRITER_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "arunda_fusion_engine_repair_loader",
        WRITER_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not create module specification for fusion_engine.py"
        )

    module = importlib.util.module_from_spec(spec)

    # Import only.
    # fusion_engine.main() is NOT called.
    spec.loader.exec_module(module)

    fn = getattr(module, "determine_direction", None)

    if not callable(fn):
        raise RuntimeError(
            "determine_direction() was not found in fusion_engine.py"
        )

    return fn


# ==================================================================================================
# DATABASE
# ==================================================================================================

def connect_production():
    """
    Normal production DB connection.

    Mutation is performed only after all preflight checks pass.
    """

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


# ==================================================================================================
# SCHEMA
# ==================================================================================================

def verify_schema(conn):
    rows = conn.execute(
        f"PRAGMA table_info({TARGET_TABLE})"
    ).fetchall()

    columns = {row["name"] for row in rows}

    required = {
        "id",
        "timestamp",
        "asset",
        "fused_score",
        "engine_version",
        "direction",
    }

    missing = required - columns

    if missing:
        raise RuntimeError(
            f"Required columns missing from {TARGET_TABLE}: "
            f"{sorted(missing)}"
        )


# ==================================================================================================
# LOAD TARGET ROWS
# ==================================================================================================

def load_target_rows(conn):
    """
    Load ONLY eligible historical NULL-direction rows.

    IMPORTANT:
        This function requires conn.
    """

    placeholders = ",".join("?" for _ in REPAIR_ENGINES)

    sql = f"""
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            confidence,
            regime,
            engine_version,
            snapshot_id,
            direction
        FROM {TARGET_TABLE}
        WHERE direction IS NULL
          AND engine_version IN ({placeholders})
        ORDER BY timestamp ASC, id ASC
    """

    return conn.execute(
        sql,
        REPAIR_ENGINES,
    ).fetchall()


# ==================================================================================================
# BASELINE
# ==================================================================================================

def get_baseline(conn):
    total = conn.execute(
        f"SELECT COUNT(*) FROM {TARGET_TABLE}"
    ).fetchone()[0]

    null_count = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {TARGET_TABLE}
        WHERE direction IS NULL
        """
    ).fetchone()[0]

    valid_count = total - null_count

    return {
        "total": total,
        "null": null_count,
        "valid": valid_count,
    }


def get_scope_counts(conn):
    result = {}

    for engine in REPAIR_ENGINES:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN direction IS NULL THEN 1
                        ELSE 0
                    END
                ) AS null_count
            FROM {TARGET_TABLE}
            WHERE engine_version = ?
            """,
            (engine,),
        ).fetchone()

        result[engine] = {
            "total": row["total"] or 0,
            "null": row["null_count"] or 0,
        }

    return result


# ==================================================================================================
# BACKUP
# ==================================================================================================

def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = now_utc()

    backup_path = os.path.join(
        BACKUP_DIR,
        f"arunda_pre_fusion_direction_repair_{timestamp}.db",
    )

    # SQLite-safe backup through sqlite backup API.
    source = sqlite3.connect(DB_PATH)

    try:
        destination = sqlite3.connect(backup_path)

        try:
            source.backup(destination)
            destination.commit()
        finally:
            destination.close()

    finally:
        source.close()

    if not os.path.exists(backup_path):
        raise RuntimeError(
            "Backup file was not created."
        )

    source_size = os.path.getsize(DB_PATH)
    backup_size = os.path.getsize(backup_path)

    if backup_size <= 0:
        raise RuntimeError(
            "Backup file is empty."
        )

    print()
    print("BACKUP")
    print(SUB)
    print(f"Backup path : {backup_path}")
    print(f"Source size : {source_size:,} bytes")
    print(f"Backup size : {backup_size:,} bytes")

    return backup_path


# ==================================================================================================
# PREPARE REPAIR PLAN
# ==================================================================================================

def prepare_repair_plan(rows, determine_direction):
    """
    Build an explicit repair plan in memory.

    No DB mutation happens here.
    """

    plan = []

    for row in rows:

        row_id = row["id"]
        score = row["fused_score"]
        engine = row["engine_version"]

        if engine not in REPAIR_ENGINES:
            raise RuntimeError(
                f"Unexpected engine in repair set: {engine}"
            )

        if row["direction"] is not None:
            raise RuntimeError(
                f"Row {row_id} is not NULL. "
                "Repair scope violation."
            )

        if score is None:
            raise RuntimeError(
                f"Row {row_id} has NULL fused_score. "
                "Direction cannot be safely generated."
            )

        direction = determine_direction(score)

        if direction not in {"LONG", "SHORT", "FLAT"}:
            raise RuntimeError(
                f"Invalid direction returned for row {row_id}: "
                f"{direction!r}"
            )

        plan.append(
            {
                "id": row_id,
                "timestamp": row["timestamp"],
                "asset": row["asset"],
                "engine_version": engine,
                "fused_score": score,
                "direction": direction,
            }
        )

    return plan


# ==================================================================================================
# PLAN VALIDATION
# ==================================================================================================

def validate_plan(plan, expected_rows):
    if len(plan) != expected_rows:
        raise RuntimeError(
            f"Repair plan size mismatch: "
            f"expected={expected_rows}, actual={len(plan)}"
        )

    ids = [item["id"] for item in plan]

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            "Duplicate IDs detected in repair plan."
        )

    for item in plan:

        if item["engine_version"] not in REPAIR_ENGINES:
            raise RuntimeError(
                f"Repair plan contains excluded engine: "
                f"{item['engine_version']}"
            )

        if item["direction"] not in {
            "LONG",
            "SHORT",
            "FLAT",
        }:
            raise RuntimeError(
                f"Invalid direction: {item['direction']}"
            )


# ==================================================================================================
# DISPLAY PLAN
# ==================================================================================================

def print_plan(plan):
    print()
    print(SEP)
    print("REPAIR PLAN")
    print(SEP)

    print(
        f"{'ID':>4} | "
        f"{'ASSET':<5} | "
        f"{'ENGINE':<12} | "
        f"{'SCORE':>14} | "
        f"{'DIRECTION':<6}"
    )

    print(SUB)

    for item in plan:
        print(
            f"{item['id']:>4} | "
            f"{item['asset']:<5} | "
            f"{item['engine_version']:<12} | "
            f"{item['fused_score']:>14.6f} | "
            f"{item['direction']:<6}"
        )

    print(SUB)


# ==================================================================================================
# APPLY REPAIR
# ==================================================================================================

def apply_repair(conn, plan):
    """
    Perform transactional UPDATE.

    IMPORTANT:
        UPDATE is restricted by:
            id
            direction IS NULL
            engine_version IN repair scope

        This prevents accidental overwrite of valid directions.
    """

    updated = 0

    conn.execute("BEGIN")

    try:

        for item in plan:

            cursor = conn.execute(
                f"""
                UPDATE {TARGET_TABLE}
                SET direction = ?
                WHERE id = ?
                  AND direction IS NULL
                  AND engine_version IN (
                      'FUSION_v0.2',
                      'FUSION_v0.3',
                      'FUSION_v0.4'
                  )
                """,
                (
                    item["direction"],
                    item["id"],
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    f"Unexpected UPDATE rowcount for id="
                    f"{item['id']}: {cursor.rowcount}"
                )

            updated += cursor.rowcount

        if updated != len(plan):
            raise RuntimeError(
                f"Updated rows mismatch: "
                f"expected={len(plan)}, actual={updated}"
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return updated


# ==================================================================================================
# POST-REPAIR VERIFICATION
# ==================================================================================================

def verify_after(conn, baseline, plan):
    after = get_baseline(conn)

    expected_total = baseline["total"]

    if after["total"] != expected_total:
        raise RuntimeError(
            f"TOTAL ROW INVARIANT FAILED: "
            f"before={expected_total}, after={after['total']}"
        )

    expected_null = baseline["null"] - len(plan)

    if after["null"] != expected_null:
        raise RuntimeError(
            f"NULL COUNT INVARIANT FAILED: "
            f"expected={expected_null}, actual={after['null']}"
        )

    expected_valid = baseline["valid"] + len(plan)

    if after["valid"] != expected_valid:
        raise RuntimeError(
            f"VALID COUNT INVARIANT FAILED: "
            f"expected={expected_valid}, actual={after['valid']}"
        )

    # Every repaired ID must now contain exactly the planned direction.
    for item in plan:

        row = conn.execute(
            f"""
            SELECT
                direction,
                engine_version
            FROM {TARGET_TABLE}
            WHERE id = ?
            """,
            (item["id"],),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                f"Repaired row disappeared: id={item['id']}"
            )

        if row["direction"] != item["direction"]:
            raise RuntimeError(
                f"Direction verification failed for id="
                f"{item['id']}: "
                f"expected={item['direction']}, "
                f"actual={row['direction']}"
            )

        if row["engine_version"] not in REPAIR_ENGINES:
            raise RuntimeError(
                f"Repaired row escaped engine scope: "
                f"id={item['id']}"
            )

    # No NULLs may remain in the repair scope.
    remaining = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {TARGET_TABLE}
        WHERE direction IS NULL
          AND engine_version IN (
              'FUSION_v0.2',
              'FUSION_v0.3',
              'FUSION_v0.4'
          )
        """
    ).fetchone()[0]

    if remaining != 0:
        raise RuntimeError(
            f"Repair scope still contains NULL directions: "
            f"{remaining}"
        )

    return after


# ==================================================================================================
# DIRECTION DISTRIBUTION
# ==================================================================================================

def direction_distribution(conn):
    rows = conn.execute(
        f"""
        SELECT
            engine_version,
            direction,
            COUNT(*) AS count
        FROM {TARGET_TABLE}
        WHERE engine_version IN (
            'FUSION_v0.2',
            'FUSION_v0.3',
            'FUSION_v0.4',
            'FUSION_v0.5'
        )
        GROUP BY engine_version, direction
        ORDER BY engine_version, direction
        """
    ).fetchall()

    return rows


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    print_header(
        "OUTCOME_v0.3 FUSION DIRECTION HISTORICAL REPAIR v0.2"
    )

    print(f"Database       : {DB_PATH}")
    print(f"Writer         : {WRITER_PATH}")
    print(f"Target table   : {TARGET_TABLE}")
    print(f"Target column  : {TARGET_COLUMN}")

    print()
    print("Repair scope:")
    for engine in REPAIR_ENGINES:
        print(f"  {engine}")

    print()
    print("Excluded:")
    for engine in EXCLUDED_ENGINES:
        print(f"  {engine}")

    print()
    print("Rules:")
    print("  Production fusion_engine.main() : NEVER EXECUTED")
    print("  Synthetic data                  : FORBIDDEN")
    print("  Interpolation                   : FORBIDDEN")
    print("  Forward fill                    : FORBIDDEN")
    print("  Back fill                       : FORBIDDEN")
    print("  Score reconstruction            : FORBIDDEN")
    print()

    # ----------------------------------------------------------------------------------------------
    # SOURCE
    # ----------------------------------------------------------------------------------------------

    print(SEP)
    print("SOURCE FINGERPRINT")
    print(SEP)

    source_hash = sha256_file(WRITER_PATH)

    print(f"SHA256 : {source_hash}")

    determine_direction = load_determine_direction()

    print()
    print("determine_direction : LOADED")
    print("fusion_engine.main  : NOT EXECUTED")

    # ----------------------------------------------------------------------------------------------
    # DB
    # ----------------------------------------------------------------------------------------------

    conn = connect_production()

    try:

        verify_schema(conn)

        # ------------------------------------------------------------------------------------------
        # BASELINE
        # ------------------------------------------------------------------------------------------

        baseline = get_baseline(conn)

        print()
        print(SEP)
        print("PRODUCTION DATABASE BASELINE")
        print(SEP)

        print(f"Total rows       : {baseline['total']}")
        print(f"Valid direction  : {baseline['valid']}")
        print(f"NULL direction   : {baseline['null']}")

        # ------------------------------------------------------------------------------------------
        # SCOPE
        # ------------------------------------------------------------------------------------------

        scope = get_scope_counts(conn)

        print()
        print(SEP)
        print("REPAIR SCOPE BASELINE")
        print(SEP)

        for engine in REPAIR_ENGINES:
            print(
                f"{engine:<20} | "
                f"rows={scope[engine]['total']:>3} | "
                f"NULL={scope[engine]['null']:>3}"
            )

        # ------------------------------------------------------------------------------------------
        # LOAD
        # ------------------------------------------------------------------------------------------

        rows = load_target_rows(conn)

        print()
        print(SEP)
        print("ELIGIBLE HISTORICAL ROWS")
        print(SEP)

        print(f"Eligible rows : {len(rows)}")

        if not rows:
            print()
            print("No eligible NULL-direction rows found.")
            print("Nothing to repair.")
            return

        # ------------------------------------------------------------------------------------------
        # SAFETY: all expected historical NULL rows should be 20 based on current state.
        # Do not hard-code repair if DB has changed unexpectedly.
        # ------------------------------------------------------------------------------------------

        if len(rows) != baseline["null"]:
            raise RuntimeError(
                "Not all NULL rows belong to the authorized historical "
                "repair scope. Refusing mutation."
            )

        # ------------------------------------------------------------------------------------------
        # PLAN
        # ------------------------------------------------------------------------------------------

        plan = prepare_repair_plan(
            rows,
            determine_direction,
        )

        validate_plan(
            plan,
            len(rows),
        )

        print_plan(plan)

        # ------------------------------------------------------------------------------------------
        # BACKUP
        # ------------------------------------------------------------------------------------------

        backup_path = create_backup()

        # ------------------------------------------------------------------------------------------
        # APPLY
        # ------------------------------------------------------------------------------------------

        print()
        print(SEP)
        print("APPLYING HISTORICAL REPAIR")
        print(SEP)

        updated = apply_repair(
            conn,
            plan,
        )

        print(f"Rows updated : {updated}")

        # ------------------------------------------------------------------------------------------
        # VERIFY
        # ------------------------------------------------------------------------------------------

        print()
        print(SEP)
        print("POST-REPAIR VERIFICATION")
        print(SEP)

        after = verify_after(
            conn,
            baseline,
            plan,
        )

        print(f"Before total       : {baseline['total']}")
        print(f"After total        : {after['total']}")

        print(f"Before NULL        : {baseline['null']}")
        print(f"After NULL         : {after['null']}")

        print(f"Before valid       : {baseline['valid']}")
        print(f"After valid        : {after['valid']}")

        print()
        print("DATABASE POPULATION INVARIANT : PASS")
        print("REPAIR SCOPE INVARIANT         : PASS")
        print("ROW-LEVEL DIRECTION VERIFY     : PASS")

        # ------------------------------------------------------------------------------------------
        # DISTRIBUTION
        # ------------------------------------------------------------------------------------------

        print()
        print(SEP)
        print("DIRECTION DISTRIBUTION AFTER REPAIR")
        print(SEP)

        for row in direction_distribution(conn):

            print(
                f"{row['engine_version']:<20} | "
                f"{str(row['direction']):<6} | "
                f"{row['count']:>3}"
            )

        # ------------------------------------------------------------------------------------------
        # FINAL
        # ------------------------------------------------------------------------------------------

        print()
        print(SEP)
        print("FINAL REPAIR VERDICT")
        print(SEP)

        print("Production fusion_engine.main() : NOT EXECUTED")
        print("Historical direction repair      : COMPLETED")
        print(f"Rows repaired                    : {updated}")
        print(f"Backup                           : {backup_path}")
        print("Synthetic data                   : NOT USED")
        print("Interpolation                    : NOT USED")
        print("Forward fill                     : NOT USED")
        print("Back fill                        : NOT USED")
        print("Score reconstruction             : NOT USED")
        print("Post-repair invariant             : PASS")

        print()
        print(SEP)
        print("HISTORICAL REPAIR COMPLETE")
        print(SEP)

    finally:
        conn.close()


if __name__ == "__main__":
    main()