from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA SNAPSHOT FEATURE CONTRACT v0.1
# =============================================================================
#
# PURPOSE:
#   MARKET DATA -> SNAPSHOT FEATURE CONTRACT
#
# MODE:
#   READ ONLY
#
# FORBIDDEN:
#   DB WRITE
#   NETWORK
#   EXCHANGE
#   SIGNAL
#   PREDICTION
#   TRADING DECISION
#   SYNTHETIC OHLC
#   INTERPOLATION
#   FORWARD FILL
#   BACK FILL
#
# IMPORTANT:
#   CMC SNAPSHOT observations are NOT genuine fixed-timeframe candles.
#   Indicator periods are OBSERVATION COUNTS.
#
#   This contract consumes real upstream feature output where available.
#   EMA12 / EMA26 are reconstructed ONLY from the real CMC snapshot close
#   observation series because the current market_data schema does not store
#   EMA12 / EMA26 as independent columns.
#
#   No OHLC reconstruction is performed.
# =============================================================================


# -----------------------------------------------------------------------------
# PATHS
# -----------------------------------------------------------------------------

DB_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

OUTPUT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)


# -----------------------------------------------------------------------------
# CONTRACT
# -----------------------------------------------------------------------------

CONTRACT_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1"
)

TIMEFRAME = "SNAPSHOT"

SNAPSHOT_SOURCE = "COINMARKETCAP"

HISTORY_WINDOW = 150

MIN_HISTORY = 60


# -----------------------------------------------------------------------------
# ALLOWED / BLOCKED
# -----------------------------------------------------------------------------

ALLOWED_FEATURES = (
    "PRICE",
    "RSI",
    "EMA12",
    "EMA26",
    "MACD",
    "BOLLINGER",
    "VOLATILITY",
)

BLOCKED_FEATURES = (
    "ATR",
    "ADX",
)


# -----------------------------------------------------------------------------
# FEATURE RULES
# -----------------------------------------------------------------------------

FEATURE_RULES = {

    "PRICE": {
        "temporal_semantics":
            "POINT_OBSERVATION",

        "calculation_semantics":
            "Latest genuine CMC snapshot price. "
            "No candle reconstruction.",

        "downstream_safe_representation":
            "numeric_point_observation",

        "caveat":
            "Snapshot price. Must not be represented "
            "as a fixed-timeframe candle close.",
    },

    "RSI": {
        "temporal_semantics":
            "OBSERVATION_COUNT",

        "calculation_semantics":
            "Upstream RSI14 calculated over snapshot observations.",

        "downstream_safe_representation":
            "numeric_observation_count_based",

        "caveat":
            "RSI period is an observation count, "
            "not guaranteed elapsed time.",
    },

    "EMA12": {
        "temporal_semantics":
            "OBSERVATION_COUNT",

        "calculation_semantics":
            "EMA12 calculated over real CMC snapshot close observations.",

        "downstream_safe_representation":
            "numeric_observation_count_based",

        "caveat":
            "EMA12 is observation-count based. "
            "The current upstream schema does not persist EMA12 "
            "as an independent column.",
    },

    "EMA26": {
        "temporal_semantics":
            "OBSERVATION_COUNT",

        "calculation_semantics":
            "EMA26 calculated over real CMC snapshot close observations.",

        "downstream_safe_representation":
            "numeric_observation_count_based",

        "caveat":
            "EMA26 is observation-count based. "
            "The current upstream schema does not persist EMA26 "
            "as an independent column.",
    },

    "MACD": {
        "temporal_semantics":
            "OBSERVATION_COUNT",

        "calculation_semantics":
            "Upstream MACD derived from snapshot observations.",

        "downstream_safe_representation":
            "structured_numeric_observation_count_based",

        "caveat":
            "MACD uses observation counts, not guaranteed elapsed-time periods.",
    },

    "BOLLINGER": {
        "temporal_semantics":
            "OBSERVATION_COUNT",

        "calculation_semantics":
            "Upstream Bollinger representation derived from snapshot observations.",

        "downstream_safe_representation":
            "structured_numeric_observation_count_based",

        "caveat":
            "Bollinger period is observation-count based.",
    },

    "VOLATILITY": {
        "temporal_semantics":
            "OBSERVATION_COUNT",

        "calculation_semantics":
            "Upstream return-based volatility over snapshot observations.",

        "downstream_safe_representation":
            "numeric_observation_count_based",

        "caveat":
            "Irregular snapshot spacing limits elapsed-time interpretation.",
    },

    "ATR": {
        "temporal_semantics":
            "UNSUPPORTED",

        "calculation_semantics":
            "NOT_CALCULATED",

        "downstream_safe_representation":
            "BLOCKED",

        "caveat":
            "Genuine OHLC high/low structure is unavailable.",
    },

    "ADX": {
        "temporal_semantics":
            "UNSUPPORTED",

        "calculation_semantics":
            "NOT_CALCULATED",

        "downstream_safe_representation":
            "BLOCKED",

        "caveat":
            "ADX requires genuine OHLC directional movement.",
    },
}


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


