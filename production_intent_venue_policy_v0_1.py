"""Authoritative per-intent venue policy and read-only Toobit evidence producer.

Conservative default semantics:
- LONG opens a base-asset position through SPOT.
- SHORT opens a short position through USDT-settled FUTURES.
This is explicit policy, not inference from the standing mandate. The policy
must still pass the standing mandate and fresh provider metadata checks.
No order submission or account mutation occurs here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


POLICY_SOURCE = "AUTHORITATIVE_PER_INTENT_MARKET_POLICY"
INSTRUMENT_SOURCE = "TOOBIT_READ_ONLY_INSTRUMENT_CONSTRAINTS"
POLICY_VERSION = "DIRECTIONAL_SPOT_LONG_FUTURES_SHORT_V0_1"


def select_venue_for_intent(*, asset: str, direction: str, intent_id: str, observed_at: str) -> dict[str, Any]:
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("VENUE_POLICY_ASSET_INVALID")
    if not isinstance(intent_id, str) or not intent_id.strip():
        raise ValueError("VENUE_POLICY_INTENT_ID_INVALID")
    normalized = str(direction).strip().upper()
    if normalized == "LONG":
        venue = "SPOT"
    elif normalized == "SHORT":
        venue = "FUTURES"
    else:
        raise ValueError("VENUE_POLICY_DIRECTION_UNSUPPORTED")
    # Ensure the timestamp is offset-aware and canonical UTC.
    parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("VENUE_POLICY_TIMESTAMP_INVALID")
    timestamp = parsed.astimezone(timezone.utc).isoformat()
    return {
        "source": POLICY_SOURCE,
        "policy_version": POLICY_VERSION,
        "decision": "SELECTED",
        "provider": "TOOBIT",
        "asset": asset,
        "venue": venue,
        "intent_id": intent_id,
        "observed_at": timestamp,
    }


def produce_authoritative_venue_evidence(
    *,
    request: Any,
    adapter: Any,
    observed_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select per-intent venue and read matching instrument status from adapter."""
    if adapter is None:
        raise RuntimeError("TOOBIT_ADAPTER_UNAVAILABLE")
    direction = str(getattr(request, "direction", "")).strip().upper()
    if direction not in {"LONG", "SHORT"}:
        raise ValueError("VENUE_POLICY_DIRECTION_UNSUPPORTED")
    # Resolve the deterministic venue before any provider read, but timestamp
    # the evidence only after the instrument metadata has actually been read.
    venue = "SPOT" if direction == "LONG" else "FUTURES"
    if venue == "SPOT":
        result = adapter.trading_constraints(request.asset)
    else:
        result = adapter.futures_trading_constraints(request.asset)
    if not getattr(result, "allowed", False) or not isinstance(getattr(result, "data", None), Mapping):
        reason = getattr(result, "reason", None) or getattr(result, "error", None) or "TOOBIT_INSTRUMENT_READ_FAILED"
        raise RuntimeError(f"TOOBIT_INSTRUMENT_READ_FAILED:{reason}")
    row = result.data
    instrument_id = row.get("symbol")
    status = str(row.get("status", "")).strip().upper()
    if not isinstance(instrument_id, str) or not instrument_id.strip():
        raise RuntimeError("TOOBIT_INSTRUMENT_ID_MISSING")
    if status != "TRADING":
        raise RuntimeError("TOOBIT_INSTRUMENT_NOT_TRADING")
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    selection = select_venue_for_intent(
        asset=request.asset,
        direction=direction,
        intent_id=request.intent_id,
        observed_at=timestamp,
    )
    instrument = {
        "source": INSTRUMENT_SOURCE,
        "provider": "TOOBIT",
        "asset": request.asset,
        "venue": venue,
        "instrument_id": instrument_id.strip().upper(),
        "instrument_status": status,
        "observed_at": selection["observed_at"],
        "policy_version": POLICY_VERSION,
    }
    return selection, instrument


__all__ = [
    "POLICY_SOURCE",
    "INSTRUMENT_SOURCE",
    "POLICY_VERSION",
    "select_venue_for_intent",
    "produce_authoritative_venue_evidence",
]
