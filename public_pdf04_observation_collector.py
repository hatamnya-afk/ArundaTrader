from __future__ import annotations

import base64
import struct
import requests
from datetime import datetime, timezone
from decimal import Decimal, getcontext

getcontext().prec = 40

RPC = "https://api.mainnet-beta.solana.com"

RAYDIUM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL = "So11111111111111111111111111111111111111112"

POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"

SIGNATURE_LIMIT = 100


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


def b58_decode(value):

    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    number = 0

    for char in value:
        number = number * 58 + alphabet.index(char)

    raw = number.to_bytes(
        (number.bit_length() + 7) // 8,
        "big",
    )

    zeros = 0

    for char in value:
        if char == "1":
            zeros += 1
        else:
            break

    return b"\x00" * zeros + raw


def u64(data, offset):

    if len(data) < offset + 8:
        return None

    return struct.unpack_from(
        "<Q",
        data,
        offset,
    )[0]


def token_amount(raw, decimals):

    return (
        Decimal(raw)
        / (Decimal(10) ** decimals)
    )


def main():

    retrieved_at = datetime.now(timezone.utc).isoformat()

    print(
        "ENGINE=PUBLIC_CANONICAL_OHLCV_OBSERVATION_COLLECTOR_v0.1"
    )
    print("STATUS=READ_ONLY_REAL_TRANSACTION_COLLECTION")

    print("\n=== CONFIG ===")
    print("RPC=", RPC)
    print("RAYDIUM=", RAYDIUM)
    print("POOL=", POOL)
    print("PAIR=SOL/USDC")
    print("SIGNATURE_LIMIT=", SIGNATURE_LIMIT)

    signatures = rpc(
        "getSignaturesForAddress",
        [
            POOL,
            {
                "limit": SIGNATURE_LIMIT,
                "commitment": "confirmed",
            },
        ],
    )

    print("\nSIGNATURES_FOUND=", len(signatures))

    observations = []

    transactions_checked = 0

    raydium_swaps = 0

    pair_observations = 0

    for item in signatures:

        signature = item.get("signature")

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

        if not tx:
            continue

        transactions_checked += 1

        meta = tx.get("meta") or {}

        inner_groups = meta.get("innerInstructions") or []

        for group in inner_groups:

            for instruction in group.get("instructions") or []:

                if instruction.get("programId") != RAYDIUM:
                    continue

                encoded = instruction.get("data")

                accounts = instruction.get("accounts") or []

                if not encoded:
                    continue

                raw = b58_decode(encoded)

                if len(raw) < 17:
                    continue

                discriminator = raw[0]

                if discriminator != 16:
                    continue

                raydium_swaps += 1

                amount_in_raw = u64(raw, 1)
                minimum_out_raw = u64(raw, 9)

                if amount_in_raw is None:
                    continue

                if len(accounts) < 8:
                    continue

                user_source = accounts[5]
                user_destination = accounts[6]

                pool_vault_a = accounts[3]
                pool_vault_b = accounts[4]

                pre = {
                    x.get("accountIndex"): x
                    for x in meta.get("preTokenBalances", [])
                }

                post = {
                    x.get("accountIndex"): x
                    for x in meta.get("postTokenBalances", [])
                }

                deltas = []

                for idx in sorted(set(pre) | set(post)):

                    before = pre.get(idx, {})
                    after = post.get(idx, {})

                    b = before.get("uiTokenAmount") or {}
                    a = after.get("uiTokenAmount") or {}

                    raw_before = b.get("amount")
                    raw_after = a.get("amount")

                    if raw_before is None or raw_after is None:
                        continue

                    delta = int(raw_after) - int(raw_before)

                    if delta == 0:
                        continue

                    mint = (
                        after.get("mint")
                        or before.get("mint")
                    )

                    decimals = (
                        a.get("decimals")
                        if a.get("decimals") is not None
                        else b.get("decimals")
                    )

                    deltas.append(
                        {
                            "index": idx,
                            "mint": mint,
                            "delta": delta,
                            "decimals": decimals,
                        }
                    )

                usdc_out = None
                wsol_out = None

                for d in deltas:

                    if d["mint"] == USDC and d["delta"] < 0:
                        usdc_out = -d["delta"]

                    if d["mint"] == WSOL and d["delta"] > 0:
                        wsol_out = d["delta"]

                if usdc_out is None or wsol_out is None:
                    continue

                usdc = token_amount(usdc_out, 6)
                sol = token_amount(wsol_out, 9)

                if sol <= 0:
                    continue

                price = usdc / sol

                observation = {
                    "asset": "SOL",
                    "symbol": "SOL/USDC",
                    "timestamp": tx.get("blockTime"),
                    "slot": tx.get("slot"),
                    "signature": signature,

                    "input_mint": USDC,
                    "output_mint": WSOL,

                    "input_amount": str(usdc),
                    "output_amount": str(sol),
                    "price": str(price),

                    "pool": POOL,

                    "pool_vault_a": pool_vault_a,
                    "pool_vault_b": pool_vault_b,

                    "user_source": user_source,
                    "user_destination": user_destination,

                    "raydium_instruction":
                        "SWAP_BASE_IN_V2",

                    "source_id":
                        "SOLANA_MAINNET_RAYDIUM_AMM_V4",

                    "source_type":
                        "DEX_ONCHAIN",

                    "source_timestamp":
                        tx.get("blockTime"),

                    "retrieved_at":
                        retrieved_at,
                }

                observations.append(observation)

                pair_observations += 1

                print("\nOBSERVATION=", pair_observations)
                print("SIGNATURE=", signature)
                print("SLOT=", tx.get("slot"))
                print("BLOCK_TIME=", tx.get("blockTime"))
                print("USDC=", usdc)
                print("SOL=", sol)
                print("PRICE=", price)

    print("\n=== COLLECTION RESULT ===")

    print("TRANSACTIONS_CHECKED=", transactions_checked)
    print("RAYDIUM_SWAP_BASE_IN_V2=", raydium_swaps)
    print("PAIR_OBSERVATIONS=", pair_observations)

    timestamps = sorted({
        x["timestamp"]
        for x in observations
        if x["timestamp"] is not None
    })

    print("UNIQUE_TIMESTAMPS=", len(timestamps))

    hours = sorted({
        int(ts // 3600) * 3600
        for ts in timestamps
    })

    print("HOUR_BUCKETS=", len(hours))

    for hour in hours:
        count = sum(
            1
            for x in observations
            if x["timestamp"] is not None
            and int(x["timestamp"] // 3600) * 3600 == hour
        )

        print(
            "HOUR_BUCKET=",
            hour,
            "OBSERVATIONS=",
            count,
        )

    print("\n=== CONTRACT ===")

    print("REAL_DATA=True")
    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")

    print("\n=== COMMIT ===")

    print("DB_WRITES=0")
    print("CANONICAL_OHLCV_COMMITTED=False")
    print("STATUS=COLLECTION_COMPLETE")

    if pair_observations == 0:
        print("FAIL_CLOSED=TRUE")
        print("REASON=NO_PROVEN_SOL_USDC_OBSERVATIONS")

    elif len(hours) == 0:
        print("FAIL_CLOSED=TRUE")
        print("REASON=NO_VALID_HOUR_BUCKETS")

    else:
        print("FAIL_CLOSED=FALSE")
        print("REASON=OBSERVATIONS_AVAILABLE_FOR_PDF04_REVIEW")


if __name__ == "__main__":
    main()
