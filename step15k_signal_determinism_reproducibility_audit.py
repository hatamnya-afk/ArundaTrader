# =============================================================================
# ARUNDA TRADER
# STEP 15K — SIGNAL DETERMINISM & REPRODUCIBILITY AUDIT v0.1
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
# PURPOSE
# -------
# Verify that the Signal Layer produces deterministic and reproducible output
# under identical inputs and independent execution conditions.
#
# PRODUCTION FILES
# ----------------
# signal_logic.py
# signal_engine.py
# signal_contract.py
#
# PRINCIPLES
# ----------
# DO NOT MODIFY PRODUCTION FILES
# DO NOT USE DATABASE
# DO NOT WRITE
# DO NOT USE NETWORK
# DO NOT USE ENVIRONMENT STATE
# DO NOT USE CURRENT TIME
# DO NOT USE RANDOMNESS
# DO NOT ADD SCORING
# DO NOT ADD PREDICTION
# DO NOT ADD DECISION
# DO NOT ADD EXECUTION
# DO NOT INTRODUCE LOOK-AHEAD
# =============================================================================

import ast
import copy
import os
import random

import signal_logic
import signal_engine
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


# =============================================================================
# AUDIT UTILITIES
# =============================================================================

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
            "{:<54} : PASS".format(name)
        )

        return True

    except Exception as error:

        print(
            "{:<54} : FAIL".format(name)
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

        if isinstance(node, ast.Name):

            names.add(node.id)

        elif isinstance(node, ast.Attribute):

            names.add(node.attr)

    return names


# =============================================================================
# 15K-01 BASELINE LONG DETERMINISM
# =============================================================================

def test_baseline_long_determinism():

    structure = long_structure()

    first = build_signal(
        "BTC",
        copy.deepcopy(structure),
    )

    second = build_signal(
        "BTC",
        copy.deepcopy(structure),
    )

    assert_equal(
        first,
        second,
        "identical LONG inputs produced different outputs",
    )


# =============================================================================
# 15K-02 BASELINE SHORT DETERMINISM
# =============================================================================

def test_baseline_short_determinism():

    structure = short_structure()

    first = build_signal(
        "ETH",
        copy.deepcopy(structure),
    )

    second = build_signal(
        "ETH",
        copy.deepcopy(structure),
    )

    assert_equal(
        first,
        second,
        "identical SHORT inputs produced different outputs",
    )


# =============================================================================
# 15K-03 BASELINE NEUTRAL DETERMINISM
# =============================================================================

def test_baseline_neutral_determinism():

    structure = neutral_structure()

    first = build_signal(
        "SOL",
        copy.deepcopy(structure),
    )

    second = build_signal(
        "SOL",
        copy.deepcopy(structure),
    )

    assert_equal(
        first,
        second,
        "identical NEUTRAL inputs produced different outputs",
    )


# =============================================================================
# 15K-04 REPEATED EXECUTION
# =============================================================================

def test_repeated_execution():

    structure = long_structure()

    outputs = []

    for _ in range(100):

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
            "100 repeated executions were not identical",
        )


# =============================================================================
# 15K-05 DEEP COPY INPUT REPRODUCIBILITY
# =============================================================================

def test_deepcopy_reproducibility():

    original = long_structure()

    first = build_signal(
        "BTC",
        copy.deepcopy(original),
    )

    cloned = copy.deepcopy(original)

    second = build_signal(
        "BTC",
        cloned,
    )

    assert_equal(
        first,
        second,
        "deep-copied equivalent input changed output",
    )


# =============================================================================
# 15K-06 REGIME REPRODUCIBILITY
# =============================================================================

def test_regime_reproducibility():

    structure = structural_record(
        long_structure()
    )

    regime_one = ready_regime()
    regime_two = ready_regime()

    first = signal_engine.build_signal(
        "BTC",
        regime_one,
        copy.deepcopy(structure),
    )

    second = signal_engine.build_signal(
        "BTC",
        regime_two,
        copy.deepcopy(structure),
    )

    assert_equal(
        first,
        second,
        "equivalent regime inputs changed output",
    )


# =============================================================================
# 15K-07 CROSS-ASSET REPRODUCIBILITY
# =============================================================================

def test_cross_asset_reproducibility():

    for asset in EXPECTED_ASSETS:

        structure = long_structure()

        first = build_signal(
            asset,
            copy.deepcopy(structure),
        )

        second = build_signal(
            asset,
            copy.deepcopy(structure),
        )

        assert_equal(
            first,
            second,
            "asset {} is not reproducible".format(asset),
        )


# =============================================================================
# 15K-08 ASSET ORDER REPRODUCIBILITY
# =============================================================================

def test_asset_order_reproducibility():

    first_map = {}

    for asset in EXPECTED_ASSETS:

        first_map[asset] = build_signal(
            asset,
            long_structure(),
        )

    second_map = {}

    reversed_assets = list(
        reversed(EXPECTED_ASSETS)
    )

    for asset in reversed_assets:

        second_map[asset] = build_signal(
            asset,
            long_structure(),
        )

    assert_equal(
        first_map,
        second_map,
        "asset execution order changed aggregate outputs",
    )


# =============================================================================
# 15K-09 INPUT IMMUTABILITY
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

    build_signal = signal_engine.build_signal

    build_signal(
        "BTC",
        regime,
        structure,
    )

    assert_equal(
        regime,
        regime_before,
        "regime input changed during execution",
    )

    assert_equal(
        structure,
        structure_before,
        "structural input changed during execution",
    )


# =============================================================================
# 15K-10 OUTPUT ISOLATION
# =============================================================================

def test_output_isolation():

    first = build_signal(
        "BTC",
        long_structure(),
    )

    second = build_signal(
        "BTC",
        long_structure(),
    )

    first["direction"] = "SHORT"

    assert_equal(
        second["direction"],
        "LONG",
        "mutating one output contaminated another output",
    )


# =============================================================================
# 15K-11 OUTPUT CONTRACT REPRODUCIBILITY
# =============================================================================

def test_output_contract_reproducibility():

    for structure in [
        long_structure(),
        short_structure(),
        neutral_structure(),
    ]:

        first = build_signal(
            "BTC",
            copy.deepcopy(structure),
        )

        second = build_signal(
            "BTC",
            copy.deepcopy(structure),
        )

        assert_true(
            signal_contract.validate_signal(first),
            "first output failed contract validation",
        )

        assert_true(
            signal_contract.validate_signal(second),
            "second output failed contract validation",
        )

        assert_equal(
            first,
            second,
            "contract-valid repeated outputs differ",
        )


# =============================================================================
# 15K-12 HIGH VOLATILITY REPRODUCIBILITY
# =============================================================================

def test_high_volatility_reproducibility():

    structure = long_structure()
    structure["volatility"] = "HIGH"

    outputs = []

    for _ in range(20):

        outputs.append(
            build_signal(
                "BTC",
                copy.deepcopy(structure),
            )
        )

    for output in outputs:

        assert_equal(
            output["signal_state"],
            "NEUTRAL",
            "HIGH volatility reproducibility state failure",
        )

        assert_equal(
            output["direction"],
            "NONE",
            "HIGH volatility reproducibility direction failure",
        )

    for output in outputs[1:]:

        assert_equal(
            output,
            outputs[0],
            "HIGH volatility outputs are not deterministic",
        )


# =============================================================================
# 15K-13 POSITION BOUNDARY REPRODUCIBILITY
# =============================================================================

def test_position_boundary_reproducibility():

    structure = long_structure()
    structure["position"] = "LOWER"

    first = build_signal(
        "BTC",
        copy.deepcopy(structure),
    )

    second = build_signal(
        "BTC",
        copy.deepcopy(structure),
    )

    assert_equal(
        first,
        second,
        "position boundary output is not reproducible",
    )

    assert_equal(
        first["direction"],
        "NONE",
        "position boundary changed deterministic result",
    )


# =============================================================================
# 15K-14 NON-READY REJECTION REPRODUCIBILITY
# =============================================================================

def test_non_ready_rejection_reproducibility():

    regimes = [
        {"status": "BLOCKED"},
        {"status": "ERROR"},
        {"status": "UNAVAILABLE"},
        {"status": "NOT_READY"},
    ]

    for regime in regimes:

        for _ in range(5):

            assert_raises(
                RuntimeError,
                lambda regime=copy.deepcopy(regime):
                    signal_engine.build_signal(
                        "BTC",
                        regime,
                        structural_record(
                            long_structure()
                        ),
                    ),
                "non-ready regime behavior is not reproducible",
            )


# =============================================================================
# 15K-15 INVALID INPUT REPRODUCIBILITY
# =============================================================================

def test_invalid_input_reproducibility():

    malformed = long_structure()

    del malformed["trend"]

    for _ in range(10):

        assert_raises(
            RuntimeError,
            lambda malformed=copy.deepcopy(malformed):
                build_signal(
                    "BTC",
                    malformed,
                ),
            "invalid input rejection is not reproducible",
        )


# =============================================================================
# 15K-16 STATE RESET BETWEEN EXECUTIONS
# =============================================================================

def test_state_reset_between_executions():

    long_result = build_signal(
        "BTC",
        long_structure(),
    )

    short_result = build_signal(
        "BTC",
        short_structure(),
    )

    long_result_again = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        long_result_again,
        long_result,
        "previous execution state contaminated later LONG output",
    )

    assert_equal(
        short_result["direction"],
        "SHORT",
        "SHORT execution was contaminated by previous LONG state",
    )


# =============================================================================
# 15K-17 INTERLEAVED EXECUTION
# =============================================================================

def test_interleaved_execution():

    baseline_long = build_signal(
        "BTC",
        long_structure(),
    )

    baseline_short = build_signal(
        "ETH",
        short_structure(),
    )

    baseline_neutral = build_signal(
        "SOL",
        neutral_structure(),
    )

    for _ in range(20):

        current_long = build_signal(
            "BTC",
            long_structure(),
        )

        current_short = build_signal(
            "ETH",
            short_structure(),
        )

        current_neutral = build_signal(
            "SOL",
            neutral_structure(),
        )

        assert_equal(
            current_long,
            baseline_long,
            "interleaved LONG execution changed output",
        )

        assert_equal(
            current_short,
            baseline_short,
            "interleaved SHORT execution changed output",
        )

        assert_equal(
            current_neutral,
            baseline_neutral,
            "interleaved NEUTRAL execution changed output",
        )


# =============================================================================
# 15K-18 RANDOMIZED EXECUTION ORDER
# =============================================================================

def test_randomized_execution_order():

    assets = list(EXPECTED_ASSETS)

    baseline = {}

    for asset in assets:

        baseline[asset] = build_signal(
            asset,
            long_structure(),
        )

    rng = random.Random(12345)

    for _ in range(20):

        shuffled = list(assets)

        rng.shuffle(shuffled)

        current = {}

        for asset in shuffled:

            current[asset] = build_signal(
                asset,
                long_structure(),
            )

        assert_equal(
            current,
            baseline,
            "randomized asset order changed outputs",
        )


# =============================================================================
# 15K-19 SIGNAL LOGIC PURE REPRODUCIBILITY
# =============================================================================

def test_signal_logic_reproducibility():

    function_names = [
        "evaluate_structure",
        "build_signal_direction",
        "determine_direction",
    ]

    available = []

    for name in function_names:

        if hasattr(signal_logic, name):

            available.append(name)

    assert_true(
        len(available) > 0,
        "no recognized signal logic entrypoint found",
    )

    for name in available:

        function = getattr(
            signal_logic,
            name,
        )

        if not callable(function):
            continue

        try:

            first = function(
                long_structure()
            )

            second = function(
                long_structure()
            )

        except TypeError:

            continue

        assert_equal(
            first,
            second,
            "signal logic function {} is not deterministic".format(
                name
            ),
        )


# =============================================================================
# 15K-20 NO RANDOMNESS IN PRODUCTION
# =============================================================================

