import requests

API_URL = "https://api.bitpin.ir/v4/mth/orderbook/1/?limit=50"


def get_orderbook():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def analyze_orderbook(data):
    asks = [(float(price), float(amount)) for price, amount in data["asks"]]
    bids = [(float(price), float(amount)) for price, amount in data["bids"]]

    best_ask = min(price for price, amount in asks)
    best_bid = max(price for price, amount in bids)

    spread = best_ask - best_bid
    spread_percent = (spread / best_bid) * 100

    total_ask = sum(amount for price, amount in asks)
    total_bid = sum(amount for price, amount in bids)

    imbalance = total_bid / (total_bid + total_ask) * 100

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "spread_percent": spread_percent,
        "bid_volume": total_bid,
        "ask_volume": total_ask,
        "bid_pressure": imbalance,
    }


data = get_orderbook()
result = analyze_orderbook(data)

print("========== ARUNDA ORDER BOOK ==========")
print(f"Best Bid       : {result['best_bid']:,.0f}")
print(f"Best Ask       : {result['best_ask']:,.0f}")
print(f"Spread         : {result['spread']:,.0f}")
print(f"Spread %       : {result['spread_percent']:.4f}%")
print(f"Bid Volume     : {result['bid_volume']:.6f} BTC")
print(f"Ask Volume     : {result['ask_volume']:.6f} BTC")
print(f"Bid Pressure   : {result['bid_pressure']:.2f}%")
print("========================================")