# =============================================================================
# ARUNDA SCORE PRODUCER v0.2
# =============================================================================
#
# PURPOSE
# -------
# Produce the REAL runtime score snapshot consumed by:
#
#     signal_scorer v0.4
#
#
# REPAIR
# ------
# SCORE PRODUCER CONTRACT REPAIR
#
# The previous v0.1 implementation expected:
#
#     asset_data["features"] == dict[str, scalar]
#
# The verified Feature Snapshot v0.7 actually provides:
#
#     asset_data["features"] == list[FeatureRecord]
#
# This version introduces a STRICT LOCAL ADAPTER between the real runtime
# Feature Snapshot and the existing frozen Score Formula.
#
#
# AUTHORITATIVE RUNTIME SOURCE
# ----------------------------
#
#     runtime_feature_producer.py
#     RECONSTRUCTED_RUNTIME_FEATURE_PRODUCER_v0.5
#
#
# AUTHORITATIVE FEATURE DEFINITIONS
# ---------------------------------
#
# Recovered and implementation-proven from:
#
#     market_analysis_engine.py
#
# Required score features:
#
#     return_20
#     momentum_20
#     trend_slope_20
#     acceleration
#     position_20
#     volatility_20
#     range_20
#
#
# IMPORTANT
# ---------
# The Score Formula is NOT changed.
#
# Existing v0.3 scoring logic is preserved:
#
#     return_20       * 0.20
#     momentum_20     * 0.20
#     trend_slope_20  * 0.20
#     acceleration    * 0.10
#     position_20     * 0.10
#     range_20        * 0.10
#
#     volatility penalty:
#         clamp(volatility_20) * 0.25
#
#
# RULES
# -----
# - REAL runtime inputs only
# - MEMORY ONLY
# - READ ONLY
# - NO SQL writes
# - NO DATABASE WRITES
# - NO SIGNAL GENERATION
# - NO DECISION
# - NO RANKING
# - NO PREDICTION
# - NO SYNTHETIC DATA
# - NO INTERPOLATION
# - NO FORWARD FILL
# - NO BACK FILL
# - NO PADDING
# - NO FABRICATED FEATURE VALUES
# - FAIL CLOSED on invalid/incomplete feature context
#
# =============================================================================

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import runtime_feature_producer
import market_state_engine
import market_regime_contract


# =============================================================================
# CONSTANTS
# =============================================================================

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]

EXPECTED_ASSET_COUNT = 15

PRODUCER_VERSION = "SCORE_PRODUCER_v0.2"


# =============================================================================
# EXISTING SCORE MODEL
# =============================================================================
#
# FROZEN
#
# Recovered from signal_scorer v0.3.
#
# =============================================================================

WEIGHTS = {
    "return_20": 0.20,
    "momentum_20": 0.20,
    "trend_slope_20": 0.20,
    "acceleration": 0.10,
    "position_20": 0.10,
    "volatility_20": 0.10,
    "range_20": 0.10,
}


# =============================================================================
# REQUIRED FEATURE CONTRACT
# =============================================================================

REQUIRED_FEATURES = (
    "return_20",
    "momentum_20",
    "trend_slope_20",
    "acceleration",
    "position_20",
    "volatility_20",
    "range_20",
)

MIN_REQUIRED_POINTS = 21


# =============================================================================
# EXPECTED RUNTIME PRODUCER CONTRACT
# =============================================================================

EXPECTED_RUNTIME_PRODUCER = (
    "RECONSTRUCTED_RUNTIME_FEATURE_PRODUCER_v0.5"
)


# =============================================================================
# VALIDATED SIGNAL CONTRACT
# =============================================================================

def validate_validated_signals(
    validated_signals: Any,
) -> None:

    if not isinstance(
        validated_signals,
        dict,
    ):
        raise RuntimeError(
            "validated_signals must be a dict."
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(validated_signals.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            "Missing validated signals: "
            + repr(sorted(missing))
        )

    if extra:
        raise RuntimeError(
            "Unexpected validated signals: "
            + repr(sorted(extra))
        )

    if len(validated_signals) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Validated signal asset count mismatch: "
            + str(len(validated_signals))
        )

    for asset in EXPECTED_ASSETS:

        signal = validated_signals[asset]

        if not isinstance(
            signal,
            dict,
        ):
            raise RuntimeError(
                "Invalid validated signal object: "
                + asset
            )

        if signal.get("asset") != asset:
            raise RuntimeError(
                "Validated signal asset mismatch: "
                + asset
            )

        if signal.get("valid") is not True:
            raise RuntimeError(
                "Cannot score invalid validated signal: "
                + asset
            )

        state = signal.get("signal_state")
        direction = signal.get("direction")

        if state not in (
            "ACTIVE",
            "NEUTRAL",
        ):
            raise RuntimeError(
                "Invalid signal state: "
                + asset
            )

        if direction not in (
            "LONG",
            "SHORT",
            "NONE",
        ):
            raise RuntimeError(
                "Invalid signal direction: "
                + asset
            )

        if state == "ACTIVE" and direction not in (
            "LONG",
            "SHORT",
        ):
            raise RuntimeError(
                "ACTIVE signal requires LONG/SHORT: "
                + asset
            )

        if state == "NEUTRAL" and direction != "NONE":
            raise RuntimeError(
                "NEUTRAL signal requires NONE: "
                + asset
            )


# =============================================================================
# GENERIC VALUE ACCESS
# =============================================================================

def _get(
    obj: Any,
    field: str,
    default: Any = None,
) -> Any:

    if isinstance(
        obj,
        Mapping,
    ):
        return obj.get(
            field,
            default,
        )

    return getattr(
        obj,
        field,
        default,
    )


# =============================================================================
# STRICT NUMERIC VALIDATION
# =============================================================================

def _finite_float(
    value: Any,
    name: str,
) -> float:

    if isinstance(
        value,
        bool,
    ):
        raise RuntimeError(
            "Boolean numeric value is invalid: "
            + name
        )

    if not isinstance(
        value,
        (int, float),
    ):
        raise RuntimeError(
            "Invalid numeric value: "
            + name
        )

    result = float(value)

    if not math.isfinite(result):
        raise RuntimeError(
            "Non-finite numeric value: "
            + name
        )

    return result


# =============================================================================
# REAL FEATURE SNAPSHOT
# =============================================================================
#
# IMPORTANT:
# ----------
# We deliberately use the verified Runtime Feature Producer directly.
#
# No independent DB query is introduced here.
#
# Runtime chain:
#
#     market_data
#       ->
#     runtime_feature_producer
#       ->
#     FeatureBar
#       ->
#     Feature Contract
#       ->
#     Feature Snapshot
#
# =============================================================================

def load_features() -> dict:

    required_functions = (
        "connect_readonly",
        "build_bars_by_asset",
        "build_indicators_by_asset",
        "build_structures_by_asset",
        "build_feature_snapshot",
    )

    for function_name in required_functions:

        if not hasattr(
            runtime_feature_producer,
            function_name,
        ):
            raise RuntimeError(
                "runtime_feature_producer.py missing "
                "required function: "
                + function_name
            )

    engine_name = getattr(
        runtime_feature_producer,
        "ENGINE_NAME",
        None,
    )

    if engine_name != EXPECTED_RUNTIME_PRODUCER:
        raise RuntimeError(
            "Unexpected runtime feature producer: "
            + repr(engine_name)
        )

    conn = (
        runtime_feature_producer
        .connect_readonly()
    )

    try:

        bars_by_asset = (
            runtime_feature_producer
            .build_bars_by_asset(
                conn
            )
        )

        indicators_by_asset = (
            runtime_feature_producer
            .build_indicators_by_asset(
                bars_by_asset
            )
        )

        structures_by_asset = (
            runtime_feature_producer
            .build_structures_by_asset(
                bars_by_asset
            )
        )

        snapshot = (
            runtime_feature_producer
            .build_feature_snapshot(
                bars_by_asset,
                indicators_by_asset,
                structures_by_asset,
            )
        )

    finally:

        conn.close()

    if not isinstance(
        snapshot,
        dict,
    ):
        raise RuntimeError(
            "Invalid Feature Snapshot."
        )

    return snapshot


