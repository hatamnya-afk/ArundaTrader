import os
import json
import hashlib
import ast
import zipfile
from datetime import datetime, timezone

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
PRODUCER = "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
CONSUMER = "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"

SCRIPT_NAME = "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_SOURCE_ARTIFACT_MAPPING_FORENSIC_v0.1.py"
REPORT_NAME = "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_SOURCE_ARTIFACT_MAPPING_FORENSIC_REPORT.json"

REPORT_PATH = os.path.join(PROJECT_ROOT, REPORT_NAME)

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
}

TEXT_EXTENSIONS = {
    ".py", ".json", ".txt", ".log", ".md", ".csv",
    ".yaml", ".yml", ".ini", ".cfg", ".xml"
}

RUNTIME_TERMS = {
    "runtime",
    "execution",
    "executed",
    "invocation",
    "entrypoint",
    "launch",
    "stdout",
    "stderr",
    "returncode",
    "capture",
    "working directory",
    "cwd",
    "subprocess",
    "isolated",
    "output",
    "report",
}

PROVENANCE_TERMS = {
    PRODUCER.lower(),
    TARGET_REPORT.lower(),
    "eligibility_no_trade",
    "live_signal_eligibility",
    "signal_eligibility",
    "eligibility_report",
    "eligible_pool",
    "candidate_created",
    "runtime_evidence",
    "runtime_provenance",
    "source_trace",
    "artifact",
}

SKIP_BINARY_LARGE = 8 * 1024 * 1024


def now_iso():
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


def safe_read_text(path):
    try:
        size = os.path.getsize(path)
        if size > SKIP_BINARY_LARGE:
            return None

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def is_target_file(name):
    return name == TARGET_REPORT


def discover_files():
    results = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for name in files:
            path = os.path.join(root, name)

            if os.path.isfile(path):
                results.append(path)

    return results


def score_text(text, path):
    if not text:
        return 0, [], 0

    lower = text.lower()
    path_lower = path.lower()

    matched = set()

    for term in PROVENANCE_TERMS:
        if term in lower or term in path_lower:
            matched.add(term)

    runtime_hits = set()

    for term in RUNTIME_TERMS:
        if term in lower:
            runtime_hits.add(term)

    score = 0

    if PRODUCER.lower() in lower:
        score += 45

    if TARGET_REPORT.lower() in lower:
        score += 45

    if "eligibility" in lower:
        score += 12

    if "artifact" in lower:
        score += 8

    if "runtime" in lower:
        score += 8

    if "source" in lower and "trace" in lower:
        score += 8

    score += min(len(runtime_hits), 10) * 2
    score += min(len(matched), 12)

    return score, sorted(matched), len(runtime_hits)


def inspect_json(path, text):
    if not text:
        return None

    try:
        data = json.loads(text)
    except Exception:
        return None

    serialized = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True
    ).lower()

    producer_ref = PRODUCER.lower() in serialized
    report_ref = TARGET_REPORT.lower() in serialized

    runtime_ref = any(
        term in serialized
        for term in RUNTIME_TERMS
    )

    artifact_ref = (
        "artifact" in serialized
        or "recovery" in serialized
        or "provenance" in serialized
        or "source_trace" in serialized
    )

    return {
        "path": path,
        "valid_json": True,
        "producer_reference": producer_ref,
        "report_reference": report_ref,
        "runtime_reference": runtime_ref,
        "artifact_reference": artifact_ref,
        "top_level_type": type(data).__name__,
        "top_level_keys": (
            sorted(data.keys())
            if isinstance(data, dict)
            else []
        ),
    }


def inspect_python(path, text):
    if not text:
        return None

    try:
        tree = ast.parse(text, filename=path)
    except Exception:
        return {
            "ast_parse": "FAIL",
            "producer_reference": PRODUCER.lower() in text.lower(),
            "report_reference": TARGET_REPORT.lower() in text.lower(),
        }

    calls = []
    names = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

        if isinstance(node, ast.Name):
            names.append(node.id)

    joined = " ".join(calls + names).lower()

    return {
        "ast_parse": "PASS",
        "producer_reference": PRODUCER.lower() in text.lower(),
        "report_reference": TARGET_REPORT.lower() in text.lower(),
        "subprocess_reference": (
            "subprocess" in joined
            or "popen" in joined
            or "run" in joined
            or "check_output" in joined
        ),
        "capture_reference": (
            "stdout" in text.lower()
            or "stderr" in text.lower()
            or "capture" in text.lower()
        ),
        "runtime_reference": any(
            term in text.lower()
            for term in RUNTIME_TERMS
        ),
    }


