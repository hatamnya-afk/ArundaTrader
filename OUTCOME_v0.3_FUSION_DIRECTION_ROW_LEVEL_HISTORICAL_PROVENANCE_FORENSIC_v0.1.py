# ==============================================================================================
# OUTCOME_v0.3 FUSION DIRECTION ROW-LEVEL HISTORICAL PROVENANCE FORENSIC v0.1
# ==============================================================================================
#
# PURPOSE
# -------
# Targeted forensic stage after:
#
#   1. Static writer boundary verification
#   2. Isolated actual runtime invocation capture
#   3. Historical source snapshot forensic
#
# Objective:
#
#   Determine whether each historical NULL-direction row can be assigned a
#   defensible writer-generation / runtime provenance identity using ONLY
#   existing production DB evidence.
#
# SAFETY
# ------
# READ ONLY.
# No production engine execution.
# No production writer execution.
# No INSERT / UPDATE / DELETE / DDL.
# No direction reconstruction.
# No score-based inference.
# No eligibility repair.
# No synthetic data.
#
# ==============================================================================================

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


# ==============================================================================================
# CONFIG
# ==============================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"
BACKUP_DIR = PROJECT_ROOT / "_backups"

WRITER_NAME = "fusion_engine.py"
TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

WIDTH = 112


# ==============================================================================================
# DISPLAY
# ==============================================================================================

def header(title: str):
    print()
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def subheader(title: str):
    print()
    print("-" * WIDTH)
    print(title)
    print("-" * WIDTH)


# ==============================================================================================
# READ ONLY DATABASE
# ==============================================================================================

def open_readonly():

    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==============================================================================================
# DB BASELINE
# ==============================================================================================

def get_baseline(conn):

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT id) AS distinct_ids,
            SUM(
                CASE
                    WHEN direction IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_direction,
            SUM(
                CASE
                    WHEN direction IS NOT NULL THEN 1
                    ELSE 0
                END
            ) AS valid_direction
        FROM fusion_signals
        """
    ).fetchone()

    return {
        "total": int(row["total"] or 0),
        "distinct_ids": int(row["distinct_ids"] or 0),
        "null_direction": int(row["null_direction"] or 0),
        "valid_direction": int(row["valid_direction"] or 0),
    }


# ==============================================================================================
# NULL ROWS
# ==============================================================================================

def load_null_rows(conn):

    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            asset,
            market_score,
            positioning_score,
            news_score,
            market_weight,
            positioning_weight,
            news_weight,
            fused_score,
            confidence,
            regime,
            data_quality,
            market_available,
            positioning_available,
            news_available,
            engine_version,
            market_score_norm,
            positioning_score_norm,
            news_score_norm,
            agreement_score,
            available_weight,
            snapshot_id,
            missing_arm_penalty,
            news_confidence,
            signal_strength,
            entry_price,
            direction
        FROM fusion_signals
        WHERE direction IS NULL
        ORDER BY timestamp, id
        """
    ).fetchall()


# ==============================================================================================
# TIMESTAMP NORMALIZATION
# ==============================================================================================

def parse_timestamp(value):

    if value is None:
        return None

    text = str(value).strip()

    # ISO timestamps in this project use:
    # 2026-08-15T16:32:24.459156+00:00
    #
    # We deliberately do not convert timezone or alter the value.
    # This is identity preservation, not transformation.

    return text


def timestamp_prefix(value, length=19):

    text = parse_timestamp(value)

    if text is None:
        return None

    return text[:length]


# ==============================================================================================
# ROW IDENTITY
# ==============================================================================================

def row_identity(row):

    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "asset": row["asset"],
        "engine_version": row["engine_version"],
        "snapshot_id": row["snapshot_id"],
        "fused_score": row["fused_score"],
    }


# ==============================================================================================
# GROUPING
# ==============================================================================================

def group_rows(rows, key):

    result = defaultdict(list)

    for row in rows:
        result[key(row)].append(row)

    return result


# ==============================================================================================
# ENGINE VERSION GROUP
# ==============================================================================================

