# =============================================================================
# ARUNDA TRADER
# TRADE GATE ENGINE v0.1
# CP6 RUNTIME ADAPTER
# =============================================================================

ENGINE_VERSION = "TRADE_GATE_v0.1"

MIN_CONFIDENCE = 0.55
MIN_SCORE = 0.10
MIN_RISK_REWARD = 1.5
MAX_SNAPSHOT_AGE_SECONDS = 900
MIN_MARKET_DATA_POINTS = 4

EXECUTION_ENABLED = False

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

APPROVED_RISK_STATES = {
    "APPROVED",
    "ACCEPTED",
    "PASS",
}

NON_TRADABLE_DECISION_STATES = {
    "HOLD",
    "NONE",
}

VALID_TRADE_DIRECTIONS = {
    "LONG",
    "SHORT",
}


# =============================================================================
# SAFE HELPERS
# =============================================================================

def safe_float(value):
    """
    Safely convert a value to float.

    Returns None when conversion is not possible.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_direction(value):
    """
    Normalize trade direction.

    Only LONG / SHORT / NONE are accepted.
    """
    if value is None:
        return "NONE"

    value = str(value).strip().upper()

    if value in VALID_TRADE_DIRECTIONS:
        return value

    if value == "NONE":
        return "NONE"

    return "NONE"


def normalize_asset(value):
    """
    Normalize asset symbol.
    """
    if value is None:
        return None

    return str(value).strip().upper()


def get_asset(row):
    """
    Extract asset from a runtime record.
    """
    if not isinstance(row, dict):
        return None

    for key in (
        "asset",
        "symbol",
    ):
        value = row.get(key)

        if value is not None:
            return normalize_asset(value)

    return None


def get_decision_state(row):
    """
    Extract Decision state.

    Production Decision Engine uses:
        state
    """
    if not isinstance(row, dict):
        return None

    state = row.get("state")

    if state is None:
        state = row.get("decision")

    if state is None:
        return None

    return str(state).strip().upper()


def get_direction(row):
    """
    Extract direction.
    """
    if not isinstance(row, dict):
        return "NONE"

    value = row.get("direction")

    return normalize_direction(value)


def get_score(row):
    """
    Extract score.
    """
    if not isinstance(row, dict):
        return None

    for key in (
        "score",
        "opportunity_score",
    ):
        value = row.get(key)

        if value is not None:
            return safe_float(value)

    return None


def get_opportunity_status(row):
    """
    Extract canonical Opportunity status.

    Trade Gate requires:
        ELIGIBLE
    """
    if not isinstance(row, dict):
        return None

    status = row.get("status")

    if status is None:
        return None

    return str(status).strip().upper()


def get_risk_status(row):
    """
    Extract the formal Risk Contract state.

    Canonical field:
        risk_state

    Compatibility fallback:
        status
    """
    if not isinstance(row, dict):
        return None

    risk_state = row.get("risk_state")

    if risk_state is not None:
        return str(risk_state).strip().upper()

    status = row.get("status")

    if status is not None:
        return str(status).strip().upper()

    return None


# =============================================================================
# OPPORTUNITY ADAPTER
# =============================================================================

def adapt_opportunity(opportunity, decision):
    """
    Adapt the current Opportunity record using the current Decision Snapshot.

    No calculation or strategy modification occurs here.
    """
    if not isinstance(opportunity, dict):
        raise RuntimeError(
            "Opportunity record must be a dictionary"
        )

    if not isinstance(decision, dict):
        raise RuntimeError(
            "Decision record must be a dictionary"
        )

    opportunity_asset = get_asset(opportunity)
    decision_asset = get_asset(decision)

    if opportunity_asset != decision_asset:
        raise RuntimeError(
            "Opportunity / Decision asset mismatch: "
            f"{opportunity_asset} != {decision_asset}"
        )

    adapted = dict(opportunity)

    adapted["asset"] = opportunity_asset

    adapted["status"] = get_opportunity_status(
        opportunity
    )

    adapted["direction"] = get_direction(
        decision
    )

    score = get_score(opportunity)

    adapted["score"] = score
    adapted["opportunity_score"] = score

    confidence = safe_float(
        opportunity.get("confidence")
    )

    adapted["confidence"] = confidence

    market_data_points = opportunity.get(
        "market_data_points"
    )

    if market_data_points is None:
        market_data_points = opportunity.get(
            "points"
        )

    if market_data_points is not None:
        try:
            market_data_points = int(
                market_data_points
            )
        except (TypeError, ValueError):
            market_data_points = None

    adapted["market_data_points"] = market_data_points

    snapshot_age = safe_float(
        opportunity.get("snapshot_age")
    )

    if snapshot_age is None:
        snapshot_age = 0.0

    adapted["snapshot_age"] = snapshot_age

    return adapted


# =============================================================================
# OPPORTUNITY GATES
# =============================================================================

def check_opportunity(opportunity):
    """
    Evaluate Opportunity-side gates.

    Score contract:
        score is evaluated on the [-1.0, +1.0] scale.

    No score transformation is performed.
    """
    reasons = []

    opportunity_status = get_opportunity_status(
        opportunity
    )

    if opportunity_status != "ELIGIBLE":
        if opportunity_status is None:
            reasons.append(
                "opportunity status unavailable"
            )
        else:
            reasons.append(
                "opportunity status not eligible: "
                f"{opportunity_status}"
            )

    direction = get_direction(
        opportunity
    )

    if direction not in VALID_TRADE_DIRECTIONS:
        reasons.append(
            "invalid direction"
        )

    confidence = safe_float(
        opportunity.get("confidence")
    )

    if confidence is None:
        reasons.append(
            "confidence unavailable"
        )
    elif confidence < MIN_CONFIDENCE:
        reasons.append(
            "confidence below minimum"
        )

    score = get_score(
        opportunity
    )

    if score is None:
        reasons.append(
            "opportunity score unavailable"
        )
    elif abs(score) < MIN_SCORE:
        reasons.append(
            "opportunity score below minimum edge"
        )

    market_data_points = opportunity.get(
        "market_data_points"
    )

    if market_data_points is None:
        market_data_points = opportunity.get(
            "points"
        )

    try:
        market_data_points = int(
            market_data_points
        )
    except (TypeError, ValueError):
        market_data_points = None

    if market_data_points is None:
        reasons.append(
            "market data points unavailable"
        )
    elif market_data_points < MIN_MARKET_DATA_POINTS:
        reasons.append(
            "insufficient market data points"
        )

    snapshot_age = safe_float(
        opportunity.get("snapshot_age")
    )

    if snapshot_age is None:
        snapshot_age = 0.0

    if snapshot_age > MAX_SNAPSHOT_AGE_SECONDS:
        reasons.append(
            "snapshot too old"
        )

    return reasons


# =============================================================================
# DECISION GATES
# =============================================================================

def check_decision(decision):
    """
    Evaluate Decision-side gates.
    """
    reasons = []

    state = get_decision_state(
        decision
    )

    if state in NON_TRADABLE_DECISION_STATES:
        reasons.append(
            "decision not actionable"
        )

        return reasons

    if state not in (
        "TRADE",
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
        "ACTIONABLE",
    ):
        reasons.append(
            "decision not actionable"
        )

    return reasons


# =============================================================================
# RISK GATES
# =============================================================================

def check_risk(risk):
    """
    Evaluate Risk-side gates.

    Canonical Risk Contract:
        risk_state

    Approved:
        APPROVED / ACCEPTED / PASS

    Risk reward is optional.
    """
    reasons = []

    risk_status = get_risk_status(
        risk
    )

    if risk_status not in APPROVED_RISK_STATES:
        reasons.append(
            "risk not approved"
        )

    risk_decision = ""

    if isinstance(risk, dict):
        value = risk.get(
            "risk_decision"
        )

        if value is None:
            value = risk.get(
                "decision"
            )

        if value is not None:
            risk_decision = str(
                value
            ).strip().upper()

    if risk_decision in {
        "WATCH",
        "NO_TRADE",
        "REJECTED",
        "NONE",
    }:
        reasons.append(
            "risk decision not tradable"
        )

    risk_reward = None

    if isinstance(risk, dict):
        risk_reward = safe_float(
            risk.get("risk_reward")
        )

    if (
        risk_reward is not None
        and risk_reward < MIN_RISK_REWARD
    ):
        reasons.append(
            "risk reward below minimum"
        )

    return reasons


# =============================================================================
# AUTHORITATIVE TRADE-GATE EVALUATION
# =============================================================================

def evaluate(
    opportunity,
    decision,
    risk,
):
    """
    Authoritative Trade Gate evaluation.

    TRADE_READY is returned only when:
        opportunity_reasons == []
        decision_reasons == []
        risk_reasons == []
    """
    opportunity_reasons = check_opportunity(
        opportunity
    )

    decision_reasons = check_decision(
        decision
    )

    risk_reasons = check_risk(
        risk
    )

    reasons = (
        opportunity_reasons
        + decision_reasons
        + risk_reasons
    )

    if not reasons:
        return (
            "TRADE_READY",
            [
                "all gates passed"
            ],
        )

    has_risk_failure = bool(
        risk_reasons
    )

    if has_risk_failure:
        return (
            "REJECTED",
            reasons,
        )

    return (
        "WATCH",
        reasons,
    )


# =============================================================================
# OBSERVABILITY
# =============================================================================

def build_gate_observability(
    opportunity,
    decision,
    risk,
):
    """
    Read-only observability layer.

    This function does not determine or modify Trade Gate behavior.
    It exposes the same predicates used by the authoritative gate.
    """
    opportunity_status = get_opportunity_status(
        opportunity
    )

    direction = get_direction(
        opportunity
    )

    confidence = safe_float(
        opportunity.get("confidence")
    )

    score = get_score(
        opportunity
    )

    market_data_points = opportunity.get(
        "market_data_points"
    )

    if market_data_points is None:
        market_data_points = opportunity.get(
            "points"
        )

    try:
        market_data_points = int(
            market_data_points
        )
    except (TypeError, ValueError):
        market_data_points = None

    snapshot_age = safe_float(
        opportunity.get("snapshot_age")
    )

    if snapshot_age is None:
        snapshot_age = 0.0

    decision_state = get_decision_state(
        decision
    )

    valid_decision_states = [
        "TRADE",
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
        "ACTIONABLE",
    ]

    risk_status = get_risk_status(
        risk
    )

    risk_decision = ""

    if isinstance(risk, dict):
        value = risk.get(
            "risk_decision"
        )

        if value is None:
            value = risk.get(
                "decision"
            )

        if value is not None:
            risk_decision = str(
                value
            ).strip().upper()

    risk_reward = None

    if isinstance(risk, dict):
        risk_reward = safe_float(
            risk.get("risk_reward")
        )

    return [
        {
            "name": "OPPORTUNITY_STATUS",
            "actual": opportunity_status,
            "expected": "ELIGIBLE",
            "pass": (
                opportunity_status == "ELIGIBLE"
            ),
            "owner_file": "opportunity_engine.py",
            "owner_function": "build_opportunity",
        },
        {
            "name": "OPPORTUNITY_DIRECTION",
            "actual": direction,
            "expected": sorted(
                VALID_TRADE_DIRECTIONS
            ),
            "pass": (
                direction
                in VALID_TRADE_DIRECTIONS
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_opportunity",
        },
        {
            "name": "OPPORTUNITY_CONFIDENCE",
            "actual": confidence,
            "expected": (
                f">= {MIN_CONFIDENCE}"
            ),
            "pass": (
                confidence is not None
                and confidence >= MIN_CONFIDENCE
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_opportunity",
        },
        {
            "name": "OPPORTUNITY_SCORE",
            "actual": score,
            "expected": (
                f"abs(score) >= {MIN_SCORE}"
            ),
            "pass": (
                score is not None
                and abs(score) >= MIN_SCORE
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_opportunity",
        },
        {
            "name": "MARKET_DATA_POINTS",
            "actual": market_data_points,
            "expected": (
                f">= {MIN_MARKET_DATA_POINTS}"
            ),
            "pass": (
                market_data_points is not None
                and market_data_points
                >= MIN_MARKET_DATA_POINTS
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_opportunity",
        },
        {
            "name": "SNAPSHOT_AGE",
            "actual": snapshot_age,
            "expected": (
                f"<= {MAX_SNAPSHOT_AGE_SECONDS}"
            ),
            "pass": (
                snapshot_age
                <= MAX_SNAPSHOT_AGE_SECONDS
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_opportunity",
        },
        {
            "name": "DECISION_STATE",
            "actual": decision_state,
            "expected": valid_decision_states,
            "pass": (
                decision_state
                in valid_decision_states
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_decision",
        },
        {
            "name": "RISK_STATUS",
            "actual": risk_status,
            "expected": sorted(
                APPROVED_RISK_STATES
            ),
            "pass": (
                risk_status
                in APPROVED_RISK_STATES
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_risk",
        },
        {
            "name": "RISK_DECISION",
            "actual": risk_decision,
            "expected": (
                "not WATCH/NO_TRADE/"
                "REJECTED/NONE"
            ),
            "pass": (
                risk_decision
                not in {
                    "WATCH",
                    "NO_TRADE",
                    "REJECTED",
                    "NONE",
                }
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_risk",
        },
        {
            "name": "RISK_REWARD",
            "actual": risk_reward,
            "expected": (
                "optional; if present "
                f">= {MIN_RISK_REWARD}"
            ),
            "pass": (
                risk_reward is None
                or risk_reward >= MIN_RISK_REWARD
            ),
            "owner_file": "trade_gate_engine.py",
            "owner_function": "check_risk",
        },
    ]


# =============================================================================
# RUNTIME INPUT VALIDATION
# =============================================================================

def validate_runtime_inputs(
    opportunities,
    decision_snapshot,
    risk_snapshot,
):
    if not isinstance(
        opportunities,
        (list, tuple, dict),
    ):
        raise RuntimeError(
            "Opportunities must be a list, tuple, or dictionary"
        )

    if not isinstance(
        decision_snapshot,
        dict,
    ):
        raise RuntimeError(
            "Decision snapshot must be a dictionary"
        )

    if not isinstance(
        risk_snapshot,
        dict,
    ):
        raise RuntimeError(
            "Risk snapshot must be a dictionary"
        )


def _rows_from_list(rows):
    """
    Convert a list of dictionaries into asset-keyed rows.
    """
    result = {}

    if not isinstance(
        rows,
        (list, tuple),
    ):
        return result

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        asset = get_asset(row)

        if asset is None:
            continue

        if asset in result:
            raise RuntimeError(
                f"Duplicate runtime asset: {asset}"
            )

        result[asset] = row

    return result


def _rows_from_asset_mapping(mapping):
    """
    Validate an asset-keyed mapping.
    """
    result = {}

    if not isinstance(
        mapping,
        dict,
    ):
        return result

    for key, row in mapping.items():
        asset = normalize_asset(key)

        if asset not in EXPECTED_ASSETS:
            continue

        if not isinstance(
            row,
            dict,
        ):
            raise RuntimeError(
                f"Invalid runtime record for {asset}"
            )

        result[asset] = row

    return result


def _coverage_score(mapping):
    """
    Return coverage count for expected assets.
    """
    if not isinstance(
        mapping,
        dict,
    ):
        return 0

    return sum(
        1
        for asset in EXPECTED_ASSETS
        if asset in mapping
    )


def _select_best_rows(rows):
    """
    Select current-run rows.

    No synthesis or modification occurs.
    """
    if isinstance(rows, dict):
        return _rows_from_asset_mapping(
            rows
        )

    if isinstance(rows, (list, tuple)):
        return _rows_from_list(
            rows
        )

    raise RuntimeError(
        "Unsupported runtime row structure"
    )


def extract_snapshot_rows(snapshot):
    """
    Extract rows from a runtime snapshot.
    """
    if not isinstance(
        snapshot,
        dict,
    ):
        raise RuntimeError(
            "Snapshot must be a dictionary"
        )

    for key in (
        "decisions",
        "risk",
        "risks",
        "snapshot",
        "rows",
    ):
        value = snapshot.get(key)

        if isinstance(value, dict):
            return _rows_from_asset_mapping(
                value
            )

        if isinstance(value, (list, tuple)):
            return _rows_from_list(
                value
            )

    return _rows_from_asset_mapping(
        snapshot
    )


def build_asset_map(rows):
    """
    Build an asset-keyed map from runtime rows.
    """
    if isinstance(rows, dict):
        return _rows_from_asset_mapping(
            rows
        )

    return _rows_from_list(
        rows
    )


# =============================================================================
# RUNTIME GATE
# =============================================================================

def run_runtime(
    opportunities,
    decision_snapshot,
    risk_snapshot,
):
    """
    Execute the Trade Gate runtime adapter.

    No DB writes.
    No exchange calls.
    No execution.
    No synthetic data.
    No fallback fabrication.
    """
    validate_runtime_inputs(
        opportunities,
        decision_snapshot,
        risk_snapshot,
    )

    decision_rows = extract_snapshot_rows(
        decision_snapshot
    )

    if _coverage_score(
        decision_rows
    ) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Decision snapshot coverage failure: "
            f"{_coverage_score(decision_rows)}/"
            f"{EXPECTED_ASSET_COUNT}"
        )

    risk_rows = extract_snapshot_rows(
        risk_snapshot
    )

    if _coverage_score(
        risk_rows
    ) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Risk snapshot coverage failure: "
            f"{_coverage_score(risk_rows)}/"
            f"{EXPECTED_ASSET_COUNT}"
        )

    opportunity_rows = _select_best_rows(
        opportunities
    )

    if len(decision_rows) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Decision asset count mismatch"
        )

    if len(risk_rows) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Risk asset count mismatch"
        )

    results = []

    for asset in EXPECTED_ASSETS:
        decision = decision_rows.get(
            asset
        )

        risk = risk_rows.get(
            asset
        )

        decision_state = get_decision_state(
            decision
        )

        direction = get_direction(
            decision
        )

        risk_status = get_risk_status(
            risk
        )

        opportunity = opportunity_rows.get(
            asset
        )

        if opportunity is None:
            results.append(
                {
                    "asset": asset,
                    "decision_state": decision_state,
                    "direction": direction,
                    "score": None,
                    "risk_status": risk_status,
                    "trade_gate_status": "WATCH",
                    "status_reason": (
                        "no current-run opportunity"
                    ),
                    "gate_observability": [],
                    "observability_consistency": True,
                }
            )

            continue

        adapted_opportunity = adapt_opportunity(
            opportunity,
            decision,
        )

        gate_status, reasons = evaluate(
            adapted_opportunity,
            decision,
            risk,
        )

        if decision_state in NON_TRADABLE_DECISION_STATES:
            gate_status = "WATCH"

            reasons = [
                "decision not actionable"
            ]

        if (
            direction
            not in VALID_TRADE_DIRECTIONS
            and gate_status == "TRADE_READY"
        ):
            gate_status = "WATCH"

            reasons = [
                "invalid direction"
            ]

        if (
            risk_status
            not in APPROVED_RISK_STATES
            and gate_status == "TRADE_READY"
        ):
            gate_status = "REJECTED"

            reasons = [
                "risk not approved"
            ]

        opportunity_status = get_opportunity_status(
            adapted_opportunity
        )

        if (
            opportunity_status != "ELIGIBLE"
            and gate_status == "TRADE_READY"
        ):
            gate_status = "WATCH"

            if opportunity_status is None:
                reasons = [
                    "opportunity status unavailable"
                ]
            else:
                reasons = [
                    "opportunity status not eligible: "
                    f"{opportunity_status}"
                ]

        gate_observability = (
            build_gate_observability(
                adapted_opportunity,
                decision,
                risk,
            )
        )

        all_predicates_pass = all(
            bool(item.get("pass"))
            for item in gate_observability
        )

        expected_ready = all_predicates_pass

        actual_ready = (
            gate_status == "TRADE_READY"
        )

        observability_consistency = (
            expected_ready
            == actual_ready
        )

        results.append(
            {
                "asset": asset,
                "decision_state": decision_state,
                "direction": direction,
                "score": get_score(
                    adapted_opportunity
                ),
                "risk_status": risk_status,
                "trade_gate_status": gate_status,
                "status_reason": (
                    "; ".join(reasons)
                    if reasons
                    else "all gates passed"
                ),
                "gate_observability": (
                    gate_observability
                ),
                "observability_consistency": (
                    observability_consistency
                ),
            }
        )

    result_assets = [
        row.get("asset")
        for row in results
    ]

    if len(results) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Trade Gate result count mismatch: "
            f"{len(results)}/"
            f"{EXPECTED_ASSET_COUNT}"
        )

    if len(
        set(result_assets)
    ) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Trade Gate result contains duplicate assets"
        )

    missing_assets = (
        set(EXPECTED_ASSETS)
        - set(result_assets)
    )

    extra_assets = (
        set(result_assets)
        - set(EXPECTED_ASSETS)
    )

    if missing_assets:
        raise RuntimeError(
            "Trade Gate result missing assets: "
            f"{sorted(missing_assets)}"
        )

    if extra_assets:
        raise RuntimeError(
            "Trade Gate result contains unexpected assets: "
            f"{sorted(extra_assets)}"
        )

    uni_result = next(
        (
            row
            for row in results
            if row.get("asset") == "UNI"
        ),
        None,
    )

    if uni_result is not None:
        print()
        print("=" * 72)
        print(
            "ARUNDA TRADE GATE OBSERVABILITY — UNI"
        )
        print("=" * 72)

        print(
            f"ASSET              : "
            f"{uni_result.get('asset')}"
        )

        print(
            f"TRADE_GATE_STATUS   : "
            f"{uni_result.get('trade_gate_status')}"
        )

        print(
            f"STATUS_REASON      : "
            f"{uni_result.get('status_reason')}"
        )

        uni_predicates = (
            uni_result.get(
                "gate_observability",
                [],
            )
        )

        all_pass = all(
            bool(item.get("pass"))
            for item in uni_predicates
        )

        print(
            f"ALL_PREDICATES_PASS: "
            f"{all_pass}"
        )

        print(
            f"OBSERVABILITY_MATCH: "
            f"{uni_result.get('observability_consistency')}"
        )

        print("-" * 72)

        for item in uni_predicates:
            print(
                "PREDICATE | "
                f"{item.get('name')} | "
                f"ACTUAL={item.get('actual')} | "
                f"EXPECTED={item.get('expected')} | "
                f"PASS={item.get('pass')} | "
                "OWNER="
                f"{item.get('owner_file')}"
                "::"
                f"{item.get('owner_function')}"
            )

        print("-" * 72)

        failed = [
            item
            for item in uni_predicates
            if not item.get("pass")
        ]

        print(
            "FIRST_REAL_GATE_FAILURE:"
        )

        if failed:
            first_failure = failed[0]

            print(
                "FAIL | "
                f"{first_failure.get('name')} | "
                f"ACTUAL={first_failure.get('actual')} | "
                f"EXPECTED={first_failure.get('expected')} | "
                "OWNER="
                f"{first_failure.get('owner_file')}"
                "::"
                f"{first_failure.get('owner_function')}"
            )
        else:
            print("NONE")

        print("=" * 72)

    return results


# =============================================================================
# CP6 SAFETY BOUNDARIES
# =============================================================================

def save_result(*args, **kwargs):
    """
    CP6:
    Trade Gate result persistence is disabled.
    """
    raise RuntimeError(
        "CP6 violation: DB result persistence is disabled."
    )


def build_order_intent(*args, **kwargs):
    """
    CP6:
    Order Intent construction is disabled.
    """
    raise RuntimeError(
        "CP6 violation: Order Intent is disabled."
    )


# =============================================================================
# STANDALONE EXECUTION BLOCK
# =============================================================================

def main():
    """
    Trade Gate standalone execution is forbidden.

    Production execution must occur through:
        arunda_pipeline.py
    """
    raise SystemExit(
        "TRADE_GATE standalone execution is disabled. "
        "Run only through arunda_pipeline.py CP6 runtime."
    )


if __name__ == "__main__":
    main()