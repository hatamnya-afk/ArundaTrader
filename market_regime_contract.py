import market_regime


# =============================================================================
# ARUNDA MARKET REGIME CONTRACT v0.2
# =============================================================================
# Purpose:
#   Convert the semantic market-regime output into a strict contract
#   consumed by downstream layers.
#
# CONTEXT CONTRACT:
#
#   WARM-UP / LIMITED:
#       0 < points < 150
#       ACCEPTED
#       REAL DATA ONLY
#
#   FULL:
#       points >= 150
#       ACCEPTED
#       MINIMUM RUNTIME CONTEXT = 150
#
# IMPORTANT:
#   The contract NEVER pads, fills, interpolates, fabricates,
#   truncates, or rewrites the real point count.
#
# Architecture:
#   READ ONLY
#   MEMORY ONLY
#   NO SQL
#   NO DATABASE WRITES
#   NO SIGNAL GENERATION
#   NO SCORING
#   NO DECISION
#   NO PREDICTION
#   NO RANKING
#   NO EXECUTION
# =============================================================================


FULL_CONTEXT_TARGET = 150
MIN_CONTEXT_POINTS = 1


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


ALLOWED_REGIMES = (
    "TRENDING",
    "RANGING",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "TRANSITION",
    "UNDEFINED",
)


# =============================================================================
# LOAD SOURCE REGIME
# =============================================================================

def load_market_regime():
    """
    Load semantic market regime from market_regime.py.

    Source state:
        AVAILABLE

    No transformation of source data is performed here.
    """

    loader = getattr(
        market_regime,
        "load_market_regime",
        None,
    )

    if loader is None:
        raise RuntimeError(
            "market_regime.py must expose "
            "load_market_regime()"
        )

    data = loader()

    if not isinstance(data, dict):
        raise RuntimeError(
            "market_regime.load_market_regime() "
            "must return dict"
        )

    return data


# =============================================================================
# VALIDATE SOURCE SNAPSHOT
# =============================================================================

def validate_source_snapshot(source):
    """
    Validate semantic market-regime source.

    Context rule:

        0 < points < 150
            VALID / LIMITED

        points >= 150
            VALID / FULL

    Actual points are preserved exactly.
    """

    if not isinstance(source, dict):
        raise RuntimeError(
            "Market regime source must be a dictionary"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(source.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            "Market regime source missing assets: "
            + str(sorted(missing))
        )

    if extra:
        raise RuntimeError(
            "Market regime source contains unexpected assets: "
            + str(sorted(extra))
        )

    for asset in EXPECTED_ASSETS:

        data = source[asset]

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid regime data for: "
                + asset
            )

        status = data.get("status")

        if status != "AVAILABLE":
            raise RuntimeError(
                "Source regime not AVAILABLE: "
                + asset
                + " -> "
                + str(status)
            )

        points = data.get("points")

        if isinstance(points, bool) or not isinstance(points, int):
            raise RuntimeError(
                "Invalid points for: "
                + asset
                + " -> "
                + str(points)
            )

        if points < MIN_CONTEXT_POINTS:
            raise RuntimeError(
                "Insufficient context for: "
                + asset
                + " -> "
                + str(points)
            )

        regime = data.get("regime")

        if regime not in ALLOWED_REGIMES:
            raise RuntimeError(
                "Invalid regime for "
                + asset
                + ": "
                + str(regime)
            )

    return True


# =============================================================================
# CONTEXT CLASSIFICATION
# =============================================================================

def classify_context(points):
    """
    Classify actual runtime context.

        0 < points < 150 -> LIMITED
        points >= 150    -> FULL

    No data modification.
    """

    if points < MIN_CONTEXT_POINTS:
        return "INSUFFICIENT"

    if points >= FULL_CONTEXT_TARGET:
        return "FULL"

    return "LIMITED"


# =============================================================================
# BUILD CONTRACT
# =============================================================================

def build_market_regime_contract():
    """
    Build strict READY contract.

    IMPORTANT:
        Actual source point count is preserved.
        132 remains 132.
        123 remains 123.
        150+ remains 150+.

    No padding.
    No interpolation.
    No fill.
    No synthetic context.
    """

    source = load_market_regime()

    validate_source_snapshot(source)

    contract = {}

    for asset in EXPECTED_ASSETS:

        data = source[asset]

        points = data["points"]

        contract[asset] = {
            "asset": asset,
            "status": "READY",
            "points": points,
            "context": classify_context(points),
            "regime": data["regime"],
        }

    return contract


# =============================================================================
# PUBLIC API
# =============================================================================

def load_market_regime_contract():
    """
    Public contract loader.

    Returns exactly 15 READY assets with their REAL context size.
    """

    return build_market_regime_contract()


# =============================================================================
# VALIDATE CONTRACT
# =============================================================================

def validate_market_regime_contract(contract):
    """
    Validate final downstream contract.
    """

    if not isinstance(contract, dict):
        return False

    expected = set(EXPECTED_ASSETS)
    actual = set(contract.keys())

    if expected != actual:
        return False

    for asset in EXPECTED_ASSETS:

        data = contract[asset]

        if not isinstance(data, dict):
            return False

        if data.get("asset") != asset:
            return False

        if data.get("status") != "READY":
            return False

        points = data.get("points")

        if isinstance(points, bool) or not isinstance(points, int):
            return False

        if points < MIN_CONTEXT_POINTS:
            return False

        expected_context = classify_context(points)

        if data.get("context") != expected_context:
            return False

        if data.get("regime") not in ALLOWED_REGIMES:
            return False

    return True


# =============================================================================
# PRINT HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print("ARUNDA MARKET REGIME CONTRACT v0.2")
    print("=" * 78)

    print("Source              : market_regime")
    print("Source State        : AVAILABLE")
    print("Contract State      : READY")
    print("Full Context Target : 150")
    print("Warm-up Policy      : 0 < points < 150 = LIMITED")
    print("Full Policy         : points >= 150 = FULL")
    print("Actual Points       : PRESERVED")
    print("Storage             : MEMORY ONLY")
    print("Writes              : NONE")
    print("SQL                 : NOT USED")
    print("Signals             : NOT USED")
    print("Scoring             : NOT USED")
    print("Decision            : NOT USED")
    print("Prediction          : NOT USED")
    print("Ranking             : NOT USED")
    print("Risk                : NOT USED")
    print("Execution           : NOT USED")

    print("=" * 78)
    print()


# =============================================================================
# PRINT CONTRACT
# =============================================================================

def print_contract(contract):

    print("MARKET REGIME SNAPSHOT")
    print("-" * 78)

    print(
        "Asset  | Status | Points | Context | Regime"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:

        data = contract[asset]

        print(
            "{:<6} | {:<6} | {:>6} | {:<7} | {}".format(
                asset,
                data["status"],
                data["points"],
                data["context"],
                data["regime"],
            )
        )

    print()

    valid = validate_market_regime_contract(
        contract
    )

    ready_assets = sum(
        1
        for asset in EXPECTED_ASSETS
        if contract[asset]["status"] == "READY"
    )

    full_assets = sum(
        1
        for asset in EXPECTED_ASSETS
        if contract[asset]["context"] == "FULL"
    )

    limited_assets = sum(
        1
        for asset in EXPECTED_ASSETS
        if contract[asset]["context"] == "LIMITED"
    )

    print("=" * 78)
    print("MARKET REGIME CONTRACT")
    print("=" * 78)

    print(
        "Expected Assets :",
        len(EXPECTED_ASSETS),
    )

    print(
        "Ready Assets    :",
        ready_assets,
    )

    print(
        "Full Assets     :",
        full_assets,
    )

    print(
        "Limited Assets   :",
        limited_assets,
    )

    print(
        "Full Target     :",
        FULL_CONTEXT_TARGET,
    )

    print(
        "Actual Points   : PRESERVED",
    )

    print(
        "Storage         : MEMORY ONLY",
    )

    print(
        "Database writes : NONE",
    )

    print(
        "SQL             : NOT USED",
    )

    print(
        "Signal Engine   : INPUT ONLY",
    )

    print(
        "Scoring         : INPUT ONLY",
    )

    print(
        "Decision        : NOT USED",
    )

    print(
        "Prediction      : NOT USED",
    )

    print(
        "Ranking         : NOT USED",
    )

    print(
        "Risk            : NOT USED",
    )

    print(
        "Execution       : NOT USED",
    )

    print(
        "Contract Status :",
        "VALID"
        if valid
        else "INVALID",
    )

    print()

    return valid


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    try:

        contract = load_market_regime_contract()

        valid = print_contract(
            contract
        )

        if valid:

            print(
                "MARKET REGIME CONTRACT STATUS : READY"
            )

            return 0

        print(
            "MARKET REGIME CONTRACT STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print()
        print("=" * 78)
        print("MARKET REGIME CONTRACT ERROR")
        print("=" * 78)

        print(
            "Type   :",
            type(error).__name__,
        )

        print(
            "Error  :",
            str(error),
        )

        print()

        print(
            "MARKET REGIME CONTRACT STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )