import inspect
import opportunity_engine as m

print("=== OPPORTUNITY STATUS PRODUCER ===")
print("FUNCTION=determine_status")
print("SIGNATURE=")
print(inspect.signature(m.determine_status))

print()
print("=== SOURCE ===")
src = inspect.getsource(m.determine_status)

for i, line in enumerate(src.splitlines(), 1):
    print(f"{i}: {line}")

print()
print("=== MODULE CONSTANTS ===")
for name in dir(m):
    if any(x in name.upper() for x in [
        "THRESHOLD",
        "MIN_",
        "MAX_",
        "CONFIDENCE",
        "SCORE",
    ]):
        value = getattr(m, name)
        if isinstance(value, (int, float, str, bool)):
            print(f"{name}={value!r}")

print()
print("RUNTIME=FALSE")
print("DB_WRITES=0")
print("PRODUCTION_DB_TOUCHED=FALSE")
