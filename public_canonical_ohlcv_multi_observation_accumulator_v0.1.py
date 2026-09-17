from __future__ import annotations

import json
import ssl
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


# ============================================================
# ARUNDA — PDF-04 REAL MULTI-OBSERVATION ACCUMULATION
# ============================================================

ENGINE = (
    "PUBLIC_CANONICAL_OHLCV_MULTI_OBSERVATION_ACCUMULATOR_v0.2"
)

RPC_URL = "https://api.mainnet-beta.solana.com"

RAYDIUM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

SOURCE_ID = "SOLANA_MAINNET_RAYDIUM_AMM_V4"
SOURCE_TYPE = "DEX_ONCHAIN"

# ------------------------------------------------------------
# EXACT PDF-03 POOL
# ------------------------------------------------------------

POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"

POOL_AUTHORITY = (
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
)

POOL_VAULT_A = (
    "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
)

POOL_VAULT_B = (
    "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"
)

# ------------------------------------------------------------
# EXACT MINTS
# ------------------------------------------------------------

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

WSOL = "So11111111111111111111111111111111111111112"

# ------------------------------------------------------------
# RATE LIMIT / SAFETY
# ------------------------------------------------------------

REQUEST_DELAY = 0.75
MAX_RETRIES = 6

SIGNATURE_PAGE_SIZE = 100
MAX_SIGNATURE_PAGES = 20
MAX_TRANSACTIONS = 1000

# Existing PDF-04 rule:
# A real 1h bucket requires >= 2 real observations.
MIN_OBSERVATIONS_PER_BUCKET = 2

SSL_CONTEXT = ssl.create_default_context(
    cafile=certifi.where()
)


# ============================================================
# RPC
# ============================================================

def rpc_call(method, params):
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode()

    for attempt in range(MAX_RETRIES):

        request = Request(
            RPC_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": (
                    "ArundaTrader-PDF04-MULTI/0.2"
                ),
            },
            method="POST",
        )

        try:

            with urlopen(
                request,
                timeout=30,
                context=SSL_CONTEXT,
            ) as response:

                return json.loads(
                    response.read().decode()
                )

        except HTTPError as exc:

            if exc.code != 429:
                raise

            if attempt == MAX_RETRIES - 1:
                raise

            delay = REQUEST_DELAY * (2 ** attempt)

            print(
                f"RATE_LIMIT_429 "
                f"attempt={attempt + 1}/{MAX_RETRIES} "
                f"sleep={delay:.2f}s"
            )

            time.sleep(delay)

        except URLError:

            if attempt == MAX_RETRIES - 1:
                raise

            delay = REQUEST_DELAY * (2 ** attempt)

            print(
                f"RPC_RETRY "
                f"attempt={attempt + 1}/{MAX_RETRIES} "
                f"sleep={delay:.2f}s"
            )

            time.sleep(delay)

    raise RuntimeError("RPC_RETRY_EXHAUSTED")


# ============================================================
# SIGNATURE PAGINATION
# ============================================================

def get_signature_page(before=None):

    config = {
        "limit": SIGNATURE_PAGE_SIZE,
        "commitment": "confirmed",
    }

    if before:
        config["before"] = before

    result = rpc_call(
        "getSignaturesForAddress",
        [
            POOL,
            config,
        ],
    )

    return result.get("result") or []


# ============================================================
# ACCOUNT KEYS
# ============================================================

def account_keys(tx):

    keys = (
        tx
        .get("transaction", {})
        .get("message", {})
        .get("accountKeys", [])
    )

    result = []

    for item in keys:

        if isinstance(item, dict):
            pubkey = item.get("pubkey")

            if pubkey:
                result.append(pubkey)

        else:
            result.append(item)

    return result


# ============================================================
# RAYDIUM INSTRUCTIONS
# ============================================================

def find_raydium_instructions(tx):

    found = []

    meta = tx.get("meta") or {}

    for group in meta.get("innerInstructions") or []:

        group_index = group.get("index")

        for position, instruction in enumerate(
            group.get("instructions") or []
        ):

            if instruction.get("programId") != RAYDIUM:
                continue

            accounts = instruction.get("accounts") or []

            found.append(
                {
                    "group": group_index,
                    "position": position,
                    "instruction": instruction,
                    "accounts": accounts,
                }
            )

    return found


# ============================================================
# EXACT POOL RAYDIUM INSTRUCTION
# ============================================================

def find_exact_pool_instruction(tx):

    matches = []

    for item in find_raydium_instructions(tx):

        accounts = item["accounts"]

        if len(accounts) < 7:
            continue

        # Immutable pool-role contract.
        if accounts[3] != POOL_VAULT_A:
            continue

        if accounts[4] != POOL_VAULT_B:
            continue

        matches.append(item)

    if len(matches) == 0:
        return None, "NO_EXACT_POOL_RAYDIUM_INSTRUCTION"

    if len(matches) > 1:
        return (
            None,
            "AMBIGUOUS_MULTIPLE_EXACT_POOL_RAYDIUM_INSTRUCTIONS",
        )

    return matches[0], None


# ============================================================
# PARSED TOKEN TRANSFERS
# ============================================================

def parsed_token_transfers(tx):

    transfers = []

    meta = tx.get("meta") or {}

    for group in meta.get("innerInstructions") or []:

        group_index = group.get("index")

        for position, instruction in enumerate(
            group.get("instructions") or []
        ):

            parsed = instruction.get("parsed")

            if not isinstance(parsed, dict):
                continue

            typ = parsed.get("type")

            if typ not in (
                "transfer",
                "transferChecked",
            ):
                continue

            info = parsed.get("info") or {}

            source = info.get("source")
            destination = info.get("destination")

            if not source or not destination:
                continue

            mint = info.get("mint")
            amount = None
            decimals = None

            if typ == "transferChecked":

                token_amount = (
                    info.get("tokenAmount") or {}
                )

                amount = token_amount.get("amount")
                decimals = token_amount.get("decimals")

            else:

                amount = info.get("amount")

            transfers.append(
                {
                    "group": group_index,
                    "position": position,
                    "type": typ,
                    "source": source,
                    "destination": destination,
                    "mint": mint,
                    "amount": amount,
                    "decimals": decimals,
                }
            )

    return transfers


# ============================================================
# TOKEN BALANCE DELTAS
# ============================================================

def account_token_deltas(tx):

    meta = tx.get("meta") or {}

    pre = {
        x.get("accountIndex"): x
        for x in (
            meta.get("preTokenBalances") or []
        )
    }

    post = {
        x.get("accountIndex"): x
        for x in (
            meta.get("postTokenBalances") or []
        )
    }

    indices = sorted(set(pre) | set(post))

    keys = account_keys(tx)

    rows = []

    for idx in indices:

        p = pre.get(idx)
        q = post.get(idx)

        if p is None and q is None:
            continue

        token_data = q or p

        mint = token_data.get("mint")

        pre_raw = int(
            (p or {})
            .get("uiTokenAmount", {})
            .get("amount", "0")
        )

        post_raw = int(
            (q or {})
            .get("uiTokenAmount", {})
            .get("amount", "0")
        )

        address = (
            keys[idx]
            if idx < len(keys)
            else None
        )

        rows.append(
            {
                "account_index": idx,
                "address": address,
                "mint": mint,
                "pre_raw": pre_raw,
                "post_raw": post_raw,
                "delta_raw": post_raw - pre_raw,
            }
        )

    return rows


# ============================================================
# EXACT TRANSFER MATCH
# ============================================================

def transfers_between(
    transfers,
    source,
    destination,
):

    return [
        t
        for t in transfers
        if (
            t["source"] == source
            and t["destination"] == destination
        )
    ]


def transfer_amount(transfer):

    if transfer is None:
        return None

    amount = transfer.get("amount")

    if amount is None:
        return None

    return int(amount)


# ============================================================
# EXACT TRANSFER SELECTION
# ============================================================

def select_exact_transfer(
    transfers,
    source,
    destination,
    expected_mint,
    expected_amount,
):

    matches = transfers_between(
        transfers,
        source,
        destination,
    )

    # Prefer exact amount + mint evidence.
    exact = []

    for t in matches:

        amount = transfer_amount(t)

        if amount != expected_amount:
            continue

        if t["type"] == "transferChecked":

            if t["mint"] != expected_mint:
                continue

        exact.append(t)

    if len(exact) == 1:
        return exact[0], None

    if len(exact) > 1:
        return (
            None,
            "AMBIGUOUS_EXACT_TRANSFER_MATCH",
        )

    if len(matches) == 0:
        return (
            None,
            "EXACT_TRANSFER_MISSING",
        )

    return (
        None,
        "EXACT_TRANSFER_AMOUNT_OR_MINT_MISMATCH",
    )


# ============================================================
# VALIDATE ONE REAL OBSERVATION
# ============================================================

def validate_exact_mapping(
    tx,
    signature,
):

    # --------------------------------------------------------
    # Find all Raydium instructions.
    # --------------------------------------------------------

    raydium_instructions = (
        find_raydium_instructions(tx)
    )

    if len(raydium_instructions) == 0:
        return None, "NO_RAYDIUM_INSTRUCTION"

    # --------------------------------------------------------
    # Select exactly one instruction belonging to
    # the exact PDF-03 pool.
    # --------------------------------------------------------

    pool_instruction, reason = (
        find_exact_pool_instruction(tx)
    )

    if pool_instruction is None:
        return None, reason

    instruction = (
        pool_instruction["instruction"]
    )

    accounts = (
        pool_instruction["accounts"]
    )

    # --------------------------------------------------------
    # Immutable positional mapping.
    #
    # account[3] = pool vault A
    # account[4] = pool vault B
    # account[5] = transaction-specific user source
    # account[6] = transaction-specific user destination
    # --------------------------------------------------------

    if len(accounts) < 7:
        return None, "RAYDIUM_ACCOUNT_COUNT_LT_7"

    if accounts[3] != POOL_VAULT_A:
        return None, "ACCOUNT_3_POOL_VAULT_A_MISMATCH"

    if accounts[4] != POOL_VAULT_B:
        return None, "ACCOUNT_4_POOL_VAULT_B_MISMATCH"

    user_source = accounts[5]
    user_destination = accounts[6]

    if not user_source:
        return None, "ACCOUNT_5_USER_SOURCE_MISSING"

    if not user_destination:
        return None, "ACCOUNT_6_USER_DESTINATION_MISSING"

    # --------------------------------------------------------
    # Transfers and vault deltas.
    # --------------------------------------------------------

    transfers = parsed_token_transfers(tx)

    deltas = account_token_deltas(tx)

    delta_by_address = {
        row["address"]: row
        for row in deltas
        if row["address"]
    }

    vault_a = delta_by_address.get(
        POOL_VAULT_A
    )

    vault_b = delta_by_address.get(
        POOL_VAULT_B
    )

    if vault_a is None:
        return None, "POOL_VAULT_A_DELTA_MISSING"

    if vault_b is None:
        return None, "POOL_VAULT_B_DELTA_MISSING"

    # --------------------------------------------------------
    # Vault A = WSOL
    # Must decrease on SOL output.
    # --------------------------------------------------------

    if vault_a["mint"] != WSOL:
        return None, "POOL_VAULT_A_MINT_MISMATCH"

    if vault_a["delta_raw"] >= 0:
        return None, "POOL_VAULT_A_DIRECTION_INVALID"

    output_raw = abs(
        vault_a["delta_raw"]
    )

    # --------------------------------------------------------
    # Vault B = USDC
    # Must increase on USDC input.
    # --------------------------------------------------------

    if vault_b["mint"] != USDC:
        return None, "POOL_VAULT_B_MINT_MISMATCH"

    if vault_b["delta_raw"] <= 0:
        return None, "POOL_VAULT_B_DIRECTION_INVALID"

    input_raw = vault_b["delta_raw"]

    if input_raw <= 0 or output_raw <= 0:
        return None, "NON_POSITIVE_SWAP_AMOUNT"

    # --------------------------------------------------------
    # USER SOURCE:
    #
    # account[5] -> account[4]
    #
    # Exact executed transfer must carry the same amount
    # as vault B delta.
    # --------------------------------------------------------

    source_transfer, source_reason = (
        select_exact_transfer(
            transfers=transfers,
            source=user_source,
            destination=POOL_VAULT_B,
            expected_mint=USDC,
            expected_amount=input_raw,
        )
    )

    if source_transfer is None:
        return None, (
            "USER_SOURCE_TRANSFER:"
            + source_reason
        )

    # --------------------------------------------------------
    # USER DESTINATION:
    #
    # account[3] -> account[6]
    #
    # Exact executed transfer must carry the same amount
    # as vault A delta.
    # --------------------------------------------------------

    destination_transfer, destination_reason = (
        select_exact_transfer(
            transfers=transfers,
            source=POOL_VAULT_A,
            destination=user_destination,
            expected_mint=WSOL,
            expected_amount=output_raw,
        )
    )

    if destination_transfer is None:
        return None, (
            "USER_DESTINATION_TRANSFER:"
            + destination_reason
        )

    # --------------------------------------------------------
    # Additional exact amount checks.
    # --------------------------------------------------------

    source_amount = transfer_amount(
        source_transfer
    )

    destination_amount = transfer_amount(
        destination_transfer
    )

    if source_amount != input_raw:
        return None, "SOURCE_AMOUNT_MISMATCH"

    if destination_amount != output_raw:
        return None, "DESTINATION_AMOUNT_MISMATCH"

    # --------------------------------------------------------
    # If transferChecked is present, mint must be exact.
    # --------------------------------------------------------

    if (
        source_transfer["type"]
        == "transferChecked"
    ):

        if source_transfer["mint"] != USDC:
            return None, "SOURCE_MINT_MISMATCH"

    if (
        destination_transfer["type"]
        == "transferChecked"
    ):

        if destination_transfer["mint"] != WSOL:
            return None, "DESTINATION_MINT_MISMATCH"

    # --------------------------------------------------------
    # Timestamp.
    # --------------------------------------------------------

    block_time = tx.get("blockTime")

    if block_time is None:
        return None, "BLOCK_TIME_MISSING"

    slot = tx.get("slot")

    # --------------------------------------------------------
    # Canonical units.
    #
    # USDC raw = 6 decimals
    # WSOL raw = 9 decimals
    #
    # Canonical price = USDC_PER_SOL
    # --------------------------------------------------------

    input_amount = (
        input_raw / 1_000_000
    )

    output_amount = (
        output_raw / 1_000_000_000
    )

    if output_amount <= 0:
        return None, "OUTPUT_AMOUNT_ZERO"

    price_usdc_per_sol = (
        input_amount / output_amount
    )

    hour_bucket = (
        block_time // 3600
    ) * 3600

    # --------------------------------------------------------
    # Real observation.
    # --------------------------------------------------------

    observation = {
        "signature": signature,
        "slot": slot,
        "block_time": block_time,
        "block_time_iso": datetime.fromtimestamp(
            block_time,
            tz=timezone.utc,
        ).isoformat(),

        "hour_bucket": hour_bucket,

        "hour_bucket_iso": datetime.fromtimestamp(
            hour_bucket,
            tz=timezone.utc,
        ).isoformat(),

        "pool": POOL,
        "pool_authority": POOL_AUTHORITY,

        "input_mint": USDC,
        "output_mint": WSOL,

        "input_amount_raw": input_raw,
        "input_decimals": 6,
        "input_amount": input_amount,

        "output_amount_raw": output_raw,
        "output_decimals": 9,
        "output_amount": output_amount,

        "price": price_usdc_per_sol,
        "price_unit": "USDC_PER_SOL",

        # Real quote volume only.
        "volume_quote_usdc": input_amount,

        "instruction": "SWAP_BASE_IN_V2",

        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,

        "provenance": {
            "rpc": RPC_URL,
            "slot": slot,
            "block_time": block_time,
            "signature": signature,

            "raydium_instruction": {
                "group": pool_instruction["group"],
                "position": pool_instruction["position"],
            },

            "account_mapping": {
                "account_3": POOL_VAULT_A,
                "account_4": POOL_VAULT_B,
                "account_5": user_source,
                "account_6": user_destination,
            },

            "transfer_mapping": {
                "input": {
                    "source": user_source,
                    "destination": POOL_VAULT_B,
                    "amount_raw": input_raw,
                    "mint": USDC,
                    "type": source_transfer["type"],
                    "group": source_transfer["group"],
                    "position": source_transfer["position"],
                },
                "output": {
                    "source": POOL_VAULT_A,
                    "destination": user_destination,
                    "amount_raw": output_raw,
                    "mint": WSOL,
                    "type": destination_transfer["type"],
                    "group": destination_transfer["group"],
                    "position": destination_transfer["position"],
                },
            },
        },
    }

    return observation, None


# ============================================================
# IN-MEMORY BUCKETS
# ============================================================

def bucket_observations(observations):

    buckets = defaultdict(list)

    for observation in observations:

        key = (
            observation["source_id"],
            observation["pool"],
            observation["input_mint"],
            observation["output_mint"],
            observation["hour_bucket"],
        )

        buckets[key].append(
            observation
        )

    return buckets


# ============================================================
# COMPLETE BUCKET DETECTION
# ============================================================

def find_complete_bucket(
    observations
):

    buckets = bucket_observations(
        observations
    )

    for key, rows in sorted(
        buckets.items(),
        key=lambda item: item[0][-1],
    ):

        if len(rows) < MIN_OBSERVATIONS_PER_BUCKET:
            continue

        rows.sort(
            key=lambda x: (
                x["block_time"],
                x["signature"],
            )
        )

        # ----------------------------------------------------
        # Defensive uniqueness check.
        # ----------------------------------------------------

        signatures = {
            x["signature"]
            for x in rows
        }

        if len(signatures) != len(rows):
            continue

        # ----------------------------------------------------
        # Every observation must be canonical unit.
        # ----------------------------------------------------

        if any(
            x["price_unit"] != "USDC_PER_SOL"
            for x in rows
        ):
            continue

        # ----------------------------------------------------
        # Build candidate entirely in memory.
        # ----------------------------------------------------

        prices = [
            x["price"]
            for x in rows
        ]

        volumes = [
            x["volume_quote_usdc"]
            for x in rows
        ]

        candidate = {
            "asset": "SOL",
            "symbol": "SOL/USDC",
            "timestamp": rows[0]["hour_bucket"],
            "timestamp_iso": datetime.fromtimestamp(
                rows[0]["hour_bucket"],
                tz=timezone.utc,
            ).isoformat(),
            "timeframe": "1h",

            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],

            "volume": sum(volumes),

            "price_unit": "USDC_PER_SOL",

            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "pool": POOL,

            "observation_count": len(rows),

            "provenance": [
                x["provenance"]
                for x in rows
            ],
        }

        return candidate

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"ENGINE={ENGINE}"
    )

    print("MODE=READ_ONLY")
    print("PRODUCTION_DB=NO_TOUCH")
    print("EXECUTION=DISABLED")
    print("OHLCV_DB_COMMIT=DISABLED")

    print(
        "SOURCE=REAL_OBSERVATIONS_ONLY"
    )

    print("TIMEFRAME=1h")
    print("SYMBOL=SOL/USDC")
    print("PRICE_UNIT=USDC_PER_SOL")

    print("PAGINATION=BEFORE")

    print()

    observations = []

    seen_signatures = set()

    signature_pages = 0
    signatures_found = 0

    transactions_checked = 0

    raydium_swaps = 0
    exact_account_mappings = 0
    valid_observations = 0

    rejected_ambiguous = 0
    rejected_invalid_mapping = 0

    rpc_failures = 0
    transaction_not_found = 0

    before = None
    candidate = None

    # --------------------------------------------------------
    # PAGINATE UNTIL:
    #
    # 1. Complete bucket found
    # 2. Safety limit reached
    # 3. Pagination exhausted
    # 4. Fatal RPC condition
    # --------------------------------------------------------

    while (
        signature_pages
        < MAX_SIGNATURE_PAGES
        and transactions_checked
        < MAX_TRANSACTIONS
        and candidate is None
    ):

        signature_pages += 1

        try:

            page = get_signature_page(
                before
            )

        except Exception as exc:

            rpc_failures += 1

            print(
                "RPC_FAILURE=1 "
                "STAGE=SIGNATURE_PAGINATION "
                f"ERROR={type(exc).__name__}:{exc}"
            )

            break

        if not page:

            print(
                f"SIGNATURE_PAGE={signature_pages} "
                "RESULT=EMPTY"
            )

            break

        print(
            f"SIGNATURE_PAGE={signature_pages} "
            f"COUNT={len(page)} "
            f"BEFORE={before}"
        )

        signatures_found += len(page)

        for item in page:

            if (
                transactions_checked
                >= MAX_TRANSACTIONS
            ):
                break

            signature = item.get(
                "signature"
            )

            if not signature:
                continue

            if signature in seen_signatures:
                continue

            seen_signatures.add(
                signature
            )

            print()

            print(
                f"CHECKING_TX="
                f"{transactions_checked + 1}/"
                f"{MAX_TRANSACTIONS}"
            )

            print(
                f"SIGNATURE={signature}"
            )

            if transactions_checked > 0:
                time.sleep(
                    REQUEST_DELAY
                )

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
                    "RPC_FAILURE=1 "
                    "STAGE=GET_TRANSACTION "
                    f"ERROR={type(exc).__name__}:{exc}"
                )

                continue

            tx = result.get("result")

            if not tx:

                transaction_not_found += 1

                print(
                    "TRANSACTION_NOT_FOUND=1"
                )

                continue

            transactions_checked += 1

            slot = tx.get("slot")
            block_time = tx.get(
                "blockTime"
            )

            raydium_instructions = (
                find_raydium_instructions(tx)
            )

            print(
                f"SLOT={slot}"
            )

            print(
                f"BLOCK_TIME={block_time}"
            )

            print(
                "RAYDIUM_INSTRUCTIONS="
                f"{len(raydium_instructions)}"
            )

            if not raydium_instructions:
                continue

            raydium_swaps += 1

            observation, reason = (
                validate_exact_mapping(
                    tx,
                    signature,
                )
            )

            if observation is None:

                if (
                    reason
                    and (
                        reason.startswith(
                            "AMBIGUOUS"
                        )
                        or "AMBIGUOUS" in reason
                    )
                ):

                    rejected_ambiguous += 1

                    print(
                        "REJECTED_AMBIGUOUS=1 "
                        f"REASON={reason}"
                    )

                else:

                    rejected_invalid_mapping += 1

                    print(
                        "REJECTED_INVALID_MAPPING=1 "
                        f"REASON={reason}"
                    )

                continue

            exact_account_mappings += 1
            valid_observations += 1

            observations.append(
                observation
            )

            print(
                "EXACT_ACCOUNT_MAPPING=1"
            )

            print(
                "VALID_PAIR_OBSERVATION=1"
            )

            print(
                "OBSERVATION="
                + json.dumps(
                    observation,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

            # ------------------------------------------------
            # STOP immediately when first complete real
            # bucket becomes available.
            # ------------------------------------------------

            candidate = (
                find_complete_bucket(
                    observations
                )
            )

            if candidate is not None:

                print()

                print(
                    "===== "
                    "COMPLETE REAL 1H BUCKET FOUND "
                    "====="
                )

                print(
                    "CANONICAL_OHLCV_CANDIDATE="
                    + json.dumps(
                        candidate,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )

                break

        if candidate is not None:
            break

        # ----------------------------------------------------
        # Solana returns newest -> oldest.
        # Last signature is the next cursor.
        # ----------------------------------------------------

        before = page[-1].get(
            "signature"
        )

        if len(page) < SIGNATURE_PAGE_SIZE:

            print(
                "PAGINATION_EXHAUSTED=True "
                "REASON=FINAL_PARTIAL_PAGE"
            )

            break

        time.sleep(
            REQUEST_DELAY
        )

    # ========================================================
    # FINAL EVIDENCE
    # ========================================================

    buckets = bucket_observations(
        observations
    )

    complete_bucket_count = sum(
        1
        for rows in buckets.values()
        if len(rows)
        >= MIN_OBSERVATIONS_PER_BUCKET
    )

    unique_timestamps = len(
        {
            x["block_time"]
            for x in observations
        }
    )

    print()

    print(
        "===== "
        "PDF-04 MULTI-OBSERVATION RUNTIME EVIDENCE "
        "====="
    )

    print(
        f"SIGNATURE_PAGES={signature_pages}"
    )

    print(
        f"SIGNATURES_FOUND={signatures_found}"
    )

    print(
        f"TRANSACTIONS_CHECKED="
        f"{transactions_checked}"
    )

    print(
        f"TRANSACTIONS_NOT_FOUND="
        f"{transaction_not_found}"
    )

    print(
        f"RAYDIUM_SWAPS={raydium_swaps}"
    )

    print(
        f"EXACT_ACCOUNT_MAPPINGS="
        f"{exact_account_mappings}"
    )

    print(
        f"VALID_PAIR_OBSERVATIONS="
        f"{valid_observations}"
    )

    print(
        f"REJECTED_AMBIGUOUS="
        f"{rejected_ambiguous}"
    )

    print(
        f"REJECTED_INVALID_MAPPING="
        f"{rejected_invalid_mapping}"
    )

    print(
        f"UNIQUE_TIMESTAMPS="
        f"{unique_timestamps}"
    )

    print(
        f"HOUR_BUCKETS="
        f"{len(buckets)}"
    )

    print(
        f"COMPLETE_1H_BUCKETS="
        f"{complete_bucket_count}"
    )

    print(
        f"RPC_FAILURES={rpc_failures}"
    )

    print(
        "RATE_LIMITING=ENABLED"
    )

    print(
        f"REQUEST_DELAY_SECONDS="
        f"{REQUEST_DELAY}"
    )

    print(
        f"MAX_RETRIES={MAX_RETRIES}"
    )

    print(
        "RETRY_BACKOFF=EXPONENTIAL"
    )

    print(
        "TLS_VERIFICATION=ENABLED"
    )

    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")

    print("DB_WRITES=0")
    print(
        "CANONICAL_OHLCV_COMMITTED=False"
    )

    print(
        "EXECUTION=DISABLED"
    )

    print(
        "FAIL_CLOSED=True"
    )

    # ========================================================
    # STOP CONDITIONS
    # ========================================================

    if candidate is not None:

        print(
            "COMPLETE_BUCKET_FOUND=True"
        )

        print(
            "IN_MEMORY_OHLCV_ONLY=True"
        )

        print(
            "STATUS=COMPLETE_BUCKET_FOUND"
        )

        print(
            "NEXT_ACTION=STOP"
        )

        return

    print(
        "COMPLETE_BUCKET_FOUND=False"
    )

    print(
        "IN_MEMORY_OHLCV_ONLY=False"
    )

    print(
        "STATUS=FAIL_CLOSED"
    )

    if rpc_failures:

        print(
            "FAIL_CLOSED_REASON="
            "RPC_OR_PAGINATION_FAILURE"
        )

    elif valid_observations == 0:

        print(
            "FAIL_CLOSED_REASON="
            "NO_VALID_REAL_OBSERVATIONS"
        )

    elif complete_bucket_count == 0:

        print(
            "FAIL_CLOSED_REASON="
            "NO_1H_BUCKET_WITH_SUFFICIENT_"
            "REAL_OBSERVATIONS"
        )

    else:

        print(
            "FAIL_CLOSED_REASON="
            "NO_COMPLETE_CANONICAL_CANDIDATE"
        )

    print(
        "NEXT_ACTION=STOP"
    )


if __name__ == "__main__":
    main()