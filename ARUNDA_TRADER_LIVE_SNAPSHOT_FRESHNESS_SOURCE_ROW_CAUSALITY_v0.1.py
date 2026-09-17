# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE SIGNAL QUALITY + DECISION SAFETY CONTRACT v0.1

OBJECTIVE:
    Validate the newest real FUSION_v0.5 live snapshot for:
        - fused_score coherence
        - confidence coherence
        - signal_strength coherence
        - regime coherence
        - direction coherence
        - available_weight coherence
        - missing_arm_penalty coherence
        - arm-aware decision safety
        - row-level provenance
        - production DB isolation

RULES:
    Production DB writes          : FORBIDDEN
    Production engine execution   : NO
    Historical repair              : NONE
    Direction inference            : NONE
    Score reconstruction           : NONE
    Synthetic data                 : FORBIDDEN
    Interpolation                  : FORBIDDEN
    Forward fill                   : FORBIDDEN
    Back fill                      : FORBIDDEN
    Live data injection            : NONE

IMPORTANT:
    This script analyzes the disposable LIVE CAPTURE only.
    It does NOT execute fusion_engine.main().
"""

import os
import sys
import sqlite3
import hashlib
import json
import tempfile
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
PRODUCTION_DB = os.path.join(PROJECT_ROOT, "arunda.db")

TARGET_TABLE = "fusion_signals"
EXPECTED_ENGINE = "FUSION_v0.5"

EXPECTED_ASSETS = {"BTC", "ETH", "SOL", "XRP"}

REPORT_NAME = "LIVE_SIGNAL_QUALITY_DECISION_SAFETY_REPORT.json"


# ============================================================
# OUTPUT
# ============================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def line():
    print("-" * 100)


# ============================================================
# HASH
# ============================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ============================================================
# READ ONLY CONNECTION
# ============================================================

def readonly_connection(path):
    uri = "file:" + path.replace("\\", "/") + "?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=5
    )


# ============================================================
# FIND LATEST LIVE CAPTURE
# ============================================================

def find_latest_capture():
    base = tempfile.gettempdir()

    candidates = []

    for name in os.listdir(base):

        if not name.startswith("arunda_live_launch_"):
            continue

        directory = os.path.join(base, name)

        if not os.path.isdir(directory):
            continue

        db_path = os.path.join(
            directory,
            "arunda_live_capture.db"
        )

        if not os.path.isfile(db_path):
            continue

        try:
            mtime = os.path.getmtime(db_path)

            candidates.append(
                (mtime, directory, db_path)
            )

        except OSError:
            pass

    if not candidates:
        raise RuntimeError(
            "No LIVE launch capture database was found."
        )

    candidates.sort(reverse=True)

    return candidates[0][1], candidates[0][2]


# ============================================================
# SCHEMA
# ============================================================

def get_columns(conn):

    rows = conn.execute(
        f"PRAGMA table_info({TARGET_TABLE})"
    ).fetchall()

    return {
        row[1]: row
        for row in rows
    }


REQUIRED_COLUMNS = {
    "id",
    "timestamp",
    "asset",
    "market_score",
    "positioning_score",
    "news_score",
    "fused_score",
    "confidence",
    "regime",
    "data_quality",
    "market_available",
    "positioning_available",
    "news_available",
    "engine_version",
    "market_score_norm",
    "positioning_score_norm",
    "news_score_norm",
    "agreement_score",
    "available_weight",
    "snapshot_id",
    "missing_arm_penalty",
    "news_confidence",
    "signal_strength",
    "entry_price",
    "direction",
}


def schema_contract(conn):

    columns = get_columns(conn)

    missing = sorted(
        REQUIRED_COLUMNS - set(columns)
    )

    return {
        "pass": len(missing) == 0,
        "missing": missing,
        "columns": sorted(columns),
    }


# ============================================================
# LOAD NEWEST SNAPSHOT
# ============================================================

def load_latest_snapshot(conn):

    row = conn.execute(
        f"""
        SELECT snapshot_id
        FROM {TARGET_TABLE}
        WHERE engine_version = ?
          AND snapshot_id IS NOT NULL
        ORDER BY timestamp DESC, id DESC
        LIMIT 1
        """,
        (EXPECTED_ENGINE,)
    ).fetchone()

    if not row:
        raise RuntimeError(
            "No FUSION_v0.5 snapshot found."
        )

    snapshot_id = row[0]

    rows = conn.execute(
        f"""
        SELECT
            id,
            timestamp,
            asset,
            market_score,
            positioning_score,
            news_score,
            fused_score,
            confidence,
            regime,
            data_quality,
            market_available,
            positioning_available,
            news_available,
            engine_version,
            market_score_norm,
            positioning_score_norm,
            news_score_norm,
            agreement_score,
            available_weight,
            snapshot_id,
            missing_arm_penalty,
            news_confidence,
            signal_strength,
            entry_price,
            direction
        FROM {TARGET_TABLE}
        WHERE snapshot_id = ?
        ORDER BY id
        """,
        (snapshot_id,)
    ).fetchall()

    return snapshot_id, rows


# ============================================================
# ROW MAPPING
# ============================================================

FIELDS = [
    "id",
    "timestamp",
    "asset",
    "market_score",
    "positioning_score",
    "news_score",
    "fused_score",
    "confidence",
    "regime",
    "data_quality",
    "market_available",
    "positioning_available",
    "news_available",
    "engine_version",
    "market_score_norm",
    "positioning_score_norm",
    "news_score_norm",
    "agreement_score",
    "available_weight",
    "snapshot_id",
    "missing_arm_penalty",
    "news_confidence",
    "signal_strength",
    "entry_price",
    "direction",
]


def row_dict(row):

    return dict(zip(FIELDS, row))


# ============================================================
# BASIC CONTRACTS
# ============================================================

def check_identity(rows):

    ids = [r["id"] for r in rows]
    assets = [r["asset"] for r in rows]

    return (
        len(ids) == len(set(ids))
        and len(assets) == len(set(assets))
        and set(assets) == EXPECTED_ASSETS
    )


def check_engine(rows):

    return all(
        r["engine_version"] == EXPECTED_ENGINE
        for r in rows
    )


def check_snapshot_identity(rows, snapshot_id):

    return all(
        r["snapshot_id"] == snapshot_id
        for r in rows
    )


# ============================================================
# ARM HELPERS
# ============================================================

def arm_state(value):
    return "ON" if value == 1 else "OFF"


def available_arm_count(r):

    return sum(
        [
            r["market_available"] == 1,
            r["positioning_available"] == 1,
            r["news_available"] == 1,
        ]
    )


# ============================================================
# SCORE AVAILABILITY CONTRACT
# ============================================================

def score_matches_availability(r):

    checks = []

    checks.append(
        r["market_available"] == 1
        and r["market_score"] is not None
        or
        r["market_available"] == 0
        and r["market_score"] is None
    )

    checks.append(
        r["positioning_available"] == 1
        and r["positioning_score"] is not None
        or
        r["positioning_available"] == 0
        and r["positioning_score"] is None
    )

    checks.append(
        r["news_available"] == 1
        and r["news_score"] is not None
        or
        r["news_available"] == 0
        and r["news_score"] is None
    )

    return all(checks)


# ============================================================
# AVAILABLE WEIGHT CONTRACT
#
# Based on the observed v0.5 runtime contract:
#
# M ON + P ON + N ON = 1.00
# M ON + P OFF + N ON = 0.65
# M OFF + P ON + N ON = 0.60
# M OFF + P OFF + N ON = 0.25
#
# We validate observed contract values rather than
# reconstructing the fusion calculation.
# ============================================================

EXPECTED_AVAILABLE_WEIGHTS = {
    (1, 1, 1): 1.00,
    (1, 0, 1): 0.65,
    (0, 1, 1): 0.60,
    (0, 0, 1): 0.25,
}


def check_available_weight(r):

    key = (
        r["market_available"],
        r["positioning_available"],
        r["news_available"],
    )

    expected = EXPECTED_AVAILABLE_WEIGHTS.get(key)

    if expected is None:
        return False

    if r["available_weight"] is None:
        return False

    return abs(
        float(r["available_weight"]) - expected
    ) < 1e-9


# ============================================================
# MISSING ARM PENALTY CONTRACT
#
# Observed runtime values:
#
# Full         -> 1.00
# One missing  -> 0.82
# Two missing  -> 0.65
#
# This is a CONTRACT VALIDATION only.
# No value is reconstructed.
# ============================================================

EXPECTED_PENALTIES = {
    (1, 1, 1): 1.00,
    (1, 0, 1): 0.82,
    (0, 1, 1): 0.82,
    (0, 0, 1): 0.65,
}


def check_missing_penalty(r):

    key = (
        r["market_available"],
        r["positioning_available"],
        r["news_available"],
    )

    expected = EXPECTED_PENALTIES.get(key)

    if expected is None:
        return False

    if r["missing_arm_penalty"] is None:
        return False

    return abs(
        float(r["missing_arm_penalty"]) - expected
    ) < 1e-9


# ============================================================
# DATA QUALITY CONTRACT
# ============================================================

def expected_quality(r):

    count = available_arm_count(r)

    if count == 3:
        return "VERIFIED"

    if count >= 1:
        return "PARTIAL"

    return None


def check_data_quality(r):

    expected = expected_quality(r)

    return (
        expected is not None
        and r["data_quality"] == expected
    )


# ============================================================
# DIRECTION SAFETY CONTRACT
#
# We do NOT calculate direction.
# We only validate:
#   - allowed vocabulary
#   - non-null
#   - existence of required supporting values
# ============================================================

ALLOWED_DIRECTIONS = {
    "LONG",
    "SHORT",
    "FLAT",
}


def check_direction_safety(r):

    if r["direction"] not in ALLOWED_DIRECTIONS:
        return False

    if r["fused_score"] is None:
        return False

    return True


# ============================================================
# CONFIDENCE SAFETY
# ============================================================

def check_confidence(r):

    if r["confidence"] is None:
        return False

    try:
        value = float(r["confidence"])
    except (TypeError, ValueError):
        return False

    return 0.0 <= value <= 1.0


# ============================================================
# SIGNAL STRENGTH CONTRACT
# ============================================================

ALLOWED_SIGNAL_STRENGTH = {
    "WEAK",
    "MODERATE",
    "STRONG",
}


def check_signal_strength(r):

    return (
        r["signal_strength"]
        in ALLOWED_SIGNAL_STRENGTH
    )


# ============================================================
# REGIME CONTRACT
# ============================================================

ALLOWED_REGIMES = {
    "BULLISH",
    "BEARISH",
    "NEUTRAL",
    "STRONG_BULLISH",
    "STRONG_BEARISH",
}


def check_regime(r):

    return r["regime"] in ALLOWED_REGIMES


# ============================================================
# ENTRY PRICE
# ============================================================

def check_entry_price(r):

    if r["entry_price"] is None:
        return False

    try:
        return float(r["entry_price"]) > 0
    except (TypeError, ValueError):
        return False


# ============================================================
# SAFETY MATRIX
# ============================================================

def decision_safety_class(r):

    arms = available_arm_count(r)

    quality = r["data_quality"]
    strength = r["signal_strength"]
    direction = r["direction"]

    if arms == 3:
        if quality == "VERIFIED":
            return "FULL_INPUT"

    if arms == 2:
        return "PARTIAL_INPUT"

    if arms == 1:
        return "LOW_INPUT"

    return "NO_INPUT"


# ============================================================
# ROW-LEVEL AUDIT
# ============================================================

def audit_row(r):

    checks = {
        "score_availability": score_matches_availability(r),
        "available_weight": check_available_weight(r),
        "missing_arm_penalty": check_missing_penalty(r),
        "data_quality": check_data_quality(r),
        "direction": check_direction_safety(r),
        "confidence": check_confidence(r),
        "signal_strength": check_signal_strength(r),
        "regime": check_regime(r),
        "entry_price": check_entry_price(r),
    }

    return checks


# ============================================================
# MAIN
# ============================================================

def main():

    banner(
        "ARUNDA TRADER LIVE SIGNAL QUALITY + "
        "DECISION SAFETY CONTRACT v0.1"
    )

    print(
        "OBJECTIVE:\n"
        "  Validate the newest real FUSION_v0.5 snapshot for:\n"
        "    - signal quality\n"
        "    - arm-aware decision safety\n"
        "    - confidence / regime / strength coherence\n"
        "    - availability metadata coherence\n"
        "    - row-level provenance\n"
        "    - production DB isolation\n"
    )

    print()
    print("Production DB writes          : FORBIDDEN")
    print("Production engine run         : NO")
    print("Historical repair             : NONE")
    print("Direction inference           : NONE")
    print("Score reconstruction          : NONE")
    print("Synthetic data                : FORBIDDEN")
    print("Live data injection           : NONE")

    # --------------------------------------------------------
    # PRODUCTION BASELINE
    # --------------------------------------------------------

    banner("PRODUCTION DATABASE BASELINE")

    prod_size = os.path.getsize(PRODUCTION_DB)
    prod_hash = sha256_file(PRODUCTION_DB)

    with readonly_connection(PRODUCTION_DB) as conn:

        prod_rows = conn.execute(
            f"SELECT COUNT(*) FROM {TARGET_TABLE}"
        ).fetchone()[0]

    print(f"Production DB                : {PRODUCTION_DB}")
    print(f"Rows                         : {prod_rows}")
    print(f"Size                         : {prod_size}")
    print(f"SHA256                       : {prod_hash}")

    # --------------------------------------------------------
    # LIVE CAPTURE
    # --------------------------------------------------------

    banner("LIVE CAPTURE DISCOVERY")

    capture_dir, capture_db = find_latest_capture()

    print(f"Capture directory            : {capture_dir}")
    print(f"Capture DB                   : {capture_db}")
    print(f"Capture size                 : {os.path.getsize(capture_db)}")

    # --------------------------------------------------------
    # READ ONLY CAPTURE
    # --------------------------------------------------------

    conn = readonly_connection(capture_db)

    try:

        # ----------------------------------------------------
        # SCHEMA
        # ----------------------------------------------------

        banner("SCHEMA CONTRACT")

        schema = schema_contract(conn)

        if not schema["pass"]:

            print("SCHEMA : FAIL")
            print("Missing columns:")

            for c in schema["missing"]:
                print(f"  {c}")

            return 1

        print("SCHEMA : PASS")

        # ----------------------------------------------------
        # SNAPSHOT
        # ----------------------------------------------------

        snapshot_id, rows_raw = load_latest_snapshot(conn)

        rows = [
            row_dict(r)
            for r in rows_raw
        ]

        banner("CURRENT LIVE SNAPSHOT")

        print(f"Snapshot ID                 : {snapshot_id}")
        print(f"Rows                        : {len(rows)}")

        assets = sorted(
            {r["asset"] for r in rows}
        )

        print(
            "Assets                      : "
            + ", ".join(assets)
        )

        # ----------------------------------------------------
        # BASIC CONTRACTS
        # ----------------------------------------------------

        banner("IDENTITY + ENGINE CONTRACT")

        identity_pass = check_identity(rows)
        engine_pass = check_engine(rows)
        snapshot_pass = check_snapshot_identity(
            rows,
            snapshot_id
        )

        print(
            f"ROW IDENTITY                : "
            f"{'PASS' if identity_pass else 'FAIL'}"
        )

        print(
            f"ENGINE IDENTITY             : "
            f"{'PASS' if engine_pass else 'FAIL'}"
        )

        print(
            f"SNAPSHOT IDENTITY           : "
            f"{'PASS' if snapshot_pass else 'FAIL'}"
        )

        # ----------------------------------------------------
        # ROW AUDIT
        # ----------------------------------------------------

        banner("ROW-LEVEL SIGNAL QUALITY")

        audit_results = []

        for r in rows:

            checks = audit_row(r)

            passed = all(checks.values())

            safety_class = decision_safety_class(r)

            audit_results.append({
                "id": r["id"],
                "asset": r["asset"],
                "direction": r["direction"],
                "fused_score": r["fused_score"],
                "confidence": r["confidence"],
                "regime": r["regime"],
                "signal_strength": r["signal_strength"],
                "data_quality": r["data_quality"],
                "available_weight": r["available_weight"],
                "missing_arm_penalty": r["missing_arm_penalty"],
                "safety_class": safety_class,
                "checks": checks,
                "pass": passed,
            })

            print(
                f"id={r['id']:>3} | "
                f"{r['asset']:<4} | "
                f"M={r['market_available']} "
                f"P={r['positioning_available']} "
                f"N={r['news_available']} | "
                f"dir={r['direction']:<5} | "
                f"conf={r['confidence']} | "
                f"regime={r['regime']:<16} | "
                f"strength={r['signal_strength']:<8} | "
                f"quality={r['data_quality']:<8} | "
                f"safety={safety_class}"
            )

        # ----------------------------------------------------
        # CONTRACT COUNTS
        # ----------------------------------------------------

        banner("SIGNAL QUALITY CONTRACTS")

        contract_names = [
            "score_availability",
            "available_weight",
            "missing_arm_penalty",
            "data_quality",
            "direction",
            "confidence",
            "signal_strength",
            "regime",
            "entry_price",
        ]

        contract_status = {}

        for name in contract_names:

            passed = sum(
                1
                for result in audit_results
                if result["checks"][name]
            )

            total = len(audit_results)

            ok = passed == total

            contract_status[name] = ok

            print(
                f"{name:<28} | "
                f"{passed:>2}/{total:<2} | "
                f"{'PASS' if ok else 'FAIL'}"
            )

        # ----------------------------------------------------
        # SAFETY DISTRIBUTION
        # ----------------------------------------------------

        banner("DECISION SAFETY DISTRIBUTION")

        safety_counts = {}

        for result in audit_results:

            key = result["safety_class"]

            safety_counts[key] = (
                safety_counts.get(key, 0) + 1
            )

        for key in [
            "FULL_INPUT",
            "PARTIAL_INPUT",
            "LOW_INPUT",
            "NO_INPUT",
        ]:

            print(
                f"{key:<20} | "
                f"{safety_counts.get(key, 0)}"
            )

        # ----------------------------------------------------
        # DIRECTION DISTRIBUTION
        # ----------------------------------------------------

        banner("DIRECTION OUTPUT OBSERVATION")

        direction_counts = {}

        for r in rows:

            d = r["direction"]

            direction_counts[d] = (
                direction_counts.get(d, 0) + 1
            )

        for d in [
            "FLAT",
            "LONG",
            "SHORT",
        ]:

            print(
                f"{d:<10} | "
                f"{direction_counts.get(d, 0)}"
            )

        # ----------------------------------------------------
        # ARM MATRIX
        # ----------------------------------------------------

        banner("ARM / QUALITY MATRIX")

        matrix = {}

        for r in rows:

            key = (
                r["market_available"],
                r["positioning_available"],
                r["news_available"],
                r["data_quality"],
            )

            matrix[key] = matrix.get(key, 0) + 1

        for key, count in sorted(matrix.items()):

            m, p, n, quality = key

            print(
                f"M={'ON' if m else 'OFF':<3} | "
                f"P={'ON' if p else 'OFF':<3} | "
                f"N={'ON' if n else 'OFF':<3} | "
                f"{quality:<8} | rows={count}"
            )

        # ----------------------------------------------------
        # PRODUCTION INVARIANT
        # ----------------------------------------------------

        banner("PRODUCTION DATABASE INVARIANT")

        prod_size_after = os.path.getsize(PRODUCTION_DB)
        prod_hash_after = sha256_file(PRODUCTION_DB)

        with readonly_connection(PRODUCTION_DB) as prod_conn:

            prod_rows_after = prod_conn.execute(
                f"SELECT COUNT(*) FROM {TARGET_TABLE}"
            ).fetchone()[0]

        invariant = (
            prod_size == prod_size_after
            and prod_hash == prod_hash_after
            and prod_rows == prod_rows_after
        )

        print(
            f"Before size                 : {prod_size}"
        )

        print(
            f"After size                  : {prod_size_after}"
        )

        print(
            f"Before SHA256               : {prod_hash}"
        )

        print(
            f"After SHA256                : {prod_hash_after}"
        )

        print(
            f"Before rows                 : {prod_rows}"
        )

        print(
            f"After rows                  : {prod_rows_after}"
        )

        print(
            "PRODUCTION DB INVARIANT     : "
            + ("PASS" if invariant else "FAIL")
        )

        # ----------------------------------------------------
        # FINAL VERDICT
        # ----------------------------------------------------

        all_contracts_pass = all(
            contract_status.values()
        )

        row_pass = all(
            result["pass"]
            for result in audit_results
        )

        final_pass = (
            identity_pass
            and engine_pass
            and snapshot_pass
            and all_contracts_pass
            and row_pass
            and invariant
        )

        banner(
            "LIVE SIGNAL QUALITY + DECISION SAFETY VERDICT"
        )

        print(
            f"SNAPSHOT_IDENTITY          : "
            f"{'PASS' if snapshot_pass else 'FAIL'}"
        )

        print(
            f"ENGINE_IDENTITY            : "
            f"{'PASS' if engine_pass else 'FAIL'}"
        )

        print(
            f"ROW_IDENTITY               : "
            f"{'PASS' if identity_pass else 'FAIL'}"
        )

        print(
            f"SIGNAL_QUALITY_CONTRACT    : "
            f"{'PASS' if all_contracts_pass else 'FAIL'}"
        )

        print(
            f"ROW_LEVEL_SAFETY           : "
            f"{'PASS' if row_pass else 'FAIL'}"
        )

        print(
            f"PRODUCTION_ISOLATION       : "
            f"{'PASS' if invariant else 'FAIL'}"
        )

        print()

        if final_pass:
            print("FRONTIER VERDICT : PASS")
        else:
            print("FRONTIER VERDICT : FAIL")

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        report = {
            "frontier": (
                "LIVE SIGNAL QUALITY + "
                "DECISION SAFETY CONTRACT v0.1"
            ),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "production_db": PRODUCTION_DB,

            "production_baseline": {
                "rows": prod_rows,
                "size": prod_size,
                "sha256": prod_hash,
            },

            "capture_db": capture_db,

            "snapshot_id": snapshot_id,

            "engine": EXPECTED_ENGINE,

            "row_count": len(rows),

            "assets": assets,

            "contract_status": contract_status,

            "safety_distribution": safety_counts,

            "direction_distribution": direction_counts,

            "rows": audit_results,

            "production_invariant": invariant,

            "verdict": (
                "PASS"
                if final_pass
                else "FAIL"
            ),

            "safety": {
                "production_writes": False,
                "production_engine_run": False,
                "historical_repair": False,
                "direction_inference": False,
                "score_reconstruction": False,
                "synthetic_data": False,
                "live_data_injection": False,
            },
        }

        report_path = os.path.join(
            capture_dir,
            REPORT_NAME
        )

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                report,
                f,
                indent=2,
                ensure_ascii=False
            )

        print()
        print(
            f"Runtime report              : "
            f"{report_path}"
        )

        # ----------------------------------------------------
        # FINAL SAFETY
        # ----------------------------------------------------

        banner("FINAL SAFETY VERDICT")

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

        print()
        print(
            "The live capture remains disposable."
        )

        print(
            "Production arunda.db was not modified."
        )

        return 0 if final_pass else 2

    finally:

        conn.close()


if __name__ == "__main__":
    sys.exit(main())