
import json
import ssl
import time
import urllib.request
import certifi
from datetime import datetime, timezone


ENGINE = "PUBLIC_CANONICAL_OHLCV_PROVENANCE_v0.1"
RPC_URL = "https://api.mainnet-beta.solana.com"

SOURCE_ID = "SOLANA_MAINNET_RAYDIUM_AMM_V4"
SOURCE_TYPE = "DEX_ONCHAIN"
PRICE_UNIT = "USDC_PER_SOL"

POOL = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
POOL_AUTHORITY = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"

RAYDIUM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

POOL_VAULT_A = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
POOL_VAULT_B = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL_MINT = "So11111111111111111111111111111111111111112"

TIMEFRAME = "1h"
SYMBOL = "SOL/USDC"

DB_WRITES = 0
CANONICAL_OHLCV_COMMITTED = False
EXECUTION = "DISABLED"

TLS_CONTEXT = ssl.create_default_context(
    cafile=certifi.where()
)


# ============================================================
# REAL PDF-04 CANDIDATE
# ============================================================

CANONICAL_CANDIDATE = {
    "asset": "SOL",
    "symbol": "SOL/USDC",
    "timestamp": 1788822000,
    "timestamp_iso": "2026-09-07T23:00:00+00:00",
    "timeframe": "1h",
    "open": 103.9433519613302,
    "high": 103.9433519613302,
    "low": 103.93748844263929,
    "close": 103.93748844263929,
    "volume": 109.97541,
    "observation_count": 2,
    "pool": POOL,
    "price_unit": PRICE_UNIT,

    "observations": [
        {
            "signature": "2m1fkxJhf2QDhqQZfd4Vb8xiYMGHraKgDVUh84mrQS6R6y9EoDJjiZzthC4vyt4fdYURtRxwcf2XrWsTvJQzZatn",
            "slot": 445186108,
            "block_time": 1788822363,
            "price": 103.9433519613302,
            "volume_quote_usdc": 0.93135,
            "pool": POOL,
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "raydium_instruction": {
                "group": 3,
                "position": 5,
            },
            "account_mapping": {
                "account_3": POOL_VAULT_A,
                "account_4": POOL_VAULT_B,
                "account_5": "4Nu86LTizYQVMJFM2Ate5aVzH77g3a7rbo9KPT9ExMZk",
                "account_6": "FdrGU7ETVKux31hGwunsVH4t1FTnVNGV7WKTfyGpgbs",
            },
        },
        {
            "signature": "2eNmAjMYRWUcrJyCwdex2JtVy3Yxo1549pHEEFjJNjvCsKLVGhkmqNhW6bz8Wrfa47hLsfRKzur1RaEs4P8DKYbA",
            "slot": 445186115,
            "block_time": 1788822365,
            "price": 103.93748844263929,
            "volume_quote_usdc": 109.04406,
            "pool": POOL,
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "raydium_instruction": {
                "group": 4,
                "position": 10,
            },
            "account_mapping": {
                "account_3": POOL_VAULT_A,
                "account_4": POOL_VAULT_B,
                "account_5": "3LB6Rx9rwhDhfqnUAYc6kmvuRpwwRBxhGWFZJb5ACeCJ",
                "account_6": "7PZyYs8WnpKvW7k29BgtrPU4CCtqGm3kexsjr5GtqLhJ",
            },
        },
    ],
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def rpc_call(method, params, retries=6):
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")

    for attempt in range(retries):
        request = urllib.request.Request(
            RPC_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ArundaTrader-PDF05/0.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                context=TLS_CONTEXT,
                timeout=30,
            ) as response:
                body = response.read().decode("utf-8")
                result = json.loads(body)

                if "error" in result:
                    raise RuntimeError(
                        f"RPC_ERROR={result['error']}"
                    )

                return result["result"]

        except Exception:
            if attempt >= retries - 1:
                raise

            time.sleep(min(2 ** attempt, 8))

    raise RuntimeError("RPC_UNREACHABLE")


def find_raydium_instructions(tx):
    message = tx.get("transaction", {}).get("message", {})
    instructions = message.get("instructions") or []

    found = []

    print()
    print("===== PDF-05 INSTRUCTION STRUCTURE DIAGNOSTIC =====")
    print(f"TOP_LEVEL_INSTRUCTIONS={len(instructions)}")

    for position, ix in enumerate(instructions):
        print(
            "TOP_LEVEL="
            + json.dumps(
                {
                    "position": position,
                    "keys": sorted(ix.keys()),
                    "programId": ix.get("programId"),
                    "program": ix.get("program"),
                    "parsed": ix.get("parsed"),
                    "accounts": ix.get("accounts"),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )

        if ix.get("programId") == RAYDIUM_PROGRAM_ID:
            found.append(
                {
                    "group": 0,
                    "position": position,
                    "accounts": ix.get("accounts") or [],
                    "data": ix.get("data"),
                }
            )

    meta = tx.get("meta") or {}
    inner_groups = meta.get("innerInstructions") or []

    print(f"INNER_INSTRUCTION_GROUPS={len(inner_groups)}")

    for group in inner_groups:
        group_index = group.get("index")

        print(
            f"INNER_GROUP_INDEX={group_index}"
            f" COUNT={len(group.get('instructions') or [])}"
        )

        if group_index is None:
            continue

        for position, ix in enumerate(
            group.get("instructions") or []
        ):
            print(
                "INNER="
                + json.dumps(
                    {
                        "group": group_index,
                        "position": position,
                        "keys": sorted(ix.keys()),
                        "programId": ix.get("programId"),
                        "program": ix.get("program"),
                        "parsed": ix.get("parsed"),
                        "accounts": ix.get("accounts"),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

            if ix.get("programId") == RAYDIUM_PROGRAM_ID:
                found.append(
                    {
                        "group": group_index,
                        "position": position,
                        "accounts": ix.get("accounts") or [],
                        "data": ix.get("data"),
                    }
                )

    print(f"RAYDIUM_INSTRUCTIONS_DETECTED={len(found)}")
    print("===== END INSTRUCTION STRUCTURE DIAGNOSTIC =====")
    print()

    return found

def exact_instruction_matches(expected, tx):
    expected_ix = expected.get("raydium_instruction") or {}

    expected_group = expected_ix.get("group")
    expected_position = expected_ix.get("position")

    expected_mapping = expected.get("account_mapping") or {}

    all_instructions = find_raydium_instructions(tx)

    # ========================================================
    # DIAGNOSTIC
    # ========================================================

    print()
    print("===== PDF-05 RAYDIUM INSTRUCTION DIAGNOSTIC =====")
    print(f"EXPECTED_GROUP={expected_group}")
    print(f"EXPECTED_POSITION={expected_position}")
    print(f"EXPECTED_ACCOUNT_3={POOL_VAULT_A}")
    print(f"EXPECTED_ACCOUNT_4={POOL_VAULT_B}")
    print(
        "EXPECTED_ACCOUNT_5="
        f"{expected_mapping.get('account_5')}"
    )
    print(
        "EXPECTED_ACCOUNT_6="
        f"{expected_mapping.get('account_6')}"
    )
    print(
        "RAYDIUM_INSTRUCTIONS_FOUND="
        f"{len(all_instructions)}"
    )

    for ix in all_instructions:
        print(
            "FOUND="
            + json.dumps(
                ix,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    # ========================================================
    # EXACT MATCH
    # ========================================================

    matches = []

    for ix in all_instructions:
        if ix.get("group") != expected_group:
            continue

        if ix.get("position") != expected_position:
            continue

        accounts = ix.get("accounts") or []

        if len(accounts) < 7:
            continue

        if accounts[3] != POOL_VAULT_A:
            continue

        if accounts[4] != POOL_VAULT_B:
            continue

        if accounts[5] != expected_mapping.get("account_5"):
            continue

        if accounts[6] != expected_mapping.get("account_6"):
            continue

        matches.append(ix)

    print(f"EXACT_MATCHES={len(matches)}")
    print("===== END DIAGNOSTIC =====")
    print()

    return matches


def validate_candidate_structure(candidate):
    required = [
        "asset",
        "symbol",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "observation_count",
        "observations",
        "pool",
        "price_unit",
    ]

    for key in required:
        if key not in candidate:
            return False, f"MISSING_CANDIDATE_FIELD={key}"

    if candidate["asset"] != "SOL":
        return False, "INVALID_ASSET"

    if candidate["symbol"] != SYMBOL:
        return False, "INVALID_SYMBOL"

    if candidate["timeframe"] != TIMEFRAME:
        return False, "INVALID_TIMEFRAME"

    if candidate["pool"] != POOL:
        return False, "INVALID_POOL"

    if candidate["price_unit"] != PRICE_UNIT:
        return False, "INVALID_PRICE_UNIT"

    observations = candidate["observations"]

    if len(observations) != candidate["observation_count"]:
        return False, "OBSERVATION_COUNT_MISMATCH"

    if len(observations) < 2:
        return False, "INSUFFICIENT_OBSERVATIONS"

    return True, None


def validate_lineage(candidate):
    ok, reason = validate_candidate_structure(candidate)

    if not ok:
        return False, reason, [], 0

    linked = []
    observation_signatures = []
    observation_slots = []
    observation_timestamps = []

    for expected in candidate["observations"]:
        signature = expected.get("signature")

        if not signature:
            return False, "MISSING_SIGNATURE", linked, len(linked)

        retrieved_at = utc_now_iso()

        tx = rpc_call(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": "finalized",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )

        if not tx:
            return (
                False,
                f"TRANSACTION_NOT_FOUND={signature}",
                linked,
                len(linked),
            )

        tx_slot = tx.get("slot")
        block_time = tx.get("blockTime")

        if tx_slot != expected["slot"]:
            return (
                False,
                f"SLOT_MISMATCH={signature}",
                linked,
                len(linked),
            )

        if block_time != expected["block_time"]:
            return (
                False,
                f"BLOCK_TIME_MISMATCH={signature}",
                linked,
                len(linked),
            )

        if expected["pool"] != POOL:
            return (
                False,
                f"POOL_MISMATCH={signature}",
                linked,
                len(linked),
            )

        if expected["source_id"] != SOURCE_ID:
            return (
                False,
                f"SOURCE_ID_MISMATCH={signature}",
                linked,
                len(linked),
            )

        if expected["source_type"] != SOURCE_TYPE:
            return (
                False,
                f"SOURCE_TYPE_MISMATCH={signature}",
                linked,
                len(linked),
            )

        matches = exact_instruction_matches(
            expected,
            tx,
        )

        if len(matches) != 1:
            return (
                False,
                f"RAYDIUM_INSTRUCTION_LINEAGE_AMBIGUOUS={signature}",
                linked,
                len(linked),
            )

        ix = matches[0]

        if (
            ix["group"]
            != expected["raydium_instruction"]["group"]
            or ix["position"]
            != expected["raydium_instruction"]["position"]
        ):
            return (
                False,
                f"INSTRUCTION_POSITION_MISMATCH={signature}",
                linked,
                len(linked),
            )

        account_mapping = {
            "account_3": ix["accounts"][3],
            "account_4": ix["accounts"][4],
            "account_5": ix["accounts"][5],
            "account_6": ix["accounts"][6],
        }

        if account_mapping != expected["account_mapping"]:
            return (
                False,
                f"ACCOUNT_MAPPING_MISMATCH={signature}",
                linked,
                len(linked),
            )

        linked.append(
            {
                "signature": signature,
                "slot": tx_slot,
                "block_time": block_time,
                "block_time_iso": datetime.fromtimestamp(
                    block_time,
                    timezone.utc,
                ).isoformat(),
                "pool": POOL,
                "source_id": SOURCE_ID,
                "source_type": SOURCE_TYPE,
                "retrieved_at": retrieved_at,
                "raydium_instruction": {
                    "group": ix["group"],
                    "position": ix["position"],
                    "program_id": RAYDIUM_PROGRAM_ID,
                    "data": ix["data"],
                },
                "account_mapping": account_mapping,
            }
        )

        observation_signatures.append(signature)
        observation_slots.append(tx_slot)
        observation_timestamps.append(block_time)

        time.sleep(0.75)

    if len(linked) != candidate["observation_count"]:
        return (
            False,
            "OBSERVATION_LINK_COUNT_MISMATCH",
            linked,
            len(linked),
        )

    # ========================================================
    # Deterministic OHLC lineage verification
    # ========================================================

    prices = [
        float(x["price"])
        for x in candidate["observations"]
    ]

    volumes = [
        float(x["volume_quote_usdc"])
        for x in candidate["observations"]
    ]

    expected_open = prices[0]
    expected_close = prices[-1]
    expected_high = max(prices)
    expected_low = min(prices)
    expected_volume = sum(volumes)

    if candidate["open"] != expected_open:
        return (
            False,
            "OPEN_LINEAGE_MISMATCH",
            linked,
            len(linked),
        )

    if candidate["high"] != expected_high:
        return (
            False,
            "HIGH_LINEAGE_MISMATCH",
            linked,
            len(linked),
        )

    if candidate["low"] != expected_low:
        return (
            False,
            "LOW_LINEAGE_MISMATCH",
            linked,
            len(linked),
        )

    if candidate["close"] != expected_close:
        return (
            False,
            "CLOSE_LINEAGE_MISMATCH",
            linked,
            len(linked),
        )

    if candidate["volume"] != expected_volume:
        return (
            False,
            "VOLUME_LINEAGE_MISMATCH",
            linked,
            len(linked),
        )

    # ========================================================
    # Deterministic bucket verification
    # ========================================================

    for observation in candidate["observations"]:
        bucket = (
            observation["block_time"] // 3600
        ) * 3600

        if bucket != candidate["timestamp"]:
            return (
                False,
                "OBSERVATION_OUTSIDE_1H_BUCKET",
                linked,
                len(linked),
            )

    provenance = {
        "asset": candidate["asset"],
        "symbol": candidate["symbol"],
        "timestamp": candidate["timestamp"],
        "timeframe": candidate["timeframe"],
        "open": candidate["open"],
        "high": candidate["high"],
        "low": candidate["low"],
        "close": candidate["close"],
        "volume": candidate["volume"],

        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,
        "source_timestamp": candidate["timestamp"],
        "retrieved_at": [
            x["retrieved_at"]
            for x in linked
        ],

        "observation_count": len(linked),
        "observation_signatures": observation_signatures,
        "observation_slots": observation_slots,
        "observation_timestamps": observation_timestamps,

        "pool": POOL,
        "raydium_instruction": [
            x["raydium_instruction"]
            for x in linked
        ],

        "lineage": linked,
    }

    return True, provenance, linked, len(linked)


def main():
    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print(f"EXECUTION={EXECUTION}")
    print("SOURCE=REAL_DATA_ONLY")
    print(f"SOURCE_ID={SOURCE_ID}")
    print(f"SOURCE_TYPE={SOURCE_TYPE}")
    print(f"PRICE_UNIT={PRICE_UNIT}")

    valid, result, linked, linked_count = validate_lineage(
        CANONICAL_CANDIDATE
    )

    canonical_input = 1

    if valid:
        print()
        print("===== PDF-05 PROVENANCE RUNTIME EVIDENCE =====")
        print("STATUS=PROVENANCE_VALID")
        print(f"CANONICAL_CANDLES_INPUT={canonical_input}")
        print("PROVENANCE_VALID_CANDLES=1")
        print("PROVENANCE_INVALID_CANDLES=0")
        print(f"OBSERVATIONS_LINKED={linked_count}")
        print(f"SOURCE_ID={SOURCE_ID}")
        print(f"SOURCE_TYPE={SOURCE_TYPE}")
        print(f"PRICE_UNIT={PRICE_UNIT}")
        print("LINEAGE_COMPLETE=True")
        print(f"DB_WRITES={DB_WRITES}")
        print(
            "CANONICAL_OHLCV_COMMITTED="
            f"{CANONICAL_OHLCV_COMMITTED}"
        )
        print("FAIL_CLOSED=False")

        print()
        print("===== PROVENANCE LINEAGE =====")
        print(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    else:
        print()
        print("===== PDF-05 PROVENANCE RUNTIME EVIDENCE =====")
        print("STATUS=FAIL_CLOSED")
        print(f"CANONICAL_CANDLES_INPUT={canonical_input}")
        print("PROVENANCE_VALID_CANDLES=0")
        print("PROVENANCE_INVALID_CANDLES=1")
        print(f"OBSERVATIONS_LINKED={linked_count}")
        print(f"SOURCE_ID={SOURCE_ID}")
        print(f"SOURCE_TYPE={SOURCE_TYPE}")
        print(f"PRICE_UNIT={PRICE_UNIT}")
        print("LINEAGE_COMPLETE=False")
        print(f"DB_WRITES={DB_WRITES}")
        print(
            "CANONICAL_OHLCV_COMMITTED="
            f"{CANONICAL_OHLCV_COMMITTED}"
        )
        print("FAIL_CLOSED=True")
        print(f"FAIL_CLOSED_REASON={result}")


if __name__ == "__main__":
    main()