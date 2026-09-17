# ==============================================================================================
# OUTCOME_v0.3 FUSION DIRECTION HISTORICAL NULL CAUSALITY FORENSIC v0.1
# ==============================================================================================
#
# PURPOSE
# -------
# Targeted forensic stage after successful isolated actual-runtime writer capture.
#
# Objective:
#   Determine whether historical NULL-direction fusion_signals rows are consistent with
#   an older writer/source generation whose INSERT boundary omitted direction or explicitly
#   supplied NULL.
#
# IMPORTANT SAFETY RULES
# ----------------------
# READ ONLY.
# Production DB is never modified.
# No production engine execution.
# No direction reconstruction.
# No score-based inference.
# No eligibility repair.
# No synthetic data.
#
# This stage inspects:
#   1. Existing production DB identities.
#   2. Current production source.
#   3. Local backup archives containing historical source snapshots.
#   4. Source-level direction/INSERT provenance.
#
# It DOES NOT modify any production artifact.
#
# ==============================================================================================

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional


# ==============================================================================================
# CONFIGURATION
# ==============================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"
WRITER_NAME = "fusion_engine.py"
BACKUP_DIR = PROJECT_ROOT / "_backups"

TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"


# ==============================================================================================
# DISPLAY
# ==============================================================================================

WIDTH = 110


def header(title: str) -> None:
    print()
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def subheader(title: str) -> None:
    print()
    print("-" * WIDTH)
    print(title)
    print("-" * WIDTH)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


# ==============================================================================================
# PRODUCTION DB — READ ONLY
# ==============================================================================================

def open_production_readonly() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Production DB not found: {DB_PATH}")

    uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row
    return conn


# ==============================================================================================
# DATABASE SNAPSHOT
# ==============================================================================================

def database_baseline(conn: sqlite3.Connection) -> dict:
    exists = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name IN ('fusion_signals', 'signal_outcomes')
        ORDER BY name
        """
    ).fetchall()

    tables = {row["name"] for row in exists}

    if TARGET_TABLE not in tables:
        raise RuntimeError("fusion_signals table not found.")

    columns = [
        row["name"]
        for row in conn.execute(
            f"PRAGMA table_info({TARGET_TABLE})"
        ).fetchall()
    ]

    rows = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT id) AS distinct_ids,
            SUM(CASE WHEN direction IS NULL THEN 1 ELSE 0 END) AS null_direction,
            SUM(CASE WHEN direction IS NOT NULL THEN 1 ELSE 0 END) AS valid_direction
        FROM fusion_signals
        """
    ).fetchone()

    distribution = conn.execute(
        """
        SELECT
            direction,
            COUNT(*) AS count
        FROM fusion_signals
        GROUP BY direction
        ORDER BY
            CASE
                WHEN direction IS NULL THEN 0
                ELSE 1
            END,
            direction
        """
    ).fetchall()

    return {
        "tables": tables,
        "columns": columns,
        "total": int(rows["total"] or 0),
        "distinct_ids": int(rows["distinct_ids"] or 0),
        "null_direction": int(rows["null_direction"] or 0),
        "valid_direction": int(rows["valid_direction"] or 0),
        "distribution": distribution,
    }


# ==============================================================================================
# HISTORICAL NULL ROWS
# ==============================================================================================

def load_null_rows(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            confidence,
            regime,
            data_quality,
            engine_version,
            snapshot_id,
            signal_strength,
            entry_price,
            direction
        FROM fusion_signals
        WHERE direction IS NULL
        ORDER BY timestamp, id
        """
    ).fetchall()


# ==============================================================================================
# NULL ROW GROUPING
# ==============================================================================================

def print_null_grouping(rows) -> None:

    subheader("HISTORICAL NULL-DIRECTION GROUPING")

    by_engine = {}

    for row in rows:
        engine = row["engine_version"]
        by_engine[engine] = by_engine.get(engine, 0) + 1

    print("By engine_version:")

    for engine, count in sorted(by_engine.items()):
        print(f"  {str(engine):35} | {count}")

    by_snapshot = {}

    for row in rows:
        snapshot = row["snapshot_id"]
        by_snapshot[snapshot] = by_snapshot.get(snapshot, 0) + 1

    print()
    print("By snapshot_id:")

    for snapshot, count in sorted(
        by_snapshot.items(),
        key=lambda x: str(x[0]),
    ):
        print(f"  {str(snapshot):45} | {count}")


# ==============================================================================================
# HISTORICAL ROW SIGNATURES
# ==============================================================================================

def historical_signature(row) -> dict:
    return {
        "timestamp": row["timestamp"],
        "asset": row["asset"],
        "fused_score": row["fused_score"],
        "engine_version": row["engine_version"],
        "snapshot_id": row["snapshot_id"],
        "confidence": row["confidence"],
        "regime": row["regime"],
        "data_quality": row["data_quality"],
        "signal_strength": row["signal_strength"],
        "entry_price": row["entry_price"],
    }


# ==============================================================================================
# SOURCE ANALYSIS
# ==============================================================================================

def normalize_source(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def source_lines(text: str):
    return normalize_source(text).splitlines()


def find_function_boundaries(lines, function_name: str):
    pattern = re.compile(
        rf"^\s*def\s+{re.escape(function_name)}\s*\("
    )

    start = None

    for i, line in enumerate(lines):
        if pattern.search(line):
            start = i
            break

    if start is None:
        return None, None

    base_indent = len(lines[start]) - len(lines[start].lstrip())

    end = len(lines)

    for i in range(start + 1, len(lines)):
        line = lines[i]

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())

        if indent <= base_indent and re.match(
            r"^\s*(def|class)\s+",
            line,
        ):
            end = i
            break

    return start, end


def source_direction_analysis(text: str) -> dict:
    lines = source_lines(text)

    result = {
        "direction_variable_assignments": [],
        "determine_direction_definitions": [],
        "determine_direction_calls": [],
        "fusion_inserts": [],
        "direction_in_insert": False,
        "direction_bound": False,
        "direction_literal_null": False,
    }

    # ------------------------------------------------------------------
    # determine_direction
    # ------------------------------------------------------------------

    for i, line in enumerate(lines, start=1):

        if re.search(
            r"\bdef\s+determine_direction\s*\(",
            line,
        ):
            result["determine_direction_definitions"].append(i)

        if re.search(
            r"\bdetermine_direction\s*\(",
            line,
        ) and not re.search(
            r"\bdef\s+determine_direction\s*\(",
            line,
        ):
            result["determine_direction_calls"].append(i)

    # ------------------------------------------------------------------
    # direction assignments
    # ------------------------------------------------------------------

    assignment_pattern = re.compile(
        r"\bdirection\s*="
    )

    for i, line in enumerate(lines, start=1):
        if assignment_pattern.search(line):
            result["direction_variable_assignments"].append(i)

    # ------------------------------------------------------------------
    # INSERT blocks
    # ------------------------------------------------------------------

    text_lower = text.lower()

    for match in re.finditer(
        r"insert\s+into\s+fusion_signals",
        text_lower,
    ):
        line_no = text_lower[:match.start()].count("\n") + 1
        result["fusion_inserts"].append(line_no)

    # ------------------------------------------------------------------
    # direction in INSERT region
    # ------------------------------------------------------------------

    for insert_line in result["fusion_inserts"]:

        start = max(0, insert_line - 1)
        end = min(len(lines), insert_line + 100)

        block = "\n".join(lines[start:end])

        if re.search(
            r"\bdirection\b",
            block,
            re.IGNORECASE,
        ):
            result["direction_in_insert"] = True

        # Search likely parameter tuple binding.
        if re.search(
            r"\bdirection\b",
            block,
            re.IGNORECASE,
        ):
            result["direction_bound"] = True

    # ------------------------------------------------------------------
    # Explicit NULL use
    # ------------------------------------------------------------------

    null_patterns = [
        r"\bdirection\s*=\s*None\b",
        r"\bdirection\s*=\s*NULL\b",
        r"\bNULL\s*,\s*direction\b",
        r"\bdirection\s*,\s*NULL\b",
    ]

    for pattern in null_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            result["direction_literal_null"] = True
            break

    return result


# ==============================================================================================
# BACKUP SOURCE DISCOVERY
# ==============================================================================================

def discover_backup_archives():
    if not BACKUP_DIR.exists():
        return []

    return sorted(
        BACKUP_DIR.glob("*.zip"),
        key=lambda p: p.stat().st_mtime,
    )


def find_writer_in_zip(zip_path: Path) -> Optional[str]:

    try:
        with zipfile.ZipFile(zip_path, "r") as z:

            candidates = []

            for name in z.namelist():
                normalized = name.replace("\\", "/")

                if normalized.endswith(
                    f"/{WRITER_NAME}"
                ) or normalized == WRITER_NAME:
                    candidates.append(name)

            if not candidates:
                return None

            # Prefer the shortest / most direct path.
            candidates.sort(
                key=lambda x: (
                    x.count("/"),
                    len(x),
                )
            )

            data = z.read(candidates[0])

            return data.decode(
                "utf-8",
                errors="replace",
            )

    except Exception:
        return None


# ==============================================================================================
# SOURCE GENERATION CLASSIFICATION
# ==============================================================================================

def classify_source_generation(
    analysis: dict,
) -> str:

    if analysis["direction_literal_null"]:
        return "EXPLICIT_DIRECTION_NULL"

    if (
        analysis["direction_in_insert"]
        and analysis["direction_bound"]
        and analysis["direction_variable_assignments"]
    ):
        return "DIRECTION_WRITER_PRESENT"

    if analysis["fusion_inserts"]:
        return "FUSION_WRITER_WITHOUT_PROVEN_DIRECTION_BINDING"

    return "NO_DIRECT_FUSION_WRITER_DETECTED"


# ==============================================================================================
# BACKUP FORENSIC
# ==============================================================================================

def analyze_backups():

    header("HISTORICAL SOURCE SNAPSHOT FORENSIC")

    archives = discover_backup_archives()

    print(f"Backup archives discovered : {len(archives)}")

    if not archives:
        print("No backup ZIP archives available.")
        return []

    results = []

    for archive in archives:

        source = find_writer_in_zip(archive)

        if source is None:
            continue

        fingerprint = sha256_bytes(
            source.encode("utf-8", errors="replace")
        )

        analysis = source_direction_analysis(source)

        classification = classify_source_generation(
            analysis
        )

        results.append(
            {
                "archive": archive,
                "fingerprint": fingerprint,
                "classification": classification,
                "analysis": analysis,
            }
        )

    if not results:
        print("No historical fusion_engine.py source snapshot found.")
        return []

    subheader("HISTORICAL WRITER SOURCE GENERATIONS")

    for index, item in enumerate(results, start=1):

        print(
            f"[{index}] {item['archive'].name}"
        )

        print(
            f"    SHA256         : {item['fingerprint']}"
        )

        print(
            f"    classification : {item['classification']}"
        )

        a = item["analysis"]

        print(
            f"    determine_direction definitions : "
            f"{len(a['determine_direction_definitions'])}"
        )

        print(
            f"    determine_direction calls       : "
            f"{len(a['determine_direction_calls'])}"
        )

        print(
            f"    direction assignments           : "
            f"{len(a['direction_variable_assignments'])}"
        )

        print(
            f"    fusion INSERTs                  : "
            f"{len(a['fusion_inserts'])}"
        )

        print(
            f"    direction in INSERT             : "
            f"{a['direction_in_insert']}"
        )

        print(
            f"    direction binding               : "
            f"{a['direction_bound']}"
        )

        print(
            f"    explicit NULL direction         : "
            f"{a['direction_literal_null']}"
        )

        print()

    return results


# ==============================================================================================
# CURRENT SOURCE
# ==============================================================================================

def analyze_current_source():

    header("CURRENT PRODUCTION SOURCE PROVENANCE")

    if not Path(PROJECT_ROOT / WRITER_NAME).exists():
        raise FileNotFoundError(
            f"Writer source not found: "
            f"{PROJECT_ROOT / WRITER_NAME}"
        )

    writer_path = PROJECT_ROOT / WRITER_NAME

    source = writer_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    fingerprint = sha256_file(writer_path)

    analysis = source_direction_analysis(source)

    classification = classify_source_generation(
        analysis
    )

    print(
        f"Source             : {writer_path}"
    )

    print(
        f"SHA256             : {fingerprint}"
    )

    print(
        f"Classification      : {classification}"
    )

    print(
        f"determine_direction : "
        f"{len(analysis['determine_direction_definitions'])}"
    )

    print(
        f"direction assigns   : "
        f"{len(analysis['direction_variable_assignments'])}"
    )

    print(
        f"fusion INSERTs      : "
        f"{len(analysis['fusion_inserts'])}"
    )

    print(
        f"direction in INSERT : "
        f"{analysis['direction_in_insert']}"
    )

    print(
        f"direction binding   : "
        f"{analysis['direction_bound']}"
    )

    return {
        "path": writer_path,
        "source": source,
        "fingerprint": fingerprint,
        "analysis": analysis,
        "classification": classification,
    }


# ==============================================================================================
# HISTORICAL ENGINE VERSION CORRELATION
# ==============================================================================================

def correlate_null_rows(conn):

    header("HISTORICAL NULL-DIRECTION ENGINE CORRELATION")

    rows = load_null_rows(conn)

    print(
        f"NULL direction rows : {len(rows)}"
    )

    grouped = {}

    for row in rows:

        key = (
            row["engine_version"],
            row["snapshot_id"],
        )

        grouped[key] = grouped.get(key, 0) + 1

    for key, count in sorted(
        grouped.items(),
        key=lambda x: (
            str(x[0][0]),
            str(x[0][1]),
        ),
    ):

        engine, snapshot = key

        print(
            f"{str(engine):25} | "
            f"snapshot={str(snapshot):45} | "
            f"NULL={count}"
        )

    return rows


# ==============================================================================================
# CURRENT VALID ROW REFERENCE
# ==============================================================================================

def current_valid_rows(conn):

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            engine_version,
            snapshot_id,
            direction
        FROM fusion_signals
        WHERE direction IS NOT NULL
        ORDER BY timestamp, id
        """
    ).fetchall()

    return rows


def print_current_valid_reference(rows):

    header("CURRENT VALID DIRECTION REFERENCE")

    print(
        f"Valid direction rows : {len(rows)}"
    )

    by_engine = {}

    for row in rows:
        engine = row["engine_version"]

        if engine not in by_engine:
            by_engine[engine] = {
                "rows": 0,
                "directions": {},
            }

        by_engine[engine]["rows"] += 1

        direction = row["direction"]

        by_engine[engine]["directions"][direction] = (
            by_engine[engine]["directions"].get(direction, 0) + 1
        )

    for engine, data in sorted(by_engine.items()):

        print(
            f"{engine:25} | rows={data['rows']}"
        )

        for direction, count in sorted(
            data["directions"].items()
        ):
            print(
                f"    {direction:10} | {count}"
            )


# ==============================================================================================
# CAUSALITY TEST
# ==============================================================================================

def causality_assessment(
    null_rows,
    backup_results,
    current_source,
):

    header("HISTORICAL NULL-DIRECTION CAUSALITY ASSESSMENT")

    engine_versions = sorted(
        {
            str(row["engine_version"])
            for row in null_rows
        }
    )

    print(
        "Historical NULL engine versions:"
    )

    for engine in engine_versions:
        print(f"  - {engine}")

    print()

    explicit_null_sources = [
        x
        for x in backup_results
        if x["classification"] == "EXPLICIT_DIRECTION_NULL"
    ]

    writerless_sources = [
        x
        for x in backup_results
        if x["classification"]
        in {
            "NO_DIRECT_FUSION_WRITER_DETECTED",
            "FUSION_WRITER_WITHOUT_PROVEN_DIRECTION_BINDING",
        }
    ]

    direction_writer_sources = [
        x
        for x in backup_results
        if x["classification"]
        == "DIRECTION_WRITER_PRESENT"
    ]

    print(
        f"Historical source snapshots        : "
        f"{len(backup_results)}"
    )

    print(
        f"Snapshots with explicit NULL        : "
        f"{len(explicit_null_sources)}"
    )

    print(
        f"Snapshots without direction binding : "
        f"{len(writerless_sources)}"
    )

    print(
        f"Snapshots with direction writer     : "
        f"{len(direction_writer_sources)}"
    )

    print()

    current_classification = current_source[
        "classification"
    ]

    print(
        f"Current source classification       : "
        f"{current_classification}"
    )

    # ------------------------------------------------------------------
    # Conservative conclusion
    # ------------------------------------------------------------------

    if explicit_null_sources:
        verdict = (
            "HISTORICAL NULL WRITING MECHANISM IDENTIFIED "
            "IN BACKUP SOURCE SNAPSHOT"
        )

    elif writerless_sources:
        verdict = (
            "HISTORICAL WRITER GENERATION WITHOUT VERIFIED "
            "DIRECTION BINDING IDENTIFIED"
        )

    else:
        verdict = (
            "HISTORICAL NULL CAUSALITY NOT PROVEN "
            "FROM AVAILABLE SOURCE SNAPSHOTS"
        )

    print()
    print(
        "CAUSALITY VERDICT:"
    )

    print(
        f"    {verdict}"
    )

    return verdict


# ==============================================================================================
# DATABASE INVARIANT
# ==============================================================================================

def database_after_check(
    before: dict,
    conn: sqlite3.Connection,
):

    after = database_baseline(conn)

    invariant = (
        before["total"] == after["total"]
        and before["distinct_ids"] == after["distinct_ids"]
        and before["null_direction"] == after["null_direction"]
        and before["valid_direction"] == after["valid_direction"]
    )

    header("POST-FORENSIC DATABASE INVARIANT")

    print(
        f"Before total rows       : {before['total']}"
    )

    print(
        f"After total rows        : {after['total']}"
    )

    print(
        f"Before NULL direction   : "
        f"{before['null_direction']}"
    )

    print(
        f"After NULL direction    : "
        f"{after['null_direction']}"
    )

    print()

    print(
        "DATABASE POPULATION INVARIANT : "
        + ("PASS" if invariant else "FAIL")
    )

    if not invariant:
        raise RuntimeError(
            "Production database invariant changed."
        )

    return invariant


# ==============================================================================================
# MAIN
# ==============================================================================================

def main():

    header(
        "OUTCOME_v0.3 FUSION DIRECTION HISTORICAL "
        "NULL CAUSALITY FORENSIC v0.1"
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
        "Mode               : READ ONLY / SOURCE PROVENANCE"
    )

    print(
        "Production DB      : NEVER MODIFIED"
    )

    print(
        "Production writer  : NEVER EXECUTED"
    )

    print(
        "Direction repair   : FORBIDDEN"
    )

    print(
        "Synthetic data     : FORBIDDEN"
    )

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    header("FORENSIC SCRIPT SAFETY CHECK")

    print(
        "Production DB writes : NONE"
    )

    print(
        "Production engine execution : NO"
    )

    print(
        "Production source writes : NO"
    )

    print(
        "Historical repair : NO"
    )

    print(
        "Direction reconstruction : NO"
    )

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------

    header("ENVIRONMENT CHECK")

    print(
        f"Python version : {sys.version}"
    )

    print(
        f"Project root  : {PROJECT_ROOT}"
    )

    print(
        f"Database      : {DB_PATH}"
    )

    print(
        f"Writer source : {PROJECT_ROOT / WRITER_NAME}"
    )

    # ------------------------------------------------------------------
    # Production DB baseline
    # ------------------------------------------------------------------

    conn = open_production_readonly()

    try:

        before = database_baseline(conn)

        header("PRODUCTION DATABASE BASELINE")

        print(
            f"fusion_signals rows : "
            f"{before['total']}"
        )

        print(
            f"distinct IDs        : "
            f"{before['distinct_ids']}"
        )

        print(
            f"valid direction     : "
            f"{before['valid_direction']}"
        )

        print(
            f"NULL direction      : "
            f"{before['null_direction']}"
        )

        print()
        print("Direction distribution:")

        for row in before["distribution"]:
            print(
                f"  {str(row['direction']):10} | "
                f"{row['count']}"
            )

        # --------------------------------------------------------------
        # Null rows
        # --------------------------------------------------------------

        null_rows = correlate_null_rows(conn)

        print_null_grouping(null_rows)

        # --------------------------------------------------------------
        # Current valid reference
        # --------------------------------------------------------------

        valid_rows = current_valid_rows(conn)

        print_current_valid_reference(
            valid_rows
        )

        # --------------------------------------------------------------
        # Current source
        # --------------------------------------------------------------

        current_source = analyze_current_source()

        # --------------------------------------------------------------
        # Backup source history
        # --------------------------------------------------------------

        backup_results = analyze_backups()

        # --------------------------------------------------------------
        # Causality
        # --------------------------------------------------------------

        verdict = causality_assessment(
            null_rows,
            backup_results,
            current_source,
        )

        # --------------------------------------------------------------
        # Database invariant
        # --------------------------------------------------------------

        database_after_check(
            before,
            conn,
        )

        # --------------------------------------------------------------
        # Final verdict
        # --------------------------------------------------------------

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
            "Direction reconstructed  : NO"
        )

        print(
            "Direction repaired       : NO"
        )

        print(
            "Eligibility repaired     : NO"
        )

        print(
            "Synthetic data            : NOT USED"
        )

        print(
            "Interpolation             : NOT USED"
        )

        print(
            "Forward fill              : NOT USED"
        )

        print(
            "Back fill                 : NOT USED"
        )

        # --------------------------------------------------------------
        # Conclusion
        # --------------------------------------------------------------

        header("FORENSIC CONCLUSION")

        print(
            "CURRENT RUNTIME BOUNDARY:"
        )

        print(
            "    Previously verified in isolated actual-runtime stage."
        )

        print()

        print(
            "HISTORICAL NULL CAUSALITY:"
        )

        print(
            f"    {verdict}"
        )

        print()

        if (
            "IDENTIFIED" in verdict
        ):
            print(
                "IMPORTANT:"
            )

            print(
                "Source-level historical evidence exists, but "
                "row-level causality remains tied to the matching "
                "historical source generation."
            )

        else:
            print(
                "Historical NULL causality remains unproven."
            )

        print()

        print(
            "DIRECTION REPAIR:"
        )

        print(
            "    BLOCKED"
        )

        print(
            "ELIGIBILITY REPAIR:"
        )

        print(
            "    BLOCKED"
        )

        print(
            "SCORE-BASED HISTORICAL DIRECTION INFERENCE:"
        )

        print(
            "    FORBIDDEN"
        )

        print()

        print(
            "FORENSIC COMPLETE."
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()