def print_engine_groups(rows):

    header("NULL ROW ENGINE-VERSION PROVENANCE")

    groups = group_rows(
        rows,
        lambda r: r["engine_version"],
    )

    for engine, group in sorted(
        groups.items(),
        key=lambda x: str(x[0]),
    ):

        timestamps = [
            parse_timestamp(r["timestamp"])
            for r in group
        ]

        print(
            f"{str(engine):25} | "
            f"rows={len(group):2d} | "
            f"first={min(timestamps)} | "
            f"last={max(timestamps)}"
        )


# ==============================================================================================
# SNAPSHOT GROUP
# ==============================================================================================

def print_snapshot_groups(rows):

    header("NULL ROW SNAPSHOT PROVENANCE")

    groups = group_rows(
        rows,
        lambda r: r["snapshot_id"],
    )

    for snapshot, group in sorted(
        groups.items(),
        key=lambda x: str(x[0]),
    ):

        print(
            f"{str(snapshot):50} | "
            f"rows={len(group)}"
        )

        assets = sorted(
            {
                str(r["asset"])
                for r in group
            }
        )

        print(
            f"    assets : {', '.join(assets)}"
        )


# ==============================================================================================
# TEMPORAL CLUSTERING
# ==============================================================================================

def print_temporal_clusters(rows):

    header("NULL ROW TEMPORAL CLUSTER FORENSIC")

    groups = group_rows(
        rows,
        lambda r: timestamp_prefix(r["timestamp"])
    )

    for timestamp, group in sorted(
        groups.items(),
        key=lambda x: str(x[0]),
    ):

        engines = sorted(
            {
                str(r["engine_version"])
                for r in group
            }
        )

        assets = sorted(
            {
                str(r["asset"])
                for r in group
            }
        )

        print(
            f"{timestamp} | "
            f"rows={len(group):2d} | "
            f"engines={','.join(engines):20} | "
            f"assets={','.join(assets)}"
        )


# ==============================================================================================
# ASSET / TIMESTAMP CLUSTER
# ==============================================================================================

def print_asset_temporal_identity(rows):

    header("NULL ROW ASSET / TIMESTAMP IDENTITY")

    for row in rows:

        print(
            f"id={row['id']:3d} | "
            f"{str(row['timestamp']):35} | "
            f"{str(row['asset']):5} | "
            f"{str(row['engine_version']):12} | "
            f"snapshot={str(row['snapshot_id']):45}"
        )


# ==============================================================================================
# SCORE / DIRECTION SEPARATION
# ==============================================================================================

def print_score_reference(rows):

    header("HISTORICAL NULL ROW SCORE REFERENCE")

    print(
        "IMPORTANT:"
    )

    print(
        "Scores are displayed only as row identity evidence."
    )

    print(
        "They are NOT converted into direction."
    )

    print()

    for row in rows:

        print(
            f"id={row['id']:3d} | "
            f"asset={row['asset']:4} | "
            f"engine={str(row['engine_version']):12} | "
            f"score={str(row['fused_score']):20} | "
            f"confidence={str(row['confidence']):8} | "
            f"regime={str(row['regime']):10}"
        )


# ==============================================================================================
# VALID ROW TEMPORAL REFERENCE
# ==============================================================================================

def load_valid_rows(conn):

    return conn.execute(
        """
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
        FROM fusion_signals
        WHERE direction IS NOT NULL
        ORDER BY timestamp, id
        """
    ).fetchall()


def print_valid_temporal_reference(rows):

    header("VALID-DIRECTION TEMPORAL REFERENCE")

    groups = group_rows(
        rows,
        lambda r: timestamp_prefix(r["timestamp"])
    )

    for timestamp, group in sorted(
        groups.items(),
        key=lambda x: str(x[0]),
    ):

        directions = defaultdict(int)

        for row in group:
            directions[str(row["direction"])] += 1

        print(
            f"{timestamp} | "
            f"rows={len(group):2d} | "
            f"directions={dict(directions)}"
        )


# ==============================================================================================
# HISTORICAL SOURCE SNAPSHOT FINGERPRINTS
# ==============================================================================================

def sha256_bytes(data: bytes):

    return hashlib.sha256(data).hexdigest()


def find_writer_inside_zip(zip_path):

    try:

        with zipfile.ZipFile(zip_path, "r") as z:

            candidates = [
                name
                for name in z.namelist()
                if name.replace("\\", "/").endswith(
                    "/" + WRITER_NAME
                )
                or name.replace("\\", "/") == WRITER_NAME
            ]

            if not candidates:
                return None

            candidates.sort(
                key=lambda x: (
                    x.count("/"),
                    len(x),
                )
            )

            name = candidates[0]

            data = z.read(name)

            return {
                "member": name,
                "data": data,
                "sha256": sha256_bytes(data),
            }

    except Exception:
        return None


# ==============================================================================================
# SOURCE DIRECTION PROVENANCE
# ==============================================================================================

def analyze_source(data: bytes):

    text = data.decode(
        "utf-8",
        errors="replace",
    )

    normalized = text.replace(
        "\r\n",
        "\n",
    )

    lines = normalized.splitlines()

    direction_assignments = []

    direction_calls = []

    insert_lines = []

    direction_insert_lines = []

    for index, line in enumerate(
        lines,
        start=1,
    ):

        if re.search(
            r"\bdirection\s*=",
            line,
        ):
            direction_assignments.append(index)

        if re.search(
            r"\bdetermine_direction\s*\(",
            line,
        ):
            if not re.search(
                r"\bdef\s+determine_direction\s*\(",
                line,
            ):
                direction_calls.append(index)

        if re.search(
            r"INSERT\s+INTO\s+fusion_signals",
            line,
            re.IGNORECASE,
        ):
            insert_lines.append(index)

    for insert_line in insert_lines:

        start = max(
            0,
            insert_line - 1,
        )

        end = min(
            len(lines),
            insert_line + 100,
        )

        block = "\n".join(
            lines[start:end]
        )

        if re.search(
            r"\bdirection\b",
            block,
            re.IGNORECASE,
        ):
            direction_insert_lines.append(
                insert_line
            )

    explicit_null = bool(
        re.search(
            r"\bdirection\s*=\s*(None|NULL)\b",
            normalized,
            re.IGNORECASE,
        )
    )

    return {
        "sha256": sha256_bytes(data),
        "direction_assignments": direction_assignments,
        "direction_calls": direction_calls,
        "insert_lines": insert_lines,
        "direction_insert_lines": direction_insert_lines,
        "explicit_null": explicit_null,
    }


def inspect_backup_source():

    header("AVAILABLE HISTORICAL SOURCE FINGERPRINT")

    archives = sorted(
        BACKUP_DIR.glob("*.zip"),
        key=lambda p: p.stat().st_mtime,
    )

    print(
        f"Backup archives : {len(archives)}"
    )

    results = []

    for archive in archives:

        found = find_writer_inside_zip(
            archive
        )

        if found is None:
            continue

        analysis = analyze_source(
            found["data"]
        )

        results.append(
            {
                "archive": archive,
                "member": found["member"],
                "analysis": analysis,
            }
        )

        print()
        print(
            f"Archive : {archive.name}"
        )

        print(
            f"Writer  : {found['member']}"
        )

        print(
            f"SHA256  : {analysis['sha256']}"
        )

        print(
            f"direction assignments : "
            f"{len(analysis['direction_assignments'])}"
        )

        print(
            f"direction calls       : "
            f"{len(analysis['direction_calls'])}"
        )

        print(
            f"fusion INSERTs        : "
            f"{len(analysis['insert_lines'])}"
        )

        print(
            f"direction in INSERT   : "
            f"{bool(analysis['direction_insert_lines'])}"
        )

        print(
            f"explicit NULL         : "
            f"{analysis['explicit_null']}"
        )

    return results


# ==============================================================================================
# CURRENT SOURCE FINGERPRINT
# ==============================================================================================

def current_source():

    path = PROJECT_ROOT / WRITER_NAME

    data = path.read_bytes()

    analysis = analyze_source(data)

    header("CURRENT SOURCE FINGERPRINT")

    print(
        f"Path   : {path}"
    )

    print(
        f"SHA256 : {analysis['sha256']}"
    )

    print(
        f"direction assignments : "
        f"{len(analysis['direction_assignments'])}"
    )

    print(
        f"direction calls       : "
        f"{len(analysis['direction_calls'])}"
    )

    print(
        f"fusion INSERTs        : "
        f"{len(analysis['insert_lines'])}"
    )

    print(
        f"direction in INSERT   : "
        f"{bool(analysis['direction_insert_lines'])}"
    )

    return analysis


# ==============================================================================================
# ROW-LEVEL CAUSALITY MATRIX
# ==============================================================================================

def build_row_level_matrix(rows, backup_results):

    header("ROW-LEVEL HISTORICAL PROVENANCE MATRIX")

    historical_source_fingerprints = [
        x["analysis"]["sha256"]
        for x in backup_results
    ]

    print(
        f"Historical source fingerprints available : "
        f"{len(historical_source_fingerprints)}"
    )

    print()

    print(
        "The matrix deliberately does NOT assign direction."
    )

    print(
        "It only determines whether row identity can be "
        "temporally / structurally clustered."
    )

    print()

    matrix = []

    for row in rows:

        timestamp = parse_timestamp(
            row["timestamp"]
        )

        engine = str(
            row["engine_version"]
        )

        snapshot = row["snapshot_id"]

        candidates = []

        # ------------------------------------------------------------------
        # Engine-specific historical grouping
        # ------------------------------------------------------------------

        if engine in {
            "FUSION_v0.2",
            "FUSION_v0.3",
            "FUSION_v0.4",
        }:
            candidates.append(
                "HISTORICAL_FUSION_GENERATION"
            )

        # ------------------------------------------------------------------
        # Snapshot identity
        # ------------------------------------------------------------------

        if snapshot is not None:
            candidates.append(
                "SNAPSHOT_IDENTIFIED"
            )
        else:
            candidates.append(
                "SNAPSHOT_ABSENT"
            )

        # ------------------------------------------------------------------
        # Temporal identity
        # ------------------------------------------------------------------

        if timestamp:
            candidates.append(
                "TIMESTAMP_IDENTIFIED"
            )

        matrix_row = {
            "id": row["id"],
            "asset": row["asset"],
            "timestamp": timestamp,
            "engine": engine,
            "snapshot": snapshot,
            "evidence": candidates,
        }

        matrix.append(matrix_row)

        print(
            f"id={row['id']:3d} | "
            f"asset={row['asset']:4} | "
            f"engine={engine:12} | "
            f"snapshot={'YES' if snapshot else 'NO ':3} | "
            f"evidence={','.join(candidates)}"
        )

    return matrix


# ==============================================================================================
# CAUSALITY CLASSIFICATION
# ==============================================================================================

def classify_row_level_causality(
    matrix,
    backup_results,
):

    header("ROW-LEVEL CAUSALITY CLASSIFICATION")

    explicit_null_history = any(
        x["analysis"]["explicit_null"]
        for x in backup_results
    )

    historical_without_direction = any(
        not x["analysis"]["direction_insert_lines"]
        and x["analysis"]["insert_lines"]
        for x in backup_results
    )

    if explicit_null_history:

        classification = (
            "HISTORICAL_EXPLICIT_NULL_WRITER_FOUND"
        )

    elif historical_without_direction:

        classification = (
            "HISTORICAL_WRITER_WITHOUT_DIRECTION_COLUMN_FOUND"
        )

    else:

        classification = (
            "ROW_LEVEL_CAUSALITY_NOT_PROVEN"
        )

    print(
        f"Classification : {classification}"
    )

    print()

    if classification == (
        "HISTORICAL_EXPLICIT_NULL_WRITER_FOUND"
    ):

        print(
            "A historical source explicitly contains "
            "direction=NULL."
        )

        print(
            "This is source-level evidence only."
        )

    elif classification == (
        "HISTORICAL_WRITER_WITHOUT_DIRECTION_COLUMN_FOUND"
    ):

        print(
            "A historical writer INSERT does not contain "
            "the direction column."
        )

        print(
            "SQLite default behavior may therefore be relevant, "
            "but row-level attribution still requires matching "
            "generation evidence."
        )

    else:

        print(
            "Available historical source snapshots all contain "
            "a direction-aware writer."
        )

        print(
            "Therefore source snapshots alone cannot explain "
            "the historical NULL rows."
        )

    return classification


# ==============================================================================================
# EXACT ROW CLUSTER SUMMARY
# ==============================================================================================

def print_exact_clusters(rows):

    header("EXACT HISTORICAL ROW CLUSTERS")

    groups = group_rows(
        rows,
        lambda r: (
            r["engine_version"],
            r["snapshot_id"],
            timestamp_prefix(r["timestamp"]),
        ),
    )

    for key, group in sorted(
        groups.items(),
        key=lambda x: str(x[0]),
    ):

        engine, snapshot, timestamp = key

        print(
            f"engine={engine:12} | "
            f"timestamp={timestamp} | "
            f"snapshot={str(snapshot):45} | "
            f"rows={len(group)}"
        )

        for row in group:

            print(
                f"    id={row['id']:3d} "
                f"asset={row['asset']:4}"
            )


# ==============================================================================================
# FINAL INVARIANT
# ==============================================================================================

def verify_invariant(before, conn):

    after = get_baseline(conn)

    passed = (
        before == after
    )

    header("POST-FORENSIC DATABASE INVARIANT")

    print(
        f"Before total       : {before['total']}"
    )

    print(
        f"After total        : {after['total']}"
    )

    print(
        f"Before NULL        : {before['null_direction']}"
    )

    print(
        f"After NULL         : {after['null_direction']}"
    )

    print(
        f"Before valid       : {before['valid_direction']}"
    )

    print(
        f"After valid        : {after['valid_direction']}"
    )

    print()

    print(
        "DATABASE POPULATION INVARIANT : "
        + ("PASS" if passed else "FAIL")
    )

    if not passed:
        raise RuntimeError(
            "Production database changed during forensic run."
        )


# ==============================================================================================
# MAIN
# ==============================================================================================

