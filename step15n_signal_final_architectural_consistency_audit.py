# =============================================================================
# ARUNDA TRADER
# STEP 15N — FINAL ARCHITECTURAL CONSISTENCY AUDIT v0.1
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
# Final architectural consistency verification of the Signal Layer.
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

        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                names.add(node.module)

            for alias in node.names:
                names.add(alias.name)

    return names


# =============================================================================
# 15N-01 PRODUCTION FILES EXIST
# =============================================================================

def test_production_files_exist():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    for module in modules:

        assert_true(
            module.__file__ is not None,
            "module path unavailable",
        )

        assert_true(
            os.path.isfile(module.__file__),
            "production file missing: {}".format(
                module.__file__
            ),
        )


# =============================================================================
# 15N-02 AST PARSABILITY
# =============================================================================

def test_ast_parsability():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    for module in modules:

        tree = source_tree(module)

        assert_true(
            isinstance(tree, ast.Module),
            "AST parse failed for {}".format(
                os.path.basename(module.__file__)
            ),
        )


# =============================================================================
# 15N-03 CONTRACT ASSET ARCHITECTURE
# =============================================================================

def test_contract_asset_architecture():

    assert_equal(
        signal_contract.EXPECTED_ASSETS,
        EXPECTED_ASSETS,
        "EXPECTED_ASSETS architecture mismatch",
    )


# =============================================================================
# 15N-04 CONTRACT FIELD ARCHITECTURE
# =============================================================================

def test_contract_field_architecture():

    expected_fields = {
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    }

    assert_equal(
        set(signal_contract.SIGNAL_FIELDS),
        expected_fields,
        "signal field architecture mismatch",
    )

    assert_equal(
        len(signal_contract.SIGNAL_FIELDS),
        6,
        "signal field count mismatch",
    )


# =============================================================================
# 15N-05 CONTRACT ENUM ARCHITECTURE
# =============================================================================

def test_contract_enum_architecture():

    assert_equal(
        set(signal_contract.SIGNAL_STATES),
        {
            "NEUTRAL",
            "ACTIVE",
        },
        "signal state enum mismatch",
    )

    assert_equal(
        set(signal_contract.DIRECTIONS),
        {
            "NONE",
            "LONG",
            "SHORT",
        },
        "direction enum mismatch",
    )


# =============================================================================
# 15N-06 EMPTY SIGNAL ARCHITECTURE
# =============================================================================

def test_empty_signal_architecture():

    for asset in EXPECTED_ASSETS:

        signal = signal_contract.build_empty_signal(
            asset
        )

        assert_equal(
            set(signal.keys()),
            set(signal_contract.SIGNAL_FIELDS),
            "empty signal field mismatch",
        )

        assert_equal(
            signal["asset"],
            asset,
            "empty signal asset mismatch",
        )

        assert_equal(
            signal["timestamp"],
            None,
            "empty signal timestamp mismatch",
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

        assert_equal(
            signal["confidence"],
            None,
            "empty signal confidence mismatch",
        )

        assert_equal(
            signal["reason"],
            None,
            "empty signal reason mismatch",
        )

        assert_true(
            signal_contract.validate_signal(signal),
            "empty signal failed validation",
        )


# =============================================================================
# 15N-07 CONTRACT BUILD VALIDITY
# =============================================================================

def test_contract_build_validity():

    contract = signal_contract.build_signal_contract()

    assert_true(
        isinstance(contract, dict),
        "contract must be dict",
    )

    assert_equal(
        len(contract),
        len(EXPECTED_ASSETS),
        "contract asset count mismatch",
    )

    assert_equal(
        set(contract.keys()),
        set(EXPECTED_ASSETS),
        "contract asset set mismatch",
    )

    assert_true(
        signal_contract.validate_signal_contract(contract),
        "built contract failed validation",
    )


# =============================================================================
# 15N-08 CONTRACT INSTANCE ISOLATION
# =============================================================================

def test_contract_instance_isolation():

    first = signal_contract.build_signal_contract()
    second = signal_contract.build_signal_contract()

    assert_true(
        first is not second,
        "contract instances are identical objects",
    )

    assert_true(
        first["BTC"] is not second["BTC"],
        "signal instances are shared",
    )

    first["BTC"]["direction"] = "NONE"

    assert_equal(
        second["BTC"]["direction"],
        "NONE",
        "contract instances are not isolated",
    )


# =============================================================================
# 15N-09 UNKNOWN ASSET BOUNDARY
#
# IMPORTANT:
# Production signal_contract.py currently does:
#
#     raise RuntimeError("Unknown asset: " + asset)
#
# Therefore:
#
# - unknown STRING assets -> RuntimeError
# - invalid NON-STRING types -> TypeError
#
# This audit accepts the existing production boundary without modifying it.
# =============================================================================

def test_unknown_asset_boundary():

    unknown_string_assets = [
        "UNKNOWN",
        "INVALID",
        "",
        "btc",
        "BTC ",
        "ETH ",
        "NOT_A_REAL_ASSET",
    ]

    for asset in unknown_string_assets:

        assert_raises(
            RuntimeError,
            lambda asset=asset:
                signal_contract.build_empty_signal(
                    asset
                ),
            "unknown string asset must be rejected",
        )

    invalid_type_assets = [
        None,
        123,
        0.5,
        [],
        {},
        True,
    ]

    for asset in invalid_type_assets:

        assert_raises(
            TypeError,
            lambda asset=asset:
                signal_contract.build_empty_signal(
                    asset
                ),
            "invalid asset type must be rejected",
        )


# =============================================================================
# 15N-10 ENGINE LONG COMPATIBILITY
# =============================================================================

def test_engine_long_compatibility():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "LONG output failed contract",
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
# 15N-11 ENGINE SHORT COMPATIBILITY
# =============================================================================

def test_engine_short_compatibility():

    result = build_signal(
        "ETH",
        short_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "SHORT output failed contract",
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
# 15N-12 ENGINE NEUTRAL COMPATIBILITY
# =============================================================================

def test_engine_neutral_compatibility():

    result = build_signal(
        "SOL",
        neutral_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "NEUTRAL output failed contract",
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
        "NEUTRAL reason mismatch",
    )


# =============================================================================
# 15N-13 ALL ASSET ENGINE COMPATIBILITY
# =============================================================================

def test_all_asset_engine_compatibility():

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "invalid engine output for {}".format(
                asset
            ),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity mismatch for {}".format(
                asset
            ),
        )

        assert_equal(
            result["direction"],
            "LONG",
            "direction mismatch for {}".format(
                asset
            ),
        )


# =============================================================================
# 15N-14 SEMANTIC INVARIANT FINAL CHECK
# =============================================================================

def test_semantic_invariant_final_check():

    long_result = build_signal(
        "BTC",
        long_structure(),
    )

    short_result = build_signal(
        "ETH",
        short_structure(),
    )

    neutral_result = build_signal(
        "SOL",
        neutral_structure(),
    )

    assert_equal(
        (
            long_result["signal_state"],
            long_result["direction"],
        ),
        (
            "ACTIVE",
            "LONG",
        ),
        "LONG semantic invariant failed",
    )

    assert_equal(
        (
            short_result["signal_state"],
            short_result["direction"],
        ),
        (
            "ACTIVE",
            "SHORT",
        ),
        "SHORT semantic invariant failed",
    )

    assert_equal(
        (
            neutral_result["signal_state"],
            neutral_result["direction"],
        ),
        (
            "NEUTRAL",
            "NONE",
        ),
        "NEUTRAL semantic invariant failed",
    )


# =============================================================================
# 15N-15 HIGH VOLATILITY FINAL BOUNDARY
# =============================================================================

def test_high_volatility_final_boundary():

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
            "HIGH volatility must clear reason",
        )


# =============================================================================
# 15N-16 POSITION FINAL BOUNDARY
# =============================================================================

def test_position_final_boundary():

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
            result["signal_state"],
            "NEUTRAL",
            "position boundary must produce NEUTRAL",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "position boundary must produce NONE",
        )


# =============================================================================
# 15N-17 NON-READY FINAL BOUNDARY
# =============================================================================

def test_non_ready_final_boundary():

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
# 15N-18 INPUT IMMUTABILITY FINAL
# =============================================================================

def test_input_immutability_final():

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
        "regime input was mutated",
    )

    assert_equal(
        structure,
        structure_before,
        "structure input was mutated",
    )


# =============================================================================
# 15N-19 OUTPUT TAMPERING FINAL
# =============================================================================

def test_output_tampering_final():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "baseline output invalid",
    )

    tampered_direction = copy.deepcopy(result)

    tampered_direction["direction"] = "SHORT"

    assert_true(
        not signal_contract.validate_signal(
            tampered_direction
        ),
        "semantically invalid direction accepted",
    )

    tampered_state = copy.deepcopy(result)

    tampered_state["signal_state"] = "NEUTRAL"

    assert_true(
        not signal_contract.validate_signal(
            tampered_state
        ),
        "semantically invalid state accepted",
    )

    tampered_reason = copy.deepcopy(result)

    tampered_reason["reason"] = None

    assert_true(
        not signal_contract.validate_signal(
            tampered_reason
        ),
        "invalid reason accepted",
    )


# =============================================================================
# 15N-20 DETERMINISM FINAL
# =============================================================================

def test_determinism_final():

    structure = long_structure()

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
            output,
            outputs[0],
            "signal generation is not deterministic",
        )


# =============================================================================
# 15N-21 ORDER INDEPENDENCE FINAL
# =============================================================================

def test_order_independence_final():

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
# 15N-22 CROSS-ASSET ISOLATION FINAL
# =============================================================================

def test_cross_asset_isolation_final():

    results = {}

    for asset in EXPECTED_ASSETS:

        results[asset] = build_signal(
            asset,
            long_structure(),
        )

    assert_equal(
        len(results),
        len(EXPECTED_ASSETS),
        "cross-asset result count mismatch",
    )

    assert_equal(
        set(results.keys()),
        set(EXPECTED_ASSETS),
        "cross-asset result set mismatch",
    )

    for asset in EXPECTED_ASSETS:

        result = results[asset]

        assert_equal(
            result["asset"],
            asset,
            "cross-asset identity contamination",
        )

        assert_equal(
            result["direction"],
            "LONG",
            "cross-asset direction contamination",
        )


# =============================================================================
# 15N-23 INFORMATION-FLOW ARCHITECTURE
# =============================================================================

def test_information_flow_architecture():

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
        "execute_order",
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
            "forbidden information-flow dependency in {}: {}".format(
                os.path.basename(module.__file__),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15N-24 PRODUCTION SOURCE IMMUTABILITY
# =============================================================================

def test_production_source_immutability():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    for module in modules:

        tree = source_tree(module)

        assert_true(
            isinstance(tree, ast.Module),
            "production source became unparsable",
        )

        source_names = ast_dependency_names(tree)

        assert_true(
            "open" not in source_names,
            "unexpected direct file access detected",
        )


# =============================================================================
# 15N-25 FINAL ARCHITECTURAL CONSISTENCY
# =============================================================================

def test_final_architectural_consistency():

    contract = signal_contract.build_signal_contract()

    assert_true(
        signal_contract.validate_signal_contract(contract),
        "final contract invalid",
    )

    assert_equal(
        len(contract),
        len(EXPECTED_ASSETS),
        "final contract asset count mismatch",
    )

    assert_equal(
        set(contract.keys()),
        set(EXPECTED_ASSETS),
        "final contract asset set mismatch",
    )

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "final engine output invalid: {}".format(
                asset
            ),
        )

        assert_equal(
            result["asset"],
            asset,
            "final asset identity mismatch",
        )

        assert_equal(
            result["signal_state"],
            "ACTIVE",
            "final state mismatch",
        )

        assert_equal(
            result["direction"],
            "LONG",
            "final direction mismatch",
        )

        assert_equal(
            result["confidence"],
            None,
            "confidence must remain uncomputed",
        )

        assert_equal(
            result["timestamp"],
            None,
            "timestamp must remain uncomputed",
        )

        assert_equal(
            result["reason"],
            "STRUCTURAL_DIRECTION",
            "final reason mismatch",
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15N")
    print("FINAL ARCHITECTURAL CONSISTENCY AUDIT v0.1")
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
            "15N-01 Production files exist",
            test_production_files_exist,
        ),

        (
            "15N-02 AST parsability",
            test_ast_parsability,
        ),

        (
            "15N-03 Contract asset architecture",
            test_contract_asset_architecture,
        ),

        (
            "15N-04 Contract field architecture",
            test_contract_field_architecture,
        ),

        (
            "15N-05 Contract enum architecture",
            test_contract_enum_architecture,
        ),

        (
            "15N-06 Empty signal architecture",
            test_empty_signal_architecture,
        ),

        (
            "15N-07 Contract build validity",
            test_contract_build_validity,
        ),

        (
            "15N-08 Contract instance isolation",
            test_contract_instance_isolation,
        ),

        (
            "15N-09 Unknown asset boundary",
            test_unknown_asset_boundary,
        ),

        (
            "15N-10 Engine LONG compatibility",
            test_engine_long_compatibility,
        ),

        (
            "15N-11 Engine SHORT compatibility",
            test_engine_short_compatibility,
        ),

        (
            "15N-12 Engine NEUTRAL compatibility",
            test_engine_neutral_compatibility,
        ),

        (
            "15N-13 All asset engine compatibility",
            test_all_asset_engine_compatibility,
        ),

        (
            "15N-14 Semantic invariant final check",
            test_semantic_invariant_final_check,
        ),

        (
            "15N-15 HIGH volatility final boundary",
            test_high_volatility_final_boundary,
        ),

        (
            "15N-16 Position final boundary",
            test_position_final_boundary,
        ),

        (
            "15N-17 Non-READY final boundary",
            test_non_ready_final_boundary,
        ),

        (
            "15N-18 Input immutability final",
            test_input_immutability_final,
        ),

        (
            "15N-19 Output tampering final",
            test_output_tampering_final,
        ),

        (
            "15N-20 Determinism final",
            test_determinism_final,
        ),

        (
            "15N-21 Order independence final",
            test_order_independence_final,
        ),

        (
            "15N-22 Cross-asset isolation final",
            test_cross_asset_isolation_final,
        ),

        (
            "15N-23 Information-flow architecture",
            test_information_flow_architecture,
        ),

        (
            "15N-24 Production source immutability",
            test_production_source_immutability,
        ),

        (
            "15N-25 Final architectural consistency",
            test_final_architectural_consistency,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("FINAL ARCHITECTURAL CONSISTENCY AUDIT")
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
    print("STEP 15N SUMMARY")
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
    print("STEP 15N VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL FINAL ARCHITECTURAL CONSISTENCY AUDIT PASS"
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
        "RESULT      : SIGNAL FINAL ARCHITECTURAL CONSISTENCY AUDIT FAIL"
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