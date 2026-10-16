"""Focused tests for the fail-closed final-attempt pipeline wiring."""

import ast
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PIPELINE_PATH = Path(__file__).with_name("arunda_pipeline.py")


def _load_verifier():
    source = PIPELINE_PATH.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "verify_execution_boundary_integration"
    )
    module = ast.Module(body=[function], type_ignores=[])

    class Request:
        asset = "BTC"
        direction = "LONG"

    class Result:
        def __init__(self, *, accepted=False, exchange_order_id=None,
                     trade_event_id=None, error_code="ADAPTER_CONTRACT_INVALID",
                     status="BLOCKED"):
            self.accepted = accepted
            self.exchange_order_id = exchange_order_id
            self.trade_event_id = trade_event_id
            self.error_code = error_code
            self.status = status

    calls = []
    queued_results = []
    namespace = {
        "EXPECTED_ASSET_SET": {"BTC"},
        "assert_execution_disabled": lambda: None,
        "fail": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
        "exchange_execution_contract": SimpleNamespace(
            CanonicalOrderRequest=Request,
            CanonicalExecutionResult=Result,
        ),
        "run_final_execution_attempt_contract": lambda **kwargs: (
            calls.append(kwargs) or (queued_results.pop(0) if queued_results else Result())
        ),
    }
    exec(compile(module, str(PIPELINE_PATH), "exec"), namespace)
    return namespace["verify_execution_boundary_integration"], calls, Request, Result, queued_results


class FinalAttemptPipelineWiringTests(unittest.TestCase):
    def _record(self, Request):
        return {
            "request": Request(),
            "execution_ready_package": {"source": "test fixture only"},
            "authorization_observation": {"source": "test fixture only"},
            "venue": "SPOT",
            "execution_instrument": "BTC-USDT",
        }

    def test_empty_runtime_path_defers_without_fabricating_request(self):
        verify, calls, _, _, _ = _load_verifier()
        self.assertEqual(verify({}), "DEFERRED_NO_CANONICAL_REQUESTS")
        self.assertEqual(calls, [])

    def test_missing_real_context_fails_closed_without_calling_contract(self):
        verify, calls, Request, _, _ = _load_verifier()
        status = verify({"BTC": {"request": Request()}})
        self.assertEqual(status, "BLOCKED_FINAL_ATTEMPT_CONTEXT_MISSING")
        self.assertEqual(calls, [])

    def test_default_off_path_never_passes_injected_adapter_to_contract(self):
        verify, calls, Request, _, _ = _load_verifier()
        adapter = object()
        claim_store = object()
        with patch.dict(os.environ, {}, clear=True):
            status = verify(
                {"BTC": self._record(Request)},
                adapter=adapter,
                claim_store=claim_store,
            )
        self.assertEqual(status, "VERIFIED_BLOCKED_FINAL_ATTEMPT")
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0]["adapter"])
        self.assertIsNone(calls[0]["claim_store"])

    def test_single_opt_in_switch_is_blocked_before_contract(self):
        verify, calls, Request, _, _ = _load_verifier()
        with patch.dict(os.environ, {"ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1"}, clear=True):
            status = verify({"BTC": self._record(Request)}, adapter=object(), claim_store=object())
        self.assertEqual(status, "BLOCKED_EXECUTION_OPT_IN_SWITCHES_INCOMPLETE")
        self.assertEqual(calls, [])

    def test_explicit_dual_opt_in_routes_result_and_dependencies_to_final_contract(self):
        verify, calls, Request, Result, queued_results = _load_verifier()
        adapter = object()
        claim_store = object()
        queued_results.append(Result(
            accepted=True,
            exchange_order_id="fixture-order-1",
            trade_event_id="fixture-event-1",
            error_code=None,
            status="PROVIDER_ACCEPTED",
        ))
        env = {
            "ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1",
            "ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION": "1",
        }
        with patch.dict(os.environ, env, clear=True):
            status = verify({"BTC": self._record(Request)}, adapter=adapter, claim_store=claim_store)
        self.assertEqual(status, "EXECUTION_ATTEMPT_RESULTS:BTC:PROVIDER_ACCEPTED:NONE")
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["adapter"], adapter)
        self.assertIs(calls[0]["claim_store"], claim_store)

    def test_dual_opt_in_without_dependencies_is_blocked_before_contract(self):
        verify, calls, Request, _, _ = _load_verifier()
        env = {
            "ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1",
            "ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION": "1",
        }
        with patch.dict(os.environ, env, clear=True):
            status = verify({"BTC": self._record(Request)})
        self.assertEqual(status, "BLOCKED_EXECUTION_DEPENDENCIES_MISSING")
        self.assertEqual(calls, [])

    def test_main_invokes_verifier_and_verifier_calls_final_contract(self):
        tree = ast.parse(PIPELINE_PATH.read_text(encoding="utf-8-sig"))
        main = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        main_calls = [
            node.func.id for node in ast.walk(main)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertIn("verify_execution_boundary_integration", main_calls)

        verifier = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "verify_execution_boundary_integration"
        )
        verifier_calls = [
            node.func.id for node in ast.walk(verifier)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertIn("run_final_execution_attempt_contract", verifier_calls)
        self.assertNotIn("execute_order", verifier_calls)


    def test_main_constructs_dependencies_only_after_both_opt_in_switches(self):
        tree = ast.parse(PIPELINE_PATH.read_text(encoding="utf-8-sig"))
        main = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        guarded_factory_calls = []
        for node in ast.walk(main):
            if not isinstance(node, ast.If):
                continue
            calls_factory = any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "load_execution_dependencies"
                for child in node.body
                for call in ast.walk(child)
            )
            if calls_factory:
                guarded_factory_calls.append(ast.unparse(node.test))
        self.assertEqual(len(guarded_factory_calls), 1)
        guard = guarded_factory_calls[0]
        self.assertIn('ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT', guard)
        self.assertIn('ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION', guard)
        self.assertIn('and', guard)
        self.assertNotIn(' or ', guard)


if __name__ == "__main__":
    unittest.main()
