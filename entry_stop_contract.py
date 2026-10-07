"""
ARUNDA ENTRY / STOP CONTRACT v0.1
"""

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

EXPECTED_ASSET_COUNT = 15

ENTRY_STOP_FIELDS = (
    "asset",
    "direction",
    "state",
    "entry_price",
    "stop_distance",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

ENTRY_STOP_STATES = (
    "READY",
    "UNAVAILABLE",
    "BLOCKED",
)


def build_empty_record(asset):

    if asset not in EXPECTED_ASSETS:
        raise ValueError(
            f"Unknown asset: {asset}"
        )

    return {
        "asset": asset,
        "direction": "NONE",
        "state": "UNAVAILABLE",
        "entry_price": None,
        "stop_distance": None,
    }


def validate_positive_number(
    value,
    field,
    asset,
):

    if isinstance(value, bool):
        raise RuntimeError(
            f"Invalid {field} type for {asset}"
        )

    if not isinstance(value, (int, float)):
        raise RuntimeError(
            f"Invalid {field} for {asset}: {value!r}"
        )

    if value <= 0:
        raise RuntimeError(
            f"{field} must be greater than zero for {asset}"
        )

    return True


def validate_entry_stop(data):

    if not isinstance(data, dict):
        raise RuntimeError(
            "Entry / Stop record must be a dictionary"
        )

    for field in ENTRY_STOP_FIELDS:

        if field not in data:
            raise RuntimeError(
                f"Missing Entry / Stop field: {field}"
            )

    asset = data["asset"]

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"Unknown asset: {asset}"
        )

    direction = data["direction"]

    if direction not in DIRECTIONS:
        raise RuntimeError(
            f"Invalid direction for {asset}: {direction}"
        )

    state = data["state"]

    if state not in ENTRY_STOP_STATES:
        raise RuntimeError(
            f"Invalid Entry / Stop state for {asset}: {state}"
        )

    if state == "UNAVAILABLE":

        if direction != "NONE":
            raise RuntimeError(
                "UNAVAILABLE Entry / Stop record must have direction NONE"
            )

        if data["entry_price"] is not None:
            raise RuntimeError(
                "UNAVAILABLE Entry / Stop record must have entry_price NONE"
            )

        if data["stop_distance"] is not None:
            raise RuntimeError(
                "UNAVAILABLE Entry / Stop record must have stop_distance NONE"
            )

    elif state == "READY":

        if direction not in ("LONG", "SHORT"):
            raise RuntimeError(
                "READY Entry / Stop record must have LONG or SHORT direction"
            )

        entry_price = data["entry_price"]
        stop_distance = data["stop_distance"]

        if entry_price is None:
            raise RuntimeError(
                f"READY record missing entry_price for {asset}"
            )

        if stop_distance is None:
            raise RuntimeError(
                f"READY record missing stop_distance for {asset}"
            )

        validate_positive_number(
            entry_price,
            "entry_price",
            asset,
        )

        validate_positive_number(
            stop_distance,
            "stop_distance",
            asset,
        )

    elif state == "BLOCKED":

        if direction == "NONE":
            raise RuntimeError(
                "BLOCKED Entry / Stop record must have LONG or SHORT direction"
            )

        if data["entry_price"] is not None:
            validate_positive_number(
                data["entry_price"],
                "entry_price",
                asset,
            )

        if data["stop_distance"] is not None:
            validate_positive_number(
                data["stop_distance"],
                "stop_distance",
                asset,
            )

    return True


def validate_entry_stop_snapshot(snapshot):

    if not isinstance(snapshot, dict):
        raise RuntimeError(
            "Entry / Stop snapshot must be a dictionary"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(snapshot.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            "Missing assets: " + ", ".join(sorted(missing))
        )

    if extra:
        raise RuntimeError(
            "Unexpected assets: " + ", ".join(sorted(extra))
        )

    for asset in EXPECTED_ASSETS:

        record = snapshot[asset]

        validate_entry_stop(record)

        if record["asset"] != asset:
            raise RuntimeError(
                f"Asset key mismatch: {asset}"
            )

    return {
        "expected_assets": EXPECTED_ASSET_COUNT,
        "validated_assets": len(snapshot),
        "ready": sum(
            1
            for asset in EXPECTED_ASSETS
            if snapshot[asset]["state"] == "READY"
        ),
        "unavailable": sum(
            1
            for asset in EXPECTED_ASSETS
            if snapshot[asset]["state"] == "UNAVAILABLE"
        ),
        "blocked": sum(
            1
            for asset in EXPECTED_ASSETS
            if snapshot[asset]["state"] == "BLOCKED"
        ),
        "contract_status": "VALID",
    }


def self_test():

    if len(EXPECTED_ASSETS) != 15:
        raise RuntimeError(
            "Expected asset count must be 15"
        )

    if len(ENTRY_STOP_FIELDS) != 5:
        raise RuntimeError(
            "Entry / Stop field count must be 5"
        )

    if len(ENTRY_STOP_STATES) != 3:
        raise RuntimeError(
            "Entry / Stop state count must be 3"
        )

    if len(DIRECTIONS) != 3:
        raise RuntimeError(
            "Direction count must be 3"
        )

    expected_fields = (
        "asset",
        "direction",
        "state",
        "entry_price",
        "stop_distance",
    )

    if ENTRY_STOP_FIELDS != expected_fields:
        raise RuntimeError(
            "Entry / Stop field definition is invalid"
        )

    expected_states = (
        "READY",
        "UNAVAILABLE",
        "BLOCKED",
    )

    if ENTRY_STOP_STATES != expected_states:
        raise RuntimeError(
            "Entry / Stop states are invalid"
        )

    expected_directions = (
        "LONG",
        "SHORT",
        "NONE",
    )

    if DIRECTIONS != expected_directions:
        raise RuntimeError(
            "Entry / Stop directions are invalid"
        )

    empty_record = build_empty_record("BTC")

    validate_entry_stop(empty_record)

    long_record = {
        "asset": "UNI",
        "direction": "LONG",
        "state": "READY",
        "entry_price": 100.0,
        "stop_distance": 5.0,
    }

    validate_entry_stop(long_record)

    short_record = {
        "asset": "NEAR",
        "direction": "SHORT",
        "state": "READY",
        "entry_price": 10.0,
        "stop_distance": 0.5,
    }

    validate_entry_stop(short_record)

    snapshot = {
        asset: build_empty_record(asset)
        for asset in EXPECTED_ASSETS
    }

    result = validate_entry_stop_snapshot(snapshot)

    if result["validated_assets"] != 15:
        raise RuntimeError(
            "Complete snapshot validation failed"
        )

    return True


def print_header():

    print("=" * 77)
    print("ARUNDA ENTRY / STOP CONTRACT v0.1")
    print("=" * 77)
    print("Expected Assets : 15")
    print("Fields          : 5")
    print("Fields          : asset / direction / state / entry_price / stop_distance")
    print("States          : READY / UNAVAILABLE / BLOCKED")
    print("Directions      : LONG / SHORT / NONE")
    print("Storage         : MEMORY ONLY")
    print("Database writes : NONE")
    print("SQL             : NOT USED")
    print("Entry Calculation : NOT USED")
    print("Stop Calculation  : NOT USED")
    print("Risk Calculation  : NOT USED")
    print("Position Sizing   : NOT USED")
    print("Exposure          : NOT USED")
    print("Execution         : NOT USED")
    print("Prediction        : NOT USED")
    print("Ranking           : NOT USED")
    print("Interpretation    : NOT USED")
    print("Contract Status   : VALID")
    print("=" * 77)


def main():

    print_header()

    try:

        self_test()

        print()
        print("=" * 77)
        print("ENTRY / STOP CONTRACT")
        print("=" * 77)
        print("Expected Assets : 15")
        print("Fields          : 5")
        print("States          : READY / UNAVAILABLE / BLOCKED")
        print("Directions      : LONG / SHORT / NONE")
        print("Storage         : MEMORY ONLY")
        print("Database writes : NONE")
        print("SQL             : NOT USED")
        print("Entry           : INPUT ONLY")
        print("Stop Distance   : INPUT ONLY")
        print("Position Size   : NOT USED")
        print("Exposure        : NOT USED")
        print("Risk Budget     : NOT USED")
        print("Execution       : NOT USED")
        print("Contract Status : VALID")
        print("=" * 77)

        print()
        print("ENTRY / STOP CONTRACT STATUS : READY")

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("ENTRY / STOP CONTRACT ERROR")
        print("=" * 77)
        print(f"Type  : {type(exc).__name__}")
        print(f"Error : {exc}")
        print()
        print("ENTRY / STOP CONTRACT STATUS : FAILED")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
