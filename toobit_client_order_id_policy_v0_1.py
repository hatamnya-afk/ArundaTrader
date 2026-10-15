"""Evidence ledger for Toobit Futures client-order IDs and reconciliation.

Toobit Support ticket #20261012000242 (reply 2026-10-13) confirms the
provider's stated client-ID constraints and several order-history semantics.
The adapter execution policy remains NOT APPROVED: Toobit specifies no safe
recovery procedure when a timed-out submission is followed by NOT_FOUND, and
history cannot be queried directly by client ID.
"""
from __future__ import annotations

from typing import Any

TOOBIT_FUTURES_V2_DOCS = "https://api-docs.toobit.com/api/usdt-m-api-v2"
TOOBIT_ERROR_CODES_DOCS = "https://api-docs.toobit.com/api/usdt-m-error-codes.html"
TOOBIT_SUPPORT_TICKET = "Toobit Support ticket #20261012000242, reply 2026-10-13"


def toobit_futures_client_order_id_policy() -> dict[str, Any]:
    """Return support-confirmed constraints without granting submit approval.

    provider_max_length is Toobit's stated hard limit. The effective local
    generation cap is 64 and the regex is a conservative local subset of
    Toobit's recommended characters; Toobit says it does not enforce a regex.
    verified deliberately remains False because timeout recovery is unresolved.
    """
    return {
        "provider_namespace": "TOOBIT-FUTURES-USDTM",
        "scope": "USDT-M_FUTURES_REGULAR_ORDERS",
        "evidence_status": "SUPPORT_CONFIRMED_CONSTRAINTS_RECOVERY_UNRESOLVED",
        "evidence_verified": True,
        "client_id_constraints_verified": True,
        "verified": False,
        "submission_enabled": False,
        "automatic_retry_after_ambiguous_submit": False,
        "prefix": "AR",
        "provider_max_length": 255,
        "max_length": 64,
        "allowed_pattern": r"^[A-Za-z0-9_-]{1,64}$",
        "local_policy_notes": {
            "max_length": "64 local cap chosen within provider recommendation (36 or 64); provider hard max is 255",
            "charset": "local policy uses provider-recommended [A-Za-z0-9_-]; provider says no regex validation",
            "scope": "USDT-M only; support explicitly says USDT-M and USDC-M constraints differ but gives no USDC-M values",
        },
        "policy_reference": TOOBIT_FUTURES_V2_DOCS,
        "support_ticket": TOOBIT_SUPPORT_TICKET,
        "evidence": {
            "submit_parameter": "newClientOrderId",
            "lookup_parameter": "origClientOrderId",
            "lookup_endpoint": "GET /api/v2/futures/order",
            "lookup_identity_fields": ["clientOrderId", "orderId", "status"],
            "history_endpoint": "GET /api/v2/futures/history-orders",
            "history_cursor": "orderId",
            "history_limit_default": 20,
            "history_limit_max": 1000,
            "history_retention": "six months",
            "history_sorting": "by time",
            "history_direct_client_id_query": False,
            "history_excludes_creation_failures": True,
            "duplicate_error_code": -1141,
            "duplicate_error_name": "ORDER_DUPLICATED",
            "duplicate_submission": "rejected; original result is not returned",
            "provider_idempotency_wording": "support says idempotency guarantee, while also specifying duplicate request rejection and no original-result replay",
            "provider_hard_max_length": 255,
            "provider_regex_validation": False,
            "provider_recommended_charset": "[A-Za-z0-9_-]",
            "provider_recommended_length": [36, 64],
            "provider_uniqueness_scope": "order-level",
            "provider_id_reuse_after_terminal_state": False,
            "successful_submit_subsequently_queryable": True,
            "maximum_lookup_propagation_delay": None,
            "timeout_then_not_found_recovery_procedure": None,
            "history_exhaustive_recovery_by_client_id": False,
            "sources": [
                TOOBIT_FUTURES_V2_DOCS,
                TOOBIT_ERROR_CODES_DOCS,
                TOOBIT_SUPPORT_TICKET,
            ],
        },
        "unverified": [
            "USDC_M_CLIENT_ID_CONSTRAINT_VALUES",
            "MAX_LOOKUP_PROPAGATION_DELAY",
            "SAFE_RECOVERY_AFTER_TIMEOUT_AND_NOT_FOUND",
            "EXHAUSTIVE_HISTORY_RECOVERY_BY_CLIENT_ID",
            "PRODUCTION_ATOMIC_CLAIM_STORE_DURABILITY",
            "LIVE_PROVIDER_ORDER_OUTCOME_EVIDENCE",
        ],
        "evidence_record": "TOOBIT_CLIENT_ORDER_ID_OFFICIAL_EVIDENCE_V0_3.md",
        "verification_blocker": "TOOBIT_AMBIGUOUS_TIMEOUT_RECOVERY_UNSPECIFIED",
    }


__all__ = [
    "TOOBIT_ERROR_CODES_DOCS",
    "TOOBIT_FUTURES_V2_DOCS",
    "TOOBIT_SUPPORT_TICKET",
    "toobit_futures_client_order_id_policy",
]
