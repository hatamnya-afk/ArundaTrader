from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY PRODUCER RUNTIME PROVENANCE FORENSIC v0.1
# =============================================================================

VERSION = "v0.1"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER_NAME = (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

CONSUMER_NAME = (
    "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"
)

OUTPUT_REPORT = (
    "HISTORICAL_ELIGIBILITY_PRODUCER_RUNTIME_PROVENANCE_FORENSIC_REPORT.json"
)

TARGET_PRODUCER = BASE_DIR / PRODUCER_NAME
TARGET_CONSUMER = BASE_DIR / CONSUMER_NAME


# =============================================================================
# SAFETY
# =============================================================================

SAFETY_POLICY = {
    "production_db_writes": False,
    "production_db_access": "READ_ONLY_ONLY",
    "production_source_modification": False,
    "producer_execution": False,
    "producer_import": False,
    "eligibility_execution": False,
    "eligibility_rebuild": False,
    "report_regeneration": False,
    "synthetic_report": False,
    "network_access": False,
    "archive_extraction": False,
    "recovery_staging": "NONE",
}


# =============================================================================
# FORENSIC SEARCH CONFIGURATION
# =============================================================================

MAX_FILE_SIZE = 25 * 1024 * 1024

TEXT_EXTENSIONS = {
    ".py",
    ".txt",
    ".json",
    ".log",
    ".out",
    ".err",
    ".csv",
    ".md",
    ".xml",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
}

ARCHIVE_EXTENSIONS = {
    ".zip",
}

PROVENANCE_TERMS = [
    TARGET_REPORT,
    PRODUCER_NAME,
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1",
    "SIGNAL_ELIGIBILITY",
    "ELIGIBILITY_NO_TRADE",
    "eligibility_report",
    "eligible_pool",
    "UPSTREAM_ELIGIBILITY_CONSUMED",
]

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

EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def safe_stat(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()

        return {
            "exists": True,
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(
                stat.st_mtime,
                timezone.utc,
            ).isoformat(),
            "ctime": datetime.fromtimestamp(
                stat.st_ctime,
                timezone.utc,
            ).isoformat(),
        }

    except Exception as exc:
        return {
            "exists": False,
            "error": repr(exc),
        }


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def is_excluded(path: Path) -> bool:
    return any(
        part.lower() in {x.lower() for x in EXCLUDED_DIR_NAMES}
        for part in path.parts
    )


def read_text_safely(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return None

        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        return None


def normalize_text(text: str) -> str:
    return text.replace("\x00", " ").lower()


# =============================================================================
# AST ANALYSIS
# =============================================================================

def analyze_python_source(path: Path) -> dict[str, Any]:
    result = {
        "path": str(path),
        "parse": "NOT_RUN",
        "report_references": [],
        "producer_references": [],
        "write_calls": [],
        "subprocess_calls": [],
        "path_construction": [],
        "main_guard": False,
    }

    text = read_text_safely(path)

    if text is None:
        result["parse"] = "UNREADABLE"
        return result

    try:
        tree = ast.parse(text)
        result["parse"] = "PASS"
    except SyntaxError as exc:
        result["parse"] = "FAIL"
        result["syntax_error"] = str(exc)
        return result

    for node in ast.walk(tree):

        if isinstance(node, ast.If):
            try:
                condition = ast.unparse(node.test)

                if (
                    "__name__" in condition
                    and "__main__" in condition
                ):
                    result["main_guard"] = True

            except Exception:
                pass

        if isinstance(node, ast.Call):

            try:
                func = ast.unparse(node.func)
            except Exception:
                func = ""

            func_lower = func.lower()

            if any(
                token in func_lower
                for token in [
                    "subprocess",
                    "popen",
                    "run",
                    "call",
                    "check_call",
                    "check_output",
                ]
            ):
                result["subprocess_calls"].append({
                    "line": getattr(node, "lineno", None),
                    "call": func,
                })

            if func_lower.endswith(
                (
                    ".write_text",
                    ".write_bytes",
                    ".open",
                )
            ):
                result["write_calls"].append({
                    "line": getattr(node, "lineno", None),
                    "call": func,
                })

        if isinstance(node, ast.Constant):
            value = node.value

            if isinstance(value, str):

                if TARGET_REPORT in value:
                    result["report_references"].append({
                        "line": getattr(node, "lineno", None),
                        "value": value,
                    })

                if PRODUCER_NAME in value:
                    result["producer_references"].append({
                        "line": getattr(node, "lineno", None),
                        "value": value,
                    })

    return result


# =============================================================================
# FILESYSTEM INVENTORY
# =============================================================================

def inventory_files() -> list[Path]:
    discovered = []

    for root, dirs, files in os.walk(BASE_DIR):

        root_path = Path(root)

        dirs[:] = [
            d for d in dirs
            if d.lower() not in {
                x.lower() for x in EXCLUDED_DIR_NAMES
            }
        ]

        for filename in files:

            path = root_path / filename

            if is_excluded(path):
                continue

            discovered.append(path)

    return discovered


# =============================================================================
# EXACT ARTIFACT PROVENANCE
# =============================================================================

def discover_exact_artifacts(files: list[Path]) -> list[dict[str, Any]]:
    results = []

    for path in files:

        if path.name == TARGET_REPORT:

            results.append({
                "path": str(path),
                "relative_path": relative_path(path),
                "stat": safe_stat(path),
                "sha256": (
                    sha256_file(path)
                    if path.is_file()
                    else None
                ),
            })

    return results


# =============================================================================
# CONTENT PROVENANCE SEARCH
# =============================================================================

def search_textual_provenance(
    files: list[Path],
) -> list[dict[str, Any]]:

    results = []

    for path in files:

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        text = read_text_safely(path)

        if not text:
            continue

        normalized = normalize_text(text)

        matched_terms = []

        for term in PROVENANCE_TERMS + RUNTIME_TERMS:

            if term.lower() in normalized:
                matched_terms.append(term)

        if not matched_terms:
            continue

        # Calculate stronger provenance score.
        score = 0

        for term in matched_terms:

            if term == TARGET_REPORT:
                score += 50

            elif term == PRODUCER_NAME:
                score += 40

            elif term in {
                "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1",
                "SIGNAL_ELIGIBILITY",
                "ELIGIBILITY_NO_TRADE",
            }:
                score += 15

            elif term in {
                "stdout",
                "stderr",
                "runtime",
                "execution",
                "invocation",
                "subprocess",
            }:
                score += 5

            else:
                score += 2

        results.append({
            "path": str(path),
            "relative_path": relative_path(path),
            "score": score,
            "matched_terms": sorted(set(matched_terms)),
            "mtime": safe_stat(path).get("mtime"),
            "size": safe_stat(path).get("size"),
        })

    results.sort(
        key=lambda item: (
            item["score"],
            item.get("mtime") or "",
        ),
        reverse=True,
    )

    return results


# =============================================================================
# RUNTIME ARTIFACT DETECTION
# =============================================================================

def classify_runtime_artifact(
    path: Path,
    text: str,
) -> dict[str, Any]:

    normalized = normalize_text(text)

    producer_match = PRODUCER_NAME.lower() in normalized
    report_match = TARGET_REPORT.lower() in normalized

    runtime_matches = [
        term
        for term in RUNTIME_TERMS
        if term.lower() in normalized
    ]

    return {
        "producer_reference": producer_match,
        "report_reference": report_match,
        "runtime_terms": runtime_matches,
        "runtime_signal": (
            producer_match
            or report_match
        ) and bool(runtime_matches),
    }


def identify_runtime_candidates(
    files: list[Path],
) -> list[dict[str, Any]]:

    results = []

    for path in files:

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        text = read_text_safely(path)

        if not text:
            continue

        classification = classify_runtime_artifact(
            path,
            text,
        )

        if not classification["runtime_signal"]:
            continue

        score = 0

        if classification["report_reference"]:
            score += 50

        if classification["producer_reference"]:
            score += 40

        score += min(
            len(classification["runtime_terms"]) * 3,
            30,
        )

        results.append({
            "path": str(path),
            "relative_path": relative_path(path),
            "score": score,
            **classification,
            "mtime": safe_stat(path).get("mtime"),
        })

    results.sort(
        key=lambda item: (
            item["score"],
            item.get("mtime") or "",
        ),
        reverse=True,
    )

    return results


# =============================================================================
# JSON ARTIFACT SCHEMA FORENSICS
# =============================================================================

def inspect_json_candidate(path: Path) -> dict[str, Any]:

    result = {
        "path": str(path),
        "valid_json": False,
        "root_type": None,
        "keys": [],
        "producer_reference": False,
        "report_reference": False,
        "eligibility_fields": [],
        "snapshot_fields": [],
        "pool_fields": [],
    }

    text = read_text_safely(path)

    if text is None:
        return result

    try:
        data = json.loads(text)
    except Exception:
        return result

    result["valid_json"] = True
    result["root_type"] = type(data).__name__

    if isinstance(data, dict):

        keys = list(data.keys())
        result["keys"] = keys

        for key in keys:

            key_lower = str(key).lower()

            if "eligib" in key_lower:
                result["eligibility_fields"].append(key)

            if "snapshot" in key_lower:
                result["snapshot_fields"].append(key)

            if "pool" in key_lower or "candidate" in key_lower:
                result["pool_fields"].append(key)

        serialized = normalize_text(
            json.dumps(
                data,
                ensure_ascii=False,
                default=str,
            )
        )

        result["producer_reference"] = (
            PRODUCER_NAME.lower() in serialized
        )

        result["report_reference"] = (
            TARGET_REPORT.lower() in serialized
        )

    return result


# =============================================================================
# JSON CANDIDATE SEARCH
# =============================================================================

def inspect_json_candidates(
    files: list[Path],
) -> list[dict[str, Any]]:

    results = []

    for path in files:

        if path.suffix.lower() != ".json":
            continue

        inspection = inspect_json_candidate(path)

        if not inspection["valid_json"]:
            continue

        signal = (
            inspection["producer_reference"]
            or inspection["report_reference"]
            or bool(inspection["eligibility_fields"])
            or bool(inspection["snapshot_fields"])
            or bool(inspection["pool_fields"])
        )

        if signal:
            results.append(inspection)

    return results


# =============================================================================
# ARCHIVE FORENSICS
# =============================================================================

def inspect_archives(
    files: list[Path],
) -> list[dict[str, Any]]:

    results = []

    for path in files:

        if path.suffix.lower() not in ARCHIVE_EXTENSIONS:
            continue

        try:

            with zipfile.ZipFile(path, "r") as archive:

                names = archive.namelist()

                exact_members = [
                    name
                    for name in names
                    if Path(name).name == TARGET_REPORT
                ]

                producer_members = [
                    name
                    for name in names
                    if PRODUCER_NAME in Path(name).name
                ]

                provenance_members = [
                    name
                    for name in names
                    if (
                        "eligibility" in name.lower()
                        or "runtime" in name.lower()
                        or "report" in name.lower()
                    )
                ]

                results.append({
                    "archive": str(path),
                    "relative_path": relative_path(path),
                    "member_count": len(names),
                    "exact_report_members": exact_members,
                    "producer_members": producer_members,
                    "provenance_members": provenance_members[:100],
                    "archive_mtime": safe_stat(path).get("mtime"),
                })

        except Exception as exc:

            results.append({
                "archive": str(path),
                "relative_path": relative_path(path),
                "error": repr(exc),
            })

    return results


# =============================================================================
# PRODUCER STATIC PROVENANCE
# =============================================================================

def producer_forensic() -> dict[str, Any]:

    result = {
        "exists": TARGET_PRODUCER.exists(),
        "path": str(TARGET_PRODUCER),
        "sha256": None,
        "analysis": None,
    }

    if not TARGET_PRODUCER.exists():
        return result

    result["sha256"] = sha256_file(TARGET_PRODUCER)

    result["analysis"] = analyze_python_source(
        TARGET_PRODUCER
    )

    return result


# =============================================================================
# CONSUMER STATIC PROVENANCE
# =============================================================================

def consumer_forensic() -> dict[str, Any]:

    result = {
        "exists": TARGET_CONSUMER.exists(),
        "path": str(TARGET_CONSUMER),
        "sha256": None,
        "analysis": None,
    }

    if not TARGET_CONSUMER.exists():
        return result

    result["sha256"] = sha256_file(TARGET_CONSUMER)

    result["analysis"] = analyze_python_source(
        TARGET_CONSUMER
    )

    return result


# =============================================================================
# HISTORICAL TIMELINE SIGNALS
# =============================================================================

def timeline_candidates(
    files: list[Path],
) -> list[dict[str, Any]]:

    candidates = []

    for path in files:

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        text = read_text_safely(path)

        if not text:
            continue

        normalized = normalize_text(text)

        producer = PRODUCER_NAME.lower() in normalized
        report = TARGET_REPORT.lower() in normalized

        if not (producer or report):
            continue

        stat = safe_stat(path)

        candidates.append({
            "path": str(path),
            "relative_path": relative_path(path),
            "mtime": stat.get("mtime"),
            "size": stat.get("size"),
            "producer_reference": producer,
            "report_reference": report,
        })

    candidates.sort(
        key=lambda item: item.get("mtime") or "",
        reverse=True,
    )

    return candidates


# =============================================================================
# PROVENANCE DECISION
# =============================================================================

def determine_verdict(
    exact_artifacts: list[dict[str, Any]],
    archive_results: list[dict[str, Any]],
    runtime_candidates: list[dict[str, Any]],
) -> dict[str, Any]:

    exact = bool(exact_artifacts)

    archive_exact = any(
        item.get("exact_report_members")
        for item in archive_results
    )

    runtime_report_evidence = any(
        item.get("report_reference")
        for item in runtime_candidates
    )

    runtime_producer_evidence = any(
        item.get("producer_reference")
        for item in runtime_candidates
    )

    if exact:

        status = "EXACT_ARTIFACT_PRESENT"

    elif archive_exact:

        status = "EXACT_ARTIFACT_PRESENT_IN_ARCHIVE"

    elif runtime_report_evidence:

        status = "HISTORICAL_RUNTIME_REPORT_REFERENCE_FOUND"

    elif runtime_producer_evidence:

        status = "PRODUCER_RUNTIME_EVIDENCE_FOUND_REPORT_UNRECOVERED"

    else:

        status = "HISTORICAL_RUNTIME_PROVENANCE_NOT_FOUND"

    return {
        "status": status,
        "exact_artifact_present": exact,
        "archive_exact_artifact_present": archive_exact,
        "historical_runtime_report_reference_found": (
            runtime_report_evidence
        ),
        "historical_runtime_producer_reference_found": (
            runtime_producer_evidence
        ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    started = utc_now()

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER RUNTIME "
        "PROVENANCE FORENSIC v0.1"
    )
    print("=" * 100)

    print("MODE")
    print("READ-ONLY FORENSIC")
    print("=" * 100)

    print("OBJECTIVE")
    print(
        "Determine whether historical runtime provenance exists "
        "for the verified eligibility producer/report."
    )

    print()
    print("No producer execution.")
    print("No producer import.")
    print("No eligibility reconstruction.")
    print("No report regeneration.")
    print("No synthetic artifact.")
    print("No production DB writes.")
    print("No source modification.")
    print("No network access.")

    print("=" * 100)
    print("BASELINE")
    print("=" * 100)

    print(f"Project root : {BASE_DIR}")
    print(f"Producer     : {PRODUCER_NAME}")
    print(f"Target report: {TARGET_REPORT}")
    print(f"Consumer     : {CONSUMER_NAME}")

    producer_info = producer_forensic()
    consumer_info = consumer_forensic()

    print()
    print("=" * 100)
    print("PRODUCER STATIC PROVENANCE")
    print("=" * 100)

    print(
        f"Producer exists : "
        f"{producer_info['exists']}"
    )

    print(
        f"Producer SHA256 : "
        f"{producer_info['sha256']}"
    )

    if producer_info["analysis"]:

        analysis = producer_info["analysis"]

        print(
            f"AST parse       : "
            f"{analysis['parse']}"
        )

        print(
            f"Report refs     : "
            f"{len(analysis['report_references'])}"
        )

        print(
            f"Write calls     : "
            f"{len(analysis['write_calls'])}"
        )

        print(
            f"Subprocess calls: "
            f"{len(analysis['subprocess_calls'])}"
        )

    print()
    print("=" * 100)
    print("CONSUMER STATIC PROVENANCE")
    print("=" * 100)

    print(
        f"Consumer exists : "
        f"{consumer_info['exists']}"
    )

    print(
        f"Consumer SHA256 : "
        f"{consumer_info['sha256']}"
    )

    # -------------------------------------------------------------------------
    # Filesystem inventory
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FILESYSTEM INVENTORY")
    print("=" * 100)

    files = inventory_files()

    print(
        f"Files discovered : {len(files)}"
    )

    # -------------------------------------------------------------------------
    # Exact artifact
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EXACT HISTORICAL ARTIFACT DISCOVERY")
    print("=" * 100)

    exact_artifacts = discover_exact_artifacts(files)

    print(
        f"Exact report files found : "
        f"{len(exact_artifacts)}"
    )

    for item in exact_artifacts:
        print(
            f"  - {item['path']}"
        )

    # -------------------------------------------------------------------------
    # Content provenance
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("CONTENT PROVENANCE SEARCH")
    print("=" * 100)

    content_candidates = search_textual_provenance(files)

    print(
        f"Content provenance candidates : "
        f"{len(content_candidates)}"
    )

    for index, item in enumerate(
        content_candidates[:40],
        start=1,
    ):

        print(
            f"{index:3d} | "
            f"score={item['score']:3d} | "
            f"{item['path']}"
        )

        print(
            f"      terms="
            f"{', '.join(item['matched_terms'][:12])}"
        )

    # -------------------------------------------------------------------------
    # Runtime provenance
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("HISTORICAL RUNTIME PROVENANCE SEARCH")
    print("=" * 100)

    runtime_candidates = identify_runtime_candidates(
        files
    )

    print(
        f"Runtime provenance candidates : "
        f"{len(runtime_candidates)}"
    )

    for index, item in enumerate(
        runtime_candidates[:50],
        start=1,
    ):

        print(
            f"{index:3d} | "
            f"score={item['score']:3d} | "
            f"{item['path']}"
        )

        print(
            f"      producer_reference="
            f"{item['producer_reference']} | "
            f"report_reference="
            f"{item['report_reference']}"
        )

        if item["runtime_terms"]:

            print(
                f"      runtime_terms="
                f"{', '.join(item['runtime_terms'][:15])}"
            )

    # -------------------------------------------------------------------------
    # JSON schema candidates
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("JSON ARTIFACT / SCHEMA FORENSIC")
    print("=" * 100)

    json_candidates = inspect_json_candidates(
        files
    )

    print(
        f"JSON candidates : "
        f"{len(json_candidates)}"
    )

    for index, item in enumerate(
        json_candidates[:40],
        start=1,
    ):

        print(
            f"{index:3d} | "
            f"{item['path']}"
        )

        print(
            f"      valid={item['valid_json']} | "
            f"producer_ref={item['producer_reference']} | "
            f"report_ref={item['report_reference']}"
        )

        if item["eligibility_fields"]:
            print(
                f"      eligibility_fields="
                f"{item['eligibility_fields'][:15]}"
            )

        if item["snapshot_fields"]:
            print(
                f"      snapshot_fields="
                f"{item['snapshot_fields'][:15]}"
            )

        if item["pool_fields"]:
            print(
                f"      pool_fields="
                f"{item['pool_fields'][:15]}"
            )

    # -------------------------------------------------------------------------
    # Archive provenance
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ARCHIVE PROVENANCE FORENSIC")
    print("=" * 100)

    archive_results = inspect_archives(
        files
    )

    print(
        f"Archives inspected : "
        f"{len(archive_results)}"
    )

    for item in archive_results:

        print(
            f"  - {item['archive']}"
        )

        if item.get("exact_report_members"):
            print(
                "      EXACT TARGET MEMBERS:"
            )

            for member in item[
                "exact_report_members"
            ]:
                print(
                    f"        {member}"
                )

        if item.get("producer_members"):
            print(
                "      PRODUCER MEMBERS:"
            )

            for member in item[
                "producer_members"
            ][:20]:
                print(
                    f"        {member}"
                )

    # -------------------------------------------------------------------------
    # Timeline
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("HISTORICAL TIMELINE SIGNALS")
    print("=" * 100)

    timeline = timeline_candidates(
        files
    )

    print(
        f"Timeline candidates : "
        f"{len(timeline)}"
    )

    for index, item in enumerate(
        timeline[:50],
        start=1,
    ):

        print(
            f"{index:3d} | "
            f"{item['mtime']} | "
            f"{item['path']}"
        )

        print(
            f"      producer_ref="
            f"{item['producer_reference']} | "
            f"report_ref="
            f"{item['report_reference']}"
        )

    # -------------------------------------------------------------------------
    # Decision
    # -------------------------------------------------------------------------

    decision = determine_verdict(
        exact_artifacts=exact_artifacts,
        archive_results=archive_results,
        runtime_candidates=runtime_candidates,
    )

    print()
    print("=" * 100)
    print("PROVENANCE DECISION")
    print("=" * 100)

    print(
        f"STATUS : {decision['status']}"
    )

    print(
        f"Exact artifact present : "
        f"{decision['exact_artifact_present']}"
    )

    print(
        f"Exact archive artifact : "
        f"{decision['archive_exact_artifact_present']}"
    )

    print(
        f"Historical runtime report reference : "
        f"{decision['historical_runtime_report_reference_found']}"
    )

    print(
        f"Historical producer runtime reference : "
        f"{decision['historical_runtime_producer_reference_found']}"
    )

    # -------------------------------------------------------------------------
    # Final safety invariant
    # -------------------------------------------------------------------------

    source_before = producer_info["sha256"]

    source_after = (
        sha256_file(TARGET_PRODUCER)
        if TARGET_PRODUCER.exists()
        else None
    )

    source_invariant = (
        source_before == source_after
    )

    print()
    print("=" * 100)
    print("SOURCE INTEGRITY")
    print("=" * 100)

    print(
        f"Before SHA256 : {source_before}"
    )

    print(
        f"After SHA256  : {source_after}"
    )

    print(
        f"Source invariant : "
        f"{'PASS' if source_invariant else 'FAIL'}"
    )

    # -------------------------------------------------------------------------
    # Final report
    # -------------------------------------------------------------------------

    finished = utc_now()

    final_report = {
        "script": Path(__file__).name,
        "version": VERSION,
        "generated_at_utc": finished,
        "started_at_utc": started,

        "mode": "READ_ONLY_FORENSIC",

        "objective": (
            "Historical runtime provenance forensic for the "
            "verified eligibility producer and report."
        ),

        "target_report": TARGET_REPORT,
        "producer": PRODUCER_NAME,
        "consumer": CONSUMER_NAME,

        "safety_policy": SAFETY_POLICY,

        "baseline": {
            "project_root": str(BASE_DIR),
            "producer": producer_info,
            "consumer": consumer_info,
        },

        "filesystem": {
            "files_discovered": len(files),
            "exact_artifacts": exact_artifacts,
        },

        "content_provenance": {
            "candidate_count": len(content_candidates),
            "top_candidates": content_candidates[:100],
        },

        "runtime_provenance": {
            "candidate_count": len(runtime_candidates),
            "candidates": runtime_candidates[:100],
        },

        "json_forensics": {
            "candidate_count": len(json_candidates),
            "candidates": json_candidates[:100],
        },

        "archive_forensics": {
            "archive_count": len(archive_results),
            "archives": archive_results,
        },

        "timeline": {
            "candidate_count": len(timeline),
            "candidates": timeline[:100],
        },

        "decision": decision,

        "integrity": {
            "producer_sha256_before": source_before,
            "producer_sha256_after": source_after,
            "source_invariant": source_invariant,
        },

        "recovery": {
            "artifact_recovered": False,
            "artifact_staged": False,
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "report_regenerated": False,
            "synthetic_report_created": False,
        },
    }

    output_path = BASE_DIR / OUTPUT_REPORT

    output_path.write_text(
        json.dumps(
            final_report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    status = decision["status"]

    if status == "EXACT_ARTIFACT_PRESENT":
        verdict = "HISTORICAL_ARTIFACT_RECOVERABLE"

    elif status == "EXACT_ARTIFACT_PRESENT_IN_ARCHIVE":
        verdict = "HISTORICAL_ARTIFACT_ARCHIVE_RECOVERABLE"

    elif status == "HISTORICAL_RUNTIME_REPORT_REFERENCE_FOUND":
        verdict = "RUNTIME_PROVENANCE_FOUND_ARTIFACT_UNRECOVERED"

    elif status == "PRODUCER_RUNTIME_EVIDENCE_FOUND_REPORT_UNRECOVERED":
        verdict = "PRODUCER_RUNTIME_PROVENANCE_FOUND_ARTIFACT_UNRECOVERED"

    else:
        verdict = "HISTORICAL_RUNTIME_PROVENANCE_NOT_FOUND"

    print(
        f"HISTORICAL ELIGIBILITY PROVENANCE : "
        f"{verdict}"
    )

    print(
        "Producer executed : NO"
    )

    print(
        "Producer imported : NO"
    )

    print(
        "Eligibility executed : NO"
    )

    print(
        "Eligibility rebuilt : NO"
    )

    print(
        "Report regenerated : NO"
    )

    print(
        "Synthetic artifact : NO"
    )

    print(
        "Production DB writes : NONE"
    )

    print(
        "Source modification : "
        f"{'NONE' if source_invariant else 'DETECTED'}"
    )

    print(
        "Network access : NONE"
    )

    print(
        f"Runtime report : {output_path}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()