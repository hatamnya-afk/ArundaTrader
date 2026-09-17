import json
import time
import urllib.request
import urllib.error

RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.nostr.band",
    "wss://nostr.wine",
]

TIMEOUT = 6


def probe(relay):
    # WebSocket handshake فقط با urllib ممکن نیست؛
    # برای Probe اولیه، TLS/DNS/HTTPS endpoint را تست می‌کنیم.
    host = relay.replace("wss://", "https://").rstrip("/")
    url = host + "/"

    started = time.perf_counter()

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ArundaTrader-Nostr-Probe/0.1"},
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            elapsed = round(time.perf_counter() - started, 3)
            return {
                "relay": relay,
                "status": "PASS",
                "http": r.status,
                "latency": elapsed,
            }

    except urllib.error.HTTPError as e:
        elapsed = round(time.perf_counter() - started, 3)

        # HTTP response یعنی شبکه/host قابل دسترسی است.
        return {
            "relay": relay,
            "status": "PASS",
            "http": e.code,
            "latency": elapsed,
        }

    except Exception as e:
        elapsed = round(time.perf_counter() - started, 3)
        return {
            "relay": relay,
            "status": "FAIL",
            "error": type(e).__name__,
            "latency": elapsed,
        }


def main():
    results = [probe(relay) for relay in RELAYS]

    passed = sum(x["status"] == "PASS" for x in results)

    print("=" * 64)
    print("ARUNDA NOSTR RUNTIME PROBE v0.1")
    print("=" * 64)

    for r in results:
        if r["status"] == "PASS":
            print(
                f"PASS | {r['relay']} | "
                f"HTTP={r['http']} | {r['latency']}s"
            )
        else:
            print(
                f"FAIL | {r['relay']} | "
                f"{r['error']} | {r['latency']}s"
            )

    print("-" * 64)
    print(f"RELAY_PASS={passed}/{len(RELAYS)}")
    print(f"RUNTIME={'PASS' if passed >= 2 else 'FAIL'}")
    print("DB_WRITE=0")
    print("LUNARCRUSH=0")
    print("EXECUTION=OFF")
    print("=" * 64)

    with open(
        "nostr_runtime_probe_result_v0_1.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "version": "NOSTR_RUNTIME_PROBE_v0.1",
                "results": results,
                "relay_pass": passed,
                "runtime": "PASS" if passed >= 2 else "FAIL",
                "db_write": 0,
                "lunarcrush": 0,
                "execution": "OFF",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    main()