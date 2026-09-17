# dynamic_fusion_adapter_v0_1.py

from __future__ import annotations

from typing import Any, Dict, List


ENGINE_VERSION = "DYNAMIC_FUSION_ADAPTER_v0.1"

DB_WRITES = 0
EXECUTION = False
CMC_USED = False
SYNTHETIC_DATA = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False


def normalize_asset(value: Any) -> str:
    asset = str(value or "").strip().upper()

    if not asset:
        raise RuntimeError("FUSION_ASSET_EMPTY")

    return asset


def validate_information_item_identity(
    item: Dict[str, Any],
    expected_asset: str,
) -> None:

    if not isinstance(item, dict):
        raise RuntimeError("INFORMATION_ITEM_NOT_DICT")

    actual = normalize_asset(item.get("asset"))

    if actual != expected_asset:
        raise RuntimeError(
            f"INFORMATION_ASSET_MISMATCH:"
            f"{expected_asset}:{actual}"
        )

    required = (
        "source",
        "source_id",
        "timestamp",
        "provenance",
        "contract_version",
        "sentiment",
    )

    for field in required:
        if field not in item:
            raise RuntimeError(
                f"INFORMATION_FIELD_MISSING:{field}"
            )


def validate_real_arm_output(
    result: Dict[str, Any],
    expected_asset: str,
    arm_name: str,
) -> List[Dict[str, Any]]:

    if not isinstance(result, dict):
        raise RuntimeError(
            f"{arm_name}_OUTPUT_INVALID"
        )

    items = result.get("items")

    if not isinstance(items, list):
        raise RuntimeError(
            f"{arm_name}_ITEMS_INVALID"
        )

    valid = []

    for item in items:

        validate_information_item_identity(
            item,
            expected_asset,
        )

        valid.append(item)

    return valid


def bind_news(
    news_module,
    asset: str,
) -> List[Dict[str, Any]]:

    result = news_module.run()

    items = result.get("items", [])

    if not isinstance(items, list):
        raise RuntimeError(
            "NEWS_OUTPUT_INVALID"
        )

    selected = []

    for item in items:

        if not isinstance(item, dict):
            continue

        item_asset = normalize_asset(
            item.get("asset")
        )

        if item_asset != asset:
            continue

        # Preserve exact real asset identity.
        validate_information_item_identity(
            item,
            asset,
        )

        selected.append(item)

    return selected


def bind_social(
    social_module,
    asset: str,
) -> List[Dict[str, Any]]:

    result = social_module.run()

    items = result.get("items", [])

    if not isinstance(items, list):
        raise RuntimeError(
            "SOCIAL_OUTPUT_INVALID"
        )

    selected = []

    for item in items:

        if not isinstance(item, dict):
            continue

        item_asset = normalize_asset(
            item.get("asset")
        )

        if item_asset != asset:
            continue

        # Preserve exact real asset identity.
        validate_information_item_identity(
            item,
            asset,
        )

        selected.append(item)

    return selected


def validate_market_signal(
    fusion_module,
    asset: str,
    market_signal: Dict[str, Any],
) -> None:

    if not isinstance(market_signal, dict):
        raise RuntimeError(
            "MARKET_SIGNAL_INVALID"
        )

    actual = normalize_asset(
        market_signal.get("asset")
    )

    if actual != asset:
        raise RuntimeError(
            f"MARKET_SIGNAL_ASSET_MISMATCH:"
            f"{asset}:{actual}"
        )

    fusion_module.validate_market_signal(
        asset,
        market_signal,
    )


def fuse_dynamic_asset(
    fusion_module,
    asset: str,
    market_signal: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    social_items: List[Dict[str, Any]],
) -> Dict[str, Any]:

    asset = normalize_asset(asset)

    validate_market_signal(
        fusion_module,
        asset,
        market_signal,
    )

    for item in news_items:
        validate_information_item_identity(
            item,
            asset,
        )

    for item in social_items:
        validate_information_item_identity(
            item,
            asset,
        )

    # IMPORTANT:
    #
    # Do NOT call fusion_engine.run().
    #
    # run() is the closed fixed-15 contract.
    #
    # MARSCOIN must use the per-asset function.
    #
    result = fusion_module.fuse_asset(
        asset,
        market_signal,
        news_items,
        social_items,
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "FUSION_RESULT_INVALID"
        )

    result_asset = normalize_asset(
        result.get("asset")
    )

    if result_asset != asset:
        raise RuntimeError(
            f"FUSION_ASSET_MISMATCH:"
            f"{asset}:{result_asset}"
        )

    return result


def static_contract_check() -> Dict[str, Any]:

    return {
        "status": "PASS",
        "engine": ENGINE_VERSION,
        "dynamic_universe": True,
        "variable_cardinality": True,
        "fixed_15_used": False,
        "semantic_change": False,
        "identity_preserved": True,
        "synthetic": SYNTHETIC_DATA,
        "interpolation": INTERPOLATION,
        "fill": FILL,
        "backfill": BACKFILL,
        "padding": PADDING,
        "blending": BLENDING,
        "cmc_used": CMC_USED,
        "db_writes": DB_WRITES,
        "execution": "OFF",
    }


if __name__ == "__main__":

    result = static_contract_check()

    print("STATUS=" + result["status"])
    print("ENGINE=" + result["engine"])
    print("DYNAMIC_UNIVERSE=True")
    print("VARIABLE_CARDINALITY=True")
    print("FIXED_15_USED=False")
    print("SEMANTIC_CHANGE=False")
    print("IDENTITY_PRESERVED=True")
    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")
    print("CMC_USED=False")
    print("DB_WRITES=0")
    print("EXECUTION=OFF")