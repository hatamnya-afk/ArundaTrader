import ast
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.1"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

ARTIFACT_NAME = "ARUNDA_LIVE_DATA_BOUNDARY_PREFLIGHT_FORENSIC_v0.1.json"
REPORT_NAME = "ARUNDA_LIVE_DATA_BOUNDARY_PREFLIGHT_FORENSIC_v0.1.txt"

QUARANTINE_DIR = "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"

# Production/runtime candidates only.
LIVE_KEYWORDS = (
    "live",
    "runtime",
    "market",
    "data",
    "signal",
    "fusion",
    "execution",
    "order",
)

NETWORK_MODULES = {
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "websocket",
    "websockets",
    "ccxt",
}

DB_MODULES = {
    "sqlite3",
}

FORBIDDEN_WRITE_TOKENS = (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "DROP TABLE",
    "ALTER TABLE",
    "CREATE TABLE",
    "REPLACE INTO",
)

LIVE_SOURCE_TOKENS = (
    "requests.",
    "httpx.",
    "aiohttp.",
    "urllib.",
    "websocket",
    "websockets",
    "ccxt",
)

ENTRYPOINT_TOKENS = (
    "if __name__",
    "def main(",
)


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


def print_section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def python_files() -> list[Path]:
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if QUARANTINE_DIR in path.parts:
            continue

        if "__pycache__" in path.parts:
            continue

        files.append(path)

    return sorted(files)


def syntax_check(path: Path) -> tuple[bool, str | None]:
    try:
        source = read_text(path)
        ast.parse(source, filename=str(path))
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def extract_imports(tree: ast.AST) -> set[str]:
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])

    return modules


def source_flags(source: str) -> dict[str, bool]:
    upper = source.upper()

    return {
        "network_usage": any(token.lower() in source.lower()
                             for token in LIVE_SOURCE_TOKENS),
        "database_usage": "sqlite3" in source.lower()
        or "sqlite" in source.lower(),
        "write_sql_present": any(token in upper
                                 for token in FORBIDDEN_WRITE_TOKENS),
        "live_source_present": any(token.lower() in source.lower()
                                   for token in LIVE_SOURCE_TOKENS),
        "main_present": any(token in source for token in ENTRYPOINT_TOKENS),
    }


def classify_file(path: Path) -> dict[str, Any]:
    source = read_text(path)

    syntax_ok, syntax_error = syntax_check(path)

    record: dict[str, Any] = {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "syntax_pass": syntax_ok,
        "syntax_error": syntax_error,
        "imports": [],
        "network_usage": False,
        "database_usage": False,
        "write_sql_present": False,
        "live_source_present": False,
        "main_present": False,
    }

    if not syntax_ok:
        return record

    try:
        tree = ast.parse(source, filename=str(path))
        imports = sorted(extract_imports(tree))

        flags = source_flags(source)

        record["imports"] = imports
        record.update(flags)

    except Exception as exc:
        record["syntax_pass"] = False
        record["syntax_error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return record


def database_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "sha256": None,
            "size": None,
            "tables": [],
        }

    tables: list[str] = []

    try:
        with sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
        ) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            ).fetchall()

            tables = [row[0] for row in rows]

    except Exception as exc:
        return {
            "exists": True,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
            "tables": [],
            "error": str(exc),
        }

    return {
        "exists": True,
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
        "tables": tables,
    }


def detect_live_boundary_candidates(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    candidates = []

    for record in records:
        name = record["file"].lower()

        keyword_match = any(
            keyword in name
            for keyword in LIVE_KEYWORDS
        )

        if (
            keyword_match
            or record["network_usage"]
            or record["live_source_present"]
        ):
            candidates.append(record)

    return candidates


def main() -> None:
    started = utc_now()

    print("=" * 100)
    print(
        "ARUNDA LIVE DATA BOUNDARY PREFLIGHT FORENSIC "
        + VERSION
    )
    print("=" * 100)

    print_section("SAFETY CONTRACT")

    print("Mode              : READ ONLY")
    print("Database writes   : FORBIDDEN")
    print("Network execution : FORBIDDEN")
    print("Production run    : FORBIDDEN")
    print("Order execution   : FORBIDDEN")
    print("Synthetic data    : FORBIDDEN")
    print("Prediction        : FORBIDDEN")
    print("Historical repair : FORBIDDEN")
    print("Universe rebuild  : FORBIDDEN")

    print_section("PROJECT INVENTORY")

    files = python_files()

    print(f"Python files      : {len(files)}")
    print(f"Quarantine ignored: {QUARANTINE_DIR}")

    records = [
        classify_file(path)
        for path in files
    ]

    syntax_failures = [
        record
        for record in records
        if not record["syntax_pass"]
    ]

    print(f"Syntax PASS       : {len(records) - len(syntax_failures)}")
    print(f"Syntax FAIL       : {len(syntax_failures)}")

    print_section("LIVE BOUNDARY CANDIDATES")

    candidates = detect_live_boundary_candidates(records)

    print(f"Candidate files   : {len(candidates)}")

    network_candidates = [
        r for r in candidates
        if r["network_usage"]
    ]

    database_candidates = [
        r for r in candidates
        if r["database_usage"]
    ]

    write_candidates = [
        r for r in candidates
        if r["write_sql_present"]
    ]

    live_source_candidates = [
        r for r in candidates
        if r["live_source_present"]
    ]

    for record in candidates:
        print("-" * 100)
        print(f"FILE              : {record['file']}")
        print(f"NETWORK USAGE     : {record['network_usage']}")
        print(f"DATABASE USAGE   : {record['database_usage']}")
        print(f"WRITE SQL         : {record['write_sql_present']}")
        print(f"LIVE SOURCE       : {record['live_source_present']}")
        print(f"MAIN PRESENT      : {record['main_present']}")

    print_section("PRODUCTION DATABASE BASELINE")

    before_db = database_fingerprint(PRODUCTION_DB)

    print(f"Exists            : {before_db['exists']}")
    print(f"Size              : {before_db['size']}")
    print(f"SHA256            : {before_db['sha256']}")

    if before_db["exists"]:
        print(f"Tables            : {len(before_db['tables'])}")

    print_section("LIVE DATA BOUNDARY PREFLIGHT")

    checks = {
        "SYNTAX_GATE":
            len(syntax_failures) == 0,

        "LIVE_SOURCE_PRESENT":
            len(live_source_candidates) > 0,

        "NETWORK_BOUNDARY_IDENTIFIED":
            len(network_candidates) > 0,

        "DATABASE_READ_BOUNDARY_IDENTIFIED":
            len(database_candidates) > 0,

        "NO_WRITE_SQL_IN_LIVE_CANDIDATES":
            len(write_candidates) == 0,
    }

    for name, status in checks.items():
        print(
            f"{name:<45}: "
            + ("PASS" if status else "BLOCKED")
        )

    # This is intentionally NOT a launch authorization.
    boundary_ready = all(checks.values())

    if boundary_ready:
        status = "LIVE_DATA_BOUNDARY_PREFLIGHT_PASSED"
    else:
        status = "LIVE_DATA_BOUNDARY_PREFLIGHT_BLOCKED"

    print()
    print(f"FORENSIC STATUS : {status}")

    print()
    print("IMPORTANT:")
    print(
        "This artifact does NOT execute the live source, "
        "does NOT inject live data, and does NOT authorize orders."
    )

    print_section("ARTIFACT")

    finished = utc_now()

    report = {
        "version": VERSION,
        "frontier": "LIVE_DATA_BOUNDARY_PREFLIGHT",
        "status": status,
        "started_utc": started,
        "finished_utc": finished,
        "mode": "READ_ONLY",
        "network_execution": False,
        "database_write": False,
        "production_run": False,
        "order_execution": False,
        "synthetic_data": False,
        "prediction": False,
        "historical_repair": False,
        "universe_rebuild": False,
        "python_files_scanned": len(files),
        "syntax_failures": len(syntax_failures),
        "candidate_files": len(candidates),
        "network_candidates": len(network_candidates),
        "database_candidates": len(database_candidates),
        "live_source_candidates": len(live_source_candidates),
        "write_candidates": len(write_candidates),
        "checks": checks,
        "production_db_before": before_db,
        "boundary_ready": boundary_ready,
        "syntax_failure_files": [
            r["file"]
            for r in syntax_failures
        ],
        "live_boundary_candidates": candidates,
    }

    output = PROJECT_ROOT / ARTIFACT_NAME
    text_report = PROJECT_ROOT / REPORT_NAME

    with output.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    summary_lines = [
        "ARUNDA LIVE DATA BOUNDARY PREFLIGHT FORENSIC "
        + VERSION,
        "=" * 100,
        f"Status : {status}",
        f"Python files scanned : {len(files)}",
        f"Syntax failures      : {len(syntax_failures)}",
        f"Live source candidates : {len(live_source_candidates)}",
        f"Network candidates      : {len(network_candidates)}",
        f"Database candidates     : {len(database_candidates)}",
        f"Write candidates        : {len(write_candidates)}",
        f"Boundary ready          : {boundary_ready}",
        "",
        "DATABASE WRITE : NOT PERFORMED",
        "NETWORK        : NOT EXECUTED",
        "PRODUCTION RUN : NOT PERFORMED",
        "ORDER EXECUTION : NOT PERFORMED",
    ]

    text_report.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print(f"Artifact : {output}")
    print(f"Report   : {text_report}")
    print(f"SHA256   : {sha256_file(output)}")


if __name__ == "__main__":
    main()