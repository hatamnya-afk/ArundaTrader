import requests

API_URL = "https://api.bitpin.ir/v4/mth/orderbook/1/?limit=50"


def get_orderbook():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def weighted_pressure(levels, reference_price, max_distance):
    weighted_volume = 0

    for price, amount in levels:
        distance = abs(price - reference_price) / reference_price

        if distance <= max_distance:
            weight = 1 - (distance / max_distance)
            weighted_volume += amount * weight

    return weighted_volume


data = get_orderbook()

asks = [(float(p), float(a)) for p, a in data["asks"]]
bids = [(float(p), float(a)) for p, a in data["bids"]]

best_bid = max(p for p, a in bids)
best_ask = min(p for p, a in asks)

mid_price = (best_bid + best_ask) / 2

distances = [
    0.001,
    0.0025,
    0.005,
    0.01,
    0.02,
]

print("========== ARUNDA WEIGHTED ORDER BOOK ==========")
print(f"Mid Price: {mid_price:,.0f}")
print()

for distance in distances:

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

    pressure = (bid / total * 100) if total else 50

    print(
        f"{distance*100:>5.2f}% "
        f"| Bid: {bid:.6f} "
        f"| Ask: {ask:.6f} "
        f"| Bid Pressure: {pressure:.2f}%"
    )

print("================================================")