
"""
ARUNDA SIGNAL SCORE CONTRACT v0.2

Purpose:
    Validate the structural score snapshot produced by signal_scorer.

Field Contract:
    asset
    signal_state
    direction
    score

Rules:
    - MEMORY ONLY
    - READ ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO DECISION
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

EXPECTED_FIELDS = (
    "asset",
    "signal_state",
    "direction",
    "score",
)

EXPECTED_SIGNAL_STATES = (
    "ACTIVE",
    "NEUTRAL",
)

EXPECTED_DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)


# ============================================================
# LOAD REAL SCORE SNAPSHOT
# ============================================================

def load_score_snapshot():

    import signal_scorer

    if not hasattr(
        signal_scorer,
        "load_scores"
    ):
        raise RuntimeError(
            "signal_scorer.py must expose load_scores()"
        )

    scores = signal_scorer.load_scores()

    if scores is None:
        raise RuntimeError(
            "signal_scorer.load_scores() returned None"
        )

    return scores


# ============================================================
# NORMALIZE SCORE SNAPSHOT
# ============================================================

def normalize_snapshot(scores):

    if not isinstance(scores, dict):
        raise RuntimeError(
            "Score snapshot must be a dict"
        )

    # --------------------------------------------------------
    # Direct asset-keyed snapshot
    #
    # {
    #     "BTC": {...},
    #     "ETH": {...},
    # }
    # --------------------------------------------------------

    if all(
        isinstance(key, str)
        and key in EXPECTED_ASSETS
        for key in scores.keys()
    ):
        return scores

    # --------------------------------------------------------
    # Optional wrapper
    #
    # {
    #     "scores": {
    #         "BTC": {...},
    #         ...
    #     }
    # }
    # --------------------------------------------------------

    if (
        "scores" in scores
        and isinstance(
            scores["scores"],
            dict
        )
    ):
        return scores["scores"]

    raise RuntimeError(
        "Unsupported score snapshot structure"
    )


# ============================================================
# SCORE VALIDATION
# ============================================================

def validate_score(value, asset):

    if isinstance(value, bool):

        raise RuntimeError(
            f"Invalid score type for {asset}: "
            f"bool is not allowed"
        )

    if not isinstance(
        value,
        (int, float)
    ):

        raise RuntimeError(
            f"Invalid score for {asset}: "
            f"{value!r}"
        )

    return float(value)


# ============================================================
# SINGLE RECORD CONTRACT
# ============================================================

def validate_record(
    asset,
    record
):

    if not isinstance(
        record,
        dict
    ):

        raise RuntimeError(
            f"Invalid score record for {asset}"
        )

    # --------------------------------------------------------
    # Required field contract
    # --------------------------------------------------------

    for field in EXPECTED_FIELDS:

        if field not in record:

            raise RuntimeError(
                f"Missing field for {asset}: "
                f"{field}"
            )

    # --------------------------------------------------------
    # Asset identity
    # --------------------------------------------------------

    if record["asset"] != asset:

        raise RuntimeError(
            f"Asset mismatch: "
            f"expected={asset}, "
            f"actual={record['asset']!r}"
        )

    # --------------------------------------------------------
    # Signal state
    # --------------------------------------------------------

    signal_state = record[
        "signal_state"
    ]

    if signal_state not in EXPECTED_SIGNAL_STATES:

        raise RuntimeError(
            f"Invalid signal_state for {asset}: "
            f"{signal_state!r}"
        )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    direction = record[
        "direction"
    ]

    if direction not in EXPECTED_DIRECTIONS:

        raise RuntimeError(
            f"Invalid direction for {asset}: "
            f"{direction!r}"
        )

    # --------------------------------------------------------
    # State / direction consistency
    #
    # This is structural contract validation.
    # It does not interpret market regime.
    # --------------------------------------------------------

    if signal_state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"ACTIVE signal must have "
                f"LONG or SHORT direction "
                f"for {asset}: {direction!r}"
            )

    elif signal_state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                f"NEUTRAL signal must have "
                f"NONE direction "
                f"for {asset}: {direction!r}"
            )

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

    score = validate_score(
        record["score"],
        asset
    )

    return {
        "asset": asset,
        "signal_state": signal_state,
        "direction": direction,
        "score": score,
    }


# ============================================================
# COMPLETE SNAPSHOT CONTRACT
# ============================================================

def validate_contract(scores):

    snapshot = normalize_snapshot(
        scores
    )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        snapshot.keys()
    )

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            f"Missing assets: "
            f"{sorted(missing)}"
        )

    if extra:

        raise RuntimeError(
            f"Unexpected assets: "
            f"{sorted(extra)}"
        )

    if len(snapshot) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            f"Asset count mismatch: "
            f"expected={EXPECTED_ASSET_COUNT}, "
            f"actual={len(snapshot)}"
        )

    validated = {}

    active = 0
    neutral = 0

    for asset in EXPECTED_ASSETS:

        validated[asset] = validate_record(
            asset,
            snapshot[asset]
        )

        if (
            validated[asset]["signal_state"]
            == "ACTIVE"
        ):
            active += 1

        elif (
            validated[asset]["signal_state"]
            == "NEUTRAL"
        ):
            neutral += 1

    return {
        "expected_assets":
            EXPECTED_ASSET_COUNT,

        "scored_assets":
            len(validated),

        "active_signals":
            active,

        "neutral_signals":
            neutral,

        "contract_status":
            "VALID",

        "fields":
            list(EXPECTED_FIELDS),
    }


# ============================================================
# HEADER
# ============================================================

def print_header():

    print("=" * 78)
    print(
        "ARUNDA SIGNAL SCORE CONTRACT v0.2"
    )
    print("=" * 78)

    print(
        "Source   : signal_scorer.load_scores()"
    )

    print(
        "Fields   : asset | signal_state | "
        "direction | score"
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

    print("=" * 78)


# ============================================================
# CONTRACT OUTPUT
# ============================================================

def print_contract(result):

    print()

    print("=" * 78)
    print(
        "SIGNAL SCORE CONTRACT"
    )
    print("=" * 78)

    print(
        f"Expected Assets : "
        f"{result['expected_assets']}"
    )

    print(
        f"Scored Assets   : "
        f"{result['scored_assets']}"
    )

    print(
        f"Active Signals  : "
        f"{result['active_signals']}"
    )

    print(
        f"Neutral Signals : "
        f"{result['neutral_signals']}"
    )

    print(
        "Fields          : "
        + ", ".join(result["fields"])
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

    print(
        "Contract Status : VALID"
    )

    print("=" * 78)


# ============================================================
# MAIN
# ============================================================

def main():

    print_header()

    try:

        scores = load_score_snapshot()

        result = validate_contract(
            scores
        )

        print_contract(
            result
        )

        print()

        print(
            "SIGNAL SCORE CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()

        print("=" * 78)
        print(
            "SIGNAL SCORE CONTRACT ERROR"
        )
        print("=" * 78)

        print(
            f"Type   : {type(exc).__name__}"
        )

        print(
            f"Error  : {exc}"
        )

        print()

        print(
            "SIGNAL SCORE CONTRACT STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )