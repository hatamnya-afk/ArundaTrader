from cp49_canonical_decision_identity_v0_1 import build_canonical_decision_identity


def test_preserves_real_decision_identity():
    r = build_canonical_decision_identity({"decision_id":"D-001", "snapshot_id":"S-001", "asset":"BTC", "decision_timestamp_ms":1000})
    assert r.status == "PASS"
    assert r.identity.decision_id == "D-001"


def test_missing_decision_id_blocks():
    r = build_canonical_decision_identity({"snapshot_id":"S-001", "asset":"BTC", "decision_timestamp_ms":1000})
    assert r.status == "BLOCK"
    assert r.reason == "CANONICAL_DECISION_ID_MISSING"


def test_no_synthetic_identity_fields_are_accepted():
    r = build_canonical_decision_identity({"snapshot_id":"S-001", "asset":"BTC", "decision_timestamp_ms":1000, "intent_id":"I-1"})
    assert r.status == "BLOCK"
    assert r.reason == "CANONICAL_DECISION_ID_MISSING"
