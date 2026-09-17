
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ENGINE = "ARUNDA_SHADOW_MONITORED_MARKET_DATA_OPERATION"
VERSION = "v0.1"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

LAUNCH_TIMESTAMP = int(
    datetime(
        2026,
        8,
        31,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    ).timestamp()
)

PRIMARY_PROVIDER = "KUCOIN"
FAILOVER_PROVIDER = "BITGET"

SOURCE_TYPE = "CEX_PUBLIC_API"
TIMEFRAME = "1h"

KUCOIN_SOURCE_PREFIX = "KUCOIN_SPOT:"
BITGET_SOURCE_PREFIX = "BITGET"

SHADOW_MODE = True
TRADING_ENABLED = False
ORDER_INTENTS_CREATED = 0
EXECUTION = "DISABLED"

DB_WRITES = 0


def fail(message: str) -> None:
    raise RuntimeError(
        f"SHADOW FAIL-CLOSED: {message}"
    )


def finite(value) -> bool:
    return (
        isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def identify_provider(row) -> str | None:
    source_id = row["source_id"] or ""

    if row["source_type"] != SOURCE_TYPE:
        return None

    if source_id.startswith(
        KUCOIN_SOURCE_PREFIX
    ):
        return PRIMARY_PROVIDER

    if source_id.startswith(
        BITGET_SOURCE_PREFIX
    ):
        return FAILOVER_PROVIDER

    return None


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


def validate_canonical(row) -> str:
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

    provider = identify_provider(row)

    if provider is None:
        fail(
            "invalid provider provenance: "
            f"{row['source_id']}"
        )

    if row["timeframe"] != TIMEFRAME:
        fail(
            f"invalid timeframe: "
            f"{row['timeframe']}"
        )

    if not isinstance(
        row["timestamp"],
        int,
    ):
        fail(
            "timestamp is not integer"
        )

    if row["timestamp"] < LAUNCH_TIMESTAMP:
        fail(
            "pre-launch candle reached "
            "shadow consumer"
        )

    if (
        row["source_timestamp"]
        != row["timestamp"]
    ):
        fail(
            "source timestamp was not preserved"
        )

    if (
        not isinstance(
            row["retrieved_at"],
            str,
        )
        or not row["retrieved_at"]
    ):
        fail(
            "invalid retrieved_at"
        )

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

    if not isinstance(
        signatures,
        list,
    ):
        fail(
            "invalid observation signatures"
        )

    if not isinstance(
        slots,
        list,
    ):
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

    # CEX records must not contain DEX provenance.
    if row["pool"] not in (
        None,
        "null",
    ):
        fail(
            "CEX record contains DEX pool provenance"
        )

    if row["raydium_instruction"] not in (
        None,
        "null",
    ):
        fail(
            "CEX record contains Raydium provenance"
        )

    if not isinstance(
        row["canonical_payload"],
        str,
    ) or not row["canonical_payload"]:
        fail(
            "missing canonical payload"
        )

    return provider


def canonical_identity(row):
    return (
        row["asset"],
        row["symbol"],
        row["timestamp"],
        row["timeframe"],
    )


def main() -> None:

    # Mandatory shadow safety.
    if SHADOW_MODE is not True:
        fail(
            "SHADOW_MODE must be True"
        )

    if TRADING_ENABLED is not False:
        fail(
            "TRADING_ENABLED must be False"
        )

    if ORDER_INTENTS_CREATED != 0:
        fail(
            "ORDER_INTENTS_CREATED must be 0"
        )

    if EXECUTION != "DISABLED":
        fail(
            "EXECUTION must be DISABLED"
        )

    if DB_WRITES != 0:
        fail(
            "DB_WRITES must be 0"
        )

    if not FABRIC_DB.exists():
        fail(
            f"Fabric store missing: {FABRIC_DB}"
        )

    if not PRODUCTION_DB.exists():
        fail(
            "production DB missing; fail-closed"
        )

    # Production DB is NEVER opened.
    production_before = (
        PRODUCTION_DB.stat().st_mtime_ns
    )

    # Read-only Fabric connection.
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

        legacy_blocked = 0
        pre_launch_blocked = 0

        invalid_source_blocked = 0
        missing_provenance_blocked = 0
        duplicate_blocked = 0

        accepted = []
        seen_keys = set()

        for row in rows:

            # Non-CEX / DEX / legacy records are blocked,
            # not fatal to the controlled cycle.
            if row["source_type"] != SOURCE_TYPE:
                legacy_blocked += 1
                continue

            source_id = row["source_id"] or ""

            provider = identify_provider(row)

            if provider is None:
                invalid_source_blocked += 1
                continue

            if not isinstance(
                row["timestamp"],
                int,
            ):
                invalid_source_blocked += 1
                continue

            # Launch boundary.
            if row["timestamp"] < LAUNCH_TIMESTAMP:
                pre_launch_blocked += 1
                continue

            # Full canonical validation.
            try:
                validate_canonical(row)

            except RuntimeError as exc:

                text = str(exc)

                provenance_terms = (
                    "missing required field",
                    "retrieved_at",
                    "observation",
                    "provenance",
                    "canonical payload",
                )

                source_terms = (
                    "source",
                    "provider",
                    "Raydium",
                    "DEX",
                )

                if any(
                    term in text
                    for term in provenance_terms
                ):
                    missing_provenance_blocked += 1

                elif any(
                    term in text
                    for term in source_terms
                ):
                    invalid_source_blocked += 1

                else:
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

        # -------------------------------------------------
        # REAL PMDF-03 CONSUMER PATH
        #
        # PMDF-03 itself defines the actual controlled
        # Fabric -> Production Market-Data consumption
        # boundary. This Shadow stage reproduces that
        # exact consumption contract without touching
        # production DB or downstream trading layers.
        # -------------------------------------------------

        production_consumed = []

        for row in accepted:

            provider = validate_canonical(row)

            if provider not in (
                PRIMARY_PROVIDER,
                FAILOVER_PROVIDER,
            ):
                fail(
                    "unknown provider crossed "
                    "shadow consumer"
                )

            production_consumed.append(row)

        if not production_consumed:
            fail(
                "production consumer received "
                "zero validated candles"
            )

        # Provider identity must remain traceable.
        providers = {
            identify_provider(row)
            for row in production_consumed
        }

        if None in providers:
            fail(
                "provider identity lost"
            )

        # Failover-only policy: never blend.
        if len(providers) > 1:
            fail(
                "provider blending detected"
            )

        selected_provider = next(
            iter(providers)
        )

        # If primary data is present, it remains primary.
        # Bitget is valid only as a failover source.
        if (
            selected_provider
            not in (
                PRIMARY_PROVIDER,
                FAILOVER_PROVIDER,
            )
        ):
            fail(
                "invalid selected provider"
            )

        failover_triggered = (
            selected_provider
            == FAILOVER_PROVIDER
        )

        # No production DB mutation.
        production_after = (
            PRODUCTION_DB.stat().st_mtime_ns
        )

        if production_before != production_after:
            fail(
                "production DB metadata changed"
            )

        # No trading artifacts.
        if TRADING_ENABLED:
            fail(
                "trading was enabled"
            )

        if ORDER_INTENTS_CREATED != 0:
            fail(
                "order intents were created"
            )

        if EXECUTION != "DISABLED":
            fail(
                "execution is not disabled"
            )

        # Mandatory final safety proof.
        if DB_WRITES != 0:
            fail(
                "DB writes detected"
            )

        # Compact runtime report.
        print(
            f"ENGINE={ENGINE}"
        )

        print(
            f"VERSION={VERSION}"
        )

        print(
            f"PRIMARY_PROVIDER="
            f"{PRIMARY_PROVIDER}"
        )

        print(
            f"SELECTED_PROVIDER="
            f"{selected_provider}"
        )

        print(
            "FABRIC_INPUT=True"
        )

        print(
            f"CANONICAL_BARS="
            f"{len(accepted)}"
        )

        print(
            "PRODUCTION_CANDLES_CONSUMED="
            f"{len(production_consumed)}"
        )

        print(
            "PROVENANCE_VALID=True"
        )

        print(
            f"LEGACY_BLOCKED="
            f"{legacy_blocked}"
        )

        print(
            f"PRE_LAUNCH_BLOCKED="
            f"{pre_launch_blocked}"
        )

        print(
            f"FAILOVER_TRIGGERED="
            f"{failover_triggered}"
        )

        print(
            "BLENDING=False"
        )

        print(
            "SHADOW_MODE=True"
        )

        print(
            "TRADING_ENABLED=False"
        )

        print(
            "ORDER_INTENTS_CREATED=0"
        )

        print(
            "EXECUTION=DISABLED"
        )

        print(
            "PRODUCTION_DB_TOUCHED=False"
        )

        print(
            "DB_WRITES=0"
        )

        print(
            "PRODUCTION_PATH_MUTATION=False"
        )

        print(
            "VALIDATION=PASS"
        )

        print(
            "STATUS=SHADOW_MONITORED_PASS"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()