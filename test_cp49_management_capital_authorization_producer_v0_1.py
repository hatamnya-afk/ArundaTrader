"""Focused tests for the CP49 Management authorization evidence boundary."""

from __future__ import annotations

from cp49_first_execution_evidence_contract_v0_1 import (
    RealCapitalAuthorizationEvidence,
)
from cp49_management_capital_authorization_producer_v0_1 import (
    build_management_capital_authorization_evidence,
)


def _authorized_record() -> dict[str, str]:
    return {
        "authorization_id": "management-auth-1",
        "account_id": "740725837",
        "capital_scope": "REAL_CAPITAL:SPOT",
        "authorized_by": "MANAGEMENT",
        "authorized_at": "2026-10-02T00:00:00+00:00",
        "source": "MANAGEMENT_AUTHORIZATION",
    }


def test_accepts_already_issued_management_authorization() -> None:
    evidence = build_management_capital_authorization_evidence(
        _authorized_record(),
        expected_account_id="740725837",
    )

    assert isinstance(evidence, RealCapitalAuthorizationEvidence)
    assert evidence.validate()
    assert evidence.account_id == "740725837"
    assert evidence.source == "MANAGEMENT_AUTHORIZATION"


def test_rejects_account_mismatch() -> None:
    assert (
        build_management_capital_authorization_evidence(
            _authorized_record(),
            expected_account_id="different-account",
        )
        is None
    )


def test_rejects_non_management_issuer() -> None:
    record = _authorized_record()
    record["authorized_by"] = "CONFIGURATION"

    assert (
        build_management_capital_authorization_evidence(
            record,
            expected_account_id="740725837",
        )
        is None
    )


def test_rejects_non_authorization_source() -> None:
    record = _authorized_record()
    record["source"] = "AUTHENTICATED_ACCOUNT_READ"

    assert (
        build_management_capital_authorization_evidence(
            record,
            expected_account_id="740725837",
        )
        is None
    )


def test_rejects_missing_authorization_record() -> None:
    assert (
        build_management_capital_authorization_evidence(
            None,
            expected_account_id="740725837",
        )
        is None
    )
