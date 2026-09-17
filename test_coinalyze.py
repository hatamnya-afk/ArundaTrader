import os
import requests
import time

API_KEY = os.getenv("COINALYZE_API_KEY")

BASE_URL = "https://api.coinalyze.net/v1"

HEADERS = {
    "api_key": API_KEY
}


def test_endpoint(name, endpoint, params=None):

    print("=" * 70)
    print(f"COINALYZE TEST | {name}")
    print("=" * 70)

    start = time.time()

    try:

        response = requests.get(
            BASE_URL + endpoint,
            headers=HEADERS,
            params=params,
            timeout=15
        )

        latency = int(
            (time.time() - start) * 1000
        )

        print(f"HTTP    : {response.status_code}")
        print(f"Latency : {latency} ms")

        try:
            data = response.json()
            print("Response:")
            print(data)

        except Exception:
            print(response.text[:1000])

        print()

        return response.status_code == 200

    except Exception as e:

        print("ERROR:", repr(e))
        print()

        return False


def main():

    print()
    print("=" * 70)
    print("          ARUNDA COINALYZE POSITIONING TEST")
    print("=" * 70)

    if not API_KEY:

        print()
        print("ERROR: COINALYZE_API_KEY is missing")
        print()

        return

    print()
    print("API KEY : OK")
    print()

    # --------------------------------------------------------
    # 1. FUTURES SYMBOLS
    # --------------------------------------------------------

    test_endpoint(
        "FUTURES SYMBOLS",
        "/future-markets"
    )

    # --------------------------------------------------------
    # 2. OPEN INTEREST
    # --------------------------------------------------------

    test_endpoint(
        "OPEN INTEREST",
        "/open-interest",
        {
            "symbols": "BTCUSDT_PERP.A"
        }
    )

    # --------------------------------------------------------
    # 3. FUNDING RATE
    # --------------------------------------------------------

    test_endpoint(
        "FUNDING RATE",
        "/funding-rate",
        {
            "symbols": "BTCUSDT_PERP.A"
        }
    )

    # --------------------------------------------------------
    # 4. LIQUIDATIONS
    # --------------------------------------------------------

    test_endpoint(
        "LIQUIDATIONS",
        "/liquidation-history",
        {
            "symbols": "BTCUSDT_PERP.A"
        }
    )

    # --------------------------------------------------------
    # 5. LONG / SHORT
    # --------------------------------------------------------

    test_endpoint(
        "LONG SHORT",
        "/long-short-ratio",
        {
            "symbols": "BTCUSDT_PERP.A"
        }
    )

    print("=" * 70)
    print("COINALYZE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()