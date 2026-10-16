"""Positive and negative tests for the live Ed25519 mandate-status gate."""
import base64
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from management_mandate_revocation_runtime_v0_1 import evaluate_signed_mandate_status


SOURCE_ID = "unit-management-authority"
MANDATE_ID = "REAL-PROD-MANDATE-001"


def _fixture(*, status="ACTIVE", mandate_id=MANDATE_ID, age_seconds=0, future_seconds=0, invalid_signature=False):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    now = datetime.now(timezone.utc)
    observed_at = now - timedelta(seconds=age_seconds) + timedelta(seconds=future_seconds)
    payload = {
        "schema_version": "1", "mandate_id": mandate_id, "status": status,
        "observed_at": observed_at.isoformat(), "source_id": SOURCE_ID,
    }
    signature = private_key.sign(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    if invalid_signature:
        signature = bytes([0]) * 64
    payload["signature"] = base64.b64encode(signature).decode("ascii")
    return payload, base64.b64encode(public_key).decode("ascii"), now


class MandateRevocationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.observation, self.public_key, self.now = _fixture()
        self.mandate = {"mandate_id": MANDATE_ID, "authorization_id": MANDATE_ID}

    def _evaluate(self, observation=None, public_key=None, mandate=None, now=None):
        return evaluate_signed_mandate_status(
            mandate=mandate or self.mandate,
            provider=lambda: self.observation if observation is None else observation,
            trusted_public_key_b64=public_key or self.public_key,
            expected_source_id=SOURCE_ID,
            now=now or self.now,
        )

    def test_valid_fresh_active_status_passes(self):
        result = self._evaluate()
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["signature_validation"], "VALID")
        self.assertEqual(result["freshness_validation"], "FRESH")

    def test_revoked_status_blocks(self):
        observation, _, _ = _fixture(status="REVOKED")
        with self.assertRaisesRegex(ValueError, "MANDATE_REVOKED"):
            self._evaluate(observation=observation)

    def test_invalid_signature_blocks(self):
        observation, _, _ = _fixture(invalid_signature=True)
        with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_SIGNATURE_INVALID"):
            self._evaluate(observation=observation)

    def test_stale_status_blocks(self):
        observation, _, _ = _fixture(age_seconds=31)
        with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_STALE"):
            self._evaluate(observation=observation)

    def test_missing_source_blocks(self):
        with patch.dict(os.environ, {"ARUNDA_MANDATE_STATUS_URL": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_SOURCE_MISSING"):
                evaluate_signed_mandate_status(
                    mandate=self.mandate, provider=None,
                    trusted_public_key_b64=self.public_key,
                    expected_source_id=SOURCE_ID, now=self.now,
                )

    def test_mismatched_mandate_id_blocks(self):
        observation, _, _ = _fixture(mandate_id="DIFFERENT-MANDATE")
        with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_IDENTITY_MISMATCH"):
            self._evaluate(observation=observation)

    def test_future_timestamp_blocks(self):
        observation, _, _ = _fixture(future_seconds=6)
        with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_TIMESTAMP_IN_FUTURE"):
            self._evaluate(observation=observation)

    def test_missing_trusted_public_key_blocks(self):
        with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_TRUSTED_PUBLIC_KEY_MISSING"):
            self._evaluate(public_key="")

    def test_unexpected_source_id_blocks(self):
        observation = dict(self.observation)
        observation["source_id"] = "other-authority"
        with self.assertRaisesRegex(ValueError, "MANDATE_STATUS_SOURCE_ID_MISMATCH"):
            self._evaluate(observation=observation)


if __name__ == "__main__":
    unittest.main()
