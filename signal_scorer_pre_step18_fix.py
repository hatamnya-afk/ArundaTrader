# =============================================================================
# ARUNDA SIGNAL SCORER v0.3
# =============================================================================
# Purpose:
#   Calculate structural score for VALIDATED signals.
#
# Rules:
#   - MEMORY ONLY
#   - READ ONLY
#   - NO DATABASE WRITES
#   - NO SQL
#   - NO NEW SIGNAL
#   - NO DECISION
#   - NO PREDICTION
#   - NO RANKING
# =============================================================================

import signal_validator
import feature_snapshot_reader
import market_state_engine
import market_regime_contract


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
# LOAD VALIDATED SIGNALS
# =============================================================================

def load_validated_signals():

    if not hasattr(
        signal_validator,
        "load_validated_signals"
    ):
        raise RuntimeError(
            "signal_validator.py must expose "
            "load_validated_signals()"
        )

    data = (
        signal_validator
        .load_validated_signals()
    )

    if not isinstance(data, dict):

        raise RuntimeError(
            "Invalid validated signal output"
        )

    return data


# =============================================================================
# LOAD FEATURE SNAPSHOT
# =============================================================================

def load_features():

    if not hasattr(
        feature_snapshot_reader,
        "load_feature_snapshot"
    ):
        raise RuntimeError(
            "feature_snapshot_reader.py must expose "
            "load_feature_snapshot()"
        )

    data = (
        feature_snapshot_reader
        .load_feature_snapshot()
    )

    if not isinstance(data, dict):

        raise RuntimeError(
            "Invalid feature snapshot"
        )

    return data


# =============================================================================
# LOAD STRUCTURAL MARKET STATE
# =============================================================================

def load_structural_states():

    if not hasattr(
        market_state_engine,
        "load_structural_state"
    ):
        raise RuntimeError(
            "market_state_engine.py must expose "
            "load_structural_state()"
        )

    data = (
        market_state_engine
        .load_structural_state()
    )

    if not isinstance(data, dict):

        raise RuntimeError(
            "Invalid structural market state"
        )

    return data


# =============================================================================
# LOAD MARKET REGIME
# =============================================================================

def load_regimes():

    if not hasattr(
        market_regime_contract,
        "load_market_regime_contract"
    ):
        raise RuntimeError(
            "market_regime_contract.py must expose "
            "load_market_regime_contract()"
        )

    data = (
        market_regime_contract
        .load_market_regime_contract()
    )

    if not isinstance(data, dict):

        raise RuntimeError(
            "Invalid market regime contract"
        )

    return data


# =============================================================================
# EXTRACT RAW FEATURE OBJECT
# =============================================================================

def extract_features(asset_data):

    if not isinstance(
        asset_data,
        dict
    ):
        raise RuntimeError(
            "Invalid asset feature object"
        )

    if asset_data.get(
        "status"
    ) != "READY":

        raise RuntimeError(
            "Feature snapshot not READY"
        )

    if "features" not in asset_data:

        raise RuntimeError(
            "Missing features container"
        )

    features = asset_data[
        "features"
    ]

    if not isinstance(
        features,
        dict
    ):

        raise RuntimeError(
            "Invalid features container"
        )

    return features


# =============================================================================
# GET FEATURE
# =============================================================================

def get_feature(
    features,
    name
):

    if name not in features:

        raise RuntimeError(
            "Missing feature: "
            + name
        )

    value = features[name]

    if not isinstance(
        value,
        (int, float)
    ):

        raise RuntimeError(
            "Invalid feature value: "
            + name
        )

    return float(value)


# =============================================================================
# SIGNED FEATURE
# =============================================================================

def signed_feature(
    value
):

    return (
        (value - 0.5) * 2.0
    )


# =============================================================================
# CLAMP
# =============================================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


# =============================================================================
# SIGNAL SEMANTIC BOUNDARY
# =============================================================================
#
# STEP 17 HARDENING
#
# Valid signal-state / direction pairs:
#
#   ACTIVE  + LONG
#   ACTIVE  + SHORT
#   NEUTRAL + NONE
#
# Invalid pairs:
#
#   ACTIVE  + NONE
#   NEUTRAL + LONG
#   NEUTRAL + SHORT
#
# This validation belongs at the scoring boundary as defense-in-depth.
# It does not create, modify, or interpret a signal.
# =============================================================================

