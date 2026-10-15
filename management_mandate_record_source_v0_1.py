"""Load and validate the authoritative one-time management mandate.

The source record is deployment-provided and never committed to source control.
No approval, identifier, issuance time, expiry, provider, or scope is synthesized.
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

    validated = evaluate_management_phase_entry(record)
    # A validly formed DENIED/DEFERRED record is not permission to proceed.
    # Keep the original management record for downstream contract evaluation.
    if validated.get("management_state") != "AUTHORIZED":
        raise ValueError("AUTHORITATIVE_MANAGEMENT_MANDATE_NOT_AUTHORIZED")
    if not isinstance(validated.get("authorization_observation"), Mapping):
        raise ValueError("AUTHORITATIVE_MANAGEMENT_AUTHORIZATION_OBSERVATION_MISSING")
    return dict(record)


__all__ = ["load_authoritative_management_mandate"]
