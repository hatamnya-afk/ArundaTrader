from pathlib import Path

p = Path("market_arm_contiguous_history_accumulation_v0_2.py")
s = p.read_text(encoding="utf-8")

old = '''        WHERE UPPER(asset)=?
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (asset, TIMEFRAME, LAUNCH_TS)
'''

new = '''        WHERE UPPER(asset)=?
          AND symbol=?
          AND source_id=?
          AND source_type=?
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (
            asset,
            asset + "/USDT",
            "KUCOIN_SPOT:" + asset + "-USDT",
            "CEX_PUBLIC_API",
            TIMEFRAME,
            LAUNCH_TS,
        )
'''

if old not in s:
    raise RuntimeError("LOAD_ROWS_TARGET_NOT_FOUND")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("=" * 100)
print("PATCH=MARKET_IDENTITY_SCOPE")
print("=" * 100)
print("ARM_MARKET_SCOPE=KUCOIN_SPOT:<ASSET>-USDT")
print("SOL_USDT=IN_SCOPE")
print("SOL_USDC=OUT_OF_SCOPE")
print("ASSET_ONLY_MERGE=FALSE")
print("RUNTIME_EXECUTED=FALSE")
print("FABRIC_MODIFIED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
print("SIGNAL_CHAIN_EXECUTED=FALSE")
print("FUSION_EXECUTED=FALSE")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
