"""Authoritative production Risk Policy observation v0.1."""

from __future__ import annotations

from typing import Any

from smart_risk_policy_bridge_v0_1 import merge_validated_risk_policy

POLICY_VERSION = "RISK_POLICY_v0.1"
POLICY_SOURCE = "ARUNDA_PRODUCTION_RISK_POLICY"
POLICY_PROVENANCE = "AUTHORITATIVE_PRODUCTION_RISK_POLICY_V0_1"
RISK_PER_TRADE = 0.005
MAX_PORTFOLIO_RISK = 0.01
MAX_CONCURRENT_POSITIONS = 2


def build_production_risk_policy() -> dict[str, Any]:
    policy = {
        "policy_version": POLICY_VERSION,
        "policy_validation": "VALID",
        "risk_per_trade": RISK_PER_TRADE,
        "max_portfolio_risk": MAX_PORTFOLIO_RISK,
        "max_concurrent_positions": MAX_CONCURRENT_POSITIONS,
        "policy_source": POLICY_SOURCE,
        "policy_provenance": POLICY_PROVENANCE,
    }
    validated = merge_validated_risk_policy(policy)
    validated.update({"policy_source": POLICY_SOURCE, "policy_provenance": POLICY_PROVENANCE})
    return validated


__all__ = [
    "MAX_CONCURRENT_POSITIONS",
    "MAX_PORTFOLIO_RISK",
    "POLICY_PROVENANCE",
    "POLICY_SOURCE",
    "POLICY_VERSION",
    "RISK_PER_TRADE",
    "build_production_risk_policy",
]
