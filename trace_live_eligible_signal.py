# trace_live_eligible_signal.py

import sys
import traceback

import signal_engine


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


def header():
    print("=" * 90)
    print("ARUNDA TRADER — LIVE ELIGIBLE SIGNAL PATH")
    print("=" * 90)
    print("MODE       : READ ONLY")
    print("SYNTHETIC  : NO")
    print("DB WRITE   : NO")
    print("ORDER      : NO")
    print()
    print("OBJECTIVE")
    print("REAL RUNTIME -> SIGNAL GENERATION -> ELIGIBLE SIGNAL")
    print("=" * 90)
    print()


def load_inputs():
    """
    Use the production signal-engine input loaders.
    No reconstruction of previous layers.
    """

    regime_contract = signal_engine.load_regime_contract()
    structural_state = signal_engine.load_structural_state()

    return regime_contract, structural_state


def run_asset(asset, regime_contract, structural_state):

    print("-" * 90)
    print(asset)
    print("-" * 90)

    if asset not in regime_contract:
        print("RESULT : BLOCKED")
        print("REASON : missing regime asset")
        return None

    if asset not in structural_state:
        print("RESULT : BLOCKED")
        print("REASON : missing structural asset")
        return None

    regime_data = regime_contract[asset]
    structural_data = structural_state[asset]

    print("REGIME STATUS :", regime_data.get("status"))
    print("REGIME        :", regime_data.get("regime"))
    print("STRUCTURE TYPE:", type(structural_data).__name__)

    try:

        signal = signal_engine.build_signal(
            asset=asset,
            regime_data=regime_data,
            structural_data=structural_data,
        )

    except Exception as error:

        print()
        print("BUILD_SIGNAL : FAILED")
        print("ERROR TYPE   :", type(error).__name__)
        print("ERROR        :", str(error))
        return None

    if not isinstance(signal, dict):

        print()
        print("BUILD_SIGNAL : FAILED")
        print("ERROR        : returned object is not dict")
        return None

    print()
    print("SIGNAL OBJECT")
    print("-------------")

    for key, value in signal.items():
        print("{:<15}: {}".format(key, value))

    direction = signal.get("direction")
    state = signal.get("signal_state")

    print()
    print("SIGNAL STATE :", state)
    print("DIRECTION    :", direction)

    # -------------------------------------------------------------------------
    # ELIGIBILITY DECISION
    #
    # This script does NOT invent eligibility rules.
    # It only recognizes the signal produced by production build_signal().
    # -------------------------------------------------------------------------

    if direction in ("LONG", "SHORT") and state == "ACTIVE":

        print()
        print("==============================================")
        print("ELIGIBLE SIGNAL : YES")
        print("==============================================")

        return signal

    print()
    print("ELIGIBLE SIGNAL : NO")

    if direction == "NONE":
        print("REASON          : direction=NONE")

    elif state != "ACTIVE":
        print("REASON          : signal_state is not ACTIVE")

    else:
        print("REASON          : production signal not eligible")

    return None


def main():

    header()

    try:

        regime_contract, structural_state = load_inputs()

    except Exception as error:

        print("INPUT LOAD FAILED")
        print("ERROR TYPE :", type(error).__name__)
        print("ERROR      :", str(error))
        return 1

    eligible = []

    for asset in EXPECTED_ASSETS:

        signal = run_asset(
            asset,
            regime_contract,
            structural_state,
        )

        if signal is not None:

            eligible.append(signal)

    print()
    print("=" * 90)
    print("LIVE ELIGIBLE SIGNAL RESULT")
    print("=" * 90)

    print("ELIGIBLE COUNT :", len(eligible))

    if eligible:

        print()
        print("ELIGIBLE SIGNALS")
        print("----------------")

        for signal in eligible:

            print(
                "{} | {} | state={} | confidence={}".format(
                    signal.get("asset"),
                    signal.get("direction"),
                    signal.get("signal_state"),
                    signal.get("confidence"),
                )
            )

        print()
        print("NEXT FRONTIER : ORDER_INTENT")
        print("STATUS        : READY TO MOVE FORWARD")

        return 0

    print()
    print("NO ELIGIBLE SIGNAL GENERATED.")
    print()
    print("IMPORTANT:")
    print("This is NOT permission to restart forensic audits.")
    print("Next action is to fix ONLY the concrete runtime blocker")
    print("shown above, then rerun this same path.")

    return 2


if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except KeyboardInterrupt:

        print()
        print("INTERRUPTED")
        raise SystemExit(130)

    except Exception as error:

        print()
        print("=" * 90)
        print("UNEXPECTED RUNTIME FAILURE")
        print("=" * 90)
        print("ERROR TYPE :", type(error).__name__)
        print("ERROR      :", str(error))
        print()
        traceback.print_exc()
        raise SystemExit(1)