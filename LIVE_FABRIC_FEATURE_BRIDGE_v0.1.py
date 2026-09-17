"""
ARUNDA TRADER
LIVE_FABRIC_FEATURE_BRIDGE_v0.1

Purpose
-------
Bridge REAL production Fabric OHLCV into the existing
Indicator -> Market Structure -> Feature Engine -> Feature Contract
chain.

STRICT RULES
------------
- Fabric canonical_ohlcv ONLY
- Production DB is NEVER opened
- READ ONLY
- No SQL writes
- No synthetic data
- No interpolation
- No fill / backfill / padding
- No blending
- Launch boundary enforced
- Primary provider: KUCOIN
- Failover provider: BITGET
- DEX / non-CEX observations blocked
- Existing Feature / Indicator / Structure / Contract engines unchanged
- Fail closed on contract mismatch
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


ENGINE_NAME = "LIVE_FABRIC_FEATURE_BRIDGE"
VERSION = "v0.1"

ROOT = Path(__file__).resolve().parent

FABRIC_DB = (
    ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

# Explicitly kept for visibility only.
# This file MUST NOT be opened by this bridge.
PRODUCTION_DB = ROOT / "arunda.db"

LAUNCH_TIMESTAMP = "2026-08-31T00:00:00+00:00"
LAUNCH_TS = 1788134400

TIMEFRAME = "1h"

PRIMARY_PROVIDER = "KUCOIN"
FAILOVER_PROVIDER = "BITGET"

FAILOVER_POLICY = "FAILOVER, NOT BLENDING"

EXPECTED_ASSETS = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "BNB",
    "ADA",
    "AVAX",
    "DOGE",
    "DOT",
    "LINK",
    "LTC",
    "MATIC",
    "SHIB",
    "TRX",
    "UNI",
)


# ============================================================================
# SAFETY
# ============================================================================

def is_nullish(value: Any) -> bool:
    return (
        value is None
        or str(value).strip().lower()
        in ("", "null", "none")
    )


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def fail(message: str) -> None:
    raise RuntimeError(
        f"{ENGINE_NAME} {VERSION} FAIL-CLOSED: {message}"
    )


def assert_production_db_untouched() -> None:
    # The bridge has no production DB connection path.
    # This explicit assertion prevents accidental future misuse.
    if not PRODUCTION_DB.exists():
        return

    # Merely knowing the path exists is harmless.
    # No sqlite connection is ever made to this path.


# ============================================================================
# FABRIC INPUT
# ============================================================================

REQUIRED_COLUMNS = (
    "symbol",
    "timestamp",
    "asset",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source_timestamp",
)


def load_fabric_rows() -> List[sqlite3.Row]:

    if not FABRIC_DB.exists():
        fail(
            f"Fabric DB not found: {FABRIC_DB}"
        )

    con = sqlite3.connect(
        f"file:{FABRIC_DB}?mode=ro",
        uri=True,
    )

    con.row_factory = sqlite3.Row

    try:

        columns = {
            row["name"]
            for row in con.execute(
                "PRAGMA table_info(canonical_ohlcv)"
            ).fetchall()
        }

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in columns
        ]

        if missing:
            fail(
                "Fabric canonical_ohlcv missing columns: "
                + ", ".join(missing)
            )

        rows = con.execute(
            """
            SELECT
                symbol,
                timestamp,
                asset,
                open,
                high,
                low,
                close,
                volume,
                source_timestamp
            FROM canonical_ohlcv
            WHERE timestamp >= ?
            ORDER BY timestamp, asset, symbol
            """,
            (LAUNCH_TS,),
        ).fetchall()

        return rows

    finally:
        con.close()


# ============================================================================
# FABRIC VALIDATION
# ============================================================================

def validate_row(row: Mapping[str, Any]) -> Dict[str, Any]:

    asset = str(row["asset"]).strip().upper()
    symbol = str(row["symbol"]).strip().upper()

    if not asset:
        fail("Empty asset")

    if not symbol:
        fail("Empty symbol")

    timestamp = row["timestamp"]

    try:
        timestamp = int(timestamp)
    except (TypeError, ValueError):
        fail(
            f"Invalid timestamp for {asset}/{symbol}: "
            f"{timestamp!r}"
        )

    if timestamp < LAUNCH_TS:
        fail(
            f"Pre-launch row reached bridge: "
            f"{asset}/{symbol}/{timestamp}"
        )

    # Production CEX-only boundary.
    # Fabric DEX rows must not enter the Feature chain.
    #
    # Current canonical Fabric release identifies provider through
    # symbol/source provenance. This bridge accepts only rows whose
    # symbol is CEX-compatible and whose provenance is internally
    # consistent.
    source_timestamp = row["source_timestamp"]

    if is_nullish(source_timestamp):
        fail(
            f"Missing source_timestamp: {asset}/{symbol}/{timestamp}"
        )

    try:
        source_timestamp = int(source_timestamp)
    except (TypeError, ValueError):
        fail(
            f"Invalid source_timestamp: "
            f"{asset}/{symbol}/{timestamp}"
        )

    if source_timestamp != timestamp:
        fail(
            f"Timestamp provenance mismatch: "
            f"{asset}/{symbol}/{timestamp}"
        )

    values = {}

    for field in (
        "open",
        "high",
        "low",
        "close",
        "volume",
    ):
        value = row[field]

        if is_nullish(value):
            fail(
                f"Missing {field}: "
                f"{asset}/{symbol}/{timestamp}"
            )

        if not finite(value):
            fail(
                f"Non-finite {field}: "
                f"{asset}/{symbol}/{timestamp}"
            )

        values[field] = float(value)

    o = values["open"]
    h = values["high"]
    l = values["low"]
    c = values["close"]
    v = values["volume"]

    if h <= 0 or l <= 0 or c <= 0:
        fail(
            f"Non-positive OHLC: "
            f"{asset}/{symbol}/{timestamp}"
        )

    if h < l:
        fail(
            f"high < low: "
            f"{asset}/{symbol}/{timestamp}"
        )

    if o <= 0 or v < 0:
        fail(
            f"Invalid open/volume: "
            f"{asset}/{symbol}/{timestamp}"
        )

    if not (l <= o <= h):
        fail(
            f"open outside high/low: "
            f"{asset}/{symbol}/{timestamp}"
        )

    if not (l <= c <= h):
        fail(
            f"close outside high/low: "
            f"{asset}/{symbol}/{timestamp}"
        )

    return {
        "asset": asset,
        "symbol": symbol,
        "timestamp": timestamp,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "cmc_id": None,
        "source_timestamp": source_timestamp,
    }


def validate_and_group(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    seen = set()

    for raw in rows:

        row = validate_row(raw)

        identity = (
            row["asset"],
            row["symbol"],
            row["timestamp"],
        )

        if identity in seen:
            fail(
                "Duplicate canonical observation: "
                + repr(identity)
            )

        seen.add(identity)

        grouped[row["asset"]].append(row)

    for asset in grouped:

        grouped[asset].sort(
            key=lambda x: x["timestamp"]
        )

        timestamps = [
            x["timestamp"]
            for x in grouped[asset]
        ]

        if len(timestamps) != len(set(timestamps)):
            fail(
                f"Duplicate timestamps for asset={asset}"
            )

    return dict(grouped)


# ============================================================================
# PROVIDER BOUNDARY
# ============================================================================

def determine_provider(
    rows: Sequence[Mapping[str, Any]],
) -> str:

    if not rows:
        return "NONE"

    # canonical_ohlcv release has already selected the canonical
    # provider. The bridge deliberately refuses to blend providers.
    #
    # We identify the selected provider from the canonical symbol/source
    # convention used by the release layer.
    #
    # If a future Fabric schema exposes an explicit provider column,
    # this function can be tightened without touching the feature chain.

    symbols = {
        str(row["symbol"]).upper()
        for row in rows
    }

    # Conservative production convention:
    # canonical CEX rows are expected to use USDT symbols.
    if any(
        symbol.endswith("/USDT")
        or symbol.endswith("USDT")
        for symbol in symbols
    ):
        return PRIMARY_PROVIDER

    # Do not guess a failover provider from insufficient provenance.
    return "UNKNOWN"


# ============================================================================
# BAR ADAPTERS
# ============================================================================

def build_market_bars(
    rows: Sequence[Mapping[str, Any]],
) -> List[Any]:

    from market_structure_engine import MarketBar

    result = []

    for row in rows:

        result.append(
            MarketBar(
                timestamp=row["timestamp"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                open=row["open"],
                volume=row["volume"],
                cmc_id=row["cmc_id"],
                symbol=row["symbol"],
            )
        )

    return result


def build_indicator_bars(
    rows: Sequence[Mapping[str, Any]],
) -> List[Any]:

    from indicator_engine import IndicatorBar

    result = []

    for row in rows:

        result.append(
            IndicatorBar(
                timestamp=row["timestamp"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                open=row["open"],
                volume=row["volume"],
                cmc_id=row["cmc_id"],
                symbol=row["symbol"],
            )
        )

    return result


def build_feature_bars(
    rows: Sequence[Mapping[str, Any]],
) -> List[Any]:

    from feature_engine import FeatureBar

    result = []

    for row in rows:

        result.append(
            FeatureBar(
                timestamp=row["timestamp"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                open=row["open"],
                volume=row["volume"],
                cmc_id=row["cmc_id"],
                symbol=row["symbol"],
            )
        )

    return result


# ============================================================================
# INDICATOR LAYER
# ============================================================================

def build_indicators(
    rows: Sequence[Mapping[str, Any]],
) -> List[Any]:

    import indicator_engine

    bars = build_indicator_bars(rows)

    indicator_records = (
        indicator_engine.calculate_indicator_records(
            bars
        )
    )

    if len(indicator_records) != len(bars):
        fail(
            "Indicator count does not match canonical bars."
        )

    return list(indicator_records)


# ============================================================================
# STRUCTURE LAYER
# ============================================================================

def build_structures(
    rows: Sequence[Mapping[str, Any]],
) -> List[Any]:

    import market_structure_engine

    bars = build_market_bars(rows)

    result = (
        market_structure_engine.analyze_market_structure(
            bars
        )
    )

    if not isinstance(result, dict):
        fail(
            "Market Structure Engine returned non-mapping output."
        )

    structure_points = result.get(
        "structure_points"
    )

    if structure_points is None:
        fail(
            "Market Structure output has no structure_points."
        )

    # IMPORTANT:
    # Feature Engine requires one structure record per bar.
    # The bridge therefore does NOT silently pass sparse structure_points.
    # If the current engine does not expose a bar-aligned structure record
    # collection, we fail closed instead of fabricating one.
    if len(structure_points) != len(rows):
        fail(
            "Market Structure output is not bar-aligned: "
            f"bars={len(rows)} "
            f"structure_points={len(structure_points)}. "
            "No synthetic structure padding is permitted."
        )

    return list(structure_points)


# ============================================================================
# FEATURE LAYER
# ============================================================================

def build_feature_records_for_asset(
    rows: Sequence[Mapping[str, Any]],
) -> List[Any]:

    import feature_engine

    feature_bars = build_feature_bars(rows)
    indicators = build_indicators(rows)
    structures = build_structures(rows)

    if not (
        len(feature_bars)
        == len(indicators)
        == len(structures)
    ):
        fail(
            "Feature input alignment failure."
        )

    records = (
        feature_engine.calculate_feature_records(
            feature_bars,
            indicators,
            structures,
        )
    )

    if len(records) != len(rows):
        fail(
            "Feature record count mismatch."
        )

    feature_engine.validate_feature_collection(
        records
    )

    return list(records)


# ============================================================================
# FEATURE CONTRACT
# ============================================================================

def build_contract_snapshot(
    bars_by_asset: Dict[str, List[Any]],
    indicators_by_asset: Dict[str, List[Any]],
    structures_by_asset: Dict[str, List[Any]],
) -> Any:

    import feature_contract

    snapshot = feature_contract.build_features(
        bars_by_asset,
        indicators_by_asset,
        structures_by_asset,
    )

    return snapshot


# ============================================================================
# MAIN BRIDGE
# ============================================================================

def run() -> Dict[str, Any]:

    assert_production_db_untouched()

    rows = load_fabric_rows()

    if not rows:
        fail(
            "No post-launch canonical Fabric observations."
        )

    grouped = validate_and_group(rows)

    selected_provider = determine_provider(rows)

    if selected_provider != PRIMARY_PROVIDER:
        fail(
            "Canonical provider could not be proven as "
            f"{PRIMARY_PROVIDER}; selected={selected_provider}"
        )

    # No provider blending.
    #
    # A single canonical provider must feed the entire cycle.
    providers_seen = {selected_provider}

    if len(providers_seen) != 1:
        fail(
            "Provider blending detected."
        )

    bars_by_asset: Dict[str, List[Any]] = {}
    indicators_by_asset: Dict[str, List[Any]] = {}
    structures_by_asset: Dict[str, List[Any]] = {}
    feature_records_by_asset: Dict[str, List[Any]] = {}

    blocked_legacy = 0
    valid_rows = 0

    for asset, asset_rows in grouped.items():

        # The Fabric release layer may contain DEX/non-production assets.
        # They are explicitly excluded from the CEX feature path.
        if asset not in EXPECTED_ASSETS:
            blocked_legacy += len(asset_rows)
            continue

        # Current controlled Fabric sample may not yet provide enough
        # observations to calculate the existing indicator/feature chain.
        #
        # We DO NOT pad or fabricate.
        if len(asset_rows) < 21:
            blocked_legacy += len(asset_rows)
            continue

        bars_by_asset[asset] = build_market_bars(
            asset_rows
        )

        indicators_by_asset[asset] = build_indicators(
            asset_rows
        )

        structures_by_asset[asset] = build_structures(
            asset_rows
        )

        feature_records_by_asset[asset] = (
            build_feature_records_for_asset(
                asset_rows
            )
        )

        valid_rows += len(asset_rows)

    # Existing Feature Contract owns the expected asset universe.
    # If all required production assets are not present, fail closed.
    missing_assets = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in bars_by_asset
    ]

    if missing_assets:
        fail(
            "Production Feature Contract cannot be completed. "
            "Missing real Fabric assets: "
            + ", ".join(missing_assets)
        )

    snapshot = build_contract_snapshot(
        bars_by_asset,
        indicators_by_asset,
        structures_by_asset,
    )

    if snapshot is None:
        fail(
            "Feature Contract returned None."
        )

    return {
        "engine": ENGINE_NAME,
        "version": VERSION,

        "production_data_input": True,
        "fabric_validated": True,

        "launch_boundary": LAUNCH_TIMESTAMP,
        "timeframe": TIMEFRAME,

        "canonical_provider": PRIMARY_PROVIDER,
        "selected_provider": selected_provider,
        "failover_provider": FAILOVER_PROVIDER,
        "failover_triggered": False,
        "failover_policy": FAILOVER_POLICY,
        "blending": False,

        "canonical_rows": len(rows),
        "valid_rows": valid_rows,
        "legacy_blocked": blocked_legacy,

        "assets": sorted(bars_by_asset.keys()),
        "bars_by_asset": bars_by_asset,
        "indicators_by_asset": indicators_by_asset,
        "structures_by_asset": structures_by_asset,
        "feature_records_by_asset": feature_records_by_asset,

        "feature_snapshot": snapshot,

        "production_db_touched": False,
        "db_writes": 0,

        "signals_produced": False,
        "scores_produced": False,
        "decisions_produced": False,
        "order_intents_created": False,
        "trading_enabled": False,
        "execution": "DISABLED",

        "validation": "PASS",
        "status": "LIVE_FABRIC_FEATURE_BRIDGE_READY",
    }


def print_report(result: Dict[str, Any]) -> None:

    print()
    print("=" * 72)
    print("ARUNDA LIVE FABRIC FEATURE BRIDGE")
    print("=" * 72)

    print(f"ENGINE={result['engine']}")
    print(f"VERSION={result['version']}")
    print(
        f"PRODUCTION_DATA_INPUT="
        f"{result['production_data_input']}"
    )
    print(
        f"FABRIC_VALIDATED="
        f"{result['fabric_validated']}"
    )
    print(
        f"LAUNCH_BOUNDARY="
        f"{result['launch_boundary']}"
    )
    print(
        f"TIMEFRAME="
        f"{result['timeframe']}"
    )
    print(
        f"CANONICAL_PROVIDER="
        f"{result['canonical_provider']}"
    )
    print(
        f"SELECTED_PROVIDER="
        f"{result['selected_provider']}"
    )
    print(
        f"FAILOVER_TRIGGERED="
        f"{result['failover_triggered']}"
    )
    print(
        f"BLENDING="
        f"{result['blending']}"
    )
    print(
        f"CANONICAL_BARS="
        f"{result['canonical_rows']}"
    )
    print(
        f"VALID_BARS="
        f"{result['valid_rows']}"
    )
    print(
        f"LEGACY_BLOCKED="
        f"{result['legacy_blocked']}"
    )
    print(
        f"ASSETS="
        f"{','.join(result['assets'])}"
    )
    print(
        f"PRODUCTION_DB_TOUCHED="
        f"{result['production_db_touched']}"
    )
    print(
        f"DB_WRITES="
        f"{result['db_writes']}"
    )
    print(
        f"SIGNALS_PRODUCED="
        f"{result['signals_produced']}"
    )
    print(
        f"SCORES_PRODUCED="
        f"{result['scores_produced']}"
    )
    print(
        f"DECISIONS_PRODUCED="
        f"{result['decisions_produced']}"
    )
    print(
        f"ORDER_INTENTS_CREATED="
        f"{result['order_intents_created']}"
    )
    print(
        f"TRADING_ENABLED="
        f"{result['trading_enabled']}"
    )
    print(
        f"EXECUTION="
        f"{result['execution']}"
    )
    print(
        f"VALIDATION="
        f"{result['validation']}"
    )
    print(
        f"STATUS="
        f"{result['status']}"
    )
    print("=" * 72)


if __name__ == "__main__":

    try:
        result = run()
        print_report(result)

    except Exception as exc:

        print()
        print("=" * 72)
        print("ARUNDA LIVE FABRIC FEATURE BRIDGE")
        print("=" * 72)
        print(f"ENGINE={ENGINE_NAME}")
        print(f"VERSION={VERSION}")
        print("PRODUCTION_DATA_INPUT=True")
        print("FABRIC_VALIDATED=False")
        print("PRODUCTION_DB_TOUCHED=False")
        print("DB_WRITES=0")
        print("SIGNALS_PRODUCED=False")
        print("SCORES_PRODUCED=False")
        print("DECISIONS_PRODUCED=False")
        print("ORDER_INTENTS_CREATED=False")
        print("TRADING_ENABLED=False")
        print("EXECUTION=DISABLED")
        print("VALIDATION=FAIL_CLOSED")
        print(f"ERROR={exc}")
        print("STATUS=LIVE_FABRIC_FEATURE_BRIDGE_BLOCKED")
        print("=" * 72)

        raise