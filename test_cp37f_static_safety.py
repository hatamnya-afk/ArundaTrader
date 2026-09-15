from pathlib import Path


PRODUCER = Path(__file__).with_name("account_balance_observation_v0_1.py")
SOURCE = PRODUCER.read_text(encoding="utf-8")


def test_provider_neutral_source():
    upper = SOURCE.upper()
    for provider in ("TOOBIT", "KUCOIN", "BITGET"):
        assert provider not in upper


def test_forbidden_scope_absent():
    upper = SOURCE.upper()
    for token in (
        "EXPECTED_ASSETS",
        "RISK_PER_TRADE",
        "MAX_PORTFOLIO_RISK",
        "ORDER_INTENT",
        "EXECUTION",
        "POSITION_SIZING",
        "RISK_BUDGET",
        "TOTAL_EXPOSURE",
        "CONCENTRATION",
        "CORRELATION_EXPOSURE",
        "SQLITE3",
        "SQL WRITE",
    ):
        assert token not in upper
