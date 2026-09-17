from __future__ import annotations

import requests
from datetime import datetime, timezone

RPC = "https://api.mainnet-beta.solana.com"
ENGINE = "PUBLIC_DEX_ONCHAIN_OBSERVATION_v0.2"

RAYDIUM_AMM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
SIGNATURES = [
    "eUEWhcc9aMePhatSNTFYAZy8zBrqdNSG2MFZwnyuxzYZ5n77GgB3wvZTCYKTpbXXquvvwNQSjiZ4BxEDkxMu1C3",
    "2AXdMLHrb8hcR4Vb2ztu4eFqQTwphEVbFAr4iYTaqE2zoYYum3BeXAGkNuBs4AvGnxDksP3DcV1APbj9fLcV55GG",
    "2YdM9Ayvsg5YZJH8WfauzgKxov2cM8cJSECZKiwhTp2jXPfQzdxTgb4KvvXrehkUesjTLzCBLpH1izn2kUL3fkX8",
    "4mSu7DvSoCSye1onotKmB8yREnaiqzVWZsKNF6R7DJ8Jr6mxsNj4gcwU5KsWe1QzJbihRkXMBgEtaSP6Qz2FwAET",
    "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr",
]


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
    retrieved_at = datetime.now(timezone.utc).isoformat()

    print("ENGINE=", ENGINE)

    valid_raydium = 0
    token_delta_count = 0

    for signature in SIGNATURES:

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
            print("\nTX=", signature)
            print("STATUS=MISSING")
            continue

        meta = tx.get("meta") or {}
        transaction = tx.get("transaction") or {}
        message = transaction.get("message") or {}

        account_keys = message.get("accountKeys") or []
        instructions = message.get("instructions") or []

        logs = meta.get("logMessages") or []
        inner = meta.get("innerInstructions") or []

        program_invoked = False

        for log in logs:
            if RAYDIUM_AMM_V4 in str(log):
                program_invoked = True
                break

        for instruction in instructions:
            if instruction.get("programId") == RAYDIUM_AMM_V4:
                program_invoked = True

        for group in inner:
            for instruction in group.get("instructions") or []:
                if instruction.get("programId") == RAYDIUM_AMM_V4:
                    program_invoked = True

        deltas = []

        pre = {
            x.get("accountIndex"): x
            for x in meta.get("preTokenBalances", [])
        }

        post = {
            x.get("accountIndex"): x
            for x in meta.get("postTokenBalances", [])
        }

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

            token_delta_count += 1

            deltas.append({
                "account_index": idx,
                "mint": after.get("mint") or before.get("mint"),
                "delta_raw": delta,
                "owner": after.get("owner") or before.get("owner"),
            })

        print("\nTX=", signature)
        print("SLOT=", tx.get("slot"))
        print("BLOCK_TIME=", tx.get("blockTime"))
        print("RAYDIUM_PROGRAM_INVOKED=", program_invoked)
        print("INNER_GROUPS=", len(inner))
        print("TOKEN_DELTAS=", len(deltas))

        if logs:
            ray_logs = [
                x for x in logs
                if "Raydium" in x
                or RAYDIUM_AMM_V4 in x
                or "ray_log" in x
            ]

            print("RAYDIUM_LOGS=", len(ray_logs))

            for log in ray_logs[:10]:
                print("  LOG=", log)

        for d in deltas[:20]:
            print(
                "  DELTA",
                "INDEX=", d["account_index"],
                "MINT=", d["mint"],
                "RAW_DELTA=", d["delta_raw"],
            )

        if program_invoked and len(deltas) >= 2:
            valid_raydium += 1
            print("OBSERVATION_CANDIDATE=YES")
        else:
            print("OBSERVATION_CANDIDATE=NO")

    print("\n=== PDF-03 OBSERVATION RUNTIME ===")
    print("STATUS=READY_RAW_TRANSACTION_ANALYSIS")
    print("SOURCE_ID=SOLANA_MAINNET_RAYDIUM_AMM_V4")
    print("SOURCE_TYPE=DEX_ONCHAIN")
    print("TRANSACTIONS_ANALYZED=", len(SIGNATURES))
    print("RAYDIUM_SWAP_CANDIDATES=", valid_raydium)
    print("TOKEN_DELTAS_TOTAL=", token_delta_count)
    print("PRICE_OBSERVATIONS=0")
    print("CANONICAL_BARS=0")
    print("DB_WRITES=0")
    print("BLENDED=False")
    print("PROVENANCE_RETRIEVED_AT=", retrieved_at)


if __name__ == "__main__":
    main()
