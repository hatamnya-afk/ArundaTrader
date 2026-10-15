"""Load the authoritative one-time management mandate from deployment configuration.

The record is intentionally external to source control. No default approval,
issue time, expiry, provider, or market scope is manufactured.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from management_execution_authorization_v0_1 import evaluate_management_phase_entry


def load_authoritative_management_mandate(
    *, env_var: str = "ARUNDA_MANAGEMENT_MANDATE_JSON"
) -> dict[str, Any]:
    raw = os.environ.get(env_var)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("AUTHORITATIVE_MANAGEMENT_MANDATE_SOURCE_MISSING")
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("AUTHORITATIVE_MANAGEMENT_MANDATE_JSON_INVALID") from exc
    if not isinstance(record, Mapping):
        raise ValueError("AUTHORITATIVE_MANAGEMENT_MANDATE_RECORD_INVALID")
    # Validate source record here, including explicit timezone-aware issued_at
    # and expires_at. Return the original values, not a synthesized replacement.
    evaluate_management_phase_entry(record)
    return dict(record)


__all__ = ["load_authoritative_management_mandate"]
