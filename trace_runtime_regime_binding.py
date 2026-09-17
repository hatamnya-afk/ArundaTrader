# -*- coding: utf-8 -*-
"""
ARUNDA TRADER — RUNTIME REGIME BINDING CHECK
READ ONLY — NO DB WRITE — NO SYNTHETIC DATA — NO ORDER
"""

import inspect
import signal_engine


ASSETS = ("XRP", "SOL", "ETH")


def call_loader(asset):
    fn = signal_engine.load_regime_contract
    params = list(inspect.signature(fn).parameters)

    if len(params) == 0:
        return fn()

    if len(params) == 1:
        return fn(asset)

    raise RuntimeError(
        f"Unexpected load_regime_contract signature: {params}"
    )


def main():
    print("=" * 82)
    print("ARUNDA TRADER — RUNTIME REGIME BINDING CHECK")
    print("=" * 82)
    print("MODE      : READ ONLY")
    print("SYNTHETIC : NO")
    print("DB WRITE  : NO")
    print("ORDER     : NO")
    print()

    fn = signal_engine.load_regime_contract

    print(f"FUNCTION   : {inspect.getsourcefile(fn)}")
    print(f"LINE       : {inspect.getsourcelines(fn)[1]}")
    print(
        "SIGNATURE  : "
        f"{inspect.signature(fn)}"
    )
    print()

    for asset in ASSETS:
        try:
            data = call_loader(asset)

            print("-" * 82)
            print(f"{asset}")

            if not isinstance(data, dict):
                print(f"TYPE       : {type(data).__name__}")
                print("RESULT     : NON-DICT REGIME CONTRACT")
                continue

            status = data.get("status")

            print(f"STATUS     : {status}")
            print(f"KEYS       : {sorted(data.keys())}")

            if status == "READY":
                print("BINDING    : READY")
            else:
                print("BINDING    : NOT_READY")

        except Exception as e:
            print("-" * 82)
            print(f"{asset}")
            print(f"ERROR      : {type(e).__name__}: {e}")

    print()
    print("=" * 82)
    print("RESULT")
    print("Only runtime regime binding was inspected.")
    print("No repair performed.")
    print("DB WRITE    : NONE")
    print("SYNTHETIC   : NO")
    print("ORDER       : NONE")
    print("=" * 82)


if __name__ == "__main__":
    main()