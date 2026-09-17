import signal_logic


print("=" * 82)
print("ARUNDA TRADER — TREND EXPECTED CONTRACT")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("ORDER     : NO")
print()

print("FUNCTION SOURCE :", signal_logic.__file__)
print()

print("EXPECTED_TYPES['trend']")
print("-" * 82)
print("VALUE :", repr(signal_logic.EXPECTED_TYPES["trend"]))
print("TYPE  :", type(signal_logic.EXPECTED_TYPES["trend"]).__name__)
print()

print("VALID_VALUES['trend']")
print("-" * 82)
print("VALUE :", repr(signal_logic.VALID_VALUES["trend"]))
print("TYPE  :", type(signal_logic.VALID_VALUES["trend"]).__name__)
print()

print("EXPECTED FIELDS")
print("-" * 82)
print(repr(signal_logic.EXPECTED_FIELDS))
print()

print("=" * 82)
print("RESULT")
print("=" * 82)
print("ACTUAL RUNTIME TREND : None")
print("CONTRACT ABOVE       : AUTHORITATIVE")
print("REPAIR                : NOT PERFORMED")
print("DB WRITE              : NONE")
print("=" * 82)