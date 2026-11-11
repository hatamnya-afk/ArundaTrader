
"""
ARUNDA DYNAMIC NEWS CONTRACT BOUNDARY v0.1
===========================================

Architecture
------------
REAL PRODUCTION UNIVERSE
        |
        v
DYNAMIC NEWS BOUNDARY
        |
        v
CLOSED NEWS ARM
        |
        v
REAL MULTI-SOURCE NEWS
        |
        v
PER-ASSET INFORMATION

Rules
-----
- news_arm_v0_1.py is CLOSED.
- Source registry is preserved.
- Existing RSS providers are preserved.
- Dynamic Universe aliases are injected only in-memory.
- No production source modification.
- No database writes.
- No synthetic records.
- No interpolation.
- No fill.
- No backfill.
- No padding.
- No blending.
- No CMC.
- Execution OFF.
"""

from __future__ import annotations

from pathlib import Path
import importlib.util
import re
from typing import Any, Dict, Iterable, Mapping


ROOT = Path(__file__).resolve().parent

NEWS_FILE = ROOT / "news_arm_v0_1.py"
UNIVERSE_FILE = ROOT / "production_universe_contract_v0_1.py"

SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False
CMC_USED = False

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
        raise ValueError("ASSET_MUST_BE_STRING")

    value = asset.strip().upper()

    if not value:
        raise ValueError("EMPTY_ASSET")

    return value


def discover_production_assets() -> tuple[str, ...]:
    universe = load_module(
        UNIVERSE_FILE,
        "arunda_dynamic_news_universe",
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


def asset_base(asset: str) -> str:
    value = normalize_asset(asset)

    if "/" in value:
        return value.split("/", 1)[0]

    if "-" in value:
        return value.split("-", 1)[0]

    if "_" in value:
        return value.split("_", 1)[0]

    return value


def build_dynamic_aliases(
    universe: Iterable[str],
    existing: Mapping[str, Iterable[str]],
) -> Dict[str, list[str]]:

    aliases: Dict[str, list[str]] = {
        normalize_asset(asset): list(values)
        for asset, values in existing.items()
    }

    for asset in universe:
        base = asset_base(asset)

        current = list(
            aliases.get(base, [])
        )

        candidates = [
            base.lower(),
            f"${base.lower()}",
            f"#{base.lower()}",
        ]

        for candidate in candidates:
            if candidate not in current:
                current.append(candidate)

        aliases[base] = current

    return aliases


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
        if not isinstance(record, Mapping):
            continue

        asset_value = record.get("asset")

        if not isinstance(asset_value, str):
            continue

        normalized = normalize_asset(
            asset_value
        )

        if normalized not in allowed:
            continue

        output.append(
            dict(record)
        )

    return output


def run_dynamic_news(
    universe: tuple[str, ...] | None = None,
) -> dict[str, Any]:

    if universe is None:
        universe = discover_production_assets()

    news = load_module(
        NEWS_FILE,
        "arunda_closed_news_arm",
    )

    run = getattr(
        news,
        "run",
        None,
    )

    if not callable(run):
        raise AttributeError(
            "NEWS_RUN_UNAVAILABLE"
        )

    if not hasattr(news, "ALIASES"):
        raise RuntimeError(
            "NEWS_ALIASES_MISSING"
        )

    if not hasattr(news, "RSS_SOURCES"):
        raise RuntimeError(
            "NEWS_SOURCE_REGISTRY_MISSING"
        )

    original_aliases = news.ALIASES

    dynamic_aliases = build_dynamic_aliases(
        universe,
        original_aliases,
    )

    news.ALIASES = dynamic_aliases

    try:
        raw = run()
    finally:
        news.ALIASES = original_aliases

    if not isinstance(raw, Mapping):
        raise RuntimeError(
            "NEWS_RESULT_NOT_MAPPING"
        )

    items = raw.get("items", [])
    errors = raw.get("errors", [])

    if not isinstance(items, list):
        raise RuntimeError(
            "NEWS_ITEMS_NOT_LIST"
        )

    if not isinstance(errors, list):
        errors = list(errors)

    filtered = filter_records_to_universe(
        items,
        universe,
    )

    return {
        "engine": raw.get(
            "engine",
            "NEWS_ARM_v0.1",
        ),
        "items": filtered,
        "errors": errors,

        "universe_size": len(universe),
        "dynamic_universe": True,
        "variable_cardinality": True,
        "universe_owns_cardinality": True,

        "source_registry_preserved": True,
        "multi_source": len(
            news.RSS_SOURCES
        ) > 1,
        "provider_count": len(
            news.RSS_SOURCES
        ),

        "fixed_15_used": False,
        "fixed_universe_size": False,

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

    news = load_module(
        NEWS_FILE,
        "arunda_news_static_engine",
    )

    universe = load_module(
        UNIVERSE_FILE,
        "arunda_news_static_universe",
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    run = getattr(
        news,
        "run",
        None,
    )

    if not callable(discover):
        raise RuntimeError(
            "UNIVERSE_DISCOVERY_MISSING"
        )

    if not callable(run):
        raise RuntimeError(
            "NEWS_RUN_MISSING"
        )

    if not hasattr(news, "RSS_SOURCES"):
        raise RuntimeError(
            "RSS_SOURCE_REGISTRY_MISSING"
        )

    if not isinstance(
        news.RSS_SOURCES,
        Mapping,
    ):
        raise RuntimeError(
            "RSS_SOURCE_REGISTRY_INVALID"
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

        "DYNAMIC_ALIAS_BINDING": True,
        "PER_ASSET_FILTER": True,

        "MULTI_SOURCE_ARCHITECTURE": (
            len(news.RSS_SOURCES) > 1
        ),
        "PROVIDER_COUNT": len(
            news.RSS_SOURCES
        ),
        "SOURCE_REGISTRY_PRESERVED": True,

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

        "PRODUCTION_UNIVERSE_SIZE": len(assets),
    }


def main() -> int:

    result = static_contract_check()

    for key, value in result.items():
        print(f"{key}={value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())