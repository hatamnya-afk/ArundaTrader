# =============================================================================
# ARUNDA TRADER — FEATURE CONTRACT ADAPTER v0.3
# =============================================================================
#
# PURPOSE
# -------
# Validate and expose the real Feature Engine output as a structured
# Feature Snapshot.
#
# ARCHITECTURE
# ------------
#
# REAL OHLCV
#     |
#     v
# REAL INDICATORS
#     |
#     v
# FEATURE BAR
#     |
#     v
# feature_engine.calculate_feature_records()
#     |
#     v
# FEATURE CONTRACT
#
#
# CONTEXT CONTRACT
# ----------------
#
# FULL_CONTEXT_TARGET = 150
# MIN_CONTEXT         = 21
#
# 150 is the FULL context target.
# 150 is NOT a minimum requirement.
#
# Real context is classified as:
#
#     < 21       -> NONE
#     21..149    -> LIMITED
#     >= 150     -> FULL
#
# IMPORTANT
# ---------
# The contract NEVER fabricates missing bars.
#
# NO:
#   padding
#   interpolation
#   forward fill
#   backward fill
#   duplication
#   synthetic bars
#   synthetic features
#
# Storage:
#   MEMORY ONLY
#
# Database:
#   NONE
#
# SQL:
#   NOT USED
#
# =============================================================================


from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Sequence

import feature_engine


# =============================================================================
# VERSION
# =============================================================================

ENGINE_VERSION = "FEATURE_CONTRACT_v0.3"


# =============================================================================
# CONTEXT CONTRACT
# =============================================================================

FULL_CONTEXT_TARGET = 150

MIN_CONTEXT = 21

# Backward-compatible alias.
WINDOW_SIZE = FULL_CONTEXT_TARGET


# =============================================================================
# EXPECTED ASSETS
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


# =============================================================================
# CONTEXT CLASSIFICATION
# =============================================================================

def classify_context(
    actual_points: int,
) -> str:
    """
    Classify the real available market context.

    Contract:

        < 21       -> NONE
        21..149    -> LIMITED
        >= 150     -> FULL
    """

    try:
        points = int(actual_points)

    except (
        TypeError,
        ValueError,
    ) as error:

        raise RuntimeError(
            "Invalid context point count: "
            + repr(actual_points)
        ) from error

    if points < MIN_CONTEXT:
        return "NONE"

    if points < FULL_CONTEXT_TARGET:
        return "LIMITED"

    return "FULL"


# =============================================================================
# COMPATIBILITY ALIAS
# =============================================================================

def _context_status(
    actual_points: int,
) -> str:
    """
    Internal compatibility alias.
    """

    return classify_context(
        actual_points
    )


# =============================================================================
# NUMERIC HELPERS
# =============================================================================

def _safe_float(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        result = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(result):
        return None

    return result


# =============================================================================
# ASSET NORMALIZATION
# =============================================================================

def _normalize_asset(
    asset: Any,
) -> Optional[str]:

    if asset is None:
        return None

    value = str(
        asset
    ).strip().upper()

    if not value:
        return None

    return value


# =============================================================================
# RECORD CONVERSION
# =============================================================================

def _record_to_mapping(
    record: Any,
) -> Mapping[str, Any]:

    if isinstance(
        record,
        Mapping,
    ):
        return record

    if hasattr(
        record,
        "__dict__",
    ):

        data = vars(
            record
        )

        if isinstance(
            data,
            dict,
        ):
            return data

    raise RuntimeError(
        "Unsupported FeatureRecord type: "
        + type(record).__name__
    )


# =============================================================================
# FEATURE RECORD VALIDATION
# =============================================================================

def validate_feature_record(
    record: Any,
) -> bool:
    """
    Validate one real FeatureRecord.

    The actual feature names are owned by feature_engine.py.
    This contract does NOT rename or fabricate them.
    """

    try:
        data = _record_to_mapping(
            record
        )

    except RuntimeError:
        return False

    if not isinstance(
        data,
        Mapping,
    ):
        return False

    if "index" not in data:
        return False

    try:
        index = int(
            data["index"]
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if index < 0:
        return False

    return True


# =============================================================================
# BUILD ONE ASSET
# =============================================================================

def build_asset_features(
    asset: str,
    bars: Sequence[Any],
    indicator_records: Sequence[Any],
    structure_records: Optional[
        Sequence[Any]
    ] = None,
) -> dict:
    """
    Build validated Feature Contract output for one asset.

    IMPORTANT:
    The actual number of real points is preserved.

    Example:

        132 real bars
        132 real indicators
        132 real feature records

    becomes:

        points = 132
        context = LIMITED

    Nothing is added to reach 150.
    """

    normalized_asset = _normalize_asset(
        asset
    )

    if normalized_asset is None:
        raise RuntimeError(
            "Invalid asset name: "
            + repr(asset)
        )

    if normalized_asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            "Unexpected asset: "
            + normalized_asset
        )

    if bars is None:
        raise RuntimeError(
            "Bars are missing for asset: "
            + normalized_asset
        )

    if indicator_records is None:
        raise RuntimeError(
            "Indicator records are missing for asset: "
            + normalized_asset
        )

    try:
        actual_points = len(
            bars
        )

    except TypeError as error:

        raise RuntimeError(
            "Bars must be a sized sequence for asset: "
            + normalized_asset
        ) from error

    if actual_points <= 0:

        raise RuntimeError(
            "Feature Contract received no real bars for asset: "
            + normalized_asset
        )

    # -------------------------------------------------------------------------
    # REAL INPUT COUNT
    # -------------------------------------------------------------------------

    if len(
        indicator_records
    ) != actual_points:

        raise RuntimeError(
            "Indicator count mismatch for "
            + normalized_asset
            + ": expected "
            + str(actual_points)
            + ", received "
            + str(len(indicator_records))
        )

    # -------------------------------------------------------------------------
    # OPTIONAL STRUCTURE INPUT
    # -------------------------------------------------------------------------

    if structure_records is not None:

        if len(
            structure_records
        ) != actual_points:

            raise RuntimeError(
                "Structure count mismatch for "
                + normalized_asset
                + ": expected "
                + str(actual_points)
                + ", received "
                + str(len(structure_records))
            )

    # -------------------------------------------------------------------------
    # CONTEXT
    # -------------------------------------------------------------------------

    context = classify_context(
        actual_points
    )

    # -------------------------------------------------------------------------
    # MINIMUM COMPUTATIONAL CONTEXT
    # -------------------------------------------------------------------------

    if actual_points < MIN_CONTEXT:

        return {
            "asset": normalized_asset,
            "status": "READY",
            "context": context,
            "points": actual_points,
            "features": [],
        }

    # -------------------------------------------------------------------------
    # REAL FEATURE ENGINE
    # -------------------------------------------------------------------------

    if not hasattr(
        feature_engine,
        "calculate_feature_records",
    ):

        raise RuntimeError(
            "feature_engine.py must expose "
            "calculate_feature_records()"
        )

    records = (
        feature_engine
        .calculate_feature_records(
            bars,
            indicator_records,
            structure_records,
        )
    )

    if records is None:

        raise RuntimeError(
            "Feature Engine returned None for asset: "
            + normalized_asset
        )

    try:
        record_count = len(
            records
        )

    except TypeError as error:

        raise RuntimeError(
            "Feature Engine returned a non-sized result for asset: "
            + normalized_asset
        ) from error

    # -------------------------------------------------------------------------
    # OUTPUT COUNT MUST MATCH REAL INPUT COUNT
    # -------------------------------------------------------------------------

    if record_count != actual_points:

        raise RuntimeError(
            "Feature Engine output count mismatch for "
            + normalized_asset
            + ": expected "
            + str(actual_points)
            + ", received "
            + str(record_count)
        )

    # -------------------------------------------------------------------------
    # VALIDATE EACH REAL RECORD
    # -------------------------------------------------------------------------

    features = []

    for position, record in enumerate(
        records
    ):

        if not validate_feature_record(
            record
        ):

            raise RuntimeError(
                "Invalid FeatureRecord for "
                + normalized_asset
                + " at position "
                + str(position)
            )

        data = dict(
            _record_to_mapping(
                record
            )
        )

        # ---------------------------------------------------------------------
        # Ensure index is a real integer.
        # ---------------------------------------------------------------------

        try:
            data["index"] = int(
                data["index"]
            )

        except (
            TypeError,
            ValueError,
        ) as error:

            raise RuntimeError(
                "Invalid FeatureRecord index for "
                + normalized_asset
                + " at position "
                + str(position)
            ) from error

        features.append(
            data
        )

    # -------------------------------------------------------------------------
    # FINAL CONTRACT
    # -------------------------------------------------------------------------

    return {
        "asset": normalized_asset,
        "status": "READY",
        "context": context,
        "points": actual_points,
        "features": features,
    }


# =============================================================================
# BUILD ALL FEATURES
# =============================================================================

def build_features(
    bars_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    indicators_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    structures_by_asset: Optional[
        Mapping[
            str,
            Sequence[Any],
        ]
    ] = None,
) -> dict:
    """
    Build the complete validated Feature Snapshot.

    Inputs must come from the real upstream runtime.

    This function does not query the database and does not manufacture data.
    """

    if not isinstance(
        bars_by_asset,
        Mapping,
    ):

        raise RuntimeError(
            "bars_by_asset must be a mapping."
        )

    if not isinstance(
        indicators_by_asset,
        Mapping,
    ):

        raise RuntimeError(
            "indicators_by_asset must be a mapping."
        )

    if structures_by_asset is not None:

        if not isinstance(
            structures_by_asset,
            Mapping,
        ):

            raise RuntimeError(
                "structures_by_asset must be a mapping or None."
            )

    # -------------------------------------------------------------------------
    # ASSET KEY VALIDATION
    # -------------------------------------------------------------------------

    expected = set(
        EXPECTED_ASSETS
    )

    actual_bars = {
        _normalize_asset(
            key
        )
        for key in bars_by_asset.keys()
    }

    actual_indicators = {
        _normalize_asset(
            key
        )
        for key in indicators_by_asset.keys()
    }

    if actual_bars != expected:

        missing = expected - actual_bars
        extra = actual_bars - expected

        if missing:

            raise RuntimeError(
                "Missing bar assets: "
                + repr(
                    sorted(
                        missing
                    )
                )
            )

        if extra:

            raise RuntimeError(
                "Unexpected bar assets: "
                + repr(
                    sorted(
                        extra
                    )
                )
            )

    if actual_indicators != expected:

        missing = (
            expected
            - actual_indicators
        )

        extra = (
            actual_indicators
            - expected
        )

        if missing:

            raise RuntimeError(
                "Missing indicator assets: "
                + repr(
                    sorted(
                        missing
                    )
                )
            )

        if extra:

            raise RuntimeError(
                "Unexpected indicator assets: "
                + repr(
                    sorted(
                        extra
                    )
                )
            )

    if structures_by_asset is not None:

        actual_structures = {
            _normalize_asset(
                key
            )
            for key in structures_by_asset.keys()
        }

        if actual_structures != expected:

            missing = (
                expected
                - actual_structures
            )

            extra = (
                actual_structures
                - expected
            )

            if missing:

                raise RuntimeError(
                    "Missing structure assets: "
                    + repr(
                        sorted(
                            missing
                        )
                    )
                )

            if extra:

                raise RuntimeError(
                    "Unexpected structure assets: "
                    + repr(
                        sorted(
                            extra
                        )
                    )
                )

    # -------------------------------------------------------------------------
    # BUILD
    # -------------------------------------------------------------------------

    snapshot = {}

    for asset in EXPECTED_ASSETS:

        bars = bars_by_asset[
            asset
        ]

        indicators = indicators_by_asset[
            asset
        ]

        structures = None

        if structures_by_asset is not None:

            structures = structures_by_asset[
                asset
            ]

        snapshot[asset] = (
            build_asset_features(
                asset,
                bars,
                indicators,
                structures,
            )
        )

    # -------------------------------------------------------------------------
    # FINAL SNAPSHOT VALIDATION
    # -------------------------------------------------------------------------

    if not validate_feature_snapshot(
        snapshot
    ):

        raise RuntimeError(
            "Feature Contract generated an invalid snapshot."
        )

    return snapshot


# =============================================================================
# LOAD FEATURE SNAPSHOT
# =============================================================================
#
# This is the API consumed by downstream layers such as SIGNAL SCORER.
#
# It intentionally requires real upstream inputs.
#
# There is NO zero-argument loader.
#
# =============================================================================

def load_feature_snapshot(
    bars_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    indicators_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    structures_by_asset: Optional[
        Mapping[
            str,
            Sequence[Any],
        ]
    ] = None,
) -> dict:

    return build_features(
        bars_by_asset,
        indicators_by_asset,
        structures_by_asset,
    )


# =============================================================================
# VALIDATE ONE ASSET SNAPSHOT
# =============================================================================

def validate_asset_features(
    asset: str,
    data: Any,
) -> bool:

    normalized_asset = _normalize_asset(
        asset
    )

    if normalized_asset not in EXPECTED_ASSETS:
        return False

    if not isinstance(
        data,
        Mapping,
    ):
        return False

    if data.get(
        "asset"
    ) != normalized_asset:
        return False

    if data.get(
        "status"
    ) != "READY":
        return False

    if "context" not in data:
        return False

    if "points" not in data:
        return False

    if "features" not in data:
        return False

    # -------------------------------------------------------------------------
    # POINT COUNT
    # -------------------------------------------------------------------------

    try:
        points = int(
            data["points"]
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if points <= 0:
        return False

    # -------------------------------------------------------------------------
    # CONTEXT
    # -------------------------------------------------------------------------

    expected_context = (
        classify_context(
            points
        )
    )

    if data.get(
        "context"
    ) != expected_context:

        return False

    # -------------------------------------------------------------------------
    # FEATURE RECORD COUNT
    # -------------------------------------------------------------------------

    features = data.get(
        "features"
    )

    if not isinstance(
        features,
        list,
    ):
        return False

    # IMPORTANT:
    # Feature count must equal actual real point count.
    # It must NOT equal WINDOW_SIZE unless the real context is FULL.
    if len(
        features
    ) != points:

        return False

    # -------------------------------------------------------------------------
    # FEATURE RECORDS
    # -------------------------------------------------------------------------

    for record in features:

        if not validate_feature_record(
            record
        ):
            return False

    # -------------------------------------------------------------------------
    # INDEX ORDER
    # -------------------------------------------------------------------------

    indexes = []

    for record in features:

        try:
            index = int(
                _record_to_mapping(
                    record
                )["index"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return False

        indexes.append(
            index
        )

    if indexes != sorted(
        indexes
    ):
        return False

    return True


# =============================================================================
# VALIDATE COMPLETE FEATURE SNAPSHOT
# =============================================================================

def validate_feature_snapshot(
    snapshot: Any,
) -> bool:
    """
    Validate the complete 15-asset Feature Snapshot.
    """

    if not isinstance(
        snapshot,
        Mapping,
    ):
        return False

    if len(
        snapshot
    ) != EXPECTED_ASSET_COUNT:
        return False

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        snapshot.keys()
    )

    if actual != expected:
        return False

    for asset in EXPECTED_ASSETS:

        if not validate_asset_features(
            asset,
            snapshot.get(
                asset
            ),
        ):
            return False

    return True


# =============================================================================
# CONTRACT REPORT
# =============================================================================

def print_contract(
    snapshot: Optional[
        Mapping[str, Any]
    ] = None,
) -> bool:

    print("=" * 82)
    print(
        "ARUNDA TRADER — FEATURE CONTRACT ADAPTER v0.3"
    )
    print("=" * 82)

    print(
        "Engine Version    :",
        ENGINE_VERSION,
    )

    print(
        "Expected Assets   :",
        EXPECTED_ASSET_COUNT,
    )

    print(
        "Full Context      :",
        FULL_CONTEXT_TARGET,
    )

    print(
        "Minimum Context   :",
        MIN_CONTEXT,
    )

    print(
        "Context Contract  :",
        "NONE<21 / LIMITED=21..149 / FULL>=150",
    )

    print(
        "Storage           : MEMORY ONLY"
    )

    print(
        "Database writes   : NONE"
    )

    print(
        "SQL               : NOT USED"
    )

    print(
        "Synthetic data    : NONE"
    )

    print(
        "Padding           : NONE"
    )

    print(
        "Interpolation     : NONE"
    )

    print(
        "Forward fill      : NONE"
    )

    print(
        "Backward fill     : NONE"
    )

    print(
        "Status            : READY"
    )

    # -------------------------------------------------------------------------
    # Optional runtime snapshot report
    # -------------------------------------------------------------------------

    if snapshot is not None:

        print()
        print(
            "RUNTIME SNAPSHOT"
        )
        print(
            "-" * 82
        )

        for asset in EXPECTED_ASSETS:

            item = snapshot.get(
                asset
            )

            if not isinstance(
                item,
                Mapping,
            ):

                print(
                    "{:<6} INVALID".format(
                        asset
                    )
                )

                continue

            print(
                "{:<6} points={:<3} context={}".format(
                    asset,
                    item.get(
                        "points"
                    ),
                    item.get(
                        "context"
                    ),
                )
            )

        print()
        print(
            "Snapshot Valid    :",
            validate_feature_snapshot(
                snapshot
            ),
        )

    print()

    return True


# =============================================================================
# SELF TEST
# =============================================================================
#
# Self-test intentionally tests the CONTRACT classification only.
#
# It does NOT create fake market bars or fake FeatureRecords.
#
# =============================================================================

def self_test() -> bool:

    # -------------------------------------------------------------------------
    # Context boundaries
    # -------------------------------------------------------------------------

    assert (
        classify_context(0)
        == "NONE"
    )

    assert (
        classify_context(20)
        == "NONE"
    )

    assert (
        classify_context(21)
        == "LIMITED"
    )

    assert (
        classify_context(22)
        == "LIMITED"
    )

    assert (
        classify_context(149)
        == "LIMITED"
    )

    assert (
        classify_context(150)
        == "FULL"
    )

    assert (
        classify_context(151)
        == "FULL"
    )

    # -------------------------------------------------------------------------
    # Contract constants
    # -------------------------------------------------------------------------

    assert (
        WINDOW_SIZE
        == FULL_CONTEXT_TARGET
    )

    assert (
        EXPECTED_ASSET_COUNT
        == 15
    )

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():

    self_test()

    print_contract()


if __name__ == "__main__":
    main()