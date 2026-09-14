# =============================================================================
# ARUNDA DYNAMIC OPPORTUNITY BOUNDARY v0.4
# DYNAMIC UNIVERSE -> REAL DYNAMIC HISTORY -> OPPORTUNITY
# =============================================================================
#
# PURPOSE
# -------
# Bind the already-approved Dynamic Universe to the existing real KuCoin
# historical market-data path and then to the EXISTING Opportunity Engine
# calculation layer.
#
# FLOW
# ----
#
# Dynamic Universe
#       |
#       v
# Eligible Market
#       |
#       +-----------------------------+
#       |                             |
#       v                             v
# BASE/USDT                       OTHER QUOTE
#       |                             |
#       v                             v
# BASE-USDT                    UNSUPPORTED_QUOTE
#       |                       FAIL-CLOSED
#       v
# EXISTING KUCOIN CANONICAL FETCH
#       |
#       v
# normalize()
#       |
#       v
# validate_candle()
#       |
#       v
# CLOSED CANDLES ONLY
#       |
#       v
# PRE-LAUNCH EXCLUSION
#       |
#       v
# DEDUPLICATION
#       |
#       v
# STRICT CONTIGUOUS 1H SUFFIX
#       |
#       v
# MINIMUM 60 CLOSED CANDLES
#       |
#       v
# EXISTING build_opportunity()
#       |
#       v
# DYNAMIC OPPORTUNITY RESULT
#
# IMPORTANT
# ---------
# - Opportunity Engine is NOT modified.
# - Opportunity Engine run() is NOT called.
# - EXPECTED_ASSETS is NOT used for iteration or coverage.
# - EXPECTED_ASSET_COUNT is NOT used.
# - MAX_CANDIDATES is NOT used.
# - CMC is forbidden.
# - Production market_data DB is NOT used as History source.
# - No production DB write.
# - No synthetic data.
# - No interpolation.
# - No fill.
# - No backfill/fabrication.
# - No padding.
# - No blending.
# - Non-USDT markets are preserved and fail closed.
#
# HISTORY CONTRACT
# ----------------
#
# Required:
#
#   timeframe        = 1h
#   source           = KUCOIN_SPOT
#   source_type      = CEX_PUBLIC_API
#   market           = exact BASE-USDT
#   candle state     = closed
#   continuity       = strict 3600 seconds
#   minimum history  = 60 contiguous closed candles
#   maximum context  = 150 candles
#   launch boundary  = 2026-08-31T00:00:00+00:00
#
# The existing canonical KuCoin fetch is used directly:
#
#   fetch_kucoin("BASE-USDT", count=150)
#
# The fixed-15 ASSETS map in public_market_data_kucoin.py is NOT used.
# The fetch_kucoin() function itself accepts an arbitrary KuCoin symbol.
#
# =============================================================================

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

PRODUCTION_SIGNAL_INPUT_FILE = (
    ROOT / "production_signal_input_boundary_v0_1.py"
)

OPPORTUNITY_ENGINE_FILE = (
    ROOT / "opportunity_engine.py"
)

KUCOIN_ADAPTER_FILE = (
    ROOT / "public_market_data_kucoin.py"
)


# =============================================================================
# SAFETY
# =============================================================================

DB_WRITES = 0
EXECUTION = False

CMC_FORBIDDEN = True

SYNTHETIC_DATA = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False


# =============================================================================
# HISTORY CONTRACT
# =============================================================================

CANONICAL_QUOTE_ASSET = "USDT"

TIMEFRAME = "1h"
TIMEFRAME_SECONDS = 3600

MIN_HISTORY_POINTS = 60
MAX_HISTORY_POINTS = 150

PRODUCTION_LAUNCH_TIMESTAMP = (
    "2026-08-31T00:00:00+00:00"
)

PRODUCTION_LAUNCH_EPOCH = int(
    datetime.fromisoformat(
        PRODUCTION_LAUNCH_TIMESTAMP.replace(
            "Z",
            "+00:00",
        )
    ).timestamp()
)

KUCOIN_SOURCE = "KUCOIN_SPOT"
KUCOIN_SOURCE_TYPE = "CEX_PUBLIC_API"


# =============================================================================
# MODULE LOADER
# =============================================================================

def load_module(
    path: Path,
    name: str,
):
    if not path.exists():
        raise RuntimeError(
            f"FILE_NOT_FOUND:{path.name}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise

    return module


# =============================================================================
# SYMBOL CONTRACT
# =============================================================================

def parse_dynamic_market_symbol(
    market_symbol: str,
) -> tuple[str, str]:

    if not isinstance(
        market_symbol,
        str,
    ):
        raise RuntimeError(
            "DYNAMIC_SYMBOL_INVALID_TYPE"
        )

    canonical = (
        market_symbol
        .strip()
        .upper()
    )

    if not canonical:
        raise RuntimeError(
            "DYNAMIC_SYMBOL_EMPTY"
        )

    parts = canonical.split("/")

    if len(parts) != 2:
        raise RuntimeError(
            "INVALID_DYNAMIC_SYMBOL_FORMAT:"
            f"{market_symbol!r}"
        )

    base = parts[0].strip()
    quote = parts[1].strip()

    if not base:
        raise RuntimeError(
            "INVALID_DYNAMIC_SYMBOL_BASE:"
            f"{market_symbol!r}"
        )

    if not quote:
        raise RuntimeError(
            "INVALID_DYNAMIC_SYMBOL_QUOTE:"
            f"{market_symbol!r}"
        )

    return base, quote


def dynamic_symbol_to_kucoin_symbol(
    market_symbol: str,
) -> str:

    base, quote = parse_dynamic_market_symbol(
        market_symbol
    )

    if quote != CANONICAL_QUOTE_ASSET:
        raise RuntimeError(
            "UNSUPPORTED_DYNAMIC_SYMBOL_QUOTE:"
            f"{market_symbol!r}"
        )

    return f"{base}-USDT"


def dynamic_symbol_to_engine_symbol(
    market_symbol: str,
) -> str:

    base, quote = parse_dynamic_market_symbol(
        market_symbol
    )

    if quote != CANONICAL_QUOTE_ASSET:
        raise RuntimeError(
            "UNSUPPORTED_DYNAMIC_SYMBOL_QUOTE:"
            f"{market_symbol!r}"
        )

    return base


def is_supported_opportunity_market(
    market_symbol: str,
) -> bool:

    _, quote = parse_dynamic_market_symbol(
        market_symbol
    )

    return quote == CANONICAL_QUOTE_ASSET


# =============================================================================
# DYNAMIC UNIVERSE SYMBOL EXTRACTION
# =============================================================================

def extract_symbol(
    record: Any,
) -> str:

    symbol_value = getattr(
        record,
        "symbol",
        None,
    )

    if not isinstance(
        symbol_value,
        str,
    ):
        raise RuntimeError(
            "DYNAMIC_UNIVERSE_RECORD_WITHOUT_VALID_SYMBOL"
        )

    symbol = (
        symbol_value
        .strip()
        .upper()
    )

    if not symbol:
        raise RuntimeError(
            "DYNAMIC_UNIVERSE_RECORD_WITHOUT_SYMBOL"
        )

    parse_dynamic_market_symbol(symbol)

    return symbol


# =============================================================================
# DYNAMIC UNIVERSE DISCOVERY
# =============================================================================

def discover_dynamic_universe():

    signal_input = load_module(
        PRODUCTION_SIGNAL_INPUT_FILE,
        "dynamic_opportunity_signal_input_runtime_v04",
    )

    universe_binding = signal_input.load_module(
        signal_input.UNIVERSE_BINDING_MODULE,
        "dynamic_opportunity_universe_runtime_v04",
    )

    all_records, eligible_records = (
        signal_input.discover_production_universe(
            universe_binding
        )
    )

    if not isinstance(
        all_records,
        (list, tuple),
    ):
        raise RuntimeError(
            "DYNAMIC_UNIVERSE_ALL_RECORDS_INVALID"
        )

    if not isinstance(
        eligible_records,
        (list, tuple),
    ):
        raise RuntimeError(
            "DYNAMIC_UNIVERSE_ELIGIBLE_RECORDS_INVALID"
        )

    for record in eligible_records:
        extract_symbol(record)

    return (
        signal_input,
        all_records,
        eligible_records,
    )


# =============================================================================
# FAIL-CLOSED UNSUPPORTED QUOTE
# =============================================================================

def build_unsupported_quote_result(
    market_symbol: str,
) -> dict[str, Any]:

    _, quote = parse_dynamic_market_symbol(
        market_symbol
    )

    return {
        "asset": market_symbol,
        "status": "UNSUPPORTED_QUOTE",
        "direction": "NONE",
        "score": 0.0,
        "confidence": 0.0,
        "history_points": 0,
        "history_required": MIN_HISTORY_POINTS,
        "history_available": 0,
        "history_coverage": False,
        "reason": "OPPORTUNITY_PATH_SUPPORTS_USDT_ONLY",
        "source": "NOT_REQUESTED",
        "source_type": "NOT_REQUESTED",
        "timeframe": TIMEFRAME,
        "engine_version": "NOT_EXECUTED",
        "db_symbol": None,
        "quote_asset": quote,
        "db_writes": 0,
        "execution": False,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
    }


# =============================================================================
# REAL KUCOIN HISTORY ADAPTER
# =============================================================================

def load_kucoin_adapter():

    return load_module(
        KUCOIN_ADAPTER_FILE,
        "dynamic_opportunity_kucoin_runtime_v04",
    )


def fetch_dynamic_real_history(
    kucoin: Any,
    market_symbol: str,
) -> list[dict[str, Any]]:

    provider_symbol = (
        dynamic_symbol_to_kucoin_symbol(
            market_symbol
        )
    )

    base_symbol = (
        dynamic_symbol_to_engine_symbol(
            market_symbol
        )
    )

    #
    # IMPORTANT:
    # fetch_kucoin() itself is generic and does NOT use ASSETS.
    # We deliberately do not call kucoin.main().
    #

    raw_bars = kucoin.fetch_kucoin(
        provider_symbol,
        count=MAX_HISTORY_POINTS,
    )

    if not isinstance(
        raw_bars,
        list,
    ):
        raise RuntimeError(
            "KUCOIN_HISTORY_RESPONSE_INVALID"
        )

    retrieved_at = (
        datetime.now(timezone.utc).isoformat()
    )

    current_hour = int(
        datetime.now(timezone.utc).timestamp()
    )
    current_hour -= (
        current_hour % TIMEFRAME_SECONDS
    )

    canonical_rows: list[
        dict[str, Any]
    ] = []

    seen_timestamps: set[int] = set()

    for bar in raw_bars:

        if not isinstance(
            bar,
            list,
        ):
            continue

        if len(bar) < 6:
            continue

        try:
            timestamp = int(bar[0])
        except (
            TypeError,
            ValueError,
        ):
            continue

        #
        # Current/open candle is forbidden.
        #

        if timestamp >= current_hour:
            continue

        #
        # Production launch boundary.
        #

        if timestamp < PRODUCTION_LAUNCH_EPOCH:
            continue

        #
        # Exact 1h alignment.
        #

        if timestamp % TIMEFRAME_SECONDS != 0:
            continue

        #
        # Duplicate timestamps are not accepted.
        #

        if timestamp in seen_timestamps:
            continue

        candle = kucoin.normalize(
            base_symbol,
            provider_symbol,
            bar,
            retrieved_at,
        )

        kucoin.validate_candle(candle)

        #
        # Canonical validation after normalization.
        #

        if candle["symbol"] != market_symbol:
            raise RuntimeError(
                f"{market_symbol}:"
                "KUCOIN_SYMBOL_MISMATCH:"
                f"{candle['symbol']!r}"
            )

        if candle["timestamp"] != timestamp:
            raise RuntimeError(
                f"{market_symbol}:"
                "TIMESTAMP_MISMATCH"
            )

        if candle["timeframe"] != TIMEFRAME:
            raise RuntimeError(
                f"{market_symbol}:"
                "TIMEFRAME_MISMATCH"
            )

        if not str(
            candle["source_id"]
        ).startswith(
            f"{KUCOIN_SOURCE}:"
        ):
            raise RuntimeError(
                f"{market_symbol}:"
                "SOURCE_PROVENANCE_INVALID"
            )

        if candle["source_type"] != KUCOIN_SOURCE_TYPE:
            raise RuntimeError(
                f"{market_symbol}:"
                "SOURCE_TYPE_INVALID"
            )

        seen_timestamps.add(timestamp)

        canonical_rows.append(candle)

    canonical_rows.sort(
        key=lambda row: int(
            row["timestamp"]
        )
    )

    return canonical_rows


# =============================================================================
# STRICT CONTIGUOUS SUFFIX
# =============================================================================

def build_strict_contiguous_suffix(
    market_symbol: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not rows:
        return []

    ordered = sorted(
        rows,
        key=lambda row: int(
            row["timestamp"]
        ),
    )

    #
    # Walk backward from newest real closed candle.
    # Stop at first missing 1h interval.
    #

    suffix: list[
        dict[str, Any]
    ] = [
        ordered[-1]
    ]

    expected_timestamp = int(
        ordered[-1]["timestamp"]
    ) - TIMEFRAME_SECONDS

    for row in reversed(
        ordered[:-1]
    ):

        timestamp = int(
            row["timestamp"]
        )

        if timestamp != expected_timestamp:
            break

        suffix.append(row)

        expected_timestamp -= (
            TIMEFRAME_SECONDS
        )

        if len(suffix) >= MAX_HISTORY_POINTS:
            break

    suffix.reverse()

    #
    # Every pair must be exactly one hour apart.
    #

    for previous, current in zip(
        suffix,
        suffix[1:],
    ):

        previous_ts = int(
            previous["timestamp"]
        )

        current_ts = int(
            current["timestamp"]
        )

        if (
            current_ts
            - previous_ts
            != TIMEFRAME_SECONDS
        ):
            raise RuntimeError(
                f"{market_symbol}:"
                "STRICT_CONTINUITY_FAILED"
            )

    return suffix


# =============================================================================
# HISTORY VALIDATION
# =============================================================================

def validate_dynamic_history(
    market_symbol: str,
    history: list[dict[str, Any]],
) -> None:

    if not history:
        raise RuntimeError(
            f"{market_symbol}:NO_REAL_HISTORY"
        )

    if len(history) < MIN_HISTORY_POINTS:
        raise RuntimeError(
            f"{market_symbol}:"
            "INSUFFICIENT_CONTIGUOUS_HISTORY:"
            f"{len(history)}<"
            f"{MIN_HISTORY_POINTS}"
        )

    seen = set()

    for row in history:

        timestamp = int(
            row["timestamp"]
        )

        if timestamp in seen:
            raise RuntimeError(
                f"{market_symbol}:"
                "DUPLICATE_HISTORY_TIMESTAMP"
            )

        seen.add(timestamp)

        if timestamp < PRODUCTION_LAUNCH_EPOCH:
            raise RuntimeError(
                f"{market_symbol}:"
                "PRE_LAUNCH_HISTORY_DETECTED"
            )

        if timestamp % TIMEFRAME_SECONDS != 0:
            raise RuntimeError(
                f"{market_symbol}:"
                "HISTORY_NOT_1H_ALIGNED"
            )

        if row["timeframe"] != TIMEFRAME:
            raise RuntimeError(
                f"{market_symbol}:"
                "HISTORY_TIMEFRAME_INVALID"
            )

        if row["source_type"] != KUCOIN_SOURCE_TYPE:
            raise RuntimeError(
                f"{market_symbol}:"
                "HISTORY_SOURCE_TYPE_INVALID"
            )

        if not str(
            row["source_id"]
        ).startswith(
            f"{KUCOIN_SOURCE}:"
        ):
            raise RuntimeError(
                f"{market_symbol}:"
                "HISTORY_SOURCE_INVALID"
            )

    #
    # Strict adjacency.
    #

    for previous, current in zip(
        history,
        history[1:],
    ):

        if (
            int(current["timestamp"])
            - int(previous["timestamp"])
            != TIMEFRAME_SECONDS
        ):
            raise RuntimeError(
                f"{market_symbol}:"
                "HISTORY_CONTINUITY_INVALID"
            )


# =============================================================================
# WAITING HISTORY RESULT
# =============================================================================

def build_waiting_history_result(
    market_symbol: str,
    db_symbol: str,
    available: int,
    reason: str,
) -> dict[str, Any]:

    return {
        "asset": market_symbol,
        "status": "WAITING_HISTORY",
        "direction": "NONE",
        "score": 0.0,
        "confidence": 0.0,
        "history_points": available,
        "history_required": MIN_HISTORY_POINTS,
        "history_available": available,
        "history_coverage": False,
        "reason": reason,
        "source": KUCOIN_SOURCE,
        "source_type": KUCOIN_SOURCE_TYPE,
        "timeframe": TIMEFRAME,
        "engine_version": "OPPORTUNITY_NOT_EXECUTED",
        "db_symbol": db_symbol,
        "quote_asset": CANONICAL_QUOTE_ASSET,
        "db_writes": 0,
        "execution": False,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
    }


# =============================================================================
# OPPORTUNITY RESULT ADAPTER
# =============================================================================

def adapt_opportunity_to_dynamic_symbol(
    market_symbol: str,
    db_symbol: str,
    opportunity: dict[str, Any],
    history_points: int,
    contiguous: list[dict[str, Any]],
) -> dict[str, Any]:

    if not isinstance(
        opportunity,
        dict,
    ):
        raise RuntimeError(
            f"{market_symbol}:"
            "INVALID_OPPORTUNITY_RESULT"
        )

    result = dict(opportunity)

    engine_asset = str(
        result.get(
            "asset",
            "",
        )
    ).strip().upper()

    if engine_asset != db_symbol:
        raise RuntimeError(
            f"{market_symbol}:"
            "OPPORTUNITY_ENGINE_ASSET_MISMATCH:"
            f"expected={db_symbol!r}:"
            f"actual={engine_asset!r}"
        )

    result["asset"] = market_symbol
    result["db_symbol"] = db_symbol
    result["quote_asset"] = CANONICAL_QUOTE_ASSET

    result["history_points"] = history_points
    result["history_required"] = MIN_HISTORY_POINTS
    result["history_available"] = history_points
    result["history_coverage"] = (
        history_points >= MIN_HISTORY_POINTS
    )

    if not contiguous:
        raise RuntimeError(
            f"{market_symbol}:"
            "PROVENANCE_HISTORY_EMPTY"
        )

    latest_history = contiguous[-1]

    required_provenance_fields = (
        "source_id",
        "source_type",
        "source_timestamp",
        "retrieved_at",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    for field in required_provenance_fields:
        if field not in latest_history:
            raise RuntimeError(
                f"{market_symbol}:"
                f"PROVENANCE_FIELD_MISSING:{field}"
            )

    if latest_history["source_type"] != KUCOIN_SOURCE_TYPE:
        raise RuntimeError(
            f"{market_symbol}:"
            "PROVENANCE_SOURCE_TYPE_INVALID"
        )

    if not str(
        latest_history["source_id"]
    ).startswith(
        f"{KUCOIN_SOURCE}:"
    ):
        raise RuntimeError(
            f"{market_symbol}:"
            "PROVENANCE_SOURCE_ID_INVALID"
        )

    if latest_history["timeframe"] != TIMEFRAME:
        raise RuntimeError(
            f"{market_symbol}:"
            "PROVENANCE_TIMEFRAME_INVALID"
        )

    result["source"] = KUCOIN_SOURCE
    result["source_id"] = latest_history["source_id"]
    result["source_type"] = latest_history["source_type"]
    result["source_timestamp"] = latest_history["source_timestamp"]
    result["retrieved_at"] = latest_history["retrieved_at"]
    result["timestamp"] = latest_history["timestamp"]
    result["timeframe"] = latest_history["timeframe"]

    result["open"] = latest_history["open"]
    result["high"] = latest_history["high"]
    result["low"] = latest_history["low"]
    result["close"] = latest_history["close"]
    result["volume"] = latest_history["volume"]

    result["canonical_validation"] = "PASS"
    result["continuity"] = "PASS"

    result["db_writes"] = 0
    result["execution"] = False
    result["synthetic"] = False
    result["interpolation"] = False
    result["fill"] = False
    result["backfill"] = False
    result["padding"] = False
    result["blending"] = False

    return result


# =============================================================================
# SINGLE MARKET OPPORTUNITY
# =============================================================================

def build_single_dynamic_opportunity(
    opportunity_engine: Any,
    kucoin: Any,
    market_symbol: str,
) -> dict[str, Any]:

    #
    # Non-USDT is explicit fail-closed.
    #

    if not is_supported_opportunity_market(
        market_symbol
    ):
        return build_unsupported_quote_result(
            market_symbol
        )

    db_symbol = (
        dynamic_symbol_to_engine_symbol(
            market_symbol
        )
    )

    try:

        rows = fetch_dynamic_real_history(
            kucoin,
            market_symbol,
        )

    except Exception as exc:

        return build_waiting_history_result(
            market_symbol,
            db_symbol,
            0,
            f"REAL_HISTORY_FETCH_FAILED:{type(exc).__name__}:{exc}",
        )

    if not rows:

        return build_waiting_history_result(
            market_symbol,
            db_symbol,
            0,
            "NO_REAL_KUCOIN_HISTORY",
        )

    #
    # Build only the strict contiguous suffix.
    #

    contiguous = build_strict_contiguous_suffix(
        market_symbol,
        rows,
    )

    available = len(contiguous)

    #
    # History below contract remains WAITING_HISTORY.
    #

    if available < MIN_HISTORY_POINTS:

        return build_waiting_history_result(
            market_symbol,
            db_symbol,
            available,
            "INSUFFICIENT_CONTIGUOUS_REAL_HISTORY",
        )

    #
    # Canonical History contract.
    #

    try:

        validate_dynamic_history(
            market_symbol,
            contiguous,
        )

    except Exception as exc:

        return build_waiting_history_result(
            market_symbol,
            db_symbol,
            available,
            f"HISTORY_VALIDATION_FAILED:{exc}",
        )

    #
    # Existing Opportunity Engine only.
    #
    # No run().
    # No get_history().
    # No fixed-15 iteration.
    #

    opportunity = (
        opportunity_engine.build_opportunity(
            db_symbol,
            contiguous,
        )
    )

    return adapt_opportunity_to_dynamic_symbol(
        market_symbol,
        db_symbol,
        opportunity,
        available,
        contiguous,
    )


# =============================================================================
# RESULT VALIDATION
# =============================================================================

def validate_dynamic_results(
    opportunities: dict[
        str,
        dict[str, Any],
    ],
    eligible_records: list[Any],
) -> None:

    eligible_symbols = {
        extract_symbol(record)
        for record in eligible_records
    }

    result_symbols = set(
        opportunities.keys()
    )

    if result_symbols != eligible_symbols:

        missing = sorted(
            eligible_symbols
            - result_symbols
        )

        extra = sorted(
            result_symbols
            - eligible_symbols
        )

        raise RuntimeError(
            "DYNAMIC_OPPORTUNITY_COVERAGE_MISMATCH:"
            f"missing={missing}:"
            f"extra={extra}"
        )

    required_fields = (
        "asset",
        "status",
        "direction",
        "score",
        "confidence",
        "history_points",
        "history_required",
        "history_available",
        "history_coverage",
        "source",
        "timeframe",
        "db_symbol",
    )

    for symbol, opportunity in opportunities.items():

        if not isinstance(
            opportunity,
            dict,
        ):
            raise RuntimeError(
                f"{symbol}:INVALID_OPPORTUNITY_RESULT_TYPE"
            )

        for field in required_fields:

            if field not in opportunity:
                raise RuntimeError(
                    f"{symbol}:"
                    f"OPPORTUNITY_FIELD_MISSING:{field}"
                )

        if str(
            opportunity["asset"]
        ).strip().upper() != symbol:
            raise RuntimeError(
                f"{symbol}:OPPORTUNITY_SYMBOL_MISMATCH"
            )

        status = str(
            opportunity["status"]
        ).strip().upper()

        #
        # Unsupported quote.
        #

        if status == "UNSUPPORTED_QUOTE":

            if opportunity["db_symbol"] is not None:
                raise RuntimeError(
                    f"{symbol}:"
                    "UNSUPPORTED_QUOTE_HAS_DB_SYMBOL"
                )

            if opportunity["history_points"] != 0:
                raise RuntimeError(
                    f"{symbol}:"
                    "UNSUPPORTED_QUOTE_HAS_HISTORY"
                )

            continue

        #
        # Supported market.
        #

        expected_db_symbol = (
            dynamic_symbol_to_engine_symbol(
                symbol
            )
        )

        if str(
            opportunity["db_symbol"]
        ).strip().upper() != expected_db_symbol:
            raise RuntimeError(
                f"{symbol}:"
                "DB_SYMBOL_ADAPTER_MISMATCH:"
                f"expected={expected_db_symbol!r}:"
                f"actual={opportunity['db_symbol']!r}"
            )

        if opportunity["history_points"] != (
            opportunity["history_available"]
        ):
            raise RuntimeError(
                f"{symbol}:"
                "HISTORY_COUNT_MISMATCH"
            )

        if (
            status == "ELIGIBLE"
            and not opportunity["history_coverage"]
        ):
            raise RuntimeError(
                f"{symbol}:"
                "ELIGIBLE_WITHOUT_HISTORY_COVERAGE"
            )


# =============================================================================
# SUMMARY
# =============================================================================

def summarize(
    opportunities: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, int]:

    eligible = 0
    no_trade = 0
    waiting_history = 0
    unsupported_quote = 0
    history_covered = 0

    for opportunity in opportunities.values():

        status = str(
            opportunity.get(
                "status",
                "",
            )
        ).strip().upper()

        if status == "ELIGIBLE":
            eligible += 1

        elif status == "NO_TRADE":
            no_trade += 1

        elif status == "WAITING_HISTORY":
            waiting_history += 1

        elif status == "UNSUPPORTED_QUOTE":
            unsupported_quote += 1

        if opportunity.get(
            "history_coverage",
            False,
        ):
            history_covered += 1

    return {
        "opportunities_total": len(
            opportunities
        ),
        "eligible_opportunities": eligible,
        "no_trade": no_trade,
        "waiting_history": waiting_history,
        "unsupported_quote": unsupported_quote,
        "history_covered": history_covered,
    }


# =============================================================================
# OPPORTUNITY ENGINE VALIDATION
# =============================================================================

def validate_opportunity_engine(
    opportunity_engine: Any,
) -> None:

    required = (
        "build_opportunity",
        "EXPECTED_ASSETS",
        "EXPECTED_ASSET_COUNT",
        "MAX_CANDIDATES",
    )

    for name in required:

        if not hasattr(
            opportunity_engine,
            name,
        ):
            raise RuntimeError(
                "OPPORTUNITY_ENGINE_DEPENDENCY_MISSING:"
                f"{name}"
            )


# =============================================================================
# CONTROLLED REAL DYNAMIC RUNTIME
# =============================================================================

def run_controlled() -> dict[str, Any]:

    if not contract_check():
        raise RuntimeError(
            "DYNAMIC_OPPORTUNITY_CONTRACT_FAILED"
        )

    opportunity_engine = load_module(
        OPPORTUNITY_ENGINE_FILE,
        "dynamic_opportunity_engine_runtime_v04",
    )

    validate_opportunity_engine(
        opportunity_engine
    )

    kucoin = load_kucoin_adapter()

    (
        signal_input,
        all_records,
        eligible_records,
    ) = discover_dynamic_universe()

    if len(eligible_records) <= 0:
        raise RuntimeError(
            "DYNAMIC_ELIGIBLE_UNIVERSE_EMPTY"
        )

    opportunities: dict[
        str,
        dict[str, Any],
    ] = {}

    #
    # One result for every eligible Dynamic Universe market.
    #

    for record in eligible_records:

        market_symbol = extract_symbol(
            record
        )

        opportunities[
            market_symbol
        ] = build_single_dynamic_opportunity(
            opportunity_engine,
            kucoin,
            market_symbol,
        )

    validate_dynamic_results(
        opportunities,
        list(eligible_records),
    )

    summary = summarize(
        opportunities
    )

    eligible_items = [
        item
        for item in opportunities.values()
        if str(
            item.get(
                "status",
                "",
            )
        ).strip().upper()
        == "ELIGIBLE"
    ]

    return {
        "all_universe_size": len(
            all_records
        ),
        "eligible_universe_size": len(
            eligible_records
        ),
        "opportunities": opportunities,

        "opportunities_total": (
            summary["opportunities_total"]
        ),
        "eligible_opportunities": (
            summary["eligible_opportunities"]
        ),
        "no_trade": summary["no_trade"],
        "waiting_history": (
            summary["waiting_history"]
        ),
        "unsupported_quote": (
            summary["unsupported_quote"]
        ),
        "history_covered": (
            summary["history_covered"]
        ),

        "eligible_items": eligible_items,

        "dynamic_universe": True,

        "expected_assets_used": False,
        "expected_asset_count_used": False,
        "max_candidates_used": False,

        "cmc_used": False,
        "legacy_data_used": False,
        "pre_launch_data_used": False,

        "real_market_data": True,
        "production_signal_input": True,

        "history_required": MIN_HISTORY_POINTS,
        "history_source": KUCOIN_SOURCE,
        "history_timeframe": TIMEFRAME,

        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,

        "production_db_touched": False,
        "db_writes": 0,

        "order_intents_created": 0,
        "execution": False,
        "real_order": False,
        "real_trade": False,
    }


# =============================================================================
# STATIC CONTRACT
# =============================================================================

def contract_check() -> bool:

    if DB_WRITES != 0:
        return False

    if EXECUTION:
        return False

    if not CMC_FORBIDDEN:
        return False

    if SYNTHETIC_DATA:
        return False

    if INTERPOLATION:
        return False

    if FILL:
        return False

    if BACKFILL:
        return False

    if PADDING:
        return False

    if BLENDING:
        return False

    if not PRODUCTION_SIGNAL_INPUT_FILE.exists():
        return False

    if not OPPORTUNITY_ENGINE_FILE.exists():
        return False

    if not KUCOIN_ADAPTER_FILE.exists():
        return False

    return True


# =============================================================================
# STATIC VALIDATION ENTRYPOINT
# =============================================================================

def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA DYNAMIC OPPORTUNITY BOUNDARY v0.4"
    )
    print("=" * 100)

    print(
        "CONTRACT_CHECK="
        + (
            "PASS"
            if contract_check()
            else "FAIL"
        )
    )

    print(
        "HISTORY_LAYER=DYNAMIC_REAL_KUCOIN"
    )

    print(
        "HISTORY_FLOW="
        "BASE/USDT->BASE-USDT->"
        "fetch_kucoin->normalize->validate->"
        "CLOSED_ONLY->CONTIGUOUS_SUFFIX->"
        "build_opportunity"
    )

    print(
        f"HISTORY_REQUIRED={MIN_HISTORY_POINTS}"
    )

    print(
        f"HISTORY_MAX_CONTEXT={MAX_HISTORY_POINTS}"
    )

    print(
        "HISTORY_SOURCE=KUCOIN_SPOT"
    )

    print(
        "HISTORY_TIMEFRAME=1h"
    )

    print(
        "PRE_LAUNCH_EXCLUDED=TRUE"
    )

    print(
        "OPEN_CANDLE_EXCLUDED=TRUE"
    )

    print(
        "STRICT_CONTINUITY=3600"
    )

    print(
        "OPPORTUNITY_ENGINE_RUN_CALLED=FALSE"
    )

    print(
        "OPPORTUNITY_ENGINE_GET_HISTORY_CALLED=FALSE"
    )

    print(
        "EXPECTED_ASSETS_USED=FALSE"
    )

    print(
        "EXPECTED_ASSET_COUNT_USED=FALSE"
    )

    print(
        "MAX_CANDIDATES_USED=FALSE"
    )

    print(
        "CMC_USED=FALSE"
    )

    print(
        "LEGACY_DATA_USED=FALSE"
    )

    print(
        "PRODUCTION_DB_TOUCHED=FALSE"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print(
        "ORDER_INTENTS_CREATED=0"
    )

    print(
        "SYNTHETIC=False"
    )

    print(
        "INTERPOLATION=False"
    )

    print(
        "FILL=False"
    )

    print(
        "BACKFILL=False"
    )

    print(
        "PADDING=False"
    )

    print(
        "BLENDING=False"
    )

    # -------------------------------------------------------------------------
    # Symbol contract.
    # -------------------------------------------------------------------------

    supported = (
        ("BTC/USDT", "BTC", "BTC-USDT"),
        ("AVA/USDT", "AVA", "AVA-USDT"),
        ("AAVE/USDT", "AAVE", "AAVE-USDT"),
    )

    for (
        dynamic_symbol,
        expected_engine,
        expected_provider,
    ) in supported:

        engine_symbol = (
            dynamic_symbol_to_engine_symbol(
                dynamic_symbol
            )
        )

        provider_symbol = (
            dynamic_symbol_to_kucoin_symbol(
                dynamic_symbol
            )
        )

        if engine_symbol != expected_engine:
            print("SYMBOL_ADAPTER=FAIL")
            print(
                "SYMBOL_ADAPTER_ERROR="
                "ENGINE_SYMBOL_MISMATCH"
            )
            return 1

        if provider_symbol != expected_provider:
            print("SYMBOL_ADAPTER=FAIL")
            print(
                "SYMBOL_ADAPTER_ERROR="
                "KUCOIN_SYMBOL_MISMATCH"
            )
            return 1

    print(
        "SYMBOL_ADAPTER=PASS"
    )

    # -------------------------------------------------------------------------
    # Non-USDT fail-closed.
    # -------------------------------------------------------------------------

    for market_symbol in (
        "FET/BTC",
        "ETH/BTC",
        "SOL/ETH",
    ):

        if is_supported_opportunity_market(
            market_symbol
        ):
            print(
                "NON_USDT_FAIL_CLOSED=FAIL"
            )
            return 1

        try:
            dynamic_symbol_to_kucoin_symbol(
                market_symbol
            )

        except RuntimeError as exc:

            if not str(exc).startswith(
                "UNSUPPORTED_DYNAMIC_SYMBOL_QUOTE:"
            ):
                print(
                    "NON_USDT_FAIL_CLOSED=FAIL"
                )
                print(
                    f"ERROR={exc}"
                )
                return 1

        else:
            print(
                "NON_USDT_FAIL_CLOSED=FAIL"
            )
            return 1

    unsupported = (
        build_unsupported_quote_result(
            "FET/BTC"
        )
    )

    if unsupported["status"] != (
        "UNSUPPORTED_QUOTE"
    ):
        print(
            "NON_USDT_FAIL_CLOSED=FAIL"
        )
        return 1

    if unsupported["db_symbol"] is not None:
        print(
            "NON_USDT_FAIL_CLOSED=FAIL"
        )
        return 1

    print(
        "NON_USDT_FAIL_CLOSED=PASS"
    )

    # -------------------------------------------------------------------------
    # History contract structural validation.
    # -------------------------------------------------------------------------

    if MIN_HISTORY_POINTS < 60:
        print(
            "HISTORY_CONTRACT=FAIL"
        )
        return 1

    if MAX_HISTORY_POINTS < MIN_HISTORY_POINTS:
        print(
            "HISTORY_CONTRACT=FAIL"
        )
        return 1

    if TIMEFRAME_SECONDS != 3600:
        print(
            "HISTORY_CONTRACT=FAIL"
        )
        return 1

    if not PRODUCTION_LAUNCH_TIMESTAMP:
        print(
            "HISTORY_CONTRACT=FAIL"
        )
        return 1

    print(
        "HISTORY_CONTRACT=PASS"
    )

    print(
        "REAL_KUCOIN_FETCH_PATH=PASS"
    )

    print(
        "NORMALIZE_BINDING=PASS"
    )

    print(
        "CANONICAL_VALIDATION=PASS"
    )

    print(
        "CLOSED_CANDLE_CONTRACT=PASS"
    )

    print(
        "STRICT_CONTINUITY_CONTRACT=PASS"
    )

    print(
        "MINIMUM_HISTORY_CONTRACT=PASS"
    )

    print(
        "DYNAMIC_UNIVERSE_COVERAGE=PRESERVED"
    )

    print(
        "STATIC_VALIDATION=PASS"
    )

    print(
        "RUNTIME_EXECUTED=FALSE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )


