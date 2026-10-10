from __future__ import annotations

import ast
import unittest
from pathlib import Path


class CanonicalOrderRequestBuilderContractTests(unittest.TestCase):
    """Static tests avoid importing the full production pipeline or running it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = Path(__file__).with_name("arunda_pipeline.py").read_text(
            encoding="utf-8-sig"
        )
        cls.tree = ast.parse(cls.source)
        cls.function = next(
            node for node in ast.walk(cls.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "build_canonical_order_requests"
        )

    def test_builder_requires_authoritative_identity_and_reference_price_inputs(self) -> None:
        arg_names = [arg.arg for arg in self.function.args.args]
        self.assertIn("decision_snapshot", arg_names)
        self.assertIn("reference_prices", arg_names)

    def test_quantity_is_authoritative_in_risk_not_order_intent(self) -> None:
        source = ast.get_source_segment(self.source, self.function) or ""
        self.assertIn('quantity = risk_row.get("position_quantity")', source)
        self.assertIn('if quantity is None:', source)
        self.assertNotIn('intent.get("quantity")', source)
        self.assertNotIn('getattr(intent, "quantity", None)', source)

    def test_contract_builder_receives_quantity_only_through_risk(self) -> None:
        calls = [
            node for node in ast.walk(self.function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "build_order_request"
        ]
        self.assertEqual(len(calls), 1)
        kwargs = {kw.arg: kw.value for kw in calls[0].keywords}
        self.assertIn("risk", kwargs)
        self.assertNotIn("quantity", kwargs)
        self.assertIn("reference_price", kwargs)
        self.assertIn("decision_id", kwargs)

    def test_authoritative_values_are_checked_before_request_construction(self) -> None:
        source = ast.get_source_segment(self.source, self.function) or ""
        self.assertIn('decision_row.get("decision_id")', source)
        self.assertIn("reference_price_is_valid", source)
        self.assertIn('contract_risk_row["quantity_source"] = CANONICAL_QUANTITY_SOURCE', source)
        self.assertIn("request.decision_id != decision_id", source)
        self.assertIn("request.reference_price != reference_price", source)

    def test_original_risk_row_is_not_mutated(self) -> None:
        source = ast.get_source_segment(self.source, self.function) or ""
        self.assertIn("contract_risk_row = dict(risk_row)", source)
        self.assertNotIn('\\n            risk_row["quantity_source"] = CANONICAL_QUANTITY_SOURCE', source)


if __name__ == "__main__":
    unittest.main()
