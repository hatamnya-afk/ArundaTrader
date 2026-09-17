import json
import inspect
import dynamic_opportunity_universe_boundary_v0_1 as m

print("=== OPPORTUNITY PRODUCER STATIC EXTRACTION ===")
print("FUNCTION=build_dynamic_opportunities")
print("READY_FUNCTION=ready_opportunities")
print()

print("=== build_dynamic_opportunities SIGNATURE ===")
print(inspect.signature(m.build_dynamic_opportunities))

print()
print("=== ready_opportunities SIGNATURE ===")
print(inspect.signature(m.ready_opportunities))

print()
print("=== SOURCE REFERENCES ===")

src = inspect.getsource(m.build_dynamic_opportunities)

for i, line in enumerate(src.splitlines(), 1):
    if any(x in line.lower() for x in [
        "status",
        "confidence",
        "direction",
        "score",
        "opportunity",
    ]):
        print(f"{i}: {line}")

print()
print("=== CONTRACT CHECK ===")

try:
    result = m.static_contract_check()
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print(f"STATIC_CONTRACT_CHECK_ERROR={type(e).__name__}: {e}")

print()
print("RUNTIME=FALSE")
print("DB_WRITES=0")
print("PRODUCTION_DB_TOUCHED=FALSE")
