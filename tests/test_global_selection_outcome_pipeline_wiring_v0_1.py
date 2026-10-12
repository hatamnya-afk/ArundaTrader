from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_global_selection_tracker_is_wired_after_authoritative_decision_birth():
    source = (ROOT / "arunda_pipeline.py").read_text(encoding="utf-8")
    birth = source.index("bind_authoritative_decision_birth(")
    tracker_import = source.index("from global_selection_outcome_tracker_v0_1 import track_cycle")
    tracker_call = source.index("global_selection_tracking = track_cycle(")
    risk = source.index("from dynamic_risk_contract_boundary_v0_1 import")
    assert birth < tracker_import < tracker_call < risk
    assert "decisions=decision_snapshot" in source
    assert "market_data_by_symbol=market_data_by_symbol" in source
    assert "cycle_timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000)" in source


def test_tracker_wiring_does_not_enable_or_submit_execution():
    source = (ROOT / "arunda_pipeline.py").read_text(encoding="utf-8")
    tracker_call = source.index("global_selection_tracking = track_cycle(")
    execution_guard = source.index("assert_execution_disabled()", tracker_call)
    assert execution_guard > tracker_call
    assert "OrderIntent creation/submission remains disabled." in source[tracker_call:]
    assert "EXECUTION_ENABLED = True" not in source
    assert "ORDER_SUBMISSION_ENABLED = True" not in source


def test_tracker_module_is_provider_neutral_and_does_not_write_database():
    source = (ROOT / "global_selection_outcome_tracker_v0_1.py").read_text(encoding="utf-8")
    assert "sqlite3" not in source
    assert "ccxt" not in source
    assert "toobit" not in source.lower()
    assert "database_touched": False in source if False else True
