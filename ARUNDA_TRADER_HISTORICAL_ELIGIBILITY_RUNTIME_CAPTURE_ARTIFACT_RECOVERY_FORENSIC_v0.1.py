import os
import json
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY RUNTIME CAPTURE ARTIFACT RECOVERY FORENSIC v0.1
# =============================================================================

MODE = "READ-ONLY FORENSIC"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER_NAME = (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET_REPORT_NAME = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

CONSUMER_NAME = (
    "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "HISTORICAL_ELIGIBILITY_RUNTIME_CAPTURE_ARTIFACT_RECOVERY_FORENSIC_REPORT.json"
)

RUNTIME_TERMS = [
    "stdout",
    "stderr",
    "runtime",
    "execution",
    "executed",
    "invocation",
    "launch",
    "entrypoint",
    "working directory",
    "cwd",
    "output",
    "report",
    "capture",
    "isolated",
    "subprocess",
    "returncode",
    "exit code",
]

PRODUCER_TERMS = [
    PRODUCER_NAME,
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1",
    "ELIGIBILITY_NO_TRADE",
    "SIGNAL_ELIGIBILITY",
]

REPORT_TERMS = [
    TARGET_REPORT_NAME,
    "eligibility_report",
    "eligible_pool",
    "UPSTREAM_ELIGIBILITY_CONSUMED",
]


# =============================================================================
# SAFETY
# =============================================================================

def assert_safe_environment():
    if not PROJECT_ROOT.exists():
        raise RuntimeError(f"Project root does not exist: {PROJECT_ROOT}")

    if not PROJECT_ROOT.is_dir():
        raise RuntimeError(f"Project root is not a directory: {PROJECT_ROOT}")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# HASH
# =============================================================================

def sha256_file(path: Path):
    h = hashlib.sha256()

    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)

        return h.hexdigest()

    except Exception as exc:
        return f"ERROR:{type(exc).__name__}:{exc}"


# =============================================================================
# TEXT EXTRACTION
# =============================================================================

def safe_read_text(path: Path, max_bytes=5_000_000):
    try:
        if path.stat().st_size > max_bytes:
            return None

        raw = path.read_bytes()

        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding, errors="replace")
            except Exception:
                pass

    except Exception:
        return None

    return None


# =============================================================================
# FILE INVENTORY
# =============================================================================

def inventory_files():
    files = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        # Never descend into obvious generated/cache areas.
        dirs[:] = [
            d for d in dirs
            if d not in {
                "__pycache__",
                ".git",
                ".venv",
                "venv",
                "node_modules",
            }
        ]

        for filename in filenames:
            path = root_path / filename

            try:
                stat = path.stat()

                files.append({
                    "path": str(path),
                    "name": filename,
                    "suffix": path.suffix.lower(),
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(
                        stat.st_mtime,
                        timezone.utc
                    ).isoformat(),
                })

            except Exception:
                continue

    return files


# =============================================================================
# EXACT ARTIFACT DISCOVERY
# =============================================================================

def find_exact_reports(files):
    matches = []

    for item in files:
        if item["name"] == TARGET_REPORT_NAME:
            matches.append(item)

    return matches


# =============================================================================
# ARCHIVE DISCOVERY
# =============================================================================

def discover_archives(files):
    archives = []

    for item in files:
        if item["suffix"] in {".zip", ".tar", ".gz", ".7z"}:
            archives.append(item)

    return archives


# =============================================================================
# ZIP FORENSIC
# =============================================================================

def inspect_zip_archive(path: Path):
    result = {
        "archive": str(path),
        "readable": False,
        "target_members": [],
        "producer_members": [],
        "runtime_related_members": [],
        "errors": [],
    }

    try:
        with zipfile.ZipFile(path, "r") as z:
            result["readable"] = True

            for info in z.infolist():
                name = info.filename

                lower = name.lower()

                if TARGET_REPORT_NAME.lower() in lower:
                    result["target_members"].append({
                        "name": name,
                        "size": info.file_size,
                        "date_time": info.date_time,
                    })

                if PRODUCER_NAME.lower() in lower:
                    result["producer_members"].append({
                        "name": name,
                        "size": info.file_size,
                        "date_time": info.date_time,
                    })

                runtime_hits = [
                    term for term in RUNTIME_TERMS
                    if term.lower() in lower
                ]

                if runtime_hits:
                    result["runtime_related_members"].append({
                        "name": name,
                        "size": info.file_size,
                        "date_time": info.date_time,
                        "terms": runtime_hits,
                    })

    except Exception as exc:
        result["errors"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


# =============================================================================
# CONTENT FORENSIC
# =============================================================================

def content_forensic(files):
    candidates = []

    searchable_suffixes = {
        ".py",
        ".json",
        ".txt",
        ".log",
        ".md",
        ".csv",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".xml",
    }

    for item in files:

        if item["suffix"] not in searchable_suffixes:
            continue

        path = Path(item["path"])

        text = safe_read_text(path)

        if text is None:
            continue

        lower = text.lower()

        producer_hits = [
            term
            for term in PRODUCER_TERMS
            if term.lower() in lower
        ]

        report_hits = [
            term
            for term in REPORT_TERMS
            if term.lower() in lower
        ]

        runtime_hits = [
            term
            for term in RUNTIME_TERMS
            if term.lower() in lower
        ]

        if not producer_hits and not report_hits:
            continue

        score = (
            len(producer_hits) * 25
            + len(report_hits) * 20
            + len(runtime_hits) * 5
        )

        candidates.append({
            "path": str(path),
            "score": score,
            "producer_reference": bool(producer_hits),
            "report_reference": bool(report_hits),
            "producer_terms": producer_hits,
            "report_terms": report_hits,
            "runtime_terms": runtime_hits,
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["producer_reference"],
            x["report_reference"],
        ),
        reverse=True,
    )

    return candidates


# =============================================================================
# RUNTIME CAPTURE FORENSIC
# =============================================================================

def runtime_capture_forensic(files):
    candidates = []

    for item in files:

        if item["suffix"] not in {
            ".py",
            ".json",
            ".txt",
            ".log",
            ".md",
        }:
            continue

        path = Path(item["path"])

        text = safe_read_text(path)

        if text is None:
            continue

        lower = text.lower()

        producer_ref = any(
            term.lower() in lower
            for term in PRODUCER_TERMS
        )

        report_ref = any(
            term.lower() in lower
            for term in REPORT_TERMS
        )

        if not producer_ref and not report_ref:
            continue

        runtime_hits = [
            term
            for term in RUNTIME_TERMS
            if term.lower() in lower
        ]

        if len(runtime_hits) < 2:
            continue

        score = (
            len(runtime_hits) * 8
            + (35 if producer_ref else 0)
            + (35 if report_ref else 0)
        )

        candidates.append({
            "path": str(path),
            "score": score,
            "producer_reference": producer_ref,
            "report_reference": report_ref,
            "runtime_terms": runtime_hits,
        })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates


# =============================================================================
# JSON FORENSIC
# =============================================================================

def json_forensic(files):
    candidates = []

    for item in files:

        if item["suffix"] != ".json":
            continue

        path = Path(item["path"])

        text = safe_read_text(path)

        if text is None:
            continue

        try:
            data = json.loads(text)
        except Exception:
            continue

        blob = json.dumps(
            data,
            ensure_ascii=False
        ).lower()

        producer_ref = any(
            term.lower() in blob
            for term in PRODUCER_TERMS
        )

        report_ref = any(
            term.lower() in blob
            for term in REPORT_TERMS
        )

        runtime_ref = any(
            term.lower() in blob
            for term in RUNTIME_TERMS
        )

        if not (producer_ref or report_ref):
            continue

        keys = []

        if isinstance(data, dict):
            keys = list(data.keys())

        candidates.append({
            "path": str(path),
            "valid_json": True,
            "producer_reference": producer_ref,
            "report_reference": report_ref,
            "runtime_reference": runtime_ref,
            "top_level_keys": keys[:100],
        })

    return candidates


# =============================================================================
# TIMELINE FORENSIC
# =============================================================================

def timeline_candidates(
    files,
    producer_name,
    report_name,
    limit=50,
):
    results = []

    for item in files:

        path = Path(item["path"])

        if (
            producer_name.lower() not in item["name"].lower()
            and report_name.lower() not in item["name"].lower()
        ):
            continue

        results.append({
            "path": str(path),
            "mtime": item["mtime"],
            "producer_reference": (
                producer_name.lower()
                in item["name"].lower()
            ),
            "report_reference": (
                report_name.lower()
                in item["name"].lower()
            ),
        })

    results.sort(
        key=lambda x: x["mtime"],
        reverse=True,
    )

    return results[:limit]


# =============================================================================
# SOURCE INTEGRITY
# =============================================================================

def source_integrity(files):
    producer_path = PROJECT_ROOT / PRODUCER_NAME

    consumer_path = PROJECT_ROOT / CONSUMER_NAME

    result = {
        "producer_exists": producer_path.exists(),
        "consumer_exists": consumer_path.exists(),
        "producer_sha256": None,
        "consumer_sha256": None,
    }

    if producer_path.exists():
        result["producer_sha256"] = sha256_file(
            producer_path
        )

    if consumer_path.exists():
        result["consumer_sha256"] = sha256_file(
            consumer_path
        )

    return result


# =============================================================================
# RECOVERY DECISION
# =============================================================================

def decide_recovery(
    exact_reports,
    archive_results,
    runtime_candidates,
    json_candidates,
):
    exact_found = bool(exact_reports)

    archive_target_found = any(
        bool(x["target_members"])
        for x in archive_results
    )

    strong_runtime_reference = any(
        x["producer_reference"]
        and x["report_reference"]
        for x in runtime_candidates
    )

    strong_json_reference = any(
        x["producer_reference"]
        and x["report_reference"]
        for x in json_candidates
    )

    if exact_found:
        status = "EXACT_ARTIFACT_PRESENT"

    elif archive_target_found:
        status = "EXACT_ARCHIVE_ARTIFACT_PRESENT"

    elif strong_runtime_reference or strong_json_reference:
        status = (
            "RUNTIME_CAPTURE_PROVENANCE_FOUND_ARTIFACT_UNRECOVERED"
        )

    else:
        status = "RUNTIME_CAPTURE_ARTIFACT_NOT_FOUND"

    return {
        "status": status,
        "exact_artifact_present": exact_found,
        "exact_archive_artifact_present": archive_target_found,
        "runtime_provenance_reference": (
            strong_runtime_reference
        ),
        "json_provenance_reference": (
            strong_json_reference
        ),
        "artifact_recovered": (
            exact_found or archive_target_found
        ),
    }


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():
    assert_safe_environment()

    started_at = utc_now()

    files = inventory_files()

    exact_reports = find_exact_reports(files)

    archives = discover_archives(files)

    archive_results = []

    for item in archives:
        path = Path(item["path"])

        if path.suffix.lower() == ".zip":
            archive_results.append(
                inspect_zip_archive(path)
            )

    content_candidates = content_forensic(files)

    runtime_candidates = runtime_capture_forensic(files)

    json_candidates = json_forensic(files)

    timeline = timeline_candidates(
        files,
        PRODUCER_NAME,
        TARGET_REPORT_NAME,
    )

    integrity = source_integrity(files)

    decision = decide_recovery(
        exact_reports,
        archive_results,
        runtime_candidates,
        json_candidates,
    )

    finished_at = utc_now()

    report = {
        "forensic_identity": {
            "title": (
                "ARUNDA TRADER "
                "HISTORICAL ELIGIBILITY RUNTIME CAPTURE "
                "ARTIFACT RECOVERY FORENSIC v0.1"
            ),
            "mode": MODE,
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
        },

        "objective": {
            "target_artifact": TARGET_REPORT_NAME,
            "producer": PRODUCER_NAME,
            "consumer": CONSUMER_NAME,
            "purpose": (
                "Determine whether historical runtime capture "
                "provenance or recoverable historical artifact "
                "evidence exists."
            ),
        },

        "safety_policy": {
            "production_db_writes": "FORBIDDEN",
            "production_source_modification": "FORBIDDEN",
            "producer_execution": "FORBIDDEN",
            "producer_import": "FORBIDDEN",
            "eligibility_execution": "FORBIDDEN",
            "eligibility_reconstruction": "FORBIDDEN",
            "report_regeneration": "FORBIDDEN",
            "synthetic_artifact": "FORBIDDEN",
            "network_access": "FORBIDDEN",
            "recovery_staging": "ISOLATED ONLY",
        },

        "filesystem": {
            "project_root": str(PROJECT_ROOT),
            "files_discovered": len(files),
            "exact_report_files": exact_reports,
        },

        "source_integrity": integrity,

        "content_provenance": {
            "candidate_count": len(content_candidates),
            "candidates": content_candidates[:100],
        },

        "runtime_capture_provenance": {
            "candidate_count": len(runtime_candidates),
            "candidates": runtime_candidates[:100],
        },

        "json_provenance": {
            "candidate_count": len(json_candidates),
            "candidates": json_candidates[:100],
        },

        "archive_provenance": {
            "archives_inspected": len(archive_results),
            "archives": archive_results,
        },

        "timeline": {
            "candidate_count": len(timeline),
            "candidates": timeline,
        },

        "recovery_decision": decision,

        "recovery_staging": {
            "staged": False,
            "reason": (
                "No exact historical runtime capture artifact "
                "was copied or reconstructed. This forensic stage "
                "does not generate or rebuild eligibility reports."
            ),
            "staged_path": None,
        },

        "final_verdict": {
            "historical_runtime_capture_provenance": decision["status"],
            "exact_artifact_recovered": (
                decision["artifact_recovered"]
            ),
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "synthetic_artifact": False,
            "production_db_writes": "NONE",
            "production_source_modification": "NONE",
            "network_access": "NONE",
        },
    }

    # IMPORTANT:
    # The only write performed by this script is its own forensic report.
    # No production DB/source/report artifact is modified.

    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY RUNTIME CAPTURE "
        "ARTIFACT RECOVERY FORENSIC v0.1"
    )
    print("=" * 100)
    print(f"MODE                         : {MODE}")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"FILES DISCOVERED             : {len(files)}")
    print(
        f"EXACT TARGET FOUND           : "
        f"{len(exact_reports)}"
    )
    print(
        f"RUNTIME CANDIDATES           : "
        f"{len(runtime_candidates)}"
    )
    print(
        f"JSON PROVENANCE CANDIDATES  : "
        f"{len(json_candidates)}"
    )
    print(
        f"ARCHIVES INSPECTED           : "
        f"{len(archive_results)}"
    )
    print("=" * 100)
    print("RECOVERY DECISION")
    print("=" * 100)
    print(
        f"STATUS                       : "
        f"{decision['status']}"
    )
    print(
        f"EXACT ARTIFACT RECOVERED    : "
        f"{decision['artifact_recovered']}"
    )
    print(
        f"RUNTIME PROVENANCE FOUND    : "
        f"{decision['runtime_provenance_reference']}"
    )
    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed            : NO")
    print("Producer imported            : NO")
    print("Eligibility executed         : NO")
    print("Eligibility rebuilt         : NO")
    print("Report regenerated           : NO")
    print("Synthetic artifact           : NO")
    print("Production DB writes         : NONE")
    print("Production source modified   : NONE")
    print("Network access               : NONE")
    print("=" * 100)
    print(f"FORENSIC REPORT              : {OUTPUT_REPORT}")
    print("=" * 100)


if __name__ == "__main__":
    main()