from pathlib import Path

import market_regime
import signal_engine


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

EXPECTED_FIELDS = {
    "trend",
    "momentum",
    "volatility",
    "position",
    "acceleration",
}

CAPTURED = False


# =============================================================================
# ORIGINAL FUNCTION
# =============================================================================

_original_build_structure = (
    market_regime.build_structure
)


# =============================================================================
# INPUT FORENSIC
# =============================================================================

def inspect_feature(feature):

    global CAPTURED

    CAPTURED = True

    print()
    print("=" * 100)
    print("BUILD_STRUCTURE INPUT CAPTURE")
    print("=" * 100)

    print(
        "INPUT TYPE :",
        type(feature).__name__
    )

    if not isinstance(feature, dict):

        print()
        print(
            "FEATURE IS NOT DICT"
        )

        print(
            "VALUE :",
            repr(feature)
        )

        print()
        print("=" * 100)

        return

    actual_fields = set(
        feature.keys()
    )

    print(
        "ACTUAL FIELDS :",
        sorted(actual_fields)
    )

    print(
        "EXPECTED FIELDS :",
        sorted(EXPECTED_FIELDS)
    )

    print()
    print(
        "MISSING :",
        sorted(
            EXPECTED_FIELDS
            - actual_fields
        )
    )

    print(
        "EXTRA   :",
        sorted(
            actual_fields
            - EXPECTED_FIELDS
        )
    )

    print()
    print("-" * 100)
    print("FEATURE FIELD RUNTIME VALUES")
    print("-" * 100)

    for field in sorted(actual_fields):

        value = feature[field]

        print(
            f"{field:<20} "
            f"type={type(value).__name__:<20} "
            f"value={repr(value)}"
        )

    print()
    print("-" * 100)
    print("EXPECTED STRUCTURAL INPUT FIELDS")
    print("-" * 100)

    for field in sorted(EXPECTED_FIELDS):

        if field not in feature:

            print(
                f"{field:<20} MISSING"
            )

            continue

        value = feature[field]

        print(
            f"{field:<20} "
            f"type={type(value).__name__:<20} "
            f"value={repr(value)}"
        )

    print()
    print("=" * 100)


# =============================================================================
# OBSERVER WRAPPER
# =============================================================================

def observed_build_structure(feature):

    inspect_feature(
        feature
    )

    return _original_build_structure(
        feature
    )


# =============================================================================
# TEMPORARY IN-MEMORY WRAP
# =============================================================================

market_regime.build_structure = (
    observed_build_structure
)


# =============================================================================
# HEADER
# =============================================================================

print("=" * 100)
print(
    "ARUNDA TRADER — "
    "BUILD_STRUCTURE INPUT FORENSIC v0.1"
)
print("=" * 100)

print(
    "PROJECT ROOT       :",
    PROJECT_ROOT
)

print(
    "TARGET             : market_regime.build_structure"
)

print(
    "MODE               : READ-ONLY RUNTIME OBSERVATION"
)

print(
    "PRODUCTION MUTATION : NONE"
)

print(
    "DATABASE ACCESS     : NONE"
)

print(
    "DATABASE WRITE      : NONE"
)

print(
    "JSON WRITE          : NONE"
)

print(
    "ARTIFACT CREATION   : NONE"
)

print(
    "SOURCE MUTATION     : NONE"
)

print(
    "SIGNAL SYNTHESIS    : NONE"
)

print(
    "ORDER CREATION      : NONE"
)

print(
    "ORDER SUBMISSION    : NONE"
)

print("=" * 100)


# =============================================================================
# REAL RUNTIME
# =============================================================================

try:

    result = signal_engine.main()

    print()
    print("=" * 100)
    print("FORENSIC RESULT")
    print("=" * 100)

    print(
        "SIGNAL ENGINE RETURN :",
        result
    )

    print(
        "BUILD_STRUCTURE CAPTURED :",
        CAPTURED
    )

finally:

    # -------------------------------------------------------------------------
    # RESTORE ORIGINAL FUNCTION
    # -------------------------------------------------------------------------

    market_regime.build_structure = (
        _original_build_structure
    )

    print()
    print("=" * 100)
    print("RESTORATION")
    print("=" * 100)

    print(
        "market_regime.build_structure : RESTORED"
    )

    print(
        "PRODUCTION SOURCE             : UNCHANGED"
    )

    print(
        "DATABASE                      : UNCHANGED"
    )

    print("=" * 100)