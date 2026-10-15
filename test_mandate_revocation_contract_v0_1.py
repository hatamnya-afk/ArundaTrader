from datetime import datetime, timedelta, timezone

import pytest

from mandate_revocation_contract_v0_1 import evaluate_mandate_revocation_observation


def _mandate():
    return {"mandate_id": "MANDATE-1", "authorization_id": "MANDATE-1"}


def _observation(now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "mandate_id": "MANDATE-1",
        "status": "ACTIVE",
        "source": "MANAGEMENT_MANDATE_REGISTRY",
        "record_id": "record-1",
        "observed_at": now.isoformat(),
        "max_age_seconds": 60,
        "freshness_policy_id": "management-freshness-policy-v1",
    }


def test_fresh_active_status_is_accepted():
    now = datetime.now(timezone.utc)
    result = evaluate_mandate_revocation_observation(
        mandate=_mandate(), observation=_observation(now), now=now
    )
    assert result["revocation_state"] == "ACTIVE"
    assert result["mandate_id"] == "MANDATE-1"


def test_revoked_status_is_rejected():
    value = _observation()
    value["status"] = "REVOKED"
    with pytest.raises(ValueError, match="MANDATE_REVOKED"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=value)


def test_missing_observation_fails_closed():
    with pytest.raises(ValueError, match="MANDATE_REVOCATION_OBSERVATION_MISSING"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=None)


def test_mandate_identity_mismatch_fails_closed():
    value = _observation()
    value["mandate_id"] = "OTHER"
    with pytest.raises(ValueError, match="MANDATE_REVOCATION_IDENTITY_MISMATCH"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=value)


def test_stale_status_fails_closed():
    now = datetime.now(timezone.utc)
    value = _observation(now - timedelta(seconds=61))
    with pytest.raises(ValueError, match="MANDATE_REVOCATION_OBSERVATION_STALE"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=value, now=now)


def test_future_timestamp_fails_closed():
    now = datetime.now(timezone.utc)
    value = _observation(now + timedelta(seconds=1))
    with pytest.raises(ValueError, match="MANDATE_REVOCATION_TIMESTAMP_IN_FUTURE"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=value, now=now)


def test_missing_freshness_policy_fails_closed():
    value = _observation()
    value.pop("freshness_policy_id")
    with pytest.raises(ValueError, match="MANDATE_REVOCATION_FRESHNESS_POLICY_INVALID"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=value)


def test_test_source_fails_closed():
    value = _observation()
    value["source"] = "TEST"
    with pytest.raises(ValueError, match="MANDATE_REVOCATION_SOURCE_INVALID"):
        evaluate_mandate_revocation_observation(mandate=_mandate(), observation=value)
