import os
import requests

API_KEY = os.getenv("LUNARCRUSH_API_KEY")
BASE_URL = "https://lunarcrush.com/api4/public"

def get_coin(symbol):
    url = f"{BASE_URL}/coins/{symbol.upper()}/v1"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code == 200:
            result = r.json()
            data = result.get("data", {})

            return {
                "status": "OK",
                "symbol": symbol.upper(),
                "galaxy_score": data.get("galaxy_score"),
                "alt_rank": data.get("alt_rank"),
                "change_24h": data.get("percent_change_24h"),
                "change_7d": data.get("percent_change_7d"),
                "volume_24h": data.get("volume_24h"),
                "market_cap": data.get("market_cap"),
            }

        elif r.status_code == 401:
            return {
                "status": "UNAVAILABLE",
                "symbol": symbol.upper(),
                "reason": "401_UNAUTHORIZED"
            }

        else:
            return {
                "status": "ERROR",
                "symbol": symbol.upper(),
                "reason": f"HTTP_{r.status_code}"
            }

    except Exception as e:
        return {
            "status": "ERROR",
            "symbol": symbol.upper(),
            "reason": str(e)
        }


if __name__ == "__main__":

    print("=" * 60)
    print("       ARUNDA LUNARCRUSH CONNECTOR v0.2")
    print("=" * 60)

    symbols = [
        "BTC",
        "ETH",
        "SOL",
        "UNI",
        "INJ",
        "YGG"
    ]

    for symbol in symbols:

        x = get_coin(symbol)

        if x["status"] == "OK":

            print(
                f"{symbol:6} | "
                f"Galaxy: {x['galaxy_score']} | "
                f"24h: {x['change_24h']:.2f}% | "
                f"7d: {x['change_7d']:.2f}%"
            )

        else:

            print(
                f"{symbol:6} | "
                f"{x['status']} | "
                f"{x['reason']}"
            )