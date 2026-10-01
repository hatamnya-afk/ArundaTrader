from types import SimpleNamespace

from cp49_first_execution_evidence_contract_v0_1 import (
    AccountSignatureEvidence,
    RealCapitalAuthorizationEvidence,
    build_account_signature_evidence,
    validate_real_capital_authorization,
)


def _api_result():
    return SimpleNamespace(
        allowed=True,
        status="PASS",
        operation="api_key_check",
        data={"account_type": "SPOT"},
    )


def _account_observation():
    return SimpleNamespace(
        account=SimpleNamespace(
            account_id="acct-1",
            account_type="SPOT",
        )
    )


def test_account_signature_requires_authenticated_identity_correlation():
    evidence = build_account_signature_evidence(
        api_key_result=_api_result(),
        account_observation=_account_observation(),
        evidence_id="evidence-1",
        observed_at="2026-10-01T00:00:00+00:00",
    )
    assert isinstance(evidence, AccountSignatureEvidence)
    assert evidence.validate() is True


def test_hmac_or_api_key_success_without_account_identity_does_not_prove_signature():
    account = SimpleNamespace(
        account=SimpleNamespace(
            account_id=None,
            account_type="SPOT",
        )
    )
    evidence = build_account_signature_evidence(
        api_key_result=_api_result(),
        account_observation=account,
        evidence_id="evidence-1",
        observed_at="2026-10-01T00:00:00+00:00",
    )
    assert evidence is None


def test_capital_authorization_requires_explicit_management_record():
    evidence = RealCapitalAuthorizationEvidence(
        authorization_id="auth-1",
        account_id="acct-1",
        capital_scope="FIRST_EXECUTION",
        authorized_by="MANAGEMENT",
        authorized_at="2026-10-01T00:00:00+00:00",
        source="MANAGEMENT_AUTHORIZATION",
    )
    assert validate_real_capital_authorization(evidence, account_id="acct-1") is True


def test_capital_authorization_cannot_be_inferred_from_account_id():
    assert validate_real_capital_authorization(None, account_id="acct-1") is False


def test_capital_authorization_is_bound_to_account():
    evidence = RealCapitalAuthorizationEvidence(
        authorization_id="auth-1",
        account_id="acct-1",
        capital_scope="FIRST_EXECUTION",
        authorized_by="MANAGEMENT",
        authorized_at="2026-10-01T00:00:00+00:00",
        source="MANAGEMENT_AUTHORIZATION",
    )
    assert validate_real_capital_authorization(evidence, account_id="acct-2") is False