# =============================================================================
# REAL STRUCTURAL STATE
# =============================================================================

def load_structural_states() -> dict:

    if not hasattr(
        market_state_engine,
        "load_structural_state",
    ):
        raise RuntimeError(
            "market_state_engine.py must expose "
            "load_structural_state()."
        )

    data = (
        market_state_engine
        .load_structural_state()
    )

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            "Invalid structural market state."
        )

    return data


# =============================================================================
# REAL MARKET REGIME
# =============================================================================

def load_regimes() -> dict:

    if not hasattr(
        market_regime_contract,
        "load_market_regime_contract",
    ):
        raise RuntimeError(
            "market_regime_contract.py must expose "
            "load_market_regime_contract()."
        )

    data = (
        market_regime_contract
        .load_market_regime_contract()
    )

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            "Invalid market regime contract."
        )

    return data


# =============================================================================
# FEATURE RECORD EXTRACTION
# =============================================================================

def _extract_feature_records(
    asset_data: Any,
    asset: str,
) -> list[Any]:

    if not isinstance(
        asset_data,
        dict,
    ):
        raise RuntimeError(
            "Invalid asset feature object: "
            + asset
        )

    if asset_data.get(
        "status"
    ) != "READY":

        raise RuntimeError(
            "Feature snapshot not READY: "
            + asset
        )

    if "points" not in asset_data:
        raise RuntimeError(
            "Missing feature snapshot points: "
            + asset
        )

    points = asset_data[
        "points"
    ]

    if isinstance(
        points,
        bool,
    ) or not isinstance(
        points,
        int,
    ):
        raise RuntimeError(
            "Invalid feature snapshot points: "
            + asset
        )

    if points < MIN_REQUIRED_POINTS:
        raise RuntimeError(
            "Insufficient REAL feature context for "
            + asset
            + ": points="
            + str(points)
            + ", required="
            + str(MIN_REQUIRED_POINTS)
        )

    if "features" not in asset_data:
        raise RuntimeError(
            "Missing features container: "
            + asset
        )

    features = asset_data[
        "features"
    ]

    if not isinstance(
        features,
        (list, tuple),
    ):
        raise RuntimeError(
            "Feature snapshot contract mismatch for "
            + asset
            + ": features must be a sequence."
        )

    features = list(
        features
    )

    if len(features) != points:
        raise RuntimeError(
            "Feature cardinality mismatch for "
            + asset
            + ": points="
            + str(points)
            + ", features="
            + str(len(features))
        )

    if len(features) < MIN_REQUIRED_POINTS:
        raise RuntimeError(
            "Insufficient feature records for "
            + asset
        )

    return features


# =============================================================================
# REAL CLOSE SERIES
# =============================================================================
#
# The seven recovered score features are defined from REAL price history.
#
# FeatureRecord.close is used only as an adapter representation of the same
# REAL OHLCV price stream already present in the Runtime Feature Producer.
#
# No values are generated.
#
# =============================================================================

def _extract_close_series(
    feature_records: Sequence[Any],
    asset: str,
) -> list[float]:

    prices: list[float] = []

    for index, record in enumerate(
        feature_records
    ):

        close = _get(
            record,
            "close",
            None,
        )

        if close is None:
            raise RuntimeError(
                "Missing REAL close in FeatureRecord: "
                + asset
                + " index="
                + str(index)
            )

        close = _finite_float(
            close,
            asset
            + ".close["
            + str(index)
            + "]",
        )

        if close <= 0.0:
            raise RuntimeError(
                "Non-positive REAL close in FeatureRecord: "
                + asset
                + " index="
                + str(index)
            )

        prices.append(
            close
        )

    if len(prices) < MIN_REQUIRED_POINTS:
        raise RuntimeError(
            "Insufficient REAL close history for "
            + asset
        )

    return prices


# =============================================================================
# AUTHORITATIVE MARKET ANALYSIS HELPERS
# =============================================================================
#
# These implementations are intentionally identical in substance to the
# implementation recovered from market_analysis_engine.py.
#
# =============================================================================

def percentage_return(
    old_price: float,
    new_price: float,
) -> float:

    if old_price == 0:
        return 0.0

    return (
        (new_price / old_price) - 1.0
    ) * 100.0


def standard_deviation(
    values: Sequence[float],
) -> float:

    if len(values) < 2:
        return 0.0

    mean = (
        sum(values)
        / len(values)
    )

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return math.sqrt(
        variance
    )


def linear_slope(
    values: Sequence[float],
) -> float:

    count = len(values)

    if count < 2:
        return 0.0

    x_mean = (
        count - 1
    ) / 2.0

    y_mean = (
        sum(values)
        / count
    )

    numerator = 0.0
    denominator = 0.0

    for index, value in enumerate(
        values
    ):

        dx = (
            index
            - x_mean
        )

        dy = (
            value
            - y_mean
        )

        numerator += (
            dx * dy
        )

        denominator += (
            dx * dx
        )

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
    )


# =============================================================================
# SCORE FEATURE ADAPTER
# =============================================================================
#
# Exact recovered definitions:
#
# return_20:
#     percentage_return(
#         prices[-21],
#         latest_price
#     )
#
# momentum_20:
#     exactly return_20
#
# volatility_20:
#     standard_deviation(
#         returns[-20:]
#     )
#
# range_20:
#     percentage_return(
#         min(prices[-20:]),
#         max(prices[-20:])
#     )
#
# trend_slope_20:
#     linear_slope(
#         prices[-20:]
#     ) / latest_price * 100
#
# acceleration:
#     trend_slope_10 - trend_slope_20
#
# position_20:
#     (latest_price - low_20)
#     /
#     (high_20 - low_20)
#
# =============================================================================

