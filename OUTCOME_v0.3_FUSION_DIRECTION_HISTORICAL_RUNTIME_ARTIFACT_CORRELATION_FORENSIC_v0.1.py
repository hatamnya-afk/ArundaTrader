# ==============================================================================================================
# OUTCOME_v0.3 FUSION DIRECTION HISTORICAL RUNTIME ARTIFACT CORRELATION FORENSIC v0.1
# ==============================================================================================================
#
# PURPOSE
# -------
# Correlate the strongest historical runtime-related filesystem/archive artifacts
# with the exact 20 NULL-direction production rows.
#
# THIS STAGE DOES NOT:
#   - execute fusion_engine.py
#   - execute execution_engine.py
#   - execute signal_logic.py
#   - modify arunda.db
#   - modify any source
#   - reconstruct direction
#   - infer direction from score
#   - repair historical rows
#
# ==============================================================================================================

from __future__ import annotations

import hashlib
import io
import re
import sqlite3
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


# ==============================================================================================================
# CONFIG
# ==============================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

BACKUP_DIR = PROJECT_ROOT / "_backups"

TARGET_TABLE = "fusion_signals"

TARGET_COLUMN = "direction"

REPORT_SELF = Path(__file__).resolve()

BACKUP_ZIP = (
    BACKUP_DIR /
    "ArundaTrader_BACKUP_20260818_003611.zip"
)

HISTORICAL_CLUSTERS = [
    {
        "label": "FUSION_v0.2",
        "engine": "FUSION_v0.2",
        "timestamp": "2026-08-15T16:21",
        "assets": {"BTC", "ETH", "SOL", "XRP"},
    },
    {
        "label": "FUSION_v0.3_A",
        "engine": "FUSION_v0.3",
        "timestamp": "2026-08-15T16:23",
        "assets": {"BTC", "ETH", "SOL", "XRP"},
    },
    {
        "label": "FUSION_v0.3_B",
        "engine": "FUSION_v0.3",
        "timestamp": "2026-08-15T16:26:26",
        "assets": {"BTC", "ETH", "SOL", "XRP"},
    },
    {
        "label": "FUSION_v0.3_C",
        "engine": "FUSION_v0.3",
        "timestamp": "2026-08-15T16:26:35",
        "assets": {"BTC", "ETH", "SOL", "XRP"},
    },
    {
        "label": "FUSION_v0.4",
        "engine": "FUSION_v0.4",
        "timestamp": "2026-08-15T16:32:24",
        "assets": {"BTC", "ETH", "SOL", "XRP"},
    },
]


# ==============================================================================================================
# TOKENS
# ==============================================================================================================

HIGH_VALUE_TOKENS = [
    "FUSION_v0.2",
    "FUSION_v0.3",
    "FUSION_v0.4",
    "fusion_signals",
    "fusion_engine.py",
    "ARUNDA FUSION ENGINE",
    "FUSION ENGINE COMPLETE",
    "Signals generated",
    "Snapshot ID",
    "Database:",
    "INSERT INTO fusion_signals",
    "direction",
    "execute",
    "execution",
    "runtime",
    "stdout",
    "stderr",
    "command",
    "python",
    "main()",
]


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

def sha256_bytes(data: bytes) -> str:

    return hashlib.sha256(data).hexdigest()


# ==============================================================================================================
# READ-ONLY DATABASE
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

def load_null_rows():

    conn = open_production_readonly()

    try:

        rows = conn.execute(
            """
            SELECT
                id,
                timestamp,
                asset,
                engine_version,
                snapshot_id,
                fused_score,
                confidence,
                regime
            FROM fusion_signals
            WHERE direction IS NULL
            ORDER BY id
            """
        ).fetchall()

        return rows

    finally:
        conn.close()


# ==============================================================================================================
# NORMALIZATION
# ==============================================================================================================

def normalize(text):

    return re.sub(
        r"\s+",
        " ",
        text.replace("\r", " ").replace("\n", " "),
    ).strip()


# ==============================================================================================================
# TOKEN SEARCH
# ==============================================================================================================

def find_token_hits(text):

    lowered = text.lower()

    hits = []

    for token in HIGH_VALUE_TOKENS:

        pos = lowered.find(token.lower())

        if pos < 0:
            continue

        start = max(0, pos - 300)
        end = min(
            len(text),
            pos + len(token) + 600,
        )

        snippet = normalize(
            text[start:end]
        )

        hits.append(
            {
                "token": token,
                "snippet": snippet,
                "position": pos,
            }
        )

    return hits


# ==============================================================================================================
# EXECUTION SIGNALS
# ==============================================================================================================

EXECUTION_PATTERNS = {

    "PYTHON_COMMAND": [
        r"\bpython(?:\.exe)?\b",
        r"\bpy(?:\.exe)?\s+",
    ],

    "FUSION_EXECUTION": [
        r"fusion_engine\.py",
        r"fusion_engine\s*\(",
        r"from\s+fusion_engine",
        r"import\s+fusion_engine",
    ],

    "MAIN_INVOCATION": [
        r"\bmain\s*\(",
        r"__main__",
    ],

    "DATABASE_USE": [
        r"arunda\.db",
        r"sqlite3\.connect",
        r"fusion_signals",
    ],

    "INSERT": [
        r"insert\s+into\s+fusion_signals",
        r"execute\s*\(",
    ],

    "RUNTIME_OUTPUT": [
        r"ARUNDA FUSION ENGINE",
        r"FUSION ENGINE COMPLETE",
        r"Signals generated",
        r"Snapshot ID",
    ],

    "ENGINE_VERSION": [
        r"FUSION_v0\.2",
        r"FUSION_v0\.3",
        r"FUSION_v0\.4",
    ],

    "DIRECTION": [
        r"\bdirection\b",
        r"LONG",
        r"SHORT",
        r"FLAT",
    ],
}


def detect_execution_signals(text):

    lowered = text.lower()

    result = defaultdict(list)

    for category, patterns in EXECUTION_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                lowered,
                flags=re.IGNORECASE,
            ):

                result[category].append(pattern)

    return dict(result)


# ==============================================================================================================
# HISTORICAL CLUSTER CORRELATION
# ==============================================================================================================

def correlate_cluster(text):

    lowered = text.lower()

    scores = []

    for cluster in HISTORICAL_CLUSTERS:

        score = 0
        evidence = []

        if cluster["engine"].lower() in lowered:

            score += 5
            evidence.append(
                f"engine={cluster['engine']}"
            )

        timestamp_token = cluster["timestamp"].lower()

        if timestamp_token in lowered:

            score += 8
            evidence.append(
                f"timestamp={cluster['timestamp']}"
            )

        for asset in cluster["assets"]:

            if re.search(
                rf"\b{re.escape(asset.lower())}\b",
                lowered,
            ):

                score += 1
                evidence.append(
                    f"asset={asset}"
                )

        if score > 0:

            scores.append(
                {
                    "label": cluster["label"],
                    "score": score,
                    "evidence": evidence,
                }
            )

    return sorted(
        scores,
        key=lambda x: x["score"],
        reverse=True,
    )


# ==============================================================================================================
# CAUSALITY SCORING
# ==============================================================================================================

def causality_score(signals, cluster_hits, token_hits):

    score = 0
    reasons = []

    if "PYTHON_COMMAND" in signals:

        score += 10
        reasons.append("python command evidence")

    if "FUSION_EXECUTION" in signals:

        score += 15
        reasons.append("fusion engine execution reference")

    if "MAIN_INVOCATION" in signals:

        score += 10
        reasons.append("main invocation reference")

    if "DATABASE_USE" in signals:

        score += 10
        reasons.append("database runtime reference")

    if "INSERT" in signals:

        score += 15
        reasons.append("writer/INSERT evidence")

    if "RUNTIME_OUTPUT" in signals:

        score += 20
        reasons.append("actual runtime output pattern")

    if "ENGINE_VERSION" in signals:

        score += 10
        reasons.append("historical engine version")

    if cluster_hits:

        best = cluster_hits[0]

        score += min(
            best["score"],
            20,
        )

        reasons.append(
            f"historical cluster correlation={best['label']}"
        )

    if token_hits:

        score += min(
            len(token_hits),
            10,
        )

    return score, reasons


# ==============================================================================================================
# CLASSIFICATION
# ==============================================================================================================

def classify(score):

    if score >= 70:
        return "HIGH_VALUE_RUNTIME_PROVENANCE"

    if score >= 45:
        return "STRONG_RUNTIME_RELATED"

    if score >= 20:
        return "RUNTIME_RELATED"

    return "LOW_VALUE_ARTIFACT"


# ==============================================================================================================
# ZIP INSPECTION
# ==============================================================================================================

def inspect_archive():

    if not BACKUP_ZIP.exists():

        return []

    results = []

    with zipfile.ZipFile(
        BACKUP_ZIP,
        "r",
    ) as archive:

        for info in archive.infolist():

            if info.is_dir():
                continue

            name = info.filename.lower()

            relevant = (
                "fusion" in name
                or "execution" in name
                or "signal" in name
                or "report" in name
                or "runtime" in name
                or "log" in name
            )

            if not relevant:
                continue

            try:

                raw = archive.read(info)

                text = raw.decode(
                    "utf-8",
                    errors="ignore",
                )

            except Exception:

                continue

            results.append(
                {
                    "source": f"ZIP::{info.filename}",
                    "data": raw,
                    "text": text,
                    "sha256": sha256_bytes(raw),
                    "size": len(raw),
                }
            )

    return results


# ==============================================================================================================
# FILESYSTEM ARTIFACTS
# ==============================================================================================================

def filesystem_artifacts():

    artifacts = []

    for path in PROJECT_ROOT.rglob("*"):

        try:

            if not path.is_file():
                continue

            if path == REPORT_SELF:
                continue

            if path.suffix.lower() not in {
                ".txt",
                ".log",
                ".out",
                ".err",
                ".json",
                ".jsonl",
                ".csv",
                ".md",
            }:

                continue

            if path.stat().st_size > 25 * 1024 * 1024:
                continue

            raw = path.read_bytes()

            text = raw.decode(
                "utf-8",
                errors="ignore",
            )

            artifacts.append(
                {
                    "source": str(path),
                    "data": raw,
                    "text": text,
                    "sha256": sha256_bytes(raw),
                    "size": len(raw),
                }
            )

        except (
            PermissionError,
            OSError,
        ):

            continue

    return artifacts


# ==============================================================================================================
# ARTIFACT ANALYSIS
# ==============================================================================================================

def analyze_artifact(artifact):

    text = artifact["text"]

    token_hits = find_token_hits(text)

    signals = detect_execution_signals(text)

    cluster_hits = correlate_cluster(text)

    score, reasons = causality_score(
        signals,
        cluster_hits,
        token_hits,
    )

    return {
        "source": artifact["source"],
        "sha256": artifact["sha256"],
        "size": artifact["size"],
        "score": score,
        "classification": classify(score),
        "signals": signals,
        "cluster_hits": cluster_hits,
        "token_hits": token_hits,
        "reasons": reasons,
    }


# ==============================================================================================================
# MAIN
# ==============================================================================================================

