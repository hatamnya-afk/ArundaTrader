"""CP49 — Toobit provider evidence and preflight boundary tests."""

from provider_preflight_v0_1 import (
    PreflightStatus,
    ProviderOrderPreflightRequest,
)
from toobit_provider_preflight_evidence_v0_1 import (
    build_toobit_provider_preflight_evidence,
    run_toobit_provider_preflight,
)


class _Result:
    def __init__(self, allowed=True, data=None, reason="ok"):
        self.allowed = allowed
        self.data = data
        self.reason = reason


class _Adapter:
    def trading_constraints(self, asset):
        return _Result(data={
            "symbol": asset.upper() + "USDT",
            "status": "TRADING",
            "filters": {
                "LOT_SIZE": {
                    "minQty": "1",
                    "maxQty": "100000",
                    "stepSize": "1",
                },
                "MIN_NOTIONAL": {
                    "minNotional": "1",
                    "maxNotional": "100000000",
                },
            },
        })

    def account_check(self):
        return _Result(data={
            "account_response": {"accountType": "SPOT"},
        })

    def duplicate_check(self, asset, direction):
        return _Result(data={
            "state_known": True,
            "open_order_client_ids": frozenset(),
            "recent_order_client_ids": frozenset(),
        })

    def get_server_time(self):
        return _Result(data={"serverTime": 1000})


def _request():
    return ProviderOrderPreflightRequest(
        symbol="BTCUSDT",
        direction="LONG",
        order_type="MARKET",
        quantity="10",
        quantity_unit="QUOTE_ASSET",
        intent_id="intent-1",
        timestamp_ms=1000,
        venue="SPOT",
    )


def test_toobit_producer_connects_all_four_authoritative_sources():
    evidence = build_toobit_provider_preflight_evidence(
        adapter=_Adapter(),
        asset="BTC",
    )

    assert evidence.contract.symbol_valid is True
    assert evidence.contract.contract_valid is True
    assert evidence.account.state_known is True
    assert evidence.account.margin_state_known is None
    assert evidence.account.leverage_state_known is None
    assert evidence.account.position_conflict is None
    assert evidence.orders.state_known is True
    assert evidence.timestamp.state_known is True
    assert evidence.timestamp.exchange_timestamp_ms == 1000
    assert evidence.portfolio is None


def test_toobit_producer_does_not_create_balance_permission():
    account = build_toobit_provider_preflight_evidence(
        adapter=_Adapter(),
        asset="BTC",
    ).account

    assert not hasattr(account, "balance_sufficient")


def test_toobit_provider_boundary_invokes_pure_cp46_a6_preflight():
    result = run_toobit_provider_preflight(
        adapter=_Adapter(),
        request=_request(),
    )

    assert result.status is PreflightStatus.PASS
