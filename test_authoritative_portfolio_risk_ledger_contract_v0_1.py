import pytest

from authoritative_portfolio_risk_ledger_contract_v0_1 import (
    build_authoritative_portfolio_risk_ledger_observation,
)


def valid_ledger():
    policy_id = "toobit-dual-market-valuation"
    policy_version = "v2"
    cycle_id = "cycle-20261014T180000Z"
    currency_evidence = {
        "USDT": {
            "raw_amount": 5000.0,
            "rate_to_usdt": 1.0,
            "rate_source": "APPROVED_BASE_CURRENCY_RULE",
            "rate_observed_at": "2026-10-14T17:59:58Z",
            "valuation_policy_id": policy_id,
            "valuation_policy_version": policy_version,
            "cycle_id": cycle_id,
        },
        "USDC": {
            "raw_amount": 3000.0,
            "rate_to_usdt": 0.9995,
            "rate_source": "APPROVED_USDC_USDT_RATE_SOURCE",
            "rate_observed_at": "2026-10-14T17:59:58Z",
            "valuation_policy_id": policy_id,
            "valuation_policy_version": policy_version,
            "cycle_id": cycle_id,
        },
    }
    return {
        "ledger_state": "AVAILABLE",
        "ledger_validation": "VALID",
        "ledger_id": "portfolio-ledger-001",
        "ledger_version": "v1",
        "ledger_source": "APPROVED_ACCOUNT_WIDE_PORTFOLIO_LEDGER",
        "account_scope": "TOOBIT:SPOT_AND_FUTURES:ACCOUNT",
        "coverage_scope": "ACCOUNT_WIDE",
        "market_coverage": ["SPOT", "FUTURES"],
        "asset_scope": "USDT_REPORTING",
        "observed_at": "2026-10-14T18:00:00Z",
        "cycle_id": cycle_id,
        "spot_observed_at": "2026-10-14T17:59:58Z",
        "futures_observed_at": "2026-10-14T17:59:59Z",
        "provenance": "explicit authoritative ledger snapshot",
        "valuation_policy_state": "APPROVED",
        "valuation_policy_id": policy_id,
        "valuation_policy_version": policy_version,
        "valuation_policy_evidence": {
            "approval_state": "APPROVED",
            "policy_id": policy_id,
            "policy_version": policy_version,
            "approval_id": "management-approval-ref-test-fixture",
            "approved_by": "test-fixture-role",
            "approval_source": "git:test-fixture/valuation-policy",
            "approved_at": "2026-10-14T17:00:00Z",
            "effective_from": "2026-10-14T17:00:00Z",
            "effective_until": "2026-10-15T17:00:00Z",
            "approved_rate_sources": {
                "USDT": {"source": "APPROVED_BASE_CURRENCY_RULE", "source_reference": "git:test-fixture/usdt"},
                "USDC": {"source": "APPROVED_USDC_USDT_RATE_SOURCE", "source_reference": "https://rates.example.invalid/test-fixture"},
            },
        },
        "reporting_currency": "USDT",
        "currency_valuation_evidence": currency_evidence,
        "portfolio_capital": 7997.5,
        "usable_capital": 7000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
    }


def test_missing_authoritative_ledger_blocks_without_defaults():
    result = build_authoritative_portfolio_risk_ledger_observation(None)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "AUTHORITATIVE_ACCOUNT_WIDE_PORTFOLIO_RISK_LEDGER_REQUIRED"
    assert result["allocated_risk"] is None
    assert result["concurrent_positions"] is None
    assert result["portfolio_capital"] is None


def test_explicit_dual_market_dual_currency_ledger_is_normalized():
    result = build_authoritative_portfolio_risk_ledger_observation(valid_ledger())
    assert result["portfolio_state"] == "AVAILABLE"
    assert result["portfolio_validation"] == "VALID"
    assert result["coverage_scope"] == "ACCOUNT_WIDE"
    assert result["market_coverage"] == ["SPOT", "FUTURES"]
    assert result["cycle_id"] == "cycle-20261014T180000Z"
    assert result["valuation_policy_id"] == "toobit-dual-market-valuation"
    assert result["valuation_policy_version"] == "v2"
    assert result["reporting_currency"] == "USDT"
    assert set(result["currency_valuation_evidence"]) == {"USDT", "USDC"}
    assert result["currency_valuation_evidence"]["USDC"]["rate_to_usdt"] == 0.9995
    assert result["ledger_id"] == "portfolio-ledger-001"
    assert result["portfolio_capital"] == 7997.5
    assert result["usable_capital"] == 7000.0
    assert result["allocated_risk"] == 250.0
    assert result["concurrent_positions"] == 2


def test_symbol_scoped_provider_positions_are_not_an_account_wide_ledger():
    row = valid_ledger()
    row["coverage_scope"] = "SYMBOL_SCOPED"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_ACCOUNT_WIDE_COVERAGE_REQUIRED"


@pytest.mark.parametrize("coverage", [None, ["SPOT"], ["FUTURES"], ["SPOT", "MARGIN"], "SPOT_AND_FUTURES"])
def test_both_market_scopes_are_required(coverage):
    row = valid_ledger()
    row["market_coverage"] = coverage
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_SPOT_AND_FUTURES_COVERAGE_REQUIRED"


@pytest.mark.parametrize("field,reason", [
    ("ledger_id", "PORTFOLIO_LEDGER_ID_MISSING"),
    ("ledger_version", "PORTFOLIO_LEDGER_VERSION_MISSING"),
    ("ledger_source", "PORTFOLIO_LEDGER_SOURCE_MISSING"),
    ("account_scope", "PORTFOLIO_LEDGER_ACCOUNT_SCOPE_MISSING"),
    ("asset_scope", "PORTFOLIO_LEDGER_ASSET_SCOPE_MISSING"),
    ("observed_at", "PORTFOLIO_LEDGER_TIMESTAMP_MISSING"),
    ("cycle_id", "PORTFOLIO_LEDGER_CYCLE_ID_MISSING"),
    ("spot_observed_at", "PORTFOLIO_LEDGER_SPOT_TIMESTAMP_MISSING"),
    ("futures_observed_at", "PORTFOLIO_LEDGER_FUTURES_TIMESTAMP_MISSING"),
    ("provenance", "PORTFOLIO_LEDGER_PROVENANCE_MISSING"),
    ("valuation_policy_id", "PORTFOLIO_LEDGER_VALUATION_POLICY_ID_MISSING"),
    ("valuation_policy_version", "PORTFOLIO_LEDGER_VALUATION_POLICY_VERSION_MISSING"),
])
def test_missing_ledger_metadata_blocks(field, reason):
    row = valid_ledger()
    row[field] = ""
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == reason


def test_unapproved_valuation_policy_blocks():
    row = valid_ledger()
    row["valuation_policy_state"] = "PENDING"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_APPROVED_VALUATION_POLICY_REQUIRED"


@pytest.mark.parametrize("evidence", [None, {}, {"USDT": {}} , {"USDT": {}, "BTC": {}}])
def test_missing_or_unapproved_currency_valuation_evidence_blocks(evidence):
    row = valid_ledger()
    row["currency_valuation_evidence"] = evidence
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_USDT_USDC_VALUATION_EVIDENCE_REQUIRED"


def test_currency_valuation_requires_same_policy_and_cycle():
    row = valid_ledger()
    row["currency_valuation_evidence"]["USDC"]["valuation_policy_version"] = "old-version"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_CURRENCY_POLICY_MISMATCH"

    row = valid_ledger()
    row["currency_valuation_evidence"]["USDC"]["cycle_id"] = "other-cycle"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_CURRENCY_CYCLE_MISMATCH"


def test_usdt_base_currency_rate_must_be_one():
    row = valid_ledger()
    row["currency_valuation_evidence"]["USDT"]["rate_to_usdt"] = 0.99
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_USDT_BASE_RATE_MUST_EQUAL_ONE"


def test_non_authoritative_source_and_invalid_risk_fields_block():
    row = valid_ledger()
    row["ledger_source"] = "TOOBIT_FUTURES_POSITIONS_GET"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_SOURCE_INVALID"

    row = valid_ledger()
    row["allocated_risk"] = float("nan")
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_ALLOCATED_RISK_INVALID"


def test_usable_capital_cannot_exceed_portfolio_capital():
    row = valid_ledger()
    row["usable_capital"] = 10000
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_USABLE_CAPITAL_INVALID"


def test_ledger_contract_has_no_execution_side_effect_surface():
    result = build_authoritative_portfolio_risk_ledger_observation(valid_ledger())
    forbidden = {
        "order_id", "api_request", "signature", "execution", "submitted",
        "trade_id", "withdrawal", "execution_authorization", "order_write",
    }
    assert forbidden.isdisjoint(result)



def test_ledger_requires_explicit_valuation_policy_approval_evidence():
    row = valid_ledger()
    row.pop("valuation_policy_evidence")
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "VALUATION_POLICY_APPROVAL_EVIDENCE_REQUIRED"


def test_currency_rate_source_must_match_approved_policy():
    row = valid_ledger()
    row["currency_valuation_evidence"]["USDC"]["rate_source"] = "UNAPPROVED_SOURCE"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_CURRENCY_RATE_SOURCE_NOT_APPROVED"


def test_policy_identity_must_match_ledger_policy_identity():
    row = valid_ledger()
    row["valuation_policy_evidence"]["policy_version"] = "different-version"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_VALUATION_POLICY_EVIDENCE_MISMATCH"