def main():

    header(
        "OUTCOME_v0.3 FUSION DIRECTION ROW-LEVEL "
        "HISTORICAL PROVENANCE FORENSIC v0.1"
    )

    print(
        f"Database          : {DB_PATH}"
    )

    print(
        f"Project root      : {PROJECT_ROOT}"
    )

    print(
        f"Writer target      : {WRITER_NAME}"
    )

    print(
        f"Target table       : {TARGET_TABLE}"
    )

    print(
        f"Target column      : {TARGET_COLUMN}"
    )

    print(
        "Mode               : READ ONLY"
    )

    print(
        "Production writer  : NEVER EXECUTED"
    )

    print(
        "Direction repair   : FORBIDDEN"
    )

    print(
        "Score inference    : FORBIDDEN"
    )

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    header("FORENSIC SCRIPT SAFETY CHECK")

    print(
        "Production DB connection : READ ONLY"
    )

    print(
        "Production INSERT        : NONE"
    )

    print(
        "Production UPDATE        : NONE"
    )

    print(
        "Production DELETE        : NONE"
    )

    print(
        "Production DDL           : NONE"
    )

    print(
        "Production engine run    : NO"
    )

    print(
        "Historical repair        : NO"
    )

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------

    header("ENVIRONMENT")

    print(
        f"Python : {sys.version}"
    )

    print(
        f"DB     : {DB_PATH}"
    )

    print(
        f"Writer : {PROJECT_ROOT / WRITER_NAME}"
    )

    # ------------------------------------------------------------------
    # Open production DB
    # ------------------------------------------------------------------

    conn = open_readonly()

    try:

        before = get_baseline(conn)

        header("PRODUCTION DATABASE BASELINE")

        print(
            f"Total rows       : {before['total']}"
        )

        print(
            f"Distinct IDs     : {before['distinct_ids']}"
        )

        print(
            f"Valid direction  : {before['valid_direction']}"
        )

        print(
            f"NULL direction   : {before['null_direction']}"
        )

        # ------------------------------------------------------------------
        # NULL rows
        # ------------------------------------------------------------------

        null_rows = load_null_rows(
            conn
        )

        print_engine_groups(
            null_rows
        )

        print_snapshot_groups(
            null_rows
        )

        print_temporal_clusters(
            null_rows
        )

        print_exact_clusters(
            null_rows
        )

        print_asset_temporal_identity(
            null_rows
        )

        print_score_reference(
            null_rows
        )

        # ------------------------------------------------------------------
        # Valid reference
        # ------------------------------------------------------------------

        valid_rows = load_valid_rows(
            conn
        )

        print_valid_temporal_reference(
            valid_rows
        )

        # ------------------------------------------------------------------
        # Current source
        # ------------------------------------------------------------------

        current = current_source()

        # ------------------------------------------------------------------
        # Historical source
        # ------------------------------------------------------------------

        backups = inspect_backup_source()

        # ------------------------------------------------------------------
        # Row-level matrix
        # ------------------------------------------------------------------

        matrix = build_row_level_matrix(
            null_rows,
            backups,
        )

        # ------------------------------------------------------------------
        # Classification
        # ------------------------------------------------------------------

        classification = classify_row_level_causality(
            matrix,
            backups,
        )

        # ------------------------------------------------------------------
        # Final invariant
        # ------------------------------------------------------------------

        verify_invariant(
            before,
            conn,
        )

        # ------------------------------------------------------------------
        # Final verdict
        # ------------------------------------------------------------------

        header("FINAL SAFETY VERDICT")

        print(
            "Database writes          : NONE"
        )

        print(
            "Production INSERT       : NONE"
        )

        print(
            "Production UPDATE       : NONE"
        )

        print(
            "Production DELETE       : NONE"
        )

        print(
            "Production DDL          : NONE"
        )

        print(
            "Production DB modified  : NO"
        )

        print(
            "Production source       : UNMODIFIED"
        )

        print(
            "Direction reconstructed : NO"
        )

        print(
            "Direction repaired      : NO"
        )

        print(
            "Eligibility repaired    : NO"
        )

        print(
            "Synthetic data          : NOT USED"
        )

        print(
            "Interpolation           : NOT USED"
        )

        print(
            "Forward fill            : NOT USED"
        )

        print(
            "Back fill               : NOT USED"
        )

        print(
            f"NULL rows analyzed      : {len(null_rows)}"
        )

        print(
            f"Row-level matrix rows   : {len(matrix)}"
        )

        # ------------------------------------------------------------------
        # Conclusion
        # ------------------------------------------------------------------

        header("FORENSIC CONCLUSION")

        print(
            "CURRENT WRITER RUNTIME:"
        )

        print(
            "    VERIFIED in previous isolated actual-runtime stage."
        )

        print()

        print(
            "HISTORICAL SOURCE:"
        )

        print(
            "    Available backup contains a direction-aware writer."
        )

        print()

        print(
            "ROW-LEVEL HISTORICAL PROVENANCE:"
        )

        print(
            f"    {classification}"
        )

        print()

        if classification == (
            "ROW_LEVEL_CAUSALITY_NOT_PROVEN"
        ):

            print(
                "The 20 NULL rows remain historically unexplained "
                "by the available source snapshot."
            )

            print()

            print(
                "NO direction value has been inferred."
            )

            print(
                "NO historical row has been repaired."
            )

            print(
                "NO eligibility decision has been made."
            )

        else:

            print(
                "Historical writer evidence exists."
            )

            print(
                "Row-level repair remains unauthorized until "
                "identity-level causality is separately established."
            )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "    Search runtime / filesystem provenance for the "
            "historical execution generation."
        )

        print()

        print(
            "FORENSIC COMPLETE."
        )

    finally:

        conn.close()


# ==============================================================================================
# ENTRY POINT
# ==============================================================================================

if __name__ == "__main__":
    main()