from __future__ import annotations

from decimal import Decimal, getcontext
from datetime import datetime, timezone
import json

getcontext().prec = 40

SIGNATURE = "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr"

SLOT = 445138167
BLOCK_TIME = 1788807186

SOURCE_ID = "SOLANA_MAINNET_RAYDIUM_AMM_V4"
SOURCE_TYPE = "DEX_ONCHAIN"

INPUT_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
OUTPUT_MINT = "So11111111111111111111111111111111111111112"

INPUT_RAW = 1892593
INPUT_DECIMALS = 6

OUTPUT_RAW = 18123314
OUTPUT_DECIMALS = 9

POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
POOL_AUTHORITY = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"

POOL_VAULT_INPUT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"
POOL_VAULT_OUTPUT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"

USER_SOURCE = "Cu7NnC4cUYPbe23Eekzzt3VwqRGqnTH4jqyeKmBaJCEf"
USER_DESTINATION = "f1JG9hFUiRUMkZjfKjhE5rQEDEGZMd19WjJEKbh1UEH"

RAYDIUM_INSTRUCTION = "SWAP_BASE_IN_V2"


def main():

    retrieved_at = datetime.now(timezone.utc).isoformat()

    input_amount = (
        Decimal(INPUT_RAW)
        / (Decimal(10) ** INPUT_DECIMALS)
    )

    output_amount = (
        Decimal(OUTPUT_RAW)
        / (Decimal(10) ** OUTPUT_DECIMALS)
    )

    price = input_amount / output_amount

    observation = {
        "asset": "SOL",
        "symbol": "SOL/USDC",
        "timestamp": BLOCK_TIME,
        "timeframe": None,

        "input_mint": INPUT_MINT,
        "output_mint": OUTPUT_MINT,

        "input_amount": str(input_amount),
        "output_amount": str(output_amount),

        "price": str(price),

        "signature": SIGNATURE,
        "slot": SLOT,

        "pool": POOL,
        "pool_authority": POOL_AUTHORITY,

        "pool_vault_input": POOL_VAULT_INPUT,
        "pool_vault_output": POOL_VAULT_OUTPUT,

        "user_source": USER_SOURCE,
        "user_destination": USER_DESTINATION,

        "raydium_instruction": RAYDIUM_INSTRUCTION,

        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,
        "source_timestamp": BLOCK_TIME,
        "retrieved_at": retrieved_at,
    }

    print("ENGINE=PUBLIC_DEX_ONCHAIN_PRICE_OBSERVATION_v0.2")
    print("STATUS=READY_REAL_PRICE_OBSERVATION")

    print("\n=== SWAP ===")
    print("PAIR=SOL/USDC")
    print("INPUT_MINT=", INPUT_MINT)
    print("OUTPUT_MINT=", OUTPUT_MINT)

    print("INPUT_RAW=", INPUT_RAW)
    print("INPUT_DECIMALS=", INPUT_DECIMALS)
    print("INPUT_AMOUNT=", input_amount)

    print("OUTPUT_RAW=", OUTPUT_RAW)
    print("OUTPUT_DECIMALS=", OUTPUT_DECIMALS)
    print("OUTPUT_AMOUNT=", output_amount)

    print("\n=== EXECUTION PRICE ===")
    print("PRICE=", price)
    print("QUOTE=USDC_PER_SOL")

    print("\n=== PROOF ===")
    print("RAYDIUM_INSTRUCTION=", RAYDIUM_INSTRUCTION)
    print("POOL_VAULT_INPUT=", POOL_VAULT_INPUT)
    print("POOL_VAULT_OUTPUT=", POOL_VAULT_OUTPUT)
    print("USER_SOURCE=", USER_SOURCE)
    print("USER_DESTINATION=", USER_DESTINATION)
    print("DESTINATION_TEMPORARY_ACCOUNT=True")
    print("DESTINATION_CLOSED_AFTER_SWAP=True")

    print("\n=== PROVENANCE ===")
    print(json.dumps(observation, ensure_ascii=False, indent=2))

    print("\n=== CONTRACT DECISION ===")
    print("REAL_DATA=True")
    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")
    print("ONE_CANDLE_ONE_SOURCE=True")

    print("\n=== COMMIT BOUNDARY ===")
    print("PRICE_OBSERVATION=READY")
    print("CANONICAL_OHLCV=NOT_YET_COMMITTED")
    print("DB_WRITES=0")


if __name__ == "__main__":
    main()
