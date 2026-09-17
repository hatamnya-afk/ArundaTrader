# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER
HISTORICAL ELIGIBILITY ARTIFACT PROVENANCE / RECOVERY FORENSIC v0.1
====================================================================================================

MODE
READ-ONLY FORENSIC + ISOLATED RECOVERY STAGING

OBJECTIVE
Locate and provenance the historical verified eligibility artifact:

    LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json

No eligibility execution is performed.
No eligibility logic is reconstructed.
No report is regenerated.
No synthetic report is created.
No production DB is modified.
No production source is modified.

If an exact historical artifact is found, it may be COPIED ONLY into an
isolated recovery staging directory.

====================================================================================================
SAFETY POLICY
====================================================================================================

Production DB writes       : FORBIDDEN
Production DB access       : NOT REQUIRED
Source modification        : FORBIDDEN
Eligibility execution      : FORBIDDEN
Eligibility rebuild       : FORBIDDEN
Report regeneration        : FORBIDDEN
Synthetic report           : FORBIDDEN
Candidate creation         : FORBIDDEN
Direction inference        : FORBIDDEN
Score reconstruction       : FORBIDDEN
Network access             : FORBIDDEN
Filesystem writes          : ISOLATED STAGING ONLY
Original artifact mutation : FORBIDDEN

====================================================================================================
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path


# ================================================================================================
# CONFIGURATION
# ================================================================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader").resolve()

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

TARGET_PRODUCER = (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET_CONSUMER = (
    "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"
)

RECOVERY_PREFIX = "arunda_historical_eligibility_recovery_"

# Never scan these locations recursively.
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".idea",
    ".venv",
    "venv",
    "node_modules",
}

# Files/directories that are operationally irrelevant and can produce huge scans.
EXCLUDED_FILE_EXTENSIONS = {
    ".db-wal",
    ".db-shm",
    ".tmp",
    ".log",
}

# Candidate artifact naming fragments.
REPORT_NAME_FRAGMENTS = (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT",
    "ELIGIBILITY_NO_TRADE_REPORT",
    "SIGNAL_ELIGIBILITY",
    "ELIGIBILITY",
)

# Content markers that strongly indicate the target report schema.
CONTENT_MARKERS = (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE",
    "eligible_pool",
    "eligibility",
    "snapshot",
    "eligible",
)

# Backup/archive extensions.
ARCHIVE_EXTENSIONS = {
    ".zip",
}

# ================================================================================================
# GLOBAL FORENSIC STATE
# ================================================================================================

RESULT = {
    "script": Path(__file__).name,
    "mode": "READ_ONLY_FORENSIC_ISOLATED_RECOVERY",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "target_report": TARGET_REPORT,
    "target_producer": TARGET_PRODUCER,
    "target_consumer": TARGET_CONSUMER,
    "base_dir": str(BASE_DIR),
    "production_source_modified": False,
    "production_db_modified": False,
    "network_access": False,
    "eligibility_executed": False,
    "report_reconstructed": False,
    "synthetic_report_created": False,
    "candidate_created": False,
    "candidates": [],
    "archive_candidates": [],
    "exact_matches": [],
    "schema_matches": [],
    "recovery_candidates": [],
    "recovery_staged": [],
    "verdict": None,
}


# ================================================================================================
# OUTPUT
# ================================================================================================

def banner(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe_print(label: str, value) -> None:
    print(f"{label:<32}: {value}")


# ================================================================================================
# HASHING
# ================================================================================================

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


# ================================================================================================
# JSON VALIDATION
# ================================================================================================

def load_json_read_only(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def json_schema_score(obj) -> int:
    """
    This does NOT reconstruct or validate eligibility semantics.
    It only measures whether an existing artifact structurally resembles
    the downstream-consumed report.
    """

    if not isinstance(obj, dict):
        return 0

    score = 0

    keys = set(obj.keys())

    expected_keys = {
        "frontier",
        "eligible_pool",
        "eligibility_report",
        "snapshot_id",
        "eligible",
    }

    score += len(keys.intersection(expected_keys)) * 10

    if isinstance(obj.get("eligible_pool"), list):
        score += 15

    if "frontier" in obj:
        if "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE" in str(
            obj.get("frontier")
        ):
            score += 25

    if "eligibility_report" in obj:
        score += 10

    if "snapshot_id" in obj:
        score += 5

    return score


def inspect_json_artifact(path: Path) -> dict:
    record = {
        "path": str(path),
        "exists": path.exists(),
        "size": None,
        "sha256": None,
        "modified_time": None,
        "json_valid": False,
        "schema_score": 0,
        "keys": [],
        "target_name_exact": path.name == TARGET_REPORT,
    }

    try:
        stat = path.stat()

        record["size"] = stat.st_size
        record["modified_time"] = datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat()

        record["sha256"] = sha256_file(path)

        obj = load_json_read_only(path)

        if obj is not None:
            record["json_valid"] = True
            record["schema_score"] = json_schema_score(obj)

            if isinstance(obj, dict):
                record["keys"] = sorted(
                    [str(k) for k in obj.keys()]
                )

    except Exception as exc:
        record["error"] = repr(exc)

    return record


# ================================================================================================
# PATH SAFETY
# ================================================================================================

def is_inside_base(path: Path) -> bool:
    try:
        path.resolve().relative_to(BASE_DIR)
        return True
    except ValueError:
        return False


def should_skip_dir(path: Path) -> bool:
    return path.name in EXCLUDED_DIR_NAMES


def should_skip_file(path: Path) -> bool:
    return path.suffix.lower() in EXCLUDED_FILE_EXTENSIONS


# ================================================================================================
# FILESYSTEM DISCOVERY
# ================================================================================================

def discover_files() -> list[Path]:
    """
    Read-only recursive filesystem discovery.

    No file is opened for writing.
    """

    discovered = []

    for root, dirs, files in os.walk(BASE_DIR):
        root_path = Path(root)

        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIR_NAMES
        ]

        for filename in files:
            path = root_path / filename

            if should_skip_file(path):
                continue

            discovered.append(path)

    return discovered


# ================================================================================================
# EXACT ARTIFACT DISCOVERY
# ================================================================================================

def discover_exact_reports(files: list[Path]) -> list[dict]:
    matches = []

    for path in files:
        if path.name == TARGET_REPORT:
            record = inspect_json_artifact(path)
            matches.append(record)

    return matches


# ================================================================================================
# RENAMED / COPIED ARTIFACT DISCOVERY
# ================================================================================================

def candidate_name_score(path: Path) -> int:
    name = path.name.upper()

    score = 0

    for fragment in REPORT_NAME_FRAGMENTS:
        if fragment.upper() in name:
            score += 10

    if path.suffix.lower() == ".json":
        score += 5

    return score


def discover_name_candidates(files: list[Path]) -> list[dict]:
    candidates = []

    for path in files:

        # Exact target handled separately.
        if path.name == TARGET_REPORT:
            continue

        score = candidate_name_score(path)

        if score <= 0:
            continue

        record = {
            "path": str(path),
            "score": score,
            "name": path.name,
            "size": None,
            "sha256": None,
            "json_valid": False,
            "schema_score": 0,
        }

        try:
            record["size"] = path.stat().st_size

            if path.suffix.lower() == ".json":
                inspected = inspect_json_artifact(path)

                record["sha256"] = inspected.get("sha256")
                record["json_valid"] = inspected.get("json_valid")
                record["schema_score"] = inspected.get("schema_score", 0)

                record["score"] += record["schema_score"]

        except Exception as exc:
            record["error"] = repr(exc)

        candidates.append(record)

    candidates.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("schema_score", 0),
        ),
        reverse=True,
    )

    return candidates


# ================================================================================================
# CONTENT FORENSIC
# ================================================================================================

def content_marker_score(path: Path) -> tuple[int, list[str]]:
    """
    Read-only content inspection.

    Only small text/JSON candidates are inspected.
    """

    if path.suffix.lower() not in {".json", ".txt", ".log", ".py"}:
        return 0, []

    try:
        size = path.stat().st_size

        # Avoid reading giant files.
        if size > 20 * 1024 * 1024:
            return 0, []

        raw = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        upper = raw.upper()

        hits = []

        for marker in CONTENT_MARKERS:
            if marker.upper() in upper:
                hits.append(marker)

        score = len(hits) * 5

        if TARGET_REPORT.upper() in upper:
            score += 25

        return score, hits

    except Exception:
        return 0, []


def discover_content_candidates(files: list[Path]) -> list[dict]:
    candidates = []

    for path in files:

        score, hits = content_marker_score(path)

        if score <= 0:
            continue

        candidates.append({
            "path": str(path),
            "score": score,
            "markers": hits,
            "size": path.stat().st_size,
        })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates


# ================================================================================================
# ARCHIVE FORENSIC
# ================================================================================================

