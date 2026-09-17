# ARUNDA_SNAPSHOT_FEATURE_HUNTER_TEMPORAL_COVERAGE_FORENSIC_v0.1.py
#
# READ-ONLY FORENSIC
# Purpose:
#   Determine whether hunter_signals contains temporally corresponding
#   records for the snapshot feature contract.
#
# Forbidden:
#   DB writes
#   Feature Contract modification
#   Outcome calculation
#   Prediction
#   Signal
#   Decision
#   Network
#
# Identity under test:
#   Feature:
#       asset_symbol + snapshot_timestamp
#
#   Hunter:
#       hunter_signals.asset + hunter_signals.timestamp
#
# NOTE:
#   Nearest Hunter rows are reported for forensic purposes only.
#   They are NEVER accepted as valid identity matches unless they satisfy
#   the explicit temporal tolerance.

import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median


DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

FEATURE_CONTRACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

ARTIFACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_HUNTER_TEMPORAL_COVERAGE_FORENSIC_v0.1.json"
)

TOLERANCES = (120, 300, 600)


# =============================================================================
# READ-ONLY DATABASE CONNECTION
# =============================================================================

def connect_read_only():
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


# =============================================================================
# TIMESTAMP NORMALIZATION
# =============================================================================

def parse_timestamp(value):
    """
    Normalize supported ISO timestamps to timezone-aware UTC.

    Supported examples:
        2026-08-23T13:39:16.730073+00:00
        2026-08-15T00:29:52.353078
        2026-08-15T00:29:52.353078Z
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None

    # Hunter timestamps observed in forensic work are naive.
    # They are treated as UTC wall-clock timestamps for comparison.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt


def delta_seconds(a, b):
    if a is None or b is None:
        return None

    return abs((a - b).total_seconds())


# =============================================================================
# FEATURE CONTRACT EXTRACTION
# =============================================================================

def extract_feature_records(contract):
    """
    Extract feature identities conservatively.

    The contract is not modified.

    Expected identity:
        asset_symbol
        snapshot_timestamp
    """

    records = []

    def walk(node):
        if isinstance(node, dict):
            asset = (
                node.get("asset_symbol")
                or node.get("asset")
                or node.get("symbol")
            )

            timestamp = (
                node.get("snapshot_timestamp")
                or node.get("timestamp")
            )

            if asset is not None and timestamp is not None:
                records.append(
                    {
                        "asset_symbol": str(asset).strip().upper(),
                        "snapshot_timestamp": str(timestamp).strip(),
                    }
                )

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(contract)

    # Deduplicate while preserving order.
    seen = set()
    unique = []

    for row in records:
        key = (
            row["asset_symbol"],
            row["snapshot_timestamp"],
        )

        if key not in seen:
            seen.add(key)
            unique.append(row)

    return unique


# =============================================================================
# HUNTER SCHEMA
# =============================================================================

def verify_hunter_schema(conn):
    columns = conn.execute(
        "PRAGMA table_info(hunter_signals)"
    ).fetchall()

    names = [row[1] for row in columns]

    required = {"id", "asset", "timestamp"}

    missing = required - set(names)

    if missing:
        raise RuntimeError(
            f"hunter_signals missing required columns: {sorted(missing)}"
        )

    return names


# =============================================================================
# LOAD HUNTER ROWS
# =============================================================================

def load_hunter_rows(conn):
    rows = conn.execute(
        """
        SELECT
            id,
            asset,
            timestamp
        FROM hunter_signals
        ORDER BY timestamp, id
        """
    ).fetchall()

    result = []

    for row in rows:
        hunter_id, asset, timestamp = row

        result.append(
            {
                "id": hunter_id,
                "asset": (
                    str(asset).strip().upper()
                    if asset is not None
                    else None
                ),
                "timestamp_raw": timestamp,
                "timestamp": parse_timestamp(timestamp),
            }
        )

    return result


# =============================================================================
# TEMPORAL COVERAGE ANALYSIS
# =============================================================================

def analyze_feature(feature, hunters_by_symbol):
    symbol = feature["asset_symbol"]
    feature_raw = feature["snapshot_timestamp"]
    feature_dt = parse_timestamp(feature_raw)

    candidates = hunters_by_symbol.get(symbol, [])

    result = {
        "asset_symbol": symbol,
        "feature_timestamp_raw": feature_raw,
        "feature_timestamp_utc": (
            feature_dt.isoformat() if feature_dt else None
        ),
        "feature_timestamp_parseable": feature_dt is not None,
        "hunter_candidates": len(candidates),
        "exact_timestamp_matches": [],
        "within_tolerance": {
            "120s": [],
            "300s": [],
            "600s": [],
        },
        "nearest_hunter": None,
        "status": None,
    }

    if feature_dt is None:
        result["status"] = "FEATURE_TIMESTAMP_UNPARSEABLE"
        return result

    if not candidates:
        result["status"] = "NO_SAME_SYMBOL_HUNTER"
        return result

    comparable = []

    for hunter in candidates:
        hunter_dt = hunter["timestamp"]

        if hunter_dt is None:
            continue

        delta = delta_seconds(feature_dt, hunter_dt)

        comparable.append(
            (
                delta,
                hunter,
            )
        )

        if delta == 0:
            result["exact_timestamp_matches"].append(
                {
                    "hunter_id": hunter["id"],
                    "hunter_timestamp": hunter["timestamp_raw"],
                    "delta_seconds": delta,
                }
            )

        for tolerance in TOLERANCES:
            if delta <= tolerance:
                result["within_tolerance"][f"{tolerance}s"].append(
                    {
                        "hunter_id": hunter["id"],
                        "hunter_timestamp": hunter["timestamp_raw"],
                        "delta_seconds": delta,
                    }
                )

    if not comparable:
        result["status"] = "HUNTER_TIMESTAMP_UNAVAILABLE"
        return result

    comparable.sort(key=lambda x: x[0])

    nearest_delta, nearest_hunter = comparable[0]

    result["nearest_hunter"] = {
        "hunter_id": nearest_hunter["id"],
        "hunter_timestamp": nearest_hunter["timestamp_raw"],
        "delta_seconds": nearest_delta,
    }

    if result["exact_timestamp_matches"]:
        result["status"] = "EXACT_TEMPORAL_MATCH"

    elif result["within_tolerance"]["120s"]:
        result["status"] = "WITHIN_120S"

    elif result["within_tolerance"]["300s"]:
        result["status"] = "WITHIN_300S"

    elif result["within_tolerance"]["600s"]:
        result["status"] = "WITHIN_600S"

    else:
        result["status"] = "SAME_SYMBOL_TEMPORAL_MISMATCH"

    return result


# =============================================================================
# SHA256
# =============================================================================

def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():

    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    if not FEATURE_CONTRACT_PATH.exists():
        raise FileNotFoundError(FEATURE_CONTRACT_PATH)

    with FEATURE_CONTRACT_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        contract = json.load(f)

    features = extract_feature_records(contract)

    conn = connect_read_only()

    try:
        hunter_columns = verify_hunter_schema(conn)
        hunter_rows = load_hunter_rows(conn)

    finally:
        conn.close()

    hunters_by_symbol = {}

    for hunter in hunter_rows:
        symbol = hunter["asset"]

        if symbol is None:
            continue

        hunters_by_symbol.setdefault(symbol, []).append(hunter)

    analyses = [
        analyze_feature(
            feature,
            hunters_by_symbol,
        )
        for feature in features
    ]

    # -------------------------------------------------------------------------
    # Aggregate statistics
    # -------------------------------------------------------------------------

    exact_matches = 0
    within_120 = 0
    within_300 = 0
    within_600 = 0
    same_symbol_mismatch = 0
    no_same_symbol = 0
    timestamp_unavailable = 0
    unparseable = 0

    deltas = []

    for item in analyses:

        if item["status"] == "EXACT_TEMPORAL_MATCH":
            exact_matches += 1

        elif item["status"] == "WITHIN_120S":
            within_120 += 1

        elif item["status"] == "WITHIN_300S":
            within_300 += 1

        elif item["status"] == "WITHIN_600S":
            within_600 += 1

        elif item["status"] == "SAME_SYMBOL_TEMPORAL_MISMATCH":
            same_symbol_mismatch += 1

        elif item["status"] == "NO_SAME_SYMBOL_HUNTER":
            no_same_symbol += 1

        elif item["status"] == "HUNTER_TIMESTAMP_UNAVAILABLE":
            timestamp_unavailable += 1

        elif item["status"] == "FEATURE_TIMESTAMP_UNPARSEABLE":
            unparseable += 1

        nearest = item.get("nearest_hunter")

        if nearest and nearest.get("delta_seconds") is not None:
            deltas.append(nearest["delta_seconds"])

    # -------------------------------------------------------------------------
    # Determine forensic status
    # -------------------------------------------------------------------------

    if exact_matches == len(features) and features:
        status = "EXACT_TEMPORAL_COVERAGE_ESTABLISHED"

    elif within_120 > 0:
        status = "PARTIAL_TEMPORAL_COVERAGE_WITHIN_120S"

    elif within_300 > 0:
        status = "PARTIAL_TEMPORAL_COVERAGE_WITHIN_300S"

    elif within_600 > 0:
        status = "PARTIAL_TEMPORAL_COVERAGE_WITHIN_600S"

    elif same_symbol_mismatch == len(features) and features:
        status = "SAME_SYMBOL_TEMPORAL_COVERAGE_MISSING"

    elif no_same_symbol == len(features) and features:
        status = "HUNTER_SYMBOL_COVERAGE_MISSING"

    else:
        status = "TEMPORAL_COVERAGE_NOT_ESTABLISHED"

    # -------------------------------------------------------------------------
    # Artifact
    # -------------------------------------------------------------------------

    artifact = {
        "artifact": "ARUNDA_SNAPSHOT_FEATURE_HUNTER_TEMPORAL_COVERAGE_FORENSIC_v0.1",
        "database": str(DB_PATH),
        "feature_contract": str(FEATURE_CONTRACT_PATH),
        "mode": "READ ONLY",
        "network": "FORBIDDEN",
        "outcome": "NOT CALCULATED",
        "prediction": "FORBIDDEN",
        "decision": "FORBIDDEN",
        "identity": {
            "feature": [
                "asset_symbol",
                "snapshot_timestamp",
            ],
            "hunter": [
                "asset",
                "timestamp",
            ],
        },
        "tolerances_seconds": list(TOLERANCES),
        "summary": {
            "feature_identities": len(features),
            "hunter_rows_total": len(hunter_rows),
            "hunter_symbols_total": len(hunters_by_symbol),
            "exact_timestamp_matches": exact_matches,
            "within_120s": within_120,
            "within_300s": within_300,
            "within_600s": within_600,
            "same_symbol_temporal_mismatch": same_symbol_mismatch,
            "no_same_symbol_hunter": no_same_symbol,
            "timestamp_unavailable": timestamp_unavailable,
            "feature_timestamp_unparseable": unparseable,
            "nearest_delta_seconds": {
                "minimum": min(deltas) if deltas else None,
                "maximum": max(deltas) if deltas else None,
                "mean": mean(deltas) if deltas else None,
                "median": median(deltas) if deltas else None,
            },
        },
        "hunter_schema": hunter_columns,
        "records": analyses,
        "forensic_status": status,
        "predictive_claim": "NOT ESTABLISHED",
        "relationship_calculation": "NOT PERFORMED",
        "database_modified": False,
        "feature_contract_modified": False,
    }

    with ARTIFACT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    digest = sha256_file(ARTIFACT_PATH)

    # -------------------------------------------------------------------------
    # Console report
    # -------------------------------------------------------------------------

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> HUNTER TEMPORAL COVERAGE FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print(f"Feature Contract: {FEATURE_CONTRACT_PATH}")
    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Outcome         : NOT CALCULATED")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")
    print("Match Tolerance : 120 / 300 / 600 seconds")
    print("-" * 90)

    print("=" * 90)
    print("TEMPORAL COVERAGE FORENSIC")
    print("=" * 90)

    print(f"Feature identities              : {len(features)}")
    print(f"Hunter rows total               : {len(hunter_rows)}")
    print(f"Hunter symbols total            : {len(hunters_by_symbol)}")
    print(f"Exact timestamp matches         : {exact_matches}")
    print(f"Within 120s                     : {within_120}")
    print(f"Within 300s                     : {within_300}")
    print(f"Within 600s                     : {within_600}")
    print(f"Same symbol temporal mismatch   : {same_symbol_mismatch}")
    print(f"No same-symbol Hunter            : {no_same_symbol}")
    print(f"Timestamp unavailable            : {timestamp_unavailable}")
    print(f"Feature timestamp unparseable    : {unparseable}")

    print("-" * 90)
    print("NEAREST HUNTER DELTA")
    print("-" * 90)

    print(
        f"Minimum delta (sec) : "
        f"{min(deltas) if deltas else None}"
    )
    print(
        f"Maximum delta (sec) : "
        f"{max(deltas) if deltas else None}"
    )
    print(
        f"Mean delta (sec)    : "
        f"{mean(deltas) if deltas else None}"
    )
    print(
        f"Median delta (sec)  : "
        f"{median(deltas) if deltas else None}"
    )

    print("-" * 90)
    print("PER-FEATURE TEMPORAL COVERAGE")
    print("-" * 90)

    for item in analyses:

        print(f"SYMBOL : {item['asset_symbol']}")
        print(
            f"  FEATURE TIMESTAMP : "
            f"{item['feature_timestamp_raw']}"
        )

        nearest = item.get("nearest_hunter")

        if nearest:
            print(
                f"  NEAREST HUNTER ID : "
                f"{nearest['hunter_id']}"
            )
            print(
                f"  HUNTER TIMESTAMP  : "
                f"{nearest['hunter_timestamp']}"
            )
            print(
                f"  DELTA SEC         : "
                f"{nearest['delta_seconds']}"
            )
        else:
            print("  NEAREST HUNTER    : NONE")

        print(
            f"  STATUS            : "
            f"{item['status']}"
        )
        print("-" * 90)

    print("=" * 90)
    print(f"FORENSIC STATUS : {status}")
    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("RELATIONSHIP CALCULATION : NOT PERFORMED")
    print(f"Artifact : {ARTIFACT_PATH}")
    print(f"SHA256   : {digest}")
    print("=" * 90)


if __name__ == "__main__":
    main()