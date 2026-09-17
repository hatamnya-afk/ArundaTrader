import json
import time
import requests
import websocket


BASE_URL = "https://api.toobit.com"
WS_URL = "wss://stream.toobit.com/quote/ws/v1"

TIMEOUT = 15

TARGET_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "DOGEUSDT",
    "AAVEUSDT",
    "UNIUSDT",
    "XRPUSDT",
]


def rest_get(endpoint, params=None):
    response = requests.get(
        BASE_URL + endpoint,
        params=params or {},
        timeout=TIMEOUT,
    )

    try:
        data = response.json()
    except Exception:
        data = response.text

    return response.status_code, data


def header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def main():

    print("=" * 80)
    print("TOOBIT MARKET DATA + WEBSOCKET")
    print("READ-ONLY RUNTIME VALIDATION v0.2")
    print("=" * 80)

    print("EXECUTION_ENABLED       : FALSE")
    print("ORDER_SUBMISSION        : BLOCKED")
    print("ORDER_CANCELLATION      : BLOCKED")
    print("WITHDRAW                : BLOCKED")
    print("DATABASE_WRITE          : FALSE")
    print("EXCHANGE_WRITE          : FALSE")

    # ============================================================
    # 1. SERVER TIME
    # ============================================================

    header("[1] PUBLIC SERVER TIME")

    time_pass = False

    try:
        status, data = rest_get("/api/v1/time")

        print("HTTP_STATUS             :", status)
        print("RESPONSE                :", data)

        time_pass = status == 200

    except Exception as e:
        print("ERROR                   :", repr(e))

    # ============================================================
    # 2. EXCHANGE INFO
    # ============================================================

    header("[2] EXCHANGE INFO")

    exchange_pass = False
    symbols = []

    try:
        status, data = rest_get("/api/v1/exchangeInfo")

        print("HTTP_STATUS             :", status)

        if status == 200 and isinstance(data, dict):

            symbols = data.get("symbols", [])

            trading = [
                x for x in symbols
                if isinstance(x, dict)
                and x.get("status") == "TRADING"
            ]

            print("SYMBOL_COUNT            :", len(symbols))
            print("TRADING_SYMBOLS         :", len(trading))

            exchange_pass = len(symbols) > 0

        else:
            print("RESPONSE                :", data)

    except Exception as e:
        print("ERROR                   :", repr(e))

    # ============================================================
    # 3. 24HR TICKER
    # ============================================================

    header("[3] TICKER MARKET DATA")

    ticker_pass = False

    for symbol in TARGET_SYMBOLS:

        try:

            status, data = rest_get(
                "/quote/v1/ticker/24hr",
                {"symbol": symbol},
            )

            print()
            print("SYMBOL                  :", symbol)
            print("HTTP_STATUS             :", status)

            if status != 200:
                print("RESPONSE                :", data)
                continue

            if isinstance(data, list) and data:

                row = data[0]

                print("LAST                    :", row.get("c"))
                print("OPEN                    :", row.get("o"))
                print("HIGH                    :", row.get("h"))
                print("LOW                     :", row.get("l"))
                print("VOLUME                  :", row.get("v"))
                print("PRICE_CHANGE            :", row.get("pc"))
                print("PRICE_CHANGE_PERCENT    :", row.get("pcp"))

                ticker_pass = True

            else:

                print(
                    "RESPONSE                :",
                    json.dumps(data, ensure_ascii=False)[:1000]
                )

        except Exception as e:

            print("ERROR                   :", repr(e))

    # ============================================================
    # 4. ORDER BOOK
    # ============================================================

    header("[4] ORDERBOOK MARKET DATA")

    orderbook_pass = False

    for symbol in ["BTCUSDT", "ETHUSDT"]:

        try:

            status, data = rest_get(
                "/quote/v1/depth",
                {
                    "symbol": symbol,
                    "limit": 20,
                },
            )

            print()
            print("SYMBOL                  :", symbol)
            print("HTTP_STATUS             :", status)

            if status != 200:
                print("RESPONSE                :", data)
                continue

            if isinstance(data, dict):

                bids = data.get("b", [])
                asks = data.get("a", [])

                print("BID_LEVELS              :", len(bids))
                print("ASK_LEVELS              :", len(asks))

                if bids:
                    print("BEST_BID                :", bids[0])

                if asks:
                    print("BEST_ASK                :", asks[0])

                if bids and asks:
                    orderbook_pass = True

            else:

                print(
                    "RESPONSE                :",
                    json.dumps(data, ensure_ascii=False)[:1000]
                )

        except Exception as e:

            print("ERROR                   :", repr(e))

    # ============================================================
    # 5. WEBSOCKET
    # ============================================================

    header("[5] WEBSOCKET MARKET STREAM")

    ws_pass = False
    messages_received = 0
    ws_error = None

    def on_open(ws):

        print("WS_CONNECTED            : TRUE")

        subscribe = {
            "symbol": "BTCUSDT",
            "topic": "trade",
            "event": "sub",
            "params": {
                "binary": "false"
            },
        }

        print(
            "WS_SUBSCRIBE            :",
            json.dumps(subscribe)
        )

        ws.send(json.dumps(subscribe))

    def on_message(ws, message):

        nonlocal messages_received
        nonlocal ws_pass

        messages_received += 1

        print()
        print("WS_MESSAGE              :", messages_received)

        try:

            payload = json.loads(message)

            print(
                "WS_PAYLOAD              :",
                json.dumps(
                    payload,
                    ensure_ascii=False
                )[:2000]
            )

            if isinstance(payload, dict):

                topic = payload.get("topic")
                symbol = payload.get("symbol")
                data = payload.get("data")

                print("WS_TOPIC                :", topic)
                print("WS_SYMBOL               :", symbol)
                print(
                    "WS_DATA_TYPE            :",
                    type(data).__name__
                )

                if topic == "trade" and data:
                    ws_pass = True

            if messages_received >= 3:
                ws.close()

        except Exception as e:

            print("WS_PARSE_ERROR          :", repr(e))

    def on_error(ws, error):

        nonlocal ws_error

        ws_error = repr(error)

        print("WS_ERROR                :", ws_error)

    def on_close(ws, close_status_code, close_msg):

        print(
            "WS_CLOSED               :",
            close_status_code,
            close_msg
        )

    try:

        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        ws.run_forever(
            ping_interval=20,
            ping_timeout=10,
        )

    except Exception as e:

        ws_error = repr(e)

        print("WS_EXCEPTION            :", ws_error)

    # ============================================================
    # 6. FINAL
    # ============================================================

    header("FINAL RESULT")

    print(
        "PUBLIC_TIME             :",
        "PASS" if time_pass else "FAIL"
    )

    print(
        "EXCHANGE_INFO           :",
        "PASS" if exchange_pass else "FAIL"
    )

    print(
        "TICKER_DATA             :",
        "PASS" if ticker_pass else "FAIL"
    )

    print(
        "ORDERBOOK_DATA          :",
        "PASS" if orderbook_pass else "FAIL"
    )

    print(
        "WEBSOCKET               :",
        "PASS" if ws_pass else "FAIL"
    )

    print("WS_MESSAGES_RECEIVED    :", messages_received)

    overall = (
        time_pass
        and exchange_pass
        and ticker_pass
        and orderbook_pass
        and ws_pass
    )

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