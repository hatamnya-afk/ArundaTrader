import requests
import csv
import os
import time
from datetime import datetime

MARKETS_URL = "https://api.bitpin.ir/v1/mkt/markets/"
ORDERBOOK_URL = "https://api.bitpin.ir/v4/mth/orderbook/{}/?limit=50"

INTERVAL = 15
TOP_N = 20

CSV_FILE = "hunter_records.csv"

EXCLUDED = {
    "USDT",
    "USDC",
    "DAI",
    "FDUSD",
    "TUSD",
    "WBTC",
    "WETH",
}


def get_markets():

    r = requests.get(
        MARKETS_URL,
        timeout=10
    )

    r.raise_for_status()

    return r.json()["results"]


def get_change(market):

    info = market.get("order_book_info") or {}

    if info.get("change") is not None:
        return float(info["change"])

    info = market.get("price_info") or {}

    if info.get("change") is not None:
        return float(info["change"])

    return 0.0


def get_candidates():

    markets = get_markets()

    candidates = []

    for m in markets:

        if not m.get("tradable"):
            continue

        if m.get("suspended"):
            continue

        currency = m.get("currency1") or {}

        asset = currency.get("code")

        if not asset:
            continue

        if asset in EXCLUDED:
            continue

        price = float(m.get("price") or 0)
        volume = float(m.get("volume_24h") or 0)
        change = get_change(m)

        if price <= 0 or volume <= 0:
            continue

        # فیلتر اولیه
        volume_score = min(volume / 1e12 * 10, 60)
        momentum_score = min(abs(change) * 20, 40)

        score = volume_score + momentum_score

        candidates.append({
            "id": m["id"],
            "code": m["code"],
            "asset": asset,
            "price": price,
            "volume": volume,
            "change": change,
            "score": score,
        })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidates[:TOP_N]


def get_orderbook(market_id):

    url = ORDERBOOK_URL.format(market_id)

    r = requests.get(
        url,
        timeout=10
    )

    r.raise_for_status()

    return r.json()


def calculate_orderbook(ob):

    bids = ob.get("bids", [])
    asks = ob.get("asks", [])

    if not bids or not asks:
        return None

    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])

    bid_volume = sum(
        float(x[1])
        for x in bids
    )

    ask_volume = sum(
        float(x[1])
        for x in asks
    )

    total = bid_volume + ask_volume

    pressure = (
        bid_volume / total * 100
        if total > 0
        else 0
    )

    mid = (best_bid + best_ask) / 2

    spread = best_ask - best_bid

    spread_pct = (
        spread / mid * 100
        if mid > 0
        else 0
    )

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": mid,
        "spread_pct": spread_pct,
        "bid_volume": bid_volume,
        "ask_volume": ask_volume,
        "pressure": pressure,
    }


def init_csv():

    if os.path.exists(CSV_FILE):
        return

    columns = [
        "timestamp",
        "market",
        "asset",
        "price",
        "change_24h",
        "volume_24h",
        "best_bid",
        "best_ask",
        "mid",
        "spread_pct",
        "bid_volume",
        "ask_volume",
        "pressure",
        "hunter_score",
    ]

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=columns
        )

        writer.writeheader()


def record():

    candidates = get_candidates()

    timestamp = datetime.now().isoformat()

    rows = []

    for coin in candidates:

        try:

            ob = get_orderbook(
                coin["id"]
            )

            data = calculate_orderbook(ob)

            if data is None:
                continue

            row = {
                "timestamp": timestamp,
                "market": coin["code"],
                "asset": coin["asset"],
                "price": coin["price"],
                "change_24h": coin["change"],
                "volume_24h": coin["volume"],
                "best_bid": data["best_bid"],
                "best_ask": data["best_ask"],
                "mid": data["mid"],
                "spread_pct": data["spread_pct"],
                "bid_volume": data["bid_volume"],
                "ask_volume": data["ask_volume"],
                "pressure": data["pressure"],
                "hunter_score": coin["score"],
            }

            rows.append(row)

        except Exception as e:

            print(
                f"[ERROR] {coin['code']}: {e}"
            )

    if not rows:
        return 0

    with open(
        CSV_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
        )

        writer.writerows(rows)

    return len(rows)


def main():

    init_csv()

    print()
    print("==========================================")
    print("       ARUNDA HUNTER RECORDER v0.1")
    print("==========================================")
    print()
    print(f"Top candidates : {TOP_N}")
    print(f"Interval       : {INTERVAL} seconds")
    print(f"File           : {CSV_FILE}")
    print()
    print("Recording started...")
    print("Press CTRL+C to stop.")
    print()

    while True:

        start = time.time()

        try:

            count = record()

            print(
                f"{datetime.now():%H:%M:%S} "
                f"| recorded: {count}"
            )

        except Exception as e:

            print(
                f"[SYSTEM ERROR] {e}"
            )

        elapsed = time.time() - start

        sleep_time = max(
            0,
            INTERVAL - elapsed
        )

        time.sleep(sleep_time)


if __name__ == "__main__":
    main()