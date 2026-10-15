"""Focused tests for the fail-closed final-attempt pipeline wiring."""

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


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
                     trade_event_id=None, error_code="ADAPTER_CONTRACT_INVALID"):
            self.accepted = accepted
            self.exchange_order_id = exchange_order_id
            self.trade_event_id = trade_event_id
            self.error_code = error_code

    calls = []
    namespace = {
        "EXPECTED_ASSET_SET": {"BTC"},
        "assert_execution_disabled": lambda: None,
        "fail": lambda message: (_ for _ in ()).throw(RuntimeError(message)),
        "exchange_execution_contract": SimpleNamespace(
            CanonicalOrderRequest=Request,
            CanonicalExecutionResult=Result,
        ),
        "run_final_execution_attempt_contract": lambda **kwargs: (
            calls.append(kwargs) or Result()
        ),
    }
    exec(compile(module, str(PIPELINE_PATH), "exec"), namespace)
    return namespace["verify_execution_boundary_integration"], calls, Request, Result


class FinalAttemptPipelineWiringTests(unittest.TestCase):
    def test_empty_runtime_path_defers_without_fabricating_request(self):
        verify, calls, _, _ = _load_verifier()
        self.assertEqual(verify({}), "DEFERRED_NO_CANONICAL_REQUESTS")
        self.assertEqual(calls, [])

    def test_missing_real_context_fails_closed_without_calling_contract(self):
        verify, calls, Request, _ = _load_verifier()
        status = verify({"BTC": {"request": Request()}})
        self.assertEqual(status, "BLOCKED_FINAL_ATTEMPT_CONTEXT_MISSING")
        self.assertEqual(calls, [])

    def test_complete_context_composes_contract_with_no_adapter(self):
        verify, calls, Request, _ = _load_verifier()
        record = {
            "request": Request(),
            "execution_ready_package": {"source": "test fixture only"},
            "authorization_observation": {"source": "test fixture only"},
            "venue": "SPOT",
            "execution_instrument": "BTC-USDT",
        }
        self.assertEqual(
            verify({"BTC": record}),
            "VERIFIED_BLOCKED_FINAL_ATTEMPT",
        )
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0]["adapter"])
        self.assertIs(calls[0]["request"], record["request"])

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


if __name__ == "__main__":
    unittest.main()
