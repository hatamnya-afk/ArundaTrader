"""
ARUNDA RISK ENGINE v0.1

Purpose:
    Apply the first structural risk gate to Decisions.

Architecture:
    Decision Engine
          ↓
    Risk Engine
          ↓
    Risk Contract

CP5 INTERFACE:
    decision_engine.run(...)
          ↓
    actual in-memory decision_snapshot
          ↓
    risk_engine.run(decision_snapshot)
          ↓
    risk_snapshot
          ↓
    risk_contract.validate_risk_snapshot()

Rules:
    - MEMORY ONLY
    - READ ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXECUTION
    - NO POSITION SIZING
    - NO STOP LOSS
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO PORTFOLIO EXPOSURE
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION

v0.1 Risk Logic:
    HOLD
        → NOT_APPLICABLE

    ACTIONABLE + LONG/SHORT
        → APPROVED

    Any inconsistent structure
        → BLOCKED
"""


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

EXPECTED_ASSET_COUNT = 15


# =============================================================================
# RISK CONTRACT VALUES
# =============================================================================

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


# =============================================================================
# NORMALIZE DECISION SNAPSHOT
# =============================================================================

def normalize_snapshot(data):
    """
    Convert supported Decision snapshot formats
    into an asset-keyed dictionary.

    CP5 accepts the actual in-memory Decision Snapshot
    produced by decision_engine.run().

    No reconstruction is performed.
    No database access is performed.
    """

    if not isinstance(data, dict):

        raise RuntimeError(
            "Decision snapshot must be a dictionary"
        )

    # -------------------------------------------------------------------------
    # Direct asset-keyed snapshot
    # -------------------------------------------------------------------------

    if all(
        key in EXPECTED_ASSETS
        for key in data.keys()
    ):

        return data

    # -------------------------------------------------------------------------
    # Wrapped snapshot support
    # -------------------------------------------------------------------------

    for wrapper in (
        "decisions",
        "decision_snapshot",
        "snapshot",
    ):

        value = data.get(wrapper)

        if isinstance(value, dict):

            if all(
                key in EXPECTED_ASSETS
                for key in value.keys()
            ):

                return value

    raise RuntimeError(
        "Unsupported Decision snapshot structure"
    )


# =============================================================================
# VALIDATE INPUT ASSETS
# =============================================================================

def validate_input_assets(snapshot):
    """
    Ensure exactly the expected 15 assets exist.
    """

    expected = set(EXPECTED_ASSETS)

    actual = set(snapshot.keys())

    missing = expected - actual

    extra = actual - expected

    if missing:

        raise RuntimeError(
            f"Decision snapshot missing assets: "
            f"{sorted(missing)}"
        )

    if extra:

        raise RuntimeError(
            f"Decision snapshot contains unexpected assets: "
            f"{sorted(extra)}"
        )


# =============================================================================
# DECISION STATE
# =============================================================================

def get_decision_state(record):
    """
    Extract Decision state.
    """

    if not isinstance(record, dict):

        raise RuntimeError(
            "Invalid Decision record"
        )

    state = record.get("state")

    if state is None:

        raise RuntimeError(
            "Decision record missing state"
        )

    return state


# =============================================================================
# DECISION DIRECTION
# =============================================================================

def get_direction(record):
    """
    Extract Decision direction.
    """

    if not isinstance(record, dict):

        raise RuntimeError(
            "Invalid Decision record"
        )

    direction = record.get("direction")

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid Decision direction: "
            f"{direction}"
        )

    return direction


# =============================================================================
# RISK EVALUATION
# =============================================================================

