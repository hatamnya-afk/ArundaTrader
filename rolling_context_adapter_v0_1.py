from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ============================================================================
# ARUNDA TRADER
# ROLLING CONTEXT ADAPTER v0.1
#
# PURPOSE:
#   PMDF-03 accepted Fabric rows
#       -> explicit Market Identity
#       -> chronological real OHLCV
#       -> MarketBar
#       -> Indicator Engine
#       -> Market Structure Engine
#       -> FeatureBar
#       -> Feature Engine
#       -> Feature Contract
#
# HARD RULES:
#   READ ONLY
#   NO DB WRITE
#   NO SYNTHETIC DATA
#   NO INTERPOLATION
#   NO FILL
#   NO BACKFILL
#   NO PADDING
#   NO BLENDING
#   FAIL CLOSED
#   SOL/USDC != SOL/USDT
# ============================================================================


ENGINE_NAME = "ROLLING_CONTEXT_ADAPTER_v0.1"
TIMEFRAME = "1h"
MIN_CONTEXT = 21
FULL_CONTEXT_TARGET = 150

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

BASE_DIR = Path(__file__).resolve().parent
FABRIC_DB = (
    BASE_DIR
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)


# ============================================================================
# DATA CONTRACTS
# ============================================================================

@dataclass(frozen=True)
class MarketIdentity:
    asset: str
    symbol: str
    source_id: str
    timeframe: str

    @property
    def key(self) -> str:
        return (
            f"{self.asset}|"
            f"{self.symbol}|"
            f"{self.source_id}|"
            f"{self.timeframe}"
        )


@dataclass(frozen=True)
class RollingContext:
    market: MarketIdentity
    bars: Tuple[Any, ...]
    indicators: Tuple[Any, ...]
    structures: Tuple[Any, ...]
    features: Tuple[Any, ...]
    actual_points: int
    context_class: str


# ============================================================================
# IMPORTS
# ============================================================================

from indicator_engine import (
    IndicatorBar,
    calculate_indicator_records,
)

from market_structure_engine import (
    MarketBar,
    analyze_market_structure,
)

from feature_engine import (
    FeatureBar,
    calculate_feature_records,
)

from feature_contract import (
    build_asset_features,
)


# ============================================================================
# READ-ONLY FABRIC
# ============================================================================

def connect_fabric_readonly() -> sqlite3.Connection:
    if not FABRIC_DB.exists():
        raise FileNotFoundError(
            f"Fabric DB not found: {FABRIC_DB}"
        )

    uri = f"file:{FABRIC_DB.as_posix()}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    conn.row_factory = sqlite3.Row
    return conn


def load_fabric_rows(
    conn: sqlite3.Connection,
) -> List[sqlite3.Row]:

    rows = conn.execute(
        """
        SELECT
            id,
            asset,
            symbol,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_id,
            source_type,
            source_timestamp,
            retrieved_at,
            observation_count,
            observation_signatures,
            observation_slots,
            pool,
            raydium_instruction,
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        ORDER BY timestamp ASC, id ASC
        """
    ).fetchall()

    return list(rows)


# ============================================================================
# CANONICAL VALIDATION
# ============================================================================

def _required(value: Any) -> bool:
    return value is not None


