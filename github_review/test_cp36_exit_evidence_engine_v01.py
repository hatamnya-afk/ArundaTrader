import pytest


def _load_engine():
    try:
        from exit_evidence_engine_v0_1 import build_exit_evidence
        return build_exit_evidence
    except ModuleNotFoundError as exc:
        pytest.fail(f"CP36 RED: Exit Evidence Engine is not implemented yet: {exc}")


def test_all_evidence_levels_are_representable():
    build = _load_engine()
    from exit_evidence_contract_v0_1 import ExitEvidenceLevel

    for level in ExitEvidenceLevel:
        result = build({"asset": "ARBITRARY/USDT"}, evidence_level=level)
        assert result.exit_evidence_level is level


def test_unknown_evidence_level_fails_closed():
    build = _load_engine()
    result = build({"asset": "ARBITRARY/USDT"}, evidence_level="UNKNOWN")
    assert result.exit_evidence_level.value == "NONE"
    assert "UNKNOWN_EVIDENCE_LEVEL" in result.evidence_reasons


def test_dynamic_asset_and_no_fixed_universe_dependency():
    build = _load_engine()
    result = build({"asset": "ARBITRARY/USDT", "symbol": "ARBITRARY/USDT"})
    assert result.exit_evidence_level.value == "NONE"


def test_missing_observations_remain_unavailable():
    build = _load_engine()
    result = build({"asset": "ARBITRARY/USDT"})
    assert result.signal_health is None
    assert result.structure_health is None
    assert result.momentum_state is None
    assert result.volatility_state is None
    assert result.mfe is None
    assert result.mae is None
    assert result.giveback is None
    assert result.holding_time is None
    assert result.liquidity is None
    assert result.market_regime is None
    assert result.trend_state is None


def test_explicit_observations_are_preserved_without_reimplementation():
    build = _load_engine()
    observations = {
        "asset": "X/USDT",
        "signal_health": "ACTIVE",
        "structure_health": "INTACT",
        "momentum_state": "POSITIVE",
        "volatility_state": "NORMAL",
        "mfe": 0.12,
        "mae": 0.03,
        "giveback": 0.02,
        "holding_time": 3600,
        "liquidity": "ADEQUATE",
        "market_regime": "TRENDING",
        "trend_state": "UP",
    }
    result = build(observations, evidence_level="MODERATE")
    assert result.signal_health == "ACTIVE"
    assert result.structure_health == "INTACT"
    assert result.momentum_state == "POSITIVE"
    assert result.volatility_state == "NORMAL"
    assert result.mfe == 0.12
    assert result.mae == 0.03
    assert result.giveback == 0.02
    assert result.holding_time == 3600
    assert result.liquidity == "ADEQUATE"
    assert result.market_regime == "TRENDING"
    assert result.trend_state == "UP"


def test_deterministic_output():
    build = _load_engine()
    observations = {"asset": "X/USDT", "signal_health": "ACTIVE"}
    assert build(observations, evidence_level="WEAK") == build(observations, evidence_level="WEAK")


def test_no_exit_decision_or_order_fields():
    build = _load_engine()
    result = build({"asset": "X/USDT"}, evidence_level="STRONG")
    for forbidden in (
        "exit_decision", "sell", "close", "reduce", "take_profit",
        "trailing_stop", "break_even", "time_exit", "quantity",
        "position_size", "order_intent", "execution", "order_id",
    ):
        assert not hasattr(result, forbidden)


def test_provider_neutral_and_capital_neutral():
    build = _load_engine()
    observations = {
        "asset": "X/USDT",
        "provider": "KUCOIN",
        "capital": 1_000_000,
        "available_capital": 1_000_000,
        "risk_per_trade": 0.005,
    }
    result = build(observations)
    assert result.exit_evidence_level.value == "NONE"
    assert result.evidence_reasons == ()


def test_input_mapping_is_not_mutated():
    build = _load_engine()
    observations = {"asset": "X/USDT", "signal_health": "ACTIVE"}
    before = dict(observations)
    build(observations, evidence_level="CRITICAL")
    assert observations == before


def test_invalid_numeric_observations_do_not_create_values():
    build = _load_engine()
    result = build({"asset": "X/USDT", "mfe": True, "mae": "bad", "holding_time": -1})
    assert result.mfe is None
    assert result.mae is None
    assert result.holding_time is None
