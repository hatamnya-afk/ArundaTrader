"""CP32 tests — pure RiskContext engine only."""
from risk_context_contract import RiskContext
from risk_context_engine_v0_1 import build_risk_context


def _fixture():
    return {
        "asset": "BTC/USDT",
        "symbol": "BTC/USDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "price": 999.0,
        "latest_close": 998.0,
    }


def test_builds_contract_from_observations():
    result = build_risk_context(
        _fixture(),
        market_data={"market_data_freshness": "FRESH", "volatility_regime": "NORMAL"},
        market_analysis={"trend_state": "UP", "acceleration": 0.2, "position": 0.6},
        signal={"momentum_state": "POSITIVE", "signal_quality": "HIGH", "confidence": 0.8},
        structure={"structure_state": "HEALTHY", "structure_strength": 0.7},
        portfolio={"portfolio_exposure": 0.0, "portfolio_risk_state": "AVAILABLE"},
        liquidity={"liquidity_state": "AVAILABLE"},
        correlation={"BTC/USDT": 1.0},
        provenance={"source": "TEST_FIXTURE"},
    )
    assert isinstance(result, RiskContext)
    assert result.asset == "BTC/USDT"
    assert result.direction == "LONG"
    assert result.entry_price == 100.0
    assert result.confidence == 0.8
    assert result.validate()


def test_entry_price_never_falls_back_to_price_or_latest_close():
    candidate = {"asset": "BTC/USDT", "symbol": "BTC/USDT", "direction": "LONG", "price": 999.0, "latest_close": 998.0}
    result = build_risk_context(candidate)
    assert result.entry_price is None


def test_missing_optional_observations_remain_unavailable():
    result = build_risk_context({"asset": "BTC/USDT", "symbol": "BTC/USDT", "direction": "LONG"})
    assert result.entry_price is None
    assert result.trend_state is None
    assert result.liquidity_state is None
    assert result.correlation_context is None
    assert result.portfolio_exposure is None


def test_deterministic_for_same_input():
    candidate = _fixture()
    sources = {"market_data_freshness": "FRESH", "volatility_regime": "NORMAL"}
    first = build_risk_context(candidate, market_data=sources)
    second = build_risk_context(candidate, market_data=sources)
    assert first == second


def test_engine_does_not_calculate_risk_or_sizing_fields():
    result = build_risk_context(_fixture())
    assert not hasattr(result, "risk_budget")
    assert not hasattr(result, "position_size")
    assert not hasattr(result, "quantity")
    assert not hasattr(result, "exit_decision")


def test_dynamic_candidate_is_not_checked_against_fixed_universe():
    result = build_risk_context({"asset": "SOME-NEW-ASSET/USDT", "symbol": "SOME-NEW-ASSET/USDT", "direction": "SHORT"})
    assert result.asset == "SOME-NEW-ASSET/USDT"
    assert result.direction == "SHORT"
