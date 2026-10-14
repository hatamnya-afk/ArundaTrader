from dataclasses import dataclass

from toobit_raw_account_observation_producer_v0_1 import (
    build_toobit_raw_account_observation,
)


@dataclass
class AdapterResult:
    allowed: bool
    reason: str
    data: dict | None = None


def test_preserves_raw_balances_but_never_claims_capital():
    raw = [{"asset": "USDT", "free": "100", "locked": "3"}]
    result = build_toobit_raw_account_observation(
        adapter_result=AdapterResult(True, "OK", {"state_known": True, "balances": raw}),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:SPOT:ACCOUNT",
        provenance="signed GET /api/v1/account; captured by caller",
    )
    assert result["observation_state"] == "AVAILABLE"
    assert result["observation_validation"] == "RAW_PROVIDER_EVIDENCE_ONLY"
    assert result["balances"] == raw
    assert result["capital_state"] == "BLOCKED"
    assert result["available_capital"] is None
    assert result["usable_capital"] is None


def test_missing_timestamp_blocks_without_inventing_one():
    result = build_toobit_raw_account_observation(
        adapter_result=AdapterResult(True, "OK", {"state_known": True, "balances": []}),
        observed_at="",
        account_scope="TOOBIT:SPOT:ACCOUNT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["capital_state"] == "BLOCKED"
    assert result["balances"] is None
    assert result["capital_block_reason"] == "TOOBIT_ACCOUNT_OBSERVATION_TIMESTAMP_MISSING"


def test_failed_provider_read_blocks():
    result = build_toobit_raw_account_observation(
        adapter_result=AdapterResult(False, "TOOBIT_CREDENTIALS_UNAVAILABLE"),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:SPOT:ACCOUNT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["capital_block_reason"] == "TOOBIT_CREDENTIALS_UNAVAILABLE"


def test_malformed_provider_balance_rows_block():
    result = build_toobit_raw_account_observation(
        adapter_result=AdapterResult(True, "OK", {"state_known": True, "balances": ["bad"]}),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:SPOT:ACCOUNT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["capital_block_reason"] == "TOOBIT_ACCOUNT_BALANCES_INVALID"
