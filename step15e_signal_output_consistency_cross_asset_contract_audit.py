# =============================================================================
# ARUNDA TRADER
# STEP 15E — SIGNAL OUTPUT CONSISTENCY & CROSS-ASSET CONTRACT AUDIT v0.1
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
# PRODUCTION FILES
# ----------------
# signal_logic.py
# signal_engine.py
# signal_contract.py
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
# EXPECTED ASSETS
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
# BUILD SIGNAL
# =============================================================================

def build_signal(asset, structure):

    return signal_engine.build_signal(
        asset,
        ready_regime(),
        structural_record(structure),
    )


# =============================================================================
# BUILD FULL SIGNAL SET
# =============================================================================

def build_signal_set():

    signals = {}

    for asset in EXPECTED_ASSETS:

        signals[asset] = build_signal(
            asset,
            long_structure(),
        )

    return signals


# =============================================================================
# 15E-01 OUTPUT SCHEMA CONSISTENCY
# =============================================================================

def test_output_schema_consistency():

    signals = build_signal_set()

    assert_equal(
        set(signals.keys()),
        set(EXPECTED_ASSETS),
        "signal asset set changed",
    )

    for asset in EXPECTED_ASSETS:

        signal = signals[asset]

        assert_true(
            isinstance(signal, dict),
            "signal output must be dict: {}".format(asset),
        )

        assert_equal(
            set(signal.keys()),
            EXPECTED_SIGNAL_FIELDS,
            "signal field set changed: {}".format(asset),
        )


# =============================================================================
# 15E-02 CROSS-ASSET IDENTITY CONSISTENCY
# =============================================================================

def test_cross_asset_identity():

    signals = build_signal_set()

    for asset in EXPECTED_ASSETS:

        assert_equal(
            signals[asset]["asset"],
            asset,
            "asset identity mismatch",
        )


# =============================================================================
# 15E-03 CROSS-ASSET SIGNAL STATE CONSISTENCY
# =============================================================================

def test_cross_asset_state_consistency():

    signals = build_signal_set()

    for asset in EXPECTED_ASSETS:

        signal = signals[asset]

        assert_equal(
            signal["signal_state"],
            "ACTIVE",
            "unexpected state for {}".format(asset),
        )

        assert_equal(
            signal["direction"],
            "LONG",
            "unexpected direction for {}".format(asset),
        )

        assert_equal(
            signal["reason"],
            "STRUCTURAL_DIRECTION",
            "unexpected reason for {}".format(asset),
        )


# =============================================================================
# 15E-04 CROSS-ASSET ISOLATION
# =============================================================================

def test_cross_asset_isolation():

    structures = {}

    for asset in EXPECTED_ASSETS:

        structures[asset] = long_structure()

    structures["BTC"] = short_structure()

    results = {}

    for asset in EXPECTED_ASSETS:

        results[asset] = build_signal(
            asset,
            structures[asset],
        )

    assert_equal(
        results["BTC"]["direction"],
        "SHORT",
        "BTC did not receive its own structure",
    )

    for asset in EXPECTED_ASSETS:

        if asset == "BTC":

            continue

        assert_equal(
            results[asset]["direction"],
            "LONG",
            "cross-asset contamination detected in {}".format(
                asset
            ),
        )


# =============================================================================
# 15E-05 ORDER INDEPENDENCE
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

    for asset in EXPECTED_ASSETS:

        assert_equal(
            forward[asset],
            reverse[asset],
            "output changed with asset processing order",
        )


# =============================================================================
# 15E-06 REPEATED AGGREGATE CONSISTENCY
# =============================================================================

def test_repeated_aggregate_consistency():

    outputs = []

    for _ in range(5):

        outputs.append(
            build_signal_set()
        )

    for output in outputs[1:]:

        assert_equal(
            output,
            outputs[0],
            "aggregate signal output is not deterministic",
        )


# =============================================================================
# 15E-07 ACTIVE SEMANTIC CONSISTENCY
# =============================================================================

def test_active_semantic_consistency():

    structures = [
        long_structure(),
        short_structure(),
    ]

    for structure in structures:

        signal = build_signal(
            "BTC",
            structure,
        )

        assert_equal(
            signal["signal_state"],
            "ACTIVE",
            "directional signal must be ACTIVE",
        )

        assert_true(
            signal["direction"] in {
                "LONG",
                "SHORT",
            },
            "ACTIVE signal has invalid direction",
        )

        assert_equal(
            signal["reason"],
            "STRUCTURAL_DIRECTION",
            "ACTIVE reason mismatch",
        )


# =============================================================================
# 15E-08 NEUTRAL SEMANTIC CONSISTENCY
# =============================================================================

def test_neutral_semantic_consistency():

    signal = build_signal(
        "BTC",
        neutral_structure(),
    )

    assert_equal(
        signal["signal_state"],
        "NEUTRAL",
        "neutral structure did not produce NEUTRAL",
    )

    assert_equal(
        signal["direction"],
        "NONE",
        "NEUTRAL signal must have NONE direction",
    )

    assert_equal(
        signal["reason"],
        None,
        "NEUTRAL signal must have no reason",
    )


# =============================================================================
# 15E-09 HIGH VOLATILITY AGGREGATE BLOCK
# =============================================================================

def test_high_volatility_aggregate_block():

    for asset in EXPECTED_ASSETS:

        structure = long_structure()

        structure["volatility"] = "HIGH"

        signal = build_signal(
            asset,
            structure,
        )

        assert_equal(
            signal["signal_state"],
            "NEUTRAL",
            "HIGH volatility must produce NEUTRAL",
        )

        assert_equal(
            signal["direction"],
            "NONE",
            "HIGH volatility must block direction",
        )

        assert_equal(
            signal["reason"],
            None,
            "blocked signal must have no reason",
        )


# =============================================================================
# 15E-10 POSITION BOUNDARY CONSISTENCY
# =============================================================================

def test_position_boundary_consistency():

    for asset in EXPECTED_ASSETS:

        long_case = long_structure()
        long_case["position"] = "LOWER"

        long_signal = build_signal(
            asset,
            long_case,
        )

        assert_equal(
            long_signal["direction"],
            "NONE",
            "LOWER position must block LONG",
        )

        short_case = short_structure()
        short_case["position"] = "UPPER"

        short_signal = build_signal(
            asset,
            short_case,
        )

        assert_equal(
            short_signal["direction"],
            "NONE",
            "UPPER position must block SHORT",
        )


# =============================================================================
# 15E-11 OUTPUT CONTRACT COMPATIBILITY
# =============================================================================

def test_output_contract_compatibility():

    signals = build_signal_set()

    assert_true(
        signal_contract.validate_signal_contract(
            signals
        ),
        "signal engine output rejected by signal contract",
    )


# =============================================================================
# 15E-12 OUTPUT INPUT IMMUTABILITY
# =============================================================================

def test_output_input_immutability():

    for asset in EXPECTED_ASSETS:

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
            asset,
            regime,
            structure,
        )

        assert_equal(
            regime,
            regime_before,
            "regime input mutated: {}".format(asset),
        )

        assert_equal(
            structure,
            structure_before,
            "structure input mutated: {}".format(asset),
        )


# =============================================================================
# 15E-13 OUTPUT METADATA ISOLATION
# =============================================================================

def test_output_metadata_isolation():

    signals = build_signal_set()

    for asset in EXPECTED_ASSETS:

        signal = signals[asset]

        assert_equal(
            signal["timestamp"],
            None,
            "timestamp must remain isolated",
        )

        assert_equal(
            signal["confidence"],
            None,
            "confidence must remain isolated",
        )


# =============================================================================
# 15E-14 ASSET COUNT INTEGRITY
# =============================================================================

def test_asset_count_integrity():

    signals = build_signal_set()

    assert_equal(
        len(signals),
        len(EXPECTED_ASSETS),
        "unexpected signal asset count",
    )


# =============================================================================
# 15E-15 MISSING ASSET REJECTION
# =============================================================================

def test_missing_asset_rejection():

    signals = build_signal_set()

    removed_asset = EXPECTED_ASSETS[-1]

    del signals[removed_asset]

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted signal set with missing asset",
    )


# =============================================================================
# 15E-16 EXTRA ASSET REJECTION
# =============================================================================

def test_extra_asset_rejection():

    signals = build_signal_set()

    signals["FAKE"] = {
        "asset": "FAKE",
        "timestamp": None,
        "signal_state": "NEUTRAL",
        "direction": "NONE",
        "confidence": None,
        "reason": None,
    }

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted signal set with extra asset",
    )


# =============================================================================
# 15E-17 ASSET SIGNAL SWAP REJECTION
# =============================================================================

def test_asset_signal_swap_rejection():

    signals = build_signal_set()

    signals["BTC"] = copy.deepcopy(
        signals["ETH"]
    )

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted cross-asset signal swap",
    )


# =============================================================================
# 15E-18 SIGNAL FIELD TAMPERING REJECTION
# =============================================================================

def test_signal_field_tampering_rejection():

    signals = build_signal_set()

    signal = copy.deepcopy(
        signals["BTC"]
    )

    signal["unexpected"] = "BAD"

    signals["BTC"] = signal

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted unexpected signal field",
    )


# =============================================================================
# 15E-19 SIGNAL DIRECTION TAMPERING REJECTION
# =============================================================================

def test_signal_direction_tampering_rejection():

    signals = build_signal_set()

    signal = copy.deepcopy(
        signals["BTC"]
    )

    # IMPORTANT:
    # ACTIVE + SHORT is a valid semantic combination.
    # Therefore changing LONG -> SHORT is NOT contract corruption.
    #
    # The actual invalid semantic combination is:
    #
    # ACTIVE + NONE
    #
    # This must be rejected by the signal contract.

    signal["direction"] = "NONE"

    signals["BTC"] = signal

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted semantically invalid ACTIVE direction",
    )


# =============================================================================
# 15E-20 SIGNAL STATE TAMPERING REJECTION
# =============================================================================

def test_signal_state_tampering_rejection():

    signals = build_signal_set()

    signal = copy.deepcopy(
        signals["BTC"]
    )

    # ACTIVE + LONG is valid.
    # Changing state to NEUTRAL while keeping LONG
    # creates an invalid semantic combination.

    signal["signal_state"] = "NEUTRAL"

    signals["BTC"] = signal

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted semantically invalid state",
    )


# =============================================================================
# 15E-21 REASON TAMPERING REJECTION
# =============================================================================

def test_reason_tampering_rejection():

    signals = build_signal_set()

    signal = copy.deepcopy(
        signals["BTC"]
    )

    # ACTIVE directional signals require
    # STRUCTURAL_DIRECTION as reason.

    signal["reason"] = None

    signals["BTC"] = signal

    assert_true(
        not signal_contract.validate_signal_contract(
            signals
        ),
        "contract accepted invalid ACTIVE reason",
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


def ast_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Name):

            names.add(node.id)

        elif isinstance(node, ast.Attribute):

            names.add(node.attr)

    return names


# =============================================================================
# 15E-22 PRODUCTION FILE INTEGRITY
# =============================================================================

def test_production_file_integrity():

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    for module in modules:

        assert_true(
            os.path.isfile(
                module.__file__
            ),
            "production file missing: {}".format(
                os.path.basename(
                    module.__file__
                )
            ),
        )

        tree = source_tree(module)

        assert_true(
            tree is not None,
            "production AST unavailable",
        )


# =============================================================================
# 15E-23 DATABASE / NETWORK ISOLATION
# =============================================================================

def test_database_network_isolation():

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
        "https",
        "socket",
        "urlopen",
    }

    for module in modules:

        tree = source_tree(module)

        names = ast_names(tree)

        overlap = forbidden & names

        assert_true(
            not overlap,
            "external dependency detected in {}: {}".format(
                os.path.basename(
                    module.__file__
                ),
                sorted(overlap),
            ),
        )


# =============================================================================
# 15E-24 FUTURE / DECISION INFORMATION ISOLATION
# =============================================================================

def test_future_decision_information_isolation():

    tree = source_tree(
        signal_engine
    )

    names = ast_names(tree)

    forbidden = {
        "prediction",
        "predict",
        "forecast",
        "future_price",
        "future_return",
        "decision",
        "decision_engine",
        "buy",
        "sell",
        "order",
        "place_order",
        "execute",
        "execution",
        "score",
        "scoring",
    }

    overlap = names & forbidden

    assert_true(
        not overlap,
        "future/decision information leaked into signal engine: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15E-25 FINAL AGGREGATE CONTRACT INTEGRITY
# =============================================================================

def test_final_aggregate_contract_integrity():

    signals = build_signal_set()

    assert_equal(
        set(signals.keys()),
        set(EXPECTED_ASSETS),
        "final asset universe mismatch",
    )

    for asset in EXPECTED_ASSETS:

        signal = signals[asset]

        assert_equal(
            signal["asset"],
            asset,
            "final asset identity mismatch",
        )

        assert_equal(
            set(signal.keys()),
            EXPECTED_SIGNAL_FIELDS,
            "final signal schema mismatch",
        )

    assert_true(
        signal_contract.validate_signal_contract(
            signals
        ),
        "final aggregate signal contract invalid",
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print(
        "ARUNDA TRADER — STEP 15E"
    )
    print(
        "SIGNAL OUTPUT CONSISTENCY & CROSS-ASSET CONTRACT AUDIT v0.1"
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
            "15E-01 Output schema consistency",
            test_output_schema_consistency,
        ),

        (
            "15E-02 Cross-asset identity consistency",
            test_cross_asset_identity,
        ),

        (
            "15E-03 Cross-asset signal state consistency",
            test_cross_asset_state_consistency,
        ),

        (
            "15E-04 Cross-asset isolation",
            test_cross_asset_isolation,
        ),

        (
            "15E-05 Order independence",
            test_order_independence,
        ),

        (
            "15E-06 Repeated aggregate consistency",
            test_repeated_aggregate_consistency,
        ),

        (
            "15E-07 ACTIVE semantic consistency",
            test_active_semantic_consistency,
        ),

        (
            "15E-08 NEUTRAL semantic consistency",
            test_neutral_semantic_consistency,
        ),

        (
            "15E-09 HIGH volatility aggregate block",
            test_high_volatility_aggregate_block,
        ),

        (
            "15E-10 Position boundary consistency",
            test_position_boundary_consistency,
        ),

        (
            "15E-11 Output contract compatibility",
            test_output_contract_compatibility,
        ),

        (
            "15E-12 Output input immutability",
            test_output_input_immutability,
        ),

        (
            "15E-13 Output metadata isolation",
            test_output_metadata_isolation,
        ),

        (
            "15E-14 Asset count integrity",
            test_asset_count_integrity,
        ),

        (
            "15E-15 Missing asset rejection",
            test_missing_asset_rejection,
        ),

        (
            "15E-16 Extra asset rejection",
            test_extra_asset_rejection,
        ),

        (
            "15E-17 Asset signal swap rejection",
            test_asset_signal_swap_rejection,
        ),

        (
            "15E-18 Signal field tampering rejection",
            test_signal_field_tampering_rejection,
        ),

        (
            "15E-19 Signal direction tampering rejection",
            test_signal_direction_tampering_rejection,
        ),

        (
            "15E-20 Signal state tampering rejection",
            test_signal_state_tampering_rejection,
        ),

        (
            "15E-21 Reason tampering rejection",
            test_reason_tampering_rejection,
        ),

        (
            "15E-22 Production file integrity",
            test_production_file_integrity,
        ),

        (
            "15E-23 Database / network isolation",
            test_database_network_isolation,
        ),

        (
            "15E-24 Future / decision information isolation",
            test_future_decision_information_isolation,
        ),

        (
            "15E-25 Final aggregate contract integrity",
            test_final_aggregate_contract_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print(
        "OUTPUT CONSISTENCY / CROSS-ASSET CONTRACT AUDIT"
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
        "STEP 15E SUMMARY"
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
        "STEP 15E VERDICT"
    )
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL OUTPUT CONSISTENCY & CROSS-ASSET CONTRACT AUDIT PASS"
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
        "RESULT      : SIGNAL OUTPUT CONSISTENCY & CROSS-ASSET CONTRACT AUDIT FAIL"
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