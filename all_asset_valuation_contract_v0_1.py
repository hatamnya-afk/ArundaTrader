"""Fail-closed, versioned valuation evidence for every non-zero account asset.

No market prices are fetched and no approval is created here. The caller must
supply authenticated approval evidence and one approved valuation rate per
non-zero asset in the account-wide balance union.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import math
from typing import Any


def _timestamp(value: Any, reason: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(reason) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(reason)
    return parsed


def validate_all_asset_valuation_evidence(
    *, balances_by_asset: Mapping[str, Any] | None,
    valuation_evidence: Mapping[str, Any] | None,
    policy_evidence: Mapping[str, Any] | None,
    observed_at: str,
    cycle_id: str,
    max_rate_age_seconds: int,
) -> dict[str, Any]:
    def blocked(reason: str) -> dict[str, Any]:
        return {"valuation_state": "BLOCKED", "valuation_validation": "INVALID",
                "valuation_block_reason": reason, "asset_rates": None}
    try:
        if not isinstance(balances_by_asset, Mapping) or not isinstance(valuation_evidence, Mapping):
            raise ValueError("ALL_ASSET_BALANCES_AND_VALUATION_EVIDENCE_REQUIRED")
        if not isinstance(policy_evidence, Mapping) or policy_evidence.get("approval_state") != "APPROVED":
            raise ValueError("ALL_ASSET_APPROVED_POLICY_REQUIRED")
        for key in ("policy_id", "policy_version", "approval_id", "approved_by", "approval_source",
                    "approved_at", "effective_from", "effective_until"):
            if not isinstance(policy_evidence.get(key), str) or not policy_evidence[key].strip():
                raise ValueError(f"ALL_ASSET_POLICY_{key.upper()}_MISSING")
        if not str(policy_evidence["approval_source"]).lower().startswith(("https://", "file:", "git:")):
            raise ValueError("ALL_ASSET_POLICY_APPROVAL_SOURCE_INVALID")
        observed = _timestamp(observed_at, "ALL_ASSET_OBSERVED_AT_INVALID")
        approved = _timestamp(policy_evidence["approved_at"], "ALL_ASSET_POLICY_APPROVED_AT_INVALID")
        start = _timestamp(policy_evidence["effective_from"], "ALL_ASSET_POLICY_EFFECTIVE_FROM_INVALID")
        end = _timestamp(policy_evidence["effective_until"], "ALL_ASSET_POLICY_EFFECTIVE_UNTIL_INVALID")
        if approved > observed or not start <= observed <= end or end <= start:
            raise ValueError("ALL_ASSET_POLICY_NOT_EFFECTIVE_AT_OBSERVATION")
        if not isinstance(cycle_id, str) or not cycle_id.strip():
            raise ValueError("ALL_ASSET_CYCLE_ID_MISSING")
        if isinstance(max_rate_age_seconds, bool) or not isinstance(max_rate_age_seconds, int) or max_rate_age_seconds < 0:
            raise ValueError("ALL_ASSET_RATE_MAX_AGE_INVALID")

        required = set()
        for raw_asset, amount in balances_by_asset.items():
            if not isinstance(raw_asset, str) or not raw_asset.strip():
                raise ValueError("ALL_ASSET_BALANCE_ASSET_INVALID")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(float(amount)) or amount < 0:
                raise ValueError("ALL_ASSET_BALANCE_AMOUNT_INVALID")
            if amount > 0:
                required.add(raw_asset.strip().upper())
        supplied = {str(k).strip().upper() for k in valuation_evidence}
        if supplied != required:
            missing = sorted(required - supplied)
            extra = sorted(supplied - required)
            if missing:
                raise ValueError("ALL_ASSET_NONZERO_ASSET_RATE_MISSING:" + ",".join(missing))
            raise ValueError("ALL_ASSET_RATE_FOR_UNHELD_ASSET:" + ",".join(extra))
        approved_sources = policy_evidence.get("approved_rate_sources")
        if not isinstance(approved_sources, Mapping):
            raise ValueError("ALL_ASSET_APPROVED_RATE_SOURCES_REQUIRED")
        approved_by_asset = {str(k).strip().upper(): v for k, v in approved_sources.items()}
        rates = {}
        for raw_asset, row in valuation_evidence.items():
            asset = str(raw_asset).strip().upper()
            if not isinstance(row, Mapping):
                raise ValueError("ALL_ASSET_RATE_EVIDENCE_INVALID:" + asset)
            approved_row = approved_by_asset.get(asset)
            if not isinstance(approved_row, Mapping):
                raise ValueError("ALL_ASSET_RATE_SOURCE_NOT_APPROVED:" + asset)
            rate = row.get("rate_to_usdt")
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(float(rate)) or rate <= 0:
                raise ValueError("ALL_ASSET_RATE_INVALID:" + asset)
            source = row.get("rate_source")
            source_ref = row.get("source_reference")
            if not isinstance(source, str) or source != approved_row.get("source"):
                raise ValueError("ALL_ASSET_RATE_SOURCE_NOT_APPROVED:" + asset)
            if not isinstance(source_ref, str) or source_ref != approved_row.get("source_reference"):
                raise ValueError("ALL_ASSET_RATE_REFERENCE_NOT_APPROVED:" + asset)
            rate_time = _timestamp(row.get("rate_observed_at"), "ALL_ASSET_RATE_TIMESTAMP_INVALID:" + asset)
            age = (observed - rate_time).total_seconds()
            if age < 0 or age > max_rate_age_seconds:
                raise ValueError("ALL_ASSET_RATE_STALE_OR_FUTURE:" + asset)
            if row.get("cycle_id") != cycle_id:
                raise ValueError("ALL_ASSET_RATE_CYCLE_MISMATCH:" + asset)
            if row.get("valuation_policy_id") != policy_evidence["policy_id"] or row.get("valuation_policy_version") != policy_evidence["policy_version"]:
                raise ValueError("ALL_ASSET_RATE_POLICY_MISMATCH:" + asset)
            if asset == "USDT" and float(rate) != 1.0:
                raise ValueError("ALL_ASSET_USDT_BASE_RATE_MUST_EQUAL_ONE")
            rates[asset] = {"rate_to_usdt": float(rate), "rate_source": source,
                            "source_reference": source_ref, "rate_observed_at": rate_time.isoformat(),
                            "cycle_id": cycle_id, "valuation_policy_id": policy_evidence["policy_id"],
                            "valuation_policy_version": policy_evidence["policy_version"]}
        return {"valuation_state": "AVAILABLE", "valuation_validation": "VALID",
                "policy_id": policy_evidence["policy_id"], "policy_version": policy_evidence["policy_version"],
                "approval_id": policy_evidence["approval_id"], "reporting_currency": "USDT",
                "valued_assets": sorted(required), "asset_rates": rates,
                "policy_authenticity": "UPSTREAM_AUTHENTICATION_REQUIRED"}
    except (TypeError, ValueError) as exc:
        return blocked(str(exc).strip() or "ALL_ASSET_VALUATION_INVALID")


__all__ = ["validate_all_asset_valuation_evidence"]
