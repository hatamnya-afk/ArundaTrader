"""Fail-closed reconciliation policy for ambiguous provider submission outcomes.

This module does not make network calls and never retries or resubmits. It
classifies already-observed provider order rows by the exact client order ID.
An absent row is NOT proof that the provider did not accept the POST.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

FOUND = "FOUND"
NOT_FOUND_UNRESOLVED = "NOT_FOUND_UNRESOLVED"
CONFLICT = "CONFLICT"
INVALID_OBSERVATION = "INVALID_OBSERVATION"


def reconcile_ambiguous_submission(
    *,
    client_order_id: str,
    open_orders: Sequence[Mapping[str, Any]],
    recent_orders: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify read-only lookup evidence without ever declaring safe-to-retry."""
    if not isinstance(client_order_id, str) or not client_order_id.strip():
        return {"state": INVALID_OBSERVATION, "reason": "CLIENT_ORDER_ID_INVALID", "safe_to_retry": False}
    if not isinstance(open_orders, Sequence) or isinstance(open_orders, (str, bytes)):
        return {"state": INVALID_OBSERVATION, "reason": "OPEN_ORDERS_INVALID", "safe_to_retry": False}
    if not isinstance(recent_orders, Sequence) or isinstance(recent_orders, (str, bytes)):
        return {"state": INVALID_OBSERVATION, "reason": "RECENT_ORDERS_INVALID", "safe_to_retry": False}

    matches: dict[str, Mapping[str, Any]] = {}
    for source, rows in (("OPEN", open_orders), ("RECENT", recent_orders)):
        for row in rows:
            if not isinstance(row, Mapping):
                return {"state": INVALID_OBSERVATION, "reason": f"{source}_ORDER_ROW_INVALID", "safe_to_retry": False}
            observed_id = row.get("clientOrderId")
            if observed_id is None:
                continue
            if not isinstance(observed_id, str):
                return {"state": INVALID_OBSERVATION, "reason": "OBSERVED_CLIENT_ORDER_ID_INVALID", "safe_to_retry": False}
            if observed_id == client_order_id.strip():
                order_id = row.get("orderId")
                identity = str(order_id) if order_id is not None else "CLIENT:" + observed_id
                prior = matches.get(identity)
                if prior is not None and dict(prior) != dict(row):
                    return {
                        "state": CONFLICT,
                        "reason": "CONFLICTING_PROVIDER_FACTS_FOR_SAME_ORDER_ID",
                        "matches": (prior, row),
                        "safe_to_retry": False,
                    }
                matches[identity] = row

    if len(matches) > 1:
        return {
            "state": CONFLICT,
            "reason": "MULTIPLE_PROVIDER_ORDERS_MATCH_CLIENT_ORDER_ID",
            "matches": tuple(matches.values()),
            "safe_to_retry": False,
        }
    if len(matches) == 1:
        return {
            "state": FOUND,
            "reason": "EXACT_CLIENT_ORDER_ID_MATCH",
            "order": next(iter(matches.values())),
            "safe_to_retry": False,
        }
    return {
        "state": NOT_FOUND_UNRESOLVED,
        "reason": "ABSENCE_DOES_NOT_PROVE_POST_WAS_NOT_ACCEPTED",
        "safe_to_retry": False,
    }


__all__ = ["FOUND", "NOT_FOUND_UNRESOLVED", "CONFLICT", "INVALID_OBSERVATION", "reconcile_ambiguous_submission"]