def evaluate_risk(asset, decision):
    """
    Apply the v0.1 structural Risk Gate.

    No numerical risk calculation is performed.

    Rules:

        HOLD + NONE
            → NOT_APPLICABLE

        ACTIONABLE + LONG
            → APPROVED

        ACTIONABLE + SHORT
            → APPROVED

        Everything else
            → BLOCKED
    """

    state = get_decision_state(
        decision
    )

    direction = get_direction(
        decision
    )


    # =========================================================================
    # HOLD
    # =========================================================================

    if state == "HOLD":

        if direction == "NONE":

            return {
                "asset": asset,
                "risk_state": "NOT_APPLICABLE",
                "direction": "NONE",
                "risk_score": None,
                "reason": "DECISION_HOLD",
            }

        return {
            "asset": asset,
            "risk_state": "BLOCKED",
            "direction": "NONE",
            "risk_score": None,
            "reason": "HOLD_DIRECTION_MISMATCH",
        }


    # =========================================================================
    # ACTIONABLE
    # =========================================================================

    if state == "ACTIONABLE":

        if direction in (
            "LONG",
            "SHORT",
        ):

            return {
                "asset": asset,
                "risk_state": "APPROVED",
                "direction": direction,
                "risk_score": None,
                "reason": "BASE_RISK_GATE_APPROVED",
            }

        return {
            "asset": asset,
            "risk_state": "BLOCKED",
            "direction": "NONE",
            "risk_score": None,
            "reason": "ACTIONABLE_DIRECTION_INVALID",
        }


    # =========================================================================
    # UNKNOWN / INVALID DECISION STATE
    # =========================================================================

    return {
        "asset": asset,
        "risk_state": "BLOCKED",
        "direction": "NONE",
        "risk_score": None,
        "reason": "UNKNOWN_DECISION_STATE",
    }


# =============================================================================
# BUILD RISK SNAPSHOT
# =============================================================================

def build_risk_snapshot(decisions):
    """
    Build the complete Risk snapshot.

    Input:
        Actual Decision Snapshot.

    Output:
        Asset-keyed Risk Snapshot.

    No Decision reconstruction occurs.
    """

    snapshot = normalize_snapshot(
        decisions
    )

    validate_input_assets(
        snapshot
    )

    risk_snapshot = {}

    for asset in EXPECTED_ASSETS:

        risk_snapshot[asset] = evaluate_risk(
            asset,
            snapshot[asset],
        )

    return risk_snapshot


# =============================================================================
# VALIDATE RISK SNAPSHOT
# =============================================================================

def validate_risk_snapshot(snapshot):
    """
    Validate the generated Risk snapshot
    against risk_contract.py.
    """

    import risk_contract

    if not hasattr(
        risk_contract,
        "validate_risk_snapshot",
    ):

        raise RuntimeError(
            "risk_contract.py must expose "
            "validate_risk_snapshot()"
        )

    return risk_contract.validate_risk_snapshot(
        snapshot
    )


# =============================================================================
# CP5 RUNTIME ENTRY
# =============================================================================

def run(decision_snapshot):
    """
    CP5 Risk Engine runtime entry point.

    Input:
        The ACTUAL in-memory Decision Snapshot
        produced by decision_engine.run().

    Output:
        Validated Risk Snapshot.

    Important:
        This function does NOT load signals.
        This function does NOT load scores.
        This function does NOT rebuild decisions.
        This function does NOT access the database.
        This function does NOT use subprocess transport.
    """

    # -------------------------------------------------------------------------
    # Input type
    # -------------------------------------------------------------------------

    if not isinstance(
        decision_snapshot,
        dict,
    ):

        raise RuntimeError(
            "Risk Engine requires an in-memory "
            "Decision Snapshot dictionary"
        )


    # -------------------------------------------------------------------------
    # Build Risk Snapshot
    # -------------------------------------------------------------------------

    risk_snapshot = build_risk_snapshot(
        decision_snapshot
    )


    # -------------------------------------------------------------------------
    # Validate Risk Contract
    # -------------------------------------------------------------------------

    contract_result = validate_risk_snapshot(
        risk_snapshot
    )

    if not isinstance(
        contract_result,
        dict,
    ):

        raise RuntimeError(
            "Risk contract validation returned "
            "an invalid result"
        )


    if contract_result.get(
        "contract_status"
    ) != "VALID":

        raise RuntimeError(
            "RISK SNAPSHOT CONTRACT FAILED"
        )


    # -------------------------------------------------------------------------
    # Return actual Risk Snapshot
    # -------------------------------------------------------------------------

    return risk_snapshot


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 77)
    print("ARUNDA RISK ENGINE v0.1")
    print("=" * 77)

    print(
        "Source   : decision_snapshot"
    )

    print(
        "Contract : risk_contract"
    )

    print(
        "Transport: IN-PROCESS MEMORY"
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
        "Position Sizing : NOT USED"
    )

    print(
        "Stop Loss       : NOT USED"
    )

    print(
        "Take Profit     : NOT USED"
    )

    print(
        "Leverage        : NOT USED"
    )

    print(
        "Portfolio Risk  : NOT USED"
    )

    print(
        "Execution       : NOT USED"
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

    print("=" * 77)


# =============================================================================
# PRINT RISK RESULTS
# =============================================================================

def print_results(snapshot):
    """
    Print the Risk snapshot.
    """

    print()
    print("RISK SNAPSHOT")
    print("-" * 77)

    print(
        "Asset  | Risk State      | Direction | Risk Score | Reason"
    )

    print("-" * 77)

    for asset in EXPECTED_ASSETS:

        risk = snapshot[asset]

        score = risk["risk_score"]

        score_text = (
            "NONE"
            if score is None
            else f"{score:.5f}"
        )

        print(
            f"{asset:<6} | "
            f"{risk['risk_state']:<15} | "
            f"{risk['direction']:<9} | "
            f"{score_text:<10} | "
            f"{risk['reason']}"
        )


# =============================================================================
# PRINT CONTRACT SUMMARY
# =============================================================================

def print_contract(snapshot):
    """
    Print Risk Engine contract summary.
    """

    approved = sum(
        1
        for record in snapshot.values()
        if record["risk_state"] == "APPROVED"
    )

    blocked = sum(
        1
        for record in snapshot.values()
        if record["risk_state"] == "BLOCKED"
    )

    not_applicable = sum(
        1
        for record in snapshot.values()
        if record["risk_state"]
        == "NOT_APPLICABLE"
    )

    long_count = sum(
        1
        for record in snapshot.values()
        if record["direction"] == "LONG"
    )

    short_count = sum(
        1
        for record in snapshot.values()
        if record["direction"] == "SHORT"
    )

    none_count = sum(
        1
        for record in snapshot.values()
        if record["direction"] == "NONE"
    )

    print()
    print("=" * 77)
    print("RISK ENGINE CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Ready Assets    : "
        f"{len(snapshot)}"
    )

    print(
        f"Approved        : "
        f"{approved}"
    )

    print(
        f"Blocked         : "
        f"{blocked}"
    )

    print(
        f"Not Applicable  : "
        f"{not_applicable}"
    )

    print(
        f"LONG            : "
        f"{long_count}"
    )

    print(
        f"SHORT           : "
        f"{short_count}"
    )

    print(
        f"NONE            : "
        f"{none_count}"
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
        "Position Sizing : NOT USED"
    )

    print(
        "Stop Loss       : NOT USED"
    )

    print(
        "Take Profit     : NOT USED"
    )

    print(
        "Leverage        : NOT USED"
    )

    print(
        "Portfolio Risk  : NOT USED"
    )

    print(
        "Execution       : NOT USED"
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

    print(
        "Contract Status : VALID"
    )

    print("=" * 77)


# =============================================================================
# STANDALONE MAIN
# =============================================================================

def main(
    decision_snapshot=None
):
    """
    Standalone entry point.

    CP5 production path MUST call:

        risk_engine.run(decision_snapshot)

    This standalone main intentionally does not attempt
    to reconstruct a Decision Snapshot.
    """

    print_header()

    try:

        if decision_snapshot is None:

            raise RuntimeError(
                "risk_engine.py requires an in-memory "
                "Decision Snapshot from the production pipeline"
            )


        risk_snapshot = run(
            decision_snapshot
        )


        print_results(
            risk_snapshot
        )


        print_contract(
            risk_snapshot
        )


        print()
        print(
            "RISK ENGINE STATUS : READY"
        )

        return risk_snapshot


    except Exception as exc:

        print()
        print("=" * 77)
        print("RISK ENGINE ERROR")
        print("=" * 77)

        print(
            f"Type   : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error  : {exc}"
        )

        print()

        print(
            "RISK ENGINE STATUS : FAILED"
        )

        print("=" * 77)

        raise


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    # -------------------------------------------------------------------------
    # Direct standalone execution is intentionally blocked because the Risk
    # Engine requires the real in-memory Decision Snapshot.
    #
    # Production pipeline must call:
    #
    #     risk_engine.run(decision_snapshot)
    #
    # -------------------------------------------------------------------------

    raise SystemExit(
        "RISK ENGINE REQUIRES IN-MEMORY "
        "DECISION SNAPSHOT FROM PRODUCTION PIPELINE"
    )