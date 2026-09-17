# =============================================================================
# ARUNDA TRADER
# STEP 15D — SIGNAL ADVERSARIAL & INTEGRITY AUDIT v0.2
#
# PURPOSE
# -------
# Adversarial / integrity audit of the existing Signal Layer.
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
#
# IMPORTANT
# ---------
# This audit validates observable contract boundaries.
#
# It does NOT require signal_contract.py to remember provenance of a
# previously generated signal. A standalone contract validator can only
# validate the signal object it receives.
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
# AUDIT FAILURE
# =============================================================================

class AuditFailure(Exception):
    pass


# =============================================================================
# ASSERTION HELPERS
# =============================================================================

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
# 15D-01 BASELINE VALIDITY
# =============================================================================

def test_baseline_validity():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "baseline signal failed contract validation",
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
# 15D-02 ASSET IDENTITY TAMPERING
# =============================================================================

def test_asset_identity_tampering():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    signal["asset"] = "ETH"

    assert_true(
        signal_contract.validate_signal(signal),
        "contract rejected structurally valid standalone asset identity",
    )

    assert_equal(
        signal["asset"],
        "ETH",
        "asset tampering fixture failed",
    )


# =============================================================================
# 15D-03 STRUCTURAL INPUT TAMPERING
# =============================================================================

def test_structural_input_tampering():

    structure = long_structure()

    structure["trend"] = "DOWN"

    result = build_signal(
        "BTC",
        structure,
    )

    assert_true(
        result["direction"] != "LONG",
        "tampered structural trend still produced LONG",
    )


# =============================================================================
# 15D-04 REGIME INPUT TAMPERING
# =============================================================================

def test_regime_input_tampering():

    invalid_regimes = [
        {},
        {"status": "BLOCKED"},
        {"status": "ERROR"},
        {"status": "NOT_READY"},
        {"status": None},
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
            "tampered regime must be rejected",
        )


# =============================================================================
# 15D-05 HIGH VOLATILITY ADVERSARIAL CASE
# =============================================================================

def test_high_volatility_adversarial_case():

    structure = long_structure()

    structure["volatility"] = "HIGH"

    result = build_signal(
        "BTC",
        structure,
    )

    assert_equal(
        result["direction"],
        "NONE",
        "HIGH volatility bypassed signal block",
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "HIGH volatility did not produce NEUTRAL state",
    )


# =============================================================================
# 15D-06 POSITION ADVERSARIAL CASE
# =============================================================================

def test_position_adversarial_case():

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
        "LOWER position bypassed LONG boundary",
    )

    assert_equal(
        short_result["direction"],
        "NONE",
        "UPPER position bypassed SHORT boundary",
    )


# =============================================================================
# 15D-07 STRUCTURAL KEY INJECTION
# =============================================================================

def test_structural_key_injection():

    structure = long_structure()

    structure["direction"] = "SHORT"
    structure["signal_state"] = "ACTIVE"
    structure["confidence"] = 1.0
    structure["reason"] = "INJECTED"

    assert_raises(
        RuntimeError,
        lambda:
            build_signal(
                "BTC",
                structure,
            ),
        "structural key injection must be rejected",
    )


# =============================================================================
# 15D-08 SIGNAL OUTPUT TAMPERING
#
# IMPORTANT
# ----------
# A standalone signal contract cannot know the historical provenance of a
# signal object. Therefore changing:
#
#     LONG -> SHORT
#
# by itself is not necessarily contract-invalid.
#
# This test intentionally checks semantic tampering that the contract can
# objectively detect from the final signal object.
# =============================================================================

def test_signal_output_tampering():

    cases = []

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)
    tampered["direction"] = "NONE"
    cases.append(
        (
            tampered,
            "ACTIVE + NONE must be rejected",
        )
    )

    tampered = copy.deepcopy(signal)
    tampered["signal_state"] = "NEUTRAL"
    cases.append(
        (
            tampered,
            "NEUTRAL + LONG must be rejected",
        )
    )

    tampered = copy.deepcopy(signal)
    tampered["reason"] = None
    cases.append(
        (
            tampered,
            "ACTIVE signal without reason must be rejected",
        )
    )

    tampered = copy.deepcopy(signal)
    tampered["reason"] = "BAD_REASON"
    cases.append(
        (
            tampered,
            "invalid directional reason must be rejected",
        )
    )

    tampered = copy.deepcopy(signal)
    tampered["direction"] = "INVALID"
    cases.append(
        (
            tampered,
            "invalid direction must be rejected",
        )
    )

    for candidate, message in cases:

        assert_true(
            not signal_contract.validate_signal(
                candidate
            ),
            message,
        )


# =============================================================================
# 15D-09 CONTRACT REJECTS TAMPERED SIGNAL
# =============================================================================

def test_contract_rejects_tampered_signal():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    tampered = copy.deepcopy(signal)

    tampered["signal_state"] = "NEUTRAL"
    tampered["direction"] = "LONG"

    assert_true(
        not signal_contract.validate_signal(
            tampered
        ),
        "contract accepted semantically impossible state",
    )


# =============================================================================
# 15D-10 MISSING OUTPUT FIELD
# =============================================================================

def test_missing_output_field():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    del signal["direction"]

    assert_true(
        not signal_contract.validate_signal(signal),
        "contract accepted signal with missing field",
    )


# =============================================================================
# 15D-11 INVALID OUTPUT TYPE
# =============================================================================

def test_invalid_output_type():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    signal["direction"] = 123

    assert_true(
        not signal_contract.validate_signal(signal),
        "contract accepted invalid direction type",
    )


# =============================================================================
# 15D-12 INVALID OUTPUT ENUM
# =============================================================================

def test_invalid_output_enum():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    signal["direction"] = "BUY"

    assert_true(
        not signal_contract.validate_signal(signal),
        "contract accepted invalid direction enum",
    )


# =============================================================================
# 15D-13 SEMANTIC STATE TAMPERING
# =============================================================================

def test_semantic_state_tampering():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    signal["signal_state"] = "NEUTRAL"

    assert_true(
        not signal_contract.validate_signal(signal),
        "contract accepted ACTIVE/NEUTRAL semantic mismatch",
    )


# =============================================================================
# 15D-14 REASON TAMPERING
# =============================================================================

def test_reason_tampering():

    signal = build_signal(
        "BTC",
        long_structure(),
    )

    signal["reason"] = "FAKE_REASON"

    assert_true(
        not signal_contract.validate_signal(signal),
        "contract accepted invalid reason",
    )


# =============================================================================
# 15D-15 NONE SEMANTIC INTEGRITY
# =============================================================================

def test_none_semantic_integrity():

    signal = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        signal["direction"],
        "NONE",
        "neutral structure must produce NONE",
    )

    assert_equal(
        signal["signal_state"],
        "NEUTRAL",
        "NONE direction must be NEUTRAL",
    )

    assert_equal(
        signal["reason"],
        None,
        "NONE direction must have no reason",
    )

    assert_true(
        signal_contract.validate_signal(signal),
        "valid NONE signal rejected",
    )


# =============================================================================
# 15D-16 CONFIDENCE ISOLATION
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
# 15D-17 TIMESTAMP ISOLATION
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
# 15D-18 DETERMINISM UNDER ATTACK
# =============================================================================

def test_determinism_under_attack():

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
            "repeated adversarial execution changed output",
        )


# =============================================================================
# 15D-19 CROSS-ASSET CONTAMINATION
# =============================================================================

def test_cross_asset_contamination():

    signals = {}

    for asset in EXPECTED_ASSETS:

        signals[asset] = build_signal(
            asset,
            long_structure(),
        )

    for asset in EXPECTED_ASSETS:

        signal = signals[asset]

        assert_equal(
            signal["asset"],
            asset,
            "asset identity contamination detected",
        )

        assert_equal(
            signal["direction"],
            "LONG",
            "cross-asset structural contamination detected",
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

    modules = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                modules.append(
                    alias.name
                )

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                modules.append(
                    node.module
                )

    return modules


def called_names(tree):

    names = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            function = node.func

            if isinstance(function, ast.Name):

                names.append(
                    function.id
                )

            elif isinstance(function, ast.Attribute):

                names.append(
                    function.attr
                )

    return names


def attribute_names(tree):

    names = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Attribute):

            names.append(
                node.attr
            )

    return names


# =============================================================================
# 15D-20 PRODUCTION AST INTEGRITY
# =============================================================================

def test_production_ast_integrity():

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
                os.path.basename(
                    module.__file__
                )
            ),
        )


# =============================================================================
# 15D-21 DATABASE ISOLATION
# =============================================================================

def test_database_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden_modules = {
        "sqlite3",
        "sqlite",
        "sqlalchemy",
        "pandas",
        "sqlalchemy.orm",
    }

    forbidden_calls = {
        "connect",
        "cursor",
        "execute",
        "executemany",
        "read_sql",
        "to_sql",
    }

    for module in modules:

        tree = source_tree(module)

        modules_found = set(
            imported_modules(tree)
        )

        overlap = (
            forbidden_modules
            & modules_found
        )

        assert_true(
            not overlap,
            "database dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )

        calls = set(
            called_names(tree)
        )

        overlap = (
            forbidden_calls
            & calls
        )

        assert_true(
            not overlap,
            "database call detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15D-22 NETWORK ISOLATION
#
# IMPORTANT
# ----------
# Do NOT treat generic methods such as:
#
#     dict.get()
#
# as network operations.
#
# Only explicit network imports/calls are considered.
# =============================================================================

def test_network_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden_modules = {
        "requests",
        "httpx",
        "urllib",
        "urllib.request",
        "aiohttp",
        "socket",
        "http.client",
        "ftplib",
        "websocket",
    }

    forbidden_calls = {
        "urlopen",
        "request",
        "urlretrieve",
        "getaddrinfo",
        "create_connection",
        "send",
        "recv",
    }

    for module in modules:

        tree = source_tree(module)

        imports = set(
            imported_modules(tree)
        )

        overlap = (
            forbidden_modules
            & imports
        )

        assert_true(
            not overlap,
            "network dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )

        calls = set(
            called_names(tree)
        )

        overlap = (
            forbidden_calls
            & calls
        )

        assert_true(
            not overlap,
            "network call detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15D-23 FUTURE INFORMATION ISOLATION
# =============================================================================

def test_future_information_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden_modules = {
        "future",
        "forecast",
        "prediction",
        "predictor",
    }

    forbidden_names = {
        "future_price",
        "future_return",
        "forecast",
        "predict",
        "prediction",
        "predicted_price",
        "target_return",
        "forward_return",
    }

    for module in modules:

        tree = source_tree(module)

        imports = set(
            imported_modules(tree)
        )

        overlap = (
            forbidden_modules
            & imports
        )

        assert_true(
            not overlap,
            "future-information module detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )

        names = set()

        for node in ast.walk(tree):

            if isinstance(node, ast.Name):

                names.add(
                    node.id
                )

            elif isinstance(node, ast.Attribute):

                names.add(
                    node.attr
                )

        overlap = (
            forbidden_names
            & names
        )

        assert_true(
            not overlap,
            "future-information dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15D-24 DECISION / EXECUTION ISOLATION
# =============================================================================

def test_decision_execution_isolation():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    forbidden_modules = {
        "decision_engine",
        "execution_engine",
        "order_manager",
        "broker",
        "exchange",
    }

    forbidden_names = {
        "decision",
        "decision_engine",
        "decision_contract",
        "execute",
        "execution",
        "place_order",
        "create_order",
        "cancel_order",
        "buy",
        "sell",
        "order",
    }

    for module in modules:

        tree = source_tree(module)

        imports = set(
            imported_modules(tree)
        )

        overlap = (
            forbidden_modules
            & imports
        )

        assert_true(
            not overlap,
            "decision/execution module detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )

        names = set()

        for node in ast.walk(tree):

            if isinstance(node, ast.Name):

                names.add(
                    node.id
                )

            elif isinstance(node, ast.Attribute):

                names.add(
                    node.attr
                )

        overlap = (
            forbidden_names
            & names
        )

        assert_true(
            not overlap,
            "decision/execution dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15D-25 INFORMATION-FLOW BOUNDARY
# =============================================================================

def test_information_flow_boundary():

    engine_tree = source_tree(
        signal_engine
    )

    logic_tree = source_tree(
        signal_logic
    )

    contract_tree = source_tree(
        signal_contract
    )

    engine_imports = set(
        imported_modules(
            engine_tree
        )
    )

    logic_imports = set(
        imported_modules(
            logic_tree
        )
    )

    contract_imports = set(
        imported_modules(
            contract_tree
        )
    )

    # Engine is allowed to depend on signal_logic and signal_contract.
    allowed_engine = {
        "signal_logic",
        "signal_contract",
    }

    engine_signal_imports = {
        name
        for name in engine_imports
        if name in {
            "signal_logic",
            "signal_contract",
        }
    }

    assert_true(
        engine_signal_imports <= allowed_engine,
        "unexpected engine signal dependency detected",
    )

    # signal_logic must not import signal_engine.
    assert_true(
        "signal_engine" not in logic_imports,
        "signal_logic depends on signal_engine",
    )

    # signal_contract must not import signal_engine.
    assert_true(
        "signal_engine" not in contract_imports,
        "signal_contract depends on signal_engine",
    )

    # signal_contract must remain independent of signal_logic.
    assert_true(
        "signal_logic" not in contract_imports,
        "signal_contract depends on signal_logic",
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15D")
    print("SIGNAL ADVERSARIAL & INTEGRITY AUDIT v0.2")
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
        "Prediction   : NOT USED"
    )

    print(
        "Decision     : NOT USED"
    )

    print(
        "Execution    : NOT USED"
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
            "15D-01 Baseline validity",
            test_baseline_validity,
        ),

        (
            "15D-02 Asset identity tampering",
            test_asset_identity_tampering,
        ),

        (
            "15D-03 Structural input tampering",
            test_structural_input_tampering,
        ),

        (
            "15D-04 Regime input tampering",
            test_regime_input_tampering,
        ),

        (
            "15D-05 HIGH volatility adversarial case",
            test_high_volatility_adversarial_case,
        ),

        (
            "15D-06 Position adversarial case",
            test_position_adversarial_case,
        ),

        (
            "15D-07 Structural key injection",
            test_structural_key_injection,
        ),

        (
            "15D-08 Signal output tampering",
            test_signal_output_tampering,
        ),

        (
            "15D-09 Contract rejects tampered signal",
            test_contract_rejects_tampered_signal,
        ),

        (
            "15D-10 Missing output field",
            test_missing_output_field,
        ),

        (
            "15D-11 Invalid output type",
            test_invalid_output_type,
        ),

        (
            "15D-12 Invalid output enum",
            test_invalid_output_enum,
        ),

        (
            "15D-13 Semantic state tampering",
            test_semantic_state_tampering,
        ),

        (
            "15D-14 Reason tampering",
            test_reason_tampering,
        ),

        (
            "15D-15 NONE semantic integrity",
            test_none_semantic_integrity,
        ),

        (
            "15D-16 Confidence isolation",
            test_confidence_isolation,
        ),

        (
            "15D-17 Timestamp isolation",
            test_timestamp_isolation,
        ),

        (
            "15D-18 Determinism under attack",
            test_determinism_under_attack,
        ),

        (
            "15D-19 Cross-asset contamination",
            test_cross_asset_contamination,
        ),

        (
            "15D-20 Production AST integrity",
            test_production_ast_integrity,
        ),

        (
            "15D-21 Database isolation",
            test_database_isolation,
        ),

        (
            "15D-22 Network isolation",
            test_network_isolation,
        ),

        (
            "15D-23 Future information isolation",
            test_future_information_isolation,
        ),

        (
            "15D-24 Decision/execution isolation",
            test_decision_execution_isolation,
        ),

        (
            "15D-25 Information-flow boundary",
            test_information_flow_boundary,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("ADVERSARIAL / INTEGRITY AUDIT")
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
    print("STEP 15D SUMMARY")
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
    print("STEP 15D VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL ADVERSARIAL & INTEGRITY AUDIT PASS"
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
        "RESULT      : SIGNAL ADVERSARIAL & INTEGRITY AUDIT FAIL"
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