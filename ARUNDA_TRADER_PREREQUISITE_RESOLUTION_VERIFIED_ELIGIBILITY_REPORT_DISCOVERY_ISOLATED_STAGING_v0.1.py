# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER
PREREQUISITE RESOLUTION — VERIFIED ELIGIBILITY REPORT DISCOVERY + ISOLATED STAGING v0.1
====================================================================================================

OBJECTIVE
Resolve the exact prerequisite required by the existing verified downstream
eligibility/candidate frontier.

This script is READ-ONLY against the production project.

SAFETY
====================================================================================================
Production DB writes : FORBIDDEN
Production DB access  : READ ONLY
Source modification   : FORBIDDEN
Synthetic report      : FORBIDDEN
Eligibility rebuild   : FORBIDDEN
Candidate creation    : FORBIDDEN
Direction inference   : FORBIDDEN
Score reconstruction  : FORBIDDEN
Production execution  : FORBIDDEN
Network access        : FORBIDDEN
====================================================================================================
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone


# ==================================================================================================
# CONFIGURATION
# ==================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader").resolve()

TARGET_FRONTIER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"
)

SELF_NAME = Path(__file__).name

REPORT_NAME = (
    "PREREQUISITE_RESOLUTION_VERIFIED_ELIGIBILITY_REPORT_DISCOVERY"
    "_ISOLATED_STAGING_REPORT.json"
)

MAX_FILE_SIZE = 50 * 1024 * 1024

IGNORED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "_backups",
}

REPORT_EXTENSIONS = {
    ".json",
    ".txt",
    ".log",
    ".csv",
    ".md",
}

# Strong indicators that a file may be the prerequisite report.
ELIGIBILITY_TERMS = (
    "eligibility",
    "eligible",
    "eligibility_report",
    "eligible_signal",
    "eligible_signals",
    "no_trade",
    "signal_eligibility",
)

VERIFIED_TERMS = (
    "verified",
    "verification",
    "forensic",
    "reconciliation",
    "readiness",
    "gate",
)

REPORT_TERMS = (
    "report",
    "result",
    "output",
    "reconciliation",
    "eligibility",
)


# ==================================================================================================
# OUTPUT
# ==================================================================================================

