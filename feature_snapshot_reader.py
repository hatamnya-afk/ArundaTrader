import feature_contract
import runtime_feature_producer


# =============================================================================
# ARUNDA FEATURE SNAPSHOT READER v0.7
# =============================================================================
# Feature Contract -> In-Memory Feature Snapshot
#
# CONTRACT:
#   <21        -> NONE / NOT CONSUMABLE
#   21..149    -> LIMITED / VALID
#   >=150      -> FULL / VALID
#
# RUNTIME SOURCE:
#   runtime_feature_producer v0.5
#
# DATA FLOW:
#   READ-ONLY DB
#       ->
#   REAL IndicatorBar
#       ->
#   REAL IndicatorRecord
#       ->
#   REAL Structure Records
#       ->
#   REAL FeatureBar
#       ->
#   feature_contract
#       ->
#   Feature Snapshot
#       ->
#   Consumer Validation
#
# READ ONLY / MEMORY ONLY
# NO DATABASE WRITE
# NO SYNTHETIC DATA
# NO PADDING
# NO INTERPOLATION
# NO FORWARD FILL
# NO BACK FILL
# EXECUTION DISABLED
#
# IMPORTANT RUNTIME BOUNDARIES:
#
#   build_bars_by_asset(conn)
#       -> IndicatorBar
#
#   build_indicators_by_asset(bars_by_asset)
#       -> IndicatorRecord
#
#   build_structures_by_asset(bars_by_asset)
#       -> Structure Records
#
#   build_feature_bars_by_asset(bars_by_asset)
#       -> FeatureBar
#
#   feature_contract.load_feature_snapshot(
#       feature_bars_by_asset,
#       indicators_by_asset,
#       structures_by_asset,
#   )
#       -> Feature Snapshot
#
# DO NOT PASS indicators_by_asset TO build_structures_by_asset().
# STRUCTURE PRODUCER CONSUMES bars_by_asset.
# =============================================================================


ENGINE_VERSION = "FEATURE_SNAPSHOT_READER_v0.7"

MIN_CONTEXT = 21
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
# CONTEXT CLASSIFICATION
# =============================================================================

def classify_context(points):

    if not isinstance(points, int):
        raise RuntimeError(
            "Invalid points type"
        )

    if points < 0:
        raise RuntimeError(
            "Invalid negative points"
        )

    if points < MIN_CONTEXT:
        return "NONE"

    if points < WINDOW_SIZE:
        return "LIMITED"

    return "FULL"


# =============================================================================
# RUNTIME INPUTS
# =============================================================================

def build_runtime_inputs():

    conn = None

    try:

        # ---------------------------------------------------------------------
        # READ-ONLY CONNECTION
        # ---------------------------------------------------------------------

        conn = (
            runtime_feature_producer.connect_readonly()
        )

        # ---------------------------------------------------------------------
        # REAL INDICATOR BARS
        #
        # OUTPUT:
        #   Dict[asset, List[IndicatorBar]]
        # ---------------------------------------------------------------------

        bars_by_asset = (
            runtime_feature_producer.build_bars_by_asset(
                conn
            )
        )

        # ---------------------------------------------------------------------
        # INDICATORS
        #
        # INPUT:
        #   IndicatorBar
        #
        # OUTPUT:
        #   IndicatorRecord
        # ---------------------------------------------------------------------

        indicators_by_asset = (
            runtime_feature_producer.build_indicators_by_asset(
                bars_by_asset
            )
        )

        # ---------------------------------------------------------------------
        # STRUCTURES
        #
        # CRITICAL:
        #
        # build_structures_by_asset() consumes bars_by_asset.
        #
        # WRONG:
        #   build_structures_by_asset(indicators_by_asset)
        #
        # CORRECT:
        #   build_structures_by_asset(bars_by_asset)
        # ---------------------------------------------------------------------

        structures_by_asset = (
            runtime_feature_producer.build_structures_by_asset(
                bars_by_asset
            )
        )

        # ---------------------------------------------------------------------
        # FEATURE BAR ADAPTER
        #
        # Producer:
        #   IndicatorBar -> FeatureBar
        #
        # Feature Contract / Feature Engine require FeatureBar.
        # ---------------------------------------------------------------------

        feature_bars_by_asset = (
            runtime_feature_producer.build_feature_bars_by_asset(
                bars_by_asset
            )
        )

        return (
            bars_by_asset,
            indicators_by_asset,
            structures_by_asset,
            feature_bars_by_asset,
        )

    finally:

        if conn is not None:
            conn.close()


# =============================================================================
# RUNTIME INPUT VALIDATION
# =============================================================================

def validate_runtime_inputs(
    bars_by_asset,
    indicators_by_asset,
    structures_by_asset,
    feature_bars_by_asset,
):

    if not isinstance(
        bars_by_asset,
        dict,
    ):
        raise RuntimeError(
            "Invalid bars_by_asset"
        )

    if not isinstance(
        indicators_by_asset,
        dict,
    ):
        raise RuntimeError(
            "Invalid indicators_by_asset"
        )

    if not isinstance(
        structures_by_asset,
        dict,
    ):
        raise RuntimeError(
            "Invalid structures_by_asset"
        )

    if not isinstance(
        feature_bars_by_asset,
        dict,
    ):
        raise RuntimeError(
            "Invalid feature_bars_by_asset"
        )

    for asset in EXPECTED_ASSETS:

        # ---------------------------------------------------------------------
        # ASSET PRESENCE
        # ---------------------------------------------------------------------

        if asset not in bars_by_asset:

            raise RuntimeError(
                "Missing runtime bars: "
                + asset
            )

        if asset not in indicators_by_asset:

            raise RuntimeError(
                "Missing runtime indicators: "
                + asset
            )

        if asset not in structures_by_asset:

            raise RuntimeError(
                "Missing runtime structures: "
                + asset
            )

        if asset not in feature_bars_by_asset:

            raise RuntimeError(
                "Missing runtime feature bars: "
                + asset
            )

        # ---------------------------------------------------------------------
        # CARDINALITY
        # ---------------------------------------------------------------------

        real_count = len(
            bars_by_asset[asset]
        )

        indicator_count = len(
            indicators_by_asset[asset]
        )

        structure_count = len(
            structures_by_asset[asset]
        )

        feature_bar_count = len(
            feature_bars_by_asset[asset]
        )

        if real_count != indicator_count:

            raise RuntimeError(
                "Bars/Indicator cardinality mismatch: "
                + asset
                + " | REAL="
                + str(real_count)
                + " | IND="
                + str(indicator_count)
            )

        if real_count != structure_count:

            raise RuntimeError(
                "Bars/Structure cardinality mismatch: "
                + asset
                + " | REAL="
                + str(real_count)
                + " | STRUCT="
                + str(structure_count)
            )

        if real_count != feature_bar_count:

            raise RuntimeError(
                "Bars/FeatureBar cardinality mismatch: "
                + asset
                + " | REAL="
                + str(real_count)
                + " | FEATURE_BAR="
                + str(feature_bar_count)
            )


# =============================================================================
# LOAD FEATURE SNAPSHOT
# =============================================================================

def load_feature_snapshot(
    feature_bars_by_asset,
    indicators_by_asset,
    structures_by_asset=None,
):

    snapshot = (
        feature_contract.load_feature_snapshot(
            feature_bars_by_asset,
            indicators_by_asset,
            structures_by_asset,
        )
    )

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "feature_contract returned invalid snapshot"
        )

    result = {}

    for asset in EXPECTED_ASSETS:

        # ---------------------------------------------------------------------
        # ASSET
        # ---------------------------------------------------------------------

        if asset not in snapshot:

            raise RuntimeError(
                "Missing asset: "
                + asset
            )

        source = snapshot[asset]

        if not isinstance(
            source,
            dict,
        ):

            raise RuntimeError(
                "Invalid snapshot for asset: "
                + asset
            )

        # ---------------------------------------------------------------------
        # STATUS
        # ---------------------------------------------------------------------

        if source.get("status") != "READY":

            raise RuntimeError(
                "Asset not READY: "
                + asset
            )

        # ---------------------------------------------------------------------
        # POINTS
        # ---------------------------------------------------------------------

        points = source.get(
            "points"
        )

        if not isinstance(
            points,
            int,
        ):

            raise RuntimeError(
                "Invalid points for asset: "
                + asset
            )

        # ---------------------------------------------------------------------
        # CONTEXT
        # ---------------------------------------------------------------------

        expected_context = (
            classify_context(points)
        )

        source_context = source.get(
            "context"
        )

        if source_context != expected_context:

            raise RuntimeError(
                "Context mismatch for asset: "
                + asset
                + " | expected="
                + expected_context
                + " | actual="
                + str(source_context)
            )

        # ---------------------------------------------------------------------
        # MINIMUM CONTEXT
        # ---------------------------------------------------------------------

        if points < MIN_CONTEXT:

            raise RuntimeError(
                "Insufficient feature context for asset: "
                + asset
                + " | points="
                + str(points)
                + " | minimum="
                + str(MIN_CONTEXT)
            )

        # ---------------------------------------------------------------------
        # FEATURES
        # ---------------------------------------------------------------------

        features = source.get(
            "features"
        )

        if not isinstance(
            features,
            list,
        ):

            raise RuntimeError(
                "Invalid features collection for asset: "
                + asset
            )

        # ---------------------------------------------------------------------
        # FEATURE CARDINALITY
        # ---------------------------------------------------------------------

        if len(features) != points:

            raise RuntimeError(
                "Feature cardinality mismatch for asset: "
                + asset
                + " | points="
                + str(points)
                + " | features="
                + str(len(features))
            )

        # ---------------------------------------------------------------------
        # FEATURE RECORD VALIDATION
        # ---------------------------------------------------------------------

        for feature in features:

            if not isinstance(
                feature,
                dict,
            ):

                raise RuntimeError(
                    "Invalid feature record for asset: "
                    + asset
                )

        # ---------------------------------------------------------------------
        # MEMORY SNAPSHOT
        # ---------------------------------------------------------------------

        result[asset] = {
            "asset": asset,
            "status": "READY",
            "points": points,
            "context": expected_context,
            "features": list(features),
        }

    return result


# =============================================================================
# SNAPSHOT VALIDATION
# =============================================================================

def validate_snapshot(snapshot):

    if not isinstance(
        snapshot,
        dict,
    ):
        return False

    if len(snapshot) != len(
        EXPECTED_ASSETS
    ):
        return False

    for asset in EXPECTED_ASSETS:

        if asset not in snapshot:
            return False

        data = snapshot[asset]

        if not isinstance(
            data,
            dict,
        ):
            return False

        # ---------------------------------------------------------------------
        # ASSET
        # ---------------------------------------------------------------------

        if data.get("asset") != asset:
            return False

        # ---------------------------------------------------------------------
        # STATUS
        # ---------------------------------------------------------------------

        if data.get("status") != "READY":
            return False

        # ---------------------------------------------------------------------
        # POINTS
        # ---------------------------------------------------------------------

        points = data.get(
            "points"
        )

        if not isinstance(
            points,
            int,
        ):
            return False

        if points < MIN_CONTEXT:
            return False

        # ---------------------------------------------------------------------
        # CONTEXT
        # ---------------------------------------------------------------------

        expected_context = (
            classify_context(points)
        )

        if data.get("context") != expected_context:
            return False

        # ---------------------------------------------------------------------
        # FEATURES
        # ---------------------------------------------------------------------

        features = data.get(
            "features"
        )

        if not isinstance(
            features,
            list,
        ):
            return False

        # ---------------------------------------------------------------------
        # CARDINALITY
        # ---------------------------------------------------------------------

        if len(features) != points:
            return False

        # ---------------------------------------------------------------------
        # FEATURE RECORDS
        # ---------------------------------------------------------------------

        for feature in features:

            if not isinstance(
                feature,
                dict,
            ):
                return False

    return True


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 78)

    print(
        "ARUNDA FEATURE SNAPSHOT READER v0.7"
    )

    print("=" * 78)

    print(
        "Engine   :",
        ENGINE_VERSION
    )

    print(
        "Source   : runtime_feature_producer v0.5"
    )

    print(
        "Contract : feature_contract"
    )

    print(
        "Storage  : MEMORY ONLY"
    )

    print(
        "Writes   : NONE"
    )

    print(
        "SQL      : PRODUCER READ-ONLY ONLY"
    )

    print(
        "Signals  : NOT USED"
    )

    print(
        "Scoring  : NOT USED"
    )

    print(
        "Minimum Context :",
        MIN_CONTEXT
    )

    print(
        "Full Context    :",
        WINDOW_SIZE
    )

    print("=" * 78)

    print()


