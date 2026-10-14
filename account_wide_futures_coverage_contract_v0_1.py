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
        semantics = evidence.get("provider_contract_semantics")
        if semantics != "DOCUMENTED_ALL_CONTRACT_POSITIONS_WHEN_SYMBOL_OMITTED":
            raise ValueError("FUTURES_ENDPOINT_ACCOUNT_WIDE_SEMANTICS_UNVERIFIED")
        positions = evidence.get("positions")
        if not isinstance(positions, list) or any(not isinstance(row, Mapping) for row in positions):
            raise ValueError("FUTURES_POSITION_ROWS_INVALID")
        ids = []
        for row in positions:
            symbol = row.get("symbol")
            side = str(row.get("side", "")).strip().upper()
            if not isinstance(symbol, str) or not symbol.strip() or side not in {"LONG", "SHORT"}:
                raise ValueError("FUTURES_POSITION_IDENTITY_MISSING")
            position_id = symbol.strip().upper() + ":" + side
            if position_id in ids:
                raise ValueError("FUTURES_POSITION_ID_DUPLICATE")
            ids.append(position_id)
        return {
            "coverage_state": "AVAILABLE", "coverage_validation": "VALID",
            "coverage_scope": "ACCOUNT_WIDE", "account_scope": evidence["account_scope"].strip(),
            "cycle_id": evidence["cycle_id"].strip(), "observed_at": evidence["observed_at"].strip(),
            "provider_endpoint": evidence["provider_endpoint"].strip(),
            "http_method": "GET", "pagination_complete": True,
            "pages_received": received, "pages_total": total,
            "position_count": len(positions), "positions": [dict(row) for row in positions],
            "provenance": evidence["provenance"].strip(),
            "provider_contract_semantics": semantics,
            "provider_completeness_claim": "DOCUMENTATION_CONTRACT_ONLY_RUNTIME_RESPONSE_STILL_REQUIRED",
        }
    except (TypeError, ValueError) as exc:
        return blocked(str(exc).strip() or "FUTURES_COVERAGE_INVALID")


__all__ = ["validate_account_wide_futures_coverage"]
