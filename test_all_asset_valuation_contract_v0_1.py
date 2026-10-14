import pytest

from all_asset_valuation_contract_v0_1 import validate_all_asset_valuation_evidence


def inputs():
    policy = {
        "approval_state": "APPROVED", "policy_id": "fixture-policy", "policy_version": "v1",
        "approval_id": "fixture-approval", "approved_by": "fixture-only",
        "approval_source": "git:fixture/policy", "approved_at": "2026-10-14T17:00:00Z",
        "effective_from": "2026-10-14T17:00:00Z", "effective_until": "2026-10-15T17:00:00Z",
        "approved_rate_sources": {
            "USDT": {"source": "BASE", "source_reference": "git:fixture/usdt"},
            "USDC": {"source": "MARKET", "source_reference": "https://fixture.invalid/usdc"},
            "BTC": {"source": "ORACLE", "source_reference": "https://fixture.invalid/btc"},
        },
    }
    observed = "2026-10-14T18:00:00Z"
    rates = {
        "USDT": {"rate_to_usdt": 1.0, "rate_source": "BASE", "source_reference": "git:fixture/usdt",
                 "rate_observed_at": observed, "cycle_id": "cycle-1", "valuation_policy_id": "fixture-policy", "valuation_policy_version": "v1"},
        "USDC": {"rate_to_usdt": 0.999, "rate_source": "MARKET", "source_reference": "https://fixture.invalid/usdc",
                 "rate_observed_at": observed, "cycle_id": "cycle-1", "valuation_policy_id": "fixture-policy", "valuation_policy_version": "v1"},
        "BTC": {"rate_to_usdt": 65000.0, "rate_source": "ORACLE", "source_reference": "https://fixture.invalid/btc",
                "rate_observed_at": observed, "cycle_id": "cycle-1", "valuation_policy_id": "fixture-policy", "valuation_policy_version": "v1"},
    }
    return {"balances_by_asset": {"USDT": 100, "USDC": 10, "BTC": 0.01},
            "valuation_evidence": rates, "policy_evidence": policy, "observed_at": observed,
            "cycle_id": "cycle-1", "max_rate_age_seconds": 60}


def test_values_every_nonzero_asset_without_assuming_stablecoin_parity():
    result = validate_all_asset_valuation_evidence(**inputs())
    assert result["valuation_state"] == "AVAILABLE"
    assert result["valued_assets"] == ["BTC", "USDC", "USDT"]
    assert result["asset_rates"]["USDC"]["rate_to_usdt"] == 0.999
    assert result["asset_rates"]["BTC"]["rate_to_usdt"] == 65000.0


def test_any_nonzero_unpriced_asset_blocks():
    args = inputs()
    args["balances_by_asset"]["ETH"] = 0.2
    result = validate_all_asset_valuation_evidence(**args)
    assert result["valuation_state"] == "BLOCKED"
    assert result["valuation_block_reason"] == "ALL_ASSET_NONZERO_ASSET_RATE_MISSING:ETH"


def test_missing_valuation_for_nonzero_asset_blocks():
    args = inputs()
    del args["valuation_evidence"]["BTC"]
    assert validate_all_asset_valuation_evidence(**args)["valuation_state"] == "BLOCKED"


def test_stale_rate_blocks():
    args = inputs()
    args["valuation_evidence"]["BTC"]["rate_observed_at"] = "2026-10-14T17:00:00Z"
    assert validate_all_asset_valuation_evidence(**args)["valuation_block_reason"] == "ALL_ASSET_RATE_STALE_OR_FUTURE:BTC"


def test_unapproved_source_blocks():
    args = inputs()
    args["valuation_evidence"]["BTC"]["rate_source"] = "UNAPPROVED"
    assert validate_all_asset_valuation_evidence(**args)["valuation_state"] == "BLOCKED"


def test_cycle_mismatch_blocks():
    args = inputs()
    args["valuation_evidence"]["BTC"]["cycle_id"] = "other"
    assert validate_all_asset_valuation_evidence(**args)["valuation_block_reason"] == "ALL_ASSET_RATE_CYCLE_MISMATCH:BTC"


def test_unheld_asset_rate_blocks_to_avoid_ambiguous_snapshot():
    args = inputs()
    args["balances_by_asset"]["BTC"] = 0
    assert validate_all_asset_valuation_evidence(**args)["valuation_block_reason"] == "ALL_ASSET_RATE_FOR_UNHELD_ASSET:BTC"


def test_no_network_execution_or_db_surface():
    result = validate_all_asset_valuation_evidence(**inputs())
    assert not {"submit_order", "cancel_order", "database_write", "network_call"} & result.keys()
