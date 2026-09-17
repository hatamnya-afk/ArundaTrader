from pathlib import Path
import ast
import hashlib
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"
ENTRY = ROOT / "arunda_pipeline.py"

SNAPSHOT_ID = (
    "RS-e32e322f107e8c26f993cdf8cb72b4c0c6f95753b0e67d15404a2dad2c573841"
)

EXPECTED_ASSETS = {
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR"
}

EXECUTION_ENABLED = False


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return row is not None


def columns(conn, table):
    return {
        r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')
    }


def rows(conn, table):
    if not table_exists(conn, table):
        return []
    return conn.execute(f'SELECT * FROM "{table}"').fetchall()


def colmap(conn, table):
    cols = list(columns(conn, table))
    return cols


def first_existing(cols, names):
    for n in names:
        if n in cols:
            return n
    return None


def find_eligible_from_opportunity(conn):
    table_candidates = [
        "opportunity_candidates",
        "opportunity_signals",
        "market_opportunity",
    ]

    result = []

    for table in table_candidates:
        if not table_exists(conn, table):
            continue

        cols = columns(conn, table)
        rows_data = conn.execute(
            f'SELECT * FROM "{table}"'
        ).fetchall()

        for row in rows_data:
            d = dict(zip(colmap(conn, table), row))

            text = " ".join(
                str(v).upper()
                for v in d.values()
                if v is not None
            )

            eligible = False

            for key in (
                "eligible",
                "is_eligible",
                "opportunity_eligible",
            ):
                if key in d:
                    v = d[key]
                    if str(v).upper() in {"1", "TRUE", "YES"}:
                        eligible = True

            if "ELIGIBLE" in text and "NOT ELIGIBLE" not in text:
                eligible = True

            if eligible:
                result.append((table, d))

    return result


def locate_symbol(d):
    for k in (
        "symbol", "asset", "asset_symbol",
        "coin", "ticker", "market"
    ):
        if k in d and d[k]:
            return str(d[k]).upper()

    for v in d.values():
        if v is not None:
            s = str(v).upper()
            for asset in EXPECTED_ASSETS:
                if s == asset or s.startswith(asset + "/"):
                    return asset

    return None


def snapshot_rows(conn, table, symbol=None):
    if not table_exists(conn, table):
        return []

    cols = columns(conn, table)

    where = []
    params = []

    if symbol:
        c = first_existing(cols, ["symbol", "asset", "asset_symbol", "ticker"])
        if c:
            where.append(f'"{c}" = ?')
            params.append(symbol)

    # Current runtime identity candidates.
    identity_cols = [
        "snapshot_id",
        "runtime_snapshot_id",
        "run_snapshot_id",
    ]

    for c in identity_cols:
        if c in cols:
            where.append(f'"{c}" = ?')
            params.append(SNAPSHOT_ID)
            break

    sql = f'SELECT * FROM "{table}"'

    if where:
        sql += " WHERE " + " AND ".join(where)

    try:
        return conn.execute(sql, params).fetchall()
    except Exception:
        return []


def static_execution_scan():
    hits = []

    for p in ROOT.rglob("*.py"):
        if ".venv" in p.parts or "__pycache__" in p.parts:
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            if re.search(
                r'\bEXECUTION_ENABLED\s*=\s*True\b',
                line
            ):
                hits.append((str(p), i, line.strip()))

    return hits


def runtime_trace():
    print("RUNNING CURRENT PRODUCTION RUNTIME...")
    print("EXECUTION_ENABLED =", EXECUTION_ENABLED)

    proc = subprocess.run(
        [sys.executable, str(ENTRY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )

    print("\nRUNTIME EXIT CODE:", proc.returncode)

    print("\n--- STDOUT ---")
    print(proc.stdout)

    print("\n--- STDERR ---")
    print(proc.stderr)

    return proc.returncode, proc.stdout, proc.stderr


def extract_runtime_fields(text):
    patterns = {
        "eligible_count": [
            r"ELIGIBLE OPPORTUNITIES\s*:\s*(\d+)",
            r"Eligible\s*[:=]\s*(\d+)",
        ],
        "trade_ready": [
            r"Trade Ready\s*[:=]\s*(\d+)",
            r"TRADE_READY\s*[:=]\s*(\d+)",
        ],
        "order_intent": [
            r"Order Intent\s*[:=]\s*(\d+)",
            r"ORDER_INTENT\s*[:=]\s*(\d+)",
        ],
    }

    result = {}

    for key, pats in patterns.items():
        result[key] = None
        for p in pats:
            m = re.search(p, text, re.I)
            if m:
                result[key] = int(m.group(1))
                break

    return result


def main():
    print("=" * 78)
    print("ARUNDA TRADER — REAL EXECUTION READINESS RECONCILIATION v0.1")
    print("=" * 78)

    print("MODE                    : READ ONLY")
    print("RUNTIME SNAPSHOT        :", SNAPSHOT_ID)
    print("PROJECT ROOT            :", ROOT)
    print("DATABASE                :", DB)
    print("ENTRYPOINT              :", ENTRY)
    print("EXECUTION_ENABLED       :", EXECUTION_ENABLED)

    if not ROOT.exists():
        print("BLOCKER: PROJECT ROOT MISSING")
        return

    if not ENTRY.exists():
        print("BLOCKER: ENTRYPOINT MISSING")
        return

    if not DB.exists():
        print("BLOCKER: DATABASE MISSING")
        return

    before_db = sha256_file(DB)
    before_entry = sha256_file(ENTRY)

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    try:
        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print("\nDB INTEGRITY             :", integrity)

        # ------------------------------------------------------------
        # OPPORTUNITY
        # ------------------------------------------------------------

        eligible = find_eligible_from_opportunity(conn)

        unique_assets = []

        for table, d in eligible:
            asset = locate_symbol(d)
            if asset and asset not in unique_assets:
                unique_assets.append(asset)

        print("\nOPPORTUNITY ELIGIBLE ROWS:", len(eligible))
        print("ELIGIBLE ASSETS          :", unique_assets)

        if len(unique_assets) != 1:
            print("\nRESULT : BLOCKED")
            print("ROOT CAUSE: Eligible Opportunity is not exactly ONE.")
            return

        asset = unique_assets[0]

        print("\n" + "-" * 78)
        print("SINGLE ELIGIBLE ASSET:", asset)
        print("-" * 78)

        # ------------------------------------------------------------
        # READ CURRENT PRODUCTION TABLES
        # ------------------------------------------------------------

        chain_tables = [
            "opportunity_candidates",
            "opportunity_signals",
            "fusion_signals",
            "trade_decisions",
            "risk_decisions",
            "trade_gate_decisions",
        ]

        for table in chain_tables:
            print(f"\n[{table}]")

            if not table_exists(conn, table):
                print("  TABLE : MISSING")
                continue

            cols = columns(conn, table)
            print("  COLUMNS:", ", ".join(sorted(cols)))

            rs = snapshot_rows(conn, table, asset)

            print("  CURRENT-SCOPE ROWS:", len(rs))

            for r in rs[:20]:
                d = dict(zip(colmap(conn, table), r))

                selected = {}
                for k in d:
                    kl = k.lower()

                    if any(
                        x in kl for x in [
                            "symbol",
                            "asset",
                            "direction",
                            "side",
                            "score",
                            "decision",
                            "risk",
                            "gate",
                            "ready",
                            "eligible",
                            "entry",
                            "price",
                            "confidence",
                            "regime",
                            "snapshot",
                            "intent",
                            "status",
                            "reason",
                            "engine_version",
                        ]
                    ):
                        selected[k] = d[k]

                print(" ", selected)

        # ------------------------------------------------------------
        # RUNTIME
        # ------------------------------------------------------------

        runtime_exit, stdout, stderr = runtime_trace()

        fields = extract_runtime_fields(stdout)

        print("\n" + "=" * 78)
        print("RUNTIME RECONCILIATION")
        print("=" * 78)

        print("Eligible Opportunity Count :", fields["eligible_count"])
        print("Trade Ready                :", fields["trade_ready"])
        print("Order Intent               :", fields["order_intent"])

        # ------------------------------------------------------------
        # STATIC EXECUTION SAFETY
        # ------------------------------------------------------------

        true_hits = static_execution_scan()

        print("\nEXECUTION_ENABLED=True HITS:", len(true_hits))

        for path, line, code in true_hits:
            print(path)
            print(" LINE", line, ":", code)

        # ------------------------------------------------------------
        # POST FINGERPRINT
        # ------------------------------------------------------------

        after_db = sha256_file(DB)
        after_entry = sha256_file(ENTRY)

        print("\nDB SHA256 BEFORE :", before_db)
        print("DB SHA256 AFTER  :", after_db)

        print("\nENTRY SHA256 BEFORE:", before_entry)
        print("ENTRY SHA256 AFTER :", after_entry)

        print("\nDB CHANGED       :", before_db != after_db)
        print("ENTRYPOINT CHANGED:", before_entry != after_entry)

        # ------------------------------------------------------------
        # FINAL CLASSIFICATION
        # ------------------------------------------------------------

        blockers = []

        if runtime_exit != 0:
            blockers.append("Production runtime exit code != 0")

        if len(unique_assets) != 1:
            blockers.append("Eligible Opportunity != exactly 1")

        if fields["trade_ready"] != 1:
            blockers.append("Trade Ready != 1")

        if fields["order_intent"] != 1:
            blockers.append("Order Intent != 1")

        if true_hits:
            blockers.append(
                "EXECUTION_ENABLED=True found in repository; "
                "must be production-scope verified"
            )

        if after_entry != before_entry:
            blockers.append("Production entrypoint changed")

        print("\n" + "=" * 78)

        if blockers:
            print("RESULT : BLOCKED")
            print("\nBLOCKERS:")
            for b in blockers:
                print("-", b)
        else:
            print("RESULT : PASS — READINESS RECONCILED")

        print("=" * 78)
        print("NO ORDER")
        print("NO EXCHANGE WRITE")
        print("EXECUTION_ENABLED = FALSE")
        print("HARD STOP")

    finally:
        conn.close()


if __name__ == "__main__":
    main()