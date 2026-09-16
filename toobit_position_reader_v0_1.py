"""ARUNDA TRADER — TOOBIT POSITION READER v0.1

Provider-specific, read-only Position Source adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Optional

POSITION_ENDPOINT = "/api/v1/futures/positions"
SOURCE_ID = "TOOBIT"
SOURCE_TYPE = "CEX_PRIVATE_API"


@dataclass(frozen=True)
class PositionReaderResult:
    allowed: bool
    data: Any
    status: str = "PASS"
    reason: str = ""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Invalid {field}")
    return value.strip()


def _optional_text(value: Any, field: str) -> Optional[str]:
    if value is None:
        return None
    return _text(value, field)


def _numeric(value: Any, field: str, *, nonnegative: bool = False) -> str:
    if value is None or isinstance(value, bool):
        raise RuntimeError(f"Missing {field}")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise RuntimeError(f"Invalid {field}") from None
    if not isfinite(number) or (nonnegative and number < 0):
        raise RuntimeError(f"Invalid {field}")
    return str(value)


def _payload(result: Any) -> tuple[list[Mapping[str, Any]], Optional[str], Optional[str], Optional[str], Optional[str]]:
    if result is None or getattr(result, "allowed", False) is not True:
        raise RuntimeError("Toobit Position Source unavailable")

    data = getattr(result, "data", None)
    if isinstance(data, Mapping):
        raw = data.get("positions")
        if raw is None:
            raw = data.get("data")
        source_id = data.get("source_id", SOURCE_ID)
        source_type = data.get("source_type", SOURCE_TYPE)
        source_timestamp = data.get("source_timestamp")
        retrieved_at = data.get("retrieved_at")
    else:
        # The official Toobit SDK returns the Position endpoint body as a list.
        raw = data
        source_id = SOURCE_ID
        source_type = SOURCE_TYPE
        source_timestamp = None
        retrieved_at = None

    if not isinstance(raw, list):
        raise RuntimeError("Toobit Position payload must contain a dynamic list")

    rows: list[Mapping[str, Any]] = []
    for row in raw:
        if not isinstance(row, Mapping):
            raise RuntimeError("Invalid Toobit Position row")
        rows.append(row)

    source_id = _text(source_id, "source_id")
    source_type = _text(source_type, "source_type")
    source_timestamp = _optional_text(source_timestamp, "source_timestamp")
    retrieved_at = _optional_text(retrieved_at, "retrieved_at")
    return rows, source_id, source_type, source_timestamp, retrieved_at


def _normalize_row(
    row: Mapping[str, Any],
    *,
    source_id: str,
    source_type: str,
    source_timestamp: Optional[str],
) -> dict[str, Any]:
    symbol = _text(row.get("symbol"), "symbol")
    side = _text(row.get("side"), "side").upper()
    if side not in {"LONG", "SHORT"}:
        raise RuntimeError("Invalid position side")

    quantity = _numeric(row.get("position"), "position", nonnegative=True)
    entry_price = _numeric(row.get("avgPrice"), "avgPrice", nonnegative=True)
    mark_price = _numeric(row.get("markPrice"), "markPrice", nonnegative=True)

    position_value = row.get("positionValue")
    notional = None if position_value is None else _numeric(position_value, "positionValue", nonnegative=True)

    unrealized_pnl = row.get("unrealizedPnL")
    if unrealized_pnl is not None:
        unrealized_pnl = _numeric(unrealized_pnl, "unrealizedPnL")

    realized_pnl = row.get("realizedPnL")
    if realized_pnl is not None:
        realized_pnl = _numeric(realized_pnl, "realizedPnL")

    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "entry_price": entry_price,
        "mark_price": mark_price,
        "notional": notional,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "source_id": source_id,
        "source_type": source_type,
        "source_timestamp": source_timestamp,
    }


def build_toobit_position_reader(adapter: Any):
    """Return a deterministic read-only reader over Toobit's Position API."""
    if adapter is None or not callable(getattr(adapter, "_signed_get", None)):
        raise TypeError("adapter must provide _signed_get")

    def read_positions() -> PositionReaderResult:
        result = adapter._signed_get(POSITION_ENDPOINT, params={})
        rows, source_id, source_type, source_timestamp, retrieved_at = _payload(result)
        normalized = [
            _normalize_row(
                row,
                source_id=source_id,
                source_type=source_type,
                source_timestamp=source_timestamp,
            )
            for row in rows
        ]
        return PositionReaderResult(
            allowed=True,
            data={
                "positions": normalized,
                "source_id": source_id,
                "source_type": source_type,
                "source_timestamp": source_timestamp,
                "retrieved_at": retrieved_at,
            },
            status=getattr(result, "status", "PASS"),
            reason=getattr(result, "reason", ""),
        )

    return read_positions
