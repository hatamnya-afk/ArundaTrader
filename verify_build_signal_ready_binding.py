import signal_engine


ASSETS = ["XRP", "SOL", "ETH"]


print("=" * 82)
print("ARUNDA TRADER — BUILD_SIGNAL READY BINDING VERIFICATION")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("ORDER     : NO")
print()

regime_contract = signal_engine.load_regime_contract()
structural_state = signal_engine.load_structural_state()

for asset in ASSETS:

    regime_data = regime_contract[asset]
    structural_data = structural_state[asset]

    print("-" * 82)
    print(asset)

    print("REGIME_DATA TYPE   :", type(regime_data).__name__)
    print("REGIME_DATA        :", repr(regime_data))
    print("STATUS             :", repr(regime_data.get("status")))
    print("REGIME             :", repr(regime_data.get("regime")))

    print(
        "READY CONDITION    :",
        regime_data.get("status") == "READY"
    )

    try:

        signal = signal_engine.build_signal(
            asset,
            regime_data,
            structural_data
        )

        print(
            "BUILD_SIGNAL       : SUCCESS"
        )

        print(
            "DIRECTION          :",
            signal.get("direction")
        )

    except Exception as error:

        print(
            "BUILD_SIGNAL       : FAILURE"
        )

        print(
            "ERROR TYPE         :",
            type(error).__name__
        )

        print(
            "ERROR              :",
            str(error)
        )

print()
print("=" * 82)
print("VERIFICATION COMPLETE")
print("REPAIR    : NONE")
print("DB WRITE  : NONE")
print("SYNTHETIC : NO")
print("ORDER     : NONE")
print("=" * 82)