import inspect
import signal_logic
import signal_engine


ASSETS = ["XRP", "SOL", "ETH"]


print("=" * 82)
print("ARUNDA TRADER — VALIDATE_STRUCTURE TREND CONTRACT TRACE")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("ORDER     : NO")
print()

# -------------------------------------------------------------------------
# SOURCE
# -------------------------------------------------------------------------

source = inspect.getsource(signal_logic.validate_structure)

print("FUNCTION :", signal_logic.validate_structure.__name__)
print("FILE     :", inspect.getsourcefile(signal_logic.validate_structure))
print("LINE     :", inspect.getsourcelines(signal_logic.validate_structure)[1])
print()
print("VALIDATE_STRUCTURE SOURCE")
print("-" * 82)
print(source)
print("-" * 82)
print()

# -------------------------------------------------------------------------
# REAL RUNTIME STRUCTURAL STATE
# -------------------------------------------------------------------------

structural_state = signal_engine.load_structural_state()

for asset in ASSETS:

    print("-" * 82)
    print(asset)

    structural_data = structural_state[asset]
    structure = structural_data.get("structure")

    print("STRUCTURE TYPE :", type(structure).__name__)
    print("STRUCTURE KEYS :", list(structure.keys()))

    trend = structure.get("trend")

    print("TREND VALUE    :", repr(trend))
    print("TREND TYPE     :", type(trend).__name__)

    try:

        signal_logic.validate_structure(structure)

        print("VALIDATION     : ACCEPTED")

    except Exception as error:

        print("VALIDATION     : REJECTED")
        print("ERROR TYPE     :", type(error).__name__)
        print("ERROR          :", str(error))

print()
print("=" * 82)
print("TRACE COMPLETE")
print("FIRST MISMATCH  : structure.trend")
print("REPAIR          : NONE")
print("DB WRITE        : NONE")
print("SYNTHETIC       : NO")
print("ORDER           : NONE")
print("=" * 82)