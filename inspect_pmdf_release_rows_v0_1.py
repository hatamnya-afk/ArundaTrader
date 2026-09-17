from pathlib import Path
import sqlite3
import json

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"

def main():
    if not FABRIC_DB.exists():
        print("FABRIC_DB_EXISTS=False")
        return

    print("FABRIC_DB_EXISTS=True")
    print(f"FABRIC_DB={FABRIC_DB}")

    con = sqlite3.connect(
        f"file:{FABRIC_DB.as_posix()}?mode=ro",
        uri=True
    )
    con.row_factory = sqlite3.Row

    try:
        rows = con.execute("""
            SELECT
                asset,
                symbol,
                timestamp,
                timeframe,
                source_id,
                source_type,
                source_timestamp,
                observation_count,
                observation_signatures,
                observation_slots,
                pool,
                raydium_instruction
            FROM canonical_ohlcv
            ORDER BY timestamp, asset, symbol
        """).fetchall()

        print(f"ROWS={len(rows)}")

        for i, r in enumerate(rows, 1):
            print(f"\n--- ROW_{i} ---")
            print(f"asset={r['asset']}")
            print(f"symbol={r['symbol']}")
            print(f"timestamp={r['timestamp']}")
            print(f"timeframe={r['timeframe']}")
            print(f"source_id={r['source_id']}")
            print(f"source_type={r['source_type']}")
            print(f"source_timestamp={r['source_timestamp']}")
            print(f"observation_count={r['observation_count']}")
            print(f"observation_signatures={r['observation_signatures']}")
            print(f"observation_slots={r['observation_slots']}")
            print(f"pool={r['pool']}")
            print(f"raydium_instruction={r['raydium_instruction']}")

    finally:
        con.close()

    print("\nREAD_ONLY=True")
    print("DB_WRITES=0")


if __name__ == "__main__":
    main()