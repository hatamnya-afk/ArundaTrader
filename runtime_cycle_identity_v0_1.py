"""Authoritative runtime-cycle identity boundary.

A cycle identity belongs to one Trader subprocess run. It is distinct from
CP49 decision identity, CP69 runtime snapshot identity, MCP case identity,
and trade-event identity.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


SCHEMA_VERSION = "ARUNDA-RUNTIME-CYCLE-IDENTITY-v0.1"
CYCLE_PREFIX = "RC-"


def build_runtime_cycle_id(
    *,
    started_at: str,
    process_id: int | None = None,
) -> str:
    if not isinstance(started_at, str) or not started_at.strip():
        raise ValueError("RUNTIME_CYCLE_STARTED_AT_INVALID")

    if process_id is None:
        process_id = os.getpid()

    if (
        isinstance(process_id, bool)
        or not isinstance(process_id, int)
        or process_id <= 0
    ):
        raise ValueError("RUNTIME_CYCLE_PROCESS_ID_INVALID")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "started_at": started_at.strip(),
        "process_id": process_id,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return CYCLE_PREFIX + hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def utc_cycle_start() -> str:
    return datetime.now(timezone.utc).isoformat()
