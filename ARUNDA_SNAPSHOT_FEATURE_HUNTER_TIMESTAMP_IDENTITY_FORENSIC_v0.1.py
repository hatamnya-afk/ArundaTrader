from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> HUNTER TIMESTAMP / IDENTITY FORENSIC v0.1
#
# PURPOSE:
#   Compare the real identity of Feature Contract records against
#   hunter_signals using:
#
#       asset_symbol + snapshot_timestamp
#       vs
#       hunter_signals.asset + hunter_signals.timestamp
#
# MODE:
#   READ ONLY
#
# FORBIDDEN:
#   DB WRITE
#   NETWORK
#   EXCHANGE
#   SIGNAL GENERATION
#   PREDICTION
#   TRADING DECISION
#   OUTCOME CALCULATION
#   FEATURE CONTRACT MODIFICATION
#   TIMESTAMP NORMALIZATION FOR MATCHING
#
# IMPORTANT:
#   This forensic does NOT establish a relationship.
#   It only identifies the actual identity/timestamp mismatch.
# =============================================================================


# -----------------------------------------------------------------------------
# PATHS
# -----------------------------------------------------------------------------

DB_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

FEATURE_CONTRACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

OUTPUT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_HUNTER_TIMESTAMP_IDENTITY_FORENSIC_v0.1.json"
)


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

FORENSIC_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_HUNTER_TIMESTAMP_IDENTITY_FORENSIC_v0.1"
)

MATCH_TOLERANCE_SECONDS = 120


# -----------------------------------------------------------------------------
# UTILITIES
# -----------------------------------------------------------------------------

def finite_number(value: Any) -> float | None:
    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (TypeError, ValueError):
        return None


def normalize_symbol(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def parse_timestamp(value: Any) -> datetime | None:
    """
    Parse timestamp without changing the original stored value.

    Naive timestamps remain naive.
    Offset-aware timestamps are converted to UTC only for
    an auxiliary comparison representation.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    candidate = text

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(candidate)

    except ValueError:
        return None

    return dt


def timestamp_comparison_seconds(
    feature_dt: datetime,
    hunter_dt: datetime,
) -> float | None:
    """
    Compare timestamps conservatively.

    We do NOT assume that a naive timestamp is UTC.

    Therefore:

    aware vs aware:
        compare in UTC

    naive vs naive:
        compare directly

    aware vs naive:
        comparison is NOT performed.
    """

    feature_aware = (
        feature_dt.tzinfo is not None
        and feature_dt.utcoffset() is not None
    )

    hunter_aware = (
        hunter_dt.tzinfo is not None
        and hunter_dt.utcoffset() is not None
    )

    if feature_aware != hunter_aware:
        return None

    if feature_aware and hunter_aware:

        feature_utc = feature_dt.astimezone(
            timezone.utc
        )

        hunter_utc = hunter_dt.astimezone(
            timezone.utc
        )

        return abs(
            (
                feature_utc
                - hunter_utc
            ).total_seconds()
        )

    return abs(
        (
            feature_dt
            - hunter_dt
        ).total_seconds()
    )


def timestamp_metadata(
    value: Any,
) -> dict[str, Any]:

    parsed = parse_timestamp(value)

    if parsed is None:

        return {
            "raw": None if value is None else str(value),
            "parseable": False,
            "timezone_aware": None,
            "utc": None,
        }

    aware = (
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None
    )

    utc_value = None

    if aware:
        utc_value = (
            parsed
            .astimezone(timezone.utc)
            .isoformat()
        )

    return {
        "raw": str(value),
        "parseable": True,
        "timezone_aware": aware,
        "utc": utc_value,
    }


# -----------------------------------------------------------------------------
# DATABASE
# -----------------------------------------------------------------------------

def connect_database() -> sqlite3.Connection:

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# -----------------------------------------------------------------------------
# SCHEMA
# -----------------------------------------------------------------------------

def get_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    if not rows:
        raise RuntimeError(
            f"Table not found: {table_name}"
        )

    return [
        row["name"]
        for row in rows
    ]


def require_columns(
    columns: list[str],
    required: tuple[str, ...],
    table_name: str,
) -> None:

    missing = [
        column
        for column in required
        if column not in columns
    ]

    if missing:
        raise RuntimeError(
            f"{table_name} missing required columns: "
            + ", ".join(missing)
        )


# -----------------------------------------------------------------------------
# FEATURE CONTRACT
# -----------------------------------------------------------------------------

def load_feature_contract() -> dict[str, Any]:

    if not FEATURE_CONTRACT_PATH.exists():
        raise FileNotFoundError(
            "Feature Contract not found: "
            f"{FEATURE_CONTRACT_PATH}"
        )

    artifact = json.loads(
        FEATURE_CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        artifact,
        dict,
    ):
        raise RuntimeError(
            "Invalid Feature Contract artifact."
        )

    if not artifact.get(
        "records"
    ):
        raise RuntimeError(
            "Feature Contract contains no records."
        )

    return artifact


# -----------------------------------------------------------------------------
# FEATURE IDENTITY EXTRACTION
# -----------------------------------------------------------------------------

def extract_feature_identities(
    contract: dict[str, Any],
) -> list[dict[str, Any]]:

    identities = []

    for record in contract["records"]:

        symbol = record.get(
            "asset_symbol"
        )

        timestamp = record.get(
            "snapshot_timestamp"
        )

        if not symbol or not timestamp:
            continue

        identities.append(
            {
                "asset_symbol":
                    normalize_symbol(symbol),

                "asset_symbol_raw":
                    str(symbol),

                "snapshot_timestamp":
                    str(timestamp),

                "timestamp":
                    timestamp_metadata(timestamp),

                "observation_count":
                    record.get(
                        "observation_count"
                    ),
            }
        )

    return identities


# -----------------------------------------------------------------------------
# HUNTER ROWS
# -----------------------------------------------------------------------------

def load_hunter_rows(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:

    columns = get_columns(
        connection,
        "hunter_signals",
    )

    require_columns(
        columns,
        (
            "id",
            "asset",
            "timestamp",
        ),
        "hunter_signals",
    )

    return connection.execute(
        """
        SELECT
            id,
            asset,
            timestamp
        FROM hunter_signals
        ORDER BY timestamp ASC, id ASC
        """
    ).fetchall()


# -----------------------------------------------------------------------------
# EXACT IDENTITY MATCH
# -----------------------------------------------------------------------------

def exact_identity_matches(
    feature: dict[str, Any],
    hunter_rows: list[sqlite3.Row],
) -> list[dict[str, Any]]:

    feature_symbol = feature[
        "asset_symbol"
    ]

    feature_timestamp = feature[
        "snapshot_timestamp"
    ]

    matches = []

    for row in hunter_rows:

        hunter_symbol = normalize_symbol(
            row["asset"]
        )

        hunter_timestamp = str(
            row["timestamp"]
        )

        if (
            hunter_symbol
            == feature_symbol
            and hunter_timestamp
            == feature_timestamp
        ):

            matches.append(
                {
                    "hunter_id":
                        row["id"],

                    "asset":
                        row["asset"],

                    "timestamp":
                        hunter_timestamp,
                }
            )

    return matches


# -----------------------------------------------------------------------------
# SAME SYMBOL CANDIDATES
# -----------------------------------------------------------------------------

def same_symbol_candidates(
    feature: dict[str, Any],
    hunter_rows: list[sqlite3.Row],
) -> list[dict[str, Any]]:

    feature_symbol = feature[
        "asset_symbol"
    ]

    candidates = []

    for row in hunter_rows:

        hunter_symbol = normalize_symbol(
            row["asset"]
        )

        if hunter_symbol != feature_symbol:
            continue

        hunter_timestamp = str(
            row["timestamp"]
        )

        feature_dt = parse_timestamp(
            feature["snapshot_timestamp"]
        )

        hunter_dt = parse_timestamp(
            hunter_timestamp
        )

        delta = None

        if (
            feature_dt is not None
            and hunter_dt is not None
        ):
            delta = timestamp_comparison_seconds(
                feature_dt,
                hunter_dt,
            )

        candidates.append(
            {
                "hunter_id":
                    row["id"],

                "asset":
                    row["asset"],

                "timestamp":
                    hunter_timestamp,

                "timestamp_metadata":
                    timestamp_metadata(
                        hunter_timestamp
                    ),

                "delta_seconds":
                    delta,

                "within_tolerance":
                    (
                        delta is not None
                        and delta
                        <= MATCH_TOLERANCE_SECONDS
                    ),
            }
        )

    candidates.sort(
        key=lambda item: (
            float("inf")
            if item["delta_seconds"] is None
            else item["delta_seconds"]
        )
    )

    return candidates


# -----------------------------------------------------------------------------
# GLOBAL NEAREST TIMESTAMP
# -----------------------------------------------------------------------------

def nearest_timestamp_candidates(
    feature: dict[str, Any],
    hunter_rows: list[sqlite3.Row],
    limit: int = 5,
) -> list[dict[str, Any]]:

    feature_dt = parse_timestamp(
        feature["snapshot_timestamp"]
    )

    if feature_dt is None:
        return []

    candidates = []

    for row in hunter_rows:

        hunter_dt = parse_timestamp(
            row["timestamp"]
        )

        if hunter_dt is None:
            continue

        delta = timestamp_comparison_seconds(
            feature_dt,
            hunter_dt,
        )

        if delta is None:
            continue

        candidates.append(
            {
                "hunter_id":
                    row["id"],

                "asset":
                    row["asset"],

                "normalized_asset":
                    normalize_symbol(
                        row["asset"]
                    ),

                "timestamp":
                    str(row["timestamp"]),

                "delta_seconds":
                    delta,

                "same_symbol":
                    (
                        normalize_symbol(
                            row["asset"]
                        )
                        == feature["asset_symbol"]
                    ),

                "within_tolerance":
                    delta
                    <= MATCH_TOLERANCE_SECONDS,
            }
        )

    candidates.sort(
        key=lambda item: item[
            "delta_seconds"
        ]
    )

    return candidates[:limit]


# -----------------------------------------------------------------------------
# PER FEATURE FORENSIC
# -----------------------------------------------------------------------------

def analyze_feature(
    feature: dict[str, Any],
    hunter_rows: list[sqlite3.Row],
) -> dict[str, Any]:

    exact = exact_identity_matches(
        feature,
        hunter_rows,
    )

    same_symbol = same_symbol_candidates(
        feature,
        hunter_rows,
    )

    nearest = nearest_timestamp_candidates(
        feature,
        hunter_rows,
    )

    nearest_same_symbol = (
        same_symbol[0]
        if same_symbol
        else None
    )

    classification = "UNMATCHED"

    if exact:
        classification = "EXACT_MATCH"

    elif (
        nearest_same_symbol is not None
        and nearest_same_symbol[
            "delta_seconds"
        ] is not None
        and nearest_same_symbol[
            "delta_seconds"
        ] <= MATCH_TOLERANCE_SECONDS
    ):
        classification = (
            "SAME_SYMBOL_WITHIN_TOLERANCE"
        )

    elif same_symbol:
        classification = (
            "SAME_SYMBOL_TIMESTAMP_MISMATCH"
        )

    elif nearest:
        classification = (
            "TIMESTAMP_NEARBY_DIFFERENT_SYMBOL"
        )

    else:
        classification = (
            "NO_COMPARABLE_TIMESTAMP"
        )

    return {
        "asset_symbol":
            feature["asset_symbol"],

        "asset_symbol_raw":
            feature["asset_symbol_raw"],

        "snapshot_timestamp":
            feature["snapshot_timestamp"],

        "feature_timestamp":
            feature["timestamp"],

        "observation_count":
            feature["observation_count"],

        "exact_matches":
            exact,

        "same_symbol_candidate_count":
            len(same_symbol),

        "nearest_same_symbol":
            nearest_same_symbol,

        "nearest_timestamp_candidates":
            nearest,

        "classification":
            classification,
    }


# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------

def build_forensic(
    contract: dict[str, Any],
    hunter_rows: list[sqlite3.Row],
) -> dict[str, Any]:

    features = extract_feature_identities(
        contract
    )

    analyses = []

    for feature in features:

        analyses.append(
            analyze_feature(
                feature,
                hunter_rows,
            )
        )

    summary = {
        "feature_identities":
            len(features),

        "hunter_rows":
            len(hunter_rows),

        "exact_matches":
            sum(
                1
                for item in analyses
                if item["classification"]
                == "EXACT_MATCH"
            ),

        "same_symbol_within_tolerance":
            sum(
                1
                for item in analyses
                if item["classification"]
                == "SAME_SYMBOL_WITHIN_TOLERANCE"
            ),

        "same_symbol_timestamp_mismatch":
            sum(
                1
                for item in analyses
                if item["classification"]
                == "SAME_SYMBOL_TIMESTAMP_MISMATCH"
            ),

        "nearby_different_symbol":
            sum(
                1
                for item in analyses
                if item["classification"]
                == "TIMESTAMP_NEARBY_DIFFERENT_SYMBOL"
            ),

        "no_comparable_timestamp":
            sum(
                1
                for item in analyses
                if item["classification"]
                == "NO_COMPARABLE_TIMESTAMP"
            ),

        "unmatched":
            sum(
                1
                for item in analyses
                if item["classification"]
                == "UNMATCHED"
            ),
    }

    return {
        "forensic":
            FORENSIC_VERSION,

        "mode":
            "READ_ONLY",

        "network":
            False,

        "signal_generation":
            False,

        "prediction":
            False,

        "trading_decision":
            False,

        "outcome_calculation":
            False,

        "feature_contract_modified":
            False,

        "database_modified":
            False,

        "match_tolerance_seconds":
            MATCH_TOLERANCE_SECONDS,

        "identity_rule":
            "asset_symbol + snapshot_timestamp",

        "comparison_rule":
            "hunter_signals.asset + hunter_signals.timestamp",

        "timestamp_policy":
            {
                "raw_values_preserved":
                    True,

                "naive_vs_naive":
                    "DIRECT_COMPARISON",

                "aware_vs_aware":
                    "UTC_COMPARISON",

                "aware_vs_naive":
                    "NOT_COMPARABLE",

                "normalization_for_matching":
                    False,
            },

        "feature_contract":
            str(FEATURE_CONTRACT_PATH),

        "summary":
            summary,

        "analyses":
            analyses,
    }


# -----------------------------------------------------------------------------
# HASH
# -----------------------------------------------------------------------------

def attach_hash(
    artifact: dict[str, Any],
) -> dict[str, Any]:

    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    artifact[
        "artifact_sha256"
    ] = digest

    return artifact


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main() -> None:

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> HUNTER "
        "TIMESTAMP / IDENTITY FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Feature Contract: {FEATURE_CONTRACT_PATH}"
    )

    print(
        "Mode            : READ ONLY"
    )

    print(
        "Network         : FORBIDDEN"
    )

    print(
        "Outcome         : NOT CALCULATED"
    )

    print(
        "Prediction      : FORBIDDEN"
    )

    print(
        "Decision        : FORBIDDEN"
    )

    print(
        f"Match Tolerance : "
        f"{MATCH_TOLERANCE_SECONDS} seconds"
    )

    print("-" * 90)

    contract = load_feature_contract()

    connection = connect_database()

    try:

        hunter_rows = load_hunter_rows(
            connection
        )

    finally:

        connection.close()

    artifact = build_forensic(
        contract,
        hunter_rows,
    )

    artifact = attach_hash(
        artifact
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summary = artifact[
        "summary"
    ]

    print("=" * 90)
    print(
        "FEATURE -> HUNTER IDENTITY FORENSIC"
    )
    print("=" * 90)

    print(
        "Feature identities                 : "
        f"{summary['feature_identities']}"
    )

    print(
        "Hunter rows                        : "
        f"{summary['hunter_rows']}"
    )

    print(
        "Exact matches                      : "
        f"{summary['exact_matches']}"
    )

    print(
        "Same symbol within tolerance       : "
        f"{summary['same_symbol_within_tolerance']}"
    )

    print(
        "Same symbol timestamp mismatch     : "
        f"{summary['same_symbol_timestamp_mismatch']}"
    )

    print(
        "Nearby timestamp different symbol  : "
        f"{summary['nearby_different_symbol']}"
    )

    print(
        "No comparable timestamp            : "
        f"{summary['no_comparable_timestamp']}"
    )

    print(
        "Unmatched                          : "
        f"{summary['unmatched']}"
    )

    print(
        f"Artifact                           : "
        f"{OUTPUT_PATH}"
    )

    print(
        f"SHA256                             : "
        f"{artifact['artifact_sha256']}"
    )

    print("=" * 90)

    if summary["exact_matches"] > 0:

        status = (
            "EXACT_FEATURE_HUNTER_IDENTITY_FOUND"
        )

    elif summary[
        "same_symbol_within_tolerance"
    ] > 0:

        status = (
            "TIMESTAMP_TOLERANCE_IDENTITY_FOUND"
        )

    elif summary[
        "same_symbol_timestamp_mismatch"
    ] > 0:

        status = (
            "SAME_SYMBOL_TIMESTAMP_MISMATCH"
        )

    else:

        status = (
            "FEATURE_HUNTER_IDENTITY_NOT_ESTABLISHED"
        )

    print(
        f"FORENSIC STATUS : {status}"
    )

    print(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    print(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()