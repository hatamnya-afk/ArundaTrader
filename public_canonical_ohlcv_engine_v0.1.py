from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


ENGINE = "PUBLIC_CANONICAL_OHLCV_ENGINE_v0.1"

TIMEFRAME = "1h"
TIMEFRAME_SECONDS = 3600
CANONICAL_SYMBOL = "SOL/USDC"
CANONICAL_PRICE_UNIT = "USDC_PER_SOL"

DB_WRITES = 0
CANONICAL_OHLCV_COMMITTED = False
EXECUTION = "DISABLED"


# ---------------------------------------------------------------------
# REAL OBSERVATION INPUT
#
# This is the single REAL observation verified by PDF-04 v0.2.
# No synthetic rows are introduced.
# ---------------------------------------------------------------------

REAL_OBSERVATIONS = [
    {
        "signature": (
            "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr"
        ),
        "slot": 445138167,
        "block_time": 1788807186,
        "pool": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        "input_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "output_mint": "So11111111111111111111111111111111111111112",
        "input_amount": Decimal("1.892593"),
        "output_amount": Decimal("0.018123314"),

        # PDF-04 collector emitted this numeric price as:
        # WSOL per USDC.
        "price": Decimal("0.009575917273285911"),
        "price_unit": "WSOL_PER_USDC",

        # No independently contracted OHLCV volume field exists
        # in this observation.
        "volume": None,

        "instruction": "SWAP_BASE_IN_V2",
        "source_id": "SOLANA_MAINNET_RAYDIUM_AMM_V4",
        "source_type": "DEX_ONCHAIN",

        "provenance": {
            "rpc": "https://api.mainnet-beta.solana.com",
            "slot": 445138167,
            "block_time": 1788807186,
        },
    }
]


def bucket_start_utc(block_time: int) -> int:
    return (int(block_time) // TIMEFRAME_SECONDS) * TIMEFRAME_SECONDS


def normalize_price(observation: dict) -> Decimal:
    unit = observation.get("price_unit")
    raw_price = observation.get("price")

    if raw_price is None:
        raise ValueError("PRICE_MISSING")

    try:
        price = Decimal(str(raw_price))
    except (InvalidOperation, ValueError):
        raise ValueError("INVALID_PRICE")

    if price <= 0:
        raise ValueError("INVALID_PRICE")

    if unit == "USDC_PER_SOL":
        return price

    if unit == "WSOL_PER_USDC":
        return Decimal("1") / price

    raise ValueError("INVALID_PRICE_UNIT")


def validate_observation(observation: dict) -> None:
    required = [
        "signature",
        "slot",
        "block_time",
        "source_id",
        "source_type",
        "price",
        "price_unit",
    ]

    for field in required:
        if field not in observation:
            raise ValueError(f"MISSING_{field.upper()}")

    if observation["block_time"] is None:
        raise ValueError("BLOCK_TIME_MISSING")

    if observation["source_id"] is None:
        raise ValueError("SOURCE_ID_MISSING")

    if observation["price_unit"] not in {
        "USDC_PER_SOL",
        "WSOL_PER_USDC",
    }:
        raise ValueError("INVALID_PRICE_UNIT")


def canonicalize(observations: list[dict]) -> tuple[list[dict], int, int]:
    valid = []
    rejected_invalid_price_unit = 0

    for obs in observations:
        try:
            validate_observation(obs)
            canonical_price = normalize_price(obs)

            row = dict(obs)
            row["canonical_price"] = canonical_price
            row["canonical_price_unit"] = CANONICAL_PRICE_UNIT
            row["hour_bucket"] = bucket_start_utc(
                obs["block_time"]
            )

            valid.append(row)

        except ValueError as exc:
            if str(exc) == "INVALID_PRICE_UNIT":
                rejected_invalid_price_unit += 1
            continue

    return valid, rejected_invalid_price_unit, len(valid)


def build_candles(valid_observations: list[dict]):
    buckets = defaultdict(list)

    for obs in valid_observations:
        buckets[
            (
                obs["source_id"],
                obs["hour_bucket"],
            )
        ].append(obs)

    candles = []
    rejected_incomplete = 0

    for (source_id, bucket), rows in sorted(buckets.items()):
        rows.sort(
            key=lambda x: (
                x["block_time"],
                x["slot"],
                x["signature"],
            )
        )

        # -------------------------------------------------------------
        # FAIL-CLOSED RULE
        #
        # A single observation is NEVER sufficient to create a candle.
        # -------------------------------------------------------------

        if len(rows) < 2:
            rejected_incomplete += 1
            continue

        # Every observation must have explicitly proven real volume.
        if any(row.get("volume") is None for row in rows):
            rejected_incomplete += 1
            continue

        prices = [
            row["canonical_price"]
            for row in rows
        ]

        try:
            volume = sum(
                Decimal(str(row["volume"]))
                for row in rows
            )
        except (InvalidOperation, ValueError, TypeError):
            rejected_incomplete += 1
            continue

        if volume < 0:
            rejected_incomplete += 1
            continue

        candle = {
            "asset": "SOL",
            "symbol": CANONICAL_SYMBOL,
            "timestamp": bucket,
            "timeframe": TIMEFRAME,
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
            "volume": volume,

            "provenance": {
                "source_id": source_id,
                "source_type": rows[0]["source_type"],
                "observations": [
                    {
                        "signature": row["signature"],
                        "slot": row["slot"],
                        "block_time": row["block_time"],
                    }
                    for row in rows
                ],
            },
        }

        candles.append(candle)

    return candles, rejected_incomplete


def main():
    observations_input = len(REAL_OBSERVATIONS)

    valid_observations, rejected_invalid_price_unit, _ = (
        canonicalize(REAL_OBSERVATIONS)
    )

    candles, rejected_incomplete = build_candles(
        valid_observations
    )

    hour_buckets = len(
        set(
            obs["hour_bucket"]
            for obs in valid_observations
        )
    )

    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print(f"EXECUTION={EXECUTION}")
    print("SOURCE=REAL_OBSERVATIONS_ONLY")
    print(f"TIMEFRAME={TIMEFRAME}")
    print(f"SYMBOL={CANONICAL_SYMBOL}")
    print(f"PRICE_UNIT={CANONICAL_PRICE_UNIT}")
    print()

    print("=== RUNTIME VERIFICATION ===")
    print(f"OBSERVATIONS_INPUT={observations_input}")
    print(f"VALID_OBSERVATIONS={len(valid_observations)}")
    print(f"PRICE_UNIT={CANONICAL_PRICE_UNIT}")
    print(f"HOUR_BUCKETS={hour_buckets}")
    print(f"CANONICAL_CANDLES={len(candles)}")
    print(
        f"REJECTED_INCOMPLETE_BUCKETS="
        f"{rejected_incomplete}"
    )
    print(
        f"REJECTED_INVALID_PRICE_UNIT="
        f"{rejected_invalid_price_unit}"
    )

    # In-memory only.
    if candles:
        print()
        print("=== IN-MEMORY CANONICAL CANDLES ===")

        for candle in candles:
            printable = dict(candle)

            for key in (
                "open",
                "high",
                "low",
                "close",
                "volume",
            ):
                printable[key] = str(printable[key])

            print(printable)

    print()
    print(f"DB_WRITES={DB_WRITES}")
    print(
        "CANONICAL_OHLCV_COMMITTED="
        f"{CANONICAL_OHLCV_COMMITTED}"
    )

    # No incomplete candle may escape.
    fail_closed = (
        observations_input > 0
        and (
            rejected_incomplete > 0
            or len(candles) == 0
        )
    )

    print(f"FAIL_CLOSED={fail_closed}")

    if fail_closed:
        print("STATUS=FAIL_CLOSED")
    else:
        print("STATUS=READY_FOR_REVIEW")

    print("NEXT_ACTION=STOP")


if __name__ == "__main__":
    main()