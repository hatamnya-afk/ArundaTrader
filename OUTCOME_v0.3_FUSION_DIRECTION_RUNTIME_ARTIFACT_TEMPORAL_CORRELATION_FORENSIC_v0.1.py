# -*- coding: utf-8 -*-

"""
==============================================================================================================
OUTCOME_v0.3 FUSION DIRECTION RUNTIME ARTIFACT TEMPORAL CORRELATION FORENSIC v0.1
==============================================================================================================

PURPOSE
-------
Correlate the strongest available runtime-related filesystem artifacts
with the exact historical NULL-direction fusion_signals clusters.

CURRENT FRONTIER
----------------
RUNTIME_PROVENANCE_CANDIDATE_FOUND
    ->
TEMPORAL_CORRELATION_REQUIRED

STRICT RULES
------------
- READ ONLY
- Production DB is never modified
- Production writer is never executed
- No direction inference
- No historical repair
- No score-based inference
- No synthetic data
- No interpolation
- No forward fill
- No back fill

TARGET
------
Database       : arunda.db
Table          : fusion_signals
Column         : direction
Historical IDs : 1-20

HIGH-VALUE ARTIFACTS
--------------------
1. ZIP::fusion_engine.py
2. fusion_code.txt
3. ZIP::signal_outcome_engine.py
4. CODE_STRUCTURE.txt
5. backup CODE_STRUCTURE.txt

The script deliberately does NOT execute these artifacts.
It only performs forensic text/provenance analysis.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================================================
# CONFIGURATION
# ============================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"
BACKUP_DIR = PROJECT_ROOT / "_backups"

TARGET_TABLE = "fusion_signals"
TARGET_COLUMN = "direction"

NULL_IDS = list(range(1, 21))

ARTIFACT_PATTERNS = [
    "fusion_engine.py",
    "fusion_code.txt",
    "signal_outcome_engine.py",
    "CODE_STRUCTURE.txt",
]

ARCHIVE_PATTERNS = [
    "ArundaTrader_BACKUP_*.zip",
]


# ============================================================================================================
# OUTPUT
# ============================================================================================================

SEP = "=" * 112
SUB = "-" * 112


def title(text: str):
    print()
    print(SEP)
    print(text)
    print(SEP)


def section(text: str):
    print()
    print("=" * 112)
    print(text)
    print("=" * 112)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================================================
# DATABASE — READ ONLY
# ============================================================================================================

def open_production_readonly():
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    return sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )


def load_null_rows():
    conn = open_production_readonly()
    try:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            f"""
            SELECT
                id,
                timestamp,
                asset,
                engine_version,
                snapshot_id,
                fused_score,
                confidence,
                regime
            FROM {TARGET_TABLE}
            WHERE {TARGET_COLUMN} IS NULL
            ORDER BY id
            """
        ).fetchall()

        return [dict(r) for r in rows]

    finally:
        conn.close()


# ============================================================================================================
# TIMESTAMP PARSING
# ============================================================================================================

ISO_PATTERNS = [
    re.compile(
        r"""
        (?P<date>
            20\d{2}[-/]\d{2}[-/]\d{2}
        )
        [T\s]
        (?P<time>
            \d{2}:\d{2}:\d{2}
            (?:[.,]\d+)?
        )
        (?P<tz>
            Z
            |
            [+-]\d{2}:?\d{2}
        )?
        """,
        re.VERBOSE,
    ),
]

COMPACT_TIMESTAMP = re.compile(
    r"""
    20\d{2}
    [-]?
    \d{2}
    [-]?
    \d{2}
    [T\s]?
    \d{2}
    [:]?
    \d{2}
    [:]?
    \d{2}
    (?:[.,]\d+)?
    """,
    re.VERBOSE,
)


def normalize_timestamp(raw: str):
    raw = raw.strip()

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    raw = raw.replace(",", ".")

    try:
        dt = datetime.fromisoformat(raw)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def extract_timestamps(text: str):
    found = []

    for pattern in ISO_PATTERNS:
        for m in pattern.finditer(text):
            value = m.group(0)

            # Avoid treating simple dates inside filenames as timestamps.
            if ":" not in value:
                continue

            dt = normalize_timestamp(value)

            if dt:
                found.append(
                    {
                        "raw": value,
                        "dt": dt,
                    }
                )

    # Deduplicate
    unique = {}
    for item in found:
        key = item["dt"].isoformat()
        unique[key] = item

    return list(unique.values())


# ============================================================================================================
# HISTORICAL NULL CLUSTERS
# ============================================================================================================

def build_clusters(rows):
    clusters = defaultdict(list)

    for row in rows:
        timestamp = row["timestamp"]

        # Exact timestamp cluster in DB.
        clusters[
            (
                row["engine_version"],
                timestamp[:19],
            )
        ].append(row)

    return clusters


def parse_db_timestamp(value):
    if not value:
        return None

    return normalize_timestamp(value)


# ============================================================================================================
# ARTIFACT DISCOVERY
# ============================================================================================================

def discover_artifacts():
    artifacts = []

    # Direct filesystem artifacts.
    for name in ARTIFACT_PATTERNS:
        path = PROJECT_ROOT / name

        if path.exists() and path.is_file():
            try:
                data = path.read_bytes()

                artifacts.append(
                    {
                        "source": str(path),
                        "member": name,
                        "data": data,
                        "sha256": sha256_bytes(data),
                        "archive": False,
                    }
                )
            except Exception:
                pass

    # ZIP archives.
    archives = []

    for pattern in ARCHIVE_PATTERNS:
        archives.extend(BACKUP_DIR.glob(pattern))

    for archive in sorted(archives):
        try:
            with zipfile.ZipFile(archive, "r") as z:
                names = set(z.namelist())

                for target in ARTIFACT_PATTERNS:
                    matches = [
                        n
                        for n in names
                        if Path(n).name.lower() == target.lower()
                    ]

                    for member in matches:
                        try:
                            data = z.read(member)

                            artifacts.append(
                                {
                                    "source": f"ZIP::{member}",
                                    "member": member,
                                    "archive_path": str(archive),
                                    "data": data,
                                    "sha256": sha256_bytes(data),
                                    "archive": True,
                                }
                            )

                        except Exception:
                            pass

        except Exception:
            pass

    return artifacts


# ============================================================================================================
# ARTIFACT CLASSIFICATION
# ============================================================================================================

def text_from_bytes(data: bytes):
    return data.decode("utf-8", errors="replace")


def classify_artifact(text: str):
    upper = text.upper()

    signals = []

    patterns = {
        "MAIN_INVOCATION": [
            r"if\s+__name__\s*==\s*[\"']__main__[\"']",
            r"\bmain\s*\(",
        ],
        "DATABASE_USE": [
            r"sqlite3",
            r"\.db\b",
            r"arunda\.db",
            r"connect\s*\(",
        ],
        "INSERT": [
            r"\bINSERT\s+INTO\b",
        ],
        "DIRECTION": [
            r"\bdirection\b",
            r"determine_direction",
        ],
        "RUNTIME_OUTPUT": [
            r"print\s*\(",
            r"FUSION ENGINE",
            r"FUSION :",
        ],
        "ENGINE_VERSION": [
            r"FUSION_v0\.\d+",
        ],
    }

    for label, regexes in patterns.items():
        for pattern in regexes:
            if re.search(pattern, text, re.IGNORECASE):
                signals.append(label)
                break

    return signals


# ============================================================================================================
# ENGINE VERSION EXTRACTION
# ============================================================================================================

ENGINE_RE = re.compile(
    r"FUSION_v0\.\d+",
    re.IGNORECASE,
)


def extract_engine_versions(text):
    values = sorted(
        set(
            m.group(0)
            for m in ENGINE_RE.finditer(text)
        )
    )

    return values


# ============================================================================================================
# COMMAND / EXECUTION EVIDENCE
# ============================================================================================================

COMMAND_PATTERNS = [
    re.compile(r"python(?:\.exe)?\s+[^\r\n]+", re.IGNORECASE),
    re.compile(r"py\s+[^\r\n]+", re.IGNORECASE),
    re.compile(r"powershell[^\r\n]+", re.IGNORECASE),
    re.compile(r"cmd(?:\.exe)?[^\r\n]+", re.IGNORECASE),
    re.compile(r"subprocess\.[a-z_]+\([^\n]+\)", re.IGNORECASE),
]


def extract_command_evidence(text):
    results = []

    for pattern in COMMAND_PATTERNS:
        for m in pattern.finditer(text):
            value = m.group(0).strip()

            if value not in results:
                results.append(value)

    return results[:20]


# ============================================================================================================
# RUNTIME-LIKE OUTPUT EXTRACTION
# ============================================================================================================

RUNTIME_MARKERS = [
    "FUSION ENGINE",
    "FUSION :",
    "SIGNALS GENERATED",
    "SNAPSHOT ID",
    "DATABASE:",
    "TABLE:",
    "ENGINE:",
    "DIRECTION",
    "ENTRY PRICE",
    "FUSION ENGINE COMPLETE",
]


def extract_runtime_markers(text):
    lines = text.splitlines()

    results = []

    for idx, line in enumerate(lines):
        upper = line.upper()

        if any(marker in upper for marker in RUNTIME_MARKERS):
            start = max(0, idx - 1)
            end = min(len(lines), idx + 2)

            block = "\n".join(lines[start:end]).strip()

            if block and block not in results:
                results.append(block)

    return results[:30]


# ============================================================================================================
# TEMPORAL CORRELATION
# ============================================================================================================

def nearest_cluster(timestamp, clusters):
    if timestamp is None:
        return None

    best = None

    for key, rows in clusters.items():
        engine, cluster_text = key

        cluster_dt = parse_db_timestamp(rows[0]["timestamp"])

        if cluster_dt is None:
            continue

        delta = abs(
            (timestamp - cluster_dt).total_seconds()
        )

        candidate = {
            "engine": engine,
            "timestamp": cluster_dt,
            "delta_seconds": delta,
            "rows": rows,
        }

        if best is None or delta < best["delta_seconds"]:
            best = candidate

    return best


def temporal_class(delta_seconds):
    if delta_seconds <= 5:
        return "EXACT_RUNTIME_WINDOW"

    if delta_seconds <= 60:
        return "STRONG_TEMPORAL_CORRELATION"

    if delta_seconds <= 300:
        return "MODERATE_TEMPORAL_CORRELATION"

    if delta_seconds <= 1800:
        return "WEAK_TEMPORAL_CORRELATION"

    return "NO_CLOSE_TEMPORAL_CORRELATION"


# ============================================================================================================
# ENGINE CORRELATION
# ============================================================================================================

def correlate_engine_versions(artifact_versions, cluster):
    if not cluster:
        return False

    return cluster["engine"] in artifact_versions


# ============================================================================================================
# FORENSIC REPORT
# ============================================================================================================

def main():

    title(
        "OUTCOME_v0.3 FUSION DIRECTION RUNTIME ARTIFACT "
        "TEMPORAL CORRELATION FORENSIC v0.1"
    )

    print(f"Database          : {DB_PATH}")
    print(f"Project root      : {PROJECT_ROOT}")
    print(f"Writer target     : fusion_engine.py")
    print(f"Target table      : {TARGET_TABLE}")
    print(f"Target column     : {TARGET_COLUMN}")
    print("Mode              : READ ONLY / TEMPORAL PROVENANCE")
    print("Production writer : NEVER EXECUTED")
    print("Direction repair  : FORBIDDEN")
    print("Score inference   : FORBIDDEN")

    # ----------------------------------------------------------------------------------------------
    # SAFETY
    # ----------------------------------------------------------------------------------------------

    section("FORENSIC SCRIPT SAFETY CHECK")

    print("Production DB connection : READ ONLY")
    print("Production INSERT        : NONE")
    print("Production UPDATE        : NONE")
    print("Production DELETE        : NONE")
    print("Production DDL           : NONE")
    print("Production writer run    : NO")
    print("Historical repair        : NO")
    print("Direction reconstruction : NO")
    print("Score inference         : NO")
    print("Synthetic data           : NO")
    print("Interpolation            : NO")
    print("Forward fill             : NO")
    print("Back fill                : NO")

    # ----------------------------------------------------------------------------------------------
    # NULL ROWS
    # ----------------------------------------------------------------------------------------------

    rows = load_null_rows()

    section("HISTORICAL NULL ROW BASELINE")

    print(f"NULL direction rows : {len(rows)}")

    if len(rows) != 20:
        print(
            f"WARNING: Expected 20 NULL rows, observed {len(rows)}"
        )

    clusters = build_clusters(rows)

    print()
    print("Historical clusters:")

    for key, cluster_rows in clusters.items():
        engine, timestamp = key

        print(
            f"{engine:25} | "
            f"{timestamp} | "
            f"rows={len(cluster_rows)} | "
            f"assets={','.join(r['asset'] for r in cluster_rows)}"
        )

    # ----------------------------------------------------------------------------------------------
    # ARTIFACT DISCOVERY
    # ----------------------------------------------------------------------------------------------

    artifacts = discover_artifacts()

    section("HIGH-VALUE ARTIFACTS")

    print(f"Artifacts discovered : {len(artifacts)}")

    for idx, artifact in enumerate(artifacts, 1):

        text = text_from_bytes(artifact["data"])

        signals = classify_artifact(text)
        versions = extract_engine_versions(text)
        timestamps = extract_timestamps(text)
        commands = extract_command_evidence(text)

        artifact["text"] = text
        artifact["signals"] = signals
        artifact["versions"] = versions
        artifact["timestamps"] = timestamps
        artifact["commands"] = commands

        print()
        print(f"[{idx}] {artifact['source']}")
        print(f"SHA256 : {artifact['sha256']}")
        print(f"SIGNALS: {', '.join(signals) if signals else 'NONE'}")
        print(
            f"ENGINE VERSIONS: "
            f"{', '.join(versions) if versions else 'NONE'}"
        )
        print(
            f"TIMESTAMPS FOUND : {len(timestamps)}"
        )

        if commands:
            print("COMMAND EVIDENCE:")
            for cmd in commands[:5]:
                print(f"  {cmd}")

    # ----------------------------------------------------------------------------------------------
    # TEMPORAL CORRELATION
    # ----------------------------------------------------------------------------------------------

    section("TEMPORAL CORRELATION MATRIX")

    correlations = []

    for artifact in artifacts:

        for timestamp_item in artifact["timestamps"]:

            ts = timestamp_item["dt"]

            nearest = nearest_cluster(ts, clusters)

            if nearest is None:
                continue

            classification = temporal_class(
                nearest["delta_seconds"]
            )

            engine_match = correlate_engine_versions(
                artifact["versions"],
                nearest,
            )

            correlations.append(
                {
                    "artifact": artifact,
                    "timestamp": timestamp_item,
                    "nearest": nearest,
                    "classification": classification,
                    "engine_match": engine_match,
                }
            )

    if not correlations:
        print(
            "No temporal correlation candidates were found."
        )

    else:

        correlations.sort(
            key=lambda x: (
                x["nearest"]["delta_seconds"],
                not x["engine_match"],
            )
        )

        for idx, item in enumerate(correlations, 1):

            artifact = item["artifact"]
            timestamp_item = item["timestamp"]
            nearest = item["nearest"]

            print()
            print(f"[CORRELATION {idx}]")
            print(f"Artifact        : {artifact['source']}")
            print(f"Artifact SHA256 : {artifact['sha256']}")
            print(
                f"Artifact time   : "
                f"{timestamp_item['dt'].isoformat()}"
            )
            print(
                f"Nearest cluster : "
                f"{nearest['engine']} | "
                f"{nearest['timestamp'].isoformat()}"
            )
            print(
                f"Delta seconds   : "
                f"{nearest['delta_seconds']:.6f}"
            )
            print(
                f"Temporal class  : "
                f"{item['classification']}"
            )
            print(
                f"Engine match    : "
                f"{'YES' if item['engine_match'] else 'NO'}"
            )
            print(
                f"Historical IDs  : "
                f"{','.join(str(r['id']) for r in nearest['rows'])}"
            )

    # ----------------------------------------------------------------------------------------------
    # EXACT MATCH CANDIDATES
    # ----------------------------------------------------------------------------------------------

    section("EXACT / STRONG TEMPORAL CANDIDATES")

    strong = [
        x
        for x in correlations
        if x["classification"]
        in {
            "EXACT_RUNTIME_WINDOW",
            "STRONG_TEMPORAL_CORRELATION",
        }
    ]

    if not strong:
        print("NONE")

    else:

        for item in strong:

            artifact = item["artifact"]
            nearest = item["nearest"]

            print(
                f"{artifact['source']}"
            )

            print(
                f"  -> cluster={nearest['engine']}"
                f" @ {nearest['timestamp'].isoformat()}"
            )

            print(
                f"  -> delta={nearest['delta_seconds']:.6f}s"
            )

            print(
                f"  -> engine_match="
                f"{'YES' if item['engine_match'] else 'NO'}"
            )

            print(
                f"  -> IDs="
                f"{','.join(str(r['id']) for r in nearest['rows'])}"
            )

    # ----------------------------------------------------------------------------------------------
    # EXECUTION EVIDENCE
    # ----------------------------------------------------------------------------------------------

    section("EXECUTION EVIDENCE REVIEW")

    execution_artifacts = []

    for artifact in artifacts:

        signals = set(artifact["signals"])

        if {
            "MAIN_INVOCATION",
            "DATABASE_USE",
            "INSERT",
        }.issubset(signals):

            execution_artifacts.append(artifact)

    print(
        f"Artifacts with MAIN + DATABASE + INSERT evidence : "
        f"{len(execution_artifacts)}"
    )

    for artifact in execution_artifacts:

        print()
        print(f"SOURCE : {artifact['source']}")
        print(f"SHA256 : {artifact['sha256']}")
        print(
            "SIGNALS: "
            + ", ".join(artifact["signals"])
        )

        if artifact["commands"]:
            print("COMMANDS:")
            for cmd in artifact["commands"][:10]:
                print(f"  {cmd}")

        markers = extract_runtime_markers(
            artifact["text"]
        )

        if markers:

            print("RUNTIME MARKERS:")

            for marker in markers[:10]:
                compact = marker.replace("\n", " | ")

                print(
                    f"  {compact[:300]}"
                )

    # ----------------------------------------------------------------------------------------------
    # CAUSALITY CLASSIFICATION
    # ----------------------------------------------------------------------------------------------

    section("HISTORICAL NULL CAUSALITY CLASSIFICATION")

    exact_engine_match = [
        x
        for x in correlations
        if x["engine_match"]
        and x["classification"]
        in {
            "EXACT_RUNTIME_WINDOW",
            "STRONG_TEMPORAL_CORRELATION",
        }
    ]

    if exact_engine_match:

        print(
            "RUNTIME_PROVENANCE_STRONG_TEMPORAL_CANDIDATE_FOUND"
        )

        print()
        print(
            "At least one runtime-related artifact contains "
            "timestamp evidence that is temporally close to a "
            "historical NULL-producing engine cluster and matches "
            "its engine generation."
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "This establishes strong provenance correlation."
        )

        print(
            "It does NOT infer any direction value."
        )

        print(
            "It does NOT authorize historical repair."
        )

    else:

        print(
            "RUNTIME_PROVENANCE_TEMPORAL_CORRELATION_NOT_ESTABLISHED"
        )

        print()
        print(
            "Available artifacts remain runtime-related, "
            "but exact temporal correlation to the historical "
            "NULL-producing clusters was not established."
        )

    # ----------------------------------------------------------------------------------------------
    # SAFETY INVARIANT
    # ----------------------------------------------------------------------------------------------

    section("FINAL SAFETY VERDICT")

    print("Production DB writes       : NONE")
    print("Production INSERT         : NONE")
    print("Production UPDATE         : NONE")
    print("Production DELETE         : NONE")
    print("Production DDL            : NONE")
    print("Production writer         : NEVER EXECUTED")
    print("Production DB modified    : NO")
    print("Production source modified: NO")
    print("Direction inferred        : NO")
    print("Direction reconstructed   : NO")
    print("Historical repair         : NO")
    print("Score inference           : NO")
    print("Eligibility repair        : NO")
    print("Synthetic data            : NOT USED")
    print("Interpolation             : NOT USED")
    print("Forward fill              : NOT USED")
    print("Back fill                 : NOT USED")

    # ----------------------------------------------------------------------------------------------
    # FINAL CONCLUSION
    # ----------------------------------------------------------------------------------------------

    section("FORENSIC CONCLUSION")

    if exact_engine_match:

        print(
            "RUNTIME ARTIFACT TEMPORAL CORRELATION:"
        )

        print(
            "STRONG CANDIDATE FOUND"
        )

        print()
        print(
            "The next evidence layer has successfully connected "
            "runtime-related artifact evidence to the historical "
            "NULL-producing generation."
        )

        print()
        print(
            "NO direction value was inferred."
        )

        print(
            "NO historical row was modified."
        )

        print(
            "NO repair was performed."
        )

        print()
        print(
            "NEXT FRONTIER:"
        )

        print(
            "Perform exact execution-provenance confirmation on "
            "the correlated artifact/cluster pair."
        )

    else:

        print(
            "RUNTIME ARTIFACT TEMPORAL CORRELATION:"
        )

        print(
            "NOT YET PROVEN"
        )

        print()
        print(
            "The strongest artifacts remain candidates, "
            "but exact temporal correlation has not been established."
        )

        print()
        print(
            "NEXT FRONTIER:"
        )

        print(
            "Inspect only the remaining highest-value runtime artifact "
            "for explicit execution timestamp / command / process evidence."
        )

    print()
    print("FORENSIC COMPLETE.")


if __name__ == "__main__":
    main()