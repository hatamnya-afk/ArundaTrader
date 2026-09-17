
from pathlib import Path
import hashlib
import re
import sqlite3
import subprocess
import sys

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

# HARD SAFETY
EXECUTION_ENABLED = False


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_current_runtime():
    print("\n" + "=" * 78)
    print("CURRENT PRODUCTION RUNTIME")
    print("=" * 78)

    proc = subprocess.run(
        [sys.executable, str(ENTRY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )

    print("EXIT CODE:", proc.returncode)

    print("\n--- STDOUT ---")
    print(proc.stdout)

    print("\n--- STDERR ---")
    print(proc.stderr)

    return proc


def extract_snapshot_id(text):
    # Prefer the exact requested snapshot.
    if SNAPSHOT_ID in text:
        return SNAPSHOT_ID

    patterns = [
        r"SNAPSHOT(?:_ID)?\s*[:=]\s*(RS-[A-Za-z0-9]+)",
        r"CURRENT(?:[-_ ]+RUNTIME)?(?:[-_ ]+SNAPSHOT)?\s*[:=]\s*(RS-[A-Za-z0-9]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1)

    return None


def extract_opportunity_block(text):
    """
    Extract only the Opportunity section from CURRENT RUNTIME stdout.
    No DB heuristic is used to determine eligibility.
    """

    lines = text.splitlines()

    start = None
    end = len(lines)

    opportunity_markers = [
        "OPPORTUNITY",
        "CURRENT-RUN OPPORTUNITY SNAPSHOT",
        "ELIGIBLE OPPORTUNITIES",
    ]

    downstream_markers = [
        "SIGNAL",
        "SCORE",
        "DECISION",
        "RISK",
        "TRADE GATE",
        "CP8",
        "CP9",
        "CP10",
        "CP11",
        "CP12",
    ]

    for i, line in enumerate(lines):
        upper = line.upper()

        if start is None and any(
            marker in upper for marker in opportunity_markers
        ):
            start = i
            continue

        if start is not None and i > start:
            if any(marker in upper for marker in downstream_markers):
                end = i
                break

    if start is None:
        return []

    return lines[start:end]


def extract_runtime_assets(text):
    """
    Only accept explicit production asset names.
    Numeric values, scores, prices, confidence values, etc.
    can NEVER become assets.
    """

    found = []

    # Strong forms:
    patterns = [
        r"\b(?:SYMBOL|ASSET|TICKER)\s*[:=]\s*([A-Z][A-Z0-9_-]{1,15})\b",
        r"\b([A-Z]{2,10})/(?:USDT|USD|IRT|IRT)\b",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text, re.I):
            candidate = m.group(1).upper()

            if candidate in EXPECTED_ASSETS and candidate not in found:
                found.append(candidate)

    # Explicit asset-list / candidate lines.
    for asset in EXPECTED_ASSETS:
        if re.search(
            rf"\b{re.escape(asset)}\b",
            text,
            re.I
        ):
            if asset not in found:
                found.append(asset)

    return found


def extract_metric(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return int(m.group(1))
    return None


def extract_runtime_metrics(text):
    return {
        "eligible_opportunities": extract_metric(
            text,
            [
                r"ELIGIBLE OPPORTUNITIES\s*:\s*(\d+)",
                r"ELIGIBLE\s*:\s*(\d+)",
            ],
        ),
        "current_snapshot": extract_metric(
            text,
            [
                r"CURRENT[-_ ]RUN OPPORTUNITY SNAPSHOT\s*:\s*(\d+)",
                r"OPPORTUNITY SNAPSHOT\s*:\s*(\d+)",
            ],
        ),
        "trade_ready": extract_metric(
            text,
            [
                r"TRADE READY\s*:\s*(\d+)",
                r"TRADE_READY\s*:\s*(\d+)",
            ],
        ),
        "order_intent": extract_metric(
            text,
            [
                r"ORDER INTENT\s*:\s*(\d+)",
                r"ORDER_INTENT\s*:\s*(\d+)",
            ],
        ),
    }


def find_asset_context(text, asset):
    """
    Return only lines containing the exact asset.
    Used for provenance inspection, not to invent state.
    """

    result = []

    for line in text.splitlines():
        if re.search(
            rf"\b{re.escape(asset)}\b",
            line,
            re.I
        ):
            result.append(line.strip())

    return result


def readonly_db_check():
    """
    Read-only DB inspection.
    No INSERT / UPDATE / DELETE / CREATE / ALTER.
    """

    conn = sqlite3.connect(
        f"file:{DB}?mode=ro",
        uri=True
    )

    try:
        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            )
        ]

        print("\nDB INTEGRITY:", integrity)
        print("TABLE COUNT :", len(tables))

        return integrity, tables

    finally:
        conn.close()


def static_execution_scan():
    hits = []

    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace"
            )
        except Exception:
            continue

        for lineno, line in enumerate(
            text.splitlines(), 1
        ):
            if re.search(
                r"\bEXECUTION_ENABLED\s*=\s*True\b",
                line
            ):
                hits.append(
                    (str(path), lineno, line.strip())
                )

    return hits


def main():

    print("=" * 78)
    print("ARUNDA TRADER — REAL EXECUTION READINESS RECONCILIATION v0.2")
    print("=" * 78)

    print("MODE                    : READ ONLY")
    print("RUNTIME SNAPSHOT        :", SNAPSHOT_ID)
    print("PROJECT ROOT            :", ROOT)
    print("DATABASE                :", DB)
    print("ENTRYPOINT              :", ENTRY)
    print("EXECUTION_ENABLED       :", EXECUTION_ENABLED)

    # ------------------------------------------------------------
    # PRECHECK
    # ------------------------------------------------------------

    if not ROOT.exists():
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: PROJECT ROOT MISSING")
        return

    if not ENTRY.exists():
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: PRODUCTION ENTRYPOINT MISSING")
        return

    if not DB.exists():
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: PRODUCTION DATABASE MISSING")
        return

    entry_before = sha256_file(ENTRY)

    integrity, tables = readonly_db_check()

    if integrity != "ok":
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: DATABASE INTEGRITY FAILURE")
        return

    # ------------------------------------------------------------
    # STATIC EXECUTION SAFETY
    # ------------------------------------------------------------

    execution_hits = static_execution_scan()

    production_execution_true = []

    for path, line, code in execution_hits:
        # Repository-wide text/report hits are not treated as
        # production execution state here.
        if Path(path).resolve() in {
            ENTRY.resolve(),
            (ROOT / "trade_gate_engine.py").resolve(),
        }:
            production_execution_true.append(
                (path, line, code)
            )

    if production_execution_true:
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: EXECUTION_ENABLED=True IN PRODUCTION SCOPE")
        for hit in production_execution_true:
            print(hit)
        return

    # ------------------------------------------------------------
    # ONE CURRENT RUNTIME ONLY
    # ------------------------------------------------------------

    proc = run_current_runtime()

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if proc.returncode != 0:
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: CURRENT PRODUCTION RUNTIME FAILED")
        return

    # ------------------------------------------------------------
    # SNAPSHOT ID
    # ------------------------------------------------------------

    runtime_snapshot = extract_snapshot_id(stdout)

    print("\nRUNTIME SNAPSHOT FOUND:", runtime_snapshot)

    if runtime_snapshot != SNAPSHOT_ID:
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: STALE OR MISMATCHED SNAPSHOT ID")
        return

    # ------------------------------------------------------------
    # OPPORTUNITY — RUNTIME NATIVE
    # ------------------------------------------------------------

    opportunity_block = extract_opportunity_block(stdout)

    opportunity_text = "\n".join(opportunity_block)

    print("\n" + "=" * 78)
    print("CURRENT RUNTIME OPPORTUNITY BLOCK")
    print("=" * 78)
    print(opportunity_text)

    metrics = extract_runtime_metrics(stdout)

    print("\nELIGIBLE OPPORTUNITIES:",
          metrics["eligible_opportunities"])

    print("CURRENT OPPORTUNITY SNAPSHOT:",
          metrics["current_snapshot"])

    # IMPORTANT:
    # We require runtime itself to report exactly one eligible opportunity.
    if metrics["eligible_opportunities"] != 1:
        print("\nRESULT : BLOCKED")
        print(
            "ROOT CAUSE: CURRENT RUNTIME DOES NOT REPORT "
            "EXACTLY ONE ELIGIBLE OPPORTUNITY"
        )
        return

    # ------------------------------------------------------------
    # ASSET RESOLUTION — STRICT
    # ------------------------------------------------------------

    runtime_assets = extract_runtime_assets(
        opportunity_text
    )

    print("\nRUNTIME-DERIVED ASSETS:", runtime_assets)

    if len(runtime_assets) != 1:
        print("\nRESULT : BLOCKED")
        print(
            "ROOT CAUSE: EXACTLY ONE RUNTIME-DERIVED "
            "PRODUCTION ASSET COULD NOT BE PROVEN"
        )
        return

    asset = runtime_assets[0]

    print("ELIGIBLE ASSET:", asset)

    # ------------------------------------------------------------
    # SAME ASSET THROUGH DOWNSTREAM RUNTIME
    # ------------------------------------------------------------

    print("\n" + "=" * 78)
    print("SAME-ASSET DOWNSTREAM RUNTIME TRACE")
    print("=" * 78)

    context = find_asset_context(
        stdout,
        asset
    )

    for line in context:
        print(line)

    if not context:
        print("NO DOWNSTREAM ASSET CONTEXT FOUND")
        print("\nRESULT : BLOCKED")
        print(
            "ROOT CAUSE: ASSET PROVEN IN OPPORTUNITY "
            "BUT NOT TRACEABLE IN CURRENT RUNTIME OUTPUT"
        )
        return

    # ------------------------------------------------------------
    # CURRENT RUNTIME COUNTS
    # ------------------------------------------------------------

    print("\n" + "=" * 78)
    print("CURRENT RUNTIME DOWNSTREAM COUNTS")
    print("=" * 78)

    print("Trade Ready :", metrics["trade_ready"])
    print("Order Intent:", metrics["order_intent"])

    # ------------------------------------------------------------
    # FINAL SAFETY CONDITIONS
    # ------------------------------------------------------------

    entry_after = sha256_file(ENTRY)

    print("\nENTRYPOINT SHA256 BEFORE:", entry_before)
    print("ENTRYPOINT SHA256 AFTER :", entry_after)

    if entry_before != entry_after:
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: PRODUCTION ENTRYPOINT CHANGED")
        return

    if metrics["trade_ready"] is None:
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: TRADE READY STATE UNRESOLVED")
        return

    if metrics["order_intent"] is None:
        print("\nRESULT : BLOCKED")
        print("ROOT CAUSE: ORDER INTENT STATE UNRESOLVED")
        return

    print("\n" + "=" * 78)

    if metrics["trade_ready"] == 1 and metrics["order_intent"] == 1:
        print("RESULT : PASS — READINESS RECONCILED")
        print("TRADE READY = 1")
        print("ORDER INTENT = 1")
        print("NO ORDER SENT")
        print("EXECUTION_ENABLED = FALSE")
        print("READY FOR MANAGEMENT AUTHORIZATION")
    else:
        print("RESULT : BLOCKED — REAL TRADE NOT ELIGIBLE")
        print(
            "TRADE READY =", metrics["trade_ready"]
        )
        print(
            "ORDER INTENT =", metrics["order_intent"]
        )
        print("NO ORDER SENT")
        print("EXECUTION_ENABLED = FALSE")

    print("=" * 78)
    print("DB WRITE              : NONE BY THIS RECONCILIATION")
    print("EXCHANGE WRITE        : NONE")
    print("ORDER SUBMISSION      : NONE")
    print("EXECUTION BYPASS      : NONE")
    print("SYNTHETIC/FALLBACK    : NONE")
    print("PRODUCTION LOGIC     : UNCHANGED")
    print("HARD STOP")


if __name__ == "__main__":
    main()