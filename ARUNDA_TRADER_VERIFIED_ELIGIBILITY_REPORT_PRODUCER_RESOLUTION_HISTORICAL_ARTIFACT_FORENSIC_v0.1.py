# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER
VERIFIED ELIGIBILITY REPORT PRODUCER RESOLUTION + HISTORICAL ARTIFACT FORENSIC v0.1
====================================================================================================

MODE
    READ-ONLY FORENSIC

OBJECTIVE
    Resolve the real producer / historical artifact provenance of:

        LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json

SAFETY
    Production DB writes : FORBIDDEN
    Production DB access  : READ ONLY
    Source modification   : FORBIDDEN
    Eligibility execution : FORBIDDEN
    Eligibility rebuild   : FORBIDDEN
    Candidate creation    : FORBIDDEN
    Synthetic report      : FORBIDDEN
    Direction inference   : FORBIDDEN
    Score reconstruction  : FORBIDDEN
    Network access        : FORBIDDEN

IMPORTANT
    This script NEVER creates the missing eligibility report.
    It only discovers existing source/artifact evidence.
====================================================================================================
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ==================================================================================================
# CONFIGURATION
# ==================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader").resolve()

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

TARGET_PRODUCER_NAME = (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

DOWNSTREAM_FRONTIER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"
)

SELF_NAME = Path(__file__).name

FORENSIC_REPORT_NAME = (
    "VERIFIED_ELIGIBILITY_REPORT_PRODUCER_RESOLUTION_HISTORICAL_ARTIFACT_FORENSIC_REPORT.json"
)

MAX_TEXT_SIZE = 100 * 1024 * 1024
MAX_BINARY_HASH_SIZE = 500 * 1024 * 1024

IGNORED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

# Files / directories that are potentially historical evidence.
HISTORICAL_DIR_HINTS = {
    "backup",
    "backups",
    "archive",
    "archives",
    "report",
    "reports",
    "runtime",
    "runtimes",
    "logs",
    "log",
    "output",
    "outputs",
    "artifacts",
    "artifact",
    "state",
    "states",
    "temp",
    "tmp",
    "_reports",
    "_report",
}

REPORT_PATTERNS = (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT",
    "SIGNAL_ELIGIBILITY",
    "ELIGIBILITY_NO_TRADE",
    "ELIGIBLE_SIGNAL",
)

PRODUCER_PATTERNS = (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE",
    "ELIGIBILITY_NO_TRADE_GATE",
    "SIGNAL_ELIGIBILITY",
)

CONSUMER_PATTERNS = (
    "LIVE_TRADE_CANDIDATE_RANKING",
    "UPSTREAM_ELIGIBILITY_CONSUMED",
    "eligible_pool",
    "eligibility_report",
)


# ==================================================================================================
# BASIC UTILITIES
# ==================================================================================================

def banner(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def safe_stat(path: Path):
    try:
        return path.stat()
    except Exception:
        return None


def safe_read_text(path: Path) -> str:
    try:
        stat = path.stat()

        if stat.st_size > MAX_TEXT_SIZE:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return ""


def file_record(path: Path, include_hash: bool = False) -> dict:
    stat = safe_stat(path)

    record = {
        "path": str(path.resolve()),
        "name": path.name,
        "size": stat.st_size if stat else None,
        "modified_time": (
            datetime.fromtimestamp(
                stat.st_mtime,
                timezone.utc,
            ).isoformat()
            if stat
            else None
        ),
    }

    if include_hash and stat and stat.st_size <= MAX_BINARY_HASH_SIZE:
        try:
            record["sha256"] = sha256_file(path)
        except Exception as exc:
            record["sha256_error"] = repr(exc)

    return record


# ==================================================================================================
# FRONTIER SOURCE ANALYSIS
# ==================================================================================================

def parse_python(path: Path):
    source = safe_read_text(path)

    if not source:
        return None, None

    try:
        return source, ast.parse(source)
    except SyntaxError as exc:
        return source, exc


def find_target_report_references(
    path: Path,
) -> list[dict]:

    source, parsed = parse_python(path)

    if not source or not isinstance(parsed, ast.AST):
        return []

    results = []

    for index, line in enumerate(
        source.splitlines(),
        1,
    ):

        if TARGET_REPORT.lower() in line.lower():

            results.append(
                {
                    "line": index,
                    "text": line.strip(),
                }
            )

    return results


# ==================================================================================================
# PROJECT FILE DISCOVERY
# ==================================================================================================

def discover_files() -> list[Path]:

    results = []

    for root, dirs, files in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIRS
        ]

        root_path = Path(root)

        for filename in files:

            path = root_path / filename

            if filename == SELF_NAME:
                continue

            results.append(path)

    return results


# ==================================================================================================
# EXACT REPORT ARTIFACT DISCOVERY
# ==================================================================================================

def discover_exact_report(files: list[Path]) -> list[dict]:

    matches = []

    for path in files:

        if path.name.lower() != TARGET_REPORT.lower():
            continue

        record = file_record(
            path,
            include_hash=True,
        )

        record["artifact_type"] = "EXACT_TARGET_REPORT"

        matches.append(record)

    return matches


# ==================================================================================================
# RENAMED / COPIED REPORT DISCOVERY
# ==================================================================================================

def score_report_artifact(
    path: Path,
    text: str,
) -> tuple[int, list[str]]:

    score = 0
    reasons = []

    name = normalize(path.name)
    content = normalize(text)

    # Filename evidence.
    for pattern in REPORT_PATTERNS:

        if normalize(pattern) in name:
            score += 20
            reasons.append(
                f"filename:{pattern}"
            )

    # Exact report stem fragments.
    fragments = (
        "live_signal",
        "eligibility",
        "no_trade",
        "eligible",
        "signal",
        "report",
    )

    for fragment in fragments:

        if fragment in name:
            score += 4
            reasons.append(
                f"filename_fragment:{fragment}"
            )

    # Content evidence.
    for pattern in REPORT_PATTERNS:

        if normalize(pattern) in content:
            score += 10
            reasons.append(
                f"content:{pattern}"
            )

    semantic_terms = (
        "eligible pool",
        "already eligible",
        "eligibility source",
        "no eligible signals",
        "upstream eligibility",
        "eligibility gate",
        "no trade",
    )

    for term in semantic_terms:

        if term in content:
            score += 5
            reasons.append(
                f"content:{term}"
            )

    return score, reasons


def discover_possible_report_artifacts(
    files: list[Path],
) -> list[dict]:

    results = []

    for path in files:

        normalized_name = normalize(path.name)

        relevant_name = (
            any(
                normalize(pattern) in normalized_name
                for pattern in REPORT_PATTERNS
            )
            or (
                "eligibility" in normalized_name
                and "report" in normalized_name
            )
        )

        text = ""

        if relevant_name or path.suffix.lower() in {
            ".json",
            ".txt",
            ".log",
            ".md",
            ".csv",
            ".py",
        }:
            text = safe_read_text(path)

        if not relevant_name and not text:
            continue

        score, reasons = score_report_artifact(
            path,
            text,
        )

        if score <= 0:
            continue

        record = file_record(
            path,
            include_hash=True,
        )

        record.update(
            {
                "score": score,
                "reasons": reasons,
                "content_size": len(text),
            }
        )

        results.append(record)

    results.sort(
        key=lambda x: (
            -x["score"],
            x["path"].lower(),
        )
    )

    return results


# ==================================================================================================
# PRODUCER DISCOVERY
# ==================================================================================================

def discover_producer_candidates(
    files: list[Path],
) -> list[dict]:

    results = []

    for path in files:

        if path.suffix.lower() != ".py":
            continue

        name = normalize(path.name)

        if not any(
            normalize(pattern) in name
            for pattern in PRODUCER_PATTERNS
        ):
            continue

        source, parsed = parse_python(path)

        record = file_record(
            path,
            include_hash=True,
        )

        record["name_match"] = True
        record["python_parse"] = isinstance(
            parsed,
            ast.AST,
        )

        if isinstance(parsed, SyntaxError):
            record["syntax_error"] = str(parsed)

        if source:

            lines = source.splitlines()

            target_lines = []

            for line_number, line in enumerate(
                lines,
                1,
            ):

                normalized_line = normalize(line)

                if (
                    TARGET_REPORT.lower()
                    in normalized_line
                ):
                    target_lines.append(
                        {
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )

            record["target_report_references"] = (
                target_lines
            )

            report_write_patterns = []

            for line_number, line in enumerate(
                lines,
                1,
            ):

                normalized_line = normalize(line)

                if (
                    (
                        "json.dump" in normalized_line
                        or "write_text" in normalized_line
                        or "open(" in normalized_line
                    )
                    and (
                        "report" in normalized_line
                        or "eligib" in normalized_line
                    )
                ):
                    report_write_patterns.append(
                        {
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )

            record["report_write_references"] = (
                report_write_patterns
            )

        results.append(record)

    results.sort(
        key=lambda x: (
            -len(
                x.get(
                    "target_report_references",
                    [],
                )
            ),
            -len(
                x.get(
                    "report_write_references",
                    [],
                )
            ),
            x["path"].lower(),
        )
    )

    return results


# ==================================================================================================
# ALL SOURCE REFERENCES
# ==================================================================================================

def discover_all_references(
    files: list[Path],
) -> list[dict]:

    references = []

    for path in files:

        if path.suffix.lower() not in {
            ".py",
            ".txt",
            ".md",
            ".json",
            ".log",
            ".csv",
        }:
            continue

        text = safe_read_text(path)

        if not text:
            continue

        lines = text.splitlines()

        for line_number, line in enumerate(
            lines,
            1,
        ):

            normalized_line = normalize(line)

            matched = []

            if (
                TARGET_REPORT.lower()
                in normalized_line
            ):
                matched.append(
                    "EXACT_REPORT_NAME"
                )

            for pattern in PRODUCER_PATTERNS:

                if normalize(pattern) in normalized_line:
                    matched.append(
                        f"PRODUCER_PATTERN:{pattern}"
                    )

            for pattern in CONSUMER_PATTERNS:

                if normalize(pattern) in normalized_line:
                    matched.append(
                        f"CONSUMER_PATTERN:{pattern}"
                    )

            if matched:

                references.append(
                    {
                        "path": str(path.resolve()),
                        "line": line_number,
                        "matches": matched,
                        "text": line.strip(),
                    }
                )

    return references


# ==================================================================================================
# HISTORICAL ARTIFACT TEMPORAL ANALYSIS
# ==================================================================================================

def classify_historical_path(path: Path) -> list[str]:

    parts = [
        normalize(part)
        for part in path.parts
    ]

    hits = []

    for part in parts:

        for hint in HISTORICAL_DIR_HINTS:

            if hint in part:
                hits.append(hint)

    return sorted(set(hits))


def historical_artifact_inventory(
    files: list[Path],
) -> list[dict]:

    results = []

    for path in files:

        hints = classify_historical_path(path)

        if not hints:
            continue

        normalized_name = normalize(path.name)

        if not (
            any(
                token in normalized_name
                for token in (
                    "elig",
                    "signal",
                    "report",
                    "trade",
                    "gate",
                    "outcome",
                )
            )
        ):
            continue

        record = file_record(
            path,
            include_hash=True,
        )

        record["historical_path_hints"] = hints

        results.append(record)

    results.sort(
        key=lambda x: (
            x["modified_time"] or "",
            x["path"].lower(),
        ),
        reverse=True,
    )

    return results


# ==================================================================================================
# REPORT CONTENT FORENSIC
# ==================================================================================================

def inspect_json_artifact(
    path: Path,
) -> dict:

    result = {
        "parseable_json": False,
        "keys": [],
        "snapshot_id": None,
        "eligible_pool": None,
        "row_count": None,
        "source": None,
        "engine": None,
        "status": None,
    }

    text = safe_read_text(path)

    if not text:
        return result

    try:
        data = json.loads(text)
    except Exception as exc:
        result["json_error"] = str(exc)
        return result

    result["parseable_json"] = True

    if isinstance(data, dict):

        result["keys"] = sorted(
            str(key)
            for key in data.keys()
        )

        lower_map = {
            str(key).lower(): value
            for key, value in data.items()
        }

        for key in (
            "snapshot_id",
            "snapshot",
            "snapshotid",
        ):

            if key in lower_map:
                result["snapshot_id"] = (
                    lower_map[key]
                )
                break

        for key in (
            "eligible_pool",
            "eligible",
            "eligible_candidates",
            "candidates",
        ):

            if key in lower_map:

                value = lower_map[key]

                if isinstance(value, list):
                    result["eligible_pool"] = len(
                        value
                    )
                else:
                    result["eligible_pool"] = value

                break

        for key in (
            "row_count",
            "rows",
            "count",
        ):

            if key in lower_map:
                value = lower_map[key]

                if isinstance(value, list):
                    result["row_count"] = len(
                        value
                    )
                else:
                    result["row_count"] = value

                break

        for key in (
            "source",
            "eligibility_source",
            "engine",
            "status",
        ):

            if key in lower_map:

                result[key] = lower_map[key]

    return result


# ==================================================================================================
# RESOLUTION LOGIC
# ==================================================================================================

def resolve_producer(
    producer_candidates: list[dict],
) -> dict:

    exact = []

    for candidate in producer_candidates:

        name = normalize(
            candidate["name"]
        )

        if normalize(TARGET_PRODUCER_NAME) == name:
            exact.append(candidate)

    if len(exact) == 1:

        return {
            "status": "RESOLVED",
            "method": "EXACT_PRODUCER_FILENAME",
            "candidate": exact[0],
        }

    if len(exact) > 1:

        return {
            "status": "AMBIGUOUS",
            "method": "EXACT_PRODUCER_FILENAME",
            "candidates": exact,
        }

    if len(producer_candidates) == 1:

        candidate = producer_candidates[0]

        if (
            candidate.get(
                "target_report_references"
            )
            or candidate.get(
                "report_write_references"
            )
        ):

            return {
                "status": "RESOLVED",
                "method": "UNIQUE_PRODUCER_WITH_REPORT_REFERENCE",
                "candidate": candidate,
            }

    return {
        "status": "UNRESOLVED",
        "method": "NO_UNIQUE_PRODUCER",
        "candidates": producer_candidates,
    }


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    started = datetime.now(timezone.utc)

    banner(
        "ARUNDA TRADER\n"
        "VERIFIED ELIGIBILITY REPORT PRODUCER RESOLUTION + "
        "HISTORICAL ARTIFACT FORENSIC v0.1"
    )

    print("MODE")
    print("READ-ONLY FORENSIC")
    print()

    print("TARGET REPORT")
    print(f"  {TARGET_REPORT}")
    print()

    print("TARGET PRODUCER")
    print(f"  {TARGET_PRODUCER_NAME}")
    print()

    print("SAFETY POLICY")
    print("Production DB writes : FORBIDDEN")
    print("Production DB access : READ ONLY")
    print("Source modification   : FORBIDDEN")
    print("Eligibility execution : FORBIDDEN")
    print("Eligibility rebuild   : FORBIDDEN")
    print("Candidate creation    : FORBIDDEN")
    print("Synthetic report      : FORBIDDEN")
    print("Direction inference   : FORBIDDEN")
    print("Score reconstruction  : FORBIDDEN")
    print("Network access        : FORBIDDEN")

    # ----------------------------------------------------------------------------------------------
    # Baseline target hashes.
    # ----------------------------------------------------------------------------------------------

    banner("PRODUCTION FRONTIER BASELINE")

    if not DOWNSTREAM_FRONTIER.exists():
        raise RuntimeError(
            "Downstream frontier was not found."
        )

    frontier_before_hash = sha256_file(
        DOWNSTREAM_FRONTIER
    )

    print(
        f"Frontier : {DOWNSTREAM_FRONTIER}"
    )

    print(
        f"SHA256   : {frontier_before_hash}"
    )

    references = find_target_report_references(
        DOWNSTREAM_FRONTIER
    )

    print()
    print("Exact report references in downstream frontier:")

    if references:
        for ref in references:
            print(
                f"  line {ref['line']:>4} | "
                f"{ref['text']}"
            )
    else:
        print("  NONE")

    # ----------------------------------------------------------------------------------------------
    # Discover project files.
    # ----------------------------------------------------------------------------------------------

    banner("PROJECT ARTIFACT INVENTORY")

    files = discover_files()

    print(
        f"Files discovered : {len(files)}"
    )

    # ----------------------------------------------------------------------------------------------
    # Exact target report.
    # ----------------------------------------------------------------------------------------------

    banner("EXACT REPORT ARTIFACT DISCOVERY")

    exact_reports = discover_exact_report(
        files
    )

    print(
        f"Exact report files found : {len(exact_reports)}"
    )

    for item in exact_reports:
        print()
        print(
            f"PATH   : {item['path']}"
        )
        print(
            f"SIZE   : {item['size']}"
        )
        print(
            f"SHA256 : {item.get('sha256')}"
        )
        print(
            f"MODIFIED UTC : {item['modified_time']}"
        )

        inspection = inspect_json_artifact(
            Path(item["path"])
        )

        item["content_forensic"] = inspection

        print(
            f"JSON parseable : "
            f"{inspection['parseable_json']}"
        )
        print(
            f"Snapshot ID    : "
            f"{inspection['snapshot_id']}"
        )
        print(
            f"Eligible pool  : "
            f"{inspection['eligible_pool']}"
        )

    # ----------------------------------------------------------------------------------------------
    # Producer discovery.
    # ----------------------------------------------------------------------------------------------

    banner("PRODUCER DISCOVERY")

    producer_candidates = (
        discover_producer_candidates(
            files
        )
    )

    print(
        f"Producer candidates : "
        f"{len(producer_candidates)}"
    )

    for index, candidate in enumerate(
        producer_candidates,
        1,
    ):

        print()
        print(
            f"{index:>3} | "
            f"{candidate['path']}"
        )

        print(
            f"     SHA256 : "
            f"{candidate.get('sha256')}"
        )

        print(
            f"     Target report references : "
            f"{len(candidate.get('target_report_references', []))}"
        )

        for ref in candidate.get(
            "target_report_references",
            [],
        ):
            print(
                f"       line {ref['line']:>4} | "
                f"{ref['text']}"
            )

        print(
            f"     Report write references : "
            f"{len(candidate.get('report_write_references', []))}"
        )

        for ref in candidate.get(
            "report_write_references",
            [],
        ):
            print(
                f"       line {ref['line']:>4} | "
                f"{ref['text']}"
            )

    # ----------------------------------------------------------------------------------------------
    # All references.
    # ----------------------------------------------------------------------------------------------

    banner("ALL HISTORICAL / SOURCE REFERENCES")

    all_references = discover_all_references(
        files
    )

    print(
        f"References discovered : "
        f"{len(all_references)}"
    )

    for item in all_references[:500]:

        print(
            f"{item['path']}"
        )

        print(
            f"  line {item['line']:>4} | "
            f"{', '.join(item['matches'])}"
        )

        print(
            f"  {item['text']}"
        )

    # ----------------------------------------------------------------------------------------------
    # Historical artifact inventory.
    # ----------------------------------------------------------------------------------------------

    banner("HISTORICAL ARTIFACT INVENTORY")

    historical_artifacts = (
        historical_artifact_inventory(
            files
        )
    )

    print(
        f"Historical artifact candidates : "
        f"{len(historical_artifacts)}"
    )

    for index, item in enumerate(
        historical_artifacts[:200],
        1,
    ):

        print(
            f"{index:>3} | "
            f"{item['modified_time']} | "
            f"{item['path']}"
        )

    # ----------------------------------------------------------------------------------------------
    # Possible renamed/copy artifacts.
    # ----------------------------------------------------------------------------------------------

    banner("POSSIBLE RENAMED / COPIED REPORT ARTIFACTS")

    possible_artifacts = (
        discover_possible_report_artifacts(
            files
        )
    )

    print(
        f"Possible artifacts : "
        f"{len(possible_artifacts)}"
    )

    for index, item in enumerate(
        possible_artifacts[:100],
        1,
    ):

        print(
            f"{index:>3} | "
            f"score={item['score']:>3} | "
            f"{item['path']}"
        )

        print(
            f"     SHA256 : "
            f"{item.get('sha256')}"
        )

        print(
            f"     Reasons: "
            f"{', '.join(item['reasons'][:12])}"
        )

    # ----------------------------------------------------------------------------------------------
    # Producer resolution.
    # ----------------------------------------------------------------------------------------------

    banner("PRODUCER RESOLUTION")

    producer_resolution = resolve_producer(
        producer_candidates
    )

    print(
        f"STATUS : "
        f"{producer_resolution['status']}"
    )

    print(
        f"METHOD : "
        f"{producer_resolution['method']}"
    )

    if producer_resolution.get(
        "candidate"
    ):

        candidate = producer_resolution[
            "candidate"
        ]

        print(
            f"PRODUCER : "
            f"{candidate['path']}"
        )

    # ----------------------------------------------------------------------------------------------
    # Artifact resolution.
    # ----------------------------------------------------------------------------------------------

    banner("ARTIFACT RESOLUTION")

    artifact_resolution_status = (
        "RESOLVED"
        if len(exact_reports) == 1
        else "AMBIGUOUS"
        if len(exact_reports) > 1
        else "NOT_PRESENT"
    )

    print(
        f"Exact target artifact : "
        f"{artifact_resolution_status}"
    )

    # ----------------------------------------------------------------------------------------------
    # Critical safety check.
    # ----------------------------------------------------------------------------------------------

    banner("SOURCE INTEGRITY CHECK")

    frontier_after_hash = sha256_file(
        DOWNSTREAM_FRONTIER
    )

    frontier_unchanged = (
        frontier_before_hash
        == frontier_after_hash
    )

    print(
        f"Before SHA256 : "
        f"{frontier_before_hash}"
    )

    print(
        f"After SHA256  : "
        f"{frontier_after_hash}"
    )

    print(
        "Source invariant : "
        f"{'PASS' if frontier_unchanged else 'FAIL'}"
    )

    if not frontier_unchanged:
        raise RuntimeError(
            "Production frontier source changed during forensic run."
        )

    # ----------------------------------------------------------------------------------------------
    # Final resolution.
    # ----------------------------------------------------------------------------------------------

    # The important distinction:
    #
    # RESOLVED does NOT mean we are allowed to manufacture the report.
    #
    # A valid resolution requires either:
    #
    #   1. exact existing report artifact
    #   2. unique producer with exact report reference
    #
    # If the producer exists but the artifact is absent, we report:
    #
    #   PRODUCER_RESOLVED_ARTIFACT_MISSING
    #
    # This is intentional.

    if len(exact_reports) == 1:

        final_status = (
            "EXACT_ARTIFACT_RESOLVED"
        )

        final_reason = (
            "The exact verified eligibility report "
            "artifact exists in the project tree."
        )

    elif (
        producer_resolution["status"]
        == "RESOLVED"
    ):

        final_status = (
            "PRODUCER_RESOLVED_ARTIFACT_MISSING"
        )

        final_reason = (
            "The producer of the required report was "
            "resolved, but the historical report artifact "
            "itself was not found. The report must not be "
            "reconstructed or regenerated in this forensic stage."
        )

    else:

        final_status = (
            "PRODUCER_AND_ARTIFACT_UNRESOLVED"
        )

        final_reason = (
            "Neither a unique producer nor the exact "
            "historical report artifact could be resolved."
        )

    banner("FINAL VERDICT")

    print(
        f"FORENSIC RESOLUTION : {final_status}"
    )

    print(
        f"Exact report present : "
        f"{'YES' if exact_reports else 'NO'}"
    )

    print(
        f"Producer resolved     : "
        f"{'YES' if producer_resolution['status'] == 'RESOLVED' else 'NO'}"
    )

    print(
        "Eligibility executed   : NO"
    )

    print(
        "Eligibility rebuilt    : NO"
    )

    print(
        "Synthetic report       : NO"
    )

    print(
        "Production DB writes   : NONE"
    )

    print(
        "Source modification    : NONE"
    )

    print(
        "Network access         : NONE"
    )

    print(
        "Production invariant   : "
        f"{'PASS' if frontier_unchanged else 'FAIL'}"
    )

    print()
    print(
        "REASON:"
    )
    print(
        final_reason
    )

    # ----------------------------------------------------------------------------------------------
    # Machine-readable forensic report.
    # ----------------------------------------------------------------------------------------------

    finished = datetime.now(timezone.utc)

    output = {
        "script": SELF_NAME,
        "version": "v0.1",
        "mode": "READ_ONLY_FORENSIC",
        "timestamp_started_utc": started.isoformat(),
        "timestamp_finished_utc": finished.isoformat(),
        "project_root": str(PROJECT_ROOT),
        "target_report": TARGET_REPORT,
        "target_producer_name": TARGET_PRODUCER_NAME,
        "downstream_frontier": str(
            DOWNSTREAM_FRONTIER
        ),
        "downstream_frontier_sha256_before": (
            frontier_before_hash
        ),
        "downstream_frontier_sha256_after": (
            frontier_after_hash
        ),
        "production_source_invariant": (
            frontier_unchanged
        ),
        "exact_report_artifacts": exact_reports,
        "producer_candidates": producer_candidates,
        "producer_resolution": producer_resolution,
        "all_references": all_references,
        "historical_artifacts": historical_artifacts[:500],
        "possible_report_artifacts": possible_artifacts[:200],
        "final_status": final_status,
        "final_reason": final_reason,
        "safety": {
            "production_db_write": False,
            "production_source_modification": False,
            "eligibility_execution": False,
            "eligibility_rebuild": False,
            "candidate_creation": False,
            "synthetic_report": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "network_access": False,
        },
        "next_action": (
            "If EXACT_ARTIFACT_RESOLVED: stage the exact artifact "
            "into an isolated runtime without modification. "
            "If PRODUCER_RESOLVED_ARTIFACT_MISSING: perform a "
            "producer execution-boundary forensic audit before "
            "any regeneration is considered."
        ),
    }

    output_path = (
        PROJECT_ROOT
        / FORENSIC_REPORT_NAME
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"Forensic report : {output_path}"
    )


if __name__ == "__main__":
    main()