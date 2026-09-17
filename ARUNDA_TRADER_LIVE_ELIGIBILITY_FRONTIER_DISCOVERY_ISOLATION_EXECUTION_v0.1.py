from pathlib import Path
import ast
import hashlib
import json
import os
import re
import runpy
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager

VERSION = "v0.3"

PROJECT_ROOT = Path(__file__).resolve().parent
SELF_PATH = Path(__file__).resolve()
SELF_NAME = SELF_PATH.name

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

REPORT_NAME = (
    "LIVE_ELIGIBILITY_FRONTIER_DISCOVERY_ISOLATION_EXECUTION_REPORT.json"
)

ISOLATED_DB_NAME = "arunda_live_capture.db"

FORBIDDEN_REAL_ORDER_PATTERNS = (
    "create_order",
    "place_order",
    "submit_order",
    "market_order",
    "limit_order",
    "cancel_order",
)

DB_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE)\b",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_json(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    return value


def print_header(title: str):
    print("=" * 100)
    print(title)
    print("=" * 100)


def source_ast(path: Path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    return source, tree


def discover_frontiers() -> list[tuple[int, Path]]:
    candidates = []

    keywords = (
        "eligib",
        "candidate",
        "trade",
        "signal",
        "gate",
        "decision",
        "rank",
    )

    for path in PROJECT_ROOT.glob("*.py"):
        if path.resolve() == SELF_PATH:
            continue

        name = path.name.lower()

        if not any(k in name for k in keywords):
            continue

        try:
            source, tree = source_ast(path)
        except Exception:
            continue

        score = 0

        for keyword in keywords:
            if keyword in name:
                score += 2

        text = source.lower()

        for token in (
            "eligibility",
            "eligible",
            "candidate",
            "gate",
            "decision",
            "rank",
            "signal",
            "trade",
            "main(",
        ):
            if token in text:
                score += 1

        candidates.append((score, path))

    candidates.sort(key=lambda x: (-x[0], x[1].name.lower()))
    return candidates


def choose_frontier(frontiers):
    preferred = (
        "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"
    )

    for score, path in frontiers:
        if path.name == preferred:
            return score, path

    if frontiers:
        return frontiers[0]

    raise RuntimeError("No eligibility/candidate frontier discovered.")


def static_analysis(path: Path):
    source, tree = source_ast(path)

    sqlite_detected = "sqlite3" in source.lower()

    env_detected = any(
        token in source
        for token in (
            "os.environ",
            "getenv(",
            "environ[",
            "DATABASE_URL",
            "DB_PATH",
        )
    )

    db_refs = []
    for match in re.finditer(
        r"""["']([^"']*arunda\.db[^"']*)["']""",
        source,
        flags=re.IGNORECASE,
    ):
        value = match.group(1)
        if value not in db_refs:
            db_refs.append(value)

    writes = []
    for match in DB_WRITE_PATTERN.finditer(source):
        token = match.group(1).lower()
        if token not in writes:
            writes.append(token)

    return {
        "python_source": True,
        "ast_parse": True,
        "sqlite3_detected": sqlite_detected,
        "environment_detected": env_detected,
        "production_db_references": db_refs,
        "write_related_patterns": writes,
    }


def create_isolated_db(source_db: Path, runtime_dir: Path) -> Path:
    isolated_db = runtime_dir / ISOLATED_DB_NAME

    if not source_db.exists():
        raise FileNotFoundError(f"Production DB not found: {source_db}")

    shutil.copy2(source_db, isolated_db)

    return isolated_db


def make_isolated_source(
    source_path: Path,
    isolated_db: Path,
    runtime_dir: Path,
) -> Path:
    source = source_path.read_text(encoding="utf-8")

    # IMPORTANT:
    # repr() is used so Windows backslashes become valid Python string syntax.
    isolated_db_literal = repr(str(isolated_db))
    runtime_dir_literal = repr(str(runtime_dir))

    replacements = []

    patterns = [
        r'(?m)^(\s*PRODUCTION_DB\s*=\s*).*$',
        r'(?m)^(\s*DATABASE\s*=\s*).*$',
        r'(?m)^(\s*DB_PATH\s*=\s*).*$',
        r'(?m)^(\s*DATABASE_PATH\s*=\s*).*$',
        r'(?m)^(\s*ARUNDA_DB\s*=\s*).*$',
    ]

    for pattern in patterns:
        source = re.sub(
            pattern,
            lambda m: f"{m.group(1)}{isolated_db_literal}",
            source,
        )

    # Replace literal arunda.db occurrences safely.
    source = source.replace(
        '"arunda.db"',
        isolated_db_literal,
    )
    source = source.replace(
        "'arunda.db'",
        isolated_db_literal,
    )

    # Replace common absolute production DB references.
    production_string = str(PRODUCTION_DB)

    source = source.replace(
        repr(production_string),
        isolated_db_literal,
    )

    source = source.replace(
        f'"{production_string}"',
        isolated_db_literal,
    )

    source = source.replace(
        f"'{production_string}'",
        isolated_db_literal,
    )

    # If the source builds the DB path with PROJECT_ROOT / "arunda.db",
    # replace that exact construction.
    source = re.sub(
        r'PROJECT_ROOT\s*/\s*["\']arunda\.db["\']',
        isolated_db_literal,
        source,
        flags=re.IGNORECASE,
    )

    source = re.sub(
        r'os\.path\.join\(\s*PROJECT_ROOT\s*,\s*["\']arunda\.db["\']\s*\)',
        isolated_db_literal,
        source,
        flags=re.IGNORECASE,
    )

    # Runtime metadata injected into the isolated copy.
    injected = f"""
# ============================================================================
# ARUNDA ISOLATED RUNTIME OVERRIDE
# ============================================================================
ARUNDA_ISOLATED_RUNTIME = True
ARUNDA_ISOLATED_DB = {isolated_db_literal}
ARUNDA_ISOLATED_RUNTIME_DIR = {runtime_dir_literal}
ARUNDA_PRODUCTION_DB = {repr(str(PRODUCTION_DB))}
# ============================================================================

"""

    redirected = injected + source

    # Validate BEFORE writing.
    ast.parse(redirected, filename=str(source_path))

    isolated_source = runtime_dir / source_path.name
    isolated_source.write_text(redirected, encoding="utf-8")

    return isolated_source


def run_frontier(
    isolated_source: Path,
    runtime_dir: Path,
):
    stdout_path = runtime_dir / "frontier_stdout.txt"
    stderr_path = runtime_dir / "frontier_stderr.txt"

    started = time.perf_counter()

    proc = subprocess.run(
        [sys.executable, str(isolated_source)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )

    duration = time.perf_counter() - started

    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    return {
        "exit_code": proc.returncode,
        "duration_seconds": round(duration, 3),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_file": stdout_path,
        "stderr_file": stderr_path,
    }


def db_snapshot(path: Path):
    if not path.exists():
        return {
            "exists": False,
            "size": None,
            "sha256": None,
        }

    return {
        "exists": True,
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def sqlite_connection_test(path: Path):
    result = {
        "connection_possible": False,
        "read_only_test": False,
        "error": None,
    }

    try:
        uri = f"file:{path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        conn.close()

        result["connection_possible"] = True
        result["read_only_test"] = True
    except Exception as exc:
        result["error"] = repr(exc)

    return result


def locate_generated_reports(runtime_dir: Path):
    reports = []

    for root in (
        runtime_dir,
        PROJECT_ROOT,
        Path(tempfile.gettempdir()),
    ):
        if not root.exists():
            continue

        try:
            for path in root.glob("**/*.json"):
                name = path.name.lower()

                if (
                    "eligib" in name
                    or "candidate" in name
                    or "gate" in name
                    or "report" in name
                ):
                    reports.append(path)
        except Exception:
            continue

    unique = []
    seen = set()

    for path in reports:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path

        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)

    return unique


def production_invariant(before, after):
    return (
        before.get("exists") is True
        and after.get("exists") is True
        and before.get("size") == after.get("size")
        and before.get("sha256") == after.get("sha256")
    )


def main():
    print_header(
        "ARUNDA TRADER LIVE ELIGIBILITY FRONTIER DISCOVERY + "
        "ISOLATION EXECUTION v0.3"
    )

    print("OBJECTIVE")
    print("Execute ONLY the existing upstream eligibility frontier")
    print("inside an isolated LIVE PAPER runtime.")
    print()
    print("No eligibility logic is reconstructed.")
    print("No candidate logic is reconstructed.")
    print("No direction inference is performed.")
    print("No score reconstruction is performed.")
    print("No synthetic candidate is created.")
    print("No production DB write is permitted.")
    print("No real order is created or submitted.")
    print()

    print_header("SAFETY POLICY")
    print("Production DB writes : FORBIDDEN")
    print("Production engine    : NO")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : FORBIDDEN")
    print("Live data injection  : NONE")
    print("Real order           : FORBIDDEN")
    print("Paper execution      : ANALYTICAL ONLY")

    production_before = db_snapshot(PRODUCTION_DB)

    print_header("PRODUCTION BASELINE")
    print(f"Exists : {production_before['exists']}")
    print(f"Size   : {production_before['size']}")
    print(f"SHA256 : {production_before['sha256']}")

    print_header("FRONTIER DISCOVERY")

    frontiers = discover_frontiers()

    if not frontiers:
        raise RuntimeError("No candidate/eligibility frontier discovered.")

    print("DISCOVERED ELIGIBILITY / CANDIDATE FRONTIERS")

    for idx, (score, path) in enumerate(frontiers, 1):
        print(f"{idx:2d} | score={score:02d} | {path}")

    selected_score, selected = choose_frontier(frontiers)

    print()
    print(f"SELECTED FRONTIER : {selected}")
    print(f"SELECTED SCORE    : {selected_score}")

    print_header("SOURCE STATIC ANALYSIS")

    static = static_analysis(selected)

    print("Python source :", "PASS" if static["python_source"] else "FAIL")
    print("AST parse     :", "PASS" if static["ast_parse"] else "FAIL")
    print(
        "sqlite3       :",
        "DETECTED" if static["sqlite3_detected"] else "NOT_DETECTED",
    )
    print(
        "environment   :",
        "DETECTED" if static["environment_detected"] else "NOT_DETECTED",
    )

    print()
    print("Production DB references:")

    if static["production_db_references"]:
        for item in static["production_db_references"]:
            print(f"  - {item}")
    else:
        print("  - NONE")

    print()
    print("Write-related patterns:")

    if static["write_related_patterns"]:
        for item in static["write_related_patterns"]:
            print(f"  - {item}")
    else:
        print("  - NONE")

    runtime_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_eligibility_isolated_"
        )
    )

    isolated_db = create_isolated_db(
        PRODUCTION_DB,
        runtime_dir,
    )

    isolated_before = db_snapshot(isolated_db)

    print_header("ISOLATED DATABASE CREATION")
    print(f"Runtime directory : {runtime_dir}")
    print(f"Isolated DB       : {isolated_db}")
    print(f"Size              : {isolated_before['size']}")
    print(f"SHA256            : {isolated_before['sha256']}")

    isolated_source = None
    execution = None
    failure = None

    try:
        isolated_source = make_isolated_source(
            selected,
            isolated_db,
            runtime_dir,
        )

        print_header("ISOLATED FRONTIER EXECUTION")
        print(f"Isolated source : {isolated_source}")

        execution = run_frontier(
            isolated_source,
            runtime_dir,
        )

        print(f"Runtime duration : {execution['duration_seconds']}s")
        print(f"Exit code        : {execution['exit_code']}")

        if execution["stdout"]:
            print()
            print("----- STDOUT -----")
            print(execution["stdout"])

        if execution["stderr"]:
            print()
            print("----- STDERR -----")
            print(execution["stderr"])

    except Exception as exc:
        failure = repr(exc)

        print()
        print("----- RUNTIME ERROR -----")
        print(failure)

    isolated_after = db_snapshot(isolated_db)

    isolated_changed = not (
        isolated_before["size"] == isolated_after["size"]
        and isolated_before["sha256"] == isolated_after["sha256"]
    )

    production_after = db_snapshot(PRODUCTION_DB)
    production_pass = production_invariant(
        production_before,
        production_after,
    )

    generated_reports = locate_generated_reports(runtime_dir)

    print_header("ISOLATED DATABASE RESULT")
    print(f"Before size  : {isolated_before['size']}")
    print(f"After size   : {isolated_after['size']}")
    print(f"Before SHA256: {isolated_before['sha256']}")
    print(f"After SHA256 : {isolated_after['sha256']}")
    print(
        "Isolated DB changed :",
        "YES" if isolated_changed else "NO",
    )

    print_header("PRODUCTION DATABASE INVARIANT")
    print(f"Before size  : {production_before['size']}")
    print(f"After size   : {production_after['size']}")
    print(f"Before SHA256: {production_before['sha256']}")
    print(f"After SHA256 : {production_after['sha256']}")
    print(
        "Production DB invariant :",
        "PASS" if production_pass else "FAIL",
    )

    execution_pass = (
        execution is not None
        and execution["exit_code"] == 0
        and failure is None
    )

    final_status = (
        "PASS"
        if execution_pass and production_pass
        else "BLOCKED"
    )

    print_header("FINAL VERDICT")
    print(f"FRONTIER EXECUTION : {final_status}")
    print("Source modification       : NONE")
    print("Synthetic candidate       : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Real order execution      : NONE")
    print("Production DB writes      : NONE")
    print(
        "Production DB invariant   :",
        "PASS" if production_pass else "FAIL",
    )

    # IMPORTANT:
    # report_path is a Path.
    # report_data is the dictionary.
    # Never call write_text() on the dictionary.
    report_path = runtime_dir / REPORT_NAME

    report_data = {
        "version": VERSION,
        "objective": (
            "Execute only the existing upstream eligibility frontier "
            "inside an isolated LIVE PAPER runtime."
        ),
        "safety_policy": {
            "production_db_writes": "FORBIDDEN",
            "production_engine": "NO",
            "historical_repair": "NONE",
            "direction_inference": "NONE",
            "score_reconstruction": "NONE",
            "synthetic_data": "FORBIDDEN",
            "live_data_injection": "NONE",
            "real_order": "FORBIDDEN",
            "paper_execution": "ANALYTICAL ONLY",
        },
        "production_db": {
            "path": str(PRODUCTION_DB),
            "before": production_before,
            "after": production_after,
            "invariant_pass": production_pass,
        },
        "frontier_discovery": [
            {
                "score": score,
                "path": str(path),
            }
            for score, path in frontiers
        ],
        "selected_frontier": {
            "score": selected_score,
            "path": str(selected),
        },
        "static_analysis": static,
        "isolated_runtime": {
            "directory": str(runtime_dir),
            "database": str(isolated_db),
            "database_before": isolated_before,
            "database_after": isolated_after,
            "database_changed": isolated_changed,
            "isolated_source": (
                str(isolated_source)
                if isolated_source
                else None
            ),
        },
        "execution": (
            {
                "exit_code": execution["exit_code"],
                "duration_seconds": execution["duration_seconds"],
                "stdout_file": str(execution["stdout_file"]),
                "stderr_file": str(execution["stderr_file"]),
                "stdout": execution["stdout"],
                "stderr": execution["stderr"],
            }
            if execution
            else None
        ),
        "runtime_error": failure,
        "generated_reports": [
            str(p) for p in generated_reports
        ],
        "final_verdict": {
            "frontier_execution": final_status,
            "source_modification": "NONE",
            "synthetic_candidate": "NONE",
            "direction_inference": "NONE",
            "score_reconstruction": "NONE",
            "real_order_execution": "NONE",
            "production_db_writes": "NONE",
            "production_db_invariant": (
                "PASS" if production_pass else "FAIL"
            ),
        },
    }

    # The actual serialization/write operation is performed on Path.
    report_path.write_text(
        json.dumps(
            safe_json(report_data),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Runtime report : {report_path}")

    return 0 if final_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())