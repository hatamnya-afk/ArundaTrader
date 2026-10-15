"""Offline tests for explicit runtime dependency wiring and DB isolation."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from execution_dependency_runtime_factory_v0_1 import load_execution_dependencies


class ExecutionDependencyFactoryTests(unittest.TestCase):
    def test_factory_requires_both_explicit_opt_in_switches(self):
        env = {
            "ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "",
            "ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION": "",
        }
        with patch.dict(os.environ, env, clear=False), tempfile.TemporaryDirectory() as root:
            os.environ.pop("ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT", None)
            os.environ.pop("ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION", None)
            with self.assertRaisesRegex(ValueError, "NOT_EXPLICITLY_ENABLED"):
                load_execution_dependencies(production_database_path=Path(root) / "arunda.db")

    def test_factory_rejects_claim_store_path_equal_to_production_db(self):
        with tempfile.TemporaryDirectory() as root:
            production = Path(root) / "arunda.db"
            production.touch()
            env = {
                "ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1",
                "ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION": "1",
                "ARUNDA_EXECUTION_CLAIM_DB": str(production),
                "TOOBIT_API_KEY": "fixture-key",
                "TOOBIT_API_SECRET": "fixture-secret",
            }
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaisesRegex(ValueError, "MUST_NOT_USE_PRODUCTION_DATABASE"):
                    load_execution_dependencies(production_database_path=production)

    def test_factory_injects_adapter_and_separate_durable_claim_store(self):
        with tempfile.TemporaryDirectory() as root:
            production = Path(root) / "arunda.db"
            production.touch()
            claim_path = Path(root) / "execution" / "claims.sqlite3"
            claim_path.parent.mkdir()
            env = {
                "ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1",
                "ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION": "1",
                "ARUNDA_EXECUTION_CLAIM_DB": str(claim_path),
                "TOOBIT_API_KEY": "fixture-key",
                "TOOBIT_API_SECRET": "fixture-secret",
            }
            with patch.dict(os.environ, env, clear=False):
                adapter, store = load_execution_dependencies(production_database_path=production)
            self.assertEqual(adapter.adapter_name, "TOOBIT")
            self.assertTrue(adapter.capabilities().order_submission)
            self.assertEqual(Path(store.path).resolve(), claim_path.resolve())
            self.assertNotEqual(Path(store.path).resolve(), production.resolve())
            self.assertTrue(claim_path.exists())


if __name__ == "__main__":
    unittest.main()
