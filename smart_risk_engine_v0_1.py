"""ARUNDA SMART RISK ENGINE v0.1.
Deterministic, side-effect-free risk budgeting and position sizing.
"""
from __future__ import annotations
from collections.abc import Mapping
from math import isfinite
from typing import Any
from smart_risk_contract_v0_1 import REAL_CAPITAL, SmartRiskDecision

EPSILON = 1e-12

def _positive(value: Any) -> float | None:
    if isinstance(value, bool): return None
    try: number = float(value)
    except (TypeError, ValueError): return None
    if not isfinite(number) or number <= EPSILON: return None
    return number

def _non_negative(value: Any) -> float | None:
    if isinstance(value, bool): return None
    try: number = float(value)
    except (TypeError, ValueError): return None
    if not isfinite(number) or number < 0: return None
    return number

def _blocked(asset: str, reason: str, policy_version: str | None = None) -> SmartRiskDecision:
    result = SmartRiskDecision(asset, None, None, None, None, None, None, None, None, None, "BLOCKED", reason, policy_version)
    result.validate(); return result

def build_smart_risk(observation: Mapping[str, Any], policy: Mapping[str, Any]) -> SmartRiskDecision:
    """Build a risk decision without side effects or inferred market data."""
    if not isinstance(observation, Mapping) or not isinstance(policy, Mapping): return _blocked("UNKNOWN", "INVALID_INPUT")
    asset = observation.get("asset")
    if not isinstance(asset, str) or not asset.strip(): return _blocked("UNKNOWN", "ASSET_NOT_EXPLICIT")
    policy_version = policy.get("policy_version")
    if not isinstance(policy_version, str) or not policy_version.strip(): return _blocked(asset, "RISK_POLICY_VERSION_MISSING")
    if policy.get("policy_validation") != "VALID": return _blocked(asset, "RISK_POLICY_UNVALIDATED", policy_version)
    if observation.get("capital_state") != REAL_CAPITAL: return _blocked(asset, "REAL_CAPITAL_NOT_AVAILABLE", policy_version)
    direction = observation.get("direction")
    if direction not in ("LONG", "SHORT"): return _blocked(asset, "DIRECTION_INVALID", policy_version)
    entry = _positive(observation.get("entry_price")); stop_distance = _positive(observation.get("stop_distance"))
    portfolio_capital = _positive(observation.get("portfolio_capital")); usable_capital = _positive(observation.get("usable_capital"))
    allocated_risk = _non_negative(observation.get("allocated_risk")); concurrent = observation.get("concurrent_positions")
    if entry is None: return _blocked(asset, "ENTRY_PRICE_NOT_EXPLICIT", policy_version)
    if stop_distance is None: return _blocked(asset, "STOP_DISTANCE_NOT_EXPLICIT", policy_version)
    if portfolio_capital is None: return _blocked(asset, "PORTFOLIO_CAPITAL_INVALID", policy_version)
    if usable_capital is None or usable_capital > portfolio_capital: return _blocked(asset, "USABLE_CAPITAL_INVALID", policy_version)
    if allocated_risk is None: return _blocked(asset, "ALLOCATED_RISK_INVALID", policy_version)
    if not isinstance(concurrent, int) or isinstance(concurrent, bool) or concurrent < 0: return _blocked(asset, "CONCURRENT_POSITIONS_INVALID", policy_version)
    risk_per_trade = _positive(policy.get("risk_per_trade")); max_portfolio_risk = _positive(policy.get("max_portfolio_risk")); max_concurrent = policy.get("max_concurrent_positions")
    if risk_per_trade is None or risk_per_trade > 1: return _blocked(asset, "RISK_PER_TRADE_POLICY_INVALID", policy_version)
    if max_portfolio_risk is None or max_portfolio_risk > 1: return _blocked(asset, "MAX_PORTFOLIO_RISK_POLICY_INVALID", policy_version)
    if not isinstance(max_concurrent, int) or isinstance(max_concurrent, bool) or max_concurrent < 1: return _blocked(asset, "MAX_CONCURRENT_POSITIONS_POLICY_INVALID", policy_version)
    if concurrent >= max_concurrent: return _blocked(asset, "MAX_CONCURRENT_POSITIONS_REACHED", policy_version)
    adjustment = 1.0
    for name in ("correlation_adjustment", "liquidity_adjustment", "execution_adjustment"):
        raw = observation.get(name)
        if raw is None: continue
        factor = _positive(raw)
        if factor is None or factor > 1: return _blocked(asset, f"{name.upper()}_INVALID", policy_version)
        adjustment *= factor
    portfolio_limit = portfolio_capital * max_portfolio_risk
    remaining = max(0.0, portfolio_limit - allocated_risk)
    risk_budget = min(portfolio_capital * risk_per_trade * adjustment, remaining)
    if risk_budget <= EPSILON: return _blocked(asset, "PORTFOLIO_RISK_CAPACITY_EXHAUSTED", policy_version)
    position_size = risk_budget / stop_distance; exposure = position_size * entry
    if not isfinite(position_size) or not isfinite(exposure) or position_size <= EPSILON or exposure <= EPSILON: return _blocked(asset, "RISK_CALCULATION_INVALID", policy_version)
    if exposure > usable_capital + EPSILON: return _blocked(asset, "USABLE_CAPITAL_EXCEEDED", policy_version)
    result = SmartRiskDecision(asset, direction, entry, stop_distance, risk_budget, position_size, exposure, remaining, concurrent, max_concurrent, "APPROVED", "RISK_POLICY_AND_CAPACITY_VALID", policy_version)
    result.validate(); return result

__all__ = ["build_smart_risk"]
