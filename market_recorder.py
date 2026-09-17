import requests
import csv
import time
from datetime import datetime

API_URL = "https://api.bitpin.ir/v4/mth/orderbook/1/?limit=50"

FILE_NAME = "market_data.csv"

INTERVAL = 1


def get_orderbook():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def weighted_pressure(levels, reference_price, max_distance):

    weighted_volume = 0

    for price, amount in levels:

        price = float(price)
        amount = float(amount)

        distance = abs(price - reference_price) / reference_price

        if distance <= max_distance:

            weight = 1 - (distance / max_distance)

            weighted_volume += amount * weight

    return weighted_volume


def analyze(data):

    asks = [(float(p), float(a)) for p, a in data["asks"]]
    bids = [(float(p), float(a)) for p, a in data["bids"]]

    best_bid = max(p for p, a in bids)
    best_ask = min(p for p, a in asks)

    mid_price = (best_bid + best_ask) / 2

    spread = best_ask - best_bid
    spread_percent = (spread / mid_price) * 100

    pressures = {}

    for distance in [0.001, 0.0025, 0.005, 0.01, 0.02]:

        bid = weighted_pressure(
            bids,
            mid_price,
            distance
        )

        ask = weighted_pressure(
            asks,
            mid_price,
            distance
        )

        total = bid + ask

        pressure = bid / total * 100 if total else 50

        pressures[str(distance)] = pressure

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "spread": spread,
        "spread_percent": spread_percent,
        "bid_volume": float(data["volume_bid"]),
        "ask_volume": float(data["volume_ask"]),
        "pressure_01": pressures["0.001"],
        "pressure_025": pressures["0.0025"],
        "pressure_05": pressures["0.005"],
        "pressure_1": pressures["0.01"],
        "pressure_2": pressures["0.02"],
    }


headers = [
    "timestamp",
    "mid_price",
    "best_bid",
    "best_ask",
    "spread",
    "spread_percent",
    "bid_volume",
    "ask_volume",
    "pressure_01",
    "pressure_025",
    "pressure_05",
    "pressure_1",
    "pressure_2",
]


try:

    with open(
        FILE_NAME,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=headers
        )

        if file.tell() == 0:
            writer.writeheader()

        print("======================================")
        print("     ARUNDA MARKET RECORDER v0.1")
        print("======================================")
        print("Recording Bitpin BTC/IRT...")
        print("Press CTRL+C to stop.")
        print()

        while True:

            try:

                data = get_orderbook()

                result = analyze(data)

                result["timestamp"] = datetime.now().isoformat()

                writer.writerow(result)

                file.flush()

                print(
                    f"{result['timestamp']} | "
                    f"BTC {result['mid_price']:,.0f} | "
                    f"P0.5 {result['pressure_05']:.2f}% | "
                    f"Spread {result['spread_percent']:.3f}%"
                )

                time.sleep(INTERVAL)

            except Exception as e:

                print("Error:", e)

                time.sleep(3)

except KeyboardInterrupt:

    print()
    print("Recorder stopped.")