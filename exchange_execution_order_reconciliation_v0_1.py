"""Fail-closed reconciliation coordinator for ambiguous provider order outcomes.

This module never submits, retries, cancels, or writes the production trading DB.
The caller supplies the explicitly isolated durable claim/evidence store.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def reconcile_ambiguous_order(
    *,
    claim_store: Any,
    adapter: Any,
    provider_namespace: str,
    intent_id: str,
    venue: str,
    symbol: str,
    execution_instrument: Any = None,
) -> dict[str, Any]:
    """Query one exact client ID and persist positive or unresolved evidence.

    A negative/error lookup is not proof of non-execution. It is persisted as
    RECONCILIATION_REQUIRED and never releases the claim or permits resubmission.
    """
    required = {
        "provider_namespace": provider_namespace,
        "intent_id": intent_id,
        "venue": venue,
        "symbol": symbol,
    }
    if any(not isinstance(v, str) or not v.strip() for v in required.values()):
        return {"state": "BLOCKED", "reason": "RECONCILIATION_INPUT_INVALID", "resubmit_allowed": False}

    try:
        claim = claim_store.get(
            provider_namespace=provider_namespace,
            intent_id=intent_id,
        )
    except Exception as exc:
        return {"state": "BLOCKED", "reason": "CLAIM_READ_FAILED", "detail": str(exc), "resubmit_allowed": False}
    if claim is None:
        return {"state": "BLOCKED", "reason": "INTENT_CLAIM_NOT_FOUND", "resubmit_allowed": False}

    client_order_id = getattr(claim, "client_order_id", None)
    if not isinstance(client_order_id, str) or not client_order_id.strip():
        return {"state": "BLOCKED", "reason": "CLAIM_CLIENT_ID_INVALID", "resubmit_allowed": False}

    try:
        result = adapter.query_order_by_client_order_id(
            venue=venue,
            symbol=symbol,
            client_order_id=client_order_id,
            execution_instrument=execution_instrument,
        )
    except Exception as exc:
        result = None
        query_detail = str(exc)
    else:
        query_detail = ""

    data = getattr(result, "data", None)
    found = (
        getattr(result, "allowed", False) is True
        and getattr(result, "reason", None) == "ORDER_FOUND"
        and isinstance(data, dict)
        and data.get("state_known") is True
        and data.get("client_order_id") == client_order_id
        and str(data.get("symbol", "")).strip().upper() == symbol.strip().upper()
        and bool(str(data.get("exchange_order_id", "")).strip())
        and bool(str(data.get("provider_status", "")).strip())
        and (
            not getattr(claim, "exchange_order_id", None)
            or str(getattr(claim, "exchange_order_id")).strip()
            == str(data.get("exchange_order_id", "")).strip()
        )
    )

    if found:
        provider_status = str(data["provider_status"]).strip().upper()
        exchange_order_id = str(data["exchange_order_id"]).strip()
        fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
        evidence_id = f"reconciliation:{intent_id}:{client_order_id}:{exchange_order_id}:{fingerprint}"
        state = "ORDER_FOUND"
        detail_code = "READ_ONLY_PROVIDER_ORDER_IDENTITY_MATCHED"
        try:
            claim_store.record_reconciliation_evidence(
                provider_namespace=provider_namespace,
                intent_id=intent_id,
                evidence_event_id=evidence_id,
                client_order_id=client_order_id,
                venue=venue,
                symbol=symbol,
                reconciliation_state=state,
                detail_code=detail_code,
                exchange_order_id=exchange_order_id,
                provider_status=provider_status,
                executed_quantity=None if data.get("executed_quantity") is None else str(data.get("executed_quantity")),
                executed_price=None if data.get("executed_price") is None else str(data.get("executed_price")),
                provider_timestamp=None if data.get("timestamp") is None else str(data.get("timestamp")),
                normalized_payload={
                    "provider": "TOOBIT",
                    "lookup_reason": getattr(result, "reason", ""),
                    "state_known": True,
                    "raw_order": data.get("raw_order", {}),
                },
            )
            # Preserve the original attempt evidence identity already fenced
            # before POST; reconciliation gets its own immutable evidence row.
            if getattr(claim, "status", None) not in {"PROVIDER_ACCEPTED", "PROVIDER_REJECTED"}:
                rejected = provider_status in {"REJECTED", "ORDER_REJECTED"}
                claim_store.transition(
                    provider_namespace=provider_namespace,
                    intent_id=intent_id,
                    status="PROVIDER_REJECTED" if rejected else "PROVIDER_ACCEPTED",
                    trade_event_id=getattr(claim, "trade_event_id", None),
                    decision_id=getattr(claim, "decision_id", None),
                    exchange_order_id=exchange_order_id,
                    provider_status=provider_status,
                    evidence_event_id=getattr(claim, "evidence_event_id", None) or evidence_id,
                    detail_code=detail_code,
                )
        except Exception as exc:
            return {
                "state": "EVIDENCE_PERSISTENCE_FAILED",
                "reason": "RECONCILIATION_EVIDENCE_PERSISTENCE_FAILED",
                "detail": str(exc),
                "client_order_id": client_order_id,
                "resubmit_allowed": False,
            }
        return {
            "state": state,
            "client_order_id": client_order_id,
            "exchange_order_id": exchange_order_id,
            "provider_status": provider_status,
            "evidence_event_id": evidence_id,
            "resubmit_allowed": False,
        }

    reason = getattr(result, "reason", "ORDER_LOOKUP_UNRESOLVED") if result is not None else "ORDER_LOOKUP_EXCEPTION"
    if isinstance(data, dict) and data.get("state_known") is False:
        query_detail = str(data.get("detail", query_detail))
    unresolved_fingerprint = hashlib.sha256(json.dumps({"reason": str(reason), "detail": query_detail}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    evidence_id = f"reconciliation-unresolved:{intent_id}:{client_order_id}:{unresolved_fingerprint}"
    detail_code = str(reason)
    try:
        claim_store.record_reconciliation_evidence(
            provider_namespace=provider_namespace,
            intent_id=intent_id,
            evidence_event_id=evidence_id,
            client_order_id=client_order_id,
            venue=venue,
            symbol=symbol,
            reconciliation_state="UNRESOLVED_KEEP_QUARANTINED",
            detail_code=detail_code,
            normalized_payload={
                "provider": "TOOBIT",
                "lookup_reason": str(reason),
                "detail": query_detail,
                "state_known": False,
                "resubmit_allowed": False,
            },
        )
        if getattr(claim, "status", None) not in {"PROVIDER_ACCEPTED", "PROVIDER_REJECTED", "RECONCILIATION_REQUIRED"}:
            claim_store.transition(
                provider_namespace=provider_namespace,
                intent_id=intent_id,
                status="RECONCILIATION_REQUIRED",
                trade_event_id=getattr(claim, "trade_event_id", None),
                decision_id=getattr(claim, "decision_id", None),
                evidence_event_id=getattr(claim, "evidence_event_id", None),
                detail_code=detail_code,
            )
    except Exception as exc:
        return {
            "state": "EVIDENCE_PERSISTENCE_FAILED",
            "reason": "RECONCILIATION_EVIDENCE_PERSISTENCE_FAILED",
            "detail": str(exc),
            "client_order_id": client_order_id,
            "resubmit_allowed": False,
        }
    return {
        "state": "UNRESOLVED_KEEP_QUARANTINED",
        "reason": str(reason),
        "client_order_id": client_order_id,
        "evidence_event_id": evidence_id,
        "resubmit_allowed": False,
    }


__all__ = ["reconcile_ambiguous_order"]
