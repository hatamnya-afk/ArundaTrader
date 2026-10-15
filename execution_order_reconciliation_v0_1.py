"""Read-only order reconciliation and durable evidence capture.

This module never submits, cancels, or retries an order. A negative or failed
provider lookup is not proof of non-execution and leaves the intent quarantined.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    PROVIDER_ACCEPTED,
    PROVIDER_REJECTED,
    RECONCILIATION_REQUIRED,
    SUBMISSION_OUTCOME_UNKNOWN,
)


def reconcile_order_attempt(
    *,
    claim_store: Any,
    adapter: Any,
    intent_id: str,
    venue: str,
    symbol: str,
    execution_instrument: Any = None,
) -> dict[str, Any]:
    """Reconcile only an already-fenced intent; never permit a retry."""
    provider_namespace = "ARUNDA-EXECUTION"
    claim = claim_store.get(provider_namespace=provider_namespace, intent_id=intent_id)
    if claim is None:
        return {"allowed": False, "reason": "INTENT_CLAIM_NOT_FOUND"}
    if claim.status not in {SUBMISSION_OUTCOME_UNKNOWN, RECONCILIATION_REQUIRED}:
        return {"allowed": False, "reason": "CLAIM_NOT_RECONCILABLE",
                "claim_status": claim.status, "resubmit_allowed": False}
    lookup = getattr(adapter, "query_order_by_client_order_id", None)
    if not callable(lookup):
        return {"allowed": False, "reason": "READ_ONLY_RECONCILIATION_UNSUPPORTED"}

    event_id = str(uuid4())
    try:
        result = lookup(venue=venue, symbol=symbol,
                        client_order_id=claim.client_order_id,
                        execution_instrument=execution_instrument)
        lookup_detail = getattr(result, "reason", "LOOKUP_RESULT_INVALID")
    except Exception as exc:
        result = None
        lookup_detail = f"LOOKUP_RAISED:{type(exc).__name__}:{exc}"

    data = getattr(result, "data", None) if result is not None else None
    if (result is not None and getattr(result, "allowed", False) is True
            and getattr(result, "reason", None) == "ORDER_FOUND"
            and isinstance(data, dict) and data.get("state_known") is True
            and data.get("client_order_id") == claim.client_order_id
            and str(data.get("symbol", "")).upper() == symbol.strip().upper()
            and str(data.get("exchange_order_id", "")).strip()
            and str(data.get("provider_status", "")).strip()):
        normalized = {
            "client_order_id": claim.client_order_id, "venue": str(venue).upper(),
            "symbol": str(data["symbol"]).upper(),
            "exchange_order_id": str(data["exchange_order_id"]),
            "provider_status": str(data["provider_status"]).upper(),
            "executed_quantity": data.get("executed_quantity"),
            "executed_price": data.get("executed_price"),
            "provider_timestamp": data.get("timestamp"),
            "reconciliation_state": "ORDER_FOUND",
        }
        fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
        evidence_id = f"{claim.trade_event_id or intent_id}:reconciliation:{normalized['exchange_order_id']}:{fingerprint}"
        claim_store.record_reconciliation_evidence(
            provider_namespace=provider_namespace, intent_id=intent_id,
            evidence_event_id=evidence_id, client_order_id=claim.client_order_id,
            venue=venue, symbol=symbol, reconciliation_state="ORDER_FOUND",
            detail_code="READ_ONLY_PROVIDER_ORDER_IDENTITY_MATCHED",
            exchange_order_id=normalized["exchange_order_id"],
            provider_status=normalized["provider_status"],
            executed_quantity=None if normalized["executed_quantity"] is None else str(normalized["executed_quantity"]),
            executed_price=None if normalized["executed_price"] is None else str(normalized["executed_price"]),
            provider_timestamp=None if normalized["provider_timestamp"] is None else str(normalized["provider_timestamp"]),
            normalized_payload=normalized)
        explicitly_rejected = normalized["provider_status"] in {"REJECTED", "ORDER_REJECTED"}
        terminal_claim_status = PROVIDER_REJECTED if explicitly_rejected else PROVIDER_ACCEPTED
        claim_store.transition(
            provider_namespace=provider_namespace, intent_id=intent_id,
            status=terminal_claim_status, trade_event_id=claim.trade_event_id,
            decision_id=claim.decision_id,
            exchange_order_id=normalized["exchange_order_id"],
            provider_status=normalized["provider_status"],
            evidence_event_id=evidence_id,
            detail_code=("READ_ONLY_RECONCILIATION_PROVIDER_REJECTION"
                         if explicitly_rejected else "READ_ONLY_RECONCILIATION_ORDER_FOUND"))
        return {"allowed": True,
                "reason": "ORDER_FOUND_PROVIDER_REJECTED" if explicitly_rejected else "ORDER_FOUND",
                "claim_status": terminal_claim_status, "evidence_event_id": evidence_id,
                "order_evidence": normalized, "resubmit_allowed": False}

    unresolved = data if isinstance(data, dict) else {}
    detail = str(unresolved.get("reconciliation_state") or lookup_detail or "ORDER_LOOKUP_UNRESOLVED")
    claim_store.record_reconciliation_evidence(
        provider_namespace=provider_namespace, intent_id=intent_id,
        evidence_event_id=event_id, client_order_id=claim.client_order_id,
        venue=venue, symbol=symbol,
        reconciliation_state="UNRESOLVED_KEEP_QUARANTINED", detail_code=detail,
        normalized_payload={"client_order_id": claim.client_order_id,
                            "venue": str(venue).upper(), "symbol": symbol.strip().upper(),
                            "state_known": False, "resubmit_allowed": False,
                            "detail": unresolved.get("detail") or lookup_detail})
    claim_store.transition(
        provider_namespace=provider_namespace, intent_id=intent_id,
        status=RECONCILIATION_REQUIRED, trade_event_id=claim.trade_event_id,
        decision_id=claim.decision_id,
        detail_code="READ_ONLY_RECONCILIATION_UNRESOLVED_NO_RESUBMIT")
    return {"allowed": False, "reason": "ORDER_LOOKUP_UNRESOLVED",
            "claim_status": RECONCILIATION_REQUIRED,
            "evidence_event_id": event_id, "resubmit_allowed": False}


__all__ = ["reconcile_order_attempt"]
