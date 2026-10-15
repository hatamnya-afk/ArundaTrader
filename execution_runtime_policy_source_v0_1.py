"""Explicit deployment-owned execution policy source; fail closed when absent."""
from __future__ import annotations
import json
import os
from collections.abc import Mapping
from typing import Any

def load_authoritative_execution_runtime_policy(*, env_var: str = "ARUNDA_EXECUTION_POLICY_JSON") -> dict[str, Any]:
    raw = os.environ.get(env_var)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("AUTHORITATIVE_EXECUTION_POLICY_SOURCE_MISSING")
    try:
        policy = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("AUTHORITATIVE_EXECUTION_POLICY_JSON_INVALID") from exc
    if not isinstance(policy, Mapping):
        raise ValueError("AUTHORITATIVE_EXECUTION_POLICY_RECORD_INVALID")
    for key in ("policy_id", "policy_version", "venue"):
        if not isinstance(policy.get(key), str) or not policy[key].strip():
            raise ValueError("AUTHORITATIVE_EXECUTION_POLICY_ID_VERSION_VENUE_REQUIRED")
    result = dict(policy)
    result["venue"] = policy["venue"].strip().upper()
    if result["venue"] not in {"SPOT", "FUTURES"}:
        raise ValueError("AUTHORITATIVE_EXECUTION_POLICY_VENUE_INVALID")
    if result["venue"] == "FUTURES":
        settlement = policy.get("settlement_asset")
        kind = policy.get("instrument_type")
        if not isinstance(settlement, str) or settlement.strip().upper() not in {"USDT", "USDC"}:
            raise ValueError("AUTHORITATIVE_FUTURES_SETTLEMENT_ASSET_INVALID")
        if not isinstance(kind, str) or kind.strip().upper() not in {"PERPETUAL", "DELIVERY"}:
            raise ValueError("AUTHORITATIVE_FUTURES_INSTRUMENT_TYPE_INVALID")
        if policy.get("futures_exposure_allowed") not in (True, False):
            raise ValueError("AUTHORITATIVE_FUTURES_EXPOSURE_PERMISSION_REQUIRED")
        result["settlement_asset"] = settlement.strip().upper()
        result["instrument_type"] = kind.strip().upper()
    return result
