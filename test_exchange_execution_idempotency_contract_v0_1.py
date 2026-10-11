"""Offline tests for deterministic provider client-order ID derivation."""
import pytest

from exchange_execution_idempotency_contract_v0_1 import derive_client_order_id

def test_same_provider_and_intent_produce_same_id_across_calls():
    first = derive_client_order_id(provider_namespace="TOOBIT-FUTURES", intent_id="INTENT-123", max_length=32)
    second = derive_client_order_id(provider_namespace="toobit-futures", intent_id="INTENT-123", max_length=32)
    assert first == second
    assert len(first) == 32

def test_different_intents_produce_different_ids():
    common = {"provider_namespace": "TOOBIT-FUTURES", "max_length": 32}
    assert derive_client_order_id(intent_id="INTENT-123", **common) != derive_client_order_id(intent_id="INTENT-124", **common)

def test_provider_namespace_separates_identifiers():
    common = {"intent_id": "INTENT-123", "max_length": 32}
    assert derive_client_order_id(provider_namespace="VENUE-A", **common) != derive_client_order_id(provider_namespace="VENUE-B", **common)

def test_surrounding_intent_whitespace_does_not_change_canonical_id():
    common = {"provider_namespace": "VENUE-A", "max_length": 32}
    assert derive_client_order_id(intent_id=" INTENT-123 ", **common) == derive_client_order_id(intent_id="INTENT-123", **common)

def test_output_uses_safe_alphanumeric_prefix_and_digest():
    value = derive_client_order_id(provider_namespace="VENUE-A", intent_id="INTENT-123", prefix="ar", max_length=32)
    assert value.startswith("AR") and value.isalnum() and value.isupper()

@pytest.mark.parametrize(("kwargs", "reason"), [
    ({"provider_namespace": "", "intent_id": "I-1", "max_length": 32}, "PROVIDER_NAMESPACE_REQUIRED"),
    ({"provider_namespace": "VENUE-A", "intent_id": " ", "max_length": 32}, "CANONICAL_INTENT_ID_REQUIRED"),
    ({"provider_namespace": "VENUE-A", "intent_id": "I-1", "prefix": "A-", "max_length": 32}, "CLIENT_ORDER_ID_PREFIX_INVALID"),
    ({"provider_namespace": "VENUE-A", "intent_id": "I-1", "max_length": 17}, "CLIENT_ORDER_ID_LENGTH_CONSTRAINT_INVALID"),
    ({"provider_namespace": "VENUE-A", "intent_id": "I-1", "max_length": 129}, "CLIENT_ORDER_ID_LENGTH_CONSTRAINT_INVALID"),
])
def test_invalid_contract_inputs_fail_closed(kwargs, reason):
    with pytest.raises(ValueError, match=reason):
        derive_client_order_id(**kwargs)

def test_boolean_length_is_rejected_even_though_bool_is_an_int():
    with pytest.raises(ValueError, match="CLIENT_ORDER_ID_LENGTH_CONSTRAINT_INVALID"):
        derive_client_order_id(provider_namespace="VENUE-A", intent_id="I-1", max_length=True)
