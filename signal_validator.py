
# =============================================================================
# ARUNDA SIGNAL VALIDATOR v0.4
#
# REAL RUNTIME CONTRACT:
#
# signal_engine.build_all()
#        |
#        v
# result[asset]["signal"]
#        |
#        v
# signal_contract.validate_signal()
#        |
#        v
# VALIDATED SIGNAL SNAPSHOT
#
# =============================================================================
#
# PURPOSE:
# Validate the real signal objects produced by signal_engine.build_all().
#
# RULES:
#   - MEMORY ONLY
#   - READ ONLY
#   - NO SQL
#   - NO DATABASE
#   - NO DATABASE WRITES
#   - NO REGIME RELOAD
#   - NO SCORING
#   - NO DECISION
#   - NO PREDICTION
#   - NO RANKING
#   - NO INTERPRETATION
#
# IMPORTANT:
# The runtime contract was verified:
#
# signal_engine.build_all() returns:
#
# {
#     "BTC": {
#         ...
#         "signal": {
#             "asset": "BTC",
#             "timestamp": None,
#             "signal_state": "ACTIVE",
#             "direction": "LONG",
#             "confidence": None,
#             "reason": "STRUCTURAL_DIRECTION"
#         }
#     },
#     ...
# }
#
# Therefore this validator consumes ONLY:
#
#   build_all()[asset]["signal"]
#
# It does NOT attempt to reconstruct regime state.
#
# =============================================================================


import signal_engine
import signal_contract


# =============================================================================
# CONSTANTS
# =============================================================================

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]

EXPECTED_ASSET_COUNT = 15

VALID_SIGNAL_STATES = {
    "ACTIVE",
    "NEUTRAL",
}

VALID_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 82)
    print("ARUNDA SIGNAL VALIDATOR v0.4")
    print("=" * 82)

    print(
        "Source   : signal_engine.build_all()[asset]['signal']"
    )

    print(
        "Contract : signal_contract.validate_signal()"
    )

    print(
        "Storage  : MEMORY ONLY"
    )

    print(
        "Writes   : NONE"
    )

    print(
        "SQL      : NOT USED"
    )

    print(
        "Regime   : NOT RELOADED"
    )

    print(
        "Scoring  : NOT USED"
    )

    print(
        "Decision : NOT USED"
    )

    print(
        "Prediction : NOT USED"
    )

    print(
        "Ranking  : NOT USED"
    )

    print(
        "Interpretation : NOT USED"
    )

    print("=" * 82)
    print()


# =============================================================================
# LOAD REAL SIGNAL ENGINE OUTPUT
# =============================================================================

def load_signal_snapshot():

    if not hasattr(
        signal_engine,
        "build_all"
    ):

        raise RuntimeError(
            "signal_engine.py must expose build_all()"
        )

    snapshot = signal_engine.build_all()

    if not isinstance(
        snapshot,
        dict
    ):

        raise RuntimeError(
            "signal_engine.build_all() must return dict"
        )

    return snapshot


# =============================================================================
# EXTRACT REAL SIGNAL
# =============================================================================

def extract_signal(
    asset,
    engine_record
):

    if not isinstance(
        engine_record,
        dict
    ):

        raise RuntimeError(
            f"Invalid engine record for {asset}"
        )

    if "signal" not in engine_record:

        raise RuntimeError(
            f"Missing signal field for {asset}"
        )

    signal = engine_record["signal"]

    if not isinstance(
        signal,
        dict
    ):

        raise RuntimeError(
            f"Invalid signal object for {asset}"
        )

    return signal


# =============================================================================
# VALIDATE ONE SIGNAL
# =============================================================================

def validate_one_signal(
    asset,
    signal
):

    if not isinstance(
        signal,
        dict
    ):

        return (
            False,
            "INVALID_OBJECT"
        )

    # -------------------------------------------------------------------------
    # ASSET IDENTITY
    # -------------------------------------------------------------------------

    if signal.get(
        "asset"
    ) != asset:

        return (
            False,
            "ASSET_MISMATCH"
        )

    # -------------------------------------------------------------------------
    # AUTHORITATIVE SIGNAL CONTRACT
    # -------------------------------------------------------------------------

    if not hasattr(
        signal_contract,
        "validate_signal"
    ):

        raise RuntimeError(
            "signal_contract.py must expose validate_signal()"
        )

    try:

        contract_valid = (
            signal_contract.validate_signal(
                signal
            )
        )

    except Exception as error:

        return (
            False,
            "SIGNAL_CONTRACT_ERROR:" +
            type(error).__name__
        )

    if not contract_valid:

        return (
            False,
            "SIGNAL_CONTRACT_INVALID"
        )

    # -------------------------------------------------------------------------
    # SIGNAL STATE
    # -------------------------------------------------------------------------

    signal_state = signal.get(
        "signal_state"
    )

    if signal_state not in VALID_SIGNAL_STATES:

        return (
            False,
            "UNKNOWN_SIGNAL_STATE"
        )

    # -------------------------------------------------------------------------
    # DIRECTION
    # -------------------------------------------------------------------------

    direction = signal.get(
        "direction"
    )

    if direction not in VALID_DIRECTIONS:

        return (
            False,
            "UNKNOWN_DIRECTION"
        )

    # -------------------------------------------------------------------------
    # STATE / DIRECTION CONSISTENCY
    # -------------------------------------------------------------------------

    if signal_state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT"
        ):

            return (
                False,
                "ACTIVE_WITHOUT_DIRECTION"
            )

    elif signal_state == "NEUTRAL":

        if direction != "NONE":

            return (
                False,
                "NEUTRAL_WITH_DIRECTION"
            )

    # -------------------------------------------------------------------------
    # VALID
    # -------------------------------------------------------------------------

    if signal_state == "ACTIVE":

        return (
            True,
            "VALID_ACTIVE"
        )

    return (
        True,
        "VALID_NEUTRAL"
    )


# =============================================================================
# BUILD VALIDATED SIGNAL SNAPSHOT
# =============================================================================

def load_validated_signals():

    engine_snapshot = (
        load_signal_snapshot()
    )

    # -------------------------------------------------------------------------
    # TOP-LEVEL ASSET CONTRACT
    # -------------------------------------------------------------------------

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        engine_snapshot.keys()
    )

    missing = (
        expected - actual
    )

    extra = (
        actual - expected
    )

    if missing:

        raise RuntimeError(
            "Missing assets: " +
            repr(sorted(missing))
        )

    if extra:

        raise RuntimeError(
            "Unexpected assets: " +
            repr(sorted(extra))
        )

    if len(engine_snapshot) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "Asset count mismatch: " +
            str(len(engine_snapshot))
        )

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    validated = {}

    for asset in EXPECTED_ASSETS:

        engine_record = (
            engine_snapshot[asset]
        )

        signal = extract_signal(
            asset,
            engine_record
        )

        valid, reason = (
            validate_one_signal(
                asset,
                signal
            )
        )

        validated[asset] = {
            "asset": asset,
            "signal_state":
                signal.get("signal_state"),
            "direction":
                signal.get("direction"),
            "valid":
                valid,
            "validation":
                reason,
        }

    return validated


# =============================================================================
# SNAPSHOT CONTRACT
# =============================================================================

def validate_snapshot(
    validated
):

    if not isinstance(
        validated,
        dict
    ):

        return False

    if len(validated) != EXPECTED_ASSET_COUNT:

        return False

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        validated.keys()
    )

    if expected != actual:

        return False

    required_fields = [
        "asset",
        "signal_state",
        "direction",
        "valid",
        "validation",
    ]

    for asset in EXPECTED_ASSETS:

        item = validated.get(
            asset
        )

        if not isinstance(
            item,
            dict
        ):

            return False

        for field in required_fields:

            if field not in item:

                return False

        if item["asset"] != asset:

            return False

        if item["signal_state"] not in (
            "ACTIVE",
            "NEUTRAL",
        ):

            return False

        if item["direction"] not in (
            "LONG",
            "SHORT",
            "NONE",
        ):

            return False

        if not isinstance(
            item["valid"],
            bool
        ):

            return False

        if not isinstance(
            item["validation"],
            str
        ):

            return False

    return True


# =============================================================================
# RESULTS
# =============================================================================

def print_results(
    validated
):

    print(
        "VALIDATED SIGNAL SNAPSHOT"
    )

    print("-" * 82)

    print(
        "Asset  | State   | Direction | Valid | Validation"
    )

    print("-" * 82)

    for asset in EXPECTED_ASSETS:

        item = validated[asset]

        print(
            "{:<6} | {:<7} | {:<9} | {:<5} | {}".format(
                asset,
                item["signal_state"],
                item["direction"],
                str(item["valid"]),
                item["validation"],
            )
        )

    print()


# =============================================================================
# CONTRACT SUMMARY
# =============================================================================

def print_contract(
    validated
):

    valid_count = 0
    invalid_count = 0

    active_count = 0
    neutral_count = 0

    for asset in EXPECTED_ASSETS:

        item = validated[asset]

        if item["valid"]:

            valid_count += 1

        else:

            invalid_count += 1

        if item["signal_state"] == "ACTIVE":

            active_count += 1

        elif item["signal_state"] == "NEUTRAL":

            neutral_count += 1

    snapshot_valid = (
        validate_snapshot(
            validated
        )
    )

    print("=" * 82)
    print("SIGNAL VALIDATION CONTRACT")
    print("=" * 82)

    print(
        "Expected Assets :",
        EXPECTED_ASSET_COUNT
    )

    print(
        "Validated       :",
        valid_count
    )

    print(
        "Invalid         :",
        invalid_count
    )

    print(
        "Active Signals  :",
        active_count
    )

    print(
        "Neutral Signals :",
        neutral_count
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "SQL             : NOT USED"
    )

    print(
        "Regime reload   : NOT USED"
    )

    print(
        "Scoring         : NOT USED"
    )

    print(
        "Decision        : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    if (
        snapshot_valid
        and invalid_count == 0
    ):

        print(
            "Contract Status : VALID"
        )

        return True

    print(
        "Contract Status : INVALID"
    )

    return False


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    try:

        validated = (
            load_validated_signals()
        )

        print_results(
            validated
        )

        valid = print_contract(
            validated
        )

        print()

        if valid:

            print(
                "SIGNAL VALIDATOR STATUS : READY"
            )

            return 0

        print(
            "SIGNAL VALIDATOR STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 82)
        print("SIGNAL VALIDATOR ERROR")
        print("=" * 82)

        print(
            "Type   :",
            type(error).__name__
        )

        print(
            "Error  :",
            str(error)
        )

        print()

        print(
            "SIGNAL VALIDATOR STATUS : FAILED"
        )

        return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )