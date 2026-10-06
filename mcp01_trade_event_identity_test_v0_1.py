"""Focused tests for the authoritative trade-event identity issuer."""

from mcp01_trade_event_identity_v0_1 import (
    issue_trade_event_id,
    validate_trade_event_id,
)


def test_issuer_produces_valid_identity():
    value = issue_trade_event_id()
    assert validate_trade_event_id(value) is True


def test_each_attempt_gets_distinct_identity():
    first = issue_trade_event_id()
    second = issue_trade_event_id()
    assert first != second


def test_invalid_values_rejected():
    assert validate_trade_event_id(None) is False
    assert validate_trade_event_id("") is False
    assert validate_trade_event_id("EXCHANGE-123") is False
    assert validate_trade_event_id("TE-not-hex") is False


def main():
    tests = (
        test_issuer_produces_valid_identity,
        test_each_attempt_gets_distinct_identity,
        test_invalid_values_rejected,
    )
    for test in tests:
        test()
    print("MCP01_TRADE_EVENT_IDENTITY_TESTS=3/3 PASS")


if __name__ == "__main__":
    main()
