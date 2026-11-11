
import json
import ssl
import urllib.request
import urllib.parse
from datetime import datetime, timezone


ENGINE = "PUBLIC_MARKET_DATA_FAILOVER_v0.1"

PRIMARY_SOURCE = "BITGET_SPOT_PUBLIC"
FALLBACK_SOURCE = "KUCOIN_SPOT_PUBLIC"

PRIMARY_SOURCE_TYPE = "CEX_PUBLIC"
FALLBACK_SOURCE_TYPE = "CEX_PUBLIC"

TIMEFRAME = "1h"
ASSET = "SOL"
PRIMARY_SYMBOL = "SOLUSDT"
FALLBACK_SYMBOL = "SOL-USDT"

DB_WRITES = 0
CANONICAL_OHLCV_COMMITTED = False
EXECUTION = "DISABLED"

TLS_CONTEXT = ssl.create_default_context()

BITGET_URL = "https://api.bitget.com/api/v2/spot/market/candles"
KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"


# ============================================================
# CONTROLLED FAILURE INJECTION
#
# This does NOT modify data.
# It only prevents the primary adapter from being selected
# in SCENARIO_B.
# ============================================================

def fetch_bitget(symbol=None):
    params = {
        "symbol": (
            str(symbol or PRIMARY_SYMBOL)
            .strip()
            .upper()
            .replace("/", "")
        ),
        "granularity": "1h",
        "limit": "150",
    }

    url = (
        BITGET_URL
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ArundaTrader-PDF07/0.1",
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(
        request,
        context=TLS_CONTEXT,
        timeout=20,
    ) as response:
        payload = json.loads(
            response.read().decode("utf-8")
        )

    if payload.get("code") != "00000":
        raise RuntimeError(
            f"BITGET_API_ERROR={payload}"
        )

    rows = payload.get("data") or []

    if not rows:
        raise RuntimeError(
            "BITGET_EMPTY_RESPONSE"
        )

    normalized_symbol = (
        str(symbol or PRIMARY_SYMBOL)
        .strip()
        .upper()
        .replace("/", "")
    )

    history = []

    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            raise RuntimeError(
                "BITGET_INVALID_CANDLE"
            )

        history.append(
            {
                "source_id": PRIMARY_SOURCE,
                "source_type": PRIMARY_SOURCE_TYPE,
                "symbol": normalized_symbol,
                "timestamp": int(row[0]) // 1000,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "quote_volume": float(row[6]),
                "raw": row,
            }
        )

    current_hour = int(
        datetime.now(timezone.utc).timestamp()
    )
    current_hour -= current_hour % 3600

    closed_history = [
        candle
        for candle in history
        if candle["timestamp"] < current_hour
    ]

    if not closed_history:
        raise RuntimeError(
            "BITGET_NO_CLOSED_1H_CANDLE"
        )

    closed_history.sort(
        key=lambda candle: candle["timestamp"],
        reverse=True,
    )

    return closed_history[0]


def fetch_kucoin():
    params = {
        "symbol": FALLBACK_SYMBOL,
        "type": "1hour",
    }

    url = (
        KUCOIN_URL
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ArundaTrader-PDF07/0.1",
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(
        request,
        context=TLS_CONTEXT,
        timeout=20,
    ) as response:
        payload = json.loads(
            response.read().decode("utf-8")
        )

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR={payload}"
        )

    rows = payload.get("data") or []

    if not rows:
        raise RuntimeError(
            "KUCOIN_EMPTY_RESPONSE"
        )

    # KuCoin returns:
    # [timestamp, open, close, high, low, volume, turnover]
    row = rows[0]

    return {
        "source_id": FALLBACK_SOURCE,
        "source_type": FALLBACK_SOURCE_TYPE,
        "symbol": FALLBACK_SYMBOL,
        "timestamp": int(row[0]),
        "open": float(row[1]),
        "close": float(row[2]),
        "high": float(row[3]),
        "low": float(row[4]),
        "volume": float(row[5]),
        "quote_volume": float(row[6]),
        "raw": row,
    }


# ============================================================
# CANONICAL OBSERVATION VALIDATION
# ============================================================

def validate_observation(obs):
    required = [
        "source_id",
        "source_type",
        "symbol",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for key in required:
        if key not in obs:
            return False, f"MISSING_FIELD={key}"

    if obs["source_id"] not in {
        PRIMARY_SOURCE,
        FALLBACK_SOURCE,
    }:
        return False, "INVALID_SOURCE_ID"

    if obs["source_type"] != "CEX_PUBLIC":
        return False, "INVALID_SOURCE_TYPE"

    if obs["timestamp"] % 3600 != 0:
        return False, "TIMESTAMP_NOT_1H_BOUNDARY"

    if obs["high"] < max(
        obs["open"],
        obs["close"],
    ):
        return False, "HIGH_STRUCTURE_VIOLATION"

    if obs["low"] > min(
        obs["open"],
        obs["close"],
    ):
        return False, "LOW_STRUCTURE_VIOLATION"

    if obs["high"] < obs["low"]:
        return False, "HIGH_BELOW_LOW"

    if obs["volume"] < 0:
        return False, "NEGATIVE_VOLUME"

    return True, None


# ============================================================
# CANONICALIZATION
#
# IMPORTANT:
# One selected observation only.
# No blending.
# ============================================================

def canonicalize(selected):
    ok, reason = validate_observation(selected)

    if not ok:
        raise RuntimeError(
            f"SELECTED_OBSERVATION_INVALID={reason}"
        )

    return {
        "asset": ASSET,
        "symbol": "SOL/USDT",
        "timestamp": selected["timestamp"],
        "timeframe": TIMEFRAME,
        "open": selected["open"],
        "high": selected["high"],
        "low": selected["low"],
        "close": selected["close"],
        "volume": selected["volume"],
        "provenance": {
            "source_id": selected["source_id"],
            "source_type": selected["source_type"],
            "source_timestamp": selected["timestamp"],
        },
    }


# ============================================================
# SCENARIO A
#
# Primary available -> Primary selected.
# Fallback is NOT called.
# ============================================================

def scenario_a():
    fallback_called = False

    try:
        primary = fetch_bitget()
        primary_status = "AVAILABLE"
    except Exception as exc:
        return {
            "primary_status": "FAILED",
            "fallback_status": "NOT_USED",
            "failover_triggered": False,
            "selected_source": None,
            "blended": False,
            "canonical_candles": 0,
            "provenance_valid": False,
            "fail_closed": True,
            "reason": str(exc),
        }

    ok, reason = validate_observation(primary)

    if not ok:
        return {
            "primary_status": "INVALID",
            "fallback_status": "NOT_USED",
            "failover_triggered": False,
            "selected_source": None,
            "blended": False,
            "canonical_candles": 0,
            "provenance_valid": False,
            "fail_closed": True,
            "reason": reason,
        }

    canonical = canonicalize(primary)

    return {
        "primary_status": primary_status,
        "fallback_status": (
            "NOT_USED"
            if not fallback_called
            else "USED"
        ),
        "failover_triggered": False,
        "selected_source": canonical["provenance"]["source_id"],
        "blended": False,
        "canonical_candles": 1,
        "provenance_valid": (
            canonical["provenance"]["source_id"]
            == PRIMARY_SOURCE
        ),
        "fail_closed": False,
        "canonical": canonical,
    }


# ============================================================
# SCENARIO B
#
# CONTROLLED FAILURE INJECTION:
# Primary adapter is intentionally disabled BEFORE invocation.
#
# This is configuration/control-plane failure injection.
# No market data is modified.
# ============================================================

def scenario_b():
    primary_injected_failure = True

    if primary_injected_failure:
        primary_status = "CONTROLLED_FAILURE"

        try:
            fallback = fetch_kucoin()
            fallback_status = "AVAILABLE"
        except Exception as exc:
            return {
                "primary_status": primary_status,
                "fallback_status": "FAILED",
                "failover_triggered": True,
                "selected_source": None,
                "blended": False,
                "canonical_candles": 0,
                "provenance_valid": False,
                "fail_closed": True,
                "reason": (
                    f"FALLBACK_UNAVAILABLE={exc}"
                ),
            }
    else:
        return {
            "primary_status": "NOT_INJECTED",
            "fallback_status": "NOT_TESTED",
            "failover_triggered": False,
            "selected_source": None,
            "blended": False,
            "canonical_candles": 0,
            "provenance_valid": False,
            "fail_closed": True,
            "reason": "FAILURE_INJECTION_NOT_ACTIVE",
        }

    ok, reason = validate_observation(
        fallback
    )

    if not ok:
        return {
            "primary_status": primary_status,
            "fallback_status": fallback_status,
            "failover_triggered": True,
            "selected_source": None,
            "blended": False,
            "canonical_candles": 0,
            "provenance_valid": False,
            "fail_closed": True,
            "reason": (
                f"FALLBACK_INVALID={reason}"
            ),
        }

    canonical = canonicalize(fallback)

    return {
        "primary_status": primary_status,
        "fallback_status": fallback_status,
        "failover_triggered": True,
        "selected_source": canonical["provenance"]["source_id"],
        "blended": False,
        "canonical_candles": 1,
        "provenance_valid": (
            canonical["provenance"]["source_id"]
            == FALLBACK_SOURCE
        ),
        "fail_closed": False,
        "canonical": canonical,
    }


# ============================================================
# RUNTIME REPORT
# ============================================================

def print_scenario(name, result):

    print()
    print(f"===== {name} =====")

    print(
        f"PRIMARY_SOURCE={PRIMARY_SOURCE}"
    )
    print(
        f"PRIMARY_STATUS={result['primary_status']}"
    )
    print(
        f"FALLBACK_SOURCE={FALLBACK_SOURCE}"
    )
    print(
        f"FALLBACK_STATUS={result['fallback_status']}"
    )
    print(
        f"FAILOVER_TRIGGERED="
        f"{result['failover_triggered']}"
    )
    print(
        f"SELECTED_SOURCE="
        f"{result['selected_source']}"
    )
    print(
        f"BLENDED={result['blended']}"
    )
    print(
        f"CANONICAL_CANDLES="
        f"{result['canonical_candles']}"
    )
    print(
        f"PROVENANCE_VALID="
        f"{result['provenance_valid']}"
    )
    print(
        f"DB_WRITES={DB_WRITES}"
    )
    print(
        "CANONICAL_OHLCV_COMMITTED="
        f"{CANONICAL_OHLCV_COMMITTED}"
    )
    print(
        f"FAIL_CLOSED="
        f"{result['fail_closed']}"
    )

    if result.get("reason"):
        print(
            f"FAIL_CLOSED_REASON="
            f"{result['reason']}"
        )

    if result.get("canonical"):
        print(
            "CANONICAL="
            + json.dumps(
                result["canonical"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"ENGINE={ENGINE}"
    )
    print("MODE=READ_ONLY")
    print(
        f"EXECUTION={EXECUTION}"
    )
    print(
        "SOURCE=REAL_PUBLIC_MARKET_DATA_ONLY"
    )
    print(
        f"PRIMARY_SOURCE={PRIMARY_SOURCE}"
    )
    print(
        f"FALLBACK_SOURCE={FALLBACK_SOURCE}"
    )
    print(
        f"TIMEFRAME={TIMEFRAME}"
    )

    a = scenario_a()
    b = scenario_b()

    print_scenario(
        "PDF-07 SCENARIO_A",
        a,
    )

    print_scenario(
        "PDF-07 SCENARIO_B",
        b,
    )

    a_verified = (
        a["primary_status"] == "AVAILABLE"
        and a["failover_triggered"] is False
        and a["selected_source"]
        == PRIMARY_SOURCE
        and a["blended"] is False
        and a["canonical_candles"] == 1
        and a["provenance_valid"] is True
        and a["fail_closed"] is False
    )

    b_verified = (
        b["primary_status"]
        == "CONTROLLED_FAILURE"
        and b["fallback_status"]
        == "AVAILABLE"
        and b["failover_triggered"] is True
        and b["selected_source"]
        == FALLBACK_SOURCE
        and b["blended"] is False
        and b["canonical_candles"] == 1
        and b["provenance_valid"] is True
        and b["fail_closed"] is False
    )

    global_verified = (
        a_verified
        and b_verified
        and DB_WRITES == 0
        and CANONICAL_OHLCV_COMMITTED is False
    )

    print()
    print(
        "===== PDF-07 FAILOVER RUNTIME EVIDENCE ====="
    )

    if global_verified:
        print("STATUS=FAILOVER_VERIFIED")
        print("SCENARIO_A_VERIFIED=True")
        print("SCENARIO_B_VERIFIED=True")
    else:
        print("STATUS=FAIL_CLOSED")
        print(
            f"SCENARIO_A_VERIFIED={a_verified}"
        )
        print(
            f"SCENARIO_B_VERIFIED={b_verified}"
        )

    print(
        f"DB_WRITES={DB_WRITES}"
    )
    print(
        "CANONICAL_OHLCV_COMMITTED="
        f"{CANONICAL_OHLCV_COMMITTED}"
    )
    print(
        f"FAIL_CLOSED={not global_verified}"
    )


if __name__ == "__main__":
    main()
