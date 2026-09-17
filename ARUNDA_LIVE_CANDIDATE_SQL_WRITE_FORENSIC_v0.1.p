```python
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.1"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

QUARANTINE_DIR_NAME = "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"

OUTPUT_JSON = PROJECT_DIR / (
    "ARUNDA_LIVE_CANDIDATE_SQL_WRITE_FORENSIC_v0.1.json"
)

OUTPUT_TXT = PROJECT_DIR / (
    "ARUNDA_LIVE_CANDIDATE_SQL_WRITE_FORENSIC_v0.1.txt"
)


# ============================================================================
# POLICY
# ============================================================================

MODE = "READ ONLY"
DATABASE_WRITE = False
NETWORK_USED = False
PRODUCTION_RUN = False
LIVE_SOURCE_RUN = False


# ============================================================================
# TERMS
# ============================================================================

LIVE_TERMS = (
    "live",
    "production",
    "execution",
    "order",
    "trade",
    "bitpin",
    "exchange",
    "paper",
    "lifecycle",
)

PRODUCTION_DB_TERMS = (
    "arunda.db",
    "production_db",
    "production database",
    "PRODUCTION_DB",
)

ISOLATED_PAPER_TERMS = (
    "paper",
    "isolated",
    "capture",
    "sandbox",
    "simulation",
    "dry_run",
    "dry-run",
)

SQL_WRITE_TERMS = (
    "insert",
    "update",
    "delete",
    "replace",
    "create",
    "alter",
    "drop",
    "vacuum",
)

DB_CALL_TERMS = (
    "sqlite3.connect",
    "connect_db",
    "connection.execute",
    "conn.execute",
    "cursor.execute",
    "executemany",
    "executescript",
)


# ============================================================================
# BASIC HELPERS
# ============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def relative_path(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT_DIR)
    except ValueError:
        return path


def is_quarantined(path: Path) -> bool:
    relative = relative_path(path)
    return QUARANTINE_DIR_NAME in relative.parts


def is_output_file(path: Path) -> bool:
    return path.resolve() in {
        OUTPUT_JSON.resolve(),
        OUTPUT_TXT.resolve(),
    }


def read_source(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        ), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def detect_terms(
    source_lower: str,
    terms: tuple[str, ...],
) -> list[str]:
    found = []

    for term in terms:
        if term.lower() in source_lower:
            found.append(term)

    return found


# ============================================================================
# PYTHON FILE DISCOVERY
# ============================================================================

def discover_python_files() -> list[Path]:
    files = []

    for path in PROJECT_DIR.rglob("*.py"):
        if is_quarantined(path):
            continue

        if is_output_file(path):
            continue

        if path.is_file():
            files.append(path)

    return sorted(files)


# ============================================================================
# SYNTAX
# ============================================================================

def syntax_check(
    source: str,
    filename: str,
) -> tuple[bool, dict[str, Any] | None]:

    try:
        ast.parse(
            source,
            filename=filename,
        )
        return True, None

    except SyntaxError as exc:
        return False, {
            "error_type": type(exc).__name__,
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
        return False, {
            "error_type": type(exc).__name__,
            "message": str(exc),
            "line": None,
            "column": None,
            "source": None,
        }


# ============================================================================
# AST SQL WRITE DETECTION
# ============================================================================

def ast_call_name(node: ast.Call) -> str:
    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts = []

        current: ast.AST | None = func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value

    return None


def classify_sql_statement(
    sql: str,
) -> list[str]:

    normalized = re.sub(
        r"\s+",
        " ",
        sql.strip().lower(),
    )

    markers = []

    for term in SQL_WRITE_TERMS:
        pattern = rf"\b{re.escape(term)}\b"

        if re.search(pattern, normalized):
            markers.append(term.upper())

    return markers


def find_ast_write_candidates(
    source: str,
) -> list[dict[str, Any]]:

    try:
        tree = ast.parse(source)
    except Exception:
        return []

    findings = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        call_name = ast_call_name(node)

        # ------------------------------------------------------------------
        # execute(...)
        # ------------------------------------------------------------------

        if call_name.endswith("execute") or call_name.endswith(
            "executemany"
        ) or call_name.endswith("executescript"):

            sql_text = None

            if node.args:
                sql_text = literal_string(node.args[0])

            if sql_text:
                sql_markers = classify_sql_statement(
                    sql_text
                )
            else:
                sql_markers = []

            if sql_markers:
                findings.append({
                    "line": getattr(
                        node,
                        "lineno",
                        None,
                    ),
                    "target": (
                        "SQL_WRITE_CANDIDATE"
                    ),
                    "types": sql_markers,
                    "source": (
                        sql_text.strip()
                    ),
                    "call": call_name,
                })

        # ------------------------------------------------------------------
        # sqlite3.connect(...)
        # ------------------------------------------------------------------

        if call_name == "sqlite3.connect":
            findings.append({
                "line": getattr(
                    node,
                    "lineno",
                    None,
                ),
                "target": "DATABASE_CONNECTION",
                "types": ["CONNECT"],
                "source": "sqlite3.connect(...)",
                "call": call_name,
            })

        # ------------------------------------------------------------------
        # pathlib write operations
        # ------------------------------------------------------------------

        if call_name in {
            "Path.write_text",
            "Path.write_bytes",
        }:
            findings.append({
                "line": getattr(
                    node,
                    "lineno",
                    None,
                ),
                "target": "FILE_WRITE",
                "types": ["WRITE"],
                "source": call_name,
                "call": call_name,
            })

    return findings


# ============================================================================
# TEXT FALLBACK DETECTION
# ============================================================================

def find_text_write_candidates(
    source: str,
) -> list[dict[str, Any]]:

    findings = []

    lines = source.splitlines()

    sql_pattern = re.compile(
        r"\b("
        r"INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|VACUUM"
        r")\b",
        re.IGNORECASE,
    )

    db_call_pattern = re.compile(
        r"(sqlite3\.connect|"
        r"connect_db|"
        r"\.execute\(|"
        r"\.executemany\(|"
        r"\.executescript\()",
        re.IGNORECASE,
    )

    for index, line in enumerate(lines, start=1):

        if sql_pattern.search(line):
            findings.append({
                "line": index,
                "target": "TEXT_SQL_WRITE_MARKER",
                "types": [
                    sql_pattern.search(line).group(1).upper()
                ],
                "source": line.strip(),
            })

        if db_call_pattern.search(line):
            findings.append({
                "line": index,
                "target": "TEXT_DATABASE_CALL",
                "types": ["DATABASE_CALL"],
                "source": line.strip(),
            })

    return findings


# ============================================================================
# FILE CLASSIFICATION
# ============================================================================

def classify_write_context(
    source: str,
    ast_findings: list[dict[str, Any]],
    text_findings: list[dict[str, Any]],
) -> dict[str, Any]:

    source_lower = source.lower()

    production_markers = detect_terms(
        source_lower,
        PRODUCTION_DB_TERMS,
    )

    isolated_markers = detect_terms(
        source_lower,
        ISOLATED_PAPER_TERMS,
    )

    live_markers = detect_terms(
        source_lower,
        LIVE_TERMS,
    )

    all_findings = (
        ast_findings +
        text_findings
    )

    sql_write_findings = [
        item
        for item in all_findings
        if (
            "SQL_WRITE" in item["target"]
            or "TEXT_SQL_WRITE" in item["target"]
        )
    ]

    database_calls = [
        item
        for item in all_findings
        if (
            item["target"] in {
                "DATABASE_CONNECTION",
                "TEXT_DATABASE_CALL",
            }
        )
    ]

    if not sql_write_findings:
        classification = "NO_SQL_WRITE_CANDIDATE"

    elif production_markers and not isolated_markers:
        classification = (
            "LIVE_CANDIDATE_PRODUCTION_DB_WRITE"
        )

    elif production_markers and isolated_markers:
        classification = (
            "LIVE_CANDIDATE_WRITE_CONTEXT_MIXED"
        )

    elif isolated_markers:
        classification = (
            "LIVE_CANDIDATE_ISOLATED_PAPER_WRITE"
        )

    else:
        classification = (
            "LIVE_CANDIDATE_WRITE_CONTEXT_UNRESOLVED"
        )

    return {
        "classification": classification,
        "production_db_markers": production_markers,
        "isolated_paper_markers": isolated_markers,
        "live_markers": live_markers,
        "database_calls": database_calls,
        "sql_write_candidates": sql_write_findings,
    }


# ============================================================================
# FILE RECORD
# ============================================================================

def build_record(
    path: Path,
) -> dict[str, Any]:

    source, read_error = read_source(path)

    record: dict[str, Any] = {
        "file": str(relative_path(path)),
        "exists": path.exists(),
        "sha256": None,
        "size": None,
        "syntax_pass": False,
        "syntax_error": None,
        "classification": None,
        "production_db_markers": [],
        "isolated_paper_markers": [],
        "live_markers": [],
        "database_calls": [],
        "sql_write_candidates": [],
        "read_error": read_error,
    }

    if not path.exists():
        return record

    record["sha256"] = sha256_file(path)
    record["size"] = path.stat().st_size

    if source is None:
        record["classification"] = (
            "SOURCE_READ_FAILURE"
        )
        return record

    passed, syntax_error = syntax_check(
        source,
        str(path),
    )

    record["syntax_pass"] = passed
    record["syntax_error"] = syntax_error

    ast_findings = []
    text_findings = []

    if passed:
        ast_findings = find_ast_write_candidates(
            source
        )

    text_findings = find_text_write_candidates(
        source
    )

    context = classify_write_context(
        source,
        ast_findings,
        text_findings,
    )

    record.update(context)

    if not passed:
        record["classification"] = (
            "SYNTAX_FAILURE"
        )

    return record


# ============================================================================
# SUMMARY
# ============================================================================

def build_summary(
    records: list[dict[str, Any]],
) -> dict[str, Any]:

    production_candidates = [
        item
        for item in records
        if item["classification"]
        == "LIVE_CANDIDATE_PRODUCTION_DB_WRITE"
    ]

    mixed_candidates = [
        item
        for item in records
        if item["classification"]
        == "LIVE_CANDIDATE_WRITE_CONTEXT_MIXED"
    ]

    isolated_candidates = [
        item
        for item in records
        if item["classification"]
        == "LIVE_CANDIDATE_ISOLATED_PAPER_WRITE"
    ]

    unresolved_candidates = [
        item
        for item in records
        if item["classification"]
        == "LIVE_CANDIDATE_WRITE_CONTEXT_UNRESOLVED"
    ]

    syntax_failures = [
        item
        for item in records
        if not item["syntax_pass"]
    ]

    sql_write_files = [
        item
        for item in records
        if item["sql_write_candidates"]
    ]

    return {
        "python_files_scanned": len(records),
        "syntax_pass": sum(
            1
            for item in records
            if item["syntax_pass"]
        ),
        "syntax_fail": len(syntax_failures),
        "sql_write_files": len(
            sql_write_files
        ),
        "production_db_write_candidates": len(
            production_candidates
        ),
        "mixed_write_candidates": len(
            mixed_candidates
        ),
        "isolated_paper_write_candidates": len(
            isolated_candidates
        ),
        "unresolved_write_candidates": len(
            unresolved_candidates
        ),
    }


# ============================================================================
# VERDICT
# ============================================================================

def build_verdict(
    summary: dict[str, Any],
) -> str:

    if summary["syntax_fail"] > 0:
        return "SYNTAX_GATE_NOT_CLEAN"

    if summary[
        "production_db_write_candidates"
    ] > 0:
        return (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_BLOCKED"
        )

    if summary["mixed_write_candidates"] > 0:
        return (
            "LIVE_DATA_BOUNDARY_WRITE_CONTEXT_REVIEW_REQUIRED"
        )

    if summary["unresolved_write_candidates"] > 0:
        return (
            "LIVE_DATA_BOUNDARY_WRITE_CONTEXT_UNRESOLVED"
        )

    if summary["isolated_paper_write_candidates"] > 0:
        return (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_PAPER_ISOLATED"
        )

    return "LIVE_DATA_BOUNDARY_SQL_WRITE_CLEAR"


# ============================================================================
# REPORT TEXT
# ============================================================================

def make_report_text(
    started: str,
    finished: str,
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    verdict: str,
) -> str:

    lines: list[str] = []

    sep = "=" * 100

    lines.append(sep)
    lines.append(
        "ARUNDA LIVE CANDIDATE SQL WRITE FORENSIC "
        + VERSION
    )
    lines.append(sep)
    lines.append(
        f"Project Directory : {PROJECT_DIR}"
    )
    lines.append(
        f"Started UTC       : {started}"
    )
    lines.append(
        f"Finished UTC      : {finished}"
    )
    lines.append(
        f"Mode              : {MODE}"
    )
    lines.append(
        "Database Write    : NOT PERFORMED"
    )
    lines.append(
        "Network            : NOT USED"
    )
    lines.append(
        "Production Run     : NOT PERFORMED"
    )
    lines.append(
        "Live Source Run    : NOT PERFORMED"
    )
    lines.append(
        "Quarantine         : NOT TOUCHED"
    )
    lines.append(sep)
    lines.append("")

    lines.append(sep)
    lines.append("SYNTAX / WRITE INVENTORY")
    lines.append(sep)
    lines.append(
        f"Python Files Scanned              : "
        f"{summary['python_files_scanned']}"
    )
    lines.append(
        f"Syntax PASS                       : "
        f"{summary['syntax_pass']}"
    )
    lines.append(
        f"Syntax FAIL                       : "
        f"{summary['syntax_fail']}"
    )
    lines.append(
        f"SQL Write Files                   : "
        f"{summary['sql_write_files']}"
    )
    lines.append(
        f"Production DB Write Candidates    : "
        f"{summary['production_db_write_candidates']}"
    )
    lines.append(
        f"Mixed Write Candidates            : "
        f"{summary['mixed_write_candidates']}"
    )
    lines.append(
        f"Isolated/Paper Write Candidates   : "
        f"{summary['isolated_paper_write_candidates']}"
    )
    lines.append(
        f"Unresolved Write Candidates       : "
        f"{summary['unresolved_write_candidates']}"
    )
    lines.append("")

    for record in records:

        writes = record["sql_write_candidates"]

        if not writes:
            continue

        lines.append(sep)
        lines.append(
            f"FILE : {record['file']}"
        )
        lines.append(
            f"CLASS : {record['classification']}"
        )
        lines.append(
            f"SYNTAX PASS : {record['syntax_pass']}"
        )

        if record["production_db_markers"]:
            lines.append(
                "PRODUCTION DB MARKERS : "
                + ", ".join(
                    record["production_db_markers"]
                )
            )
        else:
            lines.append(
                "PRODUCTION DB MARKERS : None"
            )

        if record["isolated_paper_markers"]:
            lines.append(
                "ISOLATED/PAPER MARKERS : "
                + ", ".join(
                    record["isolated_paper_markers"]
                )
            )
        else:
            lines.append(
                "ISOLATED/PAPER MARKERS : None"
            )

        if record["live_markers"]:
            lines.append(
                "LIVE MARKERS : "
                + ", ".join(
                    record["live_markers"]
                )
            )
        else:
            lines.append(
                "LIVE MARKERS : None"
            )

        lines.append("")
        lines.append("WRITE CANDIDATES:")

        for write in writes:

            lines.append(
                f"  LINE           : "
                f"{write.get('line')}"
            )

            lines.append(
                f"  TARGET         : "
                f"{write.get('target')}"
            )

            types = write.get(
                "types",
                [],
            )

            lines.append(
                "  TYPES          : "
                + (
                    ", ".join(types)
                    if types
                    else "None"
                )
            )

            lines.append(
                f"  SOURCE         : "
                f"{write.get('source')}"
            )

            lines.append("")

    lines.append(sep)
    lines.append("FORENSIC VERDICT")
    lines.append(sep)
    lines.append(
        f"FORENSIC STATUS : {verdict}"
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
        "LIVE SOURCE RUN  : NOT PERFORMED"
    )
    lines.append(sep)

    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    started = utc_now()

    records: list[dict[str, Any]] = []

    python_files = discover_python_files()

    for path in python_files:
        records.append(
            build_record(path)
        )

    summary = build_summary(records)

    verdict = build_verdict(summary)

    finished = utc_now()

    artifact = {
        "version": VERSION,
        "project_directory": str(
            PROJECT_DIR
        ),
        "started_utc": started,
        "finished_utc": finished,
        "mode": MODE,
        "database_write": False,
        "network_used": False,
        "production_run": False,
        "live_source_run": False,
        "quarantine_touched": False,
        "quarantine_directory_excluded": True,
        "summary": summary,
        "verdict": verdict,
        "records": records,
    }

    report_text = make_report_text(
        started,
        finished,
        records,
        summary,
        verdict,
    )

    # ------------------------------------------------------------------------
    # Output artifacts are the ONLY files written by this forensic script.
    # No production DB, project source, or quarantine file is modified.
    # ------------------------------------------------------------------------

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            artifact,
            f,
            indent=2,
            ensure_ascii=False,
        )

    OUTPUT_TXT.write_text(
        report_text,
        encoding="utf-8",
    )

    print(report_text)
    print("")
    print(sep := "=" * 100)
    print("ARTIFACT")
    print(sep)
    print(
        f"Artifact : {OUTPUT_JSON}"
    )
    print(
        f"Report   : {OUTPUT_TXT}"
    )
    print(sep)


if __name__ == "__main__":
    main()
```
