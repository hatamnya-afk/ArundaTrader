# ==============================================================================================================
# OUTCOME_v0.3 FUSION DIRECTION HISTORICAL RUNTIME FILESYSTEM PROVENANCE FORENSIC v0.1
# ==============================================================================================================
#
# PURPOSE:
#   Search filesystem/runtime artifacts for historical execution provenance
#   capable of explaining the 20 historical NULL direction rows.
#
# SAFETY:
#   READ ONLY
#   Production DB NEVER modified
#   Production writer NEVER executed
#   No direction reconstruction
#   No score inference
#   No repair
#   No synthetic data
#
# TARGET:
#   Historical fusion_signals NULL direction rows:
#       IDs 1..20
#
# HISTORICAL CLUSTERS:
#   FUSION_v0.2 : 2026-08-15 16:21:07
#   FUSION_v0.3 : 2026-08-15 16:23:44
#   FUSION_v0.3 : 2026-08-15 16:26:26
#   FUSION_v0.3 : 2026-08-15 16:26:35
#   FUSION_v0.4 : 2026-08-15 16:32:24
#
# SEARCH TARGETS:
#   - runtime logs
#   - forensic reports
#   - stdout/stderr captures
#   - execution reports
#   - launcher/batch artifacts
#   - Python command history artifacts
#   - filesystem timestamps
#   - backup/runtime directories
#
# ==============================================================================================================

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
import zipfile
from pathlib import Path
from datetime import datetime, timezone


# ==============================================================================================================
# CONFIGURATION
# ==============================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

REPORT_SELF = Path(__file__).resolve()

# Historical window surrounding the NULL-producing generations.
HISTORICAL_START = datetime(
    2026, 8, 15, 16, 15, 0, tzinfo=timezone.utc
)

HISTORICAL_END = datetime(
    2026, 8, 15, 16, 40, 0, tzinfo=timezone.utc
)

# Exact historical identifiers that are useful for provenance matching.
HISTORICAL_TOKENS = [
    "FUSION_v0.2",
    "FUSION_v0.3",
    "FUSION_v0.4",
    "FUSION-20260815T163224459156+0000",
    "2026-08-15T16:21",
    "2026-08-15T16:23",
    "2026-08-15T16:26",
    "2026-08-15T16:32",
    "fusion_signals",
    "fusion_engine.py",
]

# File types that can reasonably contain execution provenance.
TEXT_EXTENSIONS = {
    ".txt",
    ".log",
    ".out",
    ".err",
    ".json",
    ".jsonl",
    ".csv",
    ".md",
    ".py",
    ".bat",
    ".cmd",
    ".ps1",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".xml",
}

# Directories that are generally relevant to runtime provenance.
INTERESTING_DIR_NAMES = {
    "logs",
    "log",
    "runtime",
    "runs",
    "run",
    "reports",
    "report",
    "outputs",
    "output",
    "_logs",
    "_runtime",
    "_reports",
    "_backups",
}


# ==============================================================================================================
# OUTPUT
# ==============================================================================================================

WIDTH = 112

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


# ==============================================================================================================
# HASH
# ==============================================================================================================

def sha256_file(path: Path):
    h = hashlib.sha256()

    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)

                if not chunk:
                    break

                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return None


# ==============================================================================================================
# READ ONLY DATABASE
# ==============================================================================================================

def open_production_readonly():

    uri = (
        "file:"
        + DB_PATH.resolve().as_posix()
        + "?mode=ro"
    )

    return sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )


# ==============================================================================================================
# DATABASE BASELINE
# ==============================================================================================================

def read_database_baseline():

    conn = open_production_readonly()

    try:

        total = conn.execute(
            f"SELECT COUNT(*) FROM {TARGET_TABLE}"
        ).fetchone()[0]

        null_count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {TARGET_TABLE}
            WHERE {TARGET_COLUMN} IS NULL
            """
        ).fetchone()[0]

        valid_count = total - null_count

        rows = conn.execute(
            f"""
            SELECT
                id,
                timestamp,
                asset,
                engine_version,
                snapshot_id
            FROM {TARGET_TABLE}
            WHERE {TARGET_COLUMN} IS NULL
            ORDER BY id
            """
        ).fetchall()

        return {
            "total": total,
            "null": null_count,
            "valid": valid_count,
            "rows": rows,
        }

    finally:
        conn.close()


# ==============================================================================================================
# PATH CLASSIFICATION
# ==============================================================================================================

def is_interesting_directory(path: Path):

    return any(
        part.lower() in INTERESTING_DIR_NAMES
        for part in path.parts
    )


def is_interesting_file(path: Path):

    name = path.name.lower()

    if path == REPORT_SELF:
        return False

    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True

    keywords = (
        "fusion",
        "runtime",
        "execution",
        "run",
        "output",
        "report",
        "log",
        "history",
        "forensic",
    )

    return any(k in name for k in keywords)


# ==============================================================================================================
# FILESYSTEM ENUMERATION
# ==============================================================================================================

def enumerate_candidate_files():

    candidates = []

    for path in PROJECT_ROOT.rglob("*"):

        try:

            if not path.is_file():
                continue

            if path == REPORT_SELF:
                continue

            if is_interesting_file(path) or is_interesting_directory(path):
                candidates.append(path)

        except (PermissionError, OSError):
            continue

    return candidates


# ==============================================================================================================
# TEXT SEARCH
# ==============================================================================================================

def search_text_file(path: Path):

    try:

        size = path.stat().st_size

        # Avoid reading huge binaries accidentally.
        if size > 25 * 1024 * 1024:
            return []

        data = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    except Exception:
        return []

    matches = []

    lowered = data.lower()

    for token in HISTORICAL_TOKENS:

        token_lower = token.lower()

        if token_lower in lowered:

            # Extract a compact contextual window.
            pos = lowered.find(token_lower)

            start = max(0, pos - 180)
            end = min(len(data), pos + len(token) + 300)

            snippet = (
                data[start:end]
                .replace("\r", " ")
                .replace("\n", " ")
            )

            snippet = re.sub(
                r"\s+",
                " ",
                snippet,
            ).strip()

            matches.append(
                {
                    "token": token,
                    "snippet": snippet,
                }
            )

    return matches


# ==============================================================================================================
# FILESYSTEM TIMESTAMP FORENSIC
# ==============================================================================================================

def timestamp_forensic(path: Path):

    try:

        stat = path.stat()

        modified = datetime.fromtimestamp(
            stat.st_mtime,
            timezone.utc,
        )

        created = datetime.fromtimestamp(
            stat.st_ctime,
            timezone.utc,
        )

        accessed = datetime.fromtimestamp(
            stat.st_atime,
            timezone.utc,
        )

        return {
            "size": stat.st_size,
            "modified": modified,
            "created": created,
            "accessed": accessed,
        }

    except Exception:

        return None


def timestamp_hits(info):

    if not info:
        return False

    for key in ("modified", "created", "accessed"):

        value = info[key]

        if HISTORICAL_START <= value <= HISTORICAL_END:
            return True

    return False


# ==============================================================================================================
# ZIP FORENSIC
# ==============================================================================================================

def inspect_zip(path: Path):

    results = []

    try:

        with zipfile.ZipFile(path, "r") as z:

            for info in z.infolist():

                name_lower = info.filename.lower()

                relevant = (
                    "fusion" in name_lower
                    or "runtime" in name_lower
                    or "log" in name_lower
                    or "report" in name_lower
                    or "execution" in name_lower
                )

                if not relevant:
                    continue

                results.append(
                    {
                        "name": info.filename,
                        "size": info.file_size,
                    }
                )

    except Exception:
        pass

    return results


# ==============================================================================================================
# EXECUTION-LIKE PATTERN ANALYSIS
# ==============================================================================================================

EXECUTION_PATTERNS = [
    r"python(?:\.exe)?\s+.*fusion_engine",
    r"fusion_engine\.py",
    r"FUSION_v0\.[2345]",
    r"ARUNDA FUSION ENGINE",
    r"FUSION ENGINE COMPLETE",
    r"Signals generated",
    r"fusion_signals",
    r"Snapshot ID",
    r"Database:\s*arunda\.db",
]


def classify_runtime_evidence(matches):

    strong = 0
    medium = 0

    for item in matches:

        snippet = item["snippet"]

        for pattern in EXECUTION_PATTERNS:

            if re.search(
                pattern,
                snippet,
                flags=re.IGNORECASE,
            ):

                if (
                    "ARUNDA FUSION ENGINE" in snippet
                    or "FUSION ENGINE COMPLETE" in snippet
                    or "python" in snippet.lower()
                ):
                    strong += 1
                else:
                    medium += 1

    if strong > 0:
        return "STRONG_RUNTIME_ARTIFACT"

    if medium > 0:
        return "RUNTIME_RELATED_ARTIFACT"

    return "TOKEN_ONLY"


# ==============================================================================================================
# MAIN FORENSIC
# ==============================================================================

def main():

    title(
        "OUTCOME_v0.3 FUSION DIRECTION HISTORICAL "
        "RUNTIME FILESYSTEM PROVENANCE FORENSIC v0.1"
    )

    print(f"Database          : {DB_PATH}")
    print(f"Project root      : {PROJECT_ROOT}")
    print(f"Writer target     : fusion_engine.py")
    print(f"Target table      : {TARGET_TABLE}")
    print(f"Target column     : {TARGET_COLUMN}")
    print("Mode              : READ ONLY / FILESYSTEM PROVENANCE")
    print("Production writer  : NEVER EXECUTED")
    print("Direction repair   : FORBIDDEN")
    print("Score inference   : FORBIDDEN")
    print("Synthetic data    : FORBIDDEN")

    # ----------------------------------------------------------------------------------------------------------
    # SAFETY
    # ----------------------------------------------------------------------------------------------------------

    section("FORENSIC SCRIPT SAFETY CHECK")

    print("Production DB connection : READ ONLY")
    print("Production INSERT        : NONE")
    print("Production UPDATE        : NONE")
    print("Production DELETE        : NONE")
    print("Production DDL           : NONE")
    print("Production writer run    : NO")
    print("Historical repair        : NO")
    print("Direction reconstruction : NO")
    print("Score inference          : NO")
    print("Filesystem modification  : NO")

    # ----------------------------------------------------------------------------------------------------------
    # ENVIRONMENT
    # ----------------------------------------------------------------------------------------------------------

    section("ENVIRONMENT")

    print(f"Python : {sys.version}")
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Database : {DB_PATH}")
    print(f"Script : {REPORT_SELF}")

    # ----------------------------------------------------------------------------------------------------------
    # DATABASE BASELINE
    # ----------------------------------------------------------------------------------------------------------

    baseline = read_database_baseline()

    section("PRODUCTION DATABASE BASELINE")

    print(f"Total rows       : {baseline['total']}")
    print(f"Valid direction  : {baseline['valid']}")
    print(f"NULL direction   : {baseline['null']}")

    # ----------------------------------------------------------------------------------------------------------
    # NULL ROW IDS
    # ----------------------------------------------------------------------------------------------------------

    section("HISTORICAL NULL ROW IDENTITIES")

    for row in baseline["rows"]:

        row_id, timestamp, asset, engine, snapshot = row

        print(
            f"id={row_id:3d} | "
            f"{timestamp} | "
            f"{asset:4s} | "
            f"{engine:12s} | "
            f"snapshot={snapshot}"
        )

    # ----------------------------------------------------------------------------------------------------------
    # HISTORICAL WINDOW
    # ----------------------------------------------------------------------------------------------------------

    section("HISTORICAL EXECUTION WINDOW")

    print(f"START : {HISTORICAL_START.isoformat()}")
    print(f"END   : {HISTORICAL_END.isoformat()}")

    print()
    print("This window is used ONLY for filesystem timestamp correlation.")
    print("No timestamp is converted into a direction.")

    # ----------------------------------------------------------------------------------------------------------
    # FILESYSTEM ENUMERATION
    # ----------------------------------------------------------------------------------------------------------

    section("FILESYSTEM CANDIDATE ENUMERATION")

    candidates = enumerate_candidate_files()

    print(f"Candidate files discovered : {len(candidates)}")

    # ----------------------------------------------------------------------------------------------------------
    # FILE TIMESTAMP MATCHES
    # ----------------------------------------------------------------------------------------------------------

    subsection("FILES WITH HISTORICAL-WINDOW TIMESTAMP ACTIVITY")

    timestamp_matches = []

    for path in candidates:

        info = timestamp_forensic(path)

        if timestamp_hits(info):

            timestamp_matches.append(
                (path, info)
            )

    print(
        f"Timestamp-correlated files : "
        f"{len(timestamp_matches)}"
    )

    for path, info in sorted(
        timestamp_matches,
        key=lambda x: x[1]["modified"],
    ):

        print()
        print(f"FILE     : {path}")
        print(f"SIZE     : {info['size']}")
        print(f"CREATED  : {info['created'].isoformat()}")
        print(f"MODIFIED : {info['modified'].isoformat()}")
        print(f"ACCESSED : {info['accessed'].isoformat()}")

    # ----------------------------------------------------------------------------------------------------------
    # TEXT PROVENANCE SEARCH
    # ----------------------------------------------------------------------------------------------------------

    section("HISTORICAL RUNTIME TOKEN SEARCH")

    artifact_hits = []

    for path in candidates:

        matches = search_text_file(path)

        if not matches:
            continue

        classification = classify_runtime_evidence(matches)

        artifact_hits.append(
            {
                "path": path,
                "matches": matches,
                "classification": classification,
            }
        )

    print(
        f"Files containing historical/runtime tokens : "
        f"{len(artifact_hits)}"
    )

    for artifact in artifact_hits:

        print()
        print(f"FILE            : {artifact['path']}")
        print(f"CLASSIFICATION  : {artifact['classification']}")

        for match in artifact["matches"]:

            print(
                f"  TOKEN   : {match['token']}"
            )

            print(
                f"  CONTEXT : {match['snippet']}"
            )

    # ----------------------------------------------------------------------------------------------------------
    # ZIP FORENSIC
    # ----------------------------------------------------------------------------------------------------------

    section("ARCHIVE RUNTIME PROVENANCE")

    archives = list(PROJECT_ROOT.rglob("*.zip"))

    print(f"ZIP archives discovered : {len(archives)}")

    for archive in archives:

        results = inspect_zip(archive)

        if not results:
            continue

        print()
        print(f"ARCHIVE : {archive}")
        print(
            f"Relevant members : {len(results)}"
        )

        for item in results:

            print(
                f"  {item['name']} | "
                f"{item['size']} bytes"
            )

    # ----------------------------------------------------------------------------------------------------------
    # HIGH-VALUE EVIDENCE CLASSIFICATION
    # ----------------------------------------------------------------------------------------------------------

    section("RUNTIME PROVENANCE EVIDENCE CLASSIFICATION")

    strong = []
    medium = []
    token_only = []

    for artifact in artifact_hits:

        classification = artifact["classification"]

        if classification == "STRONG_RUNTIME_ARTIFACT":
            strong.append(artifact)

        elif classification == "RUNTIME_RELATED_ARTIFACT":
            medium.append(artifact)

        else:
            token_only.append(artifact)

    print(
        f"STRONG_RUNTIME_ARTIFACT     : {len(strong)}"
    )

    print(
        f"RUNTIME_RELATED_ARTIFACT    : {len(medium)}"
    )

    print(
        f"TOKEN_ONLY                   : {len(token_only)}"
    )

    # ----------------------------------------------------------------------------------------------------------
    # CAUSALITY RULE
    # ----------------------------------------------------------------------------------------------------------

    section("HISTORICAL NULL CAUSALITY ASSESSMENT")

    print(
        "IMPORTANT:"
    )

    print(
        "A filesystem artifact is NOT automatically treated as "
        "causal evidence."
    )

    print(
        "To establish causal provenance, an artifact must contain "
        "execution evidence that can be temporally correlated with "
        "the historical NULL-producing generation."
    )

    print()

    if strong:

        print(
            "STRONG RUNTIME ARTIFACTS FOUND."
        )

        print(
            "Historical runtime provenance may be recoverable."
        )

        print(
            "Further correlation is required before any causal claim."
        )

        causality = (
            "RUNTIME_PROVENANCE_CANDIDATE_FOUND"
        )

    elif medium:

        print(
            "Runtime-related artifacts found, "
            "but causal execution is not yet proven."
        )

        causality = (
            "RUNTIME_PROVENANCE_NOT_YET_PROVEN"
        )

    else:

        print(
            "No sufficiently strong historical runtime artifact "
            "was found in the scanned filesystem."
        )

        causality = (
            "NO_RUNTIME_PROVENANCE_FOUND"
        )

    # ----------------------------------------------------------------------------------------------------------
    # DATABASE INVARIANT
    # ----------------------------------------------------------------------------------------------------------

    after = read_database_baseline()

    section("POST-FORENSIC DATABASE INVARIANT")

    print(
        f"Before total       : {baseline['total']}"
    )

    print(
        f"After total        : {after['total']}"
    )

    print(
        f"Before NULL        : {baseline['null']}"
    )

    print(
        f"After NULL         : {after['null']}"
    )

    invariant = (
        baseline["total"] == after["total"]
        and baseline["null"] == after["null"]
    )

    print()

    print(
        "DATABASE POPULATION INVARIANT : "
        + ("PASS" if invariant else "FAIL")
    )

    # ----------------------------------------------------------------------------------------------------------
    # FINAL SAFETY
    # ----------------------------------------------------------------------------------------------------------

    section("FINAL SAFETY VERDICT")

    print("Database writes          : NONE")
    print("Production INSERT       : NONE")
    print("Production UPDATE       : NONE")
    print("Production DELETE       : NONE")
    print("Production DDL          : NONE")
    print("Production DB modified  : NO")
    print("Production writer run   : NO")
    print("Direction reconstructed  : NO")
    print("Direction repaired       : NO")
    print("Score inference          : NO")
    print("Eligibility repaired     : NO")
    print("Synthetic data           : NOT USED")
    print("Interpolation            : NOT USED")
    print("Forward fill             : NOT USED")
    print("Back fill                : NOT USED")

    # ----------------------------------------------------------------------------------------------------------
    # CONCLUSION
    # ----------------------------------------------------------------------------------------------------------

    section("FORENSIC CONCLUSION")

    print(
        f"RUNTIME FILESYSTEM PROVENANCE : {causality}"
    )

    print()

    if causality == "RUNTIME_PROVENANCE_CANDIDATE_FOUND":

        print(
            "Historical runtime artifacts exist."
        )

        print(
            "They must now be correlated against the exact "
            "NULL-row timestamps and engine generations."
        )

        print()

        print(
            "NO direction has been inferred."
        )

        print(
            "NO historical row has been modified."
        )

        print(
            "NO repair is authorized by this stage."
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Correlate identified runtime artifact(s) "
            "with IDs 1-20 and the five historical execution clusters."
        )

    elif causality == "RUNTIME_PROVENANCE_NOT_YET_PROVEN":

        print(
            "Filesystem artifacts exist but do not yet establish "
            "historical writer causality."
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Inspect the strongest runtime-related artifact(s) "
            "for execution timestamp, command line, process output, "
            "and database writer behavior."
        )

    else:

        print(
            "No historical runtime execution artifact was found "
            "within the scanned project filesystem."
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Expand provenance search outside the project directory "
            "only if an external execution mechanism was used."
        )

    print()
    print("FORENSIC COMPLETE.")


# ==============================================================================================================
# ENTRY POINT
# ==============================================================================================================

if __name__ == "__main__":
    main()