"""
ARUNDA TRADER — RUNTIME FEATURE PRODUCER
RECONSTRUCTED v0.5

IMPORTANT:
    This is a reconstructed implementation because the original
    runtime_feature_producer.py was not recoverable from available backups.

Architecture:
    market_data
        ->
    REAL OHLCV
        ->
    IndicatorBar
        ->
    Indicator Engine
        ->
    IndicatorRecord
        ->
    MarketBar
        ->
    Market Structure Engine
        ->
    Structure Records
        ->
    FeatureBar
        ->
    Feature Contract
        ->
    Feature Engine
        ->
    Feature Snapshot

Rules:
    - READ ONLY database access
    - NO database writes
    - NO synthetic data
    - NO interpolation
    - NO forward fill
    - NO back fill
    - NO duplicated bars
    - NO fabricated indicators
    - NO fabricated structure
    - strict causal structure construction
    - execution disabled
"""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, List, Mapping, Optional, Sequence


# ============================================================================
# ENGINE IMPORTS
# ============================================================================

from indicator_engine import (
    IndicatorBar,
    calculate_indicator_records,
    validate_indicator_collection,
)

from market_structure_engine import (
    MarketBar,
    analyze_market_structure,
)

from feature_engine import (
    FeatureBar,
)

from feature_contract import (
    ENGINE_VERSION,
    FULL_CONTEXT_TARGET,
    MIN_CONTEXT,
    classify_context,
    load_feature_snapshot,
    validate_feature_snapshot,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

ENGINE_NAME = (
    "RECONSTRUCTED_RUNTIME_FEATURE_PRODUCER_v0.5"
)

DB = "arunda.db"

WINDOW_SIZE = FULL_CONTEXT_TARGET
MIN_CONTEXT_POINTS = MIN_CONTEXT

STRUCTURE_LEFT_BARS = 2
STRUCTURE_RIGHT_BARS = 2

EXPECTED_ASSETS = (
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
)


# ============================================================================
# GENERIC ACCESS HELPERS
# ============================================================================

def _get(
    obj: Any,
    field: str,
    default: Any = None,
) -> Any:

    if isinstance(obj, Mapping):
        return obj.get(
            field,
            default,
        )

    return getattr(
        obj,
        field,
        default,
    )


def _safe_float(
    value: Any,
) -> Optional[float]:

    if value is None:
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


def _normalize_asset(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip().upper()


def _normalize_direction(
    value: Any,
) -> str:

    if value is None:
        return "NEUTRAL"

    value = str(value).strip().upper()

    if value in {
        "BULLISH",
        "BEARISH",
        "NEUTRAL",
    }:
        return value

    return "NEUTRAL"


def _normalize_strength(
    value: Any,
) -> str:

    if value is None:
        return "WEAK"

    value = str(value).strip().upper()

    if value in {
        "WEAK",
        "MODERATE",
        "STRONG",
    }:
        return value

    return "WEAK"


def _normalize_confidence(
    value: Any,
) -> str:

    if value is None:
        return "LOW"

    value = str(value).strip().upper()

    if value in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }:
        return value

    return "LOW"


# ============================================================================
# DATABASE — READ ONLY
# ============================================================================

def connect_readonly() -> sqlite3.Connection:

    uri = f"file:{DB}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================================
# REAL OHLCV SOURCE
# ============================================================================

def resolve_real_ohlcv_source(
    conn: sqlite3.Connection,
) -> str:

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    tables = {
        str(row["name"]).strip().lower()
        for row in rows
    }

    if "market_data" in tables:
        return "market_data"

    raise RuntimeError(
        "REAL OHLCV source not found: market_data"
    )


# ============================================================================
# SQLITE ROW -> INDICATOR BAR
# ============================================================================

def _row_to_indicator_bar(
    row: sqlite3.Row,
) -> IndicatorBar:

    timestamp = row["timestamp"]

    high = _safe_float(
        row["high"]
    )

    low = _safe_float(
        row["low"]
    )

    close = _safe_float(
        row["close"]
    )

    if high is None:
        raise ValueError(
            "Invalid high value."
        )

    if low is None:
        raise ValueError(
            "Invalid low value."
        )

    if close is None:
        raise ValueError(
            "Invalid close value."
        )

    open_value = None

    if "open" in row.keys():
        open_value = _safe_float(
            row["open"]
        )

    volume = None

    if "volume" in row.keys():
        volume = _safe_float(
            row["volume"]
        )

    cmc_id = None

    if "cmc_id" in row.keys():
        cmc_id = row["cmc_id"]

    symbol = None

    if "symbol" in row.keys():
        symbol = row["symbol"]

    return IndicatorBar(
        timestamp=timestamp,
        high=high,
        low=low,
        close=close,
        open=open_value,
        volume=volume,
        cmc_id=cmc_id,
        symbol=symbol,
    )


# ============================================================================
# REAL BARS BY ASSET
# ============================================================================

def build_bars_by_asset(
    conn: sqlite3.Connection,
) -> Dict[str, List[IndicatorBar]]:

    source = resolve_real_ohlcv_source(
        conn
    )

    result: Dict[
        str,
        List[IndicatorBar],
    ] = {}

    for asset in EXPECTED_ASSETS:

        rows = conn.execute(
            f"""
            SELECT *
            FROM {source}
            WHERE UPPER(symbol) = ?
              AND timestamp IS NOT NULL
              AND high IS NOT NULL
              AND low IS NOT NULL
              AND close IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (
                asset,
                WINDOW_SIZE,
            ),
        ).fetchall()

        bars: List[IndicatorBar] = []

        for row in rows:

            try:

                bar = _row_to_indicator_bar(
                    row
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            bars.append(
                bar
            )

        # SQL returned newest -> oldest.
        # Runtime engines require chronological order.
        bars.reverse()

        result[asset] = bars

    return result


# ============================================================================
# INDICATOR ENGINE
# ============================================================================

def build_indicators_by_asset(
    bars_by_asset: Mapping[
        str,
        Sequence[IndicatorBar],
    ],
) -> Dict[str, List[Any]]:

    result: Dict[
        str,
        List[Any],
    ] = {}

    for asset in EXPECTED_ASSETS:

        bars = list(
            bars_by_asset.get(
                asset,
                [],
            )
        )

        if not bars:

            result[asset] = []

            continue

        indicators = (
            calculate_indicator_records(
                bars
            )
        )

        validate_indicator_collection(
            indicators
        )

        if len(indicators) != len(bars):

            raise RuntimeError(
                f"Indicator cardinality mismatch for "
                f"{asset}: "
                f"bars={len(bars)} "
                f"indicators={len(indicators)}"
            )

        result[asset] = list(
            indicators
        )

    return result


# ============================================================================
# INDICATOR BAR -> MARKET BAR
# ============================================================================

def _indicator_bar_to_market_bar(
    bar: IndicatorBar,
) -> MarketBar:

    """
    Explicit model boundary:

        IndicatorBar -> MarketBar

    No transformation of market values occurs.
    """

    timestamp = _get(
        bar,
        "timestamp",
    )

    high = _safe_float(
        _get(
            bar,
            "high",
        )
    )

    low = _safe_float(
        _get(
            bar,
            "low",
        )
    )

    close = _safe_float(
        _get(
            bar,
            "close",
        )
    )

    if high is None:
        raise ValueError(
            "IndicatorBar contains invalid high."
        )

    if low is None:
        raise ValueError(
            "IndicatorBar contains invalid low."
        )

    if close is None:
        raise ValueError(
            "IndicatorBar contains invalid close."
        )

    open_value = _safe_float(
        _get(
            bar,
            "open",
        )
    )

    volume = _safe_float(
        _get(
            bar,
            "volume",
        )
    )

    cmc_id = _get(
        bar,
        "cmc_id",
    )

    symbol = _get(
        bar,
        "symbol",
    )

    return MarketBar(
        timestamp=timestamp,
        high=high,
        low=low,
        close=close,
        open=open_value,
        volume=volume,
        cmc_id=cmc_id,
        symbol=symbol,
    )


# ============================================================================
# EMPTY / COLD STRUCTURE RECORD
# ============================================================================

def _empty_structure_record(
    bar: IndicatorBar,
    index: int,
) -> Dict[str, Any]:

    return {
        "index": index,
        "timestamp": _get(
            bar,
            "timestamp",
        ),
        "cmc_id": _get(
            bar,
            "cmc_id",
        ),
        "symbol": _get(
            bar,
            "symbol",
        ),

        "direction": "NEUTRAL",
        "strength": "WEAK",
        "confidence": "LOW",

        "structure": None,
        "type": None,

        "bos": False,
        "is_bos": False,

        "choch": False,
        "is_choch": False,

        "last_structure_price": None,
        "previous_structure_price": None,
    }


# ============================================================================
# CAUSAL MARKET STRUCTURE
# ============================================================================

def _build_causal_structure_records(
    bars: Sequence[IndicatorBar],
) -> List[Dict[str, Any]]:

    """
    For bar i:

        ONLY bars[0:i+1]

    are supplied to Market Structure Engine.

    This prevents the Runtime Feature Producer from requesting
    future bars relative to the current feature timestamp.

    Market Structure Engine requires >= 3 bars, therefore
    indexes 0 and 1 use explicit cold-start structure values.
    """

    result: List[
        Dict[str, Any]
    ] = []

    for index, bar in enumerate(
        bars
    ):

        # ------------------------------------------------------------
        # COLD START
        # ------------------------------------------------------------

        if index < 2:

            result.append(
                _empty_structure_record(
                    bar,
                    index,
                )
            )

            continue

        # ------------------------------------------------------------
        # CAUSAL PREFIX
        # ------------------------------------------------------------

        indicator_prefix = list(
            bars[
                : index + 1
            ]
        )

        # ------------------------------------------------------------
        # CRITICAL TYPE BOUNDARY
        #
        # IndicatorBar is NOT accepted by Market Structure Engine.
        #
        # Convert each bar explicitly to MarketBar.
        # ------------------------------------------------------------

        market_prefix: List[
            MarketBar
        ] = []

        for source_bar in (
            indicator_prefix
        ):

            market_prefix.append(
                _indicator_bar_to_market_bar(
                    source_bar
                )
            )

        # ------------------------------------------------------------
        # MARKET STRUCTURE ENGINE
        # ------------------------------------------------------------

        analysis = (
            analyze_market_structure(
                market_prefix,
                left_bars=STRUCTURE_LEFT_BARS,
                right_bars=STRUCTURE_RIGHT_BARS,
            )
        )

        direction = (
            _normalize_direction(
                analysis.get(
                    "direction"
                )
            )
        )

        strength = (
            _normalize_strength(
                analysis.get(
                    "strength"
                )
            )
        )

        confidence = (
            _normalize_confidence(
                analysis.get(
                    "confidence"
                )
            )
        )

        structure_points = list(
            analysis.get(
                "structure_points",
                [],
            )
        )

        events = list(
            analysis.get(
                "events",
                [],
            )
        )

        # ------------------------------------------------------------
        # CURRENT / AVAILABLE STRUCTURE
        # ------------------------------------------------------------

        available_structures = [
            point
            for point in structure_points
            if point.index <= index
        ]

        latest_structure = None
        previous_structure = None

        if available_structures:

            latest_structure = (
                available_structures[-1]
            )

            if len(
                available_structures
            ) >= 2:

                previous_structure = (
                    available_structures[-2]
                )

        structure_type = None

        if latest_structure is not None:

            structure_type = (
                latest_structure.structure_type
            )

        # ------------------------------------------------------------
        # CURRENT BAR EVENTS
        # ------------------------------------------------------------

        current_events = [
            event
            for event in events
            if event.index == index
        ]

        bos = any(
            event.event_type == "BOS"
            for event in current_events
        )

        choch = any(
            event.event_type == "CHoCH"
            for event in current_events
        )

        # ------------------------------------------------------------
        # RECORD
        # ------------------------------------------------------------

        result.append(
            {
                "index": index,

                "timestamp": _get(
                    bar,
                    "timestamp",
                ),

                "cmc_id": _get(
                    bar,
                    "cmc_id",
                ),

                "symbol": _get(
                    bar,
                    "symbol",
                ),

                "direction": direction,
                "strength": strength,
                "confidence": confidence,

                "structure": structure_type,
                "type": structure_type,

                "bos": bos,
                "is_bos": bos,

                "choch": choch,
                "is_choch": choch,

                "last_structure_price": (
                    latest_structure.price
                    if latest_structure
                    is not None
                    else None
                ),

                "previous_structure_price": (
                    previous_structure.price
                    if previous_structure
                    is not None
                    else None
                ),
            }
        )

    if len(result) != len(bars):

        raise RuntimeError(
            "Structure cardinality mismatch: "
            f"bars={len(bars)} "
            f"structures={len(result)}"
        )

    return result


# ============================================================================
# STRUCTURES BY ASSET
# ============================================================================

def build_structures_by_asset(
    bars_by_asset: Mapping[
        str,
        Sequence[IndicatorBar],
    ],
) -> Dict[
    str,
    List[Dict[str, Any]],
]:

    result: Dict[
        str,
        List[Dict[str, Any]],
    ] = {}

    for asset in EXPECTED_ASSETS:

        bars = list(
            bars_by_asset.get(
                asset,
                [],
            )
        )

        if not bars:

            result[asset] = []

            continue

        structures = (
            _build_causal_structure_records(
                bars
            )
        )

        result[asset] = structures

    return result


# ============================================================================
# INDICATOR BAR -> FEATURE BAR
# ============================================================================

def _indicator_bar_to_feature_bar(
    bar: IndicatorBar,
) -> FeatureBar:

    """
    Explicit model boundary:

        IndicatorBar -> FeatureBar

    This function only transfers existing REAL OHLCV/identity data.

    No interpolation.
    No padding.
    No calculated values.
    """

    timestamp = _get(
        bar,
        "timestamp",
    )

    high = _safe_float(
        _get(
            bar,
            "high",
        )
    )

    low = _safe_float(
        _get(
            bar,
            "low",
        )
    )

    close = _safe_float(
        _get(
            bar,
            "close",
        )
    )

    if high is None:
        raise ValueError(
            "IndicatorBar contains invalid high."
        )

    if low is None:
        raise ValueError(
            "IndicatorBar contains invalid low."
        )

    if close is None:
        raise ValueError(
            "IndicatorBar contains invalid close."
        )

    open_value = _safe_float(
        _get(
            bar,
            "open",
        )
    )

    volume = _safe_float(
        _get(
            bar,
            "volume",
        )
    )

    cmc_id = _get(
        bar,
        "cmc_id",
    )

    symbol = _get(
        bar,
        "symbol",
    )

    return FeatureBar(
        timestamp=timestamp,
        high=high,
        low=low,
        close=close,
        open=open_value,
        volume=volume,
        cmc_id=cmc_id,
        symbol=symbol,
    )


# ============================================================================
# FEATURE BARS BY ASSET
# ============================================================================

def build_feature_bars_by_asset(
    bars_by_asset: Mapping[
        str,
        Sequence[IndicatorBar],
    ],
) -> Dict[
    str,
    List[FeatureBar],
]:

    result: Dict[
        str,
        List[FeatureBar],
    ] = {}

    for asset in EXPECTED_ASSETS:

        source_bars = list(
            bars_by_asset.get(
                asset,
                [],
            )
        )

        feature_bars: List[
            FeatureBar
        ] = []

        for bar in source_bars:

            feature_bars.append(
                _indicator_bar_to_feature_bar(
                    bar
                )
            )

        if len(feature_bars) != len(
            source_bars
        ):

            raise RuntimeError(
                f"FeatureBar cardinality mismatch "
                f"for {asset}: "
                f"source={len(source_bars)} "
                f"feature={len(feature_bars)}"
            )

        result[asset] = feature_bars

    return result


# ============================================================================
# FEATURE SNAPSHOT
# ============================================================================

def build_feature_snapshot(
    bars_by_asset: Mapping[
        str,
        Sequence[IndicatorBar],
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
) -> Dict[str, Any]:

    if structures_by_asset is None:

        structures_by_asset = (
            build_structures_by_asset(
                bars_by_asset
            )
        )

    # ------------------------------------------------------------
    # CRITICAL FEATURE BOUNDARY
    #
    # Feature Contract / Feature Engine require FeatureBar.
    #
    # DO NOT pass bars_by_asset directly.
    # ------------------------------------------------------------

    feature_bars_by_asset = (
        build_feature_bars_by_asset(
            bars_by_asset
        )
    )

    # ------------------------------------------------------------
    # Feature Contract
    #
    # FeatureBar
    # IndicatorRecord
    # StructureRecord
    # ------------------------------------------------------------

    snapshot = load_feature_snapshot(
        feature_bars_by_asset,
        indicators_by_asset,
        structures_by_asset,
    )

    validate_feature_snapshot(
        snapshot
    )

    return snapshot


# ============================================================================
# RUNTIME CARDINALITY CHECK
# ============================================================================

def _runtime_cardinality_check(
    bars_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    indicators_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    structures_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    snapshot: Mapping[
        str,
        Any,
    ],
) -> None:

    for asset in EXPECTED_ASSETS:

        bars = list(
            bars_by_asset.get(
                asset,
                [],
            )
        )

        indicators = list(
            indicators_by_asset.get(
                asset,
                [],
            )
        )

        structures = list(
            structures_by_asset.get(
                asset,
                [],
            )
        )

        if asset not in snapshot:

            raise RuntimeError(
                f"Missing feature snapshot asset: "
                f"{asset}"
            )

        asset_snapshot = snapshot[
            asset
        ]

        points = int(
            asset_snapshot.get(
                "points",
                0,
            )
        )

        features = list(
            asset_snapshot.get(
                "features",
                [],
            )
        )

        # ------------------------------------------------------------
        # BAR / INDICATOR
        # ------------------------------------------------------------

        if len(indicators) != len(
            bars
        ):

            raise RuntimeError(
                f"{asset}: "
                f"bars={len(bars)} "
                f"indicators={len(indicators)}"
            )

        # ------------------------------------------------------------
        # BAR / STRUCTURE
        # ------------------------------------------------------------

        if len(structures) != len(
            bars
        ):

            raise RuntimeError(
                f"{asset}: "
                f"bars={len(bars)} "
                f"structures={len(structures)}"
            )

        # ------------------------------------------------------------
        # BAR / SNAPSHOT POINTS
        # ------------------------------------------------------------

        if points != len(bars):

            raise RuntimeError(
                f"{asset}: "
                f"bars={len(bars)} "
                f"snapshot_points={points}"
            )

        # ------------------------------------------------------------
        # BAR / FEATURE RECORDS
        # ------------------------------------------------------------

        if len(features) != len(
            bars
        ):

            raise RuntimeError(
                f"{asset}: "
                f"bars={len(bars)} "
                f"features={len(features)}"
            )


# ============================================================================
# STRUCTURE COLD START CHECK
# ============================================================================

def _runtime_structure_cold_start_check(
    bars_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
    structures_by_asset: Mapping[
        str,
        Sequence[Any],
    ],
) -> None:

    for asset in EXPECTED_ASSETS:

        bars = list(
            bars_by_asset.get(
                asset,
                [],
            )
        )

        structures = list(
            structures_by_asset.get(
                asset,
                [],
            )
        )

        if len(bars) < 2:
            continue

        if len(structures) < 2:

            raise RuntimeError(
                f"{asset}: structure cold-start "
                f"cardinality invalid."
            )

        first = structures[0]
        second = structures[1]

        for item in (
            first,
            second,
        ):

            if item.get(
                "direction"
            ) != "NEUTRAL":

                raise RuntimeError(
                    f"{asset}: cold-start "
                    f"direction is not NEUTRAL."
                )

            if item.get(
                "bos"
            ) is not False:

                raise RuntimeError(
                    f"{asset}: cold-start "
                    f"BOS is not False."
                )

            if item.get(
                "choch"
            ) is not False:

                raise RuntimeError(
                    f"{asset}: cold-start "
                    f"CHoCH is not False."
                )


# ============================================================================
# RUNTIME VERIFY
# ============================================================================

def runtime_verify() -> Dict[str, Any]:

    conn = connect_readonly()

    try:

        # ============================================================
        # STEP 1
        # REAL OHLCV
        # ============================================================

        bars_by_asset = (
            build_bars_by_asset(
                conn
            )
        )

        # ============================================================
        # STEP 2
        # INDICATORS
        # ============================================================

        indicators_by_asset = (
            build_indicators_by_asset(
                bars_by_asset
            )
        )

        # ============================================================
        # STEP 3
        # MARKET STRUCTURE
        # ============================================================

        structures_by_asset = (
            build_structures_by_asset(
                bars_by_asset
            )
        )

        _runtime_structure_cold_start_check(
            bars_by_asset,
            structures_by_asset,
        )

        # ============================================================
        # STEP 4
        # FEATURE SNAPSHOT
        # ============================================================

        snapshot = (
            build_feature_snapshot(
                bars_by_asset,
                indicators_by_asset,
                structures_by_asset,
            )
        )

        # ============================================================
        # STEP 5
        # CARDINALITY
        # ============================================================

        _runtime_cardinality_check(
            bars_by_asset,
            indicators_by_asset,
            structures_by_asset,
            snapshot,
        )

        # ============================================================
        # REPORT
        # ============================================================

        asset_report: Dict[
            str,
            Any,
        ] = {}

        for asset in EXPECTED_ASSETS:

            bars = list(
                bars_by_asset.get(
                    asset,
                    [],
                )
            )

            indicators = list(
                indicators_by_asset.get(
                    asset,
                    [],
                )
            )

            structures = list(
                structures_by_asset.get(
                    asset,
                    [],
                )
            )

            asset_snapshot = snapshot[
                asset
            ]

            points = int(
                asset_snapshot[
                    "points"
                ]
            )

            features = list(
                asset_snapshot.get(
                    "features",
                    [],
                )
            )

            context = classify_context(
                points
            )

            asset_report[asset] = {
                "real_points": len(
                    bars
                ),
                "indicator_points": len(
                    indicators
                ),
                "structure_points": len(
                    structures
                ),
                "feature_points": len(
                    features
                ),
                "context": context,
                "synthetic": "NONE",
            }

        return {
            "engine": ENGINE_NAME,
            "feature_contract": ENGINE_VERSION,

            "window_size": WINDOW_SIZE,
            "min_context": MIN_CONTEXT_POINTS,

            "assets": len(
                EXPECTED_ASSETS
            ),

            "asset_report": asset_report,

            "database": DB,
            "database_write": "NONE",

            "synthetic_data": "NONE",
            "interpolation": "NONE",
            "forward_fill": "NONE",
            "back_fill": "NONE",

            "execution_enabled": False,

            "feature_snapshot_valid": True,

            "status": "PASS",
        }

    finally:

        conn.close()


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print(
        "=" * 100
    )

    print(
        "ARUNDA TRADER — "
        "RECONSTRUCTED RUNTIME FEATURE PRODUCER v0.5"
    )

    print(
        "=" * 100
    )

    print(
        f"ENGINE              : {ENGINE_NAME}"
    )

    print(
        f"DATABASE            : {DB}"
    )

    print(
        f"WINDOW_SIZE         : {WINDOW_SIZE}"
    )

    print(
        f"MIN_CONTEXT         : {MIN_CONTEXT_POINTS}"
    )

    print(
        f"EXPECTED_ASSETS     : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        "DATABASE WRITE      : NONE"
    )

    print(
        "SYNTHETIC DATA      : NONE"
    )

    print(
        "INTERPOLATION       : NONE"
    )

    print(
        "FORWARD FILL        : NONE"
    )

    print(
        "BACK FILL           : NONE"
    )

    print(
        "EXECUTION           : DISABLED"
    )

    print(
        "-" * 100
    )

    report = runtime_verify()

    for asset in EXPECTED_ASSETS:

        item = report[
            "asset_report"
        ][asset]

        print(
            f"{asset:<6} | "
            f"REAL={item['real_points']:<4} | "
            f"IND={item['indicator_points']:<4} | "
            f"STRUCT={item['structure_points']:<4} | "
            f"FEATURE={item['feature_points']:<4} | "
            f"CONTEXT={item['context']:<7} | "
            f"SYNTHETIC={item['synthetic']}"
        )

    print(
        "-" * 100
    )

    print(
        "FEATURE SNAPSHOT    : "
        f"{'VALID' if report['feature_snapshot_valid'] else 'INVALID'}"
    )

    print(
        f"RUNTIME STATUS      : "
        f"{report['status']}"
    )

    print(
        "=" * 100
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    main()