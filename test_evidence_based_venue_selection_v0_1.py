import pytest

from evidence_based_venue_selection_v0_1 import resolve_authoritative_venue


NOW = "2026-10-11T12:00:00Z"
MANDATE = {
    "decision": "AUTHORIZED",
    "provider": "TOOBIT",
    "issued_at": "2026-10-11T08:43:04Z",
    "expires_at": "2026-11-10T08:43:04Z",
    "allowed_markets": ["SPOT", "FUTURES"],
}
SELECTION = {
    "source": "AUTHORITATIVE_PER_INTENT_MARKET_POLICY",
    "decision": "SELECTED",
    "provider": "TOOBIT",
    "policy_version": "DIRECTIONAL_SPOT_LONG_FUTURES_SHORT_V0_1",
    "asset": "BTC/USDT",
    "venue": "FUTURES",
    "intent_id": "intent-123",
    "observed_at": NOW,
}
INSTRUMENT = {
    "source": "TOOBIT_READ_ONLY_INSTRUMENT_CONSTRAINTS",
    "provider": "TOOBIT",
    "asset": "BTC/USDT",
    "venue": "FUTURES",
    "intent_id": "intent-123",
    "instrument_id": "BTC-SWAP-USDT",
    "instrument_status": "TRADING",
    "policy_version": "DIRECTIONAL_SPOT_LONG_FUTURES_SHORT_V0_1",
    "observed_at": NOW,
}


def resolve(**overrides):
    args = {
        "asset": "BTC/USDT",
        "expected_intent_id": "intent-123",
        "mandate": MANDATE,
        "selection_evidence": SELECTION,
        "instrument_evidence": INSTRUMENT,
        "now": NOW,
        "max_evidence_age_seconds": 60,
    }
    args.update(overrides)
    return resolve_authoritative_venue(**args)


def test_selects_only_when_policy_and_provider_evidence_agree():
    result = resolve()
    assert result["status"] == "VENUE_SELECTED"
    assert result["venue"] == "FUTURES"
    assert result["instrument_id"] == "BTC-SWAP-USDT"


def test_standing_mandate_allowing_both_does_not_choose_a_venue():
    result = resolve(selection_evidence=None)
    assert result["status"] == "VENUE_SELECTION_BLOCKED"
    assert result["reason"] == "AUTHORITATIVE_PER_INTENT_MARKET_SELECTION_MISSING"
    assert result["venue"] is None


@pytest.mark.parametrize("field,value,reason", [
    ("venue", "SPOT", "TOOBIT_INSTRUMENT_VENUE_MISMATCH"),
    ("asset", "ETH/USDT", "TOOBIT_INSTRUMENT_ASSET_MISMATCH"),
    ("instrument_status", "HALTED", "TOOBIT_INSTRUMENT_NOT_TRADING"),
    ("intent_id", "other-intent", "TOOBIT_INSTRUMENT_INTENT_ID_MISMATCH"),
    ("policy_version", "other-policy", "TOOBIT_INSTRUMENT_POLICY_VERSION_MISMATCH"),
    ("instrument_id", "", "TOOBIT_INSTRUMENT_ID_MISSING"),
    ("observed_at", "2026-10-11T11:00:00Z", "TOOBIT_INSTRUMENT_EVIDENCE_STALE_OR_INVALID"),
])
def test_mismatched_or_stale_instrument_evidence_fails_closed(field, value, reason):
    evidence = dict(INSTRUMENT)
    evidence[field] = value
    result = resolve(instrument_evidence=evidence)
    assert result["status"] == "VENUE_SELECTION_BLOCKED"
    assert result["reason"] == reason
    assert result["venue"] is None


@pytest.mark.parametrize("field,value,reason", [
    ("venue", "MARGIN", "VENUE_SELECTION_VALUE_INVALID"),
    ("asset", "ETH/USDT", "VENUE_SELECTION_ASSET_MISMATCH"),
    ("provider", "OTHER", "VENUE_SELECTION_PROVIDER_MISMATCH"),
    ("intent_id", "other-intent", "VENUE_SELECTION_INTENT_ID_MISMATCH"),
    ("observed_at", "2026-10-11T11:00:00Z", "VENUE_SELECTION_EVIDENCE_STALE_OR_INVALID"),
])
def test_invalid_selection_evidence_fails_closed(field, value, reason):
    evidence = dict(SELECTION)
    evidence[field] = value
    result = resolve(selection_evidence=evidence)
    assert result["status"] == "VENUE_SELECTION_BLOCKED"
    assert result["reason"] == reason
    assert result["venue"] is None


def test_market_not_authorized_by_mandate_fails_closed():
    mandate = dict(MANDATE, allowed_markets=["SPOT"])
    result = resolve(mandate=mandate)
    assert result["reason"] == "VENUE_NOT_ALLOWED_BY_MANDATE"
    assert result["venue"] is None


def test_expired_mandate_fails_closed():
    mandate = dict(MANDATE, expires_at="2026-10-11T11:59:59Z")
    result = resolve(mandate=mandate)
    assert result["reason"] == "VENUE_SELECTION_MANDATE_OUTSIDE_VALIDITY"
    assert result["venue"] is None


def test_future_evidence_fails_closed():
    evidence = dict(SELECTION, observed_at="2026-10-11T12:00:01Z")
    result = resolve(selection_evidence=evidence)
    assert result["reason"] == "VENUE_SELECTION_EVIDENCE_STALE_OR_INVALID"
    assert result["venue"] is None


def test_selection_evidence_must_match_expected_intent():
    result = resolve(expected_intent_id="another-intent")
    assert result["status"] == "VENUE_SELECTION_BLOCKED"
    assert result["reason"] == "VENUE_SELECTION_INTENT_ID_MISMATCH"
    assert result["venue"] is None


def test_missing_expected_intent_blocks():
    result = resolve(expected_intent_id="")
    assert result["status"] == "VENUE_SELECTION_BLOCKED"
    assert result["reason"] == "VENUE_SELECTION_EXPECTED_INTENT_ID_INVALID"
