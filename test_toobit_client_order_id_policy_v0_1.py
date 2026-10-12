from exchange_execution_idempotency_contract_v0_1 import validate_client_order_id_policy
from toobit_client_order_id_policy_v0_1 import (
    TOOBIT_ERROR_CODES_DOCS,
    TOOBIT_FUTURES_V2_DOCS,
    toobit_futures_client_order_id_policy,
)
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def test_toobit_policy_records_only_officially_supported_futures_id_facts():
    policy = toobit_futures_client_order_id_policy()

    assert policy["provider_namespace"] == "TOOBIT-FUTURES"
    assert policy["scope"] == "USDT-M_FUTURES_REGULAR_ORDERS"
    assert policy["evidence_status"] == "PARTIALLY_VERIFIED"
    assert policy["evidence_verified"] is True
    evidence = policy["evidence"]
    assert evidence["submit_parameter"] == "newClientOrderId"
    assert evidence["lookup_parameter"] == "origClientOrderId"
    assert evidence["lookup_endpoint"] == "GET /api/v2/futures/order"
    assert evidence["duplicate_error_code"] == -1141
    assert evidence["duplicate_error_name"] == "ORDER_DUPLICATED"
    assert evidence["documented_uniqueness_scope"] == "among open orders"
    assert evidence["sources"] == [TOOBIT_FUTURES_V2_DOCS, TOOBIT_ERROR_CODES_DOCS]


def test_toobit_policy_does_not_promote_partial_evidence_to_execution_approval():
    policy = ToobitExchangeAdapter().stable_client_order_id_policy()

    assert policy["verified"] is False
    assert policy["max_length"] is None
    assert policy["allowed_pattern"] is None
    assert "CLIENT_ORDER_ID_MAX_LENGTH" in policy["unverified"]
    assert "CLIENT_ORDER_ID_ALLOWED_CHARSET" in policy["unverified"]
    assert "RETRY_OR_REPLAY_IDEMPOTENCY_SEMANTICS" in policy["unverified"]
    assert "LOOKUP_CONSISTENCY_AND_RETENTION" in policy["unverified"]
    assert policy["verification_blocker"] == (
        "TOOBIT_CLIENT_ORDER_ID_CHARSET_AND_MAX_LENGTH_UNVERIFIED"
    )

    valid, reason = validate_client_order_id_policy(policy)
    assert valid is False
    assert reason == "CLIENT_ORDER_ID_PROVIDER_POLICY_UNVERIFIED"


def test_toobit_official_duplicate_error_is_not_misrepresented_as_idempotent_replay():
    policy = toobit_futures_client_order_id_policy()
    evidence = policy["evidence"]

    # Official docs establish duplicate-ID rejection, not exactly-once replay.
    assert evidence["duplicate_error_code"] == -1141
    assert evidence["duplicate_error_name"] == "ORDER_DUPLICATED"
    assert "RETRY_OR_REPLAY_IDEMPOTENCY_SEMANTICS" in policy["unverified"]
    assert policy["verified"] is False
