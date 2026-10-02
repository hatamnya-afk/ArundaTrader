from cp49_management_authorization_source_binding_v0_1 import (
    build_capital_authorization_from_source,
)


ACCOUNT_ID = "740725837"


def _record():
    return {
        "authorization_id": "MGMT-AUTH-001",
        "account_id": ACCOUNT_ID,
        "capital_scope": "EXPLICIT_MANAGEMENT_SCOPE",
        "authorized_by": "MANAGEMENT",
        "authorized_at": "2026-10-02T00:00:00Z",
        "source": "MANAGEMENT_AUTHORIZATION",
    }


class Source:
    def __init__(self, record):
        self.record = record

    def read_authorization(self):
        return self.record


def test_binds_already_issued_authorization():
    evidence = build_capital_authorization_from_source(
        Source(_record()), expected_account_id=ACCOUNT_ID
    )
    assert evidence is not None
    assert evidence.account_id == ACCOUNT_ID
    assert evidence.authorization_id == "MGMT-AUTH-001"


def test_missing_source_record_fails_closed():
    assert (
        build_capital_authorization_from_source(
            Source(None), expected_account_id=ACCOUNT_ID
        )
        is None
    )


def test_account_mismatch_fails_closed():
    record = _record()
    record["account_id"] = "OTHER"
    assert (
        build_capital_authorization_from_source(
            Source(record), expected_account_id=ACCOUNT_ID
        )
        is None
    )


def test_source_exception_fails_closed():
    class BrokenSource:
        def read_authorization(self):
            raise RuntimeError("source unavailable")

    assert (
        build_capital_authorization_from_source(
            BrokenSource(), expected_account_id=ACCOUNT_ID
        )
        is None
    )


def test_plain_callable_source_is_supported():
    evidence = build_capital_authorization_from_source(
        _record, expected_account_id=ACCOUNT_ID
    )
    assert evidence is not None
