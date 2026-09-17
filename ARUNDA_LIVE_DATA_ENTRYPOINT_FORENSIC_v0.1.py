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
    "ARUNDA_LIVE_DATA_ENTRYPOINT_FORENSIC_v0.2.json"
)

OUTPUT_TXT = PROJECT_DIR / (
    "ARUNDA_LIVE_DATA_ENTRYPOINT_FORENSIC_v0.2.txt"
)


LIVE_TERMS = {
    "live",
    "realtime",
    "real_time",
    "live_data",
    "websocket",
    "websockets",
    "stream",
    "streaming",
    "ticker",
    "orderbook",
    "exchange",
    "bitpin",
    "market_data",
    "production",
}


NETWORK_MODULES = {
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "urllib3",
    "websocket",
    "websockets",
    "socket",
}


ORDER_CALLS = {
    "create_order",
    "place_order",
    "submit_order",
    "send_order",
    "cancel_order",
    "execute_order",
    "market_order",
    "limit_order",
    "buy_order",
    "sell_order",
}


DB_WRITE_TERMS = {
    "insert into",
    "update ",
    "delete from",
    "replace into",
    "create table",
    "alter table",
    "drop table",
}


LIVE_FUNCTION_TERMS = {
    "fetch",
    "fetch_data",
    "fetch_market_data",
    "get_market_data",
    "get_ticker",
    "get_order_book",
    "stream",
    "subscribe",
    "listen",
    "poll",
    "collect",
    "ingest",
    "receive",
    "consume",
}


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


def is_quarantined(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_DIR)
    except ValueError:
        return False

    return QUARANTINE_DIR_NAME in relative.parts


def discover_python_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_DIR.rglob("*.py"):
        if not path.is_file():
            continue

        if is_quarantined(path):
            continue

        files.append(path)

    return sorted(files)


def read_source(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def parse_source(
    source: str,
) -> tuple[ast.AST | None, bool, str | None]:

    try:
        tree = ast.parse(source)
        return tree, True, None

    except SyntaxError as exc:
        message = (
            f"{exc.msg}; "
            f"line={exc.lineno}; "
            f"column={exc.offset}"
        )
        return None, False, message

    except Exception as exc:
        return None, False, (
            f"{type(exc).__name__}: {exc}"
        )


def collect_imports(tree: ast.AST) -> list[str]:
    result: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                result.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module)

    return sorted(result)


def collect_functions(tree: ast.AST) -> list[str]:
    result: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result.add(node.name)

    return sorted(result)


def collect_calls(tree: ast.AST) -> list[str]:
    result: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):
                result.add(node.func.id)

            elif isinstance(node.func, ast.Attribute):
                result.add(node.func.attr)

    return sorted(result)


def find_term_markers(
    source_lower: str,
    terms: set[str],
) -> list[str]:

    found: list[str] = []

    for term in sorted(terms):

        if term.lower() in source_lower:
            found.append(term)

    return found


def find_network_imports(
    imports: list[str],
) -> list[str]:

    found: list[str] = []

    for module in imports:

        root = module.split(".")[0].lower()

        if root in NETWORK_MODULES:
            found.append(module)

    return sorted(set(found))


def find_order_calls(
    calls: list[str],
) -> list[str]:

    call_set = {
        item.lower()
        for item in calls
    }

    return sorted(
        term
        for term in ORDER_CALLS
        if term.lower() in call_set
    )


def find_live_functions(
    functions: list[str],
) -> list[str]:

    function_set = {
        item.lower()
        for item in functions
    }

    return sorted(
        term
        for term in LIVE_FUNCTION_TERMS
        if term.lower() in function_set
    )


