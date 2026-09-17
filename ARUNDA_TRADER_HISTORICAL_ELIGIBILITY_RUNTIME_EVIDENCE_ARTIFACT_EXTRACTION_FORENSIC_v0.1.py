import os
import json
import hashlib
import zipfile
from datetime import datetime, timezone

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
PRODUCER = "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
CONSUMER = "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"

OUTPUT_REPORT = os.path.join(
    PROJECT_ROOT,
    "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_ARTIFACT_EXTRACTION_FORENSIC_REPORT.json"
)

SCRIPT_NAME = "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_ARTIFACT_EXTRACTION_FORENSIC_v0.1.py"

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

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
    "artifact",
    "evidence",
    "historical",
]

PROVENANCE_TERMS = [
    TARGET_REPORT,
    PRODUCER,
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE",
    "SIGNAL_ELIGIBILITY",
    "eligibility_report",
    "eligible_pool",
    "UPSTREAM_ELIGIBILITY_CONSUMED",
]


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def safe_read_text(path, limit=2_000_000):
    try:
        size = os.path.getsize(path)
        if size > limit:
            with open(path, "rb") as f:
                raw = f.read(limit)
        else:
            with open(path, "rb") as f:
                raw = f.read()

        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def is_candidate_file(path):
    name = os.path.basename(path).lower()

    if name == os.path.basename(OUTPUT_REPORT).lower():
        return False

    ext = os.path.splitext(name)[1]

    return (
        ext in TEXT_EXTENSIONS
        or name.endswith(".json")
        or name.endswith(".py")
    )


def walk_files():
    results = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in files:
            path = os.path.join(root, filename)

            if is_candidate_file(path):
                results.append(path)

    return results


def exact_artifact_search(files):
    matches = []

    target_lower = TARGET_REPORT.lower()

    for path in files:
        if os.path.basename(path).lower() == target_lower:
            matches.append(path)

    return matches


def score_content(path, text):
    lower = text.lower()

    producer_ref = PRODUCER.lower() in lower
    report_ref = TARGET_REPORT.lower() in lower

    score = 0
    matched_terms = []

    for term in PROVENANCE_TERMS:
        if term.lower() in lower:
            score += 10
            matched_terms.append(term)

    runtime_hits = []

    for term in RUNTIME_TERMS:
        if term.lower() in lower:
            score += 3
            runtime_hits.append(term)

    filename = os.path.basename(path).lower()

    if "historical" in filename:
        score += 5

    if "runtime" in filename:
        score += 5

    if "evidence" in filename:
        score += 5

    if "artifact" in filename:
        score += 5

    if "forensic" in filename:
        score += 3

    return {
        "path": path,
        "score": score,
        "producer_reference": producer_ref,
        "report_reference": report_ref,
        "matched_provenance_terms": matched_terms,
        "runtime_terms": runtime_hits,
    }


def content_provenance_search(files):
    results = []

    for path in files:
        text = safe_read_text(path)

        if not text:
            continue

        item = score_content(path, text)

        if (
            item["producer_reference"]
            or item["report_reference"]
            or item["score"] >= 15
        ):
            results.append(item)

    results.sort(
        key=lambda x: (
            x["producer_reference"],
            x["report_reference"],
            x["score"],
        ),
        reverse=True,
    )

    return results


def json_evidence_search(files):
    results = []

    for path in files:
        if not path.lower().endswith(".json"):
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        serialized = json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        ).lower()

        producer_ref = PRODUCER.lower() in serialized
        report_ref = TARGET_REPORT.lower() in serialized

        runtime_hits = [
            term
            for term in RUNTIME_TERMS
            if term.lower() in serialized
        ]

        if producer_ref or report_ref or runtime_hits:
            results.append({
                "path": path,
                "producer_reference": producer_ref,
                "report_reference": report_ref,
                "runtime_reference": bool(runtime_hits),
                "runtime_terms": runtime_hits[:30],
                "valid_json": True,
            })

    return results


def archive_forensic():
    archives = []

    backup_root = os.path.join(PROJECT_ROOT, "_backups")

    if not os.path.isdir(backup_root):
        return archives

    for root, dirs, files in os.walk(backup_root):
        for filename in files:
            if filename.lower().endswith((".zip", ".7z", ".tar", ".gz")):
                archives.append(os.path.join(root, filename))

    results = []

    for archive in archives:
        item = {
            "archive": archive,
            "target_member": False,
            "producer_member": False,
            "runtime_members": [],
            "inspectable": False,
        }

        if archive.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(archive, "r") as z:
                    item["inspectable"] = True

                    for member in z.namelist():
                        lower = member.lower()

                        if os.path.basename(TARGET_REPORT).lower() == os.path.basename(lower):
                            item["target_member"] = True

                        if os.path.basename(PRODUCER).lower() == os.path.basename(lower):
                            item["producer_member"] = True

                        if (
                            "runtime" in lower
                            or "evidence" in lower
                            or "capture" in lower
                            or "provenance" in lower
                        ):
                            item["runtime_members"].append(member)

            except Exception as exc:
                item["error"] = str(exc)

        results.append(item)

    return results


def timeline_signals(files):
    results = []

    for path in files:
        name = os.path.basename(path).lower()

        if not any(
            term in name
            for term in (
                "eligibility",
                "runtime",
                "evidence",
                "artifact",
                "provenance",
            )
        ):
            continue

        try:
            stat = os.stat(path)

            producer_ref = (
                PRODUCER.lower() in name
                or "eligibility" in name
            )

            report_ref = (
                TARGET_REPORT.lower() in name
                or "eligibility" in name
            )

            results.append({
                "timestamp": datetime.fromtimestamp(
                    stat.st_mtime,
                    timezone.utc,
                ).isoformat(),
                "path": path,
                "producer_reference_signal": producer_ref,
                "report_reference_signal": report_ref,
            })

        except Exception:
            continue

    results.sort(
        key=lambda x: x["timestamp"],
        reverse=True,
    )

    return results


def extraction_candidates(content_candidates, json_candidates):
    candidates = []

    for item in content_candidates:
        if not (
            item["producer_reference"]
            and item["report_reference"]
        ):
            continue

        runtime_strength = len(
            item["runtime_terms"]
        )

        candidates.append({
            "path": item["path"],
            "score": item["score"],
            "runtime_strength": runtime_strength,
            "producer_reference": True,
            "report_reference": True,
            "runtime_terms": item["runtime_terms"],
            "extraction_status": "REFERENCE_ONLY",
        })

    for item in json_candidates:
        if (
            item["producer_reference"]
            and item["report_reference"]
        ):
            candidates.append({
                "path": item["path"],
                "score": 0,
                "runtime_strength": len(
                    item["runtime_terms"]
                ),
                "producer_reference": True,
                "report_reference": True,
                "runtime_terms": item["runtime_terms"],
                "extraction_status": "JSON_REFERENCE_ONLY",
            })

    unique = {}

    for item in candidates:
        unique[item["path"]] = item

    result = list(unique.values())

    result.sort(
        key=lambda x: (
            x["runtime_strength"],
            x["score"],
        ),
        reverse=True,
    )

    return result


def main():
    print("=" * 100)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE ARTIFACT EXTRACTION FORENSIC v0.1")
    print("=" * 100)
    print("MODE                         : READ-ONLY FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"TARGET REPORT                : {TARGET_REPORT}")
    print(f"PRODUCER                     : {PRODUCER}")
    print(f"CONSUMER                     : {CONSUMER}")
    print("=" * 100)

    files = walk_files()

    print("FILESYSTEM INVENTORY")
    print("=" * 100)
    print(f"Files discovered              : {len(files)}")

    exact = exact_artifact_search(files)

    print("=" * 100)
    print("EXACT ARTIFACT DISCOVERY")
    print("=" * 100)
    print(f"Exact target files found      : {len(exact)}")

    content_candidates = content_provenance_search(files)

    print("=" * 100)
    print("CONTENT PROVENANCE SEARCH")
    print("=" * 100)
    print(
        f"Content provenance candidates : "
        f"{len(content_candidates)}"
    )

    for idx, item in enumerate(content_candidates[:30], 1):
        print(
            f"{idx:3d} | score={item['score']:3d} | "
            f"{item['path']}"
        )

    json_candidates = json_evidence_search(files)

    print("=" * 100)
    print("JSON EVIDENCE FORENSIC")
    print("=" * 100)
    print(
        f"JSON evidence candidates      : "
        f"{len(json_candidates)}"
    )

    for idx, item in enumerate(json_candidates[:20], 1):
        print(
            f"{idx:3d} | "
            f"producer={item['producer_reference']} | "
            f"report={item['report_reference']} | "
            f"runtime={item['runtime_reference']} | "
            f"{item['path']}"
        )

    archives = archive_forensic()

    print("=" * 100)
    print("ARCHIVE FORENSIC")
    print("=" * 100)
    print(f"Archives inspected             : {len(archives)}")

    for item in archives:
        print(
            f"  - {item['archive']} | "
            f"target_member={item['target_member']} | "
            f"producer_member={item['producer_member']} | "
            f"runtime_members={len(item['runtime_members'])}"
        )

    extraction = extraction_candidates(
        content_candidates,
        json_candidates,
    )

    print("=" * 100)
    print("EXTRACTION CANDIDATES")
    print("=" * 100)
    print(
        f"Potential provenance artifacts : "
        f"{len(extraction)}"
    )

    for idx, item in enumerate(extraction[:20], 1):
        print(
            f"{idx:3d} | "
            f"score={item['score']:3d} | "
            f"runtime_strength={item['runtime_strength']:2d} | "
            f"{item['path']}"
        )

    timeline = timeline_signals(files)

    print("=" * 100)
    print("TIMELINE SIGNALS")
    print("=" * 100)
    print(
        f"Timeline candidates            : "
        f"{len(timeline)}"
    )

    for idx, item in enumerate(timeline[:20], 1):
        print(
            f"{idx:3d} | "
            f"{item['timestamp']} | "
            f"{item['path']}"
        )

    exact_recovered = len(exact) > 0

    archive_exact = any(
        item["target_member"]
        for item in archives
    )

    runtime_evidence = (
        len(extraction) > 0
        or any(
            item["runtime_reference"]
            for item in json_candidates
        )
    )

    if exact_recovered:
        status = "EXACT_ARTIFACT_PRESENT"
    elif archive_exact:
        status = "EXACT_ARCHIVE_ARTIFACT_PRESENT"
    elif runtime_evidence:
        status = (
            "RUNTIME_EVIDENCE_ARTIFACT_EXTRACTION_REFERENCE_FOUND"
        )
    else:
        status = "NO_EXTRACTABLE_HISTORICAL_ARTIFACT_EVIDENCE"

    print("=" * 100)
    print("EXTRACTION DECISION")
    print("=" * 100)
    print(f"STATUS                       : {status}")
    print(
        f"EXACT ARTIFACT RECOVERED    : "
        f"{exact_recovered}"
    )
    print(
        f"EXACT ARCHIVE ARTIFACT      : "
        f"{archive_exact}"
    )
    print(
        f"RUNTIME EVIDENCE FOUND      : "
        f"{runtime_evidence}"
    )

    report = {
        "forensic_metadata": {
            "script": SCRIPT_NAME,
            "version": "v0.1",
            "mode": "READ-ONLY FORENSIC",
            "timestamp_utc": now_utc(),
            "project_root": PROJECT_ROOT,
        },

        "baseline": {
            "target_report": TARGET_REPORT,
            "producer": PRODUCER,
            "consumer": CONSUMER,
        },

        "filesystem": {
            "files_discovered": len(files),
            "exact_target_files": exact,
        },

        "content_provenance": {
            "candidate_count": len(content_candidates),
            "candidates": content_candidates[:100],
        },

        "json_evidence": {
            "candidate_count": len(json_candidates),
            "candidates": json_candidates[:100],
        },

        "archive_forensic": {
            "archive_count": len(archives),
            "archives": archives,
        },

        "extraction": {
            "candidate_count": len(extraction),
            "candidates": extraction[:100],
            "exact_artifact_recovered": exact_recovered,
            "exact_archive_artifact": archive_exact,
            "runtime_evidence_found": runtime_evidence,
            "extraction_performed": False,
            "artifact_reconstructed": False,
            "artifact_regenerated": False,
            "synthetic_artifact_created": False,
        },

        "timeline": {
            "candidate_count": len(timeline),
            "candidates": timeline[:100],
        },

        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "synthetic_artifact": False,
            "production_db_writes": "NONE",
            "production_source_modified": "NONE",
            "network_access": "NONE",
            "recovery_staging": "NONE",
            "artifact_extraction_execution": False,
        },

        "final_verdict": {
            "historical_eligibility_evidence":
                status,
            "exact_artifact_recovered":
                exact_recovered,
            "runtime_evidence_found":
                runtime_evidence,
        },
    }

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed            : NO")
    print("Producer imported            : NO")
    print("Eligibility executed         : NO")
    print("Eligibility rebuilt          : NO")
    print("Report regenerated           : NO")
    print("Synthetic artifact           : NO")
    print("Production DB writes         : NONE")
    print("Production source modified   : NONE")
    print("Network access               : NONE")
    print("Artifact extraction executed : NO")
    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        + status
    )
    print(
        f"FORENSIC REPORT              : "
        f"{OUTPUT_REPORT}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()