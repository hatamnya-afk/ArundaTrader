"""Execution-quality / market-microstructure evidence boundary v0.1.

Real provider evidence only. No strategy, score, decision, risk, or gate mutation.
Fails closed on missing, malformed, crossed, or stale evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
import time

@dataclass(frozen=True)
class ExecutionQualityEvidence:
    asset: str
    provider_symbol: str
    captured_at_ms: int
    source: str
    best_bid: Decimal
    best_ask: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    spread_abs: Decimal
    spread_bps: Decimal
    top_book_imbalance: Decimal
    depth_levels: int
    recent_trade_count: int

@dataclass(frozen=True)
class ExecutionQualityResult:
    status: str
    allowed: bool
    reason: str
    evidence: Optional[ExecutionQualityEvidence] = None

def _decimal(value: Any) -> Optional[Decimal]:
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return value if value.is_finite() else None

def _positive(value: Any) -> Optional[Decimal]:
    value = _decimal(value)
    return value if value is not None and value > 0 else None

def collect_toobit_execution_quality(adapter: Any, *, asset: str, provider_symbol: str,
                                    max_age_ms: int = 3000) -> ExecutionQualityResult:
    """Read and normalize three real Toobit public market-data surfaces."""
    book_ticker = adapter.get_book_ticker(provider_symbol)
    depth = adapter.get_depth(provider_symbol, limit=20)
    trades = adapter.get_recent_trades(provider_symbol, limit=60)
    for name, result in (("BOOK_TICKER", book_ticker), ("DEPTH", depth), ("TRADES", trades)):
        if not result.allowed or not isinstance(result.data, dict):
            return ExecutionQualityResult("BLOCK", False, f"{name}_UNAVAILABLE")
    ticker = book_ticker.data.get("payload")
    depth_payload = depth.data.get("payload")
    trades_payload = trades.data.get("payload")
    if not isinstance(ticker, list):
        ticker = [ticker] if isinstance(ticker, dict) else None
    if not isinstance(ticker, list) or len(ticker) != 1 or not isinstance(ticker[0], dict):
        return ExecutionQualityResult("BLOCK", False, "BOOK_TICKER_INVALID")
    if not isinstance(depth_payload, dict) or not isinstance(trades_payload, list):
        return ExecutionQualityResult("BLOCK", False, "MICROSTRUCTURE_PAYLOAD_INVALID")
    t = ticker[0]
    if str(t.get("s", "")).upper() != provider_symbol.strip().upper():
        return ExecutionQualityResult("BLOCK", False, "BOOK_TICKER_SYMBOL_MISMATCH")
    bids, asks = depth_payload.get("b"), depth_payload.get("a")
    if not isinstance(bids, list) or not isinstance(asks, list) or not bids or not asks:
        return ExecutionQualityResult("BLOCK", False, "DEPTH_SIDES_MISSING")
    timestamps = []
    for value in (t.get("t"), depth_payload.get("t")):
        if isinstance(value, int) and value > 0:
            timestamps.append(value)
    for row in trades_payload:
        if not isinstance(row, dict) or _positive(row.get("p")) is None or _positive(row.get("q")) is None:
            return ExecutionQualityResult("BLOCK", False, "RECENT_TRADE_INVALID")
        if isinstance(row.get("t"), int) and row.get("t") > 0:
            timestamps.append(row["t"])
        else:
            return ExecutionQualityResult("BLOCK", False, "RECENT_TRADE_TIMESTAMP_INVALID")
    if not timestamps:
        return ExecutionQualityResult("BLOCK", False, "MICROSTRUCTURE_TIMESTAMP_MISSING")
    book = {
        "best_bid": t.get("b"), "best_ask": t.get("a"),
        "bid_qty": t.get("bq"), "ask_qty": t.get("aq"),
        "depth_levels": min(len(bids), len(asks)),
    }
    return evaluate_execution_quality(asset=asset, provider_symbol=provider_symbol,
        book=book, recent_trades=trades_payload,
        captured_at_ms=min(timestamps), max_age_ms=max_age_ms)


def evaluate_execution_quality(*, asset: str, provider_symbol: str,
                               book: dict, recent_trades: list,
                               captured_at_ms: int, now_ms: Optional[int] = None,
                               max_age_ms: int = 3000) -> ExecutionQualityResult:
    if not isinstance(asset, str) or not asset.strip():
        return ExecutionQualityResult("BLOCK", False, "ASSET_MISSING")
    if not isinstance(provider_symbol, str) or not provider_symbol.strip():
        return ExecutionQualityResult("BLOCK", False, "PROVIDER_SYMBOL_MISSING")
    if not isinstance(book, dict):
        return ExecutionQualityResult("BLOCK", False, "BOOK_INVALID")
    if not isinstance(recent_trades, list):
        return ExecutionQualityResult("BLOCK", False, "TRADES_INVALID")
    if not isinstance(captured_at_ms, int) or captured_at_ms <= 0:
        return ExecutionQualityResult("BLOCK", False, "CAPTURE_TIMESTAMP_INVALID")
    now = int(time.time() * 1000) if now_ms is None else now_ms
    age = now - captured_at_ms
    if age < 0 or age > max_age_ms:
        return ExecutionQualityResult("BLOCK", False, "MICROSTRUCTURE_DATA_STALE")
    bid, ask = _positive(book.get("best_bid")), _positive(book.get("best_ask"))
    bid_qty, ask_qty = _positive(book.get("bid_qty")), _positive(book.get("ask_qty"))
    if None in (bid, ask, bid_qty, ask_qty):
        return ExecutionQualityResult("BLOCK", False, "TOP_OF_BOOK_INVALID")
    if ask <= bid:
        return ExecutionQualityResult("BLOCK", False, "CROSSED_OR_LOCKED_BOOK")
    depth_levels = book.get("depth_levels")
    if not isinstance(depth_levels, int) or depth_levels <= 0:
        return ExecutionQualityResult("BLOCK", False, "DEPTH_LEVELS_INVALID")
    for row in recent_trades:
        if not isinstance(row, dict):
            return ExecutionQualityResult("BLOCK", False, "RECENT_TRADE_ROW_INVALID")
    spread = ask - bid
    mid = (ask + bid) / Decimal("2")
    imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty)
    evidence = ExecutionQualityEvidence(
        asset=asset.strip().upper(), provider_symbol=provider_symbol.strip().upper(),
        captured_at_ms=captured_at_ms, source="TOOBIT_PUBLIC_MARKET_DATA",
        best_bid=bid, best_ask=ask, bid_qty=bid_qty, ask_qty=ask_qty,
        spread_abs=spread, spread_bps=(spread / mid) * Decimal("10000"),
        top_book_imbalance=imbalance, depth_levels=depth_levels,
        recent_trade_count=len(recent_trades),
    )
    return ExecutionQualityResult("PASS", True, "EXECUTION_MARKET_EVIDENCE_VALID", evidence)
