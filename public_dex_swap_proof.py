from __future__ import annotations

import requests
import json

RPC = "https://api.mainnet-beta.solana.com"

SIGNATURE = "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr"

RAYDIUM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"


def rpc(method, params):
    r = requests.post(
        RPC,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        },
        timeout=30,
    )
    r.raise_for_status()

    data = r.json()

    if data.get("error"):
        raise RuntimeError(data["error"])

    return data["result"]


def main():

    tx = rpc(
        "getTransaction",
        [
            SIGNATURE,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
                "commitment": "confirmed",
            },
        ],
    )

    if not tx:
        raise RuntimeError("TRANSACTION_NOT_FOUND")

    message = (tx.get("transaction") or {}).get("message") or {}
    meta = tx.get("meta") or {}

    print("ENGINE=PUBLIC_DEX_ONCHAIN_SWAP_PROOF_v0.1")
    print("SIGNATURE=", SIGNATURE)
    print("SLOT=", tx.get("slot"))
    print("BLOCK_TIME=", tx.get("blockTime"))

    # ---------------------------------------------------------
    # ACCOUNT KEYS
    # ---------------------------------------------------------

    print("\n=== ACCOUNT KEYS ===")

    keys = message.get("accountKeys") or []

    for i, item in enumerate(keys):

        if isinstance(item, dict):
            pubkey = item.get("pubkey")
            signer = item.get("signer")
            writable = item.get("writable")
        else:
            pubkey = item
            signer = None
            writable = None

        print(
            i,
            pubkey,
            "SIGNER=", signer,
            "WRITABLE=", writable,
        )

    # ---------------------------------------------------------
    # TOP LEVEL INSTRUCTIONS
    # ---------------------------------------------------------

    print("\n=== TOP LEVEL INSTRUCTIONS ===")

    for i, instruction in enumerate(
        message.get("instructions") or []
    ):

        program_id = instruction.get("programId")
        program = instruction.get("program")

        print("\nINSTRUCTION=", i)
        print("PROGRAM=", program)
        print("PROGRAM_ID=", program_id)

        parsed = instruction.get("parsed")

        if isinstance(parsed, dict):
            print(
                "PARSED=",
                json.dumps(
                    parsed,
                    ensure_ascii=False,
                ),
            )

        accounts = instruction.get("accounts")

        if accounts:
            print("RAW_ACCOUNTS=")

            for n, account in enumerate(accounts):
                print(" ", n, account)

    # ---------------------------------------------------------
    # INNER INSTRUCTIONS
    # ---------------------------------------------------------

    print("\n=== RAYDIUM INNER INSTRUCTIONS ===")

    for group in meta.get("innerInstructions") or []:

        for n, instruction in enumerate(
            group.get("instructions") or []
        ):

            if instruction.get("programId") != RAYDIUM:
                continue

            print(
                "INNER_RAYDIUM_GROUP=",
                group.get("index"),
                "POSITION=",
                n,
            )

            print(
                json.dumps(
                    instruction,
                    ensure_ascii=False,
                    indent=2,
                )
            )

    # ---------------------------------------------------------
    # TOKEN TRANSFERS
    # ---------------------------------------------------------

    print("\n=== TOKEN TRANSFERS ===")

    for group in meta.get("innerInstructions") or []:

        for instruction in group.get("instructions") or []:

            parsed = instruction.get("parsed")

            if not isinstance(parsed, dict):
                continue

            if parsed.get("type") not in (
                "transfer",
                "transferChecked",
            ):
                continue

            info = parsed.get("info") or {}

            print(
                json.dumps(
                    {
                        "group": group.get("index"),
                        "type": parsed.get("type"),
                        "authority": info.get("authority"),
                        "source": info.get("source"),
                        "destination": info.get("destination"),
                        "mint": info.get("mint"),
                        "tokenAmount": info.get(
                            "tokenAmount"
                        ),
                        "amount": info.get("amount"),
                    },
                    ensure_ascii=False,
                )
            )

    # ---------------------------------------------------------
    # RAYDIUM LOGS
    # ---------------------------------------------------------

    print("\n=== RAYDIUM LOGS ===")

    for log in meta.get("logMessages") or []:

        if RAYDIUM in log or "ray_log:" in log:
            print(log)

    # ---------------------------------------------------------
    # PROVENANCE
    # ---------------------------------------------------------

    print("\n=== PROVENANCE ===")
    print("SOURCE_ID=SOLANA_MAINNET_RAYDIUM_AMM_V4")
    print("SOURCE_TYPE=DEX_ONCHAIN")
    print("SOURCE_TIMESTAMP=", tx.get("blockTime"))

    print("\n=== DECISION ===")
    print("SWAP_PAIR_PROOF=NOT_YET_COMMITTED")
    print("PRICE_OBSERVATION=NOT_YET_COMMITTED")
    print("CANONICAL_OHLCV=NOT_YET_COMMITTED")
    print("DB_WRITES=0")
    print("BLENDED=False")


if __name__ == "__main__":
    main()
