import urllib.request
import json

url = "https://pro-api.coinmarketcap.com/public-api/v3/cryptocurrency/quotes/latest?id=1&convert=USD"

req = urllib.request.Request(
    url,
    headers={
        "Accept": "application/json",
        "User-Agent": "Arunda/1.0"
    }
)

try:
    with urllib.request.urlopen(req, timeout=10) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

        print("=" * 70)
        print("ARUNDA CMC RAW TEST")
        print("=" * 70)

        print(json.dumps(
            data,
            indent=2
        ))

except Exception as e:

    print("CMC ERROR:")
    print(e)