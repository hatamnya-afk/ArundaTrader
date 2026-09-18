from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import math
import sqlite3
import time

import requests


# ============================================================
# ARUNDA MARKET ARM
# PRODUCTION-UNIVERSE-BOUND CONTIGUOUS HISTORY v1.1
#
# ARCHITECTURE:
#
# REAL KUCOIN MARKET DISCOVERY
#        ↓
# PRODUCTION UNIVERSE BINDING
#        ↓
# MarketRecord
#        ↓
# MarketArmInput
#        ↓
# PROVIDER SYMBOL ADAPTER
#        ↓
# REAL KUCOIN OHLCV
#        ↓
# CANONICAL FABRIC
#
# IMPORTANT:
#
# MarketArmInput.symbol is the ACTUAL canonical symbol
# discovered by the Production Universe.
#
# Provider conversion occurs ONLY at the KuCoin boundary:
#
#     BTC/USDT → BTC-USDT
#
# The asset is NEVER used to reconstruct the market symbol.
#
# NO hardcoded asset universe
# NO ranking
# NO CMC
# NO synthetic data
# NO interpolation
# NO fill
# NO backfill
# NO padding
# NO blending
# NO gap crossing
#
# PRODUCTION DB:
# NEVER OPENED
#
# SIGNAL / FUSION / SCORE / DECISION:
# OFF
#
# EXECUTION:
# OFF
# ============================================================


ROOT = Path(__file__).resolve().parent

FABRIC_DB = (
    ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

STORE_MODULE = (
    ROOT
    / "local_canonical_store_v0.1.py"
)

KUCOIN_MODULE = (
    ROOT
    / "public_market_data_kucoin.py"
)

UNIVERSE_BINDING_MODULE = (
    ROOT
    / "production_universe_binding.py"
)

KUCOIN_URL = (
    "https://api.kucoin.com/api/v1/market/candles"
)

TIMEFRAME = "1h"
TIMEFRAME_SECONDS = 3600

TARGET_RUN = 50
HISTORY_BUFFER_CANDLES = 8

LAUNCH_TS = int(
    datetime(
        2026,
        8,
        31,
        tzinfo=timezone.utc,
    ).timestamp()
)

TIMEOUT = 20


# ============================================================
# MARKET ARM INPUT
# ============================================================

@dataclass(frozen=True)
class MarketArmInput:
    asset: str
    symbol: str
    market_identity: str
    exchange: str
    base: str
    quote: str


# ============================================================
# MODULE LOADER
# ============================================================

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path}"
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


# ============================================================
# TIME
# ============================================================

def now_ts() -> int:
    return int(time.time())


def utc_iso(timestamp: int) -> str:
    return datetime.fromtimestamp(
        int(timestamp),
        timezone.utc,
    ).isoformat()


# ============================================================
# NUMERIC
# ============================================================

def finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


# ============================================================
# CLOSED CANDLE
# ============================================================

def is_closed_candle(
    timestamp: int,
    current_time: int,
) -> bool:
    return (
        int(timestamp) + TIMEFRAME_SECONDS
        <= int(current_time)
    )


# ============================================================
# MARKET INPUT VALIDATION
# ============================================================

def validate_market_input(
    market_input: MarketArmInput,
) -> MarketArmInput:

    if not isinstance(
        market_input,
        MarketArmInput,
    ):
        raise RuntimeError(
            "MARKET_ARM_INPUT_INVALID"
        )

    asset = str(
        market_input.asset
    ).strip().upper()

    symbol = str(
        market_input.symbol
    ).strip().upper()

    exchange = str(
        market_input.exchange
    ).strip().upper()

    base = str(
        market_input.base
    ).strip().upper()

    quote = str(
        market_input.quote
    ).strip().upper()

    identity = str(
        market_input.market_identity
    ).strip()

    if not asset:
        raise RuntimeError(
            "MARKET_ARM_INPUT_ASSET_EMPTY"
        )

    if not symbol:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_SYMBOL_EMPTY:{asset}"
        )

    if not exchange:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_EXCHANGE_EMPTY:{asset}"
        )

    if not base:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_BASE_EMPTY:{asset}"
        )

    if not quote:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_QUOTE_EMPTY:{asset}"
        )

    if not identity:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_IDENTITY_EMPTY:{asset}"
        )

    parts = symbol.split("/")

    if len(parts) != 2:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_SYMBOL_INVALID:"
            f"{asset}:{symbol}"
        )

    symbol_base = parts[0].strip().upper()
    symbol_quote = parts[1].strip().upper()

    if not symbol_base or not symbol_quote:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_SYMBOL_INVALID:"
            f"{asset}:{symbol}"
        )

    if symbol_base != base:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_BASE_MISMATCH:"
            f"{asset}:{base}:{symbol_base}"
        )

    if symbol_quote != quote:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_QUOTE_MISMATCH:"
            f"{asset}:{quote}:{symbol_quote}"
        )

    if asset != base:
        raise RuntimeError(
            f"MARKET_ARM_INPUT_ASSET_BASE_MISMATCH:"
            f"{asset}:{base}"
        )

    return MarketArmInput(
        asset=asset,
        symbol=f"{base}/{quote}",
        market_identity=identity,
        exchange=exchange,
        base=base,
        quote=quote,
    )


# ============================================================
# KUCOIN PROVIDER SYMBOL
#
# Canonical:
#     BTC/USDT
#
# KuCoin:
#     BTC-USDT
#
# No asset reconstruction.
# ============================================================

def kucoin_request_symbol(symbol: str) -> str:

    normalized = str(
        symbol
    ).strip().upper()

    parts = normalized.split("/")

    if len(parts) != 2:
        raise RuntimeError(
            f"KUCOIN_SYMBOL_INVALID:{normalized}"
        )

    base = parts[0].strip()
    quote = parts[1].strip()

    if not base or not quote:
        raise RuntimeError(
            f"KUCOIN_SYMBOL_INVALID:{normalized}"
        )

    return f"{base}-{quote}"


# ============================================================
# KUCOIN SOURCE ID
# ============================================================

def kucoin_source_id(symbol: str) -> str:
    return (
        "KUCOIN_SPOT:"
        + kucoin_request_symbol(symbol)
    )


# ============================================================
# REAL KUCOIN DISCOVERY
# ============================================================

def discover_production_universe(
    universe_binding,
):

    try:
        import ccxt
    except Exception as exc:
        raise RuntimeError(
            "CCXT_IMPORT_FAILED"
        ) from exc

    try:
        exchange = ccxt.kucoin()
    except Exception as exc:
        raise RuntimeError(
            "KUCOIN_EXCHANGE_CREATE_FAILED"
        ) from exc

    if not hasattr(
        exchange,
        "load_markets",
    ):
        raise RuntimeError(
            "KUCOIN_MARKET_DISCOVERY_UNAVAILABLE"
        )

    try:
        markets = exchange.load_markets()
    except Exception as exc:
        raise RuntimeError(
            "KUCOIN_MARKET_DISCOVERY_FAILED"
        ) from exc

    if not isinstance(markets, dict):
        raise RuntimeError(
            "KUCOIN_MARKET_MAP_INVALID"
        )

    if not hasattr(
        universe_binding,
        "build_production_universe",
    ):
        raise RuntimeError(
            "UNIVERSE_BINDING_BUILD_MISSING"
        )

    if not hasattr(
        universe_binding,
        "eligible_production_universe",
    ):
        raise RuntimeError(
            "UNIVERSE_BINDING_ELIGIBILITY_MISSING"
        )

    records = (
        universe_binding.build_production_universe(
            markets=markets,
            exchange="KUCOIN",
            source="KUCOIN_CCXT_MARKET_DISCOVERY",
        )
    )

    if not isinstance(records, list):
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_OUTPUT_INVALID"
        )

    if not records:
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_EMPTY"
        )

    eligible = (
        universe_binding.eligible_production_universe(
            markets=markets,
            exchange="KUCOIN",
            source="KUCOIN_CCXT_MARKET_DISCOVERY",
        )
    )

    if not isinstance(eligible, list):
        raise RuntimeError(
            "ELIGIBLE_PRODUCTION_UNIVERSE_OUTPUT_INVALID"
        )

    if not eligible:
        raise RuntimeError(
            "ELIGIBLE_PRODUCTION_UNIVERSE_EMPTY"
        )

    return eligible


# ============================================================
# MarketRecord → MarketArmInput
#
# ONE STEP.
#
# No asset/symbol reconstruction.
# ============================================================

def market_record_to_arm_input(
    record,
) -> MarketArmInput:

    required = (
        "asset",
        "symbol",
        "market_identity",
        "exchange",
        "base",
        "quote",
    )

    for field in required:
        if not hasattr(record, field):
            raise RuntimeError(
                f"MARKET_RECORD_FIELD_MISSING:{field}"
            )

    eligibility = getattr(
        record,
        "eligibility",
        False,
    )

    if eligibility is not True:
        raise RuntimeError(
            "INELIGIBLE_MARKET_RECORD:"
            f"{getattr(record, 'symbol', '')}"
        )

    arm_input = MarketArmInput(
        asset=str(record.asset),
        symbol=str(record.symbol),
        market_identity=str(
            record.market_identity
        ),
        exchange=str(record.exchange),
        base=str(record.base),
        quote=str(record.quote),
    )

    return validate_market_input(
        arm_input
    )


# ============================================================
# BUILD MARKET ARM INPUTS
# ============================================================

def build_market_arm_inputs(
    universe_binding,
):

    records = discover_production_universe(
        universe_binding
    )

    inputs = []
    identities = set()

    for record in records:

        market_input = (
            market_record_to_arm_input(
                record
            )
        )

        identity = (
            market_input.market_identity
        )

        if identity in identities:
            raise RuntimeError(
                f"DUPLICATE_MARKET_IDENTITY:"
                f"{identity}"
            )

        identities.add(identity)

        inputs.append(
            market_input
        )

    if not inputs:
        raise RuntimeError(
            "MARKET_ARM_INPUTS_EMPTY"
        )

    return inputs


# ============================================================
# FABRIC READ
# ============================================================

def load_rows(
    conn,
    market_input: MarketArmInput,
):

    market_input = validate_market_input(
        market_input
    )

    source_id = kucoin_source_id(
        market_input.symbol
    )

    return conn.execute(
        """
        SELECT
            asset,
            symbol,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_id,
            source_type,
            source_timestamp,
            retrieved_at,
            observation_count,
            observation_signatures,
            observation_slots,
            pool,
            raydium_instruction,
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        WHERE UPPER(asset)=?
          AND symbol=?
          AND source_id=?
          AND source_type='CEX_PUBLIC_API'
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (
            market_input.asset,
            market_input.symbol,
            source_id,
            TIMEFRAME,
            LAUNCH_TS,
        ),
    ).fetchall()


# ============================================================
# CURRENT CLOSED CONTIGUOUS RUN
# ============================================================

def current_contiguous_run(
    rows,
    current_time: int,
):

    if not rows:
        return 0, None, None

    timestamps = sorted(
        {
            int(row[2])
            for row in rows
            if is_closed_candle(
                int(row[2]),
                current_time,
            )
            and int(row[2]) >= LAUNCH_TS
        }
    )

    if not timestamps:
        return 0, None, None

    run = 1

    for index in range(
        len(timestamps) - 1,
        0,
        -1,
    ):

        delta = (
            timestamps[index]
            - timestamps[index - 1]
        )

        if delta == TIMEFRAME_SECONDS:
            run += 1
        else:
            break

    return (
        run,
        timestamps[-run],
        timestamps[-1],
    )


# ============================================================
# KUCOIN HISTORICAL FETCH
# ============================================================

def fetch_kucoin_history(
    market_input: MarketArmInput,
    start_ts: int,
    end_ts: int,
    current_time: int,
):

    market_input = validate_market_input(
        market_input
    )

    request_symbol = kucoin_request_symbol(
        market_input.symbol
    )

    response = requests.get(
        KUCOIN_URL,
        params={
            "symbol": request_symbol,
            "type": "1hour",
            "startAt": int(start_ts),
            "endAt": int(end_ts),
        },
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"KUCOIN_RESPONSE_INVALID:"
            f"{market_input.symbol}"
        )

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR:"
            f"{market_input.symbol}:"
            f"{payload.get('msg')}"
        )

    data = payload.get("data")

    if not isinstance(data, list):
        raise RuntimeError(
            f"KUCOIN_DATA_INVALID:"
            f"{market_input.symbol}"
        )

    result = []

    for raw in data:

        if not isinstance(raw, list):
            continue

        if len(raw) < 6:
            continue

        try:
            timestamp = int(float(raw[0]))
            open_price = float(raw[1])
            close_price = float(raw[2])
            high_price = float(raw[3])
            low_price = float(raw[4])
            volume = float(raw[5])
        except Exception:
            continue

        if not is_closed_candle(
            timestamp,
            current_time,
        ):
            continue

        if timestamp < LAUNCH_TS:
            continue

        if timestamp < int(start_ts):
            continue

        if timestamp > int(end_ts):
            continue

        if timestamp % TIMEFRAME_SECONDS != 0:
            continue

        if not all(
            finite(value)
            for value in (
                open_price,
                close_price,
                high_price,
                low_price,
                volume,
            )
        ):
            continue

        if open_price <= 0:
            continue

        if close_price <= 0:
            continue

        if high_price <= 0:
            continue

        if low_price <= 0:
            continue

        if volume < 0:
            continue

        if high_price < max(
            open_price,
            close_price,
        ):
            continue

        if low_price > min(
            open_price,
            close_price,
        ):
            continue

        if low_price > high_price:
            continue

        result.append(raw)

    unique = {}

    for raw in result:

        timestamp = int(
            float(raw[0])
        )

        if timestamp not in unique:
            unique[timestamp] = raw

    return [
        unique[timestamp]
        for timestamp in sorted(unique)
    ]


# ============================================================
# BACKWARD CONTIGUOUS SEQUENCE
# ============================================================

def build_backward_sequence(
    existing_timestamps,
    candidates,
    latest_closed,
    target_run,
    current_time,
):

    by_timestamp = {}

    for timestamp in existing_timestamps:

        ts = int(timestamp)

        if not is_closed_candle(
            ts,
            current_time,
        ):
            continue

        if ts < LAUNCH_TS:
            continue

        by_timestamp[ts] = None

    for raw in candidates:

        timestamp = int(
            float(raw[0])
        )

        if not is_closed_candle(
            timestamp,
            current_time,
        ):
            continue

        if timestamp < LAUNCH_TS:
            continue

        by_timestamp[timestamp] = raw

    selected = []
    missing = []

    timestamp = int(latest_closed)

    while len(selected) < target_run:

        if timestamp not in by_timestamp:

            missing.append(timestamp)
            break

        selected.append(
            (
                timestamp,
                by_timestamp[timestamp],
            )
        )

        timestamp -= TIMEFRAME_SECONDS

    return selected, missing


# ============================================================
# HARD CANONICAL IDENTITY
# ============================================================

def validate_identity(
    normalized,
    market_input: MarketArmInput,
):

    market_input = validate_market_input(
        market_input
    )

    expected_asset = market_input.asset
    expected_symbol = market_input.symbol
    expected_source = kucoin_source_id(
        expected_symbol
    )

    actual_asset = str(
        normalized.get(
            "asset",
            "",
        )
    ).strip().upper()

    actual_symbol = str(
        normalized.get(
            "symbol",
            "",
        )
    ).strip().upper()

    actual_source = str(
        normalized.get(
            "source_id",
            "",
        )
    ).strip().upper()

    if actual_asset != expected_asset:
        raise RuntimeError(
            f"IDENTITY_ASSET_MISMATCH:"
            f"{expected_asset}:"
            f"actual={actual_asset}"
        )

    if actual_symbol != expected_symbol:
        raise RuntimeError(
            f"IDENTITY_SYMBOL_MISMATCH:"
            f"{expected_symbol}:"
            f"actual={actual_symbol}"
        )

    if actual_source != expected_source.upper():
        raise RuntimeError(
            f"IDENTITY_SOURCE_MISMATCH:"
            f"{expected_source}:"
            f"actual={actual_source}"
        )

    if normalized.get(
        "source_type"
    ) != "CEX_PUBLIC_API":
        raise RuntimeError(
            f"SOURCE_TYPE_MISMATCH:"
            f"{expected_symbol}"
        )

    if normalized.get(
        "timeframe"
    ) != TIMEFRAME:
        raise RuntimeError(
            f"TIMEFRAME_MISMATCH:"
            f"{expected_symbol}"
        )

    timestamp = int(
        normalized["timestamp"]
    )

    if timestamp < LAUNCH_TS:
        raise RuntimeError(
            f"LAUNCH_BOUNDARY_VIOLATION:"
            f"{expected_symbol}"
        )


# ============================================================
# PROCESS ONE MARKET
# ============================================================

def process_market(
    conn,
    store,
    kucoin,
    market_input: MarketArmInput,
):

    market_input = validate_market_input(
        market_input
    )

    current_time = now_ts()

    rows = load_rows(
        conn,
        market_input,
    )

    existing_timestamps = {
        int(row[2])
        for row in rows
        if is_closed_candle(
            int(row[2]),
            current_time,
        )
        and int(row[2]) >= LAUNCH_TS
    }

    run, run_start, latest_closed = (
        current_contiguous_run(
            rows,
            current_time,
        )
    )

    # --------------------------------------------------------
    # If Fabric already has a contiguous run, use its latest
    # closed candle as context.
    # --------------------------------------------------------

    if latest_closed is None:

        # No existing Fabric candle for this market.
        #
        # Obtain the latest REAL closed candle directly from
        # KuCoin. This does NOT synthesize context and does
        # NOT reconstruct the symbol from asset.

        discovery_end = current_time

        discovery_start = (
            max(
                LAUNCH_TS,
                discovery_end
                - (
                    TARGET_RUN
                    + HISTORY_BUFFER_CANDLES
                )
                * TIMEFRAME_SECONDS,
            )
        )

        bootstrap_candidates = (
            fetch_kucoin_history(
                market_input,
                discovery_start,
                discovery_end,
                current_time,
            )
        )

        if not bootstrap_candidates:
            raise RuntimeError(
                f"NO_CLOSED_CONTEXT:"
                f"{market_input.symbol}"
            )

        latest_closed = int(
            max(
                int(float(raw[0]))
                for raw in bootstrap_candidates
            )
        )

        candidates = bootstrap_candidates

    else:

        request_end = latest_closed

        request_start = (
            latest_closed
            - (
                TARGET_RUN
                + HISTORY_BUFFER_CANDLES
            )
            * TIMEFRAME_SECONDS
        )

        if request_start < LAUNCH_TS:
            request_start = LAUNCH_TS

        candidates = fetch_kucoin_history(
            market_input,
            request_start,
            request_end,
            current_time,
        )

    if run >= TARGET_RUN:

        print(
            f"{market_input.asset} "
            f"{market_input.symbol}: "
            f"RUN={run} "
            f"TARGET_REACHED=True"
        )

        return (
            market_input,
            run,
            0,
        )

    request_end = latest_closed

    request_start = (
        latest_closed
        - (
            TARGET_RUN
            + HISTORY_BUFFER_CANDLES
        )
        * TIMEFRAME_SECONDS
    )

    if request_start < LAUNCH_TS:
        request_start = LAUNCH_TS

    print()

    print(
        f"{market_input.asset} "
        f"{market_input.symbol}: "
        f"RUN={run} "
        f"TARGET_RUN={TARGET_RUN} "
        f"LATEST_CLOSED="
        f"{utc_iso(latest_closed)}"
    )

    print(
        f"{market_input.symbol}: "
        f"BACKWARD_REQUEST="
        f"{utc_iso(request_start)}"
        f" -> "
        f"{utc_iso(request_end)}"
    )

    # --------------------------------------------------------
    # For existing markets, refresh candidates using the
    # exact requested backward window.
    # --------------------------------------------------------

    candidates = fetch_kucoin_history(
        market_input,
        request_start,
        request_end,
        current_time,
    )

    selected, missing = (
        build_backward_sequence(
            existing_timestamps,
            candidates,
            latest_closed,
            TARGET_RUN,
            current_time,
        )
    )

    if len(selected) < TARGET_RUN:

        if missing:

            missing_ts = missing[0]

            print(
                f"{market_input.symbol}: "
                f"GAP_OR_UNAVAILABLE="
                f"{missing_ts} "
                f"{utc_iso(missing_ts)}"
            )

        else:

            print(
                f"{market_input.symbol}: "
                f"INSUFFICIENT_CLOSED_HISTORY"
            )

        return (
            market_input,
            run,
            0,
        )

    # --------------------------------------------------------
    # HARD BACKWARD CONTINUITY
    # --------------------------------------------------------

    expected = latest_closed

    for timestamp, raw in selected:

        if timestamp != expected:
            raise RuntimeError(
                f"BACKWARD_CONTINUITY_FAILURE:"
                f"{market_input.symbol}:"
                f"expected={expected}:"
                f"actual={timestamp}"
            )

        if not is_closed_candle(
            timestamp,
            current_time,
        ):
            raise RuntimeError(
                f"OPEN_OR_FUTURE_CANDLE:"
                f"{market_input.symbol}:"
                f"{timestamp}"
            )

        if timestamp < LAUNCH_TS:
            raise RuntimeError(
                f"LAUNCH_BOUNDARY_VIOLATION:"
                f"{market_input.symbol}:"
                f"{timestamp}"
            )

        expected -= TIMEFRAME_SECONDS

    new_sequence = [
        (timestamp, raw)
        for timestamp, raw in selected
        if raw is not None
    ]

    inserted = 0

    for timestamp, raw in reversed(
        new_sequence
    ):

        if not is_closed_candle(
            timestamp,
            now_ts(),
        ):
            raise RuntimeError(
                f"OPEN_CANDLE_REJECTED:"
                f"{market_input.symbol}:"
                f"{timestamp}"
            )

        # ----------------------------------------------------
        # PROVIDER BOUNDARY
        #
        # Canonical:
        #     BTC/USDT
        #
        # KuCoin:
        #     BTC-USDT
        #
        # ONLY provider-specific conversion.
        # ----------------------------------------------------

        provider_symbol = (
            kucoin_request_symbol(
                market_input.symbol
            )
        )

        normalized = kucoin.normalize(
            market_input.asset,
            provider_symbol,
            raw,
            datetime.now(
                timezone.utc
            ).isoformat(),
        )

        validation_result = (
            kucoin.validate_candle(
                normalized
            )
        )

        # Existing adapter is expected to raise on
        # validation failure and return None on success.

        if validation_result is False:
            raise RuntimeError(
                f"KUCOIN_CANONICAL_VALIDATION_FAILED:"
                f"{market_input.symbol}:"
                f"{timestamp}"
            )

        validate_identity(
            normalized,
            market_input,
        )

        if int(
            normalized["timestamp"]
        ) != timestamp:
            raise RuntimeError(
                f"CANONICAL_TIMESTAMP_MISMATCH:"
                f"{market_input.symbol}:"
                f"expected={timestamp}:"
                f"actual={normalized['timestamp']}"
            )

        ok = store.insert_candle(
            conn,
            normalized,
        )

        if ok:

            inserted += 1

            print(
                f"  INSERTED="
                f"{market_input.asset} "
                f"SYMBOL={market_input.symbol} "
                f"TIMESTAMP={timestamp} "
                f"UTC={utc_iso(timestamp)}"
            )

    verify_time = now_ts()

    verify_rows = load_rows(
        conn,
        market_input,
    )

    (
        verify_run,
        verify_start,
        verify_latest,
    ) = current_contiguous_run(
        verify_rows,
        verify_time,
    )

    print(
        f"  RESULT="
        f"{market_input.symbol} "
        f"RUN={verify_run} "
        f"INSERTED={inserted} "
        f"LATEST_CLOSED={verify_latest}"
    )

    if verify_run < run:
        raise RuntimeError(
            f"RUN_REGRESSION:"
            f"{market_input.symbol}"
        )

    return (
        market_input,
        verify_run,
        inserted,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print("=" * 100)

    print(
        "ARUNDA MARKET ARM "
        "PRODUCTION-UNIVERSE-BOUND "
        "CONTIGUOUS HISTORY v1.1"
    )

    print("=" * 100)

    print(
        "INPUT_SOURCE="
        "PRODUCTION_UNIVERSE_BINDING"
    )

    print(
        "DISCOVERY_PROVIDER=KUCOIN"
    )

    print(
        "DYNAMIC_UNIVERSE=True"
    )

    print(
        "HARDCODED_ASSETS=False"
    )

    print(
        "CMC=False"
    )

    print(
        "RANKING=False"
    )

    print(
        "SYMBOL_RECONSTRUCTION_FROM_ASSET=False"
    )

    print(
        "DIRECT_MARKET_SYMBOL_CONSUMPTION=True"
    )

    print(
        "PROVIDER_SYMBOL_ADAPTER=True"
    )

    print(
        "TARGET_RUN=50"
    )

    print(
        "TIMEFRAME=1h"
    )

    print(
        "REAL_DATA_ONLY=True"
    )

    print(
        "SYNTHETIC=False"
    )

    print(
        "INTERPOLATION=False"
    )

    print(
        "FILL=False"
    )

    print(
        "BACKFILL=False"
    )

    print(
        "PADDING=False"
    )

    print(
        "BLENDING=False"
    )

    print(
        "PRODUCTION_DB_TOUCHED=False"
    )

    print(
        "SIGNAL_CHAIN_EXECUTED=False"
    )

    print(
        "FUSION_EXECUTED=False"
    )

    print(
        "SCORE=OFF"
    )

    print(
        "DECISION=OFF"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print("=" * 100)

    # ========================================================
    # FILE CHECKS
    # ========================================================

    # Fabric DB is a runtime-created local canonical store.
    # It is intentionally allowed to be absent on first bootstrap.
    # The approved store module owns schema/storage initialization.
    if not STORE_MODULE.exists():
        raise RuntimeError(
            "STORE_MODULE_NOT_FOUND"
        )

    if not KUCOIN_MODULE.exists():
        raise RuntimeError(
            "STORE_MODULE_NOT_FOUND"
        )

    if not KUCOIN_MODULE.exists():
        raise RuntimeError(
            "KUCOIN_ADAPTER_NOT_FOUND"
        )

    if not UNIVERSE_BINDING_MODULE.exists():
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_BINDING_NOT_FOUND"
        )

    # ========================================================
    # LOAD APPROVED MODULES
    # ========================================================

    store = load_module(
        STORE_MODULE,
        "canonical_store_v1_1",
    )

    kucoin = load_module(
        KUCOIN_MODULE,
        "public_market_data_kucoin_v1_1",
    )

    universe_binding = load_module(
        UNIVERSE_BINDING_MODULE,
        "production_universe_binding_v1_1",
    )

    # ========================================================
    # CONTRACT CHECKS
    # ========================================================

    if not hasattr(
        store,
        "insert_candle",
    ):
        raise RuntimeError(
            "STORE_API_INSERT_CANDLE_MISSING"
        )

    if not hasattr(
        kucoin,
        "normalize",
    ):
        raise RuntimeError(
            "KUCOIN_API_NORMALIZE_MISSING"
        )

    if not hasattr(
        kucoin,
        "validate_candle",
    ):
        raise RuntimeError(
            "KUCOIN_API_VALIDATE_CANDLE_MISSING"
        )

    if not hasattr(
        universe_binding,
        "build_production_universe",
    ):
        raise RuntimeError(
            "UNIVERSE_BINDING_BUILD_MISSING"
        )

    if not hasattr(
        universe_binding,
        "eligible_production_universe",
    ):
        raise RuntimeError(
            "UNIVERSE_BINDING_ELIGIBILITY_MISSING"
        )

    print(
        "UNIVERSE_BINDING=PASS"
    )

    print(
        "KUCOIN_BINDING=PASS"
    )

    # ========================================================
    # FABRIC SCHEMA BOOTSTRAP
    #
    # Initialize ONLY the approved canonical Fabric schema.
    # Do NOT execute store.main() and do NOT insert fixture data.
    # Production DB remains untouched.
    # ========================================================

    if not hasattr(store, "CREATE_SQL"):
        raise RuntimeError(
            "STORE_SCHEMA_CREATE_SQL_MISSING"
        )

    FABRIC_DB.parent.mkdir(parents=True, exist_ok=True)

    schema_conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    try:
        schema_conn.execute(store.CREATE_SQL)
        schema_conn.commit()
    finally:
        schema_conn.close()

    print(
        "FABRIC_SCHEMA_BOOTSTRAP=PASS"
    )

    # ========================================================
    # REAL PRODUCTION UNIVERSE
    #
    # Real market discovery.
    #
    # No production DB.
    # No signal chain.
    # No execution.
    # ========================================================

    market_inputs = (
        build_market_arm_inputs(
            universe_binding
        )
    )

    print(
        f"PRODUCTION_UNIVERSE_COUNT="
        f"{len(market_inputs)}"
    )

    # ========================================================
    # FABRIC ONLY
    # ========================================================

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    summary = []

    try:

        for market_input in market_inputs:

            result = process_market(
                conn,
                store,
                kucoin,
                market_input,
            )

            summary.append(result)

        # ====================================================
        # FINAL VALIDATION
        # ====================================================

        print()
        print("=" * 100)
        print("FINAL VALIDATION")
        print("=" * 100)

        all_ready = True

        for (
            market_input,
            run,
            inserted,
        ) in summary:

            if run >= TARGET_RUN:
                status = "READY"
            else:
                status = "PARTIAL"
                all_ready = False

            print(
                f"{market_input.asset} "
                f"{market_input.symbol}: "
                f"RUN={run} "
                f"INSERTED={inserted} "
                f"STATUS={status}"
            )

        print("=" * 100)

        if all_ready:

            print(
                "MARKET_ARM_READY=True"
            )

            print(
                "CONTIGUOUS_50_READY="
                f"{len(summary)}/{len(summary)}"
            )

            print(
                "STATUS=TARGET_RUN_50_REACHED"
            )

        else:

            print(
                "MARKET_ARM_READY=False"
            )

            print(
                "STATUS=BACKWARD_ACCUMULATION_CONTINUES"
            )

        print(
            "PRODUCTION_DB_TOUCHED=False"
        )

        print(
            "SIGNAL_CHAIN_EXECUTED=False"
        )

        print(
            "FUSION_EXECUTED=False"
        )

        print(
            "SCORE=OFF"
        )

        print(
            "DECISION=OFF"
        )

        print(
            "ORDER_INTENTS=0"
        )

        print(
            "EXECUTION=OFF"
        )

        print(
            "SYNTHETIC=False"
        )

        print(
            "INTERPOLATION=False"
        )

        print(
            "FILL=False"
        )

        print(
            "BACKFILL=False"
        )

        print(
            "PADDING=False"
        )

        print(
            "BLENDING=False"
        )

        print(
            "OPEN_LAST_CANDLE_EXCLUDED=True"
        )

        print(
            "FAIL_CLOSED=True"
        )

        return 0

    finally:

        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())