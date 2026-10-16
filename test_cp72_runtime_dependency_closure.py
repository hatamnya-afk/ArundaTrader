"""CP72 dynamic runtime dependency closure checks.

This is a source/contract audit only. It does not run the pipeline, access the
network, open the production database, or enable execution.
"""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
RUNTIME_MODULES = [
    "production_universe_contract_v0_1.py",
    "production_universe_binding.py",
    "production_signal_input_boundary_v0_1.py",
    "dynamic_opportunity_universe_boundary_v0_1.py",
    "opportunity_engine.py",
    "dynamic_market_data_boundary_v0_1.py",
    "public_market_data_kucoin.py",
    "public_market_data_failover_v0.1.py",
    "local_canonical_store_v0.1.py",
    "indicator_engine.py",
    "market_structure_engine.py",
    "feature_engine.py",
    "feature_contract.py",
    "dynamic_signal_semantic_layer.py",
    "dynamic_validation_boundary_v0_1.py",
    "signal_validator.py",
    "signal_engine.py",
    "signal_contract.py",
    "market_regime.py",
    "market_regime_engine.py",
    "signal_logic.py",
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
    "market_state_engine.py",
    "market_regime_contract.py",
    "dynamic_decision_contract_boundary_v0_1.py",
    "decision_engine.py",
    "decision_contract.py",
    "dynamic_risk_contract_boundary_v0_1.py",
    "risk_engine.py",
    "risk_contract.py",
    "dynamic_trade_gate_contract_boundary_v0_1.py",
    "trade_gate_engine.py",
    "market_analysis_engine.py"
]


class CP72RuntimeDependencyClosureTests(unittest.TestCase):
    def test_all_dynamic_runtime_modules_exist_and_compile(self):
        missing = [name for name in RUNTIME_MODULES if not (ROOT / name).is_file()]
        self.assertEqual(missing, [], f"missing CP72 runtime dependencies: {missing}")

        failures = []
        for name in RUNTIME_MODULES:
            path = ROOT / name
            try:
                source = path.read_text(encoding="utf-8-sig")
                compile(source, str(path), "exec")
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
        self.assertEqual(failures, [], "runtime dependency compile failures:\n" + "\n".join(failures))

    def test_recovered_runtime_paths_are_not_bound_to_original_windows_checkout(self):
        hardcoded = r"C:\Users\ASUS\ArundaTrader"
        offenders = []
        for name in RUNTIME_MODULES:
            text = (ROOT / name).read_text(encoding="utf-8-sig")
            if hardcoded.lower() in text.lower():
                offenders.append(name)
        self.assertEqual(
            offenders,
            [],
            f"runtime dependency still contains a checkout-specific path: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
