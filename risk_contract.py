"""
ARUNDA RISK CONTRACT v0.1

Purpose:
    Define the formal structure of the Risk layer.

Architecture:
    Decision
        ↓
    Risk Contract
        ↓
    Risk Engine (next layer)

Rules:
    - MEMORY ONLY
    - READ ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXECUTION
    - NO ORDER CREATION
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION
    - NO POSITION SIZING YET
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

RISK_STATES = (
    "APPROVED",
    "BLOCKED",
    "NOT_APPLICABLE",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

RISK_FIELDS = (
    "asset",
    "risk_state",
    "direction",
    "risk_score",
    "reason",
)


def build_empty_risk(asset):
    """
    Create an empty Risk structure.

    This function does NOT calculate risk.
    It only defines the contract shape.
    """

    if asset not in EXPECTED_ASSETS:
        raise ValueError(
            f"Unknown asset: {asset}"
        )

    return {
        "asset": asset,
        "risk_state": "NOT_APPLICABLE",
        "direction": "NONE",
        "risk_score": None,
        "reason": None,
    }


def validate_risk(risk):
    """
    Validate one Risk object against the contract.

    This function does not calculate or interpret risk.
    """

    if not isinstance(risk, dict):
        raise RuntimeError(
            "Risk must be a dictionary"
        )

    missing = [
        field
        for field in RISK_FIELDS
        if field not in risk
    ]

    if missing:
        raise RuntimeError(
            f"Missing risk fields: {missing}"
        )

    asset = risk["asset"]

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"Invalid asset: {asset}"
        )

    risk_state = risk["risk_state"]

    if risk_state not in RISK_STATES:
        raise RuntimeError(
            f"Invalid risk state for {asset}: "
            f"{risk_state}"
        )

    direction = risk["direction"]

    if direction not in DIRECTIONS:
        raise RuntimeError(
            f"Invalid direction for {asset}: "
            f"{direction}"
        )

    risk_score = risk["risk_score"]

    if risk_score is not None:

        if isinstance(risk_score, bool):
            raise RuntimeError(
                f"Invalid risk score type for {asset}"
            )

        if not isinstance(
            risk_score,
            (int, float)
        ):
            raise RuntimeError(
                f"Invalid risk score for {asset}: "
                f"{risk_score!r}"
            )

    reason = risk["reason"]

    if reason is not None:

        if not isinstance(reason, str):
            raise RuntimeError(
                f"Invalid risk reason for {asset}"
            )

    return True


def validate_risk_snapshot(snapshot):
    """
    Validate a complete Risk snapshot.

    Expected structure:

        {
            "BTC": {...},
            "ETH": {...},
            ...
        }
    """

    if not isinstance(snapshot, dict):
        raise RuntimeError(
            "Risk snapshot must be a dictionary"
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
        validate_risk(snapshot[asset])

    approved = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["risk_state"]
        == "APPROVED"
    )

    blocked = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["risk_state"]
        == "BLOCKED"
    )

    not_applicable = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["risk_state"]
        == "NOT_APPLICABLE"
    )

    return {
        "expected_assets": EXPECTED_ASSET_COUNT,
        "validated_assets": len(snapshot),
        "approved": approved,
        "blocked": blocked,
        "not_applicable": not_applicable,
        "contract_status": "VALID",
    }


def print_header():
    print("=" * 77)
    print("ARUNDA RISK CONTRACT v0.1")
    print("=" * 77)
    print("Source   : decision_engine")
    print("Storage  : MEMORY ONLY")
    print("Writes   : NONE")
    print("SQL      : NOT USED")
    print("Execution: NOT USED")
    print("Position Sizing : NOT USED")
    print("Stop Loss       : NOT USED")
    print("Take Profit     : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")
    print("=" * 77)


def print_contract():
    print()
    print("=" * 77)
    print("RISK CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Risk Fields     : "
        f"{len(RISK_FIELDS)}"
    )

    print(
        f"Risk States     : "
        f"{len(RISK_STATES)}"
    )

    print(
        "States          : "
        + " / ".join(RISK_STATES)
    )

    print(
        "Directions      : "
        + " / ".join(DIRECTIONS)
    )

    print("Storage         : MEMORY ONLY")
    print("Database writes : NONE")
    print("SQL             : NOT USED")
    print("Decision Engine : INPUT ONLY")
    print("Position Sizing : NOT USED")
    print("Stop Loss       : NOT USED")
    print("Take Profit     : NOT USED")
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
        # No real risk calculation occurs here.

        for asset in EXPECTED_ASSETS:

            risk = build_empty_risk(asset)

            validate_risk(risk)

        print_contract()

        print()
        print("RISK CONTRACT STATUS : READY")

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("RISK CONTRACT ERROR")
        print("=" * 77)

        print(
            f"Type   : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error  : {exc}"
        )

        print()
        print("RISK CONTRACT STATUS : FAILED")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())