def test_no_randomness_dependency():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
        "random",
        "randint",
        "randrange",
        "random",
        "choice",
        "shuffle",
        "sample",
        "uniform",
        "gauss",
        "seed",
    }

    for module in modules:

        tree = source_tree(module)

        names = ast_dependency_names(tree)

        overlap = names & forbidden

        assert_true(
            not overlap,
            "randomness dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15K-21 NO TIME DEPENDENCY
# =============================================================================

def test_no_time_dependency():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
        "time",
        "datetime",
        "date",
        "now",
        "utcnow",
        "today",
        "sleep",
        "perf_counter",
        "monotonic",
    }

    for module in modules:

        tree = source_tree(module)

        names = ast_dependency_names(tree)

        overlap = names & forbidden

        assert_true(
            not overlap,
            "time dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15K-22 NO ENVIRONMENT DEPENDENCY
# =============================================================================

def test_no_environment_dependency():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
        "os",
        "environ",
        "getenv",
        "sys",
        "argv",
        "platform",
        "machine",
        "uname",
    }

    for module in modules:

        tree = source_tree(module)

        names = ast_dependency_names(tree)

        overlap = names & forbidden

        assert_true(
            not overlap,
            "environment dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15K-23 NO DATABASE / NETWORK DEPENDENCY
# =============================================================================

def test_no_database_network_dependency():

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

        tree = source_tree(module)

        names = ast_dependency_names(tree)

        overlap = forbidden & names

        assert_true(
            not overlap,
            "database/network/write dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15K-24 NO FUTURE / DECISION / EXECUTION DEPENDENCY
# =============================================================================

def test_no_future_decision_execution_dependency():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden = {
        "prediction",
        "predict",
        "forecast",
        "future_return",
        "future_price",
        "decision",
        "decision_engine",
        "decision_contract",
        "buy",
        "sell",
        "execute",
        "order",
        "place_order",
        "score",
        "scoring",
        "calculate_score",
        "build_score",
    }

    for module in modules:

        tree = source_tree(module)

        names = ast_dependency_names(tree)

        overlap = names & forbidden

        assert_true(
            not overlap,
            "future/decision/execution dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15K-25 FINAL REPRODUCIBILITY INTEGRITY
# =============================================================================

def test_final_reproducibility_integrity():

    baseline = {}

    for asset in EXPECTED_ASSETS:

        baseline[asset] = build_signal(
            asset,
            long_structure(),
        )

    for _ in range(50):

        for asset in EXPECTED_ASSETS:

            current = build_signal(
                asset,
                long_structure(),
            )

            assert_equal(
                current,
                baseline[asset],
                "final reproducibility failure for {}".format(
                    asset
                ),
            )

            assert_true(
                signal_contract.validate_signal(current),
                "final output failed contract for {}".format(
                    asset
                ),
            )

    assert_equal(
        len(baseline),
        len(EXPECTED_ASSETS),
        "final asset count mismatch",
    )

    assert_equal(
        set(baseline.keys()),
        set(EXPECTED_ASSETS),
        "final asset set mismatch",
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print(
        "ARUNDA TRADER — STEP 15K"
    )
    print(
        "SIGNAL DETERMINISM & REPRODUCIBILITY AUDIT v0.1"
    )
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
        "Scoring     : NOT USED"
    )
    print(
        "Prediction  : NOT USED"
    )
    print(
        "Decision    : NOT USED"
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

    print("=" * 78)
    print()

    tests = [

        (
            "15K-01 Baseline LONG determinism",
            test_baseline_long_determinism,
        ),

        (
            "15K-02 Baseline SHORT determinism",
            test_baseline_short_determinism,
        ),

        (
            "15K-03 Baseline NEUTRAL determinism",
            test_baseline_neutral_determinism,
        ),

        (
            "15K-04 Repeated execution",
            test_repeated_execution,
        ),

        (
            "15K-05 Deep-copy reproducibility",
            test_deepcopy_reproducibility,
        ),

        (
            "15K-06 Regime reproducibility",
            test_regime_reproducibility,
        ),

        (
            "15K-07 Cross-asset reproducibility",
            test_cross_asset_reproducibility,
        ),

        (
            "15K-08 Asset-order reproducibility",
            test_asset_order_reproducibility,
        ),

        (
            "15K-09 Input immutability",
            test_input_immutability,
        ),

        (
            "15K-10 Output isolation",
            test_output_isolation,
        ),

        (
            "15K-11 Output contract reproducibility",
            test_output_contract_reproducibility,
        ),

        (
            "15K-12 HIGH volatility reproducibility",
            test_high_volatility_reproducibility,
        ),

        (
            "15K-13 Position-boundary reproducibility",
            test_position_boundary_reproducibility,
        ),

        (
            "15K-14 Non-READY rejection reproducibility",
            test_non_ready_rejection_reproducibility,
        ),

        (
            "15K-15 Invalid-input reproducibility",
            test_invalid_input_reproducibility,
        ),

        (
            "15K-16 State reset between executions",
            test_state_reset_between_executions,
        ),

        (
            "15K-17 Interleaved execution",
            test_interleaved_execution,
        ),

        (
            "15K-18 Randomized execution order",
            test_randomized_execution_order,
        ),

        (
            "15K-19 Signal logic pure reproducibility",
            test_signal_logic_reproducibility,
        ),

        (
            "15K-20 No randomness dependency",
            test_no_randomness_dependency,
        ),

        (
            "15K-21 No time dependency",
            test_no_time_dependency,
        ),

        (
            "15K-22 No environment dependency",
            test_no_environment_dependency,
        ),

        (
            "15K-23 No database/network dependency",
            test_no_database_network_dependency,
        ),

        (
            "15K-24 No future/decision/execution dependency",
            test_no_future_decision_execution_dependency,
        ),

        (
            "15K-25 Final reproducibility integrity",
            test_final_reproducibility_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print(
        "DETERMINISM / REPRODUCIBILITY AUDIT"
    )
    print("=" * 78)

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
    print(
        "STEP 15K SUMMARY"
    )
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
    print(
        "STEP 15K VERDICT"
    )
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL DETERMINISM & REPRODUCIBILITY AUDIT PASS"
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
            "Scoring      : NOT USED"
        )

        print(
            "Prediction   : NOT USED"
        )

        print(
            "Decision     : NOT USED"
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
        "RESULT      : SIGNAL DETERMINISM & REPRODUCIBILITY AUDIT FAIL"
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