"""
ARUNDA RISK BUDGET ENGINE v0.5

Purpose:
    Convert approved Risk states into formal
    monetary Risk Budget allocations.

Architecture:

    Decision Engine
          ↓
    Risk Engine
          ↓
    Risk Budget Engine
          ↓
    Position Sizing Engine

Rules:
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXECUTION
    - NO STOP LOSS
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO POSITION SIZING
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION

Capital:
    CAPITAL × RISK_PER_TRADE

Current configuration example:

    Capital = 1,000,000
    Risk Per Trade = 0.005
    Risk Budget = 5,000

Portfolio example:

    Max Portfolio Risk = 10,000
    Max Concurrent Positions = 2

IMPORTANT:
    This engine allocates monetary risk only.
    It does NOT calculate position size.
    It does NOT calculate exposure.
    It does NOT execute orders.
"""


# ============================================================================
# IMPORTS
# ============================================================================

import capital_config
import risk_engine

from risk_budget_contract import (
    EXPECTED_ASSETS,
    validate_budget_snapshot,
)


# ============================================================================
# CONSTANTS
# ============================================================================

EXPECTED_ASSET_COUNT = 15

RISK_STATES = (
    "APPROVED",
    "BLOCKED",
    "NOT_APPLICABLE",
)

BUDGET_STATES = (
    "ALLOCATED",
    "UNALLOCATED",
    "BLOCKED",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)


# ============================================================================
# CAPITAL
# ============================================================================

def load_capital_config():
    """
    Load validated capital configuration.
    """

    loader = getattr(
        capital_config,
        "get_config",
        None,
    )

    if not callable(loader):
        raise RuntimeError(
            "capital_config.py must expose get_config()"
        )

    config = loader()

    if not isinstance(config, dict):
        raise RuntimeError(
            "Capital configuration must be a dictionary"
        )

    required_fields = (
        "capital",
        "available_capital",
        "risk_per_trade",
        "max_portfolio_risk",
        "max_concurrent_positions",
    )

    for field in required_fields:

        if field not in config:
            raise RuntimeError(
                "Capital configuration missing field: "
                f"{field}"
            )

    capital = float(
        config["capital"]
    )

    available_capital = float(
        config["available_capital"]
    )

    risk_per_trade = float(
        config["risk_per_trade"]
    )

    max_portfolio_risk = float(
        config["max_portfolio_risk"]
    )

    max_concurrent_positions = int(
        config["max_concurrent_positions"]
    )

    if capital <= 0:
        raise RuntimeError(
            "Capital must be greater than zero"
        )

    if available_capital < 0:
        raise RuntimeError(
            "Available capital cannot be negative"
        )

    if available_capital > capital:
        raise RuntimeError(
            "Available capital cannot exceed capital"
        )

    if risk_per_trade <= 0:
        raise RuntimeError(
            "Risk per trade must be greater than zero"
        )

    if max_portfolio_risk <= 0:
        raise RuntimeError(
            "Maximum portfolio risk must be greater than zero"
        )

    if max_concurrent_positions <= 0:
        raise RuntimeError(
            "Maximum concurrent positions must be greater than zero"
        )

    return config


# ============================================================================
# RISK SNAPSHOT
# ============================================================================

def load_risk_snapshot():
    """
    Load the authoritative Risk snapshot.

    Authority:
        risk_engine

    API:
        risk_engine.load_decisions()
        risk_engine.build_risk_snapshot()
    """

    decision_loader = getattr(
        risk_engine,
        "load_decisions",
        None,
    )

    if not callable(decision_loader):
        raise RuntimeError(
            "risk_engine.py must expose load_decisions()"
        )

    risk_builder = getattr(
        risk_engine,
        "build_risk_snapshot",
        None,
    )

    if not callable(risk_builder):
        raise RuntimeError(
            "risk_engine.py must expose "
            "build_risk_snapshot()"
        )

    decisions = decision_loader()

    risk_snapshot = risk_builder(
        decisions
    )

    if not isinstance(
        risk_snapshot,
        dict,
    ):
        raise RuntimeError(
            "Risk snapshot must be a dictionary"
        )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        risk_snapshot.keys()
    )

    missing = expected - actual

    extra = actual - expected

    if missing:
        raise RuntimeError(
            "Risk snapshot missing assets: "
            + ", ".join(
                sorted(missing)
            )
        )

    if extra:
        raise RuntimeError(
            "Risk snapshot contains unexpected assets: "
            + ", ".join(
                sorted(extra)
            )
        )

    return risk_snapshot


# ============================================================================
# RISK INPUT VALIDATION
# ============================================================================

def validate_risk_input(
    risk_snapshot,
):
    """
    Validate Risk snapshot using risk_engine's
    own validation interface.

    Compatible with validators returning:

        True

    or:

        {
            ...
            "contract_status": "VALID"
        }
    """

    validator = getattr(
        risk_engine,
        "validate_risk_snapshot",
        None,
    )

    if not callable(validator):
        raise RuntimeError(
            "risk_engine.py must expose "
            "validate_risk_snapshot()"
        )

    result = validator(
        risk_snapshot
    )

    # ------------------------------------------------------------------------
    # VALID
    # ------------------------------------------------------------------------

    if result is True:
        return True

    # ------------------------------------------------------------------------
    # VALID SUMMARY
    # ------------------------------------------------------------------------

    if isinstance(
        result,
        dict,
    ):

        status = result.get(
            "contract_status"
        )

        if status == "VALID":
            return True

        # Some contracts use validation_status.
        validation_status = result.get(
            "validation_status"
        )

        if validation_status == "VALID":
            return True

    # ------------------------------------------------------------------------
    # INVALID
    # ------------------------------------------------------------------------

    raise RuntimeError(
        "Risk snapshot validation failed"
    )


# ============================================================================
# RISK BUDGET CALCULATION
# ============================================================================

def calculate_risk_budget(
    capital_config,
):
    """
    Calculate monetary risk budget per approved trade.

    Formula:

        Risk Budget =
            Capital × Risk Per Trade
    """

    capital = float(
        capital_config["capital"]
    )

    risk_per_trade = float(
        capital_config["risk_per_trade"]
    )

    budget = (
        capital
        * risk_per_trade
    )

    if budget <= 0:
        raise RuntimeError(
            "Calculated risk budget must be greater than zero"
        )

    return budget


# ============================================================================
# MAX PORTFOLIO RISK
# ============================================================================

def calculate_max_portfolio_risk_amount(
    capital_config,
):
    """
    Calculate maximum monetary portfolio risk.

    Formula:

        Capital × Max Portfolio Risk
    """

    capital = float(
        capital_config["capital"]
    )

    max_portfolio_risk = float(
        capital_config["max_portfolio_risk"]
    )

    amount = (
        capital
        * max_portfolio_risk
    )

    if amount <= 0:
        raise RuntimeError(
            "Maximum portfolio risk amount "
            "must be greater than zero"
        )

    return amount


# ============================================================================
# ALLOCATE ONE ASSET
# ============================================================================

