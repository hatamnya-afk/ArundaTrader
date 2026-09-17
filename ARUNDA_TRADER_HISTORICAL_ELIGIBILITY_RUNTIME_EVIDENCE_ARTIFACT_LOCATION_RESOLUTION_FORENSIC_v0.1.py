import os
import json
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SCRIPT_NAME = (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_"
    "ARTIFACT_LOCATION_RESOLUTION_FORENSIC_v0.1.py"
)

REPORT_NAME = (
    "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_"
    "ARTIFACT_LOCATION_RESOLUTION_FORENSIC_REPORT.json"
)

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

PRODUCER = "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"

CONSUMER = "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"

REPORT_PATH = PROJECT_ROOT / REPORT_NAME


TEXT_EXTENSIONS = {
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
}

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".7z",
}

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_read_text(path, limit=2_000_000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except Exception:
        return ""


def sha256_file(path):
    h = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return None


def discover_files():
    files = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        for name in filenames:
            try:
                files.append(Path(root) / name)
            except Exception:
                pass

    return files


def normalize(text):
    return " ".join(
        str(text).lower().replace("\\", "/").split()
    )


def score_location_candidate(path, content):
    name = path.name.lower()
    text = content.lower()

    score = 0
    reasons = []

    exact_target = TARGET_REPORT.lower()

    if name == exact_target:
        score += 1000
        reasons.append("exact_target_filename")

    keywords = {
        "live_signal_eligibility": 45,
        "no_trade": 40,
        "eligibility": 30,
        "runtime": 25,
        "artifact": 25,
        "report": 20,
        "capture": 20,
        "historical": 15,
        "producer": 15,
        "output": 10,
        "json": 5,
    }

    for keyword, weight in keywords.items():

        if keyword in name:
            score += weight
            reasons.append(f"name:{keyword}")

        if keyword in text:
            score += min(weight, 15)
            reasons.append(f"content:{keyword}")

    producer_refs = [
        PRODUCER.lower(),
        "arunda_trader_live_signal_eligibility_no_trade_gate",
    ]

    consumer_refs = [
        CONSUMER.lower(),
        "arunda_trader_live_trade_candidate_ranking_multi_asset_gate",
    ]

    for ref in producer_refs:
        if ref in text:
            score += 25
            reasons.append("producer_reference")

    for ref in consumer_refs:
        if ref in text:
            score += 20
            reasons.append("consumer_reference")

    target_refs = [
        TARGET_REPORT.lower(),
        "live_signal_eligibility_no_trade_report",
    ]

    for ref in target_refs:
        if ref in text:
            score += 50
            reasons.append("target_report_reference")

    runtime_terms = [
        "runtime",
        "executed",
        "invoked",
        "output",
        "artifact",
        "write",
        "report_path",
        "output_path",
        "json_path",
        "save",
        "dump",
    ]

    runtime_hits = 0

    for term in runtime_terms:
        if term in text:
            runtime_hits += 1

    score += runtime_hits * 4

    if runtime_hits:
        reasons.append(f"runtime_terms:{runtime_hits}")

    return score, sorted(set(reasons))


def extract_path_candidates(content):
    candidates = []

    lines = content.splitlines()

    for line_number, line in enumerate(lines, start=1):

        stripped = line.strip()

        if not stripped:
            continue

        lowered = stripped.lower()

        interesting = (
            "report" in lowered
            or "artifact" in lowered
            or "output" in lowered
            or "path" in lowered
            or TARGET_REPORT.lower() in lowered
            or "json" in lowered
        )

        if not interesting:
            continue

        candidates.append({
            "line_number": line_number,
            "line": stripped[:1000],
        })

    return candidates


def inspect_archive(path):
    result = {
        "path": str(path),
        "target_member": False,
        "producer_member": False,
        "runtime_members": [],
        "members_checked": 0,
        "error": None,
    }

    try:
        with zipfile.ZipFile(path, "r") as z:

            names = z.namelist()

            result["members_checked"] = len(names)

            for member in names:

                lower = member.lower()

                if lower.endswith(TARGET_REPORT.lower()):
                    result["target_member"] = True

                if PRODUCER.lower() in lower:
                    result["producer_member"] = True

                runtime_terms = [
                    "eligibility",
                    "runtime",
                    "artifact",
                    "capture",
                    "report",
                    "output",
                ]

                if any(term in lower for term in runtime_terms):
                    result["runtime_members"].append(member)

    except Exception as exc:
        result["error"] = repr(exc)

    return result


def classify_candidate(path, score, reasons):
    name = path.name.lower()

    if name == TARGET_REPORT.lower():
        return "EXACT_TARGET"

    if "report" in name and path.suffix.lower() == ".json":
        return "REPORT_EVIDENCE"

    if "artifact" in name:
        return "ARTIFACT_EVIDENCE"

    if "runtime" in name:
        return "RUNTIME_EVIDENCE"

    if "producer" in name:
        return "PRODUCER_EVIDENCE"

    if "eligibility" in name:
        return "ELIGIBILITY_EVIDENCE"

    if score >= 100:
        return "STRONG_SOURCE_MAPPING"

    if score >= 50:
        return "SOURCE_TRACE"

    return "WEAK_REFERENCE"


def main():

    started = utc_now()

    print("=" * 100)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE ARTIFACT LOCATION RESOLUTION FORENSIC v0.1")
    print("=" * 100)
    print(f"MODE                         : READ-ONLY FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"TARGET REPORT                : {TARGET_REPORT}")
    print(f"PRODUCER                     : {PRODUCER}")
    print(f"CONSUMER                     : {CONSUMER}")

    files = discover_files()

    exact_targets = []
    text_candidates = []
    archives = []

    for path in files:

        if path.name.lower() == TARGET_REPORT.lower():
            exact_targets.append(path)

        if path.suffix.lower() in TEXT_EXTENSIONS:
            text_candidates.append(path)

        if path.suffix.lower() in ARCHIVE_EXTENSIONS:
            archives.append(path)

    print("=" * 100)
    print("FILESYSTEM INVENTORY")
    print("=" * 100)
    print(f"Files discovered              : {len(files)}")
    print(f"Exact target files found      : {len(exact_targets)}")

    candidates = []

    for path in text_candidates:

        content = safe_read_text(path)

        if not content:
            continue

        score, reasons = score_location_candidate(
            path,
            content,
        )

        if score <= 0:
            continue

        path_refs = extract_path_candidates(content)

        candidates.append({
            "path": str(path),
            "filename": path.name,
            "score": score,
            "classification": classify_candidate(
                path,
                score,
                reasons,
            ),
            "reasons": reasons,
            "path_reference_count": len(path_refs),
            "path_references": path_refs[:30],
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size
            if path.exists()
            else None,
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["path_reference_count"],
        ),
        reverse=True,
    )

    print("=" * 100)
    print("ARTIFACT LOCATION CANDIDATES")
    print("=" * 100)
    print(
        f"Location resolution candidates : "
        f"{len(candidates)}"
    )

    for idx, item in enumerate(candidates[:30], start=1):

        print(
            f"{idx:>3} | "
            f"score={item['score']:>3} | "
            f"class={item['classification']:<24} | "
            f"path_refs={item['path_reference_count']:>3} | "
            f"{item['path']}"
        )

    archive_results = []

    for archive in archives:

        result = inspect_archive(archive)

        archive_results.append(result)

    print("=" * 100)
    print("ARCHIVE FORENSIC")
    print("=" * 100)
    print(f"Archives inspected             : {len(archive_results)}")

    archive_target = any(
        item["target_member"]
        for item in archive_results
    )

    archive_producer = any(
        item["producer_member"]
        for item in archive_results
    )

    runtime_archive_members = []

    for item in archive_results:
        runtime_archive_members.extend(
            item["runtime_members"]
        )

    print(
        f"Archive target artifact        : "
        f"{archive_target}"
    )

    print(
        f"Archive producer present       : "
        f"{archive_producer}"
    )

    print(
        f"Runtime archive members         : "
        f"{len(runtime_archive_members)}"
    )

    exact_recovered = len(exact_targets) > 0 or archive_target

    strong_candidates = [
        item for item in candidates
        if item["score"] >= 100
    ]

    location_resolved = (
        exact_recovered
        or len(strong_candidates) > 0
    )

    if exact_recovered:
        status = "EXACT_ARTIFACT_LOCATION_CONFIRMED"
    elif location_resolved:
        status = (
            "ARTIFACT_LOCATION_RESOLUTION_FOUND_"
            "ARTIFACT_UNRECOVERED"
        )
    else:
        status = "ARTIFACT_LOCATION_UNRESOLVED"

    print("=" * 100)
    print("LOCATION RESOLUTION DECISION")
    print("=" * 100)
    print(f"STATUS                       : {status}")
    print(
        f"EXACT ARTIFACT RECOVERED    : "
        f"{exact_recovered}"
    )
    print(
        f"LOCATION RESOLUTION FOUND   : "
        f"{location_resolved}"
    )

    safety = {
        "producer_executed": False,
        "producer_imported": False,
        "eligibility_executed": False,
        "eligibility_rebuilt": False,
        "report_regenerated": False,
        "synthetic_artifact": False,
        "production_db_writes": "NONE",
        "production_source_modified": False,
        "network_access": False,
        "artifact_extraction_executed": False,
        "recovery_staging": False,
        "source_modification": False,
        "runtime_execution": False,
    }

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print(
        f"Producer executed            : "
        f"{'YES' if safety['producer_executed'] else 'NO'}"
    )

    print(
        f"Producer imported            : "
        f"{'YES' if safety['producer_imported'] else 'NO'}"
    )

    print(
        f"Eligibility executed         : "
        f"{'YES' if safety['eligibility_executed'] else 'NO'}"
    )

    print(
        f"Eligibility rebuilt          : "
        f"{'YES' if safety['eligibility_rebuilt'] else 'NO'}"
    )

    print(
        f"Report regenerated           : "
        f"{'YES' if safety['report_regenerated'] else 'NO'}"
    )

    print(
        f"Synthetic artifact           : "
        f"{'YES' if safety['synthetic_artifact'] else 'NO'}"
    )

    print(
        f"Production DB writes         : "
        f"{safety['production_db_writes']}"
    )

    print(
        f"Production source modified   : "
        f"{'YES' if safety['production_source_modified'] else 'NO'}"
    )

    print(
        f"Network access               : "
        f"{'YES' if safety['network_access'] else 'NO'}"
    )

    print(
        f"Artifact extraction executed : "
        f"{'YES' if safety['artifact_extraction_executed'] else 'NO'}"
    )

    print(
        f"Recovery staging             : "
        f"{'YES' if safety['recovery_staging'] else 'NO'}"
    )

    print(
        f"Source modification          : "
        f"{'YES' if safety['source_modification'] else 'NO'}"
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        f"HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        f"{status}"
    )
    print(
        f"FORENSIC REPORT              : "
        f"{REPORT_PATH}"
    )
    print("=" * 100)

    report = {
        "metadata": {
            "project": "ArundaTrader",
            "stage": (
                "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_"
                "ARTIFACT_LOCATION_RESOLUTION_FORENSIC"
            ),
            "version": "v0.1",
            "mode": "READ-ONLY FORENSIC",
            "script": SCRIPT_NAME,
            "started_at_utc": started,
            "completed_at_utc": utc_now(),
        },

        "scope": {
            "project_root": str(PROJECT_ROOT),
            "target_report": TARGET_REPORT,
            "producer": PRODUCER,
            "consumer": CONSUMER,
        },

        "filesystem_inventory": {
            "files_discovered": len(files),
            "exact_target_files": [
                str(p)
                for p in exact_targets
            ],
            "exact_target_count": len(exact_targets),
        },

        "location_resolution": {
            "status": status,
            "exact_artifact_recovered": exact_recovered,
            "location_resolution_found": location_resolved,
            "candidate_count": len(candidates),
            "strong_candidate_count": len(strong_candidates),
            "top_candidates": candidates[:50],
        },

        "archive_forensic": {
            "archives_inspected": len(archive_results),
            "archive_target_artifact": archive_target,
            "archive_producer_present": archive_producer,
            "runtime_archive_member_count": len(
                runtime_archive_members
            ),
            "archives": archive_results,
        },

        "safety": safety,

        "forensic_constraints": {
            "producer_not_executed": True,
            "producer_not_imported": True,
            "eligibility_not_executed": True,
            "report_not_regenerated": True,
            "no_synthetic_artifact_created": True,
            "no_production_db_writes": True,
            "no_production_source_modification": True,
            "no_network_access": True,
            "no_artifact_extraction": True,
            "no_recovery_staging": True,
        },

        "final_verdict": {
            "status": status,
            "target_artifact_present": exact_recovered,
            "artifact_location_resolved": location_resolved,
            "artifact_recovered": exact_recovered,
        },
    }

    try:
        with open(
            REPORT_PATH,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                report,
                f,
                ensure_ascii=False,
                indent=2,
            )

    except Exception as exc:

        print(
            f"REPORT WRITE ERROR: {repr(exc)}"
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())