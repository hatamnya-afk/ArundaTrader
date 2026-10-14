"""Account-wide Spot + Futures ledger producer from supplied raw observations.

Pure validation/aggregation only: no exchange calls, DB writes, price discovery,
or invented risk. Inputs must be captured upstream by read-only providers and
normalized with explicit asset amounts. Only USDT/USDC are valued in v0.1;
any non-zero unsupported asset blocks rather than silently understating equity.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from approved_valuation_policy_source_contract_v0_1 import (
    validate_approved_valuation_policy_evidence,
)
from authoritative_portfolio_risk_ledger_contract_v0_1 import (
    build_authoritative_portfolio_risk_ledger_observation,
)
from all_asset_valuation_contract_v0_1 import validate_all_asset_valuation_evidence
from account_wide_futures_coverage_contract_v0_1 import validate_account_wide_futures_coverage


_SUPPORTED = {"USDT", "USDC"}


def _blocked(reason: str, *, spot: Any = None, futures: Any = None) -> dict[str, Any]:
    return {
        "producer_state": "BLOCKED",
        "producer_block_reason": reason,
        "portfolio_state": "BLOCKED",
        "portfolio_block_reason": reason,
        "portfolio_capital": None,
        "usable_capital": None,
        "allocated_risk": None,
        "concurrent_positions": None,
        "spot_observation": spot,
        "futures_observation": futures,
    }


def _number(value: Any, reason: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    result = float(value)
    if not math.isfinite(result) or (result < 0 if allow_zero else result <= 0):
        raise ValueError(reason)
    return result


def _balance_totals(observation: Mapping[str, Any], market: str) -> dict[str, dict[str, float]]:
    expected_source = "TOOBIT_SPOT_ACCOUNT_GET" if market == "SPOT" else "TOOBIT_FUTURES_ACCOUNT_GET"
    if observation.get("observation_state") != "AVAILABLE":
        raise ValueError(f"PORTFOLIO_LEDGER_{market}_OBSERVATION_UNAVAILABLE")
    if observation.get("observation_source") != expected_source:
        raise ValueError(f"PORTFOLIO_LEDGER_{market}_SOURCE_INVALID")
    rows = observation.get("balances")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ValueError(f"PORTFOLIO_LEDGER_{market}_BALANCES_INVALID")
    totals: dict[str, dict[str, float]] = {}
    for row in rows:
        asset = row.get("asset")
        if not isinstance(asset, str) or not asset.strip():
            raise ValueError(f"PORTFOLIO_LEDGER_{market}_BALANCE_ASSET_MISSING")
        asset = asset.strip().upper()
        total = _number(row.get("total_amount"), f"PORTFOLIO_LEDGER_{market}_TOTAL_AMOUNT_INVALID")
        usable = _number(row.get("usable_amount"), f"PORTFOLIO_LEDGER_{market}_USABLE_AMOUNT_INVALID")
        if usable > total:
            raise ValueError(f"PORTFOLIO_LEDGER_{market}_USABLE_EXCEEDS_TOTAL")
        if asset not in totals:
            totals[asset] = {"total_amount": 0.0, "usable_amount": 0.0}
        totals[asset]["total_amount"] += total
        totals[asset]["usable_amount"] += usable
    for currency in _SUPPORTED:
        totals.setdefault(currency, {"total_amount": 0.0, "usable_amount": 0.0})
    return totals


def build_toobit_account_wide_portfolio_risk_ledger(
    *,
    spot_observation: Mapping[str, Any] | None,
    futures_observation: Mapping[str, Any] | None,
    valuation_policy_evidence: Mapping[str, Any] | None,
    currency_valuation_evidence: Mapping[str, Any] | None,
    ledger_id: str,
    ledger_version: str,
    account_scope: str,
    observed_at: str,
    cycle_id: str,
    provenance: str,
    allocated_risk_usdt: float | None,
    asset_valuation_evidence: Mapping[str, Any] | None = None,
    max_rate_age_seconds: int | None = None,
) -> dict[str, Any]:
    """Aggregate normalized read-only observations; fail closed on incomplete coverage.

    Each balance row must contain normalized `asset`, `total_amount`, and
    `usable_amount`; raw provider payloads are not guessed/interpreted here.
    Futures positions must be explicitly account-wide and include one
    non-negative `allocated_risk_usdt` per open position. Risk is never inferred.
    """
    if not isinstance(spot_observation, Mapping) or not isinstance(futures_observation, Mapping):
        return _blocked("PORTFOLIO_LEDGER_SPOT_AND_FUTURES_OBSERVATIONS_REQUIRED")
    try:
        for label, value in (
            ("LEDGER_ID", ledger_id), ("LEDGER_VERSION", ledger_version),
            ("ACCOUNT_SCOPE", account_scope), ("OBSERVED_AT", observed_at),
            ("CYCLE_ID", cycle_id), ("PROVENANCE", provenance),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"PORTFOLIO_LEDGER_{label}_MISSING")
        for market, row in (("SPOT", spot_observation), ("FUTURES", futures_observation)):
            if row.get("account_scope") != account_scope:
                raise ValueError(f"PORTFOLIO_LEDGER_{market}_ACCOUNT_SCOPE_MISMATCH")
            if row.get("cycle_id") != cycle_id:
                raise ValueError(f"PORTFOLIO_LEDGER_{market}_CYCLE_MISMATCH")
            if row.get("observed_at") != observed_at:
                raise ValueError(f"PORTFOLIO_LEDGER_{market}_TIMESTAMP_MISMATCH")
            if row.get("coverage_scope") != "ACCOUNT_WIDE":
                raise ValueError(f"PORTFOLIO_LEDGER_{market}_ACCOUNT_WIDE_COVERAGE_REQUIRED")

        policy = validate_approved_valuation_policy_evidence(
            valuation_policy_evidence, valuation_observed_at=observed_at
        )
        if not isinstance(currency_valuation_evidence, Mapping) or {
            str(key).upper() for key in currency_valuation_evidence
        } != _SUPPORTED:
            raise ValueError("PORTFOLIO_LEDGER_USDT_USDC_VALUATION_EVIDENCE_REQUIRED")
        rates: dict[str, float] = {}
        for raw_currency, row in currency_valuation_evidence.items():
            currency = str(raw_currency).upper()
            if not isinstance(row, Mapping):
                raise ValueError("PORTFOLIO_LEDGER_CURRENCY_VALUATION_INVALID")
            if row.get("valuation_policy_id") != policy["policy_id"] or row.get("valuation_policy_version") != policy["policy_version"]:
                raise ValueError("PORTFOLIO_LEDGER_CURRENCY_POLICY_MISMATCH")
            if row.get("cycle_id") != cycle_id:
                raise ValueError("PORTFOLIO_LEDGER_CURRENCY_CYCLE_MISMATCH")
            if row.get("rate_source") != policy["approved_rate_sources"][currency]["source"]:
                raise ValueError("PORTFOLIO_LEDGER_CURRENCY_RATE_SOURCE_NOT_APPROVED")
            rates[currency] = _number(row.get("rate_to_usdt"), "PORTFOLIO_LEDGER_CURRENCY_RATE_INVALID", allow_zero=False)
            if currency == "USDT" and rates[currency] != 1.0:
                raise ValueError("PORTFOLIO_LEDGER_USDT_BASE_RATE_MUST_EQUAL_ONE")

        spot = _balance_totals(spot_observation, "SPOT")
        futures = _balance_totals(futures_observation, "FUTURES")
        asset_totals = {}
        for asset in set(spot) | set(futures):
            asset_totals[asset] = {
                "total_amount": spot.get(asset, {"total_amount": 0.0})["total_amount"] + futures.get(asset, {"total_amount": 0.0})["total_amount"],
                "usable_amount": spot.get(asset, {"usable_amount": 0.0})["usable_amount"] + futures.get(asset, {"usable_amount": 0.0})["usable_amount"],
            }
        nonzero_totals = {asset: row["total_amount"] for asset, row in asset_totals.items() if row["total_amount"] > 0}
        all_asset_result = None
        if asset_valuation_evidence is not None:
            if max_rate_age_seconds is None:
                raise ValueError("PORTFOLIO_LEDGER_ALL_ASSET_RATE_MAX_AGE_REQUIRED")
            all_asset_result = validate_all_asset_valuation_evidence(
                balances_by_asset=nonzero_totals,
                valuation_evidence=asset_valuation_evidence,
                policy_evidence=valuation_policy_evidence,
                observed_at=observed_at,
                cycle_id=cycle_id,
                max_rate_age_seconds=max_rate_age_seconds,
            )
            if all_asset_result.get("valuation_state") != "AVAILABLE":
                raise ValueError(all_asset_result.get("valuation_block_reason") or "PORTFOLIO_LEDGER_ALL_ASSET_VALUATION_INVALID")
            rates = {asset: row["rate_to_usdt"] for asset, row in all_asset_result["asset_rates"].items()}
        elif any(asset not in _SUPPORTED and row["total_amount"] > 0 for asset, row in asset_totals.items()):
            raise ValueError("PORTFOLIO_LEDGER_ALL_ASSET_VALUATION_EVIDENCE_REQUIRED")
        portfolio_capital = sum(row["total_amount"] * rates[asset] for asset, row in asset_totals.items() if row["total_amount"] > 0)
        usable_capital = sum(row["usable_amount"] * rates[asset] for asset, row in asset_totals.items() if row["usable_amount"] > 0)
        if portfolio_capital <= 0 or usable_capital <= 0 or usable_capital > portfolio_capital:
            raise ValueError("PORTFOLIO_LEDGER_CAPITAL_OR_USABLE_CAPITAL_INVALID")

        positions = futures_observation.get("positions")
        if futures_observation.get("positions_coverage") != "ACCOUNT_WIDE" or not isinstance(positions, list) or any(not isinstance(p, Mapping) for p in positions):
            raise ValueError("PORTFOLIO_LEDGER_ACCOUNT_WIDE_POSITIONS_REQUIRED")
        coverage_evidence = futures_observation.get("coverage_evidence")
        if coverage_evidence is not None:
            coverage = validate_account_wide_futures_coverage(coverage_evidence)
            if coverage.get("coverage_state") != "AVAILABLE":
                raise ValueError(coverage.get("coverage_block_reason") or "PORTFOLIO_LEDGER_FUTURES_COVERAGE_INVALID")
            def identities(rows):
                return sorted((str(row.get("symbol", "")).strip().upper(), str(row.get("side", "")).strip().upper()) for row in rows)
            if identities(positions) != identities(coverage.get("positions") or []):
                raise ValueError("PORTFOLIO_LEDGER_FUTURES_COVERAGE_POSITION_SET_MISMATCH")
        if allocated_risk_usdt is None:
            raise ValueError("PORTFOLIO_LEDGER_ALLOCATED_RISK_EVIDENCE_REQUIRED")
        allocated_risk = _number(allocated_risk_usdt, "PORTFOLIO_LEDGER_ALLOCATED_RISK_INVALID")
        position_risk_sum = 0.0
        for position in positions:
            risk = _number(position.get("allocated_risk_usdt"), "PORTFOLIO_LEDGER_POSITION_RISK_MISSING")
            position_risk_sum += risk
        if not math.isclose(position_risk_sum, allocated_risk, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("PORTFOLIO_LEDGER_ALLOCATED_RISK_TOTAL_MISMATCH")

        currency_evidence = {}
        for currency in sorted(_SUPPORTED):
            total = asset_totals.get(currency, {"total_amount": 0.0})["total_amount"]
            row = (asset_valuation_evidence or {}).get(currency) or currency_valuation_evidence[currency]
            currency_evidence[currency] = {
                "raw_amount": total,
                "rate_to_usdt": rates[currency],
                "rate_source": row["rate_source"],
                "rate_observed_at": row["rate_observed_at"],
                "valuation_policy_id": policy["policy_id"],
                "valuation_policy_version": policy["policy_version"],
                "cycle_id": cycle_id,
            }
        ledger_input = {
            "ledger_state": "AVAILABLE", "ledger_validation": "VALID",
            "coverage_scope": "ACCOUNT_WIDE", "market_coverage": ["SPOT", "FUTURES"],
            "ledger_id": ledger_id, "ledger_version": ledger_version,
            "ledger_source": "TOOBIT_ACCOUNT_WIDE_SPOT_FUTURES_AGGREGATOR_V0_1",
            "account_scope": account_scope, "asset_scope": "ACCOUNT_WIDE",
            "observed_at": observed_at, "cycle_id": cycle_id,
            "spot_observed_at": spot_observation["observed_at"],
            "futures_observed_at": futures_observation["observed_at"],
            "provenance": provenance, "valuation_policy_state": "APPROVED",
            "valuation_policy_id": policy["policy_id"],
            "valuation_policy_version": policy["policy_version"],
            "valuation_policy_evidence": dict(valuation_policy_evidence),
            "reporting_currency": "USDT",
            "currency_valuation_evidence": currency_evidence,
            "asset_balance_totals": nonzero_totals if all_asset_result else None,
            "asset_valuation_evidence": asset_valuation_evidence if all_asset_result else None,
            "max_rate_age_seconds": max_rate_age_seconds if all_asset_result else None,
            "portfolio_capital": portfolio_capital, "usable_capital": usable_capital,
            "allocated_risk": allocated_risk, "concurrent_positions": len(positions),
        }
        result = build_authoritative_portfolio_risk_ledger_observation(ledger_input)
        return {
            "producer_state": "AVAILABLE" if result.get("portfolio_state") == "AVAILABLE" else "BLOCKED",
            "producer_block_reason": result.get("portfolio_block_reason"),
            **result,
            "spot_observation": dict(spot_observation),
            "futures_observation": dict(futures_observation),
        }
    except (TypeError, ValueError, KeyError) as exc:
        reason = str(exc).strip() or "PORTFOLIO_LEDGER_INPUT_INVALID"
        return _blocked(reason, spot=spot_observation, futures=futures_observation)


__all__ = ["build_toobit_account_wide_portfolio_risk_ledger"]
