"""Focused contract checks for zero-capital research Trade Intent."""

from zero_capital_research_trade_contract_v0_1 import (
    NORMAL_TRADE,
    RESEARCH_TRADE,
    RESEARCH_QUANTITY_SOURCE,
    RISK_QUANTITY_SOURCE,
    resolve_trade_quantity,
    validate_research_trade_contract,
)


def main() -> int:
    normal = resolve_trade_quantity(
        observed_real_capital=25.0,
        risk_position_quantity=0.5,
        research_quantity=0.01,
    )
    assert normal["trade_type"] == NORMAL_TRADE
    assert normal["quantity"] == 0.5
    assert normal["quantity_source"] == RISK_QUANTITY_SOURCE

    zero = resolve_trade_quantity(
        observed_real_capital=0.0,
        risk_position_quantity=0.0,
    )
    assert zero["trade_type"] == NORMAL_TRADE
    assert zero["quantity"] == 0.0
    assert zero["quantity_source"] == RISK_QUANTITY_SOURCE

    zero_with_positive_risk = resolve_trade_quantity(
        observed_real_capital=0.0,
        risk_position_quantity=0.01,
        research_quantity=999.0,
    )
    assert zero_with_positive_risk["trade_type"] == NORMAL_TRADE
    assert zero_with_positive_risk["quantity"] == 0.01
    assert zero_with_positive_risk["quantity_source"] == RISK_QUANTITY_SOURCE

    try:
        validate_research_trade_contract(
            trade_type=RESEARCH_TRADE,
            observed_real_capital=1.0,
            quantity=0.01,
            quantity_source=RESEARCH_QUANTITY_SOURCE,
        )
    except ValueError as exc:
        assert str(exc) == (
            "RESEARCH_TRADE_REQUIRES_ZERO_OBSERVED_REAL_CAPITAL"
        )
    else:
        raise AssertionError("research trade accepted with positive capital")

    try:
        resolve_trade_quantity(
            observed_real_capital=0.0,
            risk_position_quantity=0.0,
            research_quantity=None,
        )
    except ValueError as exc:
        assert str(exc) == "RESEARCH_QUANTITY_INVALID"
    else:
        raise AssertionError("missing research quantity accepted")

    print("ZERO_CAPITAL_RESEARCH_CONTRACT_TEST=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
