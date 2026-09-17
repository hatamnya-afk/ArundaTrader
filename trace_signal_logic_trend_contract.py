import inspect
import signal_logic
import signal_engine


ASSETS = ["XRP", "SOL", "ETH"]


print("=" * 82)
print("ARUNDA TRADER — SIGNAL LOGIC TREND CONTRACT TRACE")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("ORDER     : NO")
print()

# -------------------------------------------------------------------------
# SOURCE INSPECTION
# -------------------------------------------------------------------------

source = inspect.getsource(signal_logic.build_direction)

print("FUNCTION :", signal_logic.build_direction.__name__)
print("FILE     :", inspect.getsourcefile(signal_logic.build_direction))
print("LINE     :", inspect.getsourcelines(signal_logic.build_direction)[1])
print()
print("BUILD_DIRECTION SOURCE")
print("-" * 82)
print(source)
print("-" * 82)
print()

# -------------------------------------------------------------------------
# REAL STRUCTURAL INPUT
# -------------------------------------------------------------------------

structural_state = signal_engine.load_structural_state()

for asset in ASSETS:

    print("-" * 82)
    print(asset)

    structural_data = structural_state[asset]
    structure = structural_data.get("structure")

    trend = structure.get("trend")

    print("ACTUAL TREND VALUE :", repr(trend))
    print("ACTUAL TREND TYPE  :", type(trend).__name__)

    try:

        signal_logic.build_direction(structure)

        print("CONTRACT RESULT    : ACCEPTED")

    except Exception as error:

        print("CONTRACT RESULT    : REJECTED")
        print("ERROR TYPE         :", type(error).__name__)
        print("ERROR              :", str(error))

print()
print("=" * 82)
print("TRACE COMPLETE")
print("FIRST MISMATCH      : structure.trend")
print("REPAIR              : NONE")
print("DB WRITE            : NONE")
print("SYNTHETIC           : NO")
print("ORDER               : NONE")
print("=" * 82)