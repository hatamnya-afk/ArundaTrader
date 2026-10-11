import unittest

from dynamic_risk_budget_sizing_bridge_v0_1 import build_dynamic_risk_budget_and_sizing


def candles(count=15):
    return [
        {"high": 102.0, "low": 98.0, "close": 100.0}
        for _ in range(count)
    ]


def inputs(assets):
    decisions = {}
    risks = {}
    opportunities = {}
    market = {}
    for asset, direction in assets:
        decisions[asset] = {"state": "ACTIONABLE", "direction": direction}
        risks[asset] = {"asset": f"{asset}/USDT", "risk_state": "APPROVED", "direction": direction}
        opportunities[asset] = {"asset": f"{asset}/USDT", "price": 100.0}
        market[f"{asset}/USDT"] = {"candles": candles()}
    return decisions, risks, opportunities, market


class DynamicRiskBudgetSizingTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "capital": 100000.0,
            "available_capital": 100000.0,
            "risk_per_trade": 0.005,
            "max_portfolio_risk": 0.01,
            "max_concurrent_positions": 2,
        }

    def test_variable_universe_sizes_with_existing_formula(self):
        d, r, o, m = inputs([("AAA", "LONG"), ("BBB", "SHORT")])
        result = build_dynamic_risk_budget_and_sizing(
            decision_snapshot=d, risk_snapshot=r, opportunity_by_asset=o,
            market_data_by_symbol=m, capital_config=self.config,
        )
        self.assertEqual(result["AAA"]["position_sizing_state"], "CALCULATED")
        self.assertAlmostEqual(result["AAA"]["risk_budget"], 500.0)
        self.assertAlmostEqual(result["AAA"]["stop_distance"], 6.0)
        self.assertAlmostEqual(result["AAA"]["position_quantity"], 500.0 / 6.0)
        self.assertAlmostEqual(result["AAA"]["stop_price"], 94.0)
        self.assertAlmostEqual(result["BBB"]["stop_price"], 106.0)
        self.assertEqual(result["AAA"]["quantity_source"], "POSITION_SIZING.position_size")
        self.assertEqual(result["AAA"]["quantity_unit"], "BASE_ASSET")

    def test_capacity_respects_max_concurrent_and_portfolio_risk(self):
        d, r, o, m = inputs([("AAA", "LONG"), ("BBB", "LONG"), ("CCC", "SHORT")])
        result = build_dynamic_risk_budget_and_sizing(
            decision_snapshot=d, risk_snapshot=r, opportunity_by_asset=o,
            market_data_by_symbol=m, capital_config=self.config,
        )
        self.assertEqual(sum(x["position_sizing_state"] == "CALCULATED" for x in result.values()), 2)
        self.assertEqual(result["CCC"]["position_sizing_reason"], "PORTFOLIO_RISK_CAPACITY_EXCEEDED")
        self.assertIsNone(result["CCC"]["position_quantity"])

    def test_missing_current_candles_fails_closed_without_consuming_slot(self):
        d, r, o, m = inputs([("AAA", "LONG"), ("BBB", "SHORT")])
        m["AAA/USDT"] = {"candles": candles(7)}
        result = build_dynamic_risk_budget_and_sizing(
            decision_snapshot=d, risk_snapshot=r, opportunity_by_asset=o,
            market_data_by_symbol=m, capital_config=self.config,
        )
        self.assertEqual(result["AAA"]["position_sizing_state"], "BLOCKED")
        self.assertEqual(result["AAA"]["position_sizing_reason"], "REAL_ATR14_STOP_DISTANCE_UNAVAILABLE")
        self.assertEqual(result["BBB"]["position_sizing_state"], "CALCULATED")

    def test_non_actionable_candidate_is_not_sized(self):
        d, r, o, m = inputs([("AAA", "LONG")])
        d["AAA"]["state"] = "HOLD"
        result = build_dynamic_risk_budget_and_sizing(
            decision_snapshot=d, risk_snapshot=r, opportunity_by_asset=o,
            market_data_by_symbol=m, capital_config=self.config,
        )
        self.assertEqual(result["AAA"]["position_sizing_state"], "BLOCKED")
        self.assertIsNone(result["AAA"]["position_quantity"])

    def test_invalid_capital_policy_fails_closed(self):
        d, r, o, m = inputs([("AAA", "LONG")])
        bad = dict(self.config, risk_per_trade=0.0)
        with self.assertRaises(ValueError):
            build_dynamic_risk_budget_and_sizing(
                decision_snapshot=d, risk_snapshot=r, opportunity_by_asset=o,
                market_data_by_symbol=m, capital_config=bad,
            )


if __name__ == "__main__":
    unittest.main()
