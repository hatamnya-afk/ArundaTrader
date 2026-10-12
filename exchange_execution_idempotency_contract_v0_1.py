"""Stable provider client-order ID derivation and acceptance policy.

Pure functions only: no I/O, provider calls, or execution. A generated ID is
usable at an execution boundary only when the adapter supplies a verified
provider policy. Unknown provider constraints must fail closed.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

_DEFAULT_PREFIX = "AR"
_MIN_DIGEST_HEX_LENGTH = 16
_MAX_CLIENT_ORDER_ID_LENGTH = 128
_SAFE_PREFIX = re.compile(r"^[A-Z0-9]+$")


def validate_client_order_id_policy(policy: Any) -> tuple[bool, str]:
    """Validate an explicit provider policy; never infer undocumented limits."""
    if not isinstance(policy, Mapping):
        return False, "CLIENT_ORDER_ID_POLICY_MISSING"
    if policy.get("verified") is not True:
        return False, "CLIENT_ORDER_ID_PROVIDER_POLICY_UNVERIFIED"
    namespace = policy.get("provider_namespace")
    prefix = policy.get("prefix")
    max_length = policy.get("max_length")
    pattern = policy.get("allowed_pattern")
    reference = policy.get("policy_reference")
    if not isinstance(namespace, str) or not namespace.strip():
        return False, "PROVIDER_NAMESPACE_REQUIRED"
    if not isinstance(prefix, str) or not _SAFE_PREFIX.fullmatch(prefix.strip().upper()):
        return False, "CLIENT_ORDER_ID_PREFIX_INVALID"
    if (not isinstance(max_length, int) or isinstance(max_length, bool)
            or max_length > _MAX_CLIENT_ORDER_ID_LENGTH
            or max_length < len(prefix.strip()) + _MIN_DIGEST_HEX_LENGTH):
        return False, "CLIENT_ORDER_ID_LENGTH_CONSTRAINT_INVALID"
    if not isinstance(pattern, str) or not pattern:
        return False, "CLIENT_ORDER_ID_PATTERN_REQUIRED"
    try:
        re.compile(pattern)
    except re.error:
        return False, "CLIENT_ORDER_ID_PATTERN_INVALID"
    if not isinstance(reference, str) or not reference.strip():
        return False, "CLIENT_ORDER_ID_POLICY_REFERENCE_REQUIRED"
    return True, "VALID"


def derive_client_order_id(*, provider_namespace: str, intent_id: str, prefix: str = _DEFAULT_PREFIX, max_length: int) -> str:
    """Derive a deterministic candidate from provider namespace + canonical intent."""
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


def derive_validated_client_order_id(*, policy: Mapping[str, Any], intent_id: str) -> str:
    """Derive and validate a candidate only under an explicitly verified policy."""
    valid, reason = validate_client_order_id_policy(policy)
    if not valid:
        raise ValueError(reason)
    candidate = derive_client_order_id(
        provider_namespace=policy["provider_namespace"],
        intent_id=intent_id,
        prefix=policy["prefix"],
        max_length=policy["max_length"],
    )
    if re.fullmatch(policy["allowed_pattern"], candidate) is None:
        raise ValueError("CLIENT_ORDER_ID_CHARSET_INVALID")
    return candidate


def validate_supplied_client_order_id(*, policy: Mapping[str, Any], intent_id: str, client_order_id: str) -> str:
    """Reject any supplied ID not exactly derived from this canonical intent."""
    expected = derive_validated_client_order_id(policy=policy, intent_id=intent_id)
    if not isinstance(client_order_id, str) or client_order_id != client_order_id.strip():
        raise ValueError("CLIENT_ORDER_ID_FORMAT_INVALID")
    if client_order_id != expected:
        raise ValueError("CLIENT_ORDER_ID_NOT_CANONICAL")
    return expected


__all__ = [
    "derive_client_order_id",
    "derive_validated_client_order_id",
    "validate_client_order_id_policy",
    "validate_supplied_client_order_id",
]
