"""Fail-closed validation for an explicitly approved capital valuation policy.

This module validates supplied approval and rate evidence only. It does not
approve policy, fetch market prices, read accounts, value balances, or perform
network/database/execution side effects.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import math
from typing import Any


def _text(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"VALUATION_POLICY_{key.upper()}_MISSING")
    return value.strip()


def _timestamp(value: str, reason: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError(reason) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(reason)
    return parsed


def _positive_finite(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(reason)
    return result


def validate_approved_valuation_policy_evidence(
    policy_evidence: Mapping[str, Any] | None,
    *,
    valuation_observed_at: str,
) -> dict[str, Any]:
    """Validate approval metadata and the active period for a valuation policy.

    The approval record and source references are supplied by the caller. A
    syntactically valid record is not cryptographic proof of approval; upstream
    governance must authenticate the referenced approval artifact.
    """
    if not isinstance(policy_evidence, Mapping):
        raise ValueError("VALUATION_POLICY_APPROVAL_EVIDENCE_REQUIRED")
    if policy_evidence.get("approval_state") != "APPROVED":
        raise ValueError("VALUATION_POLICY_APPROVAL_REQUIRED")

    policy_id = _text(policy_evidence, "policy_id")
    policy_version = _text(policy_evidence, "policy_version")
    approval_id = _text(policy_evidence, "approval_id")
    approver = _text(policy_evidence, "approved_by")
    approval_source = _text(policy_evidence, "approval_source")
    approved_at_raw = _text(policy_evidence, "approved_at")
    effective_from_raw = _text(policy_evidence, "effective_from")
    effective_until_raw = _text(policy_evidence, "effective_until")
    observed_at = _timestamp(valuation_observed_at, "VALUATION_OBSERVATION_TIMESTAMP_INVALID")
    approved_at = _timestamp(approved_at_raw, "VALUATION_POLICY_APPROVAL_TIMESTAMP_INVALID")
    effective_from = _timestamp(effective_from_raw, "VALUATION_POLICY_EFFECTIVE_FROM_INVALID")
    effective_until = _timestamp(effective_until_raw, "VALUATION_POLICY_EFFECTIVE_UNTIL_INVALID")
    if effective_until <= effective_from:
        raise ValueError("VALUATION_POLICY_EFFECTIVE_WINDOW_INVALID")
    if approved_at > observed_at or not (effective_from <= observed_at <= effective_until):
        raise ValueError("VALUATION_POLICY_NOT_EFFECTIVE_AT_OBSERVATION")
    if not approval_source.lower().startswith(("https://", "file:", "git:")):
        raise ValueError("VALUATION_POLICY_APPROVAL_SOURCE_INVALID")

    raw_rates = policy_evidence.get("approved_rate_sources")
    if not isinstance(raw_rates, Mapping):
        raise ValueError("VALUATION_POLICY_USDT_USDC_RATE_SOURCES_REQUIRED")
    normalized_keys = [str(k).strip().upper() for k in raw_rates]
    if len(set(normalized_keys)) != len(normalized_keys) or not {"USDT", "USDC"}.issubset(set(normalized_keys)):
        raise ValueError("VALUATION_POLICY_USDT_USDC_AND_UNIQUE_ASSET_RATE_SOURCES_REQUIRED")
    rates: dict[str, dict[str, str]] = {}
    for raw_currency, raw_row in raw_rates.items():
        currency = str(raw_currency).upper()
        if not isinstance(raw_row, Mapping):
            raise ValueError("VALUATION_POLICY_RATE_SOURCE_INVALID")
        source = _text(raw_row, "source")
        source_ref = _text(raw_row, "source_reference")
        if not source_ref.lower().startswith(("https://", "file:", "git:")):
            raise ValueError("VALUATION_POLICY_RATE_SOURCE_REFERENCE_INVALID")
        rates[currency] = {"source": source, "source_reference": source_ref}

    return {
        "policy_state": "APPROVED",
        "policy_validation": "VALID",
        "policy_id": policy_id,
        "policy_version": policy_version,
        "approval_id": approval_id,
        "approved_by": approver,
        "approval_source": approval_source,
        "approved_at": approved_at.isoformat(),
        "effective_from": effective_from.isoformat(),
        "effective_until": effective_until.isoformat(),
        "valuation_observed_at": observed_at.isoformat(),
        "reporting_currency": "USDT",
        "supported_currencies": sorted(rates),
        "approved_rate_sources": rates,
        "approval_authenticity": "UPSTREAM_AUTHENTICATION_REQUIRED",
    }


__all__ = ["validate_approved_valuation_policy_evidence"]
