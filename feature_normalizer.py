import math
import feature_snapshot_reader


# =============================================================================
# ARUNDA FEATURE NORMALIZER v0.2
# Feature Snapshot -> Normalized Feature Snapshot
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


# =============================================================================
# FEATURES TO NORMALIZE
# =============================================================================

NORMALIZE_FEATURES = [
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
# SNAPSHOT VALIDATION
# =============================================================================

def validate_snapshot(snapshots):

    if not isinstance(snapshots, dict):
        raise RuntimeError(
            "Feature snapshot must be a dictionary"
        )

    for asset in EXPECTED_ASSETS:

        if asset not in snapshots:
            raise RuntimeError(
                "Missing asset: " + asset
            )

        data = snapshots[asset]

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid snapshot for asset: " + asset
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

    return True


# =============================================================================
# NUMERIC VALIDATION
# =============================================================================

def numeric_value(value):

    try:
        number = float(value)

    except (TypeError, ValueError):

        raise RuntimeError(
            "Non-numeric feature value"
        )

    if not math.isfinite(number):

        raise RuntimeError(
            "Non-finite feature value"
        )

    return number


# =============================================================================
# COLLECT FEATURE VALUES
# =============================================================================

def collect_feature_values(
    snapshots,
    feature_name
):

    values = []

    for asset in EXPECTED_ASSETS:

        features = snapshots[asset]["features"]

        if feature_name not in features:

            raise RuntimeError(
                "Missing feature '{}' for {}".format(
                    feature_name,
                    asset
                )
            )

        value = numeric_value(
            features[feature_name]
        )

        values.append(value)

    return values


# =============================================================================
# MIN-MAX NORMALIZATION
# =============================================================================

def normalize_values(values):

    minimum = min(values)
    maximum = max(values)

    if maximum == minimum:

        return [
            0.0
            for _ in values
        ]

    normalized = []

    for value in values:

        result = (
            (value - minimum)
            / (maximum - minimum)
        )

        normalized.append(result)

    return normalized


# =============================================================================
# BUILD NORMALIZED SNAPSHOT
# =============================================================================

def build_normalized_features():

    snapshots = (
        feature_snapshot_reader.load_feature_snapshot()
    )

    validate_snapshot(
        snapshots
    )

    normalized_snapshot = {}

    for asset in EXPECTED_ASSETS:

        normalized_snapshot[asset] = {
            "asset": asset,
            "status": "READY",
            "points": WINDOW_SIZE,
            "features": {},
        }

    for feature_name in NORMALIZE_FEATURES:

        values = collect_feature_values(
            snapshots,
            feature_name
        )

        normalized_values = normalize_values(
            values
        )

        for index, asset in enumerate(
            EXPECTED_ASSETS
        ):

            normalized_snapshot[asset]["features"][
                feature_name
            ] = normalized_values[index]

    return normalized_snapshot


# =============================================================================
# PUBLIC API
# =============================================================================

def load_normalized_features():

    return build_normalized_features()


# =============================================================================
# VALIDATION OF NORMALIZED OUTPUT
# =============================================================================

def validate_normalized_snapshot(
    snapshot
):

    if not isinstance(snapshot, dict):
        return False

    if len(snapshot) != len(
        EXPECTED_ASSETS
    ):
        return False

    for asset in EXPECTED_ASSETS:

        if asset not in snapshot:
            return False

        data = snapshot[asset]

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

        for feature_name in NORMALIZE_FEATURES:

            if feature_name not in features:
                return False

            try:

                value = float(
                    features[feature_name]
                )

            except (TypeError, ValueError):

                return False

            if not math.isfinite(value):
                return False

            if value < 0.0:
                return False

            if value > 1.0:
                return False

    return True


# =============================================================================
# PRINT HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print("ARUNDA FEATURE NORMALIZER v0.2")
    print("=" * 78)

    print(
        "Source   : feature_snapshot_reader"
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

    print("=" * 78)
    print()


# =============================================================================
# PRINT SNAPSHOT
# =============================================================================

def print_snapshot(snapshot):

    print(
        "NORMALIZED FEATURE SNAPSHOT"
    )

    print("-" * 78)

    print(
        "Asset  | Status   | Points | Ret20N   | Vol20N   | Pos20N"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:

        data = snapshot[asset]

        features = data["features"]

        print(
            "{:<6} | {:<8} | {:>6} | {:>8.5f} | {:>8.5f} | {:>8.5f}".format(
                asset,
                data["status"],
                data["points"],
                features["return_20"],
                features["volatility_20"],
                features["position_20"],
            )
        )

    print()


# =============================================================================
# CONTRACT
# =============================================================================

def print_contract(snapshot):

    valid = validate_normalized_snapshot(
        snapshot
    )

    ready_assets = 0

    for asset in EXPECTED_ASSETS:

        if snapshot[asset]["status"] == "READY":

            ready_assets += 1

    print("=" * 78)
    print(
        "NORMALIZATION CONTRACT"
    )
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
        len(NORMALIZE_FEATURES)
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

        snapshot = (
            load_normalized_features()
        )

        print_snapshot(
            snapshot
        )

        contract_valid = (
            print_contract(
                snapshot
            )
        )

        if contract_valid:

            print(
                "FEATURE NORMALIZER STATUS : READY"
            )

            return 0

        print(
            "FEATURE NORMALIZER STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 78)
        print(
            "FEATURE NORMALIZER ERROR"
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
            "FEATURE NORMALIZER STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )