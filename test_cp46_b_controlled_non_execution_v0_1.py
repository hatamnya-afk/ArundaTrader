from __future__ import annotations

import importlib

import cp46_b_controlled_non_execution_v0_1 as cp46b


class ForbiddenSession:
    def get(self, *args, **kwargs):
        raise AssertionError(
            "CP46-B violation: HTTP GET was attempted."
        )

    def post(self, *args, **kwargs):
        raise AssertionError(
            "CP46-B violation: HTTP POST was attempted."
        )

    def put(self, *args, **kwargs):
        raise AssertionError(
            "CP46-B violation: HTTP PUT was attempted."
        )

    def delete(self, *args, **kwargs):
        raise AssertionError(
            "CP46-B violation: HTTP DELETE was attempted."
        )


def test_cp46_b_all_checks_pass():
    results = cp46b.run_cp46_b()

    assert results
    assert all(item.passed for item in results)


def test_cp46_b_runtime_flags_remain_disabled():
    adapter_module = importlib.import_module(
        "toobit_trading_adapter"
    )

    assert adapter_module.EXECUTION_ENABLED is False
    assert adapter_module.ORDER_SUBMISSION_ENABLED is False
    assert adapter_module.EXCHANGE_WRITE_ENABLED is False
    assert adapter_module.DATABASE_WRITE_ENABLED is False


def test_cp46_b_adapter_capabilities_do_not_enable_submission():
    adapter_module = importlib.import_module(
        "toobit_trading_adapter"
    )

    adapter = adapter_module.ToobitTradingAdapter()

    capabilities = adapter.capabilities()

    assert capabilities.get("ORDER_SUBMISSION") is not True
    assert capabilities["ACCOUNT_READ"] is True
    assert capabilities["BALANCE_READ"] is True


def test_cp46_b_submit_order_fails_closed_without_http():
    adapter_module = importlib.import_module(
        "toobit_trading_adapter"
    )

    adapter = adapter_module.ToobitTradingAdapter(
        api_key="CP46_B_TEST_KEY",
        api_secret="CP46_B_TEST_SECRET",
    )

    adapter.session = ForbiddenSession()

    request = cp46b.build_canonical_request()
    original_quantity = request.quantity

    result = adapter.submit_order(request)

    assert result.accepted is False
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "CP46_E_REQUIRED"

    assert result.exchange_order_id is None
    assert result.executed_quantity is None
    assert result.executed_price is None

    assert request.quantity == original_quantity


def test_cp46_b_execution_boundary_fails_closed_without_http():
    adapter_module = importlib.import_module(
        "toobit_trading_adapter"
    )

    adapter = adapter_module.ToobitTradingAdapter(
        api_key="CP46_B_TEST_KEY",
        api_secret="CP46_B_TEST_SECRET",
    )

    adapter.session = ForbiddenSession()

    request = cp46b.build_canonical_request()
    original_quantity = request.quantity

    result = cp46b.execute_order(
        request,
        adapter,
    )

    assert result.accepted is False
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "EXECUTION_DISABLED"

    assert result.exchange_order_id is None
    assert result.executed_quantity is None
    assert result.executed_price is None

    assert request.quantity == original_quantity


def test_cp46_b_preflight_blocks_unresolved_translation():
    request = cp46b.build_translation_block_request()
    evidence = cp46b.build_pass_evidence()

    result = cp46b.run_provider_preflight(
        request,
        evidence,
    )

    assert result.status.value == "BLOCK"
    assert (
        result.reason.value
        == "BLOCK_QUANTITY_TRANSLATION_REQUIRED"
    )