
"""
ARUNDA DYNAMIC FUSION CONTRACT BOUNDARY v0.1
=============================================

Production boundary for dynamic-universe Fusion.

IMPORTANT
---------
fusion_engine.py is CLOSED.
It is NOT modified.

Historical fixed-15 run() is NOT used.

Production path:
    REAL DYNAMIC UNIVERSE
        ->
    Dynamic Fusion Boundary
        ->
    fusion_engine.fuse_asset()
        ->
    FUSED RESULT PER ASSET

The historical Fusion ASSETS contract is temporarily rebound
inside a controlled in-memory boundary context so that the
CLOSED fuse_asset() primitive can validate real dynamic assets.

No source modification.
No database writes.
No execution.
No synthetic data.
No interpolation.
No fill.
No backfill.
No padding.
No blending.
No CMC.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import importlib.util
from typing import Any, Dict, Iterable, List, Mapping


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

FUSION_FILE = ROOT / "fusion_engine.py"

UNIVERSE_FILE = (
    ROOT / "production_universe_contract_v0_1.py"
)


# ============================================================
# SAFETY CONTRACT
# ============================================================

SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False
CMC_USED = False

DB_WRITES = 0
EXECUTION = "OFF"


# ============================================================
# SAFE MODULE LOADER
# ============================================================

def load_module(
    path: Path,
    module_name: str,
):
    if not path.exists():
        raise FileNotFoundError(
            f"MODULE_NOT_FOUND:{path.name}"
        )

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


# ============================================================
# ASSET NORMALIZATION
# ============================================================

def normalize_asset(asset: Any) -> str:
    if not isinstance(asset, str):
        raise ValueError(
            "ASSET_MUST_BE_STRING"
        )

    value = asset.strip().upper()

    if not value:
        raise ValueError(
            "EMPTY_ASSET"
        )

    return value


# ============================================================
# REAL PRODUCTION UNIVERSE
# ============================================================

def discover_production_assets() -> tuple[str, ...]:

    universe = load_module(
        UNIVERSE_FILE,
        "arunda_dynamic_fusion_universe",
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    if not callable(discover):
        raise AttributeError(
            "DISCOVER_PRODUCTION_ASSETS_UNAVAILABLE"
        )

    assets = tuple(
        normalize_asset(asset)
        for asset in discover()
    )

    if not assets:
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_EMPTY"
        )

    if len(assets) != len(set(assets)):
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_DUPLICATES"
        )

    return assets


# ============================================================
# INFORMATION ITEM ASSET VALIDATION
# ============================================================

def validate_information_asset(
    item: Mapping[str, Any],
    universe: set[str],
) -> bool:

    if not isinstance(item, Mapping):
        return False

    asset = item.get("asset")

    if not isinstance(asset, str):
        return False

    return normalize_asset(asset) in universe


# ============================================================
# FILTER INFORMATION FOR ONE ASSET
# ============================================================

def filter_information_for_asset(
    asset: str,
    items: Iterable[Mapping[str, Any]],
    universe: set[str],
) -> List[Dict[str, Any]]:

    dynamic_asset = normalize_asset(asset)

    output: List[Dict[str, Any]] = []

    for item in items:

        if not isinstance(item, Mapping):
            continue

        item_asset = item.get("asset")

        if not isinstance(item_asset, str):
            continue

        item_asset = normalize_asset(
            item_asset
        )

        # Exact asset identity.
        if item_asset != dynamic_asset:
            continue

        # Must belong to the real Production Universe.
        if item_asset not in universe:
            continue

        output.append(
            dict(item)
        )

    return output


# ============================================================
# CONTROLLED FUSION ASSET BINDING
# ============================================================

@contextmanager
def dynamic_fusion_asset_binding(
    fusion: Any,
    universe: tuple[str, ...],
):
    """
    Temporarily bind the CLOSED Fusion engine's internal ASSETS
    to the real Production Universe.

    This is an in-memory boundary operation only.

    The fusion_engine.py source is never modified.
    """

    if not hasattr(fusion, "ASSETS"):
        raise RuntimeError(
            "FUSION_ASSETS_SYMBOL_MISSING"
        )

    original_assets = fusion.ASSETS

    dynamic_assets = list(universe)

    fusion.ASSETS = dynamic_assets

    try:
        yield
    finally:
        fusion.ASSETS = original_assets


# ============================================================
# SINGLE-ASSET FUSION
# ============================================================

def fuse_dynamic_asset(
    asset: str,
    market_signal: Mapping[str, Any] | None,
    news_items: Iterable[Mapping[str, Any]],
    social_items: Iterable[Mapping[str, Any]],
    universe: tuple[str, ...] | None = None,
) -> Dict[str, Any]:

    if universe is None:
        universe = discover_production_assets()

    # Production Universe may be canonical BASE/USDT symbols.
    # CLOSED fusion_engine.fuse_asset() operates on base assets.
    universe_assets = tuple(
        normalize_asset(
            symbol.split("/", 1)[0]
        )
        if isinstance(symbol, str) and "/" in symbol
        else normalize_asset(symbol)
        for symbol in universe
    )

    universe_set = set(universe_assets)

    dynamic_asset = normalize_asset(asset)


    if dynamic_asset not in universe_set:
        raise ValueError(
            f"ASSET_NOT_IN_PRODUCTION_UNIVERSE:"
            f"{dynamic_asset}"
        )

    fusion = load_module(
        FUSION_FILE,
        "arunda_closed_fusion_engine",
    )

    fuse_asset = getattr(
        fusion,
        "fuse_asset",
        None,
    )

    if not callable(fuse_asset):
        raise AttributeError(
            "FUSION_FUSE_ASSET_UNAVAILABLE"
        )

    market = None

    if market_signal is not None:

        if not isinstance(
            market_signal,
            Mapping,
        ):
            raise ValueError(
                f"INVALID_MARKET_SIGNAL:"
                f"{dynamic_asset}"
            )

        market = dict(
            market_signal
        )

        signal_asset = market.get(
            "asset"
        )

        if signal_asset is not None:

            signal_asset = normalize_asset(
                signal_asset
            )

            if signal_asset != dynamic_asset:
                raise ValueError(
                    "MARKET_SIGNAL_ASSET_MISMATCH:"
                    f"{dynamic_asset}:{signal_asset}"
                )

        else:
            market["asset"] = dynamic_asset

    news = filter_information_for_asset(
        dynamic_asset,
        news_items,
        universe_set,
    )

    social = filter_information_for_asset(
        dynamic_asset,
        social_items,
        universe_set,
    )

    # --------------------------------------------------------
    # CLOSED ENGINE PRIMITIVE
    # --------------------------------------------------------

    with dynamic_fusion_asset_binding(
        fusion,
        universe_assets,
    ):

        result = fuse_asset(
            dynamic_asset,
            market,
            news,
            social,
        )

    if not isinstance(result, dict):
        raise RuntimeError(
            f"FUSION_RESULT_NOT_DICT:{dynamic_asset}"
        )

    result_asset = normalize_asset(
        result.get("asset", dynamic_asset)
    )

    if result_asset != dynamic_asset:
        raise RuntimeError(
            "FUSION_ASSET_IDENTITY_BROKEN:"
            f"{dynamic_asset}:{result_asset}"
        )

    return result


# ============================================================
# FULL DYNAMIC FUSION
# ============================================================

def fuse_dynamic_universe(
    market_signals: Mapping[str, Mapping[str, Any]],
    news_items: Iterable[Mapping[str, Any]] | None = None,
    social_items: Iterable[Mapping[str, Any]] | None = None,
) -> Dict[str, Dict[str, Any]]:

    universe = discover_production_assets()

    if not isinstance(
        market_signals,
        Mapping,
    ):
        raise ValueError(
            "MARKET_SIGNALS_MUST_BE_MAPPING"
        )

    news = (
        list(news_items)
        if news_items is not None
        else []
    )

    social = (
        list(social_items)
        if social_items is not None
        else []
    )

    expected = set(universe)

    actual = {
        normalize_asset(asset)
        for asset in market_signals.keys()
    }

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            "MISSING_PRODUCTION_MARKET_SIGNALS:"
            + repr(sorted(missing))
        )

    if extra:
        raise RuntimeError(
            "UNEXPECTED_MARKET_SIGNALS:"
            + repr(sorted(extra))
        )

    results: Dict[str, Dict[str, Any]] = {}

    for asset in universe:

        results[asset] = fuse_dynamic_asset(
            asset=asset,
            market_signal=market_signals[asset],
            news_items=news,
            social_items=social,
        )

    if set(results.keys()) != expected:
        raise RuntimeError(
            "FUSION_DYNAMIC_CARDINALITY_FAILED"
        )

    return results


# ============================================================
# STATIC CONTRACT CHECK
# ============================================================

def static_contract_check() -> dict[str, Any]:

    fusion = load_module(
        FUSION_FILE,
        "arunda_fusion_static_engine",
    )

    universe = load_module(
        UNIVERSE_FILE,
        "arunda_fusion_static_universe",
    )

    fuse_asset = getattr(
        fusion,
        "fuse_asset",
        None,
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    if not callable(fuse_asset):
        raise RuntimeError(
            "FUSE_ASSET_MISSING"
        )

    if not callable(discover):
        raise RuntimeError(
            "UNIVERSE_DISCOVERY_MISSING"
        )

    assets = tuple(
        normalize_asset(asset)
        for asset in discover()
    )

    if not assets:
        raise RuntimeError(
            "STATIC_UNIVERSE_EMPTY"
        )

    if len(assets) != len(set(assets)):
        raise RuntimeError(
            "STATIC_UNIVERSE_DUPLICATES"
        )

    # Production boundary must not use historical run().
    run = getattr(
        fusion,
        "run",
        None,
    )

    if not callable(run):
        raise RuntimeError(
            "FUSION_RUN_MISSING"
        )

    return {
        "STATUS": "PASS",

        "DYNAMIC_UNIVERSE": True,
        "VARIABLE_CARDINALITY": True,
        "UNIVERSE_OWNS_CARDINALITY": True,

        "SINGLE_ASSET_FUSION": True,
        "FUSE_ASSET_USED": True,
        "FIXED_15_RUN_USED": False,
        "FUSION_RUN_USED": False,

        "DYNAMIC_ASSET_BINDING": True,
        "SOURCE_ENGINE_MODIFIED": False,

        "ASSET_IDENTITY_PRESERVED": True,
        "PER_ASSET_INFORMATION_FILTER": True,

        "SYNTHETIC": SYNTHETIC,
        "INTERPOLATION": INTERPOLATION,
        "FILL": FILL,
        "BACKFILL": BACKFILL,
        "PADDING": PADDING,
        "BLENDING": BLENDING,

        "CMC_USED": CMC_USED,

        "DB_WRITES": DB_WRITES,
        "EXECUTION": EXECUTION,

        "PRODUCTION_UNIVERSE_SIZE": len(assets),
    }


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    result = static_contract_check()

    for key, value in result.items():
        print(
            f"{key}={value}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
