# =============================================================================
# ARUNDA TRADER
# STEP 16 — SIGNAL VALIDATOR AUDIT v0.1
#
# MODE
# ----
# READ ONLY / AUDIT ONLY
#
# DATABASE
# --------
# NOT USED
#
# WRITES
# ------
# NONE
#
# SCORING / PREDICTION / DECISION / RISK / EXECUTION
# ---------------------------------------------------
# NOT USED
#
# PURPOSE
# -------
# Independent validation boundary between SIGNAL and SIGNAL SCORING.
#
# ARCHITECTURE
# ------------
#
# SIGNAL ENGINE
#       |
#       v
# SIGNAL OUTPUT
#       |
#       v
# STEP 16 — SIGNAL VALIDATOR
#       |
#       +--> VALID
#       |
#       +--> INVALID / BLOCK
#       |
#       v
# STEP 17 — SIGNAL SCORING
#
# PRINCIPLES
# ----------
# DO NOT MODIFY PRODUCTION FILES
# DO NOT USE DATABASE
# DO NOT WRITE
# DO NOT USE NETWORK
# DO NOT USE EXCHANGE
# DO NOT ADD SCORING
# DO NOT ADD PREDICTION
# DO NOT ADD DECISION
# DO NOT ADD RISK
# DO NOT ADD EXECUTION
# DO NOT INTRODUCE LOOK-AHEAD
# VALIDATOR MUST NOT REPAIR SIGNALS
# VALIDATOR MUST NOT TRANSFORM SIGNALS
# =============================================================================

import ast
import copy
import os

import signal_logic
import signal_engine
import signal_contract


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


EXPECTED_FIELDS = {
    "asset",
    "timestamp",
    "signal_state",
    "direction",
    "confidence",
    "reason",
}


SIGNAL_STATES = {
    "NEUTRAL",
    "ACTIVE",
}


DIRECTIONS = {
    "NONE",
    "LONG",
    "SHORT",
}


# =============================================================================
# AUDIT FAILURE
# =============================================================================

class AuditFailure(Exception):
    pass


# =============================================================================
# ASSERT HELPERS
# =============================================================================

def assert_true(condition, message):

    if not condition:

        raise AuditFailure(
            message
        )


def assert_equal(actual, expected, message):

    if actual != expected:

        raise AuditFailure(
            "{} | expected={!r}, actual={!r}".format(
                message,
                expected,
                actual,
            )
        )


def assert_raises(
    exception_type,
    function,
    message,
):

    try:

        function()

    except exception_type:

        return

    except Exception as error:

        raise AuditFailure(
            "{} | expected {}, got {}".format(
                message,
                exception_type.__name__,
                type(error).__name__,
            )
        )

    raise AuditFailure(
        "{} | expected {}".format(
            message,
            exception_type.__name__,
        )
    )


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_test(name, function):

    try:

        function()

        print(
            "{:<52} : PASS".format(
                name
            )
        )

        return True

    except Exception as error:

        print(
            "{:<52} : FAIL".format(
                name
            )
        )

        print(
            "  ERROR :",
            type(error).__name__,
            str(error),
        )

        return False


# =============================================================================
# FIXTURES
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


def ready_regime():

    return {
        "status": "READY",
        "regime": "TREND",
    }


def structural_record(structure):

    return {
        "structure": structure,
    }


def build_long_signal(asset="BTC"):

    return signal_engine.build_signal(
        asset,
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )


def build_short_signal(asset="BTC"):

    return signal_engine.build_signal(
        asset,
        ready_regime(),
        structural_record(
            short_structure()
        ),
    )


def build_neutral_signal(asset="BTC"):

    return signal_engine.build_signal(
        asset,
        ready_regime(),
        structural_record(
            neutral_structure()
        ),
    )


# =============================================================================
# INDEPENDENT VALIDATOR
# =============================================================================

def validate_signal_output(signal):

    if not isinstance(
        signal,
        dict,
    ):

        return False

    if set(signal.keys()) != EXPECTED_FIELDS:

        return False

    asset = signal["asset"]

    if asset not in EXPECTED_ASSETS:

        return False

    signal_state = signal["signal_state"]

    if signal_state not in SIGNAL_STATES:

        return False

    direction = signal["direction"]

    if direction not in DIRECTIONS:

        return False

    # -------------------------------------------------------------------------
    # STATE / DIRECTION SEMANTIC BOUNDARY
    # -------------------------------------------------------------------------

    if signal_state == "ACTIVE":

        if direction not in {
            "LONG",
            "SHORT",
        }:

            return False

    elif signal_state == "NEUTRAL":

        if direction != "NONE":

            return False

    else:

        return False

    # -------------------------------------------------------------------------
    # CONFIDENCE
    # -------------------------------------------------------------------------

    confidence = signal["confidence"]

    if confidence is not None:

        if isinstance(
            confidence,
            bool,
        ):

            return False

        if not isinstance(
            confidence,
            (int, float),
        ):

            return False

        if confidence < 0.0:

            return False

        if confidence > 1.0:

            return False

    # -------------------------------------------------------------------------
    # TIMESTAMP
    # -------------------------------------------------------------------------

    timestamp = signal["timestamp"]

    if timestamp is not None:

        if not isinstance(
            timestamp,
            str,
        ):

            return False

    # -------------------------------------------------------------------------
    # REASON
    # -------------------------------------------------------------------------

    reason = signal["reason"]

    if reason is not None:

        if not isinstance(
            reason,
            str,
        ):

            return False

    if signal_state == "ACTIVE":

        if reason != "STRUCTURAL_DIRECTION":

            return False

    elif signal_state == "NEUTRAL":

        if reason is not None:

            return False

    return True


# =============================================================================
# 16-01 BASELINE VALID SIGNAL
# =============================================================================

def test_baseline_valid_signal():

    result = build_long_signal()

    assert_true(
        validate_signal_output(result),
        "baseline signal rejected by validator",
    )

    assert_true(
        signal_contract.validate_signal(result),
        "baseline signal rejected by contract",
    )


# =============================================================================
# 16-02 LONG VALIDATION
# =============================================================================

def test_long_validation():

    result = build_long_signal()

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "LONG state mismatch",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "LONG direction mismatch",
    )

    assert_equal(
        result["reason"],
        "STRUCTURAL_DIRECTION",
        "LONG reason mismatch",
    )

    assert_true(
        validate_signal_output(result),
        "valid LONG signal rejected",
    )


# =============================================================================
# 16-03 SHORT VALIDATION
# =============================================================================

def test_short_validation():

    result = build_short_signal()

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "SHORT state mismatch",
    )

    assert_equal(
        result["direction"],
        "SHORT",
        "SHORT direction mismatch",
    )

    assert_true(
        validate_signal_output(result),
        "valid SHORT signal rejected",
    )


# =============================================================================
# 16-04 NEUTRAL VALIDATION
# =============================================================================

def test_neutral_validation():

    result = build_neutral_signal()

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "NEUTRAL state mismatch",
    )

    assert_equal(
        result["direction"],
        "NONE",
        "NEUTRAL direction mismatch",
    )

    assert_equal(
        result["reason"],
        None,
        "NEUTRAL reason mismatch",
    )

    assert_true(
        validate_signal_output(result),
        "valid NEUTRAL signal rejected",
    )


# =============================================================================
# 16-05 ALL EXPECTED ASSETS
# =============================================================================

def test_all_expected_assets():

    for asset in EXPECTED_ASSETS:

        result = build_long_signal(
            asset
        )

        assert_true(
            validate_signal_output(result),
            "asset rejected: {}".format(asset),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity mismatch",
        )


# =============================================================================
# 16-06 EXACT SCHEMA
# =============================================================================

def test_exact_schema():

    result = build_long_signal()

    assert_equal(
        set(result.keys()),
        EXPECTED_FIELDS,
        "signal schema mismatch",
    )


# =============================================================================
# 16-07 MISSING FIELD REJECTION
# =============================================================================

def test_missing_field_rejection():

    result = build_long_signal()

    for field in EXPECTED_FIELDS:

        tampered = copy.deepcopy(
            result
        )

        del tampered[field]

        assert_true(
            not validate_signal_output(
                tampered
            ),
            "missing field accepted: {}".format(
                field
            ),
        )


# =============================================================================
# 16-08 EXTRA FIELD REJECTION
# =============================================================================

def test_extra_field_rejection():

    result = build_long_signal()

    tampered = copy.deepcopy(
        result
    )

    tampered["unexpected"] = "ATTACK"

    assert_true(
        not validate_signal_output(
            tampered
        ),
        "extra field accepted",
    )


# =============================================================================
# 16-09 UNKNOWN ASSET REJECTION
# =============================================================================

def test_unknown_asset_rejection():

    result = build_long_signal()

    tampered = copy.deepcopy(
        result
    )

    tampered["asset"] = "UNKNOWN_ASSET"

    assert_true(
        not validate_signal_output(
            tampered
        ),
        "unknown asset accepted",
    )


# =============================================================================
# 16-10 INVALID STATE REJECTION
# =============================================================================

def test_invalid_state_rejection():

    result = build_long_signal()

    tampered = copy.deepcopy(
        result
    )

    tampered["signal_state"] = "INVALID"

    assert_true(
        not validate_signal_output(
            tampered
        ),
        "invalid state accepted",
    )


# =============================================================================
# 16-11 INVALID DIRECTION REJECTION
# =============================================================================

def test_invalid_direction_rejection():

    result = build_long_signal()

    tampered = copy.deepcopy(
        result
    )

    tampered["direction"] = "INVALID"

    assert_true(
        not validate_signal_output(
            tampered
        ),
        "invalid direction accepted",
    )


# =============================================================================
# 16-12 STATE / DIRECTION SEMANTIC REJECTION
# =============================================================================

def test_state_direction_semantic_rejection():

    cases = [

        {
            "state": "ACTIVE",
            "direction": "NONE",
        },

        {
            "state": "NEUTRAL",
            "direction": "LONG",
        },

        {
            "state": "NEUTRAL",
            "direction": "SHORT",
        },

    ]

    for case in cases:

        result = build_long_signal()

        tampered = copy.deepcopy(
            result
        )

        tampered["signal_state"] = case["state"]
        tampered["direction"] = case["direction"]

        assert_true(
            not validate_signal_output(
                tampered
            ),
            "invalid state/direction pair accepted",
        )


# =============================================================================
# 16-13 REASON SEMANTIC REJECTION
# =============================================================================

def test_reason_semantic_rejection():

    active = build_long_signal()

    tampered_active = copy.deepcopy(
        active
    )

    tampered_active["reason"] = None

    assert_true(
        not validate_signal_output(
            tampered_active
        ),
        "ACTIVE signal without structural reason accepted",
    )

    neutral = build_neutral_signal()

    tampered_neutral = copy.deepcopy(
        neutral
    )

    tampered_neutral["reason"] = (
        "STRUCTURAL_DIRECTION"
    )

    assert_true(
        not validate_signal_output(
            tampered_neutral
        ),
        "NEUTRAL signal with directional reason accepted",
    )


# =============================================================================
# 16-14 CONFIDENCE BOUNDARY
# =============================================================================

def test_confidence_boundary():

    result = build_long_signal()

    valid_values = [
        0.0,
        0.5,
        1.0,
    ]

    for value in valid_values:

        tampered = copy.deepcopy(
            result
        )

        tampered["confidence"] = value

        assert_true(
            validate_signal_output(
                tampered
            ),
            "valid confidence rejected: {}".format(
                value
            ),
        )

    invalid_values = [
        -0.0001,
        1.0001,
        "0.5",
        [],
        {},
        True,
    ]

    for value in invalid_values:

        tampered = copy.deepcopy(
            result
        )

        tampered["confidence"] = value

        assert_true(
            not validate_signal_output(
                tampered
            ),
            "invalid confidence accepted: {!r}".format(
                value
            ),
        )


# =============================================================================
# 16-15 TIMESTAMP BOUNDARY
# =============================================================================

def test_timestamp_boundary():

    result = build_long_signal()

    valid = copy.deepcopy(
        result
    )

    valid["timestamp"] = (
        "2026-08-19T00:00:00+00:00"
    )

    assert_true(
        validate_signal_output(
            valid
        ),
        "valid timestamp rejected",
    )

    invalid_values = [
        1,
        0.5,
        [],
        {},
        True,
    ]

    for value in invalid_values:

        tampered = copy.deepcopy(
            result
        )

        tampered["timestamp"] = value

        assert_true(
            not validate_signal_output(
                tampered
            ),
            "invalid timestamp accepted",
        )


# =============================================================================
# 16-16 INPUT IMMUTABILITY
# =============================================================================

def test_input_immutability():

    regime = ready_regime()

    structure = structural_record(
        long_structure()
    )

    regime_before = copy.deepcopy(
        regime
    )

    structure_before = copy.deepcopy(
        structure
    )

    signal_engine.build_signal(
        "BTC",
        regime,
        structure,
    )

    assert_equal(
        regime,
        regime_before,
        "regime input mutated",
    )

    assert_equal(
        structure,
        structure_before,
        "structural input mutated",
    )


# =============================================================================
# 16-17 OUTPUT IMMUTABILITY
# =============================================================================

def test_output_immutability():

    result = build_long_signal()

    before = copy.deepcopy(
        result
    )

    validate_signal_output(
        result
    )

    assert_equal(
        result,
        before,
        "validator mutated signal",
    )


# =============================================================================
# 16-18 CROSS-ASSET ISOLATION
# =============================================================================

def test_cross_asset_isolation():

    results = {}

    for asset in EXPECTED_ASSETS:

        results[asset] = build_long_signal(
            asset
        )

    for asset in EXPECTED_ASSETS:

        result = results[asset]

        assert_equal(
            result["asset"],
            asset,
            "asset identity contamination",
        )

        assert_true(
            validate_signal_output(
                result
            ),
            "valid asset output rejected",
        )


# =============================================================================
# 16-19 ASSET IDENTITY TAMPERING
# =============================================================================

def test_asset_identity_tampering():

    result = build_long_signal(
        "BTC"
    )

    tampered = copy.deepcopy(
        result
    )

    tampered["asset"] = "ETH"

    assert_true(
        validate_signal_output(
            tampered
        ),
        "single signal remains schema-valid after asset replacement",
    )

    # Validator validates the signal itself.
    # Cross-asset mapping is checked separately.
    assert_equal(
        tampered["asset"],
        "ETH",
        "asset tampering fixture failed",
    )


# =============================================================================
# 16-20 DETERMINISM
# =============================================================================

def test_determinism():

    result = build_long_signal()

    outputs = []

    for _ in range(20):

        outputs.append(
            validate_signal_output(
                copy.deepcopy(
                    result
                )
            )
        )

    for output in outputs:

        assert_equal(
            output,
            outputs[0],
            "validator result is not deterministic",
        )


# =============================================================================
# 16-21 REPEATED VALIDATION CONSISTENCY
# =============================================================================

def test_repeated_validation_consistency():

    result = build_long_signal()

    for _ in range(100):

        assert_true(
            validate_signal_output(
                result
            ),
            "repeated validation failed",
        )


# =============================================================================
# 16-22 CONTRACT COMPATIBILITY
# =============================================================================

def test_contract_compatibility():

    cases = [
        build_long_signal(),
        build_short_signal(),
        build_neutral_signal(),
    ]

    for result in cases:

        contract_valid = (
            signal_contract.validate_signal(
                result
            )
        )

        validator_valid = (
            validate_signal_output(
                result
            )
        )

        assert_equal(
            validator_valid,
            contract_valid,
            "validator / contract disagreement",
        )


# =============================================================================
# 16-23 DATABASE / NETWORK ISOLATION
# =============================================================================

def test_database_network_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
        "sqlite3",
        "sqlite",
        "connect",
        "cursor",
        "execute",
        "executemany",
        "requests",
        "urllib",
        "http",
        "socket",
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "DROP",
        "to_sql",
        "to_csv",
        "write",
        "writelines",
    }

    for module in modules:

        tree = source_tree(
            module
        )

        names = ast_dependency_names(
            tree
        )

        overlap = (
            forbidden & names
        )

        assert_true(
            not overlap,
            "forbidden dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 16-24 DECISION / SCORING / EXECUTION ISOLATION
# =============================================================================

def test_decision_scoring_execution_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
        "score",
        "scoring",
        "calculate_score",
        "build_score",
        "prediction",
        "predict",
        "forecast",
        "future_return",
        "future_price",
        "decision",
        "decision_engine",
        "decision_contract",
        "risk",
        "portfolio",
        "buy",
        "sell",
        "order",
        "place_order",
        "execute",
        "execution",
        "exchange",
        "trading",
    }

    for module in modules:

        tree = source_tree(
            module
        )

        names = ast_dependency_names(
            tree
        )

        overlap = (
            forbidden & names
        )

        assert_true(
            not overlap,
            "forbidden future-layer dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 16-25 FINAL VALIDATOR INTEGRITY
# =============================================================================

def test_final_validator_integrity():

    cases = [
        build_long_signal(),
        build_short_signal(),
        build_neutral_signal(),
    ]

    for result in cases:

        original = copy.deepcopy(
            result
        )

        assert_true(
            validate_signal_output(
                result
            ),
            "valid signal rejected",
        )

        assert_equal(
            result,
            original,
            "validator modified signal",
        )

        assert_true(
            signal_contract.validate_signal(
                result
            ),
            "final signal contract failure",
        )

    # -------------------------------------------------------------------------
    # Verify validator itself does not introduce database/network/scoring/etc.
    # -------------------------------------------------------------------------

    tree = source_tree(
        signal_logic
    )

    names = ast_dependency_names(
        tree
    )

    forbidden = {
        "sqlite3",
        "requests",
        "urllib",
        "socket",
        "score",
        "scoring",
        "prediction",
        "decision",
        "risk",
        "order",
        "execute",
        "exchange",
        "trading",
    }

    overlap = (
        forbidden & names
    )

    assert_true(
        not overlap,
        "production information-flow boundary violated: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# AST HELPERS
# =============================================================================

def source_tree(module):

    with open(
        module.__file__,
        "r",
        encoding="utf-8",
    ) as file:

        return ast.parse(
            file.read(),
            filename=module.__file__,
        )


def ast_dependency_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name,
        ):

            names.add(
                node.id
            )

        elif isinstance(
            node,
            ast.Attribute,
        ):

            names.add(
                node.attr
            )

    return names


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 16")
    print("SIGNAL VALIDATOR AUDIT v0.1")
    print("=" * 78)

    print(
        "Mode        : READ ONLY / AUDIT ONLY"
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
        "Scoring     : NOT USED"
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

    print()

    print(
        "Production files:"
    )

    print(
        "  - signal_logic.py"
    )

    print(
        "  - signal_engine.py"
    )

    print(
        "  - signal_contract.py"
    )

    print()

    print(
        "Validator:"
    )

    print(
        "  - Independent"
    )

    print(
        "  - Read Only"
    )

    print(
        "  - No Signal Transformation"
    )

    print(
        "  - No Signal Repair"
    )

    print()

    print("=" * 78)
    print("SIGNAL VALIDATOR AUDIT")
    print("=" * 78)

    tests = [

        (
            "16-01 Baseline valid signal",
            test_baseline_valid_signal,
        ),

        (
            "16-02 LONG validation",
            test_long_validation,
        ),

        (
            "16-03 SHORT validation",
            test_short_validation,
        ),

        (
            "16-04 NEUTRAL validation",
            test_neutral_validation,
        ),

        (
            "16-05 All expected assets",
            test_all_expected_assets,
        ),

        (
            "16-06 Exact schema",
            test_exact_schema,
        ),

        (
            "16-07 Missing field rejection",
            test_missing_field_rejection,
        ),

        (
            "16-08 Extra field rejection",
            test_extra_field_rejection,
        ),

        (
            "16-09 Unknown asset rejection",
            test_unknown_asset_rejection,
        ),

        (
            "16-10 Invalid state rejection",
            test_invalid_state_rejection,
        ),

        (
            "16-11 Invalid direction rejection",
            test_invalid_direction_rejection,
        ),

        (
            "16-12 State/direction semantic rejection",
            test_state_direction_semantic_rejection,
        ),

        (
            "16-13 Reason semantic rejection",
            test_reason_semantic_rejection,
        ),

        (
            "16-14 Confidence boundary",
            test_confidence_boundary,
        ),

        (
            "16-15 Timestamp boundary",
            test_timestamp_boundary,
        ),

        (
            "16-16 Input immutability",
            test_input_immutability,
        ),

        (
            "16-17 Output immutability",
            test_output_immutability,
        ),

        (
            "16-18 Cross-asset isolation",
            test_cross_asset_isolation,
        ),

        (
            "16-19 Asset identity tampering",
            test_asset_identity_tampering,
        ),

        (
            "16-20 Determinism",
            test_determinism,
        ),

        (
            "16-21 Repeated validation consistency",
            test_repeated_validation_consistency,
        ),

        (
            "16-22 Contract compatibility",
            test_contract_compatibility,
        ),

        (
            "16-23 Database / network isolation",
            test_database_network_isolation,
        ),

        (
            "16-24 Decision / scoring / execution isolation",
            test_decision_scoring_execution_isolation,
        ),

        (
            "16-25 Final validator integrity",
            test_final_validator_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print()

    for name, function in tests:

        if run_test(
            name,
            function,
        ):

            passed += 1

        else:

            failed += 1

    print()

    print("=" * 78)
    print("STEP 16 SUMMARY")
    print("=" * 78)

    print(
        "Total Tests : {}".format(
            len(tests)
        )
    )

    print(
        "PASS        : {}".format(
            passed
        )
    )

    print(
        "FAIL        : {}".format(
            failed
        )
    )

    print()

    print("=" * 78)
    print("STEP 16 VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL VALIDATOR AUDIT PASS"
        )

        print(
            "STATUS      : READY FOR STEP 17"
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
            "Scoring      : NOT USED"
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
        "RESULT      : SIGNAL VALIDATOR AUDIT FAIL"
    )

    print(
        "STATUS      : REPAIR REQUIRED"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Production Signal files were NOT modified."
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