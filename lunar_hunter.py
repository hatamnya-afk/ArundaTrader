import os
import requests
import time

API_KEY = os.getenv("LUNARCRUSH_API_KEY")
BASE_URL = "https://lunarcrush.com/api4/public"


def get_coin(symbol, retries=2):

    url = f"{BASE_URL}/coins/{symbol.upper()}/v1"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    for attempt in range(retries + 1):

        try:

            r = requests.get(
                url,
                headers=headers,
                timeout=15
            )

            if r.status_code == 200:

                data = r.json().get("data", {})

                return {
                    "status": "OK",
                    "symbol": symbol.upper(),
                    "galaxy": data.get("galaxy_score"),
                    "change_24h": data.get("percent_change_24h"),
                    "change_7d": data.get("percent_change_7d"),
                    "volume_24h": data.get("volume_24h"),
                    "market_cap": data.get("market_cap")
                }

            if r.status_code == 401 and attempt < retries:

                time.sleep(1)
                continue

            return {
                "status": "UNAVAILABLE",
                "symbol": symbol.upper(),
                "reason": f"HTTP_{r.status_code}"
            }

        except Exception as e:

            if attempt < retries:
                time.sleep(1)
                continue

            return {
                "status": "ERROR",
                "symbol": symbol.upper(),
                "reason": str(e)
            }


if __name__ == "__main__":

    print()
    print("=" * 70)
    print("          ARUNDA CROSS-MARKET RADAR v0.1")
    print("=" * 70)

    symbols = [
        "BTC",
        "ETH",
        "SOL",
        "INJ",
        "UNI",
        "YGG",
        "LINK",
        "SEI",
        "SUI",
        "AVAX"
    ]

    results = []

    for symbol in symbols:

        x = get_coin(symbol)
        results.append(x)

        if x["status"] == "OK":

            print(
                f"{symbol:6} | "
                f"Galaxy {str(x['galaxy']):>5} | "
                f"24h {x['change_24h']:>7.2f}% | "
                f"7d {x['change_7d']:>7.2f}%"
            )

        else:

            print(
                f"{symbol:6} | "
                f"{x['status']} | "
                f"{x['reason']}"
            )

    print("=" * 70)
    print(f"Markets checked: {len(results)}")
    print("=" * 70)