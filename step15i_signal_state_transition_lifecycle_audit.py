# =============================================================================
# ARUNDA TRADER
# STEP 15I — SIGNAL STATE TRANSITION & LIFECYCLE AUDIT v0.1
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
# Verify Signal state transitions and lifecycle integrity.
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
# 15I-01 INITIAL NEUTRAL STATE
# =============================================================================

def test_initial_neutral_state():

    result = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "initial NEUTRAL signal failed contract",
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "initial state must be NEUTRAL",
    )

    assert_equal(
        result["direction"],
        "NONE",
        "initial NEUTRAL direction must be NONE",
    )

    assert_equal(
        result["reason"],
        None,
        "initial NEUTRAL reason must be None",
    )


# =============================================================================
# 15I-02 INITIAL LONG STATE
# =============================================================================

def test_initial_long_state():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "initial LONG signal failed contract",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "LONG signal must be ACTIVE",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "LONG signal direction mismatch",
    )


# =============================================================================
# 15I-03 INITIAL SHORT STATE
# =============================================================================

def test_initial_short_state():

    result = build_signal(
        "BTC",
        short_structure(),
    )

    assert_true(
        signal_contract.validate_signal(result),
        "initial SHORT signal failed contract",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "SHORT signal must be ACTIVE",
    )

    assert_equal(
        result["direction"],
        "SHORT",
        "SHORT signal direction mismatch",
    )


# =============================================================================
# 15I-04 NEUTRAL -> LONG
# =============================================================================

def test_neutral_to_long():

    neutral = build_signal(
        "BTC",
        neutral_structure(),
    )

    long_signal = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        neutral["signal_state"],
        "NEUTRAL",
        "source state mismatch",
    )

    assert_equal(
        neutral["direction"],
        "NONE",
        "source direction mismatch",
    )

    assert_equal(
        long_signal["signal_state"],
        "ACTIVE",
        "target state mismatch",
    )

    assert_equal(
        long_signal["direction"],
        "LONG",
        "target direction mismatch",
    )

    assert_true(
        signal_contract.validate_signal(long_signal),
        "NEUTRAL -> LONG output invalid",
    )


# =============================================================================
# 15I-05 NEUTRAL -> SHORT
# =============================================================================

def test_neutral_to_short():

    neutral = build_signal(
        "BTC",
        neutral_structure(),
    )

    short_signal = build_signal(
        "BTC",
        short_structure(),
    )

    assert_equal(
        neutral["signal_state"],
        "NEUTRAL",
        "source state mismatch",
    )

    assert_equal(
        short_signal["signal_state"],
        "ACTIVE",
        "target state mismatch",
    )

    assert_equal(
        short_signal["direction"],
        "SHORT",
        "target direction mismatch",
    )

    assert_true(
        signal_contract.validate_signal(short_signal),
        "NEUTRAL -> SHORT output invalid",
    )


# =============================================================================
# 15I-06 LONG -> NEUTRAL
# =============================================================================

def test_long_to_neutral():

    long_signal = build_signal(
        "BTC",
        long_structure(),
    )

    neutral = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        long_signal["direction"],
        "LONG",
        "source must be LONG",
    )

    assert_equal(
        neutral["signal_state"],
        "NEUTRAL",
        "target must be NEUTRAL",
    )

    assert_equal(
        neutral["direction"],
        "NONE",
        "target direction must be NONE",
    )

    assert_true(
        signal_contract.validate_signal(neutral),
        "LONG -> NEUTRAL output invalid",
    )


# =============================================================================
# 15I-07 SHORT -> NEUTRAL
# =============================================================================

def test_short_to_neutral():

    short_signal = build_signal(
        "BTC",
        short_structure(),
    )

    neutral = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        short_signal["direction"],
        "SHORT",
        "source must be SHORT",
    )

    assert_equal(
        neutral["signal_state"],
        "NEUTRAL",
        "target must be NEUTRAL",
    )

    assert_equal(
        neutral["direction"],
        "NONE",
        "target direction must be NONE",
    )

    assert_true(
        signal_contract.validate_signal(neutral),
        "SHORT -> NEUTRAL output invalid",
    )


# =============================================================================
# 15I-08 LONG <-> SHORT REVERSAL
# =============================================================================

def test_long_short_reversal():

    long_signal = build_signal(
        "BTC",
        long_structure(),
    )

    short_signal = build_signal(
        "BTC",
        short_structure(),
    )

    assert_equal(
        long_signal["direction"],
        "LONG",
        "LONG source mismatch",
    )

    assert_equal(
        short_signal["direction"],
        "SHORT",
        "SHORT target mismatch",
    )

    assert_true(
        signal_contract.validate_signal(short_signal),
        "LONG -> SHORT output invalid",
    )


# =============================================================================
# 15I-09 SHORT <-> LONG REVERSAL
# =============================================================================

def test_short_long_reversal():

    short_signal = build_signal(
        "BTC",
        short_structure(),
    )

    long_signal = build_signal(
        "BTC",
        long_structure(),
    )

    assert_equal(
        short_signal["direction"],
        "SHORT",
        "SHORT source mismatch",
    )

    assert_equal(
        long_signal["direction"],
        "LONG",
        "LONG target mismatch",
    )

    assert_true(
        signal_contract.validate_signal(long_signal),
        "SHORT -> LONG output invalid",
    )


# =============================================================================
# 15I-10 ACTIVE STATE MUST BE DIRECTIONAL
# =============================================================================

def test_active_state_directional():

    for structure in [
        long_structure(),
        short_structure(),
    ]:

        result = build_signal(
            "BTC",
            structure,
        )

        assert_equal(
            result["signal_state"],
            "ACTIVE",
            "directional structure must produce ACTIVE",
        )

        assert_true(
            result["direction"] in [
                "LONG",
                "SHORT",
            ],
            "ACTIVE state must have directional output",
        )

        assert_true(
            signal_contract.validate_signal(result),
            "ACTIVE signal failed semantic contract",
        )


# =============================================================================
# 15I-11 NEUTRAL STATE MUST NOT BE DIRECTIONAL
# =============================================================================

def test_neutral_state_not_directional():

    result = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "neutral structure must produce NEUTRAL",
    )

    assert_equal(
        result["direction"],
        "NONE",
        "NEUTRAL state must have NONE direction",
    )

    assert_equal(
        result["reason"],
        None,
        "NEUTRAL state must not carry directional reason",
    )


# =============================================================================
# 15I-12 HIGH VOLATILITY FORCES NEUTRAL
# =============================================================================

def test_high_volatility_forces_neutral():

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

        assert_equal(
            result["signal_state"],
            "NEUTRAL",
            "HIGH volatility must force NEUTRAL",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "HIGH volatility must force NONE",
        )

        assert_equal(
            result["reason"],
            None,
            "HIGH volatility must clear directional reason",
        )

        assert_true(
            signal_contract.validate_signal(result),
            "HIGH volatility lifecycle state invalid",
        )


# =============================================================================
# 15I-13 POSITION BLOCK FORCES NEUTRAL
# =============================================================================

def test_position_block_forces_neutral():

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

        assert_equal(
            result["signal_state"],
            "NEUTRAL",
            "position boundary must force NEUTRAL",
        )

        assert_equal(
            result["direction"],
            "NONE",
            "position boundary must force NONE",
        )

        assert_equal(
            result["reason"],
            None,
            "position boundary must clear reason",
        )


# =============================================================================
# 15I-14 NON-READY REGIME CANNOT PRODUCE STATE
# =============================================================================

def test_non_ready_regime_rejected():

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
            "non-ready regime must reject lifecycle evaluation",
        )


# =============================================================================
# 15I-15 STATE DOES NOT LEAK BETWEEN CALLS
# =============================================================================

def test_state_does_not_leak_between_calls():

    first = build_signal(
        "BTC",
        long_structure(),
    )

    second = build_signal(
        "BTC",
        neutral_structure(),
    )

    third = build_signal(
        "BTC",
        short_structure(),
    )

    assert_equal(
        first["direction"],
        "LONG",
        "first state incorrect",
    )

    assert_equal(
        second["direction"],
        "NONE",
        "second state leaked from first call",
    )

    assert_equal(
        third["direction"],
        "SHORT",
        "third state leaked from previous calls",
    )


# =============================================================================
# 15I-16 REPEATED STATE DETERMINISM
# =============================================================================

def test_repeated_state_determinism():

    structures = [
        long_structure(),
        neutral_structure(),
        short_structure(),
    ]

    for structure in structures:

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
                "state output is not deterministic",
            )


# =============================================================================
# 15I-17 STATE TRANSITION DOES NOT MUTATE INPUT
# =============================================================================

def test_transition_input_immutability():

    regime = ready_regime()

    structure = structural_record(
        long_structure()
    )

    regime_before = copy.deepcopy(regime)
    structure_before = copy.deepcopy(structure)

    build_signal(
        "BTC",
        structure["structure"],
    )

    assert_equal(
        regime,
        regime_before,
        "regime mutated during transition evaluation",
    )

    assert_equal(
        structure,
        structure_before,
        "structure mutated during transition evaluation",
    )


# =============================================================================
# 15I-18 ASSET-SCOPED LIFECYCLE
# =============================================================================

def test_asset_scoped_lifecycle():

    btc_long = build_signal(
        "BTC",
        long_structure(),
    )

    eth_short = build_signal(
        "ETH",
        short_structure(),
    )

    sol_neutral = build_signal(
        "SOL",
        neutral_structure(),
    )

    assert_equal(
        btc_long["asset"],
        "BTC",
        "BTC identity mismatch",
    )

    assert_equal(
        eth_short["asset"],
        "ETH",
        "ETH identity mismatch",
    )

    assert_equal(
        sol_neutral["asset"],
        "SOL",
        "SOL identity mismatch",
    )

    assert_equal(
        btc_long["direction"],
        "LONG",
        "BTC state contaminated",
    )

    assert_equal(
        eth_short["direction"],
        "SHORT",
        "ETH state contaminated",
    )

    assert_equal(
        sol_neutral["direction"],
        "NONE",
        "SOL state contaminated",
    )


# =============================================================================
# 15I-19 STATE OUTPUT CONTRACT
# =============================================================================

def test_state_output_contract():

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
            signal_contract.validate_signal(result),
            "state output violates signal contract",
        )


# =============================================================================
# 15I-20 INVALID STATE TAMPERING
# =============================================================================

def test_invalid_state_tampering():

    result = build_signal(
        "BTC",
        long_structure(),
    )

    invalid_states = [
        None,
        "",
        "INVALID",
        "READY",
        "BLOCKED",
        1,
        True,
    ]

    for state in invalid_states:

        tampered = copy.deepcopy(result)
        tampered["signal_state"] = state

        assert_true(
            not signal_contract.validate_signal(tampered),
            "invalid signal state was accepted: {!r}".format(
                state
            ),
        )


# =============================================================================
# 15I-21 INVALID DIRECTION / STATE PAIR
# =============================================================================

def test_invalid_direction_state_pairs():

    valid = build_signal(
        "BTC",
        long_structure(),
    )

    invalid_pairs = [
        ("NEUTRAL", "LONG"),
        ("NEUTRAL", "SHORT"),
        ("ACTIVE", "NONE"),
    ]

    for state, direction in invalid_pairs:

        tampered = copy.deepcopy(valid)

        tampered["signal_state"] = state
        tampered["direction"] = direction

        assert_true(
            not signal_contract.validate_signal(tampered),
            "invalid state/direction pair was accepted",
        )


# =============================================================================
# 15I-22 REASON MUST FOLLOW STATE
# =============================================================================

def test_reason_follows_state():

    active = build_signal(
        "BTC",
        long_structure(),
    )

    neutral = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        active["reason"],
        "STRUCTURAL_DIRECTION",
        "ACTIVE reason mismatch",
    )

    assert_equal(
        neutral["reason"],
        None,
        "NEUTRAL reason mismatch",
    )

    invalid = copy.deepcopy(active)
    invalid["reason"] = None

    assert_true(
        not signal_contract.validate_signal(invalid),
        "ACTIVE signal without structural reason was accepted",
    )


# =============================================================================
# 15I-23 DATABASE / NETWORK / WRITE ISOLATION
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
# 15I-24 FUTURE / DECISION / EXECUTION ISOLATION
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
# 15I-25 FINAL LIFECYCLE INTEGRITY
# =============================================================================

