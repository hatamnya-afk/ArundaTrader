import os
import json
import urllib.request
import urllib.error
import time


API_KEY = os.getenv("COINGLASS_API_KEY")

BASE_URL = "https://open-api-v4.coinglass.com"


def request(endpoint, params=None):

    if not API_KEY:
        print("ERROR: COINGLASS_API_KEY is not set")
        return None

    url = BASE_URL + endpoint

    if params:
        query = "&".join(
            f"{k}={v}"
            for k, v in params.items()
        )
        url += "?" + query

    req = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "CG-API-KEY": API_KEY,
            "User-Agent": "Arunda/1.0"
        }
    )

    start = time.time()

    try:

        with urllib.request.urlopen(
            req,
            timeout=15
        ) as response:

            elapsed = (
                time.time() - start
            ) * 1000

            raw = response.read()

            data = json.loads(
                raw.decode("utf-8")
            )

            print()
            print("=" * 70)
            print("COINGLASS V4 TEST")
            print("=" * 70)

            print(
                f"Endpoint : {endpoint}"
            )

            print(
                f"HTTP     : {response.status}"
            )

            print(
                f"Latency  : {elapsed:.0f} ms"
            )

            print(
                f"Code     : {data.get('code')}"
            )

            print(
                f"Message  : {data.get('msg')}"
            )

            print()
            print(
                json.dumps(
                    data,
                    indent=2
                )
            )

            return data

    except urllib.error.HTTPError as e:

        print()
        print(
            f"HTTP ERROR: {e.code}"
        )

        try:
            print(
                e.read().decode("utf-8")
            )
        except Exception:
            pass

    except Exception as e:

        print()
        print(
            f"CONNECTION ERROR: {e}"
        )

    return None


# ============================================================
# TEST 1 — SUPPORTED COINS
# ============================================================

request(
    "/api/futures/supported-coins"
)


# ============================================================
# TEST 2 — OPEN INTEREST
# ============================================================

request(
    "/api/futures/open-interest/exchange-list",
    {
        "symbol": "BTC"
    }
)


# ============================================================
# TEST 3 — LIQUIDATIONS
# ============================================================

request(
    "/api/futures/liquidation/exchange-list",
    {
        "symbol": "BTC",
        "range": "1h"
    }
)