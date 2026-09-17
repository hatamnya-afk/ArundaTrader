import inspect
import opportunity_engine as m

print("=== OPPORTUNITY ENGINE ===")
print("FUNCTION=build_opportunity")
print("SIGNATURE=")
print(inspect.signature(m.build_opportunity))

print()
print("=== SOURCE ===")
src = inspect.getsource(m.build_opportunity)

for i, line in enumerate(src.splitlines(), 1):
    print(f"{i}: {line}")
