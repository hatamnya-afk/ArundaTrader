from cp46_h_controlled_read_only_connectivity_v0_1 import (
    ReadOnlyConnectivityStatus,
    verify_read_only_connectivity_contract,
)
from toobit_trading_adapter import ToobitTradingAdapter


def test_read_only_contract_passes_without_io():
    adapter = ToobitTradingAdapter(api_key="test-key", api_secret="test-secret")
    result = verify_read_only_connectivity_contract(adapter)
    assert result.status == ReadOnlyConnectivityStatus.PASS
    assert result.reason == "READ_ONLY_CONTRACT_READY"


def test_invalid_adapter_blocks():
    result = verify_read_only_connectivity_contract(object())
    assert result.status == ReadOnlyConnectivityStatus.BLOCK
    assert result.reason == "ADAPTER_INVALID"


def test_execution_enabled_blocks():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.execution_enabled = True
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "EXECUTION_STATE_INVALID"


def test_order_submission_enabled_blocks():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.order_submission_enabled = True
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "ORDER_SUBMISSION_STATE_INVALID"


def test_exchange_write_enabled_blocks():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.exchange_write_enabled = True
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "EXCHANGE_WRITE_STATE_INVALID"


def test_database_write_enabled_blocks():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.database_write_enabled = True
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "DATABASE_WRITE_STATE_INVALID"


def test_account_capability_required():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.capabilities = lambda: {"BALANCE_READ": True}
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "ACCOUNT_READ_CAPABILITY_MISSING"


def test_balance_capability_required():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.capabilities = lambda: {"ACCOUNT_READ": True}
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "BALANCE_READ_CAPABILITY_MISSING"


def test_missing_read_method_blocks():
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    adapter.get_server_time = None
    result = verify_read_only_connectivity_contract(adapter)
    assert result.reason == "READ_METHOD_MISSING"


def test_no_credentials_required_for_static_contract():
    adapter = ToobitTradingAdapter(api_key=None, api_secret=None)
    result = verify_read_only_connectivity_contract(adapter)
    assert result.status == ReadOnlyConnectivityStatus.PASS
