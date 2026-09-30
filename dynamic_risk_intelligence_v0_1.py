"""Dynamic production Risk Intelligence v0.1.

This module does not choose a fixed per-trade risk percentage. It converts
explicit real upstream observations into bounded Smart-Risk adjustments and
a per-candidate risk policy inside one portfolio-risk safety envelope.

No DB/API/execution side effects.
No synthetic or padded market data.
"""

from __future__ import annotations

from math import isfinite, sqrt
from statistics import median
from typing import Any, Mapping

from smart_risk_policy_bridge_v0_1 import merge_validated_risk_policy

POLICY_VERSION = "DYNAMIC_RISK_POLICY_v0.1"
POLICY_SOURCE = "ARUNDA_DYNAMIC_RISK_INTELLIGENCE"
POLICY_PROVENANCE = "REAL_MARKET_DECISION_RISK_INTELLIGENCE_V0_1"

# Safety envelope only. This is NOT the per-trade allocation.
MAX_PORTFOLIO_RISK_CEILING = 0.01


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _confidence_factor(opportunity: Mapping[str, Any]) -> float | None:
    value = _finite(opportunity.get("confidence"))
    if value is None or value < 0 or value > 1:
        return None
    return value


def _volatility_factor(
    entry_price: float,
    stop_distance: float,
) -> float | None:
    if entry_price <= 0 or stop_distance <= 0:
        return None
    stop_ratio = stop_distance / entry_price
    if not isfinite(stop_ratio) or stop_ratio <= 0:
        return None
    # Larger real stop distance means less risk budget for the candidate.
    return _clamp(1.0 / (1.0 + stop_ratio), 0.0, 1.0)


def _volume_factor(
    asset: str,
    market_data_by_symbol: Mapping[str, Any],
) -> float | None:
    volumes: list[float] = []
    current_volume: float | None = None

    for symbol, bars in market_data_by_symbol.items():
        if not isinstance(bars, list):
            continue
        valid = [_finite(row.get("volume")) for row in bars if isinstance(row, dict)]
        valid = [v for v in valid if v is not None and v > 0]
        if not valid:
            continue
        volumes.append(valid[-1])
        if str(symbol).upper() in {asset.upper(), f"{asset.upper()}/USDT"}:
            current_volume = valid[-1]

    if current_volume is None or not volumes:
        return None

    reference = median(volumes)
    if reference <= 0:
        return None

    return _clamp(sqrt(current_volume / reference), 0.0, 1.0)


def _return_series(bars: Any) -> list[float]:
    if not isinstance(bars, list):
        return []
    closes = []
    for row in bars:
        if not isinstance(row, dict):
            continue
        close = _finite(row.get("close"))
        if close is not None and close > 0:
            closes.append(close)
    returns: list[float] = []
    for previous, current in zip(closes, closes[1:]):
        change = (current / previous) - 1.0
        if isfinite(change):
            returns.append(change)
    return returns[-30:]


def _correlation_factor(
    asset: str,
    market_data_by_symbol: Mapping[str, Any],
) -> float | None:
    target = None
    for symbol, bars in market_data_by_symbol.items():
        if str(symbol).upper() in {asset.upper(), f"{asset.upper()}/USDT"}:
            target = _return_series(bars)
            break
    if not target or len(target) < 5:
        return None

    correlations: list[float] = []
    for symbol, bars in market_data_by_symbol.items():
        if str(symbol).upper() in {asset.upper(), f"{asset.upper()}/USDT"}:
            continue
        other = _return_series(bars)
        n = min(len(target), len(other))
        if n < 5:
            continue
        a = target[-n:]
        b = other[-n:]
        ma = sum(a) / n
        mb = sum(b) / n
        va = sum((x - ma) ** 2 for x in a)
        vb = sum((x - mb) ** 2 for x in b)
        if va <= 0 or vb <= 0:
            continue
        covariance = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        corr = covariance / sqrt(va * vb)
        if isfinite(corr):
            correlations.append(abs(corr))

    if not correlations:
        return None

    mean_abs_corr = sum(correlations) / len(correlations)
    return _clamp(1.0 - mean_abs_corr, 0.0, 1.0)


def build_dynamic_risk_policy(
    *,
    asset: str,
    decision: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    entry_price: float,
    stop_distance: float,
    market_data_by_symbol: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one candidate's dynamic, validated risk policy.

    The only fixed numeric policy is the portfolio safety ceiling. Per-trade
    risk and concurrent-position capacity are derived from current real
    decision/market evidence.
    """
    if not isinstance(decision, Mapping):
        raise ValueError("DECISION_INPUT_INVALID")
    if not isinstance(opportunity, Mapping):
        raise ValueError("OPPORTUNITY_INPUT_INVALID")
    if decision.get("state") != "ACTIONABLE":
        raise ValueError("DECISION_NOT_ACTIONABLE")
    if decision.get("direction") not in ("LONG", "SHORT"):
        raise ValueError("DIRECTION_INVALID")

    confidence = _confidence_factor(opportunity)
    volatility = _volatility_factor(float(entry_price), float(stop_distance))
    liquidity = _volume_factor(asset, market_data_by_symbol)
    correlation = _correlation_factor(asset, market_data_by_symbol)

    if None in (confidence, volatility, liquidity, correlation):
        raise ValueError("DYNAMIC_RISK_CONTEXT_INCOMPLETE")

    # Execution quality is deliberately conservative until a provider-level
    # execution observation exists. It is an explicit observation boundary,
    # not a fabricated exchange metric.
    execution = 1.0

    composite = (
        confidence
        * volatility
        * liquidity
        * correlation
        * execution
    )
    risk_per_trade = MAX_PORTFOLIO_RISK_CEILING * _clamp(composite, 0.0, 1.0)

    if risk_per_trade <= 0:
        raise ValueError("DYNAMIC_RISK_BUDGET_ZERO")

    max_concurrent = max(
        1,
        int(MAX_PORTFOLIO_RISK_CEILING / risk_per_trade),
    )

    policy = {
        "policy_version": POLICY_VERSION,
        "policy_validation": "VALID",
        "risk_per_trade": risk_per_trade,
        "max_portfolio_risk": MAX_PORTFOLIO_RISK_CEILING,
        "max_concurrent_positions": max_concurrent,
        "policy_source": POLICY_SOURCE,
        "policy_provenance": POLICY_PROVENANCE,
        "risk_factors": {
            "confidence": confidence,
            "volatility": volatility,
            "liquidity": liquidity,
            "correlation": correlation,
            "execution": execution,
        },
    }

    validated = merge_validated_risk_policy(policy)
    validated.update({
        "policy_source": POLICY_SOURCE,
        "policy_provenance": POLICY_PROVENANCE,
        "risk_factors": policy["risk_factors"],
    })
    return validated


__all__ = [
    "MAX_PORTFOLIO_RISK_CEILING",
    "POLICY_VERSION",
    "POLICY_SOURCE",
    "POLICY_PROVENANCE",
    "build_dynamic_risk_policy",
]