def inspect_zip_for_report(zip_path: Path) -> list[dict]:
    matches = []

    try:
        with zipfile.ZipFile(zip_path, "r") as z:

            for info in z.infolist():

                filename = Path(info.filename).name

                name_score = 0

                if filename == TARGET_REPORT:
                    name_score += 100

                upper = filename.upper()

                for fragment in REPORT_NAME_FRAGMENTS:
                    if fragment.upper() in upper:
                        name_score += 10

                if name_score <= 0:
                    continue

                matches.append({
                    "archive": str(zip_path),
                    "member": info.filename,
                    "member_size": info.file_size,
                    "name_score": name_score,
                    "crc": info.CRC,
                })

    except Exception as exc:
        matches.append({
            "archive": str(zip_path),
            "error": repr(exc),
        })

    return matches


def discover_archives(files: list[Path]) -> list[dict]:
    archives = []

    for path in files:

        if path.suffix.lower() not in ARCHIVE_EXTENSIONS:
            continue

        matches = inspect_zip_for_report(path)

        if matches:
            archives.extend(matches)

    return archives


# ================================================================================================
# ARCHIVE EXACT RECOVERY
# ================================================================================================

def extract_zip_member_to_isolated_stage(
    archive_path: Path,
    member_name: str,
    stage_dir: Path,
) -> Path | None:

    try:
        with zipfile.ZipFile(archive_path, "r") as z:

            info = z.getinfo(member_name)

            if Path(member_name).name != TARGET_REPORT:
                return None

            destination = stage_dir / TARGET_REPORT

            with z.open(info, "r") as source:
                with destination.open("wb") as target:
                    shutil.copyfileobj(source, target)

            return destination

    except Exception as exc:
        print(f"Archive recovery failed: {archive_path}")
        print(f"Reason: {exc}")
        return None


# ================================================================================================
# ISOLATED RECOVERY STAGING
# ================================================================================================

def create_isolated_stage() -> Path:
    return Path(
        tempfile.mkdtemp(
            prefix=RECOVERY_PREFIX
        )
    )


def stage_exact_artifact(
    source: Path,
    stage_dir: Path,
) -> dict:

    destination = stage_dir / TARGET_REPORT

    source_hash_before = sha256_file(source)

    shutil.copy2(source, destination)

    staged_hash = sha256_file(destination)

    return {
        "source": str(source),
        "destination": str(destination),
        "source_sha256": source_hash_before,
        "staged_sha256": staged_hash,
        "hash_match": source_hash_before == staged_hash,
        "source_modified": False,
    }


# ================================================================================================
# PRODUCER FORENSIC CHECK
# ================================================================================================

def inspect_producer(files: list[Path]) -> dict:

    producer = BASE_DIR / TARGET_PRODUCER

    result = {
        "exists": producer.exists(),
        "path": str(producer),
        "sha256": None,
        "report_write_reference_detected": False,
        "report_name_reference_count": 0,
    }

    if not producer.exists():
        return result

    result["sha256"] = sha256_file(producer)

    try:
        text = producer.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        result["report_name_reference_count"] = text.count(
            TARGET_REPORT
        )

        # We deliberately do NOT execute the producer.
        # This is source-text provenance only.

        write_markers = (
            ".write_text",
            ".write_bytes",
            "open(",
            "json.dump",
            "json.dumps",
        )

        for marker in write_markers:
            if marker in text and TARGET_REPORT in text:
                result["report_write_reference_detected"] = True
                break

    except Exception as exc:
        result["error"] = repr(exc)

    return result


# ================================================================================================
# FILE IDENTITY COMPARISON
# ================================================================================================

def compare_candidate_to_exact_schema(
    candidate_path: Path,
) -> dict:

    result = {
        "path": str(candidate_path),
        "exact_filename": candidate_path.name == TARGET_REPORT,
        "json_valid": False,
        "schema_score": 0,
        "sha256": None,
    }

    try:
        inspected = inspect_json_artifact(candidate_path)

        result["json_valid"] = inspected["json_valid"]
        result["schema_score"] = inspected["schema_score"]
        result["sha256"] = inspected["sha256"]

    except Exception as exc:
        result["error"] = repr(exc)

    return result


# ================================================================================================
# DECISION ENGINE
# ================================================================================================

def resolve_recovery(
    exact_matches: list[dict],
    name_candidates: list[dict],
    archive_candidates: list[dict],
) -> dict:

    decision = {
        "status": "NOT_RESOLVED",
        "method": None,
        "source": None,
        "reason": None,
    }

    # --------------------------------------------------------------------------------------------
    # CASE 1: Exact historical artifact exists.
    # --------------------------------------------------------------------------------------------

    valid_exact = [
        x for x in exact_matches
        if x.get("json_valid")
    ]

    if len(valid_exact) == 1:

        decision["status"] = "RESOLVED"
        decision["method"] = "EXACT_FILENAME_SINGLE_ARTIFACT"
        decision["source"] = valid_exact[0]["path"]
        decision["reason"] = (
            "Exactly one existing artifact matches the required filename "
            "and contains valid JSON."
        )

        return decision

    if len(valid_exact) > 1:

        # Multiple exact artifacts are NOT automatically considered equivalent.
        hashes = {
            x.get("sha256")
            for x in valid_exact
        }

        if len(hashes) == 1:

            decision["status"] = "RESOLVED"
            decision["method"] = "EXACT_FILENAME_IDENTICAL_HASH"
            decision["source"] = valid_exact[0]["path"]
            decision["reason"] = (
                "Multiple exact-name artifacts exist but all valid copies "
                "have identical SHA256."
            )

            return decision

        decision["status"] = "AMBIGUOUS"
        decision["method"] = "MULTIPLE_EXACT_ARTIFACTS_DIFFERENT_HASH"
        decision["reason"] = (
            "Multiple exact-name artifacts exist with different hashes. "
            "No artifact may be selected automatically."
        )

        return decision

    # --------------------------------------------------------------------------------------------
    # CASE 2: Historical archive contains exact report member.
    # --------------------------------------------------------------------------------------------

    archive_exact = [
        x for x in archive_candidates
        if Path(x.get("member", "")).name == TARGET_REPORT
    ]

    if len(archive_exact) == 1:

        decision["status"] = "RESOLVED_ARCHIVE"
        decision["method"] = "EXACT_ARCHIVE_MEMBER"
        decision["source"] = (
            archive_exact[0]["archive"],
            archive_exact[0]["member"],
        )
        decision["reason"] = (
            "The exact historical report exists as an archive member."
        )

        return decision

    if len(archive_exact) > 1:

        decision["status"] = "AMBIGUOUS"
        decision["method"] = "MULTIPLE_ARCHIVE_EXACT_MEMBERS"
        decision["reason"] = (
            "Multiple archives contain the exact target report. "
            "No historical copy may be selected automatically."
        )

        return decision

    # --------------------------------------------------------------------------------------------
    # CASE 3: Renamed/copy candidates.
    # --------------------------------------------------------------------------------------------

    strong_candidates = [
        x for x in name_candidates
        if x.get("json_valid")
        and x.get("schema_score", 0) >= 40
    ]

    if len(strong_candidates) == 1:

        decision["status"] = "PROVISIONAL"
        decision["method"] = "RENAMED_SCHEMA_MATCH"
        decision["source"] = strong_candidates[0]["path"]
        decision["reason"] = (
            "One renamed/copied JSON artifact strongly resembles the "
            "required report schema, but exact historical identity is "
            "not cryptographically established."
        )

        return decision

    if len(strong_candidates) > 1:

        decision["status"] = "AMBIGUOUS"
        decision["method"] = "MULTIPLE_RENAMED_SCHEMA_MATCHES"
        decision["reason"] = (
            "Multiple renamed/copied artifacts resemble the required "
            "report. Exact provenance cannot be established."
        )

        return decision

    # --------------------------------------------------------------------------------------------
    # CASE 4: Nothing recoverable.
    # --------------------------------------------------------------------------------------------

    decision["status"] = "NOT_FOUND"
    decision["method"] = "FORENSIC_SEARCH_EXHAUSTED"
    decision["reason"] = (
        "No exact historical artifact, exact archive member, or "
        "sufficiently strong renamed artifact was found."
    )

    return decision


# ================================================================================================
# REPORT WRITER
# ================================================================================================

def write_forensic_report(
    result: dict,
    stage_dir: Path | None,
) -> Path:

    # This report is NOT the eligibility report.
    # It is the forensic audit output of THIS script.

    output_path = BASE_DIR / (
        "HISTORICAL_ELIGIBILITY_ARTIFACT_PROVENANCE_RECOVERY_FORENSIC_REPORT.json"
    )

    report = dict(result)

    report["forensic_report"] = str(output_path)

    if stage_dir is not None:
        report["isolated_recovery_stage"] = str(stage_dir)

    # Only this forensic report is written by this script.
    # It is not the target eligibility artifact.

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return output_path


