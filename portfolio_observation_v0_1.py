"""ARUNDA TRADER — PORTFOLIO OBSERVATION v0.1

Provider-neutral, read-only portfolio observation boundary.

This module only combines already-normalized account/balance observations
with an explicitly supplied position observation source. It does not infer
portfolio identity, capital, risk, sizing, exposure limits, or policy.
Unknown or untrusted sources remain unavailable and fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from account_balance_observation_v0_1 import AccountBalanceObservation


@dataclass(frozen=True)
class PositionObservation:
    symbol: str
    side: str
    quantity: Any
    entry_price: Any
    mark_price: Any
    notional: Optional[Any]
    unrealized_pnl: Optional[Any]
    realized_pnl: Optional[Any]
    source_id: Optional[str]
    source_type: Optional[str]
    source_timestamp: Optional[str]
    retrieved_at: str


@dataclass(frozen=True)
class PortfolioObservation:
    portfolio_id: Optional[str]
    account_id: Optional[str]
    account_type: Optional[str]
    environment: Optional[str]
    balances: Tuple[Any, ...]
    positions: Optional[Tuple[PositionObservation, ...]]
    total_exposure: Optional[float]
    exposure_source: Optional[str]
    source_status: str
    gaps: Tuple[str, ...]


def _text(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _number(value: Any, *, nonnegative: bool = False) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        result = float(value)
    except (TypeError, ValueError):
        return False
    if not isfinite(result):
        return False
    return not nonnegative or result >= 0


def _provenance(row: Mapping[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    values = []
    for key in ("source_id", "source_type", "source_timestamp"):
        if key not in row:
            values.append(None)
            continue
        value = _text(row[key])
        if value is None:
            raise RuntimeError(f"Invalid provenance field: {key}")
        values.append(value)
    return tuple(values)  # type: ignore[return-value]


def _normalize_position(row: Mapping[str, Any], retrieved_at: str) -> PositionObservation:
    symbol = _text(row.get("symbol"))
    side = _text(row.get("side"))
    if symbol is None or side is None:
        raise RuntimeError("Position symbol and side are required")

    quantity = row.get("quantity")
    if not _number(quantity, nonnegative=True):
        raise RuntimeError("Position quantity is invalid")

    for field in ("entry_price", "mark_price"):
        if not _number(row.get(field), nonnegative=True):
            raise RuntimeError(f"Position {field} is invalid")

    for field in ("notional", "unrealized_pnl", "realized_pnl"):
        value = row.get(field)
        if value is not None and not _number(value):
            raise RuntimeError(f"Position {field} is invalid")

    source_id, source_type, source_timestamp = _provenance(row)
    return PositionObservation(
        symbol=symbol,
        side=side,
        quantity=quantity,
        entry_price=row.get("entry_price"),
        mark_price=row.get("mark_price"),
        notional=row.get("notional"),
        unrealized_pnl=row.get("unrealized_pnl"),
        realized_pnl=row.get("realized_pnl"),
        source_id=source_id,
        source_type=source_type,
        source_timestamp=source_timestamp,
        retrieved_at=retrieved_at,
    )


def build_portfolio_observation(
    account_balance: AccountBalanceObservation,
    *,
    position_reader: Optional[Callable[[], Any]],
    portfolio_id: Optional[str] = None,
) -> PortfolioObservation:
    """Build a portfolio observation from trusted upstream observations.

    ``position_reader`` is deliberately injected. This module contains no
    exchange-specific position reader and performs no network access.
    Missing position source, identity, or exposure evidence is explicit.
    """
    if not isinstance(account_balance, AccountBalanceObservation):
        raise TypeError("account_balance must be AccountBalanceObservation")

    normalized_portfolio_id = _text(portfolio_id)
    account_id = account_balance.account.account_id
    account_type = account_balance.account.account_type
    environment = account_balance.account.environment

    gaps = []
    if normalized_portfolio_id is None:
        gaps.append("PORTFOLIO_ID_NOT_AVAILABLE")
    if account_id is None:
        gaps.append("ACCOUNT_ID_NOT_AVAILABLE")

    if position_reader is None:
        gaps.extend(("POSITION_SOURCE_NOT_AVAILABLE", "EXPOSURE_NOT_AVAILABLE"))
        return PortfolioObservation(
            portfolio_id=normalized_portfolio_id,
            account_id=account_id,
            account_type=account_type,
            environment=environment,
            balances=tuple(account_balance.balances),
            positions=None,
            total_exposure=None,
            exposure_source=None,
            source_status="PARTIAL_NOT_AVAILABLE",
            gaps=tuple(gaps),
        )

    result = position_reader()
    if result is None or getattr(result, "allowed", False) is not True:
        raise RuntimeError("Position observation unavailable")

    data = getattr(result, "data", None)
    if not isinstance(data, Mapping):
        raise RuntimeError("Position source payload is invalid")

    rows = data.get("positions")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise RuntimeError("Position source must provide a dynamic sequence")

    retrieved_at = _text(data.get("retrieved_at"))
    if retrieved_at is None:
        retrieved_at = account_balance.account.retrieved_at

    positions = tuple(
        _normalize_position(row, retrieved_at)
        for row in rows
        if isinstance(row, Mapping)
    )
    if len(positions) != len(rows):
        raise RuntimeError("Invalid position row")

    if positions and all(position.notional is not None for position in positions):
        total_exposure = sum(float(position.notional) for position in positions)
        exposure_source = "POSITION_NOTIONAL"
    else:
        total_exposure = None
        exposure_source = None
        gaps.append("EXPOSURE_NOT_AVAILABLE")

    return PortfolioObservation(
        portfolio_id=normalized_portfolio_id,
        account_id=account_id,
        account_type=account_type,
        environment=environment,
        balances=tuple(account_balance.balances),
        positions=positions,
        total_exposure=total_exposure,
        exposure_source=exposure_source,
        source_status="PARTIAL_NOT_AVAILABLE" if gaps else "AVAILABLE",
        gaps=tuple(gaps),
    )