def allocate_budget(
    asset,
    risk,
    risk_budget,
):
    """
    Convert one Risk record into one
    Risk Budget record.
    """

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"Unknown asset: {asset}"
        )

    if not isinstance(
        risk,
        dict,
    ):
        raise RuntimeError(
            f"Invalid Risk record for {asset}"
        )

    risk_state = risk.get(
        "risk_state"
    )

    direction = risk.get(
        "direction"
    )

    if risk_state not in RISK_STATES:
        raise RuntimeError(
            f"Invalid Risk state for {asset}: "
            f"{risk_state}"
        )

    if direction not in DIRECTIONS:
        raise RuntimeError(
            f"Invalid Risk direction for {asset}: "
            f"{direction}"
        )

    # ------------------------------------------------------------------------
    # APPROVED
    # ------------------------------------------------------------------------

    if risk_state == "APPROVED":

        if direction in (
            "LONG",
            "SHORT",
        ):

            return {
                "asset": asset,
                "budget_state": "ALLOCATED",
                "direction": direction,
                "risk_budget": float(
                    risk_budget
                ),
                "reason": "RISK_APPROVED",
            }

        return {
            "asset": asset,
            "budget_state": "BLOCKED",
            "direction": "NONE",
            "risk_budget": None,
            "reason": "APPROVED_DIRECTION_INVALID",
        }

    # ------------------------------------------------------------------------
    # NOT APPLICABLE
    # ------------------------------------------------------------------------

    if risk_state == "NOT_APPLICABLE":

        return {
            "asset": asset,
            "budget_state": "UNALLOCATED",
            "direction": "NONE",
            "risk_budget": None,
            "reason": "RISK_NOT_APPLICABLE",
        }

    # ------------------------------------------------------------------------
    # BLOCKED
    # ------------------------------------------------------------------------

    if risk_state == "BLOCKED":

        return {
            "asset": asset,
            "budget_state": "BLOCKED",
            "direction": "NONE",
            "risk_budget": None,
            "reason": risk.get(
                "reason",
                "RISK_BLOCKED",
            ),
        }

    # ------------------------------------------------------------------------
    # UNKNOWN
    # ------------------------------------------------------------------------

    return {
        "asset": asset,
        "budget_state": "BLOCKED",
        "direction": "NONE",
        "risk_budget": None,
        "reason": "UNKNOWN_RISK_STATE",
    }


# ============================================================================
# BUILD BUDGET SNAPSHOT
# ============================================================================

def build_budget_snapshot(
    risk_snapshot,
    capital_config,
):
    """
    Build complete Risk Budget snapshot.

    Portfolio rules:

        1. Each approved trade receives
           one risk budget.

        2. Total allocated risk cannot exceed
           max portfolio risk.

        3. Concurrent positions cannot exceed
           max concurrent positions.

    Allocation order follows EXPECTED_ASSETS.
    """

    if not isinstance(
        risk_snapshot,
        dict,
    ):
        raise RuntimeError(
            "Risk snapshot must be a dictionary"
        )

    risk_budget = calculate_risk_budget(
        capital_config
    )

    max_portfolio_risk_amount = (
        calculate_max_portfolio_risk_amount(
            capital_config
        )
    )

    max_positions = int(
        capital_config[
            "max_concurrent_positions"
        ]
    )

    if max_positions <= 0:
        raise RuntimeError(
            "Maximum concurrent positions "
            "must be greater than zero"
        )

    # ------------------------------------------------------------------------
    # Find approved candidates.
    # ------------------------------------------------------------------------

    approved_assets = []

    for asset in EXPECTED_ASSETS:

        risk = risk_snapshot[
            asset
        ]

        if not isinstance(
            risk,
            dict,
        ):
            raise RuntimeError(
                f"Invalid Risk record for {asset}"
            )

        if (
            risk.get("risk_state")
            == "APPROVED"
            and
            risk.get("direction")
            in ("LONG", "SHORT")
        ):

            approved_assets.append(
                asset
            )

    # ------------------------------------------------------------------------
    # Calculate capacity.
    # ------------------------------------------------------------------------

    portfolio_capacity = int(
        max_portfolio_risk_amount
        // risk_budget
    )

    allowed_count = min(
        len(approved_assets),
        max_positions,
        portfolio_capacity,
    )

    # ------------------------------------------------------------------------
    # Build snapshot.
    # ------------------------------------------------------------------------

    snapshot = {}

    allocated_count = 0

    for asset in EXPECTED_ASSETS:

        risk = risk_snapshot[
            asset
        ]

        is_approved = (
            risk.get("risk_state")
            == "APPROVED"
            and
            risk.get("direction")
            in ("LONG", "SHORT")
        )

        if is_approved:

            if allocated_count < allowed_count:

                snapshot[asset] = (
                    allocate_budget(
                        asset=asset,
                        risk=risk,
                        risk_budget=risk_budget,
                    )
                )

                allocated_count += 1

            else:

                snapshot[asset] = {
                    "asset": asset,
                    "budget_state": "BLOCKED",
                    "direction": "NONE",
                    "risk_budget": None,
                    "reason": (
                        "PORTFOLIO_RISK_CAPACITY_EXCEEDED"
                    ),
                }

        else:

            snapshot[asset] = (
                allocate_budget(
                    asset=asset,
                    risk=risk,
                    risk_budget=risk_budget,
                )
            )

    # ------------------------------------------------------------------------
    # Final structural checks.
    # ------------------------------------------------------------------------

    if len(snapshot) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Risk Budget snapshot must contain "
            f"{EXPECTED_ASSET_COUNT} assets"
        )

    total_allocated_risk = sum(
        float(
            record["risk_budget"]
        )
        for record in snapshot.values()
        if (
            record["budget_state"]
            == "ALLOCATED"
            and
            record["risk_budget"] is not None
        )
    )

    if (
        total_allocated_risk
        > max_portfolio_risk_amount + 1e-12
    ):
        raise RuntimeError(
            "Allocated risk exceeds maximum "
            "portfolio risk"
        )

    if allocated_count > max_positions:
        raise RuntimeError(
            "Allocated positions exceed "
            "maximum concurrent positions"
        )

    return snapshot


# ============================================================================
# BUDGET VALIDATION
# ============================================================================

def validate_budget(
    snapshot,
):
    """
    Validate Risk Budget snapshot against
    risk_budget_contract.py.

    Compatible with validators returning:

        True

    or:

        validation summary dictionary.
    """

    validator = validate_budget_snapshot

    if not callable(validator):
        raise RuntimeError(
            "risk_budget_contract.py must expose "
            "validate_budget_snapshot()"
        )

    result = validator(
        snapshot
    )

    # ------------------------------------------------------------------------
    # VALID
    # ------------------------------------------------------------------------

    if result is True:
        return True

    # ------------------------------------------------------------------------
    # VALID SUMMARY
    # ------------------------------------------------------------------------

    if isinstance(
        result,
        dict,
    ):

        status = result.get(
            "contract_status"
        )

        if status == "VALID":
            return True

        validation_status = result.get(
            "validation_status"
        )

        if validation_status == "VALID":
            return True

    # ------------------------------------------------------------------------
    # INVALID
    # ------------------------------------------------------------------------

    raise RuntimeError(
        "Risk Budget snapshot validation failed"
    )


# ============================================================================
# PUBLIC SNAPSHOT
# ============================================================================

def calculate_snapshot():
    """
    Public API.

    Returns:

        {
            "capital": {...},
            "risk_budget": 5000.0,
            "max_portfolio_risk": 10000.0,
            "budgets": {
                "BTC": {...},
                ...
            }
        }
    """

    capital = load_capital_config()

    risk_snapshot = load_risk_snapshot()

    validate_risk_input(
        risk_snapshot
    )

    budgets = build_budget_snapshot(
        risk_snapshot,
        capital,
    )

    validate_budget(
        budgets
    )

    return {
        "capital": capital,
        "risk_budget": calculate_risk_budget(
            capital
        ),
        "max_portfolio_risk": (
            calculate_max_portfolio_risk_amount(
                capital
            )
        ),
        "budgets": budgets,
    }


# ============================================================================
# PRINT HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print(
        "ARUNDA RISK BUDGET ENGINE v0.5"
    )
    print("=" * 77)

    print(
        "Source   : risk_engine + capital_config"
    )

    print(
        "Purpose  : RISK BUDGET ALLOCATION"
    )

    print(
        "Contract : risk_budget_contract"
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
        "Capital Calculation : USED"
    )

    print(
        "Risk Budget Value   : USED"
    )

    print(
        "Risk Amount         : CAPITAL × RISK PER TRADE"
    )

    print(
        "Position Sizing     : NOT USED"
    )

    print(
        "Stop Loss           : NOT USED"
    )

    print(
        "Take Profit         : NOT USED"
    )

    print(
        "Leverage            : NOT USED"
    )

    print(
        "Portfolio Risk      : LIMIT CHECK ONLY"
    )

    print(
        "Execution           : NOT USED"
    )

    print(
        "Prediction          : NOT USED"
    )

    print(
        "Ranking             : NOT USED"
    )

    print(
        "Interpretation      : NOT USED"
    )

    print("=" * 77)


