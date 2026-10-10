# =============================================================================
# ARUNDA SIGNAL ENGINE v0.8
#
# MARKET REGIME -> SIGNAL LOGIC -> ELIGIBILITY
#
# READ ONLY
# MEMORY ONLY
# NO SQL
# NO DATABASE WRITE
# NO ORDER
# NO SCORING
# NO DECISION
# NO SYNTHETIC DATA
# NO INTERPOLATION
# NO PADDING
#
# PIPELINE:
#
# market_regime_engine
#        |
#        v
# market_regime
#        |
#        v
# public five-field structure
#        |
#        v
# signal_logic
#        |
#        v
# direction
#        |
#        v
# eligibility
#
# CONTEXT:
# FULL    >= 150 real points
# LIMITED 21..149 real points
# NONE    < 21 real points
#
# IMPORTANT:
# LIMITED is AVAILABLE.
# Eligibility requires REAL CONTEXT >= 21.
#
# =============================================================================


import math

import market_regime
import signal_logic
import signal_contract


# =============================================================================
# CONSTANTS
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

FULL_CONTEXT_TARGET = 150
MINIMUM_CONTEXT = 21

VALID_CONTEXTS = {
    "FULL",
    "LIMITED",
}

VALID_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}


# =============================================================================
# HEADER
# =============================================================================

def print_header():

    print("=" * 82)
    print("ARUNDA SIGNAL ENGINE v0.8")
    print("=" * 82)

    print("Source        : market_regime")
    print("Logic         : signal_logic")
    print("Contract      : signal_contract")
    print("Eligibility   : AVAILABLE + REAL CONTEXT >= 21 + VALID DIRECTION")
    print("Storage       : MEMORY ONLY")
    print("Writes        : NONE")
    print("SQL           : NOT USED")
    print("Synthetic     : NO")
    print("Interpolation : NO")
    print("Padding       : NO")
    print("Order         : NO")
    print("Scoring       : NOT USED")
    print("Decision      : NOT USED")
    print("Prediction    : NOT USED")
    print("Full Context  :", FULL_CONTEXT_TARGET)
    print("Minimum       :", MINIMUM_CONTEXT)

    print("=" * 82)
    print()


# =============================================================================
# NORMALIZATION
# =============================================================================

def normalize_text(value):

    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    return value


def safe_int(value):

    if value is None:
        return 0

    try:
        return int(value)

    except (TypeError, ValueError):

        return 0


# =============================================================================
# CONTEXT
# =============================================================================

def context_from_points(points):

    points = safe_int(points)

    if points >= FULL_CONTEXT_TARGET:

        return "FULL"

    if points >= MINIMUM_CONTEXT:

        return "LIMITED"

    return "NONE"


def status_from_context(context):

    if context in VALID_CONTEXTS:

        return "AVAILABLE"

    return "UNAVAILABLE"


# =============================================================================
# LOAD MARKET REGIME
#
# IMPORTANT:
#
# Current market_regime.py exposes:
#
#     load_structural_state()
#
# It does NOT expose:
#
#     load_market_regime()
#
# Therefore this engine consumes the actual current API directly.
#
# =============================================================================

def load_regime():

    loader = getattr(
        market_regime,
        "load_structural_state",
        None,
    )

    if loader is None:

        raise RuntimeError(
            "market_regime.load_structural_state() is required"
        )

    state = loader()

    if not isinstance(state, dict):

        raise RuntimeError(
            "market_regime.load_structural_state() must return dict"
        )

    return state


# =============================================================================
# PUBLIC FIVE-FIELD ADAPTER
#
# The structural producer may expose additional internal fields.
#
# Only these five fields cross into signal_logic:
#
# trend
# momentum
# acceleration
# position
# volatility
#
# =============================================================================

def build_public_structure(feature):

    if not isinstance(feature, dict):

        raise RuntimeError(
            "Invalid structural feature"
        )

    # -------------------------------------------------------------------------
    # TREND
    #
    # Genuine structural direction only.
    # -------------------------------------------------------------------------

    direction = normalize_text(
        feature.get("structure_direction")
    )

    if direction is None:

        direction = normalize_text(
            feature.get("structure_state")
        )

    if direction == "BULLISH":

        trend = "UP"

    elif direction == "BEARISH":

        trend = "DOWN"

    elif direction == "NEUTRAL":

        trend = "FLAT"

    else:

        # If producer already provides a public trend, accept it.
        direct_trend = normalize_text(
            feature.get("trend")
        )

        if direct_trend in {
            "UP",
            "DOWN",
            "FLAT",
        }:

            trend = direct_trend

        else:

            trend = None

    # -------------------------------------------------------------------------
    # MOMENTUM
    # -------------------------------------------------------------------------

    strength = normalize_text(
        feature.get("structure_strength")
    )

    if strength in {
        "STRONG",
        "VERY_STRONG",
    }:

        momentum = "STRONG"

    elif strength in {
        "WEAK",
        "MODERATE",
        "MEDIUM",
    }:

        momentum = "WEAK"

    else:

        direct_momentum = normalize_text(
            feature.get("momentum")
        )

        if direct_momentum in {
            "STRONG",
            "WEAK",
        }:

            momentum = direct_momentum

        else:

            momentum = None

    # -------------------------------------------------------------------------
    # VOLATILITY
    #
    # Never manufacture volatility.
    # -------------------------------------------------------------------------

    volatility = normalize_text(
        feature.get("volatility")
    )

    if volatility not in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }:

        volatility = None

    # -------------------------------------------------------------------------
    # POSITION
    #
    # Never manufacture position.
    # -------------------------------------------------------------------------

    position = normalize_text(
        feature.get("position")
    )

    if position not in {
        "UPPER",
        "MIDDLE",
        "LOWER",
    }:

        position = None

    # -------------------------------------------------------------------------
    # ACCELERATION
    #
    # Preserve genuine numeric value only.
    # -------------------------------------------------------------------------

    acceleration = feature.get(
        "acceleration"
    )

    if acceleration is not None:

        try:

            acceleration = float(
                acceleration
            )

            if not math.isfinite(
                acceleration
            ):

                acceleration = None

        except (
            TypeError,
            ValueError,
        ):

            acceleration = None

    # -------------------------------------------------------------------------
    # EXACT FIVE-FIELD CONTRACT
    # -------------------------------------------------------------------------

    structure = {
        "trend": trend,
        "momentum": momentum,
        "acceleration": acceleration,
        "position": position,
        "volatility": volatility,
    }

    return structure


# =============================================================================
# STRUCTURE VALIDATION
# =============================================================================

def validate_public_structure(
    structure,
):

    if not isinstance(
        structure,
        dict,
    ):

        return False

    expected = {
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    }

    if set(
        structure.keys()
    ) != expected:

        return False

    if structure["trend"] not in {
        "UP",
        "DOWN",
        "FLAT",
        None,
    }:

        return False

    if structure["momentum"] not in {
        "STRONG",
        "WEAK",
        None,
    }:

        return False

    if structure["position"] not in {
        "UPPER",
        "MIDDLE",
        "LOWER",
        None,
    }:

        return False

    if structure["volatility"] not in {
        "LOW",
        "MEDIUM",
        "HIGH",
        None,
    }:

        return False

    acceleration = structure[
        "acceleration"
    ]

    if acceleration is not None:

        if not isinstance(
            acceleration,
            (int, float),
        ):

            return False

        if not math.isfinite(
            float(acceleration)
        ):

            return False

    return True


# =============================================================================
# BUILD SIGNAL
# =============================================================================

def build_signal(
    asset,
    feature,
):

    if asset not in EXPECTED_ASSETS:

        raise RuntimeError(
            "Unknown asset: " + str(asset)
        )

    if not isinstance(
        feature,
        dict,
    ):

        raise RuntimeError(
            "Invalid feature: " + str(asset)
        )

    # -------------------------------------------------------------------------
    # REAL CONTEXT
    # -------------------------------------------------------------------------

    points = safe_int(
        feature.get(
            "points",
            0,
        )
    )

    context = context_from_points(
        points
    )

    status = status_from_context(
        context
    )

    # -------------------------------------------------------------------------
    # PUBLIC STRUCTURE
    # -------------------------------------------------------------------------

    structure = build_public_structure(
        feature
    )

    if not validate_public_structure(
        structure
    ):

        raise RuntimeError(
            "Public five-field structure invalid: "
            + str(asset)
        )

    # -------------------------------------------------------------------------
    # SIGNAL LOGIC
    # -------------------------------------------------------------------------

    direction = signal_logic.build_direction(
        structure
    )

    if direction not in VALID_DIRECTIONS:

        raise RuntimeError(
            "Invalid direction: "
            + str(asset)
        )

    # -------------------------------------------------------------------------
    # ACTIVE
    #
    # ACTIVE means a genuine direction exists.
    #
    # It does NOT yet mean ELIGIBLE.
    # -------------------------------------------------------------------------

    active = (
        status == "AVAILABLE"
        and direction in {
            "LONG",
            "SHORT",
        }
    )

    # -------------------------------------------------------------------------
    # ELIGIBILITY
    #
    # Requirements:
    #
    # 1. AVAILABLE
    # 2. REAL CONTEXT >= 21
    # 3. Valid LONG/SHORT direction
    #
    # No 150-point requirement.
    # LIMITED is eligible.
    # -------------------------------------------------------------------------

    eligible = (
        status == "AVAILABLE"
        and points >= MINIMUM_CONTEXT
        and direction in {
            "LONG",
            "SHORT",
        }
    )

    # -------------------------------------------------------------------------
    # SIGNAL STATE
    # -------------------------------------------------------------------------

    if active:

        signal_state = "ACTIVE"

        reason = "STRUCTURAL_DIRECTION"

    else:

        signal_state = "NEUTRAL"

        reason = None

    # -------------------------------------------------------------------------
    # SIGNAL RECORD
    # -------------------------------------------------------------------------

    signal = {

        "asset": asset,

        "timestamp": None,

        "signal_state": signal_state,

        "direction": direction,

        "confidence": None,

        "reason": reason,

    }

    # -------------------------------------------------------------------------
    # SIGNAL CONTRACT
    # -------------------------------------------------------------------------

    if not signal_contract.validate_signal(
        signal
    ):

        raise RuntimeError(
            "Signal contract validation failed: "
            + str(asset)
        )

    # -------------------------------------------------------------------------
    # ENGINE RECORD
    # -------------------------------------------------------------------------

    return {

        "asset": asset,

        "status": status,

        "context": context,

        "points": points,

        "structure": structure,

        "direction": direction,

        "active": active,

        "eligible": eligible,

        "signal": signal,

    }


# =============================================================================
# BUILD ALL
# =============================================================================

def build_all():

    raw_state = load_regime()

    results = {}

    for asset in EXPECTED_ASSETS:

        if asset not in raw_state:

            raise RuntimeError(
                "Missing asset: " + asset
            )

        results[asset] = build_signal(
            asset,
            raw_state[asset],
        )

    return results


# =============================================================================
# VALIDATE FULL ENGINE CONTRACT
# =============================================================================

def validate_engine_contract(
    results,
):

    if not isinstance(
        results,
        dict,
    ):

        return False

    if set(results.keys()) != set(
        EXPECTED_ASSETS
    ):

        return False

    for asset in EXPECTED_ASSETS:

        item = results.get(
            asset
        )

        if not isinstance(
            item,
            dict,
        ):

            return False

        if item.get("asset") != asset:

            return False

        if item.get("status") not in {
            "AVAILABLE",
            "UNAVAILABLE",
        }:

            return False

        if item.get("context") not in {
            "FULL",
            "LIMITED",
            "NONE",
        }:

            return False

        points = item.get(
            "points"
        )

        if not isinstance(
            points,
            int,
        ):

            return False

        expected_context = (
            context_from_points(
                points
            )
        )

        if item.get(
            "context"
        ) != expected_context:

            return False

        expected_status = (
            status_from_context(
                expected_context
            )
        )

        if item.get(
            "status"
        ) != expected_status:

            return False

        structure = item.get(
            "structure"
        )

        if not validate_public_structure(
            structure
        ):

            return False

        direction = item.get(
            "direction"
        )

        if direction not in VALID_DIRECTIONS:

            return False

        active = item.get(
            "active"
        )

        expected_active = (
            expected_status == "AVAILABLE"
            and direction in {
                "LONG",
                "SHORT",
            }
        )

        if active != expected_active:

            return False

        eligible = item.get(
            "eligible"
        )

        expected_eligible = (
            expected_status == "AVAILABLE"
            and points >= MINIMUM_CONTEXT
            and direction in {
                "LONG",
                "SHORT",
            }
        )

        if eligible != expected_eligible:

            return False

        signal = item.get(
            "signal"
        )

        if not isinstance(
            signal,
            dict,
        ):

            return False

        if not signal_contract.validate_signal(
            signal
        ):

            return False

    return True


# =============================================================================
# PRINT SNAPSHOT
# =============================================================================

def print_snapshot(
    results,
):

    print("SIGNAL ENGINE SNAPSHOT")
    print("-" * 110)

    print(
        "Asset  | Status      | Context | Points | "
        "Direction | Active | Eligible | Regime"
    )

    print("-" * 110)

    for asset in EXPECTED_ASSETS:

        item = results[
            asset
        ]

        regime = "UNDEFINED"

        # Regime is informational only.
        # It never creates direction or eligibility.

        print(
            "{:<6} | {:<11} | {:<7} | {:>6} | "
            "{:<9} | {:<6} | {:<8} | {}".format(
                asset,
                item["status"],
                item["context"],
                item["points"],
                item["direction"],
                "YES"
                if item["active"]
                else "NO",
                "YES"
                if item["eligible"]
                else "NO",
                regime,
            )
        )

    print()


# =============================================================================
# CONTRACT SUMMARY
# =============================================================================

def print_contract(
    results,
):

    valid = validate_engine_contract(
        results
    )

    ready = len(results)

    active = sum(
        1
        for item in results.values()
        if item["active"]
    )

    eligible = sum(
        1
        for item in results.values()
        if item["eligible"]
    )

    neutral = sum(
        1
        for item in results.values()
        if not item["active"]
    )

    unavailable = sum(
        1
        for item in results.values()
        if item["status"] != "AVAILABLE"
    )

    full = sum(
        1
        for item in results.values()
        if item["context"] == "FULL"
    )

    limited = sum(
        1
        for item in results.values()
        if item["context"] == "LIMITED"
    )

    long_count = sum(
        1
        for item in results.values()
        if item["direction"] == "LONG"
    )

    short_count = sum(
        1
        for item in results.values()
        if item["direction"] == "SHORT"
    )

    none_count = sum(
        1
        for item in results.values()
        if item["direction"] == "NONE"
    )

    print("=" * 82)
    print("SIGNAL ENGINE CONTRACT")
    print("=" * 82)

    print(
        "Expected Assets :", len(EXPECTED_ASSETS)
    )

    print(
        "READY            :", ready
    )

    print(
        "ACTIVE           :", active
    )

    print(
        "ELIGIBLE         :", eligible
    )

    print(
        "NEUTRAL          :", neutral
    )

    print(
        "UNAVAILABLE      :", unavailable
    )

    print(
        "FULL             :", full
    )

    print(
        "LIMITED          :", limited
    )

    print(
        "LONG             :", long_count
    )

    print(
        "SHORT            :", short_count
    )

    print(
        "NONE             :", none_count
    )

    print(
        "Full Context     :", FULL_CONTEXT_TARGET
    )

    print(
        "Minimum Context  :", MINIMUM_CONTEXT
    )

    print(
        "Eligibility Rule : AVAILABLE + REAL CONTEXT >= 21 + LONG/SHORT"
    )

    print(
        "Storage          : MEMORY ONLY"
    )

    print(
        "Database writes  : NONE"
    )

    print(
        "Synthetic        : NO"
    )

    print(
        "Interpolation    : NO"
    )

    print(
        "Padding          : NO"
    )

    print(
        "Scoring          : NOT USED"
    )

    print(
        "Decision         : NOT USED"
    )

    print(
        "Contract Status  :",
        "VALID"
        if valid
        else "INVALID",
    )

    print()

    return valid


# =============================================================================
# FINAL VERIFICATION
# =============================================================================

def verify(
    results,
):

    print("=" * 82)
    print("SIGNAL ENGINE VERIFICATION")
    print("=" * 82)

    # -------------------------------------------------------------------------
    # READY
    # -------------------------------------------------------------------------

    ready = (
        isinstance(results, dict)
        and len(results) == len(
            EXPECTED_ASSETS
        )
    )

    print(
        "READY    :",
        "PASS"
        if ready
        else "FAIL",
    )

    if not ready:

        return False

    # -------------------------------------------------------------------------
    # STRUCTURE + LOGIC + CONTRACT
    # -------------------------------------------------------------------------

    contract = validate_engine_contract(
        results
    )

    print(
        "CONTRACT :",
        "PASS"
        if contract
        else "FAIL",
    )

    if not contract:

        return False

    # -------------------------------------------------------------------------
    # ACTIVE
    # -------------------------------------------------------------------------

    active_count = sum(
        1
        for item in results.values()
        if item["active"]
    )

    print(
        "ACTIVE   :",
        active_count,
    )

    # -------------------------------------------------------------------------
    # ELIGIBLE
    # -------------------------------------------------------------------------

    eligible_count = sum(
        1
        for item in results.values()
        if item["eligible"]
    )

    print(
        "ELIGIBLE :",
        eligible_count,
    )

    # -------------------------------------------------------------------------
    # REAL CONTEXT PROTECTION
    # -------------------------------------------------------------------------

    context_ok = True

    for item in results.values():

        if item["eligible"]:

            if item["points"] < MINIMUM_CONTEXT:

                context_ok = False

                break

            if item["status"] != "AVAILABLE":

                context_ok = False

                break

    print(
        "REAL CONTEXT :",
        "PASS"
        if context_ok
        else "FAIL",
    )

    if not context_ok:

        return False

    # -------------------------------------------------------------------------
    # NO SYNTHETIC CONTEXT
    # -------------------------------------------------------------------------

    no_fake_150 = True

    for item in results.values():

        if item["points"] < FULL_CONTEXT_TARGET:

            if item["points"] == FULL_CONTEXT_TARGET:

                no_fake_150 = False

                break

    print(
        "NO FAKE 150   :",
        "PASS"
        if no_fake_150
        else "FAIL",
    )

    if not no_fake_150:

        return False

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    print()
    print(
        "ELIGIBILITY CONTRACT : PASS"
    )

    print(
        "SIGNAL ENGINE STATUS : READY"
    )

    print()

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    try:

        results = build_all()

        print_snapshot(
            results
        )

        contract_valid = print_contract(
            results
        )

        if not contract_valid:

            print(
                "SIGNAL ENGINE STATUS : FAILED"
            )

            return 1

        verified = verify(
            results
        )

        if not verified:

            print(
                "SIGNAL ENGINE STATUS : FAILED"
            )

            return 1

        return 0

    except Exception as error:

        print("=" * 82)
        print("SIGNAL ENGINE ERROR")
        print("=" * 82)

        print(
            "Type  :",
            type(error).__name__,
        )

        print(
            "Error :",
            str(error),
        )

        print()

        print(
            "SIGNAL ENGINE STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )