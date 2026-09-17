import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

VERSION = "v0.1"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = [
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_FORENSIC_v0.2.py",
    "history_feature_extractor_corrupted_backup.py",
    "INDICATOR_POST_REPAIR_PRODUCTION_PRICE_INPUT_SOURCE_FORENSIC_AUDIT_v0.1.py",
    "prediction_test.py",
]

ARTIFACT_NAME = (
    "ARUNDA_PROJECT_NONPRODUCTION_SYNTAX_FAILURE_QUARANTINE_GATE_v0.1.json"
)

REPORT_NAME = (
    "ARUNDA_PROJECT_NONPRODUCTION_SYNTAX_FAILURE_QUARANTINE_GATE_v0.1.txt"
)

PRODUCTION_ENTRY_CANDIDATES = [
    "main.py",
    "arunda_trader.py",
    "ARUNDA_TRADER.py",
    "ARUNDA_MAIN.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def syntax_check(source: str) -> dict:
    try:
        ast.parse(source)
        return {
            "syntax_status": "PASS",
            "error_type": None,
            "error_message": None,
            "error_line": None,
            "error_column": None,
        }

    except SyntaxError as exc:
        return {
            "syntax_status": "FAIL",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "error_line": exc.lineno,
            "error_column": exc.offset,
        }


def filename_classification(name: str) -> str:
    lower = name.lower()

    if "corrupted" in lower or "backup" in lower:
        return "BACKUP_ARTIFACT"

    if "prediction_test" in lower or lower.endswith("_test.py"):
        return "TEST_ARTIFACT"

    if "forensic" in lower or "audit" in lower:
        return "FORENSIC_ARTIFACT"

    return "UNKNOWN"


def content_markers(source: str) -> list[str]:
    markers = []
    lower = source.lower()

    if "sqlite3" in lower:
        markers.append("SQLITE_USAGE")

    if "sqlite.connect" in lower or "sqlite3.connect" in lower:
        markers.append("SQLITE_CONNECT")

    if "powershell" in lower:
        markers.append("POWERSHELL_TEXT")

    if "set-location" in lower:
        markers.append("POWERSHELL_SET_LOCATION")

    if "get-childitem" in lower:
        markers.append("POWERSHELL_GET_CHILD_ITEM")

    if "@'" in source or '@"' in source:
        markers.append("POWERSHELL_HERE_STRING")

    if "create table" in lower:
        markers.append("SQL_CREATE_TABLE_TEXT")

    if "alter table" in lower:
        markers.append("SQL_ALTER_TABLE_TEXT")

    if "drop table" in lower:
        markers.append("SQL_DROP_TABLE_TEXT")

    if "t + 10 sec" in lower:
        markers.append("PLAIN_TEXT_TEST_EXPRESSION")

    if "live" in lower:
        markers.append("LIVE_TERM")

    if "paper" in lower:
        markers.append("PAPER_TERM")

    if "production" in lower:
        markers.append("PRODUCTION_TERM")

    if "order" in lower:
        markers.append("ORDER_TERM")

    if "trade" in lower:
        markers.append("TRADE_TERM")

    return markers


def discover_python_files() -> list[Path]:
    return sorted(
        p
        for p in PROJECT_DIR.glob("*.py")
        if p.is_file()
    )


def direct_references(
    target_name: str,
    python_files: list[Path],
) -> list[str]:

    references = []

    for path in python_files:
        if path.name == target_name:
            continue

        try:
            source = read_text(path)
        except Exception:
            continue

        if target_name in source:
            references.append(path.name)

    return references


def production_entry_references(
    target_name: str,
    python_files: list[Path],
) -> list[str]:

    references = []

    for path in python_files:
        if path.name == target_name:
            continue

        lower_name = path.name.lower()

        if (
            lower_name not in {
                item.lower()
                for item in PRODUCTION_ENTRY_CANDIDATES
            }
        ):
            continue

        try:
            source = read_text(path)
        except Exception:
            continue

        if target_name in source:
            references.append(path.name)

    return references


def classify_launch_relevance(
    filename_class: str,
    references: list[str],
    production_refs: list[str],
    markers: list[str],
) -> tuple[str, list[str]]:

    reasons = []

    if production_refs:
        reasons.append("direct_reference_from_production_entry_candidate")

    if references:
        reasons.append("direct_project_reference_found")
    else:
        reasons.append("no_direct_project_reference_found")

    if filename_class == "BACKUP_ARTIFACT":
        reasons.append("filename_identifies_backup_artifact")

        if not production_refs:
            return (
                "NON_PRODUCTION_QUARANTINE_CANDIDATE",
                reasons,
            )

    if filename_class == "TEST_ARTIFACT":
        reasons.append("filename_identifies_test_artifact")

        if not production_refs:
            return (
                "NON_PRODUCTION_QUARANTINE_CANDIDATE",
                reasons,
            )

    if filename_class == "FORENSIC_ARTIFACT":
        reasons.append("filename_identifies_forensic_artifact")

        if not production_refs:
            return (
                "NON_PRODUCTION_QUARANTINE_CANDIDATE",
                reasons,
            )

    if production_refs:
        return (
            "PRODUCTION_DEPENDENCY_REQUIRES_REVIEW",
            reasons,
        )

    if (
        "LIVE_TERM" in markers
        or "PAPER_TERM" in markers
        or "PRODUCTION_TERM" in markers
        or "ORDER_TERM" in markers
        or "TRADE_TERM" in markers
        or "SQLITE_USAGE" in markers
    ):
        reasons.append("runtime_or_database_markers_present")

        if references:
            return (
                "MANUAL_REVIEW_CANDIDATE",
                reasons,
            )

    return (
        "NON_PRODUCTION_QUARANTINE_CANDIDATE",
        reasons,
    )


def build_record(
    path: Path,
    python_files: list[Path],
) -> dict:

    source = read_text(path)

    syntax = syntax_check(source)

    filename_class = filename_classification(path.name)

    markers = content_markers(source)

    references = direct_references(
        path.name,
        python_files,
    )

    production_refs = production_entry_references(
        path.name,
        python_files,
    )

    relevance, reasons = classify_launch_relevance(
        filename_class,
        references,
        production_refs,
        markers,
    )

    return {
        "file": path.name,
        "exists": path.exists(),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "filename_class": filename_class,
        "launch_relevance": relevance,
        "syntax": syntax,
        "content_markers": markers,
        "referenced_by": references,
        "production_entry_references": production_refs,
        "reasons": reasons,
        "deletion_performed": False,
        "quarantine_performed": False,
    }


def print_record(record: dict) -> None:
    print("-" * 100)
    print(f"FILE                 : {record['file']}")
    print(f"EXISTS               : {record['exists']}")
    print(f"FILENAME CLASS       : {record['filename_class']}")
    print(f"LAUNCH RELEVANCE     : {record['launch_relevance']}")
    print(
        f"SYNTAX STATUS        : "
        f"{record['syntax']['syntax_status']}"
    )
    print(
        f"ERROR TYPE           : "
        f"{record['syntax']['error_type']}"
    )
    print(
        f"ERROR LINE           : "
        f"{record['syntax']['error_line']}"
    )
    print(
        f"CONTENT MARKERS      : "
        f"{', '.join(record['content_markers']) or 'None'}"
    )
    print(
        f"REFERENCED BY        : "
        f"{', '.join(record['referenced_by']) or 'None'}"
    )
    print(
        f"PRODUCTION REFERENCES: "
        f"{', '.join(record['production_entry_references']) or 'None'}"
    )
    print("REASONS:")

    for reason in record["reasons"]:
        print(f"  - {reason}")

    print(
        f"DELETION PERFORMED   : "
        f"{record['deletion_performed']}"
    )
    print(
        f"QUARANTINE PERFORMED : "
        f"{record['quarantine_performed']}"
    )


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()

    print("=" * 100)
    print(
        "ARUNDA PROJECT NONPRODUCTION SYNTAX FAILURE "
        "QUARANTINE GATE " + VERSION
    )
    print("=" * 100)
    print(f"Project Directory : {PROJECT_DIR}")
    print(f"Started UTC       : {started}")
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : FORBIDDEN")
    print("File Modification : FORBIDDEN")
    print("Deletion          : FORBIDDEN")
    print("Quarantine        : FORBIDDEN")
    print("-" * 100)

    python_files = discover_python_files()

    records = []

    print()
    print("=" * 100)
    print("TARGET CLASSIFICATION")
    print("=" * 100)

    for filename in TARGET_FILES:
        path = PROJECT_DIR / filename

        if not path.exists():
            record = {
                "file": filename,
                "exists": False,
                "size": None,
                "sha256": None,
                "filename_class": "MISSING",
                "launch_relevance": "MISSING_TARGET",
                "syntax": {
                    "syntax_status": "NOT_CHECKED",
                    "error_type": None,
                    "error_message": None,
                    "error_line": None,
                    "error_column": None,
                },
                "content_markers": [],
                "referenced_by": [],
                "production_entry_references": [],
                "reasons": [
                    "target_file_not_found"
                ],
                "deletion_performed": False,
                "quarantine_performed": False,
            }

        else:
            record = build_record(
                path,
                python_files,
            )

        records.append(record)
        print_record(record)

    quarantine_candidates = [
        r
        for r in records
        if r["launch_relevance"]
        == "NON_PRODUCTION_QUARANTINE_CANDIDATE"
    ]

    manual_review = [
        r
        for r in records
        if r["launch_relevance"]
        in {
            "MANUAL_REVIEW_CANDIDATE",
            "PRODUCTION_DEPENDENCY_REQUIRES_REVIEW",
        }
    ]

    production_dependencies = [
        r
        for r in records
        if r["launch_relevance"]
        == "PRODUCTION_DEPENDENCY_REQUIRES_REVIEW"
    ]

    print()
    print("=" * 100)
    print("CROSS-TARGET SUMMARY")
    print("=" * 100)

    print(f"Target Files                          : {len(records)}")
    print(
        "Non-Production Quarantine Candidates : "
        f"{len(quarantine_candidates)}"
    )
    print(
        f"Manual / Dependency Review Candidates: "
        f"{len(manual_review)}"
    )
    print(
        f"Production Dependency Candidates     : "
        f"{len(production_dependencies)}"
    )

    print()
    print("=" * 100)
    print("GATE DECISION")
    print("=" * 100)

    if production_dependencies:
        status = "QUARANTINE_GATE_BLOCKED_PRODUCTION_DEPENDENCY"
        print(
            "FORENSIC STATUS : "
            "QUARANTINE_GATE_BLOCKED_PRODUCTION_DEPENDENCY"
        )
        print(
            "Production references detected. "
            "No quarantine authorization."
        )

    elif manual_review:
        status = "QUARANTINE_GATE_REVIEW_REQUIRED"
        print(
            "FORENSIC STATUS : "
            "QUARANTINE_GATE_REVIEW_REQUIRED"
        )
        print(
            "Manual/runtime dependency review remains."
        )

    else:
        status = "NONPRODUCTION_FAILURES_SAFE_TO_QUARANTINE"
        print(
            "FORENSIC STATUS : "
            "NONPRODUCTION_FAILURES_SAFE_TO_QUARANTINE"
        )
        print(
            "All targeted syntax failures are classified "
            "as non-production candidates."
        )

    print()
    print("IMPORTANT:")
    print("  No file was deleted.")
    print("  No file was modified.")
    print("  No file was quarantined.")
    print("  No database was opened.")
    print("  No network was used.")
    print("  No production engine was executed.")

    finished = datetime.now(timezone.utc).isoformat()

    report = {
        "version": VERSION,
        "project_directory": str(PROJECT_DIR),
        "started_utc": started,
        "finished_utc": finished,
        "mode": "READ_ONLY",
        "database_used": False,
        "network_used": False,
        "file_modification": False,
        "deletion_performed": False,
        "quarantine_performed": False,
        "target_files": TARGET_FILES,
        "records": records,
        "summary": {
            "target_files": len(records),
            "non_production_quarantine_candidates": len(
                quarantine_candidates
            ),
            "manual_review_candidates": len(
                manual_review
            ),
            "production_dependency_candidates": len(
                production_dependencies
            ),
        },
        "status": status,
    }

    artifact_path = PROJECT_DIR / ARTIFACT_NAME
    report_path = PROJECT_DIR / REPORT_NAME

    with artifact_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "ARUNDA PROJECT NONPRODUCTION SYNTAX FAILURE "
            "QUARANTINE GATE v0.1\n"
        )
        f.write("=" * 100 + "\n")
        f.write(
            f"Project Directory : {PROJECT_DIR}\n"
        )
        f.write(
            f"Started UTC       : {started}\n"
        )
        f.write(
            f"Finished UTC      : {finished}\n"
        )
        f.write("Mode              : READ ONLY\n")
        f.write("Database          : NOT USED\n")
        f.write("Network           : FORBIDDEN\n")
        f.write("File Modification : FORBIDDEN\n")
        f.write("Deletion          : FORBIDDEN\n")
        f.write("Quarantine        : FORBIDDEN\n")
        f.write("=" * 100 + "\n\n")

        for record in records:
            f.write("-" * 100 + "\n")
            f.write(
                f"FILE : {record['file']}\n"
            )
            f.write(
                f"CLASS : {record['filename_class']}\n"
            )
            f.write(
                f"LAUNCH RELEVANCE : "
                f"{record['launch_relevance']}\n"
            )
            f.write(
                f"SYNTAX : "
                f"{record['syntax']['syntax_status']}\n"
            )
            f.write(
                f"ERROR : "
                f"{record['syntax']['error_message']}\n"
            )
            f.write(
                f"REFERENCED BY : "
                f"{', '.join(record['referenced_by']) or 'None'}\n"
            )
            f.write(
                f"PRODUCTION REFERENCES : "
                f"{', '.join(record['production_entry_references']) or 'None'}\n"
            )

        f.write("\n")
        f.write("=" * 100 + "\n")
        f.write("FORENSIC STATUS\n")
        f.write("=" * 100 + "\n")
        f.write(
            f"FORENSIC STATUS : {status}\n"
        )
        f.write("DATABASE WRITE   : NOT PERFORMED\n")
        f.write("FILE DELETION    : NOT PERFORMED\n")
        f.write("QUARANTINE       : NOT PERFORMED\n")

    artifact_sha = sha256_file(artifact_path)

    print()
    print("=" * 100)
    print("ARTIFACT")
    print("=" * 100)
    print(f"Artifact : {artifact_path}")
    print(f"Report   : {report_path}")
    print(f"SHA256   : {artifact_sha}")
    print("=" * 100)


if __name__ == "__main__":
    main()