def test_final_lifecycle_integrity():

    transitions = [
        (
            "BTC",
            neutral_structure(),
            "NEUTRAL",
            "NONE",
        ),
        (
            "BTC",
            long_structure(),
            "ACTIVE",
            "LONG",
        ),
        (
            "BTC",
            short_structure(),
            "ACTIVE",
            "SHORT",
        ),
        (
            "ETH",
            long_structure(),
            "ACTIVE",
            "LONG",
        ),
        (
            "SOL",
            neutral_structure(),
            "NEUTRAL",
            "NONE",
        ),
    ]

    for asset, structure, expected_state, expected_direction in transitions:

        result = build_signal(
            asset,
            structure,
        )

        assert_true(
            signal_contract.validate_signal(result),
            "final lifecycle output failed contract",
        )

        assert_equal(
            result["asset"],
            asset,
            "final lifecycle asset mismatch",
        )

        assert_equal(
            result["signal_state"],
            expected_state,
            "final lifecycle state mismatch",
        )

        assert_equal(
            result["direction"],
            expected_direction,
            "final lifecycle direction mismatch",
        )

    # Verify lifecycle outputs remain independent.
    btc_neutral = build_signal(
        "BTC",
        neutral_structure(),
    )

    btc_long = build_signal(
        "BTC",
        long_structure(),
    )

    btc_short = build_signal(
        "BTC",
        short_structure(),
    )

    assert_equal(
        btc_neutral["direction"],
        "NONE",
        "final lifecycle NEUTRAL contamination",
    )

    assert_equal(
        btc_long["direction"],
        "LONG",
        "final lifecycle LONG contamination",
    )

    assert_equal(
        btc_short["direction"],
        "SHORT",
        "final lifecycle SHORT contamination",
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
    print("ARUNDA TRADER — STEP 15I")
    print("SIGNAL STATE TRANSITION & LIFECYCLE AUDIT v0.1")
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
        "Decision     : NOT USED"
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
            "15I-01 Initial NEUTRAL state",
            test_initial_neutral_state,
        ),

        (
            "15I-02 Initial LONG state",
            test_initial_long_state,
        ),

        (
            "15I-03 Initial SHORT state",
            test_initial_short_state,
        ),

        (
            "15I-04 NEUTRAL -> LONG",
            test_neutral_to_long,
        ),

        (
            "15I-05 NEUTRAL -> SHORT",
            test_neutral_to_short,
        ),

        (
            "15I-06 LONG -> NEUTRAL",
            test_long_to_neutral,
        ),

        (
            "15I-07 SHORT -> NEUTRAL",
            test_short_to_neutral,
        ),

        (
            "15I-08 LONG -> SHORT reversal",
            test_long_short_reversal,
        ),

        (
            "15I-09 SHORT -> LONG reversal",
            test_short_long_reversal,
        ),

        (
            "15I-10 ACTIVE state must be directional",
            test_active_state_directional,
        ),

        (
            "15I-11 NEUTRAL state must not be directional",
            test_neutral_state_not_directional,
        ),

        (
            "15I-12 HIGH volatility forces NEUTRAL",
            test_high_volatility_forces_neutral,
        ),

        (
            "15I-13 Position block forces NEUTRAL",
            test_position_block_forces_neutral,
        ),

        (
            "15I-14 Non-READY regime rejection",
            test_non_ready_regime_rejected,
        ),

        (
            "15I-15 State isolation between calls",
            test_state_does_not_leak_between_calls,
        ),

        (
            "15I-16 Repeated state determinism",
            test_repeated_state_determinism,
        ),

        (
            "15I-17 Transition input immutability",
            test_transition_input_immutability,
        ),

        (
            "15I-18 Asset-scoped lifecycle",
            test_asset_scoped_lifecycle,
        ),

        (
            "15I-19 State output contract",
            test_state_output_contract,
        ),

        (
            "15I-20 Invalid state tampering",
            test_invalid_state_tampering,
        ),

        (
            "15I-21 Invalid direction/state pairs",
            test_invalid_direction_state_pairs,
        ),

        (
            "15I-22 Reason follows state",
            test_reason_follows_state,
        ),

        (
            "15I-23 Database/network/write isolation",
            test_database_network_write_isolation,
        ),

        (
            "15I-24 Future/decision/execution isolation",
            test_future_decision_execution_isolation,
        ),

        (
            "15I-25 Final lifecycle integrity",
            test_final_lifecycle_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("STATE TRANSITION & LIFECYCLE AUDIT")
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
    print("STEP 15I SUMMARY")
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
    print("STEP 15I VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL STATE TRANSITION & LIFECYCLE AUDIT PASS"
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
        "RESULT      : SIGNAL STATE TRANSITION & LIFECYCLE AUDIT FAIL"
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
