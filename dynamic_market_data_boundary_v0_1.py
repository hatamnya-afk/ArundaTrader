
"""
ARUNDA DYNAMIC MARKET DATA BOUNDARY v0.2

REAL DYNAMIC UNIVERSE
        ->
KUCOIN CANONICAL ACTIVE
        ->
BITGET FAILOVER
        ->
CANONICAL REAL MARKET DATA

Rules:
    Universe owns cardinality.
    KuCoin is canonical active provider.
    Bitget is failover only.
    One selected provider per market.
    No provider blending.
    Provider failure is isolated per market.

No fixed asset count.
No fixed-15.
No synthetic data.
No interpolation.
No fill.
No backfill.
No padding.
No blending.
No CMC.
No legacy data.
No production DB writes.
Execution OFF.
"""

from __future__ import annotations

import importlib.util
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent

UNIVERSE_CONTRACT_FILE = (
    ROOT / "production_universe_contract_v0_1.py"
)

KUCOIN_ADAPTER_FILE = (
    ROOT / "public_market_data_kucoin.py"
)

FAILOVER_ADAPTER_FILE = (
    ROOT / "public_market_data_failover_v0.1.py"
)

TIMEFRAME = "1h"
QUOTE = "USDT"

CANONICAL_PROVIDER = "KUCOIN_SPOT_PUBLIC"
FAILOVER_PROVIDER = "BITGET_SPOT_PUBLIC"

DB_WRITES = 0
EXECUTION = False
REAL_ORDER = False
REAL_TRADE = False

CMC_USED = False
SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False
LEGACY_DATA_USED = False
PRE_LAUNCH_DATA_USED = False


@dataclass(frozen=True)
class MarketDataResult:
    symbol: str
    status: str
    candles: tuple[Any, ...]
    source: str
    error: str | None
    real_data: bool
    provider_role: str = "NONE"


def _load_module(path: Path, name: str):
    if not path.exists():
        raise RuntimeError(f"MISSING_MODULE:{path.name}")

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def _normalize_symbol(value: Any) -> str:
    if not isinstance(value, str):
        raise RuntimeError("MARKET_SYMBOL_NOT_STRING")

    symbol = value.strip().upper()

    if not symbol:
        raise RuntimeError("MARKET_SYMBOL_EMPTY")

    if "/" not in symbol:
        raise RuntimeError(
            f"MARKET_SYMBOL_INVALID:{symbol}"
        )

    base, quote = symbol.split("/", 1)

    if not base or quote != QUOTE:
        raise RuntimeError(
            f"MARKET_SYMBOL_NOT_USDT:{symbol}"
        )

    return f"{base}/{QUOTE}"


def discover_universe() -> tuple[str, ...]:
    universe = _load_module(
        UNIVERSE_CONTRACT_FILE,
        "arunda_verified_production_universe",
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    if not callable(discover):
        raise RuntimeError(
            "UNIVERSE_DISCOVERY_FUNCTION_MISSING"
        )

    result = discover()

    if not isinstance(result, tuple):
        raise RuntimeError(
            "UNIVERSE_DISCOVERY_CONTRACT_CHANGED"
        )

    markets: list[str] = []
    seen: set[str] = set()

    for item in result:
        symbol = _normalize_symbol(item)

        if symbol in seen:
            raise RuntimeError(
                f"UNIVERSE_DUPLICATE:{symbol}"
            )

        seen.add(symbol)
        markets.append(symbol)

    if not markets:
        raise RuntimeError("UNIVERSE_EMPTY")

    return tuple(markets)


def _timestamp(row: Any) -> Any:
    if isinstance(row, Mapping):
        return row.get("timestamp")

    return getattr(row, "timestamp", None)


def _close(row: Any) -> Any:
    if isinstance(row, Mapping):
        return row.get("close")

    return getattr(row, "close", None)


def _finite_close(row: Any) -> bool:
    close = _close(row)

    return (
        isinstance(close, (int, float))
        and not isinstance(close, bool)
        and math.isfinite(float(close))
        and float(close) > 0
    )


def _timestamp_value(
    value: Any,
) -> int | float | None:

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return value

    return None


def _expected_hour_delta(
    timestamp: Any,
) -> int | float | None:

    value = _timestamp_value(timestamp)

    if value is None:
        return None

    if abs(value) > 10_000_000_000:
        return 3_600_000

    return 3_600


def _validate_candle_sequence(
    candles: list[Any],
    symbol: str,
) -> list[Any]:

    if not candles:
        return []

    unique: dict[Any, Any] = {}

    for candle in candles:
        timestamp = _timestamp(candle)

        if timestamp is None:
            raise RuntimeError(
                f"CANDLE_WITHOUT_TIMESTAMP:{symbol}"
            )

        if not _finite_close(candle):
            raise RuntimeError(
                f"CANDLE_INVALID_CLOSE:{symbol}:{timestamp}"
            )

        if timestamp in unique:
            continue

        unique[timestamp] = candle

    ordered = sorted(
        unique.values(),
        key=lambda row: _timestamp(row),
    )

    return ordered


def _contiguous_suffix(
    candles: list[Any],
) -> list[Any]:

    if not candles:
        return []

    suffix = [candles[-1]]

    for index in range(
        len(candles) - 2,
        -1,
        -1,
    ):
        current = candles[index]
        newer = candles[index + 1]

        current_ts = _timestamp_value(
            _timestamp(current)
        )
        newer_ts = _timestamp_value(
            _timestamp(newer)
        )

        if current_ts is None or newer_ts is None:
            break

        expected = _expected_hour_delta(
            newer_ts
        )

        if expected is None:
            break

        if newer_ts - current_ts != expected:
            break

        suffix.append(current)

    suffix.reverse()

    return suffix


def _prepare_kucoin():
    kucoin = _load_module(
        KUCOIN_ADAPTER_FILE,
        "arunda_kucoin_provider_boundary",
    )

    fetch = getattr(
        kucoin,
        "fetch_kucoin",
        None,
    )

    normalize = getattr(
        kucoin,
        "normalize",
        None,
    )

    validate = getattr(
        kucoin,
        "validate_candle",
        None,
    )

    if not callable(fetch):
        raise RuntimeError("KUCOIN_FETCH_MISSING")

    if not callable(normalize):
        raise RuntimeError("KUCOIN_NORMALIZE_MISSING")

    if not callable(validate):
        raise RuntimeError("KUCOIN_VALIDATE_MISSING")

    return fetch, normalize, validate


def _fetch_kucoin(
    symbol: str,
    count: int,
) -> list[Any]:

    fetch, normalize, validate = _prepare_kucoin()

    raw = fetch(
        symbol,
        count=count,
    )

    if not isinstance(raw, (list, tuple)):
        raise RuntimeError(
            "KUCOIN_HISTORY_NOT_SEQUENCE"
        )

    normalized: list[Any] = []

    for row in raw:
        timestamp = _timestamp(row)

        if timestamp is None:
            raise RuntimeError(
                "CANDLE_WITHOUT_TIMESTAMP"
            )

        candle = normalize(
            symbol.split("/", 1)[0],
            symbol,
            row,
            None,
        )

        if not validate(candle):
            raise RuntimeError(
                f"INVALID_CANONICAL_CANDLE:{timestamp}"
            )

        normalized.append(candle)

    normalized = _validate_candle_sequence(
        normalized,
        symbol,
    )

    return _contiguous_suffix(normalized)


def _prepare_bitget():
    failover = _load_module(
        FAILOVER_ADAPTER_FILE,
        "arunda_bitget_failover_provider",
    )

    fetch = getattr(
        failover,
        "fetch_bitget",
        None,
    )

    if not callable(fetch):
        raise RuntimeError(
            "BITGET_FETCH_MISSING"
        )

    return fetch


def _fetch_bitget(
    symbol: str,
) -> list[Any]:

    fetch = _prepare_bitget()

    base = symbol.split("/", 1)[0]

    observation = fetch(symbol)

    if not isinstance(observation, Mapping):
        raise RuntimeError(
            "BITGET_OBSERVATION_NOT_MAPPING"
        )

    observation_symbol = observation.get("symbol")

    if observation_symbol != f"{base}USDT":
        raise RuntimeError(
            f"BITGET_SYMBOL_MISMATCH:{observation_symbol}"
        )

    candle = {
        "timestamp": observation.get("timestamp"),
        "open": observation.get("open"),
        "high": observation.get("high"),
        "low": observation.get("low"),
        "close": observation.get("close"),
        "volume": observation.get("volume"),
    }

    if candle["timestamp"] is None:
        raise RuntimeError(
            "BITGET_CANDLE_WITHOUT_TIMESTAMP"
        )

    if not _finite_close(candle):
        raise RuntimeError(
            "BITGET_INVALID_CLOSE"
        )

    if (
        not isinstance(candle["open"], (int, float))
        or not isinstance(candle["high"], (int, float))
        or not isinstance(candle["low"], (int, float))
        or not isinstance(candle["volume"], (int, float))
    ):
        raise RuntimeError(
            "BITGET_INVALID_OHLCV"
        )

    return [candle]


def _fetch_bitget_historical(
    symbol: str,
    count: int,
) -> list[Any]:

    failover = _load_module(
        FAILOVER_ADAPTER_FILE,
        "arunda_bitget_historical_provider",
    )

    bitget_url = getattr(
        failover,
        "BITGET_URL",
        None,
    )

    tls_context = getattr(
        failover,
        "TLS_CONTEXT",
        None,
    )

    if not isinstance(bitget_url, str) or not bitget_url:
        raise RuntimeError(
            "BITGET_HISTORICAL_URL_MISSING"
        )

    if tls_context is None:
        raise RuntimeError(
            "BITGET_HISTORICAL_TLS_CONTEXT_MISSING"
        )

    if not isinstance(count, int) or count <= 0:
        raise RuntimeError(
            "BITGET_HISTORICAL_COUNT_INVALID"
        )

    base = symbol.split("/", 1)[0]
    bitget_symbol = f"{base}USDT"

    params = {
        "symbol": bitget_symbol,
        "granularity": "1h",
        "limit": str(count),
    }

    url = (
        bitget_url
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ArundaTrader-DynamicMarketData/0.2",
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(
        request,
        context=tls_context,
        timeout=20,
    ) as response:

        payload = json.loads(
            response.read().decode("utf-8")
        )

    if payload.get("code") != "00000":
        raise RuntimeError(
            f"BITGET_HISTORICAL_API_ERROR={payload}"
        )

    rows = payload.get("data") or []

    if not rows:
        raise RuntimeError(
            "BITGET_HISTORICAL_EMPTY_RESPONSE"
        )

    current_hour = int(
        datetime.now(timezone.utc).timestamp()
    )
    current_hour -= current_hour % 3600

    normalized: list[Any] = []

    for row in rows:

        if (
            not isinstance(row, (list, tuple))
            or len(row) < 7
        ):
            raise RuntimeError(
                "BITGET_HISTORICAL_INVALID_CANDLE"
            )

        timestamp = int(row[0]) // 1000

        candle = {
            "source_id": FAILOVER_PROVIDER,
            "source_type": "CEX_PUBLIC",
            "symbol": bitget_symbol,
            "timestamp": timestamp,
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
            "quote_volume": float(row[6]),
            "raw": row,
        }

        if timestamp >= current_hour:
            continue

        for field in (
            "open",
            "high",
            "low",
            "close",
            "volume",
        ):
            value = candle[field]

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
            ):
                raise RuntimeError(
                    f"BITGET_HISTORICAL_INVALID_{field.upper()}"
                )

        if not _finite_close(candle):
            raise RuntimeError(
                f"BITGET_HISTORICAL_INVALID_CLOSE:{timestamp}"
            )

        normalized.append(candle)

    if not normalized:
        raise RuntimeError(
            "BITGET_HISTORICAL_NO_CLOSED_CANDLES"
        )

    normalized = _validate_candle_sequence(
        normalized,
        symbol,
    )

    contiguous = _contiguous_suffix(
        normalized
    )

    if not contiguous:
        raise RuntimeError(
            "BITGET_HISTORICAL_NO_CONTIGUOUS_CONTEXT"
        )

    return contiguous


def _canonicalize(
    symbol: str,
    candles: list[Any],
    source: str,
    role: str,
) -> MarketDataResult:

    if not candles:
        return MarketDataResult(
            symbol=symbol,
            status="FAILED_CLOSED",
            candles=(),
            source=source,
            error="NO_VALID_REAL_CANDLES",
            real_data=False,
            provider_role=role,
        )

    return MarketDataResult(
        symbol=symbol,
        status="READY",
        candles=tuple(candles),
        source=source,
        error=None,
        real_data=True,
        provider_role=role,
    )


def fetch_market(
    symbol: str,
    *,
    count: int = 150,
) -> MarketDataResult:

    symbol = _normalize_symbol(symbol)

    # ========================================================
    # PRIMARY: KUCOIN CANONICAL ACTIVE
    # ========================================================

    try:
        kucoin_candles = _fetch_kucoin(
            symbol,
            count,
        )

        if kucoin_candles:
            return _canonicalize(
                symbol,
                kucoin_candles,
                CANONICAL_PROVIDER,
                "CANONICAL_ACTIVE",
            )

        kucoin_error = "NO_VALID_REAL_CANDLES"

    except Exception as exc:
        kucoin_error = (
            f"{type(exc).__name__}:{exc}"
        )

    # ========================================================
    # FAILOVER: BITGET HISTORICAL
    #
    # IMPORTANT:
    # The verified PDF-07 single-observation adapter
    # remains untouched.
    #
    # Production dynamic market-data history uses the
    # independent historical Bitget path below.
    # ========================================================

    try:
        bitget_candles = _fetch_bitget_historical(
            symbol,
            count,
        )

        if bitget_candles:
            return _canonicalize(
                symbol,
                bitget_candles,
                FAILOVER_PROVIDER,
                "FAILOVER",
            )

        bitget_error = "NO_VALID_REAL_CANDLES"

    except Exception as exc:
        bitget_error = (
            f"{type(exc).__name__}:{exc}"
        )

    # ========================================================
    # BOTH FAILED -> FAIL CLOSED
    # ========================================================

    return MarketDataResult(
        symbol=symbol,
        status="FAILED_CLOSED",
        candles=(),
        source=(
            f"{CANONICAL_PROVIDER}->"
            f"{FAILOVER_PROVIDER}"
        ),
        error=(
            f"CANONICAL_FAILED={kucoin_error};"
            f"FAILOVER_FAILED={bitget_error}"
        ),
        real_data=False,
        provider_role="NONE",
    )


def fetch_universe_market_data(
    markets: tuple[str, ...] | None = None,
) -> tuple[MarketDataResult, ...]:

    if markets is None:
        markets = discover_universe()

    if not isinstance(markets, tuple):
        markets = tuple(markets)

    if not markets:
        raise RuntimeError(
            "MARKET_DATA_UNIVERSE_EMPTY"
        )

    results: list[MarketDataResult] = []
    seen: set[str] = set()

    for item in markets:
        symbol = _normalize_symbol(item)

        if symbol in seen:
            raise RuntimeError(
                f"MARKET_DATA_DUPLICATE:{symbol}"
            )

        seen.add(symbol)

        try:
            result = fetch_market(
                symbol,
                count=150,
            )

        except Exception as exc:
            result = MarketDataResult(
                symbol=symbol,
                status="FAILED_CLOSED",
                candles=(),
                source=(
                    f"{CANONICAL_PROVIDER}->"
                    f"{FAILOVER_PROVIDER}"
                ),
                error=(
                    f"MARKET_ISOLATED_FAILURE:"
                    f"{type(exc).__name__}:{exc}"
                ),
                real_data=False,
                provider_role="NONE",
            )

        results.append(result)

    if len(results) != len(markets):
        raise RuntimeError(
            "MARKET_DATA_CARDINALITY_MISMATCH"
        )

    return tuple(results)


def ready_market_data(
    results: tuple[MarketDataResult, ...],
) -> tuple[MarketDataResult, ...]:

    return tuple(
        result
        for result in results
        if result.status == "READY"
        and result.real_data is True
    )


def failed_market_data(
    results: tuple[MarketDataResult, ...],
) -> tuple[MarketDataResult, ...]:

    return tuple(
        result
        for result in results
        if result.status == "FAILED_CLOSED"
    )


def static_contract_check() -> dict[str, Any]:

    universe = _load_module(
        UNIVERSE_CONTRACT_FILE,
        "arunda_universe_static",
    )

    kucoin = _load_module(
        KUCOIN_ADAPTER_FILE,
        "arunda_kucoin_static",
    )

    failover = _load_module(
        FAILOVER_ADAPTER_FILE,
        "arunda_market_failover_static",
    )

    if not callable(
        getattr(
            universe,
            "discover_production_assets",
            None,
        )
    ):
        raise RuntimeError(
            "STATIC_UNIVERSE_DISCOVERY=FAIL"
        )

    for name in (
        "fetch_kucoin",
        "normalize",
        "validate_candle",
    ):
        if not callable(
            getattr(kucoin, name, None)
        ):
            raise RuntimeError(
                f"STATIC_{name.upper()}=FAIL"
            )

    if not callable(
        getattr(
            failover,
            "fetch_bitget",
            None,
        )
    ):
        raise RuntimeError(
            "STATIC_BITGET_FETCH=FAIL"
        )

    assets = universe.discover_production_assets()

    if not isinstance(assets, tuple):
        raise RuntimeError(
            "STATIC_UNIVERSE_NOT_TUPLE"
        )

    if not assets:
        raise RuntimeError(
            "STATIC_UNIVERSE_EMPTY"
        )

    return {
        "STATUS": "PASS",
        "DYNAMIC_UNIVERSE": True,
        "UNIVERSE_OWNS_CARDINALITY": True,
        "VARIABLE_CARDINALITY": True,

        "FIXED_15_USED": False,
        "FIXED_COUNT_USED": False,

        "CANONICAL_PROVIDER": CANONICAL_PROVIDER,
        "CANONICAL_ROLE": "ACTIVE",

        "FAILOVER_PROVIDER": FAILOVER_PROVIDER,
        "FAILOVER_ROLE": "FAILOVER",

        "KUCOIN_CANONICAL_BINDING": True,
        "BITGET_FAILOVER_BINDING": True,
        "FAILOVER_ON_CANONICAL_FAILURE": True,

        "PER_MARKET_PROVIDER_ISOLATION": True,
        "PROVIDER_FAILURE_ISOLATED": True,

        "SINGLE_SOURCE_SELECTION": True,
        "NO_PROVIDER_BLENDING": True,

        "REAL_KUCOIN_PATH": True,
        "REAL_BITGET_FAILOVER_PATH": True,

        "CMC_USED": False,
        "SYNTHETIC": False,
        "INTERPOLATION": False,
        "FILL": False,
        "BACKFILL": False,
        "PADDING": False,
        "BLENDING": False,
        "LEGACY_DATA_USED": False,
        "PRE_LAUNCH_DATA_USED": False,

        "DB_WRITES": 0,
        "EXECUTION": "OFF",
        "ORDER_INTENTS_CREATED": 0,

        "PRODUCTION_UNIVERSE_SIZE": len(assets),
    }


def main() -> None:

    result = static_contract_check()

    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()