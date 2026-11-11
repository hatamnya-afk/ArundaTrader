# =============================================================================
# ARUNDA SIGNAL CONTRACT v0.2
# Signal Schema + Semantic Contract
# HARDENED BOUNDARY VERSION
#
# STORAGE : MEMORY ONLY
# DATABASE: NOT USED
# WRITES  : NONE
# SQL     : NOT USED
# =============================================================================


# =============================================================================
# EXPECTED ASSETS
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


# =============================================================================
# ENUMS
# =============================================================================

SIGNAL_STATES = [
    "NEUTRAL",
    "ACTIVE",
]

DIRECTIONS = [
    "NONE",
    "LONG",
    "SHORT",
]


# =============================================================================
# SIGNAL SCHEMA
# =============================================================================

SIGNAL_FIELDS = [
    "asset",
    "timestamp",
    "signal_state",
    "direction",
    "confidence",
    "reason",
]


# =============================================================================
# INTERNAL CONSTANTS
# =============================================================================

ACTIVE_DIRECTIONS = {
    "LONG",
    "SHORT",
}

NEUTRAL_DIRECTION = "NONE"

ACTIVE_REASON = "STRUCTURAL_DIRECTION"


# =============================================================================
# BUILD EMPTY SIGNAL
# =============================================================================

def build_empty_signal(asset):

    # -------------------------------------------------------------------------
    # HARD TYPE BOUNDARY
    # -------------------------------------------------------------------------

    if not isinstance(asset, str):
        raise RuntimeError(
            "Unknown asset: asset must be a string"
        )

    # -------------------------------------------------------------------------
    # ASSET IDENTITY BOUNDARY
    # -------------------------------------------------------------------------

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            "Unknown asset: " + asset
        )

    # -------------------------------------------------------------------------
    # EMPTY SIGNAL
    # -------------------------------------------------------------------------

    return {
        "asset": asset,
        "timestamp": None,
        "signal_state": "NEUTRAL",
        "direction": "NONE",
        "confidence": None,
        "reason": None,
    }


# =============================================================================
# BUILD SIGNAL CONTRACT
# =============================================================================

def build_signal_contract():

    contract = {}

    for asset in EXPECTED_ASSETS:

        contract[asset] = build_empty_signal(
            asset
        )

    return contract


# =============================================================================
# VALIDATE SIGNAL
# =============================================================================

def validate_signal(signal):

    # =========================================================================
    # 01 — ROOT TYPE
    # =========================================================================

    if not isinstance(signal, dict):
        return False

    # =========================================================================
    # 02 — EXACT FIELD SET
    #
    # Missing fields -> REJECT
    # Extra fields   -> REJECT
    # =========================================================================

    if set(signal.keys()) != set(SIGNAL_FIELDS):
        return False

    # =========================================================================
    # 03 — ASSET
    # =========================================================================

    asset = signal["asset"]

    if not isinstance(asset, str):
        return False

    if asset not in EXPECTED_ASSETS:
        return False

    # =========================================================================
    # 04 — SIGNAL STATE TYPE
    # =========================================================================

    signal_state = signal["signal_state"]

    if not isinstance(signal_state, str):
        return False

    # =========================================================================
    # 05 — SIGNAL STATE ENUM
    # =========================================================================

    if signal_state not in SIGNAL_STATES:
        return False

    # =========================================================================
    # 06 — DIRECTION TYPE
    # =========================================================================

    direction = signal["direction"]

    if not isinstance(direction, str):
        return False

    # =========================================================================
    # 07 — DIRECTION ENUM
    # =========================================================================

    if direction not in DIRECTIONS:
        return False

    # =========================================================================
    # 08 — HARD SEMANTIC STATE/DIRECTION INVARIANT
    #
    # Only two valid combinations exist:
    #
    # ACTIVE  -> LONG
    # ACTIVE  -> SHORT
    #
    # NEUTRAL -> NONE
    #
    # Every other combination is INVALID.
    # =========================================================================

    if signal_state == "ACTIVE":

        if direction not in ACTIVE_DIRECTIONS:
            return False

    elif signal_state == "NEUTRAL":

        if direction != NEUTRAL_DIRECTION:
            return False

    else:

        # Defensive branch.
        # SIGNAL_STATES validation above should already catch this.
        return False

    # =========================================================================
    # 09 — CONFIDENCE
    #
    # Confidence is NOT calculated by the Signal layer at this stage.
    #
    # Allowed:
    #   None
    #   int/float within [0.0, 1.0]
    #
    # Forbidden:
    #   bool
    #   strings
    #   containers
    #   NaN
    #   +/- infinity
    # =========================================================================

    confidence = signal["confidence"]

    if confidence is not None:

        if isinstance(confidence, bool):
            return False

        if not isinstance(
            confidence,
            (int, float)
        ):
            return False

        try:
            if confidence != confidence:
                return False

            if confidence == float("inf"):
                return False

            if confidence == float("-inf"):
                return False

        except Exception:
            return False

        if confidence < 0.0:
            return False

        if confidence > 1.0:
            return False

    # =========================================================================
    # 10 — TIMESTAMP
    #
    # Signal layer does not generate timestamps.
    #
    # Allowed:
    #   None
    #   string
    #
    # No time-source logic is introduced here.
    # =========================================================================

    timestamp = signal["timestamp"]

    if timestamp is not None:

        if not isinstance(timestamp, str):
            return False

    # =========================================================================
    # 11 — REASON TYPE
    # =========================================================================

    reason = signal["reason"]

    if reason is not None:

        if not isinstance(reason, str):
            return False

    # =========================================================================
    # 12 — HARD REASON SEMANTIC INVARIANT
    #
    # ACTIVE:
    #     reason MUST be STRUCTURAL_DIRECTION
    #
    # NEUTRAL:
    #     reason MUST be None
    # =========================================================================

    if signal_state == "ACTIVE":

        if reason != ACTIVE_REASON:
            return False

    elif signal_state == "NEUTRAL":

        if reason is not None:
            return False

    else:

        return False

    # =========================================================================
    # 13 — FINAL SEMANTIC CROSS-CHECK
    #
    # This deliberately repeats the invariant at the final boundary.
    # It prevents future edits from accidentally weakening one branch.
    # =========================================================================

    valid_semantic_pairs = {
        ("ACTIVE", "LONG"),
        ("ACTIVE", "SHORT"),
        ("NEUTRAL", "NONE"),
    }

    if (
        signal_state,
        direction
    ) not in valid_semantic_pairs:
        return False

    # =========================================================================
    # 14 — FINAL REASON CROSS-CHECK
    # =========================================================================

    if signal_state == "ACTIVE":

        if reason != "STRUCTURAL_DIRECTION":
            return False

    if signal_state == "NEUTRAL":

        if direction != "NONE":
            return False

        if reason is not None:
            return False

    # =========================================================================
    # VALID
    # =========================================================================

    return True


# =============================================================================
# VALIDATE CONTRACT
# =============================================================================

def validate_signal_contract(contract):

    # =========================================================================
    # 01 — ROOT TYPE
    # =========================================================================

    if not isinstance(contract, dict):
        return False

    # =========================================================================
    # 02 — EXACT ASSET COUNT
    # =========================================================================

    if len(contract) != len(EXPECTED_ASSETS):
        return False

    # =========================================================================
    # 03 — EXACT ASSET SET
    # =========================================================================

    if set(contract.keys()) != set(EXPECTED_ASSETS):
        return False

    # =========================================================================
    # 04 — VALIDATE EACH SIGNAL
    # =========================================================================

    for asset in EXPECTED_ASSETS:

        if asset not in contract:
            return False

        signal = contract[asset]

        if not validate_signal(signal):
            return False

        # =====================================================================
        # IDENTITY INVARIANT
        # =====================================================================

        if signal["asset"] != asset:
            return False

    # =========================================================================
    # VALID
    # =========================================================================

    return True


# =============================================================================
# PUBLIC API
# =============================================================================

def load_signal_contract():

    return build_signal_contract()


# =============================================================================
# PRINT HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print("ARUNDA SIGNAL CONTRACT v0.2")
    print("=" * 78)

    print(
        "Purpose   : SIGNAL SCHEMA + SEMANTIC CONTRACT"
    )

    print(
        "Storage   : MEMORY ONLY"
    )

    print(
        "Writes    : NONE"
    )

    print(
        "SQL       : NOT USED"
    )

    print(
        "Signal    : SCHEMA + SEMANTIC VALIDATION"
    )

    print(
        "Scoring   : NOT USED"
    )

    print(
        "Prediction: NOT USED"
    )

    print(
        "Decision  : NOT USED"
    )

    print("=" * 78)
    print()


# =============================================================================
# PRINT SIGNAL SCHEMA
# =============================================================================

def print_schema():

    print(
        "SIGNAL SCHEMA"
    )

    print("-" * 78)

    print(
        "Fields:"
    )

    for field in SIGNAL_FIELDS:

        print(
            "  -",
            field
        )

    print()

    print(
        "Signal States :",
        ", ".join(SIGNAL_STATES)
    )

    print(
        "Directions    :",
        ", ".join(DIRECTIONS)
    )

    print()

    print(
        "Field Policy  : EXACT"
    )

    print(
        "Extra Fields  : REJECTED"
    )

    print(
        "Missing Fields: REJECTED"
    )

    print()


# =============================================================================
# PRINT CONTRACT
# =============================================================================

def print_contract(contract):

    valid = validate_signal_contract(
        contract
    )

    print("=" * 78)
    print("SIGNAL CONTRACT")
    print("=" * 78)

    print(
        "Expected Assets :",
        len(EXPECTED_ASSETS)
    )

    print(
        "Signal Fields   :",
        len(SIGNAL_FIELDS)
    )

    print(
        "Signal States   :",
        len(SIGNAL_STATES)
    )

    print(
        "Directions      :",
        len(DIRECTIONS)
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
        "Signal Engine   : NOT USED"
    )

    print(
        "Scoring         : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Decision        : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    print(
        "Extra fields    : REJECTED"
    )

    print(
        "Missing fields  : REJECTED"
    )

    print(
        "Semantic states : ENFORCED"
    )

    print(
        "Direction pairs : ENFORCED"
    )

    if valid:

        print(
            "Contract Status : VALID"
        )

    else:

        print(
            "Contract Status : INVALID"
        )

    print()

    return valid


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    try:

        print_schema()

        contract = load_signal_contract()

        valid = print_contract(
            contract
        )

        if valid:

            print(
                "SIGNAL CONTRACT STATUS : READY"
            )

            return 0

        print(
            "SIGNAL CONTRACT STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 78)
        print("SIGNAL CONTRACT ERROR")
        print("=" * 78)

        print(
            "Type  :",
            type(error).__name__
        )

        print(
            "Error :",
            str(error)
        )

        print()

        print(
            "SIGNAL CONTRACT STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )