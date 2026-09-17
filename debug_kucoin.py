import importlib.util
from datetime import datetime, timezone
from pathlib import Path

p = Path("public_market_data_kucoin.py")

spec = importlib.util.spec_from_file_location(
    "kucoin_debug",
    p
)

m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

symbol = "BTC-USDT"

bars = m.fetch_kucoin(symbol, count=50)

print("RAW_BARS =", len(bars))

if not bars:
    raise RuntimeError("KUCOIN_RETURNED_ZERO_BARS")

print()
print("FIRST_RAW_BAR:")
print(bars[0])

print()
print("LAST_RAW_BAR:")
print(bars[-1])

print()
print("NORMALIZATION TEST")

retrieved_at = datetime.now(timezone.utc).isoformat()

for i, bar in enumerate(bars[:10]):

    print()
    print("BAR", i, bar)

    try:
        candle = m.normalize(
            "BTC",
            symbol,
            bar,
            retrieved_at,
        )

        print("NORMALIZE=PASS")
        print("TIMESTAMP=", candle["timestamp"])
        print("SOURCE_ID=", candle["source_id"])

        try:
            m.validate_candle(candle)
            print("VALIDATE=PASS")

        except Exception as exc:
            print(
                "VALIDATE=FAIL",
                type(exc).__name__,
                str(exc)
            )

    except Exception as exc:
        print(
            "NORMALIZE=FAIL",
            type(exc).__name__,
            str(exc)
        )
