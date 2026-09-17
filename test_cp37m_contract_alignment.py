from types import SimpleNamespace

from account_balance_observation_v0_1 import build_account_balance_observation
from toobit_trading_adapter import ToobitTradingAdapter


def test_toobit_adapter_exposes_account_balance_observation_contract(monkeypatch):
    adapter = ToobitTradingAdapter(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
    )

    monkeypatch.setattr(
        adapter,
        "get_account",
        lambda: SimpleNamespace(
            allowed=True,
            data={
                "account_id": "TEST_ACCOUNT",
                "account_type": "SPOT",
                "environment": "TEST",
            },
        ),
    )

    monkeypatch.setattr(
        adapter,
        "get_balances",
        lambda: SimpleNamespace(
            allowed=True,
            data={
                "balances": [],
            },
        ),
    )

    observation = build_account_balance_observation(
        adapter,
        retrieved_at="2026-01-01T00:00:00+00:00",
    )

    assert observation is not None
