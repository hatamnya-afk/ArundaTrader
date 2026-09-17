# =============================================================================
# ARUNDA TRADER
# STEP 15H — SIGNAL END-TO-END BEHAVIORAL AUDIT v0.1
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
# End-to-end behavioral verification of the Signal Layer.
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
# 15H-01 BASELINE END-TO-END LONG
# =============================================================================

def test_baseline_long():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "baseline LONG output failed contract validation",
    )

    assert_equal(
        result["asset"],
        "BTC",
        "LONG asset mismatch",
    )

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


# =============================================================================
# 15H-02 BASELINE END-TO-END SHORT
# =============================================================================

def test_baseline_short():

    result = build_signal(
        "ETH",
        short_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "baseline SHORT output failed contract validation",
    )

    assert_equal(
        result["asset"],
        "ETH",
        "SHORT asset mismatch",
    )

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

    assert_equal(
        result["reason"],
        "STRUCTURAL_DIRECTION",
        "SHORT reason mismatch",
    )


# =============================================================================
# 15H-03 BASELINE END-TO-END NEUTRAL
# =============================================================================

def test_baseline_neutral():

    result = build_signal(
        "SOL",
        neutral_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "baseline NEUTRAL output failed contract validation",
    )

    assert_equal(
        result["asset"],
        "SOL",
        "NEUTRAL asset mismatch",
    )

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
        "NEUTRAL reason must be None",
    )


# =============================================================================
# 15H-04 ALL EXPECTED ASSETS
# =============================================================================

def test_all_assets_end_to_end():

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "invalid signal for {}".format(asset),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity mismatch for {}".format(asset),
        )

        assert_equal(
            result["direction"],
            "LONG",
            "direction mismatch for {}".format(asset),
        )


# =============================================================================
# 15H-05 OUTPUT SCHEMA
# =============================================================================

def test_output_schema():

    expected = {
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    }

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
            set(result.keys()),
            expected,
            "unexpected signal field set",
        )


# =============================================================================
# 15H-06 CONTRACT COMPATIBILITY
# =============================================================================

def test_contract_compatibility():

    structures = [
        long_structure(),
        short_structure(),
        neutral_structure(),
    ]

    for structure in structures:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_true(
            signal_contract.validate_signal(result),
            "engine output incompatible with signal contract",
        )


# =============================================================================
# 15H-07 HIGH VOLATILITY END-TO-END
# =============================================================================

def test_high_volatility_end_to_end():

    long_case = long_structure()
    long_case["volatility"] = "HIGH"

    short_case = short_structure()
    short_case["volatility"] = "HIGH"

    for structure in [
        long_case,
        short_case,
    ]:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_true(
            signal_contract.validate_signal(result),
            "HIGH volatility output failed contract",
        )

        assert_equal(
            result["signal_state"],
            "NEUTRAL",
            "HIGH volatility must produce NEUTRAL",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "HIGH volatility must produce NONE",
        )

        assert_equal(
            result["reason"],
            None,
            "HIGH volatility must not produce directional reason",
        )


# =============================================================================
# 15H-08 POSITION BOUNDARY END-TO-END
# =============================================================================

def test_position_boundary_end_to_end():

    long_case = long_structure()
    long_case["position"] = "LOWER"

    short_case = short_structure()
    short_case["position"] = "UPPER"

    for structure in [
        long_case,
        short_case,
    ]:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_true(
            signal_contract.validate_signal(result),
            "position boundary output failed contract",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "position boundary must block directional signal",
        )


# =============================================================================
# 15H-09 NON-READY REGIME
# =============================================================================

def test_non_ready_regime():

    regimes = [
        {"status": "BLOCKED"},
        {"status": "ERROR"},
        {"status": "UNAVAILABLE"},
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
            "non-ready regime must reject signal",
        )


# =============================================================================
# 15H-10 MISSING STRUCTURAL FIELD
# =============================================================================

def test_missing_structural_field():

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
            "missing structural field must reject signal",
        )


# =============================================================================
# 15H-11 INVALID STRUCTURAL TYPE
# =============================================================================

def test_invalid_structural_type():

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
                "invalid structural type must reject signal: {}".format(
                    field
                ),
            )


# =============================================================================
# 15H-12 INVALID STRUCTURAL ENUM
# =============================================================================

def test_invalid_structural_enum():

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
                "invalid structural enum must reject signal: {}".format(
                    field
                ),
            )


# =============================================================================
# 15H-13 INPUT IMMUTABILITY
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
        "regime was mutated",
    )

    assert_equal(
        structure,
        structure_before,
        "structural input was mutated",
    )


# =============================================================================
# 15H-14 DETERMINISM
# =============================================================================

def test_determinism():

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
            "repeated signal generation is not deterministic",
        )


# =============================================================================
# 15H-15 ORDER INDEPENDENCE
# =============================================================================

def test_order_independence():

    first = []

    for asset in EXPECTED_ASSETS:

        first.append(
            build_signal(
                asset,
                long_structure(),
            )
        )

    second = []

    for asset in reversed(EXPECTED_ASSETS):

        second.append(
            build_signal(
                asset,
                long_structure(),
            )
        )

    first_map = {
        item["asset"]: item
        for item in first
    }

    second_map = {
        item["asset"]: item
        for item in second
    }

    assert_equal(
        first_map,
        second_map,
        "asset processing order changed outputs",
    )


# =============================================================================
# 15H-16 CROSS-ASSET ISOLATION
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
            "asset identity contamination detected",
        )

        assert_equal(
            results[asset]["direction"],
            "LONG",
            "cross-asset direction contamination detected",
        )


# =============================================================================
# 15H-17 OUTPUT TAMPERING
#
# IMPORTANT
# ---------
# LONG -> SHORT is NOT structurally invalid.
#
# Both are valid directions for ACTIVE signals:
#
# ACTIVE + LONG
# ACTIVE + SHORT
#
# Therefore this audit must tamper the direction into a
# semantically impossible state:
#
# ACTIVE + NONE
#
# That combination MUST be rejected by the contract.
# =============================================================================

def test_output_tampering():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "baseline tampering fixture must be ACTIVE",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "baseline tampering fixture must be LONG",
    )

    tampered = copy.deepcopy(result)

    # Deliberately create a semantically invalid combination.
    tampered["direction"] = "NONE"

    assert_true(
        not signal_contract.validate_signal(tampered),
        "semantically invalid ACTIVE + NONE direction was accepted",
    )


# =============================================================================
# 15H-18 STATE TAMPERING
# =============================================================================

def test_state_tampering():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(result)

    tampered["signal_state"] = "NEUTRAL"

    assert_true(
        not signal_contract.validate_signal(tampered),
        "tampered signal state was accepted",
    )


# =============================================================================
# 15H-19 REASON TAMPERING
# =============================================================================

def test_reason_tampering():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(result)

    tampered["reason"] = None

    assert_true(
        not signal_contract.validate_signal(tampered),
        "tampered reason was accepted",
    )


# =============================================================================
# 15H-20 ASSET SWAP TAMPERING
#
# A single signal remains schema-valid after changing its asset identity.
# Cross-asset contract validation is responsible for detecting mismatches
# between container key and signal asset.
# =============================================================================

def test_asset_swap_tampering():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(result)

    tampered["asset"] = "ETH"

    assert_true(
        signal_contract.validate_signal(tampered),
        "single signal schema should remain structurally valid",
    )

    assert_equal(
        tampered["asset"],
        "ETH",
        "asset swap was not applied",
    )

    contract = signal_contract.build_signal_contract()

    contract["BTC"] = tampered

    assert_true(
        not signal_contract.validate_signal_contract(contract),
        "cross-asset contract accepted swapped asset identity",
    )


# =============================================================================
# 15H-21 CONFIDENCE ISOLATION
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
# 15H-22 TIMESTAMP ISOLATION
# =============================================================================

def test_timestamp_isolation():

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
            result["timestamp"],
            None,
            "timestamp must remain uncomputed",
        )


# =============================================================================
# 15H-23 DATABASE / NETWORK / WRITE ISOLATION
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
# 15H-24 FUTURE / DECISION / EXECUTION ISOLATION
# =============================================================================

def test_future_decision_execution_isolation():

    tree = source_tree(signal_engine)

    names = ast_dependency_names(tree)

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

    overlap = names & forbidden

    assert_true(
        not overlap,
        "future/decision/execution dependency detected: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15H-25 FINAL END-TO-END INTEGRITY
# =============================================================================

def test_final_end_to_end_integrity():

    results = {}

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "final signal failed contract: {}".format(asset),
        )

        results[asset] = result

    assert_equal(
        len(results),
        len(EXPECTED_ASSETS),
        "final aggregate asset count mismatch",
    )

    assert_equal(
        set(results.keys()),
        set(EXPECTED_ASSETS),
        "final aggregate asset set mismatch",
    )

    for asset, result in results.items():

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
            "final confidence isolation failure",
        )

        assert_equal(
            result["timestamp"],
            None,
            "final timestamp isolation failure",
        )

        assert_equal(
            result["reason"],
            "STRUCTURAL_DIRECTION",
            "final reason mismatch",
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
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15H")
    print("SIGNAL END-TO-END BEHAVIORAL AUDIT v0.1")
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
            "15H-01 Baseline end-to-end LONG",
            test_baseline_long,
        ),

        (
            "15H-02 Baseline end-to-end SHORT",
            test_baseline_short,
        ),

        (
            "15H-03 Baseline end-to-end NEUTRAL",
            test_baseline_neutral,
        ),

        (
            "15H-04 All expected assets",
            test_all_assets_end_to_end,
        ),

        (
            "15H-05 Output schema",
            test_output_schema,
        ),

        (
            "15H-06 Contract compatibility",
            test_contract_compatibility,
        ),

        (
            "15H-07 HIGH volatility end-to-end",
            test_high_volatility_end_to_end,
        ),

        (
            "15H-08 Position boundary end-to-end",
            test_position_boundary_end_to_end,
        ),

        (
            "15H-09 Non-READY regime",
            test_non_ready_regime,
        ),

        (
            "15H-10 Missing structural field",
            test_missing_structural_field,
        ),

        (
            "15H-11 Invalid structural type",
            test_invalid_structural_type,
        ),

        (
            "15H-12 Invalid structural enum",
            test_invalid_structural_enum,
        ),

        (
            "15H-13 Input immutability",
            test_input_immutability,
        ),

        (
            "15H-14 Determinism",
            test_determinism,
        ),

        (
            "15H-15 Order independence",
            test_order_independence,
        ),

        (
            "15H-16 Cross-asset isolation",
            test_cross_asset_isolation,
        ),

        (
            "15H-17 Output tampering",
            test_output_tampering,
        ),

        (
            "15H-18 State tampering",
            test_state_tampering,
        ),

        (
            "15H-19 Reason tampering",
            test_reason_tampering,
        ),

        (
            "15H-20 Asset swap tampering",
            test_asset_swap_tampering,
        ),

        (
            "15H-21 Confidence isolation",
            test_confidence_isolation,
        ),

        (
            "15H-22 Timestamp isolation",
            test_timestamp_isolation,
        ),

        (
            "15H-23 Database / network / write isolation",
            test_database_network_write_isolation,
        ),

        (
            "15H-24 Future / decision / execution isolation",
            test_future_decision_execution_isolation,
        ),

        (
            "15H-25 Final end-to-end integrity",
            test_final_end_to_end_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("END-TO-END BEHAVIORAL AUDIT")
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
    print("STEP 15H SUMMARY")
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
    print("STEP 15H VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL END-TO-END BEHAVIORAL AUDIT PASS"
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
        "RESULT      : SIGNAL END-TO-END BEHAVIORAL AUDIT FAIL"
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