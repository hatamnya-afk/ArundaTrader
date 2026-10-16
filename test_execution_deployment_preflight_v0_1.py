"""Offline tests for the read-only execution deployment preflight."""
import base64
import tempfile
import unittest
from pathlib import Path

from execution_deployment_preflight_v0_1 import inspect_execution_deployment_config


class ExecutionDeploymentPreflightTests(unittest.TestCase):
    def _valid_env(self, claim_path: Path) -> dict[str, str]:
        return {
            "ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1",
            "ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION": "1",
            "ARUNDA_MANDATE_STATUS_URL": "https://management.example.invalid/status",
            "ARUNDA_MANDATE_STATUS_SOURCE_ID": "fixture-source",
            "ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64": base64.b64encode(b"x" * 32).decode(),
            "ARUNDA_EXECUTION_CLAIM_DB": str(claim_path),
            "TOOBIT_API_KEY": "fixture-key",
            "TOOBIT_API_SECRET": "fixture-secret",
        }

    def test_reports_static_shape_only_never_authorizes_or_writes(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            claim_dir = root_path / "claims"
            claim_dir.mkdir()
            result = inspect_execution_deployment_config(
                production_database_path=root_path / "arunda.db",
                environ=self._valid_env(claim_dir / "claims.sqlite3"),
            )
        self.assertEqual(result["status"], "STATIC_CONFIGURATION_SHAPE_PASS")
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["provider_contacted"])
        self.assertFalse(result["database_written"])
        self.assertFalse(result["order_attempted"])
        self.assertNotIn("fixture-secret", repr(result))
        self.assertNotIn("fixture-key", repr(result))

    def test_rejects_incomplete_switches_and_missing_signed_authority_fields(self):
        with tempfile.TemporaryDirectory() as root:
            env = {"ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT": "1"}
            result = inspect_execution_deployment_config(
                production_database_path=Path(root) / "arunda.db",
                environ=env,
            )
        self.assertEqual(result["status"], "CONFIGURATION_ISSUES_FOUND")
        self.assertIn("EXECUTION_OPT_IN_SWITCHES_INCOMPLETE", result["issues"])
        self.assertIn("MANDATE_STATUS_URL_INVALID_OR_MISSING", result["issues"])
        self.assertIn("MANDATE_STATUS_PUBLIC_KEY_INVALID_OR_MISSING", result["issues"])

    def test_rejects_claim_path_equal_to_production_database(self):
        with tempfile.TemporaryDirectory() as root:
            production = Path(root) / "arunda.db"
            production.touch()
            env = self._valid_env(production)
            result = inspect_execution_deployment_config(
                production_database_path=production,
                environ=env,
            )
        self.assertIn("CLAIM_STORE_MUST_NOT_USE_PRODUCTION_DATABASE", result["issues"])
        self.assertEqual(result["checks"]["claim_store_path"], "PRODUCTION_DB_COLLISION")


if __name__ == "__main__":
    unittest.main()