# ================================================================================================
# MAIN
# ================================================================================================

def main() -> int:

    start = time.perf_counter()

    banner(
        "ARUNDA TRADER\n"
        "HISTORICAL ELIGIBILITY ARTIFACT PROVENANCE / RECOVERY FORENSIC v0.1"
    )

    section("OBJECTIVE")

    print(
        "Locate and provenance the historical verified eligibility artifact:"
    )
    print(f"  {TARGET_REPORT}")
    print()
    print("No producer execution.")
    print("No eligibility reconstruction.")
    print("No report regeneration.")
    print("No synthetic artifact.")
    print("Only isolated recovery staging is permitted.")

    section("SAFETY POLICY")

    safe_print("Production DB writes", "FORBIDDEN")
    safe_print("Production source modification", "FORBIDDEN")
    safe_print("Eligibility execution", "FORBIDDEN")
    safe_print("Eligibility rebuild", "FORBIDDEN")
    safe_print("Report regeneration", "FORBIDDEN")
    safe_print("Synthetic report", "FORBIDDEN")
    safe_print("Network access", "FORBIDDEN")
    safe_print("Recovery staging", "ISOLATED ONLY")

    section("BASELINE")

    safe_print("Project root", BASE_DIR)
    safe_print("Target report", TARGET_REPORT)
    safe_print("Producer", TARGET_PRODUCER)
    safe_print("Consumer", TARGET_CONSUMER)

    if not BASE_DIR.exists():
        raise RuntimeError(
            f"Project root does not exist: {BASE_DIR}"
        )

    section("PRODUCER FORENSIC")

    producer_info = inspect_producer([])

    safe_print(
        "Producer exists",
        producer_info.get("exists"),
    )

    safe_print(
        "Producer SHA256",
        producer_info.get("sha256"),
    )

    safe_print(
        "Report reference count",
        producer_info.get("report_name_reference_count"),
    )

    safe_print(
        "Write reference detected",
        producer_info.get("report_write_reference_detected"),
    )

    RESULT["producer"] = producer_info

    section("FILESYSTEM INVENTORY")

    print("Scanning project tree in READ-ONLY mode...")

    files = discover_files()

    safe_print(
        "Files discovered",
        len(files),
    )

    RESULT["filesystem_files_discovered"] = len(files)

    section("EXACT ARTIFACT DISCOVERY")

    exact_matches = discover_exact_reports(files)

    RESULT["exact_matches"] = exact_matches

    safe_print(
        "Exact report files found",
        len(exact_matches),
    )

    for index, item in enumerate(exact_matches, 1):

        print(
            f"{index:>3} | "
            f"{item.get('path')} | "
            f"valid_json={item.get('json_valid')} | "
            f"sha256={item.get('sha256')}"
        )

    section("RENAMED / COPIED ARTIFACT FORENSIC")

    name_candidates = discover_name_candidates(files)

    RESULT["candidates"] = name_candidates[:100]

    safe_print(
        "Name/schema candidates",
        len(name_candidates),
    )

    for index, item in enumerate(name_candidates[:30], 1):

        print(
            f"{index:>3} | "
            f"score={item.get('score', 0):>3} | "
            f"schema={item.get('schema_score', 0):>3} | "
            f"{item.get('path')}"
        )

    section("CONTENT PROVENANCE SEARCH")

    content_candidates = discover_content_candidates(files)

    RESULT["content_candidates"] = content_candidates[:100]

    safe_print(
        "Content candidates",
        len(content_candidates),
    )

    for index, item in enumerate(content_candidates[:30], 1):

        print(
            f"{index:>3} | "
            f"score={item.get('score', 0):>3} | "
            f"{item.get('path')}"
        )

    section("HISTORICAL ARCHIVE FORENSIC")

    archive_candidates = discover_archives(files)

    RESULT["archive_candidates"] = archive_candidates

    safe_print(
        "Archive report candidates",
        len(archive_candidates),
    )

    for index, item in enumerate(archive_candidates, 1):

        print(
            f"{index:>3} | "
            f"{item.get('archive')} :: "
            f"{item.get('member')}"
        )

    section("RECOVERY DECISION")

    decision = resolve_recovery(
        exact_matches,
        name_candidates,
        archive_candidates,
    )

    RESULT["recovery_decision"] = decision

    safe_print(
        "STATUS",
        decision["status"],
    )

    safe_print(
        "METHOD",
        decision["method"],
    )

    safe_print(
        "REASON",
        decision["reason"],
    )

    stage_dir = None

    # ============================================================================================
    # EXACT RECOVERY
    # ============================================================================================

    if decision["status"] == "RESOLVED":

        source = Path(decision["source"])

        section("ISOLATED RECOVERY STAGING")

        stage_dir = create_isolated_stage()

        staged = stage_exact_artifact(
            source,
            stage_dir,
        )

        RESULT["recovery_staged"].append(staged)

        safe_print(
            "Recovery source",
            source,
        )

        safe_print(
            "Recovery destination",
            staged["destination"],
        )

        safe_print(
            "SHA256 match",
            staged["hash_match"],
        )

        if not staged["hash_match"]:
            raise RuntimeError(
                "CRITICAL: staged artifact SHA256 does not match source."
            )

    elif decision["status"] == "RESOLVED_ARCHIVE":

        archive_path, member_name = decision["source"]

        section("ISOLATED ARCHIVE RECOVERY STAGING")

        stage_dir = create_isolated_stage()

        recovered = extract_zip_member_to_isolated_stage(
            Path(archive_path),
            member_name,
            stage_dir,
        )

        if recovered is None:
            raise RuntimeError(
                "Archive contained target member but isolated recovery failed."
            )

        inspected = inspect_json_artifact(recovered)

        RESULT["recovery_staged"].append({
            "archive": archive_path,
            "member": member_name,
            "destination": str(recovered),
            "sha256": inspected.get("sha256"),
            "json_valid": inspected.get("json_valid"),
            "schema_score": inspected.get("schema_score"),
        })

        safe_print(
            "Archive",
            archive_path,
        )

        safe_print(
            "Member",
            member_name,
        )

        safe_print(
            "Recovered destination",
            recovered,
        )

        safe_print(
            "Recovered SHA256",
            inspected.get("sha256"),
        )

    else:

        section("RECOVERY STAGING")

        print(
            "No sufficiently proven exact historical artifact was resolved."
        )
        print(
            "Nothing was staged."
        )

    # ============================================================================================
    # FINAL VERDICT
    # ============================================================================================

    elapsed = time.perf_counter() - start

    if decision["status"] in {
        "RESOLVED",
        "RESOLVED_ARCHIVE",
    }:

        RESULT["verdict"] = "HISTORICAL_ARTIFACT_RECOVERED_TO_ISOLATED_STAGE"

    elif decision["status"] == "AMBIGUOUS":

        RESULT["verdict"] = "BLOCKED_AMBIGUOUS_HISTORICAL_PROVENANCE"

    elif decision["status"] == "PROVISIONAL":

        RESULT["verdict"] = "BLOCKED_PROVISIONAL_MATCH_NOT_EXACT"

    else:

        RESULT["verdict"] = "HISTORICAL_ARTIFACT_NOT_FOUND"

    RESULT["runtime_seconds"] = round(elapsed, 6)

    RESULT["production_source_modified"] = False
    RESULT["production_db_modified"] = False
    RESULT["network_access"] = False
    RESULT["eligibility_executed"] = False
    RESULT["report_reconstructed"] = False
    RESULT["synthetic_report_created"] = False
    RESULT["candidate_created"] = False

    section("FINAL VERDICT")

    safe_print(
        "HISTORICAL ARTIFACT PROVENANCE",
        RESULT["verdict"],
    )

    safe_print(
        "Exact report recovered",
        (
            "YES"
            if RESULT["recovery_staged"]
            else "NO"
        ),
    )

    safe_print(
        "Eligibility executed",
        "NO",
    )

    safe_print(
        "Eligibility rebuilt",
        "NO",
    )

    safe_print(
        "Synthetic report",
        "NO",
    )

    safe_print(
        "Production DB writes",
        "NONE",
    )

    safe_print(
        "Production source modification",
        "NONE",
    )

    safe_print(
        "Network access",
        "NONE",
    )

    if stage_dir is not None:

        safe_print(
            "Isolated recovery stage",
            stage_dir,
        )

    # ============================================================================================
    # FORENSIC REPORT
    # ============================================================================================

    report_path = write_forensic_report(
        RESULT,
        stage_dir,
    )

    print()
    safe_print(
        "Forensic report",
        report_path,
    )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())

    except KeyboardInterrupt:
        print("\nFORENSIC EXECUTION INTERRUPTED.")
        sys.exit(130)

    except Exception as exc:
        print()
        print("=" * 100)
        print("FORENSIC EXECUTION ERROR")
        print("=" * 100)
        print(repr(exc))
        print("=" * 100)
        sys.exit(1)