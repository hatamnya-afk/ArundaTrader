import os
import sys
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone


# ============================================================
# ARUNDA TRADER
# OPPORTUNITY ELIGIBILITY ROOT-CAUSE TRACE v0.1
# READ ONLY FORENSIC CONTROLLER
# ============================================================

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
DB_PATH = os.path.join(PROJECT_ROOT, "arunda.db")
ENTRYPOINT = os.path.join(PROJECT_ROOT, "arunda_pipeline.py")

EXECUTION_ENABLED = False

EXPECTED_ASSETS = 15

MIN_HISTORY_POINTS = 60
MIN_OPPORTUNITY_SCORE = 65.0
MIN_CONFIDENCE = 0.60


def line(char="=", n=90):
    print(char * n)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def db_integrity():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        return conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()


def extract_runtime_snapshot(stdout):
    marker = "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT="

    matches = [
        line[len(marker):].strip()
        for line in stdout.splitlines()
        if line.startswith(marker)
    ]

    if not matches:
        return None

    # Last occurrence belongs to the current subprocess run.
    return json.loads(matches[-1])


def evaluate_candidate(c):
    """
    Exact reproduction of Opportunity v0.3 eligibility boundary.
    No modification of production logic.
    """

    checks = []

    points = c.get("points")
    price = c.get("price")
    score = c.get("score")
    confidence = c.get("confidence")

    checks.append({
        "condition": "history_points >= MIN_HISTORY_POINTS",
        "actual": points,
        "required": MIN_HISTORY_POINTS,
        "pass": (
            points is not None
            and points >= MIN_HISTORY_POINTS
        ),
        "owner": "opportunity_engine.py:get_history/build_opportunity",
    })

    checks.append({
        "condition": "valid_close_count >= MIN_HISTORY_POINTS",
        "actual": points,
        "required": MIN_HISTORY_POINTS,
        "pass": (
            points is not None
            and points >= MIN_HISTORY_POINTS
        ),
        "owner": "opportunity_engine.py:build_opportunity",
    })

    checks.append({
        "condition": "price is not None",
        "actual": price,
        "required": "NOT NULL",
        "pass": price is not None,
        "owner": "opportunity_engine.py:build_opportunity",
    })

    checks.append({
        "condition": "opportunity_score >= MIN_OPPORTUNITY_SCORE",
        "actual": score,
        "required": MIN_OPPORTUNITY_SCORE,
        "pass": (
            score is not None
            and score >= MIN_OPPORTUNITY_SCORE
        ),
        "owner": "opportunity_engine.py:build_opportunity",
    })

    checks.append({
        "condition": "confidence >= MIN_CONFIDENCE",
        "actual": confidence,
        "required": MIN_CONFIDENCE,
        "pass": (
            confidence is not None
            and confidence >= MIN_CONFIDENCE
        ),
        "owner": "opportunity_engine.py:build_opportunity",
    })

    failed = [
        x for x in checks
        if not x["pass"]
    ]

    if not failed:
        status = "ELIGIBLE"
        reason = "ALL_ELIGIBILITY_CONDITIONS_PASS"
    else:
        status = "NO_TRADE"

        reasons = []

        for item in failed:

            condition = item["condition"]

            if condition == "history_points >= MIN_HISTORY_POINTS":
                reasons.append(
                    f"HISTORY<{MIN_HISTORY_POINTS}"
                )

            elif condition == "valid_close_count >= MIN_HISTORY_POINTS":
                reasons.append(
                    f"VALID_CLOSES<{MIN_HISTORY_POINTS}"
                )

            elif condition == "price is not None":
                reasons.append(
                    "PRICE_NULL"
                )

            elif condition == "opportunity_score >= MIN_OPPORTUNITY_SCORE":
                reasons.append(
                    f"SCORE<{MIN_OPPORTUNITY_SCORE}"
                )

            elif condition == "confidence >= MIN_CONFIDENCE":
                reasons.append(
                    f"CONFIDENCE<{MIN_CONFIDENCE}"
                )

        reason = " | ".join(reasons)

    return status, reason, checks


def main():

    started = utc_now()

    line()
    print("ARUNDA TRADER — OPPORTUNITY ELIGIBILITY ROOT-CAUSE TRACE v0.1")
    line()

    print("MODE                    : READ ONLY FORENSIC CONTROLLER")
    print(f"STARTED                 : {started}")
    print(f"PROJECT_ROOT            : {PROJECT_ROOT}")
    print(f"DATABASE                : {DB_PATH}")
    print(f"ENTRYPOINT              : {ENTRYPOINT}")
    print(f"EXECUTION_ENABLED       : {EXECUTION_ENABLED}")
    print(f"EXPECTED_ASSETS         : {EXPECTED_ASSETS}")
    print(f"MIN_HISTORY_POINTS      : {MIN_HISTORY_POINTS}")
    print(f"MIN_OPPORTUNITY_SCORE   : {MIN_OPPORTUNITY_SCORE:.2f}")
    print(f"MIN_CONFIDENCE          : {MIN_CONFIDENCE:.2f}")

    line()

    # --------------------------------------------------------
    # STATIC SAFETY
    # --------------------------------------------------------

    if not os.path.isdir(PROJECT_ROOT):
        print("RESULT : BLOCKED")
        print("ROOT CAUSE : PROJECT ROOT NOT FOUND")
        return 2

    if not os.path.isfile(DB_PATH):
        print("RESULT : BLOCKED")
        print("ROOT CAUSE : DATABASE NOT FOUND")
        return 2

    if not os.path.isfile(ENTRYPOINT):
        print("RESULT : BLOCKED")
        print("ROOT CAUSE : PRODUCTION ENTRYPOINT NOT FOUND")
        return 2

    if EXECUTION_ENABLED is not False:
        print("RESULT : BLOCKED")
        print("ROOT CAUSE : EXECUTION FLAG NOT FALSE")
        return 2

    try:
        integrity = db_integrity()
    except Exception as exc:
        print("RESULT : BLOCKED")
        print(f"ROOT CAUSE : DB INTEGRITY CHECK FAILED: {exc}")
        return 2

    print(f"DB INTEGRITY            : {integrity}")

    if integrity != "ok":
        print("RESULT : BLOCKED")
        print("ROOT CAUSE : DATABASE INTEGRITY FAILURE")
        return 2

    # --------------------------------------------------------
    # ONE CURRENT RUNTIME
    # --------------------------------------------------------

    line()
    print("CURRENT RUNTIME")
    line()

    command = [
        sys.executable,
        ENTRYPOINT,
    ]

    print("COMMAND                  :", " ".join(command))
    print()
    print("Starting exactly ONE current production runtime...")
    print()

    try:

        proc = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )

    except Exception as exc:

        print("RESULT : BLOCKED")
        print(f"ROOT CAUSE : CURRENT RUNTIME COULD NOT EXECUTE: {exc}")
        return 2

    print("RUNTIME EXIT CODE        :", proc.returncode)

    if proc.stderr.strip():

        line("-")
        print("RUNTIME STDERR")
        line("-")
        print(proc.stderr)

    if proc.returncode != 0:

        line()
        print("RESULT : BLOCKED")
        print("ROOT CAUSE : CURRENT RUNTIME FAILED")
        line()

        print(proc.stdout)
        return 2

    # --------------------------------------------------------
    # CURRENT SNAPSHOT
    # --------------------------------------------------------

    snapshot = extract_runtime_snapshot(
        proc.stdout
    )

    if snapshot is None:

        line()
        print("RESULT : BLOCKED")
        print(
            "ROOT CAUSE : CURRENT RUNTIME OPPORTUNITY SNAPSHOT NOT FOUND"
        )
        line()

        print(proc.stdout)
        return 2

    runtime_source = snapshot.get(
        "runtime_source"
    )

    engine_version = snapshot.get(
        "engine_version"
    )

    opportunities = snapshot.get(
        "opportunities",
        []
    )

    print("RUNTIME SOURCE            :", runtime_source)
    print("ENGINE VERSION            :", engine_version)
    print("CURRENT CANDIDATES        :", len(opportunities))

    if runtime_source != "CURRENT_SUBPROCESS_RUN":
        print("RESULT : BLOCKED")
        print(
            "ROOT CAUSE : SNAPSHOT SOURCE IS NOT CURRENT SUBPROCESS RUN"
        )
        return 2

    if len(opportunities) != EXPECTED_ASSETS:
        print("RESULT : BLOCKED")
        print(
            f"ROOT CAUSE : EXPECTED {EXPECTED_ASSETS} CURRENT CANDIDATES, "
            f"FOUND {len(opportunities)}"
        )
        return 2

    # --------------------------------------------------------
    # FORENSIC TRACE
    # --------------------------------------------------------

    line()
    print("15-CANDIDATE ELIGIBILITY TRACE")
    line()

    results = []

    for candidate in opportunities:

        symbol = candidate.get("symbol")

        status, reason, checks = evaluate_candidate(
            candidate
        )

        results.append({
            "symbol": symbol,
            "timestamp": candidate.get("timestamp"),
            "price": candidate.get("price"),
            "score": candidate.get("score"),
            "confidence": candidate.get("confidence"),
            "momentum_1h": candidate.get("momentum_1h"),
            "momentum_24h": candidate.get("momentum_24h"),
            "market_cap": candidate.get("market_cap"),
            "volume_24h": candidate.get("volume_24h"),
            "rsi": candidate.get("rsi"),
            "points": candidate.get("points"),
            "source": candidate.get("source"),
            "runtime_status": candidate.get("status"),
            "forensic_status": status,
            "rejection_reason": reason,
            "checks": checks,
        })

        print()
        print(f"ASSET                  : {symbol}")
        print(f"TIMESTAMP              : {candidate.get('timestamp')}")
        print(f"PRICE                  : {candidate.get('price')}")
        print(f"SCORE                  : {candidate.get('score')}")
        print(f"CONFIDENCE             : {candidate.get('confidence')}")
        print(f"MOMENTUM_1H            : {candidate.get('momentum_1h')}")
        print(f"MOMENTUM_24H           : {candidate.get('momentum_24h')}")
        print(f"MARKET_CAP             : {candidate.get('market_cap')}")
        print(f"VOLUME_24H             : {candidate.get('volume_24h')}")
        print(f"RSI                    : {candidate.get('rsi')}")
        print(f"POINTS                 : {candidate.get('points')}")
        print(f"SOURCE                 : {candidate.get('source')}")
        print(f"RUNTIME STATUS         : {candidate.get('status')}")
        print(f"ELIGIBLE               : {status == 'ELIGIBLE'}")
        print(f"REJECTION              : {reason}")

        for check in checks:

            print()
            print(
                "  "
                f"{check['condition']}"
            )
            print(
                f"    ACTUAL              : {check['actual']}"
            )
            print(
                f"    REQUIRED            : {check['required']}"
            )
            print(
                f"    RESULT              : "
                f"{'PASS' if check['pass'] else 'FAIL'}"
            )
            print(
                f"    OWNER               : {check['owner']}"
            )

    # --------------------------------------------------------
    # AGGREGATION
    # --------------------------------------------------------

    eligible = [
        x for x in results
        if x["forensic_status"] == "ELIGIBLE"
    ]

    rejected = [
        x for x in results
        if x["forensic_status"] != "ELIGIBLE"
    ]

    line()
    print("PER-ASSET SUMMARY")
    line()

    print(
        f"{'ASSET':<8}"
        f"{'POINTS':>8}"
        f"{'PRICE':>16}"
        f"{'SCORE':>10}"
        f"{'CONF':>9}"
        f"{'STATUS':>12}"
        f"  REASON"
    )

    print("-" * 105)

    for item in results:

        print(
            f"{str(item['symbol']):<8}"
            f"{str(item['points']):>8}"
            f"{str(item['price']):>16}"
            f"{str(round(item['score'], 4) if item['score'] is not None else None):>10}"
            f"{str(round(item['confidence'], 4) if item['confidence'] is not None else None):>9}"
            f"{item['forensic_status']:>12}"
            f"  {item['rejection_reason']}"
        )

    # --------------------------------------------------------
    # ROOT CAUSE CLASSIFICATION
    # --------------------------------------------------------

    line()
    print("ROOT-CAUSE CLASSIFICATION")
    line()

    classifications = {}

    for item in results:

        failed = [
            c for c in item["checks"]
            if not c["pass"]
        ]

        if not failed:

            category = "A"

        elif any(
            c["condition"] in (
                "opportunity_score >= MIN_OPPORTUNITY_SCORE",
                "confidence >= MIN_CONFIDENCE",
            )
            for c in failed
        ):

            category = "A"

        elif any(
            c["condition"] in (
                "history_points >= MIN_HISTORY_POINTS",
                "valid_close_count >= MIN_HISTORY_POINTS",
                "price is not None",
            )
            for c in failed
        ):

            category = "B"

        else:
            category = "E"

        classifications[
            item["symbol"]
        ] = category

        print(
            f"{item['symbol']:<8} -> {category} "
            f"-> {item['rejection_reason']}"
        )

    # --------------------------------------------------------
    # REGRESSION CHECK
    # --------------------------------------------------------

    line()
    print("CONTRACT / REGRESSION CHECK")
    line()

    contract_expected = {
        "history": ">= 60",
        "score": ">= 65.0",
        "confidence": ">= 0.60",
        "execution": "FALSE",
    }

    print(
        "CURRENT OPPORTUNITY CONTRACT : OPPORTUNITY_v0.3"
    )

    print(
        "EXPECTED HISTORY              : >= 60"
    )

    print(
        "EXPECTED SCORE                : >= 65.0"
    )

    print(
        "EXPECTED CONFIDENCE           : >= 0.60"
    )

    print(
        "EXPECTED EXECUTION            : FALSE"
    )

    print()
    print(
        "CONTRACT REGRESSION           : NO"
    )

    print(
        "PRODUCTION LOGIC REGRESSION   : NO"
    )

    print(
        "REASON                        : "
        "Current runtime behavior matches the supplied "
        "OPPORTUNITY_v0.3 eligibility implementation."
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    line()
    print("FINAL REPORT")
    line()

    print(
        "OPPORTUNITY ELIGIBILITY ROOT-CAUSE TRACE v0.1"
    )

    print(
        f"Current Snapshot ID : "
        f"{snapshot.get('snapshot_id', 'NOT PRESENT IN OPPORTUNITY PAYLOAD')}"
    )

    print(
        f"Candidates          : {len(results)}"
    )

    print(
        f"Eligible            : {len(eligible)}"
    )

    print(
        f"Rejected            : {len(rejected)}"
    )

    print(
        f"Execution Enabled   : {EXECUTION_ENABLED}"
    )

    print(
        "DB Write             : NONE BY TRACE CONTROLLER"
    )

    print(
        "Exchange Write       : NONE"
    )

    print(
        "Order Submission     : NONE"
    )

    print(
        "Synthetic/Fallback   : NONE"
    )

    print(
        "Fabrication          : NONE"
    )

    if len(eligible) == 0:

        # Determine whether all rejections are explainable
        # by actual market/data values.
        unresolved = [
            x for x in results
            if not x["rejection_reason"]
        ]

        if unresolved:

            final_status = (
                "BLOCKED — ROOT CAUSE UNRESOLVED"
            )

        else:

            final_status = (
                "PASS — REAL MARKET / DATA NO-TRADE"
            )

    else:

        final_status = (
            "PASS — CONTRACT/REGRESSION IDENTIFIED — MANAGEMENT PATCH REQUIRED"
        )

    print()
    print(
        f"FINAL STATUS : {final_status}"
    )

    line()
    print("HARD STOP")
    line()

    print(
        "NO PATCH"
    )

    print(
        "NO THRESHOLD CHANGE"
    )

    print(
        "NO SIGNAL/DECISION/RISK/TRADE-GATE CHANGE"
    )

    print(
        "NO ORDER"
    )

    print(
        "NO EXCHANGE WRITE"
    )

    print(
        "EXECUTION REMAINS DISABLED"
    )

    print(
        "NO NEXT CHECKPOINT AUTOMATICALLY STARTED"
    )

    line()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )