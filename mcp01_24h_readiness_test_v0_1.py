"""Focused verification for MCP-01.8 24/7 readiness."""

from mcp01_24h_readiness_v0_1 import (
    REQUIRED_COMPONENTS,
    SCHEMA,
    SCHEMA_VERSION,
    verify_24h_readiness,
)


ALL = REQUIRED_COMPONENTS


def full_checks(**overrides):
    values = {
        "continuity_verified": True,
        "bounded_output_verified": True,
        "idempotence_verified": True,
        "isolated_failure_recovery_verified": True,
        "trader_intelligence_unchanged_verified": True,
    }
    values.update(overrides)
    return values


def test_all_readiness_invariants_pass():
    result = verify_24h_readiness(
        available_components=ALL,
        **full_checks(),
    )
    assert result["schema"] == SCHEMA
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["components_missing"] == []
    assert result["structural_checks_failed"] == []
    assert result["ready_for_24h_activation"] is True
    assert result["activation_enabled"] is False


def test_missing_component_blocks_readiness():
    result = verify_24h_readiness(
        available_components=ALL[:-1],
        **full_checks(),
    )
    assert "24h_email" in result["components_missing"]
    assert result["ready_for_24h_activation"] is False


def test_missing_operational_invariant_blocks_readiness():
    result = verify_24h_readiness(
        available_components=ALL,
        **full_checks(idempotence_verified=False),
    )
    assert "idempotence_verified" in result["structural_checks_failed"]
    assert result["ready_for_24h_activation"] is False


def test_active_scheduler_blocks_readiness():
    result = verify_24h_readiness(
        available_components=ALL,
        scheduler_active=True,
        **full_checks(),
    )
    assert "24h_scheduler_active_before_management_gate" in result[
        "structural_checks_failed"
    ]
    assert result["ready_for_24h_activation"] is False
    assert result["activation_enabled"] is False


def test_management_authorization_does_not_bypass_readiness():
    result = verify_24h_readiness(
        available_components=ALL,
        management_authorized=True,
        email_delivery_enabled=True,
        **full_checks(continuity_verified=False),
    )
    assert result["ready_for_24h_activation"] is False
    assert result["activation_enabled"] is False


def test_activation_requires_ready_email_and_management_gate():
    result = verify_24h_readiness(
        available_components=ALL,
        email_delivery_enabled=True,
        management_authorized=True,
        **full_checks(),
    )
    assert result["ready_for_24h_activation"] is True
    assert result["activation_enabled"] is True


def main():
    tests = (
        test_all_readiness_invariants_pass,
        test_missing_component_blocks_readiness,
        test_missing_operational_invariant_blocks_readiness,
        test_active_scheduler_blocks_readiness,
        test_management_authorization_does_not_bypass_readiness,
        test_activation_requires_ready_email_and_management_gate,
    )
    for test in tests:
        test()
    print("MCP01.8_24_7_READINESS_TESTS=6/6 PASS")


if __name__ == "__main__":
    main()