# ============================================================================
# PRINT RESULTS
# ============================================================================

def print_results(
    snapshot,
):

    print()
    print(
        "RISK BUDGET SNAPSHOT"
    )

    print("-" * 77)

    print(
        "Asset  | Budget State | Direction | "
        "Risk Budget | Reason"
    )

    print("-" * 77)

    for asset in EXPECTED_ASSETS:

        record = snapshot[
            asset
        ]

        budget = record[
            "risk_budget"
        ]

        if budget is None:
            budget_text = "NONE"
        else:
            budget_text = (
                f"{budget:,.2f}"
            )

        print(
            f"{asset:<6} | "
            f"{record['budget_state']:<12} | "
            f"{record['direction']:<9} | "
            f"{budget_text:<11} | "
            f"{record['reason']}"
        )


# ============================================================================
# PRINT CONTRACT
# ============================================================================

def print_contract(
    snapshot,
    capital_config,
):

    allocated = sum(
        1
        for record in snapshot.values()
        if record["budget_state"]
        == "ALLOCATED"
    )

    unallocated = sum(
        1
        for record in snapshot.values()
        if record["budget_state"]
        == "UNALLOCATED"
    )

    blocked = sum(
        1
        for record in snapshot.values()
        if record["budget_state"]
        == "BLOCKED"
    )

    long_count = sum(
        1
        for record in snapshot.values()
        if record["direction"]
        == "LONG"
    )

    short_count = sum(
        1
        for record in snapshot.values()
        if record["direction"]
        == "SHORT"
    )

    none_count = sum(
        1
        for record in snapshot.values()
        if record["direction"]
        == "NONE"
    )

    risk_budget = calculate_risk_budget(
        capital_config
    )

    max_portfolio = (
        calculate_max_portfolio_risk_amount(
            capital_config
        )
    )

    allocated_risk = sum(
        float(
            record["risk_budget"]
        )
        for record in snapshot.values()
        if (
            record["budget_state"]
            == "ALLOCATED"
            and
            record["risk_budget"] is not None
        )
    )

    print()
    print("=" * 77)
    print(
        "RISK BUDGET ENGINE CONTRACT"
    )
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
        f"Allocated       : "
        f"{allocated}"
    )

    print(
        f"Unallocated     : "
        f"{unallocated}"
    )

    print(
        f"Blocked         : "
        f"{blocked}"
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
        f"Risk Budget/Trade : "
        f"{risk_budget:,.2f}"
    )

    print(
        f"Allocated Risk    : "
        f"{allocated_risk:,.2f}"
    )

    print(
        f"Max Portfolio Risk: "
        f"{max_portfolio:,.2f}"
    )

    print(
        "Capital           : USED"
    )

    print(
        "Position Sizing    : NOT USED"
    )

    print(
        "Stop Loss         : NOT USED"
    )

    print(
        "Take Profit       : NOT USED"
    )

    print(
        "Leverage          : NOT USED"
    )

    print(
        "Portfolio Risk    : LIMIT CHECK ONLY"
    )

    print(
        "Execution         : NOT USED"
    )

    print(
        "Prediction        : NOT USED"
    )

    print(
        "Ranking           : NOT USED"
    )

    print(
        "Interpretation    : NOT USED"
    )

    print(
        "Storage           : MEMORY ONLY"
    )

    print(
        "Database writes   : NONE"
    )

    print(
        "SQL               : NOT USED"
    )

    print(
        "Contract Status   : VALID"
    )

    print("=" * 77)


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        snapshot = calculate_snapshot()

        budgets = snapshot[
            "budgets"
        ]

        print_results(
            budgets
        )

        print_contract(
            budgets,
            snapshot["capital"],
        )

        print()
        print(
            "RISK BUDGET ENGINE STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print(
            "ARUNDA RISK BUDGET ENGINE ERROR"
        )
        print("=" * 77)

        print(
            f"Type  : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error : "
            f"{exc}"
        )

        print()

        print(
            "RISK BUDGET ENGINE STATUS : FAILED"
        )

        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )