# =============================================================================
# ARUNDA TRADER
# STEP 15F — SIGNAL FAILURE-MODE & RECOVERY AUDIT v0.1
#
# PURPOSE
# -------
# Failure-mode, rejection, recovery, state-isolation and post-failure
# integrity audit of the existing Signal Layer.
#
# AUDITED FILES
# -------------
# signal_logic.py
# signal_engine.py
# signal_contract.py
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
# DO NOT MODIFY PRODUCTION FILES
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
# 15F-01 BASELINE VALIDITY
# =============================================================================

def test_baseline_validity():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["asset"],
        "BTC",
        "baseline asset mismatch",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "baseline direction mismatch",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "baseline state mismatch",
    )


# =============================================================================
# 15F-02 INVALID ASSET FAILURE
# =============================================================================

def test_invalid_asset_failure():

    assert_raises(
        RuntimeError,
        lambda:
            signal_engine.build_signal(
                "INVALID",
                ready_regime(),
                structural_record(
                    long_structure()
                ),
            ),
        "invalid asset must be rejected",
    )


# =============================================================================
# 15F-03 NULL ASSET FAILURE
# =============================================================================

def test_null_asset_failure():

    assert_raises(
        RuntimeError,
        lambda:
            signal_engine.build_signal(
                None,
                ready_regime(),
                structural_record(
                    long_structure()
                ),
            ),
        "null asset must be rejected",
    )


# =============================================================================
# 15F-04 MALFORMED STRUCTURAL CONTAINER
# =============================================================================

def test_malformed_structural_container():

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
# 15F-05 MALFORMED REGIME
# =============================================================================

def test_malformed_regime():

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
                    value,
                    structural_record(
                        long_structure()
                    ),
                ),
            "malformed regime must be rejected",
        )


# =============================================================================
# 15F-06 NON-READY FAILURE
# =============================================================================

def test_non_ready_failure():

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
# 15F-07 MISSING STRUCTURAL FIELD FAILURE
# =============================================================================

def test_missing_structural_field_failure():

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
# 15F-08 INVALID STRUCTURAL TYPE FAILURE
# =============================================================================

def test_invalid_structural_type_failure():

    fields = [
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    ]

    invalid_values = [
        None,
        1,
        0.5,
        [],
        {},
        True,
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
# 15F-09 INVALID ENUM FAILURE
# =============================================================================

def test_invalid_enum_failure():

    fields = [
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    ]

    invalid_values = [
        "INVALID",
        "UNKNOWN",
        "",
        "HIGHER",
        "LOWER_THAN_LOW",
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
# 15F-10 HIGH VOLATILITY FAILURE MODE
# =============================================================================

def test_high_volatility_failure_mode():

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
        "HIGH volatility must block LONG",
    )

    assert_equal(
        short_result["direction"],
        "NONE",
        "HIGH volatility must block SHORT",
    )


# =============================================================================
# 15F-11 POSITION FAILURE MODE
# =============================================================================

def test_position_failure_mode():

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
# 15F-12 FAILURE DOES NOT RETURN PARTIAL SIGNAL
# =============================================================================

def test_failure_no_partial_signal():

    invalid_structure = long_structure()

    del invalid_structure["trend"]

    try:

        result = build_signal(
            "BTC",
            invalid_structure,
        )

    except RuntimeError:

        return

    raise AuditFailure(
        "invalid input returned a partial signal: {!r}".format(
            result
        )
    )


# =============================================================================
# 15F-13 FAILURE DOES NOT CORRUPT INPUT
# =============================================================================

def test_failure_input_immutability():

    structure = long_structure()

    del structure["trend"]

    regime = ready_regime()

    structure_before = copy.deepcopy(structure)
    regime_before = copy.deepcopy(regime)

    try:

        signal_engine.build_signal(
            "BTC",
            regime,
            structural_record(
                structure
            ),
        )

    except RuntimeError:

        pass

    assert_equal(
        structure,
        structure_before,
        "failed signal mutated structural input",
    )

    assert_equal(
        regime,
        regime_before,
        "failed signal mutated regime input",
    )


# =============================================================================
# 15F-14 RECOVERY AFTER FAILURE
# =============================================================================

def test_recovery_after_failure():

    invalid_structure = long_structure()

    del invalid_structure["trend"]

    try:

        build_signal(
            "BTC",
            invalid_structure,
        )

    except RuntimeError:

        pass

    valid_result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        valid_result["direction"],
        "LONG",
        "valid signal failed after previous failure",
    )

    assert_equal(
        valid_result["signal_state"],
        "ACTIVE",
        "signal state corrupted after previous failure",
    )


# =============================================================================
# 15F-15 RECOVERY AFTER NON-READY FAILURE
# =============================================================================

def test_recovery_after_non_ready_failure():

    try:

        signal_engine.build_signal(
            "BTC",
            {"status": "BLOCKED"},
            structural_record(
                long_structure()
            ),
        )

    except RuntimeError:

        pass

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["direction"],
        "LONG",
        "READY signal failed after non-ready failure",
    )


# =============================================================================
# 15F-16 RECOVERY ACROSS ASSETS
# =============================================================================

def test_recovery_across_assets():

    try:

        signal_engine.build_signal(
            "INVALID",
            ready_regime(),
            structural_record(
                long_structure()
            ),
        )

    except RuntimeError:

        pass

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity corrupted after failure",
        )

        assert_equal(
            result["direction"],
            "LONG",
            "direction corrupted after failure for {}".format(
                asset
            ),
        )


# =============================================================================
# 15F-17 REPEATED FAILURE DETERMINISM
# =============================================================================

def test_repeated_failure_determinism():

    invalid_structure = long_structure()

    del invalid_structure["trend"]

    errors = []

    for _ in range(5):

        try:

            build_signal(
                "BTC",
                copy.deepcopy(
                    invalid_structure
                ),
            )

        except Exception as error:

            errors.append(
                (
                    type(error).__name__,
                    str(error),
                )
            )

    assert_true(
        len(errors) == 5,
        "not every invalid execution failed",
    )

    assert_true(
        all(
            error == errors[0]
            for error in errors
        ),
        "failure behavior is not deterministic",
    )


# =============================================================================
# 15F-18 VALID OUTPUT AFTER REPEATED FAILURES
# =============================================================================

def test_valid_output_after_repeated_failures():

    invalid_structure = long_structure()

    del invalid_structure["momentum"]

    for _ in range(5):

        try:

            build_signal(
                "BTC",
                copy.deepcopy(
                    invalid_structure
                ),
            )

        except RuntimeError:

            pass

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["direction"],
        "LONG",
        "valid output corrupted after repeated failures",
    )


# =============================================================================
# 15F-19 NONE FAILURE RECOVERY
# =============================================================================

def test_none_signal_recovery():

    high_volatility = long_structure()
    high_volatility["volatility"] = "HIGH"

    result = build_signal(
        "BTC",
        high_volatility,
    )

    assert_equal(
        result["direction"],
        "NONE",
        "blocked signal did not produce NONE",
    )

    valid = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        valid["direction"],
        "LONG",
        "valid signal failed after NONE result",
    )


# =============================================================================
# 15F-20 CROSS-ASSET FAILURE ISOLATION
# =============================================================================

def test_cross_asset_failure_isolation():

    try:

        signal_engine.build_signal(
            "INVALID",
            ready_regime(),
            structural_record(
                long_structure()
            ),
        )

    except RuntimeError:

        pass

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            neutral_structure(),
        )

        assert_equal(
            result["asset"],
            asset,
            "cross-asset identity contaminated",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "neutral result contaminated for {}".format(
                asset
            ),
        )


# =============================================================================
# 15F-21 CONTRACT RECOVERY
# =============================================================================

def test_contract_recovery():

    valid_signal = signal_contract.build_empty_signal(
        "BTC"
    )

    assert_true(
        signal_contract.validate_signal(
            valid_signal
        ),
        "baseline contract signal invalid",
    )

    invalid_signal = copy.deepcopy(
        valid_signal
    )

    invalid_signal["direction"] = "INVALID"

    assert_true(
        not signal_contract.validate_signal(
            invalid_signal
        ),
        "invalid signal accepted by contract",
    )

    assert_true(
        signal_contract.validate_signal(
            valid_signal
        ),
        "valid contract failed after invalid validation",
    )


# =============================================================================
# 15F-22 PRODUCTION AST INTEGRITY
# =============================================================================

def test_production_ast_integrity():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    for module in modules:

        with open(
            module.__file__,
            "r",
            encoding="utf-8",
        ) as file:

            source = file.read()

        try:

            ast.parse(
                source,
                filename=module.__file__,
            )

        except SyntaxError as error:

            raise AuditFailure(
                "production AST invalid in {}: {}".format(
                    os.path.basename(
                        module.__file__
                    ),
                    error,
                )
            )


# =============================================================================
# 15F-23 DATABASE / NETWORK / WRITE ISOLATION
# =============================================================================

def test_runtime_isolation():

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

        with open(
            module.__file__,
            "r",
            encoding="utf-8",
        ) as file:

            source = file.read()

        tree = ast.parse(
            source,
            filename=module.__file__,
        )

        for node in ast.walk(tree):

            if isinstance(node, ast.Name):

                assert_true(
                    node.id not in forbidden,
                    "forbidden dependency in {}: {}".format(
                        os.path.basename(
                            module.__file__
                        ),
                        node.id,
                    ),
                )

            elif isinstance(node, ast.Attribute):

                assert_true(
                    node.attr not in forbidden,
                    "forbidden dependency in {}: {}".format(
                        os.path.basename(
                            module.__file__
                        ),
                        node.attr,
                    ),
                )


# =============================================================================
# 15F-24 FUTURE / DECISION / EXECUTION ISOLATION
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
        "order",
        "place_order",
        "execute",
    }

    for module in modules:

        with open(
            module.__file__,
            "r",
            encoding="utf-8",
        ) as file:

            source = file.read()

        tree = ast.parse(
            source,
            filename=module.__file__,
        )

        for node in ast.walk(tree):

            if isinstance(node, ast.Name):

                assert_true(
                    node.id not in forbidden,
                    "forbidden future/decision dependency in {}: {}".format(
                        os.path.basename(
                            module.__file__
                        ),
                        node.id,
                    ),
                )

            elif isinstance(node, ast.Attribute):

                assert_true(
                    node.attr not in forbidden,
                    "forbidden future/decision dependency in {}: {}".format(
                        os.path.basename(
                            module.__file__
                        ),
                        node.attr,
                    ),
                )


# =============================================================================
# 15F-25 FINAL FAILURE-RECOVERY INTEGRITY
# =============================================================================

def test_final_failure_recovery_integrity():

    failure_cases = [
        (
            lambda:
                signal_engine.build_signal(
                    "INVALID",
                    ready_regime(),
                    structural_record(
                        long_structure()
                    ),
                )
        ),
        (
            lambda:
                signal_engine.build_signal(
                    "BTC",
                    {"status": "BLOCKED"},
                    structural_record(
                        long_structure()
                    ),
                )
        ),
        (
            lambda:
                signal_engine.build_signal(
                    "BTC",
                    ready_regime(),
                    None,
                )
        ),
    ]

    for failure in failure_cases:

        try:

            failure()

        except RuntimeError:

            pass

    final_result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        final_result["asset"],
        "BTC",
        "final recovery asset mismatch",
    )

    assert_equal(
        final_result["direction"],
        "LONG",
        "final recovery direction mismatch",
    )

    assert_equal(
        final_result["signal_state"],
        "ACTIVE",
        "final recovery state mismatch",
    )

    assert_equal(
        final_result["confidence"],
        None,
        "confidence changed after failure recovery",
    )

    assert_equal(
        final_result["timestamp"],
        None,
        "timestamp changed after failure recovery",
    )

    assert_equal(
        final_result["reason"],
        "STRUCTURAL_DIRECTION",
        "reason changed after failure recovery",
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print(
        "ARUNDA TRADER — STEP 15F"
    )
    print(
        "SIGNAL FAILURE-MODE & RECOVERY AUDIT v0.1"
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
            "15F-01 Baseline validity",
            test_baseline_validity,
        ),

        (
            "15F-02 Invalid asset failure",
            test_invalid_asset_failure,
        ),

        (
            "15F-03 Null asset failure",
            test_null_asset_failure,
        ),

        (
            "15F-04 Malformed structural container",
            test_malformed_structural_container,
        ),

        (
            "15F-05 Malformed regime",
            test_malformed_regime,
        ),

        (
            "15F-06 Non-READY failure",
            test_non_ready_failure,
        ),

        (
            "15F-07 Missing structural field failure",
            test_missing_structural_field_failure,
        ),

        (
            "15F-08 Invalid structural type failure",
            test_invalid_structural_type_failure,
        ),

        (
            "15F-09 Invalid enum failure",
            test_invalid_enum_failure,
        ),

        (
            "15F-10 HIGH volatility failure mode",
            test_high_volatility_failure_mode,
        ),

        (
            "15F-11 Position failure mode",
            test_position_failure_mode,
        ),

        (
            "15F-12 Failure no partial signal",
            test_failure_no_partial_signal,
        ),

        (
            "15F-13 Failure input immutability",
            test_failure_input_immutability,
        ),

        (
            "15F-14 Recovery after failure",
            test_recovery_after_failure,
        ),

        (
            "15F-15 Recovery after non-ready failure",
            test_recovery_after_non_ready_failure,
        ),

        (
            "15F-16 Recovery across assets",
            test_recovery_across_assets,
        ),

        (
            "15F-17 Repeated failure determinism",
            test_repeated_failure_determinism,
        ),

        (
            "15F-18 Valid output after repeated failures",
            test_valid_output_after_repeated_failures,
        ),

        (
            "15F-19 NONE failure recovery",
            test_none_signal_recovery,
        ),

        (
            "15F-20 Cross-asset failure isolation",
            test_cross_asset_failure_isolation,
        ),

        (
            "15F-21 Contract recovery",
            test_contract_recovery,
        ),

        (
            "15F-22 Production AST integrity",
            test_production_ast_integrity,
        ),

        (
            "15F-23 Database / network / write isolation",
            test_runtime_isolation,
        ),

        (
            "15F-24 Future / decision / execution isolation",
            test_future_decision_execution_isolation,
        ),

        (
            "15F-25 Final failure-recovery integrity",
            test_final_failure_recovery_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print(
        "FAILURE-MODE / RECOVERY AUDIT"
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
        "STEP 15F SUMMARY"
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
        "STEP 15F VERDICT"
    )
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL FAILURE-MODE & RECOVERY AUDIT PASS"
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
        "RESULT      : SIGNAL FAILURE-MODE & RECOVERY AUDIT FAIL"
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


if __name__ == "__main__":

    raise SystemExit(
        main()
    )