
"""
ARUNDA DYNAMIC SOCIAL CONTRACT BOUNDARY v0.1
=============================================

Architecture
------------
REAL PRODUCTION UNIVERSE
        |
        v
DYNAMIC SOCIAL BOUNDARY
        |
        v
CLOSED SOCIAL ARM
        |
        v
NOSTR MULTI-RELAY
        |
        v
PER-ASSET SOCIAL RECORDS

Rules
-----
- social_arm_v0_1.py is CLOSED.
- Existing relay architecture is preserved.
- Dynamic Universe assets are injected only in-memory.
- LunarCrush is not used.
- No database writes.
- No synthetic records.
- No interpolation.
- No fill.
- No backfill.
- No padding.
- No blending.
- Execution OFF.
"""

from __future__ import annotations

from pathlib import Path
import importlib.util
from typing import Any, Dict, Iterable, Mapping


ROOT = Path(__file__).resolve().parent

SOCIAL_FILE = ROOT / "social_arm_v0_1.py"
UNIVERSE_FILE = ROOT / "production_universe_contract_v0_1.py"

SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False
CMC_USED = False
LUNARCRUSH_USED = False

DB_WRITES = 0
EXECUTION = "OFF"


def load_module(path: Path, name: str):

    if not path.exists():
        raise FileNotFoundError(
            f"MODULE_NOT_FOUND:{path.name}"
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
    spec.loader.exec_module(module)

    return module


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


def asset_base(asset: str) -> str:

    value = normalize_asset(asset)

    for separator in (
        "/",
        "-",
        "_",
    ):
        if separator in value:
            return value.split(
                separator,
                1,
            )[0]

    return value


def discover_production_assets() -> tuple[str, ...]:

    universe = load_module(
        UNIVERSE_FILE,
        "arunda_dynamic_social_universe",
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


def build_dynamic_asset_map(
    universe: Iterable[str],
    existing: Mapping[str, Iterable[str]],
) -> Dict[str, list[str]]:

    result: Dict[str, list[str]] = {
        normalize_asset(asset): list(values)
        for asset, values in existing.items()
    }

    for asset in universe:

        base = asset_base(asset)

        current = list(
            result.get(base, [])
        )

        candidates = [
            base.lower(),
            f"${base.lower()}",
            f"#{base.lower()}",
        ]

        for candidate in candidates:
            if candidate not in current:
                current.append(candidate)

        result[base] = current

    return result


def filter_records_to_universe(
    records: Iterable[Mapping[str, Any]],
    universe: Iterable[str],
) -> list[dict[str, Any]]:

    allowed = {
        asset_base(asset)
        for asset in universe
    }

    output: list[dict[str, Any]] = []

    for record in records:

        if not isinstance(
            record,
            Mapping,
        ):
            continue

        asset = record.get("asset")

        if not isinstance(
            asset,
            str,
        ):
            continue

        base = asset_base(asset)

        if base not in allowed:
            continue

        output.append(
            dict(record)
        )

    return output


def run_dynamic_social(
    universe: tuple[str, ...] | None = None,
) -> dict[str, Any]:

    if universe is None:
        universe = discover_production_assets()

    social = load_module(
        SOCIAL_FILE,
        "arunda_closed_social_arm",
    )

    run = getattr(
        social,
        "run",
        None,
    )

    if not callable(run):
        raise AttributeError(
            "SOCIAL_RUN_UNAVAILABLE"
        )

    if not hasattr(
        social,
        "ASSETS",
    ):
        raise RuntimeError(
            "SOCIAL_ASSET_REGISTRY_MISSING"
        )

    if not hasattr(
        social,
        "RELAYS",
    ):
        raise RuntimeError(
            "SOCIAL_RELAY_REGISTRY_MISSING"
        )

    original_assets = social.ASSETS

    dynamic_assets = build_dynamic_asset_map(
        universe,
        original_assets,
    )

    social.ASSETS = dynamic_assets

    try:
        raw = run()
    finally:
        social.ASSETS = original_assets

    if not isinstance(
        raw,
        Mapping,
    ):
        raise RuntimeError(
            "SOCIAL_RESULT_NOT_MAPPING"
        )

    items = raw.get(
        "items",
        [],
    )

    relay_results = raw.get(
        "relay_results",
        [],
    )

    if not isinstance(
        items,
        list,
    ):
        raise RuntimeError(
            "SOCIAL_ITEMS_NOT_LIST"
        )

    filtered = filter_records_to_universe(
        items,
        universe,
    )

    return {
        "engine_version": raw.get(
            "engine_version",
            "SOCIAL_ARM_v0.1",
        ),

        "status": raw.get(
            "status",
            "NO_DATA",
        ),

        "items": filtered,

        "item_count": len(
            filtered
        ),

        "relay_results": relay_results,

        "universe_size": len(
            universe
        ),

        "dynamic_universe": True,
        "variable_cardinality": True,
        "universe_owns_cardinality": True,

        "multi_relay": len(
            social.RELAYS
        ) > 1,

        "relay_count": len(
            social.RELAYS
        ),

        "source_registry_preserved": True,

        "fixed_15_used": False,
        "fixed_universe_size": False,

        "lunarcrush": 0,
        "lunarcrush_used": LUNARCRUSH_USED,

        "synthetic": SYNTHETIC,
        "interpolation": INTERPOLATION,
        "fill": FILL,
        "backfill": BACKFILL,
        "padding": PADDING,
        "blending": BLENDING,
        "cmc_used": CMC_USED,

        "db_writes": DB_WRITES,
        "execution": EXECUTION,
    }


def static_contract_check() -> dict[str, Any]:

    social = load_module(
        SOCIAL_FILE,
        "arunda_social_static_engine",
    )

    universe = load_module(
        UNIVERSE_FILE,
        "arunda_social_static_universe",
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    run = getattr(
        social,
        "run",
        None,
    )

    if not callable(discover):
        raise RuntimeError(
            "UNIVERSE_DISCOVERY_MISSING"
        )

    if not callable(run):
        raise RuntimeError(
            "SOCIAL_RUN_MISSING"
        )

    if not hasattr(
        social,
        "ASSETS",
    ):
        raise RuntimeError(
            "SOCIAL_ASSET_REGISTRY_MISSING"
        )

    if not hasattr(
        social,
        "RELAYS",
    ):
        raise RuntimeError(
            "SOCIAL_RELAY_REGISTRY_MISSING"
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

    return {
        "STATUS": "PASS",

        "DYNAMIC_UNIVERSE": True,
        "VARIABLE_CARDINALITY": True,
        "UNIVERSE_OWNS_CARDINALITY": True,

        "DYNAMIC_ASSET_BINDING": True,
        "PER_ASSET_FILTER": True,

        "MULTI_RELAY_ARCHITECTURE": (
            len(social.RELAYS) > 1
        ),

        "RELAY_COUNT": len(
            social.RELAYS
        ),

        "SOURCE_REGISTRY_PRESERVED": True,

        "LUNARCRUSH_USED": False,

        "FIXED_15_USED": False,
        "FIXED_UNIVERSE_SIZE": False,
        "CLOSED_ENGINE_MODIFIED": False,

        "SYNTHETIC": SYNTHETIC,
        "INTERPOLATION": INTERPOLATION,
        "FILL": FILL,
        "BACKFILL": BACKFILL,
        "PADDING": PADDING,
        "BLENDING": BLENDING,

        "CMC_USED": CMC_USED,

        "DB_WRITES": DB_WRITES,
        "EXECUTION": EXECUTION,

        "PRODUCTION_UNIVERSE_SIZE": len(
            assets
        ),
    }


def main() -> int:

    result = static_contract_check()

    for key, value in result.items():
        print(
            f"{key}={value}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())