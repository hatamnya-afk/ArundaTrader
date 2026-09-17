import os
import sys
import time
import json
import hashlib
import sqlite3
import tempfile
import runpy
import traceback
from pathlib import Path

# ============================================================
# ARUNDA TRADER
# LIVE TRADE CANDIDATE RANKING + MULTI-ASSET DECISION GATE
# ISOLATION EXECUTION v0.2
# ============================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = BASE_DIR / "arunda.db"

FRONTIER_CANDIDATES = [
    BASE_DIR / "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_DECISION_GATE_v0.1.py",
    BASE_DIR / "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py",
]

SELF_PREFIXES = (
    "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_DECISION_GATE_ISOLATION_EXECUTION_",
)


def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def snapshot(path):
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() else None,
    }


def discover_frontier():
    results = []

    for path in FRONTIER_CANDIDATES:
        if not path.is_file():
            continue

        if path.name.startswith(SELF_PREFIXES):
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            continue

        score = 0
        low = source.lower()

        for term in (
            "candidate",
            "ranking",
            "decision",
            "gate",
            "trade",
        ):
            if term in low:
                score += 1

        if "isolation_execution" in low:
            score -= 20

        results.append((score, path))

    results.sort(
        key=lambda x: (-x[0], str(x[1]).lower())
    )

    return results


def clone_database(source):
    runtime_dir = Path(
        tempfile.mkdtemp(
            prefix="arunda_candidate_isolated_"
        )
    )

    isolated_db = runtime_dir / "arunda_live_capture.db"

    print(f"Runtime directory : {runtime_dir}")
    print(f"Isolated DB       : {isolated_db}")

    src = sqlite3.connect(
        f"file:{source}?mode=ro",
        uri=True,
        timeout=60,
    )

    dst = sqlite3.connect(
        str(isolated_db),
        timeout=60,
    )

    try:
        src.backup(
            dst,
            pages=10000,
            progress=None,
            sleep=0.01,
        )
        dst.commit()
    finally:
        dst.close()
        src.close()

    return runtime_dir, isolated_db


def install_sqlite_isolation(isolated_db):
    original_connect = sqlite3.connect

    production_abs = os.path.normcase(
        os.path.abspath(str(PRODUCTION_DB))
    )

    isolated_abs = os.path.normcase(
        os.path.abspath(str(isolated_db))
    )

    counters = {
        "sqlite_connect_calls": 0,
        "production_redirects": 0,
        "isolated_connections": 0,
        "other_connections": 0,
    }

    def isolated_connect(database, *args, **kwargs):
        counters["sqlite_connect_calls"] += 1

        original_database = database

        if isinstance(database, os.PathLike):
            database = os.fspath(database)

        redirect = False

        if isinstance(database, str):
            raw = database.strip()

            try:
                normalized_abs = os.path.normcase(
                    os.path.abspath(raw)
                )
            except Exception:
                normalized_abs = ""

            if normalized_abs == production_abs:
                redirect = True

            normalized = raw.replace("/", "\\").lower()

            relative_production_names = {
                "arunda.db",
                ".\\arunda.db",
                "arundatrader\\arunda.db",
                ".\\arundatrader\\arunda.db",
            }

            if normalized in relative_production_names:
                redirect = True

            if normalized_abs == isolated_abs:
                redirect = False

        if redirect:
            counters["production_redirects"] += 1
            counters["isolated_connections"] += 1
            return original_connect(
                str(isolated_db),
                *args,
                **kwargs,
            )

        counters["other_connections"] += 1

        return original_connect(
            original_database,
            *args,
            **kwargs,
        )

    sqlite3.connect = isolated_connect

    return original_connect, counters


def restore_sqlite(original_connect):
    sqlite3.connect = original_connect


def execute_frontier(frontier, isolated_db):
    original_connect, counters = install_sqlite_isolation(
        isolated_db
    )

    old_argv = sys.argv[:]
    old_cwd = os.getcwd()

    start = time.perf_counter()

    stdout_error = None
    exit_code = 0

    try:
        sys.argv = [str(frontier)]

        os.chdir(str(BASE_DIR))

        try:
            runpy.run_path(
                str(frontier),
                run_name="__main__",
            )
        except SystemExit as exc:
            if exc.code is None:
                exit_code = 0
            elif isinstance(exc.code, int):
                exit_code = exc.code
            else:
                exit_code = 1

    except KeyboardInterrupt:
        exit_code = 130
        stdout_error = "KeyboardInterrupt"

    except Exception:
        exit_code = 1
        stdout_error = traceback.format_exc()

    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
        restore_sqlite(original_connect)

    duration = time.perf_counter() - start

    return {
        "exit_code": exit_code,
        "runtime_seconds": round(duration, 3),
        "error": stdout_error,
        "counters": counters,
    }


def main():
    section(
        "ARUNDA TRADER LIVE TRADE CANDIDATE RANKING + "
        "MULTI-ASSET DECISION GATE ISOLATION EXECUTION v0.2"
    )

    print("""
OBJECTIVE
Execute ONLY the existing upstream candidate-generation frontier
inside an isolated LIVE PAPER runtime.

No candidate logic is reconstructed.
No direction inference is performed.
No score reconstruction is performed.
No synthetic candidate is created.
No production DB write is permitted.
No real order is created or submitted.
""")

    section("SAFETY POLICY")

    print("Production DB writes : FORBIDDEN")
    print("Production engine    : NO")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : FORBIDDEN")
    print("Live data injection  : NONE")
    print("Real order           : FORBIDDEN")
    print("Paper execution      : ANALYTICAL ONLY")

    section("PRODUCTION BASELINE")

    if not PRODUCTION_DB.exists():
        print("PRODUCTION DATABASE : NOT FOUND")
        return 2

    production_before = snapshot(PRODUCTION_DB)

    print(f"Exists : {production_before['exists']}")
    print(f"Size   : {production_before['size']}")
    print(f"SHA256 : {production_before['sha256']}")

    section("FRONTIER DISCOVERY")

    discovered = discover_frontier()

    if not discovered:
        print("FRONTIER DISCOVERY : FAILED")
        print()
        print(
            "No existing candidate-generation frontier was found."
        )
        print(
            "No fallback implementation will be created."
        )
        return 3

    print("DISCOVERED CANDIDATE-GENERATION FRONTIERS")

    for index, (score, path) in enumerate(discovered, 1):
        print(
            f"{index:2d} | score={score:02d} | {path}"
        )

    frontier = discovered[0][1]

    print()
    print(
        f"SELECTED FRONTIER : {frontier}"
    )

    section("ISOLATED DATABASE CREATION")

    runtime_dir, isolated_db = clone_database(
        PRODUCTION_DB
    )

    isolated_before = snapshot(isolated_db)

    print(
        f"Size   : {isolated_before['size']}"
    )
    print(
        f"SHA256 : {isolated_before['sha256']}"
    )

    if (
        isolated_before["size"]
        != production_before["size"]
    ):
        print(
            "ISOLATED DATABASE CLONE : FAILED"
        )
        return 4

    section("ISOLATED FRONTIER EXECUTION")

    result = execute_frontier(
        frontier,
        isolated_db,
    )

    print(
        f"Runtime duration : "
        f"{result['runtime_seconds']:.3f}s"
    )

    print(
        f"Exit code        : "
        f"{result['exit_code']}"
    )

    if result["error"]:
        print()
        print("----- RUNTIME ERROR -----")
        print(result["error"])

    section("ISOLATED DATABASE RESULT")

    isolated_after = snapshot(isolated_db)

    print(
        f"Before size  : {isolated_before['size']}"
    )
    print(
        f"After size   : {isolated_after['size']}"
    )
    print(
        f"Before SHA256: "
        f"{isolated_before['sha256']}"
    )
    print(
        f"After SHA256 : "
        f"{isolated_after['sha256']}"
    )

    isolated_changed = (
        isolated_before["size"]
        != isolated_after["size"]
        or isolated_before["sha256"]
        != isolated_after["sha256"]
    )

    print(
        f"Isolated DB changed : "
        f"{'YES' if isolated_changed else 'NO'}"
    )

    section("RUNTIME ISOLATION EVIDENCE")

    counters = result["counters"]

    print(
        f"SQLite redirect calls       : "
        f"{counters['sqlite_connect_calls']}"
    )
    print(
        f"Production DB redirects     : "
        f"{counters['production_redirects']}"
    )
    print(
        f"Isolated connections        : "
        f"{counters['isolated_connections']}"
    )
    print(
        f"Other SQLite connections   : "
        f"{counters['other_connections']}"
    )

    section("PRODUCTION DATABASE INVARIANT")

    production_after = snapshot(PRODUCTION_DB)

    print(
        f"Before size  : "
        f"{production_before['size']}"
    )
    print(
        f"After size   : "
        f"{production_after['size']}"
    )
    print(
        f"Before SHA256: "
        f"{production_before['sha256']}"
    )
    print(
        f"After SHA256 : "
        f"{production_after['sha256']}"
    )

    production_unchanged = (
        production_before["size"]
        == production_after["size"]
        and production_before["sha256"]
        == production_after["sha256"]
    )

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if production_unchanged else "FAIL")
    )

    section("FINAL VERDICT")

    if (
        result["exit_code"] == 0
        and production_unchanged
        and counters["production_redirects"] >= 0
    ):
        verdict = "FRONTIER EXECUTION : PASS"
    elif result["exit_code"] == 130:
        verdict = "FRONTIER EXECUTION : INTERRUPTED"
    else:
        verdict = "FRONTIER EXECUTION : FAILED"

    print(verdict)
    print("Source modification       : NONE")
    print("Synthetic candidate       : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Real order execution      : NONE")
    print(
        "Production DB writes      : "
        + ("NONE" if production_unchanged else "UNKNOWN/FAIL")
    )
    print(
        "Production DB invariant   : "
        + ("PASS" if production_unchanged else "FAIL")
    )

    report = {
        "version": "v0.2",
        "frontier": str(frontier),
        "runtime_directory": str(runtime_dir),
        "isolated_database": str(isolated_db),
        "production_before": production_before,
        "production_after": production_after,
        "production_invariant": production_unchanged,
        "isolated_before": isolated_before,
        "isolated_after": isolated_after,
        "isolated_changed": isolated_changed,
        "execution": result,
        "verdict": verdict,
        "safety": {
            "source_modification": False,
            "synthetic_candidate": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "real_order_execution": False,
            "production_db_writes": not production_unchanged,
        },
    }

    report_path = (
        runtime_dir
        / "LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_DECISION_GATE_ISOLATION_EXECUTION_REPORT.json"
    )

    try:
        report_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        print(
            f"\nWARNING: Could not write runtime report: {exc}"
        )
    else:
        print()
        print(
            f"Runtime report : {report_path}"
        )

    return (
        0
        if result["exit_code"] == 0
        and production_unchanged
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())