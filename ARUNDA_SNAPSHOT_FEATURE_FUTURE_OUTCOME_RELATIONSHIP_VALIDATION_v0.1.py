# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> FUTURE OUTCOME RELATIONSHIP VALIDATION v0.1
# =============================================================================
#
# PURPOSE:
#   Validate the relationship between REAL snapshot features and REAL future
#   outcomes through the verified production identity path:
#
#       FEATURE CONTRACT
#           |
#           | asset_symbol + snapshot_timestamp
#           v
#       hunter_signals.asset + hunter_signals.timestamp
#           |
#           | hunter_signals.id
#           v
#       signal_outcomes.signal_id
#           |
#           v
#       FUTURE OUTCOME
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
#   SYNTHETIC OUTCOME
#   SYNTHETIC FEATURE
#   INTERPOLATION
#   FORWARD FILL
#   BACK FILL
#
# IMPORTANT:
#   This script DOES NOT establish predictive power.
#   It only validates whether real feature observations can be linked to
#   real future outcomes through the verified Hunter -> Outcome identity path.
# =============================================================================

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    r"\ARUNDA_SNAPSHOT_FEATURE_FUTURE_OUTCOME_RELATIONSHIP_VALIDATION_v0.1.json"
)


# -----------------------------------------------------------------------------
# CONTRACT
# -----------------------------------------------------------------------------

VALIDATION_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_FUTURE_OUTCOME_RELATIONSHIP_VALIDATION_v0.1"
)

MODE = "READ_ONLY"

MATCH_TOLERANCE_SECONDS = 120

ALLOWED_FEATURES = {
    "PRICE",
    "RSI",
    "EMA12",
    "EMA26",
    "MACD",
    "BOLLINGER",
    "VOLATILITY",
}

BLOCKED_FEATURES = {
    "ATR",
    "ADX",
}

OUTCOME_HORIZONS = (
    "5m",
    "15m",
    "30m",
    "60m",
)


# -----------------------------------------------------------------------------
# UTILITIES
# -----------------------------------------------------------------------------

def finite_number(
    value: Any,
) -> float | None:

    try:

        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (
        TypeError,
        ValueError,
    ):

        return None


def parse_timestamp(
    value: Any,
) -> datetime | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace(
        "Z",
        "+00:00",
    )

    try:

        dt = datetime.fromisoformat(
            text
        )

    except ValueError:

        return None

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def timestamp_distance_seconds(
    left: Any,
    right: Any,
) -> float | None:

    left_dt = parse_timestamp(
        left
    )

    right_dt = parse_timestamp(
        right
    )

    if (
        left_dt is None
        or right_dt is None
    ):
        return None

    return abs(
        (
            left_dt
            - right_dt
        ).total_seconds()
    )


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


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (
            table_name,
        ),
    ).fetchone()

    return row is not None


def get_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def require_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> None:

    if not table_exists(
        connection,
        table_name,
    ):

        raise RuntimeError(
            f"Required table not found: {table_name}"
        )


