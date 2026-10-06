"""Focused verification for MCP-01.7 one-email formatter."""

from mcp01_24h_email_v0_1 import build_24h_email


def report(**overrides):
    value = {
        "schema": "arunda.24h_intelligence",
        "schema_version": "1.0",
        "period": {"start": "2026-10-05T00:00:00Z", "end": "2026-10-06T00:00:00Z"},
        "cycles": {"count": 24},
        "cases": {"unique_count": 12},
        "trades": {"unique_count": 5},
        "reconciliation": {"complete_provider_chains": 4, "market_outcomes": 2, "case_outcomes": 1},
        "data_quality": {"event_count": 3},
    }
    value.update(overrides)
    return value


def test_builds_one_compact_email():
    email = build_24h_email(report())
    assert email["schema"] == "arunda.24h_email"
    assert email["schema_version"] == "1.0"
    assert email["subject"] == "ArundaTrader 24H Intelligence | 2026-10-05T00:00:00Z → 2026-10-06T00:00:00Z"
    assert "Cycles: 24" in email["body"]
    assert "Unique Cases: 12" in email["body"]
    assert "Unique Trade Events: 5" in email["body"]
    assert "Complete Provider Chains: 4" in email["body"]
    assert "Market Outcomes: 2" in email["body"]
    assert "Case Outcomes: 1" in email["body"]
    assert "Data Quality Events: 3" in email["body"]
    assert email["delivery"] == {
        "mode": "ONE_EMAIL_PER_24H_PERIOD",
        "enabled": False,
        "activation_requires_management_authorization": True,
    }


def test_formatter_does_not_activate_delivery():
    email = build_24h_email(report())
    assert email["delivery"]["enabled"] is False
    assert email["delivery"]["activation_requires_management_authorization"] is True


def test_invalid_schema_is_rejected():
    try:
        build_24h_email(report(schema="wrong.schema"))
    except ValueError as exc:
        assert "schema" in str(exc)
    else:
        raise AssertionError("invalid schema was not rejected")


def test_invalid_version_is_rejected():
    try:
        build_24h_email(report(schema_version="9.9"))
    except ValueError as exc:
        assert "version" in str(exc)
    else:
        raise AssertionError("invalid version was not rejected")


def test_missing_management_sections_are_rejected():
    broken = report()
    broken["reconciliation"] = None
    try:
        build_24h_email(broken)
    except ValueError as exc:
        assert "reconciliation" in str(exc)
    else:
        raise AssertionError("missing reconciliation section was not rejected")


def test_negative_count_is_rejected():
    broken = report()
    broken["trades"] = {"unique_count": -1}
    try:
        build_24h_email(broken)
    except ValueError as exc:
        assert "unique_count" in str(exc)
    else:
        raise AssertionError("negative count was not rejected")


if __name__ == "__main__":
    test_builds_one_compact_email()
    test_formatter_does_not_activate_delivery()
    test_invalid_schema_is_rejected()
    test_invalid_version_is_rejected()
    test_missing_management_sections_are_rejected()
    test_negative_count_is_rejected()
    print("MCP01.7_24H_EMAIL_TESTS=6/6 PASS")
