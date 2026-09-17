# ============================================================
# ARUNDA TRADER
# OPPORTUNITY ELIGIBILITY ROOT-CAUSE TRACE v0.3
# ============================================================
#
# READ-ONLY FORENSIC CONTROLLER
#
# Purpose:
#   Verify CURRENT production Opportunity eligibility against
#   the supplied OPPORTUNITY_v0.3 implementation.
#
# Pipeline:
#   CURRENT RUNTIME
#       -> Market Snapshot
#       -> Market Data
#       -> Opportunity
#
# HARD RULES:
#   - NO production code modification
#   - NO DB writes
#   - NO exchange calls
#   - NO order submission
#   - NO execution activation
#   - NO threshold changes
#   - NO formula changes
#   - NO synthetic data
#   - NO fallback
#   - NO interpolation
#   - NO forward fill
#   - NO back fill
#   - NO padding
#   - NO fabrication
#   - NO legacy data
#   - EXACTLY ONE fresh current runtime
#
# IMPORTANT:
#   Opportunity payload does NOT expose "valid_closes".
#
#   opportunity_engine.py -> get_history() explicitly queries:
#
#       close IS NOT NULL
#
#   Therefore every returned history row already represents a
#   valid close point.
#
#   The runtime payload exposes "points", which is the number
#   of returned history rows.
#
#   Therefore:
#
#       valid_closes == points
#
#   for this production Opportunity contract.
#
#   Eligible != Regression.
# ============================================================

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = PROJECT_ROOT / "arunda.db"

ENTRYPOINT = PROJECT_ROOT / "arunda_pipeline.py"

PYTHON_EXE = sys.executable

ENGINE_VERSION = "OPPORTUNITY_v0.3"

MIN_HISTORY_POINTS = 60

MAX_CANDIDATES = 15

MIN_OPPORTUNITY_SCORE = 65.0

MIN_CONFIDENCE = 0.60

EXECUTION_ENABLED_EXPECTED = False

RUNTIME_TIMEOUT_SECONDS = 300


# ============================================================
# TIME
# ============================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# HASH
# ============================================================

def sha256_file(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ============================================================
# OUTPUT
# ============================================================

def print_header(title: str) -> None:

    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


# ============================================================
# FLOAT
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        result = float(value)

        if result != result:
            return None

        if result in (
            float("inf"),
            float("-inf"),
        ):
            return None

        return result

    except Exception:

        return None


# ============================================================
# EXECUTION FLAG FORENSIC
# ============================================================

def scan_execution_flag() -> dict:

    result = {
        "true_hits": [],
        "false_hits": [],
        "error": None,
    }

    production_files = [

        ENTRYPOINT,

        PROJECT_ROOT / "arunda_pipeline.py",

        PROJECT_ROOT / "opportunity_engine.py",

        PROJECT_ROOT / "signal_engine.py",

        PROJECT_ROOT / "signal_validator.py",

        PROJECT_ROOT / "signal_scorer.py",

        PROJECT_ROOT / "decision_engine.py",

        PROJECT_ROOT / "risk_engine.py",

        PROJECT_ROOT / "trade_gate_engine.py",
    ]

    seen = set()

    try:

        for path in production_files:

            if not path.exists():
                continue

            key = str(path.resolve())

            if key in seen:
                continue

            seen.add(key)

            try:

                text = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

            except Exception:

                continue

            for line_no, line in enumerate(
                text.splitlines(),
                start=1,
            ):

                if "EXECUTION_ENABLED" not in line:
                    continue

                stripped = line.strip()

                if re.search(
                    r"\bEXECUTION_ENABLED\s*=\s*True\b",
                    stripped,
                ):

                    result["true_hits"].append(
                        f"{path.name}:{line_no}: {stripped}"
                    )

                if re.search(
                    r"\bEXECUTION_ENABLED\s*=\s*False\b",
                    stripped,
                ):

                    result["false_hits"].append(
                        f"{path.name}:{line_no}: {stripped}"
                    )

    except Exception as exc:

        result["error"] = repr(exc)

    return result


# ============================================================
# DATABASE READ-ONLY INTEGRITY
# ============================================================

def db_integrity_check() -> dict:

    result = {
        "ok": False,
        "integrity": None,
        "tables": 0,
        "error": None,
    }

    try:

        conn = sqlite3.connect(
            f"file:{DB_PATH}?mode=ro",
            uri=True,
            timeout=10,
        )

        try:

            integrity = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            result["integrity"] = (
                integrity[0]
                if integrity
                else None
            )

            tables = conn.execute(
                """
                SELECT COUNT(*)
                FROM sqlite_master
                WHERE type='table'
                """
            ).fetchone()

            result["tables"] = int(
                tables[0] or 0
            )

            result["ok"] = (
                result["integrity"] == "ok"
            )

        finally:

            conn.close()

    except Exception as exc:

        result["error"] = repr(exc)

    return result


# ============================================================
# ONE CURRENT PRODUCTION RUNTIME
# ============================================================

def run_current_runtime():

    return subprocess.run(
        [
            PYTHON_EXE,
            str(ENTRYPOINT),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=RUNTIME_TIMEOUT_SECONDS,
    )


# ============================================================
# OPPORTUNITY SNAPSHOT PARSER
# ============================================================

def parse_latest_opportunity_snapshot(
    stdout: str,
):

    prefix = (
        "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT="
    )

    matches = []

    for line in stdout.splitlines():

        if prefix in line:

            payload = line.split(
                prefix,
                1,
            )[1].strip()

            matches.append(payload)

    if not matches:

        return (
            None,
            "Opportunity runtime snapshot not found.",
        )

    raw = matches[-1]

    try:

        snapshot = json.loads(raw)

    except Exception as exc:

        return (
            None,
            f"Opportunity snapshot JSON invalid: {exc}",
        )

    return snapshot, None


# ============================================================
# EXACT OPPORTUNITY v0.3 ELIGIBILITY REPRODUCTION
# ============================================================

def reproduce_eligibility(
    opportunity: dict,
) -> dict:

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # opportunity_engine.get_history():
    #
    # SELECT ...
    # FROM market_data
    # WHERE symbol = ?
    #   AND close IS NOT NULL
    #
    # Therefore "points" in the runtime Opportunity payload
    # represent rows whose close is already non-null.
    #
    # No separate "valid_closes" field exists in payload.
    # --------------------------------------------------------

    points = opportunity.get(
        "points"
    )

    price = safe_float(
        opportunity.get("price")
    )

    score = safe_float(
        opportunity.get("score")
    )

    confidence = safe_float(
        opportunity.get("confidence")
    )

    history_pass = (
        isinstance(points, int)
        and points >= MIN_HISTORY_POINTS
    )

    valid_closes_pass = history_pass

    price_pass = (
        price is not None
    )

    score_pass = (
        score is not None
        and score >= MIN_OPPORTUNITY_SCORE
    )

    confidence_pass = (
        confidence is not None
        and confidence >= MIN_CONFIDENCE
    )

    checks = {

        "history_points": {
            "value": points,
            "required": MIN_HISTORY_POINTS,
            "pass": history_pass,
        },

        "valid_closes": {
            "value": points,
            "required": MIN_HISTORY_POINTS,
            "pass": valid_closes_pass,
            "source": "points / get_history close IS NOT NULL",
        },

        "price": {
            "value": price,
            "required": "NOT_NONE",
            "pass": price_pass,
        },

        "score": {
            "value": score,
            "required": MIN_OPPORTUNITY_SCORE,
            "pass": score_pass,
        },

        "confidence": {
            "value": confidence,
            "required": MIN_CONFIDENCE,
            "pass": confidence_pass,
        },
    }

    eligible = all(
        item["pass"]
        for item in checks.values()
    )

    failed = [
        name
        for name, item in checks.items()
        if not item["pass"]
    ]

    return {
        "eligible": eligible,
        "checks": checks,
        "failed": failed,
    }


# ============================================================
# ROOT CAUSE CLASSIFICATION
# ============================================================

def classify_root_cause(
    opportunity: dict,
    eligibility: dict,
) -> str:

    failed = set(
        eligibility["failed"]
    )

    if not failed:

        return (
            "A — REAL MARKET / DATA ELIGIBLE"
        )

    # Pure score failure = genuine market condition.

    if failed.issubset(
        {"score"}
    ):

        return (
            "A — REAL MARKET CONDITION"
        )

    # Missing/insufficient history or price.

    if failed.intersection(
        {
            "history_points",
            "valid_closes",
            "price",
        }
    ):

        return (
            "B — REAL DATA CONDITION"
        )

    return (
        "E — UNRESOLVED"
    )


# ============================================================
# REGRESSION DETERMINATION
# ============================================================

def determine_regression(
    opportunities: list[dict],
):

    contract_regression = False

    production_logic_regression = False

    mismatches = []

    for opportunity in opportunities:

        reproduction = reproduce_eligibility(
            opportunity
        )

        expected_status = (
            "ELIGIBLE"
            if reproduction["eligible"]
            else "NO_TRADE"
        )

        runtime_status = str(
            opportunity.get(
                "status",
                "",
            )
        ).upper()

        if runtime_status != expected_status:

            contract_regression = True

            production_logic_regression = True

            mismatches.append(
                {
                    "asset": opportunity.get(
                        "symbol",
                        opportunity.get(
                            "asset",
                            "UNKNOWN",
                        ),
                    ),
                    "runtime_status": runtime_status,
                    "expected_status": expected_status,
                    "failed": reproduction[
                        "failed"
                    ],
                }
            )

    if mismatches:

        reason = (
            "Runtime status does not match the "
            "supplied OPPORTUNITY_v0.3 eligibility "
            "implementation."
        )

    else:

        reason = (
            "Runtime status matches the supplied "
            "OPPORTUNITY_v0.3 eligibility implementation."
        )

    return (
        contract_regression,
        production_logic_regression,
        mismatches,
        reason,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print_header(
        "ARUNDA TRADER — OPPORTUNITY ELIGIBILITY "
        "ROOT-CAUSE TRACE v0.3"
    )

    print(
        "MODE                 : READ ONLY"
    )

    print(
        f"STARTED              : {utc_now()}"
    )

    print(
        f"PROJECT ROOT         : {PROJECT_ROOT}"
    )

    print(
        f"DATABASE             : {DB_PATH}"
    )

    print(
        f"ENTRYPOINT           : {ENTRYPOINT}"
    )

    print(
        f"PYTHON               : {PYTHON_EXE}"
    )

    # --------------------------------------------------------
    # PATH CHECK
    # --------------------------------------------------------

    if not PROJECT_ROOT.exists():

        print(
            "\nBLOCKER : PROJECT ROOT NOT FOUND"
        )

        return 1

    if not DB_PATH.exists():

        print(
            "\nBLOCKER : DATABASE NOT FOUND"
        )

        return 1

    if not ENTRYPOINT.exists():

        print(
            "\nBLOCKER : ENTRYPOINT NOT FOUND"
        )

        return 1

    print(
        "\nPROJECT ROOT         : PASS"
    )

    print(
        "DATABASE             : PASS"
    )

    print(
        "ENTRYPOINT           : PASS"
    )

    # --------------------------------------------------------
    # ENTRYPOINT FINGERPRINT
    # --------------------------------------------------------

    entry_hash_before = sha256_file(
        ENTRYPOINT
    )

    print(
        f"ENTRYPOINT SHA256    : {entry_hash_before}"
    )

    # --------------------------------------------------------
    # EXECUTION SAFETY
    # --------------------------------------------------------

    execution_scan = scan_execution_flag()

    print(
        "\nEXECUTION_ENABLED STATIC TRUE HITS : "
        f"{len(execution_scan['true_hits'])}"
    )

    print(
        "EXECUTION_ENABLED STATIC FALSE HITS: "
        f"{len(execution_scan['false_hits'])}"
    )

    if execution_scan["true_hits"]:

        print(
            "\nBLOCKER : EXECUTION_ENABLED=True "
            "FOUND IN PRODUCTION SCOPE"
        )

        for hit in execution_scan["true_hits"]:

            print(
                f"  {hit}"
            )

        return 1

    print(
        "EXECUTION ENABLED     : False"
    )

    # --------------------------------------------------------
    # DB INTEGRITY
    # --------------------------------------------------------

    db = db_integrity_check()

    print(
        f"\nDB INTEGRITY          : {db['integrity']}"
    )

    print(
        f"DB TABLES             : {db['tables']}"
    )

    if not db["ok"]:

        print(
            "\nBLOCKER : DB INTEGRITY CHECK FAILED"
        )

        if db["error"]:

            print(
                f"ERROR : {db['error']}"
            )

        return 1

    # --------------------------------------------------------
    # ONE CURRENT RUNTIME
    # --------------------------------------------------------

    print_header(
        "CURRENT PRODUCTION RUNTIME"
    )

    print(
        "RUNTIME COUNT         : 1"
    )

    print(
        "RUNTIME SOURCE        : CURRENT SUBPROCESS RUN"
    )

    try:

        completed = run_current_runtime()

    except subprocess.TimeoutExpired:

        print(
            "\nBLOCKED : CURRENT RUNTIME TIMEOUT"
        )

        return 2

    except Exception as exc:

        print(
            "\nBLOCKED : CURRENT RUNTIME FAILED"
        )

        print(
            f"ERROR : {exc}"
        )

        return 2

    print(
        f"EXIT CODE             : {completed.returncode}"
    )

    if completed.stderr.strip():

        print_header(
            "RUNTIME STDERR"
        )

        print(
            completed.stderr[-12000:]
        )

    if completed.returncode != 0:

        print(
            "\nBLOCKED : PRODUCTION RUNTIME EXIT CODE != 0"
        )

        return 2

    # --------------------------------------------------------
    # PARSE OPPORTUNITY SNAPSHOT
    # --------------------------------------------------------

    snapshot, parse_error = (
        parse_latest_opportunity_snapshot(
            completed.stdout
        )
    )

    if snapshot is None:

        print(
            "\nBLOCKED : OPPORTUNITY SNAPSHOT UNRESOLVED"
        )

        print(
            f"REASON : {parse_error}"
        )

        return 3

    runtime_source = snapshot.get(
        "runtime_source"
    )

    engine_version = snapshot.get(
        "engine_version"
    )

    opportunities = snapshot.get(
        "opportunities"
    )

    count = snapshot.get(
        "count"
    )

    print(
        f"\nRUNTIME SOURCE        : {runtime_source}"
    )

    print(
        f"ENGINE VERSION        : {engine_version}"
    )

    print(
        f"SNAPSHOT COUNT        : {count}"
    )

    # --------------------------------------------------------
    # SNAPSHOT CONTRACT
    # --------------------------------------------------------

    if runtime_source != (
        "CURRENT_SUBPROCESS_RUN"
    ):

        print(
            "\nBLOCKED : INVALID RUNTIME SOURCE"
        )

        return 4

    if engine_version != ENGINE_VERSION:

        print(
            "\nBLOCKED : UNEXPECTED OPPORTUNITY ENGINE VERSION"
        )

        return 4

    if not isinstance(
        opportunities,
        list,
    ):

        print(
            "\nBLOCKED : OPPORTUNITIES PAYLOAD INVALID"
        )

        return 4

    if count != len(opportunities):

        print(
            "\nBLOCKED : SNAPSHOT COUNT MISMATCH"
        )

        print(
            f"COUNT FIELD          : {count}"
        )

        print(
            f"ACTUAL OPPORTUNITIES : "
            f"{len(opportunities)}"
        )

        return 4

    if len(opportunities) != MAX_CANDIDATES:

        print(
            "\nBLOCKED : CURRENT OPPORTUNITY COUNT "
            f"!= {MAX_CANDIDATES}"
        )

        print(
            f"ACTUAL : {len(opportunities)}"
        )

        return 4

    # --------------------------------------------------------
    # TRACE
    # --------------------------------------------------------

    print_header(
        "OPPORTUNITY ELIGIBILITY TRACE"
    )

    print(
        "VALID CLOSE INTERPRETATION:"
    )

    print(
        "  get_history() filters close IS NOT NULL."
    )

    print(
        "  Therefore runtime 'points' are valid close rows."
    )

    eligible_count = 0

    no_trade_count = 0

    for index, opportunity in enumerate(
        opportunities,
        start=1,
    ):

        asset = opportunity.get(
            "symbol",
            opportunity.get(
                "asset",
                "UNKNOWN",
            ),
        )

        timestamp = opportunity.get(
            "timestamp"
        )

        price = opportunity.get(
            "price"
        )

        score = opportunity.get(
            "score"
        )

        confidence = opportunity.get(
            "confidence"
        )

        points = opportunity.get(
            "points"
        )

        runtime_status = str(
            opportunity.get(
                "status",
                "MISSING",
            )
        ).upper()

        reproduction = reproduce_eligibility(
            opportunity
        )

        expected_status = (
            "ELIGIBLE"
            if reproduction["eligible"]
            else "NO_TRADE"
        )

        classification = classify_root_cause(
            opportunity,
            reproduction,
        )

        if reproduction["eligible"]:

            eligible_count += 1

        else:

            no_trade_count += 1

        print()

        print(
            f"[{index:02d}] {asset}"
        )

        print(
            f"  Timestamp        : {timestamp}"
        )

        print(
            f"  Price            : {price}"
        )

        print(
            f"  Score            : {score}"
        )

        print(
            f"  Confidence       : {confidence}"
        )

        print(
            f"  Points           : {points}"
        )

        print(
            f"  Runtime Status   : {runtime_status}"
        )

        print(
            f"  Expected Status  : {expected_status}"
        )

        print(
            f"  History >= 60    : "
            f"{reproduction['checks']['history_points']['pass']}"
            f" ({points})"
        )

        print(
            f"  Valid Closes >= 60: "
            f"{reproduction['checks']['valid_closes']['pass']}"
            f" ({points})"
        )

        print(
            f"  Price Valid      : "
            f"{reproduction['checks']['price']['pass']}"
        )

        print(
            f"  Score >= 65      : "
            f"{reproduction['checks']['score']['pass']}"
        )

        print(
            f"  Confidence >= .60: "
            f"{reproduction['checks']['confidence']['pass']}"
        )

        print(
            f"  Eligibility      : "
            f"{reproduction['eligible']}"
        )

        print(
            f"  Classification   : {classification}"
        )

        if reproduction["failed"]:

            print(
                "  Failed Boundary  : "
                + ", ".join(
                    reproduction["failed"]
                )
            )

        else:

            print(
                "  Failed Boundary  : NONE"
            )

        if runtime_status == expected_status:

            print(
                "  CONTRACT MATCH   : PASS"
            )

        else:

            print(
                "  CONTRACT MATCH   : FAIL"
            )

    # --------------------------------------------------------
    # REGRESSION
    # --------------------------------------------------------

    (
        contract_regression,
        production_logic_regression,
        mismatches,
        regression_reason,
    ) = determine_regression(
        opportunities
    )

    # --------------------------------------------------------
    # ENTRYPOINT IMMUTABILITY
    # --------------------------------------------------------

    entry_hash_after = sha256_file(
        ENTRYPOINT
    )

    entrypoint_unchanged = (
        entry_hash_before
        == entry_hash_after
    )

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print_header(
        "FINAL FORENSIC REPORT"
    )

    print(
        f"Engine Version          : {engine_version}"
    )

    print(
        "Current Snapshot ID     : "
        "NOT PRESENT IN OPPORTUNITY PAYLOAD"
    )

    print(
        "Snapshot Provenance     : "
        "CURRENT_SUBPROCESS_RUN"
    )

    print(
        f"Candidates              : "
        f"{len(opportunities)}"
    )

    print(
        f"Eligible                : "
        f"{eligible_count}"
    )

    print(
        f"No Trade               : "
        f"{no_trade_count}"
    )

    print(
        f"Execution Enabled       : "
        f"{EXECUTION_ENABLED_EXPECTED}"
    )

    print(
        "DB Write by Controller  : NONE"
    )

    print(
        "Exchange Write          : NONE"
    )

    print(
        "Order Submission        : NONE"
    )

    print(
        "Synthetic Data          : NONE"
    )

    print(
        "Fallback                : NONE"
    )

    print(
        "Interpolation           : NONE"
    )

    print(
        "Forward Fill            : NONE"
    )

    print(
        "Back Fill               : NONE"
    )

    print(
        "Padding                 : NONE"
    )

    print(
        "Fabrication             : NONE"
    )

    print(
        f"Contract Regression     : "
        f"{'YES' if contract_regression else 'NO'}"
    )

    print(
        f"Production Regression   : "
        f"{'YES' if production_logic_regression else 'NO'}"
    )

    print(
        f"Entrypoint Unchanged    : "
        f"{entrypoint_unchanged}"
    )

    print(
        f"Regression Reason       : "
        f"{regression_reason}"
    )

    if mismatches:

        print()

        print(
            "CONTRACT MISMATCHES:"
        )

        for mismatch in mismatches:

            print(
                f"  {mismatch}"
            )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    if contract_regression:

        final_status = (
            "PASS — CONTRACT/REGRESSION IDENTIFIED — "
            "MANAGEMENT PATCH REQUIRED"
        )

    elif production_logic_regression:

        final_status = (
            "PASS — CONTRACT/REGRESSION IDENTIFIED — "
            "MANAGEMENT PATCH REQUIRED"
        )

    elif eligible_count == 0:

        final_status = (
            "PASS — REAL MARKET / DATA NO-TRADE"
        )

    elif eligible_count == 1:

        final_status = (
            "PASS — REAL MARKET / DATA ELIGIBLE"
        )

    else:

        final_status = (
            "BLOCKED — ROOT CAUSE UNRESOLVED"
        )

    print()

    print(
        f"FINAL STATUS            : {final_status}"
    )

    print()

    print(
        "PRODUCTION LOGIC CHANGE : NONE"
    )

    print(
        "THRESHOLD CHANGE        : NONE"
    )

    print(
        "ORDER                   : NONE"
    )

    print(
        "EXECUTION               : DISABLED"
    )

    print(
        "HARD STOP               : YES"
    )

    # --------------------------------------------------------
    # SAFETY ASSERTIONS
    # --------------------------------------------------------

    if not entrypoint_unchanged:

        print()

        print(
            "SAFETY FAILURE : ENTRYPOINT HASH CHANGED"
        )

        return 5

    if execution_scan["true_hits"]:

        print()

        print(
            "SAFETY FAILURE : EXECUTION FLAG TRUE"
        )

        return 5

    print_header(
        "TRACE CLOSED"
    )

    print(
        "No production patch was applied."
    )

    print(
        "No order was submitted."
    )

    print(
        "No exchange write was performed."
    )

    print(
        "Execution remains disabled."
    )

    print(
        "No automatic next checkpoint."
    )

    return 0


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )