# M2_REAL_SIGNAL_STATE_BLOCKER_LOCATOR_v0.1.py

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Mapping

import signal_engine


PROJECT_ROOT = Path(__file__).resolve().parent
EXPECTED_ASSETS = (
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
)


# =============================================================================
# SAFETY
# =============================================================================

MODE = "READ ONLY"
DATABASE_USED = False
DATABASE_WRITE = False
PRODUCTION_MODIFIED = False
SYNTHETIC_DATA = False


def fail(message: str) -> None:
    raise RuntimeError(message)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


# =============================================================================
# SELF TEST
# =============================================================================

def self_test() -> None:

    assert_true(
        isinstance(EXPECTED_ASSETS, tuple),
        "EXPECTED_ASSETS must be tuple",
    )

    assert_true(
        len(EXPECTED_ASSETS) == 15,
        "EXPECTED_ASSETS must contain exactly 15 assets",
    )

    assert_true(
        len(set(EXPECTED_ASSETS)) == 15,
        "EXPECTED_ASSETS contains duplicates",
    )

    assert_true(
        hasattr(signal_engine, "build_all"),
        "signal_engine.build_all() not found",
    )

    signature = inspect.signature(
        signal_engine.build_all
    )

    assert_true(
        len(signature.parameters) == 0,
        "signal_engine.build_all() must require no arguments",
    )


# =============================================================================
# STATE CANDIDATE EXTRACTION
# =============================================================================

STATE_KEYS = (
    "state",
    "signal_state",
    "status",
)

DIRECTION_KEYS = (
    "direction",
    "signal_direction",
)

ELIGIBILITY_KEYS = (
    "eligible",
    "scorer_eligible",
)


def extract_key(
    mapping: Mapping[str, Any],
    keys: tuple[str, ...],
) -> tuple[str | None, Any]:

    for key in keys:
        if key in mapping:
            return key, mapping[key]

    return None, None


def inspect_signal_record(
    asset: str,
    signal: Any,
) -> dict[str, Any]:

    result = {
        "asset": asset,
        "signal_type": type(signal).__name__,
        "state_key": None,
        "state_value": None,
        "direction_key": None,
        "direction_value": None,
        "eligible_key": None,
        "eligible_value": None,
        "mapping": False,
        "keys": [],
        "nested_keys": {},
    }

    if not isinstance(signal, Mapping):
        return result

    result["mapping"] = True
    result["keys"] = list(signal.keys())

    state_key, state_value = extract_key(
        signal,
        STATE_KEYS,
    )

    direction_key, direction_value = extract_key(
        signal,
        DIRECTION_KEYS,
    )

    eligible_key, eligible_value = extract_key(
        signal,
        ELIGIBILITY_KEYS,
    )

    result["state_key"] = state_key
    result["state_value"] = state_value

    result["direction_key"] = direction_key
    result["direction_value"] = direction_value

    result["eligible_key"] = eligible_key
    result["eligible_value"] = eligible_value

    # Inspect nested mappings only.
    for key, value in signal.items():

        if isinstance(value, Mapping):

            nested_state_key, nested_state_value = extract_key(
                value,
                STATE_KEYS,
            )

            nested_direction_key, nested_direction_value = extract_key(
                value,
                DIRECTION_KEYS,
            )

            nested_eligible_key, nested_eligible_value = extract_key(
                value,
                ELIGIBILITY_KEYS,
            )

            if (
                nested_state_key is not None
                or nested_direction_key is not None
                or nested_eligible_key is not None
            ):

                result["nested_keys"][key] = {
                    "state_key": nested_state_key,
                    "state_value": nested_state_value,
                    "direction_key": nested_direction_key,
                    "direction_value": nested_direction_value,
                    "eligible_key": nested_eligible_key,
                    "eligible_value": nested_eligible_value,
                }

    return result


# =============================================================================
# BUILD ALL
# =============================================================================

def load_real_snapshot() -> Mapping[str, Any]:

    snapshot = signal_engine.build_all()

    assert_true(
        isinstance(snapshot, Mapping),
        "signal_engine.build_all() must return a mapping",
    )

    return snapshot


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER — M2"
    )
    print(
        "M2_REAL_SIGNAL_STATE_BLOCKER_LOCATOR_v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT              : {PROJECT_ROOT}"
    )
    print(
        f"MODE                 : {MODE}"
    )
    print(
        f"DATABASE             : NOT USED"
    )
    print(
        f"DATABASE WRITE       : NONE"
    )
    print(
        f"PRODUCTION MODIFIED  : NO"
    )
    print(
        f"SYNTHETIC DATA       : {'YES' if SYNTHETIC_DATA else 'NONE'}"
    )
    print("=" * 100)

    print("Running self-test...")
    self_test()
    print("SELF TEST : PASS")

    print()
    print("-" * 100)
    print("REAL SIGNAL SOURCE")
    print("-" * 100)

    print(
        "Source       : signal_engine.build_all()"
    )

    snapshot = load_real_snapshot()

    print(
        f"Assets       : {len(snapshot)}"
    )

    print()
    print("-" * 100)
    print("ASSET PRESENCE")
    print("-" * 100)

    missing_assets = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in snapshot
    ]

    unexpected_assets = [
        asset
        for asset in snapshot
        if asset not in EXPECTED_ASSETS
    ]

    for asset in EXPECTED_ASSETS:

        if asset in snapshot:
            print(
                f"{asset:<10} : PRESENT"
            )
        else:
            print(
                f"{asset:<10} : MISSING"
            )

    if unexpected_assets:

        print()
        print(
            "UNEXPECTED ASSETS:"
        )

        for asset in unexpected_assets:
            print(
                f"  {asset}"
            )

    print()
    print("-" * 100)
    print("SIGNAL STATE RESOLUTION")
    print("-" * 100)

    analyses: dict[str, dict[str, Any]] = {}

    for asset in EXPECTED_ASSETS:

        if asset not in snapshot:
            continue

        record = snapshot[asset]

        if not isinstance(record, Mapping):

            analyses[asset] = {
                "asset": asset,
                "record_mapping": False,
                "signal_present": False,
                "signal": None,
            }

            print(
                f"{asset:<10} RECORD=INVALID"
            )

            continue

        signal = record.get("signal")

        analysis = {
            "asset": asset,
            "record_mapping": True,
            "signal_present": signal is not None,
            "signal": inspect_signal_record(
                asset,
                signal,
            ),
        }

        analyses[asset] = analysis

        if signal is None:

            print(
                f"{asset:<10} SIGNAL=MISSING"
            )

            continue

        signal_info = analysis["signal"]

        state = signal_info["state_value"]
        direction = signal_info["direction_value"]
        eligible = signal_info["eligible_value"]

        print(
            f"{asset:<10} "
            f"STATE={repr(state):<14} "
            f"DIRECTION={repr(direction):<10} "
            f"ELIGIBLE={repr(eligible):<8}"
        )

    # =========================================================================
    # BLOCKER FOCUS
    # =========================================================================

    print()
    print("-" * 100)
    print("BLOCKER FOCUS : AAVE")
    print("-" * 100)

    target = "AAVE"

    if target not in snapshot:

        print(
            "AAVE : MISSING FROM build_all()"
        )

    else:

        target_record = snapshot[target]

        print(
            f"record type : {type(target_record).__name__}"
        )

        if isinstance(target_record, Mapping):

            print(
                f"record keys : {list(target_record.keys())}"
            )

            target_signal = target_record.get("signal")

            if target_signal is None:

                print(
                    "signal      : MISSING"
                )

            else:

                print(
                    f"signal type : {type(target_signal).__name__}"
                )

                if isinstance(target_signal, Mapping):

                    print(
                        f"signal keys : {list(target_signal.keys())}"
                    )

                    print()

                    print(
                        "DIRECT STATE CANDIDATES:"
                    )

                    for key in STATE_KEYS:

                        if key in target_signal:

                            print(
                                f"  {key:<20} = "
                                f"{repr(target_signal[key])}"
                            )

                    print()

                    print(
                        "NESTED STATE CANDIDATES:"
                    )

                    found_nested = False

                    for key, value in target_signal.items():

                        if not isinstance(value, Mapping):
                            continue

                        for state_key in STATE_KEYS:

                            if state_key in value:

                                found_nested = True

                                print(
                                    f"  {key}.{state_key:<16} = "
                                    f"{repr(value[state_key])}"
                                )

                    if not found_nested:

                        print(
                            "  NONE"
                        )

                else:

                    print(
                        "signal is not a Mapping"
                    )

    # =========================================================================
    # CROSS-ASSET COMPARISON
    # =========================================================================

    print()
    print("-" * 100)
    print("CROSS-ASSET STATE SHAPE COMPARISON")
    print("-" * 100)

    state_shapes: dict[str, list[str]] = {}

    for asset, analysis in analyses.items():

        signal_info = analysis.get("signal")

        if not isinstance(signal_info, Mapping):
            continue

        keys = signal_info.get("keys", [])

        state_shapes[asset] = [
            key
            for key in keys
            if key in STATE_KEYS
        ]

    for asset in EXPECTED_ASSETS:

        if asset not in state_shapes:
            continue

        print(
            f"{asset:<10} STATE_KEYS={state_shapes[asset]}"
        )

    # =========================================================================
    # FINAL DIAGNOSIS
    # =========================================================================

    print()
    print("=" * 100)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 100)

    if missing_assets:

        print(
            f"BUILD_ALL MISSING ASSETS : {missing_assets}"
        )

    else:

        print(
            "BUILD_ALL ASSETS         : 15/15 PRESENT"
        )

    missing_signals = []

    missing_states = []

    present_states = []

    for asset in EXPECTED_ASSETS:

        analysis = analyses.get(asset)

        if not analysis:
            continue

        if not analysis.get("signal_present"):
            missing_signals.append(asset)
            continue

        signal_info = analysis.get("signal")

        if not isinstance(signal_info, Mapping):
            missing_states.append(asset)
            continue

        state_value = signal_info.get("state_value")

        if state_value is None:
            missing_states.append(asset)
        else:
            present_states.append(asset)

    print(
        f"SIGNALS PRESENT         : "
        f"{len(present_states) + len(missing_states)}/15"
    )

    print(
        f"STATE PRESENT           : "
        f"{len(present_states)}/15"
    )

    if missing_signals:

        print(
            f"SIGNALS MISSING         : {missing_signals}"
        )

    if missing_states:

        print(
            f"STATE MISSING           : {missing_states}"
        )

    print()
    print("-" * 100)
    print("FINAL STATUS")
    print("-" * 100)

    if target in missing_states:

        print(
            "STATUS : BLOCKER CONFIRMED"
        )

        print(
            "BLOCKER : REAL_SIGNAL_STATE_MISSING:AAVE"
        )

        print(
            "NEXT    : REPAIR ONLY THE M2 STATE RESOLUTION BOUNDARY"
        )

    elif target in present_states:

        print(
            "STATUS : AAVE STATE IS PRESENT"
        )

        print(
            "NEXT   : INSPECT M2 RESOLVER LOGIC"
        )

    else:

        print(
            "STATUS : AAVE SIGNAL PATH REQUIRES FURTHER RESOLUTION"
        )

    print()
    print(
        "DATABASE WRITE       : NONE"
    )
    print(
        "PRODUCTION MODIFIED  : NO"
    )
    print(
        "SYNTHETIC DATA       : NONE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()