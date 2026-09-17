import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

SCRIPT_NAME = "ARUNDA_PROJECT_SYNTAX_FAILURE_CLASSIFICATION_FORENSIC_v0.1.py"
ARTIFACT_NAME = "ARUNDA_PROJECT_SYNTAX_FAILURE_CLASSIFICATION_FORENSIC_v0.1.json"
REPORT_NAME = "ARUNDA_PROJECT_SYNTAX_FAILURE_CLASSIFICATION_FORENSIC_v0.1.txt"

ARTIFACT_PATH = PROJECT_DIR / ARTIFACT_NAME
REPORT_PATH = PROJECT_DIR / REPORT_NAME

TARGET_FILES = [
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_FORENSIC_v0.2.py",
    "ARUNDA_TRADER_LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_FROM_ISOLATED_LAUNCH_v0.1.py",
    "history_feature_extractor_corrupted_backup.py",
    "INDICATOR_POST_REPAIR_PRODUCTION_PRICE_INPUT_SOURCE_FORENSIC_AUDIT_v0.1.py",
    "prediction_test.py",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def read_source(path):
    try:
        text = path.read_text(
            encoding="utf-8-sig"
        )
        return text, None

    except UnicodeDecodeError:
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace"
            )
            return text, None

        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"

    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def syntax_error(path):
    source, read_error = read_source(path)

    if source is None:
        return {
            "syntax_status": "UNREADABLE",
            "error_type": "READ_ERROR",
            "message": read_error,
            "line": None,
            "column": None,
            "source": None,
        }

    try:
        ast.parse(
            source,
            filename=str(path)
        )

        return {
            "syntax_status": "PASS",
            "error_type": None,
            "message": None,
            "line": None,
            "column": None,
            "source": None,
        }

    except SyntaxError as exc:
        return {
            "syntax_status": "FAIL",
            "error_type": "SyntaxError",
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.offset,
            "source": (
                exc.text.strip()
                if exc.text
                else None
            ),
        }

    except Exception as exc:
        return {
            "syntax_status": "FAIL",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "line": None,
            "column": None,
            "source": None,
        }


def classify_filename(name):
    lower = name.lower()

    if "corrupted_backup" in lower:
        return "BACKUP_ARTIFACT"

    if "backup" in lower:
        return "BACKUP_ARTIFACT"

    if "prediction_test" in lower:
        return "TEST_ARTIFACT"

    if lower.startswith("test_"):
        return "TEST_ARTIFACT"

    if "_test" in lower:
        return "TEST_ARTIFACT"

    if "forensic" in lower:
        return "FORENSIC_ARTIFACT"

    if "isolated_launch" in lower:
        return "RUNTIME_LIFECYCLE_ARTIFACT"

    if "live_paper" in lower:
        return "RUNTIME_LIFECYCLE_ARTIFACT"

    return "UNKNOWN_ARTIFACT"


def detect_content_markers(source):
    if source is None:
        return []

    markers = []

    if re.search(
        r"(^|\n)\s*cd\s+[a-z]:\\",
        source,
        re.IGNORECASE
    ):
        markers.append(
            "POWERSHELL_CD_COMMAND"
        )

    if "@'" in source or "'@" in source:
        markers.append(
            "POWERSHELL_HERE_STRING"
        )

    if re.search(
        r"^\s*t\s*\+\s*\d+\s*(sec|seconds?)\s*$",
        source,
        re.IGNORECASE | re.MULTILINE
    ):
        markers.append(
            "PLAIN_TEXT_TEST_EXPRESSION"
        )

    lower = source.lower()

    if "sqlite3" in lower:
        markers.append("SQLITE_USAGE")

    if "subprocess" in lower:
        markers.append("SUBPROCESS_USAGE")

    if (
        "requests" in lower
        or "urllib" in lower
        or "httpx" in lower
    ):
        markers.append(
            "NETWORK_LIBRARY_REFERENCE"
        )

    if "socket" in lower:
        markers.append(
            "SOCKET_REFERENCE"
        )

    if "insert into" in lower:
        markers.append(
            "SQL_INSERT_TEXT"
        )

    if re.search(
        r"\bupdate\s+\w+\s+set\b",
        lower
    ):
        markers.append(
            "SQL_UPDATE_TEXT"
        )

    if re.search(
        r"\bdelete\s+from\b",
        lower
    ):
        markers.append(
            "SQL_DELETE_TEXT"
        )

    if "create table" in lower:
        markers.append(
            "SQL_CREATE_TABLE_TEXT"
        )

    if "alter table" in lower:
        markers.append(
            "SQL_ALTER_TABLE_TEXT"
        )

    if "prediction" in lower:
        markers.append(
            "PREDICTION_REFERENCE"
        )

    return sorted(set(markers))


def extract_imports(source):
    if source is None:
        return []

    try:
        tree = ast.parse(source)
    except Exception:
        return []

    imports = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return sorted(set(imports))


def find_references(
    target_name,
    all_python_files
):
    module_name = Path(
        target_name
    ).stem

    patterns = [
        re.compile(
            rf"\bimport\s+{re.escape(module_name)}\b",
            re.IGNORECASE
        ),
        re.compile(
            rf"\bfrom\s+{re.escape(module_name)}\b",
            re.IGNORECASE
        ),
        re.compile(
            rf"\b{re.escape(target_name)}\b",
            re.IGNORECASE
        ),
    ]

    references = []

    for path in all_python_files:

        if path.name == target_name:
            continue

        if path.name == SCRIPT_NAME:
            continue

        try:
            source = path.read_text(
                encoding="utf-8-sig",
                errors="ignore"
            )
        except Exception:
            continue

        for pattern in patterns:
            if pattern.search(source):
                references.append(
                    str(
                        path.relative_to(
                            PROJECT_DIR
                        )
                    )
                )
                break

    return sorted(set(references))


def determine_launch_relevance(
    filename_class,
    references,
    markers
):
    reasons = []

    if filename_class == "BACKUP_ARTIFACT":
        reasons.append(
            "filename_identifies_backup_artifact"
        )

        return (
            "NON_PRODUCTION_QUARANTINE_CANDIDATE",
            reasons
        )

    if filename_class == "TEST_ARTIFACT":
        reasons.append(
            "filename_identifies_test_artifact"
        )

        return (
            "NON_PRODUCTION_QUARANTINE_CANDIDATE",
            reasons
        )

    if filename_class == "FORENSIC_ARTIFACT":
        reasons.append(
            "filename_identifies_forensic_artifact"
        )

        if references:
            reasons.append(
                "referenced_by_other_python_files"
            )

            return (
                "FORENSIC_WITH_DEPENDENCY",
                reasons
            )

        if any(
            marker in markers
            for marker in [
                "POWERSHELL_CD_COMMAND",
                "POWERSHELL_HERE_STRING",
                "PLAIN_TEXT_TEST_EXPRESSION",
            ]
        ):
            reasons.append(
                "contains_non_python_shell_or_test_content"
            )

            return (
                "NON_PRODUCTION_QUARANTINE_CANDIDATE",
                reasons
            )

        reasons.append(
            "no_direct_python_reference_found"
        )

        return (
            "FORENSIC_ONLY_REPAIR_OR_QUARANTINE_CANDIDATE",
            reasons
        )

    if (
        filename_class
        == "RUNTIME_LIFECYCLE_ARTIFACT"
    ):
        reasons.append(
            "filename_contains_runtime_lifecycle_terms"
        )

        if references:
            reasons.append(
                "referenced_by_other_python_files"
            )

            return (
                "POTENTIAL_RUNTIME_DEPENDENCY",
                reasons
            )

        reasons.append(
            "no_direct_python_reference_found"
        )

        return (
            "RUNTIME_ARTIFACT_REVIEW_REQUIRED",
            reasons
        )

    if references:
        reasons.append(
            "referenced_by_other_python_files"
        )

        return (
            "POTENTIAL_RUNTIME_DEPENDENCY",
            reasons
        )

    reasons.append(
        "no_direct_python_reference_found"
    )

    return (
        "MANUAL_REVIEW_REQUIRED",
        reasons
    )


def build_record(
    path,
    all_python_files
):
    relative = str(
        path.relative_to(
            PROJECT_DIR
        )
    )

    if not path.exists():
        return {
            "file": relative,
            "exists": False,
            "filename_class": "FILE_NOT_FOUND",
            "launch_relevance": "UNKNOWN",
            "syntax": {},
            "content_markers": [],
            "imports": [],
            "referenced_by": [],
            "sha256": None,
            "reason": [
                "target_file_not_found"
            ],
        }

    source, read_error = read_source(path)

    syntax = syntax_error(path)

    markers = detect_content_markers(
        source
    )

    imports = extract_imports(
        source
    )

    references = find_references(
        path.name,
        all_python_files
    )

    filename_class = classify_filename(
        path.name
    )

    launch_relevance, reasons = (
        determine_launch_relevance(
            filename_class,
            references,
            markers
        )
    )

    if read_error:
        reasons.append(
            "source_read_error"
        )

    return {
        "file": relative,
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "filename_class": filename_class,
        "launch_relevance": launch_relevance,
        "syntax": syntax,
        "content_markers": markers,
        "imports": imports,
        "referenced_by": references,
        "reason": reasons,
    }


def main():

    started_at = utc_now()

    print("=" * 90)
    print(
        "ARUNDA PROJECT SYNTAX FAILURE "
        "CLASSIFICATION FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Project Directory : {PROJECT_DIR}"
    )
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : FORBIDDEN")
    print("Production Run    : NOT PERFORMED")
    print("File Modification : FORBIDDEN")
    print("Deletion          : FORBIDDEN")
    print("Quarantine        : FORBIDDEN")

    print("-" * 90)

    if not PROJECT_DIR.exists():
        print(
            "ERROR: Project directory does not exist."
        )
        raise SystemExit(2)

    all_python_files = sorted(
        [
            p
            for p in PROJECT_DIR.rglob("*.py")
            if p.is_file()
            and "__pycache__" not in p.parts
            and ".git" not in p.parts
            and p.name != SCRIPT_NAME
        ],
        key=lambda p: str(p).lower()
    )

    records = []

    print("")
    print("=" * 90)
    print("TARGET CLASSIFICATION")
    print("=" * 90)

    for target in TARGET_FILES:

        path = PROJECT_DIR / target

        print("")
        print("-" * 90)
        print(f"FILE : {target}")

        record = build_record(
            path,
            all_python_files
        )

        records.append(record)

        print(
            f"EXISTS           : "
            f"{record.get('exists')}"
        )

        print(
            f"FILENAME CLASS   : "
            f"{record.get('filename_class')}"
        )

        print(
            f"LAUNCH RELEVANCE : "
            f"{record.get('launch_relevance')}"
        )

        syntax = record.get(
            "syntax",
            {}
        )

        print(
            f"SYNTAX STATUS    : "
            f"{syntax.get('syntax_status', 'N/A')}"
        )

        if syntax.get("message"):
            print(
                f"ERROR            : "
                f"{syntax.get('message')}"
            )

        if syntax.get("line") is not None:
            print(
                f"LINE             : "
                f"{syntax.get('line')}"
            )

        markers = record.get(
            "content_markers",
            []
        )

        print(
            "CONTENT MARKERS  : "
            + (
                ", ".join(markers)
                if markers
                else "None"
            )
        )

        references = record.get(
            "referenced_by",
            []
        )

        print(
            "REFERENCED BY    : "
            + (
                ", ".join(references)
                if references
                else "None"
            )
        )

        print("REASONS:")

        for reason in record.get(
            "reason",
            []
        ):
            print(
                f"  - {reason}"
            )

    nonprod = [
        r for r in records
        if r.get("launch_relevance")
        == "NON_PRODUCTION_QUARANTINE_CANDIDATE"
    ]

    runtime = [
        r for r in records
        if r.get("launch_relevance")
        in {
            "POTENTIAL_RUNTIME_DEPENDENCY",
            "RUNTIME_ARTIFACT_REVIEW_REQUIRED",
        }
    ]

    forensic_dependency = [
        r for r in records
        if r.get("launch_relevance")
        == "FORENSIC_WITH_DEPENDENCY"
    ]

    manual = [
        r for r in records
        if r.get("launch_relevance")
        in {
            "MANUAL_REVIEW_REQUIRED",
            "FORENSIC_ONLY_REPAIR_OR_QUARANTINE_CANDIDATE",
        }
    ]

    finished_at = utc_now()

    artifact = {
        "artifact": ARTIFACT_NAME,
        "version": "v0.1",
        "project_directory": str(
            PROJECT_DIR
        ),
        "mode": "READ_ONLY",
        "database_used": False,
        "database_write": False,
        "network_used": False,
        "production_run": False,
        "file_modification": False,
        "deletion": False,
        "quarantine": False,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "targets": TARGET_FILES,
        "summary": {
            "targets": len(records),
            "non_production_quarantine_candidates": len(nonprod),
            "runtime_review_candidates": len(runtime),
            "forensic_dependency_candidates": len(
                forensic_dependency
            ),
            "manual_review_candidates": len(manual),
        },
        "records": records,
    }

    ARTIFACT_PATH.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    lines = []

    lines.append("=" * 90)
    lines.append(
        "ARUNDA PROJECT SYNTAX FAILURE "
        "CLASSIFICATION FORENSIC v0.1"
    )
    lines.append("=" * 90)

    lines.append(
        f"Project Directory : {PROJECT_DIR}"
    )
    lines.append(
        "Mode              : READ ONLY"
    )
    lines.append(
        "Database          : NOT USED"
    )
    lines.append(
        "Network           : FORBIDDEN"
    )
    lines.append(
        "Production Run    : NOT PERFORMED"
    )
    lines.append(
        "File Modification : FORBIDDEN"
    )
    lines.append(
        "Deletion          : FORBIDDEN"
    )
    lines.append(
        "Quarantine        : FORBIDDEN"
    )

    lines.append("")
    lines.append("=" * 90)
    lines.append("CROSS-TARGET SUMMARY")
    lines.append("=" * 90)

    lines.append(
        f"Target Files                          : {len(records)}"
    )
    lines.append(
        f"Non-Production Quarantine Candidates : {len(nonprod)}"
    )
    lines.append(
        f"Runtime Review Candidates             : {len(runtime)}"
    )
    lines.append(
        f"Forensic Dependency Candidates        : {len(forensic_dependency)}"
    )
    lines.append(
        f"Manual Review Candidates              : {len(manual)}"
    )

    lines.append("")
    lines.append("=" * 90)
    lines.append("CLASSIFICATION")
    lines.append("=" * 90)

    for record in records:

        lines.append("-" * 90)

        lines.append(
            f"FILE : {record.get('file')}"
        )

        lines.append(
            f"CLASS : "
            f"{record.get('launch_relevance')}"
        )

        syntax = record.get(
            "syntax",
            {}
        )

        lines.append(
            f"SYNTAX : "
            f"{syntax.get('syntax_status', 'N/A')}"
        )

        if syntax.get("message"):
            lines.append(
                f"ERROR : "
                f"{syntax.get('message')}"
            )

        if syntax.get("line") is not None:
            lines.append(
                f"LINE : "
                f"{syntax.get('line')}"
            )

        refs = record.get(
            "referenced_by",
            []
        )

        lines.append(
            "REFERENCED BY : "
            + (
                ", ".join(refs)
                if refs
                else "None"
            )
        )

        markers = record.get(
            "content_markers",
            []
        )

        lines.append(
            "MARKERS : "
            + (
                ", ".join(markers)
                if markers
                else "None"
            )
        )

        lines.append("REASONS:")

        for reason in record.get(
            "reason",
            []
        ):
            lines.append(
                f"  - {reason}"
            )

    lines.append("")
    lines.append("=" * 90)
    lines.append("FORENSIC STATUS")
    lines.append("=" * 90)

    if runtime:
        status = (
            "RUNTIME_REVIEW_REQUIRED"
        )

    elif forensic_dependency:
        status = (
            "FORENSIC_DEPENDENCY_REVIEW_REQUIRED"
        )

    elif manual:
        status = (
            "NON_PRODUCTION_FAILURES_CLASSIFIED_WITH_REVIEW_ITEMS"
        )

    else:
        status = (
            "SYNTAX_FAILURES_CLASSIFIED"
        )

    lines.append(
        f"FORENSIC STATUS : {status}"
    )

    lines.append(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    lines.append(
        "DATABASE WRITE   : NOT PERFORMED"
    )

    lines.append(
        "NETWORK          : NOT USED"
    )

    lines.append(
        "PRODUCTION RUN   : NOT PERFORMED"
    )

    lines.append(
        "DELETION         : NOT PERFORMED"
    )

    lines.append(
        "QUARANTINE       : NOT PERFORMED"
    )

    lines.append("")
    lines.append("=" * 90)
    lines.append("NEXT ACTION")
    lines.append("=" * 90)

    if runtime:
        lines.append(
            "Runtime/lifecycle candidates exist."
        )
        lines.append(
            "Do NOT quarantine them before runtime dependency review."
        )

    elif forensic_dependency:
        lines.append(
            "A forensic artifact has downstream Python references."
        )
        lines.append(
            "Review dependency before any quarantine."
        )

    elif nonprod:
        lines.append(
            "Non-production syntax failures are classified."
        )
        lines.append(
            "No deletion or quarantine was performed."
        )

    else:
        lines.append(
            "No automatic quarantine action established."
        )

    lines.append("")
    lines.append("=" * 90)
    lines.append("ARTIFACT")
    lines.append("=" * 90)

    lines.append(
        f"Artifact : {ARTIFACT_PATH}"
    )

    lines.append(
        f"Report   : {REPORT_PATH}"
    )

    lines.append("=" * 90)

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print("")
    print("\n".join(lines))

    print(
        f"SHA256   : "
        f"{sha256_file(ARTIFACT_PATH)}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()