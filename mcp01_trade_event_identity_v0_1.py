"""MCP-01 authoritative trade-event identity issuer v0.1.

A trade_event_id is issued exactly at the execution-boundary order-attempt
point. It is never derived from exchange_order_id, intent_id, decision_id,
snapshot_id, or provider response fields.

No network, database, exchange write, or order submission occurs here.
"""

from __future__ import annotations

from uuid import uuid4


PREFIX = "TE-"


def issue_trade_event_id() -> str:
    """Issue one authoritative identity for one execution-boundary attempt."""
    return f"{PREFIX}{uuid4().hex}"


def validate_trade_event_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if not value.startswith(PREFIX):
        return False
    suffix = value[len(PREFIX):]
    if len(suffix) != 32:
        return False
    try:
        int(suffix, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "PREFIX",
    "issue_trade_event_id",
    "validate_trade_event_id",
]
