"""
ARUNDA PRODUCTION UNIVERSE BINDING / NORMALIZER v0.1

Converts the real CCXT market map returned by
load_public_markets(exchange) into canonical MarketRecord objects.

No network, database, persistence, cache, ranking, retry, or execution.
No dependency on EXPECTED_ASSETS.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class MarketRecord:
    asset: str
    symbol: str
    market_identity: str
    exchange: str
    base: str
    quote: str
    market_type: Optional[str]
    active: Optional[bool]
    tradable: Optional[bool]
    timestamp: Any
    source: str
    provenance: Mapping[str, Any]
    eligibility: bool


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _spot(market: Mapping[str, Any]) -> Optional[bool]:
    value = market.get("spot")
    if isinstance(value, bool):
        return value

    market_type = _text(market.get("type"))
    if market_type is None:
        return None

    return market_type.lower() == "spot"


def _tradable(market: Mapping[str, Any]) -> Optional[bool]:
    # Never infer tradability from active/spot.
    # Use only an explicitly provider-supplied status when present.
    status = market.get("status")

    if isinstance(status, bool):
        return status

    if isinstance(status, str):
        value = status.strip().lower()
        if value in {"online", "trading"}:
            return True
        if value in {"offline", "halted", "suspended", "closed", "disabled"}:
            return False

    return None


def _timestamp(market: Mapping[str, Any]) -> Any:
    # Preserve only an actual metadata timestamp. Never manufacture one.
    for key in ("timestamp", "lastUpdate", "updated", "updateTime"):
        if market.get(key) is not None:
            return market[key]
    return None


def normalize_market(
    market: Mapping[str, Any],
    *,
    exchange: str,
    source: str = "PUBLIC_MARKET_DATA_DISCOVERY",
) -> MarketRecord:
    """
    Normalize one real CCXT market object.

    Eligibility is proven only when:
      - exchange, id, symbol, base and quote are present
      - active is explicitly True
      - spot is explicitly True
      - asset can be directly established from normalized base

    Tradable is deliberately NOT required for eligibility because absence
    of provider-specific tradability evidence must remain UNKNOWN.
    """
    if not isinstance(market, Mapping):
        raise TypeError("MARKET_OBJECT_MUST_BE_MAPPING")

    exchange_value = _text(exchange)
    market_id = _text(market.get("id"))
    symbol = _text(market.get("symbol"))
    base = _text(market.get("base"))
    quote = _text(market.get("quote"))
    market_type = _text(market.get("type"))
    active = market.get("active")
    spot = _spot(market)
    tradable = _tradable(market)

    # CCXT's normalized base is the only non-invented asset identity
    # available in this contract. No hard-coded universe is consulted.
    asset = base

    identity = (
        f"{exchange_value}:{market_id}:{symbol}"
        if exchange_value and market_id and symbol
        else ""
    )

    eligibility = all(
        (
            exchange_value,
            market_id,
            symbol,
            base,
            quote,
            identity,
            active is True,
            spot is True,
        )
    )

    provenance = {
        "discovery_source": source,
        "exchange": exchange_value,
        "market_id": market_id,
        "provider_symbol": symbol,
    }

    return MarketRecord(
        asset=asset or "",
        symbol=symbol or "",
        market_identity=identity,
        exchange=exchange_value or "",
        base=base or "",
        quote=quote or "",
        market_type=market_type,
        active=active if isinstance(active, bool) else None,
        tradable=tradable,
        timestamp=_timestamp(market),
        source=source,
        provenance=provenance,
        eligibility=bool(eligibility),
    )


def build_production_universe(
    markets: Mapping[str, Mapping[str, Any]],
    *,
    exchange: str,
    source: str = "PUBLIC_MARKET_DATA_DISCOVERY",
) -> list[MarketRecord]:
    """
    Input:
        Exact market map returned by load_public_markets(exchange).

    Output:
        Dynamic list of canonical MarketRecord objects.

    No market is ranked, merged, substituted, or limited to a fixed asset
    list. Ineligible records are retained with eligibility=False.
    """
    if not isinstance(markets, Mapping):
        raise TypeError("MARKET_MAP_MUST_BE_MAPPING")

    return [
        normalize_market(
            market,
            exchange=exchange,
            source=source,
        )
        for market in markets.values()
    ]


def eligible_production_universe(
    markets: Mapping[str, Mapping[str, Any]],
    *,
    exchange: str,
    source: str = "PUBLIC_MARKET_DATA_DISCOVERY",
) -> list[MarketRecord]:
    """Return only markets whose active/spot eligibility is proven."""
    return [
        record
        for record in build_production_universe(
            markets,
            exchange=exchange,
            source=source,
        )
        if record.eligibility
    ]
