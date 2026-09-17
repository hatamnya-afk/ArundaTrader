```python
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.2"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

QUARANTINE_DIR_NAME = "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"

OUTPUT_JSON = PROJECT_DIR / (
    "ARUNDA_LIVE_CANDIDATE_SQL_WRITE_FORENSIC_v0.2.json"
)

OUTPUT_TXT = PROJECT_DIR / (
    "ARUNDA_LIVE_CANDIDATE_SQL_WRITE_FORENSIC_v0.2.txt"
)


PRODUCTION_DB_TERMS = (
    "arunda.db",
    "production_db",
    "production database",
    "prod_db",
)

ISOLATED_PAPER_TERMS = (
    "arunda_live_capture.db",
    "paper",
    "isolated",
    "simulation",
    "dry_run",
    "dry-run",
)

WRITE_SQL_TERMS = (
    "insert ",
    "update ",
    "delete ",
    "replace ",
    "create table",
    "create index",
    "drop table",
    "drop index",
    "alter table",
)

DB_CALL_TERMS = (
    "sqlite3.connect",
    "connection.execute",
    "conn.execute",
    "cursor.execute",
    "executemany",
    "executescript",
)

LIVE_TERMS = (
    "live",
    "production",
    "execution",
    "order",
    "trade",
    "exchange",
    "bitpin",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def is_quarantined(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_DIR)
    except ValueError:
        return False

    return QUARANTINE_DIR_NAME in relative.parts


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
    return [
        term
        for term in terms
        if term in source_lower
    ]


def syntax_check(
    source: str,
) -> tuple[bool, str | None, int | None, int | None]:
    try:
        ast.parse(source)
        return True, None, None, None

    except SyntaxError as exc:
        return (
            False,
            exc.msg,
            exc.lineno,
            exc.offset,
        )

    except Exception as exc:
        return (
            False,
            f"{type(exc).__name__}: {exc}",
            None,
            None,
        )


def get_call_name(node: ast.Call) -> str:
    function = node.func

    if isinstance(function, ast.Name):
        return function.id

    if isinstance(function, ast.Attribute):
        parts: list[str] = []

        current: ast.AST | None = function

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def extract_calls(tree: ast.AST) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = get_call_name(node)

        if not name:
            continue

        if name in DB_CALL_TERMS:
            calls.append(
                {
                    "line": getattr(node, "lineno", None),
                    "column": getattr(node, "col_offset", None),
                    "call": name,
                }
            )

    return calls


def extract_sql_strings(tree: ast.AST) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue

        if not isinstance(node.value, str):
            continue

        value = node.value
        lower = value.lower().strip()

        matched = [
            term
            for term in WRITE_SQL_TERMS
            if term in lower
        ]

        if not matched:
            continue

        findings.append(
            {
                "line": getattr(node, "lineno", None),
                "sql_markers": matched,
                "source": value[:500],
            }
        )

    return findings


def classify_file(
    path: Path,
    source: str | None,
    read_error: str | None,
) -> dict[str, Any]:

    relative = str(path.relative_to(PROJECT_DIR))

    record: dict[str, Any] = {
        "file": relative,
        "exists": path.exists(),
        "quarantined": is_quarantined(path),
        "read_error": read_error,
        "syntax_pass": None,
        "syntax_error": None,
        "syntax_line": None,
        "syntax_column": None,
        "production_db_markers": [],
        "isolated_paper_markers": [],
        "live_markers": [],
        "write_sql_markers": [],
        "db_calls": [],
        "sql_findings": [],
        "classification": "UNRESOLVED",
    }

    if source is None:
        record["classification"] = "READ_FAILURE"
        return record

    source_lower = source.lower()

    (
        syntax_pass,
        syntax_error,
        syntax_line,
        syntax_column,
    ) = syntax_check(source)

    record["syntax_pass"] = syntax_pass
    record["syntax_error"] = syntax_error
    record["syntax_line"] = syntax_line
    record["syntax_column"] = syntax_column

    record["production_db_markers"] = detect_terms(
        source_lower,
        PRODUCTION_DB_TERMS,
    )

    record["isolated_paper_markers"] = detect_terms(
        source_lower,
        ISOLATED_PAPER_TERMS,
    )

    record["live_markers"] = detect_terms(
        source_lower,
        LIVE_TERMS,
    )

    record["write_sql_markers"] = detect_terms(
        source_lower,
        WRITE_SQL_TERMS,
    )

    tree: ast.AST | None = None

    if syntax_pass:
        try:
            tree = ast.parse(source)
        except Exception:
            tree = None

    if tree is not None:
        record["db_calls"] = extract_calls(tree)
        record["sql_findings"] = extract_sql_strings(tree)

    has_write = bool(
        record["write_sql_markers"]
        or record["sql_findings"]
    )

    has_production = bool(
        record["production_db_markers"]
    )

    has_isolated = bool(
        record["isolated_paper_markers"]
    )

    has_live = bool(
        record["live_markers"]
    )

    if not syntax_pass:
        record["classification"] = "SYNTAX_FAILURE"

    elif has_write and has_production and has_live:
        record["classification"] = (
            "LIVE_CANDIDATE_PRODUCTION_DB_WRITE"
        )

    elif has_write and has_isolated:
        record["classification"] = (
            "LIVE_CANDIDATE_ISOLATED_OR_PAPER_WRITE"
        )

    elif has_write:
        record["classification"] = (
            "WRITE_CONTEXT_REQUIRES_REVIEW"
        )

    elif has_live:
        record["classification"] = (
            "LIVE_CANDIDATE_NO_WRITE_MARKER"
        )

    else:
        record["classification"] = "NO_RELEVANT_WRITE_MARKER"

    return record


def discover_python_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_DIR.rglob("*.py"):
        if is_quarantined(path):
            continue

        if path.is_file():
            files.append(path)

    return sorted(files)


def print_section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_file_record(record: dict[str, Any]) -> None:
    print()
    print("-" * 100)
    print(f"FILE           : {record['file']}")
    print(f"CLASSIFICATION : {record['classification']}")
    print(f"SYNTAX PASS    : {record['syntax_pass']}")

    if record["syntax_error"]:
        print(
            f"SYNTAX ERROR   : "
            f"{record['syntax_error']}"
        )

        print(
            f"LINE           : "
            f"{record['syntax_line']}"
        )

    production = record["production_db_markers"]

    print(
        "PROD MARKERS   : "
        + (
            ", ".join(production)
            if production
            else "None"
        )
    )

    isolated = record["isolated_paper_markers"]

    print(
        "ISOLATED MARKERS: "
        + (
            ", ".join(isolated)
            if isolated
            else "None"
        )
    )

    live = record["live_markers"]

    print(
        "LIVE MARKERS   : "
        + (
            ", ".join(live)
            if live
            else "None"
        )
    )

    writes = record["write_sql_markers"]

    print(
        "WRITE MARKERS  : "
        + (
            ", ".join(writes)
            if writes
            else "None"
        )
    )

    calls = record["db_calls"]

    if calls:
        print("DB CALLS:")

        for call in calls:
            print(
                f"  LINE {call['line']} | "
                f"{call['call']}"
            )

    sql_findings = record["sql_findings"]

    if sql_findings:
        print("SQL FINDINGS:")

        for finding in sql_findings:
            markers = finding["sql_markers"]

            print(
                f"  LINE {finding['line']} | "
                f"{', '.join(markers)}"
            )


def main() -> None:
    started = datetime.now(timezone.utc)

    print("=" * 100)
    print(
        "ARUNDA LIVE CANDIDATE SQL WRITE "
        f"FORENSIC {VERSION}"
    )
    print("=" * 100)

    print(f"Project Directory : {PROJECT_DIR}")
    print(f"Started UTC       : {started.isoformat()}")
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : FORBIDDEN")
    print("Production Run    : NOT PERFORMED")
    print("Database Write    : NOT PERFORMED")
    print("File Modification : FORBIDDEN")

    print_section("SAFETY BOUNDARY")

    print("Production DB connection : FORBIDDEN")
    print("Production DB write      : FORBIDDEN")
    print("Network access           : FORBIDDEN")
    print("Live source execution    : FORBIDDEN")
    print("Order execution          : FORBIDDEN")
    print("SQL execution            : FORBIDDEN")
    print("Static source analysis   : ENABLED")

    files = discover_python_files()

    print_section("PYTHON INVENTORY")

    print(
        f"Python Files Scanned : "
        f"{len(files)}"
    )

    records: list[dict[str, Any]] = []

    syntax_pass = 0
    syntax_fail = 0

    production_write_candidates = 0
    isolated_write_candidates = 0
    unresolved_write_candidates = 0

    for path in files:
        source, read_error = read_source(path)

        record = classify_file(
            path,
            source,
            read_error,
        )

        records.append(record)

        if record["syntax_pass"] is True:
            syntax_pass += 1
        elif record["syntax_pass"] is False:
            syntax_fail += 1

        classification = record["classification"]

        if classification == (
            "LIVE_CANDIDATE_PRODUCTION_DB_WRITE"
        ):
            production_write_candidates += 1

        elif classification == (
            "LIVE_CANDIDATE_ISOLATED_OR_PAPER_WRITE"
        ):
            isolated_write_candidates += 1

        elif classification == (
            "WRITE_CONTEXT_REQUIRES_REVIEW"
        ):
            unresolved_write_candidates += 1

    print(f"Syntax PASS          : {syntax_pass}")
    print(f"Syntax FAIL          : {syntax_fail}")

    print_section("WRITE BOUNDARY CANDIDATES")

    candidates = [
        record
        for record in records
        if record["classification"]
        in (
            "LIVE_CANDIDATE_PRODUCTION_DB_WRITE",
            "LIVE_CANDIDATE_ISOLATED_OR_PAPER_WRITE",
            "WRITE_CONTEXT_REQUIRES_REVIEW",
        )
    ]

    if not candidates:
        print("NONE")

    else:
        for record in candidates:
            print_file_record(record)

    print_section("CROSS-TARGET SUMMARY")

    print(
        f"Production DB write candidates : "
        f"{production_write_candidates}"
    )

    print(
        f"Isolated/Paper write candidates : "
        f"{isolated_write_candidates}"
    )

    print(
        f"Unresolved write candidates     : "
        f"{unresolved_write_candidates}"
    )

    print(
        f"Syntax failures                 : "
        f"{syntax_fail}"
    )

    if production_write_candidates > 0:
        status = (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_BLOCKED"
        )

    elif syntax_fail > 0:
        status = "SYNTAX_GATE_NOT_CLEAN"

    elif unresolved_write_candidates > 0:
        status = (
            "LIVE_DATA_BOUNDARY_WRITE_CONTEXT_REVIEW"
        )

    else:
        status = (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_CLEAN"
        )

    finished = datetime.now(timezone.utc)

    report = {
        "version": VERSION,
        "project_directory": str(PROJECT_DIR),
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "mode": "READ_ONLY",
        "database_used": False,
        "network_used": False,
        "production_run": False,
        "database_write_performed": False,
        "file_modification_performed": False,
        "quarantine_directory_excluded": True,
        "python_files_scanned": len(files),
        "syntax_pass": syntax_pass,
        "syntax_fail": syntax_fail,
        "production_db_write_candidates": (
            production_write_candidates
        ),
        "isolated_paper_write_candidates": (
            isolated_write_candidates
        ),
        "unresolved_write_candidates": (
            unresolved_write_candidates
        ),
        "status": status,
        "candidates": candidates,
        "all_records": records,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            report,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    lines: list[str] = []

    lines.append(
        "ARUNDA LIVE CANDIDATE SQL WRITE "
        f"FORENSIC {VERSION}"
    )
    lines.append("=" * 100)
    lines.append(
        f"Project Directory : {PROJECT_DIR}"
    )
    lines.append(
        f"Started UTC       : {started.isoformat()}"
    )
    lines.append(
        f"Finished UTC      : {finished.isoformat()}"
    )
    lines.append("Mode              : READ ONLY")
    lines.append("Database          : NOT USED")
    lines.append("Network           : FORBIDDEN")
    lines.append(
        "Production Run    : NOT PERFORMED"
    )
    lines.append(
        "Database Write    : NOT PERFORMED"
    )
    lines.append(
        "File Modification : FORBIDDEN"
    )
    lines.append("")
    lines.append(
        "PYTHON FILES SCANNED : "
        f"{len(files)}"
    )
    lines.append(
        "SYNTAX PASS          : "
        f"{syntax_pass}"
    )
    lines.append(
        "SYNTAX FAIL          : "
        f"{syntax_fail}"
    )
    lines.append("")
    lines.append(
        "PRODUCTION DB WRITE CANDIDATES : "
        f"{production_write_candidates}"
    )
    lines.append(
        "ISOLATED/PAPER WRITE CANDIDATES : "
        f"{isolated_write_candidates}"
    )
    lines.append(
        "UNRESOLVED WRITE CANDIDATES : "
        f"{unresolved_write_candidates}"
    )
    lines.append("")
    lines.append(
        "FORENSIC STATUS : "
        f"{status}"
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

    with OUTPUT_TXT.open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "\n".join(lines)
            + "\n"
        )

    print_section("FORENSIC VERDICT")

    print(
        f"FORENSIC STATUS : {status}"
    )

    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("DATABASE WRITE   : NOT PERFORMED")
    print("NETWORK          : NOT USED")
    print("PRODUCTION RUN   : NOT PERFORMED")
    print("LIVE SOURCE RUN  : NOT PERFORMED")

    if production_write_candidates:
        print()
        print(
            "BLOCKER : Production DB write "
            "candidate exists inside a live candidate."
        )

    elif unresolved_write_candidates:
        print()
        print(
            "REVIEW : Write context exists but "
            "production-vs-isolated boundary "
            "could not be statically resolved."
        )

    elif syntax_fail:
        print()
        print(
            "BLOCKER : Syntax gate is not clean."
        )

    else:
        print()
        print(
            "RESULT : No unresolved production "
            "DB write candidate detected."
        )

    print_section("ARTIFACT")

    print(f"Artifact : {OUTPUT_JSON}")
    print(f"Report   : {OUTPUT_TXT}")
    print(
        "SHA256   : "
        f"{sha256_file(OUTPUT_JSON)}"
    )


if __name__ == "__main__":
    main()
```
