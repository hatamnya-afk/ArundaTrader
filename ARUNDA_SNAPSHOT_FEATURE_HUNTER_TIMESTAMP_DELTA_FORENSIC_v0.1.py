from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> HUNTER TIMESTAMP DELTA FORENSIC v0.1
#
# PURPOSE:
#   Measure the REAL timestamp delta between:
#
#       Feature Contract
#           asset_symbol + snapshot_timestamp
#
#       and
#
#       hunter_signals
#           asset + timestamp
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
#   RELATIONSHIP CALCULATION
#
# IMPORTANT:
#   This script does NOT establish a matching rule.
#   It measures the observed timestamp difference only.
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
    r"\ARUNDA_SNAPSHOT_FEATURE_HUNTER_TIMESTAMP_DELTA_FORENSIC_v0.1.json"
)


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

FORENSIC_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_HUNTER_TIMESTAMP_DELTA_FORENSIC_v0.1"
)


# -----------------------------------------------------------------------------
# UTILITIES
# -----------------------------------------------------------------------------

def parse_timestamp(
    value: Any,
) -> datetime | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    candidate = text

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(
            candidate
        )

    except ValueError:
        return None


def is_aware(
    dt: datetime,
) -> bool:

    return (
        dt.tzinfo is not None
        and dt.utcoffset() is not None
    )


def compare_timestamps(
    feature_dt: datetime,
    hunter_dt: datetime,
) -> float | None:

    feature_aware = is_aware(
        feature_dt
    )

    hunter_aware = is_aware(
        hunter_dt
    )

    # Do not invent timezone semantics.
    if feature_aware != hunter_aware:
        return None

    if feature_aware:

        feature_dt = feature_dt.astimezone(
            timezone.utc
        )

        hunter_dt = hunter_dt.astimezone(
            timezone.utc
        )

    return abs(
        (
            feature_dt
            - hunter_dt
        ).total_seconds()
    )


def normalize_symbol(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip().upper()


def timestamp_info(
    value: Any,
) -> dict[str, Any]:

    dt = parse_timestamp(
        value
    )

    if dt is None:

        return {
            "raw":
                None if value is None
                else str(value),

            "parseable":
                False,

            "timezone_aware":
                None,

            "utc":
                None,
        }

    aware = is_aware(
        dt
    )

    utc = None

    if aware:

        utc = (
            dt.astimezone(
                timezone.utc
            ).isoformat()
        )

    return {
        "raw":
            str(value),

        "parseable":
            True,

        "timezone_aware":
            aware,

        "utc":
            utc,
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
            "Invalid Feature Contract."
        )

    return artifact


def extract_feature_identities(
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:

    identities = []

    for record in artifact.get(
        "records",
        [],
    ):

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
                    normalize_symbol(
                        symbol
                    ),

                "asset_symbol_raw":
                    str(symbol),

                "snapshot_timestamp":
                    str(timestamp),

                "observation_count":
                    record.get(
                        "observation_count"
                    ),
            }
        )

    return identities


# -----------------------------------------------------------------------------
# HUNTER SIGNALS
# -----------------------------------------------------------------------------

def load_hunter_rows(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:

    rows = connection.execute(
        """
        SELECT
            id,
            asset,
            timestamp
        FROM hunter_signals
        ORDER BY timestamp ASC, id ASC
        """
    ).fetchall()

    return rows


# -----------------------------------------------------------------------------
# SAME-SYMBOL DELTA
# -----------------------------------------------------------------------------

def find_nearest_same_symbol(
    feature: dict[str, Any],
    hunter_rows: list[sqlite3.Row],
) -> dict[str, Any] | None:

    feature_dt = parse_timestamp(
        feature[
            "snapshot_timestamp"
        ]
    )

    if feature_dt is None:
        return None

    candidates = []

    for row in hunter_rows:

        hunter_symbol = normalize_symbol(
            row["asset"]
        )

        if hunter_symbol != feature[
            "asset_symbol"
        ]:
            continue

        hunter_timestamp = str(
            row["timestamp"]
        )

        hunter_dt = parse_timestamp(
            hunter_timestamp
        )

        if hunter_dt is None:
            continue

        delta = compare_timestamps(
            feature_dt,
            hunter_dt,
        )

        if delta is None:
            continue

        candidates.append(
            {
                "hunter_id":
                    row["id"],

                "hunter_asset":
                    row["asset"],

                "hunter_timestamp":
                    hunter_timestamp,

                "feature_timestamp":
                    feature[
                        "snapshot_timestamp"
                    ],

                "delta_seconds":
                    delta,

                "delta_minutes":
                    delta / 60.0,

                "delta_hours":
                    delta / 3600.0,

                "feature_timestamp_info":
                    timestamp_info(
                        feature[
                            "snapshot_timestamp"
                        ]
                    ),

                "hunter_timestamp_info":
                    timestamp_info(
                        hunter_timestamp
                    ),
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item:
            item["delta_seconds"]
    )

    return candidates[0]


# -----------------------------------------------------------------------------
# DELTA CLASSIFICATION
# -----------------------------------------------------------------------------

def classify_delta(
    delta_seconds: float | None,
) -> str:

    if delta_seconds is None:
        return "NOT_COMPARABLE"

    if delta_seconds == 0:
        return "EXACT"

    if delta_seconds <= 10:
        return "0_10_SECONDS"

    if delta_seconds <= 30:
        return "10_30_SECONDS"

    if delta_seconds <= 60:
        return "30_60_SECONDS"

    if delta_seconds <= 120:
        return "60_120_SECONDS"

    if delta_seconds <= 300:
        return "2_5_MINUTES"

    if delta_seconds <= 600:
        return "5_10_MINUTES"

    if delta_seconds <= 1800:
        return "10_30_MINUTES"

    if delta_seconds <= 3600:
        return "30_60_MINUTES"

    if delta_seconds <= 7200:
        return "1_2_HOURS"

    if delta_seconds <= 21600:
        return "2_6_HOURS"

    if delta_seconds <= 43200:
        return "6_12_HOURS"

    if delta_seconds <= 86400:
        return "12_24_HOURS"

    return "OVER_24_HOURS"


# -----------------------------------------------------------------------------
# FORENSIC
# -----------------------------------------------------------------------------

def build_forensic(
    feature_identities: list[dict[str, Any]],
    hunter_rows: list[sqlite3.Row],
) -> dict[str, Any]:

    comparisons = []

    for feature in feature_identities:

        nearest = find_nearest_same_symbol(
            feature,
            hunter_rows,
        )

        if nearest is None:

            comparisons.append(
                {
                    "asset_symbol":
                        feature[
                            "asset_symbol"
                        ],

                    "feature_timestamp":
                        feature[
                            "snapshot_timestamp"
                        ],

                    "status":
                        "NO_SAME_SYMBOL_HUNTER_ROW",
                }
            )

            continue

        delta = nearest[
            "delta_seconds"
        ]

        nearest[
            "delta_classification"
        ] = classify_delta(
            delta
        )

        comparisons.append(
            {
                "asset_symbol":
                    feature[
                        "asset_symbol"
                    ],

                "feature_timestamp":
                    feature[
                        "snapshot_timestamp"
                    ],

                "hunter_id":
                    nearest[
                        "hunter_id"
                    ],

                "hunter_timestamp":
                    nearest[
                        "hunter_timestamp"
                    ],

                "delta_seconds":
                    nearest[
                        "delta_seconds"
                    ],

                "delta_minutes":
                    nearest[
                        "delta_minutes"
                    ],

                "delta_hours":
                    nearest[
                        "delta_hours"
                    ],

                "delta_classification":
                    nearest[
                        "delta_classification"
                    ],

                "feature_timestamp_info":
                    nearest[
                        "feature_timestamp_info"
                    ],

                "hunter_timestamp_info":
                    nearest[
                        "hunter_timestamp_info"
                    ],
            }
        )

    comparable = [
        item
        for item in comparisons
        if "delta_seconds" in item
    ]

    deltas = [
        item["delta_seconds"]
        for item in comparable
    ]

    summary = {
        "feature_identities":
            len(feature_identities),

        "hunter_rows":
            len(hunter_rows),

        "comparable_pairs":
            len(comparable),

        "non_comparable_pairs":
            len(comparisons)
            - len(comparable),

        "exact_zero_delta":
            sum(
                1
                for value in deltas
                if value == 0
            ),

        "within_120_seconds":
            sum(
                1
                for value in deltas
                if value <= 120
            ),

        "within_300_seconds":
            sum(
                1
                for value in deltas
                if value <= 300
            ),

        "within_600_seconds":
            sum(
                1
                for value in deltas
                if value <= 600
            ),

        "minimum_delta_seconds":
            min(deltas)
            if deltas
            else None,

        "maximum_delta_seconds":
            max(deltas)
            if deltas
            else None,

        "mean_delta_seconds":
            (
                sum(deltas)
                / len(deltas)
            )
            if deltas
            else None,

        "median_delta_seconds":
            (
                sorted(deltas)[
                    len(deltas) // 2
                ]
            )
            if deltas
            else None,
    }

    histogram = {}

    for item in comparable:

        classification = item[
            "delta_classification"
        ]

        histogram[
            classification
        ] = histogram.get(
            classification,
            0,
        ) + 1

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

        "relationship_calculation":
            False,

        "feature_contract_modified":
            False,

        "database_modified":
            False,

        "identity_rule":
            "asset_symbol + snapshot_timestamp",

        "hunter_identity_rule":
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

                "matching_rule_established":
                    False,
            },

        "feature_contract":
            str(
                FEATURE_CONTRACT_PATH
            ),

        "summary":
            summary,

        "delta_histogram":
            histogram,

        "comparisons":
            comparisons,
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
        "TIMESTAMP DELTA FORENSIC v0.1"
    )

    print("=" * 90)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Feature Contract: "
        f"{FEATURE_CONTRACT_PATH}"
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
        "Relationship    : NOT CALCULATED"
    )

    print("-" * 90)

    contract = load_feature_contract()

    features = extract_feature_identities(
        contract
    )

    connection = connect_database()

    try:

        hunter_rows = load_hunter_rows(
            connection
        )

    finally:

        connection.close()

    artifact = build_forensic(
        features,
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
        "TIMESTAMP DELTA FORENSIC"
    )

    print("=" * 90)

    print(
        "Feature identities       : "
        f"{summary['feature_identities']}"
    )

    print(
        "Hunter rows              : "
        f"{summary['hunter_rows']}"
    )

    print(
        "Comparable pairs         : "
        f"{summary['comparable_pairs']}"
    )

    print(
        "Non-comparable pairs     : "
        f"{summary['non_comparable_pairs']}"
    )

    print(
        "Exact zero delta         : "
        f"{summary['exact_zero_delta']}"
    )

    print(
        "Within 120s              : "
        f"{summary['within_120_seconds']}"
    )

    print(
        "Within 300s              : "
        f"{summary['within_300_seconds']}"
    )

    print(
        "Within 600s              : "
        f"{summary['within_600_seconds']}"
    )

    print(
        "Minimum delta (sec)      : "
        f"{summary['minimum_delta_seconds']}"
    )

    print(
        "Maximum delta (sec)      : "
        f"{summary['maximum_delta_seconds']}"
    )

    print(
        "Mean delta (sec)        : "
        f"{summary['mean_delta_seconds']}"
    )

    print(
        "Median delta (sec)      : "
        f"{summary['median_delta_seconds']}"
    )

    print("-" * 90)

    print(
        "DELTA HISTOGRAM"
    )

    print("-" * 90)

    for key, value in sorted(
        artifact[
            "delta_histogram"
        ].items()
    ):

        print(
            f"{key:30s}: {value}"
        )

    print("-" * 90)

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        "SHA256   : "
        f"{artifact['artifact_sha256']}"
    )

    print("=" * 90)

    if (
        summary[
            "comparable_pairs"
        ]
        == 0
    ):

        status = (
            "TIMESTAMP_DELTA_NOT_ESTABLISHED"
        )

    elif (
        summary[
            "exact_zero_delta"
        ]
        == summary[
            "comparable_pairs"
        ]
    ):

        status = (
            "EXACT_TIMESTAMP_IDENTITY"
        )

    elif (
        summary[
            "within_120_seconds"
        ]
        == summary[
            "comparable_pairs"
        ]
    ):

        status = (
            "SUB_120_SECOND_DELTA"
        )

    else:

        status = (
            "TIMESTAMP_DELTA_ESTABLISHED"
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