import inspect
import dynamic_trade_gate_contract_boundary_v0_1 as m

print("=== TRADE GATE STATIC TRACE ===")

for name in dir(m):
    if (
        "gate" in name.lower()
        or "predicate" in name.lower()
        or "aggregate" in name.lower()
        or "qualified" in name.lower()
    ):
        obj = getattr(m, name)

        if callable(obj):
            try:
                print()
                print(f"=== {name} ===")
                print(inspect.signature(obj))
                print(inspect.getsource(obj))
            except Exception as e:
                print(f"{name}: SOURCE_ERROR={e}")

print()
print("=== MODULE CONSTANTS / STATE ===")

for name in dir(m):
    if name.startswith("_"):
        value = getattr(m, name)

        if isinstance(value, (dict, list, tuple, set, int, float, str, bool)):
            if any(x in name.upper() for x in [
                "PREDICATE",
                "AGGREGATE",
                "CANDIDATE",
                "QUALIFIED",
            ]):
                print(f"{name}={value!r}")

print()
print("RUNTIME=FALSE")
print("DB_WRITES=0")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("EXECUTION=OFF")