def main():

    title(
        "OUTCOME_v0.3 FUSION DIRECTION HISTORICAL "
        "RUNTIME ARTIFACT CORRELATION FORENSIC v0.1"
    )

    print(f"Database          : {DB_PATH}")
    print(f"Project root      : {PROJECT_ROOT}")
    print(f"Backup archive    : {BACKUP_ZIP}")
    print(f"Target table      : {TARGET_TABLE}")
    print(f"Target column     : {TARGET_COLUMN}")
    print("Mode              : READ ONLY")
    print("Production writer : NEVER EXECUTED")
    print("Direction repair  : FORBIDDEN")
    print("Score inference   : FORBIDDEN")

    # ----------------------------------------------------------------------------------------------------------
    # SAFETY
    # ----------------------------------------------------------------------------------------------------------

    section("SAFETY")

    print("Production DB writes : NONE")
    print("Production writer    : NOT EXECUTED")
    print("Production source    : NOT MODIFIED")
    print("Filesystem writes    : NONE")
    print("Direction inference  : NONE")
    print("Historical repair    : NONE")

    # ----------------------------------------------------------------------------------------------------------
    # NULL ROW BASELINE
    # ----------------------------------------------------------------------------------------------------------

    null_rows = load_null_rows()

    section("HISTORICAL NULL ROW TARGET SET")

    print(
        f"NULL direction rows : {len(null_rows)}"
    )

    print()

    for row in null_rows:

        (
            row_id,
            timestamp,
            asset,
            engine,
            snapshot,
            score,
            confidence,
            regime,
        ) = row

        print(
            f"id={row_id:3d} | "
            f"{timestamp} | "
            f"{asset:4s} | "
            f"{engine:12s} | "
            f"snapshot={snapshot}"
        )

    # ----------------------------------------------------------------------------------------------------------
    # LOAD ARTIFACTS
    # ----------------------------------------------------------------------------------------------------------

    section("ARTIFACT COLLECTION")

    fs = filesystem_artifacts()
    archive = inspect_archive()

    artifacts = fs + archive

    print(
        f"Filesystem text artifacts : {len(fs)}"
    )

    print(
        f"Archive artifacts         : {len(archive)}"
    )

    print(
        f"Total artifacts analyzed  : {len(artifacts)}"
    )

    # ----------------------------------------------------------------------------------------------------------
    # ANALYZE
    # ----------------------------------------------------------------------------------------------------------

    analyzed = []

    for artifact in artifacts:

        result = analyze_artifact(
            artifact
        )

        if result["score"] <= 0:
            continue

        analyzed.append(result)

    analyzed.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    # ----------------------------------------------------------------------------------------------------------
    # RANKING
    # ----------------------------------------------------------------------------------------------------------

    section("RUNTIME ARTIFACT RANKING")

    print(
        f"Artifacts with evidence : {len(analyzed)}"
    )

    for index, result in enumerate(
        analyzed[:40],
        start=1,
    ):

        print()

        print(
            f"[{index}] "
            f"SCORE={result['score']:3d} | "
            f"{result['classification']}"
        )

        print(
            f"SOURCE : {result['source']}"
        )

        print(
            f"SIZE   : {result['size']}"
        )

        print(
            f"SHA256 : {result['sha256']}"
        )

        if result["reasons"]:

            print(
                "EVIDENCE:"
            )

            for reason in result["reasons"]:

                print(
                    f"  - {reason}"
                )

        if result["cluster_hits"]:

            print(
                "CLUSTER CORRELATION:"
            )

            for hit in result["cluster_hits"][:3]:

                print(
                    f"  {hit['label']} "
                    f"| score={hit['score']} "
                    f"| {', '.join(hit['evidence'])}"
                )

    # ----------------------------------------------------------------------------------------------------------
    # HIGH VALUE ARTIFACTS
    # ----------------------------------------------------------------------------------------------------------

    high_value = [
        x
        for x in analyzed
        if x["classification"]
        in {
            "HIGH_VALUE_RUNTIME_PROVENANCE",
            "STRONG_RUNTIME_RELATED",
        }
    ]

    section("HIGH-VALUE RUNTIME PROVENANCE")

    print(
        f"High-value artifacts : {len(high_value)}"
    )

    if high_value:

        for result in high_value:

            print()

            print(
                f"SOURCE : {result['source']}"
            )

            print(
                f"SCORE  : {result['score']}"
            )

            print(
                f"CLASS  : {result['classification']}"
            )

            print(
                f"SHA256 : {result['sha256']}"
            )

            if result["cluster_hits"]:

                print(
                    "BEST HISTORICAL CORRELATION:"
                )

                best = result["cluster_hits"][0]

                print(
                    f"  {best['label']} "
                    f"| score={best['score']}"
                )

                for evidence in best["evidence"]:

                    print(
                        f"    - {evidence}"
                    )

    else:

        print(
            "No artifact reached the high-value "
            "runtime provenance threshold."
        )

    # ----------------------------------------------------------------------------------------------------------
    # EXACT HISTORICAL ENGINE MATCH
    # ----------------------------------------------------------------------------------------------------------

    section("EXACT HISTORICAL ENGINE MATCH")

    for engine in (
        "FUSION_v0.2",
        "FUSION_v0.3",
        "FUSION_v0.4",
    ):

        matches = []

        for result in analyzed:

            if engine.lower() in result["source"].lower():
                matches.append(result)

            for token_hit in result["token_hits"]:

                if token_hit["token"].lower() == engine.lower():

                    if result not in matches:
                        matches.append(result)

        print()

        print(
            f"{engine} : {len(matches)} artifact(s)"
        )

        for result in matches[:10]:

            print(
                f"  - {result['source']}"
            )

    # ----------------------------------------------------------------------------------------------------------
    # DATABASE WRITER EVIDENCE
    # ----------------------------------------------------------------------------------------------------------

    section("DATABASE WRITER EVIDENCE")

    writer_candidates = []

    for result in analyzed:

        signals = result["signals"]

        if (
            "DATABASE_USE" in signals
            and "INSERT" in signals
        ):

            writer_candidates.append(result)

    print(
        f"Artifacts containing DB + INSERT evidence : "
        f"{len(writer_candidates)}"
    )

    for result in writer_candidates:

        print()

        print(
            f"SOURCE : {result['source']}"
        )

        print(
            f"SCORE  : {result['score']}"
        )

        print(
            f"CLASS  : {result['classification']}"
        )

        print(
            "SIGNALS:"
        )

        for category in result["signals"]:

            print(
                f"  - {category}"
            )

    # ----------------------------------------------------------------------------------------------------------
    # HISTORICAL CLUSTER MATRIX
    # ----------------------------------------------------------------------------------------------------------

    section("HISTORICAL CLUSTER CORRELATION MATRIX")

    for cluster in HISTORICAL_CLUSTERS:

        matched = []

        for result in analyzed:

            for hit in result["cluster_hits"]:

                if hit["label"] == cluster["label"]:

                    matched.append(
                        result
                    )

                    break

        print()

        print(
            f"{cluster['label']}"
        )

        print(
            f"  Engine    : {cluster['engine']}"
        )

        print(
            f"  Timestamp : {cluster['timestamp']}"
        )

        print(
            f"  Artifacts : {len(matched)}"
        )

        for result in matched[:8]:

            print(
                f"    - {result['source']} "
                f"| score={result['score']}"
            )

    # ----------------------------------------------------------------------------------------------------------
    # CAUSALITY VERDICT
    # ----------------------------------------------------------------------------------------------------------

    section("HISTORICAL NULL CAUSALITY ASSESSMENT")

    if high_value:

        print(
            "HIGH-VALUE RUNTIME PROVENANCE CANDIDATE FOUND."
        )

        print()

        print(
            "This stage has identified artifact(s) with "
            "execution-level evidence."
        )

        print(
            "Temporal correlation must still be established "
            "against the exact NULL-producing clusters."
        )

        print()

        print(
            "VERDICT:"
        )

        print(
            "RUNTIME_PROVENANCE_CANDIDATE_FOUND"
        )

    elif writer_candidates:

        print(
            "Database writer artifacts were found."
        )

        print(
            "However, temporal execution causality is not yet proven."
        )

        print()

        print(
            "VERDICT:"
        )

        print(
            "WRITER_ARTIFACT_FOUND_CAUSALITY_NOT_PROVEN"
        )

    else:

        print(
            "No artifact currently establishes "
            "historical writer causality."
        )

        print()

        print(
            "VERDICT:"
        )

        print(
            "HISTORICAL_RUNTIME_CAUSALITY_NOT_PROVEN"
        )

    # ----------------------------------------------------------------------------------------------------------
    # POST CHECK
    # ----------------------------------------------------------------------------------------------------------

    after = load_null_rows()

    section("POST-FORENSIC DATABASE INVARIANT")

    print(
        f"Before NULL rows : {len(null_rows)}"
    )

    print(
        f"After NULL rows  : {len(after)}"
    )

    invariant = (
        len(null_rows) == len(after)
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

    print("Production DB writes       : NONE")
    print("Production writer          : NEVER EXECUTED")
    print("Production DB modified     : NO")
    print("Production source modified : NO")
    print("Direction inferred         : NO")
    print("Direction reconstructed    : NO")
    print("Historical repair          : NO")
    print("Score inference            : NO")
    print("Synthetic data             : NOT USED")
    print("Interpolation              : NOT USED")
    print("Forward fill               : NOT USED")
    print("Back fill                  : NOT USED")

    # ----------------------------------------------------------------------------------------------------------
    # CONCLUSION
    # ----------------------------------------------------------------------------------------------------------

    section("FORENSIC CONCLUSION")

    if high_value:

        print(
            "RUNTIME ARTIFACT CORRELATION:"
        )

        print(
            "CANDIDATE FOUND — TEMPORAL CORRELATION REQUIRED"
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Inspect only the highest-ranked artifact(s) "
            "and correlate execution timestamp / command / "
            "engine generation against NULL IDs 1-20."
        )

    elif writer_candidates:

        print(
            "DATABASE WRITER ARTIFACT FOUND."
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Perform exact timestamp + execution-generation "
            "correlation on the writer artifact."
        )

    else:

        print(
            "No causal runtime artifact was established."
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Search external execution provenance "
            "(PowerShell history, Task Scheduler, IDE/run history, "
            "terminal logs) if applicable."
        )

    print()

    print(
        "NO direction value was inferred."
    )

    print(
        "NO historical row was modified."
    )

    print(
        "FORENSIC COMPLETE."
    )


# ==============================================================================================================
# ENTRY
# ==============================================================================================================

if __name__ == "__main__":
    main()