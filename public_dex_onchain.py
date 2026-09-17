from __future__ import annotations

import requests
from datetime import datetime, timezone

RPC = "https://api.mainnet-beta.solana.com"
ENGINE = "PUBLIC_DEX_ONCHAIN_INGESTION_v0.2"

RAYDIUM_AMM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
LIMIT = 5


def rpc(method, params):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    r = requests.post(RPC, json=payload, timeout=30)

    print("RPC_HTTP=", r.status_code)

    r.raise_for_status()

    data = r.json()

    if data.get("error") is not None:
        raise RuntimeError(data["error"])

    return data["result"]


def main():
    retrieved_at = datetime.now(timezone.utc).isoformat()

    print("ENGINE=", ENGINE)
    print("RPC=", RPC)

    # 1. Verify live finalized chain.
    blockhash = rpc(
        "getLatestBlockhash",
        [{"commitment": "finalized"}],
    )

    print("RPC_STATUS=READY")
    print("BLOCK_HEIGHT=",
          blockhash["value"]["lastValidBlockHeight"])

    # 2. Get only recent signatures involving the DEX program.
    signatures = rpc(
        "getSignaturesForAddress",
        [
            RAYDIUM_AMM_V4,
            {
                "limit": LIMIT,
                "commitment": "confirmed",
            },
        ],
    )

    print("SIGNATURES=", len(signatures))

    if not signatures:
        raise RuntimeError("NO_RECENT_RAYDIUM_ACTIVITY")

    # 3. Retrieve individual real transactions.
    transactions = []

    for item in signatures:
        signature = item["signature"]

        tx = rpc(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed",
                },
            ],
        )

        if tx is not None:
            transactions.append(
                {
                    "signature": signature,
                    "slot": tx.get("slot"),
                    "block_time": tx.get("blockTime"),
                    "meta": tx.get("meta"),
                    "transaction": tx.get("transaction"),
                }
            )

    print("TRANSACTIONS=", len(transactions))

    # 4. Runtime evidence only.
    # No OHLCV claim yet.
    # No database write.
    # No blending.
    print("\n=== PDF-03 RUNTIME ===")
    print("STATUS=READY_RAW_ONCHAIN")
    print("SOURCE_ID=SOLANA_MAINNET_RAYDIUM_AMM_V4")
    print("SOURCE_TYPE=DEX_ONCHAIN")
    print("RAW_TRANSACTIONS=", len(transactions))
    print("PROVENANCE_RETRIEVED_AT=", retrieved_at)
    print("DB_WRITES=0")
    print("ORDERS_SUBMITTED=0")
    print("BLENDED=False")

    for i, tx in enumerate(transactions, 1):
        print(
            "TX",
            i,
            "SIGNATURE=", tx["signature"],
            "SLOT=", tx["slot"],
            "BLOCK_TIME=", tx["block_time"],
        )


if __name__ == "__main__":
    main()
