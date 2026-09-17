from __future__ import annotations

import requests
import struct
import json

RPC = "https://api.mainnet-beta.solana.com"

SIGNATURE = "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr"

RAYDIUM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58_decode(value):
    number = 0

    for char in value:
        number = number * 58 + ALPHABET.index(char)

    raw = number.to_bytes(
        (number.bit_length() + 7) // 8,
        "big",
    )

    leading_zeros = 0

    for char in value:
        if char == "1":
            leading_zeros += 1
        else:
            break

    return b"\x00" * leading_zeros + raw


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


def u64(data, offset):

    if len(data) < offset + 8:
        return None

    return struct.unpack_from(
        "<Q",
        data,
        offset,
    )[0]


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

    meta = tx.get("meta") or {}

    print("ENGINE=PUBLIC_DEX_ONCHAIN_RAYDIUM_INSTRUCTION_DECODE_v0.2")
    print("STATUS=DECODING_REAL_RAYDIUM_INSTRUCTION")
    print("SIGNATURE=", SIGNATURE)
    print("SLOT=", tx.get("slot"))
    print("BLOCK_TIME=", tx.get("blockTime"))

    found = 0

    print("\n=== RAYDIUM RAW INSTRUCTIONS ===")

    for group in meta.get("innerInstructions") or []:

        for position, instruction in enumerate(
            group.get("instructions") or []
        ):

            if instruction.get("programId") != RAYDIUM:
                continue

            found += 1

            print("\nGROUP=", group.get("index"))
            print("POSITION=", position)

            accounts = instruction.get("accounts") or []
            encoded = instruction.get("data")

            print("ACCOUNT_COUNT=", len(accounts))
            print("DATA_BASE58=", encoded)

            if encoded:

                raw = base58_decode(encoded)

                print("DATA_BYTES=", len(raw))
                print("DATA_HEX=", raw.hex())
                print("FIRST_BYTE=", raw[0] if raw else None)

                print("\nU64_FIELDS_LE=")

                for offset in range(
                    1,
                    len(raw) - 7,
                    8,
                ):

                    print(
                        "OFFSET=",
                        offset,
                        "VALUE=",
                        u64(raw, offset),
                    )

                print("\nRAW_BYTES=")

                for i, byte in enumerate(raw):
                    print(i, byte)

            print("\nRAYDIUM_ACCOUNTS=")

            for i, account in enumerate(accounts):
                print(i, account)

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
                        "amount": info.get("amount"),
                        "tokenAmount": info.get(
                            "tokenAmount"
                        ),
                    },
                    ensure_ascii=False,
                )
            )

    print("\n=== RAYDIUM LOGS ===")

    for log in meta.get("logMessages") or []:

        if "ray_log:" in log:
            print(log)

    print("\n=== DECISION ===")

    print("RAYDIUM_INSTRUCTION_FOUND=", found)

    print("INSTRUCTION_TYPE=NOT_YET_COMMITTED")
    print("INPUT_AMOUNT=NOT_YET_COMMITTED")
    print("OUTPUT_AMOUNT=NOT_YET_COMMITTED")
    print("SWAP_PAIR_PROOF=NOT_YET_COMMITTED")
    print("PRICE_OBSERVATION=NOT_YET_COMMITTED")
    print("CANONICAL_OHLCV=NOT_YET_COMMITTED")

    print("DB_WRITES=0")
    print("BLENDED=False")


if __name__ == "__main__":
    main()
