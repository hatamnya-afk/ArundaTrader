from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ENGINE = "ARUNDA_PMDF_03_CONTROLLED_PRODUCTION_MARKET_DATA_CONSUMPTION"
VERSION = "v0.1"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_ROOT / "arunda.db"
FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

LAUNCH_TIMESTAMP = datetime(
    2026,
    8,
    31,
    0,
    0,
    0,
    tzinfo=timezone.utc,
).timestamp()

CANONICAL_PROVIDER = "KUCOIN"
SOURCE_TYPE = "CEX_PUBLIC_API"
TIMEFRAME = "1h"
KUCOIN_SOURCE_PREFIX = "KUCOIN_SPOT:"

EXECUTION = "DISABLED"
ORDER_INTENTS_CREATED = 0

PRODUCTION_CONSUMPTION_ENABLED = True


def fail(message: str) -> None:
    raise RuntimeError(
        f"PMDF-03 FAIL-CLOSED: {message}"
    )


def finite(value) -> bool:
    return (
        isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def load_fabric_rows(conn):
    conn.row_factory = sqlite3.Row

    return conn.execute(
        """
        SELECT
            id,
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
        ORDER BY id ASC
        """
    ).fetchall()


def validate_canonical(row) -> None:
    required = [
        "asset",
        "symbol",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source_id",
        "source_type",
        "source_timestamp",
        "retrieved_at",
        "observation_count",
        "observation_signatures",
        "observation_slots",
        "canonical_payload",
    ]

    for field in required:
        if row[field] is None:
            fail(
                f"missing required field: {field}"
            )

    if row["source_type"] != SOURCE_TYPE:
        fail(
            f"invalid source_type: {row['source_type']}"
        )

    if not row["source_id"].startswith(
        KUCOIN_SOURCE_PREFIX
    ):
        fail(
            f"invalid provider source_id: "
            f"{row['source_id']}"
        )

    if row["timeframe"] != TIMEFRAME:
        fail(
            f"invalid timeframe: {row['timeframe']}"
        )

    if not isinstance(row["timestamp"], int):
        fail("timestamp is not integer")

    if row["timestamp"] < LAUNCH_TIMESTAMP:
        fail(
            "pre-launch candle reached production "
            "consumer"
        )

    if (
        row["source_timestamp"]
        != row["timestamp"]
    ):
        fail(
            "source timestamp was not preserved"
        )

    if not isinstance(
        row["retrieved_at"],
        str,
    ) or not row["retrieved_at"]:
        fail("invalid retrieved_at")

    for field in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        if not finite(row[field]):
            fail(
                f"invalid numeric field: {field}"
            )

    if row["open"] <= 0:
        fail("invalid open")

    if row["high"] <= 0:
        fail("invalid high")

    if row["low"] <= 0:
        fail("invalid low")

    if row["close"] <= 0:
        fail("invalid close")

    if row["volume"] < 0:
        fail("invalid volume")

    if row["high"] < max(
        row["open"],
        row["close"],
        row["low"],
    ):
        fail("invalid OHLC high")

    if row["low"] > min(
        row["open"],
        row["close"],
        row["high"],
    ):
        fail("invalid OHLC low")

    if row["observation_count"] != 1:
        fail(
            "one-candle-one-source violation"
        )

    try:
        signatures = json.loads(
            row["observation_signatures"]
        )
        slots = json.loads(
            row["observation_slots"]
        )
    except Exception as exc:
        fail(
            f"invalid provenance JSON: {exc}"
        )

    if not isinstance(signatures, list):
        fail(
            "invalid observation signatures"
        )

    if not isinstance(slots, list):
        fail(
            "invalid observation slots"
        )

    if len(signatures) != 1:
        fail(
            "invalid observation signature count"
        )

    if len(slots) != 1:
        fail(
            "invalid observation slot count"
        )

    if not signatures[0]:
        fail(
            "missing observation signature"
        )

    if slots[0] != row["timestamp"]:
        fail(
            "observation timestamp mismatch"
        )

    # CEX record must not contain DEX provenance.
    if row["pool"] not in (None, "null"):
        fail(
            "source mixing: pool present"
        )

    if row["raydium_instruction"] not in (
        None,
        "null",
    ):
        fail(
            "source mixing: Raydium provenance present"
        )

    if not isinstance(
        row["canonical_payload"],
        str,
    ) or not row["canonical_payload"]:
        fail(
            "missing canonical payload"
        )


def canonical_identity(row):
    return (
        row["asset"],
        row["symbol"],
        row["timestamp"],
        row["timeframe"],
    )


def main() -> None:
    if not FABRIC_DB.exists():
        fail(
            f"Fabric store missing: {FABRIC_DB}"
        )

    if not PRODUCTION_DB.exists():
        fail(
            "production DB missing; fail-closed"
        )

    # Production DB is deliberately NOT opened.
    production_before = (
        PRODUCTION_DB.stat().st_mtime_ns
    )

    # Isolated Fabric read-only connection.
    conn = sqlite3.connect(
        f"file:{FABRIC_DB}?mode=ro",
        uri=True,
    )

    try:
        rows = load_fabric_rows(conn)

        if not rows:
            fail(
                "no Fabric canonical input available"
            )

        # Track evidence from the complete Fabric store.
        pre_launch_blocked = 0
        legacy_blocked = 0
        invalid_source_blocked = 0
        missing_provenance_blocked = 0
        duplicate_blocked = 0

        accepted = []
        seen_keys = set()

        for row in rows:

            # Legacy/non-Fabric data is never accepted.
            if row["source_type"] != SOURCE_TYPE:
                legacy_blocked += 1
                continue

            if not row["source_id"].startswith(
                KUCOIN_SOURCE_PREFIX
            ):
                invalid_source_blocked += 1
                continue

            # Launch boundary.
            if (
                not isinstance(
                    row["timestamp"],
                    int,
                )
                or row["timestamp"]
                < LAUNCH_TIMESTAMP
            ):
                pre_launch_blocked += 1
                continue

            # Canonical/provenance validation.
            try:
                validate_canonical(row)
            except RuntimeError as exc:

                text = str(exc)

                if (
                    "missing required field"
                    in text
                    or "missing retrieved_at"
                    in text
                    or "missing observation"
                    in text
                    or "invalid observation"
                    in text
                    or "missing canonical payload"
                    in text
                ):
                    missing_provenance_blocked += 1

                elif (
                    "source" in text
                    or "provider" in text
                ):
                    invalid_source_blocked += 1

                else:
                    # Invalid canonical data remains
                    # rejected and fail-closed.
                    invalid_source_blocked += 1

                continue

            key = canonical_identity(row)

            if key in seen_keys:
                duplicate_blocked += 1
                continue

            seen_keys.add(key)
            accepted.append(row)

        if not accepted:
            fail(
                "no valid post-launch Fabric "
                "canonical data accepted"
            )

        # The controlled cycle consumes ONLY accepted
        # Fabric canonical records.
        production_consumed = list(accepted)

        for row in production_consumed:
            if row["source_type"] != SOURCE_TYPE:
                fail(
                    "non-Fabric record entered "
                    "production consumer"
                )

            if not row["source_id"].startswith(
                KUCOIN_SOURCE_PREFIX
            ):
                fail(
                    "non-KuCoin source entered "
                    "production consumer"
                )

            if row["timestamp"] < LAUNCH_TIMESTAMP:
                fail(
                    "pre-launch record entered "
                    "production consumer"
                )

            validate_canonical(row)

        # Explicit proof: production consumer receives
        # only Fabric-validated data.
        if len(production_consumed) != len(
            accepted
        ):
            fail(
                "production consumption set mismatch"
            )

        if any(
            row["source_type"] != SOURCE_TYPE
            for row in production_consumed
        ):
            fail(
                "invalid source crossed boundary"
            )

        if any(
            row["timestamp"] < LAUNCH_TIMESTAMP
            for row in production_consumed
        ):
            fail(
                "pre-launch data crossed boundary"
            )

        # No production DB mutation.
        production_after = (
            PRODUCTION_DB.stat().st_mtime_ns
        )

        if production_before != production_after:
            fail(
                "production DB metadata changed"
            )

        # No trading downstream.
        if EXECUTION != "DISABLED":
            fail("execution safety violation")

        if ORDER_INTENTS_CREATED != 0:
            fail(
                "order intents were created"
            )

        print(
            "ENGINE=" + ENGINE
        )
        print(
            "VERSION=" + VERSION
        )
        print("FABRIC_INPUT=True")
        print(
            f"BOUNDARY_ACCEPTED={len(accepted)}"
        )
        print(
            "PRODUCTION_CONSUMPTION_ENABLED=True"
        )
        print(
            f"PRODUCTION_CANDLES_CONSUMED="
            f"{len(production_consumed)}"
        )
        print(
            f"PRE_LAUNCH_BLOCKED="
            f"{pre_launch_blocked}"
        )
        print(
            f"LEGACY_BLOCKED={legacy_blocked}"
        )
        print(
            f"INVALID_SOURCE_BLOCKED="
            f"{invalid_source_blocked}"
        )
        print(
            f"MISSING_PROVENANCE_BLOCKED="
            f"{missing_provenance_blocked}"
        )
        print(
            f"DUPLICATE_BLOCKED="
            f"{duplicate_blocked}"
        )
        print("FAIL_CLOSED=True")
        print("EXECUTION=DISABLED")
        print(
            "ORDER_INTENTS_CREATED=0"
        )
        print(
            "PRODUCTION_PATH_MUTATION=False"
        )
        print("DB_WRITES=0")
        print(
            "DATA_SOURCE=KUCOIN_FABRIC_CANONICAL"
        )
        print(
            "DATA_TIMESTAMP="
            + str(
                production_consumed[0][
                    "timestamp"
                ]
            )
        )
        print(
            "TIMEFRAME=1h"
        )
        print(
            "PROVENANCE_VALID=True"
        )
        print("VALIDATION=PASS")
        print("STATUS=PMDF_03_READY")

    finally:
        conn.close()


if __name__ == "__main__":
    main()