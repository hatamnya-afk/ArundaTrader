"""
ARUNDA MARKET TECHNICAL PERSISTENCE v0.1

Purpose
-------
Persist real TechnicalRecord objects into market_technical.

Rules
-----
- Consumes real TechnicalRecord objects only.
- No synthetic values.
- No indicator recalculation.
- No history modification.
- No identity repair.
- NULL is preserved when a TechnicalRecord does not provide a field.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable


DATABASE_FILE = "arunda.db"
TABLE_NAME = "market_technical"

PERSISTENCE_VERSION = "TECHNICAL_PERSISTENCE_v0.1"
SOURCE = "ARUNDA_TECHNICAL_ENGINE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get(record: dict[str, Any], *keys: str) -> Any:
    """
    Return the first existing key.
    """
    for key in keys:
        if key in record:
            return record[key]
    return None


def _nested(record: dict[str, Any], group: str, key: str) -> Any:
    value = record.get(group)

    if not isinstance(value, dict):
        return None

    return value.get(key)


def _flatten_record(record_obj: Any) -> dict[str, Any]:
    """
    Convert TechnicalRecord into the relational market_technical contract.

    Only values genuinely present in TechnicalRecord are mapped.
    Missing extended fields remain NULL.
    """

    record = asdict(record_obj)

    trend = record.get("trend") or {}
    momentum = record.get("momentum") or {}
    volatility = record.get("volatility") or {}
    volume = record.get("volume") or {}
    structure = record.get("structure") or {}
    regime = record.get("regime") or {}

    timestamp = record.get("timestamp")
    symbol = record.get("symbol")
    history_points = record.get("history_points")

    close = None
    previous_close = None

    # TechnicalRecord itself does not expose these as top-level fields.
    # They are therefore deliberately left NULL rather than fabricated.

    row = {
        # ------------------------------------------------------------------
        # Identity / core
        # ------------------------------------------------------------------
        "timestamp": timestamp,
        "symbol": symbol,
        "history_points": history_points,
        "close": close,
        "previous_close": previous_close,

        # ------------------------------------------------------------------
        # Returns
        # ------------------------------------------------------------------
        "return_5": momentum.get("return_5"),
        "return_10": momentum.get("return_10"),
        "return_20": momentum.get("return_20"),

        # Existing legacy-compatible return fields
        "return_1": None,
        "return_3": None,

        # ------------------------------------------------------------------
        # Trend
        # ------------------------------------------------------------------
        "sma_20": trend.get("sma_20"),
        "ema_20": trend.get("ema_20"),

        "trend": trend.get("strength"),

        # Direction/alignment are represented by the newer textual contract.
        "trend_regime": regime.get("state"),

        # ------------------------------------------------------------------
        # Momentum
        # ------------------------------------------------------------------
        "momentum_5": None,
        "momentum_10": None,
        "momentum_20": None,

        "momentum_1": None,
        "momentum_3": None,

        "rsi_14": momentum.get("rsi_14"),
        "rsi14": momentum.get("rsi_14"),

        # ------------------------------------------------------------------
        # Volatility
        # ------------------------------------------------------------------
        "volatility_20": volatility.get("volatility_20"),
        "volatility": volatility.get("volatility_20"),

        # ------------------------------------------------------------------
        # Volume
        # ------------------------------------------------------------------
        "volume": None,
        "volume_ratio": volume.get("volume_ratio_20"),
        "relative_volume_20": volume.get("volume_ratio_20"),

        # ------------------------------------------------------------------
        # Structure
        # ------------------------------------------------------------------
        "range_position_20": structure.get("price_position_20"),
        "swing_structure": structure.get("state"),

        # ------------------------------------------------------------------
        # Regime
        # ------------------------------------------------------------------
        "regime": regime.get("state"),

        # ------------------------------------------------------------------
        # Availability / quality
        # ------------------------------------------------------------------
        "data_status": record.get("data_quality"),
        "technical_available": (
            1
            if record.get("data_quality") == "READY"
            else 0
        ),

        # A complete technical record requires the principal calculated
        # groups. We only mark it complete when those real groups exist.
        "technical_completeness": _technical_completeness(
            record
        ),

        "completeness": _technical_completeness(
            record
        ),

        "available": (
            1
            if record.get("data_quality") == "READY"
            else 0
        ),

        # ------------------------------------------------------------------
        # Engine lineage
        # ------------------------------------------------------------------
        "source": SOURCE,
        "engine_version": record.get(
            "engine_version"
        ),
        "technical_version": record.get(
            "engine_version"
        ),

        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    return row


def _technical_completeness(
    record: dict[str, Any],
) -> float:
    """
    Completeness is based only on actual TechnicalRecord groups.

    No fabricated indicator values are used.
    """

    required_groups = (
        "trend",
        "momentum",
        "volatility",
        "volume",
        "structure",
        "regime",
    )

    present = 0

    for group in required_groups:
        value = record.get(group)

        if isinstance(value, dict) and value:
            present += 1

    return present / len(required_groups)


def _validate_table(
    conn: sqlite3.Connection,
) -> set[str]:

    rows = conn.execute(
        f"PRAGMA table_info({TABLE_NAME})"
    ).fetchall()

    if not rows:
        raise RuntimeError(
            f"Required table '{TABLE_NAME}' does not exist."
        )

    return {row[1] for row in rows}


def persist_record(
    conn: sqlite3.Connection,
    technical_record: Any,
) -> int:
    """
    Persist one real TechnicalRecord.

    Returns
    -------
    int
        SQLite row id.
    """

    columns = _validate_table(conn)

    record = asdict(technical_record)

    if not record.get("symbol"):
        raise ValueError(
            "TechnicalRecord symbol is required."
        )

    if not record.get("timestamp"):
        raise ValueError(
            "TechnicalRecord timestamp is required."
        )

    row = _flatten_record(
        technical_record
    )

    # Only write columns that actually exist in production schema.
    payload = {
        key: value
        for key, value in row.items()
        if key in columns
    }

    if not payload:
        raise RuntimeError(
            "No compatible columns found for TechnicalRecord."
        )

    names = list(payload.keys())

    placeholders = ", ".join(
        "?"
        for _ in names
    )

    column_sql = ", ".join(
        f'"{name}"'
        for name in names
    )

    sql = f"""
        INSERT INTO {TABLE_NAME}
        ({column_sql})
        VALUES ({placeholders})
    """

    cursor = conn.execute(
        sql,
        [
            payload[name]
            for name in names
        ],
    )

    return int(cursor.lastrowid)


def persist_records(
    conn: sqlite3.Connection,
    records: Iterable[Any],
) -> int:

    count = 0

    for record in records:

        persist_record(
            conn,
            record,
        )

        count += 1

    return count


def persist_records_transaction(
    records: Iterable[Any],
    database_file: str = DATABASE_FILE,
) -> int:
    """
    Production persistence entry point.

    The transaction is atomic:
    either all real TechnicalRecords are persisted,
    or none are committed.
    """

    records = list(records)

    if not records:
        return 0

    conn = sqlite3.connect(
        database_file
    )

    try:

        count = persist_records(
            conn,
            records,
        )

        conn.commit()

        return count

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


__all__ = [
    "persist_record",
    "persist_records",
    "persist_records_transaction",
]