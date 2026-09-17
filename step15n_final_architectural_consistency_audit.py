# =============================================================================
# ARUNDA TRADER
# STEP 15N — FINAL ARCHITECTURAL CONSISTENCY AUDIT v0.1
#
# MODE        : READ ONLY / AUDIT ONLY
# DATABASE    : NOT USED
# WRITES      : NONE
# SCORING     : NOT USED
# PREDICTION  : NOT USED
# DECISION    : NOT USED
# EXECUTION   : NOT USED
#
# PRODUCTION FILES ARE NOT MODIFIED
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
        print("{:<52} : PASS".format(name))
        return True

    except Exception as error:
        print("{:<52} : FAIL".format(name))
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
                names.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])

    return names


# =============================================================================
# 15N-01 PRODUCTION FILES EXIST
# =============================================================================

def test_production_files_exist():

    required = [
        "signal_logic.py",
        "signal_engine.py",
        "signal_contract.py",
    ]

    base = os.path.dirname(
        os.path.abspath(__file__)
    )

    for filename in required:

        path = os.path.join(
            base,
            filename,
        )

        assert_true(
            os.path.isfile(path),
            "missing production file: {}".format(filename),
        )


# =============================================================================
# 15N-02 AST PARSABILITY
# =============================================================================

def test_ast_parsability():

    for module in [
        signal_logic,
        signal_engine,
        signal_contract,
    ]:

        source_tree(module)


# =============================================================================
# 15N-03 CONTRACT ASSET ARCHITECTURE
# =============================================================================

def test_contract_asset_architecture():

    assert_equal(
        signal_contract.EXPECTED_ASSETS,
        EXPECTED_ASSETS,
        "contract asset architecture mismatch",
    )


# =============================================================================
# 15N-04 CONTRACT FIELD ARCHITECTURE
# =============================================================================

def test_contract_field_architecture():

    expected = {
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    }

    assert_equal(
        set(signal_contract.SIGNAL_FIELDS),
        expected,
        "contract field architecture mismatch",
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

    signal = signal_contract.build_empty_signal(
        "BTC"
    )

    assert_true(
        signal_contract.validate_signal(signal),
        "empty BTC signal failed validation",
    )

    assert_equal(
        signal["asset"],
        "BTC",
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

    assert_equal(
        signal["confidence"],
        None,
        "empty confidence mismatch",
    )

    assert_equal(
        signal["timestamp"],
        None,
        "empty timestamp mismatch",
    )

    assert_equal(
        signal["reason"],
        None,
        "empty reason mismatch",
    )


# =============================================================================
# 15N-07 CONTRACT BUILD VALIDITY
# =============================================================================

def test_contract_build_validity():

    contract = signal_contract.build_signal_contract()

    assert_true(
        signal_contract.validate_signal_contract(contract),
        "built contract is invalid",
    )

    assert_equal(
        len(contract),
        15,
        "contract asset count mismatch",
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

    first["BTC"]["direction"] = "LONG"

    assert_equal(
        second["BTC"]["direction"],
        "NONE",
        "contract instances share mutable state",
    )


# =============================================================================
# 15N-09 UNKNOWN ASSET BOUNDARY
# =============================================================================

def test_unknown_asset_boundary():

    invalid_assets = [
        "UNKNOWN",
        "",
        "BTC_USDT",
        None,
        123,
        [],
        {},
        True,
    ]

    for asset in invalid_assets:

        assert_raises(
            RuntimeError,
            lambda asset=asset:
                signal_contract.build_empty_signal(asset),
            "unknown asset must be rejected",
        )


# =============================================================================
# 15N-10 ENGINE LONG COMPATIBILITY
# =============================================================================

def test_engine_long():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "LONG engine output invalid",
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

def test_engine_short():

    result = build_signal(
        "ETH",
        short_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "SHORT engine output invalid",
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

def test_engine_neutral():

    result = build_signal(
        "SOL",
        neutral_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "NEUTRAL engine output invalid",
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

def test_all_asset_engine():

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "invalid engine output for {}".format(asset),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity mismatch",
        )

        assert_equal(
            result["direction"],
            "LONG",
            "direction mismatch",
        )


# =============================================================================
# 15N-14 SEMANTIC INVARIANT FINAL CHECK
# =============================================================================

def test_semantic_invariant():

    valid_pairs = [
        ("ACTIVE", "LONG"),
        ("ACTIVE", "SHORT"),
        ("NEUTRAL", "NONE"),
    ]

    invalid_pairs = [
        ("ACTIVE", "NONE"),
        ("NEUTRAL", "LONG"),
        ("NEUTRAL", "SHORT"),
    ]

    base = signal_contract.build_empty_signal(
        "BTC"
    )

    for state, direction in valid_pairs:

        signal = copy.deepcopy(base)

        signal["signal_state"] = state
        signal["direction"] = direction

        if state == "ACTIVE":
            signal["reason"] = "STRUCTURAL_DIRECTION"

        assert_true(
            signal_contract.validate_signal(signal),
            "valid semantic pair rejected: {} {}".format(
                state,
                direction,
            ),
        )

    for state, direction in invalid_pairs:

        signal = copy.deepcopy(base)

        signal["signal_state"] = state
        signal["direction"] = direction

        if state == "ACTIVE":
            signal["reason"] = "STRUCTURAL_DIRECTION"

        assert_true(
            not signal_contract.validate_signal(signal),
            "invalid semantic pair accepted: {} {}".format(
                state,
                direction,
            ),
        )


# =============================================================================
# 15N-15 HIGH VOLATILITY FINAL BOUNDARY
# =============================================================================

def test_high_volatility():

    structure = long_structure()
    structure["volatility"] = "HIGH"

    result = build_signal(
        "BTC",
        structure,
    )

    assert_true(
        signal_contract.validate_signal(result),
        "HIGH volatility result invalid",
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "HIGH volatility state boundary failed",
    )

    assert_equal(
        result["direction"],
        "NONE",
        "HIGH volatility direction boundary failed",
    )


# =============================================================================
# 15N-16 POSITION FINAL BOUNDARY
# =============================================================================

def test_position_boundary():

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
            "position boundary result invalid",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "position boundary failed",
        )


# =============================================================================
# 15N-17 NON-READY FINAL BOUNDARY
# =============================================================================

def test_non_ready_boundary():

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
            "non-ready regime must be rejected",
        )


# =============================================================================
# 15N-18 INPUT IMMUTABILITY FINAL
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
        "structure was mutated",
    )


# =============================================================================
# 15N-19 OUTPUT TAMPERING FINAL
#
# IMPORTANT:
# A LONG -> SHORT mutation is NOT intrinsically invalid under the schema.
# Therefore this test uses an actually semantically invalid combination:
#
# ACTIVE + NONE
#
# The contract MUST reject it.
# =============================================================================

def test_output_tampering():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "baseline signal is not ACTIVE",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "baseline signal is not LONG",
    )

    tampered = copy.deepcopy(result)

    tampered["direction"] = "NONE"

    assert_true(
        not signal_contract.validate_signal(tampered),
        "semantically invalid direction accepted",
    )


