
import math
from datetime import datetime, timezone


ENGINE = "PUBLIC_CANONICAL_OHLCV_GAP_DUPLICATE_VALIDATION_v0.1"

SOURCE_ID = "SOLANA_MAINNET_RAYDIUM_AMM_V4"
SOURCE_TYPE = "DEX_ONCHAIN"
PRICE_UNIT = "USDC_PER_SOL"

POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"

TIMEFRAME = "1h"
BUCKET_SECONDS = 3600
SYMBOL = "SOL/USDC"

DB_WRITES = 0
CANONICAL_OHLCV_COMMITTED = False
EXECUTION = "DISABLED"
SOURCE = "REAL_DATA_ONLY"


# ============================================================
# REAL PDF-04 / PDF-05 CANONICAL CANDIDATE
# ============================================================

CANONICAL_CANDIDATES = [
    {
        "asset": "SOL",
        "symbol": "SOL/USDC",
        "timestamp": 1788822000,
        "timestamp_iso": "2026-09-07T23:00:00+00:00",
        "timeframe": "1h",
        "open": 103.9433519613302,
        "high": 103.9433519613302,
        "low": 103.93748844263929,
        "close": 103.93748844263929,
        "volume": 109.97541,
        "observation_count": 2,
        "pool": POOL,
        "price_unit": PRICE_UNIT,

        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,
        "source_timestamp": 1788822000,

        "observations": [
            {
                "signature":
                    "2m1fkxJhf2QDhqQZfd4Vb8xiYMGHraKgDVUh84mrQS6R6y9EoDJjiZzthC4vyt4fdYURtRxwcf2XrWsTvJQZatn",
                "slot": 445186108,
                "block_time": 1788822363,
                "price": 103.9433519613302,
                "volume_quote_usdc": 0.93135,
                "pool": POOL,
                "source_id": SOURCE_ID,
                "source_type": SOURCE_TYPE,
                "raydium_instruction": {
                    "group": 3,
                    "position": 5,
                    "program_id":
                        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                },
                "account_mapping": {
                    "account_3":
                        "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz",
                    "account_4":
                        "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz",
                    "account_5":
                        "4Nu86LTizYQVMJFM2Ate5aVzH77g3a7rbo9KPT9ExMZk",
                    "account_6":
                        "FdrGU7ETVKux31hGwunsVH4t1FTnVNGV7WKTfyGpgbs",
                },
                "retrieved_at":
                    "2026-09-08T00:00:00+00:00",
            },
            {
                "signature":
                    "2eNmAjMYRWUcrJyCwdex2JtVy3Yxo1549pHEEFjJNjvCsKLVGhkmqNhW6bz8Wrfa47hLsfRKzur1RaEs4P8DKYbA",
                "slot": 445186115,
                "block_time": 1788822365,
                "price": 103.93748844263929,
                "volume_quote_usdc": 109.04406,
                "pool": POOL,
                "source_id": SOURCE_ID,
                "source_type": SOURCE_TYPE,
                "raydium_instruction": {
                    "group": 4,
                    "position": 10,
                    "program_id":
                        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                },
                "account_mapping": {
                    "account_3":
                        "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz",
                    "account_4":
                        "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz",
                    "account_5":
                        "3LB6Rx9rwhDhfqnUAYc6kmvuRpwwRBxhGWFZJb5ACeCJ",
                    "account_6":
                        "7PZyYs8WnpKvW7k29BgtrPU4CCtqGm3kexsjr5GtqLhJ",
                },
                "retrieved_at":
                    "2026-09-08T00:00:00+00:00",
            },
        ],

        "provenance": {
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_timestamp": 1788822000,
            "observation_count": 2,
            "observation_signatures": [
                "2m1fkxJhf2QDhqQZfd4Vb8xiYMGHraKgDVUh84mrQS6R6y9EoDJjiZzthC4vyt4fdYURtRxwcf2XrWsTvJQZatn",
                "2eNmAjMYRWUcrJyCwdex2JtVy3Yxo1549pHEEFjJNjvCsKLVGhkmqNhW6bz8Wrfa47hLsfRKzur1RaEs4P8DKYbA",
            ],
            "observation_slots": [
                445186108,
                445186115,
            ],
            "observation_timestamps": [
                1788822363,
                1788822365,
            ],
            "pool": POOL,
            "raydium_instruction": [
                {
                    "group": 3,
                    "position": 5,
                    "program_id":
                        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                },
                {
                    "group": 4,
                    "position": 10,
                    "program_id":
                        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
                },
            ],
        },
    }
]


# ============================================================
# HELPERS
# ============================================================

def is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def is_utc_bucket(timestamp):
    if not isinstance(timestamp, int):
        return False

    return timestamp % BUCKET_SECONDS == 0


def bucket_distance_seconds(a, b):
    return abs(b - a)


# ============================================================
# SINGLE CANDLE VALIDATION
# ============================================================

def validate_candle(candidate):
    violations = {
        "duplicate": [],
        "ohcl": [],
        "source": [],
        "provenance": [],
    }

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
        "observation_count",
        "observations",
        "pool",
        "price_unit",
        "source_id",
        "source_type",
        "source_timestamp",
        "provenance",
    ]

    for key in required:
        if key not in candidate:
            violations["provenance"].append(
                f"MISSING_FIELD={key}"
            )

    if violations["provenance"]:
        return violations

    # --------------------------------------------------------
    # UTC / BUCKET
    # --------------------------------------------------------

    timestamp = candidate["timestamp"]

    if not is_utc_bucket(timestamp):
        violations["ohcl"].append(
            "TIMESTAMP_NOT_ON_1H_BOUNDARY"
        )

    if candidate["timeframe"] != TIMEFRAME:
        violations["ohcl"].append(
            "INVALID_TIMEFRAME"
        )

    try:
        dt = datetime.fromtimestamp(
            timestamp,
            timezone.utc,
        )

        if dt.tzinfo != timezone.utc:
            violations["ohcl"].append(
                "TIMESTAMP_NOT_UTC"
            )

    except Exception:
        violations["ohcl"].append(
            "INVALID_TIMESTAMP"
        )

    # --------------------------------------------------------
    # OHLC
    # --------------------------------------------------------

    for field in ["open", "high", "low", "close"]:
        if not is_finite_number(candidate[field]):
            violations["ohcl"].append(
                f"INVALID_PRICE={field}"
            )

    if not is_finite_number(candidate["volume"]):
        violations["ohcl"].append(
            "INVALID_VOLUME"
        )
    elif float(candidate["volume"]) < 0:
        violations["ohcl"].append(
            "NEGATIVE_VOLUME"
        )

    if not violations["ohcl"]:
        o = float(candidate["open"])
        h = float(candidate["high"])
        l = float(candidate["low"])
        c = float(candidate["close"])

        if h < max(o, c):
            violations["ohcl"].append(
                "HIGH_BELOW_OPEN_OR_CLOSE"
            )

        if l > min(o, c):
            violations["ohcl"].append(
                "LOW_ABOVE_OPEN_OR_CLOSE"
            )

        if h < l:
            violations["ohcl"].append(
                "HIGH_BELOW_LOW"
            )

    # --------------------------------------------------------
    # SOURCE CONSISTENCY
    # --------------------------------------------------------

    if candidate["source_id"] != SOURCE_ID:
        violations["source"].append(
            "INVALID_SOURCE_ID"
        )

    if candidate["source_type"] != SOURCE_TYPE:
        violations["source"].append(
            "INVALID_SOURCE_TYPE"
        )

    if candidate["pool"] != POOL:
        violations["source"].append(
            "INVALID_POOL"
        )

    if candidate["price_unit"] != PRICE_UNIT:
        violations["source"].append(
            "INVALID_PRICE_UNIT"
        )

    # --------------------------------------------------------
    # PROVENANCE
    # --------------------------------------------------------

    observations = candidate["observations"]
    provenance = candidate["provenance"]

    if len(observations) != candidate["observation_count"]:
        violations["provenance"].append(
            "OBSERVATION_COUNT_MISMATCH"
        )

    required_provenance = [
        "source_id",
        "source_type",
        "source_timestamp",
        "observation_count",
        "observation_signatures",
        "observation_slots",
        "observation_timestamps",
        "pool",
        "raydium_instruction",
    ]

    for key in required_provenance:
        if key not in provenance:
            violations["provenance"].append(
                f"MISSING_PROVENANCE_FIELD={key}"
            )

    if provenance.get("source_id") != SOURCE_ID:
        violations["source"].append(
            "PROVENANCE_SOURCE_ID_MISMATCH"
        )

    if provenance.get("source_type") != SOURCE_TYPE:
        violations["source"].append(
            "PROVENANCE_SOURCE_TYPE_MISMATCH"
        )

    if provenance.get("pool") != POOL:
        violations["source"].append(
            "PROVENANCE_POOL_MISMATCH"
        )

    if provenance.get("source_timestamp") != timestamp:
        violations["provenance"].append(
            "PROVENANCE_SOURCE_TIMESTAMP_MISMATCH"
        )

    # --------------------------------------------------------
    # OBSERVATION SOURCE / POOL CONSISTENCY
    # --------------------------------------------------------

    for i, obs in enumerate(observations):
        if obs.get("source_id") != SOURCE_ID:
            violations["source"].append(
                f"OBSERVATION_SOURCE_ID_MISMATCH={i}"
            )

        if obs.get("source_type") != SOURCE_TYPE:
            violations["source"].append(
                f"OBSERVATION_SOURCE_TYPE_MISMATCH={i}"
            )

        if obs.get("pool") != POOL:
            violations["source"].append(
                f"OBSERVATION_POOL_MISMATCH={i}"
            )

        if "signature" not in obs:
            violations["provenance"].append(
                f"MISSING_OBSERVATION_SIGNATURE={i}"
            )

        if "block_time" not in obs:
            violations["provenance"].append(
                f"MISSING_OBSERVATION_TIMESTAMP={i}"
            )

        if "retrieved_at" not in obs:
            violations["provenance"].append(
                f"MISSING_RETRIEVED_AT={i}"
            )

    # --------------------------------------------------------
    # DUPLICATE OBSERVATIONS
    # --------------------------------------------------------

    observation_keys = set()
    observation_signatures = set()

    for i, obs in enumerate(observations):
        block_time = obs.get("block_time")
        signature = obs.get("signature")

        key = (
            obs.get("source_id"),
            obs.get("source_type"),
            obs.get("pool"),
            block_time,
        )

        if key in observation_keys:
            violations["duplicate"].append(
                f"DUPLICATE_OBSERVATION_TIMESTAMP={block_time}"
            )

        observation_keys.add(key)

        if signature in observation_signatures:
            violations["duplicate"].append(
                f"DUPLICATE_OBSERVATION_SIGNATURE={signature}"
            )

        observation_signatures.add(signature)

    # --------------------------------------------------------
    # DUPLICATE PROVENANCE LINEAGE
    # --------------------------------------------------------

    signatures = provenance.get(
        "observation_signatures", []
    )

    slots = provenance.get(
        "observation_slots", []
    )

    timestamps = provenance.get(
        "observation_timestamps", []
    )

    if len(signatures) != len(set(signatures)):
        violations["duplicate"].append(
            "DUPLICATE_PROVENANCE_SIGNATURE"
        )

    lineage_keys = list(
        zip(
            signatures,
            slots,
            timestamps,
        )
    )

    if len(lineage_keys) != len(set(lineage_keys)):
        violations["duplicate"].append(
            "DUPLICATE_PROVENANCE_LINEAGE"
        )

    # --------------------------------------------------------
    # PROVENANCE <-> OBSERVATION EXACT MATCH
    # --------------------------------------------------------

    actual_signatures = [
        x.get("signature")
        for x in observations
    ]

    actual_slots = [
        x.get("slot")
        for x in observations
    ]

    actual_timestamps = [
        x.get("block_time")
        for x in observations
    ]

    if signatures != actual_signatures:
        violations["provenance"].append(
            "PROVENANCE_SIGNATURE_LINEAGE_MISMATCH"
        )

    if slots != actual_slots:
        violations["provenance"].append(
            "PROVENANCE_SLOT_LINEAGE_MISMATCH"
        )

    if timestamps != actual_timestamps:
        violations["provenance"].append(
            "PROVENANCE_TIMESTAMP_LINEAGE_MISMATCH"
        )

    # --------------------------------------------------------
    # ONE CANDLE = ONE SOURCE
    # --------------------------------------------------------

    source_pairs = {
        (
            obs.get("source_id"),
            obs.get("source_type"),
        )
        for obs in observations
    }

    if len(source_pairs) != 1:
        violations["source"].append(
            "MULTIPLE_SOURCES_IN_SINGLE_CANDLE"
        )

    if source_pairs and source_pairs != {
        (SOURCE_ID, SOURCE_TYPE)
    }:
        violations["source"].append(
            "SOURCE_SET_NOT_CANONICAL"
        )

    return violations


