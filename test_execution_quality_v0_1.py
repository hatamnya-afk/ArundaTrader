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