def validate_signal_semantics(
    asset,
    signal
):

    if not isinstance(
        signal,
        dict
    ):

        raise RuntimeError(
            "Invalid signal object: "
            + asset
        )

    if signal.get(
        "valid"
    ) is not True:

        raise RuntimeError(
            "Cannot score invalid signal: "
            + asset
        )

    signal_asset = signal.get(
        "asset"
    )

    if signal_asset != asset:

        raise RuntimeError(
            "Signal asset mismatch: "
            + asset
        )

    signal_state = signal.get(
        "signal_state"
    )

    direction = signal.get(
        "direction"
    )

    # -------------------------------------------------------------------------
    # State enum
    # -------------------------------------------------------------------------

    if signal_state not in (
        "ACTIVE",
        "NEUTRAL"
    ):

        raise RuntimeError(
            "Invalid signal state: "
            + asset
        )

    # -------------------------------------------------------------------------
    # Direction enum
    # -------------------------------------------------------------------------

    if direction not in (
        "NONE",
        "LONG",
        "SHORT"
    ):

        raise RuntimeError(
            "Invalid signal direction: "
            + asset
        )

    # -------------------------------------------------------------------------
    # Semantic pair enforcement
    # -------------------------------------------------------------------------

    if signal_state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT"
        ):

            raise RuntimeError(
                "ACTIVE signal must have LONG or SHORT direction: "
                + asset
            )

    # -------------------------------------------------------------------------
    # NEUTRAL must remain non-directional
    # -------------------------------------------------------------------------

    if signal_state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                "NEUTRAL signal must have NONE direction: "
                + asset
            )

    return (
        signal_state,
        direction
    )


# =============================================================================
# SCORE ONE SIGNAL
# =============================================================================

def calculate_score(
    direction,
    features,
    structural_state,
    regime_data
):

    # -------------------------------------------------------------------------
    # Direction validation
    # -------------------------------------------------------------------------

    if direction not in (
        "NONE",
        "LONG",
        "SHORT"
    ):

        raise RuntimeError(
            "Invalid direction"
        )

    # -------------------------------------------------------------------------
    # Neutral
    # -------------------------------------------------------------------------

    if direction == "NONE":

        return 0.0

    # -------------------------------------------------------------------------
    # Structural state validation
    # -------------------------------------------------------------------------

    if not isinstance(
        structural_state,
        dict
    ):

        raise RuntimeError(
            "Invalid structural state"
        )

    # -------------------------------------------------------------------------
    # Regime validation
    # -------------------------------------------------------------------------

    if not isinstance(
        regime_data,
        dict
    ):

        raise RuntimeError(
            "Invalid market regime"
        )

    # -------------------------------------------------------------------------
    # Required features
    # -------------------------------------------------------------------------

    return_20 = get_feature(
        features,
        "return_20"
    )

    momentum_20 = get_feature(
        features,
        "momentum_20"
    )

    trend_slope_20 = get_feature(
        features,
        "trend_slope_20"
    )

    acceleration = get_feature(
        features,
        "acceleration"
    )

    position_20 = get_feature(
        features,
        "position_20"
    )

    volatility_20 = get_feature(
        features,
        "volatility_20"
    )

    range_20 = get_feature(
        features,
        "range_20"
    )

    # -------------------------------------------------------------------------
    # Raw feature components
    #
    # IMPORTANT:
    # This is only structural scoring.
    # No trading decision is made here.
    # -------------------------------------------------------------------------

    return_component = (
        return_20 * WEIGHTS["return_20"]
    )

    momentum_component = (
        momentum_20 * WEIGHTS["momentum_20"]
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

    # -------------------------------------------------------------------------
    # Direction
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Final score
    # -------------------------------------------------------------------------

    score = (
        directional_score
        - volatility_penalty
    )

    return round(
        score,
        6
    )


# =============================================================================
# BUILD SCORE SNAPSHOT
# =============================================================================

def load_scores():

    signals = (
        load_validated_signals()
    )

    feature_snapshot = (
        load_features()
    )

    structural_states = (
        load_structural_states()
    )

    regimes = (
        load_regimes()
    )

    scores = {}

    for asset in EXPECTED_ASSETS:

        # ---------------------------------------------------------------------
        # Asset existence
        # ---------------------------------------------------------------------

        if asset not in signals:

            raise RuntimeError(
                "Missing validated signal: "
                + asset
            )

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

        # ---------------------------------------------------------------------
        # Signal
        # ---------------------------------------------------------------------

        signal = signals[
            asset
        ]

        signal_state, direction = (
            validate_signal_semantics(
                asset,
                signal
            )
        )

        # ---------------------------------------------------------------------
        # Feature extraction
        # ---------------------------------------------------------------------

        features = extract_features(
            feature_snapshot[asset]
        )

        # ---------------------------------------------------------------------
        # Score
        # ---------------------------------------------------------------------

        score = calculate_score(

            direction,

            features,

            structural_states[asset],

            regimes[asset]

        )

        scores[asset] = {

            "asset":
                asset,

            "signal_state":
                signal_state,

            "direction":
                direction,

            "score":
                score,

        }

    return scores


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print(
        "ARUNDA SIGNAL SCORER v0.3"
    )
    print("=" * 78)

    print(
        "Source   : validated signals"
    )

    print(
        "Features : feature_snapshot.features"
    )

    print(
        "State    : market_state_engine"
    )

    print(
        "Regime   : market_regime_contract"
    )

    print(
        "Storage  : MEMORY ONLY"
    )

    print(
        "Writes   : NONE"
    )

    print(
        "SQL      : NOT USED"
    )

    print(
        "Decision : NOT USED"
    )

    print(
        "Prediction : NOT USED"
    )

    print(
        "Ranking  : NOT USED"
    )

    print("=" * 78)

    print()


# =============================================================================
# PRINT SCORES
# =============================================================================

def print_scores(
    scores
):

    print(
        "SIGNAL SCORE SNAPSHOT"
    )

    print("-" * 78)

    print(
        "Asset  | State   | Direction | Score"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:

        item = scores[
            asset
        ]

        print(
            "{:<6} | {:<7} | {:<9} | {:+.6f}".format(
                asset,
                item["signal_state"],
                item["direction"],
                item["score"]
            )
        )

    print()


# =============================================================================
# SCORE CONTRACT
# =============================================================================

def print_contract(
    scores
):

    active = 0
    neutral = 0

    for asset in EXPECTED_ASSETS:

        direction = scores[
            asset
        ]["direction"]

        if direction == "NONE":

            neutral += 1

        else:

            active += 1

    valid = (

        isinstance(
            scores,
            dict
        )

        and len(scores)
        == len(EXPECTED_ASSETS)

    )

    print("=" * 78)
    print(
        "SIGNAL SCORE CONTRACT"
    )
    print("=" * 78)

    print(
        "Expected Assets :",
        len(EXPECTED_ASSETS)
    )

    print(
        "Scored Assets   :",
        len(scores)
    )

    print(
        "Active Signals  :",
        active
    )

    print(
        "Neutral Signals :",
        neutral
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "SQL             : NOT USED"
    )

    print(
        "Decision        : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    print(
        "Contract Status :",
        "VALID"
        if valid
        else
        "INVALID"
    )

    print()

    return valid


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    try:

        scores = (
            load_scores()
        )

        print_scores(
            scores
        )

        valid = (
            print_contract(
                scores
            )
        )

        if valid:

            print(
                "SIGNAL SCORER STATUS : READY"
            )

            return 0

        print(
            "SIGNAL SCORER STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 78)
        print(
            "SIGNAL SCORER ERROR"
        )
        print("=" * 78)

        print(
            "Type   :",
            type(error).__name__
        )

        print(
            "Error  :",
            str(error)
        )

        print()

        print(
            "SIGNAL SCORER STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )