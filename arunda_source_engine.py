import os
import json
import sqlite3
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone


# ============================================================
# ARUNDA SOURCE ENGINE v0.1
# ============================================================
#
# PURPOSE:
#   Test real connectivity and data availability of external
#   market / positioning / news / macro sources.
#
# IMPORTANT:
#   This engine DOES NOT trade.
#   This engine DOES NOT calculate indicators.
#
#   It answers one question:
#
#       "Which data sources are actually alive?"
#
# ============================================================


DB = "arunda.db"

ENGINE_VERSION = "SOURCE_ENGINE_v0.1"

TIMEOUT_SECONDS = 10


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

CMC_API_KEY = os.getenv("CMC_API_KEY")

COINAPI_API_KEY = os.getenv("COINAPI_API_KEY")

COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")

CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

FRED_API_KEY = os.getenv("FRED_API_KEY")


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    return sqlite3.connect(DB)


def create_tables(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS source_status (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,

            source TEXT NOT NULL,

            arm TEXT NOT NULL,

            status TEXT NOT NULL,

            http_status INTEGER,

            latency_ms REAL,

            data_received INTEGER,

            message TEXT,

            endpoint TEXT,

            engine_version TEXT

        )
    """)

    conn.commit()


# ============================================================
# TIME
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# HTTP
# ============================================================

def http_get(
    url,
    headers=None
):

    if headers is None:
        headers = {}

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )

    start = time.perf_counter()

    try:

        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS
        ) as response:

            body = response.read()

            elapsed = (
                time.perf_counter()
                - start
            ) * 1000

            return {
                "ok": True,
                "status": response.status,
                "latency_ms": round(
                    elapsed,
                    2
                ),
                "body": body
            }

    except urllib.error.HTTPError as e:

        elapsed = (
            time.perf_counter()
            - start
        ) * 1000

        try:
            body = e.read()
        except Exception:
            body = b""

        return {
            "ok": False,
            "status": e.code,
            "latency_ms": round(
                elapsed,
                2
            ),
            "body": body,
            "error": str(e)
        }

    except Exception as e:

        elapsed = (
            time.perf_counter()
            - start
        ) * 1000

        return {
            "ok": False,
            "status": None,
            "latency_ms": round(
                elapsed,
                2
            ),
            "body": b"",
            "error": str(e)
        }


# ============================================================
# JSON
# ============================================================

def parse_json(body):

    if not body:
        return None

    try:

        return json.loads(
            body.decode(
                "utf-8",
                errors="ignore"
            )
        )

    except Exception:

        return None


# ============================================================
# SOURCE RESULT
# ============================================================

def result(
    source,
    arm,
    status,
    http_status=None,
    latency_ms=None,
    data_received=False,
    message="",
    endpoint=""
):

    return {

        "timestamp": utc_now(),

        "source": source,

        "arm": arm,

        "status": status,

        "http_status": http_status,

        "latency_ms": latency_ms,

        "data_received": (
            1 if data_received else 0
        ),

        "message": message,

        "endpoint": endpoint,

        "engine_version": ENGINE_VERSION
    }


# ============================================================
# BINANCE
# ============================================================

def test_binance():

    endpoint = (
        "https://api.binance.com/api/v3/ping"
    )

    response = http_get(
        endpoint
    )

    if response["ok"]:

        return result(
            source="BINANCE",
            arm="REFERENCE_MARKET",
            status="ONLINE",
            http_status=response["status"],
            latency_ms=response["latency_ms"],
            data_received=True,
            message="Binance API reachable",
            endpoint=endpoint
        )

    return result(
        source="BINANCE",
        arm="REFERENCE_MARKET",
        status="OFFLINE",
        http_status=response["status"],
        latency_ms=response["latency_ms"],
        message=response.get(
            "error",
            "Unknown error"
        ),
        endpoint=endpoint
    )


# ============================================================
# COINMARKETCAP
# ============================================================

def test_coinmarketcap():

    #
    # CMC currently exposes a keyless public API path for
    # supported endpoints.
    #
    # We use Bitcoin as the first live test.
    #

    endpoint = (
        "https://pro-api.coinmarketcap.com/"
        "public-api/v3/cryptocurrency/"
        "quotes/latest?id=1&convert=USD"
    )

    headers = {
        "Accept": "application/json",
        "User-Agent": "ArundaSourceEngine/0.1"
    }

    #
    # If user supplied an API key, prefer authenticated API.
    #

    if CMC_API_KEY:

        endpoint = (
            "https://pro-api.coinmarketcap.com/"
            "v3/cryptocurrency/"
            "quotes/latest?id=1&convert=USD"
        )

        headers[
            "X-CMC_PRO_API_KEY"
        ] = CMC_API_KEY

    response = http_get(
        endpoint,
        headers
    )

    data = parse_json(
        response.get("body", b"")
    )

    if response["ok"] and data:

        return result(
            source="COINMARKETCAP",
            arm="MARKET",
            status="ONLINE",
            http_status=response["status"],
            latency_ms=response["latency_ms"],
            data_received=True,
            message="CMC returned JSON market data",
            endpoint=endpoint
        )

    return result(
        source="COINMARKETCAP",
        arm="MARKET",
        status=(
            "AUTH_REQUIRED"
            if response["status"] in (401, 403)
            else "OFFLINE"
        ),
        http_status=response["status"],
        latency_ms=response["latency_ms"],
        data_received=False,
        message=response.get(
            "error",
            "No valid JSON response"
        ),
        endpoint=endpoint
    )


# ============================================================
# COINAPI
# ============================================================

def test_coinapi():

    endpoint = (
        "https://rest.coinapi.io/v1/exchanges"
    )

    if not COINAPI_API_KEY:

        return result(
            source="COINAPI",
            arm="MARKET",
            status="CONFIG_REQUIRED",
            message=(
                "Set COINAPI_API_KEY "
                "before testing CoinAPI"
            ),
            endpoint=endpoint
        )

    headers = {
        "X-CoinAPI-Key": COINAPI_API_KEY,
        "Accept": "application/json",
        "User-Agent": "ArundaSourceEngine/0.1"
    }

    response = http_get(
        endpoint,
        headers
    )

    data = parse_json(
        response.get("body", b"")
    )

    if response["ok"] and isinstance(
        data,
        list
    ):

        return result(
            source="COINAPI",
            arm="MARKET",
            status="ONLINE",
            http_status=response["status"],
            latency_ms=response["latency_ms"],
            data_received=True,
            message="CoinAPI returned exchange data",
            endpoint=endpoint
        )

    return result(
        source="COINAPI",
        arm="MARKET",
        status=(
            "AUTH_ERROR"
            if response["status"] in (401, 403)
            else "OFFLINE"
        ),
        http_status=response["status"],
        latency_ms=response["latency_ms"],
        message=response.get(
            "error",
            "Invalid CoinAPI response"
        ),
        endpoint=endpoint
    )


# ============================================================
# COINGLASS
# ============================================================

def test_coinglass():

    endpoint = (
        "https://open-api-v4.coinglass.com/"
        "api/futures/supported-coins"
    )

    if not COINGLASS_API_KEY:

        return result(
            source="COINGLASS",
            arm="POSITIONING",
            status="CONFIG_REQUIRED",
            message=(
                "Set COINGLASS_API_KEY "
                "before testing CoinGlass"
            ),
            endpoint=endpoint
        )

    headers = {
        "CG-API-KEY": COINGLASS_API_KEY,
        "Accept": "application/json",
        "User-Agent": "ArundaSourceEngine/0.1"
    }

    response = http_get(
        endpoint,
        headers
    )

    data = parse_json(
        response.get("body", b"")
    )

    if response["ok"] and data:

        return result(
            source="COINGLASS",
            arm="POSITIONING",
            status="ONLINE",
            http_status=response["status"],
            latency_ms=response["latency_ms"],
            data_received=True,
            message="CoinGlass returned futures data",
            endpoint=endpoint
        )

    return result(
        source="COINGLASS",
        arm="POSITIONING",
        status=(
            "AUTH_ERROR"
            if response["status"] in (401, 403)
            else "OFFLINE"
        ),
        http_status=response["status"],
        latency_ms=response["latency_ms"],
        message=response.get(
            "error",
            "Invalid CoinGlass response"
        ),
        endpoint=endpoint
    )


# ============================================================
# CRYPTOPANIC
# ============================================================

def test_cryptopanic():

    endpoint = (
        "https://cryptopanic.com/api/"
        "developer/v2/posts/"
    )

    if not CRYPTOPANIC_API_KEY:

        return result(
            source="CRYPTOPANIC",
            arm="NEWS",
            status="CONFIG_REQUIRED",
            message=(
                "Set CRYPTOPANIC_API_KEY "
                "before testing CryptoPanic"
            ),
            endpoint=endpoint
        )

    endpoint += (
        "?auth_token="
        + CRYPTOPANIC_API_KEY
        + "&public=true"
    )

    headers = {
        "Accept": "application/json",
        "User-Agent": "ArundaSourceEngine/0.1"
    }

    response = http_get(
        endpoint,
        headers
    )

    data = parse_json(
        response.get("body", b"")
    )

    if response["ok"] and data:

        return result(
            source="CRYPTOPANIC",
            arm="NEWS",
            status="ONLINE",
            http_status=response["status"],
            latency_ms=response["latency_ms"],
            data_received=True,
            message="CryptoPanic returned news",
            endpoint=endpoint
        )

    return result(
        source="CRYPTOPANIC",
        arm="NEWS",
        status=(
            "AUTH_ERROR"
            if response["status"] in (401, 403)
            else "OFFLINE"
        ),
        http_status=response["status"],
        latency_ms=response["latency_ms"],
        message=response.get(
            "error",
            "Invalid CryptoPanic response"
        ),
        endpoint=endpoint
    )


# ============================================================
# FRED
# ============================================================

def test_fred():

    endpoint = (
        "https://api.stlouisfed.org/"
        "fred/series/observations"
    )

    #
    # DXY is represented by series DEXUSAL in FRED
    # only as an example of an economic series.
    #
    # For the first connectivity test we use
    # a lightweight series request.
    #

    if not FRED_API_KEY:

        return result(
            source="FRED",
            arm="MACRO",
            status="CONFIG_REQUIRED",
            message=(
                "Set FRED_API_KEY "
                "before testing FRED"
            ),
            endpoint=endpoint
        )

    full_endpoint = (
        endpoint
        + "?series_id=DFF"
        + "&api_key="
        + FRED_API_KEY
        + "&file_type=json"
        + "&limit=1"
    )

    headers = {
        "Accept": "application/json",
        "User-Agent": "ArundaSourceEngine/0.1"
    }

    response = http_get(
        full_endpoint,
        headers
    )

    data = parse_json(
        response.get("body", b"")
    )

    if response["ok"] and data:

        return result(
            source="FRED",
            arm="MACRO",
            status="ONLINE",
            http_status=response["status"],
            latency_ms=response["latency_ms"],
            data_received=True,
            message="FRED returned economic data",
            endpoint=endpoint
        )

    return result(
        source="FRED",
        arm="MACRO",
        status=(
            "AUTH_ERROR"
            if response["status"] in (401, 403)
            else "OFFLINE"
        ),
        http_status=response["status"],
        latency_ms=response["latency_ms"],
        message=response.get(
            "error",
            "Invalid FRED response"
        ),
        endpoint=endpoint
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_tests():

    tests = [

        test_binance,

        test_coinmarketcap,

        test_coinapi,

        test_coinglass,

        test_cryptopanic,

        test_fred

    ]

    results = []

    for test in tests:

        try:

            results.append(
                test()
            )

        except Exception as e:

            results.append(
                result(
                    source=test.__name__,
                    arm="UNKNOWN",
                    status="ERROR",
                    message=str(e)
                )
            )

    return results


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    conn,
    results
):

    for item in results:

        conn.execute("""
            INSERT INTO source_status (

                timestamp,
                source,
                arm,
                status,
                http_status,
                latency_ms,
                data_received,
                message,
                endpoint,
                engine_version

            )

            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
        """, (

            item["timestamp"],

            item["source"],

            item["arm"],

            item["status"],

            item["http_status"],

            item["latency_ms"],

            item["data_received"],

            item["message"],

            item["endpoint"],

            item["engine_version"]

        ))

    conn.commit()


# ============================================================
# PRINT
# ============================================================

def print_header():

    print()
    print("=" * 90)
    print(
        "                 ARUNDA SOURCE ENGINE v0.1"
    )
    print("=" * 90)

    print(
        "Purpose : REAL CONNECTIVITY + DATA AVAILABILITY TEST"
    )

    print(
        "Database: arunda.db"
    )

    print("=" * 90)
    print()


def print_result(item):

    latency = item["latency_ms"]

    if latency is None:
        latency_text = "---"
    else:
        latency_text = (
            f"{latency:.0f} ms"
        )

    http_status = item["http_status"]

    if http_status is None:
        http_text = "---"
    else:
        http_text = str(
            http_status
        )

    data_text = (
        "YES"
        if item["data_received"]
        else "NO"
    )

    print(
        f"{item['source']:15}"
        f" | {item['arm']:14}"
        f" | {item['status']:15}"
        f" | HTTP {http_text:3}"
        f" | {latency_text:8}"
        f" | DATA {data_text}"
    )

    if item["message"]:

        print(
            f"  └─ {item['message']}"
        )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results):

    online = sum(
        1
        for x in results
        if x["status"] == "ONLINE"
    )

    config = sum(
        1
        for x in results
        if x["status"] == "CONFIG_REQUIRED"
    )

    offline = sum(
        1
        for x in results
        if x["status"] in (
            "OFFLINE",
            "AUTH_ERROR"
        )
    )

    errors = sum(
        1
        for x in results
        if x["status"] == "ERROR"
    )

    print()
    print("=" * 90)
    print("SOURCE ENGINE SUMMARY")
    print("=" * 90)

    print(
        f"ONLINE           : {online}"
    )

    print(
        f"CONFIG REQUIRED  : {config}"
    )

    print(
        f"OFFLINE/AUTH     : {offline}"
    )

    print(
        f"ERRORS           : {errors}"
    )

    print("=" * 90)

    print()
    print(
        "Next step: activate only VERIFIED sources."
    )

    print("=" * 90)


# ============================================================
# MAIN
# ============================================================

def main():

    print_header()

    conn = get_connection()

    create_tables(
        conn
    )

    print(
        "Running source connectivity tests..."
    )

    print()

    results = run_tests()

    for item in results:

        print_result(
            item
        )

    save_results(
        conn,
        results
    )

    print_summary(
        results
    )

    conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()