def build_score_features(
    feature_records: Sequence[Mapping[str, Any]],
    asset: str,
) -> dict[str, float]:

    if not isinstance(feature_records, (list, tuple)):
        raise RuntimeError(
            f"Invalid FeatureRecord collection for {asset}."
        )

    if len(feature_records) < MIN_REQUIRED_POINTS:
        raise RuntimeError(
            f"Insufficient REAL FeatureRecords for {asset}: "
            f"{len(feature_records)} < {MIN_REQUIRED_POINTS}"
        )

    prices = _extract_close_series(
        feature_records,
        asset,
    )

    latest_price = prices[-1]

    if not math.isfinite(latest_price) or latest_price <= 0:
        raise RuntimeError(
            f"Invalid latest REAL price for {asset}."
        )

    def percentage_return(
        old_price: float,
        new_price: float,
    ) -> float:
        if old_price <= 0:
            raise RuntimeError(
                f"Invalid old price for {asset}."
            )

        return (
            (new_price / old_price) - 1.0
        ) * 100.0

    def standard_deviation(
        values: Sequence[float],
    ) -> float:
        if len(values) < 2:
            return 0.0

        mean_value = sum(values) / len(values)

        variance = sum(
            (value - mean_value) ** 2
            for value in values
        ) / len(values)

        return math.sqrt(variance)

    def linear_slope(
        values: Sequence[float],
    ) -> float:
        if len(values) < 2:
            return 0.0

        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n

        numerator = sum(
            (index - x_mean)
            * (value - y_mean)
            for index, value in enumerate(values)
        )

        denominator = sum(
            (index - x_mean) ** 2
            for index in range(n)
        )

        if denominator == 0:
            return 0.0

        return numerator / denominator

    return_20 = percentage_return(
        prices[-21],
        latest_price,
    )

    momentum_20 = return_20

    returns: list[float] = []

    for index in range(1, len(prices)):
        returns.append(
            percentage_return(
                prices[index - 1],
                prices[index],
            )
        )

    recent_returns_20 = returns[-20:]

    volatility_20 = standard_deviation(
        recent_returns_20
    )

    recent_prices_20 = prices[-20:]

    range_20 = percentage_return(
        min(recent_prices_20),
        max(recent_prices_20),
    )

    slope_10 = linear_slope(
        prices[-10:]
    )

    slope_20 = linear_slope(
        prices[-20:]
    )

    slope_10_pct = (
        slope_10 / latest_price
    ) * 100.0

    slope_20_pct = (
        slope_20 / latest_price
    ) * 100.0

    acceleration = (
        slope_10_pct - slope_20_pct
    )

    low_20 = min(recent_prices_20)
    high_20 = max(recent_prices_20)

    if high_20 == low_20:
        position_20 = 0.0
    else:
        position_20 = (
            (latest_price - low_20)
            / (high_20 - low_20)
        )

    if not math.isfinite(position_20):
        raise RuntimeError(
            f"Produced non-finite position_20 for {asset}."
        )

    position_20 = max(
        0.0,
        min(1.0, position_20),
    )

    # -------------------------------------------------------------------------
    # SCORE-SPACE ADAPTER
    #
    # The authoritative legacy snapshot expresses these quantities in
    # percentage points. The score contract is bounded to [-1,+1].
    # Convert percentage-point features to decimal score-space here.
    #
    # No weight, scoring direction, or scoring formula is changed.
    # -------------------------------------------------------------------------

    score_features = {
        "return_20": max(
            -1.0,
            min(1.0, return_20 / 100.0),
        ),
        "momentum_20": max(
            -1.0,
            min(1.0, momentum_20 / 100.0),
        ),
        "trend_slope_20": max(
            -1.0,
            min(1.0, slope_20_pct / 100.0),
        ),
        "acceleration": max(
            -1.0,
            min(1.0, acceleration / 100.0),
        ),
        "position_20": position_20,
        "volatility_20": max(
            0.0,
            min(1.0, volatility_20 / 100.0),
        ),
        "range_20": max(
            0.0,
            min(1.0, range_20 / 100.0),
        ),
    }

    for name, value in score_features.items():
        if not math.isfinite(float(value)):
            raise RuntimeError(
                f"Produced non-finite score feature "
                f"{name} for {asset}: {value!r}"
            )

    return score_features


# =============================================================================
# FEATURE EXTRACTION PUBLIC ADAPTER
# =============================================================================

def extract_features(
    asset_data: Any,
    asset: str,
) -> dict[str, float]:

    records = _extract_feature_records(
        asset_data,
        asset,
    )

    features = build_score_features(
        records,
        asset,
    )

    if set(features.keys()) != set(
        REQUIRED_FEATURES
    ):
        raise RuntimeError(
            "Required score features incomplete: "
            + asset
        )

    return features


# =============================================================================
# FEATURE VALUE
# =============================================================================

def get_feature(
    features: Mapping[str, Any],
    name: str,
) -> float:

    if name not in features:
        raise RuntimeError(
            "Missing feature: "
            + name
        )

    value = features[
        name
    ]

    if isinstance(
        value,
        bool,
    ):
        raise RuntimeError(
            "Boolean feature is invalid: "
            + name
        )

    if not isinstance(
        value,
        (int, float),
    ):
        raise RuntimeError(
            "Invalid feature value: "
            + name
        )

    value = float(
        value
    )

    if not math.isfinite(
        value
    ):
        raise RuntimeError(
            "Non-finite feature value: "
            + name
        )

    return value


# =============================================================================
# CLAMP
# =============================================================================

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