def require_columns(
    actual_columns: list[str],
    required: tuple[str, ...],
    table_name: str,
) -> None:

    actual = {
        column.lower()
        for column in actual_columns
    }

    missing = [
        column
        for column in required
        if column.lower()
        not in actual
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

    return artifact


def validate_feature_contract_identity(
    artifact: dict[str, Any],
) -> None:

    if artifact.get(
        "mode"
    ) != "READ_ONLY":

        raise RuntimeError(
            "Feature Contract is not READ_ONLY."
        )

    if not artifact.get(
        "records"
    ):

        raise RuntimeError(
            "Feature Contract contains no records."
        )


# -----------------------------------------------------------------------------
# HUNTER SIGNAL DISCOVERY
# -----------------------------------------------------------------------------

def discover_hunter_schema(
    connection: sqlite3.Connection,
) -> dict[str, str]:

    require_table(
        connection,
        "hunter_signals",
    )

    columns = get_columns(
        connection,
        "hunter_signals",
    )

    normalized = {
        column.lower(): column
        for column in columns
    }

    required = (
        "id",
        "asset",
        "timestamp",
    )

    missing = [
        column
        for column in required
        if column not in normalized
    ]

    if missing:

        raise RuntimeError(
            "hunter_signals identity columns missing: "
            + ", ".join(missing)
        )

    return {
        "id": normalized["id"],
        "asset": normalized["asset"],
        "timestamp": normalized["timestamp"],
    }


# -----------------------------------------------------------------------------
# OUTCOME SCHEMA
# -----------------------------------------------------------------------------

def discover_outcome_schema(
    connection: sqlite3.Connection,
) -> dict[str, str | None]:

    require_table(
        connection,
        "signal_outcomes",
    )

    columns = get_columns(
        connection,
        "signal_outcomes",
    )

    normalized = {
        column.lower(): column
        for column in columns
    }

    required = (
        "id",
        "signal_id",
    )

    missing = [
        column
        for column in required
        if column not in normalized
    ]

    if missing:

        raise RuntimeError(
            "signal_outcomes identity columns missing: "
            + ", ".join(missing)
        )

    result: dict[str, str | None] = {
        "id": normalized["id"],
        "signal_id": normalized["signal_id"],
        "timestamp": normalized.get(
            "timestamp"
        ),
        "entry_timestamp": normalized.get(
            "entry_timestamp"
        ),
        "entry_price": normalized.get(
            "entry_price"
        ),
        "price_5m": normalized.get(
            "price_5m"
        ),
        "price_15m": normalized.get(
            "price_15m"
        ),
        "price_30m": normalized.get(
            "price_30m"
        ),
        "price_60m": normalized.get(
            "price_60m"
        ),
        "return_5m": normalized.get(
            "return_5m"
        ),
        "return_15m": normalized.get(
            "return_15m"
        ),
        "return_30m": normalized.get(
            "return_30m"
        ),
        "return_60m": normalized.get(
            "return_60m"
        ),
        "outcome_5m": normalized.get(
            "outcome_5m"
        ),
        "outcome_15m": normalized.get(
            "outcome_15m"
        ),
        "outcome_30m": normalized.get(
            "outcome_30m"
        ),
        "outcome_60m": normalized.get(
            "outcome_60m"
        ),
        "outcome": normalized.get(
            "outcome"
        ),
    }

    return result


# -----------------------------------------------------------------------------
# LOAD HUNTER SIGNALS
# -----------------------------------------------------------------------------

def load_hunter_signals(
    connection: sqlite3.Connection,
    hunter_schema: dict[str, str],
) -> list[sqlite3.Row]:

    hunter_id = hunter_schema["id"]
    hunter_asset = hunter_schema["asset"]
    hunter_timestamp = hunter_schema["timestamp"]

    query = f"""
        SELECT
            {hunter_id} AS hunter_id,
            {hunter_asset} AS hunter_asset,
            {hunter_timestamp} AS hunter_timestamp
        FROM hunter_signals
        WHERE {hunter_asset} IS NOT NULL
          AND {hunter_timestamp} IS NOT NULL
        ORDER BY {hunter_timestamp} ASC
    """

    return connection.execute(
        query
    ).fetchall()


# -----------------------------------------------------------------------------
# LOAD REAL OUTCOMES THROUGH SIGNAL_ID
# -----------------------------------------------------------------------------

def load_outcomes(
    connection: sqlite3.Connection,
    outcome_schema: dict[str, str | None],
) -> list[sqlite3.Row]:

    outcome_id = outcome_schema["id"]
    signal_id = outcome_schema["signal_id"]

    select_columns = [
        f"{outcome_id} AS outcome_id",
        f"{signal_id} AS signal_id",
    ]

    for logical_name in (
        "timestamp",
        "entry_timestamp",
        "entry_price",
        "price_5m",
        "price_15m",
        "price_30m",
        "price_60m",
        "return_5m",
        "return_15m",
        "return_30m",
        "return_60m",
        "outcome_5m",
        "outcome_15m",
        "outcome_30m",
        "outcome_60m",
        "outcome",
    ):

        column = outcome_schema.get(
            logical_name
        )

        if column:

            select_columns.append(
                f"{column} AS {logical_name}"
            )

        else:

            select_columns.append(
                f"NULL AS {logical_name}"
            )

    query = f"""
        SELECT
            {", ".join(select_columns)}
        FROM signal_outcomes
        WHERE {signal_id} IS NOT NULL
        ORDER BY {outcome_id} ASC
    """

    return connection.execute(
        query
    ).fetchall()


# -----------------------------------------------------------------------------
# BUILD HUNTER -> OUTCOME PATH
# -----------------------------------------------------------------------------

def build_outcome_path(
    hunter_rows: list[sqlite3.Row],
    outcome_rows: list[sqlite3.Row],
) -> tuple[
    dict[Any, sqlite3.Row],
    dict[Any, list[sqlite3.Row]],
]:

    hunter_by_id = {
        row["hunter_id"]: row
        for row in hunter_rows
    }

    outcomes_by_hunter: dict[
        Any,
        list[sqlite3.Row],
    ] = {}

    for outcome in outcome_rows:

        hunter_id = outcome[
            "signal_id"
        ]

        if hunter_id not in hunter_by_id:
            continue

        outcomes_by_hunter.setdefault(
            hunter_id,
            [],
        ).append(
            outcome
        )

    return (
        hunter_by_id,
        outcomes_by_hunter,
    )


# -----------------------------------------------------------------------------
# FEATURE -> HUNTER MATCH
# -----------------------------------------------------------------------------

def find_best_hunter(
    asset_symbol: str,
    snapshot_timestamp: str,
    hunter_rows: list[sqlite3.Row],
) -> tuple[
    sqlite3.Row | None,
    float | None,
]:

    best_row = None
    best_distance = None

    target_asset = (
        str(asset_symbol)
        .strip()
        .upper()
    )

    for hunter in hunter_rows:

        hunter_asset = str(
            hunter["hunter_asset"]
        ).strip().upper()

        if hunter_asset != target_asset:
            continue

        distance = timestamp_distance_seconds(
            snapshot_timestamp,
            hunter["hunter_timestamp"],
        )

        if distance is None:
            continue

        if (
            best_distance is None
            or distance < best_distance
        ):

            best_row = hunter
            best_distance = distance

    if (
        best_row is None
        or best_distance is None
    ):

        return None, None

    if (
        best_distance
        > MATCH_TOLERANCE_SECONDS
    ):

        return None, best_distance

    return (
        best_row,
        best_distance,
    )


# -----------------------------------------------------------------------------
# OUTCOME OBSERVATION EXTRACTION
# -----------------------------------------------------------------------------

def extract_outcome_observations(
    outcomes: list[sqlite3.Row],
) -> dict[str, int]:

    observations = {
        "5m": 0,
        "15m": 0,
        "30m": 0,
        "60m": 0,
    }

    for outcome in outcomes:

        for horizon in OUTCOME_HORIZONS:

            return_key = (
                f"return_{horizon}"
            )

            price_key = (
                f"price_{horizon}"
            )

            outcome_key = (
                f"outcome_{horizon}"
            )

            if (
                finite_number(
                    outcome[return_key]
                )
                is not None
                or finite_number(
                    outcome[price_key]
                )
                is not None
                or outcome[outcome_key]
                is not None
            ):

                observations[
                    horizon
                ] += 1

    return observations


# -----------------------------------------------------------------------------
# FEATURE RELATIONSHIP RECORD
# -----------------------------------------------------------------------------

def build_feature_relationship(
    feature: dict[str, Any],
    hunter: sqlite3.Row,
    hunter_distance: float,
    outcomes: list[sqlite3.Row],
) -> dict[str, Any]:

    feature_name = feature[
        "feature_name"
    ]

    value = feature.get(
        "value"
    )

    observations = (
        extract_outcome_observations(
            outcomes
        )
    )

    total_observations = sum(
        observations.values()
    )

    return {

        "feature_name":
            feature_name,

        "asset_symbol":
            feature["asset_symbol"],

        "snapshot_timestamp":
            feature["snapshot_timestamp"],

        "feature_value":
            value,

        "feature_source":
            feature.get("source"),

        "feature_source_engine_version":
            feature.get(
                "source_engine_version"
            ),

        "feature_eligibility_status":
            feature.get(
                "eligibility_status"
            ),

        "hunter_signal_id":
            hunter["hunter_id"],

        "hunter_asset":
            hunter["hunter_asset"],

        "hunter_timestamp":
            hunter["hunter_timestamp"],

        "feature_to_hunter_distance_seconds":
            hunter_distance,

        "match_tolerance_seconds":
            MATCH_TOLERANCE_SECONDS,

        "linked_outcome_count":
            len(outcomes),

        "outcome_observations":
            observations,

        "total_outcome_observations":
            total_observations,

        "relationship_status":
            (
                "RELATIONSHIP_READY"
                if total_observations > 0
                else "OUTCOME_UNAVAILABLE"
            ),

        "predictive_claim":
            "NOT_ESTABLISHED",

    }


# -----------------------------------------------------------------------------
# VALIDATION
# -----------------------------------------------------------------------------

def validate_artifact(
    artifact: dict[str, Any],
) -> None:

    assert artifact[
        "mode"
    ] == MODE

    assert artifact[
        "predictive_claim"
    ] == "NOT_ESTABLISHED"

    assert artifact[
        "database_write"
    ] is False

    assert artifact[
        "network"
    ] is False

    assert artifact[
        "signal_generation"
    ] is False

    assert artifact[
        "prediction"
    ] is False

    assert artifact[
        "trading_decision"
    ] is False

    for relationship in artifact[
        "relationships"
    ]:

        assert (
            relationship[
                "feature_name"
            ]
            not in BLOCKED_FEATURES
        )


# -----------------------------------------------------------------------------
# CONTRACT BUILD
# -----------------------------------------------------------------------------

def build_validation(
    connection: sqlite3.Connection,
    feature_contract: dict[str, Any],
) -> dict[str, Any]:

    hunter_schema = (
        discover_hunter_schema(
            connection
        )
    )

    outcome_schema = (
        discover_outcome_schema(
            connection
        )
    )

    hunter_rows = load_hunter_signals(
        connection,
        hunter_schema,
    )

    outcome_rows = load_outcomes(
        connection,
        outcome_schema,
    )

    (
        hunter_by_id,
        outcomes_by_hunter,
    ) = build_outcome_path(
        hunter_rows,
        outcome_rows,
    )

    relationships = []

    feature_records = (
        feature_contract[
            "records"
        ]
    )

    feature_record_count = 0
    blocked_features = 0
    feature_hunter_matches = 0
    feature_hunter_unmatched = 0
    linked_outcome_records = 0
    outcome_observations = 0

    horizon_counts = {
        horizon: 0
        for horizon in OUTCOME_HORIZONS
    }

    for record in feature_records:

        feature_record_count += 1

        symbol = str(
            record[
                "asset_symbol"
            ]
        )

        timestamp = str(
            record[
                "snapshot_timestamp"
            ]
        )

        hunter, distance = (
            find_best_hunter(
                symbol,
                timestamp,
                hunter_rows,
            )
        )

        for feature in record[
            "features"
        ]:

            feature_name = feature[
                "feature_name"
            ]

            if feature_name in (
                BLOCKED_FEATURES
            ):

                blocked_features += 1
                continue

            if feature_name not in (
                ALLOWED_FEATURES
            ):

                continue

            if (
                hunter is None
                or distance is None
            ):

                feature_hunter_unmatched += 1

                relationships.append(
                    {
                        "feature_name":
                            feature_name,

                        "asset_symbol":
                            symbol,

                        "snapshot_timestamp":
                            timestamp,

                        "feature_value":
                            feature.get(
                                "value"
                            ),

                        "feature_eligibility_status":
                            feature.get(
                                "eligibility_status"
                            ),

                        "relationship_status":
                            "FEATURE_TO_HUNTER_UNMATCHED",

                        "hunter_signal_id":
                            None,

                        "feature_to_hunter_distance_seconds":
                            None,

                        "linked_outcome_count":
                            0,

                        "total_outcome_observations":
                            0,

                        "predictive_claim":
                            "NOT_ESTABLISHED",
                    }
                )

                continue

            feature_hunter_matches += 1

            hunter_id = hunter[
                "hunter_id"
            ]

            linked_outcomes = (
                outcomes_by_hunter.get(
                    hunter_id,
                    [],
                )
            )

            if linked_outcomes:
                linked_outcome_records += 1

            relationship = (
                build_feature_relationship(
                    feature,
                    hunter,
                    distance,
                    linked_outcomes,
                )
            )

            relationships.append(
                relationship
            )

            observation_map = (
                relationship[
                    "outcome_observations"
                ]
            )

            for horizon in OUTCOME_HORIZONS:

                horizon_counts[
                    horizon
                ] += observation_map[
                    horizon
                ]

            outcome_observations += (
                relationship[
                    "total_outcome_observations"
                ]
            )

    relationship_ready = sum(
        1
        for relationship
        in relationships
        if relationship[
            "relationship_status"
        ]
        == "RELATIONSHIP_READY"
    )

    return {

        "validation":
            VALIDATION_VERSION,

        "mode":
            MODE,

        "database":
            str(DB_PATH),

        "feature_contract":
            str(
                FEATURE_CONTRACT_PATH
            ),

        "network":
            False,

        "exchange":
            False,

        "database_write":
            False,

        "signal_generation":
            False,

        "prediction":
            False,

        "trading_decision":
            False,

        "predictive_claim":
            "NOT_ESTABLISHED",

        "identity_path":
            {
                "feature":
                    "asset_symbol + snapshot_timestamp",

                "feature_to_hunter":
                    "hunter_signals.asset + hunter_signals.timestamp",

                "hunter_identity":
                    "hunter_signals.id",

                "outcome_identity":
                    "signal_outcomes.signal_id",

                "path":
                    (
                        "FEATURE -> "
                        "hunter_signals -> "
                        "hunter_signals.id -> "
                        "signal_outcomes.signal_id -> "
                        "signal_outcomes"
                    ),
            },

        "match_policy":
            {
                "asset_match":
                    "CASE_INSENSITIVE_EXACT",

                "timestamp_match":
                    "NEAREST_REAL_HUNTER_TIMESTAMP",

                "tolerance_seconds":
                    MATCH_TOLERANCE_SECONDS,

                "synthetic_timestamp":
                    False,

                "interpolation":
                    False,

                "forward_fill":
                    False,

                "back_fill":
                    False,
            },

        "hunter_schema":
            hunter_schema,

        "outcome_schema":
            outcome_schema,

        "statistics":
            {
                "feature_records_analyzed":
                    feature_record_count,

                "blocked_features":
                    blocked_features,

                "feature_to_hunter_matches":
                    feature_hunter_matches,

                "feature_to_hunter_unmatched":
                    feature_hunter_unmatched,

                "linked_hunter_outcome_records":
                    linked_outcome_records,

                "outcome_observations":
                    outcome_observations,

                "relationship_ready":
                    relationship_ready,

                "horizon_observations":
                    horizon_counts,

                "hunter_rows":
                    len(hunter_rows),

                "outcome_rows":
                    len(outcome_rows),

                "outcome_rows_with_verified_hunter_link":
                    sum(
                        len(outcomes)
                        for outcomes
                        in outcomes_by_hunter.values()
                    ),

                "outcome_rows_orphaned_from_hunter":
                    len(outcome_rows)
                    -
                    sum(
                        len(outcomes)
                        for outcomes
                        in outcomes_by_hunter.values()
                    ),
            },

        "relationships":
            relationships,
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
        canonical.encode(
            "utf-8"
        )
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
        "ARUNDA SNAPSHOT FEATURE -> FUTURE OUTCOME "
        "RELATIONSHIP VALIDATION v0.1"
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
        "Signal          : FORBIDDEN"
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

    feature_contract = (
        load_feature_contract()
    )

    validate_feature_contract_identity(
        feature_contract
    )

    connection = connect_database()

    try:

        artifact = build_validation(
            connection,
            feature_contract,
        )

    finally:

        connection.close()

    validate_artifact(
        artifact
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

    stats = artifact[
        "statistics"
    ]

    print("=" * 90)
    print(
        "FEATURE -> FUTURE OUTCOME VALIDATION"
    )
    print("=" * 90)

    print(
        "Feature Records Analyzed : "
        f"{stats['feature_records_analyzed']}"
    )

    print(
        "Blocked Features         : "
        f"{stats['blocked_features']}"
    )

    print(
        "Feature -> Hunter Matches: "
        f"{stats['feature_to_hunter_matches']}"
    )

    print(
        "Feature -> Hunter Unmatched: "
        f"{stats['feature_to_hunter_unmatched']}"
    )

    print(
        "Hunter Outcome Links     : "
        f"{stats['linked_hunter_outcome_records']}"
    )

    print(
        "Outcome Observations     : "
        f"{stats['outcome_observations']}"
    )

    print(
        "Relationships Ready      : "
        f"{stats['relationship_ready']}"
    )

    print(
        "5m Observations          : "
        f"{stats['horizon_observations']['5m']}"
    )

    print(
        "15m Observations         : "
        f"{stats['horizon_observations']['15m']}"
    )

    print(
        "30m Observations         : "
        f"{stats['horizon_observations']['30m']}"
    )

    print(
        "60m Observations         : "
        f"{stats['horizon_observations']['60m']}"
    )

    print(
        "Hunter Rows              : "
        f"{stats['hunter_rows']}"
    )

    print(
        "Outcome Rows             : "
        f"{stats['outcome_rows']}"
    )

    print(
        "Verified Hunter Links    : "
        f"{stats['outcome_rows_with_verified_hunter_link']}"
    )

    print(
        "Orphaned Outcome Rows    : "
        f"{stats['outcome_rows_orphaned_from_hunter']}"
    )

    print(
        f"Artifact                 : {OUTPUT_PATH}"
    )

    print(
        "SHA256                   : "
        f"{artifact['artifact_sha256']}"
    )

    print("=" * 90)

    if stats[
        "relationship_ready"
    ] > 0:

        print(
            "RELATIONSHIP STATUS      : "
            "REAL_OUTCOME_RELATIONSHIP_ESTABLISHED"
        )

    else:

        print(
            "RELATIONSHIP STATUS      : "
            "INSUFFICIENT_EVIDENCE"
        )

    print(
        "PREDICTIVE CLAIM         : "
        "NOT_ESTABLISHED"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()