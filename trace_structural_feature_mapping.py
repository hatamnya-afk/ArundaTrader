# =============================================================================
# ARUNDA TRADER — STRUCTURAL FEATURE MAPPING FORENSIC TRACE
# =============================================================================
#
# PURPOSE:
#   Trace the exact runtime object produced by:
#
#       market_regime_engine.build_structural_state()
#                   ↓
#       market_regime.build_structure(feature)
#
#   Focus:
#       structure_direction
#       trend
#       first producer -> consumer mismatch
#
# MODE:
#   READ ONLY
#   NO DB WRITE
#   NO REPAIR
#   NO SIGNAL
#   NO SCORING
#   NO DECISION
#   NO SYNTHETIC DATA
# =============================================================================

import inspect

import market_regime_engine
import market_regime


TARGET_ASSETS = [
    "XRP",
    "SOL",
    "ETH",
]

EXPECTED_TREND_VALUES = {
    "UP",
    "DOWN",
    "FLAT",
}

EXPECTED_STRUCTURE_DIRECTION_VALUES = {
    "BULLISH",
    "BEARISH",
    "NEUTRAL",
    "UNKNOWN",
}


def print_header():

    print("=" * 82)
    print("ARUNDA TRADER — STRUCTURAL FEATURE MAPPING FORENSIC TRACE")
    print("=" * 82)

    print("MODE      : READ ONLY")
    print("SYNTHETIC : NO")
    print("DB WRITE  : NO")
    print("REPAIR    : NO")
    print("SIGNAL    : NO")
    print("SCORING   : NO")
    print("DECISION  : NO")
    print()

    print(
        "PRODUCER  : market_regime_engine.build_structural_state()"
    )

    print(
        "CONSUMER  : market_regime.build_structure(feature)"
    )

    print()


def safe_source(function):

    try:
        return inspect.getsource(function).strip()

    except Exception as error:

        return (
            "SOURCE UNAVAILABLE: "
            + type(error).__name__
            + ": "
            + str(error)
        )


def inspect_producer_source():

    print("-" * 82)
    print("PRODUCER SOURCE")
    print("-" * 82)

    print(
        safe_source(
            market_regime_engine.build_structural_state
        )
    )

    print()


def inspect_consumer_source():

    print("-" * 82)
    print("CONSUMER SOURCE")
    print("-" * 82)

    print(
        safe_source(
            market_regime.build_structure
        )
    )

    print()


def trace():

    structural_state = (
        market_regime_engine.build_structural_state()
    )

    if not isinstance(
        structural_state,
        dict,
    ):

        raise RuntimeError(
            "Producer returned non-dict structural state"
        )

    print("=" * 82)
    print("RUNTIME PRODUCER OUTPUT")
    print("=" * 82)

    print(
        "TYPE :",
        type(structural_state).__name__,
    )

    print(
        "ASSETS :",
        len(structural_state),
    )

    print()

    first_mismatch = None

    for asset in TARGET_ASSETS:

        print("-" * 82)
        print(asset)
        print("-" * 82)

        if asset not in structural_state:

            print("PRODUCER ENTRY : MISSING")
            print()

            if first_mismatch is None:
                first_mismatch = (
                    asset,
                    "producer_entry",
                )

            continue

        feature = structural_state[asset]

        print(
            "FEATURE TYPE :",
            type(feature).__name__,
        )

        if not isinstance(
            feature,
            dict,
        ):

            print("FEATURE : INVALID")
            print()

            if first_mismatch is None:
                first_mismatch = (
                    asset,
                    "feature_type",
                )

            continue

        print(
            "FEATURE KEYS :",
            list(feature.keys()),
        )

        print()

        print(
            "feature['structure_direction'] :",
            repr(
                feature.get(
                    "structure_direction"
                )
            ),
        )

        print(
            "structure_direction TYPE        :",
            type(
                feature.get(
                    "structure_direction"
                )
            ).__name__,
        )

        print()

        print(
            "feature['trend']               :",
            repr(
                feature.get(
                    "trend"
                )
            ),
        )

        print(
            "trend TYPE                     :",
            type(
                feature.get(
                    "trend"
                )
            ).__name__,
        )

        print()

        print(
            "feature['structure_state']      :",
            repr(
                feature.get(
                    "structure_state"
                )
            ),
        )

        print()

        producer_direction = feature.get(
            "structure_direction"
        )

        producer_trend = feature.get(
            "trend"
        )

        print(
            "PRODUCER STRUCTURE_DIRECTION :",
            repr(producer_direction),
        )

        print(
            "PRODUCER TREND               :",
            repr(producer_trend),
        )

        # ---------------------------------------------------------------------
        # EXACT CONSUMER MAPPING
        # ---------------------------------------------------------------------

        try:

            public_structure = (
                market_regime.build_structure(
                    feature
                )
            )

            print()

            print(
                "CONSUMER OUTPUT TYPE :",
                type(
                    public_structure
                ).__name__,
            )

            print(
                "CONSUMER trend       :",
                repr(
                    public_structure.get(
                        "trend"
                    )
                ),
            )

            print(
                "CONSUMER volatility  :",
                repr(
                    public_structure.get(
                        "volatility"
                    )
                ),
            )

            print(
                "CONSUMER momentum    :",
                repr(
                    public_structure.get(
                        "momentum"
                    )
                ),
            )

            print(
                "CONSUMER position    :",
                repr(
                    public_structure.get(
                        "position"
                    )
                ),
            )

            print(
                "CONSUMER acceleration:",
                repr(
                    public_structure.get(
                        "acceleration"
                    )
                ),
            )

        except Exception as error:

            print()

            print(
                "CONSUMER RESULT : FAILURE"
            )

            print(
                "ERROR TYPE      :",
                type(error).__name__,
            )

            print(
                "ERROR           :",
                str(error),
            )

            if first_mismatch is None:
                first_mismatch = (
                    asset,
                    "consumer_build_structure",
                )

            continue

        # ---------------------------------------------------------------------
        # MAPPING DIAGNOSIS
        # ---------------------------------------------------------------------

        print()

        if (
            producer_direction is not None
            and producer_trend is None
        ):

            print(
                "MAPPING STATUS : STRUCTURE_DIRECTION_PRESENT / TREND_ABSENT"
            )

            print(
                "DIAGNOSIS      : PRODUCER DOES NOT SUPPLY feature['trend']"
            )

            if first_mismatch is None:

                first_mismatch = (
                    asset,
                    "structure_direction_to_trend",
                )

        elif (
            producer_direction is not None
            and producer_trend is not None
        ):

            print(
                "MAPPING STATUS : BOTH_PRESENT"
            )

        elif (
            producer_direction is None
            and producer_trend is None
        ):

            print(
                "MAPPING STATUS : BOTH_ABSENT"
            )

        else:

            print(
                "MAPPING STATUS : TREND_PRESENT_ONLY"
            )

        print()


def print_final(first_mismatch):

    print("=" * 82)
    print("FINAL FORENSIC RESULT")
    print("=" * 82)

    if first_mismatch is None:

        print(
            "FIRST MISMATCH : NONE OBSERVED"
        )

        print(
            "RESULT         : NO PRODUCER/CONSUMER MAPPING MISMATCH OBSERVED"
        )

    else:

        asset, mismatch = first_mismatch

        print(
            "FIRST MISMATCH :",
            mismatch,
        )

        print(
            "ASSET         :",
            asset,
        )

        if mismatch == "structure_direction_to_trend":

            print(
                "ROOT OBSERVATION : producer emits "
                "structure_direction while consumer reads trend"
            )

        print(
            "RESULT         : PRODUCER → CONSUMER FIELD MISMATCH"
        )

    print()

    print(
        "REPAIR    : NONE"
    )

    print(
        "DB WRITE  : NONE"
    )

    print(
        "SYNTHETIC : NO"
    )

    print(
        "ORDER     : NONE"
    )

    print(
        "FRONTIER  : LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR"
    )


def main():

    print_header()

    inspect_producer_source()

    inspect_consumer_source()

    first_mismatch = None

    try:

        structural_state = (
            market_regime_engine.build_structural_state()
        )

        if not isinstance(
            structural_state,
            dict,
        ):

            raise RuntimeError(
                "Producer returned non-dict structural state"
            )

        # Re-run trace with exact same producer output
        # so the observed feature objects are from one runtime snapshot.

        print("=" * 82)
        print("RUNTIME PRODUCER → CONSUMER TRACE")
        print("=" * 82)

        for asset in TARGET_ASSETS:

            print("-" * 82)
            print(asset)
            print("-" * 82)

            if asset not in structural_state:

                print("PRODUCER ENTRY : MISSING")

                if first_mismatch is None:

                    first_mismatch = (
                        asset,
                        "producer_entry",
                    )

                continue

            feature = structural_state[
                asset
            ]

            if not isinstance(
                feature,
                dict,
            ):

                print(
                    "FEATURE TYPE :",
                    type(feature).__name__,
                )

                print(
                    "FAILURE : producer feature is not dict"
                )

                if first_mismatch is None:

                    first_mismatch = (
                        asset,
                        "feature_type",
                    )

                continue

            direction = feature.get(
                "structure_direction"
            )

            trend = feature.get(
                "trend"
            )

            print(
                "PRODUCER KEYS :",
                list(feature.keys()),
            )

            print(
                "structure_direction :",
                repr(direction),
            )

            print(
                "trend               :",
                repr(trend),
            )

            print()

            # Exact consumer transformation.
            consumer = (
                market_regime.build_structure(
                    feature
                )
            )

            consumer_trend = consumer.get(
                "trend"
            )

            print(
                "CONSUMER trend       :",
                repr(consumer_trend),
            )

            print(
                "CONSUMER structure keys :",
                list(consumer.keys()),
            )

            print()

            if (
                direction is not None
                and trend is None
            ):

                print(
                    "FIRST FIELD MAPPING FAILURE"
                )

                print(
                    "SOURCE FIELD : structure_direction"
                )

                print(
                    "TARGET FIELD : trend"
                )

                print(
                    "SOURCE VALUE :",
                    repr(direction),
                )

                print(
                    "TARGET VALUE :",
                    repr(consumer_trend),
                )

                print(
                    "RESULT       : MISMATCH"
                )

                if first_mismatch is None:

                    first_mismatch = (
                        asset,
                        "structure_direction_to_trend",
                    )

            elif (
                trend is not None
                and consumer_trend is None
            ):

                print(
                    "RESULT : CONSUMER NORMALIZATION DROPPED TREND"
                )

                if first_mismatch is None:

                    first_mismatch = (
                        asset,
                        "trend_normalization",
                    )

            else:

                print(
                    "RESULT : NO TREND MAPPING FAILURE"
                )

            print()

    except Exception as error:

        print("=" * 82)
        print("TRACE ERROR")
        print("=" * 82)

        print(
            "TYPE :",
            type(error).__name__,
        )

        print(
            "ERROR:",
            str(error),
        )

    print_final(
        first_mismatch
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )