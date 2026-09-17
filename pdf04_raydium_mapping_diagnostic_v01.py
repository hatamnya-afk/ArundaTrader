from __future__ import annotations

import json
import ssl
import certifi
from urllib.request import Request, urlopen


RPC = "https://api.mainnet-beta.solana.com"

SIGNATURE = (
    "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr"
)

RAYDIUM = (
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
)

SSL_CONTEXT = ssl.create_default_context(
    cafile=certifi.where()
)


def rpc(method, params):

    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")

    request = Request(
        RPC,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ArundaTrader-PDF04-DIAGNOSTIC",
        },
        method="POST",
    )

    with urlopen(
        request,
        timeout=30,
        context=SSL_CONTEXT,
    ) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

    if data.get("error"):
        raise RuntimeError(
            data["error"]
        )

    return data["result"]


def address(value):

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return value.get("pubkey")

    return None


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
        raise RuntimeError(
            "TRANSACTION_NOT_FOUND"
        )

    message = (
        tx.get("transaction", {})
        .get("message", {})
    )

    meta = tx.get("meta") or {}

    keys = message.get(
        "accountKeys"
    ) or []

    addresses = {
        i: address(item)
        for i, item in enumerate(keys)
    }

    print(
        "ENGINE=PDF04_RAYDIUM_MAPPING_DIAGNOSTIC_v0.1"
    )
    print("MODE=READ_ONLY")
    print("DB_WRITES=0")
    print(
        "SIGNATURE=",
        SIGNATURE,
    )
    print(
        "SLOT=",
        tx.get("slot"),
    )
    print(
        "BLOCK_TIME=",
        tx.get("blockTime"),
    )

    # ========================================================
    # RAYDIUM INSTRUCTION
    # ========================================================

    print(
        "\n=== EXACT RAYDIUM INSTRUCTION ==="
    )

    candidates = []

    for group in (
        meta.get("innerInstructions")
        or []
    ):

        for position, ix in enumerate(
            group.get("instructions")
            or []
        ):

            if ix.get("programId") != RAYDIUM:
                continue

            accounts = [
                address(x)
                for x in (
                    ix.get("accounts")
                    or []
                )
            ]

            candidates.append(
                (
                    group.get("index"),
                    position,
                    accounts,
                    ix,
                )
            )

    print(
        "RAYDIUM_INSTRUCTIONS=",
        len(candidates),
    )

    if len(candidates) != 1:

        print(
            "FAIL_CLOSED_REASON="
            "MULTIPLE_OR_ZERO_RAYDIUM_INSTRUCTIONS"
        )

        return

    group_index, position, accounts, ix = (
        candidates[0]
    )

    print(
        "GROUP=",
        group_index,
    )

    print(
        "POSITION=",
        position,
    )

    print(
        "ACCOUNT_COUNT=",
        len(accounts),
    )

    for i, account in enumerate(accounts):

        print(
            f"ACCOUNT_{i}=",
            account,
        )

    # ========================================================
    # EXACT REQUIRED ROLES
    # ========================================================

    print(
        "\n=== REQUIRED PDF-03 ROLE MAP ==="
    )

    if len(accounts) < 7:

        print(
            "STATUS=FAIL_CLOSED"
        )
        print(
            "REASON=ACCOUNT_COUNT_LT_7"
        )
        return

    roles = {
        "POOL_VAULT_A": accounts[3],
        "POOL_VAULT_B": accounts[4],
        "USER_SOURCE": accounts[5],
        "USER_DESTINATION": accounts[6],
    }

    for name, value in roles.items():

        print(
            f"{name}=",
            value,
        )

    # ========================================================
    # TOKEN BALANCES
    # ========================================================

    print(
        "\n=== TOKEN BALANCES ==="
    )

    pre = {
        x.get("accountIndex"): x
        for x in (
            meta.get(
                "preTokenBalances"
            )
            or []
        )
    }

    post = {
        x.get("accountIndex"): x
        for x in (
            meta.get(
                "postTokenBalances"
            )
            or []
        )
    }

    delta_by_address = {}

    for idx in sorted(
        set(pre) | set(post)
    ):

        before = pre.get(idx) or {}
        after = post.get(idx) or {}

        before_amount = (
            (
                before.get(
                    "uiTokenAmount"
                )
                or {}
            ).get("amount")
        )

        after_amount = (
            (
                after.get(
                    "uiTokenAmount"
                )
                or {}
            ).get("amount")
        )

        if before_amount is None:
            before_amount = "0"

        if after_amount is None:
            after_amount = "0"

        delta = (
            int(after_amount)
            - int(before_amount)
        )

        if delta == 0:
            continue

        mint = (
            after.get("mint")
            or before.get("mint")
        )

        addr = addresses.get(idx)

        record = {
            "account_index": idx,
            "address": addr,
            "mint": mint,
            "pre_raw": int(before_amount),
            "post_raw": int(after_amount),
            "delta_raw": delta,
        }

        delta_by_address[addr] = record

        print(
            json.dumps(
                record,
                ensure_ascii=False,
            )
        )

    # ========================================================
    # REQUIRED ROLE DELTAS
    # ========================================================

    print(
        "\n=== REQUIRED ROLE DELTAS ==="
    )

    for role, addr in roles.items():

        item = delta_by_address.get(
            addr
        )

        print(
            f"{role}_ADDRESS=",
            addr,
        )

        print(
            f"{role}_DELTA=",
            (
                item["delta_raw"]
                if item
                else "MISSING"
            ),
        )

        print(
            f"{role}_MINT=",
            (
                item["mint"]
                if item
                else "MISSING"
            ),
        )

    # ========================================================
    # ACTUAL TOKEN TRANSFERS
    # ========================================================

    print(
        "\n=== ACTUAL TOKEN TRANSFERS ==="
    )

    transfers = []

    for group in (
        meta.get("innerInstructions")
        or []
    ):

        for position, instruction in enumerate(
            group.get("instructions")
            or []
        ):

            parsed = instruction.get(
                "parsed"
            )

            if not isinstance(
                parsed,
                dict,
            ):
                continue

            if parsed.get("type") not in (
                "transfer",
                "transferChecked",
            ):
                continue

            info = (
                parsed.get("info")
                or {}
            )

            item = {
                "group": group.get(
                    "index"
                ),
                "position": position,
                "type": parsed.get(
                    "type"
                ),
                "source": info.get(
                    "source"
                ),
                "destination": info.get(
                    "destination"
                ),
                "mint": info.get(
                    "mint"
                ),
                "amount": info.get(
                    "amount"
                ),
                "tokenAmount": info.get(
                    "tokenAmount"
                ),
            }

            transfers.append(item)

            print(
                json.dumps(
                    item,
                    ensure_ascii=False,
                )
            )

    # ========================================================
    # ROLE MATCHING AGAINST ACTUAL TRANSFERS
    # ========================================================

    print(
        "\n=== ROLE TRANSFER MATCHING ==="
    )

    for role, addr in roles.items():

        source_matches = [
            x
            for x in transfers
            if x["source"] == addr
        ]

        destination_matches = [
            x
            for x in transfers
            if x["destination"] == addr
        ]

        print(
            f"{role}_AS_SOURCE=",
            len(source_matches),
        )

        print(
            f"{role}_AS_DESTINATION=",
            len(destination_matches),
        )

        for item in source_matches:

            print(
                "SOURCE_MATCH=",
                json.dumps(
                    item,
                    ensure_ascii=False,
                ),
            )

        for item in destination_matches:

            print(
                "DESTINATION_MATCH=",
                json.dumps(
                    item,
                    ensure_ascii=False,
                ),
            )

    # ========================================================
    # SPECIFIC PDF-03 EXPECTED SOURCE
    # ========================================================

    print(
        "\n=== PDF-03 EXPECTED INPUT EVIDENCE ==="
    )

    print(
        "EXPECTED_USER_SOURCE=",
        roles["USER_SOURCE"],
    )

    print(
        "EXPECTED_USER_DESTINATION=",
        roles["USER_DESTINATION"],
    )

    print(
        "\n=== DECISION ==="
    )

    source_delta = delta_by_address.get(
        roles["USER_SOURCE"]
    )

    destination_delta = (
        delta_by_address.get(
            roles["USER_DESTINATION"]
        )
    )

    print(
        "USER_SOURCE_DELTA_PRESENT=",
        source_delta is not None,
    )

    print(
        "USER_DESTINATION_DELTA_PRESENT=",
        destination_delta is not None,
    )

    print(
        "OHLCV_BUILD=DISABLED"
    )

    print(
        "CANONICAL_OHLCV_COMMITTED=False"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "STATUS=DIAGNOSTIC_ONLY"
    )


if __name__ == "__main__":
    main()