import os
import time
import hmac
import hashlib
import requests

BASE_URL = "https://api.toobit.com"
TIMEOUT = 15

API_KEY = os.getenv("TOOBIT_API_KEY")
SECRET_KEY = os.getenv("TOOBIT_API_SECRET")


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
    try:
        data = r.json()
    except Exception:
        data = r.text
    return r.status_code, data


def signed_get(endpoint, params=None):
    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 5000
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

    print("=" * 80)
    print("TOOBIT ACCOUNT + SYMBOL + TRADING-CONSTRAINT")
    print("READ-ONLY CONTRACT VALIDATION v0.1")
    print("=" * 80)

    print("EXECUTION_ENABLED       : FALSE")
    print("ORDER_SUBMISSION        : BLOCKED")
    print("ORDER_CANCELLATION      : BLOCKED")
    print("WITHDRAW                : BLOCKED")
    print("DATABASE_WRITE          : FALSE")
    print("EXCHANGE_WRITE          : FALSE")
    print()

    if not API_KEY or not SECRET_KEY:
        print("STATUS                  : BLOCKED")
        print("REASON                  : TOOBIT_API_KEY / TOOBIT_API_SECRET missing")
        return 2

    # ================================================================
    # 1. ACCOUNT
    # ================================================================

    print("[1] ACCOUNT")

    account_pass = False

    try:
        status, data = signed_get("/api/v1/account")

        print("HTTP_STATUS             :", status)

        if status == 200 and isinstance(data, dict):

            account_pass = True

            print("ACCOUNT_RESPONSE        : PASS")

            account_type = data.get("accountType")
            can_trade = data.get("canTrade")
            can_withdraw = data.get("canWithdraw")
            can_deposit = data.get("canDeposit")

            print("ACCOUNT_TYPE            :", account_type)
            print("CAN_TRADE               :", can_trade)
            print("CAN_WITHDRAW            :", can_withdraw)
            print("CAN_DEPOSIT             :", can_deposit)

            balances = data.get("balances", [])

            print("BALANCE_ROWS            :", len(balances))

            nonzero = []

            for b in balances:
                try:
                    total = float(b.get("total", 0))
                except Exception:
                    total = 0

                if total != 0:
                    nonzero.append(b)

            print("NONZERO_BALANCES        :", len(nonzero))

            for b in nonzero[:20]:
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
            print("ACCOUNT_RESPONSE        : FAIL")
            print("RESPONSE                :", data)

    except Exception as e:
        print("ACCOUNT_EXCEPTION       :", repr(e))

    # ================================================================
    # 2. EXCHANGE INFO
    # ================================================================

    print()
    print("[2] EXCHANGE INFO")

    exchange_pass = False
    symbols = []

    try:
        status, data = public_get("/api/v1/exchangeInfo")

        print("HTTP_STATUS             :", status)

        if status == 200 and isinstance(data, dict):

            exchange_pass = True
            symbols = data.get("symbols", [])

            print("EXCHANGE_INFO           : PASS")
            print("SYMBOL_COUNT            :", len(symbols))

        else:
            print("EXCHANGE_INFO           : FAIL")
            print("RESPONSE                :", data)

    except Exception as e:
        print("EXCHANGE_EXCEPTION      :", repr(e))

    # ================================================================
    # 3. SYMBOL CONTRACT
    # ================================================================

    print()
    print("[3] SYMBOL CONTRACT")

    symbol_pass = False
    trading_symbols = []

    if exchange_pass:

        required_symbol_fields = [
            "symbol",
            "status",
        ]

        valid_symbols = 0
        missing_field_symbols = 0

        for s in symbols:

            if all(field in s for field in required_symbol_fields):
                valid_symbols += 1
            else:
                missing_field_symbols += 1

            if s.get("status") == "TRADING":
                trading_symbols.append(s)

        print("TOTAL_SYMBOLS           :", len(symbols))
        print("TRADING_SYMBOLS         :", len(trading_symbols))
        print("VALID_SYMBOL_ROWS       :", valid_symbols)
        print("MISSING_REQUIRED_FIELDS :", missing_field_symbols)

        symbol_pass = (
            len(symbols) > 0
            and valid_symbols == len(symbols)
        )

        print(
            "SYMBOL_CONTRACT         :",
            "PASS" if symbol_pass else "FAIL"
        )

    else:
        print("SYMBOL_CONTRACT         : BLOCKED")

    # ================================================================
    # 4. TRADING CONSTRAINTS
    # ================================================================

    print()
    print("[4] TRADING CONSTRAINTS")

    constraints_pass = False
    constraint_rows = 0
    symbols_with_filters = 0

    if symbol_pass:

        samples = trading_symbols[:20]

        print("INSPECTED_SYMBOLS       :", len(samples))

        for s in samples:

            symbol = s.get("symbol")
            filters = s.get("filters", [])

            if isinstance(filters, list):
                constraint_rows += len(filters)

            if filters:
                symbols_with_filters += 1

            print()
            print("SYMBOL                  :", symbol)
            print("STATUS                  :", s.get("status"))

            base_asset = s.get("baseAsset")
            quote_asset = s.get("quoteAsset")

            print("BASE_ASSET              :", base_asset)
            print("QUOTE_ASSET             :", quote_asset)

            if "baseAssetPrecision" in s:
                print(
                    "BASE_PRECISION          :",
                    s.get("baseAssetPrecision")
                )

            if "quotePrecision" in s:
                print(
                    "QUOTE_PRECISION         :",
                    s.get("quotePrecision")
                )

            if filters:
                print("FILTERS                 :")

                for f in filters:

                    if isinstance(f, dict):
                        print(
                            " ",
                            f.get("filterType"),
                            "|",
                            {
                                k: v
                                for k, v in f.items()
                                if k != "filterType"
                            }
                        )

        constraints_pass = (
            len(samples) > 0
            and symbols_with_filters > 0
        )

        print()
        print("FILTER_ROWS             :", constraint_rows)
        print("SYMBOLS_WITH_FILTERS    :", symbols_with_filters)
        print(
            "TRADING_CONSTRAINT     :",
            "PASS" if constraints_pass else "FAIL"
        )

    else:
        print("TRADING_CONSTRAINT      : BLOCKED")

    # ================================================================
    # 5. READ-ONLY SYMBOL SPOT CHECK
    # ================================================================

    print()
    print("[5] REPRESENTATIVE SYMBOL CHECK")

    representative_pass = False

    targets = [
        "BTCUSDT",
        "ETHUSDT",
        "DOGEUSDT",
        "AAVEUSDT",
    ]

    available = {
        s.get("symbol"): s
        for s in symbols
        if isinstance(s, dict)
    }

    found = 0

    for target in targets:

        s = available.get(target)

        if s:
            found += 1

            print(
                target,
                "| status=",
                s.get("status"),
                "| base=",
                s.get("baseAsset"),
                "| quote=",
                s.get("quoteAsset")
            )
        else:
            print(target, "| NOT_FOUND")

    representative_pass = found > 0

    print(
        "REPRESENTATIVE_CHECK    :",
        "PASS" if representative_pass else "FAIL"
    )

    # ================================================================
    # FINAL
    # ================================================================

    overall = (
        account_pass
        and exchange_pass
        and symbol_pass
        and constraints_pass
        and representative_pass
    )

    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    print("ACCOUNT                 :", "PASS" if account_pass else "FAIL")
    print("EXCHANGE_INFO           :", "PASS" if exchange_pass else "FAIL")
    print("SYMBOL_CONTRACT         :", "PASS" if symbol_pass else "FAIL")
    print("TRADING_CONSTRAINT      :", "PASS" if constraints_pass else "FAIL")
    print("REPRESENTATIVE_CHECK    :", "PASS" if representative_pass else "FAIL")

    print()
    print("OVERALL                 :", "PASS" if overall else "FAIL")

    print()
    print("EXECUTION               : DISABLED")
    print("ORDER_SUBMISSION        : BLOCKED")
    print("ORDER_CANCELLATION      : BLOCKED")
    print("WITHDRAW                : BLOCKED")
    print("DATABASE_WRITE          : FALSE")
    print("EXCHANGE_WRITE          : FALSE")

    print("=" * 80)

    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())