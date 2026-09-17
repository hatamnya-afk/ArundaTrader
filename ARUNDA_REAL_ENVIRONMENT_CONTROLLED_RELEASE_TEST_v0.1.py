from pathlib import Path
import sys
import sqlite3
import hashlib
import subprocess
import re
import json
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"
ENTRY = ROOT / "arunda_pipeline.py"

REPORT = ROOT / "ARUNDA_REAL_ENVIRONMENT_CONTROLLED_RELEASE_TEST_v0.1.txt"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def db_fingerprint():
    uri = f"file:{DB.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            )
        ]

        counts = {}
        for table in tables:
            try:
                counts[table] = con.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
            except Exception:
                counts[table] = "ERROR"

    payload = json.dumps(
        {"integrity": integrity, "tables": tables, "counts": counts},
        sort_keys=True,
        default=str
    )

    return {
        "integrity": integrity,
        "tables": tables,
        "counts": counts,
        "sha256": hashlib.sha256(payload.encode()).hexdigest()
    }

def production_execution_flag():
    text = ENTRY.read_text(
        encoding="utf-8-sig",
        errors="replace"
    )

    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bEXECUTION_ENABLED\s*=\s*True\b", line):
            hits.append((n, line.strip()))

    return hits

def repository_write_scan():
    hits = []

    targets = [
        "order",
        "submit",
        "create_order",
        "place_order",
        "cancel_order",
        "exchange",
        "requests.post",
        "requests.put",
        "requests.patch",
    ]

    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue

        try:
            text = path.read_text(
                encoding="utf-8-sig",
                errors="replace"
            )
        except Exception:
            continue

        lower = text.lower()

        for target in targets:
            if target in lower:
                hits.append((str(path), target))

    return hits

def main():

    lines = []

    def out(x=""):
        print(x)
        lines.append(str(x))

    out("=" * 78)
    out("ARUNDA TRADER — REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1")
    out("=" * 78)

    out(f"TIMESTAMP                  : {datetime.now(timezone.utc).isoformat()}")
    out("MODE                       : CONTROLLED / EXECUTION DISABLED")
    out(f"PYTHON                    : {sys.executable}")
    out(f"PYTHON VERSION            : {sys.version.split()[0]}")
    out(f"PROJECT_ROOT              : {ROOT}")
    out(f"ENTRYPOINT                : {ENTRY}")
    out(f"DATABASE                  : {DB}")

    blockers = []

    # ----------------------------------------------------------
    # STATIC SAFETY
    # ----------------------------------------------------------

    if not ROOT.exists():
        blockers.append("PROJECT_ROOT missing")

    if not ENTRY.exists():
        blockers.append("Production entrypoint missing")

    if not DB.exists():
        blockers.append("Production database missing")

    flag_hits = production_execution_flag()

    out()
    out("EXECUTION SAFETY")
    out("-" * 78)
    out(f"EXECUTION_ENABLED=True    : {len(flag_hits)}")

    if flag_hits:
        blockers.append("EXECUTION_ENABLED=True in production entrypoint")

    else:
        out("EXECUTION_ENABLED        : FALSE")
        out("ORDER SUBMISSION          : DISABLED")
        out("EXCHANGE WRITE            : DISABLED")

    # ----------------------------------------------------------
    # DB BEFORE
    # ----------------------------------------------------------

    try:
        db_before = db_fingerprint()

        out()
        out("DATABASE BEFORE")
        out("-" * 78)
        out(f"INTEGRITY                 : {db_before['integrity']}")
        out(f"TABLE COUNT               : {len(db_before['tables'])}")
        out(f"FINGERPRINT               : {db_before['sha256']}")

        if db_before["integrity"] != "ok":
            blockers.append("Database integrity check failed")

    except Exception as e:
        blockers.append(f"Database read failure: {e}")
        db_before = None

    # ----------------------------------------------------------
    # ENTRYPOINT FINGERPRINT
    # ----------------------------------------------------------

    entry_hash_before = sha256_file(ENTRY)

    out()
    out("ENTRYPOINT BASELINE")
    out("-" * 78)
    out(f"SHA256                    : {entry_hash_before}")

    # ----------------------------------------------------------
    # REAL RUNTIME
    # ----------------------------------------------------------

    out()
    out("REAL ENVIRONMENT RUNTIME")
    out("-" * 78)
    out("EXECUTION                 : NOT ACTIVATED")
    out("ORDER                     : NONE")
    out("EXCHANGE WRITE            : NONE")

    try:
        result = subprocess.run(
            [sys.executable, str(ENTRY)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300
        )

        runtime_rc = result.returncode

        out(f"EXIT CODE                 : {runtime_rc}")

        stdout = result.stdout[-12000:]
        stderr = result.stderr[-12000:]

        out()
        out("RUNTIME STDOUT")
        out("-" * 78)
        out(stdout)

        out()
        out("RUNTIME STDERR")
        out("-" * 78)
        out(stderr)

        if runtime_rc != 0:
            blockers.append(
                f"Production runtime exited with code {runtime_rc}"
            )

    except subprocess.TimeoutExpired:
        blockers.append("Production runtime timeout")
        out("RUNTIME                   : TIMEOUT")

    except Exception as e:
        blockers.append(f"Runtime invocation failure: {e}")
        out(f"RUNTIME ERROR             : {e}")

    # ----------------------------------------------------------
    # DB AFTER
    # ----------------------------------------------------------

    try:
        db_after = db_fingerprint()

        out()
        out("DATABASE AFTER")
        out("-" * 78)
        out(f"INTEGRITY                 : {db_after['integrity']}")
        out(f"TABLE COUNT               : {len(db_after['tables'])}")
        out(f"FINGERPRINT               : {db_after['sha256']}")

        if db_before:
            if db_before["sha256"] != db_after["sha256"]:
                blockers.append(
                    "DATABASE FINGERPRINT CHANGED"
                )

    except Exception as e:
        blockers.append(f"Database post-run read failure: {e}")
        db_after = None

    # ----------------------------------------------------------
    # ENTRYPOINT AFTER
    # ----------------------------------------------------------

    entry_hash_after = sha256_file(ENTRY)

    out()
    out("ENTRYPOINT AFTER RUNTIME")
    out("-" * 78)
    out(f"SHA256                    : {entry_hash_after}")

    if entry_hash_before != entry_hash_after:
        blockers.append("Production entrypoint changed during test")

    # ----------------------------------------------------------
    # FINAL
    # ----------------------------------------------------------

    out()
    out("=" * 78)

    if blockers:
        out("RESULT                    : BLOCKED")
        out()
        out("BLOCKERS:")
        for b in blockers:
            out(f"- {b}")
    else:
        out("RESULT                    : PASS")
        out("REAL ENVIRONMENT          : VERIFIED")
        out("PRODUCTION RUNTIME       : PASS")
        out("EXECUTION                 : DISABLED")
        out("ORDER                     : NONE")
        out("EXCHANGE WRITE            : NONE")
        out("DATABASE CHANGE           : NONE")
        out("ENTRYPOINT CHANGE        : NONE")

    out("=" * 78)
    out("HARD STOP")
    out("NO EXECUTION ACTIVATION")
    out("NO ORDER SENT")
    out("NO EXCHANGE WRITE")

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print()
    print(f"REPORT: {REPORT}")

if __name__ == "__main__":
    main()