def inspect_archives(files):
    archives = []

    for path in files:
        if not path.lower().endswith(".zip"):
            continue

        record = {
            "path": path,
            "target_member": False,
            "producer_member": False,
            "runtime_members": 0,
            "matching_members": [],
        }

        try:
            with zipfile.ZipFile(path, "r") as z:
                for member in z.namelist():
                    lower = member.lower()

                    if os.path.basename(lower) == TARGET_REPORT.lower():
                        record["target_member"] = True

                    if os.path.basename(lower) == PRODUCER.lower():
                        record["producer_member"] = True

                    runtime_hits = sum(
                        1
                        for term in RUNTIME_TERMS
                        if term in lower
                    )

                    if runtime_hits >= 1:
                        record["runtime_members"] += 1

                    if (
                        TARGET_REPORT.lower() in lower
                        or PRODUCER.lower() in lower
                        or (
                            "eligibility" in lower
                            and (
                                "runtime" in lower
                                or "artifact" in lower
                                or "provenance" in lower
                            )
                        )
                    ):
                        record["matching_members"].append(member)

        except Exception as exc:
            record["error"] = str(exc)

        archives.append(record)

    return archives


def build_mapping_candidate(path, text, score, matched_terms, runtime_strength):
    lower = (text or "").lower()

    producer = PRODUCER.lower() in lower
    report = TARGET_REPORT.lower() in lower

    source_mapping_terms = [
        term for term in [
            "source",
            "trace",
            "artifact",
            "mapping",
            "runtime",
            "output",
            "report",
            "producer",
            "consumer",
            "entrypoint",
            "invocation",
            "stdout",
            "stderr",
            "cwd",
            "execution",
        ]
        if term in lower
    ]

    return {
        "path": path,
        "score": score,
        "runtime_strength": runtime_strength,
        "producer_reference": producer,
        "report_reference": report,
        "matched_provenance_terms": matched_terms,
        "source_mapping_terms": source_mapping_terms,
        "sha256": sha256_file(path),
        "modified_utc": datetime.fromtimestamp(
            os.path.getmtime(path),
            timezone.utc
        ).isoformat(),
    }


