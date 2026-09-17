import requests

API_URL = "https://api.bitpin.ir/v1/mkt/markets/"


def get_btc_market():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()

    data = response.json()

    for market in data["results"]:
        if market["code"] == "BTC_IRT":
            return market

    raise ValueError("BTC_IRT market not found")


market = get_btc_market()

print("========== ARUNDA TRADER ==========")
print(f"Market : {market['title']}")
print(f"Code   : {market['code']}")
print(f"Price  : {market['price']} IRT")
print(f"24h Vol: {market['volume_24h']}")
print(f"Change : {market['price_info']['change']}")
print("===================================")