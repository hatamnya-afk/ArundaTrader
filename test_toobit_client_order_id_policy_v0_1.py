from exchange_execution_idempotency_contract_v0_1 import validate_client_order_id_policy
from toobit_client_order_id_policy_v0_1 import (
    TOOBIT_ERROR_CODES_DOCS,
    TOOBIT_FUTURES_V2_DOCS,
    TOOBIT_SUPPORT_TICKET,
    toobit_futures_client_order_id_policy,
)
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def test_toobit_support_reply_records_usdtm_client_id_constraints():
    policy = toobit_futures_client_order_id_policy()

    assert policy["provider_namespace"] == "TOOBIT-FUTURES-USDTM"
    assert policy["scope"] == "USDT-M_FUTURES_REGULAR_ORDERS"
    assert policy["evidence_status"] == "SUPPORT_CONFIRMED_CONSTRAINTS_RECOVERY_UNRESOLVED"
    assert policy["evidence_verified"] is True
    assert policy["client_id_constraints_verified"] is True
    assert policy["provider_max_length"] == 255
    assert policy["max_length"] == 64  # conservative local cap, not provider hard max
    assert policy["allowed_pattern"] == r"^[A-Za-z0-9_-]{1,64}$"
    assert policy["submission_enabled"] is False
    assert policy["automatic_retry_after_ambiguous_submit"] is False
    assert policy["support_ticket"] == TOOBIT_SUPPORT_TICKET

    evidence = policy["evidence"]
    assert evidence["provider_hard_max_length"] == 255
    assert evidence["provider_regex_validation"] is False
    assert evidence["provider_recommended_charset"] == "[A-Za-z0-9_-]"
    assert evidence["provider_recommended_length"] == [36, 64]
    assert evidence["provider_uniqueness_scope"] == "order-level"
    assert evidence["provider_id_reuse_after_terminal_state"] is False
    assert evidence["duplicate_submission"] == "rejected; original result is not returned"
    assert evidence["history_retention"] == "six months"
    assert evidence["history_direct_client_id_query"] is False
    assert evidence["history_excludes_creation_failures"] is True
    assert evidence["maximum_lookup_propagation_delay"] is None
    assert evidence["timeout_then_not_found_recovery_procedure"] is None
    assert evidence["history_exhaustive_recovery_by_client_id"] is False
    assert evidence["sources"] == [TOOBIT_FUTURES_V2_DOCS, TOOBIT_ERROR_CODES_DOCS, TOOBIT_SUPPORT_TICKET]


def test_recovery_gap_keeps_execution_policy_fail_closed():
    policy = ToobitExchangeAdapter().stable_client_order_id_policy()

    assert policy["verified"] is False
    assert policy["submission_enabled"] is False
    assert policy["automatic_retry_after_ambiguous_submit"] is False
    assert "SAFE_RECOVERY_AFTER_TIMEOUT_AND_NOT_FOUND" in policy["unverified"]
    assert "EXHAUSTIVE_HISTORY_RECOVERY_BY_CLIENT_ID" in policy["unverified"]
    assert "USDC_M_CLIENT_ID_CONSTRAINT_VALUES" in policy["unverified"]
    assert policy["evidence_record"] == "TOOBIT_CLIENT_ORDER_ID_OFFICIAL_EVIDENCE_V0_3.md"
    assert policy["verification_blocker"] == "TOOBIT_AMBIGUOUS_TIMEOUT_RECOVERY_UNSPECIFIED"

    valid, reason = validate_client_order_id_policy(policy)
    assert valid is False
    assert reason == "CLIENT_ORDER_ID_PROVIDER_POLICY_UNVERIFIED"


def test_duplicate_submission_is_not_treated_as_original_order_replay():
    policy = toobit_futures_client_order_id_policy()
    evidence = policy["evidence"]

    assert evidence["duplicate_error_code"] == -1141
    assert evidence["duplicate_error_name"] == "ORDER_DUPLICATED"
    assert "original result is not returned" in evidence["duplicate_submission"]
    assert policy["verified"] is False
    assert policy["submission_enabled"] is False


def test_usdc_m_constraints_are_not_inferred_from_usdt_m_answer():
    policy = toobit_futures_client_order_id_policy()
    assert policy["scope"] == "USDT-M_FUTURES_REGULAR_ORDERS"
    assert "USDC_M_CLIENT_ID_CONSTRAINT_VALUES" in policy["unverified"]
    assert "USDC-M" in policy["local_policy_notes"]["scope"]


def test_official_evidence_record_does_not_approve_execution():
    policy = toobit_futures_client_order_id_policy()
    assert policy["evidence_status"] == "SUPPORT_CONFIRMED_CONSTRAINTS_RECOVERY_UNRESOLVED"
    assert policy["client_id_constraints_verified"] is True
    assert policy["verified"] is False
    assert policy["submission_enabled"] is False