def main():
    print("=" * 100)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE SOURCE ARTIFACT MAPPING FORENSIC v0.1")
    print("=" * 100)
    print("MODE                         : READ-ONLY FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"TARGET REPORT                : {TARGET_REPORT}")
    print(f"PRODUCER                     : {PRODUCER}")
    print(f"CONSUMER                     : {CONSUMER}")
    print("=" * 100)

    files = discover_files()

    exact_targets = [
        p for p in files
        if os.path.basename(p) == TARGET_REPORT
    ]

    print("FILESYSTEM INVENTORY")
    print("=" * 100)
    print(f"Files discovered              : {len(files)}")
    print(f"Exact target files found      : {len(exact_targets)}")
    print("=" * 100)

    content_candidates = []
    json_candidates = []
    mapping_candidates = []

    for path in files:
        ext = os.path.splitext(path)[1].lower()

        if ext not in TEXT_EXTENSIONS:
            continue

        text = safe_read_text(path)

        if not text:
            continue

        score, matched, runtime_strength = score_text(text, path)

        if score > 0:
            content_candidates.append({
                "path": path,
                "score": score,
                "matched_terms": matched,
                "runtime_strength": runtime_strength,
            })

        if ext == ".json":
            info = inspect_json(path, text)

            if info and (
                info["producer_reference"]
                or info["report_reference"]
                or info["runtime_reference"]
                or info["artifact_reference"]
            ):
                json_candidates.append(info)

        if (
            PRODUCER.lower() in text.lower()
            or TARGET_REPORT.lower() in text.lower()
        ):
            candidate = build_mapping_candidate(
                path,
                text,
                score,
                matched,
                runtime_strength
            )

            mapping_candidates.append(candidate)

    content_candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    mapping_candidates.sort(
        key=lambda x: (
            x["producer_reference"] and x["report_reference"],
            x["runtime_strength"],
            x["score"]
        ),
        reverse=True
    )

    print("SOURCE ARTIFACT MAPPING CANDIDATES")
    print("=" * 100)
    print(f"Mapping candidates             : {len(mapping_candidates)}")

    for i, item in enumerate(mapping_candidates[:30], 1):
        print(
            f"{i:3d} | "
            f"score={item['score']:3d} | "
            f"runtime_strength={item['runtime_strength']:2d} | "
            f"producer={item['producer_reference']} | "
            f"report={item['report_reference']} | "
            f"{item['path']}"
        )

    print("=" * 100)
    print("JSON MAPPING EVIDENCE")
    print("=" * 100)
    print(f"JSON evidence candidates      : {len(json_candidates)}")

    for i, item in enumerate(json_candidates[:20], 1):
        print(
            f"{i:3d} | "
            f"producer={item['producer_reference']} | "
            f"report={item['report_reference']} | "
            f"runtime={item['runtime_reference']} | "
            f"artifact={item['artifact_reference']} | "
            f"{item['path']}"
        )

    archives = inspect_archives(files)

    print("=" * 100)
    print("ARCHIVE FORENSIC")
    print("=" * 100)
    print(f"Archives inspected             : {len(archives)}")

    for archive in archives:
        print(
            f"  - {archive['path']} | "
            f"target_member={archive.get('target_member', False)} | "
            f"producer_member={archive.get('producer_member', False)} | "
            f"runtime_members={archive.get('runtime_members', 0)}"
        )

    strong_mappings = [
        x for x in mapping_candidates
        if x["producer_reference"]
        and x["report_reference"]
        and x["runtime_strength"] >= 2
    ]

    exact_archive_artifact = any(
        x.get("target_member", False)
        for x in archives
    )

    exact_recovered = len(exact_targets) > 0

    if exact_recovered:
        status = "EXACT_ARTIFACT_PRESENT"
    elif exact_archive_artifact:
        status = "EXACT_ARCHIVE_ARTIFACT_PRESENT"
    elif strong_mappings:
        status = "SOURCE_ARTIFACT_MAPPING_FOUND_ARTIFACT_UNRECOVERED"
    elif mapping_candidates:
        status = "SOURCE_ARTIFACT_REFERENCE_FOUND_ARTIFACT_UNRECOVERED"
    else:
        status = "NO_SOURCE_ARTIFACT_MAPPING_FOUND"

    print("=" * 100)
    print("MAPPING DECISION")
    print("=" * 100)
    print(f"STATUS                       : {status}")
    print(f"EXACT ARTIFACT RECOVERED    : {exact_recovered}")
    print(f"EXACT ARCHIVE ARTIFACT      : {exact_archive_artifact}")
    print(f"SOURCE ARTIFACT MAPPING     : {bool(strong_mappings)}")

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
    print("Recovery staging             : NONE")
    print("Source modification          : NONE")

    report = {
        "metadata": {
            "tool": SCRIPT_NAME,
            "version": "v0.1",
            "mode": "READ-ONLY FORENSIC",
            "generated_utc": now_iso(),
            "project_root": PROJECT_ROOT,
        },
        "baseline": {
            "target_report": TARGET_REPORT,
            "producer": PRODUCER,
            "consumer": CONSUMER,
        },
        "filesystem": {
            "files_discovered": len(files),
            "exact_target_files_found": len(exact_targets),
            "exact_target_paths": exact_targets,
        },
        "source_artifact_mapping": {
            "mapping_candidates_count": len(mapping_candidates),
            "strong_mapping_count": len(strong_mappings),
            "candidates": mapping_candidates[:100],
        },
        "json_evidence": {
            "candidate_count": len(json_candidates),
            "candidates": json_candidates[:100],
        },
        "archive_forensic": {
            "archives_inspected": len(archives),
            "archives": archives,
            "exact_archive_artifact": exact_archive_artifact,
        },
        "decision": {
            "status": status,
            "exact_artifact_recovered": exact_recovered,
            "exact_archive_artifact": exact_archive_artifact,
            "source_artifact_mapping_found": bool(strong_mappings),
            "runtime_evidence_found": bool(mapping_candidates),
        },
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "synthetic_artifact": False,
            "production_db_writes": False,
            "production_source_modified": False,
            "network_access": False,
            "artifact_extraction_executed": False,
            "recovery_staging": False,
            "source_modification": False,
        },
        "final_verdict": {
            "historical_eligibility_runtime_evidence": status,
            "forensic_report": REPORT_PATH,
        },
    }

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        f"HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : {status}"
    )
    print(
        f"FORENSIC REPORT              : {REPORT_PATH}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()