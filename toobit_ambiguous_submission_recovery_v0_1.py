"""Read-only Toobit recovery for one ambiguous order submission.

This path performs only a signed GET order lookup by the original client order
ID. It never submits, retries, cancels, or treats lookup failure/absence as
proof that a POST was not accepted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from exchange_execution_contract import CanonicalOrderRequest
from toobit_ambiguous_submission_outcome_bridge_v0_1 import (
    capture_reconciled_toobit_outcome,
)
from toobit_ambiguous_submission_reconciliation_v0_1 import (
    FOUND,
    INVALID_OBSERVATION,
    NOT_FOUND_UNRESOLVED,
    reconcile_ambiguous_submission,
)

LOOKUP_UNAVAILABLE = "LOOKUP_UNAVAILABLE"


def recover_ambiguous_toobit_submission(
    *,
    adapter: Any,
    request: CanonicalOrderRequest,
    venue: str,
    symbol: str,
    trade_event_id: str,
    stream_path: Path,
    observed_at: str | None = None,
    category: str = "USDT",
) -> dict[str, Any]:
    """Query one exact order by client ID and persist only an exact provider row.

    observed_at is the local observation timestamp for this GET response,
    not a timestamp claimed to have been supplied by Toobit.
    """
    if not isinstance(request, CanonicalOrderRequest):
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "CANONICAL_ORDER_REQUEST_INVALID",
            "safe_to_retry": False,
        }
    local_observed_at = observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed_observed_at = datetime.fromisoformat(local_observed_at.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "LOCAL_OBSERVATION_TIMESTAMP_INVALID",
            "safe_to_retry": False,
        }
    if parsed_observed_at.tzinfo is None or parsed_observed_at.utcoffset() is None:
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "LOCAL_OBSERVATION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE",
            "safe_to_retry": False,
        }

    client_order_id = request.intent_id
    if not isinstance(client_order_id, str) or not client_order_id.strip():
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "CLIENT_ORDER_ID_INVALID",
            "safe_to_retry": False,
        }
    if not isinstance(trade_event_id, str) or not trade_event_id.strip():
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "AUTHORITATIVE_TRADE_EVENT_ID_REQUIRED",
            "safe_to_retry": False,
        }
    normalized_venue = str(venue).strip().upper()
    if normalized_venue not in {"SPOT", "FUTURES"}:
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "VENUE_INVALID",
            "safe_to_retry": False,
        }
    if not isinstance(symbol, str) or not symbol.strip():
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "PROVIDER_SYMBOL_REQUIRED",
            "safe_to_retry": False,
        }
    if not callable(getattr(adapter, "_call", None)) or not callable(
        getattr(adapter, "_unwrap", None)
    ):
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "TOOBIT_ADAPTER_LOOKUP_INTERFACE_REQUIRED",
            "safe_to_retry": False,
        }

    path = (
        "/api/v1/spot/order"
        if normalized_venue == "SPOT"
        else "/api/v2/futures/order"
    )
    params: dict[str, Any] = {
        "symbol": symbol.strip(),
        "origClientOrderId": client_order_id.strip(),
    }
    if normalized_venue == "FUTURES":
        normalized_category = str(category).strip().upper()
        if normalized_category not in {"USDT", "USDC"}:
            return {
                "reconciliation_state": INVALID_OBSERVATION,
                "capture_state": "NOT_CAPTURED",
                "reason": "FUTURES_CATEGORY_INVALID",
                "safe_to_retry": False,
            }
        params["category"] = normalized_category

    try:
        response = adapter._call("GET", path, params=params, signed=True)
        row = adapter._unwrap(response)
    except Exception as exc:
        return {
            "reconciliation_state": LOOKUP_UNAVAILABLE,
            "capture_state": "NOT_CAPTURED",
            "reason": f"READ_ONLY_LOOKUP_FAILED:{type(exc).__name__}:{exc}",
            "safe_to_retry": False,
        }

    if not isinstance(row, Mapping):
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "PROVIDER_LOOKUP_ROW_INVALID",
            "safe_to_retry": False,
        }
    observed_client_id = row.get("clientOrderId")
    if not isinstance(observed_client_id, str) or observed_client_id != client_order_id:
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "PROVIDER_LOOKUP_CLIENT_ORDER_ID_MISMATCH",
            "safe_to_retry": False,
        }
    observed_symbol = row.get("symbol")
    if not isinstance(observed_symbol, str) or observed_symbol.strip().upper() != symbol.strip().upper():
        return {
            "reconciliation_state": INVALID_OBSERVATION,
            "capture_state": "NOT_CAPTURED",
            "reason": "PROVIDER_LOOKUP_SYMBOL_MISMATCH",
            "safe_to_retry": False,
        }

    reconciliation = reconcile_ambiguous_submission(
        client_order_id=client_order_id,
        open_orders=[],
        recent_orders=[row],
    )
    if reconciliation.get("state") != FOUND:
        return {
            "reconciliation_state": reconciliation.get("state", NOT_FOUND_UNRESOLVED),
            "capture_state": "NOT_CAPTURED",
            "reason": reconciliation.get("reason") or NOT_FOUND_UNRESOLVED,
            "safe_to_retry": False,
        }

    return capture_reconciled_toobit_outcome(
        request=request,
        reconciliation=reconciliation,
        trade_event_id=trade_event_id.strip(),
        observed_at=local_observed_at,
        stream_path=Path(stream_path),
    )


__all__ = ["LOOKUP_UNAVAILABLE", "recover_ambiguous_toobit_submission"]
