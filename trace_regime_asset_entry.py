# trace_regime_asset_entry.py
# READ ONLY — NO DB WRITE — NO SYNTHETIC DATA

import signal_engine
import inspect

ASSETS = ("XRP", "SOL", "ETH")

print("=" * 82)
print("ARUNDA TRADER — REGIME ASSET ENTRY TRACE")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("ORDER     : NO")
print()

fn = signal_engine.load_regime_contract
print(f"FUNCTION : {inspect.getsourcefile(fn)}")
print(f"LINE     : {inspect.getsourcelines(fn)[1]}")
print()

regime_data = fn()

for asset in ASSETS:
    print("-" * 82)
    print(asset)

    entry = regime_data.get(asset)

    if entry is None:
        print("ENTRY     : MISSING")
        continue

    print(f"TYPE      : {type(entry).__name__}")

    if isinstance(entry, dict):
        print(f"KEYS      : {sorted(entry.keys())}")
        print(f"STATUS    : {entry.get('status')}")
        print(f"REGIME    : {entry.get('regime')}")
        print(f"READY     : {entry.get('ready')}")
    else:
        print(f"VALUE     : {entry!r}")

print()
print("=" * 82)
print("TRACE COMPLETE")
print("REPAIR    : NONE")
print("DB WRITE  : NONE")
print("SYNTHETIC : NO")
print("ORDER     : NONE")
print("=" * 82)