# ============================================================
# GLOBAL DUPLICATE + GAP VALIDATION
# ============================================================

def validate_collection(candidates):
    duplicate_candles = 0
    duplicate_observations = 0
    gaps_found = 0
    gap_buckets = 0
    ohlc_violations = 0
    source_violations = 0
    provenance_violations = 0

    timestamps = set()
    ordered_timestamps = []

    observation_keys = set()

    for candidate in candidates:

        ts = candidate.get("timestamp")

        if ts in timestamps:
            duplicate_candles += 1

        timestamps.add(ts)
        ordered_timestamps.append(ts)

        violations = validate_candle(candidate)

        duplicate_count = len(
            violations["duplicate"]
        )
        duplicate_observations += duplicate_count

        if violations["ohcl"]:
            ohlc_violations += 1

        if violations["source"]:
            source_violations += 1

        if violations["provenance"]:
            provenance_violations += 1

        for obs in candidate.get("observations", []):
            key = (
                obs.get("source_id"),
                obs.get("source_type"),
                obs.get("pool"),
                obs.get("block_time"),
            )

            if key in observation_keys:
                duplicate_observations += 1

            observation_keys.add(key)

    # --------------------------------------------------------
    # GAP DETECTION
    #
    # IMPORTANT:
    # A single bucket produces NO GAP.
    # Missing adjacent buckets are not treated as violations.
    # --------------------------------------------------------

    ordered_timestamps = sorted(set(ordered_timestamps))

    for previous, current in zip(
        ordered_timestamps,
        ordered_timestamps[1:],
    ):
        distance = bucket_distance_seconds(
            previous,
            current,
        )

        if distance > BUCKET_SECONDS:
            missing = (
                distance // BUCKET_SECONDS
            ) - 1

            if missing > 0:
                gaps_found += 1
                gap_buckets += missing

    return {
        "duplicate_candles": duplicate_candles,
        "duplicate_observations": duplicate_observations,
        "gaps_found": gaps_found,
        "gap_buckets": gap_buckets,
        "ohlc_violations": ohlc_violations,
        "source_violations": source_violations,
        "provenance_violations": provenance_violations,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    canonical_input = len(
        CANONICAL_CANDIDATES
    )

    results = validate_collection(
        CANONICAL_CANDIDATES
    )

    total_violations = (
        results["duplicate_candles"]
        + results["duplicate_observations"]
        + results["gaps_found"]
        + results["ohlc_violations"]
        + results["source_violations"]
        + results["provenance_violations"]
    )

    invalid_candles = 0

    for candidate in CANONICAL_CANDIDATES:
        violations = validate_candle(candidate)

        has_violation = any(
            violations[group]
            for group in violations
        )

        if has_violation:
            invalid_candles += 1

    valid_candles = (
        canonical_input - invalid_candles
    )

    if total_violations > 0:
        status = "FAIL_CLOSED"
        fail_closed = True
    else:
        status = "VALID"
        fail_closed = False

    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print(f"EXECUTION={EXECUTION}")
    print(f"SOURCE={SOURCE}")
    print(f"SOURCE_ID={SOURCE_ID}")
    print(f"SOURCE_TYPE={SOURCE_TYPE}")
    print(f"TIMEFRAME={TIMEFRAME}")

    print()
    print("===== PDF-06 GAP / DUPLICATE VALIDATION RUNTIME EVIDENCE =====")
    print(f"STATUS={status}")
    print(f"CANONICAL_CANDLES_INPUT={canonical_input}")
    print(f"VALID_CANDLES={valid_candles}")
    print(f"INVALID_CANDLES={invalid_candles}")
    print(
        f"DUPLICATE_CANDLES="
        f"{results['duplicate_candles']}"
    )
    print(
        f"DUPLICATE_OBSERVATIONS="
        f"{results['duplicate_observations']}"
    )
    print(
        f"GAPS_FOUND="
        f"{results['gaps_found']}"
    )
    print(
        f"GAP_BUCKETS="
        f"{results['gap_buckets']}"
    )
    print(
        f"OHLC_VIOLATIONS="
        f"{results['ohlc_violations']}"
    )
    print(
        f"SOURCE_VIOLATIONS="
        f"{results['source_violations']}"
    )
    print(
        f"PROVENANCE_VIOLATIONS="
        f"{results['provenance_violations']}"
    )
    print(f"DB_WRITES={DB_WRITES}")
    print(
        "CANONICAL_OHLCV_COMMITTED="
        f"{CANONICAL_OHLCV_COMMITTED}"
    )
    print(f"FAIL_CLOSED={fail_closed}")


if __name__ == "__main__":
    main()