import requests

MARKETS_URL = "https://api.bitpin.ir/v1/mkt/markets/"


def get_markets():
    response = requests.get(MARKETS_URL, timeout=10)
    response.raise_for_status()
    return response.json()["results"]


def scan_markets(markets):

    candidates = []

    for market in markets:

        if not market.get("tradable", False):
            continue

        if market.get("suspended", False):
            continue

        currency = market["currency1"]

        code = market["code"]
        title = market["title"]

        price = float(market.get("price") or 0)
        volume_24h = float(market.get("volume_24h") or 0)

        if price <= 0:
            continue

        candidates.append({
            "id": market["id"],
            "code": code,
            "title": title,
            "price": price,
            "volume_24h": volume_24h,
            "currency": currency["code"],
            "risk": currency.get("high_risk", False),
        })

    return candidates


markets = get_markets()

candidates = scan_markets(markets)

print()
print("==============================================")
print("          ARUNDA HUNTER v0.1")
print("==============================================")
print()
print(f"Total markets received : {len(markets)}")
print(f"Tradable candidates    : {len(candidates)}")
print()

# مرتب‌سازی اولیه بر اساس حجم 24 ساعته
candidates.sort(
    key=lambda x: x["volume_24h"],
    reverse=True
)

print("TOP 30 BY 24H VOLUME")
print("----------------------------------------------")

for i, coin in enumerate(candidates[:30], 1):

    print(
        f"{i:02d} | "
        f"{coin['code']:12} | "
        f"Price: {coin['price']:,.0f} | "
        f"Vol: {coin['volume_24h']:,.0f}"
    )

print()
print("==============================================")