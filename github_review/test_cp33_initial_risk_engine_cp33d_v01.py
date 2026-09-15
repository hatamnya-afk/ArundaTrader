"""CP33-D — Initial Risk Engine boundary, side-effect, and edge tests."""
from __future__ import annotations

from copy import deepcopy

from initial_risk_contract import ATR_POLICY_REFERENCE, STOP_MULTIPLIER_STATUS, InitialRisk
from initial_risk_engine_v0_1 import build_initial_risk


def test_cp33d_is_deterministic_for_identical_observations():
    context = {
        "asset": "ICX/USDT",
        "symbol": "ICX/USDT",
        "direction": "LONG",
        "entry_price": 0.12,
        "atr14": 0.004,
        "stop_price": 0.114,
        "stop_distance": 0.006,
        "stop_method": "EXPLICIT_OBSERVATION",
    }

    first = build_initial_risk(context)
    second = build_initial_risk(context)

    assert first == second


def test_cp33d_does_not_mutate_any_input_mapping():
    context = {
        "asset": "BTC/USDT",
        "symbol": "BTC/USDT",
        "direction": "LONG",
        "entry_price": 100000.0,
        "atr14": 2500.0,
        "stop_price": 96250.0,
        "stop_distance": 3750.0,
        "stop_method": "EXPLICIT_OBSERVATION",
    }
    structure = {"structure_state": "BULLISH"}
    thesis = {"thesis_reference": "existing-thesis"}
    before = (deepcopy(context), deepcopy(structure), deepcopy(thesis))

    build_initial_risk(context, structure=structure, thesis=thesis)

    assert context == before[0]
    assert structure == before[1]
    assert thesis == before[2]


def test_cp33d_missing_entry_price_is_not_inferred_from_other_price_fields():
    result = build_initial_risk(
        {
            "asset": "ETH/USDT",
            "symbol": "ETH/USDT",
            "direction": "LONG",
            "price": 4000.0,
            "latest_close": 3995.0,
            "atr14": 100.0,
        }
    )

    assert result.entry_price is None
    assert result.risk_invalidation_reason == "ENTRY_PRICE_NOT_EXPLICIT"


def test_cp33d_unvalidated_stop_policy_never_derives_stop_from_atr():
    result = build_initial_risk(
        {
            "asset": "SOL/USDT",
            "symbol": "SOL/USDT",
            "direction": "LONG",
            "entry_price": 200.0,
            "atr14": 5.0,
        }
    )

    assert STOP_MULTIPLIER_STATUS == "UNVALIDATED"
    assert ATR_POLICY_REFERENCE == "SOURCE_REFERENCE_ONLY"
    assert result.atr14 == 5.0
    assert result.stop_price is None
    assert result.stop_distance is None
    assert result.risk_invalidation_reason == "STOP_POLICY_UNVALIDATED"


def test_cp33d_explicit_risk_observations_are_preserved():
    result = build_initial_risk(
        {
            "asset": "FIL/USDT",
            "symbol": "FIL/USDT",
            "direction": "LONG",
            "entry_price": 1.25,
            "stop_price": 1.18,
            "stop_distance": 0.07,
            "atr14": 0.05,
            "stop_method": "EXPLICIT_OBSERVATION",
        },
        structure={"structure_state": "BULLISH"},
        thesis={"thesis_reference": "signal-thesis"},
    )

    assert isinstance(result, InitialRisk)
    assert result.entry_price == 1.25
    assert result.stop_price == 1.18
    assert result.stop_distance == 0.07
    assert result.atr14 == 0.05
    assert result.stop_method == "EXPLICIT_OBSERVATION"
    assert result.structure_reference == "BULLISH"
    assert result.thesis_reference == "signal-thesis"
    assert result.risk_invalidation_reason is None


def test_cp33d_dynamic_asset_is_accepted_without_fixed_universe_logic():
    result = build_initial_risk(
        {
            "asset": "ARBITRARY-NEW-ASSET/USDT",
            "symbol": "ARBITRARY-NEW-ASSET/USDT",
            "direction": "SHORT",
            "entry_price": 10.0,
            "stop_price": 10.5,
            "stop_distance": 0.5,
        }
    )

    assert isinstance(result, InitialRisk)
    assert result.entry_price == 10.0
    assert result.stop_price == 10.5
    assert result.stop_distance == 0.5


def test_cp33d_missing_optional_observations_remain_none():
    result = build_initial_risk(
        {
            "asset": "NEAR/USDT",
            "symbol": "NEAR/USDT",
            "direction": "SHORT",
            "entry_price": 5.0,
        }
    )

    assert result.stop_price is None
    assert result.stop_distance is None
    assert result.atr14 is None
    assert result.stop_method is None
    assert result.structure_reference is None
    assert result.thesis_reference is None


def test_cp33d_invalid_numeric_observations_do_not_create_risk_values():
    result = build_initial_risk(
        {
            "asset": "SUI/USDT",
            "symbol": "SUI/USDT",
            "direction": "LONG",
            "entry_price": -1.0,
            "stop_price": 0.0,
            "stop_distance": -0.1,
            "atr14": "not-a-number",
        }
    )

    assert result.entry_price is None
    assert result.stop_price is None
    assert result.stop_distance is None
    assert result.atr14 is None
    assert result.risk_invalidation_reason == "ENTRY_PRICE_NOT_EXPLICIT"


def test_cp33d_no_sizing_allocation_exit_or_execution_fields_are_created():
    result = build_initial_risk(
        {
            "asset": "AAVE/USDT",
            "symbol": "AAVE/USDT",
            "direction": "LONG",
            "entry_price": 100.0,
            "atr14": 2.0,
        }
    )

    forbidden = {
        "quantity",
        "position_size",
        "risk_amount",
        "risk_percent",
        "allocation",
        "portfolio_risk",
        "take_profit",
        "trailing_stop",
        "order_intent",
        "execution",
    }
    assert not (forbidden & set(vars(result)))


if __name__ == "__main__":
    raise SystemExit("Use pytest to execute CP33-D tests.")
