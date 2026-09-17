import ast
import hashlib
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SCRIPT_NAME = (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_SOURCE_TRACE_FORENSIC_v0.1.py"
)

REPORT_NAME = (
    "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_SOURCE_TRACE_FORENSIC_REPORT.json"
)

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

PRODUCER = "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"

CONSUMER = "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"

REPORT_PATH = PROJECT_ROOT / REPORT_NAME

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
    ".env",
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
    ".xml",
}

RUNTIME_TERMS = [
    "stdout",
    "stderr",
    "runtime",
    "execution",
    "executed",
    "invocation",
    "invoke",
    "launch",
    "entrypoint",
    "working directory",
    "cwd",
    "output",
    "capture",
    "subprocess",
    "returncode",
    "process",
    "command",
    "isolated",
]

SOURCE_TERMS = [
    PRODUCER,
    TARGET_REPORT,
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE",
    "ELIGIBILITY_NO_TRADE",
    "SIGNAL_ELIGIBILITY",
    "eligibility_report",
    "eligible_pool",
    "candidate_created",
    "UPSTREAM_ELIGIBILITY_CONSUMED",
]

ARTIFACT_TERMS = [
    TARGET_REPORT,
    "report",
    "artifact",
    "json",
    "eligibility",
    "eligible_pool",
]

MAX_TEXT_SIZE = 8 * 1024 * 1024
MAX_CANDIDATES = 50


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def safe_read_text(path):
    try:
        if path.stat().st_size > MAX_TEXT_SIZE:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def iter_files():
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for name in files:
            path = Path(root) / name

            if path == REPORT_PATH:
                continue

            yield path


def normalized(text):
    return text.replace("\\", "/").lower()


def score_content(text, path):
    low = normalized(text)
    name = normalized(path.name)

    score = 0
    matched = []

    for term in SOURCE_TERMS:
        if term.lower() in low or term.lower() in name:
            score += 10
            matched.append(term)

    for term in RUNTIME_TERMS:
        if term.lower() in low:
            score += 4
            matched.append(term)

    for term in ARTIFACT_TERMS:
        if term.lower() in low:
            score += 2
            matched.append(term)

    return score, sorted(set(matched))


def runtime_strength(text):
    low = normalized(text)
    hits = sum(
        1 for term in RUNTIME_TERMS
        if term.lower() in low
    )
    return min(hits, 20)


def producer_reference(text):
    low = normalized(text)
    return (
        PRODUCER.lower() in low
        or "eligibility_no_trade" in low
        or "signal_eligibility" in low
    )


def report_reference(text):
    low = normalized(text)
    return TARGET_REPORT.lower() in low


def runtime_reference(text):
    low = normalized(text)
    return any(
        term.lower() in low
        for term in RUNTIME_TERMS
    )


def ast_forensics(path):
    result = {
        "ast_parse": "NOT_ATTEMPTED",
        "report_refs": 0,
        "subprocess_calls": 0,
        "write_calls": 0,
    }

    text = safe_read_text(path)

    if text is None:
        result["ast_parse"] = "UNREADABLE"
        return result

    try:
        tree = ast.parse(text, filename=str(path))
        result["ast_parse"] = "PASS"
    except Exception:
        result["ast_parse"] = "FAIL"
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ""

            if isinstance(node.func, ast.Name):
                func_name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in {
                "Popen",
                "run",
                "call",
                "check_call",
                "check_output",
            }:
                result["subprocess_calls"] += 1

            if func_name in {
                "write_text",
                "write_bytes",
                "dump",
                "dumps",
                "open",
            }:
                result["write_calls"] += 1

            for arg in list(node.args) + list(node.keywords):
                value = getattr(arg, "value", None)

                if isinstance(value, str):
                    if TARGET_REPORT in value:
                        result["report_refs"] += 1

    return result


def collect_content_candidates():
    candidates = []

    for path in iter_files():
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        text = safe_read_text(path)

        if text is None:
            continue

        score, terms = score_content(text, path)

        if score <= 0:
            continue

        candidates.append({
            "path": str(path),
            "name": path.name,
            "score": score,
            "runtime_strength": runtime_strength(text),
            "producer_reference": producer_reference(text),
            "report_reference": report_reference(text),
            "runtime_reference": runtime_reference(text),
            "matched_terms": terms[:30],
            "size": path.stat().st_size,
            "modified_utc": datetime.fromtimestamp(
                path.stat().st_mtime,
                timezone.utc
            ).isoformat(),
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["runtime_strength"],
        ),
        reverse=True,
    )

    return candidates


def collect_source_trace_candidates():
    candidates = []

    for path in iter_files():
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        text = safe_read_text(path)

        if text is None:
            continue

        has_producer = producer_reference(text)
        has_report = report_reference(text)
        has_runtime = runtime_reference(text)

        if not (has_producer or has_report or has_runtime):
            continue

        score, terms = score_content(text, path)

        trace_strength = 0

        if has_producer:
            trace_strength += 20

        if has_report:
            trace_strength += 20

        if has_runtime:
            trace_strength += runtime_strength(text)

        candidates.append({
            "path": str(path),
            "name": path.name,
            "score": score,
            "source_trace_strength": trace_strength,
            "producer_reference": has_producer,
            "report_reference": has_report,
            "runtime_reference": has_runtime,
            "matched_terms": terms[:40],
        })

    candidates.sort(
        key=lambda x: (
            x["source_trace_strength"],
            x["score"],
        ),
        reverse=True,
    )

    return candidates


def inspect_json_candidates():
    results = []

    for path in iter_files():
        if path.suffix.lower() != ".json":
            continue

        text = safe_read_text(path)

        if text is None:
            continue

        try:
            data = json.loads(text)
            valid = True
        except Exception:
            data = None
            valid = False

        if not valid:
            continue

        blob = json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        )

        has_producer = producer_reference(blob)
        has_report = report_reference(blob)
        has_runtime = runtime_reference(blob)

        if not (has_producer or has_report or has_runtime):
            continue

        results.append({
            "path": str(path),
            "valid_json": valid,
            "producer_reference": has_producer,
            "report_reference": has_report,
            "runtime_reference": has_runtime,
            "top_level_keys": (
                list(data.keys())[:50]
                if isinstance(data, dict)
                else []
            ),
        })

    return results


def inspect_archives():
    archives = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".zip",
            ".7z",
            ".rar",
        }:
            continue

        if any(
            part in EXCLUDED_DIRS
            for part in path.parts
        ):
            continue

        record = {
            "archive": str(path),
            "target_member": False,
            "producer_member": False,
            "runtime_members": 0,
            "matching_members": [],
        }

        if path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as z:
                    names = z.namelist()

                    for member in names:
                        low = member.lower()

                        if TARGET_REPORT.lower() in low:
                            record["target_member"] = True
                            record["matching_members"].append(member)

                        if PRODUCER.lower() in low:
                            record["producer_member"] = True
                            record["matching_members"].append(member)

                        if any(
                            term.lower() in low
                            for term in RUNTIME_TERMS
                        ):
                            record["runtime_members"] += 1

            except Exception:
                pass

        archives.append(record)

    return archives


def exact_artifact_paths():
    found = []

    for path in PROJECT_ROOT.rglob(TARGET_REPORT):
        if path.is_file():
            found.append(str(path))

    return found


def source_hashes():
    producer_path = PROJECT_ROOT / PRODUCER
    consumer_path = PROJECT_ROOT / CONSUMER
    script_path = PROJECT_ROOT / SCRIPT_NAME

    return {
        "producer_sha256": sha256_file(producer_path),
        "consumer_sha256": sha256_file(consumer_path),
        "forensic_script_sha256": sha256_file(script_path),
    }


def classify_source_trace(candidates):
    strong = []

    for item in candidates:
        if (
            item["producer_reference"]
            and item["report_reference"]
            and item["runtime_reference"]
        ):
            strong.append(item)

    return strong


def main():
    started = utc_now()

    files = list(iter_files())
    exact = exact_artifact_paths()

    content_candidates = collect_content_candidates()
    source_candidates = collect_source_trace_candidates()
    json_candidates = inspect_json_candidates()
    archives = inspect_archives()

    strong_sources = classify_source_trace(
        source_candidates
    )

    archive_target = any(
        a["target_member"]
        for a in archives
    )

    archive_producer = any(
        a["producer_member"]
        for a in archives
    )

    runtime_archive_members = sum(
        a["runtime_members"]
        for a in archives
    )

    producer_path = PROJECT_ROOT / PRODUCER
    consumer_path = PROJECT_ROOT / CONSUMER

    producer_ast = ast_forensics(producer_path)

    report = {
        "metadata": {
            "project": "ARUNDA TRADER",
            "stage": "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE SOURCE TRACE FORENSIC",
            "version": "v0.1",
            "mode": "READ-ONLY FORENSIC",
            "started_utc": started,
            "completed_utc": utc_now(),
        },

        "objective": {
            "target_report": TARGET_REPORT,
            "producer": PRODUCER,
            "consumer": CONSUMER,
            "purpose": (
                "Trace the historical runtime evidence back to "
                "its identifiable filesystem/source provenance "
                "without executing or reconstructing the producer."
            ),
        },

        "safety_contract": {
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
            "recovery_staging": "NONE",
        },

        "filesystem_inventory": {
            "files_discovered": len(files),
            "exact_target_files_found": len(exact),
            "exact_target_paths": exact,
        },

        "producer_static_trace": {
            "exists": producer_path.exists(),
            "sha256": sha256_file(producer_path),
            **producer_ast,
        },

        "consumer_static_trace": {
            "exists": consumer_path.exists(),
            "sha256": sha256_file(consumer_path),
        },

        "content_provenance": {
            "candidate_count": len(content_candidates),
            "top_candidates": content_candidates[
                :MAX_CANDIDATES
            ],
        },

        "runtime_source_trace": {
            "candidate_count": len(source_candidates),
            "strong_trace_count": len(strong_sources),
            "strong_trace_candidates": strong_sources[
                :MAX_CANDIDATES
            ],
            "all_candidates": source_candidates[
                :MAX_CANDIDATES
            ],
        },

        "json_evidence": {
            "candidate_count": len(json_candidates),
            "candidates": json_candidates[
                :MAX_CANDIDATES
            ],
        },

        "archive_forensic": {
            "archives_inspected": len(archives),
            "target_artifact_in_archive": archive_target,
            "producer_in_archive": archive_producer,
            "runtime_members_total": runtime_archive_members,
            "archives": archives,
        },

        "source_hashes": source_hashes(),

        "trace_decision": {
            "exact_artifact_recovered": bool(exact),
            "exact_archive_artifact": archive_target,
            "runtime_source_trace_found": bool(strong_sources),
            "producer_runtime_trace_found": any(
                x["producer_reference"]
                and x["runtime_reference"]
                for x in source_candidates
            ),
            "report_runtime_trace_found": any(
                x["report_reference"]
                and x["runtime_reference"]
                for x in source_candidates
            ),
        },
    }

    if exact:
        status = "EXACT_ARTIFACT_PRESENT_SOURCE_TRACE_CONFIRMED"
    elif archive_target:
        status = "ARCHIVE_ARTIFACT_PRESENT_SOURCE_TRACE_CONFIRMED"
    elif strong_sources:
        status = "RUNTIME_SOURCE_TRACE_FOUND_ARTIFACT_UNRECOVERED"
    elif source_candidates:
        status = "PARTIAL_RUNTIME_SOURCE_TRACE_FOUND"
    else:
        status = "NO_RUNTIME_SOURCE_TRACE_FOUND"

    report["final_verdict"] = {
        "status": status,
        "historical_runtime_evidence": (
            "SOURCE_TRACE_FOUND"
            if strong_sources
            else (
                "PARTIAL_SOURCE_TRACE"
                if source_candidates
                else "NOT_FOUND"
            )
        ),
        "artifact_recovered": bool(exact),
        "producer_executed": False,
        "eligibility_executed": False,
        "report_regenerated": False,
        "production_db_writes": "NONE",
        "network_access": False,
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=" * 100)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE SOURCE TRACE FORENSIC v0.1")
    print("=" * 100)
    print("MODE                         : READ-ONLY FORENSIC")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"TARGET REPORT                : {TARGET_REPORT}")
    print(f"PRODUCER                     : {PRODUCER}")
    print(f"CONSUMER                     : {CONSUMER}")
    print("=" * 100)
    print("FILESYSTEM INVENTORY")
    print("=" * 100)
    print(f"Files discovered              : {len(files)}")
    print(f"Exact target files found      : {len(exact)}")
    print("=" * 100)
    print("SOURCE TRACE")
    print("=" * 100)
    print(
        f"Source trace candidates       : {len(source_candidates)}"
    )
    print(
        f"Strong runtime source traces  : {len(strong_sources)}"
    )
    print("=" * 100)
    print("JSON EVIDENCE")
    print("=" * 100)
    print(
        f"JSON evidence candidates      : {len(json_candidates)}"
    )
    print("=" * 100)
    print("ARCHIVE FORENSIC")
    print("=" * 100)
    print(f"Archives inspected             : {len(archives)}")
    print(
        f"Archive target artifact        : "
        f"{archive_target}"
    )
    print(
        f"Archive producer present       : "
        f"{archive_producer}"
    )
    print(
        f"Runtime archive members        : "
        f"{runtime_archive_members}"
    )
    print("=" * 100)
    print("TRACE DECISION")
    print("=" * 100)
    print(f"STATUS                       : {status}")
    print(
        f"EXACT ARTIFACT RECOVERED    : "
        f"{bool(exact)}"
    )
    print(
        f"RUNTIME SOURCE TRACE FOUND  : "
        f"{bool(strong_sources)}"
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
    print("Recovery staging             : NONE")
    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        f"HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        f"{report['final_verdict']['historical_runtime_evidence']}"
    )
    print(
        f"FORENSIC REPORT              : {REPORT_PATH}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()