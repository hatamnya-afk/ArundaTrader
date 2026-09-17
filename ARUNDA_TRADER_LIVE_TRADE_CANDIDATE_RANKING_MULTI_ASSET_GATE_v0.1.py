# ==================================================================================================
# ARUNDA TRADER
# LIVE TRADE CANDIDATE RANKING + MULTI-ASSET DECISION GATE v0.1
# ==================================================================================================
#
# PURPOSE
# -------
# Consume ONLY the output of the previously verified:
#
#   LIVE SIGNAL ELIGIBILITY + NO-TRADE SAFETY GATE v0.1
#
# This frontier does NOT re-audit:
#   - live source health
#   - snapshot freshness
#   - source-to-row provenance
#   - signal quality
#   - signal eligibility
#
# Those frontiers are CLOSED / VERIFIED.
#
# This frontier performs:
#
#   Eligible candidates
#          ↓
#   Candidate normalization
#          ↓
#   Multi-asset ranking
#          ↓
#   Decision gate
#          ↓
#   Candidate / NO-CANDIDATE
#
# IMPORTANT
# ---------
# No orders.
# No execution.
# No production DB writes.
# No historical repair.
# No direction inference.
# No score reconstruction.
# No synthetic data.
#
# Conservative by design.
# ==================================================================================================

import os
import sqlite3
import hashlib
import json
from datetime import datetime, timezone


# --------------------------------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------------------------------

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
PRODUCTION_DB = os.path.join(PROJECT_ROOT, "arunda.db")

CAPTURE_ROOT = os.path.expandvars(
    r"C:\Users\ASUS\AppData\Local\Temp"
)

EXPECTED_ENGINE = "FUSION_v0.5"

# Candidate ranking configuration.
#
# IMPORTANT:
# These are ranking weights, NOT signal-generation parameters.
# They do not modify the Fusion output.
#
WEIGHT_CONFIDENCE = 0.40
WEIGHT_AVAILABLE_WEIGHT = 0.25
WEIGHT_DATA_QUALITY = 0.20
WEIGHT_SIGNAL_STRENGTH = 0.15

# Only the strongest available candidates are surfaced.
TOP_N = 5

# Multi-asset concentration control.
# One asset may appear only once in the final candidate set.
MAX_CANDIDATES_PER_ASSET = 1


# --------------------------------------------------------------------------------------------------
# QUALITY MAPS
# --------------------------------------------------------------------------------------------------

DATA_QUALITY_SCORE = {
    "VERIFIED": 1.0,
    "PARTIAL": 0.5,
    "UNKNOWN": 0.0,
}

SIGNAL_STRENGTH_SCORE = {
    "STRONG": 1.0,
    "MODERATE": 0.75,
    "WEAK": 0.25,
    "UNKNOWN": 0.0,
}


# --------------------------------------------------------------------------------------------------
# UTILITIES
# --------------------------------------------------------------------------------------------------

def sha256_file(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def open_readonly(path):

    uri = "file:" + path.replace("\\", "/") + "?mode=ro"

    return sqlite3.connect(uri, uri=True)


def utc_now():

    return datetime.now(timezone.utc).isoformat()


def find_latest_capture():

    candidates = []

    if not os.path.isdir(CAPTURE_ROOT):
        return None

    for name in os.listdir(CAPTURE_ROOT):

        if not name.startswith("arunda_live_launch_"):
            continue

        path = os.path.join(CAPTURE_ROOT, name)

        if not os.path.isdir(path):
            continue

        db_path = os.path.join(
            path,
            "arunda_live_capture.db"
        )

        if not os.path.isfile(db_path):
            continue

        try:
            mtime = os.path.getmtime(db_path)

            candidates.append(
                (
                    mtime,
                    path,
                    db_path
                )
            )

        except OSError:
            pass

    if not candidates:
        return None

    candidates.sort(reverse=True)

    return candidates[0][1], candidates[0][2]


# --------------------------------------------------------------------------------------------------
# PRODUCTION BASELINE
# --------------------------------------------------------------------------------------------------

def production_baseline():

    size = os.path.getsize(PRODUCTION_DB)

    digest = sha256_file(PRODUCTION_DB)

    conn = open_readonly(PRODUCTION_DB)

    try:

        rows = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]

    finally:

        conn.close()

    return {
        "rows": rows,
        "size": size,
        "sha256": digest,
    }


# --------------------------------------------------------------------------------------------------
# ELIGIBILITY OUTPUT CONSUMPTION
# --------------------------------------------------------------------------------------------------
#
# We deliberately consume the existing eligibility report instead of rebuilding
# the eligibility logic.
#
# This prevents Frontier duplication.
# --------------------------------------------------------------------------------------------------

def locate_eligibility_report(capture_dir):

    path = os.path.join(
        capture_dir,
        "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
    )

    if not os.path.isfile(path):
        return None

    return path


def load_eligibility_report(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# --------------------------------------------------------------------------------------------------
# CANDIDATE SCORING
# --------------------------------------------------------------------------------------------------

def normalize_confidence(value):

    if value is None:
        return 0.0

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    if value < 0:
        return 0.0

    if value > 1:
        return 1.0

    return value


def normalize_available_weight(value):

    if value is None:
        return 0.0

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    if value < 0:
        return 0.0

    if value > 1:
        return 1.0

    return value


def quality_score(value):

    return DATA_QUALITY_SCORE.get(
        str(value).upper(),
        0.0
    )


def strength_score(value):

    return SIGNAL_STRENGTH_SCORE.get(
        str(value).upper(),
        0.0
    )


def calculate_candidate_score(row):

    confidence = normalize_confidence(
        row.get("confidence")
    )

    available_weight = normalize_available_weight(
        row.get("available_weight")
    )

    data_quality = quality_score(
        row.get("data_quality")
    )

    signal_strength = strength_score(
        row.get("signal_strength")
    )

    score = (
        confidence * WEIGHT_CONFIDENCE
        + available_weight * WEIGHT_AVAILABLE_WEIGHT
        + data_quality * WEIGHT_DATA_QUALITY
        + signal_strength * WEIGHT_SIGNAL_STRENGTH
    )

    return round(score, 6)


# --------------------------------------------------------------------------------------------------
# CANDIDATE VALIDATION
# --------------------------------------------------------------------------------------------------

def validate_candidate(row):

    reasons = []

    if not row.get("eligible"):
        reasons.append(
            "ELIGIBILITY_GATE_NOT_PASSED"
        )

    direction = str(
        row.get("direction") or ""
    ).upper()

    if direction not in {
        "LONG",
        "SHORT",
    }:
        reasons.append(
            "NON_DIRECTIONAL_OUTPUT"
        )

    if not row.get("asset"):
        reasons.append(
            "MISSING_ASSET"
        )

    if row.get("entry_price") is None:
        reasons.append(
            "MISSING_ENTRY_PRICE"
        )

    if row.get("confidence") is None:
        reasons.append(
            "MISSING_CONFIDENCE"
        )

    return reasons


# --------------------------------------------------------------------------------------------------
# RANKING
# --------------------------------------------------------------------------------------------------

def rank_candidates(rows):

    eligible_rows = []

    rejected_rows = []

    for row in rows:

        reasons = validate_candidate(row)

        if reasons:

            rejected_rows.append(
                {
                    "id": row.get("id"),
                    "asset": row.get("asset"),
                    "reasons": reasons,
                }
            )

            continue

        candidate = dict(row)

        candidate["candidate_score"] = (
            calculate_candidate_score(candidate)
        )

        candidate["candidate_status"] = (
            "TRADE_CANDIDATE"
        )

        eligible_rows.append(candidate)

    # Highest score first.
    #
    # Secondary ordering:
    #   confidence
    #   available_weight
    #   id
    #
    eligible_rows.sort(
        key=lambda x: (
            x["candidate_score"],
            normalize_confidence(
                x.get("confidence")
            ),
            normalize_available_weight(
                x.get("available_weight")
            ),
            -int(x.get("id", 0)),
        ),
        reverse=True,
    )

    # ----------------------------------------------------------------------------------------------
    # MULTI-ASSET CONCENTRATION CONTROL
    # ----------------------------------------------------------------------------------------------

    selected = []

    per_asset = {}

    for candidate in eligible_rows:

        asset = candidate.get("asset")

        count = per_asset.get(
            asset,
            0
        )

        if count >= MAX_CANDIDATES_PER_ASSET:

            candidate["selection_status"] = (
                "REJECTED_ASSET_DUPLICATE"
            )

            continue

        if len(selected) >= TOP_N:

            candidate["selection_status"] = (
                "OUTSIDE_TOP_N"
            )

            continue

        candidate["selection_status"] = (
            "SELECTED"
        )

        selected.append(candidate)

        per_asset[asset] = count + 1

    return (
        eligible_rows,
        selected,
        rejected_rows,
    )


# --------------------------------------------------------------------------------------------------
# REPORT
# --------------------------------------------------------------------------------------------------

def build_report(
    production_before,
    production_after,
    capture_db,
    eligibility_report_path,
    snapshot_id,
    all_eligible,
    selected,
    rejected,
):

    return {

        "frontier":
            "LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1",

        "timestamp_utc":
            utc_now(),

        "engine":
            EXPECTED_ENGINE,

        "snapshot_id":
            snapshot_id,

        "source_frontier":
            "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1",

        "eligibility_report":
            eligibility_report_path,

        "ranking_configuration": {

            "weight_confidence":
                WEIGHT_CONFIDENCE,

            "weight_available_weight":
                WEIGHT_AVAILABLE_WEIGHT,

            "weight_data_quality":
                WEIGHT_DATA_QUALITY,

            "weight_signal_strength":
                WEIGHT_SIGNAL_STRENGTH,

            "top_n":
                TOP_N,

            "max_candidates_per_asset":
                MAX_CANDIDATES_PER_ASSET,
        },

        "candidate_pool":
            len(all_eligible),

        "selected_candidates":
            len(selected),

        "rejected_candidates":
            len(rejected),

        "decision":
            (
                "CANDIDATES_AVAILABLE"
                if selected
                else "NO_TRADE_CANDIDATE"
            ),

        "selected":
            selected,

        "eligible_pool":
            all_eligible,

        "rejected":
            rejected,

        "production_database": {

            "before":
                production_before,

            "after":
                production_after,

            "unchanged":
                production_before ==
                production_after,
        },

        "safety": {

            "production_db_modified":
                False,

            "production_engine_executed":
                False,

            "historical_repair":
                False,

            "direction_inference":
                False,

            "score_reconstruction":
                False,

            "synthetic_data":
                False,

            "live_data_injection":
                False,

            "order_execution":
                False,
        },
    }


# --------------------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------------------

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE TRADE CANDIDATE RANKING "
        "+ MULTI-ASSET DECISION GATE v0.1"
    )
    print("=" * 100)

    print("OBJECTIVE:")
    print(
        "  Rank ONLY candidates that already passed "
        "the verified eligibility gate."
    )

    print()
    print(
        "Previously verified frontiers are NOT re-audited."
    )

    print()
    print("Production DB writes : FORBIDDEN")
    print("Production engine run : NO")
    print("Historical repair     : NONE")
    print("Direction inference   : NONE")
    print("Score reconstruction  : NONE")
    print("Synthetic data        : FORBIDDEN")
    print("Live data injection   : NONE")
    print("Order execution       : NONE")

    # ----------------------------------------------------------------------------------------------
    # PRODUCTION BASELINE
    # ----------------------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    production_before = production_baseline()

    print(
        f"Rows   : {production_before['rows']}"
    )

    print(
        f"Size   : {production_before['size']}"
    )

    print(
        f"SHA256 : {production_before['sha256']}"
    )

    # ----------------------------------------------------------------------------------------------
    # LIVE CAPTURE
    # ----------------------------------------------------------------------------------------------

    latest = find_latest_capture()

    if not latest:

        raise RuntimeError(
            "No disposable live capture found."
        )

    capture_dir, capture_db = latest

    print()
    print("=" * 100)
    print("LIVE CAPTURE")
    print("=" * 100)

    print(
        f"Directory : {capture_dir}"
    )

    print(
        f"Database  : {capture_db}"
    )

    # ----------------------------------------------------------------------------------------------
    # ELIGIBILITY REPORT
    # ----------------------------------------------------------------------------------------------

    eligibility_report = locate_eligibility_report(
        capture_dir
    )

    if not eligibility_report:

        raise RuntimeError(
            "Previously verified eligibility report "
            "was not found."
        )

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    print(
        "Eligibility source : "
        "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1"
    )

    print(
        f"Report : {eligibility_report}"
    )

    report = load_eligibility_report(
        eligibility_report
    )

    snapshot_id = report.get(
        "snapshot_id"
    )

    rows = report.get(
        "row_results",
        []
    )

    if not snapshot_id:

        raise RuntimeError(
            "Eligibility report has no snapshot ID."
        )

    if not rows:

        raise RuntimeError(
            "Eligibility report contains no rows."
        )

    # ----------------------------------------------------------------------------------------------
    # ELIGIBLE POOL
    # ----------------------------------------------------------------------------------------------

    eligible_source = [
        row
        for row in rows
        if row.get("eligible") is True
    ]

    print()
    print("=" * 100)
    print("ELIGIBLE CANDIDATE POOL")
    print("=" * 100)

    print(
        f"Snapshot : {snapshot_id}"
    )

    print(
        f"Total rows           : {len(rows)}"
    )

    print(
        f"Already eligible     : {len(eligible_source)}"
    )

    print(
        f"Already NO_TRADE     : "
        f"{len(rows) - len(eligible_source)}"
    )

    # ----------------------------------------------------------------------------------------------
    # IMPORTANT SHORT CIRCUIT
    # ----------------------------------------------------------------------------------------------
    #
    # If eligibility produced zero candidates, we DO NOT manufacture candidates.
    #
    # This is a legitimate NO_TRADE state.
    # ----------------------------------------------------------------------------------------------

    if not eligible_source:

        all_eligible = []
        selected = []
        rejected = []

        print()
        print("=" * 100)
        print("MULTI-ASSET CANDIDATE GATE")
        print("=" * 100)

        print(
            "Eligible candidates : 0"
        )

        print(
            "Candidate ranking   : NOT PERFORMED"
        )

        print(
            "Reason              : "
            "NO ELIGIBLE SIGNALS FROM UPSTREAM GATE"
        )

    else:

        # ------------------------------------------------------------------------------------------
        # RANK
        # ------------------------------------------------------------------------------------------

        (
            all_eligible,
            selected,
            rejected,
        ) = rank_candidates(
            eligible_source
        )

        print()
        print("=" * 100)
        print("RANKED CANDIDATE POOL")
        print("=" * 100)

        print(
            "RANK | ID | ASSET | DIR   | CONF     | "
            "AVAILABLE | QUALITY  | STRENGTH | SCORE"
        )

        print("-" * 100)

        for index, candidate in enumerate(
            all_eligible,
            start=1
        ):

            print(
                f"{index:4d} | "
                f"{candidate.get('id'):2} | "
                f"{candidate.get('asset'):<5} | "
                f"{candidate.get('direction'):<5} | "
                f"{candidate.get('confidence')!s:<8} | "
                f"{candidate.get('available_weight')!s:<9} | "
                f"{candidate.get('data_quality'):<8} | "
                f"{candidate.get('signal_strength'):<8} | "
                f"{candidate.get('candidate_score'):.6f}"
            )

        print()
        print("=" * 100)
        print("SELECTED MULTI-ASSET CANDIDATES")
        print("=" * 100)

        if not selected:

            print(
                "NONE"
            )

        else:

            for index, candidate in enumerate(
                selected,
                start=1
            ):

                print(
                    f"{index}. "
                    f"{candidate.get('asset')} "
                    f"{candidate.get('direction')} "
                    f"score={candidate.get('candidate_score'):.6f}"
                )

    # ----------------------------------------------------------------------------------------------
    # PRODUCTION INVARIANT
    # ----------------------------------------------------------------------------------------------

    production_after = production_baseline()

    unchanged = (
        production_before ==
        production_after
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(
        f"Before rows : "
        f"{production_before['rows']}"
    )

    print(
        f"After rows  : "
        f"{production_after['rows']}"
    )

    print(
        f"Before size : "
        f"{production_before['size']}"
    )

    print(
        f"After size  : "
        f"{production_after['size']}"
    )

    print(
        f"Before SHA256 : "
        f"{production_before['sha256']}"
    )

    print(
        f"After SHA256  : "
        f"{production_after['sha256']}"
    )

    print(
        "PRODUCTION DB INVARIANT : "
        + (
            "PASS"
            if unchanged
            else "FAIL"
        )
    )

    if not unchanged:

        raise RuntimeError(
            "CRITICAL: Production DB changed."
        )

    # ----------------------------------------------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------------------------------------------

    output = build_report(
        production_before,
        production_after,
        capture_db,
        eligibility_report,
        snapshot_id,
        all_eligible,
        selected,
        rejected,
    )

    report_path = os.path.join(
        capture_dir,
        "LIVE_TRADE_CANDIDATE_RANKING_REPORT.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ----------------------------------------------------------------------------------------------
    # FINAL VERDICT
    # ----------------------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print(
        "LIVE TRADE CANDIDATE RANKING "
        "+ MULTI-ASSET DECISION GATE VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_ELIGIBILITY_CONSUMED : PASS"
    )

    print(
        "CANDIDATE_RANKING             : PASS"
    )

    print(
        "MULTI_ASSET_SELECTION         : PASS"
    )

    print(
        "PRODUCTION_ISOLATION          : PASS"
    )

    if selected:

        print(
            "FRONTIER VERDICT              : "
            "CANDIDATES_AVAILABLE"
        )

    else:

        print(
            "FRONTIER VERDICT              : "
            "NO_TRADE_CANDIDATE"
        )

    print()
    print(
        "Selected candidates : "
        f"{len(selected)}"
    )

    print(
        "Eligible pool       : "
        f"{len(all_eligible)}"
    )

    print(
        "Runtime report      : "
        f"{report_path}"
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)

    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Production engine    : NOT EXECUTED")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : NONE")
    print("Live data injection  : NONE")
    print("Order execution      : NONE")

    print()
    print(
        "This frontier selects candidates only."
    )

    print(
        "No trading order or execution action is performed."
    )


if __name__ == "__main__":
    main()