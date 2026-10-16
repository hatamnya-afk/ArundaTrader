# =============================================================================
# ARUNDA SIGNAL LOGIC v0.4
#
# PURPOSE:
# Public five-field structural state -> signal direction
#
# READ ONLY
# MEMORY ONLY
# NO SQL
# NO DATABASE WRITE
# NO ORDER
# NO SCORING
# NO DECISION
#
# PUBLIC STRUCTURE CONTRACT:
#
# {
#     "trend": "UP" | "DOWN" | "FLAT" | None,
#     "momentum": "STRONG" | "WEAK" | None,
#     "acceleration": float | int | None,
#     "position": "UPPER" | "MIDDLE" | "LOWER" | None,
#     "volatility": "LOW" | "MEDIUM" | "HIGH" | None,
# }
#
# DIRECTION:
#     LONG
#     SHORT
#     NONE
#
# IMPORTANT:
# - No hidden structural fields are accepted.
# - No inference from regime.
# - No inference from volatility.
# - No fabricated confidence.
# - Acceleration must be the genuine numeric value when supplied.
# =============================================================================


EXPECTED_FIELDS = [
    "trend",
    "momentum",
    "acceleration",
    "position",
    "volatility",
]


VALID_TRENDS = {
    "UP",
    "DOWN",
    "FLAT",
    None,
}


VALID_MOMENTUM = {
    "STRONG",
    "WEAK",
    None,
}


VALID_POSITION = {
    "UPPER",
    "MIDDLE",
    "LOWER",
    None,
}


VALID_VOLATILITY = {
    "LOW",
    "MEDIUM",
    "HIGH",
    None,
}


VALID_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}


# =============================================================================
# NORMALIZATION
# =============================================================================

def _normalize_text(value):

    if value is None:
        return None

    value = str(value).strip().upper()

    if value == "":
        return None

    return value


def _normalize_acceleration(value):

    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):

        return None


# =============================================================================
# STRUCTURE VALIDATION
# =============================================================================

def validate_structure(structure):

    if not isinstance(structure, dict):
        raise RuntimeError(
            "Invalid structural state: expected dict"
        )

    if set(structure.keys()) != set(EXPECTED_FIELDS):

        raise RuntimeError(
            "Invalid structural fields: expected exactly "
            + ", ".join(EXPECTED_FIELDS)
        )

    trend = structure.get("trend")
    momentum = structure.get("momentum")
    acceleration = structure.get("acceleration")
    position = structure.get("position")
    volatility = structure.get("volatility")

    if trend not in VALID_TRENDS:

        raise RuntimeError(
            "Invalid trend value: "
            + str(trend)
        )

    if momentum not in VALID_MOMENTUM:

        raise RuntimeError(
            "Invalid momentum value: "
            + str(momentum)
        )

    if position not in VALID_POSITION:

        raise RuntimeError(
            "Invalid position value: "
            + str(position)
        )

    if volatility not in VALID_VOLATILITY:

        raise RuntimeError(
            "Invalid volatility value: "
            + str(volatility)
        )

    if acceleration is not None:

        normalized = _normalize_acceleration(
            acceleration
        )

        if normalized is None:

            raise RuntimeError(
                "Invalid acceleration value: "
                + str(acceleration)
            )

    return True


# =============================================================================
# DIRECTION
# =============================================================================

def determine_direction(structure):

    validate_structure(
        structure
    )

    trend = _normalize_text(
        structure.get("trend")
    )

    momentum = _normalize_text(
        structure.get("momentum")
    )

    acceleration = _normalize_acceleration(
        structure.get("acceleration")
    )

    # -------------------------------------------------------------------------
    # LONG
    #
    # Strong momentum:
    #   UP + STRONG -> LONG
    #
    # Weak momentum:
    #   UP + WEAK + non-negative acceleration -> LONG
    # -------------------------------------------------------------------------

    if trend == "UP":

        if momentum == "STRONG":

            return "LONG"

        if (
            momentum == "WEAK"
            and acceleration is not None
            and acceleration >= 0
        ):

            return "LONG"

    # -------------------------------------------------------------------------
    # SHORT
    #
    # Strong momentum:
    #   DOWN + STRONG -> SHORT
    #
    # Weak momentum:
    #   DOWN + WEAK + non-positive acceleration -> SHORT
    # -------------------------------------------------------------------------

    if trend == "DOWN":

        if momentum == "STRONG":

            return "SHORT"

        if (
            momentum == "WEAK"
            and acceleration is not None
            and acceleration <= 0
        ):

            return "SHORT"

    # -------------------------------------------------------------------------
    # NO DIRECTION
    # -------------------------------------------------------------------------

    return "NONE"


# =============================================================================
# PUBLIC API
# =============================================================================

def build_direction(structure):

    direction = determine_direction(
        structure
    )

    if direction not in VALID_DIRECTIONS:

        raise RuntimeError(
            "Invalid direction generated: "
            + str(direction)
        )

    return direction


# =============================================================================
# SELF VERIFY
# =============================================================================

def self_verify():

    # -------------------------------------------------------------------------
    # LONG / STRONG
    # -------------------------------------------------------------------------

    long_strong = {
        "trend": "UP",
        "momentum": "STRONG",
        "acceleration": 0.10,
        "position": None,
        "volatility": None,
    }

    if build_direction(long_strong) != "LONG":
        return False

    # -------------------------------------------------------------------------
    # SHORT / STRONG
    # -------------------------------------------------------------------------

    short_strong = {
        "trend": "DOWN",
        "momentum": "STRONG",
        "acceleration": -0.10,
        "position": None,
        "volatility": None,
    }

    if build_direction(short_strong) != "SHORT":
        return False

    # -------------------------------------------------------------------------
    # LONG / WEAK / POSITIVE ACCELERATION
    # -------------------------------------------------------------------------

    long_weak = {
        "trend": "UP",
        "momentum": "WEAK",
        "acceleration": 0.10,
        "position": None,
        "volatility": None,
    }

    if build_direction(long_weak) != "LONG":
        return False

    # -------------------------------------------------------------------------
    # SHORT / WEAK / NEGATIVE ACCELERATION
    # -------------------------------------------------------------------------

    short_weak = {
        "trend": "DOWN",
        "momentum": "WEAK",
        "acceleration": -0.10,
        "position": None,
        "volatility": None,
    }

    if build_direction(short_weak) != "SHORT":
        return False

    # -------------------------------------------------------------------------
    # INVALID DIRECTION
    # -------------------------------------------------------------------------

    neutral = {
        "trend": "FLAT",
        "momentum": "WEAK",
        "acceleration": 0.0,
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }

    if build_direction(neutral) != "NONE":
        return False

    # -------------------------------------------------------------------------
    # UNKNOWN TREND
    # -------------------------------------------------------------------------

    unknown = {
        "trend": None,
        "momentum": "STRONG",
        "acceleration": 1.0,
        "position": None,
        "volatility": None,
    }

    if build_direction(unknown) != "NONE":
        return False

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("ARUNDA SIGNAL LOGIC v0.4")
    print("=" * 60)

    try:

        verify = self_verify()

        print(
            "Structure Contract : VALID"
        )

        print(
            "Direction Logic    :",
            "VALID"
            if verify
            else "INVALID",
        )

        if verify:

            print(
                "SELF VERIFY        : PASS"
            )

            print(
                "SIGNAL LOGIC STATUS: READY"
            )

            return 0

        print(
            "SELF VERIFY        : FAIL"
        )

        print(
            "SIGNAL LOGIC STATUS: FAILED"
        )

        return 1

    except Exception as error:

        print(
            "SELF VERIFY        : ERROR"
        )

        print(
            "Type               :",
            type(error).__name__,
        )

        print(
            "Error              :",
            str(error),
        )

        print(
            "SIGNAL LOGIC STATUS: FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )