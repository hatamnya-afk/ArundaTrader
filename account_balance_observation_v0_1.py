"""ARUNDA TRADER — REAL ACCOUNT/BALANCE OBSERVATION PRODUCER v0.1

Provider-neutral read-only producer.

Scope is deliberately limited to account and balance observations.
No positions, exposure, risk, sizing, order intent, execution, or DB access.

The producer receives an already-resolved ExchangeAdapter. Provider-specific
knowledge remains outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping, Optional, Sequence, Tuple


CAPABILITY_ACCOUNT_READ = "ACCOUNT_READ"
CAPABILITY_BALANCE_READ = "BALANCE_READ"


@dataclass(frozen=True)
class AccountObservation:
    account_id: Optional[str]
    account_type: Optional[str]
    environment: Optional[str]
    source_id: Optional[str]
    source_type: Optional[str]
    source_timestamp: Optional[str]
    retrieved_at: str
    status: str


@dataclass(frozen=True)
class BalanceObservation:
    asset: str
    free: Any
    locked: Any
    total: Any
    source_id: Optional[str]
    source_type: Optional[str]
    source_timestamp: Optional[str]
    retrieved_at: str


@dataclass(frozen=True)
class AccountBalanceObservation:
    account: AccountObservation
    balances: Tuple[BalanceObservation, ...]
    balance_observation_complete: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _result_data(result: Any) -> Mapping[str, Any]:
    data = getattr(result, "data", None)
    return data if isinstance(data, Mapping) else {}


def _provenance(data: Mapping[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    values = []
    for key in ("source_id", "source_type", "source_timestamp"):
        if key not in data:
            values.append(None)
            continue
        value = data[key]
        normalized = _text(value)
        if normalized is None:
            raise RuntimeError(f"Invalid provenance field: {key}")
        values.append(normalized)
    return tuple(values)  # type: ignore[return-value]


def _valid_nonnegative_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        if isinstance(value, float) and not isfinite(value):
            return False
        return value >= 0
    except (TypeError, ValueError):
        return False


def _require_read_capabilities(adapter: Any) -> None:
    capabilities = adapter.capabilities()
    if not isinstance(capabilities, Mapping):
        raise RuntimeError("Invalid adapter capability map")
    if capabilities.get(CAPABILITY_ACCOUNT_READ) is not True:
        raise RuntimeError("ACCOUNT_READ is unavailable")
    if capabilities.get(CAPABILITY_BALANCE_READ) is not True:
        raise RuntimeError("BALANCE_READ is unavailable")


def build_account_balance_observation(
    adapter: Any,
    *,
    retrieved_at: Optional[str] = None,
) -> AccountBalanceObservation:
    """Build one immutable observation from adapter read results.

    ``retrieved_at`` is injectable so the same adapter inputs can produce a
    byte-for-byte equivalent observation during deterministic verification.
    When omitted, the current UTC retrieval time is used for live observation.
    """
    _require_read_capabilities(adapter)

    account_result = adapter.get_account()
    balance_result = adapter.get_balances()

    if account_result is None or getattr(account_result, "allowed", False) is not True:
        raise RuntimeError("Account observation unavailable")
    if balance_result is None or getattr(balance_result, "allowed", False) is not True:
        raise RuntimeError("Balance observation unavailable")

    effective_retrieved_at = _utc_now() if retrieved_at is None else _text(retrieved_at)
    if effective_retrieved_at is None:
        raise RuntimeError("retrieved_at must be a non-empty string")

    account_data = _result_data(account_result)
    balance_data = _result_data(balance_result)

    account_source_id, account_source_type, account_source_timestamp = _provenance(account_data)

    account = AccountObservation(
        account_id=_text(account_data.get("account_id")),
        account_type=_text(account_data.get("account_type")),
        environment=_text(account_data.get("environment")),
        source_id=account_source_id,
        source_type=account_source_type,
        source_timestamp=account_source_timestamp,
        retrieved_at=effective_retrieved_at,
        status=str(getattr(account_result, "status", "UNKNOWN")),
    )

    rows = balance_data.get("balances", [])
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise RuntimeError("Balance payload must contain a dynamic sequence")

    observations = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError("Invalid balance row")

        asset = _text(row.get("asset"))
        if asset is None:
            raise RuntimeError("Balance asset is required")

        free = row.get("free")
        locked = row.get("locked")
        total = row.get("total")
        if not all(_valid_nonnegative_number(value) for value in (free, locked, total)):
            raise RuntimeError("Invalid balance numeric value")

        source_id, source_type, source_timestamp = _provenance(row)
        observations.append(
            BalanceObservation(
                asset=asset,
                free=free,
                locked=locked,
                total=total,
                source_id=source_id if source_id is not None else account_source_id,
                source_type=source_type if source_type is not None else account_source_type,
                source_timestamp=(
                    source_timestamp
                    if source_timestamp is not None
                    else account_source_timestamp
                ),
                retrieved_at=effective_retrieved_at,
            )
        )

    balance_observation_complete = (
        balance_data.get("balance_observation_complete") is True
    )

    return AccountBalanceObservation(
        account=account,
        balances=tuple(observations),
        balance_observation_complete=balance_observation_complete,
    )
