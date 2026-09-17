# =============================================================================
# ARUNDA TRADER
# STEP 15B — SIGNAL SEMANTIC & BOUNDARY BEHAVIOR AUDIT v0.1
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
# PRINCIPLE
# ---------
# DO NOT REBUILD
# DO NOT RESET
# DO NOT REDESIGN
# =============================================================================

import ast
import copy
import os

import signal_engine
import signal_logic
import signal_contract


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


class AuditFailure(Exception):
    pass


def assert_true(condition, message):

    if not condition:
        raise AuditFailure(message)


def assert_equal(actual, expected, message):

    if actual != expected:

        raise AuditFailure(
            "{} | expected={!r}, actual={!r}".format(
                message,
                expected,
                actual,
            )
        )


def assert_raises(exception_type, function, message):

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


def run_test(name, function):

    try:

        function()

        print(
            "{:<52} : PASS".format(name)
        )

        return True

    except Exception as error:

        print(
            "{:<52} : FAIL".format(name)
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


def build_signal(asset, structure):

    return signal_engine.build_signal(
        asset,
        ready_regime(),
        structural_record(structure),
    )


# =============================================================================
# 15B-01 SEMANTIC INVARIANT MATRIX
# =============================================================================

def test_semantic_matrix():

    cases = [
        (
            long_structure(),
            "LONG",
            "ACTIVE",
        ),
        (
            short_structure(),
            "SHORT",
            "ACTIVE",
        ),
        (
            neutral_structure(),
            "NONE",
            "NEUTRAL",
        ),
    ]

    for structure, direction, state in cases:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_equal(
            result["direction"],
            direction,
            "direction semantic invariant failed",
        )

        assert_equal(
            result["signal_state"],
            state,
            "state semantic invariant failed",
        )


# =============================================================================
# 15B-02 LONG BOUNDARY MUTATION
# =============================================================================

def test_long_boundary_mutation():

    base = long_structure()

    mutations = [
        ("trend", "DOWN"),
        ("momentum", "WEAK"),
        ("acceleration", "DECELERATING"),
        ("position", "LOWER"),
    ]

    for field, value in mutations:

        structure = copy.deepcopy(base)
        structure[field] = value

        result = build_signal(
            "BTC",
            structure,
        )

        assert_true(
            result["direction"] != "LONG",
            "LONG survived mutation of {}".format(
                field
            ),
        )


# =============================================================================
# 15B-03 SHORT BOUNDARY MUTATION
# =============================================================================

def test_short_boundary_mutation():

    base = short_structure()

    mutations = [
        ("trend", "UP"),
        ("momentum", "STRONG"),
        ("acceleration", "ACCELERATING"),
        ("position", "UPPER"),
    ]

    for field, value in mutations:

        structure = copy.deepcopy(base)
        structure[field] = value

        result = build_signal(
            "BTC",
            structure,
        )

        assert_true(
            result["direction"] != "SHORT",
            "SHORT survived mutation of {}".format(
                field
            ),
        )


# =============================================================================
# 15B-04 HIGH VOLATILITY UNIVERSAL BLOCK
# =============================================================================

def test_high_volatility_universal_block():

    long_case = long_structure()
    long_case["volatility"] = "HIGH"

    short_case = short_structure()
    short_case["volatility"] = "HIGH"

    long_result = build_signal(
        "BTC",
        long_case,
    )

    short_result = build_signal(
        "BTC",
        short_case,
    )

    assert_equal(
        long_result["direction"],
        "NONE",
        "HIGH volatility failed to block LONG",
    )

    assert_equal(
        short_result["direction"],
        "NONE",
        "HIGH volatility failed to block SHORT",
    )


# =============================================================================
# 15B-05 POSITION BOUNDARY
# =============================================================================

def test_position_boundary():

    long_case = long_structure()
    long_case["position"] = "LOWER"

    short_case = short_structure()
    short_case["position"] = "UPPER"

    long_result = build_signal(
        "BTC",
        long_case,
    )

    short_result = build_signal(
        "BTC",
        short_case,
    )

    assert_equal(
        long_result["direction"],
        "NONE",
        "LOWER position must block LONG",
    )

    assert_equal(
        short_result["direction"],
        "NONE",
        "UPPER position must block SHORT",
    )


# =============================================================================
# 15B-06 MISSING STRUCTURAL FIELDS
# =============================================================================

def test_missing_structural_fields():

    base = long_structure()

    for field in list(base.keys()):

        malformed = copy.deepcopy(base)
        del malformed[field]

        assert_raises(
            RuntimeError,
            lambda malformed=malformed:
                build_signal(
                    "BTC",
                    malformed,
                ),
            "missing structural field must be rejected",
        )


# =============================================================================
# 15B-07 INVALID STRUCTURAL TYPES
# =============================================================================

def test_invalid_structural_types():

    invalid_values = [
        None,
        1,
        0.5,
        [],
        {},
        True,
    ]

    fields = [
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    ]

    for field in fields:

        for value in invalid_values:

            structure = long_structure()
            structure[field] = value

            assert_raises(
                RuntimeError,
                lambda structure=structure:
                    build_signal(
                        "BTC",
                        structure,
                    ),
                "invalid structural type must be rejected: {}".format(
                    field
                ),
            )


# =============================================================================
# 15B-08 INVALID ENUM VALUES
# =============================================================================

def test_invalid_enum_values():

    invalid_values = [
        "INVALID",
        "UNKNOWN",
        "HIGHER",
        "LOWER_THAN_LOW",
        "",
    ]

    fields = [
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    ]

    for field in fields:

        for value in invalid_values:

            structure = long_structure()
            structure[field] = value

            assert_raises(
                RuntimeError,
                lambda structure=structure:
                    build_signal(
                        "BTC",
                        structure,
                    ),
                "invalid structural enum must be rejected: {}".format(
                    field
                ),
            )


# =============================================================================
# 15B-09 MALFORMED CONTAINERS
# =============================================================================

def test_malformed_containers():

    malformed = [
        None,
        [],
        (),
        "",
        0,
        False,
    ]

    for value in malformed:

        assert_raises(
            RuntimeError,
            lambda value=value:
                signal_engine.build_signal(
                    "BTC",
                    ready_regime(),
                    value,
                ),
            "malformed structural container must be rejected",
        )


# =============================================================================
# 15B-10 REGIME GATE BOUNDARY
# =============================================================================

def test_regime_gate_boundary():

    invalid_regimes = [
        {},
        {"status": None},
        {"status": "BLOCKED"},
        {"status": "INVALID"},
        {"status": ""},
        {"status": None, "regime": "TREND"},
    ]

    for regime in invalid_regimes:

        assert_raises(
            RuntimeError,
            lambda regime=regime:
                signal_engine.build_signal(
                    "BTC",
                    regime,
                    structural_record(
                        long_structure()
                    ),
                ),
            "non-READY regime must be rejected",
        )


# =============================================================================
# 15B-11 READY STATE INTEGRITY
# =============================================================================

def test_ready_state_integrity():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "READY regime failed to permit valid signal",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "READY regime altered valid direction",
    )


# =============================================================================
# 15B-12 NON-READY REJECTION
# =============================================================================

def test_non_ready_rejection():

    regimes = [
        {"status": "BLOCKED"},
        {"status": "UNAVAILABLE"},
        {"status": "ERROR"},
        {"status": "NOT_READY"},
    ]

    for regime in regimes:

        assert_raises(
            RuntimeError,
            lambda regime=regime:
                signal_engine.build_signal(
                    "BTC",
                    regime,
                    structural_record(
                        long_structure()
                    ),
                ),
            "non-ready state must reject signal",
        )


# =============================================================================
# 15B-13 CROSS-ASSET ISOLATION
# =============================================================================

def test_cross_asset_isolation():

    results = {}

    for asset in EXPECTED_ASSETS:

        results[asset] = build_signal(
            asset,
            long_structure(),
        )

    for asset in EXPECTED_ASSETS:

        assert_equal(
            results[asset]["asset"],
            asset,
            "asset identity contaminated",
        )

        assert_equal(
            results[asset]["direction"],
            "LONG",
            "asset {} received wrong direction".format(
                asset
            ),
        )


# =============================================================================
# 15B-14 REPEATED DETERMINISM
# =============================================================================

def test_repeated_determinism():

    structure = long_structure()

    outputs = []

    for _ in range(10):

        outputs.append(
            build_signal(
                "BTC",
                copy.deepcopy(structure),
            )
        )

    for output in outputs[1:]:

        assert_equal(
            output,
            outputs[0],
            "repeated execution is not deterministic",
        )


# =============================================================================
# 15B-15 INPUT IMMUTABILITY
# =============================================================================

def test_input_immutability():

    regime = ready_regime()

    structure = structural_record(
        long_structure()
    )

    regime_before = copy.deepcopy(regime)
    structure_before = copy.deepcopy(structure)

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
# 15B-16 SIGNAL FIELD EXACTNESS
# =============================================================================

def test_signal_field_exactness():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    expected = {
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    }

    assert_equal(
        set(result.keys()),
        expected,
        "signal field set changed",
    )


# =============================================================================
# 15B-17 UNEXPECTED FIELD REJECTION
# =============================================================================

def test_unexpected_field_rejection():

    signal = signal_contract.build_empty_signal(
        "BTC"
    )

    signal["unexpected"] = "BAD"

    assert_true(
        not signal_contract.validate_signal(signal),
        "contract accepted unexpected signal field",
    )


# =============================================================================
# 15B-18 CONFIDENCE ISOLATION
# =============================================================================

def test_confidence_isolation():

    for structure in [
        long_structure(),
        short_structure(),
        neutral_structure(),
    ]:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_equal(
            result["confidence"],
            None,
            "confidence must remain uncomputed",
        )


# =============================================================================
# 15B-19 TIMESTAMP ISOLATION
# =============================================================================

def test_timestamp_isolation():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["timestamp"],
        None,
        "timestamp must remain uncomputed",
    )


# =============================================================================
# 15B-20 REASON SEMANTIC INTEGRITY
# =============================================================================

def test_reason_semantic_integrity():

    long_result = build_signal(
        "BTC",
        long_structure(),
    )

    short_result = build_signal(
        "BTC",
        short_structure(),
    )

    neutral_result = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        long_result["reason"],
        "STRUCTURAL_DIRECTION",
        "LONG reason mismatch",
    )

    assert_equal(
        short_result["reason"],
        "STRUCTURAL_DIRECTION",
        "SHORT reason mismatch",
    )

    assert_equal(
        neutral_result["reason"],
        None,
        "NONE reason must be None",
    )


# =============================================================================
# AST DEPENDENCY AUDIT
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

        if isinstance(node, ast.Name):

            names.add(node.id)

        elif isinstance(node, ast.Attribute):

            names.add(node.attr)

    return names


# =============================================================================
# 15B-21 DATABASE ISOLATION
# =============================================================================

def test_database_isolation():

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
    }

    for module in modules:

        tree = source_tree(module)
        names = ast_dependency_names(tree)

        overlap = forbidden & names

        assert_true(
            not overlap,
            "database dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15B-22 WRITE ISOLATION
# =============================================================================

def test_write_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
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

        tree = source_tree(module)

        for node in ast.walk(tree):

            if isinstance(node, ast.Name):

                assert_true(
                    node.id not in forbidden,
                    "write dependency detected: {}".format(
                        node.id
                    ),
                )

            elif isinstance(node, ast.Attribute):

                assert_true(
                    node.attr not in forbidden,
                    "write dependency detected: {}".format(
                        node.attr
                    ),
                )


# =============================================================================
# 15B-23 SCORING ISOLATION
# =============================================================================

def test_scoring_isolation():

    tree = source_tree(signal_engine)

    names = ast_dependency_names(tree)

    forbidden = {
        "signal_scorer",
        "score",
        "scoring",
        "calculate_score",
        "build_score",
    }

    overlap = names & forbidden

    assert_true(
        not overlap,
        "scoring dependency detected: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15B-24 PREDICTION ISOLATION
# =============================================================================

def test_prediction_isolation():

    tree = source_tree(signal_engine)

    names = ast_dependency_names(tree)

    forbidden = {
        "prediction",
        "predict",
        "future_return",
        "future_price",
        "forecast",
    }

    overlap = names & forbidden

    assert_true(
        not overlap,
        "prediction dependency detected: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15B-25 DECISION / EXECUTION ISOLATION
# =============================================================================

def test_decision_execution_isolation():

    tree = source_tree(signal_engine)

    names = ast_dependency_names(tree)

    forbidden = {
        "decision",
        "decision_engine",
        "decision_contract",
        "buy",
        "sell",
        "execute",
        "order",
        "place_order",
    }

    overlap = names & forbidden

    assert_true(
        not overlap,
        "decision/execution dependency detected: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15B")
    print("SIGNAL SEMANTIC & BOUNDARY BEHAVIOR AUDIT v0.1")
    print("=" * 78)

    print("Mode        : READ ONLY / AUDIT ONLY")
    print("Database    : NOT USED")
    print("Writes      : NONE")
    print("Scoring     : NOT USED")
    print("Prediction  : NOT USED")
    print("Decision     : NOT USED")
    print("Execution   : NOT USED")
    print()

    print("Production files:")
    print("  - signal_logic.py")
    print("  - signal_engine.py")
    print("  - signal_contract.py")
    print("=" * 78)
    print()

    tests = [

        ("15B-01 Semantic invariant matrix",
         test_semantic_matrix),

        ("15B-02 LONG boundary mutation",
         test_long_boundary_mutation),

        ("15B-03 SHORT boundary mutation",
         test_short_boundary_mutation),

        ("15B-04 HIGH volatility universal block",
         test_high_volatility_universal_block),

        ("15B-05 Position boundary",
         test_position_boundary),

        ("15B-06 Missing structural fields",
         test_missing_structural_fields),

        ("15B-07 Invalid structural types",
         test_invalid_structural_types),

        ("15B-08 Invalid enum values",
         test_invalid_enum_values),

        ("15B-09 Malformed containers",
         test_malformed_containers),

        ("15B-10 Regime gate boundary",
         test_regime_gate_boundary),

        ("15B-11 READY state integrity",
         test_ready_state_integrity),

        ("15B-12 Non-READY rejection",
         test_non_ready_rejection),

        ("15B-13 Cross-asset isolation",
         test_cross_asset_isolation),

        ("15B-14 Repeated determinism",
         test_repeated_determinism),

        ("15B-15 Input immutability",
         test_input_immutability),

        ("15B-16 Signal field exactness",
         test_signal_field_exactness),

        ("15B-17 Unexpected field rejection",
         test_unexpected_field_rejection),

        ("15B-18 Confidence isolation",
         test_confidence_isolation),

        ("15B-19 Timestamp isolation",
         test_timestamp_isolation),

        ("15B-20 Reason semantic integrity",
         test_reason_semantic_integrity),

        ("15B-21 Database isolation",
         test_database_isolation),

        ("15B-22 Write isolation",
         test_write_isolation),

        ("15B-23 Scoring isolation",
         test_scoring_isolation),

        ("15B-24 Prediction isolation",
         test_prediction_isolation),

        ("15B-25 Decision/execution isolation",
         test_decision_execution_isolation),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("BEHAVIORAL / BOUNDARY AUDIT")
    print("=" * 78)

    for name, function in tests:

        if run_test(name, function):

            passed += 1

        else:

            failed += 1

    print()
    print("=" * 78)
    print("STEP 15B SUMMARY")
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
    print("STEP 15B VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL SEMANTIC & BOUNDARY AUDIT PASS"
        )

        print(
            "STATUS      : READY FOR NEXT SIGNAL STEP"
        )

        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Scoring      : NOT USED")
        print("Prediction   : NOT USED")
        print("Decision     : NOT USED")
        print("Execution    : NOT USED")
        print("Look-Ahead   : PROTECTED")

        print("=" * 78)

        return 0

    print(
        "RESULT      : SIGNAL SEMANTIC & BOUNDARY AUDIT FAIL"
    )

    print(
        "STATUS      : REPAIR REQUIRED"
    )

    print()
    print("IMPORTANT:")
    print("Production Signal files were NOT modified.")
    print("=" * 78)

    return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )