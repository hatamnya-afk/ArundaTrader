# ARUNDA_TRADER_LIVE_CONNECTIVITY_REPAIR_v0.1.py

from __future__ import annotations

import ast
import re
import socket
import ssl
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = [
    PROJECT_ROOT / "market_adapter.py",
    PROJECT_ROOT / "news_adapter.py",
    PROJECT_ROOT / "coinalyze_positioning.py",
    PROJECT_ROOT / "arunda_source_engine.py",
]


def extract_urls(text: str) -> list[str]:
    urls = re.findall(
        r'https?://[^\s\'"<>]+',
        text,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for url in urls:
        url = url.rstrip("),]}>'\"")
        if url not in cleaned:
            cleaned.append(url)

    return cleaned


def classify(url: str) -> str:
    u = url.lower()

    if "coinmarketcap" in u or "cmc" in u:
        return "CMC"

    if "coinalyze" in u:
        return "COINALYZE"

    if any(x in u for x in (
        "news",
        "rss",
        "cryptopanic",
        "googleapis",
        "feed",
    )):
        return "NEWS"

    return "OTHER"


def resolve_host(url: str):
    parsed = urllib.request.urlparse(url)
    host = parsed.hostname

    if not host:
        return None, "NO_HOST"

    try:
        addresses = socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM,
        )

        ips = sorted({
            item[4][0]
            for item in addresses
        })

        return ips, "DNS_OK"

    except Exception as exc:
        return None, f"DNS_FAIL: {exc}"


def request_url(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "ArundaTrader/ConnectivityRepair"
            )
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:

            body = response.read(512)

            return {
                "status": response.status,
                "reason": response.reason,
                "headers": dict(response.headers),
                "body_prefix": body.decode(
                    "utf-8",
                    errors="replace",
                ),
                "error": None,
            }

    except urllib.error.HTTPError as exc:

        return {
            "status": exc.code,
            "reason": str(exc.reason),
            "headers": dict(exc.headers),
            "body_prefix": exc.read(512).decode(
                "utf-8",
                errors="replace",
            ),
            "error": "HTTP_ERROR",
        }

    except urllib.error.URLError as exc:

        return {
            "status": None,
            "reason": None,
            "headers": {},
            "body_prefix": "",
            "error": f"URL_ERROR: {exc.reason}",
        }

    except ssl.SSLError as exc:

        return {
            "status": None,
            "reason": None,
            "headers": {},
            "body_prefix": "",
            "error": f"SSL_ERROR: {exc}",
        }

    except Exception as exc:

        return {
            "status": None,
            "reason": None,
            "headers": {},
            "body_prefix": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE CONNECTIVITY REPAIR v0.1"
    )
    print("=" * 100)

    urls = []

    print("\nPROJECT URL DISCOVERY")
    print("-" * 100)

    for path in TARGET_FILES:

        if not path.exists():
            continue

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        found = extract_urls(text)

        for url in found:

            if url not in urls:
                urls.append(url)

                print(
                    f"{classify(url):12} | "
                    f"{path.name:45} | "
                    f"{url}"
                )

    print("\n" + "=" * 100)
    print("CONNECTIVITY TEST")
    print("=" * 100)

    results = []

    for url in urls:

        category = classify(url)

        if category == "OTHER":
            continue

        print("\n" + "-" * 100)
        print(f"SOURCE : {category}")
        print(f"URL    : {url}")

        ips, dns_status = resolve_host(url)

        print(f"DNS    : {dns_status}")

        if ips:
            print(
                "IPS    : "
                + ", ".join(ips)
            )

        result = request_url(url)

        print(
            f"HTTP   : "
            f"{result['status']} "
            f"{result['reason']}"
        )

        if result["error"]:
            print(
                f"ERROR  : "
                f"{result['error']}"
            )

        if result["body_prefix"]:
            print(
                "BODY   : "
                + result["body_prefix"]
                .replace("\n", " ")
                [:300]
            )

        results.append({
            "source": category,
            "url": url,
            "dns": dns_status,
            "ips": ips,
            "http_status": result["status"],
            "http_reason": result["reason"],
            "error": result["error"],
        })

    print("\n" + "=" * 100)
    print("FINAL CONNECTIVITY RESULT")
    print("=" * 100)

    for source in (
        "CMC",
        "COINALYZE",
        "NEWS",
    ):

        rows = [
            x for x in results
            if x["source"] == source
        ]

        if not rows:
            print(
                f"{source:12} : "
                "NO_URL_FOUND"
            )
            continue

        working = [
            x for x in rows
            if (
                x["http_status"] is not None
                and 200 <= x["http_status"] < 400
            )
        ]

        if working:
            print(
                f"{source:12} : "
                "REACHABLE"
            )
        else:
            print(
                f"{source:12} : "
                "NOT_REACHABLE"
            )

    print("=" * 100)
    print(
        "NO DATABASE ACCESS"
    )
    print(
        "NO ENGINE EXECUTION"
    )
    print(
        "NO SIGNAL CREATION"
    )
    print(
        "NO SIGNAL INJECTION"
    )
    print(
        "NO PRODUCTION WRITE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()