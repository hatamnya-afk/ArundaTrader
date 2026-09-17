from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from account_balance_observation_v0_1 import (
    AccountBalanceObservation,
    AccountObservation,
    BalanceObservation,
)
from portfolio_observation_v0_1 import (
    PortfolioObservation,
    build_portfolio_observation,
)


RETRIEVED_AT = "2026-09-16T00:00:00+00:00"


def _account_balance(account_id=None):
    return AccountBalanceObservation(
        account=AccountObservation(
            account_id=account_id,
            account_type="SPOT",
            environment=None,
            source_id=None,
            source_type=None,
            source_timestamp=None,
            retrieved_at=RETRIEVED_AT,
            status="PASS",
        ),
        balances=(
            BalanceObservation(
                asset="USDT",
                free=100,
                locked=0,
                total=100,
                source_id=None,
                source_type=None,
                source_timestamp=None,
                retrieved_at=RETRIEVED_AT,
            ),
        ),
    )


def _result(rows, retrieved_at=RETRIEVED_AT):
    return SimpleNamespace(
        allowed=True,
        data={"positions": rows, "retrieved_at": retrieved_at},
    )


def test_missing_position_source_is_explicitly_unavailable():
    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=None,
    )
    assert observation.positions is None
    assert observation.total_exposure is None
    assert "POSITION_SOURCE_NOT_AVAILABLE" in observation.gaps
    assert "EXPOSURE_NOT_AVAILABLE" in observation.gaps


def test_identity_is_never_invented():
    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=None,
    )
    assert observation.portfolio_id is None
    assert observation.account_id is None
    assert "PORTFOLIO_ID_NOT_AVAILABLE" in observation.gaps
    assert "ACCOUNT_ID_NOT_AVAILABLE" in observation.gaps


def test_dynamic_positions_and_source_exposure_are_preserved():
    rows = [
        {
            "symbol": "AAA/USDT",
            "side": "LONG",
            "quantity": 2,
            "entry_price": 10,
            "mark_price": 11,
            "notional": 22,
            "unrealized_pnl": 2,
            "realized_pnl": 0,
            "source_id": "account-position-read",
            "source_type": "CEX_PUBLIC_API",
            "source_timestamp": "2026-09-16T00:00:00+00:00",
        },
        {
            "symbol": "BBB/USDT",
            "side": "SHORT",
            "quantity": 3,
            "entry_price": 20,
            "mark_price": 19,
            "notional": 57,
            "unrealized_pnl": 3,
            "realized_pnl": 0,
            "source_id": "account-position-read",
            "source_type": "CEX_PUBLIC_API",
            "source_timestamp": "2026-09-16T00:00:00+00:00",
        },
    ]
    observation = build_portfolio_observation(
        _account_balance("account-real"),
        position_reader=lambda: _result(rows),
        portfolio_id="portfolio-real",
    )
    assert len(observation.positions) == 2
    assert observation.total_exposure == 79.0
    assert observation.exposure_source == "POSITION_NOTIONAL"
    assert observation.source_status == "AVAILABLE"


def test_missing_position_notional_does_not_infer_exposure():
    rows = [
        {
            "symbol": "AAA/USDT",
            "side": "LONG",
            "quantity": 2,
            "entry_price": 10,
            "mark_price": 11,
            "notional": None,
            "source_id": "account-position-read",
            "source_type": "CEX_PUBLIC_API",
            "source_timestamp": "2026-09-16T00:00:00+00:00",
        }
    ]
    observation = build_portfolio_observation(
        _account_balance("account-real"),
        position_reader=lambda: _result(rows),
        portfolio_id="portfolio-real",
    )
    assert observation.total_exposure is None
    assert "EXPOSURE_NOT_AVAILABLE" in observation.gaps


def test_unavailable_position_result_fails_closed():
    result = SimpleNamespace(allowed=False, data={})
    with pytest.raises(RuntimeError):
        build_portfolio_observation(
            _account_balance(),
            position_reader=lambda: result,
        )


def test_invalid_position_provenance_fails_closed():
    rows = [
        {
            "symbol": "AAA/USDT",
            "side": "LONG",
            "quantity": 1,
            "entry_price": 10,
            "mark_price": 10,
            "notional": 10,
            "source_id": "",
        }
    ]
    with pytest.raises(RuntimeError):
        build_portfolio_observation(
            _account_balance(),
            position_reader=lambda: _result(rows),
        )


def test_no_fixed_asset_count_dependency():
    rows = []
    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=lambda: _result(rows),
    )
    assert observation.positions == ()
    assert observation.total_exposure is None


def test_immutable():
    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=None,
    )
    with pytest.raises(FrozenInstanceError):
        observation.source_status = "MUTATED"


def test_no_risk_sizing_or_execution_fields():
    fields = set(PortfolioObservation.__dataclass_fields__)
    forbidden = {
        "risk_budget",
        "position_size",
        "order_intent",
        "execution",
        "usable_capital",
        "total_risk",
        "policy_version",
    }
    assert not fields.intersection(forbidden)