# =============================================================================
# SCORE CALCULATION
# =============================================================================
#
# FROZEN EXISTING SCORE FORMULA
#
# DO NOT MODIFY.
#
# =============================================================================

def calculate_score(
    direction: str,
    features: Mapping[str, Any],
    structural_state: Any,
    regime_data: Any,
) -> float:

    if direction not in (
        "NONE",
        "LONG",
        "SHORT",
    ):
        raise RuntimeError(
            "Invalid direction."
        )

    # -------------------------------------------------------------------------
    # Neutral is structurally zero.
    # -------------------------------------------------------------------------

    if direction == "NONE":
        return 0.0

    if not isinstance(
        structural_state,
        dict,
    ):
        raise RuntimeError(
            "Invalid structural state."
        )

    if not isinstance(
        regime_data,
        dict,
    ):
        raise RuntimeError(
            "Invalid market regime."
        )

    return_20 = get_feature(
        features,
        "return_20",
    )

    momentum_20 = get_feature(
        features,
        "momentum_20",
    )

    trend_slope_20 = get_feature(
        features,
        "trend_slope_20",
    )

    acceleration = get_feature(
        features,
        "acceleration",
    )

    position_20 = get_feature(
        features,
        "position_20",
    )

    volatility_20 = get_feature(
        features,
        "volatility_20",
    )

    range_20 = get_feature(
        features,
        "range_20",
    )

    return_component = (
        return_20
        * WEIGHTS["return_20"]
    )

    momentum_component = (
        momentum_20
        * WEIGHTS["momentum_20"]
    )

    trend_component = (
        trend_slope_20
        * WEIGHTS["trend_slope_20"]
    )

    acceleration_component = (
        acceleration
        * WEIGHTS["acceleration"]
    )

    position_component = (
        position_20
        * WEIGHTS["position_20"]
    )

    range_component = (
        clamp(range_20)
        * WEIGHTS["range_20"]
    )

    volatility_penalty = (
        clamp(volatility_20)
        * 0.25
    )

    if direction == "LONG":

        directional_score = (
            return_component
            + momentum_component
            + trend_component
            + acceleration_component
            + position_component
            + range_component
        )

    else:

        directional_score = (
            -return_component
            -momentum_component
            -trend_component
            -acceleration_component
            -position_component
            + range_component
        )

    score = (
        directional_score
        - volatility_penalty
    )

    score = round(
        score,
        6,
    )

    if not math.isfinite(
        score
    ):
        raise RuntimeError(
            "Produced non-finite score."
        )

    if score < -1.0 or score > 1.0:
        raise RuntimeError(
            "Produced score violates "
            "[-1, +1] contract: "
            + repr(score)
        )

    return score


# =============================================================================
# SCORE SNAPSHOT VALIDATION
# =============================================================================

def validate_score_snapshot(
    scores: Mapping[str, Any],
) -> None:

    if set(scores.keys()) != set(
        EXPECTED_ASSETS
    ):
        raise RuntimeError(
            "Produced score snapshot asset contract failed."
        )

    if len(scores) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Produced score asset count mismatch."
        )

    for asset in EXPECTED_ASSETS:

        item = scores[
            asset
        ]

        if not isinstance(
            item,
            dict,
        ):
            raise RuntimeError(
                "Invalid score object: "
                + asset
            )

        if item.get(
            "asset"
        ) != asset:
            raise RuntimeError(
                "Score asset mismatch: "
                + asset
            )

        if item.get(
            "signal_state"
        ) not in (
            "ACTIVE",
            "NEUTRAL",
        ):
            raise RuntimeError(
                "Invalid score signal state: "
                + asset
            )

        if item.get(
            "direction"
        ) not in (
            "LONG",
            "SHORT",
            "NONE",
        ):
            raise RuntimeError(
                "Invalid score direction: "
                + asset
            )

        score = item.get(
            "score"
        )

        score = _finite_float(
            score,
            asset + ".score",
        )

        if score < -1.0 or score > 1.0:
            raise RuntimeError(
                "Score outside [-1,+1]: "
                + asset
            )


