from pathlib import Path

# ============================================================
# PATCH 1 — EXISTING KUCOIN ADAPTER
# Extend fetch_kucoin() to return real historical 1h candles.
# ============================================================

adapter = Path("public_market_data_kucoin.py")
text = adapter.read_text(encoding="utf-8")

start = text.index("def fetch_kucoin(")
end = text.index("\ndef select_latest_closed_bar", start)

new_fetch = r'''def fetch_kucoin(
    symbol: str,
    count: int = 50,
) -> list[list]:

    """
    Canonical KuCoin production fetch.

    REAL DATA ONLY.
    1h candles.
    No synthetic data.
    No interpolation.
    No fill.
    No backfill.
    """

    if not isinstance(count, int) or count < 2:
        raise ValueError("INVALID_KUCOIN_CANDLE_COUNT")

    now = int(
        datetime.now(timezone.utc).timestamp()
    )

    # Request enough real history for the requested
    # number of closed 1h candles.
    end_at = now
    start_at = end_at - (
        int(count) + 2
    ) * TIMEFRAME_SECONDS

    response = requests.get(
        API_URL,
        params={
            "symbol": symbol,
            "type": "1hour",
            "startAt": start_at,
            "endAt": end_at,
        },
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR:{payload.get('code')}"
        )

    data = payload.get("data")

    if not isinstance(data, list):
        raise RuntimeError(
            "INVALID_KUCOIN_DATA"
        )

    return data
'''

adapter.write_text(
    text[:start] +
    new_fetch +
    text[end:],
    encoding="utf-8",
)

print("PATCH 1 PASS: public_market_data_kucoin.py")


# ============================================================
# PATCH 2 — MARKET DATA ENGINE
# Replace CMC fetch with canonical KuCoin adapter.
# ============================================================

engine = Path("market_data_engine.py")
text = engine.read_text(encoding="utf-8")

start = text.index("def fetch_real_1h_ohlcv(")
end = text.index("\ndef calculate_real_atr14_series", start)

new_fetch_engine = r'''def fetch_real_1h_ohlcv(
    symbol,
    count=OHLCV_LOOKBACK,
):
    """
    Production OHLCV source.

    Provider:
        Existing canonical KuCoin adapter.

    Rules:
        REAL DATA ONLY
        1h ONLY
        CLOSED CANDLES ONLY
        NO SYNTHETIC
        NO INTERPOLATION
        NO FILL
        NO BACKFILL
        NO CMC
    """

    import importlib.util

    adapter_path = (
        Path(__file__).resolve().parent
        / "public_market_data_kucoin.py"
    )

    if not adapter_path.exists():
        raise RuntimeError(
            "KUCOIN_ADAPTER_NOT_FOUND"
        )

    spec = importlib.util.spec_from_file_location(
        "arunda_public_market_data_kucoin",
        adapter_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "KUCOIN_ADAPTER_LOAD_FAILED"
        )

    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)

    required = (
        "fetch_kucoin",
        "normalize",
        "validate_candle",
    )

    for name in required:
        if not hasattr(adapter, name):
            raise RuntimeError(
                f"KUCOIN_ADAPTER_MISSING:{name}"
            )

    # SYMBOLS in this engine are canonical asset names.
    # Existing adapter owns asset -> KuCoin symbol mapping.
    assets = getattr(
        adapter,
        "ASSETS",
        {},
    )

    if symbol not in assets:
        raise RuntimeError(
            f"KUCOIN_ASSET_MAPPING_MISSING:{symbol}"
        )

    provider_symbol = assets[symbol]

    retrieved_at = (
        datetime.now(timezone.utc).isoformat()
    )

    raw_bars = adapter.fetch_kucoin(
        provider_symbol,
        count=int(count),
    )

    if not isinstance(raw_bars, list):
        raise RuntimeError(
            f"{symbol}: INVALID_KUCOIN_BARS"
        )

    candles = []

    for bar in raw_bars:

        if not isinstance(bar, list):
            continue

        if len(bar) < 6:
            continue

        try:
            candle = adapter.normalize(
                symbol,
                provider_symbol,
                bar,
                retrieved_at,
            )

            adapter.validate_candle(
                candle
            )

        except (
            ValueError,
            TypeError,
        ):
            continue

        # Production engine internal shape.
        internal = {
            "asset": symbol,
            "timestamp": int(
                candle["timestamp"]
            ),
            "open": float(
                candle["open"]
            ),
            "high": float(
                candle["high"]
            ),
            "low": float(
                candle["low"]
            ),
            "close": float(
                candle["close"]
            ),
            "volume": float(
                candle["volume"]
            ),
            "timeframe": "1h",

            # Preserve real provenance.
            "source": candle[
                "source_id"
            ],
            "source_id": candle[
                "source_id"
            ],
            "source_type": candle[
                "source_type"
            ],
            "source_timestamp": candle[
                "source_timestamp"
            ],
            "retrieved_at": candle[
                "retrieved_at"
            ],
        }

        if not validate_real_ohlcv_candle(
            internal
        ):
            continue

        candles.append(
            internal
        )

    if not candles:
        raise RuntimeError(
            f"{symbol}: NO_VALID_KUCOIN_1H_OHLCV"
        )

    # Oldest -> newest.
    candles.sort(
        key=lambda row: row["timestamp"]
    )

    # Remove duplicate timestamps.
    unique = {}
    for candle in candles:
        unique[
            candle["timestamp"]
        ] = candle

    candles = list(
        sorted(
            unique.values(),
            key=lambda row: row["timestamp"],
        )
    )

    # Explicitly exclude current/open candle.
    now = int(
        datetime.now(timezone.utc).timestamp()
    )

    current_hour = (
        now
        - (
            now % 3600
        )
    )

    candles = [
        candle
        for candle in candles
        if candle["timestamp"]
        < current_hour
    ]

    if len(candles) < ATR_PERIOD:
        raise RuntimeError(
            f"{symbol}: INSUFFICIENT_REAL_1H_CONTEXT:"
            f"{len(candles)}<{ATR_PERIOD}"
        )

    # Hard continuity validation.
    for index in range(
        1,
        len(candles),
    ):
        previous = candles[
            index - 1
        ]["timestamp"]

        current = candles[
            index
        ]["timestamp"]

        if (
            current - previous
            != 3600
        ):
            raise RuntimeError(
                f"{symbol}: "
                "NON_CONTIGUOUS_REAL_1H_CONTEXT"
            )

    return candles
'''

engine.write_text(
    text[:start] +
    new_fetch_engine +
    text[end:],
    encoding="utf-8",
)

# Replace only production CMC identity strings
text = engine.read_text(encoding="utf-8")

text = text.replace(
    "MARKET_DATA_CMC_OHLCV_1H_v1.0",
    "MARKET_DATA_KUCOIN_OHLCV_1H_v1.1",
)

text = text.replace(
    "genuine CMC 1h OHLCV",
    "genuine KuCoin 1h OHLCV",
)

engine.write_text(
    text,
    encoding="utf-8",
)

print("PATCH 2 PASS: market_data_engine.py")
print("CMC PRODUCTION FETCH REMOVED")
print("KUCOIN CANONICAL ADAPTER BOUND")
