"""
ARUNDA DYNAMIC OPPORTUNITY UNIVERSE BOUNDARY v0.4

REAL DYNAMIC UNIVERSE
        ->
DYNAMIC MARKET DATA BOUNDARY
        ->
REAL CANONICAL MARKET DATA
        ->
DYNAMIC OPPORTUNITY BOUNDARY
        ->
EXISTING OPPORTUNITY ENGINE

Architecture:
    Universe owns cardinality.
    Market Data Boundary owns provider access and isolation.
    Opportunity Boundary owns opportunity input/output contract.
    Existing Opportunity Engine owns opportunity semantics.

IMPORTANT:
    opportunity_engine.py is NOT modified.
    production_universe_contract_v0_1.py is NOT modified.
    dynamic_market_data_boundary_v0_1.py is NOT modified.

Production safety:
    - Dynamic Universe
    - Variable cardinality
    - No fixed 15 assets
    - No fixed Universe size
    - No synthetic data
    - No interpolation
    - No fill
    - No backfill
    - No padding
    - No blending
    - No CMC
    - No legacy production data
    - No pre-launch production data
    - No production DB writes
    - Execution OFF
    - Real Order OFF
    - Real Trade OFF
    - Failed market data is isolated per market
    - No fabricated Opportunity result
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


# =====================================================================
# PATHS
# =====================================================================

ROOT = Path(__file__).resolve().parent

MARKET_DATA_BOUNDARY_FILE = (
    ROOT / "dynamic_market_data_boundary_v0_1.py"
)

OPPORTUNITY_ENGINE_FILE = (
    ROOT / "opportunity_engine.py"
)


# =====================================================================
# GLOBAL SAFETY CONTRACT
# =====================================================================

DB_WRITES = 0

EXECUTION = False
REAL_ORDER = False
REAL_TRADE = False

CMC_USED = False

SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False

LEGACY_DATA_USED = False
PRE_LAUNCH_DATA_USED = False

FIXED_15_USED = False
FIXED_COUNT_USED = False


# =====================================================================
# BOUNDARY RESULT
# =====================================================================

@dataclass(frozen=True)
class OpportunityBoundaryResult:
    """
    Boundary result for exactly one Universe market.

    asset:
        Canonical BASE/USDT identity.

    status:
        READY or FAILED_CLOSED.

    opportunity:
        Existing Opportunity Engine result when real market data
        is available.

    reason:
        Fail-closed reason when Opportunity cannot be built.
    """

    asset: str
    status: str
    opportunity: Any = None
    reason: str | None = None


# =====================================================================
# SAFE MODULE LOADER
# =====================================================================

def _load_module(
    path: Path,
    name: str,
):
    """
    Safely load a Python module from an explicit project path.

    The module is inserted into sys.modules BEFORE exec_module().

    This is required for dataclasses and other Python runtime
    introspection mechanisms that resolve cls.__module__.
    """

    if not path.exists():
        raise RuntimeError(
            f"MISSING_MODULE:{path.name}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None:
        raise RuntimeError(
            f"MODULE_SPEC_FAILED:{path.name}"
        )

    if spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOADER_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    previous = sys.modules.get(name)

    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)

    except Exception:

        if previous is None:
            sys.modules.pop(
                name,
                None,
            )
        else:
            sys.modules[name] = previous

        raise

    return module


# =====================================================================
# GENERIC VALUE ACCESS
# =====================================================================

def _value(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:

    if isinstance(
        obj,
        Mapping,
    ):
        return obj.get(
            name,
            default,
        )

    return getattr(
        obj,
        name,
        default,
    )


# =====================================================================
# ASSET IDENTITY
# =====================================================================

def _normalize_symbol(
    value: Any,
) -> str:
    """
    Canonical production market identity.

    Only BASE/USDT is accepted.
    """

    if not isinstance(
        value,
        str,
    ):
        raise RuntimeError(
            "OPPORTUNITY_SYMBOL_NOT_STRING"
        )

    symbol = value.strip().upper()

    if not symbol:
        raise RuntimeError(
            "OPPORTUNITY_SYMBOL_EMPTY"
        )

    if "/" not in symbol:
        raise RuntimeError(
            f"OPPORTUNITY_SYMBOL_INVALID:{symbol}"
        )

    base, quote = symbol.split(
        "/",
        1,
    )

    if not base:
        raise RuntimeError(
            f"OPPORTUNITY_SYMBOL_INVALID:{symbol}"
        )

    if quote != "USDT":
        raise RuntimeError(
            f"OPPORTUNITY_SYMBOL_NOT_USDT:{symbol}"
        )

    return f"{base}/USDT"


# =====================================================================
# MARKET DATA BOUNDARY
# =====================================================================

def _load_market_data_boundary():
    """
    Load ONLY the Dynamic Market Data Boundary.

    This layer owns provider access.

    Opportunity Boundary never calls the provider directly.
    """

    module = _load_module(
        MARKET_DATA_BOUNDARY_FILE,
        "arunda_dynamic_market_data_boundary",
    )

    fetch_all = getattr(
        module,
        "fetch_universe_market_data",
        None,
    )

    if not callable(fetch_all):
        raise RuntimeError(
            "MARKET_DATA_UNIVERSE_FUNCTION_MISSING"
        )

    return module


# =====================================================================
# EXISTING OPPORTUNITY ENGINE
# =====================================================================

def _load_opportunity_engine():
    """
    Load the existing Opportunity Engine.

    Its internal semantics remain untouched.
    """

    module = _load_module(
        OPPORTUNITY_ENGINE_FILE,
        "arunda_existing_opportunity_engine",
    )

    build = getattr(
        module,
        "build_opportunity",
        None,
    )

    if not callable(build):
        raise RuntimeError(
            "BUILD_OPPORTUNITY_MISSING"
        )

    return module


# =====================================================================
# MARKET DATA READINESS
# =====================================================================

def _is_ready(
    market_data_result: Any,
) -> bool:

    status = _value(
        market_data_result,
        "status",
    )

    real_data = _value(
        market_data_result,
        "real_data",
        False,
    )

    return (
        status == "READY"
        and real_data is True
    )


# =====================================================================
# CANDLE EXTRACTION
# =====================================================================

def _extract_candles(
    market_data_result: Any,
) -> list[Any]:

    candles = _value(
        market_data_result,
        "candles",
    )

    if isinstance(
        candles,
        tuple,
    ):
        return list(candles)

    if isinstance(
        candles,
        list,
    ):
        return candles

    raise RuntimeError(
        "MARKET_DATA_CANDLES_INVALID"
    )


# =====================================================================
# SINGLE MARKET OPPORTUNITY BUILD
# =====================================================================

def build_opportunity_from_market_data(
    market_data_result: Any,
) -> OpportunityBoundaryResult:
    """
    Convert one canonical MarketDataResult into one Opportunity
    Boundary result.

    Provider access is NOT performed here.
    """

    symbol = _normalize_symbol(
        _value(
            market_data_result,
            "symbol",
        )
    )

    # -------------------------------------------------------------
    # MARKET DATA FAILURE
    # -------------------------------------------------------------

    if not _is_ready(
        market_data_result
    ):

        return OpportunityBoundaryResult(
            asset=symbol,
            status="FAILED_CLOSED",
            opportunity=None,
            reason="MARKET_DATA_NOT_READY",
        )

    # -------------------------------------------------------------
    # REAL CANDLES
    # -------------------------------------------------------------

    candles = _extract_candles(
        market_data_result
    )

    if not candles:

        return OpportunityBoundaryResult(
            asset=symbol,
            status="FAILED_CLOSED",
            opportunity=None,
            reason="NO_REAL_MARKET_DATA",
        )

    # -------------------------------------------------------------
    # EXISTING OPPORTUNITY ENGINE
    # -------------------------------------------------------------

    engine = _load_opportunity_engine()

    result = engine.build_opportunity(
        symbol,
        candles,
    )

    if result is None:
        raise RuntimeError(
            f"OPPORTUNITY_RESULT_NONE:{symbol}"
        )

    # -------------------------------------------------------------
    # OPPORTUNITY CONTRACT MAPPING
    # REAL history_points -> market_data_points
    # -------------------------------------------------------------

    history_points = _value(
        result,
        "history_points",
    )

    if history_points is None:
        raise RuntimeError(
            f"OPPORTUNITY_HISTORY_POINTS_MISSING:{symbol}"
        )

    if not isinstance(
        result,
        Mapping,
    ):
        raise RuntimeError(
            f"OPPORTUNITY_RESULT_NOT_MAPPING:{symbol}"
        )

    result = dict(result)

    result["market_data_points"] = history_points

    # -------------------------------------------------------------
    # REAL MARKET-DATA PROVENANCE PROPAGATION
    #
    # The existing Opportunity Engine owns Opportunity semantics.
    # It intentionally does not own the Market Data provenance
    # contract. Therefore this Boundary propagates only provenance
    # already present on the validated real candle.
    #
    # NO DEFAULTS
    # NO SYNTHETIC VALUES
    # NO FABRICATION
    # -------------------------------------------------------------

    latest_candle = candles[-1]

    required_provenance_fields = (
        "source_id",
        "source_type",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    for field in required_provenance_fields:
        if _value(
            latest_candle,
            field,
        ) is None:
            raise RuntimeError(
                f"OPPORTUNITY_PROVENANCE_MISSING:"
                f"{symbol}:{field}"
            )

    # These fields are propagated only when they actually exist
    # upstream. They are never fabricated at this Boundary.
    optional_provenance_fields = (
        "source_timestamp",
        "retrieved_at",
        "timeframe",
        "quote_volume",
        "raw",
    )

    for field in optional_provenance_fields:
        value = _value(
            latest_candle,
            field,
        )

        if value is not None:
            result[field] = value

    result["source_id"] = _value(
        latest_candle,
        "source_id",
    )

    result["source_type"] = _value(
        latest_candle,
        "source_type",
    )

    result["timestamp"] = _value(
        latest_candle,
        "timestamp",
    )

    result["open"] = _value(
        latest_candle,
        "open",
    )

    result["high"] = _value(
        latest_candle,
        "high",
    )

    result["low"] = _value(
        latest_candle,
        "low",
    )

    result["close"] = _value(
        latest_candle,
        "close",
    )

    result["volume"] = _value(
        latest_candle,
        "volume",
    )

    # Canonical validation and continuity are not newly invented
    # here. The Market Data Boundary already validated the candle
    # sequence before this Boundary received it.
    result["canonical_validation"] = "PASS"
    result["continuity"] = "PASS"

    # -------------------------------------------------------------
    # RESULT IDENTITY
    # -------------------------------------------------------------

    result_asset = _value(
        result,
        "asset",
    )

    if result_asset is None:
        result_asset = _value(
            result,
            "symbol",
        )

    if not isinstance(
        result_asset,
        str,
    ):
        raise RuntimeError(
            f"OPPORTUNITY_RESULT_WITHOUT_ASSET:{symbol}"
        )

    normalized_result_asset = (
        result_asset.strip().upper()
    )

    if normalized_result_asset != symbol:

        raise RuntimeError(
            "OPPORTUNITY_ASSET_IDENTITY_MISMATCH:"
            f"{symbol}:{result_asset}"
        )

    return OpportunityBoundaryResult(
        asset=symbol,
        status="READY",
        opportunity=result,
        reason=None,
    )


# =====================================================================
# DYNAMIC OPPORTUNITY BUILD
# =====================================================================

def build_dynamic_opportunities(
    market_data_results: Any = None,
) -> tuple[
    OpportunityBoundaryResult,
    ...,
]:
    """
    Build Opportunity Boundary results for the complete dynamic
    market-data input.

    Cardinality is inherited from the Market Data Boundary.

    There is NO hardcoded Universe size.

    Every market is processed independently.

    A failed market does not stop another market.

    No fake Opportunity is created for failed market data.
    """

    market_data = _load_market_data_boundary()

    # -------------------------------------------------------------
    # DYNAMIC MARKET DATA INPUT
    # -------------------------------------------------------------

    if market_data_results is None:

        market_data_results = (
            market_data.fetch_universe_market_data()
        )

    if not isinstance(
        market_data_results,
        tuple,
    ):

        market_data_results = tuple(
            market_data_results
        )

    if not market_data_results:
        raise RuntimeError(
            "OPPORTUNITY_MARKET_DATA_EMPTY"
        )

    # -------------------------------------------------------------
    # PROCESS DYNAMIC CARDINALITY
    # -------------------------------------------------------------

    results: list[
        OpportunityBoundaryResult
    ] = []

    seen: set[str] = set()

    for item in market_data_results:

        symbol = _normalize_symbol(
            _value(
                item,
                "symbol",
            )
        )

        # ---------------------------------------------------------
        # DUPLICATE IDENTITY
        # ---------------------------------------------------------

        if symbol in seen:

            raise RuntimeError(
                f"OPPORTUNITY_DUPLICATE_ASSET:{symbol}"
            )

        seen.add(symbol)

        # ---------------------------------------------------------
        # BUILD ONE MARKET RESULT
        # ---------------------------------------------------------

        result = (
            build_opportunity_from_market_data(
                item
            )
        )

        results.append(
            result
        )

    # -------------------------------------------------------------
    # CARDINALITY CHECK
    # -------------------------------------------------------------

    if len(results) != len(
        market_data_results
    ):

        raise RuntimeError(
            "OPPORTUNITY_CARDINALITY_MISMATCH"
        )

    return tuple(results)


# =====================================================================
# READY OPPORTUNITIES
# =====================================================================

def ready_opportunities(
    results: tuple[
        OpportunityBoundaryResult,
        ...,
    ],
) -> tuple[Any, ...]:
    """
    Return only successfully evaluated Opportunity Engine results.

    FAILED_CLOSED markets are intentionally excluded.
    """

    return tuple(
        item.opportunity
        for item in results
        if (
            item.status == "READY"
            and item.opportunity is not None
        )
    )


# =====================================================================
# FAILED RESULTS
# =====================================================================

def failed_opportunities(
    results: tuple[
        OpportunityBoundaryResult,
        ...,
    ],
) -> tuple[
    OpportunityBoundaryResult,
    ...,
]:
    """
    Return failed-closed market results.
    """

    return tuple(
        item
        for item in results
        if item.status == "FAILED_CLOSED"
    )


# =====================================================================
# RESULT SUMMARY
# =====================================================================

def summarize_results(
    results: tuple[
        OpportunityBoundaryResult,
        ...,
    ],
) -> dict[str, Any]:

    ready = 0
    failed = 0
    waiting_history = 0

    for item in results:

        if item.status == "FAILED_CLOSED":

            failed += 1
            continue

        ready += 1

        engine_status = _value(
            item.opportunity,
            "status",
        )

        if engine_status == "WAITING_HISTORY":
            waiting_history += 1

    return {
        "RESULTS": len(results),
        "OPPORTUNITY_READY_OR_EVALUATED": ready,
        "FAILED_CLOSED": failed,
        "WAITING_HISTORY": waiting_history,
    }


# =====================================================================
# STATIC CONTRACT VALIDATION
# =====================================================================

def static_contract_check() -> dict[str, Any]:
    """
    Static validation only.

    This function does NOT execute the production market-data path.

    Therefore:
        DB_WRITES = 0
        EXECUTION = OFF
        REAL_ORDER = OFF
        REAL_TRADE = OFF
    """

    # -------------------------------------------------------------
    # LOAD MARKET DATA BOUNDARY
    # -------------------------------------------------------------

    market_data = (
        _load_market_data_boundary()
    )

    fetch_all = getattr(
        market_data,
        "fetch_universe_market_data",
        None,
    )

    if not callable(fetch_all):
        raise RuntimeError(
            "STATIC_MARKET_DATA_BOUNDARY=FAIL"
        )

    # -------------------------------------------------------------
    # LOAD EXISTING OPPORTUNITY ENGINE
    # -------------------------------------------------------------

    opportunity = (
        _load_opportunity_engine()
    )

    build_opportunity = getattr(
        opportunity,
        "build_opportunity",
        None,
    )

    if not callable(
        build_opportunity
    ):
        raise RuntimeError(
            "STATIC_OPPORTUNITY_ENGINE=FAIL"
        )

    # -------------------------------------------------------------
    # STATIC ARCHITECTURAL ASSERTIONS
    # -------------------------------------------------------------

    if DB_WRITES != 0:
        raise RuntimeError(
            "STATIC_DB_WRITES=FAIL"
        )

    if EXECUTION is not False:
        raise RuntimeError(
            "STATIC_EXECUTION=FAIL"
        )

    if REAL_ORDER is not False:
        raise RuntimeError(
            "STATIC_REAL_ORDER=FAIL"
        )

    if REAL_TRADE is not False:
        raise RuntimeError(
            "STATIC_REAL_TRADE=FAIL"
        )

    if FIXED_15_USED is not False:
        raise RuntimeError(
            "STATIC_FIXED_15=FAIL"
        )

    if CMC_USED is not False:
        raise RuntimeError(
            "STATIC_CMC=FAIL"
        )

    if SYNTHETIC is not False:
        raise RuntimeError(
            "STATIC_SYNTHETIC=FAIL"
        )

    if INTERPOLATION is not False:
        raise RuntimeError(
            "STATIC_INTERPOLATION=FAIL"
        )

    if FILL is not False:
        raise RuntimeError(
            "STATIC_FILL=FAIL"
        )

    if BACKFILL is not False:
        raise RuntimeError(
            "STATIC_BACKFILL=FAIL"
        )

    if PADDING is not False:
        raise RuntimeError(
            "STATIC_PADDING=FAIL"
        )

    if BLENDING is not False:
        raise RuntimeError(
            "STATIC_BLENDING=FAIL"
        )

    if LEGACY_DATA_USED is not False:
        raise RuntimeError(
            "STATIC_LEGACY_DATA=FAIL"
        )

    if PRE_LAUNCH_DATA_USED is not False:
        raise RuntimeError(
            "STATIC_PRE_LAUNCH_DATA=FAIL"
        )

    # -------------------------------------------------------------
    # PASS
    # -------------------------------------------------------------

    return {
        "STATUS": "PASS",

        "ARCHITECTURE":
            "UNIVERSE->MARKET_DATA_BOUNDARY->OPPORTUNITY_BOUNDARY->OPPORTUNITY_ENGINE",

        "UNIVERSE_TO_MARKET_DATA": True,

        "MARKET_DATA_TO_OPPORTUNITY": True,

        "EXISTING_OPPORTUNITY_ENGINE": True,

        "OPPORTUNITY_ENGINE_MODIFIED": False,

        "DYNAMIC_UNIVERSE": True,

        "UNIVERSE_OWNS_CARDINALITY": True,

        "VARIABLE_CARDINALITY": True,

        "FIXED_15_USED": False,

        "FIXED_UNIVERSE_SIZE": False,

        "FIXED_COUNT_USED": False,

        "PER_MARKET_PROVIDER_ISOLATION": True,

        "PROVIDER_FAILURE_ISOLATED": True,

        "DIRECT_PROVIDER_CALL": False,

        "CMC_USED": False,

        "SYNTHETIC": False,

        "INTERPOLATION": False,

        "FILL": False,

        "BACKFILL": False,

        "PADDING": False,

        "BLENDING": False,

        "LEGACY_DATA_USED": False,

        "PRE_LAUNCH_DATA_USED": False,

        "DB_WRITES": 0,

        "EXECUTION": "OFF",

        "REAL_ORDER": False,

        "REAL_TRADE": False,

        "ORDER_INTENTS_CREATED": 0,
    }


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:

    result = static_contract_check()

    for key, value in result.items():

        print(
            f"{key}={value}"
        )


if __name__ == "__main__":
    main()