"""Fail-closed runtime dependency factory for an explicitly enabled order path.

The normal pipeline remains read-only unless two independent runtime switches
are explicitly enabled and a separate absolute SQLite claim-store path is given.
This factory never changes global execution constants or starts a runtime.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from exchange_execution_atomic_intent_claim_store_v0_1 import SQLiteIntentClaimStore
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter
from toobit_https_transport_v0_1 import toobit_https_transport


def load_execution_dependencies(*, production_database_path: str | Path) -> tuple[Any, Any]:
    if os.getenv("ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT") != "1":
        raise ValueError("PROVIDER_ORDER_ATTEMPT_NOT_EXPLICITLY_ENABLED")
    if os.getenv("ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION") != "1":
        raise ValueError("TOOBIT_ORDER_SUBMISSION_NOT_EXPLICITLY_ENABLED")

    claim_path_raw = os.getenv("ARUNDA_EXECUTION_CLAIM_DB", "").strip()
    if not claim_path_raw:
        raise ValueError("ISOLATED_EXECUTION_CLAIM_DB_PATH_REQUIRED")
    claim_path = Path(claim_path_raw).expanduser()
    if not claim_path.is_absolute():
        raise ValueError("EXECUTION_CLAIM_DB_PATH_MUST_BE_ABSOLUTE")

    production_path = Path(production_database_path).expanduser().resolve()
    resolved_claim_path = claim_path.resolve()
    if resolved_claim_path == production_path:
        raise ValueError("CLAIM_STORE_MUST_NOT_USE_PRODUCTION_DATABASE")
    if not resolved_claim_path.parent.exists():
        raise ValueError("CLAIM_STORE_PARENT_DIRECTORY_MISSING")

    adapter = ToobitExchangeAdapter(
        transport=toobit_https_transport,
        enable_order_submission=True,
    )
    if not adapter.capabilities().order_submission:
        raise ValueError("TOOBIT_SUBMISSION_CREDENTIALS_OR_TRANSPORT_UNAVAILABLE")

    claim_store = SQLiteIntentClaimStore(resolved_claim_path)
    return adapter, claim_store


__all__ = ["load_execution_dependencies"]
