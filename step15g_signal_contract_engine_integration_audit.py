# =============================================================================
# ARUNDA TRADER
# STEP 15G — SIGNAL CONTRACT & ENGINE INTEGRATION AUDIT v0.1
#
# PURPOSE
# -------
# Validate integration between:
#
#   signal_engine.py
#   signal_logic.py
#   signal_contract.py
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
# SCORING
# -------
# NOT USED
#
# PREDICTION
# ----------
# NOT USED
#
# DECISION
# --------
# NOT USED
#
# EXECUTION
# ---------
# NOT USED
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


# =============================================================================
# EXPECTED CONTRACT VALUES
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

EXPECTED_SIGNAL_FIELDS = {
    "asset",
    "timestamp",
    "signal_state",
    "direction",
    "confidence",
    "reason",
}

EXPECTED_DIRECTIONS = {
    "NONE",
    "LONG",
    "SHORT",
}

EXPECTED_STATES = {
    "NEUTRAL",
    "ACTIVE",
}


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
            "{:<56} : PASS".format(name)
        )

        return True

    except Exception as error:

        print(
            "{:<56} : FAIL".format(name)
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
        structural_record(
            structure
        ),
    )


# =============================================================================
# AST UTILITIES
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


def imported_modules(tree):

    modules = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                modules.add(
                    alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                modules.add(
                    node.module.split(".")[0]
                )

    return modules


def function_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            names.add(node.name)

    return names


def called_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            target = node.func

            if isinstance(
                target,
                ast.Name,
            ):

                names.add(target.id)

            elif isinstance(
                target,
                ast.Attribute,
            ):

                names.add(target.attr)

    return names


def attribute_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Attribute):

            names.add(node.attr)

    return names


# =============================================================================
# 15G-01 PRODUCTION FILE EXISTENCE
# =============================================================================

def test_production_files_exist():

    modules = [
        signal_engine,
        signal_logic,
        signal_contract,
    ]

    for module in modules:

        assert_true(
            module.__file__ is not None,
            "module file missing: {}".format(
                module.__name__
            ),
        )

        assert_true(
            os.path.isfile(
                module.__file__
            ),
            "production file does not exist: {}".format(
                module.__file__
            ),
        )


# =============================================================================
# 15G-02 AST PARSABILITY
# =============================================================================

def test_ast_parsability():

    modules = [
        signal_engine,
        signal_logic,
        signal_contract,
    ]

    for module in modules:

        tree = source_tree(module)

        assert_true(
            isinstance(tree, ast.Module),
            "AST parse failed: {}".format(
                module.__name__
            ),
        )


# =============================================================================
# 15G-03 ENGINE ENTRYPOINT
# =============================================================================

def test_engine_entrypoint():

    assert_true(
        hasattr(
            signal_engine,
            "build_signal",
        ),
        "signal_engine.build_signal missing",
    )

    assert_true(
        callable(
            signal_engine.build_signal
        ),
        "signal_engine.build_signal is not callable",
    )


# =============================================================================
# 15G-04 LOGIC ENTRYPOINT
# =============================================================================

def test_logic_entrypoint():

    names = function_names(
        source_tree(
            signal_logic
        )
    )

    assert_true(
        len(names) > 0,
        "signal_logic contains no callable functions",
    )


# =============================================================================
# 15G-05 CONTRACT ENTRYPOINTS
# =============================================================================

def test_contract_entrypoints():

    required = [
        "build_empty_signal",
        "build_signal_contract",
        "validate_signal",
        "validate_signal_contract",
        "load_signal_contract",
    ]

    for name in required:

        assert_true(
            hasattr(
                signal_contract,
                name,
            ),
            "missing contract entrypoint: {}".format(
                name
            ),
        )

        assert_true(
            callable(
                getattr(
                    signal_contract,
                    name,
                )
            ),
            "contract entrypoint not callable: {}".format(
                name
            ),
        )


# =============================================================================
# 15G-06 BASIC ENGINE -> CONTRACT COMPATIBILITY
# =============================================================================

def test_basic_engine_contract_compatibility():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        isinstance(
            result,
            dict,
        ),
        "engine output is not dict",
    )

    assert_equal(
        set(result.keys()),
        EXPECTED_SIGNAL_FIELDS,
        "engine output schema incompatible with contract",
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "engine output rejected by signal contract",
    )


# =============================================================================
# 15G-07 LONG INTEGRATION
# =============================================================================

def test_long_integration():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        result["asset"],
        "BTC",
        "LONG asset identity mismatch",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "LONG integration direction mismatch",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "LONG integration state mismatch",
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "LONG engine output rejected by contract",
    )


# =============================================================================
# 15G-08 SHORT INTEGRATION
# =============================================================================

def test_short_integration():

    result = build_signal(
        "BTC",
        short_structure(),
    )

    assert_equal(
        result["asset"],
        "BTC",
        "SHORT asset identity mismatch",
    )

    assert_equal(
        result["direction"],
        "SHORT",
        "SHORT integration direction mismatch",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "SHORT integration state mismatch",
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "SHORT engine output rejected by contract",
    )


# =============================================================================
# 15G-09 NEUTRAL INTEGRATION
# =============================================================================

def test_neutral_integration():

    result = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        result["direction"],
        "NONE",
        "NEUTRAL direction mismatch",
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "NEUTRAL state mismatch",
    )

    assert_equal(
        result["reason"],
        None,
        "NEUTRAL reason must be None",
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "NEUTRAL engine output rejected by contract",
    )


# =============================================================================
# 15G-10 ALL ASSETS CONTRACT COMPATIBILITY
# =============================================================================

def test_all_assets_contract_compatibility():

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity mismatch: {}".format(
                asset
            ),
        )

        assert_true(
            signal_contract.validate_signal(
                result
            ),
            "contract rejected asset output: {}".format(
                asset
            ),
        )


# =============================================================================
# 15G-11 CROSS-ASSET ISOLATION
# =============================================================================

def test_cross_asset_isolation():

    outputs = {}

    for asset in EXPECTED_ASSETS:

        outputs[asset] = build_signal(
            asset,
            long_structure(),
        )

    for asset in EXPECTED_ASSETS:

        for other in EXPECTED_ASSETS:

            if asset == other:
                continue

            assert_true(
                outputs[asset]["asset"] != outputs[other]["asset"],
                "cross-asset identity collision",
            )


# =============================================================================
# 15G-12 CONTRACT ASSET IDENTITY
# =============================================================================

def test_contract_asset_identity():

    contract = (
        signal_contract.build_signal_contract()
    )

    assert_true(
        signal_contract.validate_signal_contract(
            contract
        ),
        "generated signal contract invalid",
    )

    for asset in EXPECTED_ASSETS:

        assert_true(
            asset in contract,
            "asset missing from contract: {}".format(
                asset
            ),
        )

        assert_equal(
            contract[asset]["asset"],
            asset,
            "contract asset identity mismatch",
        )


# =============================================================================
# 15G-13 ENGINE OUTPUT FIELD EXACTNESS
# =============================================================================

def test_engine_output_field_exactness():

    for asset in EXPECTED_ASSETS:

        result = build_signal(
            asset,
            long_structure(),
        )

        assert_equal(
            set(result.keys()),
            EXPECTED_SIGNAL_FIELDS,
            "unexpected engine output fields",
        )


# =============================================================================
# 15G-14 OUTPUT VALIDATION ROUNDTRIP
# =============================================================================

def test_output_validation_roundtrip():

    for structure in [
        long_structure(),
        short_structure(),
        neutral_structure(),
    ]:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_true(
            signal_contract.validate_signal(
                result
            ),
            "valid engine output failed contract roundtrip",
        )


# =============================================================================
# 15G-15 OUTPUT COPY VALIDATION
# =============================================================================

def test_output_copy_validation():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    copied = copy.deepcopy(
        result
    )

    assert_true(
        signal_contract.validate_signal(
            copied
        ),
        "deep-copied valid output rejected",
    )

    assert_equal(
        copied,
        result,
        "deep copy changed signal output",
    )


# =============================================================================
# 15G-16 INPUT IMMUTABILITY
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
        "regime mutated during integration",
    )

    assert_equal(
        structure,
        structure_before,
        "structure mutated during integration",
    )


# =============================================================================
# 15G-17 CONTRACT REJECTION PROPAGATION
# =============================================================================

def test_contract_rejection_propagation():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(
        result
    )

    tampered["direction"] = "INVALID"

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted invalid direction",
    )


# =============================================================================
# 15G-18 STATE/DIRECTION SEMANTIC PROTECTION
# =============================================================================

def test_state_direction_semantic_protection():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(
        result
    )

    tampered["signal_state"] = "NEUTRAL"

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted ACTIVE/NEUTRAL semantic mismatch",
    )


# =============================================================================
# 15G-19 REASON CONTRACT PROTECTION
# =============================================================================

def test_reason_contract_protection():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(
        result
    )

    tampered["reason"] = None

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted invalid ACTIVE reason",
    )


# =============================================================================
# 15G-20 DETERMINISTIC INTEGRATION
# =============================================================================

def test_deterministic_integration():

    structure = long_structure()

    outputs = []

    for _ in range(10):

        outputs.append(
            build_signal(
                "BTC",
                copy.deepcopy(
                    structure
                ),
            )
        )

    for output in outputs:

        assert_equal(
            output,
            outputs[0],
            "engine/contract integration is nondeterministic",
        )


# =============================================================================
# 15G-21 ENGINE DOES NOT BYPASS CONTRACT
# =============================================================================

def test_engine_contract_dependency():

    tree = source_tree(
        signal_engine
    )

    imports = imported_modules(
        tree
    )

    assert_true(
        "signal_contract" in imports,
        "signal_engine does not import signal_contract",
    )


# =============================================================================
# 15G-22 ENGINE USES SIGNAL LOGIC
# =============================================================================

def test_engine_logic_dependency():

    tree = source_tree(
        signal_engine
    )

    imports = imported_modules(
        tree
    )

    assert_true(
        "signal_logic" in imports,
        "signal_engine does not import signal_logic",
    )


# =============================================================================
# 15G-23 LOGIC DOES NOT DEPEND ON ENGINE
# =============================================================================

def test_logic_engine_prohibition():

    tree = source_tree(
        signal_logic
    )

    imports = imported_modules(
        tree
    )

    assert_true(
        "signal_engine" not in imports,
        "signal_logic illegally depends on signal_engine",
    )


# =============================================================================
# 15G-24 CONTRACT DOES NOT DEPEND ON ENGINE OR LOGIC
# =============================================================================

def test_contract_dependency_prohibition():

    tree = source_tree(
        signal_contract
    )

    imports = imported_modules(
        tree
    )

    assert_true(
        "signal_engine" not in imports,
        "signal_contract illegally depends on signal_engine",
    )

    assert_true(
        "signal_logic" not in imports,
        "signal_contract illegally depends on signal_logic",
    )


# =============================================================================
# 15G-25 INFORMATION-FLOW INTEGRATION INTEGRITY
# =============================================================================

def test_information_flow_integration():

    modules = [
        signal_engine,
        signal_logic,
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
        "httpx",
        "aiohttp",
        "socket",
        "subprocess",
        "future_price",
        "future_return",
        "forecast",
        "prediction",
        "predict",
        "decision",
        "decision_engine",
        "order",
        "place_order",
        "buy",
        "sell",
        "score",
        "scoring",
        "calculate_score",
    }

    for module in modules:

        tree = source_tree(
            module
        )

        names = (
            set(
                node.id
                for node in ast.walk(tree)
                if isinstance(
                    node,
                    ast.Name,
                )
            )
        )

        names.update(
            node.attr
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.Attribute,
            )
        )

        overlap = (
            forbidden & names
        )

        assert_true(
            not overlap,
            "forbidden integration dependency in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print(
        "ARUNDA TRADER — STEP 15G"
    )
    print(
        "SIGNAL CONTRACT & ENGINE INTEGRATION AUDIT v0.1"
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
            "15G-01 Production files exist",
            test_production_files_exist,
        ),

        (
            "15G-02 AST parsability",
            test_ast_parsability,
        ),

        (
            "15G-03 Engine entrypoint",
            test_engine_entrypoint,
        ),

        (
            "15G-04 Logic entrypoint",
            test_logic_entrypoint,
        ),

        (
            "15G-05 Contract entrypoints",
            test_contract_entrypoints,
        ),

        (
            "15G-06 Basic engine/contract compatibility",
            test_basic_engine_contract_compatibility,
        ),

        (
            "15G-07 LONG integration",
            test_long_integration,
        ),

        (
            "15G-08 SHORT integration",
            test_short_integration,
        ),

        (
            "15G-09 NEUTRAL integration",
            test_neutral_integration,
        ),

        (
            "15G-10 All-assets contract compatibility",
            test_all_assets_contract_compatibility,
        ),

        (
            "15G-11 Cross-asset isolation",
            test_cross_asset_isolation,
        ),

        (
            "15G-12 Contract asset identity",
            test_contract_asset_identity,
        ),

        (
            "15G-13 Engine output field exactness",
            test_engine_output_field_exactness,
        ),

        (
            "15G-14 Output validation roundtrip",
            test_output_validation_roundtrip,
        ),

        (
            "15G-15 Output copy validation",
            test_output_copy_validation,
        ),

        (
            "15G-16 Input immutability",
            test_input_immutability,
        ),

        (
            "15G-17 Contract rejection propagation",
            test_contract_rejection_propagation,
        ),

        (
            "15G-18 State/direction semantic protection",
            test_state_direction_semantic_protection,
        ),

        (
            "15G-19 Reason contract protection",
            test_reason_contract_protection,
        ),

        (
            "15G-20 Deterministic integration",
            test_deterministic_integration,
        ),

        (
            "15G-21 Engine does not bypass contract",
            test_engine_contract_dependency,
        ),

        (
            "15G-22 Engine uses signal logic",
            test_engine_logic_dependency,
        ),

        (
            "15G-23 Logic does not depend on engine",
            test_logic_engine_prohibition,
        ),

        (
            "15G-24 Contract dependency prohibition",
            test_contract_dependency_prohibition,
        ),

        (
            "15G-25 Information-flow integration integrity",
            test_information_flow_integration,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print(
        "CONTRACT / ENGINE INTEGRATION AUDIT"
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
        "STEP 15G SUMMARY"
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
        "STEP 15G VERDICT"
    )
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL CONTRACT & ENGINE INTEGRATION AUDIT PASS"
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
        "RESULT      : SIGNAL CONTRACT & ENGINE INTEGRATION AUDIT FAIL"
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