def classify_record(
    path: Path,
    source: str,
    tree: ast.AST | None,
    syntax_pass: bool,
    syntax_error: str | None,
) -> dict[str, Any]:

    source_lower = source.lower()

    imports: list[str] = []
    functions: list[str] = []
    calls: list[str] = []

    if tree is not None:

        imports = collect_imports(tree)
        functions = collect_functions(tree)
        calls = collect_calls(tree)

    network_imports = find_network_imports(
        imports
    )

    order_calls = find_order_calls(
        calls
    )

    live_functions = find_live_functions(
        functions
    )

    live_markers = find_term_markers(
        source_lower,
        LIVE_TERMS,
    )

    db_write_markers = find_term_markers(
        source_lower,
        DB_WRITE_TERMS,
    )

    filename = path.name.lower()

    filename_live = any(
        term in filename
        for term in (
            "live",
            "realtime",
            "real_time",
            "websocket",
            "stream",
            "entrypoint",
        )
    )

    filename_forensic = (
        "forensic" in filename
        or "audit" in filename
        or "diagnostic" in filename
        or "repair" in filename
    )

    filename_test = (
        "test" in filename
        or "demo" in filename
        or "example" in filename
    )

    has_live_signal = bool(
        live_markers
        or live_functions
        or network_imports
        or filename_live
    )

    has_network = bool(
        network_imports
    )

    has_order_boundary = bool(
        order_calls
    )

    has_sql_write = bool(
        db_write_markers
    )

    if not syntax_pass:

        classification = "SYNTAX_FAILURE"
        relevance = "BLOCKED"

    elif filename_forensic:

        classification = "FORENSIC_TOOLING"
        relevance = "NON_PRODUCTION"

    elif filename_test:

        classification = "TEST_TOOLING"
        relevance = "NON_PRODUCTION"

    elif has_live_signal and has_order_boundary:

        classification = (
            "LIVE_EXECUTION_BOUNDARY_CANDIDATE"
        )
        relevance = "CRITICAL"

    elif has_live_signal and has_sql_write:

        classification = (
            "LIVE_DATA_SQL_WRITE_CANDIDATE"
        )
        relevance = "CRITICAL"

    elif has_live_signal:

        classification = (
            "LIVE_DATA_ENTRYPOINT_CANDIDATE"
        )
        relevance = "HIGH"

    elif has_order_boundary:

        classification = (
            "ORDER_BOUNDARY_CANDIDATE"
        )
        relevance = "HIGH"

    elif has_sql_write:

        classification = (
            "DATABASE_WRITE_CANDIDATE"
        )
        relevance = "MEDIUM"

    else:

        classification = (
            "NON_LIVE_SUPPORT"
        )
        relevance = "LOW"

    if has_network:
        network_boundary = "NETWORK_MARKER_PRESENT"
    else:
        network_boundary = "NO_NETWORK_MARKER"

    if has_sql_write:
        write_boundary = "SQL_WRITE_MARKER_PRESENT"
    else:
        write_boundary = "NO_SQL_WRITE_MARKER"

    if has_order_boundary:
        order_boundary = "ORDER_CALL_MARKER_PRESENT"
    else:
        order_boundary = "NO_EXPLICIT_ORDER_CALL"

    return {
        "file": str(
            path.relative_to(PROJECT_DIR)
        ),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "syntax_pass": syntax_pass,
        "syntax_error": syntax_error,
        "imports": imports,
        "functions": functions,
        "calls": calls,
        "live_markers": live_markers,
        "live_function_markers": live_functions,
        "network_imports": network_imports,
        "production_db_write_markers": db_write_markers,
        "order_call_markers": order_calls,
        "classification": classification,
        "launch_relevance": relevance,
        "network_boundary": network_boundary,
        "write_boundary": write_boundary,
        "order_boundary": order_boundary,
        "has_live_signal": has_live_signal,
        "has_network_marker": has_network,
        "has_sql_write_marker": has_sql_write,
        "has_order_marker": has_order_boundary,
    }


def write_json(
    report: dict[str, Any],
) -> None:

    OUTPUT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_text(
    report: dict[str, Any],
) -> None:

    lines: list[str] = []

    lines.append(
        "ARUNDA LIVE DATA ENTRYPOINT FORENSIC "
        + VERSION
    )

    lines.append("=" * 100)

    lines.append(
        f"Project Directory : {PROJECT_DIR}"
    )

    lines.append(
        f"Started UTC       : "
        f"{report['started_utc']}"
    )

    lines.append(
        f"Finished UTC      : "
        f"{report['finished_utc']}"
    )

    lines.append(
        "Mode              : READ ONLY"
    )

    lines.append(
        "Database          : NOT USED"
    )

    lines.append(
        "Network           : NOT USED"
    )

    lines.append(
        "Production Run    : NOT PERFORMED"
    )

    lines.append(
        "File Modification : NOT PERFORMED"
    )

    lines.append("=" * 100)

    lines.append(
        f"Python Files Scanned : "
        f"{report['files_scanned']}"
    )

    lines.append(
        f"Syntax PASS          : "
        f"{report['syntax_pass']}"
    )

    lines.append(
        f"Syntax FAIL          : "
        f"{report['syntax_fail']}"
    )

    lines.append("=" * 100)
    lines.append("LIVE DATA ENTRYPOINT CANDIDATES")
    lines.append("=" * 100)

    if not report["live_candidates"]:

        lines.append("NONE")

    else:

        for item in report["live_candidates"]:

            lines.append(
                f"{item['file']} | "
                f"{item['classification']} | "
                f"{item['launch_relevance']}"
            )

    lines.append("=" * 100)
    lines.append("LIVE + SQL WRITE CANDIDATES")
    lines.append("=" * 100)

    if not report["live_sql_write_candidates"]:

        lines.append("NONE")

    else:

        for item in (
            report["live_sql_write_candidates"]
        ):

            lines.append(
                f"{item['file']} | "
                f"{item['production_db_write_markers']}"
            )

    lines.append("=" * 100)
    lines.append("NETWORK CANDIDATES")
    lines.append("=" * 100)

    if not report["network_candidates"]:

        lines.append("NONE")

    else:

        for item in report["network_candidates"]:

            lines.append(
                f"{item['file']} | "
                f"{item['network_imports']}"
            )

    lines.append("=" * 100)
    lines.append("ORDER BOUNDARY CANDIDATES")
    lines.append("=" * 100)

    if not report["order_candidates"]:

        lines.append("NONE")

    else:

        for item in report["order_candidates"]:

            lines.append(
                f"{item['file']} | "
                f"{item['order_call_markers']}"
            )

    lines.append("=" * 100)
    lines.append("FORENSIC STATUS")
    lines.append("=" * 100)

    lines.append(
        f"FORENSIC STATUS : "
        f"{report['forensic_status']}"
    )

    lines.append(
        f"Live entrypoint candidates : "
        f"{len(report['live_candidates'])}"
    )

    lines.append(
        f"Live + SQL write candidates : "
        f"{len(report['live_sql_write_candidates'])}"
    )

    lines.append(
        f"Network candidates : "
        f"{len(report['network_candidates'])}"
    )

    lines.append(
        f"Order candidates : "
        f"{len(report['order_candidates'])}"
    )

    lines.append(
        "DATABASE WRITE : NOT PERFORMED"
    )

    lines.append(
        "NETWORK : NOT USED"
    )

    lines.append(
        "PRODUCTION RUN : NOT PERFORMED"
    )

    lines.append(
        "LIVE SOURCE RUN : NOT PERFORMED"
    )

    lines.append("=" * 100)
    lines.append("ARTIFACT")
    lines.append("=" * 100)

    lines.append(
        f"JSON : {OUTPUT_JSON}"
    )

    lines.append(
        f"TXT  : {OUTPUT_TXT}"
    )

    OUTPUT_TXT.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:

    started = utc_now()

    print("=" * 100)

    print(
        "ARUNDA LIVE DATA ENTRYPOINT FORENSIC "
        + VERSION
    )

    print("=" * 100)

    print()
    print("MODE              : READ ONLY")
    print("DATABASE          : NOT USED")
    print("NETWORK           : NOT USED")
    print("PRODUCTION RUN    : NOT PERFORMED")
    print("FILE MODIFICATION : NOT PERFORMED")
    print("ORDER EXECUTION   : NOT PERFORMED")
    print("LIVE SOURCE RUN   : NOT PERFORMED")

    if not PROJECT_DIR.exists():

        raise FileNotFoundError(
            f"Project directory not found: "
            f"{PROJECT_DIR}"
        )

    files = discover_python_files()

    records: list[dict[str, Any]] = []

    syntax_pass = 0
    syntax_fail = 0

    for path in files:

        source = read_source(path)

        tree, passed, error = parse_source(
            source
        )

        if passed:
            syntax_pass += 1
        else:
            syntax_fail += 1

        record = classify_record(
            path=path,
            source=source,
            tree=tree,
            syntax_pass=passed,
            syntax_error=error,
        )

        records.append(record)

    live_candidates = [
        item
        for item in records
        if item["has_live_signal"]
        and item["syntax_pass"]
        and item["classification"]
        not in {
            "FORENSIC_TOOLING",
            "TEST_TOOLING",
        }
    ]

    live_sql_write_candidates = [
        item
        for item in live_candidates
        if item["has_sql_write_marker"]
    ]

    network_candidates = [
        item
        for item in live_candidates
        if item["has_network_marker"]
    ]

    order_candidates = [
        item
        for item in records
        if item["has_order_marker"]
        and item["syntax_pass"]
    ]

    syntax_failures = [
        item
        for item in records
        if not item["syntax_pass"]
    ]

    if syntax_failures:

        forensic_status = (
            "SYNTAX_GATE_NOT_CLEAN"
        )

    elif live_sql_write_candidates:

        forensic_status = (
            "LIVE_DATA_BOUNDARY_SQL_WRITE_BLOCKED"
        )

    elif not live_candidates:

        forensic_status = (
            "LIVE_DATA_ENTRYPOINT_NOT_IDENTIFIED"
        )

    elif network_candidates:

        forensic_status = (
            "LIVE_DATA_NETWORK_ENTRYPOINT_IDENTIFIED"
        )

    else:

        forensic_status = (
            "LIVE_DATA_ENTRYPOINT_IDENTIFIED"
        )

    finished = utc_now()

    report: dict[str, Any] = {
        "version": VERSION,
        "project_directory": str(
            PROJECT_DIR
        ),
        "started_utc": started,
        "finished_utc": finished,
        "mode": "READ_ONLY",
        "database_used": False,
        "network_used": False,
        "production_run": False,
        "file_modification": False,
        "files_scanned": len(files),
        "syntax_pass": syntax_pass,
        "syntax_fail": syntax_fail,
        "forensic_status": forensic_status,
        "live_candidates": live_candidates,
        "live_sql_write_candidates": (
            live_sql_write_candidates
        ),
        "network_candidates": network_candidates,
        "order_candidates": order_candidates,
        "syntax_failures": syntax_failures,
        "records": records,
    }

    print()
    print("=" * 100)
    print("SYNTAX INVENTORY")
    print("=" * 100)

    print(
        f"Python Files Scanned : {len(files)}"
    )

    print(
        f"Syntax PASS          : {syntax_pass}"
    )

    print(
        f"Syntax FAIL          : {syntax_fail}"
    )

    print()
    print("=" * 100)
    print("LIVE DATA ENTRYPOINT CANDIDATES")
    print("=" * 100)

    if not live_candidates:

        print("NONE")

    else:

        for item in live_candidates:

            print(
                f"{item['file']} | "
                f"{item['classification']} | "
                f"{item['launch_relevance']}"
            )

    print()
    print("=" * 100)
    print("LIVE + SQL WRITE CANDIDATES")
    print("=" * 100)

    if not live_sql_write_candidates:

        print("NONE")

    else:

        for item in live_sql_write_candidates:

            print(
                f"{item['file']} | "
                f"{item['production_db_write_markers']}"
            )

    print()
    print("=" * 100)
    print("NETWORK CANDIDATES")
    print("=" * 100)

    if not network_candidates:

        print("NONE")

    else:

        for item in network_candidates:

            print(
                f"{item['file']} | "
                f"{item['network_imports']}"
            )

    print()
    print("=" * 100)
    print("ORDER BOUNDARY CANDIDATES")
    print("=" * 100)

    if not order_candidates:

        print("NONE")

    else:

        for item in order_candidates:

            print(
                f"{item['file']} | "
                f"{item['order_call_markers']}"
            )

    print()
    print("=" * 100)
    print("FORENSIC STATUS")
    print("=" * 100)

    print(
        f"FORENSIC STATUS : "
        f"{forensic_status}"
    )

    print(
        "DATABASE WRITE : NOT PERFORMED"
    )

    print(
        "NETWORK : NOT USED"
    )

    print(
        "PRODUCTION RUN : NOT PERFORMED"
    )

    print(
        "LIVE SOURCE RUN : NOT PERFORMED"
    )

    write_json(report)
    write_text(report)

    print()
    print("=" * 100)
    print("ARTIFACT")
    print("=" * 100)

    print(
        f"Artifact : {OUTPUT_JSON}"
    )

    print(
        f"Report   : {OUTPUT_TXT}"
    )

    print("=" * 100)

    print("DONE")


if __name__ == "__main__":
    main()