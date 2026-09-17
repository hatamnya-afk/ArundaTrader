# =============================================================================
# ARUNDA TRADER — STEP 15L
# SIGNAL CONTRACT IMMUTABILITY & BOUNDARY HARDENING AUDIT v0.1
#
# MODE
# ----
# READ ONLY / AUDIT ONLY
#
# IMPORTANT
# ---------
# This audit does NOT modify production files.
# =============================================================================

import ast
import copy
import os

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

EXPECTED_FIELDS = {
    "asset",
    "timestamp",
    "signal_state",
    "direction",
    "confidence",
    "reason",
}

EXPECTED_STATES = {
    "NEUTRAL",
    "ACTIVE",
}

EXPECTED_DIRECTIONS = {
    "NONE",
    "LONG",
    "SHORT",
}


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
        print("{:<54} : PASS".format(name))
        return True

    except Exception as error:
        print("{:<54} : FAIL".format(name))
        print(
            "  ERROR :",
            type(error).__name__,
            str(error),
        )
        return False


# =============================================================================
# FIXTURES
# =============================================================================

def valid_neutral_signal(asset="BTC"):
    return {
        "asset": asset,
        "timestamp": None,
        "signal_state": "NEUTRAL",
        "direction": "NONE",
        "confidence": None,
        "reason": None,
    }


def valid_active_long(asset="BTC"):
    return {
        "asset": asset,
        "timestamp": None,
        "signal_state": "ACTIVE",
        "direction": "LONG",
        "confidence": None,
        "reason": "STRUCTURAL_DIRECTION",
    }


def valid_active_short(asset="BTC"):
    return {
        "asset": asset,
        "timestamp": None,
        "signal_state": "ACTIVE",
        "direction": "SHORT",
        "confidence": None,
        "reason": "STRUCTURAL_DIRECTION",
    }


# =============================================================================
# 15L-01 BASELINE CONTRACT VALIDITY
# =============================================================================

def test_baseline_contract_validity():

    contract = signal_contract.build_signal_contract()

    assert_true(
        signal_contract.validate_signal_contract(contract),
        "baseline contract is invalid",
    )


# =============================================================================
# 15L-02 EXPECTED ASSET COUNT
# =============================================================================

def test_expected_asset_count():

    assert_equal(
        len(signal_contract.EXPECTED_ASSETS),
        len(EXPECTED_ASSETS),
        "unexpected asset count",
    )


# =============================================================================
# 15L-03 EXPECTED ASSET SET
# =============================================================================

def test_expected_asset_set():

    assert_equal(
        set(signal_contract.EXPECTED_ASSETS),
        set(EXPECTED_ASSETS),
        "unexpected asset set",
    )


# =============================================================================
# 15L-04 SIGNAL FIELD SET HARDENING
# =============================================================================

def test_signal_field_set_hardening():

    assert_equal(
        set(signal_contract.SIGNAL_FIELDS),
        EXPECTED_FIELDS,
        "signal field set mismatch",
    )


# =============================================================================
# 15L-05 SIGNAL STATE ENUM HARDENING
# =============================================================================

def test_signal_state_enum_hardening():

    assert_equal(
        set(signal_contract.SIGNAL_STATES),
        EXPECTED_STATES,
        "signal state enum mismatch",
    )


# =============================================================================
# 15L-06 DIRECTION ENUM HARDENING
# =============================================================================

def test_direction_enum_hardening():

    assert_equal(
        set(signal_contract.DIRECTIONS),
        EXPECTED_DIRECTIONS,
        "direction enum mismatch",
    )


# =============================================================================
# 15L-07 ASSET IDENTITY HARDENING
# =============================================================================

def test_asset_identity_hardening():

    contract = signal_contract.build_signal_contract()

    for asset in EXPECTED_ASSETS:

        assert_true(
            asset in contract,
            "missing contract asset: {}".format(asset),
        )

        assert_equal(
            contract[asset]["asset"],
            asset,
            "asset identity mismatch: {}".format(asset),
        )


# =============================================================================
# 15L-08 EMPTY SIGNAL SEMANTIC HARDENING
# =============================================================================

def test_empty_signal_semantic_hardening():

    for asset in EXPECTED_ASSETS:

        signal = signal_contract.build_empty_signal(asset)

        assert_true(
            signal_contract.validate_signal(signal),
            "empty signal invalid for {}".format(asset),
        )

        assert_equal(
            signal["signal_state"],
            "NEUTRAL",
            "empty signal state must be NEUTRAL",
        )

        assert_equal(
            signal["direction"],
            "NONE",
            "empty signal direction must be NONE",
        )

        assert_equal(
            signal["reason"],
            None,
            "empty signal reason must be None",
        )


# =============================================================================
# 15L-09 UNKNOWN ASSET REJECTION
# =============================================================================

def test_unknown_asset_rejection():

    invalid_assets = [
        "UNKNOWN",
        "",
        "BTC ",
        "btc",
        "ETHEREUM",
    ]

    for asset in invalid_assets:

        assert_raises(
            RuntimeError,
            lambda asset=asset:
                signal_contract.build_empty_signal(asset),
            "unknown asset was not rejected",
        )


# =============================================================================
# 15L-10 MISSING FIELD REJECTION
# =============================================================================

def test_missing_field_rejection():

    base = valid_active_long()

    for field in EXPECTED_FIELDS:

        malformed = copy.deepcopy(base)
        del malformed[field]

        assert_true(
            not signal_contract.validate_signal(malformed),
            "missing field accepted: {}".format(field),
        )


# =============================================================================
# 15L-11 EXTRA FIELD REJECTION
# =============================================================================

def test_extra_field_rejection():

    signal = valid_active_long()

    signal["unexpected"] = "ATTACK"

    assert_true(
        not signal_contract.validate_signal(signal),
        "extra field accepted",
    )


# =============================================================================
# 15L-12 DIRECTION SEMANTIC HARDENING
# =============================================================================

def test_direction_semantic_hardening():

    invalid_cases = [
        {
            "signal_state": "NEUTRAL",
            "direction": "LONG",
        },
        {
            "signal_state": "NEUTRAL",
            "direction": "SHORT",
        },
        {
            "signal_state": "ACTIVE",
            "direction": "NONE",
        },
    ]

    for case in invalid_cases:

        signal = valid_neutral_signal()

        signal["signal_state"] = case["signal_state"]
        signal["direction"] = case["direction"]

        if case["signal_state"] == "ACTIVE":
            signal["reason"] = "STRUCTURAL_DIRECTION"
        else:
            signal["reason"] = None

        assert_true(
            not signal_contract.validate_signal(signal),
            "semantically invalid direction accepted",
        )


# =============================================================================
# 15L-13 STATE SEMANTIC HARDENING
# =============================================================================

def test_state_semantic_hardening():

    invalid_states = [
        "INVALID",
        "UNKNOWN",
        "",
        None,
        1,
        True,
    ]

    for state in invalid_states:

        signal = valid_neutral_signal()
        signal["signal_state"] = state

        assert_true(
            not signal_contract.validate_signal(signal),
            "invalid state accepted: {!r}".format(state),
        )


# =============================================================================
# 15L-14 REASON SEMANTIC HARDENING
# =============================================================================

def test_reason_semantic_hardening():

    signal = valid_active_long()

    invalid_reasons = [
        None,
        "",
        "WRONG",
        "DIRECTION",
        "STRUCTURAL",
    ]

    for reason in invalid_reasons:

        malformed = copy.deepcopy(signal)
        malformed["reason"] = reason

        assert_true(
            not signal_contract.validate_signal(malformed),
            "invalid ACTIVE reason accepted: {!r}".format(reason),
        )


# =============================================================================
# 15L-15 CONFIDENCE BOUNDARY HARDENING
# =============================================================================

def test_confidence_boundary_hardening():

    valid_values = [
        0.0,
        0.5,
        1.0,
    ]

    for value in valid_values:

        signal = valid_active_long()
        signal["confidence"] = value

        assert_true(
            signal_contract.validate_signal(signal),
            "valid confidence rejected: {!r}".format(value),
        )

    invalid_values = [
        -0.0001,
        1.0001,
        "0.5",
        [],
        {},
        True,
        False,
    ]

    for value in invalid_values:

        signal = valid_active_long()
        signal["confidence"] = value

        assert_true(
            not signal_contract.validate_signal(signal),
            "invalid confidence accepted: {!r}".format(value),
        )


# =============================================================================
# 15L-16 TIMESTAMP TYPE HARDENING
# =============================================================================

def test_timestamp_type_hardening():

    invalid_values = [
        1,
        1.5,
        [],
        {},
        True,
    ]

    for value in invalid_values:

        signal = valid_active_long()
        signal["timestamp"] = value

        assert_true(
            not signal_contract.validate_signal(signal),
            "invalid timestamp type accepted",
        )


# =============================================================================
# 15L-17 REASON TYPE HARDENING
# =============================================================================

def test_reason_type_hardening():

    invalid_values = [
        1,
        1.5,
        [],
        {},
        True,
    ]

    for value in invalid_values:

        signal = valid_active_long()
        signal["reason"] = value

        assert_true(
            not signal_contract.validate_signal(signal),
            "invalid reason type accepted",
        )


# =============================================================================
# 15L-18 CONTRACT INSTANCE ISOLATION
# =============================================================================

def test_contract_instance_isolation():

    first = signal_contract.build_signal_contract()
    second = signal_contract.build_signal_contract()

    assert_true(
        first is not second,
        "contract instances share outer identity",
    )

    first["BTC"]["direction"] = "LONG"

    assert_equal(
        second["BTC"]["direction"],
        "NONE",
        "contract instances share mutable signal state",
    )


# =============================================================================
# 15L-19 CONTRACT INSTANCE REBUILD
# =============================================================================

def test_contract_instance_rebuild():

    first = signal_contract.build_signal_contract()

    first["BTC"]["direction"] = "LONG"

    second = signal_contract.build_signal_contract()

    assert_equal(
        second["BTC"]["direction"],
        "NONE",
        "rebuilding contract retained previous mutation",
    )


# =============================================================================
# 15L-20 EMPTY SIGNAL ISOLATION
# =============================================================================

def test_empty_signal_isolation():

    first = signal_contract.build_empty_signal("BTC")
    second = signal_contract.build_empty_signal("BTC")

    assert_true(
        first is not second,
        "empty signal instances share identity",
    )

    first["direction"] = "LONG"

    assert_equal(
        second["direction"],
        "NONE",
        "empty signal instances share mutable state",
    )


# =============================================================================
# 15L-21 INPUT IMMUTABILITY
# =============================================================================

def test_input_immutability():

    signal = valid_active_long()
    before = copy.deepcopy(signal)

    signal_contract.validate_signal(signal)

    assert_equal(
        signal,
        before,
        "validate_signal mutated input",
    )


# =============================================================================
# 15L-22 CONTRACT VALIDATOR IMMUTABILITY
# =============================================================================

def test_contract_validator_immutability():

    contract = signal_contract.build_signal_contract()
    before = copy.deepcopy(contract)

    signal_contract.validate_signal_contract(contract)

    assert_equal(
        contract,
        before,
        "validate_signal_contract mutated input",
    )


# =============================================================================
# 15L-23 PUBLIC API REPRODUCIBILITY
# =============================================================================

def test_public_api_reproducibility():

    first = signal_contract.load_signal_contract()
    second = signal_contract.load_signal_contract()

    assert_equal(
        first,
        second,
        "public contract API is not reproducible",
    )


# =============================================================================
# 15L-24 PRODUCTION DEPENDENCY ISOLATION
# =============================================================================

def test_production_dependency_isolation():

    with open(
        signal_contract.__file__,
        "r",
        encoding="utf-8",
    ) as file:

        tree = ast.parse(
            file.read(),
            filename=signal_contract.__file__,
        )

    forbidden = {
        "sqlite3",
        "sqlite",
        "requests",
        "urllib",
        "socket",
        "http",
        "connect",
        "cursor",
        "execute",
        "executemany",
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "DROP",
        "write",
        "writelines",
        "to_sql",
        "to_csv",
        "prediction",
        "predict",
        "forecast",
        "decision",
        "buy",
        "sell",
        "order",
        "place_order",
        "score",
        "scoring",
    }

    names = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Name):
            names.add(node.id)

        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    overlap = names & forbidden

    assert_true(
        not overlap,
        "forbidden production dependency detected: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15L-25 FINAL CONTRACT BOUNDARY INTEGRITY
# =============================================================================

def test_final_contract_boundary_integrity():

    contract = signal_contract.load_signal_contract()

    assert_true(
        signal_contract.validate_signal_contract(contract),
        "final contract validation failed",
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

        signal = contract[asset]

        assert_equal(
            signal["asset"],
            asset,
            "final asset identity mismatch",
        )

        assert_equal(
            signal["signal_state"],
            "NEUTRAL",
            "final state mismatch",
        )

        assert_equal(
            signal["direction"],
            "NONE",
            "final direction mismatch",
        )

        assert_equal(
            signal["timestamp"],
            None,
            "final timestamp mismatch",
        )

        assert_equal(
            signal["confidence"],
            None,
            "final confidence mismatch",
        )

        assert_equal(
            signal["reason"],
            None,
            "final reason mismatch",
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15L")
    print("SIGNAL CONTRACT IMMUTABILITY & BOUNDARY HARDENING AUDIT v0.1")
    print("=" * 78)

    print("Mode        : READ ONLY / AUDIT ONLY")
    print("Database    : NOT USED")
    print("Writes      : NONE")
    print("Scoring     : NOT USED")
    print("Prediction  : NOT USED")
    print("Decision    : NOT USED")
    print("Execution   : NOT USED")
    print()

    print("Production file:")
    print("  - signal_contract.py")

    print("=" * 78)
    print()

    tests = [
        ("15L-01 Baseline contract validity", test_baseline_contract_validity),
        ("15L-02 Expected asset count", test_expected_asset_count),
        ("15L-03 Expected asset set", test_expected_asset_set),
        ("15L-04 Signal field set hardening", test_signal_field_set_hardening),
        ("15L-05 Signal state enum hardening", test_signal_state_enum_hardening),
        ("15L-06 Direction enum hardening", test_direction_enum_hardening),
        ("15L-07 Asset identity hardening", test_asset_identity_hardening),
        ("15L-08 Empty signal semantic hardening", test_empty_signal_semantic_hardening),
        ("15L-09 Unknown asset rejection", test_unknown_asset_rejection),
        ("15L-10 Missing field rejection", test_missing_field_rejection),
        ("15L-11 Extra field rejection", test_extra_field_rejection),
        ("15L-12 Direction semantic hardening", test_direction_semantic_hardening),
        ("15L-13 State semantic hardening", test_state_semantic_hardening),
        ("15L-14 Reason semantic hardening", test_reason_semantic_hardening),
        ("15L-15 Confidence boundary hardening", test_confidence_boundary_hardening),
        ("15L-16 Timestamp type hardening", test_timestamp_type_hardening),
        ("15L-17 Reason type hardening", test_reason_type_hardening),
        ("15L-18 Contract instance isolation", test_contract_instance_isolation),
        ("15L-19 Contract instance rebuild", test_contract_instance_rebuild),
        ("15L-20 Empty signal isolation", test_empty_signal_isolation),
        ("15L-21 Input immutability", test_input_immutability),
        ("15L-22 Contract validator immutability", test_contract_validator_immutability),
        ("15L-23 Public API reproducibility", test_public_api_reproducibility),
        ("15L-24 Production dependency isolation", test_production_dependency_isolation),
        ("15L-25 Final contract boundary integrity", test_final_contract_boundary_integrity),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("CONTRACT IMMUTABILITY / BOUNDARY HARDENING AUDIT")
    print("=" * 78)

    for name, function in tests:

        if run_test(name, function):
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 78)
    print("STEP 15L SUMMARY")
    print("=" * 78)

    print("Total Tests : {}".format(len(tests)))
    print("PASS        : {}".format(passed))
    print("FAIL        : {}".format(failed))

    print()
    print("=" * 78)
    print("STEP 15L VERDICT")
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL CONTRACT IMMUTABILITY & BOUNDARY HARDENING AUDIT PASS"
        )

        print(
            "STATUS      : READY FOR NEXT SIGNAL STEP"
        )

        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Scoring      : NOT USED")
        print("Prediction   : NOT USED")
        print("Decision     : NOT USED")
        print("Execution    : NOT USED")
        print("Look-Ahead   : PROTECTED")
        print("=" * 78)

        return 0

    print(
        "RESULT      : SIGNAL CONTRACT IMMUTABILITY & BOUNDARY HARDENING AUDIT FAIL"
    )

    print(
        "STATUS      : REPAIR REQUIRED"
    )

    print()
    print("IMPORTANT:")
    print("Production Signal files were NOT modified.")
    print("=" * 78)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
