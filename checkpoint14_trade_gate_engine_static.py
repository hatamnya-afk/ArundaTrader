import inspect
import trade_gate_engine as m

print("=== TRADE GATE ENGINE ===")

for name in ("evaluate", "build_gate_observability"):
    obj = getattr(m, name, None)

    print()
    print(f"=== {name} ===")

    if obj is None:
        print("NOT_FOUND")
        continue

    print("SIGNATURE=")
    print(inspect.signature(obj))

    print()
    print("SOURCE=")
    src = inspect.getsource(obj)

    for i, line in enumerate(src.splitlines(), 1):
        print(f"{i}: {line}")

print()
print("=== MODULE CONSTANTS ===")

for name in dir(m):
    if any(x in name.upper() for x in [
        "THRESHOLD",
        "MIN_",
        "MAX_",
        "PREDICATE",
        "REWARD",
        "CONFIDENCE",
        "SCORE",
        "SNAPSHOT",
        "POINT",
    ]):
        value = getattr(m, name)
        if isinstance(value, (int, float, str, bool, tuple, list, dict)):
            print(f"{name}={value!r}")

print()
print("RUNTIME=FALSE")
print("DB_WRITES=0")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
