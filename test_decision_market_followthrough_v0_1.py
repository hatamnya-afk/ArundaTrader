"""Focused tests for real-market decision follow-through; no provider or DB access."""
from __future__ import annotations

import unittest

from decision_market_followthrough_v0_1 import evaluate_followthrough


def decision(direction="LONG"):
    return {
        "decision_id": "dec-001",
        "asset": "BTC/USDT",
        "direction": direction,
        "decision_timestamp_ms": 1000,
        "decision_price": 100.0,
        "source_id": "kucoin:BTC/USDT:1m",
    }


def candle(ts, o, h, l, c, source="kucoin:BTC/USDT:1m", asset="BTC/USDT"):
    return {"timestamp_ms": ts, "asset": asset, "source_id": source,
            "open": o, "high": h, "low": l, "close": c}


class FollowthroughTests(unittest.TestCase):
    def test_long_metrics_and_not_trade_pnl(self):
        result = evaluate_followthrough(
            decision=decision(),
            candles=[candle(1000, 100, 102, 99, 101), candle(2000, 101, 110, 95, 105)],
            horizon_end_ms=2000,
        )
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["quality_metrics"]["terminal_directional_return_pct"], 5.0)
        self.assertEqual(result["quality_metrics"]["max_favorable_excursion_pct"], 10.0)
        self.assertEqual(result["quality_metrics"]["max_adverse_excursion_pct"], 5.0)
        self.assertFalse(result["is_trade_pnl"])
        self.assertFalse(result["execution_or_fill_inferred"])

    def test_short_directional_return(self):
        result = evaluate_followthrough(
            decision=decision("SHORT"),
            candles=[candle(2000, 100, 103, 90, 95)],
            horizon_end_ms=2000,
        )
        self.assertEqual(result["quality_metrics"]["terminal_directional_return_pct"], round((100/95-1)*100, 8))
        self.assertEqual(result["quality_metrics"]["max_favorable_excursion_pct"], round((100/90-1)*100, 8))
        self.assertEqual(result["quality_metrics"]["max_adverse_excursion_pct"], 3.0)

    def test_missing_horizon_is_incomplete_not_extrapolated(self):
        result = evaluate_followthrough(
            decision=decision(), candles=[candle(1500, 100, 102, 99, 101)],
            horizon_end_ms=2000,
        )
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["reason"], "HORIZON_ENDPOINT_NOT_OBSERVED")
        self.assertIsNone(result["quality_metrics"])

    def test_source_blending_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "source mismatch"):
            evaluate_followthrough(
                decision=decision(),
                candles=[candle(2000, 100, 102, 99, 101, source="bybit:BTC/USDT:1m")],
                horizon_end_ms=2000,
            )

    def test_asset_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "asset mismatch"):
            evaluate_followthrough(
                decision=decision(), candles=[candle(2000, 100, 102, 99, 101, asset="ETH/USDT")],
                horizon_end_ms=2000,
            )

    def test_bad_ohlc_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid candle high"):
            evaluate_followthrough(
                decision=decision(), candles=[candle(2000, 100, 99, 98, 101)],
                horizon_end_ms=2000,
            )

    def test_pre_decision_candles_are_excluded(self):
        result = evaluate_followthrough(
            decision=decision(),
            candles=[candle(900, 90, 120, 80, 110), candle(2000, 100, 102, 99, 101)],
            horizon_end_ms=2000,
        )
        self.assertEqual(result["quality_metrics"]["max_favorable_excursion_pct"], 2.0)

    def test_horizon_must_be_after_decision(self):
        with self.assertRaisesRegex(ValueError, "horizon_end_ms must be later"):
            evaluate_followthrough(decision=decision(), candles=[], horizon_end_ms=1000)

    def test_duplicate_timestamps_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate candle timestamp"):
            evaluate_followthrough(
                decision=decision(),
                candles=[candle(2000, 100, 102, 99, 101), candle(2000, 100, 103, 98, 102)],
                horizon_end_ms=2000,
            )


if __name__ == "__main__":
    unittest.main()
