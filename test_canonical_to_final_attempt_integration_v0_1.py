"""Offline end-to-end contract: canonical runtime producer -> final attempt boundary.

Uses only in-memory fixtures and a fake adapter that returns a rejection.
Never contacts an exchange or persists a claim to a database.
"""
import json
import exchange_execution_contract as execution_contract
from unittest.mock import patch
from canonical_request_runtime_producer_v0_1 import (
    produce_canonical_requests_from_runtime_outputs,
)
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract
from test_canonical_request_runtime_producer_v0_1 import snapshots
from test_final_execution_attempt_contract_v0_1 import (
    _FakeAdapter,
    _FakeClaimStore,
    _standing_mandate,
)


def test_canonical_runtime_output_reaches_final_attempt_boundary_offline():
    policy = json.dumps({
        "policy_id": "TEST-ONLY-POLICY",
        "policy_version": "TEST-ONLY-V1",
        "venue": "SPOT",
    })
    with patch.dict("os.environ", {"ARUNDA_EXECUTION_POLICY_JSON": policy}):
        decision, risk, gate, intents, _management_observation = snapshots()
        records = produce_canonical_requests_from_runtime_outputs(
            decision_snapshot=decision,
            risk_snapshot=risk,
            trade_gate_snapshot=gate,
            order_intents=intents,
            management_observation={
                "decision": "AUTHORIZED",
                "mandate_id": "TEST-ONLY",
                "issued_at": "test",
                "expires_at": "test",
                "environment": "REAL_PRODUCTION",
            },
        )
    record = records["BTC"]

    with patch.object(execution_contract, "safety_contract", return_value={
        "EXECUTION_ENABLED": True,
        "ORDER_SUBMISSION_ENABLED": True,
        "EXCHANGE_WRITE_ENABLED": True,
    }):
        result = run_final_execution_attempt_contract(
            execution_ready_package=record["execution_ready_package"],
            request=record["request"],
            authorization_observation=_standing_mandate(),
            mandate_status_observation=_active_mandate_status(),
            adapter=_FakeAdapter(),
            venue=record["venue"],
            execution_instrument=record["execution_instrument"],
            claim_store=_FakeClaimStore(),
        )

    # Proves the canonical request reaches the final boundary and the adapter
    # is invoked only as an offline test double; no accepted order is produced.
    assert result.accepted is False
    assert result.exchange_order_id is None
    assert result.error_code == "TEST_PROVIDER_REJECTION"
    assert record["request"].decision_id == decision["BTC"]["decision_id"]
    assert record["execution_instrument"].venue == "SPOT"
