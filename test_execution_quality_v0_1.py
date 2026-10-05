from decimal import Decimal
from execution_quality_v0_1 import evaluate_execution_quality

def book():
    return {"best_bid":"0.400","best_ask":"0.401","bid_qty":"1000","ask_qty":"800","depth_levels":5}

def test_valid_fresh_evidence():
    r=evaluate_execution_quality(asset="ADA",provider_symbol="ADAUSDT",book=book(),
        recent_trades=[{"p":"0.4005","q":"10","t":1000500}],
        captured_at_ms=1000000,now_ms=1001000)
    assert r.allowed and r.status=="PASS"
    assert r.evidence.spread_bps > Decimal("0")

def test_stale_fails_closed():
    r=evaluate_execution_quality(asset="ADA",provider_symbol="ADAUSDT",book=book(),
        recent_trades=[],captured_at_ms=1000000,now_ms=1003001)
    assert not r.allowed and r.reason=="MICROSTRUCTURE_DATA_STALE"

def test_crossed_book_fails_closed():
    b=book(); b["best_ask"]="0.399"
    r=evaluate_execution_quality(asset="ADA",provider_symbol="ADAUSDT",book=b,
        recent_trades=[],captured_at_ms=1000000,now_ms=1001000)
    assert not r.allowed and r.reason=="CROSSED_OR_LOCKED_BOOK"


class FakeAdapter:
    def _r(self, payload):
        return type("R", (), {"allowed": True, "data": {"payload": payload}})()
    def get_book_ticker(self, symbol):
        return self._r([{"t": 1000000, "s": symbol, "b": "0.400", "bq": "1000", "a": "0.401", "aq": "800"}])
    def get_depth(self, symbol, limit=20):
        return self._r({"t": 1000000, "b": [["0.400","1000"]], "a": [["0.401","800"]]})
    def get_recent_trades(self, symbol, limit=60):
        return self._r([{"p":"0.4005","q":"10","t":1000000}])


def test_toobit_collection_uses_real_three_surface_contract():
    from execution_quality_v0_1 import collect_toobit_execution_quality
    r=collect_toobit_execution_quality(FakeAdapter(), asset="ADA", provider_symbol="ADAUSDT", max_age_ms=1000)
    assert r.allowed and r.evidence.source=="TOOBIT_PUBLIC_MARKET_DATA"


def test_toobit_collection_fails_closed_on_symbol_mismatch():
    from execution_quality_v0_1 import collect_toobit_execution_quality
    class Bad(FakeAdapter):
        def get_book_ticker(self, symbol):
            return self._r([{"t":1000000,"s":"OTHERUSDT","b":"0.4","bq":"1","a":"0.401","aq":"1"}])
    r=collect_toobit_execution_quality(Bad(), asset="ADA", provider_symbol="ADAUSDT", max_age_ms=1000)
    assert not r.allowed and r.reason=="BOOK_TICKER_SYMBOL_MISMATCH"
