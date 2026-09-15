"""ARUNDA CP32 — pure RiskContext construction engine.

Observation-only boundary. No calculations, database access, execution,
position sizing, risk allocation, stop calculation, or strategy logic.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from risk_context_contract import RiskContext


NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_YET_AVAILABLE = "NOT_YET_AVAILABLE"


def _mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("observation source must be a mapping or None")
    return value


def _value(primary: Mapping[str, Any], secondary: Mapping[str, Any], key: str) -> Any:
    if key in primary:
        return primary[key]
    return secondary.get(key, None)


def build_risk_context(
    trade_ready_candidate: Mapping[str, Any],
    *,
    market_data: Mapping[str, Any] | None = None,
    market_analysis: Mapping[str, Any] | None = None,
    signal: Mapping[str, Any] | None = None,
    structure: Mapping[str, Any] | None = None,
    portfolio: Mapping[str, Any] | None = None,
    liquidity: Mapping[str, Any] | None = None,
    correlation: Mapping[str, Any] | None = None,
    trading_constraints: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> RiskContext:
    """Build an immutable RiskContext from existing observations only.

    Identity and direction are observed from the TradeReady candidate. Entry
    price is read only from an explicit ``entry_price`` field; ``price`` and
    ``latest_close`` are intentionally not accepted as fallbacks.
    """
    candidate = _mapping(trade_ready_candidate)
    md = _mapping(market_data)
    analysis = _mapping(market_analysis)
    sig = _mapping(signal)
    struct = _mapping(structure)
    port = _mapping(portfolio)
    liq = _mapping(liquidity)
    corr = _mapping(correlation)
    _mapping(trading_constraints)
    prov = _mapping(provenance)

    asset = candidate.get("asset", NOT_AVAILABLE)
    symbol = candidate.get("symbol", NOT_AVAILABLE)
    direction = candidate.get("direction", NOT_AVAILABLE)
    entry_price = candidate.get("entry_price")

    context = RiskContext(
        asset=asset,
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        trend_state=_value(analysis, sig, "trend_state"),
        momentum_state=_value(analysis, sig, "momentum_state"),
        acceleration=_value(analysis, sig, "acceleration"),
        position=_value(analysis, sig, "position"),
        volatility_regime=_value(analysis, md, "volatility_regime"),
        market_regime=_value(analysis, md, "market_regime"),
        structure_state=struct.get("structure_state"),
        structure_strength=struct.get("structure_strength"),
        signal_quality=sig.get("signal_quality"),
        confidence=sig.get("confidence"),
        liquidity_state=liq.get("liquidity_state"),
        correlation_context=(dict(corr) if corr else None),
        portfolio_exposure=port.get("portfolio_exposure"),
        portfolio_risk_state=port.get("portfolio_risk_state"),
        market_data_freshness=md.get("market_data_freshness"),
        provenance=(dict(prov) if prov else None),
        timestamp=_value(candidate, md, "timestamp"),
        snapshot_id=_value(candidate, md, "snapshot_id"),
    )
    context.validate()
    return context


__all__ = ["NOT_AVAILABLE", "NOT_YET_AVAILABLE", "build_risk_context"]
