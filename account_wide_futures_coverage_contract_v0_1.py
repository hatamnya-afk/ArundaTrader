"""Fail-closed evidence contract for account-wide Futures position coverage.

This contract validates supplied provider evidence only. It does not assert that
a particular Toobit endpoint provides account-wide results, and performs no I/O.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def validate_account_wide_futures_coverage(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    def blocked(reason: str) -> dict[str, Any]:
        return {"coverage_state": "BLOCKED", "coverage_validation": "INVALID",
                "coverage_block_reason": reason, "positions": None}
    if not isinstance(evidence, Mapping):
        return blocked("FUTURES_ACCOUNT_WIDE_EVIDENCE_REQUIRED")
    try:
        for key, reason in (
            ("account_scope", "FUTURES_ACCOUNT_SCOPE_MISSING"),
            ("cycle_id", "FUTURES_CYCLE_ID_MISSING"),
            ("observed_at", "FUTURES_OBSERVED_AT_MISSING"),
            ("provider_endpoint", "FUTURES_PROVIDER_ENDPOINT_MISSING"),
            ("provider_request_id", "FUTURES_PROVIDER_REQUEST_ID_MISSING"),
            ("provenance", "FUTURES_PROVENANCE_MISSING"),
        ):
            value = evidence.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(reason)
        if evidence.get("http_method") != "GET":
            raise ValueError("FUTURES_READ_ONLY_GET_REQUIRED")
        if evidence.get("coverage_scope") != "ACCOUNT_WIDE":
            raise ValueError("FUTURES_ACCOUNT_WIDE_COVERAGE_REQUIRED")
        if evidence.get("pagination_complete") is not True:
            raise ValueError("FUTURES_PAGINATION_COMPLETENESS_UNPROVEN")
        received = evidence.get("pages_received")
        total = evidence.get("pages_total")
        if (isinstance(received, bool) or not isinstance(received, int) or received < 1
                or isinstance(total, bool) or not isinstance(total, int) or total < 1
                or received != total):
            raise ValueError("FUTURES_PAGINATION_PAGE_COUNT_MISMATCH")
        positions = evidence.get("positions")
        if not isinstance(positions, list) or any(not isinstance(row, Mapping) for row in positions):
            raise ValueError("FUTURES_POSITION_ROWS_INVALID")
        ids = []
        for row in positions:
            position_id = row.get("position_id")
            if not isinstance(position_id, str) or not position_id.strip():
                raise ValueError("FUTURES_POSITION_ID_MISSING")
            if position_id in ids:
                raise ValueError("FUTURES_POSITION_ID_DUPLICATE")
            ids.append(position_id)
            risk = row.get("allocated_risk_usdt")
            if isinstance(risk, bool) or not isinstance(risk, (int, float)) or risk < 0:
                raise ValueError("FUTURES_POSITION_ALLOCATED_RISK_MISSING")
        return {
            "coverage_state": "AVAILABLE", "coverage_validation": "VALID",
            "coverage_scope": "ACCOUNT_WIDE", "account_scope": evidence["account_scope"].strip(),
            "cycle_id": evidence["cycle_id"].strip(), "observed_at": evidence["observed_at"].strip(),
            "provider_endpoint": evidence["provider_endpoint"].strip(),
            "provider_request_id": evidence["provider_request_id"].strip(),
            "http_method": "GET", "pagination_complete": True,
            "pages_received": received, "pages_total": total,
            "position_count": len(positions), "positions": [dict(row) for row in positions],
            "provenance": evidence["provenance"].strip(),
            "provider_completeness_claim": "REQUIRES_ENDPOINT_SEMANTICS_VERIFICATION",
        }
    except (TypeError, ValueError) as exc:
        return blocked(str(exc).strip() or "FUTURES_COVERAGE_INVALID")


__all__ = ["validate_account_wide_futures_coverage"]
