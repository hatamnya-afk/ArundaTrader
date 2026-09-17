# =============================================================================
# ARUNDA TRADER
# STEP 15M — SIGNAL CONTRACT / ENGINE STRESS & RESILIENCE AUDIT v0.1
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
# SCORING / PREDICTION / DECISION / EXECUTION
# --------------------------------------------
# NOT USED
#
# PURPOSE
# -------
# Stress and resilience verification of the Signal Contract and Signal Engine.
#
# PRODUCTION FILES
# ----------------
# signal_logic.py
# signal_engine.py
# signal_contract.py
#
# PRINCIPLE
# ---------
# DO NOT MODIFY PRODUCTION FILES
# DO NOT USE DATABASE
# DO NOT WRITE
# DO NOT ADD SCORING
# DO NOT ADD PREDICTION
# DO NOT ADD DECISION
# DO NOT ADD EXECUTION
# DO NOT INTRODUCE LOOK-AHEAD
# =============================================================================

import ast
import copy
import os

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
# 15M-01 BASELINE LONG RESILIENCE
# =============================================================================

def test_baseline_long_resilience():

    for _ in range(20):

        result = build_signal(
            "BTC",
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "baseline LONG failed contract",
        )

        assert_equal(
            result["direction"],
            "LONG",
            "baseline LONG direction mismatch",
        )

        assert_equal(
            result["signal_state"],
            "ACTIVE",
            "baseline LONG state mismatch",
        )


# =============================================================================
# 15M-02 BASELINE SHORT RESILIENCE
# =============================================================================

def test_baseline_short_resilience():

    for _ in range(20):

        result = build_signal(
            "ETH",
            short_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "baseline SHORT failed contract",
        )

        assert_equal(
            result["direction"],
            "SHORT",
            "baseline SHORT direction mismatch",
        )

        assert_equal(
            result["signal_state"],
            "ACTIVE",
            "baseline SHORT state mismatch",
        )


# =============================================================================
# 15M-03 BASELINE NEUTRAL RESILIENCE
# =============================================================================

def test_baseline_neutral_resilience():

    for _ in range(20):

        result = build_signal(
            "SOL",
            neutral_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "baseline NEUTRAL failed contract",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "baseline NEUTRAL direction mismatch",
        )

        assert_equal(
            result["signal_state"],
            "NEUTRAL",
            "baseline NEUTRAL state mismatch",
        )


# =============================================================================
# 15M-04 ALL ASSET STRESS
# =============================================================================

def test_all_asset_stress():

    for asset in EXPECTED_ASSETS:

        for structure in [
            long_structure(),
            short_structure(),
            neutral_structure(),
        ]:

            result = build_signal(
                asset,
                structure,
            )

            assert_true(
                signal_contract.validate_signal(result),
                "invalid output for {}".format(asset),
            )

            assert_equal(
                result["asset"],
                asset,
                "asset identity mismatch",
            )


# =============================================================================
# 15M-05 REPEATED CONTRACT BUILD
# =============================================================================

def test_repeated_contract_build():

    first = signal_contract.load_signal_contract()

    for _ in range(25):

        current = signal_contract.load_signal_contract()

        assert_equal(
            current,
            first,
            "repeated contract build changed output",
        )


# =============================================================================
# 15M-06 CONTRACT INSTANCE ISOLATION
# =============================================================================

def test_contract_instance_isolation():

    first = signal_contract.load_signal_contract()
    second = signal_contract.load_signal_contract()

    assert_true(
        first is not second,
        "contract instances are aliased",
    )

    first["BTC"]["direction"] = "LONG"

    assert_equal(
        second["BTC"]["direction"],
        "NONE",
        "contract instances share mutable state",
    )


# =============================================================================
# 15M-07 EMPTY SIGNAL STRESS
# =============================================================================

def test_empty_signal_stress():

    for asset in EXPECTED_ASSETS:

        for _ in range(20):

            signal = signal_contract.build_empty_signal(
                asset
            )

            assert_true(
                signal_contract.validate_signal(signal),
                "empty signal invalid for {}".format(asset),
            )

            assert_equal(
                signal["asset"],
                asset,
                "empty signal asset mismatch",
            )

            assert_equal(
                signal["signal_state"],
                "NEUTRAL",
                "empty signal state mismatch",
            )

            assert_equal(
                signal["direction"],
                "NONE",
                "empty signal direction mismatch",
            )


# =============================================================================
# 15M-08 INPUT IMMUTABILITY STRESS
# =============================================================================

