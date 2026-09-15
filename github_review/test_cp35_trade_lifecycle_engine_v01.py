import pytest


def _load_engine():
    try:
        from trade_lifecycle_engine_v0_1 import transition_trade_lifecycle
        return transition_trade_lifecycle
    except ModuleNotFoundError as exc:
        pytest.fail(f"CP35 RED: Trade Lifecycle Manager is not implemented yet: {exc}")


def test_valid_pre_trade_to_open_transition():
    transition = _load_engine()
    result = transition("PRE_TRADE", "OPEN")
    assert result.state == "OPEN"
    assert result.valid is True


def test_invalid_transition_fails_closed():
    transition = _load_engine()
    result = transition("PRE_TRADE", "PROTECTION")
    assert result.valid is False
    assert result.state == "PRE_TRADE"


def test_terminal_exit_cannot_transition_further():
    transition = _load_engine()
    result = transition("EXIT", "OPEN")
    assert result.valid is False
    assert result.state == "EXIT"


def test_emergency_exit_is_terminal():
    transition = _load_engine()
    result = transition("OPEN", "EMERGENCY_EXIT")
    assert result.valid is True
    assert result.state == "EMERGENCY_EXIT"


def test_dynamic_asset_context_is_not_fixed_universe_logic():
    transition = _load_engine()
    result = transition("INITIAL_RISK", "PROFIT_ACTIVATION", asset="ARBITRARY/USDT")
    assert result.valid is True
    assert result.asset == "ARBITRARY/USDT"


def test_transition_is_deterministic_and_does_not_create_execution_fields():
    transition = _load_engine()
    first = transition("PROTECTION", "EXTENSION", asset="BTC/USDT")
    second = transition("PROTECTION", "EXTENSION", asset="BTC/USDT")
    assert first == second
    for forbidden in (
        "quantity", "position_size", "order_intent", "execution", "order_id"
    ):
        assert not hasattr(first, forbidden)
