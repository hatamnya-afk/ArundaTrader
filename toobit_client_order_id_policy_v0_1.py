"""Evidence ledger for Toobit Futures client-order IDs.

This is deliberately NOT an execution-approved ID policy. Official Toobit
sources establish the regular Futures lookup parameter and duplicate-ID error,
but the sources inspected do not publish a client-ID maximum length or allowed
character set, nor a durable idempotency guarantee across terminal orders.
Consequently the execution policy remains unverified and must fail closed.
"""
from __future__ import annotations

from typing import Any

TOOBIT_FUTURES_V2_DOCS = "https://api-docs.toobit.com/api/usdt-m-api-v2"
TOOBIT_ERROR_CODES_DOCS = "https://api-docs.toobit.com/api/usdt-m-error-codes.html"

def toobit_futures_client_order_id_policy() -> dict[str, Any]:
    """Return evidence-backed facts separately from unresolved constraints.

    'evidence_verified' refers only to the narrow documented statements below;
    'verified' is the execution-boundary approval flag and stays False.
    """
    return {
        "provider_namespace": "TOOBIT-FUTURES",
        "scope": "USDT-M_FUTURES_REGULAR_ORDERS",
        "evidence_status": "PARTIALLY_VERIFIED",
        "evidence_verified": True,
        "verified": False,
        "prefix": "AR",
        "max_length": None,
        "allowed_pattern": None,
        "policy_reference": TOOBIT_FUTURES_V2_DOCS,
        "evidence": {
            "submit_parameter": "newClientOrderId",
            "lookup_parameter": "origClientOrderId",
            "lookup_endpoint": "GET /api/v2/futures/order",
            "lookup_identity_fields": ["clientOrderId", "orderId", "status"],
            "duplicate_error_code": -1141,
            "duplicate_error_name": "ORDER_DUPLICATED",
            "duplicate_error_message": "Duplicate clientOrderId",
            "documented_uniqueness_scope": "among open orders",
            "sources": [
                TOOBIT_FUTURES_V2_DOCS,
                TOOBIT_ERROR_CODES_DOCS,
            ],
        },
        "unverified": [
            "CLIENT_ORDER_ID_MAX_LENGTH",
            "CLIENT_ORDER_ID_ALLOWED_CHARSET",
            "CLIENT_ID_UNIQUENESS_AFTER_ORDER_TERMINAL_STATE",
            "RETRY_OR_REPLAY_IDEMPOTENCY_SEMANTICS",
            "LOOKUP_CONSISTENCY_AND_RETENTION",
            "HISTORY_LOOKUP_COMPLETENESS_AND_PAGINATION",
        ],
        "verification_blocker": (
            "TOOBIT_CLIENT_ORDER_ID_CHARSET_AND_MAX_LENGTH_UNVERIFIED"
        ),
    }


__all__ = [
    "TOOBIT_ERROR_CODES_DOCS",
    "TOOBIT_FUTURES_V2_DOCS",
    "toobit_futures_client_order_id_policy",
]