def validate_row(
    row: sqlite3.Row,
) -> Tuple[bool, str]:

    required = [
        "asset",
        "symbol",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source_id",
        "source_type",
        "source_timestamp",
        "retrieved_at",
        "observation_count",
        "observation_signatures",
        "observation_slots",
        "canonical_payload",
    ]

    for field in required:
        if not _required(row[field]):
            return False, f"MISSING_{field}"

    if str(row["timeframe"]) != TIMEFRAME:
        return False, "INVALID_TIMEFRAME"

    if str(row["asset"]).upper() not in EXPECTED_ASSETS:
        return False, "UNEXPECTED_ASSET"

    if not isinstance(row["timestamp"], int):
        return False, "INVALID_TIMESTAMP"

    symbol = str(row["symbol"]).strip()

    if not symbol:
        return False, "EMPTY_SYMBOL"

    source_id = str(row["source_id"]).strip()

    if not source_id:
        return False, "EMPTY_SOURCE_ID"

    # Prevent accidental source mixing.
    if (
        "KUCOIN" not in source_id.upper()
        and "RAYDIUM" not in source_id.upper()
    ):
        return False, "UNSUPPORTED_SOURCE"

    # OHLCV must be real finite numeric values.
    for field in (
        "open",
        "high",
        "low",
        "close",
        "volume",
    ):
        try:
            value = float(row[field])
        except (TypeError, ValueError):
            return False, f"INVALID_{field}"

        if not value == value:
            return False, f"NAN_{field}"

    return True, "PASS"


# ============================================================================
# MARKET IDENTITY
# ============================================================================

def make_market_identity(
    row: sqlite3.Row,
) -> MarketIdentity:

    return MarketIdentity(
        asset=str(row["asset"]).upper().strip(),
        symbol=str(row["symbol"]).strip().upper(),
        source_id=str(row["source_id"]).strip(),
        timeframe=str(row["timeframe"]).strip(),
    )


# ============================================================================
# BAR CONVERSION
# ============================================================================

def row_to_market_bar(
    row: sqlite3.Row,
) -> MarketBar:

    return MarketBar(
        timestamp=row["timestamp"],
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        open=float(row["open"])
        if row["open"] is not None
        else None,
        volume=float(row["volume"])
        if row["volume"] is not None
        else None,
        cmc_id=None,
        symbol=str(row["symbol"]),
    )


def market_bar_to_indicator_bar(
    bar: MarketBar,
) -> IndicatorBar:

    return IndicatorBar(
        timestamp=bar.timestamp,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        open=bar.open,
        volume=bar.volume,
        cmc_id=bar.cmc_id,
        symbol=bar.symbol,
    )


def market_bar_to_feature_bar(
    bar: MarketBar,
) -> FeatureBar:

    return FeatureBar(
        timestamp=bar.timestamp,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        open=bar.open,
        volume=bar.volume,
        cmc_id=bar.cmc_id,
        symbol=bar.symbol,
    )


# ============================================================================
# CONTEXT CLASSIFICATION
# ============================================================================

def classify_context(
    actual_points: int,
) -> str:

    if actual_points < MIN_CONTEXT:
        return "NONE"

    if actual_points < FULL_CONTEXT_TARGET:
        return "LIMITED"

    return "FULL"


# ============================================================================
# CAUSAL STRUCTURE ALIGNMENT
# ============================================================================

def align_structure_points(
    bars: Sequence[MarketBar],
    structure_result: Dict[str, Any],
) -> List[Any]:
    """
    Convert sparse StructurePoint output into a causal per-bar sequence.

    IMPORTANT:
      No future structure information is allowed to leak backward.

    For each bar index i:
      use the latest structure point whose index <= i.

    If none exists yet:
      use None.

    No synthetic StructurePoint is created.
    """

    points = structure_result.get(
        "structure_points",
        [],
    )

    indexed = sorted(
        points,
        key=lambda p: int(p.index),
    )

    aligned: List[Any] = []

    pointer = 0
    latest = None

    for i, _bar in enumerate(bars):

        while (
            pointer < len(indexed)
            and int(indexed[pointer].index) <= i
        ):
            latest = indexed[pointer]
            pointer += 1

        aligned.append(latest)

    return aligned


# ============================================================================
# MARKET GROUPING
# ============================================================================

def group_rows_by_market(
    rows: Sequence[sqlite3.Row],
) -> Dict[str, Tuple[MarketIdentity, List[sqlite3.Row]]]:

    grouped: Dict[
        str,
        Tuple[MarketIdentity, List[sqlite3.Row]]
    ] = {}

    for row in rows:

        identity = make_market_identity(row)

        if identity.key not in grouped:
            grouped[identity.key] = (
                identity,
                [],
            )

        grouped[identity.key][1].append(row)

    return grouped


# ============================================================================
# PER-MARKET PIPELINE
# ============================================================================

def build_market_context(
    identity: MarketIdentity,
    rows: Sequence[sqlite3.Row],
) -> RollingContext:

    ordered_rows = sorted(
        rows,
        key=lambda r: (
            int(r["timestamp"]),
            int(r["id"]),
        ),
    )

    # One real canonical row per timestamp.
    seen_timestamps = set()

    unique_rows: List[sqlite3.Row] = []

    for row in ordered_rows:

        ts = int(row["timestamp"])

        if ts in seen_timestamps:
            raise RuntimeError(
                "FAIL_CLOSED: duplicate timestamp inside "
                f"market={identity.key}, timestamp={ts}"
            )

        seen_timestamps.add(ts)
        unique_rows.append(row)

    bars = [
        row_to_market_bar(row)
        for row in unique_rows
    ]

    actual_points = len(bars)

    context_class = classify_context(
        actual_points
    )

    # ------------------------------------------------------------------------
    # Insufficient real history:
    # fail closed and DO NOT manufacture context.
    # ------------------------------------------------------------------------

    if actual_points < MIN_CONTEXT:

        return RollingContext(
            market=identity,
            bars=tuple(bars),
            indicators=tuple(),
            structures=tuple(),
            features=tuple(),
            actual_points=actual_points,
            context_class=context_class,
        )

    # ------------------------------------------------------------------------
    # Indicator layer
    # ------------------------------------------------------------------------

    indicator_bars = [
        market_bar_to_indicator_bar(bar)
        for bar in bars
    ]

    indicator_records = calculate_indicator_records(
        indicator_bars
    )

    if len(indicator_records) != actual_points:
        raise RuntimeError(
            "FAIL_CLOSED: indicator cardinality mismatch"
        )

    # ------------------------------------------------------------------------
    # Structure layer
    # ------------------------------------------------------------------------

    structure_result = analyze_market_structure(
        bars
    )

    aligned_structures = align_structure_points(
        bars,
        structure_result,
    )

    if len(aligned_structures) != actual_points:
        raise RuntimeError(
            "FAIL_CLOSED: structure cardinality mismatch"
        )

    # ------------------------------------------------------------------------
    # Feature layer
    # ------------------------------------------------------------------------

    feature_bars = [
        market_bar_to_feature_bar(bar)
        for bar in bars
    ]

    feature_records = calculate_feature_records(
        feature_bars,
        indicator_records,
        aligned_structures,
    )

    if len(feature_records) != actual_points:
        raise RuntimeError(
            "FAIL_CLOSED: feature cardinality mismatch"
        )

    # ------------------------------------------------------------------------
    # Feature Contract
    #
    # Feature Contract is ASSET-scoped.
    # We invoke it per explicit market context so that two markets of the
    # same asset are never merged.
    # ------------------------------------------------------------------------

    asset_features = build_asset_features(
        identity.asset,
        feature_bars,
        indicator_records,
        aligned_structures,
    )

    if asset_features.get("asset") != identity.asset:
        raise RuntimeError(
            "FAIL_CLOSED: feature contract asset mismatch"
        )

    return RollingContext(
        market=identity,
        bars=tuple(bars),
        indicators=tuple(indicator_records),
        structures=tuple(aligned_structures),
        features=tuple(feature_records),
        actual_points=actual_points,
        context_class=context_class,
    )


# ============================================================================
# RUNTIME
# ============================================================================

def runtime_verify() -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "engine": ENGINE_NAME,
        "fabric_db": str(FABRIC_DB),
        "db_writes": 0,
        "production_db_touched": False,
        "execution": "DISABLED",
        "order_intents_created": 0,
        "fail_closed": True,
        "status": "UNKNOWN",
        "markets": [],
    }

    conn = connect_fabric_readonly()

    try:

        rows = load_fabric_rows(conn)

    finally:

        conn.close()

    accepted: List[sqlite3.Row] = []
    rejected: List[Dict[str, Any]] = []

    for row in rows:

        valid, reason = validate_row(row)

        if valid:
            accepted.append(row)
        else:
            rejected.append(
                {
                    "id": row["id"],
                    "reason": reason,
                }
            )

    grouped = group_rows_by_market(
        accepted
    )

    contexts: List[RollingContext] = []

    for identity, market_rows in grouped.values():

        context = build_market_context(
            identity,
            market_rows,
        )

        contexts.append(context)

        result["markets"].append(
            {
                "market_key": identity.key,
                "asset": identity.asset,
                "symbol": identity.symbol,
                "source_id": identity.source_id,
                "timeframe": identity.timeframe,
                "real_points": context.actual_points,
                "context": context.context_class,
                "indicators": len(context.indicators),
                "structures": len(context.structures),
                "features": len(context.features),
                "feature_contract": (
                    "READY"
                    if context.actual_points >= MIN_CONTEXT
                    else "NOT_READY"
                ),
            }
        )

    # ------------------------------------------------------------------------
    # Explicit identity safety checks
    # ------------------------------------------------------------------------

    sol_markets = {
        c.market.symbol
        for c in contexts
        if c.market.asset == "SOL"
    }

    if (
        "SOL/USDC" in sol_markets
        and "SOL/USDT" in sol_markets
        and len(
            {
                c.market.key
                for c in contexts
                if c.market.asset == "SOL"
            }
        ) < 2
    ):
        raise RuntimeError(
            "FAIL_CLOSED: SOL/USDC and SOL/USDT collapsed"
        )

    result["fabric_rows"] = len(rows)
    result["accepted_rows"] = len(accepted)
    result["rejected_rows"] = len(rejected)
    result["market_count"] = len(contexts)

    result["ready_markets"] = sum(
        1
        for c in contexts
        if c.actual_points >= MIN_CONTEXT
    )

    result["not_ready_markets"] = sum(
        1
        for c in contexts
        if c.actual_points < MIN_CONTEXT
    )

    result["status"] = "READY_NO_EXECUTION"

    return result


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    result = runtime_verify()

    print()
    print("=" * 78)
    print("ARUNDA TRADER — ROLLING CONTEXT ADAPTER v0.1")
    print("=" * 78)

    print(f"ENGINE={result['engine']}")
    print(f"FABRIC_DB={result['fabric_db']}")
    print(f"FABRIC_ROWS={result['fabric_rows']}")
    print(f"ACCEPTED_ROWS={result['accepted_rows']}")
    print(f"REJECTED_ROWS={result['rejected_rows']}")
    print(f"MARKETS={result['market_count']}")
    print(f"READY_MARKETS={result['ready_markets']}")
    print(f"NOT_READY_MARKETS={result['not_ready_markets']}")
    print(f"DB_WRITES={result['db_writes']}")
    print(
        f"PRODUCTION_DB_TOUCHED="
        f"{result['production_db_touched']}"
    )
    print(f"EXECUTION={result['execution']}")
    print(
        f"ORDER_INTENTS_CREATED="
        f"{result['order_intents_created']}"
    )
    print(f"FAIL_CLOSED={result['fail_closed']}")
    print(f"STATUS={result['status']}")

    print()
    print("--- MARKET CONTEXT ---")

    for market in result["markets"]:

        print(
            f"{market['market_key']} | "
            f"points={market['real_points']} | "
            f"context={market['context']} | "
            f"indicators={market['indicators']} | "
            f"structures={market['structures']} | "
            f"features={market['features']} | "
            f"contract={market['feature_contract']}"
        )

    print()
    print("=" * 78)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()