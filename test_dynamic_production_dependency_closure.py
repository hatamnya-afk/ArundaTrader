from pathlib import Path


ROOT = Path(__file__).resolve().parent

REQUIRED_DYNAMIC_PRODUCTION_FILES = (
    "production_universe_contract_v0_1.py",
    "dynamic_opportunity_universe_boundary_v0_1.py",
    "opportunity_engine.py",
    "dynamic_market_data_boundary_v0_1.py",
    "public_market_data_kucoin.py",
    "public_market_data_failover_v0.1.py",
    "dynamic_signal_semantic_layer.py",
    "signal_logic.py",
    "dynamic_validation_boundary_v0_1.py",
    "signal_validator.py",
    "dynamic_news_boundary_v0_1.py",
    "news_arm_v0_1.py",
    "information_contract_v0_1.py",
    "dynamic_social_boundary_v0_1.py",
    "social_arm_v0_1.py",
    "dynamic_fusion_boundary_v0_1.py",
    "fusion_engine.py",
    "dynamic_score_contract_boundary_v0_1.py",
    "score_producer.py",
    "runtime_feature_producer.py",
    "feature_contract.py",
    "market_state_engine.py",
    "market_regime_contract.py",
    "dynamic_decision_contract_boundary_v0_1.py",
    "decision_engine.py",
    "dynamic_risk_contract_boundary_v0_1.py",
    "risk_engine.py",
    "dynamic_trade_gate_contract_boundary_v0_1.py",
    "trade_gate_engine.py",
)


def test_dynamic_production_dependency_closure_is_present():
    missing = [name for name in REQUIRED_DYNAMIC_PRODUCTION_FILES if not (ROOT / name).is_file()]
    assert not missing, "Missing dynamic production dependencies: " + ", ".join(missing)


def test_market_data_store_paths_are_checkout_relative():
    kucoin_source = (ROOT / "public_market_data_kucoin.py").read_text(encoding="utf-8-sig")
    store_source = (ROOT / "local_canonical_store_v0.1.py").read_text(encoding="utf-8-sig")
    assert 'PROJECT_ROOT = Path(__file__).resolve().parent' in kucoin_source
    assert 'STORE_PATH = PROJECT_ROOT / "local_canonical_store_v0.1.py"' in kucoin_source
    assert 'PROJECT_ROOT = Path(__file__).resolve().parent' in store_source
    assert r"C:\Users\ASUS\ArundaTrader" not in kucoin_source
    assert r"C:\Users\ASUS\ArundaTrader" not in store_source
