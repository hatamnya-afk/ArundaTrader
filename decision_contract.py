"""
ARUNDA DECISION CONTRACT v0.1

Purpose:
    Define the formal structure of the Decision layer.

Rules:
    - MEMORY ONLY
    - READ ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO DECISION ENGINE YET
    - NO EXECUTION
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION
"""

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

DECISION_STATES = (
    "ACTIONABLE",
    "HOLD",
    "REJECT",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

DECISION_FIELDS = (
    "asset",
    "state",
    "direction",
    "score",
    "reason",
)


def build_empty_decision(asset):
    """
    Create the formal Decision structure.

    This function DOES NOT make a trading decision.
    It only defines the contract shape.
    """

    if asset not in EXPECTED_ASSETS:
        raise ValueError(f"Unknown asset: {asset}")

    return {
        "asset": asset,
        "state": "HOLD",
        "direction": "NONE",
        "score": None,
        "reason": None,
    }


def validate_decision(decision):
    """
    Validate one Decision object against the contract.

    This function does not interpret or modify the decision.
    """

    if not isinstance(decision, dict):
        raise RuntimeError("Decision must be a dictionary")

    missing = [
        field
        for field in DECISION_FIELDS
        if field not in decision
    ]

    if missing:
        raise RuntimeError(
            f"Missing decision fields: {missing}"
        )

    asset = decision["asset"]

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"Invalid asset: {asset}"
        )

    state = decision["state"]

    if state not in DECISION_STATES:
        raise RuntimeError(
            f"Invalid decision state for {asset}: {state}"
        )

    direction = decision["direction"]

    if direction not in DIRECTIONS:
        raise RuntimeError(
            f"Invalid direction for {asset}: {direction}"
        )

    score = decision["score"]

    if score is not None:
        if isinstance(score, bool):
            raise RuntimeError(
                f"Invalid score type for {asset}"
            )

        if not isinstance(score, (int, float)):
            raise RuntimeError(
                f"Invalid score for {asset}: {score!r}"
            )

    reason = decision["reason"]

    if reason is not None and not isinstance(reason, str):
        raise RuntimeError(
            f"Invalid reason for {asset}"
        )

    return True


def validate_decision_snapshot(snapshot):
    """
    Validate a complete Decision snapshot.

    Expected structure:

        {
            "BTC": {...},
            "ETH": {...},
            ...
        }
    """

    if not isinstance(snapshot, dict):
        raise RuntimeError(
            "Decision snapshot must be a dictionary"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(snapshot.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            f"Missing assets: {sorted(missing)}"
        )

    if extra:
        raise RuntimeError(
            f"Unexpected assets: {sorted(extra)}"
        )

    for asset in EXPECTED_ASSETS:
        validate_decision(snapshot[asset])

    return {
        "expected_assets": EXPECTED_ASSET_COUNT,
        "validated_assets": len(snapshot),
        "decision_states": len(DECISION_STATES),
        "directions": len(DIRECTIONS),
        "contract_status": "VALID",
    }


def print_header():
    print("=" * 77)
    print("ARUNDA DECISION CONTRACT v0.1")
    print("=" * 77)
    print("Source   : validated signal + score")
    print("Storage  : MEMORY ONLY")
    print("Writes   : NONE")
    print("SQL      : NOT USED")
    print("Execution: NOT USED")
    print("Prediction: NOT USED")
    print("Ranking  : NOT USED")
    print("Interpretation : NOT USED")
    print("=" * 77)


def print_contract():
    print()
    print("=" * 77)
    print("DECISION CONTRACT")
    print("=" * 77)
    print(
        f"Expected Assets : {EXPECTED_ASSET_COUNT}"
    )
    print(
        f"Decision Fields : {len(DECISION_FIELDS)}"
    )
    print(
        f"Decision States : {len(DECISION_STATES)}"
    )
    print(
        "States          : "
        + " / ".join(DECISION_STATES)
    )
    print(
        "Directions      : "
        + " / ".join(DIRECTIONS)
    )
    print("Storage         : MEMORY ONLY")
    print("Database writes : NONE")
    print("SQL             : NOT USED")
    print("Signal Engine   : NOT USED")
    print("Scoring         : INPUT ONLY")
    print("Execution       : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")
    print("Contract Status : VALID")
    print("=" * 77)


def main():
    print_header()

    try:
        # Contract-only validation.
        # No real decision is generated here.

        for asset in EXPECTED_ASSETS:
            decision = build_empty_decision(asset)
            validate_decision(decision)

        print_contract()

        print()
        print("DECISION CONTRACT STATUS : READY")

        return 0

    except Exception as exc:
        print()
        print("=" * 77)
        print("DECISION CONTRACT ERROR")
        print("=" * 77)
        print(f"Type   : {type(exc).__name__}")
        print(f"Error  : {exc}")
        print()
        print("DECISION CONTRACT STATUS : FAILED")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())