
"""
ARUNDA TRADER — REAL SCORE PRODUCER v0.1

Purpose
-------
Consume the REAL in-memory Feature Snapshot produced by
runtime_feature_producer and produce REAL asset scores.

Pipeline
--------
REAL market_data
    |
    v
runtime_feature_producer
    |
    v
REAL Feature Snapshot
    |
    v
REAL SCORE PRODUCER
    |
    v
REAL SCORES

Rules
-----
- REAL DATA ONLY
- NO SYNTHETIC DATA
- NO FALLBACK DATA
- NO DATABASE WRITES
- READ ONLY
- MEMORY ONLY
- NO SIGNAL GENERATION
- NO DECISION
- NO RISK
- NO TRADE
- SCORE FORMULA MUST NOT CHANGE
"""

from __future__ import annotations

import math
from typing import Any


# =============================================================================
# CONFIG
# =============================================================================

ENGINE_VERSION = "REAL_SCORE_PRODUCER_v0.1"

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
# AUTHORITATIVE SCORE FEATURES
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


# =============================================================================
# AUTHORITATIVE SCORE FORMULA
# =============================================================================
#
# return_20       0.20
# momentum_20     0.20
# trend_slope_20  0.20
# acceleration    0.10
# position_20     0.10
# volatility_20   0.10
# range_20        0.10
#
# Total = 1.00
#
# IMPORTANT:
# Do not modify these weights.
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
# DIRECTIONAL FEATURES
# =============================================================================

DIRECTIONAL_FEATURES = {
    "return_20",
    "momentum_20",
    "trend_slope_20",
    "acceleration",
}


# =============================================================================
# NUMERICAL HELPERS
# =============================================================================

def safe_float(
    value: Any,
    feature_name: str,
) -> float:

    try:
        result = float(value)

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise RuntimeError(
            f"Invalid numeric value for feature "
            f"{feature_name}: {value!r}"
        ) from exc

    if not math.isfinite(result):

        raise RuntimeError(
            f"Non-finite value for feature "
            f"{feature_name}: {value!r}"
        )

    return result


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


# =============================================================================
# WEIGHT VALIDATION
# =============================================================================

def validate_weights() -> None:

    missing = [
        feature
        for feature in REQUIRED_FEATURES
        if feature not in WEIGHTS
    ]

    if missing:

        raise RuntimeError(
            "Score weights missing for features: "
            + ", ".join(missing)
        )

    extra = [
        feature
        for feature in WEIGHTS
        if feature not in REQUIRED_FEATURES
    ]

    if extra:

        raise RuntimeError(
            "Unexpected score weights: "
            + ", ".join(extra)
        )

    total = sum(
        float(
            WEIGHTS[feature]
        )
        for feature in REQUIRED_FEATURES
    )

    if not math.isfinite(total):

        raise RuntimeError(
            "Score weight total is non-finite."
        )

    if abs(total - 1.0) > 1e-12:

        raise RuntimeError(
            f"Score weights must sum to 1.0. "
            f"Actual={total}"
        )


# =============================================================================
# FEATURE SNAPSHOT NORMALIZATION
# =============================================================================

def normalize_asset(
    asset: str,
    asset_data: Any,
) -> dict[str, Any]:

    if not isinstance(
        asset_data,
        dict,
    ):

        raise RuntimeError(
            f"{asset}: invalid Feature Snapshot asset data."
        )

    return asset_data


# =============================================================================
# FEATURE SNAPSHOT VALIDATION
# =============================================================================

def validate_feature_snapshot(
    feature_snapshot: Any,
) -> None:

    if not isinstance(
        feature_snapshot,
        dict,
    ):

        raise RuntimeError(
            "Feature Snapshot must be a dictionary."
        )

    missing_assets = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in feature_snapshot
    ]

    if missing_assets:

        raise RuntimeError(
            "Feature Snapshot missing assets: "
            + ", ".join(missing_assets)
        )

    for asset in EXPECTED_ASSETS:

        asset_data = normalize_asset(
            asset,
            feature_snapshot[asset],
        )

        if "features" not in asset_data:

            raise RuntimeError(
                f"{asset}: Feature Snapshot has no "
                "'features' field."
            )

        features = asset_data["features"]

        if not isinstance(
            features,
            list,
        ):

            raise RuntimeError(
                f"{asset}: Feature Snapshot "
                "'features' must be a list."
            )

        if not features:

            raise RuntimeError(
                f"{asset}: Feature Snapshot "
                "contains no features."
            )

        context = asset_data.get(
            "context",
            "UNKNOWN",
        )

        if context not in {
            "NONE",
            "LIMITED",
            "FULL",
        }:

            raise RuntimeError(
                f"{asset}: invalid feature context: "
                f"{context!r}"
            )


# =============================================================================
# LATEST FEATURE RECORD
# =============================================================================

def get_latest_feature_record(
    asset: str,
    asset_data: dict[str, Any],
) -> dict[str, Any]:

    features = asset_data["features"]

    if not features:

        raise RuntimeError(
            f"{asset}: no feature records available."
        )

    record = features[-1]

    if isinstance(
        record,
        dict,
    ):

        return record

    if hasattr(
        record,
        "__dict__",
    ):

        return vars(record)

    raise RuntimeError(
        f"{asset}: latest feature record has "
        "unsupported type: "
        f"{type(record).__name__}"
    )


# =============================================================================
# REQUIRED FEATURE VALIDATION
# =============================================================================

def validate_required_features(
    asset: str,
    record: dict[str, Any],
) -> None:

    missing = [
        feature
        for feature in REQUIRED_FEATURES
        if feature not in record
    ]

    if missing:

        raise RuntimeError(
            f"{asset}: required score features missing: "
            + ", ".join(missing)
        )


# =============================================================================
# FEATURE NORMALIZATION
# =============================================================================

def normalize_component(
    name: str,
    value: Any,
) -> float:

    raw = safe_float(
        value,
        name,
    )

    # -------------------------------------------------------------------------
    # Directional features
    # -------------------------------------------------------------------------

    if name in DIRECTIONAL_FEATURES:

        return clamp(
            raw,
            -1.0,
            1.0,
        )

    # -------------------------------------------------------------------------
    # Position feature
    # -------------------------------------------------------------------------

    if name == "position_20":

        centered = (
            2.0 * raw
        ) - 1.0

        return clamp(
            centered,
            -1.0,
            1.0,
        )

    # -------------------------------------------------------------------------
    # Volatility / range
    #
    # No arbitrary normalization is permitted.
    # -------------------------------------------------------------------------

    if name in {
        "volatility_20",
        "range_20",
    }:

        raise RuntimeError(
            "Authoritative normalization is not available "
            f"for feature: {name}"
        )

    raise RuntimeError(
        f"Unsupported score feature: {name}"
    )


# =============================================================================
# SCORE CALCULATION
# =============================================================================

def calculate_score(
    record: dict[str, Any],
) -> float:

    total = 0.0

    for feature in REQUIRED_FEATURES:

        normalized = normalize_component(
            feature,
            record[feature],
        )

        weighted = (
            WEIGHTS[feature]
            * normalized
        )

        total += weighted

    if not math.isfinite(total):

        raise RuntimeError(
            "Calculated score is non-finite."
        )

    return total


# =============================================================================
# ASSET SCORE
# =============================================================================

def build_asset_score(
    asset: str,
    asset_data: dict[str, Any],
) -> dict[str, Any]:

    record = get_latest_feature_record(
        asset,
        asset_data,
    )

    validate_required_features(
        asset,
        record,
    )

    score = calculate_score(
        record,
    )

    return {
        "asset": asset,
        "feature_context": asset_data.get(
            "context",
            "UNKNOWN",
        ),
        "feature_count": len(
            asset_data["features"]
        ),
        "score": score,
        "score_status": "READY",
        "engine_version": ENGINE_VERSION,
    }


# =============================================================================
# BUILD REAL SCORES
# =============================================================================

def build_scores(
    feature_snapshot: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    validate_feature_snapshot(
        feature_snapshot
    )

    scores = {}

    for asset in EXPECTED_ASSETS:

        scores[asset] = build_asset_score(
            asset,
            feature_snapshot[asset],
        )

    return scores


# =============================================================================
# SCORE SNAPSHOT CONTRACT
# =============================================================================

def validate_score_snapshot(
    scores: Any,
) -> None:

    if not isinstance(
        scores,
        dict,
    ):

        raise RuntimeError(
            "Score Snapshot must be a dictionary."
        )

    missing_assets = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in scores
    ]

    if missing_assets:

        raise RuntimeError(
            "Score Snapshot missing assets: "
            + ", ".join(missing_assets)
        )

    for asset in EXPECTED_ASSETS:

        row = scores[asset]

        if not isinstance(
            row,
            dict,
        ):

            raise RuntimeError(
                f"{asset}: invalid score row."
            )

        required_fields = (
            "asset",
            "feature_context",
            "feature_count",
            "score",
            "score_status",
            "engine_version",
        )

        missing = [
            field
            for field in required_fields
            if field not in row
        ]

        if missing:

            raise RuntimeError(
                f"{asset}: score row missing fields: "
                + ", ".join(missing)
            )

        if row["asset"] != asset:

            raise RuntimeError(
                f"{asset}: asset identity mismatch."
            )

        feature_count = row[
            "feature_count"
        ]

        if not isinstance(
            feature_count,
            int,
        ):

            raise RuntimeError(
                f"{asset}: feature_count must be integer."
            )

        if feature_count <= 0:

            raise RuntimeError(
                f"{asset}: invalid feature_count="
                f"{feature_count}"
            )

        score = safe_float(
            row["score"],
            f"{asset}.score",
        )

        if score < -1.0 or score > 1.0:

            raise RuntimeError(
                f"{asset}: score outside [-1, 1]: "
                f"{score}"
            )

        if row["score_status"] != "READY":

            raise RuntimeError(
                f"{asset}: score_status is not READY."
            )

        if row["engine_version"] != ENGINE_VERSION:

            raise RuntimeError(
                f"{asset}: engine version mismatch."
            )


# =============================================================================
# REAL FEATURE SNAPSHOT LOADER
# =============================================================================

def load_real_feature_snapshot():

    import runtime_feature_producer

    # -------------------------------------------------------------------------
    # REAL READ-ONLY DATABASE CONNECTION
    # -------------------------------------------------------------------------

    conn = runtime_feature_producer.connect_readonly()

    try:

        # =====================================================================
        # REAL OHLCV BARS
        #
        # IMPORTANT:
        # The active runtime_feature_producer API exposes
        # build_bars_by_asset(conn).
        #
        # The function internally resolves the authoritative
        # real OHLCV source.
        # =====================================================================

        bars_by_asset = (
            runtime_feature_producer
            .build_bars_by_asset(
                conn
            )
        )

        if not isinstance(
            bars_by_asset,
            dict,
        ):

            raise RuntimeError(
                "runtime_feature_producer.build_bars_by_asset() "
                "returned invalid data."
            )

        # =====================================================================
        # REAL INDICATORS
        # =====================================================================

        indicators_by_asset = (
            runtime_feature_producer
            .build_indicators_by_asset(
                bars_by_asset
            )
        )

        if not isinstance(
            indicators_by_asset,
            dict,
        ):

            raise RuntimeError(
                "runtime_feature_producer."
                "build_indicators_by_asset() "
                "returned invalid data."
            )

        # =====================================================================
        # REAL FEATURE BARS
        #
        # IMPORTANT:
        # build_feature_bars_by_asset() consumes bars_by_asset.
        # =====================================================================

        feature_bars_by_asset = (
            runtime_feature_producer
            .build_feature_bars_by_asset(
                bars_by_asset
            )
        )

        if not isinstance(
            feature_bars_by_asset,
            dict,
        ):

            raise RuntimeError(
                "runtime_feature_producer."
                "build_feature_bars_by_asset() "
                "returned invalid data."
            )

        # =====================================================================
        # REAL FEATURE SNAPSHOT
        # =====================================================================

        feature_snapshot = (
            runtime_feature_producer
            .build_feature_snapshot(
                feature_bars_by_asset,
                indicators_by_asset,
            )
        )

        if not isinstance(
            feature_snapshot,
            dict,
        ):

            raise RuntimeError(
                "Runtime Feature Producer returned "
                "an invalid Feature Snapshot."
            )

        return feature_snapshot

    finally:

        conn.close()


# =============================================================================
# SCORE REPORT
# =============================================================================

def print_scores(
    scores: dict[str, dict[str, Any]],
) -> None:

    print()

    print("=" * 90)

    print(
        "ARUNDA TRADER — REAL SCORE PRODUCER RESULT"
    )

    print("=" * 90)

    print()

    for asset in EXPECTED_ASSETS:

        row = scores[asset]

        print(
            f"{asset:<6} | "
            f"context={row['feature_context']:<7} | "
            f"features={row['feature_count']:<3} | "
            f"score={row['score']:+.8f} | "
            f"status={row['score_status']}"
        )

    print()


# =============================================================================
# SCORE CONTRACT REPORT
# =============================================================================

def print_contract(
    scores: dict[str, dict[str, Any]],
) -> None:

    print(
        "Score Snapshot   : "
        + (
            "VALID"
            if all(
                row["score_status"] == "READY"
                for row in scores.values()
            )
            else "INVALID"
        )
    )

    print(
        "Score Formula    : "
        "0.20R + 0.20M + 0.20T + "
        "0.10A + 0.10P + 0.10V + 0.10RG"
    )

    print(
        "Synthetic Data   : NONE"
    )

    print(
        "Database Writes  : NONE"
    )

    print(
        "Execution        : DISABLED"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 100)

    print(
        "ARUNDA TRADER — REAL SCORE PRODUCER v0.1"
    )

    print("=" * 100)

    print()

    print(
        "SOURCE : runtime_feature_producer"
    )

    print(
        "DATA   : REAL market_data"
    )

    print(
        "MODE   : READ ONLY / MEMORY ONLY"
    )

    print()

    # =========================================================================
    # [1] WEIGHTS
    # =========================================================================

    print(
        "[1/4] SCORE FORMULA VALIDATION"
    )

    validate_weights()

    print(
        "  Weights          : VALID"
    )

    print(
        "  Weight Sum       : 1.000000"
    )

    print()

    # =========================================================================
    # [2] REAL FEATURE SNAPSHOT
    # =========================================================================

    print(
        "[2/4] REAL FEATURE SNAPSHOT"
    )

    feature_snapshot = (
        load_real_feature_snapshot()
    )

    validate_feature_snapshot(
        feature_snapshot
    )

    print(
        "  Feature Snapshot : VALID"
    )

    print()

    # =========================================================================
    # [3] REAL SCORES
    # =========================================================================

    print(
        "[3/4] REAL SCORE GENERATION"
    )

    scores = build_scores(
        feature_snapshot
    )

    print_scores(
        scores
    )

    # =========================================================================
    # [4] SCORE CONTRACT
    # =========================================================================

    print(
        "[4/4] SCORE CONTRACT"
    )

    validate_score_snapshot(
        scores
    )

    print_contract(
        scores
    )

    print()

    print("=" * 100)

    print(
        "RUNTIME STATUS : PASS"
    )

    print("=" * 100)


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    main()