def test_input_immutability_stress():

    for asset in EXPECTED_ASSETS:

        regime = ready_regime()

        structure = structural_record(
            long_structure()
        )

        regime_before = copy.deepcopy(regime)
        structure_before = copy.deepcopy(structure)

        for _ in range(10):

            signal_engine.build_signal(
                asset,
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
# 15M-09 OUTPUT INDEPENDENCE
# =============================================================================

def test_output_independence():

    first = build_signal(
        "BTC",
        long_structure(),
    )

    second = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        first is not second,
        "outputs are aliased",
    )

    first["direction"] = "SHORT"

    assert_equal(
        second["direction"],
        "LONG",
        "mutating one output affected another",
    )


# =============================================================================
# 15M-10 CROSS-ASSET OUTPUT INDEPENDENCE
# =============================================================================

def test_cross_asset_output_independence():

    outputs = {}

    for asset in EXPECTED_ASSETS:

        outputs[asset] = build_signal(
            asset,
            long_structure(),
        )

    outputs["BTC"]["direction"] = "SHORT"

    for asset in EXPECTED_ASSETS:

        if asset == "BTC":
            continue

        assert_equal(
            outputs[asset]["direction"],
            "LONG",
            "cross-asset output contamination",
        )


# =============================================================================
# 15M-11 LONG / SHORT INTERLEAVING
# =============================================================================

def test_long_short_interleaving():

    for _ in range(25):

        long_result = build_signal(
            "BTC",
            long_structure(),
        )

        short_result = build_signal(
            "ETH",
            short_structure(),
        )

        assert_equal(
            long_result["direction"],
            "LONG",
            "LONG corrupted by interleaving",
        )

        assert_equal(
            short_result["direction"],
            "SHORT",
            "SHORT corrupted by interleaving",
        )


# =============================================================================
# 15M-12 NEUTRAL INTERLEAVING
# =============================================================================

def test_neutral_interleaving():

    for _ in range(25):

        long_result = build_signal(
            "BTC",
            long_structure(),
        )

        neutral_result = build_signal(
            "SOL",
            neutral_structure(),
        )

        short_result = build_signal(
            "ETH",
            short_structure(),
        )

        assert_equal(
            long_result["direction"],
            "LONG",
            "LONG corrupted by neutral interleaving",
        )

        assert_equal(
            neutral_result["direction"],
            "NONE",
            "NEUTRAL corrupted by interleaving",
        )

        assert_equal(
            short_result["direction"],
            "SHORT",
            "SHORT corrupted by interleaving",
        )


# =============================================================================
# 15M-13 HIGH VOLATILITY STRESS
# =============================================================================

def test_high_volatility_stress():

    cases = [
        long_structure(),
        short_structure(),
    ]

    for structure in cases:

        structure["volatility"] = "HIGH"

        for _ in range(20):

            result = build_signal(
                "BTC",
                structure,
            )

            assert_equal(
                result["signal_state"],
                "NEUTRAL",
                "HIGH volatility did not block signal",
            )

            assert_equal(
                result["direction"],
                "NONE",
                "HIGH volatility produced direction",
            )

            assert_equal(
                result["reason"],
                None,
                "HIGH volatility produced reason",
            )


# =============================================================================
# 15M-14 POSITION BOUNDARY STRESS
# =============================================================================

def test_position_boundary_stress():

    cases = [
        ("LOWER", long_structure()),
        ("UPPER", short_structure()),
    ]

    for position, structure in cases:

        structure["position"] = position

        for _ in range(20):

            result = build_signal(
                "BTC",
                structure,
            )

            assert_equal(
                result["direction"],
                "NONE",
                "position boundary failed to block",
            )

            assert_equal(
                result["signal_state"],
                "NEUTRAL",
                "position boundary state mismatch",
            )


# =============================================================================
# 15M-15 INVALID INPUT STRESS
# =============================================================================

def test_invalid_input_stress():

    invalid_structures = [
        None,
        [],
        {},
        "INVALID",
        1,
        0.5,
        True,
    ]

    for invalid in invalid_structures:

        assert_raises(
            RuntimeError,
            lambda invalid=invalid:
                signal_engine.build_signal(
                    "BTC",
                    ready_regime(),
                    structural_record(invalid),
                ),
            "invalid structural input was accepted",
        )


# =============================================================================
# 15M-16 INVALID ENUM STRESS
# =============================================================================

def test_invalid_enum_stress():

    fields = [
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    ]

    values = [
        "INVALID",
        "UNKNOWN",
        "",
        "HIGHER",
        "LOWER_THAN_LOW",
    ]

    for field in fields:

        for value in values:

            structure = long_structure()
            structure[field] = value

            assert_raises(
                RuntimeError,
                lambda structure=structure:
                    build_signal(
                        "BTC",
                        structure,
                    ),
                "invalid enum accepted: {}".format(field),
            )


# =============================================================================
# 15M-17 NON-READY REGIME STRESS
# =============================================================================

def test_non_ready_regime_stress():

    regimes = [
        {"status": "BLOCKED"},
        {"status": "ERROR"},
        {"status": "UNAVAILABLE"},
        {"status": "NOT_READY"},
        {},
        None,
        [],
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
            "non-READY regime was accepted",
        )


# =============================================================================
# 15M-18 UNKNOWN ASSET STRESS
# =============================================================================

def test_unknown_asset_stress():

    invalid_assets = [
        "UNKNOWN",
        "",
        "BTC_USDT",
        "btc",
        None,
        1,
        [],
        {},
    ]

    for asset in invalid_assets:

        assert_raises(
            RuntimeError,
            lambda asset=asset:
                signal_engine.build_signal(
                    asset,
                    ready_regime(),
                    structural_record(
                        long_structure()
                    ),
                ),
            "unknown asset was accepted",
        )


# =============================================================================
# 15M-19 CONTRACT TAMPERING STRESS
# =============================================================================

def test_contract_tampering_stress():

    valid = build_signal(
        "BTC",
        long_structure(),
    )

    invalid_directions = [
        "INVALID",
        "UNKNOWN",
        "",
        None,
        1,
        True,
        [],
        {},
    ]

    for direction in invalid_directions:

        tampered = copy.deepcopy(valid)
        tampered["direction"] = direction

        assert_true(
            not signal_contract.validate_signal(
                tampered
            ),
            "contract accepted tampered direction: {!r}".format(
                direction
            ),
        )

    # Semantically invalid but enum-valid mutation.
    tampered = copy.deepcopy(valid)
    tampered["direction"] = "NONE"

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted semantically invalid direction",
    )

    tampered = copy.deepcopy(valid)
    tampered["signal_state"] = "NEUTRAL"

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted ACTIVE/NEUTRAL semantic mismatch",
    )

    tampered = copy.deepcopy(valid)
    tampered["reason"] = None

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted invalid ACTIVE reason",
    )


# =============================================================================
# 15M-20 SCHEMA HARDENING STRESS
# =============================================================================

def test_schema_hardening_stress():

    valid = build_signal(
        "BTC",
        long_structure(),
    )

    missing_fields = [
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    ]

    for field in missing_fields:

        tampered = copy.deepcopy(valid)
        del tampered[field]

        assert_true(
            not signal_contract.validate_signal(
                tampered
            ),
            "missing field was accepted: {}".format(field),
        )

    tampered = copy.deepcopy(valid)
    tampered["unexpected"] = "X"

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "unexpected field was accepted",
    )


# =============================================================================
# 15M-21 DETERMINISM STRESS
# =============================================================================

def test_determinism_stress():

    structure = long_structure()

    baseline = build_signal(
        "BTC",
        structure,
    )

    for _ in range(100):

        current = build_signal(
            "BTC",
            copy.deepcopy(structure),
        )

        assert_equal(
            current,
            baseline,
            "signal output is not deterministic",
        )


# =============================================================================
# 15M-22 ORDER INDEPENDENCE STRESS
# =============================================================================

def test_order_independence_stress():

    forward = {}

    for asset in EXPECTED_ASSETS:

        forward[asset] = build_signal(
            asset,
            long_structure(),
        )

    reverse = {}

    for asset in reversed(EXPECTED_ASSETS):

        reverse[asset] = build_signal(
            asset,
            long_structure(),
        )

    assert_equal(
        forward,
        reverse,
        "asset processing order changed outputs",
    )


# =============================================================================
# 15M-23 DATABASE / NETWORK / WRITE ISOLATION
# =============================================================================

def test_database_network_write_isolation():

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
            "forbidden dependency detected in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15M-24 FUTURE / DECISION / EXECUTION ISOLATION
# =============================================================================

def test_future_decision_execution_isolation():

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
# 15M-25 FINAL RESILIENCE INTEGRITY
# =============================================================================

def test_final_resilience_integrity():

    contract = signal_contract.load_signal_contract()

    assert_true(
        signal_contract.validate_signal_contract(contract),
        "final contract invalid",
    )

    results = {}

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "final signal invalid for {}".format(asset),
        )

        assert_equal(
            result["asset"],
            asset,
            "final asset identity mismatch",
        )

        assert_equal(
            result["signal_state"],
            "ACTIVE",
            "final signal state mismatch",
        )

        assert_equal(
            result["direction"],
            "LONG",
            "final direction mismatch",
        )

        assert_equal(
            result["confidence"],
            None,
            "confidence must remain isolated",
        )

        assert_equal(
            result["timestamp"],
            None,
            "timestamp must remain isolated",
        )

        assert_equal(
            result["reason"],
            "STRUCTURAL_DIRECTION",
            "final reason mismatch",
        )

        results[asset] = result

    assert_equal(
        len(results),
        len(EXPECTED_ASSETS),
        "final asset count mismatch",
    )

    assert_equal(
        set(results.keys()),
        set(EXPECTED_ASSETS),
        "final asset set mismatch",
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

        elif isinstance(node, ast.alias):

            names.add(node.name)

    return names


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15M")
    print("SIGNAL CONTRACT / ENGINE STRESS & RESILIENCE AUDIT v0.1")
    print("=" * 78)

    print("Mode        : READ ONLY / AUDIT ONLY")
    print("Database    : NOT USED")
    print("Writes      : NONE")
    print("Scoring     : NOT USED")
    print("Prediction  : NOT USED")
    print("Decision    : NOT USED")
    print("Execution   : NOT USED")
    print()

    print("Production files:")
    print("  - signal_logic.py")
    print("  - signal_engine.py")
    print("  - signal_contract.py")

    print("=" * 78)
    print()

    tests = [

        (
            "15M-01 Baseline LONG resilience",
            test_baseline_long_resilience,
        ),

        (
            "15M-02 Baseline SHORT resilience",
            test_baseline_short_resilience,
        ),

        (
            "15M-03 Baseline NEUTRAL resilience",
            test_baseline_neutral_resilience,
        ),

        (
            "15M-04 All asset stress",
            test_all_asset_stress,
        ),

        (
            "15M-05 Repeated contract build",
            test_repeated_contract_build,
        ),

        (
            "15M-06 Contract instance isolation",
            test_contract_instance_isolation,
        ),

        (
            "15M-07 Empty signal stress",
            test_empty_signal_stress,
        ),

        (
            "15M-08 Input immutability stress",
            test_input_immutability_stress,
        ),

        (
            "15M-09 Output independence",
            test_output_independence,
        ),

        (
            "15M-10 Cross-asset output independence",
            test_cross_asset_output_independence,
        ),

        (
            "15M-11 LONG / SHORT interleaving",
            test_long_short_interleaving,
        ),

        (
            "15M-12 NEUTRAL interleaving",
            test_neutral_interleaving,
        ),

        (
            "15M-13 HIGH volatility stress",
            test_high_volatility_stress,
        ),

        (
            "15M-14 Position boundary stress",
            test_position_boundary_stress,
        ),

        (
            "15M-15 Invalid input stress",
            test_invalid_input_stress,
        ),

        (
            "15M-16 Invalid enum stress",
            test_invalid_enum_stress,
        ),

        (
            "15M-17 Non-READY regime stress",
            test_non_ready_regime_stress,
        ),

        (
            "15M-18 Unknown asset stress",
            test_unknown_asset_stress,
        ),

        (
            "15M-19 Contract tampering stress",
            test_contract_tampering_stress,
        ),

        (
            "15M-20 Schema hardening stress",
            test_schema_hardening_stress,
        ),

        (
            "15M-21 Determinism stress",
            test_determinism_stress,
        ),

        (
            "15M-22 Order independence stress",
            test_order_independence_stress,
        ),

        (
            "15M-23 Database / network / write isolation",
            test_database_network_write_isolation,
        ),

        (
            "15M-24 Future / decision / execution isolation",
            test_future_decision_execution_isolation,
        ),

        (
            "15M-25 Final resilience integrity",
            test_final_resilience_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("SIGNAL CONTRACT / ENGINE STRESS & RESILIENCE AUDIT")
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
    print("STEP 15M SUMMARY")
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
    print("STEP 15M VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL CONTRACT / ENGINE STRESS & RESILIENCE AUDIT PASS"
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
        "RESULT      : SIGNAL CONTRACT / ENGINE STRESS & RESILIENCE AUDIT FAIL"
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