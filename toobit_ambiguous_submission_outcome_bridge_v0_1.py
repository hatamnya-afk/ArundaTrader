"""Pure bridge from Toobit reconciliation decisions to outcome evidence.

Consumes only already-observed lookup results. It performs no network calls,
never retries, and persists an order observation only for an exact FOUND result.
Unresolved/conflicting/invalid lookup states remain explicit and are not
misrepresented as provider order facts.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from exchange_execution_contract import CanonicalOrderRequest
from toobit_ambiguous_submission_reconciliation_v0_1 import (
    CONFLICT,
    FOUND,
    INVALID_OBSERVATION,
    NOT_FOUND_UNRESOLVED,
)
from toobit_order_observation_normalizer_v0_1 import (
    capture_toobit_read_only_order_observation,
)

_NON_FOUND_STATES = frozenset({CONFLICT, INVALID_OBSERVATION, NOT_FOUND_UNRESOLVED})


def capture_reconciled_toobit_outcome(
    *,
    request: CanonicalOrderRequest,
    reconciliation: Mapping[str, Any],
    trade_event_id: str,
    observed_at: str,
    stream_path: Path,
) -> dict[str, Any]:
    """Persist the exact provider row only when reconciliation state is FOUND."""
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_INVALID")
    if not isinstance(reconciliation, Mapping):
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "RECONCILIATION_RESULT_INVALID",
            "safe_to_retry": False,
        }

    state = reconciliation.get("state")
    if state != FOUND:
        if state not in _NON_FOUND_STATES:
            state = INVALID_OBSERVATION
            reason = "RECONCILIATION_STATE_INVALID"
        else:
            reason = reconciliation.get("reason") or state
        return {
            "reconciliation_state": state,
            "capture_state": "NOT_CAPTURED",
            "reason": reason,
            "safe_to_retry": False,
        }

    if reconciliation.get("safe_to_retry") is not False:
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "RECONCILIATION_RETRY_POLICY_NOT_FAIL_CLOSED",
            "safe_to_retry": False,
        }
    order = reconciliation.get("order")
    if not isinstance(order, Mapping):
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "FOUND_ORDER_ROW_INVALID",
            "safe_to_retry": False,
        }

    captured = capture_toobit_read_only_order_observation(
        request=request,
        provider_order=order,
        trade_event_id=trade_event_id,
        observed_at=observed_at,
        stream_path=Path(stream_path),
    )
    return {
        "reconciliation_state": FOUND,
        "capture_state": captured.get("state", "PERSISTENCE_FAILED"),
        "reason": captured.get("reason"),
        "record": captured.get("record"),
        "event_id": captured.get("event_id"),
        "path": captured.get("path"),
        "safe_to_retry": False,
    }


__all__ = ["capture_reconciled_toobit_outcome"]
