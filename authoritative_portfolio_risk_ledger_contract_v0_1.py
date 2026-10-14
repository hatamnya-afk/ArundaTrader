"""Versioned contract for authoritative account-wide portfolio risk ledger input.

This module validates an explicitly supplied ledger observation. It does not
discover positions, call an exchange, value balances, or calculate allocated
risk. Missing or symbol-scoped evidence remains BLOCKED.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED", "TOOBIT_FUTURES_POSITIONS_GET"}


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "portfolio_state": "BLOCKED",
        "portfolio_validation": "INVALID",
        "portfolio_block_reason": reason,
        "portfolio_source": None,
        "provenance": None,
        "asset_scope": None,
        "account_scope": None,
        "ledger_id": None,
        "ledger_version": None,
        "observed_at": None,
        "portfolio_capital": None,
        "usable_capital": None,
        "allocated_risk": None,
        "concurrent_positions": None,
    }


def _nonempty(row: Mapping[str, Any], field: str, reason: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _finite_number(value: Any, reason: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    number = float(value)
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(reason)
    return number


def build_authoritative_portfolio_risk_ledger_observation(
    ledger_observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate a real account-wide ledger observation; never infer missing fields."""
    if ledger_observation is None:
        return _blocked("AUTHORITATIVE_ACCOUNT_WIDE_PORTFOLIO_RISK_LEDGER_REQUIRED")
    if not isinstance(ledger_observation, Mapping):
        return _blocked("PORTFOLIO_LEDGER_INPUT_INVALID")

    try:
        if ledger_observation.get("ledger_state") != "AVAILABLE":
            raise ValueError("PORTFOLIO_LEDGER_STATE_INVALID")
        if ledger_observation.get("ledger_validation") != "VALID":
            raise ValueError("PORTFOLIO_LEDGER_VALIDATION_INVALID")
        if ledger_observation.get("coverage_scope") != "ACCOUNT_WIDE":
            raise ValueError("PORTFOLIO_LEDGER_ACCOUNT_WIDE_COVERAGE_REQUIRED")

        ledger_id = _nonempty(ledger_observation, "ledger_id", "PORTFOLIO_LEDGER_ID_MISSING")
        ledger_version = _nonempty(
            ledger_observation, "ledger_version", "PORTFOLIO_LEDGER_VERSION_MISSING"
        )
        source = _nonempty(ledger_observation, "ledger_source", "PORTFOLIO_LEDGER_SOURCE_MISSING")
        if source.upper() in _FORBIDDEN_SOURCES:
            raise ValueError("PORTFOLIO_LEDGER_SOURCE_INVALID")
        account_scope = _nonempty(
            ledger_observation, "account_scope", "PORTFOLIO_LEDGER_ACCOUNT_SCOPE_MISSING"
        )
        asset_scope = _nonempty(
            ledger_observation, "asset_scope", "PORTFOLIO_LEDGER_ASSET_SCOPE_MISSING"
        )
        observed_at = _nonempty(
            ledger_observation, "observed_at", "PORTFOLIO_LEDGER_TIMESTAMP_MISSING"
        )
        provenance = _nonempty(
            ledger_observation, "provenance", "PORTFOLIO_LEDGER_PROVENANCE_MISSING"
        )

        portfolio_capital = _finite_number(
            ledger_observation.get("portfolio_capital"),
            "PORTFOLIO_LEDGER_CAPITAL_INVALID",
            positive=True,
        )
        usable_capital = _finite_number(
            ledger_observation.get("usable_capital"),
            "PORTFOLIO_LEDGER_USABLE_CAPITAL_INVALID",
            positive=True,
        )
        if usable_capital > portfolio_capital:
            raise ValueError("PORTFOLIO_LEDGER_USABLE_CAPITAL_INVALID")
        allocated_risk = _finite_number(
            ledger_observation.get("allocated_risk"), "PORTFOLIO_LEDGER_ALLOCATED_RISK_INVALID"
        )
        concurrent_positions = ledger_observation.get("concurrent_positions")
        if (
            isinstance(concurrent_positions, bool)
            or not isinstance(concurrent_positions, int)
            or concurrent_positions < 0
        ):
            raise ValueError("PORTFOLIO_LEDGER_CONCURRENT_POSITIONS_INVALID")

        return {
            "portfolio_state": "AVAILABLE",
            "portfolio_validation": "VALID",
            "portfolio_source": source,
            "provenance": provenance,
            "asset_scope": asset_scope,
            "account_scope": account_scope,
            "ledger_id": ledger_id,
            "ledger_version": ledger_version,
            "coverage_scope": "ACCOUNT_WIDE",
            "observed_at": observed_at,
            "portfolio_capital": portfolio_capital,
            "usable_capital": usable_capital,
            "allocated_risk": allocated_risk,
            "concurrent_positions": concurrent_positions,
        }
    except (TypeError, ValueError) as exc:
        return _blocked(str(exc).strip() or "PORTFOLIO_LEDGER_INPUT_INVALID")


__all__ = ["build_authoritative_portfolio_risk_ledger_observation"]
