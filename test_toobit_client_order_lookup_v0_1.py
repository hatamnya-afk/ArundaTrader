        AdapterOrderPreparation(
            ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT", request=None
        ),
        "AR-STABLE-002",
    )

    assert missing.ready is False
    assert missing.reason == "STABLE_CLIENT_ORDER_ID_REQUIRED"
    assert invalid.ready is False
    assert invalid.reason == "TOOBIT_ORDER_PAYLOAD_INVALID"


def test_toobit_policy_records_confirmed_id_constraints_but_keeps_submission_unapproved():
    policy = ToobitExchangeAdapter().stable_client_order_id_policy()
    assert policy["verified"] is False
    assert policy["client_id_constraints_verified"] is True
    assert policy["provider_max_length"] == 255
    assert policy["max_length"] == 64
    assert policy["allowed_pattern"] == r"^[A-Za-z0-9_-]{1,64}$"
    assert policy["submission_enabled"] is False
    assert policy["verification_blocker"] == "TOOBIT_AMBIGUOUS_TIMEOUT_RECOVERY_UNSPECIFIED"
