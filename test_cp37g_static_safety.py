from pathlib import Path


SOURCE = Path(__file__).with_name("portfolio_observation_v0_1.py").read_text(
    encoding="utf-8"
)


def test_provider_neutral_and_read_only_surface():
    upper = SOURCE.upper()
    forbidden = (
        "TOOBIT",
        "KUCOIN",
        "BITGET",
        "SQLITE3",
        "ORDER_INTENT",
        "POSITION_SIZING",
        "RISK_BUDGET",
        "EXECUTE_ORDER",
        "SUBMIT_ORDER",
        "DATABASE_WRITE",
        "EXPECTED_ASSETS",
        "FIXED_15",
        "CAPITAL=1000000",
        "AVAILABLE_CAPITAL=1000000",
    )
    assert all(token not in upper for token in forbidden)


def test_no_network_or_database_imports():
    assert "import requests" not in SOURCE
    assert "import httpx" not in SOURCE
    assert "import sqlite3" not in SOURCE
    assert "connect(" not in SOURCE


def test_dynamic_position_boundary():
    assert "Sequence" in SOURCE
    assert "positions" in SOURCE
    assert "EXPECTED_ASSETS" not in SOURCE
