import pytest

from approved_valuation_policy_source_contract_v0_1 import (
    validate_approved_valuation_policy_evidence,
)


def valid_policy():
    return {
        "approval_state": "APPROVED",
        "policy_id": "toobit-dual-market-valuation",
        "policy_version": "v2",
        "approval_id": "management-approval-ref-001",
        "approved_by": "authorized-management-role",
        "approval_source": "git:management/valuation-policy-approval",
        "approved_at": "2026-10-14T17:00:00Z",
        "effective_from": "2026-10-14T17:00:00Z",
        "effective_until": "2026-10-15T17:00:00Z",
        "approved_rate_sources": {
            "USDT": {"source": "APPROVED_BASE_CURRENCY_RULE", "source_reference": "git:policy/usdt-base-rate"},
            "USDC": {"source": "APPROVED_USDC_USDT_RATE_SOURCE", "source_reference": "https://rates.example.invalid/policy-reference"},
        },
    }


def test_valid_policy_evidence_does_not_claim_authenticity():
    result = validate_approved_valuation_policy_evidence(valid_policy(), valuation_observed_at="2026-10-14T18:00:00Z")
    assert result["policy_validation"] == "VALID"
    assert result["policy_id"] == "toobit-dual-market-valuation"
    assert result["policy_version"] == "v2"
    assert result["reporting_currency"] == "USDT"
    assert set(result["supported_currencies"]) == {"USDT", "USDC"}
    assert result["approval_authenticity"] == "UPSTREAM_AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize("evidence", [None, {}, {"approval_state": "PENDING"}])
def test_missing_or_unapproved_policy_blocks(evidence):
    with pytest.raises(ValueError):
        validate_approved_valuation_policy_evidence(evidence, valuation_observed_at="2026-10-14T18:00:00Z")


@pytest.mark.parametrize("field", ["policy_id", "policy_version", "approval_id", "approved_by", "approval_source", "approved_at", "effective_from", "effective_until"])
def test_missing_metadata_blocks(field):
    row = valid_policy()
    row[field] = ""
    with pytest.raises(ValueError):
        validate_approved_valuation_policy_evidence(row, valuation_observed_at="2026-10-14T18:00:00Z")


def test_observation_outside_effective_window_blocks():
    with pytest.raises(ValueError, match="VALUATION_POLICY_NOT_EFFECTIVE_AT_OBSERVATION"):
        validate_approved_valuation_policy_evidence(valid_policy(), valuation_observed_at="2026-10-16T18:00:00Z")


def test_naive_timestamp_blocks():
    with pytest.raises(ValueError, match="VALUATION_OBSERVATION_TIMESTAMP_INVALID"):
        validate_approved_valuation_policy_evidence(valid_policy(), valuation_observed_at="2026-10-14T18:00:00")


@pytest.mark.parametrize("rates", [None, {}, {"USDT": {}}, {"USDT": {}, "BTC": {}}])
def test_both_currency_rate_sources_required(rates):
    row = valid_policy()
    row["approved_rate_sources"] = rates
    with pytest.raises(ValueError, match="VALUATION_POLICY_USDT_USDC_RATE_SOURCES_REQUIRED"):
        validate_approved_valuation_policy_evidence(row, valuation_observed_at="2026-10-14T18:00:00Z")


def test_rate_source_reference_must_be_traceable():
    row = valid_policy()
    row["approved_rate_sources"]["USDC"]["source_reference"] = "guess"
    with pytest.raises(ValueError, match="VALUATION_POLICY_RATE_SOURCE_REFERENCE_INVALID"):
        validate_approved_valuation_policy_evidence(row, valuation_observed_at="2026-10-14T18:00:00Z")
