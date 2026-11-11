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

    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("Asset must be a non-empty string")
    asset = asset.strip().upper()

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

    if not isinstance(asset, str) or not asset.strip():
        raise RuntimeError("Invalid asset")
    asset = asset.strip().upper()

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
    Validate a complete dynamic Decision snapshot.

    The contract validates the assets actually present in the snapshot;
    it does not impose a fixed universe or cardinality.
    """
    if not isinstance(snapshot, dict):
        raise RuntimeError("Decision snapshot must be a dictionary")

    actual = set()
    for key, decision in snapshot.items():
        if not isinstance(key, str) or not key.strip():
            raise RuntimeError("Decision snapshot contains invalid asset key")
        asset = key.strip().upper()
        if asset in actual:
            raise RuntimeError(f"Duplicate normalized asset: {asset}")
        actual.add(asset)
        if not isinstance(decision, dict):
            raise RuntimeError(f"Invalid decision object: {asset}")
        row_asset = decision.get("asset")
        if not isinstance(row_asset, str) or row_asset.strip().upper() != asset:
            raise RuntimeError(f"Decision asset mismatch: {asset}")
        validate_decision(decision)

    if not actual:
        raise RuntimeError("Decision snapshot must contain at least one asset")

    return {
        "observed_assets": sorted(actual),
        "observed_asset_count": len(actual),
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
        "Asset Universe   : DYNAMIC (observed input)"
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

        sample_asset = "BTC"
        decision = build_empty_decision(sample_asset)
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