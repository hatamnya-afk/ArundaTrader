import normalized_feature_contract


# =============================================================================
# ARUNDA MARKET STATE READER v0.1
# Normalized Feature Contract -> In-Memory Market State
# READ ONLY / MEMORY ONLY
# =============================================================================

WINDOW_SIZE = 150

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

EXPECTED_FEATURES = [
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "return_20",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "volatility_10",
    "volatility_20",
    "range_10",
    "range_20",
    "trend_slope_10",
    "trend_slope_20",
    "acceleration",
    "position_20",
]


# =============================================================================
# LOAD SOURCE CONTRACT
# =============================================================================

def load_source_contract():

    if hasattr(
        normalized_feature_contract,
        "load_normalized_feature_contract"
    ):
        return (
            normalized_feature_contract
            .load_normalized_feature_contract()
        )

    raise RuntimeError(
        "normalized_feature_contract.py must expose "
        "load_normalized_feature_contract()"
    )


# =============================================================================
# VALIDATE SOURCE
# =============================================================================

def validate_source(source):

    if not isinstance(source, dict):
        raise RuntimeError(
            "Normalized feature contract is invalid"
        )

    if len(source) != len(EXPECTED_ASSETS):
        raise RuntimeError(
            "Invalid asset count"
        )

    for asset in EXPECTED_ASSETS:

        if asset not in source:
            raise RuntimeError(
                "Missing asset: " + asset
            )

        data = source[asset]

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid data for asset: " + asset
            )

        if data.get("status") != "READY":
            raise RuntimeError(
                "Asset not READY: " + asset
            )

        if data.get("points") != WINDOW_SIZE:
            raise RuntimeError(
                "Invalid window for asset: " + asset
            )

        features = data.get("features")

        if not isinstance(features, dict):
            raise RuntimeError(
                "Missing features for asset: " + asset
            )

        for feature_name in EXPECTED_FEATURES:

            if feature_name not in features:
                raise RuntimeError(
                    "Missing feature '{}' for {}".format(
                        feature_name,
                        asset
                    )
                )


# =============================================================================
# BUILD MARKET STATE
# =============================================================================

def build_market_state():

    source = load_source_contract()

    validate_source(
        source
    )

    market_state = {}

    for asset in EXPECTED_ASSETS:

        source_data = source[asset]

        market_state[asset] = {
            "asset": asset,
            "status": "READY",
            "points": WINDOW_SIZE,
            "features": dict(
                source_data["features"]
            ),
        }

    return market_state


# =============================================================================
# PUBLIC API
# =============================================================================

def load_market_state():

    return build_market_state()


# =============================================================================
# VALIDATE MARKET STATE
# =============================================================================

def validate_market_state(
    market_state
):

    if not isinstance(
        market_state,
        dict
    ):
        return False

    if len(market_state) != len(
        EXPECTED_ASSETS
    ):
        return False

    for asset in EXPECTED_ASSETS:

        if asset not in market_state:
            return False

        data = market_state[asset]

        if data.get("status") != "READY":
            return False

        if data.get("points") != WINDOW_SIZE:
            return False

        features = data.get("features")

        if not isinstance(
            features,
            dict
        ):
            return False

        for feature_name in EXPECTED_FEATURES:

            if feature_name not in features:
                return False

    return True


# =============================================================================
# PRINT HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print("ARUNDA MARKET STATE READER v0.1")
    print("=" * 78)

    print(
        "Source   : normalized_feature_contract"
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
        "Signals  : NOT USED"
    )

    print(
        "Scoring  : NOT USED"
    )

    print(
        "Window   :",
        WINDOW_SIZE
    )

    print(
        "Features :",
        len(EXPECTED_FEATURES)
    )

    print("=" * 78)
    print()


# =============================================================================
# PRINT STATE
# =============================================================================

def print_state(
    market_state
):

    print("MARKET STATE")
    print("-" * 78)

    print(
        "Asset  | Status   | Points | Features"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:

        data = market_state[asset]

        print(
            "{:<6} | {:<8} | {:>6} | {:>8}".format(
                asset,
                data["status"],
                data["points"],
                len(data["features"]),
            )
        )

    print()


# =============================================================================
# CONTRACT
# =============================================================================

def print_contract(
    market_state
):

    valid = validate_market_state(
        market_state
    )

    ready_assets = 0

    for asset in EXPECTED_ASSETS:

        if (
            market_state[asset]["status"]
            == "READY"
        ):
            ready_assets += 1

    print("=" * 78)
    print("MARKET STATE CONTRACT")
    print("=" * 78)

    print(
        "Expected Assets :",
        len(EXPECTED_ASSETS)
    )

    print(
        "Ready Assets    :",
        ready_assets
    )

    print(
        "Window Size     :",
        WINDOW_SIZE
    )

    print(
        "Features        :",
        len(EXPECTED_FEATURES)
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
        "Signal Engine   : NOT USED"
    )

    print(
        "Scoring         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    if valid:

        print(
            "Contract Status : VALID"
        )

    else:

        print(
            "Contract Status : INVALID"
        )

    print()

    return valid


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    try:

        market_state = (
            load_market_state()
        )

        print_state(
            market_state
        )

        contract_valid = (
            print_contract(
                market_state
            )
        )

        if contract_valid:

            print(
                "MARKET STATE READER STATUS : READY"
            )

            return 0

        print(
            "MARKET STATE READER STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 78)
        print("MARKET STATE READER ERROR")
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
            "MARKET STATE READER STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )