
from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


# ============================================================
# ARUNDA PRODUCTION UNIVERSE CONTRACT v0.1
# ============================================================
#
# SINGLE PRODUCTION UNIVERSE BOUNDARY
#
# Production Universe:
#   - REAL
#   - DYNAMIC
#   - sourced from existing production Universe discovery
#   - ACTIVE SPOT USDT markets
#
# IMPORTANT:
#   production_universe_binding.py exposes:
#
#       asset  = BASE
#       base   = BASE
#       quote  = QUOTE
#       symbol = BASE/QUOTE
#
# Non-USDT markets are valid upstream records but are outside
# the Production USDT Universe and are therefore filtered.
#
# Duplicate handling:
#
#   IDENTICAL canonical market identities
#       -> safely canonicalized once
#
#   SAME canonical market with conflicting identity fields
#       -> FAIL CLOSED
#
# NO:
#   - fixed 15
#   - hard-coded production asset list
#   - synthetic data
#   - interpolation
#   - fill
#   - backfill
#   - padding
#   - blending
#   - CMC
#   - DB writes
#   - execution
# ============================================================


ROOT = Path(__file__).resolve().parent

PRODUCTION_SIGNAL_INPUT = (
    ROOT / "production_signal_input_boundary_v0_1.py"
)

PRODUCTION_UNIVERSE_BINDING = (
    ROOT / "production_universe_binding.py"
)

DYNAMIC_UNIVERSE = True
FIXED_15_USED = False

DB_WRITES = 0
EXECUTION = False

CMC_USED = False
SYNTHETIC_DATA = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False


# ============================================================
# MODULE LOADER
# ============================================================

def _load_module(
    path: Path,
    name: str,
):
    if not path.is_file():
        raise RuntimeError(
            f"MODULE_FILE_NOT_FOUND:{path.name}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
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
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous

        raise

    return module


# ============================================================
# RECORD ACCESS
# ============================================================

def _record_value(
    record: Any,
    field: str,
) -> Any:

    if isinstance(record, Mapping):
        return record.get(field)

    return getattr(
        record,
        field,
        None,
    )


# ============================================================
# MARKET RECORD DETECTION
# ============================================================

def _is_market_record(
    value: Any,
) -> bool:

    required = (
        "asset",
        "symbol",
        "market_identity",
        "exchange",
        "base",
        "quote",
        "eligibility",
    )

    if isinstance(value, Mapping):
        return all(
            key in value
            for key in required
        )

    return all(
        hasattr(value, key)
        for key in required
    )


# ============================================================
# CANONICAL MARKET
# ============================================================

def _canonical_market(
    base: Any,
    quote: Any,
) -> str:

    if not isinstance(base, str):
        raise RuntimeError(
            "UNIVERSE_BASE_INVALID"
        )

    if not isinstance(quote, str):
        raise RuntimeError(
            "UNIVERSE_QUOTE_INVALID"
        )

    normalized_base = base.strip().upper()
    normalized_quote = quote.strip().upper()

    if not normalized_base:
        raise RuntimeError(
            "UNIVERSE_EMPTY_BASE"
        )

    if not normalized_quote:
        raise RuntimeError(
            "UNIVERSE_EMPTY_QUOTE"
        )

    if "/" in normalized_base:
        raise RuntimeError(
            f"UNIVERSE_BASE_INVALID:{base}"
        )

    if "-" in normalized_base:
        raise RuntimeError(
            f"UNIVERSE_BASE_INVALID:{base}"
        )

    if normalized_quote != "USDT":
        raise RuntimeError(
            f"UNIVERSE_NON_USDT_ASSET:"
            f"{normalized_base}/{normalized_quote}"
        )

    return (
        f"{normalized_base}/{normalized_quote}"
    )


# ============================================================
# MARKET RECORD VALIDATION
# ============================================================

def _validate_market_record(
    record: Any,
) -> str | None:
    """
    Validate one real MarketRecord.

    Returns:
        canonical BASE/USDT
            for a valid Production market.

        None
            for a valid upstream non-USDT/ineligible market.
    """

    if not _is_market_record(record):
        raise RuntimeError(
            "UNIVERSE_INVALID_RECORD_TYPE"
        )

    asset = _record_value(
        record,
        "asset",
    )

    symbol = _record_value(
        record,
        "symbol",
    )

    market_identity = _record_value(
        record,
        "market_identity",
    )

    exchange = _record_value(
        record,
        "exchange",
    )

    base = _record_value(
        record,
        "base",
    )

    quote = _record_value(
        record,
        "quote",
    )

    eligibility = _record_value(
        record,
        "eligibility",
    )

    # --------------------------------------------------------
    # Ineligible upstream record.
    # --------------------------------------------------------

    if eligibility is not True:
        return None

    # --------------------------------------------------------
    # Required fields.
    # --------------------------------------------------------

    if not isinstance(asset, str) or not asset.strip():
        raise RuntimeError(
            "UNIVERSE_RECORD_WITHOUT_ASSET"
        )

    if not isinstance(symbol, str) or not symbol.strip():
        raise RuntimeError(
            "UNIVERSE_RECORD_WITHOUT_SYMBOL"
        )

    if not isinstance(
        market_identity,
        str,
    ) or not market_identity.strip():

        raise RuntimeError(
            "UNIVERSE_RECORD_WITHOUT_MARKET_IDENTITY"
        )

    if not isinstance(exchange, str) or not exchange.strip():
        raise RuntimeError(
            "UNIVERSE_RECORD_WITHOUT_EXCHANGE"
        )

    if not isinstance(base, str) or not base.strip():
        raise RuntimeError(
            "UNIVERSE_RECORD_WITHOUT_BASE"
        )

    if not isinstance(quote, str) or not quote.strip():
        raise RuntimeError(
            "UNIVERSE_RECORD_WITHOUT_QUOTE"
        )

    normalized_asset = asset.strip().upper()
    normalized_base = base.strip().upper()
    normalized_quote = quote.strip().upper()

    normalized_symbol = (
        symbol
        .strip()
        .upper()
        .replace("-", "/")
    )

    normalized_market_identity = (
        market_identity
        .strip()
        .upper()
    )

    # --------------------------------------------------------
    # Non-USDT markets are outside Production Universe.
    # --------------------------------------------------------

    if normalized_quote != "USDT":
        return None

    # --------------------------------------------------------
    # asset semantics:
    #
    # asset == base
    # --------------------------------------------------------

    if "/" in normalized_asset:
        raise RuntimeError(
            f"UNIVERSE_ASSET_IS_NOT_BASE:{asset}"
        )

    if "-" in normalized_asset:
        raise RuntimeError(
            f"UNIVERSE_ASSET_IS_NOT_BASE:{asset}"
        )

    if normalized_asset != normalized_base:
        raise RuntimeError(
            f"UNIVERSE_ASSET_BASE_MISMATCH:"
            f"{asset}:{base}"
        )

    # --------------------------------------------------------
    # Canonical market.
    # --------------------------------------------------------

    canonical_market = _canonical_market(
        normalized_base,
        normalized_quote,
    )

    # --------------------------------------------------------
    # Provider symbol must identify the same market.
    # --------------------------------------------------------

    if normalized_symbol != canonical_market:
        raise RuntimeError(
            f"UNIVERSE_SYMBOL_MISMATCH:"
            f"{symbol}:{canonical_market}"
        )

    # --------------------------------------------------------
    # Existing market identity must contain canonical market.
    # --------------------------------------------------------

    if canonical_market not in normalized_market_identity:
        raise RuntimeError(
            f"UNIVERSE_MARKET_IDENTITY_MISMATCH:"
            f"{market_identity}:{canonical_market}"
        )

    return canonical_market


# ============================================================
# DISCOVERY OUTPUT
# ============================================================

def _collect_market_records(
    value: Any,
) -> list[Any]:

    collected: list[Any] = []

    def walk(
        node: Any,
    ) -> None:

        if node is None:
            return

        if _is_market_record(node):
            collected.append(node)
            return

        if isinstance(
            node,
            Mapping,
        ):

            for child in node.values():
                walk(child)

            return

        if isinstance(
            node,
            (str, bytes),
        ):
            return

        if isinstance(
            node,
            Iterable,
        ):

            for child in node:
                walk(child)

            return

    walk(value)

    if not collected:
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_NO_MARKET_RECORDS"
        )

    return collected


# ============================================================
# DUPLICATE CONSISTENCY
# ============================================================

def _duplicate_identity_is_consistent(
    previous: Any,
    current: Any,
) -> bool:
    """
    Two records with the same canonical market may safely
    collapse ONLY when their core identity agrees.

    This prevents accidental merging of different provider
    markets under one canonical asset.
    """

    fields = (
        "asset",
        "symbol",
        "market_identity",
        "exchange",
        "base",
        "quote",
    )

    for field in fields:

        left = _record_value(
            previous,
            field,
        )

        right = _record_value(
            current,
            field,
        )

        if str(left).strip().upper() != str(right).strip().upper():
            return False

    return True


# ============================================================
# PRODUCTION UNIVERSE DISCOVERY
# ============================================================

def discover_production_assets() -> tuple[str, ...]:
    """
    Discover CURRENT dynamic Production Universe.

    Source:

        production_signal_input_boundary_v0_1.py
                    +
        production_universe_binding.py

    The result is canonical BASE/USDT market identity.

    Identical duplicate records are canonicalized once.
    Conflicting duplicate identities fail closed.
    """

    signal_module = _load_module(
        PRODUCTION_SIGNAL_INPUT,
        "production_signal_input_boundary_v01",
    )

    discover = getattr(
        signal_module,
        "discover_production_universe",
        None,
    )

    if not callable(discover):
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_DISCOVERY_MISSING"
        )

    universe_binding = _load_module(
        PRODUCTION_UNIVERSE_BINDING,
        "production_universe_binding_v01",
    )

    discovered = discover(
        universe_binding
    )

    records = _collect_market_records(
        discovered
    )

    assets: list[str] = []

    # Canonical market -> first authoritative record.
    seen_records: dict[str, Any] = {}

    # --------------------------------------------------------
    # Process all discovered records.
    # --------------------------------------------------------

    for record in records:

        market = _validate_market_record(
            record
        )

        # Non-USDT or ineligible.
        if market is None:
            continue

        # ----------------------------------------------------
        # First occurrence.
        # ----------------------------------------------------

        if market not in seen_records:

            seen_records[market] = record
            assets.append(market)
            continue

        # ----------------------------------------------------
        # Duplicate occurrence.
        #
        # Same exact identity:
        #     safely collapse.
        #
        # Conflicting identity:
        #     fail closed.
        # ----------------------------------------------------

        previous = seen_records[market]

        if not _duplicate_identity_is_consistent(
            previous,
            record,
        ):

            raise RuntimeError(
                f"UNIVERSE_CONFLICTING_DUPLICATE:"
                f"{market}"
            )

        # Identical duplicate is intentionally ignored.
        continue

    if not assets:
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_EMPTY"
        )

    return tuple(assets)


# ============================================================
# DYNAMIC UNIVERSE VALIDATOR
# ============================================================

def validate_dynamic_universe(
    assets: Iterable[str],
) -> tuple[str, ...]:

    if assets is None:
        raise RuntimeError(
            "UNIVERSE_NONE"
        )

    if isinstance(
        assets,
        (str, bytes, Mapping),
    ):
        raise RuntimeError(
            "UNIVERSE_INVALID_CONTAINER"
        )

    normalized: list[str] = []
    seen: set[str] = set()

    for value in assets:

        if not isinstance(
            value,
            str,
        ):
            raise RuntimeError(
                "UNIVERSE_ASSET_NOT_STRING"
            )

        text = value.strip().upper().replace(
            "-",
            "/",
        )

        if not text:
            raise RuntimeError(
                "UNIVERSE_EMPTY_ASSET"
            )

        if "/" not in text:
            raise RuntimeError(
                f"UNIVERSE_ASSET_NOT_MARKET:{value}"
            )

        parts = text.split("/")

        if len(parts) != 2:
            raise RuntimeError(
                f"UNIVERSE_INVALID_MARKET:{value}"
            )

        base = parts[0].strip()
        quote = parts[1].strip()

        if not base or not quote:
            raise RuntimeError(
                f"UNIVERSE_INVALID_MARKET:{value}"
            )

        market = _canonical_market(
            base,
            quote,
        )

        if market in seen:
            raise RuntimeError(
                f"UNIVERSE_DUPLICATE_ASSET:{market}"
            )

        seen.add(market)
        normalized.append(market)

    if not normalized:
        raise RuntimeError(
            "UNIVERSE_EMPTY"
        )

    return tuple(normalized)


# ============================================================
# ASSET SET
# ============================================================

def asset_set(
    assets: Iterable[str],
) -> set[str]:

    return set(
        validate_dynamic_universe(
            assets
        )
    )


# ============================================================
# ASSET MEMBERSHIP
# ============================================================

def contains_asset(
    assets: Iterable[str],
    asset: str,
) -> bool:

    if not isinstance(
        asset,
        str,
    ):
        raise RuntimeError(
            "UNIVERSE_ASSET_NOT_STRING"
        )

    text = asset.strip().upper().replace(
        "-",
        "/",
    )

    canonical = validate_dynamic_universe(
        [text]
    )[0]

    return canonical in asset_set(
        assets
    )


# ============================================================
# CONTRACT CHECK
# ============================================================

def contract_check() -> dict:

    assets = discover_production_assets()

    validated = validate_dynamic_universe(
        assets
    )

    return {
        "status": "PASS",
        "dynamic_universe": True,
        "fixed_15_used": False,
        "asset_count": len(validated),
        "assets": validated,
        "duplicate_assets": False,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
        "cmc_used": False,
        "db_writes": 0,
        "execution": "OFF",
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        result = contract_check()

        print(
            "STATUS="
            + result["status"]
        )

        print(
            "DYNAMIC_UNIVERSE=True"
        )

        print(
            "FIXED_15_USED=False"
        )

        print(
            "PRODUCTION_UNIVERSE_SIZE="
            + str(
                result["asset_count"]
            )
        )

        print(
            "DUPLICATE_ASSETS=False"
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

        print(
            "CMC_USED=False"
        )

        print(
            "DB_WRITES=0"
        )

        print(
            "EXECUTION=OFF"
        )

        print(
            "SAMPLE_ASSETS="
            + ",".join(
                result["assets"][:10]
            )
        )

    except Exception as exc:

        print(
            "STATUS=FAIL_CLOSED"
        )

        print(
            "ERROR="
            + type(exc).__name__
            + ":"
            + str(exc)
        )

        raise