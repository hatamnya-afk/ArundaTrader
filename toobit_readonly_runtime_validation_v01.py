import os
import time
import hmac
import hashlib
import requests
import json

BASE_URL = "https://api.toobit.com"

API_KEY = os.getenv("TOOBIT_API_KEY")
SECRET_KEY = os.getenv("TOOBIT_API_SECRET")

TIMEOUT = 15


def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def public_get(endpoint, params=None):
    r = requests.get(
        BASE_URL + endpoint,
        params=params or {},
        timeout=TIMEOUT
    )
    return r.status_code, r.json()


def signed_get(endpoint):
    params = {
        "timestamp": int(time.time() * 1000),
        "recvWindow": 5000,
    }

    params["signature"] = sign(params)

    headers = {
        "X-BB-APIKEY": API_KEY
    }

    r = requests.get(
        BASE_URL + endpoint,
        params=params,
        headers=headers,
        timeout=TIMEOUT
    )

    try:
        data = r.json()
    except Exception:
        data = r.text

    return r.status_code, data


def main():

    print("=" * 72)
    print("TOOBIT API READ-ONLY RUNTIME VALIDATION v0.1")
    print("=" * 72)

    print("EXECUTION_ENABLED       : FALSE")
    print("ORDER_SUBMISSION        : BLOCKED")
    print("ORDER_CANCELLATION      : BLOCKED")
    print("WITHDRAW                 : BLOCKED")
    print("DATABASE_WRITE           : FALSE")
    print()

    if not API_KEY or not SECRET_KEY:
        print("STATUS                  : BLOCKED")
        print("REASON                  : TOOBIT_API_KEY / TOOBIT_API_SECRET missing")
        return 2

    # ------------------------------------------------------------------
    # 1. PUBLIC CONNECTIVITY
    # ------------------------------------------------------------------

    print("[1] PUBLIC TIME")

    try:
        status, data = public_get("/api/v1/time")
        print("HTTP_STATUS             :", status)
        print("RESPONSE_OK             :", status == 200)
    except Exception as e:
        print("STATUS                  : FAIL")
        print("ERROR                   :", repr(e))
        return 1

    # ------------------------------------------------------------------
    # 2. EXCHANGE INFO
    # ------------------------------------------------------------------

    print()
    print("[2] EXCHANGE INFO")

    try:
        status, data = public_get("/api/v1/exchangeInfo")

        print("HTTP_STATUS             :", status)

        if status == 200 and isinstance(data, dict):
            symbols = data.get("symbols", [])

            print("SYMBOL_COUNT            :", len(symbols))

            if symbols:
                sample = symbols[:5]
                print("SAMPLE_SYMBOLS          :")

                for item in sample:
                    print(
                        " ",
                        item.get("symbol"),
                        "| status=",
                        item.get("status")
                    )

            exchange_info_pass = True
        else:
            exchange_info_pass = False

    except Exception as e:
        print("STATUS                  : FAIL")
        print("ERROR                   :", repr(e))
        exchange_info_pass = False

    # ------------------------------------------------------------------
    # 3. ACCOUNT
    # ------------------------------------------------------------------

    print()
    print("[3] ACCOUNT")

    try:
        status, data = signed_get("/api/v1/account")

        print("HTTP_STATUS             :", status)

        account_pass = status == 200

        if account_pass and isinstance(data, dict):

            balances = data.get("balances", [])

            print("BALANCE_ROWS            :", len(balances))

            for b in balances[:10]:
                print(
                    " ",
                    b.get("coin"),
                    "| total=",
                    b.get("total"),
                    "| free=",
                    b.get("free"),
                    "| locked=",
                    b.get("locked")
                )

        else:
            print("ACCOUNT_RESPONSE        :", data)

    except Exception as e:
        print("STATUS                  : FAIL")
        print("ERROR                   :", repr(e))
        account_pass = False

    # ------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------

    print()
    print("=" * 72)
    print("RESULT")
    print("=" * 72)

    print("PUBLIC_TIME             :", "PASS")
    print("EXCHANGE_INFO           :", "PASS" if exchange_info_pass else "FAIL")
    print("ACCOUNT_READ            :", "PASS" if account_pass else "FAIL")

    overall = exchange_info_pass and account_pass

    print()
    print("OVERALL                 :", "PASS" if overall else "FAIL")
    print("EXECUTION               : DISABLED")
    print("ORDER_SUBMISSION        : BLOCKED")
    print("DATABASE_WRITE          : FALSE")
    print("EXCHANGE_WRITE          : FALSE")
    print("=" * 72)

    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())