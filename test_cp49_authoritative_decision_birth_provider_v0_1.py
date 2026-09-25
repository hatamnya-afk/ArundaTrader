from cp49_canonical_decision_birth_source_v0_1 import (
    read_authoritative_birth,
)


class RealProvider:
    def get_decision_birth(
        self,
        *,
        asset,
        snapshot_id,
        decision_timestamp_ms,
    ):
        return {
            "decision_id": "REAL-AUTHORITATIVE-001",
            "asset": asset,
            "snapshot_id": snapshot_id,
            "decision_timestamp_ms": decision_timestamp_ms,
            "source": "AUTHORITATIVE_DECISION_SOURCE",
        }


class MissingProvider:
    def get_decision_birth(
        self,
        *,
        asset,
        snapshot_id,
        decision_timestamp_ms,
    ):
        return {
            "asset": asset,
            "snapshot_id": snapshot_id,
            "decision_timestamp_ms": decision_timestamp_ms,
            "source": "AUTHORITATIVE_DECISION_SOURCE",
        }


def test_authoritative_source_preserves_existing_id():
    event = read_authoritative_birth(
        RealProvider(),
        asset="BTC",
        snapshot_id="RS-REAL",
        decision_timestamp_ms=1760000000000,
    )
    assert event["decision_id"] == "REAL-AUTHORITATIVE-001"


def test_missing_provider_fails_closed():
    try:
        read_authoritative_birth(
            None,
            asset="BTC",
            snapshot_id="RS-REAL",
            decision_timestamp_ms=1760000000000,
        )
    except RuntimeError as exc:
        assert str(exc) == "CANONICAL_DECISION_BIRTH_PROVIDER_MISSING"
    else:
        raise AssertionError("missing provider must fail closed")


def test_provider_without_identity_fails_closed():
    try:
        read_authoritative_birth(
            MissingProvider(),
            asset="BTC",
            snapshot_id="RS-REAL",
            decision_timestamp_ms=1760000000000,
        )
    except RuntimeError as exc:
        assert str(exc) == (
            "CANONICAL_DECISION_ID_MISSING_FROM_AUTHORITATIVE_SOURCE"
        )
    else:
        raise AssertionError("missing authoritative identity must fail closed")
