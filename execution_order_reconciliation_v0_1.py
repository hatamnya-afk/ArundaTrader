"""Compatibility wrapper over the canonical reconciliation coordinator.

All evidence persistence and claim transitions are owned by
exchange_execution_order_reconciliation_v0_1.reconcile_ambiguous_order.
This wrapper adds no independent reconciliation logic.
"""
from __future__ import annotations

from typing import Any

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    RECONCILIATION_REQUIRED,
    SUBMISSION_OUTCOME_UNKNOWN,
)
from exchange_execution_order_reconciliation_v0_1 import reconcile_ambiguous_order


def reconcile_order_attempt(
    *,
    claim_store: Any,
    adapter: Any,
    intent_id: str,
    venue: str,
    symbol: str,
    execution_instrument: Any = None,
) -> dict[str, Any]:
    namespace = "ARUNDA-EXECUTION"
    claim = claim_store.get(provider_namespace=namespace, intent_id=intent_id)
    if claim is None:
        return {"allowed": False, "reason": "INTENT_CLAIM_NOT_FOUND",
                "claim_status": None, "resubmit_allowed": False}
    if claim.status not in {SUBMISSION_OUTCOME_UNKNOWN, RECONCILIATION_REQUIRED}:
        return {"allowed": False, "reason": "CLAIM_NOT_RECONCILABLE",
                "claim_status": claim.status, "resubmit_allowed": False}

    result = reconcile_ambiguous_order(
        claim_store=claim_store, adapter=adapter,
        provider_namespace=namespace, intent_id=intent_id,
        venue=venue, symbol=symbol,
        execution_instrument=execution_instrument,
    )
    current = claim_store.get(provider_namespace=namespace, intent_id=intent_id)
    state = result.get("state")
    found = state == "ORDER_FOUND"
    evidence = {
        "client_order_id": result.get("client_order_id"),
        "venue": venue.upper(),
        "symbol": symbol.upper(),
        "exchange_order_id": result.get("exchange_order_id"),
        "provider_status": result.get("provider_status"),
        "reconciliation_state": state,
    }
    reason = "ORDER_FOUND"
    if found and str(result.get("provider_status", "")).upper() in {"REJECTED", "ORDER_REJECTED"}:
        reason = "ORDER_FOUND_PROVIDER_REJECTED"
    elif not found:
        reason = "ORDER_LOOKUP_UNRESOLVED"
    return {
        **result,
        "allowed": found,
        "reason": reason,
        "claim_status": getattr(current, "status", None),
        "order_evidence": evidence if found else None,
        "resubmit_allowed": False,
    }


__all__ = ["reconcile_order_attempt"]
