import signal_engine
import signal_logic


ASSETS = ["XRP", "SOL", "ETH"]


print("=" * 82)
print("ARUNDA TRADER — STRUCTURAL TREND CONTRACT TRACE")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("ORDER     : NO")
print()

structural_state = signal_engine.load_structural_state()

for asset in ASSETS:

    print("-" * 82)
    print(asset)

    structural_data = structural_state[asset]

    print("STRUCTURAL TYPE :", type(structural_data).__name__)
    print("STRUCTURAL KEYS  :", list(structural_data.keys()))

    structure = structural_data.get("structure")

    print("STRUCTURE TYPE   :", type(structure).__name__)

    if not isinstance(structure, dict):
        print("RESULT           : FAIL — structure is not dict")
        continue

    print("STRUCTURE KEYS   :", list(structure.keys()))

    trend = structure.get("trend")

    print("TREND VALUE      :", repr(trend))
    print("TREND TYPE       :", type(trend).__name__)

    print()
    print("DIRECT CALL TO signal_logic.build_direction()")

    try:
        direction = signal_logic.build_direction(structure)

        print("RESULT           : SUCCESS")
        print("DIRECTION        :", repr(direction))

    except Exception as error:

        print("RESULT           : FAILURE")
        print("ERROR TYPE       :", type(error).__name__)
        print("ERROR            :", str(error))

print()
print("=" * 82)
print("TRACE COMPLETE")
print("REPAIR    : NONE")
print("DB WRITE  : NONE")
print("SYNTHETIC : NO")
print("ORDER     : NONE")
print("=" * 82)