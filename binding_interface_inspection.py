import importlib
import inspect

names = [
    "rolling_context_adapter_v0_1",
    "feature_contract",
    "feature_engine",
    "market_structure_engine",
    "indicator_engine",
]

print("=" * 90)
print("ARUNDA BINDING INTERFACE INSPECTION")
print("=" * 90)

for name in names:
    print()
    print("MODULE:", name)

    try:
        m = importlib.import_module(name)

        print("FILE:", getattr(m, "__file__", None))

        print("FUNCTIONS:")
        for x in dir(m):
            if x.startswith("_"):
                continue

            obj = getattr(m, x, None)

            if callable(obj):
                try:
                    print(" ", x, inspect.signature(obj))
                except Exception:
                    print(" ", x, "(signature unavailable)")

        print("CLASSES:")
        for x in dir(m):
            if x.startswith("_"):
                continue

            obj = getattr(m, x, None)

            if isinstance(obj, type):
                print(" ", x)

    except Exception as e:
        print("IMPORT ERROR:", type(e).__name__, str(e))

print()
print("=" * 90)
print("INSPECTION COMPLETE")
print("=" * 90)
