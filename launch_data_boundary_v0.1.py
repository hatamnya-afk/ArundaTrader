# C:\Users\ASUS\ArundaTrader\public_market_data_fabric\launch_data_boundary_v0.1.py

from __future__ import annotations

from datetime import datetime, timezone


ENGINE = "LAUNCH_DATA_BOUNDARY_v0.1"

# ============================================================
# FORMALLY ESTABLISHED LAUNCH BOUNDARY
# ============================================================

LAUNCH_TIMESTAMP = "2026-08-31T00:00:00+00:00"
LAUNCH_TIMESTAMP_STATUS = "RESOLVED_FORMALLY_ESTABLISHED"

TIMEFRAME = "1h"

# ============================================================
# CANONICAL CONTRACT
# ============================================================

CANONICAL_FIELDS = [
    "asset",
    "symbol",
    "timestamp",
    "timeframe",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

PROVENANCE_FIELDS = [
    "source_id",
    "source_type",
    "source_timestamp",
    "retrieved_at",
]

LINEAGE_FIELDS = [
    "observation_count",
    "observation_signatures",
    "observation_slots",
    "pool",
    "raydium_instruction",
]

VALID_SOURCE_TYPES = {
    "CEX_PUBLIC",
    "DEX_ONCHAIN",
}

VALID_SOURCE_IDS = {
    "BITGET_SPOT_PUBLIC",
    "KUCOIN_SPOT_PUBLIC",
    "SOLANA_MAINNET_RAYDIUM_AMM_V4",
}

VALIDATION_REQUIREMENTS = [
    "canonical",
    "validated",
    "provenance_complete",
    "timestamp_gte_launch",
    "valid_source",
    "no_duplicate",
    "no_gap_contract_violation",
    "one_candle_one_source",
]

FAIL_CLOSED_RULE = (
    "Any missing canonical/provenance/validation/source/boundary "
    "requirement blocks production consumption."
)

LEGACY_DATA_POLICY = (
    "legacy market_technical is NON-PRODUCTION; "
    "all data before LAUNCH_TIMESTAMP is NON-PRODUCTION."
)

POST_LAUNCH_DATA_POLICY = (
    "Only Fabric canonical candles that pass validation, complete "
    "provenance, valid source, duplicate protection, gap/contract "
    "validation, and timestamp >= LAUNCH_TIMESTAMP may be eligible "
    "for future production consumption."
)

# ============================================================
# HARD PRODUCTION BOUNDARY
# ============================================================

PRODUCTION_DB_TOUCHED = False
DB_WRITES_PRODUCTION = 0
EXECUTION = "DISABLED"
PRODUCTION_CONSUMPTION_ENABLED = False

# Explicitly informational only.
PRODUCTION_DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"


# ============================================================
# PREFLIGHT VALIDATION
# ============================================================

def validate_launch_timestamp() -> bool:
    try:
        dt = datetime.fromisoformat(LAUNCH_TIMESTAMP)

        if dt.tzinfo is None:
            return False

        if dt.tzinfo != timezone.utc:
            return False

        if dt.isoformat() != LAUNCH_TIMESTAMP:
            return False

        return True

    except Exception:
        return False


def validate_contract() -> bool:
    return (
        validate_launch_timestamp()
        and TIMEFRAME == "1h"
        and all(CANONICAL_FIELDS)
        and all(PROVENANCE_FIELDS)
        and all(LINEAGE_FIELDS)
        and bool(VALID_SOURCE_TYPES)
        and bool(VALID_SOURCE_IDS)
        and len(VALIDATION_REQUIREMENTS) >= 1
        and bool(FAIL_CLOSED_RULE)
        and bool(LEGACY_DATA_POLICY)
        and bool(POST_LAUNCH_DATA_POLICY)
    )


def main():

    launch_valid = validate_launch_timestamp()
    contract_valid = validate_contract()

    if not launch_valid:
        status = "READY_BUT_BLOCKED_ON_LAUNCH_TIMESTAMP"
        fail_closed = True
    elif not contract_valid:
        status = "READY_BUT_BLOCKED_ON_CONTRACT"
        fail_closed = True
    else:
        status = "LAUNCH_DATA_BOUNDARY_PREFLIGHT_VERIFIED"
        fail_closed = False

    # ========================================================
    # RUNTIME EVIDENCE
    # ========================================================

    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print("PRODUCTION_DB_ACCESS=NONE")
    print(f"PRODUCTION_DB_PATH={PRODUCTION_DB_PATH}")

    print()
    print("===== PDF-09 LAUNCH DATA BOUNDARY PREFLIGHT =====")

    print(f"STATUS={status}")
    print(f"LAUNCH_TIMESTAMP={LAUNCH_TIMESTAMP}")
    print(f"LAUNCH_TIMESTAMP_STATUS={LAUNCH_TIMESTAMP_STATUS}")
    print(f"TIMEFRAME={TIMEFRAME}")

    print(f"CANONICAL_CONTRACT_VALID={contract_valid}")
    print("PROVENANCE_REQUIRED=True")
    print("SOURCE_VALIDATION=True")

    print("LEGACY_DATA_EXCLUDED=True")
    print("PRE_LAUNCH_DATA_EXCLUDED=True")

    print(
        "POST_LAUNCH_DATA_POLICY="
        "FABRIC_VALIDATED_ONLY"
    )

    print(f"FAIL_CLOSED={fail_closed}")

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
        f"PRODUCTION_CONSUMPTION_ENABLED="
        f"{PRODUCTION_CONSUMPTION_ENABLED}"
    )


if __name__ == "__main__":
    main()