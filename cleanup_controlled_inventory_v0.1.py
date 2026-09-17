# -*- coding: utf-8 -*-
"""
ARUNDA TRADER — CLEANUP CONTROLLED INVENTORY v0.1

MODE:
    READ-ONLY INVENTORY

IMPORTANT:
    - NO FILE DELETE
    - NO DB WRITE
    - NO DB RESET
    - NO MIGRATION
    - NO RUNTIME EXECUTION
    - NO CP RE-AUDIT
    - NO PRODUCTION LOGIC CHANGE
    - EXECUTION MUST REMAIN DISABLED

PURPOSE:
    Inventory project root and classify artifacts safely before any cleanup.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path
from collections import defaultdict


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent
DB_NAME = "arunda.db"

EXECUTION_ENABLED_PATTERN = re.compile(
    r"\bEXECUTION_ENABLED\s*=\s*(True|False)\b",
    re.IGNORECASE,
)

PYTHON_EXTENSIONS = {".py"}
DATA_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3",
    ".json", ".csv", ".txt", ".log",
    ".yaml", ".yml",
}
BACKUP_EXTENSIONS = {
    ".bak", ".backup", ".old", ".orig", ".copy",
}
TEMP_EXTENSIONS = {
    ".tmp", ".temp", ".cache",
}

PRODUCTION_FILES = {
    "arunda_pipeline.py",
    "feature_contract.py",
    "feature_snapshot_reader.py",
    "score_producer.py",
    "signal_engine.py",
    "signal_validator.py",
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "trade_gate_engine.py",
    "market_snapshot_engine.py",
    "market_data_engine.py",
    "opportunity_engine.py",
}

PRODUCTION_KEYWORDS = {
    "feature",
    "signal",
    "score",
    "decision",
    "risk",
    "trade_gate",
    "order_intent",
    "market_snapshot",
    "market_data",
    "opportunity",
    "execution",
    "pipeline",
}

FORENSIC_KEYWORDS = {
    "forensic",
    "audit",
    "diagnostic",
    "verify",
    "verification",
    "repair",
    "tolerance",
    "fingerprint",
    "runtime_verify",
    "contract_check",
    "coverage",
    "inspect",
    "probe",
}

CHECKPOINT_KEYWORDS = {
    "cp1", "cp2", "cp3", "cp4", "cp5", "cp6",
    "cp7", "cp8", "cp9", "cp10", "cp11", "cp12",
    "checkpoint",
    "release",
    "preflight",
    "observation",
}

LEGACY_KEYWORDS = {
    "legacy",
    "museum",
    "old",
    "deprecated",
    "archive",
    "archived",
    "obsolete",
}

TEMP_KEYWORDS = {
    "temp",
    "tmp",
    "cache",
    "runtime.txt",
    "__pycache__",
}

# Explicitly protected regardless of other classification.
PROTECTED_FILES = {
    "arunda.db",
    "arunda_pipeline.py",
    "feature_contract.py",
    "feature_snapshot_reader.py",
    "score_producer.py",
    "signal_engine.py",
    "signal_validator.py",
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "trade_gate_engine.py",
    "market_snapshot_engine.py",
    "market_data_engine.py",
    "opportunity_engine.py",
}


# ============================================================
# HELPERS
# ============================================================

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_DIR))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def python_imports(path: Path) -> set[str]:
    result = set()

    if path.suffix.lower() != ".py":
        return result

    text = read_text(path)
    if not text:
        return result

    try:
        tree = ast.parse(text, filename=str(path))
    except Exception:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module.split(".")[0])

    return result


def references_file(source: Path, target_name: str) -> bool:
    text = read_text(source)

    if not text:
        return False

    stem = Path(target_name).stem

    patterns = [
        rf"\b{re.escape(target_name)}\b",
        rf"\b{re.escape(stem)}\b",
    ]

    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def contains_any(text: str, keywords: set[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def is_protected(path: Path) -> bool:
    return path.name.lower() in {
        x.lower() for x in PROTECTED_FILES
    }


# ============================================================
# CLASSIFICATION
# ============================================================

def classify(path: Path, all_files: list[Path]) -> tuple[str, str]:
    name = path.name.lower()
    r = rel(path).lower()

    if is_protected(path):
        return (
            "A) CURRENT PRODUCTION",
            "EXPLICITLY PROTECTED PRODUCTION ARTIFACT",
        )

    if path.is_dir():
        if "__pycache__" in r or contains_any(r, TEMP_KEYWORDS):
            return (
                "F) TEMP / CACHE / LOG",
                "CACHE/TEMP DIRECTORY",
            )

        if contains_any(r, LEGACY_KEYWORDS):
            return (
                "E) LEGACY / MUSEUM",
                "LEGACY/ARCHIVE DIRECTORY",
            )

        if contains_any(r, FORENSIC_KEYWORDS):
            return (
                "C) FORENSIC / DIAGNOSTIC",
                "FORENSIC/DIAGNOSTIC DIRECTORY",
            )

        if contains_any(r, CHECKPOINT_KEYWORDS):
            return (
                "D) BACKUP / CHECKPOINT ARTIFACT",
                "CHECKPOINT/RELEASE DIRECTORY",
            )

        return (
            "G) UNKNOWN / NEEDS REVIEW",
            "DIRECTORY REQUIRES REVIEW",
        )

    # --------------------------------------------------------
    # Current production support
    # --------------------------------------------------------

    if path.suffix.lower() == ".py":

        if contains_any(name, PRODUCTION_KEYWORDS):
            # Not automatically production.
            # Search whether production pipeline references it.
            pipeline = PROJECT_DIR / "arunda_pipeline.py"

            if pipeline.exists() and references_file(
                pipeline,
                path.name
            ):
                return (
                    "A) CURRENT PRODUCTION",
                    "REFERENCED BY PRODUCTION ENTRYPOINT",
                )

            # Important supporting Python module.
            return (
                "B) VERIFIED PRODUCTION SUPPORT",
                "PRODUCTION-RELATED PYTHON MODULE; ENTRYPOINT REFERENCE NOT PROVEN",
            )

        if contains_any(name, FORENSIC_KEYWORDS):
            return (
                "C) FORENSIC / DIAGNOSTIC",
                "FORENSIC/DIAGNOSTIC PYTHON ARTIFACT",
            )

        if contains_any(name, CHECKPOINT_KEYWORDS):
            return (
                "D) BACKUP / CHECKPOINT ARTIFACT",
                "CHECKPOINT/RELEASE PYTHON ARTIFACT",
            )

        if contains_any(name, LEGACY_KEYWORDS):
            return (
                "E) LEGACY / MUSEUM",
                "LEGACY/DEPRECATED PYTHON ARTIFACT",
            )

    # --------------------------------------------------------
    # Legacy
    # --------------------------------------------------------

    if contains_any(name, LEGACY_KEYWORDS) or contains_any(r, LEGACY_KEYWORDS):
        return (
            "E) LEGACY / MUSEUM",
            "LEGACY/ARCHIVE ARTIFACT",
        )

    # --------------------------------------------------------
    # Checkpoint / backup
    # --------------------------------------------------------

    if path.suffix.lower() in BACKUP_EXTENSIONS:
        return (
            "D) BACKUP / CHECKPOINT ARTIFACT",
            "BACKUP EXTENSION",
        )

    if contains_any(name, CHECKPOINT_KEYWORDS):
        return (
            "D) BACKUP / CHECKPOINT ARTIFACT",
            "CHECKPOINT/RELEASE ARTIFACT",
        )

    # --------------------------------------------------------
    # Temp / cache / log
    # --------------------------------------------------------

    if (
        path.suffix.lower() in TEMP_EXTENSIONS
        or contains_any(name, TEMP_KEYWORDS)
    ):
        return (
            "F) TEMP / CACHE / LOG",
            "TEMP/CACHE ARTIFACT",
        )

    if path.suffix.lower() == ".log":
        return (
            "F) TEMP / CACHE / LOG",
            "LOG FILE",
        )

    # --------------------------------------------------------
    # Database / production data
    # --------------------------------------------------------

    if path.name.lower() == DB_NAME:
        return (
            "A) CURRENT PRODUCTION",
            "PRODUCTION DATABASE — PROTECTED",
        )

    if path.suffix.lower() in DATA_EXTENSIONS:
        return (
            "G) UNKNOWN / NEEDS REVIEW",
            "DATA ARTIFACT — DO NOT REMOVE WITHOUT REVIEW",
        )

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return (
        "G) UNKNOWN / NEEDS REVIEW",
        "NO SAFE CLASSIFICATION",
    )


# ============================================================
# PRODUCTION IMPORT GRAPH
# ============================================================

def build_import_graph(py_files: list[Path]) -> dict[str, set[str]]:
    graph = {}

    for p in py_files:
        graph[p.name] = python_imports(p)

    return graph


def resolve_local_imports(
    module_name: str,
    py_by_stem: dict[str, Path],
) -> Path | None:

    return py_by_stem.get(module_name)


def production_dependency_closure(
    py_files: list[Path],
) -> set[str]:

    by_stem = {
        p.stem: p
        for p in py_files
    }

    graph = build_import_graph(py_files)

    pipeline = PROJECT_DIR / "arunda_pipeline.py"

    if not pipeline.exists():
        return set()

    queue = ["arunda_pipeline"]
    visited = set()

    while queue:
        current = queue.pop(0)

        if current in visited:
            continue

        visited.add(current)

        for imported in graph.get(
            f"{current}.py",
            graph.get(current, set())
        ):
            if imported in by_stem and imported not in visited:
                queue.append(imported)

    return {
        by_stem[x].name
        for x in visited
        if x in by_stem
    }


# ============================================================
# EXECUTION SAFETY SOURCE CHECK
# ============================================================

def execution_enabled_state() -> tuple[str, str]:
    pipeline = PROJECT_DIR / "arunda_pipeline.py"

    if not pipeline.exists():
        return "MISSING", "pipeline missing"

    text = read_text(pipeline)

    matches = EXECUTION_ENABLED_PATTERN.findall(text)

    if not matches:
        return "NOT_FOUND", "EXECUTION_ENABLED assignment not found"

    values = {x.lower() for x in matches}

    if values == {"false"}:
        return "FALSE", "all discovered assignments are False"

    if "true" in values:
        return "TRUE", "EXECUTION_ENABLED=True found"

    return "UNKNOWN", "ambiguous assignment state"


# ============================================================
# MAIN INVENTORY
# ============================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — CLEANUP CONTROLLED INVENTORY v0.1")
    print("=" * 100)
    print("MODE              : READ-ONLY")
    print(f"PROJECT DIR       : {PROJECT_DIR}")
    print(f"DATABASE          : {PROJECT_DIR / DB_NAME}")
    print("FILE DELETE       : NONE")
    print("DB WRITE          : NONE")
    print("RUNTIME EXECUTION : NONE")
    print("CP RE-AUDIT        : NONE")
    print()

    # --------------------------------------------------------
    # Filesystem inventory
    # --------------------------------------------------------

    all_paths = sorted(
        PROJECT_DIR.rglob("*"),
        key=lambda p: str(p).lower()
    )

    files = [p for p in all_paths if p.is_file()]
    dirs = [p for p in all_paths if p.is_dir()]
    py_files = [p for p in files if p.suffix.lower() == ".py"]

    print("=" * 100)
    print("1 — PROJECT ARTIFACT INVENTORY")
    print("=" * 100)

    print(f"PROJECT FILE COUNT : {len(files)}")
    print(f"PROJECT DIR COUNT  : {len(dirs)}")
    print(f"PYTHON FILE COUNT  : {len(py_files)}")
    print()

    # --------------------------------------------------------
    # Production dependency closure
    # --------------------------------------------------------

    production_deps = production_dependency_closure(py_files)

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    categories = defaultdict(list)
    reasons = {}

    for p in files:
        category, reason = classify(p, files)

        # Strong protection if dependency closure says production.
        if p.name in production_deps:
            category = "A) CURRENT PRODUCTION"
            reason = "LOCAL IMPORT DEPENDENCY OF PRODUCTION ENTRYPOINT"

        categories[category].append(p)
        reasons[rel(p)] = reason

    # --------------------------------------------------------
    # Directory classification separately
    # --------------------------------------------------------

    dir_categories = defaultdict(list)

    for p in dirs:
        category, reason = classify(p, dirs)
        dir_categories[category].append(p)
        reasons[rel(p)] = reason

    # --------------------------------------------------------
    # Print categories
    # --------------------------------------------------------

    ordered_categories = [
        "A) CURRENT PRODUCTION",
        "B) VERIFIED PRODUCTION SUPPORT",
        "C) FORENSIC / DIAGNOSTIC",
        "D) BACKUP / CHECKPOINT ARTIFACT",
        "E) LEGACY / MUSEUM",
        "F) TEMP / CACHE / LOG",
        "G) UNKNOWN / NEEDS REVIEW",
    ]

    for category in ordered_categories:

        entries = categories.get(category, [])

        print("-" * 100)
        print(category)
        print("-" * 100)

        print(f"FILE COUNT : {len(entries)}")

        for p in entries:
            print(f"  {rel(p)}")
            print(f"      STATUS : RETAIN")
            print(f"      REASON : {reasons.get(rel(p), '')}")

        d_entries = dir_categories.get(category, [])

        if d_entries:
            print(f"DIRECTORIES : {len(d_entries)}")

            for p in d_entries:
                print(f"  [DIR] {rel(p)}")
                print(f"      STATUS : RETAIN")
                print(f"      REASON : {reasons.get(rel(p), '')}")

        print()

    # --------------------------------------------------------
    # Explicit production dependency list
    # --------------------------------------------------------

    print("=" * 100)
    print("2 — PRODUCTION IMPORT / DEPENDENCY CLOSURE")
    print("=" * 100)

    if production_deps:
        print(f"DEPENDENCY COUNT : {len(production_deps)}")

        for name in sorted(production_deps):
            print(f"  {name}")

    else:
        print("DEPENDENCY CLOSURE : NOT RESOLVED")

    print()

    # --------------------------------------------------------
    # Pipeline references
    # --------------------------------------------------------

    pipeline = PROJECT_DIR / "arunda_pipeline.py"

    print("=" * 100)
    print("3 — PRODUCTION ENTRYPOINT REFERENCES")
    print("=" * 100)

    if pipeline.exists():

        pipeline_text = read_text(pipeline)

        for p in sorted(py_files, key=lambda x: x.name.lower()):

            if p.name == "arunda_pipeline.py":
                continue

            if references_file(
                pipeline,
                p.name
            ):
                print(f"REFERENCED : {p.name}")

    else:
        print("BLOCKER : arunda_pipeline.py NOT FOUND")

    print()

    # --------------------------------------------------------
    # Execution state
    # --------------------------------------------------------

    print("=" * 100)
    print("4 — EXECUTION SAFETY")
    print("=" * 100)

    exec_state, exec_reason = execution_enabled_state()

    print(f"EXECUTION_ENABLED : {exec_state}")
    print(f"DETAIL            : {exec_reason}")

    if exec_state == "FALSE":
        print("EXECUTION SAFETY : PASS")
    else:
        print("EXECUTION SAFETY : REVIEW_REQUIRED")

    print()

    # --------------------------------------------------------
    # Database state
    # --------------------------------------------------------

    db_path = PROJECT_DIR / DB_NAME

    print("=" * 100)
    print("5 — DATABASE SAFETY")
    print("=" * 100)

    if db_path.exists():

        stat = db_path.stat()

        print("DATABASE          : PRESENT")
        print("DB WRITE          : NONE")
        print("DB DELETE         : NONE")
        print("DB RESET          : NONE")
        print("DB MIGRATION      : NONE")
        print(f"DB SIZE BYTES     : {stat.st_size}")
        print(
            f"DB SHA256         : "
            f"{sha256_file(db_path)}"
        )
        print("DATABASE STATUS   : PROTECTED")

    else:

        print("DATABASE : NOT FOUND")
        print("STATUS   : REVIEW_REQUIRED")

    print()

    # --------------------------------------------------------
    # Safe removal determination
    # --------------------------------------------------------

    print("=" * 100)
    print("6 — SAFE CLEANUP CANDIDATES")
    print("=" * 100)

    safe_to_remove = []
    review_required = []

    for category, entries in categories.items():

        for p in entries:

            # HARD RULE:
            # This inventory phase never authorizes deletion.
            # Even temp/legacy files are only candidates.

            if category == "E) LEGACY / MUSEUM":
                review_required.append(
                    (p, "LEGACY — REQUIRE EXPLICIT DELETE REVIEW")
                )

            elif category == "F) TEMP / CACHE / LOG":
                review_required.append(
                    (p, "TEMP/LOG — REQUIRE EXPLICIT DELETE REVIEW")
                )

            elif category == "D) BACKUP / CHECKPOINT ARTIFACT":
                review_required.append(
                    (p, "BACKUP/CHECKPOINT — NEVER BLIND DELETE")
                )

            else:
                review_required.append(
                    (p, "NOT CERTAIN ENOUGH FOR DELETION")
                )

    print("SAFE_TO_REMOVE = NONE")
    print(
        "Reason: inventory-only phase; no artifact is authorized "
        "for deletion before explicit review."
    )

    print()

    print("=" * 100)
    print("7 — REVIEW REQUIRED")
    print("=" * 100)

    if review_required:

        print(f"COUNT : {len(review_required)}")

        for p, reason in sorted(
            review_required,
            key=lambda x: str(x[0]).lower()
        ):
            print(f"  {rel(p)}")
            print(f"      {reason}")

    else:
        print("NONE")

    print()

    # --------------------------------------------------------
    # Production protection
    # --------------------------------------------------------

    print("=" * 100)
    print("8 — PRODUCTION PATH PROTECTION")
    print("=" * 100)

    required = [
        "arunda_pipeline.py",
        "feature_contract.py",
        "feature_snapshot_reader.py",
        "score_producer.py",
        "signal_engine.py",
        "signal_validator.py",
        "signal_scorer.py",
        "decision_engine.py",
        "risk_engine.py",
        "trade_gate_engine.py",
        "market_snapshot_engine.py",
        "market_data_engine.py",
        "opportunity_engine.py",
    ]

    protection_failures = []

    for name in required:

        path = PROJECT_DIR / name

        if not path.exists():
            protection_failures.append(name)
            print(f"MISSING : {name}")
        else:
            print(f"PRESENT : {name}")

    opportunity = PROJECT_DIR / "opportunity_engine.py"

    print()

    if opportunity.exists():

        text = read_text(opportunity)

        match = re.search(
            r"\bMAX_CANDIDATES\s*=\s*(\d+)",
            text
        )

        if match:

            value = match.group(1)

            print(f"MAX_CANDIDATES : {value}")

            if value == "15":
                print("MAX_CANDIDATES STATUS : VERIFIED / PRESERVE")
            else:
                print(
                    "MAX_CANDIDATES STATUS : "
                    "REVIEW_REQUIRED — DO NOT CHANGE"
                )

        else:
            print("MAX_CANDIDATES : NOT FOUND")

    print()

    # --------------------------------------------------------
    # Final inventory report
    # --------------------------------------------------------

    report = {
        "version": "CLEANUP_INVENTORY_v0.1",
        "mode": "READ_ONLY",
        "project_dir": str(PROJECT_DIR),
        "database": str(db_path),
        "file_count_before": len(files),
        "directory_count": len(dirs),
        "python_file_count": len(py_files),
        "production_dependency_closure": sorted(production_deps),
        "execution_enabled": exec_state,
        "safe_to_remove": [],
        "review_required": [
            rel(p)
            for p, _ in review_required
        ],
        "production_protection_failures": protection_failures,
        "db_write": "NONE",
        "db_delete": "NONE",
        "db_reset": "NONE",
        "db_migration": "NONE",
        "runtime_execution": "NONE",
        "cp_reaudit": "NONE",
        "max_candidates_expected": 15,
        "delete_performed": False,
    }

    report_path = (
        PROJECT_DIR /
        "cleanup_controlled_inventory_v0.1.json"
    )

    try:
        report_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8",
        )

        print("=" * 100)
        print("9 — INVENTORY REPORT")
        print("=" * 100)
        print(f"REPORT : {report_path}")

    except Exception as exc:
        print(
            f"REPORT WRITE FAILED : {type(exc).__name__}: {exc}"
        )

    print()

    # --------------------------------------------------------
    # HARD STOP
    # --------------------------------------------------------

    print("=" * 100)
    print("CLEANUP CONTROLLED INVENTORY FINAL")
    print("=" * 100)

    print(f"PROJECT FILE COUNT BEFORE : {len(files)}")
    print("PROJECT FILE COUNT AFTER  : NOT CHANGED")
    print("FILES REMOVED             : NONE")
    print("DB WRITE                  : NONE")
    print("PRODUCTION LOGIC CHANGES  : NONE")
    print("EXECUTION                 : DISABLED")
    print("RUNTIME EXECUTION         : NONE")
    print("CP RE-AUDIT               : NONE")
    print()

    if protection_failures:
        print("CLEANUP INVENTORY = BLOCKED")
        print(
            "BLOCKER : required production artifact(s) missing."
        )
    elif exec_state != "FALSE":
        print("CLEANUP INVENTORY = BLOCKED")
        print(
            "BLOCKER : EXECUTION_ENABLED is not verified False."
        )
    else:
        print("CLEANUP INVENTORY = PASS")
        print(
            "STATUS = INVENTORY COMPLETE / NO DELETE PERFORMED"
        )

    print()
    print("HARD STOP")
    print("NO FILE DELETE")
    print("NO DB CHANGE")
    print("NO RUNTIME")
    print("NO CP RE-AUDIT")
    print("NO EXECUTION")


if __name__ == "__main__":
    main()