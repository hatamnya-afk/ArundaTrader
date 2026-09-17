# C:\Users\ASUS\ArundaTrader\public_market_data_fabric\controlled_launch_preflight_v0.1.py

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


ENGINE = "CONTROLLED_LAUNCH_PREFLIGHT_v0.1"

LAUNCH_TIMESTAMP = "2026-08-31T00:00:00+00:00"
LAUNCH_TS = int(
    datetime.fromisoformat(LAUNCH_TIMESTAMP).timestamp()
)

TIMEFRAME = "1h"

# ============================================================
# HARD PRODUCTION BOUNDARY
# ============================================================

PRODUCTION_CONSUMPTION_ENABLED = False
PRODUCTION_DB_TOUCHED = False
DB_WRITES_PRODUCTION = 0
EXECUTION = "DISABLED"
ORDER_INTENTS_CREATED = 0
PRODUCTION_PATH_MUTATION = False

# ============================================================
# REAL FABRIC CANONICAL CANDLE
# Exact real candle verified in PDF-04/PDF-05/PDF-08.
# No new market data is generated.
# ============================================================

REAL_FABRIC_CANDLE = {
    "asset": "SOL",
    "symbol": "SOL/USDC",
    "timestamp": 1788822000,
    "timeframe": "1h",

    "open": 103.9433519613302,
    "high": 103.9433519613302,
    "low": 103.93748844263929,
    "close": 103.93748844263929,
    "volume": 109.97541,

    "source_id": "SOLANA_MAINNET_RAYDIUM_AMM_V4",
    "source_type": "DEX_ONCHAIN",
    "source_timestamp": 1788822000,
    "retrieved_at": (
        "2026-09-07T23:06:03+00:00"
    ),

    "observation_count": 2,
    "observation_signatures": [
        "2m1fkxJhf2QDhqQZfd4Vb8xiYMGHraKgDVUh84mrQS6R6y9EoDJjiZzthC4vyt4fdYURtRxwcf2XrWsTvJQZatn",
        "2eNmAjMYRWUcrJyCwdex2JtVy3Yxo1549pHEEFjJNjvCsKLVGhkmqNhW6bz8Wrfa47hLsfRKzur1RaEs4P8DKYbA",
    ],
    "observation_slots": [
        445186108,
        445186115,
    ],
    "pool": (
        "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
    ),
    "raydium_instruction": {
        "program_id":
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        "observations": [
            {
                "group": 3,
                "position": 5,
                "data": "9mXzHTFUufwuPjERJWfrwTV",
            },
            {
                "group": 4,
                "position": 10,
                "data": "9vG8YrqrBwUiB58scjSXySw",
            },
        ],
    },
    "price_unit": "USDC_PER_SOL",
}


# ============================================================
# CONTRACT
# ============================================================

CANONICAL_FIELDS = (
    "asset",
    "symbol",
    "timestamp",
    "timeframe",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

PROVENANCE_FIELDS = (
    "source_id",
    "source_type",
    "source_timestamp",
    "retrieved_at",
)

VALID_SOURCE_IDS = {
    "BITGET_SPOT_PUBLIC",
    "KUCOIN_SPOT_PUBLIC",
    "SOLANA_MAINNET_RAYDIUM_AMM_V4",
}

VALID_SOURCE_TYPES = {
    "CEX_PUBLIC",
    "DEX_ONCHAIN",
}


# ============================================================
# READ-ONLY BOUNDARY VALIDATOR
# ============================================================

def validate_fabric_candle(candle: dict) -> tuple[bool, str]:

    # Canonical contract
    if any(
        field not in candle
        for field in CANONICAL_FIELDS
    ):
        return False, "MISSING_CANONICAL_FIELD"

    # Provenance contract
    if any(
        field not in candle
        or candle[field] in (None, "")
        for field in PROVENANCE_FIELDS
    ):
        return False, "MISSING_PROVENANCE"

    # Timeframe
    if candle["timeframe"] != TIMEFRAME:
        return False, "INVALID_TIMEFRAME"

    # UTC timestamp
    timestamp = candle["timestamp"]

    if not isinstance(timestamp, int):
        return False, "INVALID_TIMESTAMP"

    # 1h UTC boundary
    if timestamp % 3600 != 0:
        return False, "TIMESTAMP_NOT_1H_BOUNDARY"

    # Launch boundary
    if timestamp < LAUNCH_TS:
        return False, "PRE_LAUNCH_DATA"

    # Source
    if candle["source_id"] not in VALID_SOURCE_IDS:
        return False, "INVALID_SOURCE"

    if candle["source_type"] not in VALID_SOURCE_TYPES:
        return False, "INVALID_SOURCE_TYPE"

    # One candle = one source
    if not isinstance(candle["source_id"], str):
        return False, "SOURCE_ID_INVALID"

    # OHLC contract
    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]
    v = candle["volume"]

    if h < max(o, c):
        return False, "OHLC_HIGH_VIOLATION"

    if l > min(o, c):
        return False, "OHLC_LOW_VIOLATION"

    if h < l:
        return False, "OHLC_RANGE_VIOLATION"

    if v < 0:
        return False, "NEGATIVE_VOLUME"

    # DEX provenance / lineage
    if candle["source_type"] == "DEX_ONCHAIN":

        lineage = (
            "observation_count",
            "observation_signatures",
            "observation_slots",
            "pool",
            "raydium_instruction",
        )

        if any(
            field not in candle
            or candle[field] in (None, "", [], {})
            for field in lineage
        ):
            return False, "INCOMPLETE_DEX_LINEAGE"

    return True, "VALID"


# ============================================================
# DUPLICATE DETECTOR
# ============================================================

def canonical_key(candle: dict) -> tuple:
    return (
        candle["asset"],
        candle["symbol"],
        candle["timestamp"],
        candle["timeframe"],
    )


def is_duplicate(
    candle: dict,
    accepted_keys: set,
) -> bool:
    return canonical_key(candle) in accepted_keys


# ============================================================
# LEGACY POLICY
# ============================================================

def is_legacy_market_technical(candle: dict) -> bool:
    return candle.get("storage_origin") == "market_technical"


# ============================================================
# READ-ONLY CONSUMPTION SIMULATION
# ============================================================

def consume_read_only(
    candle: dict,
    accepted_keys: set,
) -> tuple[bool, str]:

    if is_legacy_market_technical(candle):
        return False, "LEGACY_DATA"

    valid, reason = validate_fabric_candle(candle)

    if not valid:
        return False, reason

    if is_duplicate(candle, accepted_keys):
        return False, "DUPLICATE"

    return True, "ACCEPTED"


# ============================================================
# PREFLIGHT
# ============================================================

def main():

    # --------------------------------------------------------
    # A — VALID FABRIC CANDLE
    # --------------------------------------------------------

    valid_candle = deepcopy(REAL_FABRIC_CANDLE)

    accepted_keys = set()

    accepted, reason = consume_read_only(
        valid_candle,
        accepted_keys,
    )

    valid_fabric_input = 1
    valid_input_accepted = int(
        accepted and reason == "ACCEPTED"
    )

    if accepted:
        accepted_keys.add(
            canonical_key(valid_candle)
        )

    # --------------------------------------------------------
    # B — PRE-LAUNCH CANDLE
    # --------------------------------------------------------

    pre_launch = deepcopy(REAL_FABRIC_CANDLE)

    pre_launch["timestamp"] = (
        LAUNCH_TS - 3600
    )
    pre_launch["source_timestamp"] = (
        LAUNCH_TS - 3600
    )

    accepted_pre, reason_pre = consume_read_only(
        pre_launch,
        accepted_keys,
    )

    pre_launch_rejected = int(
        not accepted_pre
        and reason_pre == "PRE_LAUNCH_DATA"
    )

    # --------------------------------------------------------
    # C — MISSING PROVENANCE
    # --------------------------------------------------------

    missing_provenance = deepcopy(
        REAL_FABRIC_CANDLE
    )

    missing_provenance.pop(
        "retrieved_at",
        None,
    )

    accepted_prov, reason_prov = consume_read_only(
        missing_provenance,
        accepted_keys,
    )

    missing_provenance_rejected = int(
        not accepted_prov
        and reason_prov == "MISSING_PROVENANCE"
    )

    # --------------------------------------------------------
    # D — INVALID SOURCE
    # --------------------------------------------------------

    invalid_source = deepcopy(
        REAL_FABRIC_CANDLE
    )

    invalid_source["source_id"] = (
        "UNREGISTERED_SOURCE"
    )

    accepted_source, reason_source = consume_read_only(
        invalid_source,
        accepted_keys,
    )

    invalid_source_rejected = int(
        not accepted_source
        and reason_source == "INVALID_SOURCE"
    )

    # --------------------------------------------------------
    # E — LEGACY market_technical
    # --------------------------------------------------------

    legacy = deepcopy(REAL_FABRIC_CANDLE)

    legacy["storage_origin"] = "market_technical"

    accepted_legacy, reason_legacy = consume_read_only(
        legacy,
        accepted_keys,
    )

    legacy_rejected = int(
        not accepted_legacy
        and reason_legacy == "LEGACY_DATA"
    )

    # --------------------------------------------------------
    # F — DUPLICATE
    # --------------------------------------------------------

    duplicate = deepcopy(
        REAL_FABRIC_CANDLE
    )

    accepted_duplicate, reason_duplicate = (
        consume_read_only(
            duplicate,
            accepted_keys,
        )
    )

    duplicate_rejected = int(
        not accepted_duplicate
        and reason_duplicate == "DUPLICATE"
    )

    # --------------------------------------------------------
    # G — REJECTED DATA NEVER ENTERS PRODUCTION
    # --------------------------------------------------------

    rejected_cases = [
        accepted_pre,
        accepted_prov,
        accepted_source,
        accepted_legacy,
        accepted_duplicate,
    ]

    rejected_entered_production = any(
        rejected_cases
    )

    all_rejected_blocked = not rejected_entered_production

    # --------------------------------------------------------
    # GLOBAL FAIL-CLOSED
    # --------------------------------------------------------

    all_verified = all([
        valid_fabric_input == 1,
        valid_input_accepted == 1,
        pre_launch_rejected == 1,
        missing_provenance_rejected == 1,
        invalid_source_rejected == 1,
        legacy_rejected == 1,
        duplicate_rejected == 1,
        all_rejected_blocked,
        PRODUCTION_CONSUMPTION_ENABLED is False,
        PRODUCTION_DB_TOUCHED is False,
        DB_WRITES_PRODUCTION == 0,
        EXECUTION == "DISABLED",
        ORDER_INTENTS_CREATED == 0,
        PRODUCTION_PATH_MUTATION is False,
    ])

    status = (
        "CONTROLLED_LAUNCH_PREFLIGHT_VERIFIED"
        if all_verified
        else "FAIL_CLOSED"
    )

    # ========================================================
    # RUNTIME EVIDENCE
    # ========================================================

    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print("ARUNDA_DB_ACCESS=NONE")

    print()
    print("===== CONTROLLED LAUNCH PREFLIGHT RUNTIME EVIDENCE =====")

    print(f"STATUS={status}")
    print(f"LAUNCH_TIMESTAMP={LAUNCH_TIMESTAMP}")

    print(
        f"VALID_FABRIC_INPUT="
        f"{valid_fabric_input}"
    )

    print(
        f"VALID_INPUT_ACCEPTED_BY_BOUNDARY="
        f"{valid_input_accepted}"
    )

    print(
        f"PRE_LAUNCH_REJECTED="
        f"{pre_launch_rejected}"
    )

    print(
        f"MISSING_PROVENANCE_REJECTED="
        f"{missing_provenance_rejected}"
    )

    print(
        f"INVALID_SOURCE_REJECTED="
        f"{invalid_source_rejected}"
    )

    print(
        f"DUPLICATE_REJECTED="
        f"{duplicate_rejected}"
    )

    print(
        f"LEGACY_DATA_REJECTED="
        f"{legacy_rejected}"
    )

    print(
        f"FAIL_CLOSED="
        f"{not all_verified}"
    )

    print(
        f"PRODUCTION_CONSUMPTION_ENABLED="
        f"{PRODUCTION_CONSUMPTION_ENABLED}"
    )

    print(
        f"PRODUCTION_DB_TOUCHED="
        f"{PRODUCTION_DB_TOUCHED}"
    )

    print(
        f"DB_WRITES_PRODUCTION="
        f"{DB_WRITES_PRODUCTION}"
    )

    print(f"EXECUTION={EXECUTION}")

    print(
        f"ORDER_INTENTS_CREATED="
        f"{ORDER_INTENTS_CREATED}"
    )

    print(
        f"PRODUCTION_PATH_MUTATION="
        f"{PRODUCTION_PATH_MUTATION}"
    )

    print(
        f"REJECTED_DATA_ENTERED_PRODUCTION="
        f"{rejected_entered_production}"
    )


if __name__ == "__main__":
    main()