def get_table_columns(
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


def require_real_schema(
    columns: list[str],
) -> None:

    required = {
        "symbol",
        "timestamp",
        "timeframe",
        "close",
        "source",
        "engine_version",
        "rsi14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "volatility",
    }

    missing = sorted(
        required.difference(
            columns
        )
    )

    if missing:

        raise RuntimeError(
            "Real market_data schema is missing required "
            "upstream fields: "
            + ", ".join(missing)
        )


# -----------------------------------------------------------------------------
# EMA
# -----------------------------------------------------------------------------

def ema(
    values: list[float],
    period: int,
) -> float | None:

    if len(values) < period:

        return None

    multiplier = (
        2.0 / (period + 1.0)
    )

    result = (
        sum(values[:period])
        / period
    )

    for value in values[period:]:

        result = (
            (
                value - result
            )
            * multiplier
        ) + result

    return result


# -----------------------------------------------------------------------------
# REAL SCHEMA INSPECTION
# -----------------------------------------------------------------------------

def inspect_market_data(
    connection: sqlite3.Connection,
) -> list[str]:

    columns = get_table_columns(
        connection,
        "market_data",
    )

    require_real_schema(
        columns
    )

    return columns


# -----------------------------------------------------------------------------
# UPSTREAM ANALYSIS SOURCE DISCOVERY
# -----------------------------------------------------------------------------

def discover_analysis_identity(
    connection: sqlite3.Connection,
) -> tuple[str, str]:

    """
    Find the latest real upstream analysis identity.

    We deliberately do NOT hard-code the old v0.2 source.

    The row must contain the actual stored upstream feature fields.
    """

    row = connection.execute(
        """
        SELECT
            source,
            engine_version
        FROM market_data
        WHERE
            timeframe = ?
            AND source IS NOT NULL
            AND engine_version IS NOT NULL
            AND rsi14 IS NOT NULL
            AND macd IS NOT NULL
            AND bb_middle IS NOT NULL
            AND volatility IS NOT NULL
        ORDER BY
            timestamp DESC,
            id DESC
        LIMIT 1
        """,
        (
            TIMEFRAME,
        ),
    ).fetchone()

    if row is None:

        raise RuntimeError(
            "No real upstream analysis rows containing "
            "the required feature fields were found."
        )

    return (
        str(row["source"]),
        str(row["engine_version"]),
    )


# -----------------------------------------------------------------------------
# LATEST UPSTREAM ROWS
# -----------------------------------------------------------------------------

def load_latest_analysis_rows(
    connection: sqlite3.Connection,
    analysis_source: str,
) -> list[sqlite3.Row]:

    rows = connection.execute(
        """
        SELECT *
        FROM market_data
        WHERE
            timeframe = ?
            AND source = ?
            AND close IS NOT NULL
        ORDER BY
            timestamp DESC,
            id DESC
        """,
        (
            TIMEFRAME,
            analysis_source,
        ),
    ).fetchall()

    latest: dict[str, sqlite3.Row] = {}

    for row in rows:

        symbol = str(
            row["symbol"]
        )

        if symbol not in latest:

            latest[symbol] = row

    return sorted(
        latest.values(),
        key=lambda row: str(
            row["symbol"]
        ),
    )


# -----------------------------------------------------------------------------
# REAL CMC SNAPSHOT HISTORY
# -----------------------------------------------------------------------------

def load_snapshot_history(
    connection: sqlite3.Connection,
    symbol: str,
) -> list[sqlite3.Row]:

    """
    Retrieve the MOST RECENT real CMC observations.

    Important:
        DESC + LIMIT
        then reverse to chronological order.

    No interpolation.
    No forward fill.
    No back fill.
    """

    rows = connection.execute(
        """
        SELECT
            id,
            timestamp,
            close,
            source,
            timeframe
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND close IS NOT NULL
        ORDER BY
            timestamp DESC,
            id DESC
        LIMIT ?
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            TIMEFRAME,
            HISTORY_WINDOW,
        ),
    ).fetchall()

    return list(
        reversed(rows)
    )


# -----------------------------------------------------------------------------
# FEATURE VALUE EXTRACTION
# -----------------------------------------------------------------------------

def get_value(
    row: sqlite3.Row,
    column: str,
) -> float | None:

    return finite_number(
        row[column]
    )


def build_bollinger(
    row: sqlite3.Row,
) -> dict[str, float | None]:

    return {
        "middle":
            get_value(
                row,
                "bb_middle",
            ),

        "upper":
            get_value(
                row,
                "bb_upper",
            ),

        "lower":
            get_value(
                row,
                "bb_lower",
            ),

        "width":
            get_value(
                row,
                "bb_width",
            ),
    }


# -----------------------------------------------------------------------------
# CONTRACT FEATURE
# -----------------------------------------------------------------------------

def make_feature(
    feature_name: str,
    value: Any,
    source: str,
    engine_version: str | None,
    symbol: str,
    timestamp: str,
    observation_count: int,
) -> dict[str, Any]:

    rule = FEATURE_RULES[
        feature_name
    ]

    blocked = (
        feature_name
        in BLOCKED_FEATURES
    )

    if blocked:

        status = "BLOCKED"

        safe_value = None

    elif value is None:

        status = "UNAVAILABLE"

        safe_value = None

    elif observation_count < MIN_HISTORY:

        status = "INSUFFICIENT_HISTORY"

        safe_value = value

    else:

        status = "ELIGIBLE_WITH_CAVEAT"

        safe_value = value

    return {

        "feature_name":
            feature_name,

        "value":
            safe_value,

        "source":
            source,

        "source_engine_version":
            engine_version,

        "asset_symbol":
            symbol,

        "snapshot_timestamp":
            timestamp,

        "observation_count":
            observation_count,

        "temporal_semantics":
            rule[
                "temporal_semantics"
            ],

        "calculation_semantics":
            rule[
                "calculation_semantics"
            ],

        "eligibility_status":
            status,

        "blocked":
            blocked,

        "caveat":
            rule["caveat"],

        "downstream_safe_representation":
            rule[
                "downstream_safe_representation"
            ],
    }


# -----------------------------------------------------------------------------
# CONTRACT GENERATION
# -----------------------------------------------------------------------------

def build_contract(
    connection: sqlite3.Connection,
) -> dict[str, Any]:

    actual_columns = (
        inspect_market_data(
            connection
        )
    )

    analysis_source, analysis_engine = (
        discover_analysis_identity(
            connection
        )
    )

    latest_rows = (
        load_latest_analysis_rows(
            connection,
            analysis_source,
        )
    )

    if not latest_rows:

        raise RuntimeError(
            "No usable upstream analysis rows found."
        )

    records = []

    for row in latest_rows:

        symbol = str(
            row["symbol"]
        )

        timestamp = str(
            row["timestamp"]
        )

        history = (
            load_snapshot_history(
                connection,
                symbol,
            )
        )

        observation_count = len(
            history
        )

        closes = [
            finite_number(
                item["close"]
            )
            for item in history
        ]

        closes = [
            value
            for value in closes
            if value is not None
        ]

        if len(closes) != observation_count:

            raise RuntimeError(
                f"Snapshot history contains invalid close "
                f"values for {symbol}."
            )

        features = []

        # ---------------------------------------------------------------------
        # PRICE
        # ---------------------------------------------------------------------

        features.append(
            make_feature(
                "PRICE",
                get_value(
                    row,
                    "close",
                ),
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # RSI
        # ---------------------------------------------------------------------

        features.append(
            make_feature(
                "RSI",
                get_value(
                    row,
                    "rsi14",
                ),
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # EMA12
        # ---------------------------------------------------------------------

        ema12_value = ema(
            closes,
            12,
        )

        features.append(
            make_feature(
                "EMA12",
                ema12_value,
                SNAPSHOT_SOURCE,
                "OBSERVATION_SERIES_FROM_REAL_CMC_SNAPSHOTS",
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # EMA26
        # ---------------------------------------------------------------------

        ema26_value = ema(
            closes,
            26,
        )

        features.append(
            make_feature(
                "EMA26",
                ema26_value,
                SNAPSHOT_SOURCE,
                "OBSERVATION_SERIES_FROM_REAL_CMC_SNAPSHOTS",
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # MACD
        # ---------------------------------------------------------------------

        macd_value = (
            get_value(
                row,
                "macd",
            )
        )

        macd_signal = (
            get_value(
                row,
                "macd_signal",
            )
        )

        macd_hist = (
            get_value(
                row,
                "macd_hist",
            )
        )

        macd_payload = {

            "value":
                macd_value,

            "signal":
                macd_signal,

            "histogram":
                macd_hist,
        }

        if all(
            value is None
            for value in macd_payload.values()
        ):

            macd_payload_value = None

        else:

            macd_payload_value = (
                macd_payload
            )

        features.append(
            make_feature(
                "MACD",
                macd_payload_value,
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # BOLLINGER
        # ---------------------------------------------------------------------

        bollinger_payload = (
            build_bollinger(
                row
            )
        )

        if all(
            value is None
            for value in bollinger_payload.values()
        ):

            bollinger_value = None

        else:

            bollinger_value = (
                bollinger_payload
            )

        features.append(
            make_feature(
                "BOLLINGER",
                bollinger_value,
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # VOLATILITY
        # ---------------------------------------------------------------------

        features.append(
            make_feature(
                "VOLATILITY",
                get_value(
                    row,
                    "volatility",
                ),
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # ATR BLOCKED
        # ---------------------------------------------------------------------

        features.append(
            make_feature(
                "ATR",
                None,
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        # ---------------------------------------------------------------------
        # ADX BLOCKED
        # ---------------------------------------------------------------------

        features.append(
            make_feature(
                "ADX",
                None,
                analysis_source,
                analysis_engine,
                symbol,
                timestamp,
                observation_count,
            )
        )

        records.append(
            {
                "asset_symbol":
                    symbol,

                "snapshot_timestamp":
                    timestamp,

                "observation_count":
                    observation_count,

                "features":
                    features,
            }
        )

    return {

        "contract":
            CONTRACT_VERSION,

        "mode":
            "READ_ONLY",

        "provider":
            SNAPSHOT_SOURCE,

        "timeframe":
            TIMEFRAME,

        "upstream_analysis_source":
            analysis_source,

        "upstream_analysis_engine":
            analysis_engine,

        "history_window":
            HISTORY_WINDOW,

        "minimum_history":
            MIN_HISTORY,

        "ohlc_semantics":
            "NO_GENUINE_OHLC",

        "production_db_write":
            False,

        "network":
            False,

        "exchange":
            False,

        "signal_generation":
            False,

        "prediction":
            False,

        "trading_decision":
            False,

        "forbidden_transformations":
            [
                "SYNTHETIC_OHLC",
                "INTERPOLATION",
                "FORWARD_FILL",
                "BACK_FILL",
            ],

        "allowed_features":
            list(
                ALLOWED_FEATURES
            ),

        "blocked_features":
            list(
                BLOCKED_FEATURES
            ),

        "schema":
            {
                "actual_columns":
                    sorted(
                        actual_columns
                    ),

                "ema12_ema26_storage":
                    "NOT_PERSISTED_AS_INDEPENDENT_COLUMNS",

                "upstream_feature_storage":
                    {
                        "RSI":
                            "rsi14",

                        "MACD":
                            [
                                "macd",
                                "macd_signal",
                                "macd_hist",
                            ],

                        "BOLLINGER":
                            [
                                "bb_middle",
                                "bb_upper",
                                "bb_lower",
                                "bb_width",
                            ],

                        "VOLATILITY":
                            "volatility",
                    },
            },

        "feature_contract_rules":
            FEATURE_RULES,

        "records":
            records,
    }


# -----------------------------------------------------------------------------
# VALIDATION
# -----------------------------------------------------------------------------

def validate_contract(
    artifact: dict[str, Any],
) -> None:

    assert (
        artifact["contract"]
        == CONTRACT_VERSION
    )

    assert (
        artifact["mode"]
        == "READ_ONLY"
    )

    assert (
        artifact["ohlc_semantics"]
        == "NO_GENUINE_OHLC"
    )

    assert (
        artifact["production_db_write"]
        is False
    )

    assert (
        artifact["network"]
        is False
    )

    assert (
        artifact["exchange"]
        is False
    )

    assert (
        artifact["signal_generation"]
        is False
    )

    assert (
        artifact["prediction"]
        is False
    )

    assert (
        artifact["trading_decision"]
        is False
    )

    assert (
        tuple(
            artifact["allowed_features"]
        )
        == ALLOWED_FEATURES
    )

    assert (
        tuple(
            artifact["blocked_features"]
        )
        == BLOCKED_FEATURES
    )

    if not artifact["records"]:

        raise AssertionError(
            "Contract contains no records."
        )

    for record in artifact["records"]:

        if not record["asset_symbol"]:

            raise AssertionError(
                "Missing asset symbol."
            )

        if not record["snapshot_timestamp"]:

            raise AssertionError(
                "Missing snapshot timestamp."
            )

        if (
            record["observation_count"]
            < 0
        ):

            raise AssertionError(
                "Invalid observation count."
            )

        feature_names = set()

        for feature in record["features"]:

            feature_names.add(
                feature["feature_name"]
            )

            required_keys = (

                "feature_name",

                "value",

                "source",

                "source_engine_version",

                "asset_symbol",

                "snapshot_timestamp",

                "observation_count",

                "temporal_semantics",

                "calculation_semantics",

                "eligibility_status",

                "blocked",

                "caveat",

                "downstream_safe_representation",
            )

            for key in required_keys:

                if key not in feature:

                    raise AssertionError(
                        f"Missing contract field: {key}"
                    )

            if (
                feature["feature_name"]
                in BLOCKED_FEATURES
            ):

                assert (
                    feature["eligibility_status"]
                    == "BLOCKED"
                )

                assert (
                    feature["value"]
                    is None
                )

                assert (
                    feature["blocked"]
                    is True
                )

            if (
                feature["feature_name"]
                in ALLOWED_FEATURES
            ):

                assert (
                    feature["blocked"]
                    is False
                )

                assert (
                    feature["temporal_semantics"]
                    in (
                        "POINT_OBSERVATION",
                        "OBSERVATION_COUNT",
                    )
                )

        expected = (
            set(ALLOWED_FEATURES)
            | set(BLOCKED_FEATURES)
        )

        if feature_names != expected:

            raise AssertionError(
                "Feature set mismatch for "
                f"{record['asset_symbol']}: "
                f"{sorted(feature_names)}"
            )


# -----------------------------------------------------------------------------
# DETERMINISTIC HASH
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
        "ARUNDA SNAPSHOT FEATURE CONTRACT v0.1"
    )
    print("=" * 90)

    print(
        f"Database : {DB_PATH}"
    )

    print(
        "Mode     : READ ONLY"
    )

    print(
        "Network  : FORBIDDEN"
    )

    print(
        "Signal   : FORBIDDEN"
    )

    print(
        "Decision : FORBIDDEN"
    )

    print("-" * 90)

    connection = connect_database()

    try:

        artifact = build_contract(
            connection
        )

        validate_contract(
            artifact
        )

    finally:

        connection.close()

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

    total_symbols = len(
        artifact["records"]
    )

    total_features = sum(
        len(record["features"])
        for record
        in artifact["records"]
    )

    blocked = sum(
        1
        for record
        in artifact["records"]
        for feature
        in record["features"]
        if feature[
            "eligibility_status"
        ] == "BLOCKED"
    )

    unavailable = sum(
        1
        for record
        in artifact["records"]
        for feature
        in record["features"]
        if feature[
            "eligibility_status"
        ] == "UNAVAILABLE"
    )

    insufficient = sum(
        1
        for record
        in artifact["records"]
        for feature
        in record["features"]
        if feature[
            "eligibility_status"
        ] == "INSUFFICIENT_HISTORY"
    )

    eligible = sum(
        1
        for record
        in artifact["records"]
        for feature
        in record["features"]
        if feature[
            "eligibility_status"
        ] == "ELIGIBLE_WITH_CAVEAT"
    )

    print("=" * 90)
    print(
        "FEATURE CONTRACT VALIDATION"
    )
    print("=" * 90)

    print(
        f"Symbols              : {total_symbols}"
    )

    print(
        f"Feature records      : {total_features}"
    )

    print(
        f"Eligible             : {eligible}"
    )

    print(
        f"Blocked              : {blocked}"
    )

    print(
        f"Unavailable          : {unavailable}"
    )

    print(
        f"Insufficient History : {insufficient}"
    )

    print(
        f"Upstream Source      : "
        f"{artifact['upstream_analysis_source']}"
    )

    print(
        f"Upstream Engine      : "
        f"{artifact['upstream_analysis_engine']}"
    )

    print(
        f"Artifact             : {OUTPUT_PATH}"
    )

    print(
        f"SHA256               : "
        f"{artifact['artifact_sha256']}"
    )

    print("=" * 90)

    if (
        unavailable == 0
        and insufficient == 0
    ):

        print(
            "FEATURE CONTRACT STATUS : VERIFIED"
        )

    else:

        print(
            "FEATURE CONTRACT STATUS : PARTIAL"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()