# =============================================================================
# 15N-20 DETERMINISM FINAL
# =============================================================================

def test_determinism():

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

def test_order_independence():

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
# 15N-22 CROSS-ASSET ISOLATION
# =============================================================================

def test_cross_asset_isolation():

    results = {}

    for asset in EXPECTED_ASSETS:

        results[asset] = build_signal(
            asset,
            long_structure(),
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
        "place_order",
        "scoring",
        "calculate_score",
        "build_score",
    }

    for module in modules:

        tree = source_tree(module)
        names = ast_dependency_names(tree)

        overlap = forbidden & names

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

        path = module.__file__

        assert_true(
            os.path.isfile(path),
            "production source missing: {}".format(
                os.path.basename(path)
            ),
        )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            content = file.read()

        assert_true(
            len(content) > 0,
            "production source is empty: {}".format(
                os.path.basename(path)
            ),
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
        "final asset count mismatch",
    )

    assert_equal(
        set(contract.keys()),
        set(EXPECTED_ASSETS),
        "final asset set mismatch",
    )

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_true(
            signal_contract.validate_signal(result),
            "final engine output invalid: {}".format(asset),
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
            "final confidence must remain None",
        )

        assert_equal(
            result["timestamp"],
            None,
            "final timestamp must remain None",
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

    print("Production files:")
    print("  - signal_logic.py")
    print("  - signal_engine.py")
    print("  - signal_contract.py")

    print()
    print("=" * 78)
    print()
    print("=" * 78)
    print("FINAL ARCHITECTURAL CONSISTENCY AUDIT")
    print("=" * 78)

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
            test_engine_long,
        ),

        (
            "15N-11 Engine SHORT compatibility",
            test_engine_short,
        ),

        (
            "15N-12 Engine NEUTRAL compatibility",
            test_engine_neutral,
        ),

        (
            "15N-13 All asset engine compatibility",
            test_all_asset_engine,
        ),

        (
            "15N-14 Semantic invariant final check",
            test_semantic_invariant,
        ),

        (
            "15N-15 HIGH volatility final boundary",
            test_high_volatility,
        ),

        (
            "15N-16 Position final boundary",
            test_position_boundary,
        ),

        (
            "15N-17 Non-READY final boundary",
            test_non_ready_boundary,
        ),

        (
            "15N-18 Input immutability final",
            test_input_immutability,
        ),

        (
            "15N-19 Output tampering final",
            test_output_tampering,
        ),

        (
            "15N-20 Determinism final",
            test_determinism,
        ),

        (
            "15N-21 Order independence final",
            test_order_independence,
        ),

        (
            "15N-22 Cross-asset isolation final",
            test_cross_asset_isolation,
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


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
