"""CP46-D production provider preflight orchestration tests."""

from cp46_d_production_provider_preflight_v0_1 import (
    build_toobit_translation_evidence,
    translate_and_preflight_toobit,
)
from exchange_execution_contract import CanonicalOrderRequest


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
                "TRADE_AMOUNT": {
                    "minAmount": "1",
                    "maxAmount": "100000000",
                },
            },
        })

    def account_check(self):
        return _Result(data={"account_response": {"accountType": "SPOT"}})

    def duplicate_check(self, asset, direction):
        return _Result(data={
            "state_known": True,
            "open_order_client_ids": frozenset(),
            "recent_order_client_ids": frozenset(),
        })

    def get_server_time(self):
        return _Result(data={"serverTime": 1000})


def _canonical():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=10,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=None,
        reference_price=None,
        intent_id="CP46D-PROD-001",
        snapshot_id="SNAP-001",
        timestamp="1000",
    )


def test_authoritative_provider_symbol_is_not_reconstructed():
    evidence = build_toobit_translation_evidence(
        adapter=_Adapter(),
        canonical_request=_canonical(),
    )
    assert evidence.provider_symbol == "BTCUSDT"
    assert evidence.quote_quantity is None


def test_market_buy_passes_with_authoritative_risk_exposure_quote_quantity():
    result = translate_and_preflight_toobit(
        canonical_request=_canonical(),
        adapter=_Adapter(),
        quote_quantity=1000,
    )
    assert result.status == "PASS"
    assert result.translation is not None
    assert result.translation.request is not None
    assert result.translation.request.quantity == 1000
    assert result.translation.request.quantity_unit == "QUOTE_ASSET"
    assert result.handoff is not None
    assert result.handoff.preflight is not None


def test_market_buy_blocks_without_authoritative_quote_quantity():
    result = translate_and_preflight_toobit(
        canonical_request=_canonical(),
        adapter=_Adapter(),
    )
    assert result.status == "BLOCK"
    assert result.reason == "CP46_C_TRANSLATION_BLOCKED"
    assert result.translation is not None
    assert result.translation.request is None


def test_translation_evidence_preserves_authoritative_quote_quantity():
    evidence = build_toobit_translation_evidence(
        adapter=_Adapter(),
        canonical_request=_canonical(),
        quote_quantity=1000,
    )
    assert evidence.quote_quantity == 1000


def test_unavailable_authoritative_state_fails_closed():
    class BrokenAdapter(_Adapter):
        def account_check(self):
            return _Result(
                allowed=False,
                reason="INVALID_SIGNATURE",
            )

    result = translate_and_preflight_toobit(
        canonical_request=_canonical(),
        adapter=BrokenAdapter(),
        quote_quantity=1000,
    )
    assert result.status == "BLOCK"
    assert result.reason == "AUTHORITATIVE_PROVIDER_STATE_UNAVAILABLE"


def test_cp46_d_reaches_authoritative_toobit_evidence_for_spot_limit():
    request = _canonical()
    request = CanonicalOrderRequest(
        asset=request.asset,
        direction=request.direction,
        order_type="LIMIT",
        quantity=1,
        quantity_unit=request.quantity_unit,
        quantity_source=request.quantity_source,
        entry_price=100,
        reference_price=None,
        intent_id=request.intent_id,
        snapshot_id=request.snapshot_id,
        timestamp=request.timestamp,
    )

    result = translate_and_preflight_toobit(
        canonical_request=request,
        adapter=_Adapter(),
    )

    assert result.status == "PASS"
    assert result.translation is not None
    assert result.translation.request is not None
    assert result.handoff is not None
    assert result.handoff.preflight is not None
