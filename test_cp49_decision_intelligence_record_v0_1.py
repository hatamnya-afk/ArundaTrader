from cp49_decision_intelligence_record_v0_1 import (
    build_decision_intelligence_record,
)


def canonical_input():
    return {
        "decision_id": "D-001",
        "snapshot_id": "S-001",
        "decision_timestamp_ms": 1000,
        "knowledge_cutoff_ms": 900,
        "asset": "BTC",
        "direction": "LONG",
        "decision_state": "ACTIONABLE",
        "decision_score": 0.82,
        "decision_reason": "VALID_ACTIVE_SIGNAL",
        "layer_scores": {
            "fusion": 0.84,
            "score": 0.82,
            "risk": 0.91,
        },
        "selection_reasons": (
            "VALID_ACTIVE_SIGNAL",
            "risk approved",
        ),
        "rejection_reasons": (),
        "provenance": {
            "decision": "D-001",
            "risk": "R-001",
            "allocation": "A-001",
            "position_size": "P-001",
            "quantity": "RISK.position_quantity",
        },
    }


def test_builds_traceable_record_without_reconstructing_decision():
    result = build_decision_intelligence_record(canonical_input())
    assert result.status == "PASS"
    record = result.record
    assert record is not None
    assert record.decision_id == "D-001"
    assert record.snapshot_id == "S-001"
    assert record.layer_scores == (
        ("fusion", 0.84),
        ("risk", 0.91),
        ("score", 0.82),
    )
    assert record.selection_reasons == (
        "VALID_ACTIVE_SIGNAL",
        "risk approved",
    )


def test_missing_canonical_decision_id_blocks_instead_of_synthesizing():
    data = canonical_input()
    data.pop("decision_id")
    result = build_decision_intelligence_record(data)
    assert result.status == "BLOCK"
    assert result.reason == "CANONICAL_DECISION_ID_MISSING"


def test_preserves_actual_decision_reason_and_layer_scores():
    data = canonical_input()
    data["decision_reason"] = "REAL_DECISION_REASON"
    data["layer_scores"] = {"fusion": 0.77, "score": 0.73}
    result = build_decision_intelligence_record(data)
    assert result.status == "PASS"
    assert result.record.decision_reason == "REAL_DECISION_REASON"
    assert result.record.layer_scores == (("fusion", 0.77), ("score", 0.73))
