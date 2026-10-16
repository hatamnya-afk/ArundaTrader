"""Live signed management-mandate status gate (Ed25519, fail closed).

The management authority owns the private key. ArundaTrader receives only the
trusted public key and a fresh signed ACTIVE/REVOKED observation. The default
provider performs a bounded HTTPS GET to the configured authority endpoint.
No order, database, or exchange operation is performed by this module.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

ACTIVE = "ACTIVE"
REVOKED = "REVOKED"
SCHEMA_VERSION = "1"
MAX_STATUS_AGE_SECONDS = 30
MAX_FUTURE_SKEW_SECONDS = 5
MAX_RESPONSE_BYTES = 16_384
HTTP_TIMEOUT_SECONDS = 3
_REQUIRED_SIGNED_FIELDS = frozenset({
    "schema_version", "mandate_id", "status", "observed_at", "source_id",
    "signature",
})
_SIGNED_FIELDS = ("schema_version", "mandate_id", "status", "observed_at", "source_id")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_signed_mandate_status_from_authority() -> Mapping[str, Any]:
    """Fetch one signed status from the configured HTTPS management authority.

    Required environment:
      ARUNDA_MANDATE_STATUS_URL=https://<management-authority>/...
      ARUNDA_MANDATE_STATUS_SOURCE_ID=<expected signed source_id>
      ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64=<trusted 32-byte Ed25519 public key>
    """
    raw_url = os.environ.get("ARUNDA_MANDATE_STATUS_URL", "").strip()
    if not raw_url:
        raise ValueError("MANDATE_STATUS_SOURCE_MISSING")
    parsed = urllib.parse.urlsplit(raw_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("MANDATE_STATUS_SOURCE_URL_INVALID")
    request = urllib.request.Request(
        raw_url,
        headers={"Accept": "application/json", "User-Agent": "ArundaTrader-MandateGate/1"},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if response.geturl() != raw_url:
                raise ValueError("MANDATE_STATUS_SOURCE_REDIRECT_FORBIDDEN")
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
                raise ValueError("MANDATE_STATUS_RESPONSE_TOO_LARGE")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError("MANDATE_STATUS_SOURCE_UNAVAILABLE") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("MANDATE_STATUS_RESPONSE_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("MANDATE_STATUS_RESPONSE_INVALID") from exc
    if not isinstance(value, Mapping):
        raise ValueError("MANDATE_STATUS_RESPONSE_INVALID")
    return value


def _parse_aware(value: Any, reason: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(reason) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(reason)
    return parsed.astimezone(timezone.utc)


def _canonical_signed_bytes(observation: Mapping[str, Any]) -> bytes:
    payload = {key: observation[key] for key in _SIGNED_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def evaluate_signed_mandate_status(
    *,
    mandate: Mapping[str, Any],
    provider: Callable[[], Mapping[str, Any]] | None = None,
    trusted_public_key_b64: str | None = None,
    expected_source_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Require a fresh, correctly signed, identity-matched ACTIVE status."""
    if not isinstance(mandate, Mapping):
        raise ValueError("MANDATE_STATUS_MANDATE_INVALID")
    mandate_id = mandate.get("mandate_id") or mandate.get("authorization_id")
    if not isinstance(mandate_id, str) or not mandate_id.strip():
        raise ValueError("MANDATE_STATUS_MANDATE_ID_INVALID")
    mandate_id = mandate_id.strip()

    provider = provider or fetch_signed_mandate_status_from_authority
    if not callable(provider):
        raise ValueError("MANDATE_STATUS_SOURCE_MISSING")
    try:
        observation = provider()
    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("MANDATE_STATUS_"):
            raise
        raise ValueError("MANDATE_STATUS_SOURCE_UNAVAILABLE") from exc
    if not isinstance(observation, Mapping):
        raise ValueError("MANDATE_STATUS_OBSERVATION_MISSING")
    if frozenset(observation.keys()) != _REQUIRED_SIGNED_FIELDS:
        raise ValueError("MANDATE_STATUS_SCHEMA_INVALID")

    key_text = trusted_public_key_b64
    if key_text is None:
        key_text = os.environ.get("ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64", "")
    if not isinstance(key_text, str) or not key_text.strip():
        raise ValueError("MANDATE_STATUS_TRUSTED_PUBLIC_KEY_MISSING")
    try:
        public_key_bytes = base64.b64decode(key_text.strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("MANDATE_STATUS_TRUSTED_PUBLIC_KEY_INVALID") from exc
    if len(public_key_bytes) != 32:
        raise ValueError("MANDATE_STATUS_TRUSTED_PUBLIC_KEY_INVALID")

    source_id_expected = expected_source_id
    if source_id_expected is None:
        source_id_expected = os.environ.get("ARUNDA_MANDATE_STATUS_SOURCE_ID", "")
    if not isinstance(source_id_expected, str) or not source_id_expected.strip():
        raise ValueError("MANDATE_STATUS_EXPECTED_SOURCE_MISSING")
    source_id_expected = source_id_expected.strip()

    if observation.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("MANDATE_STATUS_SCHEMA_INVALID")
    observed_mandate_id = observation.get("mandate_id")
    if not isinstance(observed_mandate_id, str) or observed_mandate_id != mandate_id:
        raise ValueError("MANDATE_STATUS_IDENTITY_MISMATCH")
    source_id = observation.get("source_id")
    if not isinstance(source_id, str) or source_id != source_id_expected:
        raise ValueError("MANDATE_STATUS_SOURCE_ID_MISMATCH")
    status = observation.get("status")
    if status not in (ACTIVE, REVOKED):
        raise ValueError("MANDATE_STATUS_VALUE_INVALID")

    observed_at = _parse_aware(observation.get("observed_at"), "MANDATE_STATUS_TIMESTAMP_INVALID")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("MANDATE_STATUS_CLOCK_INVALID")
    age = (current.astimezone(timezone.utc) - observed_at).total_seconds()
    if age < -MAX_FUTURE_SKEW_SECONDS:
        raise ValueError("MANDATE_STATUS_TIMESTAMP_IN_FUTURE")
    if age > MAX_STATUS_AGE_SECONDS:
        raise ValueError("MANDATE_STATUS_STALE")

    signature_text = observation.get("signature")
    if not isinstance(signature_text, str) or not signature_text.strip():
        raise ValueError("MANDATE_STATUS_SIGNATURE_MISSING")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("MANDATE_STATUS_SIGNATURE_INVALID") from exc
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, _canonical_signed_bytes(observation))
    except ImportError as exc:
        raise ValueError("MANDATE_STATUS_ED25519_UNAVAILABLE") from exc
    except ValueError as exc:
        raise ValueError("MANDATE_STATUS_TRUSTED_PUBLIC_KEY_INVALID") from exc
    except InvalidSignature as exc:
        raise ValueError("MANDATE_STATUS_SIGNATURE_INVALID") from exc

    if status == REVOKED:
        raise ValueError("MANDATE_REVOKED")
    return {
        "mandate_id": mandate_id, "status": ACTIVE, "source_id": source_id,
        "observed_at": observed_at.isoformat(), "signature_validation": "VALID",
        "freshness_validation": "FRESH",
    }


__all__ = [
    "ACTIVE", "REVOKED", "MAX_STATUS_AGE_SECONDS",
    "fetch_signed_mandate_status_from_authority", "evaluate_signed_mandate_status",
]