def banner(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def safe_read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return ""


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


# ==================================================================================================
# TARGET FRONTIER ANALYSIS
# ==================================================================================================

def analyze_frontier() -> dict:
    result = {
        "exists": TARGET_FRONTIER.exists(),
        "path": str(TARGET_FRONTIER),
        "python_parse": False,
        "eligibility_report_references": [],
        "path_references": [],
        "open_references": [],
        "environment_references": [],
        "string_literals": [],
    }

    if not TARGET_FRONTIER.exists():
        return result

    source = TARGET_FRONTIER.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    try:
        tree = ast.parse(source)
        result["python_parse"] = True
    except SyntaxError as exc:
        result["syntax_error"] = str(exc)
        return result

    class Visitor(ast.NodeVisitor):

        def __init__(self):
            self.strings = []

        def visit_Constant(self, node):
            if isinstance(node.value, str):
                self.strings.append(node.value)

            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(tree)

    result["string_literals"] = visitor.strings

    for value in visitor.strings:
        normalized = normalize_text(value)

        if any(term in normalized for term in ELIGIBILITY_TERMS):
            result["eligibility_report_references"].append(value)

        if (
            "report" in normalized
            or "eligible" in normalized
            or "eligibility" in normalized
        ):
            result["path_references"].append(value)

    # Search source itself for likely runtime constructions.
    lines = source.splitlines()

    for line_number, line in enumerate(lines, 1):
        normalized = normalize_text(line)

        if (
            "report" in normalized
            and (
                "open(" in normalized
                or "exists" in normalized
                or "path(" in normalized
                or "read_text" in normalized
                or "json" in normalized
            )
        ):
            result["open_references"].append(
                {
                    "line": line_number,
                    "text": line.strip(),
                }
            )

        if (
            "environment" in normalized
            or "env" in normalized
            or "os.environ" in normalized
        ):
            result["environment_references"].append(
                {
                    "line": line_number,
                    "text": line.strip(),
                }
            )

    # De-duplicate while preserving order.
    result["eligibility_report_references"] = list(
        dict.fromkeys(result["eligibility_report_references"])
    )

    result["path_references"] = list(
        dict.fromkeys(result["path_references"])
    )

    return result


# ==================================================================================================
# SOURCE STRING EXTRACTION
# ==================================================================================================

def discover_literal_report_names(frontier_info: dict) -> list[str]:
    names = []

    for value in frontier_info.get("string_literals", []):
        normalized = normalize_text(value)

        if (
            "report" in normalized
            or "eligib" in normalized
            or "eligible" in normalized
        ):
            if len(value) <= 500:
                names.append(value)

    return list(dict.fromkeys(names))


# ==================================================================================================
# FILE DISCOVERY
# ==================================================================================================

def candidate_score(
    path: Path,
    content: str,
    literal_hints: list[str],
) -> tuple[int, list[str]]:

    score = 0
    reasons = []

    name = normalize_text(path.name)
    text = normalize_text(content)

    # Filename evidence.
    for term in ELIGIBILITY_TERMS:
        if term in name:
            score += 10
            reasons.append(f"filename:{term}")

    for term in VERIFIED_TERMS:
        if term in name:
            score += 5
            reasons.append(f"filename:{term}")

    for term in REPORT_TERMS:
        if term in name:
            score += 3
            reasons.append(f"filename:{term}")

    # Content evidence.
    for term in ELIGIBILITY_TERMS:
        if term in text:
            score += 4
            reasons.append(f"content:{term}")

    for term in VERIFIED_TERMS:
        if term in text:
            score += 2
            reasons.append(f"content:{term}")

    # Exact literal hint matching.
    for hint in literal_hints:
        normalized_hint = normalize_text(hint)

        if (
            normalized_hint
            and len(normalized_hint) >= 6
            and normalized_hint in text
        ):
            score += 25
            reasons.append("exact_literal_reference")

    return score, reasons


def discover_report_candidates(
    literal_hints: list[str],
) -> list[dict]:

    candidates = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        # Do not enter known irrelevant directories.
        dirs[:] = [
            d
            for d in dirs
            if d not in IGNORED_DIR_NAMES
        ]

        for filename in files:

            path = root_path / filename

            if filename == SELF_NAME:
                continue

            if path.suffix.lower() not in REPORT_EXTENSIONS:
                continue

            try:
                size = path.stat().st_size
            except OSError:
                continue

            if size > MAX_FILE_SIZE:
                continue

            # Filename quick filter.
            normalized_name = normalize_text(filename)

            filename_relevant = (
                any(term in normalized_name for term in ELIGIBILITY_TERMS)
                or (
                    "report" in normalized_name
                    and any(
                        term in normalized_name
                        for term in VERIFIED_TERMS
                    )
                )
                or "eligible" in normalized_name
            )

            # Read content only for relevant names.
            content = safe_read_text(path)

            if not filename_relevant and not content:
                continue

            score, reasons = candidate_score(
                path,
                content,
                literal_hints,
            )

            if score <= 0:
                continue

            candidates.append(
                {
                    "path": str(path.resolve()),
                    "name": path.name,
                    "suffix": path.suffix.lower(),
                    "size": size,
                    "score": score,
                    "reasons": reasons,
                    "sha256": sha256_file(path),
                }
            )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["name"].lower(),
        )
    )

    return candidates


# ==================================================================================================
# ISOLATED STAGING
# ==================================================================================================

def create_isolated_runtime() -> tuple[Path, Path]:
    runtime_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_verified_eligibility_isolated_"
        )
    ).resolve()

    staging_dir = runtime_dir / "prerequisite"
    staging_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return runtime_dir, staging_dir


def stage_candidate(
    source_path: Path,
    staging_dir: Path,
) -> dict:

    staged_path = staging_dir / source_path.name

    shutil.copy2(
        source_path,
        staged_path,
    )

    source_hash = sha256_file(source_path)
    staged_hash = sha256_file(staged_path)

    return {
        "source": str(source_path),
        "staged": str(staged_path),
        "source_size": source_path.stat().st_size,
        "staged_size": staged_path.stat().st_size,
        "source_sha256": source_hash,
        "staged_sha256": staged_hash,
        "hash_match": source_hash == staged_hash,
    }


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    started = datetime.now(timezone.utc)

    banner(
        "ARUNDA TRADER\n"
        "PREREQUISITE RESOLUTION — VERIFIED ELIGIBILITY REPORT "
        "DISCOVERY + ISOLATED STAGING v0.1"
    )

    print("OBJECTIVE")
    print(
        "Resolve the exact verified eligibility report required by the "
        "existing downstream frontier."
    )
    print()
    print("No eligibility logic is reconstructed.")
    print("No candidate is created.")
    print("No production DB write is permitted.")
    print("No production source modification is permitted.")
    print("No synthetic report is created.")
    print("No network access is performed.")
    print()

    banner("SAFETY POLICY")

    print("Production DB writes : FORBIDDEN")
    print("Production DB access : READ ONLY")
    print("Source modification   : FORBIDDEN")
    print("Eligibility rebuild   : FORBIDDEN")
    print("Candidate creation    : FORBIDDEN")
    print("Direction inference   : FORBIDDEN")
    print("Score reconstruction  : FORBIDDEN")
    print("Synthetic report      : FORBIDDEN")
    print("Network access        : FORBIDDEN")

    banner("PRODUCTION FRONTIER")

    print(f"Project root : {PROJECT_ROOT}")
    print(f"Target       : {TARGET_FRONTIER}")
    print(f"Target exists: {TARGET_FRONTIER.exists()}")

    if not TARGET_FRONTIER.exists():
        raise RuntimeError(
            "Target frontier was not found."
        )

    before_frontier_hash = sha256_file(TARGET_FRONTIER)

    print(f"Target SHA256: {before_frontier_hash}")

    banner("FRONTIER PREREQUISITE ANALYSIS")

    frontier_info = analyze_frontier()

    print(
        f"Python source : "
        f"{'PASS' if frontier_info.get('exists') else 'FAIL'}"
    )

    print(
        f"AST parse     : "
        f"{'PASS' if frontier_info.get('python_parse') else 'FAIL'}"
    )

    print()
    print("Eligibility/report-related literals discovered:")

    literal_hints = discover_literal_report_names(
        frontier_info
    )

    if literal_hints:
        for value in literal_hints:
            print(f"  - {value}")
    else:
        print("  NONE")

    print()
    print("Report-related source references:")

    if frontier_info.get("open_references"):
        for item in frontier_info["open_references"]:
            print(
                f"  line {item['line']:>4} | "
                f"{item['text']}"
            )
    else:
        print("  NONE")

    banner("VERIFIED ELIGIBILITY REPORT DISCOVERY")

    candidates = discover_report_candidates(
        literal_hints
    )

    print(
        f"Candidate reports discovered : {len(candidates)}"
    )

    if candidates:
        for index, candidate in enumerate(
            candidates[:100],
            1,
        ):
            print(
                f"{index:>3} | "
                f"score={candidate['score']:>3} | "
                f"{candidate['path']}"
            )
    else:
        print("NO CANDIDATE REPORTS DISCOVERED")

    banner("RESOLUTION DECISION")

    # Safety rule:
    # Do NOT automatically stage an ambiguous candidate.
    #
    # Only a uniquely strongest candidate with meaningful evidence may be staged.

    selected = None

    if candidates:

        top_score = candidates[0]["score"]

        top_candidates = [
            item
            for item in candidates
            if item["score"] == top_score
        ]

        if len(top_candidates) == 1 and top_score >= 15:
            selected = top_candidates[0]

    if selected is None:

        print("STATUS : BLOCKED")
        print()
        print(
            "A unique, sufficiently evidenced verified eligibility "
            "report could not be resolved automatically."
        )
        print()
        print(
            "No report was staged."
        )
        print(
            "No source was modified."
        )
        print(
            "No production DB was modified."
        )

        report = {
            "script": SELF_NAME,
            "version": "v0.1",
            "status": "BLOCKED",
            "reason": (
                "Verified eligibility report could not be resolved "
                "uniquely and safely."
            ),
            "project_root": str(PROJECT_ROOT),
            "target_frontier": str(TARGET_FRONTIER),
            "target_frontier_sha256": before_frontier_hash,
            "candidate_count": len(candidates),
            "candidates": candidates[:100],
            "production_modification": False,
            "database_write": False,
            "synthetic_report": False,
            "network_access": False,
            "timestamp_utc": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        output_path = (
            PROJECT_ROOT / REPORT_NAME
        )

        output_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        banner("FINAL VERDICT")

        print("PREREQUISITE RESOLUTION : BLOCKED")
        print("Verified report staged  : NO")
        print("Source modification     : NONE")
        print("Production DB writes    : NONE")
        print("Synthetic report        : NONE")
        print("Network access          : NONE")
        print()
        print(f"Runtime report : {output_path}")

        return

    print("STATUS : RESOLVED")
    print()
    print(f"SELECTED REPORT : {selected['path']}")
    print(f"SCORE           : {selected['score']}")
    print(f"SHA256          : {selected['sha256']}")

    banner("ISOLATED STAGING")

    runtime_dir, staging_dir = create_isolated_runtime()

    print(f"Runtime directory : {runtime_dir}")
    print(f"Staging directory : {staging_dir}")

    staged = stage_candidate(
        Path(selected["path"]),
        staging_dir,
    )

    print()
    print(f"Source size       : {staged['source_size']}")
    print(f"Staged size       : {staged['staged_size']}")
    print(f"Source SHA256     : {staged['source_sha256']}")
    print(f"Staged SHA256     : {staged['staged_sha256']}")
    print(
        "Hash identity     : "
        f"{'PASS' if staged['hash_match'] else 'FAIL'}"
    )

    if not staged["hash_match"]:
        raise RuntimeError(
            "Staged prerequisite hash does not match source hash."
        )

    banner("POST-STAGING SOURCE INVARIANT")

    after_frontier_hash = sha256_file(
        TARGET_FRONTIER
    )

    print(
        "Target source invariant : "
        f"{'PASS' if before_frontier_hash == after_frontier_hash else 'FAIL'}"
    )

    if before_frontier_hash != after_frontier_hash:
        raise RuntimeError(
            "Target frontier changed unexpectedly."
        )

    banner("FINAL VERDICT")

    print("PREREQUISITE RESOLUTION : PASS")
    print("Verified report staged  : YES")
    print("Source modification     : NONE")
    print("Production DB writes    : NONE")
    print("Synthetic report        : NONE")
    print("Network access          : NONE")
    print("Staged hash identity    : PASS")
    print()
    print(f"Isolated runtime : {runtime_dir}")
    print(f"Staged report    : {staged['staged']}")

    finished = datetime.now(timezone.utc)

    report = {
        "script": SELF_NAME,
        "version": "v0.1",
        "status": "PASS",
        "objective": (
            "Discover and isolate-stage the exact verified "
            "eligibility report prerequisite."
        ),
        "timestamp_started_utc": started.isoformat(),
        "timestamp_finished_utc": finished.isoformat(),
        "project_root": str(PROJECT_ROOT),
        "target_frontier": str(TARGET_FRONTIER),
        "target_frontier_sha256_before": before_frontier_hash,
        "target_frontier_sha256_after": after_frontier_hash,
        "target_frontier_invariant": (
            before_frontier_hash == after_frontier_hash
        ),
        "selected_report": selected,
        "staging": staged,
        "runtime_directory": str(runtime_dir),
        "production_db_write": False,
        "production_source_modified": False,
        "synthetic_report": False,
        "network_access": False,
        "next_action": (
            "Re-run the existing "
            "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py "
            "inside an isolated runtime with the staged verified "
            "eligibility prerequisite."
        ),
    }

    output_path = (
        runtime_dir / REPORT_NAME
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Runtime report   : {output_path}")


if __name__ == "__main__":
    main()