"""Stable provider client-order ID contract v0.1.

Pure deterministic identity derivation for offline contract tests and future
adapter integration. This module performs no I/O and is not wired to execution.

The ID is independent of trade_event_id (which identifies an individual
attempt), snapshot_id, timestamps, and provider responses. It is derived from
a provider namespace plus the canonical intent_id so retries/restarts for the
same intent produce the same candidate ID.

IMPORTANT:
- A concrete adapter must confirm the provider allowed charset and length.
- This derivation alone does NOT prove provider-side idempotency.
- It must be paired with durable/atomic per-intent attempt claiming and
  read-only provider reconciliation before any production use.
"""
from __future__ import annotations

import hashlib
import re

_DEFAULT_PREFIX = "AR"
_MIN_DIGEST_HEX_LENGTH = 16
_MAX_CLIENT_ORDER_ID_LENGTH = 128
_SAFE_PREFIX = re.compile(r"^[A-Z0-9]+$")


def derive_client_order_id(*, provider_namespace: str, intent_id: str, prefix: str = _DEFAULT_PREFIX, max_length: int) -> str:
    """Derive a stable candidate client-order ID from provider + intent.

    The caller must pass the canonical intent identity, not snapshot or attempt
    identity. The adapter owns provider-specific constraints and must choose
    prefix/max_length only after checking the provider contract.
    """
    namespace = provider_namespace.strip().upper() if isinstance(provider_namespace, str) else ""
    canonical_intent = intent_id.strip() if isinstance(intent_id, str) else ""
    normalized_prefix = prefix.strip().upper() if isinstance(prefix, str) else ""

    if not namespace:
        raise ValueError("PROVIDER_NAMESPACE_REQUIRED")
    if not canonical_intent:
        raise ValueError("CANONICAL_INTENT_ID_REQUIRED")
    if not normalized_prefix or not _SAFE_PREFIX.fullmatch(normalized_prefix):
        raise ValueError("CLIENT_ORDER_ID_PREFIX_INVALID")
    if (not isinstance(max_length, int) or isinstance(max_length, bool)
            or max_length > _MAX_CLIENT_ORDER_ID_LENGTH
            or max_length < len(normalized_prefix) + _MIN_DIGEST_HEX_LENGTH):
        raise ValueError("CLIENT_ORDER_ID_LENGTH_CONSTRAINT_INVALID")

    material = (f"ARUNDA_CLIENT_ORDER_ID_V1:{len(namespace)}:{namespace}:{len(canonical_intent)}:{canonical_intent}").encode("utf-8")
    digest = hashlib.sha256(material).hexdigest().upper()
    return normalized_prefix + digest[: max_length - len(normalized_prefix)]


__all__ = ["derive_client_order_id"]
