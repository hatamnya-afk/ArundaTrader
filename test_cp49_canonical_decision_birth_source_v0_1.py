from cp49_canonical_decision_birth_source_v0_1 import (
    propagate_canonical_decision_id,
    require_canonical_decision_birth,
)


def valid_event():
    return {
        "decision_id": "REAL-DECISION-001",
        "asset": "BTC",
        "decision_timestamp_ms": 1760000000000,
        "snapshot_id": "RS-real-snapshot",
        "source": "REAL_DECISION_BIRTH",
    }


def test_real_birth_identity_is_preserved():
    event = valid_event()
    bound = require_canonical_decision_birth(event)

    assert bound["decision_id"] == "REAL-DECISION-001"
    assert propagate_canonical_decision_id(event) == "REAL-DECISION-001"


def test_missing_identity_fails_closed():
    event = valid_event()
    event.pop("decision_id")

    try:
        require_canonical_decision_birth(event)
    except ValueError as exc:
        assert str(exc) == (
            "CANONICAL_DECISION_BIRTH_FIELDS_MISSING:decision_id"
        )
    else:
        raise AssertionError("missing decision_id must fail closed")


def test_blank_identity_fails_closed():
    event = valid_event()
    event["decision_id"] = "   "

    try:
        require_canonical_decision_birth(event)
    except ValueError as exc:
        assert str(exc) == (
            "CANONICAL_DECISION_ID_MISSING_AT_BIRTH_SOURCE"
        )
    else:
        raise AssertionError("blank decision_id must fail closed")


def test_identity_is_not_derived_from_snapshot():
    event = valid_event()
    event["decision_id"] = "AUTHORITATIVE-ID-7"

    bound = require_canonical_decision_birth(event)

    assert bound["decision_id"] == "AUTHORITATIVE-ID-7"
    assert bound["decision_id"] != event["snapshot_id"]


def test_non_mapping_fails_closed():
    try:
        require_canonical_decision_birth(None)
    except ValueError as exc:
        assert str(exc) == "CANONICAL_DECISION_BIRTH_INPUT_INVALID"
    else:
        raise AssertionError("non-mapping input must fail closed")
