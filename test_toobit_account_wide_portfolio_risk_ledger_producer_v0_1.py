import pytest

from toobit_account_wide_portfolio_risk_ledger_producer_v0_1 import (
    build_toobit_account_wide_portfolio_risk_ledger,
)


def policy():
    return {
        "approval_state": "APPROVED",
        "policy_id": "fixture-policy",
        "policy_version": "v1",
        "approval_id": "fixture-approval",
        "approved_by": "test-fixture-only",
        "approval_source": "git:test-fixture/approval",
        "approved_at": "2026-10-14T17:00:00Z",
        "effective_from": "2026-10-14T17:00:00Z",
        "effective_until": "2026-10-15T17:00:00Z",
        "approved_rate_sources": {
            "USDT": {"source": "USDT_BASE", "source_reference": "git:test-fixture/usdt"},
            "USDC": {"source": "USDC_RATE", "source_reference": "https://rates.example.invalid/fixture"},
        },
    }


def observations():
    common = {
        "observation_state": "AVAILABLE",
        "account_scope": "TOOBIT:ACCOUNT:FIXTURE",
        "cycle_id": "cycle-fixture-1",
        "observed_at": "2026-10-14T18:00:00Z",
        "coverage_scope": "ACCOUNT_WIDE",
    }
    spot = {
        **common,
        "observation_source": "TOOBIT_SPOT_ACCOUNT_GET",
        "balances": [
            {"asset": "USDT", "total_amount": 1000.0, "usable_amount": 900.0},
            {"asset": "USDC", "total_amount": 200.0, "usable_amount": 150.0},
        ],
    }
    futures = {
        **common,
        "observation_source": "TOOBIT_FUTURES_ACCOUNT_GET",
        "balances": [
            {"asset": "USDT", "total_amount": 300.0, "usable_amount": 250.0},
            {"asset": "USDC", "total_amount": 100.0, "usable_amount": 80.0},
        ],
        "positions_coverage": "ACCOUNT_WIDE",
        "positions": [
            {"symbol": "BTC-SWAP-USDT", "allocated_risk_usdt": 12.0},
            {"symbol": "ETH-SWAP-USDT", "allocated_risk_usdt": 8.0},
        ],
    }
    currency = {
        "USDT": {
            "rate_to_usdt": 1.0, "rate_source": "USDT_BASE",
            "rate_observed_at": "2026-10-14T18:00:00Z",
            "valuation_policy_id": "fixture-policy", "valuation_policy_version": "v1",
            "cycle_id": "cycle-fixture-1",
        },
        "USDC": {
            "rate_to_usdt": 0.999, "rate_source": "USDC_RATE",
            "rate_observed_at": "2026-10-14T18:00:00Z",
            "valuation_policy_id": "fixture-policy", "valuation_policy_version": "v1",
            "cycle_id": "cycle-fixture-1",
        },
    }
    return spot, futures, currency


def build(**overrides):
    spot, futures, currency = observations()
    args = {
        "spot_observation": spot,
        "futures_observation": futures,
        "valuation_policy_evidence": policy(),
        "currency_valuation_evidence": currency,
        "ledger_id": "fixture-ledger",
        "ledger_version": "v1",
        "account_scope": "TOOBIT:ACCOUNT:FIXTURE",
        "observed_at": "2026-10-14T18:00:00Z",
        "cycle_id": "cycle-fixture-1",
        "provenance": "test fixture only; not exchange data",
        "allocated_risk_usdt": 20.0,
    }
    args.update(overrides)
    return build_toobit_account_wide_portfolio_risk_ledger(**args)


def test_aggregates_explicit_account_wide_dual_market_stablecoin_evidence():
    result = build()
    assert result["producer_state"] == "AVAILABLE"
    assert result["portfolio_state"] == "AVAILABLE"
    assert result["portfolio_capital"] == pytest.approx(1599.7)
    assert result["usable_capital"] == pytest.approx(1379.77)
    assert result["allocated_risk"] == 20.0
    assert result["concurrent_positions"] == 2
    assert result["market_coverage"] == ["SPOT", "FUTURES"]


def test_missing_one_market_blocks():
    result = build(futures_observation=None)
    assert result["producer_state"] == "BLOCKED"
    assert result["portfolio_capital"] is None


def test_symbol_scoped_futures_positions_block():
    spot, futures, currency = observations()
    futures["positions_coverage"] = "SYMBOL_SCOPED"
    result = build(spot_observation=spot, futures_observation=futures, currency_valuation_evidence=currency)
    assert result["producer_state"] == "BLOCKED"
    assert result["producer_block_reason"] == "PORTFOLIO_LEDGER_ACCOUNT_WIDE_POSITIONS_REQUIRED"


def test_nonzero_unvalued_asset_blocks_instead_of_understating_capital():
    spot, futures, currency = observations()
    spot["balances"].append({"asset": "BTC", "total_amount": 0.01, "usable_amount": 0.01})
    result = build(spot_observation=spot, futures_observation=futures, currency_valuation_evidence=currency)
    assert result["producer_state"] == "BLOCKED"
    assert result["producer_block_reason"] == "PORTFOLIO_LEDGER_UNVALUED_NONZERO_ASSET:SPOT:BTC"


def test_cycle_mismatch_blocks():
    spot, futures, currency = observations()
    futures["cycle_id"] = "different-cycle"
    result = build(spot_observation=spot, futures_observation=futures, currency_valuation_evidence=currency)
    assert result["producer_state"] == "BLOCKED"
    assert result["producer_block_reason"] == "PORTFOLIO_LEDGER_FUTURES_CYCLE_MISMATCH"


def test_allocated_risk_must_match_position_evidence():
    result = build(allocated_risk_usdt=19.0)
    assert result["producer_state"] == "BLOCKED"
    assert result["producer_block_reason"] == "PORTFOLIO_LEDGER_ALLOCATED_RISK_TOTAL_MISMATCH"


def test_unapproved_rate_source_blocks():
    spot, futures, currency = observations()
    currency["USDC"]["rate_source"] = "UNAPPROVED"
    result = build(spot_observation=spot, futures_observation=futures, currency_valuation_evidence=currency)
    assert result["producer_state"] == "BLOCKED"
    assert result["producer_block_reason"] == "PORTFOLIO_LEDGER_CURRENCY_RATE_SOURCE_NOT_APPROVED"


def test_missing_valuation_policy_blocks():
    result = build(valuation_policy_evidence=None)
    assert result["producer_state"] == "BLOCKED"
    assert result["portfolio_capital"] is None


def test_no_execution_or_database_side_effect_surface():
    result = build()
    forbidden = {"order_id", "submit_order", "cancel_order", "database_write", "execution_enabled"}
    assert forbidden.isdisjoint(result)