# =============================================================================
# PRODUCE SCORE SNAPSHOT
# =============================================================================

def run(
    validated_signals: dict,
) -> dict:

    print("=" * 90)
    print(
        "ARUNDA SCORE PRODUCER v0.2"
    )
    print("=" * 90)

    print(
        "Contract repair      : FEATURE SNAPSHOT -> SCORE PRODUCER"
    )

    print(
        "Runtime source       : runtime_feature_producer"
    )

    print(
        "Runtime engine       :",
        EXPECTED_RUNTIME_PRODUCER,
    )

    print(
        "Feature definitions  : market_analysis_engine"
    )

    print(
        "Scoring model        : signal_scorer v0.3 recovered logic"
    )

    print(
        "Storage              : MEMORY ONLY"
    )

    print(
        "Database writes      : NONE"
    )

    print(
        "Synthetic data       : NONE"
    )

    print(
        "Interpolation        : NONE"
    )

    print(
        "Forward fill         : NONE"
    )

    print(
        "Back fill            : NONE"
    )

    print(
        "Padding              : NONE"
    )

    print(
        "Execution            : DISABLED"
    )

    print()

    # =========================================================================
    # STEP 1 — VALIDATED SIGNALS
    # =========================================================================

    validate_validated_signals(
        validated_signals
    )

    # =========================================================================
    # STEP 2 — REAL FEATURE SNAPSHOT
    # =========================================================================

    feature_snapshot = (
        load_features()
    )

    # =========================================================================
    # STEP 3 — STRUCTURAL STATE
    # =========================================================================

    structural_states = (
        load_structural_states()
    )

    # =========================================================================
    # STEP 4 — MARKET REGIME
    # =========================================================================

    regimes = (
        load_regimes()
    )

    # =========================================================================
    # STEP 5 — SCORE
    # =========================================================================

    scores = {}

    for asset in EXPECTED_ASSETS:

        if asset not in feature_snapshot:
            raise RuntimeError(
                "Missing feature snapshot: "
                + asset
            )

        if asset not in structural_states:
            raise RuntimeError(
                "Missing structural state: "
                + asset
            )

        if asset not in regimes:
            raise RuntimeError(
                "Missing market regime: "
                + asset
            )

        signal = (
            validated_signals[
                asset
            ]
        )

        signal_state = (
            signal[
                "signal_state"
            ]
        )

        direction = (
            signal[
                "direction"
            ]
        )

        features = extract_features(
            feature_snapshot[
                asset
            ],
            asset,
        )

        score = calculate_score(
            direction,
            features,
            structural_states[
                asset
            ],
            regimes[
                asset
            ],
        )

        scores[
            asset
        ] = {
            "asset": asset,
            "signal_state": signal_state,
            "direction": direction,
            "score": score,
        }

    # =========================================================================
    # STEP 6 — FINAL CONTRACT
    # =========================================================================

    validate_score_snapshot(
        scores
    )

    print(
        "SCORE PRODUCER STATUS : READY"
    )

    print(
        "Produced assets       :",
        len(scores),
    )

    print(
        "Feature adapter       : PASS"
    )

    print(
        "7/7 score features    : PASS"
    )

    print(
        "Score formula         : FROZEN"
    )

    print(
        "Database writes       : NONE"
    )

    print(
        "Execution             : DISABLED"
    )

    print()

    return scores


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    print("=" * 90)
    print(
        "ARUNDA SCORE PRODUCER v0.2"
    )
    print("=" * 90)

    print(
        "STATUS : NOT EXECUTED"
    )

    print(
        "REASON : validated_signals must come from "
        "the real runtime."
    )

    print(
        "REQUIRED:"
    )

    print(
        "    run(validated_signals)"
    )

    print("=" * 90)