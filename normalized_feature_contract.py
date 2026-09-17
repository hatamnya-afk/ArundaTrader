import math
import feature_normalizer


# =============================================================================
# ARUNDA NORMALIZED FEATURE CONTRACT v0.1
# Normalized Feature Engine -> In-Memory Contract
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
# LOAD NORMALIZED FEATURES
# =============================================================================

def load_normalized_features():

    if hasattr(
        feature_normalizer,
        "load_normalized_features"
    ):
        return (
            feature_normalizer
            .load_normalized_features()
        )

    raise RuntimeError(
        "feature_normalizer.py must expose "
        "load_normalized_features()"
    )


# =============================================================================
# NUMERIC VALIDATION
# =============================================================================

def validate_numeric(value):

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    if not math.isfinite(number):
        return False

    return True


# =============================================================================
# BUILD CONTRACT
# =============================================================================

def build_contract():

    source = load_normalized_features()

    if not isinstance(source, dict):
        raise RuntimeError(
            "Normalized Feature Engine returned invalid data"
        )

    if len(source) != len(EXPECTED_ASSETS):
        raise RuntimeError(
            "Invalid asset count"
        )

    contract = {}

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

            value = features[feature_name]

            if not validate_numeric(value):
                raise RuntimeError(
                    "Invalid numeric value for "
                    "{}: {}".format(
                        feature_name,
                        asset
                    )
                )

            number = float(value)

            if number < 0.0 or number > 1.0:
                raise RuntimeError(
                    "Feature out of normalized range "
                    "{}: {}".format(
                        feature_name,
                        asset
                    )
                )

        contract[asset] = {
            "asset": asset,
            "status": "READY",
            "points": WINDOW_SIZE,
            "features": dict(features),
        }

    return contract


# =============================================================================
# PUBLIC API
# =============================================================================

def load_normalized_feature_contract():

    return build_contract()


# =============================================================================
# CONTRACT VALIDATION
# =============================================================================

def validate_contract(contract):

    if not isinstance(contract, dict):
        return False

    if len(contract) != len(EXPECTED_ASSETS):
        return False

    for asset in EXPECTED_ASSETS:

        if asset not in contract:
            return False

        data = contract[asset]

        if data.get("status") != "READY":
            return False

        if data.get("points") != WINDOW_SIZE:
            return False

        features = data.get("features")

        if not isinstance(features, dict):
            return False

        for feature_name in EXPECTED_FEATURES:

            if feature_name not in features:
                return False

            value = features[feature_name]

            if not validate_numeric(value):
                return False

            number = float(value)

            if number < 0.0 or number > 1.0:
                return False

    return True


# =============================================================================
# PRINT HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print("ARUNDA NORMALIZED FEATURE CONTRACT v0.1")
    print("=" * 78)

    print("Source   : feature_normalizer")
    print("Storage  : MEMORY ONLY")
    print("Writes   : NONE")
    print("SQL      : NOT USED")
    print("Signals  : NOT USED")
    print("Scoring  : NOT USED")
    print("Window   :", WINDOW_SIZE)
    print("Features :", len(EXPECTED_FEATURES))

    print("=" * 78)
    print()


# =============================================================================
# PRINT SNAPSHOT
# =============================================================================

def print_snapshot(contract):

    print("NORMALIZED FEATURE SNAPSHOT")
    print("-" * 78)

    print(
        "Asset  | Status   | Points | Features"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:

        data = contract[asset]

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
# PRINT CONTRACT
# =============================================================================

def print_contract(contract):

    valid = validate_contract(
        contract
    )

    ready_assets = 0

    for asset in EXPECTED_ASSETS:

        if contract[asset]["status"] == "READY":
            ready_assets += 1

    print("=" * 78)
    print("NORMALIZED FEATURE CONTRACT")
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
        "Value Range     : 0.0 -> 1.0"
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

        contract = (
            load_normalized_feature_contract()
        )

        print_snapshot(
            contract
        )

        contract_valid = (
            print_contract(
                contract
            )
        )

        if contract_valid:

            print(
                "NORMALIZED FEATURE CONTRACT STATUS : READY"
            )

            return 0

        print(
            "NORMALIZED FEATURE CONTRACT STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 78)
        print("NORMALIZED FEATURE CONTRACT ERROR")
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
            "NORMALIZED FEATURE CONTRACT STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )