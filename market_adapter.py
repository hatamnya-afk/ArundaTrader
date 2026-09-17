# ================================================================
# ARUNDA MARKET ADAPTER v0.4
# Source: CoinMarketCap
# Purpose: REAL MARKET DATA -> arunda.db
# ================================================================

import os
import sqlite3
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ================================================================
# CONFIG
# ================================================================

DB_PATH = "arunda.db"

CMC_URL = (
    "https://pro-api.coinmarketcap.com/v1/"
    "cryptocurrency/quotes/latest"
)

ASSETS = ["BTC", "ETH", "SOL", "XRP"]

ENGINE_VERSION = "MARKET_CMC_v0.4"


# ================================================================
# DATABASE
# ================================================================

def get_db():
    return sqlite3.connect(DB_PATH)


def ensure_schema(conn):
    """
    Ensure market_data has the expected columns.
    Existing database is preserved.
    """

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            ema20 REAL,
            ema50 REAL,
            rsi14 REAL,
            macd REAL,
            macd_signal REAL,
            macd_hist REAL,
            atr14 REAL,
            adx14 REAL,
            bb_middle REAL,
            bb_upper REAL,
            bb_lower REAL,
            bb_width REAL,
            volume_sma20 REAL,
            volume_ratio REAL,
            volatility REAL,
            technical_score REAL,
            source TEXT,
            source_timestamp TEXT
        )
    """)

    conn.commit()


# ================================================================
# HTTP
# ================================================================

def fetch_cmc():
    api_key = os.getenv("COINMARKETCAP_API_KEY")

    if not api_key:
        raise RuntimeError(
            "COINMARKETCAP_API_KEY is not configured."
        )

    symbols = ",".join(ASSETS)

    url = f"{CMC_URL}?symbol={symbols}&convert=USD"

    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
        "User-Agent": "ArundaTrader/0.4"
    }

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()

            latency_ms = (
                time.perf_counter() - started
            ) * 1000

            http_status = response.status

    except urllib.error.HTTPError as e:

        body = e.read().decode("utf-8", errors="replace")

        raise RuntimeError(
            f"CMC HTTP {e.code}: {body}"
        )

    except Exception as e:

        raise RuntimeError(
            f"CMC connection failed: {repr(e)}"
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            f"CMC returned invalid JSON: {repr(e)}"
        )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Unexpected CMC root format: "
            f"{type(payload).__name__}"
        )

    status = payload.get("status", {})

    error_code = status.get("error_code", 0)

    if error_code not in (0, "0", None):

        raise RuntimeError(
            "CMC API error: "
            f"{status.get('error_message')}"
        )

    data = payload.get("data")

    if data is None:
        raise RuntimeError(
            "CMC response contains no data field."
        )

    print(
        f"CMC API  | ONLINE  | "
        f"HTTP {http_status} | "
        f"Latency {latency_ms:.0f} ms"
    )

    return data, latency_ms


# ================================================================
# NORMALIZE CMC DATA
# ================================================================

def normalize_assets(data):
    """
    Convert CMC's different possible structures into:

        {
            "BTC": {...},
            "ETH": {...}
        }
    """

    result = {}

    # ------------------------------------------------------------
    # Case 1:
    # CMC standard:
    #
    # {
    #   "BTC": {...},
    #   "ETH": {...}
    # }
    # ------------------------------------------------------------

    if isinstance(data, dict):

        for symbol, item in data.items():

            if symbol in ASSETS and isinstance(item, dict):

                result[symbol] = item

        if result:
            return result

    # ------------------------------------------------------------
    # Case 2:
    #
    # [
    #   {...},
    #   {...}
    # ]
    # ------------------------------------------------------------

    if isinstance(data, list):

        for item in data:

            if not isinstance(item, dict):
                continue

            symbol = item.get("symbol")

            if symbol in ASSETS:
                result[symbol] = item

        if result:
            return result

    # ------------------------------------------------------------
    # Case 3:
    # Sometimes data is nested
    # ------------------------------------------------------------

    if isinstance(data, dict):

        nested = data.get("data")

        if isinstance(nested, dict):

            for symbol, item in nested.items():

                if symbol in ASSETS and isinstance(item, dict):

                    result[symbol] = item

        elif isinstance(nested, list):

            for item in nested:

                if not isinstance(item, dict):
                    continue

                symbol = item.get("symbol")

                if symbol in ASSETS:
                    result[symbol] = item

    return result


# ================================================================
# NUMERIC HELPERS
# ================================================================

def number(value, default=None):

    try:

        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):

        return default


def clamp(value, low, high):

    return max(low, min(high, value))


# ================================================================
# MARKET SCORE
# ================================================================

def calculate_market_score(quote):
    """
    CMC does not provide enough OHLC history here to calculate
    real RSI/MACD/EMA.

    Therefore this is deliberately named MARKET MOMENTUM SCORE.

    Inputs:
        1h
        24h
        7d
        30d

    Output:
        -100 ... +100
    """

    p1h = number(
        quote.get("percent_change_1h"),
        0
    )

    p24 = number(
        quote.get("percent_change_24h"),
        0
    )

    p7d = number(
        quote.get("percent_change_7d"),
        0
    )

    p30d = number(
        quote.get("percent_change_30d"),
        0
    )

    # Weighted momentum
    score = (
        p1h * 0.15 +
        p24 * 0.35 +
        p7d * 0.30 +
        p30d * 0.20
    )

    # Convert approximately to -100/+100
    score *= 5.0

    return round(
        clamp(score, -100, 100),
        4
    )


# ================================================================
# EXTRACT ASSET
# ================================================================

def extract_asset(symbol, item):

    if not isinstance(item, dict):
        return None

    quote_block = item.get("quote")

    if not isinstance(quote_block, dict):
        return None

    quote = quote_block.get("USD")

    if not isinstance(quote, dict):

        # Defensive fallback:
        # first quote object

        if isinstance(quote_block, list) and quote_block:
            quote = quote_block[0]

        else:
            return None

    price = number(
        quote.get("price")
    )

    volume = number(
        quote.get("volume_24h")
    )

    change_24h = number(
        quote.get("percent_change_24h")
    )

    market_cap = number(
        quote.get("market_cap")
    )

    source_timestamp = (
        quote.get("last_updated")
        or item.get("last_updated")
    )

    if price is None:

        return None

    market_score = calculate_market_score(
        quote
    )

    return {
        "symbol": symbol,
        "price": price,
        "volume": volume,
        "change_24h": change_24h,
        "market_cap": market_cap,
        "market_score": market_score,
        "source_timestamp": source_timestamp,
        "quote": quote
    }


# ================================================================
# DATABASE INSERT
# ================================================================

def insert_market_data(
    conn,
    asset,
    timestamp
):

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO market_data (
            timestamp,
            symbol,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            ema20,
            ema50,
            rsi14,
            macd,
            macd_signal,
            macd_hist,
            atr14,
            adx14,
            bb_middle,
            bb_upper,
            bb_lower,
            bb_width,
            volume_sma20,
            volume_ratio,
            volatility,
            technical_score,
            source,
            source_timestamp
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        timestamp,
        asset["symbol"],
        "24h",

        # No OHLC history from current endpoint.
        None,
        None,
        None,

        # Current market price
        asset["price"],

        asset["volume"],

        # Technical indicators intentionally NULL.
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,

        # Market momentum score
        asset["market_score"],

        "COINMARKETCAP",

        asset["source_timestamp"]
    ))

    conn.commit()


# ================================================================
# MARKET RECORDS
# ================================================================

def ensure_market_records_schema(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            market TEXT NOT NULL,
            asset TEXT,
            price REAL,
            change_24h REAL,
            volume_24h REAL,
            best_bid REAL,
            best_ask REAL,
            mid REAL,
            spread_pct REAL,
            bid_volume REAL,
            ask_volume REAL,
            pressure REAL,
            hunter_score REAL,
            snapshot_id TEXT,
            collection_ms REAL
        )
    """)

    conn.commit()


def insert_market_record(
    conn,
    asset,
    timestamp,
    latency_ms
):

    conn.execute("""
        INSERT INTO market_records (
            timestamp,
            market,
            asset,
            price,
            change_24h,
            volume_24h,
            collection_ms
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        "COINMARKETCAP",
        asset["symbol"],
        asset["price"],
        asset["change_24h"],
        asset["volume"],
        latency_ms
    ))

    conn.commit()


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 78)

    print(
        "             ARUNDA MARKET ADAPTER v0.4"
    )

    print("=" * 78)

    print(
        "Source   : COINMARKETCAP"
    )

    print(
        f"Database : {DB_PATH}"
    )

    print(
        "Assets   : " + ", ".join(ASSETS)
    )

    print("=" * 78)

    try:

        conn = get_db()

        ensure_schema(conn)

        ensure_market_records_schema(conn)

        data, latency_ms = fetch_cmc()

        assets = normalize_assets(data)

        if not assets:

            # Diagnostic information
            print()
            print("CMC RAW DATA TYPE :", type(data).__name__)

            if isinstance(data, dict):
                print(
                    "CMC DATA KEYS     :",
                    list(data.keys())[:20]
                )

            elif isinstance(data, list):
                print(
                    "CMC DATA LENGTH   :",
                    len(data)
                )

            raise RuntimeError(
                "CMC returned no supported assets. "
                f"Expected: {ASSETS}"
            )

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        inserted = 0

        print()

        print(
            "ASSET        PRICE              "
            "24H %       MARKET SCORE"
        )

        print("-" * 78)

        for symbol in ASSETS:

            item = assets.get(symbol)

            if not item:

                print(
                    f"{symbol:<12} NOT AVAILABLE"
                )

                continue

            asset = extract_asset(
                symbol,
                item
            )

            if not asset:

                print(
                    f"{symbol:<12} INVALID CMC DATA"
                )

                continue

            insert_market_data(
                conn,
                asset,
                timestamp
            )

            insert_market_record(
                conn,
                asset,
                timestamp,
                latency_ms
            )

            inserted += 1

            print(
                f"{symbol:<12}"
                f"{asset['price']:>15,.4f}   "
                f"{asset['change_24h']:>8.2f}%   "
                f"{asset['market_score']:>10.2f}"
            )

        print()
        print("=" * 78)

        if inserted == 0:

            raise RuntimeError(
                "CMC connection succeeded but "
                "no market records were inserted."
            )

        print(
            f"MARKET RECORDS INSERTED : {inserted}"
        )

        print(
            "Source                  : COINMARKETCAP"
        )

        print(
            "Engine                  : "
            f"{ENGINE_VERSION}"
        )

        print(
            "Database                : arunda.db"
        )

        print("=" * 78)

        conn.close()

    except Exception as e:

        print()
        print("=" * 78)

        print(
            "MARKET ADAPTER ERROR"
        )

        print("=" * 78)

        print(
            repr(e)
        )

        print("=" * 78)

        raise


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":
    main()