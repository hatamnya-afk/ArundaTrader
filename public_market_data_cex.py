from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import requests

from public_market_data_contract import (
    CANONICAL_OHLCV_FIELDS,
    PROVENANCE_FIELDS,
    PRODUCTION_TIMEFRAME,
    SOURCE_TYPES,
    FORBIDDEN,
    FAIL_CLOSED,
)


ENGINE_VERSION = "PUBLIC_CEX_INGESTION_v0.1"

PRIMARY_SOURCE_ID = "BITGET_SPOT_PUBLIC"
FAILOVER_SOURCE_ID = "KUCOIN_SPOT_PUBLIC"

BITGET_URL = "https://api.bitget.com/api/v2/spot/market/candles"
KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"

TIMEFRAME = PRODUCTION_TIMEFRAME
DEFAULT_LIMIT = 100
REQUEST_TIMEOUT = 15


class CEXDataError(RuntimeError):
    pass


def _decimal(value: str) -> Decimal:
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise CEXDataError("NON_NUMERIC_OHLCV")

    if not x.is_finite() or x <= 0:
        raise CEXDataError("INVALID_OHLCV_VALUE")

    return x


def _validate_bar(bar: dict) -> dict:
    required = set(CANONICAL_OHLCV_FIELDS) | set(PROVENANCE_FIELDS)

    if not required.issubset(bar):
        raise CEXDataError("MISSING_CANONICAL_FIELDS")

    if bar["timeframe"] != TIMEFRAME:
        raise CEXDataError("INVALID_TIMEFRAME")

    for field in ("open", "high", "low", "close", "volume"):
        _decimal(bar[field])

    if not (
        _decimal(bar["high"]) >= _decimal(bar["open"])
        and _decimal(bar["high"]) >= _decimal(bar["close"])
        and _decimal(bar["high"]) >= _decimal(bar["low"])
        and _decimal(bar["low"]) <= _decimal(bar["open"])
        and _decimal(bar["low"]) <= _decimal(bar["close"])
    ):
        raise CEXDataError("INVALID_OHLC_STRUCTURE")

    if not bar["source_id"]:
        raise CEXDataError("MISSING_SOURCE_ID")

    if bar["source_type"] not in SOURCE_TYPES:
        raise CEXDataError("INVALID_SOURCE_TYPE")

    return bar


def _deduplicate_and_sort(bars: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for bar in sorted(bars, key=lambda x: int(x["timestamp"])):
        ts = int(bar["timestamp"])

        if ts in seen:
            raise CEXDataError("DUPLICATE_CANDLE")

        seen.add(ts)
        result.append(bar)

    return result


def _bitget(symbol: str, limit: int) -> list[dict]:
    params = {
        "symbol": symbol,
        "granularity": "1h",
        "limit": limit,
    }

    response = requests.get(
        BITGET_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("code") != "00000":
        raise CEXDataError("BITGET_API_ERROR")

    rows = payload.get("data")

    if not isinstance(rows, list) or not rows:
        raise CEXDataError("BITGET_EMPTY_DATA")

    retrieved_at = datetime.now(timezone.utc).isoformat()

    bars = []

    for row in rows:
        if len(row) < 6:
            raise CEXDataError("BITGET_INVALID_ROW")

        # Bitget:
        # timestamp_ms, open, high, low, close, base_volume, ...
        bar = {
            "asset": symbol.replace("USDT", ""),
            "symbol": symbol,
            "timestamp": str(int(row[0]) // 1000),
            "timeframe": TIMEFRAME,
            "open": str(row[1]),
            "high": str(row[2]),
            "low": str(row[3]),
            "close": str(row[4]),
            "volume": str(row[5]),
            "source_id": PRIMARY_SOURCE_ID,
            "source_type": "CEX_PUBLIC_API",
            "source_timestamp": str(int(row[0]) // 1000),
            "retrieved_at": retrieved_at,
        }

        bars.append(_validate_bar(bar))

    return _deduplicate_and_sort(bars)


def _kucoin(symbol: str, limit: int) -> list[dict]:
    params = {
        "symbol": symbol,
        "type": "1hour",
    }

    response = requests.get(
        KUCOIN_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("code") != "200000":
        raise CEXDataError("KUCOIN_API_ERROR")

    rows = payload.get("data")

    if not isinstance(rows, list) or not rows:
        raise CEXDataError("KUCOIN_EMPTY_DATA")

    rows = rows[:limit]

    retrieved_at = datetime.now(timezone.utc).isoformat()

    bars = []

    for row in rows:
        if len(row) < 6:
            raise CEXDataError("KUCOIN_INVALID_ROW")

        # KuCoin:
        # timestamp_s, open, close, high, low, volume, turnover
        bar = {
            "asset": symbol.replace("USDT", ""),
            "symbol": symbol,
            "timestamp": str(int(row[0])),
            "timeframe": TIMEFRAME,
            "open": str(row[1]),
            "high": str(row[3]),
            "low": str(row[4]),
            "close": str(row[2]),
            "volume": str(row[5]),
            "source_id": FAILOVER_SOURCE_ID,
            "source_type": "CEX_PUBLIC_API",
            "source_timestamp": str(int(row[0])),
            "retrieved_at": retrieved_at,
        }

        bars.append(_validate_bar(bar))

    return _deduplicate_and_sort(bars)


def fetch_ohlcv(symbol: str = "BTCUSDT", limit: int = DEFAULT_LIMIT) -> dict:
    if limit < 1:
        raise CEXDataError("INVALID_LIMIT")

    # FAILOVER, NOT BLENDING:
    # Bitget is attempted first.
    # KuCoin is used only if Bitget fails.
    try:
        bars = _bitget(symbol, limit)

        return {
            "engine_version": ENGINE_VERSION,
            "status": "READY",
            "source_id": PRIMARY_SOURCE_ID,
            "source_type": "CEX_PUBLIC_API",
            "failover_used": False,
            "blended": False,
            "bars": bars,
        }

    except Exception as primary_error:
        if not FAIL_CLOSED:
            raise

        try:
            bars = _kucoin(symbol, limit)

            return {
                "engine_version": ENGINE_VERSION,
                "status": "READY",
                "source_id": FAILOVER_SOURCE_ID,
                "source_type": "CEX_PUBLIC_API",
                "failover_used": True,
                "blended": False,
                "primary_error": type(primary_error).__name__,
                "bars": bars,
            }

        except Exception as failover_error:
            raise CEXDataError(
                "ALL_CEX_SOURCES_FAILED"
            ) from failover_error


if __name__ == "__main__":
    result = fetch_ohlcv("BTCUSDT", 3)

    print("ENGINE=", result["engine_version"])
    print("STATUS=", result["status"])
    print("SOURCE=", result["source_id"])
    print("FAILOVER=", result["failover_used"])
    print("BLENDED=", result["blended"])
    print("BARS=", len(result["bars"]))

    for bar in result["bars"]:
        print(
            bar["timestamp"],
            bar["open"],
            bar["high"],
            bar["low"],
            bar["close"],
            bar["volume"],
            bar["source_id"],
        )