# =============================================================================
# SNAPSHOT PRINT
# =============================================================================

def print_snapshot(snapshot):

    print(
        "FEATURE SNAPSHOT"
    )

    print("-" * 78)

    print(
        "Asset  | Status   | Points | Context | Features"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:

        data = snapshot[asset]

        print(
            "{:<6} | {:<8} | {:>6} | {:<7} | {:>8}".format(
                asset,
                data["status"],
                data["points"],
                data["context"],
                len(data["features"]),
            )
        )

    print()


# =============================================================================
# CONTRACT REPORT
# =============================================================================

def print_contract(snapshot):

    valid = validate_snapshot(
        snapshot
    )

    ready_assets = 0
    limited_assets = 0
    full_assets = 0

    for asset in EXPECTED_ASSETS:

        data = snapshot[asset]

        if data["status"] == "READY":
            ready_assets += 1

        if data["context"] == "LIMITED":
            limited_assets += 1

        elif data["context"] == "FULL":
            full_assets += 1

    print("=" * 78)

    print(
        "FEATURE SNAPSHOT CONTRACT"
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
        "LIMITED Assets  :",
        limited_assets
    )

    print(
        "FULL Assets     :",
        full_assets
    )

    print(
        "Minimum Context :",
        MIN_CONTEXT
    )

    print(
        "Full Context    :",
        WINDOW_SIZE
    )

    print(
        "Accepted Range  : 21..infinity"
    )

    print(
        "LIMITED Range   : 21..149"
    )

    print(
        "FULL Range      : >=150"
    )

    print(
        "Features Type   : list"
    )

    print(
        "Cardinality     : len(features) == points"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
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

        # ---------------------------------------------------------------------
        # 1. BUILD REAL RUNTIME INPUTS
        # ---------------------------------------------------------------------

        (
            bars_by_asset,
            indicators_by_asset,
            structures_by_asset,
            feature_bars_by_asset,
        ) = build_runtime_inputs()

        # ---------------------------------------------------------------------
        # 2. VERIFY INPUT CARDINALITY
        # ---------------------------------------------------------------------

        validate_runtime_inputs(
            bars_by_asset,
            indicators_by_asset,
            structures_by_asset,
            feature_bars_by_asset,
        )

        # ---------------------------------------------------------------------
        # 3. LOAD FEATURE SNAPSHOT
        # ---------------------------------------------------------------------

        snapshot = load_feature_snapshot(
            feature_bars_by_asset,
            indicators_by_asset,
            structures_by_asset,
        )

        # ---------------------------------------------------------------------
        # 4. PRINT SNAPSHOT
        # ---------------------------------------------------------------------

        print_snapshot(
            snapshot
        )

        # ---------------------------------------------------------------------
        # 5. CONTRACT VALIDATION
        # ---------------------------------------------------------------------

        contract_valid = print_contract(
            snapshot
        )

        if not contract_valid:

            print(
                "RUNTIME STATUS      : FAIL"
            )

            print(
                "CONSUMER CONTRACT   : INVALID"
            )

            print(
                "FEATURE SNAPSHOT READER STATUS : FAILED"
            )

            return 1

        # ---------------------------------------------------------------------
        # 6. FINAL RESULT
        # ---------------------------------------------------------------------

        print(
            "RUNTIME STATUS      : PASS"
        )

        print(
            "CONSUMER CONTRACT   : VALID"
        )

        print(
            "FEATURE SNAPSHOT READER STATUS : READY"
        )

        return 0

    except Exception as error:

        print("=" * 78)

        print(
            "FEATURE SNAPSHOT READER ERROR"
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
            "RUNTIME STATUS      : FAIL"
        )

        print(
            "FEATURE SNAPSHOT READER STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )