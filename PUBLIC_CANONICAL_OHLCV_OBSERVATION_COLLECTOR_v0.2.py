from __future__ import annotations

import json
import ssl
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


ENGINE = "PUBLIC_CANONICAL_OHLCV_OBSERVATION_COLLECTOR_v0.2"
RPC_URL = "https://api.mainnet-beta.solana.com"

RAYDIUM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
SOURCE_ID = "SOLANA_MAINNET_RAYDIUM_AMM_V4"
SOURCE_TYPE = "DEX_ONCHAIN"

SIGNATURES = [
    "eUEWhcc9aMePhatSNTFYAZy8zBrqdNSG2MFZwnyuxzYZ5n77GgB3wvZTCYKTpbXXquvvwNQSjiZ4BxEDkxMu1C3",
    "2AXdMLHrb8hcR4Vb2ztu4eFqQTwphEVbFAr4iYTaqE2zoYYum3BeXAGkNuBs4AvGnxDksP3DcV1APbj9fLcV55GG",
    "2YdM9Ayvsg5YZJH8WfauzgKxov2cM8cJSECZKiwhTp2jXPfQzdxTgb4KvvXrehkUesjTLzCBLpH1izn2kUL3fkX8",
    "4mSu7DvSoCSye1onotKmB8yREnaiqzVWZsKNF6R7DJ8Jr6mxsNj4gcwU5KsWe1QzJbihRkXMBgEtaSP6Qz2FwAET",
    "2zwC7mMvQQD3tNeZvDmLb8zqJt362ZPY2f46NhZEJiLiwZ6zp8JtyZx1WJCoFBcKmvfdY8zhCYYsRNnB8oqQKpPr",
]

# Exact PDF-03 role map.
POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
POOL_AUTHORITY = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
POOL_VAULT_A = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
POOL_VAULT_B = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"
USER_SOURCE = "Cu7NnC4cUYPbe23Eekzzt3VwqRGqnTH4jqyeKmBaJCEf"
USER_DESTINATION = "f1JG9hFUiRUMkZjfKjhE5rQEDEGZMd19WjJEKbh1UEH"

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL = "So11111111111111111111111111111111111111112"

REQUEST_DELAY = 0.75
MAX_RETRIES = 6
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def rpc_call(method, params):
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }).encode()

    for attempt in range(MAX_RETRIES):
        request = Request(
            RPC_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ArundaTrader-PDF04/0.2",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=30,
                context=SSL_CONTEXT,
            ) as response:
                return json.loads(response.read().decode())

        except HTTPError as exc:
            if exc.code != 429:
                raise

            if attempt == MAX_RETRIES - 1:
                raise

            delay = REQUEST_DELAY * (2 ** attempt)
            print(
                f"RATE_LIMIT_429 attempt={attempt + 1}/{MAX_RETRIES} "
                f"sleep={delay:.2f}s"
            )
            time.sleep(delay)

        except URLError:
            if attempt == MAX_RETRIES - 1:
                raise

            delay = REQUEST_DELAY * (2 ** attempt)
            time.sleep(delay)

    raise RuntimeError("RPC_RETRY_EXHAUSTED")


def account_keys(tx):
    keys = tx["transaction"]["message"]["accountKeys"]

    result = []

    for item in keys:
        if isinstance(item, dict):
            result.append(item["pubkey"])
        else:
            result.append(item)

    return result


def find_raydium_instructions(tx):
    found = []

    meta = tx.get("meta") or {}

    for group in meta.get("innerInstructions") or []:
        group_index = group.get("index")

        for position, instruction in enumerate(group.get("instructions") or []):
            program_id = instruction.get("programId")

            if program_id == RAYDIUM:
                found.append({
                    "group": group_index,
                    "position": position,
                    "instruction": instruction,
                })

    return found


def parsed_token_transfers(tx):
    transfers = []

    meta = tx.get("meta") or {}

    for group in meta.get("innerInstructions") or []:
        group_index = group.get("index")

        for position, instruction in enumerate(group.get("instructions") or []):
            parsed = instruction.get("parsed")

            if not isinstance(parsed, dict):
                continue

            typ = parsed.get("type")
            info = parsed.get("info") or {}

            if typ not in ("transfer", "transferChecked"):
                continue

            source = info.get("source")
            destination = info.get("destination")

            if not source or not destination:
                continue

            amount = None
            decimals = None
            mint = info.get("mint")

            if typ == "transferChecked":
                token_amount = info.get("tokenAmount") or {}
                amount = token_amount.get("amount")
                decimals = token_amount.get("decimals")

            else:
                amount = info.get("amount")

            transfers.append({
                "group": group_index,
                "position": position,
                "type": typ,
                "source": source,
                "destination": destination,
                "mint": mint,
                "amount": amount,
                "decimals": decimals,
                "raw": info,
            })

    return transfers


def account_token_deltas(tx):
    meta = tx.get("meta") or {}

    pre = {
        x.get("accountIndex"): x
        for x in (meta.get("preTokenBalances") or [])
    }

    post = {
        x.get("accountIndex"): x
        for x in (meta.get("postTokenBalances") or [])
    }

    indices = sorted(set(pre) | set(post))
    keys = account_keys(tx)

    rows = []

    for idx in indices:
        p = pre.get(idx)
        q = post.get(idx)

        mint = (q or p).get("mint")
        pre_raw = int((p or {}).get("uiTokenAmount", {}).get("amount", "0"))
        post_raw = int((q or {}).get("uiTokenAmount", {}).get("amount", "0"))

        rows.append({
            "account_index": idx,
            "address": keys[idx] if idx < len(keys) else None,
            "mint": mint,
            "pre_raw": pre_raw,
            "post_raw": post_raw,
            "delta_raw": post_raw - pre_raw,
        })

    return rows


def unique_role_transfer(transfers, source=None, destination=None):
    matches = []

    for t in transfers:
        if source is not None and t["source"] != source:
            continue

        if destination is not None and t["destination"] != destination:
            continue

        matches.append(t)

    if len(matches) != 1:
        return None, len(matches)

    return matches[0], 1


def transfer_amount(t):
    if t is None:
        return None

    if t["amount"] is not None:
        return int(t["amount"])

    return None


def validate_exact_mapping(tx, signature):
    raydium = find_raydium_instructions(tx)

    if len(raydium) != 1:
        if len(raydium) > 1:
            return None, "AMBIGUOUS_MULTIPLE_RAYDIUM_INSTRUCTIONS"

        return None, "NO_RAYDIUM_INSTRUCTION"

    instruction = raydium[0]["instruction"]
    accounts = instruction.get("accounts") or []

    if len(accounts) < 7:
        return None, "RAYDIUM_ACCOUNT_COUNT_LT_7"

    # Required mapping is positional and immutable.
    if accounts[3] != POOL_VAULT_A:
        return None, "ACCOUNT_3_NOT_POOL_VAULT_A"

    if accounts[4] != POOL_VAULT_B:
        return None, "ACCOUNT_4_NOT_POOL_VAULT_B"

    if accounts[5] != USER_SOURCE:
        return None, "ACCOUNT_5_NOT_USER_SOURCE"

    if accounts[6] != USER_DESTINATION:
        return None, "ACCOUNT_6_NOT_USER_DESTINATION"

    transfers = parsed_token_transfers(tx)
    deltas = account_token_deltas(tx)

    delta_by_address = {
        row["address"]: row
        for row in deltas
    }

    # ------------------------------------------------------------------
    # VAULT VALIDATION
    # ------------------------------------------------------------------

    vault_a_delta = delta_by_address.get(POOL_VAULT_A)
    vault_b_delta = delta_by_address.get(POOL_VAULT_B)

    if vault_a_delta is None:
        return None, "POOL_VAULT_A_DELTA_MISSING"

    if vault_b_delta is None:
        return None, "POOL_VAULT_B_DELTA_MISSING"

    if vault_a_delta["mint"] != WSOL:
        return None, "POOL_VAULT_A_MINT_MISMATCH"

    if vault_b_delta["mint"] != USDC:
        return None, "POOL_VAULT_B_MINT_MISMATCH"

    if vault_a_delta["delta_raw"] >= 0:
        return None, "POOL_VAULT_A_DIRECTION_INVALID"

    if vault_b_delta["delta_raw"] <= 0:
        return None, "POOL_VAULT_B_DIRECTION_INVALID"

    # ------------------------------------------------------------------
    # USER ENDPOINT VALIDATION
    #
    # IMPORTANT:
    # USER_SOURCE and USER_DESTINATION are NOT required to have
    # pre/postTokenBalances.
    #
    # They are validated by exact executed transfer evidence.
    # ------------------------------------------------------------------

    user_source_transfer, source_count = unique_role_transfer(
        transfers,
        source=USER_SOURCE,
        destination=POOL_VAULT_B,
    )

    if source_count != 1:
        if source_count > 1:
            return None, "AMBIGUOUS_USER_SOURCE_TRANSFER"

        return None, "USER_SOURCE_TRANSFER_MISSING"

    user_destination_transfer, destination_count = unique_role_transfer(
        transfers,
        source=POOL_VAULT_A,
        destination=USER_DESTINATION,
    )

    if destination_count != 1:
        if destination_count > 1:
            return None, "AMBIGUOUS_USER_DESTINATION_TRANSFER"

        return None, "USER_DESTINATION_TRANSFER_MISSING"

    input_amount = transfer_amount(user_source_transfer)
    output_amount = transfer_amount(user_destination_transfer)

    if input_amount is None:
        return None, "USER_SOURCE_AMOUNT_MISSING"

    if output_amount is None:
        return None, "USER_DESTINATION_AMOUNT_MISSING"

    # Exact amount agreement with vault deltas.
    if input_amount != vault_b_delta["delta_raw"]:
        return None, "INPUT_AMOUNT_VAULT_DELTA_MISMATCH"

    if output_amount != abs(vault_a_delta["delta_raw"]):
        return None, "OUTPUT_AMOUNT_VAULT_DELTA_MISMATCH"

    # transferChecked evidence, when available, must identify USDC.
    checked_source = None

    for t in transfers:
        if (
            t["source"] == USER_SOURCE
            and t["destination"] == POOL_VAULT_B
            and t["type"] == "transferChecked"
        ):
            checked_source = t
            break

    if checked_source is not None and checked_source["mint"] != USDC:
        return None, "USER_SOURCE_MINT_MISMATCH"

    checked_destination = None

    for t in transfers:
        if (
            t["source"] == POOL_VAULT_A
            and t["destination"] == USER_DESTINATION
            and t["type"] == "transferChecked"
        ):
            checked_destination = t
            break

    if checked_destination is not None and checked_destination["mint"] != WSOL:
        return None, "USER_DESTINATION_MINT_MISMATCH"

    price = output_amount / 1_000_000_000
    price /= input_amount / 1_000_000

    slot = tx.get("slot")
    block_time = tx.get("blockTime")

    if block_time is None:
        return None, "BLOCK_TIME_MISSING"

    observation = {
        "signature": signature,
        "slot": slot,
        "block_time": block_time,
        "block_time_iso": datetime.fromtimestamp(
            block_time,
            tz=timezone.utc,
        ).isoformat(),
        "pool": POOL,
        "pool_authority": POOL_AUTHORITY,
        "input_mint": USDC,
        "output_mint": WSOL,
        "input_amount_raw": input_amount,
        "input_decimals": 6,
        "input_amount": input_amount / 1_000_000,
        "output_amount_raw": output_amount,
        "output_decimals": 9,
        "output_amount": output_amount / 1_000_000_000,
        "price": price,
        "instruction": "SWAP_BASE_IN_V2",
        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,
        "provenance": {
            "rpc": RPC_URL,
            "slot": slot,
            "block_time": block_time,
            "signature": signature,
            "account_mapping": {
                "account_3": POOL_VAULT_A,
                "account_4": POOL_VAULT_B,
                "account_5": USER_SOURCE,
                "account_6": USER_DESTINATION,
            },
        },
    }

    return observation, None


def main():
    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print("OHLCV_BUILD=DISABLED")
    print("DB_WRITE=DISABLED")
    print("CANONICAL_COMMIT=DISABLED")
    print("TLS_VERIFICATION=ENABLED")
    print()

    signatures_found = len(SIGNATURES)
    transactions_checked = 0
    raydium_swaps = 0
    exact_account_mappings = 0
    valid_pair_observations = 0
    rejected_ambiguous = 0
    rejected_invalid_mapping = 0
    rpc_failures = 0

    observations = []

    print(f"SIGNATURES_FOUND={signatures_found}")

    for i, signature in enumerate(SIGNATURES[:100], start=1):
        print()
        print(f"CHECKING={i}/{min(signatures_found, 100)}")
        print(f"SIGNATURE={signature}")

        if i > 1:
            time.sleep(REQUEST_DELAY)

        try:
            result = rpc_call(
                "getTransaction",
                [
                    signature,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed",
                        "maxSupportedTransactionVersion": 0,
                    },
                ],
            )

        except Exception as exc:
            rpc_failures += 1
            print(
                f"RPC_FAILURE=1 "
                f"ERROR={type(exc).__name__}:{exc}"
            )
            continue

        tx = result.get("result")

        if not tx:
            print("TRANSACTION_NOT_FOUND=1")
            continue

        transactions_checked += 1

        slot = tx.get("slot")
        block_time = tx.get("blockTime")

        raydium = find_raydium_instructions(tx)

        if raydium:
            raydium_swaps += 1

        print(f"SLOT={slot}")
        print(f"BLOCK_TIME={block_time}")
        print(f"RAYDIUM_INSTRUCTIONS={len(raydium)}")

        if not raydium:
            continue

        observation, reason = validate_exact_mapping(tx, signature)

        if observation is None:
            if reason and reason.startswith("AMBIGUOUS"):
                rejected_ambiguous += 1
                print(
                    f"REJECTED_AMBIGUOUS=1 "
                    f"REASON={reason}"
                )
            else:
                rejected_invalid_mapping += 1
                print(
                    f"REJECTED_INVALID_MAPPING=1 "
                    f"REASON={reason}"
                )

            continue

        exact_account_mappings += 1
        valid_pair_observations += 1
        observations.append(observation)

        print("EXACT_ACCOUNT_MAPPING=1")
        print("VALID_PAIR_OBSERVATION=1")
        print(
            "OBSERVATION="
            + json.dumps(
                observation,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    unique_timestamps = len(
        set(
            x["block_time"]
            for x in observations
        )
    )

    hour_buckets = len(
        set(
            x["block_time"] // 3600
            for x in observations
        )
    )

    print()
    print("===== PDF-04 v0.2 RUNTIME EVIDENCE =====")
    print(f"SIGNATURES_FOUND={signatures_found}")
    print(f"TRANSACTIONS_CHECKED={transactions_checked}")
    print(f"RAYDIUM_SWAPS={raydium_swaps}")
    print(f"EXACT_ACCOUNT_MAPPINGS={exact_account_mappings}")
    print(f"VALID_PAIR_OBSERVATIONS={valid_pair_observations}")
    print(f"REJECTED_AMBIGUOUS={rejected_ambiguous}")
    print(f"REJECTED_INVALID_MAPPING={rejected_invalid_mapping}")
    print(f"UNIQUE_TIMESTAMPS={unique_timestamps}")
    print(f"HOUR_BUCKETS={hour_buckets}")
    print(f"RPC_FAILURES={rpc_failures}")
    print("RATE_LIMITING=ENABLED")
    print(f"REQUEST_DELAY_SECONDS={REQUEST_DELAY}")
    print(f"MAX_RETRIES={MAX_RETRIES}")
    print("RETRY_BACKOFF=EXPONENTIAL")
    print("TLS_VERIFICATION=ENABLED")

    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")

    print("DB_WRITES=0")
    print("CANONICAL_OHLCV_COMMITTED=False")
    print("FAIL_CLOSED=True")

    if valid_pair_observations > 0:
        status = "READY_FOR_PDF04_REVIEW"
    elif rpc_failures > 0 and transactions_checked == 0:
        status = "FAIL_CLOSED"
    else:
        status = "FAIL_CLOSED"

    print(f"STATUS={status}")
    print("NEXT_ACTION=PDF04_REVIEW_ONLY")


if __name__ == "__main__":
    main()