import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.2"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

QUARANTINE_DIR_NAME = "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"

ARTIFACT_NAME = "ARUNDA_LIVE_CANDIDATE_SQL_WRITE_FORENSIC_v0.2.json"
REPORT_NAME = "ARUNDA_LIVE_CANDIDATE_SQL_WRITE_FORENSIC_v0.2.txt"

WRITE_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "CREATE",
    "REPLACE",
)

LIVE_TERMS = (
    "LIVE",
    "LAUNCH",
    "RUNTIME",
    "EXECUTION",
    "ORDER",
    "TRADE",
)

DB_TERMS = (
    "sqlite",
    "sqlite3",
    "connect(",
    ".db",
    "execute(",
    "executemany(",
    "executescript(",
)

PRODUCTION_DB_TERMS = (
    "arunda.db",
    "PRODUCTION_DB",
    "PRODUCTION_DATABASE",
)

ISOLATED_DB_TERMS = (
    "arunda_live_capture.db",
    "isolated",
    "paper",
    "capture",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def is_quarantined(path: Path) -> bool:
    return QUARANTINE_DIR_NAME in path.parts


def discover_python_files() -> list[Path]:
    files = []

    for path in PROJECT_DIR.rglob("*.py"):
        if is_quarantined(path):
            continue

        files.append(path)

    return sorted(files)


def read_source(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def syntax_status(source: str) -> tuple[bool, str | None]:
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as exc:
        return False, str(exc)


def classify_sql_context(
    source: str,
    line_no: int,
    context: str,
) -> dict[str, Any]:

    lines = source.splitlines()

    start = max(1, line_no - 8)
    end = min(len(lines), line_no + 8)

    nearby = "\n".join(
        lines[start - 1:end]
    )

    nearby_upper = nearby.upper()

    write_operations = []

    for keyword in WRITE_KEYWORDS:
        if keyword in context.upper():
            write_operations.append(keyword)

    production_markers = []

    for term in PRODUCTION_DB_TERMS:
        if term.upper() in nearby_upper:
            production_markers.append(term)

    isolated_markers = []

    for term in ISOLATED_DB_TERMS:
        if term.upper() in nearby_upper:
            isolated_markers.append(term)

    if production_markers:
        target_class = "PRODUCTION_DB_WRITE_CANDIDATE"

    elif isolated_markers:
        target_class = "ISOLATED_OR_PAPER_DB_WRITE_CANDIDATE"

    else:
        target_class = "UNRESOLVED_DB_WRITE_CONTEXT"

    return {
        "write_operations": sorted(
            set(write_operations)
        ),
        "production_db_markers": production_markers,
        "isolated_paper_markers": isolated_markers,
        "target_class": target_class,
        "nearby_context": nearby,
    }


def scan_file(path: Path) -> dict[str, Any]:

    source = read_source(path)

    syntax_pass, syntax_error = syntax_status(source)

    upper = source.upper()

    live_markers = [
        term
        for term in LIVE_TERMS
        if term in upper
    ]

    database_markers = [
        term
        for term in DB_TERMS
        if term.upper() in upper
    ]

    records = []

    for line_no, line in enumerate(
        source.splitlines(),
        start=1,
    ):

        line_upper = line.upper()

        matched = [
            keyword
            for keyword in WRITE_KEYWORDS
            if keyword in line_upper
        ]

        if not matched:
            continue

        context = classify_sql_context(
            source,
            line_no,
            line.strip(),
        )

        records.append(
            {
                "line": line_no,
                "source": line.strip(),
                "matched_write_keywords": matched,
                **context,
            }
        )

    return {
        "file": str(path),
        "relative_file": str(
            path.relative_to(PROJECT_DIR)
        ),
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "syntax_pass": syntax_pass,
        "syntax_error": syntax_error,
        "live_markers": sorted(
            set(live_markers)
        ),
        "database_markers": sorted(
            set(database_markers)
        ),
        "sql_write_records": records,
        "sql_write_count": len(records),
    }


def determine_file_class(
    record: dict[str, Any],
) -> str:

    relative = record["relative_file"].upper()

    live_score = len(
        record["live_markers"]
    )

    if "LIVE" in relative:
        live_score += 3

    if "LAUNCH" in relative:
        live_score += 2

    if "RUNTIME" in relative:
        live_score += 2

    if "EXECUTION" in relative:
        live_score += 2

    if live_score == 0:
        return "NON_LIVE_CANDIDATE"

    if record["sql_write_count"] == 0:
        return "LIVE_CANDIDATE_NO_SQL_WRITE"

    has_production = any(
        item["target_class"]
        == "PRODUCTION_DB_WRITE_CANDIDATE"
        for item in record["sql_write_records"]
    )

    if has_production:
        return "LIVE_CANDIDATE_PRODUCTION_WRITE"

    has_isolated = any(
        item["target_class"]
        == "ISOLATED_OR_PAPER_DB_WRITE_CANDIDATE"
        for item in record["sql_write_records"]
    )

    if has_isolated:
        return "LIVE_CANDIDATE_ISOLATED_PAPER_WRITE"

    return "LIVE_CANDIDATE_WRITE_CONTEXT_UNRESOLVED"


def main() -> None:

    started = datetime.now(timezone.utc)

    print_section(
        "ARUNDA LIVE CANDIDATE SQL WRITE FORENSIC "
        + VERSION
    )

    print(
        "Project Directory : "
        + str(PROJECT_DIR)
    )
    print(
        "Started UTC       : "
        + started.isoformat()
    )
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : FORBIDDEN")
    print("Execution         : STATIC ANALYSIS ONLY")
    print("Database Write    : FORBIDDEN")
    print("File Modification : FORBIDDEN")
    print("Deletion          : FORBIDDEN")
    print("Quarantine        : FORBIDDEN")

    files = discover_python_files()

    print_section("PROJECT INVENTORY")

    print(
        "Python Files Scanned : "
        + str(len(files))
    )

    print(
        "Quarantine Excluded  : "
        + QUARANTINE_DIR_NAME
    )

    results = []

    for path in files:

        record = scan_file(path)

        record["classification"] = (
            determine_file_class(record)
        )

        results.append(record)

    live_candidates = [
        item
        for item in results
        if item["classification"].startswith(
            "LIVE_CANDIDATE"
        )
    ]

    live_with_writes = [
        item
        for item in live_candidates
        if item["sql_write_count"] > 0
    ]

    production_write_candidates = []
    isolated_write_candidates = []
    unresolved_write_candidates = []

    for item in live_with_writes:

        for write in item["sql_write_records"]:

            target_class = write["target_class"]

            if (
                target_class
                == "PRODUCTION_DB_WRITE_CANDIDATE"
            ):
                production_write_candidates.append(
                    (item, write)
                )

            elif (
                target_class
                == "ISOLATED_OR_PAPER_DB_WRITE_CANDIDATE"
            ):
                isolated_write_candidates.append(
                    (item, write)
                )

            else:
                unresolved_write_candidates.append(
                    (item, write)
                )

    print_section("LIVE CANDIDATE INVENTORY")

    print(
        "Live Candidates               : "
        + str(len(live_candidates))
    )

    print(
        "Live Candidates With SQL Write: "
        + str(len(live_with_writes))
    )

    print(
        "Production Write Candidates   : "
        + str(len(production_write_candidates))
    )

    print(
        "Isolated/Paper Write Candidates: "
        + str(len(isolated_write_candidates))
    )

    print(
        "Unresolved Write Candidates   : "
        + str(len(unresolved_write_candidates))
    )

    print_section("SQL WRITE FINDINGS")

    for item in live_with_writes:

        print("-" * 100)

        print(
            "FILE           : "
            + item["relative_file"]
        )

        print(
            "CLASSIFICATION : "
            + item["classification"]
        )

        print(
            "SYNTAX PASS    : "
            + str(item["syntax_pass"])
        )

        print(
            "SHA256         : "
            + item["sha256"]
        )

        for write in item["sql_write_records"]:

            print()

            print(
                "LINE           : "
                + str(write["line"])
            )

            print(
                "WRITE TYPES    : "
                + ", ".join(
                    write["write_operations"]
                )
            )

            print(
                "TARGET CLASS   : "
                + write["target_class"]
            )

            print(
                "SOURCE         : "
                + write["source"]
            )

            production_text = (
                ", ".join(
                    write["production_db_markers"]
                )
                if write["production_db_markers"]
                else "None"
            )

            isolated_text = (
                ", ".join(
                    write["isolated_paper_markers"]
                )
                if write["isolated_paper_markers"]
                else "None"
            )

            print(
                "PROD MARKERS   : "
                + production_text
            )

            print(
                "ISOLATED MARKERS: "
                + isolated_text
            )

    if production_write_candidates:

        status = (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_BLOCKED"
        )

    elif unresolved_write_candidates:

        status = (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_CONTEXT_UNRESOLVED"
        )

    elif isolated_write_candidates:

        status = (
            "LIVE_CANDIDATE_WRITES_ISOLATED_OR_PAPER_ONLY"
        )

    else:

        status = (
            "NO_LIVE_CANDIDATE_SQL_WRITE_OBSERVED"
        )

    finished = datetime.now(timezone.utc)

    print_section("FORENSIC VERDICT")

    print(
        "FORENSIC STATUS : "
        + status
    )

    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("DATABASE WRITE   : NOT PERFORMED")
    print("NETWORK          : NOT USED")
    print("PRODUCTION RUN   : NOT PERFORMED")
    print("LIVE SOURCE RUN  : NOT PERFORMED")

    if production_write_candidates:

        print()
        print(
            "BLOCKER : Production DB write candidate "
            "exists inside a live candidate."
        )

    elif unresolved_write_candidates:

        print()
        print(
            "BLOCKER : SQL write context requires "
            "manual/static dependency resolution."
        )

    elif isolated_write_candidates:

        print()
        print(
            "INTERPRETATION : SQL writes are associated "
            "with isolated/paper/capture context."
        )

    else:

        print()
        print(
            "INTERPRETATION : No SQL write operation was "
            "observed in live candidates."
        )

    artifact = {
        "version": VERSION,
        "project_directory": str(PROJECT_DIR),
        "mode": "READ_ONLY",
        "database_used": False,
        "network_used": False,
        "execution_performed": False,
        "database_write_performed": False,
        "files_modified": False,
        "files_deleted": False,
        "quarantine_performed": False,
        "python_files_scanned": len(files),
        "live_candidates": len(live_candidates),
        "live_candidates_with_sql_write": len(
            live_with_writes
        ),
        "production_write_candidates": len(
            production_write_candidates
        ),
        "isolated_paper_write_candidates": len(
            isolated_write_candidates
        ),
        "unresolved_write_candidates": len(
            unresolved_write_candidates
        ),
        "status": status,
        "results": results,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
    }

    artifact_path = PROJECT_DIR / ARTIFACT_NAME
    report_path = PROJECT_DIR / REPORT_NAME

    with artifact_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            artifact,
            f,
            indent=2,
            ensure_ascii=False,
        )

    report_lines = [
        "ARUNDA LIVE CANDIDATE SQL WRITE FORENSIC "
        + VERSION,
        "",
        "Project Directory : "
        + str(PROJECT_DIR),
        "Started UTC       : "
        + started.isoformat(),
        "Finished UTC      : "
        + finished.isoformat(),
        "Mode              : READ ONLY",
        "Database          : NOT USED",
        "Network           : FORBIDDEN",
        "Execution         : STATIC ANALYSIS ONLY",
        "",
        "Python Files Scanned : "
        + str(len(files)),
        "Live Candidates      : "
        + str(len(live_candidates)),
        "Live With SQL Write  : "
        + str(len(live_with_writes)),
        "Production Writes    : "
        + str(len(production_write_candidates)),
        "Isolated/Paper Writes: "
        + str(len(isolated_write_candidates)),
        "Unresolved Writes    : "
        + str(len(unresolved_write_candidates)),
        "",
        "FORENSIC STATUS : "
        + status,
        "DATABASE WRITE   : NOT PERFORMED",
        "NETWORK          : NOT USED",
        "PRODUCTION RUN   : NOT PERFORMED",
        "",
    ]

    for item in live_with_writes:

        report_lines.append(
            "FILE : "
            + item["relative_file"]
        )

        report_lines.append(
            "CLASSIFICATION : "
            + item["classification"]
        )

        for write in item["sql_write_records"]:

            report_lines.append(
                "LINE : "
                + str(write["line"])
            )

            report_lines.append(
                "WRITE TYPES : "
                + ", ".join(
                    write["write_operations"]
                )
            )

            report_lines.append(
                "TARGET CLASS : "
                + write["target_class"]
            )

            report_lines.append(
                "SOURCE : "
                + write["source"]
            )

            report_lines.append("")

    report_path.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print_section("ARTIFACT")

    print(
        "Artifact : "
        + str(artifact_path)
    )

    print(
        "Report   : "
        + str(report_path)
    )

    print(
        "SHA256   : "
        + sha256_file(artifact_path)
    )


if __name__ == "__main__":
    main()