"""Versioned contract for authoritative Spot + Futures portfolio risk input.

Validates explicit account-wide evidence. It does not discover positions, call
an exchange, value raw balances, or calculate allocated risk. Both USDT and
USDC holdings require explicit, versioned valuation evidence into a common
USDT reporting unit. Missing evidence remains BLOCKED.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from approved_valuation_policy_source_contract_v0_1 import (
    validate_approved_valuation_policy_evidence,
)
from all_asset_valuation_contract_v0_1 import validate_all_asset_valuation_evidence


_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED", "TOOBIT_FUTURES_POSITIONS_GET"}
_REQUIRED_MARKETS = {"SPOT", "FUTURES"}
_REQUIRED_CURRENCIES = {"USDT", "USDC"}


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
        "cycle_id": None,
        "market_coverage": None,
        "spot_observed_at": None,
        "futures_observed_at": None,
        "valuation_policy_id": None,
        "valuation_policy_version": None,
        "reporting_currency": None,
        "currency_valuation_evidence": None,
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


def _validate_currency_evidence(
    evidence: Any, *, policy_id: str, policy_version: str, cycle_id: str,
    approved_rate_sources: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, Any]]:
    if not isinstance(evidence, Mapping) or {str(k).upper() for k in evidence} != _REQUIRED_CURRENCIES:
        raise ValueError("PORTFOLIO_LEDGER_USDT_USDC_VALUATION_EVIDENCE_REQUIRED")

    normalized: dict[str, dict[str, Any]] = {}
    for raw_currency, row in evidence.items():
        currency = str(raw_currency).upper()
        if not isinstance(row, Mapping):
            raise ValueError("PORTFOLIO_LEDGER_CURRENCY_VALUATION_INVALID")
        amount = _finite_number(row.get("raw_amount"), "PORTFOLIO_LEDGER_CURRENCY_AMOUNT_INVALID")
        rate = _finite_number(row.get("rate_to_usdt"), "PORTFOLIO_LEDGER_CURRENCY_RATE_INVALID", positive=True)
        rate_source = _nonempty(row, "rate_source", "PORTFOLIO_LEDGER_CURRENCY_RATE_SOURCE_MISSING")
        if rate_source.upper() in _FORBIDDEN_SOURCES:
            raise ValueError("PORTFOLIO_LEDGER_CURRENCY_RATE_SOURCE_INVALID")
        if rate_source != approved_rate_sources[currency]["source"]:
            raise ValueError("PORTFOLIO_LEDGER_CURRENCY_RATE_SOURCE_NOT_APPROVED")
        rate_timestamp = _nonempty(
            row, "rate_observed_at", "PORTFOLIO_LEDGER_CURRENCY_RATE_TIMESTAMP_MISSING"
        )
        row_policy_id = _nonempty(
            row, "valuation_policy_id", "PORTFOLIO_LEDGER_CURRENCY_POLICY_ID_MISSING"
        )
        row_policy_version = _nonempty(
            row, "valuation_policy_version", "PORTFOLIO_LEDGER_CURRENCY_POLICY_VERSION_MISSING"
        )
        row_cycle = _nonempty(row, "cycle_id", "PORTFOLIO_LEDGER_CURRENCY_CYCLE_ID_MISSING")
        if row_policy_id != policy_id or row_policy_version != policy_version:
            raise ValueError("PORTFOLIO_LEDGER_CURRENCY_POLICY_MISMATCH")
        if row_cycle != cycle_id:
            raise ValueError("PORTFOLIO_LEDGER_CURRENCY_CYCLE_MISMATCH")
        if currency == "USDT" and rate != 1.0:
            raise ValueError("PORTFOLIO_LEDGER_USDT_BASE_RATE_MUST_EQUAL_ONE")
        normalized[currency] = {
            "raw_amount": amount,
            "rate_to_usdt": rate,
            "rate_source": rate_source,
            "rate_observed_at": rate_timestamp,
            "valuation_policy_id": row_policy_id,
            "valuation_policy_version": row_policy_version,
            "cycle_id": row_cycle,
        }
    return normalized


def build_authoritative_portfolio_risk_ledger_observation(
    ledger_observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate explicit dual-market, dual-currency account-wide evidence."""
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

        coverage = ledger_observation.get("market_coverage")
        if (
            not isinstance(coverage, (list, tuple, set, frozenset))
            or any(not isinstance(item, str) for item in coverage)
            or {item.strip().upper() for item in coverage} != _REQUIRED_MARKETS
        ):
            raise ValueError("PORTFOLIO_LEDGER_SPOT_AND_FUTURES_COVERAGE_REQUIRED")

        ledger_id = _nonempty(ledger_observation, "ledger_id", "PORTFOLIO_LEDGER_ID_MISSING")
        ledger_version = _nonempty(ledger_observation, "ledger_version", "PORTFOLIO_LEDGER_VERSION_MISSING")
        source = _nonempty(ledger_observation, "ledger_source", "PORTFOLIO_LEDGER_SOURCE_MISSING")
        if source.upper() in _FORBIDDEN_SOURCES:
            raise ValueError("PORTFOLIO_LEDGER_SOURCE_INVALID")
        account_scope = _nonempty(ledger_observation, "account_scope", "PORTFOLIO_LEDGER_ACCOUNT_SCOPE_MISSING")
        asset_scope = _nonempty(ledger_observation, "asset_scope", "PORTFOLIO_LEDGER_ASSET_SCOPE_MISSING")
        observed_at = _nonempty(ledger_observation, "observed_at", "PORTFOLIO_LEDGER_TIMESTAMP_MISSING")
        cycle_id = _nonempty(ledger_observation, "cycle_id", "PORTFOLIO_LEDGER_CYCLE_ID_MISSING")
        spot_observed_at = _nonempty(ledger_observation, "spot_observed_at", "PORTFOLIO_LEDGER_SPOT_TIMESTAMP_MISSING")
        futures_observed_at = _nonempty(ledger_observation, "futures_observed_at", "PORTFOLIO_LEDGER_FUTURES_TIMESTAMP_MISSING")
        provenance = _nonempty(ledger_observation, "provenance", "PORTFOLIO_LEDGER_PROVENANCE_MISSING")

        if ledger_observation.get("valuation_policy_state") != "APPROVED":
            raise ValueError("PORTFOLIO_LEDGER_APPROVED_VALUATION_POLICY_REQUIRED")
        valuation_policy_id = _nonempty(ledger_observation, "valuation_policy_id", "PORTFOLIO_LEDGER_VALUATION_POLICY_ID_MISSING")
        valuation_policy_version = _nonempty(
            ledger_observation, "valuation_policy_version", "PORTFOLIO_LEDGER_VALUATION_POLICY_VERSION_MISSING"
        )
        reporting_currency = ledger_observation.get("reporting_currency")
        if reporting_currency != "USDT":
            raise ValueError("PORTFOLIO_LEDGER_REPORTING_CURRENCY_MUST_BE_USDT")
        policy_evidence = validate_approved_valuation_policy_evidence(
            ledger_observation.get("valuation_policy_evidence"),
            valuation_observed_at=observed_at,
        )
        if (
            policy_evidence["policy_id"] != valuation_policy_id
            or policy_evidence["policy_version"] != valuation_policy_version
        ):
            raise ValueError("PORTFOLIO_LEDGER_VALUATION_POLICY_EVIDENCE_MISMATCH")
        currency_evidence = _validate_currency_evidence(
            ledger_observation.get("currency_valuation_evidence"),
            policy_id=valuation_policy_id,
            policy_version=valuation_policy_version,
            cycle_id=cycle_id,
            approved_rate_sources=policy_evidence["approved_rate_sources"],
        )
        asset_valuation_result = None
        if ledger_observation.get("asset_balance_totals") is not None or ledger_observation.get("asset_valuation_evidence") is not None:
            asset_valuation_result = validate_all_asset_valuation_evidence(
                balances_by_asset=ledger_observation.get("asset_balance_totals"),
                valuation_evidence=ledger_observation.get("asset_valuation_evidence"),
                policy_evidence=ledger_observation.get("valuation_policy_evidence"),
                observed_at=observed_at,
                cycle_id=cycle_id,
                max_rate_age_seconds=ledger_observation.get("max_rate_age_seconds"),
            )
            if asset_valuation_result.get("valuation_state") != "AVAILABLE":
                raise ValueError(asset_valuation_result.get("valuation_block_reason") or "PORTFOLIO_LEDGER_ALL_ASSET_VALUATION_INVALID")

        portfolio_capital = _finite_number(
            ledger_observation.get("portfolio_capital"), "PORTFOLIO_LEDGER_CAPITAL_INVALID", positive=True
        )
        usable_capital = _finite_number(
            ledger_observation.get("usable_capital"), "PORTFOLIO_LEDGER_USABLE_CAPITAL_INVALID", positive=True
        )
        if usable_capital > portfolio_capital:
            raise ValueError("PORTFOLIO_LEDGER_USABLE_CAPITAL_INVALID")
        allocated_risk = _finite_number(
            ledger_observation.get("allocated_risk"), "PORTFOLIO_LEDGER_ALLOCATED_RISK_INVALID"
        )
        concurrent_positions = ledger_observation.get("concurrent_positions")
        if isinstance(concurrent_positions, bool) or not isinstance(concurrent_positions, int) or concurrent_positions < 0:
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
            "market_coverage": ["SPOT", "FUTURES"],
            "observed_at": observed_at,
            "cycle_id": cycle_id,
            "spot_observed_at": spot_observed_at,
            "futures_observed_at": futures_observed_at,
            "valuation_policy_state": "APPROVED",
            "valuation_policy_id": valuation_policy_id,
            "valuation_policy_version": valuation_policy_version,
            "valuation_policy_approval_id": policy_evidence["approval_id"],
            "reporting_currency": "USDT",
            "currency_valuation_evidence": currency_evidence,
            "asset_valuation_evidence": asset_valuation_result.get("asset_rates") if asset_valuation_result else None,
            "valued_assets": asset_valuation_result.get("valued_assets") if asset_valuation_result else ["USDT", "USDC"],
            "portfolio_capital": portfolio_capital,
            "usable_capital": usable_capital,
            "allocated_risk": allocated_risk,
            "concurrent_positions": concurrent_positions,
        }
    except (TypeError, ValueError) as exc:
        return _blocked(str(exc).strip() or "PORTFOLIO_LEDGER_INPUT_INVALID")


__all__ = ["build_authoritative_portfolio_risk_ledger_observation"]
