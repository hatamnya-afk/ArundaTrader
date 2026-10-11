"""Evidence-based, fail-closed venue selection for the production order path.

This resolver never chooses SPOT/FUTURES from a standing mandate that permits
both. It requires an authoritative per-intent selection plus fresh, matching
read-only provider instrument evidence. It performs no network or write calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Mapping
from typing import Any


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _asset(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().upper().replace("-", "/").split("/", 1)[0]


def resolve_authoritative_venue(
    *,
    asset: str,
    expected_intent_id: str,
    mandate: Mapping[str, Any],
    selection_evidence: Mapping[str, Any] | None,
    instrument_evidence: Mapping[str, Any] | None,
    now: str,
    max_evidence_age_seconds: int,
) -> dict[str, Any]:
    """Resolve one venue only when every independent authority agrees.

    Required selection evidence:
      source=AUTHORITATIVE_PER_INTENT_MARKET_POLICY, decision=SELECTED,
      provider=TOOBIT, asset, venue, intent_id, observed_at.
    Required instrument evidence:
      source=TOOBIT_READ_ONLY_INSTRUMENT_CONSTRAINTS, provider=TOOBIT,
      asset, venue, instrument_id, instrument_status=TRADING, observed_at.
    """
    def blocked(reason: str) -> dict[str, Any]:
        return {"status": "VENUE_SELECTION_BLOCKED", "venue": None, "reason": reason}

    current = _instant(now)
    if current is None:
        return blocked("VENUE_SELECTION_REFERENCE_TIME_INVALID")
    if not isinstance(max_evidence_age_seconds, int) or isinstance(max_evidence_age_seconds, bool) or max_evidence_age_seconds <= 0:
        return blocked("VENUE_SELECTION_FRESHNESS_POLICY_INVALID")
    if not isinstance(mandate, Mapping):
        return blocked("VENUE_SELECTION_MANDATE_MISSING")
    if (
        mandate.get("decision") != "AUTHORIZED"
        or mandate.get("provider") != "TOOBIT"
        or mandate.get("environment") != "REAL_PRODUCTION"
        or not isinstance(mandate.get("mandate_id"), str)
        or not mandate["mandate_id"].strip()
        or not isinstance(mandate.get("authorized_by"), str)
        or not mandate["authorized_by"].strip()
        or not isinstance(mandate.get("authorization_source"), str)
        or not mandate["authorization_source"].strip()
    ):
        return blocked("VENUE_SELECTION_MANDATE_INVALID")
    issued = _instant(mandate.get("issued_at"))
    expires = _instant(mandate.get("expires_at"))
    if issued is None or expires is None or not issued <= current < expires:
        return blocked("VENUE_SELECTION_MANDATE_OUTSIDE_VALIDITY")
    allowed = mandate.get("allowed_markets")
    if not isinstance(allowed, list) or not allowed or any(v not in {"SPOT", "FUTURES"} for v in allowed):
        return blocked("VENUE_SELECTION_MANDATE_MARKETS_INVALID")

    if not isinstance(expected_intent_id, str) or not expected_intent_id.strip():
        return blocked("VENUE_SELECTION_EXPECTED_INTENT_ID_INVALID")

    if not isinstance(selection_evidence, Mapping):
        return blocked("AUTHORITATIVE_PER_INTENT_MARKET_SELECTION_MISSING")
    if selection_evidence.get("source") != "AUTHORITATIVE_PER_INTENT_MARKET_POLICY" or selection_evidence.get("decision") != "SELECTED":
        return blocked("AUTHORITATIVE_PER_INTENT_MARKET_SELECTION_INVALID")
    if selection_evidence.get("provider") != "TOOBIT":
        return blocked("VENUE_SELECTION_PROVIDER_MISMATCH")
    if _asset(selection_evidence.get("asset")) != _asset(asset):
        return blocked("VENUE_SELECTION_ASSET_MISMATCH")
    if not isinstance(selection_evidence.get("intent_id"), str) or not selection_evidence["intent_id"].strip():
        return blocked("VENUE_SELECTION_INTENT_ID_MISSING")
    if selection_evidence["intent_id"] != expected_intent_id:
        return blocked("VENUE_SELECTION_INTENT_ID_MISMATCH")
    venue = selection_evidence.get("venue")
    if venue not in {"SPOT", "FUTURES"}:
        return blocked("VENUE_SELECTION_VALUE_INVALID")
    if venue not in allowed:
        return blocked("VENUE_NOT_ALLOWED_BY_MANDATE")

    selected_at = _instant(selection_evidence.get("observed_at"))
    if selected_at is None or selected_at > current or (current - selected_at).total_seconds() > max_evidence_age_seconds:
        return blocked("VENUE_SELECTION_EVIDENCE_STALE_OR_INVALID")

    if not isinstance(instrument_evidence, Mapping):
        return blocked("TOOBIT_INSTRUMENT_EVIDENCE_MISSING")
    if instrument_evidence.get("source") != "TOOBIT_READ_ONLY_INSTRUMENT_CONSTRAINTS":
        return blocked("TOOBIT_INSTRUMENT_EVIDENCE_SOURCE_INVALID")
    if instrument_evidence.get("provider") != "TOOBIT":
        return blocked("TOOBIT_INSTRUMENT_PROVIDER_MISMATCH")
    if _asset(instrument_evidence.get("asset")) != _asset(asset):
        return blocked("TOOBIT_INSTRUMENT_ASSET_MISMATCH")
    if instrument_evidence.get("venue") != venue:
        return blocked("TOOBIT_INSTRUMENT_VENUE_MISMATCH")
    if instrument_evidence.get("intent_id") != expected_intent_id:
        return blocked("TOOBIT_INSTRUMENT_INTENT_ID_MISMATCH")
    if instrument_evidence.get("policy_version") != selection_evidence.get("policy_version"):
        return blocked("TOOBIT_INSTRUMENT_POLICY_VERSION_MISMATCH")
    instrument_id = instrument_evidence.get("instrument_id")
    if not isinstance(instrument_id, str) or not instrument_id.strip():
        return blocked("TOOBIT_INSTRUMENT_ID_MISSING")
    if instrument_evidence.get("instrument_status") != "TRADING":
        return blocked("TOOBIT_INSTRUMENT_NOT_TRADING")
    instrument_at = _instant(instrument_evidence.get("observed_at"))
    if instrument_at is None or instrument_at > current or (current - instrument_at).total_seconds() > max_evidence_age_seconds:
        return blocked("TOOBIT_INSTRUMENT_EVIDENCE_STALE_OR_INVALID")

    return {
        "status": "VENUE_SELECTED",
        "venue": venue,
        "provider": "TOOBIT",
        "asset": _asset(asset),
        "intent_id": selection_evidence["intent_id"],
        "instrument_id": instrument_id,
        "selection_observed_at": selection_evidence["observed_at"],
        "instrument_observed_at": instrument_evidence["observed_at"],
        "provenance": "AUTHORITATIVE_POLICY_AND_READ_ONLY_PROVIDER_EVIDENCE",
    }


__all__ = ["resolve_authoritative_venue"]
