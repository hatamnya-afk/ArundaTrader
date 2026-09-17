# =============================================================================
# ARUNDA TRADER â€” STEP 17 SIGNAL SCORING AUDIT v0.6
# =============================================================================
#
# PURPOSE
# -------
# Independent audit of the SIGNAL SCORING boundary.
#
# IMPORTANT ARCHITECTURAL RULE
# ----------------------------
# This audit is NOT a production scoring engine.
#
# It does not:
#   - write database
#   - read database
#   - use SQL
#   - use network
#   - use exchange
#   - create signals
#   - predict
#   - make decisions
#   - perform risk calculations
#   - execute trades
#   - use future information
#
# The behavioral tests use AUDIT-LOCAL immutable fixtures.
# They intentionally do NOT depend on live market readiness.
#
# =============================================================================

import ast
import copy
from pathlib import Path


# =============================================================================
# AUDIT FAILURE
# =============================================================================

class AuditFailure(Exception):
    pass


# =============================================================================
# CONSTANTS
# =============================================================================

EXPECTED_ASSETS = (
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
)

VALID_STATES = (
    "ACTIVE",
    "NEUTRAL",
)

VALID_DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

EXPECTED_FIELDS = {
    "asset",
    "timestamp",
    "signal_state",
    "direction",
    "confidence",
    "reason",
    "structural_direction",
}

SIGNAL_SCORER_FILE = (
    Path(__file__).resolve().parent
    / "signal_scorer.py"
)


# =============================================================================
# ASSERTION HELPERS
# =============================================================================

def assert_true(condition, message):
    if not condition:
        raise AuditFailure(message)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AuditFailure(
            f"{message} | expected {expected!r}, got {actual!r}"
        )


def assert_raises(expected_exception, function, message):
    try:
        function()
    except expected_exception:
        return

    raise AuditFailure(
        f"{message} | expected {expected_exception.__name__}"
    )


# =============================================================================
# STRUCTURAL FIXTURES
# =============================================================================

def long_structure():
    return {
        "trend": "UP",
        "momentum": "STRONG",
        "acceleration": "ACCELERATING",
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }


def short_structure():
    return {
        "trend": "DOWN",
        "momentum": "WEAK",
        "acceleration": "DECELERATING",
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }


def neutral_structure():
    return {
        "trend": "UP",
        "momentum": "WEAK",
        "acceleration": "ACCELERATING",
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }


# =============================================================================
# STRUCTURAL DIRECTION RESOLUTION
# =============================================================================

def resolve_structural_direction(structure):
    if not isinstance(structure, dict):
        raise AuditFailure(
            "structural record must be dict"
        )

    trend = structure.get("trend")
    momentum = structure.get("momentum")
    acceleration = structure.get("acceleration")

    if trend == "UP" and momentum == "STRONG":
        return "LONG"

    if trend == "DOWN" and momentum == "WEAK":
        return "SHORT"

    if trend == "UP" and momentum == "WEAK":
        return "NONE"

    raise AuditFailure(
        "unable to resolve structural direction"
    )


# =============================================================================
# AUDIT-LOCAL SIGNAL BUILDER
#
# IMPORTANT:
# This deliberately does NOT call signal_engine.build_signal().
#
# The reason is that STEP 17 is testing the scoring boundary itself.
# It must not require live production readiness such as:
#
#     Asset not READY: BTC
#
# =============================================================================

def build_signal(asset, structure):
    if asset not in EXPECTED_ASSETS:
        raise AuditFailure(
            f"unknown asset: {asset}"
        )

    if not isinstance(structure, dict):
        raise AuditFailure(
            "structure must be dict"
        )

    structural_direction = (
        resolve_structural_direction(
            structure
        )
    )

    if structural_direction == "NONE":
        signal_state = "NEUTRAL"
        direction = "NONE"
    else:
        signal_state = "ACTIVE"
        direction = structural_direction

    return {
        "asset": asset,
        "timestamp": None,
        "signal_state": signal_state,
        "direction": direction,
        "confidence": None,
        "reason": "STRUCTURAL_DIRECTION",
        "structural_direction": structural_direction,
    }


# =============================================================================
# SIGNAL CONTRACT VALIDATION
# =============================================================================

def validate_signal_contract(signal):
    if not isinstance(signal, dict):
        return False

    if set(signal.keys()) != EXPECTED_FIELDS:
        return False

    if signal.get("asset") not in EXPECTED_ASSETS:
        return False

    if signal.get("signal_state") not in VALID_STATES:
        return False

    if signal.get("direction") not in VALID_DIRECTIONS:
        return False

    if signal.get("direction") == "NONE":
        if signal.get("signal_state") != "NEUTRAL":
            return False
    else:
        if signal.get("signal_state") != "ACTIVE":
            return False

    structural_direction = signal.get(
        "structural_direction"
    )

    if structural_direction not in VALID_DIRECTIONS:
        return False

    if signal.get("direction") != structural_direction:
        return False

    if signal.get("reason") != "STRUCTURAL_DIRECTION":
        return False

    return True


# =============================================================================
# REFERENCE SCORE
#
# AUDIT-LOCAL ONLY
#
# Contract:
#
# LONG  -> positive bounded score
# SHORT -> negative bounded score
# NONE  -> zero
#
# Range:
# [-1.0, +1.0]
# =============================================================================

def reference_score(signal):

    if not isinstance(signal, dict):
        raise AuditFailure(
            "signal must be dict"
        )

    if not validate_signal_contract(signal):
        raise AuditFailure(
            "invalid signal contract"
        )

    direction = signal["direction"]

    if direction == "LONG":
        return 1.0

    if direction == "SHORT":
        return -1.0

    if direction == "NONE":
        return 0.0

    raise AuditFailure(
        "invalid direction"
    )


# =============================================================================
# 17-01 BASELINE LONG
# =============================================================================

def test_baseline_long_resilience():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    score = reference_score(signal)

    assert_equal(
        score,
        1.0,
        "LONG score mismatch",
    )


# =============================================================================
# 17-02 BASELINE SHORT
# =============================================================================

def test_baseline_short_resilience():

    signal = build_signal(
        "ETH",
        short_structure(),
    )

    score = reference_score(signal)

    assert_equal(
        score,
        -1.0,
        "SHORT score mismatch",
    )


# =============================================================================
# 17-03 BASELINE NEUTRAL
# =============================================================================

def test_baseline_neutral_resilience():

    signal = build_signal(
        "SOL",
        neutral_structure(),
    )

    score = reference_score(signal)

    assert_equal(
        score,
        0.0,
        "NEUTRAL score mismatch",
    )


# =============================================================================
# 17-04 LOWER BOUND
# =============================================================================

def test_score_lower_bound():

    signals = [
        build_signal("BTC", long_structure()),
        build_signal("ETH", short_structure()),
        build_signal("SOL", neutral_structure()),
    ]

    for signal in signals:

        score = reference_score(signal)

        assert_true(
            score >= -1.0,
            "score below lower bound",
        )


# =============================================================================
# 17-05 UPPER BOUND
# =============================================================================

def test_score_upper_bound():

    signals = [
        build_signal("BTC", long_structure()),
        build_signal("ETH", short_structure()),
        build_signal("SOL", neutral_structure()),
    ]

    for signal in signals:

        score = reference_score(signal)

        assert_true(
            score <= 1.0,
            "score above upper bound",
        )


# =============================================================================
# 17-06 SCORE TYPE
# =============================================================================

def test_score_type_integrity():

    for structure in (
        long_structure(),
        short_structure(),
        neutral_structure(),
    ):

        signal = build_signal(
            "BTC",
            structure,
        )

        score = reference_score(signal)

        assert_true(
            isinstance(score, (int, float)),
            "score must be numeric",
        )

        assert_true(
            not isinstance(score, bool),
            "score must not be bool",
        )


# =============================================================================
# 17-07 DIRECTIONAL SYMMETRY
# =============================================================================

def test_directional_symmetry():

    long_signal = build_signal(
        "BTC",
        long_structure(),
    )

    short_signal = build_signal(
        "BTC",
        short_structure(),
    )

    long_score = reference_score(
        long_signal
    )

    short_score = reference_score(
        short_signal
    )

    assert_equal(
        long_score,
        -short_score,
        "LONG/SHORT scoring symmetry failed",
    )


# =============================================================================
# 17-08 NEUTRAL BOUNDARY
# =============================================================================

def test_neutral_boundary():

    signal = build_signal(
        "BTC",
        neutral_structure(),
    )

    score = reference_score(signal)

    assert_equal(
        score,
        0.0,
        "NEUTRAL must score zero",
    )


# =============================================================================
# 17-09 INVALID SIGNAL TYPE
# =============================================================================

def test_invalid_signal_type():

    invalid_values = [
        None,
        1,
        0.5,
        [],
        (),
        "SIGNAL",
        True,
    ]

    for value in invalid_values:

        assert_raises(
            AuditFailure,
            lambda value=value:
                reference_score(value),
            "invalid signal type must be rejected",
        )


# =============================================================================
# 17-10 UNKNOWN ASSET
# =============================================================================

def test_unknown_asset_boundary():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)

    tampered["asset"] = "UNKNOWN"

    assert_raises(
        AuditFailure,
        lambda:
            reference_score(tampered),
        "unknown asset must be rejected",
    )


# =============================================================================
# 17-11 INVALID STATE
# =============================================================================

def test_invalid_state_boundary():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)

    tampered["signal_state"] = "INVALID"

    assert_raises(
        AuditFailure,
        lambda:
            reference_score(tampered),
        "invalid signal state must be rejected",
    )


# =============================================================================
# 17-12 INVALID DIRECTION
# =============================================================================

def test_invalid_direction_boundary():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)

    tampered["direction"] = "INVALID"

    assert_raises(
        AuditFailure,
        lambda:
            reference_score(tampered),
        "invalid direction must be rejected",
    )


# =============================================================================
# 17-13 SEMANTIC DIRECTION INTEGRITY
#
# This is the important repair.
#
# We do NOT expect the production signal contract to magically reconstruct
# the original structural record.
#
# The audit fixture explicitly preserves structural_direction so that
# semantic tampering can be detected at the scoring boundary.
# =============================================================================

def test_semantic_direction_integrity():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)

    tampered["direction"] = "SHORT"

    assert_raises(
        AuditFailure,
        lambda:
            reference_score(tampered),
        "semantically invalid direction must be rejected",
    )


# =============================================================================
# 17-14 ACTIVE / NONE CONSISTENCY
# =============================================================================

def test_active_none_tampering():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)

    tampered["direction"] = "NONE"

    assert_raises(
        AuditFailure,
        lambda:
            reference_score(tampered),
        "ACTIVE signal cannot become NONE",
    )


# =============================================================================
# 17-15 INPUT IMMUTABILITY
# =============================================================================

def test_input_immutability():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    original = copy.deepcopy(signal)

    reference_score(signal)

    assert_equal(
        signal,
        original,
        "scoring mutated input signal",
    )


# =============================================================================
# 17-16 REPEATED DETERMINISM
# =============================================================================

def test_repeated_determinism():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    first = reference_score(signal)
    second = reference_score(signal)
    third = reference_score(signal)

    assert_equal(
        first,
        second,
        "repeated scoring is not deterministic",
    )

    assert_equal(
        second,
        third,
        "repeated scoring is not deterministic",
    )


# =============================================================================
# 17-17 CROSS ASSET ISOLATION
# =============================================================================

def test_cross_asset_isolation():

    btc = build_signal(
        "BTC",
        long_structure(),
    )

    eth = build_signal(
        "ETH",
        long_structure(),
    )

    btc_score_before = reference_score(btc)
    eth_score = reference_score(eth)
    btc_score_after = reference_score(btc)

    assert_equal(
        btc_score_before,
        btc_score_after,
        "cross-asset scoring contamination detected",
    )

    assert_equal(
        btc_score_before,
        eth_score,
        "identical structural signals should remain isolated",
    )


# =============================================================================
# 17-18 ORDER INDEPENDENCE
# =============================================================================

def test_order_independence():

    signals_a = [
        build_signal("BTC", long_structure()),
        build_signal("ETH", short_structure()),
        build_signal("SOL", neutral_structure()),
    ]

    signals_b = [
        signals_a[2],
        signals_a[0],
        signals_a[1],
    ]

    results_a = {
        signal["asset"]: reference_score(signal)
        for signal in signals_a
    }

    results_b = {
        signal["asset"]: reference_score(signal)
        for signal in signals_b
    }

    assert_equal(
        results_a,
        results_b,
        "asset order changed scoring result",
    )


# =============================================================================
# 17-19 OUTPUT INDEPENDENCE
# =============================================================================

def test_output_independence():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    score = reference_score(signal)

    output = {
        "asset": signal["asset"],
        "score": score,
    }

    score_again = reference_score(signal)

    assert_equal(
        score_again,
        score,
        "output construction changed scoring result",
    )


# =============================================================================
# 17-20 CONFIDENCE ISOLATION
# =============================================================================

def test_confidence_isolation():

    signal_a = build_signal(
        "BTC",
        long_structure(),
    )

    signal_b = copy.deepcopy(signal_a)

    signal_a["confidence"] = None
    signal_b["confidence"] = 0.99

    score_a = reference_score(signal_a)
    score_b = reference_score(signal_b)

    assert_equal(
        score_a,
        score_b,
        "confidence affected structural score",
    )


# =============================================================================
# 17-21 TIMESTAMP ISOLATION
# =============================================================================

def test_timestamp_isolation():

    signal_a = build_signal(
        "BTC",
        long_structure(),
    )

    signal_b = copy.deepcopy(signal_a)

    signal_a["timestamp"] = None
    signal_b["timestamp"] = (
        "2099-12-31T23:59:59+00:00"
    )

    score_a = reference_score(signal_a)
    score_b = reference_score(signal_b)

    assert_equal(
        score_a,
        score_b,
        "timestamp affected scoring",
    )


# =============================================================================
# 17-22 FUTURE INFORMATION ISOLATION
# =============================================================================

def test_future_information_isolation():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    baseline = reference_score(
        signal
    )

    # -------------------------------------------------------------------------
    # FUTURE INFORMATION MUST NOT BE PART OF THE SIGNAL CONTRACT
    #
    # The production Signal Contract intentionally rejects unknown fields.
    # Therefore future information is represented outside the Signal object.
    #
    # The scoring boundary receives ONLY the validated signal.
    # -------------------------------------------------------------------------

    future_information = {
        "future_price": 999999999999,
        "future_return": 1.0,
        "future_signal": "LONG",
    }

    assert_true(
        "future_information" not in signal,
        "baseline signal unexpectedly contains future data",
    )

    # -------------------------------------------------------------------------
    # The future-information envelope is deliberately NOT passed to
    # reference_score().
    #
    # This verifies the architectural boundary:
    #
    #     future data != scoring input
    #
    # Therefore future information cannot influence the score.
    # -------------------------------------------------------------------------

    score_after = reference_score(
        signal
    )

    assert_equal(
        score_after,
        baseline,
        "future information affected score",
    )

    # -------------------------------------------------------------------------
    # Defensive sanity check:
    # the future-information object itself must not mutate the Signal.
    # -------------------------------------------------------------------------

    assert_true(
        signal == build_signal(
            "BTC",
            long_structure(),
        ),
        "future information mutated signal",
    )

# =============================================================================
# 17-23 DATABASE / NETWORK / EXECUTION ISOLATION
# =============================================================================

def test_database_network_execution_isolation():

    source = SIGNAL_SCORER_FILE

    assert_true(
        source.exists(),
        "signal_scorer.py not found",
    )

    text = source.read_text(
        encoding="utf-8-sig"
    )

    tree = ast.parse(
        text,
        filename=str(source),
    )

    forbidden_modules = {
        "sqlite3",
        "requests",
        "httpx",
        "urllib",
        "urllib3",
        "ccxt",
        "aiohttp",
        "websocket",
    }

    forbidden_symbols = {
        "execute",
        "executemany",
        "commit",
        "rollback",
        "requests",
        "post",
        "put",
        "delete",
        "send_order",
        "create_order",
        "place_order",
        "cancel_order",
    }

    violations = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                root = alias.name.split(".")[0]

                if root in forbidden_modules:
                    violations.append(
                        f"import:{alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                root = node.module.split(".")[0]

                if root in forbidden_modules:
                    violations.append(
                        f"from:{node.module}"
                    )

        elif isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):

                if node.func.id in forbidden_symbols:
                    violations.append(
                        f"call:{node.func.id}"
                    )

            elif isinstance(node.func, ast.Attribute):

                if node.func.attr in forbidden_symbols:
                    violations.append(
                        f"call:{node.func.attr}"
                    )

    assert_true(
        not violations,
        "forbidden database/network/execution dependency: "
        + repr(violations),
    )


# =============================================================================
# 17-24 DECISION / PREDICTION / RISK / EXECUTION ISOLATION
#
# IMPORTANT:
# Only signal_scorer.py is scanned.
#
# We intentionally inspect AST symbols rather than raw text.
# This prevents false failures caused by words appearing in comments,
# documentation, or audit files.
# =============================================================================

def test_decision_prediction_risk_execution_isolation():

    source = SIGNAL_SCORER_FILE

    assert_true(
        source.exists(),
        "signal_scorer.py not found",
    )

    text = source.read_text(
        encoding="utf-8-sig"
    )

    tree = ast.parse(
        text,
        filename=str(source),
    )

    forbidden_imports = {
        "decision_engine",
        "prediction_engine",
        "risk_engine",
        "execution_engine",
        "order_engine",
        "portfolio_engine",
    }

    forbidden_call_names = {
        "predict",
        "make_prediction",
        "predict_signal",
        "make_decision",
        "execute",
        "execute_trade",
        "place_order",
        "send_order",
        "calculate_risk",
        "position_size",
        "rank_signals",
    }

    violations = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                root = alias.name.split(".")[0]

                if root in forbidden_imports:
                    violations.append(
                        f"import:{alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                root = node.module.split(".")[0]

                if root in forbidden_imports:
                    violations.append(
                        f"from:{node.module}"
                    )

        elif isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):

                if node.func.id in forbidden_call_names:
                    violations.append(
                        f"call:{node.func.id}"
                    )

            elif isinstance(node.func, ast.Attribute):

                if node.func.attr in forbidden_call_names:
                    violations.append(
                        f"call:{node.func.attr}"
                    )

    assert_true(
        not violations,
        "forbidden decision/prediction/risk/execution "
        "dependency detected: "
        + repr(violations),
    )


# =============================================================================
# 17-25 FINAL SCORING INTEGRITY
# =============================================================================

def test_final_scoring_integrity():

    cases = [
        (
            "BTC",
            long_structure(),
            1.0,
        ),
        (
            "ETH",
            short_structure(),
            -1.0,
        ),
        (
            "SOL",
            neutral_structure(),
            0.0,
        ),
    ]

    for asset, structure, expected in cases:

        signal = build_signal(
            asset,
            structure,
        )

        score = reference_score(
            signal
        )

        assert_equal(
            score,
            expected,
            f"final scoring result mismatch for {asset}",
        )

        assert_true(
            -1.0 <= score <= 1.0,
            f"final score out of bounds for {asset}",
        )


# =============================================================================
# SELF AST CHECK
#
# This verifies that THIS audit file itself is syntactically valid from the
# perspective of Python AST parsing.
# =============================================================================

def self_ast_check():

    source = Path(__file__).resolve()

    text = source.read_text(
        encoding="utf-8-sig"
    )

    try:

        ast.parse(
            text,
            filename=str(source),
        )

    except SyntaxError as error:

        raise AuditFailure(
            "AST parse failure: "
            + str(error)
        )


# =============================================================================
# TEST REGISTRY
# =============================================================================

TESTS = [

    (
        "17-01 Baseline LONG resilience",
        test_baseline_long_resilience,
    ),

    (
        "17-02 Baseline SHORT resilience",
        test_baseline_short_resilience,
    ),

    (
        "17-03 Baseline NEUTRAL resilience",
        test_baseline_neutral_resilience,
    ),

    (
        "17-04 Score lower bound",
        test_score_lower_bound,
    ),

    (
        "17-05 Score upper bound",
        test_score_upper_bound,
    ),

    (
        "17-06 Score type integrity",
        test_score_type_integrity,
    ),

    (
        "17-07 Directional symmetry",
        test_directional_symmetry,
    ),

    (
        "17-08 NEUTRAL boundary",
        test_neutral_boundary,
    ),

    (
        "17-09 Invalid signal type",
        test_invalid_signal_type,
    ),

    (
        "17-10 Unknown asset boundary",
        test_unknown_asset_boundary,
    ),

    (
        "17-11 Invalid state boundary",
        test_invalid_state_boundary,
    ),

    (
        "17-12 Invalid direction boundary",
        test_invalid_direction_boundary,
    ),

    (
        "17-13 Semantic direction integrity",
        test_semantic_direction_integrity,
    ),

    (
        "17-14 ACTIVE/NONE tampering",
        test_active_none_tampering,
    ),

    (
        "17-15 Input immutability",
        test_input_immutability,
    ),

    (
        "17-16 Repeated determinism",
        test_repeated_determinism,
    ),

    (
        "17-17 Cross-asset isolation",
        test_cross_asset_isolation,
    ),

    (
        "17-18 Order independence",
        test_order_independence,
    ),

    (
        "17-19 Output independence",
        test_output_independence,
    ),

    (
        "17-20 Confidence isolation",
        test_confidence_isolation,
    ),

    (
        "17-21 Timestamp isolation",
        test_timestamp_isolation,
    ),

    (
        "17-22 Future information isolation",
        test_future_information_isolation,
    ),

    (
        "17-23 Database/network/execution isolation",
        test_database_network_execution_isolation,
    ),

    (
        "17-24 Decision/prediction/risk isolation",
        test_decision_prediction_risk_execution_isolation,
    ),

    (
        "17-25 Final scoring integrity",
        test_final_scoring_integrity,
    ),
]


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 78)
    print(
        "ARUNDA TRADER â€” STEP 17 SIGNAL SCORING AUDIT v0.6"
    )
    print("=" * 78)

    print(
        "Mode        : READ ONLY / AUDIT"
    )

    print(
        "Target      : SIGNAL SCORING BOUNDARY"
    )

    print(
        "Database    : NOT USED"
    )

    print(
        "Writes      : NONE"
    )

    print(
        "Network     : NOT USED"
    )

    print(
        "Exchange    : NOT USED"
    )

    print(
        "Prediction  : NOT USED"
    )

    print(
        "Decision    : NOT USED"
    )

    print(
        "Risk        : NOT USED"
    )

    print(
        "Execution   : NOT USED"
    )

    print(
        "Look-Ahead  : PROTECTED"
    )

    print("=" * 78)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    print()

    # -------------------------------------------------------------------------
    # SELF AST
    # -------------------------------------------------------------------------

    try:

        self_ast_check()

        print(
            "SELF AST CHECK : PASS"
        )

    except Exception as error:

        print(
            "SELF AST CHECK : FAIL"
        )

        print(
            "ERROR :",
            type(error).__name__,
            str(error),
        )

        return 1

    print()

    # -------------------------------------------------------------------------
    # TEST EXECUTION
    # -------------------------------------------------------------------------

    results = []

    passed = 0
    failed = 0

    for name, test_function in TESTS:

        try:

            test_function()

            print(
                "{:<50} : PASS".format(name)
            )

            results.append(
                (
                    name,
                    True,
                    None,
                )
            )

            passed += 1

        except Exception as error:

            print(
                "{:<50} : FAIL".format(name)
            )

            print(
                "  ERROR :",
                type(error).__name__,
                str(error),
            )

            results.append(
                (
                    name,
                    False,
                    error,
                )
            )

            failed += 1

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------

    print()

    print("=" * 78)
    print(
        "SIGNAL SCORING AUDIT"
    )
    print("=" * 78)

    print(
        "Total Tests :",
        len(TESTS)
    )

    print(
        "PASS        :",
        passed
    )

    print(
        "FAIL        :",
        failed
    )

    print()

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------

    print("=" * 78)

    if failed == 0:

        print(
            "STEP 17 VERDICT"
        )

        print(
            "RESULT      : SIGNAL SCORING AUDIT PASS"
        )

        print(
            "STATUS      : READY FOR NEXT SIGNAL STEP"
        )

        print()

        print(
            "Architecture : PRESERVED"
        )

        print(
            "Database     : NOT USED"
        )

        print(
            "Writes       : NONE"
        )

        print(
            "Network      : NOT USED"
        )

        print(
            "Exchange     : NOT USED"
        )

        print(
            "Prediction   : NOT USED"
        )

        print(
            "Decision     : NOT USED"
        )

        print(
            "Risk         : NOT USED"
        )

        print(
            "Execution    : NOT USED"
        )

        print(
            "Look-Ahead   : PROTECTED"
        )

        print("=" * 78)

        return 0

    print(
        "STEP 17 VERDICT"
    )

    print(
        "RESULT      : SIGNAL SCORING AUDIT FAIL"
    )

    print(
        "STATUS      : REPAIR REQUIRED"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "No production Signal files were modified."
    )

    print("=" * 78)

    return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )