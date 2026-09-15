"""CP31-B contract tests — no engines, runtime, database, or execution."""
from risk_context_contract import RiskContext
from initial_risk_contract import InitialRisk
from risk_allocation_contract import RiskAllocation
from position_sizing_contract_v0_1 import PositionSizing, validate_runtime_invariants
from trade_lifecycle_contract_v0_1 import TradeLifecycle, TradeLifecycleState
from exit_evidence_contract_v0_1 import ExitEvidence, ExitEvidenceLevel
from portfolio_risk_contract_v0_1 import PortfolioRisk
from trade_outcome_contract_v0_1 import TradeOutcome
from risk_policy_contract_v0_1 import RiskPolicy
from calibration_observation_contract_v0_1 import CalibrationObservation, CalibrationEvidenceState
from trade_management_contract_common import CapitalState


def test_contracts_are_immutable():
    ctx = RiskContext("BTC/USDT", "BTC/USDT", "LONG", 100.0)
    try:
        ctx.entry_price = 101.0
    except Exception:
        pass
    else:
        raise AssertionError("RiskContext must be immutable")


def test_basic_contract_validation():
    assert RiskContext("BTC/USDT", "BTC/USDT", "LONG", 100.0).validate()
    assert InitialRisk(100.0, None, None, None, None, 2.0, None, None).validate()
    assert RiskAllocation(None, None, None, None, None, None, None).validate()
    assert PositionSizing("BTC/USDT", "BTC/USDT", "LONG", 100.0, 2.0, 98.0, None, None, None, None).validate()
    assert PortfolioRisk(None, None, None, None, None, 0, None, None, None).validate()
    assert TradeLifecycle(TradeLifecycleState.PRE_TRADE).validate()
    assert ExitEvidence(None, None, None, None, None, None, None, None, None, None, None, ExitEvidenceLevel.NONE).validate()
    assert TradeOutcome("BTC/USDT", "BTC/USDT", "LONG", "t0", 100.0, "t1", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None).validate()
    assert RiskPolicy("RISK_POLICY", "v0.1", None, None, None, None, {}, {}, {}, {}, {}, {}, {}).validate()
    assert CalibrationObservation("v0.1", None, None, None, 0, None, None, None, None, None, None, None, None, None, "t0", CalibrationEvidenceState.PRIOR).validate()


def test_production_sizing_requires_real_capital():
    record = PositionSizing(
        "BTC/USDT", "BTC/USDT", "LONG", 100.0, 2.0, 98.0,
        None, None, None, None, quantity=1.0,
        capital_state=CapitalState.UNAVAILABLE_CAPITAL,
    )
    try:
        record.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("Unavailable capital must fail closed for sizing output")


def test_runtime_invariants_are_explicitly_runtime_bound():
    record = PositionSizing("BTC/USDT", "BTC/USDT", "LONG", 100.0, 2.0, 98.0, None, None, None, None)
    result = validate_runtime_invariants(record)
    assert result["entry_price"] == "VALID"
    assert result["stop_distance"] == "VALID"
    assert result["quantity_positive"] == "RUNTIME_VALIDATION_REQUIRED"


def test_emergency_exit_is_terminal_and_separate():
    lifecycle = TradeLifecycle(TradeLifecycleState.EMERGENCY_EXIT)
    assert lifecycle.is_terminal()
    assert lifecycle.allowed_transitions() == ()


def test_calibration_does_not_auto_mutate_policy():
    from calibration_observation_contract_v0_1 import AUTOMATIC_POLICY_MUTATION, VALIDATED_IS_NOT_AUTOMATIC_UPDATE
    assert AUTOMATIC_POLICY_MUTATION is False
    assert VALIDATED_IS_NOT_AUTOMATIC_UPDATE is True
