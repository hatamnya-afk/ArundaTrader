import market_regime_engine


# =============================================================================
# ARUNDA MARKET REGIME
# =============================================================================
# ROLE:
#   Thin runtime wrapper around market_regime_engine.
#
# ARCHITECTURE:
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
#
# IMPORTANT:
#   This layer does NOT calculate or redefine market regime.
#   It only exposes the canonical engine APIs required by downstream
#   contract layers.
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


FULL_CONTEXT_TARGET = 150


# =============================================================================
# LOAD MARKET REGIME
# =============================================================================

def load_market_regime():
    """
    Expose the canonical market-regime loader from market_regime_engine.

    IMPORTANT:
        No regime logic is implemented here.
        No transformation is performed.
        The engine remains the single source of truth.
    """

    loader = getattr(
        market_regime_engine,
        "load_market_regime",
        None,
    )

    if loader is None:
        raise RuntimeError(
            "market_regime_engine.py must expose "
            "load_market_regime()"
        )

    data = loader()

    if not isinstance(data, dict):
        raise RuntimeError(
            "market_regime_engine.load_market_regime() "
            "must return dict"
        )

    return data


# =============================================================================
# LOAD STRUCTURAL STATE
# =============================================================================

def load_structural_state():
    """
    Preserve the existing structural-state API.

    This is intentionally separate from load_market_regime().
    """

    loader = getattr(
        market_regime_engine,
        "load_structural_state",
        None,
    )

    if loader is None:
        raise RuntimeError(
            "market_regime_engine.py must expose "
            "load_structural_state()"
        )

    state = loader()

    if not isinstance(state, dict):
        raise RuntimeError(
            "market_regime_engine.load_structural_state() "
            "must return dict"
        )

    return state


# =============================================================================
# MAIN
# =============================================================================

def main():

    market_regime = load_market_regime()

    print("ARUNDA MARKET REGIME")
    print("=" * 60)
    print("Assets:", len(market_regime))

    for asset in EXPECTED_ASSETS:

        data = market_regime.get(asset)

        if not isinstance(data, dict):
            print(asset, "| INVALID")
            continue

        points = data.get("points", 0)

        try:
            points = int(points)
        except (TypeError, ValueError):
            points = 0

        context = (
            "FULL"
            if points >= FULL_CONTEXT_TARGET
            else "LIMITED"
            if points > 0
            else "INSUFFICIENT"
        )

        print(
            asset,
            "|",
            data.get("status"),
            "|",
            context,
            "| points=",
            points,
            "| regime=",
            data.get("regime"),
        )

    print()
    print("MARKET REGIME STATUS : READY")


if __name__ == "__main__":
    main()